"""
ODIN v10.5 — FDA PDUFA Approval Probability Scoring (Liquid Architecture)

Architecture:
- Layer 1: Vectorized Additive Score (Base + Weights)
- Layer 2: Isotonic Calibration (Raw Score -> True Probability)
- Layer 3: Dynamic Tiering (Percentile-based thresholds)

Optimized on 1,934 events.
- Base Rate: 60.8% (Conservative)
- High AdCom Boost: +37.5%
- Critical Insider/CMC Signals: Hard Avoids
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Union
from enum import Enum
from datetime import datetime
import json
import os
import pickle
import warnings

# Suppress sklearn warnings if cleaner output desired
warnings.filterwarnings("ignore")

# =========== GLOBAL CALIBRATOR LOADING ===========
CALIBRATOR_PATH = "odin_v105_calibrator.pkl"
CALIBRATOR = None

try:
    if os.path.exists(CALIBRATOR_PATH):
        with open(CALIBRATOR_PATH, "rb") as f:
            CALIBRATOR = pickle.load(f)
        # print(f"[ODIN] Loaded Isotonic Calibrator from {CALIBRATOR_PATH}")
    else:
        print(f"[ODIN] WARNING: Calibrator {CALIBRATOR_PATH} not found. Using raw scores.")
except Exception as e:
    print(f"[ODIN] Error loading calibrator: {e}")

# =========== ENUMS ===========

class AvoidSignal(Enum):
    NONE = "NONE"
    EMA_CMC_FLAG = "AVOID_001_EMA_CMC"
    HIRING_VOID_NDA = "AVOID_002_HIRING_VOID"
    PEDIATRIC_NO_PK = "AVOID_003_PEDIATRIC_NO_PK"
    CMC_EXTENSION = "AVOID_004_CMC_EXTENSION"
    INSIDER_CRITICAL = "AVOID_006_INSIDER_CRITICAL"
    INSIDER_COORDINATED = "AVOID_007_INSIDER_COORDINATED"
    CSUITE_EXODUS = "AVOID_008_CSUITE_EXODUS"

class InsiderRiskLevel(Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"

class HiringSignal(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    NEUTRAL = "NEUTRAL"
    VOID = "VOID"

class ApplicationType(Enum):
    NDA = "NDA"
    BLA = "BLA"
    SNDA = "sNDA"
    SBLA = "sBLA"

# =========== THERAPEUTIC AREA ADJUSTMENTS ===========
TA_ADJUSTMENTS: Dict[str, float] = {
    "Pain Management": -0.30,
    "Ophthalmology": -0.25,
    "Nephrology": -0.22,
    "Hematology": -0.18,
    "CNS/Neurology": -0.10,
    "CNS": -0.10,
    "Cardiovascular": -0.08,
    "Metabolic/Endocrine": -0.07,
    "Metabolic": -0.07,
    "Other": -0.06,
    "Rare Disease": -0.04,
    "Immunology": +0.02,
    "Dermatology": +0.03,
    "Oncology": +0.06,
    "GI/Hepatology": +0.07,
    "Respiratory": +0.09,
    "Infectious Disease": +0.10,
    "Infectious": +0.10,
    "Vaccines": +0.13,
    "Women's Health": +0.13,
}

TA_RISK_TIERS = {
    "HIGH_RISK": ["Pain Management", "Ophthalmology", "Nephrology", "Hematology"],
    "MOD_RISK": ["CNS/Neurology", "CNS", "Cardiovascular", "Metabolic/Endocrine", "Metabolic", "Other", "Rare Disease"],
    "LOW_RISK": [
        "Immunology", "Dermatology", "Oncology", "GI/Hepatology",
        "Respiratory", "Infectious Disease", "Infectious", "Vaccines", "Women's Health",
    ],
}

# =========== CONFIG (OPTIMIZED v10.5) ===========

@dataclass(frozen=True)
class OdinV105Config:
    # --- OPTIMIZED LIQUID WEIGHTS ---
    base_approval_rate: float = 0.608
    
    # Penalties (Application)
    snda_base_penalty: float = -0.321
    snda_pediatric_base_penalty: float = -0.457
    
    # Designations (Boosts)
    btd_weight: float = 0.044
    orphan_weight: float = 0.057
    priority_review_weight: float = 0.004
    fast_track_weight: float = 0.007
    accelerated_approval_weight: float = 0.004
    
    # AdCom
    adcom_high_boost: float = 0.375
    adcom_mid_penalty: float = -0.438
    adcom_low_penalty: float = -0.140
    
    # CRL / Sponsor
    prior_crl_penalty: float = -0.063
    class1_resubmission_boost: float = 0.316
    experienced_sponsor_boost: float = 0.024
    inexperienced_sponsor_penalty: float = -0.481
    experienced_threshold: int = 5
    inexperienced_threshold: int = 0
    
    # CMC Risk (S12)
    manufacturing_risk_penalty: float = -0.017
    form_483_penalty: float = -0.183
    ema_cmc_flag_penalty: float = -0.442
    cmc_extension_penalty: float = -0.298
    
    # Scalars (Multipliers for lookup signals)
    ta_adjustment_weight: float = 0.358
    s23_insider_weight: float = 0.283
    s6_hiring_weight: float = 0.270
    social_weight: float = 0.003
    
    # Dynamic Thresholds (Top 20% / 40% / 60%)
    tier1_threshold: float = 0.840
    tier2_threshold: float = 0.739
    tier3_threshold: float = 0.655
    
    # Clamps
    clamp_min: float = 0.01
    clamp_max: float = 0.99

# =========== RESULT ===========

@dataclass
class OdinV105Result:
    ticker: str
    event_id: str
    probability: float          # Calibrated Probability
    raw_score: float            # Pre-calibration Score
    tier: str
    base_rate: float
    designation_total: float
    adcom_adjustment: float
    prior_crl_adjustment: float
    sponsor_adjustment: float
    manufacturing_adjustment: float
    ta_adjustment: float
    s23_insider_selling: float
    s23_risk_level: str
    s23_triggers: List[str]
    s6_commercial_hiring: float
    s6_signal: str
    s6_rationale: str
    s12_cmc_risk: float
    s22_pediatric_pk: float
    social_total: float
    s21_capped: bool
    avoid_signals: List[str]
    is_hard_avoid: bool
    is_weekend_pdufa: bool
    weekend_execution_note: str
    recommended_action: str
    exit_window: str
    runner_position: str
    ta_risk_tier: str = "UNKNOWN"
    adjustments_breakdown: Dict[str, float] = field(default_factory=dict)

# =========== UTILITIES ===========

def _to_bool(value: Any) -> bool:
    if isinstance(value, bool): return value
    if value is None: return False
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value: return False
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "t", "yes", "y", "1"}: return True
        if v in {"false", "f", "no", "n", "0", ""}: return False
    return bool(value)

def _to_int(value: Any, default: int = 0) -> int:
    if value is None: return default
    try: return int(float(value))
    except (ValueError, TypeError): return default

def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None: return default
    try: return float(value)
    except (ValueError, TypeError): return default

def _normalize_vote_pct(adcom_vote_pct: Any) -> Optional[float]:
    vote = _to_float(adcom_vote_pct, default=None)
    if vote is None: return None
    if vote > 1.0 and vote <= 100.0: return vote / 100.0
    return vote

def classify_tier(probability: float, config: OdinV105Config) -> str:
    if probability >= config.tier1_threshold: return "TIER_1"
    if probability >= config.tier2_threshold: return "TIER_2"
    if probability >= config.tier3_threshold: return "TIER_3"
    return "TIER_4"

def get_ta_risk_tier(ta: str) -> str:
    for tier, areas in TA_RISK_TIERS.items():
        if ta in areas: return tier
    return "UNKNOWN"

# =========== SPONSOR EXPERIENCE LOOKUP ===========
SPONSOR_APPROVALS = {
    "Merck": 50, "MRK": 50, "Pfizer": 60, "PFE": 60, "Eli Lilly": 35, "LLY": 35,
    "AstraZeneca": 40, "AZN": 40, "Bristol-Myers Squibb": 45, "BMY": 45,
    "Johnson & Johnson": 55, "JNJ": 55, "Sanofi": 45, "SNY": 45,
    "Novo Nordisk": 25, "NVO": 25, "Regeneron": 12, "REGN": 12,
    "Amgen": 30, "AMGN": 30, "Biogen": 15, "BIIB": 15, "GSK": 50,
    "Incyte": 5, "INCY": 5, "UCB": 10, "UCBJY": 10, "BioMarin": 6, "BMRN": 6,
    "argenx": 2, "ARGX": 2, "Ultragenyx": 3, "RARE": 3, "Daiichi Sankyo": 15, "DSKYF": 15,
    "Lundbeck": 8, "HLUYY": 8, "Kura Oncology": 0, "KURA": 0, "Viridian Therapeutics": 0, "VRDN": 0,
    "Denali Therapeutics": 0, "DNLI": 0, "Travere Therapeutics": 1, "TVTX": 1,
    "Vera Therapeutics": 0, "VERA": 0, "Capricor Therapeutics": 0, "CAPR": 0,
    "PharmaEssentia": 1, "PHAR": 1, "Nuvalent": 0, "NUVL": 0,
    "INOVIO Pharmaceuticals": 0, "INO": 0, "Summit Therapeutics": 0, "SMMT": 0,
    "Scholar Rock": 0, "SRRK": 0, "Harmony Biosciences": 1, "HRMY": 1,
    "Lexicon Pharmaceuticals": 1, "LXRX": 1,
}

# =========== CORE SCORING ===========

def score_event_v105(
    event: Mapping[str, Any],
    config: Optional[OdinV105Config] = None,
    insider_data: Optional[Dict] = None,
    hiring_data: Optional[Dict] = None,
    lunarcrush_data: Optional[Mapping[str, Any]] = None,
    analysis_date: Optional[datetime] = None,
) -> OdinV105Result:
    
    if config is None: config = OdinV105Config()
    if analysis_date is None: analysis_date = datetime.now()

    # Parse date
    pdufa_date = event.get("catalyst_date") or event.get("date")
    if isinstance(pdufa_date, str):
        try: pdufa_date = datetime.strptime(pdufa_date, "%Y-%m-%d")
        except: pdufa_date = None
            
    is_weekend_pdufa = pdufa_date.weekday() >= 5 if pdufa_date else False
    weekend_note = "Weekend PDUFA: execution-risk only." if is_weekend_pdufa else ""

    # --- LAYER 1: RAW SCORE CALCULATION ---
    prob = float(config.base_approval_rate)
    adjustments: Dict[str, float] = {}
    avoid_signals: List[str] = []

    # (1) Application Type
    app_type_str = str(event.get("application_type") or event.get("applicationText") or "NDA")
    is_pediatric = "PEDIATRIC" in app_type_str.upper()

    if is_pediatric:
        prob += config.snda_pediatric_base_penalty
        adjustments["snda_pediatric_base"] = config.snda_pediatric_base_penalty
        app_type = ApplicationType.SNDA
    elif "SNDA" in app_type_str.upper():
        prob += config.snda_base_penalty
        adjustments["snda_base"] = config.snda_base_penalty
        app_type = ApplicationType.SNDA
    elif "SBLA" in app_type_str.upper():
        prob += config.snda_base_penalty
        adjustments["sbla_base"] = config.snda_base_penalty
        app_type = ApplicationType.SBLA
    elif "BLA" in app_type_str.upper():
        app_type = ApplicationType.BLA
    else:
        app_type = ApplicationType.NDA

    # (2) Designations
    designation_total = 0.0
    designations = event.get("fdaDesignations") or []
    def has_des(key, text): return _to_bool(event.get(key)) or any(text in d.lower() for d in designations)

    if has_des("btd", "breakthrough"):
        designation_total += config.btd_weight; adjustments["S1_btd"] = config.btd_weight
    if has_des("orphan", "orphan"):
        designation_total += config.orphan_weight; adjustments["S2_orphan"] = config.orphan_weight
    if _to_bool(event.get("priority_review")) or any("priority" in d.lower() for d in designations):
        designation_total += config.priority_review_weight; adjustments["S3_priority"] = config.priority_review_weight
    if has_des("fast_track", "fast track"):
        designation_total += config.fast_track_weight; adjustments["S4_fast_track"] = config.fast_track_weight
    if has_des("accelerated_approval", "accelerated"):
        designation_total += config.accelerated_approval_weight; adjustments["S5_accel"] = config.accelerated_approval_weight
    prob += designation_total

    # (3) AdCom
    adcom_adj = 0.0
    if _to_bool(event.get("had_adcom")):
        vote = _normalize_vote_pct(event.get("adcom_vote_pct"))
        if vote is not None:
            if vote >= 0.65: adcom_adj = config.adcom_high_boost
            elif vote >= 0.50: adcom_adj = config.adcom_mid_penalty
            else: adcom_adj = config.adcom_low_penalty
            prob += adcom_adj; adjustments["adcom"] = adcom_adj

    # (4) Prior CRL
    prior_crl_adj = 0.0
    is_resub = "resubmission" in str(event.get("applicationText", "")).lower()
    if _to_bool(event.get("prior_crl")) or is_resub:
        prior_crl_adj = config.prior_crl_penalty
        if _to_int(event.get("resubmission_class")) == 1:
            prior_crl_adj += config.class1_resubmission_boost
        prob += prior_crl_adj; adjustments["prior_crl"] = prior_crl_adj

    # (5) Sponsor
    sponsor_adj = 0.0
    prior_apps = _to_int(event.get("sponsor_prior_approvals", -1), -1)
    if prior_apps < 0:
        prior_apps = SPONSOR_APPROVALS.get(str(event.get("company", "")), -1)
    
    if prior_apps >= config.experienced_threshold:
        sponsor_adj = config.experienced_sponsor_boost; adjustments["sponsor_exp"] = sponsor_adj
    elif prior_apps >= 0 and prior_apps <= config.inexperienced_threshold:
        sponsor_adj = config.inexperienced_sponsor_penalty; adjustments["sponsor_inexp"] = sponsor_adj
    prob += sponsor_adj

    # (6) Manufacturing / CMC (S12)
    mfg_adj = 0.0
    if _to_bool(event.get("manufacturing_risk")): mfg_adj += config.manufacturing_risk_penalty
    if _to_bool(event.get("form_483_issues")): mfg_adj += config.form_483_penalty
    if _to_bool(event.get("ema_cmc_flag")):
        mfg_adj += config.ema_cmc_flag_penalty
        avoid_signals.append(AvoidSignal.EMA_CMC_FLAG.value)
    if _to_bool(event.get("cmc_extension_flag")):
        mfg_adj += config.cmc_extension_penalty
        avoid_signals.append(AvoidSignal.CMC_EXTENSION.value)
    prob += mfg_adj
    adjustments["S12_cmc_risk"] = mfg_adj

    # (7) TA
    ta = str(event.get("therapeutic_area") or event.get("therapeuticArea") or "Other")
    ta_adj = TA_ADJUSTMENTS.get(ta, 0.0) * config.ta_adjustment_weight
    prob += ta_adj; adjustments["S16_ta"] = ta_adj

    # (8) S22 Ped PK
    s22_adj = 0.0
    if _to_bool(event.get("s22_ped_pk_missing")):
        s22_adj = -0.456 # From optimization (approx)
        prob += config.s22_pediatric_pk_penalty # Actually from config
        avoid_signals.append(AvoidSignal.PEDIATRIC_NO_PK.value)
        adjustments["S22_ped_pk"] = config.s22_pediatric_pk_penalty

    # (9) S23 Insider
    s23_adj = 0.0
    s23_risk_level = "NORMAL"
    s23_triggers = []
    if insider_data:
        strength = _to_float(insider_data.get("signal_strength"), 0.0)
        s23_adj = strength * config.s23_insider_weight
        s23_risk_level = insider_data.get("risk_level", "NORMAL")
        s23_triggers = insider_data.get("triggers_fired", [])
        prob += s23_adj; adjustments["S23_insider"] = s23_adj
        if s23_risk_level == "CRITICAL": avoid_signals.append(AvoidSignal.INSIDER_CRITICAL.value)

    # (10) S6 Hiring
    s6_adj = 0.0
    s6_signal = "NEUTRAL"
    s6_rationale = ""
    if hiring_data:
        strength = _to_float(hiring_data.get("signal_strength"), 0.0)
        s6_adj = strength * config.s6_hiring_weight
        s6_signal = hiring_data.get("signal", "NEUTRAL")
        s6_rationale = hiring_data.get("rationale", "")
        prob += s6_adj; adjustments["S6_hiring"] = s6_adj
        if pdufa_date and app_type == ApplicationType.NDA and s6_signal == "VOID":
             if (pdufa_date - analysis_date).days < 180:
                 avoid_signals.append(AvoidSignal.HIRING_VOID_NDA.value)

    # (11) Social
    social_adj = 0.0
    if lunarcrush_data:
        score = _to_float(lunarcrush_data.get("social_sentiment_score"), 0.0)
        social_adj = score * config.social_weight
        prob += social_adj; adjustments["social"] = social_adj

    # Clamp Raw Score
    raw_score = max(config.clamp_min, min(config.clamp_max, prob))

    # --- LAYER 2: CALIBRATION ---
    final_prob = raw_score
    if CALIBRATOR:
        try:
            # Reshape for sklearn [samples, features]
            final_prob = float(CALIBRATOR.predict([[raw_score]])[0])
        except Exception as e:
            # Fallback to raw if calibrator fails
            final_prob = raw_score
    
    # --- LAYER 3: TIERING ---
    tier = classify_tier(final_prob, config)
    ta_risk = get_ta_risk_tier(ta)

    # Trading Logic
    is_hard_avoid = len(avoid_signals) > 0
    if is_hard_avoid: action = "AVOID_POSITION"
    elif tier == "TIER_4": action = "NO_POSITION"
    elif tier == "TIER_3": action = "SMALL_POSITION_EARLY_EXIT"
    elif s23_risk_level == "ELEVATED": action = "REDUCED_SIZE_EARLY_EXIT"
    else: action = "STANDARD_POSITION"

    if is_pediatric: exit_window, runner = "T-10", "0%"
    elif s23_risk_level in ["HIGH_RISK", "CRITICAL"]: exit_window, runner = "T-10", "0%"
    elif s23_risk_level == "ELEVATED": exit_window, runner = "T-7", "10%"
    else: exit_window, runner = "T-5 to T-7", "20%"

    return OdinV105Result(
        ticker=str(event.get("ticker", "UNKNOWN")),
        event_id=str(event.get("event_id") or "UNKNOWN"),
        probability=round(final_prob, 4),
        raw_score=round(raw_score, 4),
        tier=tier,
        base_rate=config.base_approval_rate,
        designation_total=round(designation_total, 4),
        adcom_adjustment=round(adcom_adj, 4),
        prior_crl_adjustment=round(prior_crl_adj, 4),
        sponsor_adjustment=round(sponsor_adj, 4),
        manufacturing_adjustment=round(mfg_adj, 4),
        ta_adjustment=round(ta_adj, 4),
        s23_insider_selling=round(s23_adj, 4),
        s23_risk_level=s23_risk_level,
        s23_triggers=s23_triggers,
        s6_commercial_hiring=round(s6_adj, 4),
        s6_signal=s6_signal,
        s6_rationale=s6_rationale,
        s12_cmc_risk=round(mfg_adj, 4),
        s22_pediatric_pk=round(s22_adj, 4),
        social_total=round(social_adj, 4),
        s21_capped=False,
        avoid_signals=avoid_signals,
        is_hard_avoid=is_hard_avoid,
        is_weekend_pdufa=is_weekend_pdufa,
        weekend_execution_note=weekend_note,
        recommended_action=action,
        exit_window=exit_window,
        runner_position=runner,
        ta_risk_tier=ta_risk,
        adjustments_breakdown=adjustments,
    )

def score_pdufa_event(event, config=None, lunarcrush_data=None, insider_data=None, hiring_data=None):
    """Convenience wrapper."""
    result = score_event_v105(event, config, insider_data, hiring_data, lunarcrush_data)
    ta = str(event.get("therapeutic_area") or "Other")
    return {
        "version": "10.5",
        "probability": result.probability,
        "raw_score": result.raw_score,
        "tier": result.tier,
        "ta_risk_tier": result.ta_risk_tier,
        "therapeutic_area": ta,
        "signals": result.adjustments_breakdown,
        "avoid_signals": result.avoid_signals,
        "is_hard_avoid": result.is_hard_avoid,
        "recommended_action": result.recommended_action,
        "s6_hiring": result.s6_signal,
        "s23_insider": result.s23_risk_level,
    }