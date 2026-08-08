"""
ODIN Orchestrator v1.0
======================
Combines:
  1. POA (canonical odin_v1066_expanded_best.json — IMMUTABLE)
  2. S24 Revenue Impact
  3. Runup Module (odin_runup_module.py)

ENGINEER'S NOTE:
  - odin_v1066_expanded_best.json is loaded READ-ONLY and never modified.
  - POA probability is computed, then passed to Runup Module as INPUT.
  - The Runup Module NEVER changes p_approval.
  - T-1 honest: only data available before the trade window is used.
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any

from odin_runup_module import (
    score_runup_event, RunupResult, runup_to_dict,
    classify_revenue_tier, classify_mcap_cohort,
)

# ============================================================
# POA SCORER — Uses canonical config (IMMUTABLE)
# ============================================================

CANONICAL_CONFIG_PATH = "odin_v1066_expanded_best.json"

# Ordered parameter names matching odin5.py feature matrix columns
PARAM_NAMES = [
    "base_logit",
    "snda_base_penalty",
    "snda_pediatric_base_penalty",
    "prior_crl_penalty",
    "inexperienced_sponsor_penalty",
    "manufacturing_risk_penalty",
    "form_483_penalty",
    "ema_cmc_flag_penalty",
    "cmc_extension_penalty",
    "adcom_mid_penalty",
    "adcom_low_penalty",
    "s22_pediatric_pk_penalty",
    "btd_weight",
    "orphan_weight",
    "priority_review_weight",
    "fast_track_weight",
    "accelerated_approval_weight",
    "class1_resubmission_boost",
    "experienced_sponsor_boost",
    "adcom_high_boost",
    "ta_adjustment_weight",
    "s23_insider_weight",
    "s6_hiring_weight",
    "social_weight",
    "odin_weight",
    "hint_weight",
    "hint_crl_rate_penalty",
    "ta_high_risk_penalty",
    "ta_mod_risk_penalty",
    "ta_low_risk_boost",
    "indication_pain_penalty",
    "indication_onc_boost",
    "novice_sponsor_high_risk_ta_penalty",
]


def load_canonical_config(path: str = CANONICAL_CONFIG_PATH) -> dict:
    """Load the immutable canonical POA config. NEVER overwrite this file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Canonical config not found: {path}")
    with open(path, 'r') as f:
        config = json.load(f)
    return config


def _to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ('TRUE', '1', '1.0', 'YES', 'Y', 'APPROVED')


