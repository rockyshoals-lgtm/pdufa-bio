#!/usr/bin/env python3
"""
Phase 2 Stage 3 — Build per-event T-1 compliant short-interest features.

Input:
  - si_stage2_manifest.json    — { 'YYYY-MM-DD': { http_code, size, rows, path, ... } }
  - si_raw/shrt{YYYYMMDD}.csv  — pipe-delimited FINRA biweekly files
  - backfill_event_index.csv   — event_id, ticker, catalyst_date, outcome, engine

Schema (14 pipe-delimited columns):
  accountingYearMonthNumber | symbolCode | issueName | issuerServicesGroupExchangeCode |
  marketClassCode | currentShortPositionQuantity | previousShortPositionQuantity |
  stockSplitFlag | averageDailyVolumeQuantity | daysToCoverQuantity | revisionFlag |
  changePercent | changePreviousNumber | settlementDate

T-1 compliance rule:
  For event E (ticker T, catalyst_date D), the most recent SI snapshot MUST have
  settlement_date < D. We find the last snapshot per ticker-before-D and build
  a 4-point time series (T-1, T-2, T-3, T-4) going backwards through history.

Features per event (24 total):
  Level (T-1):
    si_t1_short_qty              — current short position quantity
    si_t1_adv                    — average daily volume quantity
    si_t1_days_to_cover          — days to cover
    si_t1_change_pct             — % change vs previous snapshot
    si_t1_short_to_adv           — short_qty / adv (alt measure)
    si_t1_log_short_qty          — log1p(short_qty)
    si_t1_log_adv                — log1p(adv)
    si_t1_lag_days               — days between settlement and catalyst
  Deltas (T-1 vs T-2, T-3, T-4):
    si_delta_1_2_short_pct       — (T1-T2)/T2 in short_qty
    si_delta_1_3_short_pct
    si_delta_1_4_short_pct
    si_delta_1_2_dtc             — T1-T2 days_to_cover
    si_delta_1_3_dtc
  Trend features:
    si_trend_4pt_slope           — linear slope across 4 snapshots (log-short)
    si_trend_monotonic_up        — binary: strict monotonic increase
    si_trend_monotonic_down      — binary: strict monotonic decrease
    si_vol_ratio_recent          — std(recent 4) / mean(recent 4) log-short
  Non-linear:
    si_t1_dtc_sq                 — days_to_cover**2
    si_t1_short_to_adv_sq        — (short/adv)**2
    si_t1_log_short_qty_sq
  Indicators:
    si_t1_has_snapshot           — 1 if any T-1 snapshot found, else 0
    si_n_snapshots_365d          — count of snapshots in prior 365 days
    si_n_snapshots_total         — total snapshots ever before catalyst

Output:
  - si_event_features.csv       — event_id × 24 features + ticker + catalyst_date
  - si_stage3_build.log         — progress log
"""
import csv
import json
import math
import os
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import time

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
MANIFEST_IN = BASE / 'si_stage2_manifest.json'
EVENT_IN = BASE / 'backfill_event_index.csv'
FEAT_OUT = BASE / 'si_event_features.csv'
LOG_OUT = BASE / 'si_stage3_build.log'


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG_OUT, 'a') as f:
        f.write(line + '\n')


def parse_date(s):
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def safe_float(x, default=0.0):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (ValueError, TypeError):
        return default


def load_finra_file(path, date_str):
    """Parse one biweekly file. Returns dict ticker -> snapshot dict."""
    out = {}
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            header = f.readline().strip().split('|')
            for line in f:
                parts = line.rstrip('\n').split('|')
                if len(parts) < 14:
                    continue
                ticker = parts[1].strip().upper()
                if not ticker:
                    continue
                # Prefer NMS/NYSE; keep first match per ticker (file is per-symbol).
                if ticker in out:
                    continue
                out[ticker] = {
                    'settlement_date': date_str,
                    'short_qty': safe_float(parts[5]),
                    'prev_short_qty': safe_float(parts[6]),
                    'adv': safe_float(parts[8]),
                    'days_to_cover': safe_float(parts[9]),
                    'change_pct': safe_float(parts[11]),
                    'market_class': parts[4].strip(),
                    'exchange': parts[3].strip(),
                }
    except Exception as e:
        log(f'  ! failed to parse {path}: {e}')
    return out


