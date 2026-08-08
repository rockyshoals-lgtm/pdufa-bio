#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v41 KAIZEN — ORATS Options/IV Features (Explosion Detector Signal)
================================================================================

CONTEXT:
  Gungnir v40 is the champion: 125 features, 3-model meta-ensemble (Ridge 70% + XGB 30%),
  WF AUC 0.7678.

  BIFROST v5.2 Explosion Detector uses options/IV features to predict D1 moves > 25%.
  Can these same features improve phase readout outcome prediction?

ORATS CANDIDATE FEATURES (all T-1 compliant):
  1. has_options: binary — whether the event had tradeable options at T-14
  2. entry_iv_pct: IV level at T-14 entry
  3. iv_high: binary IV > 100%
  4. iv_low: binary IV < 50%
  5. entry_spread_pct: bid-ask spread percentage
  6. spread_tight: binary spread < 15%
  7. entry_oi: open interest at entry
  8. oi_high: binary OI > 500
  9. iv_x_micro: IV × micro-cap interaction
  10. iv_x_phase3: IV × Phase 3 interaction
  11. iv_x_small: IV × small-cap interaction
  12. options_x_phase2: has_options × Phase 2 interaction

APPROACH:
  1. Load v40 champion data + features
  2. Merge ORATS options data by (ticker, event_date)
  3. Test each candidate INDEPENDENTLY on WF AUC
  4. Greedy forward selection
  5. 10-seed stability test
  6. Report final AUC vs v40 baseline
