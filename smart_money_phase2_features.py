#!/usr/bin/env python3
"""
Smart Money Phase 2: Event-level feature engineering.

For each PDUFA event in the ODIN training set, compute smart money features
from the latest 13F-HR snapshot PUBLICLY AVAILABLE at T-1 (i.e. filing_date
strictly before catalyst_date).

Features (12 per event):
    god_tier_any_present           Binary: any god tier fund holding ticker
    god_tier_count                 # funds with position > 0
    god_tier_weighted_count        Sum of weights of holders
    god_tier_total_value_usd       Sum of values across holders
    god_tier_max_fund_value_usd    Largest single fund position
    god_tier_top_fund_weight       Weight of largest holder
    god_tier_concentration         Weighted avg fund quality
    god_tier_quarter_delta_value   Change vs prior quarter snapshot
    god_tier_new_positions         # funds entering (0->>0)
    god_tier_exited_positions      # funds exiting (>0->0)
    god_tier_total_shares          Sum of shares across holders
    god_tier_snapshot_lag_days     pdufa_date - filing_date

Output: smart_money_event_features.csv (event_id, ticker, catalyst_date, + 12 features)
"""
from __future__ import annotations
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

WORKDIR = Path("/sessions/confident-serene-ptolemy/mnt/9realms")
ODIN_CSV = WORKDIR / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
CACHE_JSON = WORKDIR / "smart_money_13f_cache.json"
OUT_CSV = WORKDIR / "smart_money_event_features.csv"


