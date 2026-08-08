#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  9REALMS — LightGBM V2.0 CHALLENGER MODEL                       ║
║                                                                  ║
║  Trains a LightGBM classifier on ODIN_ENRICHED features as a    ║
║  challenger to the hand-tuned v1071 / ULTIMATE V2 logit scorer. ║
║                                                                  ║
║  Walk-forward validation: train on years < Y, test on year Y     ║
║  Final model: trained on all data, calibrated via Platt scaling  ║
║                                                                  ║
║  Features: 30 engineered from ODIN_ENRICHED_1349.csv columns     ║
║  Target: outcome_binary (1=APPROVAL, 0=CRL)                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import math
import os
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss, precision_score
from sklearn.model_selection import StratifiedKFold

REALMS_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REALMS_ROOT / "data"
MODELS_DIR = REALMS_ROOT / "models"
VALIDATION_DIR = REALMS_ROOT / "validation"

DATASET_PATH = DATA_DIR / "ODIN_ENRICHED_1349.csv"


# ── Feature Engineering ─────────────────────────────────────────

FEATURE_COLS = [
    # Binary designations
    "btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
    # Sponsor
    "experienced_sponsor", "sponsor_prior_approvals",
    # AdCom
    "had_adcom", "adcom_vote_pct",
    # Risk flags
    "manufacturing_risk", "prior_crl",
    # Rates
    "base_rate_ta", "base_rate_modality", "base_rate_mfg", "base_rate_stack",
    # Designation stack
    "designation_stack_count", "designation_trap_flag",
    # Financial
    "cash_runway_months", "pe_ratio", "price_to_book",
    # Social/sentiment
    "sentiment_30d", "insider_net_90d", "analyst_consensus",
    "social_sentiment_avg", "social_bullish_pct", "galaxy_score",
    # Safety
    "ae_count_12m", "warning_letters_2y",
    # Publication/trials
    "publications_12m", "sponsor_active_trials",
]

# Engineered features added at runtime
ENGINEERED = [
    "is_resubmission", "is_class1_resub", "is_gene_therapy",
    "is_oncology", "is_neurology", "is_pain",
    "is_hoeg_era", "year",
    "desig_x_experienced",  # interaction: designation stack × experienced
    "prior_crl_x_base_rate",  # interaction: prior CRL × base rate
]


def _bflag(row, col):
    v = row.get(col, "")
    if isinstance(v, bool):
        return v
    return str(v).strip().upper() in ("TRUE", "1", "YES", "T")


def _fval(val, default=0.0):
    try:
        v = val.strip() if isinstance(val, str) else str(val)
        return float(v) if v else default
    except (ValueError, TypeError):
        return default


def extract_features(row):
    """Extract feature vector from a single CSV row."""
    feats = {}

    # Base columns
    for col in FEATURE_COLS:
        raw = row.get(col, "")
        if col in ("btd", "orphan", "priority_review", "fast_track",
                    "accelerated_approval", "experienced_sponsor",
                    "had_adcom", "manufacturing_risk", "prior_crl",
                    "designation_trap_flag"):
            feats[col] = 1.0 if _bflag(row, col) else 0.0
        else:
            feats[col] = _fval(raw)

    # Engineered features
    resub = str(row.get("resubmission_class", "") or "").strip()
    feats["is_resubmission"] = 1.0 if resub else 0.0
    feats["is_class1_resub"] = 1.0 if resub == "1" else 0.0

    modality = (row.get("modality", "") or "").strip().lower()
    feats["is_gene_therapy"] = 1.0 if modality in ("gene therapy", "gene_therapy",
                                                      "cell therapy", "cell_therapy") else 0.0

    ta = (row.get("therapeutic_area", "") or "").strip().lower()
    feats["is_oncology"] = 1.0 if ta == "oncology" else 0.0
    feats["is_neurology"] = 1.0 if ta in ("neurology", "cns", "psychiatry") else 0.0
    feats["is_pain"] = 1.0 if "pain" in ta else 0.0

    cat_date = row.get("catalyst_date", "")
    try:
        year = int(cat_date[:4]) if cat_date else 2024
    except ValueError:
        year = 2024
    feats["year"] = float(year)
    feats["is_hoeg_era"] = 1.0 if year >= 2024 else 0.0

    # Interactions
    feats["desig_x_experienced"] = feats.get("designation_stack_count", 0) * feats.get("experienced_sponsor", 0)
    feats["prior_crl_x_base_rate"] = feats.get("prior_crl", 0) * feats.get("base_rate_ta", 0)

    return feats


