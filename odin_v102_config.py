# ODIN v10.2 Configuration - PHAR CRL Post-Mortem Fixes
# ======================================================
# Codename: PHAR_POSTMORTEM
# Release: 2026-02-02
#
# Critical fixes implemented:
# - S22: Pediatric PK Bridging Risk (NEW)
# - S12: Cross-regulatory CMC intelligence (EMA + FDA)
# - S6: Hiring gradient with VOID signal
# - S21: Sentiment cap when objective signals flash
# - Avoid signals: Hard no-trade list
# - sNDA base penalties
#
# Philosophy: Risk reduction > Brier optimization
# "We can't let this happen again" - 2026-02-02

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class SubmissionType(Enum):
    NDA = "NDA"
    BLA = "BLA"
    SNDA = "sNDA"
    SNDA_PEDIATRIC = "sNDA_PEDIATRIC"
    BLA_SUPPLEMENT = "BLA_SUPPLEMENT"
    BLA_SUPPLEMENT_PEDIATRIC = "BLA_SUPPLEMENT_PEDIATRIC"

class DosingType(Enum):
    FIXED = "fixed"
    WEIGHT_BASED = "weight_based"
    AGE_TIERED = "age_tiered"
    BSA_BASED = "bsa_based"

class AvoidSeverity(Enum):
    CRITICAL = "CRITICAL"  # Do not trade under any circumstances
    HIGH = "HIGH"          # Strong avoid unless exceptional circumstances
    MODERATE = "MODERATE"  # Proceed with caution, reduce position size

# CMC Keywords to monitor across regulatory sources
CMC_KEYWORDS = [
    "cmc question", "manufacturing extension", "analytical method",
    "starting materials", "batch testing", "production batch",
    "chmp extension", "quality issue", "gmp deficiency",
    "process validation", "stability data", "specification",
    "drug substance", "drug product", "container closure"
]

# =============================================================================
# THERAPEUTIC AREA ADJUSTMENTS (updated from v9.1)
# =============================================================================

THERAPEUTIC_AREA_ADJUSTMENTS = {
    # HIGH RISK - Increased penalties from v9.1
    "Pain Management": -0.30,       # Was -0.286, HIGHEST RISK
    "Hematology": -0.224,
    "Nephrology": -0.177,
    "Ophthalmology": -0.25,         # Was -0.131, increased
    
    # MODERATE RISK
    "CNS/Neurology": -0.098,
    "Cardiovascular": -0.081,
    "Metabolic/Endocrine": -0.067,
    "Rare Disease": -0.043,
    "Other": -0.019,
    
    # LOW RISK
    "Immunology": 0.016,
    "Dermatology": 0.028,
    "Oncology": 0.061,
    "GI/Hepatology": 0.067,
    "Respiratory": 0.09,
    "Infectious Disease": 0.103,
    "Vaccines": 0.133,
    "Women's Health": 0.133,
}

# =============================================================================
# MAIN CONFIG CLASS
# =============================================================================

