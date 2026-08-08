#!/usr/bin/env python3
"""
Phase 1.4 — Build event-level Form 4 features with T-1 compliance.

Input:
  - form4_transactions.json (from stage 2)  — ticker -> list of transactions
  - backfill_event_index.csv                — event_id, ticker, catalyst_date, outcome, engine

Output:
  - form4_event_features.csv                — event_id × feature matrix

T-1 compliance rule:
  A transaction is included for event E (ticker T, date D) only if:
    txn['ticker'] == T
    AND txn['filing_date'] < D  (STRICTLY before catalyst date)

Transaction code semantics:
  P = open-market purchase (ACTIVE BUY — strong signal)
  S = open-market sale     (ACTIVE SELL — directional signal)
  A = grant/award          (compensation, NEUTRAL)
  D = disposition to issuer
  F = tax withholding / share surrender (NEUTRAL — mechanical)
  M = derivative exercise  (NEUTRAL — mechanical)
  G = gift                 (NEUTRAL)
  X = exercise of in-the-money derivative
  C = conversion
  V = voluntary transaction
  I = discretionary
"""

import json
import sys
import math
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
TXN_IN = BASE / 'form4_transactions.json'
EVENT_IN = BASE / 'backfill_event_index.csv'
FEAT_OUT = BASE / 'form4_event_features.csv'

WINDOWS = [30, 90, 180, 365]

ACTIVE_BUY_CODES = {'P'}
ACTIVE_SELL_CODES = {'S'}


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def classify_role(t):
    """Return tuple (is_ceo, is_cfo, is_director, is_officer, is_ten, is_other)."""
    is_ceo = False
    is_cfo = False
    title = (t.get('officer_title') or '').lower()
    if 'chief executive' in title or title.strip() == 'ceo' or title.startswith('ceo '):
        is_ceo = True
    if 'chief financial' in title or title.strip() == 'cfo' or title.startswith('cfo '):
        is_cfo = True
    return (
        is_ceo,
        is_cfo,
        bool(t.get('is_director')),
        bool(t.get('is_officer')),
        bool(t.get('is_ten_percent')),
        bool(t.get('is_other')),
    )


