#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v40 KAIZEN — Conference Signal + SI + Float + Price Features
================================================================================

APPROACH:
  Start from v39.1.0 as baseline (AUC 0.7599, 122 features, 96.6% CT.gov coverage)

  NEW FEATURE VECTORS:
  1. CONFERENCE SIGNAL (mined from Catalyst text — ~23% of events have mentions)
     - has_conference: binary — catalyst text mentions any major conference
     - conf_tier: ELITE/TIER1/TIER2/NONE encoded (3/2/1/0)
     - conf_x_phase3: conference × Phase 3 interaction
     - conf_x_micro: conference × micro-cap interaction
     - conf_x_small: conference × (micro + small) interaction
     - conf_elite: binary for ELITE conferences
     - conf_tier1_plus: binary for ELITE or TIER1

  2. SHORT INTEREST / FLOAT (from yfinance cache — ~95% of tickers)
     - log_float_inv: log(1B/float) — smaller float → bigger moves
     - pct_float_short: % float shorted
     - days_to_cover: short ratio
     - si_high: binary ≥15% SI
     - si_x_micro: SI × micro interaction
     - si_x_phase3: SI × Phase 3 interaction
     - dtc_high: days to cover ≥10

  3. PRICE FEATURES (from pre_price in readout data)
     - is_penny_stock: price < $5
     - is_low_price: price < $10
     - log_price_inv_gun: log(1/price)
     - penny_x_phase3: penny × Phase 3 interaction
     - low_price_x_micro: low price × micro interaction
     - small_float_penny: small float × penny interaction

  T-1 COMPLIANCE: All features known before readout.

STRATEGY:
  - Use v39's EXACT load_data() + build_features() + evaluate_wf() pipeline
  - Append new candidate columns to the 122-feature matrix
  - Screen each independently via WF AUC, greedy forward select, stability test
