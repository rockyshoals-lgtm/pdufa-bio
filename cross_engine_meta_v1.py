#!/usr/bin/env python3
"""
Cross-Engine Meta v1.0 — ODIN × BIFROST PDUFA Meta-Learning (HONEST)
======================================================================

Intent: Under a SINGLE unified 3-way split (ODIN cutoffs), train honest ODIN
(approval classifier) and honest BIFROST explosion (|D1|>25% classifier) on
the SAME training set, fit a meta-learner on VAL that combines both signals
plus a disagreement feature, then touch TEST once.

Hypothesis (from edge-ideation memo #4):
  BIFROST explosion probability encodes "market uncertainty / institutional
  positioning intensity" that is ORTHOGONAL to ODIN's regulatory approval
  signal. When ODIN says APPROVE and BIFROST says quiet, confidence is high.
  When ODIN says APPROVE and BIFROST says explosive, something's unusual —
  informative signal. Disagreement is the feature.

Split (UNIFIED on ODIN cutoffs):
  train  = events with catalyst_date ≤ 2022-12-31
  val    = 2023-01-01 → 2024-12-31   (meta selection happens here)
  test   = ≥ 2025-01-01              (touched once, final report)

Methodology:
  1. Train honest ODIN (C=0.01 from odin_v14_honest, 51 features) on train,
     save per-event approval probabilities for train/val/test.
  2. Train honest BIFROST explosion Ridge (C swept on val, V54_BASE 57 features)
     on train, save per-event explosion probabilities for train/val/test.
  3. Merge predictions by (ticker, catalyst_date). Inner join — events must
     exist in BOTH the ODIN dataset and the BIFROST dataset.
  4. Construct 6 meta-features from merged pairs:
       f1. odin_p
       f2. bifrost_p
       f3. abs_diff      = |odin_p − bifrost_p|
       f4. interact      = odin_p * bifrost_p
       f5. hi_both       = 1 if (odin_p > 0.7 AND bifrost_p > 0.15) else 0
       f6. hi_odin_lo_bf = 1 if (odin_p > 0.85 AND bifrost_p < 0.05) else 0
  5. Fit LogisticRegression meta on VAL, sweep C over [0.1, 1.0, 10.0, 100.0].
  6. Predict on TEST once. Compare:
       baseline_test_auc = roc_auc_score(y_test, odin_p_test)       # ODIN alone
       meta_test_auc     = roc_auc_score(y_test, meta_test_preds)
       lift = meta - baseline
  7. Bootstrap 95% CI on lift (n_boot=2000, seed=42).

Honest compliance:
  • SAME split discipline across both engines — no temporal ambiguity.
  • No holdout touching: meta hyperparam C selected on VAL AUC, test called once.
  • Feature set fixed from deployed honest versions (no greedy).
  • Merge key clean: (ticker.upper().strip(), catalyst_date[:10]).
"""

import json
import math
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
import warnings
warnings.filterwarnings('ignore')

ROOT = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
ODIN_CSV = ROOT / 'ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv'
BF_CSV = ROOT / 'pdufa_runup_bifrost_v2.csv'
PRICE_CACHE = ROOT / 'bifrost_price_cache.json'
SI_SNAP = ROOT / 'short_interest_snapshot.json'
XBI_CACHE = ROOT / 'xbi_daily_cache.json'
OUT = ROOT / 'cross_engine_meta_v1_results.json'

CUTOFF_TRAIN = pd.Timestamp('2022-12-31')
CUTOFF_VAL = pd.Timestamp('2024-12-31')

print("=" * 80)
print("  CROSS-ENGINE META v1.0 — ODIN × BIFROST")
print("=" * 80)

# ============================================================
# STEP 1: ODIN side — honest rebuild, 51 features, C=0.01
# ============================================================
print("\n[STEP 1] ODIN honest rebuild ...")

df = pd.read_csv(ODIN_CSV)
df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
df = df.sort_values('catalyst_date').reset_index(drop=True)

# drop events without outcome (can't train or evaluate)
df = df[df['outcome'].notna()].copy()

df_train_o = df[df['catalyst_date'] <= CUTOFF_TRAIN].copy()
df_val_o = df[(df['catalyst_date'] > CUTOFF_TRAIN) & (df['catalyst_date'] <= CUTOFF_VAL)].copy()
df_test_o = df[df['catalyst_date'] > CUTOFF_VAL].copy()

print(f"  ODIN train: {len(df_train_o)}  val: {len(df_val_o)}  test: {len(df_test_o)}")


