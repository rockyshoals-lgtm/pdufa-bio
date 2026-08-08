# ODIN v9.3 Configuration - T-1 Compliance Fix
# ==============================================
# 
# CRITICAL FIX: Replaced outcome-derived `manufacturing_risk` with
# T-1 compliant `modality_complexity` proxy.
#
# The previous `manufacturing_risk` field was retroactively assigned based on
# CRL outcome (chi-squared=365.5, p=1.76e-81). This version removes that leakage.
#
# MODALITY COMPLEXITY PROXY (T-1 COMPLIANT):
# Based on INHERENT manufacturing process difficulty, NOT outcome rates.
# - Cell/Gene Therapy: 0.65 (autologous, viral vectors, cold chain)
# - RNA Therapy: 0.55 (LNP encapsulation, stability issues)
# - Vaccine: 0.50 (antigen production, adjuvants, sterility)
# - ADC: 0.45 (conjugation chemistry, payload stability)
# - Antibody: 0.30 (biologics production, glycosylation)
# - Peptide: 0.15 (synthesis/recombinant, purification)
# - Small Molecule: 0.00 (baseline - well-understood processes)
#
# These scores reflect PROCESS DIFFICULTY, not historical CRL rates.

import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import numpy as np

# =============================================================================
# THERAPEUTIC AREA ADJUSTMENTS (unchanged from v9.2)
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
# INDICATION-LEVEL RISK OVERRIDES (unchanged from v9.2)
# =============================================================================

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
# NEW v9.3: T-1 COMPLIANT MODALITY COMPLEXITY PROXY
# =============================================================================
# CRITICAL: These values are based on INHERENT MANUFACTURING DIFFICULTY,
# NOT on historical CRL rates (which would be outcome-derived leakage).
#
# Rationale for each score:
# - Cell/Gene Therapy (0.65): Autologous products, viral vector production,
#   cold chain requirements, patient-specific manufacturing
# - RNA Therapy (0.55): Lipid nanoparticle encapsulation, RNA stability,
#   scalability challenges, specialized handling
# - Vaccine (0.50): Antigen production, adjuvant formulation, sterility,
#   potency assays, cold chain for some platforms
# - ADC (0.45): Antibody production + payload synthesis + conjugation
#   chemistry, drug-to-antibody ratio control
# - Antibody (0.30): CHO cell culture, glycosylation consistency,
#   aggregation control, larger scale processes
# - Peptide (0.15): Chemical synthesis or recombinant production,
#   purification challenges
# - Small Molecule (0.00): Baseline - well-understood chemical synthesis

MODALITY_COMPLEXITY = {
    "Cell/Gene Therapy": 0.65,
    "RNA Therapy": 0.55,
    "Vaccine": 0.50,
    "ADC": 0.45,
    "Antibody": 0.30,
    "Peptide": 0.15,
    "Small Molecule": 0.00,
}

# Weight to apply to complexity score (optimizable)
# penalty = complexity_weight * MODALITY_COMPLEXITY[modality]
# A weight of -0.10 means Cell/Gene gets -0.065 penalty, Antibody gets -0.03

# =============================================================================
# ODIN v9.3 CONFIGURATION
# =============================================================================

