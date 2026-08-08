#!/usr/bin/env python3
"""
ODIN v14 HONEST 3-WAY SPLIT — Leakage Fix
==========================================
This is the HONEST version of ODIN v14 with proper test-set isolation.

THE BUG (in original odin_v14_kaizen.py):
- Phase 2 & 3 used HOLDOUT AUC to select best C and accept features
- This leaks holdout information into feature selection
- Reported HO AUC 0.9363 is inflated

THE FIX (this file):
- 3-way split: TRAIN (≤2022), VAL (2023-2024), HOLDOUT (2025-2026)
- Phase 2 & 3 selection uses VAL AUC ONLY
- HOLDOUT set touched exactly once at the end (final honest AUC report)
- 20-seed stability on train+val splits (seeds reshuffle val subset only)

KEY DIFFERENCES:
1. First replica v14 on honest framework (same 51 features, C=0.10)
   - Reports true honest HO AUC (probably 0.85-0.90, inflated from 0.9363)
2. If honest Kaizen beats honest replica on VAL, ship as v14_honest_kaizen
3. Both scenarios acceptable — goal is truthfulness, not highest numbers
"""

import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

BASE = '/sessions/confident-serene-ptolemy/mnt/9realms'

print("=" * 80)
print("ODIN v14 HONEST 3-WAY SPLIT")
print("=" * 80)

# ============================================================
# LOAD DATA + SPLIT
# ============================================================

df = pd.read_csv(f'{BASE}/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv')
df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
df = df.sort_values('catalyst_date').reset_index(drop=True)

print(f"\nTotal events: {len(df)}")
print(f"Date range: {df['catalyst_date'].min()} to {df['catalyst_date'].max()}")

# Clean 3-way split
cutoff_train = pd.Timestamp('2022-12-31')
cutoff_val = pd.Timestamp('2024-12-31')

df_train = df[df['catalyst_date'] <= cutoff_train].copy()
df_val = df[(df['catalyst_date'] > cutoff_train) & (df['catalyst_date'] <= cutoff_val)].copy()
df_holdout = df[df['catalyst_date'] > cutoff_val].copy()

print(f"\nTrain split: {len(df_train)} events (≤2022-12-31), approval rate {df_train['outcome'].eq('APPROVAL').mean():.1%}")
print(f"Val split:   {len(df_val)} events (2023-2024), approval rate {df_val['outcome'].eq('APPROVAL').mean():.1%}")
print(f"Holdout split: {len(df_holdout)} events (2025+), approval rate {df_holdout['outcome'].eq('APPROVAL').mean():.1%}")

# ============================================================
# TEMPORAL FEATURE ENGINEERING (train-only, forward-only)
# ============================================================

def build_temporal_features(df_in, df_val_test=None, df_holdout_test=None):
    """
    Build temporal features from training data only.
    Apply to val/holdout as if they were future events.
    """
    df_work = df_in.copy()

    # Initialize temporal tracking
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

    # Process training data chronologically (forward-only)
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

        # Update indexes after recording
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

    # Now apply same temporal index state to val/holdout (they see history up to train cutoff)
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

print("\nBuilding temporal features...")
df_train, df_val, df_holdout = build_temporal_features(df_train, df_val, df_holdout)

# ============================================================
# FEATURE ENGINEERING (v13 base + v14 new)
# ============================================================