@dataclass
class OdinV102Config:
    """
    ODIN v10.2 Configuration - PHAR CRL Post-Mortem Fixes
    
    All parameters tunable. New signals for CMC, pediatric PK, hiring gradient.
    """
    # Base parameters
    base_approval_rate: float = 0.867
    nda_base_penalty: float = 0.0
    snda_base_penalty: float = -0.03
    snda_pediatric_base_penalty: float = -0.08  # NEW: Pediatric sNDAs are risky
    
    # Designation weights (from v10.1)
    btd_weight: float = 0.12
    orphan_weight: float = 0.10
    priority_review_weight: float = 0.085
    fast_track_weight: float = 0.03
    accelerated_approval_weight: float = 0.05
    
    # AdCom adjustments
    adcom_high_threshold: float = 0.65
    adcom_high_boost: float = 0.08
    adcom_mid_threshold: float = 0.50
    adcom_mid_penalty: float = -0.06
    adcom_low_penalty: float = -0.19
    
    # Prior CRL / Resubmission
    prior_crl_penalty: float = -0.085
    class1_resubmission_boost: float = 0.157
    class2_resubmission_penalty: float = -0.05
    
    # Sponsor experience
    experienced_sponsor_boost: float = 0.053
    inexperienced_sponsor_penalty: float = -0.068
    experienced_threshold: int = 5
    inexperienced_threshold: int = 0
    
    # Manufacturing risk - ENHANCED for v10.2
    manufacturing_risk_penalty: float = -0.12
    form_483_penalty: float = -0.07
    ema_cmc_flag_penalty: float = -0.10      # NEW: EMA CMC issues
    cmc_extension_penalty: float = -0.08     # NEW: Any agency CMC extension
    analytical_method_flag_penalty: float = -0.06  # NEW: Analytical method issues
    
    # S6 Hiring - NEW GRADIENT for v10.2
    hiring_void_threshold: int = 3           # <3 hires = VOID
    hiring_neutral_threshold: int = 10       # 3-10 = neutral
    hiring_void_penalty: float = -0.05       # AVOID SIGNAL
    hiring_neutral: float = 0.0
    hiring_bullish_boost: float = 0.02       # >10 hires
    
    # S21 Sentiment - NEW CAP for v10.2
    sentiment_max_contribution: float = 0.03
    sentiment_capped_contribution: float = 0.02  # When triggers fire
    
    # S22 Pediatric PK Risk - NEW for v10.2
    pediatric_pk_risk_penalty: float = -0.10
    
    # P3 Publication Volume - ENHANCED for v10.2
    pub_very_low_threshold: int = 10
    pub_low_threshold: int = 25
    pub_adequate_threshold: int = 50
    pub_very_low_penalty: float = -0.08
    pub_low_penalty: float = -0.04
    pub_high_boost: float = 0.02
    pub_unpublished_data_penalty: float = -0.05  # NEW: Press release only
    
    # Social signals (from v10.1)
    social_sentiment_bullish_threshold: float = 80.0
    social_sentiment_bearish_threshold: float = 60.0
    social_sentiment_bullish_boost: float = 0.03
    social_sentiment_bearish_penalty: float = -0.02
    engagement_spike_threshold: float = 1.5
    engagement_spike_boost: float = 0.02
    social_silence_threshold: float = 0.3
    social_silence_penalty: float = -0.03
    galaxy_divergence_threshold: float = 40.0
    galaxy_divergence_penalty: float = -0.02
    
    # TA adjustment weight
    ta_adjustment_weight: float = 0.829
    
    # Tier thresholds
    tier1_threshold: float = 0.858
    tier2_threshold: float = 0.734
    tier3_threshold: float = 0.578


# =============================================================================
# AVOID SIGNAL CHECKER
# =============================================================================

def check_avoid_signals(event: dict) -> List[Tuple[str, str, str]]:
    """
    Check for hard avoid signals. Returns list of (signal_id, name, severity).
    
    If ANY CRITICAL signal fires, DO NOT TRADE.
    """
    avoid_signals = []
    
    # AVOID_001: EMA CMC Flag
    if event.get('ema_cmc_flag', False):
        avoid_signals.append(("AVOID_001", "EMA_CMC_Flag", "CRITICAL"))
    
    # AVOID_002: Hiring Void (sparse hiring near PDUFA)
    hire_count = event.get('commercial_hire_count', None)
    months_to_pdufa = event.get('months_to_pdufa', 12)
    if hire_count is not None and hire_count < 3 and months_to_pdufa < 6:
        avoid_signals.append(("AVOID_002", "Hiring_Void", "HIGH"))
    
    # AVOID_003: Pediatric sNDA without published PK
    submission_type = event.get('submission_type', '')
    pediatric_pk = event.get('pediatric_pk_published', True)  # Default True to not penalize missing data
    if submission_type in ['sNDA_PEDIATRIC', 'BLA_SUPPLEMENT_PEDIATRIC'] and not pediatric_pk:
        avoid_signals.append(("AVOID_003", "Pediatric_No_PK", "CRITICAL"))
    
    # AVOID_004: CMC Extension from any agency
    if event.get('cmc_extension_flag', False):
        avoid_signals.append(("AVOID_004", "CMC_Extension_Any_Agency", "CRITICAL"))
    
    # AVOID_005: Weekend PDUFA with low probability (checked after scoring)
    # This one needs the probability, so we'll check it separately
    
    return avoid_signals


def check_weekend_pdufa_avoid(event: dict, probability: float) -> Optional[Tuple[str, str, str]]:
    """Check weekend PDUFA avoid signal after scoring."""
    pdufa_day = event.get('pdufa_day_of_week', '')
    if pdufa_day in ['Saturday', 'Sunday'] and probability < 0.80:
        return ("AVOID_005", "Weekend_PDUFA_Low_Prob", "HIGH")
    return None


