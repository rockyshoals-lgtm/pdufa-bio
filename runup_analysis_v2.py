"""
Comprehensive PDUFA/Phase Readout Runup Analysis — v2
Dataset: 1,451 events with daily price time series (T-120 to T+10)
Outputs: Full statistical tables for the research paper
"""
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ── Load data ──────────────────────────────────────────────────────────
print("Loading expanded price time series...")
df = pd.read_csv('price_timeseries_expanded.csv')
df['Date'] = pd.to_datetime(df['Date'], format='mixed')
df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], format='mixed')
n_events = df['event_id'].nunique()
print(f"Loaded: {n_events} events, {len(df)} price observations")
print(f"Tiers: {df.groupby('tier')['event_id'].nunique().to_dict()}")
print(f"Outcomes: {df.groupby('outcome')['event_id'].nunique().to_dict()}")

# ── Helper: compute return over window ─────────────────────────────────
def compute_window_return(event_df, entry_t, exit_t):
    """Compute return from t_days=entry_t to t_days=exit_t for one event."""
    entry_rows = event_df[(event_df['t_days'] >= entry_t - 2) & (event_df['t_days'] <= entry_t + 2)]
    exit_rows = event_df[(event_df['t_days'] >= exit_t - 2) & (event_df['t_days'] <= exit_t + 2)]

    if entry_rows.empty or exit_rows.empty:
        return np.nan

    # Take the closest to target
    entry_row = entry_rows.iloc[(entry_rows['t_days'] - entry_t).abs().argsort()[:1]]
    exit_row = exit_rows.iloc[(exit_rows['t_days'] - exit_t).abs().argsort()[:1]]

    entry_price = entry_row['Close'].values[0]
    exit_price = exit_row['Close'].values[0]

    if entry_price <= 0:
        return np.nan
    return (exit_price / entry_price - 1) * 100


# ── 1. DESCRIPTIVE STATISTICS BY TIER ──────────────────────────────────
print("\n" + "="*80)
print("SECTION 1: DESCRIPTIVE STATISTICS OF PDUFA RUNUPS")
print("="*80)

# Standard windows to analyze
WINDOWS = [
    ('T-90→T-7', -90, -7),
    ('T-90→T-5', -90, -5),
    ('T-60→T-7', -60, -7),
    ('T-60→T-14', -60, -14),
    ('T-30→T-7', -30, -7),
    ('T-30→T-5', -30, -5),
    ('T-120→T-7', -120, -7),
    ('T-120→T-5', -120, -5),
    ('T-14→T-5', -14, -5),
    ('T-14→T-7', -14, -7),
    ('T-7→T-1', -7, -1),
    ('T-5→T-1', -5, -1),
]

# Compute all event-window returns
print("\nComputing returns for all events × windows...")
event_ids = df['event_id'].unique()
results_rows = []

for i, eid in enumerate(event_ids):
    if (i + 1) % 200 == 0:
        print(f"  Processing event {i+1}/{len(event_ids)}...")
    edf = df[df['event_id'] == eid].sort_values('t_days')
    tier = edf['tier'].iloc[0]
    outcome = edf['outcome'].iloc[0]
    ticker = edf['ticker'].iloc[0]

    row = {'event_id': eid, 'tier': tier, 'outcome': outcome, 'ticker': ticker}
    for wname, entry_t, exit_t in WINDOWS:
        ret = compute_window_return(edf, entry_t, exit_t)
        row[wname] = ret
    results_rows.append(row)

results = pd.DataFrame(results_rows)
print(f"Computed returns for {len(results)} events × {len(WINDOWS)} windows")

# ── TABLE 1: Overall descriptive stats ────────────────────────────────
print("\n── TABLE 1: Overall Runup Descriptive Statistics ──")
print(f"{'Window':<18} {'N':>5} {'Mean%':>8} {'Med%':>8} {'Std%':>8} {'Hit%':>7} {'Skew':>7} {'Kurt':>7} {'t-stat':>8} {'p-val':>8}")
print("-" * 105)

for wname, _, _ in WINDOWS:
    vals = results[wname].dropna()
    n = len(vals)
    if n < 10:
        continue
    mean = vals.mean()
    med = vals.median()
    std = vals.std()
    hit = (vals > 0).mean() * 100
    skew = vals.skew()
    kurt = vals.kurtosis()
    t_stat, p_val = stats.ttest_1samp(vals, 0)
    print(f"{wname:<18} {n:>5} {mean:>8.2f} {med:>8.2f} {std:>8.2f} {hit:>6.1f}% {skew:>7.2f} {kurt:>7.2f} {t_stat:>8.3f} {p_val:>8.4f}")