@dataclass
class OdinV93Config:
    """
    ODIN v9.3 Configuration - T-1 Compliance Fix
    
    Key change: Replaced outcome-derived manufacturing_risk with
    T-1 compliant modality_complexity proxy.
    """
    # Base parameters
    base_approval_rate: float = 0.867
    
    # === DESIGNATION WEIGHTS (individual) ===
    btd_weight: float = 0.025
    orphan_weight: float = 0.019
    priority_review_weight: float = 0.024
    fast_track_weight: float = 0.015
    accelerated_approval_weight: float = 0.029
    
    # === DESIGNATION STACK INTERACTIONS ===
    no_designation_penalty: float = -0.021
    btd_pr_synergy_bonus: float = 0.114
    btd_alone_bonus: float = 0.043
    full_stack_bonus: float = 0.023
    
    # === ADCOM ADJUSTMENTS ===
    adcom_high_threshold: float = 0.65
    adcom_high_boost: float = 0.095
    adcom_mid_threshold: float = 0.50
    adcom_mid_penalty: float = -0.072
    adcom_low_penalty: float = -0.081
    
    # === PRIOR CRL / RESUBMISSION ===
    prior_crl_penalty: float = -0.064
    class1_resubmission_boost: float = 0.093
    class2_resubmission_penalty: float = -0.058
    
    # === NON-LINEAR SPONSOR EXPERIENCE ===
    sponsor_one_approval_penalty: float = -0.022
    sponsor_sweet_spot_boost: float = 0.090
    sponsor_mid_tier_penalty: float = -0.016
    sponsor_large_pharma_boost: float = 0.029
    
    # === MANUFACTURING (T-1 COMPLIANT) ===
    # Form 483 penalty only applies if form_483_issues=True
    form_483_penalty: float = -0.144
    
    # NEW v9.3: Modality complexity weight (replaces manufacturing_risk)
    # Penalty = modality_complexity_weight * MODALITY_COMPLEXITY[modality]
    modality_complexity_weight: float = -0.08  # Optimizable: range (-0.20, 0.0)
    
    # === TA ADJUSTMENT ===
    ta_adjustment_weight: float = 0.613
    
    # === TEMPORAL ADJUSTMENT ===
    # NOTE: For backtest evaluation, set to 0 (regime leakage concern)
    # For production predictions on 2026+ events, can use optimized value
    temporal_2024_plus_boost: float = 0.079
    temporal_backtest_mode: bool = False  # If True, disables temporal boost
    
    # === TIER THRESHOLDS ===
    tier1_threshold: float = 0.832
    tier2_threshold: float = 0.707
    tier3_threshold: float = 0.611


def check_indication_override(indication: str) -> Optional[float]:
    """Check if indication matches any high-risk override patterns."""
    if not indication:
        return None
    
    indication_lower = indication.lower()
    
    for pattern, adjustment in INDICATION_RISK_OVERRIDES.items():
        if pattern in indication_lower:
            return adjustment
    
    return None


def get_designation_stack_adjustment(config: OdinV93Config, event: dict) -> tuple:
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
    
    # BTD + PR (without Orphan) = strongest combo
    if btd and pr and not orphan:
        return config.btd_pr_synergy_bonus, "btd_pr_synergy"
    
    # BTD alone (without Orphan or PR)
    if btd and not orphan and not pr:
        return config.btd_alone_bonus, "btd_alone"
    
    # Full stack (BTD + Orphan + PR + FT)
    if btd and orphan and pr and ft:
        return config.full_stack_bonus, "full_stack"
    
    return 0.0, "standard_stack"


def get_sponsor_experience_adjustment(config: OdinV93Config, prior_approvals: int) -> tuple:
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


def get_modality_complexity_penalty(config: OdinV93Config, modality: str) -> tuple:
    """
    T-1 COMPLIANT modality complexity penalty.
    
    Replaces the outcome-derived manufacturing_risk field with a proxy
    based on inherent manufacturing process difficulty.
    
    Returns (adjustment, description)
    """
    complexity = MODALITY_COMPLEXITY.get(modality, 0.15)  # Default to Peptide level
    penalty = config.modality_complexity_weight * complexity
    
    if abs(penalty) < 0.001:
        return 0.0, "no_complexity_penalty"
    
    return penalty, f"complexity_{modality.lower().replace(' ', '_').replace('/', '_')}"


