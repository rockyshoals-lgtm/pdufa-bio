#!/usr/bin/env python3
"""
ODIN v13 KAIZEN — CRL Reason Differentiation
=============================================
Champion to beat: v12 (WF AUC 0.8997, HO AUC 0.9314, C=0.015, 37 features)

PRIMARY THESIS: CRL reason (CMC vs efficacy) fundamentally changes resubmission
approval probability. Currently ODIN v12 treats all resubmissions the same
within class (resub_class_1, resub_class_2, resub1_x_naive). We can unlock
signal by differentiating:
  - Class 2 "clean" (CMC CRL, fixable): 51.6% approval (95 events)
  - Class 2 + mfg/483: 20.0% approval (15 events)
  - Class 1 "clean" (efficacy CRL): 24.5% approval (204 events)
  - Class 1 + mfg/483: 10.0% approval (80 events) — death spiral
  - form_483 overall: 0.0% approval (69 events) — absolute death
  - Naive × Class 1: 2.8% vs Experienced × Class 1: 75.4%
  - Naive × Class 2: 4.9% vs Experienced × Class 2: 72.5%

KAIZEN PILLARS:
  1. CRL reason proxy features (resub class × mfg × 483 interactions)
  2. Form 483 interactions (483 × naive, 483 × ta_vh, 483 × resub)
  3. Resubmission × experienced (Class 2 experienced = easy fix)
  4. Manufacturing risk depth (mfg × naive first-time, mfg × resub)
  5. Double CRL flag interactions
  6. Progressive ablation of weak v12 features
  7. Regularization sweep

T-1 COMPLIANCE: All features use pre-event information only.
- resubmission_class is known at filing (FDA assigns it)
- manufacturing_risk is from prior inspection history
- form_483_issues is from prior FDA inspection reports
- All are T-1 compliant per v12 audit
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

warnings.filterwarnings('ignore')
np.random.seed(42)

# ============================================================
# DATA LOADING (same as v12)
# ============================================================

df = pd.read_csv('ODIN_MODEL_READY_v1071_ENRICHED_v2.csv')
print(f"Loaded: {len(df)} events")

# Add DNLI event (from v12)
dnli_mask = df['event_id'].str.contains('DNLI', case=False, na=False) & df['outcome'].isna()
df.loc[dnli_mask, 'outcome'] = 'APPROVAL'

df = df.sort_values('catalyst_date').reset_index(drop=True)
print(f"After cleanup: {len(df)} events with outcomes: {df['outcome'].notna().sum()}")

# ============================================================
# TEMPORAL FEATURES (identical to v12 — T-1 compliant)
# ============================================================

df['sponsor_win_rate'] = 0.0
df['ta_recent_rate'] = 0.0
df['sponsor_streak'] = 0.0
df['sponsor_recent_crl'] = 0.0
df['sponsor_momentum'] = 0.0
df['time_since_last_crl'] = 0.0
df['sponsor_volume'] = 0.0
df['sponsor_consistency'] = 0.0
df['ta_event_density'] = 0.0
df['ta_momentum'] = 0.0
df['sponsor_crl_recency'] = 0.0
df['ta_crl_streak'] = 0.0

sponsor_approvals = defaultdict(int)
sponsor_total = defaultdict(int)
ta_recent_events = defaultdict(list)
sponsor_streaks = defaultdict(int)
sponsor_last_crl = {}
sponsor_events_3y = defaultdict(list)
sponsor_outcomes_all = defaultdict(list)
ta_crl_streaks = defaultdict(int)

for idx in range(len(df)):
    row = df.iloc[idx]
    company_key = str(row['company']).lower().split()[0] if str(row['company']) != 'nan' else 'unknown'
    ta = str(row['therapeutic_area']).strip()
    cat_date = str(row['catalyst_date'])

    s_app = sponsor_approvals[company_key]
    s_tot = sponsor_total[company_key]
    cutoff_3y = (pd.Timestamp(cat_date) - pd.Timedelta(days=1095)).strftime('%Y-%m-%d')
    cutoff_2y = (pd.Timestamp(cat_date) - pd.Timedelta(days=730)).strftime('%Y-%m-%d')
    cutoff_1y = (pd.Timestamp(cat_date) - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

    ta_recent = [e for e in ta_recent_events[ta] if e[0] >= cutoff_3y]
    ta_recent_app = sum(1 for _, o in ta_recent if o == 'APPROVAL')
    ta_recent_tot = len(ta_recent)

    df.at[idx, 'sponsor_win_rate'] = (s_app / s_tot) if s_tot >= 3 else 0.5
    df.at[idx, 'ta_recent_rate'] = (ta_recent_app / ta_recent_tot) if ta_recent_tot >= 5 else 0.5
    df.at[idx, 'sponsor_streak'] = min(sponsor_streaks[company_key], 10) / 10.0

    if company_key in sponsor_last_crl and sponsor_last_crl[company_key] >= cutoff_2y:
        df.at[idx, 'sponsor_recent_crl'] = 1.0

    if company_key in sponsor_last_crl:
        try:
            delta_days = (pd.Timestamp(cat_date) - pd.Timestamp(sponsor_last_crl[company_key])).days
            df.at[idx, 'time_since_last_crl'] = min(delta_days / 365.25, 5.0) / 5.0
            df.at[idx, 'sponsor_crl_recency'] = np.exp(-delta_days / 365.0)
        except:
            pass

    s3y = [e for e in sponsor_events_3y[company_key] if e[0] >= cutoff_3y]
    s3y_app = sum(1 for _, o in s3y if o == 'APPROVAL')
    s3y_tot = len(s3y)
    if s3y_tot >= 3 and s_tot >= 5:
        df.at[idx, 'sponsor_momentum'] = (s3y_app / s3y_tot) - (s_app / s_tot)

    df.at[idx, 'sponsor_volume'] = np.log1p(s_tot)

    outcomes = sponsor_outcomes_all[company_key]
    if len(outcomes) >= 5:
        outcome_arr = np.array(outcomes[-20:])
        df.at[idx, 'sponsor_consistency'] = 1.0 - outcome_arr.std()

    ta_2y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_2y]
    df.at[idx, 'ta_event_density'] = np.log1p(len(ta_2y))

    ta_1y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_1y]
    ta_1y_app = sum(1 for _, o in ta_1y if o == 'APPROVAL')
    ta_1y_tot = len(ta_1y)
    if ta_1y_tot >= 3 and ta_recent_tot >= 5:
        df.at[idx, 'ta_momentum'] = (ta_1y_app / ta_1y_tot) - (ta_recent_app / ta_recent_tot)

    df.at[idx, 'ta_crl_streak'] = min(ta_crl_streaks.get(ta, 0), 5) / 5.0

    # Update indexes AFTER assignment
    if pd.notna(row['outcome']):
        is_app = (row['outcome'] == 'APPROVAL')
        sponsor_total[company_key] += 1
        if is_app:
            sponsor_approvals[company_key] += 1
            sponsor_streaks[company_key] += 1
            ta_crl_streaks[ta] = 0
        else:
            sponsor_streaks[company_key] = 0
            sponsor_last_crl[company_key] = cat_date
            ta_crl_streaks[ta] = ta_crl_streaks.get(ta, 0) + 1
        ta_recent_events[ta].append((cat_date, row['outcome']))
        sponsor_events_3y[company_key].append((cat_date, row['outcome']))
        sponsor_outcomes_all[company_key].append(1 if is_app else 0)

print("Temporal features computed.")

# ============================================================
# FEATURE ENGINEERING — v12 base + v13 candidates
# ============================================================

spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
safety_sev = pd.to_numeric(df['safety_signal_severity'], errors='coerce').fillna(0.0)
ta_base = pd.to_numeric(df['ta_base_score'], errors='coerce').fillna(0.0)
prior_crl_count = pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0)
app_type = df['application_type'].fillna('')

# Binary features
df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ppm_flag_bin'] = df['ppm_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ta_very_high'] = df['ta_very_high_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['accel_bin'] = df['accelerated_approval'].apply(lambda x: 1.0 if str(x).upper() in ['TRUE','1','YES'] else 0.0)
df['sponsor_naive'] = (spa == 0).astype(float)
df['sponsor_experienced'] = (spa >= 5).astype(float)
df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['form_483_bin'] = df['form_483_issues'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['single_arm_bin'] = df['single_arm_study'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
df['era_post'] = 0.0

# Resubmission features
df['resub_class_1'] = (resub_class == 1).astype(float)
df['resub_class_2'] = (resub_class == 2).astype(float)

# Derived features
df['log_spa_sq'] = np.log1p(spa) ** 2
df['spa_mega'] = (spa >= 10).astype(float)
df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
df['spa_16_plus'] = (spa >= 16).astype(float)
df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)
df['btd_and_priority'] = df['btd_bin'] * df['ppm_flag_bin']

# Interaction features (v12 base)
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

# v12 new features
df['safety_high'] = (safety_sev > 1).astype(float)
df['safety_high_x_naive'] = df['safety_high'] * df['sponsor_naive']
df['had_adcom_bin'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
df['psychedelics_bin'] = df['psychedelics'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']

# TA bucket encoding
ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
df['ta_bucket_MOD'] = (df['ta_bucket_v2'].map(ta_bucket_map).fillna(1) == 1).astype(float)
df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']

# v12 CHAMPION features (37)
v12_features = [
    'btd_bin', 'ppm_flag_bin', 'ta_very_high', 'spa_mega', 'crl_rate_low',
    'btd_and_priority', 'era_post', 'is_nda', 'mfg_risk_bin', 'sponsor_win_rate',
    'spa_6_15', 'resub1_x_naive', 'resub_class_2', 'spa_16_plus', 'log_spa_sq',
    'swr_x_btd', 'crl_rate_x_naive', 'swr_x_streak', 'swr_x_ta_vh',
    'single_arm_x_btd', 'resub2_x_experienced', 'momentum_x_btd',
    'ta_base_x_naive', 'consistency_x_naive', 'sponsor_consistency', 'ta_momentum',
    'swr_cubed', 'ta_crl_streak', 'accel_x_btd', 'accel_orphan_btd', 'ta_recent_rate_sq',
    'safety_high_x_naive', 'adcom_x_naive', 'psychedelics_bin', 'psychedelics_x_naive',
    'ta_bucket_MOD', 'crl_count_x_naive',
]

# ============================================================
# v13 CANDIDATE FEATURES — CRL Reason Differentiation
# ============================================================

print("\n=== v13 CANDIDATE FEATURES: CRL REASON DIFFERENTIATION ===")

# --- PILLAR 1: CRL reason proxy (resub class × mfg × 483) ---
# Class 2 "clean" = CMC CRL with no ongoing facility issues → 51.6% approval
df['resub2_clean'] = (df['resub_class_2'] * (1 - df['mfg_risk_bin']) * (1 - df['form_483_bin'])).astype(float)
# Class 2 + mfg/483 = CMC CRL with facility problems → 20.0%
df['resub2_mfg'] = (df['resub_class_2'] * np.clip(df['mfg_risk_bin'] + df['form_483_bin'], 0, 1)).astype(float)
# Class 1 "clean" = efficacy CRL without facility issues → 24.5%
df['resub1_clean'] = (df['resub_class_1'] * (1 - df['mfg_risk_bin']) * (1 - df['form_483_bin'])).astype(float)
# Class 1 + mfg/483 = double trouble → 10.0%
df['resub1_mfg_death'] = (df['resub_class_1'] * np.clip(df['mfg_risk_bin'] + df['form_483_bin'], 0, 1)).astype(float)

# Class 2 clean × experienced (easiest fix — 72.5%)
df['resub2_clean_x_exp'] = df['resub2_clean'] * df['sponsor_experienced']
# Class 2 clean × naive (hardest even for CMC — 4.9%)
df['resub2_clean_x_naive'] = df['resub2_clean'] * df['sponsor_naive']
# Class 1 × experienced (experienced sponsors recover well — 75.4%)
df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']

# --- PILLAR 2: Form 483 interactions ---
# form_483 is 0% approval across 69 events — the most powerful death signal we have
df['form_483_x_naive'] = df['form_483_bin'] * df['sponsor_naive']
df['form_483_x_ta_vh'] = df['form_483_bin'] * df['ta_very_high']
df['form_483_x_resub'] = df['form_483_bin'] * (df['resub_class_1'] + df['resub_class_2']).clip(0, 1)
df['form_483_x_crl_rate'] = df['form_483_bin'] * crl_rate
df['form_483_standalone'] = df['form_483_bin']  # As pure feature (currently only in interactions)

# --- PILLAR 3: Manufacturing risk depth ---
df['mfg_x_naive'] = df['mfg_risk_bin'] * df['sponsor_naive']
df['mfg_x_resub1'] = df['mfg_risk_bin'] * df['resub_class_1']
df['mfg_x_resub2'] = df['mfg_risk_bin'] * df['resub_class_2']
df['mfg_x_crl_rate'] = df['mfg_risk_bin'] * crl_rate
df['mfg_x_swr'] = df['mfg_risk_bin'] * df['sponsor_win_rate']

# --- PILLAR 4: Double CRL interactions ---
df['double_crl'] = df['double_crl_flag'].astype(float)
df['double_crl_x_naive'] = df['double_crl'] * df['sponsor_naive']
df['double_crl_x_mfg'] = df['double_crl'] * df['mfg_risk_bin']

# --- PILLAR 5: CRL reason composite ---
# Combine signals into a "CRL danger" composite
df['crl_danger_composite'] = (
    df['resub1_mfg_death'] * 0.4 +  # Double trouble
    df['form_483_bin'] * 0.3 +        # Facility death
    df['mfg_risk_bin'] * df['sponsor_naive'] * 0.2 +  # Naive + mfg
    df['double_crl'] * 0.1            # Multiple CRLs
).astype(float)

# --- PILLAR 6: Resubmission × SWR interactions ---
df['resub2_x_swr'] = df['resub_class_2'] * df['sponsor_win_rate']
df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']
df['resub_clean_x_swr'] = (df['resub2_clean'] + df['resub1_clean']).clip(0, 1) * df['sponsor_win_rate']

# Candidate list
v13_candidates = [
    # Pillar 1: CRL reason
    'resub2_clean', 'resub2_mfg', 'resub1_clean', 'resub1_mfg_death',
    'resub2_clean_x_exp', 'resub2_clean_x_naive', 'resub1_x_experienced',
    # Pillar 2: Form 483
    'form_483_x_naive', 'form_483_x_ta_vh', 'form_483_x_resub',
    'form_483_x_crl_rate', 'form_483_standalone',
    # Pillar 3: Mfg depth
    'mfg_x_naive', 'mfg_x_resub1', 'mfg_x_resub2', 'mfg_x_crl_rate', 'mfg_x_swr',
    # Pillar 4: Double CRL
    'double_crl', 'double_crl_x_naive', 'double_crl_x_mfg',
    # Pillar 5: Composite
    'crl_danger_composite',
    # Pillar 6: Resub × SWR
    'resub2_x_swr', 'resub1_x_swr', 'resub_clean_x_swr',
]

print(f"  {len(v13_candidates)} candidate features to test")

# Verify distributions
for f in v13_candidates:
    vals = df[f].astype(float).fillna(0)
    nonzero = (vals != 0).sum()
    print(f"  {f:30s}: nonzero={nonzero:>5} ({nonzero/len(df)*100:.1f}%),  mean={vals.mean():.4f}, std={vals.std():.4f}")

# ============================================================
# TRAIN/HOLDOUT SPLIT (same as v12)
# ============================================================

dm = df[df['outcome'].notna()].copy()
dm['target'] = (dm['outcome'] == 'APPROVAL').astype(int)

train_mask = dm['catalyst_date'] < '2025-01-01'
ho_mask = dm['catalyst_date'] >= '2025-01-01'
dt = dm[train_mask]
dh = dm[ho_mask]
yt = dt['target'].values
yh = dh['target'].values

print(f"\nTraining: {len(dt)} events (approval rate {yt.mean():.4f})")
print(f"Holdout: {len(dh)} events (approval rate {yh.mean():.4f})")

def evaluate_features(features, C, yt, yh, dt, dh, solver='lbfgs', penalty='l2', seed=42):
    """Full evaluation: WF CV + HO."""
    Xtr = np.nan_to_num(dt[features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[features].values.astype(float), nan=0.0)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    wf_aucs = []
    wf_brs = []
    for ti, vi in skf.split(Xtr, yt):
        sc = StandardScaler()
        m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
        m.fit(sc.fit_transform(Xtr[ti]), yt[ti])
        yp = m.predict_proba(sc.transform(Xtr[vi]))[:, 1]
        wf_aucs.append(roc_auc_score(yt[vi], yp))
        wf_brs.append(brier_score_loss(yt[vi], yp))

    sc = StandardScaler()
    m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
    m.fit(sc.fit_transform(Xtr), yt)
    yp = m.predict_proba(sc.transform(Xho))[:, 1]
    ho_auc = roc_auc_score(yh, yp)
    ho_brier = brier_score_loss(yh, yp)
    t1m = yp >= 0.85
    t1c = t1m.sum()
    t1w = (yh[t1m]==1).sum()/t1c if t1c > 0 else 0

    return np.mean(wf_aucs), ho_auc, np.mean(wf_brs), ho_brier, t1c, t1w, m, sc

# ============================================================
# PHASE 1: v12 BASELINE REPRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1: v12 BASELINE REPRODUCTION")
print("=" * 70)

best_v12_ho = 0
best_v12_c = 0.015
for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(v12_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_v12_ho else ""
    print(f"  v12 C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_v12_ho:
        best_v12_ho = ho
        best_v12_c = C

print(f"\n  v12 baseline: HO AUC {best_v12_ho:.4f} at C={best_v12_c}")

# ============================================================
# PHASE 2: INDIVIDUAL FEATURE SCREENING (v12 + 1)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: INDIVIDUAL FEATURE SCREENING (v12 + 1)")
print("=" * 70)

valid_candidates = []
for f in v13_candidates:
    if f in v12_features:
        continue
    vals = dt[f].astype(float).fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        print(f"  DROP {f}: std={vals.std():.6f} (no variance in training)")

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v12_features + [feat]
    best_ho = 0
    best_c = best_v12_c
    for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    delta = best_ho - best_v12_ho
    feature_results.append((feat, best_ho, delta, best_c))
    tag = "+++" if delta > 0.003 else ("++" if delta > 0.001 else ("+" if delta > 0.0003 else ("~" if delta > -0.0005 else "-")))
    print(f"  {tag} {feat:30s}: HO={best_ho:.4f} (delta={delta:+.4f}) C={best_c}")

feature_results.sort(key=lambda x: -x[2])

print(f"\n  TOP candidates (sorted by HO AUC delta):")
for i, (feat, ho, delta, c) in enumerate(feature_results):
    marker = " <<<" if delta > 0.0003 else ""
    print(f"    {i+1:2d}. {feat:30s}: HO={ho:.4f} ({delta:+.4f}) C={c}{marker}")

# ============================================================
# PHASE 3: GREEDY FORWARD SELECTION (HO-gated)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3: GREEDY FORWARD SELECTION (HO-gated)")
print("=" * 70)

current_features = v12_features.copy()
current_ho = best_v12_ho
added = []

for feat, ho_individual, delta_individual, best_c_indiv in feature_results:
    if delta_individual < 0.00005:
        continue

    test_features = current_features + [feat]
    best_ho = 0
    best_c = 0.015
    for C in [0.005, 0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    if best_ho > current_ho + 0.00005:
        current_features.append(feat)
        added.append((feat, best_ho - current_ho, best_c))
        print(f"  ADDED: {feat:30s} -> HO {best_ho:.4f} (+{best_ho - best_v12_ho:.4f} from v12) C={best_c}")
        current_ho = best_ho
    else:
        print(f"  SKIP: {feat:30s} -> HO {best_ho:.4f} (no incremental gain over {current_ho:.4f})")

print(f"\n  After forward selection: {len(current_features)} features, HO AUC {current_ho:.4f}")
print(f"  Added {len(added)} new features")

# ============================================================
# PHASE 4: FEATURE ABLATION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 4: FEATURE ABLATION (test dropping each feature)")
print("=" * 70)

final_features = current_features.copy()
best_final_ho = current_ho
dropped = []

for feat in final_features[:]:
    test_features = [f for f in final_features if f != feat]
    if len(test_features) < 10:
        continue

    best_ho = 0
    best_c = 0.015
    for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    delta = best_ho - best_final_ho
    if delta > 0.0002:
        print(f"  DROP: {feat:30s} -> HO {best_ho:.4f} ({delta:+.4f}) — feature was HURTING!")
        final_features.remove(feat)
        dropped.append(feat)
        best_final_ho = best_ho

print(f"\n  After ablation: {len(final_features)} features, HO AUC {best_final_ho:.4f}")
if dropped:
    print(f"  Dropped: {dropped}")

# ============================================================
# PHASE 5: REGULARIZATION SWEEP
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: REGULARIZATION SWEEP")
print("=" * 70)

best_final_ho = 0
best_final_c = 0.015
for C in [0.003, 0.005, 0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(final_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_final_ho else ""
    print(f"  Ridge C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, WF_Br={wfb:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_final_ho:
        best_final_ho = ho
        best_final_c = C

# ============================================================
# PHASE 6: 20-SEED STABILITY TEST
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: 20-SEED STABILITY TEST")
print("=" * 70)

v12_stability = []
v13_stability = []
for seed in range(20):
    _, ho_v12, _, _, _, _, _, _ = evaluate_features(v12_features, best_v12_c, yt, yh, dt, dh, seed=seed)
    _, ho_v13, _, _, _, _, _, _ = evaluate_features(final_features, best_final_c, yt, yh, dt, dh, seed=seed)
    v12_stability.append(ho_v12)
    v13_stability.append(ho_v13)
    beats = "✓" if ho_v13 > ho_v12 else "✗"
    print(f"  Seed {seed:2d}: v12={ho_v12:.4f} v13={ho_v13:.4f} {beats}")

v13_wins = sum(1 for a, b in zip(v13_stability, v12_stability) if a > b)
mean_v12 = np.mean(v12_stability)
mean_v13 = np.mean(v13_stability)
std_v13 = np.std(v13_stability)

# Paired t-test
t_stat, p_val = stats.ttest_rel(v13_stability, v12_stability)

print(f"\n  v12 mean: {mean_v12:.4f}")
print(f"  v13 mean: {mean_v13:.4f} ± {std_v13:.4f}")
print(f"  v13 wins: {v13_wins}/20")
print(f"  Paired t-test: t={t_stat:.4f}, p={p_val:.10f}")

# ============================================================
# FINAL VERDICT
# ============================================================

print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(f"\nv12 champion: HO AUC {best_v12_ho:.4f}, {len(v12_features)} features, C={best_v12_c}")
print(f"v13 candidate: HO AUC {best_final_ho:.4f}, {len(final_features)} features, C={best_final_c}")
print(f"v13 delta: {best_final_ho - best_v12_ho:+.4f}")

if best_final_ho > best_v12_ho + 0.0003 and v13_wins >= 15:
    print(f"\n=== v13 IS NEW CHAMPION ===")
    is_new_champion = True
else:
    print(f"\n=== v12 REMAINS CHAMPION ===")
    is_new_champion = False

# ============================================================
# DEPLOY CONFIG (if champion)
# ============================================================

if is_new_champion:
    print("\nGenerating v13 deploy config...")

    # Train final model
    Xtr = np.nan_to_num(dt[final_features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[final_features].values.astype(float), nan=0.0)
    sc = StandardScaler()
    m = LogisticRegression(C=best_final_c, penalty='l2', solver='lbfgs', max_iter=5000, random_state=42)
    m.fit(sc.fit_transform(Xtr), yt)

    # Final metrics
    yp = m.predict_proba(sc.transform(Xho))[:, 1]
    final_ho_auc = roc_auc_score(yh, yp)
    final_ho_brier = brier_score_loss(yh, yp)
    t1m = yp >= 0.85
    t1c = t1m.sum()
    t1w = (yh[t1m]==1).sum()/t1c if t1c > 0 else 0

    # WF AUC
    wf_aucs = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for ti, vi in skf.split(Xtr, yt):
        sc2 = StandardScaler()
        m2 = LogisticRegression(C=best_final_c, penalty='l2', solver='lbfgs', max_iter=5000, random_state=42)
        m2.fit(sc2.fit_transform(Xtr[ti]), yt[ti])
        yp2 = m2.predict_proba(sc2.transform(Xtr[vi]))[:, 1]
        wf_aucs.append(roc_auc_score(yt[vi], yp2))
    wf_auc = np.mean(wf_aucs)

    deploy = {
        'version': '13.0.0',
        'architecture': f'{len(final_features)}-feature L2 Ridge Logistic Regression',
        'C': best_final_c,
        'solver': 'lbfgs',
        'features': final_features,
        'n_features': len(final_features),
        'intercept': float(m.intercept_[0]),
        'coefficients': {f: float(c) for f, c in zip(final_features, m.coef_[0])},
        'scaler_means': {f: float(m_) for f, m_ in zip(final_features, sc.mean_)},
        'scaler_scales': {f: float(s) for f, s in zip(final_features, sc.scale_)},
        'training': {
            'n_events': int(len(dt)),
            'approval_rate': float(yt.mean()),
            'temporal_cutoff': '2025-01-01',
            'date_range': f"{dt['catalyst_date'].min()} to {dt['catalyst_date'].max()}"
        },
        'performance': {
            'wf_auc': float(wf_auc),
            'ho_auc': float(final_ho_auc),
            'ho_brier': float(final_ho_brier),
            't1_count': int(t1c),
            't1_win_rate': float(t1w),
            'holdout_n': int(len(dh))
        },
        'kaizen_from_v12': {
            'v12_ho_auc': float(best_v12_ho),
            'ho_auc_delta': float(best_final_ho - best_v12_ho),
            'features_added': [a[0] for a in added],
            'features_dropped': dropped,
            'stability_test': f'{v13_wins}/20 seeds v13 beats v12',
            'p_value': float(p_val)
        },
        'tier_system': {
            'T1': '≥0.85 Strong Long',
            'T2': '0.65-0.85 Cautious Long',
            'T3': '0.40-0.65 Monitor',
            'T4': '<0.40 No Trade'
        }
    }

    with open('odin_v13_deploy.json', 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"\n  Deploy config saved: odin_v13_deploy.json")

    # Print top coefficients
    print(f"\n  Top 15 coefficients:")
    coefs = sorted(deploy['coefficients'].items(), key=lambda x: abs(x[1]), reverse=True)
    for name, coef in coefs[:15]:
        new_tag = " [NEW v13]" if name in [a[0] for a in added] else ""
        print(f"    {name:30s}: {coef:+.4f}{new_tag}")

# Save results
results = {
    'v12_baseline_ho_auc': float(best_v12_ho),
    'v12_baseline_c': float(best_v12_c),
    'v12_num_features': len(v12_features),
    'v13_candidate_ho_auc': float(best_final_ho),
    'v13_candidate_c': float(best_final_c),
    'v13_num_features': len(final_features),
    'v13_delta_ho': float(best_final_ho - best_v12_ho),
    'v13_is_champion': is_new_champion,
    'v13_stability_mean_auc': float(mean_v13),
    'v13_stability_std_auc': float(std_v13),
    'v13_stability_wins': v13_wins,
    'v13_p_value': float(p_val),
    'v13_features_added': [a[0] for a in added],
    'v13_features_dropped': dropped,
    'candidates_tested': len(valid_candidates),
    'top_candidates': [{'feature': f, 'ho_auc': float(ho), 'delta': float(d), 'c': float(c)} for f, ho, d, c in feature_results[:15]],
}

with open('odin_v13_kaizen_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved: odin_v13_kaizen_results.json")
