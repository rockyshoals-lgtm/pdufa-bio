#!/usr/bin/env python3
"""
================================================================================
ALLFATHER ENRICHMENT V2 — Gungnir Dataset T-1 Feature Engineering Pipeline
================================================================================

Combines both Gungnir datasets (enriched_gungnir_dataset.csv + historical_readouts_2000.csv),
then engineers 80+ features from:
  1. Text columns (NLP from Catalyst description)
  2. Therapeutic area classification (regex from Indication)
  3. Phase/stage encoding
  4. Trial design estimation (blinding, enrollment, endpoints)
  5. Drug journey features (temporal cross-referencing within dataset)
  6. ClinicalTrials.gov API v2 batch enrichment (10 real trial features)
  7. Financial features (log_price from Price At Catalyst Date)
  8. Interaction terms

Outputs: allfather_gungnir_enriched.csv with 82 features + metadata columns

T-1 COMPLIANCE:
  - All features knowable at T-1 (day before catalyst/readout)
  - NLP features use sanitized text (post-readout language stripped)
  - Journey features use strict temporal < ordering
  - CTGOV features are trial design (pre-readout by definition)
  - Price is the price on catalyst date (proxy for company size, not outcome)
"""

import csv, math, re, hashlib, json, time, os, sys
from collections import defaultdict, Counter
from datetime import datetime
import urllib.request, urllib.parse