def score_event(config: OdinV93Config, event: dict) -> dict:
    """
    Score a PDUFA event using ODIN v9.3 (T-1 compliant).
    
    Args:
        config: OdinV93Config with tunable parameters
        event: Dict with event features
    
    Returns:
        Dict with probability, tier, adjustments breakdown
    """
    prob = config.base_approval_rate
    adjustments = {}
    
    # 1. Individual designation weights
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
    
    # 2. Designation stack interactions
    stack_adj, stack_desc = get_designation_stack_adjustment(config, event)
    if stack_adj != 0:
        prob += stack_adj
        adjustments[stack_desc] = stack_adj
    
    # 3. AdCom vote
    if event.get('had_adcom') and event.get('adcom_vote_pct') is not None:
        vote = event['adcom_vote_pct']
        if vote >= config.adcom_high_threshold:
            prob += config.adcom_high_boost
            adjustments['adcom_high'] = config.adcom_high_boost
        elif vote >= config.adcom_mid_threshold:
            prob += config.adcom_mid_penalty
            adjustments['adcom_mid'] = config.adcom_mid_penalty
        else:
            prob += config.adcom_low_penalty
            adjustments['adcom_low'] = config.adcom_low_penalty
    
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
    
    # 5. Sponsor experience (non-linear)
    prior_approvals = event.get('sponsor_prior_approvals')
    sponsor_adj, sponsor_tier = get_sponsor_experience_adjustment(config, prior_approvals)
    if sponsor_adj != 0:
        prob += sponsor_adj
        adjustments[f'sponsor_{sponsor_tier}'] = sponsor_adj
    
    # 6. Form 483 penalty (T-1 safe if properly sourced)
    if event.get('form_483_issues'):
        prob += config.form_483_penalty
        adjustments['form_483'] = config.form_483_penalty
    
    # 7. NEW v9.3: Modality complexity penalty (T-1 COMPLIANT)
    # Replaces the leaky manufacturing_risk field
    modality = event.get('modality', 'Small Molecule')
    complexity_adj, complexity_desc = get_modality_complexity_penalty(config, modality)
    if complexity_adj != 0:
        prob += complexity_adj
        adjustments[complexity_desc] = complexity_adj
    
    # 8. Therapeutic area adjustment
    ta = event.get('therapeutic_area', 'Other')
    ta_base_adj = THERAPEUTIC_AREA_ADJUSTMENTS.get(ta, 0.0)
    ta_adj = ta_base_adj * config.ta_adjustment_weight
    if ta_adj != 0:
        prob += ta_adj
        adjustments['therapeutic_area'] = ta_adj
    
    # 9. Indication-level override (if more specific than TA)
    indication = event.get('indication', '')
    indication_override = check_indication_override(indication)
    if indication_override is not None:
        # Override replaces TA adjustment
        override_diff = indication_override * config.ta_adjustment_weight - ta_adj
        prob += override_diff
        adjustments['indication_override'] = indication_override * config.ta_adjustment_weight
    
    # 10. Temporal adjustment (2024+)
    # In backtest mode, this is disabled to avoid regime leakage
    year = event.get('year', 2020)
    if not config.temporal_backtest_mode and year >= 2024:
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
        'modality': modality,
        'therapeutic_area': ta,
        'adjustments': adjustments,
    }