"""

import csv, json, math, os, re, sys, warnings, io
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# v40 config
V40_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}


def load_v39_module():
    """Import v39 kaizen module (v40 uses v39 underneath)."""
    import importlib.util

    v39_path = os.path.join(DATA_DIR, "gungnir_v39_kaizen.py")
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

    return v39_mod


def load_orats_data():
    """Load ORATS options backtest data (readout trades only)."""
    orats_path = os.path.join(DATA_DIR, "options_backtest_v2_results.json")

    if not os.path.exists(orats_path):
        print(f"  [WARN] ORATS file not found: {orats_path}")
        return {}

    with open(orats_path) as f:
        data = json.load(f)

    # Build lookup: (ticker, event_date) → ORATS data
    # Use readout_trades since we're testing Gungnir (phase readouts)
    orats_lookup = {}
    for trade in data.get("readout_trades", []):
        ticker = trade.get("ticker", "").upper()
        event_date = trade.get("event_date", "")

        key = (ticker, event_date)
        orats_lookup[key] = {
            "has_options": 1,
            "entry_iv_pct": float(trade.get("entry_iv_pct", 0) or 0),
            "entry_spread_pct": float(trade.get("entry_spread_pct", 0) or 0),
            "entry_oi": float(trade.get("entry_oi", 0) or 0),
        }

    n_readout = len(data.get("readout_trades", []))
    n_matched = len(orats_lookup)
    print(f"  ORATS readout trades: {n_readout}, matched with IV data: {n_matched}")

    return orats_lookup


def engineer_orats_candidates(events, orats_lookup):
    """Engineer ORATS candidate features."""
    candidate_lookup = {}
    matched = 0

    for ev in events:
        ticker = ev.get("ticker", "").upper()
        date = ev.get("date", "")
        key = (ticker, date)

        # Get base event info
        is_phase2 = 1 if ev.get("_parse_phase") == 2 else 0
        is_phase3 = 1 if ev.get("_parse_phase") == 3 else 0
        is_micro = int(ev.get("is_micro", 0) or 0)
        is_small = int(ev.get("is_small", 0) or 0)

        # Get ORATS data
        orats = orats_lookup.get(key, {})

        if orats:
            matched += 1
            has_opts = 1.0
            iv_pct = orats.get("entry_iv_pct", 0)
            spread_pct = orats.get("entry_spread_pct", 0)
            oi = orats.get("entry_oi", 0)
        else:
            has_opts = 0.0
            iv_pct = 0.0
            spread_pct = 0.0
            oi = 0.0

        # Binary features
        iv_high = 1.0 if iv_pct > 100 else 0.0
        iv_low = 1.0 if 0 < iv_pct < 50 else 0.0
        spread_tight = 1.0 if 0 < spread_pct < 15 else 0.0
        oi_high = 1.0 if oi > 500 else 0.0

        # Interactions
        iv_x_micro = iv_pct * is_micro
        iv_x_phase3 = iv_pct * is_phase3
        iv_x_small = iv_pct * (is_micro + is_small)
        options_x_phase2 = has_opts * is_phase2

        candidate_lookup[key] = {
            "v41_has_options": has_opts,
            "v41_entry_iv_pct": iv_pct,
            "v41_iv_high": iv_high,
            "v41_iv_low": iv_low,
            "v41_entry_spread_pct": spread_pct,
            "v41_spread_tight": spread_tight,
            "v41_entry_oi": oi,
            "v41_oi_high": oi_high,
            "v41_iv_x_micro": iv_x_micro,
            "v41_iv_x_phase3": iv_x_phase3,
            "v41_iv_x_small": iv_x_small,
            "v41_options_x_phase2": options_x_phase2,
        }

    n = len(events)
    print(f"  ORATS features engineered: {matched}/{n} events matched ({100*matched/n:.1f}%)")

    return candidate_lookup


def main():
    print("\n" + "=" * 80)
    print("  GUNGNIR v41 KAIZEN — ORATS Options/IV Features")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Load v40 baseline (via v39 module)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Load v40 baseline (125 features, AUC ~0.7678)")
    print(f"{'=' * 80}")

    print("\n  Loading v39 kaizen module (v40 uses v39)...")
    v39 = load_v39_module()

    print("  Loading data via v39.load_data()...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    events, ctgov_lookup = v39.load_data()
    sys.stdout = old_stdout

    print(f"  Total events: {len(events)}")

    print("\n  Building v40 feature matrix (125 features)...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    # v40 features: v39's 122 + conference (3 features selected) = 125 total
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = v39.build_features(
        events, ctgov_lookup,
        include_v37=True, include_v38=True,
        include_candidates=["ct_ep_is_safety", "ct_ep_is_biomarker", "ct_active_comp_x_phase3",
                           "orphan_x_micro", "ch_is_enzyme", "ind_maturity_high",
                           "ch_is_ion_channel", "ct_has_combination", "ct_ep_is_pfs", "ch_is_agonist",
                           "v40_has_conference", "v40_days_to_cover", "v40_conf_x_small"]
    )
    sys.stdout = old_stdout

    print(f"  Feature matrix: {X_base.shape[0]} events × {X_base.shape[1]} features")
    print(f"  Positive rate: {y_bin.mean():.3f}")

    print("\n  Evaluating v40 baseline (walk-forward)...")
    baseline = v39.evaluate_wf(
        X_base, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=False, **V40_CONFIG
    )

    base_auc = baseline["avg_auc"]
    print(f"\n  *** v40 BASELINE: AUC={base_auc:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp")

    # =========================================================================
    # PHASE 1b: Load and engineer ORATS features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1b: Load and engineer ORATS candidate features")
    print(f"{'=' * 80}")

    print("\n  Loading ORATS options backtest data...")
    orats_lookup = load_orats_data()

    print("\n  Engineering v41 candidate features...")
    cand_lookup = engineer_orats_candidates(events, orats_lookup)

    # Get candidate feature names
    sample_key = next(iter(cand_lookup))
    candidate_names = sorted(cand_lookup[sample_key].keys())
    print(f"  Candidate features: {len(candidate_names)}")

    def get_candidate_column(feat_name):
        vals = []
        for ev in events:
            key = (ev.get("ticker", "").upper(), ev.get("date", ""))
            cands = cand_lookup.get(key, {})
            vals.append(float(cands.get(feat_name, 0) or 0))
        return np.array(vals)

    # =========================================================================
    # PHASE 2: Deep column audit — test each candidate independently
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 2: Deep Column Audit — test each v41 candidate")
    print(f"{'=' * 80}")

    print(f"\n  {'Feature':<35s} {'WF_AUC':>8s} {'ΔAUC':>8s} {'Status':>10s}")
    print(f"  {'-' * 68}")

    audit_results = []
    for feat_name in candidate_names:
        col = get_candidate_column(feat_name)

        # Skip zero-variance features
        if np.std(col) < 1e-10:
            print(f"  {feat_name:<35s} {'ZERO VARIANCE — SKIP':>40s}")
            continue

        # Append to baseline matrix
        X_cand = np.column_stack([X_base, col])

        # Walk-forward evaluation
        result = v39.evaluate_wf(
            X_cand, y_bin, y_gp, y_cr, y_ret, dates,
            **V40_CONFIG
        )
        delta = result["avg_auc"] - base_auc

        status = "✓ PASS" if delta > 0.0005 else "≈ FLAT" if delta > -0.0005 else "✗ HURTS"
        flag = " <<<" if delta > 0.001 else (" !!!" if delta < -0.003 else "")

        print(f"  {feat_name:<35s} {result['avg_auc']:>8.4f} {delta:>+8.4f} {status:>10s}{flag}")

        audit_results.append({
            "feature": feat_name,
            "auc": result["avg_auc"],
            "delta_auc": delta,
            "brier": result["avg_brier"],
            "ev_spread": result["avg_ev_spread"],
            "status": status.strip(),
        })

    # Sort by AUC delta
    audit_results.sort(key=lambda x: -x["delta_auc"])

    print(f"\n  {'=' * 68}")
    print(f"  AUDIT RESULTS (sorted by ΔAUC)")
    print(f"  {'=' * 68}")
    for r in audit_results:
        marker = " ***" if r["delta_auc"] > 0.001 else ""
        print(f"  {r['feature']:<35s} AUC={r['auc']:.4f} Δ={r['delta_auc']:+.4f} "
              f"EV={r['ev_spread']:+.1f}pp{marker}")

    winners = [r for r in audit_results if r["delta_auc"] > 0.0005]
    print(f"\n  *** {len(winners)} features pass audit (ΔAUC > +0.0005)")

    if not winners:
        print("\n  No features pass audit. v40 remains champion.")
        results = {
            "version": "41.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "40.0.0", "baseline_auc": round(base_auc, 4),
            "final_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results, "selected": [],
            "verdict": "No ORATS features improve outcome prediction",
            "coverage": f"{len(orats_lookup)}/{len(events)} events matched",
        }
        with open(os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        print("\n  Results saved: gungnir_v41_kaizen_results.json")
        return results

    # =========================================================================
    # PHASE 3: Greedy forward selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Greedy Forward Selection")
    print(f"{'=' * 80}")

    current_X = X_base.copy()
    current_auc = base_auc
    selected = []

    # Candidates: all features with positive delta, sorted by delta
    candidates_to_try = [r["feature"] for r in audit_results if r["delta_auc"] > 0]
    print(f"  Starting AUC: {current_auc:.4f} ({X_base.shape[1]} features)")
    print(f"  Candidates to try: {len(candidates_to_try)}")

    for round_num in range(len(candidates_to_try)):
        best_feat = None
        best_auc = current_auc
        best_result = None

        for feat_name in candidates_to_try:
            if feat_name in [s["feature"] for s in selected]:
                continue

            col = get_candidate_column(feat_name).reshape(-1, 1)
            if np.std(col) < 1e-10:
                continue

            X_trial = np.column_stack([current_X, col])
            result = v40.evaluate_wf(
                X_trial, y_bin, y_gp, y_cr, y_ret, dates,
                **V40_CONFIG
            )

            if result["avg_auc"] > best_auc + 0.0002:
                best_feat = feat_name
                best_auc = result["avg_auc"]
                best_result = result

        if best_feat:
            col = get_candidate_column(best_feat).reshape(-1, 1)
            current_X = np.column_stack([current_X, col])
            delta = best_auc - current_auc
            current_auc = best_auc
            selected.append({
                "feature": best_feat,
                "auc": round(best_auc, 4),
                "delta": round(delta, 4),
                "ev_spread": round(best_result["avg_ev_spread"], 2),
            })
            print(f"  Round {round_num+1}: +{best_feat} → AUC={best_auc:.4f} "
                  f"(Δ={delta:+.4f}) EV_spread={best_result['avg_ev_spread']:+.1f}pp")
        else:
            print(f"  Round {round_num+1}: No improvement ≥ +0.0002. Stopping.")
            break

    n_new = len(selected)
    n_total = X_base.shape[1] + n_new
    total_delta = current_auc - base_auc
    print(f"\n  FINAL: {n_total} features ({X_base.shape[1]} v40 + {n_new} new)")
    if selected:
        print(f"  v41 adds: {[s['feature'] for s in selected]}")
    print(f"  AUC improvement: {total_delta:+.4f} ({base_auc:.4f} → {current_auc:.4f})")

    if not selected:
        print("\n  ❌ No features selected via greedy. v40 remains champion.")
        results = {
            "version": "41.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "40.0.0", "baseline_auc": round(base_auc, 4),
            "final_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results, "selected": [],
            "verdict": "No features pass greedy forward selection",
            "coverage": f"{len(orats_lookup)}/{len(events)} events matched",
        }
        with open(os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        print("\n  Results saved: gungnir_v41_kaizen_results.json")
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
        # v41
        r41 = v40.evaluate_wf(
            current_X, y_bin, y_gp, y_cr, y_ret, dates,
            seed=seed, **V40_CONFIG
        )
        aucs_v41.append(r41["avg_auc"])

        # v40 baseline
        r40 = v40.evaluate_wf(
            X_base, y_bin, y_gp, y_cr, y_ret, dates,
            seed=seed, **V40_CONFIG
        )
        aucs_v40.append(r40["avg_auc"])

    aucs_v41 = np.array(aucs_v41)
    aucs_v40 = np.array(aucs_v40)
    wins = sum(1 for a41, a40 in zip(aucs_v41, aucs_v40) if a41 > a40)

    from scipy import stats
    t_stat, p_val = stats.ttest_rel(aucs_v41, aucs_v40)

    print(f"  v41: {aucs_v41.mean():.4f} ± {aucs_v41.std():.4f} "
          f"(min {aucs_v41.min():.4f}, max {aucs_v41.max():.4f})")
    print(f"  v40: {aucs_v40.mean():.4f} ± {aucs_v40.std():.4f}")
    print(f"  v41 beats v40: {wins}/10 seeds")
    print(f"  Paired t-test: t={t_stat:.4f}, p={p_val:.10f}")

    is_champion = wins >= 7 and current_auc > base_auc

    # =========================================================================
    # PHASE 5: Full evaluation
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 5: Full Meta-Ensemble Evaluation")
    print(f"{'=' * 80}")

    final_result = v40.evaluate_wf(
        current_X, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **V40_CONFIG
    )
    print(f"\n  *** v41 FINAL: AUC={final_result['avg_auc']:.4f} "
          f"Brier={final_result['avg_brier']:.4f} "
          f"EV_spread={final_result['avg_ev_spread']:+.2f}pp "
          f"EV_edge={final_result['avg_ev_edge']:+.2f}%")

    # =========================================================================
    # Save results
    # =========================================================================
    if is_champion:
        print(f"\n  🏆 v41 IS NEW CHAMPION! AUC {final_result['avg_auc']:.4f} > v40 {base_auc:.4f}")
    else:
        print(f"\n  ❌ v41 does NOT reliably beat v40 ({wins}/10 seeds)")

    results = {
        "version": "41.0.0",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline_version": "40.0.0",
        "baseline_auc": round(base_auc, 4),
        "final_wf_auc": round(final_result["avg_auc"], 4),
        "final_wf_brier": round(final_result["avg_brier"], 4),
        "final_wf_ev_spread": round(final_result["avg_ev_spread"], 2),
        "auc_delta": round(final_result["avg_auc"] - base_auc, 4),
        "n_features_v40": X_base.shape[1],
        "n_features_v41": n_total,
        "features_added": [s["feature"] for s in selected],
        "greedy_selection": selected,
        "audit_results": audit_results,
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
        "coverage": f"{len(orats_lookup)}/{len(events)} events had ORATS options data ({100*len(orats_lookup)/len(events):.1f}%)",
        "verdict": "ORATS features do NOT improve phase readout outcome prediction" if not is_champion else "ORATS features improve outcome prediction",
    }

    results_path = os.path.join(DATA_DIR, "gungnir_v41_kaizen_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {results_path}")

    return results


if __name__ == "__main__":
    result = main()
    if result is None:
        print("\n  Pipeline could not complete.")
    elif result.get("champion"):
        print(f"\n  🏆 CHAMPION: v41 AUC {result['final_wf_auc']} (v40 was {result['baseline_auc']})")
    else:
        print(f"\n  v40 remains champion. v41 AUC: {result['final_wf_auc']}")
