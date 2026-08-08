#!/usr/bin/env python3
"""
BIFROST v1.0 — PDUFA Runup Timing Engine
==========================================
Multi-window optimization for PDUFA catalyst entry/exit timing.
Segments by ODIN tier × market cap tier.

Pipeline:
  1. Load existing 1,705-event runup dataset
  2. Pull yfinance daily prices for wider windows (T-90 to T-1)
  3. Compute returns for all entry×exit combos
  4. Segment by ODIN tier (v9) × mcap tier (nano/micro/small/mid/large)
  5. Calculate Sharpe, hit rate, vol-adjusted returns
  6. Backtest multi-window vs buy-hold
  7. Build optimal window predictor
  8. Output enriched JSON for MCP deployment
"""

import pandas as pd
import numpy as np
import json
import math
import os
import time
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = '/sessions/loving-nifty-dirac/mnt/Python/9realms'
CACHE_FILE = os.path.join(BASE_DIR, 'bifrost_price_cache.json')
OUTPUT_JSON = os.path.join(BASE_DIR, 'bifrost_v1_deploy.json')

# ============================================================================
# STEP 1: Load existing data
# ============================================================================
print("=" * 70)
print("  BIFROST v1.0 — PDUFA RUNUP TIMING ENGINE")
print("=" * 70)

print("\n[1/7] Loading existing datasets...")
df = pd.read_csv(os.path.join(BASE_DIR, 'pdufa_runup_mcap.csv'))
df['pdufa_date'] = pd.to_datetime(df['pdufa_date'])
print(f"  Loaded: {len(df)} events ({df['pdufa_date'].min().date()} to {df['pdufa_date'].max().date()})")
print(f"  Mcap tiers: {df['mcap_tier'].value_counts().to_dict()}")
print(f"  ODIN tiers: {df['v5_tier'].value_counts().to_dict()}")

# Load BPIQ reference stats
BPIQ_STATS = {
    "pdufa": {
        "nano_cap": {"n": 142, "win_rate_t45_t7": 0.75, "median_return_t45_t7": 0.45},
        "small_cap": {"n": 105, "win_rate_t45_t7": 0.72, "median_return_t45_t7": 0.32},
    },
    "windows": {
        "t90_t60": {"nano": {"median": 0.09, "win": 0.58}, "small": {"median": 0.07, "win": 0.55}},
        "t60_t45": {"nano": {"median": 0.12, "win": 0.62}, "small": {"median": 0.09, "win": 0.60}},
        "t45_t25": {"nano": {"median": 0.22, "win": 0.68}, "small": {"median": 0.17, "win": 0.65}},
        "t25_t7":  {"nano": {"median": 0.28, "win": 0.72}, "small": {"median": 0.20, "win": 0.70}},
        "t45_t7":  {"nano": {"median": 0.42, "win": 0.75}, "small": {"median": 0.32, "win": 0.72}},
    }
}

# Load existing analysis if available
existing_analysis = {}
analysis_path = os.path.join(BASE_DIR, 'runup_analysis_summary.json')
if os.path.exists(analysis_path):
    with open(analysis_path) as f:
        existing_analysis = json.load(f)
    print(f"  Loaded existing analysis: {existing_analysis.get('n_events', '?')} events analyzed")

# ============================================================================
# STEP 2: Pull yfinance data for wider windows
# ============================================================================
print("\n[2/7] Pulling yfinance price data for multi-window analysis...")

# Load price cache if exists
price_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE) as f:
        price_cache = json.load(f)
    print(f"  Loaded {len(price_cache)} cached price series")

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    print("  WARNING: yfinance not installed. Installing...")
    import subprocess
    subprocess.run(['pip', 'install', 'yfinance', '--break-system-packages', '-q'])
    import yfinance as yf
    HAS_YFINANCE = True

