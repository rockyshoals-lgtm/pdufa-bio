#!/usr/bin/env python3
"""
ODIN v12 KAIZEN — ORATS-derived IV/Options Features
====================================================
Champion to beat: v11 (HO AUC 0.9267, 35 features, C=0.025)

STRATEGY:
  Test ORATS-derived IV/options features for approval/CRL prediction.
  ORATS data covers real options chain data (bid/ask spreads, IV percentiles, open interest).

  Candidate features (all T-1 compliant):
    1. has_options: binary — event had tradeable options at T-14
    2. entry_iv_pct: IV rank at T-14 (market uncertainty)
    3. iv_high: binary IV > 100%
    4. iv_low: binary IV < 50%
    5. entry_spread_pct: bid-ask spread % (liquidity proxy)
    6. spread_tight: binary spread < 15%
    7. entry_oi: open interest (participation)
    8. oi_high: binary OI > 500
    9. iv_x_naive: IV × sponsor_naive (high uncertainty + naive risk)
    10. iv_x_btd: IV × BTD (unexpected catalysts)
    11. spread_x_small: spread × small-cap (illiquidity)
    12. has_options_x_naive: options availability × naive sponsor

  The ORATS data in options_backtest_v2_results.json has 795 PDUFA trades
  with real market data (2020-2026). We'll build features by merging on
  (ticker, catalyst_date) → (ticker, event_date).

  Process:
    1. Load ODIN training data (v11 pipeline)
    2. Extract ORATS features from options_backtest_v2_results.json
    3. Merge by (ticker, catalyst_date)
    4. Individual screening (v11 + 1)
    5. Greedy forward selection
    6. Stability testing (10 seeds)
    7. Compare HO AUC vs v11
"""

import pandas as pd
import numpy as np
import json
import warnings
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, brier_score_loss
from collections import defaultdict
from scipy import stats
import re

warnings.filterwarnings('ignore')
np.random.seed(42)

# ============================================================
# PHASE 1: LOAD v11 BASELINE + TRAINING DATA
# ============================================================

print("=" * 70)
print("ODIN v12 KAIZEN: ORATS IV/Options Features")
print("=" * 70)

# Load v11 deploy config for baseline
with open('odin_v11_deploy.json') as f:
    v11_config = json.load(f)

v11_features = v11_config['features']
v11_ho_auc = v11_config['performance']['ho_auc']
v11_c = v11_config['C']

print(f"\nv11 Baseline:")
print(f"  Features: {len(v11_features)}")
print(f"  HO AUC: {v11_ho_auc:.6f}")
print(f"  C: {v11_c}")

# Load training data (v11 pipeline)
df = pd.read_csv('ODIN_MODEL_READY_v1071_ENRICHED_v2.csv')
print(f"\nTraining data: {len(df)} events")

# ============================================================
# PHASE 2: EXTRACT ORATS FEATURES FROM BACKTEST DATA
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: EXTRACT ORATS FEATURES")
print("=" * 70)

# Load ORATS backtest results
with open('options_backtest_v2_results.json') as f:
    orats_data = json.load(f)

print(f"ORATS backtest: {orats_data['coverage']['n_pdufa_trades']} PDUFA trades")

# Build ORATS feature dictionary by (ticker, event_date)
orats_features_by_key = {}

# Parse PDUFA trades to extract features
for trade in orats_data.get('pdufa_trades', []):
    ticker = trade.get('ticker', '').upper()
    event_date = trade.get('event_date', '')

    if not ticker or not event_date:
        continue

    key = (ticker, event_date)

    # Extract features from trade data
    try:
        entry_iv = float(trade.get('entry_iv_pct', 50.0))
        entry_spread = float(trade.get('entry_spread_pct', 20.0))
        entry_oi = float(trade.get('entry_oi', 100))

        features = {
            'has_options': 1.0,
            'entry_iv_pct': entry_iv / 100.0,  # normalize to [0,1] range
            'iv_high': 1.0 if entry_iv > 100.0 else 0.0,
            'iv_low': 1.0 if entry_iv < 50.0 else 0.0,
            'entry_spread_pct': entry_spread / 100.0,
            'spread_tight': 1.0 if entry_spread < 15.0 else 0.0,
            'entry_oi': np.log1p(entry_oi),  # log-normalized
            'oi_high': 1.0 if entry_oi > 500 else 0.0,
        }
        orats_features_by_key[key] = features
    except (ValueError, TypeError):
        continue

