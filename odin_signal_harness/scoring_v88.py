
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScoreResult:
    p: np.ndarray                 # final probability
    score_points: np.ndarray      # 0..100
    base_points: np.ndarray       # baseline prior points used (may be overridden)
    adj_points: np.ndarray        # total adjustments excluding base
    details: Dict[str, np.ndarray]  # per-component points (audit)


def _safe_bool(series: pd.Series) -> pd.Series:
    """Return bool series, preserving NaN as NaN (unknown)."""
    if series.dtype == bool:
        return series
    # For object/mixed: map True/False strings, keep NaN
    return series.map(lambda v: v if isinstance(v, bool) else (np.nan if pd.isna(v) else bool(v)))


def score_v88_points(
    df: pd.DataFrame,
    v88_config: Dict[str, Any],
    *,
    base_override_prob: Optional[np.ndarray] = None,
    min_prob: float = 0.05,
    max_prob: float = 0.95,
) -> ScoreResult:
    """
    Reconstruct a v8.8-style points scorer (0-100) from ODIN_v88_UNIFIED_CONFIG.json.

    Notes:
    - This is an *audit-friendly baseline* for signal-discovery harnessing.
    - It is not intended to be a perfect replica of every historical ODIN version.
    """
    p = v88_config["core_params"]
    n = len(df)

    base_points = np.full(n, float(p.get("base", 50.0)), dtype=float)
    if base_override_prob is not None:
        base_points = np.clip(np.asarray(base_override_prob, dtype=float) * 100.0, 0.0, 100.0)

    # Start with zero adjustments
    adj = np.zeros(n, dtype=float)
    details: Dict[str, np.ndarray] = {}

    def add(name: str, pts: np.ndarray) -> None:
        nonlocal adj
        pts = np.asarray(pts, dtype=float)
        details[name] = pts
        adj = adj + pts

    # --- Designations ---
    add("btd", df["btd"].astype(float) * float(p.get("btd", 0.0)))
    add("orphan", df["orphan"].astype(float) * float(p.get("orphan", 0.0)))
    add("priority_review", df["priority_review"].astype(float) * float(p.get("priority", 0.0)))
    add("fast_track", df["fast_track"].astype(float) * float(p.get("fast_track", 0.0)))

    # accelerated_approval sometimes object; treat truthy as 1
    accel = df.get("accelerated_approval")
    if accel is None:
        add("accelerated_approval", np.zeros(n))
    else:
        accel_bool = accel.map(lambda v: False if pd.isna(v) else bool(v)).astype(float).values
        add("accelerated_approval", accel_bool * float(p.get("accel", 0.0)))

    # --- Sponsor experience ---
    exp_flag = df["experienced_sponsor"].astype(bool).values
    sponsor_prior = df["sponsor_prior_approvals"].fillna(0).astype(int).values

    exp_pts = np.where(exp_flag, float(p.get("exp", 0.0)), 0.0)
    some_exp_pts = np.where((~exp_flag) & (sponsor_prior > 0), float(p.get("some_exp", 0.0)), 0.0)
    add("experienced_sponsor", exp_pts + some_exp_pts)

    # --- Stack counts ---
    stack = df["designation_stack_count"].fillna(0).astype(int).values
    stack_pts = np.zeros(n, dtype=float)
    stack_pts = np.where(stack >= 5, float(p.get("stack5", 0.0)), stack_pts)
    stack_pts = np.where(stack == 4, float(p.get("stack4", 0.0)), stack_pts)
    stack_pts = np.where(stack == 3, float(p.get("stack3", 0.0)), stack_pts)
    add("designation_stack_count", stack_pts)

    # stack + experienced synergy (only for big stacks)
    add("stack_exp", np.where((stack >= 4) & exp_flag, float(p.get("stack_exp", 0.0)), 0.0))

    # --- Therapeutic areas ---
    ta = df["therapeutic_area"].fillna("").astype(str).str.lower().values
    ta_pts = np.zeros(n, dtype=float)

    # Map dataset categories -> config keys
    # (kept intentionally small + explicit; unknown stays neutral)
    def is_ta(*needles: str) -> np.ndarray:
        return np.array([any(k in x for k in needles) for x in ta], dtype=bool)

    ta_pts += np.where(is_ta("oncolog"), float(p.get("onc", 0.0)), 0.0)
    ta_pts += np.where(is_ta("infect"), float(p.get("inf", 0.0)), 0.0)
    ta_pts += np.where(is_ta("gene", "cell", "cgt"), float(p.get("gene_cell", 0.0)), 0.0)
    ta_pts += np.where(is_ta("pain"), float(p.get("pain", 0.0)), 0.0)
    ta_pts += np.where(is_ta("hemato"), float(p.get("hemato", 0.0)), 0.0)
    ta_pts += np.where(is_ta("nephro"), float(p.get("nephro", 0.0)), 0.0)
    ta_pts += np.where(is_ta("ophthal", "eye"), float(p.get("ophthal", 0.0)), 0.0)
    ta_pts += np.where(is_ta("cns", "neuro"), float(p.get("cns", 0.0)), 0.0)
    ta_pts += np.where(is_ta("cardio"), float(p.get("cardio", 0.0)), 0.0)
    ta_pts += np.where(is_ta("metab", "endocrine", "diabet"), float(p.get("metab", 0.0)), 0.0)

    add("therapeutic_area", ta_pts)

    # Experienced sponsor in oncology synergy
    add("exp_onc", np.where(exp_flag & is_ta("oncolog"), float(p.get("exp_onc", 0.0)), 0.0))

    # --- Manufacturing risk ---
    mfg = df["manufacturing_risk"].astype(bool).values
    add("manufacturing_risk", np.where(mfg, float(p.get("mfg", 0.0)), 0.0))
    add("mfg_inexp", np.where(mfg & (~exp_flag), float(p.get("mfg_inexp", 0.0)), 0.0))

    # Inexperienced sponsor penalties:
    # - "inexp_highta": penalize inexperienced sponsors in complex / high-scrutiny areas
    # - "inexp_sm": penalize inexperienced + small molecule (often CMC-heavy)
    modality = df["modality"].fillna("").astype(str).str.lower().values
    is_small_molecule = np.array(["small molecule" in m for m in modality], dtype=bool)
    high_ta = is_ta("oncolog") | is_ta("gene", "cell", "cgt") | is_ta("infect")
    add("inexp_highta", np.where((~exp_flag) & high_ta, float(p.get("inexp_highta", 0.0)), 0.0))
    add("inexp_sm", np.where((~exp_flag) & is_small_molecule, float(p.get("inexp_sm", 0.0)), 0.0))

    # --- AdCom ---
    had_adcom = df["had_adcom"].astype(bool).values
    vote = df["adcom_vote_pct"].values  # may be NaN
    adcom_pts = np.zeros(n, dtype=float)

    # Default adcom handling: only apply if had_adcom and vote is known
    vote_known = ~np.isnan(vote)
    strong = had_adcom & vote_known & (vote >= 80.0)
    pos = had_adcom & vote_known & (vote >= 50.0) & (vote < 80.0)
    neg = had_adcom & vote_known & (vote < 50.0)

    adcom_pts += np.where(strong, float(p.get("adcom_strong", 0.0)), 0.0)
    adcom_pts += np.where(pos, float(p.get("adcom_pos", 0.0)), 0.0)
    adcom_pts += np.where(neg, float(p.get("adcom_neg", 0.0)), 0.0)

    add("adcom", adcom_pts)

    # --- Patches (subset implemented for harness) ---
    patches = v88_config.get("patches", {})

    # P001: Class 1 CMC Resubmission floor
    p001 = patches.get("P001_class1_cmc_override", {})
    if p001.get("enabled", False):
        floor = float(p001.get("floor", 95))
        prior_crl = df["prior_crl"].astype(bool).values
        reason = df["prior_crl_reason"].fillna("").astype(str).str.upper().values
        resub_class = df["resubmission_class"].fillna(np.nan).values
        cond = prior_crl & np.isin(reason, ["CMC", "MANUFACTURING"]) & (resub_class == 1)
        # Floor acts on final score points (after adjustments).
        details["P001_floor_mask"] = cond.astype(float)
    else:
        details["P001_floor_mask"] = np.zeros(n)

    # P003: Low-designation clinical risk penalty
    p003 = patches.get("P003_low_designation_clinical_risk", {})
    if p003.get("enabled", False):
        penalty = float(p003.get("penalty", -10))
        trigger = (df["experienced_sponsor"].astype(bool).values
                   & (~df["manufacturing_risk"].astype(bool).values)
                   & (~df["btd"].astype(bool).values)
                   & (df["designation_stack_count"].fillna(0).astype(int).values <= 1))
        add("P003_low_designation_clinical_risk", np.where(trigger, penalty, 0.0))
    else:
        add("P003_low_designation_clinical_risk", np.zeros(n))

    # silent failure: stack==0 and no AdCom vote (approx using had_adcom==False and vote is NaN)
    sf = patches.get("silent_failure", {})
    if sf.get("enabled", False):
        penalty = float(sf.get("penalty", -5))
        trigger = (df["designation_stack_count"].fillna(0).astype(int).values == 0) & (~had_adcom) & (~vote_known)
        add("silent_failure", np.where(trigger, penalty, 0.0))
    else:
        add("silent_failure", np.zeros(n))

    # --- Final combine ---
    score_points = base_points + adj
    score_points = np.clip(score_points, 0.0, 100.0)

    # Apply P001 floor if enabled
    if p001.get("enabled", False):
        floor = float(p001.get("floor", 95))
        prior_crl = df["prior_crl"].astype(bool).values
        reason = df["prior_crl_reason"].fillna("").astype(str).str.upper().values
        resub_class = df["resubmission_class"].fillna(np.nan).values
        cond = prior_crl & np.isin(reason, ["CMC", "MANUFACTURING"]) & (resub_class == 1)
        score_points = np.where(cond, np.maximum(score_points, floor), score_points)

    # Probability clamp
    p_pred = np.clip(score_points / 100.0, min_prob, max_prob)

    return ScoreResult(
        p=p_pred,
        score_points=score_points,
        base_points=base_points,
        adj_points=adj,
        details=details,
    )
