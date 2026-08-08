"""
Expanded price fetcher — targets 600+ events for meta-quality research.
Stratified by tier, prioritizes events with known outcomes (2016-2025).
Fetches T-120 to T+10 trading day windows.
Runs in batches with checkpointing to handle yfinance rate limits.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
import time
import os
import sys

# ── Config ──────────────────────────────────────────────────────────────
TARGET_PER_TIER = {
    'TIER_1': 200,
    'TIER_2': 160,
    'TIER_3': 130,
    'TIER_4': 150,
}
TOTAL_TARGET = sum(TARGET_PER_TIER.values())  # 640
T_BEFORE = 130  # calendar days before catalyst to start
T_AFTER = 15    # calendar days after catalyst
CHECKPOINT_FILE = 'price_timeseries_expanded.csv'
ERROR_FILE = 'price_fetch_errors_expanded.csv'
BATCH_SIZE = 25  # events per batch (to avoid rate limits)
SLEEP_BETWEEN_BATCHES = 2  # seconds

def load_enriched():
    df = pd.read_csv('odin_enriched_clean.csv')
    df['cat_date_parsed'] = pd.to_datetime(df['cat_date'], format='mixed', errors='coerce')
    # Keep events with outcomes and dates from 2016-2025 (not future)
    df = df[df['outcome'].isin(['APPROVAL', 'CRL'])]
    df = df[df['cat_date_parsed'] >= '2016-01-01']
    df = df[df['cat_date_parsed'] <= '2025-12-31']
    df = df.dropna(subset=['cat_date_parsed', 'v1070_tier', 'ticker'])
    return df

def select_events(df, already_fetched_ids):
    """Stratified selection targeting 640 events, excluding already fetched."""
    selected = []
    for tier, target_n in TARGET_PER_TIER.items():
        tier_df = df[df['v1070_tier'] == tier]
        # Exclude already fetched
        tier_df = tier_df[~tier_df['event_id'].isin(already_fetched_ids)]
        # Stratify by outcome within tier
        approvals = tier_df[tier_df['outcome'] == 'APPROVAL']
        crls = tier_df[tier_df['outcome'] == 'CRL']
        # Take proportional mix
        n_app = min(len(approvals), int(target_n * 0.65))
        n_crl = min(len(crls), target_n - n_app)
        n_app = min(len(approvals), target_n - n_crl)  # adjust if CRL short

        # Sample with diversity: spread across years
        app_sample = approvals.sample(n=min(n_app, len(approvals)), random_state=42)
        crl_sample = crls.sample(n=min(n_crl, len(crls)), random_state=42)
        tier_selected = pd.concat([app_sample, crl_sample])
        selected.append(tier_selected)
        print(f"  {tier}: selected {len(tier_selected)} events ({len(app_sample)} APP, {len(crl_sample)} CRL) from {len(tier_df)} available")

    result = pd.concat(selected)
    print(f"\nTotal new events to fetch: {len(result)}")
    return result

def fetch_event_prices(row):
    """Fetch daily prices for a single event, T-130 to T+15 calendar days."""
    ticker = row['ticker']
    cat_date = row['cat_date_parsed']
    event_id = row['event_id']
    tier = row['v1070_tier']
    outcome = row['outcome']

    start = cat_date - timedelta(days=T_BEFORE)
    end = cat_date + timedelta(days=T_AFTER)

    try:
        data = yf.download(ticker, start=start.strftime('%Y-%m-%d'),
                          end=end.strftime('%Y-%m-%d'), progress=False)
        if data.empty or len(data) < 10:
            return None, f"Insufficient data ({len(data)} rows)"

        # Flatten multi-level columns if needed
        if hasattr(data.columns, 'levels') and data.columns.nlevels > 1:
            data.columns = [c[0] for c in data.columns]

        data = data.reset_index()
        data['event_id'] = event_id
        data['ticker'] = ticker
        data['catalyst_date'] = cat_date.strftime('%Y-%m-%d')
        data['tier'] = tier
        data['outcome'] = outcome

        # Compute trading days to catalyst
        trading_dates = data['Date'].sort_values().values
        cat_np = np.datetime64(cat_date)
        t_days = []
        for d in data['Date']:
            d_np = np.datetime64(d)
            if d_np <= cat_np:
                mask = (trading_dates >= d_np) & (trading_dates <= cat_np)
                t_days.append(-mask.sum() + 1)
            else:
                mask = (trading_dates > cat_np) & (trading_dates <= d_np)
                t_days.append(mask.sum())
        data['t_days'] = t_days

        # Normalize returns to T-120 (or earliest available)
        ref_mask = data['t_days'] <= -100
        if ref_mask.any():
            ref_price = data.loc[ref_mask, 'Close'].iloc[-1]
        else:
            ref_price = data['Close'].iloc[0]
        data['norm_return'] = (data['Close'] / ref_price - 1) * 100

        return data, None
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 70)
    print("EXPANDED PRICE FETCHER — Targeting 600+ events")
    print("=" * 70)

    # Load data
    df = load_enriched()
    print(f"Eligible events (2016-2025, with outcome): {len(df)}")

    # Check for existing checkpoint
    already_fetched_ids = set()
    existing_data = []
    if os.path.exists(CHECKPOINT_FILE):
        existing = pd.read_csv(CHECKPOINT_FILE)
        already_fetched_ids = set(existing['event_id'].unique())
        existing_data.append(existing)
        print(f"Checkpoint found: {len(already_fetched_ids)} events already fetched")

    # Also include data from previous session
    if os.path.exists('price_timeseries.csv'):
        old = pd.read_csv('price_timeseries.csv')
        old_ids = set(old['event_id'].unique())
        already_fetched_ids.update(old_ids)
        existing_data.append(old)
        print(f"Previous session data: {len(old_ids)} events")

    print(f"Total already fetched: {len(already_fetched_ids)}")

    # Select new events
    print("\nSelecting events by tier:")
    events = select_events(df, already_fetched_ids)

    if len(events) == 0:
        print("All events already fetched!")
        return

    # Fetch in batches
    all_results = existing_data.copy()
    errors = []
    fetched_count = len(already_fetched_ids)
    total_to_fetch = len(events)

    event_list = events.to_dict('records')

    for batch_start in range(0, len(event_list), BATCH_SIZE):
        batch = event_list[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(event_list) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n── Batch {batch_num}/{total_batches} ({batch_start+1}-{min(batch_start+BATCH_SIZE, len(event_list))}/{total_to_fetch}) ──")

        for i, row in enumerate(batch):
            ticker = row['ticker']
            event_id = row['event_id']
            sys.stdout.write(f"  [{batch_start+i+1}/{total_to_fetch}] {ticker}... ")
            sys.stdout.flush()

            data, error = fetch_event_prices(pd.Series(row))

            if data is not None:
                all_results.append(data)
                fetched_count += 1
                print(f"OK ({len(data)} rows)")
            else:
                errors.append({'event_id': event_id, 'ticker': ticker, 'error': error})
                print(f"FAIL: {error[:60]}")

        # Checkpoint after each batch
        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            combined.to_csv(CHECKPOINT_FILE, index=False)
            n_events = combined['event_id'].nunique()
            print(f"  → Checkpoint saved: {n_events} total events, {len(combined)} price rows")

        if batch_start + BATCH_SIZE < len(event_list):
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # Final save
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        # Deduplicate
        combined = combined.drop_duplicates(subset=['event_id', 'Date'], keep='last')
        combined.to_csv(CHECKPOINT_FILE, index=False)
        n_events = combined['event_id'].nunique()
        print(f"\n{'='*70}")
        print(f"FINAL: {n_events} events, {len(combined)} price observations")
        print(f"Events by tier:")
        print(combined.groupby('tier')['event_id'].nunique())

    if errors:
        pd.DataFrame(errors).to_csv(ERROR_FILE, index=False)
        print(f"\nErrors: {len(errors)} events failed (saved to {ERROR_FILE})")

if __name__ == '__main__':
    main()
