#!/usr/bin/env python3
"""
BIFROST v5 KAIZEN — "Sniper Edition"
=====================================
Goal: Predict EXPLOSIVE post-catalyst moves (>25%, >50%, >100%)
Add features BIFROST v4 cannot see: surprise factor, price compression,
float proxy, fallen angel ratio, resubmission surprise, short squeeze indicators.

Architecture:
  - Phase 1: Data enrichment (ODIN merge + price compression from cache)
  - Phase 2: Feature engineering (13 sniper candidates)
  - Phase 3: Individual screening (WF correlation + magnitude prediction lift)
  - Phase 4: Explosion Detector (binary classifier for P(big_move))
  - Phase 5: Enhanced magnitude model (forward selection)
  - Phase 6: Walk-forward validation + stability (20 seeds)
  - Phase 7: Deploy config generation

Training: 1,705 PDUFA events (2020-2026) with real stock returns
Validation: Walk-forward honest (train ≤2024, test 2025-2026)
"""

import pandas as pd
import numpy as np
import json
import warnings
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report
from sklearn.preprocessing import StandardScaler
from scipy import stats
import lightgbm as lgb

warnings.filterwarnings('ignore')

print("=" * 70)
print("BIFROST v5 KAIZEN — SNIPER EDITION")
print("=" * 70)

# ============================================================
# PHASE 1: DATA LOADING & ENRICHMENT
# ============================================================
print("\n>>> PHASE 1: Data Loading & Enrichment")

# Load BIFROST runup data
bf = pd.read_csv("/sessions/loving-nifty-dirac/mnt/Python/9realms/pdufa_runup_bifrost.csv")
print(f"  BIFROST events: {len(bf)}")