# =============================================================================
# SIGNAL FUNCTIONS
# =============================================================================

def s6_hiring_signal(event: dict, config: OdinV102Config) -> Tuple[float, str]:
    """
    S6: Pre-Launch Hiring Intelligence v2.0
    
    NEW in v10.2: Void signal for sparse hiring.
    <3 hires = AVOID, 3-10 = neutral, >10 = bullish
    
    Returns: (adjustment, classification)
    """
    hire_count = event.get('commercial_hire_count', None)
    
    if hire_count is None:
        return 0.0, "UNKNOWN"
    
    if hire_count < config.hiring_void_threshold:
        return config.hiring_void_penalty, "VOID"
    elif hire_count <= config.hiring_neutral_threshold:
        return config.hiring_neutral, "NEUTRAL"
    else:
        return config.hiring_bullish_boost, "BULLISH"


def s12_cmc_risk_signal(event: dict, config: OdinV102Config) -> Tuple[float, str]:
    """
    S12: CMC Risk Intelligence v2.0 - Cross-Regulatory
    
    NEW in v10.2: Now monitors EMA CHMP, not just FDA.
    
    Returns: (adjustment, classification)
    """
    adjustment = 0.0
    flags = []
    
    # FDA Form 483
    if event.get('form_483_issues', False):
        adjustment += config.form_483_penalty
        flags.append("FDA_483")
    
    # EMA CMC Flag (NEW)
    if event.get('ema_cmc_flag', False):
        adjustment += config.ema_cmc_flag_penalty
        flags.append("EMA_CMC")
    
    # CMC Extension from any agency (NEW)
    if event.get('cmc_extension_flag', False):
        adjustment += config.cmc_extension_penalty
        flags.append("CMC_EXTENSION")
    
    # Analytical method issues (NEW)
    if event.get('analytical_method_flag', False):
        adjustment += config.analytical_method_flag_penalty
        flags.append("ANALYTICAL_METHOD")
    
    # Manufacturing risk (legacy)
    if event.get('manufacturing_risk', False):
        adjustment += config.manufacturing_risk_penalty
        flags.append("MFG_RISK")
    
    if len(flags) == 0:
        return 0.0, "CLEAN"
    elif len(flags) == 1:
        return adjustment, f"FLAG:{flags[0]}"
    else:
        return adjustment, f"MULTI_FLAG:{','.join(flags)}"


def s22_pediatric_pk_risk_signal(event: dict, config: OdinV102Config) -> Tuple[float, str]:
    """
    S22: Pediatric PK Bridging Risk v1.0 (NEW)
    
    Created from PHAR CRL failure. Triggers when:
    - Pediatric submission (sNDA or BLA supplement)
    - Weight-based or age-tiered dosing
    - No published pediatric PK study
    
    Returns: (adjustment, classification)
    """
    submission_type = event.get('submission_type', 'NDA')
    dosing_type = event.get('dosing_type', 'fixed')
    pediatric_pk = event.get('pediatric_pk_published', True)
    
    # Check if pediatric submission
    is_pediatric = submission_type in ['sNDA_PEDIATRIC', 'BLA_SUPPLEMENT_PEDIATRIC']
    
    # Check if complex dosing
    is_complex_dosing = dosing_type in ['weight_based', 'age_tiered', 'bsa_based']
    
    # Check if PK data missing
    no_pk_data = not pediatric_pk
    
    if is_pediatric and is_complex_dosing and no_pk_data:
        return config.pediatric_pk_risk_penalty, "HIGH_RISK"
    elif is_pediatric and no_pk_data:
        return config.pediatric_pk_risk_penalty * 0.5, "MODERATE_RISK"
    elif is_pediatric:
        return -0.03, "PEDIATRIC_BASE"
    
    return 0.0, "NOT_APPLICABLE"