def load_dataset(path=None):
    """Load dataset and return features array, labels, years."""
    path = path or DATASET_PATH
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    all_features = []
    labels = []
    years = []
    tickers = []

    for row in rows:
        outcome = (row.get("outcome", "") or "").strip().upper()
        if outcome not in ("APPROVAL", "CRL"):
            continue

        feats = extract_features(row)
        all_features.append(feats)
        labels.append(1 if outcome == "APPROVAL" else 0)

        cat_date = row.get("catalyst_date", "")
        try:
            yr = int(cat_date[:4]) if cat_date else 0
        except ValueError:
            yr = 0
        years.append(yr)
        tickers.append(row.get("ticker", ""))

    # Convert to arrays
    feature_names = FEATURE_COLS + ENGINEERED
    X = np.array([[f.get(col, 0.0) for col in feature_names] for f in all_features])
    y = np.array(labels)
    years = np.array(years)

    return X, y, years, tickers, feature_names


# ── Training ────────────────────────────────────────────────────

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_child_samples": 10,
    "scale_pos_weight": 1.0,  # Will adjust per fold
    "verbose": -1,
    "seed": 42,
    "n_estimators": 500,
    "early_stopping_rounds": 50,
}


def walk_forward_validation(X, y, years, feature_names):
    """Walk-forward: train on years < Y, test on year Y."""
    unique_years = sorted(set(years[years > 0]))
    results = {}

    for test_year in unique_years:
        if test_year < 2021:  # Need at least 1 year of training
            continue

        train_mask = (years < test_year) & (years > 0)
        test_mask = years == test_year

        if train_mask.sum() < 50 or test_mask.sum() < 10:
            continue

        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]

        # Adjust scale_pos_weight for class imbalance
        params = dict(LGB_PARAMS)
        neg = (y_train == 0).sum()
        pos = (y_train == 1).sum()
        params["scale_pos_weight"] = neg / max(pos, 1)

        dtrain = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
        dval = lgb.Dataset(X_test, label=y_test, reference=dtrain, feature_name=feature_names)

        model = lgb.train(
            params,
            dtrain,
            valid_sets=[dval],
            callbacks=[lgb.log_evaluation(0)],
        )

        preds = model.predict(X_test)
        auc = roc_auc_score(y_test, preds)
        brier = brier_score_loss(y_test, preds)

        # Tier4 precision: among preds < 0.40, what % are CRL?
        t4_mask = preds < 0.40
        t4_prec = 0.0
        if t4_mask.sum() > 0:
            t4_prec = (y_test[t4_mask] == 0).sum() / t4_mask.sum()

        # Tier1 precision: among preds >= 0.85, what % are approval?
        t1_mask = preds >= 0.85
        t1_prec = 0.0
        if t1_mask.sum() > 0:
            t1_prec = (y_test[t1_mask] == 1).sum() / t1_mask.sum()

        results[int(test_year)] = {
            "N_train": int(train_mask.sum()),
            "N_test": int(test_mask.sum()),
            "CRL_rate": round(1 - y_test.mean(), 3),
            "AUC": round(auc, 4),
            "Brier": round(brier, 4),
            "Tier4_Precision": round(t4_prec, 4),
            "Tier1_Precision": round(t1_prec, 4),
            "N_Tier4": int(t4_mask.sum()),
            "N_Tier1": int(t1_mask.sum()),
            "n_estimators": model.best_iteration if model.best_iteration else params["n_estimators"],
        }

        print(f"  Year {test_year}: N={test_mask.sum()}, AUC={auc:.4f}, "
              f"Brier={brier:.4f}, T4P={t4_prec:.1%}, T1P={t1_prec:.1%}")

    return results


