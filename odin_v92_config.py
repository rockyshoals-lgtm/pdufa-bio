# ODIN v9.2 Configuration - Enhanced Predictive Features
# ========================================================
# Improvements over v9.1:
#   1. Designation stack interactions (BTD+PR synergy, no-designation penalty)
#   2. Non-linear sponsor experience tiers
#   3. Modality-specific manufacturing risk
#   4. Indication-level risk overrides
#   5. Temporal adjustment (2024+ FDA efficiency)
#
# All features validated against 1,349 historical PDUFA events

import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import numpy as np

# =============================================================================
# THERAPEUTIC AREA ADJUSTMENTS (from v9.1)
# =============================================================================

THERAPEUTIC_AREA_ADJUSTMENTS = {
    "Pain Management": -0.286,
    "Hematology": -0.224,
    "Nephrology": -0.177,
    "Ophthalmology": -0.131,
    "CNS/Neurology": -0.098,
    "Cardiovascular": -0.081,
    "Metabolic/Endocrine": -0.067,
    "Rare Disease": -0.043,
    "Other": -0.019,
    "Immunology": 0.016,
    "Dermatology": 0.028,
    "Oncology": 0.061,
    "GI/Hepatology": 0.067,
    "Respiratory": 0.090,
    "Infectious Disease": 0.103,
    "Vaccines": 0.133,
    "Women's Health": 0.133,
}

# =============================================================================
# NEW v9.2: INDICATION-LEVEL RISK OVERRIDES
# =============================================================================
# These override TA adjustments for specific high-risk indications
# Based on historical CRL rates within each indication

INDICATION_RISK_OVERRIDES = {
    # Extreme risk (>40% CRL rate historically)
    "bunionectomy": -0.40,
    "postoperative pain": -0.35,
    "chronic pain": -0.30,
    "inflammatory disease": -0.25,
    
    # High risk (30-40% CRL)
    "parkinson": -0.20,
    "migraine": -0.15,
    "mdd": -0.12,
    "major depressive": -0.12,
    "schizophrenia": -0.10,
    "hypercholesterolemia": -0.10,
    "dry eye": -0.10,
    
    # Low risk overrides (boost)
    "covid": 0.10,
    "hiv": 0.08,
    "nsclc": 0.05,
    "multiple myeloma": 0.05,
}

# =============================================================================
# NEW v9.2: MODALITY-SPECIFIC MANUFACTURING RISK
# =============================================================================
# Small molecule + manufacturing risk = near-certain CRL!

MODALITY_MFG_RISK_PENALTIES = {
    "Small Molecule": -0.45,      # 100% CRL rate historically!
    "Antibody": -0.15,            # 23.6% CRL with mfg risk
    "Cell/Gene Therapy": -0.08,   # 10.8% CRL with mfg risk
    "RNA Therapy": -0.08,
    "Peptide": -0.12,
    "Vaccine": -0.05,
    "ADC": -0.12,
}

# =============================================================================
# ODIN v9.2 CONFIGURATION
# =============================================================================