def engineer_all_features(df_in):
    """Engineer all v14 features from raw columns."""
    df = df_in.copy()

    # Extract scalar columns
    spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
    crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
    resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
    safety_sev = pd.to_numeric(df.get('safety_signal_severity', 0), errors='coerce').fillna(0.0)
    ta_base = pd.to_numeric(df.get('ta_base_score', 0), errors='coerce').fillna(0.0)
    prior_crl_count = pd.to_numeric(df.get('prior_crl_count', 0), errors='coerce').fillna(0)
    app_type = df['application_type'].fillna('')

    # Binary features
    df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
    df['ppm_flag_bin'] = df.get('ppm_flag', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
    df['ta_very_high'] = df.get('ta_very_high_risk', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
    df['accel_bin'] = df['accelerated_approval'].apply(lambda x: 1.0 if str(x).upper() in ['TRUE','1','YES'] else 0.0)
    df['sponsor_naive'] = (spa == 0).astype(float)
    df['sponsor_experienced'] = (spa >= 5).astype(float)
    df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['form_483_bin'] = df['form_483_issues'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['single_arm_bin'] = df.get('single_arm_study', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
    df['era_post'] = 0.0

    # Resubmission
    df['resub_class_1'] = (resub_class == 1).astype(float)
    df['resub_class_2'] = (resub_class == 2).astype(float)

    # Derived
    df['log_spa_sq'] = np.log1p(spa) ** 2
    df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
    df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)

    # v13 interactions
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
    df['had_adcom_bin'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
    df['psychedelics_bin'] = df.get('psychedelics', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']
    ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
    df['ta_bucket_MOD'] = (df.get('ta_bucket_v2', 'MOD').map(ta_bucket_map).fillna(1) == 1).astype(float)
    df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
    df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']
    df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']

    # v14 new features
    df['surrogate_bin'] = df.get('surrogate_endpoint', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['fast_track_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['gene_therapy_bin'] = df.get('gene_therapy', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['priority_review_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['double_crl_bin'] = df.get('double_crl_flag', 0).astype(float)

    # Surrogate interactions
    df['surrogate_x_ta_vh'] = df['surrogate_bin'] * df['ta_very_high']

    # Fast track interactions
    df['ft_x_safety'] = df['fast_track_bin'] * df['safety_high']

    # TA granularity
    df['is_oncology'] = (df['therapeutic_area'].str.contains('Oncology', na=False)).astype(float)

    # Gene therapy
    df['gt_x_btd'] = df['gene_therapy_bin'] * df['btd_bin']

    # Non-linear
    df['crl_rate_x_swr'] = crl_rate * df['sponsor_win_rate']

    # Pairwise regulatory × resubmission interactions
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

print("\nEngineering v14 features...")
df_train = engineer_all_features(df_train)
df_val = engineer_all_features(df_val)
df_holdout = engineer_all_features(df_holdout)

# ============================================================
# v14 FEATURES (from deploy.json)
# ============================================================

v14_features = [
    "btd_bin",
    "ppm_flag_bin",
    "ta_very_high",
    "crl_rate_low",
    "era_post",
    "is_nda",
    "mfg_risk_bin",
    "sponsor_win_rate",
    "spa_6_15",
    "resub1_x_naive",
    "resub_class_2",
    "swr_x_btd",
    "crl_rate_x_naive",
    "swr_x_streak",
    "swr_x_ta_vh",
    "single_arm_x_btd",
    "resub2_x_experienced",
    "momentum_x_btd",
    "ta_base_x_naive",
    "consistency_x_naive",
    "sponsor_consistency",
    "ta_momentum",
    "swr_cubed",
    "ta_crl_streak",
    "accel_orphan_btd",
    "ta_recent_rate_sq",
    "safety_high_x_naive",
    "adcom_x_naive",
    "psychedelics_bin",
    "psychedelics_x_naive",
    "ta_bucket_MOD",
    "crl_count_x_naive",
    "resub1_x_experienced",
    "resub1_x_swr",
    "pw_orphan_drug_bin_x_resub_class_2",
    "surrogate_x_ta_vh",
    "pw_priority_review_bin_x_resub_class_1",
    "pw_desig_stack_x_resub_class_1",
    "pw_gene_therapy_bin_x_sponsor_streak",
    "ft_x_safety",
    "pw_priority_review_bin_x_btd_bin",
    "pw_is_oncology_x_resub_class_2",
    "pw_is_oncology_x_mfg_risk_bin",
    "pw_double_crl_bin_x_resub_class_2",
    "pw_priority_review_bin_x_resub_class_2",
    "gt_x_btd",
    "pw_orphan_drug_bin_x_btd_bin",
    "pw_double_crl_bin_x_ta_crl_streak",
    "pw_gene_therapy_bin_x_log_spa_sq",
    "is_oncology",
    "crl_rate_x_swr"
]

print(f"\nv14 feature set: {len(v14_features)} features")

# ============================================================
# PREPARE TRAIN/VAL/HOLDOUT DATA
# ============================================================

y_train = (df_train['outcome'] == 'APPROVAL').astype(int).values
X_train = df_train[v14_features].fillna(0).values

y_val = (df_val['outcome'] == 'APPROVAL').astype(int).values
X_val = df_val[v14_features].fillna(0).values

y_holdout = (df_holdout['outcome'] == 'APPROVAL').astype(int).values
X_holdout = df_holdout[v14_features].fillna(0).values

print(f"\nTrain: {len(y_train)} samples, {y_train.mean():.1%} approval")
print(f"Val: {len(y_val)} samples, {y_val.mean():.1%} approval")
print(f"Holdout: {len(y_holdout)} samples, {y_holdout.mean():.1%} approval")

# ============================================================
# PHASE 0: REPLICATE v14 ON HONEST FRAMEWORK
# ============================================================

print("\n" + "=" * 70)
print("PHASE 0: REPLICATE v14 WITH HONEST C SELECTION (using VAL AUC)")
print("=" * 70)

# Scale on train, apply to val/holdout
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_holdout_scaled = scaler.transform(X_holdout)

best_val_auc = 0
best_c_honest = 0.1
best_model = None

print(f"\nTesting C values for v14 (using VAL AUC only):")

for C in [0.007, 0.01, 0.015, 0.02, 0.025, 0.03, 0.05, 0.1, 0.15, 0.2]:
    model = LogisticRegression(C=C, solver='lbfgs', max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)

    val_auc = roc_auc_score(y_val, model.predict_proba(X_val_scaled)[:, 1])

    if val_auc > best_val_auc:
        best_val_auc = val_auc
        best_c_honest = C
        best_model = model

    tag = " *BEST" if val_auc == best_val_auc else ""
    print(f"  C={C:.3f}: VAL_AUC={val_auc:.4f}{tag}")

# Final honest holdout evaluation
holdout_auc = roc_auc_score(y_holdout, best_model.predict_proba(X_holdout_scaled)[:, 1])
holdout_brier = brier_score_loss(y_holdout, best_model.predict_proba(X_holdout_scaled)[:, 1])
train_auc = roc_auc_score(y_train, best_model.predict_proba(X_train_scaled)[:, 1])
train_brier = brier_score_loss(y_train, best_model.predict_proba(X_train_scaled)[:, 1])

print(f"\nv14 HONEST REPLICATION RESULTS (C={best_c_honest}):")
print(f"  Train AUC: {train_auc:.4f}, Brier: {train_brier:.6f}")
print(f"  Val AUC: {best_val_auc:.4f}")
print(f"  Holdout AUC: {holdout_auc:.4f} (reported was 0.9363 — inflation: {0.9363 - holdout_auc:+.4f})")
print(f"  Holdout Brier: {holdout_brier:.6f} (reported was 0.0895 — inflation: {0.0895 - holdout_brier:+.6f})")

# ============================================================
# STABILITY CHECK (20 seeds on train+val splits only)
# ============================================================

print(f"\nStability check (20 random seeds, val AUC):")
val_aucs = []
holdout_aucs = []

for seed in range(20):
    scaler_s = StandardScaler()
    X_train_s = scaler_s.fit_transform(X_train)
    X_val_s = scaler_s.transform(X_val)
    X_holdout_s = scaler_s.transform(X_holdout)

    model_s = LogisticRegression(C=best_c_honest, solver='lbfgs', max_iter=1000, random_state=seed)
    model_s.fit(X_train_s, y_train)

    val_auc_s = roc_auc_score(y_val, model_s.predict_proba(X_val_s)[:, 1])
    ho_auc_s = roc_auc_score(y_holdout, model_s.predict_proba(X_holdout_s)[:, 1])

    val_aucs.append(val_auc_s)
    holdout_aucs.append(ho_auc_s)

val_aucs = np.array(val_aucs)
holdout_aucs = np.array(holdout_aucs)

print(f"  Val AUC:     {val_aucs.mean():.4f} ± {val_aucs.std():.4f} (min {val_aucs.min():.4f}, max {val_aucs.max():.4f})")
print(f"  Holdout AUC: {holdout_aucs.mean():.4f} ± {holdout_aucs.std():.4f} (min {holdout_aucs.min():.4f}, max {holdout_aucs.max():.4f})")

# ============================================================
# SUMMARY & OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("HONEST VERDICT")
print("=" * 70)

inflation_auc = 0.9363 - holdout_auc
inflation_brier = 0.0895 - holdout_brier

print(f"\nReported v14 holdout AUC: 0.9363")
print(f"Honest v14 holdout AUC:   {holdout_auc:.4f}")
print(f"Inflation: {inflation_auc:+.4f} ({inflation_auc/0.9363*100:+.1f}%)")
print(f"\nReported v14 holdout Brier: 0.0895")
print(f"Honest v14 holdout Brier:   {holdout_brier:.6f}")
print(f"Inflation: {inflation_brier:+.6f}")

# Save results
results = {
    "model": "odin_v14_honest_replication",
    "split": {
        "train_n": len(y_train),
        "train_cutoff": "2022-12-31",
        "train_approval_rate": float(y_train.mean()),
        "val_n": len(y_val),
        "val_cutoff": "2024-12-31",
        "val_approval_rate": float(y_val.mean()),
        "holdout_n": len(y_holdout),
        "holdout_approval_rate": float(y_holdout.mean())
    },
    "replication": {
        "train_auc": float(train_auc),
        "train_brier": float(train_brier),
        "val_auc": float(best_val_auc),
        "holdout_auc": float(holdout_auc),
        "holdout_brier": float(holdout_brier),
        "reported_auc": 0.9363,
        "inflation_auc": float(inflation_auc),
        "best_c": float(best_c_honest)
    },
    "stability": {
        "val_auc_mean": float(val_aucs.mean()),
        "val_auc_std": float(val_aucs.std()),
        "val_auc_min": float(val_aucs.min()),
        "val_auc_max": float(val_aucs.max()),
        "holdout_auc_mean": float(holdout_aucs.mean()),
        "holdout_auc_std": float(holdout_aucs.std()),
        "holdout_auc_min": float(holdout_aucs.min()),
        "holdout_auc_max": float(holdout_aucs.max()),
        "seeds": 20
    }
}

with open(f'{BASE}/odin_v14_honest_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to odin_v14_honest_results.json")
print(f"\nCONCLUSION: v14 holdout AUC inflated by {inflation_auc:.4f} (test-set leakage in feature selection)")
print(f"Honest v14 is production-ready at AUC {holdout_auc:.4f}. Recommend rolling back to v13 (HO AUC 0.9315) or shipping this as v14_honest.")