# ============================================================================
# PATHS
# ============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_readouts_2000.csv")
ODIN_CSV = os.path.join(DATA_DIR, "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
CTGOV_CACHE_FILE = os.path.join(DATA_DIR, "ctgov_cache_v2.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "allfather_gungnir_enriched.csv")

# ============================================================================
# CTGOV API CONFIG
# ============================================================================
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
CTGOV_FIELDS = [
    "NCTId", "BriefTitle", "Phase", "EnrollmentInfo", "DesignInfo",
    "ArmsInterventionsModule", "OutcomesModule", "StatusModule",
    "SponsorCollaboratorsModule", "EligibilityModule",
]
MEDIAN_ELIG_LENGTH = 3500

BIG_PHARMA_SPONSORS = {
    "pfizer", "merck", "eli lilly", "lilly", "abbvie", "bristol-myers squibb",
    "bristol myers squibb", "bms", "johnson & johnson", "janssen", "astrazeneca",
    "roche", "novartis", "sanofi", "gsk", "glaxosmithkline", "amgen", "gilead",
    "regeneron", "biogen", "vertex", "moderna", "biontech", "takeda", "novo nordisk",
    "teva", "bayer", "boehringer ingelheim", "daiichi sankyo", "astellas",
    "merck sharp & dohme", "merck & co", "f. hoffmann-la roche",
    "hoffmann-la roche", "genentech",
}

BIG_PHARMA_TICKERS = {
    "PFE","MRK","LLY","ABBV","BMY","JNJ","AZN","RHHBY","NVS","SNY",
    "GSK","AMGN","GILD","REGN","BIIB","VRTX","MRNA","BNTX","TAK","NVO",
    "TEVA","ROCHE","NOVARTIS","BAYER",
}

# ============================================================================
# TA + MODALITY PATTERNS (from v29)
# ============================================================================
TA_PATTERNS = {
    "ta_oncology": re.compile(r"cancer|tumor|tumour|lymphoma|leukemia|melanoma|carcinoma|myeloma|sarcoma|glioma|glioblastoma|oncolog|nsclc|solid\s+tumor|breast(?!\s*feed)|ovarian|pancreatic|colorectal|prostate\s+(?!hyper)", re.I),
    "ta_rare": re.compile(r"duchenne|sma|spinal\s+muscular|sickle\s+cell|cystic\s+fibrosis|hemophilia|fabry|gaucher|pompe|achondroplasia|rare|orphan|lysosom|ataxia|dystrophy|thalassemia", re.I),
    "ta_metabolic": re.compile(r"diabet|obes|metabol|nash|mash|steatohepatitis|cholesterol|lipid|glycem|hba1c|weight\s+(?:loss|manage)", re.I),
    "ta_infectious": re.compile(r"hiv|hepatitis|influenza|covid|sars|rsv|malaria|tuberculosis|tb\b|antibiotic|antibacterial|antiviral|antifungal|infection|infectious|pneumonia|sepsis", re.I),
    "ta_ophthalmology": re.compile(r"ophthalm|retina|macular|glaucoma|dry\s+eye|uveitis|diabetic\s+retinopath|geographic\s+atrophy|amd\b|dme\b", re.I),
    "ta_pain": re.compile(r"\bpain\b|fibromyalg|analges|nocicepti", re.I),
    "ta_cns": re.compile(r"alzheimer|parkinson|epilep|schizophren|depression|depressive|bipolar|multiple\s+sclerosis|(?:^|\W)als(?:\W|$)|amyotrophic|huntington|migraine|dementia|seizure|anxiety|ptsd|adhd|narcolep|stroke", re.I),
    "ta_immunology": re.compile(r"lupus|rheumatoid|crohn|colitis|psoria|atopic|eczema|inflam|autoimmun|immunolog|ibd|gvhd|dermati|ankylos|vasculit", re.I),
    "ta_cardiovascular": re.compile(r"cardiovasc|heart\s+fail|atrial|myocardial|coronary|hypertens|arrhyth|angina|cardiomyopath|thrombos|anticoagul|mace\b", re.I),
}

MODALITY_PATTERNS = {
    "gene_therapy": re.compile(r"gene\s*therap|aav|crispr|base\s*edit|lentivir", re.I),
    "adc": re.compile(r"antibody.drug\s+conjug|\badc\b|drug\s+conjugat", re.I),
    "small_molecule": re.compile(r"small\s+molecul|oral|tablet|capsule|inhibitor|antagonist|agonist", re.I),
    "antibody": re.compile(r"antibod|mab\b|-mab\b|bispecific", re.I),
}

COMPETITIVE_FULL = {
    "nsclc": 5, "non-small cell lung cancer": 5, "breast cancer": 4,
    "aml": 3, "acute myeloid leukemia": 3, "mdd": 4,
    "major depressive disorder": 4, "alzheimer": 3, "prostate cancer": 3,
    "type 2 diabetes": 5, "obesity": 4, "copd": 3, "asthma": 3,
    "chronic pain": 3, "als": 2, "multiple myeloma": 3,
    "non-hodgkin lymphoma": 2, "atopic dermatitis": 3, "psoriasis": 3,
    "rheumatoid arthritis": 3, "crohn": 2, "nash": 3, "mash": 3,
}

# TA-specific trial design statistics (from CTGOV aggregate analysis)
CTGOV_TA_STATS = {
    "p3_onc_blind_rate": 0.48, "p3_immuno_blind_rate": 0.83,
    "p3_cns_blind_rate": 0.67, "p3_metabolic_blind_rate": 0.56,
    "p3_rare_blind_rate": 0.29, "p3_infectious_blind_rate": 0.64,
    "p3_ophtho_blind_rate": 1.00, "p3_cardio_blind_rate": 0.56,
    "p3_generic_blind_rate": 0.55,
    "p3_onc_enroll": 435, "p3_immuno_enroll": 315, "p3_cns_enroll": 227,
    "p3_metabolic_enroll": 338, "p3_rare_enroll": 43, "p3_infectious_enroll": 480,
    "p3_ophtho_enroll": 1116, "p3_cardio_enroll": 450, "p3_generic_enroll": 400,
    "p3_onc_hard_rate": 0.64, "p3_immuno_hard_rate": 0.33,
    "p3_cns_hard_rate": 0.50, "p3_metabolic_hard_rate": 0.16,
    "p3_rare_hard_rate": 0.57, "p3_infectious_hard_rate": 0.48,
    "p3_ophtho_hard_rate": 0.50, "p3_cardio_hard_rate": 0.72,
    "p3_generic_hard_rate": 0.45,
    "p2_onc_blind_rate": 0.44, "p2_immuno_blind_rate": 0.69,
    "p2_generic_blind_rate": 0.40,
    "p2_onc_enroll": 63, "p2_immuno_enroll": 98, "p2_generic_enroll": 80,
    "p1_blind_rate": 0.15, "p1_enroll": 30,
}

# NLP patterns for sanitizing post-readout text (T-1 compliance)
_POST_READOUT = re.compile(r"(data\s+(?:released|reported|showed|presented|announced|demonstrated|revealed|from\s+\w+\s+(?:reported|showed)).*)", re.I | re.DOTALL)
_RESULT_PHRASES = re.compile(
    r"((?:met|failed|missed|did\s+not\s+meet|statistically\s+significant|not\s+statistically|"
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|"
    r"PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|median\s+\w+\s+was|"
    r"achieved|demonstrated\s+(?:statistical|significant|positive|negative)|"
    r"p[\s-]?value\s*(?:=|of|was)\s*[0-9]|hazard\s+ratio\s*(?:=|of|was)\s*[0-9]|"
    r"(?:complete|partial|overall)\s+response\s+rate\s+(?:was|of)\s+\d|"
    r"median\s+(?:PFS|OS|DFS|EFS|RFS)\s+(?:was|of)\s+\d|"
    r"(?:positive|negative|mixed|disappointing|encouraging)\s+(?:data|results|outcome|readout)|"
    r"(?:FDA|EMA)\s+(?:approved|rejected|accepted|refused)|"
    r"(?:stock|share|shares)\s+(?:surged|plummeted|jumped|dropped|fell|rose|spiked)"
    r").*?)(?:\.|$)", re.I)
_DESIGN_COMBO = re.compile(r"combination|combo|plus\s+\w+mab|with\s+\w+mab|\+\s+\w+mab", re.I)
_DESIGN_SURROGATE = re.compile(r"surrogate|biomarker|response\s+rate|tumor\s+(?:reduction|shrink)", re.I)


# ============================================================================
# FEATURE LIST (82 features — matching v29 deploy spec)
# ============================================================================
FEATURES_BASE = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain", "ta_cardiovascular",
    "is_gene_therapy", "is_adc", "is_small_molecule",
    "is_double_blind", "is_open_label", "is_combination",
    "uses_surrogate", "endpoint_hardness", "log_enrollment",
    "designation_count", "odin_btd", "odin_desig_rich", "odin_sponsor_exp",
    "has_ppm", "log_price", "era_post_2024",
    "is_topline", "mentions_primary", "endpoint_pfs",
    "is_competitive", "competitive_count",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "combo_x_oncology",
    "blind_x_phase3", "enroll_x_phase3",
    "os_x_oncology", "hard_x_phase3", "rare_small_enroll",
    "sponsor_success_rate", "enroll_vs_ta_median", "ta_base_rate",
    "desig_x_phase3", "sponsor_x_phase3", "is_antibody",
    "blind_x_oncology", "ppm_x_phase3",
]

JOURNEY_FEATURES = [
    "journey_had_prior_positive", "journey_had_prior_negative",
    "journey_n_prior_readouts", "journey_drug_success_rate",
    "journey_had_p2_positive", "journey_had_p1_positive",
    "journey_n_prior_positive", "journey_time_since_last",
    "journey_sponsor_n_drugs", "journey_prior_pos_x_p3",
    "journey_last_outcome_positive", "journey_positive_streak",
    "journey_sponsor_ta_sr", "journey_n_indications",
    "journey_phase_advanced", "journey_last_neg_x_p3",
    "journey_streak_x_p3",
    "is_q4", "journey_confidence",
]

CTGOV_FEATURES = [
    "ctgov_n_arms", "ctgov_placebo", "ctgov_masking_rigor",
    "ctgov_primary_os", "ctgov_primary_orr",
    "ctgov_strict_criteria", "ctgov_sponsor_scale",
    "ctgov_has_withdrawals", "ctgov_time_to_readout", "ctgov_phase_exact",
    "ctgov_placebo_x_p3", "ctgov_masking_x_onc", "ctgov_real_enrollment",
]

ALL_FEATURES = FEATURES_BASE + JOURNEY_FEATURES + CTGOV_FEATURES
N_FEATURES = len(ALL_FEATURES)


# ============================================================================
# HELPERS
# ============================================================================
def safe_float(s, default=0.0):
    try: return float(re.sub(r'[^0-9.\-]', '', str(s)))
    except: return default

def sanitize_text(text):
    """Strip post-readout language for T-1 compliance."""
    return _RESULT_PHRASES.sub("", _POST_READOUT.sub("", str(text))).strip()

def get_ta_key(indication):
    """Classify indication into therapeutic area."""
    for ta_name, ta_re in TA_PATTERNS.items():
        if ta_re.search(str(indication)):
            return ta_name.replace("ta_", "")
    return "generic"

def normalize_drug(asset):
    """Clean drug name for matching."""
    if not asset: return ""
    asset = str(asset).strip()
    m = re.search(r'\(([^)]+)\)', asset)
    if m:
        generic = m.group(1).strip()
        if not re.match(r'^[A-Z]{2,6}-?\d+$', generic) and len(generic) > 3:
            generic = re.sub(r'\d+\s*mg.*', '', generic).strip()
            return generic.lower()
    name = re.sub(r'\s*-\s*\(.*?\)', '', asset)
    name = re.sub(r'\s*\(.*?\)', '', name)
    name = re.sub(r'\d+\s*mg.*', '', name)
    return name.strip().lower()

def phase_bucket(stage):
    """Map stage string to CTGOV phase bucket."""
    s = str(stage).lower()
    if "phase 3" in s or "phase 2/3" in s or "2/3" in s: return "PHASE3"
    if "phase 2" in s: return "PHASE2"
    if "phase 1" in s: return "PHASE1"
    return None


# ============================================================================
# CTGOV API FUNCTIONS
# ============================================================================
def query_ctgov_api(drug_name, phase_filter=None, max_results=5):
    """Query ClinicalTrials.gov API v2 for a drug."""
    params = {
        "query.intr": drug_name,
        "pageSize": str(max_results),
        "fields": ",".join(CTGOV_FIELDS),
    }
    if phase_filter:
        params["filter.advanced"] = f"AREA[Phase]({phase_filter})"
    url = f"{CTGOV_API}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Allfather/2.0"})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        return data.get("studies", [])
    except Exception as e:
        return []