def compute_event_features(event_id, ticker, catalyst_date, txns):
    """Compute the feature vector for a single event."""
    feats = {'event_id': event_id, 'ticker': ticker, 'catalyst_date': catalyst_date.strftime('%Y-%m-%d')}

    for w in WINDOWS:
        lower = catalyst_date - timedelta(days=w)
        in_window = []
        for t in txns:
            fd = parse_date(t.get('filing_date'))
            if fd is None:
                continue
            # STRICT T-1: filing_date < catalyst_date AND filing_date >= catalyst - w
            if fd >= catalyst_date:
                continue
            if fd < lower:
                continue
            in_window.append(t)

        buys = [t for t in in_window if t.get('transaction_code') in ACTIVE_BUY_CODES]
        sells = [t for t in in_window if t.get('transaction_code') in ACTIVE_SELL_CODES]

        buy_dollars = sum(max(0.0, float(t.get('total_dollars') or 0)) for t in buys)
        sell_dollars = sum(max(0.0, float(t.get('total_dollars') or 0)) for t in sells)
        net_dollars = buy_dollars - sell_dollars

        n_buys = len(buys)
        n_sells = len(sells)

        unique_buyers = len({(t.get('owner_name') or '') for t in buys if t.get('owner_name')})
        unique_sellers = len({(t.get('owner_name') or '') for t in sells if t.get('owner_name')})

        n_director_buys = 0
        n_officer_buys = 0
        n_ten_pct_buys = 0
        n_ceo_buys = 0
        n_cfo_buys = 0
        largest_single_buy = 0.0

        for t in buys:
            is_ceo, is_cfo, is_dir, is_off, is_ten, _ = classify_role(t)
            if is_ceo:
                n_ceo_buys += 1
            if is_cfo:
                n_cfo_buys += 1
            if is_dir:
                n_director_buys += 1
            if is_off:
                n_officer_buys += 1
            if is_ten:
                n_ten_pct_buys += 1
            d = float(t.get('total_dollars') or 0.0)
            if d > largest_single_buy:
                largest_single_buy = d

        # Ratios / derived
        if (n_buys + n_sells) > 0:
            buy_sell_ratio = n_buys / (n_buys + n_sells)
        else:
            buy_sell_ratio = 0.0
        multi_insider_cluster = 1 if unique_buyers >= 3 else 0

        prefix = f'f4_{w}d'
        feats[f'{prefix}_n_buys'] = n_buys
        feats[f'{prefix}_n_sells'] = n_sells
        feats[f'{prefix}_buy_dollars'] = buy_dollars
        feats[f'{prefix}_sell_dollars'] = sell_dollars
        feats[f'{prefix}_net_dollars'] = net_dollars
        feats[f'{prefix}_log1p_net_dollars'] = math.copysign(math.log1p(abs(net_dollars)), net_dollars) if net_dollars != 0 else 0.0
        feats[f'{prefix}_log1p_buy_dollars'] = math.log1p(buy_dollars)
        feats[f'{prefix}_log1p_largest_buy'] = math.log1p(largest_single_buy)
        feats[f'{prefix}_unique_buyers'] = unique_buyers
        feats[f'{prefix}_unique_sellers'] = unique_sellers
        feats[f'{prefix}_n_ceo_buys'] = n_ceo_buys
        feats[f'{prefix}_n_cfo_buys'] = n_cfo_buys
        feats[f'{prefix}_n_director_buys'] = n_director_buys
        feats[f'{prefix}_n_officer_buys'] = n_officer_buys
        feats[f'{prefix}_n_ten_pct_buys'] = n_ten_pct_buys
        feats[f'{prefix}_buy_sell_ratio'] = buy_sell_ratio
        feats[f'{prefix}_multi_insider_cluster'] = multi_insider_cluster
        feats[f'{prefix}_ceo_buy_flag'] = 1 if n_ceo_buys > 0 else 0
        feats[f'{prefix}_cfo_buy_flag'] = 1 if n_cfo_buys > 0 else 0
        feats[f'{prefix}_any_buy_flag'] = 1 if n_buys > 0 else 0
        feats[f'{prefix}_any_sell_flag'] = 1 if n_sells > 0 else 0

    # Trend feature: recent acceleration (90d buys / 365d buys)
    b90 = feats.get('f4_90d_n_buys', 0)
    b365 = feats.get('f4_365d_n_buys', 0)
    if b365 > 0:
        feats['f4_buy_accel_90_365'] = b90 / b365
    else:
        feats['f4_buy_accel_90_365'] = 0.0
    d90 = feats.get('f4_90d_net_dollars', 0.0)
    d365 = feats.get('f4_365d_net_dollars', 0.0)
    if abs(d365) > 1e-6:
        feats['f4_net_dollar_accel_90_365'] = d90 / d365
    else:
        feats['f4_net_dollar_accel_90_365'] = 0.0

    # Scoreable indicator
    feats['f4_has_any_data'] = 1 if any(
        feats.get(f'f4_{w}d_n_buys', 0) + feats.get(f'f4_{w}d_n_sells', 0) > 0 for w in WINDOWS
    ) else 0

    return feats


def main():
    # Load transactions
    print(f'[+] Loading {TXN_IN}')
    with open(TXN_IN) as f:
        ticker_txns = json.load(f)

    n_tk_with_data = sum(1 for v in ticker_txns.values() if v)
    total_txns = sum(len(v) for v in ticker_txns.values())
    print(f'    {len(ticker_txns)} tickers ({n_tk_with_data} with data), {total_txns:,} total transactions')

    # Load events
    print(f'[+] Loading {EVENT_IN}')
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
    print(f'    {len(events):,} events')

    # Compute features per event
    print(f'[+] Computing features')
    rows_out = []
    feature_columns = None
    matched_events = 0
    events_with_data = 0

    for idx, ev in enumerate(events):
        tk = ev['ticker']
        txns = ticker_txns.get(tk, [])
        if txns:
            matched_events += 1
        feats = compute_event_features(ev['event_id'], tk, ev['catalyst_date'], txns)
        if feats.get('f4_has_any_data', 0) == 1:
            events_with_data += 1
        rows_out.append(feats)

        if feature_columns is None:
            feature_columns = list(feats.keys())

        if (idx + 1) % 500 == 0:
            print(f'    {idx+1:,}/{len(events):,} events processed')

    print(f'[+] Matched events (ticker had any Form 4 data): {matched_events:,}/{len(events):,} ({100*matched_events/len(events):.1f}%)')
    print(f'[+] Events with scorable T-1 Form 4 data (any window): {events_with_data:,}/{len(events):,} ({100*events_with_data/len(events):.1f}%)')

    # Write CSV
    print(f'[+] Writing {FEAT_OUT}')
    with open(FEAT_OUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=feature_columns)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f'    {len(rows_out):,} rows × {len(feature_columns)} columns written')
    print('[DONE]')


if __name__ == '__main__':
    main()