# ── TABLE 2: Runup stats by ODIN tier ────────────────────────────────
print("\n── TABLE 2: Runup Returns by ODIN Tier ──")
for wname in ['T-90→T-7', 'T-60→T-14', 'T-30→T-7', 'T-120→T-7']:
    print(f"\n  Window: {wname}")
    print(f"  {'Tier':<10} {'N':>5} {'Mean%':>8} {'Med%':>8} {'Std%':>8} {'Hit%':>7} {'Sharpe':>8}")
    print("  " + "-" * 60)
    for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
        vals = results[(results['tier'] == tier)][wname].dropna()
        n = len(vals)
        if n < 5:
            continue
        mean = vals.mean()
        med = vals.median()
        std = vals.std()
        hit = (vals > 0).mean() * 100
        sharpe = mean / std if std > 0 else 0
        print(f"  {tier:<10} {n:>5} {mean:>8.2f} {med:>8.2f} {std:>8.2f} {hit:>6.1f}% {sharpe:>8.3f}")

# ── TABLE 3: By Outcome ─────────────────────────────────────────────
print("\n── TABLE 3: Runup Returns by Outcome ──")
for wname in ['T-90→T-7', 'T-60→T-14', 'T-30→T-7']:
    print(f"\n  Window: {wname}")
    print(f"  {'Outcome':<12} {'N':>5} {'Mean%':>8} {'Med%':>8} {'Std%':>8} {'Hit%':>7}")
    print("  " + "-" * 50)
    for outcome in ['APPROVAL', 'CRL']:
        vals = results[(results['outcome'] == outcome)][wname].dropna()
        n = len(vals)
        if n < 5:
            continue
        mean = vals.mean()
        med = vals.median()
        std = vals.std()
        hit = (vals > 0).mean() * 100
        print(f"  {outcome:<12} {n:>5} {mean:>8.2f} {med:>8.2f} {std:>8.2f} {hit:>6.1f}%")

# ── TABLE 4: Tier × Outcome interaction ──────────────────────────────
print("\n── TABLE 4: Mean Runup (T-90→T-7) by Tier × Outcome ──")
print(f"  {'Tier':<10} {'Approval':>12} {'CRL':>12} {'Diff':>10} {'p-val':>8}")
print("  " + "-" * 55)
for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
    app = results[(results['tier'] == tier) & (results['outcome'] == 'APPROVAL')]['T-90→T-7'].dropna()
    crl = results[(results['tier'] == tier) & (results['outcome'] == 'CRL')]['T-90→T-7'].dropna()
    if len(app) < 5 or len(crl) < 5:
        continue
    diff = app.mean() - crl.mean()
    _, p = stats.ttest_ind(app, crl, equal_var=False)
    print(f"  {tier:<10} {app.mean():>11.2f}% {crl.mean():>11.2f}% {diff:>9.2f}% {p:>8.4f}")


# ── 2. FACTOR ANALYSIS ────────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 2: FACTOR ANALYSIS — WHAT DRIVES RUNUP MAGNITUDE?")
print("="*80)

# Load enriched data to merge factor info
enriched = pd.read_csv('odin_enriched_clean.csv')
enriched_cols = ['event_id', 'therapeutic_area', 'btd', 'orphan', 'priority_review',
                 'fast_track', 'prior_crl', 'gene_therapy', 'accelerated_approval',
                 'resubmission_class', 'v1070_score']
enriched_sub = enriched[enriched_cols].copy()

merged = results.merge(enriched_sub, on='event_id', how='left')

# Factor analysis on T-90→T-7 window
target_col = 'T-90→T-7'
valid = merged.dropna(subset=[target_col])

print(f"\n── Factor Analysis on {target_col} (N={len(valid)}) ──")

# TA analysis
print(f"\n  Therapeutic Area Effects:")
print(f"  {'TA':<20} {'N':>5} {'Mean%':>8} {'Med%':>8} {'vs All':>8}")
print("  " + "-" * 50)
overall_mean = valid[target_col].mean()
for ta in valid['therapeutic_area'].value_counts().head(12).index:
    ta_vals = valid[valid['therapeutic_area'] == ta][target_col].dropna()
    if len(ta_vals) < 10:
        continue
    mean = ta_vals.mean()
    med = ta_vals.median()
    diff = mean - overall_mean
    print(f"  {str(ta):<20} {len(ta_vals):>5} {mean:>8.2f} {med:>8.2f} {diff:>+8.2f}")

