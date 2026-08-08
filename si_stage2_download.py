#!/usr/bin/env python3
"""
Phase 2 Stage 2 — Download FINRA biweekly short-interest consolidated files.

Source URL pattern (verified 2026-04-20):
  https://cdn.finra.org/equity/otcmarket/biweekly/shrt{YYYYMMDD}.csv

Coverage note:
  - FINRA CDN serves files from 2017-12-29 onward. Pre-2018 dates return 403.
  - Files are pipe-delimited, 14 columns, schema:
      accountingYearMonthNumber|symbolCode|issueName|issuerServicesGroupExchangeCode|
      marketClassCode|currentShortPositionQuantity|previousShortPositionQuantity|
      stockSplitFlag|averageDailyVolumeQuantity|daysToCoverQuantity|revisionFlag|
      changePercent|changePreviousNumber|settlementDate
  - NYSE/NASDAQ NMS listings ARE included (verified: 'A' Agilent listed as NYSE in 2018-01-31 file).

Input:
  - si_settlement_dates.json (272 dates 2015-01-15 → 2026-04-30)

Output:
  - si_raw/shrt{YYYYMMDD}.csv    — raw download cache (per-date)
  - si_stage2_manifest.json       — { date: { http_code, size, rows, path } }
  - si_stage2.log                 — progress log
"""
import json
import os
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
DATES_IN = BASE / 'si_settlement_dates.json'
RAW_DIR = BASE / 'si_raw'
MANIFEST_OUT = BASE / 'si_stage2_manifest.json'
LOG_OUT = BASE / 'si_stage2.log'

URL_TEMPLATE = 'https://cdn.finra.org/equity/otcmarket/biweekly/shrt{yyyymmdd}.csv'
HEADERS = {'User-Agent': '9Realms Research rockyshoals@gmail.com'}
MAX_WORKERS = 6  # polite with CDN
RATE_LIMIT_PER_SEC = 4.0  # well under any CDN limit

_rate_lock = threading.Lock()
_last_request_time = [0.0]
_min_interval = 1.0 / RATE_LIMIT_PER_SEC
_log_lock = threading.Lock()


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    with _log_lock:
        print(line, flush=True)
        with open(LOG_OUT, 'a') as f:
            f.write(line + '\n')


def rate_limited_wait():
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time[0]
        if elapsed < _min_interval:
            time.sleep(_min_interval - elapsed)
        _last_request_time[0] = time.time()


def download_one(date_str: str):
    """date_str = 'YYYY-MM-DD'. Returns dict with http_code, size, rows, path."""
    yyyymmdd = date_str.replace('-', '')
    url = URL_TEMPLATE.format(yyyymmdd=yyyymmdd)
    out_path = RAW_DIR / f'shrt{yyyymmdd}.csv'

    # Skip if already downloaded and non-empty
    if out_path.exists() and out_path.stat().st_size > 1000:
        try:
            with open(out_path) as f:
                rows = sum(1 for _ in f) - 1
            return {
                'date': date_str,
                'http_code': 200,
                'size': out_path.stat().st_size,
                'rows': rows,
                'path': str(out_path),
                'cached': True,
            }
        except Exception:
            pass  # fall through to re-download

    rate_limited_wait()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
        out_path.write_bytes(body)
        rows = body.count(b'\n') - 1
        return {
            'date': date_str,
            'http_code': 200,
            'size': len(body),
            'rows': rows,
            'path': str(out_path),
            'cached': False,
        }
    except urllib.error.HTTPError as e:
        return {
            'date': date_str,
            'http_code': e.code,
            'size': 0,
            'rows': 0,
            'path': None,
            'cached': False,
        }
    except Exception as e:
        return {
            'date': date_str,
            'http_code': 0,
            'size': 0,
            'rows': 0,
            'path': None,
            'cached': False,
            'error': str(e),
        }


def main():
    RAW_DIR.mkdir(exist_ok=True)
    LOG_OUT.write_text('')  # truncate

    with open(DATES_IN) as f:
        dates_data = json.load(f)
    dates = dates_data['dates']
    log(f'Loaded {len(dates)} settlement dates from {dates[0]} to {dates[-1]}')
    log(f'Target URL pattern: {URL_TEMPLATE}')
    log(f'Rate limit: {RATE_LIMIT_PER_SEC}/s, workers: {MAX_WORKERS}')

    # Load existing manifest to resume
    existing = {}
    if MANIFEST_OUT.exists():
        try:
            with open(MANIFEST_OUT) as f:
                existing = json.load(f)
            existing_files = sum(1 for v in existing.values() if v.get('http_code') == 200)
            log(f'Resuming: {existing_files} successful downloads in existing manifest')
        except json.JSONDecodeError:
            existing = {}

    results = dict(existing)
    done = [0]
    success = [0]
    fail_403 = [0]
    fail_other = [0]
    start_time = time.time()

    def process_date(date_str):
        # Skip if already successful in manifest
        prev = results.get(date_str, {})
        if prev.get('http_code') == 200 and prev.get('size', 0) > 1000:
            return None  # already done
        res = download_one(date_str)
        done[0] += 1
        if res['http_code'] == 200:
            success[0] += 1
        elif res['http_code'] == 403:
            fail_403[0] += 1
        else:
            fail_other[0] += 1
        return res

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_date, d): d for d in dates}
        last_save = time.time()
        for fut in as_completed(futures):
            res = fut.result()
            if res is None:
                continue
            results[res['date']] = res
            total = done[0]
            if total % 25 == 0:
                elapsed = time.time() - start_time
                rate = total / elapsed if elapsed > 0 else 0
                log(f'  {total:>3} processed  ok={success[0]}  403={fail_403[0]}  other={fail_other[0]}  rate={rate:.1f}/s')
            # checkpoint every 30s
            if time.time() - last_save > 30:
                with open(MANIFEST_OUT, 'w') as f:
                    json.dump(results, f, indent=2)
                last_save = time.time()

    # Final save
    with open(MANIFEST_OUT, 'w') as f:
        json.dump(results, f, indent=2)

    ok_count = sum(1 for v in results.values() if v.get('http_code') == 200)
    total_rows = sum(v.get('rows', 0) for v in results.values() if v.get('http_code') == 200)
    total_mb = sum(v.get('size', 0) for v in results.values() if v.get('http_code') == 200) / 1e6
    log(f'Stage 2 COMPLETE: {ok_count}/{len(dates)} dates downloaded')
    log(f'  total rows: {total_rows:,}')
    log(f'  total size: {total_mb:.1f} MB')
    log(f'  403 (pre-Dec-2017): {fail_403[0]}')
    log(f'  other failures: {fail_other[0]}')


if __name__ == '__main__':
    main()