def build_ticker_series(manifest):
    """Return { ticker: [(settlement_date, snapshot_dict), ...] } sorted ascending."""
    # Order manifest dates ascending
    dates_ok = sorted(
        d for d, meta in manifest.items()
        if meta.get('http_code') == 200 and meta.get('rows', 0) > 100 and meta.get('path')
    )
    log(f'Loading {len(dates_ok)} FINRA biweekly files...')
    ticker_map = defaultdict(list)
    for i, d in enumerate(dates_ok):
        path = manifest[d]['path']
        snap = load_finra_file(path, d)
        for tk, row in snap.items():
            ticker_map[tk].append((d, row))
        if (i + 1) % 20 == 0:
            log(f'  parsed {i+1}/{len(dates_ok)} files, {len(ticker_map):,} tickers seen')
    # Already sorted because dates_ok is sorted
    log(f'Loaded series for {len(ticker_map):,} unique tickers')
    return dict(ticker_map)


def compute_event_features(ticker, catalyst_date, series):
    """Compute T-1 SI features for a single event."""
    feats = {}
    # Default zeros
    zero_keys = [
        'si_t1_short_qty', 'si_t1_adv', 'si_t1_days_to_cover', 'si_t1_change_pct',
        'si_t1_short_to_adv', 'si_t1_log_short_qty', 'si_t1_log_adv', 'si_t1_lag_days',
        'si_delta_1_2_short_pct', 'si_delta_1_3_short_pct', 'si_delta_1_4_short_pct',
        'si_delta_1_2_dtc', 'si_delta_1_3_dtc',
        'si_trend_4pt_slope', 'si_trend_monotonic_up', 'si_trend_monotonic_down',
        'si_vol_ratio_recent',
        'si_t1_dtc_sq', 'si_t1_short_to_adv_sq', 'si_t1_log_short_qty_sq',
        'si_t1_has_snapshot', 'si_n_snapshots_365d', 'si_n_snapshots_total',
    ]
    for k in zero_keys:
        feats[k] = 0.0

    if ticker not in series:
        return feats
    # Filter to snapshots STRICTLY before catalyst_date
    prior = [(parse_date(d), row) for (d, row) in series[ticker] if parse_date(d) and parse_date(d) < catalyst_date]
    if not prior:
        return feats
    # Already in ascending order; take last 4 as [T-4, T-3, T-2, T-1]
    prior.sort(key=lambda x: x[0])
    feats['si_n_snapshots_total'] = len(prior)
    cutoff_365 = catalyst_date - timedelta(days=365)
    feats['si_n_snapshots_365d'] = sum(1 for d, _ in prior if d >= cutoff_365)
    feats['si_t1_has_snapshot'] = 1

    recent = prior[-4:]  # up to 4
    # T-1 = recent[-1]
    t1_date, t1 = recent[-1]
    feats['si_t1_short_qty'] = t1['short_qty']
    feats['si_t1_adv'] = t1['adv']
    feats['si_t1_days_to_cover'] = t1['days_to_cover']
    feats['si_t1_change_pct'] = t1['change_pct']
    if t1['adv'] > 0:
        feats['si_t1_short_to_adv'] = t1['short_qty'] / t1['adv']
    feats['si_t1_log_short_qty'] = math.log1p(max(0.0, t1['short_qty']))
    feats['si_t1_log_adv'] = math.log1p(max(0.0, t1['adv']))
    feats['si_t1_lag_days'] = (catalyst_date - t1_date).days

    # Deltas
    def delta_pct(newer, older):
        if older <= 0:
            return 0.0
        return (newer - older) / older

    if len(recent) >= 2:
        _, t2 = recent[-2]
        feats['si_delta_1_2_short_pct'] = delta_pct(t1['short_qty'], t2['short_qty'])
        feats['si_delta_1_2_dtc'] = t1['days_to_cover'] - t2['days_to_cover']
    if len(recent) >= 3:
        _, t3 = recent[-3]
        feats['si_delta_1_3_short_pct'] = delta_pct(t1['short_qty'], t3['short_qty'])
        feats['si_delta_1_3_dtc'] = t1['days_to_cover'] - t3['days_to_cover']
    if len(recent) >= 4:
        _, t4 = recent[-4]
        feats['si_delta_1_4_short_pct'] = delta_pct(t1['short_qty'], t4['short_qty'])

    # Trend features
    log_shorts = [math.log1p(max(0.0, row['short_qty'])) for _, row in recent]
    if len(log_shorts) >= 2:
        xs = list(range(len(log_shorts)))
        mx = sum(xs) / len(xs)
        my = sum(log_shorts) / len(log_shorts)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, log_shorts))
        den = sum((x - mx) ** 2 for x in xs)
        feats['si_trend_4pt_slope'] = num / den if den > 0 else 0.0
        feats['si_trend_monotonic_up'] = 1 if all(log_shorts[i] < log_shorts[i + 1] for i in range(len(log_shorts) - 1)) else 0
        feats['si_trend_monotonic_down'] = 1 if all(log_shorts[i] > log_shorts[i + 1] for i in range(len(log_shorts) - 1)) else 0
    if len(log_shorts) >= 2:
        mean_ls = sum(log_shorts) / len(log_shorts)
        if mean_ls > 1e-6:
            try:
                std_ls = statistics.pstdev(log_shorts)
                feats['si_vol_ratio_recent'] = std_ls / mean_ls
            except statistics.StatisticsError:
                pass

    # Non-linear
    feats['si_t1_dtc_sq'] = feats['si_t1_days_to_cover'] ** 2
    feats['si_t1_short_to_adv_sq'] = feats['si_t1_short_to_adv'] ** 2
    feats['si_t1_log_short_qty_sq'] = feats['si_t1_log_short_qty'] ** 2

    return feats