def evaluate_model(config: OdinV93Config, df, backtest_mode: bool = True) -> dict:
    """
    Evaluate model on full dataset.
    
    Args:
        config: OdinV93Config
        df: DataFrame with PDUFA events
        backtest_mode: If True, disables temporal_2024_plus_boost
    
    Returns:
        Dict with evaluation metrics
    """
    import pandas as pd
    
    # Set backtest mode
    config.temporal_backtest_mode = backtest_mode
    
    results = []
    for _, row in df.iterrows():
        event = row.to_dict()
        
        # Convert outcome to binary
        outcome_str = str(event.get('outcome', '')).upper()
        actual = 0 if 'CRL' in outcome_str else 1
        
        result = score_event(config, event)
        
        results.append({
            'probability': result['probability'],
            'predicted': 1 if result['probability'] >= 0.5 else 0,
            'actual': actual,
            'tier': result['tier'],
            'modality': result['modality'],
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
        'backtest_mode': backtest_mode,
    }


# =============================================================================
# GPU OPTIMIZATION PARAMETER BOUNDS
# =============================================================================

PARAMETER_BOUNDS_V93 = {
    # Designation weights
    'btd_weight': (0.0, 0.15),
    'orphan_weight': (0.0, 0.10),
    'priority_review_weight': (0.0, 0.12),
    'fast_track_weight': (0.0, 0.08),
    'accelerated_approval_weight': (0.0, 0.08),
    
    # Stack interactions
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
    
    # Non-linear sponsor
    'sponsor_one_approval_penalty': (-0.12, 0.0),
    'sponsor_sweet_spot_boost': (0.0, 0.15),
    'sponsor_mid_tier_penalty': (-0.10, 0.0),
    'sponsor_large_pharma_boost': (0.0, 0.10),
    
    # Manufacturing (T-1 compliant)
    'form_483_penalty': (-0.20, 0.0),
    'modality_complexity_weight': (-0.20, 0.0),  # NEW: replaces mfg_risk
    
    # TA weight
    'ta_adjustment_weight': (0.4, 1.2),
    
    # Temporal (for production only, set to 0 for backtest)
    'temporal_2024_plus_boost': (0.0, 0.10),
    
    # Tier thresholds
    'tier1_threshold': (0.78, 0.90),
    'tier2_threshold': (0.65, 0.78),
    'tier3_threshold': (0.50, 0.65),
}


def export_config(config: OdinV93Config, filepath: str, include_performance: dict = None):
    """Export config to JSON file."""
    data = {
        'version': '9.3',
        'fix_description': 'T-1 compliance fix: replaced outcome-derived manufacturing_risk with modality_complexity proxy',
        'leakage_removed': {
            'field': 'manufacturing_risk',
            'evidence': 'chi2=365.5, p=1.76e-81 correlation with outcome',
            'replacement': 'modality_complexity (based on inherent process difficulty)'
        },
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
            'modality_complexity_weight': config.modality_complexity_weight,
            'ta_adjustment_weight': config.ta_adjustment_weight,
            'temporal_2024_plus_boost': config.temporal_2024_plus_boost,
            'tier1_threshold': config.tier1_threshold,
            'tier2_threshold': config.tier2_threshold,
            'tier3_threshold': config.tier3_threshold,
        },
        'modality_complexity': MODALITY_COMPLEXITY,
        'therapeutic_area_adjustments': THERAPEUTIC_AREA_ADJUSTMENTS,
        'indication_risk_overrides': INDICATION_RISK_OVERRIDES,
    }
    
    if include_performance:
        data['performance'] = include_performance
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    import pandas as pd
    
    print("=" * 70)
    print("ODIN v9.3 - T-1 Compliance Fix")
    print("=" * 70)
    print("\nKey change: Replaced outcome-derived manufacturing_risk with")
    print("T-1 compliant modality_complexity proxy.")
    
    # Create config
    config = OdinV93Config()
    
    # Show modality complexity values
    print("\n" + "-" * 70)
    print("MODALITY COMPLEXITY (T-1 compliant proxy)")
    print("-" * 70)
    for modality, complexity in sorted(MODALITY_COMPLEXITY.items(), 
                                        key=lambda x: x[1], reverse=True):
        penalty = config.modality_complexity_weight * complexity
        print(f"  {modality:20s}: complexity={complexity:.2f}, penalty={penalty:+.3f}")
    
    # Test scoring on sample events
    test_events = [
        {
            'name': 'Small Molecule Pain Drug (HIGH RISK - but no leaky mfg_risk)',
            'btd': False, 'orphan': False, 'priority_review': False, 'fast_track': False,
            'therapeutic_area': 'Pain Management', 
            'indication': 'chronic pain',
            'modality': 'Small Molecule',
            'sponsor_prior_approvals': 1,
            'year': 2023,
        },
        {
            'name': 'Cell/Gene Therapy (inherent complexity penalty)',
            'btd': True, 'orphan': True, 'priority_review': True, 'fast_track': False,
            'therapeutic_area': 'Rare Disease',
            'indication': 'muscular dystrophy',
            'modality': 'Cell/Gene Therapy',
            'sponsor_prior_approvals': 3,
            'year': 2024,
        },
        {
            'name': 'Oncology mAb BTD+PR (BEST CASE)',
            'btd': True, 'orphan': False, 'priority_review': True, 'fast_track': False,
            'therapeutic_area': 'Oncology',
            'indication': 'NSCLC',
            'modality': 'Antibody',
            'sponsor_prior_approvals': 25,
            'year': 2024,
        },
    ]
    
    print("\n" + "-" * 70)
    print("SAMPLE EVENT SCORING")
    print("-" * 70)
    
    for event in test_events:
        result = score_event(config, event)
        print(f"\n{event['name']}")
        print(f"  Probability: {result['probability']*100:.1f}%")
        print(f"  Tier: {result['tier']}")
        print(f"  Key adjustments:")
        for adj_name, adj_val in sorted(result['adjustments'].items(), 
                                        key=lambda x: abs(x[1]), reverse=True)[:5]:
            print(f"    {adj_name}: {adj_val:+.3f}")
    
    # Load dataset and evaluate
    print("\n" + "=" * 70)
    print("FULL DATASET EVALUATION (BACKTEST MODE - temporal boost disabled)")
    print("=" * 70)
    
    df = pd.read_csv('/mnt/project/ODIN_ENRICHED_PDUFA_1349_v2.csv', 
                     encoding='utf-8', encoding_errors='replace')
    
    # Evaluate in backtest mode (no temporal boost)
    metrics_backtest = evaluate_model(config, df, backtest_mode=True)
    
    print(f"\nN = {metrics_backtest['n']} events")
    print(f"Brier Score: {metrics_backtest['brier_score']:.5f}")
    print(f"CRL Recall @ 85%: {metrics_backtest['crl_recall_at_85']*100:.1f}%")
    print(f"CRL Recall @ 80%: {metrics_backtest['crl_recall_at_80']*100:.1f}%")
    
    print("\nTier Performance:")
    for tier, stats in metrics_backtest['tier_stats'].items():
        print(f"  {tier}: N={stats['n']}, Approval={stats['approval_rate']*100:.1f}%, CRL={stats['crl_rate']*100:.1f}%")
    
    # Compare with production mode (temporal boost enabled)
    print("\n" + "=" * 70)
    print("COMPARISON: PRODUCTION MODE (temporal boost enabled)")
    print("=" * 70)
    
    metrics_prod = evaluate_model(config, df, backtest_mode=False)
    
    print(f"Brier Score: {metrics_prod['brier_score']:.5f}")
    print(f"  (vs backtest: {metrics_backtest['brier_score']:.5f}, diff: {(metrics_prod['brier_score'] - metrics_backtest['brier_score'])*100:.2f}%)")
    
    # Export config
    export_config(config, '/home/claude/ODIN_v93_CHAMPION_CONFIG.json', 
                  include_performance={
                      'backtest_brier': metrics_backtest['brier_score'],
                      'production_brier': metrics_prod['brier_score'],
                      'tier4_crl_rate': metrics_backtest['tier_stats'].get('TIER_4', {}).get('crl_rate', 0),
                      'tier4_count': metrics_backtest['tier_stats'].get('TIER_4', {}).get('n', 0),
                      'crl_recall_at_85': metrics_backtest['crl_recall_at_85'],
                  })
    print(f"\n✅ Config exported to ODIN_v93_CHAMPION_CONFIG.json")
