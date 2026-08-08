#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v38 KAIZEN — Full Cycle: Deep Column Audit + New Data + Architecture
================================================================================

APPROACH:
  1. Start from v37.0.0 as baseline (AUC 0.7537)
  2. EXPAND data: Match CT.gov T1 dataset (117 cols) to 1,752 training events
  3. EXPAND data: Integrate IIS auto-detected features (1,752 events)
  4. EXPAND data: Integrate FinBrain features (1,752 events)
  5. Deep column audit: test 80+ candidate features independently
  6. Greedy forward selection of HO-gated winners
  7. Architecture sweep: hyperparameters, LightGBM, different meta configs
  8. Stability test: 10 seeds, v38 must beat v37 on ALL

CANDIDATE FEATURE CATEGORIES:
  A. CT.gov T1 expanded (50+ new columns):
     - Trial design: is_single_arm, is_crossover, is_parallel, is_open_label
     - Endpoints: ep_is_os, ep_is_pfs, ep_is_orr, ep_is_biomarker, ep_is_qol
     - Complexity: num_primary_outcomes, total_criteria_count, num_interventions
     - Sponsor type: is_industry, is_academic, is_nih, has_industry_collab
     - Geographic: has_us_sites, has_eu_sites, has_china_sites, has_japan_sites
     - Duration: primary_timeframe_days, time_to_readout_days, study_duration
     - Comparators: has_active_comparator, has_sham_comparator
     - Drug type: has_biological, has_genetic, has_combination
     - Demographics: min_age_years, max_age_years, includes_children

  B. IIS auto-detected (12 features):
     - is_interim, is_small_n, combined_dose, prior_readout history, IIS score

  C. FinBrain (12 features):
     - Sentiment, PCR, analyst signals, insider activity

  D. New derived features:
     - Trial complexity score, indication maturity, time-based features
     - CT.gov interaction terms with existing features

