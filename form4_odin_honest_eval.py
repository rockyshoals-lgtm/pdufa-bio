#!/usr/bin/env python3
"""
Phase 1.5 — Honest eval: Form 4 insider trading features on ODIN v18.

Methodology (STRICT — matches Form 4 / ODIN v17 / Smart Money Phase 3 pattern):
  - Split: train <= 2022-12-31 / val 2023-2024 / test >= 2025
  - Baseline: ODIN v14 51-feature Ridge, C swept on val only
  - Candidate: baseline + Form 4 feature (one at a time), val gate Δval_AUC >= +0.002
  - Greedy forward: add the best surviving candidate, repeat up to max_rounds
  - Test touched once at the end, bootstrap 95% CI (n_boot=2000, seed=42)

Baseline feature engineering ports ODIN v14 Kaizen pipeline from odin_v14_kaizen.py
(lines 43-256) into this script so we build the real 51-feature matrix from raw
primitives, not a zero-filled stub.

Input:
  - ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv (ticker + catalyst_date + outcome + primitives)
  - form4_event_features.csv (ticker + catalyst_date + Form 4 features, T-1 compliant)

Output:
  - form4_odin_honest_results.json (methodology + baseline + candidate AUCs + lift CI + greedy log + final test AUC)
"""

import json
import csv
import sys
import warnings
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss
except Exception:
    print('ERROR: sklearn required. pip install scikit-learn')
    sys.exit(1)

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
WORKSPACE = Path('/sessions/confident-serene-ptolemy')
ODIN_CSV = BASE / 'ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv'
F4_CSV = WORKSPACE / 'form4_event_features.csv'
OUT_JSON = WORKSPACE / 'form4_odin_honest_results.json'

TRAIN_END = pd.Timestamp('2022-12-31')
VAL_START = pd.Timestamp('2023-01-01')
VAL_END = pd.Timestamp('2024-12-31')
TEST_START = pd.Timestamp('2025-01-01')

C_GRID = [0.005, 0.01, 0.025, 0.05, 0.10, 0.25]
VAL_GATE = 0.002
MAX_GREEDY_ROUNDS = 10
BOOT = 2000

# ODIN v14 51-feature list (training order)
ODIN_V14_FEATURES = [
    'btd_bin', 'ppm_flag_bin', 'ta_very_high', 'crl_rate_low', 'era_post', 'is_nda',
    'mfg_risk_bin', 'sponsor_win_rate', 'spa_6_15', 'resub1_x_naive', 'resub_class_2',
    'swr_x_btd', 'crl_rate_x_naive', 'swr_x_streak', 'swr_x_ta_vh', 'single_arm_x_btd',
    'resub2_x_experienced', 'momentum_x_btd', 'ta_base_x_naive', 'consistency_x_naive',
    'sponsor_consistency', 'ta_momentum', 'swr_cubed', 'ta_crl_streak', 'accel_orphan_btd',
    'ta_recent_rate_sq', 'safety_high_x_naive', 'adcom_x_naive', 'psychedelics_bin',
    'psychedelics_x_naive', 'ta_bucket_MOD', 'crl_count_x_naive', 'resub1_x_experienced',
    'resub1_x_swr', 'pw_orphan_drug_bin_x_resub_class_2', 'surrogate_x_ta_vh',
    'pw_priority_review_bin_x_resub_class_1', 'pw_desig_stack_x_resub_class_1',
    'pw_gene_therapy_bin_x_sponsor_streak', 'ft_x_safety', 'pw_priority_review_bin_x_btd_bin',
    'pw_is_oncology_x_resub_class_2', 'pw_is_oncology_x_mfg_risk_bin',
    'pw_double_crl_bin_x_resub_class_2', 'pw_priority_review_bin_x_resub_class_2',
    'gt_x_btd', 'pw_orphan_drug_bin_x_btd_bin', 'pw_double_crl_bin_x_ta_crl_streak',
    'pw_gene_therapy_bin_x_log_spa_sq', 'is_oncology', 'crl_rate_x_swr',
]


def _bin(x):
    """Coerce a truthy/string value to 1.0 or 0.0."""
    if x is True:
        return 1.0
    if isinstance(x, (int, float)) and not pd.isna(x):
        return 1.0 if float(x) != 0 else 0.0
    if isinstance(x, str):
        return 1.0 if x.strip().upper() in ('TRUE', '1', 'YES', 'Y', 'T') else 0.0
    return 0.0