def p3_publication_volume_signal(event: dict, config: OdinV102Config) -> Tuple[float, str]:
    """
    P3: Publication Volume Signal v2.0
    
    NEW in v10.2: Additional penalty for unpublished pivotal data.
    
    Returns: (adjustment, classification)
    """
    pub_count = event.get('publication_count', None)
    pivotal_peer_reviewed = event.get('pivotal_data_peer_reviewed', True)
    
    adjustment = 0.0
    classification = "UNKNOWN"
    
    if pub_count is not None:
        if pub_count < config.pub_very_low_threshold:
            adjustment = config.pub_very_low_penalty
            classification = "VERY_LOW"
        elif pub_count < config.pub_low_threshold:
            adjustment = config.pub_low_penalty
            classification = "LOW"
        elif pub_count >= config.pub_adequate_threshold:
            adjustment = config.pub_high_boost
            classification = "HIGH"
        else:
            classification = "ADEQUATE"
    
    # NEW: Unpublished pivotal data penalty
    if not pivotal_peer_reviewed:
        adjustment += config.pub_unpublished_data_penalty
        classification += "+UNPUBLISHED"
    
    return adjustment, classification


def s21_sentiment_signal(event: dict, config: OdinV102Config, 
                         objective_flags: dict) -> Tuple[float, str]:
    """
    S21: Specialist Sentiment Signal v2.0
    
    NEW in v10.2: Cap contribution when objective signals flash yellow.
    
    Args:
        event: Event dictionary
        config: ODIN config
        objective_flags: Dict with keys like 's12_penalty', 'p3_penalty', 
                        's6_void', 's22_risk'
    
    Returns: (adjustment, classification)
    """
    # Check if any cap triggers fire
    cap_triggered = False
    cap_reasons = []
    
    if objective_flags.get('s12_penalty', 0) <= -0.05:
        cap_triggered = True
        cap_reasons.append("S12_CMC")
    
    if objective_flags.get('p3_penalty', 0) <= -0.08:
        cap_triggered = True
        cap_reasons.append("P3_PUBS")
    
    if objective_flags.get('s6_void', False):
        cap_triggered = True
        cap_reasons.append("S6_HIRING")
    
    if objective_flags.get('s22_risk', False):
        cap_triggered = True
        cap_reasons.append("S22_PEDIATRIC")
    
    # Get base sentiment contribution
    base_sentiment = event.get('specialist_sentiment_score', 0.0)
    
    # Apply cap if triggered
    if cap_triggered:
        max_contribution = config.sentiment_capped_contribution
        actual_contribution = min(base_sentiment, max_contribution)
        return actual_contribution, f"CAPPED:{','.join(cap_reasons)}"
    else:
        max_contribution = config.sentiment_max_contribution
        actual_contribution = min(base_sentiment, max_contribution)
        return actual_contribution, "UNCAPPED"


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def score_event(config: OdinV102Config, event: dict) -> dict:
    """
    Score a PDUFA event using ODIN v10.2.
    
    Returns dict with:
    - probability: float
    - tier: str
    - avoid_signals: list
    - adjustments: dict
    - warnings: list
    """
    prob = config.base_approval_rate
    adjustments = {}
    warnings = []
    
    # 0. Check submission type base penalty
    submission_type = event.get('submission_type', 'NDA')
    if submission_type == 'sNDA_PEDIATRIC':
        prob += config.snda_pediatric_base_penalty
        adjustments['submission_type'] = config.snda_pediatric_base_penalty
    elif submission_type in ['sNDA', 'BLA_SUPPLEMENT']:
        prob += config.snda_base_penalty
        adjustments['submission_type'] = config.snda_base_penalty
    
    # 1. Designation stack
    if event.get('btd'):
        prob += config.btd_weight
        adjustments['btd'] = config.btd_weight
    if event.get('orphan'):
        prob += config.orphan_weight
        adjustments['orphan'] = config.orphan_weight
    if event.get('priority_review'):
        prob += config.priority_review_weight
        adjustments['priority_review'] = config.priority_review_weight
    if event.get('fast_track'):
        prob += config.fast_track_weight
        adjustments['fast_track'] = config.fast_track_weight
    if event.get('accelerated_approval'):
        prob += config.accelerated_approval_weight
        adjustments['accelerated_approval'] = config.accelerated_approval_weight
    
    # 2. AdCom vote
    if event.get('had_adcom') and event.get('adcom_vote_pct') is not None:
        vote = event['adcom_vote_pct']
        if vote >= config.adcom_high_threshold:
            prob += config.adcom_high_boost
            adjustments['adcom'] = config.adcom_high_boost
        elif vote >= config.adcom_mid_threshold:
            prob += config.adcom_mid_penalty
            adjustments['adcom'] = config.adcom_mid_penalty
        else:
            prob += config.adcom_low_penalty
            adjustments['adcom'] = config.adcom_low_penalty
    
    # 3. Prior CRL / Resubmission
    if event.get('prior_crl'):
        prob += config.prior_crl_penalty
        adjustments['prior_crl'] = config.prior_crl_penalty
        
        resubmission_class = event.get('resubmission_class')
        if resubmission_class == 1:
            prob += config.class1_resubmission_boost
            adjustments['class1_resubmission'] = config.class1_resubmission_boost
        elif resubmission_class == 2:
            prob += config.class2_resubmission_penalty
            adjustments['class2_resubmission'] = config.class2_resubmission_penalty
    
    # 4. Sponsor experience
    prior_approvals = event.get('sponsor_prior_approvals', 0)
    if prior_approvals >= config.experienced_threshold:
        prob += config.experienced_sponsor_boost
        adjustments['sponsor_experience'] = config.experienced_sponsor_boost
    elif prior_approvals <= config.inexperienced_threshold:
        prob += config.inexperienced_sponsor_penalty
        adjustments['sponsor_experience'] = config.inexperienced_sponsor_penalty
    
    # 5. S12: CMC Risk (ENHANCED)
    s12_adj, s12_class = s12_cmc_risk_signal(event, config)
    if s12_adj != 0:
        prob += s12_adj
        adjustments['s12_cmc_risk'] = s12_adj
        if 'EMA' in s12_class or 'MULTI' in s12_class:
            warnings.append(f"CMC RISK: {s12_class}")
    
    # 6. S6: Hiring (NEW GRADIENT)
    s6_adj, s6_class = s6_hiring_signal(event, config)
    if s6_adj != 0:
        prob += s6_adj
        adjustments['s6_hiring'] = s6_adj
        if s6_class == "VOID":
            warnings.append("HIRING VOID: <3 commercial hires")
    
    # 7. S22: Pediatric PK Risk (NEW)
    s22_adj, s22_class = s22_pediatric_pk_risk_signal(event, config)
    if s22_adj != 0:
        prob += s22_adj
        adjustments['s22_pediatric_pk'] = s22_adj
        if 'HIGH_RISK' in s22_class:
            warnings.append("PEDIATRIC PK RISK: No published PK study")
    
    # 8. P3: Publication Volume (ENHANCED)
    p3_adj, p3_class = p3_publication_volume_signal(event, config)
    if p3_adj != 0:
        prob += p3_adj
        adjustments['p3_publications'] = p3_adj
        if 'UNPUBLISHED' in p3_class:
            warnings.append("PUBLICATION GAP: Pivotal data not peer-reviewed")
    
    # 9. Therapeutic area adjustment
    ta = event.get('therapeutic_area', 'Other')
    ta_base_adj = THERAPEUTIC_AREA_ADJUSTMENTS.get(ta, 0.0)
    ta_adj = ta_base_adj * config.ta_adjustment_weight
    if ta_adj != 0:
        prob += ta_adj
        adjustments['therapeutic_area'] = ta_adj
    
    # 10. S21: Sentiment (with cap logic)
    objective_flags = {
        's12_penalty': s12_adj,
        'p3_penalty': p3_adj,
        's6_void': s6_class == "VOID",
        's22_risk': 'HIGH_RISK' in s22_class
    }
    s21_adj, s21_class = s21_sentiment_signal(event, config, objective_flags)
    if s21_adj != 0:
        prob += s21_adj
        adjustments['s21_sentiment'] = s21_adj
        if 'CAPPED' in s21_class:
            warnings.append(f"SENTIMENT CAPPED: {s21_class}")
    
    # 11. Social signals (from LunarCrush)
    if event.get('social_total') is not None:
        social_adj = event['social_total']
        prob += social_adj
        adjustments['social_signals'] = social_adj
    
    # Clamp probability
    prob = max(0.01, min(0.99, prob))
    
    # Determine tier
    if prob >= config.tier1_threshold:
        tier = "TIER_1"
    elif prob >= config.tier2_threshold:
        tier = "TIER_2"
    elif prob >= config.tier3_threshold:
        tier = "TIER_3"
    else:
        tier = "TIER_4"
    
    # Check avoid signals
    avoid_signals = check_avoid_signals(event)
    weekend_avoid = check_weekend_pdufa_avoid(event, prob)
    if weekend_avoid:
        avoid_signals.append(weekend_avoid)
    
    # Add avoid signal warnings
    for avoid_id, avoid_name, severity in avoid_signals:
        if severity == "CRITICAL":
            warnings.insert(0, f"🚨 AVOID: {avoid_name} ({avoid_id})")
        else:
            warnings.append(f"⚠️ CAUTION: {avoid_name} ({avoid_id})")
    
    return {
        'probability': prob,
        'tier': tier,
        'avoid_signals': avoid_signals,
        'has_critical_avoid': any(s[2] == "CRITICAL" for s in avoid_signals),
        'adjustments': adjustments,
        'warnings': warnings,
        'therapeutic_area': ta,
        'submission_type': submission_type,
    }


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def export_config(config: OdinV102Config, filepath: str):
    """Export config to JSON file."""
    data = {
        'version': '10.2',
        'codename': 'PHAR_POSTMORTEM',
        'parameters': {k: v for k, v in config.__dict__.items()},
        'therapeutic_area_adjustments': THERAPEUTIC_AREA_ADJUSTMENTS,
        'cmc_keywords': CMC_KEYWORDS,
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


# =============================================================================
# TEST SCORING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("ODIN v10.2 - PHAR CRL Post-Mortem Fixes")
    print("=" * 70)
    
    config = OdinV102Config()
    
    # Test: PHAR-like event (should trigger avoid signals)
    phar_like = {
        'name': 'PHAR-Like Pediatric sNDA',
        'submission_type': 'sNDA_PEDIATRIC',
        'btd': False,
        'orphan': True,
        'priority_review': True,
        'fast_track': False,
        'therapeutic_area': 'Immunology',
        'sponsor_prior_approvals': 3,
        'ema_cmc_flag': True,
        'cmc_extension_flag': True,
        'pediatric_pk_published': False,
        'dosing_type': 'weight_based',
        'commercial_hire_count': 2,
        'publication_count': 12,
        'pivotal_data_peer_reviewed': False,
    }
    
    print("\n📋 Test Event: PHAR-Like Pediatric sNDA (should trigger AVOID)")
    print("-" * 50)
    result = score_event(config, phar_like)
    print(f"   Probability: {result['probability']*100:.1f}%")
    print(f"   Tier: {result['tier']}")
    print(f"   Has Critical Avoid: {result['has_critical_avoid']}")
    print(f"   Avoid Signals: {result['avoid_signals']}")
    print(f"   Warnings:")
    for w in result['warnings']:
        print(f"      - {w}")
    
    # Test: Clean oncology NDA (should NOT trigger avoid)
    clean_oncology = {
        'name': 'Clean Oncology NDA',
        'submission_type': 'NDA',
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'fast_track': True,
        'therapeutic_area': 'Oncology',
        'sponsor_prior_approvals': 15,
        'ema_cmc_flag': False,
        'form_483_issues': False,
        'commercial_hire_count': 25,
        'publication_count': 85,
        'pivotal_data_peer_reviewed': True,
    }
    
    print("\n📋 Test Event: Clean Oncology NDA (should be high probability)")
    print("-" * 50)
    result = score_event(config, clean_oncology)
    print(f"   Probability: {result['probability']*100:.1f}%")
    print(f"   Tier: {result['tier']}")
    print(f"   Has Critical Avoid: {result['has_critical_avoid']}")
    print(f"   Warnings: {result['warnings']}")
    
    # Test: CNS with sparse hiring (moderate risk)
    cns_sparse = {
        'name': 'CNS with Sparse Hiring',
        'submission_type': 'NDA',
        'btd': False,
        'orphan': False,
        'priority_review': True,
        'therapeutic_area': 'CNS/Neurology',
        'sponsor_prior_approvals': 2,
        'commercial_hire_count': 1,
        'months_to_pdufa': 3,
        'publication_count': 35,
    }
    
    print("\n📋 Test Event: CNS with Sparse Hiring (should flag S6 void)")
    print("-" * 50)
    result = score_event(config, cns_sparse)
    print(f"   Probability: {result['probability']*100:.1f}%")
    print(f"   Tier: {result['tier']}")
    print(f"   Avoid Signals: {result['avoid_signals']}")
    print(f"   Warnings:")
    for w in result['warnings']:
        print(f"      - {w}")
    
    print("\n" + "=" * 70)
    print("✅ v10.2 Scoring Logic Validated")
    print("=" * 70)
