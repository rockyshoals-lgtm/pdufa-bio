#!/usr/bin/env python3
"""
Smart Money Phase 3: Honest 3-way eval of god-tier-fund 13F features
====================================================================

Setup (copied from odin_v14_honest.py — same split, same features, same
temporal pipeline). Add 12 smart money features as candidates.

Protocol:
  1. Replicate ODIN v14 honest baseline (51 features, C swept on VAL)
  2. Greedy forward selection on VAL AUC with smart money candidates
     (gate Δ VAL AUC ≥ +0.002)
  3. Re-sweep C on chosen feature set (VAL only)
  4. Touch TEST once — report final AUC, Brier, bootstrap CI
  5. 20-seed stability on chosen feature set
  6. Ship JSON + optional deploy weights

Split:
  train ≤ 2022-12-31
  val 2023-01-01 to 2024-12-31
  test ≥ 2025-01-01
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
ODIN_CSV = BASE / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
SM_CSV = BASE / "smart_money_event_features.csv"
OUT_JSON = BASE / "smart_money_phase3_results.json"

# ---- helpers copied from odin_v14_honest.py ----

def build_temporal_features(df_in, df_val_test=None, df_holdout_test=None):
    """Chronological forward-only temporal feature engineering."""
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


def engineer_all_features(df_in):
    df = df_in.copy()

    spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
    crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
    resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
    safety_sev = pd.to_numeric(df.get('safety_signal_severity', 0), errors='coerce').fillna(0.0)
    ta_base = pd.to_numeric(df.get('ta_base_score', 0), errors='coerce').fillna(0.0)
    prior_crl_count = pd.to_numeric(df.get('prior_crl_count', 0), errors='coerce').fillna(0)
    app_type = df['application_type'].fillna('')

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
    df['had_adcom_bin'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
    df['psychedelics_bin'] = df.get('psychedelics', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']
    ta_bucket_map = {'LOW': 0, 'MOD': 1, 'HIGH': 2, 'VHIGH': 3}
    df['ta_bucket_MOD'] = (df.get('ta_bucket_v2', 'MOD').map(ta_bucket_map).fillna(1) == 1).astype(float)
    df['crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
    df['resub1_x_experienced'] = df['resub_class_1'] * df['sponsor_experienced']
    df['resub1_x_swr'] = df['resub_class_1'] * df['sponsor_win_rate']
    df['surrogate_bin'] = df.get('surrogate_endpoint', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['fast_track_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['gene_therapy_bin'] = df.get('gene_therapy', 0).apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
    df['priority_review_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
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


V14_FEATURES = [
    "btd_bin","ppm_flag_bin","ta_very_high","crl_rate_low","era_post","is_nda",
    "mfg_risk_bin","sponsor_win_rate","spa_6_15","resub1_x_naive","resub_class_2",
    "swr_x_btd","crl_rate_x_naive","swr_x_streak","swr_x_ta_vh","single_arm_x_btd",
    "resub2_x_experienced","momentum_x_btd","ta_base_x_naive","consistency_x_naive",
    "sponsor_consistency","ta_momentum","swr_cubed","ta_crl_streak","accel_orphan_btd",
    "ta_recent_rate_sq","safety_high_x_naive","adcom_x_naive","psychedelics_bin",
    "psychedelics_x_naive","ta_bucket_MOD","crl_count_x_naive","resub1_x_experienced",
    "resub1_x_swr","pw_orphan_drug_bin_x_resub_class_2","surrogate_x_ta_vh",
    "pw_priority_review_bin_x_resub_class_1","pw_desig_stack_x_resub_class_1",
    "pw_gene_therapy_bin_x_sponsor_streak","ft_x_safety",
    "pw_priority_review_bin_x_btd_bin","pw_is_oncology_x_resub_class_2",
    "pw_is_oncology_x_mfg_risk_bin","pw_double_crl_bin_x_resub_class_2",
    "pw_priority_review_bin_x_resub_class_2","gt_x_btd","pw_orphan_drug_bin_x_btd_bin",
    "pw_double_crl_bin_x_ta_crl_streak","pw_gene_therapy_bin_x_log_spa_sq",
    "is_oncology","crl_rate_x_swr",
]

# Smart money raw feature columns (from Phase 2 CSV)
SM_RAW = [
    "god_tier_any_present",
    "god_tier_count",
    "god_tier_weighted_count",
    "god_tier_total_value_usd",
    "god_tier_max_fund_value_usd",
    "god_tier_top_fund_weight",
    "god_tier_concentration",
    "god_tier_quarter_delta_value",
    "god_tier_new_positions",
    "god_tier_exited_positions",
    "god_tier_total_shares",
    "god_tier_snapshot_lag_days",
]


def build_smart_money_candidates(df):
    """Engineer derived / log-transformed smart money features. Returns list of col names added."""
    added = []

    # Log-transform big-$ features (heavy-tailed)
    for col in ["god_tier_total_value_usd", "god_tier_max_fund_value_usd", "god_tier_total_shares"]:
        new_col = f"log1p_{col}"
        df[new_col] = np.log1p(np.maximum(df[col].fillna(0), 0))
        added.append(new_col)

    # Signed log for quarter delta (can be negative)
    v = df["god_tier_quarter_delta_value"].fillna(0)
    df["signed_log_quarter_delta"] = np.sign(v) * np.log1p(np.abs(v))
    added.append("signed_log_quarter_delta")

    # Snapshot lag clipped (sometimes -1 means no holding data)
    lag = df["god_tier_snapshot_lag_days"].fillna(-1)
    df["sm_lag_days_pos"] = np.where(lag >= 0, lag, 365.0)  # 1y default if missing
    df["sm_lag_fresh"] = (df["sm_lag_days_pos"] <= 60).astype(float)  # within 60d (recent 13F)
    added += ["sm_lag_days_pos", "sm_lag_fresh"]

    # Interaction: god_tier presence × weighted_count (quality-weighted presence)
    df["sm_presence_x_weighted"] = df["god_tier_any_present"].fillna(0) * df["god_tier_weighted_count"].fillna(0)
    added.append("sm_presence_x_weighted")

    # Interaction: concentration × count (both high = strong conviction from a strong pool)
    df["sm_conc_x_count"] = df["god_tier_concentration"].fillna(0) * df["god_tier_count"].fillna(0)
    added.append("sm_conc_x_count")

    return added


def main():
    print("=" * 80)
    print("SMART MONEY PHASE 3 — HONEST 3-WAY EVAL vs ODIN v14 BASELINE")
    print("=" * 80)

    # ---- load ----
    print("\nLoading ODIN training CSV...")
    df = pd.read_csv(ODIN_CSV)
    df['catalyst_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
    df = df.sort_values('catalyst_date').reset_index(drop=True)
    df = df.dropna(subset=['catalyst_date', 'outcome']).copy()
    print(f"  {len(df)} events")

    # Standardize outcome
    df['y'] = (df['outcome'] == 'APPROVAL').astype(int)

    print("\nLoading smart money event features...")
    sm = pd.read_csv(SM_CSV)
    sm['event_id'] = sm['event_id'].astype(str)
    df['event_id'] = df['event_id'].astype(str)
    before = len(df)
    df = df.merge(sm[['event_id'] + SM_RAW], on='event_id', how='left')

    # Fill missing smart money features with neutrals
    for col in SM_RAW:
        if col == "god_tier_snapshot_lag_days":
            df[col] = df[col].fillna(-1)
        else:
            df[col] = df[col].fillna(0)

    sm_any = df["god_tier_any_present"].sum()
    print(f"  merged; {int(sm_any)}/{len(df)} events ({100*sm_any/len(df):.1f}%) have god tier presence")

    # ---- split ----
    cutoff_train = pd.Timestamp('2022-12-31')
    cutoff_val = pd.Timestamp('2024-12-31')

    df_train = df[df['catalyst_date'] <= cutoff_train].copy().reset_index(drop=True)
    df_val = df[(df['catalyst_date'] > cutoff_train) & (df['catalyst_date'] <= cutoff_val)].copy().reset_index(drop=True)
    df_test = df[df['catalyst_date'] > cutoff_val].copy().reset_index(drop=True)

    print(f"\nTrain: {len(df_train)}, Val: {len(df_val)}, Test: {len(df_test)}")
    print(f"  Approval rates: train {df_train['y'].mean():.1%} / val {df_val['y'].mean():.1%} / test {df_test['y'].mean():.1%}")

    # Smart money coverage per split
    for name, ds in [('train', df_train), ('val', df_val), ('test', df_test)]:
        pct = 100 * ds['god_tier_any_present'].mean()
        print(f"  Smart money presence ({name}): {pct:.1f}%")

    # ---- temporal features ----
    print("\nBuilding temporal features (forward-only)...")
    df_train, df_val, df_test = build_temporal_features(df_train, df_val, df_test)

    # ---- v14 feature engineering ----
    print("Engineering v14 features...")
    df_train = engineer_all_features(df_train)
    df_val = engineer_all_features(df_val)
    df_test = engineer_all_features(df_test)

    # ---- smart money candidates ----
    print("Building smart money candidate features...")
    sm_derived_train = build_smart_money_candidates(df_train)
    build_smart_money_candidates(df_val)
    build_smart_money_candidates(df_test)

    # full candidate pool = raw + derived
    sm_candidates = SM_RAW + sm_derived_train
    print(f"  Smart money candidate pool: {len(sm_candidates)} features")
    print(f"    raw:     {SM_RAW}")
    print(f"    derived: {sm_derived_train}")

    y_train = df_train['y'].values
    y_val = df_val['y'].values
    y_test = df_test['y'].values

    # =====================================================
    # PHASE 0: REPLICATE v14 HONEST BASELINE
    # =====================================================
    print("\n" + "=" * 70)
    print("PHASE 0: ODIN v14 HONEST BASELINE (51 features, C swept on VAL)")
    print("=" * 70)

    def fit_eval(features, C, seed=42):
        scaler = StandardScaler()
        Xtr = scaler.fit_transform(df_train[features].fillna(0).values)
        Xv = scaler.transform(df_val[features].fillna(0).values)
        Xte = scaler.transform(df_test[features].fillna(0).values)
        model = LogisticRegression(C=C, solver='lbfgs', max_iter=2000, random_state=seed)
        model.fit(Xtr, y_train)
        p_val = model.predict_proba(Xv)[:, 1]
        p_test = model.predict_proba(Xte)[:, 1]
        p_train = model.predict_proba(Xtr)[:, 1]
        return {
            "model": model,
            "scaler": scaler,
            "train_auc": roc_auc_score(y_train, p_train),
            "val_auc": roc_auc_score(y_val, p_val),
            "test_auc": roc_auc_score(y_test, p_test),
            "train_brier": brier_score_loss(y_train, p_train),
            "val_brier": brier_score_loss(y_val, p_val),
            "test_brier": brier_score_loss(y_test, p_test),
            "p_test": p_test,
        }

    C_grid = [0.007, 0.01, 0.015, 0.02, 0.025, 0.03, 0.05, 0.1, 0.15, 0.2]

    best_baseline_val = 0
    best_baseline_c = None
    baseline_results = None
    for C in C_grid:
        r = fit_eval(V14_FEATURES, C)
        print(f"  C={C:.3f}: val_auc={r['val_auc']:.4f}  test_auc={r['test_auc']:.4f}")
        if r['val_auc'] > best_baseline_val:
            best_baseline_val = r['val_auc']
            best_baseline_c = C
            baseline_results = r

    print(f"\nBaseline best: C={best_baseline_c}  val={baseline_results['val_auc']:.4f}  "
          f"test={baseline_results['test_auc']:.4f}  brier_test={baseline_results['test_brier']:.4f}")

    # =====================================================
    # PHASE 1: GREEDY FORWARD SELECTION on SM candidates
    # =====================================================
    print("\n" + "=" * 70)
    print("PHASE 1: SMART MONEY GREEDY FORWARD SELECTION (val gate +0.002)")
    print("=" * 70)

    GATE = 0.002
    chosen_features = list(V14_FEATURES)
    chosen_sm = []
    current_best_val = best_baseline_val
    current_c = best_baseline_c
    rounds = []

    # Allow up to 6 rounds
    for round_idx in range(6):
        best_cand = None
        best_cand_val = current_best_val
        best_cand_test = baseline_results['test_auc']
        best_cand_c = current_c

        # Score each remaining candidate individually at the current baseline C
        round_scores = []
        for cand in sm_candidates:
            if cand in chosen_sm:
                continue
            feats = chosen_features + [cand]
            # Sweep C quickly for this candidate
            best_cand_local_val = 0
            best_cand_local = None
            for C in C_grid:
                r = fit_eval(feats, C)
                if r['val_auc'] > best_cand_local_val:
                    best_cand_local_val = r['val_auc']
                    best_cand_local = (C, r)
            round_scores.append((cand, best_cand_local_val, best_cand_local[0]))
            if best_cand_local_val > best_cand_val:
                best_cand_val = best_cand_local_val
                best_cand = cand
                best_cand_c = best_cand_local[0]

        # Rank this round
        round_scores.sort(key=lambda x: -x[1])
        print(f"\n  Round {round_idx+1} top 5 candidates (val AUC):")
        for cand, val_auc, c in round_scores[:5]:
            delta = val_auc - current_best_val
            print(f"    {cand:40s}  val={val_auc:.4f}  Δ={delta:+.4f}  C={c}")

        delta = best_cand_val - current_best_val
        if best_cand is None or delta < GATE:
            print(f"  → No candidate clears +{GATE} gate. STOP.")
            rounds.append({"round": round_idx+1, "chose": None, "delta": float(delta), "candidates_scored": len(round_scores)})
            break

        print(f"  → ADD {best_cand}  Δ={delta:+.4f}  new_C={best_cand_c}  new_val={best_cand_val:.4f}")
        chosen_sm.append(best_cand)
        chosen_features.append(best_cand)
        current_best_val = best_cand_val
        current_c = best_cand_c
        rounds.append({
            "round": round_idx+1,
            "chose": best_cand,
            "delta": float(delta),
            "new_val_auc": float(best_cand_val),
            "new_C": float(best_cand_c),
        })

    # =====================================================
    # PHASE 2: RE-SWEEP C on FINAL FEATURE SET (VAL only)
    # =====================================================
    print("\n" + "=" * 70)
    print("PHASE 2: RE-SWEEP C on FINAL FEATURE SET (VAL only)")
    print("=" * 70)
    final_best_val = 0
    final_c = None
    final_result = None
    for C in C_grid:
        r = fit_eval(chosen_features, C)
        print(f"  C={C:.3f}: val_auc={r['val_auc']:.4f}  test_auc={r['test_auc']:.4f}")
        if r['val_auc'] > final_best_val:
            final_best_val = r['val_auc']
            final_c = C
            final_result = r

    print(f"\n  Final: C={final_c}  val={final_best_val:.4f}")

    # =====================================================
    # PHASE 3: TOUCH TEST ONCE — bootstrap CI
    # =====================================================
    print("\n" + "=" * 70)
    print("PHASE 3: TEST (touched once) — bootstrap CI, 20-seed stability")
    print("=" * 70)

    p_test_final = final_result['p_test']
    p_test_baseline = baseline_results['p_test']

    rng = np.random.default_rng(42)
    n_test = len(y_test)
    n_boot = 2000
    boot_final = np.empty(n_boot)
    boot_base = np.empty(n_boot)
    boot_lift = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n_test, n_test)
        yb = y_test[idx]
        if yb.sum() == 0 or yb.sum() == n_test:
            boot_final[b] = np.nan
            boot_base[b] = np.nan
            boot_lift[b] = np.nan
            continue
        boot_final[b] = roc_auc_score(yb, p_test_final[idx])
        boot_base[b] = roc_auc_score(yb, p_test_baseline[idx])
        boot_lift[b] = boot_final[b] - boot_base[b]

    def ci95(arr):
        arr = arr[~np.isnan(arr)]
        return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]

    final_test_auc = final_result['test_auc']
    baseline_test_auc = baseline_results['test_auc']
    lift = final_test_auc - baseline_test_auc
    lift_ci = ci95(boot_lift)
    p_lift_pos = float(np.mean(boot_lift > 0))

    print(f"\n  Baseline test AUC:  {baseline_test_auc:.4f}  CI95 {ci95(boot_base)}")
    print(f"  Final test AUC:     {final_test_auc:.4f}  CI95 {ci95(boot_final)}")
    print(f"  Lift (final-base):  {lift:+.4f}  CI95 {lift_ci}  p(lift>0)={p_lift_pos:.3f}")
    print(f"  Final test Brier:   {final_result['test_brier']:.4f}")
    print(f"  Baseline test Brier: {baseline_results['test_brier']:.4f}")

    # 20-seed stability
    print("\n  20-seed stability on final feature set...")
    seed_val = []
    seed_test = []
    for seed in range(20):
        r = fit_eval(chosen_features, final_c, seed=seed)
        seed_val.append(r['val_auc'])
        seed_test.append(r['test_auc'])
    seed_val = np.array(seed_val)
    seed_test = np.array(seed_test)
    print(f"    Val  AUC: {seed_val.mean():.4f} ± {seed_val.std():.4f} (min {seed_val.min():.4f}, max {seed_val.max():.4f})")
    print(f"    Test AUC: {seed_test.mean():.4f} ± {seed_test.std():.4f} (min {seed_test.min():.4f}, max {seed_test.max():.4f})")

    # =====================================================
    # VERDICT
    # =====================================================
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    if lift_ci[0] > 0:
        verdict = "PROMOTE — lift CI entirely above zero"
    elif lift > 0 and p_lift_pos >= 0.80 and len(chosen_sm) > 0:
        verdict = "WEAK_LIFT — positive point estimate but CI spans zero"
    elif len(chosen_sm) == 0:
        verdict = "NULL — no smart money feature cleared val gate +0.002"
    else:
        verdict = "NULL — features selected but no test lift"

    print(f"\n  {verdict}")
    print(f"  chosen smart money features ({len(chosen_sm)}): {chosen_sm}")
    print(f"  final C = {final_c}")
    print(f"  final feature count = {len(chosen_features)}")

    # =====================================================
    # SAVE
    # =====================================================
    out = {
        "version": "smart_money_phase3_v1",
        "honest_3way_split": {
            "cutoff_train": "2022-12-31",
            "cutoff_val": "2024-12-31",
            "train_n": int(len(y_train)),
            "val_n": int(len(y_val)),
            "test_n": int(len(y_test)),
            "train_approval_rate": float(df_train['y'].mean()),
            "val_approval_rate": float(df_val['y'].mean()),
            "test_approval_rate": float(df_test['y'].mean()),
            "train_sm_presence": float(df_train['god_tier_any_present'].mean()),
            "val_sm_presence": float(df_val['god_tier_any_present'].mean()),
            "test_sm_presence": float(df_test['god_tier_any_present'].mean()),
        },
        "baseline": {
            "features": V14_FEATURES,
            "n_features": len(V14_FEATURES),
            "best_c": float(best_baseline_c),
            "val_auc": float(best_baseline_val),
            "test_auc": float(baseline_test_auc),
            "test_brier": float(baseline_results['test_brier']),
            "test_auc_ci95": ci95(boot_base),
        },
        "smart_money_candidates": sm_candidates,
        "greedy_forward_rounds": rounds,
        "final": {
            "features": chosen_features,
            "n_features": len(chosen_features),
            "smart_money_chosen": chosen_sm,
            "best_c": float(final_c),
            "val_auc": float(final_best_val),
            "test_auc": float(final_test_auc),
            "test_brier": float(final_result['test_brier']),
            "test_auc_ci95": ci95(boot_final),
        },
        "lift": {
            "test_auc_lift": float(lift),
            "test_auc_lift_ci95": lift_ci,
            "p_lift_positive": p_lift_pos,
        },
        "stability": {
            "seeds": 20,
            "val_auc_mean": float(seed_val.mean()),
            "val_auc_std": float(seed_val.std()),
            "val_auc_min": float(seed_val.min()),
            "val_auc_max": float(seed_val.max()),
            "test_auc_mean": float(seed_test.mean()),
            "test_auc_std": float(seed_test.std()),
            "test_auc_min": float(seed_test.min()),
            "test_auc_max": float(seed_test.max()),
        },
        "verdict": verdict,
    }

    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {OUT_JSON}")


if __name__ == "__main__":
    main()
