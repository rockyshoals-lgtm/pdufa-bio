#!/usr/bin/env python3
"""
================================================================================
CATALYST SCORER v36.0.0 — Re-score 2026 Catalysts with Gungnir v36
================================================================================
Loads v36 deploy JSON (103 features: v32.1 + momentum + competitive + XGBoost).
5-model meta-ensemble: Ridge 50% + ElasticNet 20% + XGBoost 30%.

USAGE:
  python catalyst_scorer_v36.py
"""

import csv, json, math, os, re, sys, warnings
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_JSON = os.path.join(DATA_DIR, "gungnir_v36_deploy.json")
XGB_MODEL_PATH = os.path.join(DATA_DIR, "gungnir_v36_xgb.json")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
XLSX_PATH = "/sessions/loving-nifty-dirac/mnt/uploads/fda_2026-03-26.xlsx"
OUTPUT_JSON = os.path.join(DATA_DIR, "catalyst_scores_v36.json")

# =============================================================================
# READOUT EDGE SIGNALS (from 1,752-event stock move analysis)
# =============================================================================
PHASE_SIZE_EDGE = {
    (3, "micro"):  (26.5, 20.8, 9.4),
    (3, "small"):  (18.4, 21.0, 1.7),
    (3, "mid"):    (4.2, 8.0, 1.5),
    (3, "large"):  (-0.0, 2.1, 1.0),
    (2, "micro"):  (18.5, 14.7, 5.6),
    (2, "small"):  (7.0, 11.1, 9.3),
    (2, "mid"):    (1.3, 6.4, 10.9),
    (2, "large"):  (-2.5, 2.8, 7.6),
    (1, "micro"):  (9.2, 14.0, 20.0),
    (1, "small"):  (4.5, 12.5, 18.2),
    (1, "mid"):    (-1.3, 6.4, 10.9),
    (1, "large"):  (-2.5, 2.8, 7.6),
}

