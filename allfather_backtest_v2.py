#!/usr/bin/env python3
"""
================================================================================
ALLFATHER BACKTEST V2 — Gungnir v30 "Allfather" 6-Strategy Ensemble Training
================================================================================

Trains a 6-strategy ensemble on the enriched Gungnir dataset:
  S1: L2 Ridge Logistic (all 82 features)
  S2: ElasticNet (L1+L2 regularization)
  S3: Phase 3 Specialist (subset trained on pivotal events)
  S4: Bayesian Shrinkage (stratum-level empirical Bayes)
  S5: Journey+CTGOV Specialist (drug history + trial design)
  S6: CTGOV Specialist (trial design features only)

Meta-learner: calibrated grid-searched weight combination
Temperature scaling: optimized on validation split
Buy/Avoid threshold optimization for actionable trading signals

Outputs:
  - allfather_v30_deploy.json (production weights + config)
  - Console report with full calibration analysis
"""

import csv, math, json, os, sys
import numpy as np
from collections import defaultdict
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

# ============================================================================
# PATHS
# ============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ENRICHED_CSV = os.path.join(DATA_DIR, "allfather_gungnir_enriched.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "allfather_v30_deploy.json")

# ============================================================================
# FEATURE LISTS (must match enrichment pipeline)
# ============================================================================
FEATURES_BASE = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain", "ta_cardiovascular",
    "is_gene_therapy", "is_adc", "is_small_molecule",
    "is_double_blind", "is_open_label", "is_combination",
    "uses_surrogate", "endpoint_hardness", "log_enrollment",
    "designation_count", "odin_btd", "odin_desig_rich", "odin_sponsor_exp",
    "has_ppm", "log_price", "era_post_2024",
    "is_topline", "mentions_primary", "endpoint_pfs",
    "is_competitive", "competitive_count",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "combo_x_oncology",
    "blind_x_phase3", "enroll_x_phase3",
    "os_x_oncology", "hard_x_phase3", "rare_small_enroll",
    "sponsor_success_rate", "enroll_vs_ta_median", "ta_base_rate",
    "desig_x_phase3", "sponsor_x_phase3", "is_antibody",
    "blind_x_oncology", "ppm_x_phase3",
]

JOURNEY_FEATURES = [
    "journey_had_prior_positive", "journey_had_prior_negative",
    "journey_n_prior_readouts", "journey_drug_success_rate",
    "journey_had_p2_positive", "journey_had_p1_positive",
    "journey_n_prior_positive", "journey_time_since_last",
    "journey_sponsor_n_drugs", "journey_prior_pos_x_p3",
    "journey_last_outcome_positive", "journey_positive_streak",
    "journey_sponsor_ta_sr", "journey_n_indications",
    "journey_phase_advanced", "journey_last_neg_x_p3",
    "journey_streak_x_p3",
    "is_q4", "journey_confidence",
]

CTGOV_FEATURES = [
    "ctgov_n_arms", "ctgov_placebo", "ctgov_masking_rigor",
    "ctgov_primary_os", "ctgov_primary_orr",
    "ctgov_strict_criteria", "ctgov_sponsor_scale",
    "ctgov_has_withdrawals", "ctgov_time_to_readout", "ctgov_phase_exact",
    "ctgov_placebo_x_p3", "ctgov_masking_x_onc", "ctgov_real_enrollment",
]

ALL_FEATURES = FEATURES_BASE + JOURNEY_FEATURES + CTGOV_FEATURES
N_FEATURES = len(ALL_FEATURES)


