#!/usr/bin/env python3
"""
ODIN v12.51 CORNERSTONE — FDA PDUFA Approval Probability Scorer
Champion config: WF Brier 0.08880, WF AUC 0.9082, Val AUC 0.9190
Selected from 267 honing iterations (v1083→v1349), engine v5.2.0

Usage:
    from odin_v1251_scorer import OdinScorer
    scorer = OdinScorer()
    result = scorer.score(signals)
    scorer.print_scorecard(result)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

__version__ = "12.51"
__codename__ = "CORNERSTONE"

# ═══════════════════════════════════════════════════════════════════════════
# v1251 CHAMPION WEIGHTS (walk-forward validated, DO NOT MODIFY)
# ═══════════════════════════════════════════════════════════════════════════

W = {
    # Base
    "base_logit": 1.6877965449124204,

    # Penalties (negative values, subtracted from logit)
    "snda_base_penalty": -3.0,
    "snda_pediatric_base_penalty": -0.06800629686518996,
    "prior_crl_penalty": -3.8551249937004815,
    "inexperienced_sponsor_penalty": -0.9877390491325875,
    "manufacturing_risk_penalty": -1e-06,
    "form_483_penalty": -1.0032841165652016,
    "ema_cmc_flag_penalty": -1.7637221258168696,
    "cmc_extension_penalty": -1.2804336072183253,
    "adcom_mid_penalty": -0.4388235981850125,
    "adcom_low_penalty": -1e-06,
    "s22_pediatric_pk_penalty": -1.742907536222042,
    "indication_pain_penalty": -0.10000000149011612,
    "novice_sponsor_high_risk_ta_penalty": -0.30000001192092896,
    "gene_therapy_penalty": -0.8653127123308743,
    "single_arm_study_penalty": -3.5955999549937543,
    "surrogate_endpoint_penalty": -0.2574345660486174,
    "prior_crl_count_penalty": -0.7014723992715777,
    "safety_severity_penalty": -0.15358569077830592,
    "ppm_penalty": -3.799999952316284,
    "eu_approved_2026_penalty": -0.17461282956209842,
    "psychedelics_penalty": -1e-06,
    "hoeg_era_constant": -0.10000000149011612,
    "accel_approval_2025plus_penalty": -1.045293387445537,
    "experienced_sponsor_2026_reduction": -1.389068962125728,
    "double_crl_penalty": -1e-06,
    "class1_resubmission_boost": -1.3777807269584754,

    # Boosts (positive values, added to logit)
    "btd_weight": 0.20790020747697294,
    "orphan_weight": 0.03999999910593033,
    "priority_review_weight": 2.5256676705876178,
    "fast_track_weight": 1.1936271681297903,
    "accelerated_approval_weight": 0.3895689176206382,
    "experienced_sponsor_boost": 1.2455899836706399,
    "adcom_high_boost": 3.2669080748307007,
    "eu_approved_boost": 0.2916146425428995,
    "btd_oncology_boost": 2.1105462377523563,
    "ta_very_high_boost": 1.2788227468655247,

    # TA weights
    "ta_adjustment_weight": -0.05641338337930061,
    "ta_high_risk_penalty": -0.9626554744429417,
    "ta_mod_risk_penalty": -0.5079140606058509,
    "ta_low_risk_boost": -1.86914877334142,
    "indication_onc_boost": -0.9253040106386666,

    # Signal weights
    "s23_insider_weight": 0.5861676961239876,
    "s6_hiring_weight": 0.9371508494347254,
    "social_weight": 0.12445292250731003,

    # HINT ensemble
    "odin_weight": 0.7520477981855773,
    "hint_weight": 0.6684420832053102,
    "hint_crl_rate_penalty": -0.2005418595851598,

    # Interaction terms
    "ix_prior_crl_x_mfg_risk": -0.25764701477541224,
    "ix_prior_crl_x_form483": -0.48206294901375923,
    "ix_gene_therapy_x_mfg_risk": -0.15000000596046448,
    "ix_inexperienced_x_mfg_risk": -3.0,
    "ix_single_arm_x_surrogate": 2.801338275288041,
    "ix_btd_x_single_arm": 1.7816286536277133,
}

# Platt calibration (fitted on training data)
PLATT_A = -0.026989505605139973
PLATT_B = 0.5827207756734252

# Tier thresholds
TIERS = {
    1: {"min": 0.85, "action": "LONG",          "sizing": "FULL",    "exit": "T-5"},
    2: {"min": 0.65, "action": "CAUTIOUS LONG",  "sizing": "HALF",    "exit": "T-7"},
    3: {"min": 0.40, "action": "MONITOR",         "sizing": "QUARTER", "exit": "T-7"},
    4: {"min": 0.00, "action": "NO TRADE",        "sizing": "ZERO",    "exit": "N/A"},
}

# TA risk classification
TA_RISK = {
    "VERY_HIGH_APPROVAL": ["vaccines", "womens_health"],
    "LOW_RISK": ["immunology", "dermatology", "oncology", "gi_hepatology",
                 "respiratory", "infectious", "anti_infective"],
    "MOD_RISK": ["cns", "neurology", "cardiovascular", "metabolic",
                 "rare_disease", "endocrine", "other"],
    "HIGH_RISK": ["pain", "ophthalmology", "nephrology", "hematology",
                  "psychiatry"],
}

# Hard override signals → force TIER 4
AVOID_SIGNALS = [
    "ppm_flag", "gene_therapy_cmc", "ema_cmc_flag",
    "hiring_void_nda", "pediatric_no_pk", "cmc_extension_active",
    "insider_critical_sell",
]


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ez = math.exp(x)
        return ez / (1.0 + ez)


def _classify_ta_risk(ta: str) -> str:
    """Classify therapeutic area into risk tier."""
    ta_lower = ta.lower().replace(" ", "_").replace("-", "_")
    for tier, areas in TA_RISK.items():
        if ta_lower in areas:
            return tier
    # Fuzzy match
    if any(k in ta_lower for k in ["pain", "analges"]):
        return "HIGH_RISK"
    if any(k in ta_lower for k in ["onc", "cancer", "tumor"]):
        return "LOW_RISK"
    if any(k in ta_lower for k in ["cns", "neuro", "alzh", "parkin"]):
        return "MOD_RISK"
    if any(k in ta_lower for k in ["vaccin"]):
        return "VERY_HIGH_APPROVAL"
    return "MOD_RISK"


@dataclass
class OdinSignals:
    """All input signals for ODIN scoring."""
    # Regulatory designations
    btd: bool = False
    orphan: bool = False
    priority_review: bool = False
    fast_track: bool = False
    accelerated_approval: bool = False

    # Sponsor
    experienced_sponsor: bool = False       # ≥5 prior approvals
    inexperienced_sponsor: bool = False     # 0 prior approvals
    sponsor_approvals: int = 0

    # Application type
    is_snda: bool = False                   # Supplemental NDA/BLA
    is_snda_pediatric: bool = False
    is_class1_resubmission: bool = False

    # Trial design
    single_arm: bool = False
    surrogate_endpoint: bool = False

    # History
    prior_crl: bool = False
    prior_crl_count: int = 0
    double_crl: bool = False                # ≥2 prior CRLs

    # Manufacturing / CMC
    manufacturing_risk: bool = False
    form_483: bool = False
    ema_cmc_flag: bool = False
    cmc_extension: bool = False

    # AdCom
    adcom_high: bool = False                # Vote ≥65%
    adcom_mid: bool = False                 # Vote 50-65%
    adcom_low: bool = False                 # Vote <50%

    # Safety
    safety_severity: float = 0.0            # 0-1 scale
    ppm_flag: bool = False                  # Primary pivotal miss

    # Therapeutic area
    therapeutic_area: str = "other"
    is_oncology: bool = False
    is_gene_therapy: bool = False
    is_psychedelic: bool = False
    is_pain: bool = False

    # Temporal
    is_hoeg_era: bool = True                # Default True for 2025+
    pdufa_year: int = 2026

    # EU
    eu_approved: bool = False

    # Pediatric
    pediatric_no_pk: bool = False

    # MCP-derived signals
    insider_signal: float = 0.0             # -1 to +1 (bearish to bullish)
    hiring_signal: float = 0.0              # 0 to 1
    social_signal: float = 0.0              # -1 to +1

    # HINT
    historical_crl_rate: Optional[float] = None  # 0-1, CRL rate for indication

    # Avoid overrides
    avoid_override: bool = False


class OdinScorer:
    """ODIN v12.51 CORNERSTONE production scorer."""

    def __init__(self):
        self.version = __version__
        self.weights = W

    def score(self, s: OdinSignals) -> Dict[str, Any]:
        """Score a PDUFA catalyst. Returns full scorecard dict."""

        # Check avoid signals first
        avoid_reasons = []
        if s.ppm_flag: avoid_reasons.append("PPM_FLAG: Primary pivotal miss")
        if s.is_gene_therapy and s.manufacturing_risk:
            avoid_reasons.append("GENE_THERAPY_CMC: Gene therapy + CMC risk")
        if s.ema_cmc_flag: avoid_reasons.append("EMA_CMC_FLAG: EMA manufacturing concern")
        if s.hiring_signal < -0.5: avoid_reasons.append("HIRING_VOID: No NDA-stage hiring")
        if s.pediatric_no_pk: avoid_reasons.append("PEDIATRIC_NO_PK: No PK bridging data")
        if s.cmc_extension: avoid_reasons.append("CMC_EXTENSION: PDUFA extended for CMC")
        if s.insider_signal < -0.8: avoid_reasons.append("INSIDER_CRITICAL: Heavy insider selling")
        if s.avoid_override: avoid_reasons.append("MANUAL_OVERRIDE: Forced avoid")

        # ─── Step 1: Base logit ───
        logit = W["base_logit"]
        contributions = [("base_logit", W["base_logit"])]

        # ─── Step 2: Penalties ───
        if s.is_snda:
            logit += W["snda_base_penalty"]
            contributions.append(("snda_base_penalty", W["snda_base_penalty"]))
        if s.is_snda_pediatric:
            logit += W["snda_pediatric_base_penalty"]
            contributions.append(("snda_pediatric_base_penalty", W["snda_pediatric_base_penalty"]))
        if s.prior_crl:
            logit += W["prior_crl_penalty"]
            contributions.append(("prior_crl_penalty", W["prior_crl_penalty"]))
        if s.prior_crl_count > 1:
            extra = (s.prior_crl_count - 1) * W["prior_crl_count_penalty"]
            logit += extra
            contributions.append(("prior_crl_count_penalty", extra))
        if s.double_crl:
            logit += W["double_crl_penalty"]
            contributions.append(("double_crl_penalty", W["double_crl_penalty"]))
        if s.inexperienced_sponsor:
            logit += W["inexperienced_sponsor_penalty"]
            contributions.append(("inexperienced_sponsor_penalty", W["inexperienced_sponsor_penalty"]))
        if s.manufacturing_risk:
            logit += W["manufacturing_risk_penalty"]
            contributions.append(("manufacturing_risk_penalty", W["manufacturing_risk_penalty"]))
        if s.form_483:
            logit += W["form_483_penalty"]
            contributions.append(("form_483_penalty", W["form_483_penalty"]))
        if s.ema_cmc_flag:
            logit += W["ema_cmc_flag_penalty"]
            contributions.append(("ema_cmc_flag_penalty", W["ema_cmc_flag_penalty"]))
        if s.cmc_extension:
            logit += W["cmc_extension_penalty"]
            contributions.append(("cmc_extension_penalty", W["cmc_extension_penalty"]))
        if s.adcom_mid:
            logit += W["adcom_mid_penalty"]
            contributions.append(("adcom_mid_penalty", W["adcom_mid_penalty"]))
        if s.adcom_low:
            logit += W["adcom_low_penalty"]
            contributions.append(("adcom_low_penalty", W["adcom_low_penalty"]))
        if s.pediatric_no_pk:
            logit += W["s22_pediatric_pk_penalty"]
            contributions.append(("s22_pediatric_pk_penalty", W["s22_pediatric_pk_penalty"]))
        if s.is_gene_therapy:
            logit += W["gene_therapy_penalty"]
            contributions.append(("gene_therapy_penalty", W["gene_therapy_penalty"]))
        if s.single_arm:
            logit += W["single_arm_study_penalty"]
            contributions.append(("single_arm_study_penalty", W["single_arm_study_penalty"]))
        if s.surrogate_endpoint:
            logit += W["surrogate_endpoint_penalty"]
            contributions.append(("surrogate_endpoint_penalty", W["surrogate_endpoint_penalty"]))
        if s.safety_severity > 0:
            pen = s.safety_severity * W["safety_severity_penalty"]
            logit += pen
            contributions.append(("safety_severity_penalty", pen))
        if s.ppm_flag:
            logit += W["ppm_penalty"]
            contributions.append(("ppm_penalty", W["ppm_penalty"]))
        if s.is_psychedelic:
            logit += W["psychedelics_penalty"]
            contributions.append(("psychedelics_penalty", W["psychedelics_penalty"]))
        if s.is_class1_resubmission:
            logit += W["class1_resubmission_boost"]
            contributions.append(("class1_resubmission_boost", W["class1_resubmission_boost"]))

        # Temporal
        if s.is_hoeg_era:
            logit += W["hoeg_era_constant"]
            contributions.append(("hoeg_era_constant", W["hoeg_era_constant"]))
        if s.accelerated_approval and s.pdufa_year >= 2025:
            logit += W["accel_approval_2025plus_penalty"]
            contributions.append(("accel_approval_2025plus_penalty", W["accel_approval_2025plus_penalty"]))
        if s.experienced_sponsor and s.pdufa_year >= 2026:
            logit += W["experienced_sponsor_2026_reduction"]
            contributions.append(("experienced_sponsor_2026_reduction", W["experienced_sponsor_2026_reduction"]))
        if s.eu_approved and s.pdufa_year >= 2026:
            logit += W["eu_approved_2026_penalty"]
            contributions.append(("eu_approved_2026_penalty", W["eu_approved_2026_penalty"]))

        # TA penalties
        ta_risk = _classify_ta_risk(s.therapeutic_area)
        if ta_risk == "HIGH_RISK":
            logit += W["ta_high_risk_penalty"]
            contributions.append(("ta_high_risk_penalty", W["ta_high_risk_penalty"]))
        elif ta_risk == "MOD_RISK":
            logit += W["ta_mod_risk_penalty"]
            contributions.append(("ta_mod_risk_penalty", W["ta_mod_risk_penalty"]))
        if s.is_pain:
            logit += W["indication_pain_penalty"]
            contributions.append(("indication_pain_penalty", W["indication_pain_penalty"]))
        if s.is_oncology:
            logit += W["indication_onc_boost"]
            contributions.append(("indication_onc_boost", W["indication_onc_boost"]))
        if s.inexperienced_sponsor and ta_risk == "HIGH_RISK":
            logit += W["novice_sponsor_high_risk_ta_penalty"]
            contributions.append(("novice_sponsor_high_risk_ta_penalty", W["novice_sponsor_high_risk_ta_penalty"]))

        # ─── Step 3: Boosts ───
        if s.btd:
            logit += W["btd_weight"]
            contributions.append(("btd_weight", W["btd_weight"]))
        if s.orphan:
            logit += W["orphan_weight"]
            contributions.append(("orphan_weight", W["orphan_weight"]))
        if s.priority_review:
            logit += W["priority_review_weight"]
            contributions.append(("priority_review_weight", W["priority_review_weight"]))
        if s.fast_track:
            logit += W["fast_track_weight"]
            contributions.append(("fast_track_weight", W["fast_track_weight"]))
        if s.accelerated_approval:
            logit += W["accelerated_approval_weight"]
            contributions.append(("accelerated_approval_weight", W["accelerated_approval_weight"]))
        if s.experienced_sponsor:
            logit += W["experienced_sponsor_boost"]
            contributions.append(("experienced_sponsor_boost", W["experienced_sponsor_boost"]))
        if s.adcom_high:
            logit += W["adcom_high_boost"]
            contributions.append(("adcom_high_boost", W["adcom_high_boost"]))
        if s.eu_approved:
            logit += W["eu_approved_boost"]
            contributions.append(("eu_approved_boost", W["eu_approved_boost"]))
        if s.btd and s.is_oncology:
            logit += W["btd_oncology_boost"]
            contributions.append(("btd_oncology_boost", W["btd_oncology_boost"]))
        if ta_risk == "VERY_HIGH_APPROVAL":
            logit += W["ta_very_high_boost"]
            contributions.append(("ta_very_high_boost", W["ta_very_high_boost"]))

        # ─── Step 4: Signal weights ───
        if s.insider_signal != 0:
            sig = s.insider_signal * W["s23_insider_weight"]
            logit += sig
            contributions.append(("s23_insider", sig))
        if s.hiring_signal != 0:
            sig = s.hiring_signal * W["s6_hiring_weight"]
            logit += sig
            contributions.append(("s6_hiring", sig))
        if s.social_signal != 0:
            sig = s.social_signal * W["social_weight"]
            logit += sig
            contributions.append(("social", sig))

        # ─── Step 5: Interaction terms ───
        if s.prior_crl and s.manufacturing_risk:
            logit += W["ix_prior_crl_x_mfg_risk"]
            contributions.append(("ix_prior_crl_x_mfg_risk", W["ix_prior_crl_x_mfg_risk"]))
        if s.prior_crl and s.form_483:
            logit += W["ix_prior_crl_x_form483"]
            contributions.append(("ix_prior_crl_x_form483", W["ix_prior_crl_x_form483"]))
        if s.is_gene_therapy and s.manufacturing_risk:
            logit += W["ix_gene_therapy_x_mfg_risk"]
            contributions.append(("ix_gene_therapy_x_mfg_risk", W["ix_gene_therapy_x_mfg_risk"]))
        if s.inexperienced_sponsor and s.manufacturing_risk:
            logit += W["ix_inexperienced_x_mfg_risk"]
            contributions.append(("ix_inexperienced_x_mfg_risk", W["ix_inexperienced_x_mfg_risk"]))
        if s.single_arm and s.surrogate_endpoint:
            logit += W["ix_single_arm_x_surrogate"]
            contributions.append(("ix_single_arm_x_surrogate", W["ix_single_arm_x_surrogate"]))
        if s.btd and s.single_arm:
            logit += W["ix_btd_x_single_arm"]
            contributions.append(("ix_btd_x_single_arm", W["ix_btd_x_single_arm"]))

        # ─── Step 6: HINT blend (if available) ───
        odin_logit = logit
        hint_applied = False
        if s.historical_crl_rate is not None:
            hint_logit = W["base_logit"] + W["hint_crl_rate_penalty"] * s.historical_crl_rate
            logit = W["odin_weight"] * odin_logit + W["hint_weight"] * hint_logit
            hint_applied = True
            contributions.append(("hint_blend", logit - odin_logit))

        # ─── Step 7: Convert to probability ───
        raw_logit = logit
        p_raw = _sigmoid(logit)

        # Platt calibration (a=-0.027, b=0.583) was fitted on probabilities
        # in the honing engine. For MCP scoring we use raw sigmoid which
        # preserves the model's full discriminative range. The Platt params
        # are stored for reference but the raw probability is used for tiering.
        # To apply Platt: p_cal = sigmoid(PLATT_A * p_raw + PLATT_B)
        probability = p_raw

        # ─── Step 8: Tier classification ───
        if avoid_reasons:
            tier = 4
        elif probability >= TIERS[1]["min"]:
            tier = 1
        elif probability >= TIERS[2]["min"]:
            tier = 2
        elif probability >= TIERS[3]["min"]:
            tier = 3
        else:
            tier = 4

        tier_info = TIERS[tier]

        # Build positive signals list
        positive_signals = []
        if s.btd: positive_signals.append("✅ Breakthrough Therapy Designation")
        if s.priority_review: positive_signals.append("✅ Priority Review")
        if s.orphan: positive_signals.append("✅ Orphan Drug Designation")
        if s.fast_track: positive_signals.append("✅ Fast Track")
        if s.accelerated_approval: positive_signals.append("✅ Accelerated Approval")
        if s.experienced_sponsor: positive_signals.append("✅ Experienced Sponsor")
        if s.adcom_high: positive_signals.append("✅ Favorable AdCom (≥65%)")
        if s.eu_approved: positive_signals.append("✅ EU Approved")
        if s.btd and s.is_oncology: positive_signals.append("✅ BTD + Oncology (strong combo)")
        if s.insider_signal > 0.3: positive_signals.append("✅ Bullish Insider Activity")
        if s.hiring_signal > 0.5: positive_signals.append("✅ NDA-Stage Hiring Detected")

        # Build risk flags list
        risk_flags = []
        if s.prior_crl: risk_flags.append("🔴 Prior CRL")
        if s.ppm_flag: risk_flags.append("💀 Primary Pivotal Miss")
        if s.single_arm: risk_flags.append("🟡 Single-Arm Study")
        if s.is_gene_therapy: risk_flags.append("🟡 Gene Therapy CMC Risk")
        if s.form_483: risk_flags.append("🔴 Form 483 Findings")
        if s.ema_cmc_flag: risk_flags.append("🔴 EMA CMC Concern")
        if s.surrogate_endpoint: risk_flags.append("🟡 Surrogate Endpoint")
        if s.is_hoeg_era: risk_flags.append("⚡ Hoeg-Era FDA")
        if s.manufacturing_risk: risk_flags.append("🟡 Manufacturing Risk")
        if s.safety_severity > 0.5: risk_flags.append("🔴 Safety Signal")
        if s.inexperienced_sponsor: risk_flags.append("🟡 Inexperienced Sponsor")
        risk_flags.extend([f"🚫 AVOID: {r}" for r in avoid_reasons])

        # Sort contributions by magnitude
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        return {
            "version": self.version,
            "model": "v1251_champion_cornerstone",
            "probability": round(probability, 4),
            "tier": tier,
            "action": tier_info["action"],
            "sizing": tier_info["sizing"],
            "exit": tier_info["exit"],
            "ta_risk_tier": ta_risk,
            "raw_logit": round(raw_logit, 4),
            "p_raw": round(p_raw, 4),
            "hint_applied": hint_applied,
            "positive_signals": positive_signals,
            "risk_flags": risk_flags,
            "avoid_reasons": avoid_reasons,
            "contributions": contributions[:15],
            "wf_metrics": {"brier": 0.08880, "auc": 0.9082},
        }

    def print_scorecard(self, r: Dict, ticker: str = "", drug: str = "",
                        indication: str = "", pdufa_date: str = ""):
        """Pretty-print scorecard to stdout."""
        W = 72
        print(f"\n{'═'*W}")
        print(f"  ODIN v{self.version} CORNERSTONE — PDUFA SCORECARD")
        print(f"{'═'*W}")
        if ticker: print(f"  Ticker: {ticker:12s}  Drug: {drug}")
        if indication: print(f"  Indication: {indication:8s}  PDUFA: {pdufa_date}")

        print(f"\n  PROBABILITY: {r['probability']:.1%}")
        print(f"  Raw Logit:   {r['raw_logit']:.3f}")
        if r['hint_applied']:
            print(f"  HINT Blend:  Applied")

        tier_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}
        print(f"\n  ┌{'─'*46}┐")
        print(f"  │ {tier_emoji[r['tier']]} TIER {r['tier']:37d}│")
        print(f"  │  ACTION: {r['action']:35s}│")
        print(f"  │  SIZING: {r['sizing']:35s}│")
        print(f"  │  EXIT:   {r['exit']:35s}│")
        print(f"  │  TA RISK: {r['ta_risk_tier']:34s}│")
        print(f"  └{'─'*46}┘")

        if r['positive_signals']:
            print(f"\n  POSITIVE SIGNALS:")
            for s in r['positive_signals']:
                print(f"    {s}")

        if r['risk_flags']:
            print(f"\n  RISK FLAGS:")
            for f in r['risk_flags']:
                print(f"    {f}")

        if r['contributions']:
            print(f"\n  TOP CONTRIBUTIONS (logit-space):")
            for name, val in r['contributions'][:10]:
                arrow = '↑' if val > 0 else '↓'
                print(f"    {arrow} {name:>38s}: {val:+.3f}")

        print(f"\n  WF Validation: Brier={r['wf_metrics']['brier']:.5f}, AUC={r['wf_metrics']['auc']:.4f}")
        print(f"{'═'*W}")


# ═══════════════════════════════════════════════════════════════════════════
# DEMO / CLI
# ═══════════════════════════════════════════════════════════════════════════

def demo():
    """Run demo cases."""
    scorer = OdinScorer()

    # Case 1: Strong approval candidate
    print("\n" + "="*72)
    print("  DEMO CASE 1: Strong approval candidate (BTD + PR + Experienced)")
    s1 = OdinSignals(
        btd=True, priority_review=True, experienced_sponsor=True,
        therapeutic_area="oncology", is_oncology=True,
        is_hoeg_era=True, pdufa_year=2026,
    )
    r1 = scorer.score(s1)
    scorer.print_scorecard(r1, "ONCO", "oncodrug", "NSCLC", "2026-06-15")

    # Case 2: High risk — prior CRL + gene therapy
    print("\n" + "="*72)
    print("  DEMO CASE 2: High risk (Prior CRL + Gene Therapy + Mfg Risk)")
    s2 = OdinSignals(
        prior_crl=True, prior_crl_count=1,
        is_gene_therapy=True, manufacturing_risk=True,
        inexperienced_sponsor=True,
        therapeutic_area="rare_disease",
        is_hoeg_era=True, pdufa_year=2026,
    )
    r2 = scorer.score(s2)
    scorer.print_scorecard(r2, "GENE", "genetherapy", "Hemophilia B", "2026-09-01")

    # Case 3: PPM flag (forced TIER 4)
    print("\n" + "="*72)
    print("  DEMO CASE 3: PPM Flag (primary pivotal miss)")
    s3 = OdinSignals(
        ppm_flag=True, priority_review=True, btd=True,
        experienced_sponsor=True,
        therapeutic_area="cns",
        is_hoeg_era=True, pdufa_year=2026,
    )
    r3 = scorer.score(s3)
    scorer.print_scorecard(r3, "FAIL", "failamab", "Alzheimer's", "2026-04-20")

    # Case 4: Single-arm + BTD (interaction terms active)
    print("\n" + "="*72)
    print("  DEMO CASE 4: Single-arm + BTD + Surrogate (interaction offsets)")
    s4 = OdinSignals(
        btd=True, priority_review=True, orphan=True,
        single_arm=True, surrogate_endpoint=True,
        therapeutic_area="oncology", is_oncology=True,
        experienced_sponsor=True,
        is_hoeg_era=True, pdufa_year=2026,
    )
    r4 = scorer.score(s4)
    scorer.print_scorecard(r4, "RARE", "raredrug", "R/R DLBCL", "2026-07-10")

    # Summary
    print(f"\n{'═'*72}")
    print(f"  {'Case':>40s} {'Prob':>8s} {'Tier':>6s} {'Action':>15s}")
    print(f"  {'─'*70}")
    for label, r in [("Strong (BTD+PR+Exp)", r1), ("High Risk (CRL+Gene+Mfg)", r2),
                      ("PPM Flag", r3), ("SA+BTD+Surrogate", r4)]:
        print(f"  {label:>40s} {r['probability']:>8.1%} {r['tier']:>6d} {r['action']:>15s}")
    print(f"{'═'*72}")


if __name__ == "__main__":
    demo()
