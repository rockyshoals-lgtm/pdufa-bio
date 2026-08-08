#!/usr/bin/env python3
"""
RUNNER -- SELF-CONTAINED Phase Readout Scanner v1.1.1
2026-05-28 patch: surfaces FMP errors instead of swallowing, auto-tries 3 endpoint variants.

Drop-in replacement: copy this file to C:\\Users\\dcmoo\\Documents\\Python\\9realms\\runner.py

USAGE
-----
python runner.py                # full scan with FMP fetch
python runner.py --dry-run      # skip FMP, curated calendar only
python runner.py --max-tickers 10
python runner.py --debug-fmp    # print full response from first FMP call
"""

import os
import json
import csv
import re
import time
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATE_DATA_DIRS = [
    HERE,
    HERE / "Odin Perfection",
    HERE.parent / "Odin Perfection",
    Path("C:/Users/dcmoo/Documents/Python/9realms/Odin Perfection"),
]

def find_data_file(filename: str):
    for d in CANDIDATE_DATA_DIRS:
        p = d / filename
        if p.exists():
            return p
    return None

CACHE_DIR = HERE / "phase_readout_cache"
CACHE_DIR.mkdir(exist_ok=True)

def load_universe():
    universe_csv = find_data_file("phase_readout_universe_2026-05-26.csv")
    universe = {}
    if universe_csv and universe_csv.exists():
        with open(universe_csv) as f:
            for row in csv.DictReader(f):
                try:
                    universe[row['ticker']] = {'mcap_M': float(row['mcap_M']), 'bucket': row['bucket']}
                except Exception:
                    continue
        print(f"  Loaded universe from {universe_csv}")
    additions = {
        'CRBP': {'mcap_M': 99.2, 'bucket': 'micro'}, 'BDTX': {'mcap_M': 133.5, 'bucket': 'micro'},
        'OTLK': {'mcap_M': 58.4, 'bucket': 'micro'}, 'CRDF': {'mcap_M': 131.0, 'bucket': 'micro'},
        'IRON': {'mcap_M': 1200.0, 'bucket': 'small'}, 'IDYA': {'mcap_M': 1400.0, 'bucket': 'small'},
        'CABA': {'mcap_M': 240.0, 'bucket': 'micro'}, 'MIRM': {'mcap_M': 1900.0, 'bucket': 'small'},
        'LEGN': {'mcap_M': 5800.0, 'bucket': 'mid'}, 'NMRA': {'mcap_M': 850.0, 'bucket': 'small'},
        'TSHA': {'mcap_M': 450.0, 'bucket': 'small'}, 'VRDN': {'mcap_M': 1700.0, 'bucket': 'small'},
        'NUVL': {'mcap_M': 1900.0, 'bucket': 'small'}, 'VERA': {'mcap_M': 1400.0, 'bucket': 'small'},
        'ARQT': {'mcap_M': 1500.0, 'bucket': 'small'}, 'MNKD': {'mcap_M': 1800.0, 'bucket': 'small'},
        'AVBP': {'mcap_M': 950.0, 'bucket': 'small'}, 'KURA': {'mcap_M': 770.4, 'bucket': 'small'},
    }
    for t, info in additions.items():
        if t not in universe:
            universe[t] = info
    return universe

BUCKET_WEIGHTS = {'nano': 0.5, 'micro': 1.0, 'small': 0.7, 'mid': 0.3, 'large': 0.0}
DIRECTION_MULTIPLIERS = {'positive_squeeze': 1.2, 'positive_confirmed': 0.4, 'muted_positive': 0.6,
    'muted_positive_or_sell': 0.9, 'uncertain': 0.5, 'negative': -0.8}

