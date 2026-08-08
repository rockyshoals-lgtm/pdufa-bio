#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v35.0.0 — KAIZEN: CT.GOV v35 EXPANSION + XGB_SLOW TUNING
================================================================================

IMPROVEMENTS OVER v33:

LEVER 2: CT.GOV v35 FEATURE ENGINEERING (34 NEW FEATURES)
  - Endpoint granularity (8 binary): ep_is_os, ep_is_pfs, ep_is_orr, ep_is_safety,
    ep_is_biomarker, ep_is_pk_pd, ep_is_qol
  - Endpoint counts (3): num_primary_outcomes, num_secondary_outcomes, num_total_outcomes
  - Trial timing (4): primary_timeframe_days, log_primary_timeframe, time_to_primary_completion,
    time_to_readout_days
  - Trial stringency (5): inclusion_criteria_count, exclusion_criteria_count,
    total_criteria_count, log_elig_text_length, stringency_score
  - Intervention types (5): has_drug, has_biological, has_genetic, has_combination,
    has_active_comparator
  - Comparator design (2): has_sham_comparator, comparator_richness
  - Sponsor type (6): is_industry, is_nih, is_academic, has_industry_collab,
    is_fda_regulated_drug, num_collaborators
  - Enrollment & recruitment (2): is_actual_enrollment, healthy_volunteers
  - Phase x Endpoint interactions (4): phase3_x_os, phase3_x_orr, phase3_x_biomarker, phase2_x_biomarker
  - Oncology interactions (1): onc_x_pk_pd
  - Sponsor x Design interactions (3): industry_x_double_blind, industry_x_randomized, academic_x_single_arm
  - Design x Size interactions (2): stringency_x_large_trial, biomarker_x_enrollment

LEVER 3: XGB_SLOW ARCHITECTURE TUNING
  - XGBoost n_estimators: 300 → 500 (deeper learning)
  - XGBoost learning_rate: 0.05 → 0.02 (slower, more careful steps)
  - All other hyperparameters unchanged
  - Meta-ensemble weights unchanged: Ridge 50% + EN 20% + XGB 30%

EXPECTED IMPACT:
  - 34 new CT.gov features should capture endpoint/trial design signal missed by v33
  - Slower XGBoost should regularize better on smaller feature interactions
  - Total features: 103 (v33) + 34 (new) = 137 features
  - Target: Beat v33 AUC (0.7241) and Brier (0.1548)

TRAINING DATA:
  - 1,752 events with real stock returns (gungnir_readout_analysis.csv)
  - Binary outcome labels + return magnitude tiers
  - CT.gov enrichment with 34 new features via ctgov_v35_features module
  - Full walk-forward validation (4 temporal splits)

