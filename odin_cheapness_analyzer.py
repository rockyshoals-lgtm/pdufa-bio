#!/usr/bin/env python3
"""
ODIN Cheapness Analyzer v3.0
============================
4-Metric IV Cheapness Framework for Options Entry Timing

Metrics:
1. IV/HV Ratio (Premium Check)
2. Expected Move (Straddle Cost vs Historical)
3. IV Percentile (52-week context)
4. Timing Phase (Calendar position)

Usage:
    analyzer = CheapnessAnalyzer(fmp_api_key)
    result = analyzer.analyze(ticker, pdufa_date)
    print(result['recommendation'])  # "BUY_CALLS", "SPREADS_ONLY", "SKIP"
"""

import os
import json
import requests
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from enum import Enum

# API Configuration
FMP_API_KEY = os.environ.get('FMP_API_KEY', '')
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class Signal(Enum):
    EXTREMELY_CHEAP = "EXTREMELY_CHEAP"
    CHEAP = "CHEAP"
    FAIR = "FAIR"
    EXPENSIVE = "EXPENSIVE"
    TRAP = "TRAP"


class Action(Enum):
    BUY_CALLS = "BUY_CALLS"
    CALLS_OR_SPREADS = "CALLS_OR_SPREADS"
    SPREADS_ONLY = "SPREADS_ONLY"
    SKIP_OR_SELL = "SKIP_OR_SELL"


@dataclass
class MetricResult:
    """Individual metric result"""
    name: str
    value: float
    signal: Signal
    score: int
    interpretation: str


@dataclass
class CheapnessResult:
    """Complete cheapness analysis result"""
    ticker: str
    analysis_date: datetime
    pdufa_date: datetime
    days_to_catalyst: int
    
    iv_hv_metric: MetricResult
    expected_move_metric: MetricResult
    iv_percentile_metric: MetricResult
    timing_metric: MetricResult
    
    composite_score: int
    recommendation: Action
    confidence: str
    position_size_multiplier: float
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "analysis_date": self.analysis_date.isoformat(),
            "pdufa_date": self.pdufa_date.isoformat(),
            "days_to_catalyst": self.days_to_catalyst,
            "metrics": {
                "iv_hv_ratio": {
                    "value": self.iv_hv_metric.value,
                    "signal": self.iv_hv_metric.signal.value,
                    "score": self.iv_hv_metric.score,
                    "interpretation": self.iv_hv_metric.interpretation
                },
                "expected_move": {
                    "value": self.expected_move_metric.value,
                    "signal": self.expected_move_metric.signal.value,
                    "score": self.expected_move_metric.score,
                    "interpretation": self.expected_move_metric.interpretation
                },
                "iv_percentile": {
                    "value": self.iv_percentile_metric.value,
                    "signal": self.iv_percentile_metric.signal.value,
                    "score": self.iv_percentile_metric.score,
                    "interpretation": self.iv_percentile_metric.interpretation
                },
                "timing_phase": {
                    "value": self.timing_metric.value,
                    "signal": self.timing_metric.signal.value,
                    "score": self.timing_metric.score,
                    "interpretation": self.timing_metric.interpretation
                }
            },
            "composite_score": self.composite_score,
            "recommendation": self.recommendation.value,
            "confidence": self.confidence,
            "position_size_multiplier": self.position_size_multiplier
        }


