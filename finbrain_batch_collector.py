#!/usr/bin/env python3
"""
FinBrain Batch Collector for Gungnir Training Set
==================================================
Collects sentiment, put/call, analyst ratings, insider data for all
unique tickers in the training set via REST API.

Outputs: finbrain_raw_cache.json (raw API responses per ticker)
"""

import json
import csv
import time
import os
import requests
from datetime import datetime, timezone
from collections import Counter

API_KEY = os.environ.get("FINBRAIN_API_KEY", "5813fe19-a03c-4873-a7be-354315c39b80")
BASE = "https://api.finbrain.tech/v1"
MARKETS = ["NASDAQ", "NYSE", "S%26P%20500", "OTC%20Market"]
CACHE_FILE = "finbrain_raw_cache.json"
DATASET = "gungnir_readout_analysis.csv"
RATE_LIMIT_DELAY = 0.35  # seconds between API calls


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def api_get(url, retries=2):
    """GET with retry and rate limiting."""
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 429:
                print("    Rate limited, waiting 5s...")
                time.sleep(5)
                continue
            if r.ok:
                return r.json()
            else:
                return None
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            return None
    return None


def find_market(ticker):
    """Find which market a ticker belongs to."""
    for market in MARKETS:
        data = api_get(f"{BASE}/sentiments/{market}/{ticker}?dateFrom=2025-01-01&token={API_KEY}")
        time.sleep(RATE_LIMIT_DELAY)
        if data and data.get("sentimentAnalysis"):
            return market.replace("%26", "&").replace("%20", " ")
    return None


def collect_ticker(ticker, market_encoded):
    """Collect all data types for a ticker."""
    result = {"collected_at": datetime.now(timezone.utc).isoformat()}

    # Sentiment (from 2021 for full training coverage)
    data = api_get(f"{BASE}/sentiments/{market_encoded}/{ticker}?dateFrom=2021-01-01&token={API_KEY}")
    time.sleep(RATE_LIMIT_DELAY)
    if data:
        result["sentiment"] = data.get("sentimentAnalysis", {})

    # Put/Call ratio
    data = api_get(f"{BASE}/putcalldata/{market_encoded}/{ticker}?dateFrom=2021-01-01&token={API_KEY}")
    time.sleep(RATE_LIMIT_DELAY)
    if data:
        pc = data.get("putCallData", [])
        result["put_call"] = {item["date"]: item for item in pc} if isinstance(pc, list) else pc

    # Analyst ratings
    data = api_get(f"{BASE}/analystratings/{market_encoded}/{ticker}?dateFrom=2021-01-01&token={API_KEY}")
    time.sleep(RATE_LIMIT_DELAY)
    if data:
        ar = data.get("analystRatings", [])
        result["analyst_ratings"] = ar

    # Insider transactions
    data = api_get(f"{BASE}/insidertransactions/{market_encoded}/{ticker}?token={API_KEY}")
    time.sleep(RATE_LIMIT_DELAY)
    if data:
        result["insider"] = data.get("insiderTransactions", [])

    return result


def main():
    # Load training data to get unique tickers
    rows = []
    with open(DATASET) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    ticker_counts = Counter(r["ticker"] for r in rows)
    unique_tickers = sorted(ticker_counts.keys(), key=lambda t: -ticker_counts[t])
    print(f"Dataset: {len(rows)} events, {len(unique_tickers)} unique tickers")

    # Load existing cache
    cache = load_cache()
    already_done = {t for t in cache if cache[t].get("sentiment") or cache[t].get("market") == "NOT_FOUND"}
    remaining = [t for t in unique_tickers if t not in already_done]
    print(f"Cache: {len(already_done)} done, {len(remaining)} remaining")

    # Process remaining tickers
    total_collected = len(already_done)
    for i, ticker in enumerate(remaining):
        print(f"[{i+1}/{len(remaining)}] {ticker} ({ticker_counts[ticker]} events)...", end=" ", flush=True)

        # Find market
        market = find_market(ticker)
        if not market:
            cache[ticker] = {"market": "NOT_FOUND", "collected_at": datetime.now(timezone.utc).isoformat()}
            print("NOT FOUND")
            save_cache(cache)
            continue

        market_encoded = market.replace("&", "%26").replace(" ", "%20")
        print(f"[{market}]", end=" ", flush=True)

        # Collect all data
        ticker_data = collect_ticker(ticker, market_encoded)
        ticker_data["market"] = market
        cache[ticker] = ticker_data
        total_collected += 1

        sent_count = len(ticker_data.get("sentiment", {}))
        pc_count = len(ticker_data.get("put_call", {}))
        ar_count = len(ticker_data.get("analyst_ratings", []))
        print(f"sent={sent_count}, pc={pc_count}, ar={ar_count}")

        # Save every 5 tickers
        if (i + 1) % 5 == 0:
            save_cache(cache)
            print(f"  [saved cache: {total_collected} tickers]")

    save_cache(cache)
    print(f"\nDone! {total_collected} tickers in cache.")

    # Coverage summary
    events_covered = sum(ticker_counts[t] for t in cache if cache[t].get("sentiment"))
    print(f"Events with sentiment data: {events_covered}/{len(rows)} ({100*events_covered/len(rows):.1f}%)")


if __name__ == "__main__":
    main()
