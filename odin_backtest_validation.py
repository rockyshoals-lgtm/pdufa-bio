"""
ODIN Runup Module — Backtest Validation (Phase 3)
===================================================
Run the Runup Module on all historical 2020-2025 events and validate:

1. Do ALPHA_1 events have higher realized returns than ALPHA_3?
2. Do window recommendations match optimal historical windows?
3. Does position sizing improve risk-adjusted returns?
4. Does specialist interest predict larger runups?
5. Time-split validation: train 2020-22 / val 2023 / test 2024-25

Uses: pdufa_full_v2.csv (1,865 events with 10 return windows)
      odin_v1066_expanded_best.json (canonical POA weights)
      odin_runup_module.py (scoring functions)
      odin_orchestrator.py (POA scorer)

HONEST EVALUATION: No peeking at test set during development.
"""

import pandas as pd
import numpy as np
import json
from collections import defaultdict

from odin_orchestrator import score_poa, load_canonical_config
from odin_runup_module import (
    score_runup_event, runup_to_dict, RunupResult,
    classify_revenue_tier, classify_mcap_cohort, classify_price_cohort,
    is_specialist_interest, designation_boost_score,
    TA_RUNUP_QUALITY,
)
from odin_live_scorer import estimate_peak_sales


def load_dataset():
    df = pd.read_csv("pdufa_full_v2.csv")
    df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
    df['year'] = df['catalyst_date'].dt.year
    # Only events with price data
    df = df.dropna(subset=['ret_T-25_T-7'])
    print(f"Loaded {len(df)} events with T-25→T-7 returns")
    return df


def score_event_for_backtest(row: pd.Series) -> dict:
    """Score a single historical event through the full pipeline (offline mode)."""
    event = row.to_dict()

    # POA
    poa = score_poa(event)

    # Revenue estimate (basic — no market cap override in historical data)
    mcap = row.get('market_cap') if pd.notna(row.get('market_cap')) else None
    peak_est = estimate_peak_sales(event)
    peak_sales = peak_est['peak_sales']

    revenue = None
    if mcap and mcap > 0 and peak_sales > 0:
        revenue = {
            'peak_sales': peak_sales,
            'market_cap': mcap,
            'ratio': peak_sales / mcap,
            'tier': classify_revenue_tier(peak_sales, mcap)['tier'],
            'multiplier': classify_revenue_tier(peak_sales, mcap)['multiplier'],
        }

    # Market data from price cache columns
    market_data = None
    p_t30 = row.get('price_t30')
    p_t25 = row.get('price_t25')
    p_t7 = row.get('price_t7')
    if pd.notna(p_t30) and pd.notna(p_t25) and p_t30 > 0:
        market_data = {
            'price_current': float(p_t25) if pd.notna(p_t25) else float(p_t30),
            'price_t30': float(p_t30),
            'price_t60': float(row.get('price_t60', p_t30)) if pd.notna(row.get('price_t60')) else float(p_t30),
            'spy_return_30d': 0.0,  # Not computing SPY relative for backtest
        }

    # Score
    runup = score_runup_event(
        event=event,
        poa_result=poa,
        revenue_result=revenue,
        market_data=market_data,
        options_data=None,
        smart_money_data=None,
        base_position=10000.0,
        regime='NORMAL',
    )

    return {
        'poa_prob': poa['probability'],
        'poa_tier': poa['tier'],
        'alpha_score': runup.alpha_score,
        'alpha_tier': runup.alpha_tier,
        'window_name': runup.window_name,
        'entry_day': runup.entry_day,
        'exit_day': runup.exit_day,
        'expected_return_low': runup.expected_return_low,
        'expected_return_high': runup.expected_return_high,
        'position_multiplier': runup.position_multiplier,
        'specialist_interest': runup.specialist_interest,
        'confidence': runup.confidence,
        'revenue_tier': runup.revenue_tier,
    }


