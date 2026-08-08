#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v40 KAIZEN — Feature Extension via v39 Infrastructure
================================================================================

Uses gungnir_v39_kaizen.py's load_data() and build_features() to ensure
proper baseline. Tests new candidate features through v39's pipeline.

BASELINE: v39.1.0 (AUC 0.7599, 122 features)

NEW FEATURES FOR V40:
1. Conference presentation features (has_conference, conference_tier, etc.)
2. CT.gov interaction enhancements
3. Temporal momentum interactions
4. Non-linear transforms (log, sqrt, cubic)
5. Sponsor dynamics × indication interactions
"""

import sys
import os
import json
import numpy as np
import random

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

# Import v39 infrastructure
from gungnir_v39_kaizen import (
    load_data, build_features, evaluate_wf,
    V38_ADDED, V37_ADDED,
)

# v39.1 config (baseline)
V39_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

def engineer_v40_features(row, base_features):
    """Generate v40 candidate features."""
    candidates = {}

    phase = base_features.get("phase_numeric", 2)
    ssr = base_features.get("sponsor_success_rate", 0.5)
    is_micro = base_features.get("is_micro", 0)
    is_small = base_features.get("is_small", 0)
    is_onc = base_features.get("ta_oncology", 0)
    is_rare = base_features.get("ta_rare_disease", 0)
    indication_density = base_features.get("indication_density", 0.5)
    momentum_5d = base_features.get("momentum_5d", 0)
    momentum_10d = base_features.get("momentum_10d", 0)

    # CONFERENCE FEATURES
    conference_str = row.get("Conference", "").upper() if row else ""
    catalyst_str = row.get("Catalyst", "").lower() if row else ""

    has_conf = 1 if (conference_str and "NO" not in conference_str) else 0
    conf_tier = 0
    if has_conf:
        if any(x in conference_str for x in ["AACR", "ASH", "ESMO"]):
            conf_tier = 3
        elif any(x in conference_str for x in ["ASCO", "AAN", "EHA"]):
            conf_tier = 2
        elif any(x in conference_str for x in ["SITC", "SNO"]):
            conf_tier = 1

    candidates["has_conference"] = has_conf
    candidates["conference_tier"] = conf_tier
    candidates["conference_x_phase3"] = has_conf * (1 if phase == 3 else 0)
    candidates["tier_x_phase3"] = conf_tier * (1 if phase == 3 else 0)

    # CT.GOV INTERACTIONS
    ep_hard = base_features.get("ctgov_ep_hard", 0)
    is_randomized = base_features.get("ctgov_is_randomized", 0)
    is_double_blind = base_features.get("ctgov_is_double_blind", 0)

    candidates["ct_ep_hard_x_onc"] = ep_hard * is_onc
    candidates["ct_db_phase3"] = is_double_blind * (1 if phase == 3 else 0)
    candidates["ct_randomized_x_phase3"] = is_randomized * (1 if phase == 3 else 0)

    # MOMENTUM INTERACTIONS
    candidates["momentum_10d_x_ssr"] = momentum_10d * ssr
    candidates["momentum_5d_x_micro"] = momentum_5d * is_micro

    # COMPETITIVE LANDSCAPE
    import math
    candidates["ind_dens_sqrt"] = math.sqrt(max(indication_density, 0.001))
    candidates["ind_dens_x_ssr"] = indication_density * ssr
    candidates["high_comp"] = 1 if indication_density > 1.0 else 0

    return candidates


def main():
    print("\n" + "="*80)
    print("GUNGNIR v40 KAIZEN — Simple Feature Extension")
    print("="*80)

    # Load data with v39 infrastructure
    events, ctgov_lookup = load_data()
    
    # Phase 1: Baseline
    print("\n[PHASE 1] Baseline v39.1.0")
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = build_features(
        events, ctgov_lookup, include_v37=True, include_v38=True, include_candidates=None
    )
    print(f"  Features: {len(feat_base)}")
    print(f"  Events: {X_base.shape[0]}, Positive: {y_bin.mean():.3f}")

    baseline = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates,
                           verbose=True, **V39_CONFIG)
    print(f"\n*** v39.1 BASELINE: AUC={baseline['avg_auc']:.4f} "
          f"Brier={baseline['avg_brier']:.4f}")

    # Phase 2: Test candidates
    print("\n[PHASE 2] Deep Column Audit")
    sample_ev = events[0]
    sample_base = dict(zip(feat_base, X_base[0]))
    all_candidates = engineer_v40_features(sample_ev, sample_base)
    candidate_names = sorted(all_candidates.keys())
    print(f"  Testing {len(candidate_names)} candidates...")

    audit_results = []
    for i, cand in enumerate(candidate_names):
        X_cand, _, _, _, _, _, _, _ = build_features(
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=[cand]
        )
        result = evaluate_wf(X_cand, y_bin, y_gp, y_cr, y_ret, dates, **V39_CONFIG)
        delta_auc = result["avg_auc"] - baseline["avg_auc"]
        audit_results.append({"feature": cand, "auc": result["avg_auc"], "delta_auc": delta_auc})
        flag = " <<<" if delta_auc > 0.001 else ""
        print(f"    [{i+1:2d}] {cand:35s} {result['avg_auc']:.4f} (Δ={delta_auc:+.4f}){flag}")

    audit_sorted = sorted(audit_results, key=lambda x: -x["delta_auc"])
    winners = [r["feature"] for r in audit_sorted if r["delta_auc"] > 0]
    print(f"  Winners: {winners}")

    # Phase 3: Greedy FS
    print("\n[PHASE 3] Greedy Forward Selection")
    selected = []
    best_auc = baseline["avg_auc"]

    for cand in winners:
        test_set = selected + [cand]
        X_test, _, _, _, _, _, _, _ = build_features(
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=test_set
        )
        result = evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates, **V39_CONFIG)
        if result["avg_auc"] > best_auc + 0.0002:
            selected.append(cand)
            best_auc = result["avg_auc"]
            print(f"  + {cand:35s} AUC={result['avg_auc']:.4f}")
        else:
            print(f"  - {cand:35s} AUC={result['avg_auc']:.4f}")

    print(f"\n  Selected: {selected} (AUC gain={best_auc-baseline['avg_auc']:+.4f})")

    # Phase 4: Final
    print("\n[PHASE 4] Final Champion")
    X_final, y_bin_f, y_gp_f, y_cr_f, y_ret_f, dates_f, meta_f, _ = build_features(
        events, ctgov_lookup, include_v37=True, include_v38=True,
        include_candidates=selected
    )
    final = evaluate_wf(X_final, y_bin_f, y_gp_f, y_cr_f, y_ret_f, dates_f,
                        verbose=True, **V39_CONFIG)

    auc_delta = final["avg_auc"] - baseline["avg_auc"]
    print(f"\n*** v40 FINAL: AUC={final['avg_auc']:.4f} (Δ={auc_delta:+.4f})")

    # Save results
    results = {
        "version": "40.0.0",
        "baseline_auc": baseline["avg_auc"],
        "final_auc": final["avg_auc"],
        "auc_delta": auc_delta,
        "features_added": selected,
        "n_features_total": len(feat_base) + len(selected),
    }
    with open(os.path.join(DATA_DIR, "gungnir_v40_kaizen_results.json"), 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*80)
    print("KAIZEN COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