def build_temporal_features_odin(df_in, df_val_test=None, df_holdout_test=None):
    """Forward-only temporal features. State from train frozen, applied to val/holdout."""
    df_work = df_in.copy()
    sponsor_win_counts = defaultdict(lambda: {'wins': 0, 'total': 0})
    sponsor_streaks = defaultdict(int)
    sponsor_recent_crls = defaultdict(int)
    sponsor_outcomes_all = defaultdict(list)
    ta_win_counts = defaultdict(lambda: {'wins': 0, 'total': 0})
    ta_crl_streaks = defaultdict(int)
    ta_recent_events = defaultdict(list)

    temporal_cols = ['sponsor_win_rate', 'ta_recent_rate', 'sponsor_streak', 'sponsor_recent_crl',
                     'sponsor_momentum', 'sponsor_volume', 'sponsor_consistency',
                     'ta_event_density', 'ta_momentum', 'ta_crl_streak']
    for col in temporal_cols:
        df_work[col] = 0.0

    for idx, row in df_work.iterrows():
        company_key = str(row.get('company', 'UNK')).strip().upper()
        ta = str(row.get('therapeutic_area', 'UNK')).strip().upper()
        si = sponsor_win_counts[company_key]
        df_work.at[idx, 'sponsor_win_rate'] = si['wins'] / si['total'] if si['total'] >= 2 else 0.5
        df_work.at[idx, 'sponsor_streak'] = sponsor_streaks[company_key]
        df_work.at[idx, 'sponsor_recent_crl'] = sponsor_recent_crls[company_key]
        df_work.at[idx, 'sponsor_volume'] = si['total']
        all_outcomes = sponsor_outcomes_all[company_key]
        recent_5 = all_outcomes[-5:] if len(all_outcomes) >= 5 else all_outcomes
        if len(recent_5) >= 3:
            rec_rate = sum(recent_5) / len(recent_5)
            ovr_rate = si['wins'] / si['total'] if si['total'] > 0 else 0.5
            df_work.at[idx, 'sponsor_momentum'] = rec_rate - ovr_rate
        if len(all_outcomes) >= 5:
            df_work.at[idx, 'sponsor_consistency'] = 1.0 - np.std(all_outcomes[-10:])
        ti = ta_win_counts[ta]
        df_work.at[idx, 'ta_recent_rate'] = ti['wins'] / ti['total'] if ti['total'] >= 5 else 0.5
        df_work.at[idx, 'ta_event_density'] = ti['total']
        df_work.at[idx, 'ta_crl_streak'] = ta_crl_streaks.get(ta, 0)
        ta_rec = ta_recent_events[ta][-10:] if len(ta_recent_events[ta]) >= 10 else ta_recent_events[ta]
        if len(ta_rec) >= 5:
            ta_rec_wins = sum(1 for _, o in ta_rec if o == 'APPROVAL')
            df_work.at[idx, 'ta_momentum'] = ta_rec_wins / len(ta_rec) - (ti['wins'] / ti['total'] if ti['total'] > 0 else 0.5)
        # update
        if pd.notna(row['outcome']):
            is_app = row['outcome'] == 'APPROVAL'
            si['total'] += 1
            si['wins'] += int(is_app)
            if is_app:
                sponsor_streaks[company_key] = max(1, sponsor_streaks[company_key] + 1)
                sponsor_recent_crls[company_key] = 0
                ta_crl_streaks[ta] = 0
            else:
                sponsor_streaks[company_key] = min(-1, sponsor_streaks[company_key] - 1)
                sponsor_recent_crls[company_key] = 1
                ta_crl_streaks[ta] = ta_crl_streaks.get(ta, 0) + 1
            ti['total'] += 1
            ti['wins'] += int(is_app)
            sponsor_outcomes_all[company_key].append(is_app)
            ta_recent_events[ta].append((row['catalyst_date'], 'APPROVAL' if is_app else 'CRL'))

    for dfs_test in [df_val_test, df_holdout_test]:
        if dfs_test is None:
            continue
        for col in temporal_cols:
            dfs_test[col] = 0.0
        for idx, row in dfs_test.iterrows():
            company_key = str(row.get('company', 'UNK')).strip().upper()
            ta = str(row.get('therapeutic_area', 'UNK')).strip().upper()
            si = sponsor_win_counts[company_key]
            dfs_test.at[idx, 'sponsor_win_rate'] = si['wins'] / si['total'] if si['total'] >= 2 else 0.5
            dfs_test.at[idx, 'sponsor_streak'] = sponsor_streaks[company_key]
            dfs_test.at[idx, 'sponsor_recent_crl'] = sponsor_recent_crls[company_key]
            dfs_test.at[idx, 'sponsor_volume'] = si['total']
            all_outcomes = sponsor_outcomes_all[company_key]
            recent_5 = all_outcomes[-5:] if len(all_outcomes) >= 5 else all_outcomes
            if len(recent_5) >= 3:
                rec_rate = sum(recent_5) / len(recent_5)
                ovr_rate = si['wins'] / si['total'] if si['total'] > 0 else 0.5
                dfs_test.at[idx, 'sponsor_momentum'] = rec_rate - ovr_rate
            if len(all_outcomes) >= 5:
                dfs_test.at[idx, 'sponsor_consistency'] = 1.0 - np.std(all_outcomes[-10:])
            ti = ta_win_counts[ta]
            dfs_test.at[idx, 'ta_recent_rate'] = ti['wins'] / ti['total'] if ti['total'] >= 5 else 0.5
            dfs_test.at[idx, 'ta_event_density'] = ti['total']
            dfs_test.at[idx, 'ta_crl_streak'] = ta_crl_streaks.get(ta, 0)
            ta_rec = ta_recent_events[ta][-10:] if len(ta_recent_events[ta]) >= 10 else ta_recent_events[ta]
            if len(ta_rec) >= 5:
                ta_rec_wins = sum(1 for _, o in ta_rec if o == 'APPROVAL')
                dfs_test.at[idx, 'ta_momentum'] = ta_rec_wins / len(ta_rec) - (ti['wins'] / ti['total'] if ti['total'] > 0 else 0.5)
    return df_work, df_val_test, df_holdout_test


