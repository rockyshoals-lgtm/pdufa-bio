"""
ODIN v10.65 — Enhanced Logistic PDUFA Engine
-------------------------------------------

This module builds upon the v10.6 "Golden" logistic engine by adding
several empirically motivated features and refining the handling of
sponsor experience, designation stacks, therapeutic areas, modality
complexity and synergies.  The goal is to preserve the honesty and
calibration of the original logistic model while capturing additional
positive drivers identified in historical data.

Key additions:

* **Sponsor tiers:** separate boosts for sponsors with 1–4, 5–10 and >10
  prior approvals, in addition to a penalty for zero approvals.  Medium
  sponsors (5–10 approvals) receive the largest uplift based on their
  superior track record【858793163435896†L36-L46】.
* **Designation stack boost:** a logit increment when an event has two or
  more FDA designations (e.g. BTD + Orphan).  This captures the high
  approval rate of multi‑designated programmes【858793163435896†L59-L64】.
* **Therapeutic‑area enhancements:** discrete boosts for Infectious
  Disease, Respiratory, Vaccines and Oncology indications.  These
  complement the existing TA adjustment table without double counting.
* **Modality & complexity refinements:** positive weights for
  cell/gene therapies, vaccines and antibodies, plus a penalty for
  high‑complexity modalities and a bonus for medium complexity.
* **Synergy features:** additional uplifts for Infectious Disease
  programmes with ≥2 designations or Breakthrough Therapy, and a modest
  boost when an experienced sponsor (≥5 approvals) has multiple
  designations.

As with earlier versions, the model computes the log‑odds by summing
the base logit and all applicable weights, then applies the logistic
function to obtain a probability.  Tier thresholds remain at 0.85/0.65/0.40.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional
import math

# === CONFIGURATION FOR v10.65 ===

@dataclass(frozen=True)
class OdinV1065Config:
    """
    Configuration container for ODIN v10.65 logit weights.

    Weights are expressed on the log‑odds scale; positive values
    increase the probability and negative values decrease it.
    """
    # Base logit corresponding to ~77% base approval probability
    base_logit: float = 1.2096

    # --- Penalties (negative logit contributions) ---
    prior_crl_penalty: float = -1.9705
    class1_resubmission_boost: float = 0.5040
    sponsor_zero_penalty: float = -1.4900
    manufacturing_risk_penalty: float = -0.9153
    form_483_penalty: float = -0.9857
    adcom_mid_penalty: float = -0.4663
    adcom_low_penalty: float = -0.5913

    # --- Existing designation and boost weights (positive) ---
    btd_weight: float = 0.1249
    orphan_weight: float = 0.1718
    priority_review_weight: float = 0.4306
    fast_track_weight: float = 0.1822
    accelerated_approval_weight: float = 0.4710
    experienced_sponsor_boost: float = 0.5826  # fallback boost for ≥5 approvals when no tier specified
    adcom_high_boost: float = 1.3553

    # --- New sponsor tier boosts ---
    sponsor_1_4_boost: float = 0.35
    sponsor_5_10_boost: float = 1.20
    sponsor_gt10_boost: float = 0.80

    # --- Designation stack and synergy boosts ---
    des_count_ge2_boost: float = 0.50
    sponsor_ge5_des2_boost: float = 0.20
    infectious_des2_boost: float = 0.60
    infectious_btd_boost: float = 0.40

    # --- Modality and complexity adjustments ---
    complexity_medium_boost: float = 0.30
    complexity_high_penalty: float = -0.30
    modality_cellgene_boost: float = 0.50
    modality_vaccine_boost: float = 0.40
    modality_antibody_boost: float = 0.20

    # --- Therapeutic area discrete boosts ---
    ta_infectious_boost: float = 0.40
    ta_respiratory_boost: float = 0.50
    ta_vaccines_boost: float = 0.50
    ta_oncology_boost: float = 0.40

    # --- Adjusted TA penalty/bonus table (used with ta_adjustment_weight) ---
    # Certain positive TA categories have been zeroed to avoid double counting with discrete boosts.
    TA_ADJUSTMENTS: Dict[str, float] = field(default_factory=lambda: {
        "Pain Management": -0.30,
        "Ophthalmology": -0.25,
        "Nephrology": -0.22,
        "Hematology": -0.18,
        "CNS/Neurology": -0.10,
        "CNS": -0.10,
        "Cardiovascular": -0.08,
        "Metabolic": -0.07,
        "Other": -0.06,
        "Rare Disease": -0.04,
        # Positive TA classes set to zero to prevent double counting
        "Immunology": 0.0,
        "Dermatology": 0.0,
        "Oncology": 0.0,
        "GI": 0.0,
        "Infectious Disease": 0.0,
        "Respiratory": 0.0,
        "Vaccines": 0.0,
    })
    ta_adjustment_weight: float = 0.4912

    # --- Tier thresholds (probability) ---
    tier1_threshold: float = 0.85
    tier2_threshold: float = 0.65
    tier3_threshold: float = 0.40


def _sigmoid(x: float) -> float:
    """Logistic function mapping logit to probability."""
    # guard against overflow
    if x < -35.0:
        return 0.0
    if x > 35.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _to_bool(val: Any) -> bool:
    """Convert various truthy representations to bool."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"true", "1", "yes", "y", "t", "approved", "success"}


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _to_int(val: Any, default: int = -1) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def score_pdufa_event(
    event: Mapping[str, Any],
    config: Optional[OdinV1065Config] = None
) -> Dict[str, Any]:
    """
    Compute the logit, probability and tier for a given PDUFA event under
    the v10.65 model.

    Parameters
    ----------
    event : mapping
        PDUFA event data with keys matching those in the ODIN dataset.
    config : OdinV1065Config, optional
        Config instance; defaults to OdinV1065Config() if None.

    Returns
    -------
    result : dict
        Contains the ticker, probability, tier, logit and a breakdown of
        logit contributions for interpretability.
    """
    cfg = config or OdinV1065Config()
    logit = cfg.base_logit
    breakdown: Dict[str, float] = {"Base": cfg.base_logit}
    avoids: List[str] = []

    # --- CRL and resubmission ---
    prior_crl = _to_bool(event.get("prior_crl"))
    app_str = str(event.get("catalyst_type") or "").upper()
    if prior_crl or "RESUBMISSION" in app_str:
        cls = _to_int(event.get("resubmission_class"), default=-1)
        if cls == 1:
            delta = cfg.prior_crl_penalty + cfg.class1_resubmission_boost
            logit += delta
            breakdown["CRL_Class1"] = delta
        else:
            logit += cfg.prior_crl_penalty
            breakdown["CRL"] = cfg.prior_crl_penalty

    # --- Sponsor experience tiers ---
    sp_approvals = _to_int(event.get("sponsor_prior_approvals"), default=-1)
    if sp_approvals == 0:
        logit += cfg.sponsor_zero_penalty
        breakdown["Sponsor_0"] = cfg.sponsor_zero_penalty
    elif 1 <= sp_approvals < 5:
        logit += cfg.sponsor_1_4_boost
        breakdown["Sponsor_1_4"] = cfg.sponsor_1_4_boost
    elif 5 <= sp_approvals <= 10:
        logit += cfg.sponsor_5_10_boost
        breakdown["Sponsor_5_10"] = cfg.sponsor_5_10_boost
    elif sp_approvals > 10:
        logit += cfg.sponsor_gt10_boost
        breakdown["Sponsor_gt10"] = cfg.sponsor_gt10_boost
    # fallback for unknown negative values
    elif sp_approvals >= 5:
        logit += cfg.experienced_sponsor_boost
        breakdown["Sponsor_Exp"] = cfg.experienced_sponsor_boost

    # --- Manufacturing / CMC ---
    if _to_bool(event.get("manufacturing_risk")):
        logit += cfg.manufacturing_risk_penalty
        breakdown["Mfg_Risk"] = cfg.manufacturing_risk_penalty
    if _to_bool(event.get("form_483_issues")):
        logit += cfg.form_483_penalty
        breakdown["Form_483"] = cfg.form_483_penalty

    # --- AdCom ---
    if _to_bool(event.get("had_adcom")):
        vote = _to_float(event.get("adcom_vote_pct"))
        if vote > 1.0:
            vote /= 100.0
        if vote >= 0.65:
            logit += cfg.adcom_high_boost
            breakdown["AdCom_High"] = cfg.adcom_high_boost
        elif vote >= 0.50:
            logit += cfg.adcom_mid_penalty
            breakdown["AdCom_Mid"] = cfg.adcom_mid_penalty
        else:
            logit += cfg.adcom_low_penalty
            breakdown["AdCom_Low"] = cfg.adcom_low_penalty

    # --- Designations ---
    if _to_bool(event.get("btd")):
        logit += cfg.btd_weight
        breakdown["BTD"] = cfg.btd_weight
    if _to_bool(event.get("orphan")):
        logit += cfg.orphan_weight
        breakdown["Orphan"] = cfg.orphan_weight
    if _to_bool(event.get("priority_review")):
        logit += cfg.priority_review_weight
        breakdown["Priority"] = cfg.priority_review_weight
    if _to_bool(event.get("fast_track")):
        logit += cfg.fast_track_weight
        breakdown["FastTrack"] = cfg.fast_track_weight
    if _to_bool(event.get("accelerated_approval")):
        logit += cfg.accelerated_approval_weight
        breakdown["Accel"] = cfg.accelerated_approval_weight

    # --- Designation stack count boost ---
    des_count = _to_int(event.get("designation_stack_count"), default=0)
    if des_count >= 2:
        logit += cfg.des_count_ge2_boost
        breakdown["Des_ge2"] = cfg.des_count_ge2_boost

    # --- Sponsor × designation synergy ---
    if sp_approvals >= 5 and des_count >= 2:
        logit += cfg.sponsor_ge5_des2_boost
        breakdown["Sponsor_ge5_Des2"] = cfg.sponsor_ge5_des2_boost

    # --- Modality complexity ---
    comp = str(event.get("modality_complexity") or "").upper()
    if comp == "MEDIUM":
        logit += cfg.complexity_medium_boost
        breakdown["Comp_MED"] = cfg.complexity_medium_boost
    elif comp == "HIGH":
        logit += cfg.complexity_high_penalty
        breakdown["Comp_HIGH"] = cfg.complexity_high_penalty

    # --- Modality category boosts ---
    mod = str(event.get("modality") or "").lower()
    if "cell" in mod or "gene" in mod:
        logit += cfg.modality_cellgene_boost
        breakdown["Mod_CellGene"] = cfg.modality_cellgene_boost
    if "vaccine" in mod:
        logit += cfg.modality_vaccine_boost
        breakdown["Mod_Vaccine"] = cfg.modality_vaccine_boost
    if "antibody" in mod:
        logit += cfg.modality_antibody_boost
        breakdown["Mod_Antibody"] = cfg.modality_antibody_boost

    # --- Therapeutic area discrete boosts ---
    ta = str(event.get("therapeutic_area") or "").strip()
    if ta in {"Infectious Disease", "Infectious"}:
        logit += cfg.ta_infectious_boost
        breakdown["TA_Infectious"] = cfg.ta_infectious_boost
    elif ta == "Respiratory":
        logit += cfg.ta_respiratory_boost
        breakdown["TA_Resp"] = cfg.ta_respiratory_boost
    elif ta == "Vaccines":
        logit += cfg.ta_vaccines_boost
        breakdown["TA_Vaccines"] = cfg.ta_vaccines_boost
    elif ta == "Oncology":
        logit += cfg.ta_oncology_boost
        breakdown["TA_Oncology"] = cfg.ta_oncology_boost

    # --- Synergies for Infectious Disease ---
    is_infectious = ta in {"Infectious Disease", "Infectious"}
    if is_infectious and des_count >= 2:
        logit += cfg.infectious_des2_boost
        breakdown["Infectious_Des2"] = cfg.infectious_des2_boost
    if is_infectious and _to_bool(event.get("btd")):
        logit += cfg.infectious_btd_boost
        breakdown["Infectious_BTD"] = cfg.infectious_btd_boost

    # --- Residual TA adjustments (negative classes) ---
    # Use modified TA_ADJUSTMENTS table to penalize high‑risk areas
    ta_factor = cfg.TA_ADJUSTMENTS.get(ta, 0.0)
    if ta_factor != 0.0:
        delta = ta_factor * cfg.ta_adjustment_weight
        logit += delta
        breakdown["TA_Adjust"] = delta

    # --- Compute probability ---
    prob = _sigmoid(logit)

    # --- Tier classification ---
    if prob >= cfg.tier1_threshold:
        tier = "TIER_1"
    elif prob >= cfg.tier2_threshold:
        tier = "TIER_2"
    elif prob >= cfg.tier3_threshold:
        tier = "TIER_3"
    else:
        tier = "TIER_4"

    # Action recommendation (simplified)
    if tier == "TIER_1":
        action = "STANDARD_POSITION"
    elif tier == "TIER_2":
        action = "REDUCED_SIZE"
    elif tier == "TIER_3":
        action = "SMALL_SPEC_OR_AVOID"
    else:
        action = "NO_POSITION"

    return {
        "ticker": str(event.get("ticker", "N/A")),
        "probability": round(prob, 4),
        "tier": tier,
        "action": action,
        "logit": round(logit, 4),
        "breakdown": {k: round(v, 4) for k, v in breakdown.items()}
    }
