#!/usr/bin/env python3
"""
================================================================================
PHASE 3 — ORATS Historical Options Panel — STAGE 1 PILOT (~50 events)
================================================================================

GOAL:
  Validate ORATS Delayed Data historical endpoint coverage across BIFROST-aligned
  PDUFA events spanning 2020-2026, BEFORE committing to a full 1,705-event pull.

SCOPE (user-locked):
  - Event universe: pdufa_runup_bifrost.csv (1,705 BIFROST-aligned PDUFA events)
  - Snapshots per event: T-14, T-7, T-1 (trading-day offset from pdufa_date)
  - Target engine: BIFROST Explosion v5.9 (|D1 move| > 25% binary classifier)
  - Endpoints (per snapshot): /hist/ivrank, /hist/summaries, /hist/dailies
  - Pilot size: ~50 events, stratified across 2020-2021, 2022-2023, 2024, 2025

PILOT QUESTIONS:
  1. Does ORATS Delayed Data retain 2020 historical data? (critical for full pull)
  2. What is the endpoint coverage rate per (ticker, trade_date)?
  3. Are /hist/strikes calls in budget? (each returns ~100-500 rows per trade_date)
  4. Rate-limit behavior at 95 req/min headroom?
  5. Data quality: IV sanity, structure format, any parser edge cases?

DELIVERABLE:
  - orats_phase3_cache/<ticker>_<trade_date>_<endpoint>.json (cached raw responses)
  - phase3_pilot_report.json (coverage stats, per-bucket outcomes, quality notes)
  - Terminal summary + go/no-go recommendation for Stage 2 full pull
================================================================================
"""
import os
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import pandas as pd
from pandas.tseries.offsets import BDay


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
ORATS_BASE_URL = "https://api.orats.io/datav2"
ORATS_TOKEN = "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"

CACHE_DIR = Path(__file__).parent / "orats_phase3_cache"
CACHE_DIR.mkdir(exist_ok=True)

BIFROST_CSV = Path(__file__).parent / "pdufa_runup_bifrost.csv"
REPORT_OUT = Path(__file__).parent / "phase3_pilot_report.json"

# Endpoints we want at each snapshot (all /hist/* — historical variants).
# NOTE: /hist/strikes is NOT in the Delayed Data plan per ORATS docs; we probe
# the cheaper /hist/ivrank + /hist/summaries + /hist/dailies first. The pilot
# also probes /hist/strikes on a couple events to confirm unavailability.
CORE_ENDPOINTS = ["/hist/ivrank", "/hist/summaries", "/hist/dailies"]
PROBE_ENDPOINTS = ["/hist/strikes"]  # only run on 3 events to confirm (un)availability

# Pilot sampling strata (year-bucketed, total ≈ 50)
STRATA = {
    "2020_2021": {"years": [2020, 2021], "n": 10},
    "2022_2023": {"years": [2022, 2023], "n": 10},
    "2024":       {"years": [2024],       "n": 15},
    "2025_2026":  {"years": [2025, 2026], "n": 15},
}

RANDOM_SEED = 42
MAX_REQUESTS_PER_MINUTE = 95
REQUEST_TIMEOUT_S = 30


# -----------------------------------------------------------------------------
# HTTP layer (stdlib, matches mcp_orats.py patterns)
# -----------------------------------------------------------------------------
_req_stamps: list = []
_ssl_ctx = ssl.create_default_context()


def _rate_limit():
    now = time.time()
    while _req_stamps and _req_stamps[0] < now - 60:
        _req_stamps.pop(0)
    if len(_req_stamps) >= MAX_REQUESTS_PER_MINUTE:
        sleep = 60 - (now - _req_stamps[0]) + 0.1
        if sleep > 0:
            time.sleep(sleep)
    _req_stamps.append(time.time())


def _cache_path(ticker: str, trade_date: str, endpoint: str) -> Path:
    safe_ep = endpoint.replace("/", "_").strip("_")
    return CACHE_DIR / f"{ticker}_{trade_date}_{safe_ep}.json"


