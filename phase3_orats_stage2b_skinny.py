#!/usr/bin/env python3
"""
PHASE 3 STAGE 2B — SKINNY (API-conserving fork of Stage 2)

User directive Apr 20, 2026 22:31: "we are near API limit, scale back and get as
much as possible before we are cut off"

STRATEGY:
  - Stage 2 was killed at event 1300/1649 (14,300 total calls, ~9,617 new this run).
  - Events 1300-1649 (the last 349, mostly 2025-2026 = TEST set) have NO coverage.
  - Skinny fork pulls only T-14 snapshot with 2 most-critical endpoints per event:
      /hist/summaries  (IV surface: iv20d/30d/60d/90d, skew, contango, rVol30)
      /hist/strikes    (ATM IV + vol/OI aggregates for UOA-style features)
  - Per-event calls: 2 (vs 11 in full Stage 2) = 5.5x cheaper
  - 349 remaining × 2 = 698 max new calls (safe within any reasonable budget)

RESUME LOGIC:
  - Same cache directory as Stage 2 (orats_phase3_cache/)
  - Skinny checks both T-14 endpoints. If both cached, event is skipped.
  - START_EVENT_ID arg lets operator begin exactly where Stage 2 stopped.
  - Rate limit unchanged (0.65s sleep, ~92 calls/min).

USAGE:
  python3 phase3_orats_stage2b_skinny.py              # full remaining universe
  python3 phase3_orats_stage2b_skinny.py --start 1300 # start at event 1300
  python3 phase3_orats_stage2b_skinny.py --dry-run    # no API calls
"""
import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas.tseries.offsets import BDay

ORATS_BASE_URL = "https://api.orats.io/datav2"
ORATS_TOKEN = "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"

HERE = Path(__file__).parent
CACHE_DIR = HERE / "orats_phase3_cache"
CACHE_DIR.mkdir(exist_ok=True)
BIFROST_CSV = HERE / "pdufa_runup_bifrost.csv"
PROGRESS_OUT = HERE / "phase3_stage2b_progress.json"

PROBLEM_TICKERS = {"RHHBY", "BAYRY", "HOTH", "INTE", "TLX", "DERM"}

# SKINNY endpoint set — T-14 only, 2 endpoints
SKINNY_ENDPOINTS = ["/hist/summaries", "/hist/strikes"]
SNAP_LABEL = "T-14"

SLEEP_S = 0.65
TIMEOUT_S = 30

_ssl_ctx = ssl.create_default_context()
_last_call = [0.0]


def _rate_sleep():
    el = time.time() - _last_call[0]
    if el < SLEEP_S:
        time.sleep(SLEEP_S - el)
    _last_call[0] = time.time()


def _cache_path(ticker, trade_date, endpoint):
    safe = endpoint.replace("/", "_").strip("_")
    return CACHE_DIR / f"{ticker}_{trade_date}_{safe}.json"