CATALYST_KEYWORDS = [
    "topline", "interim data", "phase 2 data", "phase 3 data", "primary endpoint",
    "updated results", "extended follow-up", "fda decision", "pdufa", "fda appeal",
    "complete response", "approval", "snda", "bla acceptance", "nda acceptance",
    "advisory committee", "adcom", "asco", "esmo", "aacr", "ash", "eular", "aha", "aan",
    "abstract", "oral presentation", "rapid oral", "late-breaking", "lba",
    "poster presentation", "plenary", "topline results", "trial readout", "data update",
    "clinical readout", "last patient last visit", "lplv", "first patient dosed",
]
NEGATIVE_KEYWORDS = ["crl", "complete response letter", "delay", "additional information",
    "voluntary withdrawal", "discontinue", "clinical hold", "going concern",
    "form 483", "cmc observations"]

def score_event(event, universe):
    ticker = event['ticker']
    if ticker not in universe: return None
    bucket = universe[ticker]['bucket']
    bucket_w = BUCKET_WEIGHTS.get(bucket, 0)
    direction_w = DIRECTION_MULTIPLIERS.get(event.get('expected_direction', 'uncertain'), 0.5)
    try:
        event_dt = datetime.strptime(event['date'], '%Y-%m-%d').date()
        days_to = (event_dt - datetime.now().date()).days
        if days_to < -5: return None
        urgency = max(0, 1.0 - abs(days_to) / 30.0)
    except Exception:
        urgency = 0.5
    return round(100 * bucket_w * abs(direction_w) * urgency, 1)

def get_action(event, score):
    if score is None or score == 0: return "OUT_OF_SCOPE"
    direction = event.get('expected_direction', 'uncertain')
    if direction in ('positive_squeeze', 'positive_confirmed', 'muted_positive', 'muted_positive_or_sell'):
        return "WATCH_FOR_SELL_THE_NEWS_FLIP" if score >= 50 else "MONITOR"
    if direction == 'negative': return "POTENTIAL_SHORT_CANDIDATE"
    return "MONITOR_PRE_EVENT_VOL"

CONFERENCE_CALENDAR_2026 = [
    {"ticker": "KURA", "date": "2026-05-26", "conference": "ASCO 2026 (pre-release)",
     "drug": "darlifarnib + adagrasib", "indication": "KRAS G12C solid tumors",
     "expected_direction": "muted_positive_or_sell", "notes": "Released May 26; -7.47%"},
    {"ticker": "CRBP", "date": "2026-05-26", "conference": "ASCO 2026 (pre-release)",
     "drug": "CRB-701 (Nectin-4 ADC)", "indication": "HNSCC + cervical",
     "expected_direction": "negative", "notes": "Released May 26; -30.31%"},
    {"ticker": "BDTX", "date": "2026-05-21", "conference": "ASCO 2026 (pre-release)",
     "drug": "silevertinib", "indication": "EGFR-NCM NSCLC",
     "expected_direction": "muted_positive", "notes": "15.2-mo mPFS, 60% ORR; muted"},
    {"ticker": "IDYA", "date": "2026-06-01", "conference": "ASCO 2026 LBA",
     "drug": "Darovasertib + crizotinib", "indication": "1L HLA-A2-neg uveal melanoma",
     "expected_direction": "muted_positive_or_sell", "notes": "Primary endpoint MET"},
    {"ticker": "CRDF", "date": "2026-06-02", "conference": "ASCO 2026 rapid oral",
     "drug": "Onvansertib + FOLFIRI/bev", "indication": "1L RAS-mutated mCRC",
     "expected_direction": "positive_squeeze", "notes": "Phase 2 CRDF-004; webcast Jun 3"},
    {"ticker": "IRON", "date": "2026-06-02", "conference": "ASCO 2026 oral",
     "drug": "DISC-0974", "indication": "Anemia in myelofibrosis",
     "expected_direction": "uncertain", "notes": "Phase 2 RALLY-MF"},
    {"ticker": "LEGN", "date": "2026-05-31", "conference": "ASCO 2026 rapid oral",
     "drug": "LB2102 (DLL3 CAR-T)", "indication": "R/R SCLC",
     "expected_direction": "uncertain", "notes": "First DLL3 CAR-T data"},
    {"ticker": "CABA", "date": "2026-06-04", "conference": "EULAR 2026 oral",
     "drug": "rese-cel", "indication": "RESET-SLE Phase 1/2 + RESET-SSc",
     "expected_direction": "uncertain", "notes": "POS0698. Existing position."},
    {"ticker": "MIRM", "date": "2026-05-30", "conference": "EASL late-breaker",
     "drug": "Volixibat", "indication": "PSC",
     "expected_direction": "positive_confirmed", "notes": "May 4 topline already POSITIVE"},
]