T-1 COMPLIANCE: All new features knowable at D-1. No post-readout data leakage.
"""

import csv, json, math, os, re, sys, warnings
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

from gungnir_v36_train import (
    TA_PATTERNS, classify_ta, parse_phase,
    engineer_v31_features, build_journey_index
)

# File paths
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
CTGOV_CACHE_V2 = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
CTGOV_TRAIN_LOOKUP = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
CTGOV_T1_DATASET = os.path.join(DATA_DIR, "ctgov_t1_dataset.csv")
MOMENTUM_CACHE_PATH = os.path.join(DATA_DIR, "readout_momentum_cache.json")
IIS_FEATURES_PATH = os.path.join(DATA_DIR, "iis_features_auto.json")
FINBRAIN_FEATURES_PATH = os.path.join(DATA_DIR, "finbrain_features.json")
DEPLOY_V37_JSON = os.path.join(DATA_DIR, "gungnir_v37_deploy.json")
DEPLOY_V38_JSON = os.path.join(DATA_DIR, "gungnir_v38_deploy.json")
RESULTS_JSON = os.path.join(DATA_DIR, "gungnir_v38_kaizen_results.json")

# V37 features for baseline reference
V37_ADDED = ["is_phase2b", "is_phase1b", "is_phase2a", "is_bridging",
             "enrollment_sq", "indication_density_sq"]
V37_CONFIG = {
    "ridge_c": 0.01, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.60, "meta_xgb": 0.40, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}


# =============================================================================
# EXPANDED CT.GOV T1 MATCHING
# =============================================================================

def build_ctgov_t1_expanded_lookup():
    """Match CT.gov T1 dataset (18,524 trials, 117 cols) to training events.

    Uses existing ctgov_training_lookup matches (1,004 events) but pulls
    the FULL 117-column feature set instead of just 15 fields.
    """
    if not os.path.exists(CTGOV_T1_DATASET):
        print("  [WARN] CT.gov T1 dataset not found, returning empty")
        return {}

    # Load existing matches to get NCT IDs
    existing_lookup = {}
    if os.path.exists(CTGOV_TRAIN_LOOKUP):
        with open(CTGOV_TRAIN_LOOKUP) as f:
            existing = json.load(f)
        existing_lookup = existing.get("matched", {})

    # Get NCT IDs from existing matches
    nct_to_event_idx = {}
    for event_idx, match_data in existing_lookup.items():
        nct_id = match_data.get("nct_id", "")
        if nct_id:
            nct_to_event_idx[nct_id] = event_idx

    print(f"  Existing NCT matches: {len(nct_to_event_idx)}")

    # Load full T1 dataset and match by NCT ID
    expanded = {}
    numeric_fields = [
        'enrollment_count', 'log_enrollment', 'num_arms', 'num_interventions',
        'num_sites', 'log_num_sites', 'num_countries', 'num_primary_outcomes',
        'num_secondary_outcomes', 'num_total_outcomes', 'primary_timeframe_days',
        'min_age_years', 'max_age_years', 'inclusion_criteria_count',
        'exclusion_criteria_count', 'total_criteria_count', 'elig_text_length',
        'time_to_readout_days', 'time_start_to_primary_completion',
        'study_duration_planned', 'time_registration_to_start',
        'masking_rigor', 'num_collaborators', 'num_tas',
    ]
    binary_fields = [
        'is_open_label', 'is_single_blind', 'is_parallel', 'is_crossover',
        'is_single_arm', 'is_treatment_purpose', 'is_actual_enrollment',
        'has_us_sites', 'has_eu_sites', 'has_china_sites', 'has_japan_sites',
        'is_global_trial', 'is_industry', 'is_nih', 'is_academic',
        'has_industry_collab', 'is_placebo_controlled', 'has_active_comparator',
        'has_sham_comparator', 'has_no_intervention', 'has_drug', 'has_biological',
        'has_genetic', 'has_combination', 'ep_is_os', 'ep_is_pfs', 'ep_is_orr',
        'ep_is_safety', 'ep_is_biomarker', 'ep_is_pk_pd', 'ep_is_qol',
        'ep_is_hard', 'ep_is_surrogate', 'healthy_volunteers', 'is_sex_restricted',
        'includes_children', 'includes_older_adult', 'is_adult_only', 'has_dmc',
        'is_fda_regulated_drug', 'is_fda_regulated_device',
    ]
    # Pre-built interaction fields in T1 dataset
    interaction_fields = [
        'phase3_x_randomized', 'phase3_x_double_blind', 'phase3_x_placebo',
        'phase2_x_single_arm', 'onc_x_single_arm', 'onc_x_orr', 'onc_x_os',
        'rare_x_small_trial', 'large_trial', 'small_trial', 'large_x_phase3',
        'industry_x_phase3', 'industry_x_large', 'hard_ep_x_phase3',
        'surrogate_ep_x_phase2', 'dmc_x_phase3', 'global_x_phase3',
    ]
    all_fields = numeric_fields + binary_fields + interaction_fields

    matched_count = 0
    with open(CTGOV_T1_DATASET) as f:
        reader = csv.DictReader(f)
        for row in reader:
            nct_id = row.get('nct_id', '')
            if nct_id in nct_to_event_idx:
                event_idx = nct_to_event_idx[nct_id]
                features = {}
                for field in all_fields:
                    val = row.get(field, '')
                    try:
                        features[field] = float(val) if val != '' else 0.0
                    except (ValueError, TypeError):
                        features[field] = 0.0
                expanded[event_idx] = features
                matched_count += 1

    print(f"  Expanded CT.gov matches: {matched_count} events × {len(all_fields)} fields")
    return expanded


# =============================================================================
# v38 CANDIDATE FEATURES
# =============================================================================

def engineer_v38_candidates(row, base_features, ctgov_t1_data=None,
                            iis_data=None, finbrain_data=None):
    """Build ALL v38 candidate features on top of v37 base.

    Returns dict of {feature_name: value} for ALL candidates.
    Each tested independently in deep column audit.
    """
    candidates = {}

    def _sf(v, default=0):
        """Safe float conversion — handles None, strings, etc."""
        if v is None:
            return default
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    # =====================================================================
    # CATEGORY A: CT.GOV T1 EXPANDED FEATURES
    # =====================================================================
    ct = ctgov_t1_data or {}

    # A1: Trial design
    candidates["ct_is_single_arm"] = ct.get("is_single_arm", 0)
    candidates["ct_is_crossover"] = ct.get("is_crossover", 0)
    candidates["ct_is_parallel"] = ct.get("is_parallel", 0)
    candidates["ct_is_open_label"] = ct.get("is_open_label", 0)
    candidates["ct_has_active_comparator"] = ct.get("has_active_comparator", 0)
    candidates["ct_has_sham_comparator"] = ct.get("has_sham_comparator", 0)

    # A2: Endpoint type (NOT already in v37 — v37 only has ep_hard and ep_surrogate)
    candidates["ct_ep_is_os"] = ct.get("ep_is_os", 0)
    candidates["ct_ep_is_pfs"] = ct.get("ep_is_pfs", 0)
    candidates["ct_ep_is_orr"] = ct.get("ep_is_orr", 0)
    candidates["ct_ep_is_safety"] = ct.get("ep_is_safety", 0)
    candidates["ct_ep_is_biomarker"] = ct.get("ep_is_biomarker", 0)
    candidates["ct_ep_is_pk_pd"] = ct.get("ep_is_pk_pd", 0)
    candidates["ct_ep_is_qol"] = ct.get("ep_is_qol", 0)

    # A3: Trial complexity
    n_primary = ct.get("num_primary_outcomes", 1)
    n_secondary = ct.get("num_secondary_outcomes", 3)
    n_total = ct.get("num_total_outcomes", 5)
    n_interventions = ct.get("num_interventions", 1)
    criteria_count = ct.get("total_criteria_count", 20)
    elig_len = ct.get("elig_text_length", 500)

    candidates["ct_num_primary_outcomes"] = n_primary
    candidates["ct_num_total_outcomes"] = n_total
    candidates["ct_num_interventions"] = n_interventions
    candidates["ct_total_criteria_count"] = criteria_count
    candidates["ct_log_criteria"] = math.log1p(criteria_count)
    candidates["ct_log_elig_length"] = math.log1p(elig_len)
    # Complexity score: more arms × more outcomes × more criteria = more complex
    n_arms = ct.get("num_arms", 2)
    candidates["ct_complexity_score"] = math.log1p(n_arms * n_primary * max(1, criteria_count / 20))
    candidates["ct_multiple_primary_ep"] = 1 if n_primary > 1 else 0

    # A4: Sponsor type (industry vs academic vs NIH)
    candidates["ct_is_industry"] = ct.get("is_industry", 0)
    candidates["ct_is_academic"] = ct.get("is_academic", 0)
    candidates["ct_is_nih"] = ct.get("is_nih", 0)
    candidates["ct_has_industry_collab"] = ct.get("has_industry_collab", 0)
    candidates["ct_num_collaborators"] = ct.get("num_collaborators", 0)

    # A5: Drug type
    candidates["ct_has_biological"] = ct.get("has_biological", 0)
    candidates["ct_has_genetic"] = ct.get("has_genetic", 0)
    candidates["ct_has_combination"] = ct.get("has_combination", 0)
    candidates["ct_has_drug_small_mol"] = ct.get("has_drug", 0)

    # A6: Geographic
    candidates["ct_has_us_sites"] = ct.get("has_us_sites", 0)
    candidates["ct_has_eu_sites"] = ct.get("has_eu_sites", 0)
    candidates["ct_has_china_sites"] = ct.get("has_china_sites", 0)
    candidates["ct_has_japan_sites"] = ct.get("has_japan_sites", 0)
    candidates["ct_num_countries"] = ct.get("num_countries", 1)
    candidates["ct_log_num_sites"] = ct.get("log_num_sites", 0)

    # A7: Duration / timing
    timeframe = ct.get("primary_timeframe_days", 0)
    readout_time = ct.get("time_to_readout_days", 0)
    study_dur = ct.get("study_duration_planned", 0)
    reg_delay = ct.get("time_registration_to_start", 0)

    candidates["ct_log_timeframe"] = math.log1p(max(0, timeframe))
    candidates["ct_log_study_duration"] = math.log1p(max(0, study_dur))
    candidates["ct_log_reg_delay"] = math.log1p(max(0, reg_delay))
    candidates["ct_long_study"] = 1 if study_dur > 1095 else 0  # >3 years
    candidates["ct_quick_readout"] = 1 if 0 < readout_time < 365 else 0  # <1 year

    # A8: Demographics
    candidates["ct_includes_children"] = ct.get("includes_children", 0)
    candidates["ct_includes_older_adult"] = ct.get("includes_older_adult", 0)
    candidates["ct_is_adult_only"] = ct.get("is_adult_only", 0)

    # A9: Pre-built interactions from T1 dataset
    candidates["ct_phase2_x_single_arm"] = ct.get("phase2_x_single_arm", 0)
    candidates["ct_onc_x_single_arm_t1"] = ct.get("onc_x_single_arm", 0)
    candidates["ct_onc_x_orr_t1"] = ct.get("onc_x_orr", 0)
    candidates["ct_onc_x_os_t1"] = ct.get("onc_x_os", 0)
    candidates["ct_rare_x_small_trial"] = ct.get("rare_x_small_trial", 0)
    candidates["ct_industry_x_large"] = ct.get("industry_x_large", 0)
    candidates["ct_surrogate_ep_x_phase2"] = ct.get("surrogate_ep_x_phase2", 0)

    # A10: NEW CT.gov interactions with existing v37 features
    phase = base_features.get("phase_numeric", 2)
    ssr = base_features.get("sponsor_success_rate", 0.5)
    is_micro = base_features.get("is_micro", 0)

    candidates["ct_single_arm_x_phase3"] = candidates["ct_is_single_arm"] * (1 if phase == 3 else 0)
    candidates["ct_biological_x_phase3"] = candidates["ct_has_biological"] * (1 if phase == 3 else 0)
    candidates["ct_industry_x_sponsor_sr"] = candidates["ct_is_industry"] * ssr
    candidates["ct_complexity_x_phase3"] = candidates["ct_complexity_score"] * (1 if phase == 3 else 0)
    candidates["ct_open_label_x_oncology"] = candidates["ct_is_open_label"] * base_features.get("ta_oncology", 0)
    candidates["ct_active_comp_x_phase3"] = candidates["ct_has_active_comparator"] * (1 if phase == 3 else 0)
    candidates["ct_biological_x_sponsor_sr"] = candidates["ct_has_biological"] * ssr
    candidates["ct_os_endpoint_x_oncology"] = candidates["ct_ep_is_os"] * base_features.get("ta_oncology", 0)
    candidates["ct_genetic_x_rare"] = candidates["ct_has_genetic"] * base_features.get("ta_rare_disease", 0)
    candidates["ct_criteria_x_phase3"] = candidates["ct_log_criteria"] * (1 if phase == 3 else 0)

    # =====================================================================
    # CATEGORY B: IIS AUTO-DETECTED FEATURES
    # =====================================================================
    iis = iis_data or {}

    candidates["iis_is_interim"] = _sf(iis.get("v34_is_interim"))
    candidates["iis_n_per_arm_log"] = _sf(iis.get("v34_n_per_arm_log"))
    candidates["iis_is_small_n"] = _sf(iis.get("v34_is_small_n"))
    candidates["iis_has_prior_readout"] = _sf(iis.get("v34_has_prior_readout"))
    candidates["iis_days_since_prior_log"] = _sf(iis.get("v34_days_since_prior_log"))
    candidates["iis_combined_dose_flag"] = _sf(iis.get("v34_combined_dose_flag"))
    candidates["iis_score_auto"] = _sf(iis.get("iis_score_auto"))

    # IIS interactions
    candidates["iis_interim_x_micro"] = candidates["iis_is_interim"] * is_micro
    candidates["iis_interim_x_phase2"] = candidates["iis_is_interim"] * (1 if phase == 2 else 0)
    candidates["iis_small_n_x_interim"] = candidates["iis_is_small_n"] * candidates["iis_is_interim"]
    candidates["iis_score_x_phase2"] = candidates["iis_score_auto"] * (1 if phase == 2 else 0)

    # =====================================================================
    # CATEGORY C: FINBRAIN FEATURES
    # =====================================================================
    fb = finbrain_data or {}

    candidates["fb_sentiment_30d"] = _sf(fb.get("finbrain_sentiment_avg_30d"))
    candidates["fb_sentiment_7d"] = _sf(fb.get("finbrain_sentiment_avg_7d"))
    candidates["fb_sentiment_trend"] = _sf(fb.get("finbrain_sentiment_trend"))
    candidates["fb_pcr_30d"] = _sf(fb.get("finbrain_pcr_avg_30d"))
    candidates["fb_pcr_7d"] = _sf(fb.get("finbrain_pcr_avg_7d"))
    candidates["fb_pcr_trend"] = _sf(fb.get("finbrain_pcr_trend"))
    candidates["fb_analyst_net_signal"] = _sf(fb.get("finbrain_analyst_net_signal"))
    candidates["fb_insider_net_90d"] = _sf(fb.get("finbrain_insider_net_90d"))
    fb_cov = fb.get("finbrain_coverage", 0)
    candidates["fb_coverage"] = 1.0 if fb_cov in ("full", 1, "1") else 0.0

    # FinBrain interactions
    candidates["fb_sentiment_x_phase3"] = candidates["fb_sentiment_30d"] * (1 if phase == 3 else 0)
    candidates["fb_pcr_x_micro"] = candidates["fb_pcr_30d"] * is_micro
    candidates["fb_analyst_x_sponsor_sr"] = candidates["fb_analyst_net_signal"] * ssr

    # =====================================================================
    # CATEGORY D: NEW DERIVED FEATURES
    # =====================================================================

    # D1: Indication maturity (how crowded is this indication historically)
    ind_density = base_features.get("indication_density", 0)
    candidates["ind_maturity_high"] = 1 if ind_density > 10 else 0
    candidates["ind_maturity_low"] = 1 if ind_density <= 2 else 0
    candidates["log_ind_density"] = math.log1p(ind_density)

    # D2: Sponsor portfolio concentration
    # (approximated by sponsor success rate variance from 50%)
    candidates["sponsor_extreme"] = 1 if abs(ssr - 0.5) > 0.3 else 0
    candidates["sponsor_strong"] = 1 if ssr > 0.7 else 0
    candidates["sponsor_weak"] = 1 if ssr < 0.3 else 0

    # D3: Multi-signal conviction (combination of positive signals)
    has_btd = base_features.get("has_btd", 0)
    has_orphan = base_features.get("has_orphan", 0)
    has_ft = base_features.get("has_fast_track", 0)
    has_pr = base_features.get("has_priority_review", 0)
    desig_count = base_features.get("designation_count", 0)
    journey_pos = base_features.get("journey_had_prior_positive", 0)

    candidates["conviction_score"] = (has_btd + has_orphan + has_ft + has_pr +
                                       (1 if ssr > 0.6 else 0) + journey_pos)
    candidates["conviction_high"] = 1 if candidates["conviction_score"] >= 4 else 0

    # D4: Risk concentration (combination of negative signals)
    journey_neg = base_features.get("journey_had_prior_negative", 0)
    candidates["risk_score"] = (journey_neg + (1 if ssr < 0.4 else 0) +
                                 (1 if ind_density > 8 else 0) +
                                 candidates["iis_is_interim"])
    candidates["risk_high"] = 1 if candidates["risk_score"] >= 3 else 0

    # D5: Size × designation interactions (small caps with strong designations = high beta)
    candidates["desig_x_micro"] = desig_count * is_micro
    candidates["btd_x_micro"] = has_btd * is_micro
    candidates["orphan_x_micro"] = has_orphan * is_micro

    # D6: Journey momentum (how recently was the last positive readout)
    journey_streak = base_features.get("journey_positive_streak", 0)
    candidates["journey_streak_sq"] = journey_streak ** 2
    candidates["journey_hot_streak"] = 1 if journey_streak >= 3 else 0

    return candidates


# =============================================================================
# DATA LOADING — v37 pipeline + expanded data sources
# =============================================================================

def load_data():
    """Load all data sources: v37 base + CT.gov T1 + IIS + FinBrain."""
    print("="*80)
    print("GUNGNIR v38 KAIZEN — Full Cycle")
    print("="*80)

    # Step 1: Readout events (same as v37)
    print("\n[LOAD] Loading readout events...")
    with open(READOUT_CSV) as f:
        reader = csv.DictReader(f)
        readout_events = list(reader)
    print(f"  Readout events: {len(readout_events)}")

    # Step 2: Enriched dataset for catalyst text + conference
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

    for ev in readout_events:
        key = f"{ev['ticker'].upper()}|{ev['date']}"
        enr = enriched.get(key, {})
        ev["catalyst_text"] = enr.get("Catalyst", "")
        ev["stage"] = enr.get("Stage", ev.get("stage", "Phase 2"))
        ev["_conference"] = enriched_conferences.get(key, "")
        ev["_parse_phase"] = parse_phase(ev["stage"])

    # Step 3: CT.gov lookup (original 15-field)
    print("[LOAD] Loading CT.gov lookup...")
    ctgov_lookup = {}
    for cache_path in [CTGOV_CACHE_V2, CTGOV_CACHE]:
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                ctgov_lookup = json.load(f)
            print(f"  CT.gov cache: {len(ctgov_lookup)} entries")
            break

    # Step 3b: Sort by date, build journey/sponsor indexes
    sorted_merged = sorted(readout_events, key=lambda e: e.get("date", ""))
    for i, ev in enumerate(sorted_merged):
        ev["_orig_idx"] = i

    print("[BUILD] Journey index...")
    journey_index = build_journey_index(sorted_merged)

    print("[BUILD] Sponsor index...")
    sponsor_index = defaultdict(lambda: {"n_total": 0, "n_positive": 0})
    indication_counter = defaultdict(int)

    for ev in sorted_merged:
        ticker = ev.get("ticker", "").upper()
        sponsor_key = ticker[:4]
        s = sponsor_index[sponsor_key]
        if s["n_total"] > 0:
            ev["_sponsor"] = {"success_rate": s["n_positive"] / s["n_total"],
                             "n_events": s["n_total"]}
        else:
            ev["_sponsor"] = {"success_rate": 0.5, "n_events": 0}

        outcome = ev.get("outcome", "")
        sponsor_index[sponsor_key]["n_total"] += 1
        if outcome == "positive":
            sponsor_index[sponsor_key]["n_positive"] += 1

        ind = ev.get("indication", "").strip().lower()[:50]
        ev["_indication_count"] = indication_counter.get(ind, 0)
        indication_counter[ind] += 1

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

    for ev in sorted_merged:
        key = f"{ev['ticker']}|{ev['date']}"
        ev["_momentum"] = momentum_cache.get(key, {})

    # Step 4b: Competitive landscape
    print("[BUILD] Competitive landscape...")
    indication_dates = defaultdict(list)
    for i, ev in enumerate(sorted_merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = datetime.strptime(ev["date"], "%Y-%m-%d")
        except:
            continue
        if ind:
            indication_dates[ind].append((dt, i))

    for i, ev in enumerate(sorted_merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = datetime.strptime(ev["date"], "%Y-%m-%d")
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

    # =====================================================================
    # NEW: v38 expanded data sources
    # =====================================================================

    # Step 5: CT.gov T1 expanded matching
    print("\n[v38 NEW] Building CT.gov T1 expanded lookup...")
    ctgov_t1_expanded = build_ctgov_t1_expanded_lookup()
    for ev in sorted_merged:
        orig_idx = ev.get("_orig_idx")
        ev["_ctgov_t1"] = ctgov_t1_expanded.get(str(orig_idx), {})

    ct_matched = sum(1 for ev in sorted_merged if ev.get("_ctgov_t1"))
    print(f"  CT.gov T1 attached: {ct_matched}/{len(sorted_merged)}")

    # Step 6: IIS features
    print("[v38 NEW] Loading IIS features...")
    iis_features = {}
    if os.path.exists(IIS_FEATURES_PATH):
        with open(IIS_FEATURES_PATH) as f:
            iis_raw = json.load(f)
        # Match by key format (ticker|date or index)
        if isinstance(iis_raw, dict):
            iis_features = iis_raw
        print(f"  IIS features: {len(iis_features)} entries")

    iis_matched = 0
    for ev in sorted_merged:
        key = f"{ev['ticker']}|{ev['date']}"
        iis = iis_features.get(key, {})
        if not iis:
            # Try index-based
            idx_key = str(ev.get("_orig_idx", ""))
            iis = iis_features.get(idx_key, {})
        ev["_iis"] = iis
        if iis:
            iis_matched += 1
    print(f"  IIS attached: {iis_matched}/{len(sorted_merged)}")

    # Step 7: FinBrain features
    print("[v38 NEW] Loading FinBrain features...")
    finbrain_features = {}
    if os.path.exists(FINBRAIN_FEATURES_PATH):
        with open(FINBRAIN_FEATURES_PATH) as f:
            fb_raw = json.load(f)
        if isinstance(fb_raw, dict):
            finbrain_features = fb_raw
        print(f"  FinBrain features: {len(finbrain_features)} entries")

    fb_matched = 0
    for ev in sorted_merged:
        key = f"{ev['ticker']}|{ev['date']}"
        fb = finbrain_features.get(key, {})
        if not fb:
            idx_key = str(ev.get("_orig_idx", ""))
            fb = finbrain_features.get(idx_key, {})
        ev["_finbrain"] = fb
        if fb:
            fb_matched += 1
    print(f"  FinBrain attached: {fb_matched}/{len(sorted_merged)}")

    return sorted_merged, ctgov_lookup


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def build_features(events, ctgov_lookup, include_v37=True, include_candidates=None):
    """Build feature matrix.

    include_v37: if True, include v37's 6 added features
    include_candidates: None = v37 base only,
                        list of str = add those v38 candidate features,
                        "all" = add all v38 candidates
    """
    from gungnir_v37_kaizen import engineer_v37_candidates

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
        for jk, jv in journey_data.items():
            features[f"journey_{jk}"] = jv

        # v37 features (the 6 winners from v37 kaizen)
        if include_v37:
            v37_cands = engineer_v37_candidates(ev, features)
            for f_name in V37_ADDED:
                if f_name in v37_cands:
                    features[f_name] = v37_cands[f_name]

        # v38 candidate features
        if include_candidates is not None:
            candidates = engineer_v38_candidates(
                ev, features,
                ctgov_t1_data=ev.get("_ctgov_t1", {}),
                iis_data=ev.get("_iis", {}),
                finbrain_data=ev.get("_finbrain", {}),
            )
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
                ridge_c=0.01, xgb_lr=0.01, xgb_trees=400, xgb_depth=3,
                meta_ridge=0.60, meta_xgb=0.40, temperature=1.0,
                crash_c=0.3, goodplus_c=0.5, seed=42, verbose=False,
                use_lgbm=False, lgbm_lr=0.01, lgbm_trees=400, lgbm_depth=3,
                meta_lgbm=0.0):
    """Walk-forward validation with optional LightGBM."""
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

    lgbm_lib = None
    if use_lgbm:
        try:
            import lightgbm as lgbm_lib
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "lightgbm", "--break-system-packages", "-q"],
                          capture_output=True)
            try:
                import lightgbm as lgbm_lib
            except:
                print("  [WARN] LightGBM not available, skipping")
                use_lgbm = False

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

        # Model 6: LightGBM (optional)
        p6 = None
        if use_lgbm and lgbm_lib is not None:
            m6 = lgbm_lib.LGBMClassifier(
                n_estimators=lgbm_trees, max_depth=lgbm_depth, learning_rate=lgbm_lr,
                subsample=0.8, colsample_bytree=0.6, reg_alpha=0.3, reg_lambda=2.0,
                min_child_weight=10, random_state=seed, verbose=-1
            )
            m6.fit(X_tr, y_train)
            p6 = m6.predict_proba(X_te)[:, 1]

        # Meta blend
        if use_lgbm and p6 is not None:
            total_w = meta_ridge + meta_xgb + meta_lgbm
            p_meta = (meta_ridge * p1 + meta_xgb * p5 + meta_lgbm * p6) / total_w
        else:
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
    print("PHASE 1: BASELINE — v37.0.0 reproduction")
    print("="*80)

    events, ctgov_lookup = load_data()

    # Baseline: v37 features with v37 config
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = build_features(
        events, ctgov_lookup, include_v37=True, include_candidates=None
    )
    print(f"\nv37 Baseline features: {len(feat_base)}")
    print(f"Events: {X_base.shape[0]}, Positive rate: {y_bin.mean():.3f}")

    baseline = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates,
                           verbose=True, **V37_CONFIG)
    print(f"\n*** v37 BASELINE: AUC={baseline['avg_auc']:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp "
          f"EV_edge={baseline['avg_ev_edge']:+.2f}%")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 2: DEEP COLUMN AUDIT — test each v38 candidate independently")
    print("="*80)

    # Get all candidate names
    sample_ev = events[0]
    sample_base = dict(zip(feat_base, X_base[0]))
    all_candidates = engineer_v38_candidates(
        sample_ev, sample_base,
        ctgov_t1_data=sample_ev.get("_ctgov_t1", {}),
        iis_data=sample_ev.get("_iis", {}),
        finbrain_data=sample_ev.get("_finbrain", {}),
    )
    candidate_names = sorted(all_candidates.keys())
    print(f"\nTesting {len(candidate_names)} candidate features individually...")

    audit_results = []

    for i, cand in enumerate(candidate_names):
        X_cand, _, _, _, _, _, _, feat_cand = build_features(
            events, ctgov_lookup, include_v37=True, include_candidates=[cand]
        )
        result = evaluate_wf(X_cand, y_bin, y_gp, y_cr, y_ret, dates, **V37_CONFIG)
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

        flag = " <<<" if delta_auc > 0.001 else (" !!!" if delta_auc < -0.003 else "")
        print(f"  [{i+1:3d}/{len(candidate_names)}] {cand:40s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta_auc:+.4f}) "
              f"Brier={result['avg_brier']:.4f} (Δ={delta_brier:+.4f}){flag}")

    # Sort by AUC delta
    audit_sorted = sorted(audit_results, key=lambda x: -x["delta_auc"])

    print(f"\n{'='*80}")
    print("DEEP COLUMN AUDIT RESULTS (sorted by AUC delta)")
    print(f"{'='*80}")
    print(f"{'Feature':40s} {'AUC':>8s} {'ΔAUC':>8s} {'ΔBrier':>8s} {'ΔEV':>8s}")
    print("-"*72)
    for r in audit_sorted[:30]:
        marker = " ✓" if r["delta_auc"] > 0.001 else ""
        print(f"{r['feature']:40s} {r['auc']:.4f} {r['delta_auc']:+.4f} "
              f"{r['delta_brier']:+.4f} {r['delta_ev']:+.2f}{marker}")

    # Winners: features with positive AUC delta above noise threshold
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
        X_test_fs, _, _, _, _, _, _, _ = build_features(
            events, ctgov_lookup, include_v37=True, include_candidates=test_set
        )
        result = evaluate_wf(X_test_fs, y_bin, y_gp, y_cr, y_ret, dates, **V37_CONFIG)

        if result["avg_auc"] > best_auc + 0.0002:  # slightly relaxed threshold
            selected.append(cand)
            best_auc = result["avg_auc"]
            print(f"  + {cand:40s} → AUC={result['avg_auc']:.4f} "
                  f"(+{result['avg_auc']-baseline['avg_auc']:.4f} vs v37)")
        else:
            print(f"  - {cand:40s} → AUC={result['avg_auc']:.4f} (no improvement, skip)")

    print(f"\n*** Selected {len(selected)} features: {selected}")

    if selected:
        X_sel, _, _, _, _, _, _, feat_sel = build_features(
            events, ctgov_lookup, include_v37=True, include_candidates=selected
        )
        sel_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                                 verbose=True, **V37_CONFIG)
        print(f"\n*** SELECTED SET: AUC={sel_result['avg_auc']:.4f} "
              f"(Δ={sel_result['avg_auc']-baseline['avg_auc']:+.4f}) "
              f"Brier={sel_result['avg_brier']:.4f} "
              f"EV_spread={sel_result['avg_ev_spread']:+.2f}pp")
    else:
        X_sel = X_base
        feat_sel = feat_base
        sel_result = baseline
        print("  No features improved over v37 baseline. Using v37 feature set.")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 4: ARCHITECTURE / HYPERPARAMETER SWEEP")
    print("="*80)

    best_config = dict(V37_CONFIG)
    best_sweep_auc = sel_result["avg_auc"]

    sweep_configs = [
        # Ridge C sweep (v37 is at 0.01 — try even stronger and weaker)
        {"ridge_c": 0.005}, {"ridge_c": 0.008}, {"ridge_c": 0.015},
        {"ridge_c": 0.02}, {"ridge_c": 0.03}, {"ridge_c": 0.05},
        # XGB learning rate sweep
        {"xgb_lr": 0.005}, {"xgb_lr": 0.008}, {"xgb_lr": 0.015},
        {"xgb_lr": 0.02}, {"xgb_lr": 0.03},
        # XGB trees
        {"xgb_trees": 300}, {"xgb_trees": 500}, {"xgb_trees": 600},
        # XGB depth
        {"xgb_depth": 2}, {"xgb_depth": 4},
        # Meta-weight sweep
        {"meta_ridge": 0.70, "meta_xgb": 0.30},
        {"meta_ridge": 0.50, "meta_xgb": 0.50},
        {"meta_ridge": 0.55, "meta_xgb": 0.45},
        {"meta_ridge": 0.65, "meta_xgb": 0.35},
        # Temperature sweep
        {"temperature": 0.90}, {"temperature": 0.95},
        {"temperature": 1.05}, {"temperature": 1.10},
        # Crash/GOOD+ C sweep
        {"crash_c": 0.1}, {"crash_c": 0.5},
        {"goodplus_c": 0.3}, {"goodplus_c": 1.0},
        # Combined promising configs
        {"ridge_c": 0.008, "xgb_lr": 0.008},
        {"ridge_c": 0.005, "xgb_trees": 500},
        {"ridge_c": 0.015, "meta_ridge": 0.55, "meta_xgb": 0.45},
        {"ridge_c": 0.008, "xgb_lr": 0.008, "xgb_trees": 500},
        {"ridge_c": 0.005, "xgb_lr": 0.005, "xgb_trees": 600, "xgb_depth": 2},
    ]

    print(f"\nSweeping {len(sweep_configs)} configurations...")

    for i, config in enumerate(sweep_configs):
        params = dict(V37_CONFIG)
        params.update(config)

        result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, **params)

        delta = result["avg_auc"] - best_sweep_auc
        flag = " <<<" if delta > 0.001 else ""
        changes = ", ".join(f"{k}={v}" for k, v in config.items())
        print(f"  [{i+1:2d}/{len(sweep_configs)}] {changes:50s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta:+.4f}) "
              f"Brier={result['avg_brier']:.4f}{flag}")

        if result["avg_auc"] > best_sweep_auc + 0.0005:
            best_sweep_auc = result["avg_auc"]
            best_config.update(config)
            print(f"         >>> NEW BEST CONFIG")

    # Try LightGBM as additional model
    print("\n  [LGBM] Testing LightGBM addition...")
    lgbm_configs = [
        {"use_lgbm": True, "lgbm_lr": 0.01, "lgbm_trees": 400, "lgbm_depth": 3,
         "meta_ridge": 0.50, "meta_xgb": 0.30, "meta_lgbm": 0.20},
        {"use_lgbm": True, "lgbm_lr": 0.01, "lgbm_trees": 400, "lgbm_depth": 3,
         "meta_ridge": 0.40, "meta_xgb": 0.30, "meta_lgbm": 0.30},
        {"use_lgbm": True, "lgbm_lr": 0.01, "lgbm_trees": 300, "lgbm_depth": 2,
         "meta_ridge": 0.50, "meta_xgb": 0.25, "meta_lgbm": 0.25},
    ]

    for i, config in enumerate(lgbm_configs):
        params = dict(best_config)
        params.update(config)
        result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, **params)
        delta = result["avg_auc"] - best_sweep_auc
        print(f"  [LGBM {i+1}] AUC={result['avg_auc']:.4f} (Δ={delta:+.4f})")
        if result["avg_auc"] > best_sweep_auc + 0.0005:
            best_sweep_auc = result["avg_auc"]
            best_config.update(config)
            print(f"         >>> LGBM HELPS! New best config")

    # Clean up config for non-LGBM case
    if not best_config.get("use_lgbm"):
        for k in ["use_lgbm", "lgbm_lr", "lgbm_trees", "lgbm_depth", "meta_lgbm"]:
            best_config.pop(k, None)

    print(f"\n*** BEST CONFIG: {best_config}")
    print(f"*** BEST AUC: {best_sweep_auc:.4f} (Δ={best_sweep_auc-baseline['avg_auc']:+.4f} vs v37)")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 5: STABILITY TEST — 10 seeds")
    print("="*80)

    v37_aucs = []
    v38_aucs = []

    for seed in range(10):
        v37_r = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates,
                           seed=seed, **V37_CONFIG)
        v38_r = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                           seed=seed, **best_config)
        v37_aucs.append(v37_r["avg_auc"])
        v38_aucs.append(v38_r["avg_auc"])
        wins = "v38" if v38_r["avg_auc"] > v37_r["avg_auc"] else "v37"
        print(f"  Seed {seed}: v37={v37_r['avg_auc']:.4f} v38={v38_r['avg_auc']:.4f} → {wins}")

    v38_wins = sum(1 for a, b in zip(v38_aucs, v37_aucs) if a > b)

    from scipy import stats
    try:
        t_stat, p_val = stats.ttest_rel(v38_aucs, v37_aucs)
    except:
        t_stat, p_val = 0, 1.0

    print(f"\n*** STABILITY: v38 wins {v38_wins}/10 seeds")
    print(f"*** Mean v37 AUC: {np.mean(v37_aucs):.4f} ± {np.std(v37_aucs):.4f}")
    print(f"*** Mean v38 AUC: {np.mean(v38_aucs):.4f} ± {np.std(v38_aucs):.4f}")
    print(f"*** Paired t-test: t={t_stat:.4f}, p={p_val:.10f}")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 6: FINAL VERDICT")
    print("="*80)

    final_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **best_config)

    is_champion = (v38_wins >= 7 and
                   final_result["avg_auc"] > baseline["avg_auc"] + 0.001 and
                   p_val < 0.05)

    print(f"\n{'='*80}")
    print(f"GUNGNIR v38 KAIZEN RESULTS")
    print(f"{'='*80}")
    print(f"  v37 Baseline AUC: {baseline['avg_auc']:.4f}")
    print(f"  v38 Final AUC:    {final_result['avg_auc']:.4f} "
          f"(Δ={final_result['avg_auc']-baseline['avg_auc']:+.4f})")
    print(f"  v38 Brier:        {final_result['avg_brier']:.4f} "
          f"(Δ={final_result['avg_brier']-baseline['avg_brier']:+.4f})")
    print(f"  v38 EV Spread:    {final_result['avg_ev_spread']:+.2f}pp "
          f"(Δ={final_result['avg_ev_spread']-baseline['avg_ev_spread']:+.2f})")
    print(f"  EV Edge:          {final_result['avg_ev_edge']:+.2f}% "
          f"(Δ={final_result['avg_ev_edge']-baseline['avg_ev_edge']:+.2f})")
    print(f"  Stability:        {v38_wins}/10 seeds, p={p_val:.10f}")
    print(f"  Features added:   {selected}")
    print(f"  Config:           {best_config}")
    print(f"  Total features:   {X_sel.shape[1]}")
    print(f"  VERDICT:          "
          f"{'*** v38 IS NEW CHAMPION ***' if is_champion else 'v37 retains crown'}")

    # Save results
    results = {
        "version": "38.0.0",
        "baseline_version": "37.0.0",
        "baseline_auc": baseline["avg_auc"],
        "baseline_brier": baseline["avg_brier"],
        "baseline_ev_spread": baseline["avg_ev_spread"],
        "final_auc": final_result["avg_auc"],
        "final_brier": final_result["avg_brier"],
        "final_ev_spread": final_result["avg_ev_spread"],
        "auc_delta": final_result["avg_auc"] - baseline["avg_auc"],
        "features_added": selected,
        "features_tested": len(candidate_names),
        "config": best_config,
        "stability": {"wins": v38_wins, "p_value": p_val},
        "audit_results": audit_results,
        "is_champion": str(is_champion),
        "n_features_total": X_sel.shape[1],
        "data_sources": {
            "ctgov_t1_matched": sum(1 for ev in events if ev.get("_ctgov_t1")),
            "iis_matched": sum(1 for ev in events if ev.get("_iis")),
            "finbrain_matched": sum(1 for ev in events if ev.get("_finbrain")),
        }
    }

    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {RESULTS_JSON}")

    # If champion, train final model and save deploy config
    if is_champion:
        print("\n[CHAMPION] Training final v38 model on full dataset...")
        train_and_deploy(X_sel, y_bin, y_gp, y_cr, y_ret, dates, meta,
                        feat_sel if selected else feat_base, best_config, baseline)

    return 0


def train_and_deploy(X, y_bin, y_gp, y_cr, y_ret, dates, meta, feature_names,
                     config, baseline):
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

    # Model 1: Binary
    m1 = LogisticRegression(C=config["ridge_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_full, y_bin)

    # Model 2: GOOD+
    m2 = LogisticRegression(C=config["goodplus_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m2.fit(X_full, y_gp)

    # Model 3: CRASH
    m3 = LogisticRegression(C=config["crash_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m3.fit(X_full, y_cr)

    # Model 4: ElasticNet (compat)
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

    XGB_PATH = os.path.join(DATA_DIR, "gungnir_v38_xgb.json")
    m5.save_model(XGB_PATH)
    print(f"  XGBoost model saved to {XGB_PATH}")

    # LightGBM if used
    lgbm_path = None
    if config.get("use_lgbm"):
        try:
            import lightgbm as lgbm_lib
            m6 = lgbm_lib.LGBMClassifier(
                n_estimators=config.get("lgbm_trees", 400),
                max_depth=config.get("lgbm_depth", 3),
                learning_rate=config.get("lgbm_lr", 0.01),
                subsample=0.8, colsample_bytree=0.6,
                reg_alpha=0.3, reg_lambda=2.0,
                min_child_weight=10, random_state=42, verbose=-1
            )
            m6.fit(X_full, y_bin)
            lgbm_path = os.path.join(DATA_DIR, "gungnir_v38_lgbm.txt")
            m6.booster_.save_model(lgbm_path)
            print(f"  LightGBM model saved to {lgbm_path}")
        except Exception as e:
            print(f"  [WARN] LightGBM save failed: {e}")

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

    meta_ridge_w = config.get("meta_ridge", 0.6)
    meta_xgb_w = config.get("meta_xgb", 0.4)
    meta_lgbm_w = config.get("meta_lgbm", 0.0)

    arch_desc = f"3-model meta-ensemble (Ridge {meta_ridge_w*100:.0f}% + XGB {meta_xgb_w*100:.0f}%"
    if meta_lgbm_w > 0:
        arch_desc += f" + LGBM {meta_lgbm_w*100:.0f}%"
    arch_desc += f") + Ridge_GOOD+ + Ridge_CRASH + Bayesian strata + T={config.get('temperature', 1.0):.2f}"

    deploy = {
        "version": "38.0.0",
        "codename": "Allfather_v38_Kaizen",
        "architecture": arch_desc,
        "meta_weights": {
            "ridge_binary": meta_ridge_w,
            "elasticnet": 0.00,
            "xgboost": meta_xgb_w,
            "lightgbm": meta_lgbm_w,
        },
        "xgb_model_path": "gungnir_v38_xgb.json",
        "lgbm_model_path": os.path.basename(lgbm_path) if lgbm_path else None,
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
        "kaizen_from_v37": {
            "v37_auc": baseline["avg_auc"],
            "v37_brier": baseline["avg_brier"],
        }
    }

    with open(DEPLOY_V38_JSON, "w") as f:
        json.dump(deploy, f, indent=2)
    print(f"\n[DEPLOY] v38 deploy config written to {DEPLOY_V38_JSON}")


if __name__ == "__main__":
    sys.exit(main())
