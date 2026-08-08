#!/usr/bin/env python3
"""
ODIN Catalyst Options & Insider Scanner
========================================
Pulls ALL current options data and insider selling for Q1/H1 2026 catalyst tickers.

Uses:
- FinBrain API: Insider transactions, options put/call ratios
- FMP API: Current options chain data

API Keys (from environment):
- FINBRAIN_API_KEY
- FMP_API_KEY

Usage:
    python odin_catalyst_options_insider_scanner.py
    python odin_catalyst_options_insider_scanner.py --q1-only
    python odin_catalyst_options_insider_scanner.py --pdufa-only
"""

import os
import sys
import json
import time
import asyncio
import aiohttp
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================

FINBRAIN_API_KEY = os.getenv('FINBRAIN_API_KEY')
FMP_API_KEY = os.getenv('FMP_API_KEY')

# Rate limits
FINBRAIN_RATE_LIMIT = 5  # requests per second
FMP_RATE_LIMIT = 300     # requests per minute

# Output directory
OUTPUT_DIR = Path("odin_catalyst_scan_output")

# =============================================================================
# Q1/H1 2026 CATALYST TICKERS (from fda_2026-01-29.xlsx)
# =============================================================================

Q1_2026_TICKERS = [
    'ABBV', 'ACET', 'ACIU', 'ACRV', 'ADAG', 'ALDX', 'ALMS', 'ALZN', 'ANRO', 'APGE',
    'APRE', 'AQST', 'ARQT', 'ARTV', 'ASND', 'ATAI', 'AXSM', 'BAYRY', 'BBIO', 'BCDA',
    'BCYC', 'BFRI', 'BMRN', 'BMY', 'BTAI', 'CAPR', 'CGEM', 'CLDX', 'CLLS', 'CLNN',
    'CLSD', 'CMPS', 'CMPX', 'CTMX', 'CYBN', 'ETON', 'FGEN', 'GLUE', 'GOSS', 'GSK',
    'HOTH', 'IDYA', 'IMMP', 'INMB', 'INSM', 'IONS', 'IOVA', 'IRD', 'JNJ', 'KLRS',
    'KOD', 'KPTI', 'KZR', 'LLY', 'LNTH', 'LSTA', 'LXEO', 'MAZE', 'MBRX', 'MDCX',
    'MLTX', 'MLYS', 'MRK', 'NRSN', 'NSRX', 'OCUL', 'OKUR', 'ONCY', 'ORIC', 'OSTX',
    'PALI', 'PCSA', 'PDSB', 'PEPG', 'PHAR', 'PVLA', 'QNCX', 'RCKT', 'RCUS', 'REGN',
    'RGNX', 'RHHBY', 'RXRX', 'RYTM', 'SCYX', 'SKYE', 'SPRB', 'TARA', 'TBPH', 'TCRX',
    'TGTX', 'UPB', 'VNDA', 'VRDN', 'VTYX', 'WVE', 'XCUR', 'XENE', 'XOMA', 'ZBIO'
]