# Designation effects
print(f"\n  Designation Effects on Runup:")
print(f"  {'Factor':<25} {'Yes N':>6} {'Yes Mean%':>10} {'No N':>6} {'No Mean%':>10} {'Diff':>8} {'p-val':>8}")
print("  " + "-" * 80)
for factor in ['btd', 'orphan', 'priority_review', 'fast_track', 'prior_crl', 'gene_therapy', 'accelerated_approval']:
    col = factor
    if col not in valid.columns:
        continue
    yes = valid[valid[col].astype(str).isin(['True', '1', 'true', 'Yes'])][target_col].dropna()
    no = valid[~valid[col].astype(str).isin(['True', '1', 'true', 'Yes'])][target_col].dropna()
    if len(yes) < 5 or len(no) < 5:
        continue
    diff = yes.mean() - no.mean()
    _, p = stats.ttest_ind(yes, no, equal_var=False)
    print(f"  {factor:<25} {len(yes):>6} {yes.mean():>10.2f} {len(no):>6} {no.mean():>10.2f} {diff:>+8.2f} {p:>8.4f}")

# ODIN score correlation
valid_score = valid.dropna(subset=['v1070_score'])
if len(valid_score) > 50:
    corr, p = stats.pearsonr(valid_score['v1070_score'], valid_score[target_col])
    print(f"\n  ODIN Score ↔ Runup correlation: r={corr:.3f}, p={p:.4f} (N={len(valid_score)})")

# Score quartile analysis
valid_score['score_q'] = pd.qcut(valid_score['v1070_score'], 4, labels=['Q1_low', 'Q2', 'Q3', 'Q4_high'])
print(f"\n  Runup by ODIN Score Quartile:")
print(f"  {'Quartile':<12} {'N':>5} {'Score Range':>18} {'Mean Runup%':>12} {'Med%':>8} {'Hit%':>7}")
print("  " + "-" * 65)
for q in ['Q1_low', 'Q2', 'Q3', 'Q4_high']:
    qdf = valid_score[valid_score['score_q'] == q]
    vals = qdf[target_col].dropna()
    score_min = qdf['v1070_score'].min()
    score_max = qdf['v1070_score'].max()
    hit = (vals > 0).mean() * 100
    print(f"  {q:<12} {len(vals):>5} [{score_min:.3f}, {score_max:.3f}] {vals.mean():>12.2f} {vals.median():>8.2f} {hit:>6.1f}%")


# ── 3. TIMING OPTIMIZATION ────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 3: TIMING OPTIMIZATION — OPTIMAL ENTRY/EXIT BY TIER")
print("="*80)

# Systematic grid search over entry/exit combinations
ENTRIES = [-120, -90, -60, -45, -30, -21, -14]
EXITS = [-1, -3, -5, -7, -10, -14]

print("\n── Timing Grid Search (Mean Return %) ──")
for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
    tier_data = results[results['tier'] == tier]
    tier_events = df[df['tier'] == tier]

    print(f"\n  {tier} (N={len(tier_data)} events)")

    # Compute returns for each entry/exit combo
    grid_results = []
    for entry_t in ENTRIES:
        for exit_t in EXITS:
            if entry_t >= exit_t:
                continue
            # Compute returns
            rets = []
            for eid in tier_data['event_id']:
                edf = tier_events[tier_events['event_id'] == eid].sort_values('t_days')
                if edf.empty:
                    # Fall back to full df
                    edf = df[df['event_id'] == eid].sort_values('t_days')
                ret = compute_window_return(edf, entry_t, exit_t)
                if not np.isnan(ret):
                    rets.append(ret)

            if len(rets) < 20:
                continue
            rets = np.array(rets)
            mean_ret = rets.mean()
            med_ret = np.median(rets)
            std_ret = rets.std()
            hit_rate = (rets > 0).mean()
            sharpe = mean_ret / std_ret if std_ret > 0 else 0
            # Annualize Sharpe (approximate)
            holding_days = abs(entry_t - exit_t)
            ann_factor = np.sqrt(252 / max(holding_days, 1))
            ann_sharpe = sharpe * ann_factor

            grid_results.append({
                'entry': entry_t, 'exit': exit_t,
                'n': len(rets), 'mean': mean_ret, 'median': med_ret,
                'std': std_ret, 'hit_rate': hit_rate, 'sharpe': sharpe,
                'ann_sharpe': ann_sharpe, 'holding_days': holding_days
            })

    gdf = pd.DataFrame(grid_results)
    if gdf.empty:
        print("  No valid combinations")
        continue

    # Show top 10 by Sharpe
    top = gdf.nlargest(10, 'ann_sharpe')
    print(f"  {'Entry':>6} {'Exit':>6} {'N':>5} {'Mean%':>8} {'Med%':>8} {'Hit%':>7} {'Sharpe':>8} {'Ann Shp':>8}")
    print("  " + "-" * 65)
    for _, r in top.iterrows():
        print(f"  T{int(r['entry']):>5} T{int(r['exit']):>5} {int(r['n']):>5} {r['mean']:>8.2f} {r['median']:>8.2f} {r['hit_rate']*100:>6.1f}% {r['sharpe']:>8.3f} {r['ann_sharpe']:>8.3f}")

    # Best overall
    best = gdf.loc[gdf['ann_sharpe'].idxmax()]
    print(f"  ★ OPTIMAL: T{int(best['entry'])}→T{int(best['exit'])}, Mean={best['mean']:.2f}%, Sharpe={best['ann_sharpe']:.3f}")