def train_final_model(X, y, feature_names):
    """Train final model on all data with 5-fold CV for calibration."""
    params = dict(LGB_PARAMS)
    neg = (y == 0).sum()
    pos = (y == 1).sum()
    params["scale_pos_weight"] = neg / max(pos, 1)

    # 5-fold CV for best iteration
    dtrain = lgb.Dataset(X, label=y, feature_name=feature_names)
    cv_results = lgb.cv(
        params,
        dtrain,
        num_boost_round=500,
        nfold=5,
        stratified=True,
        callbacks=[lgb.log_evaluation(0)],
        return_cvbooster=False,
    )

    best_iter = len(cv_results["valid auc-mean"])
    print(f"\n  Best iteration from CV: {best_iter}")
    std_key = "valid auc-stdv" if "valid auc-stdv" in cv_results else "valid auc-stddev"
    print(f"  CV AUC: {cv_results['valid auc-mean'][-1]:.4f} "
          f"± {cv_results[std_key][-1]:.4f}")

    # Train final model
    params["n_estimators"] = best_iter
    if "early_stopping_rounds" in params:
        del params["early_stopping_rounds"]

    model = lgb.LGBMClassifier(**params)
    model.fit(X, y)

    # Calibrate with Platt scaling (sigmoid)
    calibrated = CalibratedClassifierCV(model, cv=5, method="sigmoid")
    calibrated.fit(X, y)

    return model, calibrated, best_iter


def get_feature_importance(model, feature_names):
    """Get feature importance from LightGBM model."""
    importances = model.feature_importances_
    pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    return pairs