TA_PATTERNS = {
    "oncology": r"(?i)(cancer|tumor|carcinoma|lymphoma|leukemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|neoplasm|malignant|metasta|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|cholang|solid.tumor|hematolog)",
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

def parse_phase(stage_str):
    if not stage_str: return None, False
    s = stage_str.upper()
    is_pdufa = "PDUFA" in s or "NDA" in s or "BLA" in s or "SNDA" in s or "BIOSIMILAR" in s
    if "3" in s: return 3, is_pdufa
    if "2B" in s: return 2, is_pdufa
    if "2/3" in s: return 3, is_pdufa
    if "2" in s: return 2, is_pdufa
    if "1/2" in s: return 2, is_pdufa
    if "1" in s: return 1, is_pdufa
    if is_pdufa: return 4, True
    return None, is_pdufa

def size_tier(price):
    if price is None: return "mid"
    if price < 5: return "micro"
    if price < 20: return "small"
    if price < 80: return "mid"
    return "large"


# =============================================================================
# GUNGNIR v36 SCORING ENGINE
# =============================================================================

class GungnirV33:
    """Self-contained v36 scoring engine with XGBoost support."""

    def __init__(self, deploy_path=DEPLOY_JSON, xgb_path=XGB_MODEL_PATH):
        import xgboost as xgb

        with open(deploy_path) as f:
            self.config = json.load(f)
        self.version = self.config["version"]
        self.features = self.config["feature_names"]
        self.n_features = len(self.features)
        self.scaler_means = np.array([self.config["scaler_means"][f] for f in self.features])
        self.scaler_scales = np.array([self.config["scaler_scales"][f] for f in self.features])

        # Linear model weights
        self.m1_coef = np.array([self.config["M1_coef"][f] for f in self.features])
        self.m1_intercept = self.config["M1_intercept"]
        self.m2_coef = np.array([self.config["M2_coef"][f] for f in self.features])
        self.m2_intercept = self.config["M2_intercept"]
        self.m3_coef = np.array([self.config["M3_coef"][f] for f in self.features])
        self.m3_intercept = self.config["M3_intercept"]
        self.m4_coef = np.array([self.config["M4_coef"][f] for f in self.features])
        self.m4_intercept = self.config["M4_intercept"]

        # XGBoost model (v36 NEW)
        self.xgb_model = xgb.XGBClassifier()
        self.xgb_model.load_model(xgb_path)

        self.meta_weights = self.config.get("meta_weights", {"ridge_binary": 0.50, "elasticnet": 0.20, "xgboost": 0.30})
        self.strata = self.config.get("strata", {})
        self.base_rate = self.config["train_base_rate"]
        self.good_rate = self.config["train_good_rate"]
        self.crash_rate = self.config["train_crash_rate"]

    def _sigmoid(self, z):
        return 1.0 / (1.0 + np.exp(-np.clip(z, -20, 20)))

    def score(self, feature_dict):
        """Score a single event. Returns dict with probability, tier, p_good, p_crash."""
        x = np.array([float(feature_dict.get(f, 0)) for f in self.features])

        # Scale
        x_scaled = (x - self.scaler_means) / np.maximum(self.scaler_scales, 1e-10)

        # Model predictions
        p1 = self._sigmoid(x_scaled @ self.m1_coef + self.m1_intercept)  # P(positive) Ridge
        p2 = self._sigmoid(x_scaled @ self.m2_coef + self.m2_intercept)  # P(GOOD+)
        p3 = self._sigmoid(x_scaled @ self.m3_coef + self.m3_intercept)  # P(CRASH)
        p4 = self._sigmoid(x_scaled @ self.m4_coef + self.m4_intercept)  # P(positive) ElasticNet

        # XGBoost P(positive) — v36 NEW
        import xgboost as xgb
        x_xgb = x_scaled.reshape(1, -1)
        p5 = float(self.xgb_model.predict_proba(x_xgb)[0, 1])

        # Meta-ensemble: 50% Ridge + 20% ElasticNet + 30% XGBoost
        w_ridge = self.meta_weights.get("ridge_binary", 0.50)
        w_en = self.meta_weights.get("elasticnet", 0.20)
        w_xgb = self.meta_weights.get("xgboost", 0.30)
        p_meta = w_ridge * p1 + w_en * p4 + w_xgb * p5
        p_meta = np.clip(p_meta, 0.02, 0.98)

        # Temperature scaling
        logit = np.log(p_meta / (1 - p_meta))
        p_cal = float(self._sigmoid(logit / 0.85))

        # Investment score (blends P(pos) + upside - downside)
        good_lift = p2 / max(self.good_rate, 0.01)
        crash_lift = p3 / max(self.crash_rate, 0.01)
        inv_score = float(p_meta + 0.10 * (good_lift - 1.0) - 0.10 * (crash_lift - 1.0))
        inv_score = max(0.01, min(0.99, inv_score))

        # Bayesian strata adjustment
        ta_key = None
        for f in self.features:
            if f.startswith("ta_") and f not in ["ta_base_rate"] and feature_dict.get(f, 0) > 0.5:
                ta_name = f[3:]  # strip "ta_"
                phase_num = feature_dict.get("phase_numeric", 2)
                ta_key = f"{ta_name}|{int(phase_num)}"
                break

        strata_data = self.strata.get(ta_key, {}) if ta_key else {}
        if strata_data:
            strata_rate = strata_data["rate"]
            # Shrink toward strata mean (20% blend)
            p_cal = 0.80 * p_cal + 0.20 * strata_rate

        # Tier assignment
        if p_cal >= 0.85:
            tier, tier_label = "T1", "Strong Long"
        elif p_cal >= 0.70:
            tier, tier_label = "T2", "Cautious Long"
        elif p_cal >= 0.55:
            tier, tier_label = "T3", "Monitor"
        else:
            tier, tier_label = "T4", "Avoid"

        return {
            "probability": round(float(p_cal), 4),
            "tier": tier,
            "tier_label": tier_label,
            "p_good_plus": round(float(p2), 4),
            "p_crash": round(float(p3), 4),
            "inv_score_raw": round(inv_score, 4),
            "strata_applied": ta_key if strata_data else None,
        }


def engineer_v31_features_for_catalyst(event, ctgov_data=None):
    """Engineer v31 features from a catalyst event (T-1 compliant, no outcome leakage)."""
    features = {}

    phase = event.get("phase") or 2
    ta = event.get("ta", "other")
    price = event.get("price")
    cat_text = (event.get("catalyst_text", "") or "").lower()
    stage = (event.get("stage", "") or "").lower()

    if price is None:
        price = 15.0

    # --- PHASE ---
    features["is_phase1"] = 1 if phase == 1 else 0
    features["is_phase2"] = 1 if phase == 2 else 0
    features["is_phase3"] = 1 if phase >= 3 else 0
    features["is_pivotal"] = 1 if phase >= 3 else 0
    features["phase_numeric"] = phase

    # --- TA ---
    for ta_name in ["oncology", "cns", "cardiovascular", "immunology", "infectious",
                     "rare_disease", "metabolic", "ophthalmology", "hematology", "other"]:
        features[f"ta_{ta_name}"] = 1 if ta == ta_name else 0

    ta_rates = {"oncology": 0.55, "cns": 0.45, "rare_disease": 0.60, "metabolic": 0.58,
                "immunology": 0.52, "cardiovascular": 0.48, "infectious": 0.50,
                "ophthalmology": 0.55, "hematology": 0.53, "other": 0.50}
    features["ta_base_rate"] = ta_rates.get(ta, 0.50)

    # --- SIZE ---
    features["log_price"] = math.log(max(price, 0.01))
    features["is_micro"] = 1 if price < 5 else 0
    features["is_small"] = 1 if 5 <= price < 20 else 0
    features["is_mid"] = 1 if 20 <= price < 80 else 0
    features["is_large"] = 1 if price >= 80 else 0

    mcap = event.get("market_cap")
    features["log_market_cap"] = math.log(max(mcap, 1e6)) if mcap and mcap > 0 else math.log(max(price * 50e6, 1e6))

    # --- NLP (T-1 SAFE — pre-readout text features ONLY) ---
    features["nlp_topline"] = 1 if "topline" in cat_text else 0
    features["nlp_interim"] = 1 if "interim" in cat_text else 0
    features["nlp_phase3"] = 1 if re.search(r"phase.?3|pivotal", cat_text) else 0
    features["nlp_dose_response"] = 1 if re.search(r"dose.?response|dose.?escal", cat_text) else 0
    features["nlp_biomarker"] = 1 if re.search(r"biomark|surrogate|ORR|PFS|DFS", cat_text) else 0
    features["nlp_combo_therapy"] = 1 if re.search(r"combin|combo|plus |\\+", cat_text) else 0
    features["nlp_first_in"] = 1 if re.search(r"first.in|novel|first.time", cat_text) else 0

    # --- DESIGNATIONS ---
    combined = cat_text + " " + (event.get("status", "") or "").lower()
    features["has_btd"] = 1 if re.search(r"(breakthrough|BTD)", combined, re.I) else 0
    features["has_fast_track"] = 1 if re.search(r"(fast.track|FTD)", combined, re.I) else 0
    features["has_priority_review"] = 1 if re.search(r"priority.review", combined, re.I) else 0
    features["has_orphan"] = 1 if re.search(r"orphan", combined, re.I) else 0
    features["designation_count"] = sum([features["has_btd"], features["has_fast_track"],
                                          features["has_priority_review"], features["has_orphan"]])

    # --- CATALYST TYPE ---
    next_cat = (event.get("next_catalyst", "") or "").lower()
    features["cat_topline"] = 1 if "topline" in next_cat else 0
    features["cat_interim"] = 1 if "interim" in next_cat else 0
    features["cat_initial"] = 1 if "initial" in next_cat else 0
    features["cat_conference"] = 1 if "conference" in next_cat or "presentation" in next_cat else 0
    features["cat_regulatory"] = 1 if "regulatory" in next_cat or "decision" in next_cat else 0
    features["cat_full_results"] = 1 if "full" in next_cat else 0
    features["cat_submission"] = 1 if "submission" in next_cat or "filing" in next_cat else 0

    # --- JOURNEY (no prior data for future catalysts — use defaults) ---
    features["journey_n_prior"] = 0
    features["journey_success_rate"] = 0.5
    features["journey_had_prior_positive"] = 0
    features["journey_had_prior_negative"] = 0
    features["journey_positive_streak"] = 0
    features["journey_last_positive"] = 0.5
    # Additional journey keys that may be in the feature set
    features["journey_had_positive"] = 0
    features["journey_had_negative"] = 0
    features["journey_n_positive"] = 0
    features["journey_n_negative"] = 0

    # --- HISTORICAL LOA/POP ---
    features["hist_loa"] = (event.get("hist_loa") or 0) / 100.0
    features["hist_pop"] = (event.get("hist_pop") or 0) / 100.0

    # --- CT.GOV ---
    ctgov = ctgov_data or {}
    if "error" in ctgov:
        ctgov = {}

    if ctgov:
        enroll = ctgov.get("enrollment")
        features["ctgov_enrollment"] = math.log(max(enroll, 1)) if enroll else math.log(100)
        features["ctgov_n_arms"] = ctgov.get("n_arms", 2)
        features["ctgov_is_randomized"] = ctgov.get("is_randomized", 0)
        features["ctgov_is_double_blind"] = ctgov.get("is_double_blind", 0)
        features["ctgov_is_placebo"] = ctgov.get("is_placebo", 0)
        features["ctgov_masking_rigor"] = ctgov.get("masking_rigor", 0)
        features["ctgov_has_dmc"] = ctgov.get("has_dmc", 0)
        features["ctgov_ep_hard"] = ctgov.get("ep_hard", 0)
        features["ctgov_ep_surrogate"] = ctgov.get("ep_surrogate", 0)
        features["ctgov_n_sites"] = min(ctgov.get("n_sites", 0), 500)
        features["ctgov_n_countries"] = min(ctgov.get("n_countries", 0), 50)
        features["ctgov_is_global"] = ctgov.get("is_global", 0)
        features["ctgov_has_withdrawals"] = ctgov.get("has_withdrawals", 0)
        features["ctgov_real"] = 1
    else:
        # Phase-average imputation (honest — no hash-based fake data)
        # Averages from real CT.gov training data (886 matched events):
        PHASE_AVG = {
            1: {"enrollment": 146, "n_sites": 13, "n_countries": 2.7, "pct_randomized": 0.63,
                "pct_double_blind": 0.35, "pct_placebo": 0.30, "pct_dmc": 0.55,
                "pct_ep_hard": 0.25, "pct_ep_surrogate": 0.60, "pct_global": 0.20},
            2: {"enrollment": 247, "n_sites": 45, "n_countries": 6.0, "pct_randomized": 0.83,
                "pct_double_blind": 0.55, "pct_placebo": 0.50, "pct_dmc": 0.70,
                "pct_ep_hard": 0.35, "pct_ep_surrogate": 0.50, "pct_global": 0.45},
            3: {"enrollment": 1287, "n_sites": 147, "n_countries": 14.6, "pct_randomized": 0.91,
                "pct_double_blind": 0.72, "pct_placebo": 0.68, "pct_dmc": 0.82,
                "pct_ep_hard": 0.50, "pct_ep_surrogate": 0.35, "pct_global": 0.70},
        }
        pa = PHASE_AVG.get(phase, PHASE_AVG[2])  # default to phase 2 averages
        features["ctgov_enrollment"] = math.log(max(pa["enrollment"], 1))
        features["ctgov_n_arms"] = 2 if phase >= 2 else 1
        features["ctgov_is_randomized"] = round(pa["pct_randomized"])
        features["ctgov_is_double_blind"] = round(pa["pct_double_blind"])
        features["ctgov_is_placebo"] = round(pa["pct_placebo"])
        features["ctgov_masking_rigor"] = 2 if features["ctgov_is_double_blind"] else 0
        features["ctgov_has_dmc"] = round(pa["pct_dmc"])
        features["ctgov_ep_hard"] = round(pa["pct_ep_hard"])
        features["ctgov_ep_surrogate"] = round(pa["pct_ep_surrogate"])
        features["ctgov_n_sites"] = min(pa["n_sites"], 500)
        features["ctgov_n_countries"] = min(pa["n_countries"], 50)
        features["ctgov_is_global"] = 1 if pa["n_countries"] >= 5 else 0
        features["ctgov_has_withdrawals"] = 0
        features["ctgov_real"] = 0

    # --- INTERACTIONS ---
    features["phase3_x_randomized"] = features["is_phase3"] * features["ctgov_is_randomized"]
    features["phase3_x_double_blind"] = features["is_phase3"] * features["ctgov_is_double_blind"]
    features["phase3_x_placebo"] = features["is_phase3"] * features["ctgov_is_placebo"]
    features["phase3_x_cns"] = features["is_phase3"] * features["ta_cns"]
    features["phase3_x_oncology"] = features["is_phase3"] * features["ta_oncology"]
    features["onc_x_single_arm"] = features["ta_oncology"] * (1 if features["ctgov_n_arms"] <= 1 else 0)
    features["rare_x_small"] = features["ta_rare_disease"] * (features["is_micro"] + features["is_small"])
    features["btd_x_phase3"] = features["has_btd"] * features["is_phase3"]
    features["micro_x_phase3"] = features["is_micro"] * features["is_phase3"]
    features["small_x_phase3"] = features["is_small"] * features["is_phase3"]
    features["large_x_any"] = features["is_large"]
    features["desig_x_small"] = features["designation_count"] * (features["is_micro"] + features["is_small"])
    features["ep_hard_x_phase3"] = features["ctgov_ep_hard"] * features["is_phase3"]
    features["dmc_x_phase3"] = features["ctgov_has_dmc"] * features["is_phase3"]
    features["cns_x_micro"] = features["ta_cns"] * features["is_micro"]
    features["journey_pos_x_phase3"] = features["journey_had_prior_positive"] * features["is_phase3"]
    features["journey_sr_x_phase3"] = features["journey_success_rate"] * features["is_phase3"]
    features["journey_streak_x_small"] = features["journey_positive_streak"] * (features["is_micro"] + features["is_small"])
    features["enrollment_x_phase3"] = features["ctgov_enrollment"] * features["is_phase3"]
    features["global_x_phase3"] = features["ctgov_is_global"] * features["is_phase3"]
    features["combo_x_onc"] = features.get("nlp_combo_therapy", 0) * features["ta_oncology"]
    features["micro_x_rare"] = features["is_micro"] * features["ta_rare_disease"]

    # --- v32 NEW: SPONSOR TRACK RECORD + INDICATION DENSITY ---
    features["sponsor_success_rate"] = event.get("_sponsor_sr", 0.5)
    features["indication_density"] = math.log1p(event.get("_indication_count", 0))

    # --- v36 NEW: PRE-READOUT MOMENTUM (T-1 compliant) ---
    # For future catalysts, momentum is 0 (no price data available yet)
    momentum = event.get("_momentum", {})
    if momentum and momentum.get("d_m1"):
        d_m1 = momentum["d_m1"]
        d_m5 = momentum.get("d_m5")
        d_m10 = momentum.get("d_m10")
        d_m20 = momentum.get("d_m20")
        features["momentum_5d"] = (d_m1 / d_m5 - 1) if d_m5 and d_m5 > 0 else 0
        features["momentum_10d"] = (d_m1 / d_m10 - 1) if d_m10 and d_m10 > 0 else 0
        features["momentum_20d"] = (d_m1 / d_m20 - 1) if d_m20 and d_m20 > 0 else 0
        features["volatility_5d"] = abs(features["momentum_5d"])
        features["volatility_20d"] = abs(features["momentum_20d"])
    else:
        features["momentum_5d"] = 0
        features["momentum_10d"] = 0
        features["momentum_20d"] = 0
        features["volatility_5d"] = 0
        features["volatility_20d"] = 0

    # --- v36 NEW: COMPETITIVE LANDSCAPE (T-1 compliant) ---
    comp = event.get("_competitive", {})
    features["competitive_6mo"] = min(comp.get("n_6mo", 0), 20)
    features["competitive_3mo"] = min(comp.get("n_3mo", 0), 10)

    # --- v36 NEW INTERACTIONS ---
    features["momentum_x_phase3"] = features["momentum_5d"] * features["is_phase3"]
    features["momentum_x_micro"] = features["momentum_5d"] * features["is_micro"]
    features["volatility_x_phase3"] = features["volatility_5d"] * features["is_phase3"]
    features["competitive_x_onc"] = features["competitive_6mo"] * features["ta_oncology"]

    # --- ERA ---
    features["era_2024_plus"] = 1

    return features


def compute_investment_score(gungnir_result, event):
    """Compute investment score combining Gungnir probability + readout edge data."""
    prob = gungnir_result["probability"]
    p_good = gungnir_result["p_good_plus"]
    p_crash = gungnir_result["p_crash"]
    phase = event.get("phase") or 2
    stier = event.get("size_tier", "mid")
    ta = event.get("ta", "other")
    is_pdufa = event.get("is_pdufa", False)

    # Edge data lookup
    size_edge = PHASE_SIZE_EDGE.get((min(phase, 3), stier), (0, 5, 10))
    avg_ret_if_positive = size_edge[0]
    good_plus_rate = size_edge[1]
    crash_rate = size_edge[2]

    # Expected value
    neg_avg = {1: -3, 2: -19, 3: -14, 4: -5}.get(phase, -10)
    ev = prob * avg_ret_if_positive + (1 - prob) * neg_avg

    # Investment score (0-100)
    raw_score = (
        prob * 30 +
        max(ev, 0) / 30 * 25 +
        good_plus_rate / 25 * 15 +
        (1 - crash_rate / 50) * 15 +
        p_good * 100 * 10 / 100 +   # Bonus for model-predicted GOOD+
        (1 - p_crash) * 5            # Bonus for low crash risk
    )
    investment_score = max(0, min(100, raw_score))

    # Tier
    if investment_score >= 75: inv_tier, inv_action = "ALPHA", "Strong Long"
    elif investment_score >= 55: inv_tier, inv_action = "BETA", "Cautious Long"
    elif investment_score >= 40: inv_tier, inv_action = "GAMMA", "Watch / Small Position"
    elif investment_score >= 25: inv_tier, inv_action = "DELTA", "Avoid / Very Small"
    else: inv_tier, inv_action = "OMEGA", "No Trade"

    # Position sizing
    if inv_tier == "ALPHA": position = "3-5%" if stier in ["small", "micro"] else "2-3%"
    elif inv_tier == "BETA": position = "2-3%" if stier in ["small", "micro"] else "1-2%"
    elif inv_tier == "GAMMA": position = "1%" if stier in ["small", "micro"] else "0.5%"
    else: position = "0%"

    # Flags
    flags = []
    if stier in ["micro", "small"] and phase >= 3 and prob >= 0.6:
        flags.append("MONSTER_POTENTIAL")
    if ta == "rare_disease" and prob >= 0.55:
        flags.append("RARE_DISEASE_EDGE")
    if ta == "cns" and phase >= 3:
        flags.append("CNS_HIGH_VARIANCE")
    if stier == "large":
        flags.append("LARGE_CAP_MUTED")
    if p_crash >= 0.15:
        flags.append("HIGH_CRASH_RISK")
    if is_pdufa:
        flags.append("PDUFA_EVENT")
    if p_good >= 0.15:
        flags.append("HIGH_UPSIDE_POTENTIAL")

    return {
        "investment_score": round(investment_score, 1),
        "investment_tier": inv_tier,
        "investment_action": inv_action,
        "expected_value": round(ev, 2),
        "avg_ret_if_positive": round(avg_ret_if_positive, 1),
        "good_plus_rate": round(good_plus_rate, 1),
        "crash_rate": round(crash_rate, 1),
        "position_size": position,
        "flags": flags,
    }


# =============================================================================
# IIS (INTERIM INFLATION SCORE) OVERLAY — v1.0
# =============================================================================

IIS_INTERIM_PATTERNS = [
    r"(?i)\binterim\b",
    r"(?i)\bpreliminary\b(?!.*(?:full|final|topline))",
    r"(?i)\binitial\s+(?:data|results|analysis)",
    r"(?i)\bearly\s+(?:data|results|signal|look)",
    r"(?i)\bupdated?\s+(?:data|results|analysis)\b",
    r"(?i)\bpartial\s+(?:data|results)",
    r"(?i)\bfutility\b",
    r"(?i)\bDSMB\b",
]

IIS_COMBINED_DOSE_PATTERNS = [
    r"(?i)\bcombined\s+(?:dose|arm)",
    r"(?i)\bpooled\s+(?:analysis|data|dose|arm)",
    r"(?i)\ball\s+(?:treated|dose|arm).*(?:vs|versus)\s+(?:placebo|control)",
]


def compute_iis_overlay(event, ctgov_data=None):
    """Compute IIS flags for a catalyst event. Returns dict with IIS info."""
    cat_text = (event.get("catalyst_text", "") or "").lower()
    stage = (event.get("stage", "") or "").lower()
    next_cat = (event.get("next_catalyst", "") or "").lower()
    full_text = cat_text + " " + stage + " " + next_cat

    # Detect interim
    is_interim = 0
    interim_evidence = []
    for p in IIS_INTERIM_PATTERNS:
        m = re.search(p, full_text)
        if m:
            is_interim = 1
            interim_evidence.append(m.group())

    # Detect combined dose
    is_combined_dose = 0
    for p in IIS_COMBINED_DOSE_PATTERNS:
        if re.search(p, full_text):
            is_combined_dose = 1

    # N per arm from CT.gov
    n_per_arm = 60  # default
    if ctgov_data and "error" not in ctgov_data:
        enrollment = ctgov_data.get("enrollment") or 0
        n_arms = ctgov_data.get("n_arms") or 2
        if enrollment > 0 and n_arms > 0:
            n_per_arm = round(enrollment / n_arms)

    # Compute IIS score (auto-detectable only — no outcome leakage)
    iis_score = 0
    iis_flags = []

    if is_interim:
        iis_score += 10  # base penalty for all interims
        iis_flags.append("INTERIM_DATA")

        if n_per_arm < 12:
            iis_score += 20
            iis_flags.append("TINY_N_LT_12")
        elif n_per_arm < 20:
            iis_score += 12
            iis_flags.append("TINY_N_LT_20")

        if is_combined_dose:
            iis_score += 15
            iis_flags.append("COMBINED_DOSE")

    elif n_per_arm < 20:
        # Even non-interim with tiny N is worth flagging
        iis_score += 8
        iis_flags.append("SMALL_TRIAL")

    # IIS tier
    if iis_score >= 46:
        iis_tier = "IIS_HIGH"
        position_modifier = 0.0  # NO TRADE
    elif iis_score >= 21:
        iis_tier = "IIS_MODERATE"
        position_modifier = 0.5  # half size
    elif iis_score > 0:
        iis_tier = "IIS_LOW"
        position_modifier = 0.8  # slight reduction
    else:
        iis_tier = "IIS_CLEAR"
        position_modifier = 1.0  # no change

    return {
        "iis_score": iis_score,
        "iis_tier": iis_tier,
        "iis_flags": iis_flags,
        "iis_is_interim": is_interim,
        "iis_n_per_arm": n_per_arm,
        "iis_combined_dose": is_combined_dose,
        "iis_position_modifier": position_modifier,
        "iis_interim_evidence": "; ".join(interim_evidence) if interim_evidence else "",
    }


def main():
    print("=" * 80)
    print("CATALYST SCORER v36.0.0 + IIS v1.0 — 2026 Investment Engine")
    print("=" * 80)

    # Load Gungnir v36
    gungnir = GungnirV33()
    print(f"\n[ENGINE] Gungnir v{gungnir.version} loaded ({gungnir.n_features} features, XGBoost enabled)")

    # Build sponsor track record + indication density from training data
    print("[HISTORY] Building sponsor/indication indexes from training data...")
    sponsor_final = {}   # ticker -> final success_rate (using ALL historical data)
    indication_counts = defaultdict(int)
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            ticker = r.get("ticker", "").strip()
            outcome = r.get("outcome", "")
            indication = r.get("indication", "").lower()[:40]
            if ticker:
                if ticker not in sponsor_final:
                    sponsor_final[ticker] = {"n_pos": 0, "n_neg": 0}
                if outcome == "positive":
                    sponsor_final[ticker]["n_pos"] += 1
                elif outcome == "negative":
                    sponsor_final[ticker]["n_neg"] += 1
            if indication:
                indication_counts[indication] += 1

    # Compute success rates
    sponsor_sr = {}
    for ticker, d in sponsor_final.items():
        total = d["n_pos"] + d["n_neg"]
        sponsor_sr[ticker] = d["n_pos"] / total if total > 0 else 0.5
    print(f"  Sponsors: {len(sponsor_sr)} | Indications: {len(indication_counts)}")

    # Load Excel
    import openpyxl
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    data_rows = rows[1:]
    print(f"[LOAD] {len(data_rows)} catalysts from Excel")

    # Parse events
    events = []
    for r in data_rows:
        ticker = str(r[0] or "").strip()
        if not ticker: continue
        try: price = float(r[2]) if r[2] else None
        except: price = None
        try: mcap = float(r[14]) if r[14] else None
        except: mcap = None

        phase, is_pdufa = parse_phase(str(r[6] or ""))
        ta = classify_ta(str(r[5] or "") + " " + str(r[3] or ""))
        stier = size_tier(price)

        events.append({
            "ticker": ticker,
            "name": str(r[1] or ""),
            "price": price,
            "drug": str(r[3] or ""),
            "nct_id": str(r[4] or "").strip(),
            "indication": str(r[5] or ""),
            "stage": str(r[6] or ""),
            "status": str(r[7] or ""),
            "next_catalyst": str(r[8] or ""),
            "catalyst_date": str(r[9] or ""),
            "catalyst_text": str(r[10] or ""),
            "conference": str(r[11] or ""),
            "hist_loa": (float(r[12]) if r[12] else None) if len(r) > 12 else None,
            "hist_pop": (float(r[13]) if r[13] else None) if len(r) > 13 else None,
            "market_cap": mcap,
            "phase": phase,
            "is_pdufa": is_pdufa,
            "ta": ta,
            "size_tier": stier,
        })

    print(f"[PARSE] {len(events)} events")

    # Load CT.gov cache
    ctgov_cache = {}
    if os.path.exists(CTGOV_CACHE):
        with open(CTGOV_CACHE) as f:
            ctgov_cache = json.load(f)
    print(f"[CTGOV] {len(ctgov_cache)} cached entries")

    # Attach sponsor SR + indication density to events
    for event in events:
        event["_sponsor_sr"] = sponsor_sr.get(event["ticker"], 0.5)
        ind = event.get("indication", "").lower()[:40]
        event["_indication_count"] = indication_counts.get(ind, 0)

    sr_matched = sum(1 for e in events if e["_sponsor_sr"] != 0.5)
    ind_matched = sum(1 for e in events if e["_indication_count"] > 0)
    print(f"  Sponsor SR matched: {sr_matched}/{len(events)} | Indication density matched: {ind_matched}/{len(events)}")

    # Score all events
    print(f"\n[SCORE] Scoring {len(events)} catalysts with Gungnir v36 + IIS overlay...")
    scored = []
    iis_flagged = 0
    for event in events:
        ctgov_data = ctgov_cache.get(event["nct_id"], {})
        features = engineer_v31_features_for_catalyst(event, ctgov_data)
        gungnir_result = gungnir.score(features)
        inv_result = compute_investment_score(gungnir_result, event)

        # IIS overlay
        iis_result = compute_iis_overlay(event, ctgov_data)
        if iis_result["iis_flags"]:
            iis_flagged += 1
            # Adjust position sizing based on IIS
            if iis_result["iis_position_modifier"] < 1.0:
                inv_result["flags"].extend(iis_result["iis_flags"])
                if iis_result["iis_position_modifier"] == 0.0:
                    inv_result["position_size"] = "0% (IIS BLOCK)"
                elif iis_result["iis_position_modifier"] == 0.5:
                    inv_result["flags"].append("IIS_HALF_SIZE")
                elif iis_result["iis_position_modifier"] == 0.8:
                    inv_result["flags"].append("IIS_REDUCED")

        scored.append({
            "ticker": event["ticker"],
            "name": event["name"],
            "drug": event["drug"],
            "indication": event["indication"],
            "stage": event["stage"],
            "status": event["status"],
            "next_catalyst": event["next_catalyst"],
            "catalyst_date": event["catalyst_date"],
            "conference": event["conference"],
            "price": event["price"],
            "market_cap": event["market_cap"],
            "size_tier": event["size_tier"],
            "phase": event["phase"],
            "is_pdufa": event["is_pdufa"],
            "ta": event["ta"],
            "hist_loa": event["hist_loa"],
            "hist_pop": event["hist_pop"],
            "has_ctgov": bool(ctgov_data and "error" not in ctgov_data),
            "gungnir_probability": gungnir_result["probability"],
            "gungnir_tier": gungnir_result["tier"],
            "gungnir_tier_label": gungnir_result["tier_label"],
            "p_good_plus": gungnir_result["p_good_plus"],
            "p_crash": gungnir_result["p_crash"],
            "iis_score": iis_result["iis_score"],
            "iis_tier": iis_result["iis_tier"],
            "iis_flags": iis_result["iis_flags"],
            "iis_is_interim": iis_result["iis_is_interim"],
            "iis_n_per_arm": iis_result["iis_n_per_arm"],
            **inv_result,
        })
    print(f"  IIS flagged: {iis_flagged}/{len(events)} catalysts")

    scored.sort(key=lambda x: -x["investment_score"])

    # Write output
    with open(OUTPUT_JSON, "w") as f:
        json.dump(scored, f, indent=2, default=str)

    # Summary
    tier_counts = Counter(s["investment_tier"] for s in scored)
    print(f"\n{'='*80}")
    print("v36.0 INVESTMENT TIER SUMMARY")
    print(f"{'='*80}")
    for t in ["ALPHA", "BETA", "GAMMA", "DELTA", "OMEGA"]:
        subset = [s for s in scored if s["investment_tier"] == t]
        cnt = len(subset)
        if cnt == 0: continue
        avg_score = sum(s["investment_score"] for s in subset) / cnt
        avg_ev = sum(s["expected_value"] for s in subset) / cnt
        avg_prob = sum(s["gungnir_probability"] for s in subset) / cnt
        print(f"  {t:6s}: {cnt:4d} catalysts  avg_score={avg_score:.1f}  avg_prob={avg_prob:.0%}  avg_EV={avg_ev:+.1f}%")

    print(f"\n  Top 15 Picks:")
    for s in scored[:15]:
        flags = " ".join(f"[{f}]" for f in s.get("flags", []))
        print(f"    {s['investment_score']:5.1f}  {s['investment_tier']:5s}  {s['ticker']:6s}  "
              f"${s['price'] or 0:>8.2f}  P{s['phase'] or '?'}  {s['ta']:12s}  "
              f"Prob={s['gungnir_probability']:.0%}  Good={s['p_good_plus']:.0%}  Crash={s['p_crash']:.0%}  "
              f"EV={s['expected_value']:+.1f}%  {s['drug'][:30]}  {flags}")

    # IIS Summary
    iis_interim = [s for s in scored if s.get("iis_is_interim")]
    iis_small_n = [s for s in scored if s.get("iis_n_per_arm", 999) < 20]
    print(f"\n{'='*80}")
    print("IIS (INTERIM INFLATION SCORE) OVERLAY SUMMARY")
    print(f"{'='*80}")
    print(f"  Interim readouts detected: {len(iis_interim)}")
    print(f"  Small N (<20/arm): {len(iis_small_n)}")
    print(f"  Total IIS-flagged: {iis_flagged}")

    if iis_interim:
        print(f"\n  Interim Catalysts (CAUTION — data may shrink at full readout):")
        for s in sorted(iis_interim, key=lambda x: -x.get("iis_score", 0)):
            flags = " ".join(f"[{f}]" for f in s.get("iis_flags", []))
            print(f"    IIS={s['iis_score']:3d} {s['iis_tier']:12s}  {s['ticker']:8s}  "
                  f"P{s['phase'] or '?'}  {s['ta']:12s}  N/arm={s['iis_n_per_arm']:4d}  "
                  f"Score={s['investment_score']:.1f} {s['investment_tier']}  {s['drug'][:35]}  {flags}")

    print(f"\n[OUTPUT] {len(scored)} scored → {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
