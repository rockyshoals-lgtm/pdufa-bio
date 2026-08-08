#!/usr/bin/env python3
"""
BIFROST v5.1 — Short Interest Data Ingestion Pipeline
======================================================
Collects short interest, float, and options data for the Explosion Detector.

Data Sources:
  1. yfinance: Current short interest %, shares short, float, shares outstanding
  2. FINRA API: Historical bi-monthly short interest (free, CSV/JSON)
  3. FINRA RegSHO: Daily short sale volume (free, CSV)
  4. SEC EDGAR: Float and shares outstanding from filings

Target Features for v5.1 Explosion Detector:
  - pct_float_short: % of float that is sold short
  - days_to_cover: shares_short / avg_daily_volume
  - short_ratio_change: change in short interest over last 2 reporting periods
  - float_size: total float shares (smaller = more explosive)
  - float_turnover: avg_daily_volume / float (high = hot stock)
  - surprise_x_short: (1 - odin_score) * pct_float_short (holy grail interaction)
  - short_x_micro: pct_float_short * is_micro (short + small = squeeze)
  - cost_to_borrow: (requires Ortex/paid data — use proxy from short % for now)

Pipeline Phases:
  Phase 1: yfinance snapshot — current short interest for all training tickers
  Phase 2: FINRA historical — backfill 2020-2026 bi-monthly short interest
  Phase 3: Feature engineering — compute all v5.1 candidate features
  Phase 4: Merge with BIFROST v5 training data

Usage:
  python bifrost_v51_short_interest.py --snapshot          # Phase 1: yfinance snapshot
  python bifrost_v51_short_interest.py --historical         # Phase 2: FINRA backfill
  python bifrost_v51_short_interest.py --engineer           # Phase 3: Feature engineering
  python bifrost_v51_short_interest.py --all                # Run all phases
"""

import json, os, sys, time, math, csv
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ============================================================================
# CONFIG
# ============================================================================

CACHE_DIR = Path(__file__).parent
SNAPSHOT_CACHE = CACHE_DIR / "short_interest_snapshot.json"
HISTORICAL_CACHE = CACHE_DIR / "short_interest_historical.json"
FINRA_DAILY_CACHE = CACHE_DIR / "finra_daily_short_volume.json"
V51_FEATURES_CACHE = CACHE_DIR / "bifrost_v51_features.json"

# FINRA API endpoints
FINRA_API_BASE = "https://api.finra.org/data/group"
FINRA_SHORT_INTEREST = f"{FINRA_API_BASE}/otcMarket/name/consolidatedShortInterest"
FINRA_REGSHO_DAILY = f"{FINRA_API_BASE}/OTCMarket/name/regShoDaily"

# Rate limiting
YFINANCE_DELAY = 0.3   # seconds between yfinance calls
FINRA_DELAY = 1.0       # seconds between FINRA API calls


# ============================================================================
# PHASE 1: yfinance Snapshot — Current Short Interest
# ============================================================================