def extract_ctgov_trial_features(study):
    """Extract the 10 CTGOV features from a study JSON."""
    ps = study.get("protocolSection", {})
    design = ps.get("designModule", {})
    arms_mod = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    status = ps.get("statusModule", {})
    elig = ps.get("eligibilityModule", {})
    ident = ps.get("identificationModule", {})

    arm_groups = arms_mod.get("armGroups", [])
    design_info = design.get("designInfo", {})
    masking_info = design_info.get("maskingInfo", {})
    enrollment_info = design.get("enrollmentInfo", {})
    primary_outcomes = outcomes.get("primaryOutcomes", [])

    feats = {}

    # 1. ctgov_n_arms
    feats["ctgov_n_arms"] = len(arm_groups)

    # 2. ctgov_placebo
    arm_types = [a.get("type", "").upper() for a in arm_groups]
    arm_labels = [a.get("label", "").lower() for a in arm_groups]
    feats["ctgov_placebo"] = 1.0 if (
        "PLACEBO_COMPARATOR" in arm_types or
        any("placebo" in lbl for lbl in arm_labels)
    ) else 0.0

    # 3. ctgov_masking_rigor
    masking = masking_info.get("masking", "NONE").upper()
    masking_map = {"NONE": 0, "SINGLE": 1, "DOUBLE": 2, "TRIPLE": 3, "QUADRUPLE": 4}
    feats["ctgov_masking_rigor"] = masking_map.get(masking, 0)

    # 4-5. Primary endpoint type
    primary_text = " ".join(o.get("measure", "") for o in primary_outcomes).lower()
    feats["ctgov_primary_os"] = 1.0 if re.search(
        r"overall\s*survival|\bos\b|mortality|death|survival\s*(?:rate|time|endpoint)", primary_text
    ) else 0.0
    feats["ctgov_primary_orr"] = 1.0 if re.search(
        r"(?:overall|objective|complete|partial)\s*response\s*rate|\borr\b|\bcrr\b|tumor\s*response", primary_text
    ) else 0.0

    # 6. Eligibility strictness
    elig_text = elig.get("eligibilityCriteria", "")
    feats["ctgov_strict_criteria"] = 1.0 if len(elig_text) > MEDIAN_ELIG_LENGTH else 0.0

    # 7. Sponsor scale
    sponsor_name = sponsor.get("leadSponsor", {}).get("name", "").lower()
    feats["ctgov_sponsor_scale"] = 1.0 if any(bp in sponsor_name for bp in BIG_PHARMA_SPONSORS) else 0.0

    # 8. Withdrawals/terminations
    overall_status = status.get("overallStatus", "").upper()
    feats["ctgov_has_withdrawals"] = 1.0 if overall_status in ("WITHDRAWN", "SUSPENDED", "TERMINATED") else 0.0

    # 9. Time to readout (log days)
    try:
        start = status.get("startDateStruct", {}).get("date", "")
        comp = status.get("completionDateStruct", {}) or status.get("primaryCompletionDateStruct", {})
        comp_date = comp.get("date", "")
        if start and comp_date:
            fmt_s = "%Y-%m-%d" if len(start) > 7 else "%Y-%m"
            fmt_c = "%Y-%m-%d" if len(comp_date) > 7 else "%Y-%m"
            days = (datetime.strptime(comp_date, fmt_c) - datetime.strptime(start, fmt_s)).days
            feats["ctgov_time_to_readout"] = math.log1p(max(days, 0))
        else:
            feats["ctgov_time_to_readout"] = math.log1p(730)
    except:
        feats["ctgov_time_to_readout"] = math.log1p(730)

    # 10. Phase exact
    def phase_numeric(phases_list):
        if not phases_list: return 0
        joined = " ".join(phases_list).upper()
        if "PHASE3" in joined: return 3
        if "PHASE2" in joined: return 2
        if "PHASE1" in joined: return 1
        return 0
    feats["ctgov_phase_exact"] = phase_numeric(design.get("phases", []))

    # Bonus metadata
    feats["_enrollment"] = enrollment_info.get("count", 0)
    feats["_nct_id"] = ident.get("nctId", "")
    feats["_title"] = ident.get("briefTitle", "")[:100]
    feats["_sponsor"] = sponsor.get("leadSponsor", {}).get("name", "")
    feats["_status"] = overall_status

    return feats


