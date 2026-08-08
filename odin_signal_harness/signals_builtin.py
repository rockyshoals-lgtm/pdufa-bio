
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .registry import DataStatus, Signal, SignalMeta, SignalOutput


def _as_float(x: pd.Series) -> np.ndarray:
    return x.astype(float).to_numpy()


def signal_trap_v2() -> Signal:
    """
    Trap v2 (backtestable from core dataset):
      - designation_stack_count >= 4
      - inexperienced sponsor
      - NOT orphan

    Rationale: designation stacks can create false confidence, especially for inexperienced sponsors.
    """
    meta = SignalMeta(
        name="trap_v2_stack4_inexp_non_orphan",
        description="Penalty when stack>=4 AND experienced_sponsor=False AND orphan=False (Designation Trap v2).",
        kind="adjustment",
        data_status="backtestable",
        expects_columns=("designation_stack_count", "experienced_sponsor", "orphan"),
        default_weight=1.0,
        default_cap=(-0.25, 0.0),
        tags=("fp_reduction", "trap", "designation"),
    )

    def fn(df: pd.DataFrame) -> SignalOutput:
        stack = df["designation_stack_count"].fillna(0).astype(int).to_numpy()
        exp = df["experienced_sponsor"].astype(bool).to_numpy()
        orphan = df["orphan"].astype(bool).to_numpy()
        trigger = (stack >= 4) & (~exp) & (~orphan)

        # Canonical penalty: -10pp (not tuned)
        adj = np.where(trigger, -0.10, 0.0)
        return SignalOutput(adjustment=adj, notes={"trigger_rate": float(trigger.mean())})

    return Signal(meta=meta, fn=fn)


def signal_form483_flag() -> Signal:
    meta = SignalMeta(
        name="form_483_flag",
        description="Penalty if form_483_issues=True (proxy for inspection/CMP risk).",
        kind="adjustment",
        data_status="backtestable",
        expects_columns=("form_483_issues",),
        default_weight=1.0,
        default_cap=(-0.20, 0.0),
        tags=("cmc", "fp_reduction"),
    )

    def fn(df: pd.DataFrame) -> SignalOutput:
        flag = df["form_483_issues"].astype(bool).to_numpy()
        adj = np.where(flag, -0.06, 0.0)  # canonical -6pp
        return SignalOutput(adjustment=adj, notes={"trigger_rate": float(flag.mean())})

    return Signal(meta=meta, fn=fn)


def signal_adcom_vote_curve() -> Signal:
    meta = SignalMeta(
        name="adcom_vote_curve",
        description="Continuous AdCom vote% curve adjustment (replaces coarse buckets).",
        kind="adjustment",
        data_status="backtestable",
        expects_columns=("had_adcom", "adcom_vote_pct"),
        default_weight=1.0,
        default_cap=(-0.35, 0.20),
        tags=("adcom", "calibration"),
    )

    def fn(df: pd.DataFrame) -> SignalOutput:
        had = df["had_adcom"].astype(bool).to_numpy()
        vote = df["adcom_vote_pct"].to_numpy()  # may have NaN
        out = np.zeros(len(df), dtype=float)

        # Map vote% to [-0.30, +0.15] with a smooth-ish piecewise-linear curve.
        # - Below 50%: strong negative
        # - 50-70: mild positive
        # - 70-90: stronger positive
        # - >90: saturate
        v = vote.copy()
        known = ~np.isnan(v)
        active = had & known

        vv = v[active]
        adj = np.zeros_like(vv, dtype=float)

        # below 50: down to -0.30 at 0%
        m1 = vv < 50
        adj[m1] = -0.30 * (50 - vv[m1]) / 50.0

        # 50-70: 0 to +0.06
        m2 = (vv >= 50) & (vv < 70)
        adj[m2] = 0.06 * (vv[m2] - 50) / 20.0

        # 70-90: +0.06 to +0.12
        m3 = (vv >= 70) & (vv < 90)
        adj[m3] = 0.06 + 0.06 * (vv[m3] - 70) / 20.0

        # 90-100: +0.12 to +0.15
        m4 = vv >= 90
        adj[m4] = 0.12 + 0.03 * (np.minimum(vv[m4], 100) - 90) / 10.0

        out[active] = adj
        return SignalOutput(adjustment=out, notes={"active_rate": float(active.mean())})

    return Signal(meta=meta, fn=fn)