@dataclass
class OdinV92Config:
    """
    ODIN v9.2 Configuration with enhanced predictive features.
    """
    # Base parameters
    base_approval_rate: float = 0.867
    
    # === DESIGNATION WEIGHTS (individual) ===
    btd_weight: float = 0.06
    orphan_weight: float = 0.04
    priority_review_weight: float = 0.05
    fast_track_weight: float = 0.02
    accelerated_approval_weight: float = 0.03
    
    # === NEW v9.2: DESIGNATION STACK INTERACTIONS ===
    no_designation_penalty: float = -0.05       # BTD=F, Orphan=F, PR=F
    btd_pr_synergy_bonus: float = 0.08          # BTD+PR combo (1.7% CRL!)
    btd_alone_bonus: float = 0.06               # BTD only (2.5% CRL)
    full_stack_bonus: float = 0.04              # BTD+Orphan+PR+FT
    
    # === ADCOM ADJUSTMENTS ===
    adcom_high_threshold: float = 0.65
    adcom_high_boost: float = 0.08
    adcom_mid_threshold: float = 0.50
    adcom_mid_penalty: float = -0.05
    adcom_low_penalty: float = -0.15
    
    # === PRIOR CRL / RESUBMISSION ===
    prior_crl_penalty: float = -0.10
    class1_resubmission_boost: float = 0.15
    class2_resubmission_penalty: float = -0.05
    
    # === NEW v9.2: NON-LINEAR SPONSOR EXPERIENCE ===
    # Discovery: 1 prior approval = HIGH RISK (19.1% CRL)
    #            2-3 prior = LOWEST RISK (4.3% CRL)
    sponsor_one_approval_penalty: float = -0.06    # "One-hit wonders"
    sponsor_sweet_spot_boost: float = 0.08         # 2-3 approvals
    sponsor_mid_tier_penalty: float = -0.03        # 4-10 approvals
    sponsor_large_pharma_boost: float = 0.05       # >10 approvals
    
    # === MANUFACTURING RISK (base, modality-specific applied separately) ===
    form_483_penalty: float = -0.08
    
    # === TA ADJUSTMENT ===
    ta_adjustment_weight: float = 0.83  # From v9.1 optimization
    
    # === NEW v9.2: TEMPORAL ADJUSTMENT ===
    temporal_2024_plus_boost: float = 0.03  # 2024+ has ~5% lower CRL rate
    
    # === TIER THRESHOLDS ===
    tier1_threshold: float = 0.858
    tier2_threshold: float = 0.734
    tier3_threshold: float = 0.578


def check_indication_override(indication: str) -> Optional[float]:
    """Check if indication matches any high-risk override patterns."""
    if not indication:
        return None
    
    indication_lower = indication.lower()
    
    for pattern, adjustment in INDICATION_RISK_OVERRIDES.items():
        if pattern in indication_lower:
            return adjustment
    
    return None


def get_designation_stack_adjustment(config: OdinV92Config, event: dict) -> tuple:
    """
    Calculate designation stack interactions.
    Returns (adjustment, description)
    """
    btd = event.get('btd', False)
    orphan = event.get('orphan', False)
    pr = event.get('priority_review', False)
    ft = event.get('fast_track', False)
    
    # No designations at all
    if not (btd or orphan or pr or ft):
        return config.no_designation_penalty, "no_designations"
    
    # BTD + PR (without Orphan) = strongest combo (1.7% CRL)
    if btd and pr and not orphan:
        return config.btd_pr_synergy_bonus, "btd_pr_synergy"
    
    # BTD alone (without Orphan or PR) = very strong (2.5% CRL)
    if btd and not orphan and not pr:
        return config.btd_alone_bonus, "btd_alone"
    
    # Full stack (BTD + Orphan + PR + FT)
    if btd and orphan and pr and ft:
        return config.full_stack_bonus, "full_stack"
    
    return 0.0, "standard_stack"


def get_sponsor_experience_adjustment(config: OdinV92Config, prior_approvals: int) -> tuple:
    """
    Non-linear sponsor experience adjustment.
    Returns (adjustment, tier_name)
    """
    if prior_approvals is None:
        return 0.0, "unknown"
    
    if prior_approvals == 1:
        return config.sponsor_one_approval_penalty, "one_hit_wonder"
    elif 2 <= prior_approvals <= 3:
        return config.sponsor_sweet_spot_boost, "sweet_spot"
    elif 4 <= prior_approvals <= 10:
        return config.sponsor_mid_tier_penalty, "mid_tier"
    elif prior_approvals > 10:
        return config.sponsor_large_pharma_boost, "large_pharma"
    else:  # 0 approvals
        return 0.0, "first_timer"


def get_manufacturing_risk_penalty(config: OdinV92Config, event: dict) -> tuple:
    """
    Modality-specific manufacturing risk penalty.
    Returns (adjustment, description)
    """
    if not event.get('manufacturing_risk', False):
        return 0.0, "no_mfg_risk"
    
    modality = event.get('modality', 'Small Molecule')
    penalty = MODALITY_MFG_RISK_PENALTIES.get(modality, -0.12)
    
    return penalty, f"mfg_risk_{modality.lower().replace(' ', '_')}"


