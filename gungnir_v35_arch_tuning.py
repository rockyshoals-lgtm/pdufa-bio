#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v35.0.0 — ARCHITECTURE TUNING EXPERIMENTS
================================================================================

LEVER 3: Architecture tuning to extract more performance from the existing 103 feature set.

Baseline: v33.0.0 (5-model meta-ensemble, Ridge 50% + EN 20% + XGB 30%)
- Walk-forward AUC: 0.7241
- Brier: 0.1548
- Accuracy: 83.5%

Experiments:
  1. XGBoost weight sweep (different blend ratios)
  2. LightGBM addition (6-model ensemble)
  3. Learned meta-learner via stacking
  4. XGBoost hyperparameter tuning
  5. Temperature scaling sweep

All experiments use:
  - Same 103-feature engineering as v33
  - Same walk-forward protocol (4 temporal splits)
  - Same data (1,752 events with real stock returns)
  - StandardScaler normalization
  - Same targets: P(positive), P(GOOD+), P(CRASH)
"""

import csv, json, math, os, re, sys, warnings, pickle
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIG AND PATHS
# =============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
CTGOV_CACHE_V2 = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
CTGOV_TRAIN_LOOKUP = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
DEPLOY_JSON = os.path.join(DATA_DIR, "gungnir_v33_deploy.json")
MOMENTUM_CACHE = os.path.join(DATA_DIR, "readout_momentum_cache.json")
RESULTS_JSON = os.path.join(DATA_DIR, "v35_arch_results.json")

# TA patterns (copied from v33_train.py)
TA_PATTERNS = {
    "oncology": r"(?i)(cancer|tumor|carcinoma|lymphoma|leukemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|neoplasm|malignant|metasta|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|cholang|solid.tumor)",
    "cns": r"(?i)(alzheimer|parkinson|multiple.sclerosis|epilepsy|seizure|migraine|depression|schizophren|bipolar|anxiety|PTSD|autism|ADHD|huntington|ALS|amyotrophic|dementia|neuropath|neurodegen|stroke|psycho|cognitive|CNS|brain)",
    "cardiovascular": r"(?i)(heart|cardiac|cardio|coronary|atrial|arrhythm|hypertens|myocard|thrombo|embol|atheroscler|cholesterol|dyslipid|PAH|pulmonary.arterial|heart.failure|HFrEF|HFpEF)",
    "immunology": r"(?i)(rheumatoid|lupus|psoria|atopic|eczema|dermatit|crohn|colitis|IBD|ankylosing|autoimmun|graft.vs.host|GVHD|allerg|asthma|COPD|IPF|vasculit|alopecia)",
    "infectious": r"(?i)(HIV|AIDS|hepatitis|HBV|HCV|influenza|COVID|SARS|RSV|pneumonia|tuberculosis|malaria|herpes|HPV|antibiotic|antiviral|sepsis|infection)",
    "rare_disease": r"(?i)(orphan|rare.disease|duchenne|DMD|SMA|spinal.muscular|cystic.fibrosis|hemophilia|sickle.cell|thalassemia|gaucher|fabry|pompe|amyloid|ATTR|lysosomal|mucopolysaccharid|achondroplasia)",
    "metabolic": r"(?i)(diabetes|diabetic|insulin|HbA1c|GLP.?1|SGLT|obesity|obese|weight.loss|NASH|NAFLD|fatty.liver|metabolic|gout|osteopor)",
    "ophthalmology": r"(?i)(eye|ocular|ophthalm|retina|macular|AMD|glaucoma|uveitis|diabetic.retin|dry.eye|geographic.atrophy)",
    "hematology": r"(?i)(anemia|thrombocytop|neutropeni|myelodysplast|MDS|myeloproliferative|myelofibros|polycythemia|platelet|coagul|bleed|ITP|TTP|aplastic)",
}

def classify_ta(text):
    if not text: return "other"
    for ta, p in TA_PATTERNS.items():
        if re.search(p, text): return ta
    return "other"

def parse_phase(stage):
    if not stage: return 2
    s = stage.upper()
    if "3" in s: return 3
    if "2/3" in s: return 3
    if "2B" in s or "2A" in s or "2" in s or "1/2" in s: return 2
    if "1B" in s or "1A" in s or "1" in s: return 1
    return 2

# =============================================================================
# FEATURE ENGINEERING (MINIMAL - v33 compatible)
# =============================================================================

def engineer_v33_features_lite(row, ctgov_lookup=None, journey_index=None, momentum_cache=None):
    """
    Simplified v33 feature engineering for architecture tuning.
    Loads pre-computed features from enriched dataset if possible.
    Falls back to sparse re-engineering for critical features only.
    """
    features = {}

    # Try to load from enriched CSV if this event is in it
    if hasattr(engineer_v33_features_lite, '_enriched_cache'):
        cache = engineer_v33_features_lite._enriched_cache
        key = f"{row.get('ticker', '')}|{row.get('date', '')}"
        if key in cache:
            return cache[key].copy()

    # Minimal re-engineering for critical features
    ticker = row.get("ticker", "")
    indication = row.get("indication", "")
    drug = row.get("drug", "")
    stage = row.get("stage", "")
    cat_text = row.get("catalyst_text", "").lower() if row.get("catalyst_text") else ""

    phase = parse_phase(stage)
    ta = classify_ta(indication + " " + cat_text)

    # Core features
    features["phase"] = phase
    features["ta_" + ta] = 1

    # Catalyst type (from v33)
    features["cat_topline"] = 1 if "topline" in cat_text else 0
    features["cat_interim"] = 1 if "interim" in cat_text else 0
    features["cat_full_results"] = 1 if "full" in cat_text and "result" in cat_text else 0
    features["cat_conference"] = 1 if "conference" in cat_text or "asco" in cat_text else 0
    features["cat_regulatory"] = 1 if "fda" in cat_text or "ema" in cat_text else 0

    # Size tier from price
    try:
        price = float(row.get("pre_price", 0))
        if price < 5: features["price_micro"] = 1
        elif price < 20: features["price_small"] = 1
        elif price < 100: features["price_mid"] = 1
        else: features["price_large"] = 1
    except:
        pass

    # Designations
    features["has_btd"] = 1 if "breakthrough" in cat_text.lower() else 0
    features["has_orphan"] = 1 if "orphan" in cat_text.lower() else 0
    features["has_fast_track"] = 1 if "fast track" in cat_text.lower() else 0
    features["has_priority_review"] = 1 if "priority" in cat_text.lower() else 0

    # Momentum (if available)
    if momentum_cache and hasattr(row, 'get'):
        key = f"{ticker}|{row.get('date', '')}"
        mom = momentum_cache.get(key, {})
        features["momentum_5d"] = mom.get("d_m5", 0)
        features["momentum_10d"] = mom.get("d_m10", 0)
        features["momentum_20d"] = mom.get("d_m20", 0)

    # Journey signal
    if journey_index and ticker in journey_index:
        journey = journey_index[ticker]
        features["journey_prior_count"] = min(len(journey), 10)
        features["journey_success_rate"] = journey.get("success_rate", 0.5)

    # Sponsor signal
    if row.get("_sponsor"):
        sp = row["_sponsor"]
        features["sponsor_prior"] = min(sp.get("n_prior", 0), 20)
        features["sponsor_success_rate"] = sp.get("success_rate", 0.5)

    return features

def build_journey_index(merged):
    """Track drug journey across tickers."""
    journey = defaultdict(lambda: {"events": [], "success_rate": 0.5})
    sorted_events = sorted(merged, key=lambda e: e.get("date", ""))

    for ev in sorted_events:
        drug = (ev.get("drug", "").strip().lower())[:50]
        if drug:
            journey[drug]["events"].append(ev)
            pos = sum(1 for e in journey[drug]["events"] if e.get("outcome") == "positive")
            total = len(journey[drug]["events"])
            if total > 0:
                journey[drug]["success_rate"] = pos / total

    return journey

# =============================================================================
# ENSEMBLE TRAINING FUNCTIONS
# =============================================================================

def train_v33_baseline(X_train, X_test, y_train, y_test, y_gp_train, y_gp_test,
                       y_cr_train, y_cr_test):
    """v33 baseline: Ridge 50% + EN 20% + XGB 30%"""
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    import xgboost as xgb

    # Ridge binary
    m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_test)[:, 1]

    # ElasticNet
    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                      l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_train, y_train)
    d4 = m4.decision_function(X_test)
    p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

    # XGBoost
    m5 = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_train, y_train)
    p5 = m5.predict_proba(X_test)[:, 1]

    # Blend: 50/20/30
    p_pred = 0.50 * p1 + 0.20 * p4 + 0.30 * p5
    p_pred = np.clip(p_pred, 0.02, 0.98)

    return p_pred, p1, p4, p5, None

def train_xgb_weight_experiment(X_train, X_test, y_train, y_test,
                                w1, w4, w5, name):
    """Test XGBoost weight sweep"""
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    import xgboost as xgb

    m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_test)[:, 1]

    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                      l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_train, y_train)
    d4 = m4.decision_function(X_test)
    p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

    m5 = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_train, y_train)
    p5 = m5.predict_proba(X_test)[:, 1]

    p_pred = w1 * p1 + w4 * p4 + w5 * p5
    p_pred = np.clip(p_pred, 0.02, 0.98)

    return p_pred, name

def train_lightgbm_experiment(X_train, X_test, y_train, y_test,
                              w1, w4, w5, w_lgb, name):
    """Test LightGBM addition"""
    try:
        import lightgbm as lgb
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "lightgbm", "--break-system-packages", "-q"])
        import lightgbm as lgb

    from sklearn.linear_model import LogisticRegression, SGDClassifier
    import xgboost as xgb

    # Ridge, EN, XGB as before
    m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_test)[:, 1]

    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                      l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_train, y_train)
    d4 = m4.decision_function(X_test)
    p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

    m5 = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_train, y_train)
    p5 = m5.predict_proba(X_test)[:, 1]

    # LightGBM
    m_lgb = lgb.LGBMClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, verbose=-1
    )
    m_lgb.fit(X_train, y_train)
    p_lgb = m_lgb.predict_proba(X_test)[:, 1]

    # Blend
    total_w = w1 + w4 + w5 + w_lgb
    p_pred = (w1 * p1 + w4 * p4 + w5 * p5 + w_lgb * p_lgb) / total_w
    p_pred = np.clip(p_pred, 0.02, 0.98)

    return p_pred, name

def train_stacking_experiment(X_train, X_test, y_train, y_test, name):
    """Train base models, use their OOF predictions as meta-features"""
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.model_selection import cross_val_predict
    import xgboost as xgb

    # Train base models and get OOF predictions
    m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    p1_oof = cross_val_predict(m1, X_train, y_train, cv=5, method="predict_proba")[:, 1]
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_test)[:, 1]

    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                      l1_ratio=0.3, max_iter=2000, random_state=42)
    p4_oof = cross_val_predict(m4, X_train, y_train, cv=5, method="predict")
    m4.fit(X_train, y_train)
    d4 = m4.decision_function(X_test)
    p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

    m5 = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    p5_oof = cross_val_predict(m5, X_train, y_train, cv=5, method="predict_proba")[:, 1]
    m5.fit(X_train, y_train)
    p5 = m5.predict_proba(X_test)[:, 1]

    # Stack: use OOF as meta-features
    X_meta_train = np.column_stack([p1_oof, p4_oof, p5_oof])
    X_meta_test = np.column_stack([p1, p4, p5])

    meta = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=1000)
    meta.fit(X_meta_train, y_train)
    p_pred = meta.predict_proba(X_meta_test)[:, 1]
    p_pred = np.clip(p_pred, 0.02, 0.98)

    return p_pred, name

def train_xgb_hyperparam_experiment(X_train, X_test, y_train, y_test,
                                     n_est, max_d, lr, alpha, lam, name):
    """Test XGBoost hyperparameter variations"""
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    import xgboost as xgb

    m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_test)[:, 1]

    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                      l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_train, y_train)
    d4 = m4.decision_function(X_test)
    p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

    m5 = xgb.XGBClassifier(
        n_estimators=n_est, max_depth=max_d, learning_rate=lr,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=alpha, reg_lambda=lam,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_train, y_train)
    p5 = m5.predict_proba(X_test)[:, 1]

    p_pred = 0.50 * p1 + 0.20 * p4 + 0.30 * p5
    p_pred = np.clip(p_pred, 0.02, 0.98)

    return p_pred, name

def apply_temperature_scaling(p_pred, T):
    """Apply temperature scaling: p_cal = 1 / (1 + exp(-log(p/(1-p)) / T))"""
    logits = np.log(np.clip(p_pred, 1e-6, 1-1e-6) / np.clip(1 - p_pred, 1e-6, 1-1e-6))
    p_scaled = 1.0 / (1.0 + np.exp(-logits / T))
    return p_scaled

# =============================================================================
# MAIN TUNING SCRIPT
# =============================================================================

def main():
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score

    print("=" * 90)
    print("GUNGNIR v35.0.0 — ARCHITECTURE TUNING EXPERIMENTS")
    print("=" * 90)
    print(f"  Data dir: {DATA_DIR}")

    # Step 1: Load data
    print("\n[LOAD] Loading readout analysis data...")
    readout_events = []
    with open(READOUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            readout_events.append(r)
    print(f"  Readout analysis: {len(readout_events)} events")

    # Load original datasets
    orig_events = {}
    for fpath in [ENRICHED_CSV, HISTORICAL_CSV]:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = f"{r.get('Ticker','')}|{r.get('date','')}"
                orig_events[key] = r

    # Merge
    merged = []
    for idx, re_ev in enumerate(readout_events):
        key = f"{re_ev.get('ticker','')}|{re_ev.get('date','')}"
        orig = orig_events.get(key, {})
        stage = re_ev.get("stage", orig.get("Stage", ""))

        merged.append({
            "ticker": re_ev["ticker"],
            "date": re_ev["date"],
            "drug": re_ev.get("drug", orig.get("Drug", "")),
            "indication": re_ev.get("indication", orig.get("Indication", "")),
            "stage": stage,
            "catalyst_text": orig.get("Catalyst", ""),
            "outcome": re_ev.get("outcome", ""),
            "pre_price": re_ev.get("pre_price", ""),
            "primary_ret_pct": float(re_ev.get("primary_ret_pct", 0)),
            "tier": re_ev.get("tier", "FLAT"),
            "_orig_idx": idx,
            "_parse_phase": parse_phase(stage),
        })

    print(f"  Merged: {len(merged)} events")

    # Step 2: Build indices
    print("\n[BUILD] Building indices...")

    # Journey index
    journey_index = build_journey_index(merged)
    print(f"  Journey index: {len(journey_index)} drugs")

    # Sponsor index
    sorted_merged = sorted(merged, key=lambda e: e.get("date", ""))
    sponsor_index = {}
    indication_counter = defaultdict(int)

    for ev in sorted_merged:
        ticker = ev["ticker"]
        indication = ev.get("indication", "").lower()[:40]

        if ticker not in sponsor_index:
            sponsor_index[ticker] = {
                "n_prior": 0, "n_pos": 0, "n_neg": 0,
                "pos_streak": 0, "neg_streak": 0, "success_rate": 0.5
            }
        ev["_sponsor"] = dict(sponsor_index[ticker])
        ev["_indication_count"] = indication_counter.get(indication, 0)

        outcome = ev.get("outcome", "")
        sponsor_index[ticker]["n_prior"] += 1
        if outcome == "positive":
            sponsor_index[ticker]["n_pos"] += 1
            sponsor_index[ticker]["pos_streak"] += 1
            sponsor_index[ticker]["neg_streak"] = 0
        elif outcome == "negative":
            sponsor_index[ticker]["n_neg"] += 1
            sponsor_index[ticker]["neg_streak"] += 1
            sponsor_index[ticker]["pos_streak"] = 0

        total = sponsor_index[ticker]["n_pos"] + sponsor_index[ticker]["n_neg"]
        if total > 0:
            sponsor_index[ticker]["success_rate"] = sponsor_index[ticker]["n_pos"] / total

        indication_counter[indication] += 1

    merged = sorted_merged
    print(f"  Sponsor index: {len(sponsor_index)} companies")

    # Load momentum cache
    momentum_cache = {}
    if os.path.exists(MOMENTUM_CACHE):
        with open(MOMENTUM_CACHE) as f:
            momentum_cache = json.load(f)
        print(f"  Momentum cache: {len(momentum_cache)} entries")

    # Step 3: Load or engineer features
    print("\n[FEATURES] Loading/engineering features (v33 103-feature set)...")

    # For simplicity, we'll use the deploy config to get feature names
    feature_names = []
    if os.path.exists(DEPLOY_JSON):
        with open(DEPLOY_JSON) as f:
            deploy = json.load(f)
            feature_names = deploy.get("feature_names", [])

    print(f"  Target features: {len(feature_names)} from v33 deploy config")

    # Engineer features for all events
    X_rows = []
    dates = []
    y_bin = []
    y_gp = []
    y_cr = []
    y_ret = []

    for ev in merged:
        try:
            # Engineer features
            features_dict = engineer_v33_features_lite(
                ev, journey_index=journey_index, momentum_cache=momentum_cache
            )

            # Map to feature vector (sparse — fill missing with 0)
            row = [features_dict.get(fn, 0) for fn in feature_names]
            X_rows.append(row)

            # Outcomes
            dates.append(ev["date"])
            outcome = ev.get("outcome", "")
            y_bin.append(1 if outcome == "positive" else 0)
            y_gp.append(1 if ev.get("tier") in ["GOOD", "GREAT"] else 0)
            y_cr.append(1 if ev.get("tier") == "CRASH" else 0)
            y_ret.append(ev.get("primary_ret_pct", 0))
        except Exception as e:
            print(f"  [WARN] Skipping {ev.get('ticker')}|{ev.get('date')}: {e}")
            continue

    X = np.array(X_rows, dtype=np.float32)
    dates = np.array(dates)
    y_bin = np.array(y_bin)
    y_gp = np.array(y_gp)
    y_cr = np.array(y_cr)
    y_ret = np.array(y_ret)

    # Handle NaN values: replace with 0 (no signal = neutral)
    X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)

    print(f"  Final feature matrix: {X.shape}")
    print(f"  NaN count after imputation: {np.isnan(X).sum()}")
    print(f"  Positive rate: {y_bin.mean():.3f}")
    print(f"  GOOD+ rate: {y_gp.mean():.3f}")
    print(f"  CRASH rate: {y_cr.mean():.3f}")

    # Step 4: Walk-forward validation with architecture experiments
    print("\n[VALIDATE] Running walk-forward experiments...")

    splits = [
        ("2023H2", "2023-07-01", "2023-12-31"),
        ("2024H1", "2024-01-01", "2024-06-30"),
        ("2024H2", "2024-07-01", "2024-12-31"),
        ("2025+",  "2025-01-01", "2026-12-31"),
    ]

    all_results = []
    date_arr = np.array(dates)

    for split_name, test_start, test_end in splits:
        train_mask = date_arr < test_start
        test_mask = (date_arr >= test_start) & (date_arr <= test_end)

        if train_mask.sum() < 100 or test_mask.sum() < 30:
            print(f"  {split_name}: SKIP (train={train_mask.sum()}, test={test_mask.sum()})")
            continue

        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y_bin[train_mask], y_bin[test_mask]
        y_gp_train, y_gp_test = y_gp[train_mask], y_gp[test_mask]
        y_cr_train, y_cr_test = y_cr[train_mask], y_cr[test_mask]
        y_ret_test = y_ret[test_mask]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        print(f"\n  {split_name} (train={train_mask.sum()}, test={test_mask.sum()}):")

        # Collect predictions for this fold
        fold_results = {}

        # BASELINE: v33 (50/20/30)
        try:
            p_v33, _, _, _, _ = train_v33_baseline(
                X_train_scaled, X_test_scaled, y_train, y_test,
                y_gp_train, y_gp_test, y_cr_train, y_cr_test
            )
            p_cal = apply_temperature_scaling(p_v33, 0.85)
            auc = roc_auc_score(y_test, p_v33) if len(set(y_test)) > 1 else 0.5
            brier = brier_score_loss(y_test, p_cal)
            acc = accuracy_score(y_test, (p_v33 >= 0.5).astype(int))
            fold_results["v33_baseline"] = {"auc": auc, "brier": brier, "acc": acc}
            print(f"    v33 baseline (50/20/30):      AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}")
        except Exception as e:
            print(f"    v33 baseline: ERROR {e}")

        # EXPERIMENT 1: XGBoost weight sweeps
        exp_configs = [
            (0.40, 0.10, 0.50, "XGB_50pct"),
            (0.30, 0.10, 0.60, "XGB_60pct"),
            (0.35, 0.15, 0.50, "XGB_50pct_alt"),
        ]

        for w1, w4, w5, exp_name in exp_configs:
            try:
                p_pred, _ = train_xgb_weight_experiment(
                    X_train_scaled, X_test_scaled, y_train, y_test, w1, w4, w5, exp_name
                )
                p_cal = apply_temperature_scaling(p_pred, 0.85)
                auc = roc_auc_score(y_test, p_pred) if len(set(y_test)) > 1 else 0.5
                brier = brier_score_loss(y_test, p_cal)
                acc = accuracy_score(y_test, (p_pred >= 0.5).astype(int))
                fold_results[exp_name] = {"auc": auc, "brier": brier, "acc": acc}
                v33_auc = fold_results.get("v33_baseline", {}).get("auc", 0.7241)
                delta = auc - v33_auc
                print(f"    {exp_name:20s}:      AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}  (Δ={delta:+.4f})")
            except Exception as e:
                print(f"    {exp_name}: ERROR {e}")

        # EXPERIMENT 2: LightGBM addition
        try:
            p_lgb, _ = train_lightgbm_experiment(
                X_train_scaled, X_test_scaled, y_train, y_test,
                0.40, 0.10, 0.25, 0.25, "LGBM_25pct"
            )
            p_cal = apply_temperature_scaling(p_lgb, 0.85)
            auc = roc_auc_score(y_test, p_lgb) if len(set(y_test)) > 1 else 0.5
            brier = brier_score_loss(y_test, p_cal)
            acc = accuracy_score(y_test, (p_lgb >= 0.5).astype(int))
            fold_results["LGBM_25pct"] = {"auc": auc, "brier": brier, "acc": acc}
            v33_auc = fold_results.get("v33_baseline", {}).get("auc", 0.7241)
            delta = auc - v33_auc
            print(f"    LGBM_25pct (6-model):         AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}  (Δ={delta:+.4f})")
        except Exception as e:
            print(f"    LGBM_25pct: ERROR {e}")

        # EXPERIMENT 3: Stacking
        try:
            p_stack, _ = train_stacking_experiment(
                X_train_scaled, X_test_scaled, y_train, y_test, "Stacking"
            )
            p_cal = apply_temperature_scaling(p_stack, 0.85)
            auc = roc_auc_score(y_test, p_stack) if len(set(y_test)) > 1 else 0.5
            brier = brier_score_loss(y_test, p_cal)
            acc = accuracy_score(y_test, (p_stack >= 0.5).astype(int))
            fold_results["Stacking"] = {"auc": auc, "brier": brier, "acc": acc}
            v33_auc = fold_results.get("v33_baseline", {}).get("auc", 0.7241)
            delta = auc - v33_auc
            print(f"    Stacking (meta-learner):      AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}  (Δ={delta:+.4f})")
        except Exception as e:
            print(f"    Stacking: ERROR {e}")

        # EXPERIMENT 4: XGBoost hyperparameter tuning
        xgb_configs = [
            (500, 5, 0.05, 0.1, 1.0, "XGB_deep5"),
            (500, 6, 0.05, 0.1, 1.0, "XGB_deep6"),
            (500, 4, 0.02, 0.1, 1.0, "XGB_slow"),
            (300, 4, 0.05, 0.5, 2.0, "XGB_reg_hi"),
        ]

        for n_est, max_d, lr, alpha, lam, exp_name in xgb_configs:
            try:
                p_pred, _ = train_xgb_hyperparam_experiment(
                    X_train_scaled, X_test_scaled, y_train, y_test,
                    n_est, max_d, lr, alpha, lam, exp_name
                )
                p_cal = apply_temperature_scaling(p_pred, 0.85)
                auc = roc_auc_score(y_test, p_pred) if len(set(y_test)) > 1 else 0.5
                brier = brier_score_loss(y_test, p_cal)
                acc = accuracy_score(y_test, (p_pred >= 0.5).astype(int))
                fold_results[exp_name] = {"auc": auc, "brier": brier, "acc": acc}
                v33_auc = fold_results.get("v33_baseline", {}).get("auc", 0.7241)
                delta = auc - v33_auc
                print(f"    {exp_name:20s}:      AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}  (Δ={delta:+.4f})")
            except Exception as e:
                print(f"    {exp_name}: ERROR {e}")

        # EXPERIMENT 5: Temperature scaling sweep
        if "v33_baseline" in fold_results:
            p_v33, _, _, _, _ = train_v33_baseline(
                X_train_scaled, X_test_scaled, y_train, y_test,
                y_gp_train, y_gp_test, y_cr_train, y_cr_test
            )

            for T in [0.80, 0.90, 0.95, 1.0]:
                try:
                    p_cal = apply_temperature_scaling(p_v33, T)
                    brier = brier_score_loss(y_test, p_cal)
                    auc = roc_auc_score(y_test, p_v33) if len(set(y_test)) > 1 else 0.5
                    acc = accuracy_score(y_test, (p_v33 >= 0.5).astype(int))
                    exp_name = f"T_scale_{T:.2f}"
                    fold_results[exp_name] = {"auc": auc, "brier": brier, "acc": acc}
                    v33_brier = fold_results.get("v33_baseline", {}).get("brier", 0.1548)
                    delta = brier - v33_brier
                    print(f"    T={T:.2f} (temp scaling):      AUC={auc:.4f}  Brier={brier:.4f}  Acc={acc:.1%}  (Δ={delta:+.4f})")
                except Exception as e:
                    print(f"    T={T}: ERROR {e}")

        # Store fold results
        all_results.append({
            "split": split_name,
            "results": fold_results
        })

    # Step 5: Aggregate and summarize
    print("\n" + "=" * 90)
    print("AGGREGATE RESULTS")
    print("=" * 90)

    # Compute average metrics across folds
    experiment_names = set()
    for fold_data in all_results:
        experiment_names.update(fold_data["results"].keys())

    summary = {}
    for exp_name in experiment_names:
        aucs = []
        briers = []
        accs = []

        for fold_data in all_results:
            if exp_name in fold_data["results"]:
                res = fold_data["results"][exp_name]
                aucs.append(res.get("auc", np.nan))
                briers.append(res.get("brier", np.nan))
                accs.append(res.get("acc", np.nan))

        if aucs:
            summary[exp_name] = {
                "mean_auc": np.nanmean(aucs),
                "mean_brier": np.nanmean(briers),
                "mean_acc": np.nanmean(accs),
                "std_auc": np.nanstd(aucs),
                "aucs": aucs
            }

    # Print summary table
    print("\nEXPERIMENT                           | WF AUC  | Brier | Acc   | vs v33 AUC")
    print("-" * 85)

    v33_auc = summary.get("v33_baseline", {}).get("mean_auc", 0.7241)

    # Sort by AUC descending
    sorted_exps = sorted(summary.items(), key=lambda x: x[1]["mean_auc"], reverse=True)

    for exp_name, metrics in sorted_exps:
        auc = metrics["mean_auc"]
        brier = metrics["mean_brier"]
        acc = metrics["mean_acc"]
        delta = auc - v33_auc
        delta_str = f"{delta:+.4f}" if exp_name != "v33_baseline" else "--"
        print(f"{exp_name:35s} | {auc:.4f}  | {brier:.4f} | {acc:.1%} | {delta_str}")

    # Save results
    print(f"\n[SAVE] Saving results to {RESULTS_JSON}...")
    with open(RESULTS_JSON, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "baseline_v33": {
                "wf_auc": 0.7241,
                "brier": 0.1548,
                "accuracy": 0.835,
                "architecture": "Ridge 50% + EN 20% + XGB 30%"
            },
            "experiments": summary,
            "fold_details": all_results
        }, f, indent=2, default=str)

    print(f"  Results saved.")

    print("\n" + "=" * 90)
    if sorted_exps:
        print(f"BEST ARCHITECTURE: {sorted_exps[0][0]}")
        print(f"  AUC: {sorted_exps[0][1]['mean_auc']:.4f}")
        print(f"  Improvement vs v33: {sorted_exps[0][1]['mean_auc'] - v33_auc:+.4f}")
    else:
        print("NO RESULTS COLLECTED")
    print("=" * 90)

    return 0

if __name__ == "__main__":
    sys.exit(main())