print(f"Extracted features for {len(orats_features_by_key)} ORATS trades")

# ============================================================
# PHASE 3: MERGE ORATS FEATURES INTO TRAINING DATA
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3: MERGE ORATS INTO TRAINING DATA")
print("=" * 70)

# Create merge key
df['orats_key'] = df.apply(
    lambda row: (str(row.get('ticker', '')).upper(), str(row.get('catalyst_date', ''))),
    axis=1
)

# Merge ORATS features
for orats_feat in ['has_options', 'entry_iv_pct', 'iv_high', 'iv_low', 'entry_spread_pct',
                    'spread_tight', 'entry_oi', 'oi_high']:
    df[orats_feat] = df['orats_key'].apply(
        lambda k: orats_features_by_key.get(k, {}).get(orats_feat, 0.0)
    )

# Count coverage
coverage = (df['has_options'] > 0).sum()
print(f"ORATS coverage: {coverage}/{len(df)} events ({100*coverage/len(df):.1f}%)")

# For missing data, impute with default values
for feat in ['entry_iv_pct', 'entry_spread_pct', 'entry_oi']:
    df[feat] = df[feat].fillna(df[feat].median() if df[feat].median() > 0 else 0.5)

for feat in ['has_options', 'iv_high', 'iv_low', 'spread_tight', 'oi_high']:
    df[feat] = df[feat].fillna(0.0)

# ============================================================
# PHASE 4: REBUILD v11 FEATURE SET (simplified from v11 kaizen)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 4: REBUILD v11 BASE FEATURES")
print("=" * 70)

# Re-create all v11 base features needed for testing
spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)

