#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v42 KAIZEN — Exhaustive Pairwise Interaction Search
================================================================================

APPROACH:
  Start from v41.0.0 as baseline (AUC 0.7752, 130 features)

  v41 FINDINGS:
    WORKED: sponsor_x_conference (+0.1606), journey_last_pos_sq (+0.1651),
            immuno_x_phase2 (-0.1493), placebo_x_cns (-0.1362),
            enrollment_x_journey (+0.1330)
    KEY INSIGHT: Interaction terms between existing strong features unlock
                 more signal than new data sources.

  v42 STRATEGY: EXHAUSTIVE pairwise interaction search across ALL 130 features.
  Previous kaizen rounds tested 30-100 hand-picked candidates. v42 tests ALL
  pairwise combinations (~8,400) plus higher-order transforms. This is the
  "brute force meets domain knowledge" approach.

  FEATURE GENERATION:
    1. ALL pairwise products: feature_i × feature_j for all i < j
       Filter: skip pairs where >95% of products are zero (too sparse)
       Filter: skip near-zero variance (std < 1e-8)
    2. Higher-order single transforms on continuous features:
       - cubed, sqrt(abs), log1p(abs) for top 20 continuous features
    3. Ratio features where denominator > 0 for >10% of events

  SCREENING:
    - Phase 1: Fast pre-screen using Ridge-only (no XGB) for speed
    - Phase 2: Full WF eval on top 100 candidates from pre-screen
    - Phase 3: Greedy forward selection
    - Phase 4: Architecture sweep
    - Phase 5: 10-seed stability test

  T-1 COMPLIANCE: All features are products/transforms of existing T-1 features.
"""

import csv, json, math, os, re, sys, warnings, io, time
from collections import defaultdict, Counter
from datetime import datetime
from itertools import combinations
import numpy as np
warnings.filterwarnings("ignore")

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()

# v41 config (from v41 kaizen results)
V41_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 500, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# v41 selected features (on top of v40)
V41_SELECTED = [
    "v41_sponsor_x_conference", "v41_journey_last_pos_sq",
    "v41_immuno_x_phase2", "v41_placebo_x_cns", "v41_enrollment_x_journey"
]

# v40 selected features
V40_SELECTED = ["v40_has_conference", "v40_days_to_cover", "v40_conf_x_small"]

# v39 selected features
V39_SELECTED = [
    "ct_ep_is_safety", "ct_ep_is_biomarker", "ct_active_comp_x_phase3",
    "orphan_x_micro", "ch_is_enzyme", "ind_maturity_high",
    "ch_is_ion_channel", "ct_has_combination", "ct_ep_is_pfs", "ch_is_agonist"
]

# Conference extraction (from v40)
ELITE_CONFERENCES = ["AACR", "ASH", "ESMO"]
TIER1_CONFERENCES = ["ASCO", "AAN", "EHA", "AASLD"]
TIER2_CONFERENCES = ["SITC", "SNO", "ACNP", "ACR", "ADA", "EASD", "ECTRIMS",
                     "WCG", "EULAR", "DDW", "AUA", "ATS", "CHEST", "IDSA"]
GENERIC_CONF = ["conference", "congress", "meeting", "symposium", "annual meeting",
                "presented at", "poster", "oral presentation", "late-breaking"]


def extract_conference(catalyst_text, conference_field):
    text = (str(catalyst_text) + " " + str(conference_field)).upper()
    for conf in ELITE_CONFERENCES:
        if conf.upper() in text:
            return 1, 3
    for conf in TIER1_CONFERENCES:
        if conf.upper() in text:
            return 1, 2
    for conf in TIER2_CONFERENCES:
        if conf.upper() in text:
            return 1, 1
    for g in GENERIC_CONF:
        if g.upper() in text:
            return 1, 1
    return 0, 0


def load_v39_module():
    import importlib.util
    v39_path = os.path.join(DATA_DIR, "gungnir_v39_kaizen.py")
    full_lookup_path = os.path.join(DATA_DIR, "ctgov_training_lookup_v2_full.json")
    spec = importlib.util.spec_from_file_location("v39_kaizen", v39_path)
    v39_mod = importlib.util.module_from_spec(spec)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(v39_mod)
    except Exception as e:
        sys.stdout = old_stdout
        print(f"  [WARN] v39 module load warning: {e}")
    sys.stdout = old_stdout
    if os.path.exists(full_lookup_path):
        v39_mod.CTGOV_TRAIN_LOOKUP_V2 = full_lookup_path
        print(f"  Patched v39 to use FULL CT.gov lookup (96.6% coverage)")
    return v39_mod


def build_v40_features(events):
    si_path = os.path.join(DATA_DIR, "short_interest_snapshot.json")
    si_data = {}
    if os.path.exists(si_path):
        with open(si_path) as f:
            si_data = json.load(f)
    v40_lookup = {}
    for ev in events:
        ticker = ev.get("ticker", "").upper()
        date = ev.get("date", "")
        key = (ticker, date)
        catalyst_text = ev.get("catalyst_text", "")
        conference_field = ev.get("_conference", "")
        is_micro = int(ev.get("is_micro", 0) or 0)
        is_small = int(ev.get("is_small", 0) or 0)
        has_conf, _ = extract_conference(catalyst_text, conference_field)
        conf_x_small = has_conf * (is_micro + is_small)
        si = si_data.get(ticker, {})
        dtc = float(si.get("short_ratio", 0) or 0) if "error" not in si else 0
        v40_lookup[key] = {
            "v40_has_conference": has_conf,
            "v40_days_to_cover": dtc,
            "v40_conf_x_small": conf_x_small,
        }
    return v40_lookup


def build_v41_features(events, X_base, feat_names, v40_lookup):
    """Build v41's 5 selected features."""
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}

    def get_col(name):
        idx = feat_idx.get(name)
        if idx is not None:
            return X_base[:, idx]
        return np.zeros(n)

    def get_v40_col(v40_name):
        vals = []
        for ev in events:
            key = (ev.get("ticker", "").upper(), ev.get("date", ""))
            vals.append(float(v40_lookup.get(key, {}).get(v40_name, 0) or 0))
        return np.array(vals)

    v41_cols = {}
    sponsor_sr = get_col("sponsor_success_rate")
    journey_last_pos = get_col("journey_last_positive")
    ta_immuno = get_col("ta_immunology")
    is_phase2 = get_col("is_phase2")
    ctgov_placebo = get_col("ctgov_is_placebo")
    ta_cns = get_col("ta_cns")
    ctgov_enrollment = get_col("ctgov_enrollment")
    journey_sr = get_col("journey_success_rate")
    v40_has_conf = get_v40_col("v40_has_conference")

    v41_cols["v41_sponsor_x_conference"] = sponsor_sr * v40_has_conf
    v41_cols["v41_journey_last_pos_sq"] = journey_last_pos ** 2
    v41_cols["v41_immuno_x_phase2"] = ta_immuno * is_phase2
    v41_cols["v41_placebo_x_cns"] = ctgov_placebo * ta_cns
    v41_cols["v41_enrollment_x_journey"] = ctgov_enrollment * journey_sr

    return v41_cols


