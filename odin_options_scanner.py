#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════════
ODIN GÖTTERDÄMMERUNG v4.0 - OPTIONS FLOW SCANNER
Smart Money Signal Detection for Biotech Catalysts
═══════════════════════════════════════════════════════════════════════════════════════════

Usage:
    export MASSIVE_API_KEY="your_api_key_here"
    python odin_options_scanner.py

    Or with specific ticker:
    python odin_options_scanner.py --ticker DBVT

Requirements:
    pip install polygon-api-client pandas tabulate requests

═══════════════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

# Try to import optional dependencies
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not installed. Install with: pip install pandas")

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ═══════════════════════════════════════════════════════════════════════════════════════════
# CATALYST DATABASE - UPDATE THIS REGULARLY
# ═══════════════════════════════════════════════════════════════════════════════════════════

BIOTECH_CATALYSTS = [
    # Format: (Ticker, Company, Drug, Indication, Catalyst Type, Date, Notes)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # JANUARY 2026
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "ATA",
        "company": "Atara Biotherapeutics",
        "drug": "Tabelecleucel",
        "indication": "EBV+ PTLD",
        "catalyst_type": "PDUFA",
        "date": "2026-01-15",
        "notes": "Allogeneic T-cell immunotherapy, Prior CRL",
        "odin_base_score": -20,  # Prior CRL, cell therapy
    },
    {
        "ticker": "TVTX",
        "company": "Travere Therapeutics",
        "drug": "Sparsentan",
        "indication": "FSGS (sNDA)",
        "catalyst_type": "PDUFA",
        "date": "2026-01-18",
        "notes": "Already approved for IgA nephropathy, line extension",
        "odin_base_score": 40,  # Approved drug, line extension
    },
    {
        "ticker": "OYST",
        "company": "Oyster Point Pharma",
        "drug": "Brimochol PF",
        "indication": "Presbyopia",
        "catalyst_type": "PDUFA",
        "date": "2026-01-24",
        "notes": "Fixed-dose combo, eye drops",
        "odin_base_score": 20,
    },
    {
        "ticker": "AQST",
        "company": "Aquestive Therapeutics",
        "drug": "Anaphylm",
        "indication": "Anaphylaxis (sublingual epinephrine)",
        "catalyst_type": "PDUFA",
        "date": "2026-01-29",
        "notes": "Novel delivery, competitive space",
        "odin_base_score": 15,
    },
    {
        "ticker": "DSGN",
        "company": "Design Therapeutics",
        "drug": "Enhertu combo",
        "indication": "HER2+ Breast Cancer (1L)",
        "catalyst_type": "PDUFA",
        "date": "2026-01-30",
        "notes": "Daiichi Sankyo/AstraZeneca sBLA",
        "odin_base_score": 60,  # Large pharma, proven drug
    },
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # FEBRUARY 2026
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "IONS",
        "company": "Ionis Pharmaceuticals",
        "drug": "Donidalorsen",
        "indication": "HAE (Hereditary Angioedema)",
        "catalyst_type": "PDUFA",
        "date": "2026-02-21",
        "notes": "ASO platform, competitive with Takeda",
        "odin_base_score": 45,
    },
    {
        "ticker": "AKRO",
        "company": "Akero Therapeutics",
        "drug": "Efruxifermin",
        "indication": "MASH/NASH",
        "catalyst_type": "PDUFA",
        "date": "2026-02-28",
        "notes": "FGF21 analog, hot indication post-Rezdiffra",
        "odin_base_score": 35,  # Competitive space
    },
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # MARCH 2026
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "ALDX",
        "company": "Aldeyra Therapeutics",
        "drug": "Reproxalap",
        "indication": "Dry Eye Disease",
        "catalyst_type": "PDUFA",
        "date": "2026-03-16",
        "notes": "EXTENDED - Prior CRL, resubmission",
        "odin_base_score": -10,  # Prior CRL (efficacy concerns)
    },
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # H1 2026 - BLA SUBMISSIONS EXPECTED (Dates TBD)
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "DBVT",
        "company": "DBV Technologies",
        "drug": "Viaskin Peanut",
        "indication": "Peanut Allergy (4-7 years)",
        "catalyst_type": "BLA_SUBMISSION",
        "date": "2026-06-30",  # H1 2026
        "notes": "VITESSE Phase 3 positive Dec 2025, BTD, Prior CRL 2020",
        "odin_base_score": 50,  # Strong Phase 3, but prior CRL history
    },
    {
        "ticker": "CAPR",
        "company": "Capricor Therapeutics",
        "drug": "Deramiocel",
        "indication": "DMD Cardiomyopathy",
        "catalyst_type": "BLA_RESUB",
        "date": "2026-06-30",  # After HOPE-3 data
        "notes": "HOPE-3 positive, resubmission after CRL",
        "odin_base_score": 25,  # Positive Phase 3, but prior CRL
    },
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # PHASE 3 READOUTS - 2026 (High Impact)
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "BMRN",
        "company": "BioMarin",
        "drug": "Voxzogo",
        "indication": "Achondroplasia (infant)",
        "catalyst_type": "PHASE3_DATA",
        "date": "2026-03-31",  # Q1 2026
        "notes": "Line extension to infants",
        "odin_base_score": 55,
    },
    {
        "ticker": "SRPT",
        "company": "Sarepta Therapeutics",
        "drug": "SRP-9001",
        "indication": "DMD Gene Therapy",
        "catalyst_type": "CONFIRMATORY_DATA",
        "date": "2026-06-30",  # 2026
        "notes": "Confirmatory data for accelerated approval",
        "odin_base_score": 40,
    },
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # WATCHLIST - POTENTIAL 2026 PDUFA (Submissions pending)
    # ═══════════════════════════════════════════════════════════════════════════════════════
    {
        "ticker": "RARE",
        "company": "Ultragenyx",
        "drug": "DTX401",
        "indication": "GSDIa Gene Therapy",
        "catalyst_type": "PDUFA_POTENTIAL",
        "date": "2026-12-31",  # After CRL resolution
        "notes": "Prior CRL Oct 2025, resubmission path unclear",
        "odin_base_score": -15,
    },
    {
        "ticker": "KURA",
        "company": "Kura Oncology",
        "drug": "Ziftomenib",
        "indication": "AML",
        "catalyst_type": "NDA_SUBMISSION",
        "date": "2026-06-30",  # H1 2026 submission expected
        "notes": "Menin inhibitor, strong data",
        "odin_base_score": 50,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MASSIVE.COM API CLIENT (Polygon.io rebrand)
# ═══════════════════════════════════════════════════════════════════════════════════════════

class MassiveAPIClient:
    """Client for Massive.com (formerly Polygon.io) API"""
    
    BASE_URL = "https://api.polygon.io"  # Still uses polygon.io endpoints
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"apiKey": api_key}
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to API"""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params or {}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return {"error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # OPTIONS DATA ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════════════════
    
    def get_options_chain(self, ticker: str, expiration_date_gte: str = None) -> dict:
        """Get options chain snapshot for a ticker"""
        params = {}
        if expiration_date_gte:
            params["expiration_date.gte"] = expiration_date_gte
        return self._get(f"/v3/snapshot/options/{ticker}", params)
    
    def get_options_contracts(self, ticker: str, 
                              contract_type: str = None,
                              expiration_date_gte: str = None,
                              expiration_date_lte: str = None) -> dict:
        """List options contracts for underlying ticker"""
        params = {"underlying_ticker": ticker, "limit": 1000}
        if contract_type:
            params["contract_type"] = contract_type
        if expiration_date_gte:
            params["expiration_date.gte"] = expiration_date_gte
        if expiration_date_lte:
            params["expiration_date.lte"] = expiration_date_lte
        return self._get("/v3/reference/options/contracts", params)
    
    def get_options_trades(self, options_ticker: str, 
                           date: str = None,
                           limit: int = 1000) -> dict:
        """Get trades for specific options contract"""
        params = {"limit": limit}
        endpoint = f"/v3/trades/{options_ticker}"
        if date:
            params["timestamp.gte"] = f"{date}T00:00:00Z"
            params["timestamp.lte"] = f"{date}T23:59:59Z"
        return self._get(endpoint, params)
    
    def get_options_aggregates(self, options_ticker: str,
                                from_date: str,
                                to_date: str,
                                timespan: str = "day") -> dict:
        """Get OHLCV aggregates for options contract"""
        return self._get(
            f"/v2/aggs/ticker/{options_ticker}/range/1/{timespan}/{from_date}/{to_date}"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # STOCK DATA ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════════════════
    
    def get_stock_snapshot(self, ticker: str) -> dict:
        """Get current stock snapshot"""
        return self._get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}")
    
    def get_stock_aggregates(self, ticker: str,
                              from_date: str,
                              to_date: str,
                              timespan: str = "day") -> dict:
        """Get OHLCV aggregates for stock"""
        return self._get(
            f"/v2/aggs/ticker/{ticker}/range/1/{timespan}/{from_date}/{to_date}"
        )
    
    def get_ticker_details(self, ticker: str) -> dict:
        """Get company details"""
        return self._get(f"/v3/reference/tickers/{ticker}")


# ═══════════════════════════════════════════════════════════════════════════════════════════
# ODIN SMART MONEY SIGNAL CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════════

class ODINOptionsAnalyzer:
    """Calculate ODIN v4.0 Smart Money Signals from options data"""
    
    def __init__(self, client: MassiveAPIClient):
        self.client = client
    
    def analyze_ticker(self, ticker: str, catalyst_date: str) -> dict:
        """
        Comprehensive options analysis for a biotech ticker before catalyst
        
        Returns dict with:
        - put_call_ratio: Current put/call volume ratio
        - put_call_signal: ODIN adjustment based on ratio
        - unusual_volume: Whether volume is unusual
        - iv_skew: Put IV vs Call IV difference
        - open_interest_trend: Rising/falling OI
        - large_trades: Any block trades detected
        - smart_money_score: Total ODIN adjustment
        """
        
        results = {
            "ticker": ticker,
            "catalyst_date": catalyst_date,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "data_available": False,
            "put_call_ratio": None,
            "put_call_signal": 0,
            "unusual_volume_flag": False,
            "unusual_volume_signal": 0,
            "iv_skew": None,
            "iv_skew_signal": 0,
            "oi_trend": None,
            "oi_signal": 0,
            "price_action_30d": None,
            "price_action_signal": 0,
            "smart_money_score": 0,
            "confidence": "LOW",
            "raw_data": {},
            "errors": []
        }
        
        try:
            # Calculate date ranges
            catalyst_dt = datetime.strptime(catalyst_date, "%Y-%m-%d")
            today = datetime.now()
            
            # Get options expiring around catalyst
            exp_start = (catalyst_dt - timedelta(days=7)).strftime("%Y-%m-%d")
            exp_end = (catalyst_dt + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # 1. GET OPTIONS CHAIN SNAPSHOT
            # ═══════════════════════════════════════════════════════════════════════════════
            chain_data = self.client.get_options_chain(ticker, exp_start)
            
            if "results" in chain_data and chain_data["results"]:
                results["data_available"] = True
                results["raw_data"]["chain"] = chain_data
                
                # Calculate put/call ratio from chain
                total_call_volume = 0
                total_put_volume = 0
                total_call_oi = 0
                total_put_oi = 0
                put_ivs = []
                call_ivs = []
                
                for contract in chain_data["results"]:
                    details = contract.get("details", {})
                    day = contract.get("day", {})
                    greeks = contract.get("greeks", {})
                    
                    contract_type = details.get("contract_type", "").lower()
                    volume = day.get("volume", 0) or 0
                    oi = day.get("open_interest", 0) or 0
                    iv = greeks.get("implied_volatility")
                    
                    if contract_type == "call":
                        total_call_volume += volume
                        total_call_oi += oi
                        if iv:
                            call_ivs.append(iv)
                    elif contract_type == "put":
                        total_put_volume += volume
                        total_put_oi += oi
                        if iv:
                            put_ivs.append(iv)
                
                # ═══════════════════════════════════════════════════════════════════════════
                # 2. CALCULATE PUT/CALL RATIO
                # ═══════════════════════════════════════════════════════════════════════════
                if total_call_volume > 0:
                    pc_ratio = total_put_volume / total_call_volume
                    results["put_call_ratio"] = round(pc_ratio, 2)
                    
                    # ODIN Signal: Put/Call Ratio
                    if pc_ratio > 2.0:
                        results["put_call_signal"] = -20  # Very bearish
                    elif pc_ratio > 1.5:
                        results["put_call_signal"] = -15  # Bearish
                    elif pc_ratio > 1.2:
                        results["put_call_signal"] = -10  # Slightly bearish
                    elif pc_ratio < 0.3:
                        results["put_call_signal"] = +15  # Very bullish
                    elif pc_ratio < 0.5:
                        results["put_call_signal"] = +10  # Bullish
                    elif pc_ratio < 0.7:
                        results["put_call_signal"] = +5   # Slightly bullish
                
                # ═══════════════════════════════════════════════════════════════════════════
                # 3. CALCULATE IV SKEW
                # ═══════════════════════════════════════════════════════════════════════════
                if put_ivs and call_ivs:
                    avg_put_iv = sum(put_ivs) / len(put_ivs)
                    avg_call_iv = sum(call_ivs) / len(call_ivs)
                    iv_skew = (avg_put_iv - avg_call_iv) * 100  # Convert to percentage points
                    results["iv_skew"] = round(iv_skew, 1)
                    
                    # ODIN Signal: IV Skew
                    if iv_skew > 20:
                        results["iv_skew_signal"] = -15  # Heavy put premium = fear
                    elif iv_skew > 10:
                        results["iv_skew_signal"] = -10
                    elif iv_skew < -15:
                        results["iv_skew_signal"] = +10  # Call premium = optimism
                    elif iv_skew < -5:
                        results["iv_skew_signal"] = +5
                
                # ═══════════════════════════════════════════════════════════════════════════
                # 4. CHECK FOR UNUSUAL VOLUME
                # ═══════════════════════════════════════════════════════════════════════════
                total_volume = total_call_volume + total_put_volume
                total_oi = total_call_oi + total_put_oi
                
                if total_oi > 0:
                    volume_oi_ratio = total_volume / total_oi
                    if volume_oi_ratio > 5:
                        results["unusual_volume_flag"] = True
                        # Check if it's put-heavy unusual volume
                        if total_put_volume > total_call_volume * 1.5:
                            results["unusual_volume_signal"] = -15  # Bearish unusual activity
                        elif total_call_volume > total_put_volume * 1.5:
                            results["unusual_volume_signal"] = +10  # Bullish unusual activity
            
            else:
                results["errors"].append("No options chain data available")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # 5. GET 30-DAY PRICE ACTION
            # ═══════════════════════════════════════════════════════════════════════════════
            thirty_days_ago = (today - timedelta(days=35)).strftime("%Y-%m-%d")
            today_str = today.strftime("%Y-%m-%d")
            
            stock_data = self.client.get_stock_aggregates(ticker, thirty_days_ago, today_str)
            
            if "results" in stock_data and len(stock_data["results"]) > 1:
                results["raw_data"]["stock"] = stock_data
                
                prices = stock_data["results"]
                start_price = prices[0]["c"]  # Close 30 days ago
                end_price = prices[-1]["c"]   # Most recent close
                
                price_change = ((end_price - start_price) / start_price) * 100
                results["price_action_30d"] = round(price_change, 1)
                
                # ODIN Signal: Price Action
                if price_change > 30:
                    results["price_action_signal"] = +15  # Strong momentum
                elif price_change > 20:
                    results["price_action_signal"] = +10
                elif price_change < -25:
                    results["price_action_signal"] = -20  # Smart money selling
                elif price_change < -15:
                    results["price_action_signal"] = -15
                elif price_change < -10:
                    results["price_action_signal"] = -10
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # 6. CALCULATE TOTAL SMART MONEY SCORE
            # ═══════════════════════════════════════════════════════════════════════════════
            results["smart_money_score"] = (
                results["put_call_signal"] +
                results["iv_skew_signal"] +
                results["unusual_volume_signal"] +
                results["price_action_signal"]
            )
            
            # Determine confidence level
            signals_available = sum([
                results["put_call_ratio"] is not None,
                results["iv_skew"] is not None,
                results["price_action_30d"] is not None
            ])
            
            if signals_available >= 3:
                results["confidence"] = "HIGH"
            elif signals_available >= 2:
                results["confidence"] = "MEDIUM"
            else:
                results["confidence"] = "LOW"
            
        except Exception as e:
            results["errors"].append(str(e))
        
        return results
    
    def generate_odin_report(self, ticker: str, catalyst: dict, options_analysis: dict) -> dict:
        """
        Generate final ODIN v4.0 score combining fundamentals and smart money
        """
        
        # Base score from fundamental analysis
        base_score = catalyst.get("odin_base_score", 0)
        
        # Smart money adjustment
        smart_money = options_analysis.get("smart_money_score", 0)
        
        # Weight: 60% fundamentals, 40% smart money
        # But if smart money contradicts fundamentals, defer to smart money
        
        if base_score > 20 and smart_money < -15:
            # Fundamentals bullish but smart money bearish → DEFER TO SMART MONEY
            final_score = base_score * 0.4 + smart_money * 1.5
            signal_agreement = "CONTRADICTION - DEFER TO SMART MONEY"
        elif base_score < -20 and smart_money > 15:
            # Fundamentals bearish but smart money bullish → cautious upgrade
            final_score = base_score * 0.6 + smart_money * 0.8
            signal_agreement = "CONTRADICTION - SMART MONEY DISAGREES"
        else:
            # Signals agree or neutral
            final_score = base_score * 0.6 + smart_money * 0.4
            if abs(base_score) > 20 and abs(smart_money) > 10:
                if (base_score > 0 and smart_money > 0) or (base_score < 0 and smart_money < 0):
                    final_score += 10 * (1 if base_score > 0 else -1)  # Conviction bonus
                    signal_agreement = "CONFIRMATION - HIGH CONVICTION"
                else:
                    signal_agreement = "MIXED SIGNALS"
            else:
                signal_agreement = "NEUTRAL"
        
        # Convert score to probability
        probability = self._score_to_probability(final_score)
        
        # Generate action tier
        action_tier = self._get_action_tier(probability)
        
        return {
            "ticker": ticker,
            "company": catalyst.get("company"),
            "drug": catalyst.get("drug"),
            "indication": catalyst.get("indication"),
            "catalyst_type": catalyst.get("catalyst_type"),
            "catalyst_date": catalyst.get("date"),
            "fundamental_score": base_score,
            "smart_money_score": smart_money,
            "signal_agreement": signal_agreement,
            "final_score": round(final_score, 1),
            "probability": probability,
            "action_tier": action_tier,
            "confidence": options_analysis.get("confidence", "LOW"),
            "key_signals": {
                "put_call_ratio": options_analysis.get("put_call_ratio"),
                "iv_skew": options_analysis.get("iv_skew"),
                "price_30d": options_analysis.get("price_action_30d"),
                "unusual_volume": options_analysis.get("unusual_volume_flag"),
            },
            "notes": catalyst.get("notes")
        }
    
    def _score_to_probability(self, score: float) -> int:
        """Convert ODIN score to approval probability"""
        if score < -100:
            return 5
        elif score < -80:
            return 10
        elif score < -60:
            return 15
        elif score < -40:
            return 20
        elif score < -20:
            return 30
        elif score < 0:
            return 40
        elif score < 20:
            return 50
        elif score < 40:
            return 60
        elif score < 60:
            return 70
        elif score < 80:
            return 80
        elif score < 100:
            return 85
        else:
            return 90
    
    def _get_action_tier(self, probability: int) -> str:
        """Convert probability to investment action tier"""
        if probability <= 15:
            return "STRONG AVOID ⛔"
        elif probability <= 30:
            return "AVOID ❌"
        elif probability <= 45:
            return "HOLD/REDUCE ⚠️"
        elif probability <= 60:
            return "SPECULATIVE BUY 🎲"
        elif probability <= 80:
            return "BUY ✅"
        else:
            return "STRONG BUY 🚀"


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════════════════

def run_full_scan(api_key: str, specific_ticker: str = None):
    """Run ODIN scan on all catalysts"""
    
    print("\n" + "═" * 80)
    print("ODIN GÖTTERDÄMMERUNG v4.0 - OPTIONS FLOW SCANNER")
    print("═" * 80)
    print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 80 + "\n")
    
    client = MassiveAPIClient(api_key)
    analyzer = ODINOptionsAnalyzer(client)
    
    results = []
    
    # Filter catalysts if specific ticker requested
    catalysts = BIOTECH_CATALYSTS
    if specific_ticker:
        catalysts = [c for c in catalysts if c["ticker"].upper() == specific_ticker.upper()]
        if not catalysts:
            print(f"No catalyst found for ticker: {specific_ticker}")
            return
    
    for catalyst in catalysts:
        ticker = catalyst["ticker"]
        print(f"\n🔍 Analyzing {ticker} - {catalyst['company']}...")
        print(f"   Drug: {catalyst['drug']} | {catalyst['indication']}")
        print(f"   Catalyst: {catalyst['catalyst_type']} on {catalyst['date']}")
        
        # Get options analysis
        options_analysis = analyzer.analyze_ticker(ticker, catalyst["date"])
        
        # Generate ODIN report
        report = analyzer.generate_odin_report(ticker, catalyst, options_analysis)
        results.append(report)
        
        # Print summary
        print(f"\n   📊 ODIN ANALYSIS:")
        print(f"   ├─ Fundamental Score: {report['fundamental_score']:+d}")
        print(f"   ├─ Smart Money Score: {report['smart_money_score']:+d}")
        print(f"   ├─ Signal Agreement:  {report['signal_agreement']}")
        print(f"   ├─ Final Score:       {report['final_score']:+.1f}")
        print(f"   ├─ Probability:       {report['probability']}%")
        print(f"   └─ ACTION: {report['action_tier']}")
        
        if report["key_signals"]["put_call_ratio"]:
            print(f"\n   📈 Key Signals:")
            print(f"   ├─ Put/Call Ratio:  {report['key_signals']['put_call_ratio']}")
            if report["key_signals"]["iv_skew"]:
                print(f"   ├─ IV Skew:         {report['key_signals']['iv_skew']:+.1f}%")
            if report["key_signals"]["price_30d"]:
                print(f"   ├─ 30-Day Return:   {report['key_signals']['price_30d']:+.1f}%")
            print(f"   └─ Unusual Volume:  {'⚠️ YES' if report['key_signals']['unusual_volume'] else 'No'}")
        
        print("-" * 60)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════
    # SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════════════════════════════
    print("\n" + "═" * 80)
    print("SUMMARY - ALL CATALYSTS RANKED BY PROBABILITY")
    print("═" * 80 + "\n")
    
    # Sort by probability (highest first for buys, lowest first for avoids)
    results_sorted = sorted(results, key=lambda x: x["probability"], reverse=True)
    
    if HAS_TABULATE:
        table_data = []
        for r in results_sorted:
            table_data.append([
                r["ticker"],
                r["drug"][:20],
                r["catalyst_date"],
                f"{r['fundamental_score']:+d}",
                f"{r['smart_money_score']:+d}",
                f"{r['probability']}%",
                r["action_tier"]
            ])
        
        headers = ["Ticker", "Drug", "Date", "Fund", "Smart$", "Prob", "Action"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        for r in results_sorted:
            print(f"{r['ticker']:6} | {r['drug'][:20]:20} | {r['catalyst_date']} | "
                  f"Fund:{r['fundamental_score']:+3d} | Smart$:{r['smart_money_score']:+3d} | "
                  f"Prob:{r['probability']:2d}% | {r['action_tier']}")
    
    # Save results to JSON
    output_file = f"odin_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Full results saved to: {output_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="ODIN v4.0 Options Flow Scanner")
    parser.add_argument("--ticker", "-t", help="Analyze specific ticker only")
    parser.add_argument("--api-key", "-k", help="Massive.com API key (or set MASSIVE_API_KEY env var)")
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    
    if not api_key:
        print("ERROR: No API key provided!")
        print("\nSet your API key:")
        print("  export MASSIVE_API_KEY='your_key_here'")
        print("\nOr pass it as argument:")
        print("  python odin_options_scanner.py --api-key YOUR_KEY")
        sys.exit(1)
    
    run_full_scan(api_key, args.ticker)


if __name__ == "__main__":
    main()
