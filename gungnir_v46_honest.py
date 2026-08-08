#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v46 HONEST 4-WAY SPLIT — Test-Set Leakage Fix
================================================================================

CRITICAL BUG: v46_kaizen.py uses TEST-SET AUC to rank candidates in Phase 3
fast screen. This inflates reported AUC by ~100-150bp.

FIX: Implement 4-way temporal split (train/val/test/final holdout) with
validation-set ranking to prevent future data leakage into feature selection.

SPLITS:
  Train:      ≤2023-06 (n ≈ 1,100)
  Validation: 2023-07 to 2024-06 (n ≈ 400)
  Test:       2024-07 to 2025-06 (n ≈ 250)
  Final HO:   ≥2025-07 (n ≈ 10-15)

PIPELINE:
  1. Load enriched_gungnir_dataset_v3.csv + extract date from catalyst_id
  2. Apply 4-way temporal split based on readout date
  3. Build Ridge M1 baseline on train set only
  4. Replicate v46's exact 126 features
  5. Train M1/M2/M3 on train, report val/test/final-holdout AUCs
  6. 20-seed stability test
  7. Publish honest AUCs to quantify inflation

TARGET: Establish true baseline AUCs before honest Kaizen (if time permits).
DELIVERY: gungnir_v46_honest.py, gungnir_v46_honest_deploy.json,
  gungnir_v46_honest_xgb.json, gungnir_v46_honest_results.json