def get_prices(ticker, pdufa_date, days_before=95, days_after=10):
    """Get daily prices around a PDUFA date."""
    cache_key = f"{ticker}_{pdufa_date.strftime('%Y%m%d')}"
    if cache_key in price_cache:
        return price_cache[cache_key]

    try:
        start = pdufa_date - timedelta(days=int(days_before * 1.6))  # Trading days buffer
        end = pdufa_date + timedelta(days=int(days_after * 1.6))

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'))

        if hist.empty or len(hist) < 10:
            return None

        # Convert to trading-day offsets from PDUFA date
        prices = {}
        for date, row in hist.iterrows():
            dt = date.tz_localize(None) if date.tzinfo else date
            delta = (dt - pd.Timestamp(pdufa_date)).days
            prices[str(delta)] = round(float(row['Close']), 4)

        price_cache[cache_key] = prices
        return prices
    except Exception as e:
        return None


def compute_return_from_prices(prices, entry_td, exit_td, tolerance=3):
    """Compute return from calendar-day offset prices."""
    if not prices:
        return np.nan

    # Find closest price to target trading days
    # Trading days ≈ calendar days * 5/7
    entry_cal = int(entry_td * 7 / 5)
    exit_cal = int(exit_td * 7 / 5)

    def find_closest(target_cal):
        best_key, best_dist = None, 999
        for k in prices:
            dist = abs(int(k) - target_cal)
            if dist < best_dist:
                best_dist = dist
                best_key = k
        if best_dist <= tolerance * 2:
            return float(prices[best_key])
        return None

    entry_price = find_closest(entry_cal)
    exit_price = find_closest(exit_cal)

    if entry_price and exit_price and entry_price > 0:
        return (exit_price / entry_price - 1) * 100
    return np.nan


# Define ALL entry × exit window combinations
ENTRY_POINTS = [-90, -60, -45, -25]  # Trading days before PDUFA
EXIT_POINTS = [-7, -3, -1]           # Trading days before PDUFA

WINDOW_COMBOS = []
for entry in ENTRY_POINTS:
    for exit_pt in EXIT_POINTS:
        if entry < exit_pt:  # entry must be before exit
            name = f"T{entry}_T{exit_pt}"
            WINDOW_COMBOS.append((name, entry, exit_pt))

print(f"  Window combinations to compute: {len(WINDOW_COMBOS)}")
for name, entry, exit_pt in WINDOW_COMBOS:
    print(f"    {name}: enter {entry}td, exit {exit_pt}td")

# Pull prices for all events (with rate limiting)
needs_fetch = []
for idx, row in df.iterrows():
    cache_key = f"{row['ticker']}_{row['pdufa_date'].strftime('%Y%m%d')}"
    if cache_key not in price_cache:
        needs_fetch.append(idx)

print(f"\n  Events needing price fetch: {len(needs_fetch)} / {len(df)}")
if len(needs_fetch) > 500:
    print(f"  NOTE: Large fetch. Sampling {min(500, len(needs_fetch))} events for efficiency.")
    # Prioritize 2025-2026 events and smaller caps
    priority_mask = df.index.isin(needs_fetch)
    priority_df = df[priority_mask].copy()
    # Sort: 2025+ first, then smaller mcap
    priority_df['year'] = priority_df['pdufa_date'].dt.year
    priority_df['mcap_rank'] = priority_df['mcap_tier'].map({
        'Nano (<$50M)': 0, 'Micro ($50M-$300M)': 1, 'Small ($300M-$2B)': 2,
        'Mid ($2B-$10B)': 3, 'Large (>$10B)': 4
    }).fillna(5)
    priority_df = priority_df.sort_values(['year', 'mcap_rank'], ascending=[False, True])
    needs_fetch = priority_df.index[:500].tolist()

fetched = 0
fetch_errors = 0
batch_size = 20
for i, idx in enumerate(needs_fetch):
    row = df.loc[idx]
    prices = get_prices(row['ticker'], row['pdufa_date'])
    if prices:
        fetched += 1
    else:
        fetch_errors += 1

    if (i + 1) % batch_size == 0:
        print(f"  Fetched {i+1}/{len(needs_fetch)} ({fetched} ok, {fetch_errors} errors)")
        time.sleep(0.5)  # Rate limit

print(f"  Total fetched: {fetched} ok, {fetch_errors} errors")