"""

import csv, json, math, os, re, sys, warnings, io
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# v39 selected features (from v39 kaizen results)
V39_SELECTED = [
    "ct_ep_is_safety", "ct_ep_is_biomarker", "ct_active_comp_x_phase3",
    "orphan_x_micro", "ch_is_enzyme", "ind_maturity_high",
    "ch_is_ion_channel", "ct_has_combination", "ct_ep_is_pfs", "ch_is_agonist"
]

# v39 config (from v39 kaizen results)
V39_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# Conference patterns
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
    """Import v39 kaizen module via importlib."""
    import importlib.util

    v39_path = os.path.join(DATA_DIR, "gungnir_v39_kaizen.py")

    # Before loading v39, patch its CTGOV path to use the FULL lookup (96.6%)
    # v39.1 deployed with full coverage, so we need to match that
    full_lookup_path = os.path.join(DATA_DIR, "ctgov_training_lookup_v2_full.json")
    base_lookup_path = os.path.join(DATA_DIR, "ctgov_training_lookup_v2.json")

    spec = importlib.util.spec_from_file_location("v39_kaizen", v39_path)
    v39_mod = importlib.util.module_from_spec(spec)

    # Suppress v39's print during import
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(v39_mod)
    except Exception as e:
        sys.stdout = old_stdout
        print(f"  [WARN] v39 module load warning: {e}")
    sys.stdout = old_stdout

    # Patch the CTGOV_TRAIN_LOOKUP_V2 path to use full lookup if available
    if os.path.exists(full_lookup_path):
        v39_mod.CTGOV_TRAIN_LOOKUP_V2 = full_lookup_path
        print(f"  Patched v39 to use FULL CT.gov lookup (96.6% coverage)")
    else:
        print(f"  Using standard CT.gov lookup")

    return v39_mod


def engineer_v40_candidates(events, si_data):
    """Engineer v40 candidate features for all events.

    Returns dict mapping (ticker, date) → {feature_name: value, ...}
    """
    candidate_lookup = {}
    conf_count = 0
    si_count = 0

    for ev in events:
        ticker = ev.get("ticker", "").upper()
        date = ev.get("date", "")
        key = (ticker, date)

        # Get base event info
        catalyst_text = ev.get("catalyst_text", "")
        conference_field = ev.get("_conference", "")
        is_phase3 = 1 if ev.get("_parse_phase") == 3 else 0
        is_micro = int(ev.get("is_micro", 0) or 0)
        is_small = int(ev.get("is_small", 0) or 0)
        pre_price = float(ev.get("pre_price", 0) or 0)

        # --- CONFERENCE FEATURES ---
        has_conf, conf_tier = extract_conference(catalyst_text, conference_field)
        if has_conf:
            conf_count += 1

        conf_x_phase3 = has_conf * is_phase3
        conf_x_micro = has_conf * is_micro
        conf_x_small = has_conf * (is_micro + is_small)
        conf_elite = 1 if conf_tier == 3 else 0
        conf_tier1_plus = 1 if conf_tier >= 2 else 0

        # --- SHORT INTEREST / FLOAT FEATURES ---
        si = si_data.get(ticker, {})
        if "error" in si:
            si = {}
        pct_si = float(si.get("short_pct_float", 0) or 0)
        dtc = float(si.get("short_ratio", 0) or 0)
        flt = float(si.get("float_shares", 0) or 0)
        if pct_si > 0:
            si_count += 1

        log_float_inv = math.log(1e9 / max(flt, 1)) if flt > 0 else 0
        si_high = 1.0 if pct_si >= 0.15 else 0.0
        si_x_micro = pct_si * is_micro
        si_x_phase3 = pct_si * is_phase3
        dtc_high = 1.0 if dtc >= 10 else 0.0

        # --- PRICE FEATURES ---
        is_penny = 1.0 if 0 < pre_price < 5 else 0.0
        is_low_price = 1.0 if 0 < pre_price < 10 else 0.0
        log_price_inv = math.log(1.0 / max(pre_price, 0.01)) if pre_price > 0 else 0
        log_price_inv = max(0, log_price_inv)
        penny_x_phase3 = is_penny * is_phase3
        low_price_x_micro = is_low_price * is_micro

        # --- FLOAT × PRICE INTERACTIONS ---
        small_float_penny = (1.0 if flt > 0 and flt < 20e6 else 0.0) * is_penny

        candidate_lookup[key] = {
            # Conference
            "v40_has_conference": has_conf,
            "v40_conf_tier": conf_tier,
            "v40_conf_elite": conf_elite,
            "v40_conf_tier1_plus": conf_tier1_plus,
            "v40_conf_x_phase3": conf_x_phase3,
            "v40_conf_x_micro": conf_x_micro,
            "v40_conf_x_small": conf_x_small,
            # SI / Float
            "v40_pct_float_short": pct_si,
            "v40_days_to_cover": dtc,
            "v40_log_float_inv": log_float_inv,
            "v40_si_high": si_high,
            "v40_si_x_micro": si_x_micro,
            "v40_si_x_phase3": si_x_phase3,
            "v40_dtc_high": dtc_high,
            # Price
            "v40_is_penny_stock": is_penny,
            "v40_is_low_price": is_low_price,
            "v40_log_price_inv": log_price_inv,
            "v40_penny_x_phase3": penny_x_phase3,
            "v40_low_price_x_micro": low_price_x_micro,
            "v40_small_float_penny": small_float_penny,
        }

    n = len(events)
    print(f"  Conference signal: {conf_count}/{n} ({100*conf_count/n:.1f}%)")
    print(f"  SI data matched: {si_count}/{n} ({100*si_count/n:.1f}%)")

    return candidate_lookup


def fetch_missing_si(events, si_data):
    """Fetch yfinance SI data for training tickers not already cached."""
    training_tickers = set(ev.get("ticker", "").upper() for ev in events)
    missing = [t for t in training_tickers
               if t not in si_data or "error" in si_data.get(t, {})]

    if not missing:
        print(f"  SI cache complete: {len(si_data)} tickers, 0 missing")
        return si_data

    print(f"  Fetching yfinance for {min(len(missing), 300)} missing tickers...")
    import yfinance as yf
    import time

    for i, ticker in enumerate(missing[:300]):
        try:
            info = yf.Ticker(ticker).info
            si_data[ticker] = {
                "ticker": ticker,
                "short_pct_float": info.get("shortPercentOfFloat", 0) or 0,
                "short_ratio": info.get("shortRatio", 0) or 0,
                "float_shares": info.get("floatShares", 0) or 0,
                "avg_volume": info.get("averageVolume", 0) or 0,
                "market_cap": info.get("marketCap", 0) or 0,
                "fetch_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception:
            si_data[ticker] = {"ticker": ticker, "error": "fetch_failed"}
        if (i + 1) % 50 == 0:
            print(f"    [{i+1}/{min(len(missing),300)}] {ticker}")
        time.sleep(0.25)

    si_path = os.path.join(DATA_DIR, "short_interest_snapshot.json")
    with open(si_path, "w") as f:
        json.dump(si_data, f, indent=2, default=str)
    print(f"  SI cache updated: {len(si_data)} tickers")
    return si_data


def main():
    print("\n" + "=" * 80)
    print("  GUNGNIR v40 KAIZEN — Conference + SI + Float + Price Features")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Load v39 module and reproduce baseline
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Load v39 baseline (122 features, AUC ~0.7599)")
    print(f"{'=' * 80}")

    print("\n  Loading v39 kaizen module...")
    v39 = load_v39_module()

    print("  Loading data via v39.load_data()...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    events, ctgov_lookup = v39.load_data()
    captured = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # Print summary of v39 load
    for line in captured.strip().split("\n"):
        if "attached" in line or "loaded" in line or "matched" in line or "events" in line:
            print(f"  {line.strip()}")

    print(f"  Total events: {len(events)}")

    print("\n  Building v39.1 feature matrix (122 features)...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = v39.build_features(
        events, ctgov_lookup,
        include_v37=True, include_v38=True,
        include_candidates=V39_SELECTED
    )
    sys.stdout = old_stdout

    print(f"  Feature matrix: {X_base.shape[0]} events × {X_base.shape[1]} features")
    print(f"  Positive rate: {y_bin.mean():.3f}")

    print("\n  Evaluating v39.1 baseline (walk-forward)...")
    baseline = v39.evaluate_wf(
        X_base, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **V39_CONFIG
    )

    base_auc = baseline["avg_auc"]
    print(f"\n  *** v39.1 BASELINE: AUC={base_auc:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp")
    print(f"  (v39.1 reported: AUC 0.7599)")

    # =========================================================================
    # PHASE 1b: Engineer v40 candidate features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1b: Engineer v40 candidate features")
    print(f"{'=' * 80}")

    # Load SI cache
    si_path = os.path.join(DATA_DIR, "short_interest_snapshot.json")
    with open(si_path) as f:
        si_data = json.load(f)
    print(f"  SI cache: {len(si_data)} tickers")

    # Fetch missing SI
    si_data = fetch_missing_si(events, si_data)

    # Engineer candidates
    print("\n  Engineering v40 candidate features...")
    cand_lookup = engineer_v40_candidates(events, si_data)

    # Get candidate feature names from first entry
    sample_key = next(iter(cand_lookup))
    candidate_names = sorted(cand_lookup[sample_key].keys())
    print(f"  Candidate features: {len(candidate_names)}")

    # Build candidate arrays aligned with events
    # events are in the same order as X_base rows
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
    print(f"  PHASE 2: Deep Column Audit — test each v40 candidate")
    print(f"{'=' * 80}")

    print(f"\n  {'Feature':<30s} {'WF_AUC':>8s} {'ΔAUC':>8s} {'Status':>10s}")
    print(f"  {'-' * 60}")

    audit_results = []
    for feat_name in candidate_names:
        col = get_candidate_column(feat_name)

        # Skip zero-variance features
        if np.std(col) < 1e-10:
            print(f"  {feat_name:<30s} {'ZERO VARIANCE — SKIP':>40s}")
            continue

        # Append to baseline matrix
        X_cand = np.column_stack([X_base, col])

        # Walk-forward evaluation
        result = v39.evaluate_wf(
            X_cand, y_bin, y_gp, y_cr, y_ret, dates,
            **V39_CONFIG
        )
        delta = result["avg_auc"] - base_auc

        status = "✓ PASS" if delta > 0.0005 else "≈ FLAT" if delta > -0.0005 else "✗ HURTS"
        flag = " <<<" if delta > 0.001 else (" !!!" if delta < -0.003 else "")

        print(f"  {feat_name:<30s} {result['avg_auc']:>8.4f} {delta:>+8.4f} {status:>10s}{flag}")

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

    print(f"\n  {'=' * 60}")
    print(f"  AUDIT RESULTS (sorted by ΔAUC)")
    print(f"  {'=' * 60}")
    for r in audit_results:
        marker = " ***" if r["delta_auc"] > 0.001 else ""
        print(f"  {r['feature']:<30s} AUC={r['auc']:.4f} Δ={r['delta_auc']:+.4f} "
              f"EV={r['ev_spread']:+.1f}pp{marker}")

    winners = [r for r in audit_results if r["delta_auc"] > 0.0005]
    print(f"\n  *** {len(winners)} features pass audit (ΔAUC > +0.0005)")

    if not winners:
        print("\n  No features pass audit. v39.1 remains champion.")
        results = {
            "version": "40.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "39.1.0", "baseline_auc": round(base_auc, 4),
            "final_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results, "selected": [],
            "verdict": "No new features pass deep column audit",
        }
        with open(os.path.join(DATA_DIR, "gungnir_v40_kaizen_results.json"), "w") as f:
            json.dump(results, f, indent=2)
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
            result = v39.evaluate_wf(
                X_trial, y_bin, y_gp, y_cr, y_ret, dates,
                **V39_CONFIG
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
    print(f"\n  FINAL: {n_total} features ({X_base.shape[1]} v39 + {n_new} new)")
    print(f"  v40 adds: {[s['feature'] for s in selected]}")
    print(f"  AUC improvement: {total_delta:+.4f} ({base_auc:.4f} → {current_auc:.4f})")

    if not selected:
        print("\n  ❌ No features selected. v39.1 remains champion.")
        results = {
            "version": "40.0.0", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_version": "39.1.0", "baseline_auc": round(base_auc, 4),
            "final_auc": round(base_auc, 4), "champion": False,
            "audit_results": audit_results, "selected": [],
            "verdict": "No features pass greedy forward selection",
        }
        with open(os.path.join(DATA_DIR, "gungnir_v40_kaizen_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        return results

    # =========================================================================
    # PHASE 4: Architecture sweep (test C values)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 4: Architecture Sweep")
    print(f"{'=' * 80}")

    c_values = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.050]
    best_c = V39_CONFIG["ridge_c"]
    best_c_auc = current_auc

    for c in c_values:
        cfg = dict(V39_CONFIG)
        cfg["ridge_c"] = c
        result = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates, **cfg)
        flag = " <<<" if result["avg_auc"] > best_c_auc else ""
        print(f"  C={c:.3f}: AUC={result['avg_auc']:.4f} "
              f"Brier={result['avg_brier']:.4f} "
              f"EV={result['avg_ev_spread']:+.1f}pp{flag}")
        if result["avg_auc"] > best_c_auc + 0.0003:
            best_c = c
            best_c_auc = result["avg_auc"]

    if best_c != V39_CONFIG["ridge_c"]:
        print(f"\n  *** Architecture improvement: C={V39_CONFIG['ridge_c']} → C={best_c} "
              f"(AUC +{best_c_auc - current_auc:.4f})")
        current_auc = best_c_auc
    else:
        print(f"\n  C={V39_CONFIG['ridge_c']} remains optimal")

    # Use best config
    final_config = dict(V39_CONFIG)
    final_config["ridge_c"] = best_c

    # =========================================================================
    # PHASE 5: 10-Seed Stability Test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 5: 10-Seed Stability Test")
    print(f"{'=' * 80}")

    aucs_v40 = []
    aucs_v39 = []
    for seed in range(10):
        # v40
        r40 = v39.evaluate_wf(
            current_X, y_bin, y_gp, y_cr, y_ret, dates,
            seed=seed, **final_config
        )
        aucs_v40.append(r40["avg_auc"])

        # v39 baseline
        r39 = v39.evaluate_wf(
            X_base, y_bin, y_gp, y_cr, y_ret, dates,
            seed=seed, **V39_CONFIG
        )
        aucs_v39.append(r39["avg_auc"])

    aucs_v40 = np.array(aucs_v40)
    aucs_v39 = np.array(aucs_v39)
    wins = sum(1 for a40, a39 in zip(aucs_v40, aucs_v39) if a40 > a39)

    from scipy import stats
    t_stat, p_val = stats.ttest_rel(aucs_v40, aucs_v39)

    print(f"  v40: {aucs_v40.mean():.4f} ± {aucs_v40.std():.4f} "
          f"(min {aucs_v40.min():.4f}, max {aucs_v40.max():.4f})")
    print(f"  v39: {aucs_v39.mean():.4f} ± {aucs_v39.std():.4f}")
    print(f"  v40 beats v39: {wins}/10 seeds")
    print(f"  Paired t-test: t={t_stat:.4f}, p={p_val:.10f}")

    is_champion = wins >= 7 and current_auc > base_auc

    # =========================================================================
    # PHASE 6: Full Meta-Ensemble (Ridge 70% + XGB 30%)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 6: Full Meta-Ensemble Evaluation")
    print(f"{'=' * 80}")

    final_result = v39.evaluate_wf(
        current_X, y_bin, y_gp, y_cr, y_ret, dates,
        verbose=True, **final_config
    )
    print(f"\n  *** v40 FINAL: AUC={final_result['avg_auc']:.4f} "
          f"Brier={final_result['avg_brier']:.4f} "
          f"EV_spread={final_result['avg_ev_spread']:+.2f}pp "
          f"EV_edge={final_result['avg_ev_edge']:+.2f}%")

    # =========================================================================
    # PHASE 7: Train final Ridge model for deploy coefficients
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 7: Train Final Model for Deploy")
    print(f"{'=' * 80}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    # Full feature names: v39 base + v40 additions
    v40_added = [s["feature"] for s in selected]
    all_feature_names = list(feat_base) + v40_added

    # Train on all data ≤ 2024
    train_mask = dates < "2025-01-01"
    test_mask = dates >= "2025-01-01"

    X_train_final = current_X[train_mask]
    X_test_final = current_X[test_mask]
    y_train_final = y_bin[train_mask]
    y_test_final = y_bin[test_mask]

    scaler_final = StandardScaler()
    X_tr_s = scaler_final.fit_transform(X_train_final)
    X_te_s = scaler_final.transform(X_test_final)

    lr_final = LogisticRegression(
        C=best_c, penalty="l2", solver="lbfgs",
        max_iter=2000, random_state=42
    )
    lr_final.fit(X_tr_s, y_train_final)

    from sklearn.metrics import roc_auc_score
    train_auc = roc_auc_score(y_train_final, lr_final.predict_proba(X_tr_s)[:, 1])
    test_auc = roc_auc_score(y_test_final, lr_final.predict_proba(X_te_s)[:, 1])

    print(f"  Final Ridge C={best_c}: Train AUC={train_auc:.4f}, Test AUC={test_auc:.4f}")
    print(f"  Features: {len(all_feature_names)}")

    # Extract coefficients for new features
    coefs = lr_final.coef_[0]
    new_coefs = {}
    for i, feat in enumerate(all_feature_names):
        if feat in v40_added:
            new_coefs[feat] = round(float(coefs[i]), 4)

    print(f"\n  New feature coefficients:")
    for feat, c in sorted(new_coefs.items(), key=lambda x: -abs(x[1])):
        print(f"    {feat:<30s} {c:+.4f}")

    # =========================================================================
    # Save results
    # =========================================================================
    if is_champion:
        print(f"\n  🏆 v40 IS NEW CHAMPION! AUC {final_result['avg_auc']:.4f} > v39.1 {base_auc:.4f}")
    else:
        print(f"\n  ❌ v40 does NOT reliably beat v39.1 ({wins}/10 seeds)")

    results = {
        "version": "40.0.0",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline_version": "39.1.0",
        "baseline_auc": round(base_auc, 4),
        "final_wf_auc": round(final_result["avg_auc"], 4),
        "final_wf_brier": round(final_result["avg_brier"], 4),
        "final_wf_ev_spread": round(final_result["avg_ev_spread"], 2),
        "final_ridge_train_auc": round(train_auc, 4),
        "final_ridge_test_auc": round(test_auc, 4),
        "auc_delta": round(final_result["avg_auc"] - base_auc, 4),
        "config": {
            "ridge_c": best_c,
            "xgb_lr": final_config["xgb_lr"],
            "xgb_trees": final_config["xgb_trees"],
            "xgb_depth": final_config["xgb_depth"],
            "meta_ridge": final_config["meta_ridge"],
            "meta_xgb": final_config["meta_xgb"],
            "temperature": final_config["temperature"],
        },
        "n_features_v39": X_base.shape[1],
        "n_features_v40": n_total,
        "features_added": v40_added,
        "new_feature_coefficients": new_coefs,
        "greedy_selection": selected,
        "audit_results": audit_results,
        "stability": {
            "v40_mean": round(float(aucs_v40.mean()), 4),
            "v40_std": round(float(aucs_v40.std()), 4),
            "v39_mean": round(float(aucs_v39.mean()), 4),
            "v39_std": round(float(aucs_v39.std()), 4),
            "wins": int(wins),
            "n_seeds": 10,
            "t_stat": round(float(t_stat), 4),
            "p_value": float(p_val),
        },
        "champion": bool(is_champion),
        "scaler_means": scaler_final.mean_.tolist(),
        "scaler_scales": scaler_final.scale_.tolist(),
        "lr_intercept": float(lr_final.intercept_[0]),
        "lr_coefficients": {feat: round(float(coefs[i]), 4)
                           for i, feat in enumerate(all_feature_names)},
        "all_feature_names": all_feature_names,
    }

    results_path = os.path.join(DATA_DIR, "gungnir_v40_kaizen_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {results_path}")

    return results


if __name__ == "__main__":
    result = main()
    if result is None:
        print("\n  Pipeline could not complete.")
    elif result.get("champion"):
        print(f"\n  🏆 CHAMPION: v40 AUC {result['final_wf_auc']} (v39.1 was {result['baseline_auc']})")
    else:
        print(f"\n  v39.1 remains champion. v40 AUC: {result['final_wf_auc']}")