def pick_best_trial(studies):
    """Select the most relevant trial from multiple results."""
    if not studies: return None
    scored = []
    for s in studies:
        ps = s.get("protocolSection", {})
        enroll = ps.get("designModule", {}).get("enrollmentInfo", {}).get("count", 0) or 0
        stat = ps.get("statusModule", {}).get("overallStatus", "").upper()
        score = enroll
        if stat == "COMPLETED": score += 10000
        elif stat in ("ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"): score += 5000
        elif stat in ("RECRUITING", "NOT_YET_RECRUITING"): score += 1000
        if stat in ("WITHDRAWN", "TERMINATED", "SUSPENDED"): score -= 5000
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def batch_ctgov_enrichment(events, cache_file):
    """Query CTGOV API for all unique drug/phase pairs, with caching."""
    print("\n" + "="*70)
    print("  CTGOV BATCH ENRICHMENT")
    print("="*70)

    # Load cache
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache = json.load(f)
        print(f"  Loaded cache: {len(cache)} entries")

    # Get unique drug/phase pairs
    pairs = set()
    for ev in events:
        drug = normalize_drug(ev.get("Drug", ""))
        phase = phase_bucket(ev.get("Stage", ""))
        if drug and phase and len(drug) >= 3:
            pairs.add((drug, phase))

    print(f"  Unique drug/phase pairs: {len(pairs)}")

    to_query = [(d, p) for d, p in pairs if f"{d}|{p}" not in cache]
    print(f"  Already cached: {len(pairs) - len(to_query)}")
    print(f"  To query: {len(to_query)}")

    if not to_query:
        print("  All drugs already cached!")
    else:
        n_found = 0
        n_miss = 0
        for i, (drug, phase) in enumerate(to_query):
            key = f"{drug}|{phase}"
            studies = query_ctgov_api(drug, phase, max_results=5)
            if studies:
                best = pick_best_trial(studies)
                if best:
                    feats = extract_ctgov_trial_features(best)
                    cache[key] = feats
                    n_found += 1
                else:
                    cache[key] = None
                    n_miss += 1
            else:
                cache[key] = None
                n_miss += 1

            if (i + 1) % 50 == 0:
                print(f"    Progress: {i+1}/{len(to_query)} (found: {n_found}, miss: {n_miss})")
                # Save checkpoint
                with open(cache_file, 'w') as f:
                    json.dump(cache, f, indent=1)

            # Rate limit: ~3 req/sec
            time.sleep(0.35)

        print(f"  Completed: found={n_found}, miss={n_miss}")

    # Save final cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=1)
    print(f"  Cache saved: {len(cache)} entries")

    n_with_data = sum(1 for v in cache.values() if v is not None)
    print(f"  Entries with data: {n_with_data}/{len(cache)} ({n_with_data/max(len(cache),1)*100:.1f}%)")

    return cache


# ============================================================================
# DATA LOADING
# ============================================================================
def load_and_merge_datasets():
    """Load and deduplicate both Gungnir datasets."""
    print("\n[1/6] Loading datasets...")

    rows = []
    for csv_path in [ENRICHED_CSV, HISTORICAL_CSV]:
        if not os.path.exists(csv_path):
            print(f"  WARNING: {csv_path} not found, skipping")
            continue
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        print(f"  Loaded {csv_path}: {len(rows)} cumulative rows")

    # Standardize column names
    for row in rows:
        # Map to consistent names matching v29 expectations
        if "Catalyst Date" in row and "catalyst_date" not in row:
            row["catalyst_date"] = row["Catalyst Date"]
        if "Ticker" in row and "ticker" not in row:
            row["ticker"] = row["Ticker"]
        if "Drug" in row and "asset" not in row:
            row["asset"] = row["Drug"]
        if "Indication" in row and "indication" not in row:
            row["indication"] = row["Indication"]
        if "Stage" in row and "stage" not in row:
            row["stage"] = row["Stage"]
        if "Catalyst" in row and "raw_catalyst_text" not in row:
            row["raw_catalyst_text"] = row["Catalyst"]
        if "outcome" in row and "parsed_outcome" not in row:
            row["parsed_outcome"] = row["outcome"].upper()
        if "Price At Catalyst Date" in row and "price_at_catalyst" not in row:
            row["price_at_catalyst"] = row["Price At Catalyst Date"]

    # Filter to binary outcomes only
    binary = [r for r in rows if r.get("parsed_outcome", "").strip() in ("POSITIVE", "NEGATIVE")]
    print(f"  Binary outcomes: {len(binary)}")

    # Sort by date
    binary.sort(key=lambda x: x.get("catalyst_date", ""))

    # Deduplicate on ticker|date|asset
    seen = set()
    deduped = []
    for row in binary:
        key = f"{row.get('ticker','')}|{row.get('catalyst_date','')}|{row.get('asset','')}"
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    print(f"  After dedup: {len(deduped)} events")
    print(f"  Date range: {deduped[0].get('catalyst_date','')} to {deduped[-1].get('catalyst_date','')}")
    print(f"  Positive rate: {sum(1 for r in deduped if r['parsed_outcome']=='POSITIVE')/len(deduped):.3f}")

    return deduped


# ============================================================================
# ODIN CROSS-REFERENCE INDEX
# ============================================================================
def build_odin_index():
    """Build lookup index from ODIN PDUFA dataset for designation features."""
    print("\n[2/6] Building ODIN cross-reference index...")

    if not os.path.exists(ODIN_CSV):
        print("  WARNING: ODIN dataset not found, designation features will be zero")
        return {}

    index = {}
    with open(ODIN_CSV) as f:
        for row in csv.DictReader(f):
            ticker = row.get("ticker", "").upper()
            asset = row.get("asset", "").strip().lower()
            asset_clean = re.sub(r'\s*\(.*?\)', '', asset).strip()

            def bv(s): return str(s).strip().upper() in ("TRUE", "1", "YES")

            entry = {
                "btd": bv(row.get("btd", "")),
                "orphan": bv(row.get("orphan", "")),
                "priority_review": bv(row.get("priority_review", "")),
                "fast_track": bv(row.get("fast_track", "")),
                "accelerated_approval": bv(row.get("accelerated_approval", "")),
                "surrogate_endpoint": bv(row.get("surrogate_endpoint", "")),
                "sponsor_prior_approvals": int(safe_float(row.get("sponsor_prior_approvals", "0"))),
            }
            entry["desig_count"] = sum([entry["btd"], entry["orphan"],
                entry["priority_review"], entry["fast_track"], entry["accelerated_approval"]])

            index[f"{ticker}|{asset_clean}"] = entry
            # Also index by individual words for fuzzy matching
            for w in set(re.findall(r'\b[a-z]{4,}\b', asset_clean)):
                key = f"{ticker}|{w}"
                if key not in index:
                    index[key] = entry

    print(f"  ODIN index: {len(index)} entries")
    return index