H1_2026_ADDITIONAL_TICKERS = [
    'ABEO', 'ABVX', 'ACHV', 'ACTU', 'ADCT', 'ALEC', 'ALGS', 'ALLO', 'ALPN', 'ALXO',
    'ARGX', 'ARVN', 'AVBP', 'AVDL', 'AZN', 'BCAB', 'BCRX', 'BCTX', 'BEAM', 'BHC',
    'BHVN', 'BIIB', 'BIOA', 'BIVI', 'BLTE', 'BMEA', 'BPMC', 'BSMO', 'BXRX', 'CBAY',
    'CDTX', 'CELC', 'CERS', 'CING', 'CLVR', 'CNTA', 'CNVS', 'COGT', 'CORT', 'CRSP',
    'CSTL', 'CTLT', 'CYT', 'DCGO', 'DNLI', 'DRMA', 'EDIT', 'ELEV', 'ELTX', 'EOLS',
    'EWTX', 'EXEL', 'FDMT', 'FHTX', 'FMTX', 'FOLD', 'FREQ', 'FULC', 'GBIO', 'GH',
    'GILD', 'GPCR', 'GRCE', 'GRFS', 'GTHX', 'HALO', 'HRMY', 'IBRX', 'ICPT', 'IMCR',
    'IMRX', 'IMTX', 'INCY', 'IRTC', 'ISEE', 'JANX', 'JNPR', 'KALV', 'KDNY', 'KNTK',
    'KRYS', 'KURA', 'KYMR', 'LPTX', 'LYEL', 'MDGL', 'MGNX', 'MIRM', 'MNKD', 'MREO',
    'MRSN', 'MRTX', 'NBIX', 'NEOG', 'NKTX', 'NRIX', 'NTLA', 'NUVA', 'NVAX', 'OMER',
    'ONVO', 'ORGO', 'PCVX', 'PFE', 'PHVS', 'PLRX', 'PRTX', 'PTGX', 'RARE', 'RCUS',
    'REPL', 'RLAY', 'RVMD', 'SAGE', 'SANA', 'SAVA', 'SBBP', 'SBRA', 'SGEN', 'SGMO',
    'SMMT', 'SNCE', 'SNDX', 'SPRY', 'SRPT', 'STOK', 'SUPN', 'SWTX', 'TALK', 'TCRT',
    'TEVA', 'TNGX', 'TVTX', 'TWST', 'UNCY', 'UTHR', 'VCEL', 'VERA', 'VERV', 'VIAV',
    'VKTX', 'VRTX', 'WINT', 'XBIT', 'XERS', 'YMAB', 'ZLAB', 'ZNTL', 'ZYME'
]

# High-priority PDUFA tickers (H1 2026)
PDUFA_H1_TICKERS = [
    'PHAR', 'AQST', 'RGNX', 'MRK', 'VNDA', 'ETON', 'ASND', 'BMRN', 'BMY', 'LNTH',
    'ALDX', 'RYTM', 'GSK', 'RCKT', 'DNLI', 'REPL', 'TVTX', 'GRCE', 'AXSM', 'INCY',
    'MGNX', 'ARGX', 'AZN', 'BIIB', 'MNKD', 'CING', 'PFE', 'ARVN', 'ACHV', 'UNCY',
    'ARQT', 'VRDN', 'GH'
]

# =============================================================================
# API CLIENTS
# =============================================================================

class FinBrainClient:
    """FinBrain API client for insider transactions and options data."""
    
    BASE_URL = "https://api.finbrain.tech/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        self.last_request = 0
        
    async def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < 1 / FINBRAIN_RATE_LIMIT:
            await asyncio.sleep(1 / FINBRAIN_RATE_LIMIT - elapsed)
        self.last_request = time.time()
        
    async def get_insider_transactions(self, ticker: str, limit: int = 100) -> Dict:
        """Get insider transactions for a ticker."""
        await self.init_session()
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/insider-transactions/{ticker}"
        params = {"api_key": self.api_key, "limit": limit}
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"ticker": ticker, "status": "SUCCESS", "data": data}
                elif resp.status == 404:
                    return {"ticker": ticker, "status": "NO_DATA", "data": []}
                else:
                    return {"ticker": ticker, "status": f"ERROR_{resp.status}", "data": []}
        except Exception as e:
            return {"ticker": ticker, "status": f"ERROR: {str(e)}", "data": []}
            
    async def get_options_put_call(self, ticker: str, limit: int = 100) -> Dict:
        """Get options put/call ratio history."""
        await self.init_session()
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/options-put-call/{ticker}"
        params = {"api_key": self.api_key, "limit": limit}
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"ticker": ticker, "status": "SUCCESS", "data": data}
                elif resp.status == 404:
                    return {"ticker": ticker, "status": "NO_DATA", "data": []}
                else:
                    return {"ticker": ticker, "status": f"ERROR_{resp.status}", "data": []}
        except Exception as e:
            return {"ticker": ticker, "status": f"ERROR: {str(e)}", "data": []}


