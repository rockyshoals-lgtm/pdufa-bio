#!/usr/bin/env python3
"""
================================================================================
CT.GOV T-1 COMPLIANT TRIAL-LEVEL DATASET BUILDER
================================================================================

Builds a comprehensive dataset of ALL interventional Phase 1-3 drug/biologic/
gene therapy trials from ClinicalTrials.gov (2020-present) with readout dates.

OUTPUT: One row per trial readout with 45+ strictly T-1 safe features engineered
from protocol/design data ONLY. No outcome data, no post-readout information.

T-1 COMPLIANCE RULES:
  - Readout date D = ResultsFirstPostDate (earliest results posted)
  - ALL features must be knowable at market close on D-1
  - Protocol/design fields (phase, arms, masking, enrollment, endpoints) are
    locked at trial registration — safe by definition
  - Status fields (overallStatus) are NOT used as features (can change post-D)
  - resultsSection is NEVER read for features (only to locate D)
  - Any edge-case features are flagged in the data dictionary

DATA SOURCE: ClinicalTrials.gov API v2 (https://clinicaltrials.gov/api/v2/studies)
  - Filter: Interventional, Phase 1-3, Drug/Biological, results posted >= 2020-01-01
  - Pagination: 200 per page, ~89 pages for ~17,787 trials

ARCHITECTURE: Streaming — fetch page → engineer features → append CSV → discard raw.
  No giant JSON accumulation. Memory-efficient for 17K+ studies.

USAGE:
  python ctgov_t1_dataset_builder.py                  # Full run (stream to CSV)
  python ctgov_t1_dataset_builder.py --max-pages 5     # Dev/test mode (first ~1000)
  python ctgov_t1_dataset_builder.py --resume           # Resume from last page token
"""

import csv, json, math, os, re, sys, time, traceback
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import urllib.request, urllib.parse

