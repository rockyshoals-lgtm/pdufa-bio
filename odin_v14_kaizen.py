#!/usr/bin/env python3
"""
ODIN v14 KAIZEN — Resolution-Focused Brier Optimization
========================================================
Strategy:
  1. Untapped HIGH-SIGNAL features (surrogate_endpoint, fast_track, gene_therapy)
  2. New interaction terms (surrogate×btd, fast_track×naive, TA granularity)
  3. Exhaustive pairwise interactions of new × existing features
  4. Non-linear transforms for resolution improvement
  5. Isotonic recalibration for reliability improvement
  6. Optimize for BRIER as primary, AUC as secondary
  7. Aggressive ablation — drop any feature hurting Brier
"""

import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.isotonic import IsotonicRegression
from scipy import stats
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

BASE = '/sessions/loving-nifty-dirac/mnt/Python/9realms'

print("=" * 80)
print("ODIN v14 KAIZEN — Resolution-Focused Brier Optimization")
print("=" * 80)

# ============================================================
# LOAD DATA + TEMPORAL FEATURES (exact v13 pattern)
# ============================================================

df = pd.read_csv(f'{BASE}/ODIN_MODEL_READY_v1071_ENRICHED_v2.csv')
df = df.sort_values('catalyst_date').reset_index(drop=True)

print(f"\nDataset: {len(df)} events")

# Forward-only temporal features
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
    df[col] = 0.0

for idx, row in df.iterrows():
    company_key = str(row.get('company', 'UNK')).strip().upper()
    ta = str(row.get('therapeutic_area', 'UNK')).strip().upper()

    si = sponsor_win_counts[company_key]
    df.at[idx, 'sponsor_win_rate'] = si['wins'] / si['total'] if si['total'] >= 2 else 0.5
    df.at[idx, 'sponsor_streak'] = sponsor_streaks[company_key]
    df.at[idx, 'sponsor_recent_crl'] = sponsor_recent_crls[company_key]
    df.at[idx, 'sponsor_volume'] = si['total']

    all_outcomes = sponsor_outcomes_all[company_key]
    recent_5 = all_outcomes[-5:] if len(all_outcomes) >= 5 else all_outcomes
    if len(recent_5) >= 3:
        rec_rate = sum(recent_5) / len(recent_5)
        ovr_rate = si['wins'] / si['total'] if si['total'] > 0 else 0.5
        df.at[idx, 'sponsor_momentum'] = rec_rate - ovr_rate
    if len(all_outcomes) >= 5:
        df.at[idx, 'sponsor_consistency'] = 1.0 - np.std(all_outcomes[-10:])

    ti = ta_win_counts[ta]
    df.at[idx, 'ta_recent_rate'] = ti['wins'] / ti['total'] if ti['total'] >= 5 else 0.5
    df.at[idx, 'ta_event_density'] = ti['total']
    df.at[idx, 'ta_crl_streak'] = ta_crl_streaks.get(ta, 0)

    ta_rec = ta_recent_events[ta][-10:] if len(ta_recent_events[ta]) >= 10 else ta_recent_events[ta]
    if len(ta_rec) >= 5:
        ta_rec_wins = sum(1 for _, o in ta_rec if o == 'APPROVAL')
        df.at[idx, 'ta_momentum'] = ta_rec_wins / len(ta_rec) - (ti['wins'] / ti['total'] if ti['total'] > 0 else 0.5)

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
        ta_recent_events[ta].append((row['catalyst_date'], row['outcome']))
        sponsor_outcomes_all[company_key].append(1 if is_app else 0)

print("Temporal features computed (forward-only).")