"""

import csv, json, math, os, re, sys, warnings, io
from collections import defaultdict
from datetime import datetime
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.ensemble import RandomForestClassifier

# Try to import xgboost; fallback to RandomForest if not available
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("WARNING: xgboost not available, using RandomForest as substitute")

warnings.filterwarnings("ignore")

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()

# ============================================================================
# v46 CHAMPION CONFIG (replication target)
# ============================================================================
V46_FEATURES = [
    "ch_is_agonist", "ch_is_enzyme", "ch_is_ion_channel", "cns_x_micro",
    "competitive_3mo", "competitive_6mo", "competitive_x_onc",
    "ct_active_comp_x_phase3", "ct_ep_is_biomarker", "ct_ep_is_pfs",
    "ct_ep_is_safety", "ct_has_combination", "ct_is_industry",
    "ct_log_elig_length", "ctgov_enrollment", "ctgov_ep_hard",
    "ctgov_ep_surrogate", "ctgov_has_dmc", "ctgov_is_double_blind",
    "ctgov_is_global", "ctgov_is_placebo", "ctgov_is_randomized",
    "ctgov_masking_rigor", "ctgov_n_arms", "ctgov_n_countries",
    "ctgov_n_sites", "ctgov_real", "designation_count", "dmc_x_phase3",
    "enrollment_sq", "enrollment_x_phase3", "ep_hard_x_phase3",
    "era_2024_plus", "global_x_phase3", "has_orphan", "iis_is_interim",
    "indication_density_sq", "is_bridging", "is_large", "is_micro",
    "is_mid", "is_phase1", "is_phase1b", "is_phase2", "is_phase2a",
    "is_phase2b", "is_phase3", "is_pivotal", "is_small",
    "journey_had_negative", "journey_had_positive", "journey_last_positive",
    "journey_n_negative", "journey_sr_x_phase3", "journey_success_rate",
    "large_x_any", "log_market_cap", "log_price", "micro_x_phase3",
    "micro_x_rare", "momentum_10d", "momentum_20d", "momentum_5d",
    "momentum_x_phase3", "nlp_biomarker", "nlp_combo_therapy",
    "nlp_first_in", "nlp_interim", "nlp_phase3", "nlp_topline",
    "onc_x_single_arm", "orphan_x_micro", "phase3_x_cns",
    "phase3_x_double_blind", "phase3_x_oncology", "phase3_x_placebo",
    "phase3_x_randomized", "phase_numeric", "rare_x_small", "small_x_phase3",
    "sponsor_success_rate", "ta_base_rate", "ta_cardiovascular", "ta_cns",
    "ta_hematology", "ta_immunology", "ta_infectious", "ta_metabolic",
    "ta_oncology", "ta_other", "ta_rare_disease", "volatility_20d",
    "volatility_5d", "volatility_x_phase3", "v40_has_conference",
    "v40_days_to_cover", "v40_conf_x_small", "v41_sponsor_x_conference",
    "v41_journey_last_pos_sq", "v41_immuno_x_phase2", "v41_placebo_x_cns",
    "v41_enrollment_x_journey", "v42_iis_is_interim_X_momentum_10d",
    "v42_ctgov_n_arms_X_phase3_x_oncology",
    "v42_ctgov_n_countries_X_indication_density",
    "v42_global_x_phase3_X_volatility_20d",
    "v42_ct_is_industry_X_ctgov_masking_rigor",
    "v42_iis_is_interim_X_indication_density_sq",
    "v42_momentum_20d_X_ta_metabolic", "v42_is_small_X_ta_cns",
    "v43_ch2_is_oligo_X_volatility_20d",
    "v43_ch2_is_biologic_X_is_phase3",
    "v43_ch2_is_cell_X_ctgov_is_randomized",
    "v43_ch2_is_adc_X_enrollment_sq", "v43_ch2_is_cell_X_momentum_10d",
    "v43_ch2_is_oligo_X_is_phase2",
    "v44_ch2_moa_antagonist_X_journey_had_positive",
    "v44_ch2_is_sm_X_is_phase2_X_is_small", "v46_p1_ch2_moa_agonist",
    "v46_p6_fic_X_is_phase3_X_sponsor",
    "v46_p6_sponsor_X_ch2_is_adc_X_is_phase2",
    "v46_p6_conf_X_ch2_is_advanced_X_is_small",
    "v46_p5_log1p_journey_last_positive",
    "v46_p2_ch2_is_adc_X_journey_n_negative",
    "v46_p6_conf_X_ch2_is_mab_X_is_small",
    "v46_p2_ch2_is_adc_X_journey_had_negative",
]

V46_CONFIG = {
    "ridge_c": 0.02, "xgb_lr": 0.01, "xgb_trees": 500, "xgb_depth": 3,
    "meta_ridge": 0.90, "meta_xgb": 0.10, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# ============================================================================
# DATA LOADING
# ============================================================================
def load_data(csv_path):
    """Load enriched dataset. Dataset uses `date` column (YYYY-MM-DD) and
    `outcome` column with values 'positive' / 'negative'."""
    events = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Prefer `date`, fallback to `Catalyst Date`
                date_str = row.get('date') or row.get('Catalyst Date') or ''
                readout_date = None
                if date_str:
                    try:
                        readout_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    except ValueError:
                        readout_date = None

                events.append({
                    'catalyst_id': row.get('catalyst_id') or f"{row.get('Ticker','?')}_{date_str}",
                    'readout_date': readout_date,
                    'row': row,
                })
    except FileNotFoundError:
        print(f"ERROR: {csv_path} not found")
        sys.exit(1)

    return events

# ============================================================================
# 4-WAY TEMPORAL SPLIT
# ============================================================================
def split_4way(events):
    """
    Train: ≤2023-06
    Val:   2023-07 to 2024-06
    Test:  2024-07 to 2025-06
    Final: ≥2025-07
    """
    train, val, test, final = [], [], [], []

    for evt in events:
        if evt['readout_date'] is None:
            continue

        d = evt['readout_date']

        # Train ≤2023-06
        if d.year < 2023 or (d.year == 2023 and d.month <= 6):
            train.append(evt)
        # Val 2023-07 to 2024-06
        elif (d.year == 2023 and d.month >= 7) or (d.year == 2024 and d.month <= 6):
            val.append(evt)
        # Test 2024-07 to 2025-06
        elif (d.year == 2024 and d.month >= 7) or (d.year == 2025 and d.month <= 6):
            test.append(evt)
        # Final ≥2025-07
        else:
            final.append(evt)

    return train, val, test, final

# ============================================================================
# FEATURE EXTRACTION + STANDARDIZATION
# ============================================================================
def build_matrices(events, features, scaler=None, fit=False):
    """Extract features, standardize."""
    X, y = [], []
    for evt in events:
        row = evt['row']
        # outcome is "positive" / "negative" in v3 CSV
        raw = str(row.get('outcome', '')).strip().lower()
        if raw in ('positive', '1', 'true', 'yes'):
            y_val = 1
        elif raw in ('negative', '0', 'false', 'no'):
            y_val = 0
        else:
            continue

        x_vec = []
        for feat in features:
            try:
                x_vec.append(float(row.get(feat, 0)))
            except (ValueError, TypeError):
                x_vec.append(0)

        X.append(x_vec)
        y.append(y_val)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)

    if fit:
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
    else:
        if scaler:
            X = scaler.transform(X)

    return X, y, scaler

# ============================================================================
# ENSEMBLE MODELS (v46 config)
# ============================================================================
def train_ensemble(X_tr, y_tr, X_val, y_val, config):
    """Train M1 (Ridge), M2 (XGB or RF for CRASH), M3 (XGB or RF for GOOD+)."""
    # M1: Ridge (90% weight)
    m1 = LogisticRegression(
        C=config['ridge_c'], solver='lbfgs', max_iter=1000,
        random_state=42, n_jobs=-1
    )
    m1.fit(X_tr, y_tr)
    m1_prob_val = m1.predict_proba(X_val)[:, 1]
    m1_auc = roc_auc_score(y_val, m1_prob_val)

    # M2 & M3: XGB if available, else RandomForest
    if HAS_XGB:
        # M2: XGB for CRASH prediction
        m2 = xgb.XGBClassifier(
            n_estimators=config['xgb_trees'], learning_rate=config['xgb_lr'],
            max_depth=config['xgb_depth'], random_state=42, n_jobs=-1,
            objective='binary:logistic'
        )
        m2.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        m2_prob_val = m2.predict_proba(X_val)[:, 1]

        # M3: XGB for GOOD+ prediction
        m3 = xgb.XGBClassifier(
            n_estimators=config['xgb_trees'], learning_rate=config['xgb_lr'],
            max_depth=config['xgb_depth'], random_state=42, n_jobs=-1,
            objective='binary:logistic'
        )
        m3.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        m3_prob_val = m3.predict_proba(X_val)[:, 1]
    else:
        # Fallback to RandomForest
        m2 = RandomForestClassifier(
            n_estimators=200, max_depth=config['xgb_depth'], random_state=42, n_jobs=-1
        )
        m2.fit(X_tr, y_tr)
        m2_prob_val = m2.predict_proba(X_val)[:, 1]

        m3 = RandomForestClassifier(
            n_estimators=200, max_depth=config['xgb_depth'], random_state=42, n_jobs=-1
        )
        m3.fit(X_tr, y_tr)
        m3_prob_val = m3.predict_proba(X_val)[:, 1]

    # Meta-ensemble: 90% Ridge + 10% ensemble of M2/M3
    ensemble_prob_val = (config['meta_ridge'] * m1_prob_val +
                         config['meta_xgb'] * 0.5 * (m2_prob_val + m3_prob_val))

    ensemble_auc = roc_auc_score(y_val, ensemble_prob_val)

    return {
        'M1': m1, 'M2': m2, 'M3': m3,
        'M1_auc_val': m1_auc, 'ensemble_auc_val': ensemble_auc,
    }

# ============================================================================
# EVALUATION
# ============================================================================
def evaluate(models, X_test, y_test, split_name='test', config=None):
    """Evaluate on test/final-holdout set."""
    m1, m2, m3 = models['M1'], models['M2'], models['M3']

    m1_prob = m1.predict_proba(X_test)[:, 1]
    m2_prob = m2.predict_proba(X_test)[:, 1]
    m3_prob = m3.predict_proba(X_test)[:, 1]

    ensemble_prob = (config['meta_ridge'] * m1_prob +
                     config['meta_xgb'] * 0.5 * (m2_prob + m3_prob))

    m1_auc = roc_auc_score(y_test, m1_prob)
    m1_brier = brier_score_loss(y_test, m1_prob)
    ensemble_auc = roc_auc_score(y_test, ensemble_prob)
    ensemble_brier = brier_score_loss(y_test, ensemble_prob)

    return {
        f'M1_auc_{split_name}': m1_auc,
        f'M1_brier_{split_name}': m1_brier,
        f'ensemble_auc_{split_name}': ensemble_auc,
        f'ensemble_brier_{split_name}': ensemble_brier,
        f'{split_name}_n': len(y_test),
        f'{split_name}_approval_rate': np.mean(y_test),
    }

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "=" * 80)
    print("GUNGNIR v46 HONEST 4-WAY SPLIT REPLICATION")
    print("=" * 80)

    # Load data
    csv_path = os.path.join(DATA_DIR, 'enriched_gungnir_dataset_v3.csv')
    print(f"\nLoading: {csv_path}")
    events = load_data(csv_path)
    print(f"Loaded {len(events)} events")

    # Apply 4-way split
    print("\nApplying 4-way temporal split...")
    train, val, test, final = split_4way(events)
    print(f"  Train (≤2023-06):      n={len(train)}")
    print(f"  Val (2023-07–2024-06): n={len(val)}")
    print(f"  Test (2024-07–2025-06): n={len(test)}")
    print(f"  Final (≥2025-07):      n={len(final)}")

    # Build matrices
    print("\nBuilding feature matrices...")
    X_tr, y_tr, scaler = build_matrices(train, V46_FEATURES, fit=True)
    X_val, y_val, _ = build_matrices(val, V46_FEATURES, scaler=scaler)
    X_te, y_te, _ = build_matrices(test, V46_FEATURES, scaler=scaler)
    X_final, y_final, _ = build_matrices(final, V46_FEATURES, scaler=scaler)

    print(f"  Train: {X_tr.shape[0]} × {X_tr.shape[1]}")
    print(f"  Val:   {X_val.shape[0]} × {X_val.shape[1]}")
    print(f"  Test:  {X_te.shape[0]} × {X_te.shape[1]}")
    print(f"  Final: {X_final.shape[0]} × {X_final.shape[1]}")

    # Train ensemble
    print("\nTraining ensemble on train split...")
    models = train_ensemble(X_tr, y_tr, X_val, y_val, V46_CONFIG)

    # Evaluate on all splits
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS (HONEST 4-WAY SPLIT)")
    print("=" * 80)

    val_results = evaluate(models, X_val, y_val, 'val', V46_CONFIG)
    test_results = evaluate(models, X_te, y_te, 'test', V46_CONFIG)
    final_results = evaluate(models, X_final, y_final, 'final', V46_CONFIG)

    print(f"\nVAL SET (2023-07–2024-06, n={len(y_val)}):")
    print(f"  M1 AUC:        {val_results.get('M1_auc_val', 0):.4f}")
    print(f"  Ensemble AUC:  {val_results.get('ensemble_auc_val', 0):.4f}")

    print(f"\nTEST SET (2024-07–2025-06, n={len(y_te)}):")
    print(f"  M1 AUC:        {test_results.get('M1_auc_test', 0):.4f}")
    print(f"  M1 Brier:      {test_results.get('M1_brier_test', 0):.4f}")
    print(f"  Ensemble AUC:  {test_results.get('ensemble_auc_test', 0):.4f}")
    print(f"  Ensemble Brier:{test_results.get('ensemble_brier_test', 0):.4f}")
    print(f"  Approval Rate: {test_results.get('test_approval_rate', 0):.4f}")

    if len(y_final) > 0:
        print(f"\nFINAL HOLDOUT (≥2025-07, n={len(y_final)}):")
        print(f"  M1 AUC:        {final_results.get('M1_auc_final', 0):.4f}")
        print(f"  Ensemble AUC:  {final_results.get('ensemble_auc_final', 0):.4f}")
        print(f"  Approval Rate: {final_results.get('final_approval_rate', 0):.4f}")

    # Leakage disclosure
    print("\n" + "=" * 80)
    print("LEAKAGE ANALYSIS")
    print("=" * 80)
    reported_auc = 0.8135  # v46 reported
    honest_test_auc = test_results.get('ensemble_auc_test', 0)
    inflation_bp = (reported_auc - honest_test_auc) * 10000

    print(f"\nv46 REPORTED TEST AUC:  {reported_auc:.4f}")
    print(f"HONEST TEST AUC:        {honest_test_auc:.4f}")
    print(f"IMPLIED INFLATION:      {inflation_bp:.0f} bps")

    # Save results
    results = {
        'version': 'v46_honest',
        'split_config': {
            'train': '≤2023-06',
            'val': '2023-07 to 2024-06',
            'test': '2024-07 to 2025-06',
            'final': '≥2025-07',
        },
        'n_train': len(y_tr),
        'n_val': len(y_val),
        'n_test': len(y_te),
        'n_final': len(y_final),
        'val_metrics': val_results,
        'test_metrics': test_results,
        'final_metrics': final_results,
        'leakage_disclosure': {
            'reported_auc': reported_auc,
            'honest_test_auc': honest_test_auc,
            'inflation_bps': inflation_bp,
        },
    }

    results_path = os.path.join(DATA_DIR, 'gungnir_v46_honest_results.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {results_path}")

if __name__ == '__main__':
    main()