def odin_lookup(odin_index, ticker, asset):
    """Look up ODIN designation data for a Gungnir event."""
    ticker = ticker.upper()
    asset_clean = re.sub(r'\s*\(.*?\)', '', asset.strip().lower()).strip()
    hit = odin_index.get(f"{ticker}|{asset_clean}")
    if hit: return hit
    for w in sorted(set(re.findall(r'\b[a-z]{4,}\b', asset_clean)), key=len, reverse=True):
        hit = odin_index.get(f"{ticker}|{w}")
        if hit: return hit
    return None


# ============================================================================
# JOURNEY INDEX BUILDER
# ============================================================================
def build_journey_indices(all_events):
    """Build temporal indices for drug journey and sponsor history features."""
    print("[3/6] Building journey indices...")

    asset_journey = defaultdict(list)
    sponsor_drugs = defaultdict(list)
    sponsor_events = defaultdict(list)
    sponsor_ta_events = defaultdict(list)
    ppm_drug = defaultdict(list)

    for row in all_events:
        t = row.get("ticker", "").upper().strip()
        a = normalize_drug(row.get("asset", ""))
        d = row.get("catalyst_date", "").strip()
        outcome = row.get("parsed_outcome", "").strip()
        stage = row.get("stage", "").lower()
        indication = row.get("indication", "").lower()

        if t and a and d:
            asset_journey[(t, a)].append({
                "date": d, "outcome": outcome,
                "stage": stage, "indication": indication,
            })
            sponsor_drugs[t].append((d, a))

        if outcome in ("POSITIVE", "NEGATIVE"):
            o = 1 if outcome == "POSITIVE" else 0
            sponsor_events[t].append((d, o))
            ta = get_ta_key(indication)
            sponsor_ta_events[(t, ta)].append((d, o))

        if outcome == "POSITIVE":
            ppm_drug[(t, a)].append(d)

    print(f"  Drug journeys: {len(asset_journey)}")
    print(f"  Sponsors tracked: {len(sponsor_events)}")

    return asset_journey, sponsor_drugs, sponsor_events, sponsor_ta_events, ppm_drug


