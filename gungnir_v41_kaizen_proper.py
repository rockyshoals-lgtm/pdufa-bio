#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v41 KAIZEN — Multi-Pillar Deep Feature Mining
================================================================================

v40 BASELINE: AUC 0.7678, 125 features (v39.1's 122 + 3 new: conference, days_to_cover, conf_x_small)

STRATEGY FOR v41:
1. Load v39 module and data (same as v40 did)
2. Engineer BOTH v40 AND v41 features (to get to 125+ new candidates)
3. Deep column audit on NEW features only (not re-testing v40)
4. Greedy forward selection
5. Stability test
6. Report improvements

KAIZEN PILLARS FOR v41:
1. Non-linear transforms of CT.gov continuous features
2. Phase × TA deeper interactions
3. CT.gov × outcome quality interactions
4. Price/float deep mining
5. V40 signal (conference + days_to_cover) deeper interactions
"""

import csv, json, math, os, re, sys, warnings, io
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

V40_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# Conference patterns from v40
ELITE_CONFERENCES = ["AACR", "ASH", "ESMO"]
TIER1_CONFERENCES = ["ASCO", "AAN", "EHA", "AASLD"]
TIER2_CONFERENCES = ["SITC", "SNO", "ACNP", "ACR", "ADA", "EASD", "ECTRIMS",
                     "WCG", "EULAR", "DDW", "AUA", "ATS", "CHEST", "IDSA"]
ALL_CONFERENCES = ELITE_CONFERENCES + TIER1_CONFERENCES + TIER2_CONFERENCES
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
    """Import v39 kaizen module."""
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

    return v39_mod


def engineer_v40_and_v41_features(events, si_data):
    """Engineer both v40 and v41 features.

    Returns dict mapping (ticker, date) → {v40_feat: val, v41_feat: val, ...}
    """
    lookup = {}

    for ev in events:
        ticker = ev.get("ticker", "").upper()
        date = ev.get("date", "")
        key = (ticker, date)

        # Base info
        catalyst_text = ev.get("catalyst_text", "")
        conference_field = ev.get("_conference", "")
        is_phase3 = 1 if ev.get("_parse_phase") == 3 else 0
        is_phase2 = 1 if ev.get("_parse_phase") == 2 else 0
        is_phase2b = 1 if ev.get("_parse_phase") == 2 and "2b" in str(ev.get("stage", "")).lower() else 0
        is_phase1 = 1 if ev.get("_parse_phase") == 1 else 0
        is_micro = int(ev.get("is_micro", 0) or 0)
        is_small = int(ev.get("is_small", 0) or 0)
        pre_price = float(ev.get("pre_price", 0) or 0)

        ta_very_high = float(ev.get("ta_very_high", 0) or 0)
        ta_recent_rate = float(ev.get("ta_recent_rate", 0) or 0)
        indication_density = float(ev.get("indication_density", 0) or 0)

        # CT.gov features
        ct_enrollment = float(ev.get("ct_enrollment", 0) or 0)
        ct_n_sites = float(ev.get("ct_n_sites", 0) or 0)
        ct_n_arms = float(ev.get("ct_n_arms", 0) or 0)
        ct_n_per_arm = float(ev.get("ct_n_per_arm", 0) or 0)
        ct_log_enrollment = float(ev.get("ct_log_enrollment", 0) or 0)
        ct_ep_hard = float(ev.get("ct_ep_hard", 0) or 0)
        ct_ep_surrogate = float(ev.get("ct_ep_surrogate", 0) or 0)
        ct_is_randomized = float(ev.get("ct_is_randomized", 0) or 0)
        ct_is_double_blind = float(ev.get("ct_is_double_blind", 0) or 0)
        ct_masking_rigor = float(ev.get("ct_masking_rigor", 0) or 0)
        ct_has_dmc = float(ev.get("ct_has_dmc", 0) or 0)
        ct_is_global = float(ev.get("ct_is_global", 0) or 0)

        # ===== V40 FEATURES =====
        has_conf, conf_tier = extract_conference(catalyst_text, conference_field)
        conf_x_small = has_conf * (is_micro + is_small)

        # SI data
        si = si_data.get(ticker, {})
        if "error" in si:
            si = {}
        pct_si = float(si.get("short_pct_float", 0) or 0)
        dtc = float(si.get("short_ratio", 0) or 0)

        # ===== V41 FEATURES (NEW PILLARS) =====
        # Pillar 1: Non-linear transforms
        enrollment_sq = ct_enrollment ** 2 if ct_enrollment > 0 else 0
        n_sites_sq = ct_n_sites ** 2 if ct_n_sites > 0 else 0
        n_per_arm_sq = ct_n_per_arm ** 2 if ct_n_per_arm > 0 else 0

        # Pillar 2: Phase × TA
        phase2_x_ta_vh = is_phase2 * ta_very_high
        phase3_x_ta_vh = is_phase3 * ta_very_high

        # Pillar 3: CT.gov × outcome/phase
        hard_ep_x_phase3 = ct_ep_hard * is_phase3
        surrogate_x_phase2 = ct_ep_surrogate * is_phase2
        randomized_x_phase3 = ct_is_randomized * is_phase3
        double_blind_x_phase3 = ct_is_double_blind * is_phase3
        n_arms_x_phase3 = ct_n_arms * is_phase3

        # Pillar 4: V40 signal interactions
        conf_x_ind_density = has_conf * indication_density
        conf_x_phase3 = has_conf * is_phase3
        dtc_x_micro = dtc * is_micro

        # Pillar 5: Price
        is_penny = 1.0 if 0 < pre_price < 5 else 0.0
        penny_x_micro = is_penny * is_micro

        lookup[key] = {
            # V40 features
            "v40_has_conference": float(has_conf),
            "v40_days_to_cover": float(dtc),
            "v40_conf_x_small": float(conf_x_small),
            # V41 features
            "v41_enrollment_sq": float(enrollment_sq),
            "v41_n_sites_sq": float(n_sites_sq),
            "v41_n_per_arm_sq": float(n_per_arm_sq),
            "v41_phase2_x_ta_vh": float(phase2_x_ta_vh),
            "v41_phase3_x_ta_vh": float(phase3_x_ta_vh),
            "v41_hard_ep_x_phase3": float(hard_ep_x_phase3),
            "v41_surrogate_x_phase2": float(surrogate_x_phase2),
            "v41_randomized_x_phase3": float(randomized_x_phase3),
            "v41_double_blind_x_phase3": float(double_blind_x_phase3),
            "v41_n_arms_x_phase3": float(n_arms_x_phase3),
            "v41_conf_x_ind_density": float(conf_x_ind_density),
            "v41_conf_x_phase3": float(conf_x_phase3),
            "v41_dtc_x_micro": float(dtc_x_micro),
            "v41_penny_x_micro": float(penny_x_micro),
        }

    return lookup


def main():
    print("\n" + "=" * 80)
    print("  GUNGNIR v41 KAIZEN — Multi-Pillar Deep Feature Mining")
    print("=" * 80)

    # Load v39 module
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Load v39 baseline (122 features)")
    print(f"{'=' * 80}")

    print("\n  Loading v39 kaizen module...")
    v39 = load_v39_module()

    print("  Loading data...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    events, ctgov_lookup = v39.load_data()
    sys.stdout = old_stdout
    print(f"  Total events: {len(events)}")

    # Load SI cache
    si_path = os.path.join(DATA_DIR, "short_interest_snapshot.json")
    with open(si_path) as f:
        si_data = json.load(f)
    print(f"  SI cache: {len(si_data)} tickers")

    # Build v39 baseline features (122)
    print("\n  Building v39 base feature matrix (122 features)...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = v39.build_features(
        events, ctgov_lookup, include_v37=True, include_v38=True, include_candidates=[]
    )
    sys.stdout = old_stdout
    print(f"  v39 base: {X_base.shape[0]} × {X_base.shape[1]} features")

    # Evaluate v39 baseline
    print("\n  Evaluating v39 baseline (walk-forward)...")
    baseline_v39 = v39.evaluate_wf(
        X_base, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **V40_CONFIG
    )
    v39_auc = baseline_v39["avg_auc"]
    print(f"\n  *** v39 BASELINE: AUC={v39_auc:.4f} (reported: 0.7599)")

    # Engineer both V40 + V41 features
    print(f"\n{'=' * 80}")
    print("  PHASE 1b: Engineer V40 + V41 features")
    print(f"{'=' * 80}")

    print("\n  Engineering V40 + V41 candidate features...")
    feat_lookup = engineer_v40_and_v41_features(events, si_data)

    sample_key = next(iter(feat_lookup))
    v40_features = [k for k in feat_lookup[sample_key].keys() if k.startswith("v40_")]
    v41_features = [k for k in feat_lookup[sample_key].keys() if k.startswith("v41_")]
    print(f"  V40 features: {len(v40_features)}")
    print(f"  V41 candidate features: {len(v41_features)}")

    # Add V40 features to baseline first (to get to v40 AUC)
    def get_col(feat_name):
        vals = []
        for ev in events:
            key = (ev.get("ticker", "").upper(), ev.get("date", ""))
            val = feat_lookup.get(key, {}).get(feat_name, 0)
            vals.append(float(val or 0))
        return np.array(vals)

    print("\n  Adding V40 features to baseline...")
    X_v40 = X_base.copy()
    for v40_feat in v40_features:
        col = get_col(v40_feat).reshape(-1, 1)
        if np.std(col) > 1e-10:
            X_v40 = np.column_stack([X_v40, col])

    baseline_v40 = v39.evaluate_wf(
        X_v40, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=False, **V40_CONFIG
    )
    v40_auc = baseline_v40["avg_auc"]
    print(f"  *** v40 RECONSTRUCTED: AUC={v40_auc:.4f} (target: 0.7678, v39 was {v39_auc:.4f})")

    # =========================================================================
    # PHASE 2: Deep column audit on V41 features only
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 2: Deep Column Audit — V41 candidates only")
    print(f"{'=' * 80}")

    print(f"\n  {'Feature':<35s} {'WF_AUC':>8s} {'ΔAUC':>8s} {'Status':>10s}")
    print(f"  {'-' * 65}")

    audit_results = []
    for feat_name in v41_features:
        col = get_col(feat_name)

        if np.std(col) < 1e-10:
            print(f"  {feat_name:<35s} {'ZERO VARIANCE':>40s}")
            continue

        X_test = np.column_stack([X_v40, col.reshape(-1, 1)])
        result = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates, **V40_CONFIG)
        delta = result["avg_auc"] - v40_auc

        status = "✓ PASS" if delta > 0.0005 else "≈ FLAT" if delta > -0.0005 else "✗ HURTS"
        flag = " <<<" if delta > 0.001 else (" !!!" if delta < -0.003 else "")

        print(f"  {feat_name:<35s} {result['avg_auc']:>8.4f} {delta:>+8.4f} {status:>10s}{flag}")

        audit_results.append({
            "feature": feat_name,
            "auc": result["avg_auc"],
            "delta_auc": delta,
            "status": status.strip(),
        })

    audit_results.sort(key=lambda x: -x["delta_auc"])

    print(f"\n  Top candidates:")
    for r in audit_results[:10]:
        print(f"  {r['feature']:<35s} Δ={r['delta_auc']:+.4f}")

    winners = [r for r in audit_results if r["delta_auc"] > 0.0005]
    print(f"\n  *** {len(winners)}/{len(v41_features)} features pass audit (Δ > +0.0005)")

    if not winners:
        print("\n  No V41 features pass audit. v40 remains champion.")
        results = {
            "version": "41.0.0",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_auc": round(v40_auc, 4),
            "final_auc": round(v40_auc, 4),
            "champion": False,
            "verdict": "No new V41 features beat V40",
            "audit_count": len(audit_results),
            "winners_count": 0,
        }
        with open(os.path.join(DATA_DIR, "gungnir_v41_kaizen_proper_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        return results

    # =========================================================================
    # PHASE 3: Greedy forward selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Greedy Forward Selection")
    print(f"{'=' * 80}")

    current_X = X_v40.copy()
    current_auc = v40_auc
    selected = []

    candidates = [r["feature"] for r in audit_results if r["delta_auc"] > 0]
    print(f"  Starting: AUC={current_auc:.4f}, {current_X.shape[1]} features")
    print(f"  Candidates: {len(candidates)}")

    for round_num in range(min(10, len(candidates))):
        best_feat = None
        best_auc = current_auc
        best_result = None

        for feat in candidates:
            if feat in [s["feature"] for s in selected]:
                continue

            col = get_col(feat)
            if np.std(col) < 1e-10:
                continue

            X_trial = np.column_stack([current_X, col.reshape(-1, 1)])
            result = v39.evaluate_wf(X_trial, y_bin, y_gp, y_cr, y_ret, dates, **V40_CONFIG)

            if result["avg_auc"] > best_auc + 0.0002:
                best_feat = feat
                best_auc = result["avg_auc"]
                best_result = result

        if best_feat:
            col = get_col(best_feat)
            current_X = np.column_stack([current_X, col.reshape(-1, 1)])
            delta = best_auc - current_auc
            current_auc = best_auc
            selected.append({
                "feature": best_feat,
                "auc": round(best_auc, 4),
                "delta": round(delta, 4),
            })
            print(f"  Rd {round_num+1}: +{best_feat} → AUC={best_auc:.4f} Δ={delta:+.4f}")
        else:
            print(f"  Rd {round_num+1}: No improvement. Stopping.")
            break

    n_new = len(selected)
    total_delta = current_auc - v40_auc
    print(f"\n  Selected: {n_new} features")
    print(f"  AUC delta: {total_delta:+.4f} ({v40_auc:.4f} → {current_auc:.4f})")

    if not selected:
        results = {
            "version": "41.0.0",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_auc": round(v40_auc, 4),
            "final_auc": round(v40_auc, 4),
            "champion": False,
            "verdict": "No features pass greedy forward selection",
        }
        with open(os.path.join(DATA_DIR, "gungnir_v41_kaizen_proper_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        return results

    # =========================================================================
    # PHASE 4: 10-Seed Stability Test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 4: 10-Seed Stability Test")
    print(f"{'=' * 80}")

    aucs_v41 = []
    aucs_v40 = []
    for seed in range(10):
        r41 = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates, seed=seed, **V40_CONFIG)
        aucs_v41.append(r41["avg_auc"])
        r40 = v39.evaluate_wf(X_v40, y_bin, y_gp, y_cr, y_ret, dates, seed=seed, **V40_CONFIG)
        aucs_v40.append(r40["avg_auc"])

    aucs_v41 = np.array(aucs_v41)
    aucs_v40 = np.array(aucs_v40)
    wins = sum(1 for a41, a40 in zip(aucs_v41, aucs_v40) if a41 > a40)

    from scipy import stats
    t_stat, p_val = stats.ttest_rel(aucs_v41, aucs_v40)

    print(f"  v41: {aucs_v41.mean():.4f} ± {aucs_v41.std():.4f}")
    print(f"  v40: {aucs_v40.mean():.4f} ± {aucs_v40.std():.4f}")
    print(f"  v41 beats v40: {wins}/10 seeds, p={p_val:.6f}")

    is_champion = wins >= 7 and current_auc > v40_auc

    # Final evaluation
    print(f"\n{'=' * 80}")
    print(f"  PHASE 5: Final Evaluation")
    print(f"{'=' * 80}")

    final_result = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates, verbose=True, **V40_CONFIG)
    print(f"\n  *** v41 FINAL: AUC={final_result['avg_auc']:.4f}")

    # Save results
    if is_champion:
        print(f"\n  🏆 v41 IS NEW CHAMPION! AUC {final_result['avg_auc']:.4f} > v40 {v40_auc:.4f}")
    else:
        print(f"\n  v40 remains champion ({wins}/10 seeds)")

    results = {
        "version": "41.0.0",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline_version": "40.0.0",
        "baseline_auc": round(v40_auc, 4),
        "final_wf_auc": round(final_result["avg_auc"], 4),
        "final_wf_brier": round(final_result["avg_brier"], 4),
        "final_wf_ev_spread": round(final_result["avg_ev_spread"], 2),
        "auc_delta": round(final_result["avg_auc"] - v40_auc, 4),
        "n_features_v40": X_v40.shape[1],
        "n_features_v41": current_X.shape[1],
        "features_added": [s["feature"] for s in selected],
        "greedy_selection": selected,
        "audit_top_15": audit_results[:15],
        "audit_count": len(audit_results),
        "winners_count": len(winners),
        "stability": {
            "v41_mean": round(float(aucs_v41.mean()), 4),
            "v41_std": round(float(aucs_v41.std()), 4),
            "v40_mean": round(float(aucs_v40.mean()), 4),
            "v40_std": round(float(aucs_v40.std()), 4),
            "wins": int(wins),
            "n_seeds": 10,
            "t_stat": round(float(t_stat), 4),
            "p_value": float(p_val),
        },
        "champion": bool(is_champion),
    }

    results_path = os.path.join(DATA_DIR, "gungnir_v41_kaizen_proper_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {results_path}")

    return results


if __name__ == "__main__":
    result = main()
    if result and result.get("champion"):
        print(f"\n  🏆 v41 is NEW CHAMPION: {result['final_wf_auc']}")
    else:
        print(f"\n  v40 remains champion")
