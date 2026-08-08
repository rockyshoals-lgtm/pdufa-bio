#!/usr/bin/env python3
"""
ODIN Options Orchestrator v3.0
==============================
Master Controller for Options Trading Intelligence

Integrates:
- Cheapness Analysis (entry timing)
- Position Sizing (Kelly Criterion)
- Exit Triggers (dynamic exits)
- Golden Sweep Detection (smart money)
- ODIN Predictions (approval probabilities)

Produces complete trade recommendations with:
- Entry signal (BUY/WAIT/SKIP)
- Position size
- Strike/Expiration selection
- Exit calendar
- Risk parameters

Usage:
    orchestrator = OptionsOrchestrator(portfolio_value=100000)
    recommendation = orchestrator.analyze(
        ticker="RCKT",
        pdufa_date="2026-03-28",
        odin_approval_prob=0.71,
        mfg_risk_score=0.0
    )
"""

import os
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Import ODIN modules
from odin_cheapness_analyzer import CheapnessAnalyzer, quick_cheapness_check
from odin_position_sizer import PositionSizer, calculate_adjusted_volatility
from odin_exit_trigger_engine import ExitTriggerEngine, Position
from odin_golden_sweep_detector import GoldenSweepDetector, integrate_sweep_signal


class TradeAction(Enum):
    STRONG_BUY = "STRONG_BUY"     # All signals aligned
    BUY = "BUY"                   # Favorable setup
    TACTICAL_BUY = "TACTICAL_BUY" # Mixed signals, reduced size
    WAIT = "WAIT"                 # Not optimal timing
    SKIP = "SKIP"                 # Unfavorable setup