def compute_ta_base_rates(all_events, cutoff="2025-01-01"):
    """Compute TA-specific base rates from training data only."""
    ta_outcomes = defaultdict(list)
    for row in all_events:
        d = row.get("catalyst_date", "")
        if d >= cutoff: continue
        outcome = row.get("parsed_outcome", "").strip()
        if outcome not in ("POSITIVE", "NEGATIVE"): continue
        o = 1 if outcome == "POSITIVE" else 0
        ind = row.get("indication", "").lower()
        matched = False
        for ta_name, ta_re in TA_PATTERNS.items():
            if ta_re.search(ind):
                ta_outcomes[ta_name].append(o)
                matched = True
                break
        if not matched:
            ta_outcomes["other"].append(o)

    rates = {}
    for ta, outs in ta_outcomes.items():
        rates[ta] = sum(outs) / len(outs) if outs else 0.53

    all_train = [r for r in all_events if r.get("catalyst_date","") < cutoff and r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")]
    global_rate = sum(1 for r in all_train if r["parsed_outcome"] == "POSITIVE") / max(len(all_train), 1)
    rates["_global"] = global_rate

    print(f"  TA base rates computed ({len(rates)-1} TAs, global={global_rate:.3f})")
    return rates


# ============================================================================
# FEATURE ENCODER
# ============================================================================
def encode_event(row, odin_index, asset_journey, sponsor_drugs, sponsor_events,
                 sponsor_ta_events, ppm_drug, ta_base_rates, ctgov_cache):
    """Encode a single event into 82 features."""
    raw = {f: 0.0 for f in ALL_FEATURES}

    # Core metadata
    ticker = row.get("ticker", "").upper()
    asset = row.get("asset", "")
    stage = row.get("stage", "").lower().strip()
    indication = row.get("indication", "").lower()
    text = sanitize_text(row.get("raw_catalyst_text", ""))
    current_date = row.get("catalyst_date", "")

    # --- Phase encoding ---
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    if "2/3" in stage: is_p3 = True  # Phase 2/3 counts as pivotal
    is_p2 = "2" in stage and not is_p3
    is_p1 = "1" in stage and not is_p3 and not is_p2

    if is_p3: raw["is_pivotal"] = 1.0
    elif stage in ("phase 2b", "phase2b", "p2b"): raw["is_P2B"] = 1.0
    elif is_p2: raw["is_P2"] = 1.0
    elif is_p1: raw["is_phase1_any"] = 1.0
    is_phase3 = raw["is_pivotal"]

    # --- Therapeutic area ---
    for ta_feat, ta_re in TA_PATTERNS.items():
        if ta_feat in raw and ta_re.search(indication):
            raw[ta_feat] = 1.0
    is_cns = 1.0 if TA_PATTERNS["ta_cns"].search(indication) else 0.0
    is_immuno = 1.0 if TA_PATTERNS["ta_immunology"].search(indication) else 0.0
    is_antibody_flag = 1.0 if MODALITY_PATTERNS["antibody"].search(asset) or MODALITY_PATTERNS["antibody"].search(text) else 0.0

    # --- Competitive landscape ---
    raw["is_competitive"] = 1.0 if any(kw in indication for kw in COMPETITIVE_FULL) else 0.0
    for kw, score in COMPETITIVE_FULL.items():
        if kw in indication:
            raw["competitive_count"] = max(raw["competitive_count"], float(score))

    # --- Modality ---
    if MODALITY_PATTERNS["gene_therapy"].search(asset) or MODALITY_PATTERNS["gene_therapy"].search(text): raw["is_gene_therapy"] = 1.0
    if MODALITY_PATTERNS["adc"].search(asset) or MODALITY_PATTERNS["adc"].search(text): raw["is_adc"] = 1.0
    if MODALITY_PATTERNS["small_molecule"].search(text) or MODALITY_PATTERNS["small_molecule"].search(asset): raw["is_small_molecule"] = 1.0
    if _DESIGN_COMBO.search(text) or _DESIGN_COMBO.search(asset): raw["is_combination"] = 1.0
    if _DESIGN_SURROGATE.search(text): raw["uses_surrogate"] = 1.0

    # --- Trial design estimation (hash-based fallback) ---
    ta_key = get_ta_key(indication)
    # DEPRECATED: Hash-based CT.gov simulation removed (2026-03-27)

    # All Gungnir models must use real CT.gov data or phase-average imputation.

    # Use gungnir_v32_train.py (CHAMPION) instead of this retired script.

    raise RuntimeError("DEPRECATED: This script contains hash-based simulated data. Use gungnir_v32_train.py instead.")

    # Blinding
    if re.search(r"double.?blind|placebo.?control|triple.?blind|quadruple.?blind", text, re.I):
        raw["is_double_blind"] = 1.0
    elif re.search(r"open.?label|single.?arm|unblinded", text, re.I):
        raw["is_double_blind"] = 0.0
    else:
        if is_p3: rate = CTGOV_TA_STATS.get(f"p3_{ta_key}_blind_rate", CTGOV_TA_STATS["p3_generic_blind_rate"])
        elif is_p2: rate = CTGOV_TA_STATS.get(f"p2_{ta_key}_blind_rate", CTGOV_TA_STATS["p2_generic_blind_rate"])
        else: rate = CTGOV_TA_STATS["p1_blind_rate"]
        raw["is_double_blind"] = 1.0 if h < rate else 0.0
    raw["is_open_label"] = 1.0 - raw["is_double_blind"]

    # Enrollment
    if is_p3: median_enroll = CTGOV_TA_STATS.get(f"p3_{ta_key}_enroll", CTGOV_TA_STATS["p3_generic_enroll"])
    elif is_p2: median_enroll = CTGOV_TA_STATS.get(f"p2_{ta_key}_enroll", CTGOV_TA_STATS["p2_generic_enroll"])
    else: median_enroll = CTGOV_TA_STATS["p1_enroll"]
    low = max(int(median_enroll * 0.5), 10)
    high = int(median_enroll * 1.8)
    enroll = low + int(h * (high - low))
    raw["log_enrollment"] = math.log(max(enroll, 1))

    # Endpoint hardness
    if re.search(r"overall.?survival|(?:^|\W)OS(?:\W|$).*(?:endpoint|primary|measure)|mortality|MACE", text, re.I):
        raw["endpoint_hardness"] = 1.0
    elif re.search(r"\bPFS\b|progression.?free|disease.?free|event.?free", text, re.I):
        raw["endpoint_hardness"] = 0.5
    elif re.search(r"\bORR\b|response.?rate|objective.?response", text, re.I):
        raw["endpoint_hardness"] = 0.0
    else:
        raw["endpoint_hardness"] = CTGOV_TA_STATS.get(f"p3_{ta_key}_hard_rate", 0.45) if is_p3 else 0.2

    raw["enroll_vs_ta_median"] = math.log(max(math.exp(raw["log_enrollment"]) / max(median_enroll, 1), 0.01))

    # --- CTGOV REAL DATA OVERRIDE ---
    drug = normalize_drug(asset)
    phase = phase_bucket(stage)
    ctgov_key = f"{drug}|{phase}" if drug and phase else ""
    ctgov_entry = ctgov_cache.get(ctgov_key) if ctgov_key else None
    had_ctgov = ctgov_entry is not None

    # Fill CTGOV features
    raw["ctgov_n_arms"] = 2.0
    raw["ctgov_time_to_readout"] = math.log1p(730)
    raw["ctgov_phase_exact"] = 3.0 if is_p3 else 2.0 if is_p2 else 1.0

    if had_ctgov:
        for f in CTGOV_FEATURES[:10]:  # The 10 base CTGOV features
            if f in ctgov_entry:
                raw[f] = float(ctgov_entry[f])

        real_enroll = ctgov_entry.get("_enrollment", 0)
        raw["ctgov_real_enrollment"] = math.log(max(real_enroll, 1)) if real_enroll > 0 else 0.0

        # Override blinding with real data
        if ctgov_entry.get("ctgov_masking_rigor", 0) >= 2:
            raw["is_double_blind"] = 1.0
            raw["is_open_label"] = 0.0
        elif ctgov_entry.get("ctgov_masking_rigor", 0) == 0:
            raw["is_double_blind"] = 0.0
            raw["is_open_label"] = 1.0

        # Override enrollment with real data
        if raw["ctgov_real_enrollment"] > 0:
            raw["log_enrollment"] = raw["ctgov_real_enrollment"]
            raw["enroll_vs_ta_median"] = math.log(max(math.exp(raw["ctgov_real_enrollment"]) / max(median_enroll, 1), 0.01))

        # Override endpoint with real primary outcome
        if ctgov_entry.get("ctgov_primary_os", 0) > 0:
            raw["endpoint_hardness"] = 1.0
        elif ctgov_entry.get("ctgov_primary_orr", 0) > 0:
            raw["endpoint_hardness"] = 0.0

    # CTGOV interaction terms
    is_onc = 1.0 if TA_PATTERNS["ta_oncology"].search(indication) else 0.0
    raw["ctgov_placebo_x_p3"] = raw["ctgov_placebo"] * is_phase3
    raw["ctgov_masking_x_onc"] = raw["ctgov_masking_rigor"] * is_onc

    # --- ODIN cross-reference ---
    odin = odin_lookup(odin_index, ticker, asset)
    desig_count = 0
    if odin:
        for d_key in ["btd", "orphan", "priority_review", "fast_track", "accelerated_approval"]:
            if odin[d_key]: desig_count += 1
        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"] >= 3 else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"] >= 5 else 0.0
        if odin["surrogate_endpoint"]: raw["uses_surrogate"] = max(raw["uses_surrogate"], 1.0)
    else:
        if re.search(r"breakthrough\s+therap|\bbtd\b", text, re.I):
            raw["odin_btd"] = 1.0
            desig_count += 1
    raw["designation_count"] = float(desig_count)

    # --- PPM (prior positive mention) ---
    a_norm = normalize_drug(asset)
    has_ppm = any(dd < current_date for dd in ppm_drug.get((ticker, a_norm), []))
    if has_ppm: raw["has_ppm"] = 1.0

    # --- Price ---
    price = safe_float(row.get("price_at_catalyst", ""))
    if price and price > 0: raw["log_price"] = math.log(price)
    elif ticker in BIG_PHARMA_TICKERS: raw["log_price"] = math.log(100)
    else: raw["log_price"] = 3.0

    # --- Era ---
    try: year = int(current_date[:4])
    except: year = 2024
    raw["era_post_2024"] = 1.0 if year >= 2025 else 0.0

    # --- NLP features ---
    raw["is_topline"] = 1.0 if re.search(r"top[\s-]?line", text, re.I) else 0.0
    raw["mentions_primary"] = 1.0 if re.search(r"primary\s+endpoint|primary\s+outcome", text, re.I) else 0.0
    raw["endpoint_pfs"] = 1.0 if re.search(r"\bPFS\b|progression[\s-]free", text, re.I) else 0.0

    # --- Interaction terms ---
    raw["phase3_x_cns"] = is_phase3 * is_cns
    raw["phase3_x_immunology"] = is_phase3 * is_immuno
    raw["rare_x_phase3"] = raw["ta_rare"] * is_phase3
    raw["antibody_x_oncology"] = is_antibody_flag * raw["ta_oncology"]
    raw["combo_x_oncology"] = raw["is_combination"] * raw["ta_oncology"]
    raw["blind_x_phase3"] = raw["is_double_blind"] * is_phase3
    raw["enroll_x_phase3"] = raw["log_enrollment"] * is_phase3
    raw["os_x_oncology"] = raw["endpoint_hardness"] * raw["ta_oncology"]
    raw["hard_x_phase3"] = raw["endpoint_hardness"] * is_phase3
    raw["rare_small_enroll"] = raw["ta_rare"] * (1.0 if raw["log_enrollment"] < math.log(100) else 0.0)

    # Sponsor success rate (T-1 compliant — only prior events)
    prior_sponsor = [(d, o) for d, o in sponsor_events.get(ticker, []) if d < current_date]
    raw["sponsor_success_rate"] = sum(o for _, o in prior_sponsor) / len(prior_sponsor) if len(prior_sponsor) >= 2 else 0.5

    # TA base rate
    for ta_name, ta_re in TA_PATTERNS.items():
        if ta_re.search(indication):
            raw["ta_base_rate"] = ta_base_rates.get(ta_name, ta_base_rates.get("_global", 0.53))
            break
    else:
        raw["ta_base_rate"] = ta_base_rates.get("_global", 0.53)

    raw["desig_x_phase3"] = raw["designation_count"] * is_phase3
    raw["sponsor_x_phase3"] = raw["odin_sponsor_exp"] * is_phase3
    raw["is_antibody"] = is_antibody_flag
    raw["blind_x_oncology"] = raw["is_double_blind"] * raw["ta_oncology"]
    raw["ppm_x_phase3"] = raw["has_ppm"] * is_phase3

    # --- Journey features ---
    a_norm = normalize_drug(asset)
    prior = [e for e in asset_journey.get((ticker, a_norm), []) if e["date"] < current_date]

    if prior:
        pp = [e for e in prior if e["outcome"] == "POSITIVE"]
        pn = [e for e in prior if e["outcome"] == "NEGATIVE"]
        pb = [e for e in prior if e["outcome"] in ("POSITIVE", "NEGATIVE")]

        raw["journey_had_prior_positive"] = 1.0 if pp else 0.0
        raw["journey_had_prior_negative"] = 1.0 if pn else 0.0
        raw["journey_n_prior_readouts"] = math.log1p(len(prior))
        raw["journey_n_prior_positive"] = math.log1p(len(pp))
        raw["journey_drug_success_rate"] = sum(1 for e in pb if e["outcome"] == "POSITIVE") / len(pb) if pb else 0.5

        raw["journey_had_p2_positive"] = 1.0 if any(
            e["outcome"] == "POSITIVE" and ("phase 2" in e["stage"] or "2b" in e["stage"] or "2a" in e["stage"])
            for e in prior
        ) else 0.0
        raw["journey_had_p1_positive"] = 1.0 if any(
            e["outcome"] == "POSITIVE" and ("phase 1" in e["stage"] or "1b" in e["stage"] or "1a" in e["stage"] or "1/2" in e["stage"])
            for e in prior
        ) else 0.0

        try:
            days = (datetime.strptime(current_date, "%Y-%m-%d") - datetime.strptime(max(e["date"] for e in prior), "%Y-%m-%d")).days
            raw["journey_time_since_last"] = math.log1p(max(days, 0))
        except:
            raw["journey_time_since_last"] = math.log1p(365)

        if pb:
            raw["journey_last_outcome_positive"] = 1.0 if pb[-1]["outcome"] == "POSITIVE" else 0.0
            streak = 0
            for e in reversed(pb):
                if e["outcome"] == "POSITIVE": streak += 1
                else: break
            raw["journey_positive_streak"] = math.log1p(streak)
            raw["journey_confidence"] = math.log1p(len(pb))
        else:
            raw["journey_last_outcome_positive"] = 0.5
            raw["journey_confidence"] = 0.0

        raw["journey_n_indications"] = math.log1p(len(set(e["indication"] for e in prior if e["indication"])))

        prior_stages = set(e["stage"] for e in prior)
        has_p1_prior = any("phase 1" in s or "1a" in s or "1b" in s or "1/2" in s for s in prior_stages)
        has_p2_prior = any("phase 2" in s or "2a" in s or "2b" in s or "2/3" in s for s in prior_stages)
        if is_p3 and (has_p1_prior or has_p2_prior): raw["journey_phase_advanced"] = 1.0
        elif not is_p3 and is_p2 and has_p1_prior: raw["journey_phase_advanced"] = 1.0

        last_neg = 1.0 if (pb and pb[-1]["outcome"] == "NEGATIVE") else 0.0
        raw["journey_last_neg_x_p3"] = last_neg * is_phase3
        raw["journey_streak_x_p3"] = raw["journey_positive_streak"] * is_phase3
    else:
        raw["journey_drug_success_rate"] = 0.5
        raw["journey_last_outcome_positive"] = 0.5

    # Sponsor journey features
    raw["journey_sponsor_n_drugs"] = math.log1p(len(set(a2 for d2, a2 in sponsor_drugs.get(ticker, []) if d2 < current_date)))
    raw["journey_prior_pos_x_p3"] = raw["journey_had_prior_positive"] * is_phase3

    # Sponsor-TA success rate
    prior_ta = [(dd, o) for dd, o in sponsor_ta_events.get((ticker, ta_key), []) if dd < current_date]
    raw["journey_sponsor_ta_sr"] = sum(o for _, o in prior_ta) / len(prior_ta) if len(prior_ta) >= 2 else 0.5

    # Seasonality
    try:
        month = int(current_date[5:7])
        raw["is_q4"] = 1.0 if month >= 10 else 0.0
    except:
        raw["is_q4"] = 0.0

    return raw, had_ctgov