def _load_dotenv():
    for d in [HERE] + list(HERE.parents)[:3]:
        p = d / ".env"
        if p.exists():
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
            return
_load_dotenv()
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

# ============================================================================
# FMP CLIENT v1.1.1 -- tries 3 endpoint variants, surfaces errors verbatim
# ============================================================================
FMP_ENDPOINTS = [
    # (url, param_name_for_ticker)
    # CONFIRMED WORKING 2026-05-28: /stable/news/stock with symbols=TICKER returns per-symbol filtered news.
    # /stable/news/stock-latest IGNORES symbol filter (returns market-wide) -- removed.
    # /api/v3/stock_news is LEGACY (HTTP 403 for post-Aug-2025 accounts) -- kept as last-resort fallback only.
    ("https://financialmodelingprep.com/stable/news/stock", "symbols"),
    ("https://financialmodelingprep.com/stable/news/press-releases", "symbols"),
    ("https://financialmodelingprep.com/api/v3/stock_news", "tickers"),
]

# Track which endpoint actually works -- discovered on first successful call
_WORKING_ENDPOINT = [None]
_FIRST_ERROR_PRINTED = [False]

def fmp_stock_news(ticker, limit=20, cache_hours=6.0, debug=False):
    cpath = CACHE_DIR / f"news_{ticker}_{limit}.json"
    if cpath.exists() and (time.time() - cpath.stat().st_mtime) / 3600.0 < cache_hours:
        try:
            return json.load(open(cpath))
        except Exception:
            pass
    if not FMP_API_KEY:
        return {"_error": "FMP_API_KEY missing"}
    try:
        import requests
    except ImportError:
        return {"_error": "requests missing"}

    # Try working endpoint first if known, else iterate
    endpoints_to_try = [_WORKING_ENDPOINT[0]] if _WORKING_ENDPOINT[0] else FMP_ENDPOINTS

    last_error = None
    for url, param_name in endpoints_to_try:
        try:
            params = {param_name: ticker, "limit": limit, "apikey": FMP_API_KEY}
            r = requests.get(url, params=params, timeout=15)
            if debug and not _FIRST_ERROR_PRINTED[0]:
                print(f"  DEBUG FMP: url={url} status={r.status_code} body={r.text[:300]}")
                _FIRST_ERROR_PRINTED[0] = True
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    _WORKING_ENDPOINT[0] = (url, param_name)
                    with open(cpath, 'w') as f:
                        json.dump(data, f)
                    return data
                else:
                    last_error = f"HTTP 200 but body is {type(data).__name__}: {str(data)[:120]}"
            elif r.status_code == 401:
                last_error = "HTTP 401 -- API key rejected"
                break  # don't try other endpoints
            elif r.status_code == 403:
                last_error = f"HTTP 403 -- endpoint requires higher subscription tier (tried {url})"
            elif r.status_code == 404:
                last_error = f"HTTP 404 -- endpoint not found ({url})"
            elif r.status_code == 429:
                last_error = "HTTP 429 -- rate limited"
                break
            else:
                last_error = f"HTTP {r.status_code} on {url}: {r.text[:120]}"
        except Exception as e:
            last_error = f"Exception on {url}: {str(e)[:120]}"
            continue

    return {"_error": last_error or "unknown FMP failure"}