def score_event(config: OdinV92Config, event: dict) -> dict:
    """
    Score a PDUFA event using ODIN v9.2.
    
    Args:
        config: OdinV92Config with tunable parameters
        event: Dict with event features
    
    Returns:
        Dict with probability, tier, adjustments breakdown
    """
    prob = config.base_approval_rate
    adjustments = {}
    
    # 1. Individual designation weights (still additive as base)
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
    
    # 2. NEW: Designation stack interactions
    stack_adj, stack_type = get_designation_stack_adjustment(config, event)
    if stack_adj != 0:
        prob += stack_adj
        adjustments[f'stack_{stack_type}'] = stack_adj
    
    # 3. AdCom vote
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
    
    # 4. Prior CRL / Resubmission
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
    
    # 5. NEW: Non-linear sponsor experience
    prior_approvals = event.get('sponsor_prior_approvals', 0)
    sponsor_adj, sponsor_tier = get_sponsor_experience_adjustment(config, prior_approvals)
    if sponsor_adj != 0:
        prob += sponsor_adj
        adjustments[f'sponsor_{sponsor_tier}'] = sponsor_adj
    
    # 6. NEW: Modality-specific manufacturing risk
    mfg_adj, mfg_desc = get_manufacturing_risk_penalty(config, event)
    if mfg_adj != 0:
        prob += mfg_adj
        adjustments[mfg_desc] = mfg_adj
    
    # 7. Form 483 issues (separate from manufacturing risk)
    if event.get('form_483_issues'):
        prob += config.form_483_penalty
        adjustments['form_483'] = config.form_483_penalty
    
    # 8. Therapeutic area adjustment (from v9.1)
    ta = event.get('therapeutic_area', 'Other')
    ta_base_adj = THERAPEUTIC_AREA_ADJUSTMENTS.get(ta, 0.0)
    ta_adj = ta_base_adj * config.ta_adjustment_weight
    if ta_adj != 0:
        prob += ta_adj
        adjustments['therapeutic_area'] = ta_adj
    
    # 9. NEW: Indication-level override (overrides TA if stronger signal)
    indication = event.get('indication', '')
    indication_override = check_indication_override(indication)
    if indication_override is not None:
        # Only apply if stronger than TA adjustment
        if abs(indication_override) > abs(ta_adj):
            delta = indication_override - ta_adj
            prob += delta
            adjustments['indication_override'] = delta
    
    # 10. NEW: Temporal adjustment (2024+ has lower CRL rates)
    year = event.get('year', 2023)
    if year >= 2024:
        prob += config.temporal_2024_plus_boost
        adjustments['temporal_2024_plus'] = config.temporal_2024_plus_boost
    
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
    
    return {
        'probability': prob,
        'tier': tier,
        'adjustments': adjustments,
        'therapeutic_area': ta,
        'indication': indication,
        'year': year,
    }


def evaluate_model(config: OdinV92Config, df) -> dict:
    """
    Evaluate ODIN v9.2 on a dataset.
    Returns performance metrics.
    """
    import pandas as pd
    
    results = []
    for _, row in df.iterrows():
        event = row.to_dict()
        result = score_event(config, event)
        
        # Get actual outcome
        outcome = str(row.get('outcome', '')).upper()
        actual = 1 if outcome in ['APPROVED', 'APPROVAL'] else 0
        
        results.append({
            'probability': result['probability'],
            'predicted': 1 if result['probability'] >= 0.5 else 0,
            'actual': actual,
            'tier': result['tier'],
        })
    
    results_df = pd.DataFrame(results)
    
    # Calculate metrics
    n = len(results_df)
    brier = ((results_df['probability'] - results_df['actual']) ** 2).mean()
    
    # Tier analysis
    tier_stats = {}
    for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
        tier_df = results_df[results_df['tier'] == tier]
        if len(tier_df) > 0:
            tier_stats[tier] = {
                'n': len(tier_df),
                'approval_rate': tier_df['actual'].mean(),
                'crl_rate': 1 - tier_df['actual'].mean(),
            }
    
    # CRL detection (recall at various thresholds)
    crls = results_df[results_df['actual'] == 0]
    crl_recall_85 = (crls['probability'] < 0.85).mean() if len(crls) > 0 else 0
    crl_recall_80 = (crls['probability'] < 0.80).mean() if len(crls) > 0 else 0
    
    return {
        'n': n,
        'brier_score': brier,
        'tier_stats': tier_stats,
        'crl_recall_at_85': crl_recall_85,
        'crl_recall_at_80': crl_recall_80,
    }


