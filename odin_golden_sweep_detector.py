#!/usr/bin/env python3
"""
ODIN Golden Sweep Detector v3.0
===============================
Smart Money Detection for Biotech Options

Detects institutional "Golden Sweeps" - aggressive option buying patterns
that signal smart money positioning before PDUFA events.

Detection Criteria:
1. Volume > Open Interest × 2 (NEW money, not closing positions)
2. OTM Strike (10-25% out of the money)
3. Near-dated Expiration (within 30 days of catalyst)
4. Ask-side Execution (urgent buying, not patient limits)

Usage:
    detector = GoldenSweepDetector(fmp_api_key)
    sweeps = detector.scan(ticker, pdufa_date)
    
    if sweeps:
        print("SMART MONEY DETECTED!")
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


# API Configuration
FMP_API_KEY = os.environ.get('FMP_API_KEY', '')
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class SweepDirection(Enum):
    BULLISH = "BULLISH"   # Call sweeps
    BEARISH = "BEARISH"   # Put sweeps
    MIXED = "MIXED"       # Both


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class GoldenSweep:
    """Individual sweep detection"""
    ticker: str
    contract_type: str  # "call" or "put"
    strike: float
    expiration: datetime
    
    volume: int
    open_interest: int
    vol_oi_ratio: float
    
    last_price: float
    bid: float
    ask: float
    execution_side: str  # "ask", "bid", "mid"
    
    stock_price: float
    moneyness_pct: float  # How far OTM
    
    days_to_expiry: int
    days_to_catalyst: int
    
    confidence: Confidence
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "contract_type": self.contract_type,
            "strike": self.strike,
            "expiration": self.expiration.strftime("%Y-%m-%d"),
            "volume": self.volume,
            "open_interest": self.open_interest,
            "vol_oi_ratio": round(self.vol_oi_ratio, 2),
            "last_price": self.last_price,
            "execution_side": self.execution_side,
            "stock_price": self.stock_price,
            "moneyness_pct": round(self.moneyness_pct * 100, 1),
            "days_to_expiry": self.days_to_expiry,
            "days_to_catalyst": self.days_to_catalyst,
            "confidence": self.confidence.value
        }


@dataclass
class SweepSummary:
    """Summary of all sweeps for a ticker"""
    ticker: str
    scan_date: datetime
    pdufa_date: datetime
    
    total_sweeps: int
    call_sweeps: int
    put_sweeps: int
    
    direction: SweepDirection
    total_premium: float
    avg_vol_oi_ratio: float
    
    strongest_sweep: Optional[GoldenSweep]
    all_sweeps: List[GoldenSweep]
    
    signal: str  # "STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH"
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "scan_date": self.scan_date.strftime("%Y-%m-%d %H:%M"),
            "pdufa_date": self.pdufa_date.strftime("%Y-%m-%d"),
            "summary": {
                "total_sweeps": self.total_sweeps,
                "call_sweeps": self.call_sweeps,
                "put_sweeps": self.put_sweeps,
                "direction": self.direction.value,
                "total_premium": round(self.total_premium, 2),
                "avg_vol_oi_ratio": round(self.avg_vol_oi_ratio, 2)
            },
            "signal": self.signal,
            "strongest_sweep": self.strongest_sweep.to_dict() if self.strongest_sweep else None,
            "all_sweeps": [s.to_dict() for s in self.all_sweeps]
        }


class GoldenSweepDetector:
    """
    ODIN Golden Sweep Detector
    
    Scans option chains for institutional accumulation patterns.
    Golden Sweeps are high-confidence smart money signals.
    """
    
    # Detection thresholds
    VOL_OI_THRESHOLD = 2.0       # Volume must be 2x open interest
    MONEYNESS_MIN = 0.10        # At least 10% OTM
    MONEYNESS_MAX = 0.25        # No more than 25% OTM
    EXPIRY_MAX_DAYS = 30        # Within 30 days of catalyst
    ASK_SIDE_THRESHOLD = 0.95   # Last price within 5% of ask
    
    # Confidence scoring
    VOL_OI_HIGH = 5.0           # Vol/OI > 5 = high confidence
    VOL_OI_MEDIUM = 3.0         # Vol/OI > 3 = medium confidence
    
    def __init__(self, fmp_api_key: str = None):
        self.api_key = fmp_api_key or FMP_API_KEY
        self._price_cache = {}
    
    def scan(self, ticker: str, pdufa_date: datetime,
             scan_date: datetime = None) -> SweepSummary:
        """
        Scan for Golden Sweeps in a ticker's option chain
        
        Args:
            ticker: Stock symbol
            pdufa_date: FDA catalyst date
            scan_date: Date of scan (default: now)
            
        Returns:
            SweepSummary with all detected sweeps
        """
        if scan_date is None:
            scan_date = datetime.now()
        
        # Get current stock price
        stock_price = self._get_stock_price(ticker)
        
        # Get option chain
        chain = self._get_option_chain(ticker)
        
        if not chain:
            return self._empty_summary(ticker, scan_date, pdufa_date)
        
        # Scan for sweeps
        sweeps = []
        
        for contract in chain:
            sweep = self._evaluate_contract(
                contract, 
                stock_price, 
                pdufa_date, 
                ticker
            )
            if sweep:
                sweeps.append(sweep)
        
        # Build summary
        return self._build_summary(ticker, scan_date, pdufa_date, sweeps)
    
    def _evaluate_contract(self, contract: Dict, stock_price: float,
                           pdufa_date: datetime, ticker: str) -> Optional[GoldenSweep]:
        """
        Evaluate a single contract for Golden Sweep criteria
        
        Returns GoldenSweep if all criteria met, None otherwise
        """
        try:
            # Extract contract data
            strike = contract.get('strike', 0)
            contract_type = contract.get('type', 'call').lower()
            volume = contract.get('volume', 0)
            open_interest = contract.get('openInterest', 1)
            last_price = contract.get('lastPrice', 0)
            bid = contract.get('bid', 0)
            ask = contract.get('ask', 0)
            expiration = datetime.strptime(
                contract.get('expiration', '2099-12-31'), 
                '%Y-%m-%d'
            )
            
            # Skip if missing critical data
            if volume == 0 or open_interest == 0 or ask == 0:
                return None
            
            # Calculate metrics
            vol_oi_ratio = volume / max(open_interest, 1)
            days_to_expiry = (expiration - datetime.now()).days
            days_to_catalyst = (pdufa_date - datetime.now()).days
            
            # Calculate moneyness
            if contract_type == 'call':
                moneyness = (strike - stock_price) / stock_price
            else:
                moneyness = (stock_price - strike) / stock_price
            
            # Determine execution side
            if ask > 0 and last_price >= ask * self.ASK_SIDE_THRESHOLD:
                execution_side = "ask"
            elif bid > 0 and last_price <= bid * 1.05:
                execution_side = "bid"
            else:
                execution_side = "mid"
            
            # ===== GOLDEN SWEEP CRITERIA =====
            
            # 1. Volume > OI × 2 (new positioning)
            if vol_oi_ratio < self.VOL_OI_THRESHOLD:
                return None
            
            # 2. OTM strike (10-25% out of the money)
            if not (self.MONEYNESS_MIN <= moneyness <= self.MONEYNESS_MAX):
                return None
            
            # 3. Expiration within 30 days of catalyst
            if not (0 < days_to_expiry <= days_to_catalyst + self.EXPIRY_MAX_DAYS):
                return None
            
            # 4. Ask-side execution (urgent buying)
            if execution_side != "ask":
                return None
            
            # ===== ALL CRITERIA MET =====
            
            # Determine confidence
            if vol_oi_ratio >= self.VOL_OI_HIGH:
                confidence = Confidence.HIGH
            elif vol_oi_ratio >= self.VOL_OI_MEDIUM:
                confidence = Confidence.MEDIUM
            else:
                confidence = Confidence.LOW
            
            return GoldenSweep(
                ticker=ticker,
                contract_type=contract_type,
                strike=strike,
                expiration=expiration,
                volume=volume,
                open_interest=open_interest,
                vol_oi_ratio=vol_oi_ratio,
                last_price=last_price,
                bid=bid,
                ask=ask,
                execution_side=execution_side,
                stock_price=stock_price,
                moneyness_pct=moneyness,
                days_to_expiry=days_to_expiry,
                days_to_catalyst=days_to_catalyst,
                confidence=confidence
            )
            
        except Exception as e:
            return None
    
    def _build_summary(self, ticker: str, scan_date: datetime,
                       pdufa_date: datetime, 
                       sweeps: List[GoldenSweep]) -> SweepSummary:
        """Build summary from detected sweeps"""
        
        if not sweeps:
            return self._empty_summary(ticker, scan_date, pdufa_date)
        
        call_sweeps = [s for s in sweeps if s.contract_type == 'call']
        put_sweeps = [s for s in sweeps if s.contract_type == 'put']
        
        # Determine direction
        if len(call_sweeps) > len(put_sweeps) * 2:
            direction = SweepDirection.BULLISH
        elif len(put_sweeps) > len(call_sweeps) * 2:
            direction = SweepDirection.BEARISH
        else:
            direction = SweepDirection.MIXED
        
        # Calculate totals
        total_premium = sum(s.last_price * s.volume * 100 for s in sweeps)
        avg_vol_oi = sum(s.vol_oi_ratio for s in sweeps) / len(sweeps)
        
        # Find strongest sweep
        strongest = max(sweeps, key=lambda x: x.vol_oi_ratio)
        
        # Determine signal strength
        high_conf_count = sum(1 for s in sweeps if s.confidence == Confidence.HIGH)
        
        if high_conf_count >= 3 and direction == SweepDirection.BULLISH:
            signal = "STRONG_BULLISH"
        elif high_conf_count >= 1 and direction == SweepDirection.BULLISH:
            signal = "BULLISH"
        elif high_conf_count >= 1 and direction == SweepDirection.BEARISH:
            signal = "BEARISH"
        elif len(sweeps) >= 2:
            signal = "MIXED_ACTIVITY"
        else:
            signal = "NEUTRAL"
        
        return SweepSummary(
            ticker=ticker,
            scan_date=scan_date,
            pdufa_date=pdufa_date,
            total_sweeps=len(sweeps),
            call_sweeps=len(call_sweeps),
            put_sweeps=len(put_sweeps),
            direction=direction,
            total_premium=total_premium,
            avg_vol_oi_ratio=avg_vol_oi,
            strongest_sweep=strongest,
            all_sweeps=sweeps,
            signal=signal
        )
    
    def _empty_summary(self, ticker: str, scan_date: datetime,
                       pdufa_date: datetime) -> SweepSummary:
        """Create empty summary when no sweeps found"""
        return SweepSummary(
            ticker=ticker,
            scan_date=scan_date,
            pdufa_date=pdufa_date,
            total_sweeps=0,
            call_sweeps=0,
            put_sweeps=0,
            direction=SweepDirection.MIXED,
            total_premium=0,
            avg_vol_oi_ratio=0,
            strongest_sweep=None,
            all_sweeps=[],
            signal="NO_ACTIVITY"
        )
    
    def _get_stock_price(self, ticker: str) -> float:
        """Fetch current stock price"""
        if ticker in self._price_cache:
            cached = self._price_cache[ticker]
            if (datetime.now() - cached['timestamp']).seconds < 60:
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
        except:
            pass
        
        return 10.0
    
    def _get_option_chain(self, ticker: str) -> List[Dict]:
        """
        Fetch option chain from FMP
        
        Note: FMP option chain endpoint structure may vary.
        In production, adapt to actual API response format.
        """
        try:
            url = f"{FMP_BASE_URL}/stock_option_chain/{ticker}?apikey={self.api_key}"
            response = requests.get(url, timeout=15)
            data = response.json()
            
            # FMP returns nested structure, flatten it
            contracts = []
            
            if isinstance(data, list):
                for exp_group in data:
                    if isinstance(exp_group, dict):
                        # Handle different FMP response formats
                        if 'calls' in exp_group:
                            for call in exp_group.get('calls', []):
                                call['type'] = 'call'
                                call['expiration'] = exp_group.get('expirationDate', '2099-12-31')
                                contracts.append(call)
                        if 'puts' in exp_group:
                            for put in exp_group.get('puts', []):
                                put['type'] = 'put'
                                put['expiration'] = exp_group.get('expirationDate', '2099-12-31')
                                contracts.append(put)
                        else:
                            # Direct contract format
                            contracts.append(exp_group)
            
            return contracts
            
        except Exception as e:
            print(f"Error fetching option chain for {ticker}: {e}")
            return []


# ==================== UNUSUAL OPTIONS ACTIVITY ====================

class UnusualOptionsActivityScanner:
    """
    Broader unusual options activity scanner
    
    Detects various patterns beyond Golden Sweeps:
    - Large block trades
    - Unusual put activity (hedging)
    - Calendar spread positioning
    """
    
    def __init__(self, fmp_api_key: str = None):
        self.api_key = fmp_api_key or FMP_API_KEY
        self.sweep_detector = GoldenSweepDetector(self.api_key)
    
    def scan_portfolio(self, tickers: List[Dict]) -> List[Dict]:
        """
        Scan multiple tickers for unusual activity
        
        Args:
            tickers: List of dicts with 'ticker' and 'pdufa_date'
            
        Returns:
            List of scan results, sorted by signal strength
        """
        results = []
        
        for t in tickers:
            try:
                pdufa = datetime.strptime(t['pdufa_date'], '%Y-%m-%d')
                summary = self.sweep_detector.scan(t['ticker'], pdufa)
                results.append(summary.to_dict())
            except Exception as e:
                print(f"Error scanning {t['ticker']}: {e}")
        
        # Sort by signal strength
        signal_order = {
            "STRONG_BULLISH": 0,
            "BULLISH": 1,
            "MIXED_ACTIVITY": 2,
            "NEUTRAL": 3,
            "BEARISH": 4,
            "NO_ACTIVITY": 5
        }
        
        results.sort(key=lambda x: signal_order.get(x['signal'], 6))
        
        return results


# ==================== INTEGRATION WITH ODIN ====================

def integrate_sweep_signal(odin_prediction: Dict, 
                           sweep_summary: SweepSummary) -> Dict:
    """
    Integrate Golden Sweep signal into ODIN prediction
    
    Args:
        odin_prediction: Base ODIN prediction dict
        sweep_summary: Sweep detection results
        
    Returns:
        Enhanced prediction with sweep signal
    """
    # Base prediction
    result = odin_prediction.copy()
    
    # Add sweep signal
    if sweep_summary.signal == "STRONG_BULLISH":
        sweep_adjustment = 0.05  # +5% confidence boost
        sweep_confidence = "HIGH"
    elif sweep_summary.signal == "BULLISH":
        sweep_adjustment = 0.03  # +3% confidence boost
        sweep_confidence = "MEDIUM"
    elif sweep_summary.signal == "BEARISH":
        sweep_adjustment = -0.05  # -5% confidence penalty
        sweep_confidence = "HIGH"
    else:
        sweep_adjustment = 0
        sweep_confidence = "LOW"
    
    result['signals'] = result.get('signals', {})
    result['signals']['golden_sweep'] = {
        "detected": sweep_summary.total_sweeps > 0,
        "signal": sweep_summary.signal,
        "total_sweeps": sweep_summary.total_sweeps,
        "call_sweeps": sweep_summary.call_sweeps,
        "put_sweeps": sweep_summary.put_sweeps,
        "total_premium": sweep_summary.total_premium,
        "confidence": sweep_confidence,
        "probability_adjustment": sweep_adjustment
    }
    
    # Adjust overall probability
    base_prob = result.get('approval_probability', 0.5)
    adjusted_prob = min(0.99, max(0.01, base_prob + sweep_adjustment))
    result['approval_probability_adjusted'] = round(adjusted_prob, 3)
    
    return result


# ==================== QUICK SCAN FUNCTION ====================

def quick_sweep_scan(ticker: str, pdufa_date: str) -> Dict:
    """
    Quick sweep scan for a single ticker
    
    Args:
        ticker: Stock symbol
        pdufa_date: PDUFA date as string "YYYY-MM-DD"
        
    Returns:
        Dict with sweep summary
    """
    detector = GoldenSweepDetector()
    pdufa = datetime.strptime(pdufa_date, '%Y-%m-%d')
    summary = detector.scan(ticker, pdufa)
    return summary.to_dict()


# ==================== MAIN ====================

if __name__ == "__main__":
    print("ODIN Golden Sweep Detector v3.0")
    print("=" * 50)
    
    # Test catalysts
    test_catalysts = [
        {"ticker": "RCKT", "pdufa_date": "2026-03-28"},
        {"ticker": "DNLI", "pdufa_date": "2026-04-05"},
        {"ticker": "TVTX", "pdufa_date": "2026-04-02"},
    ]
    
    detector = GoldenSweepDetector()
    
    print("\nScanning for Golden Sweeps...")
    print("-" * 50)
    
    for cat in test_catalysts:
        pdufa = datetime.strptime(cat['pdufa_date'], '%Y-%m-%d')
        summary = detector.scan(cat['ticker'], pdufa)
        
        print(f"\n{cat['ticker']} (PDUFA: {cat['pdufa_date']})")
        print(f"  Signal: {summary.signal}")
        print(f"  Total Sweeps: {summary.total_sweeps}")
        print(f"  Call Sweeps: {summary.call_sweeps}")
        print(f"  Put Sweeps: {summary.put_sweeps}")
        
        if summary.total_sweeps > 0:
            print(f"  Total Premium: ${summary.total_premium:,.0f}")
            print(f"  Avg Vol/OI: {summary.avg_vol_oi_ratio:.1f}x")
            
            if summary.strongest_sweep:
                s = summary.strongest_sweep
                print(f"  Strongest Sweep:")
                print(f"    {s.contract_type.upper()} ${s.strike} exp {s.expiration.date()}")
                print(f"    Vol/OI: {s.vol_oi_ratio:.1f}x | Confidence: {s.confidence.value}")
        else:
            print("  No Golden Sweeps detected")
    
    # Example integration with ODIN
    print("\n" + "=" * 50)
    print("Example ODIN Integration:")
    print("-" * 50)
    
    # Mock ODIN prediction
    mock_odin = {
        "ticker": "RCKT",
        "approval_probability": 0.71,
        "mfg_risk_score": 0.0
    }
    
    # Get sweep summary
    pdufa = datetime.strptime("2026-03-28", '%Y-%m-%d')
    sweep_summary = detector.scan("RCKT", pdufa)
    
    # Integrate
    enhanced = integrate_sweep_signal(mock_odin, sweep_summary)
    
    print(f"Base ODIN Probability: {mock_odin['approval_probability']*100:.0f}%")
    print(f"Sweep Signal: {enhanced['signals']['golden_sweep']['signal']}")
    print(f"Adjustment: {enhanced['signals']['golden_sweep']['probability_adjustment']*100:+.0f}%")
    print(f"Adjusted Probability: {enhanced['approval_probability_adjusted']*100:.0f}%")