class CheapnessAnalyzer:
    """
    ODIN Cheapness Analyzer
    
    Combines 4 metrics to determine if options are cheap/expensive
    and whether NOW is the right time to enter.
    """
    
    # Historical move data by therapeutic area (approval scenarios)
    HISTORICAL_MOVES = {
        "default": {"approval": 0.80, "crl": -0.60},
        "oncology": {"approval": 0.65, "crl": -0.55},
        "rare_disease": {"approval": 1.00, "crl": -0.70},
        "gene_therapy": {"approval": 1.20, "crl": -0.75},
        "cnf": {"approval": 0.50, "crl": -0.45},  # CNS
        "cardiovascular": {"approval": 0.55, "crl": -0.50},
        "infectious_disease": {"approval": 0.70, "crl": -0.60},
    }
    
    def __init__(self, fmp_api_key: str = None):
        self.api_key = fmp_api_key or FMP_API_KEY
        self._iv_cache = {}
        self._price_cache = {}
    
    def analyze(self, ticker: str, pdufa_date: datetime, 
                analysis_date: datetime = None,
                therapeutic_area: str = "default") -> CheapnessResult:
        """
        Run complete cheapness analysis
        
        Args:
            ticker: Stock symbol
            pdufa_date: FDA decision date
            analysis_date: Date of analysis (default: today)
            therapeutic_area: For historical move lookup
            
        Returns:
            CheapnessResult with all metrics and recommendation
        """
        if analysis_date is None:
            analysis_date = datetime.now()
        
        days_to_catalyst = (pdufa_date - analysis_date).days
        
        # Run each metric
        iv_hv = self._analyze_iv_hv_ratio(ticker)
        expected_move = self._analyze_expected_move(ticker, therapeutic_area)
        iv_pct = self._analyze_iv_percentile(ticker, days_to_catalyst)
        timing = self._analyze_timing_phase(days_to_catalyst)
        
        # Calculate composite score
        composite = iv_hv.score + expected_move.score + iv_pct.score + timing.score
        
        # Determine recommendation
        recommendation = self._score_to_action(composite)
        confidence = self._score_to_confidence(composite)
        size_mult = self._score_to_position_size(composite)
        
        return CheapnessResult(
            ticker=ticker,
            analysis_date=analysis_date,
            pdufa_date=pdufa_date,
            days_to_catalyst=days_to_catalyst,
            iv_hv_metric=iv_hv,
            expected_move_metric=expected_move,
            iv_percentile_metric=iv_pct,
            timing_metric=timing,
            composite_score=composite,
            recommendation=recommendation,
            confidence=confidence,
            position_size_multiplier=size_mult
        )
    
    def _analyze_iv_hv_ratio(self, ticker: str) -> MetricResult:
        """
        Metric 1: IV/HV Ratio
        
        Compares implied volatility to historical volatility.
        < 1.2 = CHEAP (market not pricing event)
        > 2.0 = TRAP (IV crush baked in)
        """
        try:
            iv30 = self._get_implied_volatility(ticker)
            hv30 = self._get_historical_volatility(ticker, days=30)
            
            if hv30 == 0:
                hv30 = 0.01  # Prevent division by zero
            
            ratio = iv30 / hv30
        except Exception as e:
            # Default to FAIR if data unavailable
            ratio = 1.5
            iv30, hv30 = 0.5, 0.33
        
        if ratio < 1.2:
            signal = Signal.CHEAP
            score = 25
            interp = f"IV only {(ratio-1)*100:.0f}% above HV; market underpricing event"
        elif ratio < 1.8:
            signal = Signal.FAIR
            score = 15
            interp = f"IV {(ratio-1)*100:.0f}% above HV; market aware but not fully pricing"
        elif ratio < 2.0:
            signal = Signal.EXPENSIVE
            score = 5
            interp = f"IV {(ratio-1)*100:.0f}% above HV; event heavily priced"
        else:
            signal = Signal.TRAP
            score = 0
            interp = f"IV {(ratio-1)*100:.0f}% above HV; IV crush will destroy gains"
        
        return MetricResult(
            name="IV/HV Ratio",
            value=round(ratio, 2),
            signal=signal,
            score=score,
            interpretation=interp
        )
    
    def _analyze_expected_move(self, ticker: str, 
                               therapeutic_area: str) -> MetricResult:
        """
        Metric 2: Expected Move vs Historical
        
        Compares straddle cost (expected move) to historical PDUFA moves.
        Large gap = cheap (market underpricing the move)
        """
        try:
            stock_price = self._get_stock_price(ticker)
            atm_call, atm_put = self._get_atm_option_prices(ticker)
            
            straddle_cost = atm_call + atm_put
            expected_move_pct = (straddle_cost / stock_price) * 100
        except Exception as e:
            # Default estimates if data unavailable
            expected_move_pct = 35
            stock_price = 10
        
        # Get historical move for this therapeutic area
        hist_data = self.HISTORICAL_MOVES.get(therapeutic_area, 
                                               self.HISTORICAL_MOVES["default"])
        historical_move_pct = hist_data["approval"] * 100
        
        # Calculate edge (how much market is underpricing)
        edge = historical_move_pct - expected_move_pct
        
        if edge > 50:
            signal = Signal.CHEAP
            score = 25
            interp = f"Market pricing {expected_move_pct:.0f}% vs historical {historical_move_pct:.0f}%. Massive edge."
        elif edge > 20:
            signal = Signal.FAIR
            score = 15
            interp = f"Market pricing {expected_move_pct:.0f}% vs historical {historical_move_pct:.0f}%. Moderate edge."
        elif edge > -10:
            signal = Signal.EXPENSIVE
            score = 5
            interp = f"Market pricing {expected_move_pct:.0f}% vs historical {historical_move_pct:.0f}%. Minimal edge."
        else:
            signal = Signal.TRAP
            score = 0
            interp = f"Market pricing {expected_move_pct:.0f}% vs historical {historical_move_pct:.0f}%. OVERPRICED."
        
        return MetricResult(
            name="Expected Move",
            value=round(expected_move_pct, 1),
            signal=signal,
            score=score,
            interpretation=interp
        )
    
    def _analyze_iv_percentile(self, ticker: str, 
                                days_to_catalyst: int) -> MetricResult:
        """
        Metric 3: IV Percentile (52-week context)
        
        Where is current IV relative to its yearly range?
        < 20% = extremely cheap
        > 80% = extremely expensive
        """
        try:
            iv_history = self._get_iv_history(ticker, days=252)
            current_iv = self._get_implied_volatility(ticker)
            
            # Calculate percentile
            iv_lower_count = sum(1 for iv in iv_history if iv < current_iv)
            iv_percentile = (iv_lower_count / len(iv_history)) * 100
        except Exception as e:
            # Default to median if unavailable
            iv_percentile = 50
            current_iv = 0.5
        
        # Adjust threshold based on days to catalyst
        # If far from event, we want LOWER IV percentile to enter
        if days_to_catalyst > 21:
            if iv_percentile < 20:
                signal = Signal.EXTREMELY_CHEAP
                score = 25
                interp = f"IV at {iv_percentile:.0f}th percentile. Rare entry window."
            elif iv_percentile < 40:
                signal = Signal.CHEAP
                score = 20
                interp = f"IV at {iv_percentile:.0f}th percentile. Below median, good entry."
            elif iv_percentile < 60:
                signal = Signal.FAIR
                score = 10
                interp = f"IV at {iv_percentile:.0f}th percentile. At median."
            elif iv_percentile < 80:
                signal = Signal.EXPENSIVE
                score = 5
                interp = f"IV at {iv_percentile:.0f}th percentile. Elevated."
            else:
                signal = Signal.TRAP
                score = 0
                interp = f"IV at {iv_percentile:.0f}th percentile. Near yearly high."
        else:
            # Close to event - IV will be high naturally
            if iv_percentile < 60:
                signal = Signal.FAIR
                score = 15
                interp = f"IV at {iv_percentile:.0f}th percentile. Reasonable for event proximity."
            else:
                signal = Signal.EXPENSIVE
                score = 5
                interp = f"IV at {iv_percentile:.0f}th percentile. High but expected near event."
        
        return MetricResult(
            name="IV Percentile",
            value=round(iv_percentile, 0),
            signal=signal,
            score=score,
            interpretation=interp
        )
    
    def _analyze_timing_phase(self, days_to_catalyst: int) -> MetricResult:
        """
        Metric 4: Timing Phase
        
        Phase 1 (T-60 to T-45): Optimal entry
        Phase 2 (T-45 to T-21): Good entry
        Phase 3 (T-21 to T-7): Late, use spreads
        Phase 4 (< T-7): Too late, skip
        """
        if days_to_catalyst > 45:
            phase = 1
            signal = Signal.CHEAP
            score = 25
            interp = f"Phase 1 ({days_to_catalyst} days). Optimal entry window."
        elif days_to_catalyst > 21:
            phase = 2
            signal = Signal.FAIR
            score = 20
            interp = f"Phase 2 ({days_to_catalyst} days). Good entry, IV ramp starting."
        elif days_to_catalyst > 7:
            phase = 3
            signal = Signal.EXPENSIVE
            score = 5
            interp = f"Phase 3 ({days_to_catalyst} days). Late entry, use spreads only."
        else:
            phase = 4
            signal = Signal.TRAP
            score = 0
            interp = f"Phase 4 ({days_to_catalyst} days). TOO LATE. IV crush imminent."
        
        return MetricResult(
            name="Timing Phase",
            value=phase,
            signal=signal,
            score=score,
            interpretation=interp
        )
    
    def _score_to_action(self, score: int) -> Action:
        """Convert composite score to trading action"""
        if score >= 70:
            return Action.BUY_CALLS
        elif score >= 50:
            return Action.CALLS_OR_SPREADS
        elif score >= 30:
            return Action.SPREADS_ONLY
        else:
            return Action.SKIP_OR_SELL
    
    def _score_to_confidence(self, score: int) -> str:
        """Determine confidence level"""
        if score > 85 or score < 25:
            return "HIGH"  # Clear signal either way
        else:
            return "MEDIUM"  # Mixed signals
    
    def _score_to_position_size(self, score: int) -> float:
        """Modulate position size based on cheapness"""
        if score > 80:
            return 1.2  # 20% larger (exceptional entry)
        elif score > 60:
            return 1.0  # Full size
        elif score > 40:
            return 0.75  # 75% size
        else:
            return 0.5  # Half size (or skip)
    
    # ==================== DATA FETCHING ====================
    
    def _get_stock_price(self, ticker: str) -> float:
        """Fetch current stock price from FMP"""
        if ticker in self._price_cache:
            cached = self._price_cache[ticker]
            if (datetime.now() - cached['timestamp']).seconds < 300:
                return cached['price']
        
        try:
            url = f"{FMP_BASE_URL}/quote/{ticker}?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                price = data[0].get('price', 10.0)
                self._price_cache[ticker] = {
                    'price': price,
                    'timestamp': datetime.now()
                }
                return price
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
        
        return 10.0  # Default fallback
    
    def _get_implied_volatility(self, ticker: str) -> float:
        """
        Get current ATM implied volatility
        
        FMP doesn't directly provide IV, so we estimate from option prices
        using Black-Scholes inversion. For now, use simplified approach.
        """
        # In production, calculate from option chain
        # For now, use proxy based on sector
        try:
            url = f"{FMP_BASE_URL}/stock-price-change/{ticker}?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                # Use recent price volatility as proxy
                change_30d = abs(data[0].get('1M', 10)) / 100
                # IV typically 1.2-2x historical vol
                return change_30d * 1.5 + 0.3  # Baseline + multiplier
        except:
            pass
        
        return 0.50  # Default 50% IV
    
    def _get_historical_volatility(self, ticker: str, days: int = 30) -> float:
        """Calculate historical volatility from price data"""
        try:
            url = f"{FMP_BASE_URL}/historical-price-full/{ticker}?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'historical' in data:
                prices = [d['close'] for d in data['historical'][:days]]
                if len(prices) >= 2:
                    returns = np.diff(np.log(prices))
                    hv = np.std(returns) * np.sqrt(252)  # Annualized
                    return hv
        except:
            pass
        
        return 0.40  # Default 40% HV
    
    def _get_iv_history(self, ticker: str, days: int = 252) -> List[float]:
        """
        Get historical IV values for percentile calculation
        
        In production, this would come from an options data provider.
        For now, simulate based on price volatility.
        """
        try:
            url = f"{FMP_BASE_URL}/historical-price-full/{ticker}?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'historical' in data:
                prices = [d['close'] for d in data['historical'][:days+30]]
                
                # Calculate rolling 30-day volatility as IV proxy
                iv_history = []
                for i in range(days):
                    if i + 30 <= len(prices):
                        window = prices[i:i+30]
                        if len(window) >= 2:
                            returns = np.diff(np.log(window))
                            vol = np.std(returns) * np.sqrt(252)
                            # IV premium over HV
                            iv_history.append(vol * 1.3 + 0.2)
                
                if len(iv_history) > 0:
                    return iv_history
        except:
            pass
        
        # Generate synthetic history if unavailable
        return list(np.random.uniform(0.3, 0.8, days))
    
    def _get_atm_option_prices(self, ticker: str) -> Tuple[float, float]:
        """
        Get ATM call and put prices
        
        In production, fetch from options chain.
        For now, estimate using simplified Black-Scholes.
        """
        stock_price = self._get_stock_price(ticker)
        iv = self._get_implied_volatility(ticker)
        
        # Simplified ATM option pricing (30-60 DTE typical)
        # ATM call ≈ 0.4 * S * IV * sqrt(T)
        # where T = time to expiry in years
        T = 45 / 365  # 45 days typical
        
        atm_call = 0.4 * stock_price * iv * np.sqrt(T)
        atm_put = 0.4 * stock_price * iv * np.sqrt(T) * 0.9  # Slight put skew
        
        return atm_call, atm_put


