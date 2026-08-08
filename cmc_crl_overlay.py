# -*- coding: utf-8 -*-
"""
CMC-CRL Resubmission Overlay v1.0  (9realms / ODIN companion)
=============================================================
Re-anchors ODIN PDUFA probabilities for RESUBMISSION events whose prior CRL was
CMC/manufacturing-ONLY (no efficacy/safety/clinical deficiency).

WHY THIS OVERLAY EXISTS
-----------------------
ODIN's core model over-penalizes a clean CMC-only resubmission for two structural
reasons we proved empirically:
  1. It lumps "naive + CMC CRL" together with "naive + efficacy CRL." But a CMC CRL
     is a FACTORY fix (no new trial), while an efficacy CRL requires a successful
     re-trial. They are not the same bet — yet ODIN's resub_class_2 feature applies
     only a small generic adjustment and does not neutralize the naive penalty.
  2. The core model CANNOT learn the right number by re-fitting: in the training
     data, naive and CMC-resubmission are near-collinear (72 naive CMC-resubs, 0
     experienced) and the prior_crl flag marks the CRL event itself (cell shows 0%
     approval), so a re-fit interaction is unidentifiable. An overlay is the correct
     engineering pattern (same as Smart Money / Conference / UOA overlays).

EMPIRICAL BASIS (auditable)
---------------------------
  - openFDA + BioPharmaCatalyst CMC/facility CRL cohort, resolved cases:
        ~90% eventually approved overall; naive sponsors 83% (5/6); experienced 100% (8/8).
        (cosibelimab, Pedmark, ROLVEDON, YCANTH, SIMLANDI, SELARSDI, Omvoh, etc.)
  - REAL naive-sponsor FIRST-CYCLE approval rate 2020-present: ~74% (our BPC cohort,
        n=273) — statistically indistinguishable from experienced sponsors
        (Amin et al., Clin Pharmacol Ther 2025; FDA CDER first-cycle 74-92% 2020-24).
  - ODIN experienced-sponsor counterfactual for UNCY: 57%.
  - ODIN core (v19 honest) for UNCY naive: 32%  <-- the number this overlay corrects.

CALIBRATION
-----------
  adjusted = (1 - W) * odin_p + W * CMC_BASE
     CMC_BASE = 0.72  (clean CMC-only resubmission base rate, conservatively below the
                       selection-biased 83% and near the real naive first-cycle 74%)
     W        = 0.60  (weight toward the empirical base rate for a clean CMC-only case)
  modifiers:
     - sponsor_naive            : -0.05  (small execution-risk haircut)
     - new_facility_verified    : +0.07  (remediation done / new vendor passed-or-clean record)
     - double_crl (same issue)  : -0.10  (the tab-cel/Atara failure pattern)
  clipped to [0.05, 0.95].

T-1 COMPLIANCE
--------------
All inputs are PUBLIC pre-decision facts: CRL reason (CMC vs efficacy, from the
FDA CRL letter), resubmission status, sponsor approval history, and facility-
remediation status (company disclosure). No outcome encoding.

INTEGRATION
-----------
Wire into mcp_9realms_vnext.py as a tool `cmc_crl_score` (mirrors smart_money_score):
    from cmc_crl_overlay import cmc_crl_overlay
    res = cmc_crl_overlay(odin_probability=0.318, is_resubmission=True, cmc_only=True,
                          has_efficacy_or_safety_deficiency=False, sponsor_naive=True,
                          new_facility_verified=True)
Apply AFTER odin_score / odin_score_honest. Only fires for CMC-only resubmissions;
returns the ODIN probability unchanged for every other event type.
"""

VERSION = "CMC-CRL Overlay v1.0"
CMC_BASE = 0.72
W = 0.60
NAIVE_HAIRCUT = 0.05
FACILITY_VERIFIED_BONUS = 0.07
DOUBLE_CRL_PENALTY = 0.10


def _tier(p):
    if p >= 0.85:
        return "T1", "Strong Long"
    if p >= 0.65:
        return "T2", "Cautious Long"
    if p >= 0.40:
        return "T3", "Monitor"
    return "T4", "No Trade"