class FMPClient:
    """FMP API client for options chain data."""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        self.request_count = 0
        self.minute_start = time.time()
        
    async def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self):
        """Enforce rate limiting (300/min)."""
        self.request_count += 1
        if self.request_count >= FMP_RATE_LIMIT:
            elapsed = time.time() - self.minute_start
            if elapsed < 60:
                await asyncio.sleep(60 - elapsed + 1)
            self.request_count = 0
            self.minute_start = time.time()
            
    async def get_options_chain(self, ticker: str) -> Dict:
        """Get current options chain for a ticker."""
        await self.init_session()
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/stock-options/{ticker}"
        params = {"apikey": self.api_key}
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return {"ticker": ticker, "status": "SUCCESS", "data": data}
                    else:
                        return {"ticker": ticker, "status": "NO_DATA", "data": []}
                elif resp.status == 404:
                    return {"ticker": ticker, "status": "NO_OPTIONS", "data": []}
                else:
                    return {"ticker": ticker, "status": f"ERROR_{resp.status}", "data": []}
        except Exception as e:
            return {"ticker": ticker, "status": f"ERROR: {str(e)}", "data": []}
            
    async def get_quote(self, ticker: str) -> Dict:
        """Get current quote for a ticker."""
        await self.init_session()
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/quote/{ticker}"
        params = {"apikey": self.api_key}
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return {"ticker": ticker, "status": "SUCCESS", "data": data[0] if data else {}}
                    return {"ticker": ticker, "status": "NO_DATA", "data": {}}
                else:
                    return {"ticker": ticker, "status": f"ERROR_{resp.status}", "data": {}}
        except Exception as e:
            return {"ticker": ticker, "status": f"ERROR: {str(e)}", "data": {}}


# =============================================================================
# DATA PROCESSING
# =============================================================================

def process_insider_transactions(data: List[Dict]) -> Dict:
    """Process insider transactions to extract selling signals."""
    if not data:
        return {
            "total_transactions": 0,
            "total_sells": 0,
            "total_buys": 0,
            "net_shares": 0,
            "net_value": 0,
            "sell_value_30d": 0,
            "buy_value_30d": 0,
            "recent_transactions": []
        }
    
    sells = [t for t in data if t.get('transaction_type', '').upper() in ['SELL', 'S', 'SALE']]
    buys = [t for t in data if t.get('transaction_type', '').upper() in ['BUY', 'P', 'PURCHASE']]
    
    # Calculate 30-day values
    cutoff = datetime.now() - timedelta(days=30)
    sell_value_30d = 0
    buy_value_30d = 0
    
    for t in data:
        try:
            tx_date = pd.to_datetime(t.get('date', t.get('transaction_date', '')))
            if pd.isna(tx_date):
                continue
            value = float(t.get('usd_value', t.get('value', 0)) or 0)
            if tx_date >= cutoff:
                if t.get('transaction_type', '').upper() in ['SELL', 'S', 'SALE']:
                    sell_value_30d += value
                elif t.get('transaction_type', '').upper() in ['BUY', 'P', 'PURCHASE']:
                    buy_value_30d += value
        except:
            continue
    
    return {
        "total_transactions": len(data),
        "total_sells": len(sells),
        "total_buys": len(buys),
        "net_shares": sum(float(t.get('shares', 0) or 0) for t in buys) - sum(float(t.get('shares', 0) or 0) for t in sells),
        "sell_value_30d": sell_value_30d,
        "buy_value_30d": buy_value_30d,
        "net_value_30d": buy_value_30d - sell_value_30d,
        "recent_transactions": data[:10]  # Keep 10 most recent
    }


