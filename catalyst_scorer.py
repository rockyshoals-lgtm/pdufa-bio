#!/usr/bin/env python3
"""
================================================================================
CATALYST SCORER — Score All 2026 Catalysts with Gungnir + Readout Edge
================================================================================

Pipeline:
  1. Parse fda_2026 Excel (848 events with ticker, drug, NCT, indication, stage, price, etc.)
  2. Enrich via ClinicalTrials.gov API for NCT IDs → real trial design features
  3. Score with local Gungnir v30 engine (82-feature meta-ensemble)
  4. Apply readout analysis edge (size effect, TA edge, phase/outcome asymmetry)
  5. Combine into investment tier + expected value estimate
  6. Output JSON for dashboard rendering

USAGE:
  python catalyst_scorer.py                    # Full run
  python catalyst_scorer.py --skip-ctgov       # Use cached CT.gov data
"""

import csv, json, math, os, re, sys, time
from collections import defaultdict, Counter
from datetime import datetime
import urllib.request, urllib.parse
import warnings
warnings.filterwarnings("ignore")

# Add parent for allfather import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = "/sessions/loving-nifty-dirac/mnt/uploads/fda_2026-03-26.xlsx"
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
OUTPUT_JSON = os.path.join(DATA_DIR, "catalyst_scores.json")

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"

