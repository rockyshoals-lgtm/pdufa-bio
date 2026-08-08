#!/usr/bin/env python3
"""
GUNGNIR v47 HONEST REBUILD — 4-way temporal split, val-only selection

Methodology (mirrors ODIN v16):
  Train  ≤2023-06         (C fit, meta-learner fit)
  Val    2023-07..2024-06  (C sweep, backward elim, meta weight sweep, temperature scaling)
  Test   2024-07..2025-06  (touched ONCE — confirms test-leakage corrected)
  Final  ≥2025-07          (truly blind — final bar)

Bar to beat: v46 honest Final HO AUC 0.7551 (Brier 0.1529).

Steps:
  1. Build v46's 126-feature matrix via its kaizen chain.
  2. Scale on train; fit Ridge+XGB on train; combine via meta-learner tuned on val.
  3. Backward elimination — drop features whose removal improves or holds val AUC (Δ≥0).
  4. C sweep for Ridge on val.
  5. XGB tree-count sweep on val.
  6. Meta-weight sweep on val (100/0, 90/10, 80/20, 70/30, Ridge only).
  7. Temperature scaling on val for Brier calibration.
  8. Snapshot test + final HO metrics (touched once).
"""

import os, sys, io, json, time, warnings, math
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

RANDOM_SEED = 42
TARGET_FINAL_AUC = 0.7551  # v46 honest final HO AUC — bar to beat
np.random.seed(RANDOM_SEED)

# ---------------------------------------------------------------
# Step 0 — feature matrix from v46 kaizen chain
# ---------------------------------------------------------------
print("=" * 70)
print("GUNGNIR v47 HONEST REBUILD")
print("=" * 70)
t0 = time.time()

print("\n[0/8] Loading v46 kaizen pipeline (building 126-feature matrix)...")
old = sys.stdout; sys.stdout = io.StringIO()
try:
    import gungnir_v46_kaizen as k
finally:
    sys.stdout = old

v39 = k.load_v39_module()

