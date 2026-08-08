#!/usr/bin/env python3
"""
ODIN v9.0 FinBrain Batch Data Collector (REST API Version)
===========================================================
Collects FinBrain alternative data for all ODIN tickers.

Usage:
    python odin_finbrain_collector.py --api-key YOUR_API_KEY

No additional dependencies required (uses requests only).
"""

import json
import argparse
import time
import os
import shutil
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List


def utc_now() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Configuration
BASE_URL = "https://api.finbrain.tech/v1"
ENV_API_KEY = "FINBRAIN_API_KEY"  # Environment variable name
MARKET = "S&P 500"  # URL-encoded as "S%26P%20500"
MARKET_ENCODED = "S%26P%20500"
CACHE_FILE = "finbrain_cache.json"
TICKERS_FILE = "odin_tickers_clean.txt"

# Data types to collect per ticker
DATA_TYPES = [
    "predictions",
    "news_sentiment", 
    "put_call",
    "insider_transactions",
    "analyst_ratings",
    "linkedin"
]


def load_cache(cache_file: str) -> Dict[str, Any]:
    """Load existing cache or create new one."""
    path = Path(cache_file)
    if path.exists():
        with open(path, 'r') as f:
            cache = json.load(f)
        ticker_count = len([k for k in cache.keys() if k != "metadata"])
        print(f"✓ Loaded existing cache with {ticker_count} tickers")
        return cache
    else:
        return {
            "metadata": {
                "created": utc_now(),
                "total_tickers": 0,
                "collected": 0,
                "collection_phase": "Phase 1 - FinBrain Batch Collection"
            }
        }


def save_cache(cache: Dict[str, Any], cache_file: str):
    """Save cache to disk (Windows-compatible)."""
    temp_file = cache_file + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(cache, f, indent=2, default=str)
    # shutil.move handles cross-platform overwrites correctly
    shutil.move(temp_file, cache_file)


