
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .evaluate import Metrics, choose_threshold_fp_averse, metrics_at_threshold
from .registry import Signal, SignalRegistry
from .scoring_v88 import ScoreResult, score_v88_points
from .signal_cache import ByteLRUCache, estimate_signaloutput_bytes


def validate_t_minus_1(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate data_cutoff_date == catalyst_date - 1 day where possible."""
    out: Dict[str, Any] = {"t_minus_1_ok_rate": None, "t_minus_1_bad_rows": 0}
    if "catalyst_date" not in df.columns or "data_cutoff_date" not in df.columns:
        return out
    try:
        cd = pd.to_datetime(df["catalyst_date"])
        cutoff = pd.to_datetime(df["data_cutoff_date"])
        ok = (cutoff == (cd - pd.Timedelta(days=1)))
        out["t_minus_1_ok_rate"] = float(ok.mean())
        out["t_minus_1_bad_rows"] = int((~ok).sum())
    except Exception as e:
        out["t_minus_1_ok_rate"] = None
        out["t_minus_1_error"] = str(e)
    return out

def sha256_file(path: str, block_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(block_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


@dataclass(frozen=True)
class RunSettings:
    version: str
    precision_floor: float = 0.94
    min_prob: float = 0.05
    max_prob: float = 0.95
    fixed_threshold: Optional[float] = None  # if provided, evaluate also at this threshold
    scorer: str = "v88_points"


def _outcome_binary(df: pd.DataFrame) -> np.ndarray:
    return (df["outcome"].astype(str).str.upper() == "APPROVAL").astype(int).to_numpy()


def apply_signal_to_prob(
    p_base: np.ndarray,
    signal: Signal,
    df: pd.DataFrame,
    *,
    min_prob: float,
    max_prob: float,
    cache: Optional[ByteLRUCache[str]] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    out = compute_signal_output(signal, df, cache=cache)
    notes = dict(out.notes)

    if signal.meta.kind == "base_override":
        if out.base_override is None:
            raise ValueError(f"Signal {signal.meta.name} returned no base_override")
        # base_override is used by the scorer; here we just pass it back to caller
        return p_base, {"base_override": out.base_override, **notes}

    if signal.meta.kind == "adjustment":
        if out.adjustment is None:
            raise ValueError(f"Signal {signal.meta.name} returned no adjustment")
        adj = np.asarray(out.adjustment, dtype=float) * float(signal.meta.default_weight)
        if signal.meta.default_cap is not None:
            lo, hi = signal.meta.default_cap
            adj = np.clip(adj, lo, hi)
        p_new = np.clip(p_base + adj, min_prob, max_prob)
        return p_new, {"mean_adj": float(np.mean(adj)), "nonzero_rate": float(np.mean(adj != 0.0)), **notes}

    # transformer reserved
    return p_base, {"note": "transformer kind not applied in v38 harness"}


def compute_signal_output(
    signal: Signal,
    df: pd.DataFrame,
    *,
    cache: Optional[ByteLRUCache[str]] = None,
) -> "SignalOutput":
    """Compute a signal output, optionally using a byte-bounded cache.

    Cache key strategy (v38): signal name only.
    - This harness runs one dataset per process/run, so signal name is
      sufficient. If you mix datasets in-process, create a separate cache
      instance per dataset.
    """
    if cache is not None:
        hit = cache.get(signal.meta.name)
        if hit is not None:
            return hit

    out = signal.fn(df)
    if cache is not None:
        cache.set(signal.meta.name, out, estimate_signaloutput_bytes(out))
    return out


def run_baseline(
    df: pd.DataFrame,
    v88_config: Dict[str, Any],
    settings: RunSettings,
    *,
    base_override: Optional[np.ndarray] = None,
) -> ScoreResult:
    return score_v88_points(
        df,
        v88_config,
        base_override_prob=base_override,
        min_prob=settings.min_prob,
        max_prob=settings.max_prob,
    )


def summarize_model(
    y: np.ndarray,
    p: np.ndarray,
    settings: RunSettings,
) -> Dict[str, Any]:
    thr_opt, m_opt = choose_threshold_fp_averse(y, p, precision_floor=settings.precision_floor)
    summary: Dict[str, Any] = {
        "brier": float(m_opt.brier),
        "threshold_opt": float(thr_opt),
        "precision_opt": float(m_opt.precision),
        "recall_opt": float(m_opt.recall),
        "specificity_opt": float(m_opt.specificity),
        "mcc_opt": float(m_opt.mcc),
        "fp_opt": int(m_opt.fp),
        "tp_opt": int(m_opt.tp),
        "tn_opt": int(m_opt.tn),
        "fn_opt": int(m_opt.fn),
    }
    if settings.fixed_threshold is not None:
        m_fixed = metrics_at_threshold(y, p, float(settings.fixed_threshold))
        summary.update({
            "threshold_fixed": float(settings.fixed_threshold),
            "precision_fixed": float(m_fixed.precision),
            "recall_fixed": float(m_fixed.recall),
            "specificity_fixed": float(m_fixed.specificity),
            "mcc_fixed": float(m_fixed.mcc),
            "fp_fixed": int(m_fixed.fp),
            "tp_fixed": int(m_fixed.tp),
            "tn_fixed": int(m_fixed.tn),
            "fn_fixed": int(m_fixed.fn),
        })
    return summary


def run_marginal_tests(
    df: pd.DataFrame,
    v88_config: Dict[str, Any],
    registry: SignalRegistry,
    settings: RunSettings,
    *,
    signal_names: Optional[Sequence[str]] = None,
    cache: Optional[ByteLRUCache[str]] = None,
) -> pd.DataFrame:
    y = _outcome_binary(df)

    baseline = run_baseline(df, v88_config, settings, base_override=None)
    base_summary = summarize_model(y, baseline.p, settings)

    rows: List[Dict[str, Any]] = []
    rows.append({
        "signal": "__BASELINE__",
        "kind": "baseline",
        "data_status": "backtestable",
        **base_summary,
    })

    if signal_names is None:
        signals = registry.computable_signals(df)
    else:
        signals = [registry.get(n) for n in signal_names]

    for s in signals:
        if s.meta.name == "__BASELINE__":
            continue

        extra: Dict[str, Any] = {}
        # Handle base_override specially: rerun baseline scorer with base override
        if s.meta.kind == "base_override":
            out = compute_signal_output(s, df, cache=cache)
            base_override = out.base_override
            if base_override is None:
                continue
            scored = run_baseline(df, v88_config, settings, base_override=base_override)
            p_new = scored.p
            extra.update(out.notes)
            extra["base_override_mean"] = float(np.mean(base_override))
        else:
            p_new, extra = apply_signal_to_prob(
                baseline.p,
                s,
                df,
                min_prob=settings.min_prob,
                max_prob=settings.max_prob,
                cache=cache,
            )

        summ = summarize_model(y, p_new, settings)

        rows.append({
            "signal": s.meta.name,
            "kind": s.meta.kind,
            "data_status": s.meta.data_status,
            "description": s.meta.description,
            **summ,
            "delta_brier_vs_base": float(summ["brier"] - base_summary["brier"]),
            "delta_fp_opt_vs_base": int(summ["fp_opt"] - base_summary["fp_opt"]),
            "delta_specificity_opt_vs_base": float(summ["specificity_opt"] - base_summary["specificity_opt"]),
            **{f"meta_{k}": v for k, v in extra.items()},
        })

    out_df = pd.DataFrame(rows)
    # Rank: primary by ΔFP (lower better), secondary by ΔBrier (lower better)
    out_df["rank"] = out_df.apply(lambda r: (r.get("delta_fp_opt_vs_base", 0), r.get("delta_brier_vs_base", 0.0)), axis=1)
    out_df = out_df.sort_values(by=["signal"])
    return out_df


def run_ablation(
    df: pd.DataFrame,
    v88_config: Dict[str, Any],
    registry: SignalRegistry,
    settings: RunSettings,
    *,
    active_signals: Sequence[str],
    cache: Optional[ByteLRUCache[str]] = None,
) -> pd.DataFrame:
    """Leave-one-out ablation for a chosen set of signals."""
    y = _outcome_binary(df)

    # Compose signals sequentially on top of baseline.
    baseline = run_baseline(df, v88_config, settings, base_override=None)
    p_full = baseline.p.copy()
    base_override: Optional[np.ndarray] = None

    applied_meta: List[Dict[str, Any]] = []
    for name in active_signals:
        s = registry.get(name)
        if s.meta.kind == "base_override":
            out = compute_signal_output(s, df, cache=cache)
            base_override = out.base_override
            if base_override is None:
                continue
            baseline = run_baseline(df, v88_config, settings, base_override=base_override)
            p_full = baseline.p.copy()
            applied_meta.append({"signal": name, **out.notes})
        else:
            p_full, extra = apply_signal_to_prob(
                p_full,
                s,
                df,
                min_prob=settings.min_prob,
                max_prob=settings.max_prob,
                cache=cache,
            )
            applied_meta.append({"signal": name, **extra})

    full_summary = summarize_model(y, p_full, settings)

    rows: List[Dict[str, Any]] = [{
        "variant": "__FULL__",
        "removed_signal": "",
        **full_summary,
    }]

    for remove in active_signals:
        p = baseline.p.copy()
        base_override2 = base_override
        # Rebuild without 'remove'
        # If we removed base_override signal, we revert to None
        if registry.get(remove).meta.kind == "base_override":
            base_override2 = None
        baseline2 = run_baseline(df, v88_config, settings, base_override=base_override2)
        p = baseline2.p.copy()

        for name in active_signals:
            if name == remove:
                continue
            s = registry.get(name)
            if s.meta.kind == "base_override":
                out = compute_signal_output(s, df, cache=cache)
                bo = out.base_override
                if bo is None:
                    continue
                baseline2 = run_baseline(df, v88_config, settings, base_override=bo)
                p = baseline2.p.copy()
            else:
                p, _ = apply_signal_to_prob(
                    p,
                    s,
                    df,
                    min_prob=settings.min_prob,
                    max_prob=settings.max_prob,
                    cache=cache,
                )

        summ = summarize_model(y, p, settings)
        rows.append({
            "variant": "ablation",
            "removed_signal": remove,
            **summ,
            "delta_brier_vs_full": float(summ["brier"] - full_summary["brier"]),
            "delta_fp_opt_vs_full": int(summ["fp_opt"] - full_summary["fp_opt"]),
            "delta_specificity_opt_vs_full": float(summ["specificity_opt"] - full_summary["specificity_opt"]),
        })

    return pd.DataFrame(rows)


def write_run_artifacts(
    outdir: str,
    *,
    settings: RunSettings,
    dataset_path: str,
    baseline_config_path: str,
    marginal_df: pd.DataFrame,
    ablation_df: Optional[pd.DataFrame] = None,
    extra_manifest: Optional[Dict[str, Any]] = None,
) -> str:
    os.makedirs(outdir, exist_ok=True)

    dataset_hash = sha256_file(dataset_path)
    baseline_hash = sha256_file(baseline_config_path)

    # Write CSVs
    marginal_path = os.path.join(outdir, "marginal_tests.csv")
    marginal_df.to_csv(marginal_path, index=False)

    ablation_path = None
    if ablation_df is not None:
        ablation_path = os.path.join(outdir, "ablations.csv")
        ablation_df.to_csv(ablation_path, index=False)

    manifest: Dict[str, Any] = {
        "version": settings.version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "settings": asdict(settings),
        "dataset": {"path": dataset_path, "sha256": dataset_hash},
        "baseline_config": {"path": baseline_config_path, "sha256": baseline_hash},
        "artifacts": {
            "marginal_tests_csv": marginal_path,
            "ablations_csv": ablation_path,
        },
    }
    if extra_manifest:
        manifest.update(extra_manifest)

    # Immutable run hash = sha256(manifest json without run_hash)
    tmp = dict(manifest)
    tmp.pop("run_hash", None)
    run_hash = hashlib.sha256(json.dumps(tmp, sort_keys=True).encode("utf-8")).hexdigest()
    manifest["run_hash"] = run_hash

    manifest_path = os.path.join(outdir, "run_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return run_hash