T-1 COMPLIANCE: All features knowable at D-1. No post-readout data leakage.
"""

import csv, json, math, os, re, sys, warnings
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
CTGOV_CACHE_V2 = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
CTGOV_TRAIN_LOOKUP = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
V32_ENRICHMENT = os.path.join(DATA_DIR, "gungnir_v32_enrichment.json")
DEPLOY_JSON = os.path.join(DATA_DIR, "gungnir_v35_deploy.json")
CTGOV_T1_DATASET = os.path.join(DATA_DIR, "ctgov_t1_dataset.csv")

# =============================================================================
# IMPORT CT.GOV v35 FEATURE ENGINEERING MODULE
# =============================================================================

try:
    from ctgov_v35_features import get_ctgov_v35_features, load_ctgov_data
    HAS_CTGOV_V35 = True
    print("[IMPORT] ctgov_v35_features module loaded successfully")
except ImportError as e:
    print(f"[WARNING] ctgov_v35_features not found: {e}")
    print("[WARNING] Will create stub function for v35 features")
    HAS_CTGOV_V35 = False

    def get_ctgov_v35_features(row, ctgov_data=None):
        """Stub: return empty feature dict if module not available."""
        return {}

    def load_ctgov_data(path=None):
        """Stub: return empty dict if module not available."""
        return {}

# =============================================================================
# TA CLASSIFICATION (same as v33)
# =============================================================================
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
# FEATURE ENGINEERING — v35 (103 v33 + 34 v35 = 137 features)
# =============================================================================

def engineer_v35_features(row, ctgov_lookup=None, ctgov_v35_data=None, journey_index=None):
    """
    Engineer 137 features: v33 base (103) + v35 CT.gov (34).

    All features from v33 are preserved exactly.
    After v33 features, merge in 34 new v35 CT.gov features.
    """
    features = {}

    # --- BASIC ---
    ticker = row.get("ticker", "")
    indication = row.get("indication", "")
    drug = row.get("drug", "")
    stage = row.get("stage", "")
    cat_text = row.get("catalyst_text", "").lower() if row.get("catalyst_text") else ""
    outcome = row.get("outcome", "")

    phase = parse_phase(stage)
    ta = classify_ta(indication + " " + drug)

    # Price
    pre_price = None
    try:
        pre_price = float(row.get("pre_price", 0))
    except:
        pass
    if not pre_price:
        try:
            pre_price = float(row.get("price", 0))
        except:
            pre_price = 15.0

    # --- PHASE FEATURES ---
    features["is_phase1"] = 1 if phase == 1 else 0
    features["is_phase2"] = 1 if phase == 2 else 0
    features["is_phase3"] = 1 if phase == 3 else 0
    features["is_pivotal"] = 1 if phase >= 3 else 0
    features["phase_numeric"] = phase

    # --- TA FEATURES ---
    features["ta_oncology"] = 1 if ta == "oncology" else 0
    features["ta_cns"] = 1 if ta == "cns" else 0
    features["ta_cardiovascular"] = 1 if ta == "cardiovascular" else 0
    features["ta_immunology"] = 1 if ta == "immunology" else 0
    features["ta_infectious"] = 1 if ta == "infectious" else 0
    features["ta_rare_disease"] = 1 if ta == "rare_disease" else 0
    features["ta_metabolic"] = 1 if ta == "metabolic" else 0
    features["ta_ophthalmology"] = 1 if ta == "ophthalmology" else 0
    features["ta_hematology"] = 1 if ta == "hematology" else 0
    features["ta_other"] = 1 if ta == "other" else 0

    ta_rates = {"oncology":0.55,"cns":0.45,"rare_disease":0.60,"metabolic":0.58,
                "immunology":0.52,"cardiovascular":0.48,"infectious":0.50,
                "ophthalmology":0.55,"hematology":0.53,"other":0.50}
    features["ta_base_rate"] = ta_rates.get(ta, 0.50)

    # --- SIZE FEATURES ---
    features["log_price"] = math.log(max(pre_price, 0.01))
    features["is_micro"] = 1 if pre_price < 5 else 0
    features["is_small"] = 1 if 5 <= pre_price < 20 else 0
    features["is_mid"] = 1 if 20 <= pre_price < 80 else 0
    features["is_large"] = 1 if pre_price >= 80 else 0

    mcap = None
    try:
        mcap = float(row.get("market_cap", 0))
    except:
        pass
    features["log_market_cap"] = math.log(max(mcap, 1e6)) if mcap and mcap > 0 else math.log(max(pre_price * 50e6, 1e6))

    # --- NLP SIGNALS (T-1 SAFE) ---
    features["nlp_topline"] = 1 if "topline" in cat_text else 0
    features["nlp_interim"] = 1 if "interim" in cat_text else 0
    features["nlp_phase3"] = 1 if re.search(r"phase.?3|pivotal", cat_text) else 0
    features["nlp_dose_response"] = 1 if re.search(r"dose.?response|dose.?escal", cat_text) else 0
    features["nlp_biomarker"] = 1 if re.search(r"biomark|surrogate|ORR|PFS|DFS", cat_text) else 0
    features["nlp_combo_therapy"] = 1 if re.search(r"combin|combo|plus |\\+", cat_text) else 0
    features["nlp_first_in"] = 1 if re.search(r"first.in|novel|first.time", cat_text) else 0

    # --- DESIGNATION SIGNALS ---
    status = row.get("status", "").lower() if row.get("status") else ""
    combined = cat_text + " " + status
    features["has_btd"] = 1 if re.search(r"(breakthrough|BTD)", combined, re.I) else 0
    features["has_fast_track"] = 1 if re.search(r"(fast.track|FTD)", combined, re.I) else 0
    features["has_priority_review"] = 1 if re.search(r"priority.review", combined, re.I) else 0
    features["has_orphan"] = 1 if re.search(r"orphan", combined, re.I) else 0
    features["designation_count"] = sum([features["has_btd"], features["has_fast_track"],
                                          features["has_priority_review"], features["has_orphan"]])

    # --- CATALYST TYPE ---
    next_cat = row.get("next_catalyst", "").lower() if row.get("next_catalyst") else ""
    features["cat_topline"] = 1 if "topline" in next_cat else 0
    features["cat_interim"] = 1 if "interim" in next_cat else 0
    features["cat_initial"] = 1 if "initial" in next_cat else 0
    features["cat_conference"] = 1 if "conference" in next_cat or "presentation" in next_cat else 0
    features["cat_regulatory"] = 1 if "regulatory" in next_cat or "decision" in next_cat else 0
    features["cat_full_results"] = 1 if "full" in next_cat else 0
    features["cat_submission"] = 1 if "submission" in next_cat or "filing" in next_cat else 0

    # --- JOURNEY SIGNALS ---
    journey_data = {}
    if journey_index and drug:
        drug_key = re.sub(r"[^a-z0-9]", "", drug.lower())[:20]
        journey_data = journey_index.get(drug_key, {})

    features["journey_n_prior"] = journey_data.get("n_prior", 0)
    features["journey_success_rate"] = journey_data.get("success_rate", 0.5)
    features["journey_had_prior_positive"] = journey_data.get("had_positive", 0)
    features["journey_had_prior_negative"] = journey_data.get("had_negative", 0)
    features["journey_positive_streak"] = math.log1p(journey_data.get("positive_streak", 0))
    features["journey_last_positive"] = journey_data.get("last_positive", 0.5)

    # --- HISTORICAL LOA/POP ---
    try:
        features["hist_loa"] = float(row.get("hist_loa", 0) or 0) / 100.0
    except:
        features["hist_loa"] = 0
    try:
        features["hist_pop"] = float(row.get("hist_pop", 0) or 0) / 100.0
    except:
        features["hist_pop"] = 0

    # --- CT.GOV REAL FEATURES (v33) ---
    ctgov = row.get("_ctgov_real", {})
    if not ctgov:
        nct = row.get("nct_id", "")
        if ctgov_lookup and nct:
            ctgov = ctgov_lookup.get(nct, {})
        if "error" in ctgov:
            ctgov = {}

    if ctgov and ctgov.get("enrollment"):
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
        phase_avg = row.get("_ctgov_phase_avg", {})
        features["ctgov_enrollment"] = math.log(max(phase_avg.get("enrollment", 250), 1))
        features["ctgov_n_arms"] = phase_avg.get("n_arms", 2)
        features["ctgov_is_randomized"] = phase_avg.get("is_randomized", 1 if phase >= 2 else 0)
        features["ctgov_is_double_blind"] = phase_avg.get("is_double_blind", 1 if phase >= 3 else 0)
        features["ctgov_is_placebo"] = phase_avg.get("is_placebo", features["ctgov_is_double_blind"])
        features["ctgov_masking_rigor"] = phase_avg.get("masking_rigor", 2 if features["ctgov_is_double_blind"] else 0)
        features["ctgov_has_dmc"] = phase_avg.get("has_dmc", 1 if phase >= 3 else 0)
        features["ctgov_ep_hard"] = phase_avg.get("ep_hard", 0)
        features["ctgov_ep_surrogate"] = phase_avg.get("ep_surrogate", 1)
        features["ctgov_n_sites"] = phase_avg.get("n_sites", 50)
        features["ctgov_n_countries"] = phase_avg.get("n_countries", 5)
        features["ctgov_is_global"] = phase_avg.get("is_global", 1 if features["ctgov_n_countries"] >= 5 else 0)
        features["ctgov_has_withdrawals"] = 0
        features["ctgov_real"] = 0

    # --- INTERACTION FEATURES (v33) ---
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
    features["journey_pos_x_phase3"] = features.get("journey_had_prior_positive", features.get("journey_had_positive", 0)) * features["is_phase3"]
    features["journey_sr_x_phase3"] = features["journey_success_rate"] * features["is_phase3"]
    features["journey_streak_x_small"] = features["journey_positive_streak"] * (features["is_micro"] + features["is_small"])
    features["enrollment_x_phase3"] = features["ctgov_enrollment"] * features["is_phase3"]
    features["global_x_phase3"] = features["ctgov_is_global"] * features["is_phase3"]
    features["combo_x_onc"] = features.get("nlp_combo_therapy", 0) * features["ta_oncology"]
    features["micro_x_rare"] = features["is_micro"] * features["ta_rare_disease"]

    # --- v32 FEATURES ---
    sponsor_data = row.get("_sponsor", {})
    features["sponsor_success_rate"] = sponsor_data.get("success_rate", 0.5)

    indication_count = row.get("_indication_count", 0)
    features["indication_density"] = math.log1p(indication_count)

    # --- ERA ---
    try:
        yr = int(row.get("date", "2025")[:4])
    except:
        yr = 2025
    features["era_2024_plus"] = 1 if yr >= 2024 else 0
    features["year"] = yr

    # --- v33 NEW: PRE-READOUT MOMENTUM ---
    momentum = row.get("_momentum", {})
    if momentum and "error" not in momentum and momentum.get("d_m1"):
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

    # --- v33 NEW: COMPETITIVE LANDSCAPE ---
    comp = row.get("_competitive", {})
    features["competitive_6mo"] = min(comp.get("n_6mo", 0), 20)
    features["competitive_3mo"] = min(comp.get("n_3mo", 0), 10)

    # --- v33 NEW INTERACTIONS ---
    features["momentum_x_phase3"] = features["momentum_5d"] * features["is_phase3"]
    features["momentum_x_micro"] = features["momentum_5d"] * features["is_micro"]
    features["volatility_x_phase3"] = features["volatility_5d"] * features["is_phase3"]
    features["competitive_x_onc"] = features["competitive_6mo"] * features["ta_oncology"]

    # =========================================================================
    # NEW in v35: ADD 34 CT.GOV v35 FEATURES
    # =========================================================================
    v35_features = get_ctgov_v35_features(row, ctgov_v35_data)
    features.update(v35_features)

    return features


# =============================================================================
# JOURNEY INDEX BUILDER (same as v33)
# =============================================================================

def build_journey_index(events):
    """Build temporal journey index: for each drug, track prior readouts."""
    sorted_events = sorted(events, key=lambda e: e.get("date", ""))
    index = {}

    for ev in sorted_events:
        drug = ev.get("drug", "")
        drug_key = re.sub(r"[^a-z0-9]", "", drug.lower())[:20]
        if not drug_key:
            continue

        if drug_key not in index:
            index[drug_key] = {"n_prior": 0, "n_positive": 0, "n_negative": 0,
                               "had_positive": 0, "had_negative": 0,
                               "positive_streak": 0, "last_positive": 0.5,
                               "success_rate": 0.5}

        state = dict(index[drug_key])
        ev["_journey"] = state

        outcome = ev.get("outcome", "")
        if outcome == "positive":
            index[drug_key]["n_positive"] += 1
            index[drug_key]["had_positive"] = 1
            index[drug_key]["positive_streak"] += 1
            index[drug_key]["last_positive"] = 1.0
        elif outcome == "negative":
            index[drug_key]["n_negative"] += 1
            index[drug_key]["had_negative"] = 1
            index[drug_key]["positive_streak"] = 0
            index[drug_key]["last_positive"] = 0.0
        index[drug_key]["n_prior"] += 1
        total = index[drug_key]["n_positive"] + index[drug_key]["n_negative"]
        if total > 0:
            index[drug_key]["success_rate"] = index[drug_key]["n_positive"] / total

    return index


# =============================================================================
# MAIN TRAINING PIPELINE
# =============================================================================

def main():
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

    try:
        import xgboost as xgb
        HAS_XGB = True
    except ImportError:
        try:
            import subprocess
            subprocess.run(["pip", "install", "xgboost", "--break-system-packages", "-q"])
            import xgboost as xgb
            HAS_XGB = True
        except:
            HAS_XGB = False

    print("=" * 80)
    print("GUNGNIR v35.0.0 — KAIZEN: CT.GOV v35 EXPANSION + XGB_SLOW TUNING")
    print("=" * 80)
    if not HAS_XGB:
        print("  ERROR: XGBoost is REQUIRED. Install with: pip install xgboost")
        return 1
    print(f"  XGBoost: available")

    # Step 1: Load readout analysis data
    print("\n[LOAD] Loading readout analysis data...")
    readout_events = []
    with open(READOUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            readout_events.append(r)
    print(f"  Readout analysis: {len(readout_events)} events with real returns")

    # Load original datasets
    orig_events = {}
    for fpath in [ENRICHED_CSV, HISTORICAL_CSV]:
        if os.path.exists(fpath):
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
            "nct_id": "",
            "_orig_idx": idx,
            "_parse_phase": parse_phase(stage),
        })

    print(f"  Merged events: {len(merged)}")

    # Step 2: Load CT.gov v35 data
    print("\n[CT.GOV v35] Loading CT.gov v35 feature data...")
    ctgov_v35_data = {}
    if HAS_CTGOV_V35 and os.path.exists(CTGOV_T1_DATASET):
        ctgov_v35_data = load_ctgov_data(CTGOV_T1_DATASET)
        print(f"  CT.gov v35 dataset: {len(ctgov_v35_data)} trials loaded")
    else:
        print(f"  [WARNING] CT.gov v35 data not available; will use zeros")

    # Step 3: Build sponsor/indication indices and load CT.gov
    print("\n[INDEX] Building sponsor/indication indices...")
    from datetime import datetime as _dt, timedelta as _td

    sorted_merged = sorted(merged, key=lambda e: e.get("date", ""))
    # === T-1 COMPLIANT temporal snapshotting (matches v33 pattern) ===
    # For each event in chronological order:
    #   1. Snapshot sponsor state BEFORE this event
    #   2. Snapshot indication count BEFORE this event
    #   3. THEN update indices with this event's outcome
    sponsor_index = {}  # ticker -> accumulated stats
    indication_counter = defaultdict(int)

    for ev in sorted_merged:
        ticker = ev.get("ticker", "").strip().lower()
        indication = ev.get("indication", "").strip().lower()

        # Snapshot sponsor state BEFORE this event (T-1 compliant)
        if ticker not in sponsor_index:
            sponsor_index[ticker] = {"n_prior": 0, "n_pos": 0, "n_neg": 0,
                                     "pos_streak": 0, "neg_streak": 0, "success_rate": 0.5}
        ev["_sponsor"] = dict(sponsor_index[ticker])

        # Snapshot indication count BEFORE this event
        ev["_indication_count"] = indication_counter.get(indication, 0)

        # Update sponsor index with this event's outcome (for FUTURE events)
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

        # Update indication counter (for FUTURE events)
        indication_counter[indication] += 1

    print(f"  Sponsor index: {len(sponsor_index)} companies tracked")
    print(f"  Indication density: {len(indication_counter)} unique indications")

    # Load CT.gov training lookup
    ctgov_train = {}
    if os.path.exists(CTGOV_TRAIN_LOOKUP):
        with open(CTGOV_TRAIN_LOOKUP) as f:
            ctgov_train = json.load(f)
        matched_ct = ctgov_train.get("matched", {})
        phase_avgs = ctgov_train.get("phase_averages", {})
        print(f"  Real CT.gov matches: {len(matched_ct)} events")
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

    merged = sorted_merged

    # Sponsor data and indication counts already attached via T-1 temporal snapshotting above
    # (No second pass needed — each event already has _sponsor and _indication_count)

    # Step 4: Load momentum cache
    print("\n[MOMENTUM] Loading pre-readout momentum data...")
    MOMENTUM_CACHE = os.path.join(DATA_DIR, "readout_momentum_cache.json")
    momentum_cache = {}
    if os.path.exists(MOMENTUM_CACHE):
        with open(MOMENTUM_CACHE) as f:
            momentum_cache = json.load(f)
        print(f"  Momentum cache: {len(momentum_cache)} entries")

    for ev in merged:
        key = f"{ev['ticker']}|{ev['date']}"
        mom = momentum_cache.get(key, {})
        ev["_momentum"] = mom

    # Step 5: Build competitive landscape
    print("\n[COMPETITIVE] Building competitive landscape index...")
    indication_dates = defaultdict(list)
    for i, ev in enumerate(merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = _dt.strptime(ev["date"], "%Y-%m-%d")
        except:
            continue
        if ind:
            indication_dates[ind].append((dt, i))

    for i, ev in enumerate(merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = _dt.strptime(ev["date"], "%Y-%m-%d")
        except:
            ev["_competitive"] = {"n_6mo": 0, "n_3mo": 0}
            continue

        n_6mo = 0
        n_3mo = 0
        for other_dt, other_i in indication_dates.get(ind, []):
            if other_i == i:
                continue
            days_diff = (dt - other_dt).days
            if 0 < days_diff <= 180:
                n_6mo += 1
            if 0 < days_diff <= 90:
                n_3mo += 1
        ev["_competitive"] = {"n_6mo": n_6mo, "n_3mo": n_3mo}

    # Step 6: Build journey index
    print("\n[JOURNEY] Building temporal journey index...")
    journey_index = build_journey_index(merged)

    # Step 7: Engineer features (v33 + v35)
    print("\n[ENGINEER] Building v35 feature vectors (v33 base + 34 v35 CT.gov features)...")
    feature_names = None
    X_rows = []
    y_binary = []
    y_good_plus = []
    y_crash = []
    y_returns = []
    dates = []
    meta = []

    for ev in merged:
        journey_data = ev.get("_journey", {})

        features = engineer_v35_features(ev, ctgov_lookup=None, ctgov_v35_data=ctgov_v35_data, journey_index=None)
        for jk, jv in journey_data.items():
            features[f"journey_{jk}"] = jv

        if feature_names is None:
            feature_names = sorted(features.keys())
            feature_names = [f for f in feature_names if f not in ["year"]]

        x = [float(features.get(f, 0)) for f in feature_names]
        X_rows.append(x)

        y_binary.append(1 if ev["outcome"] == "positive" else 0)
        y_good_plus.append(1 if ev["tier"] in ["GOOD", "GREAT"] else 0)
        y_crash.append(1 if ev["tier"] in ["CRASH"] else 0)
        y_returns.append(ev["primary_ret_pct"])
        dates.append(ev["date"])
        meta.append({"ticker": ev["ticker"], "drug": ev["drug"], "tier": ev["tier"]})

    X = np.array(X_rows, dtype=np.float64)
    y_bin = np.array(y_binary)
    y_gp = np.array(y_good_plus)
    y_cr = np.array(y_crash)
    y_ret = np.array(y_returns)

    print(f"  Features: {len(feature_names)}")
    print(f"  Events: {X.shape[0]}")
    print(f"  Positive rate: {y_bin.mean():.3f}")
    print(f"  GOOD+ rate: {y_gp.mean():.3f}")
    print(f"  CRASH rate: {y_cr.mean():.3f}")
    print(f"  Mean return: {y_ret.mean():+.2f}%")

    # Step 8: Walk-forward temporal validation
    print("\n[VALIDATE] Walk-forward temporal validation...")
    splits = [
        ("2023H2", "2023-07-01", "2023-12-31"),
        ("2024H1", "2024-01-01", "2024-06-30"),
        ("2024H2", "2024-07-01", "2024-12-31"),
        ("2025+",  "2025-01-01", "2026-12-31"),
    ]

    date_arr = np.array(dates)
    all_results = []

    for split_name, test_start, test_end in splits:
        train_mask = date_arr < test_start
        test_mask = (date_arr >= test_start) & (date_arr <= test_end)

        if train_mask.sum() < 100 or test_mask.sum() < 30:
            print(f"  {split_name}: skipped (train={train_mask.sum()}, test={test_mask.sum()})")
            continue

        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y_bin[train_mask], y_bin[test_mask]
        y_gp_train, y_gp_test = y_gp[train_mask], y_gp[test_mask]
        y_cr_train, y_cr_test = y_cr[train_mask], y_cr[test_mask]
        y_ret_test = y_ret[test_mask]

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_train)
        X_te = scaler.transform(X_test)

        # Model 1: Ridge P(positive)
        m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
        m1.fit(X_tr, y_train)
        p1 = m1.predict_proba(X_te)[:, 1]

        # Model 2: Ridge P(GOOD+)
        m2 = LogisticRegression(C=0.5, penalty="l2", solver="lbfgs", max_iter=2000)
        m2.fit(X_tr, y_gp_train)
        p2 = m2.predict_proba(X_te)[:, 1]

        # Model 3: Ridge P(CRASH)
        m3 = LogisticRegression(C=0.5, penalty="l2", solver="lbfgs", max_iter=2000)
        m3.fit(X_tr, y_cr_train)
        p3 = m3.predict_proba(X_te)[:, 1]

        # Model 4: ElasticNet
        m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                          l1_ratio=0.3, max_iter=2000, random_state=42)
        m4.fit(X_tr, y_train)
        d4 = m4.decision_function(X_te)
        p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))

        # Model 5: XGBoost with XGB_SLOW architecture (v35 NEW)
        # 500 trees, learning_rate=0.02 (slower than v33's 300/0.05)
        m5 = xgb.XGBClassifier(
            n_estimators=500, max_depth=4, learning_rate=0.02,
            subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
            min_child_weight=5, gamma=0.1, random_state=42,
            use_label_encoder=False, eval_metric="logloss", verbosity=0
        )
        m5.fit(X_tr, y_train)
        p5 = m5.predict_proba(X_te)[:, 1]

        # Meta-ensemble: 50/20/30 Ridge+EN+XGB (unchanged from v33)
        p_meta = 0.50 * p1 + 0.20 * p4 + 0.30 * p5
        p_meta = np.clip(p_meta, 0.02, 0.98)

        # Temperature scaling (T=0.85, same as v33)
        base_rate = y_train.mean()
        logits = np.log(p_meta / (1 - p_meta))
        T = 0.85
        p_meta_cal = 1.0 / (1.0 + np.exp(-logits / T))

        # Investment score
        good_base = y_gp_train.mean()
        crash_base = y_cr_train.mean()
        good_lift = p2 / max(good_base, 0.01)
        crash_lift = p3 / max(crash_base, 0.01)
        inv_score = p_meta + 0.10 * (good_lift - 1.0) - 0.10 * (crash_lift - 1.0)
        inv_score = np.clip(inv_score, 0.01, 0.99)

        # Metrics
        auc = roc_auc_score(y_test, p_meta) if len(set(y_test)) > 1 else 0.5
        brier = brier_score_loss(y_test, p_meta_cal)
        baseline_brier = brier_score_loss(y_test, np.full_like(y_test, base_rate, dtype=float))
        auc_inv = roc_auc_score(y_test, inv_score) if len(set(y_test)) > 1 else 0.5

        # Tier analysis
        tiers = {"T1": inv_score >= 0.85, "T2": (inv_score >= 0.70) & (inv_score < 0.85),
                 "T3": (inv_score >= 0.55) & (inv_score < 0.70), "T4": inv_score < 0.55}
        tier_str = []
        for t, mask in tiers.items():
            if mask.sum() > 0:
                actual = y_test[mask].mean()
                avg_ret = y_ret_test[mask].mean()
                gp_rate = y_gp_test[mask].mean() if hasattr(y_gp_test, '__len__') else 0
                cr_rate = y_cr_test[mask].mean() if hasattr(y_cr_test, '__len__') else 0
                tier_str.append(f"{t}={actual:.0%}(ret={avg_ret:+.1f}%,GOOD={gp_rate:.0%},CRASH={cr_rate:.0%},n={mask.sum()})")

        # EV analysis
        inv_top = np.percentile(inv_score, 80)
        inv_bot = np.percentile(inv_score, 20)
        top_mask = inv_score >= inv_top
        bot_mask = inv_score <= inv_bot
        long_mask = inv_score >= 0.70

        ev_long = y_ret_test[long_mask].mean() if long_mask.sum() > 0 else 0
        ev_top_ret = y_ret_test[top_mask].mean() if top_mask.sum() > 0 else 0
        ev_bot_ret = y_ret_test[bot_mask].mean() if bot_mask.sum() > 0 else 0
        ev_all = y_ret_test.mean()
        ev_spread = ev_top_ret - ev_bot_ret
        win_rate = y_test[long_mask].mean() if long_mask.sum() > 0 else 0
        t4_mask = inv_score < 0.55
        avoid_rate = (1 - y_test[t4_mask].mean()) if t4_mask.sum() > 0 else 0

        print(f"  {split_name}: AUC={auc:.4f} (Inv_AUC={auc_inv:.4f})  Brier={brier:.4f} (base={baseline_brier:.4f}, imp={100*(1-brier/baseline_brier):.1f}%)")
        print(f"    Tiers: {' | '.join(tier_str)}")
        print(f"    EV: T1+T2={ev_long:+.2f}%(win={win_rate:.0%},n={long_mask.sum()}) | Top20%={ev_top_ret:+.2f}% | Bot20%={ev_bot_ret:+.2f}% | Spread={ev_spread:+.2f}pp")
        print(f"    Avoid: T4 neg rate={avoid_rate:.0%}(n={t4_mask.sum()}) | All avg={ev_all:+.2f}%")

        all_results.append({
            "split": split_name,
            "auc": auc,
            "auc_inv": auc_inv,
            "brier": brier,
            "baseline_brier": baseline_brier,
            "n_train": int(train_mask.sum()),
            "n_test": int(test_mask.sum()),
            "ev_long": ev_long,
            "ev_top": ev_top_ret,
            "ev_bot": ev_bot_ret,
            "ev_spread": ev_spread,
            "ev_all": ev_all,
        })

    # Step 9: Final full-data model training
    print("\n[TRAIN] Training final v35 models on full dataset...")
    scaler = StandardScaler()
    X_full = scaler.fit_transform(X)

    m1_final = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
    m1_final.fit(X_full, y_bin)

    m2_final = LogisticRegression(C=0.5, penalty="l2", solver="lbfgs", max_iter=2000)
    m2_final.fit(X_full, y_gp)

    m3_final = LogisticRegression(C=0.5, penalty="l2", solver="lbfgs", max_iter=2000)
    m3_final.fit(X_full, y_cr)

    m4_final = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                            l1_ratio=0.3, max_iter=2000, random_state=42)
    m4_final.fit(X_full, y_bin)

    # v35 NEW: XGB_SLOW architecture
    m5_final = xgb.XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.02,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        min_child_weight=5, gamma=0.1, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5_final.fit(X_full, y_bin)

    # Save XGBoost model
    XGB_PATH = os.path.join(DATA_DIR, "gungnir_v35_xgb.json")
    m5_final.save_model(XGB_PATH)
    print(f"  XGBoost model saved to {XGB_PATH}")

    # Bayesian strata
    strata = {}
    for ta_name in list(TA_PATTERNS.keys()) + ["other"]:
        for ph in [1, 2, 3]:
            mask = np.array([1 if (f"ta_{ta_name}" in feature_names and
                                    X[i, feature_names.index(f"ta_{ta_name}")] > 0.5 and
                                    X[i, feature_names.index("phase_numeric")] == ph)
                             else 0 for i in range(len(X))], dtype=bool)
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
        coef_importance[f] = round(float(m1_final.coef_[0][i]), 6)

    xgb_importance = {}
    for i, importance in enumerate(m5_final.feature_importances_):
        if i < len(feature_names):
            xgb_importance[feature_names[i]] = round(float(importance), 6)

    top_positive = sorted(coef_importance.items(), key=lambda x: -x[1])[:25]
    top_negative = sorted(coef_importance.items(), key=lambda x: x[1])[:25]
    top_xgb = sorted(xgb_importance.items(), key=lambda x: -x[1])[:25]

    print(f"\n  Top 25 POSITIVE predictors (Ridge coefficient):")
    for f, c in top_positive:
        xgb_imp = xgb_importance.get(f, 0)
        is_v35 = 1 if "ctgov_v35_" in f else 0
        marker = " [V35]" if is_v35 else ""
        print(f"    {f:45s} {c:+.4f}  (XGB imp={xgb_imp:.4f}){marker}")

    print(f"\n  Top 25 XGBoost feature importances:")
    for f, imp in top_xgb:
        is_v35 = 1 if "ctgov_v35_" in f else 0
        marker = " [V35]" if is_v35 else ""
        ridge_coef = coef_importance.get(f, 0)
        print(f"    {f:45s} {imp:+.4f}  (Ridge coef={ridge_coef:.4f}){marker}")

    # Count v35 features in top 25 of each model
    v35_in_ridge_top25 = sum(1 for f, _ in top_positive if "ctgov_v35_" in f)
    v35_in_xgb_top25 = sum(1 for f, _ in top_xgb if "ctgov_v35_" in f)
    v35_zero_coef = sum(1 for f, c in coef_importance.items() if "ctgov_v35_" in f and abs(c) < 0.0001)
    v35_zero_imp = sum(1 for f, imp in xgb_importance.items() if "ctgov_v35_" in f and imp < 0.0001)

    print(f"\n  V35 FEATURE ANALYSIS:")
    print(f"    V35 features in Ridge top 25: {v35_in_ridge_top25}/25")
    print(f"    V35 features in XGB top 25: {v35_in_xgb_top25}/25")
    print(f"    V35 features with near-zero Ridge coef (<0.0001): {v35_zero_coef}")
    print(f"    V35 features with near-zero XGB importance (<0.0001): {v35_zero_imp}")

    # Step 10: Deploy config
    deploy = {
        "version": "35.0.0",
        "codename": "KAIZEN",
        "architecture": "5-model meta-ensemble (Ridge_Binary 50% + ElasticNet 20% + XGBoost_SLOW 30%) + Ridge_GOOD+ + Ridge_CRASH + Bayesian strata + T=0.85",
        "meta_weights": {"ridge_binary": 0.50, "elasticnet": 0.20, "xgboost_slow": 0.30},
        "xgb_config": {"n_estimators": 500, "learning_rate": 0.02, "max_depth": 4},
        "xgb_model_path": "gungnir_v35_xgb.json",
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "n_features_v33_base": 103,
        "n_features_v35_new": 34,
        "scaler_means": {f: float(scaler.mean_[i]) for i, f in enumerate(feature_names)},
        "scaler_scales": {f: float(scaler.scale_[i]) for i, f in enumerate(feature_names)},
        "M1_coef": {f: float(m1_final.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M1_intercept": float(m1_final.intercept_[0]),
        "M2_coef": {f: float(m2_final.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M2_intercept": float(m2_final.intercept_[0]),
        "M3_coef": {f: float(m3_final.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M3_intercept": float(m3_final.intercept_[0]),
        "M4_coef": {f: float(m4_final.coef_[0][i]) for i, f in enumerate(feature_names)},
        "M4_intercept": float(m4_final.intercept_[0]),
        "strata": strata,
        "train_base_rate": float(y_bin.mean()),
        "train_good_rate": float(y_gp.mean()),
        "train_crash_rate": float(y_cr.mean()),
        "train_mean_return": float(y_ret.mean()),
        "n_train": int(len(X)),
        "validation_results": all_results,
        "feature_importance_ridge": coef_importance,
        "feature_importance_xgb": xgb_importance,
    }

    with open(DEPLOY_JSON, "w") as f:
        json.dump(deploy, f, indent=2)
    print(f"\n[DEPLOY] Written to {DEPLOY_JSON}")

    # Summary & Comparison
    avg_auc = np.mean([r["auc"] for r in all_results])
    avg_brier = np.mean([r["brier"] for r in all_results])
    avg_ev_spread = np.mean([r["ev_spread"] for r in all_results])
    avg_ev_edge = np.mean([r["ev_long"] - r["ev_all"] for r in all_results])

    print(f"\n{'='*80}")
    print(f"GUNGNIR v35.0.0 TRAINING COMPLETE — KAIZEN")
    print(f"{'='*80}")
    print(f"  Architecture: 5-model meta-ensemble (Ridge 50% + EN 20% + XGB_SLOW 30%)")
    print(f"  XGBoost: 500 trees, learning_rate=0.02 (vs v33: 300 trees, lr=0.05)")
    print(f"  Features: {len(feature_names)} total (103 v33 base + 34 v35 new CT.gov)")
    print(f"  Training events: {len(X)} (with real stock returns)")
    print(f"  Walk-forward AUC: {avg_auc:.4f}")
    print(f"  Walk-forward Brier: {avg_brier:.4f}")
    print(f"  Walk-forward EV Spread: {avg_ev_spread:+.2f}pp")
    print(f"  Walk-forward EV Edge: {avg_ev_edge:+.2f}%")
    print(f"  Strata: {len(strata)} TA×Phase combinations")
    print(f"  Leakage status: CLEAN — all NLP outcome features removed")

    print(f"\n{'='*80}")
    print(f"COMPARISON: v33 CHAMPION vs v35 KAIZEN")
    print(f"{'='*80}")
    print(f"  v33 champion:  AUC=0.7241, Brier=0.1548, Features=103")
    print(f"  v35 KAIZEN:    AUC={avg_auc:.4f}, Brier={avg_brier:.4f}, Features={len(feature_names)}")
    print(f"  AUC Delta:     {avg_auc - 0.7241:+.4f} ({(avg_auc/0.7241 - 1)*100:+.1f}%)")
    print(f"  Brier Delta:   {avg_brier - 0.1548:+.4f} (lower is better)")
    if avg_auc > 0.7241:
        print(f"\n  *** v35 KAIZEN BEATS v33 CHAMPION! NEW MODEL CHAMPION ***")
    else:
        print(f"\n  v35 did not beat v33. Analyzing feature quality...")

    print(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