def main():
    LOG_OUT.write_text('')
    log('Phase 2 Stage 3 starting')

    # Load manifest
    if not MANIFEST_IN.exists():
        log(f'ERROR: manifest not found at {MANIFEST_IN}')
        return
    with open(MANIFEST_IN) as f:
        manifest = json.load(f)
    ok = [d for d, v in manifest.items() if v.get('http_code') == 200]
    log(f'Manifest has {len(manifest)} entries, {len(ok)} successful (200) downloads')

    # Build ticker series
    series = build_ticker_series(manifest)

    # Load events
    events = []
    with open(EVENT_IN) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cd = parse_date(row.get('catalyst_date'))
            if cd is None:
                continue
            events.append({
                'event_id': row['event_id'],
                'ticker': row['ticker'].upper(),
                'catalyst_date': cd,
                'outcome': row.get('outcome', ''),
                'engine': row.get('engine', ''),
            })
    log(f'Loaded {len(events):,} events from {EVENT_IN.name}')

    # Compute features
    rows_out = []
    matched = 0
    t1_hit = 0
    for i, ev in enumerate(events):
        feats = compute_event_features(ev['ticker'], ev['catalyst_date'], series)
        feats['event_id'] = ev['event_id']
        feats['ticker'] = ev['ticker']
        feats['catalyst_date'] = ev['catalyst_date'].strftime('%Y-%m-%d')
        if ev['ticker'] in series:
            matched += 1
        if feats['si_t1_has_snapshot'] == 1:
            t1_hit += 1
        rows_out.append(feats)
        if (i + 1) % 500 == 0:
            log(f'  processed {i+1}/{len(events)} events  matched_ticker={matched}  has_t1_snapshot={t1_hit}')

    log(f'Coverage: {matched:,}/{len(events):,} events had ticker in FINRA series ({100*matched/len(events):.1f}%)')
    log(f'T-1 snapshot hit: {t1_hit:,}/{len(events):,} ({100*t1_hit/len(events):.1f}%)')

    # Write CSV
    cols_lead = ['event_id', 'ticker', 'catalyst_date']
    feat_cols = [
        'si_t1_has_snapshot', 'si_n_snapshots_365d', 'si_n_snapshots_total',
        'si_t1_short_qty', 'si_t1_adv', 'si_t1_days_to_cover', 'si_t1_change_pct',
        'si_t1_short_to_adv', 'si_t1_log_short_qty', 'si_t1_log_adv', 'si_t1_lag_days',
        'si_delta_1_2_short_pct', 'si_delta_1_3_short_pct', 'si_delta_1_4_short_pct',
        'si_delta_1_2_dtc', 'si_delta_1_3_dtc',
        'si_trend_4pt_slope', 'si_trend_monotonic_up', 'si_trend_monotonic_down',
        'si_vol_ratio_recent',
        'si_t1_dtc_sq', 'si_t1_short_to_adv_sq', 'si_t1_log_short_qty_sq',
    ]
    cols = cols_lead + feat_cols
    with open(FEAT_OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k, 0) for k in cols})
    log(f'Wrote {FEAT_OUT}  rows={len(rows_out)}  cols={len(cols)}')
    log('Stage 3 COMPLETE')


if __name__ == '__main__':
    main()