@dataclass
class TradeRecommendation:
    """Complete trade recommendation"""
    ticker: str
    pdufa_date: datetime
    analysis_date: datetime
    
    # Overall signals
    action: TradeAction
    confidence: str
    primary_reason: str
    
    # ODIN integration
    odin_approval_prob: float
    odin_adjusted_prob: float
    mfg_risk_score: float
    
    # Cheapness analysis
    cheapness_score: int
    cheapness_signal: str
    
    # Position sizing
    allocation_pct: float
    dollar_amount: float
    max_contracts: int
    kelly_raw: float
    
    # Trade structure
    recommended_strike: float
    strike_type: str  # "ATM", "OTM_10", "OTM_15", etc.
    recommended_expiry: datetime
    entry_price_target: float
    
    # Exit plan
    exit_t21_action: str
    exit_t14_action: str
    exit_t7_action: str
    trailing_stop_pct: float
    
    # Risk parameters
    max_loss: float
    expected_return_pct: float
    risk_reward_ratio: float
    
    # Supporting signals
    golden_sweep_detected: bool
    golden_sweep_signal: str
    
    # Warnings/notes
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "pdufa_date": self.pdufa_date.strftime("%Y-%m-%d"),
            "analysis_date": self.analysis_date.strftime("%Y-%m-%d %H:%M"),
            "recommendation": {
                "action": self.action.value,
                "confidence": self.confidence,
                "primary_reason": self.primary_reason
            },
            "odin_integration": {
                "base_approval_prob": round(self.odin_approval_prob * 100, 1),
                "adjusted_approval_prob": round(self.odin_adjusted_prob * 100, 1),
                "mfg_risk_score": self.mfg_risk_score
            },
            "cheapness_analysis": {
                "composite_score": self.cheapness_score,
                "signal": self.cheapness_signal
            },
            "position_sizing": {
                "allocation_pct": round(self.allocation_pct * 100, 2),
                "dollar_amount": round(self.dollar_amount, 2),
                "max_contracts": self.max_contracts,
                "kelly_raw": round(self.kelly_raw * 100, 2)
            },
            "trade_structure": {
                "strike": self.recommended_strike,
                "strike_type": self.strike_type,
                "expiration": self.recommended_expiry.strftime("%Y-%m-%d"),
                "entry_price_target": round(self.entry_price_target, 2)
            },
            "exit_plan": {
                "t21_action": self.exit_t21_action,
                "t14_action": self.exit_t14_action,
                "t7_action": self.exit_t7_action,
                "trailing_stop_pct": self.trailing_stop_pct
            },
            "risk_parameters": {
                "max_loss": round(self.max_loss, 2),
                "expected_return_pct": round(self.expected_return_pct, 1),
                "risk_reward_ratio": round(self.risk_reward_ratio, 2)
            },
            "signals": {
                "golden_sweep_detected": self.golden_sweep_detected,
                "golden_sweep_signal": self.golden_sweep_signal
            },
            "warnings": self.warnings
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = f"""
# OPTIONS TRADE RECOMMENDATION: {self.ticker}

**Analysis Date:** {self.analysis_date.strftime("%Y-%m-%d %H:%M")}  
**PDUFA Date:** {self.pdufa_date.strftime("%Y-%m-%d")} (T-{(self.pdufa_date - datetime.now()).days})  
**Action:** {self.action.value} | **Confidence:** {self.confidence}

---

## SUMMARY

**{self.primary_reason}**

| Metric | Value |
|--------|-------|
| ODIN Approval Probability | {self.odin_approval_prob*100:.0f}% (adjusted: {self.odin_adjusted_prob*100:.0f}%) |
| Cheapness Score | {self.cheapness_score}/100 ({self.cheapness_signal}) |
| Manufacturing Risk | {self.mfg_risk_score:.2f} |
| Golden Sweep | {'✅ DETECTED' if self.golden_sweep_detected else '⚪ None'} ({self.golden_sweep_signal}) |

---

## POSITION SIZING

| Parameter | Value |
|-----------|-------|
| Allocation | {self.allocation_pct*100:.1f}% of portfolio |
| Dollar Amount | ${self.dollar_amount:,.0f} |
| Max Contracts | {self.max_contracts} |
| Raw Kelly | {self.kelly_raw*100:.1f}% |

---

## TRADE STRUCTURE

| Parameter | Value |
|-----------|-------|
| Strike | ${self.recommended_strike:.2f} ({self.strike_type}) |
| Expiration | {self.recommended_expiry.strftime("%Y-%m-%d")} |
| Entry Price Target | ${self.entry_price_target:.2f} |

---

## EXIT PLAN

| Checkpoint | Action |
|------------|--------|
| T-21 | {self.exit_t21_action} |
| T-14 | {self.exit_t14_action} |
| T-7 | {self.exit_t7_action} |
| Trailing Stop | {self.trailing_stop_pct}% from peak |

---

## RISK PARAMETERS

| Parameter | Value |
|-----------|-------|
| Max Loss | ${self.max_loss:,.0f} |
| Expected Return | {self.expected_return_pct:.0f}% |
| Risk/Reward | {self.risk_reward_ratio:.1f}:1 |

---

## WARNINGS

"""
        if self.warnings:
            for w in self.warnings:
                md += f"⚠️ {w}\n"
        else:
            md += "✅ No warnings\n"
        
        return md