def load_tickers(tickers_file: str) -> List[str]:
    """Load tickers from file."""
    with open(tickers_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers


def is_ticker_complete(cache: Dict, ticker: str) -> bool:
    """Check if ticker has all data types collected."""
    if ticker not in cache:
        return False
    entry = cache[ticker]
    return entry.get("status") == "COMPLETE"


def get_missing_data_types(cache: Dict, ticker: str) -> List[str]:
    """Get list of data types not yet collected for ticker."""
    if ticker not in cache:
        return DATA_TYPES.copy()
    
    entry = cache[ticker]
    if entry.get("status") == "COMPLETE":
        return []
    
    collected = entry.get("collected", [])
    return [dt for dt in DATA_TYPES if dt not in collected]


def api_call(endpoint: str, api_key: str) -> Optional[Dict]:
    """Make API call with error handling."""
    url = f"{endpoint}&token={api_key}" if "?" in endpoint else f"{endpoint}?token={api_key}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # No data for this ticker
        else:
            print(f"      API error {response.status_code}: {response.text[:100]}")
            return None
    except Exception as e:
        print(f"      Request error: {e}")
        return None


def collect_predictions(ticker: str, api_key: str) -> Optional[Dict]:
    """Collect AI price predictions."""
    url = f"{BASE_URL}/ticker/{ticker}/predictions/daily"
    result = api_call(url, api_key)
    if result:
        return {
            "expected_short": result.get("expectedShort") or result.get("expected_short"),
            "expected_mid": result.get("expectedMid") or result.get("expected_mid"),
            "expected_long": result.get("expectedLong") or result.get("expected_long"),
            "technical_analysis": (result.get("technicalAnalysis") or result.get("technical_analysis", ""))[:200],
            "last_sentiment_score": result.get("sentimentScore") or result.get("sentiment_score")
        }
    return None


def collect_news_sentiment(ticker: str, api_key: str) -> Optional[List[Dict]]:
    """Collect news sentiment time series."""
    url = f"{BASE_URL}/sentiments/{MARKET_ENCODED}/{ticker}?dateFrom=2025-01-01"
    result = api_call(url, api_key)
    if result:
        sentiments = result.get("sentiments") or result.get("sentiment") or []
        return [
            {"date": s.get("date"), "score": s.get("sentiment") or s.get("score")}
            for s in sentiments[:30]
        ]
    return None


def collect_put_call(ticker: str, api_key: str) -> Optional[List[Dict]]:
    """Collect options put/call ratio data."""
    url = f"{BASE_URL}/putcalldata/{MARKET_ENCODED}/{ticker}?dateFrom=2025-01-01"
    result = api_call(url, api_key)
    if result:
        data = result.get("putCallData") or result.get("put_call_data") or []
        return [
            {
                "date": pc.get("date"),
                "put_call_ratio": pc.get("putCallRatio") or pc.get("ratio"),
                "call_count": pc.get("callCount") or pc.get("call_count"),
                "put_count": pc.get("putCount") or pc.get("put_count")
            }
            for pc in data[:15]
        ]
    return None


def collect_insider_transactions(ticker: str, api_key: str) -> Optional[List[Dict]]:
    """Collect insider transaction data."""
    url = f"{BASE_URL}/insidertransactions/{MARKET_ENCODED}/{ticker}"
    result = api_call(url, api_key)
    if result:
        txns = result.get("insiderTransactions") or result.get("insider_transactions") or []
        return [
            {
                "date": tx.get("date"),
                "insider_name": tx.get("insiderTradings") or tx.get("insider_name"),
                "relationship": tx.get("relationship"),
                "transaction_type": tx.get("transaction") or tx.get("transaction_type"),
                "usd_value": tx.get("USDValue") or tx.get("usd_value"),
                "shares": tx.get("shares"),
                "total_shares": tx.get("totalShares") or tx.get("total_shares")
            }
            for tx in txns[:20]
        ]
    return None


def collect_analyst_ratings(ticker: str, api_key: str) -> Optional[List[Dict]]:
    """Collect analyst ratings data."""
    url = f"{BASE_URL}/analystratings/{MARKET_ENCODED}/{ticker}?dateFrom=2024-01-01"
    result = api_call(url, api_key)
    if result:
        ratings = result.get("analystRatings") or result.get("analyst_ratings") or []
        return [
            {
                "date": ar.get("date"),
                "institution": ar.get("institution"),
                "signal": ar.get("signal"),
                "rating_type": ar.get("ratingType") or ar.get("rating_type"),
                "target_price_from": ar.get("targetPriceFrom") or ar.get("target_price_from"),
                "target_price_to": ar.get("targetPriceTo") or ar.get("target_price_to")
            }
            for ar in ratings[:15]
        ]
    return None


def collect_linkedin(ticker: str, api_key: str) -> Optional[List[Dict]]:
    """Collect LinkedIn metrics data."""
    url = f"{BASE_URL}/linkedindata/{MARKET_ENCODED}/{ticker}?dateFrom=2025-06-01"
    result = api_call(url, api_key)
    if result:
        data = result.get("linkedinData") or result.get("linkedin_data") or []
        return [
            {
                "date": ld.get("date"),
                "employee_count": ld.get("employeeCount") or ld.get("employee_count"),
                "followers_count": ld.get("followersCount") or ld.get("followers_count")
            }
            for ld in data[:20]
        ]
    return None


def collect_ticker_data(ticker: str, api_key: str, missing_types: List[str]) -> Dict[str, Any]:
    """Collect all missing data types for a ticker."""
    data = {}
    
    collectors = {
        "predictions": collect_predictions,
        "news_sentiment": collect_news_sentiment,
        "put_call": collect_put_call,
        "insider_transactions": collect_insider_transactions,
        "analyst_ratings": collect_analyst_ratings,
        "linkedin": collect_linkedin
    }
    
    for data_type in missing_types:
        if data_type in collectors:
            result = collectors[data_type](ticker, api_key)
            if result is not None:
                data[data_type] = result
                print(f"    ✓ {data_type}")
            else:
                # Still mark as collected (no data available)
                data[data_type] = []
                print(f"    ○ {data_type} (no data)")
            time.sleep(0.05)  # Small delay between calls
    
    return data


def update_cache_entry(cache: Dict, ticker: str, new_data: Dict[str, Any]):
    """Update or create cache entry for ticker."""
    timestamp = utc_now()
    
    if ticker not in cache:
        cache[ticker] = {
            "ticker": ticker,
            "query_timestamp": timestamp,
            "status": "PARTIAL",
            "collected": []
        }
    
    entry = cache[ticker]
    entry["query_timestamp"] = timestamp
    
    # Map data to cache fields
    field_mapping = {
        "predictions": "predictions",
        "news_sentiment": "news_sentiment",
        "put_call": "put_call_data",
        "insider_transactions": "insider_transactions",
        "analyst_ratings": "analyst_ratings",
        "linkedin": "linkedin_data"
    }
    
    for data_type, data in new_data.items():
        field_name = field_mapping.get(data_type, data_type)
        entry[field_name] = data
        if data_type not in entry.get("collected", []):
            if "collected" not in entry:
                entry["collected"] = []
            entry["collected"].append(data_type)
    
    # Check if complete
    if set(entry.get("collected", [])) >= set(DATA_TYPES):
        entry["status"] = "COMPLETE"
        # Clean up tracking fields
        if "collected" in entry:
            del entry["collected"]
        if "missing" in entry:
            del entry["missing"]
    else:
        entry["missing"] = [dt for dt in DATA_TYPES if dt not in entry.get("collected", [])]


def print_summary(cache: Dict, tickers: List[str]):
    """Print collection summary."""
    complete = sum(1 for t in tickers if is_ticker_complete(cache, t))
    partial = sum(1 for t in tickers if t in cache and not is_ticker_complete(cache, t))
    remaining = len(tickers) - complete - partial
    
    print("\n" + "="*60)
    print("COLLECTION SUMMARY")
    print("="*60)
    print(f"Total tickers:    {len(tickers)}")
    print(f"Complete:         {complete} ({100*complete/len(tickers):.1f}%)")
    print(f"Partial:          {partial}")
    print(f"Remaining:        {remaining}")
    print(f"Cache file:       {CACHE_FILE}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="ODIN FinBrain Batch Collector")
    parser.add_argument("--api-key", default=os.environ.get(ENV_API_KEY), 
                        help=f"FinBrain API key (or set {ENV_API_KEY} env var)")
    parser.add_argument("--tickers", default=TICKERS_FILE, help="Tickers file")
    parser.add_argument("--cache", default=CACHE_FILE, help="Cache file")
    parser.add_argument("--limit", type=int, default=0, help="Max tickers to process (0=all)")
    parser.add_argument("--priority", nargs="+", help="Priority tickers to process first")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    # Check for API key
    if not args.api_key:
        print(f"✗ No API key provided")
        print(f"  Either set {ENV_API_KEY} environment variable:")
        print(f"    set {ENV_API_KEY}=your-key-here")
        print(f"  Or pass via command line:")
        print(f"    python {Path(__file__).name} --api-key YOUR_KEY")
        return
    
    # Initialize
    print("="*60)
    print("ODIN v9.0 FinBrain Batch Collector (REST API)")
    print("="*60)
    print(f"✓ API key loaded from {'environment' if os.environ.get(ENV_API_KEY) else 'command line'}")
    
    # Test API connection first
    print("✓ Testing API connection...")
    test_url = f"{BASE_URL}/available/markets?token={args.api_key}"
    try:
        test_resp = requests.get(test_url, timeout=10)
        if test_resp.status_code != 200:
            print(f"✗ API connection failed: {test_resp.status_code}")
            print(f"  Response: {test_resp.text[:200]}")
            return
        print("✓ API connection successful")
    except Exception as e:
        print(f"✗ API connection error: {e}")
        return
    
    # Load data
    cache = load_cache(args.cache)
    
    # Check if tickers file exists
    tickers_path = Path(args.tickers)
    if not tickers_path.exists():
        print(f"✗ Tickers file not found: {args.tickers}")
        print("  Make sure odin_tickers_clean.txt is in the same directory")
        return
    
    tickers = load_tickers(args.tickers)
    print(f"✓ Loaded {len(tickers)} tickers from {args.tickers}")
    
    # Update metadata
    cache["metadata"]["total_tickers"] = len(tickers)
    
    # Determine processing order
    if args.priority:
        priority_set = set(args.priority)
        priority_tickers = [t for t in args.priority if t in tickers]
        other_tickers = [t for t in tickers if t not in priority_set]
        process_order = priority_tickers + other_tickers
        print(f"✓ Priority tickers: {', '.join(priority_tickers)}")
    else:
        process_order = tickers
    
    # Filter to incomplete tickers
    to_process = []
    for ticker in process_order:
        if is_ticker_complete(cache, ticker):
            continue
        to_process.append(ticker)
    
    if args.limit > 0:
        to_process = to_process[:args.limit]
    
    already_complete = len(tickers) - len([t for t in tickers if not is_ticker_complete(cache, t)])
    print(f"✓ Processing {len(to_process)} tickers ({already_complete} already complete)")
    print()
    
    if not to_process:
        print("All tickers already collected!")
        print_summary(cache, tickers)
        return
    
    # Process tickers
    start_time = time.time()
    api_calls = 0
    
    for i, ticker in enumerate(to_process, 1):
        missing = get_missing_data_types(cache, ticker)
        if not missing:
            continue
        
        print(f"[{i}/{len(to_process)}] {ticker} - collecting {len(missing)} data types...")
        
        new_data = collect_ticker_data(ticker, args.api_key, missing)
        api_calls += len(missing)
        
        if new_data:
            update_cache_entry(cache, ticker, new_data)
            
            # Update metadata
            complete_count = sum(1 for t in tickers if is_ticker_complete(cache, t))
            cache["metadata"]["collected"] = complete_count
            cache["metadata"]["last_updated"] = utc_now()
            
            # Save incrementally
            save_cache(cache, args.cache)
        
        # Progress update every 10 tickers
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = api_calls / elapsed * 3600 if elapsed > 0 else 0
            eta_seconds = (len(to_process) - i) * 6 * (elapsed / api_calls) if api_calls > 0 else 0
            print(f"    → Progress: {i}/{len(to_process)} | Calls: {api_calls} | Rate: {rate:.0f}/hr | ETA: {eta_seconds/60:.1f}m")
    
    # Final summary
    elapsed = time.time() - start_time
    print_summary(cache, tickers)
    print(f"\nCompleted in {elapsed:.1f}s ({api_calls} API calls)")
    if elapsed > 0:
        print(f"Average rate: {api_calls/elapsed*3600:.0f} calls/hour")


if __name__ == "__main__":
    main()