def build_odin_v14_df():
    """
    Load ODIN CSV and compute the full ODIN v14 feature set via forward-only
    temporal accumulators + binary conversions + v13 interactions + v14 pillars.

    Returns:
        df: pandas DataFrame with 51 feature columns + ticker, catalyst_date,
            outcome, target (0/1) columns. Rows with missing date or outcome
            are DROPPED.
    """
    df = pd.read_csv(ODIN_CSV)
    df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
    df = df.dropna(subset=['catalyst_date']).copy()
    # Keep only events with a resolvable outcome
    df['outcome_u'] = df['outcome'].astype(str).str.strip().str.upper()
    valid_outcomes = ('APPROVE', 'APPROVAL', 'CRL', '1', '0', 'POS', 'POSITIVE', 'NEG', 'NEGATIVE')
    df = df[df['outcome_u'].isin(valid_outcomes)].copy()

    def _to_y(o):
        if o in ('APPROVE', 'APPROVAL', '1', 'POS', 'POSITIVE'):
            return 1
        return 0
    df['target'] = df['outcome_u'].apply(_to_y)
    # Normalize outcome string to APPROVAL / CRL for the temporal accumulators
    df['outcome_norm'] = df['target'].map({1: 'APPROVAL', 0: 'CRL'})

    # Deterministic sort matching kaizen script
    df = df.sort_values(['catalyst_date', 'event_id'] if 'event_id' in df.columns else 'catalyst_date').reset_index(drop=True)

    # ------------------------------------------------------------
    # Forward-only temporal features
    # ------------------------------------------------------------
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
            df.at[idx, 'sponsor_consistency'] = 1.0 - float(np.std(all_outcomes[-10:]))

        ti = ta_win_counts[ta]
        df.at[idx, 'ta_recent_rate'] = ti['wins'] / ti['total'] if ti['total'] >= 5 else 0.5
        df.at[idx, 'ta_event_density'] = ti['total']
        df.at[idx, 'ta_crl_streak'] = ta_crl_streaks.get(ta, 0)

        ta_rec = ta_recent_events[ta][-10:] if len(ta_recent_events[ta]) >= 10 else ta_recent_events[ta]
        if len(ta_rec) >= 5:
            ta_rec_wins = sum(1 for _, o in ta_rec if o == 'APPROVAL')
            df.at[idx, 'ta_momentum'] = ta_rec_wins / len(ta_rec) - (ti['wins'] / ti['total'] if ti['total'] > 0 else 0.5)

        is_app = row['outcome_norm'] == 'APPROVAL'
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
        ta_recent_events[ta].append((row['catalyst_date'], row['outcome_norm']))
        sponsor_outcomes_all[company_key].append(1 if is_app else 0)

    # ------------------------------------------------------------
    # Primitive coercions
    # ------------------------------------------------------------
    spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
    crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
    resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
    safety_sev = pd.to_numeric(df['safety_signal_severity'], errors='coerce').fillna(0.0)
    ta_base = pd.to_numeric(df['ta_base_score'], errors='coerce').fillna(0.0)
    prior_crl_count = pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0)
    app_type = df['application_type'].fillna('')

    # Binary features
    df['btd_bin'] = df['btd'].apply(_bin)
    df['ppm_flag_bin'] = df['ppm_flag'].apply(_bin)
    df['ta_very_high'] = df['ta_very_high_risk'].apply(_bin)
    df['orphan_bin'] = df['orphan'].apply(_bin)
    df['accel_bin'] = df['accelerated_approval'].apply(_bin)
    df['sponsor_naive'] = (spa == 0).astype(float)
    df['sponsor_experienced'] = (spa >= 5).astype(float)
    df['mfg_risk_bin'] = df['manufacturing_risk'].apply(_bin)
    df['form_483_bin'] = df['form_483_issues'].apply(_bin)
    df['single_arm_bin'] = df['single_arm_study'].apply(_bin)
    df['is_nda'] = app_type.astype(str).str.upper().isin(['NDA']).astype(float)
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
    df['had_adcom_bin'] = df['had_adcom'].apply(_bin)
    df['adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
    df['psychedelics_bin'] = df['psychedelics'].apply(_bin)
    df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']
    ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
    df['ta_bucket_MOD'] = (df['ta_bucket_v2'].map(ta_bucket_map).fillna(1) == 1).astype(float)
    df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
    df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']
    df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']

    # v14 Pillar 1: Untapped base features
    df['surrogate_bin'] = df['surrogate_endpoint'].apply(_bin)
    df['fast_track_bin'] = df['fast_track'].apply(_bin)
    df['gene_therapy_bin'] = df['gene_therapy'].apply(_bin)
    df['orphan_drug_bin'] = df['orphan_bin']
    df['priority_review_bin'] = df['priority_review'].apply(_bin)
    df['double_crl_bin'] = df['double_crl_flag'].apply(_bin) if 'double_crl_flag' in df.columns else 0.0
    if isinstance(df['double_crl_bin'], float):
        df['double_crl_bin'] = 0.0

    # v14 Pillar 2: Surrogate interactions (only surrogate_x_ta_vh needed for final)
    df['surrogate_x_btd'] = df['surrogate_bin'] * df['btd_bin']
    df['surrogate_x_naive'] = df['surrogate_bin'] * df['sponsor_naive']
    df['surrogate_x_swr'] = df['surrogate_bin'] * df['sponsor_win_rate']
    df['surrogate_x_accel'] = df['surrogate_bin'] * df['accel_bin']
    df['surrogate_x_orphan'] = df['surrogate_bin'] * df['orphan_bin']
    df['surrogate_x_ta_vh'] = df['surrogate_bin'] * df['ta_very_high']

    # v14 Pillar 3: Fast track interactions (only ft_x_safety in final)
    df['ft_x_naive'] = df['fast_track_bin'] * df['sponsor_naive']
    df['ft_x_experienced'] = df['fast_track_bin'] * df['sponsor_experienced']
    df['ft_x_btd'] = df['fast_track_bin'] * df['btd_bin']
    df['ft_x_swr'] = df['fast_track_bin'] * df['sponsor_win_rate']
    df['ft_x_oncology'] = df['fast_track_bin'] * df['therapeutic_area'].astype(str).str.contains('Oncology', na=False, case=False).astype(float)
    df['ft_x_resub1'] = df['fast_track_bin'] * df['resub_class_1']
    df['ft_x_crl_rate'] = df['fast_track_bin'] * crl_rate
    df['ft_x_safety'] = df['fast_track_bin'] * df['safety_high']

    # v14 Pillar 4: TA granularity
    df['is_oncology'] = df['therapeutic_area'].astype(str).str.contains('Oncology', na=False, case=False).astype(float)
    df['is_infectious'] = df['therapeutic_area'].astype(str).str.contains('Infectious', na=False, case=False).astype(float)
    df['is_rare'] = df['therapeutic_area'].astype(str).str.contains('Rare', na=False, case=False).astype(float)
    df['is_cns'] = df['therapeutic_area'].astype(str).str.contains('CNS|Neurology', na=False, case=False).astype(float)
    df['is_immunology'] = df['therapeutic_area'].astype(str).str.contains('Immunology', na=False, case=False).astype(float)
    df['onc_x_naive'] = df['is_oncology'] * df['sponsor_naive']
    df['onc_x_experienced'] = df['is_oncology'] * df['sponsor_experienced']
    df['onc_x_btd'] = df['is_oncology'] * df['btd_bin']
    df['onc_x_swr'] = df['is_oncology'] * df['sponsor_win_rate']
    df['rare_x_btd'] = df['is_rare'] * df['btd_bin']

    # v14 Pillar 5: Gene therapy + designation stacking
    df['gt_x_naive'] = df['gene_therapy_bin'] * df['sponsor_naive']
    df['gt_x_btd'] = df['gene_therapy_bin'] * df['btd_bin']
    df['gt_x_orphan'] = df['gene_therapy_bin'] * df['orphan_bin']
    df['orphan_x_naive'] = df['orphan_bin'] * df['sponsor_naive']
    df['orphan_x_swr'] = df['orphan_bin'] * df['sponsor_win_rate']
    df['desig_stack'] = (df['btd_bin'] + df['fast_track_bin'] + df['orphan_bin'] + df['accel_bin'] + df['priority_review_bin']).astype(float)
    df['desig_stack_sq'] = df['desig_stack'] ** 2
    df['desig_rich'] = (df['desig_stack'] >= 3).astype(float)

    # v14 Pillar 6: Non-linear transforms
    df['swr_sq'] = df['sponsor_win_rate'] ** 2
    df['crl_rate_sq'] = crl_rate ** 2
    df['crl_rate_x_swr'] = crl_rate * df['sponsor_win_rate']
    df['log_spa_cubed'] = np.log1p(spa) ** 3
    df['ta_base_sq'] = ta_base ** 2
    df['safety_sev_bin'] = (safety_sev >= 2).astype(float)
    df['safety_sev_x_swr'] = safety_sev * df['sponsor_win_rate']

    # v14 Pillar 7: Exhaustive pairwise (matches kaizen script exactly)
    new_bases = ['surrogate_bin', 'fast_track_bin', 'gene_therapy_bin', 'orphan_drug_bin',
                 'priority_review_bin', 'double_crl_bin', 'is_oncology', 'desig_stack']
    key_existing = ['sponsor_win_rate', 'sponsor_naive', 'sponsor_experienced', 'btd_bin',
                    'ta_very_high', 'resub_class_1', 'resub_class_2', 'mfg_risk_bin',
                    'sponsor_streak', 'ta_crl_streak', 'log_spa_sq', 'crl_rate_low']
    for nb in new_bases:
        for ke in key_existing:
            fname = f'pw_{nb}_x_{ke}'
            df[fname] = df[nb] * df[ke]

    # Verify every feature in ODIN_V14_FEATURES is present
    missing = [f for f in ODIN_V14_FEATURES if f not in df.columns]
    if missing:
        raise RuntimeError(f'Missing engineered features: {missing}')

    # NaN-safe the final feature columns (pairwise may produce NaN if any factor was NaN)
    for f in ODIN_V14_FEATURES:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0.0)

    return df