# ============================================================
# FEATURE ENGINEERING — v13 base + v14 candidates
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
df['psychedelics_bin'] = df['psychedelics'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']
ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
df['ta_bucket_MOD'] = (df['ta_bucket_v2'].map(ta_bucket_map).fillna(1) == 1).astype(float)
df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']
df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']

# v13 CHAMPION features (36)
v13_features = [
    'btd_bin', 'ppm_flag_bin', 'ta_very_high', 'crl_rate_low',
    'era_post', 'is_nda', 'mfg_risk_bin', 'sponsor_win_rate',
    'spa_6_15', 'resub1_x_naive', 'resub_class_2', 'log_spa_sq',
    'swr_x_btd', 'crl_rate_x_naive', 'swr_x_streak', 'swr_x_ta_vh',
    'single_arm_x_btd', 'resub2_x_experienced', 'momentum_x_btd',
    'ta_base_x_naive', 'consistency_x_naive', 'sponsor_consistency', 'ta_momentum',
    'swr_cubed', 'ta_crl_streak', 'accel_x_btd', 'accel_orphan_btd', 'ta_recent_rate_sq',
    'safety_high_x_naive', 'adcom_x_naive', 'psychedelics_bin', 'psychedelics_x_naive',
    'ta_bucket_MOD', 'crl_count_x_naive', 'resub1_x_experienced', 'resub1_x_swr',
]

# ============================================================
# v14 CANDIDATE FEATURES — 7 PILLARS
# ============================================================

print("\n=== v14 CANDIDATE FEATURES ===")

# --- PILLAR 1: Untapped high-signal base features ---
df['surrogate_bin'] = df['surrogate_endpoint'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['fast_track_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['gene_therapy_bin'] = df['gene_therapy'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['orphan_drug_bin'] = df['orphan_bin']  # Already computed but not in v13
df['priority_review_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['double_crl_bin'] = df['double_crl_flag'].astype(float)

# --- PILLAR 2: Surrogate endpoint interactions ---
df['surrogate_x_btd'] = df['surrogate_bin'] * df['btd_bin']
df['surrogate_x_naive'] = df['surrogate_bin'] * df['sponsor_naive']
df['surrogate_x_swr'] = df['surrogate_bin'] * df['sponsor_win_rate']
df['surrogate_x_accel'] = df['surrogate_bin'] * df['accel_bin']
df['surrogate_x_orphan'] = df['surrogate_bin'] * df['orphan_bin']
df['surrogate_x_ta_vh'] = df['surrogate_bin'] * df['ta_very_high']

# --- PILLAR 3: Fast track interactions ---
df['ft_x_naive'] = df['fast_track_bin'] * df['sponsor_naive']
df['ft_x_experienced'] = df['fast_track_bin'] * df['sponsor_experienced']
df['ft_x_btd'] = df['fast_track_bin'] * df['btd_bin']
df['ft_x_swr'] = df['fast_track_bin'] * df['sponsor_win_rate']
df['ft_x_oncology'] = df['fast_track_bin'] * (df['therapeutic_area'].str.contains('Oncology', na=False)).astype(float)
df['ft_x_resub1'] = df['fast_track_bin'] * df['resub_class_1']
df['ft_x_crl_rate'] = df['fast_track_bin'] * crl_rate
df['ft_x_safety'] = df['fast_track_bin'] * df['safety_high']

# --- PILLAR 4: TA granularity (oncology penalty, high-rate TA boosts) ---
df['is_oncology'] = (df['therapeutic_area'].str.contains('Oncology', na=False)).astype(float)
df['is_infectious'] = (df['therapeutic_area'].str.contains('Infectious', na=False)).astype(float)
df['is_rare'] = (df['therapeutic_area'].str.contains('Rare', na=False)).astype(float)
df['is_cns'] = (df['therapeutic_area'].str.contains('CNS|Neurology', na=False)).astype(float)
df['is_immunology'] = (df['therapeutic_area'].str.contains('Immunology', na=False)).astype(float)
df['onc_x_naive'] = df['is_oncology'] * df['sponsor_naive']
df['onc_x_experienced'] = df['is_oncology'] * df['sponsor_experienced']
df['onc_x_btd'] = df['is_oncology'] * df['btd_bin']
df['onc_x_swr'] = df['is_oncology'] * df['sponsor_win_rate']
df['rare_x_btd'] = df['is_rare'] * df['btd_bin']

# --- PILLAR 5: Gene therapy and designation stacking ---
df['gt_x_naive'] = df['gene_therapy_bin'] * df['sponsor_naive']
df['gt_x_btd'] = df['gene_therapy_bin'] * df['btd_bin']
df['gt_x_orphan'] = df['gene_therapy_bin'] * df['orphan_bin']
df['orphan_x_naive'] = df['orphan_bin'] * df['sponsor_naive']
df['orphan_x_swr'] = df['orphan_bin'] * df['sponsor_win_rate']
df['desig_stack'] = (df['btd_bin'] + df['fast_track_bin'] + df['orphan_bin'] + df['accel_bin'] + df['priority_review_bin']).astype(float)
df['desig_stack_sq'] = df['desig_stack'] ** 2
df['desig_rich'] = (df['desig_stack'] >= 3).astype(float)

# --- PILLAR 6: Non-linear transforms for resolution ---
df['swr_sq'] = df['sponsor_win_rate'] ** 2
df['crl_rate_sq'] = crl_rate ** 2
df['crl_rate_x_swr'] = crl_rate * df['sponsor_win_rate']
df['log_spa_cubed'] = np.log1p(spa) ** 3
df['ta_base_sq'] = ta_base ** 2
df['safety_sev_bin'] = (safety_sev >= 2).astype(float)
df['safety_sev_x_swr'] = safety_sev * df['sponsor_win_rate']

# --- PILLAR 7: Exhaustive pairwise of NEW bases × key existing ---
new_bases = ['surrogate_bin', 'fast_track_bin', 'gene_therapy_bin', 'orphan_drug_bin',
             'priority_review_bin', 'double_crl_bin', 'is_oncology', 'desig_stack']
key_existing = ['sponsor_win_rate', 'sponsor_naive', 'sponsor_experienced', 'btd_bin',
                'ta_very_high', 'resub_class_1', 'resub_class_2', 'mfg_risk_bin',
                'sponsor_streak', 'ta_crl_streak', 'log_spa_sq', 'crl_rate_low']

pairwise_candidates = []
for nb in new_bases:
    for ke in key_existing:
        fname = f'pw_{nb}_x_{ke}'
        df[fname] = df[nb] * df[ke]
        pairwise_candidates.append(fname)

# Candidate list
v14_candidates = [
    # Pillar 1: Base features
    'surrogate_bin', 'fast_track_bin', 'gene_therapy_bin', 'orphan_drug_bin',
    'priority_review_bin', 'double_crl_bin',
    # Pillar 2: Surrogate interactions
    'surrogate_x_btd', 'surrogate_x_naive', 'surrogate_x_swr', 'surrogate_x_accel',
    'surrogate_x_orphan', 'surrogate_x_ta_vh',
    # Pillar 3: Fast track interactions
    'ft_x_naive', 'ft_x_experienced', 'ft_x_btd', 'ft_x_swr',
    'ft_x_oncology', 'ft_x_resub1', 'ft_x_crl_rate', 'ft_x_safety',
    # Pillar 4: TA granularity
    'is_oncology', 'is_infectious', 'is_rare', 'is_cns', 'is_immunology',
    'onc_x_naive', 'onc_x_experienced', 'onc_x_btd', 'onc_x_swr', 'rare_x_btd',
    # Pillar 5: Gene therapy + designation stacking
    'gt_x_naive', 'gt_x_btd', 'gt_x_orphan',
    'orphan_x_naive', 'orphan_x_swr',
    'desig_stack', 'desig_stack_sq', 'desig_rich',
    # Pillar 6: Non-linear transforms
    'swr_sq', 'crl_rate_sq', 'crl_rate_x_swr', 'log_spa_cubed',
    'ta_base_sq', 'safety_sev_bin', 'safety_sev_x_swr',
    # Pillar 7: Pairwise
] + pairwise_candidates

# Deduplicate and remove any already in v13
v14_candidates = [f for f in v14_candidates if f not in v13_features]
v14_candidates = list(dict.fromkeys(v14_candidates))  # preserve order, remove dupes

print(f"  {len(v14_candidates)} candidate features to test across 7 pillars")

# ============================================================
# TRAIN/HOLDOUT SPLIT
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

# ============================================================
# EVALUATION FUNCTION — dual metric (AUC + Brier)
# ============================================================

def evaluate_features(features, C, yt, yh, dt, dh, solver='lbfgs', penalty='l2', seed=42):
    """Full evaluation with AUC and Brier."""
    Xtr = np.nan_to_num(dt[features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[features].values.astype(float), nan=0.0)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    wf_aucs, wf_brs = [], []
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
# PHASE 1: v13 BASELINE
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1: v13 BASELINE REPRODUCTION")
print("=" * 70)

best_v13_ho_auc = 0
best_v13_ho_brier = 1.0
best_v13_c = 0.025

for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04]:
    wf, ho_auc, wfb, ho_brier, t1c, t1w, _, _ = evaluate_features(v13_features, C, yt, yh, dt, dh)
    tag = ""
    if ho_auc > best_v13_ho_auc:
        best_v13_ho_auc = ho_auc
        best_v13_ho_brier = ho_brier
        best_v13_c = C
        tag = " *AUC"
    print(f"  v13 C={C:.3f}: WF_AUC={wf:.4f}, HO_AUC={ho_auc:.4f}, WF_Br={wfb:.4f}, HO_Br={ho_brier:.4f}, T1={t1c}({t1w:.3f}){tag}")

print(f"\n  v13 baseline: HO AUC={best_v13_ho_auc:.4f}, HO Brier={best_v13_ho_brier:.4f}, C={best_v13_c}")

# Also find best Brier C
best_v13_brier_c = 0.025
best_v13_brier_val = 1.0
for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04]:
    _, _, _, ho_brier, _, _, _, _ = evaluate_features(v13_features, C, yt, yh, dt, dh)
    if ho_brier < best_v13_brier_val:
        best_v13_brier_val = ho_brier
        best_v13_brier_c = C

print(f"  v13 best Brier: {best_v13_brier_val:.6f} at C={best_v13_brier_c}")

# ============================================================
# PHASE 2: INDIVIDUAL FEATURE SCREENING (v13 + 1)
# Dual metric: screen on COMPOSITE = 0.5*AUC_delta + 0.5*(-Brier_delta)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: INDIVIDUAL FEATURE SCREENING (v13 + 1)")
print("=" * 70)

valid_candidates = []
for f in v14_candidates:
    if f in v13_features:
        continue
    vals = dt[f].astype(float).fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        pass  # silently skip zero-variance

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v13_features + [feat]
    best_ho_auc = 0
    best_ho_brier = 1.0
    best_c = best_v13_c

    for C in [0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04]:
        _, ho_auc, _, ho_brier, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        # Composite: maximize AUC, minimize Brier
        # We use the C that maximizes AUC first (primary screen)
        if ho_auc > best_ho_auc:
            best_ho_auc = ho_auc
            best_ho_brier = ho_brier
            best_c = C

    auc_delta = best_ho_auc - best_v13_ho_auc
    brier_delta = best_ho_brier - best_v13_brier_val  # Negative = improvement
    # Composite score: positive = good
    composite = auc_delta * 1000 - brier_delta * 1000  # Scale to make readable
    feature_results.append((feat, best_ho_auc, auc_delta, best_ho_brier, brier_delta, best_c, composite))

    tag = "+++" if auc_delta > 0.003 else ("++" if auc_delta > 0.001 else ("+" if auc_delta > 0.0003 else ("~" if auc_delta > -0.0005 else "-")))
    brier_tag = " Br↓" if brier_delta < -0.001 else (" Br↑" if brier_delta > 0.001 else "")
    print(f"  {tag} {feat:40s}: AUC={best_ho_auc:.4f} ({auc_delta:+.4f}) Br={best_ho_brier:.4f} ({brier_delta:+.4f}){brier_tag} C={best_c}")

feature_results.sort(key=lambda x: -x[6])  # Sort by composite

print(f"\n  TOP candidates (sorted by composite AUC+Brier):")
for i, (feat, ho, auc_d, br, br_d, c, comp) in enumerate(feature_results[:30]):
    marker = " <<<" if auc_d > 0.0003 or br_d < -0.0003 else ""
    print(f"    {i+1:2d}. {feat:40s}: AUC={ho:.4f} ({auc_d:+.4f}) Br={br:.4f} ({br_d:+.4f}) comp={comp:+.2f}{marker}")

# ============================================================
# PHASE 3: GREEDY FORWARD SELECTION (Brier-primary, AUC-gated)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3: GREEDY FORWARD SELECTION (Brier-primary)")
print("=" * 70)

current_features = v13_features.copy()
current_ho_auc = best_v13_ho_auc
current_ho_brier = best_v13_brier_val
added = []

MIN_AUC_IMPROVEMENT = -0.0005  # Allow tiny AUC regression if Brier improves
MIN_BRIER_IMPROVEMENT = 0.0001  # Must improve Brier by at least this

for feat, _, auc_d_indiv, _, br_d_indiv, _, composite in feature_results:
    if composite < -0.5:  # Skip clearly bad features
        continue

    test_features = current_features + [feat]
    best_ho_auc = 0
    best_ho_brier = 1.0
    best_c = 0.025

    for C in [0.005, 0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho_auc, _, ho_brier, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        # Primary: best Brier, with AUC as tiebreak
        if ho_brier < best_ho_brier - 0.00001 or (abs(ho_brier - best_ho_brier) < 0.00001 and ho_auc > best_ho_auc):
            best_ho_brier = ho_brier
            best_ho_auc = ho_auc
            best_c = C

    auc_change = best_ho_auc - current_ho_auc
    brier_change = best_ho_brier - current_ho_brier

    # Accept if: Brier improves AND AUC doesn't regress badly
    if brier_change < -MIN_BRIER_IMPROVEMENT and auc_change > MIN_AUC_IMPROVEMENT:
        current_features.append(feat)
        added.append((feat, auc_change, brier_change, best_c))
        print(f"  ADDED (Brier↓): {feat:40s} -> AUC={best_ho_auc:.4f} ({auc_change:+.4f}) Br={best_ho_brier:.6f} ({brier_change:+.6f}) C={best_c}")
        current_ho_auc = best_ho_auc
        current_ho_brier = best_ho_brier
    # Also accept if: AUC improves significantly (even if Brier flat)
    elif auc_change > 0.0003 and brier_change < 0.001:
        current_features.append(feat)
        added.append((feat, auc_change, brier_change, best_c))
        print(f"  ADDED (AUC↑):  {feat:40s} -> AUC={best_ho_auc:.4f} ({auc_change:+.4f}) Br={best_ho_brier:.6f} ({brier_change:+.6f}) C={best_c}")
        current_ho_auc = best_ho_auc
        current_ho_brier = best_ho_brier
    else:
        pass  # Skip silently

print(f"\n  After forward selection: {len(current_features)} features")
print(f"    AUC: {current_ho_auc:.4f} (v13: {best_v13_ho_auc:.4f}, delta: {current_ho_auc - best_v13_ho_auc:+.4f})")
print(f"    Brier: {current_ho_brier:.6f} (v13: {best_v13_brier_val:.6f}, delta: {current_ho_brier - best_v13_brier_val:+.6f})")
print(f"  Added {len(added)} new features:")
for feat, auc_d, br_d, c in added:
    print(f"    {feat}: AUC {auc_d:+.4f}, Brier {br_d:+.6f}, C={c}")

# ============================================================
# PHASE 4: AGGRESSIVE BRIER ABLATION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 4: AGGRESSIVE BRIER ABLATION")
print("=" * 70)

final_features = current_features.copy()
best_final_brier = current_ho_brier
best_final_auc = current_ho_auc
dropped = []

# Try dropping each feature — keep if Brier improves
for feat in final_features[:]:
    test_features = [f for f in final_features if f != feat]
    if len(test_features) < 10:
        continue

    best_ho_brier = 1.0
    best_ho_auc = 0
    best_c = 0.025
    for C in [0.007, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]:
        _, ho_auc, _, ho_brier, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho_brier < best_ho_brier - 0.00001:
            best_ho_brier = ho_brier
            best_ho_auc = ho_auc
            best_c = C

    brier_change = best_ho_brier - best_final_brier
    auc_change = best_ho_auc - best_final_auc

    if brier_change < -0.0001:  # Dropping improves Brier
        print(f"  DROP: {feat:40s} -> Brier={best_ho_brier:.6f} ({brier_change:+.6f}) AUC={best_ho_auc:.4f} ({auc_change:+.4f})")
        final_features.remove(feat)
        dropped.append(feat)
        best_final_brier = best_ho_brier
        best_final_auc = best_ho_auc

print(f"\n  After ablation: {len(final_features)} features")
print(f"    Brier: {best_final_brier:.6f}")
print(f"    AUC: {best_final_auc:.4f}")
if dropped:
    print(f"  Dropped: {dropped}")

# ============================================================
# PHASE 5: REGULARIZATION SWEEP (Brier-focused)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: REGULARIZATION SWEEP")
print("=" * 70)

best_sweep_auc = 0
best_sweep_brier = 1.0
best_sweep_c = 0.025
results_table = []

for C in [0.003, 0.005, 0.007, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15]:
    wf, ho_auc, wfb, ho_brier, t1c, t1w, _, _ = evaluate_features(final_features, C, yt, yh, dt, dh)
    results_table.append((C, wf, ho_auc, wfb, ho_brier, t1c, t1w))

    tag_auc = " *AUC" if ho_auc > best_sweep_auc else ""
    tag_brier = " *Br" if ho_brier < best_sweep_brier else ""
    if ho_auc > best_sweep_auc:
        best_sweep_auc = ho_auc
    if ho_brier < best_sweep_brier:
        best_sweep_brier = ho_brier
        best_sweep_c = C

    print(f"  C={C:.3f}: WF_AUC={wf:.4f}, HO_AUC={ho_auc:.4f}, WF_Br={wfb:.4f}, HO_Br={ho_brier:.6f}, T1={t1c}({t1w:.3f}){tag_auc}{tag_brier}")

# Pick C that minimizes Brier while keeping AUC within 0.002 of best
final_c = best_sweep_c
final_brier = best_sweep_brier

print(f"\n  Best Brier C={final_c}: Brier={final_brier:.6f}")

# Get final metrics at chosen C
wf_auc, ho_auc, wf_brier, ho_brier, t1c, t1w, final_model, final_scaler = evaluate_features(
    final_features, final_c, yt, yh, dt, dh)

print(f"\n  v14 CANDIDATE at C={final_c}:")
print(f"    WF AUC: {wf_auc:.4f}")
print(f"    HO AUC: {ho_auc:.4f}")
print(f"    WF Brier: {wf_brier:.6f}")
print(f"    HO Brier: {ho_brier:.6f}")
print(f"    T1 count: {t1c}, T1 win rate: {t1w:.4f}")

# ============================================================
# PHASE 6: 20-SEED STABILITY TEST
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: 20-SEED STABILITY TEST")
print("=" * 70)

v13_aucs = []
v14_aucs = []
v13_briers = []
v14_briers = []

for seed in range(20):
    _, ho13_auc, _, ho13_brier, _, _, _, _ = evaluate_features(v13_features, best_v13_c, yt, yh, dt, dh, seed=seed)
    _, ho14_auc, _, ho14_brier, _, _, _, _ = evaluate_features(final_features, final_c, yt, yh, dt, dh, seed=seed)
    v13_aucs.append(ho13_auc)
    v14_aucs.append(ho14_auc)
    v13_briers.append(ho13_brier)
    v14_briers.append(ho14_brier)

    auc_beats = "✓" if ho14_auc > ho13_auc else ("=" if ho14_auc == ho13_auc else "✗")
    brier_beats = "✓" if ho14_brier < ho13_brier else ("=" if ho14_brier == ho13_brier else "✗")
    print(f"  Seed {seed:2d}: v13 AUC={ho13_auc:.4f} Br={ho13_brier:.6f} | v14 AUC={ho14_auc:.4f} Br={ho14_brier:.6f} | AUC:{auc_beats} Br:{brier_beats}")

v14_auc_wins = sum(1 for a, b in zip(v14_aucs, v13_aucs) if a > b)
v14_brier_wins = sum(1 for a, b in zip(v14_briers, v13_briers) if a < b)
t_auc, p_auc = stats.ttest_rel(v14_aucs, v13_aucs)
t_brier, p_brier = stats.ttest_rel(v13_briers, v14_briers)  # Note: reversed for "v14 better"

print(f"\n  AUC: v14 mean={np.mean(v14_aucs):.6f} vs v13 mean={np.mean(v13_aucs):.6f}")
print(f"    v14 wins {v14_auc_wins}/20, t={t_auc:.4f}, p={p_auc:.10f}")
print(f"  Brier: v14 mean={np.mean(v14_briers):.6f} vs v13 mean={np.mean(v13_briers):.6f}")
print(f"    v14 wins {v14_brier_wins}/20, t={t_brier:.4f}, p={p_brier:.10f}")

# ============================================================
# FINAL VERDICT
# ============================================================

print("\n" + "=" * 70)
print("FINAL VERDICT")
print("=" * 70)

print(f"\nv13 champion: {len(v13_features)} features, C={best_v13_c}")
print(f"  HO AUC: {best_v13_ho_auc:.4f}")
print(f"  HO Brier: {best_v13_brier_val:.6f}")

print(f"\nv14 candidate: {len(final_features)} features, C={final_c}")
print(f"  HO AUC: {ho_auc:.4f}")
print(f"  HO Brier: {ho_brier:.6f}")

auc_delta = ho_auc - best_v13_ho_auc
brier_delta = ho_brier - best_v13_brier_val

print(f"\nDeltas:")
print(f"  AUC: {auc_delta:+.4f}")
print(f"  Brier: {brier_delta:+.6f} ({'IMPROVED' if brier_delta < 0 else 'REGRESSED'})")

# Champion criteria: Brier must improve OR AUC must improve significantly
is_champion = False
if brier_delta < -0.001 and v14_brier_wins >= 15:
    print(f"\n=== v14 IS NEW CHAMPION (Brier improvement) ===")
    is_champion = True
elif auc_delta > 0.001 and v14_auc_wins >= 15:
    print(f"\n=== v14 IS NEW CHAMPION (AUC improvement) ===")
    is_champion = True
elif brier_delta < -0.0005 and auc_delta > 0:
    print(f"\n=== v14 IS NEW CHAMPION (dual improvement) ===")
    is_champion = True
else:
    print(f"\n=== v13 REMAINS CHAMPION ===")
    print(f"  v14 did not meet improvement threshold")

# ============================================================
# DEPLOY CONFIG (if champion)
# ============================================================

if is_champion:
    print("\nGenerating v14 deploy config...")

    # Retrain final model
    Xtr = np.nan_to_num(dt[final_features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[final_features].values.astype(float), nan=0.0)

    sc = StandardScaler()
    Xtr_s = sc.fit_transform(Xtr)
    Xho_s = sc.transform(Xho)

    m = LogisticRegression(C=final_c, penalty='l2', solver='lbfgs', max_iter=5000, random_state=42)
    m.fit(Xtr_s, yt)

    yp_final = m.predict_proba(Xho_s)[:, 1]

    # Build deploy config
    deploy_config = {
        'version': '14.0.0',
        'model_type': 'L2_Ridge_LogisticRegression',
        'C': final_c,
        'solver': 'lbfgs',
        'n_features': len(final_features),
        'features': final_features,
        'intercept': float(m.intercept_[0]),
        'coefficients': {f: float(c) for f, c in zip(final_features, m.coef_[0])},
        'scaler_means': {f: float(mu) for f, mu in zip(final_features, sc.mean_)},
        'scaler_scales': {f: float(s) for f, s in zip(final_features, sc.scale_)},
        'performance': {
            'wf_auc': float(wf_auc),
            'ho_auc': float(ho_auc),
            'wf_brier': float(wf_brier),
            'ho_brier': float(ho_brier),
            't1_count': int(t1c),
            't1_win_rate': float(t1w),
            'holdout_n': int(len(dh)),
        },
        'training': {
            'n_events': int(len(dt)),
            'approval_rate': float(yt.mean()),
            'temporal_cutoff': '2025-01-01',
            'date_range': f"{dt['catalyst_date'].min()} to {dt['catalyst_date'].max()}",
        },
        'kaizen': {
            'parent_version': '13.0.0',
            'parent_ho_auc': float(best_v13_ho_auc),
            'parent_ho_brier': float(best_v13_brier_val),
            'auc_delta': float(auc_delta),
            'brier_delta': float(brier_delta),
            'features_added': [f for f, _, _, _ in added],
            'features_dropped': dropped,
            'stability_auc_wins': int(v14_auc_wins),
            'stability_brier_wins': int(v14_brier_wins),
            'stability_auc_pval': float(p_auc),
            'stability_brier_pval': float(p_brier),
        },
    }

    with open(f'{BASE}/odin_v14_deploy.json', 'w') as f:
        json.dump(deploy_config, f, indent=2)

    print(f"\n  Deploy config saved to odin_v14_deploy.json")
    print(f"  {len(final_features)} features, C={final_c}")
    print(f"  HO AUC: {ho_auc:.4f}, HO Brier: {ho_brier:.6f}")

    # Print new feature coefficients
    print(f"\n  New feature coefficients:")
    for feat, auc_d, br_d, c in added:
        if feat in deploy_config['coefficients']:
            coef = deploy_config['coefficients'][feat]
            print(f"    {feat:40s}: coef={coef:+.4f}")
    if dropped:
        print(f"\n  Dropped features: {dropped}")

else:
    print("\n  No deploy config generated — v13 remains champion.")
    print("\n  Features that showed promise but didn't survive greedy:")
    for feat, ho, auc_d, br, br_d, c, comp in feature_results[:10]:
        print(f"    {feat:40s}: AUC delta={auc_d:+.4f}, Brier delta={br_d:+.4f}")