# Save cache
with open(CACHE_FILE, 'w') as f:
    json.dump(price_cache, f)
print(f"  Price cache saved: {len(price_cache)} entries")

# ============================================================================
# STEP 3: Compute multi-window returns for ALL events
# ============================================================================
print("\n[3/7] Computing multi-window returns...")

# Initialize return columns
for name, _, _ in WINDOW_COMBOS:
    df[name] = np.nan

# Also compute from existing shorter-window data where we have it
# Map existing columns to approximate window combos
existing_map = {
    'runup_30d': ('T-30_approx', -30),
    'runup_21d': ('T-21_approx', -21),
    'runup_14d': ('T-14_approx', -14),
    'runup_7d':  ('T-7_approx', -7),
    'runup_5d':  ('T-5_approx', -5),
    'runup_3d':  ('T-3_approx', -3),
}

computed = 0
from_cache = 0
for idx, row in df.iterrows():
    cache_key = f"{row['ticker']}_{row['pdufa_date'].strftime('%Y%m%d')}"
    prices = price_cache.get(cache_key)

    if prices:
        for name, entry, exit_pt in WINDOW_COMBOS:
            ret = compute_return_from_prices(prices, entry, exit_pt)
            df.at[idx, name] = ret
            if not np.isnan(ret):
                computed += 1
        from_cache += 1

print(f"  Computed {computed} window returns from {from_cache} cached price series")
print(f"  Coverage per window:")
for name, _, _ in WINDOW_COMBOS:
    valid = df[name].notna().sum()
    print(f"    {name}: {valid}/{len(df)} ({valid/len(df)*100:.1f}%)")

# For events without yfinance data, approximate wider windows from existing columns
# T-45 to T-7 ≈ runup_30d + some of runup_21d (rough approximation)
# We'll use what we can and mark coverage

# ============================================================================
# STEP 4: Segment by ODIN tier × mcap tier
# ============================================================================
print("\n[4/7] Segmenting by ODIN tier × mcap tier...")

# Remap mcap tiers to match BPIQ convention + add mid-cap
# Existing: Nano (<$50M), Micro ($50M-$300M), Small ($300M-$2B), Mid ($2B-$10B), Large (>$10B)
# BPIQ: nano (<$100M), small ($100M-$500M), mid ($500M-$2B)
# We'll use our existing tiers but create a BPIQ-compatible grouping too
df['mcap_group'] = df['mcap_tier'].map({
    'Nano (<$50M)': 'nano',
    'Micro ($50M-$300M)': 'micro',
    'Small ($300M-$2B)': 'small',
    'Mid ($2B-$10B)': 'mid',
    'Large (>$10B)': 'large',
})

# Map v5_tier to standard tier names
df['tier'] = df['v5_tier'].map({'T1': 'T1', 'T2': 'T2', 'T3': 'T3', 'T4': 'T4'})

# Compute stats for each tier × mcap × window combo
results = {}
for tier in ['T1', 'T2', 'T3', 'T4', 'ALL']:
    results[tier] = {}
    for mcap in ['nano', 'micro', 'small', 'mid', 'large', 'ALL']:
        results[tier][mcap] = {}

        # Filter
        if tier == 'ALL' and mcap == 'ALL':
            subset = df
        elif tier == 'ALL':
            subset = df[df['mcap_group'] == mcap]
        elif mcap == 'ALL':
            subset = df[df['tier'] == tier]
        else:
            subset = df[(df['tier'] == tier) & (df['mcap_group'] == mcap)]

        if len(subset) < 5:
            continue

        for name, entry, exit_pt in WINDOW_COMBOS:
            returns = subset[name].dropna()
            if len(returns) < 5:
                continue

            mean_ret = returns.mean()
            median_ret = returns.median()
            std_ret = returns.std()
            hit_rate = (returns > 0).mean()
            sharpe = mean_ret / std_ret if std_ret > 0 else 0

            # Vol-adjusted return (annualized Sharpe × sqrt of holding period in years)
            holding_days = abs(exit_pt - entry)
            ann_factor = math.sqrt(252 / max(holding_days, 1))
            ann_sharpe = sharpe * ann_factor

            # Skewness
            skew = returns.skew() if len(returns) >= 8 else np.nan

            # Max drawdown proxy (worst return)
            max_loss = returns.min()

            # 75th / 25th percentile
            p25 = returns.quantile(0.25)
            p75 = returns.quantile(0.75)

            results[tier][mcap][name] = {
                'n': int(len(returns)),
                'mean': round(float(mean_ret), 3),
                'median': round(float(median_ret), 3),
                'std': round(float(std_ret), 3),
                'hit_rate': round(float(hit_rate), 3),
                'sharpe': round(float(sharpe), 4),
                'ann_sharpe': round(float(ann_sharpe), 4),
                'skew': round(float(skew), 3) if not np.isnan(skew) else None,
                'max_loss': round(float(max_loss), 2),
                'p25': round(float(p25), 3),
                'p75': round(float(p75), 3),
                'holding_days': holding_days,
            }