# ── 4. T-7→T-1 "DEAD MONEY" TEST ────────────────────────────────────
print("\n" + "="*80)
print("SECTION 4: T-7→T-1 'DEAD MONEY' HYPOTHESIS")
print("="*80)

dead_money = results['T-7→T-1'].dropna()
print(f"\n  Overall T-7→T-1: Mean={dead_money.mean():.2f}%, Med={dead_money.median():.2f}%, "
      f"Std={dead_money.std():.2f}%, Hit={( dead_money > 0).mean()*100:.1f}%")
t_stat, p_val = stats.ttest_1samp(dead_money, 0)
print(f"  t-test vs 0: t={t_stat:.3f}, p={p_val:.4f}")

for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
    vals = results[results['tier'] == tier]['T-7→T-1'].dropna()
    if len(vals) < 10:
        continue
    t, p = stats.ttest_1samp(vals, 0)
    print(f"  {tier}: Mean={vals.mean():.2f}%, Med={vals.median():.2f}%, Hit={(vals>0).mean()*100:.1f}%, t={t:.3f}, p={p:.4f}")


# ── 5. ROBUSTNESS: SUBPERIOD ANALYSIS ────────────────────────────────
print("\n" + "="*80)
print("SECTION 5: ROBUSTNESS — SUBPERIOD ANALYSIS")
print("="*80)

merged['year'] = pd.to_datetime(merged['ticker'].map(
    lambda x: x  # placeholder
), errors='coerce')

# Use catalyst date from the event_id
def extract_year(eid):
    parts = eid.split('|')
    if len(parts) >= 4:
        try:
            return int(parts[-1].split('-')[0])
        except:
            pass
    return None

results['year'] = results['event_id'].apply(extract_year)

for period_name, year_range in [('2016-2019', range(2016, 2020)),
                                  ('2020-2022', range(2020, 2023)),
                                  ('2023-2025', range(2023, 2026))]:
    period = results[results['year'].isin(year_range)]
    vals = period['T-90→T-7'].dropna()
    if len(vals) < 20:
        continue
    print(f"\n  {period_name} (N={len(vals)}):")
    print(f"    Mean={vals.mean():.2f}%, Med={vals.median():.2f}%, Hit={(vals>0).mean()*100:.1f}%")
    for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
        tv = period[period['tier'] == tier]['T-90→T-7'].dropna()
        if len(tv) >= 10:
            print(f"    {tier}: N={len(tv)}, Mean={tv.mean():.2f}%, Med={tv.median():.2f}%")


# ── 6. TAIL RISK & DISTRIBUTION ANALYSIS ─────────────────────────────
print("\n" + "="*80)
print("SECTION 6: DISTRIBUTION ANALYSIS & TAIL RISK")
print("="*80)