DATE_REGEXES = [
    (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(2026|2027)', 'named'),
    (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(2026|2027)', 'named'),
    (r'(\d{1,2})/(\d{1,2})/(2026|2027)', 'numeric'),
    (r'(Q[1-4])\s+(2026|2027)', 'quarter'),
    (r'(1H|2H|H1|H2)\s*(2026|2027)', 'half'),
]
MONTH_MAP = {'january':1,'jan':1,'february':2,'feb':2,'march':3,'mar':3,'april':4,'apr':4,'may':5,
    'june':6,'jun':6,'july':7,'jul':7,'august':8,'aug':8,'september':9,'sep':9,
    'october':10,'oct':10,'november':11,'nov':11,'december':12,'dec':12}

def extract_event_date(text):
    if not text: return None
    for pat, kind in DATE_REGEXES:
        m = re.search(pat, text, re.IGNORECASE)
        if not m: continue
        try:
            if kind == 'named':
                return f"{int(m.group(3))}-{MONTH_MAP[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
            elif kind == 'numeric':
                return f"{int(m.group(3))}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
            elif kind == 'quarter':
                return f"{int(m.group(2))}-{ {'Q1':2,'Q2':5,'Q3':8,'Q4':11}[m.group(1).upper()] :02d}-15"
            elif kind == 'half':
                return f"{int(m.group(2))}-{ {'1H':3,'H1':3,'2H':9,'H2':9}[m.group(1).upper()] :02d}-15"
        except Exception:
            continue
    return None

def detect_catalyst_in_pr(pr_text, pr_date):
    text_lower = (pr_text or "").lower()
    matched = [k for k in CATALYST_KEYWORDS if k in text_lower]
    matched_neg = [k for k in NEGATIVE_KEYWORDS if k in text_lower]
    if not matched: return None
    event_date = extract_event_date(pr_text) or pr_date
    if any(k in text_lower for k in ('pdufa', 'fda decision', 'complete response')):
        event_type = 'PDUFA'
    elif any(k in text_lower for k in ('asco','esmo','aacr','ash','eular','abstract','oral','late-breaking')):
        event_type = 'CONFERENCE_READOUT'
    elif any(k in text_lower for k in ('topline','interim data','phase 2 data','phase 3 data','primary endpoint')):
        event_type = 'PHASE_READOUT'
    else:
        event_type = 'OTHER_CATALYST'
    if matched_neg: direction = 'negative'
    elif event_type in ('PHASE_READOUT','CONFERENCE_READOUT'): direction = 'muted_positive_or_sell'
    else: direction = 'uncertain'
    return {'event_date': event_date, 'event_type': event_type, 'matched_keywords': matched[:5],
            'matched_negatives': matched_neg, 'expected_direction': direction}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--limit', type=int, default=20)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--max-tickers', type=int, default=None)
    p.add_argument('--debug-fmp', action='store_true', help='Print full FMP response from first call')
    args = p.parse_args()

    print(f"PHASE READOUT SCANNER v1.1.1 -- {args.date}")
    print(f"Run dir: {HERE}")
    print(f"FMP_API_KEY: {'PRESENT' if FMP_API_KEY else 'MISSING (.env not found)'}")
    print("=" * 70)

    universe = load_universe()
    tickers = list(universe.keys())
    if args.max_tickers:
        tickers = tickers[:args.max_tickers]
    print(f"Universe: {len(tickers)} tickers")
    curated_keys = set((e['ticker'], e['date']) for e in CONFERENCE_CALENDAR_2026)
    print(f"Curated calendar: {len(curated_keys)} events")

    auto_events = []
    if not args.dry_run and FMP_API_KEY:
        print(f"Fetching PRs for {len(tickers)} tickers (cached 6h)...")
        cutoff = datetime.now() - timedelta(days=args.days)
        fetched = errors = 0
        first_error_msg = None
        for ticker in tickers:
            news = fmp_stock_news(ticker, limit=args.limit, debug=args.debug_fmp)
            if isinstance(news, dict) and "_error" in news:
                if first_error_msg is None:
                    first_error_msg = news["_error"]
                errors += 1
                continue
            if not isinstance(news, list):
                errors += 1
                continue
            fetched += 1
            for pr in news:
                try:
                    pub = pr.get('publishedDate', '')[:10]
                    if not pub: continue
                    if datetime.strptime(pub, '%Y-%m-%d') < cutoff: continue
                    det = detect_catalyst_in_pr((pr.get('title','') + ' ' + pr.get('text','')), pub)
                    if not det: continue
                    auto_events.append({
                        'ticker': ticker, 'date': det['event_date'] or pub, 'pr_published': pub,
                        'event_type': det['event_type'], 'expected_direction': det['expected_direction'],
                        'matched_keywords': '|'.join(det['matched_keywords']),
                        'matched_negatives': '|'.join(det['matched_negatives']),
                        'title': pr.get('title', '')[:120], 'url': pr.get('url', ''),
                        'auto_detected': True,
                        'is_new_vs_curated': (ticker, det['event_date']) not in curated_keys,
                    })
                except Exception:
                    continue
        print(f"  FMP fetches: {fetched} ok, {errors} errors. Auto-detected: {len(auto_events)}")
        if errors > 0 and first_error_msg:
            print(f"  FIRST ERROR: {first_error_msg}")
            print(f"  HINT: try `python runner.py --debug-fmp` to see the full first response.")
        if _WORKING_ENDPOINT[0]:
            print(f"  Working endpoint: {_WORKING_ENDPOINT[0][0]}")
    elif not FMP_API_KEY:
        print("  Skipping FMP fetch (no API key). Curated-only mode.")

    combined = []
    for ce in CONFERENCE_CALENDAR_2026:
        ec = dict(ce)
        ec['auto_detected'] = False
        ec['is_new_vs_curated'] = False
        s = score_event(ec, universe)
        if s is None: continue
        ec['scanner_score'] = s
        ec['mcap_bucket'] = universe[ec['ticker']]['bucket']
        ec['mcap_M'] = universe[ec['ticker']]['mcap_M']
        ec['action'] = get_action(ec, s)
        combined.append(ec)
    for ae in auto_events:
        s = score_event(ae, universe)
        if s is None: continue
        ae['scanner_score'] = s
        ae['mcap_bucket'] = universe[ae['ticker']]['bucket']
        ae['mcap_M'] = universe[ae['ticker']]['mcap_M']
        ae['action'] = get_action(ae, s)
        combined.append(ae)
    combined.sort(key=lambda x: -x.get('scanner_score', 0))
    new_only = [e for e in combined if e.get('is_new_vs_curated')]

    out_combined = HERE / f"phase_readout_calendar_{args.date}.csv"
    if combined:
        keys = sorted({k for e in combined for k in e.keys()})
        with open(out_combined, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            w.writeheader()
            for r in combined: w.writerow(r)
        print(f"\n  Wrote {len(combined)} events to {out_combined}")
    if new_only:
        out_new = HERE / f"phase_readout_new_events_{args.date}.csv"
        keys = sorted({k for e in new_only for k in e.keys()})
        with open(out_new, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            w.writeheader()
            for r in new_only: w.writerow(r)
        print(f"  Wrote {len(new_only)} NEW events to {out_new}")

    print(f"\n=== TOP 10 EVENTS BY SCORE ===")
    print(f"{'TICKER':<8} {'DATE':<12} {'BUCKET':<8} {'DIR':<25} {'SCORE':>7}  ACTION")
    print("-" * 100)
    for e in combined[:10]:
        print(f"{e['ticker']:<8} {e['date']:<12} {e['mcap_bucket']:<8} {e['expected_direction']:<25} {e['scanner_score']:>7.1f}  {e['action']}")
    print(f"\n=== SUMMARY ===")
    print(f"  Curated events: {sum(1 for e in combined if not e.get('auto_detected'))}")
    print(f"  Auto-detected: {sum(1 for e in combined if e.get('auto_detected'))}")
    print(f"  NEW events flagged: {len(new_only)}")
    print(f"  Total scored: {len(combined)}")

if __name__ == "__main__":
    main()
