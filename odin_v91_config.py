# ODIN v9.1 Configuration - Indication Difficulty Adjustments
# ============================================================
# Improvement #1: Historical TA-specific approval rate adjustments
# Ready for GPU billion-parameter optimization
#
# Key insight: Pain Management, Hematology, Nephrology, Ophthalmology
# have CRL rates 2-5x higher than baseline. This signal was missing.

import json
from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np

# =============================================================================
# THERAPEUTIC AREA DIFFICULTY ADJUSTMENTS (from 1,349 historical events)
# =============================================================================
# Baseline approval rate: 86.66%
# Adjustments are additive to base probability

THERAPEUTIC_AREA_ADJUSTMENTS = {
    # HIGH RISK (CRL rate > 25%)
    "Pain Management": -0.286,      # 58.1% approval, 41.9% CRL - HIGHEST RISK
    "Hematology": -0.224,           # 64.3% approval, 35.7% CRL
    "Nephrology": -0.177,           # 69.0% approval, 31.0% CRL
    "Ophthalmology": -0.131,        # 73.5% approval, 26.5% CRL
    
    # MODERATE RISK (CRL rate 15-25%)
    "CNS/Neurology": -0.098,        # 76.8% approval, 23.2% CRL
    "Cardiovascular": -0.081,       # 78.6% approval, 21.4% CRL
    "Metabolic/Endocrine": -0.067,  # 80.0% approval, 20.0% CRL
    "Rare Disease": -0.043,         # 82.4% approval, 17.6% CRL
    "Other": -0.019,                # 84.8% approval, 15.2% CRL
    
    # LOW RISK (CRL rate < 15%)
    "Immunology": 0.016,            # 88.2% approval, 11.8% CRL
    "Dermatology": 0.028,           # 89.5% approval, 10.5% CRL
    "Oncology": 0.061,              # 92.8% approval, 7.2% CRL
    "GI/Hepatology": 0.067,         # 93.3% approval, 6.7% CRL
    "Respiratory": 0.090,           # 95.7% approval, 4.3% CRL
    "Infectious Disease": 0.103,    # 97.0% approval, 3.0% CRL
    "Vaccines": 0.133,              # 100% approval - LOWEST RISK
    "Women's Health": 0.133,        # 100% approval
}

# Risk tier classification for reporting
TA_RISK_TIERS = {
    "HIGH_RISK": ["Pain Management", "Hematology", "Nephrology", "Ophthalmology"],
    "MOD_RISK": ["CNS/Neurology", "Cardiovascular", "Metabolic/Endocrine", "Rare Disease", "Other"],
    "LOW_RISK": ["Immunology", "Dermatology", "Oncology", "GI/Hepatology", "Respiratory", 
                 "Infectious Disease", "Vaccines", "Women's Health"]
}

# =============================================================================
# OPTIMIZABLE WEIGHT PARAMETERS (for GPU scan)
# =============================================================================

@dataclass
class OdinV91Config:
    """
    ODIN v9.1 Configuration with indication difficulty adjustments.
    All weights are optimizable via GPU parameter scan.
    """
    # Base parameters
    base_approval_rate: float = 0.867
    
    # Designation weights (from v8.11 champion)
    btd_weight: float = 0.06
    orphan_weight: float = 0.04
    priority_review_weight: float = 0.05
    fast_track_weight: float = 0.02
    accelerated_approval_weight: float = 0.03
    
    # AdCom adjustments
    adcom_high_threshold: float = 0.65
    adcom_high_boost: float = 0.08
    adcom_mid_threshold: float = 0.50
    adcom_mid_penalty: float = -0.05
    adcom_low_penalty: float = -0.15
    
    # Prior CRL / Resubmission
    prior_crl_penalty: float = -0.10
    class1_resubmission_boost: float = 0.15
    class2_resubmission_penalty: float = -0.05
    
    # Sponsor experience
    experienced_sponsor_boost: float = 0.05  # >5 approvals
    inexperienced_sponsor_penalty: float = -0.08  # 0 approvals
    
    # Manufacturing risk
    manufacturing_risk_penalty: float = -0.12
    form_483_penalty: float = -0.08
    
    # Modality adjustments
    modality_adjustments: Dict[str, float] = field(default_factory=lambda: {
        "Small Molecule": 0.0,      # baseline (15.1% CRL)
        "Antibody": 0.02,           # 11.9% CRL
        "Cell/Gene Therapy": -0.08, # 7.0% CRL but high manufacturing risk
        "RNA Therapy": -0.03,       # 7.3% CRL but novel
        "Peptide": 0.0,             # 12.0% CRL
        "Vaccine": 0.05,            # 0% CRL historically
        "ADC": 0.0,                 # limited data
    })
    
    # NEW: Therapeutic area difficulty adjustments
    # This is the key improvement from HINT analysis
    ta_adjustment_weight: float = 1.0  # Multiplier for TA adjustments (optimizable)
    therapeutic_area_adjustments: Dict[str, float] = field(
        default_factory=lambda: THERAPEUTIC_AREA_ADJUSTMENTS.copy()
    )
    
    # Tier thresholds (for classification)
    tier1_threshold: float = 0.85
    tier2_threshold: float = 0.70
    tier3_threshold: float = 0.55