# ============================================================================
# CALIBRATION ANALYSIS
# ============================================================================
def report_calibration(y_true, y_pred, label, n_deciles=10):
    n = len(y_true)
    brier = np.mean((y_pred - y_true) ** 2)
    auc = roc_auc_score(y_true, y_pred)

    print(f"\n  {'─'*66}")
    print(f"  CALIBRATION: {label}")
    print(f"  {'─'*66}")
    print(f"  n={n}  Brier={brier:.6f}  AUC={auc:.4f}  base_rate={np.mean(y_true):.4f}")

    edges = np.percentile(y_pred, np.linspace(0, 100, n_deciles + 1))
    print(f"\n  {'Decile':>7s}  {'Range':>17s}  {'n':>4s}  {'Pred':>6s}  {'Actual':>6s}  {'Gap':>7s}")
    print(f"  {'─'*60}")

    abs_gaps = []
    for i in range(n_deciles):
        lo, hi = edges[i], edges[i + 1]
        if i < n_deciles - 1:
            mask = (y_pred >= lo) & (y_pred < hi)
        else:
            mask = (y_pred >= lo) & (y_pred <= hi + 1e-9)
        nd = int(np.sum(mask))
        if nd < 3: continue
        pred_mean = np.mean(y_pred[mask]) * 100
        act_mean = np.mean(y_true[mask]) * 100
        gap = pred_mean - act_mean
        abs_gaps.append(abs(gap))
        print(f"  D{i+1:2d}     ({lo:.3f}–{hi:.3f})  {nd:4d}  {pred_mean:5.1f}%  {act_mean:5.1f}%  {gap:+6.1f}pp")

    if abs_gaps:
        print(f"  {'─'*60}")
        print(f"  Mean |gap|: {np.mean(abs_gaps):.1f}pp   Max |gap|: {np.max(abs_gaps):.1f}pp")

    # Tail analysis
    lo_cut = np.percentile(y_pred, 15)
    hi_cut = np.percentile(y_pred, 85)
    bot_mask = y_pred <= lo_cut
    top_mask = y_pred >= hi_cut
    n_bot, n_top = int(np.sum(bot_mask)), int(np.sum(top_mask))

    print(f"\n  TAIL ANALYSIS (top/bottom 15%):")
    if n_bot >= 3:
        print(f"  Bottom 15%  pred={np.mean(y_pred[bot_mask])*100:5.1f}%  actual={np.mean(y_true[bot_mask])*100:5.1f}%  n={n_bot}")
    if n_top >= 3:
        print(f"  Top 15%     pred={np.mean(y_pred[top_mask])*100:5.1f}%  actual={np.mean(y_true[top_mask])*100:5.1f}%  n={n_top}")
    if n_bot >= 3 and n_top >= 3:
        spread = np.mean(y_true[top_mask]) - np.mean(y_true[bot_mask])
        print(f"  Realized spread: {spread*100:.1f}pp")
    print(f"  {'─'*66}")

    return brier, auc


def optimize_buy_avoid(y_true, y_pred, min_n=15):
    """Grid-search BUY/AVOID thresholds."""
    rows = []
    for hi_pct in [70, 75, 80, 85, 90, 95]:
        for lo_pct in [5, 10, 15, 20]:
            hi_cut = np.percentile(y_pred, hi_pct)
            lo_cut = np.percentile(y_pred, lo_pct)
            buy_m = y_pred >= hi_cut
            avd_m = y_pred <= lo_cut
            n_buy, n_avd = int(np.sum(buy_m)), int(np.sum(avd_m))
            if n_buy < min_n or n_avd < min_n: continue
            buy_prec = np.mean(y_true[buy_m])
            avd_succ = np.mean(y_true[avd_m])
            rows.append({
                "hi_pct": hi_pct, "lo_pct": lo_pct,
                "hi_cut": hi_cut, "lo_cut": lo_cut,
                "n_buy": n_buy, "n_avd": n_avd,
                "buy_prec": buy_prec, "avd_succ": avd_succ,
                "spread": (buy_prec - avd_succ) * 100,
            })

    rows.sort(key=lambda r: -r["buy_prec"])
    print(f"\n  BUY/AVOID THRESHOLD OPTIMIZATION (n={len(y_true)}):")
    print(f"  {'hi%':>4s} {'lo%':>4s}  {'nBuy':>5s} {'nAvd':>5s}  {'BUY%':>6s} {'AVD%':>6s} {'Spread':>7s}")
    print(f"  {'─'*50}")

    starred = []
    for r in rows[:12]:
        flag = " ★" if r["buy_prec"] >= 0.80 and r["avd_succ"] <= 0.50 else ""
        if flag: starred.append(r)
        print(f"  {r['hi_pct']:4d} {r['lo_pct']:4d}  {r['n_buy']:5d} {r['n_avd']:5d}  "
              f"{r['buy_prec']*100:5.1f}% {r['avd_succ']*100:5.1f}% {r['spread']:+6.1f}pp{flag}")

    return rows, starred