def engineer_odin_features(df_in):
    df = df_in.copy()
    spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
    crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
    resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
    safety_sev = pd.to_numeric(df.get('safety_signal_severity', 0), errors='coerce').fillna(0.0)
    ta_base = pd.to_numeric(df.get('ta_base_score', 0), errors='coerce').fillna(0.0)
    prior_crl_count = pd.to_numeric(df.get('prior_crl_count', 0), errors='coerce').fillna(0)
    app_type = df['application_type'].fillna('')

    df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1', 'Yes'] else 0.0)
    df['ppm_flag_bin'] = df.get('ppm_flag', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1', 'Yes'] else 0.0)
    df['ta_very_high'] = df.get('ta_very_high_risk', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1', 'Yes'] else 0.0)
    df['accel_bin'] = df['accelerated_approval'].apply(lambda x: 1.0 if str(x).upper() in ['TRUE', '1', 'YES'] else 0.0)
    df['sponsor_naive'] = (spa == 0).astype(float)
    df['sponsor_experienced'] = (spa >= 5).astype(float)
    df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['form_483_bin'] = df['form_483_issues'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['single_arm_bin'] = df.get('single_arm_study', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
    df['era_post'] = 0.0
    df['resub_class_1'] = (resub_class == 1).astype(float)
    df['resub_class_2'] = (resub_class == 2).astype(float)
    df['log_spa_sq'] = np.log1p(spa) ** 2
    df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
    df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)
    df['resub1_x_naive'] = df['resub_class_1'] * df['sponsor_naive']
    df['swr_x_btd'] = df['sponsor_win_rate'] * df['btd_bin']
    df['crl_rate_x_naive'] = crl_rate * df['sponsor_naive']
    df['swr_x_streak'] = df['sponsor_win_rate'] * df['sponsor_streak']
    df['swr_x_ta_vh'] = df['sponsor_win_rate'] * df['ta_very_high']
    df['single_arm_x_btd'] = df['single_arm_bin'] * df['btd_bin']
    df['resub2_x_experienced'] = df['resub_class_2'] * df['sponsor_experienced']
    df['momentum_x_btd'] = df['sponsor_momentum'] * df['btd_bin']
    df['ta_base_x_naive'] = ta_base * df['sponsor_naive']
    df['consistency_x_naive'] = df['sponsor_consistency'] * df['sponsor_naive']
    df['swr_cubed'] = df['sponsor_win_rate'] ** 3
    df['ta_recent_rate_sq'] = df['ta_recent_rate'] ** 2
    df['accel_x_btd'] = df['accel_bin'] * df['btd_bin']
    df['accel_orphan_btd'] = df['accel_bin'] * df['orphan_bin'] * df['btd_bin']
    df['safety_high'] = (safety_sev > 1).astype(float)
    df['safety_high_x_naive'] = df['safety_high'] * df['sponsor_naive']
    df['had_adcom_bin'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
    df['psychedelics_bin'] = df.get('psychedelics', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']
    ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
    df['ta_bucket_MOD'] = (df.get('ta_bucket_v2', 'MOD').map(ta_bucket_map).fillna(1) == 1).astype(float)
    df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
    df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']
    df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']
    df['surrogate_bin'] = df.get('surrogate_endpoint', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['fast_track_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['gene_therapy_bin'] = df.get('gene_therapy', 0).apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['priority_review_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0)
    df['double_crl_bin'] = df.get('double_crl_flag', 0).astype(float)
    df['surrogate_x_ta_vh'] = df['surrogate_bin'] * df['ta_very_high']
    df['ft_x_safety'] = df['fast_track_bin'] * df['safety_high']
    df['is_oncology'] = (df['therapeutic_area'].str.contains('Oncology', na=False)).astype(float)
    df['gt_x_btd'] = df['gene_therapy_bin'] * df['btd_bin']
    df['crl_rate_x_swr'] = crl_rate * df['sponsor_win_rate']
    df['pw_orphan_drug_bin_x_resub_class_2'] = df['orphan_bin'] * df['resub_class_2']
    df['pw_priority_review_bin_x_resub_class_1'] = df['priority_review_bin'] * df['resub_class_1']
    df['pw_desig_stack_x_resub_class_1'] = ((df['btd_bin'] + df['fast_track_bin'] + df['orphan_bin'] + df['accel_bin'] + df['priority_review_bin']) * df['resub_class_1'])
    df['pw_gene_therapy_bin_x_sponsor_streak'] = df['gene_therapy_bin'] * df['sponsor_streak']
    df['pw_priority_review_bin_x_btd_bin'] = df['priority_review_bin'] * df['btd_bin']
    df['pw_is_oncology_x_resub_class_2'] = df['is_oncology'] * df['resub_class_2']
    df['pw_is_oncology_x_mfg_risk_bin'] = df['is_oncology'] * df['mfg_risk_bin']
    df['pw_double_crl_bin_x_resub_class_2'] = df['double_crl_bin'] * df['resub_class_2']
    df['pw_priority_review_bin_x_resub_class_2'] = df['priority_review_bin'] * df['resub_class_2']
    df['pw_orphan_drug_bin_x_btd_bin'] = df['orphan_bin'] * df['btd_bin']
    df['pw_double_crl_bin_x_ta_crl_streak'] = df['double_crl_bin'] * df['ta_crl_streak']
    df['pw_gene_therapy_bin_x_log_spa_sq'] = df['gene_therapy_bin'] * df['log_spa_sq']
    return df


print("  Building ODIN temporal features ...")
df_train_o, df_val_o, df_test_o = build_temporal_features_odin(df_train_o, df_val_o, df_test_o)
print("  Engineering ODIN features ...")
df_train_o = engineer_odin_features(df_train_o)
df_val_o = engineer_odin_features(df_val_o)
df_test_o = engineer_odin_features(df_test_o)

v14_features = [
    "btd_bin", "ppm_flag_bin", "ta_very_high", "crl_rate_low", "era_post", "is_nda",
    "mfg_risk_bin", "sponsor_win_rate", "spa_6_15", "resub1_x_naive", "resub_class_2",
    "swr_x_btd", "crl_rate_x_naive", "swr_x_streak", "swr_x_ta_vh", "single_arm_x_btd",
    "resub2_x_experienced", "momentum_x_btd", "ta_base_x_naive", "consistency_x_naive",
    "sponsor_consistency", "ta_momentum", "swr_cubed", "ta_crl_streak", "accel_orphan_btd",
    "ta_recent_rate_sq", "safety_high_x_naive", "adcom_x_naive", "psychedelics_bin",
    "psychedelics_x_naive", "ta_bucket_MOD", "crl_count_x_naive", "resub1_x_experienced",
    "resub1_x_swr", "pw_orphan_drug_bin_x_resub_class_2", "surrogate_x_ta_vh",
    "pw_priority_review_bin_x_resub_class_1", "pw_desig_stack_x_resub_class_1",
    "pw_gene_therapy_bin_x_sponsor_streak", "ft_x_safety",
    "pw_priority_review_bin_x_btd_bin", "pw_is_oncology_x_resub_class_2",
    "pw_is_oncology_x_mfg_risk_bin", "pw_double_crl_bin_x_resub_class_2",
    "pw_priority_review_bin_x_resub_class_2", "gt_x_btd",
    "pw_orphan_drug_bin_x_btd_bin", "pw_double_crl_bin_x_ta_crl_streak",
    "pw_gene_therapy_bin_x_log_spa_sq", "is_oncology", "crl_rate_x_swr"
]

# Impute missing cols
for col in v14_features:
    for d in (df_train_o, df_val_o, df_test_o):
        if col not in d.columns:
            d[col] = 0.0
        d[col] = pd.to_numeric(d[col], errors='coerce').fillna(0.0)

# Build matrices
y_train_o = df_train_o['outcome'].eq('APPROVAL').astype(int).values
y_val_o = df_val_o['outcome'].eq('APPROVAL').astype(int).values
y_test_o = df_test_o['outcome'].eq('APPROVAL').astype(int).values

X_train_o = df_train_o[v14_features].values
X_val_o = df_val_o[v14_features].values
X_test_o = df_test_o[v14_features].values

scaler_o = StandardScaler().fit(X_train_o)
X_train_o_s = scaler_o.transform(X_train_o)
X_val_o_s = scaler_o.transform(X_val_o)
X_test_o_s = scaler_o.transform(X_test_o)

# Honest C — use odin_v14_honest's winner (C=0.01)
odin_C = 0.01
odin_model = LogisticRegression(C=odin_C, solver='lbfgs', max_iter=1000, random_state=42)
odin_model.fit(X_train_o_s, y_train_o)
odin_p_train = odin_model.predict_proba(X_train_o_s)[:, 1]
odin_p_val = odin_model.predict_proba(X_val_o_s)[:, 1]
odin_p_test = odin_model.predict_proba(X_test_o_s)[:, 1]

odin_val_auc = roc_auc_score(y_val_o, odin_p_val)
odin_test_auc = roc_auc_score(y_test_o, odin_p_test)
print(f"  ODIN val AUC  = {odin_val_auc:.4f}")
print(f"  ODIN test AUC = {odin_test_auc:.4f}")

# Attach keys
df_train_o['_key'] = df_train_o['ticker'].astype(str).str.upper().str.strip() + '|' + df_train_o['catalyst_date'].dt.strftime('%Y-%m-%d')
df_val_o['_key'] = df_val_o['ticker'].astype(str).str.upper().str.strip() + '|' + df_val_o['catalyst_date'].dt.strftime('%Y-%m-%d')
df_test_o['_key'] = df_test_o['ticker'].astype(str).str.upper().str.strip() + '|' + df_test_o['catalyst_date'].dt.strftime('%Y-%m-%d')

odin_preds = {
    'train': dict(zip(df_train_o['_key'].values, zip(odin_p_train, y_train_o))),
    'val': dict(zip(df_val_o['_key'].values, zip(odin_p_val, y_val_o))),
    'test': dict(zip(df_test_o['_key'].values, zip(odin_p_test, y_test_o))),
}

# ============================================================
# STEP 2: BIFROST side — honest explosion classifier
# ============================================================
print("\n[STEP 2] BIFROST honest explosion rebuild ...")


def safe_float(x, default=0.0):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _xbi_return(xbi, date_str, lookback_days):
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0
    end_p = None
    for off in range(7):
        d = (dt - timedelta(days=off)).strftime("%Y-%m-%d")
        if d in xbi and xbi[d] is not None:
            end_p = xbi[d]
            break
    start_p = None
    st = dt - timedelta(days=lookback_days)
    for off in range(7):
        d = (st - timedelta(days=off)).strftime("%Y-%m-%d")
        if d in xbi and xbi[d] is not None:
            start_p = xbi[d]
            break
    if end_p and start_p and start_p > 0:
        return (end_p - start_p) / start_p
    return 0.0


with open(BF_CSV) as f:
    bf_rows = list(csv.DictReader(f))
print(f"  BIFROST events: {len(bf_rows)}")

with open(PRICE_CACHE) as f:
    price_cache = json.load(f)

si_data = {}
si_cutoff = None
if SI_SNAP.exists():
    with open(SI_SNAP) as f:
        si_data = json.load(f)
    if si_data and isinstance(si_data, dict):
        sample = next(iter(si_data.values()), None)
        if isinstance(sample, dict):
            si_cutoff = sample.get("fetch_date")

odin_csv_lookup = {}
with open(ODIN_CSV) as f:
    for r in csv.DictReader(f):
        key = (r.get("ticker", "").upper().strip(),
               (r.get("catalyst_date", "") or "")[:10])
        odin_csv_lookup[key] = r

with open(XBI_CACHE) as f:
    xbi = json.load(f)

features_bf = []
for row in bf_rows:
    ticker = row.get("ticker", "").upper().strip()
    pdufa_date = row.get("pdufa_date", "")
    eve_price = safe_float(row.get("eve_price"), 0.0)
    post_1d_raw = row.get("post_1d")
    post_1d = safe_float(post_1d_raw, None) if post_1d_raw not in (None, "") else None
    if not ticker or not pdufa_date or eve_price <= 0 or post_1d is None:
        continue
    use_si = True
    if si_cutoff:
        try:
            if pdufa_date[:10] < si_cutoff:
                use_si = False
        except Exception:
            pass
    v5_score = safe_float(row.get("v5_score"), 0.5)
    surprise = 1.0 - v5_score
    is_penny = 1.0 if eve_price < 5 else 0.0
    is_low = 1.0 if eve_price < 10 else 0.0
    log_price_inv = max(0.0, math.log(1.0 / max(eve_price, 0.01)))
    mcap_tier = row.get("mcap_tier", "") or ""
    is_nano = 1.0 if "Nano" in mcap_tier else 0.0
    is_micro = 1.0 if "Micro" in mcap_tier else 0.0
    is_small = 1.0 if "Small" in mcap_tier else 0.0
    small_cap = is_nano + is_micro + is_small
    cache_key = row.get("cache_key", "") or ""
    prices = price_cache.get(cache_key, {})
    high_52w = 0.0
    if isinstance(prices, dict) and prices:
        pre = []
        for day_str, p in prices.items():
            try:
                if int(day_str) <= -1:
                    pre.append(p)
            except Exception:
                continue
        if pre:
            high_52w = max(pre)
    compression = eve_price / high_52w if high_52w > 0 else 1.0
    drawdown = (eve_price - high_52w) / high_52w if high_52w > 0 else 0.0
    drawdown = max(-1.0, min(0.0, drawdown))
    runup_30d = safe_float(row.get("runup_30d"), 0.0)
    runup_7d = safe_float(row.get("runup_7d"), 0.0)
    vol_ratio = safe_float(row.get("vol_ratio"), 1.0)
    beaten_30d = 1.0 if runup_30d < -15 else 0.0
    beaten_surprise = beaten_30d * surprise
    compression_x_surprise = (1.0 - compression) * surprise if high_52w > 0 else 0.0
    si = si_data.get(ticker, {}) if use_si else {}
    if isinstance(si, dict) and "error" in si:
        si = {}
    pct_float_short = safe_float(si.get("short_pct_float"), 0.0) if use_si else 0.0
    dtc_val = safe_float(si.get("short_ratio"), 0.0) if use_si else 0.0
    float_shares = safe_float(si.get("float_shares"), 0.0) if use_si else 0.0
    log_float_inv = math.log(1e9 / max(float_shares, 1)) if (use_si and float_shares > 0) else 0.0
    short_high = 1.0 if (use_si and pct_float_short >= 0.15) else 0.0
    drift_mag = abs(runup_30d)
    drift_7d = abs(runup_7d)
    xbi_30d = _xbi_return(xbi, pdufa_date, 30)
    xbi_x_surprise = xbi_30d * surprise
    xbi_x_small = xbi_30d * small_cap
    odin_key = (ticker, pdufa_date[:10])
    o = odin_csv_lookup.get(odin_key, {})

    def otrue(k):
        return 1.0 if str(o.get(k, "")).lower() in ("true", "1") else 0.0

    btd = otrue("btd")
    orphan = otrue("orphan")
    priority_rev = otrue("priority_review")
    fast_track = otrue("fast_track")
    gene_th = otrue("gene_therapy")
    ppm_flag = otrue("ppm_flag")
    psychedelics = otrue("psychedelics")
    prior_crl_count = int(safe_float(o.get("prior_crl_count"), 0))
    resub_class = int(safe_float(o.get("resubmission_class"), 0))
    is_resub = 1.0 if resub_class > 0 else 0.0
    resub1 = 1.0 if resub_class == 1 else 0.0
    resub2 = 1.0 if resub_class == 2 else 0.0
    spa = int(safe_float(o.get("sponsor_prior_approvals"), 5))
    sponsor_naive = 1.0 if spa == 0 else 0.0
    log_spa = math.log1p(spa)
    safety_sev = int(safe_float(o.get("safety_signal_severity"), 0))
    safety_high = 1.0 if safety_sev > 1 else 0.0
    ta_vh = otrue("ta_very_high_risk")
    hist_crl = safe_float(o.get("historical_crl_rate"), 0.32)
    vol_high = 1.0 if vol_ratio > 1.5 else 0.0
    crl_count_x_small = float(prior_crl_count) * small_cap
    resub_x_surprise = is_resub * surprise
    naive_x_small = sponsor_naive * (is_nano + is_micro)
    drawdown_x_vol = abs(drawdown) * vol_ratio
    ta_vh_x_small = ta_vh * small_cap
    big_move = 1.0 if abs(post_1d) > 25 else 0.0
    t90_t7 = safe_float(row.get("T-90_T-7"), 0.0)

    # Unified split using ODIN cutoffs (not BIFROST's original cutoffs)
    try:
        event_ts = pd.Timestamp(pdufa_date[:10])
    except Exception:
        continue
    if event_ts <= CUTOFF_TRAIN:
        split = 'train'
    elif event_ts <= CUTOFF_VAL:
        split = 'val'
    else:
        split = 'test'

    features_bf.append({
        'ticker': ticker,
        'pdufa_date': pdufa_date[:10],
        'split': split,
        'big_move': big_move,
        'surprise_factor': surprise,
        'is_penny': is_penny, 'is_low_price': is_low, 'log_price_inv': log_price_inv,
        'is_nano': is_nano, 'is_micro': is_micro, 'is_small': is_small,
        'surprise_x_small_cap': surprise * (is_nano + is_micro),
        'surprise_x_low_price': surprise * is_low,
        'price_compression': compression, 'drawdown_pct': drawdown,
        'beaten_down_30d': beaten_30d, 'beaten_surprise': beaten_surprise,
        'compression_x_surprise': compression_x_surprise,
        'vol_ratio': vol_ratio, 'runup_30d': runup_30d, 'v5_score': v5_score,
        'log_float_inv': log_float_inv, 'pct_float_short': pct_float_short,
        'short_high': short_high, 'days_to_cover': dtc_val,
        'drift_magnitude': drift_mag, 'xbi_return_30d': xbi_30d,
        'xbi_x_surprise': xbi_x_surprise, 'xbi_x_small': xbi_x_small,
        'vol_high': vol_high, 'crl_count_x_small': crl_count_x_small,
        'is_resub': is_resub, 'drift_7d': drift_7d,
        'resub_x_surprise': resub_x_surprise, 'naive_x_small': naive_x_small,
        'drawdown_x_vol': drawdown_x_vol, 'runup_7d': runup_7d,
        'ta_vh_x_small': ta_vh_x_small,
        'cand_orphan_x_runup_7d_val': orphan * runup_7d,
        'cand_resub1_x_vol_high': resub1 * vol_high,
        'cand_ppm_x_runup_30d': ppm_flag * runup_30d,
        'cand_spa_log_x_is_small': log_spa * is_small,
        'cand_ppm_x_dtc': ppm_flag * dtc_val,
        'cand_safety_h_x_dtc': safety_high * dtc_val,
        'cand_crl_rate_x_is_small': hist_crl * is_small,
        'cand_resub2_x_log_float_inv': resub2 * log_float_inv,
        'cand_ta_vh_x_log_float_inv': ta_vh * log_float_inv,
        'cand_resub1_x_beaten': resub1 * beaten_30d,
        'cand_ppm_x_is_micro': ppm_flag * is_micro,
        'cand_btd_x_is_penny_val': btd * is_penny,
        'cand_resub2_x_xbi_30d': resub2 * xbi_30d,
        'cand_safety_h_x_short_high': safety_high * short_high,
        'cand_resub2_x_si_pct': resub2 * pct_float_short,
        'cand_resub1_x_is_micro': resub1 * is_micro,
        'cand_ft_x_drawdown': fast_track * abs(drawdown),
        'cand_ft_x_is_small': fast_track * is_small,
        'cand_safety_h_x_is_penny_val': safety_high * is_penny,
        'cand_fast_track': fast_track,
        'cand_gene_th_x_small_cap': gene_th * small_cap,
        'cand_resub2_x_runup_7d_val': resub2 * runup_7d,
        'cand_t90_t7': t90_t7,
    })

V54_BASE = [
    "surprise_factor", "is_penny", "is_low_price", "log_price_inv",
    "is_nano", "is_micro", "is_small",
    "surprise_x_small_cap", "surprise_x_low_price",
    "price_compression", "drawdown_pct", "beaten_down_30d",
    "beaten_surprise", "compression_x_surprise",
    "vol_ratio", "runup_30d", "v5_score",
    "log_float_inv", "pct_float_short", "short_high", "days_to_cover",
    "drift_magnitude", "xbi_return_30d", "xbi_x_surprise",
    "xbi_x_small", "vol_high", "crl_count_x_small", "is_resub",
    "drift_7d", "resub_x_surprise", "naive_x_small",
    "drawdown_x_vol", "runup_7d", "ta_vh_x_small",
    "cand_orphan_x_runup_7d_val", "cand_resub1_x_vol_high",
    "cand_ppm_x_runup_30d", "cand_spa_log_x_is_small",
    "cand_ppm_x_dtc", "cand_safety_h_x_dtc",
    "cand_crl_rate_x_is_small", "cand_resub2_x_log_float_inv",
    "cand_ta_vh_x_log_float_inv", "cand_resub1_x_beaten",
    "cand_ppm_x_is_micro", "cand_btd_x_is_penny_val",
    "cand_resub2_x_xbi_30d", "cand_safety_h_x_short_high",
    "cand_resub2_x_si_pct", "cand_resub1_x_is_micro",
    "cand_ft_x_drawdown", "cand_ft_x_is_small",
    "cand_safety_h_x_is_penny_val", "cand_fast_track",
    "cand_gene_th_x_small_cap", "cand_resub2_x_runup_7d_val",
    "cand_t90_t7",
]

train_bf = [f for f in features_bf if f['split'] == 'train']
val_bf = [f for f in features_bf if f['split'] == 'val']
test_bf = [f for f in features_bf if f['split'] == 'test']
print(f"  BIFROST train: {len(train_bf)}  val: {len(val_bf)}  test: {len(test_bf)}")
print(f"    train explosion rate: {np.mean([r['big_move'] for r in train_bf]):.3f}")
print(f"    val   explosion rate: {np.mean([r['big_move'] for r in val_bf]):.3f}")
print(f"    test  explosion rate: {np.mean([r['big_move'] for r in test_bf]):.3f}")


def build_matrix(rows, cols):
    return np.array([[safe_float(r.get(c, 0.0), 0.0) for c in cols] for r in rows], dtype=float)


X_train_bf = build_matrix(train_bf, V54_BASE)
X_val_bf = build_matrix(val_bf, V54_BASE)
X_test_bf = build_matrix(test_bf, V54_BASE)
y_train_bf = np.array([r['big_move'] for r in train_bf])
y_val_bf = np.array([r['big_move'] for r in val_bf])
y_test_bf = np.array([r['big_move'] for r in test_bf])

sc_bf = StandardScaler().fit(X_train_bf)
X_train_bf_s = sc_bf.transform(X_train_bf)
X_val_bf_s = sc_bf.transform(X_val_bf)
X_test_bf_s = sc_bf.transform(X_test_bf)

# C sweep on VAL only
C_sweep = [0.01, 0.03, 0.05, 0.10, 0.25, 0.50, 1.0]
best_bf_C, best_bf_val = None, -1.0
for C in C_sweep:
    m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
    m.fit(X_train_bf_s, y_train_bf)
    v = roc_auc_score(y_val_bf, m.predict_proba(X_val_bf_s)[:, 1])
    print(f"    BIFROST C={C}: val AUC = {v:.4f}")
    if v > best_bf_val:
        best_bf_val, best_bf_C = v, C
print(f"  BIFROST C winner: C={best_bf_C}  val AUC={best_bf_val:.4f}")

bf_model = LogisticRegression(C=best_bf_C, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
bf_model.fit(X_train_bf_s, y_train_bf)
bf_p_train = bf_model.predict_proba(X_train_bf_s)[:, 1]
bf_p_val = bf_model.predict_proba(X_val_bf_s)[:, 1]
bf_p_test = bf_model.predict_proba(X_test_bf_s)[:, 1]
bf_test_auc_explosion = roc_auc_score(y_test_bf, bf_p_test)
print(f"  BIFROST test AUC (explosion target) = {bf_test_auc_explosion:.4f}")

bf_preds = {
    'train': {f'{r["ticker"]}|{r["pdufa_date"]}': bf_p_train[i] for i, r in enumerate(train_bf)},
    'val': {f'{r["ticker"]}|{r["pdufa_date"]}': bf_p_val[i] for i, r in enumerate(val_bf)},
    'test': {f'{r["ticker"]}|{r["pdufa_date"]}': bf_p_test[i] for i, r in enumerate(test_bf)},
}

# ============================================================
# STEP 3: Merge by (ticker, catalyst_date), build meta-features
# ============================================================
print("\n[STEP 3] Merging ODIN × BIFROST predictions ...")


def build_meta(split_name):
    o = odin_preds[split_name]
    b = bf_preds[split_name]
    rows = []
    for key in o:
        if key not in b:
            continue
        odin_p, y_app = o[key]
        bf_p = b[key]
        rows.append({
            'key': key,
            'odin_p': odin_p,
            'bifrost_p': bf_p,
            'abs_diff': abs(odin_p - bf_p),
            'interact': odin_p * bf_p,
            'hi_both': 1.0 if (odin_p > 0.7 and bf_p > 0.15) else 0.0,
            'hi_odin_lo_bf': 1.0 if (odin_p > 0.85 and bf_p < 0.05) else 0.0,
            'y_approval': int(y_app),
        })
    return rows


meta_train = build_meta('train')
meta_val = build_meta('val')
meta_test = build_meta('test')
print(f"  Meta merged  train: {len(meta_train)}  val: {len(meta_val)}  test: {len(meta_test)}")

meta_cols = ['odin_p', 'bifrost_p', 'abs_diff', 'interact', 'hi_both', 'hi_odin_lo_bf']


def matrix(rows, cols):
    return np.array([[r[c] for c in cols] for r in rows], dtype=float)


X_mtrain = matrix(meta_train, meta_cols)
X_mval = matrix(meta_val, meta_cols)
X_mtest = matrix(meta_test, meta_cols)
y_mtrain = np.array([r['y_approval'] for r in meta_train])
y_mval = np.array([r['y_approval'] for r in meta_val])
y_mtest = np.array([r['y_approval'] for r in meta_test])

# ODIN-only baselines on merged intersection
odin_only_val = roc_auc_score(y_mval, [r['odin_p'] for r in meta_val])
odin_only_test = roc_auc_score(y_mtest, [r['odin_p'] for r in meta_test])
print(f"  ODIN-only val (on merged intersection)  = {odin_only_val:.4f}")
print(f"  ODIN-only test (on merged intersection) = {odin_only_test:.4f}")

# ============================================================
# STEP 4: Meta-learner — LogisticRegression, C sweep on val
# ============================================================
print("\n[STEP 4] Meta-learner fit (C sweep on val) ...")

# Fit meta on VAL (not train) because train data saw both ODIN and BIFROST fitted to it.
# Standard stacking discipline: meta is fit on held-out (val) predictions.
# test is untouched through fitting.

sc_meta = StandardScaler().fit(X_mval)
X_mval_s = sc_meta.transform(X_mval)
X_mtest_s = sc_meta.transform(X_mtest)

# We select C using k-fold on VAL (since VAL is the stacking training set).
from sklearn.model_selection import cross_val_score
C_meta_sweep = [0.1, 1.0, 10.0, 100.0]
best_meta_C, best_cv = None, -1.0
for C in C_meta_sweep:
    m = LogisticRegression(C=C, solver='lbfgs', max_iter=1000, random_state=42)
    try:
        scores = cross_val_score(m, X_mval_s, y_mval, cv=5, scoring='roc_auc')
        cv_auc = scores.mean()
        print(f"    Meta C={C}: 5-fold CV val AUC = {cv_auc:.4f}")
        if cv_auc > best_cv:
            best_cv, best_meta_C = cv_auc, C
    except Exception as e:
        print(f"    Meta C={C} failed: {e}")
print(f"  Meta C winner: C={best_meta_C}  CV val AUC={best_cv:.4f}")

# Fit final meta on full VAL, predict on TEST (touched once)
meta_model = LogisticRegression(C=best_meta_C, solver='lbfgs', max_iter=1000, random_state=42)
meta_model.fit(X_mval_s, y_mval)
meta_p_test = meta_model.predict_proba(X_mtest_s)[:, 1]

meta_test_auc = roc_auc_score(y_mtest, meta_p_test)
meta_test_brier = brier_score_loss(y_mtest, meta_p_test)
odin_only_brier = brier_score_loss(y_mtest, [r['odin_p'] for r in meta_test])

# ============================================================
# STEP 5: Bootstrap 95% CI on lift
# ============================================================
print("\n[STEP 5] Bootstrap CI on lift ...")

rng = np.random.RandomState(42)
n_boot = 2000
n_test = len(y_mtest)
odin_test_arr = np.array([r['odin_p'] for r in meta_test])

meta_aucs = []
odin_aucs = []
lifts = []
for _ in range(n_boot):
    idx = rng.choice(n_test, n_test, replace=True)
    if len(np.unique(y_mtest[idx])) < 2:
        continue
    m_auc = roc_auc_score(y_mtest[idx], meta_p_test[idx])
    o_auc = roc_auc_score(y_mtest[idx], odin_test_arr[idx])
    meta_aucs.append(m_auc)
    odin_aucs.append(o_auc)
    lifts.append(m_auc - o_auc)

meta_ci = (float(np.percentile(meta_aucs, 2.5)), float(np.percentile(meta_aucs, 97.5)))
odin_ci = (float(np.percentile(odin_aucs, 2.5)), float(np.percentile(odin_aucs, 97.5)))
lift_ci = (float(np.percentile(lifts, 2.5)), float(np.percentile(lifts, 97.5)))
lift_mean = float(np.mean(lifts))
p_lift_positive = float(np.mean(np.array(lifts) > 0))

print(f"  ODIN-only  test AUC = {odin_only_test:.4f}  CI95 [{odin_ci[0]:.4f}, {odin_ci[1]:.4f}]")
print(f"  META       test AUC = {meta_test_auc:.4f}  CI95 [{meta_ci[0]:.4f}, {meta_ci[1]:.4f}]")
print(f"  LIFT       mean = {lift_mean:+.4f}  CI95 [{lift_ci[0]:+.4f}, {lift_ci[1]:+.4f}]")
print(f"  P(lift>0) = {p_lift_positive:.3f}")

# ============================================================
# Verdict
# ============================================================
VERDICT = "NULL (no lift)"
if lift_ci[0] > 0:
    VERDICT = "SHIP — lift CI strictly above zero"
elif lift_mean > 0 and p_lift_positive > 0.8:
    VERDICT = "WEAK POSITIVE — lift mean positive with 80%+ boot support, CI spans 0"
elif lift_mean < 0 and p_lift_positive < 0.2:
    VERDICT = "REGRESSION — meta hurts"

print(f"\n  VERDICT: {VERDICT}")

# ============================================================
# Save results
# ============================================================
meta_coef = dict(zip(meta_cols, [float(c) for c in meta_model.coef_[0]]))

results = {
    'version': 'cross_engine_meta_v1.0',
    'split': {
        'cutoff_train': str(CUTOFF_TRAIN.date()),
        'cutoff_val': str(CUTOFF_VAL.date()),
    },
    'odin': {
        'C': odin_C,
        'n_features': len(v14_features),
        'train_n': int(len(df_train_o)),
        'val_n': int(len(df_val_o)),
        'test_n': int(len(df_test_o)),
        'val_auc_full': float(odin_val_auc),
        'test_auc_full': float(odin_test_auc),
    },
    'bifrost': {
        'C': best_bf_C,
        'n_features': len(V54_BASE),
        'train_n': int(len(train_bf)),
        'val_n': int(len(val_bf)),
        'test_n': int(len(test_bf)),
        'val_auc': float(best_bf_val),
        'test_auc_explosion_target': float(bf_test_auc_explosion),
    },
    'meta': {
        'meta_cols': meta_cols,
        'merged_train_n': len(meta_train),
        'merged_val_n': len(meta_val),
        'merged_test_n': len(meta_test),
        'C_sweep': C_meta_sweep,
        'best_C': best_meta_C,
        'best_cv_val_auc': float(best_cv),
        'coefficients': meta_coef,
        'intercept': float(meta_model.intercept_[0]),
    },
    'headline': {
        'odin_only_test_auc': float(odin_only_test),
        'odin_only_test_brier': float(odin_only_brier),
        'odin_only_test_auc_ci95': list(odin_ci),
        'meta_test_auc': float(meta_test_auc),
        'meta_test_brier': float(meta_test_brier),
        'meta_test_auc_ci95': list(meta_ci),
        'lift_mean': lift_mean,
        'lift_ci95': list(lift_ci),
        'p_lift_positive': p_lift_positive,
    },
    'verdict': VERDICT,
}

with open(OUT, 'w') as fh:
    json.dump(results, fh, indent=2)

print(f"\n  Results → {OUT}")
print("=" * 80)