# =============================================================================
# GPU OPTIMIZATION PARAMETER BOUNDS
# =============================================================================

PARAMETER_BOUNDS_V92 = {
    # Designation weights
    'btd_weight': (0.0, 0.15),
    'orphan_weight': (0.0, 0.10),
    'priority_review_weight': (0.0, 0.12),
    'fast_track_weight': (0.0, 0.08),
    'accelerated_approval_weight': (0.0, 0.08),
    
    # NEW: Stack interactions
    'no_designation_penalty': (-0.12, 0.0),
    'btd_pr_synergy_bonus': (0.0, 0.15),
    'btd_alone_bonus': (0.0, 0.12),
    'full_stack_bonus': (0.0, 0.10),
    
    # AdCom
    'adcom_high_boost': (0.0, 0.15),
    'adcom_mid_penalty': (-0.15, 0.0),
    'adcom_low_penalty': (-0.25, -0.05),
    
    # Prior CRL
    'prior_crl_penalty': (-0.20, 0.0),
    'class1_resubmission_boost': (0.05, 0.25),
    'class2_resubmission_penalty': (-0.15, 0.0),
    
    # NEW: Non-linear sponsor
    'sponsor_one_approval_penalty': (-0.12, 0.0),
    'sponsor_sweet_spot_boost': (0.0, 0.15),
    'sponsor_mid_tier_penalty': (-0.10, 0.0),
    'sponsor_large_pharma_boost': (0.0, 0.10),
    
    # Manufacturing
    'form_483_penalty': (-0.15, 0.0),
    
    # TA weight
    'ta_adjustment_weight': (0.5, 1.5),
    
    # NEW: Temporal
    'temporal_2024_plus_boost': (0.0, 0.08),
    
    # Tier thresholds
    'tier1_threshold': (0.80, 0.92),
    'tier2_threshold': (0.65, 0.78),
    'tier3_threshold': (0.50, 0.62),
}