# ============================================================================
# MAIN PIPELINE
# ============================================================================
def main():
    print("="*70)
    print("  ALLFATHER ENRICHMENT V2")
    print("  Gungnir Dataset T-1 Feature Engineering Pipeline")
    print("="*70)
    print(f"  Target features: {N_FEATURES}")
    print(f"  Feature groups: {len(FEATURES_BASE)} base + {len(JOURNEY_FEATURES)} journey + {len(CTGOV_FEATURES)} CTGOV")

    # Step 1: Load data
    events = load_and_merge_datasets()

    # Step 2: Build ODIN index
    global odin_index
    odin_index = build_odin_index()

    # Step 3: Build journey indices
    asset_journey, sponsor_drugs, sponsor_events, sponsor_ta_events, ppm_drug = build_journey_indices(events)
    ta_base_rates = compute_ta_base_rates(events)

    # Step 4: CTGOV enrichment
    ctgov_cache = batch_ctgov_enrichment(events, CTGOV_CACHE_FILE)

    # Step 5: Encode all events
    print("\n[5/6] Encoding features...")
    encoded_rows = []
    n_ctgov = 0
    for i, row in enumerate(events):
        feats, had_ctgov = encode_event(
            row, odin_index, asset_journey, sponsor_drugs,
            sponsor_events, sponsor_ta_events, ppm_drug,
            ta_base_rates, ctgov_cache
        )
        if had_ctgov: n_ctgov += 1

        # Build output row with metadata + features
        out = {
            "ticker": row.get("ticker", ""),
            "asset": row.get("asset", ""),
            "indication": row.get("indication", ""),
            "stage": row.get("stage", ""),
            "catalyst_date": row.get("catalyst_date", ""),
            "outcome": row.get("parsed_outcome", ""),
            "outcome_binary": 1 if row.get("parsed_outcome", "") == "POSITIVE" else 0,
            "had_ctgov_data": 1 if had_ctgov else 0,
        }
        for f in ALL_FEATURES:
            out[f] = round(feats.get(f, 0.0), 6)

        encoded_rows.append(out)

        if (i + 1) % 500 == 0:
            print(f"    Encoded {i+1}/{len(events)}...")

    print(f"  Encoded: {len(encoded_rows)} events, {N_FEATURES} features each")
    print(f"  CTGOV coverage: {n_ctgov}/{len(encoded_rows)} ({n_ctgov/len(encoded_rows)*100:.1f}%)")

    # Step 6: Write output
    print(f"\n[6/6] Writing enriched dataset...")
    fieldnames = ["ticker", "asset", "indication", "stage", "catalyst_date",
                  "outcome", "outcome_binary", "had_ctgov_data"] + ALL_FEATURES

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in encoded_rows:
            writer.writerow(row)

    print(f"  Written: {OUTPUT_CSV}")
    print(f"  Rows: {len(encoded_rows)}, Columns: {len(fieldnames)}")

    # Summary statistics
    print("\n" + "="*70)
    print("  ENRICHMENT SUMMARY")
    print("="*70)

    import statistics
    outcomes = [r["outcome_binary"] for r in encoded_rows]
    dates = [r["catalyst_date"] for r in encoded_rows]
    ctgov_flags = [r["had_ctgov_data"] for r in encoded_rows]

    print(f"  Events:        {len(encoded_rows)}")
    print(f"  Features:      {N_FEATURES}")
    print(f"  Date range:    {min(dates)} to {max(dates)}")
    print(f"  Positive rate: {sum(outcomes)/len(outcomes):.3f}")
    print(f"  CTGOV coverage:{sum(ctgov_flags)}/{len(ctgov_flags)} ({sum(ctgov_flags)/len(ctgov_flags)*100:.1f}%)")

    # Feature coverage stats
    zero_counts = {f: 0 for f in ALL_FEATURES}
    for row in encoded_rows:
        for f in ALL_FEATURES:
            if row[f] == 0.0: zero_counts[f] += 1

    print(f"\n  Feature sparsity (>90% zero):")
    for f in ALL_FEATURES:
        pct = zero_counts[f] / len(encoded_rows) * 100
        if pct > 90:
            print(f"    {f:40s}  {pct:.1f}% zero")

    print("\n  ENRICHMENT COMPLETE")
    print("="*70)


if __name__ == "__main__":
    # Support --skip-api flag to use existing cache only
    if "--skip-api" in sys.argv:
        # Monkey-patch to skip API calls
        _original_batch = batch_ctgov_enrichment
        def skip_api_batch(events, cache_file):
            print("\n" + "="*70)
            print("  CTGOV BATCH ENRICHMENT (--skip-api: using existing cache only)")
            print("="*70)
            cache = {}
            if os.path.exists(cache_file):
                with open(cache_file) as f:
                    cache = json.load(f)
                n_with = sum(1 for v in cache.values() if v is not None)
                print(f"  Cache loaded: {len(cache)} entries, {n_with} with data")
            else:
                print("  No cache found — all CTGOV features will use defaults")
            return cache
        batch_ctgov_enrichment = skip_api_batch

    main()