for wname in ['T-90→T-7', 'T-60→T-14', 'T-30→T-7']:
    vals = results[wname].dropna()
    print(f"\n  {wname} (N={len(vals)}):")
    print(f"    Percentiles: P5={vals.quantile(0.05):.1f}%, P10={vals.quantile(0.10):.1f}%, "
          f"P25={vals.quantile(0.25):.1f}%, P50={vals.quantile(0.50):.1f}%, "
          f"P75={vals.quantile(0.75):.1f}%, P90={vals.quantile(0.90):.1f}%, P95={vals.quantile(0.95):.1f}%")

    # Fat tail test (Jarque-Bera)
    jb_stat, jb_p = stats.jarque_bera(vals)
    print(f"    Jarque-Bera: stat={jb_stat:.1f}, p={jb_p:.4f} (normal if p>0.05)")
    print(f"    Skewness={vals.skew():.2f}, Kurtosis={vals.kurtosis():.2f}")

    # Extreme moves
    big_up = (vals > 50).sum()
    big_down = (vals < -30).sum()
    print(f"    Extreme moves: >+50%={big_up} ({big_up/len(vals)*100:.1f}%), <-30%={big_down} ({big_down/len(vals)*100:.1f}%)")


# ── 7. MULTIVARIATE REGRESSION ───────────────────────────────────────
print("\n" + "="*80)
print("SECTION 7: MULTIVARIATE REGRESSION — RUNUP DRIVERS")
print("="*80)

from sklearn.linear_model import LinearRegression

reg_data = merged.dropna(subset=[target_col, 'v1070_score'])

# Build features
features = {}
features['odin_score'] = reg_data['v1070_score']
features['is_tier1'] = (reg_data['tier'] == 'TIER_1').astype(int)
features['is_tier4'] = (reg_data['tier'] == 'TIER_4').astype(int)
features['is_btd'] = reg_data['btd'].astype(str).isin(['True', '1']).astype(int)
features['is_orphan'] = reg_data['orphan'].astype(str).isin(['True', '1']).astype(int)
features['is_priority'] = reg_data['priority_review'].astype(str).isin(['True', '1']).astype(int)
features['is_prior_crl'] = reg_data['prior_crl'].astype(str).isin(['True', '1']).astype(int)
features['is_gene_therapy'] = reg_data['gene_therapy'].astype(str).isin(['True', '1']).astype(int)
features['is_oncology'] = (reg_data['therapeutic_area'] == 'Oncology').astype(int)
features['is_cns'] = (reg_data['therapeutic_area'] == 'CNS').astype(int)
features['is_rare'] = (reg_data['therapeutic_area'] == 'Rare Disease').astype(int)

X = pd.DataFrame(features)
y = reg_data[target_col].values

model = LinearRegression()
model.fit(X, y)

print(f"\n  Linear Regression: R²={model.score(X, y):.4f}")
print(f"  Intercept: {model.intercept_:.3f}")
print(f"\n  {'Feature':<20} {'Coef':>10} {'|Coef|':>10}")
print("  " + "-" * 45)
for feat, coef in sorted(zip(X.columns, model.coef_), key=lambda x: abs(x[1]), reverse=True):
    print(f"  {feat:<20} {coef:>10.3f} {abs(coef):>10.3f}")


# ── SAVE ALL RESULTS ─────────────────────────────────────────────────
print("\n" + "="*80)
print("SAVING RESULTS")
print("="*80)

results.to_csv('event_metrics_expanded.csv', index=False)
merged.to_csv('event_metrics_enriched_expanded.csv', index=False)
print(f"Saved event_metrics_expanded.csv ({len(results)} rows)")
print(f"Saved event_metrics_enriched_expanded.csv ({len(merged)} rows)")

# Save summary stats as JSON for the module
import json
summary = {
    'n_events': int(n_events),
    'overall_stats': {},
    'tier_stats': {},
    'factor_effects': {},
    'optimal_windows': {}
}

for wname, _, _ in WINDOWS:
    vals = results[wname].dropna()
    if len(vals) < 10:
        continue
    summary['overall_stats'][wname] = {
        'n': int(len(vals)),
        'mean': round(float(vals.mean()), 3),
        'median': round(float(vals.median()), 3),
        'std': round(float(vals.std()), 3),
        'hit_rate': round(float((vals > 0).mean()), 3),
        'skewness': round(float(vals.skew()), 3),
    }

for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
    tier_stats = {}
    for wname, _, _ in WINDOWS:
        vals = results[results['tier'] == tier][wname].dropna()
        if len(vals) < 10:
            continue
        tier_stats[wname] = {
            'n': int(len(vals)),
            'mean': round(float(vals.mean()), 3),
            'median': round(float(vals.median()), 3),
            'hit_rate': round(float((vals > 0).mean()), 3),
            'sharpe': round(float(vals.mean() / vals.std()) if vals.std() > 0 else 0, 4),
        }
    summary['tier_stats'][tier] = tier_stats

with open('runup_analysis_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print("Saved runup_analysis_summary.json")

print("\n✓ ANALYSIS COMPLETE")