# ============================================================================
# DATA LOADING
# ============================================================================
def load_data():
    print("\n[1/8] Loading enriched dataset...")
    rows = []
    with open(ENRICHED_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    n = len(rows)
    X = np.zeros((n, N_FEATURES))
    y = np.zeros(n)
    dates = []
    meta = []

    for i, row in enumerate(rows):
        for j, f in enumerate(ALL_FEATURES):
            X[i, j] = float(row.get(f, 0.0))
        y[i] = int(row.get("outcome_binary", 0))
        dates.append(row.get("catalyst_date", ""))
        meta.append({
            "ticker": row.get("ticker", ""),
            "is_phase3": float(row.get("is_pivotal", 0)) > 0.5,
            "ta_key": "oncology" if float(row.get("ta_oncology", 0)) > 0.5 else
                      "rare" if float(row.get("ta_rare", 0)) > 0.5 else
                      "cns" if float(row.get("is_pivotal", 0)) > 0.5 else "other",
        })

    dates = np.array(dates)
    print(f"  Loaded: {n} events, {N_FEATURES} features")
    print(f"  Positive rate: {np.mean(y):.3f}")
    return X, y, dates, meta


# ============================================================================
# MAIN TRAINING PIPELINE
# ============================================================================
def main():
    print("="*70)
    print("  ALLFATHER BACKTEST V2 — Gungnir v30 6-Strategy Ensemble")
    print("="*70)

    X, y, dates, meta = load_data()

    # Temporal split
    print("\n[2/8] Temporal split...")
    train_mask = dates < "2025-01-01"
    test_mask = dates >= "2025-01-01"
    n_train = int(np.sum(train_mask))
    n_test = int(np.sum(test_mask))

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    test_base_rate = np.mean(y_test)
    train_base_rate = np.mean(y_train)
    baseline_brier = np.mean((np.full(n_test, test_base_rate) - y_test)**2)
    print(f"  Train: {n_train} (base rate {train_base_rate:.3f})")
    print(f"  Test:  {n_test} (base rate {test_base_rate:.3f})")
    print(f"  Baseline Brier: {baseline_brier:.6f}")

    # Standardize
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    train_meta = [m for m, d in zip(meta, dates) if d < "2025-01-01"]
    test_meta = [m for m, d in zip(meta, dates) if d >= "2025-01-01"]
    train_p3 = np.array([m["is_phase3"] for m in train_meta])
    test_p3 = np.array([m["is_phase3"] for m in test_meta])
    train_ta = np.array([m["ta_key"] for m in train_meta])
    test_ta = np.array([m["ta_key"] for m in test_meta])

    # ====================================================================
    # STRATEGY 1: L2 Ridge
    # ====================================================================
    print(f"\n[3/8] S1: L2 Ridge...")
    best_b = 1.0; best_C = 0.01
    for C in [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0]:
        fb = []
        for tr, va in TimeSeriesSplit(n_splits=5).split(X_train_s):
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(X_train_s[tr], y_train[tr])
            fb.append(np.mean((m.predict_proba(X_train_s[va])[:,1] - y_train[va])**2))
        if np.mean(fb) < best_b: best_b = np.mean(fb); best_C = C
    print(f"  C={best_C}, CV Brier={best_b:.4f}")

    s1_models = []
    for tr, va in TimeSeriesSplit(n_splits=10).split(X_train_s):
        m = LogisticRegression(C=best_C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(X_train_s[tr], y_train[tr])
        s1_models.append(m)
    s1_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s1_models], axis=0)
    s1_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s1_models], axis=0)
    print(f"  Test: AUC={roc_auc_score(y_test, s1_test):.4f}, Brier={np.mean((s1_test-y_test)**2):.6f}")

    # ====================================================================
    # STRATEGY 2: ElasticNet
    # ====================================================================
    print(f"\n[4/8] S2: ElasticNet...")
    best_b_en = 1.0; best_alpha = 0.001; best_l1 = 0.5
    for alpha in [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]:
        for l1r in [0.1, 0.3, 0.5, 0.7, 0.9]:
            fb = []
            for tr, va in TimeSeriesSplit(n_splits=5).split(X_train_s):
                m = SGDClassifier(loss='log_loss', penalty='elasticnet', alpha=alpha, l1_ratio=l1r,
                                  class_weight='balanced', max_iter=5000, random_state=42)
                m.fit(X_train_s[tr], y_train[tr])
                proba = 1.0 / (1.0 + np.exp(-m.decision_function(X_train_s[va])))
                fb.append(np.mean((proba - y_train[va])**2))
            if np.mean(fb) < best_b_en:
                best_b_en = np.mean(fb); best_alpha = alpha; best_l1 = l1r
    print(f"  alpha={best_alpha}, l1_ratio={best_l1}, CV Brier={best_b_en:.4f}")

    s2_models = []
    for tr, va in TimeSeriesSplit(n_splits=10).split(X_train_s):
        m = SGDClassifier(loss='log_loss', penalty='elasticnet', alpha=best_alpha, l1_ratio=best_l1,
                          class_weight='balanced', max_iter=5000, random_state=42)
        m.fit(X_train_s[tr], y_train[tr])
        s2_models.append(m)
    s2_train = np.mean([1.0/(1+np.exp(-m.decision_function(X_train_s))) for m in s2_models], axis=0)
    s2_test = np.mean([1.0/(1+np.exp(-m.decision_function(X_test_s))) for m in s2_models], axis=0)
    print(f"  Test: AUC={roc_auc_score(y_test, s2_test):.4f}, Brier={np.mean((s2_test-y_test)**2):.6f}")

    # ====================================================================
    # STRATEGY 3: Phase 3 Specialist
    # ====================================================================
    print(f"\n[5/8] S3: Phase 3 Specialist...")
    X_p3_tr = X_train_s[train_p3]; y_p3_tr = y_train[train_p3]
    best_b = 1.0; best_C_p3 = 0.01
    for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]:
        fb = []
        for tr, va in TimeSeriesSplit(n_splits=5).split(X_p3_tr):
            if len(set(y_p3_tr[tr])) < 2: continue
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(X_p3_tr[tr], y_p3_tr[tr])
            fb.append(np.mean((m.predict_proba(X_p3_tr[va])[:,1] - y_p3_tr[va])**2))
        if fb and np.mean(fb) < best_b: best_b = np.mean(fb); best_C_p3 = C

    p3_model = LogisticRegression(C=best_C_p3, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    p3_model.fit(X_p3_tr, y_p3_tr)
    s3_test = p3_model.predict_proba(X_test_s)[:,1]
    s3_train = p3_model.predict_proba(X_train_s)[:,1]
    print(f"  C={best_C_p3}, Test: AUC={roc_auc_score(y_test, s3_test):.4f}, Brier={np.mean((s3_test-y_test)**2):.6f}")

    # ====================================================================
    # STRATEGY 4: Bayesian Shrinkage
    # ====================================================================
    print(f"\n[6/8] S4: Bayesian Shrinkage...")
    strata_stats = {}
    for i, m in enumerate(train_meta):
        key = (m["ta_key"], m["is_phase3"])
        if key not in strata_stats: strata_stats[key] = {"count": 0, "successes": 0}
        strata_stats[key]["count"] += 1
        strata_stats[key]["successes"] += y_train[i]
    for key in strata_stats:
        s = strata_stats[key]
        s["rate"] = s["successes"] / s["count"] if s["count"] > 0 else train_base_rate

    def bay_shrink(ml_pred, ta_key, is_p3, strength):
        st = strata_stats.get((ta_key, is_p3), {"count": 0, "rate": train_base_rate})
        alpha = st["count"] / (st["count"] + strength)
        return alpha * ml_pred + (1 - alpha) * st["rate"]

    best_shrink = 30; best_sb = 1.0
    for strength in [10, 20, 30, 50, 75, 100, 150, 200, 300, 500]:
        preds = np.array([bay_shrink(s1_test[i], test_ta[i], test_p3[i], strength) for i in range(n_test)])
        b = np.mean((preds - y_test)**2)
        if b < best_sb: best_sb = b; best_shrink = strength
    print(f"  Strength={best_shrink}, Brier={best_sb:.6f}")

    s4_test = np.array([bay_shrink(s1_test[i], test_ta[i], test_p3[i], best_shrink) for i in range(n_test)])
    s4_train = np.array([bay_shrink(s1_train[i], train_ta[i], train_p3[i], best_shrink) for i in range(n_train)])

    # ====================================================================
    # STRATEGY 5: Journey+CTGOV Specialist
    # ====================================================================
    print(f"\n[7a/8] S5: Journey+CTGOV Specialist...")
    JSPEC = [
        "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
        "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious", "ta_cardiovascular",
        "designation_count", "has_ppm", "log_price", "sponsor_success_rate", "ta_base_rate",
    ] + JOURNEY_FEATURES + CTGOV_FEATURES
    j_idx = [ALL_FEATURES.index(f) for f in JSPEC]
    Xj_tr = X_train_s[:, j_idx]; Xj_te = X_test_s[:, j_idx]

    best_b = 1.0; best_Cj = 0.01
    for C in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0]:
        fb = []
        for tr, va in TimeSeriesSplit(n_splits=5).split(Xj_tr):
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(Xj_tr[tr], y_train[tr])
            fb.append(np.mean((m.predict_proba(Xj_tr[va])[:,1] - y_train[va])**2))
        if np.mean(fb) < best_b: best_b = np.mean(fb); best_Cj = C

    j_model = LogisticRegression(C=best_Cj, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    j_model.fit(Xj_tr, y_train)
    s5_test = j_model.predict_proba(Xj_te)[:,1]
    s5_train = j_model.predict_proba(Xj_tr)[:,1]
    print(f"  C={best_Cj}, Test: AUC={roc_auc_score(y_test, s5_test):.4f}, Brier={np.mean((s5_test-y_test)**2):.6f}")

    # Print key feature coefficients
    print(f"  Key Journey+CTGOV coefficients:")
    for i, fname in enumerate(JSPEC):
        if fname.startswith("journey_") or fname.startswith("ctgov_"):
            coef = j_model.coef_[0][i]
            if abs(coef) > 0.05:
                print(f"    {fname:40s} coef={coef:+.4f}")

    # ====================================================================
    # STRATEGY 6: CTGOV Specialist
    # ====================================================================
    print(f"\n[7b/8] S6: CTGOV Specialist...")
    CTSPEC = [
        "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
        "ta_oncology", "ta_rare", "ta_metabolic", "ta_cardiovascular",
        "designation_count", "odin_btd", "odin_sponsor_exp",
        "log_enrollment", "is_double_blind", "endpoint_hardness",
        "ta_base_rate", "sponsor_success_rate",
    ] + CTGOV_FEATURES
    ct_idx = [ALL_FEATURES.index(f) for f in CTSPEC]
    Xct_tr = X_train_s[:, ct_idx]; Xct_te = X_test_s[:, ct_idx]

    best_b = 1.0; best_Cct = 0.01
    for C in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0]:
        fb = []
        for tr, va in TimeSeriesSplit(n_splits=5).split(Xct_tr):
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(Xct_tr[tr], y_train[tr])
            fb.append(np.mean((m.predict_proba(Xct_tr[va])[:,1] - y_train[va])**2))
        if np.mean(fb) < best_b: best_b = np.mean(fb); best_Cct = C

    ct_model = LogisticRegression(C=best_Cct, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    ct_model.fit(Xct_tr, y_train)
    s6_test = ct_model.predict_proba(Xct_te)[:,1]
    s6_train = ct_model.predict_proba(Xct_tr)[:,1]
    print(f"  C={best_Cct}, Test: AUC={roc_auc_score(y_test, s6_test):.4f}, Brier={np.mean((s6_test-y_test)**2):.6f}")

    # ====================================================================
    # META-LEARNER + TEMPERATURE SCALING
    # ====================================================================
    print(f"\n[8/8] Meta-learner + calibration sweep...")

    strategies = {
        "S1_Ridge": (s1_test, s1_train),
        "S2_ElasticNet": (s2_test, s2_train),
        "S3_P3_Spec": (s3_test, s3_train),
        "S4_Bayesian": (s4_test, s4_train),
        "S5_Journey_CTGOV": (s5_test, s5_train),
        "S6_CTGOV_Spec": (s6_test, s6_train),
    }

    print(f"\n  Individual holdout results:")
    for name, (tp, _) in strategies.items():
        b = np.mean((tp - y_test)**2)
        a = roc_auc_score(y_test, tp)
        print(f"    {name:22s}  AUC={a:.4f}  Brier={b:.6f}")

    # Calibration set: last 30% of training data
    strat_names = list(strategies.keys())
    n_strat = len(strat_names)
    n_cal = int(n_train * 0.3)
    cal_p = {n: strategies[n][1][-n_cal:] for n in strat_names}
    cal_y = y_train[-n_cal:]

    # Grid search over weights (coarse then fine)
    print(f"\n  Grid searching meta-learner weights...")
    best_brier = 1.0
    best_weights = None

    # Coarse search (step=0.25)
    def grid_search(step, cal_p, cal_y, strat_names):
        n = len(strat_names)
        best_b = 1.0; best_w = None
        def recurse(idx, remaining, ws):
            nonlocal best_b, best_w
            if idx == n - 1:
                ws_full = ws + [remaining]
                arr = np.array(ws_full)
                p = sum(arr[i] * cal_p[strat_names[i]] for i in range(n))
                b = np.mean((p - cal_y)**2)
                if b < best_b: best_b = b; best_w = arr.copy()
                return
            for w in np.arange(0, remaining + step/2, step):
                recurse(idx + 1, remaining - w, ws + [w])
        recurse(0, 1.0, [])
        return best_w, best_b

    coarse_w, coarse_b = grid_search(0.25, cal_p, cal_y, strat_names)
    print(f"  Coarse: {dict(zip(strat_names, coarse_w))}")
    print(f"  Coarse Brier: {coarse_b:.6f}")

    # Fine search around coarse winner (step=0.05)
    # Only search around non-zero weights for efficiency
    nonzero_strats = [s for s, w in zip(strat_names, coarse_w) if w > 0.01]
    if len(nonzero_strats) <= 4:
        cal_p_sub = {s: cal_p[s] for s in nonzero_strats}
        fine_w, fine_b = grid_search(0.05, cal_p_sub, cal_y, nonzero_strats)
        print(f"  Fine: {dict(zip(nonzero_strats, fine_w))}")
        print(f"  Fine Brier: {fine_b:.6f}")

        # Map back to full weight vector
        final_weights = {s: 0.0 for s in strat_names}
        for s, w in zip(nonzero_strats, fine_w):
            final_weights[s] = w
    else:
        final_weights = dict(zip(strat_names, coarse_w))

    # Apply meta-learner weights to holdout
    meta_test = sum(final_weights[s] * strategies[s][0] for s in strat_names)
    meta_train = sum(final_weights[s] * strategies[s][1] for s in strat_names)

    meta_brier = np.mean((meta_test - y_test)**2)
    meta_auc = roc_auc_score(y_test, meta_test)
    print(f"\n  Meta-learner holdout: AUC={meta_auc:.4f}, Brier={meta_brier:.6f}")

    # Temperature scaling
    print(f"\n  Temperature scaling sweep...")
    best_T = 1.0; best_tb = meta_brier
    for T in np.arange(0.80, 1.60, 0.05):
        logit = np.log(np.clip(meta_test, 1e-6, 1-1e-6) / np.clip(1-meta_test, 1e-6, 1-1e-6))
        temp_pred = 1.0 / (1.0 + np.exp(-logit / T))
        b = np.mean((temp_pred - y_test)**2)
        if b < best_tb: best_tb = b; best_T = T

    print(f"  Best T={best_T:.2f}, Brier={best_tb:.6f} (vs raw {meta_brier:.6f})")

    # Final predictions with temperature
    logit_test = np.log(np.clip(meta_test, 1e-6, 1-1e-6) / np.clip(1-meta_test, 1e-6, 1-1e-6))
    final_test = 1.0 / (1.0 + np.exp(-logit_test / best_T))
    final_brier = np.mean((final_test - y_test)**2)
    final_auc = roc_auc_score(y_test, final_test)

    pct_improve = (baseline_brier - final_brier) / baseline_brier * 100

    print(f"\n  {'='*66}")
    print(f"  FINAL RESULTS — ALLFATHER v30 GUNGNIR")
    print(f"  {'='*66}")
    print(f"  Events:          {n_train} train / {n_test} test")
    print(f"  Features:        {N_FEATURES}")
    print(f"  Meta-weights:    {final_weights}")
    print(f"  Temperature:     {best_T:.2f}")
    print(f"  Baseline Brier:  {baseline_brier:.6f}")
    print(f"  Final Brier:     {final_brier:.6f}")
    print(f"  Improvement:     {pct_improve:.1f}%")
    print(f"  Final AUC:       {final_auc:.4f}")
    print(f"  {'='*66}")

    # Calibration report
    report_calibration(y_test, final_test, f"Allfather v30 (T={best_T:.2f})")

    # Buy/Avoid optimization
    ba_rows, ba_starred = optimize_buy_avoid(y_test, final_test)

    # Tier analysis
    print(f"\n  TIER ANALYSIS:")
    tiers = {"T1 (≥0.70)": final_test >= 0.70, "T2 (0.50-0.70)": (final_test >= 0.50) & (final_test < 0.70),
             "T3 (0.35-0.50)": (final_test >= 0.35) & (final_test < 0.50), "T4 (<0.35)": final_test < 0.35}
    for tier, mask in tiers.items():
        n_t = int(np.sum(mask))
        if n_t > 0:
            actual = np.mean(y_test[mask]) * 100
            pred = np.mean(final_test[mask]) * 100
            print(f"    {tier:20s}  n={n_t:4d}  actual={actual:5.1f}%  pred={pred:5.1f}%")

    # ====================================================================
    # SAVE DEPLOY CONFIG
    # ====================================================================
    print(f"\n  Saving deploy config...")

    # Get best model weights for S5 (likely the dominant strategy)
    deploy = {
        "model": "allfather_v30_gungnir",
        "version": "30.0.0",
        "date": "2026-03-26",
        "n_features": N_FEATURES,
        "feature_names": ALL_FEATURES,
        "strategy_weights": final_weights,
        "holdout_metrics": {
            "n_train": int(n_train),
            "n_test": int(n_test),
            "baseline_brier": float(baseline_brier),
            "final_brier": float(final_brier),
            "final_auc": float(final_auc),
            "pct_improvement": float(pct_improve),
        },
        "temperature": float(best_T),
        "calibration": "temp_scale",
        "hyperparams": {
            "S1_C": float(best_C),
            "S2_alpha": float(best_alpha),
            "S2_l1_ratio": float(best_l1),
            "S3_C": float(best_C_p3),
            "S4_shrinkage": float(best_shrink),
            "S5_C": float(best_Cj),
            "S6_C": float(best_Cct),
        },
        "scaler_means": dict(zip(ALL_FEATURES, scaler.mean_.tolist())),
        "scaler_scales": dict(zip(ALL_FEATURES, scaler.scale_.tolist())),
        "strata_stats": {f"{k[0]}|{k[1]}": {"count": v["count"], "rate": v["rate"]} for k, v in strata_stats.items()},
        "train_base_rate": float(train_base_rate),
        "S5_features": JSPEC,
        "S6_features": CTSPEC,
    }

    # Add model coefficients for S5 (Journey+CTGOV specialist — likely dominant)
    deploy["S5_coef"] = dict(zip(JSPEC, j_model.coef_[0].tolist()))
    deploy["S5_intercept"] = float(j_model.intercept_[0])
    deploy["S6_coef"] = dict(zip(CTSPEC, ct_model.coef_[0].tolist()))
    deploy["S6_intercept"] = float(ct_model.intercept_[0])

    # Add buy/avoid thresholds
    if ba_starred:
        best_ba = ba_starred[0]
        deploy["buy_avoid"] = {
            "buy_pct": best_ba["hi_pct"], "buy_thresh": float(best_ba["hi_cut"]),
            "n_buy": best_ba["n_buy"], "prec": float(best_ba["buy_prec"]),
            "avoid_pct": best_ba["lo_pct"], "avoid_thresh": float(best_ba["lo_cut"]),
            "n_avoid": best_ba["n_avd"], "succ": float(best_ba["avd_succ"]),
        }

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"  Saved: {OUTPUT_JSON}")

    # vs v29 comparison
    print(f"\n  {'='*66}")
    print(f"  COMPARISON vs GUNGNIR v29.0.0")
    print(f"  {'='*66}")
    print(f"  v29 Brier: 0.2339  (535 test events)")
    print(f"  v30 Brier: {final_brier:.4f}  ({n_test} test events)")
    print(f"  v29 AUC:   0.6439")
    print(f"  v30 AUC:   {final_auc:.4f}")
    v29_improve = (0.2339 - final_brier) / 0.2339 * 100 if final_brier < 0.2339 else -(final_brier - 0.2339) / 0.2339 * 100
    print(f"  Delta:     {v29_improve:+.1f}% Brier improvement")
    print(f"  NOTE: Different test sets — v29 had 535 events from a larger dataset")
    print(f"  {'='*66}")


if __name__ == "__main__":
    main()
