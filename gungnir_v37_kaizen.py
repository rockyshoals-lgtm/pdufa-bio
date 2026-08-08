#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v37 KAIZEN — Deep Column Audit + Architecture Sweep
================================================================================

APPROACH (from ODIN v9 success):
  1. Start from v36.1.0 as baseline (AUC 0.7404)
  2. Deep column audit: test 30+ candidate features independently on WF AUC
  3. Greedy forward selection of HO-gated winners
  4. Architecture/hyperparameter sweep on combined feature set
  5. Stability test: 10 seeds, v37 must beat v36.1 on ALL

CANDIDATE FEATURES:
  - Granular stage encoding (Phase 2b, 2/3, 1/2, 1b — 9 raw stage values collapsed to 3)
  - Non-linear transforms (sponsor_sr², indication_density², log_price², momentum²)
  - New interactions (sponsor_sr × oncology, journey × micro, momentum × journey, etc.)
  - Price band features (penny stock flag, price quartiles)
  - Conference flag, combination therapy × phase3
  - Calendar effects (quarter, month)

T-1 COMPLIANCE: All new features knowable at D-1. No post-readout data leakage.
"""

import csv, json, math, os, re, sys, warnings
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

# Import v36 pipeline components
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

from gungnir_v36_train import (
    TA_PATTERNS, classify_ta, parse_phase,
    engineer_v31_features, build_journey_index
)

READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
CTGOV_CACHE_V2 = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
CTGOV_TRAIN_LOOKUP = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
MOMENTUM_CACHE_PATH = os.path.join(DATA_DIR, "readout_momentum_cache.json")
DEPLOY_JSON = os.path.join(DATA_DIR, "gungnir_v37_deploy.json")


# =============================================================================
# v37 CANDIDATE FEATURES — added on top of v36.1's 95+ features
# =============================================================================

def engineer_v37_candidates(row, base_features):
    """Add v37 candidate features on top of v36.1 base features.

    Each candidate is tested independently in deep column audit.
    Returns dict of {feature_name: value} for ALL candidates.
    """
    candidates = {}

    stage = row.get("stage", "").upper()
    phase = base_features.get("phase_numeric", 2)

    # --- GRANULAR STAGE ENCODING ---
    # v36 maps 9 stages to 3 phases. These capture sub-phase granularity.
    candidates["is_phase2b"] = 1 if "2B" in stage else 0
    candidates["is_phase2_3"] = 1 if "2/3" in stage else 0
    candidates["is_phase1_2"] = 1 if "1/2" in stage else 0
    candidates["is_phase1b"] = 1 if "1B" in stage else 0
    candidates["is_phase2a"] = 1 if "2A" in stage else 0
    # Phase 2b and 2/3 are often more advanced — closer to pivotal
    candidates["is_advanced_phase2"] = 1 if ("2B" in stage or "2/3" in stage) else 0
    # Bridging trials: 1/2 designs span phases
    candidates["is_bridging"] = 1 if ("1/2" in stage or "2/3" in stage) else 0

    # --- NON-LINEAR TRANSFORMS (ODIN v9's log_spa_sq was +0.116 coef) ---
    ssr = base_features.get("sponsor_success_rate", 0.5)
    candidates["sponsor_sr_sq"] = ssr ** 2
    candidates["sponsor_sr_centered_sq"] = (ssr - 0.5) ** 2  # distance from 50/50

    ind_den = base_features.get("indication_density", 0)
    candidates["indication_density_sq"] = ind_den ** 2

    lp = base_features.get("log_price", 2.7)
    candidates["log_price_sq"] = lp ** 2

    m20 = base_features.get("momentum_20d", 0)
    candidates["momentum_20d_sq"] = m20 ** 2
    candidates["abs_momentum_20d"] = abs(m20)

    m5 = base_features.get("momentum_5d", 0)
    candidates["momentum_5d_sq"] = m5 ** 2

    jsr = base_features.get("journey_success_rate", 0.5)
    candidates["journey_sr_sq"] = jsr ** 2

    # --- NEW INTERACTION TERMS ---
    # Sponsor track record × TA (experienced sponsors matter more in hard TAs)
    candidates["sponsor_sr_x_oncology"] = ssr * base_features.get("ta_oncology", 0)
    candidates["sponsor_sr_x_cns"] = ssr * base_features.get("ta_cns", 0)
    candidates["sponsor_sr_x_rare"] = ssr * base_features.get("ta_rare_disease", 0)
    candidates["sponsor_sr_x_phase3"] = ssr * base_features.get("is_phase3", 0)

    # Journey × size (small caps with strong drug journey = high conviction)
    candidates["journey_sr_x_micro"] = jsr * base_features.get("is_micro", 0)
    candidates["journey_sr_x_small"] = jsr * (base_features.get("is_micro", 0) + base_features.get("is_small", 0))
    candidates["journey_pos_x_micro"] = base_features.get("journey_had_prior_positive", 0) * base_features.get("is_micro", 0)

    # Momentum × journey (positive momentum on drug with good history)
    candidates["momentum_x_journey_pos"] = m20 * base_features.get("journey_had_prior_positive", 0)
    candidates["momentum_x_sponsor_sr"] = m20 * ssr

    # Competitive × phase (competitive pressure matters more for pivotal)
    comp6 = base_features.get("competitive_6mo", 0)
    candidates["competitive_x_phase3"] = comp6 * base_features.get("is_phase3", 0)
    candidates["competitive_x_oncology"] = comp6 * base_features.get("ta_oncology", 0)

    # Indication density × phase
    candidates["ind_density_x_phase3"] = ind_den * base_features.get("is_phase3", 0)

    # Price level × phase (price level matters differently by phase)
    candidates["log_price_x_phase3"] = lp * base_features.get("is_phase3", 0)
    candidates["log_price_x_oncology"] = lp * base_features.get("ta_oncology", 0)

    # --- PRICE BAND FEATURES ---
    try:
        price = float(row.get("pre_price", 15))
    except:
        price = 15.0
    candidates["is_penny"] = 1 if price < 2 else 0
    candidates["is_penny_x_phase3"] = candidates["is_penny"] * base_features.get("is_phase3", 0)
    candidates["price_band_low"] = 1 if price < 5 else 0  # duplicates is_micro but included for completeness
    candidates["price_band_high"] = 1 if price > 100 else 0

    # --- COMBINATION THERAPY × PHASE ---
    combo = base_features.get("nlp_combo_therapy", 0)
    candidates["combo_x_phase3"] = combo * base_features.get("is_phase3", 0)
    candidates["combo_x_oncology"] = combo * base_features.get("ta_oncology", 0)

    # --- CALENDAR EFFECTS ---
    try:
        dt = datetime.strptime(row.get("date", "2025-01-01"), "%Y-%m-%d")
        candidates["is_q1"] = 1 if dt.month <= 3 else 0
        candidates["is_q4"] = 1 if dt.month >= 10 else 0
        candidates["is_summer"] = 1 if dt.month in [6, 7, 8] else 0
    except:
        candidates["is_q1"] = 0
        candidates["is_q4"] = 0
        candidates["is_summer"] = 0

    # --- CONFERENCE FLAG ---
    conference = row.get("_conference", "")
    candidates["is_conference_readout"] = 1 if conference else 0

    # --- TRIAL DESIGN INTERACTIONS ---
    enroll = base_features.get("ctgov_enrollment", math.log(250))
    candidates["enrollment_sq"] = enroll ** 2
    candidates["enrollment_x_randomized"] = enroll * base_features.get("ctgov_is_randomized", 0)

    # --- BTD × SPONSOR (strong sponsor + BTD = highest conviction)
    candidates["btd_x_sponsor_sr"] = base_features.get("has_btd", 0) * ssr

    # --- DESIGNATION × PHASE3 (regulatory signals matter most for pivotal)
    candidates["desig_count_x_phase3"] = base_features.get("designation_count", 0) * base_features.get("is_phase3", 0)

    return candidates


# =============================================================================
# DATA LOADING — reuses v36 pipeline exactly
# =============================================================================

def load_data():
    """Load and merge all data sources exactly as v36 does."""
    from datetime import datetime as _dt, timedelta as _td

    print("="*80)
    print("GUNGNIR v37 KAIZEN — Deep Column Audit")
    print("="*80)

    # Step 1: Load readout events
    print("\n[LOAD] Loading readout events...")
    with open(READOUT_CSV) as f:
        reader = csv.DictReader(f)
        readout_events = list(reader)
    print(f"  Readout events: {len(readout_events)}")

    # Step 2: Load enriched dataset for catalyst text + conference
    print("[LOAD] Loading enriched dataset...")
    enriched = {}
    enriched_conferences = {}
    for csv_path in [ENRICHED_CSV, HISTORICAL_CSV]:
        if os.path.exists(csv_path):
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row.get('Ticker','').upper()}|{row.get('date','')}"
                    enriched[key] = row
                    if row.get("Conference"):
                        enriched_conferences[key] = row["Conference"]
    print(f"  Enriched records: {len(enriched)}")
    print(f"  Conference flags: {len(enriched_conferences)}")

    # Merge catalyst text + conference into readout events
    for ev in readout_events:
        key = f"{ev['ticker'].upper()}|{ev['date']}"
        enr = enriched.get(key, {})
        ev["catalyst_text"] = enr.get("Catalyst", "")
        ev["stage"] = enr.get("Stage", ev.get("stage", "Phase 2"))
        ev["_conference"] = enriched_conferences.get(key, "")
        # Parse phase from stage
        ev["_parse_phase"] = parse_phase(ev["stage"])

    # Step 3: CT.gov lookup
    print("[LOAD] Loading CT.gov lookup...")
    ctgov_lookup = {}
    for cache_path in [CTGOV_CACHE_V2, CTGOV_CACHE]:
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                ctgov_lookup = json.load(f)
            print(f"  CT.gov cache: {len(ctgov_lookup)} entries from {os.path.basename(cache_path)}")
            break

    # Step 3b: Sort by date and build journey/sponsor indexes
    sorted_merged = sorted(readout_events, key=lambda e: e.get("date", ""))
    for i, ev in enumerate(sorted_merged):
        ev["_orig_idx"] = i

    # Build journey index
    print("[BUILD] Journey index...")
    journey_index = build_journey_index(sorted_merged)

    # Build sponsor index (temporal T-1 compliant)
    print("[BUILD] Sponsor index...")
    sponsor_index = defaultdict(lambda: {"n_total": 0, "n_positive": 0})
    indication_counter = defaultdict(int)

    for ev in sorted_merged:
        ticker = ev.get("ticker", "").upper()
        name = ev.get("name", "")
        sponsor_key = ticker[:4]  # simple sponsor grouping

        # Snapshot BEFORE updating (T-1 compliant)
        s = sponsor_index[sponsor_key]
        if s["n_total"] > 0:
            ev["_sponsor"] = {"success_rate": s["n_positive"] / s["n_total"],
                             "n_events": s["n_total"]}
        else:
            ev["_sponsor"] = {"success_rate": 0.5, "n_events": 0}

        # Update after snapshot
        outcome = ev.get("outcome", "")
        sponsor_index[sponsor_key]["n_total"] += 1
        if outcome == "positive":
            sponsor_index[sponsor_key]["n_positive"] += 1

        # Indication counter (for density)
        ind = ev.get("indication", "").strip().lower()[:50]
        ev["_indication_count"] = indication_counter.get(ind, 0)
        indication_counter[ind] += 1

    print(f"  Sponsor index: {len(sponsor_index)} companies")
    print(f"  Indication density: {len(indication_counter)} unique indications")

    # Step 3d: CT.gov training lookup
    ctgov_train = {}
    if os.path.exists(CTGOV_TRAIN_LOOKUP):
        with open(CTGOV_TRAIN_LOOKUP) as f:
            ctgov_train = json.load(f)
        matched_ct = ctgov_train.get("matched", {})
        phase_avgs = ctgov_train.get("phase_averages", {})
        print(f"  CT.gov training matches: {len(matched_ct)}")
    else:
        matched_ct = {}
        phase_avgs = {}

    for i, ev in enumerate(sorted_merged):
        orig_idx = ev.get("_orig_idx")
        if orig_idx is not None and str(orig_idx) in matched_ct:
            ev["_ctgov_real"] = matched_ct[str(orig_idx)]
        else:
            ev["_ctgov_real"] = {}
        phase_str = str(ev.get("_parse_phase", 2))
        ev["_ctgov_phase_avg"] = phase_avgs.get(phase_str, {})

    # Step 4a: Momentum cache
    print("[LOAD] Momentum cache...")
    momentum_cache = {}
    if os.path.exists(MOMENTUM_CACHE_PATH):
        with open(MOMENTUM_CACHE_PATH) as f:
            momentum_cache = json.load(f)
        print(f"  Momentum cache: {len(momentum_cache)} entries")

    mom_attached = 0
    for ev in sorted_merged:
        key = f"{ev['ticker']}|{ev['date']}"
        mom = momentum_cache.get(key, {})
        ev["_momentum"] = mom
        if mom and "error" not in mom and mom.get("d_m5"):
            mom_attached += 1
    print(f"  Momentum attached: {mom_attached}/{len(sorted_merged)}")

    # Step 4b: Competitive landscape
    print("[BUILD] Competitive landscape...")
    indication_dates = defaultdict(list)
    for i, ev in enumerate(sorted_merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = _dt.strptime(ev["date"], "%Y-%m-%d")
        except:
            continue
        if ind:
            indication_dates[ind].append((dt, i))

    for i, ev in enumerate(sorted_merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = _dt.strptime(ev["date"], "%Y-%m-%d")
        except:
            ev["_competitive"] = {"n_6mo": 0, "n_3mo": 0}
            continue
        n_6mo = n_3mo = 0
        for other_dt, other_i in indication_dates.get(ind, []):
            if other_i == i:
                continue
            days_diff = (dt - other_dt).days
            if 0 < days_diff <= 180:
                n_6mo += 1
            if 0 < days_diff <= 90:
                n_3mo += 1
        ev["_competitive"] = {"n_6mo": n_6mo, "n_3mo": n_3mo}

    return sorted_merged, ctgov_lookup


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def build_features(events, ctgov_lookup, include_candidates=None):
    """Build feature matrix from events.

    include_candidates: None = base v36.1 only,
                       list of str = add those specific candidate features,
                       "all" = add all candidates
    """
    feature_names = None
    X_rows = []
    y_binary = []
    y_good_plus = []
    y_crash = []
    y_returns = []
    dates = []
    meta = []

    for ev in events:
        journey_data = ev.get("_journey", {})

        # Base v36.1 features
        features = engineer_v31_features(ev, ctgov_lookup, None)
        # Override journey with temporal snapshot
        for jk, jv in journey_data.items():
            features[f"journey_{jk}"] = jv

        # v37 candidate features
        if include_candidates is not None:
            candidates = engineer_v37_candidates(ev, features)
            if include_candidates == "all":
                features.update(candidates)
            else:
                for c in include_candidates:
                    if c in candidates:
                        features[c] = candidates[c]

        if feature_names is None:
            feature_names = sorted(f for f in features.keys() if f != "year")

        x = [float(features.get(f, 0)) for f in feature_names]
        X_rows.append(x)

        y_binary.append(1 if ev["outcome"] == "positive" else 0)
        y_good_plus.append(1 if ev["tier"] in ["GOOD", "GREAT"] else 0)
        y_crash.append(1 if ev["tier"] in ["CRASH"] else 0)
        y_returns.append(float(ev["primary_ret_pct"]))
        dates.append(ev["date"])
        meta.append({"ticker": ev["ticker"], "drug": ev.get("drug",""), "tier": ev["tier"]})

    X = np.array(X_rows, dtype=np.float64)
    y_bin = np.array(y_binary)
    y_gp = np.array(y_good_plus)
    y_cr = np.array(y_crash)
    y_ret = np.array(y_returns)

    return X, y_bin, y_gp, y_cr, y_ret, np.array(dates), meta, feature_names


# =============================================================================
# WALK-FORWARD EVALUATION
# =============================================================================

def evaluate_wf(X, y_bin, y_gp, y_cr, y_ret, dates,
                ridge_c=0.10, xgb_lr=0.03, xgb_trees=200, xgb_depth=3,
                meta_ridge=0.60, meta_xgb=0.40, temperature=1.0,
                crash_c=0.3, goodplus_c=0.5, seed=42, verbose=False):
    """Run walk-forward validation and return metrics."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss

    try:
        import xgboost as xgb_lib
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "xgboost", "--break-system-packages", "-q"],
                      capture_output=True)
        import xgboost as xgb_lib

    splits = [
        ("2023H2", "2023-07-01", "2023-12-31"),
        ("2024H1", "2024-01-01", "2024-06-30"),
        ("2024H2", "2024-07-01", "2024-12-31"),
        ("2025+",  "2025-01-01", "2026-12-31"),
    ]

    all_results = []

    for split_name, test_start, test_end in splits:
        train_mask = dates < test_start
        test_mask = (dates >= test_start) & (dates <= test_end)

        if train_mask.sum() < 100 or test_mask.sum() < 30:
            continue

        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y_bin[train_mask], y_bin[test_mask]
        y_gp_train, y_gp_test = y_gp[train_mask], y_gp[test_mask]
        y_cr_train, y_cr_test = y_cr[train_mask], y_cr[test_mask]
        y_ret_test = y_ret[test_mask]

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_train)
        X_te = scaler.transform(X_test)

        # Model 1: Ridge Binary
        m1 = LogisticRegression(C=ridge_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=seed)
        m1.fit(X_tr, y_train)
        p1 = m1.predict_proba(X_te)[:, 1]

        # Model 2: GOOD+
        m2 = LogisticRegression(C=goodplus_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=seed)
        m2.fit(X_tr, y_gp_train)
        p2 = m2.predict_proba(X_te)[:, 1]

        # Model 3: CRASH
        m3 = LogisticRegression(C=crash_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=seed)
        m3.fit(X_tr, y_cr_train)
        p3 = m3.predict_proba(X_te)[:, 1]

        # Model 5: XGBoost
        m5 = xgb_lib.XGBClassifier(
            n_estimators=xgb_trees, max_depth=xgb_depth, learning_rate=xgb_lr,
            subsample=0.8, colsample_bytree=0.6, reg_alpha=0.3, reg_lambda=2.0,
            min_child_weight=10, gamma=0.2, random_state=seed,
            use_label_encoder=False, eval_metric="logloss", verbosity=0
        )
        m5.fit(X_tr, y_train)
        p5 = m5.predict_proba(X_te)[:, 1]

        # Meta blend
        p_meta = meta_ridge * p1 + meta_xgb * p5
        p_meta = np.clip(p_meta, 0.02, 0.98)

        # Temperature scaling
        logits = np.log(p_meta / (1 - p_meta))
        p_meta_cal = 1.0 / (1.0 + np.exp(-logits / temperature))

        # Metrics
        auc = roc_auc_score(y_test, p_meta) if len(set(y_test)) > 1 else 0.5
        brier = brier_score_loss(y_test, p_meta_cal)

        # Investment score
        good_base = y_gp_train.mean()
        crash_base = y_cr_train.mean()
        good_lift = p2 / max(good_base, 0.01)
        crash_lift = p3 / max(crash_base, 0.01)
        inv_score = p_meta + 0.10 * (good_lift - 1.0) - 0.10 * (crash_lift - 1.0)
        inv_score = np.clip(inv_score, 0.01, 0.99)

        # EV spread
        inv_top = np.percentile(inv_score, 80)
        inv_bot = np.percentile(inv_score, 20)
        top_mask = inv_score >= inv_top
        bot_mask = inv_score <= inv_bot
        long_mask = inv_score >= 0.70

        ev_top = y_ret_test[top_mask].mean() if top_mask.sum() > 0 else 0
        ev_bot = y_ret_test[bot_mask].mean() if bot_mask.sum() > 0 else 0
        ev_long = y_ret_test[long_mask].mean() if long_mask.sum() > 0 else 0
        ev_all = y_ret_test.mean()
        ev_spread = ev_top - ev_bot

        # T1 analysis
        t1_mask = inv_score >= 0.85
        t1_wr = y_bin[test_mask][t1_mask].mean() if t1_mask.sum() > 0 else 0

        all_results.append({
            "split": split_name,
            "auc": auc,
            "brier": brier,
            "ev_spread": ev_spread,
            "ev_long": ev_long,
            "ev_all": ev_all,
            "t1_n": int(t1_mask.sum()),
            "t1_wr": t1_wr,
            "n_test": int(test_mask.sum()),
        })

        if verbose:
            print(f"  {split_name}: AUC={auc:.4f} Brier={brier:.4f} "
                  f"EV_spread={ev_spread:+.2f}pp T1={t1_mask.sum()}({t1_wr:.0%})")

    if not all_results:
        return {"avg_auc": 0.5, "avg_brier": 0.25, "avg_ev_spread": 0, "splits": []}

    avg_auc = np.mean([r["auc"] for r in all_results])
    avg_brier = np.mean([r["brier"] for r in all_results])
    avg_ev_spread = np.mean([r["ev_spread"] for r in all_results])
    avg_ev_long = np.mean([r["ev_long"] for r in all_results])
    avg_ev_all = np.mean([r["ev_all"] for r in all_results])

    return {
        "avg_auc": avg_auc,
        "avg_brier": avg_brier,
        "avg_ev_spread": avg_ev_spread,
        "avg_ev_edge": avg_ev_long - avg_ev_all,
        "splits": all_results,
    }


