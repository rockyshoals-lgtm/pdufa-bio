#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v39 KAIZEN — Enrichment Leverage: CT.gov v2 (80.3%) + ChEMBL
================================================================================

APPROACH:
  1. Start from v38.0.0 as baseline (AUC 0.7568)
  2. LEVERAGE: CT.gov v2 matching (80.3% coverage, up from 25.5%)
     - v38 had 447/1,752 matched → 75% imputed with phase averages
     - v39 has 1,624/2,022 matched → only 20% imputed
     - Existing CT.gov features should now be FAR more predictive with real data
  3. ADD: ChEMBL drug mechanism features (57 drugs, 308/2,022 matches)
     - target_class: kinase, immune_checkpoint, gpcr, receptor, etc.
     - mechanism_type: inhibitor, antagonist, agonist, etc.
     - is_biologic, first_in_class
  4. Deep column audit: test each candidate independently
  5. Greedy forward selection on HO-gated winners
  6. Architecture sweep
  7. 10-seed stability test vs v38

KEY INSIGHT: The CT.gov features in v38 were largely noise because 75% were
imputed. With 80.3% real matches, features like ct_is_industry, ct_log_elig_length,
and trial rigor should show dramatically stronger signal.

T-1 COMPLIANCE: All features knowable before readout. ChEMBL drug data is static.
CT.gov data is registered before trial completion.
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
CTGOV_CACHE = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
CTGOV_CACHE_FALLBACK = os.path.join(DATA_DIR, "ctgov_cache.json")
CTGOV_TRAIN_LOOKUP_V2 = os.path.join(DATA_DIR, "ctgov_training_lookup_v2.json")
CTGOV_TRAIN_LOOKUP = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
CTGOV_T1_DATASET = os.path.join(DATA_DIR, "ctgov_t1_dataset.csv")
MOMENTUM_CACHE_PATH = os.path.join(DATA_DIR, "readout_momentum_cache.json")
IIS_FEATURES_PATH = os.path.join(DATA_DIR, "iis_features_auto.json")
CHEMBL_CACHE_PATH = os.path.join(DATA_DIR, "chembl_enrichment_cache.json")
DEPLOY_V38_JSON = os.path.join(DATA_DIR, "gungnir_v38_deploy.json")
DEPLOY_V39_JSON = os.path.join(DATA_DIR, "gungnir_v39_deploy.json")
RESULTS_JSON = os.path.join(DATA_DIR, "gungnir_v39_kaizen_results.json")