def _to_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_feature_vector(event: dict) -> np.ndarray:
    """
    Build the 33-element feature vector for a single event,
    matching odin5.py _build_matrices column order exactly.
    """
    X = np.zeros(33, dtype=np.float32)

    app_type = str(event.get('application_type', '')).upper()
    prior_approvals = _to_float(event.get('sponsor_prior_approvals', 0))
    had_adcom = _to_bool(event.get('had_adcom', False))
    vote = _to_float(event.get('adcom_vote_pct', 0))
    if vote > 1:
        vote /= 100.0

    # Feature mapping (indices match odin5.py)
    X[0] = 1.0  # base_logit intercept
    X[1] = 1.0 if ('SNDA' in app_type or 'SBLA' in app_type) else 0.0
    X[2] = 1.0 if 'PEDIATRIC' in app_type else 0.0
    X[3] = 1.0 if _to_bool(event.get('prior_crl', False)) else 0.0
    X[4] = 1.0 if prior_approvals == 0 else 0.0
    X[5] = 1.0 if _to_bool(event.get('manufacturing_risk', False)) else 0.0
    X[6] = 1.0 if _to_bool(event.get('form_483_issues', False)) else 0.0
    X[7] = 1.0 if _to_bool(event.get('ema_cmc_flag', False)) else 0.0
    X[8] = 1.0 if _to_bool(event.get('cmc_extension_flag', False)) else 0.0
    X[9] = float(had_adcom and (0.50 <= vote < 0.65))
    X[10] = float(had_adcom and vote < 0.50)
    X[11] = 1.0 if _to_bool(event.get('s22_ped_pk_missing', False)) else 0.0
    X[12] = 1.0 if _to_bool(event.get('btd', False)) else 0.0
    X[13] = 1.0 if _to_bool(event.get('orphan', False)) else 0.0
    X[14] = 1.0 if _to_bool(event.get('priority_review', False)) else 0.0
    X[15] = 1.0 if _to_bool(event.get('fast_track', False)) else 0.0
    X[16] = 1.0 if _to_bool(event.get('accelerated_approval', False)) else 0.0
    X[17] = 1.0 if _to_float(event.get('resubmission_class', 0)) == 1.0 else 0.0
    X[18] = 1.0 if prior_approvals >= 5 else 0.0
    X[19] = float(had_adcom and vote >= 0.65)
    X[20] = _to_float(event.get('ta_base_score', 0))
    X[21] = _to_float(event.get('s23_signal_strength', 0))
    X[22] = _to_float(event.get('s6_signal_strength', 0))
    X[23] = _to_float(event.get('social_sentiment_score', 0))
    # Indices 24, 25 = odin_weight, hint_weight (used in ensemble, zeroed for logit calc)
    X[24] = 0.0
    X[25] = 0.0
    X[26] = _to_float(event.get('historical_crl_rate', 0))

    ta = str(event.get('therapeutic_area', 'Other'))
    HIGH_RISK_TA = ['Pain', 'Ophthalmology', 'Nephrology', 'Hematology']
    MOD_RISK_TA = ['CNS', 'Neurology', 'Cardiovascular', 'Metabolic']
    LOW_RISK_TA = ['Oncology', 'Immunology', 'Dermatology', 'Infectious']

    X[27] = 1.0 if any(k.lower() in ta.lower() for k in HIGH_RISK_TA) else 0.0
    X[28] = 1.0 if any(k.lower() in ta.lower() for k in MOD_RISK_TA) else 0.0
    X[29] = 1.0 if any(k.lower() in ta.lower() for k in LOW_RISK_TA) else 0.0

    indication = str(event.get('indication', ''))
    X[30] = 1.0 if 'pain' in indication.lower() else 0.0
    X[31] = 1.0 if ('cancer' in indication.lower() or 'tumor' in indication.lower()) else 0.0
    X[32] = 1.0 if (prior_approvals < 3 and X[27] > 0) else 0.0

    return X


def score_poa(event: dict, config: Optional[dict] = None) -> dict:
    """
    Compute POA probability using canonical config.

    Returns:
        dict with 'probability', 'tier', 'logit'
    """
    if config is None:
        config = load_canonical_config()

    weights = np.array([config[k] for k in PARAM_NAMES], dtype=np.float32)

    # Zero out ensemble weights for logit calculation (same as odin5.py)
    weights_logit = weights.copy()
    weights_logit[24] = 0.0  # odin_weight
    weights_logit[25] = 0.0  # hint_weight

    X = build_feature_vector(event)
    logit = float(np.dot(weights_logit, X))
    probability = 1.0 / (1.0 + np.exp(-logit))

    # Tier classification (Spec §9.1)
    if probability >= 0.86:
        tier = 'TIER_1'
    elif probability >= 0.73:
        tier = 'TIER_2'
    elif probability >= 0.58:
        tier = 'TIER_3'
    else:
        tier = 'TIER_4'

    return {
        'probability': round(float(probability), 4),
        'tier': tier,
        'logit': round(float(logit), 4),
    }


# ============================================================
# S24 REVENUE IMPACT (Stub — fill from external data)
# ============================================================