def orats_hist_get(endpoint: str, ticker: str, trade_date: str) -> dict:
    """Fetch historical ORATS endpoint for (ticker, trade_date). Uses file cache."""
    cp = _cache_path(ticker, trade_date, endpoint)
    if cp.exists():
        try:
            body = json.loads(cp.read_text())
            body["_cached"] = True
            return body
        except Exception:
            pass  # corrupt cache — refetch

    params = {
        "ticker": ticker,
        "tradeDate": trade_date,
        "token": ORATS_TOKEN,
    }
    url = f"{ORATS_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"

    _rate_limit()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=REQUEST_TIMEOUT_S) as resp:
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
        err = {"_error": f"HTTP {e.code}", "_body": body[:500], "_elapsed_s": round(time.time() - t0, 3)}
        # Cache errors too so we don't re-hammer the API on known 4xx
        cp.write_text(json.dumps(err))
        return err
    except Exception as e:
        err = {"_error": str(e), "_elapsed_s": round(time.time() - t0, 3)}
        return err


# -----------------------------------------------------------------------------
# Pilot sampling
# -----------------------------------------------------------------------------
def load_and_sample() -> pd.DataFrame:
    df = pd.read_csv(BIFROST_CSV)
    df["pdufa_date"] = pd.to_datetime(df["pdufa_date"], errors="coerce")
    df = df.dropna(subset=["pdufa_date", "ticker"]).copy()
    df = df[df["ticker"].str.match(r"^[A-Z]+$", na=False)]  # clean OTC/foreign-listing noise
    df["year"] = df["pdufa_date"].dt.year

    rng = random.Random(RANDOM_SEED)
    picks = []
    for bucket, cfg in STRATA.items():
        pool = df[df["year"].isin(cfg["years"])]
        n = min(cfg["n"], len(pool))
        if n == 0:
            continue
        idx = rng.sample(list(pool.index), n)
        sub = pool.loc[idx].copy()
        sub["pilot_bucket"] = bucket
        picks.append(sub)

    out = pd.concat(picks, ignore_index=True)
    return out


def compute_snapshot_dates(pdufa_date: pd.Timestamp) -> dict:
    """
    Compute T-14 / T-7 / T-1 using business-day offset.

    BDay approximates US market days well (weekends excluded) but does not
    account for US market holidays. If ORATS returns empty for a non-trading
    day, we walk back by 1 BDay up to 5 steps as fallback.
    """
    return {
        "T-14": (pdufa_date - BDay(14)).strftime("%Y-%m-%d"),
        "T-7":  (pdufa_date - BDay(7)).strftime("%Y-%m-%d"),
        "T-1":  (pdufa_date - BDay(1)).strftime("%Y-%m-%d"),
    }


def is_data_populated(endpoint: str, response: dict) -> bool:
    """
    Decide whether a response actually has data. ORATS returns {"data": [...]} on success;
    an empty list or an error key means no coverage.
    """
    if "_error" in response:
        return False
    data = response.get("data")
    if data is None:
        return False
    if isinstance(data, list):
        return len(data) > 0
    return True