def score_event(config: OdinV91Config, event: dict) -> dict:
    """
    Score a PDUFA event using ODIN v9.1 with indication difficulty.
    
    Args:
        config: OdinV91Config with tunable parameters
        event: Dict with event features (btd, orphan, therapeutic_area, etc.)
    
    Returns:
        Dict with probability, tier, adjustments breakdown
    """
    prob = config.base_approval_rate
    adjustments = {}
    
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
    if prior_approvals >= 5:
        prob += config.experienced_sponsor_boost
        adjustments['sponsor_experience'] = config.experienced_sponsor_boost
    elif prior_approvals == 0:
        prob += config.inexperienced_sponsor_penalty
        adjustments['sponsor_experience'] = config.inexperienced_sponsor_penalty
    
    # 5. Manufacturing risk
    if event.get('manufacturing_risk'):
        prob += config.manufacturing_risk_penalty
        adjustments['manufacturing_risk'] = config.manufacturing_risk_penalty
    if event.get('form_483_issues'):
        prob += config.form_483_penalty
        adjustments['form_483'] = config.form_483_penalty
    
    # 6. Modality adjustment
    modality = event.get('modality', 'Small Molecule')
    mod_adj = config.modality_adjustments.get(modality, 0.0)
    if mod_adj != 0:
        prob += mod_adj
        adjustments['modality'] = mod_adj
    
    # 7. NEW: Therapeutic area difficulty adjustment
    ta = event.get('therapeutic_area', 'Other')
    ta_base_adj = config.therapeutic_area_adjustments.get(ta, 0.0)
    ta_adj = ta_base_adj * config.ta_adjustment_weight
    if ta_adj != 0:
        prob += ta_adj
        adjustments['therapeutic_area'] = ta_adj
    
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
    
    # Determine TA risk tier
    ta_risk = "UNKNOWN"
    for risk_level, tas in TA_RISK_TIERS.items():
        if ta in tas:
            ta_risk = risk_level
            break
    
    return {
        'probability': prob,
        'tier': tier,
        'ta_risk_tier': ta_risk,
        'adjustments': adjustments,
        'therapeutic_area': ta,
        'modality': modality
    }


def batch_score(config: OdinV91Config, df) -> 'pd.DataFrame':
    """
    Score entire DataFrame with ODIN v9.1.
    
    Returns DataFrame with added columns:
    - odin_v91_probability
    - odin_v91_tier
    - odin_v91_ta_risk
    """
    import pandas as pd
    
    results = []
    for _, row in df.iterrows():
        event = row.to_dict()
        result = score_event(config, event)
        results.append({
            'odin_v91_probability': result['probability'],
            'odin_v91_tier': result['tier'],
            'odin_v91_ta_risk': result['ta_risk_tier'],
        })
    
    result_df = pd.DataFrame(results)
    return pd.concat([df.reset_index(drop=True), result_df], axis=1)


# =============================================================================
# GPU OPTIMIZATION PARAMETER BOUNDS
# =============================================================================
# For CuPy/Optuna billion-parameter scan

PARAMETER_BOUNDS = {
    # Designation weights (0 to 0.15)
    'btd_weight': (0.0, 0.15),
    'orphan_weight': (0.0, 0.10),
    'priority_review_weight': (0.0, 0.12),
    'fast_track_weight': (0.0, 0.08),
    'accelerated_approval_weight': (0.0, 0.08),
    
    # AdCom
    'adcom_high_boost': (0.0, 0.15),
    'adcom_mid_penalty': (-0.15, 0.0),
    'adcom_low_penalty': (-0.25, -0.05),
    
    # Prior CRL
    'prior_crl_penalty': (-0.20, 0.0),
    'class1_resubmission_boost': (0.05, 0.25),
    'class2_resubmission_penalty': (-0.15, 0.0),
    
    # Sponsor
    'experienced_sponsor_boost': (0.0, 0.10),
    'inexperienced_sponsor_penalty': (-0.15, 0.0),
    
    # Manufacturing
    'manufacturing_risk_penalty': (-0.20, 0.0),
    'form_483_penalty': (-0.15, 0.0),
    
    # NEW: TA adjustment weight (how much to trust historical TA rates)
    'ta_adjustment_weight': (0.5, 1.5),  # 0.5 = half weight, 1.5 = amplify
    
    # Tier thresholds
    'tier1_threshold': (0.80, 0.92),
    'tier2_threshold': (0.65, 0.78),
    'tier3_threshold': (0.50, 0.62),
}


def config_to_vector(config: OdinV91Config) -> np.ndarray:
    """Convert config to parameter vector for GPU optimization."""
    return np.array([
        config.btd_weight,
        config.orphan_weight,
        config.priority_review_weight,
        config.fast_track_weight,
        config.accelerated_approval_weight,
        config.adcom_high_boost,
        config.adcom_mid_penalty,
        config.adcom_low_penalty,
        config.prior_crl_penalty,
        config.class1_resubmission_boost,
        config.class2_resubmission_penalty,
        config.experienced_sponsor_boost,
        config.inexperienced_sponsor_penalty,
        config.manufacturing_risk_penalty,
        config.form_483_penalty,
        config.ta_adjustment_weight,
        config.tier1_threshold,
        config.tier2_threshold,
        config.tier3_threshold,
    ], dtype=np.float32)


