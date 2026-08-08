#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v41 KAIZEN — Non-Linear + Journey Interactions + Sponsor Depth + TA×Phase
================================================================================

APPROACH:
  Start from v40.0.0 as baseline (AUC 0.7678, 125 features)

  v40 FINDINGS (what worked / what failed):
    WORKED: has_conference (+0.0061), days_to_cover (+0.0005), conf_x_small (+0.0012)
    FAILED: ALL SI/float features, ALL price features, conf_x_micro, conf_x_phase3

  v41 STRATEGY: Mine signal from EXISTING features via non-linear transforms and
  interaction terms. The strongest Gungnir feature families are:
    - Journey features (coefs: +0.274, +0.250, +0.188, -0.182)
    - Phase granularity (coefs: +0.162, +0.138, -0.137, +0.113)
    - TA features (coefs: +0.120, -0.117)
    - Sponsor features (coef: +0.105)
    - Trial design (coefs: -0.159, -0.114, -0.096)

  NEW FEATURE VECTORS (6 pillars, ~35 candidates):

  P1. NON-LINEAR TRANSFORMS — squared versions of top features
    - journey_success_rate_sq: non-linear journey success
    - sponsor_success_rate_sq: non-linear sponsor success
    - ta_base_rate_sq: non-linear TA base rate
    - journey_last_positive_sq: non-linear last positive
    - journey_streak_sq: non-linear streak
    - momentum_20d_sq: non-linear momentum
    - indication_density_cubed: non-linear competitive pressure

  P2. JOURNEY × INTERACTIONS — strongest family crossed with size/phase/TA
    - journey_sr_x_phase3: experienced journey + late stage
    - journey_sr_x_micro: journey success in tiny companies
    - journey_sr_x_onc: journey success in oncology
    - journey_streak_x_phase3: winning streak in pivotal
    - journey_neg_x_micro: negative history in small caps
    - journey_last_pos_x_small: recent positive + small cap
    - journey_sr_x_bridging: journey success + bridging design
    - journey_sr_x_conference: journey success + conference

  P3. SPONSOR DEPTH — sponsor interactions
    - sponsor_sr_x_phase3: strong sponsor + pivotal stage
    - sponsor_sr_x_micro: strong sponsor + micro cap
    - sponsor_sr_x_onc: strong sponsor + oncology
    - sponsor_sr_cubed: non-linear sponsor (like ODIN's swr_cubed)
    - sponsor_x_journey: sponsor × journey double strength

  P4. TA × PHASE GRANULARITY — phase-specific TA effects
    - onc_x_phase2: oncology Phase 2 (hypothesis: different from Phase 3)
    - cns_x_phase2: CNS Phase 2
    - rare_x_phase2: rare disease Phase 2
    - onc_x_phase1: oncology Phase 1 (early signal)
    - cns_x_bridging: CNS bridging designs
    - heme_x_phase3: hematology Phase 3

  P5. TRIAL DESIGN INTERACTIONS — CT.gov × journey/sponsor/size
    - enrollment_x_journey_sr: big trial + positive journey
    - randomized_x_phase2: RCT in Phase 2
    - masking_x_onc: blinding rigor × oncology
    - dmc_x_journey: DMC × journey success
    - industry_x_micro: industry-sponsored micro-cap
    - rigorous_x_small: rigorous design × small cap
    - placebo_x_cns: placebo-controlled CNS

  T-1 COMPLIANCE: All features derived from pre-readout public information.

STRATEGY:
  - Load v40 pipeline (which loads v39 → training data)
  - Build v40 baseline with 125 features
  - Append ~35 v41 candidate features
  - Phase 2: Deep column audit (each independently)
  - Phase 3: Greedy forward selection
  - Phase 4: Architecture sweep (C, meta weights, LightGBM)
  - Phase 5: 10-seed stability test
"""

import csv, json, math, os, re, sys, warnings, io
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()

# v40 config (from v40 kaizen results)
V40_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# v40 selected features (from v40 kaizen results — added on top of v39.1)
V40_SELECTED = ["v40_has_conference", "v40_days_to_cover", "v40_conf_x_small"]

# v39 selected features (from v39 kaizen results)
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
    """Extract conference signal from text."""
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
    """Import v39 kaizen module via importlib."""
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
    """Build v40's 3 selected features for all events."""
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


def engineer_v41_candidates(events, X_base, feat_names, v40_lookup):
    """Engineer v41 candidate features.

    Returns dict mapping feature_name → np.array of values (aligned with events).
    """
    n = len(events)
    candidates = {}

    # Build lookup: feature_name → column index in X_base
    feat_idx = {name: i for i, name in enumerate(feat_names)}

    def get_col(name):
        """Get column from base feature matrix by name."""
        idx = feat_idx.get(name)
        if idx is not None:
            return X_base[:, idx]
        return np.zeros(n)

    # Helper to get v40 features
    def get_v40_col(v40_name):
        vals = []
        for ev in events:
            key = (ev.get("ticker", "").upper(), ev.get("date", ""))
            vals.append(float(v40_lookup.get(key, {}).get(v40_name, 0) or 0))
        return np.array(vals)

    # Extract base columns we'll reuse
    journey_sr = get_col("journey_success_rate")
    journey_last_pos = get_col("journey_last_positive")
    journey_streak = get_col("journey_positive_streak")
    journey_neg = get_col("journey_had_negative")
    journey_pos = get_col("journey_had_positive")
    sponsor_sr = get_col("sponsor_success_rate")
    ta_base = get_col("ta_base_rate")
    momentum_20d = get_col("momentum_20d")
    ind_density = get_col("indication_density")
    is_phase3 = get_col("is_phase3")
    is_phase2 = get_col("is_phase2")
    is_phase2a = get_col("is_phase2a")
    is_phase2b = get_col("is_phase2b")
    is_phase1 = get_col("is_phase1")
    is_phase1b = get_col("is_phase1b")
    is_bridging = get_col("is_bridging")
    is_micro = get_col("is_micro")
    is_small = get_col("is_small")
    is_mid = get_col("is_mid")
    ta_onc = get_col("ta_oncology")
    ta_cns = get_col("ta_cns")
    ta_rare = get_col("ta_rare_disease")
    ta_heme = get_col("ta_hematology")
    ta_immuno = get_col("ta_immunology")
    ctgov_enrollment = get_col("ctgov_enrollment")
    ctgov_randomized = get_col("ctgov_is_randomized")
    ctgov_masking = get_col("ctgov_masking_rigor")
    ctgov_dmc = get_col("ctgov_has_dmc")
    ctgov_industry = get_col("ct_is_industry")
    ctgov_placebo = get_col("ctgov_is_placebo")
    ctgov_real = get_col("ctgov_real")
    v40_has_conf = get_v40_col("v40_has_conference")

    # =========================================================================
    # PILLAR 1: Non-linear transforms
    # =========================================================================
    candidates["v41_journey_sr_sq"] = journey_sr ** 2
    candidates["v41_sponsor_sr_sq"] = sponsor_sr ** 2
    candidates["v41_ta_base_sq"] = ta_base ** 2
    candidates["v41_journey_last_pos_sq"] = journey_last_pos ** 2
    candidates["v41_journey_streak_sq"] = journey_streak ** 2
    candidates["v41_momentum_20d_sq"] = momentum_20d ** 2
    candidates["v41_ind_density_cubed"] = ind_density ** 3
    candidates["v41_sponsor_sr_cubed"] = sponsor_sr ** 3

    # =========================================================================
    # PILLAR 2: Journey × Interactions
    # =========================================================================
    candidates["v41_journey_sr_x_phase3"] = journey_sr * is_phase3
    candidates["v41_journey_sr_x_micro"] = journey_sr * is_micro
    candidates["v41_journey_sr_x_onc"] = journey_sr * ta_onc
    candidates["v41_journey_streak_x_phase3"] = journey_streak * is_phase3
    candidates["v41_journey_neg_x_micro"] = journey_neg * is_micro
    candidates["v41_journey_last_pos_x_small"] = journey_last_pos * is_small
    candidates["v41_journey_sr_x_bridging"] = journey_sr * is_bridging
    candidates["v41_journey_sr_x_conference"] = journey_sr * v40_has_conf
    candidates["v41_journey_pos_x_onc"] = journey_pos * ta_onc
    candidates["v41_journey_sr_x_cns"] = journey_sr * ta_cns

    # =========================================================================
    # PILLAR 3: Sponsor depth
    # =========================================================================
    candidates["v41_sponsor_sr_x_phase3"] = sponsor_sr * is_phase3
    candidates["v41_sponsor_sr_x_micro"] = sponsor_sr * is_micro
    candidates["v41_sponsor_sr_x_onc"] = sponsor_sr * ta_onc
    candidates["v41_sponsor_x_journey"] = sponsor_sr * journey_sr
    candidates["v41_sponsor_x_conference"] = sponsor_sr * v40_has_conf

    # =========================================================================
    # PILLAR 4: TA × Phase granularity
    # =========================================================================
    candidates["v41_onc_x_phase2"] = ta_onc * is_phase2
    candidates["v41_cns_x_phase2"] = ta_cns * is_phase2
    candidates["v41_rare_x_phase2"] = ta_rare * is_phase2
    candidates["v41_onc_x_phase1"] = ta_onc * is_phase1
    candidates["v41_cns_x_bridging"] = ta_cns * is_bridging
    candidates["v41_heme_x_phase3"] = ta_heme * is_phase3
    candidates["v41_immuno_x_phase2"] = ta_immuno * is_phase2
    candidates["v41_rare_x_phase1b"] = ta_rare * is_phase1b

    # =========================================================================
    # PILLAR 5: Trial design interactions
    # =========================================================================
    candidates["v41_enrollment_x_journey"] = ctgov_enrollment * journey_sr
    candidates["v41_randomized_x_phase2"] = ctgov_randomized * is_phase2
    candidates["v41_masking_x_onc"] = ctgov_masking * ta_onc
    candidates["v41_dmc_x_journey"] = ctgov_dmc * journey_sr
    candidates["v41_industry_x_micro"] = ctgov_industry * is_micro
    candidates["v41_placebo_x_cns"] = ctgov_placebo * ta_cns
    candidates["v41_real_x_micro"] = ctgov_real * is_micro

    # Filter out zero-variance
    valid = {}
    for name, col in candidates.items():
        if np.std(col) > 1e-10:
            valid[name] = col
        else:
            print(f"  [SKIP] {name}: zero variance")

    return valid


def main():
    print("\n" + "=" * 80)
    print("  GUNGNIR v41 KAIZEN — Non-Linear + Journey×Interactions + Sponsor + TA×Phase")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Load v39 → build v40 baseline
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Load v40 baseline (125 features, AUC ~0.7678)")
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

    # Evaluate v40 baseline
    print("\n  Evaluating v40 baseline (walk-forward)...")
    baseline = v39.evaluate_wf(
        X_v40, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **V40_CONFIG
    )

    base_auc = baseline["avg_auc"]
    print(f"\n  *** v40 BASELINE: AUC={base_auc:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp")
    print(f"  (v40 reported: AUC 0.7678)")

    # =========================================================================
    # PHASE 1b: Engineer v41 candidate features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1b: Engineer v41 candidate features (6 pillars)")
    print(f"{'=' * 80}")

    candidates = engineer_v41_candidates(events, X_v40, feat_v40, v40_lookup)
    print(f"\n  Total valid candidates: {len(candidates)}")

    # =========================================================================
    # PHASE 2: Deep column audit — test each candidate independently
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 2: Deep Column Audit — test each v41 candidate vs v40 baseline")
    print(f"{'=' * 80}")

    print(f"\n  {'Feature':<35s} {'WF_AUC':>8s} {'ΔAUC':>8s} {'Brier':>7s} {'EV_sp':>7s} {'Status':>10s}")
    print(f"  {'-' * 80}")

    audit_results = []
    for feat_name in sorted(candidates.keys()):
        col = candidates[feat_name]

        X_cand = np.column_stack([X_v40, col.reshape(-1, 1)])

        result = v39.evaluate_wf(
            X_cand, y_bin, y_gp, y_cr, y_ret, dates,
            **V40_CONFIG
        )
        delta = result["avg_auc"] - base_auc

        status = "✓ PASS" if delta > 0.0005 else "≈ FLAT" if delta > -0.0005 else "✗ HURTS"
        flag = " <<<" if delta > 0.001 else (" !!!" if delta < -0.003 else "")

        print(f"  {feat_name:<35s} {result['avg_auc']:>8.4f} {delta:>+8.4f} "
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

    print(f"\n  {'=' * 80}")
    print(f"  AUDIT RESULTS (sorted by ΔAUC)")
    print(f"  {'=' * 80}")
    for r in audit_results:
        marker = " ***" if r["delta_auc"] > 0.001 else ""
        print(f"  {r['feature']:<35s} AUC={r['auc']:.4f} Δ={r['delta_auc']:+.4f} "
              f"EV={r['ev_spread']:+.1f}pp{marker}")

    winners = [r for r in audit_results if r["delta_auc"] > 0.0005]
    positives = [r for r in audit_results if r["delta_auc"] > 0]
    print(f"\n  *** {len(winners)} features pass audit (ΔAUC > +0.0005)")
    print(f"  *** {len(positives)} features with positive delta")

    if not positives:
        print("\n  No features have positive delta. v40 remains champion.")
        results = {
            "version": "41.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "40.0.0", "baseline_auc": round(base_auc, 4),
            "final_wf_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results,
            "verdict": "No new features beat v40 baseline",
        }
        out_path = os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to {out_path}")
        return results

    # =========================================================================
    # PHASE 3: Greedy forward selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Greedy Forward Selection")
    print(f"{'=' * 80}")

    current_X = X_v40.copy()
    current_feat = list(feat_v40)
    current_auc = base_auc
    selected = []

    candidates_to_try = [r["feature"] for r in audit_results if r["delta_auc"] > 0]
    print(f"  Starting AUC: {current_auc:.4f} ({current_X.shape[1]} features)")
    print(f"  Candidates to try: {len(candidates_to_try)}")

    for round_num in range(len(candidates_to_try)):
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
                **V40_CONFIG
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
        print("\n  No features survive greedy selection. v40 remains champion.")
        results = {
            "version": "41.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "40.0.0", "baseline_auc": round(base_auc, 4),
            "final_wf_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results, "greedy_selection": [],
            "verdict": "Features pass audit but not greedy selection",
        }
        out_path = os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to {out_path}")
        return results

    # =========================================================================
    # PHASE 4: Architecture sweep
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 4: Architecture Sweep")
    print(f"{'=' * 80}")

    best_config = dict(V40_CONFIG)
    best_arch_auc = current_auc

    # Test different C values
    c_values = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.05]
    print(f"\n  Ridge C sweep:")
    for c in c_values:
        cfg = dict(V40_CONFIG)
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
        (0.01, 300, 3), (0.01, 400, 3), (0.01, 500, 3),
        (0.01, 400, 4), (0.005, 500, 3),
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
    # PHASE 5: 10-seed stability test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 5: 10-Seed Stability Test")
    print(f"{'=' * 80}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    # Walk-forward split — dates may be strings or ints
    dates_int = np.array([int(str(d)[:4]) if isinstance(d, str) else int(d) for d in dates])
    train_mask = dates_int < 2025
    test_mask = dates_int >= 2025
    X_train, X_test = current_X[train_mask], current_X[test_mask]
    y_train, y_test = y_bin[train_mask], y_bin[test_mask]

    v41_aucs = []
    v40_aucs = []

    for seed in range(10):
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_train)
        X_te_s = scaler.transform(X_test)

        # v41
        lr41 = LogisticRegression(
            C=best_config["ridge_c"], penalty="l2", solver="lbfgs",
            max_iter=5000, random_state=seed
        )
        lr41.fit(X_tr_s, y_train)
        p41 = lr41.predict_proba(X_te_s)[:, 1]
        auc41 = roc_auc_score(y_test, p41)
        v41_aucs.append(auc41)

        # v40 baseline
        X_v40_train = X_v40[train_mask]
        X_v40_test = X_v40[test_mask]
        X_v40_tr_s = scaler.fit_transform(X_v40_train)
        X_v40_te_s = scaler.transform(X_v40_test)

        lr40 = LogisticRegression(
            C=V40_CONFIG["ridge_c"], penalty="l2", solver="lbfgs",
            max_iter=5000, random_state=seed
        )
        lr40.fit(X_v40_tr_s, y_train)
        p40 = lr40.predict_proba(X_v40_te_s)[:, 1]
        auc40 = roc_auc_score(y_test, p40)
        v40_aucs.append(auc40)

        win = "v41" if auc41 > auc40 else "v40"
        print(f"  Seed {seed}: v41={auc41:.4f} v40={auc40:.4f} → {win}")

    from scipy import stats
    t_stat, p_value = stats.ttest_rel(v41_aucs, v40_aucs)
    wins = sum(1 for a41, a40 in zip(v41_aucs, v40_aucs) if a41 > a40)

    print(f"\n  v41 mean: {np.mean(v41_aucs):.4f} ± {np.std(v41_aucs):.4f}")
    print(f"  v40 mean: {np.mean(v40_aucs):.4f} ± {np.std(v40_aucs):.4f}")
    print(f"  Wins: {wins}/10")
    print(f"  Paired t-test: t={t_stat:.3f}, p={p_value:.10f}")

    is_champion = bool(wins >= 7 and p_value < 0.05 and final_auc > base_auc)

    # =========================================================================
    # PHASE 6: Get coefficients for selected features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  FINAL: v41 Coefficients for selected features")
    print(f"{'=' * 80}")

    scaler_final = StandardScaler()
    X_all_s = scaler_final.fit_transform(current_X)

    # Get train split for coefficient extraction
    lr_final = LogisticRegression(
        C=best_config["ridge_c"], penalty="l2", solver="lbfgs",
        max_iter=5000, random_state=42
    )
    X_train_final = scaler_final.fit_transform(current_X[train_mask])
    lr_final.fit(X_train_final, y_train)

    new_feat_coefs = {}
    for sel in selected:
        idx = current_feat.index(sel["feature"])
        coef = lr_final.coef_[0][idx]
        new_feat_coefs[sel["feature"]] = round(coef, 4)
        print(f"  {sel['feature']}: {coef:+.4f}")

    # =========================================================================
    # Save results
    # =========================================================================
    results = {
        "version": "41.0.0",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline_version": "40.0.0",
        "baseline_auc": round(base_auc, 4),
        "final_wf_auc": round(final_auc, 4),
        "final_wf_brier": round(final_result["avg_brier"], 4),
        "final_wf_ev_spread": round(final_result["avg_ev_spread"], 2),
        "auc_delta": round(final_auc - base_auc, 4),
        "config": best_config,
        "n_features_v40": X_v40.shape[1],
        "n_features_v41": current_X.shape[1],
        "features_added": [s["feature"] for s in selected],
        "new_feature_coefficients": new_feat_coefs,
        "audit_results": audit_results,
        "greedy_selection": selected,
        "stability": {
            "v41_mean": round(np.mean(v41_aucs), 4),
            "v41_std": round(np.std(v41_aucs), 4),
            "v40_mean": round(np.mean(v40_aucs), 4),
            "v40_std": round(np.std(v40_aucs), 4),
            "wins": wins,
            "n_seeds": 10,
            "t_stat": round(t_stat, 3),
            "p_value": p_value,
        },
        "champion": is_champion,
    }

    if is_champion:
        print(f"\n  {'=' * 80}")
        print(f"  ★★★ GUNGNIR v41.0.0 IS THE NEW CHAMPION ★★★")
        print(f"  AUC: {base_auc:.4f} → {final_auc:.4f} (+{final_auc - base_auc:.4f})")
        print(f"  Features: {X_v40.shape[1]} → {current_X.shape[1]} "
              f"(+{len(selected)})")
        print(f"  Stability: {wins}/10 seeds, p={p_value:.10f}")
        print(f"  {'=' * 80}")
    else:
        print(f"\n  v41 does NOT beat v40 with sufficient stability.")
        print(f"  v40 remains CHAMPION (AUC {base_auc:.4f})")

    out_path = os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=lambda x: bool(x) if isinstance(x, np.bool_) else float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
    print(f"\n  Results saved to {out_path}")

    return results


if __name__ == "__main__":
    main()