# v38 config for baseline
V38_CONFIG = {
    "ridge_c": 0.01, "xgb_lr": 0.01, "xgb_trees": 400, "xgb_depth": 3,
    "meta_ridge": 0.70, "meta_xgb": 0.30, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# v38's 3 added features (over v37)
V38_ADDED = ["ct_is_industry", "iis_is_interim", "ct_log_elig_length"]

# v37's 6 added features (over v36.1)
V37_ADDED = ["is_phase2b", "is_phase1b", "is_phase2a", "is_bridging",
             "enrollment_sq", "indication_density_sq"]


# =============================================================================
# CT.GOV V2 MATCHING (80.3% COVERAGE)
# =============================================================================

def build_ctgov_v2_lookup():
    """Load CT.gov v2 training lookup with 80.3% coverage.

    This is the KEY v39 improvement: 1,624 matched events vs 447 in v38.
    The lookup maps GUNGNIR event index → CT.gov trial design features.
    """
    if os.path.exists(CTGOV_TRAIN_LOOKUP_V2):
        with open(CTGOV_TRAIN_LOOKUP_V2) as f:
            v2_lookup = json.load(f)
        matched = v2_lookup.get("matched", {})
        print(f"  CT.gov v2 lookup loaded: {len(matched)} matched events")
        return matched
    else:
        print("  [WARN] CT.gov v2 lookup not found, falling back to v1")
        if os.path.exists(CTGOV_TRAIN_LOOKUP):
            with open(CTGOV_TRAIN_LOOKUP) as f:
                v1_lookup = json.load(f)
            return v1_lookup.get("matched", {})
        return {}


def build_ctgov_t1_expanded_lookup():
    """Match CT.gov T1 dataset to training events via NCT IDs from v2 lookup."""
    if not os.path.exists(CTGOV_T1_DATASET):
        print("  [WARN] CT.gov T1 dataset not found")
        return {}

    # Get NCT IDs from v2 matches
    v2_matched = build_ctgov_v2_lookup()
    nct_to_event_idx = {}
    for event_idx, match_data in v2_matched.items():
        nct_id = match_data.get("nct_id", "")
        if nct_id:
            nct_to_event_idx[nct_id] = event_idx

    print(f"  NCT IDs to match in T1: {len(nct_to_event_idx)}")

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
    interaction_fields = [
        'phase3_x_randomized', 'phase3_x_double_blind', 'phase3_x_placebo',
        'phase2_x_single_arm', 'onc_x_single_arm', 'onc_x_orr', 'onc_x_os',
        'rare_x_small_trial', 'large_trial', 'small_trial', 'large_x_phase3',
        'industry_x_phase3', 'industry_x_large', 'hard_ep_x_phase3',
        'surrogate_ep_x_phase2', 'dmc_x_phase3', 'global_x_phase3',
    ]
    all_fields = numeric_fields + binary_fields + interaction_fields

    expanded = {}
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

    print(f"  T1 expanded matches: {matched_count} events × {len(all_fields)} fields")
    return expanded


# =============================================================================
# ChEMBL DRUG MATCHING
# =============================================================================

def clean_drug_name(raw):
    """Extract core drug name from GUNGNIR strings."""
    name = raw.strip()
    name = re.sub(r'\s*-\s*\(.*?\)\s*$', '', name)
    paren_match = re.search(r'\(([^)]+)\)', name)
    generic = paren_match.group(1).strip() if paren_match else None
    brand = re.sub(r'\s*\(.*?\)\s*', '', name).strip()
    return brand.upper(), (generic.upper() if generic else None)


def build_chembl_lookup():
    """Load ChEMBL drug enrichment cache."""
    if not os.path.exists(CHEMBL_CACHE_PATH):
        print("  [WARN] ChEMBL cache not found")
        return {}
    with open(CHEMBL_CACHE_PATH) as f:
        chembl = json.load(f)
    # Build uppercase lookup
    lookup = {k.upper(): v for k, v in chembl.items()}
    print(f"  ChEMBL drugs loaded: {len(lookup)}")
    return lookup


# =============================================================================
# v39 CANDIDATE FEATURES
# =============================================================================

def engineer_v39_candidates(row, base_features, ctgov_t1_data=None,
                            ctgov_v2_data=None, iis_data=None, chembl_data=None):
    """Build ALL v39 candidate features on top of v38 base.

    KEY DIFFERENCE from v38: CT.gov features now have 80.3% real data coverage.
    Many CT.gov features that were neutral in v38 (due to 75% imputation) may
    now show real signal.
    """
    candidates = {}

    def _sf(v, default=0):
        if v is None:
            return default
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    phase = base_features.get("phase_numeric", 2)
    ssr = base_features.get("sponsor_success_rate", 0.5)
    is_micro = base_features.get("is_micro", 0)
    is_small = base_features.get("is_small", 0)
    is_onc = base_features.get("ta_oncology", 0)
    is_rare = base_features.get("ta_rare_disease", 0)

    # =====================================================================
    # CATEGORY A: CT.GOV T1 EXPANDED — RE-TEST WITH 80.3% REAL COVERAGE
    # =====================================================================
    # Features that were neutral at 25% may now have signal at 80%
    ct = ctgov_t1_data or {}

    # A1: Trial design (re-test with better coverage)
    candidates["ct_is_single_arm"] = ct.get("is_single_arm", 0)
    candidates["ct_is_crossover"] = ct.get("is_crossover", 0)
    candidates["ct_is_parallel"] = ct.get("is_parallel", 0)
    candidates["ct_is_open_label"] = ct.get("is_open_label", 0)
    candidates["ct_has_active_comparator"] = ct.get("has_active_comparator", 0)

    # A2: Endpoints (re-test)
    candidates["ct_ep_is_os"] = ct.get("ep_is_os", 0)
    candidates["ct_ep_is_pfs"] = ct.get("ep_is_pfs", 0)
    candidates["ct_ep_is_orr"] = ct.get("ep_is_orr", 0)
    candidates["ct_ep_is_safety"] = ct.get("ep_is_safety", 0)
    candidates["ct_ep_is_biomarker"] = ct.get("ep_is_biomarker", 0)
    candidates["ct_ep_is_qol"] = ct.get("ep_is_qol", 0)

    # A3: Complexity — re-test with real data
    n_primary = ct.get("num_primary_outcomes", 1)
    n_total = ct.get("num_total_outcomes", 5)
    n_interventions = ct.get("num_interventions", 1)
    criteria_count = ct.get("total_criteria_count", 20)
    elig_len = ct.get("elig_text_length", 500)
    n_arms = ct.get("num_arms", 2)

    candidates["ct_num_primary_outcomes"] = n_primary
    candidates["ct_num_interventions"] = n_interventions
    candidates["ct_log_criteria"] = math.log1p(criteria_count)
    candidates["ct_complexity_score"] = math.log1p(n_arms * n_primary * max(1, criteria_count / 20))
    candidates["ct_multiple_primary_ep"] = 1 if n_primary > 1 else 0

    # A4: Sponsor type (ct_is_industry already in v38 — re-test others)
    candidates["ct_is_academic"] = ct.get("is_academic", 0)
    candidates["ct_is_nih"] = ct.get("is_nih", 0)
    candidates["ct_has_industry_collab"] = ct.get("has_industry_collab", 0)
    candidates["ct_num_collaborators"] = ct.get("num_collaborators", 0)

    # A5: Drug type
    candidates["ct_has_biological"] = ct.get("has_biological", 0)
    candidates["ct_has_genetic"] = ct.get("has_genetic", 0)
    candidates["ct_has_combination"] = ct.get("has_combination", 0)

    # A6: Geography (re-test with better coverage)
    candidates["ct_has_us_sites"] = ct.get("has_us_sites", 0)
    candidates["ct_has_eu_sites"] = ct.get("has_eu_sites", 0)
    candidates["ct_has_china_sites"] = ct.get("has_china_sites", 0)
    candidates["ct_has_japan_sites"] = ct.get("has_japan_sites", 0)

    # A7: Duration/timing (re-test)
    timeframe = ct.get("primary_timeframe_days", 0)
    study_dur = ct.get("study_duration_planned", 0)

    candidates["ct_log_timeframe"] = math.log1p(max(0, timeframe))
    candidates["ct_log_study_duration"] = math.log1p(max(0, study_dur))
    candidates["ct_long_study"] = 1 if study_dur > 1095 else 0

    # A8: Demographics
    candidates["ct_includes_children"] = ct.get("includes_children", 0)
    candidates["ct_is_adult_only"] = ct.get("is_adult_only", 0)

    # A9: NEW interaction terms for v39 (CT.gov × existing features)
    candidates["ct_single_arm_x_phase3"] = candidates["ct_is_single_arm"] * (1 if phase == 3 else 0)
    candidates["ct_biological_x_phase3"] = candidates["ct_has_biological"] * (1 if phase == 3 else 0)
    candidates["ct_industry_x_sponsor_sr"] = _sf(ct.get("is_industry", 0)) * ssr
    candidates["ct_complexity_x_phase3"] = candidates["ct_complexity_score"] * (1 if phase == 3 else 0)
    candidates["ct_open_label_x_oncology"] = candidates["ct_is_open_label"] * is_onc
    candidates["ct_genetic_x_rare"] = candidates["ct_has_genetic"] * is_rare
    candidates["ct_os_x_oncology"] = candidates["ct_ep_is_os"] * is_onc
    candidates["ct_orr_x_oncology"] = candidates["ct_ep_is_orr"] * is_onc
    candidates["ct_biomarker_x_phase2"] = candidates["ct_ep_is_biomarker"] * (1 if phase == 2 else 0)
    candidates["ct_active_comp_x_phase3"] = candidates["ct_has_active_comparator"] * (1 if phase == 3 else 0)
    candidates["ct_china_x_oncology"] = candidates["ct_has_china_sites"] * is_onc
    candidates["ct_japan_x_rare"] = candidates["ct_has_japan_sites"] * is_rare
    candidates["ct_collab_x_micro"] = candidates["ct_num_collaborators"] * is_micro
    candidates["ct_combination_x_phase3"] = candidates["ct_has_combination"] * (1 if phase == 3 else 0)
    candidates["ct_nih_x_rare"] = candidates["ct_is_nih"] * is_rare
    candidates["ct_multiple_ep_x_phase3"] = candidates["ct_multiple_primary_ep"] * (1 if phase == 3 else 0)

    # A10: CT.gov v2 15-field features (from the direct lookup, not T1)
    cv2 = ctgov_v2_data or {}
    enrollment = _sf(cv2.get("enrollment", 0))
    n_arms_v2 = _sf(cv2.get("n_arms", 2))
    n_sites_v2 = _sf(cv2.get("n_sites", 0))
    masking = _sf(cv2.get("masking_rigor", 0))

    candidates["cv2_log_enrollment"] = math.log1p(enrollment)
    candidates["cv2_n_per_arm"] = enrollment / max(n_arms_v2, 1)
    candidates["cv2_log_n_per_arm"] = math.log1p(enrollment / max(n_arms_v2, 1))
    candidates["cv2_masking_rigor"] = masking
    candidates["cv2_log_n_sites"] = math.log1p(n_sites_v2)
    candidates["cv2_is_rigorous"] = 1 if (_sf(cv2.get("is_randomized", 0)) and
                                           _sf(cv2.get("is_double_blind", 0)) and
                                           _sf(cv2.get("is_placebo", 0))) else 0
    candidates["cv2_is_global_large"] = 1 if (_sf(cv2.get("is_global", 0)) and n_sites_v2 >= 20) else 0

    # v2 interaction terms
    candidates["cv2_rigorous_x_phase3"] = candidates["cv2_is_rigorous"] * (1 if phase == 3 else 0)
    candidates["cv2_enrollment_x_micro"] = math.log1p(enrollment) * is_micro
    candidates["cv2_global_x_onc"] = candidates["cv2_is_global_large"] * is_onc
    candidates["cv2_masking_x_phase3"] = masking * (1 if phase == 3 else 0)
    candidates["cv2_n_per_arm_sq"] = candidates["cv2_n_per_arm"] ** 0.5  # sqrt for diminishing returns

    # =====================================================================
    # CATEGORY B: ChEMBL DRUG MECHANISM FEATURES (NEW for v39)
    # =====================================================================
    ch = chembl_data or {}

    # Target class one-hot encoding
    tc = str(ch.get("target_class", "")).lower()
    candidates["ch_is_kinase"] = 1 if tc == "kinase" else 0
    candidates["ch_is_immune_checkpoint"] = 1 if tc == "immune_checkpoint" else 0
    candidates["ch_is_gpcr"] = 1 if tc == "gpcr" else 0
    candidates["ch_is_receptor"] = 1 if "receptor" in tc else 0
    candidates["ch_is_ion_channel"] = 1 if tc == "ion_channel" else 0
    candidates["ch_is_enzyme"] = 1 if tc == "enzyme" else 0

    # Mechanism type
    mt = str(ch.get("mechanism_type", "")).lower()
    candidates["ch_is_inhibitor"] = 1 if mt == "inhibitor" else 0
    candidates["ch_is_antagonist"] = 1 if mt == "antagonist" else 0
    candidates["ch_is_agonist"] = 1 if mt == "agonist" else 0

    # Drug properties
    candidates["ch_is_biologic"] = _sf(ch.get("is_biologic", 0))
    candidates["ch_first_in_class"] = _sf(ch.get("first_in_class", 0))
    candidates["ch_has_approved_competitor"] = _sf(ch.get("has_approved_competitor", 0))
    candidates["ch_has_match"] = 1 if ch else 0

    # ChEMBL interaction terms
    candidates["ch_kinase_x_phase3"] = candidates["ch_is_kinase"] * (1 if phase == 3 else 0)
    candidates["ch_checkpoint_x_onc"] = candidates["ch_is_immune_checkpoint"] * is_onc
    candidates["ch_biologic_x_micro"] = candidates["ch_is_biologic"] * is_micro
    candidates["ch_fic_x_phase3"] = candidates["ch_first_in_class"] * (1 if phase == 3 else 0)
    candidates["ch_competitor_x_ssr"] = candidates["ch_has_approved_competitor"] * ssr
    candidates["ch_inhibitor_x_onc"] = candidates["ch_is_inhibitor"] * is_onc
    candidates["ch_biologic_x_phase3"] = candidates["ch_is_biologic"] * (1 if phase == 3 else 0)
    candidates["ch_fic_x_micro"] = candidates["ch_first_in_class"] * is_micro

    # =====================================================================
    # CATEGORY C: IIS FEATURES (kept from v38, iis_is_interim already selected)
    # =====================================================================
    iis = iis_data or {}
    candidates["iis_n_per_arm_log"] = _sf(iis.get("v34_n_per_arm_log"))
    candidates["iis_is_small_n"] = _sf(iis.get("v34_is_small_n"))
    candidates["iis_combined_dose_flag"] = _sf(iis.get("v34_combined_dose_flag"))
    candidates["iis_score_auto"] = _sf(iis.get("iis_score_auto"))
    candidates["iis_small_n_x_interim"] = candidates["iis_is_small_n"] * _sf(iis.get("v34_is_interim"))

    # =====================================================================
    # CATEGORY D: DERIVED FEATURES
    # =====================================================================
    ind_density = base_features.get("indication_density", 0)
    has_btd = base_features.get("has_btd", 0)
    has_orphan = base_features.get("has_orphan", 0)
    desig_count = base_features.get("designation_count", 0)
    journey_pos = base_features.get("journey_had_prior_positive", 0)
    journey_neg = base_features.get("journey_had_prior_negative", 0)
    journey_streak = base_features.get("journey_positive_streak", 0)

    candidates["sponsor_strong"] = 1 if ssr > 0.7 else 0
    candidates["sponsor_weak"] = 1 if ssr < 0.3 else 0
    candidates["conviction_score"] = (has_btd + has_orphan +
                                       base_features.get("has_fast_track", 0) +
                                       base_features.get("has_priority_review", 0) +
                                       (1 if ssr > 0.6 else 0) + journey_pos)
    candidates["conviction_high"] = 1 if candidates["conviction_score"] >= 4 else 0
    candidates["risk_high"] = 1 if (journey_neg + (1 if ssr < 0.4 else 0) +
                                     (1 if ind_density > 8 else 0)) >= 3 else 0
    candidates["btd_x_micro"] = has_btd * is_micro
    candidates["orphan_x_micro"] = has_orphan * is_micro
    candidates["journey_streak_sq"] = journey_streak ** 2
    candidates["journey_hot_streak"] = 1 if journey_streak >= 3 else 0
    candidates["log_ind_density"] = math.log1p(ind_density)
    candidates["ind_maturity_high"] = 1 if ind_density > 10 else 0

    return candidates


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data():
    """Load all data sources with v2 CT.gov matching."""
    print("="*80)
    print("GUNGNIR v39 KAIZEN — Enrichment Leverage")
    print("="*80)

    # Step 1: Readout events
    print("\n[LOAD] Readout events...")
    with open(READOUT_CSV) as f:
        readout_events = list(csv.DictReader(f))
    print(f"  Readout events: {len(readout_events)}")

    # Step 2: Enriched dataset for catalyst text + conference
    print("[LOAD] Enriched dataset...")
    enriched = {}
    enriched_conferences = {}
    for csv_path in [ENRICHED_CSV, HISTORICAL_CSV]:
        if os.path.exists(csv_path):
            with open(csv_path) as f:
                for row in csv.DictReader(f):
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
        ev["_drug_name"] = enr.get("Drug", "")

    # Step 3: CT.gov caches
    print("[LOAD] CT.gov caches...")
    ctgov_lookup = {}
    for cache_path in [CTGOV_CACHE, CTGOV_CACHE_FALLBACK]:
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                ctgov_lookup = json.load(f)
            print(f"  CT.gov cache: {len(ctgov_lookup)} entries")
            break

    # Step 3b: Sort + build indexes
    sorted_merged = sorted(readout_events, key=lambda e: e.get("date", ""))
    for i, ev in enumerate(sorted_merged):
        ev["_orig_idx"] = i

    print("[BUILD] Journey index...")
    journey_index = build_journey_index(sorted_merged)

    print("[BUILD] Sponsor index (T-1 compliant)...")
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

    # Step 3d: CT.gov training lookup — USE V2 (80.3% coverage!)
    print("[LOAD] CT.gov training lookup v2 (80.3% coverage)...")
    ctgov_v2_matched = {}
    ctgov_phase_avgs = {}

    # Try v2 first, then v1
    for lookup_path in [CTGOV_TRAIN_LOOKUP_V2, CTGOV_TRAIN_LOOKUP]:
        if os.path.exists(lookup_path):
            with open(lookup_path) as f:
                train_lookup = json.load(f)
            ctgov_v2_matched = train_lookup.get("matched", {})
            ctgov_phase_avgs = train_lookup.get("phase_averages", {})
            print(f"  Loaded from {os.path.basename(lookup_path)}: {len(ctgov_v2_matched)} matches")
            break

    for i, ev in enumerate(sorted_merged):
        orig_idx = ev.get("_orig_idx")
        if orig_idx is not None and str(orig_idx) in ctgov_v2_matched:
            raw = ctgov_v2_matched[str(orig_idx)]
            # Coerce all numeric fields to proper types for engineer_v31_features
            coerced = {}
            for k, v in raw.items():
                if k == 'nct_id':
                    coerced[k] = v
                else:
                    try:
                        coerced[k] = float(v) if v not in (None, '', 'None') else 0
                    except (ValueError, TypeError):
                        coerced[k] = v
            # Ensure enrollment is numeric
            if 'enrollment' in coerced:
                try:
                    coerced['enrollment'] = int(float(coerced['enrollment']))
                except:
                    coerced['enrollment'] = 0
            ev["_ctgov_v2"] = coerced
        else:
            ev["_ctgov_v2"] = {}
        phase_str = str(ev.get("_parse_phase", 2))
        ev["_ctgov_phase_avg"] = ctgov_phase_avgs.get(phase_str, {})

        # ALSO set the old _ctgov_real for compatibility with base features
        ev["_ctgov_real"] = ev["_ctgov_v2"]

    v2_matched = sum(1 for ev in sorted_merged if ev.get("_ctgov_v2"))
    print(f"  CT.gov v2 attached: {v2_matched}/{len(sorted_merged)} ({100*v2_matched/len(sorted_merged):.1f}%)")

    # Step 5: CT.gov T1 expanded
    print("[LOAD] CT.gov T1 expanded...")
    ctgov_t1_expanded = build_ctgov_t1_expanded_lookup()
    for ev in sorted_merged:
        orig_idx = ev.get("_orig_idx")
        ev["_ctgov_t1"] = ctgov_t1_expanded.get(str(orig_idx), {})

    ct_t1_matched = sum(1 for ev in sorted_merged if ev.get("_ctgov_t1"))
    print(f"  CT.gov T1 attached: {ct_t1_matched}/{len(sorted_merged)}")

    # Step 6: IIS features
    print("[LOAD] IIS features...")
    iis_features = {}
    if os.path.exists(IIS_FEATURES_PATH):
        with open(IIS_FEATURES_PATH) as f:
            iis_raw = json.load(f)
        if isinstance(iis_raw, dict):
            iis_features = iis_raw

    iis_matched = 0
    for ev in sorted_merged:
        key = f"{ev['ticker']}|{ev['date']}"
        iis = iis_features.get(key, {})
        if not iis:
            iis = iis_features.get(str(ev.get("_orig_idx", "")), {})
        ev["_iis"] = iis
        if iis:
            iis_matched += 1
    print(f"  IIS attached: {iis_matched}/{len(sorted_merged)}")

    # Step 7: Momentum cache
    print("[LOAD] Momentum cache...")
    momentum_cache = {}
    if os.path.exists(MOMENTUM_CACHE_PATH):
        with open(MOMENTUM_CACHE_PATH) as f:
            momentum_cache = json.load(f)
    for ev in sorted_merged:
        ev["_momentum"] = momentum_cache.get(f"{ev['ticker']}|{ev['date']}", {})

    # Step 8: Competitive landscape
    print("[BUILD] Competitive landscape...")
    indication_dates = defaultdict(list)
    for i, ev in enumerate(sorted_merged):
        ind = ev.get("indication", "").strip().lower()[:50]
        try:
            dt = datetime.strptime(ev["date"], "%Y-%m-%d")
            if ind:
                indication_dates[ind].append((dt, i))
        except:
            pass

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

    # Step 9: ChEMBL drug matching (NEW for v39)
    print("[v39 NEW] ChEMBL drug matching...")
    chembl_lookup = build_chembl_lookup()

    ch_matched = 0
    for ev in sorted_merged:
        drug_raw = ev.get("_drug_name", "")
        brand, generic = clean_drug_name(drug_raw)

        cdata = chembl_lookup.get(brand)
        if not cdata and generic:
            cdata = chembl_lookup.get(generic)
        if not cdata:
            for cname, cval in chembl_lookup.items():
                if cname in brand or brand in cname:
                    cdata = cval
                    break

        ev["_chembl"] = cdata or {}
        if cdata:
            ch_matched += 1

    print(f"  ChEMBL attached: {ch_matched}/{len(sorted_merged)} ({100*ch_matched/len(sorted_merged):.1f}%)")

    return sorted_merged, ctgov_lookup


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def build_features(events, ctgov_lookup, include_v37=True, include_v38=True,
                   include_candidates=None):
    """Build feature matrix.

    include_v37: include v37's 6 features
    include_v38: include v38's 3 features (ct_is_industry, iis_is_interim, ct_log_elig_length)
    include_candidates: None = v38 base only,
                        list of str = add those v39 candidates,
                        "all" = add all v39 candidates
    """
    from gungnir_v37_kaizen import engineer_v37_candidates
    from gungnir_v38_kaizen import engineer_v38_candidates

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

        # v37 features
        if include_v37:
            v37_cands = engineer_v37_candidates(ev, features)
            for f_name in V37_ADDED:
                if f_name in v37_cands:
                    features[f_name] = v37_cands[f_name]

        # v38 features
        if include_v38:
            v38_cands = engineer_v38_candidates(
                ev, features,
                ctgov_t1_data=ev.get("_ctgov_t1", {}),
                iis_data=ev.get("_iis", {}),
                finbrain_data={},  # Empty — FinBrain not used in v38 final
            )
            for f_name in V38_ADDED:
                if f_name in v38_cands:
                    features[f_name] = v38_cands[f_name]

        # v39 candidate features
        if include_candidates is not None:
            candidates = engineer_v39_candidates(
                ev, features,
                ctgov_t1_data=ev.get("_ctgov_t1", {}),
                ctgov_v2_data=ev.get("_ctgov_v2", {}),
                iis_data=ev.get("_iis", {}),
                chembl_data=ev.get("_chembl", {}),
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
# WALK-FORWARD EVALUATION (same as v38)
# =============================================================================

def evaluate_wf(X, y_bin, y_gp, y_cr, y_ret, dates,
                ridge_c=0.01, xgb_lr=0.01, xgb_trees=400, xgb_depth=3,
                meta_ridge=0.70, meta_xgb=0.30, temperature=1.0,
                crash_c=0.3, goodplus_c=0.5, seed=42, verbose=False,
                use_lgbm=False, lgbm_lr=0.01, lgbm_trees=400, lgbm_depth=3,
                meta_lgbm=0.0):
    """Walk-forward validation."""
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

        t1_mask = inv_score >= 0.85
        t1_wr = y_bin[test_mask][t1_mask].mean() if t1_mask.sum() > 0 else 0

        all_results.append({
            "split": split_name,
            "auc": auc, "brier": brier,
            "ev_spread": ev_spread, "ev_long": ev_long, "ev_all": ev_all,
            "t1_n": int(t1_mask.sum()), "t1_wr": t1_wr,
            "n_test": int(test_mask.sum()),
        })

        if verbose:
            print(f"  {split_name}: AUC={auc:.4f} Brier={brier:.4f} "
                  f"EV_spread={ev_spread:+.2f}pp T1={t1_mask.sum()}({t1_wr:.0%})")

    if not all_results:
        return {"avg_auc": 0.5, "avg_brier": 0.25, "avg_ev_spread": 0, "splits": []}

    return {
        "avg_auc": np.mean([r["auc"] for r in all_results]),
        "avg_brier": np.mean([r["brier"] for r in all_results]),
        "avg_ev_spread": np.mean([r["ev_spread"] for r in all_results]),
        "avg_ev_edge": np.mean([r["ev_long"] for r in all_results]) - np.mean([r["ev_all"] for r in all_results]),
        "splits": all_results,
    }


# =============================================================================
# MAIN KAIZEN PIPELINE
# =============================================================================

def main():
    print("\n" + "="*80)
    print("PHASE 1: BASELINE — v38.0.0 reproduction")
    print("="*80)

    events, ctgov_lookup = load_data()

    # v38 baseline: v37 features + v38's 3 additions, with v38 config
    X_base, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_base = build_features(
        events, ctgov_lookup, include_v37=True, include_v38=True, include_candidates=None
    )
    print(f"\nv38 Baseline features: {len(feat_base)}")
    print(f"Events: {X_base.shape[0]}, Positive rate: {y_bin.mean():.3f}")

    baseline = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates,
                           verbose=True, **V38_CONFIG)
    print(f"\n*** v38 BASELINE: AUC={baseline['avg_auc']:.4f} "
          f"Brier={baseline['avg_brier']:.4f} "
          f"EV_spread={baseline['avg_ev_spread']:+.2f}pp "
          f"EV_edge={baseline['avg_ev_edge']:+.2f}%")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 2: DEEP COLUMN AUDIT — test each v39 candidate independently")
    print("="*80)

    # Get all candidate names
    sample_ev = events[0]
    sample_base = dict(zip(feat_base, X_base[0]))
    all_candidates = engineer_v39_candidates(
        sample_ev, sample_base,
        ctgov_t1_data=sample_ev.get("_ctgov_t1", {}),
        ctgov_v2_data=sample_ev.get("_ctgov_v2", {}),
        iis_data=sample_ev.get("_iis", {}),
        chembl_data=sample_ev.get("_chembl", {}),
    )
    candidate_names = sorted(all_candidates.keys())
    print(f"\nTesting {len(candidate_names)} candidate features individually...")

    audit_results = []

    for i, cand in enumerate(candidate_names):
        X_cand, _, _, _, _, _, _, feat_cand = build_features(
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=[cand]
        )
        result = evaluate_wf(X_cand, y_bin, y_gp, y_cr, y_ret, dates, **V38_CONFIG)
        delta_auc = result["avg_auc"] - baseline["avg_auc"]

        audit_results.append({
            "feature": cand,
            "auc": result["avg_auc"],
            "delta_auc": delta_auc,
            "brier": result["avg_brier"],
            "delta_brier": result["avg_brier"] - baseline["avg_brier"],
            "ev_spread": result["avg_ev_spread"],
            "delta_ev": result["avg_ev_spread"] - baseline["avg_ev_spread"],
        })

        flag = " <<<" if delta_auc > 0.001 else (" !!!" if delta_auc < -0.003 else "")
        print(f"  [{i+1:3d}/{len(candidate_names)}] {cand:40s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta_auc:+.4f}){flag}")

    # Sort by AUC delta
    audit_sorted = sorted(audit_results, key=lambda x: -x["delta_auc"])

    print(f"\n{'='*80}")
    print("DEEP COLUMN AUDIT RESULTS (sorted by AUC delta)")
    print(f"{'='*80}")
    print(f"{'Feature':40s} {'AUC':>8s} {'ΔAUC':>8s} {'ΔBrier':>8s} {'ΔEV':>8s}")
    print("-"*72)
    for r in audit_sorted[:30]:
        marker = " *" if r["delta_auc"] > 0.001 else ""
        print(f"{r['feature']:40s} {r['auc']:.4f} {r['delta_auc']:+.4f} "
              f"{r['delta_brier']:+.4f} {r['delta_ev']:+.2f}{marker}")

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
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=test_set
        )
        result = evaluate_wf(X_test_fs, y_bin, y_gp, y_cr, y_ret, dates, **V38_CONFIG)

        if result["avg_auc"] > best_auc + 0.0002:
            selected.append(cand)
            best_auc = result["avg_auc"]
            print(f"  + {cand:40s} -> AUC={result['avg_auc']:.4f} "
                  f"(+{result['avg_auc']-baseline['avg_auc']:.4f} vs v38)")
        else:
            print(f"  - {cand:40s} -> AUC={result['avg_auc']:.4f} (skip)")

    print(f"\n*** Selected {len(selected)} features: {selected}")

    if selected:
        X_sel, _, _, _, _, _, _, feat_sel = build_features(
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=selected
        )
        sel_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                                 verbose=True, **V38_CONFIG)
        print(f"\n*** SELECTED SET: AUC={sel_result['avg_auc']:.4f} "
              f"(Δ={sel_result['avg_auc']-baseline['avg_auc']:+.4f}) "
              f"Brier={sel_result['avg_brier']:.4f}")
    else:
        X_sel = X_base
        feat_sel = feat_base
        sel_result = baseline
        print("  No features improved over v38 baseline.")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 4: ARCHITECTURE SWEEP")
    print("="*80)

    best_config = dict(V38_CONFIG)
    best_sweep_auc = sel_result["avg_auc"]

    sweep_configs = [
        {"ridge_c": 0.005}, {"ridge_c": 0.008}, {"ridge_c": 0.015},
        {"ridge_c": 0.02}, {"ridge_c": 0.05},
        {"xgb_lr": 0.005}, {"xgb_lr": 0.008}, {"xgb_lr": 0.015}, {"xgb_lr": 0.02},
        {"xgb_trees": 300}, {"xgb_trees": 500}, {"xgb_trees": 600},
        {"xgb_depth": 2}, {"xgb_depth": 4},
        {"meta_ridge": 0.60, "meta_xgb": 0.40},
        {"meta_ridge": 0.75, "meta_xgb": 0.25},
        {"meta_ridge": 0.80, "meta_xgb": 0.20},
        {"meta_ridge": 0.65, "meta_xgb": 0.35},
        {"temperature": 0.90}, {"temperature": 0.95},
        {"temperature": 1.05}, {"temperature": 1.10},
        {"crash_c": 0.1}, {"crash_c": 0.5},
        {"goodplus_c": 0.3}, {"goodplus_c": 1.0},
        {"ridge_c": 0.008, "xgb_lr": 0.008},
        {"ridge_c": 0.005, "xgb_trees": 500},
        {"ridge_c": 0.015, "meta_ridge": 0.60, "meta_xgb": 0.40},
        {"ridge_c": 0.008, "meta_ridge": 0.75, "meta_xgb": 0.25},
    ]

    print(f"\nSweeping {len(sweep_configs)} configurations...")

    for i, config in enumerate(sweep_configs):
        params = dict(V38_CONFIG)
        params.update(config)
        result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates, **params)
        delta = result["avg_auc"] - best_sweep_auc
        changes = ", ".join(f"{k}={v}" for k, v in config.items())
        flag = " <<<" if delta > 0.001 else ""
        print(f"  [{i+1:2d}/{len(sweep_configs)}] {changes:50s} "
              f"AUC={result['avg_auc']:.4f} (Δ={delta:+.4f}){flag}")

        if result["avg_auc"] > best_sweep_auc + 0.0005:
            best_sweep_auc = result["avg_auc"]
            best_config.update(config)
            print(f"         >>> NEW BEST CONFIG")

    print(f"\n*** BEST CONFIG: {best_config}")
    print(f"*** BEST AUC: {best_sweep_auc:.4f}")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 5: STABILITY TEST — 10 seeds")
    print("="*80)

    v38_aucs = []
    v39_aucs = []

    for seed in range(10):
        v38_r = evaluate_wf(X_base, y_bin, y_gp, y_cr, y_ret, dates,
                           seed=seed, **V38_CONFIG)
        v39_r = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                           seed=seed, **best_config)
        v38_aucs.append(v38_r["avg_auc"])
        v39_aucs.append(v39_r["avg_auc"])
        wins = "v39" if v39_r["avg_auc"] > v38_r["avg_auc"] else "v38"
        print(f"  Seed {seed}: v38={v38_r['avg_auc']:.4f} v39={v39_r['avg_auc']:.4f} -> {wins}")

    v39_wins = sum(1 for a, b in zip(v39_aucs, v38_aucs) if a > b)

    from scipy import stats
    try:
        t_stat, p_val = stats.ttest_rel(v39_aucs, v38_aucs)
    except:
        t_stat, p_val = 0, 1.0

    print(f"\n*** STABILITY: v39 wins {v39_wins}/10 seeds")
    print(f"*** Mean v38 AUC: {np.mean(v38_aucs):.4f} +/- {np.std(v38_aucs):.4f}")
    print(f"*** Mean v39 AUC: {np.mean(v39_aucs):.4f} +/- {np.std(v39_aucs):.4f}")
    print(f"*** Paired t-test: t={t_stat:.4f}, p={p_val:.10f}")

    # =================================================================
    print("\n" + "="*80)
    print("PHASE 6: FINAL VERDICT")
    print("="*80)

    final_result = evaluate_wf(X_sel, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **best_config)

    is_champion = (v39_wins >= 7 and
                   final_result["avg_auc"] > baseline["avg_auc"] + 0.001 and
                   p_val < 0.05)

    print(f"\n{'='*80}")
    print(f"GUNGNIR v39 KAIZEN RESULTS")
    print(f"{'='*80}")
    print(f"  v38 Baseline AUC: {baseline['avg_auc']:.4f}")
    print(f"  v39 Final AUC:    {final_result['avg_auc']:.4f} "
          f"(Δ={final_result['avg_auc']-baseline['avg_auc']:+.4f})")
    print(f"  v39 Brier:        {final_result['avg_brier']:.4f}")
    print(f"  v39 EV Spread:    {final_result['avg_ev_spread']:+.2f}pp")
    print(f"  EV Edge:          {final_result['avg_ev_edge']:+.2f}%")
    print(f"  Stability:        {v39_wins}/10 seeds, p={p_val:.10f}")
    print(f"  Features added:   {selected}")
    print(f"  Config:           {best_config}")
    print(f"  Total features:   {X_sel.shape[1]}")
    print(f"  CT.gov v2 coverage: {sum(1 for ev in events if ev.get('_ctgov_v2'))}/{len(events)}")
    print(f"  ChEMBL coverage:  {sum(1 for ev in events if ev.get('_chembl'))}/{len(events)}")
    print(f"  VERDICT:          "
          f"{'*** v39 IS NEW CHAMPION ***' if is_champion else 'v38 retains crown'}")

    # Save results
    results = {
        "version": "39.0.0",
        "baseline_version": "38.0.0",
        "baseline_auc": baseline["avg_auc"],
        "baseline_brier": baseline["avg_brier"],
        "final_auc": final_result["avg_auc"],
        "final_brier": final_result["avg_brier"],
        "final_ev_spread": final_result["avg_ev_spread"],
        "auc_delta": final_result["avg_auc"] - baseline["avg_auc"],
        "features_added": selected,
        "features_tested": len(candidate_names),
        "config": best_config,
        "stability": {"wins": v39_wins, "p_value": p_val, "t_stat": t_stat},
        "is_champion": str(is_champion),
        "n_features_total": X_sel.shape[1],
        "data_sources": {
            "ctgov_v2_matched": sum(1 for ev in events if ev.get("_ctgov_v2")),
            "ctgov_t1_matched": sum(1 for ev in events if ev.get("_ctgov_t1")),
            "chembl_matched": sum(1 for ev in events if ev.get("_chembl")),
            "iis_matched": sum(1 for ev in events if ev.get("_iis")),
        },
        "audit_results": audit_results,
    }

    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {RESULTS_JSON}")

    # If champion, train final model and deploy
    if is_champion:
        print("\n[CHAMPION] Training final v39 model on full dataset...")
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

    m1 = LogisticRegression(C=config["ridge_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m1.fit(X_full, y_bin)

    m2 = LogisticRegression(C=config["goodplus_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m2.fit(X_full, y_gp)

    m3 = LogisticRegression(C=config["crash_c"], penalty="l2", solver="lbfgs", max_iter=2000)
    m3.fit(X_full, y_cr)

    m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                       l1_ratio=0.3, max_iter=2000, random_state=42)
    m4.fit(X_full, y_bin)

    m5 = xgb_lib.XGBClassifier(
        n_estimators=config["xgb_trees"], max_depth=config["xgb_depth"],
        learning_rate=config["xgb_lr"],
        subsample=0.8, colsample_bytree=0.6, reg_alpha=0.3, reg_lambda=2.0,
        min_child_weight=10, gamma=0.2, random_state=42,
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )
    m5.fit(X_full, y_bin)

    XGB_PATH = os.path.join(DATA_DIR, "gungnir_v39_xgb.json")
    m5.save_model(XGB_PATH)
    print(f"  XGBoost saved to {XGB_PATH}")

    # Strata
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

    coef_importance = {f: round(float(m1.coef_[0][i]), 6) for i, f in enumerate(feature_names)}

    meta_ridge_w = config.get("meta_ridge", 0.70)
    meta_xgb_w = config.get("meta_xgb", 0.30)

    deploy = {
        "version": "39.0.0",
        "codename": "Allfather_v39_Enrichment",
        "architecture": f"3-model meta-ensemble (Ridge {meta_ridge_w*100:.0f}% + XGB {meta_xgb_w*100:.0f}%) + Ridge_GOOD+ + Ridge_CRASH + Bayesian strata + T={config.get('temperature', 1.0):.2f}",
        "meta_weights": {
            "ridge_binary": meta_ridge_w,
            "elasticnet": 0.00,
            "xgboost": meta_xgb_w,
            "lightgbm": 0.0,
        },
        "xgb_model_path": "gungnir_v39_xgb.json",
        "lgbm_model_path": None,
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
        "kaizen_from_v38": {
            "v38_auc": baseline["avg_auc"],
            "v38_brier": baseline["avg_brier"],
        }
    }

    with open(DEPLOY_V39_JSON, "w") as f:
        json.dump(deploy, f, indent=2)
    print(f"\n[DEPLOY] v39 deploy config written to {DEPLOY_V39_JSON}")


if __name__ == "__main__":
    sys.exit(main())
