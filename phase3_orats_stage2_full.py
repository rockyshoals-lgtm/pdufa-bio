#!/usr/bin/env python3
"""
================================================================================
PHASE 3 — ORATS Historical Options Panel — STAGE 2 FULL PULL
================================================================================

GOAL:
  Execute the full ORATS historical panel pull across 1,649 BIFROST-aligned PDUFA
  events (1,705 raw minus 56 problem-ticker events) spanning 2020-2026. Output is
  a complete per-event file cache + manifest CSV ready for Stage 3 feature
  engineering and BIFROST Explosion v5.9 honest eval.

USER-LOCKED SCOPE (Apr 20, 2026):
  - Universe: 1,705 BIFROST events minus {RHHBY, BAYRY, HOTH, INTE, TLX, DERM} = 1,649
      (exclusion list derived from Stage 1 pilot: 100% of pilot errors concentrated
       in these 6 tickers — 5 foreign ADRs + 1 delisted microcap)
  - Snapshots per event: T-14, T-7, T-1 (trading-day BDay offset from pdufa_date)
  - Endpoint policy:
      /hist/ivrank, /hist/summaries, /hist/dailies  → ALL 3 snapshots
      /hist/strikes                                 → T-14 and T-1 ONLY
      (T-7 strikes skipped: /hist/summaries already delivers IV surface at T-7)
  - v5.9 success bar: beat BIFROST Explosion v5.5 honest test AUC 0.8861

BUDGET:
  Per event: 3 core × 3 snapshots + 1 strikes × 2 snapshots = 11 calls
  Total new calls (assuming zero cache): 1,649 × 11 = 18,139
  Against 20K/month ORATS Delayed Data budget = 90.7%
  Wall clock at 92 calls/min (0.65s sleep): ~3.3 hours

RESUME LOGIC:
  - File cache at orats_phase3_cache/ is authoritative. Cached calls skipped.
  - Stage 1 pilot left 502 cached files on disk; Stage 2 reuses them.
  - Re-runnable: a killed run resumes exactly where it left off.

OUTPUTS:
  - orats_phase3_cache/<ticker>_<trade_date>_<endpoint>.json  (raw responses)
  - phase3_stage2_manifest.csv  (per-event status flags for Stage 3)
  - phase3_stage2_progress.json (checkpoint every 100 events)
  - phase3_stage2_summary.json  (final coverage + error report + budget accounting)

USAGE:
  python3 phase3_orats_stage2_full.py           # run the full pull
  python3 phase3_orats_stage2_full.py --dry-run # plan only, no API calls
  python3 phase3_orats_stage2_full.py --limit N # stop after N events (for testing)
================================================================================
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
from collections import defaultdict

import pandas as pd
from pandas.tseries.offsets import BDay


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
ORATS_BASE_URL = "https://api.orats.io/datav2"
ORATS_TOKEN = "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"

HERE = Path(__file__).parent
CACHE_DIR = HERE / "orats_phase3_cache"
CACHE_DIR.mkdir(exist_ok=True)

BIFROST_CSV = HERE / "pdufa_runup_bifrost.csv"
MANIFEST_OUT = HERE / "phase3_stage2_manifest.csv"
PROGRESS_OUT = HERE / "phase3_stage2_progress.json"
SUMMARY_OUT = HERE / "phase3_stage2_summary.json"

# Stage 1 pilot found 100% of errors concentrated in these 6 tickers (foreign ADRs
# and delisted/thin microcaps). ORATS Delayed Data does not carry them.
PROBLEM_TICKERS = {"RHHBY", "BAYRY", "HOTH", "INTE", "TLX", "DERM"}

CORE_ENDPOINTS = ["/hist/ivrank", "/hist/summaries", "/hist/dailies"]
STRIKES_ENDPOINT = "/hist/strikes"
CORE_SNAPS = ["T-14", "T-7", "T-1"]
STRIKES_SNAPS = ["T-14", "T-1"]  # budget discipline: skip T-7 strikes

SLEEP_BETWEEN_CALLS_S = 0.65   # ~92 calls/min; ORATS limit is 100/min
REQUEST_TIMEOUT_S = 30
CHECKPOINT_EVERY_N_EVENTS = 100


# -----------------------------------------------------------------------------
# HTTP layer (stdlib — mirrors Stage 1 pilot and mcp_orats.py patterns)
# -----------------------------------------------------------------------------
_ssl_ctx = ssl.create_default_context()
_last_call_ts = [0.0]


def _sleep_for_rate_limit():
    """Simple per-call sleep — 0.65s between calls gives ~92/min headroom."""
    elapsed = time.time() - _last_call_ts[0]
    if elapsed < SLEEP_BETWEEN_CALLS_S:
        time.sleep(SLEEP_BETWEEN_CALLS_S - elapsed)
    _last_call_ts[0] = time.time()


def _cache_path(ticker: str, trade_date: str, endpoint: str) -> Path:
    safe_ep = endpoint.replace("/", "_").strip("_")
    return CACHE_DIR / f"{ticker}_{trade_date}_{safe_ep}.json"


def orats_hist_get(endpoint: str, ticker: str, trade_date: str, dry_run: bool = False) -> dict:
    """
    Fetch a historical ORATS endpoint for (ticker, trade_date). Returns:
      {"data": [...], "_http_status": 200, "_elapsed_s": ..., "_cached": bool}
    or
      {"_error": "HTTP 404", "_body": "...", "_elapsed_s": ...}

    File cache is authoritative — cached hits skip the API call entirely.
    Cached ERRORS (e.g., 404s from Stage 1) are returned as-is so we don't re-hammer.
    """
    cp = _cache_path(ticker, trade_date, endpoint)
    if cp.exists():
        try:
            body = json.loads(cp.read_text())
            body["_cached"] = True
            return body
        except Exception:
            pass  # corrupt cache, proceed to refetch

    if dry_run:
        return {"_error": "DRY_RUN", "_cached": False, "_elapsed_s": 0.0}

    params = {"ticker": ticker, "tradeDate": trade_date, "token": ORATS_TOKEN}
    url = f"{ORATS_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"

    _sleep_for_rate_limit()
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
        err = {
            "_error": f"HTTP {e.code}",
            "_body": body[:500],
            "_elapsed_s": round(time.time() - t0, 3),
        }
        # Cache errors too — known 404s should not be retried every run.
        cp.write_text(json.dumps(err))
        return err
    except Exception as e:
        # Transient errors (timeout, DNS, etc.) — DO NOT cache, let next run retry.
        return {"_error": str(e), "_elapsed_s": round(time.time() - t0, 3)}


# -----------------------------------------------------------------------------
# Universe + snapshots
# -----------------------------------------------------------------------------
def load_universe() -> pd.DataFrame:
    """Load BIFROST events, drop problem tickers, return a clean event frame."""
    df = pd.read_csv(BIFROST_CSV)
    df["pdufa_date"] = pd.to_datetime(df["pdufa_date"], errors="coerce")
    df = df.dropna(subset=["pdufa_date", "ticker"]).copy()
    df = df[df["ticker"].str.match(r"^[A-Z]+$", na=False)]  # US-listed plain tickers
    n_before = len(df)
    df = df[~df["ticker"].isin(PROBLEM_TICKERS)].copy()
    n_excluded = n_before - len(df)
    df = df.sort_values("pdufa_date").reset_index(drop=True)
    df["event_id"] = df.index
    print(f"Universe: {n_before} raw → {len(df)} after excluding {n_excluded} problem-ticker events")
    return df


def compute_snapshot_dates(pdufa_date: pd.Timestamp) -> dict:
    """
    Compute T-14 / T-7 / T-1 via pandas business-day offset.
    BDay skips weekends but NOT US market holidays, so rare holiday-date
    snapshots will 404 from ORATS. Stage 1 confirmed this rate is <5% and
    tolerable — we record the failure and move on (graceful degradation).
    """
    return {
        "T-14": (pdufa_date - BDay(14)).strftime("%Y-%m-%d"),
        "T-7":  (pdufa_date - BDay(7)).strftime("%Y-%m-%d"),
        "T-1":  (pdufa_date - BDay(1)).strftime("%Y-%m-%d"),
    }


def is_data_populated(resp: dict) -> bool:
    """Response has real data → True; empty/error → False."""
    if "_error" in resp:
        return False
    data = resp.get("data")
    if data is None:
        return False
    if isinstance(data, list):
        return len(data) > 0
    return True


# -----------------------------------------------------------------------------
# Stage 2 execution
# -----------------------------------------------------------------------------
def run(dry_run: bool = False, limit: int | None = None):
    print("=" * 80)
    print("PHASE 3 STAGE 2 — ORATS Historical Full Pull")
    print("=" * 80)
    print(f"Mode:         {'DRY RUN (no API calls)' if dry_run else 'LIVE'}")
    print(f"BIFROST CSV:  {BIFROST_CSV.name}")
    print(f"Cache dir:    {CACHE_DIR.name}/ ({len(list(CACHE_DIR.glob('*.json')))} files pre-run)")
    print(f"Excluded:     {sorted(PROBLEM_TICKERS)}")
    print(f"Endpoints:    core={CORE_ENDPOINTS} all snaps; strikes @ {STRIKES_SNAPS}")
    print(f"Rate limit:   {SLEEP_BETWEEN_CALLS_S}s sleep → ~{int(60/SLEEP_BETWEEN_CALLS_S)} calls/min")
    print()

    events = load_universe()
    if limit:
        events = events.head(limit).copy()
        print(f"--limit={limit}: truncated to first {len(events)} events")
    print(f"Target universe: {len(events)} events")
    per_event_calls = len(CORE_ENDPOINTS) * len(CORE_SNAPS) + len(STRIKES_SNAPS)
    max_new_calls = len(events) * per_event_calls
    print(f"Per-event call count: {per_event_calls}  (max total if zero cache: {max_new_calls})")
    print()

    # Stats + manifest accumulators
    stats = defaultdict(lambda: {"ok": 0, "empty": 0, "error": 0, "cached": 0})
    errors_log: list = []
    manifest_rows: list = []
    t_start = time.time()
    call_count_total = 0
    call_count_new = 0
    call_count_cached = 0

    for i, row in events.iterrows():
        ticker = row["ticker"]
        pdufa_date = row["pdufa_date"]
        event_id = int(row["event_id"])
        snaps = compute_snapshot_dates(pdufa_date)

        manifest = {
            "event_id": event_id,
            "ticker": ticker,
            "pdufa_date": pdufa_date.strftime("%Y-%m-%d"),
            "year": pdufa_date.year,
        }
        for snap_label, td in snaps.items():
            manifest[f"date_{snap_label}"] = td

        for snap_label, td in snaps.items():
            endpoints_for_snap = list(CORE_ENDPOINTS)
            if snap_label in STRIKES_SNAPS:
                endpoints_for_snap.append(STRIKES_ENDPOINT)

            for ep in endpoints_for_snap:
                resp = orats_hist_get(ep, ticker, td, dry_run=dry_run)
                call_count_total += 1
                if resp.get("_cached"):
                    call_count_cached += 1
                else:
                    call_count_new += 1

                is_err = "_error" in resp
                is_ok = (not is_err) and is_data_populated(resp)
                is_empty = (not is_err) and (not is_ok)

                bkey = f"{ep}|{snap_label}"
                if is_ok:
                    stats[bkey]["ok"] += 1
                elif is_empty:
                    stats[bkey]["empty"] += 1
                else:
                    stats[bkey]["error"] += 1
                    if len(errors_log) < 500:  # cap error log size
                        errors_log.append({
                            "event_id": event_id,
                            "ticker": ticker,
                            "trade_date": td,
                            "endpoint": ep,
                            "snap": snap_label,
                            "error": resp.get("_error", "unknown"),
                        })
                if resp.get("_cached"):
                    stats[bkey]["cached"] += 1

                # Per-event manifest flags (bool per endpoint × snap)
                safe_ep = ep.replace("/hist/", "")
                manifest[f"ok_{safe_ep}_{snap_label}"] = int(is_ok)

                # Strikes row-count if present
                if is_ok and ep == STRIKES_ENDPOINT:
                    data = resp.get("data", [])
                    n = len(data) if isinstance(data, list) else 1
                    manifest[f"n_strikes_{snap_label}"] = n

        manifest_rows.append(manifest)

        # Progress output every 25 events
        if (i + 1) % 25 == 0 or i == len(events) - 1:
            elapsed = time.time() - t_start
            rate = call_count_new / max(elapsed, 1e-6)
            eta_s = (len(events) - (i + 1)) * per_event_calls / max(rate, 1e-6) if rate > 0 else 0
            print(f"  [{i+1:4d}/{len(events)}] {ticker:6s} {pdufa_date.strftime('%Y-%m-%d')} "
                  f"calls={call_count_total} (new={call_count_new}, cached={call_count_cached}) "
                  f"elapsed={elapsed/60:5.1f}m  eta={eta_s/60:5.1f}m")

        # Checkpoint every N events: write progress + partial manifest
        if (i + 1) % CHECKPOINT_EVERY_N_EVENTS == 0 or i == len(events) - 1:
            pd.DataFrame(manifest_rows).to_csv(MANIFEST_OUT, index=False)
            progress = {
                "last_event_id": event_id,
                "completed": i + 1,
                "total": len(events),
                "call_count_total": call_count_total,
                "call_count_new": call_count_new,
                "call_count_cached": call_count_cached,
                "elapsed_s": round(time.time() - t_start, 1),
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            PROGRESS_OUT.write_text(json.dumps(progress, indent=2))

    elapsed_total = time.time() - t_start

    # -------------------------------------------------------------------------
    # Final manifest + summary
    # -------------------------------------------------------------------------
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(MANIFEST_OUT, index=False)

    # Coverage by endpoint × snapshot
    coverage = {}
    for bkey, s in sorted(stats.items()):
        total = s["ok"] + s["empty"] + s["error"]
        coverage[bkey] = {
            "ok": s["ok"],
            "empty": s["empty"],
            "error": s["error"],
            "cached": s["cached"],
            "pct_ok": round(100 * s["ok"] / total, 2) if total else 0.0,
            "total": total,
        }

    # Coverage by year (using manifest)
    coverage_by_year = {}
    for year, grp in manifest_df.groupby("year"):
        row = {"n_events": len(grp)}
        for ep in CORE_ENDPOINTS:
            safe_ep = ep.replace("/hist/", "")
            for snap in CORE_SNAPS:
                col = f"ok_{safe_ep}_{snap}"
                if col in grp.columns:
                    row[f"pct_{safe_ep}_{snap}"] = round(100 * grp[col].mean(), 2)
        for snap in STRIKES_SNAPS:
            col = f"ok_strikes_{snap}"
            if col in grp.columns:
                row[f"pct_strikes_{snap}"] = round(100 * grp[col].mean(), 2)
        coverage_by_year[int(year)] = row

    # Event completeness score (how many endpoints×snaps landed per event)
    ok_cols = [c for c in manifest_df.columns if c.startswith("ok_")]
    manifest_df["total_ok"] = manifest_df[ok_cols].sum(axis=1)
    manifest_df["max_possible_ok"] = len(ok_cols)
    completeness_hist = manifest_df["total_ok"].value_counts().sort_index().to_dict()

    summary = {
        "run_config": {
            "dry_run": dry_run,
            "limit": limit,
            "problem_tickers_excluded": sorted(PROBLEM_TICKERS),
            "core_endpoints": CORE_ENDPOINTS,
            "strikes_endpoint": STRIKES_ENDPOINT,
            "core_snapshots": CORE_SNAPS,
            "strikes_snapshots": STRIKES_SNAPS,
            "sleep_between_calls_s": SLEEP_BETWEEN_CALLS_S,
        },
        "universe": {
            "total_events": int(len(events)),
            "per_event_calls_max": per_event_calls,
            "max_new_calls": max_new_calls,
        },
        "totals": {
            "calls_total":  int(call_count_total),
            "calls_new":    int(call_count_new),
            "calls_cached": int(call_count_cached),
            "elapsed_s":    round(elapsed_total, 1),
            "elapsed_min":  round(elapsed_total / 60, 1),
            "cache_files_after": len(list(CACHE_DIR.glob("*.json"))),
        },
        "coverage_by_endpoint_snapshot": coverage,
        "coverage_by_year": coverage_by_year,
        "event_completeness_histogram": {int(k): int(v) for k, v in completeness_hist.items()},
        "error_count": int(sum(s["error"] for s in stats.values())),
        "errors_sample": errors_log[:50],
        "finished_at": datetime.utcnow().isoformat() + "Z",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, default=str))

    # -------------------------------------------------------------------------
    # Terminal summary
    # -------------------------------------------------------------------------
    print()
    print("=" * 80)
    print("COVERAGE BY ENDPOINT × SNAPSHOT")
    print("=" * 80)
    for bkey, c in sorted(coverage.items()):
        print(f"  {bkey:30s}  OK={c['ok']:4d}  EMPTY={c['empty']:3d}  ERR={c['error']:3d}  "
              f"({c['pct_ok']:5.1f}%)  cached={c['cached']}")
    print()
    print("=" * 80)
    print("COVERAGE BY YEAR")
    print("=" * 80)
    for yr in sorted(coverage_by_year.keys()):
        row = coverage_by_year[yr]
        print(f"  {yr}  n={row['n_events']:4d}  "
              f"ivrank T-1={row.get('pct_ivrank_T-1', 0):5.1f}%  "
              f"summaries T-1={row.get('pct_summaries_T-1', 0):5.1f}%  "
              f"dailies T-1={row.get('pct_dailies_T-1', 0):5.1f}%  "
              f"strikes T-1={row.get('pct_strikes_T-1', 0):5.1f}%")

    print()
    print("=" * 80)
    print(f"TOTAL: {call_count_total} calls ({call_count_new} new, {call_count_cached} cached)")
    print(f"Elapsed: {elapsed_total/60:.1f} min  ({call_count_new / max(elapsed_total, 1):.1f} new calls/s)")
    print(f"Cache size after: {len(list(CACHE_DIR.glob('*.json')))} files")
    print(f"Manifest: {MANIFEST_OUT.name}")
    print(f"Summary:  {SUMMARY_OUT.name}")
    print("=" * 80)

    return summary


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Phase 3 Stage 2 ORATS full pull")
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan only (use cache, no new API calls)")
    ap.add_argument("--limit", type=int, default=None,
                    help="Stop after N events (testing)")
    args = ap.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
