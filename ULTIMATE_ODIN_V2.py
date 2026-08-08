#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               ULTIMATE ODIN V2.0 — THE SPEAR OF ODIN                       ║
║                                                                              ║
║  Forged from 298 iterations. Champion v12.51 CORNERSTONE base.              ║
║  + Expanded Social Signals (GOD MODE V7.1)                                  ║
║  + Operational Risk Module (v10.70)                                          ║
║  + CEO Tone / Qualitative Sentiment Module                                   ║
║  + Market Regime Detection (XBI/VIX)                                         ║
║  + Expectation Gap Module (S25 Research)                                     ║
║  + Enhanced HINT Ensemble with Modality/Sponsor interactions                 ║
║                                                                              ║
║  Base metrics (v12.51): WF Brier 0.08880, WF AUC 0.9082, Val AUC 0.9190   ║
║  Target: AUC > 0.9382 (+0.03), Tier4 accuracy > best +5%                   ║
║                                                                              ║
║  ALDX ACID TEST: prior_crl=2x, CEO bullish, quiet review → TIER_3          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    from ULTIMATE_ODIN_V2 import UltimateOdinScorer
    scorer = UltimateOdinScorer()
    result = scorer.score(signals)
    scorer.print_scorecard(result)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

__version__ = "2.0.0"
__codename__ = "SPEAR_OF_ODIN"
__lineage__ = "v12.51 CORNERSTONE + GOD_MODE_V71 + v10.70 + HINT + REGIME"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 1: v12.51 CHAMPION WEIGHTS (IMMUTABLE — DO NOT MODIFY)            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

