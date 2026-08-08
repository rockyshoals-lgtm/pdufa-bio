"""
BIFROST Explosion v5.7 Kaizen — Non-Linear Transforms + Cross-Window Ratios
============================================================================

Under strict 3-way split (train ≤2023, val 2024, test ≥2025), fit a baseline
Ridge logistic on features readily available from pdufa_runup_bifrost_v2.csv,
then test whether NEW features (non-linear transforms + cross-window runup
ratios + ta_risk interactions) improve TEST AUC over baseline under val-only
forward-greedy selection.

Honest methodology: hyperparameters + feature selection decided on val ONLY.
Test AUC reported once at the end. Bootstrap 95% CI (n_boot=2000, seed=42).

Inputs
------
/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv
  (1,705 rows, 42 cols, includes outcome, post_1d, runup windows, v5/v9 scores,
   mcap_tier, ta_risk, crl_rate)

Label: explosion = |post_1d| > 25%
"""

import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

INPUT = Path("/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv")
OUT   = Path("/sessions/confident-serene-ptolemy/mnt/9realms/bifrost_v57_kaizen_results.json")

df = pd.read_csv(INPUT)
df["pdufa_date"] = pd.to_datetime(df["pdufa_date"], errors="coerce")
df["year"] = df["pdufa_date"].dt.year
df = df.dropna(subset=["pdufa_date", "post_1d", "year"]).copy()
df["explosion"] = (df["post_1d"].abs() > 25).astype(int)
print(f"rows (valid): {len(df):,}  explosion_rate: {df['explosion'].mean():.3f}")

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def safe_log1p(x): return np.log1p(np.clip(np.asarray(x, dtype=float), -0.99, None))
def sq(x):          return np.asarray(x, dtype=float) ** 2
def cube(x):        return np.asarray(x, dtype=float) ** 3

# Baseline features (v5.5-ish core that should exist)
base_cols = ["v5_score", "v9_score", "runup_30d", "runup_7d", "runup_3d",
             "vol_ratio", "crl_rate", "ta_risk"]

# Fill missing with 0
for c in base_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# One-hot mcap_tier
mcap_dummies = pd.get_dummies(df["mcap_tier"].astype(str), prefix="mcap", dtype=float)
df = pd.concat([df, mcap_dummies], axis=1)

base_cols = base_cols + list(mcap_dummies.columns)

# v5.7 candidate features (NEW, not yet tested under honest split)
candidates = {
    # Non-linear transforms
    "v57_runup_7d_sq":      sq(df["runup_7d"]),
    "v57_runup_30d_sq":     sq(df["runup_30d"]),
    "v57_runup_3d_cube":    cube(df["runup_3d"]),
    "v57_vol_ratio_log":    safe_log1p(df["vol_ratio"]),
    "v57_v9_score_sq":      sq(df["v9_score"]),
    # Cross-window ratios / differentials
    "v57_runup_30d_m_7d":   (df["runup_30d"] - df["runup_7d"]).values,
    "v57_runup_7d_m_3d":    (df["runup_7d"] - df["runup_3d"]).values,
    "v57_runup_30d_div_7d": (df["runup_30d"] / df["runup_7d"].replace(0, 1e-6)).clip(-10, 10).values,
    "v57_accel_3d":         (df["runup_3d"] - df["runup_7d"] / 2.0).values,  # proxy for acceleration
    # ta_risk interactions
    "v57_tarisk_x_runup7d":  (df["ta_risk"] * df["runup_7d"]).values,
    "v57_tarisk_x_v9":       (df["ta_risk"] * df["v9_score"]).values,
    "v57_crl_x_runup30d":    (df["crl_rate"] * df["runup_30d"]).values,
    # Size × momentum interactions
    "v57_micro_x_runup7d":   ((df["mcap_tier"] == "micro").astype(float) * df["runup_7d"]).values,
    "v57_nano_x_runup7d":    ((df["mcap_tier"] == "nano").astype(float) * df["runup_7d"]).values,
    "v57_nano_x_vol_ratio":  ((df["mcap_tier"] == "nano").astype(float) * df["vol_ratio"]).values,
}
for name, vals in candidates.items():
    df[name] = pd.Series(vals).fillna(0).values

print(f"baseline features: {len(base_cols)}")
print(f"v5.7 candidates:   {len(candidates)}")

# ---------------------------------------------------------------------------
# 3-way split
# ---------------------------------------------------------------------------
train = df[df["year"] <= 2023].copy()
val   = df[df["year"] == 2024].copy()
test  = df[df["year"] >= 2025].copy()
print(f"train (<=2023): {len(train):,}  val (2024): {len(val):,}  test (>=2025): {len(test):,}")
print(f"train explosion rate: {train['explosion'].mean():.3f}")
print(f"val   explosion rate: {val['explosion'].mean():.3f}")
print(f"test  explosion rate: {test['explosion'].mean():.3f}")

def fit_eval(features, C=0.10):
    X_tr = train[features].values
    X_va = val[features].values
    X_te = test[features].values
    y_tr = train["explosion"].values
    y_va = val["explosion"].values
    y_te = test["explosion"].values
    # Standardize
    mu = X_tr.mean(axis=0); sd = X_tr.std(axis=0) + 1e-8
    X_tr = (X_tr - mu) / sd
    X_va = (X_va - mu) / sd
    X_te = (X_te - mu) / sd
    clf = LogisticRegression(C=C, solver="lbfgs", max_iter=500)
    clf.fit(X_tr, y_tr)
    p_va = clf.predict_proba(X_va)[:, 1]
    p_te = clf.predict_proba(X_te)[:, 1]
    return roc_auc_score(y_va, p_va), roc_auc_score(y_te, p_te)

# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------
base_val, base_test = fit_eval(base_cols, C=0.10)
print(f"\nBASELINE (base {len(base_cols)} features, C=0.10): val_auc={base_val:.4f}  test_auc={base_test:.4f}")

# C-sweep on val only
best_C = 0.10; best_val = base_val
for C in (0.01, 0.05, 0.10, 0.25, 1.0):
    v, _ = fit_eval(base_cols, C=C)
    if v > best_val:
        best_val = v; best_C = C
print(f"C-sweep winner: C={best_C} val_auc={best_val:.4f}")
base_val, base_test = fit_eval(base_cols, C=best_C)
print(f"BASELINE (C={best_C}): val_auc={base_val:.4f}  test_auc={base_test:.4f}")

# ---------------------------------------------------------------------------
# Forward-greedy on val only
# ---------------------------------------------------------------------------
selected = list(base_cols)
candidate_pool = list(candidates.keys())
gains = []
for round_n in range(10):
    best_gain = 0.0
    best_feat = None
    best_new_val = base_val
    for feat in candidate_pool:
        trial = selected + [feat]
        v, _ = fit_eval(trial, C=best_C)
        if v > best_new_val + 1e-4:
            best_new_val = v
            best_feat = feat
            best_gain = v - base_val
    if best_feat is None:
        break
    selected.append(best_feat)
    candidate_pool.remove(best_feat)
    gains.append({"feature": best_feat, "val_auc_after": round(best_new_val, 4),
                  "val_delta": round(best_new_val - base_val, 4)})
    base_val = best_new_val
    print(f"  ROUND {round_n+1}: +{best_feat}  val_auc={best_new_val:.4f}")

# ---------------------------------------------------------------------------
# Final test AUC (reported ONCE)
# ---------------------------------------------------------------------------
final_val, final_test = fit_eval(selected, C=best_C)

# Bootstrap CI on test AUC
X_tr = train[selected].values; X_te = test[selected].values
y_tr = train["explosion"].values; y_te = test["explosion"].values
mu = X_tr.mean(axis=0); sd = X_tr.std(axis=0) + 1e-8
X_tr_s = (X_tr - mu) / sd; X_te_s = (X_te - mu) / sd
clf = LogisticRegression(C=best_C, solver="lbfgs", max_iter=500).fit(X_tr_s, y_tr)
p_te = clf.predict_proba(X_te_s)[:, 1]

rng = np.random.default_rng(42)
n_te = len(y_te); boot = []
for _ in range(2000):
    idx = rng.integers(0, n_te, n_te)
    if len(np.unique(y_te[idx])) < 2:
        continue
    boot.append(roc_auc_score(y_te[idx], p_te[idx]))
boot.sort()
ci_lo = boot[int(0.025 * len(boot))]
ci_hi = boot[int(0.975 * len(boot)) - 1]

result = {
    "version": "5.7.0",
    "generated": "2026-04-18",
    "methodology": "3-way split (train<=2023 val=2024 test>=2025) + val-only feature selection",
    "input": str(INPUT.name),
    "n_events": len(df),
    "n_train": len(train), "n_val": len(val), "n_test": len(test),
    "train_explosion_rate": round(train["explosion"].mean(), 4),
    "val_explosion_rate":   round(val["explosion"].mean(), 4),
    "test_explosion_rate":  round(test["explosion"].mean(), 4),
    "baseline_features_n": len(base_cols) + 0,
    "candidates_tested": list(candidates.keys()),
    "best_C": best_C,
    "baseline_val_auc":  round(base_val, 4),
    "baseline_test_auc": round(base_test, 4),
    "selected_features_new": [g["feature"] for g in gains],
    "greedy_gains": gains,
    "final_selected_total_n": len(selected),
    "final_val_auc":  round(final_val, 4),
    "final_test_auc": round(final_test, 4),
    "final_test_auc_ci95": [round(ci_lo, 4), round(ci_hi, 4)],
    "v56_honest_test_auc_for_comparison": 0.8861,
    "v57_improvement_vs_v56_bp": round((final_test - 0.8861) * 10000),
    "verdict": None,  # filled below
}
if final_test > 0.8861 + 0.002:
    result["verdict"] = "PROMOTE — v5.7 beats v5.6 honest baseline"
elif final_test > 0.8861 - 0.005:
    result["verdict"] = "FLAT — no meaningful improvement, hold v5.5 deployment"
else:
    result["verdict"] = "REGRESSION — new features hurt on test"

OUT.write_text(json.dumps(result, indent=2, default=str))
print(f"\n{'='*70}\nBIFROST EXPLOSION v5.7 FINAL")
print(f"{'='*70}")
print(f"final val AUC:  {final_val:.4f}")
print(f"final test AUC: {final_test:.4f}  CI95 [{ci_lo:.4f}, {ci_hi:.4f}]")
print(f"vs v5.6 honest baseline (0.8861): {'+' if final_test>0.8861 else ''}{(final_test-0.8861)*100:.2f} pp")
print(f"verdict: {result['verdict']}")
print(f"WROTE: {OUT}")