def process_options_chain(data: List[Dict], current_price: float) -> Dict:
    """Process options chain to extract key metrics."""
    if not data:
        return {
            "total_contracts": 0,
            "expirations": [],
            "atm_calls": [],
            "atm_puts": [],
            "total_call_oi": 0,
            "total_put_oi": 0,
            "put_call_ratio": None,
            "max_pain": None,
            "nearest_expiry_iv": None
        }
    
    # Group by expiration
    expirations = {}
    for opt in data:
        exp = opt.get('expiration', opt.get('expirationDate', ''))
        if exp not in expirations:
            expirations[exp] = {'calls': [], 'puts': []}
        
        opt_type = opt.get('type', opt.get('optionType', '')).upper()
        if opt_type in ['CALL', 'C']:
            expirations[exp]['calls'].append(opt)
        elif opt_type in ['PUT', 'P']:
            expirations[exp]['puts'].append(opt)
    
    # Calculate totals
    total_call_oi = sum(float(opt.get('openInterest', opt.get('open_interest', 0)) or 0) for opt in data if opt.get('type', opt.get('optionType', '')).upper() in ['CALL', 'C'])
    total_put_oi = sum(float(opt.get('openInterest', opt.get('open_interest', 0)) or 0) for opt in data if opt.get('type', opt.get('optionType', '')).upper() in ['PUT', 'P'])
    
    put_call_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else None
    
    # Find ATM options (within 5% of current price)
    atm_calls = []
    atm_puts = []
    if current_price > 0:
        for opt in data:
            strike = float(opt.get('strike', opt.get('strikePrice', 0)) or 0)
            if abs(strike - current_price) / current_price <= 0.05:
                opt_type = opt.get('type', opt.get('optionType', '')).upper()
                if opt_type in ['CALL', 'C']:
                    atm_calls.append(opt)
                elif opt_type in ['PUT', 'P']:
                    atm_puts.append(opt)
    
    # Get nearest expiry IV
    nearest_expiry_iv = None
    if expirations:
        sorted_exps = sorted(expirations.keys())
        if sorted_exps:
            nearest_opts = expirations[sorted_exps[0]]['calls'] + expirations[sorted_exps[0]]['puts']
            ivs = [float(opt.get('impliedVolatility', opt.get('iv', 0)) or 0) for opt in nearest_opts if opt.get('impliedVolatility', opt.get('iv'))]
            if ivs:
                nearest_expiry_iv = sum(ivs) / len(ivs)
    
    return {
        "total_contracts": len(data),
        "expirations": sorted(expirations.keys())[:10],
        "total_call_oi": int(total_call_oi),
        "total_put_oi": int(total_put_oi),
        "put_call_ratio": round(put_call_ratio, 3) if put_call_ratio else None,
        "atm_call_count": len(atm_calls),
        "atm_put_count": len(atm_puts),
        "nearest_expiry_iv": round(nearest_expiry_iv * 100, 2) if nearest_expiry_iv and nearest_expiry_iv < 10 else nearest_expiry_iv
    }


def classify_insider_signal(insider_data: Dict) -> str:
    """Classify insider activity as BULLISH/BEARISH/NEUTRAL."""
    net_value = insider_data.get('net_value_30d', 0)
    sells = insider_data.get('total_sells', 0)
    buys = insider_data.get('total_buys', 0)
    
    if net_value > 100000:
        return "BULLISH"
    elif net_value < -500000:
        return "BEARISH"
    elif sells > buys * 3:
        return "BEARISH"
    elif buys > sells * 2:
        return "BULLISH"
    else:
        return "NEUTRAL"


def classify_options_signal(options_data: Dict) -> str:
    """Classify options activity as BULLISH/BEARISH/NEUTRAL."""
    pcr = options_data.get('put_call_ratio')
    if pcr is None:
        return "NO_DATA"
    
    if pcr > 1.5:
        return "BEARISH"
    elif pcr < 0.7:
        return "BULLISH"
    else:
        return "NEUTRAL"


# =============================================================================
# MAIN SCANNER
# =============================================================================

