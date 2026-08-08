#!/usr/bin/env python3
"""
GUNGNIR v29.0 — CTGOV ENRICHER
================================
Fetches REAL trial design data from ClinicalTrials.gov API v2 for every
unique drug in the backtest dataset. Caches results to JSON for the
training pipeline.

10 new features (per user spec):
  ctgov_n_arms, ctgov_placebo, ctgov_masking_rigor, ctgov_primary_os,
  ctgov_primary_orr, ctgov_strict_criteria, ctgov_sponsor_scale,
  ctgov_has_withdrawals, ctgov_time_to_readout, ctgov_phase_exact
"""

import csv, re, json, time, math, os
import urllib.request, urllib.parse
from collections import defaultdict
from datetime import datetime

# ============================================================================
# CONFIG
# ============================================================================
API_BASE = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = [
    "NCTId", "BriefTitle", "Phase", "EnrollmentInfo", "DesignInfo",
    "ArmsInterventionsModule", "OutcomesModule", "StatusModule",
    "SponsorCollaboratorsModule", "EligibilityModule",
]
CACHE_FILE = "/sessions/adoring-relaxed-shannon/ctgov_cache.json"
DATA_FILE = "/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_PHASE_BACKTEST_EXTENDED.csv"

BIG_PHARMA_SPONSORS = {
    "pfizer", "merck", "eli lilly", "lilly", "abbvie", "bristol-myers squibb",
    "bristol myers squibb", "bms", "johnson & johnson", "janssen", "astrazeneca",
    "roche", "novartis", "sanofi", "gsk", "glaxosmithkline", "amgen", "gilead",
    "regeneron", "biogen", "vertex", "moderna", "biontech", "takeda", "novo nordisk",
    "teva", "bayer", "boehringer ingelheim", "daiichi sankyo", "astellas",
    "merck sharp & dohme", "merck & co", "f. hoffmann-la roche",
    "hoffmann-la roche", "genentech",
}

# Median eligibility criteria length from a sample of 300+ trials
MEDIAN_ELIG_LENGTH = 3500


# ============================================================================
# DRUG NAME CLEANING
# ============================================================================
def normalize_asset(asset):
    """Extract clean drug name for CTGOV search."""
    if not asset:
        return ""
    asset = str(asset).strip()

    # Try to extract generic name from parentheses: BRAND (generic)
    m = re.search(r'\(([^)]+)\)', asset)
    if m:
        generic = m.group(1).strip()
        # Skip if it's just a study code like CAT-1004 or APPROACH
        if not re.match(r'^[A-Z]{2,6}-?\d+$', generic) and len(generic) > 3:
            # Remove dosage info
            generic = re.sub(r'\d+\s*mg.*', '', generic).strip()
            return generic.lower()

    # Use raw name, strip study names and codes
    name = re.sub(r'\s*-\s*\(.*?\)', '', asset)  # Remove " - (STUDY_NAME)"
    name = re.sub(r'\s*\(.*?\)', '', name)         # Remove (anything)
    name = re.sub(r'\d+\s*mg.*', '', name)         # Remove dosage
    name = name.strip().lower()

    # If name is a known brand, return as-is
    return name


def phase_to_filter(stage):
    """Map dataset stage to CTGOV phase filter."""
    s = str(stage).lower()
    if "phase 3" in s or "phase 2/3" in s or "2/3" in s:
        return "PHASE3"
    if "phase 2" in s:
        return "PHASE2"
    if "phase 1" in s:
        return "PHASE1"
    return None


def phase_to_numeric(phases_list):
    """Map CTGOV phases list to numeric value."""
    if not phases_list:
        return 0
    joined = " ".join(phases_list).upper()
    if "PHASE3" in joined:
        return 3
    if "PHASE2" in joined:
        return 2
    if "PHASE1" in joined:
        return 1
    if "EARLY_PHASE1" in joined:
        return 0.5
    return 0


# ============================================================================
# CTGOV API QUERIER
# ============================================================================
def query_ctgov(drug_name, phase_filter=None, max_results=5):
    """Query CTGOV API v2 for a drug, optionally filtered by phase."""
    params = {
        "query.intr": drug_name,
        "pageSize": str(max_results),
        "fields": ",".join(FIELDS),
    }
    if phase_filter:
        params["filter.advanced"] = f"AREA[Phase]({phase_filter})"

    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Gungnir/29.0"})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        return data.get("studies", [])
    except Exception as e:
        return []