print(f"  Computed stats for {sum(len(v2) for v1 in results.values() for v2 in v1.values())} tier×mcap×window combos")

# ============================================================================
# STEP 5: Calculate Sharpe ratios, backtest vs buy-hold
# ============================================================================
print("\n[5/7] Computing risk-adjusted metrics + backtest vs buy-hold...")

# Buy-and-hold benchmark: buy at T-45, hold through PDUFA to T+5
# This captures both runup AND binary event outcome
bh_window = 'T-45_T-1'  # Approximate buy-hold through PDUFA

# For each tier×mcap, find the OPTIMAL window
optimal_windows = {}
for tier in ['T1', 'T2', 'T3', 'T4']:
    optimal_windows[tier] = {}
    for mcap in ['nano', 'micro', 'small', 'mid', 'large']:
        if mcap not in results.get(tier, {}):
            continue

        tier_mcap_results = results[tier][mcap]
        if not tier_mcap_results:
            continue

        # Score each window by: Sharpe * sqrt(n) (reliability-weighted)
        best_score = -999
        best_window = None
        for wname, wdata in tier_mcap_results.items():
            if wdata['n'] < 10:
                continue
            # Composite score: Sharpe × hit_rate × sqrt(n) / max_loss_penalty
            score = (wdata['ann_sharpe'] * wdata['hit_rate'] * math.sqrt(wdata['n']))
            if wdata['max_loss'] < -50:
                score *= 0.7  # Penalize extreme tail risk
            if score > best_score:
                best_score = score
                best_window = wname

        if best_window:
            optimal_windows[tier][mcap] = {
                'window': best_window,
                'score': round(best_score, 3),
                'stats': tier_mcap_results[best_window],
            }

print("\n  OPTIMAL WINDOWS BY TIER × MCAP:")
print(f"  {'Tier':<5} {'Mcap':<8} {'Window':<15} {'Sharpe':<8} {'Hit%':<7} {'Mean%':<8} {'N':<5}")
print(f"  {'-'*56}")
for tier in ['T1', 'T2', 'T3', 'T4']:
    for mcap in ['nano', 'micro', 'small', 'mid', 'large']:
        if mcap in optimal_windows.get(tier, {}):
            ow = optimal_windows[tier][mcap]
            s = ow['stats']
            print(f"  {tier:<5} {mcap:<8} {ow['window']:<15} {s['ann_sharpe']:<8.3f} {s['hit_rate']*100:<6.1f}% {s['mean']:<8.2f} {s['n']:<5}")

# Compare optimal vs buy-hold
print("\n  OPTIMAL vs BUY-HOLD (T-45→T-1):")
for tier in ['T1', 'T2', 'T3', 'T4']:
    for mcap in ['nano', 'micro', 'small', 'mid', 'large']:
        if mcap not in optimal_windows.get(tier, {}):
            continue
        ow = optimal_windows[tier][mcap]
        # Get buy-hold stats if available
        bh = results.get(tier, {}).get(mcap, {}).get('T-45_T-1')
        if bh:
            alpha = ow['stats']['mean'] - bh['mean']
            sharpe_diff = ow['stats']['ann_sharpe'] - bh['ann_sharpe']
            print(f"  {tier} {mcap}: Optimal={ow['window']} ({ow['stats']['mean']:+.2f}%) vs BH ({bh['mean']:+.2f}%) → alpha={alpha:+.2f}%, Sharpe Δ={sharpe_diff:+.3f}")

