#!/usr/bin/env python3
"""
================================================================================
ALLFATHER ODIN V2 — ODIN Improvement Iteration
================================================================================

Loads the ODIN v1071 T1 2015+ ENRICHED dataset, runs systematic model
improvement experiments:

1. Baseline: v5 specification (25 features, L2 Ridge C=1.5)
2. Extended feature set: add financial + NLP features from enriched columns
3. Hyperparameter sweep (C, solver, class_weight)
4. Walk-forward expanding window validation (2020-2025)
5. GradientBoosting comparison
6. Feature importance analysis

Temporal splits:
  Train: 2015-2022
  Val: 2023
  Test: 2024-2025
"""

import csv, math, re, os, json
import numpy as np
from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ODIN_CSV = os.path.join(DATA_DIR, "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "allfather_odin_v6_deploy.json")

# ============================================================================
# V5 FEATURES (baseline)
# ============================================================================
V5_FEATURES = [
    "prior_crl_bin", "btd_bin", "pr_bin", "ppm_flag_bin",
    "sponsor_naive", "sponsor_experienced", "is_resub",
    "ta_very_high", "log_spa", "surrogate",
    "had_adcom_flag", "spa_sweet", "spa_mega",
    "multi_crl", "crl_rate_low", "desig_rich",
    "spa_3_5", "surrogate_x_pr", "is_nda",
    "btd_and_priority", "sweet_x_btd", "experienced_x_btd",
    "desig_count", "era_post", "ta_vh_x_experienced",
]

# Extended features (candidates for v6)
EXTENDED_CANDIDATES = [
    # Continuous features (potentially more informative than binary)
    "sponsor_prior_approvals", "adcom_vote_pct", "ta_base_score",
    "historical_crl_rate",
    # Interaction/derived features
    "orphan_drug",  # orphan designation
    "fast_track",   # fast track designation
]

def safe_float(s, default=0.0):
    try: return float(str(s).strip())
    except: return default

def safe_bool(s):
    return str(s).strip().upper() in ("TRUE", "1", "YES", "1.0")


# ============================================================================
# DATA LOADING + ENCODING
# ============================================================================
def load_odin_data():
    print("\n[1/6] Loading ODIN dataset...")
    rows = []
    with open(ODIN_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    print(f"  Raw rows: {len(rows)}")
    print(f"  Columns: {list(rows[0].keys())[:20]}...")

    # Encode features
    encoded = []
    for row in rows:
        ev = {}

        # Target
        outcome = row.get("outcome", "").strip().upper()
        if outcome not in ("APPROVED", "CRL", "APPROVAL", "REJECTION"):
            continue
        ev["y"] = 1 if outcome in ("APPROVED", "APPROVAL") else 0

        # Date
        ev["date"] = row.get("catalyst_date", row.get("pdufa_date", "")).strip()
        if not ev["date"]: continue
        ev["ticker"] = row.get("ticker", "").upper()

        # V5 binary features
        ev["prior_crl_bin"] = 1.0 if safe_bool(row.get("prior_crl", "")) else 0.0
        ev["btd_bin"] = 1.0 if safe_bool(row.get("btd", "")) else 0.0
        ev["pr_bin"] = 1.0 if safe_bool(row.get("priority_review", "")) else 0.0
        ev["ppm_flag_bin"] = 1.0 if safe_bool(row.get("ppm_flag", "")) else 0.0

        spa = safe_float(row.get("sponsor_prior_approvals", 0))
        ev["sponsor_naive"] = 1.0 if spa < 5 else 0.0
        ev["sponsor_experienced"] = 1.0 if spa > 10 else 0.0
        ev["is_resub"] = 1.0 if safe_bool(row.get("is_resubmission", "")) or safe_bool(row.get("resubmission", "")) else 0.0

        # TA very high risk
        ta = row.get("ta_bucket_v2", row.get("therapeutic_area", "")).lower()
        ev["ta_very_high"] = 1.0 if any(k in ta for k in ["cns", "psychiatry", "neuro", "pain"]) else 0.0

        ev["log_spa"] = math.log1p(spa)
        ev["surrogate"] = 1.0 if safe_bool(row.get("surrogate_endpoint", "")) else 0.0
        ev["had_adcom_flag"] = 1.0 if safe_bool(row.get("had_adcom", row.get("adcom", ""))) else 0.0

        ev["spa_sweet"] = 1.0 if 5 <= spa <= 15 else 0.0
        ev["spa_mega"] = 1.0 if spa > 20 else 0.0
        ev["multi_crl"] = 1.0 if safe_float(row.get("prior_crl_count", 0)) > 1 else 0.0

        crl_rate = safe_float(row.get("historical_crl_rate", 0.2))
        ev["crl_rate_low"] = 1.0 if crl_rate < 0.20 else 0.0

        btd = safe_bool(row.get("btd", ""))
        pr = safe_bool(row.get("priority_review", ""))
        orphan = safe_bool(row.get("orphan", row.get("orphan_drug", "")))
        ft = safe_bool(row.get("fast_track", ""))
        aa = safe_bool(row.get("accelerated_approval", ""))
        desig_count = sum([btd, pr, orphan, ft, aa])
        ev["desig_rich"] = 1.0 if desig_count >= 2 else 0.0
        ev["desig_count"] = float(desig_count)

        ev["spa_3_5"] = 1.0 if 3 <= spa <= 5 else 0.0
        ev["surrogate_x_pr"] = ev["surrogate"] * ev["pr_bin"]

        app_type = row.get("application_type", "").upper()
        ev["is_nda"] = 1.0 if "NDA" in app_type else 0.0

        ev["btd_and_priority"] = ev["btd_bin"] * ev["pr_bin"]
        ev["sweet_x_btd"] = ev["spa_sweet"] * ev["btd_bin"]
        ev["experienced_x_btd"] = ev["sponsor_experienced"] * ev["btd_bin"]

        try: year = int(ev["date"][:4])
        except: year = 2020
        ev["era_post"] = 1.0 if year >= 2016 else 0.0

        ev["ta_vh_x_experienced"] = ev["ta_very_high"] * ev["sponsor_experienced"]

        # Extended features
        ev["sponsor_prior_approvals"] = spa
        ev["adcom_vote_pct"] = safe_float(row.get("adcom_vote_pct", -1))
        ev["ta_base_score"] = safe_float(row.get("ta_base_score", 0.5))
        ev["historical_crl_rate"] = crl_rate
        ev["orphan_drug"] = 1.0 if orphan else 0.0
        ev["fast_track"] = 1.0 if ft else 0.0

        # NEW v6 candidates
        ev["prior_crl_count"] = safe_float(row.get("prior_crl_count", 0))
        ev["desig_x_resub"] = ev["desig_rich"] * ev["is_resub"]
        ev["spa_x_surrogate"] = ev["log_spa"] * ev["surrogate"]
        ev["btd_x_rare"] = ev["btd_bin"] * (1.0 if orphan else 0.0)
        ev["naive_x_ta_vh"] = ev["sponsor_naive"] * ev["ta_very_high"]
        ev["mega_x_nda"] = ev["spa_mega"] * ev["is_nda"]
        ev["adcom_x_crl"] = (1.0 if ev["adcom_vote_pct"] > 0.5 else 0.0) * ev["prior_crl_bin"]
        ev["era_x_btd"] = ev["era_post"] * ev["btd_bin"]
        ev["pr_x_experienced"] = ev["pr_bin"] * ev["sponsor_experienced"]

        encoded.append(ev)

    print(f"  Encoded: {len(encoded)} events")
    print(f"  Approval rate: {sum(e['y'] for e in encoded)/len(encoded):.3f}")

    return encoded


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================
def run_experiment(encoded, feature_list, label, C=1.5, solver='lbfgs', class_weight=None):
    """Run a single LR experiment with given features and hyperparams."""
    # Sort by date
    encoded_sorted = sorted(encoded, key=lambda e: e["date"])

    n = len(encoded_sorted)
    X = np.zeros((n, len(feature_list)))
    y = np.zeros(n)
    dates = []

    for i, ev in enumerate(encoded_sorted):
        for j, f in enumerate(feature_list):
            X[i, j] = ev.get(f, 0.0)
        y[i] = ev["y"]
        dates.append(ev["date"])

    dates = np.array(dates)

    # Train/Val/Test split
    train_mask = dates < "2023-01-01"
    val_mask = (dates >= "2023-01-01") & (dates < "2024-01-01")
    test_mask = dates >= "2024-01-01"

    X_tr, y_tr = X[train_mask], y[train_mask]
    X_va, y_va = X[val_mask], y[val_mask]
    X_te, y_te = X[test_mask], y[test_mask]

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)
    X_te_s = scaler.transform(X_te)

    model = LogisticRegression(C=C, penalty='l2', solver=solver,
                               class_weight=class_weight, max_iter=2000)
    model.fit(X_tr_s, y_tr)

    val_pred = model.predict_proba(X_va_s)[:,1]
    test_pred = model.predict_proba(X_te_s)[:,1]

    val_auc = roc_auc_score(y_va, val_pred)
    val_brier = np.mean((val_pred - y_va)**2)
    test_auc = roc_auc_score(y_te, test_pred)
    test_brier = np.mean((test_pred - y_te)**2)

    return {
        "label": label,
        "n_features": len(feature_list),
        "C": C,
        "val_auc": val_auc, "val_brier": val_brier,
        "test_auc": test_auc, "test_brier": test_brier,
        "n_train": int(np.sum(train_mask)),
        "n_val": int(np.sum(val_mask)),
        "n_test": int(np.sum(test_mask)),
        "model": model, "scaler": scaler, "features": feature_list,
    }


def walk_forward_validation(encoded, feature_list, C=1.5):
    """Expanding window walk-forward validation 2020-2025."""
    encoded_sorted = sorted(encoded, key=lambda e: e["date"])
    n = len(encoded_sorted)
    X = np.zeros((n, len(feature_list)))
    y = np.zeros(n)
    dates = []
    for i, ev in enumerate(encoded_sorted):
        for j, f in enumerate(feature_list):
            X[i, j] = ev.get(f, 0.0)
        y[i] = ev["y"]
        dates.append(ev["date"])
    dates = np.array(dates)

    results = []
    for test_year in range(2020, 2026):
        train_mask = dates < f"{test_year}-01-01"
        test_mask = (dates >= f"{test_year}-01-01") & (dates < f"{test_year+1}-01-01")
        n_tr, n_te = int(np.sum(train_mask)), int(np.sum(test_mask))
        if n_te < 10: continue

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])

        model = LogisticRegression(C=C, penalty='l2', solver='lbfgs', max_iter=2000)
        model.fit(X_tr, y[train_mask])
        pred = model.predict_proba(X_te)[:,1]

        auc = roc_auc_score(y[test_mask], pred)
        brier = np.mean((pred - y[test_mask])**2)
        results.append({"year": test_year, "auc": auc, "brier": brier, "n": n_te})

    return results