# =============================================================================
# READOUT EDGE SIGNALS (from our 1,752-event analysis)
# =============================================================================
# Phase x Size expected returns (avg return %)
PHASE_SIZE_EDGE = {
    # (phase, size_tier): (avg_ret, good_plus_rate, crash_rate)
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

# TA expected returns (avg return % for positive outcomes)
TA_EDGE = {
    "rare_disease": (23.4, 16.1, 3.2),  # (avg_ret_pos, good_plus_rate, crash_rate)
    "ophthalmology": (17.0, 23.1, 11.5),
    "cns": (9.0, 16.7, 22.1),
    "metabolic": (5.9, 11.2, 22.5),
    "oncology": (4.6, 7.2, 9.3),
    "immunology": (5.0, 7.8, 18.0),
    "infectious": (5.4, 3.8, 11.5),
    "cardiovascular": (3.1, 8.3, 13.1),
    "other": (6.9, 9.2, 16.2),
}

# Post-event drift by tier
DRIFT_EDGE = {
    "GREAT": +12.0,  # GREAT movers continue +12pp to D+5
    "GOOD": -0.8,
    "OKAY": -0.4,
}

# TA PATTERNS
TA_PATTERNS = {
    "oncology": r"(?i)(cancer|tumor|carcinoma|lymphoma|leukemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|neoplasm|malignant|metasta|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|cholang|solid.tumor|hematolog)",
    "cns": r"(?i)(alzheimer|parkinson|multiple.sclerosis|epilepsy|seizure|migraine|depression|schizophren|bipolar|anxiety|PTSD|autism|ADHD|huntington|ALS|amyotrophic|dementia|neuropath|neurodegen|stroke|psycho|cognitive|CNS|brain)",
    "cardiovascular": r"(?i)(heart|cardiac|cardio|coronary|atrial|arrhythm|hypertens|myocard|thrombo|embol|atheroscler|cholesterol|dyslipid|PAH|pulmonary.arterial|heart.failure|HFrEF|HFpEF)",
    "immunology": r"(?i)(rheumatoid|lupus|psoria|atopic|eczema|dermatit|crohn|colitis|IBD|ankylosing|autoimmun|graft.vs.host|GVHD|allerg|asthma|COPD|IPF|vasculit|alopecia)",
    "infectious": r"(?i)(HIV|AIDS|hepatitis|HBV|HCV|influenza|COVID|SARS|RSV|pneumonia|tuberculosis|malaria|herpes|HPV|antibiotic|antiviral|sepsis|infection)",
    "rare_disease": r"(?i)(orphan|rare.disease|duchenne|DMD|SMA|spinal.muscular|cystic.fibrosis|hemophilia|sickle.cell|thalassemia|gaucher|fabry|pompe|amyloid|ATTR|lysosomal|mucopolysaccharid|achondroplasia)",
    "metabolic": r"(?i)(diabetes|diabetic|insulin|HbA1c|GLP.?1|SGLT|obesity|obese|weight.loss|NASH|NAFLD|fatty.liver|metabolic|gout|osteopor)",
    "ophthalmology": r"(?i)(eye|ocular|ophthalm|retina|macular|AMD|glaucoma|uveitis|diabetic.retin|dry.eye|geographic.atrophy)",
}


def classify_ta(text):
    if not text:
        return "other"
    for ta, pattern in TA_PATTERNS.items():
        if re.search(pattern, text):
            return ta
    return "other"


def parse_phase(stage_str):
    if not stage_str:
        return None, False
    s = stage_str.upper()
    is_pdufa = "PDUFA" in s or "NDA" in s or "BLA" in s or "SNDA" in s or "BIOSIMILAR" in s
    if "3" in s: return 3, is_pdufa
    if "2B" in s: return 2, is_pdufa
    if "2A" in s: return 2, is_pdufa
    if "2/3" in s: return 3, is_pdufa
    if "2" in s: return 2, is_pdufa
    if "1/2" in s: return 2, is_pdufa
    if "1B" in s: return 1, is_pdufa
    if "1A" in s: return 1, is_pdufa
    if "1" in s: return 1, is_pdufa
    if is_pdufa: return 4, True  # Regulatory stage
    return None, is_pdufa


def size_tier(price):
    if price is None:
        return "mid"
    if price < 5:
        return "micro"
    if price < 20:
        return "small"
    if price < 80:
        return "mid"
    return "large"


# =============================================================================
# CT.GOV ENRICHMENT
# =============================================================================

def fetch_ctgov_batch(nct_ids, cache):
    """Fetch trial design features from CT.gov API for NCT IDs not in cache."""
    to_fetch = [n for n in nct_ids if n and n not in cache]
    print(f"[CTGOV] {len(cache)} cached, {len(to_fetch)} to fetch")

    # Fetch in batches of 5 using the search API with NCT filter
    for i in range(0, len(to_fetch), 5):
        batch = to_fetch[i:i+5]
        nct_filter = " OR ".join(f"AREA[NCTId] {nct}" for nct in batch)

        params = {
            "filter.advanced": nct_filter,
            "pageSize": 10,
            "format": "json",
        }
        url = f"{CTGOV_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "9Realms-CatalystScorer/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for study in data.get("studies", []):
                proto = study.get("protocolSection", {})
                nct = proto.get("identificationModule", {}).get("nctId", "")
                if not nct:
                    continue

                design = proto.get("designModule", {})
                design_info = design.get("designInfo", {})
                enrollment = design.get("enrollmentInfo", {})
                arms_mod = proto.get("armsInterventionsModule", {})
                outcomes_mod = proto.get("outcomesModule", {})
                elig_mod = proto.get("eligibilityModule", {})
                oversight = proto.get("oversightModule", {})
                sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
                status_mod = proto.get("statusModule", {})

                masking_info = design_info.get("maskingInfo", {})
                masking = masking_info.get("masking", "")
                who_masked = masking_info.get("whoMaskedList", masking_info.get("whoMasked", []))
                if isinstance(who_masked, dict):
                    who_masked = who_masked.get("whoMasked", [])

                arm_groups = arms_mod.get("armGroups", [])
                interventions = arms_mod.get("interventions", [])
                arm_types = [a.get("type", "").upper() for a in arm_groups]
                arm_labels = " ".join(a.get("label", "") for a in arm_groups).lower()
                interv_text = " ".join(iv.get("name", "") + " " + iv.get("description", "")
                                       for iv in interventions).lower()

                primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
                primary_text = " ".join(o.get("measure", "") + " " + o.get("description", "")
                                        for o in primary_outcomes)

                # Classify endpoint
                ep_hard = bool(re.search(r"(?i)(overall.survival|OS\b|progression.free|PFS\b|event.free|EFS|disease.free|DFS|death|mortality)", primary_text))
                ep_surrogate = bool(re.search(r"(?i)(response.rate|ORR|objective.response|complete.response|CR\b|pCR|biomarker|viral.load)", primary_text))
                ep_safety = bool(re.search(r"(?i)(safety|tolerability|adverse|AE\b|SAE|DLT|MTD)", primary_text))

                lead_sponsor = sponsor_mod.get("leadSponsor", {})
                collaborators = sponsor_mod.get("collaborators", [])
                locations = proto.get("contactsLocationsModule", {}).get("locations", [])
                countries = list(set(loc.get("country", "") for loc in locations if loc.get("country")))

                overall_status = status_mod.get("overallStatus", "")

                cache[nct] = {
                    "n_arms": len(arm_groups),
                    "n_interventions": len(interventions),
                    "enrollment": enrollment.get("count"),
                    "enrollment_type": enrollment.get("type", ""),
                    "allocation": design_info.get("allocation", ""),
                    "masking": masking,
                    "masking_rigor": len(who_masked) if isinstance(who_masked, list) else 0,
                    "is_randomized": 1 if "RANDOMIZED" in design_info.get("allocation", "").upper() else 0,
                    "is_double_blind": 1 if masking and ("DOUBLE" in masking.upper() or "TRIPLE" in masking.upper() or "QUADRUPLE" in masking.upper()) else 0,
                    "is_open_label": 1 if masking and ("NONE" in masking.upper() or "OPEN" in masking.upper()) else 0,
                    "is_placebo": 1 if ("PLACEBO" in " ".join(arm_types) or "placebo" in arm_labels or "placebo" in interv_text) else 0,
                    "has_active_comparator": 1 if "ACTIVE_COMPARATOR" in " ".join(arm_types) else 0,
                    "has_dmc": 1 if oversight.get("oversightHasDmc") else 0,
                    "is_fda_regulated": 1 if oversight.get("isFdaRegulatedDrug") else 0,
                    "n_primary_outcomes": len(primary_outcomes),
                    "n_secondary_outcomes": len(outcomes_mod.get("secondaryOutcomes", [])),
                    "ep_hard": 1 if ep_hard else 0,
                    "ep_surrogate": 1 if ep_surrogate else 0,
                    "ep_safety": 1 if ep_safety else 0,
                    "sponsor_name": lead_sponsor.get("name", ""),
                    "sponsor_class": lead_sponsor.get("class", ""),
                    "n_collaborators": len(collaborators),
                    "n_sites": len(locations),
                    "n_countries": len(countries),
                    "has_us_sites": 1 if "United States" in countries else 0,
                    "is_global": 1 if len(countries) >= 5 else 0,
                    "overall_status": overall_status,
                    "has_withdrawals": 1 if overall_status in ["TERMINATED", "WITHDRAWN", "SUSPENDED"] else 0,
                    "primary_endpoint_text": primary_text[:200],
                }

        except Exception as e:
            print(f"  [WARN] Batch fetch error: {e}")
            for nct in batch:
                if nct not in cache:
                    cache[nct] = {"error": str(e)}

        if (i + 5) % 50 == 0:
            print(f"  [{i+5}/{len(to_fetch)}] fetched...")

        time.sleep(0.35)

    return cache


# =============================================================================
# GUNGNIR FEATURE ENGINEERING FOR CATALYSTS
# =============================================================================

def build_gungnir_features(event, ctgov_data=None):
    """Build Gungnir v30 feature vector from catalyst event + CT.gov data."""
    features = {}

    phase = event.get("phase") or 2
    ta = event.get("ta", "other")
    price = event.get("price")
    cat_text = event.get("catalyst_text", "").lower()
    stage = event.get("stage", "").lower()

    # Phase features
    features["is_pivotal"] = 1 if phase >= 3 else 0
    features["is_P2"] = 1 if phase == 2 else 0
    features["is_phase1_any"] = 1 if phase == 1 else 0

    # TA features
    features["ta_oncology"] = 1 if ta == "oncology" else 0
    features["ta_cns"] = 1 if ta == "cns" else 0
    features["ta_rare"] = 1 if ta == "rare_disease" else 0
    features["ta_metabolic"] = 1 if ta == "metabolic" else 0
    features["ta_immunology"] = 1 if ta == "immunology" else 0
    features["ta_cardiovascular"] = 1 if ta == "cardiovascular" else 0
    features["ta_infectious"] = 1 if ta == "infectious" else 0

    # TA base rates (historical)
    ta_rates = {"oncology": 0.55, "cns": 0.45, "rare_disease": 0.60, "metabolic": 0.58,
                "immunology": 0.52, "cardiovascular": 0.48, "infectious": 0.50,
                "ophthalmology": 0.55, "other": 0.50}
    features["ta_base_rate"] = ta_rates.get(ta, 0.50)

    # Designation signals from text
    features["odin_btd"] = 1 if re.search(r"(?i)(breakthrough|BTD)", cat_text + " " + event.get("status", "")) else 0
    features["odin_priority"] = 1 if re.search(r"(?i)(priority.review|fast.track|FTD)", cat_text + " " + event.get("status", "")) else 0
    features["designation_count"] = features["odin_btd"] + features["odin_priority"]

    # NLP signals from catalyst text
    features["has_prior_positive"] = 1 if re.search(r"(?i)(met.*primary|positive|significant|efficacy|durable|superior|improvement)", cat_text) else 0
    features["has_prior_negative"] = 1 if re.search(r"(?i)(did not meet|failed|miss|not meet|discontinued|terminated|halted)", cat_text) else 0
    features["has_ppm"] = 1 if re.search(r"(?i)(post.?marketing|phase.?4|real.?world)", cat_text) else 0

    # Journey signals from text
    features["journey_had_prior_positive"] = features["has_prior_positive"]
    features["journey_had_prior_negative"] = features["has_prior_negative"]
    features["journey_had_p2_positive"] = 1 if re.search(r"(?i)(phase.?2.*met|phase.?2.*positive|phase.?2.*significant|phase.?2.*improvement)", cat_text) else 0
    features["journey_last_outcome_positive"] = 1.0 if features["has_prior_positive"] and not features["has_prior_negative"] else 0.5
    features["journey_n_prior_readouts"] = 1 if features["has_prior_positive"] or features["has_prior_negative"] else 0
    features["journey_positive_streak"] = math.log1p(2) if features["has_prior_positive"] else 0
    features["journey_drug_success_rate"] = 0.8 if features["has_prior_positive"] else 0.5

    # Sponsor signals
    features["sponsor_success_rate"] = 0.6  # default
    if re.search(r"(?i)(pfizer|roche|novartis|merck|bristol|abbvie|lilly|amgen|johnson|astrazeneca|gilead|sanofi|gsk|bayer|takeda|regeneron|vertex|biogen)", event.get("name", "")):
        features["sponsor_success_rate"] = 0.65
    if re.search(r"(?i)(preclinical|IND)", stage):
        features["sponsor_success_rate"] = 0.45

    # Era
    features["era_post_2024"] = 1

    # Interactions
    features["phase3_x_cns"] = features["is_pivotal"] * features["ta_cns"]
    features["is_gene_therapy"] = 1 if re.search(r"(?i)(gene.therapy|AAV|lentivir|crispr|cas9|base.edit|prime.edit)", cat_text + " " + event.get("drug", "")) else 0

    # CT.gov enrichment
    ctgov = ctgov_data or {}
    if "error" not in ctgov and ctgov:
        enroll = ctgov.get("enrollment")
        features["log_enrollment"] = math.log(max(enroll, 1)) if enroll else math.log(100)
        features["is_double_blind"] = ctgov.get("is_double_blind", 0)
        features["endpoint_hardness"] = ctgov.get("ep_hard", 0)
        features["uses_surrogate"] = ctgov.get("ep_surrogate", 0)
        features["ctgov_n_arms"] = ctgov.get("n_arms", 2)
        features["ctgov_masking_rigor"] = ctgov.get("masking_rigor", 0)
        features["ctgov_placebo"] = ctgov.get("is_placebo", 0)
        features["ctgov_has_withdrawals"] = ctgov.get("has_withdrawals", 0)
        features["ctgov_real_enrollment"] = math.log(max(enroll, 1)) if enroll else 0
        features["ctgov_n_sites"] = ctgov.get("n_sites", 0)
        features["competitive_count"] = 0  # would need broader analysis
    else:
        # Phase-average imputation (honest — no hash-based fake data)
        PHASE_AVG = {
            1: {"enrollment": 146, "blind": 0.35, "hard": 0.25, "surrogate": 0.60},
            2: {"enrollment": 247, "blind": 0.55, "hard": 0.35, "surrogate": 0.50},
            3: {"enrollment": 1287, "blind": 0.72, "hard": 0.50, "surrogate": 0.35},
        }
        pa = PHASE_AVG.get(phase, PHASE_AVG[2])
        features["log_enrollment"] = math.log(max(pa["enrollment"], 1))
        features["is_double_blind"] = round(pa["blind"])
        features["endpoint_hardness"] = pa["hard"]
        features["uses_surrogate"] = round(pa["surrogate"])
        features["ctgov_n_arms"] = 2 if phase >= 2 else 1
        features["ctgov_masking_rigor"] = 2 if features["is_double_blind"] else 0
        features["ctgov_placebo"] = 1 if features["is_double_blind"] else 0
        features["ctgov_has_withdrawals"] = 0
        features["ctgov_real_enrollment"] = 0
        features["ctgov_n_sites"] = 0
        features["competitive_count"] = 0

    # Indication for overlay
    features["indication"] = event.get("indication", "")
    features["_indication"] = event.get("indication", "")

    return features


# =============================================================================
# INVESTMENT SCORING
# =============================================================================

def compute_investment_score(gungnir_result, event):
    """
    Combine Gungnir probability with readout analysis edge data to produce
    an investment score and expected value estimate.
    """
    prob = gungnir_result["probability"]
    tier = gungnir_result["tier"]
    phase = event.get("phase") or 2
    stier = event.get("size_tier", "mid")
    ta = event.get("ta", "other")
    price = event.get("price")
    is_pdufa = event.get("is_pdufa", False)

    # Lookup edge data
    size_edge = PHASE_SIZE_EDGE.get((phase, stier), (0, 5, 10))
    ta_edge = TA_EDGE.get(ta, (5.0, 9.0, 15.0))

    avg_ret_if_positive = size_edge[0]  # avg return for positive outcome at this phase/size
    good_plus_rate = size_edge[1]       # % chance of GOOD or GREAT move
    crash_rate = size_edge[2]           # % chance of CRASH

    # Expected value = P(positive) * E[return|positive] + P(negative) * E[return|negative]
    # From our data: negative outcomes average about -15% for phase 3, -18% for phase 2
    neg_avg = {1: -3, 2: -19, 3: -14, 4: -5}.get(phase, -10)
    ev = prob * avg_ret_if_positive + (1 - prob) * neg_avg

    # Risk-adjusted score (0-100)
    # Factors: Gungnir probability, expected value, good+ rate, inverse crash rate
    raw_score = (
        prob * 35 +                         # 35% weight: model confidence
        max(ev, 0) / 30 * 25 +             # 25% weight: expected value (capped)
        good_plus_rate / 25 * 20 +          # 20% weight: upside potential
        (1 - crash_rate / 50) * 20          # 20% weight: downside protection
    )
    investment_score = max(0, min(100, raw_score))

    # Investment tier
    if investment_score >= 75:
        inv_tier = "ALPHA"     # Highest conviction
        inv_action = "Strong Long"
    elif investment_score >= 55:
        inv_tier = "BETA"      # Good risk/reward
        inv_action = "Cautious Long"
    elif investment_score >= 40:
        inv_tier = "GAMMA"     # Monitor
        inv_action = "Watch / Small Position"
    elif investment_score >= 25:
        inv_tier = "DELTA"     # Low conviction
        inv_action = "Avoid / Very Small"
    else:
        inv_tier = "OMEGA"     # Negative EV
        inv_action = "No Trade / Consider Short"

    # Size-adjusted position recommendation (% of portfolio)
    if inv_tier == "ALPHA":
        position = "3-5%" if stier in ["small", "micro"] else "2-3%"
    elif inv_tier == "BETA":
        position = "2-3%" if stier in ["small", "micro"] else "1-2%"
    elif inv_tier == "GAMMA":
        position = "1%" if stier in ["small", "micro"] else "0.5%"
    else:
        position = "0%"

    # Special flags
    flags = []
    if stier in ["micro", "small"] and phase >= 3 and prob >= 0.6:
        flags.append("MONSTER_POTENTIAL")
    if ta == "rare_disease" and prob >= 0.55:
        flags.append("RARE_DISEASE_EDGE")
    if ta == "cns" and phase >= 3:
        flags.append("CNS_HIGH_VARIANCE")
    if stier == "large":
        flags.append("LARGE_CAP_MUTED")
    if crash_rate >= 20:
        flags.append("HIGH_CRASH_RISK")
    if is_pdufa:
        flags.append("PDUFA_EVENT")

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
        "ta_edge": {
            "ta": ta,
            "avg_ret_positive": ta_edge[0],
            "good_plus_rate": ta_edge[1],
        },
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ctgov", action="store_true")
    args = parser.parse_args()

    print("=" * 80)
    print("CATALYST SCORER — 2026 Biotech Catalyst Investment Engine")
    print("=" * 80)

    # Step 1: Load Excel
    import openpyxl
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    data_rows = rows[1:]
    print(f"\n[LOAD] {len(data_rows)} catalysts from Excel")

    # Parse events
    events = []
    for r in data_rows:
        ticker = str(r[0] or "").strip()
        if not ticker:
            continue

        try:
            price = float(r[2]) if r[2] else None
        except:
            price = None

        try:
            mcap = float(r[14]) if r[14] else None
        except:
            mcap = None

        phase, is_pdufa = parse_phase(str(r[6] or ""))
        ta = classify_ta(str(r[5] or "") + " " + str(r[3] or ""))
        stier = size_tier(price)

        cat_date = str(r[9] or "")
        hist_loa = None
        try:
            hist_loa = float(r[12]) if r[12] else None
        except:
            pass
        hist_pop = None
        try:
            hist_pop = float(r[13]) if r[13] else None
        except:
            pass

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
            "catalyst_date": cat_date,
            "catalyst_text": str(r[10] or ""),
            "conference": str(r[11] or ""),
            "hist_loa": hist_loa,
            "hist_pop": hist_pop,
            "market_cap": mcap,
            "phase": phase,
            "is_pdufa": is_pdufa,
            "ta": ta,
            "size_tier": stier,
        })

    print(f"[PARSE] {len(events)} events parsed")

    # Step 2: CT.gov enrichment
    ctgov_cache = {}
    if os.path.exists(CTGOV_CACHE):
        with open(CTGOV_CACHE) as f:
            ctgov_cache = json.load(f)

    nct_ids = [e["nct_id"] for e in events if e["nct_id"].startswith("NCT")]
    print(f"\n[CTGOV] {len(nct_ids)} events with NCT IDs")

    if not args.skip_ctgov:
        ctgov_cache = fetch_ctgov_batch(nct_ids, ctgov_cache)
        with open(CTGOV_CACHE, "w") as f:
            json.dump(ctgov_cache, f)
        print(f"[CTGOV] Cache: {len(ctgov_cache)} entries")
    else:
        print(f"[SKIP] Using {len(ctgov_cache)} cached entries")

    # Step 3: Load Gungnir engine
    from allfather_v2 import GungnirV30, OdinV6
    gungnir = GungnirV30()
    print(f"\n[ENGINE] Gungnir v{gungnir.version} loaded ({len(gungnir.features)} features)")

    try:
        odin = OdinV6()
        has_odin = True
        print(f"[ENGINE] ODIN v{odin.version} loaded ({len(odin.features)} features)")
    except:
        has_odin = False

    # Step 4: Score all events
    print(f"\n[SCORE] Scoring {len(events)} catalysts...")
    scored = []
    for i, event in enumerate(events):
        nct = event["nct_id"]
        ctgov_data = ctgov_cache.get(nct, {})

        # Build features
        features = build_gungnir_features(event, ctgov_data)

        # Score with Gungnir
        gungnir_result = gungnir.score(features)

        # Compute investment score
        inv_result = compute_investment_score(gungnir_result, event)

        scored.append({
            # Core identity
            "ticker": event["ticker"],
            "name": event["name"],
            "drug": event["drug"],
            "indication": event["indication"],
            "stage": event["stage"],
            "status": event["status"],
            "next_catalyst": event["next_catalyst"],
            "catalyst_date": event["catalyst_date"],
            "conference": event["conference"],

            # Pricing
            "price": event["price"],
            "market_cap": event["market_cap"],
            "size_tier": event["size_tier"],

            # Classification
            "phase": event["phase"],
            "is_pdufa": event["is_pdufa"],
            "ta": event["ta"],
            "hist_loa": event["hist_loa"],
            "hist_pop": event["hist_pop"],

            # CT.gov enrichment
            "has_ctgov": bool(ctgov_data and "error" not in ctgov_data),
            "ctgov": {
                "enrollment": ctgov_data.get("enrollment"),
                "is_randomized": ctgov_data.get("is_randomized"),
                "is_double_blind": ctgov_data.get("is_double_blind"),
                "is_placebo": ctgov_data.get("is_placebo"),
                "has_dmc": ctgov_data.get("has_dmc"),
                "n_arms": ctgov_data.get("n_arms"),
                "ep_hard": ctgov_data.get("ep_hard"),
                "ep_surrogate": ctgov_data.get("ep_surrogate"),
                "n_sites": ctgov_data.get("n_sites"),
                "n_countries": ctgov_data.get("n_countries"),
                "has_us_sites": ctgov_data.get("has_us_sites"),
                "status": ctgov_data.get("overall_status"),
            } if ctgov_data and "error" not in ctgov_data else {},

            # Gungnir score
            "gungnir_probability": gungnir_result["probability"],
            "gungnir_tier": gungnir_result["tier"],
            "gungnir_tier_label": gungnir_result["tier_label"],
            "gungnir_overlay": gungnir_result.get("overlay_applied", []),

            # Investment score
            **inv_result,
        })

    # Sort by investment score descending
    scored.sort(key=lambda x: -x["investment_score"])

    # Step 5: Write output
    with open(OUTPUT_JSON, "w") as f:
        json.dump(scored, f, indent=2, default=str)
    print(f"\n[OUTPUT] {len(scored)} scored catalysts → {OUTPUT_JSON}")

    # Summary
    tier_counts = Counter(s["investment_tier"] for s in scored)
    print(f"\n{'='*80}")
    print("INVESTMENT TIER SUMMARY")
    print(f"{'='*80}")
    for t in ["ALPHA", "BETA", "GAMMA", "DELTA", "OMEGA"]:
        cnt = tier_counts.get(t, 0)
        subset = [s for s in scored if s["investment_tier"] == t]
        avg_score = sum(s["investment_score"] for s in subset) / max(len(subset), 1)
        avg_ev = sum(s["expected_value"] for s in subset) / max(len(subset), 1)
        print(f"  {t:6s}: {cnt:4d} catalysts  avg_score={avg_score:.1f}  avg_EV={avg_ev:+.1f}%")

    print(f"\n  Top 10 ALPHA Picks:")
    for s in scored[:10]:
        print(f"    {s['investment_score']:5.1f}  {s['ticker']:6s}  ${s['price'] or 0:>8.2f}  P{s['phase']}  "
              f"{s['ta']:12s}  Gungnir={s['gungnir_probability']*100:.0f}%  EV={s['expected_value']:+.1f}%  "
              f"{s['drug'][:35]}")

    print(f"\n[DONE]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
