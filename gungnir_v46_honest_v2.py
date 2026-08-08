#!/usr/bin/env python3
"""
GUNGNIR v46 HONEST 4-WAY SPLIT — takes 2

Uses v46 kaizen's feature-building chain (v39 → v40 → v41 → v42 → v43 → v44 → v45 prune → v46 add)
then applies a proper 4-way temporal split:
  Train:  ≤2023-06
  Val:    2023-07 to 2024-06
  Test:   2024-07 to 2025-06  (touched ONCE; used to confirm test-set leakage)
  Final:  ≥2025-07            (true blind holdout)

Selects C on VAL only, reports Test/Final AUCs. NO hyperparameter tuning on test or final.
"""

import os, sys, io, json, time, warnings
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

# Import v46 kaizen (silently)
print("Loading v46 kaizen module (for feature-building chain)...")
old = sys.stdout; sys.stdout = io.StringIO()
try:
    import gungnir_v46_kaizen as k
finally:
    sys.stdout = old

# Pull helpers
v39 = k.load_v39_module()

print("Loading events...")
old = sys.stdout; sys.stdout = io.StringIO()
events, ctgov_lookup = v39.load_data()
sys.stdout = old
print(f"  Events: {len(events)}")

# Build full v46 feature matrix (pre-split — feature generation is event-level)
print("Building v39.1 features...")
old = sys.stdout; sys.stdout = io.StringIO()
X_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
    events, ctgov_lookup, include_v37=True, include_v38=True,
    include_candidates=k.V39_SELECTED
)
sys.stdout = old
print(f"  v39.1: {X_v39.shape}")