# ==================== QUICK ANALYSIS FUNCTION ====================

def quick_cheapness_check(ticker: str, pdufa_date: str, 
                          therapeutic_area: str = "default") -> Dict:
    """
    Quick cheapness analysis for a single ticker
    
    Args:
        ticker: Stock symbol
        pdufa_date: PDUFA date as string "YYYY-MM-DD"
        therapeutic_area: For historical move lookup
        
    Returns:
        Dict with analysis results
    """
    analyzer = CheapnessAnalyzer()
    pdufa = datetime.strptime(pdufa_date, "%Y-%m-%d")
    result = analyzer.analyze(ticker, pdufa, therapeutic_area=therapeutic_area)
    return result.to_dict()


# ==================== BATCH ANALYSIS ====================

def batch_cheapness_analysis(catalysts: List[Dict]) -> List[Dict]:
    """
    Run cheapness analysis on multiple catalysts
    
    Args:
        catalysts: List of dicts with 'ticker', 'pdufa_date', 'therapeutic_area'
        
    Returns:
        List of analysis results sorted by composite score
    """
    analyzer = CheapnessAnalyzer()
    results = []
    
    for cat in catalysts:
        try:
            pdufa = datetime.strptime(cat['pdufa_date'], "%Y-%m-%d")
            result = analyzer.analyze(
                cat['ticker'], 
                pdufa,
                therapeutic_area=cat.get('therapeutic_area', 'default')
            )
            results.append(result.to_dict())
        except Exception as e:
            print(f"Error analyzing {cat['ticker']}: {e}")
    
    # Sort by composite score (highest first)
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return results


# ==================== MAIN ====================

if __name__ == "__main__":
    # Example usage
    print("ODIN Cheapness Analyzer v3.0")
    print("=" * 50)
    
    # Test catalysts
    test_catalysts = [
        {"ticker": "RCKT", "pdufa_date": "2026-03-28", "therapeutic_area": "gene_therapy"},
        {"ticker": "DNLI", "pdufa_date": "2026-04-05", "therapeutic_area": "rare_disease"},
        {"ticker": "TVTX", "pdufa_date": "2026-04-02", "therapeutic_area": "default"},
    ]
    
    print("\nRunning batch analysis...")
    results = batch_cheapness_analysis(test_catalysts)
    
    for r in results:
        print(f"\n{r['ticker']} (PDUFA: {r['pdufa_date']})")
        print(f"  Composite Score: {r['composite_score']}/100")
        print(f"  Recommendation: {r['recommendation']}")
        print(f"  Confidence: {r['confidence']}")
        print(f"  Position Multiplier: {r['position_size_multiplier']}x")
        print(f"  Metrics:")
        for name, metric in r['metrics'].items():
            print(f"    {name}: {metric['signal']} ({metric['score']} pts)")