async def scan_ticker(
    ticker: str,
    finbrain: FinBrainClient,
    fmp: FMPClient,
    progress: Dict
) -> Dict:
    """Scan a single ticker for options and insider data."""
    
    result = {
        "ticker": ticker,
        "scan_timestamp": datetime.now().isoformat(),
        "quote": {},
        "insider": {},
        "options_chain": {},
        "options_flow": {},
        "signals": {}
    }
    
    # Get quote first
    quote_result = await fmp.get_quote(ticker)
    result["quote"] = quote_result.get("data", {})
    current_price = float(result["quote"].get("price", 0) or 0)
    
    # Get insider transactions (FinBrain)
    insider_result = await finbrain.get_insider_transactions(ticker)
    if insider_result["status"] == "SUCCESS":
        result["insider"] = process_insider_transactions(insider_result.get("data", []))
        result["signals"]["insider"] = classify_insider_signal(result["insider"])
    else:
        result["insider"] = {"status": insider_result["status"]}
        result["signals"]["insider"] = "NO_DATA"
    
    # Get options put/call ratio (FinBrain)
    pcr_result = await finbrain.get_options_put_call(ticker)
    if pcr_result["status"] == "SUCCESS":
        pcr_data = pcr_result.get("data", [])
        if pcr_data:
            latest = pcr_data[0] if isinstance(pcr_data, list) else pcr_data
            result["options_flow"] = {
                "latest_date": latest.get("date"),
                "put_call_ratio": latest.get("put_call_ratio"),
                "call_count": latest.get("call_count"),
                "put_count": latest.get("put_count"),
                "history_30d": pcr_data[:30] if isinstance(pcr_data, list) else []
            }
    
    # Get options chain (FMP)
    chain_result = await fmp.get_options_chain(ticker)
    if chain_result["status"] == "SUCCESS":
        result["options_chain"] = process_options_chain(chain_result.get("data", []), current_price)
        result["signals"]["options"] = classify_options_signal(result["options_chain"])
    else:
        result["options_chain"] = {"status": chain_result["status"]}
        result["signals"]["options"] = "NO_DATA"
    
    # Update progress
    progress["completed"] += 1
    pct = progress["completed"] / progress["total"] * 100
    print(f"\r  [{progress['completed']}/{progress['total']}] {pct:.1f}% - {ticker}: Insider={result['signals'].get('insider', 'N/A')}, Options={result['signals'].get('options', 'N/A')}", end="", flush=True)
    
    return result