print("Building v40 features...")
v40_lookup = k.build_v40_features(events)
v40_cols = []
for f in k.V40_SELECTED:
    col = np.array([float(v40_lookup.get(
        (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(f, 0) or 0)
        for ev in events])
    v40_cols.append(col)
X_v40 = np.column_stack([X_v39] + [c.reshape(-1, 1) for c in v40_cols])
feat_v40 = list(feat_v39) + k.V40_SELECTED

print("Building v41 features...")
v41_dict = k.build_v41_features(events, X_v40, feat_v40, v40_lookup)
X_v41 = np.column_stack([X_v40] + [v41_dict[f].reshape(-1, 1) for f in k.V41_SELECTED])
feat_v41 = list(feat_v40) + k.V41_SELECTED

print("Building v42 features...")
v42_dict = k.build_v42_features(events, X_v41, feat_v41)
X_v42 = np.column_stack([X_v41] + [v42_dict[f].reshape(-1, 1) for f in k.V42_SELECTED])
feat_v42 = list(feat_v41) + k.V42_SELECTED

print("Building ChEMBL + v43 features...")
ch2_features = k.build_chembl_features(events)
v43_dict = k.build_v43_features(events, X_v42, feat_v42, ch2_features)
X_v43 = np.column_stack([X_v42] + [v43_dict[f].reshape(-1, 1) for f in k.V43_SELECTED])
feat_v43 = list(feat_v42) + k.V43_SELECTED

print("Building v44 features...")
v44_dict = k.build_v44_features(events, X_v43, feat_v43, ch2_features)
X_v44 = np.column_stack([X_v43] + [v44_dict[f].reshape(-1, 1) for f in k.V44_SELECTED])
feat_v44 = list(feat_v43) + k.V44_SELECTED
print(f"  v44: {X_v44.shape}")

print("Applying v45 pruning (drop 28 dead/ablation features)...")
keep = [i for i, f in enumerate(feat_v44) if f not in k.V45_DROPPED]
X_v45 = X_v44[:, keep]
feat_v45 = [feat_v44[i] for i in keep]
print(f"  v45: {X_v45.shape}")

# Add v46 features — try to read from deploy JSON which lists the 8 selected
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
print(f"Generating v46 candidate features + selecting {len(v46_selected)}...")
v46_dict = k.generate_v46_candidates(events, X_v45, feat_v45, ch2_features, v40_lookup)
missing = [f for f in v46_selected if f not in v46_dict]
if missing:
    print(f"  WARNING: missing v46 features: {missing}")
    v46_selected = [f for f in v46_selected if f in v46_dict]
X_v46 = np.column_stack([X_v45] + [v46_dict[f].reshape(-1, 1) for f in v46_selected])
feat_v46 = list(feat_v45) + v46_selected
print(f"  v46: {X_v46.shape}")

# ============================================================================
# 4-WAY TEMPORAL SPLIT
# ============================================================================
print("\n" + "=" * 70)
print("HONEST 4-WAY TEMPORAL SPLIT")
print("=" * 70)

dates_arr = np.array(dates)
train_mask = dates_arr < "2023-07-01"
val_mask   = (dates_arr >= "2023-07-01") & (dates_arr < "2024-07-01")
test_mask  = (dates_arr >= "2024-07-01") & (dates_arr < "2025-07-01")
final_mask = dates_arr >= "2025-07-01"

for name, m in [("Train ≤2023-06", train_mask), ("Val 2023H2–2024H1", val_mask),
                ("Test 2024H2–2025H1", test_mask), ("Final ≥2025H2", final_mask)]:
    n = int(m.sum())
    pr = float(y_bin[m].mean()) if n else 0.0
    print(f"  {name}: n={n}, pos rate={pr:.1%}")

X_tr = X_v46[train_mask]; y_tr = y_bin[train_mask]
X_va = X_v46[val_mask];   y_va = y_bin[val_mask]
X_te = X_v46[test_mask];  y_te = y_bin[test_mask]
X_fn = X_v46[final_mask]; y_fn = y_bin[final_mask]

# Scale on TRAIN only
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_va_s = scaler.transform(X_va)
X_te_s = scaler.transform(X_te)
X_fn_s = scaler.transform(X_fn)

# ============================================================================
# HONEST C SELECTION ON VAL ONLY
# ============================================================================
print("\n" + "=" * 70)
print("HONEST C SELECTION (VAL AUC only)")
print("=" * 70)

best_c = None; best_val = -1; best_model = None
for C in [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]:
    m = LogisticRegression(C=C, solver='lbfgs', max_iter=2000, random_state=42, n_jobs=-1)
    m.fit(X_tr_s, y_tr)
    va_pred = m.predict_proba(X_va_s)[:, 1]
    va_auc = roc_auc_score(y_va, va_pred) if len(set(y_va)) > 1 else 0.5
    tr_pred = m.predict_proba(X_tr_s)[:, 1]
    tr_auc = roc_auc_score(y_tr, tr_pred)
    print(f"  C={C:<6} train AUC={tr_auc:.4f}  val AUC={va_auc:.4f}")
    if va_auc > best_val:
        best_val = va_auc; best_c = C; best_model = m

print(f"\n  Best C (selected on VAL only): {best_c}  val AUC={best_val:.4f}")

# ============================================================================
# ONE-SHOT TEST + FINAL AUCs
# ============================================================================
te_pred = best_model.predict_proba(X_te_s)[:, 1]
fn_pred = best_model.predict_proba(X_fn_s)[:, 1]

te_auc = roc_auc_score(y_te, te_pred) if len(set(y_te)) > 1 else 0.5
fn_auc = roc_auc_score(y_fn, fn_pred) if len(set(y_fn)) > 1 else 0.5
te_brier = brier_score_loss(y_te, te_pred)
fn_brier = brier_score_loss(y_fn, fn_pred)

REPORTED = 0.8135

print("\n" + "=" * 70)
print("HONEST RESULTS")
print("=" * 70)
print(f"  Train AUC:     {roc_auc_score(y_tr, best_model.predict_proba(X_tr_s)[:,1]):.4f}")
print(f"  Val AUC:       {best_val:.4f}  [selection set]")
print(f"  TEST AUC:      {te_auc:.4f}  [touched once]")
print(f"  TEST Brier:    {te_brier:.4f}")
print(f"  FINAL HO AUC:  {fn_auc:.4f}  [truly blind]")
print(f"  FINAL Brier:   {fn_brier:.4f}")
print(f"  Approval rate (test): {y_te.mean():.1%}")
print(f"  Approval rate (final): {y_fn.mean():.1%}")
print(f"\n  v46 REPORTED WF AUC:  {REPORTED}")
print(f"  Honest TEST inflation: {(REPORTED - te_auc)*10000:.0f} bp")
print(f"  Honest FINAL inflation: {(REPORTED - fn_auc)*10000:.0f} bp")

results = {
    "model": "gungnir_v46_honest_v2",
    "split": {
        "train_n": int(train_mask.sum()), "val_n": int(val_mask.sum()),
        "test_n": int(test_mask.sum()),   "final_n": int(final_mask.sum()),
        "train_pos_rate": float(y_tr.mean()), "val_pos_rate": float(y_va.mean()),
        "test_pos_rate": float(y_te.mean()), "final_pos_rate": float(y_fn.mean()),
    },
    "honest_replication": {
        "best_c": best_c,
        "train_auc": float(roc_auc_score(y_tr, best_model.predict_proba(X_tr_s)[:,1])),
        "val_auc": float(best_val),
        "test_auc": float(te_auc), "test_brier": float(te_brier),
        "final_auc": float(fn_auc), "final_brier": float(fn_brier),
        "reported_auc": REPORTED,
        "inflation_vs_test_bp": (REPORTED - te_auc) * 10000,
        "inflation_vs_final_bp": (REPORTED - fn_auc) * 10000,
    },
    "n_features": X_v46.shape[1],
}
out = os.path.join(DATA_DIR, "gungnir_v46_honest_v2_results.json")
json.dump(results, open(out, "w"), indent=2)
print(f"\nResults saved: {out}")