# ============================================================================
# STEP 6: Build predictive entry/exit model
# ============================================================================
print("\n[6/7] Building BIFROST predictive model...")

# The model maps (odin_tier, mcap_tier, days_to_pdufa) → recommendation
# Based on empirical optimal windows from Step 5

# Build the BIFROST decision matrix
bifrost_matrix = {}

# For each tier, compute recommended action at different time horizons
for tier in ['T1', 'T2', 'T3', 'T4']:
    bifrost_matrix[tier] = {}
    for mcap in ['nano', 'micro', 'small', 'mid', 'large']:
        # Get all window stats for this tier×mcap
        tier_stats = results.get(tier, {}).get(mcap, {})
        if not tier_stats:
            bifrost_matrix[tier][mcap] = {'action': 'INSUFFICIENT_DATA', 'n': 0}
            continue

        # Find the entry/exit with best risk-adjusted return
        opt = optimal_windows.get(tier, {}).get(mcap)
        if not opt:
            bifrost_matrix[tier][mcap] = {'action': 'NO_EDGE', 'n': 0}
            continue

        # Parse optimal window
        parts = opt['window'].split('_')
        opt_entry = int(parts[0].replace('T', ''))
        opt_exit = int(parts[1].replace('T', ''))

        # Build entry/exit recommendation
        s = opt['stats']

        # Determine action and confidence
        if s['ann_sharpe'] >= 0.5 and s['hit_rate'] >= 0.55 and s['n'] >= 20:
            action = 'STRONG_BUY'
        elif s['ann_sharpe'] >= 0.3 and s['hit_rate'] >= 0.52 and s['n'] >= 15:
            action = 'BUY'
        elif s['ann_sharpe'] >= 0.15 and s['hit_rate'] >= 0.50:
            action = 'LEAN_LONG'
        elif s['hit_rate'] < 0.45:
            action = 'AVOID'
        else:
            action = 'NEUTRAL'

        bifrost_matrix[tier][mcap] = {
            'action': action,
            'optimal_entry': opt_entry,
            'optimal_exit': opt_exit,
            'window': opt['window'],
            'ann_sharpe': s['ann_sharpe'],
            'hit_rate': s['hit_rate'],
            'mean_return': s['mean'],
            'median_return': s['median'],
            'max_loss': s['max_loss'],
            'n': s['n'],
            'holding_days': s['holding_days'],
        }

# Also compute aggregate tier-level recommendations (mcap-weighted)
for tier in ['T1', 'T2', 'T3', 'T4']:
    tier_all = results.get(tier, {}).get('ALL', {})
    if not tier_all:
        continue

    # Find best window for tier overall
    best_sharpe = -999
    best_window = None
    for wname, wdata in tier_all.items():
        if wdata['n'] >= 20 and wdata['ann_sharpe'] > best_sharpe:
            best_sharpe = wdata['ann_sharpe']
            best_window = wname

    if best_window:
        s = tier_all[best_window]
        parts = best_window.split('_')
        bifrost_matrix[tier]['ALL'] = {
            'action': 'STRONG_BUY' if s['ann_sharpe'] >= 0.5 else 'BUY' if s['ann_sharpe'] >= 0.3 else 'LEAN_LONG',
            'optimal_entry': int(parts[0].replace('T', '')),
            'optimal_exit': int(parts[1].replace('T', '')),
            'window': best_window,
            'ann_sharpe': s['ann_sharpe'],
            'hit_rate': s['hit_rate'],
            'mean_return': s['mean'],
            'median_return': s['median'],
            'max_loss': s['max_loss'],
            'n': s['n'],
            'holding_days': s['holding_days'],
        }

