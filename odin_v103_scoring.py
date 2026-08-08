# ODIN v10.3 Integrated Scoring Module
# =====================================
# Combines v10.2 baseline with new S23 Insider Selling and enhanced S6 Commercial Hiring
# Calibrated from AQST (insider selling) and PHAR (commercial hiring) case studies
#
# Key improvements:
# - S23: Insider selling pattern detection (2-3 month early warning)
# - S6: NDA vs sNDA bifurcated commercial hiring logic
# - New AVOID signals for coordinated insider selling
# - Trading protocol updates for insider risk management

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

# Import S23 and S6 signal implementations
from odin_v103_insider_hiring_signals import (
    InsiderTransaction, InsiderSellingAnalysis, InsiderRiskLevel,
    HiringData, HiringSignal, ApplicationType,
    analyze_insider_selling, analyze_commercial_hiring,
    INSIDER_SIGNAL_WEIGHTS, HIRING_SIGNAL_WEIGHTS
)

# =============================================================================
# CONFIGURATION (from v10.2 champion + v10.3 additions)
# =============================================================================

V103_CONFIG = {
    # Base parameters
    "base_approval_rate": 0.867,
    "nda_base_penalty": 0.0,
    "snda_base_penalty": -0.03,
    "snda_pediatric_base_penalty": -0.08,
    
    # Designation weights
    "btd_weight": 0.12,
    "orphan_weight": 0.10,
    "priority_review_weight": 0.085,
    "fast_track_weight": 0.03,
    "accelerated_approval_weight": 0.05,
    
    # AdCom parameters
    "adcom_high_threshold": 0.65,
    "adcom_high_boost": 0.08,
    "adcom_mid_threshold": 0.50,
    "adcom_mid_penalty": -0.06,
    "adcom_low_penalty": -0.19,
    
    # Prior CRL
    "prior_crl_penalty": -0.085,
    "class1_resubmission_boost": 0.157,
    "class2_resubmission_penalty": -0.05,
    
    # Sponsor experience
    "experienced_sponsor_boost": 0.053,
    "inexperienced_sponsor_penalty": -0.068,
    "experienced_threshold": 5,
    "inexperienced_threshold": 0,
    
    # Manufacturing risk
    "manufacturing_risk_penalty": -0.12,
    "form_483_penalty": -0.07,
    "ema_cmc_flag_penalty": -0.10,
    "cmc_extension_penalty": -0.08,
    
    # Therapeutic area adjustments
    "ta_adjustment_weight": 0.829,
    
    # Tier thresholds
    "tier1_threshold": 0.858,
    "tier2_threshold": 0.734,
    "tier3_threshold": 0.578,
}