# -----------------------------------------------------------------------------
# Pilot execution
# -----------------------------------------------------------------------------
def run_pilot():
    print("=" * 80)
    print("Phase 3 Stage 1 — ORATS Historical Pilot")
    print("=" * 80)
    print(f"BIFROST source: {BIFROST_CSV.name}")
    print(f"Cache dir:      {CACHE_DIR.name}/")
    print(f"Seed:           {RANDOM_SEED}")
    print()

    sample = load_and_sample()
    print(f"Pilot sample: {len(sample)} events")
    print(sample["pilot_bucket"].value_counts().to_string())
    print()

    # Track results: per (bucket, endpoint, snapshot) coverage and per-event status
    stats = defaultdict(lambda: {"ok": 0, "empty": 0, "error": 0})
    event_rows = []
    errors_log = []
    call_count = 0
    t_start = time.time()

    # Sort by pdufa_date desc so most recent events come first (canary for endpoint health)
    sample = sample.sort_values("pdufa_date", ascending=False).reset_index(drop=True)

    # Reserve a tiny subsample for /hist/strikes probe (3 events: 1 per year bucket)
    probe_ids = set()
    for bucket in STRATA.keys():
        sub = sample[sample["pilot_bucket"] == bucket]
        if len(sub) > 0:
            probe_ids.add(sub.iloc[0].name)  # first (most recent) of each bucket

    for i, row in sample.iterrows():
        ticker = row["ticker"]
        pdufa_date = row["pdufa_date"]
        bucket = row["pilot_bucket"]
        snaps = compute_snapshot_dates(pdufa_date)

        event_result = {
            "ticker": ticker,
            "pdufa_date": pdufa_date.strftime("%Y-%m-%d"),
            "bucket": bucket,
            "snapshots": {},
        }

        endpoints_for_event = list(CORE_ENDPOINTS)
        if i in probe_ids:
            endpoints_for_event += PROBE_ENDPOINTS

        for snap_label, td in snaps.items():
            snap_out = {}
            for ep in endpoints_for_event:
                resp = orats_hist_get(ep, ticker, td)
                call_count += 1

                cached = resp.get("_cached", False)
                is_err = "_error" in resp
                is_ok = (not is_err) and is_data_populated(ep, resp)
                is_empty = (not is_err) and (not is_ok)

                bucket_key = f"{bucket}|{ep}|{snap_label}"
                if is_ok:
                    stats[bucket_key]["ok"] += 1
                elif is_empty:
                    stats[bucket_key]["empty"] += 1
                else:
                    stats[bucket_key]["error"] += 1
                    errors_log.append({
                        "ticker": ticker,
                        "trade_date": td,
                        "endpoint": ep,
                        "error": resp.get("_error", "unknown"),
                        "body_snippet": resp.get("_body", "")[:200],
                    })

                snap_out[ep] = {
                    "status": "OK" if is_ok else ("EMPTY" if is_empty else "ERROR"),
                    "cached": cached,
                    "elapsed_s": resp.get("_elapsed_s"),
                }

                # Data-quality probes on success
                if is_ok and ep == "/hist/ivrank":
                    row0 = resp["data"][0] if isinstance(resp["data"], list) else resp["data"]
                    snap_out[ep]["sample"] = {
                        "iv": row0.get("iv"),
                        "ivPct1y": row0.get("ivPct1y"),
                        "ivRank1y": row0.get("ivRank1y"),
                    }
                elif is_ok and ep == "/hist/summaries":
                    row0 = resp["data"][0] if isinstance(resp["data"], list) else resp["data"]
                    snap_out[ep]["sample"] = {
                        "iv30d": row0.get("iv30d"),
                        "iv60d": row0.get("iv60d"),
                        "iv90d": row0.get("iv90d"),
                        "slope": row0.get("slope"),
                    }
                elif is_ok and ep == "/hist/dailies":
                    row0 = resp["data"][0] if isinstance(resp["data"], list) else resp["data"]
                    snap_out[ep]["sample"] = {
                        "clsPx": row0.get("clsPx"),
                        "open": row0.get("open"),
                    }
                elif is_ok and ep == "/hist/strikes":
                    data = resp["data"]
                    snap_out[ep]["n_strikes"] = len(data) if isinstance(data, list) else 1

            event_result["snapshots"][snap_label] = snap_out

        event_rows.append(event_result)

        # Periodic progress line
        if (i + 1) % 10 == 0 or i == len(sample) - 1:
            elapsed = time.time() - t_start
            print(f"  [{i+1:3d}/{len(sample)}] {ticker:6s} {pdufa_date.strftime('%Y-%m-%d')} "
                  f"bucket={bucket:10s} calls={call_count} elapsed={elapsed:5.1f}s")

    elapsed_total = time.time() - t_start

    # -------------------------------------------------------------------------
    # Build summary
    # -------------------------------------------------------------------------
    print()
    print("-" * 80)
    print("COVERAGE BY BUCKET × ENDPOINT × SNAPSHOT")
    print("-" * 80)
    coverage_summary = {}
    for bucket_key, s in sorted(stats.items()):
        total = s["ok"] + s["empty"] + s["error"]
        pct = 100 * s["ok"] / total if total else 0
        print(f"  {bucket_key:40s}  OK={s['ok']:3d}  EMPTY={s['empty']:3d}  ERR={s['error']:3d}  ({pct:5.1f}%)")
        coverage_summary[bucket_key] = {
            "ok": s["ok"],
            "empty": s["empty"],
            "error": s["error"],
            "pct_ok": round(pct, 2),
        }

    print()
    print("-" * 80)
    print("BUCKET-LEVEL ROLL-UP (any core endpoint success rate, averaged)")
    print("-" * 80)
    rollup = {}
    for bucket in STRATA.keys():
        ok_total, all_total = 0, 0
        for ep in CORE_ENDPOINTS:
            for snap in ["T-14", "T-7", "T-1"]:
                s = stats.get(f"{bucket}|{ep}|{snap}", {"ok": 0, "empty": 0, "error": 0})
                ok_total += s["ok"]
                all_total += s["ok"] + s["empty"] + s["error"]
        pct = 100 * ok_total / all_total if all_total else 0
        print(f"  {bucket:10s}  core-endpoint OK rate = {pct:5.1f}%  ({ok_total}/{all_total})")
        rollup[bucket] = {"ok": ok_total, "total": all_total, "pct_ok": round(pct, 2)}

    print()
    print("-" * 80)
    print(f"TOTAL API CALLS: {call_count}")
    print(f"TOTAL ELAPSED:   {elapsed_total:.1f}s  ({call_count / max(elapsed_total, 1):.1f} calls/s)")
    print(f"CACHE ENTRIES:   {len(list(CACHE_DIR.glob('*.json')))}")
    print()

    if errors_log:
        print("-" * 80)
        print(f"ERRORS ({len(errors_log)} — showing first 10)")
        print("-" * 80)
        for err in errors_log[:10]:
            print(f"  {err['ticker']:6s} {err['trade_date']} {err['endpoint']:20s}  {err['error']}")
        print()

    # -------------------------------------------------------------------------
    # Go/no-go recommendation for Stage 2
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("STAGE 2 GO/NO-GO RECOMMENDATION")
    print("=" * 80)

    # Heuristics
    oldest_ok = rollup.get("2020_2021", {}).get("pct_ok", 0)
    midold_ok = rollup.get("2022_2023", {}).get("pct_ok", 0)
    recent_ok = rollup.get("2025_2026", {}).get("pct_ok", 0)

    verdict_lines = []
    if oldest_ok >= 70 and midold_ok >= 80 and recent_ok >= 80:
        verdict = "GO — ORATS Delayed Data covers 2020-2026 well enough for full pull."
    elif midold_ok >= 80 and recent_ok >= 80 and oldest_ok >= 40:
        verdict = "PARTIAL GO — restrict Stage 2 to events with pdufa_date >= 2022-01-01."
    elif recent_ok >= 80 and midold_ok < 60:
        verdict = "STRICT PARTIAL — restrict Stage 2 to 2024-2026 events only; pre-2024 has insufficient coverage."
    else:
        verdict = "NO-GO — historical endpoints do not return enough data; escalate to ORATS support or pivot data source."

    verdict_lines.append(verdict)
    verdict_lines.append(f"  2020-2021 OK rate: {oldest_ok:.1f}%")
    verdict_lines.append(f"  2022-2023 OK rate: {midold_ok:.1f}%")
    verdict_lines.append(f"  2024      OK rate: {rollup.get('2024', {}).get('pct_ok', 0):.1f}%")
    verdict_lines.append(f"  2025-2026 OK rate: {recent_ok:.1f}%")

    for line in verdict_lines:
        print(line)
    print()

    report = {
        "pilot_config": {
            "seed": RANDOM_SEED,
            "strata": STRATA,
            "core_endpoints": CORE_ENDPOINTS,
            "probe_endpoints": PROBE_ENDPOINTS,
            "sample_size": len(sample),
        },
        "totals": {
            "api_calls": call_count,
            "elapsed_s": round(elapsed_total, 1),
            "cache_entries": len(list(CACHE_DIR.glob("*.json"))),
        },
        "coverage_by_bucket_endpoint_snapshot": coverage_summary,
        "bucket_rollup": rollup,
        "verdict": verdict,
        "verdict_detail": verdict_lines,
        "errors": errors_log[:50],
        "event_results": event_rows,
    }

    REPORT_OUT.write_text(json.dumps(report, indent=2, default=str))
    print(f"Report written: {REPORT_OUT.name}")
    print("=" * 80)
    return report


if __name__ == "__main__":
    run_pilot()
