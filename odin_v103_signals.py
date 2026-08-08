"""
ODIN v10.3 Signals Module - Insider Trading & Commercial Hiring
================================================================
Calibrated from AQST (Jan 2026 CRL) and PHAR (Jan 2026 CRL) case studies.

Key insight: Insider selling provides STRONGER bearish signal than commercial
hiring provides bullish signal. AQST's C-suite coordinated selling was 
detectable 2-3 months before FDA deficiency letter disclosure.

Signals implemented:
- S23: Insider Trading Signal (bearish asymmetric)
- S6: Commercial Hiring Signal (enhanced for NDA vs sNDA)

Data sources:
- SEC Form 4 filings (via FinBrain API)
- Job postings (LinkedIn/Indeed)

T-1 Compliance: All data must be publicly available before PDUFA date.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class ApplicationType(Enum):
    """Distinguish NDA (new drug) from sNDA (label expansion)"""
    NDA = "NDA"           # New Drug Application - full commercial buildout expected
    SNDA = "sNDA"         # Supplemental NDA - maintenance hiring acceptable
    BLA = "BLA"           # Biologics License Application
    SBLA = "sBLA"         # Supplemental BLA


class InsiderRole(Enum):
    """Insider classification by role importance"""
    CEO = "CEO"
    CFO = "CFO"
    COO = "COO"
    CMO = "CMO"           # Chief Medical Officer
    CCO = "CCO"           # Chief Commercial Officer
    CSO = "CSO"           # Chief Scientific Officer
    PRESIDENT = "President"
    SVP = "SVP"
    VP = "VP"
    DIRECTOR = "Director"
    OTHER = "Other"


# C-suite roles carry higher signal weight
C_SUITE_ROLES = {InsiderRole.CEO, InsiderRole.CFO, InsiderRole.COO, 
                 InsiderRole.CMO, InsiderRole.CCO, InsiderRole.CSO, 
                 InsiderRole.PRESIDENT}


class RiskLevel(Enum):
    """Risk classification for signals"""
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# S23: INSIDER TRADING SIGNAL
# =============================================================================
# Calibrated from AQST case study where:
# - COO sold 35% cumulative holdings
# - 3 executives sold on same day (Oct 15, 2025)
# - 100% sell ratio (zero purchases)
# - Selling clustered 60-120 days before FDA deficiency letter

@dataclass
class InsiderTransaction:
    """Single insider transaction from SEC Form 4"""
    transaction_date: datetime
    insider_name: str
    insider_role: InsiderRole
    transaction_type: str  # "BUY" or "SELL"
    shares: int
    price_per_share: float
    total_value: float
    shares_held_after: int
    percent_of_holdings: float  # % of holdings this transaction represents
    is_10b5_1: bool = False     # Under 10b5-1 trading plan


@dataclass 
class InsiderSellingThresholds:
    """
    Calibrated thresholds from AQST analysis.
    Trigger ANY single threshold for elevated scrutiny.
    """
    # Threshold 1: Cumulative selling percentage
    cumulative_selling_pct_6mo: float = 0.10  # >10% of holdings in 6 months
    
    # Threshold 2: Single transaction size
    single_transaction_pct: float = 0.08  # >8% in one transaction
    
    # Threshold 3: Coordinated C-suite selling
    csuite_selling_window_days: int = 30
    csuite_selling_min_count: int = 2  # 2+ C-suite in same window
    
    # Threshold 4: Same-day cluster selling
    same_day_insider_count: int = 3  # 3+ insiders same day
    
    # Threshold 5: Aggregate selling with no purchases
    aggregate_selling_threshold: float = 500_000  # >$500K with zero buys
    
    # Threshold 6: Temporal clustering before quiet period
    clustering_window_start_days: int = 120  # 60-120 days before PDUFA
    clustering_window_end_days: int = 60
    quiet_period_days: int = 45  # Days before PDUFA with no sales
    
    # Signal weights (asymmetric - selling stronger than buying)
    weight_low: float = 0.0
    weight_elevated: float = -0.03
    weight_high: float = -0.06
    weight_critical: float = -0.10


@dataclass
class InsiderSignalResult:
    """Result of S23 insider trading analysis"""
    signal_code: str = "S23"
    signal_name: str = "Insider Trading"
    risk_level: RiskLevel = RiskLevel.LOW
    score_adjustment: float = 0.0
    triggers_fired: List[str] = field(default_factory=list)
    
    # Detailed metrics
    total_sells: int = 0
    total_buys: int = 0
    sell_buy_ratio: float = 0.0
    aggregate_sell_value: float = 0.0
    aggregate_buy_value: float = 0.0
    max_single_transaction_pct: float = 0.0
    csuite_sellers_in_window: int = 0
    max_same_day_sellers: int = 0
    has_quiet_period_after_cluster: bool = False
    
    rationale: str = ""


def classify_insider_role(title: str) -> InsiderRole:
    """Parse insider title to role enum"""
    title_upper = title.upper()
    
    if "CEO" in title_upper or "CHIEF EXECUTIVE" in title_upper:
        return InsiderRole.CEO
    elif "CFO" in title_upper or "CHIEF FINANCIAL" in title_upper:
        return InsiderRole.CFO
    elif "COO" in title_upper or "CHIEF OPERATING" in title_upper:
        return InsiderRole.COO
    elif "CMO" in title_upper or "CHIEF MEDICAL" in title_upper:
        return InsiderRole.CMO
    elif "CCO" in title_upper or "CHIEF COMMERCIAL" in title_upper:
        return InsiderRole.CCO
    elif "CSO" in title_upper or "CHIEF SCIENTIFIC" in title_upper:
        return InsiderRole.CSO
    elif "PRESIDENT" in title_upper:
        return InsiderRole.PRESIDENT
    elif "SVP" in title_upper or "SENIOR VICE" in title_upper:
        return InsiderRole.SVP
    elif "VP" in title_upper or "VICE PRESIDENT" in title_upper:
        return InsiderRole.VP
    elif "DIRECTOR" in title_upper:
        return InsiderRole.DIRECTOR
    else:
        return InsiderRole.OTHER


def analyze_insider_trading(
    transactions: List[InsiderTransaction],
    pdufa_date: datetime,
    lookback_months: int = 6,
    thresholds: InsiderSellingThresholds = None
) -> InsiderSignalResult:
    """
    Analyze insider trading patterns for S23 signal.
    
    Args:
        transactions: List of SEC Form 4 transactions
        pdufa_date: PDUFA action date
        lookback_months: Months before PDUFA to analyze (default 6)
        thresholds: Calibrated thresholds (uses defaults if None)
    
    Returns:
        InsiderSignalResult with risk level and score adjustment
    """
    if thresholds is None:
        thresholds = InsiderSellingThresholds()
    
    result = InsiderSignalResult()
    
    # Filter to lookback window
    lookback_start = pdufa_date - timedelta(days=lookback_months * 30)
    relevant_txns = [
        t for t in transactions
        if lookback_start <= t.transaction_date < pdufa_date
    ]
    
    if not relevant_txns:
        result.rationale = "No insider transactions in lookback window"
        return result
    
    # Separate buys and sells
    sells = [t for t in relevant_txns if t.transaction_type == "SELL"]
    buys = [t for t in relevant_txns if t.transaction_type == "BUY"]
    
    result.total_sells = len(sells)
    result.total_buys = len(buys)
    result.aggregate_sell_value = sum(t.total_value for t in sells)
    result.aggregate_buy_value = sum(t.total_value for t in buys)
    
    # Sell/buy ratio (handle zero buys)
    if result.total_buys > 0:
        result.sell_buy_ratio = result.total_sells / result.total_buys
    else:
        result.sell_buy_ratio = float('inf') if result.total_sells > 0 else 0
    
    # =========================================================================
    # CHECK EACH THRESHOLD
    # =========================================================================
    
    # Threshold 1: Cumulative selling by individual
    insider_cumulative = {}
    for t in sells:
        if t.insider_name not in insider_cumulative:
            insider_cumulative[t.insider_name] = {
                'total_pct': 0.0,
                'role': t.insider_role,
                'transactions': []
            }
        insider_cumulative[t.insider_name]['total_pct'] += t.percent_of_holdings
        insider_cumulative[t.insider_name]['transactions'].append(t)
    
    high_sellers = [
        (name, data) for name, data in insider_cumulative.items()
        if data['total_pct'] > thresholds.cumulative_selling_pct_6mo
    ]
    
    if high_sellers:
        result.triggers_fired.append(
            f"T1_CUMULATIVE: {len(high_sellers)} insider(s) sold >{thresholds.cumulative_selling_pct_6mo*100:.0f}% holdings"
        )
        for name, data in high_sellers:
            result.triggers_fired.append(
                f"  - {name} ({data['role'].value}): {data['total_pct']*100:.1f}% sold"
            )
    
    # Threshold 2: Single large transaction
    if sells:
        result.max_single_transaction_pct = max(t.percent_of_holdings for t in sells)
        if result.max_single_transaction_pct > thresholds.single_transaction_pct:
            result.triggers_fired.append(
                f"T2_SINGLE_TXN: Transaction of {result.max_single_transaction_pct*100:.1f}% "
                f"(>{thresholds.single_transaction_pct*100:.0f}% threshold)"
            )
    
    # Threshold 3: Coordinated C-suite selling
    csuite_sells = [t for t in sells if t.insider_role in C_SUITE_ROLES]
    if csuite_sells:
        # Check for clustering within window
        csuite_sells_sorted = sorted(csuite_sells, key=lambda x: x.transaction_date)
        window_end = thresholds.csuite_selling_window_days
        
        for i, txn in enumerate(csuite_sells_sorted):
            sellers_in_window = set()
            sellers_in_window.add(txn.insider_name)
            
            for other in csuite_sells_sorted[i+1:]:
                if (other.transaction_date - txn.transaction_date).days <= window_end:
                    sellers_in_window.add(other.insider_name)
            
            if len(sellers_in_window) > result.csuite_sellers_in_window:
                result.csuite_sellers_in_window = len(sellers_in_window)
        
        if result.csuite_sellers_in_window >= thresholds.csuite_selling_min_count:
            result.triggers_fired.append(
                f"T3_CSUITE_CLUSTER: {result.csuite_sellers_in_window} C-suite executives "
                f"sold within {thresholds.csuite_selling_window_days}-day window"
            )
    
    # Threshold 4: Same-day cluster
    by_date = {}
    for t in sells:
        date_key = t.transaction_date.date()
        if date_key not in by_date:
            by_date[date_key] = set()
        by_date[date_key].add(t.insider_name)
    
    for date_key, sellers in by_date.items():
        if len(sellers) > result.max_same_day_sellers:
            result.max_same_day_sellers = len(sellers)
    
    if result.max_same_day_sellers >= thresholds.same_day_insider_count:
        result.triggers_fired.append(
            f"T4_SAME_DAY: {result.max_same_day_sellers} insiders sold on same day "
            f"(>={thresholds.same_day_insider_count} threshold)"
        )
    
    # Threshold 5: Aggregate selling with no purchases
    if (result.total_buys == 0 and 
        result.aggregate_sell_value > thresholds.aggregate_selling_threshold):
        result.triggers_fired.append(
            f"T5_NO_BUYS: ${result.aggregate_sell_value:,.0f} in sales with ZERO purchases"
        )
    
    # Threshold 6: Clustering followed by quiet period
    cluster_start = pdufa_date - timedelta(days=thresholds.clustering_window_start_days)
    cluster_end = pdufa_date - timedelta(days=thresholds.clustering_window_end_days)
    quiet_start = pdufa_date - timedelta(days=thresholds.quiet_period_days)
    
    cluster_sells = [
        t for t in sells 
        if cluster_start <= t.transaction_date <= cluster_end
    ]
    quiet_period_sells = [
        t for t in sells
        if quiet_start <= t.transaction_date < pdufa_date
    ]
    
    if cluster_sells and not quiet_period_sells:
        result.has_quiet_period_after_cluster = True
        result.triggers_fired.append(
            f"T6_CLUSTER_QUIET: {len(cluster_sells)} sales in cluster window "
            f"({thresholds.clustering_window_start_days}-{thresholds.clustering_window_end_days}d pre-PDUFA), "
            f"then quiet period"
        )
    
    # =========================================================================
    # DETERMINE RISK LEVEL AND SCORE
    # =========================================================================
    
    num_triggers = len([t for t in result.triggers_fired if t.startswith("T")])
    
    if num_triggers >= 4:
        result.risk_level = RiskLevel.CRITICAL
        result.score_adjustment = thresholds.weight_critical
        result.rationale = f"CRITICAL: {num_triggers} insider selling triggers fired (AQST-pattern match)"
    elif num_triggers >= 2:
        result.risk_level = RiskLevel.HIGH
        result.score_adjustment = thresholds.weight_high
        result.rationale = f"HIGH RISK: {num_triggers} insider selling triggers fired"
    elif num_triggers >= 1:
        result.risk_level = RiskLevel.ELEVATED
        result.score_adjustment = thresholds.weight_elevated
        result.rationale = f"ELEVATED: {num_triggers} insider selling trigger(s) fired"
    else:
        result.risk_level = RiskLevel.LOW
        result.score_adjustment = thresholds.weight_low
        result.rationale = "Normal insider trading pattern"
    
    return result


# =============================================================================
# S6: COMMERCIAL HIRING SIGNAL (ENHANCED)
# =============================================================================
# Calibrated from PHAR case study - label expansions don't require
# full commercial buildout, so "hiring void" signal must distinguish
# NDA (new launch) from sNDA (existing product expansion).

@dataclass
class CommercialHiringData:
    """Commercial hiring status for a company pre-PDUFA"""
    has_cco_or_commercial_leadership: bool = False
    cco_hire_months_before_pdufa: Optional[int] = None
    
    has_msl_postings: bool = False
    msl_posting_months_before_pdufa: Optional[int] = None
    
    has_market_access_hiring: bool = False
    market_access_months_before_pdufa: Optional[int] = None
    
    has_sales_force_hiring: bool = False
    sales_force_months_before_pdufa: Optional[int] = None
    
    total_commercial_postings: int = 0
    
    # For sNDA context
    has_existing_commercial_infrastructure: bool = False
    existing_sales_reps: int = 0
    commercial_team_protected_in_restructuring: bool = False


@dataclass
class CommercialHiringThresholds:
    """
    Timing thresholds from McKinsey/PharmExec benchmarks.
    Earlier hiring = higher confidence.
    """
    # For NEW NDAs (full commercial buildout expected)
    cco_bullish_months: int = 18
    cco_neutral_months: int = 12
    
    msl_bullish_months: int = 12
    msl_neutral_months: int = 6
    
    market_access_bullish_months: int = 15
    market_access_neutral_months: int = 9
    
    sales_force_bullish_months: int = 6
    sales_force_neutral_months: int = 0  # At approval is neutral
    
    # Minimum postings for confidence
    min_commercial_postings_bullish: int = 5
    min_commercial_postings_neutral: int = 2
    
    # Signal weights
    weight_bullish: float = 0.02
    weight_neutral: float = 0.0
    weight_bearish: float = -0.05  # "Hiring void" for NDA
    
    # sNDA adjustment - less negative for label expansions
    snda_bearish_weight: float = -0.02  # Only for explicit pullback


@dataclass
class CommercialHiringResult:
    """Result of S6 commercial hiring analysis"""
    signal_code: str = "S6"
    signal_name: str = "Commercial Hiring"
    risk_level: RiskLevel = RiskLevel.LOW
    score_adjustment: float = 0.0
    
    is_nda: bool = True  # vs sNDA
    category_scores: Dict[str, str] = field(default_factory=dict)  # e.g., {"CCO": "BULLISH"}
    
    rationale: str = ""


def analyze_commercial_hiring(
    hiring_data: CommercialHiringData,
    months_to_pdufa: int,
    application_type: ApplicationType,
    thresholds: CommercialHiringThresholds = None
) -> CommercialHiringResult:
    """
    Analyze commercial hiring patterns for S6 signal.
    
    CRITICAL: Must distinguish NDA (new product) from sNDA (label expansion).
    PHAR case study showed maintenance hiring is appropriate for sNDAs.
    
    Args:
        hiring_data: Current commercial hiring status
        months_to_pdufa: Months until PDUFA date
        application_type: NDA, sNDA, BLA, or sBLA
        thresholds: Calibrated thresholds
    
    Returns:
        CommercialHiringResult with score adjustment
    """
    if thresholds is None:
        thresholds = CommercialHiringThresholds()
    
    result = CommercialHiringResult()
    result.is_nda = application_type in {ApplicationType.NDA, ApplicationType.BLA}
    
    # For sNDA with existing commercial infrastructure, different rules apply
    if not result.is_nda and hiring_data.has_existing_commercial_infrastructure:
        return _analyze_snda_hiring(hiring_data, thresholds, result)
    
    # =========================================================================
    # NDA ANALYSIS - Full commercial buildout expected
    # =========================================================================
    
    scores = []
    
    # CCO / Commercial Leadership
    if hiring_data.has_cco_or_commercial_leadership:
        if hiring_data.cco_hire_months_before_pdufa:
            if hiring_data.cco_hire_months_before_pdufa >= thresholds.cco_bullish_months:
                result.category_scores["CCO"] = "BULLISH"
                scores.append(1)
            elif hiring_data.cco_hire_months_before_pdufa >= thresholds.cco_neutral_months:
                result.category_scores["CCO"] = "NEUTRAL"
                scores.append(0)
            else:
                result.category_scores["CCO"] = "LATE"
                scores.append(-0.5)
        else:
            result.category_scores["CCO"] = "PRESENT"
            scores.append(0.5)
    else:
        if months_to_pdufa < thresholds.cco_neutral_months:
            result.category_scores["CCO"] = "VOID"
            scores.append(-1)
        else:
            result.category_scores["CCO"] = "PENDING"
            scores.append(0)
    
    # MSL Postings
    if hiring_data.has_msl_postings:
        if hiring_data.msl_posting_months_before_pdufa:
            if hiring_data.msl_posting_months_before_pdufa >= thresholds.msl_bullish_months:
                result.category_scores["MSL"] = "BULLISH"
                scores.append(1)
            elif hiring_data.msl_posting_months_before_pdufa >= thresholds.msl_neutral_months:
                result.category_scores["MSL"] = "NEUTRAL"
                scores.append(0)
            else:
                result.category_scores["MSL"] = "LATE"
                scores.append(-0.5)
        else:
            result.category_scores["MSL"] = "PRESENT"
            scores.append(0.5)
    else:
        if months_to_pdufa < thresholds.msl_neutral_months:
            result.category_scores["MSL"] = "VOID"
            scores.append(-1)
        else:
            result.category_scores["MSL"] = "PENDING"
            scores.append(0)
    
    # Market Access
    if hiring_data.has_market_access_hiring:
        if hiring_data.market_access_months_before_pdufa:
            if hiring_data.market_access_months_before_pdufa >= thresholds.market_access_bullish_months:
                result.category_scores["MarketAccess"] = "BULLISH"
                scores.append(1)
            elif hiring_data.market_access_months_before_pdufa >= thresholds.market_access_neutral_months:
                result.category_scores["MarketAccess"] = "NEUTRAL"
                scores.append(0)
            else:
                result.category_scores["MarketAccess"] = "LATE"
                scores.append(-0.5)
        else:
            result.category_scores["MarketAccess"] = "PRESENT"
            scores.append(0.5)
    else:
        if months_to_pdufa < thresholds.market_access_neutral_months:
            result.category_scores["MarketAccess"] = "VOID"
            scores.append(-1)
        else:
            result.category_scores["MarketAccess"] = "PENDING"
            scores.append(0)
    
    # Sales Force
    if hiring_data.has_sales_force_hiring:
        if hiring_data.sales_force_months_before_pdufa:
            if hiring_data.sales_force_months_before_pdufa >= thresholds.sales_force_bullish_months:
                result.category_scores["SalesForce"] = "BULLISH"
                scores.append(1)
            else:
                result.category_scores["SalesForce"] = "NEUTRAL"
                scores.append(0)
        else:
            result.category_scores["SalesForce"] = "PRESENT"
            scores.append(0.5)
    else:
        result.category_scores["SalesForce"] = "PENDING"
        scores.append(0)
    
    # Aggregate score
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Count voids
    void_count = sum(1 for v in result.category_scores.values() if v == "VOID")
    
    if avg_score > 0.5:
        result.risk_level = RiskLevel.LOW
        result.score_adjustment = thresholds.weight_bullish
        result.rationale = f"Strong commercial preparation ({sum(1 for s in scores if s > 0)}/4 categories bullish)"
    elif void_count >= 2:
        result.risk_level = RiskLevel.HIGH
        result.score_adjustment = thresholds.weight_bearish
        result.rationale = f"HIRING VOID: {void_count} critical commercial categories missing"
    elif avg_score < 0:
        result.risk_level = RiskLevel.ELEVATED
        result.score_adjustment = thresholds.weight_bearish * 0.5
        result.rationale = f"Weak commercial preparation (avg score {avg_score:.2f})"
    else:
        result.risk_level = RiskLevel.LOW
        result.score_adjustment = thresholds.weight_neutral
        result.rationale = "Neutral commercial hiring pattern"
    
    return result


def _analyze_snda_hiring(
    hiring_data: CommercialHiringData,
    thresholds: CommercialHiringThresholds,
    result: CommercialHiringResult
) -> CommercialHiringResult:
    """
    Specialized analysis for sNDA/sBLA label expansions.
    
    PHAR case study: Maintenance hiring is appropriate when existing
    commercial infrastructure exists. Only explicit pullback is bearish.
    """
    result.rationale = "sNDA with existing commercial infrastructure - "
    
    # Check for signs of pullback (the only bearish signal for sNDA)
    if (hiring_data.existing_sales_reps > 0 and 
        not hiring_data.commercial_team_protected_in_restructuring):
        # Potential pullback during restructuring
        result.risk_level = RiskLevel.ELEVATED
        result.score_adjustment = thresholds.snda_bearish_weight
        result.rationale += "Commercial team not protected in restructuring"
        result.category_scores["Infrastructure"] = "PULLBACK"
        return result
    
    # Otherwise, maintenance mode is appropriate
    if hiring_data.existing_sales_reps >= 30:
        result.category_scores["Infrastructure"] = "STRONG"
        result.rationale += f"Strong existing infrastructure ({hiring_data.existing_sales_reps} reps)"
    else:
        result.category_scores["Infrastructure"] = "ADEQUATE"
        result.rationale += "Adequate existing infrastructure"
    
    # CCO transition during sNDA is neutral, not concerning
    if hiring_data.has_cco_or_commercial_leadership:
        result.category_scores["Leadership"] = "PRESENT"
    else:
        result.category_scores["Leadership"] = "TRANSITION"
    
    result.risk_level = RiskLevel.LOW
    result.score_adjustment = thresholds.weight_neutral
    
    return result


# =============================================================================
# COMBINED SIGNAL SCORING
# =============================================================================

@dataclass
class OdinV103SignalResult:
    """Combined result from all v10.3 signals"""
    s23_insider: InsiderSignalResult
    s6_hiring: CommercialHiringResult
    
    total_adjustment: float = 0.0
    risk_summary: str = ""
    
    def __post_init__(self):
        self.total_adjustment = (
            self.s23_insider.score_adjustment + 
            self.s6_hiring.score_adjustment
        )
        
        # Build risk summary
        risks = []
        if self.s23_insider.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            risks.append(f"S23 Insider: {self.s23_insider.risk_level.value}")
        if self.s6_hiring.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            risks.append(f"S6 Hiring: {self.s6_hiring.risk_level.value}")
        
        self.risk_summary = " | ".join(risks) if risks else "No elevated risks"


def score_v103_signals(
    insider_transactions: List[InsiderTransaction],
    hiring_data: CommercialHiringData,
    pdufa_date: datetime,
    months_to_pdufa: int,
    application_type: ApplicationType,
    insider_thresholds: InsiderSellingThresholds = None,
    hiring_thresholds: CommercialHiringThresholds = None
) -> OdinV103SignalResult:
    """
    Score both S23 and S6 signals.
    
    Returns combined result with total score adjustment.
    """
    s23_result = analyze_insider_trading(
        transactions=insider_transactions,
        pdufa_date=pdufa_date,
        thresholds=insider_thresholds
    )
    
    s6_result = analyze_commercial_hiring(
        hiring_data=hiring_data,
        months_to_pdufa=months_to_pdufa,
        application_type=application_type,
        thresholds=hiring_thresholds
    )
    
    return OdinV103SignalResult(
        s23_insider=s23_result,
        s6_hiring=s6_result
    )


# =============================================================================
# CONFIGURATION EXPORT
# =============================================================================

def export_v103_config() -> dict:
    """Export v10.3 signal configuration as JSON"""
    insider_thresh = InsiderSellingThresholds()
    hiring_thresh = CommercialHiringThresholds()
    
    return {
        "version": "10.3",
        "signals": {
            "S23_insider_trading": {
                "description": "Insider selling patterns (AQST-calibrated)",
                "asymmetric": True,
                "note": "Selling signals stronger than buying signals",
                "thresholds": {
                    "cumulative_selling_6mo_pct": insider_thresh.cumulative_selling_pct_6mo,
                    "single_transaction_pct": insider_thresh.single_transaction_pct,
                    "csuite_window_days": insider_thresh.csuite_selling_window_days,
                    "csuite_min_count": insider_thresh.csuite_selling_min_count,
                    "same_day_insider_count": insider_thresh.same_day_insider_count,
                    "aggregate_no_buys_threshold": insider_thresh.aggregate_selling_threshold,
                    "cluster_window_start_days": insider_thresh.clustering_window_start_days,
                    "cluster_window_end_days": insider_thresh.clustering_window_end_days,
                    "quiet_period_days": insider_thresh.quiet_period_days
                },
                "weights": {
                    "LOW": insider_thresh.weight_low,
                    "ELEVATED": insider_thresh.weight_elevated,
                    "HIGH": insider_thresh.weight_high,
                    "CRITICAL": insider_thresh.weight_critical
                }
            },
            "S6_commercial_hiring": {
                "description": "Commercial hiring patterns (PHAR-calibrated)",
                "distinguishes_nda_snda": True,
                "nda_thresholds": {
                    "cco_bullish_months": hiring_thresh.cco_bullish_months,
                    "cco_neutral_months": hiring_thresh.cco_neutral_months,
                    "msl_bullish_months": hiring_thresh.msl_bullish_months,
                    "msl_neutral_months": hiring_thresh.msl_neutral_months,
                    "market_access_bullish_months": hiring_thresh.market_access_bullish_months,
                    "market_access_neutral_months": hiring_thresh.market_access_neutral_months,
                    "sales_force_bullish_months": hiring_thresh.sales_force_bullish_months,
                    "min_postings_bullish": hiring_thresh.min_commercial_postings_bullish,
                    "min_postings_neutral": hiring_thresh.min_commercial_postings_neutral
                },
                "weights": {
                    "bullish": hiring_thresh.weight_bullish,
                    "neutral": hiring_thresh.weight_neutral,
                    "bearish_nda": hiring_thresh.weight_bearish,
                    "bearish_snda": hiring_thresh.snda_bearish_weight
                }
            }
        },
        "calibration_sources": {
            "AQST_CRL_2026-01-30": {
                "trigger_count": "5/6 thresholds would have fired",
                "warning_lead_time": "2+ months before deficiency letter"
            },
            "PHAR_CRL_2026-01-31": {
                "hiring_void_would_fire": False,
                "reason": "sNDA with existing 54-rep salesforce"
            }
        }
    }


# =============================================================================
# EXAMPLE USAGE AND TESTING
# =============================================================================

if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 70)
    print("ODIN v10.3 Signals Module - Test Suite")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # Test Case 1: AQST-style insider selling (should trigger CRITICAL)
    # -------------------------------------------------------------------------
    print("\n[TEST 1] AQST-Pattern Insider Selling")
    print("-" * 50)
    
    pdufa_date = datetime(2026, 1, 31)
    
    aqst_transactions = [
        # COO selling 35% cumulative
        InsiderTransaction(
            transaction_date=datetime(2025, 9, 4),
            insider_name="Jane COO",
            insider_role=InsiderRole.COO,
            transaction_type="SELL",
            shares=50000,
            price_per_share=6.50,
            total_value=325000,
            shares_held_after=100000,
            percent_of_holdings=0.15
        ),
        InsiderTransaction(
            transaction_date=datetime(2025, 10, 15),
            insider_name="Jane COO",
            insider_role=InsiderRole.COO,
            transaction_type="SELL",
            shares=70000,
            price_per_share=7.00,
            total_value=490000,
            shares_held_after=30000,
            percent_of_holdings=0.20
        ),
        # CEO selling
        InsiderTransaction(
            transaction_date=datetime(2025, 9, 15),
            insider_name="John CEO",
            insider_role=InsiderRole.CEO,
            transaction_type="SELL",
            shares=40000,
            price_per_share=6.75,
            total_value=270000,
            shares_held_after=400000,
            percent_of_holdings=0.09
        ),
        # CMO same day as COO (Oct 15)
        InsiderTransaction(
            transaction_date=datetime(2025, 10, 15),
            insider_name="Mike CMO",
            insider_role=InsiderRole.CMO,
            transaction_type="SELL",
            shares=15000,
            price_per_share=7.00,
            total_value=105000,
            shares_held_after=80000,
            percent_of_holdings=0.06
        ),
        # SVP same day as COO (Oct 15)
        InsiderTransaction(
            transaction_date=datetime(2025, 10, 15),
            insider_name="Pete SVP",
            insider_role=InsiderRole.SVP,
            transaction_type="SELL",
            shares=25000,
            price_per_share=7.00,
            total_value=175000,
            shares_held_after=50000,
            percent_of_holdings=0.10
        ),
    ]
    
    result = analyze_insider_trading(aqst_transactions, pdufa_date)
    
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Score Adjustment: {result.score_adjustment:+.2f}")
    print(f"Total Sells: {result.total_sells}, Buys: {result.total_buys}")
    print(f"Aggregate Sell Value: ${result.aggregate_sell_value:,.0f}")
    print(f"Rationale: {result.rationale}")
    print("\nTriggers Fired:")
    for trigger in result.triggers_fired:
        print(f"  {trigger}")
    
    # -------------------------------------------------------------------------
    # Test Case 2: Normal insider activity (should be LOW risk)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Normal Insider Activity")
    print("-" * 50)
    
    normal_transactions = [
        InsiderTransaction(
            transaction_date=datetime(2025, 8, 1),
            insider_name="CEO Normal",
            insider_role=InsiderRole.CEO,
            transaction_type="SELL",
            shares=5000,
            price_per_share=10.00,
            total_value=50000,
            shares_held_after=200000,
            percent_of_holdings=0.02
        ),
        InsiderTransaction(
            transaction_date=datetime(2025, 11, 1),
            insider_name="CEO Normal",
            insider_role=InsiderRole.CEO,
            transaction_type="BUY",
            shares=3000,
            price_per_share=9.00,
            total_value=27000,
            shares_held_after=203000,
            percent_of_holdings=0.0
        ),
    ]
    
    result2 = analyze_insider_trading(normal_transactions, pdufa_date)
    print(f"Risk Level: {result2.risk_level.value}")
    print(f"Score Adjustment: {result2.score_adjustment:+.2f}")
    print(f"Rationale: {result2.rationale}")
    
    # -------------------------------------------------------------------------
    # Test Case 3: NDA with hiring void (should trigger bearish)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] NDA with Commercial Hiring Void")
    print("-" * 50)
    
    void_hiring = CommercialHiringData(
        has_cco_or_commercial_leadership=False,
        has_msl_postings=False,
        has_market_access_hiring=False,
        has_sales_force_hiring=False,
        total_commercial_postings=0
    )
    
    result3 = analyze_commercial_hiring(
        void_hiring, 
        months_to_pdufa=6,
        application_type=ApplicationType.NDA
    )
    
    print(f"Risk Level: {result3.risk_level.value}")
    print(f"Score Adjustment: {result3.score_adjustment:+.2f}")
    print(f"Category Scores: {result3.category_scores}")
    print(f"Rationale: {result3.rationale}")
    
    # -------------------------------------------------------------------------
    # Test Case 4: sNDA with existing infrastructure (PHAR pattern - neutral)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] sNDA with Existing Infrastructure (PHAR Pattern)")
    print("-" * 50)
    
    phar_hiring = CommercialHiringData(
        has_cco_or_commercial_leadership=True,
        cco_hire_months_before_pdufa=1,  # CCO transition
        has_msl_postings=True,
        has_market_access_hiring=True,
        has_sales_force_hiring=True,
        total_commercial_postings=5,
        has_existing_commercial_infrastructure=True,
        existing_sales_reps=54,
        commercial_team_protected_in_restructuring=True
    )
    
    result4 = analyze_commercial_hiring(
        phar_hiring,
        months_to_pdufa=3,
        application_type=ApplicationType.SNDA
    )
    
    print(f"Risk Level: {result4.risk_level.value}")
    print(f"Score Adjustment: {result4.score_adjustment:+.2f}")
    print(f"Category Scores: {result4.category_scores}")
    print(f"Rationale: {result4.rationale}")
    
    # -------------------------------------------------------------------------
    # Export configuration
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Exporting v10.3 Configuration")
    print("=" * 70)
    
    config = export_v103_config()
    config_path = "/home/claude/ODIN_v103_SIGNALS_CONFIG.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Config exported to {config_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("SIGNAL WEIGHT SUMMARY")
    print("=" * 70)
    print("\nS23 Insider Trading (Bearish Asymmetric):")
    print("  LOW:      +0.00")
    print("  ELEVATED: -0.03")
    print("  HIGH:     -0.06")
    print("  CRITICAL: -0.10")
    print("\nS6 Commercial Hiring:")
    print("  BULLISH (NDA):  +0.02")
    print("  NEUTRAL:        +0.00")
    print("  BEARISH (NDA):  -0.05")
    print("  BEARISH (sNDA): -0.02 (only explicit pullback)")
