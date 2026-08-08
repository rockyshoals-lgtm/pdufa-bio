#!/usr/bin/env python3
"""
FinBrain T-1 Feature Builder for Gungnir
==========================================
Reads finbrain_raw_cache.json + gungnir_readout_analysis.csv
Extracts T-1 compliant features for each of the 1,752 events.

Output: finbrain_features.json keyed by row index

FEATURES (all T-1 compliant — computed from data available before readout):
1. finbrain_sentiment_avg_30d  - Avg news sentiment T-30 to T-1
2. finbrain_sentiment_avg_7d   - Avg news sentiment T-7 to T-1
3. finbrain_sentiment_trend    - sentiment_7d - sentiment_30d
4. finbrain_pcr_avg_30d        - Avg put/call ratio T-30 to T-1
5. finbrain_pcr_avg_7d         - Avg put/call ratio T-7 to T-1
6. finbrain_pcr_trend          - pcr_7d - pcr_30d
7. finbrain_analyst_upgrades_90d  - Count of upgrades 90d pre-readout
8. finbrain_analyst_downgrades_90d - Count of downgrades 90d pre-readout
9. finbrain_analyst_net_signal  - upgrades - downgrades
10. finbrain_insider_net_90d    - Net insider buys - sells (count, 90d)
11. finbrain_insider_value_90d  - Net dollar value of insider txns (90d)
"""

import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict


def parse_date(s):
    """Parse YYYY-MM-DD string to date."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return None


def get_sentiment_window(sentiment_dict, event_date, days_back):
    """Get sentiment scores from T-days_back to T-1."""
    if not sentiment_dict or not event_date:
        return []
    scores = []
    start = event_date - timedelta(days=days_back)
    end = event_date - timedelta(days=1)
    for date_str, score_str in sentiment_dict.items():
        d = parse_date(date_str)
        if d and start <= d <= end:
            try:
                scores.append(float(score_str))
            except (ValueError, TypeError):
                pass
    return scores


def get_pcr_window(pcr_dict, event_date, days_back):
    """Get put/call ratios from T-days_back to T-1."""
    if not pcr_dict or not event_date:
        return []
    ratios = []
    start = event_date - timedelta(days=days_back)
    end = event_date - timedelta(days=1)
    for date_str, item in pcr_dict.items():
        d = parse_date(date_str)
        if d and start <= d <= end:
            ratio = item.get("ratio") if isinstance(item, dict) else None
            if ratio is not None:
                try:
                    ratios.append(float(ratio))
                except (ValueError, TypeError):
                    pass
    return ratios


def get_analyst_window(ratings_list, event_date, days_back):
    """Count upgrades and downgrades in window."""
    if not ratings_list or not event_date:
        return 0, 0
    upgrades = 0
    downgrades = 0
    start = event_date - timedelta(days=days_back)
    end = event_date - timedelta(days=1)

    upgrade_signals = {"upgrade", "upgraded", "buy", "outperform", "overweight", "strong buy", "positive"}
    downgrade_signals = {"downgrade", "downgraded", "sell", "underperform", "underweight", "strong sell", "negative", "reduce"}

    for item in ratings_list:
        if not isinstance(item, dict):
            continue
        d = parse_date(item.get("date", ""))
        if not d or not (start <= d <= end):
            continue

        signal = (item.get("signal", "") or "").lower()
        rtype = (item.get("type", "") or "").lower()

        if any(s in signal for s in upgrade_signals) or "upgrade" in rtype:
            upgrades += 1
        elif any(s in signal for s in downgrade_signals) or "downgrade" in rtype:
            downgrades += 1

    return upgrades, downgrades


def get_insider_window(insider_list, event_date, days_back):
    """Count net insider buys and total value in window."""
    if not insider_list or not event_date:
        return 0, 0.0
    net_count = 0
    net_value = 0.0
    start = event_date - timedelta(days=days_back)
    end = event_date - timedelta(days=1)

    for item in insider_list:
        if not isinstance(item, dict):
            continue
        d = parse_date(item.get("date", ""))
        if not d or not (start <= d <= end):
            continue

        txn_type = (item.get("transactionType", "") or item.get("transaction_type", "") or "").lower()
        value = 0.0
        try:
            val_str = str(item.get("value", item.get("usd_value", "0")))
            val_str = val_str.replace(",", "").replace("$", "").replace("+", "").replace("-", "")
            value = float(val_str) if val_str else 0.0
        except:
            pass

        if "purchase" in txn_type or "buy" in txn_type:
            net_count += 1
            net_value += value
        elif "sale" in txn_type or "sell" in txn_type:
            net_count -= 1
            net_value -= value

    return net_count, net_value


def safe_mean(values):
    """Mean of list, or None if empty."""
    return sum(values) / len(values) if values else None


def main():
    # Load data
    with open("finbrain_raw_cache.json") as f:
        fb_cache = json.load(f)

    rows = []
    with open("gungnir_readout_analysis.csv") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    print(f"FinBrain cache: {len(fb_cache)} tickers")
    print(f"Events: {len(rows)}")

    tickers_with_sent = sum(1 for v in fb_cache.values() if v.get("sentiment"))
    print(f"Tickers with sentiment: {tickers_with_sent}")

    # Build features per event
    features = {}
    covered = 0
    partial = 0

    for i, row in enumerate(rows):
        ticker = row.get("ticker", "")
        date_str = row.get("date", "")
        event_date = parse_date(date_str)

        fb = fb_cache.get(ticker, {})

        feat = {
            "ticker": ticker,
            "date": date_str,
            "finbrain_sentiment_avg_30d": None,
            "finbrain_sentiment_avg_7d": None,
            "finbrain_sentiment_trend": None,
            "finbrain_pcr_avg_30d": None,
            "finbrain_pcr_avg_7d": None,
            "finbrain_pcr_trend": None,
            "finbrain_analyst_upgrades_90d": None,
            "finbrain_analyst_downgrades_90d": None,
            "finbrain_analyst_net_signal": None,
            "finbrain_insider_net_90d": None,
            "finbrain_insider_value_90d": None,
            "finbrain_coverage": "none",
        }

        if not event_date or not fb.get("sentiment"):
            features[str(i)] = feat
            continue

        # Sentiment features
        sent_30 = get_sentiment_window(fb.get("sentiment", {}), event_date, 30)
        sent_7 = get_sentiment_window(fb.get("sentiment", {}), event_date, 7)

        feat["finbrain_sentiment_avg_30d"] = safe_mean(sent_30)
        feat["finbrain_sentiment_avg_7d"] = safe_mean(sent_7)
        if feat["finbrain_sentiment_avg_30d"] is not None and feat["finbrain_sentiment_avg_7d"] is not None:
            feat["finbrain_sentiment_trend"] = feat["finbrain_sentiment_avg_7d"] - feat["finbrain_sentiment_avg_30d"]

        # Put/Call features
        pcr_30 = get_pcr_window(fb.get("put_call", {}), event_date, 30)
        pcr_7 = get_pcr_window(fb.get("put_call", {}), event_date, 7)

        feat["finbrain_pcr_avg_30d"] = safe_mean(pcr_30)
        feat["finbrain_pcr_avg_7d"] = safe_mean(pcr_7)
        if feat["finbrain_pcr_avg_30d"] is not None and feat["finbrain_pcr_avg_7d"] is not None:
            feat["finbrain_pcr_trend"] = feat["finbrain_pcr_avg_7d"] - feat["finbrain_pcr_avg_30d"]

        # Analyst features
        upgrades, downgrades = get_analyst_window(fb.get("analyst_ratings", []), event_date, 90)
        feat["finbrain_analyst_upgrades_90d"] = upgrades
        feat["finbrain_analyst_downgrades_90d"] = downgrades
        feat["finbrain_analyst_net_signal"] = upgrades - downgrades

        # Insider features
        net_count, net_value = get_insider_window(fb.get("insider", []), event_date, 90)
        feat["finbrain_insider_net_90d"] = net_count
        feat["finbrain_insider_value_90d"] = round(net_value, 2)

        # Coverage assessment
        has_sentiment = feat["finbrain_sentiment_avg_30d"] is not None
        has_pcr = feat["finbrain_pcr_avg_30d"] is not None
        has_analyst = upgrades > 0 or downgrades > 0

        if has_sentiment and has_pcr:
            feat["finbrain_coverage"] = "full"
            covered += 1
        elif has_sentiment or has_pcr or has_analyst:
            feat["finbrain_coverage"] = "partial"
            partial += 1

        features[str(i)] = feat

    # Save
    with open("finbrain_features.json", "w") as f:
        json.dump(features, f, indent=2)

    none_count = len(rows) - covered - partial
    print(f"\nFeature extraction complete:")
    print(f"  Full coverage (sentiment + pcr): {covered}/{len(rows)} ({100*covered/len(rows):.1f}%)")
    print(f"  Partial coverage: {partial}/{len(rows)} ({100*partial/len(rows):.1f}%)")
    print(f"  No coverage: {none_count}/{len(rows)} ({100*none_count/len(rows):.1f}%)")

    # Sample features for top tickers
    print("\nSample features (first event per top ticker):")
    seen = set()
    for i, row in enumerate(rows):
        t = row["ticker"]
        if t in seen or t not in ["MRK", "PFE", "MRNA", "SAVA", "ABBV"]:
            continue
        seen.add(t)
        f = features[str(i)]
        print(f"  {t} ({f['date']}): sent_30d={f['finbrain_sentiment_avg_30d']}, pcr_30d={f['finbrain_pcr_avg_30d']}, coverage={f['finbrain_coverage']}")


if __name__ == "__main__":
    main()