def load_f4_features():
    """Load Form 4 event feature CSV. Key = (ticker, catalyst_date_str)."""
    d = {}
    feature_cols = []
    if not F4_CSV.exists():
        print(f'WARNING: {F4_CSV} not found')
        return d, feature_cols
    with open(F4_CSV) as f:
        reader = csv.DictReader(f)
        feature_cols = [c for c in reader.fieldnames if c.startswith('f4_')]
        for r in reader:
            key = (r['ticker'].upper(), r['catalyst_date'])
            d[key] = {c: float(r[c]) if r[c] not in ('', None) else 0.0 for c in feature_cols}
    return d, feature_cols


def fit_score(X_train, y_train, X_val, y_val, X_test, y_test, C):
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    lr = LogisticRegression(C=C, solver='lbfgs', max_iter=5000, penalty='l2')
    lr.fit(X_train_s, y_train)
    p_val = lr.predict_proba(X_val_s)[:, 1]
    p_test = lr.predict_proba(X_test_s)[:, 1]
    val_auc = roc_auc_score(y_val, p_val)
    test_auc = roc_auc_score(y_test, p_test)
    test_brier = brier_score_loss(y_test, p_test)
    return {
        'val_auc': float(val_auc),
        'test_auc': float(test_auc),
        'test_brier': float(test_brier),
        'p_test': p_test.tolist(),
        'p_val': p_val.tolist(),
        'coefs': lr.coef_[0].tolist(),
        'intercept': float(lr.intercept_[0]),
    }