def orats_get(endpoint, ticker, trade_date, dry_run=False):
    cp = _cache_path(ticker, trade_date, endpoint)
    if cp.exists():
        try:
            body = json.loads(cp.read_text())
            body["_cached"] = True
            return body
        except Exception:
            pass
    if dry_run:
        return {"_error": "DRY_RUN", "_cached": False}
    params = {"ticker": ticker, "tradeDate": trade_date, "token": ORATS_TOKEN}
    url = f"{ORATS_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"
    _rate_sleep()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=TIMEOUT_S) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
            data["_http_status"] = resp.status
            data["_elapsed_s"] = round(time.time() - t0, 3)
            cp.write_text(json.dumps(data))
            return data
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        err = {"_error": f"HTTP {e.code}", "_body": body[:300],
               "_elapsed_s": round(time.time() - t0, 3)}
        cp.write_text(json.dumps(err))
        return err
    except Exception as e:
        # Transient — log but don't cache, allow retry on next run
        return {"_error": str(e)[:200], "_elapsed_s": round(time.time() - t0, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0, help="Start at event_id (default 0 = full)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("=" * 80)
    print("PHASE 3 STAGE 2B — SKINNY ORATS PULL")
    print("=" * 80)
    print(f"Mode:       {'DRY' if args.dry_run else 'LIVE'}")
    print(f"Endpoints:  T-14 only × {SKINNY_ENDPOINTS} (2 calls/event)")
    print(f"Rate:       {SLEEP_S}s sleep → ~{int(60/SLEEP_S)} calls/min")
    print(f"Start:      event_id >= {args.start}")

    df = pd.read_csv(BIFROST_CSV)
    df["pdufa_date"] = pd.to_datetime(df["pdufa_date"], errors="coerce")
    df = df.dropna(subset=["pdufa_date", "ticker"])
    df = df[df["ticker"].str.match(r"^[A-Z]+$", na=False)]
    df = df[~df["ticker"].isin(PROBLEM_TICKERS)]
    df = df.sort_values("pdufa_date").reset_index(drop=True)
    df["event_id"] = df.index
    df = df[df["event_id"] >= args.start].copy()
    print(f"Target:     {len(df)} events")
    print()

    n_new = 0
    n_cached = 0
    n_err = 0
    n_events_processed = 0
    n_events_complete = 0
    t0 = time.time()

    for i, row in df.iterrows():
        ticker = row["ticker"]
        pdufa_date = row["pdufa_date"]
        event_id = int(row["event_id"])
        t14 = (pdufa_date - BDay(14)).strftime("%Y-%m-%d")

        got = 0
        for ep in SKINNY_ENDPOINTS:
            resp = orats_get(ep, ticker, t14, dry_run=args.dry_run)
            if resp.get("_cached"):
                n_cached += 1
                if "_error" not in resp:
                    got += 1
            elif "_error" not in resp:
                n_new += 1
                got += 1
            else:
                n_new += 1  # a cached 404 counts as "attempted"
                n_err += 1

        n_events_processed += 1
        if got == len(SKINNY_ENDPOINTS):
            n_events_complete += 1

        if n_events_processed % 10 == 0 or n_events_processed == len(df):
            elapsed = time.time() - t0
            rate = n_new / max(elapsed, 1e-6)
            rem = len(df) - n_events_processed
            eta_s = rem * 2 / max(rate, 1e-6) if rate > 0 else 0
            print(f"  [{n_events_processed:4d}/{len(df)}] eid={event_id:4d} {ticker:6s} "
                  f"{pdufa_date.strftime('%Y-%m-%d')}  new={n_new} cached={n_cached} err={n_err}  "
                  f"el={elapsed/60:4.1f}m eta={eta_s/60:4.1f}m")

        if n_events_processed % 50 == 0:
            PROGRESS_OUT.write_text(json.dumps({
                "events_processed": n_events_processed,
                "events_complete": n_events_complete,
                "last_event_id": event_id,
                "new_calls": n_new,
                "cached_calls": n_cached,
                "errors": n_err,
                "elapsed_s": round(time.time() - t0, 1),
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }, indent=2))

    elapsed = time.time() - t0
    print()
    print("=" * 80)
    print(f"DONE: {n_events_processed} events, {n_events_complete} complete (both endpoints)")
    print(f"  new={n_new}  cached={n_cached}  errors={n_err}")
    print(f"  elapsed {elapsed/60:.1f}m  rate {n_new/max(elapsed,1):.2f} new/s")
    print(f"Cache files now: {len(list(CACHE_DIR.glob('*.json')))}")

    PROGRESS_OUT.write_text(json.dumps({
        "events_processed": n_events_processed,
        "events_complete": n_events_complete,
        "new_calls": n_new,
        "cached_calls": n_cached,
        "errors": n_err,
        "elapsed_s": round(elapsed, 1),
        "done": True,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }, indent=2))


if __name__ == "__main__":
    main()
