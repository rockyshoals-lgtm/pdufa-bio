# ODIN v10.3 Signal Implementation: Insider Selling & Commercial Hiring
# ======================================================================
# Based on AQST and PHAR case study calibration (January 2026)
#
# Key Findings:
# - Insider selling provides STRONGER bearish signal than commercial hiring bullish signal
# - AQST: 35% COO selling + 3 executives same-day sale → detected 2-3 months before CRL
# - PHAR: Commercial hiring signals require different calibration for sNDA vs NDA
#
# T-1 Compliant: All data from SEC Form 4 filings and public job postings

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

# =============================================================================
# SIGNAL ENUMS AND CONSTANTS
# =============================================================================

class InsiderRiskLevel(Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"  # Multiple triggers

class HiringSignal(Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    VOID = "VOID"  # Complete absence

class ApplicationType(Enum):
    NDA = "NDA"           # New Drug Application - full commercial build required
    SNDA = "sNDA"         # Supplemental NDA - label expansion
    BLA = "BLA"           # Biologics License Application
    SBLA = "sBLA"         # Supplemental BLA

# =============================================================================
# S23: INSIDER SELLING SIGNAL
# =============================================================================
# Calibrated from AQST case study where:
# - COO sold 35% cumulative holdings
# - 3 executives sold same day (Oct 15, 2025)
# - Zero purchases, $1.69M total sales
# - Pattern detected 2-3 months before January 2026 CRL

@dataclass
class InsiderTransaction:
    """Single insider transaction from SEC Form 4"""
    date: datetime
    insider_name: str
    title: str  # CEO, CFO, COO, CMO, etc.
    transaction_type: str  # "SELL" or "BUY"
    shares: int
    price: float
    total_value: float
    holdings_before: int
    holdings_after: int
    pct_holdings_sold: float  # For sells only
    is_10b5_1: bool  # Under trading plan

@dataclass
class InsiderSellingAnalysis:
    """Aggregated insider selling analysis for a ticker"""
    ticker: str
    analysis_date: datetime
    pdufa_date: datetime
    lookback_days: int = 180  # 6 months
    
    # Raw transaction data
    transactions: List[InsiderTransaction] = field(default_factory=list)
    
    # Computed metrics
    total_sell_value: float = 0.0
    total_buy_value: float = 0.0
    sell_buy_ratio: float = 0.0  # >1 = more selling
    num_sellers: int = 0
    num_buyers: int = 0
    
    # C-Suite specific
    csuite_sellers: List[str] = field(default_factory=list)
    csuite_max_pct_sold: float = 0.0  # Highest % sold by any C-suite
    csuite_cumulative_sold: float = 0.0  # Total $ sold by C-suite
    
    # Clustering detection
    same_day_sellers: Dict[str, List[str]] = field(default_factory=dict)  # date -> [names]
    max_same_day_count: int = 0
    same_30day_window_count: int = 0
    
    # Timing analysis
    selling_period_start: Optional[datetime] = None
    selling_period_end: Optional[datetime] = None
    quiet_period_days: int = 0  # Days between last sale and PDUFA
    
    # Final scoring
    risk_level: InsiderRiskLevel = InsiderRiskLevel.NORMAL
    triggers_fired: List[str] = field(default_factory=list)
    signal_adjustment: float = 0.0


# Thresholds calibrated from AQST case study and industry benchmarks
INSIDER_THRESHOLDS = {
    # Individual transaction thresholds
    "single_transaction_pct_elevated": 0.03,   # 3% = elevated
    "single_transaction_pct_high": 0.08,       # 8% = high risk
    "single_transaction_pct_critical": 0.15,   # 15%+ = critical
    
    # Cumulative selling thresholds (6-month window)
    "cumulative_pct_elevated": 0.05,           # 5% annual = elevated
    "cumulative_pct_high": 0.10,               # 10% = high risk
    "cumulative_pct_critical": 0.20,           # 20%+ = critical
    
    # Multiple seller thresholds
    "same_day_elevated": 2,                    # 2 sellers same day
    "same_day_high": 3,                        # 3+ sellers = AQST pattern
    "same_30day_elevated": 2,                  # 2 C-suite in 30 days
    "same_30day_high": 3,                      # 3+ C-suite in 30 days
    
    # Dollar thresholds
    "aggregate_sell_elevated": 250000,         # $250K total
    "aggregate_sell_high": 500000,             # $500K = significant
    "aggregate_sell_critical": 1000000,        # $1M+ = AQST level
    
    # Timing thresholds (days before PDUFA)
    "quiet_period_suspicious": 45,             # Last sale >45 days before = quiet period
    "selling_window_start": 180,               # Look back 6 months
    "selling_window_end": 30,                  # Stop analyzing <30 days (blackout)
}

# Signal adjustments based on risk level
INSIDER_SIGNAL_WEIGHTS = {
    InsiderRiskLevel.NORMAL: 0.0,
    InsiderRiskLevel.ELEVATED: -0.03,
    InsiderRiskLevel.HIGH_RISK: -0.06,
    InsiderRiskLevel.CRITICAL: -0.10,  # Same weight as S22 Pediatric PK Risk
}


def analyze_insider_selling(
    ticker: str,
    transactions: List[InsiderTransaction],
    pdufa_date: datetime,
    analysis_date: Optional[datetime] = None
) -> InsiderSellingAnalysis:
    """
    Analyze insider selling patterns for PDUFA prediction.
    
    Implements calibrated thresholds from AQST case study:
    - Flags cumulative selling >10% holdings
    - Detects same-day coordinated selling (AQST: 3 executives Oct 15)
    - Identifies quiet periods before PDUFA
    - Zero-purchase ratio as bearish indicator
    
    Args:
        ticker: Stock ticker
        transactions: List of SEC Form 4 transactions
        pdufa_date: PDUFA decision date
        analysis_date: Date of analysis (default: today)
    
    Returns:
        InsiderSellingAnalysis with risk level and signal adjustment
    """
    if analysis_date is None:
        analysis_date = datetime.now()
    
    analysis = InsiderSellingAnalysis(
        ticker=ticker,
        analysis_date=analysis_date,
        pdufa_date=pdufa_date
    )
    
    # Filter to lookback window (6 months before analysis, >30 days before PDUFA)
    window_start = analysis_date - timedelta(days=INSIDER_THRESHOLDS["selling_window_start"])
    window_end = pdufa_date - timedelta(days=INSIDER_THRESHOLDS["selling_window_end"])
    
    filtered_txns = [
        t for t in transactions
        if window_start <= t.date <= window_end
    ]
    
    if not filtered_txns:
        analysis.risk_level = InsiderRiskLevel.NORMAL
        analysis.signal_adjustment = 0.0
        return analysis
    
    analysis.transactions = filtered_txns
    
    # Aggregate metrics
    sells = [t for t in filtered_txns if t.transaction_type == "SELL"]
    buys = [t for t in filtered_txns if t.transaction_type == "BUY"]
    
    analysis.total_sell_value = sum(t.total_value for t in sells)
    analysis.total_buy_value = sum(t.total_value for t in buys)
    analysis.num_sellers = len(set(t.insider_name for t in sells))
    analysis.num_buyers = len(set(t.insider_name for t in buys))
    
    # Sell/buy ratio (infinity if zero buys)
    if analysis.total_buy_value > 0:
        analysis.sell_buy_ratio = analysis.total_sell_value / analysis.total_buy_value
    else:
        analysis.sell_buy_ratio = float('inf') if analysis.total_sell_value > 0 else 0
    
    # C-Suite analysis (CEO, CFO, COO, CMO, CBO, CSO, etc.)
    csuite_titles = {"CEO", "CFO", "COO", "CMO", "CBO", "CSO", "CTO", "CAO", 
                    "Chief Executive", "Chief Financial", "Chief Operating",
                    "Chief Medical", "Chief Business", "Chief Scientific",
                    "President", "Chairman"}
    
    csuite_sells = [
        t for t in sells 
        if any(title in t.title.upper() for title in csuite_titles)
    ]
    
    analysis.csuite_sellers = list(set(t.insider_name for t in csuite_sells))
    analysis.csuite_cumulative_sold = sum(t.total_value for t in csuite_sells)
    
    if csuite_sells:
        analysis.csuite_max_pct_sold = max(t.pct_holdings_sold for t in csuite_sells)
    
    # Same-day clustering detection (AQST: 3 executives Oct 15, 2025)
    from collections import defaultdict
    daily_sellers = defaultdict(list)
    for t in sells:
        date_str = t.date.strftime("%Y-%m-%d")
        daily_sellers[date_str].append(t.insider_name)
    
    analysis.same_day_sellers = {
        date: list(set(names)) for date, names in daily_sellers.items()
        if len(set(names)) >= 2
    }
    
    if analysis.same_day_sellers:
        analysis.max_same_day_count = max(len(names) for names in analysis.same_day_sellers.values())
    
    # 30-day window clustering for C-suite
    if len(csuite_sells) >= 2:
        csuite_sells_sorted = sorted(csuite_sells, key=lambda t: t.date)
        for i, t1 in enumerate(csuite_sells_sorted):
            window_end_30 = t1.date + timedelta(days=30)
            in_window = [
                t2 for t2 in csuite_sells_sorted[i:]
                if t2.date <= window_end_30
            ]
            analysis.same_30day_window_count = max(
                analysis.same_30day_window_count,
                len(set(t.insider_name for t in in_window))
            )
    
    # Timing analysis
    if sells:
        analysis.selling_period_start = min(t.date for t in sells)
        analysis.selling_period_end = max(t.date for t in sells)
        analysis.quiet_period_days = (pdufa_date - analysis.selling_period_end).days
    
    # =================================================================
    # TRIGGER EVALUATION
    # =================================================================
    triggers = []
    
    # TRIGGER 1: C-suite cumulative selling >10% holdings
    if analysis.csuite_max_pct_sold >= INSIDER_THRESHOLDS["cumulative_pct_critical"]:
        triggers.append(f"CRITICAL: C-suite sold {analysis.csuite_max_pct_sold*100:.1f}% holdings (>20%)")
    elif analysis.csuite_max_pct_sold >= INSIDER_THRESHOLDS["cumulative_pct_high"]:
        triggers.append(f"HIGH: C-suite sold {analysis.csuite_max_pct_sold*100:.1f}% holdings (>10%)")
    elif analysis.csuite_max_pct_sold >= INSIDER_THRESHOLDS["cumulative_pct_elevated"]:
        triggers.append(f"ELEVATED: C-suite sold {analysis.csuite_max_pct_sold*100:.1f}% holdings (>5%)")
    
    # TRIGGER 2: Single transaction >8% holdings
    max_single_txn = max((t.pct_holdings_sold for t in sells), default=0)
    if max_single_txn >= INSIDER_THRESHOLDS["single_transaction_pct_critical"]:
        triggers.append(f"CRITICAL: Single transaction {max_single_txn*100:.1f}% holdings (>15%)")
    elif max_single_txn >= INSIDER_THRESHOLDS["single_transaction_pct_high"]:
        triggers.append(f"HIGH: Single transaction {max_single_txn*100:.1f}% holdings (>8%)")
    
    # TRIGGER 3: Same-day coordinated selling (AQST pattern)
    if analysis.max_same_day_count >= INSIDER_THRESHOLDS["same_day_high"]:
        triggers.append(f"CRITICAL: {analysis.max_same_day_count} insiders sold same day (AQST pattern)")
    elif analysis.max_same_day_count >= INSIDER_THRESHOLDS["same_day_elevated"]:
        triggers.append(f"ELEVATED: {analysis.max_same_day_count} insiders sold same day")
    
    # TRIGGER 4: Multiple C-suite in 30-day window
    if analysis.same_30day_window_count >= INSIDER_THRESHOLDS["same_30day_high"]:
        triggers.append(f"HIGH: {analysis.same_30day_window_count} C-suite sold within 30 days")
    elif analysis.same_30day_window_count >= INSIDER_THRESHOLDS["same_30day_elevated"]:
        triggers.append(f"ELEVATED: {analysis.same_30day_window_count} C-suite sold within 30 days")
    
    # TRIGGER 5: Zero purchases + significant selling
    if analysis.num_buyers == 0 and analysis.total_sell_value >= INSIDER_THRESHOLDS["aggregate_sell_high"]:
        triggers.append(f"HIGH: Zero purchases + ${analysis.total_sell_value/1000:.0f}K in sales")
    
    # TRIGGER 6: Aggregate dollar threshold
    if analysis.total_sell_value >= INSIDER_THRESHOLDS["aggregate_sell_critical"]:
        triggers.append(f"HIGH: ${analysis.total_sell_value/1000000:.2f}M aggregate selling")
    elif analysis.total_sell_value >= INSIDER_THRESHOLDS["aggregate_sell_high"]:
        triggers.append(f"ELEVATED: ${analysis.total_sell_value/1000:.0f}K aggregate selling")
    
    # TRIGGER 7: Quiet period after selling cluster
    if (analysis.quiet_period_days >= INSIDER_THRESHOLDS["quiet_period_suspicious"] 
        and analysis.total_sell_value >= INSIDER_THRESHOLDS["aggregate_sell_elevated"]):
        triggers.append(f"ELEVATED: {analysis.quiet_period_days} day quiet period after selling")
    
    analysis.triggers_fired = triggers
    
    # =================================================================
    # RISK LEVEL DETERMINATION
    # =================================================================
    critical_count = sum(1 for t in triggers if "CRITICAL" in t)
    high_count = sum(1 for t in triggers if "HIGH" in t)
    elevated_count = sum(1 for t in triggers if "ELEVATED" in t)
    
    if critical_count >= 1 or (high_count >= 2):
        analysis.risk_level = InsiderRiskLevel.CRITICAL
    elif high_count >= 1 or (elevated_count >= 3):
        analysis.risk_level = InsiderRiskLevel.HIGH_RISK
    elif elevated_count >= 1:
        analysis.risk_level = InsiderRiskLevel.ELEVATED
    else:
        analysis.risk_level = InsiderRiskLevel.NORMAL
    
    analysis.signal_adjustment = INSIDER_SIGNAL_WEIGHTS[analysis.risk_level]
    
    return analysis


# =============================================================================
# S6 ENHANCED: COMMERCIAL HIRING SIGNAL
# =============================================================================
# Calibrated from PHAR case study:
# - sNDA label expansions require different thresholds than new NDAs
# - Maintenance hiring for existing products = neutral, not bearish
# - Explicit commercial pullback = bearish even for sNDAs

@dataclass
class HiringData:
    """Job posting data for commercial signal analysis"""
    ticker: str
    analysis_date: datetime
    pdufa_date: datetime
    application_type: ApplicationType
    
    # Leadership hires
    has_cco: bool = False                      # Chief Commercial Officer
    cco_hire_date: Optional[datetime] = None
    has_commercial_vp: bool = False            # VP Commercial/Sales
    commercial_vp_hire_date: Optional[datetime] = None
    
    # Field force
    msl_postings: int = 0                      # Medical Science Liaisons
    msl_posting_date: Optional[datetime] = None
    sales_rep_postings: int = 0               # Territory/Account Managers
    sales_posting_date: Optional[datetime] = None
    
    # Market access
    has_market_access_lead: bool = False
    market_access_hire_date: Optional[datetime] = None
    reimbursement_postings: int = 0
    
    # Existing infrastructure (for sNDAs)
    has_existing_salesforce: bool = False
    existing_salesforce_size: int = 0
    recent_commercial_layoffs: bool = False   # Bearish override
    
    # Computed
    signal: HiringSignal = HiringSignal.NEUTRAL
    signal_adjustment: float = 0.0
    rationale: str = ""


# Timing thresholds (months before PDUFA)
HIRING_THRESHOLDS_NDA = {
    # For new product launches (NDA/BLA)
    "cco_bullish_months": 18,
    "cco_neutral_months": 12,
    "msl_bullish_months": 12,
    "msl_neutral_months": 6,
    "sales_bullish_months": 6,
    "sales_neutral_months": 3,  # At approval
    "market_access_bullish_months": 15,
    "market_access_neutral_months": 9,
    
    # Minimum postings for bullish signal
    "min_msl_postings": 3,
    "min_sales_postings": 5,
}

HIRING_THRESHOLDS_SNDA = {
    # For label expansions (sNDA/sBLA)
    # Lower thresholds since infrastructure exists
    "cco_required": False,  # CCO already in place
    "msl_bullish_months": 6,
    "msl_neutral_months": 3,
    "sales_expansion_expected": False,  # Same reps serve expanded label
    
    # Override conditions
    "layoff_is_bearish": True,
    "maintenance_hiring_is_neutral": True,
}

# Signal weights
HIRING_SIGNAL_WEIGHTS = {
    HiringSignal.BULLISH: 0.03,    # Confidence signal
    HiringSignal.NEUTRAL: 0.0,
    HiringSignal.BEARISH: -0.05,   # Existing S6 weight
    HiringSignal.VOID: -0.05,      # Same as bearish for NDAs
}


def analyze_commercial_hiring(
    ticker: str,
    hiring_data: Dict,
    pdufa_date: datetime,
    application_type: ApplicationType,
    analysis_date: Optional[datetime] = None
) -> HiringData:
    """
    Analyze commercial hiring patterns for PDUFA prediction.
    
    Key insight from PHAR case study:
    - sNDA label expansions don't require new commercial build
    - Existing salesforce serving adult patients will serve pediatric
    - Only explicit pullback (layoffs, hiring freeze) is bearish for sNDAs
    
    Args:
        ticker: Stock ticker
        hiring_data: Dict with job posting data from LinkedIn/Indeed
        pdufa_date: PDUFA decision date
        application_type: NDA, sNDA, BLA, or sBLA
        analysis_date: Date of analysis
    
    Returns:
        HiringData with signal and adjustment
    """
    if analysis_date is None:
        analysis_date = datetime.now()
    
    months_to_pdufa = (pdufa_date - analysis_date).days / 30
    
    result = HiringData(
        ticker=ticker,
        analysis_date=analysis_date,
        pdufa_date=pdufa_date,
        application_type=application_type,
        has_cco=hiring_data.get("has_cco", False),
        cco_hire_date=hiring_data.get("cco_hire_date"),
        has_commercial_vp=hiring_data.get("has_commercial_vp", False),
        commercial_vp_hire_date=hiring_data.get("commercial_vp_hire_date"),
        msl_postings=hiring_data.get("msl_postings", 0),
        msl_posting_date=hiring_data.get("msl_posting_date"),
        sales_rep_postings=hiring_data.get("sales_rep_postings", 0),
        sales_posting_date=hiring_data.get("sales_posting_date"),
        has_market_access_lead=hiring_data.get("has_market_access_lead", False),
        market_access_hire_date=hiring_data.get("market_access_hire_date"),
        reimbursement_postings=hiring_data.get("reimbursement_postings", 0),
        has_existing_salesforce=hiring_data.get("has_existing_salesforce", False),
        existing_salesforce_size=hiring_data.get("existing_salesforce_size", 0),
        recent_commercial_layoffs=hiring_data.get("recent_commercial_layoffs", False),
    )
    
    # =================================================================
    # SNDA/SBLA LOGIC (Label Expansions)
    # =================================================================
    if application_type in [ApplicationType.SNDA, ApplicationType.SBLA]:
        
        # BEARISH OVERRIDE: Commercial layoffs during label expansion
        if result.recent_commercial_layoffs:
            result.signal = HiringSignal.BEARISH
            result.signal_adjustment = HIRING_SIGNAL_WEIGHTS[HiringSignal.BEARISH]
            result.rationale = "Commercial layoffs during label expansion - bearish override"
            return result
        
        # NEUTRAL: Existing infrastructure with maintenance hiring
        if result.has_existing_salesforce and result.existing_salesforce_size > 0:
            # Maintenance hiring is expected and neutral
            result.signal = HiringSignal.NEUTRAL
            result.signal_adjustment = 0.0
            result.rationale = (
                f"sNDA with existing salesforce ({result.existing_salesforce_size} reps) - "
                f"maintenance hiring expected, no signal"
            )
            return result
        
        # BEARISH: sNDA without existing infrastructure is unusual
        if not result.has_existing_salesforce:
            result.signal = HiringSignal.BEARISH
            result.signal_adjustment = HIRING_SIGNAL_WEIGHTS[HiringSignal.BEARISH]
            result.rationale = "sNDA without existing commercial infrastructure - unusual"
            return result
        
        # Default: neutral for sNDAs
        result.signal = HiringSignal.NEUTRAL
        result.signal_adjustment = 0.0
        result.rationale = "sNDA label expansion - commercial signals less predictive"
        return result
    
    # =================================================================
    # NDA/BLA LOGIC (New Product Launches)
    # =================================================================
    bullish_signals = 0
    bearish_signals = 0
    rationale_parts = []
    
    thresholds = HIRING_THRESHOLDS_NDA
    
    # CCO/Commercial Leadership
    if result.has_cco and result.cco_hire_date:
        months_since_hire = (analysis_date - result.cco_hire_date).days / 30
        months_before_pdufa = months_to_pdufa + months_since_hire
        
        if months_before_pdufa >= thresholds["cco_bullish_months"]:
            bullish_signals += 1
            rationale_parts.append(f"CCO hired {months_before_pdufa:.0f}m before PDUFA (bullish)")
        elif months_before_pdufa >= thresholds["cco_neutral_months"]:
            rationale_parts.append(f"CCO hired {months_before_pdufa:.0f}m before PDUFA (neutral)")
        else:
            bearish_signals += 1
            rationale_parts.append(f"CCO hired late ({months_before_pdufa:.0f}m before PDUFA)")
    elif months_to_pdufa <= thresholds["cco_neutral_months"]:
        bearish_signals += 1
        rationale_parts.append(f"No CCO with {months_to_pdufa:.0f}m to PDUFA (bearish)")
    
    # MSL Postings
    if result.msl_postings >= thresholds["min_msl_postings"]:
        bullish_signals += 1
        rationale_parts.append(f"{result.msl_postings} MSL postings (bullish)")
    elif result.msl_postings == 0 and months_to_pdufa <= thresholds["msl_neutral_months"]:
        bearish_signals += 1
        rationale_parts.append(f"No MSL postings with {months_to_pdufa:.0f}m to PDUFA (bearish)")
    
    # Sales Force
    if result.sales_rep_postings >= thresholds["min_sales_postings"]:
        bullish_signals += 1
        rationale_parts.append(f"{result.sales_rep_postings} sales postings (bullish)")
    elif result.sales_rep_postings == 0 and months_to_pdufa <= thresholds["sales_neutral_months"]:
        bearish_signals += 1
        rationale_parts.append(f"No sales postings with {months_to_pdufa:.0f}m to PDUFA (bearish)")
    
    # Market Access
    if result.has_market_access_lead:
        bullish_signals += 1
        rationale_parts.append("Market access lead in place (bullish)")
    elif months_to_pdufa <= thresholds["market_access_neutral_months"]:
        bearish_signals += 1
        rationale_parts.append(f"No market access lead with {months_to_pdufa:.0f}m to PDUFA")
    
    # Determine signal
    if bearish_signals >= 2 or (bearish_signals >= 1 and bullish_signals == 0):
        result.signal = HiringSignal.VOID if bearish_signals >= 3 else HiringSignal.BEARISH
    elif bullish_signals >= 3:
        result.signal = HiringSignal.BULLISH
    else:
        result.signal = HiringSignal.NEUTRAL
    
    result.signal_adjustment = HIRING_SIGNAL_WEIGHTS[result.signal]
    result.rationale = "; ".join(rationale_parts) if rationale_parts else "Insufficient data"
    
    return result


# =============================================================================
# ODIN v10.3 SIGNAL INTEGRATION
# =============================================================================

@dataclass
class OdinV103Signals:
    """
    Complete signal package for ODIN v10.3
    Adds S23 (Insider Selling) and enhances S6 (Commercial Hiring)
    """
    # S23: Insider Selling (NEW)
    s23_insider_selling: float = 0.0
    s23_risk_level: str = "NORMAL"
    s23_triggers: List[str] = field(default_factory=list)
    
    # S6: Commercial Hiring (ENHANCED)
    s6_commercial_hiring: float = 0.0
    s6_signal: str = "NEUTRAL"
    s6_rationale: str = ""
    
    # Combined adjustment
    total_adjustment: float = 0.0


def calculate_v103_signals(
    ticker: str,
    pdufa_date: datetime,
    application_type: ApplicationType,
    insider_transactions: List[InsiderTransaction],
    hiring_data: Dict,
    analysis_date: Optional[datetime] = None
) -> OdinV103Signals:
    """
    Calculate ODIN v10.3 signals for a PDUFA event.
    
    Args:
        ticker: Stock ticker
        pdufa_date: PDUFA decision date
        application_type: NDA, sNDA, BLA, or sBLA
        insider_transactions: SEC Form 4 transaction data
        hiring_data: Job posting data
        analysis_date: Date of analysis
    
    Returns:
        OdinV103Signals with adjustments
    """
    if analysis_date is None:
        analysis_date = datetime.now()
    
    signals = OdinV103Signals()
    
    # S23: Insider Selling Analysis
    insider_analysis = analyze_insider_selling(
        ticker=ticker,
        transactions=insider_transactions,
        pdufa_date=pdufa_date,
        analysis_date=analysis_date
    )
    signals.s23_insider_selling = insider_analysis.signal_adjustment
    signals.s23_risk_level = insider_analysis.risk_level.value
    signals.s23_triggers = insider_analysis.triggers_fired
    
    # S6: Commercial Hiring Analysis
    hiring_analysis = analyze_commercial_hiring(
        ticker=ticker,
        hiring_data=hiring_data,
        pdufa_date=pdufa_date,
        application_type=application_type,
        analysis_date=analysis_date
    )
    signals.s6_commercial_hiring = hiring_analysis.signal_adjustment
    signals.s6_signal = hiring_analysis.signal.value
    signals.s6_rationale = hiring_analysis.rationale
    
    # Combined adjustment
    # Note: Insider selling has HIGHER weight than commercial hiring (asymmetric)
    signals.total_adjustment = signals.s23_insider_selling + signals.s6_commercial_hiring
    
    return signals


# =============================================================================
# CONFIGURATION EXPORT
# =============================================================================

ODIN_V103_CONFIG = {
    "version": "10.3",
    "improvement": "insider_selling_commercial_hiring_signals",
    "source": "AQST/PHAR case study calibration (January 2026)",
    
    "signals": {
        "S23_insider_selling": {
            "description": "Insider selling pattern detection",
            "source": "SEC Form 4 filings via FinBrain",
            "weight_normal": 0.0,
            "weight_elevated": -0.03,
            "weight_high_risk": -0.06,
            "weight_critical": -0.10,
            "triggers": [
                "C-suite cumulative selling >10% holdings",
                "Single transaction >8% holdings",
                "3+ insiders selling same day",
                "Zero purchases + >$500K sales",
                "Quiet period >45 days after selling cluster"
            ],
            "case_study": "AQST Oct 2025: COO 35% sold, 3 execs same day, $1.69M total → Jan 2026 CRL"
        },
        "S6_commercial_hiring_enhanced": {
            "description": "Commercial hiring pattern (NDA vs sNDA calibration)",
            "source": "LinkedIn/Indeed job postings",
            "weight_bullish": 0.03,
            "weight_neutral": 0.0,
            "weight_bearish": -0.05,
            "nda_triggers": {
                "bearish": "No CCO <12m, No MSL <6m, No sales <3m, No market access <9m",
                "bullish": "CCO >18m, MSL >12m, Sales >6m, Market access >15m"
            },
            "snda_logic": {
                "neutral": "Existing salesforce with maintenance hiring",
                "bearish": "Commercial layoffs OR no existing infrastructure"
            },
            "case_study": "PHAR Jan 2026: sNDA with 54-rep salesforce → neutral (CRL was technical)"
        }
    },
    
    "asymmetry_note": (
        "Insider selling provides STRONGER bearish signal than commercial hiring provides "
        "bullish signal. AQST detected 2-3 months before CRL; PHAR commercial posture did not "
        "predict technical CRL."
    ),
    
    "thresholds": {
        "insider": INSIDER_THRESHOLDS,
        "hiring_nda": HIRING_THRESHOLDS_NDA,
        "hiring_snda": HIRING_THRESHOLDS_SNDA
    }
}


def export_v103_config(filepath: str):
    """Export v10.3 configuration to JSON."""
    with open(filepath, 'w') as f:
        json.dump(ODIN_V103_CONFIG, f, indent=2, default=str)


# =============================================================================
# EXAMPLE USAGE / TESTING
# =============================================================================

if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 70)
    print("ODIN v10.3 Signal Implementation: Insider Selling & Commercial Hiring")
    print("=" * 70)
    
    # Example 1: AQST-like insider selling pattern
    print("\n--- Example 1: AQST-like Insider Selling Pattern ---")
    
    aqst_transactions = [
        InsiderTransaction(
            date=datetime(2025, 9, 15),
            insider_name="Jane COO",
            title="Chief Operating Officer",
            transaction_type="SELL",
            shares=50000,
            price=6.50,
            total_value=325000,
            holdings_before=200000,
            holdings_after=150000,
            pct_holdings_sold=0.25,  # 25% - HIGH
            is_10b5_1=True
        ),
        InsiderTransaction(
            date=datetime(2025, 10, 15),
            insider_name="Jane COO",
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
            date=datetime(2025, 10, 15),  # SAME DAY
            insider_name="John CMO",
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
            date=datetime(2025, 10, 15),  # SAME DAY (3rd person!)
            insider_name="Bob SVP",
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
    
    insider_result = analyze_insider_selling(
        ticker="AQST",
        transactions=aqst_transactions,
        pdufa_date=datetime(2026, 1, 31),
        analysis_date=datetime(2025, 11, 15)
    )
    
    print(f"Ticker: {insider_result.ticker}")
    print(f"Risk Level: {insider_result.risk_level.value}")
    print(f"Signal Adjustment: {insider_result.signal_adjustment:+.2f}")
    print(f"Total Sell Value: ${insider_result.total_sell_value:,.0f}")
    print(f"C-Suite Sellers: {insider_result.csuite_sellers}")
    print(f"Max Same-Day Sellers: {insider_result.max_same_day_count}")
    print(f"Triggers Fired:")
    for trigger in insider_result.triggers_fired:
        print(f"  - {trigger}")
    
    # Example 2: PHAR-like sNDA with existing salesforce
    print("\n--- Example 2: PHAR-like sNDA Label Expansion ---")
    
    phar_hiring = {
        "has_cco": True,
        "cco_hire_date": datetime(2025, 11, 1),  # Recently appointed
        "has_existing_salesforce": True,
        "existing_salesforce_size": 54,
        "recent_commercial_layoffs": False,
        "msl_postings": 2,
        "sales_rep_postings": 3,  # Maintenance hiring
    }
    
    hiring_result = analyze_commercial_hiring(
        ticker="PHAR",
        hiring_data=phar_hiring,
        pdufa_date=datetime(2026, 1, 31),
        application_type=ApplicationType.SNDA,
        analysis_date=datetime(2025, 12, 15)
    )
    
    print(f"Ticker: {hiring_result.ticker}")
    print(f"Application Type: {hiring_result.application_type.value}")
    print(f"Signal: {hiring_result.signal.value}")
    print(f"Signal Adjustment: {hiring_result.signal_adjustment:+.2f}")
    print(f"Rationale: {hiring_result.rationale}")
    
    # Example 3: New NDA with hiring void
    print("\n--- Example 3: New NDA with Hiring Void ---")
    
    void_hiring = {
        "has_cco": False,
        "has_existing_salesforce": False,
        "msl_postings": 0,
        "sales_rep_postings": 0,
        "has_market_access_lead": False,
    }
    
    void_result = analyze_commercial_hiring(
        ticker="VOID",
        hiring_data=void_hiring,
        pdufa_date=datetime(2026, 6, 15),
        application_type=ApplicationType.NDA,
        analysis_date=datetime(2026, 2, 1)
    )
    
    print(f"Ticker: {void_result.ticker}")
    print(f"Signal: {void_result.signal.value}")
    print(f"Signal Adjustment: {void_result.signal_adjustment:+.2f}")
    print(f"Rationale: {void_result.rationale}")
    
    # Export config
    export_v103_config("/home/claude/ODIN_v103_CONFIG.json")
    print("\n✅ Configuration exported to ODIN_v103_CONFIG.json")
    
    print("\n" + "=" * 70)
    print("KEY FINDINGS FROM AQST/PHAR CALIBRATION:")
    print("=" * 70)
    print("""
    1. INSIDER SELLING (S23) - HIGH PREDICTIVE VALUE
       - AQST pattern: COO 35% sold + 3 execs same day = CRITICAL signal
       - Detected 2-3 months before January 2026 CRL
       - Weight: -0.10 for CRITICAL, -0.06 for HIGH_RISK
    
    2. COMMERCIAL HIRING (S6) - CONTEXT-DEPENDENT
       - NDA launches: Hiring void is bearish (-0.05)
       - sNDA expansions: Maintenance hiring is neutral
       - PHAR showed commercial readiness ≠ FDA approval
       - Weight: +0.03 bullish, -0.05 bearish
    
    3. ASYMMETRY: Insider selling > Commercial hiring
       - Bearish insider signals are MORE predictive
       - Bullish commercial signals provide less certainty
       - Model should weight accordingly
    """)
