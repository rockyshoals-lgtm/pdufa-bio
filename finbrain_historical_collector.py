#!/usr/bin/env python3
"""
FinBrain Historical Data Collector (2021-2023 window)
=====================================================
Second pass: collects sentiment + put/call for the 2021-2023 window
that the main collector misses due to the 500-entry cap.

Merges into the existing finbrain_raw_cache.json.
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
CACHE_FILE = "finbrain_raw_cache.json"
DATASET = "gungnir_readout_analysis.csv"
RATE_LIMIT_DELAY = 0.35


def api_get(url, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 429:
                time.sleep(5)
                continue
            return r.json() if r.ok else None
        except:
            if attempt < retries:
                time.sleep(2)
            continue
    return None


def main():
    # Load existing cache
    with open(CACHE_FILE) as f:
        cache = json.load(f)

    # Find tickers that have a market but need historical data
    # Only process tickers with events before 2024-04
    rows = []
    with open(DATASET) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # Find tickers with pre-2024 events
    tickers_need_history = set()
    for row in rows:
        if row["date"] < "2024-04-01":
            tickers_need_history.add(row["ticker"])

    print(f"Tickers with pre-2024 events: {len(tickers_need_history)}")

    # Filter to those already in cache with a known market
    eligible = []
    for t in tickers_need_history:
        c = cache.get(t, {})
        market = c.get("market")
        if market and market != "NOT_FOUND":
            # Check if we already have historical sentiment
            sent = c.get("sentiment_historical", {})
            if not sent:
                eligible.append((t, market))

    print(f"Eligible (have market, no historical data yet): {len(eligible)}")

    collected = 0
    for i, (ticker, market) in enumerate(eligible):
        market_enc = market.replace("&", "%26").replace(" ", "%20")
        print(f"[{i+1}/{len(eligible)}] {ticker} ({market})...", end=" ", flush=True)

        # Sentiment 2021-2023
        data = api_get(f"{BASE}/sentiments/{market_enc}/{ticker}?dateFrom=2021-01-01&dateTo=2023-12-31&token={API_KEY}")
        time.sleep(RATE_LIMIT_DELAY)
        hist_sent = {}
        if data:
            hist_sent = data.get("sentimentAnalysis", {})

        # Put/Call 2021-2023
        data = api_get(f"{BASE}/putcalldata/{market_enc}/{ticker}?dateFrom=2021-01-01&dateTo=2023-12-31&token={API_KEY}")
        time.sleep(RATE_LIMIT_DELAY)
        hist_pc = {}
        if data:
            pc_list = data.get("putCallData", [])
            hist_pc = {item["date"]: item for item in pc_list} if isinstance(pc_list, list) else {}

        # Merge into existing sentiment/put_call dicts
        existing_sent = cache[ticker].get("sentiment", {})
        existing_pc = cache[ticker].get("put_call", {})

        # Historical goes first (won't overwrite newer data)
        merged_sent = {**hist_sent, **existing_sent}
        merged_pc = {**hist_pc, **existing_pc}

        cache[ticker]["sentiment"] = merged_sent
        cache[ticker]["put_call"] = merged_pc
        cache[ticker]["sentiment_historical"] = True  # flag that we've done historical pass
        cache[ticker]["historical_collected_at"] = datetime.now(timezone.utc).isoformat()

        print(f"sent={len(hist_sent)} new ({len(merged_sent)} total), pc={len(hist_pc)} new ({len(merged_pc)} total)")
        collected += 1

        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            print(f"  [saved cache after {collected} tickers]")

    # Final save
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"\nDone! Collected historical data for {collected} tickers.")

    # Verify coverage improvement
    events_with_sent = 0
    for row in rows:
        t = row["ticker"]
        d = row["date"]
        sent = cache.get(t, {}).get("sentiment", {})
        dates = sorted(sent.keys())
        if dates and dates[0] <= d:
            events_with_sent += 1

    print(f"Events with sentiment coverage: {events_with_sent}/{len(rows)} ({100*events_with_sent/len(rows):.1f}%)")


if __name__ == "__main__":
    main()