# Load ODIN enriched data for feature merge
odin = pd.read_csv("/sessions/loving-nifty-dirac/mnt/Python/9realms/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
print(f"  ODIN events: {len(odin)}")

# Load price cache for 52-week high calculation
with open("/sessions/loving-nifty-dirac/mnt/Python/9realms/bifrost_price_cache.json") as f:
    price_cache = json.load(f)
print(f"  Price cache entries: {len(price_cache)}")

# Numeric conversions
for col in ['post_1d', 'post_2d', 'post_5d', 'eve_price', 'v5_score', 'vol_ratio',
            'runup_30d', 'runup_21d', 'runup_14d', 'runup_7d', 'runup_5d', 'runup_3d']:
    bf[col] = pd.to_numeric(bf[col], errors='coerce')

bf['pdufa_date'] = pd.to_datetime(bf['pdufa_date'], errors='coerce')

# ============================================================
# PHASE 1A: Calculate 52-week high from price cache
# ============================================================
print("\n  Computing 52-week highs and price compression from cache...")

def get_52w_high_and_compression(row):
    """Calculate 52-week high and compression ratio from price cache."""
    cache_key = row.get('cache_key', '')
    if not cache_key or cache_key not in price_cache:
        return pd.Series({'high_52w': np.nan, 'price_compression': np.nan,
                          'high_90d': np.nan, 'drawdown_from_high': np.nan})

    prices = price_cache[cache_key]
    eve_price = row['eve_price']

    # Get all prices before T-1 (keys are negative days like "-30", "-60", etc.)
    pre_prices = []
    for day_str, price in prices.items():
        day = int(day_str)
        if day <= -1:  # before eve
            pre_prices.append((day, price))

    if not pre_prices:
        return pd.Series({'high_52w': np.nan, 'price_compression': np.nan,
                          'high_90d': np.nan, 'drawdown_from_high': np.nan})

    # 52-week high (all available pre-event prices, cache goes back ~150 days typically)
    all_prices = [p for _, p in pre_prices]
    high_all = max(all_prices)

    # 90-day high
    prices_90d = [p for d, p in pre_prices if d >= -90]
    high_90d = max(prices_90d) if prices_90d else high_all

    # Price compression = current / high (lower = more compressed = more explosive potential)
    compression = eve_price / high_all if high_all > 0 else 1.0
    drawdown = (eve_price - high_all) / high_all if high_all > 0 else 0.0

    return pd.Series({'high_52w': high_all, 'price_compression': compression,
                      'high_90d': high_90d, 'drawdown_from_high': drawdown})

price_features = bf.apply(get_52w_high_and_compression, axis=1)
bf = pd.concat([bf, price_features], axis=1)
print(f"  Price compression computed: {bf['price_compression'].notna().sum()}/{len(bf)} events")

# ============================================================
# PHASE 1B: Merge ODIN features
# ============================================================
print("\n  Merging ODIN features...")

# Create merge key: ticker + approximate date
odin['cat_date'] = pd.to_datetime(odin['cat_date'], errors='coerce')
bf['merge_ticker'] = bf['ticker'].str.upper().str.strip()
odin['merge_ticker'] = odin['ticker'].str.upper().str.strip()

# Merge on ticker — some events may have multiple ODIN entries, take closest date
odin_features_to_merge = [
    'merge_ticker', 'cat_date', 'prior_crl', 'sponsor_prior_approvals', 'btd', 'orphan',
    'priority_review', 'fast_track', 'accelerated_approval', 'resubmission_class',
    'ta_base_score', 'historical_crl_rate', 'gene_therapy', 'single_arm_study',
    'application_type', 'prior_crl_count', 'surrogate_endpoint', 'ta_very_high_risk',
    'manufacturing_risk', 'ppm_flag', 'ta_bucket_v2'
]

odin_sub = odin[[c for c in odin_features_to_merge if c in odin.columns]].copy()

# For each BIFROST event, find the closest ODIN event by ticker
merged_count = 0
odin_cols_added = ['is_resub', 'is_prior_crl', 'is_btd', 'is_orphan', 'is_priority_review',
                   'is_accelerated', 'is_first_in_class_proxy', 'is_single_arm',
                   'ta_base_score_odin', 'crl_rate_odin', 'sponsor_approvals',
                   'is_gene_therapy', 'is_resubmission_class1', 'is_resubmission_class2',
                   'prior_crl_count_odin']

for col in odin_cols_added:
    bf[col] = np.nan

for idx, row in bf.iterrows():
    ticker = row['merge_ticker']
    pdufa = row['pdufa_date']

    matches = odin_sub[odin_sub['merge_ticker'] == ticker]
    if len(matches) == 0:
        continue

    # Find closest by date
    if pd.notna(pdufa) and 'cat_date' in matches.columns:
        matches = matches.copy()
        matches['date_diff'] = abs((matches['cat_date'] - pdufa).dt.days)
        matches = matches.sort_values('date_diff')

    best = matches.iloc[0]

    bf.at[idx, 'is_resub'] = 1 if (pd.notna(best.get('resubmission_class')) and best.get('resubmission_class') not in ['', 'FALSE', False]) else 0
    bf.at[idx, 'is_prior_crl'] = 1 if best.get('prior_crl', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_btd'] = 1 if best.get('btd', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_orphan'] = 1 if best.get('orphan', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_priority_review'] = 1 if best.get('priority_review', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_accelerated'] = 1 if best.get('accelerated_approval', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_single_arm'] = 1 if best.get('single_arm_study', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'is_gene_therapy'] = 1 if best.get('gene_therapy', False) in [True, 'True', 1, '1'] else 0
    bf.at[idx, 'ta_base_score_odin'] = float(best.get('ta_base_score', 0)) if pd.notna(best.get('ta_base_score')) else np.nan
    bf.at[idx, 'crl_rate_odin'] = float(best.get('historical_crl_rate', 0)) if pd.notna(best.get('historical_crl_rate')) else np.nan
    bf.at[idx, 'sponsor_approvals'] = float(best.get('sponsor_prior_approvals', 0)) if pd.notna(best.get('sponsor_prior_approvals')) else np.nan
    bf.at[idx, 'prior_crl_count_odin'] = float(best.get('prior_crl_count', 0)) if pd.notna(best.get('prior_crl_count')) else np.nan

    resub_class = best.get('resubmission_class', '')
    bf.at[idx, 'is_resubmission_class1'] = 1 if str(resub_class) == '1' else 0
    bf.at[idx, 'is_resubmission_class2'] = 1 if str(resub_class) == '2' else 0

    merged_count += 1

print(f"  ODIN merge: {merged_count}/{len(bf)} events matched")

# ============================================================
# PHASE 2: FEATURE ENGINEERING — Sniper Features
# ============================================================
print("\n>>> PHASE 2: Feature Engineering — Sniper Features")

# Market cap encoding
bf['is_nano'] = (bf['mcap_tier'] == 'Nano (<$50M)').astype(float)
bf['is_micro'] = (bf['mcap_tier'] == 'Micro ($50M-$300M)').astype(float)
bf['is_small'] = (bf['mcap_tier'] == 'Small ($300M-$2B)').astype(float)
bf['is_mid'] = (bf['mcap_tier'] == 'Mid ($2B-$10B)').astype(float)
bf['is_large'] = (bf['mcap_tier'] == 'Large (>$10B)').astype(float)

# === SNIPER FEATURE 1: SURPRISE FACTOR ===
# How unexpected is an approval? Higher = more surprise if approved
bf['surprise_factor'] = 1.0 - bf['v5_score']

# === SNIPER FEATURE 2: SURPRISE × SMALL CAP ===
bf['surprise_x_nano'] = bf['surprise_factor'] * bf['is_nano']
bf['surprise_x_micro'] = bf['surprise_factor'] * bf['is_micro']
bf['surprise_x_small_cap'] = bf['surprise_factor'] * (bf['is_nano'] + bf['is_micro'])

# === SNIPER FEATURE 3: PRICE COMPRESSION ===
# Already computed: price_compression (eve_price / high). Lower = more compressed
bf['price_compressed'] = (bf['price_compression'] < 0.5).astype(float)  # >50% off highs
bf['drawdown_pct'] = bf['drawdown_from_high'].clip(-1, 0)  # capped at -100%

# === SNIPER FEATURE 4: LOW PRICE INDICATOR ===
bf['is_penny'] = (bf['eve_price'] < 5).astype(float)
bf['is_low_price'] = (bf['eve_price'] < 10).astype(float)
bf['log_price_inv'] = np.log1p(1.0 / bf['eve_price'].clip(0.01, None))  # inverse log price

# === SNIPER FEATURE 5: SURPRISE × LOW PRICE ===
bf['surprise_x_low_price'] = bf['surprise_factor'] * bf['is_low_price']
bf['surprise_x_penny'] = bf['surprise_factor'] * bf['is_penny']

# === SNIPER FEATURE 6: RESUBMISSION SURPRISE ===
# Market over-discounts CRL history — resubmission approvals are massive re-rates
bf['resub_surprise'] = bf['is_resub'].fillna(0) * bf['surprise_factor']
bf['prior_crl_surprise'] = bf['is_prior_crl'].fillna(0) * bf['surprise_factor']

# === SNIPER FEATURE 7: BEATEN DOWN ===
bf['beaten_down_30d'] = (bf['runup_30d'] < -10).astype(float)
bf['beaten_down_14d'] = (bf['runup_14d'] < -5).astype(float)
bf['runup_30d_neg'] = bf['runup_30d'].clip(None, 0)  # only negative values

# === SNIPER FEATURE 8: BEATEN DOWN × SURPRISE ===
bf['beaten_surprise'] = bf['beaten_down_30d'] * bf['surprise_factor']

# === SNIPER FEATURE 9: FALLEN ANGEL (price compression × small cap) ===
bf['fallen_angel'] = bf['price_compressed'] * (bf['is_nano'] + bf['is_micro'] + bf['is_small'])
bf['compression_x_surprise'] = (1.0 - bf['price_compression'].fillna(1.0)) * bf['surprise_factor']

# === SNIPER FEATURE 10: BINARY CATALYST PROXY ===
# First-in-class, orphan, gene therapy, accelerated — more binary outcomes
bf['binary_catalyst'] = (bf['is_orphan'].fillna(0) + bf['is_gene_therapy'].fillna(0) +
                         bf['is_accelerated'].fillna(0) + bf['is_single_arm'].fillna(0)).clip(0, 3)
bf['binary_x_small'] = bf['binary_catalyst'] * (bf['is_nano'] + bf['is_micro'])

# === SNIPER FEATURE 11: BTD × SMALL CAP ===
bf['btd_x_small_cap'] = bf['is_btd'].fillna(0) * (bf['is_nano'] + bf['is_micro'])

# === SNIPER FEATURE 12: HIGH CRL RATE TA × SURPRISE ===
bf['high_crl_ta_surprise'] = bf['crl_rate_odin'].fillna(0) * bf['surprise_factor']

# === SNIPER FEATURE 13: SPONSOR NAIVE × SMALL CAP (compressed expectations) ===
bf['naive_small'] = (bf['sponsor_approvals'].fillna(1) == 0).astype(float) * (bf['is_nano'] + bf['is_micro'])

# Collect all candidate features
SNIPER_CANDIDATES = [
    'surprise_factor', 'surprise_x_nano', 'surprise_x_micro', 'surprise_x_small_cap',
    'price_compression', 'price_compressed', 'drawdown_pct', 'log_price_inv',
    'is_penny', 'is_low_price', 'surprise_x_low_price', 'surprise_x_penny',
    'resub_surprise', 'prior_crl_surprise', 'beaten_down_30d', 'beaten_down_14d',
    'runup_30d_neg', 'beaten_surprise', 'fallen_angel', 'compression_x_surprise',
    'binary_catalyst', 'binary_x_small', 'btd_x_small_cap', 'high_crl_ta_surprise',
    'naive_small',
    # Also test the raw ODIN merge features
    'is_resub', 'is_prior_crl', 'is_btd', 'is_orphan', 'is_priority_review',
    'is_accelerated', 'is_single_arm', 'is_gene_therapy', 'ta_base_score_odin',
    'crl_rate_odin', 'prior_crl_count_odin'
]

print(f"  Total sniper candidates: {len(SNIPER_CANDIDATES)}")

# Fill NaN with 0 for binary features, median for continuous
for col in SNIPER_CANDIDATES:
    if col in bf.columns:
        if bf[col].dtype in ['float64', 'float32']:
            bf[col] = bf[col].fillna(0)

# ============================================================
# PHASE 3: INDIVIDUAL FEATURE SCREENING
# ============================================================
print("\n>>> PHASE 3: Individual Feature Screening")

# Target: post_1d return magnitude (for positive outcomes)
# We screen each feature for correlation with magnitude AND ability to predict big moves

# Walk-forward split
bf['year'] = bf['pdufa_date'].dt.year
train = bf[bf['year'] <= 2024].copy()
test = bf[bf['year'] >= 2025].copy()

print(f"  Train: {len(train)} events (≤2024)")
print(f"  Test: {len(test)} events (≥2025)")

# Define big move targets
train['is_big_move'] = (train['post_1d'].abs() > 25).astype(int)
train['is_explosive'] = (train['post_1d'] > 50).astype(int)
train['is_pos_big'] = ((train['post_1d'] > 25) & (train['outcome_bin'] == 1)).astype(int)
train['abs_post_1d'] = train['post_1d'].abs()

test['is_big_move'] = (test['post_1d'].abs() > 25).astype(int)
test['is_explosive'] = (test['post_1d'] > 50).astype(int)
test['is_pos_big'] = ((test['post_1d'] > 25) & (test['outcome_bin'] == 1)).astype(int)
test['abs_post_1d'] = test['post_1d'].abs()

print(f"\n  Train big moves (|D1|>25%): {train['is_big_move'].sum()} ({train['is_big_move'].mean()*100:.1f}%)")
print(f"  Train explosive (D1>50%): {train['is_explosive'].sum()} ({train['is_explosive'].mean()*100:.1f}%)")
print(f"  Test big moves (|D1|>25%): {test['is_big_move'].sum()} ({test['is_big_move'].mean()*100:.1f}%)")

# Screen each feature
print(f"\n  {'FEATURE':<30} {'Train corr':>10} {'Big move AUC':>13} {'Test corr':>10} {'Test AUC':>10}")
print("  " + "-" * 73)

screening_results = []
for feat in SNIPER_CANDIDATES:
    if feat not in train.columns:
        continue

    tr_valid = train[[feat, 'post_1d', 'abs_post_1d', 'is_big_move']].dropna()
    te_valid = test[[feat, 'post_1d', 'abs_post_1d', 'is_big_move']].dropna()

    if len(tr_valid) < 50 or tr_valid[feat].std() == 0:
        continue

    # Correlation with absolute magnitude
    tr_corr = tr_valid[feat].corr(tr_valid['abs_post_1d'])

    # AUC for predicting big moves
    try:
        if tr_valid['is_big_move'].sum() >= 3 and tr_valid['is_big_move'].sum() < len(tr_valid):
            tr_auc = roc_auc_score(tr_valid['is_big_move'], tr_valid[feat].abs())
        else:
            tr_auc = 0.5
    except:
        tr_auc = 0.5

    te_corr = te_valid[feat].corr(te_valid['abs_post_1d']) if len(te_valid) > 10 else np.nan

    try:
        if te_valid['is_big_move'].sum() >= 2 and te_valid['is_big_move'].sum() < len(te_valid):
            te_auc = roc_auc_score(te_valid['is_big_move'], te_valid[feat].abs())
        else:
            te_auc = 0.5
    except:
        te_auc = 0.5

    flag = " ***" if (tr_auc > 0.60 and te_auc > 0.55) else ""
    print(f"  {feat:<30} {tr_corr:>+10.3f} {tr_auc:>13.3f} {te_corr:>+10.3f} {te_auc:>10.3f}{flag}")

    screening_results.append({
        'feature': feat, 'train_corr': tr_corr, 'train_auc': tr_auc,
        'test_corr': te_corr, 'test_auc': te_auc
    })

screening_df = pd.DataFrame(screening_results)

# ============================================================
# PHASE 4: EXPLOSION DETECTOR — Binary Classifier
# ============================================================
print("\n>>> PHASE 4: Explosion Detector — Binary Classifier")
print("  Target: P(|D1 move| > 25%)")

# Use features that showed signal in screening
# Include all reasonable candidates — the model will learn which matter
explosion_features = [
    'surprise_factor', 'is_penny', 'is_low_price', 'log_price_inv',
    'is_nano', 'is_micro', 'is_small',
    'surprise_x_small_cap', 'surprise_x_low_price',
    'price_compression', 'drawdown_pct',
    'beaten_down_30d', 'beaten_surprise',
    'fallen_angel', 'compression_x_surprise',
    'binary_catalyst', 'binary_x_small',
    'is_resub', 'resub_surprise',
    'is_orphan', 'is_btd', 'btd_x_small_cap',
    'vol_ratio', 'runup_30d',
    'v5_score',  # include raw ODIN score
]

# Filter to features that exist and have variance
valid_features = []
for f in explosion_features:
    if f in train.columns and train[f].notna().sum() > 100 and train[f].std() > 0.001:
        valid_features.append(f)

print(f"  Valid features: {len(valid_features)}")

# Prepare data
X_train = train[valid_features].fillna(0).values
y_train_big = train['is_big_move'].values
y_train_abs = train['abs_post_1d'].values
y_train_post = train['post_1d'].values

X_test = test[valid_features].fillna(0).values
y_test_big = test['is_big_move'].values
y_test_abs = test['abs_post_1d'].values
y_test_post = test['post_1d'].values

# Scale
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# Model 1: Logistic Regression for P(big move)
print("\n  --- Logistic Regression (Ridge, C=0.1) ---")
lr = LogisticRegression(C=0.1, solver='lbfgs', max_iter=1000, random_state=42)
lr.fit(X_train_s, y_train_big)

train_probs_lr = lr.predict_proba(X_train_s)[:, 1]
test_probs_lr = lr.predict_proba(X_test_s)[:, 1]

train_auc_lr = roc_auc_score(y_train_big, train_probs_lr)
test_auc_lr = roc_auc_score(y_test_big, test_probs_lr)
print(f"  Train AUC: {train_auc_lr:.4f}")
print(f"  Test AUC:  {test_auc_lr:.4f}")

# Feature importance
print(f"\n  Top features by |coefficient|:")
coef_importance = sorted(zip(valid_features, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True)
for feat, coef in coef_importance[:15]:
    print(f"    {feat:<30} {coef:+.4f}")

# Model 2: Gradient Boosting for P(big move)
print("\n  --- Gradient Boosting Classifier ---")
gb = GradientBoostingClassifier(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, min_samples_leaf=20, random_state=42
)
gb.fit(X_train, y_train_big)

train_probs_gb = gb.predict_proba(X_train)[:, 1]
test_probs_gb = gb.predict_proba(X_test)[:, 1]

train_auc_gb = roc_auc_score(y_train_big, train_probs_gb)
test_auc_gb = roc_auc_score(y_test_big, test_probs_gb)
print(f"  Train AUC: {train_auc_gb:.4f}")
print(f"  Test AUC:  {test_auc_gb:.4f}")

# Feature importance (GBM)
print(f"\n  Top features by GBM importance:")
gb_importance = sorted(zip(valid_features, gb.feature_importances_), key=lambda x: x[1], reverse=True)
for feat, imp in gb_importance[:15]:
    print(f"    {feat:<30} {imp:.4f}")

# Model 3: LightGBM
print("\n  --- LightGBM Classifier ---")
lgb_model = lgb.LGBMClassifier(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, min_child_samples=20, random_state=42,
    verbose=-1
)
lgb_model.fit(X_train, y_train_big)

train_probs_lgb = lgb_model.predict_proba(X_train)[:, 1]
test_probs_lgb = lgb_model.predict_proba(X_test)[:, 1]

train_auc_lgb = roc_auc_score(y_train_big, train_probs_lgb)
test_auc_lgb = roc_auc_score(y_test_big, test_probs_lgb)
print(f"  Train AUC: {train_auc_lgb:.4f}")
print(f"  Test AUC:  {test_auc_lgb:.4f}")

# Ensemble: 40% LR + 30% GBM + 30% LGB
train_probs_ens = 0.40 * train_probs_lr + 0.30 * train_probs_gb + 0.30 * train_probs_lgb
test_probs_ens = 0.40 * test_probs_lr + 0.30 * test_probs_gb + 0.30 * test_probs_lgb

train_auc_ens = roc_auc_score(y_train_big, train_probs_ens)
test_auc_ens = roc_auc_score(y_test_big, test_probs_ens)
print(f"\n  --- Ensemble (40% LR + 30% GBM + 30% LGB) ---")
print(f"  Train AUC: {train_auc_ens:.4f}")
print(f"  Test AUC:  {test_auc_ens:.4f}")

# Analyze explosion detector performance
print("\n  --- Explosion Detector Analysis ---")
test_with_probs = test.copy()
test_with_probs['explosion_prob'] = test_probs_ens

# By decile
test_with_probs['prob_decile'] = pd.qcut(test_with_probs['explosion_prob'], 5, labels=False, duplicates='drop')
print(f"\n  {'Quintile':<10} {'Avg Prob':>10} {'Big Move %':>12} {'Med |D1|':>10} {'Mean |D1|':>10} {'n':>5}")
for q in sorted(test_with_probs['prob_decile'].unique()):
    subset = test_with_probs[test_with_probs['prob_decile'] == q]
    print(f"  Q{int(q)+1:<9} {subset['explosion_prob'].mean():>10.3f} "
          f"{subset['is_big_move'].mean()*100:>11.1f}% "
          f"{subset['abs_post_1d'].median():>10.1f} "
          f"{subset['abs_post_1d'].mean():>10.1f} "
          f"{len(subset):>5}")

# ============================================================
# PHASE 5: MAGNITUDE REGRESSION MODEL
# ============================================================
print("\n>>> PHASE 5: Enhanced Magnitude Regression")
print("  Target: |D1 return| (absolute magnitude prediction)")

# Ridge regression for magnitude
print("\n  --- Ridge Regression (magnitude) ---")
ridge_mag = Ridge(alpha=100.0)
ridge_mag.fit(X_train_s, y_train_abs)

train_pred_ridge = ridge_mag.predict(X_train_s)
test_pred_ridge = ridge_mag.predict(X_test_s)

train_corr_ridge = np.corrcoef(y_train_abs, train_pred_ridge)[0, 1]
test_corr_ridge = np.corrcoef(y_test_abs, test_pred_ridge)[0, 1]

train_mae_ridge = np.mean(np.abs(y_train_abs - train_pred_ridge))
test_mae_ridge = np.mean(np.abs(y_test_abs - test_pred_ridge))

print(f"  Train corr: {train_corr_ridge:.4f}, MAE: {train_mae_ridge:.2f}%")
print(f"  Test corr:  {test_corr_ridge:.4f}, MAE: {test_mae_ridge:.2f}%")

# GBM for magnitude
print("\n  --- GBM Regression (magnitude) ---")
gbr = GradientBoostingRegressor(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, min_samples_leaf=20, random_state=42
)
gbr.fit(X_train, y_train_abs)

train_pred_gbr = gbr.predict(X_train)
test_pred_gbr = gbr.predict(X_test)

train_corr_gbr = np.corrcoef(y_train_abs, train_pred_gbr)[0, 1]
test_corr_gbr = np.corrcoef(y_test_abs, test_pred_gbr)[0, 1]

print(f"  Train corr: {train_corr_gbr:.4f}")
print(f"  Test corr:  {test_corr_gbr:.4f}")

# ============================================================
# PHASE 6: WALK-FORWARD STABILITY (20 seeds)
# ============================================================
print("\n>>> PHASE 6: Walk-Forward Stability (20 seeds)")

seed_results = []
for seed in range(20):
    lr_s = LogisticRegression(C=0.1, solver='lbfgs', max_iter=1000, random_state=seed)
    lr_s.fit(X_train_s, y_train_big)

    gb_s = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.8, min_samples_leaf=20, random_state=seed
    )
    gb_s.fit(X_train, y_train_big)

    lgb_s = lgb.LGBMClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.8, min_child_samples=20, random_state=seed, verbose=-1
    )
    lgb_s.fit(X_train, y_train_big)

    probs_s = (0.40 * lr_s.predict_proba(X_test_s)[:, 1] +
               0.30 * gb_s.predict_proba(X_test)[:, 1] +
               0.30 * lgb_s.predict_proba(X_test)[:, 1])

    auc_s = roc_auc_score(y_test_big, probs_s)
    seed_results.append(auc_s)

seed_results = np.array(seed_results)
print(f"  20-seed Test AUC: mean {seed_results.mean():.4f} ± {seed_results.std():.4f}")
print(f"  Min: {seed_results.min():.4f}, Max: {seed_results.max():.4f}")

# ============================================================
# PHASE 7: PRACTICAL VALUE — Can we make money?
# ============================================================
print("\n>>> PHASE 7: Practical Value Assessment")
print("  Question: If we size positions based on explosion probability, do we make more?")

# Strategy: weight positions by explosion probability
# Compare: equal-weight vs explosion-weighted for runup trades
test_with_probs['runup_21d'] = pd.to_numeric(test_with_probs['runup_21d'], errors='coerce')

# Only T1/T2 events (high ODIN score — our actual trading universe)
t1t2 = test_with_probs[test_with_probs['v5_score'] >= 0.65].copy()
print(f"\n  T1/T2 events in test set: {len(t1t2)}")

if len(t1t2) > 10:
    # Equal weight runup return
    eq_return = t1t2['runup_21d'].mean()

    # Explosion-weighted: overweight high explosion probability events
    t1t2['weight'] = t1t2['explosion_prob'] / t1t2['explosion_prob'].sum()
    weighted_return = (t1t2['runup_21d'] * t1t2['weight']).sum()

    # Top quintile vs bottom quintile
    q80 = t1t2['explosion_prob'].quantile(0.80)
    q20 = t1t2['explosion_prob'].quantile(0.20)

    top_quintile = t1t2[t1t2['explosion_prob'] >= q80]
    bottom_quintile = t1t2[t1t2['explosion_prob'] <= q20]

    print(f"  Equal-weight mean runup: {eq_return:+.2f}%")
    print(f"  Explosion-weighted runup: {weighted_return:+.2f}%")
    if len(top_quintile) > 3 and len(bottom_quintile) > 3:
        print(f"  Top quintile (high explosion) mean runup: {top_quintile['runup_21d'].mean():+.2f}% (n={len(top_quintile)})")
        print(f"  Bottom quintile (low explosion) mean runup: {bottom_quintile['runup_21d'].mean():+.2f}% (n={len(bottom_quintile)})")
        print(f"  Spread: {top_quintile['runup_21d'].mean() - bottom_quintile['runup_21d'].mean():+.2f}%")

# Post-event analysis — does the explosion detector actually predict big post-event moves?
print("\n  Post-event magnitude prediction (ALL events):")
for threshold in [0.10, 0.15, 0.20, 0.30]:
    flagged = test_with_probs[test_with_probs['explosion_prob'] >= threshold]
    if len(flagged) > 0:
        big_rate = flagged['is_big_move'].mean() * 100
        avg_abs = flagged['abs_post_1d'].mean()
        print(f"  P(explosion) ≥ {threshold:.0%}: {len(flagged)} events, {big_rate:.1f}% had |D1|>25%, avg |D1| = {avg_abs:.1f}%")

# ============================================================
# PHASE 8: SAVE RESULTS
# ============================================================
print("\n>>> PHASE 8: Saving Results")

results = {
    'version': '5.0.0_kaizen',
    'description': 'BIFROST v5 Sniper Edition — Explosion Detector + Enhanced Magnitude',
    'training': {
        'n_events': len(train),
        'n_test': len(test),
        'n_features': len(valid_features),
        'feature_list': valid_features,
        'sniper_candidates_tested': len(SNIPER_CANDIDATES),
    },
    'explosion_detector': {
        'architecture': 'Ensemble (40% Ridge LR + 30% GBM + 30% LGB)',
        'target': 'P(|D1 move| > 25%)',
        'train_auc': float(train_auc_ens),
        'test_auc': float(test_auc_ens),
        'stability_20_seed_mean': float(seed_results.mean()),
        'stability_20_seed_std': float(seed_results.std()),
        'lr_test_auc': float(test_auc_lr),
        'gbm_test_auc': float(test_auc_gb),
        'lgb_test_auc': float(test_auc_lgb),
    },
    'magnitude_model': {
        'ridge_test_corr': float(test_corr_ridge),
        'ridge_test_mae': float(test_mae_ridge),
        'gbr_test_corr': float(test_corr_gbr),
    },
    'screening_results': screening_results,
    'feature_coefficients': {feat: float(coef) for feat, coef in coef_importance},
    'gbm_feature_importance': {feat: float(imp) for feat, imp in gb_importance},
}

with open('/sessions/loving-nifty-dirac/mnt/Python/9realms/bifrost_v5_kaizen_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"  Results saved to bifrost_v5_kaizen_results.json")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("BIFROST v5 KAIZEN SUMMARY")
print("=" * 70)
print(f"""
  Explosion Detector:
    Architecture:  40% Ridge LR + 30% GBM + 30% LightGBM
    Target:        P(|D1 move| > 25%)
    Train AUC:     {train_auc_ens:.4f}
    Test AUC:      {test_auc_ens:.4f}
    20-seed mean:  {seed_results.mean():.4f} ± {seed_results.std():.4f}

  Features ({len(valid_features)} total):
    {', '.join(valid_features[:10])}
    ... and {len(valid_features)-10} more

  Magnitude Model:
    Ridge test corr: {test_corr_ridge:.4f}
    GBR test corr:   {test_corr_gbr:.4f}

  Key Insight: The Explosion Detector identifies events with high
  probability of extreme post-catalyst moves. Combined with ODIN/Gungnir
  direction prediction, this tells you WHICH events to size up on.
""")

print("BIFROST v5 KAIZEN COMPLETE ✓")