def cmc_crl_overlay(odin_probability,
                    is_resubmission=False,
                    cmc_only=False,
                    has_efficacy_or_safety_deficiency=False,
                    sponsor_naive=True,
                    new_facility_verified=False,
                    double_crl=False,
                    ticker=None):
    """Return ODIN probability re-anchored for clean CMC-only resubmissions.

    Parameters
    ----------
    odin_probability : float   ODIN core probability (0-1), from odin_score_honest.
    is_resubmission  : bool     This PDUFA is a resubmission after a prior CRL.
    cmc_only         : bool     The prior CRL was CMC/manufacturing/facility related.
    has_efficacy_or_safety_deficiency : bool  Prior CRL also cited efficacy/safety/clinical.
    sponsor_naive    : bool     Sponsor has no prior FDA approval.
    new_facility_verified : bool  Remediation complete / switched to a vendor with a
                                   clean inspection record (de-risks the lone failure mode).
    double_crl       : bool     A *second* CRL on the same manufacturing issue (tab-cel pattern).
    ticker           : str      Optional, for labeling.
    """
    flags = []
    eligible = bool(is_resubmission and cmc_only and not has_efficacy_or_safety_deficiency)
    if not eligible:
        tier, action = _tier(odin_probability)
        return {
            "version": VERSION, "ticker": ticker,
            "odin_probability": round(odin_probability, 3),
            "adjusted_probability": round(odin_probability, 3),
            "delta": 0.0, "tier": tier, "action": action,
            "applied": False, "flags": [],
            "rationale": "Not a clean CMC-only resubmission - ODIN probability unchanged.",
            "disclaimer": "Informational/educational only. Not investment advice.",
        }

    adj = (1 - W) * odin_probability + W * CMC_BASE
    flags.append("CMC_ONLY_RESUBMISSION")
    if sponsor_naive:
        adj -= NAIVE_HAIRCUT
        flags.append("NAIVE_EXEC_HAIRCUT")
    if new_facility_verified:
        adj += FACILITY_VERIFIED_BONUS
        flags.append("FACILITY_REMEDIATION_VERIFIED")
    if double_crl:
        adj -= DOUBLE_CRL_PENALTY
        flags.append("DOUBLE_CRL_PENALTY")
    adj = max(0.05, min(0.95, adj))
    tier, action = _tier(adj)
    return {
        "version": VERSION, "ticker": ticker,
        "odin_probability": round(odin_probability, 3),
        "adjusted_probability": round(adj, 3),
        "delta": round(adj - odin_probability, 3),
        "tier": tier, "action": action,
        "applied": True, "flags": flags,
        "calibration": {"cmc_base": CMC_BASE, "weight": W,
                        "naive_haircut": NAIVE_HAIRCUT,
                        "facility_verified_bonus": FACILITY_VERIFIED_BONUS,
                        "double_crl_penalty": DOUBLE_CRL_PENALTY},
        "rationale": ("Clean CMC-only resubmission: ODIN over-penalizes (naive+CMC "
                      "collinear, training cell CRL-enriched). Re-anchored toward the "
                      "empirical CMC-resolution base rate (~72%), with modifiers."),
        "empirical_anchors": {"naive_cmc_cohort_resolved": 0.83,
                              "real_naive_first_cycle": 0.74,
                              "experienced_counterfactual": 0.57,
                              "odin_core": odin_probability},
        "disclaimer": "Informational/educational only. Not investment advice.",
    }


if __name__ == "__main__":
    import json
    print(VERSION + " - self-test\n")
    cases = [
        ("UNCY (naive, CMC-only, new vendor verified)",
         dict(odin_probability=0.318, is_resubmission=True, cmc_only=True,
              has_efficacy_or_safety_deficiency=False, sponsor_naive=True,
              new_facility_verified=True, ticker="UNCY")),
        ("UNCY (naive, CMC-only, remediation NOT yet verified)",
         dict(odin_probability=0.318, is_resubmission=True, cmc_only=True,
              sponsor_naive=True, new_facility_verified=False, ticker="UNCY")),
        ("Experienced + CMC-only (e.g., big-pharma facility CRL)",
         dict(odin_probability=0.55, is_resubmission=True, cmc_only=True,
              sponsor_naive=False, new_facility_verified=True)),
        ("Double CMC CRL (tab-cel pattern)",
         dict(odin_probability=0.40, is_resubmission=True, cmc_only=True,
              sponsor_naive=True, double_crl=True)),
        ("Efficacy CRL (NOT eligible - unchanged)",
         dict(odin_probability=0.30, is_resubmission=True, cmc_only=False,
              has_efficacy_or_safety_deficiency=True, sponsor_naive=True)),
        ("First-cycle (NOT a resubmission - unchanged)",
         dict(odin_probability=0.82, is_resubmission=False, cmc_only=False)),
    ]
    for label, kw in cases:
        r = cmc_crl_overlay(**kw)
        print(f"{label}\n  ODIN {r['odin_probability']:.0%} -> adj {r['adjusted_probability']:.0%} "
              f"({r['tier']}, delta {r['delta']:+.0%}) flags={r['flags']}\n")