def score_revenue_impact(
    event: dict,
    peak_sales: Optional[float] = None,
    market_cap: Optional[float] = None,
) -> dict:
    """
    Compute S24 revenue impact tier.

    If peak_sales and market_cap not provided, returns R3 (default).
    In production, these should be sourced from Yahoo Finance / FMP / analyst data.
    """
    if peak_sales is None or market_cap is None:
        return {
            'peak_sales': 0,
            'market_cap': market_cap or 0,
            'ratio': 0,
            'tier': 'R3',
            'multiplier': 1.0,
            'estimation_method': 'DEFAULT_FALLBACK',
        }

    rev = classify_revenue_tier(peak_sales, market_cap)
    return {
        'peak_sales': peak_sales,
        'market_cap': market_cap,
        'ratio': rev['ratio'],
        'tier': rev['tier'],
        'multiplier': rev['multiplier'],
        'estimation_method': 'PROVIDED',
    }


# ============================================================
# FULL ORCHESTRATOR (Spec §10.2 Data Flow)
# ============================================================

def score_catalyst_full(
    event: dict,
    peak_sales: Optional[float] = None,
    market_cap: Optional[float] = None,
    market_data: Optional[dict] = None,
    options_data: Optional[dict] = None,
    smart_money_data: Optional[dict] = None,
    base_position: float = 10000.0,
    regime: str = 'NORMAL',
    config: Optional[dict] = None,
) -> dict:
    """
    Full ODIN scoring pipeline:
      1. POA using canonical config (immutable)
      2. S24 Revenue impact
      3. Runup timing/sizing/alpha (from ODIN_RUNUP_MODULE_IMPLEMENTATION_SPEC_2.md)

    T-1 honest: uses only information available before the trade window.

    Args:
        event:            Event-level data dict
        peak_sales:       Peak annual sales estimate (optional)
        market_cap:       Market cap at scoring time (optional)
        market_data:      Price data for technicals (optional)
        options_data:     IV/P-C ratio data (optional)
        smart_money_data: Insider/congressional data (optional)
        base_position:    Base $ per trade
        regime:           BULL/NORMAL/BEAR/CRISIS
        config:           Override POA config (default: canonical)

    Returns:
        dict with 'poa', 'revenue', 'runup' sections
    """
    # STEP 1: POA — canonical config
    poa = score_poa(event, config=config)

    # STEP 2: S24 Revenue
    revenue = score_revenue_impact(event, peak_sales, market_cap)

    # STEP 3: Runup Module
    runup = score_runup_event(
        event=event,
        poa_result=poa,
        revenue_result=revenue,
        market_data=market_data,
        options_data=options_data,
        smart_money_data=smart_money_data,
        base_position=base_position,
        regime=regime,
    )

    return {
        'ticker': event.get('ticker', 'UNKNOWN'),
        'catalyst_date': event.get('catalyst_date', ''),
        'poa': poa,
        'revenue': revenue,
        'runup': runup_to_dict(runup),
    }


# ============================================================
# BATCH SCORING (for backtests)
# ============================================================

def score_dataset(
    df: pd.DataFrame,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Score every event in a DataFrame with POA using canonical config.
    Returns original df with added columns: poa_probability, poa_tier, poa_logit.
    """
    if config is None:
        config = load_canonical_config()

    probs, tiers, logits = [], [], []
    for _, row in df.iterrows():
        event = row.to_dict()
        poa = score_poa(event, config=config)
        probs.append(poa['probability'])
        tiers.append(poa['tier'])
        logits.append(poa['logit'])

    df = df.copy()
    df['poa_probability'] = probs
    df['poa_tier'] = tiers
    df['poa_logit'] = logits
    return df


# ============================================================
# CLI DEMO
# ============================================================

def _demo():
    """Quick demo: score a single event."""
    example_event = {
        'ticker': 'IRON',
        'catalyst_date': '2026-02-15',
        'company': 'Disc Medicine',
        'asset': 'bitopertin',
        'indication': 'Erythropoietic protoporphyria (EPP)',
        'therapeutic_area': 'Rare Disease',
        'application_type': 'NDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 0,
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0,
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0,
        'ta_base_score': -0.04,
        'historical_crl_rate': 0.17,
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    }

    result = score_catalyst_full(
        event=example_event,
        peak_sales=200_000_000,
        market_cap=1_200_000_000,
    )

    import json as _json
    print(_json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    _demo()