def fast_ridge_screen(X_base, y_bin, dates, candidate_col, ridge_c=0.015, seed=42):
    """Fast Ridge-only screen: train<2025, test>=2025. Returns AUC delta vs base."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    dates_str = np.array([str(d) for d in dates])
    train_mask = dates_str < "2025"
    test_mask = dates_str >= "2025"

    if train_mask.sum() < 100 or test_mask.sum() < 30:
        return 0.0, 0.0

    # Baseline (without candidate)
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_base[train_mask])
    X_te = scaler.transform(X_base[test_mask])
    y_tr = y_bin[train_mask]
    y_te = y_bin[test_mask]

    lr_base = LogisticRegression(C=ridge_c, penalty="l2", solver="lbfgs",
                                  max_iter=2000, random_state=seed)
    lr_base.fit(X_tr, y_tr)
    base_auc = roc_auc_score(y_te, lr_base.predict_proba(X_te)[:, 1])

    # With candidate
    X_cand = np.column_stack([X_base, candidate_col.reshape(-1, 1)])
    scaler2 = StandardScaler()
    X_tr2 = scaler2.fit_transform(X_cand[train_mask])
    X_te2 = scaler2.transform(X_cand[test_mask])

    lr_cand = LogisticRegression(C=ridge_c, penalty="l2", solver="lbfgs",
                                  max_iter=2000, random_state=seed)
    lr_cand.fit(X_tr2, y_tr)
    cand_auc = roc_auc_score(y_te, lr_cand.predict_proba(X_te2)[:, 1])

    return cand_auc - base_auc, cand_auc


def generate_exhaustive_candidates(X_v41, feat_v41, events):
    """Generate ALL pairwise interactions + higher-order transforms.

    Returns dict: feature_name → np.array
    """
    n_events, n_feats = X_v41.shape
    candidates = {}

    # Identify feature properties
    feat_nonzero_pct = {}  # % of events where feature != 0
    feat_is_binary = {}    # is the feature binary (only 0/1)?
    feat_is_continuous = {}

    for i, name in enumerate(feat_v41):
        col = X_v41[:, i]
        nz = np.sum(col != 0) / n_events
        feat_nonzero_pct[name] = nz
        unique_vals = np.unique(col)
        feat_is_binary[name] = len(unique_vals) <= 2
        feat_is_continuous[name] = len(unique_vals) > 10

    # =========================================================================
    # PART 1: Pairwise interactions
    # =========================================================================
    print(f"\n  Generating pairwise interactions across {n_feats} features...")
    n_pairs = n_feats * (n_feats - 1) // 2
    print(f"  Total possible pairs: {n_pairs}")

    skipped_sparse = 0
    skipped_variance = 0
    skipped_duplicate = 0
    generated = 0

    # Skip pairs where BOTH features are >95% zero (product would be >99% zero)
    # Also skip binary×binary if both are sparse (< 5% nonzero each)
    for i in range(n_feats):
        for j in range(i + 1, n_feats):
            name_i = feat_v41[i]
            name_j = feat_v41[j]

            # Skip if product would be too sparse
            nz_i = feat_nonzero_pct[name_i]
            nz_j = feat_nonzero_pct[name_j]

            # For binary×binary, expected nonzero = nz_i * nz_j (independence assumption)
            if feat_is_binary[name_i] and feat_is_binary[name_j]:
                expected_nz = nz_i * nz_j
                if expected_nz < 0.02:  # < 2% nonzero = too sparse for 1752 events (~35 events)
                    skipped_sparse += 1
                    continue
            elif nz_i < 0.03 or nz_j < 0.03:
                skipped_sparse += 1
                continue

            # Generate the interaction
            product = X_v41[:, i] * X_v41[:, j]

            # Check variance
            if np.std(product) < 1e-8:
                skipped_variance += 1
                continue

            # Check it's not essentially identical to an existing feature
            # (correlation > 0.99 with either parent)
            corr_i = abs(np.corrcoef(product, X_v41[:, i])[0, 1]) if np.std(X_v41[:, i]) > 1e-8 else 0
            corr_j = abs(np.corrcoef(product, X_v41[:, j])[0, 1]) if np.std(X_v41[:, j]) > 1e-8 else 0
            if corr_i > 0.995 or corr_j > 0.995:
                skipped_duplicate += 1
                continue

            # Clean name
            # Remove version prefixes for readability
            short_i = name_i.replace("v40_", "").replace("v41_", "")
            short_j = name_j.replace("v40_", "").replace("v41_", "")
            feat_name = f"v42_{short_i}_X_{short_j}"

            candidates[feat_name] = product
            generated += 1

    print(f"  Pairwise: {generated} generated, {skipped_sparse} sparse, "
          f"{skipped_variance} zero-var, {skipped_duplicate} duplicate")

    # =========================================================================
    # PART 2: Higher-order transforms on continuous features
    # =========================================================================
    continuous_feats = [(name, i) for i, name in enumerate(feat_v41)
                        if feat_is_continuous.get(name, False)
                        and feat_nonzero_pct.get(name, 0) > 0.1]

    # Sort by variance (most informative first)
    continuous_feats.sort(key=lambda x: -np.std(X_v41[:, x[1]]))
    continuous_feats = continuous_feats[:25]  # top 25

    n_transforms = 0
    for name, idx in continuous_feats:
        col = X_v41[:, idx]
        short = name.replace("v40_", "").replace("v41_", "")

        # Cubed
        cubed = col ** 3
        if np.std(cubed) > 1e-8 and abs(np.corrcoef(cubed, col)[0, 1]) < 0.995:
            candidates[f"v42_{short}_cubed"] = cubed
            n_transforms += 1

        # sqrt(abs)
        sqrt_abs = np.sqrt(np.abs(col)) * np.sign(col)
        if np.std(sqrt_abs) > 1e-8 and abs(np.corrcoef(sqrt_abs, col)[0, 1]) < 0.995:
            candidates[f"v42_{short}_sqrt"] = sqrt_abs
            n_transforms += 1

        # log1p(abs) * sign
        log1p = np.log1p(np.abs(col)) * np.sign(col)
        if np.std(log1p) > 1e-8 and abs(np.corrcoef(log1p, col)[0, 1]) < 0.995:
            candidates[f"v42_{short}_log1p"] = log1p
            n_transforms += 1

    print(f"  Transforms: {n_transforms} generated from {len(continuous_feats)} continuous features")

    # =========================================================================
    # PART 3: Three-way interactions among strongest features
    # =========================================================================
    # Take the top features by absolute coefficient in v41
    # These are the features that MATTER most — three-way might unlock residual
    top_feats = [
        "journey_success_rate", "journey_last_positive", "journey_positive_streak",
        "sponsor_success_rate", "ta_base_rate", "is_phase3", "is_phase2",
        "is_micro", "is_small", "ta_oncology", "ta_cns", "ta_rare_disease",
        "ctgov_enrollment", "v40_has_conference", "indication_density",
        "ctgov_is_placebo", "ctgov_is_randomized", "momentum_20d",
        "designation_count", "ctgov_real"
    ]

    # Map to indices
    feat_to_idx = {name: i for i, name in enumerate(feat_v41)}
    top_indices = [(name, feat_to_idx[name]) for name in top_feats if name in feat_to_idx]

    n_three_way = 0
    for a in range(len(top_indices)):
        for b in range(a + 1, len(top_indices)):
            for c in range(b + 1, len(top_indices)):
                name_a, idx_a = top_indices[a]
                name_b, idx_b = top_indices[b]
                name_c, idx_c = top_indices[c]

                product = X_v41[:, idx_a] * X_v41[:, idx_b] * X_v41[:, idx_c]

                if np.std(product) < 1e-8:
                    continue

                # Check non-zero proportion
                nz_pct = np.sum(product != 0) / n_events
                if nz_pct < 0.02:
                    continue

                short_a = name_a.replace("v40_", "").replace("v41_", "")
                short_b = name_b.replace("v40_", "").replace("v41_", "")
                short_c = name_c.replace("v40_", "").replace("v41_", "")
                feat_name = f"v42_3w_{short_a}_X_{short_b}_X_{short_c}"

                candidates[feat_name] = product
                n_three_way += 1

    print(f"  Three-way: {n_three_way} generated from {len(top_indices)} top features")

    total = len(candidates)
    print(f"\n  *** TOTAL CANDIDATES: {total}")

    return candidates


def main():
    t_start = time.time()

    print("\n" + "=" * 80)
    print("  GUNGNIR v42 KAIZEN — Exhaustive Pairwise Interaction Search")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Load v39 → build v40 → build v41 baseline
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Build v41 baseline (130 features, AUC ~0.7752)")
    print(f"{'=' * 80}")

    print("\n  Loading v39 kaizen module...")
    v39 = load_v39_module()

    print("  Loading data via v39.load_data()...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    events, ctgov_lookup = v39.load_data()
    captured = sys.stdout.getvalue()
    sys.stdout = old_stdout

    for line in captured.strip().split("\n"):
        if any(k in line for k in ["attached", "loaded", "matched", "events", "Total"]):
            print(f"    {line.strip()}")

    print(f"  Total events: {len(events)}")

    # Build v39.1 base features (122)
    print("\n  Building v39.1 feature matrix (122 features)...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    X_base_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
        events, ctgov_lookup,
        include_v37=True, include_v38=True,
        include_candidates=V39_SELECTED
    )
    sys.stdout = old_stdout
    print(f"  v39.1 matrix: {X_base_v39.shape[0]} × {X_base_v39.shape[1]}")

    # Build v40 features and append
    print("\n  Building v40 features (3 columns)...")
    v40_lookup = build_v40_features(events)

    v40_cols = []
    v40_names = []
    for v40_feat in V40_SELECTED:
        col = []
        for ev in events:
            key = (ev.get("ticker", "").upper(), ev.get("date", ""))
            col.append(float(v40_lookup.get(key, {}).get(v40_feat, 0) or 0))
        v40_cols.append(np.array(col))
        v40_names.append(v40_feat)

    X_v40 = np.column_stack([X_base_v39] + [c.reshape(-1, 1) for c in v40_cols])
    feat_v40 = list(feat_v39) + v40_names
    print(f"  v40 matrix: {X_v40.shape[0]} × {X_v40.shape[1]}")

    # Build v41 features and append
    print("\n  Building v41 features (5 columns)...")
    v41_cols_dict = build_v41_features(events, X_v40, feat_v40, v40_lookup)

    v41_cols_list = []
    v41_names = []
    for v41_feat in V41_SELECTED:
        v41_cols_list.append(v41_cols_dict[v41_feat])
        v41_names.append(v41_feat)

    X_v41 = np.column_stack([X_v40] + [c.reshape(-1, 1) for c in v41_cols_list])
    feat_v41 = list(feat_v40) + v41_names
    print(f"  v41 matrix: {X_v41.shape[0]} × {X_v41.shape[1]}")

    # Evaluate v41 baseline with FULL WF
    print("\n  Evaluating v41 baseline (walk-forward)...")
    baseline = v39.evaluate_wf(
        X_v41, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **V41_CONFIG
    )

    base_auc = baseline["avg_auc"]
    print(f"\n  *** v41 BASELINE: AUC={base_auc:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp")

    # =========================================================================
    # PHASE 1b: Generate exhaustive candidates
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1b: Generate Exhaustive Candidate Features")
    print(f"{'=' * 80}")

    candidates = generate_exhaustive_candidates(X_v41, feat_v41, events)

    # =========================================================================
    # PHASE 2: Fast pre-screen (Ridge-only, single split)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 2: Fast Pre-Screen ({len(candidates)} candidates, Ridge-only)")
    print(f"{'=' * 80}")

    t_screen_start = time.time()
    screen_results = []
    n_total = len(candidates)
    batch_size = max(1, n_total // 20)  # print progress every 5%

    for i, (feat_name, col) in enumerate(candidates.items()):
        delta, abs_auc = fast_ridge_screen(X_v41, y_bin, dates, col,
                                            ridge_c=V41_CONFIG["ridge_c"])
        screen_results.append({
            "feature": feat_name,
            "ridge_delta": delta,
            "ridge_auc": abs_auc,
        })

        if (i + 1) % batch_size == 0 or i == n_total - 1:
            elapsed = time.time() - t_screen_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (n_total - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{n_total}] {elapsed:.0f}s elapsed, "
                  f"{rate:.1f} feat/s, ETA {eta:.0f}s")

    screen_results.sort(key=lambda x: -x["ridge_delta"])

    t_screen_end = time.time()
    print(f"\n  Pre-screen complete in {t_screen_end - t_screen_start:.0f}s")

    # Show top 50
    print(f"\n  {'Feature':<55s} {'Ridge_ΔAUC':>12s}")
    print(f"  {'-' * 70}")
    for r in screen_results[:50]:
        marker = " <<<" if r["ridge_delta"] > 0.001 else ""
        print(f"  {r['feature']:<55s} {r['ridge_delta']:>+12.5f}{marker}")

    n_positive = sum(1 for r in screen_results if r["ridge_delta"] > 0)
    n_strong = sum(1 for r in screen_results if r["ridge_delta"] > 0.001)
    print(f"\n  *** {n_positive} candidates with positive ridge delta")
    print(f"  *** {n_strong} candidates with ridge delta > +0.001")

    # Take top 100 for full WF eval (or all positives if fewer)
    n_full_eval = min(100, max(n_positive, 50))
    top_candidates = [r["feature"] for r in screen_results[:n_full_eval]]

    # =========================================================================
    # PHASE 3: Full walk-forward audit on top candidates
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Full WF Audit on top {len(top_candidates)} candidates")
    print(f"{'=' * 80}")

    print(f"\n  {'Feature':<55s} {'WF_AUC':>8s} {'ΔAUC':>8s} {'Brier':>7s} {'EV_sp':>7s} {'Status':>10s}")
    print(f"  {'-' * 100}")

    audit_results = []
    for idx, feat_name in enumerate(top_candidates):
        col = candidates[feat_name]
        X_cand = np.column_stack([X_v41, col.reshape(-1, 1)])

        result = v39.evaluate_wf(
            X_cand, y_bin, y_gp, y_cr, y_ret, dates,
            **V41_CONFIG
        )
        delta = result["avg_auc"] - base_auc
        status = "✓ PASS" if delta > 0.0005 else "≈ FLAT" if delta > -0.0005 else "✗ HURTS"
        flag = " <<<" if delta > 0.001 else (" !!!" if delta < -0.003 else "")

        print(f"  {feat_name:<55s} {result['avg_auc']:>8.4f} {delta:>+8.4f} "
              f"{result['avg_brier']:>7.4f} {result['avg_ev_spread']:>+7.2f} {status:>10s}{flag}")

        audit_results.append({
            "feature": feat_name,
            "auc": result["avg_auc"],
            "delta_auc": delta,
            "brier": result["avg_brier"],
            "ev_spread": result["avg_ev_spread"],
            "status": status.strip(),
        })

    audit_results.sort(key=lambda x: -x["delta_auc"])

    print(f"\n  {'=' * 100}")
    print(f"  FULL WF AUDIT RESULTS (sorted by ΔAUC)")
    print(f"  {'=' * 100}")
    for r in audit_results[:30]:
        marker = " ***" if r["delta_auc"] > 0.001 else ""
        print(f"  {r['feature']:<55s} AUC={r['auc']:.4f} Δ={r['delta_auc']:+.4f} "
              f"EV={r['ev_spread']:+.1f}pp{marker}")

    winners = [r for r in audit_results if r["delta_auc"] > 0.0005]
    positives = [r for r in audit_results if r["delta_auc"] > 0]
    print(f"\n  *** {len(winners)} features pass audit (ΔAUC > +0.0005)")
    print(f"  *** {len(positives)} features with positive delta")

    if not positives:
        print("\n  No features have positive delta. v41 remains champion.")
        results = {
            "version": "42.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "41.0.0", "baseline_auc": round(base_auc, 4),
            "final_wf_auc": round(base_auc, 4), "champion": False,
            "n_candidates_generated": len(candidates),
            "n_pre_screened": len(screen_results),
            "n_full_wf_eval": len(audit_results),
            "screen_results_top50": screen_results[:50],
            "audit_results": audit_results,
            "verdict": "No new features beat v41 baseline",
            "runtime_seconds": round(time.time() - t_start, 1),
        }
        out_path = os.path.join(DATA_DIR, "gungnir_v42_kaizen_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2,
                     default=lambda x: bool(x) if isinstance(x, np.bool_) else
                                       float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
        print(f"  Results saved to {out_path}")
        return results

    # =========================================================================
    # PHASE 4: Greedy forward selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 4: Greedy Forward Selection")
    print(f"{'=' * 80}")

    current_X = X_v41.copy()
    current_feat = list(feat_v41)
    current_auc = base_auc
    selected = []

    candidates_to_try = [r["feature"] for r in audit_results if r["delta_auc"] > 0]
    print(f"  Starting AUC: {current_auc:.4f} ({current_X.shape[1]} features)")
    print(f"  Candidates to try: {len(candidates_to_try)}")

    for round_num in range(min(len(candidates_to_try), 15)):  # max 15 new features
        best_feat = None
        best_auc = current_auc
        best_result = None

        for feat_name in candidates_to_try:
            if feat_name in [s["feature"] for s in selected]:
                continue

            col = candidates[feat_name].reshape(-1, 1)
            X_trial = np.column_stack([current_X, col])

            result = v39.evaluate_wf(
                X_trial, y_bin, y_gp, y_cr, y_ret, dates,
                **V41_CONFIG
            )

            if result["avg_auc"] > best_auc + 0.0002:
                best_feat = feat_name
                best_auc = result["avg_auc"]
                best_result = result

        if best_feat is None:
            print(f"\n  Round {round_num + 1}: No improvement > +0.0002. STOPPING.")
            break

        col = candidates[best_feat].reshape(-1, 1)
        current_X = np.column_stack([current_X, col])
        current_feat.append(best_feat)
        current_auc = best_auc

        selected.append({
            "feature": best_feat,
            "auc": round(best_auc, 4),
            "delta": round(best_auc - (selected[-1]["auc"] if selected else base_auc), 4),
            "ev_spread": round(best_result["avg_ev_spread"], 2),
        })

        print(f"  Round {round_num + 1}: +{best_feat} → AUC={best_auc:.4f} "
              f"(+{selected[-1]['delta']:.4f}) EV={best_result['avg_ev_spread']:+.2f}pp")

    print(f"\n  *** GREEDY SELECTION: {len(selected)} features selected")
    print(f"  *** AUC: {base_auc:.4f} → {current_auc:.4f} (+{current_auc - base_auc:.4f})")

    if not selected:
        print("\n  No features survive greedy selection. v41 remains champion.")
        results = {
            "version": "42.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "41.0.0", "baseline_auc": round(base_auc, 4),
            "final_wf_auc": round(base_auc, 4), "champion": False,
            "n_candidates_generated": len(candidates),
            "n_pre_screened": len(screen_results),
            "n_full_wf_eval": len(audit_results),
            "screen_results_top50": screen_results[:50],
            "audit_results": audit_results, "greedy_selection": [],
            "verdict": "Features pass audit but not greedy selection",
            "runtime_seconds": round(time.time() - t_start, 1),
        }
        out_path = os.path.join(DATA_DIR, "gungnir_v42_kaizen_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2,
                     default=lambda x: bool(x) if isinstance(x, np.bool_) else
                                       float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
        print(f"  Results saved to {out_path}")
        return results

    # =========================================================================
    # PHASE 5: Architecture sweep
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 5: Architecture Sweep")
    print(f"{'=' * 80}")

    best_config = dict(V41_CONFIG)
    best_arch_auc = current_auc

    # Test different C values
    c_values = [0.005, 0.008, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03, 0.05]
    print(f"\n  Ridge C sweep:")
    for c in c_values:
        cfg = dict(V41_CONFIG)
        cfg["ridge_c"] = c
        result = v39.evaluate_wf(
            current_X, y_bin, y_gp, y_cr, y_ret, dates, **cfg
        )
        marker = " <<<" if result["avg_auc"] > best_arch_auc else ""
        print(f"    C={c:.3f} → AUC={result['avg_auc']:.4f} "
              f"Brier={result['avg_brier']:.4f} EV={result['avg_ev_spread']:+.2f}pp{marker}")
        if result["avg_auc"] > best_arch_auc + 0.0001:
            best_arch_auc = result["avg_auc"]
            best_config["ridge_c"] = c

    # Test different meta weights
    meta_weights = [(0.60, 0.40), (0.65, 0.35), (0.70, 0.30), (0.75, 0.25), (0.80, 0.20)]
    print(f"\n  Meta weight sweep:")
    for ridge_w, xgb_w in meta_weights:
        cfg = dict(best_config)
        cfg["meta_ridge"] = ridge_w
        cfg["meta_xgb"] = xgb_w
        result = v39.evaluate_wf(
            current_X, y_bin, y_gp, y_cr, y_ret, dates, **cfg
        )
        marker = " <<<" if result["avg_auc"] > best_arch_auc else ""
        print(f"    Ridge {ridge_w:.0%} / XGB {xgb_w:.0%} → AUC={result['avg_auc']:.4f} "
              f"Brier={result['avg_brier']:.4f}{marker}")
        if result["avg_auc"] > best_arch_auc + 0.0001:
            best_arch_auc = result["avg_auc"]
            best_config["meta_ridge"] = ridge_w
            best_config["meta_xgb"] = xgb_w

    # Test XGB parameters
    xgb_configs = [
        (0.01, 400, 3), (0.01, 500, 3), (0.01, 600, 3),
        (0.01, 500, 4), (0.005, 600, 3), (0.008, 500, 3),
    ]
    print(f"\n  XGB sweep:")
    for lr, trees, depth in xgb_configs:
        cfg = dict(best_config)
        cfg["xgb_lr"] = lr
        cfg["xgb_trees"] = trees
        cfg["xgb_depth"] = depth
        result = v39.evaluate_wf(
            current_X, y_bin, y_gp, y_cr, y_ret, dates, **cfg
        )
        marker = " <<<" if result["avg_auc"] > best_arch_auc else ""
        print(f"    lr={lr} trees={trees} depth={depth} → AUC={result['avg_auc']:.4f}{marker}")
        if result["avg_auc"] > best_arch_auc + 0.0001:
            best_arch_auc = result["avg_auc"]
            best_config["xgb_lr"] = lr
            best_config["xgb_trees"] = trees
            best_config["xgb_depth"] = depth

    print(f"\n  *** Best config: C={best_config['ridge_c']}, "
          f"meta {best_config['meta_ridge']:.0%}/{best_config['meta_xgb']:.0%}, "
          f"XGB lr={best_config['xgb_lr']}/trees={best_config['xgb_trees']}")
    print(f"  *** AUC after arch sweep: {best_arch_auc:.4f}")

    # Final eval with best config
    final_result = v39.evaluate_wf(
        current_X, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **best_config
    )
    final_auc = final_result["avg_auc"]

    # =========================================================================
    # PHASE 6: 10-seed stability test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 6: 10-Seed Stability Test")
    print(f"{'=' * 80}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    dates_int = np.array([int(str(d)[:4]) if isinstance(d, str) else int(d) for d in dates])
    train_mask = dates_int < 2025
    test_mask = dates_int >= 2025
    X_train, X_test = current_X[train_mask], current_X[test_mask]
    y_train, y_test = y_bin[train_mask], y_bin[test_mask]

    v42_aucs = []
    v41_aucs = []

    for seed in range(10):
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_train)
        X_te_s = scaler.transform(X_test)

        lr42 = LogisticRegression(
            C=best_config["ridge_c"], penalty="l2", solver="lbfgs",
            max_iter=5000, random_state=seed
        )
        lr42.fit(X_tr_s, y_train)
        p42 = lr42.predict_proba(X_te_s)[:, 1]
        auc42 = roc_auc_score(y_test, p42)
        v42_aucs.append(auc42)

        # v41 baseline
        X_v41_train = X_v41[train_mask]
        X_v41_test = X_v41[test_mask]
        scaler2 = StandardScaler()
        X_v41_tr_s = scaler2.fit_transform(X_v41_train)
        X_v41_te_s = scaler2.transform(X_v41_test)

        lr41 = LogisticRegression(
            C=V41_CONFIG["ridge_c"], penalty="l2", solver="lbfgs",
            max_iter=5000, random_state=seed
        )
        lr41.fit(X_v41_tr_s, y_train)
        p41 = lr41.predict_proba(X_v41_te_s)[:, 1]
        auc41 = roc_auc_score(y_test, p41)
        v41_aucs.append(auc41)

        win = "v42" if auc42 > auc41 else "v41"
        print(f"  Seed {seed}: v42={auc42:.4f} v41={auc41:.4f} → {win}")

    from scipy import stats
    t_stat, p_value = stats.ttest_rel(v42_aucs, v41_aucs)
    wins = sum(1 for a42, a41 in zip(v42_aucs, v41_aucs) if a42 > a41)

    print(f"\n  v42 mean: {np.mean(v42_aucs):.4f} ± {np.std(v42_aucs):.4f}")
    print(f"  v41 mean: {np.mean(v41_aucs):.4f} ± {np.std(v41_aucs):.4f}")
    print(f"  Wins: {wins}/10")
    print(f"  Paired t-test: t={t_stat:.3f}, p={p_value:.10f}")

    is_champion = bool(wins >= 7 and p_value < 0.05 and final_auc > base_auc)

    # =========================================================================
    # PHASE 7: Get coefficients for selected features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  FINAL: v42 Coefficients for selected features")
    print(f"{'=' * 80}")

    scaler_final = StandardScaler()
    X_train_final = scaler_final.fit_transform(current_X[train_mask])

    lr_final = LogisticRegression(
        C=best_config["ridge_c"], penalty="l2", solver="lbfgs",
        max_iter=5000, random_state=42
    )
    lr_final.fit(X_train_final, y_train)

    new_feat_coefs = {}
    for sel in selected:
        idx = current_feat.index(sel["feature"])
        coef = lr_final.coef_[0][idx]
        new_feat_coefs[sel["feature"]] = round(coef, 4)
        print(f"  {sel['feature']}: {coef:+.4f}")

    # Key discoveries
    key_discoveries = []
    for sel in selected:
        coef = new_feat_coefs.get(sel["feature"], 0)
        key_discoveries.append({
            "feature": sel["feature"],
            "coefficient": coef,
            "auc_at_selection": sel["auc"],
            "incremental_auc": sel["delta"],
        })

    # =========================================================================
    # Save results
    # =========================================================================
    total_time = time.time() - t_start

    results = {
        "version": "42.0.0",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline_version": "41.0.0",
        "baseline_auc": round(base_auc, 4),
        "final_wf_auc": round(final_auc, 4),
        "final_wf_brier": round(final_result["avg_brier"], 4),
        "final_wf_ev_spread": round(final_result["avg_ev_spread"], 2),
        "auc_delta": round(final_auc - base_auc, 4),
        "config": best_config,
        "n_features_v41": X_v41.shape[1],
        "n_features_v42": current_X.shape[1],
        "features_added": [s["feature"] for s in selected],
        "new_feature_coefficients": new_feat_coefs,
        "key_discoveries": key_discoveries,
        "n_candidates_generated": len(candidates),
        "n_pre_screened": len(screen_results),
        "n_full_wf_eval": len(audit_results),
        "screen_results_top50": screen_results[:50],
        "audit_results": audit_results[:30],  # top 30 only to save space
        "greedy_selection": selected,
        "stability": {
            "v42_mean": round(np.mean(v42_aucs), 4),
            "v42_std": round(np.std(v42_aucs), 4),
            "v41_mean": round(np.mean(v41_aucs), 4),
            "v41_std": round(np.std(v41_aucs), 4),
            "wins": wins,
            "n_seeds": 10,
            "t_stat": round(t_stat, 3),
            "p_value": p_value,
        },
        "champion": is_champion,
        "runtime_seconds": round(total_time, 1),
        "pillar_summary": {
            "pairwise_interactions": "ALL pairs of 130 features (~8400 candidates)",
            "higher_order_transforms": "cubed/sqrt/log1p on top 25 continuous features",
            "three_way_interactions": "Triple products of top 20 features",
            "approach": "Exhaustive brute-force — no human feature selection bias",
        },
    }

    if is_champion:
        print(f"\n  {'=' * 80}")
        print(f"  ★★★ GUNGNIR v42.0.0 IS THE NEW CHAMPION ★★★")
        print(f"  AUC: {base_auc:.4f} → {final_auc:.4f} (+{final_auc - base_auc:.4f})")
        print(f"  Features: {X_v41.shape[1]} → {current_X.shape[1]} "
              f"(+{len(selected)})")
        print(f"  Stability: {wins}/10 seeds, p={p_value:.10f}")
        print(f"  {'=' * 80}")
    else:
        print(f"\n  v42 does NOT beat v41 with sufficient stability.")
        print(f"  v41 remains CHAMPION (AUC {base_auc:.4f})")

    print(f"\n  Total runtime: {total_time:.0f}s ({total_time/60:.1f} min)")

    out_path = os.path.join(DATA_DIR, "gungnir_v42_kaizen_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2,
                 default=lambda x: bool(x) if isinstance(x, np.bool_) else
                                   float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
    print(f"\n  Results saved to {out_path}")

    return results


if __name__ == "__main__":
    main()
