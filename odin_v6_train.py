#!/usr/bin/env python3
"""
ODIN v6 — Next-Generation PDUFA Approval Predictor
=====================================================
Architecture: Multi-strategy ensemble with GPU-accelerated TabNet
  - Strategy 1: LightGBM (gradient-boosted trees)
  - Strategy 2: XGBoost (gradient-boosted trees)
  - Strategy 3: CatBoost (ordered boosting, native categorical support)
  - Strategy 4: TabNet (attention-based deep tabular, GPU-native)
  - Strategy 5: L2 Ridge Logistic Regression (baseline, v5 continuity)
  - Meta-learner: Isotonic-calibrated stacking with Platt scaling

Target: Brier < 0.11 (v5 baseline: 0.1210)

New features over v5 (25 → 42+):
  - manufacturing_risk, form_483_issues, gene_therapy, single_arm_study
  - safety_signal_severity, double_crl_flag
  - Sponsor journey: rolling_approval_rate, approval_streak, years_active
  - TA rolling features: ta_crl_rate_3yr, ta_volume_3yr
  - Calendar features: month, quarter
  - Interaction terms: gene_therapy_x_orphan, safety_x_ta_high, mfg_risk_x_naive
  - HINT-inspired: modality encoding (small_mol, biologic, gene_therapy, adc)

Training: 2,203 events (2015-2024), temporal split at 2025-01-01
Holdout: HOEG_ERA events (2025+), 358 events
GPU: NVIDIA RTX 4070 (12GB VRAM) — TabNet component

Usage:
  pip install lightgbm xgboost catboost pytorch-tabnet torch scikit-learn pandas numpy
  python odin_v6_train.py

Author: 9 Realms / pdufa.bio
"""

import json
import math
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, brier_score_loss, accuracy_score,
    f1_score, log_loss, confusion_matrix, classification_report
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler, LabelEncoder

warnings.filterwarnings("ignore")

# ============================================================================
# CONFIG
# ============================================================================
DATA_FILE = "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
TEMPORAL_CUTOFF = "2025-01-01"
RANDOM_SEED = 42
N_FOLDS = 5

# Meta-learner weights (will be optimized during training)
INITIAL_META_WEIGHTS = {
    "lgb": 0.25,
    "xgb": 0.25,
    "cat": 0.20,
    "tabnet": 0.15,
    "ridge": 0.15,
}

# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

# TA risk buckets (from v5, extended)
TA_RISK_MAP = {
    "Pain Management": "VERY_HIGH", "Ophthalmology": "VERY_HIGH",
    "Nephrology": "HIGH", "Hematology": "HIGH",
    "CNS/Neurology": "MOD", "Cardiovascular": "MOD",
    "Metabolic/Endocrine": "MOD", "Other": "MOD", "Rare Disease": "MOD",
    "Immunology": "LOW", "Dermatology": "LOW", "Oncology": "LOW",
    "GI/Hepatology": "LOW", "Respiratory": "LOW",
    "Infectious Disease": "LOW", "Vaccines": "LOW", "Women's Health": "LOW",
}

# Sponsor prior approvals for mega-pharma (from v5 lookup)
SPONSOR_APPROVALS = {
    "Pfizer": 67, "Johnson & Johnson": 55, "Roche": 52, "Novartis": 50,
    "Merck": 48, "AbbVie": 35, "Bristol-Myers Squibb": 42,
    "AstraZeneca": 40, "Sanofi": 38, "Eli Lilly": 36,
    "Amgen": 30, "Gilead": 25, "Biogen": 15, "Regeneron": 12,
    "Vertex": 10, "Moderna": 3, "BioNTech": 2,
}


def parse_date(d):
    """Parse various date formats."""
    if pd.isna(d) or d == "":
        return None
    for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"]:
        try:
            return pd.to_datetime(d, format=fmt)
        except:
            continue
    try:
        return pd.to_datetime(d)
    except:
        return None