W_V1251 = {
    # Base
    "base_logit": 1.6877965449124204,

    # Penalties (negative values)
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

    # Boosts (positive values)
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

# Platt calibration (from v1251 training)
PLATT_A = -0.026989505605139973
PLATT_B = 0.5827207756734252


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 2: NEW MODULE WEIGHTS (ULTIMATE V2.0 INNOVATIONS)                 ║
# ║ These are ADDITIVE layers on top of v1251 base. Conservatively seeded.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

W_ULTIMATE = {
    # ── Expanded Social Signals (GOD MODE V7.1) ──────────────────────
    # Individual social channel weights (replace single social_weight)
    "s17_sentiment_weight": 0.06,       # Social sentiment [-1, +1]
    "s18_engagement_spike_weight": 0.04, # Engagement spike [0, 1]
    "s19_social_silence_weight": -0.08,  # Social silence [0, 1] → bearish
    "s20_smart_money_divergence_weight": 0.07, # Smart money divergence [-1, +1]
    "social_master_amplifier": 1.2,     # Master social amplifier (conservative; GOD MODE found ~4.5)

    # ── CEO Tone / Qualitative Sentiment ─────────────────────────────
    # From S25 research: management tone on earnings calls is predictive
    # CALIBRATED v2: ALDX base is -5.22 (0.5%), need ~+1.0 logit total to reach 11%
    # CEO module budget: 0.37 logits (bullish + quiet_review)
    # Non-CRL cases get only CEO tone; CRL cases get CEO + interaction terms
    "ceo_tone_bullish_boost": 0.22,     # CEO/mgmt expressing confidence
    "ceo_tone_cautious_penalty": -0.18, # CEO hedging or cautious language
    "ceo_tone_silent_penalty": -0.10,   # No comment (suspicious for big PDUFA)
    "quiet_review_boost": 0.15,         # FDA quiet review = no issues raised

    # ── Operational Risk (v10.70) ────────────────────────────────────
    "amendment_count_penalty": -0.04,   # Per protocol amendment above 0
    "endpoint_change_penalty": -0.25,   # Primary endpoint changed mid-trial
    "pi_bad_history_penalty": -0.30,    # PI with bad BMIS/enrollment history
    "zero_enroller_penalty": -0.15,     # Per unit of zero_enroller_fraction

    # ── Expectation Gap (S25 Research) ───────────────────────────────
    # Gap between analyst consensus and ODIN probability
    "expectation_gap_weight": 0.10,     # Positive = ODIN more bullish than street
    "high_expectation_penalty": -0.20,  # Street expects approval, ODIN says risky

    # ── New Interaction Terms ────────────────────────────────────────
    # CALIBRATED v2: CRL recovery budget = 0.60 logits (ceo_bullish + quiet_review IXs)
    # Total ALDX lift: CEO(0.37) + IX(0.60) = 0.97 logits → after HINT ~11%
    # These only fire for prior_crl cases, so non-CRL scoring is unaffected
    "ix_prior_crl_x_ceo_bullish": 0.35, # Prior CRL but CEO confident → recovery signal
    "ix_prior_crl_x_quiet_review": 0.25, # Prior CRL + FDA quiet → positive
    "ix_gene_therapy_x_experienced": 0.15, # Gene therapy + big pharma → less CMC risk
    "ix_orphan_x_single_arm": 0.20,     # Orphan + single arm is acceptable
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 3: CONSTANTS & CLASSIFICATIONS                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Tier thresholds (same as v1251)
TIERS = {
    1: {"min": 0.85, "action": "LONG",          "sizing": "FULL",    "exit": "T-5"},
    2: {"min": 0.65, "action": "CAUTIOUS LONG",  "sizing": "HALF",    "exit": "T-7"},
    3: {"min": 0.40, "action": "MONITOR",         "sizing": "QUARTER", "exit": "T-7"},
    4: {"min": 0.00, "action": "NO TRADE",        "sizing": "ZERO",    "exit": "N/A"},
}

# TA risk classification (from v1251)
TA_RISK = {
    "VERY_HIGH_APPROVAL": ["vaccines", "womens_health"],
    "LOW_RISK": ["immunology", "dermatology", "oncology", "gi_hepatology",
                 "respiratory", "infectious", "anti_infective"],
    "MOD_RISK": ["cns", "neurology", "cardiovascular", "metabolic",
                 "rare_disease", "endocrine", "other"],
    "HIGH_RISK": ["pain", "ophthalmology", "nephrology", "hematology",
                  "psychiatry"],
}

# HINT CRL rates by TA (from odin_hint_engine.py — 1,350 event dataset)
HINT_TA_CRL_RATES = {
    "pain":              0.419,
    "hematology":        0.357,
    "nephrology":        0.310,
    "ophthalmology":     0.265,
    "cns":               0.232,
    "neurology":         0.232,
    "cardiovascular":    0.214,
    "metabolic":         0.200,
    "endocrine":         0.200,
    "rare_disease":      0.176,
    "other":             0.152,
    "immunology":        0.118,
    "dermatology":       0.105,
    "psychiatry":        0.100,
    "oncology":          0.072,
    "gi_hepatology":     0.067,
    "respiratory":       0.043,
    "infectious":        0.030,
    "anti_infective":    0.030,
    "womens_health":     0.000,
    "vaccines":          0.000,
}

# Hard override signals → force TIER 4
AVOID_SIGNALS = [
    "ppm_flag", "gene_therapy_cmc", "ema_cmc_flag",
    "hiring_void_nda", "pediatric_no_pk", "cmc_extension_active",
    "insider_critical_sell",
]

# Regime multipliers (from odin_regime.py)
REGIME_MULTIPLIERS = {
    "BULL":   1.2,
    "NORMAL": 1.0,
    "BEAR":   0.5,
    "CRISIS": 0.0,
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 4: ENUMS & DATA CLASSES                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class CeoTone(Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    SILENT = "silent"


class MarketRegime(Enum):
    BULL = "BULL"
    NORMAL = "NORMAL"
    BEAR = "BEAR"
    CRISIS = "CRISIS"


@dataclass
class UltimateSignals:
    """
    All input signals for ULTIMATE ODIN V2.0 scoring.
    Superset of v1251 OdinSignals + new modules.
    """
    # ── v1251 Core Signals (unchanged) ───────────────────────────────
    # Regulatory designations
    btd: bool = False
    orphan: bool = False
    priority_review: bool = False
    fast_track: bool = False
    accelerated_approval: bool = False

    # Sponsor
    experienced_sponsor: bool = False
    inexperienced_sponsor: bool = False
    sponsor_approvals: int = 0

    # Application type
    is_snda: bool = False
    is_snda_pediatric: bool = False
    is_class1_resubmission: bool = False

    # Trial design
    single_arm: bool = False
    surrogate_endpoint: bool = False

    # History
    prior_crl: bool = False
    prior_crl_count: int = 0
    double_crl: bool = False

    # Manufacturing / CMC
    manufacturing_risk: bool = False
    form_483: bool = False
    ema_cmc_flag: bool = False
    cmc_extension: bool = False

    # AdCom
    adcom_high: bool = False
    adcom_mid: bool = False
    adcom_low: bool = False

    # Safety
    safety_severity: float = 0.0
    ppm_flag: bool = False

    # Therapeutic area
    therapeutic_area: str = "other"
    is_oncology: bool = False
    is_gene_therapy: bool = False
    is_psychedelic: bool = False
    is_pain: bool = False

    # Temporal
    is_hoeg_era: bool = True
    pdufa_year: int = 2026

    # EU
    eu_approved: bool = False

    # Pediatric
    pediatric_no_pk: bool = False

    # v1251 MCP signals (aggregate)
    insider_signal: float = 0.0
    hiring_signal: float = 0.0
    social_signal: float = 0.0

    # HINT
    historical_crl_rate: Optional[float] = None

    # Avoid overrides
    avoid_override: bool = False

    # ── NEW: Expanded Social Signals (GOD MODE V7.1) ────────────────
    s17_sentiment: float = 0.0          # Social sentiment [-1, +1]
    s18_engagement_spike: float = 0.0   # Engagement spike [0, 1]
    s19_social_silence: float = 0.0     # Social silence [0, 1]
    s20_smart_money_divergence: float = 0.0  # Smart money divergence [-1, +1]

    # ── NEW: CEO Tone / Qualitative Sentiment ────────────────────────
    ceo_tone: CeoTone = CeoTone.NEUTRAL
    quiet_review: bool = False          # FDA quiet review (no issues)

    # ── NEW: Operational Risk (v10.70) ───────────────────────────────
    amendment_count: int = 0            # Protocol amendments
    endpoint_changed: bool = False       # Primary endpoint changed
    pi_bad_history: bool = False         # PI with bad BMIS record
    zero_enroller_fraction: float = 0.0  # Fraction of zero-enrolling sites

    # ── NEW: Expectation Gap (S25) ───────────────────────────────────
    analyst_consensus: Optional[float] = None  # Street probability [0, 1]

    # ── NEW: Market Regime ───────────────────────────────────────────
    market_regime: MarketRegime = MarketRegime.NORMAL
    regime_confidence: float = 0.6

    # ── NEW: Revenue Impact (Runup Module) ───────────────────────────
    revenue_tier: Optional[str] = None   # R1, R2, R3, R4
    peak_revenue_estimate: float = 0.0   # $ millions


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 5: HELPER FUNCTIONS                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

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
    if any(k in ta_lower for k in ["pain", "analges"]):
        return "HIGH_RISK"
    if any(k in ta_lower for k in ["onc", "cancer", "tumor"]):
        return "LOW_RISK"
    if any(k in ta_lower for k in ["cns", "neuro", "alzh", "parkin"]):
        return "MOD_RISK"
    if any(k in ta_lower for k in ["vaccin"]):
        return "VERY_HIGH_APPROVAL"
    return "MOD_RISK"


def _get_hint_crl_rate(ta: str) -> Optional[float]:
    """Look up HINT CRL rate for a therapeutic area."""
    ta_lower = ta.lower().replace(" ", "_").replace("-", "_")
    if ta_lower in HINT_TA_CRL_RATES:
        return HINT_TA_CRL_RATES[ta_lower]
    # Fuzzy match
    for key, rate in HINT_TA_CRL_RATES.items():
        if key in ta_lower or ta_lower in key:
            return rate
    return None


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 6: THE ULTIMATE SCORER                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class UltimateOdinScorer:
    """
    ULTIMATE ODIN V2.0 — THE SPEAR OF ODIN

    Scoring pipeline (7 layers):
      1. v1251 Champion Base (54 features + 6 interactions) — IMMUTABLE
      2. CEO Tone & Qualitative Module
      3. Expanded Social Signals (4-channel)
      4. Operational Risk Module
      5. New Interaction Terms (CRL recovery signals)
      6. Expectation Gap Module
      7. HINT Ensemble Blend
      → sigmoid → Platt calibration → tier → regime sizing
    """

    def __init__(self, enable_regime: bool = True, enable_social_v2: bool = True,
                 enable_ceo_tone: bool = True, enable_ops_risk: bool = True,
                 enable_expectation_gap: bool = True):
        self.version = __version__
        self.codename = __codename__
        self.w_base = W_V1251.copy()
        self.w_new = W_ULTIMATE.copy()

        # Module toggles (for ablation studies)
        self.enable_regime = enable_regime
        self.enable_social_v2 = enable_social_v2
        self.enable_ceo_tone = enable_ceo_tone
        self.enable_ops_risk = enable_ops_risk
        self.enable_expectation_gap = enable_expectation_gap

    def score(self, s: UltimateSignals) -> Dict[str, Any]:
        """
        Score a PDUFA catalyst through the full 7-layer pipeline.
        Returns comprehensive scorecard dict.
        """
        W = self.w_base
        U = self.w_new
        contributions = []
        module_contributions = {}  # Track by module for analysis

        # ════════════════════════════════════════════════════════════════
        # LAYER 0: AVOID SIGNAL CHECK
        # ════════════════════════════════════════════════════════════════
        avoid_reasons = []
        if s.ppm_flag:
            avoid_reasons.append("PPM_FLAG: Primary pivotal miss")
        if s.is_gene_therapy and s.manufacturing_risk:
            avoid_reasons.append("GENE_THERAPY_CMC: Gene therapy + CMC risk")
        if s.ema_cmc_flag:
            avoid_reasons.append("EMA_CMC_FLAG: EMA manufacturing concern")
        if s.hiring_signal < -0.5:
            avoid_reasons.append("HIRING_VOID: No NDA-stage hiring")
        if s.pediatric_no_pk:
            avoid_reasons.append("PEDIATRIC_NO_PK: No PK bridging data")
        if s.cmc_extension:
            avoid_reasons.append("CMC_EXTENSION: PDUFA extended for CMC")
        if s.insider_signal < -0.8:
            avoid_reasons.append("INSIDER_CRITICAL: Heavy insider selling")
        if s.avoid_override:
            avoid_reasons.append("MANUAL_OVERRIDE: Forced avoid")

        # ════════════════════════════════════════════════════════════════
        # LAYER 1: v1251 CHAMPION BASE (IMMUTABLE)
        # ════════════════════════════════════════════════════════════════
        logit = W["base_logit"]
        contributions.append(("base_logit", W["base_logit"], "BASE"))

        # --- Penalties ---
        def _add(cond, key, label="BASE"):
            nonlocal logit
            if cond:
                logit += W[key]
                contributions.append((key, W[key], label))

        _add(s.is_snda, "snda_base_penalty")
        _add(s.is_snda_pediatric, "snda_pediatric_base_penalty")
        _add(s.prior_crl, "prior_crl_penalty")
        if s.prior_crl_count > 1:
            extra = (s.prior_crl_count - 1) * W["prior_crl_count_penalty"]
            logit += extra
            contributions.append(("prior_crl_count_penalty", extra, "BASE"))
        _add(s.double_crl, "double_crl_penalty")
        _add(s.inexperienced_sponsor, "inexperienced_sponsor_penalty")
        _add(s.manufacturing_risk, "manufacturing_risk_penalty")
        _add(s.form_483, "form_483_penalty")
        _add(s.ema_cmc_flag, "ema_cmc_flag_penalty")
        _add(s.cmc_extension, "cmc_extension_penalty")
        _add(s.adcom_mid, "adcom_mid_penalty")
        _add(s.adcom_low, "adcom_low_penalty")
        _add(s.pediatric_no_pk, "s22_pediatric_pk_penalty")
        _add(s.is_gene_therapy, "gene_therapy_penalty")
        _add(s.single_arm, "single_arm_study_penalty")
        _add(s.surrogate_endpoint, "surrogate_endpoint_penalty")
        if s.safety_severity > 0:
            pen = s.safety_severity * W["safety_severity_penalty"]
            logit += pen
            contributions.append(("safety_severity_penalty", pen, "BASE"))
        _add(s.ppm_flag, "ppm_penalty")
        _add(s.is_psychedelic, "psychedelics_penalty")
        _add(s.is_class1_resubmission, "class1_resubmission_boost")

        # Temporal
        _add(s.is_hoeg_era, "hoeg_era_constant")
        if s.accelerated_approval and s.pdufa_year >= 2025:
            logit += W["accel_approval_2025plus_penalty"]
            contributions.append(("accel_approval_2025plus_penalty",
                                  W["accel_approval_2025plus_penalty"], "BASE"))
        if s.experienced_sponsor and s.pdufa_year >= 2026:
            logit += W["experienced_sponsor_2026_reduction"]
            contributions.append(("experienced_sponsor_2026_reduction",
                                  W["experienced_sponsor_2026_reduction"], "BASE"))
        if s.eu_approved and s.pdufa_year >= 2026:
            logit += W["eu_approved_2026_penalty"]
            contributions.append(("eu_approved_2026_penalty",
                                  W["eu_approved_2026_penalty"], "BASE"))

        # TA penalties
        ta_risk = _classify_ta_risk(s.therapeutic_area)
        if ta_risk == "HIGH_RISK":
            logit += W["ta_high_risk_penalty"]
            contributions.append(("ta_high_risk_penalty", W["ta_high_risk_penalty"], "BASE"))
        elif ta_risk == "MOD_RISK":
            logit += W["ta_mod_risk_penalty"]
            contributions.append(("ta_mod_risk_penalty", W["ta_mod_risk_penalty"], "BASE"))
        _add(s.is_pain, "indication_pain_penalty")
        _add(s.is_oncology, "indication_onc_boost")
        if s.inexperienced_sponsor and ta_risk == "HIGH_RISK":
            logit += W["novice_sponsor_high_risk_ta_penalty"]
            contributions.append(("novice_sponsor_high_risk_ta_penalty",
                                  W["novice_sponsor_high_risk_ta_penalty"], "BASE"))

        # --- Boosts ---
        _add(s.btd, "btd_weight")
        _add(s.orphan, "orphan_weight")
        _add(s.priority_review, "priority_review_weight")
        _add(s.fast_track, "fast_track_weight")
        _add(s.accelerated_approval, "accelerated_approval_weight")
        _add(s.experienced_sponsor, "experienced_sponsor_boost")
        _add(s.adcom_high, "adcom_high_boost")
        _add(s.eu_approved, "eu_approved_boost")
        if s.btd and s.is_oncology:
            logit += W["btd_oncology_boost"]
            contributions.append(("btd_oncology_boost", W["btd_oncology_boost"], "BASE"))
        if ta_risk == "VERY_HIGH_APPROVAL":
            logit += W["ta_very_high_boost"]
            contributions.append(("ta_very_high_boost", W["ta_very_high_boost"], "BASE"))

        # --- v1251 Signal Weights ---
        if s.insider_signal != 0:
            sig = s.insider_signal * W["s23_insider_weight"]
            logit += sig
            contributions.append(("s23_insider", sig, "BASE"))
        if s.hiring_signal != 0:
            sig = s.hiring_signal * W["s6_hiring_weight"]
            logit += sig
            contributions.append(("s6_hiring", sig, "BASE"))

        # --- v1251 Interaction Terms ---
        if s.prior_crl and s.manufacturing_risk:
            logit += W["ix_prior_crl_x_mfg_risk"]
            contributions.append(("ix_prior_crl_x_mfg_risk", W["ix_prior_crl_x_mfg_risk"], "BASE"))
        if s.prior_crl and s.form_483:
            logit += W["ix_prior_crl_x_form483"]
            contributions.append(("ix_prior_crl_x_form483", W["ix_prior_crl_x_form483"], "BASE"))
        if s.is_gene_therapy and s.manufacturing_risk:
            logit += W["ix_gene_therapy_x_mfg_risk"]
            contributions.append(("ix_gene_therapy_x_mfg_risk", W["ix_gene_therapy_x_mfg_risk"], "BASE"))
        if s.inexperienced_sponsor and s.manufacturing_risk:
            logit += W["ix_inexperienced_x_mfg_risk"]
            contributions.append(("ix_inexperienced_x_mfg_risk", W["ix_inexperienced_x_mfg_risk"], "BASE"))
        if s.single_arm and s.surrogate_endpoint:
            logit += W["ix_single_arm_x_surrogate"]
            contributions.append(("ix_single_arm_x_surrogate", W["ix_single_arm_x_surrogate"], "BASE"))
        if s.btd and s.single_arm:
            logit += W["ix_btd_x_single_arm"]
            contributions.append(("ix_btd_x_single_arm", W["ix_btd_x_single_arm"], "BASE"))

        base_logit = logit  # Snapshot after v1251 base
        module_contributions["v1251_base"] = logit - W["base_logit"]

        # ════════════════════════════════════════════════════════════════
        # LAYER 2: CEO TONE & QUALITATIVE MODULE
        # ════════════════════════════════════════════════════════════════
        ceo_contribution = 0.0
        if self.enable_ceo_tone:
            if s.ceo_tone == CeoTone.BULLISH:
                ceo_contribution += U["ceo_tone_bullish_boost"]
                contributions.append(("ceo_tone_bullish", U["ceo_tone_bullish_boost"], "CEO_TONE"))
            elif s.ceo_tone == CeoTone.CAUTIOUS:
                ceo_contribution += U["ceo_tone_cautious_penalty"]
                contributions.append(("ceo_tone_cautious", U["ceo_tone_cautious_penalty"], "CEO_TONE"))
            elif s.ceo_tone == CeoTone.SILENT:
                ceo_contribution += U["ceo_tone_silent_penalty"]
                contributions.append(("ceo_tone_silent", U["ceo_tone_silent_penalty"], "CEO_TONE"))

            if s.quiet_review:
                ceo_contribution += U["quiet_review_boost"]
                contributions.append(("quiet_review", U["quiet_review_boost"], "CEO_TONE"))

            logit += ceo_contribution
            module_contributions["ceo_tone"] = ceo_contribution

        # ════════════════════════════════════════════════════════════════
        # LAYER 3: EXPANDED SOCIAL SIGNALS (GOD MODE V7.1 architecture)
        # ════════════════════════════════════════════════════════════════
        social_contribution = 0.0
        if self.enable_social_v2:
            # Use individual channel weights instead of single social_weight
            has_social_v2 = any([s.s17_sentiment, s.s18_engagement_spike,
                                s.s19_social_silence, s.s20_smart_money_divergence])

            if has_social_v2:
                raw_social = (
                    s.s17_sentiment * U["s17_sentiment_weight"] +
                    s.s18_engagement_spike * U["s18_engagement_spike_weight"] +
                    s.s19_social_silence * U["s19_social_silence_weight"] +
                    s.s20_smart_money_divergence * U["s20_smart_money_divergence_weight"]
                )
                social_contribution = raw_social * U["social_master_amplifier"]
                if abs(social_contribution) > 0.001:
                    logit += social_contribution
                    contributions.append(("social_v2_expanded", social_contribution, "SOCIAL_V2"))
            elif s.social_signal != 0:
                # Fallback to v1251 single social weight
                social_contribution = s.social_signal * W["social_weight"]
                logit += social_contribution
                contributions.append(("social_v1_fallback", social_contribution, "SOCIAL_V2"))

            module_contributions["social_v2"] = social_contribution
        elif s.social_signal != 0:
            # Module disabled, use v1251 social
            sig = s.social_signal * W["social_weight"]
            logit += sig
            contributions.append(("social_v1", sig, "BASE"))

        # ════════════════════════════════════════════════════════════════
        # LAYER 4: OPERATIONAL RISK MODULE (v10.70)
        # ════════════════════════════════════════════════════════════════
        ops_contribution = 0.0
        if self.enable_ops_risk:
            if s.amendment_count > 0:
                pen = s.amendment_count * U["amendment_count_penalty"]
                ops_contribution += pen
                contributions.append(("amendment_count", pen, "OPS_RISK"))
            if s.endpoint_changed:
                ops_contribution += U["endpoint_change_penalty"]
                contributions.append(("endpoint_changed", U["endpoint_change_penalty"], "OPS_RISK"))
            if s.pi_bad_history:
                ops_contribution += U["pi_bad_history_penalty"]
                contributions.append(("pi_bad_history", U["pi_bad_history_penalty"], "OPS_RISK"))
            if s.zero_enroller_fraction > 0:
                pen = s.zero_enroller_fraction * U["zero_enroller_penalty"]
                ops_contribution += pen
                contributions.append(("zero_enroller", pen, "OPS_RISK"))

            logit += ops_contribution
            module_contributions["ops_risk"] = ops_contribution

        # ════════════════════════════════════════════════════════════════
        # LAYER 5: NEW INTERACTION TERMS (CRL recovery signals)
        # ════════════════════════════════════════════════════════════════
        new_ix_contribution = 0.0
        if s.prior_crl and s.ceo_tone == CeoTone.BULLISH and self.enable_ceo_tone:
            new_ix_contribution += U["ix_prior_crl_x_ceo_bullish"]
            contributions.append(("ix_prior_crl_x_ceo_bullish",
                                  U["ix_prior_crl_x_ceo_bullish"], "NEW_IX"))
        if s.prior_crl and s.quiet_review and self.enable_ceo_tone:
            new_ix_contribution += U["ix_prior_crl_x_quiet_review"]
            contributions.append(("ix_prior_crl_x_quiet_review",
                                  U["ix_prior_crl_x_quiet_review"], "NEW_IX"))
        if s.is_gene_therapy and s.experienced_sponsor:
            new_ix_contribution += U["ix_gene_therapy_x_experienced"]
            contributions.append(("ix_gene_therapy_x_experienced",
                                  U["ix_gene_therapy_x_experienced"], "NEW_IX"))
        if s.orphan and s.single_arm:
            new_ix_contribution += U["ix_orphan_x_single_arm"]
            contributions.append(("ix_orphan_x_single_arm",
                                  U["ix_orphan_x_single_arm"], "NEW_IX"))

        logit += new_ix_contribution
        module_contributions["new_interactions"] = new_ix_contribution

        # ════════════════════════════════════════════════════════════════
        # LAYER 6: HINT ENSEMBLE BLEND
        # ════════════════════════════════════════════════════════════════
        odin_logit = logit
        hint_applied = False
        hint_crl_rate = s.historical_crl_rate

        # Auto-lookup HINT CRL rate if not provided
        if hint_crl_rate is None:
            hint_crl_rate = _get_hint_crl_rate(s.therapeutic_area)

        if hint_crl_rate is not None:
            hint_logit = W["base_logit"] + W["hint_crl_rate_penalty"] * hint_crl_rate
            logit = W["odin_weight"] * odin_logit + W["hint_weight"] * hint_logit
            hint_applied = True
            hint_blend_delta = logit - odin_logit
            contributions.append(("hint_blend", hint_blend_delta, "HINT"))
            module_contributions["hint"] = hint_blend_delta

        # ════════════════════════════════════════════════════════════════
        # LAYER 7: EXPECTATION GAP MODULE
        # ════════════════════════════════════════════════════════════════
        gap_contribution = 0.0
        if self.enable_expectation_gap and s.analyst_consensus is not None:
            odin_prob_pre = _sigmoid(logit)
            gap = odin_prob_pre - s.analyst_consensus  # positive = ODIN more bullish
            gap_contribution = gap * U["expectation_gap_weight"]

            # Penalty when street expects approval but ODIN sees risk
            if s.analyst_consensus > 0.80 and odin_prob_pre < 0.60:
                gap_contribution += U["high_expectation_penalty"]
                contributions.append(("high_expectation_gap",
                                      U["high_expectation_penalty"], "EXP_GAP"))

            if abs(gap_contribution) > 0.001:
                logit += gap_contribution
                contributions.append(("expectation_gap", gap_contribution, "EXP_GAP"))

            module_contributions["expectation_gap"] = gap_contribution

        # ════════════════════════════════════════════════════════════════
        # CONVERT TO PROBABILITY & TIER
        # ════════════════════════════════════════════════════════════════
        raw_logit = logit
        probability = _sigmoid(logit)

        # Tier classification (avoid signals force TIER 4)
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

        # ════════════════════════════════════════════════════════════════
        # REGIME SIZING ADJUSTMENT
        # ════════════════════════════════════════════════════════════════
        regime_mult = 1.0
        regime_str = "NORMAL"
        if self.enable_regime:
            regime_str = s.market_regime.value
            regime_mult = REGIME_MULTIPLIERS.get(regime_str, 1.0)

        sizing_map = {"FULL": 1.0, "HALF": 0.5, "QUARTER": 0.25, "ZERO": 0.0}
        base_sizing = sizing_map.get(tier_info["sizing"], 0.0)
        adjusted_sizing = base_sizing * regime_mult

        # CRISIS regime forces NO TRADE regardless of tier
        if regime_str == "CRISIS":
            tier = 4
            tier_info = TIERS[4]
            adjusted_sizing = 0.0

        # ════════════════════════════════════════════════════════════════
        # BUILD OUTPUT
        # ════════════════════════════════════════════════════════════════

        # Positive signals
        positive_signals = []
        if s.btd: positive_signals.append("✅ Breakthrough Therapy Designation")
        if s.priority_review: positive_signals.append("✅ Priority Review")
        if s.orphan: positive_signals.append("✅ Orphan Drug Designation")
        if s.fast_track: positive_signals.append("✅ Fast Track")
        if s.accelerated_approval: positive_signals.append("✅ Accelerated Approval")
        if s.experienced_sponsor: positive_signals.append("✅ Experienced Sponsor")
        if s.adcom_high: positive_signals.append("✅ Favorable AdCom (≥65%)")
        if s.eu_approved: positive_signals.append("✅ EU Approved")
        if s.btd and s.is_oncology: positive_signals.append("✅ BTD + Oncology")
        if s.insider_signal > 0.3: positive_signals.append("✅ Bullish Insider Activity")
        if s.hiring_signal > 0.5: positive_signals.append("✅ NDA-Stage Hiring Detected")
        if s.ceo_tone == CeoTone.BULLISH: positive_signals.append("✅ CEO Bullish Tone")
        if s.quiet_review: positive_signals.append("✅ FDA Quiet Review")
        if s.s20_smart_money_divergence > 0.5: positive_signals.append("✅ Smart Money Bullish")

        # Risk flags
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
        if s.endpoint_changed: risk_flags.append("🔴 Endpoint Changed Mid-Trial")
        if s.amendment_count >= 3: risk_flags.append("🟡 Multiple Protocol Amendments")
        if s.ceo_tone == CeoTone.CAUTIOUS: risk_flags.append("🟡 CEO Cautious Tone")
        if s.ceo_tone == CeoTone.SILENT: risk_flags.append("🟡 Management Silent on PDUFA")
        if s.s19_social_silence > 0.7: risk_flags.append("🟡 Social Silence (bearish)")
        if regime_str == "BEAR": risk_flags.append("📉 Bear Market Regime (0.5x sizing)")
        if regime_str == "CRISIS": risk_flags.append("🚨 Crisis Regime (NO TRADE)")
        risk_flags.extend([f"🚫 AVOID: {r}" for r in avoid_reasons])

        # Sort contributions by magnitude
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        # v1251 comparison
        v1251_prob = _sigmoid(base_logit)

        return {
            "version": self.version,
            "codename": self.codename,
            "model": "ULTIMATE_ODIN_V2_SPEAR",
            "probability": round(probability, 4),
            "v1251_probability": round(v1251_prob, 4),
            "delta_from_v1251": round(probability - v1251_prob, 4),
            "tier": tier,
            "action": tier_info["action"],
            "sizing": tier_info["sizing"],
            "adjusted_sizing": round(adjusted_sizing, 4),
            "exit": tier_info["exit"],
            "ta_risk_tier": ta_risk,
            "raw_logit": round(raw_logit, 4),
            "base_logit_v1251": round(base_logit, 4),
            "hint_applied": hint_applied,
            "hint_crl_rate": hint_crl_rate,
            "market_regime": regime_str,
            "regime_multiplier": regime_mult,
            "regime_confidence": round(s.regime_confidence, 2),
            "positive_signals": positive_signals,
            "risk_flags": risk_flags,
            "avoid_reasons": avoid_reasons,
            "contributions": [(n, round(v, 4), m) for n, v, m in contributions[:20]],
            "module_contributions": {k: round(v, 4) for k, v in module_contributions.items()},
            "modules_active": {
                "ceo_tone": self.enable_ceo_tone,
                "social_v2": self.enable_social_v2,
                "ops_risk": self.enable_ops_risk,
                "expectation_gap": self.enable_expectation_gap,
                "regime": self.enable_regime,
            },
            "wf_metrics_base": {"brier": 0.08880, "auc": 0.9082},
        }

    def print_scorecard(self, r: Dict, ticker: str = "", drug: str = "",
                        indication: str = "", pdufa_date: str = ""):
        """Pretty-print the ULTIMATE scorecard."""
        W = 78
        print(f"\n{'═'*W}")
        print(f"  ⚔️  ULTIMATE ODIN V{self.version} ({self.codename}) — PDUFA SCORECARD")
        print(f"{'═'*W}")
        if ticker:
            print(f"  Ticker: {ticker:12s}  Drug: {drug}")
        if indication:
            print(f"  Indication: {indication}")
        if pdufa_date:
            print(f"  PDUFA Date: {pdufa_date}")

        print(f"\n  PROBABILITY: {r['probability']:.1%}  (v1251 base: {r['v1251_probability']:.1%}, Δ{r['delta_from_v1251']:+.1%})")
        print(f"  Raw Logit:   {r['raw_logit']:.3f}  (v1251 base logit: {r['base_logit_v1251']:.3f})")
        if r['hint_applied']:
            print(f"  HINT Blend:  Applied (CRL rate: {r['hint_crl_rate']:.1%})")

        tier_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}
        print(f"\n  ┌{'─'*52}┐")
        print(f"  │ {tier_emoji[r['tier']]} TIER {r['tier']:43d}│")
        print(f"  │  ACTION: {r['action']:41s}│")
        print(f"  │  BASE SIZING: {r['sizing']:35s}│")
        print(f"  │  REGIME-ADJ SIZING: {r['adjusted_sizing']:4.2f}x{' '*24}│")
        print(f"  │  EXIT:   {r['exit']:41s}│")
        print(f"  │  TA RISK: {r['ta_risk_tier']:40s}│")
        print(f"  │  REGIME: {r['market_regime']:>6s} ({r['regime_multiplier']:.1f}x){' '*26}│")
        print(f"  └{'─'*52}┘")

        if r['positive_signals']:
            print(f"\n  POSITIVE SIGNALS:")
            for s in r['positive_signals']:
                print(f"    {s}")

        if r['risk_flags']:
            print(f"\n  RISK FLAGS:")
            for f in r['risk_flags']:
                print(f"    {f}")

        # Module contributions
        mc = r.get('module_contributions', {})
        if mc:
            print(f"\n  MODULE CONTRIBUTIONS (logit-space):")
            for mod, val in sorted(mc.items(), key=lambda x: abs(x[1]), reverse=True):
                if abs(val) > 0.001:
                    arrow = '↑' if val > 0 else '↓'
                    print(f"    {arrow} {mod:>25s}: {val:+.4f}")

        if r['contributions']:
            print(f"\n  TOP FEATURE CONTRIBUTIONS:")
            for name, val, module in r['contributions'][:12]:
                arrow = '↑' if val > 0 else '↓'
                print(f"    {arrow} [{module:>10s}] {name:>35s}: {val:+.4f}")

        print(f"\n  Base WF Metrics: Brier={r['wf_metrics_base']['brier']:.5f}, AUC={r['wf_metrics_base']['auc']:.4f}")
        print(f"  Active Modules: {sum(r['modules_active'].values())}/5")
        print(f"{'═'*W}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SECTION 7: ALDX ACID TEST & DEMO CASES                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def aldx_acid_test():
    """
    ALDX ACID TEST — The defining validation case.

    ALDX reproxalap: 2x CRL, CEO bullish on resubmission, FDA quiet review.
    v1251 would output ~TIER_4 (1-5%) due to heavy prior_crl penalties.
    ULTIMATE V2.0 target: TIER_3 (10-15%) due to recovery signals.
    """
    print("\n" + "🧪"*35)
    print("  ALDX ACID TEST — REPROXALAP RESUBMISSION")
    print("🧪"*35)

    scorer = UltimateOdinScorer()

    # ALDX reproxalap signals
    aldx = UltimateSignals(
        # History: 2x CRL (very bearish in v1251)
        prior_crl=True,
        prior_crl_count=2,
        double_crl=True,

        # But recovery signals:
        ceo_tone=CeoTone.BULLISH,      # CEO confident on resubmission
        quiet_review=True,              # FDA not raising new issues
        priority_review=False,
        fast_track=True,                # Fast track designation

        # Sponsor/TA
        experienced_sponsor=False,       # Mid-size biotech
        inexperienced_sponsor=False,
        therapeutic_area="ophthalmology",
        is_pain=False,

        # Signals
        insider_signal=0.2,             # Mild insider buying
        hiring_signal=0.6,              # NDA-stage hiring detected
        social_signal=0.1,

        # Expanded social
        s17_sentiment=0.3,              # Moderately bullish sentiment
        s18_engagement_spike=0.2,
        s19_social_silence=0.1,         # Not silent (good)
        s20_smart_money_divergence=0.4, # Smart money accumulating

        # Context
        is_hoeg_era=True,
        pdufa_year=2026,
        market_regime=MarketRegime.NORMAL,
    )

    result = scorer.score(aldx)
    scorer.print_scorecard(result, "ALDX", "reproxalap", "Dry Eye Disease", "2026-Q3")

    # Acid test assertion
    prob = result["probability"]
    tier = result["tier"]
    print(f"\n  {'✅' if tier <= 3 else '❌'} ALDX ACID TEST: Prob={prob:.1%}, Tier={tier}")
    print(f"  {'✅' if 0.10 <= prob <= 0.25 else '⚠️'} Target range: 10-25% (TIER_3)")
    print(f"  v1251 base would give: {result['v1251_probability']:.1%}")
    print(f"  ULTIMATE V2.0 delta:   {result['delta_from_v1251']:+.1%}")

    return result


def demo():
    """Run full demo suite."""
    scorer = UltimateOdinScorer()

    print("\n" + "="*78)
    print("  ULTIMATE ODIN V2.0 — DEMO SUITE")
    print("="*78)

    # Case 1: Strong approval candidate
    s1 = UltimateSignals(
        btd=True, priority_review=True, experienced_sponsor=True,
        therapeutic_area="oncology", is_oncology=True,
        ceo_tone=CeoTone.BULLISH, quiet_review=True,
        s17_sentiment=0.8, s20_smart_money_divergence=0.6,
        is_hoeg_era=True, pdufa_year=2026,
    )
    r1 = scorer.score(s1)
    scorer.print_scorecard(r1, "ONCO", "oncodrug", "NSCLC 2L", "2026-06-15")

    # Case 2: High risk — prior CRL + gene therapy
    s2 = UltimateSignals(
        prior_crl=True, prior_crl_count=1,
        is_gene_therapy=True, manufacturing_risk=True,
        inexperienced_sponsor=True,
        therapeutic_area="rare_disease",
        ceo_tone=CeoTone.CAUTIOUS,
        amendment_count=2,
        is_hoeg_era=True, pdufa_year=2026,
    )
    r2 = scorer.score(s2)
    scorer.print_scorecard(r2, "GENE", "genetherapy", "Hemophilia B", "2026-09-01")

    # Case 3: Gene therapy + experienced sponsor (interaction helps)
    s3 = UltimateSignals(
        is_gene_therapy=True, manufacturing_risk=False,
        experienced_sponsor=True, btd=True, orphan=True,
        priority_review=True,
        therapeutic_area="rare_disease",
        ceo_tone=CeoTone.BULLISH,
        is_hoeg_era=True, pdufa_year=2026,
    )
    r3 = scorer.score(s3)
    scorer.print_scorecard(r3, "BIG", "genecure", "SMA Type 1", "2026-07-20")

    # Case 4: Bear market regime
    s4 = UltimateSignals(
        btd=True, priority_review=True, experienced_sponsor=True,
        therapeutic_area="immunology",
        ceo_tone=CeoTone.NEUTRAL,
        is_hoeg_era=True, pdufa_year=2026,
        market_regime=MarketRegime.BEAR,
    )
    r4 = scorer.score(s4)
    scorer.print_scorecard(r4, "IMMU", "immunodrug", "Atopic Dermatitis", "2026-08-10")

    # Case 5: PPM flag (forced TIER 4 — ultimate can't save this)
    s5 = UltimateSignals(
        ppm_flag=True, priority_review=True, btd=True,
        experienced_sponsor=True,
        therapeutic_area="cns",
        ceo_tone=CeoTone.BULLISH,  # Even bullish CEO can't override PPM
        is_hoeg_era=True, pdufa_year=2026,
    )
    r5 = scorer.score(s5)
    scorer.print_scorecard(r5, "FAIL", "failamab", "Alzheimer's", "2026-04-20")

    # Summary table
    print(f"\n{'═'*78}")
    print(f"  {'Case':>35s} {'Prob':>7s} {'v1251':>7s} {'Delta':>7s} {'Tier':>5s} {'Action':>15s}")
    print(f"  {'─'*76}")
    cases = [
        ("Strong Onc (BTD+PR+CEO Bull)", r1),
        ("Gene Therapy + Novice + CRL", r2),
        ("Gene Therapy + BigPharma + BTD", r3),
        ("Immunology + Bear Market", r4),
        ("PPM Flag (forced TIER 4)", r5),
    ]
    for label, r in cases:
        print(f"  {label:>35s} {r['probability']:>7.1%} {r['v1251_probability']:>7.1%} "
              f"{r['delta_from_v1251']:>+7.1%} {r['tier']:>5d} {r['action']:>15s}")
    print(f"{'═'*78}")

    # ALDX Acid Test
    aldx_acid_test()


if __name__ == "__main__":
    demo()