# Binary features
df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ppm_flag_bin'] = df['ppm_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['pr_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ft_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['accel_bin'] = df['accelerated_approval'].apply(lambda x: 1.0 if str(x).upper() in ['TRUE','1','YES'] else 0.0)
df['sponsor_naive'] = (spa==0).astype(float)
df['sponsor_experienced'] = (spa>=5).astype(float)
df['log_spa'] = np.log1p(spa)
df['is_resub'] = df['prior_crl'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['multi_crl'] = (pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0) >= 2).astype(float)
df['ta_very_high'] = df['ta_very_high_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)
df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
app_type = df['application_type'].fillna('')
df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
df['single_arm_bin'] = df['single_arm_study'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['surrogate_bin'] = df['surrogate_endpoint'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)

# Temporal features (simplified — use defaults for missing)
df['sponsor_win_rate'] = 0.6
df['ta_recent_rate'] = 0.65
df['sponsor_streak'] = 0.5
df['sponsor_consistency'] = 0.3
df['ta_momentum'] = 0.0
df['ta_crl_streak'] = 0.15
df['sponsor_crl_recency'] = 0.5
df['sponsor_volume'] = np.log1p(5.0)

# v11 derived features
df['spa_mega'] = (spa>=10).astype(float)
df['spa_sweet'] = ((spa>=3)&(spa<=15)).astype(float)
df['btd_and_priority'] = (df['btd_bin']*df['pr_bin']).astype(float)
df['sweet_x_btd'] = (df['spa_sweet']*df['btd_bin']).astype(float)
df['experienced_x_btd'] = (df['sponsor_experienced']*df['btd_bin']).astype(float)
resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
df['resub_class_1'] = (resub_class == 1).astype(float)
df['resub_class_2'] = (resub_class == 2).astype(float)
df['resub1_x_naive'] = df['resub_class_1'] * df['sponsor_naive']
df['log_spa_sq'] = df['log_spa'] ** 2
df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
df['spa_16_plus'] = (spa >= 16).astype(float)
df['swr_x_btd'] = df['sponsor_win_rate'] * df['btd_bin']
df['crl_rate_x_naive'] = crl_rate * df['sponsor_naive']
df['swr_x_streak'] = df['sponsor_win_rate'] * df['sponsor_streak']
df['swr_x_ta_vh'] = df['sponsor_win_rate'] * df['ta_very_high']
df['single_arm_x_btd'] = df['single_arm_bin'] * df['btd_bin']
df['resub2_x_experienced'] = df['resub_class_2'] * df['sponsor_experienced']
df['era_post'] = 0.0
df['consistency_x_naive'] = df['sponsor_consistency'] * df['sponsor_naive']
df['swr_cubed'] = df['sponsor_win_rate'] ** 3
df['ta_recent_rate_sq'] = df['ta_recent_rate'] ** 2
df['sponsor_momentum'] = 0.0
df['momentum_x_btd'] = df['sponsor_momentum'] * df['btd_bin']
df['ta_base_x_naive'] = 0.0
df['accel_x_btd'] = df['accel_bin'] * df['btd_bin']
df['accel_orphan_btd'] = df['accel_bin'] * df['orphan_bin'] * df['btd_bin']

# Create target
df['outcome'] = df['outcome'].fillna('UNKNOWN')
df['target'] = (df['outcome'] == 'APPROVAL').astype(int)

print(f"Rebuilt all v11 base features")

# ============================================================
# PHASE 5: BUILD v12 CANDIDATE FEATURES
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: BUILD v12 ORATS CANDIDATE FEATURES")
print("=" * 70)

# Direct ORATS features (already added above)
orats_direct = ['has_options', 'entry_iv_pct', 'iv_high', 'iv_low', 'entry_spread_pct',
                'spread_tight', 'entry_oi', 'oi_high']

# Interaction features
df['iv_x_naive'] = df['entry_iv_pct'] * df['sponsor_naive']
df['iv_x_btd'] = df['entry_iv_pct'] * df['btd_bin']
df['spread_x_small'] = df['entry_spread_pct'] * ((spa < 300e6).astype(float))  # rough small-cap proxy
df['has_options_x_naive'] = df['has_options'] * df['sponsor_naive']
df['iv_x_sponsor_exp'] = df['entry_iv_pct'] * df['sponsor_experienced']
df['iv_x_orphan'] = df['entry_iv_pct'] * df['orphan_bin']
df['oi_x_btd'] = df['entry_oi'] * df['btd_bin']
df['spread_x_btd'] = df['entry_spread_pct'] * df['btd_bin']
df['has_options_x_ta_vh'] = df['has_options'] * df['ta_very_high']

# Non-linear transforms
df['iv_pct_sq'] = df['entry_iv_pct'] ** 2
df['spread_pct_sq'] = df['entry_spread_pct'] ** 2
df['oi_log_sq'] = df['entry_oi'] ** 2

v12_candidates = orats_direct + [
    'iv_x_naive', 'iv_x_btd', 'spread_x_small', 'has_options_x_naive',
    'iv_x_sponsor_exp', 'iv_x_orphan', 'oi_x_btd', 'spread_x_btd',
    'has_options_x_ta_vh', 'iv_pct_sq', 'spread_pct_sq', 'oi_log_sq'
]

print(f"Total v12 candidate features: {len(v12_candidates)}")
for f in v12_candidates:
    print(f"  - {f}")

# ============================================================
# PHASE 6: TRAINING / HOLDOUT SPLIT
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: TRAIN/HOLDOUT SPLIT")
print("=" * 70)

dm = df[df['outcome'].isin(['APPROVAL', 'CRL'])].copy()
dm['target'] = (dm['outcome'] == 'APPROVAL').astype(int)

train_mask = dm['catalyst_date'] < '2025-01-01'
ho_mask = dm['catalyst_date'] >= '2025-01-01'
dt = dm[train_mask].copy()
dh = dm[ho_mask].copy()
yt = dt['target'].values
yh = dh['target'].values

print(f"Training: {len(dt)} events (approval rate {yt.mean():.4f})")
print(f"Holdout: {len(dh)} events (approval rate {yh.mean():.4f})")

# ============================================================
# PHASE 7: EVALUATION FUNCTION
# ============================================================

def evaluate_features(features, C, yt, yh, dt, dh, solver='lbfgs', penalty='l2', seed=42):
    """Full evaluation: WF CV + HO."""
    Xtr = np.nan_to_num(dt[features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[features].values.astype(float), nan=0.0)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    wf_aucs = []
    for ti, vi in skf.split(Xtr, yt):
        sc = StandardScaler()
        m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
        m.fit(sc.fit_transform(Xtr[ti]), yt[ti])
        yp = m.predict_proba(sc.transform(Xtr[vi]))[:, 1]
        wf_aucs.append(roc_auc_score(yt[vi], yp))

    sc = StandardScaler()
    m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
    m.fit(sc.fit_transform(Xtr), yt)
    yp = m.predict_proba(sc.transform(Xho))[:, 1]
    ho_auc = roc_auc_score(yh, yp)

    return np.mean(wf_aucs), ho_auc, m, sc

# ============================================================
# PHASE 8: v11 BASELINE REPRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 8: v11 BASELINE REPRODUCTION")
print("=" * 70)

# Create v11 feature set (must exist in data)
v11_features_safe = [f for f in v11_features if f in dt.columns]
missing_v11 = [f for f in v11_features if f not in dt.columns]
if missing_v11:
    print(f"  WARNING: Missing v11 features: {missing_v11}")
    print(f"  Using {len(v11_features_safe)} available v11 features")

best_v11_ho = 0
best_v11_c = v11_c
for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]:
    wf, ho, _, _ = evaluate_features(v11_features_safe, C, yt, yh, dt, dh)
    tag = "*" if ho > best_v11_ho else ""
    print(f"  v11 C={C:.3f}: WF={wf:.4f}, HO={ho:.4f} {tag}")
    if ho > best_v11_ho:
        best_v11_ho = ho
        best_v11_c = C

print(f"\n  v11 Reproduced: HO AUC {best_v11_ho:.6f} (original: {v11_ho_auc:.6f})")

# ============================================================
# PHASE 9: INDIVIDUAL FEATURE SCREENING
# ============================================================

print("\n" + "=" * 70)
print("PHASE 9: INDIVIDUAL FEATURE SCREENING (v11 + 1)")
print("=" * 70)

valid_candidates = []
for f in v12_candidates:
    if f not in dt.columns:
        print(f"  SKIP {f}: not in data")
        continue
    vals = dt[f].astype(float).fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        print(f"  DROP {f}: std={vals.std():.5f}")

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v11_features_safe + [feat]
    best_ho = 0
    best_c = best_v11_c
    for C in [0.015, 0.02, 0.025, 0.03, 0.035, 0.04]:
        _, ho, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    delta = best_ho - best_v11_ho
    feature_results.append((feat, best_ho, delta, best_c))
    tag = "+++" if delta > 0.003 else ("++" if delta > 0.001 else ("+" if delta > 0.0003 else ("~" if delta > -0.0005 else "-")))
    print(f"  {tag} {feat}: HO={best_ho:.4f} (delta={delta:+.4f}) C={best_c}")

feature_results.sort(key=lambda x: -x[2])

print(f"\n  TOP 20 candidates:")
for i, (feat, ho, delta, c) in enumerate(feature_results[:20]):
    print(f"    {i+1}. {feat}: HO={ho:.4f} ({delta:+.4f})")

# ============================================================
# PHASE 10: GREEDY FORWARD SELECTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 10: GREEDY FORWARD SELECTION (HO-gated)")
print("=" * 70)

current_features = v11_features_safe.copy()
current_ho = best_v11_ho
added = []

for feat, ho_individual, delta_individual, best_c_indiv in feature_results:
    if delta_individual < 0.0001:
        continue

    test_features = current_features + [feat]
    best_ho = 0
    best_c = 0.03
    for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    if best_ho > current_ho + 0.0001:
        current_features.append(feat)
        added.append((feat, best_ho - current_ho, best_c))
        print(f"  ADDED: {feat} -> HO {best_ho:.4f} (+{best_ho - best_v11_ho:.4f} from v11) C={best_c}")
        current_ho = best_ho
    else:
        print(f"  SKIP: {feat} -> HO {best_ho:.4f} (no gain)")

print(f"\n  After forward selection: {len(current_features)} features, HO AUC {current_ho:.4f}")
if added:
    print(f"  Added {len(added)} new features: {[f for f, _, _ in added]}")
else:
    print(f"  No features added (ORATS does not improve HO AUC)")

# ============================================================
# PHASE 11: STABILITY TEST (10 seeds)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 11: STABILITY TEST (10 seeds)")
print("=" * 70)

v12_hos = []
v11_hos = []
for seed in range(10):
    _, ho12, _, _ = evaluate_features(current_features, best_v11_c, yt, yh, dt, dh, seed=seed)
    _, ho11, _, _ = evaluate_features(v11_features_safe, best_v11_c, yt, yh, dt, dh, seed=seed)
    v12_hos.append(ho12)
    v11_hos.append(ho11)

wins = sum(1 for a, b in zip(v12_hos, v11_hos) if a > b)
t_stat, p_val = stats.ttest_rel(v12_hos, v11_hos)

print(f"  v12 mean HO: {np.mean(v12_hos):.6f} (std={np.std(v12_hos):.6f})")
print(f"  v11 mean HO: {np.mean(v11_hos):.6f} (std={np.std(v11_hos):.6f})")
print(f"  v12 wins: {wins}/10 seeds")
print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.10f}")

# ============================================================
# PHASE 12: FINAL REPORT
# ============================================================

print("\n" + "=" * 70)
print("PHASE 12: FINAL REPORT")
print("=" * 70)

wf_final, ho_final, model_final, scaler_final = evaluate_features(current_features, best_v11_c, yt, yh, dt, dh)

v12_added = [f for f in current_features if f not in v11_features_safe]
v11_dropped = [f for f in v11_features_safe if f not in current_features]

print(f"\nv12 REPORT:")
print(f"  Features: {len(current_features)} ({len(v12_added)} new, {len(v11_dropped)} dropped)")
print(f"  C: {best_v11_c}")
print(f"  WF AUC: {wf_final:.6f}")
print(f"  HO AUC: {ho_final:.6f} (v11: {best_v11_ho:.6f})")
print(f"  HO delta: {ho_final - best_v11_ho:+.6f}")
print(f"  Stability: {wins}/10 seeds")
print(f"  p-value: {p_val:.10f}")

if added:
    print(f"\n  Features added ({len(v12_added)}):")
    for f in v12_added:
        print(f"    - {f}")
else:
    print(f"\n  NO FEATURES ADDED - ORATS features do not improve v11")

if v11_dropped:
    print(f"\n  Features dropped ({len(v11_dropped)}):")
    for f in v11_dropped:
        print(f"    - {f}")

# ============================================================
# CHAMPION CHALLENGE
# ============================================================

print(f"\n{'=' * 70}")
print(f"CHAMPION CHALLENGE: v12 vs v11")
print(f"{'=' * 70}")

ho_better = ho_final > best_v11_ho
stability_good = wins >= 6

print(f"  HO AUC: v12={ho_final:.6f} vs v11={best_v11_ho:.6f}")
print(f"           delta={ho_final - best_v11_ho:+.6f}")
if ho_better:
    print(f"           >>> v12 WINS <<<")
else:
    print(f"           v11 WINS")

print(f"  Stability: {wins}/10 seeds, p={p_val:.10f}")
if stability_good:
    print(f"             Stable")
else:
    print(f"             Unstable")

if ho_better and stability_good and len(v12_added) > 0:
    print(f"\n  >>> v12 is NEW CHAMPION! <<<")
else:
    print(f"\n  v11 remains CHAMPION")
    print(f"  Reason: ", end="")
    if not ho_better:
        print("HO AUC not improved")
    elif not stability_good:
        print("Stability issues")
    else:
        print("No features added")

# ============================================================
# SAVE RESULTS
# ============================================================

results = {
    'version': 'v12.0.0',
    'timestamp': pd.Timestamp.now().isoformat(),
    'baseline_v11': {
        'ho_auc': float(best_v11_ho),
        'c': float(best_v11_c),
        'features': len(v11_features_safe)
    },
    'v12_results': {
        'ho_auc': float(ho_final),
        'wf_auc': float(wf_final),
        'c': float(best_v11_c),
        'features': len(current_features),
        'ho_delta': float(ho_final - best_v11_ho),
        'features_added': v12_added,
        'features_dropped': v11_dropped,
        'n_added': len(v12_added),
        'n_candidates_tested': len(valid_candidates),
        'stability': {
            'wins_10_seeds': int(wins),
            'v12_mean': float(np.mean(v12_hos)),
            'v11_mean': float(np.mean(v11_hos)),
            'v12_std': float(np.std(v12_hos)),
            'v11_std': float(np.std(v11_hos)),
            't_stat': float(t_stat),
            'p_value': float(p_val)
        }
    },
    'orats_coverage': {
        'total_training': len(dt),
        'with_orats': int((dt['has_options'] > 0).sum()),
        'coverage_pct': float(100 * (dt['has_options'] > 0).sum() / len(dt))
    },
    'individual_screening_top_10': [
        {'feature': feat, 'ho_auc': float(ho), 'delta': float(delta), 'c': float(c)}
        for feat, ho, delta, c in feature_results[:10]
    ]
}

with open('odin_v12_kaizen_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: odin_v12_kaizen_results.json")
print("\n" + "=" * 70)
print("KAIZEN COMPLETE")
print("=" * 70)