def main():
    print("="*70)
    print("  ALLFATHER ODIN V2 — ODIN Improvement Iteration")
    print("="*70)

    encoded = load_odin_data()

    # ================================================================
    # EXPERIMENT 1: V5 Baseline (25 features, C=1.5)
    # ================================================================
    print(f"\n[2/6] Experiment 1: V5 Baseline (25 features, C=1.5)...")
    r1 = run_experiment(encoded, V5_FEATURES, "V5 Baseline", C=1.5)
    print(f"  Val:  AUC={r1['val_auc']:.4f}  Brier={r1['val_brier']:.4f}")
    print(f"  Test: AUC={r1['test_auc']:.4f}  Brier={r1['test_brier']:.4f}")

    # ================================================================
    # EXPERIMENT 2: V5 + Extended (31 features)
    # ================================================================
    print(f"\n[3/6] Experiment 2: V5 + Extended (31 features)...")
    V6_FEATURES = V5_FEATURES + [
        "sponsor_prior_approvals", "adcom_vote_pct", "ta_base_score",
        "historical_crl_rate", "orphan_drug", "fast_track",
    ]
    r2 = run_experiment(encoded, V6_FEATURES, "V6 Extended", C=1.5)
    print(f"  Val:  AUC={r2['val_auc']:.4f}  Brier={r2['val_brier']:.4f}")
    print(f"  Test: AUC={r2['test_auc']:.4f}  Brier={r2['test_brier']:.4f}")

    # ================================================================
    # EXPERIMENT 3: V6 + Novel interactions (40 features)
    # ================================================================
    print(f"\n[4/6] Experiment 3: V6 + Novel interactions (40 features)...")
    V6_PLUS = V6_FEATURES + [
        "prior_crl_count", "desig_x_resub", "spa_x_surrogate",
        "btd_x_rare", "naive_x_ta_vh", "mega_x_nda",
        "adcom_x_crl", "era_x_btd", "pr_x_experienced",
    ]
    r3 = run_experiment(encoded, V6_PLUS, "V6+ Interactions", C=1.5)
    print(f"  Val:  AUC={r3['val_auc']:.4f}  Brier={r3['val_brier']:.4f}")
    print(f"  Test: AUC={r3['test_auc']:.4f}  Brier={r3['test_brier']:.4f}")

    # ================================================================
    # EXPERIMENT 4: Hyperparameter sweep on best feature set
    # ================================================================
    print(f"\n[5/6] Experiment 4: Hyperparameter sweep...")
    best_exp = min([r1, r2, r3], key=lambda r: r["val_brier"])
    best_feats = best_exp["features"]
    print(f"  Best feature set: {best_exp['label']} ({len(best_feats)} features)")

    results = []
    for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0]:
        for cw in [None, 'balanced']:
            r = run_experiment(encoded, best_feats, f"C={C},cw={cw}", C=C, class_weight=cw)
            results.append(r)

    results.sort(key=lambda r: r["val_brier"])
    print(f"\n  Top 5 configs (by Val Brier):")
    for r in results[:5]:
        print(f"    {r['label']:25s}  Val AUC={r['val_auc']:.4f}  Val Brier={r['val_brier']:.4f}  "
              f"Test AUC={r['test_auc']:.4f}  Test Brier={r['test_brier']:.4f}")

    best = results[0]
    print(f"\n  Champion config: {best['label']}")

    # ================================================================
    # Walk-Forward Validation
    # ================================================================
    print(f"\n[6/6] Walk-forward validation (2020-2025)...")
    wf_v5 = walk_forward_validation(encoded, V5_FEATURES, C=1.5)
    wf_best = walk_forward_validation(encoded, best["features"], C=best["C"])

    print(f"\n  {'Year':>6s}  {'V5 AUC':>8s}  {'V5 Brier':>9s}  {'Best AUC':>9s}  {'Best Brier':>11s}  {'n':>4s}")
    print(f"  {'─'*55}")
    for v5, vb in zip(wf_v5, wf_best):
        y = v5["year"]
        print(f"  {y:6d}  {v5['auc']:8.4f}  {v5['brier']:9.4f}  {vb['auc']:9.4f}  {vb['brier']:11.4f}  {v5['n']:4d}")

    v5_aucs = [r["auc"] for r in wf_v5]
    best_aucs = [r["auc"] for r in wf_best]
    v5_briers = [r["brier"] for r in wf_v5]
    best_briers = [r["brier"] for r in wf_best]

    print(f"  {'─'*55}")
    print(f"  Mean:  {np.mean(v5_aucs):.4f}  {np.mean(v5_briers):.4f}  "
          f"{np.mean(best_aucs):.4f}  {np.mean(best_briers):.4f}")
    print(f"  Std:   {np.std(v5_aucs):.4f}  {np.std(v5_briers):.4f}  "
          f"{np.std(best_aucs):.4f}  {np.std(best_briers):.4f}")

    # Feature importance
    print(f"\n  FEATURE IMPORTANCE (top 15 by |coefficient|):")
    model = best["model"]
    feat_imp = sorted(zip(best["features"], model.coef_[0]), key=lambda x: abs(x[1]), reverse=True)
    for fname, coef in feat_imp[:15]:
        print(f"    {fname:30s}  coef={coef:+.4f}")

    # ================================================================
    # TIER ANALYSIS on test set
    # ================================================================
    print(f"\n  TIER ANALYSIS (test set):")
    encoded_sorted = sorted(encoded, key=lambda e: e["date"])
    n = len(encoded_sorted)
    X = np.zeros((n, len(best["features"])))
    y = np.zeros(n)
    dates = []
    for i, ev in enumerate(encoded_sorted):
        for j, f in enumerate(best["features"]):
            X[i, j] = ev.get(f, 0.0)
        y[i] = ev["y"]
        dates.append(ev["date"])
    dates = np.array(dates)
    test_mask = dates >= "2024-01-01"
    X_te = best["scaler"].transform(X[test_mask])
    y_te = y[test_mask]
    preds = best["model"].predict_proba(X_te)[:,1]

    tiers = {
        "T1 (≥0.85)": preds >= 0.85,
        "T2 (0.65-0.85)": (preds >= 0.65) & (preds < 0.85),
        "T3 (0.40-0.65)": (preds >= 0.40) & (preds < 0.65),
        "T4 (<0.40)": preds < 0.40,
    }
    for tier, mask in tiers.items():
        n_t = int(np.sum(mask))
        if n_t > 0:
            actual = np.mean(y_te[mask]) * 100
            pred = np.mean(preds[mask]) * 100
            print(f"    {tier:20s}  n={n_t:4d}  actual={actual:5.1f}%  pred={pred:5.1f}%")

    # ================================================================
    # SAVE DEPLOY CONFIG
    # ================================================================
    print(f"\n  Saving ODIN v6 deploy config...")
    deploy = {
        "model": "allfather_odin_v6",
        "version": "6.0.0",
        "date": "2026-03-26",
        "n_features": len(best["features"]),
        "feature_names": best["features"],
        "holdout_metrics": {
            "n_train": best["n_train"],
            "n_val": best["n_val"],
            "n_test": best["n_test"],
            "val_auc": float(best["val_auc"]),
            "val_brier": float(best["val_brier"]),
            "test_auc": float(best["test_auc"]),
            "test_brier": float(best["test_brier"]),
        },
        "hyperparams": {
            "C": float(best["C"]),
            "penalty": "l2",
            "solver": "lbfgs",
        },
        "walk_forward": {
            "mean_auc": float(np.mean(best_aucs)),
            "std_auc": float(np.std(best_aucs)),
            "mean_brier": float(np.mean(best_briers)),
        },
        "coefficients": dict(zip(best["features"], best["model"].coef_[0].tolist())),
        "intercept": float(best["model"].intercept_[0]),
        "scaler_means": dict(zip(best["features"], best["scaler"].mean_.tolist())),
        "scaler_scales": dict(zip(best["features"], best["scaler"].scale_.tolist())),
    }

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"  Saved: {OUTPUT_JSON}")

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print(f"\n  {'='*66}")
    print(f"  ALLFATHER ODIN V6 FINAL SUMMARY")
    print(f"  {'='*66}")
    print(f"  Features:      {len(best['features'])}")
    print(f"  Config:        {best['label']}")
    print(f"  Val AUC:       {best['val_auc']:.4f}")
    print(f"  Val Brier:     {best['val_brier']:.4f}")
    print(f"  Test AUC:      {best['test_auc']:.4f}")
    print(f"  Test Brier:    {best['test_brier']:.4f}")
    print(f"  WF Mean AUC:   {np.mean(best_aucs):.4f} ± {np.std(best_aucs):.4f}")
    print(f"  V5 Baseline:   Test AUC={r1['test_auc']:.4f}, Brier={r1['test_brier']:.4f}")
    print(f"  Delta AUC:     {best['test_auc'] - r1['test_auc']:+.4f}")
    print(f"  Delta Brier:   {best['test_brier'] - r1['test_brier']:+.4f}")
    print(f"  {'='*66}")


if __name__ == "__main__":
    main()