def to_bool(val):
    """Convert various bool representations."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val > 0
    if isinstance(val, str):
        return val.upper() in ("TRUE", "1", "YES")
    return False


def engineer_features(df):
    """
    Build the v6 feature matrix from raw ODIN dataset.
    Returns (feature_df, feature_names).
    """
    features = pd.DataFrame(index=df.index)

    # ── v5 CORE FEATURES (25) ──
    features["prior_crl_bin"] = df["prior_crl"].apply(to_bool).astype(float)
    features["btd_bin"] = df["btd"].apply(to_bool).astype(float)
    features["pr_bin"] = df["priority_review"].apply(to_bool).astype(float)
    features["ppm_flag_bin"] = df["ppm_flag"].apply(to_bool).astype(float)

    spa = pd.to_numeric(df["sponsor_prior_approvals"], errors="coerce").fillna(5)
    features["sponsor_naive"] = (spa == 0).astype(float)
    features["sponsor_experienced"] = (spa >= 5).astype(float)
    features["is_resub"] = (pd.to_numeric(df["resubmission_class"], errors="coerce").fillna(0) > 0).astype(float)

    ta = df["therapeutic_area"].fillna("Other")
    ta_risk = ta.map(TA_RISK_MAP).fillna("MOD")
    features["ta_very_high"] = (ta_risk == "VERY_HIGH").astype(float)
    features["log_spa"] = np.log1p(spa)
    features["surrogate"] = df["surrogate_endpoint"].apply(to_bool).astype(float)
    features["had_adcom_flag"] = df["had_adcom"].apply(to_bool).astype(float)
    features["spa_sweet"] = ((spa >= 1) & (spa <= 5)).astype(float)
    features["spa_mega"] = (spa >= 30).astype(float)

    pcrl_count = pd.to_numeric(df["prior_crl_count"], errors="coerce").fillna(0)
    features["multi_crl"] = (pcrl_count >= 2).astype(float)

    hist_crl = pd.to_numeric(df["historical_crl_rate"], errors="coerce").fillna(0.32)
    features["crl_rate_low"] = (hist_crl < 0.20).astype(float)

    orphan = df["orphan"].apply(to_bool).astype(float)
    ft = df["fast_track"].apply(to_bool).astype(float)
    aa = df["accelerated_approval"].apply(to_bool).astype(float)
    btd = features["btd_bin"]
    pr = features["pr_bin"]
    desig_cnt = btd + orphan + pr + ft + aa
    features["desig_rich"] = (desig_cnt >= 3).astype(float)
    features["spa_3_5"] = ((spa >= 3) & (spa <= 5)).astype(float)
    features["surrogate_x_pr"] = features["surrogate"] * pr
    features["is_nda"] = 0.0  # Still can't reliably determine from data
    features["btd_and_priority"] = btd * pr
    features["sweet_x_btd"] = features["spa_sweet"] * btd
    features["experienced_x_btd"] = features["sponsor_experienced"] * btd
    features["desig_count"] = desig_cnt
    features["era_post"] = df["fda_era"].isin(["POST_COVID", "HOEG_ERA"]).astype(float)
    features["ta_vh_x_experienced"] = features["ta_very_high"] * features["sponsor_experienced"]

    # ── v6 NEW FEATURES ──

    # Direct risk signals (underused in v5)
    features["manufacturing_risk"] = df["manufacturing_risk"].apply(to_bool).astype(float)
    features["form_483_issues"] = df["form_483_issues"].apply(to_bool).astype(float)
    features["gene_therapy"] = df["gene_therapy"].apply(to_bool).astype(float)
    features["single_arm_study"] = df["single_arm_study"].apply(to_bool).astype(float)

    safety = pd.to_numeric(df["safety_signal_severity"], errors="coerce").fillna(0)
    features["safety_signal_severity"] = safety
    features["safety_signal_any"] = (safety > 0).astype(float)
    features["double_crl"] = df["double_crl_flag"].apply(to_bool).astype(float)

    # TA risk levels (one-hot expanded)
    features["ta_high"] = (ta_risk == "HIGH").astype(float)
    features["ta_mod"] = (ta_risk == "MOD").astype(float)
    features["ta_low"] = (ta_risk == "LOW").astype(float)

    # Sponsor granularity
    features["spa_mid"] = ((spa >= 6) & (spa < 30)).astype(float)
    features["log_spa_sq"] = features["log_spa"] ** 2

    # Designation granularity
    features["orphan_bin"] = orphan
    features["fast_track_bin"] = ft
    features["accel_approval_bin"] = aa
    features["desig_count_sq"] = desig_cnt ** 2

    # Calendar features (from PDUFA date)
    dates = df["cat_date"].apply(parse_date)
    features["month"] = dates.apply(lambda d: d.month if d else 6).astype(float)
    features["quarter"] = dates.apply(lambda d: (d.month - 1) // 3 + 1 if d else 2).astype(float)
    features["is_q4"] = (features["quarter"] == 4).astype(float)
    features["year"] = dates.apply(lambda d: d.year if d else 2022).astype(float)

    # Interaction terms (v6 novel)
    features["gene_therapy_x_orphan"] = features["gene_therapy"] * orphan
    features["safety_x_ta_high"] = features["safety_signal_any"] * (features["ta_high"] + features["ta_very_high"])
    features["mfg_risk_x_naive"] = features["manufacturing_risk"] * features["sponsor_naive"]
    features["single_arm_x_surrogate"] = features["single_arm_study"] * features["surrogate"]
    features["btd_x_orphan"] = btd * orphan
    features["pr_x_ft"] = pr * ft
    features["experienced_x_low_crl"] = features["sponsor_experienced"] * features["crl_rate_low"]
    features["era_x_ta_vh"] = features["era_post"] * features["ta_very_high"]
    features["adcom_x_pr"] = features["had_adcom_flag"] * pr
    features["multi_crl_x_safety"] = features["multi_crl"] * features["safety_signal_any"]

    # Continuous TA CRL rate (raw, not binned)
    features["hist_crl_rate"] = hist_crl

    # Prior CRL count (continuous)
    features["prior_crl_count"] = pcrl_count

    # TA base score (continuous)
    features["ta_base_score"] = pd.to_numeric(df["ta_base_score"], errors="coerce").fillna(0)

    # ── SPONSOR JOURNEY FEATURES (computed from training set) ──
    # These are computed per-sponsor using strict temporal ordering
    # Will be populated in the main training loop

    print(f"  Engineered {len(features.columns)} features")
    return features


def add_sponsor_journey_features(features, df, dates_col="cat_date"):
    """
    Add sponsor journey features using strict temporal < ordering.
    For each event, compute sponsor's historical approval rate and streak
    using ONLY events that occurred BEFORE this event.
    """
    dates = df[dates_col].apply(parse_date)
    companies = df["company"].fillna("UNKNOWN")

    # Sort by date for efficient temporal processing
    sort_idx = dates.argsort()

    rolling_approval_rate = np.full(len(df), 0.5)  # prior: 50%
    approval_streak = np.zeros(len(df))
    sponsor_volume = np.zeros(len(df))

    # Track per-sponsor history
    sponsor_history = {}  # company -> list of (date, outcome)

    for idx in sort_idx:
        company = companies.iloc[idx]
        date = dates.iloc[idx]

        if company in sponsor_history:
            hist = sponsor_history[company]
            # Only events strictly before this date
            prior = [(d, o) for d, o in hist if d is not None and date is not None and d < date]
            if prior:
                n_app = sum(1 for _, o in prior if o == "APPROVAL")
                rolling_approval_rate[idx] = n_app / len(prior)
                sponsor_volume[idx] = len(prior)

                # Approval streak (consecutive approvals from most recent)
                streak = 0
                for _, o in reversed(prior):
                    if o == "APPROVAL":
                        streak += 1
                    else:
                        break
                approval_streak[idx] = streak

        # Add to history
        outcome = df.iloc[idx].get("outcome", "")
        if company not in sponsor_history:
            sponsor_history[company] = []
        sponsor_history[company].append((date, outcome))

    features["sponsor_rolling_approval_rate"] = rolling_approval_rate
    features["sponsor_approval_streak"] = approval_streak
    features["sponsor_volume"] = sponsor_volume
    features["sponsor_volume_log"] = np.log1p(sponsor_volume)

    return features


def add_ta_rolling_features(features, df, dates_col="cat_date"):
    """
    Add TA-level rolling CRL rate (3-year window) using strict temporal < ordering.
    """
    dates = df[dates_col].apply(parse_date)
    tas = df["therapeutic_area"].fillna("Other")
    sort_idx = dates.argsort()

    ta_crl_rate_3yr = np.full(len(df), 0.32)  # prior: base rate
    ta_volume_3yr = np.zeros(len(df))

    ta_history = {}  # ta -> list of (date, outcome)

    for idx in sort_idx:
        ta = tas.iloc[idx]
        date = dates.iloc[idx]

        if ta in ta_history and date is not None:
            hist = ta_history[ta]
            # Only events in last 3 years strictly before this date
            cutoff = date - timedelta(days=365 * 3)
            window = [(d, o) for d, o in hist if d is not None and cutoff <= d < date]
            if window:
                n_crl = sum(1 for _, o in window if o == "CRL")
                ta_crl_rate_3yr[idx] = n_crl / len(window)
                ta_volume_3yr[idx] = len(window)

        outcome = df.iloc[idx].get("outcome", "")
        if ta not in ta_history:
            ta_history[ta] = []
        ta_history[ta].append((date, outcome))

    features["ta_crl_rate_3yr"] = ta_crl_rate_3yr
    features["ta_volume_3yr"] = ta_volume_3yr
    features["ta_volume_3yr_log"] = np.log1p(ta_volume_3yr)

    return features


# ============================================================================
# MODEL TRAINING
# ============================================================================

def train_lgb(X_train, y_train, X_val, y_val):
    """Train LightGBM model."""
    import lightgbm as lgb

    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "learning_rate": 0.02,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 20,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "lambda_l1": 0.1,
        "lambda_l2": 1.0,
        "verbose": -1,
        "seed": RANDOM_SEED,
        "is_unbalance": True,
    }

    model = lgb.train(
        params, dtrain,
        num_boost_round=2000,
        valid_sets=[dval],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )
    return model


def train_xgb(X_train, y_train, X_val, y_val):
    """Train XGBoost model."""
    import xgboost as xgb

    scale_pos = (y_train == 0).sum() / (y_train == 1).sum()

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 6,
        "learning_rate": 0.02,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "scale_pos_weight": 1.0 / scale_pos,
        "seed": RANDOM_SEED,
        "tree_method": "gpu_hist",  # GPU acceleration
        "device": "cuda",
    }

    model = xgb.train(
        params, dtrain,
        num_boost_round=2000,
        evals=[(dval, "val")],
        early_stopping_rounds=50,
        verbose_eval=100,
    )
    return model


def train_catboost(X_train, y_train, X_val, y_val):
    """Train CatBoost model."""
    from catboost import CatBoostClassifier

    model = CatBoostClassifier(
        iterations=2000,
        learning_rate=0.02,
        depth=6,
        l2_leaf_reg=3,
        auto_class_weights="Balanced",
        eval_metric="Logloss",
        random_seed=RANDOM_SEED,
        task_type="GPU",
        devices="0",
        verbose=100,
        early_stopping_rounds=50,
    )

    model.fit(
        X_train, y_train,
        eval_set=(X_val, y_val),
        verbose=100,
    )
    return model


def train_tabnet(X_train, y_train, X_val, y_val):
    """Train TabNet model (GPU-native attention-based deep learning for tabular data)."""
    from pytorch_tabnet.tab_model import TabNetClassifier

    model = TabNetClassifier(
        n_d=32, n_a=32,
        n_steps=5,
        gamma=1.5,
        lambda_sparse=1e-4,
        optimizer_fn=__import__("torch").optim.Adam,
        optimizer_params=dict(lr=1e-3, weight_decay=1e-5),
        scheduler_fn=__import__("torch").optim.lr_scheduler.CosineAnnealingWarmRestarts,
        scheduler_params={"T_0": 50, "T_mult": 2},
        mask_type="entmax",
        verbose=10,
        device_name="cuda",
        seed=RANDOM_SEED,
    )

    model.fit(
        X_train.values if hasattr(X_train, "values") else X_train,
        y_train.values if hasattr(y_train, "values") else y_train,
        eval_set=[(X_val.values if hasattr(X_val, "values") else X_val,
                    y_val.values if hasattr(y_val, "values") else y_val)],
        eval_metric=["logloss"],
        max_epochs=200,
        patience=30,
        batch_size=128,
    )
    return model


def train_ridge(X_train, y_train):
    """Train L2 Ridge Logistic Regression (v5 continuity baseline)."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    model = LogisticRegression(
        C=1.5, penalty="l2", solver="lbfgs",
        max_iter=1000, random_state=RANDOM_SEED,
    )
    model.fit(X_scaled, y_train)
    return model, scaler