def phase1_yfinance_snapshot(tickers: list = None, force_refresh: bool = False):
    """Collect current short interest data from yfinance for all tickers.

    yfinance provides:
      - sharesShort: total shares currently sold short
      - sharesPercentSharesOut: short interest as % of shares outstanding
      - shortRatio: days to cover (shares_short / avg_daily_volume)
      - shortPercentOfFloat: short interest as % of float
      - floatShares: total float shares
      - sharesOutstanding: total shares outstanding
      - averageVolume: 10-day average volume
      - averageVolume10days: 10-day average volume
      - dateShortInterest: timestamp of last short interest report
    """
    try:
        import yfinance as yf
    except ImportError:
        print("[ERROR] yfinance not installed: pip install yfinance --break-system-packages")
        return {}

    # Load existing cache
    cache = {}
    if SNAPSHOT_CACHE.exists() and not force_refresh:
        with open(SNAPSHOT_CACHE) as f:
            cache = json.load(f)

    # If no tickers specified, load from BIFROST training data
    if tickers is None:
        tickers = _load_bifrost_tickers()

    print(f"\n{'='*60}")
    print(f"  PHASE 1: yfinance Short Interest Snapshot")
    print(f"  {len(tickers)} tickers to process")
    print(f"{'='*60}")

    results = {}
    errors = []
    skipped = 0

    for i, ticker in enumerate(tickers):
        # Skip if already cached within last 7 days
        if ticker in cache and not force_refresh:
            cached_date = cache[ticker].get("fetch_date", "")
            if cached_date:
                try:
                    cached_dt = datetime.strptime(cached_date, "%Y-%m-%d")
                    if (datetime.now() - cached_dt).days < 7:
                        results[ticker] = cache[ticker]
                        skipped += 1
                        continue
                except:
                    pass

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            data = {
                "ticker": ticker,
                "shares_short": info.get("sharesShort", 0) or 0,
                "shares_pct_out": info.get("sharesPercentSharesOut", 0) or 0,
                "short_ratio": info.get("shortRatio", 0) or 0,
                "short_pct_float": info.get("shortPercentOfFloat", 0) or 0,
                "float_shares": info.get("floatShares", 0) or 0,
                "shares_outstanding": info.get("sharesOutstanding", 0) or 0,
                "avg_volume": info.get("averageVolume", 0) or 0,
                "avg_volume_10d": info.get("averageVolume10days", 0) or 0,
                "market_cap": info.get("marketCap", 0) or 0,
                "current_price": info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0,
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0) or 0,
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0) or 0,
                "date_short_interest": info.get("dateShortInterest", 0),
                "fetch_date": datetime.now().strftime("%Y-%m-%d"),
            }

            # Derived features
            if data["float_shares"] > 0:
                data["float_turnover"] = data["avg_volume"] / data["float_shares"]
            else:
                data["float_turnover"] = 0

            if data["shares_outstanding"] > 0:
                data["float_pct"] = data["float_shares"] / data["shares_outstanding"]
            else:
                data["float_pct"] = 0

            results[ticker] = data

            if (i + 1) % 25 == 0:
                print(f"  [{i+1}/{len(tickers)}] Processed {ticker}: "
                      f"SI={data['short_pct_float']:.1%}, "
                      f"DTC={data['short_ratio']:.1f}, "
                      f"Float={data['float_shares']/1e6:.1f}M")

        except Exception as e:
            errors.append((ticker, str(e)))
            results[ticker] = {"ticker": ticker, "error": str(e), "fetch_date": datetime.now().strftime("%Y-%m-%d")}

        time.sleep(YFINANCE_DELAY)

    # Save cache
    all_results = {**cache, **results}
    with open(SNAPSHOT_CACHE, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Summary
    valid = [r for r in results.values() if "error" not in r and r.get("shares_short", 0) > 0]
    print(f"\n  Results: {len(valid)} valid / {len(errors)} errors / {skipped} cached")

    if valid:
        si_values = [r["short_pct_float"] for r in valid if r["short_pct_float"] > 0]
        if si_values:
            print(f"  Short Interest: mean={sum(si_values)/len(si_values):.1%}, "
                  f"median={sorted(si_values)[len(si_values)//2]:.1%}, "
                  f"max={max(si_values):.1%}")

    if errors:
        print(f"  Errors: {errors[:5]}{'...' if len(errors) > 5 else ''}")

    print(f"  Cache saved: {SNAPSHOT_CACHE}")
    return all_results


# ============================================================================
# PHASE 2: FINRA Historical Short Interest
# ============================================================================

def phase2_finra_historical(tickers: list = None):
    """Download historical short interest from FINRA API.

    FINRA publishes short interest data bi-monthly (mid-month and end-of-month).
    Free API access, CSV/JSON format. Data available from 2019 onwards.

    Endpoint: POST https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest

    Note: FINRA API requires specific query format and may have rate limits.
    This phase collects what's freely available and augments with RegSHO daily volume.
    """
    try:
        import requests
    except ImportError:
        print("[ERROR] requests not installed: pip install requests --break-system-packages")
        return {}

    if tickers is None:
        tickers = _load_bifrost_tickers()[:50]  # Start with subset

    print(f"\n{'='*60}")
    print(f"  PHASE 2: FINRA Historical Short Interest")
    print(f"  {len(tickers)} tickers to query")
    print(f"{'='*60}")

    # Load existing cache
    cache = {}
    if HISTORICAL_CACHE.exists():
        with open(HISTORICAL_CACHE) as f:
            cache = json.load(f)

    results = {}
    errors = []

    for i, ticker in enumerate(tickers):
        if ticker in cache and len(cache[ticker].get("records", [])) > 0:
            results[ticker] = cache[ticker]
            continue

        try:
            # FINRA consolidated short interest query
            # POST with filter on symbolCode
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Query for this ticker's short interest history
            payload = {
                "fields": ["symbolCode", "currentShortPositionQuantity",
                          "previousShortPositionQuantity", "changePreviousNumber",
                          "changePercent", "averageDailyVolumeQuantity",
                          "daysToCoverQuantity", "settlementDate"],
                "compareFilters": [
                    {"fieldName": "symbolCode", "fieldValue": ticker, "compareType": "EQUAL"}
                ],
                "limit": 100,
                "sortFields": ["-settlementDate"],
            }

            resp = requests.post(FINRA_SHORT_INTEREST, json=payload, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                results[ticker] = {
                    "ticker": ticker,
                    "records": data if isinstance(data, list) else [],
                    "n_records": len(data) if isinstance(data, list) else 0,
                    "fetch_date": datetime.now().strftime("%Y-%m-%d"),
                }
                if (i + 1) % 10 == 0:
                    n = results[ticker]["n_records"]
                    print(f"  [{i+1}/{len(tickers)}] {ticker}: {n} historical records")
            else:
                errors.append((ticker, f"HTTP {resp.status_code}"))
                results[ticker] = {"ticker": ticker, "records": [], "error": f"HTTP {resp.status_code}"}

        except Exception as e:
            errors.append((ticker, str(e)))
            results[ticker] = {"ticker": ticker, "records": [], "error": str(e)}

        time.sleep(FINRA_DELAY)

    # Save
    all_results = {**cache, **results}
    with open(HISTORICAL_CACHE, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    valid = [r for r in results.values() if r.get("n_records", 0) > 0]
    print(f"\n  Results: {len(valid)} with data / {len(errors)} errors")
    print(f"  Cache saved: {HISTORICAL_CACHE}")
    return all_results


# ============================================================================
# PHASE 2B: FINRA RegSHO Daily Short Sale Volume (Fallback)
# ============================================================================

def phase2b_regsho_daily(tickers: list = None, lookback_days: int = 30):
    """Download daily short sale volume from FINRA RegSHO reports.

    RegSHO tracks DAILY short sale volume (not total short interest position).
    Useful as a proxy for short selling pressure when bi-monthly SI is stale.

    Free: https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt
    """
    try:
        import requests
    except ImportError:
        print("[ERROR] requests not installed")
        return {}

    print(f"\n{'='*60}")
    print(f"  PHASE 2B: FINRA RegSHO Daily Short Volume")
    print(f"  Lookback: {lookback_days} days")
    print(f"{'='*60}")

    if tickers is None:
        tickers = set(_load_bifrost_tickers()[:100])
    else:
        tickers = set(tickers)

    results = defaultdict(list)

    today = datetime.now()
    for day_offset in range(lookback_days):
        date = today - timedelta(days=day_offset)
        if date.weekday() >= 5:  # Skip weekends
            continue

        date_str = date.strftime("%Y%m%d")
        url = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date_str}.txt"

        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                for line in lines[1:]:  # Skip header
                    parts = line.strip().split("|")
                    if len(parts) >= 5:
                        symbol = parts[1].strip()
                        if symbol in tickers:
                            results[symbol].append({
                                "date": date.strftime("%Y-%m-%d"),
                                "short_volume": int(parts[2]) if parts[2].strip() else 0,
                                "short_exempt_volume": int(parts[3]) if parts[3].strip() else 0,
                                "total_volume": int(parts[4]) if parts[4].strip() else 0,
                            })
                print(f"  {date_str}: loaded ({len(lines)-1} rows)")
            else:
                pass  # Weekend/holiday — no file
        except Exception as e:
            pass  # Skip failed days

        time.sleep(0.2)

    # Compute short volume ratio for each ticker
    summary = {}
    for ticker in tickers:
        records = results.get(ticker, [])
        if records:
            total_short = sum(r["short_volume"] for r in records)
            total_vol = sum(r["total_volume"] for r in records)
            summary[ticker] = {
                "ticker": ticker,
                "n_days": len(records),
                "avg_short_volume_ratio": total_short / total_vol if total_vol > 0 else 0,
                "total_short_volume": total_short,
                "total_volume": total_vol,
                "records": records,
            }

    # Save
    with open(FINRA_DAILY_CACHE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Tickers with data: {len(summary)}")
    if summary:
        ratios = [s["avg_short_volume_ratio"] for s in summary.values() if s["avg_short_volume_ratio"] > 0]
        if ratios:
            print(f"  Short volume ratio: mean={sum(ratios)/len(ratios):.1%}, max={max(ratios):.1%}")
    print(f"  Cache saved: {FINRA_DAILY_CACHE}")
    return summary


# ============================================================================
# PHASE 3: Feature Engineering
# ============================================================================

def phase3_engineer_features():
    """Engineer v5.1 candidate features from collected short interest data.

    Target features (8 candidates):
      1. pct_float_short: % of float sold short (raw)
      2. days_to_cover: shares_short / avg_daily_volume
      3. short_change_pct: change in SI from previous reporting period
      4. log_float_inv: log(1/float_shares) — smaller float = more explosive
      5. float_turnover: avg_volume / float — high = actively traded
      6. surprise_x_short: (1 - odin_score) * pct_float_short — HOLY GRAIL
      7. short_x_micro: pct_float_short * is_micro — short + small = squeeze
      8. short_vol_ratio: daily short volume / total volume (RegSHO)
    """
    print(f"\n{'='*60}")
    print(f"  PHASE 3: v5.1 Feature Engineering")
    print(f"{'='*60}")

    # Load snapshot data
    if not SNAPSHOT_CACHE.exists():
        print("  [ERROR] No snapshot cache. Run --snapshot first.")
        return {}

    with open(SNAPSHOT_CACHE) as f:
        snapshot = json.load(f)

    # Load BIFROST training data for merge
    bifrost_path = CACHE_DIR / "pdufa_runup_bifrost.csv"
    if not bifrost_path.exists():
        print(f"  [ERROR] BIFROST training data not found: {bifrost_path}")
        return {}

    import csv
    with open(bifrost_path) as f:
        reader = csv.DictReader(f)
        bifrost_rows = list(reader)

    print(f"  Snapshot: {len(snapshot)} tickers")
    print(f"  BIFROST training: {len(bifrost_rows)} events")

    # Load daily short volume if available
    daily_short = {}
    if FINRA_DAILY_CACHE.exists():
        with open(FINRA_DAILY_CACHE) as f:
            daily_short = json.load(f)

    # Engineer features for each BIFROST event
    features = []
    matched = 0

    for row in bifrost_rows:
        ticker = row.get("ticker", "").upper()
        si = snapshot.get(ticker, {})

        if "error" in si or si.get("shares_short", 0) == 0:
            # No SI data — use defaults (will be imputed later)
            feat = {
                "ticker": ticker,
                "pdufa_date": row.get("pdufa_date", ""),
                "pct_float_short": 0.0,
                "days_to_cover": 0.0,
                "short_change_pct": 0.0,
                "log_float_inv": 0.0,
                "float_turnover": 0.0,
                "short_vol_ratio": 0.0,
                "has_si_data": False,
            }
        else:
            matched += 1
            pct_float_short = si.get("short_pct_float", 0)
            days_to_cover = si.get("short_ratio", 0)
            float_shares = si.get("float_shares", 0)
            avg_vol = si.get("avg_volume", 0)

            # log(1/float) — smaller float = bigger value = more explosive
            log_float_inv = math.log(1e9 / max(float_shares, 1)) if float_shares > 0 else 0

            # Float turnover
            float_turnover = avg_vol / float_shares if float_shares > 0 else 0

            # Daily short volume ratio
            ds = daily_short.get(ticker, {})
            short_vol_ratio = ds.get("avg_short_volume_ratio", 0)

            feat = {
                "ticker": ticker,
                "pdufa_date": row.get("pdufa_date", ""),
                "pct_float_short": round(pct_float_short, 4),
                "days_to_cover": round(days_to_cover, 2),
                "short_change_pct": 0.0,  # Requires historical data (Phase 2)
                "log_float_inv": round(log_float_inv, 4),
                "float_turnover": round(float_turnover, 6),
                "short_vol_ratio": round(short_vol_ratio, 4),
                "has_si_data": True,
            }

        features.append(feat)

    # Save
    with open(V51_FEATURES_CACHE, "w") as f:
        json.dump(features, f, indent=2)

    coverage = matched / len(bifrost_rows) * 100 if bifrost_rows else 0
    print(f"\n  Matched: {matched}/{len(bifrost_rows)} events ({coverage:.1f}% coverage)")
    print(f"  Features per event: 6 + 2 interaction candidates")

    if matched > 0:
        si_vals = [f["pct_float_short"] for f in features if f["has_si_data"] and f["pct_float_short"] > 0]
        dtc_vals = [f["days_to_cover"] for f in features if f["has_si_data"] and f["days_to_cover"] > 0]
        if si_vals:
            print(f"  Short Interest: mean={sum(si_vals)/len(si_vals):.1%}, "
                  f"median={sorted(si_vals)[len(si_vals)//2]:.1%}, "
                  f"max={max(si_vals):.1%}")
        if dtc_vals:
            print(f"  Days to Cover: mean={sum(dtc_vals)/len(dtc_vals):.1f}, "
                  f"median={sorted(dtc_vals)[len(dtc_vals)//2]:.1f}, "
                  f"max={max(dtc_vals):.1f}")

    print(f"  Features saved: {V51_FEATURES_CACHE}")

    # Preview interaction features that will be computed at training time
    print(f"\n  v5.1 Interaction Feature Candidates (computed at training time):")
    print(f"    surprise_x_short = (1 - odin_score) * pct_float_short")
    print(f"    short_x_micro    = pct_float_short * is_micro")
    print(f"    short_x_penny    = pct_float_short * is_penny")
    print(f"    dtc_x_surprise   = days_to_cover * (1 - odin_score)")
    print(f"    float_x_surprise = log_float_inv * (1 - odin_score)")
    print(f"    squeeze_signal   = pct_float_short * is_micro * (1 - odin_score)")
    print(f"    ^^^ THIS is the holy grail: surprise × short × small float")

    return features


# ============================================================================
# UTILITIES
# ============================================================================

def _load_bifrost_tickers():
    """Load unique tickers from BIFROST training data."""
    bifrost_path = CACHE_DIR / "pdufa_runup_bifrost.csv"
    if not bifrost_path.exists():
        print(f"  [WARN] BIFROST data not found: {bifrost_path}")
        return []

    tickers = set()
    with open(bifrost_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row.get("ticker", "").upper().strip()
            if t and len(t) <= 5:
                tickers.add(t)
    return sorted(tickers)


def test_snapshot_small():
    """Test Phase 1 with a small set of current portfolio tickers."""
    print("\n" + "="*60)
    print("  TEST: Small Portfolio Snapshot")
    print("="*60)

    test_tickers = ["GRCE", "WHWK", "CRDF", "CABA", "ALXO"]
    results = phase1_yfinance_snapshot(test_tickers, force_refresh=True)

    for t in test_tickers:
        r = results.get(t, {})
        if "error" in r:
            print(f"  {t}: ERROR — {r['error']}")
        else:
            print(f"  {t}: SI={r.get('short_pct_float',0):.1%}  "
                  f"DTC={r.get('short_ratio',0):.1f}  "
                  f"Float={r.get('float_shares',0)/1e6:.1f}M  "
                  f"MCap={r.get('market_cap',0)/1e6:.0f}M  "
                  f"52wH=${r.get('fifty_two_week_high',0):.2f}")

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        phase1_yfinance_snapshot()
    elif "--historical" in sys.argv:
        phase2_finra_historical()
    elif "--regsho" in sys.argv:
        phase2b_regsho_daily()
    elif "--engineer" in sys.argv:
        phase3_engineer_features()
    elif "--test" in sys.argv:
        test_snapshot_small()
    elif "--all" in sys.argv:
        phase1_yfinance_snapshot()
        phase2_finra_historical()
        phase2b_regsho_daily()
        phase3_engineer_features()
    else:
        print("BIFROST v5.1 — Short Interest Data Pipeline")
        print("Usage:")
        print("  python bifrost_v51_short_interest.py --test        # Test with portfolio tickers")
        print("  python bifrost_v51_short_interest.py --snapshot    # Phase 1: yfinance snapshot (all training tickers)")
        print("  python bifrost_v51_short_interest.py --historical  # Phase 2: FINRA historical SI")
        print("  python bifrost_v51_short_interest.py --regsho      # Phase 2B: FINRA daily short volume")
        print("  python bifrost_v51_short_interest.py --engineer    # Phase 3: Feature engineering")
        print("  python bifrost_v51_short_interest.py --all         # Run all phases")
