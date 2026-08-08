
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

# Make local package importable without requiring `pip install`.
#
# Common failure mode on Windows: the user copies `run_v38a_signal_discovery.py`
# out of the extracted folder and runs it from elsewhere, so `odin_signal_harness/`
# is no longer on sys.path. We defensively search a few likely locations.
def _ensure_local_package_importable() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        script_dir,
        os.path.join(script_dir, "ODIN_signal_harness_v38"),
        os.path.join(script_dir, "ODIN_signal_harness_v38_dynamic_ram"),
    ]

    parent = os.path.dirname(script_dir)
    if parent and parent != script_dir:
        candidates.extend([
            parent,
            os.path.join(parent, "ODIN_signal_harness_v38"),
            os.path.join(parent, "ODIN_signal_harness_v38_dynamic_ram"),
        ])

    for cand in candidates:
        pkg_dir = os.path.join(cand, "odin_signal_harness")
        if os.path.isdir(pkg_dir) and os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return

    raise ModuleNotFoundError(
        "Could not find local 'odin_signal_harness' package.\n\n"
        "Fix: Extract the harness zip so the folder structure looks like:\n"
        "  ODIN_signal_harness_v38\\\n"
        "    run_v38a_signal_discovery.py\n"
        "    odin_signal_harness\\\n"
        "      __init__.py\n\n"
        "Then either:\n"
        "  (A) cd into ODIN_signal_harness_v38 and run the script there, OR\n"
        "  (B) keep run_v38a_signal_discovery.py next to odin_signal_harness\\\n"
        "      (do not copy the script by itself).\n"
    )


_ensure_local_package_importable()
import pandas as pd

from odin_signal_harness.registry import SignalRegistry
from odin_signal_harness.runner import RunSettings, run_ablation, run_marginal_tests, write_run_artifacts, validate_t_minus_1
from odin_signal_harness.signals_builtin import (
    signal_adcom_vote_curve,
    signal_form483_flag,
    signal_publication_velocity_stub,
    signal_rolling_t1_base_rate,
    signal_trap_v2,
)

from odin_signal_harness.resources import RamBudgetPolicy
from odin_signal_harness.signal_cache import ByteLRUCache


def build_registry() -> SignalRegistry:
    reg = SignalRegistry()
    reg.register(signal_trap_v2())
    reg.register(signal_form483_flag())
    reg.register(signal_adcom_vote_curve())
    reg.register(signal_rolling_t1_base_rate(min_n=20, group_cols=("therapeutic_area", "modality")))
    # Stub (won't run until enrichment columns are present)
    reg.register(signal_publication_velocity_stub())
    return reg