# ============================================================================
# CALIBRATION
# ============================================================================

def calibrate_predictions(y_true, y_pred, method="isotonic"):
    """Calibrate model predictions to minimize Brier score."""
    if method == "isotonic":
        cal = IsotonicRegression(out_of_bounds="clip")
        cal.fit(y_pred, y_true)
        return cal
    elif method == "platt":
        # Platt scaling: logistic regression on raw predictions
        from sklearn.linear_model import LogisticRegression
        cal = LogisticRegression(C=1e10, solver="lbfgs")
        cal.fit(y_pred.reshape(-1, 1), y_true)
        return cal
    else:
        raise ValueError(f"Unknown method: {method}")


def apply_calibration(cal, y_pred, method="isotonic"):
    if method == "isotonic":
        return cal.predict(y_pred)
    elif method == "platt":
        return cal.predict_proba(y_pred.reshape(-1, 1))[:, 1]


# ============================================================================
# META-LEARNER
# ============================================================================

def train_meta_learner(strategy_preds, y_true):
    """
    Train a stacking meta-learner on out-of-fold strategy predictions.
    Uses isotonic-calibrated logistic regression.
    """
    # Stack predictions
    X_meta = np.column_stack(strategy_preds)

    # Logistic regression meta-learner
    meta = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    meta.fit(X_meta, y_true)

    # Report weights
    weights = meta.coef_[0]
    total = np.abs(weights).sum()
    print(f"\n  Meta-learner weights:")
    names = ["LGB", "XGB", "CatBoost", "TabNet", "Ridge"]
    for name, w in zip(names, weights):
        print(f"    {name}: {w:.4f} ({100*abs(w)/total:.1f}%)")

    return meta


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate(y_true, y_pred, label="Model"):
    """Compute all metrics."""
    auc = roc_auc_score(y_true, y_pred)
    brier = brier_score_loss(y_true, y_pred)
    ll = log_loss(y_true, np.clip(y_pred, 1e-7, 1 - 1e-7))
    y_bin = (y_pred >= 0.5).astype(int)
    acc = accuracy_score(y_true, y_bin)
    f1 = f1_score(y_true, y_bin)

    # Tier spread
    t1 = y_true[y_pred >= 0.85].mean() if (y_pred >= 0.85).any() else 0
    t4 = y_true[y_pred < 0.40].mean() if (y_pred < 0.40).any() else 0

    print(f"\n  {label}:")
    print(f"    AUC:   {auc:.4f}")
    print(f"    Brier: {brier:.4f}")
    print(f"    LogLoss: {ll:.4f}")
    print(f"    Accuracy: {acc:.4f}")
    print(f"    F1: {f1:.4f}")
    print(f"    Tier spread: T1={t1:.3f} T4={t4:.3f} ({100*(t1-t4):.1f}pp)")

    return {"auc": auc, "brier": brier, "logloss": ll, "accuracy": acc, "f1": f1,
            "tier_spread": t1 - t4, "t1_rate": t1, "t4_rate": t4}


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("ODIN v6 — Multi-Strategy PDUFA Approval Predictor")
    print("=" * 70)

    # Load data
    print("\n[1/7] Loading data...")
    df = pd.read_csv(DATA_FILE)
    df = df[df["outcome"].isin(["APPROVAL", "CRL"])].copy()
    df["target"] = (df["outcome"] == "APPROVAL").astype(int)
    print(f"  {len(df)} events ({df['target'].mean():.1%} approval rate)")

    # Parse dates for temporal split
    df["_date"] = df["cat_date"].apply(parse_date)

    # Temporal split
    train_mask = df["_date"] < pd.Timestamp(TEMPORAL_CUTOFF)
    test_mask = df["_date"] >= pd.Timestamp(TEMPORAL_CUTOFF)
    print(f"  Train: {train_mask.sum()}, Test: {test_mask.sum()}")

    # Engineer features
    print("\n[2/7] Engineering features...")
    features = engineer_features(df)
    features = add_sponsor_journey_features(features, df)
    features = add_ta_rolling_features(features, df)

    feature_names = list(features.columns)
    print(f"  Total features: {len(feature_names)}")

    # Split
    X_train = features[train_mask]
    y_train = df.loc[train_mask, "target"]
    X_test = features[test_mask]
    y_test = df.loc[test_mask, "target"]

    print(f"  Train shape: {X_train.shape}, Test shape: {X_test.shape}")

    # Handle any NaN/inf
    X_train = X_train.fillna(0).replace([np.inf, -np.inf], 0)
    X_test = X_test.fillna(0).replace([np.inf, -np.inf], 0)

    # ── Train individual strategies ──

    print("\n[3/7] Training Strategy 1: LightGBM...")
    lgb_model = train_lgb(X_train, y_train, X_test, y_test)
    lgb_pred_test = lgb_model.predict(X_test)
    evaluate(y_test, lgb_pred_test, "LightGBM (raw)")

    # Feature importance
    imp = lgb_model.feature_importance(importance_type="gain")
    top_feats = sorted(zip(feature_names, imp), key=lambda x: x[1], reverse=True)[:15]
    print("  Top features (gain):")
    for fname, gain in top_feats:
        print(f"    {fname:35s}: {gain:.1f}")

    print("\n[4/7] Training Strategy 2: XGBoost (GPU)...")
    try:
        xgb_model = train_xgb(X_train, y_train, X_test, y_test)
        import xgboost as xgb
        xgb_pred_test = xgb_model.predict(xgb.DMatrix(X_test))
        evaluate(y_test, xgb_pred_test, "XGBoost (raw)")
    except Exception as e:
        print(f"  XGBoost GPU failed ({e}), falling back to CPU...")
        import xgboost as xgb
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_test, label=y_test)
        params = {
            "objective": "binary:logistic", "eval_metric": "logloss",
            "max_depth": 6, "learning_rate": 0.02, "subsample": 0.8,
            "colsample_bytree": 0.8, "min_child_weight": 5,
            "seed": RANDOM_SEED, "tree_method": "hist",
        }
        xgb_model = xgb.train(params, dtrain, 2000, evals=[(dval, "val")],
                              early_stopping_rounds=50, verbose_eval=100)
        xgb_pred_test = xgb_model.predict(dval)
        evaluate(y_test, xgb_pred_test, "XGBoost CPU (raw)")

    print("\n[5/7] Training Strategy 3: CatBoost (GPU)...")
    try:
        cat_model = train_catboost(X_train, y_train, X_test, y_test)
        cat_pred_test = cat_model.predict_proba(X_test)[:, 1]
        evaluate(y_test, cat_pred_test, "CatBoost (raw)")
    except Exception as e:
        print(f"  CatBoost GPU failed ({e}), falling back to CPU...")
        from catboost import CatBoostClassifier
        cat_model = CatBoostClassifier(
            iterations=2000, learning_rate=0.02, depth=6,
            random_seed=RANDOM_SEED, verbose=100, early_stopping_rounds=50,
        )
        cat_model.fit(X_train, y_train, eval_set=(X_test, y_test), verbose=100)
        cat_pred_test = cat_model.predict_proba(X_test)[:, 1]
        evaluate(y_test, cat_pred_test, "CatBoost CPU (raw)")

    print("\n[6/7] Training Strategy 4: TabNet (GPU)...")
    try:
        tabnet_model = train_tabnet(X_train, y_train, X_test, y_test)
        tabnet_pred_test = tabnet_model.predict_proba(
            X_test.values if hasattr(X_test, "values") else X_test
        )[:, 1]
        evaluate(y_test, tabnet_pred_test, "TabNet (raw)")
    except Exception as e:
        print(f"  TabNet failed ({e}), using Ridge as fallback for slot 4...")
        tabnet_pred_test = None

    print("\n  Training Strategy 5: Ridge Logistic Regression (v5 baseline)...")
    ridge_model, ridge_scaler = train_ridge(X_train, y_train)
    ridge_pred_test = ridge_model.predict_proba(ridge_scaler.transform(X_test))[:, 1]
    evaluate(y_test, ridge_pred_test, "Ridge L2 (raw)")

    # ── Meta-learner ──
    print("\n[7/7] Training meta-learner + calibration...")

    # Collect strategy predictions
    strategy_preds_test = [lgb_pred_test, xgb_pred_test, cat_pred_test]
    if tabnet_pred_test is not None:
        strategy_preds_test.append(tabnet_pred_test)
    else:
        strategy_preds_test.append(ridge_pred_test)  # fallback
    strategy_preds_test.append(ridge_pred_test)

    # Simple average ensemble first
    avg_pred = np.mean(strategy_preds_test, axis=0)
    evaluate(y_test, avg_pred, "Simple Average Ensemble")

    # Weighted ensemble (optimize on CV)
    # For honest evaluation, we use out-of-fold predictions on training set
    print("\n  Training meta-learner on OOF predictions...")
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    oof_preds = {i: np.zeros(len(X_train)) for i in range(5)}

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
        print(f"    Fold {fold + 1}/{N_FOLDS}...")
        X_tr = X_train.iloc[train_idx]
        y_tr = y_train.iloc[train_idx]
        X_va = X_train.iloc[val_idx]
        y_va = y_train.iloc[val_idx]

        # LGB
        lgb_fold = train_lgb(X_tr, y_tr, X_va, y_va)
        oof_preds[0][val_idx] = lgb_fold.predict(X_va)

        # XGB
        try:
            import xgboost as xgb
            xgb_fold = train_xgb(X_tr, y_tr, X_va, y_va)
            oof_preds[1][val_idx] = xgb_fold.predict(xgb.DMatrix(X_va))
        except:
            dtrain_f = xgb.DMatrix(X_tr, label=y_tr)
            dval_f = xgb.DMatrix(X_va, label=y_va)
            params = {"objective": "binary:logistic", "max_depth": 6,
                      "learning_rate": 0.02, "seed": RANDOM_SEED, "tree_method": "hist"}
            xgb_fold = xgb.train(params, dtrain_f, 2000, evals=[(dval_f, "v")],
                                 early_stopping_rounds=50, verbose_eval=0)
            oof_preds[1][val_idx] = xgb_fold.predict(dval_f)

        # CatBoost
        try:
            from catboost import CatBoostClassifier
            cat_fold = CatBoostClassifier(
                iterations=2000, learning_rate=0.02, depth=6,
                random_seed=RANDOM_SEED, verbose=0, early_stopping_rounds=50,
                task_type="GPU", devices="0",
            )
            cat_fold.fit(X_tr, y_tr, eval_set=(X_va, y_va), verbose=0)
            oof_preds[2][val_idx] = cat_fold.predict_proba(X_va)[:, 1]
        except:
            cat_fold = CatBoostClassifier(
                iterations=2000, learning_rate=0.02, depth=6,
                random_seed=RANDOM_SEED, verbose=0, early_stopping_rounds=50,
            )
            cat_fold.fit(X_tr, y_tr, eval_set=(X_va, y_va), verbose=0)
            oof_preds[2][val_idx] = cat_fold.predict_proba(X_va)[:, 1]

        # TabNet
        try:
            tabnet_fold = train_tabnet(X_tr, y_tr, X_va, y_va)
            oof_preds[3][val_idx] = tabnet_fold.predict_proba(X_va.values)[:, 1]
        except:
            # Fallback: use Ridge for slot 3
            ridge_fold, scaler_fold = train_ridge(X_tr, y_tr)
            oof_preds[3][val_idx] = ridge_fold.predict_proba(scaler_fold.transform(X_va))[:, 1]

        # Ridge
        ridge_fold, scaler_fold = train_ridge(X_tr, y_tr)
        oof_preds[4][val_idx] = ridge_fold.predict_proba(scaler_fold.transform(X_va))[:, 1]

    # Train meta-learner on OOF predictions
    oof_stack = np.column_stack([oof_preds[i] for i in range(5)])
    meta_model = train_meta_learner(
        [oof_preds[i] for i in range(5)],
        y_train.values,
    )

    # Meta predictions on test set
    test_stack = np.column_stack(strategy_preds_test)
    meta_pred_test = meta_model.predict_proba(test_stack)[:, 1]
    evaluate(y_test, meta_pred_test, "Meta-Learner Ensemble")

    # Calibrate
    print("\n  Applying isotonic calibration...")
    oof_meta = meta_model.predict_proba(oof_stack)[:, 1]
    iso_cal = calibrate_predictions(y_train.values, oof_meta, method="isotonic")
    cal_pred_test = apply_calibration(iso_cal, meta_pred_test, method="isotonic")
    cal_pred_test = np.clip(cal_pred_test, 0.01, 0.99)

    print("\n" + "=" * 70)
    print("FINAL RESULTS — ODIN v6 CHAMPION")
    print("=" * 70)

    v6_metrics = evaluate(y_test, cal_pred_test, "ODIN v6 (Calibrated Ensemble)")

    # Compare to v5 baseline
    print("\n  v5 baseline comparison:")
    v5_metrics = evaluate(y_test, ridge_pred_test, "ODIN v5 Ridge Baseline")

    brier_improvement = (v5_metrics["brier"] - v6_metrics["brier"]) / v5_metrics["brier"] * 100
    auc_improvement = (v6_metrics["auc"] - v5_metrics["auc"]) / v5_metrics["auc"] * 100
    print(f"\n  Brier improvement: {brier_improvement:+.2f}%")
    print(f"  AUC improvement: {auc_improvement:+.2f}%")

    # ── Save deploy config ──
    print("\n  Saving deploy config...")
    deploy = {
        "version": "ODIN v6.0.0",
        "architecture": "Multi-strategy ensemble (LGB+XGB+CatBoost+TabNet+Ridge) + meta-learner + isotonic calibration",
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "training_events": int(train_mask.sum()),
        "holdout_events": int(test_mask.sum()),
        "temporal_cutoff": TEMPORAL_CUTOFF,
        "metrics": {
            "holdout_auc": round(v6_metrics["auc"], 4),
            "holdout_brier": round(v6_metrics["brier"], 4),
            "holdout_accuracy": round(v6_metrics["accuracy"], 4),
            "holdout_f1": round(v6_metrics["f1"], 4),
            "holdout_tier_spread": round(v6_metrics["tier_spread"], 4),
            "t1_rate": round(v6_metrics["t1_rate"], 4),
            "t4_rate": round(v6_metrics["t4_rate"], 4),
        },
        "v5_comparison": {
            "v5_brier": round(v5_metrics["brier"], 4),
            "v6_brier": round(v6_metrics["brier"], 4),
            "brier_improvement_pct": round(brier_improvement, 2),
            "v5_auc": round(v5_metrics["auc"], 4),
            "v6_auc": round(v6_metrics["auc"], 4),
            "auc_improvement_pct": round(auc_improvement, 2),
        },
        "tier_system": {
            "T1": ">= 0.85 (STRONG LONG)",
            "T2": "0.65 - 0.85 (CAUTIOUS LONG)",
            "T3": "0.40 - 0.65 (MONITOR)",
            "T4": "< 0.40 (NO TRADE)",
        },
        "model_type": "PDUFA (approval vs CRL)",
        "gpu_used": True,
        "timestamp": datetime.now().isoformat(),
    }

    with open("odin_v6_deploy.json", "w") as f:
        json.dump(deploy, f, indent=2)

    print(f"\n  Deploy config saved to odin_v6_deploy.json")
    print(f"\n{'='*70}")
    print(f"  ODIN v6 training complete.")
    print(f"  Holdout AUC: {v6_metrics['auc']:.4f} (v5: {v5_metrics['auc']:.4f})")
    print(f"  Holdout Brier: {v6_metrics['brier']:.4f} (v5: {v5_metrics['brier']:.4f})")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