def extract_trial_features(study):
    """Extract the 10 CTGOV features from a single study."""
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

    # 1. ctgov_n_arms: number of arms
    feats["ctgov_n_arms"] = len(arm_groups)

    # 2. ctgov_placebo: has placebo arm (0/1)
    arm_types = [a.get("type", "").upper() for a in arm_groups]
    arm_labels = [a.get("label", "").lower() for a in arm_groups]
    feats["ctgov_placebo"] = 1.0 if (
        "PLACEBO_COMPARATOR" in arm_types or
        any("placebo" in lbl for lbl in arm_labels)
    ) else 0.0

    # 3. ctgov_masking_rigor: NONE=0, SINGLE=1, DOUBLE=2, TRIPLE=3, QUADRUPLE=4
    masking = masking_info.get("masking", "NONE").upper()
    masking_map = {"NONE": 0, "SINGLE": 1, "DOUBLE": 2, "TRIPLE": 3, "QUADRUPLE": 4}
    feats["ctgov_masking_rigor"] = masking_map.get(masking, 0)

    # 4. ctgov_primary_os: primary endpoint mentions OS/survival (0/1)
    primary_text = " ".join(o.get("measure", "") for o in primary_outcomes).lower()
    feats["ctgov_primary_os"] = 1.0 if re.search(
        r"overall\s*survival|\bos\b|mortality|death|survival\s*(?:rate|time|endpoint)",
        primary_text
    ) else 0.0

    # 5. ctgov_primary_orr: primary endpoint mentions ORR/response rate (0/1)
    feats["ctgov_primary_orr"] = 1.0 if re.search(
        r"(?:overall|objective|complete|partial)\s*response\s*rate|\borr\b|\bcrr\b|tumor\s*response",
        primary_text
    ) else 0.0

    # 6. ctgov_strict_criteria: eligibility text length > median (0/1)
    elig_text = elig.get("eligibilityCriteria", "")
    feats["ctgov_strict_criteria"] = 1.0 if len(elig_text) > MEDIAN_ELIG_LENGTH else 0.0

    # 7. ctgov_sponsor_scale: big pharma sponsor (0/1)
    sponsor_name = sponsor.get("leadSponsor", {}).get("name", "").lower()
    feats["ctgov_sponsor_scale"] = 1.0 if any(
        bp in sponsor_name for bp in BIG_PHARMA_SPONSORS
    ) else 0.0

    # 8. ctgov_has_withdrawals: trial has WITHDRAWN or SUSPENDED status (0/1)
    overall_status = status.get("overallStatus", "").upper()
    feats["ctgov_has_withdrawals"] = 1.0 if overall_status in (
        "WITHDRAWN", "SUSPENDED", "TERMINATED"
    ) else 0.0

    # 9. ctgov_time_to_readout: days from start to completion (log-transformed)
    try:
        start = status.get("startDateStruct", {}).get("date", "")
        comp = status.get("completionDateStruct", {}) or status.get("primaryCompletionDateStruct", {})
        comp_date = comp.get("date", "")
        if start and comp_date:
            # Dates can be "YYYY-MM-DD" or "YYYY-MM"
            fmt_s = "%Y-%m-%d" if len(start) > 7 else "%Y-%m"
            fmt_c = "%Y-%m-%d" if len(comp_date) > 7 else "%Y-%m"
            days = (datetime.strptime(comp_date, fmt_c) - datetime.strptime(start, fmt_s)).days
            feats["ctgov_time_to_readout"] = math.log1p(max(days, 0))
        else:
            feats["ctgov_time_to_readout"] = math.log1p(730)  # default 2 years
    except:
        feats["ctgov_time_to_readout"] = math.log1p(730)

    # 10. ctgov_phase_exact: numeric phase
    feats["ctgov_phase_exact"] = phase_to_numeric(design.get("phases", []))

    # Bonus: enrollment count for potential use
    feats["_ctgov_enrollment"] = enrollment_info.get("count", 0)
    feats["_ctgov_nct_id"] = ident.get("nctId", "")
    feats["_ctgov_title"] = ident.get("briefTitle", "")[:100]
    feats["_ctgov_sponsor"] = sponsor.get("leadSponsor", {}).get("name", "")
    feats["_ctgov_status"] = overall_status if 'overall_status' in dir() else status.get("overallStatus", "")

    return feats


def pick_best_trial(studies, drug_name):
    """From multiple studies, pick the most relevant (largest enrollment, completed)."""
    if not studies:
        return None

    scored = []
    for s in studies:
        ps = s.get("protocolSection", {})
        design = ps.get("designModule", {})
        status = ps.get("statusModule", {})
        enroll = design.get("enrollmentInfo", {}).get("count", 0) or 0
        stat = status.get("overallStatus", "").upper()

        # Score: prefer completed, larger enrollment
        score = enroll
        if stat == "COMPLETED":
            score += 10000
        elif stat in ("ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"):
            score += 5000
        elif stat in ("RECRUITING", "NOT_YET_RECRUITING"):
            score += 1000
        # Penalize withdrawn/terminated
        if stat in ("WITHDRAWN", "TERMINATED", "SUSPENDED"):
            score -= 5000

        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