async def run_scanner(
    tickers: List[str],
    finbrain_key: str,
    fmp_key: str,
    batch_size: int = 5
) -> List[Dict]:
    """Run the scanner on all tickers."""
    
    finbrain = FinBrainClient(finbrain_key)
    fmp = FMPClient(fmp_key)
    
    progress = {"completed": 0, "total": len(tickers)}
    results = []
    
    print(f"\n{'='*60}")
    print(f"ODIN CATALYST OPTIONS & INSIDER SCANNER")
    print(f"{'='*60}")
    print(f"Tickers to scan: {len(tickers)}")
    print(f"Batch size: {batch_size}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # Process in batches
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                scan_ticker(ticker, finbrain, fmp, progress)
                for ticker in batch
            ])
            results.extend(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(tickers):
                await asyncio.sleep(0.5)
                
    finally:
        await finbrain.close()
        await fmp.close()
    
    print(f"\n\n{'='*60}")
    print(f"Scan complete! {len(results)} tickers processed.")
    print(f"{'='*60}\n")
    
    return results


def generate_reports(results: List[Dict], output_dir: Path):
    """Generate output reports."""
    
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Full JSON dump
    json_path = output_dir / f"catalyst_scan_full_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✅ Full JSON: {json_path}")
    
    # 2. Summary DataFrame
    summary_rows = []
    for r in results:
        row = {
            "ticker": r["ticker"],
            "price": r["quote"].get("price"),
            "market_cap": r["quote"].get("marketCap"),
            "volume": r["quote"].get("volume"),
            # Insider
            "insider_signal": r["signals"].get("insider"),
            "insider_sells_30d": r["insider"].get("total_sells"),
            "insider_sell_value_30d": r["insider"].get("sell_value_30d"),
            "insider_buys_30d": r["insider"].get("total_buys"),
            "insider_buy_value_30d": r["insider"].get("buy_value_30d"),
            "insider_net_value_30d": r["insider"].get("net_value_30d"),
            # Options
            "options_signal": r["signals"].get("options"),
            "put_call_ratio": r["options_chain"].get("put_call_ratio") or r["options_flow"].get("put_call_ratio"),
            "total_call_oi": r["options_chain"].get("total_call_oi"),
            "total_put_oi": r["options_chain"].get("total_put_oi"),
            "nearest_iv": r["options_chain"].get("nearest_expiry_iv"),
            "expirations": len(r["options_chain"].get("expirations", [])),
        }
        summary_rows.append(row)
    
    summary_df = pd.DataFrame(summary_rows)
    
    # Sort by insider selling (most selling first)
    summary_df = summary_df.sort_values("insider_sell_value_30d", ascending=False, na_position='last')
    
    csv_path = output_dir / f"catalyst_scan_summary_{timestamp}.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"✅ Summary CSV: {csv_path}")
    
    # 3. High-alert tickers (heavy insider selling OR high put/call)
    alerts = summary_df[
        (summary_df["insider_signal"] == "BEARISH") |
        (summary_df["options_signal"] == "BEARISH")
    ].copy()
    
    if len(alerts) > 0:
        alerts_path = output_dir / f"catalyst_alerts_{timestamp}.csv"
        alerts.to_csv(alerts_path, index=False)
        print(f"⚠️  Alerts CSV: {alerts_path} ({len(alerts)} tickers)")
    
    # 4. Print summary to console
    print(f"\n{'='*60}")
    print("SCAN SUMMARY")
    print(f"{'='*60}")
    print(f"Total tickers scanned: {len(results)}")
    print(f"\nInsider Signals:")
    print(summary_df["insider_signal"].value_counts().to_string())
    print(f"\nOptions Signals:")
    print(summary_df["options_signal"].value_counts().to_string())
    
    # Top insider sellers
    print(f"\n{'='*60}")
    print("TOP 10 INSIDER SELLERS (30-day)")
    print(f"{'='*60}")
    top_sellers = summary_df.nlargest(10, "insider_sell_value_30d")[
        ["ticker", "price", "insider_sell_value_30d", "insider_signal"]
    ]
    print(top_sellers.to_string(index=False))
    
    # Highest put/call ratios
    print(f"\n{'='*60}")
    print("TOP 10 PUT/CALL RATIOS (Bearish)")
    print(f"{'='*60}")
    pcr_sorted = summary_df[summary_df["put_call_ratio"].notna()].nlargest(10, "put_call_ratio")[
        ["ticker", "price", "put_call_ratio", "options_signal"]
    ]
    print(pcr_sorted.to_string(index=False))
    
    return summary_df


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ODIN Catalyst Options & Insider Scanner")
    parser.add_argument("--q1-only", action="store_true", help="Scan only Q1 2026 tickers")
    parser.add_argument("--pdufa-only", action="store_true", help="Scan only PDUFA tickers")
    parser.add_argument("--batch-size", type=int, default=5, help="Concurrent requests per batch")
    parser.add_argument("--output-dir", type=str, default="odin_catalyst_scan_output", help="Output directory")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of specific tickers")
    args = parser.parse_args()
    
    # Check API keys
    if not FINBRAIN_API_KEY:
        print("❌ ERROR: FINBRAIN_API_KEY environment variable not set")
        sys.exit(1)
    if not FMP_API_KEY:
        print("❌ ERROR: FMP_API_KEY environment variable not set")
        sys.exit(1)
    
    print(f"✅ FinBrain API Key: ...{FINBRAIN_API_KEY[-4:]}")
    print(f"✅ FMP API Key: ...{FMP_API_KEY[-4:]}")
    
    # Select tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        print(f"📋 Custom tickers: {len(tickers)}")
    elif args.pdufa_only:
        tickers = PDUFA_H1_TICKERS
        print(f"📋 PDUFA-only mode: {len(tickers)} tickers")
    elif args.q1_only:
        tickers = Q1_2026_TICKERS
        print(f"📋 Q1-only mode: {len(tickers)} tickers")
    else:
        # Full H1 scan
        tickers = list(set(Q1_2026_TICKERS + H1_2026_ADDITIONAL_TICKERS + PDUFA_H1_TICKERS))
        print(f"📋 Full H1 mode: {len(tickers)} unique tickers")
    
    # Remove duplicates and sort
    tickers = sorted(set(tickers))
    
    # Run scanner
    output_dir = Path(args.output_dir)
    results = asyncio.run(run_scanner(tickers, FINBRAIN_API_KEY, FMP_API_KEY, args.batch_size))
    
    # Generate reports
    summary_df = generate_reports(results, output_dir)
    
    print(f"\n✅ Scan complete! Output saved to: {output_dir}/")


if __name__ == "__main__":
    main()