def signal_rolling_t1_base_rate(
    *,
    min_n: int = 20,
    group_cols: Tuple[str, ...] = ("therapeutic_area", "modality"),
) -> Signal:
    meta = SignalMeta(
        name="rolling_t1_reference_base_rate",
        description=(
            "T-1-safe rolling approval base rate by reference class (group_cols), "
            "with fallback to therapeutic_area then global if prior N < min_n."
        ),
        kind="base_override",
        data_status="backtestable",
        expects_columns=("catalyst_date", "outcome", "therapeutic_area", "modality"),
        default_weight=1.0,
        tags=("base_rate", "calibration", "t_minus_1"),
    )

    def fn(df: pd.DataFrame) -> SignalOutput:
        d = df.copy()
        d["catalyst_date"] = pd.to_datetime(d["catalyst_date"])
        d = d.sort_values("catalyst_date").reset_index(drop=True)

        y = (d["outcome"].astype(str).str.upper() == "APPROVAL").astype(int)

        # Global rolling prior (exclude current via shift)
        g_count = np.arange(len(d))
        g_approvals = y.cumsum().shift(1).fillna(0).astype(int)
        g_n = pd.Series(g_count).astype(int)
        g_rate = (g_approvals / g_n.replace(0, np.nan)).fillna(y.mean()).to_numpy()

        # TA rolling
        ta = d["therapeutic_area"].fillna("UNKNOWN").astype(str)
        ta_approvals = y.groupby(ta).cumsum().shift(1).fillna(0).astype(int)
        ta_n = d.groupby(ta).cumcount()
        ta_rate = (ta_approvals / ta_n.replace(0, np.nan)).fillna(np.nan).to_numpy()

        # Group rolling
        grp = d[list(group_cols)].fillna("UNKNOWN").astype(str).agg("|".join, axis=1)
        grp_approvals = y.groupby(grp).cumsum().shift(1).fillna(0).astype(int)
        grp_n = d.groupby(grp).cumcount()
        grp_rate = (grp_approvals / grp_n.replace(0, np.nan)).fillna(np.nan).to_numpy()

        # Choose best available rate with sufficient N
        grp_ok = grp_n.to_numpy() >= min_n
        ta_ok = ta_n.to_numpy() >= min_n

        base = np.where(grp_ok, grp_rate, np.where(ta_ok, ta_rate, g_rate))
        base = np.clip(base, 0.01, 0.99)

        # Reorder back to original df index order
        # Return aligned to the *input df* order.
        base_aligned = pd.Series(base, index=d.index).reindex(df.index).to_numpy()

        return SignalOutput(
            base_override=base_aligned,
            notes={
                "min_n": int(min_n),
                "group_cols": ",".join(group_cols),
                "grp_ok_rate": float(grp_ok.mean()),
                "ta_ok_rate": float(ta_ok.mean()),
            },
        )

    return Signal(meta=meta, fn=fn)


# Stubs (registered but only computable once enrichment columns exist)
def signal_publication_velocity_stub() -> Signal:
    meta = SignalMeta(
        name="publication_velocity",
        description="PubMed recent vs lifetime publications (requires enrichment columns).",
        kind="adjustment",
        data_status="needs_enrichment",
        expects_columns=("pubmed_total", "pubmed_recent_24m"),
        default_weight=1.0,
        default_cap=(-0.20, 0.10),
        tags=("pubmed", "backtestable_with_enrichment"),
    )

    def fn(df: pd.DataFrame) -> SignalOutput:
        total = df["pubmed_total"].fillna(np.nan).to_numpy()
        recent = df["pubmed_recent_24m"].fillna(np.nan).to_numpy()
        out = np.zeros(len(df), dtype=float)
        known = (~np.isnan(total)) & (~np.isnan(recent)) & (total > 0)

        # Ratio-based heuristic (canonical, not tuned)
        ratio = np.zeros_like(out)
        ratio[known] = recent[known] / total[known]

        # Penalize very low total pubs
        out[known & (total < 10)] -= 0.10
        out[known & (total < 20) & (total >= 10)] -= 0.06

        # Bonus if recent velocity is high (active field)
        out[known & (ratio >= 0.25) & (total >= 20)] += 0.03

        return SignalOutput(adjustment=out, notes={"known_rate": float(known.mean())})

    return Signal(meta=meta, fn=fn)