def main() -> None:
    ap = argparse.ArgumentParser(description="ODIN v38 signal-discovery harness (marginal tests + ablation).")
    ap.add_argument("--dataset", required=True, help="Path to ODIN dataset CSV (T-1 safe).")
    ap.add_argument("--baseline-config", required=True, help="Path to baseline config JSON (v8.8 unified recommended).")
    ap.add_argument("--outdir", required=True, help="Output directory for run artifacts.")
    ap.add_argument("--version", default="v38.a", help="Version tag (e.g., v38.a).")
    ap.add_argument("--precision-floor", type=float, default=0.94, help="Hard precision floor.")
    ap.add_argument("--min-prob", type=float, default=0.05, help="Clamp min probability.")
    ap.add_argument("--max-prob", type=float, default=0.95, help="Clamp max probability.")
    ap.add_argument("--fixed-threshold", type=float, default=None, help="Optional fixed threshold evaluation.")
    ap.add_argument("--signals", default=None, help="Comma-separated list of signals to test (default: all computable).")
    ap.add_argument("--ablate", default=None, help="Comma-separated list of signals for leave-one-out ablation.")

    # Optional: RAM-aware caching of computed signal outputs (helps big ablations).
    ap.add_argument("--ram-mode", choices=["off", "fixed", "dynamic"], default="off", help="RAM budget mode for signal cache.")
    ap.add_argument("--ram-fixed-gb", type=float, default=2.0, help="Cache budget in GB (fixed mode).")
    ap.add_argument("--ram-frac-available", type=float, default=0.25, help="Fraction of available RAM to use (dynamic mode).")
    ap.add_argument("--ram-reserve-gb", type=float, default=2.0, help="Always try to leave this many GB free (dynamic mode).")
    ap.add_argument("--ram-min-gb", type=float, default=0.25, help="Minimum cache budget in GB (dynamic mode).")
    ap.add_argument("--ram-max-gb", type=float, default=32.0, help="Maximum cache budget in GB (dynamic mode).")
    ap.add_argument("--ram-pressure-lo", type=float, default=0.65, help="Used%% (0..1) below which cache is unscaled (dynamic mode).")
    ap.add_argument("--ram-pressure-hi", type=float, default=0.85, help="Used%% (0..1) at which cache is maximally scaled down.")
    ap.add_argument("--ram-pressure-scale-hi", type=float, default=0.50, help="Scale factor applied at/above --ram-pressure-hi.")
    ap.add_argument("--ram-recompute-every-s", type=float, default=1.0, help="How often to recompute dynamic RAM budget.")
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    with open(args.baseline_config, "r") as f:
        cfg = json.load(f)

    reg = build_registry()
    settings = RunSettings(
        version=args.version,
        precision_floor=args.precision_floor,
        min_prob=args.min_prob,
        max_prob=args.max_prob,
        fixed_threshold=args.fixed_threshold,
    )

    signal_names: Optional[List[str]] = None
    if args.signals:
        signal_names = [s.strip() for s in args.signals.split(",") if s.strip()]

    # Optional RAM-aware cache (dynamic budgets supported)
    cache = None
    if args.ram_mode != "off":
        policy = RamBudgetPolicy(
            mode=args.ram_mode,
            fixed_gb=args.ram_fixed_gb,
            frac_available=args.ram_frac_available,
            reserve_gb=args.ram_reserve_gb,
            min_gb=args.ram_min_gb,
            max_gb=args.ram_max_gb,
            pressure_lo=args.ram_pressure_lo,
            pressure_hi=args.ram_pressure_hi,
            pressure_scale_hi=args.ram_pressure_scale_hi,
            recompute_every_s=args.ram_recompute_every_s,
        )
        cache = ByteLRUCache(policy)
        # Prime budget snapshot once at start (and validate psutil availability)
        _ = cache.budget_bytes()

        # One-line sanity log so users can confirm dynamic mode is active.
        # (This is intentionally minimal and does not affect run determinism.)
        snap = cache.snapshot()
        mem = (snap.get("policy") or {}).get("mem") or {}
        used = mem.get("used_percent")
        used_str = (f"{float(used) * 100.0:.0f}%" if isinstance(used, (int, float)) else "?%")
        avail = mem.get("available_gb")
        avail_str = (f"{float(avail):.2f}GB" if isinstance(avail, (int, float)) else "?GB")
        src = mem.get("source") or "unknown"
        print(
            f"[ram-cache] mode={args.ram_mode} budget={snap.get('budget_gb', 0.0):.2f}GB "
            f"avail={avail_str} used={used_str} source={src}",
            flush=True,
        )

    marginal = run_marginal_tests(df, cfg, reg, settings, signal_names=signal_names, cache=cache)

    ablation_df = None
    if args.ablate:
        active = [s.strip() for s in args.ablate.split(",") if s.strip()]
        ablation_df = run_ablation(df, cfg, reg, settings, active_signals=active, cache=cache)

    run_hash = write_run_artifacts(
        args.outdir,
        settings=settings,
        dataset_path=args.dataset,
        baseline_config_path=args.baseline_config,
        marginal_df=marginal,
        ablation_df=ablation_df,
        extra_manifest={
            "signals_registered": reg.list_names(),
            **validate_t_minus_1(df),
            "signal_cache": cache.snapshot() if cache is not None else {"enabled": False},
        },
    )

    print(f"Run complete. run_hash={run_hash}", flush=True)
    print(f"Artifacts written to: {os.path.abspath(args.outdir)}", flush=True)
    print("", flush=True)


if __name__ == "__main__":
    main()