def main():
    print("Loading ODIN events...")
    events = pd.read_csv(ODIN_CSV)
    events["catalyst_date"] = pd.to_datetime(events["catalyst_date"], errors="coerce")
    events = events.dropna(subset=["catalyst_date", "ticker"]).copy()
    events["ticker_u"] = events["ticker"].astype(str).str.upper()
    print(f"  {len(events)} events with valid ticker + catalyst_date")

    print("Loading smart money cache...")
    with open(CACHE_JSON) as f:
        cache = json.load(f)
    weights = {cik: info["weight"] for cik, info in cache["methodology"]["god_tier_funds"].items()}
    fund_name_by_cik = {cik: info["name"] for cik, info in cache["methodology"]["god_tier_funds"].items()}

    # Build holdings lookup: (ticker_u, filing_date) -> list[dict]
    # Also build a sorted unique list of (ticker_u, fund_cik, filing_date, period, value, shares)
    print("Indexing holdings...")
    rows = cache["holdings"]
    for r in rows:
        r["ticker_u"] = str(r["ticker"]).upper()
        r["weight"] = weights.get(r["cik"], 0.0)
    # group by ticker
    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_ticker[r["ticker_u"]].append(r)
    # sort each bucket chronologically
    for t in by_ticker:
        by_ticker[t].sort(key=lambda r: r["filing_date"])
    print(f"  {len(by_ticker)} tickers in cache; {sum(len(v) for v in by_ticker.values())} holdings rows")

    # For each event compute features
    print("Computing per-event features...")
    feat_rows = []
    for i, ev in events.iterrows():
        ticker = ev["ticker_u"]
        pdufa = ev["catalyst_date"]
        pdufa_s = pdufa.strftime("%Y-%m-%d")

        # Default (no data)
        out = {
            "event_id": ev["event_id"],
            "ticker": ticker,
            "catalyst_date": pdufa_s,
            "god_tier_any_present": 0,
            "god_tier_count": 0,
            "god_tier_weighted_count": 0.0,
            "god_tier_total_value_usd": 0.0,
            "god_tier_max_fund_value_usd": 0.0,
            "god_tier_top_fund_weight": 0.0,
            "god_tier_concentration": 0.0,
            "god_tier_quarter_delta_value": 0.0,
            "god_tier_new_positions": 0,
            "god_tier_exited_positions": 0,
            "god_tier_total_shares": 0.0,
            "god_tier_snapshot_lag_days": -1,
        }

        hits = by_ticker.get(ticker, [])
        if not hits:
            feat_rows.append(out)
            continue

        # Find the latest filing_date strictly before pdufa
        # holdings list is chronological on filing_date
        # Each record has (cik, filing_date, value_usd, shares)
        # We need the snapshot: for each fund, the most recent report as-of T-1.
        latest_by_fund: dict[str, dict] = {}
        prior_by_fund: dict[str, dict] = {}  # prior quarter snapshot
        latest_filing_dates: list[str] = []

        for h in hits:
            if h["filing_date"] >= pdufa_s:
                break
            # Update: latest_by_fund keeps the most recent filing PER FUND
            fund = h["cik"]
            if fund in latest_by_fund:
                # Move previous latest into prior
                prior_by_fund[fund] = latest_by_fund[fund]
            latest_by_fund[fund] = h
            latest_filing_dates.append(h["filing_date"])

        if not latest_by_fund:
            feat_rows.append(out)
            continue

        # Compute features
        values = [h["value_usd"] for h in latest_by_fund.values() if h["value_usd"] > 0]
        shares = [h["shares"] for h in latest_by_fund.values() if h["value_usd"] > 0]
        fund_weights_held = [h["weight"] for h in latest_by_fund.values() if h["value_usd"] > 0]
        n_holders = len(values)

        if n_holders == 0:
            feat_rows.append(out)
            continue

        total_val = sum(values)
        max_val = max(values)
        # top fund's weight (by value, find argmax)
        top = max(latest_by_fund.values(), key=lambda h: h["value_usd"])
        top_weight = top["weight"]

        # concentration: weighted avg fund weight, weighted by position size
        if total_val > 0:
            concentration = sum(h["value_usd"] * h["weight"] for h in latest_by_fund.values() if h["value_usd"] > 0) / total_val
        else:
            concentration = 0.0

        # Quarter delta: compare current latest_by_fund total to sum of prior_by_fund for same funds
        prior_total = sum(h["value_usd"] for h in prior_by_fund.values())
        delta_val = total_val - prior_total

        # New / exited positions
        # new: fund in latest with value>0 but NOT in prior (or prior value==0)
        # exited: fund in prior with value>0 but NOT in latest (or latest value==0)
        new_pos = 0
        exited_pos = 0
        all_funds_seen = set(latest_by_fund) | set(prior_by_fund)
        for fund in all_funds_seen:
            cur = latest_by_fund.get(fund, {}).get("value_usd", 0.0)
            prev = prior_by_fund.get(fund, {}).get("value_usd", 0.0)
            if prev == 0 and cur > 0:
                new_pos += 1
            if prev > 0 and cur == 0:
                exited_pos += 1

        # Snapshot lag: most recent filing_date across all holders
        most_recent_filing = max(h["filing_date"] for h in latest_by_fund.values())
        lag_days = (pdufa - pd.to_datetime(most_recent_filing)).days

        out.update({
            "god_tier_any_present": 1,
            "god_tier_count": n_holders,
            "god_tier_weighted_count": round(sum(fund_weights_held), 4),
            "god_tier_total_value_usd": round(total_val, 2),
            "god_tier_max_fund_value_usd": round(max_val, 2),
            "god_tier_top_fund_weight": round(top_weight, 4),
            "god_tier_concentration": round(concentration, 4),
            "god_tier_quarter_delta_value": round(delta_val, 2),
            "god_tier_new_positions": new_pos,
            "god_tier_exited_positions": exited_pos,
            "god_tier_total_shares": round(sum(shares), 0),
            "god_tier_snapshot_lag_days": int(lag_days),
        })
        feat_rows.append(out)

    df = pd.DataFrame(feat_rows)
    df.to_csv(OUT_CSV, index=False)
    print()
    print("=" * 70)
    print(f"DONE. Saved {OUT_CSV}")
    print(f"  {len(df)} events scored")
    print(f"  {df['god_tier_any_present'].sum()} with god_tier presence ({100*df['god_tier_any_present'].mean():.1f}%)")
    print()
    print("Feature summary (non-zero events only):")
    nz = df[df["god_tier_any_present"] == 1]
    for col in ["god_tier_count", "god_tier_weighted_count", "god_tier_total_value_usd",
                "god_tier_concentration", "god_tier_new_positions", "god_tier_exited_positions",
                "god_tier_snapshot_lag_days"]:
        print(f"  {col:35s}  mean={nz[col].mean():12.2f}  median={nz[col].median():12.2f}  max={nz[col].max():12.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