# ============================================================================
# BATCH ENRICHMENT
# ============================================================================
def run_batch_enrichment():
    """Query CTGOV for all unique drugs in the dataset, cache results."""
    print("\n" + "=" * 70)
    print("  GUNGNIR v29.0 CTGOV ENRICHER")
    print("=" * 70)

    # Load existing cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f"  Loaded cache: {len(cache)} entries")

    # Load dataset
    with open(DATA_FILE, encoding="latin-1") as f:
        reader = csv.DictReader(f)
        all_rows = []
        for row in reader:
            try:
                all_rows.append(row)
            except:
                continue

    binary = [r for r in all_rows if r.get("parsed_outcome", "").strip() in ("POSITIVE", "NEGATIVE")]
    print(f"  Binary events: {len(binary)}")

    # Get unique drug/phase pairs
    pairs = set()
    drug_names = {}
    for row in binary:
        asset = row.get("asset", "")
        stage = row.get("stage", "")
        drug = normalize_asset(asset)
        phase = phase_to_filter(stage)
        if drug and phase and len(drug) >= 3:
            pairs.add((drug, phase))
            drug_names[(drug, phase)] = asset  # Keep original for reference

    print(f"  Unique drug/phase pairs: {len(pairs)}")

    # Filter out already cached
    to_query = [(d, p) for d, p in pairs if f"{d}|{p}" not in cache]
    print(f"  Already cached: {len(pairs) - len(to_query)}")
    print(f"  To query: {len(to_query)}")

    if not to_query:
        print("  All drugs already cached!")
        return cache

    # Batch query with rate limiting
    n_total = len(to_query)
    n_found = 0
    n_missed = 0
    save_every = 50

    for idx, (drug, phase) in enumerate(to_query):
        key = f"{drug}|{phase}"

        # Query with phase filter first
        studies = query_ctgov(drug, phase_filter=phase, max_results=5)

        # If nothing found, try without phase filter
        if not studies:
            studies = query_ctgov(drug, phase_filter=None, max_results=5)

        best = pick_best_trial(studies, drug)
        if best:
            feats = extract_trial_features(best)
            cache[key] = feats
            n_found += 1
        else:
            cache[key] = None  # Mark as searched but not found
            n_missed += 1

        # Progress
        if (idx + 1) % 25 == 0 or idx == n_total - 1:
            pct = (idx + 1) / n_total * 100
            print(f"  [{idx+1:4d}/{n_total}] {pct:5.1f}%  found={n_found}  missed={n_missed}  drug='{drug}' phase={phase}")

        # Save periodically
        if (idx + 1) % save_every == 0:
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=1)

        # Rate limit: 100ms between requests (10 req/sec)
        time.sleep(0.1)

    # Final save
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=1)

    print(f"\n  ENRICHMENT COMPLETE:")
    print(f"    Total queried: {n_total}")
    print(f"    Found: {n_found} ({n_found/max(n_total,1)*100:.1f}%)")
    print(f"    Missed: {n_missed} ({n_missed/max(n_total,1)*100:.1f}%)")
    print(f"    Cache size: {len(cache)}")

    # Stats on found entries
    found_entries = [v for v in cache.values() if v is not None]
    if found_entries:
        avg_arms = sum(e.get("ctgov_n_arms", 0) for e in found_entries) / len(found_entries)
        pct_placebo = sum(1 for e in found_entries if e.get("ctgov_placebo", 0) > 0) / len(found_entries) * 100
        pct_blind = sum(1 for e in found_entries if e.get("ctgov_masking_rigor", 0) >= 2) / len(found_entries) * 100
        pct_os = sum(1 for e in found_entries if e.get("ctgov_primary_os", 0) > 0) / len(found_entries) * 100
        pct_orr = sum(1 for e in found_entries if e.get("ctgov_primary_orr", 0) > 0) / len(found_entries) * 100
        pct_bigpharma = sum(1 for e in found_entries if e.get("ctgov_sponsor_scale", 0) > 0) / len(found_entries) * 100
        avg_time = sum(e.get("ctgov_time_to_readout", 0) for e in found_entries) / len(found_entries)

        print(f"\n  FEATURE DISTRIBUTIONS (n={len(found_entries)}):")
        print(f"    Avg arms: {avg_arms:.1f}")
        print(f"    Has placebo: {pct_placebo:.1f}%")
        print(f"    Double+ blind: {pct_blind:.1f}%")
        print(f"    Primary OS: {pct_os:.1f}%")
        print(f"    Primary ORR: {pct_orr:.1f}%")
        print(f"    Big pharma: {pct_bigpharma:.1f}%")
        print(f"    Avg log(time): {avg_time:.2f}")

    return cache


if __name__ == "__main__":
    cache = run_batch_enrichment()