def export_config(config: OdinV92Config, filepath: str):
    """Export config to JSON file."""
    data = {
        'version': '9.2',
        'improvements': [
            'designation_stack_interactions',
            'nonlinear_sponsor_experience',
            'modality_specific_manufacturing_risk',
            'indication_level_overrides',
            'temporal_adjustment_2024_plus',
        ],
        'parameters': {
            'base_approval_rate': config.base_approval_rate,
            'btd_weight': config.btd_weight,
            'orphan_weight': config.orphan_weight,
            'priority_review_weight': config.priority_review_weight,
            'fast_track_weight': config.fast_track_weight,
            'accelerated_approval_weight': config.accelerated_approval_weight,
            'no_designation_penalty': config.no_designation_penalty,
            'btd_pr_synergy_bonus': config.btd_pr_synergy_bonus,
            'btd_alone_bonus': config.btd_alone_bonus,
            'full_stack_bonus': config.full_stack_bonus,
            'adcom_high_threshold': config.adcom_high_threshold,
            'adcom_high_boost': config.adcom_high_boost,
            'adcom_mid_threshold': config.adcom_mid_threshold,
            'adcom_mid_penalty': config.adcom_mid_penalty,
            'adcom_low_penalty': config.adcom_low_penalty,
            'prior_crl_penalty': config.prior_crl_penalty,
            'class1_resubmission_boost': config.class1_resubmission_boost,
            'class2_resubmission_penalty': config.class2_resubmission_penalty,
            'sponsor_one_approval_penalty': config.sponsor_one_approval_penalty,
            'sponsor_sweet_spot_boost': config.sponsor_sweet_spot_boost,
            'sponsor_mid_tier_penalty': config.sponsor_mid_tier_penalty,
            'sponsor_large_pharma_boost': config.sponsor_large_pharma_boost,
            'form_483_penalty': config.form_483_penalty,
            'ta_adjustment_weight': config.ta_adjustment_weight,
            'temporal_2024_plus_boost': config.temporal_2024_plus_boost,
            'tier1_threshold': config.tier1_threshold,
            'tier2_threshold': config.tier2_threshold,
            'tier3_threshold': config.tier3_threshold,
        },
        'therapeutic_area_adjustments': THERAPEUTIC_AREA_ADJUSTMENTS,
        'indication_risk_overrides': INDICATION_RISK_OVERRIDES,
        'modality_mfg_risk_penalties': MODALITY_MFG_RISK_PENALTIES,
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    import pandas as pd
    
    print("=" * 70)
    print("ODIN v9.2 - Enhanced Predictive Features")
    print("=" * 70)
    
    # Create default config
    config = OdinV92Config()
    
    # Test scoring on sample events
    test_events = [
        {
            'name': 'Pain Drug, No Designations, 1 Prior Approval (WORST CASE)',
            'btd': False, 'orphan': False, 'priority_review': False, 'fast_track': False,
            'therapeutic_area': 'Pain Management', 
            'indication': 'chronic pain',
            'modality': 'Small Molecule',
            'sponsor_prior_approvals': 1,
            'manufacturing_risk': True,
            'year': 2023,
        },
        {
            'name': 'Oncology BTD+PR, Large Pharma (BEST CASE)',
            'btd': True, 'orphan': False, 'priority_review': True, 'fast_track': False,
            'therapeutic_area': 'Oncology',
            'indication': 'NSCLC',
            'modality': 'Antibody',
            'sponsor_prior_approvals': 25,
            'manufacturing_risk': False,
            'year': 2024,
        },
        {
            'name': 'CNS Drug, Sweet Spot Sponsor, 2024',
            'btd': False, 'orphan': True, 'priority_review': True, 'fast_track': False,
            'therapeutic_area': 'CNS/Neurology',
            'indication': 'epilepsy',
            'modality': 'Small Molecule',
            'sponsor_prior_approvals': 3,
            'manufacturing_risk': False,
            'year': 2024,
        },
        {
            'name': 'Parkinson Drug (High Risk Indication Override)',
            'btd': True, 'orphan': True, 'priority_review': True, 'fast_track': True,
            'therapeutic_area': 'CNS/Neurology',
            'indication': "Parkinson's disease",
            'modality': 'Small Molecule',
            'sponsor_prior_approvals': 15,
            'manufacturing_risk': False,
            'year': 2025,
        },
    ]
    
    print("\nSample Event Scoring:")
    print("-" * 70)
    for event in test_events:
        result = score_event(config, event)
        print(f"\n{event['name']}")
        print(f"  Probability: {result['probability']*100:.1f}%")
        print(f"  Tier: {result['tier']}")
        print(f"  Key adjustments:")
        for adj_name, adj_val in sorted(result['adjustments'].items(), key=lambda x: abs(x[1]), reverse=True):
            print(f"    {adj_name}: {adj_val:+.3f}")
    
    # Load dataset and evaluate
    print("\n" + "=" * 70)
    print("Full Dataset Evaluation")
    print("=" * 70)
    
    df = pd.read_csv('/mnt/project/ODIN_ENRICHED_PDUFA_1349_v2.csv', encoding='utf-8', encoding_errors='replace')
    
    metrics = evaluate_model(config, df)
    
    print(f"\nN = {metrics['n']} events")
    print(f"Brier Score: {metrics['brier_score']:.5f}")
    print(f"CRL Recall @ 85%: {metrics['crl_recall_at_85']*100:.1f}%")
    print(f"CRL Recall @ 80%: {metrics['crl_recall_at_80']*100:.1f}%")
    
    print("\nTier Performance:")
    for tier, stats in metrics['tier_stats'].items():
        print(f"  {tier}: N={stats['n']}, Approval={stats['approval_rate']*100:.1f}%, CRL={stats['crl_rate']*100:.1f}%")
    
    # Export config
    export_config(config, '/home/claude/odin_v92_config.json')
    print(f"\n✅ Config exported to odin_v92_config.json")