class OptionsOrchestrator:
    """
    Master orchestrator for ODIN Options Trading
    
    Combines all analysis modules to produce complete trade recommendations.
    """
    
    # Expected returns for EV calculation
    EXPECTED_RETURN_APPROVAL = 3.5   # +350% on approval play
    EXPECTED_RETURN_CRL = -0.75      # -75% on CRL
    
    # Default strike selection
    STRIKE_OTM_PCT = 0.10  # 10% OTM calls by default
    
    def __init__(self, 
                 portfolio_value: float = 100000,
                 fmp_api_key: str = None):
        """
        Initialize orchestrator
        
        Args:
            portfolio_value: Total portfolio value
            fmp_api_key: FMP API key for market data
        """
        self.portfolio_value = portfolio_value
        self.fmp_api_key = fmp_api_key or os.environ.get('FMP_API_KEY', '')
        
        # Initialize sub-modules
        self.cheapness_analyzer = CheapnessAnalyzer(self.fmp_api_key)
        self.position_sizer = PositionSizer(portfolio_value)
        self.exit_engine = ExitTriggerEngine()
        self.sweep_detector = GoldenSweepDetector(self.fmp_api_key)
    
    def analyze(self,
                ticker: str,
                pdufa_date: str,
                odin_approval_prob: float,
                mfg_risk_score: float = 0.0,
                therapeutic_area: str = "default",
                prior_crl: bool = False,
                current_stock_price: float = None,
                current_iv: float = None) -> TradeRecommendation:
        """
        Generate complete trade recommendation
        
        Args:
            ticker: Stock symbol
            pdufa_date: PDUFA date as "YYYY-MM-DD"
            odin_approval_prob: ODIN approval probability (0-1)
            mfg_risk_score: Manufacturing/CMC risk (0-1)
            therapeutic_area: For complexity adjustments
            prior_crl: Whether drug has prior CRL
            current_stock_price: Current stock price (optional, will fetch)
            current_iv: Current IV (optional, will estimate)
            
        Returns:
            TradeRecommendation with complete trade plan
        """
        pdufa = datetime.strptime(pdufa_date, "%Y-%m-%d")
        analysis_date = datetime.now()
        days_to_pdufa = (pdufa - analysis_date).days
        warnings = []
        
        # ===== STEP 1: CHEAPNESS ANALYSIS =====
        cheapness = self.cheapness_analyzer.analyze(
            ticker, pdufa, analysis_date, therapeutic_area
        )
        
        # ===== STEP 2: GOLDEN SWEEP DETECTION =====
        sweep_summary = self.sweep_detector.scan(ticker, pdufa)
        
        # ===== STEP 3: POSITION SIZING =====
        position = self.position_sizer.calculate(
            ticker=ticker,
            approval_prob=odin_approval_prob,
            mfg_risk_score=mfg_risk_score,
            cheapness_score=cheapness.composite_score,
            prior_crl=prior_crl,
            therapeutic_area=therapeutic_area
        )
        
        # ===== STEP 4: ADJUST PROBABILITY =====
        # Apply Golden Sweep adjustment
        if sweep_summary.signal == "STRONG_BULLISH":
            sweep_adj = 0.05
        elif sweep_summary.signal == "BULLISH":
            sweep_adj = 0.03
        elif sweep_summary.signal == "BEARISH":
            sweep_adj = -0.05
        else:
            sweep_adj = 0
        
        adjusted_prob = min(0.99, max(0.01, odin_approval_prob + sweep_adj))
        
        # ===== STEP 5: DETERMINE ACTION =====
        action, confidence, reason = self._determine_action(
            cheapness=cheapness,
            sweep_summary=sweep_summary,
            position=position,
            days_to_pdufa=days_to_pdufa,
            mfg_risk_score=mfg_risk_score
        )
        
        # ===== STEP 6: CALCULATE TRADE STRUCTURE =====
        stock_price = current_stock_price or self._get_stock_price(ticker)
        strike, strike_type = self._select_strike(stock_price, action)
        expiry = self._select_expiration(pdufa)
        entry_price = self._estimate_entry_price(stock_price, current_iv, days_to_pdufa)
        
        # ===== STEP 7: EXIT PLAN =====
        exit_t21 = self._plan_exit_t21(cheapness, position)
        exit_t14 = self._plan_exit_t14(cheapness)
        exit_t7 = self._plan_exit_t7()
        
        # ===== STEP 8: RISK PARAMETERS =====
        max_loss = position.dollar_amount  # Options can go to zero
        expected_return = self._calculate_expected_return(
            adjusted_prob, 
            self.EXPECTED_RETURN_APPROVAL,
            self.EXPECTED_RETURN_CRL
        )
        risk_reward = expected_return / 100 if expected_return > 0 else 0
        
        # ===== STEP 9: WARNINGS =====
        warnings = self._generate_warnings(
            days_to_pdufa=days_to_pdufa,
            mfg_risk_score=mfg_risk_score,
            cheapness_score=cheapness.composite_score,
            therapeutic_area=therapeutic_area,
            prior_crl=prior_crl
        )
        
        return TradeRecommendation(
            ticker=ticker,
            pdufa_date=pdufa,
            analysis_date=analysis_date,
            action=action,
            confidence=confidence,
            primary_reason=reason,
            odin_approval_prob=odin_approval_prob,
            odin_adjusted_prob=adjusted_prob,
            mfg_risk_score=mfg_risk_score,
            cheapness_score=cheapness.composite_score,
            cheapness_signal=cheapness.recommendation.value,
            allocation_pct=position.final_allocation_pct,
            dollar_amount=position.dollar_amount,
            max_contracts=position.max_contracts,
            kelly_raw=position.raw_kelly_fraction,
            recommended_strike=strike,
            strike_type=strike_type,
            recommended_expiry=expiry,
            entry_price_target=entry_price,
            exit_t21_action=exit_t21,
            exit_t14_action=exit_t14,
            exit_t7_action=exit_t7,
            trailing_stop_pct=25,
            max_loss=max_loss,
            expected_return_pct=expected_return,
            risk_reward_ratio=risk_reward,
            golden_sweep_detected=sweep_summary.total_sweeps > 0,
            golden_sweep_signal=sweep_summary.signal,
            warnings=warnings
        )
    
    def _determine_action(self, cheapness, sweep_summary, position,
                          days_to_pdufa: int, mfg_risk_score: float) -> Tuple[TradeAction, str, str]:
        """Determine overall trade action"""
        
        # Strong signals
        if (cheapness.composite_score >= 70 and 
            sweep_summary.signal in ["STRONG_BULLISH", "BULLISH"] and
            mfg_risk_score < 0.25 and
            days_to_pdufa > 21):
            return (
                TradeAction.STRONG_BUY,
                "HIGH",
                f"All signals aligned: Cheap entry ({cheapness.composite_score}/100), "
                f"smart money active ({sweep_summary.signal}), low CMC risk"
            )
        
        # Good setup
        if (cheapness.composite_score >= 60 and 
            mfg_risk_score < 0.35 and
            days_to_pdufa > 14):
            return (
                TradeAction.BUY,
                "MEDIUM",
                f"Favorable setup: Cheapness {cheapness.composite_score}/100, "
                f"T-{days_to_pdufa} is good timing"
            )
        
        # Tactical (mixed signals)
        if (cheapness.composite_score >= 50 and 
            days_to_pdufa > 7):
            return (
                TradeAction.TACTICAL_BUY,
                "MEDIUM",
                f"Mixed signals: Entry timing fair ({cheapness.composite_score}/100), "
                f"use reduced position size"
            )
        
        # Wait (not optimal)
        if days_to_pdufa > 45 and cheapness.composite_score < 60:
            return (
                TradeAction.WAIT,
                "LOW",
                f"Options not yet cheap ({cheapness.composite_score}/100). "
                f"Wait for better entry or monitor for sweeps."
            )
        
        # Skip (unfavorable)
        return (
            TradeAction.SKIP,
            "HIGH",
            f"Unfavorable setup: "
            f"{'Expensive entry' if cheapness.composite_score < 50 else ''}"
            f"{'High CMC risk' if mfg_risk_score > 0.4 else ''}"
            f"{'Too close to event' if days_to_pdufa <= 7 else ''}"
        )
    
    def _select_strike(self, stock_price: float, 
                       action: TradeAction) -> Tuple[float, str]:
        """Select appropriate strike based on action"""
        
        if action in [TradeAction.STRONG_BUY, TradeAction.BUY]:
            # OTM calls for higher leverage
            strike = round(stock_price * (1 + self.STRIKE_OTM_PCT), 2)
            return strike, "OTM_10"
        
        elif action == TradeAction.TACTICAL_BUY:
            # ATM for balanced exposure
            strike = round(stock_price, 0)
            return strike, "ATM"
        
        else:
            # Default to ATM
            strike = round(stock_price, 0)
            return strike, "ATM"
    
    def _select_expiration(self, pdufa_date: datetime) -> datetime:
        """Select expiration date (1 month after PDUFA)"""
        # Target ~20-30 days after PDUFA for buffer
        target = pdufa_date + timedelta(days=21)
        
        # Round to nearest Friday (options typically expire Friday)
        days_to_friday = (4 - target.weekday()) % 7
        expiry = target + timedelta(days=days_to_friday)
        
        return expiry
    
    def _estimate_entry_price(self, stock_price: float, 
                               current_iv: float,
                               days_to_pdufa: int) -> float:
        """Estimate entry price for options"""
        # Simplified pricing based on moneyness and time
        if current_iv is None:
            current_iv = 0.50  # Default 50% IV
        
        # Basic Black-Scholes approximation for ATM options
        T = days_to_pdufa / 365
        atm_price = 0.4 * stock_price * current_iv * (T ** 0.5)
        
        # Adjust for 10% OTM
        otm_discount = 0.65  # OTM options are cheaper
        
        return round(atm_price * otm_discount, 2)
    
    def _plan_exit_t21(self, cheapness, position) -> str:
        """Plan T-21 exit action"""
        if cheapness.composite_score >= 70:
            return "SELL 50% if up 40%+, HOLD otherwise"
        else:
            return "MONITOR - check IV plateau and profit targets"
    
    def _plan_exit_t14(self, cheapness) -> str:
        """Plan T-14 exit action"""
        return "SELL 100% if IV plateau (<8pts/week), check earnings conflict"
    
    def _plan_exit_t7(self) -> str:
        """Plan T-7 exit action"""
        return "SELL 75% of remaining position, keep 25% moonbag"
    
    def _calculate_expected_return(self, prob: float, 
                                    win_return: float, 
                                    loss_return: float) -> float:
        """Calculate expected return percentage"""
        # EV = P(win) * return_win + P(loss) * return_loss
        ev = prob * win_return + (1 - prob) * loss_return
        return ev * 100  # As percentage
    
    def _generate_warnings(self, days_to_pdufa: int,
                           mfg_risk_score: float,
                           cheapness_score: int,
                           therapeutic_area: str,
                           prior_crl: bool) -> List[str]:
        """Generate warning messages"""
        warnings = []
        
        if days_to_pdufa <= 14:
            warnings.append(f"Close to event (T-{days_to_pdufa}). IV crush risk elevated.")
        
        if mfg_risk_score > 0.3:
            warnings.append(f"Elevated CMC risk ({mfg_risk_score:.2f}). 74% of CRLs are CMC-related.")
        
        if cheapness_score < 50:
            warnings.append(f"Options not cheap ({cheapness_score}/100). Consider waiting or spreads.")
        
        if therapeutic_area in ["gene_therapy", "cell_therapy"]:
            warnings.append(f"Gene/cell therapy ({therapeutic_area}). Manufacturing complexity high.")
        
        if therapeutic_area in ["pain", "cns"]:
            warnings.append(f"High-failure therapeutic area ({therapeutic_area}). Historical approval ~50-65%.")
        
        if prior_crl:
            warnings.append("Prior CRL history. Increased uncertainty despite resubmission.")
        
        return warnings
    
    def _get_stock_price(self, ticker: str) -> float:
        """Fetch current stock price"""
        try:
            import requests
            url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={self.fmp_api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('price', 10.0)
        except:
            pass
        return 10.0


# ==================== BATCH ANALYSIS ====================

def analyze_portfolio(catalysts: List[Dict], 
                      portfolio_value: float = 100000) -> List[Dict]:
    """
    Analyze multiple catalysts and generate recommendations
    
    Args:
        catalysts: List of dicts with catalyst data
        portfolio_value: Total portfolio value
        
    Returns:
        List of recommendations sorted by action strength
    """
    orchestrator = OptionsOrchestrator(portfolio_value)
    results = []
    
    for cat in catalysts:
        try:
            rec = orchestrator.analyze(
                ticker=cat['ticker'],
                pdufa_date=cat['pdufa_date'],
                odin_approval_prob=cat.get('approval_prob', 0.70),
                mfg_risk_score=cat.get('mfg_risk_score', 0.0),
                therapeutic_area=cat.get('therapeutic_area', 'default'),
                prior_crl=cat.get('prior_crl', False)
            )
            results.append(rec.to_dict())
        except Exception as e:
            print(f"Error analyzing {cat['ticker']}: {e}")
    
    # Sort by action strength
    action_order = {
        "STRONG_BUY": 0,
        "BUY": 1,
        "TACTICAL_BUY": 2,
        "WAIT": 3,
        "SKIP": 4
    }
    
    results.sort(key=lambda x: action_order.get(x['recommendation']['action'], 5))
    
    return results


# ==================== MAIN ====================

if __name__ == "__main__":
    print("ODIN Options Orchestrator v3.0")
    print("=" * 60)
    
    # Test catalysts
    test_catalysts = [
        {
            "ticker": "RCKT",
            "pdufa_date": "2026-03-28",
            "approval_prob": 0.71,
            "mfg_risk_score": 0.0,
            "therapeutic_area": "gene_therapy",
            "prior_crl": True
        },
        {
            "ticker": "DNLI",
            "pdufa_date": "2026-04-05",
            "approval_prob": 0.84,
            "mfg_risk_score": 0.15,
            "therapeutic_area": "rare_disease",
            "prior_crl": False
        },
        {
            "ticker": "TVTX",
            "pdufa_date": "2026-04-02",
            "approval_prob": 0.65,
            "mfg_risk_score": 0.10,
            "therapeutic_area": "default",
            "prior_crl": False
        }
    ]
    
    portfolio_value = 100000
    orchestrator = OptionsOrchestrator(portfolio_value)
    
    print(f"\nPortfolio Value: ${portfolio_value:,}")
    print("\n" + "=" * 60)
    
    for cat in test_catalysts:
        print(f"\nAnalyzing {cat['ticker']}...")
        
        rec = orchestrator.analyze(**cat)
        
        print(f"\n{'='*60}")
        print(f"RECOMMENDATION: {cat['ticker']}")
        print(f"{'='*60}")
        print(f"  Action: {rec.action.value}")
        print(f"  Confidence: {rec.confidence}")
        print(f"  Reason: {rec.primary_reason}")
        print(f"\n  ODIN Approval: {rec.odin_approval_prob*100:.0f}% → {rec.odin_adjusted_prob*100:.0f}%")
        print(f"  Cheapness Score: {rec.cheapness_score}/100")
        print(f"  Golden Sweep: {rec.golden_sweep_signal}")
        print(f"\n  Position Size: ${rec.dollar_amount:,.0f} ({rec.allocation_pct*100:.1f}%)")
        print(f"  Strike: ${rec.recommended_strike:.2f} ({rec.strike_type})")
        print(f"  Expiration: {rec.recommended_expiry.strftime('%Y-%m-%d')}")
        print(f"  Entry Target: ${rec.entry_price_target:.2f}")
        print(f"\n  Expected Return: {rec.expected_return_pct:.0f}%")
        print(f"  Max Loss: ${rec.max_loss:,.0f}")
        print(f"  Risk/Reward: {rec.risk_reward_ratio:.1f}:1")
        
        if rec.warnings:
            print(f"\n  Warnings:")
            for w in rec.warnings:
                print(f"    ⚠️ {w}")
    
    # Save markdown report for best opportunity
    print("\n" + "=" * 60)
    print("Generating detailed report for top recommendation...")
    
    best = orchestrator.analyze(**test_catalysts[1])  # DNLI has best setup
    report_path = f"/home/claude/odin_trade_recommendation_{best.ticker}_{datetime.now().strftime('%Y%m%d')}.md"
    
    with open(report_path, 'w') as f:
        f.write(best.to_markdown())
    
    print(f"Report saved: {report_path}")