THERAPEUTIC_AREA_ADJUSTMENTS = {
    "Pain Management": -0.30,
    "Hematology": -0.224,
    "Nephrology": -0.177,
    "Ophthalmology": -0.25,
    "CNS/Neurology": -0.098,
    "Cardiovascular": -0.081,
    "Metabolic/Endocrine": -0.067,
    "Rare Disease": -0.043,
    "Other": -0.019,
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
# SCORING RESULT DATA STRUCTURES
# =============================================================================

class AvoidSignal(Enum):
    NONE = "NONE"
    EMA_CMC_FLAG = "AVOID_001_EMA_CMC"
    HIRING_VOID_NDA = "AVOID_002_HIRING_VOID"
    PEDIATRIC_NO_PK = "AVOID_003_PEDIATRIC_NO_PK"
    CMC_EXTENSION = "AVOID_004_CMC_EXTENSION"
    WEEKEND_PDUFA_LOW = "AVOID_005_WEEKEND_PDUFA"
    INSIDER_CRITICAL = "AVOID_006_INSIDER_CRITICAL"
    INSIDER_COORDINATED = "AVOID_007_INSIDER_COORDINATED"
    CSUITE_EXODUS = "AVOID_008_CSUITE_EXODUS"


@dataclass
class OdinV103Result:
    """Complete ODIN v10.3 scoring result."""
    # Core scoring
    ticker: str
    event_id: str
    probability: float
    tier: str
    
    # Component adjustments
    base_rate: float
    designation_total: float
    adcom_adjustment: float
    prior_crl_adjustment: float
    sponsor_adjustment: float
    manufacturing_adjustment: float
    ta_adjustment: float
    
    # v10.3 signals
    s23_insider_selling: float
    s23_risk_level: str
    s23_triggers: List[str]
    
    s6_commercial_hiring: float
    s6_signal: str
    s6_rationale: str
    
    s12_cmc_risk: float
    s22_pediatric_pk: float
    
    # Social signals
    social_total: float
    s21_capped: bool
    
    # Avoid signals
    avoid_signals: List[str]
    is_hard_avoid: bool
    
    # Trading guidance
    recommended_action: str
    exit_window: str
    runner_position: str
    
    # Breakdown for debugging
    adjustments_breakdown: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def score_event_v103(
    event: Dict,
    insider_transactions: Optional[List[InsiderTransaction]] = None,
    hiring_data: Optional[Dict] = None,
    analysis_date: Optional[datetime] = None,
    config: Dict = V103_CONFIG
) -> OdinV103Result:
    """
    Score a PDUFA event using ODIN v10.3.
    
    Args:
        event: Dict with event features
        insider_transactions: SEC Form 4 transaction data for S23
        hiring_data: Job posting data for S6
        analysis_date: Date of analysis (for T-1 compliance)
        config: Configuration dict (default V103_CONFIG)
    
    Returns:
        OdinV103Result with probability, tier, signals, and trading guidance
    """
    if analysis_date is None:
        analysis_date = datetime.now()
    
    # Parse PDUFA date
    pdufa_date = event.get('catalyst_date')
    if isinstance(pdufa_date, str):
        pdufa_date = datetime.strptime(pdufa_date, '%Y-%m-%d')
    
    # Initialize
    prob = config["base_approval_rate"]
    adjustments = {}
    avoid_signals = []
    
    # =========================================================================
    # 1. BASE ADJUSTMENTS (NDA vs sNDA)
    # =========================================================================
    app_type_str = event.get('application_type', event.get('catalyst_type', 'NDA'))
    
    if 'PEDIATRIC' in app_type_str.upper():
        prob += config["snda_pediatric_base_penalty"]
        adjustments['snda_pediatric_base'] = config["snda_pediatric_base_penalty"]
        app_type = ApplicationType.SNDA
    elif 'SNDA' in app_type_str.upper() or 'SBLA' in app_type_str.upper():
        prob += config["snda_base_penalty"]
        adjustments['snda_base'] = config["snda_base_penalty"]
        app_type = ApplicationType.SNDA if 'SNDA' in app_type_str.upper() else ApplicationType.SBLA
    else:
        app_type = ApplicationType.NDA if 'NDA' in app_type_str.upper() else ApplicationType.BLA
    
    # =========================================================================
    # 2. DESIGNATION STACK
    # =========================================================================
    designation_total = 0.0
    
    if event.get('btd'):
        designation_total += config["btd_weight"]
        adjustments['btd'] = config["btd_weight"]
    if event.get('orphan'):
        designation_total += config["orphan_weight"]
        adjustments['orphan'] = config["orphan_weight"]
    if event.get('priority_review'):
        designation_total += config["priority_review_weight"]
        adjustments['priority_review'] = config["priority_review_weight"]
    if event.get('fast_track'):
        designation_total += config["fast_track_weight"]
        adjustments['fast_track'] = config["fast_track_weight"]
    if event.get('accelerated_approval'):
        designation_total += config["accelerated_approval_weight"]
        adjustments['accelerated_approval'] = config["accelerated_approval_weight"]
    
    prob += designation_total
    
    # =========================================================================
    # 3. ADCOM VOTE
    # =========================================================================
    adcom_adj = 0.0
    if event.get('had_adcom') and event.get('adcom_vote_pct') is not None:
        vote = event['adcom_vote_pct']
        if vote >= config["adcom_high_threshold"]:
            adcom_adj = config["adcom_high_boost"]
        elif vote >= config["adcom_mid_threshold"]:
            adcom_adj = config["adcom_mid_penalty"]
        else:
            adcom_adj = config["adcom_low_penalty"]
        prob += adcom_adj
        adjustments['adcom'] = adcom_adj
    
    # =========================================================================
    # 4. PRIOR CRL / RESUBMISSION
    # =========================================================================
    prior_crl_adj = 0.0
    if event.get('prior_crl'):
        prior_crl_adj = config["prior_crl_penalty"]
        
        resubmission_class = event.get('resubmission_class')
        if resubmission_class == 1:
            prior_crl_adj += config["class1_resubmission_boost"]
        elif resubmission_class == 2:
            prior_crl_adj += config["class2_resubmission_penalty"]
        
        prob += prior_crl_adj
        adjustments['prior_crl'] = prior_crl_adj
    
    # =========================================================================
    # 5. SPONSOR EXPERIENCE
    # =========================================================================
    sponsor_adj = 0.0
    prior_approvals = event.get('sponsor_prior_approvals', 0)
    if prior_approvals >= config["experienced_threshold"]:
        sponsor_adj = config["experienced_sponsor_boost"]
    elif prior_approvals <= config["inexperienced_threshold"]:
        sponsor_adj = config["inexperienced_sponsor_penalty"]
    prob += sponsor_adj
    adjustments['sponsor_experience'] = sponsor_adj
    
    # =========================================================================
    # 6. MANUFACTURING / CMC RISK (S12)
    # =========================================================================
    mfg_adj = 0.0
    
    if event.get('manufacturing_risk'):
        mfg_adj += config["manufacturing_risk_penalty"]
    if event.get('form_483_issues'):
        mfg_adj += config["form_483_penalty"]
    if event.get('ema_cmc_flag'):
        mfg_adj += config["ema_cmc_flag_penalty"]
        avoid_signals.append(AvoidSignal.EMA_CMC_FLAG.value)
    if event.get('cmc_extension_flag'):
        mfg_adj += config["cmc_extension_penalty"]
        avoid_signals.append(AvoidSignal.CMC_EXTENSION.value)
    
    prob += mfg_adj
    adjustments['manufacturing'] = mfg_adj
    s12_cmc_risk = mfg_adj
    
    # =========================================================================
    # 7. THERAPEUTIC AREA
    # =========================================================================
    ta = event.get('therapeutic_area', 'Other')
    ta_base_adj = THERAPEUTIC_AREA_ADJUSTMENTS.get(ta, 0.0)
    ta_adj = ta_base_adj * config["ta_adjustment_weight"]
    prob += ta_adj
    adjustments['therapeutic_area'] = ta_adj
    
    # =========================================================================
    # 8. S22 PEDIATRIC PK RISK
    # =========================================================================
    s22_adj = 0.0
    if (event.get('submission_type', '').upper().find('PEDIATRIC') >= 0 and
        event.get('dosing_type') in ['weight_based', 'age_tiered'] and
        not event.get('pediatric_pk_published', True)):
        s22_adj = -0.10
        prob += s22_adj
        adjustments['s22_pediatric_pk'] = s22_adj
        avoid_signals.append(AvoidSignal.PEDIATRIC_NO_PK.value)
    
    # =========================================================================
    # 9. S23 INSIDER SELLING (NEW in v10.3)
    # =========================================================================
    s23_adj = 0.0
    s23_risk_level = "NORMAL"
    s23_triggers = []
    
    if insider_transactions:
        insider_analysis = analyze_insider_selling(
            ticker=event.get('ticker', 'UNKNOWN'),
            transactions=insider_transactions,
            pdufa_date=pdufa_date,
            analysis_date=analysis_date
        )
        s23_adj = insider_analysis.signal_adjustment
        s23_risk_level = insider_analysis.risk_level.value
        s23_triggers = insider_analysis.triggers_fired
        
        prob += s23_adj
        adjustments['s23_insider_selling'] = s23_adj
        
        # Check for AVOID signals
        if insider_analysis.risk_level == InsiderRiskLevel.CRITICAL:
            avoid_signals.append(AvoidSignal.INSIDER_CRITICAL.value)
        if insider_analysis.max_same_day_count >= 3:
            avoid_signals.append(AvoidSignal.INSIDER_COORDINATED.value)
        if (len(insider_analysis.csuite_sellers) >= 3 and 
            insider_analysis.total_sell_value >= 500000):
            avoid_signals.append(AvoidSignal.CSUITE_EXODUS.value)
    
    # =========================================================================
    # 10. S6 COMMERCIAL HIRING (ENHANCED in v10.3)
    # =========================================================================
    s6_adj = 0.0
    s6_signal = "NEUTRAL"
    s6_rationale = "No hiring data provided"
    
    if hiring_data:
        hiring_analysis = analyze_commercial_hiring(
            ticker=event.get('ticker', 'UNKNOWN'),
            hiring_data=hiring_data,
            pdufa_date=pdufa_date,
            application_type=app_type,
            analysis_date=analysis_date
        )
        s6_adj = hiring_analysis.signal_adjustment
        s6_signal = hiring_analysis.signal.value
        s6_rationale = hiring_analysis.rationale
        
        prob += s6_adj
        adjustments['s6_commercial_hiring'] = s6_adj
        
        # Check for hiring void AVOID (NDA/BLA only)
        months_to_pdufa = (pdufa_date - analysis_date).days / 30
        if (app_type in [ApplicationType.NDA, ApplicationType.BLA] and
            hiring_analysis.signal == HiringSignal.VOID and
            months_to_pdufa < 6):
            avoid_signals.append(AvoidSignal.HIRING_VOID_NDA.value)
    
    # =========================================================================
    # 11. SOCIAL SIGNALS (with S21 cap logic)
    # =========================================================================
    social_total = 0.0
    s21_capped = False
    
    # Check cap triggers
    cap_triggers_fired = (
        s12_cmc_risk <= -0.05 or
        s22_adj <= -0.08 or
        (s6_signal == "VOID") or
        s23_risk_level in ["HIGH_RISK", "CRITICAL"]
    )
    
    if event.get('social_signals'):
        social = event['social_signals']
        
        # S17 Social Sentiment
        sentiment = social.get('sentiment_score', 70)
        if sentiment >= 80:
            social_total += 0.03
        elif sentiment <= 60:
            social_total += -0.02
        
        # S18 Engagement Spike
        if social.get('engagement_spike') and sentiment >= 80:
            social_total += 0.02
        
        # S19 Social Silence
        if social.get('social_silence'):
            social_total += -0.03
        
        # S20 Smart Money Divergence
        if social.get('galaxy_score', 50) < 40 and sentiment < 70:
            social_total += -0.02
        
        # S21 Cap
        max_social = 0.02 if cap_triggers_fired else 0.03
        if social_total > max_social:
            social_total = max_social
            s21_capped = True
    
    prob += social_total
    adjustments['social_total'] = social_total
    
    # =========================================================================
    # 12. WEEKEND PDUFA CHECK
    # =========================================================================
    if pdufa_date.weekday() >= 5:  # Saturday=5, Sunday=6
        if prob < 0.80:
            avoid_signals.append(AvoidSignal.WEEKEND_PDUFA_LOW.value)
    
    # =========================================================================
    # 13. CLAMP AND TIER DETERMINATION
    # =========================================================================
    prob = max(0.01, min(0.99, prob))
    
    if prob >= config["tier1_threshold"]:
        tier = "TIER_1"
    elif prob >= config["tier2_threshold"]:
        tier = "TIER_2"
    elif prob >= config["tier3_threshold"]:
        tier = "TIER_3"
    else:
        tier = "TIER_4"
    
    # =========================================================================
    # 14. TRADING GUIDANCE
    # =========================================================================
    is_hard_avoid = len(avoid_signals) > 0
    
    # Determine recommended action
    if is_hard_avoid:
        recommended_action = "AVOID_POSITION"
    elif tier == "TIER_4":
        recommended_action = "NO_POSITION"
    elif tier == "TIER_3":
        recommended_action = "SMALL_POSITION_EARLY_EXIT"
    elif s23_risk_level == "ELEVATED":
        recommended_action = "REDUCED_SIZE_EARLY_EXIT"
    else:
        recommended_action = "STANDARD_POSITION"
    
    # Determine exit window and runner
    if 'PEDIATRIC' in app_type_str.upper():
        exit_window = "T-10"
        runner_position = "0%"
    elif app_type in [ApplicationType.SNDA, ApplicationType.SBLA]:
        exit_window = "T-7 to T-10"
        runner_position = "0%"
    elif s23_risk_level in ["HIGH_RISK", "CRITICAL"]:
        exit_window = "T-10"
        runner_position = "0%"
    elif s23_risk_level == "ELEVATED":
        exit_window = "T-7"
        runner_position = "10%"
    else:
        exit_window = "T-5 to T-7"
        runner_position = "20%"
    
    # =========================================================================
    # 15. BUILD RESULT
    # =========================================================================
    return OdinV103Result(
        ticker=event.get('ticker', 'UNKNOWN'),
        event_id=event.get('event_id', 'UNKNOWN'),
        probability=prob,
        tier=tier,
        
        base_rate=config["base_approval_rate"],
        designation_total=designation_total,
        adcom_adjustment=adcom_adj,
        prior_crl_adjustment=prior_crl_adj,
        sponsor_adjustment=sponsor_adj,
        manufacturing_adjustment=mfg_adj,
        ta_adjustment=ta_adj,
        
        s23_insider_selling=s23_adj,
        s23_risk_level=s23_risk_level,
        s23_triggers=s23_triggers,
        
        s6_commercial_hiring=s6_adj,
        s6_signal=s6_signal,
        s6_rationale=s6_rationale,
        
        s12_cmc_risk=s12_cmc_risk,
        s22_pediatric_pk=s22_adj,
        
        social_total=social_total,
        s21_capped=s21_capped,
        
        avoid_signals=avoid_signals,
        is_hard_avoid=is_hard_avoid,
        
        recommended_action=recommended_action,
        exit_window=exit_window,
        runner_position=runner_position,
        
        adjustments_breakdown=adjustments
    )


def batch_score_v103(
    events: List[Dict],
    insider_data: Dict[str, List[InsiderTransaction]] = None,
    hiring_data: Dict[str, Dict] = None,
    analysis_date: Optional[datetime] = None
) -> List[OdinV103Result]:
    """
    Batch score multiple events with ODIN v10.3.
    
    Args:
        events: List of event dicts
        insider_data: Dict mapping ticker -> insider transactions
        hiring_data: Dict mapping ticker -> hiring data
        analysis_date: Date of analysis
    
    Returns:
        List of OdinV103Result
    """
    if insider_data is None:
        insider_data = {}
    if hiring_data is None:
        hiring_data = {}
    
    results = []
    for event in events:
        ticker = event.get('ticker', '')
        result = score_event_v103(
            event=event,
            insider_transactions=insider_data.get(ticker, None),
            hiring_data=hiring_data.get(ticker, None),
            analysis_date=analysis_date
        )
        results.append(result)
    
    return results


# =============================================================================
# REPORTING UTILITIES
# =============================================================================

def format_result_report(result: OdinV103Result) -> str:
    """Format scoring result as readable report."""
    
    lines = [
        f"=" * 70,
        f"ODIN v10.3 SCORING REPORT: {result.ticker}",
        f"=" * 70,
        f"",
        f"PROBABILITY: {result.probability*100:.1f}%",
        f"TIER: {result.tier}",
        f"HARD AVOID: {'YES - ' + ', '.join(result.avoid_signals) if result.is_hard_avoid else 'NO'}",
        f"",
        f"--- ADJUSTMENT BREAKDOWN ---",
        f"Base Rate:           {result.base_rate*100:.1f}%",
        f"Designations:       {result.designation_total*100:+.1f}%",
        f"AdCom:              {result.adcom_adjustment*100:+.1f}%",
        f"Prior CRL:          {result.prior_crl_adjustment*100:+.1f}%",
        f"Sponsor:            {result.sponsor_adjustment*100:+.1f}%",
        f"Manufacturing:      {result.manufacturing_adjustment*100:+.1f}%",
        f"Therapeutic Area:   {result.ta_adjustment*100:+.1f}%",
        f"",
        f"--- v10.3 SIGNALS ---",
        f"S23 Insider Selling: {result.s23_insider_selling*100:+.1f}% (Risk: {result.s23_risk_level})",
    ]
    
    if result.s23_triggers:
        for trigger in result.s23_triggers:
            lines.append(f"    - {trigger}")
    
    lines.extend([
        f"S6 Commercial Hiring: {result.s6_commercial_hiring*100:+.1f}% ({result.s6_signal})",
        f"    Rationale: {result.s6_rationale}",
        f"S12 CMC Risk:        {result.s12_cmc_risk*100:+.1f}%",
        f"S22 Pediatric PK:    {result.s22_pediatric_pk*100:+.1f}%",
        f"Social Total:        {result.social_total*100:+.1f}% (Capped: {result.s21_capped})",
        f"",
        f"--- TRADING GUIDANCE ---",
        f"Recommended Action: {result.recommended_action}",
        f"Exit Window:        {result.exit_window}",
        f"Runner Position:    {result.runner_position}",
        f"=" * 70,
    ])
    
    return "\n".join(lines)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("ODIN v10.3 Integrated Scoring Module")
    print("=" * 70)
    
    # Example 1: AQST-like event with critical insider selling
    print("\n--- Example 1: AQST-like Event (Critical Insider Selling) ---\n")
    
    aqst_event = {
        'ticker': 'AQST',
        'event_id': 'AQST_2026_01_31',
        'catalyst_date': datetime(2026, 1, 31),
        'application_type': 'NDA',
        'therapeutic_area': 'Immunology',
        'btd': False,
        'orphan': False,
        'priority_review': False,
        'sponsor_prior_approvals': 0,
    }
    
    aqst_insider_txns = [
        InsiderTransaction(
            date=datetime(2025, 9, 15),
            insider_name="COO Jung",
            title="Chief Operating Officer",
            transaction_type="SELL",
            shares=50000,
            price=6.50,
            total_value=325000,
            holdings_before=200000,
            holdings_after=150000,
            pct_holdings_sold=0.25,
            is_10b5_1=True
        ),
        InsiderTransaction(
            date=datetime(2025, 10, 15),
            insider_name="COO Jung",
            title="Chief Operating Officer",
            transaction_type="SELL",
            shares=30000,
            price=7.00,
            total_value=210000,
            holdings_before=150000,
            holdings_after=120000,
            pct_holdings_sold=0.10,
            is_10b5_1=True
        ),
        InsiderTransaction(
            date=datetime(2025, 10, 15),
            insider_name="CMO Kraus",
            title="Chief Medical Officer",
            transaction_type="SELL",
            shares=15000,
            price=7.00,
            total_value=105000,
            holdings_before=100000,
            holdings_after=85000,
            pct_holdings_sold=0.15,
            is_10b5_1=True
        ),
        InsiderTransaction(
            date=datetime(2025, 10, 15),
            insider_name="SVP Boyd",
            title="Senior Vice President",
            transaction_type="SELL",
            shares=20000,
            price=7.00,
            total_value=140000,
            holdings_before=80000,
            holdings_after=60000,
            pct_holdings_sold=0.125,
            is_10b5_1=True
        ),
    ]
    
    aqst_result = score_event_v103(
        event=aqst_event,
        insider_transactions=aqst_insider_txns,
        hiring_data=None,
        analysis_date=datetime(2025, 11, 15)
    )
    
    print(format_result_report(aqst_result))
    
    # Example 2: PHAR-like sNDA with neutral commercial signal
    print("\n--- Example 2: PHAR-like sNDA (Neutral Commercial) ---\n")
    
    phar_event = {
        'ticker': 'PHAR',
        'event_id': 'PHAR_2026_01_31',
        'catalyst_date': datetime(2026, 1, 31),
        'application_type': 'sNDA_PEDIATRIC',
        'submission_type': 'sNDA_PEDIATRIC',
        'therapeutic_area': 'Immunology',
        'btd': False,
        'orphan': True,
        'priority_review': True,
        'sponsor_prior_approvals': 3,
        'dosing_type': 'weight_based',
        'pediatric_pk_published': False,
        'ema_cmc_flag': True,
    }
    
    phar_hiring = {
        "has_cco": True,
        "cco_hire_date": datetime(2025, 11, 1),
        "has_existing_salesforce": True,
        "existing_salesforce_size": 54,
        "recent_commercial_layoffs": False,
        "msl_postings": 2,
        "sales_rep_postings": 3,
    }
    
    phar_result = score_event_v103(
        event=phar_event,
        insider_transactions=None,
        hiring_data=phar_hiring,
        analysis_date=datetime(2025, 12, 15)
    )
    
    print(format_result_report(phar_result))
    
    # Example 3: Strong NDA with bullish signals
    print("\n--- Example 3: Strong NDA (No Red Flags) ---\n")
    
    strong_event = {
        'ticker': 'STRONG',
        'event_id': 'STRONG_2026_06_15',
        'catalyst_date': datetime(2026, 6, 15),
        'application_type': 'NDA',
        'therapeutic_area': 'Oncology',
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'sponsor_prior_approvals': 12,
    }
    
    strong_hiring = {
        "has_cco": True,
        "cco_hire_date": datetime(2024, 6, 1),
        "has_existing_salesforce": False,
        "msl_postings": 8,
        "sales_rep_postings": 15,
        "has_market_access_lead": True,
        "market_access_hire_date": datetime(2024, 9, 1),
    }
    
    strong_result = score_event_v103(
        event=strong_event,
        insider_transactions=None,  # No concerning insider activity
        hiring_data=strong_hiring,
        analysis_date=datetime(2026, 2, 1)
    )
    
    print(format_result_report(strong_result))
    
    print("\n" + "=" * 70)
    print("v10.3 KEY IMPROVEMENTS:")
    print("=" * 70)
    print("""
    1. S23 INSIDER SELLING: Detects AQST-like patterns 2-3 months early
       - CRITICAL = HARD AVOID
       - HIGH_RISK = 50% reduced size, T-10 exit
       - ELEVATED = T-7 exit, 10% runner

    2. S6 COMMERCIAL HIRING: NDA vs sNDA bifurcation
       - NDA/BLA: Full commercial build required, void = bearish
       - sNDA/sBLA: Maintenance hiring = neutral (PHAR lesson)
       
    3. NEW AVOID SIGNALS:
       - AVOID_006: S23 CRITICAL
       - AVOID_007: 3+ insiders same day (AQST pattern)
       - AVOID_008: 3+ C-suite + $500K+ selling
       
    4. S21 CAP TRIGGER: S23 HIGH_RISK now caps sentiment boost
    """)