old = sys.stdout; sys.stdout = io.StringIO()
events, ctgov_lookup = v39.load_data()
X_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
    events, ctgov_lookup, include_v37=True, include_v38=True,
    include_candidates=k.V39_SELECTED
)
v40_lookup = k.build_v40_features(events)
v40_cols = []
for f in k.V40_SELECTED:
    col = np.array([float(v40_lookup.get(
        (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(f, 0) or 0)
        for ev in events])
    v40_cols.append(col)
X_v40 = np.column_stack([X_v39] + [c.reshape(-1, 1) for c in v40_cols])
feat_v40 = list(feat_v39) + k.V40_SELECTED

v41_dict = k.build_v41_features(events, X_v40, feat_v40, v40_lookup)
X_v41 = np.column_stack([X_v40] + [v41_dict[f].reshape(-1, 1) for f in k.V41_SELECTED])
feat_v41 = list(feat_v40) + k.V41_SELECTED

v42_dict = k.build_v42_features(events, X_v41, feat_v41)
X_v42 = np.column_stack([X_v41] + [v42_dict[f].reshape(-1, 1) for f in k.V42_SELECTED])
feat_v42 = list(feat_v41) + k.V42_SELECTED

ch2_features = k.build_chembl_features(events)
v43_dict = k.build_v43_features(events, X_v42, feat_v42, ch2_features)
X_v43 = np.column_stack([X_v42] + [v43_dict[f].reshape(-1, 1) for f in k.V43_SELECTED])
feat_v43 = list(feat_v42) + k.V43_SELECTED

v44_dict = k.build_v44_features(events, X_v43, feat_v43, ch2_features)
X_v44 = np.column_stack([X_v43] + [v44_dict[f].reshape(-1, 1) for f in k.V44_SELECTED])
feat_v44 = list(feat_v43) + k.V44_SELECTED

keep = [i for i, f in enumerate(feat_v44) if f not in k.V45_DROPPED]
X_v45 = X_v44[:, keep]
feat_v45 = [feat_v44[i] for i in keep]

deploy = json.load(open(os.path.join(DATA_DIR, "gungnir_v46_deploy.json")))
v46_selected = [f for f in deploy.get("features", []) if f.startswith("v46_")]
if not v46_selected:
    v46_selected = [
        "v46_p1_ch2_moa_agonist", "v46_p6_fic_X_is_phase3_X_sponsor",
        "v46_p6_sponsor_X_ch2_is_adc_X_is_phase2",
        "v46_p6_conf_X_ch2_is_advanced_X_is_small",
        "v46_p5_log1p_journey_last_positive",
        "v46_p2_ch2_is_adc_X_journey_n_negative",
        "v46_p6_conf_X_ch2_is_mab_X_is_small",
        "v46_p2_ch2_is_adc_X_journey_had_negative",
    ]
v46_dict = k.generate_v46_candidates(events, X_v45, feat_v45, ch2_features, v40_lookup)
v46_selected = [f for f in v46_selected if f in v46_dict]
X_full = np.column_stack([X_v45] + [v46_dict[f].reshape(-1, 1) for f in v46_selected])
feat_full = list(feat_v45) + v46_selected

sys.stdout = old
print(f"  Events: {len(events)}  Features: {X_full.shape[1]}")
print(f"  Build time: {time.time()-t0:.1f}s")

# ---------------------------------------------------------------
# 4-way temporal split
# ---------------------------------------------------------------
print("\n[1/8] 4-way temporal split...")
dates_arr = np.array(dates)
train_mask = dates_arr < "2023-07-01"
val_mask   = (dates_arr >= "2023-07-01") & (dates_arr < "2024-07-01")
test_mask  = (dates_arr >= "2024-07-01") & (dates_arr < "2025-07-01")
final_mask = dates_arr >= "2025-07-01"

for name, m in [("Train ≤2023-06", train_mask), ("Val 2023H2-2024H1", val_mask),
                ("Test 2024H2-2025H1", test_mask), ("Final ≥2025H2", final_mask)]:
    n = int(m.sum())
    pr = float(y_bin[m].mean()) if n else 0.0
    print(f"  {name}: n={n}, pos_rate={pr:.1%}")

X_tr = X_full[train_mask]; y_tr = y_bin[train_mask]
X_va = X_full[val_mask];   y_va = y_bin[val_mask]
X_te = X_full[test_mask];  y_te = y_bin[test_mask]
X_fn = X_full[final_mask]; y_fn = y_bin[final_mask]

scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_va_s = scaler.transform(X_va)
X_te_s = scaler.transform(X_te)
X_fn_s = scaler.transform(X_fn)

feat_idx = {f: i for i, f in enumerate(feat_full)}

# ---------------------------------------------------------------
# Step 2 — baseline Ridge at C=0.05 (v46 honest pick)
# ---------------------------------------------------------------
print("\n[2/8] Baseline Ridge C=0.05 (v46 honest config)...")
def fit_ridge(C, X, y):
    m = LogisticRegression(C=C, solver="lbfgs", max_iter=2000, random_state=RANDOM_SEED, n_jobs=-1)
    m.fit(X, y)
    return m

def auc(model, X, y):
    p = model.predict_proba(X)[:, 1]
    return roc_auc_score(y, p) if len(set(y)) > 1 else 0.5

base_model = fit_ridge(0.05, X_tr_s, y_tr)
base_val = auc(base_model, X_va_s, y_va)
base_test = auc(base_model, X_te_s, y_te)
base_final = auc(base_model, X_fn_s, y_fn)
print(f"  Baseline (126 feats, C=0.05): val={base_val:.4f}  test={base_test:.4f}  final={base_final:.4f}")

# ---------------------------------------------------------------
# Step 3 — backward elimination on VAL AUC
# ---------------------------------------------------------------
print("\n[3/8] Backward elimination (drop features where val AUC improves or holds)...")
drop_candidates = list(range(X_full.shape[1]))

# Rank features by |coefficient| — prune smallest first for efficiency
coefs = np.abs(base_model.coef_[0])
rank_order = np.argsort(coefs)

keep_set = set(range(X_full.shape[1]))
current_val = base_val
history = []
# Allow DROP_DELTA ≥ -2bp (don't drop features that cost >2bp on val)
DROP_DELTA = -0.0002
checked = 0
for feat_i in rank_order:
    if feat_i not in keep_set:
        continue
    trial = sorted(keep_set - {feat_i})
    if len(trial) < 20:
        break
    X_tr_t = X_tr_s[:, trial]
    X_va_t = X_va_s[:, trial]
    m = fit_ridge(0.05, X_tr_t, y_tr)
    va = auc(m, X_va_t, y_va)
    delta = va - current_val
    checked += 1
    if delta >= DROP_DELTA:
        keep_set = set(trial)
        current_val = va
        history.append({"dropped": feat_full[feat_i], "new_val": float(va), "delta_bp": delta*10000})
    if checked > 130:
        break

dropped_feats = sorted([feat_full[i] for i in range(X_full.shape[1]) if i not in keep_set])
kept_idx = sorted(list(keep_set))
print(f"  Dropped {len(dropped_feats)} features, kept {len(kept_idx)}. Val AUC after pruning: {current_val:.4f}")
if history:
    print(f"  First 5 drops: {[h['dropped'] for h in history[:5]]}")
    print(f"  Last 5 drops: {[h['dropped'] for h in history[-5:]]}")

X_tr_p = X_tr_s[:, kept_idx]
X_va_p = X_va_s[:, kept_idx]
X_te_p = X_te_s[:, kept_idx]
X_fn_p = X_fn_s[:, kept_idx]
feat_pruned = [feat_full[i] for i in kept_idx]

# ---------------------------------------------------------------
# Step 4 — C sweep on VAL (pruned feature set)
# ---------------------------------------------------------------
print("\n[4/8] C sweep on VAL (pruned features)...")
best_c = None; best_c_val = -1; best_c_model = None
for C in [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2, 0.5]:
    m = fit_ridge(C, X_tr_p, y_tr)
    va = auc(m, X_va_p, y_va)
    tr_auc = auc(m, X_tr_p, y_tr)
    print(f"  C={C:<6} train={tr_auc:.4f}  val={va:.4f}")
    if va > best_c_val:
        best_c_val = va; best_c = C; best_c_model = m
print(f"  Best C (VAL only): {best_c}  val AUC={best_c_val:.4f}")

# ---------------------------------------------------------------
# Step 5 — Optional XGB sweep on val (val-only selection)
# ---------------------------------------------------------------
print("\n[5/8] XGB tree-count sweep on VAL...")
try:
    import xgboost as xgb
    xgb_available = True
except Exception:
    print("  xgboost unavailable; skipping XGB.")
    xgb_available = False

best_xgb = None; best_xgb_val = -1; best_xgb_cfg = None
if xgb_available:
    for n_trees in [200, 300, 400, 500]:
        for lr in [0.01, 0.03]:
            m = xgb.XGBClassifier(
                n_estimators=n_trees, learning_rate=lr, max_depth=3,
                subsample=0.8, colsample_bytree=0.8, random_state=RANDOM_SEED,
                use_label_encoder=False, eval_metric="logloss", n_jobs=-1, verbosity=0,
            )
            m.fit(X_tr_p, y_tr)
            va = roc_auc_score(y_va, m.predict_proba(X_va_p)[:, 1])
            if va > best_xgb_val:
                best_xgb_val = va; best_xgb = m; best_xgb_cfg = (n_trees, lr)
    print(f"  Best XGB: trees={best_xgb_cfg[0]} lr={best_xgb_cfg[1]}  val AUC={best_xgb_val:.4f}")

# ---------------------------------------------------------------
# Step 6 — Meta-weight sweep on VAL
# ---------------------------------------------------------------
print("\n[6/8] Meta-weight sweep on VAL (ridge vs xgb blend)...")
p_ridge_val = best_c_model.predict_proba(X_va_p)[:, 1]
p_ridge_test = best_c_model.predict_proba(X_te_p)[:, 1]
p_ridge_final = best_c_model.predict_proba(X_fn_p)[:, 1]

if xgb_available:
    p_xgb_val = best_xgb.predict_proba(X_va_p)[:, 1]
    p_xgb_test = best_xgb.predict_proba(X_te_p)[:, 1]
    p_xgb_final = best_xgb.predict_proba(X_fn_p)[:, 1]
    best_w = 1.0; best_blend_val = best_c_val
    for w in [1.0, 0.95, 0.90, 0.85, 0.80, 0.70, 0.60, 0.50, 0.40, 0.20, 0.0]:
        p = w * p_ridge_val + (1 - w) * p_xgb_val
        va = roc_auc_score(y_va, p)
        print(f"  Ridge {w:.2f} / XGB {1-w:.2f}: val AUC={va:.4f}")
        if va > best_blend_val:
            best_blend_val = va; best_w = w
    print(f"  Best blend: Ridge {best_w:.2f} / XGB {1-best_w:.2f}  val AUC={best_blend_val:.4f}")
else:
    best_w = 1.0; best_blend_val = best_c_val; p_xgb_val = None; p_xgb_test = None; p_xgb_final = None

# ---------------------------------------------------------------
# Step 7 — Temperature scaling on VAL for Brier calibration
# ---------------------------------------------------------------
print("\n[7/8] Temperature scaling on VAL for Brier calibration...")
p_val_final = best_w * p_ridge_val + (1 - best_w) * (p_xgb_val if p_xgb_val is not None else 0.0)
p_test_final = best_w * p_ridge_test + (1 - best_w) * (p_xgb_test if p_xgb_test is not None else 0.0)
p_fn_final = best_w * p_ridge_final + (1 - best_w) * (p_xgb_final if p_xgb_final is not None else 0.0)

# Clip to avoid logit overflow
def logit(p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))
def sigm(z):
    return 1.0 / (1.0 + np.exp(-z))

best_T = 1.0; best_T_brier = brier_score_loss(y_va, p_val_final)
for T in [0.6, 0.75, 0.85, 0.95, 1.0, 1.1, 1.25, 1.5, 2.0]:
    p_T = sigm(logit(p_val_final) / T)
    b = brier_score_loss(y_va, p_T)
    if b < best_T_brier:
        best_T_brier = b; best_T = T
print(f"  Best T: {best_T:.2f}  val Brier={best_T_brier:.4f}")

p_val_T = sigm(logit(p_val_final) / best_T)
p_test_T = sigm(logit(p_test_final) / best_T)
p_fn_T = sigm(logit(p_fn_final) / best_T)

# ---------------------------------------------------------------
# Step 8 — ONE-SHOT TEST + FINAL HO
# ---------------------------------------------------------------
print("\n[8/8] One-shot TEST + FINAL HO evaluation...")
val_auc = roc_auc_score(y_va, p_val_final)
test_auc = roc_auc_score(y_te, p_test_final) if len(set(y_te)) > 1 else 0.5
final_auc = roc_auc_score(y_fn, p_fn_final) if len(set(y_fn)) > 1 else 0.5
val_brier = brier_score_loss(y_va, p_val_T)
test_brier = brier_score_loss(y_te, p_test_T)
final_brier = brier_score_loss(y_fn, p_fn_T)

print("\n" + "=" * 70)
print("GUNGNIR v47 HONEST RESULTS")
print("=" * 70)
print(f"  Features kept:          {len(feat_pruned)} / {len(feat_full)}")
print(f"  Features dropped:       {len(dropped_feats)}")
print(f"  Best C (VAL):           {best_c}")
if xgb_available:
    print(f"  Best XGB:               trees={best_xgb_cfg[0]} lr={best_xgb_cfg[1]}")
print(f"  Best meta weight:       Ridge {best_w:.2f} / XGB {1-best_w:.2f}")
print(f"  Best T (calibration):   {best_T:.2f}")
print()
print(f"  VAL AUC (selection):    {val_auc:.4f}   Brier: {val_brier:.4f}")
print(f"  TEST AUC (touched 1x):  {test_auc:.4f}   Brier: {test_brier:.4f}")
print(f"  FINAL HO AUC (blind):   {final_auc:.4f}   Brier: {final_brier:.4f}")
print()
print(f"  v46 honest Final HO AUC: {TARGET_FINAL_AUC:.4f}")
print(f"  v47 delta vs v46 honest: {(final_auc - TARGET_FINAL_AUC)*10000:+.0f} bp")
print(f"  v46 honest Final HO Brier: 0.1529")
print(f"  v47 delta Brier: {(final_brier - 0.1529)*10000:+.0f} bp")

# ---------------------------------------------------------------
# Bootstrap CI on Final HO AUC
# ---------------------------------------------------------------
print("\nBootstrap 95% CI on Final HO AUC (n_boot=1000)...")
rng = np.random.default_rng(RANDOM_SEED)
n_fn = len(y_fn)
boot_aucs = []
for _ in range(1000):
    idx = rng.integers(0, n_fn, n_fn)
    if len(set(y_fn[idx])) < 2:
        continue
    boot_aucs.append(roc_auc_score(y_fn[idx], p_fn_final[idx]))
boot_aucs = np.array(boot_aucs)
ci_lo = float(np.percentile(boot_aucs, 2.5))
ci_hi = float(np.percentile(boot_aucs, 97.5))
print(f"  Final HO AUC {final_auc:.4f} [95% CI {ci_lo:.4f}, {ci_hi:.4f}]")

# ---------------------------------------------------------------
# Coefficient summary
# ---------------------------------------------------------------
coefs_final = best_c_model.coef_[0]
top_by_abs = sorted(zip(feat_pruned, coefs_final), key=lambda t: -abs(t[1]))[:20]
print("\nTop 20 features by |coef|:")
for f, c in top_by_abs:
    print(f"  {c:+7.4f}  {f}")

# ---------------------------------------------------------------
# Save results
# ---------------------------------------------------------------
results = {
    "model": "gungnir_v47_honest",
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "methodology": "4-way split (train ≤2023-06 / val 2023H2-2024H1 / test 2024H2-2025H1 / final ≥2025H2). All hyperparam + feature selection on VAL only. Test and Final touched ONCE.",
    "split": {
        "train_n": int(train_mask.sum()), "val_n": int(val_mask.sum()),
        "test_n": int(test_mask.sum()),   "final_n": int(final_mask.sum()),
        "train_pos_rate": float(y_tr.mean()), "val_pos_rate": float(y_va.mean()),
        "test_pos_rate": float(y_te.mean()), "final_pos_rate": float(y_fn.mean()),
    },
    "feature_pruning": {
        "start_features": len(feat_full),
        "kept_features": len(feat_pruned),
        "dropped_features": dropped_feats,
        "drop_history": history,
    },
    "config": {
        "ridge_C": best_c,
        "xgb_trees": best_xgb_cfg[0] if xgb_available and best_xgb_cfg else None,
        "xgb_lr": best_xgb_cfg[1] if xgb_available and best_xgb_cfg else None,
        "meta_ridge_weight": best_w,
        "temperature": best_T,
    },
    "honest_metrics": {
        "val_auc": float(val_auc), "val_brier": float(val_brier),
        "test_auc": float(test_auc), "test_brier": float(test_brier),
        "final_auc": float(final_auc), "final_brier": float(final_brier),
        "final_auc_ci95": [ci_lo, ci_hi],
    },
    "comparison": {
        "v46_deployed_auc": 0.8135,
        "v46_honest_test_auc": 0.7841,
        "v46_honest_final_auc": TARGET_FINAL_AUC,
        "v46_honest_final_brier": 0.1529,
        "v47_final_auc": float(final_auc),
        "v47_final_brier": float(final_brier),
        "v47_delta_vs_v46_honest_bp": (final_auc - TARGET_FINAL_AUC) * 10000,
        "v47_delta_brier_bp": (final_brier - 0.1529) * 10000,
    },
    "top_features": [(f, float(c)) for f, c in top_by_abs],
    "features_kept": feat_pruned,
}
out = os.path.join(DATA_DIR, "gungnir_v47_honest_results.json")
json.dump(results, open(out, "w"), indent=2)
print(f"\nResults saved: {out}")
print(f"\nTotal run time: {time.time()-t0:.1f}s")
