#!/usr/bin/env python3
"""
================================================================================
GUNGNIR READOUT ANALYZER — Stock Move Classification & Feature Analysis
================================================================================

Combines Gungnir datasets, pulls actual stock prices around catalyst dates via
yfinance, computes post-readout returns, classifies events into:
  - BAD:   stock drops or flat (< +5%)
  - OKAY:  modest move (+5% to +15%)
  - GOOD:  strong move (+15% to +50%)
  - GREAT: monster move (+50%+)
  - CRASH: severe drop (<-30%)

Then analyzes which features predict each tier for actionable trading strategy.

USAGE:
  python gungnir_readout_analyzer.py                # Full run
  python gungnir_readout_analyzer.py --skip-prices  # Use cached prices
"""

import csv, json, math, os, sys, time, re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
PRICE_CACHE = os.path.join(DATA_DIR, "readout_price_cache.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
REPORT_FILE = os.path.join(DATA_DIR, "gungnir_readout_report.txt")

# =============================================================================
# THERAPEUTIC AREA CLASSIFICATION (same as builder)
# =============================================================================
TA_PATTERNS = {
    "oncology": r"(?i)\b(cancer|tumor|tumour|carcinoma|lymphoma|leukemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|neoplasm|malignant|metasta|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|cholang|solid.tumor|hematolog)",
    "cns": r"(?i)\b(alzheimer|parkinson|multiple.sclerosis|epilepsy|seizure|migraine|depression|schizophren|bipolar|anxiety|PTSD|autism|ADHD|huntington|ALS|amyotrophic|dementia|neuropath|neurodegen|stroke|psycho|cognitive|CNS|brain)",
    "cardiovascular": r"(?i)\b(heart|cardiac|cardio|coronary|atrial|arrhythm|hypertens|myocard|aort|thrombo|embol|atheroscler|cholesterol|lipid|dyslipid|PAH|pulmonary.arterial|heart.failure|HFrEF|HFpEF)",
    "immunology": r"(?i)\b(rheumatoid|lupus|SLE|psoria|atopic|eczema|dermatit|crohn|colitis|IBD|inflammat.bowel|ankylosing|autoimmun|graft.vs.host|GVHD|allerg|asthma|COPD|IPF|vasculit)",
    "infectious": r"(?i)\b(HIV|AIDS|hepatitis|HBV|HCV|influenza|COVID|SARS|RSV|pneumonia|tuberculosis|malaria|herpes|HPV|bacteri|antibiotic|antiviral|sepsis|infection)",
    "rare_disease": r"(?i)\b(orphan|rare.disease|duchenne|DMD|SMA|spinal.muscular|cystic.fibrosis|hemophilia|sickle.cell|thalassemia|gaucher|fabry|pompe|amyloid|ATTR|lysosomal|mucopolysaccharid)",
    "metabolic": r"(?i)\b(diabetes|diabetic|insulin|HbA1c|GLP.?1|SGLT|obesity|obese|weight.loss|NASH|NAFLD|fatty.liver|metabolic|gout|osteopor|thyroid)",
    "ophthalmology": r"(?i)\b(eye|ocular|ophthalm|retina|macular|AMD|glaucoma|uveitis|diabetic.retin|dry.eye)",
}


def classify_ta(text):
    if not text:
        return "other"
    for ta, pattern in TA_PATTERNS.items():
        if re.search(pattern, text):
            return ta
    return "other"


def parse_phase(stage_str):
    """Extract phase number from Stage field."""
    if not stage_str:
        return None
    s = stage_str.upper()
    if "3" in s:
        return 3
    if "2" in s:
        return 2
    if "1" in s:
        return 1
    return None


# =============================================================================
# STOCK PRICE FETCHING
# =============================================================================

def fetch_prices_batch(events, cache):
    """
    Fetch stock prices for all events using yfinance.
    For each event, we need:
      - close on D-1 (day before catalyst)
      - close on D (catalyst date)
      - close on D+1, D+2, D+5 (next trading days)

    We batch by ticker to minimize API calls.
    """
    import yfinance as yf

    # Group events by ticker
    ticker_events = defaultdict(list)
    for ev in events:
        ticker = ev["ticker"]
        date_str = ev["date"]
        cache_key = f"{ticker}|{date_str}"
        if cache_key not in cache:
            ticker_events[ticker].append(ev)

    already_cached = len(events) - sum(len(v) for v in ticker_events.values())
    print(f"[PRICES] {already_cached} already cached, {sum(len(v) for v in ticker_events.values())} to fetch across {len(ticker_events)} tickers")

    total_tickers = len(ticker_events)
    for i, (ticker, evs) in enumerate(ticker_events.items()):
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{total_tickers}] Processing {ticker}...")

        # Find date range needed for this ticker
        all_dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in evs]
        min_date = min(all_dates) - timedelta(days=10)
        max_date = max(all_dates) + timedelta(days=15)

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=min_date.strftime("%Y-%m-%d"),
                               end=max_date.strftime("%Y-%m-%d"),
                               auto_adjust=True)

            if hist.empty:
                # Try with common suffixes for delisted/changed tickers
                for ev in evs:
                    cache_key = f"{ticker}|{ev['date']}"
                    cache[cache_key] = {"error": "no_data"}
                continue

            # Convert index to date strings for lookup
            hist.index = hist.index.tz_localize(None)
            price_dates = sorted(hist.index.tolist())

            for ev in evs:
                cache_key = f"{ticker}|{ev['date']}"
                d = datetime.strptime(ev["date"], "%Y-%m-%d")

                # Find D-1, D, D+1, D+2, D+5 (nearest trading days)
                prices = {}
                for offset_name, target in [
                    ("d_minus_1", d - timedelta(days=1)),
                    ("d_0", d),
                    ("d_plus_1", d + timedelta(days=1)),
                    ("d_plus_2", d + timedelta(days=2)),
                    ("d_plus_5", d + timedelta(days=5)),
                ]:
                    # Find closest trading day
                    best = None
                    best_dist = 999
                    for pd_date in price_dates:
                        dist = abs((pd_date - target).days)
                        if dist < best_dist:
                            if offset_name.startswith("d_minus") and pd_date <= target:
                                best = pd_date
                                best_dist = dist
                            elif offset_name.startswith("d_plus") and pd_date >= target:
                                best = pd_date
                                best_dist = dist
                            elif offset_name == "d_0":
                                # For D itself, take closest
                                if dist <= 3:
                                    best = pd_date
                                    best_dist = dist

                    if best is not None and best in hist.index:
                        prices[offset_name] = float(hist.loc[best, "Close"])
                    else:
                        prices[offset_name] = None

                cache[cache_key] = prices

        except Exception as e:
            for ev in evs:
                cache_key = f"{ticker}|{ev['date']}"
                cache[cache_key] = {"error": str(e)}

        # Rate limit
        if (i + 1) % 20 == 0:
            time.sleep(0.5)

    return cache


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-prices", action="store_true")
    args = parser.parse_args()

    print("=" * 80)
    print("GUNGNIR READOUT ANALYZER — Stock Move Classification")
    print("=" * 80)

    # Step 1: Load and combine datasets
    events = []
    for fpath in [ENRICHED_CSV, HISTORICAL_CSV]:
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                ticker = r.get("Ticker", "").strip()
                date_str = r.get("date", r.get("Catalyst Date", "")).strip()
                if not ticker or not date_str:
                    continue
                events.append({
                    "ticker": ticker,
                    "name": r.get("Name", ""),
                    "drug": r.get("Drug", ""),
                    "indication": r.get("Indication", ""),
                    "stage": r.get("Stage", ""),
                    "date": date_str,
                    "catalyst_text": r.get("Catalyst", ""),
                    "outcome": r.get("outcome", ""),
                    "price_at_catalyst": r.get("Price At Catalyst Date", ""),
                })

    # Dedup by ticker+date
    seen = set()
    unique_events = []
    for ev in events:
        key = f"{ev['ticker']}|{ev['date']}"
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)
    events = unique_events
    print(f"\n[DATA] {len(events)} unique events loaded ({len(seen)} after dedup)")

    # Step 2: Load/fetch prices
    cache = {}
    if os.path.exists(PRICE_CACHE):
        with open(PRICE_CACHE, "r") as f:
            cache = json.load(f)
        print(f"[CACHE] Loaded {len(cache)} cached price entries")

    if not args.skip_prices:
        print(f"\n[FETCH] Pulling stock prices via yfinance...")
        cache = fetch_prices_batch(events, cache)
        with open(PRICE_CACHE, "w") as f:
            json.dump(cache, f)
        print(f"[CACHE] Saved {len(cache)} price entries")
    else:
        print(f"[SKIP] Using cached prices only")

    # Step 3: Compute returns and classify
    print(f"\n[ANALYZE] Computing returns and classifying...")

    rows = []
    for ev in events:
        cache_key = f"{ev['ticker']}|{ev['date']}"
        prices = cache.get(cache_key, {})

        if "error" in prices or not prices:
            continue

        # Compute 1-day return: D+1 close / D-1 close - 1
        # This captures the full catalyst move (pre-market, intraday, after-hours)
        d_minus_1 = prices.get("d_minus_1")
        d_0 = prices.get("d_0")
        d_plus_1 = prices.get("d_plus_1")
        d_plus_2 = prices.get("d_plus_2")
        d_plus_5 = prices.get("d_plus_5")

        if not d_minus_1 or d_minus_1 <= 0:
            continue

        # Primary return: D+1 / D-1 - 1 (captures overnight + next day)
        ret_1d = (d_plus_1 / d_minus_1 - 1) if d_plus_1 else None
        ret_0d = (d_0 / d_minus_1 - 1) if d_0 else None
        ret_2d = (d_plus_2 / d_minus_1 - 1) if d_plus_2 else None
        ret_5d = (d_plus_5 / d_minus_1 - 1) if d_plus_5 else None

        # Use best available return (prefer D+1)
        primary_ret = ret_1d if ret_1d is not None else ret_0d

        if primary_ret is None:
            continue

        # Classify
        if primary_ret >= 0.50:
            tier = "GREAT"
        elif primary_ret >= 0.15:
            tier = "GOOD"
        elif primary_ret >= 0.05:
            tier = "OKAY"
        elif primary_ret >= -0.15:
            tier = "FLAT"
        elif primary_ret >= -0.30:
            tier = "BAD"
        else:
            tier = "CRASH"

        # Extract features
        phase = parse_phase(ev["stage"])
        ta = classify_ta(ev["indication"])
        cat_text = ev.get("catalyst_text", "").lower()

        # Catalyst type signals from text
        met_primary = 1 if re.search(r"met.*(primary|endpoint)", cat_text) else 0
        failed_primary = 1 if re.search(r"(did not meet|failed|miss|not meet).*(primary|endpoint)", cat_text) else 0
        stat_sig = 1 if re.search(r"statistic.*signif", cat_text) else 0
        topline = 1 if "topline" in cat_text else 0
        fda_approval = 1 if re.search(r"(fda|approved|approval|accept)", cat_text) else 0
        crl = 1 if re.search(r"(complete response letter|CRL|refuse)", cat_text) else 0
        breakthrough = 1 if "breakthrough" in cat_text else 0
        fast_track = 1 if "fast track" in cat_text else 0
        accelerated = 1 if "accelerated" in cat_text else 0

        # Price/market cap proxy
        pre_price = d_minus_1
        is_micro = 1 if pre_price < 5 else 0
        is_small = 1 if 5 <= pre_price < 20 else 0
        is_mid = 1 if 20 <= pre_price < 80 else 0
        is_large = 1 if pre_price >= 80 else 0
        log_price = math.log(max(pre_price, 0.01))

        rows.append({
            "ticker": ev["ticker"],
            "name": ev["name"],
            "drug": ev["drug"],
            "indication": ev["indication"],
            "stage": ev["stage"],
            "date": ev["date"],
            "outcome": ev["outcome"],
            "ta": ta,
            "phase": phase,
            "pre_price": round(pre_price, 2),
            "log_price": round(log_price, 3),
            "d0_price": round(d_0, 2) if d_0 else "",
            "d1_price": round(d_plus_1, 2) if d_plus_1 else "",
            "d5_price": round(d_plus_5, 2) if d_plus_5 else "",
            "ret_0d": round(ret_0d * 100, 2) if ret_0d is not None else "",
            "ret_1d": round(ret_1d * 100, 2) if ret_1d is not None else "",
            "ret_2d": round(ret_2d * 100, 2) if ret_2d is not None else "",
            "ret_5d": round(ret_5d * 100, 2) if ret_5d is not None else "",
            "primary_ret_pct": round(primary_ret * 100, 2),
            "tier": tier,
            "met_primary": met_primary,
            "failed_primary": failed_primary,
            "stat_sig": stat_sig,
            "topline": topline,
            "fda_approval": fda_approval,
            "crl": crl,
            "breakthrough": breakthrough,
            "is_micro": is_micro,
            "is_small": is_small,
            "is_mid": is_mid,
            "is_large": is_large,
            "is_positive_outcome": 1 if ev["outcome"] == "positive" else 0,
            "is_negative_outcome": 1 if ev["outcome"] == "negative" else 0,
        })

    print(f"[RESULTS] {len(rows)} events with valid price data")

    # Write output
    if rows:
        fieldnames = list(rows[0].keys())
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[OUTPUT] Written to {OUTPUT_CSV}")

    # =========================================================================
    # DEEP ANALYSIS
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEEP ANALYSIS — WHAT MAKES MONEY?")
    print("=" * 80)

    report_lines = []
    def rprint(s=""):
        print(s)
        report_lines.append(s)

    n = len(rows)
    returns = [r["primary_ret_pct"] for r in rows]
    returns.sort()

    rprint(f"\n{'='*80}")
    rprint(f"GUNGNIR READOUT STOCK MOVE ANALYSIS — {n} Events")
    rprint(f"{'='*80}")

    # --- TIER DISTRIBUTION ---
    rprint(f"\n--- TIER DISTRIBUTION ---")
    tier_counts = Counter(r["tier"] for r in rows)
    tier_order = ["CRASH", "BAD", "FLAT", "OKAY", "GOOD", "GREAT"]
    for t in tier_order:
        cnt = tier_counts.get(t, 0)
        avg_ret = sum(r["primary_ret_pct"] for r in rows if r["tier"] == t) / max(cnt, 1)
        med_vals = sorted(r["primary_ret_pct"] for r in rows if r["tier"] == t)
        median_ret = med_vals[len(med_vals)//2] if med_vals else 0
        rprint(f"  {t:6s}: {cnt:4d} ({100*cnt/n:5.1f}%)  avg={avg_ret:+7.1f}%  median={median_ret:+7.1f}%")

    # --- OVERALL STATS ---
    rprint(f"\n--- OVERALL RETURN STATS ---")
    avg_all = sum(returns) / n
    med_all = returns[n // 2]
    pos_pct = 100 * sum(1 for r in returns if r > 0) / n
    rprint(f"  Mean return:   {avg_all:+.2f}%")
    rprint(f"  Median return: {med_all:+.2f}%")
    rprint(f"  Positive rate: {pos_pct:.1f}%")
    rprint(f"  Std dev:       {(sum((r - avg_all)**2 for r in returns) / n)**0.5:.2f}%")
    rprint(f"  Range:         {min(returns):+.1f}% to {max(returns):+.1f}%")

    # --- BY OUTCOME ---
    rprint(f"\n--- BY OUTCOME (positive vs negative) ---")
    for outcome in ["positive", "negative"]:
        subset = [r for r in rows if r["outcome"] == outcome]
        if not subset:
            continue
        rets = [r["primary_ret_pct"] for r in subset]
        rets.sort()
        avg = sum(rets) / len(rets)
        med = rets[len(rets)//2]
        rprint(f"  {outcome.upper():10s} (n={len(subset):4d}): avg={avg:+7.2f}%  median={med:+7.2f}%")
        for t in tier_order:
            tc = sum(1 for r in subset if r["tier"] == t)
            if tc > 0:
                rprint(f"    {t}: {tc} ({100*tc/len(subset):.1f}%)")

    # --- BY PHASE ---
    rprint(f"\n--- BY PHASE ---")
    for phase in [1, 2, 3]:
        subset = [r for r in rows if r["phase"] == phase]
        if not subset:
            continue
        rets = [r["primary_ret_pct"] for r in subset]
        rets.sort()
        avg = sum(rets) / len(rets)
        med = rets[len(rets)//2]
        good_rate = 100 * sum(1 for r in subset if r["tier"] in ["GOOD", "GREAT"]) / len(subset)
        crash_rate = 100 * sum(1 for r in subset if r["tier"] in ["CRASH", "BAD"]) / len(subset)
        rprint(f"  Phase {phase} (n={len(subset):4d}): avg={avg:+7.2f}%  median={med:+7.2f}%  GOOD+GREAT={good_rate:.1f}%  BAD+CRASH={crash_rate:.1f}%")

    # --- BY PHASE + OUTCOME (the money matrix) ---
    rprint(f"\n--- PHASE x OUTCOME MATRIX (avg return) ---")
    rprint(f"  {'':15s} {'Positive':>12s} {'Negative':>12s} {'Spread':>12s}")
    for phase in [1, 2, 3]:
        pos = [r["primary_ret_pct"] for r in rows if r["phase"] == phase and r["outcome"] == "positive"]
        neg = [r["primary_ret_pct"] for r in rows if r["phase"] == phase and r["outcome"] == "negative"]
        if pos and neg:
            pos_avg = sum(pos)/len(pos)
            neg_avg = sum(neg)/len(neg)
            rprint(f"  Phase {phase} (n={len(pos)+len(neg):4d}) {pos_avg:+11.2f}% {neg_avg:+11.2f}% {pos_avg-neg_avg:+11.2f}%")

    # --- BY TA ---
    rprint(f"\n--- BY THERAPEUTIC AREA ---")
    ta_stats = []
    for ta in sorted(set(r["ta"] for r in rows)):
        subset = [r for r in rows if r["ta"] == ta]
        if len(subset) < 20:
            continue
        rets = [r["primary_ret_pct"] for r in subset]
        avg = sum(rets) / len(rets)
        good_rate = 100 * sum(1 for r in subset if r["tier"] in ["GOOD", "GREAT"]) / len(subset)
        crash_rate = 100 * sum(1 for r in subset if r["tier"] in ["CRASH", "BAD"]) / len(subset)
        ta_stats.append((ta, len(subset), avg, good_rate, crash_rate))

    ta_stats.sort(key=lambda x: -x[2])
    rprint(f"  {'TA':15s} {'N':>6s} {'AvgRet':>10s} {'GOOD+GREAT':>12s} {'BAD+CRASH':>12s}")
    for ta, cnt, avg, gr, cr in ta_stats:
        rprint(f"  {ta:15s} {cnt:6d} {avg:+9.2f}% {gr:11.1f}% {cr:11.1f}%")

    # --- BY PRICE TIER (size proxy) ---
    rprint(f"\n--- BY PRICE TIER (market cap proxy) ---")
    for label, field in [("Micro (<$5)", "is_micro"), ("Small ($5-20)", "is_small"),
                          ("Mid ($20-80)", "is_mid"), ("Large (>$80)", "is_large")]:
        subset = [r for r in rows if r[field] == 1]
        if not subset:
            continue
        rets = [r["primary_ret_pct"] for r in subset]
        avg = sum(rets) / len(rets)
        good_rate = 100 * sum(1 for r in subset if r["tier"] in ["GOOD", "GREAT"]) / len(subset)
        crash_rate = 100 * sum(1 for r in subset if r["tier"] in ["CRASH", "BAD"]) / len(subset)
        great_rate = 100 * sum(1 for r in subset if r["tier"] == "GREAT") / len(subset)
        rprint(f"  {label:18s} (n={len(subset):4d}): avg={avg:+7.2f}%  GOOD+GREAT={good_rate:5.1f}%  GREAT={great_rate:4.1f}%  BAD+CRASH={crash_rate:5.1f}%")

    # --- POSITIVE OUTCOME BREAKDOWNS ---
    rprint(f"\n--- WHAT MAKES A POSITIVE READOUT GREAT vs JUST OKAY? ---")
    pos_rows = [r for r in rows if r["outcome"] == "positive"]
    if pos_rows:
        rprint(f"  Among {len(pos_rows)} positive outcomes:")
        # Phase
        for phase in [1, 2, 3]:
            sub = [r for r in pos_rows if r["phase"] == phase]
            if not sub:
                continue
            great = sum(1 for r in sub if r["tier"] == "GREAT")
            good = sum(1 for r in sub if r["tier"] in ["GOOD", "GREAT"])
            avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
            rprint(f"    Phase {phase}: n={len(sub)}, avg={avg:+.1f}%, GREAT={100*great/len(sub):.1f}%, GOOD+={100*good/len(sub):.1f}%")

        # Size
        for label, field in [("Micro (<$5)", "is_micro"), ("Small ($5-20)", "is_small"),
                              ("Mid ($20-80)", "is_mid"), ("Large (>$80)", "is_large")]:
            sub = [r for r in pos_rows if r[field] == 1]
            if not sub:
                continue
            great = sum(1 for r in sub if r["tier"] == "GREAT")
            avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
            rprint(f"    {label:18s}: n={len(sub)}, avg={avg:+.1f}%, GREAT={100*great/len(sub):.1f}%")

        # TA
        rprint(f"\n  Positive outcomes by TA (sorted by avg return):")
        ta_pos = []
        for ta in sorted(set(r["ta"] for r in pos_rows)):
            sub = [r for r in pos_rows if r["ta"] == ta]
            if len(sub) < 10:
                continue
            avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
            great = 100 * sum(1 for r in sub if r["tier"] == "GREAT") / len(sub)
            ta_pos.append((ta, len(sub), avg, great))
        ta_pos.sort(key=lambda x: -x[2])
        for ta, cnt, avg, great in ta_pos:
            rprint(f"    {ta:15s}: n={cnt:4d}, avg={avg:+7.1f}%, GREAT={great:5.1f}%")

    # --- NEGATIVE OUTCOME SEVERITY ---
    rprint(f"\n--- WHAT MAKES A BAD READOUT CATASTROPHIC? ---")
    neg_rows = [r for r in rows if r["outcome"] == "negative"]
    if neg_rows:
        rprint(f"  Among {len(neg_rows)} negative outcomes:")
        for phase in [1, 2, 3]:
            sub = [r for r in neg_rows if r["phase"] == phase]
            if not sub:
                continue
            crash = sum(1 for r in sub if r["tier"] == "CRASH")
            avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
            rprint(f"    Phase {phase}: n={len(sub)}, avg={avg:+.1f}%, CRASH={100*crash/len(sub):.1f}%")

        for label, field in [("Micro (<$5)", "is_micro"), ("Small ($5-20)", "is_small"),
                              ("Mid ($20-80)", "is_mid"), ("Large (>$80)", "is_large")]:
            sub = [r for r in neg_rows if r[field] == 1]
            if not sub:
                continue
            crash = sum(1 for r in sub if r["tier"] == "CRASH")
            avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
            rprint(f"    {label:18s}: n={len(sub)}, avg={avg:+.1f}%, CRASH={100*crash/len(sub):.1f}%")

    # --- STATISTICAL SIGNIFICANCE SIGNAL ---
    rprint(f"\n--- TEXT SIGNALS IN CATALYST DESCRIPTION ---")
    for signal, field in [("Met primary endpoint", "met_primary"),
                           ("Failed primary endpoint", "failed_primary"),
                           ("Statistically significant", "stat_sig"),
                           ("Topline data", "topline"),
                           ("FDA approval", "fda_approval"),
                           ("CRL/Refuse", "crl")]:
        yes = [r for r in rows if r[field] == 1]
        no = [r for r in rows if r[field] == 0]
        if len(yes) < 5:
            continue
        avg_yes = sum(r["primary_ret_pct"] for r in yes) / len(yes)
        avg_no = sum(r["primary_ret_pct"] for r in no) / len(no) if no else 0
        great_yes = 100 * sum(1 for r in yes if r["tier"] in ["GOOD", "GREAT"]) / len(yes)
        rprint(f"  {signal:30s}: n={len(yes):4d}, avg={avg_yes:+7.1f}%  (vs {avg_no:+7.1f}% without)  GOOD+GREAT={great_yes:.1f}%")

    # --- COMBINATION SIGNALS (THE MONEY SPOTS) ---
    rprint(f"\n{'='*80}")
    rprint(f"MONEY SPOTS — HIGH-CONVICTION TRADE SETUPS")
    rprint(f"{'='*80}")

    setups = [
        ("Phase 3 + Positive + Micro", lambda r: r["phase"]==3 and r["outcome"]=="positive" and r["is_micro"]==1),
        ("Phase 3 + Positive + Small", lambda r: r["phase"]==3 and r["outcome"]=="positive" and r["is_small"]==1),
        ("Phase 3 + Positive + Mid", lambda r: r["phase"]==3 and r["outcome"]=="positive" and r["is_mid"]==1),
        ("Phase 3 + Positive + Large", lambda r: r["phase"]==3 and r["outcome"]=="positive" and r["is_large"]==1),
        ("Phase 2 + Positive + Micro", lambda r: r["phase"]==2 and r["outcome"]=="positive" and r["is_micro"]==1),
        ("Phase 2 + Positive + Small", lambda r: r["phase"]==2 and r["outcome"]=="positive" and r["is_small"]==1),
        ("Phase 3 + Negative + Micro", lambda r: r["phase"]==3 and r["outcome"]=="negative" and r["is_micro"]==1),
        ("Phase 3 + Negative + Small", lambda r: r["phase"]==3 and r["outcome"]=="negative" and r["is_small"]==1),
        ("Phase 3 + Negative + Mid", lambda r: r["phase"]==3 and r["outcome"]=="negative" and r["is_mid"]==1),
        ("Phase 3 + Negative + Large", lambda r: r["phase"]==3 and r["outcome"]=="negative" and r["is_large"]==1),
        ("Oncology + Phase 2 + Positive", lambda r: r["ta"]=="oncology" and r["phase"]==2 and r["outcome"]=="positive"),
        ("Oncology + Phase 3 + Positive", lambda r: r["ta"]=="oncology" and r["phase"]==3 and r["outcome"]=="positive"),
        ("Rare Disease + Positive", lambda r: r["ta"]=="rare_disease" and r["outcome"]=="positive"),
        ("CNS + Phase 3 + Positive", lambda r: r["ta"]=="cns" and r["phase"]==3 and r["outcome"]=="positive"),
        ("CNS + Phase 3 + Negative", lambda r: r["ta"]=="cns" and r["phase"]==3 and r["outcome"]=="negative"),
        ("Immunology + Phase 3 + Positive", lambda r: r["ta"]=="immunology" and r["phase"]==3 and r["outcome"]=="positive"),
        ("StatSig + Phase 3 + Micro/Small", lambda r: r["stat_sig"]==1 and r["phase"]==3 and (r["is_micro"]==1 or r["is_small"]==1)),
        ("Met Primary + Phase 3", lambda r: r["met_primary"]==1 and r["phase"]==3),
        ("Failed Primary + Phase 3", lambda r: r["failed_primary"]==1 and r["phase"]==3),
    ]

    rprint(f"\n  {'Setup':45s} {'N':>5s} {'AvgRet':>9s} {'MedRet':>9s} {'GREAT%':>8s} {'GOOD+%':>8s} {'CRASH%':>8s}")
    rprint(f"  {'-'*45} {'-'*5} {'-'*9} {'-'*9} {'-'*8} {'-'*8} {'-'*8}")

    for label, filt in setups:
        sub = [r for r in rows if filt(r)]
        if len(sub) < 5:
            continue
        rets = sorted(r["primary_ret_pct"] for r in sub)
        avg = sum(rets) / len(rets)
        med = rets[len(rets)//2]
        great = 100 * sum(1 for r in sub if r["tier"] == "GREAT") / len(sub)
        good_plus = 100 * sum(1 for r in sub if r["tier"] in ["GOOD", "GREAT"]) / len(sub)
        crash = 100 * sum(1 for r in sub if r["tier"] == "CRASH") / len(sub)
        rprint(f"  {label:45s} {len(sub):5d} {avg:+8.1f}% {med:+8.1f}% {great:7.1f}% {good_plus:7.1f}% {crash:7.1f}%")

    # --- TOP 20 BEST AND WORST MOVES ---
    rprint(f"\n--- TOP 20 BIGGEST WINNERS ---")
    by_ret = sorted(rows, key=lambda r: -r["primary_ret_pct"])
    for r in by_ret[:20]:
        rprint(f"  {r['primary_ret_pct']:+7.1f}%  {r['ticker']:6s} Phase {r['phase']}  {r['ta']:12s}  ${r['pre_price']:>7.2f}  {r['drug'][:40]}")

    rprint(f"\n--- TOP 20 BIGGEST LOSERS ---")
    for r in by_ret[-20:]:
        rprint(f"  {r['primary_ret_pct']:+7.1f}%  {r['ticker']:6s} Phase {r['phase']}  {r['ta']:12s}  ${r['pre_price']:>7.2f}  {r['drug'][:40]}")

    # --- D+5 DRIFT ANALYSIS ---
    rprint(f"\n--- POST-EVENT DRIFT (D+1 to D+5) ---")
    rprint(f"  Does the move continue or reverse?")
    for tier in tier_order:
        sub = [r for r in rows if r["tier"] == tier and r["ret_1d"] and r["ret_5d"]]
        if len(sub) < 10:
            continue
        d1_avg = sum(float(r["ret_1d"]) for r in sub) / len(sub)
        d5_avg = sum(float(r["ret_5d"]) for r in sub) / len(sub)
        drift = d5_avg - d1_avg
        rprint(f"  {tier:6s} (n={len(sub):4d}): D+1 avg={d1_avg:+7.1f}%  D+5 avg={d5_avg:+7.1f}%  drift={drift:+6.1f}% {'(CONTINUES)' if (tier in ['GOOD','GREAT'] and drift > 0) or (tier in ['CRASH','BAD'] and drift < 0) else '(REVERSES)' if abs(drift) > 1 else '(FLAT)'}")

    # --- ASYMMETRY ANALYSIS ---
    rprint(f"\n--- ASYMMETRY: IS IT WORTH PLAYING? ---")
    rprint(f"  Expected value analysis for blind positions:")
    for phase in [1, 2, 3]:
        sub = [r for r in rows if r["phase"] == phase]
        if not sub:
            continue
        avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
        pos_rate = 100 * sum(1 for r in sub if r["outcome"] == "positive") / len(sub)
        avg_win = sum(r["primary_ret_pct"] for r in sub if r["primary_ret_pct"] > 0)
        avg_win = avg_win / max(sum(1 for r in sub if r["primary_ret_pct"] > 0), 1)
        avg_loss = sum(r["primary_ret_pct"] for r in sub if r["primary_ret_pct"] < 0)
        avg_loss = avg_loss / max(sum(1 for r in sub if r["primary_ret_pct"] < 0), 1)
        win_rate = sum(1 for r in sub if r["primary_ret_pct"] > 0) / len(sub)
        ev = win_rate * avg_win + (1 - win_rate) * avg_loss
        rprint(f"  Phase {phase}: n={len(sub)}, win_rate={100*win_rate:.1f}%, avg_win={avg_win:+.1f}%, avg_loss={avg_loss:+.1f}%, EV={ev:+.2f}%")

    # --- YEAR-OVER-YEAR ---
    rprint(f"\n--- YEAR OVER YEAR ---")
    for yr in sorted(set(r["date"][:4] for r in rows)):
        sub = [r for r in rows if r["date"].startswith(yr)]
        avg = sum(r["primary_ret_pct"] for r in sub) / len(sub)
        pos = 100 * sum(1 for r in sub if r["outcome"] == "positive") / len(sub)
        rprint(f"  {yr}: n={len(sub):4d}, avg_return={avg:+6.1f}%, positive_rate={pos:.1f}%")

    # Save report
    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\n[REPORT] Full analysis saved to {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