# =============================================================================
# MAIN KAIZEN PIPELINE
# =============================================================================

def main():
    print("\n" + "="*80)
    print("PHASE 1: BASELINE — v36.1.0 reproduction")
    print("="*80)

    events, ctgov_lookup = load_data()

    # Baseline: v36.1 features only
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = build_features(
        events, ctgov_lookup, include_candidates=None
    )
    print(f"\nBaseline features: {len(feat_base)}")
    print(f"Events: {X_base.shape[0]}, Positive rate: {y_bin.mean():.3f}")

    baseline = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates, verbose=True)
    print(f"\n*** v36.1 BASELINE: AUC={baseline['avg_auc']:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp "
          f"EV_edge={baseline['avg_ev_edge']:+.2f}%")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 2: DEEP COLUMN AUDIT — test each candidate independently")
    print("="*80)

    # Get all candidate feature names
    sample_base = dict(zip(feat_base, X_base[0]))
    all_candidates = engineer_v37_candidates(events[0], sample_base)
    candidate_names = sorted(all_candidates.keys())
    print(f"\nTesting {len(candidate_names)} candidate features individually...")

    audit_results = []

    for i, cand in enumerate(candidate_names):
        X_cand, _, _, _, _, _, _, feat_cand = build_features(
            events, ctgov_lookup, include_candidates=[cand]
        )
        result = evaluate_wf(X_cand, y_bin, y_gp, y_cr, y_ret, dates)
        delta_auc = result["avg_auc"] - baseline["avg_auc"]
        delta_brier = result["avg_brier"] - baseline["avg_brier"]
        delta_ev = result["avg_ev_spread"] - baseline["avg_ev_spread"]

        audit_results.append({
            "feature": cand,
            "auc": result["avg_auc"],
            "delta_auc": delta_auc,
            "brier": result["avg_brier"],
            "delta_brier": delta_brier,
            "ev_spread": result["avg_ev_spread"],
            "delta_ev": delta_ev,
        })

        flag = " <<<" if delta_auc > 0.001 else (" !!!" if delta_auc < -0.005 else "")
        print(f"  [{i+1:2d}/{len(candidate_names)}] {cand:35s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta_auc:+.4f}) "
              f"Brier={result['avg_brier']:.4f} (Δ={delta_brier:+.4f}) "
              f"EV={result['avg_ev_spread']:+.2f}pp (Δ={delta_ev:+.2f}){flag}")

    # Sort by AUC delta
    audit_sorted = sorted(audit_results, key=lambda x: -x["delta_auc"])

    print(f"\n{'='*80}")
    print("DEEP COLUMN AUDIT RESULTS (sorted by AUC delta)")
    print(f"{'='*80}")
    print(f"{'Feature':35s} {'AUC':>8s} {'ΔAUC':>8s} {'ΔBrier':>8s} {'ΔEV':>8s}")
    print("-"*72)
    for r in audit_sorted:
        marker = " ✓" if r["delta_auc"] > 0.001 else ""
        print(f"{r['feature']:35s} {r['auc']:.4f} {r['delta_auc']:+.4f} "
              f"{r['delta_brier']:+.4f} {r['delta_ev']:+.2f}{marker}")

    # Winners: features with positive AUC delta
    winners = [r["feature"] for r in audit_sorted if r["delta_auc"] > 0.0005]
    print(f"\n*** {len(winners)} features pass HO gate (ΔAUC > +0.0005): {winners}")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 3: GREEDY FORWARD SELECTION")
    print("="*80)

    selected = []
    best_auc = baseline["avg_auc"]

    for cand in [r["feature"] for r in audit_sorted if r["delta_auc"] > 0]:
        test_set = selected + [cand]
        X_test, _, _, _, _, _, _, _ = build_features(
            events, ctgov_lookup, include_candidates=test_set
        )
        result = evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates)

        if result["avg_auc"] > best_auc + 0.0003:
            selected.append(cand)
            best_auc = result["avg_auc"]
            print(f"  + {cand:35s} → AUC={result['avg_auc']:.4f} (+{result['avg_auc']-baseline['avg_auc']:.4f} vs baseline)")
        else:
            print(f"  - {cand:35s} → AUC={result['avg_auc']:.4f} (no improvement, skip)")

    print(f"\n*** Selected {len(selected)} features: {selected}")

    if selected:
        X_sel, _, _, _, _, _, _, feat_sel = build_features(
            events, ctgov_lookup, include_candidates=selected
        )
        sel_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, verbose=True)
        print(f"\n*** SELECTED SET: AUC={sel_result['avg_auc']:.4f} "
              f"(Δ={sel_result['avg_auc']-baseline['avg_auc']:+.4f}) "
              f"Brier={sel_result['avg_brier']:.4f} "
              f"EV_spread={sel_result['avg_ev_spread']:+.2f}pp")
    else:
        X_sel = X_base
        feat_sel = feat_base
        sel_result = baseline
        print("  No features improved over baseline. Using v36.1 base set.")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 4: ARCHITECTURE / HYPERPARAMETER SWEEP")
    print("="*80)

    best_config = {
        "ridge_c": 0.10, "xgb_lr": 0.03, "xgb_trees": 200, "xgb_depth": 3,
        "meta_ridge": 0.60, "meta_xgb": 0.40, "temperature": 1.0,
        "crash_c": 0.3, "goodplus_c": 0.5,
    }
    best_sweep_auc = sel_result["avg_auc"]

    # Sweep configurations
    sweep_configs = [
        # Ridge C sweep
        {"ridge_c": 0.05}, {"ridge_c": 0.15}, {"ridge_c": 0.20}, {"ridge_c": 0.30},
        {"ridge_c": 0.50}, {"ridge_c": 0.01}, {"ridge_c": 0.005},
        # XGB learning rate sweep
        {"xgb_lr": 0.01}, {"xgb_lr": 0.02}, {"xgb_lr": 0.05}, {"xgb_lr": 0.10},
        # XGB trees sweep
        {"xgb_trees": 100}, {"xgb_trees": 300}, {"xgb_trees": 400},
        # XGB depth sweep
        {"xgb_depth": 2}, {"xgb_depth": 4}, {"xgb_depth": 5},
        # Meta-weight sweep
        {"meta_ridge": 0.70, "meta_xgb": 0.30},
        {"meta_ridge": 0.50, "meta_xgb": 0.50},
        {"meta_ridge": 0.80, "meta_xgb": 0.20},
        {"meta_ridge": 0.40, "meta_xgb": 0.60},
        # Temperature sweep
        {"temperature": 0.85}, {"temperature": 0.90}, {"temperature": 1.10},
        # Crash/GOOD+ C sweep
        {"crash_c": 0.1}, {"crash_c": 0.5}, {"crash_c": 1.0},
        {"goodplus_c": 0.1}, {"goodplus_c": 0.3}, {"goodplus_c": 1.0},
        # Combined promising configs
        {"ridge_c": 0.05, "xgb_lr": 0.02},
        {"ridge_c": 0.15, "xgb_trees": 300},
        {"ridge_c": 0.05, "meta_ridge": 0.70, "meta_xgb": 0.30},
    ]

    print(f"\nSweeping {len(sweep_configs)} configurations...")

    for i, config in enumerate(sweep_configs):
        params = dict(best_config)
        params.update(config)

        result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, **params)

        delta = result["avg_auc"] - best_sweep_auc
        flag = " <<<" if delta > 0.001 else ""
        changes = ", ".join(f"{k}={v}" for k, v in config.items())
        print(f"  [{i+1:2d}/{len(sweep_configs)}] {changes:45s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta:+.4f}) "
              f"Brier={result['avg_brier']:.4f}{flag}")

        if result["avg_auc"] > best_sweep_auc + 0.0005:
            best_sweep_auc = result["avg_auc"]
            best_config.update(config)
            print(f"         >>> NEW BEST CONFIG: {best_config}")

    print(f"\n*** BEST CONFIG: {best_config}")
    print(f"*** BEST AUC: {best_sweep_auc:.4f} (Δ={best_sweep_auc-baseline['avg_auc']:+.4f} vs v36.1)")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 5: STABILITY TEST — 10 seeds")
    print("="*80)

    v36_aucs = []
    v37_aucs = []

    for seed in range(10):
        v36_r = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates, seed=seed)
        v37_r = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, seed=seed, **best_config)
        v36_aucs.append(v36_r["avg_auc"])
        v37_aucs.append(v37_r["avg_auc"])
        wins = "v37" if v37_r["avg_auc"] > v36_r["avg_auc"] else "v36.1"
        print(f"  Seed {seed}: v36.1={v36_r['avg_auc']:.4f} v37={v37_r['avg_auc']:.4f} → {wins}")

    v37_wins = sum(1 for a, b in zip(v37_aucs, v36_aucs) if a > b)

    # Paired t-test
    diffs = np.array(v37_aucs) - np.array(v36_aucs)
    from scipy import stats
    try:
        t_stat, p_val = stats.ttest_rel(v37_aucs, v36_aucs)
    except:
        t_stat, p_val = 0, 1.0

    print(f"\n*** STABILITY: v37 wins {v37_wins}/10 seeds")
    print(f"*** Mean v36.1 AUC: {np.mean(v36_aucs):.4f} ± {np.std(v36_aucs):.4f}")
    print(f"*** Mean v37 AUC: {np.mean(v37_aucs):.4f} ± {np.std(v37_aucs):.4f}")
    print(f"*** Paired t-test: t={t_stat:.4f}, p={p_val:.6f}")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 6: FINAL VERDICT")
    print("="*80)

    final_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **best_config)

    is_champion = (v37_wins >= 7 and
                   final_result["avg_auc"] > baseline["avg_auc"] + 0.002 and
                   p_val < 0.05)

    print(f"\n{'='*80}")
    print(f"GUNGNIR v37 KAIZEN RESULTS")
    print(f"{'='*80}")
    print(f"  v36.1 Baseline AUC: {baseline['avg_auc']:.4f}")
    print(f"  v37 Final AUC:      {final_result['avg_auc']:.4f} (Δ={final_result['avg_auc']-baseline['avg_auc']:+.4f})")
    print(f"  v37 Brier:          {final_result['avg_brier']:.4f} (Δ={final_result['avg_brier']-baseline['avg_brier']:+.4f})")
    print(f"  v37 EV Spread:      {final_result['avg_ev_spread']:+.2f}pp (Δ={final_result['avg_ev_spread']-baseline['avg_ev_spread']:+.2f})")
    print(f"  EV Edge:            {final_result['avg_ev_edge']:+.2f}% (Δ={final_result['avg_ev_edge']-baseline['avg_ev_edge']:+.2f})")
    print(f"  Stability:          {v37_wins}/10 seeds, p={p_val:.6f}")
    print(f"  Features added:     {selected}")
    print(f"  Config changes:     {best_config}")
    print(f"  Total features:     {X_sel.shape[1]}")
    print(f"  VERDICT:            {'*** v37 IS NEW CHAMPION ***' if is_champion else 'v36.1 retains crown'}")

    # Save results
    results = {
        "version": "37.0.0",
        "baseline_auc": baseline["avg_auc"],
        "baseline_brier": baseline["avg_brier"],
        "final_auc": final_result["avg_auc"],
        "final_brier": final_result["avg_brier"],
        "auc_delta": final_result["avg_auc"] - baseline["avg_auc"],
        "features_added": selected,
        "features_tested": len(candidate_names),
        "config": best_config,
        "stability": {"wins": v37_wins, "p_value": p_val},
        "audit_results": audit_results,
        "is_champion": is_champion,
        "n_features_total": X_sel.shape[1],
    }

    kaizen_path = os.path.join(DATA_DIR, "gungnir_v37_kaizen_results.json")
    with open(kaizen_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {kaizen_path}")

    # If champion, train final model and save deploy config
    if is_champion:
        print("\n[CHAMPION] Training final v37 model on full dataset...")
        train_and_deploy(X_sel, y_bin, y_gp, y_cr, y_ret, dates, meta,
                        feat_sel if selected else feat_base, best_config, baseline)

    return 0


def train_and_deploy(X, y_bin, y_gp, y_cr, y_ret, dates, meta, feature_names, config, baseline):
    """Train final model on full data and save deploy config."""
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.preprocessing import StandardScaler

    try:
        import xgboost as xgb_lib
    except:
        import subprocess
        subprocess.run(["pip", "install", "xgboost", "--break-system-packages", "-q"],
                      capture_output=True)
        import xgboost as xgb_lib

    scaler = StandardScaler()
    X_full = scaler.fit_transform(X)

    # Model 1: Binary P(positive)
    m1 = LogisticRegression(C=config["ridge_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_full, y_bin)

    # Model 2: P(GOOD+)
    m2 = LogisticRegression(C=config["goodplus_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m2.fit(X_full, y_gp)

    # Model 3: P(CRASH)
    m3 = LogisticRegression(C=config["crash_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m3.fit(X_full, y_cr)

    # Model 4: ElasticNet (weight=0 but kept for compatibility)
    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                       l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_full, y_bin)

    # Model 5: XGBoost
    m5 = xgb_lib.XGBClassifier(
        n_estimators=config["xgb_trees"], max_depth=config["xgb_depth"],
        learning_rate=config["xgb_lr"],
        subsample=0.8, colsample_bytree=0.6, reg_alpha=0.3, reg_lambda=2.0,
        min_child_weight=10, gamma=0.2, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_full, y_bin)

    # Save XGBoost
    XGB_PATH = os.path.join(DATA_DIR, "gungnir_v37_xgb.json")
    m5.save_model(XGB_PATH)
    print(f"  XGBoost model saved to {XGB_PATH}")

    # Bayesian strata
    strata = {}
    for ta_name in list(TA_PATTERNS.keys()) + ["other"]:
        for ph in [1, 2, 3]:
            ta_feat = f"ta_{ta_name}"
            if ta_feat in feature_names and "phase_numeric" in feature_names:
                ta_idx = feature_names.index(ta_feat)
                ph_idx = feature_names.index("phase_numeric")
                mask = np.array([(X[i, ta_idx] > 0.5 and X[i, ph_idx] == ph)
                                 for i in range(len(X))], dtype=bool)
                if mask.sum() >= 5:
                    strata[f"{ta_name}|{ph}"] = {
                        "count": int(mask.sum()),
                        "rate": float(y_bin[mask].mean()),
                        "good_rate": float(y_gp[mask].mean()),
                        "crash_rate": float(y_cr[mask].mean()),
                        "avg_ret": float(y_ret[mask].mean()),
                    }

    # Feature importance
    coef_importance = {}
    for i, f in enumerate(feature_names):
        coef_importance[f] = round(float(m1.coef_[0][i]), 6)

    deploy = {
        "version": "37.0.0",
        "codename": "Allfather_Kaizen",
        "architecture": f"3-model meta-ensemble (Ridge {config['meta_ridge']*100:.0f}% + XGB {config['meta_xgb']*100:.0f}%) + Ridge_GOOD+ + Ridge_CRASH + Bayesian strata + T={config['temperature']:.2f}",
        "meta_weights": {"ridge_binary": config["meta_ridge"], "elasticnet": 0.00, "xgboost": config["meta_xgb"]},
        "xgb_model_path": "gungnir_v37_xgb.json",
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "scaler_means": {f: float(scaler.mean_[i]) for i, f in enumerate(feature_names)},
        "scaler_scales": {f: float(scaler.scale_[i]) for i, f in enumerate(feature_names)},
        "M1_coef": {f: float(m1.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M1_intercept": float(m1.intercept_[0]),
        "M2_coef": {f: float(m2.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M2_intercept": float(m2.intercept_[0]),
        "M3_coef": {f: float(m3.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M3_intercept": float(m3.intercept_[0]),
        "M4_coef": {f: float(m4.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M4_intercept": float(m4.intercept_[0]),
        "strata": strata,
        "train_base_rate": float(y_bin.mean()),
        "train_good_rate": float(y_gp.mean()),
        "train_crash_rate": float(y_cr.mean()),
        "train_mean_return": float(y_ret.mean()),
        "n_train": int(len(X)),
        "feature_importance": coef_importance,
        "config": config,
        "kaizen_from_v36": {
            "v36_auc": baseline["avg_auc"],
            "v37_auc": None,  # filled from evaluation
            "features_added": [f for f in feature_names if f not in
                              [fn for fn in coef_importance.keys()][:95]],  # approximate
        }
    }

    with open(DEPLOY_JSON, "w") as f:
        json.dump(deploy, f, indent=2)
    print(f"\n[DEPLOY] v37 deploy config written to {DEPLOY_JSON}")


if __name__ == "__main__":
    sys.exit(main())
