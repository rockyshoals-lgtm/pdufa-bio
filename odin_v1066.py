"""
ODIN v10.66 — ODIN/HINT Hybrid Engine
-------------------------------------

This module extends the v10.65 logistic ODIN engine by blending in
historical indication risk information (HINT) and a handful of
additional high‑risk adjustment features.  The objective is to
further improve calibration and reduce over‑confidence in high risk
therapeutic areas or indications while preserving the transparent,
additive structure of the original ODIN model.

Key enhancements over v10.65:

* **HINT integration:** Each PDUFA event is scored twice: once by the
  refined ODIN logic (v10.65) and once by a simplified HINT
  estimator that uses historical CRL rates by therapeutic area,
  modality and sponsor experience.  The two probabilities are
  combined via a configurable weighted average (`odin_weight` vs
  `hint_weight`).  Empirically a strong ODIN weighting (~0.85)
  delivers good calibration while HINT provides a downwards
  correction for historically challenging indications.

* **High‑risk penalties:**  The model applies extra logit penalties
  when a drug targets therapeutic areas with historically high CRL
  rates (Pain Management, Hematology, Nephrology, Ophthalmology), or
  when the indication string matches one of several granular
  high‑risk patterns (e.g. postoperative pain, Parkinson’s disease).
  Moderate‑risk TAs receive a smaller penalty, while low‑risk TAs
  receive a modest boost.  Novice sponsors (<3 prior approvals) in
  high‑risk TAs incur an additional penalty.

* **TA × modality interactions:**  Certain combinations of
  therapeutic area and modality are known to be more (or less)
  favourable than the TA alone.  For example, Pain Management with a
  small‑molecule modality is particularly risky; Infectious Disease
  with a vaccine modality is especially favourable.  These
  interactions are encoded as additive adjustments to the logit.

* **Weighted ensemble:**  After computing the ODIN probability
  (including the high‑risk adjustments) and the HINT probability, a
  final probability is obtained via `final_prob = odin_weight *
  odin_prob + hint_weight * hint_prob`.  Tier classification and
  action guidance are then derived from this blended probability.

This version does **not** attempt to achieve 95% accuracy on the
hold‑out set — an unrealistic target given the inherent noise and
class balance of the historical PDUFA dataset — but it does deliver
incremental improvements in calibration and robustness compared to
v10.65 by respecting historical CRL patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple
import math

# Import the base v10.65 configuration for reuse
from odin_v1065 import OdinV1065Config, _sigmoid, _to_bool, _to_float, _to_int


@dataclass(frozen=True)
class OdinV1066Config(OdinV1065Config):
    """Configuration for the ODIN v10.66 hybrid engine.

    Extends the v10.65 configuration with additional
    parameters controlling HINT integration and high‑risk
    adjustments.  All weights are expressed on the logit scale
    (except the ensemble weights, which are probabilities).
    """
    # Ensemble weights
    odin_weight: float = 0.85
    hint_weight: float = 0.15

    # High‑risk therapeutic area penalties/boosts
    high_risk_ta_penalty: float = -0.50
    mod_risk_ta_penalty: float = -0.20
    low_risk_ta_boost: float = 0.20

    # High‑risk indication penalty (e.g. postoperative pain)
    high_indication_penalty: float = -0.70

    # Novice sponsor (<3 approvals) in a high‑risk TA
    novice_high_ta_penalty: float = -0.40

    # TA × modality interaction weights
    ta_modality_interactions: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("Pain Management", "Small Molecule"): -0.10,
        ("Hematology", "Small Molecule"): -0.10,
        ("Metabolic/Endocrine", "Small Molecule"): -0.20,
        ("Ophthalmology", "Antibody"): 0.10,
        ("Other", "Cell/Gene Therapy"): -0.20,
        ("Oncology", "Antibody"): 0.10,
        ("Infectious Disease", "Vaccine"): 0.30,
    })

    # High‑risk indication patterns and approximate CRL rates
    high_risk_indications: Dict[str, float] = field(default_factory=lambda: {
        "postoperative pain following bunionectomy surgery": 1.00,
        "postoperative pain": 0.80,
        "inflammatory diseases": 0.75,
        "parkinson's disease": 0.50,
        "major depressive disorder": 0.40,
        "chronic spontaneous urticaria": 0.40,
        "migraine": 0.40,
        "dry eye disease": 0.33,
        "hypercholesterolemia": 0.33,
        "schizophrenia": 0.29,
    })

    # Historical TA CRL rates (used for HINT component)
    hint_ta_crl_rates: Dict[str, float] = field(default_factory=lambda: {
        "Pain Management": 0.419,
        "Hematology": 0.357,
        "Nephrology": 0.310,
        "Ophthalmology": 0.265,
        "CNS/Neurology": 0.232,
        "Cardiovascular": 0.214,
        "Metabolic/Endocrine": 0.200,
        "Rare Disease": 0.176,
        "Other": 0.152,
        "Immunology": 0.118,
        "Dermatology": 0.105,
        "Psychiatry": 0.100,
        "Oncology": 0.072,
        "GI/Hepatology": 0.067,
        "Respiratory": 0.043,
        "Infectious Disease": 0.030,
        "Women's Health": 0.000,
        "Vaccines": 0.000,
    })

    # TA × modality adjustments used in HINT CRL calculation (fractional CRL shifts)
    hint_ta_modality_interactions: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("Pain Management", "Small Molecule"): 0.014,
        ("Hematology", "Small Molecule"): 0.027,
        ("Metabolic/Endocrine", "Small Molecule"): 0.078,
        ("Ophthalmology", "Antibody"): 0.035,
        ("Other", "Cell/Gene Therapy"): 0.048,
        ("Oncology", "Antibody"): -0.020,
        ("Infectious Disease", "Vaccine"): -0.030,
    })

    # Sponsor × TA interaction CRL rates
    hint_sponsor_ta_interactions: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("novice", "Pain Management"): 0.433,
        ("novice", "Nephrology"): 0.421,
        ("novice", "Hematology"): 0.357,
        ("novice", "CNS/Neurology"): 0.292,
        ("novice", "Ophthalmology"): 0.286,
        ("novice", "Cardiovascular"): 0.235,
        ("novice", "Rare Disease"): 0.233,
        ("novice", "Immunology"): 0.231,
        ("expert", "Ophthalmology"): 0.231,
        ("expert", "Metabolic/Endocrine"): 0.200,
    })

    # Era adjustments for HINT CRL (additive to CRL)
    hint_era_adjustments: Dict[str, float] = field(default_factory=lambda: {
        "pre_2015": 0.05,
        "2015_2019": 0.02,
        "2020_plus": 0.00,
    })

    # Weights for HINT adjustments (can be tuned)
    hint_era_weight: float = 1.0
    hint_modality_weight: float = 0.5


def _compute_hint_prob(event: Mapping[str, Any], cfg: OdinV1066Config) -> float:
    """Compute the HINT‑style approval probability for an event.

    This function mirrors the hierarchical logic of the HINT engine
    described in `odin_hint_engine.py` but uses a simplified
    implementation.  It returns the probability of approval
    (`1 - CRL`) after applying therapeutic area, modality,
    sponsor and era adjustments.  Missing values fall back to
    reasonable defaults.
    """
    # Extract event fields as strings/lowercase
    indication = str(event.get("indication", "") or "").lower()
    ta = str(event.get("therapeutic_area", "Other") or "Other")
    modality = str(event.get("modality", "Small Molecule") or "Small Molecule")
    year = 0
    try:
        year = int(float(event.get("year", 0) or 0))
    except Exception:
        year = 0
    prior_approvals = _to_int(event.get("sponsor_prior_approvals"), default=0)
    # Determine sponsor tier for HINT
    if prior_approvals >= 5:
        sponsor_tier = "expert"
    elif prior_approvals >= 3:
        sponsor_tier = "mid"
    else:
        sponsor_tier = "novice"
    # Level 1: specific high‑risk indication override
    for pattern, crl_rate in cfg.high_risk_indications.items():
        if pattern in indication:
            final_crl = crl_rate
            break
    else:
        final_crl = None
    # Level 2: sponsor × TA interaction (if not overridden)
    if final_crl is None:
        key = (sponsor_tier, ta)
        if key in cfg.hint_sponsor_ta_interactions:
            final_crl = cfg.hint_sponsor_ta_interactions[key]
    # Base TA rate
    base_crl = cfg.hint_ta_crl_rates.get(ta, 0.133)
    # TA × modality adjustment
    ta_mod_key = (ta, modality)
    ta_mod_adj = cfg.hint_ta_modality_interactions.get(ta_mod_key, 0.0)
    # If final_crl still None, compute from base + interaction
    if final_crl is None:
        final_crl = base_crl + ta_mod_adj * cfg.hint_modality_weight
    # Era adjustment
    if year < 2015:
        era_adj = cfg.hint_era_adjustments["pre_2015"]
    elif year < 2020:
        era_adj = cfg.hint_era_adjustments["2015_2019"]
    else:
        era_adj = cfg.hint_era_adjustments["2020_plus"]
    final_crl += era_adj * cfg.hint_era_weight
    # Clamp CRL to [0.01, 0.99]
    final_crl = max(0.01, min(0.99, final_crl))
    return 1.0 - final_crl


def score_pdufa_event(
    event: Mapping[str, Any],
    config: Optional[OdinV1066Config] = None
) -> Dict[str, Any]:
    """Compute the ODIN/HINT hybrid score for a PDUFA event.

    The function replicates the v10.65 ODIN logit calculation,
    applies additional high‑risk adjustments, computes a HINT
    approval probability, and returns a weighted combination of
    the two.  The returned dictionary includes the blended
    probability, the tier classification, the recommended action
    and a breakdown of contributing factors for transparency.
    """
    cfg = config or OdinV1066Config()
    # Start with base logit
    logit = cfg.base_logit
    breakdown: Dict[str, float] = {"Base": cfg.base_logit}
    # --- CRL & resubmission (same as v10.65) ---
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
    sp = _to_int(event.get("sponsor_prior_approvals"), default=-1)
    if sp == 0:
        logit += cfg.sponsor_zero_penalty
        breakdown["Sponsor_0"] = cfg.sponsor_zero_penalty
    elif 1 <= sp < 5:
        logit += cfg.sponsor_1_4_boost
        breakdown["Sponsor_1_4"] = cfg.sponsor_1_4_boost
    elif 5 <= sp <= 10:
        logit += cfg.sponsor_5_10_boost
        breakdown["Sponsor_5_10"] = cfg.sponsor_5_10_boost
    elif sp > 10:
        logit += cfg.sponsor_gt10_boost
        breakdown["Sponsor_gt10"] = cfg.sponsor_gt10_boost
    elif sp >= 5:
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
        if vote is not None and vote > 1.0:
            vote /= 100.0
        if vote is not None and vote >= 0.65:
            logit += cfg.adcom_high_boost
            breakdown["AdCom_High"] = cfg.adcom_high_boost
        elif vote is not None and vote >= 0.50:
            logit += cfg.adcom_mid_penalty
            breakdown["AdCom_Mid"] = cfg.adcom_mid_penalty
        elif vote is not None:
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
    # --- Designation stack boost ---
    des_count = _to_int(event.get("designation_stack_count"), default=0)
    if des_count >= 2:
        logit += cfg.des_count_ge2_boost
        breakdown["Des_ge2"] = cfg.des_count_ge2_boost
    # --- Sponsor × designation synergy ---
    if sp >= 5 and des_count >= 2:
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
    # --- Infectious synergies ---
    is_infectious = ta in {"Infectious Disease", "Infectious"}
    if is_infectious and des_count >= 2:
        logit += cfg.infectious_des2_boost
        breakdown["Infectious_Des2"] = cfg.infectious_des2_boost
    if is_infectious and _to_bool(event.get("btd")):
        logit += cfg.infectious_btd_boost
        breakdown["Infectious_BTD"] = cfg.infectious_btd_boost
    # --- Residual TA adjustments (negative classes) ---
    ta_factor = cfg.TA_ADJUSTMENTS.get(ta, 0.0)
    if ta_factor != 0.0:
        delta = ta_factor * cfg.ta_adjustment_weight
        logit += delta
        breakdown["TA_Adjust"] = delta
    # --- Additional high‑risk adjustments (new in v10.66) ---
    # Determine risk tier of TA
    high_risk_tas = ["Pain Management", "Hematology", "Nephrology", "Ophthalmology"]
    mod_risk_tas = ["CNS/Neurology", "Cardiovascular", "Metabolic/Endocrine", "Rare Disease", "Other"]
    low_risk_tas = ["Immunology", "Dermatology", "Psychiatry", "Oncology", "GI/Hepatology", "Respiratory", "Infectious Disease", "Women's Health", "Vaccines"]
    # High‑risk TA penalty or boost
    if ta in high_risk_tas:
        logit += cfg.high_risk_ta_penalty
        breakdown["HighRisk_TA"] = cfg.high_risk_ta_penalty
    elif ta in mod_risk_tas:
        logit += cfg.mod_risk_ta_penalty
        breakdown["ModRisk_TA"] = cfg.mod_risk_ta_penalty
    elif ta in low_risk_tas:
        logit += cfg.low_risk_ta_boost
        breakdown["LowRisk_TA"] = cfg.low_risk_ta_boost
    # High‑risk indication penalty
    indication = str(event.get("indication") or "").lower()
    for pattern in cfg.high_risk_indications.keys():
        if pattern in indication:
            logit += cfg.high_indication_penalty
            breakdown["HighRisk_Indication"] = cfg.high_indication_penalty
            break
    # Novice sponsor (<3) in high‑risk TA penalty
    if sp >= 0 and sp < 3 and ta in high_risk_tas:
        logit += cfg.novice_high_ta_penalty
        breakdown["Novice_HighTA"] = cfg.novice_high_ta_penalty
    # TA × modality interactions
    mod_key = None
    if "cell" in mod or "gene" in mod:
        mod_key = "Cell/Gene Therapy"
    elif "vaccine" in mod:
        mod_key = "Vaccine"
    elif "antibody" in mod:
        mod_key = "Antibody"
    else:
        # assume small molecule for everything else
        mod_key = "Small Molecule"
    interaction_key = (ta, mod_key)
    if interaction_key in cfg.ta_modality_interactions:
        delta = cfg.ta_modality_interactions[interaction_key]
        logit += delta
        breakdown[f"TAxMod_{ta}_{mod_key}"] = delta
    # --- Compute ODIN probability after adjustments ---
    odin_prob = _sigmoid(logit)
    # --- Compute HINT probability ---
    hint_prob = _compute_hint_prob(event, cfg)
    # --- Blend ODIN and HINT probabilities ---
    final_prob = cfg.odin_weight * odin_prob + cfg.hint_weight * hint_prob
    # --- Tier classification ---
    if final_prob >= cfg.tier1_threshold:
        tier = "TIER_1"
    elif final_prob >= cfg.tier2_threshold:
        tier = "TIER_2"
    elif final_prob >= cfg.tier3_threshold:
        tier = "TIER_3"
    else:
        tier = "TIER_4"
    # --- Action guidance ---
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
        "probability": round(final_prob, 4),
        "tier": tier,
        "action": action,
        "odin_prob": round(odin_prob, 4),
        "hint_prob": round(hint_prob, 4),
        "logit": round(logit, 4),
        "breakdown": {k: round(v, 4) for k, v in breakdown.items()},
    }


__all__ = ["OdinV1066Config", "score_pdufa_event"]