def main():
    """Full LightGBM challenger pipeline."""
    print("=" * 60)
    print("  9REALMS LightGBM V2.0 CHALLENGER")
    print("=" * 60)

    os.makedirs(VALIDATION_DIR, exist_ok=True)

    # Load data
    print("\nLoading dataset...")
    X, y, years, tickers, feature_names = load_dataset()
    print(f"  Features: {X.shape[1]}, Events: {X.shape[0]}")
    print(f"  Approvals: {(y==1).sum()}, CRLs: {(y==0).sum()}")

    # Walk-forward validation
    print("\n── Walk-Forward Validation ──")
    wf_results = walk_forward_validation(X, y, years, feature_names)

    # Overall walk-forward AUC
    all_wf_aucs = [r["AUC"] for r in wf_results.values()]
    avg_wf_auc = np.mean(all_wf_aucs) if all_wf_aucs else 0
    print(f"\n  Average WF AUC: {avg_wf_auc:.4f}")

    # Train final model
    print("\n── Training Final Model ──")
    model, calibrated, best_iter = train_final_model(X, y, feature_names)

    # Feature importance
    print("\n── Feature Importance (top 15) ──")
    importances = get_feature_importance(model, feature_names)
    for name, imp in importances[:15]:
        print(f"  {name:<30} {imp:>6}")

    # Full-dataset metrics (in-sample, for comparison)
    preds_raw = model.predict_proba(X)[:, 1]
    preds_cal = calibrated.predict_proba(X)[:, 1]

    auc_raw = roc_auc_score(y, preds_raw)
    auc_cal = roc_auc_score(y, preds_cal)
    brier_raw = brier_score_loss(y, preds_raw)
    brier_cal = brier_score_loss(y, preds_cal)

    # Tier metrics on calibrated
    t4_mask = preds_cal < 0.40
    t4_prec = (y[t4_mask] == 0).sum() / t4_mask.sum() if t4_mask.sum() > 0 else 0
    t1_mask = preds_cal >= 0.85
    t1_prec = (y[t1_mask] == 1).sum() / t1_mask.sum() if t1_mask.sum() > 0 else 0

    print(f"\n── In-Sample Metrics (calibrated) ──")
    print(f"  AUC:            {auc_cal:.4f}")
    print(f"  Brier:          {brier_cal:.4f}")
    print(f"  Tier4 Precision:{t4_prec:.1%} ({t4_mask.sum()} events)")
    print(f"  Tier1 Precision:{t1_prec:.1%} ({t1_mask.sum()} events)")

    # Save model artifacts
    model_path = MODELS_DIR / "lightgbm_challenger_v1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": model,
            "calibrated": calibrated,
            "feature_names": feature_names,
            "best_iteration": best_iter,
            "params": LGB_PARAMS,
        }, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\n  Saved model: {model_path}")

    # Save validation results
    val_results = {
        "model": "LightGBM V2.0 Challenger",
        "dataset": "ODIN_ENRICHED_1349.csv",
        "n_events": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "feature_names": feature_names,
        "walk_forward": wf_results,
        "avg_wf_auc": round(avg_wf_auc, 4),
        "in_sample": {
            "AUC_raw": round(auc_raw, 4),
            "AUC_calibrated": round(auc_cal, 4),
            "Brier_raw": round(brier_raw, 4),
            "Brier_calibrated": round(brier_cal, 4),
            "Tier4_Precision": round(t4_prec, 4),
            "Tier1_Precision": round(t1_prec, 4),
            "N_Tier4": int(t4_mask.sum()),
            "N_Tier1": int(t1_mask.sum()),
        },
        "feature_importance": {name: int(imp) for name, imp in importances},
        "best_iteration": best_iter,
    }

    val_path = VALIDATION_DIR / "lightgbm_challenger_results.json"
    with open(val_path, "w") as f:
        json.dump(val_results, f, indent=2)
    print(f"  Saved results: {val_path}")

    # HEAD2HEAD comparison with v1071 and V2
    print("\n" + "=" * 60)
    print("  LightGBM vs ODIN v1071 vs V2.0 (Walk-Forward)")
    print("=" * 60)

    # Load v1071 baseline
    baseline_path = VALIDATION_DIR / "v1071_baseline.json"
    if baseline_path.exists():
        with open(baseline_path) as f:
            baseline = json.load(f)

        v1071_m = baseline["v1071"]
        v2_m = baseline["V2.0"]
        wf_base = baseline.get("walkforward", {})

        print(f"\n  {'Metric':<20} {'v1071':>10} {'V2.0':>10} {'LightGBM':>10}")
        print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10}")
        print(f"  {'AUC (full)':<20} {v1071_m['AUC']:>10.4f} {v2_m['AUC']:>10.4f} {auc_cal:>10.4f}")
        print(f"  {'Brier (full)':<20} {v1071_m['Brier']:>10.4f} {v2_m['Brier']:>10.4f} {brier_cal:>10.4f}")
        print(f"  {'Tier4 Prec':<20} {v1071_m['Tier4_Precision']:>10.1%} {v2_m['Tier4_Precision']:>10.1%} {t4_prec:>10.1%}")
        print(f"  {'Tier1 Prec':<20} {v1071_m['Tier1_Precision']:>10.1%} {v2_m['Tier1_Precision']:>10.1%} {t1_prec:>10.1%}")
        print(f"  {'Avg WF AUC':<20} {'':>10} {'':>10} {avg_wf_auc:>10.4f}")

        print(f"\n  Walk-Forward Year-by-Year:")
        print(f"  {'Year':<6} {'v1071':>10} {'V2.0':>10} {'LightGBM':>10}")
        print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10}")
        for yr_str, wf in sorted(wf_results.items()):
            v1071_yr = wf_base.get(str(yr_str), {}).get("v1071_AUC", 0)
            v2_yr = wf_base.get(str(yr_str), {}).get("v2_AUC", 0)
            print(f"  {yr_str:<6} {v1071_yr:>10.4f} {v2_yr:>10.4f} {wf['AUC']:>10.4f}")

    print("=" * 60)
    return val_results


if __name__ == "__main__":
    main()