def bootstrap_auc_diff(y, p_baseline, p_candidate, n_boot=BOOT, seed=42):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p_b = np.asarray(p_baseline)
    p_c = np.asarray(p_candidate)
    n = len(y)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(y[idx])) < 2:
            continue
        auc_b = roc_auc_score(y[idx], p_b[idx])
        auc_c = roc_auc_score(y[idx], p_c[idx])
        diffs.append(auc_c - auc_b)
    diffs = np.asarray(diffs)
    return {
        'mean': float(diffs.mean()),
        'ci95_lo': float(np.percentile(diffs, 2.5)),
        'ci95_hi': float(np.percentile(diffs, 97.5)),
        'p_lift_gt_0': float((diffs > 0).mean()),
    }


def bootstrap_auc(y, p, n_boot=BOOT, seed=42):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p = np.asarray(p)
    n = len(y)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(y[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y[idx], p[idx]))
    aucs = np.asarray(aucs)
    return {
        'ci95_lo': float(np.percentile(aucs, 2.5)),
        'ci95_hi': float(np.percentile(aucs, 97.5)),
    }


def main():
    print('[+] Building ODIN v14 feature DataFrame (51 features from raw primitives)')
    df = build_odin_v14_df()
    print(f'    {len(df):,} events after outcome filter')
    print(f'    approval rate: {df["target"].mean():.4f}')

    # Build X matrix in exact v14 feature order
    X_base = df[ODIN_V14_FEATURES].values.astype(float)
    y = df['target'].values.astype(int)
    print(f'    X_base shape: {X_base.shape}')

    # Quick sanity: check variance on each feature
    low_var = [f for f, v in zip(ODIN_V14_FEATURES, X_base.var(axis=0)) if v < 1e-10]
    if low_var:
        print(f'    WARNING: {len(low_var)} features with near-zero variance: {low_var[:5]}...')

    # Form 4 features
    print('[+] Loading Form 4 features')
    f4_map, f4_cols = load_f4_features()
    print(f'    {len(f4_map):,} Form 4 events, {len(f4_cols)} feature columns')

    # Attach Form 4 features per row (default 0 if unmatched)
    n_matched = 0
    X_f4 = np.zeros((len(df), len(f4_cols)))
    df_date_str = df['catalyst_date'].dt.strftime('%Y-%m-%d').values
    df_ticker = df['ticker'].astype(str).str.upper().values
    for i in range(len(df)):
        key = (df_ticker[i], df_date_str[i])
        if key in f4_map:
            n_matched += 1
            for j, c in enumerate(f4_cols):
                X_f4[i, j] = f4_map[key].get(c, 0.0)
    print(f'    Matched: {n_matched:,}/{len(df):,} ODIN events ({100*n_matched/max(1,len(df)):.1f}%)')

    # Temporal split
    dates = df['catalyst_date'].values
    train_mask = dates <= np.datetime64(TRAIN_END)
    val_mask = (dates >= np.datetime64(VAL_START)) & (dates <= np.datetime64(VAL_END))
    test_mask = dates >= np.datetime64(TEST_START)
    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    test_idx = np.where(test_mask)[0]
    print(f'[+] Split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}')

    # C sweep on baseline (val-only selection)
    print('[+] C sweep on baseline (val-only selection)')
    best_C = None
    best_val = -1.0
    c_results = {}
    for C in C_GRID:
        r = fit_score(X_base[train_idx], y[train_idx], X_base[val_idx], y[val_idx],
                      X_base[test_idx], y[test_idx], C)
        c_results[C] = r
        print(f'    C={C}: val_auc={r["val_auc"]:.4f}, test_auc={r["test_auc"]:.4f}')
        if r['val_auc'] > best_val:
            best_val = r['val_auc']
            best_C = C
    print(f'[+] Best C on val: {best_C} (val_auc={best_val:.4f})')

    baseline = c_results[best_C]
    p_baseline_test = baseline['p_test']

    # Greedy forward selection over Form 4 features
    print(f'[+] Greedy forward selection over {len(f4_cols)} Form 4 features')
    selected = []
    selected_idx = []
    greedy_log = []
    current_val = best_val
    current_p_test = p_baseline_test

    for round_num in range(1, MAX_GREEDY_ROUNDS + 1):
        best_cand = None
        best_cand_val = current_val
        best_cand_delta = -1.0
        best_cand_result = None
        best_cand_idx = None
        round_scores = []

        for j, cname in enumerate(f4_cols):
            if j in selected_idx:
                continue
            cols = selected_idx + [j]
            X_tr = np.hstack([X_base[train_idx], X_f4[train_idx][:, cols]])
            X_v = np.hstack([X_base[val_idx], X_f4[val_idx][:, cols]])
            X_te = np.hstack([X_base[test_idx], X_f4[test_idx][:, cols]])
            try:
                r = fit_score(X_tr, y[train_idx], X_v, y[val_idx], X_te, y[test_idx], best_C)
            except Exception:
                continue
            delta = r['val_auc'] - current_val
            round_scores.append({'feature': cname, 'delta_val': delta, 'val_auc': r['val_auc']})
            if delta > best_cand_delta:
                best_cand_delta = delta
                best_cand_val = r['val_auc']
                best_cand = cname
                best_cand_idx = j
                best_cand_result = r

        round_scores.sort(key=lambda x: -x['delta_val'])
        top5 = round_scores[:5]
        print(f'    Round {round_num}: best candidate={best_cand} Δval={best_cand_delta:+.4f}')
        print(f'              top5: {[(t["feature"], round(t["delta_val"],4)) for t in top5]}')

        if best_cand_delta < VAL_GATE:
            print(f'    STOP: best delta {best_cand_delta:.4f} < gate {VAL_GATE}')
            greedy_log.append({
                'round': round_num,
                'stopped': True,
                'best_candidate': best_cand,
                'delta_val': best_cand_delta,
                'top5': top5,
            })
            break

        selected.append(best_cand)
        selected_idx.append(best_cand_idx)
        current_val = best_cand_val
        current_p_test = best_cand_result['p_test']
        greedy_log.append({
            'round': round_num,
            'selected': best_cand,
            'delta_val': best_cand_delta,
            'new_val_auc': current_val,
            'new_test_auc': best_cand_result['test_auc'],
            'top5': top5,
        })

    # Final model
    if selected_idx:
        X_tr = np.hstack([X_base[train_idx], X_f4[train_idx][:, selected_idx]])
        X_v = np.hstack([X_base[val_idx], X_f4[val_idx][:, selected_idx]])
        X_te = np.hstack([X_base[test_idx], X_f4[test_idx][:, selected_idx]])
        final = fit_score(X_tr, y[train_idx], X_v, y[val_idx], X_te, y[test_idx], best_C)
    else:
        final = baseline

    # Test CIs + lift CI
    test_auc_ci = bootstrap_auc(y[test_idx], final['p_test'])
    baseline_test_auc_ci = bootstrap_auc(y[test_idx], baseline['p_test'])
    lift_ci = bootstrap_auc_diff(y[test_idx], baseline['p_test'], final['p_test'])

    results = {
        'model': 'form4_odin_honest_v18',
        'generated_utc': datetime.utcnow().isoformat() + 'Z',
        'methodology': {
            'train_end': TRAIN_END.strftime('%Y-%m-%d'),
            'val_range': [VAL_START.strftime('%Y-%m-%d'), VAL_END.strftime('%Y-%m-%d')],
            'test_start': TEST_START.strftime('%Y-%m-%d'),
            'C_grid': C_GRID,
            'val_gate': VAL_GATE,
            'max_greedy_rounds': MAX_GREEDY_ROUNDS,
            'bootstrap_n': BOOT,
            'bootstrap_seed': 42,
            'baseline_feature_engineering': 'ported from odin_v14_kaizen.py (51 features)',
        },
        'data': {
            'n_events': int(len(df)),
            'n_train': int(len(train_idx)),
            'n_val': int(len(val_idx)),
            'n_test': int(len(test_idx)),
            'train_approval_rate': float(y[train_idx].mean()),
            'val_approval_rate': float(y[val_idx].mean()),
            'test_approval_rate': float(y[test_idx].mean()),
            'n_f4_candidate_features': len(f4_cols),
            'n_odin_events_matched_with_si': int(n_matched),
            'f4_coverage_pct': 100 * n_matched / max(1, len(df)),
        },
        'c_sweep': {str(C): {'val_auc': c_results[C]['val_auc'], 'test_auc': c_results[C]['test_auc']} for C in C_GRID},
        'best_C_on_val': best_C,
        'baseline': {
            'val_auc': baseline['val_auc'],
            'test_auc': baseline['test_auc'],
            'test_auc_ci95': [baseline_test_auc_ci['ci95_lo'], baseline_test_auc_ci['ci95_hi']],
            'test_brier': baseline['test_brier'],
            'n_features': len(ODIN_V14_FEATURES),
        },
        'greedy_log': greedy_log,
        'selected_f4_features': selected,
        'final': {
            'val_auc': final['val_auc'],
            'test_auc': final['test_auc'],
            'test_auc_ci95': [test_auc_ci['ci95_lo'], test_auc_ci['ci95_hi']],
            'test_brier': final['test_brier'],
            'n_features': len(ODIN_V14_FEATURES) + len(selected_idx),
            'lift_vs_baseline': {
                'test_auc_delta': final['test_auc'] - baseline['test_auc'],
                'lift_ci95': [lift_ci['ci95_lo'], lift_ci['ci95_hi']],
                'p_lift_gt_0': lift_ci['p_lift_gt_0'],
            },
        },
    }

    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)

    print('\n=== SUMMARY ===')
    print(f'Baseline val_auc={baseline["val_auc"]:.4f}  test_auc={baseline["test_auc"]:.4f}  CI95=[{baseline_test_auc_ci["ci95_lo"]:.4f}, {baseline_test_auc_ci["ci95_hi"]:.4f}]')
    print(f'Final    val_auc={final["val_auc"]:.4f}  test_auc={final["test_auc"]:.4f}  CI95=[{test_auc_ci["ci95_lo"]:.4f}, {test_auc_ci["ci95_hi"]:.4f}]')
    print(f'Lift     Δtest={final["test_auc"]-baseline["test_auc"]:+.4f}  CI95=[{lift_ci["ci95_lo"]:+.4f}, {lift_ci["ci95_hi"]:+.4f}]  p(lift>0)={lift_ci["p_lift_gt_0"]:.3f}')
    print(f'Selected features ({len(selected)}): {selected}')
    print(f'\nWrote {OUT_JSON}')


if __name__ == '__main__':
    main()