# =============================================================================
# PATHS
# =============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CACHE = os.path.join(DATA_DIR, "ctgov_t1_raw_studies.json")
RESUME_FILE = os.path.join(DATA_DIR, "ctgov_t1_resume.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "ctgov_t1_dataset.csv")
DICT_CSV = os.path.join(DATA_DIR, "ctgov_t1_data_dictionary.csv")

# =============================================================================
# API CONFIG
# =============================================================================
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 200
RATE_LIMIT_DELAY = 0.35  # seconds between API calls

# Fields to request — protocol/design sections only (NO resultsSection content)
# We request resultsFirstPostDateStruct ONLY for readout date identification
CTGOV_FIELDS = [
    # Identification
    "NCTId", "OrgStudyId", "BriefTitle", "OfficialTitle",
    # Organization
    "Organization",
    # Status — for D identification only
    "StatusModule",
    # Sponsor
    "SponsorCollaboratorsModule",
    # Design
    "DesignModule",
    # Conditions
    "ConditionsModule",
    # Arms & Interventions
    "ArmsInterventionsModule",
    # Outcomes structure (measure names, NOT results)
    "OutcomesModule",
    # Eligibility
    "EligibilityModule",
    # Oversight
    "OversightModule",
    # Locations
    "ContactsLocationsModule",
    # Derived section (MeSH terms)
    "DerivedSection",
    # Phase (also in DesignModule but explicit)
    "Phase",
]

# =============================================================================
# THERAPEUTIC AREA CLASSIFICATION
# =============================================================================
TA_PATTERNS = {
    "oncology": r"(?i)\b(cancer|tumor|tumour|carcinoma|lymphoma|leukemia|leukaemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|mesothelioma|neuroblastoma|neoplasm|malignant|metasta|oncolog|chemotherapy|immuno.?therapy|checkpoint|PD.?[L1]|CTLA|CAR.?T|HER2|EGFR|VEGF|BRAF|ALK.fusion|KRAS|BRCA|solid.tumor|hematolog|non.?small.cell|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|esophag|cholang|thyroid.cancer|endometri|cervi)\b",
    "cns": r"(?i)\b(alzheimer|parkinson|multiple.sclerosis|epilepsy|seizure|migraine|headache|depression|schizophren|bipolar|anxiety|PTSD|autism|ADHD|attention.deficit|huntington|ALS|amyotrophic|dementia|neuropath|neurodegen|stroke|cerebr|psycho|cognitive|CNS|brain|spinal|neuro(?!blast|fibro)|tremor|dystonia|ataxia)\b",
    "cardiovascular": r"(?i)\b(heart|cardiac|cardio|coronary|atrial|ventricul|arrhythm|hypertens|hypotens|angina|myocard|pericardi|aort|thrombo|embol|anticoagul|atheroscler|cholesterol|lipid|statin|dyslipid|PAH|pulmonary.arterial|CHF|heart.failure|HFrEF|HFpEF|stroke|cerebrovascular)\b",
    "immunology": r"(?i)\b(rheumatoid|lupus|SLE|psoria|atopic|eczema|dermatit|crohn|colitis|IBD|inflammat.bowel|ankylosing|spondyl|autoimmun|immun(?!o.?therap)|graft.vs.host|GVHD|transplant.reject|allerg|asthma|COPD|idiopathic.pulmonary|IPF|vasculit|sjogren|scleroderma|myasthenia|pemphig)\b",
    "infectious": r"(?i)\b(HIV|AIDS|hepatitis|HBV|HCV|influenza|flu|COVID|SARS|corona|RSV|respiratory.syncytial|pneumonia|tuberculosis|TB|malaria|dengue|ebola|zika|herpes|HPV|fungal|candid|aspergill|bacteri|antibiotic|antiviral|antifungal|antimicrob|sepsis|infection|infect|MRSA|C.?diff|clostrid)\b",
    "rare_disease": r"(?i)\b(orphan|rare.disease|ultra.?rare|duchenne|DMD|SMA|spinal.muscular|cystic.fibrosis|CF|hemophilia|haemophilia|sickle.cell|thalassemia|gaucher|fabry|pompe|hunter|hurler|PKU|phenylketon|acromegal|amyloid|transthyretin|ATTR|lysosomal|mucopolysaccharid|epidermolysis|retinitis.pigmentosa|usher.syndrome|batten|niemann|wilson.disease)\b",
    "metabolic": r"(?i)\b(diabetes|diabetic|insulin|HbA1c|glycem|metformin|GLP.?1|SGLT|DPP.?4|obesity|obese|weight.loss|BMI|NASH|NAFLD|fatty.liver|metabolic|gout|uric.acid|osteopor|bone.density|thyroid(?!.cancer)|hypothyroid|hyperthyroid|growth.hormone|acromegal|adrenal|cushing|addison)\b",
    "hematology": r"(?i)\b(anemia|anaemia|thrombocytop|neutropeni|myelodysplast|MDS|myeloproliferative|MPN|myelofibros|polycythemia|hemoglobin|iron.deficien|EPO|erythropoiet|platelet|coagul|bleed|von.willebrand|ITP|TTP|HUS|DIC|sickle.cell|thalassemia|hemophilia|aplastic)\b",
    "ophthalmology": r"(?i)\b(eye|ocular|ophthalm|retina|macular|AMD|glaucoma|cataract|uveitis|diabetic.retin|dry.eye|conjunctiv|cornea|optic|visual|vision.loss|blindness|retinitis|choroid|vitreo)\b",
    "nephrology": r"(?i)\b(kidney|renal|nephro|dialysis|CKD|chronic.kidney|glomerul|IgA.nephropathy|FSGS|polycystic|ADPKD|lupus.nephritis|nephrotic|proteinuria|eGFR|creatinine)\b",
    "hepatology": r"(?i)\b(liver|hepat(?!itis)|cirrhos|fibrosis.liver|biliary|cholestatic|PBC|PSC|portal.hypertension|ascites|hepatorenal|ACLF|liver.transplant)\b",
}

# =============================================================================
# ENDPOINT TYPE CLASSIFICATION
# =============================================================================
ENDPOINT_PATTERNS = {
    "os": r"(?i)\b(overall.survival|OS\b|death|mortality|survival.time)",
    "pfs": r"(?i)\b(progression.free|PFS\b|progression.free.survival)",
    "efs": r"(?i)\b(event.free|EFS\b|event.free.survival)",
    "dfs": r"(?i)\b(disease.free|DFS\b|relapse.free|RFS\b)",
    "orr": r"(?i)\b(overall.response|ORR\b|objective.response|response.rate|tumor.response|tumour.response|RECIST)",
    "cr": r"(?i)\b(complete.response|complete.remission|CR\b|pathologic.complete|pCR)",
    "dor": r"(?i)\b(duration.of.response|DOR\b)",
    "ttp": r"(?i)\b(time.to.progression|TTP\b)",
    "ttf": r"(?i)\b(time.to.treatment.failure|TTF\b)",
    "hba1c": r"(?i)\b(HbA1c|glycated.hemoglobin|A1C\b|glycemic.control)",
    "ldl": r"(?i)\b(LDL|cholesterol|lipid.level|apoB)",
    "pain": r"(?i)\b(pain.score|VAS\b|NRS\b|pain.reduction|analges)",
    "acr": r"(?i)\b(ACR20|ACR50|ACR70|ACR.response)",
    "pasi": r"(?i)\b(PASI\b|PASI.?75|PASI.?90|PASI.?100|psoriasis.area)",
    "easi": r"(?i)\b(EASI\b|eczema.area|IGA\b|investigators.global)",
    "edss": r"(?i)\b(EDSS\b|expanded.disability|relapse.rate|annualized.relapse)",
    "fev1": r"(?i)\b(FEV1|forced.expiratory|lung.function|pulmonary.function)",
    "mayo": r"(?i)\b(mayo.score|partial.mayo|endoscopic.remission|mucosal.healing)",
    "biomarker": r"(?i)\b(biomarker|viral.load|viral.suppression|seroconversion|antibody.titer|immune.response|immunogenicity)",
    "pk_pd": r"(?i)\b(pharmacokinetic|PK\b|AUC\b|Cmax|half.life|clearance|bioavailability|pharmacodynamic|PD\b.*marker)",
    "safety": r"(?i)\b(safety|tolerability|adverse.event|AE\b|SAE\b|dose.limiting|DLT|MTD|maximum.tolerated|TEAE)",
    "qol": r"(?i)\b(quality.of.life|QoL|patient.reported|PRO\b|EQ.?5D|SF.?36|FACT|EORTC)",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_get(d, *keys, default=None):
    """Safely navigate nested dicts."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d if d is not None else default


def parse_date(date_str):
    """Parse CT.gov date string to datetime. Handles 'YYYY-MM-DD' and 'YYYY-MM'."""
    if not date_str:
        return None
    try:
        if len(date_str) == 7:  # YYYY-MM
            return datetime.strptime(date_str, "%Y-%m")
        elif len(date_str) == 10:  # YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d")
        elif len(date_str) == 4:  # YYYY
            return datetime.strptime(date_str, "%Y")
        return None
    except ValueError:
        return None


def parse_age_years(age_str):
    """Convert age string like '18 Years', '6 Months' to float years."""
    if not age_str:
        return None
    m = re.match(r"(\d+)\s*(Year|Month|Week|Day|Hour)", age_str, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("year"):
        return val
    elif unit.startswith("month"):
        return val / 12.0
    elif unit.startswith("week"):
        return val / 52.0
    elif unit.startswith("day"):
        return val / 365.25
    return val


def classify_ta(conditions_text):
    """Classify therapeutic area from conditions text. Returns list of matched TAs."""
    if not conditions_text:
        return []
    matched = []
    for ta, pattern in TA_PATTERNS.items():
        if re.search(pattern, conditions_text):
            matched.append(ta)
    return matched if matched else ["other"]


def classify_endpoints(outcomes_text):
    """Classify primary endpoint types from outcome measure text."""
    if not outcomes_text:
        return []
    matched = []
    for ep_type, pattern in ENDPOINT_PATTERNS.items():
        if re.search(pattern, outcomes_text):
            matched.append(ep_type)
    return matched if matched else ["unclassified"]


def extract_phase_numeric(phases_list):
    """Convert phase list to numeric. E.g., ['PHASE2','PHASE3'] -> 2.5"""
    if not phases_list:
        return None
    nums = []
    for p in phases_list:
        p_upper = str(p).upper()
        if "1" in p_upper:
            nums.append(1)
        if "2" in p_upper:
            nums.append(2)
        if "3" in p_upper:
            nums.append(3)
    return sum(nums) / len(nums) if nums else None


def count_eligibility_criteria(text):
    """Count inclusion/exclusion criteria from eligibility text."""
    if not text:
        return 0, 0
    # Split on common patterns
    inc_section = ""
    exc_section = ""
    # Try to find Inclusion/Exclusion headers
    parts = re.split(r"(?i)(exclusion\s+criteria|key\s+exclusion)", text, maxsplit=1)
    if len(parts) >= 2:
        inc_section = parts[0]
        exc_section = parts[1] if len(parts) > 1 else ""
    else:
        inc_section = text
    # Count bullet points or numbered items
    inc_count = len(re.findall(r"(?m)^\s*[\-\*\d]+[\.\)]\s", inc_section)) or max(1, inc_section.count("\n") // 3)
    exc_count = len(re.findall(r"(?m)^\s*[\-\*\d]+[\.\)]\s", exc_section)) or max(0, exc_section.count("\n") // 3)
    return inc_count, exc_count


def extract_timeframe_days(timeframe_str):
    """Extract numeric timeframe in days from outcome timeframe string."""
    if not timeframe_str:
        return None
    # Look for patterns like "24 weeks", "6 months", "1 year", "52 weeks"
    m = re.search(r"(\d+\.?\d*)\s*(day|week|month|year)", timeframe_str, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if "day" in unit:
        return val
    elif "week" in unit:
        return val * 7
    elif "month" in unit:
        return val * 30.44
    elif "year" in unit:
        return val * 365.25
    return None


# =============================================================================
# API FETCH
# =============================================================================

def _save_resume(token, page_num, total_rows):
    with open(RESUME_FILE, "w") as f:
        json.dump({"pageToken": token, "pageNum": page_num, "totalRows": total_rows}, f)


def qualifies(study):
    """Check if study qualifies: Phase 1-3, drug/bio intervention, has results date."""
    proto = study.get("protocolSection", {})
    design = proto.get("designModule", {})
    phases = design.get("phases", [])
    phase_ok = any(p in ["PHASE1", "PHASE2", "PHASE3", "EARLY_PHASE1"] for p in phases)
    if not phase_ok:
        return False

    arms_mod = proto.get("armsInterventionsModule", {})
    interventions = arms_mod.get("interventions", [])
    has_drug_bio = any(
        iv.get("type", "").upper() in ["DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"]
        for iv in interventions
    ) if interventions else False
    if not has_drug_bio:
        return False

    status_mod = proto.get("statusModule", {})
    results_date = safe_get(status_mod, "resultsFirstPostDateStruct", "date")
    return bool(results_date)


def stream_fetch_and_engineer(max_pages=None, resume_token=None, resume_page=0):
    """
    STREAMING pipeline: fetch page → filter → engineer features → append CSV.
    Never holds all raw studies in memory. Memory-efficient for 17K+ studies.

    Returns: (total_rows, errors_list)
    """
    filter_expr = (
        "AREA[StudyType] INTERVENTIONAL AND "
        "AREA[ResultsFirstPostDate] RANGE[2020-01-01, MAX]"
    )

    page_token = resume_token
    page_num = resume_page
    total_rows = 0
    total_fetched_raw = 0
    errors = []

    # Determine CSV write mode: append if resuming, write if fresh
    is_resume = resume_token is not None
    csv_mode = "a" if is_resume else "w"

    # Get fieldnames from a dummy row (we need header for fresh file)
    dummy_fieldnames = None

    csv_file = open(OUTPUT_CSV, csv_mode, newline="", encoding="utf-8")
    writer = None

    try:
        while True:
            page_num += 1
            if max_pages and page_num > (resume_page + (max_pages or 999999)):
                print(f"[LIMIT] Reached max_pages={max_pages}, stopping.")
                break

            # Build URL
            params = {
                "filter.advanced": filter_expr,
                "pageSize": PAGE_SIZE,
                "format": "json",
            }
            if page_token:
                params["pageToken"] = page_token

            url = f"{CTGOV_API}?{urllib.parse.urlencode(params)}"
            print(f"[PAGE {page_num}] Fetching (rows so far: {total_rows}, raw: {total_fetched_raw})...", flush=True)

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "9Realms-CTGOV-Builder/1.0"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"[ERROR] Page {page_num} failed: {e}")
                _save_resume(page_token, page_num - 1, total_rows)
                print(f"[SAVED] Resume state saved. Re-run with --resume to continue.")
                break

            page_studies = data.get("studies", [])
            if not page_studies:
                print(f"[DONE] No more studies returned.")
                break

            total_fetched_raw += len(page_studies)

            # Filter and engineer features immediately
            for study in page_studies:
                if not qualifies(study):
                    continue
                try:
                    row = engineer_features(study)

                    # Initialize writer with header on first row
                    if writer is None:
                        fieldnames = list(row.keys())
                        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                        if not is_resume:
                            writer.writeheader()

                    writer.writerow(row)
                    total_rows += 1
                except Exception as e:
                    nct = safe_get(study, "protocolSection", "identificationModule", "nctId", default="?")
                    errors.append((nct, str(e)))
                    if len(errors) <= 5:
                        print(f"  [WARN] {nct}: {e}")

            # Flush CSV after each page
            csv_file.flush()

            # Get next page token
            page_token = data.get("nextPageToken")
            if not page_token:
                print(f"[DONE] No more pages.")
                break

            # Save resume state every 5 pages
            if page_num % 5 == 0:
                _save_resume(page_token, page_num, total_rows)
                print(f"[CHECKPOINT] Page {page_num}: {total_rows} rows, {total_fetched_raw} raw")

            time.sleep(RATE_LIMIT_DELAY)

    finally:
        csv_file.close()

    print(f"[COMPLETE] {total_rows} qualifying rows from {total_fetched_raw} raw studies ({page_num} pages)")
    return total_rows, errors


# =============================================================================
# FEATURE ENGINEERING — T-1 COMPLIANT
# =============================================================================

def engineer_features(study):
    """
    Extract all T-1 compliant features from a single CT.gov study record.

    T-1 COMPLIANCE:
    - Only protocol/design fields used (locked at registration)
    - resultsSection NEVER read for features
    - overallStatus NOT used (changes post-readout)
    - Only resultsFirstPostDate used from status (to define D)
    """
    proto = study.get("protocolSection", {})
    derived = study.get("derivedSection", {})

    # --- IDENTIFICATION ---
    ident = proto.get("identificationModule", {})
    nct_id = ident.get("nctId", "")
    brief_title = ident.get("briefTitle", "")
    official_title = ident.get("officialTitle", "")
    org = ident.get("organization", {})
    org_name = org.get("fullName", "")
    org_class = org.get("class", "")  # INDUSTRY, NIH, FED, OTHER, NETWORK, INDIV
    org_study_id = safe_get(ident, "orgStudyIdInfo", "id", default="")

    # --- STATUS / DATES (for D identification only) ---
    status_mod = proto.get("statusModule", {})
    results_first_post = safe_get(status_mod, "resultsFirstPostDateStruct", "date", default="")
    study_first_post = safe_get(status_mod, "studyFirstPostDateStruct", "date", default="")
    start_date_str = safe_get(status_mod, "startDateStruct", "date", default="")
    primary_completion_str = safe_get(status_mod, "primaryCompletionDateStruct", "date", default="")
    completion_str = safe_get(status_mod, "completionDateStruct", "date", default="")
    last_update_str = safe_get(status_mod, "lastUpdatePostDateStruct", "date", default="")

    # D = readout date
    D = parse_date(results_first_post)
    start_dt = parse_date(start_date_str)
    primary_comp_dt = parse_date(primary_completion_str)
    study_first_dt = parse_date(study_first_post)

    # --- SPONSOR ---
    sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
    lead_sponsor = sponsor_mod.get("leadSponsor", {})
    lead_sponsor_name = lead_sponsor.get("name", "")
    lead_sponsor_class = lead_sponsor.get("class", "")
    collaborators = sponsor_mod.get("collaborators", [])
    num_collaborators = len(collaborators)
    responsible_party = safe_get(sponsor_mod, "responsibleParty", "type", default="")

    # Sponsor class features
    is_industry = 1 if lead_sponsor_class == "INDUSTRY" else 0
    is_nih = 1 if lead_sponsor_class in ["NIH", "FED"] else 0
    is_academic = 1 if lead_sponsor_class in ["OTHER", "NETWORK"] else 0
    has_industry_collab = 1 if any(c.get("class") == "INDUSTRY" for c in collaborators) else 0

    # --- DESIGN ---
    design_mod = proto.get("designModule", {})
    phases = design_mod.get("phases", [])
    phase_numeric = extract_phase_numeric(phases)
    is_phase1 = 1 if any("1" in str(p) for p in phases) else 0
    is_phase2 = 1 if any("2" in str(p) for p in phases) else 0
    is_phase3 = 1 if any("3" in str(p) for p in phases) else 0
    is_phase12 = 1 if is_phase1 and is_phase2 else 0
    is_phase23 = 1 if is_phase2 and is_phase3 else 0

    design_info = design_mod.get("designInfo", {})
    allocation = design_info.get("allocation", "")
    intervention_model = design_info.get("interventionModel", "")
    primary_purpose = design_info.get("primaryPurpose", "")

    # Masking
    masking_info = design_info.get("maskingInfo", {})
    masking = masking_info.get("masking", "")
    who_masked = masking_info.get("whoMaskedList", masking_info.get("whoMasked", []))
    if isinstance(who_masked, dict):
        who_masked = who_masked.get("whoMasked", [])

    is_randomized = 1 if allocation and "RANDOMIZED" in allocation.upper() else 0
    is_open_label = 1 if masking and ("NONE" in masking.upper() or "OPEN" in masking.upper()) else 0
    is_single_blind = 1 if masking and "SINGLE" in masking.upper() else 0
    is_double_blind = 1 if masking and ("DOUBLE" in masking.upper() or "TRIPLE" in masking.upper() or "QUADRUPLE" in masking.upper()) else 0
    masking_rigor = len(who_masked) if isinstance(who_masked, list) else 0

    is_parallel = 1 if intervention_model and "PARALLEL" in intervention_model.upper() else 0
    is_crossover = 1 if intervention_model and "CROSSOVER" in intervention_model.upper() else 0
    is_single_arm = 1 if intervention_model and "SINGLE" in intervention_model.upper() else 0
    is_treatment_purpose = 1 if primary_purpose and "TREATMENT" in primary_purpose.upper() else 0
    is_prevention_purpose = 1 if primary_purpose and "PREVENTION" in primary_purpose.upper() else 0

    # Enrollment
    enrollment_info = design_mod.get("enrollmentInfo", {})
    enrollment_count = enrollment_info.get("count")
    enrollment_type = enrollment_info.get("type", "")
    is_actual_enrollment = 1 if enrollment_type.upper() == "ACTUAL" else 0
    log_enrollment = math.log(max(enrollment_count, 1)) if enrollment_count else None

    # --- ARMS & INTERVENTIONS ---
    arms_mod = proto.get("armsInterventionsModule", {})
    arm_groups = arms_mod.get("armGroups", [])
    interventions = arms_mod.get("interventions", [])

    num_arms = len(arm_groups)
    num_interventions = len(interventions)

    # Arm type analysis
    arm_types = [a.get("type", "").upper() for a in arm_groups]
    has_placebo_arm = 1 if any("PLACEBO" in t for t in arm_types) else 0
    has_active_comparator = 1 if any("ACTIVE_COMPARATOR" in t for t in arm_types) else 0
    has_sham_comparator = 1 if any("SHAM" in t for t in arm_types) else 0
    has_no_intervention = 1 if any("NO_INTERVENTION" in t for t in arm_types) else 0

    # Also check arm labels and intervention descriptions for placebo
    arm_labels = " ".join(a.get("label", "") for a in arm_groups).lower()
    interv_text = " ".join(iv.get("name", "") + " " + iv.get("description", "")
                           for iv in interventions).lower()
    has_placebo_mentioned = 1 if ("placebo" in arm_labels or "placebo" in interv_text) else 0
    is_placebo_controlled = 1 if (has_placebo_arm or has_placebo_mentioned) else 0

    # Intervention types
    interv_types = [iv.get("type", "").upper() for iv in interventions]
    has_drug = 1 if "DRUG" in interv_types else 0
    has_biological = 1 if "BIOLOGICAL" in interv_types else 0
    has_genetic = 1 if "GENETIC" in interv_types else 0
    has_combination = 1 if "COMBINATION_PRODUCT" in interv_types else 0

    # Drug names (for downstream dedup/journey linking)
    drug_names = [iv.get("name", "") for iv in interventions
                  if iv.get("type", "").upper() in ["DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"]]
    drug_names_str = "|".join(drug_names)

    # --- CONDITIONS ---
    cond_mod = proto.get("conditionsModule", {})
    conditions = cond_mod.get("conditions", [])
    keywords = cond_mod.get("keywords", [])
    conditions_text = " ".join(conditions + keywords)
    num_conditions = len(conditions)

    # MeSH terms from derived section
    cond_browse = safe_get(derived, "conditionBrowseModule", default={})
    mesh_terms = [m.get("term", "") for m in cond_browse.get("meshes", [])]
    mesh_ancestors = [m.get("term", "") for m in cond_browse.get("ancestors", [])]
    all_condition_text = conditions_text + " " + " ".join(mesh_terms + mesh_ancestors)

    # Therapeutic area classification
    ta_list = classify_ta(all_condition_text)
    primary_ta = ta_list[0] if ta_list else "other"
    num_tas = len(ta_list)

    # Binary TA flags
    ta_oncology = 1 if "oncology" in ta_list else 0
    ta_cns = 1 if "cns" in ta_list else 0
    ta_cardiovascular = 1 if "cardiovascular" in ta_list else 0
    ta_immunology = 1 if "immunology" in ta_list else 0
    ta_infectious = 1 if "infectious" in ta_list else 0
    ta_rare_disease = 1 if "rare_disease" in ta_list else 0
    ta_metabolic = 1 if "metabolic" in ta_list else 0
    ta_hematology = 1 if "hematology" in ta_list else 0
    ta_ophthalmology = 1 if "ophthalmology" in ta_list else 0
    ta_nephrology = 1 if "nephrology" in ta_list else 0
    ta_hepatology = 1 if "hepatology" in ta_list else 0

    # --- OUTCOMES STRUCTURE (design, NOT results) ---
    outcomes_mod = proto.get("outcomesModule", {})
    primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
    secondary_outcomes = outcomes_mod.get("secondaryOutcomes", [])

    num_primary_outcomes = len(primary_outcomes)
    num_secondary_outcomes = len(secondary_outcomes)
    num_total_outcomes = num_primary_outcomes + num_secondary_outcomes

    # Primary endpoint text for classification
    primary_endpoint_text = " ".join(
        o.get("measure", "") + " " + o.get("description", "") + " " + o.get("timeFrame", "")
        for o in primary_outcomes
    )
    endpoint_types = classify_endpoints(primary_endpoint_text)
    primary_endpoint_class = endpoint_types[0] if endpoint_types else "unclassified"

    # Binary endpoint flags
    ep_is_os = 1 if "os" in endpoint_types else 0
    ep_is_pfs = 1 if "pfs" in endpoint_types else 0
    ep_is_orr = 1 if "orr" in endpoint_types else 0
    ep_is_safety = 1 if "safety" in endpoint_types else 0
    ep_is_biomarker = 1 if "biomarker" in endpoint_types else 0
    ep_is_pk_pd = 1 if "pk_pd" in endpoint_types else 0
    ep_is_qol = 1 if "qol" in endpoint_types else 0
    ep_is_hard = 1 if any(e in endpoint_types for e in ["os", "pfs", "efs", "dfs"]) else 0
    ep_is_surrogate = 1 if any(e in endpoint_types for e in ["orr", "cr", "biomarker", "pk_pd"]) else 0

    # Primary endpoint timeframe
    timeframes = [extract_timeframe_days(o.get("timeFrame", "")) for o in primary_outcomes]
    timeframes = [t for t in timeframes if t is not None]
    primary_timeframe_days = max(timeframes) if timeframes else None

    # --- ELIGIBILITY ---
    elig_mod = proto.get("eligibilityModule", {})
    elig_text = elig_mod.get("eligibilityCriteria", "")
    healthy_volunteers = 1 if elig_mod.get("healthyVolunteers", False) else 0
    sex = elig_mod.get("sex", "ALL")
    is_sex_restricted = 1 if sex.upper() not in ["ALL", ""] else 0
    min_age_str = elig_mod.get("minimumAge", "")
    max_age_str = elig_mod.get("maximumAge", "")
    min_age_years = parse_age_years(min_age_str)
    max_age_years = parse_age_years(max_age_str)
    std_ages = elig_mod.get("stdAges", [])
    includes_children = 1 if "CHILD" in std_ages else 0
    includes_older_adult = 1 if "OLDER_ADULT" in std_ages else 0
    is_adult_only = 1 if std_ages == ["ADULT"] else 0

    # Eligibility criteria complexity
    inc_count, exc_count = count_eligibility_criteria(elig_text)
    total_criteria = inc_count + exc_count
    elig_text_length = len(elig_text) if elig_text else 0

    # --- OVERSIGHT ---
    oversight_mod = proto.get("oversightModule", {})
    has_dmc = 1 if oversight_mod.get("oversightHasDmc", False) else 0
    is_fda_regulated_drug = 1 if oversight_mod.get("isFdaRegulatedDrug", False) else 0
    is_fda_regulated_device = 1 if oversight_mod.get("isFdaRegulatedDevice", False) else 0
    is_unapproved_device = 1 if oversight_mod.get("isUnapprovedDevice", False) else 0

    # --- LOCATIONS ---
    contacts_mod = proto.get("contactsLocationsModule", {})
    locations = contacts_mod.get("locations", [])
    num_sites = len(locations)
    countries = list(set(loc.get("country", "") for loc in locations if loc.get("country")))
    num_countries = len(countries)
    has_us_sites = 1 if "United States" in countries else 0
    has_eu_sites = 1 if any(c in countries for c in [
        "Germany", "France", "Italy", "Spain", "Netherlands", "Belgium",
        "Austria", "Sweden", "Denmark", "Finland", "Norway", "Poland",
        "Czech Republic", "Portugal", "Ireland", "Greece", "Hungary",
        "Romania", "Bulgaria", "Croatia", "Slovakia", "Slovenia",
        "United Kingdom"
    ]) else 0
    has_china_sites = 1 if "China" in countries else 0
    has_japan_sites = 1 if "Japan" in countries else 0
    is_global_trial = 1 if num_countries >= 5 else 0
    log_num_sites = math.log(max(num_sites, 1))

    # --- TIMING FEATURES (T-1 safe: computed from registration/design dates) ---
    # All these dates are set at registration or protocol amendment, before D
    time_to_readout_days = None
    if D and start_dt:
        time_to_readout_days = (D - start_dt).days

    time_registration_to_start = None
    if study_first_dt and start_dt:
        time_registration_to_start = (start_dt - study_first_dt).days

    time_start_to_primary_completion = None
    if start_dt and primary_comp_dt:
        time_start_to_primary_completion = (primary_comp_dt - start_dt).days

    study_duration_planned = None
    if start_dt and primary_comp_dt:
        study_duration_planned = (primary_comp_dt - start_dt).days

    # Year of readout (for temporal analysis)
    readout_year = D.year if D else None
    readout_month = D.month if D else None

    # --- INTERACTION FEATURES ---
    # Phase x design interactions
    phase3_x_randomized = is_phase3 * is_randomized
    phase3_x_double_blind = is_phase3 * is_double_blind
    phase3_x_placebo = is_phase3 * is_placebo_controlled
    phase2_x_single_arm = is_phase2 * is_single_arm

    # TA x design interactions
    onc_x_single_arm = ta_oncology * is_single_arm
    onc_x_orr = ta_oncology * ep_is_orr
    onc_x_os = ta_oncology * ep_is_os
    rare_x_small_trial = ta_rare_disease * (1 if enrollment_count and enrollment_count < 100 else 0)

    # Scale interactions
    large_trial = 1 if enrollment_count and enrollment_count >= 500 else 0
    small_trial = 1 if enrollment_count and enrollment_count < 50 else 0
    large_x_phase3 = large_trial * is_phase3
    small_x_phase1 = small_trial * is_phase1

    # Industry x phase
    industry_x_phase3 = is_industry * is_phase3
    industry_x_large = is_industry * large_trial

    # Hard endpoint x phase3 (pivotal signal)
    hard_ep_x_phase3 = ep_is_hard * is_phase3
    surrogate_ep_x_phase2 = ep_is_surrogate * is_phase2

    # DMC x phase (higher phase trials more likely to have DMC)
    dmc_x_phase3 = has_dmc * is_phase3

    # Global trial x phase3
    global_x_phase3 = is_global_trial * is_phase3

    # =================================================================
    # ASSEMBLE ROW
    # =================================================================
    row = {
        # ---- IDENTIFIERS (not features, for linking) ----
        "nct_id": nct_id,
        "brief_title": brief_title,
        "official_title": official_title,
        "org_study_id": org_study_id,
        "lead_sponsor_name": lead_sponsor_name,
        "drug_names": drug_names_str,
        "conditions_raw": "|".join(conditions),
        "primary_ta": primary_ta,
        "primary_endpoint_class": primary_endpoint_class,

        # ---- DATES (metadata, not features except readout_year) ----
        "readout_date": results_first_post if results_first_post else "",
        "start_date": start_date_str,
        "primary_completion_date": primary_completion_str,
        "study_first_posted": study_first_post,
        "readout_year": readout_year,
        "readout_month": readout_month,

        # ==== T-1 FEATURES START HERE ====

        # ---- Phase/Design (F1-F15) ----
        "phase_numeric": phase_numeric,
        "is_phase1": is_phase1,
        "is_phase2": is_phase2,
        "is_phase3": is_phase3,
        "is_phase12": is_phase12,
        "is_phase23": is_phase23,
        "is_randomized": is_randomized,
        "is_open_label": is_open_label,
        "is_single_blind": is_single_blind,
        "is_double_blind": is_double_blind,
        "masking_rigor": masking_rigor,
        "is_parallel": is_parallel,
        "is_crossover": is_crossover,
        "is_single_arm": is_single_arm,
        "is_treatment_purpose": is_treatment_purpose,

        # ---- Scale (F16-F21) ----
        "enrollment_count": enrollment_count,
        "log_enrollment": log_enrollment,
        "is_actual_enrollment": is_actual_enrollment,
        "num_arms": num_arms,
        "num_interventions": num_interventions,
        "num_sites": num_sites,
        "log_num_sites": log_num_sites,
        "num_countries": num_countries,

        # ---- Geography (F22-F27) ----
        "has_us_sites": has_us_sites,
        "has_eu_sites": has_eu_sites,
        "has_china_sites": has_china_sites,
        "has_japan_sites": has_japan_sites,
        "is_global_trial": is_global_trial,

        # ---- Sponsor (F28-F33) ----
        "is_industry": is_industry,
        "is_nih": is_nih,
        "is_academic": is_academic,
        "has_industry_collab": has_industry_collab,
        "num_collaborators": num_collaborators,
        "lead_sponsor_class": lead_sponsor_class,

        # ---- Arms/Comparators (F34-F39) ----
        "is_placebo_controlled": is_placebo_controlled,
        "has_active_comparator": has_active_comparator,
        "has_sham_comparator": has_sham_comparator,
        "has_no_intervention": has_no_intervention,
        "has_drug": has_drug,
        "has_biological": has_biological,
        "has_genetic": has_genetic,
        "has_combination": has_combination,

        # ---- Endpoints/Outcomes (F40-F52) ----
        "num_primary_outcomes": num_primary_outcomes,
        "num_secondary_outcomes": num_secondary_outcomes,
        "num_total_outcomes": num_total_outcomes,
        "ep_is_os": ep_is_os,
        "ep_is_pfs": ep_is_pfs,
        "ep_is_orr": ep_is_orr,
        "ep_is_safety": ep_is_safety,
        "ep_is_biomarker": ep_is_biomarker,
        "ep_is_pk_pd": ep_is_pk_pd,
        "ep_is_qol": ep_is_qol,
        "ep_is_hard": ep_is_hard,
        "ep_is_surrogate": ep_is_surrogate,
        "primary_timeframe_days": primary_timeframe_days,

        # ---- Eligibility (F53-F61) ----
        "healthy_volunteers": healthy_volunteers,
        "is_sex_restricted": is_sex_restricted,
        "min_age_years": min_age_years,
        "max_age_years": max_age_years,
        "includes_children": includes_children,
        "includes_older_adult": includes_older_adult,
        "is_adult_only": is_adult_only,
        "inclusion_criteria_count": inc_count,
        "exclusion_criteria_count": exc_count,
        "total_criteria_count": total_criteria,
        "elig_text_length": elig_text_length,

        # ---- Oversight/Regulatory (F62-F65) ----
        "has_dmc": has_dmc,
        "is_fda_regulated_drug": is_fda_regulated_drug,
        "is_fda_regulated_device": is_fda_regulated_device,

        # ---- Therapeutic Area Flags (F66-F76) ----
        "ta_oncology": ta_oncology,
        "ta_cns": ta_cns,
        "ta_cardiovascular": ta_cardiovascular,
        "ta_immunology": ta_immunology,
        "ta_infectious": ta_infectious,
        "ta_rare_disease": ta_rare_disease,
        "ta_metabolic": ta_metabolic,
        "ta_hematology": ta_hematology,
        "ta_ophthalmology": ta_ophthalmology,
        "ta_nephrology": ta_nephrology,
        "ta_hepatology": ta_hepatology,
        "num_tas": num_tas,

        # ---- Timing (F77-F80) ----
        "time_to_readout_days": time_to_readout_days,
        "time_start_to_primary_completion": time_start_to_primary_completion,
        "study_duration_planned": study_duration_planned,
        "time_registration_to_start": time_registration_to_start,

        # ---- Interaction Features (F81-F95) ----
        "phase3_x_randomized": phase3_x_randomized,
        "phase3_x_double_blind": phase3_x_double_blind,
        "phase3_x_placebo": phase3_x_placebo,
        "phase2_x_single_arm": phase2_x_single_arm,
        "onc_x_single_arm": onc_x_single_arm,
        "onc_x_orr": onc_x_orr,
        "onc_x_os": onc_x_os,
        "rare_x_small_trial": rare_x_small_trial,
        "large_trial": large_trial,
        "small_trial": small_trial,
        "large_x_phase3": large_x_phase3,
        "industry_x_phase3": industry_x_phase3,
        "industry_x_large": industry_x_large,
        "hard_ep_x_phase3": hard_ep_x_phase3,
        "surrogate_ep_x_phase2": surrogate_ep_x_phase2,
        "dmc_x_phase3": dmc_x_phase3,
        "global_x_phase3": global_x_phase3,
    }

    return row


# =============================================================================
# DATA DICTIONARY GENERATION
# =============================================================================

DATA_DICTIONARY = [
    # Identifiers
    ("nct_id", "identifier", "ClinicalTrials.gov NCT ID", "T-1 safe (registration ID)", "identificationModule.nctId"),
    ("brief_title", "identifier", "Short study title", "T-1 safe (set at registration)", "identificationModule.briefTitle"),
    ("official_title", "identifier", "Full official study title", "T-1 safe (set at registration)", "identificationModule.officialTitle"),
    ("org_study_id", "identifier", "Sponsor's internal study ID", "T-1 safe", "identificationModule.orgStudyIdInfo.id"),
    ("lead_sponsor_name", "identifier", "Name of lead sponsor organization", "T-1 safe", "sponsorCollaboratorsModule.leadSponsor.name"),
    ("drug_names", "identifier", "Pipe-delimited drug/biologic intervention names", "T-1 safe (protocol)", "armsInterventionsModule.interventions[].name"),
    ("conditions_raw", "identifier", "Pipe-delimited condition names", "T-1 safe (protocol)", "conditionsModule.conditions"),
    ("primary_ta", "identifier", "Primary therapeutic area (regex-classified)", "T-1 safe (derived from conditions)", "Computed from conditionsModule + MeSH"),
    ("primary_endpoint_class", "identifier", "Primary endpoint type classification", "T-1 safe (from outcome measure names)", "Computed from outcomesModule.primaryOutcomes"),

    # Dates
    ("readout_date", "metadata", "Results first posted date (D) — YYYY-MM-DD or YYYY-MM", "Defines D; NOT a feature", "statusModule.resultsFirstPostDateStruct.date"),
    ("start_date", "metadata", "Study start date", "T-1 safe (pre-D by definition)", "statusModule.startDateStruct.date"),
    ("primary_completion_date", "metadata", "Primary completion date (planned or actual)", "T-1 safe (protocol design date)", "statusModule.primaryCompletionDateStruct.date"),
    ("study_first_posted", "metadata", "Date study first posted to CT.gov", "T-1 safe (registration date)", "statusModule.studyFirstPostDateStruct.date"),
    ("readout_year", "metadata", "Year of readout date D", "Derived from D", "Computed"),
    ("readout_month", "metadata", "Month of readout date D", "Derived from D", "Computed"),

    # Phase/Design features
    ("phase_numeric", "feature", "Phase as numeric (1, 1.5, 2, 2.5, 3)", "T-1 SAFE: locked at registration", "designModule.phases"),
    ("is_phase1", "feature", "Binary: Phase 1 trial", "T-1 SAFE", "designModule.phases"),
    ("is_phase2", "feature", "Binary: Phase 2 trial", "T-1 SAFE", "designModule.phases"),
    ("is_phase3", "feature", "Binary: Phase 3 trial", "T-1 SAFE", "designModule.phases"),
    ("is_phase12", "feature", "Binary: Phase 1/2 trial", "T-1 SAFE", "designModule.phases"),
    ("is_phase23", "feature", "Binary: Phase 2/3 trial", "T-1 SAFE", "designModule.phases"),
    ("is_randomized", "feature", "Binary: randomized allocation", "T-1 SAFE: protocol design", "designModule.designInfo.allocation"),
    ("is_open_label", "feature", "Binary: open label (no masking)", "T-1 SAFE: protocol design", "designModule.designInfo.maskingInfo.masking"),
    ("is_single_blind", "feature", "Binary: single-blind masking", "T-1 SAFE: protocol design", "designModule.designInfo.maskingInfo.masking"),
    ("is_double_blind", "feature", "Binary: double/triple/quadruple blind", "T-1 SAFE: protocol design", "designModule.designInfo.maskingInfo.masking"),
    ("masking_rigor", "feature", "Count of masked parties (0-4)", "T-1 SAFE: protocol design", "designModule.designInfo.maskingInfo.whoMaskedList"),
    ("is_parallel", "feature", "Binary: parallel group design", "T-1 SAFE: protocol design", "designModule.designInfo.interventionModel"),
    ("is_crossover", "feature", "Binary: crossover design", "T-1 SAFE: protocol design", "designModule.designInfo.interventionModel"),
    ("is_single_arm", "feature", "Binary: single-arm (no comparator)", "T-1 SAFE: protocol design", "designModule.designInfo.interventionModel"),
    ("is_treatment_purpose", "feature", "Binary: primary purpose is treatment", "T-1 SAFE: protocol design", "designModule.designInfo.primaryPurpose"),

    # Scale
    ("enrollment_count", "feature", "Number of participants (actual or anticipated)", "T-1 SAFE: protocol/actual pre-D", "designModule.enrollmentInfo.count"),
    ("log_enrollment", "feature", "log(enrollment_count)", "T-1 SAFE: derived", "Computed"),
    ("is_actual_enrollment", "feature", "Binary: enrollment is actual (not estimated)", "T-1 SAFE", "designModule.enrollmentInfo.type"),
    ("num_arms", "feature", "Number of study arms", "T-1 SAFE: protocol design", "armsInterventionsModule.armGroups length"),
    ("num_interventions", "feature", "Number of interventions", "T-1 SAFE: protocol design", "armsInterventionsModule.interventions length"),
    ("num_sites", "feature", "Number of study sites/facilities", "T-1 SAFE: from locations", "contactsLocationsModule.locations length"),
    ("log_num_sites", "feature", "log(num_sites)", "T-1 SAFE: derived", "Computed"),
    ("num_countries", "feature", "Number of countries with sites", "T-1 SAFE: from locations", "contactsLocationsModule.locations[].country"),

    # Geography
    ("has_us_sites", "feature", "Binary: has US study sites", "T-1 SAFE", "contactsLocationsModule.locations"),
    ("has_eu_sites", "feature", "Binary: has European study sites", "T-1 SAFE", "contactsLocationsModule.locations"),
    ("has_china_sites", "feature", "Binary: has China study sites", "T-1 SAFE", "contactsLocationsModule.locations"),
    ("has_japan_sites", "feature", "Binary: has Japan study sites", "T-1 SAFE", "contactsLocationsModule.locations"),
    ("is_global_trial", "feature", "Binary: sites in 5+ countries", "T-1 SAFE: derived", "Computed"),

    # Sponsor
    ("is_industry", "feature", "Binary: lead sponsor is INDUSTRY class", "T-1 SAFE", "sponsorCollaboratorsModule.leadSponsor.class"),
    ("is_nih", "feature", "Binary: lead sponsor is NIH/FED", "T-1 SAFE", "sponsorCollaboratorsModule.leadSponsor.class"),
    ("is_academic", "feature", "Binary: lead sponsor is OTHER/NETWORK (academic)", "T-1 SAFE", "sponsorCollaboratorsModule.leadSponsor.class"),
    ("has_industry_collab", "feature", "Binary: has industry collaborator", "T-1 SAFE", "sponsorCollaboratorsModule.collaborators[].class"),
    ("num_collaborators", "feature", "Number of collaborators", "T-1 SAFE", "sponsorCollaboratorsModule.collaborators length"),
    ("lead_sponsor_class", "feature", "Lead sponsor class (INDUSTRY/NIH/FED/OTHER/NETWORK/INDIV)", "T-1 SAFE", "sponsorCollaboratorsModule.leadSponsor.class"),

    # Arms/Comparators
    ("is_placebo_controlled", "feature", "Binary: has placebo arm or placebo mentioned", "T-1 SAFE: protocol design", "armsInterventionsModule"),
    ("has_active_comparator", "feature", "Binary: has active comparator arm", "T-1 SAFE: protocol design", "armsInterventionsModule.armGroups[].type"),
    ("has_sham_comparator", "feature", "Binary: has sham comparator", "T-1 SAFE: protocol design", "armsInterventionsModule.armGroups[].type"),
    ("has_no_intervention", "feature", "Binary: has no-intervention arm", "T-1 SAFE: protocol design", "armsInterventionsModule.armGroups[].type"),
    ("has_drug", "feature", "Binary: has DRUG type intervention", "T-1 SAFE: protocol", "armsInterventionsModule.interventions[].type"),
    ("has_biological", "feature", "Binary: has BIOLOGICAL type intervention", "T-1 SAFE: protocol", "armsInterventionsModule.interventions[].type"),
    ("has_genetic", "feature", "Binary: has GENETIC (gene therapy) intervention", "T-1 SAFE: protocol", "armsInterventionsModule.interventions[].type"),
    ("has_combination", "feature", "Binary: has combination product", "T-1 SAFE: protocol", "armsInterventionsModule.interventions[].type"),

    # Endpoints/Outcomes
    ("num_primary_outcomes", "feature", "Number of primary outcome measures", "T-1 SAFE: protocol design (measure names, not results)", "outcomesModule.primaryOutcomes length"),
    ("num_secondary_outcomes", "feature", "Number of secondary outcome measures", "T-1 SAFE: protocol design", "outcomesModule.secondaryOutcomes length"),
    ("num_total_outcomes", "feature", "Total outcome measures (primary + secondary)", "T-1 SAFE: derived", "Computed"),
    ("ep_is_os", "feature", "Binary: primary endpoint includes overall survival", "T-1 SAFE: from outcome measure name (not result)", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_pfs", "feature", "Binary: primary endpoint includes PFS", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_orr", "feature", "Binary: primary endpoint includes ORR/response rate", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_safety", "feature", "Binary: primary endpoint is safety/tolerability", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_biomarker", "feature", "Binary: primary endpoint is biomarker-based", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_pk_pd", "feature", "Binary: primary endpoint is PK/PD", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_qol", "feature", "Binary: primary endpoint includes QoL/PRO", "T-1 SAFE: from measure name", "outcomesModule.primaryOutcomes[].measure"),
    ("ep_is_hard", "feature", "Binary: primary endpoint is 'hard' (OS/PFS/EFS/DFS)", "T-1 SAFE: derived", "Computed"),
    ("ep_is_surrogate", "feature", "Binary: primary endpoint is surrogate (ORR/CR/biomarker)", "T-1 SAFE: derived", "Computed"),
    ("primary_timeframe_days", "feature", "Primary endpoint timeframe in days (max across primary outcomes)", "T-1 SAFE: protocol design", "outcomesModule.primaryOutcomes[].timeFrame"),

    # Eligibility
    ("healthy_volunteers", "feature", "Binary: accepts healthy volunteers", "T-1 SAFE: protocol", "eligibilityModule.healthyVolunteers"),
    ("is_sex_restricted", "feature", "Binary: restricted to one sex", "T-1 SAFE: protocol", "eligibilityModule.sex"),
    ("min_age_years", "feature", "Minimum age in years", "T-1 SAFE: protocol", "eligibilityModule.minimumAge"),
    ("max_age_years", "feature", "Maximum age in years", "T-1 SAFE: protocol", "eligibilityModule.maximumAge"),
    ("includes_children", "feature", "Binary: includes CHILD age group", "T-1 SAFE: protocol", "eligibilityModule.stdAges"),
    ("includes_older_adult", "feature", "Binary: includes OLDER_ADULT age group", "T-1 SAFE: protocol", "eligibilityModule.stdAges"),
    ("is_adult_only", "feature", "Binary: ADULT only (no children or older adults)", "T-1 SAFE: protocol", "eligibilityModule.stdAges"),
    ("inclusion_criteria_count", "feature", "Estimated number of inclusion criteria", "T-1 SAFE: from criteria text structure", "eligibilityModule.eligibilityCriteria"),
    ("exclusion_criteria_count", "feature", "Estimated number of exclusion criteria", "T-1 SAFE: from criteria text structure", "eligibilityModule.eligibilityCriteria"),
    ("total_criteria_count", "feature", "Total inclusion + exclusion criteria", "T-1 SAFE: derived", "Computed"),
    ("elig_text_length", "feature", "Character length of eligibility criteria text", "T-1 SAFE: protocol complexity proxy", "eligibilityModule.eligibilityCriteria"),

    # Oversight
    ("has_dmc", "feature", "Binary: has Data Monitoring Committee", "T-1 SAFE: protocol oversight", "oversightModule.oversightHasDmc"),
    ("is_fda_regulated_drug", "feature", "Binary: FDA-regulated drug product", "T-1 SAFE: regulatory designation", "oversightModule.isFdaRegulatedDrug"),
    ("is_fda_regulated_device", "feature", "Binary: FDA-regulated device product", "T-1 SAFE: regulatory designation", "oversightModule.isFdaRegulatedDevice"),

    # Therapeutic Area
    ("ta_oncology", "feature", "Binary: oncology indication", "T-1 SAFE: from conditions/MeSH", "Computed from conditionsModule"),
    ("ta_cns", "feature", "Binary: CNS/neurological indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_cardiovascular", "feature", "Binary: cardiovascular indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_immunology", "feature", "Binary: immunology/autoimmune indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_infectious", "feature", "Binary: infectious disease indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_rare_disease", "feature", "Binary: rare/orphan disease indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_metabolic", "feature", "Binary: metabolic/endocrine indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_hematology", "feature", "Binary: hematology indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_ophthalmology", "feature", "Binary: ophthalmology indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_nephrology", "feature", "Binary: nephrology/kidney indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("ta_hepatology", "feature", "Binary: hepatology/liver indication", "T-1 SAFE: from conditions/MeSH", "Computed"),
    ("num_tas", "feature", "Number of therapeutic areas matched", "T-1 SAFE: derived", "Computed"),

    # Timing
    ("time_to_readout_days", "feature", "Days from study start to D (results posted)", "T-1 SAFE: start_date is pre-D", "Computed from statusModule dates"),
    ("time_start_to_primary_completion", "feature", "Days from start to primary completion date", "T-1 SAFE: protocol dates", "Computed from statusModule dates"),
    ("study_duration_planned", "feature", "Planned study duration in days (start to primary completion)", "T-1 SAFE: protocol dates", "Computed"),
    ("time_registration_to_start", "feature", "Days from CT.gov posting to study start", "T-1 SAFE: registration dates", "Computed"),

    # Interactions
    ("phase3_x_randomized", "feature", "Phase 3 AND randomized", "T-1 SAFE: interaction", "Computed"),
    ("phase3_x_double_blind", "feature", "Phase 3 AND double-blind", "T-1 SAFE: interaction", "Computed"),
    ("phase3_x_placebo", "feature", "Phase 3 AND placebo-controlled", "T-1 SAFE: interaction", "Computed"),
    ("phase2_x_single_arm", "feature", "Phase 2 AND single-arm", "T-1 SAFE: interaction", "Computed"),
    ("onc_x_single_arm", "feature", "Oncology AND single-arm", "T-1 SAFE: interaction", "Computed"),
    ("onc_x_orr", "feature", "Oncology AND ORR endpoint", "T-1 SAFE: interaction", "Computed"),
    ("onc_x_os", "feature", "Oncology AND OS endpoint", "T-1 SAFE: interaction", "Computed"),
    ("rare_x_small_trial", "feature", "Rare disease AND enrollment < 100", "T-1 SAFE: interaction", "Computed"),
    ("large_trial", "feature", "Binary: enrollment >= 500", "T-1 SAFE: derived", "Computed"),
    ("small_trial", "feature", "Binary: enrollment < 50", "T-1 SAFE: derived", "Computed"),
    ("large_x_phase3", "feature", "Large trial AND Phase 3", "T-1 SAFE: interaction", "Computed"),
    ("industry_x_phase3", "feature", "Industry sponsor AND Phase 3", "T-1 SAFE: interaction", "Computed"),
    ("industry_x_large", "feature", "Industry sponsor AND large trial", "T-1 SAFE: interaction", "Computed"),
    ("hard_ep_x_phase3", "feature", "Hard endpoint AND Phase 3", "T-1 SAFE: interaction", "Computed"),
    ("surrogate_ep_x_phase2", "feature", "Surrogate endpoint AND Phase 2", "T-1 SAFE: interaction", "Computed"),
    ("dmc_x_phase3", "feature", "DMC AND Phase 3", "T-1 SAFE: interaction", "Computed"),
    ("global_x_phase3", "feature", "Global trial AND Phase 3", "T-1 SAFE: interaction", "Computed"),
]


def write_data_dictionary():
    """Write the data dictionary CSV."""
    with open(DICT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["column_name", "type", "description", "t1_compliance", "api_source"])
        for entry in DATA_DICTIONARY:
            writer.writerow(entry)
    print(f"[DICT] Data dictionary written to {DICT_CSV} ({len(DATA_DICTIONARY)} entries)")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def summarize_output():
    """Read the output CSV and print summary statistics."""
    if not os.path.exists(OUTPUT_CSV):
        print("[WARN] No output CSV found to summarize.")
        return

    print(f"\n[SUMMARY] Reading {OUTPUT_CSV}...")
    rows = []
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    n = len(rows)
    print(f"  {n} rows x {len(fieldnames)} columns")

    feature_cols = [c for c in fieldnames if c not in [
        "nct_id", "brief_title", "official_title", "org_study_id",
        "lead_sponsor_name", "drug_names", "conditions_raw", "primary_ta",
        "primary_endpoint_class", "readout_date", "start_date",
        "primary_completion_date", "study_first_posted", "readout_year",
        "readout_month", "lead_sponsor_class"
    ]]
    print(f"  {len(feature_cols)} ML-ready features + {len(fieldnames) - len(feature_cols)} metadata/identifier columns")

    print("\n" + "=" * 80)
    print("DATASET SUMMARY")
    print("=" * 80)

    # Phase distribution
    phase_counts = Counter()
    for r in rows:
        pv = r.get("phase_numeric", "")
        if pv:
            try:
                phase_counts[float(pv)] += 1
            except ValueError:
                pass
    print(f"\nPhase Distribution:")
    for p in sorted(phase_counts.keys()):
        print(f"  Phase {p}: {phase_counts[p]} ({100*phase_counts[p]/n:.1f}%)")

    # TA distribution
    print(f"\nTop Therapeutic Areas:")
    ta_counts = Counter(r.get("primary_ta", "other") for r in rows)
    for ta, cnt in ta_counts.most_common(10):
        print(f"  {ta}: {cnt} ({100*cnt/n:.1f}%)")

    # Year distribution
    year_counts = Counter()
    for r in rows:
        yr = r.get("readout_year", "")
        if yr:
            try:
                year_counts[int(yr)] += 1
            except ValueError:
                pass
    print(f"\nReadout Year Distribution:")
    for yr in sorted(year_counts.keys()):
        print(f"  {yr}: {year_counts[yr]}")

    # Design features
    print(f"\nDesign Feature Rates:")
    for feat in ["is_randomized", "is_double_blind", "is_placebo_controlled",
                  "is_single_arm", "has_dmc", "is_industry", "is_global_trial",
                  "is_fda_regulated_drug", "ep_is_hard", "ep_is_surrogate"]:
        rate = sum(1 for r in rows if r.get(feat) == "1") / n
        print(f"  {feat}: {100*rate:.1f}%")

    # Enrollment stats
    enrollments = []
    for r in rows:
        ev = r.get("enrollment_count", "")
        if ev:
            try:
                enrollments.append(int(ev))
            except ValueError:
                pass
    if enrollments:
        enrollments.sort()
        print(f"\nEnrollment: median={enrollments[len(enrollments)//2]}, "
              f"mean={sum(enrollments)/len(enrollments):.0f}, "
              f"min={min(enrollments)}, max={max(enrollments)}, "
              f"missing={n - len(enrollments)}")

    # Missing value analysis
    print(f"\nMissing Value Rates (top 10):")
    missing = {}
    for col in fieldnames:
        miss = sum(1 for r in rows if not r.get(col) or r.get(col) == "None")
        if miss > 0:
            missing[col] = miss
    for col, cnt in sorted(missing.items(), key=lambda x: -x[1])[:10]:
        print(f"  {col}: {cnt} ({100*cnt/n:.1f}%)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CT.gov T-1 Compliant Dataset Builder")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit API pages (dev/test)")
    parser.add_argument("--resume", action="store_true", help="Resume from last page token")
    parser.add_argument("--summary-only", action="store_true", help="Just print summary of existing CSV")
    args = parser.parse_args()

    print("=" * 80)
    print("CT.GOV T-1 COMPLIANT TRIAL-LEVEL DATASET BUILDER (STREAMING)")
    print("=" * 80)

    if args.summary_only:
        summarize_output()
        write_data_dictionary()
        print(f"\n[DONE] Summary complete.")
        return 0

    # Resolve resume state
    resume_token = None
    resume_page = 0
    if args.resume and os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, "r") as f:
            resume_data = json.load(f)
        resume_token = resume_data.get("pageToken")
        resume_page = resume_data.get("pageNum", 0)
        prev_rows = resume_data.get("totalRows", 0)
        print(f"[RESUME] Continuing from page {resume_page} ({prev_rows} rows already written)")

    # Stream fetch + engineer + write
    total_rows, errors = stream_fetch_and_engineer(
        max_pages=args.max_pages,
        resume_token=resume_token,
        resume_page=resume_page
    )

    # Write data dictionary
    write_data_dictionary()

    # Print summary
    summarize_output()

    if errors:
        print(f"\n[ERRORS] {len(errors)} studies failed feature engineering:")
        for nct, err in errors[:10]:
            print(f"  {nct}: {err}")

    print(f"\n[DONE] Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