print("\n  BIFROST DECISION MATRIX:")
print(f"  {'Tier':<5} {'Mcap':<8} {'Action':<14} {'Entry':<7} {'Exit':<6} {'Sharpe':<8} {'Hit%':<7} {'Mean%':<8} {'N':<5}")
print(f"  {'-'*68}")
for tier in ['T1', 'T2', 'T3', 'T4']:
    for mcap in ['nano', 'micro', 'small', 'mid', 'large', 'ALL']:
        m = bifrost_matrix.get(tier, {}).get(mcap, {})
        if m and m.get('action') not in ('INSUFFICIENT_DATA', 'NO_EDGE', None):
            print(f"  {tier:<5} {mcap:<8} {m['action']:<14} T{m['optimal_entry']:<5} T{m['optimal_exit']:<4} {m['ann_sharpe']:<8.3f} {m['hit_rate']*100:<6.1f}% {m['mean_return']:<8.2f} {m['n']:<5}")

# ============================================================================
# STEP 7: Output enriched JSON for MCP deployment
# ============================================================================
print("\n[7/7] Building BIFROST deploy JSON...")

deploy_config = {
    'version': '1.0.0',
    'engine': 'BIFROST',
    'description': 'PDUFA Runup Timing Engine — optimal entry/exit windows by ODIN tier × mcap',
    'built_from': f'{len(df)} PDUFA events ({df["pdufa_date"].min().date()} to {df["pdufa_date"].max().date()})',
    'window_combos': [{'name': n, 'entry': e, 'exit': x} for n, e, x in WINDOW_COMBOS],
    'bpiq_reference': BPIQ_STATS,
    'decision_matrix': bifrost_matrix,
    'tier_window_stats': {},
    'optimal_windows': optimal_windows,
    'methodology': {
        'sharpe': 'mean_return / std_return (per-window)',
        'ann_sharpe': 'sharpe * sqrt(252 / holding_days)',
        'hit_rate': 'fraction of events with positive return',
        'optimal_selection': 'max(ann_sharpe * hit_rate * sqrt(n)) with tail risk penalty',
        'action_thresholds': {
            'STRONG_BUY': 'ann_sharpe >= 0.5 AND hit_rate >= 0.55 AND n >= 20',
            'BUY': 'ann_sharpe >= 0.3 AND hit_rate >= 0.52 AND n >= 15',
            'LEAN_LONG': 'ann_sharpe >= 0.15 AND hit_rate >= 0.50',
            'AVOID': 'hit_rate < 0.45',
            'NEUTRAL': 'everything else',
        }
    },
    'core_thesis': {
        'cardinal_rule': 'Never hold through FDA decision — the runup IS the trade',
        'optimal_capture': '80-90% of gains captured by T-7 exit, 0% binary event risk',
    }
}

# Add tier-level aggregate stats
for tier in ['T1', 'T2', 'T3', 'T4', 'ALL']:
    deploy_config['tier_window_stats'][tier] = {}
    for mcap in ['nano', 'micro', 'small', 'mid', 'large', 'ALL']:
        if mcap in results.get(tier, {}) and results[tier][mcap]:
            deploy_config['tier_window_stats'][tier][mcap] = results[tier][mcap]

with open(OUTPUT_JSON, 'w') as f:
    json.dump(deploy_config, f, indent=2, default=str)
print(f"  Deploy JSON saved: {OUTPUT_JSON}")

# Also save to Odin Perfection
import shutil
dest = '/sessions/loving-nifty-dirac/mnt/Odin Perfection/bifrost_v1_deploy.json'
shutil.copy(OUTPUT_JSON, dest)
print(f"  Copied to: {dest}")

# Save enriched CSV
enriched_path = os.path.join(BASE_DIR, 'pdufa_runup_bifrost.csv')
df.to_csv(enriched_path, index=False)
print(f"  Enriched CSV saved: {enriched_path}")

print(f"\n{'='*70}")
print(f"  BIFROST v1.0 BUILD COMPLETE")
print(f"  Events: {len(df)}")
print(f"  Windows: {len(WINDOW_COMBOS)} entry×exit combos")
print(f"  Price cache: {len(price_cache)} series")
print(f"{'='*70}")