def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    """Score all events and merge results."""
    print(f"\nScoring {len(df)} events...")
    results = []
    for i, (idx, row) in enumerate(df.iterrows()):
        try:
            r = score_event_for_backtest(row)
            results.append(r)
        except Exception as e:
            results.append({
                'poa_prob': None, 'poa_tier': None,
                'alpha_score': None, 'alpha_tier': None,
                'window_name': None, 'entry_day': None, 'exit_day': None,
                'expected_return_low': None, 'expected_return_high': None,
                'position_multiplier': None, 'specialist_interest': None,
                'confidence': None, 'revenue_tier': None,
            })
        if (i + 1) % 200 == 0:
            print(f"  Scored {i+1}/{len(df)}")

    results_df = pd.DataFrame(results, index=df.index)
    merged = pd.concat([df, results_df], axis=1)
    print(f"  Done. {merged['alpha_score'].notna().sum()} scored successfully.")
    return merged


def analyze_by_group(df, group_col, return_col='ret_T-25_T-7', min_n=10):
    """Compute return stats grouped by a column."""
    rows = []
    for val, grp in df.groupby(group_col):
        rets = grp[return_col].dropna()
        if len(rets) < min_n:
            continue
        rows.append({
            'group': val,
            'N': len(rets),
            'mean': rets.mean(),
            'median': rets.median(),
            'std': rets.std(),
            'wr': (rets > 0).mean(),
            'p_20pct': (rets >= 0.20).mean(),
            'sharpe': rets.mean() / rets.std() if rets.std() > 0 else 0,
        })
    return pd.DataFrame(rows).sort_values('mean', ascending=False)


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    # Load
    df = load_dataset()

    # Score all events
    scored = run_backtest(df)

    # Filter to scored events only
    s = scored[scored['alpha_score'].notna()].copy()
    print(f"\n{len(s)} events with valid scores")

    # Also create price-based cohorts for nano analysis
    s['price_cohort'] = 'UNKNOWN'
    mask_nano = s['price_t25'].notna() & (s['price_t25'] <= 10)
    mask_micro = s['price_t25'].notna() & (s['price_t25'] > 10) & (s['price_t25'] <= 20)
    mask_small = s['price_t25'].notna() & (s['price_t25'] > 20) & (s['price_t25'] <= 50)
    mask_mid = s['price_t25'].notna() & (s['price_t25'] > 50)
    s.loc[mask_nano, 'price_cohort'] = 'NANO'
    s.loc[mask_micro, 'price_cohort'] = 'MICRO'
    s.loc[mask_small, 'price_cohort'] = 'SMALL'
    s.loc[mask_mid, 'price_cohort'] = 'MID+'

    # Time splits
    s_train = s[s['year'].between(2020, 2022)]
    s_val = s[s['year'] == 2023]
    s_test = s[s['year'].between(2024, 2025)]

    # ==============================================================
    # TEST 1: Alpha Tier → Realized Returns (THE KEY VALIDATION)
    # ==============================================================
    print_section("TEST 1: ALPHA TIER → REALIZED RETURNS (T-25→T-7)")

    for label, subset in [("ALL", s), ("NANO <$10", s[mask_nano])]:
        print(f"\n--- {label} ---")
        at = analyze_by_group(subset, 'alpha_tier', 'ret_T-25_T-7', min_n=5)
        for _, r in at.iterrows():
            print(f"  {r['group']:10s}  N={r['N']:4.0f}  Mean={r['mean']:+7.2%}  "
                  f"Med={r['median']:+7.2%}  WR={r['wr']:5.1%}  Sharpe={r['sharpe']:.3f}")

    # ==============================================================
    # TEST 2: Alpha Tier vs Different Windows
    # ==============================================================
    print_section("TEST 2: ALPHA TIER × WINDOW PERFORMANCE")

    windows = ['ret_T-60_T-7', 'ret_T-30_T-7', 'ret_T-25_T-7', 'ret_T-18_T-7', 'ret_T-7_T-1']
    wnames = ['T-60→T-7', 'T-30→T-7', 'T-25→T-7', 'T-18→T-7', 'T-7→T-1']
    nano = s[mask_nano]

    for tier in ['ALPHA_1', 'ALPHA_2', 'ALPHA_3', 'ALPHA_4']:
        subset = nano[nano['alpha_tier'] == tier]
        if len(subset) < 5:
            continue
        print(f"\n  {tier} (N={len(subset)}):")
        for wc, wn in zip(windows, wnames):
            rets = subset[wc].dropna()
            if len(rets) < 5:
                continue
            print(f"    {wn:12s}  Mean={rets.mean():+7.2%}  Med={rets.median():+7.2%}  WR={( rets > 0).mean():5.1%}")

    # ==============================================================
    # TEST 3: Specialist Interest → Runup Magnitude
    # ==============================================================
    print_section("TEST 3: SPECIALIST INTEREST → RUNUP (T-25→T-7)")

    for label, subset in [("ALL", s), ("NANO <$10", nano)]:
        print(f"\n--- {label} ---")
        spec = analyze_by_group(subset, 'specialist_interest', 'ret_T-25_T-7', min_n=10)
        for _, r in spec.iterrows():
            lbl = "SPECIALIST" if r['group'] else "NON-SPEC"
            print(f"  {lbl:12s}  N={r['N']:4.0f}  Mean={r['mean']:+7.2%}  "
                  f"Med={r['median']:+7.2%}  WR={r['wr']:5.1%}  Sharpe={r['sharpe']:.3f}")

    # ==============================================================
    # TEST 4: ODIN Tier → Realized Returns
    # ==============================================================
    print_section("TEST 4: ODIN TIER → RUNUP (T-25→T-7)")

    for label, subset in [("ALL", s), ("NANO <$10", nano)]:
        print(f"\n--- {label} ---")
        tiers = analyze_by_group(subset, 'poa_tier', 'ret_T-25_T-7', min_n=10)
        for _, r in tiers.iterrows():
            print(f"  {r['group']:10s}  N={r['N']:4.0f}  Mean={r['mean']:+7.2%}  "
                  f"Med={r['median']:+7.2%}  WR={r['wr']:5.1%}  Sharpe={r['sharpe']:.3f}")

    # ==============================================================
    # TEST 5: Revenue Tier → Runup Magnitude
    # ==============================================================
    print_section("TEST 5: REVENUE TIER → RUNUP (T-25→T-7)")

    rev = analyze_by_group(s, 'revenue_tier', 'ret_T-25_T-7', min_n=10)
    for _, r in rev.iterrows():
        print(f"  {r['group']:5s}  N={r['N']:4.0f}  Mean={r['mean']:+7.2%}  "
              f"Med={r['median']:+7.2%}  WR={r['wr']:5.1%}  Sharpe={r['sharpe']:.3f}")

    # ==============================================================
    # TEST 6: Confidence → Realized Returns
    # ==============================================================
    print_section("TEST 6: CONFIDENCE LEVEL → RUNUP (T-25→T-7)")

    conf = analyze_by_group(s, 'confidence', 'ret_T-25_T-7', min_n=10)
    for _, r in conf.iterrows():
        print(f"  {r['group']:10s}  N={r['N']:4.0f}  Mean={r['mean']:+7.2%}  "
              f"Med={r['median']:+7.2%}  WR={r['wr']:5.1%}  Sharpe={r['sharpe']:.3f}")

    # ==============================================================
    # TEST 7: Position-Weighted Returns
    # ==============================================================
    print_section("TEST 7: POSITION-WEIGHTED vs EQUAL-WEIGHT RETURNS")

    for label, subset in [("ALL", s), ("NANO <$10", nano)]:
        ret = subset['ret_T-25_T-7'].dropna()
        pos = subset.loc[ret.index, 'position_multiplier'].fillna(1.0)
        eq_mean = ret.mean()
        pw_mean = (ret * pos).sum() / pos.sum() if pos.sum() > 0 else 0

        # Exclude TIER_4 (NO_TRADE)
        tradeable = subset[subset['poa_tier'] != 'TIER_4']
        ret_t = tradeable['ret_T-25_T-7'].dropna()
        pos_t = tradeable.loc[ret_t.index, 'position_multiplier'].fillna(1.0)
        eq_t = ret_t.mean()
        pw_t = (ret_t * pos_t).sum() / pos_t.sum() if pos_t.sum() > 0 else 0

        print(f"\n--- {label} ---")
        print(f"  All events:      EW={eq_mean:+7.2%}  PW={pw_mean:+7.2%}  Lift={pw_mean - eq_mean:+7.2%}")
        print(f"  Tradeable only:  EW={eq_t:+7.2%}  PW={pw_t:+7.2%}  Lift={pw_t - eq_t:+7.2%}")

    # ==============================================================
    # TEST 8: TIME-SPLIT VALIDATION (Honest 3-way)
    # ==============================================================
    print_section("TEST 8: TIME-SPLIT VALIDATION (Train/Val/Test)")

    for label, subset in [("ALL", s), ("NANO <$10", nano)]:
        print(f"\n--- {label} ---")
        for split_name, split_df in [("Train 2020-22", s_train), ("Val 2023", s_val), ("Test 2024-25", s_test)]:
            sub = split_df if label == "ALL" else split_df[split_df['price_t25'].notna() & (split_df['price_t25'] <= 10)]
            if len(sub) < 10:
                print(f"  {split_name:15s}  N={len(sub)} (too small)")
                continue

            # Alpha tier monotonicity check
            a1 = sub[sub['alpha_tier'] == 'ALPHA_1']['ret_T-25_T-7'].dropna()
            a2 = sub[sub['alpha_tier'] == 'ALPHA_2']['ret_T-25_T-7'].dropna()
            a3 = sub[sub['alpha_tier'].isin(['ALPHA_3', 'ALPHA_4'])]['ret_T-25_T-7'].dropna()

            mono = "N/A"
            if len(a1) >= 3 and len(a3) >= 3:
                mono = "✅ YES" if a1.mean() > a3.mean() else "❌ NO"

            all_ret = sub['ret_T-25_T-7'].dropna()
            print(f"  {split_name:15s}  N={len(all_ret):4d}  Mean={all_ret.mean():+7.2%}  "
                  f"WR={(all_ret>0).mean():5.1%}  A1>A3_4: {mono}  "
                  f"[A1={a1.mean():+.1%} n={len(a1)}, A2={a2.mean():+.1%} n={len(a2)}, A3_4={a3.mean():+.1%} n={len(a3)}]")

    # ==============================================================
    # TEST 9: TA Quality Score → Realized Returns
    # ==============================================================
    print_section("TEST 9: TA QUALITY SCORE → RUNUP (T-25→T-7, NANO)")

    ta_groups = analyze_by_group(nano, 'therapeutic_area', 'ret_T-25_T-7', min_n=5)
    ta_groups['ta_quality'] = ta_groups['group'].map(TA_RUNUP_QUALITY).fillna(0.45)
    ta_groups = ta_groups.sort_values('ta_quality', ascending=False)
    for _, r in ta_groups.iterrows():
        q = TA_RUNUP_QUALITY.get(r['group'], 0.45)
        print(f"  {r['group']:25s}  Q={q:.2f}  N={r['N']:3.0f}  "
              f"Mean={r['mean']:+7.2%}  Med={r['median']:+7.2%}  Sharpe={r['sharpe']:.3f}")

    # Correlation: TA quality score vs realized mean return
    ta_merged = ta_groups[['group', 'mean', 'ta_quality']].dropna()
    if len(ta_merged) >= 3:
        corr = ta_merged['ta_quality'].corr(ta_merged['mean'])
        print(f"\n  Correlation (TA Quality vs Mean Return): {corr:.3f}")

    # ==============================================================
    # TEST 10: Dead Money Validation (T-7→T-1)
    # ==============================================================
    print_section("TEST 10: DEAD MONEY VALIDATION (T-7→T-1 vs T-25→T-7)")

    for label, subset in [("ALL", s), ("NANO <$10", nano)]:
        r25 = subset['ret_T-25_T-7'].dropna()
        r7 = subset['ret_T-7_T-1'].dropna()
        print(f"\n--- {label} ---")
        print(f"  T-25→T-7:  Mean={r25.mean():+7.2%}  Med={r25.median():+7.2%}  WR={(r25>0).mean():5.1%}")
        print(f"  T-7→T-1:   Mean={r7.mean():+7.2%}  Med={r7.median():+7.2%}  WR={(r7>0).mean():5.1%}")
        print(f"  Difference: {r25.mean() - r7.mean():+7.2%} (T-25→T-7 better)")

    # ==============================================================
    # SUMMARY
    # ==============================================================
    print_section("VALIDATION SUMMARY")

    # Check key conditions
    checks = []

    # 1. Alpha monotonicity (overall)
    a1_all = s[s['alpha_tier'] == 'ALPHA_1']['ret_T-25_T-7'].dropna().mean()
    a3_all = s[s['alpha_tier'].isin(['ALPHA_3', 'ALPHA_4'])]['ret_T-25_T-7'].dropna().mean()
    c1 = a1_all > a3_all
    checks.append(("Alpha monotonicity (A1 > A3_4)", c1, f"A1={a1_all:+.2%} vs A3_4={a3_all:+.2%}"))

    # 2. Specialist lift
    spec_yes = s[s['specialist_interest'] == True]['ret_T-25_T-7'].dropna().mean()
    spec_no = s[s['specialist_interest'] == False]['ret_T-25_T-7'].dropna().mean()
    c2 = spec_yes > spec_no
    checks.append(("Specialist > Non-specialist", c2, f"Spec={spec_yes:+.2%} vs Non={spec_no:+.2%}"))

    # 3. Dead money confirmed
    dm_25 = s['ret_T-25_T-7'].dropna().mean()
    dm_7 = s['ret_T-7_T-1'].dropna().mean()
    c3 = dm_25 > dm_7
    checks.append(("T-25→T-7 beats T-7→T-1", c3, f"T25T7={dm_25:+.2%} vs T7T1={dm_7:+.2%}"))

    # 4. Position weighting improves
    tradeable = s[s['poa_tier'] != 'TIER_4']
    ret_t = tradeable['ret_T-25_T-7'].dropna()
    pos_t = tradeable.loc[ret_t.index, 'position_multiplier'].fillna(1.0)
    ew = ret_t.mean()
    pw = (ret_t * pos_t).sum() / pos_t.sum() if pos_t.sum() > 0 else 0
    c4 = pw > ew
    checks.append(("Position weighting helps", c4, f"PW={pw:+.2%} vs EW={ew:+.2%}"))

    # 5. Test set positive
    test_ret = s_test['ret_T-25_T-7'].dropna().mean()
    c5 = test_ret > 0
    checks.append(("Test set (2024-25) positive", c5, f"Mean={test_ret:+.2%}"))

    for desc, passed, detail in checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {desc}: {detail}")

    passed_count = sum(1 for _, p, _ in checks if p)
    print(f"\n  RESULT: {passed_count}/{len(checks)} checks passed")

    # Save scored dataset
    scored_path = "backtest_scored_full.csv"
    scored_cols = ['event_id', 'ticker', 'company', 'asset', 'indication',
                   'therapeutic_area', 'catalyst_date', 'outcome', 'year',
                   'price_t25', 'market_cap',
                   'ret_T-60_T-7', 'ret_T-30_T-7', 'ret_T-25_T-7', 'ret_T-18_T-7', 'ret_T-7_T-1',
                   'poa_prob', 'poa_tier',
                   'alpha_score', 'alpha_tier', 'window_name',
                   'position_multiplier', 'specialist_interest', 'confidence',
                   'revenue_tier']
    existing = [c for c in scored_cols if c in s.columns]
    s[existing].to_csv(scored_path, index=False)
    print(f"\n  Saved scored dataset: {scored_path} ({len(s)} events)")

    return s


if __name__ == '__main__':
    main()