def vector_to_config(vec: np.ndarray) -> OdinV91Config:
    """Convert parameter vector back to config."""
    return OdinV91Config(
        btd_weight=float(vec[0]),
        orphan_weight=float(vec[1]),
        priority_review_weight=float(vec[2]),
        fast_track_weight=float(vec[3]),
        accelerated_approval_weight=float(vec[4]),
        adcom_high_boost=float(vec[5]),
        adcom_mid_penalty=float(vec[6]),
        adcom_low_penalty=float(vec[7]),
        prior_crl_penalty=float(vec[8]),
        class1_resubmission_boost=float(vec[9]),
        class2_resubmission_penalty=float(vec[10]),
        experienced_sponsor_boost=float(vec[11]),
        inexperienced_sponsor_penalty=float(vec[12]),
        manufacturing_risk_penalty=float(vec[13]),
        form_483_penalty=float(vec[14]),
        ta_adjustment_weight=float(vec[15]),
        tier1_threshold=float(vec[16]),
        tier2_threshold=float(vec[17]),
        tier3_threshold=float(vec[18]),
    )


# =============================================================================
# EXPORT CONFIG AS JSON (for cross-session persistence)
# =============================================================================

def export_config(config: OdinV91Config, filepath: str):
    """Export config to JSON file."""
    data = {
        'version': '9.1',
        'improvement': 'indication_difficulty_adjustments',
        'parameters': {
            'base_approval_rate': config.base_approval_rate,
            'btd_weight': config.btd_weight,
            'orphan_weight': config.orphan_weight,
            'priority_review_weight': config.priority_review_weight,
            'fast_track_weight': config.fast_track_weight,
            'accelerated_approval_weight': config.accelerated_approval_weight,
            'adcom_high_threshold': config.adcom_high_threshold,
            'adcom_high_boost': config.adcom_high_boost,
            'adcom_mid_threshold': config.adcom_mid_threshold,
            'adcom_mid_penalty': config.adcom_mid_penalty,
            'adcom_low_penalty': config.adcom_low_penalty,
            'prior_crl_penalty': config.prior_crl_penalty,
            'class1_resubmission_boost': config.class1_resubmission_boost,
            'class2_resubmission_penalty': config.class2_resubmission_penalty,
            'experienced_sponsor_boost': config.experienced_sponsor_boost,
            'inexperienced_sponsor_penalty': config.inexperienced_sponsor_penalty,
            'manufacturing_risk_penalty': config.manufacturing_risk_penalty,
            'form_483_penalty': config.form_483_penalty,
            'ta_adjustment_weight': config.ta_adjustment_weight,
            'tier1_threshold': config.tier1_threshold,
            'tier2_threshold': config.tier2_threshold,
            'tier3_threshold': config.tier3_threshold,
        },
        'therapeutic_area_adjustments': config.therapeutic_area_adjustments,
        'modality_adjustments': config.modality_adjustments,
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    # Test scoring
    import pandas as pd
    
    print("ODIN v9.1 - Indication Difficulty Adjustments")
    print("=" * 60)
    
    # Create default config
    config = OdinV91Config()
    
    # Test events
    test_events = [
        {
            'name': 'Pain Management Drug (HIGH RISK)',
            'btd': False, 'orphan': False, 'priority_review': False,
            'therapeutic_area': 'Pain Management', 'modality': 'Small Molecule',
            'sponsor_prior_approvals': 3
        },
        {
            'name': 'Oncology BTD Drug (LOW RISK)',
            'btd': True, 'orphan': True, 'priority_review': True,
            'therapeutic_area': 'Oncology', 'modality': 'Small Molecule',
            'sponsor_prior_approvals': 15
        },
        {
            'name': 'CNS Drug No Designations (MOD RISK)',
            'btd': False, 'orphan': False, 'priority_review': False,
            'therapeutic_area': 'CNS/Neurology', 'modality': 'Small Molecule',
            'sponsor_prior_approvals': 2
        },
        {
            'name': 'Nephrology with Manufacturing Risk',
            'btd': False, 'orphan': True, 'priority_review': False,
            'therapeutic_area': 'Nephrology', 'modality': 'Antibody',
            'manufacturing_risk': True,
            'sponsor_prior_approvals': 8
        },
    ]
    
    for event in test_events:
        result = score_event(config, event)
        print(f"\n{event['name']}")
        print(f"  Probability: {result['probability']*100:.1f}%")
        print(f"  Tier: {result['tier']}")
        print(f"  TA Risk: {result['ta_risk_tier']}")
        print(f"  Key adjustments: {result['adjustments']}")
    
    # Export default config
    export_config(config, '/home/claude/odin_v91_config.json')
    print(f"\n✅ Config exported to odin_v91_config.json")
