#!/usr/bin/env python3
"""
CT.gov Enrichment Pipeline for Gungnir Readout Analysis Dataset
================================================================
Processes MCP API results and builds the enriched CSV.

This script:
1. Loads the 1,752-event dataset
2. Loads existing NCT ID matches (1,004 pre-matched)
3. Accepts MCP API results (saved as JSON) and extracts required fields
4. Builds the final enriched CSV with all columns + provenance flags

Required output columns per David's spec:
- nct_id, ctgov_startdate, ctgov_completiondate, ctgov_status,
  ctgov_enrollment, ctgov_masking, ctgov_primary_endpoint,
  ctgov_has_placebo_arm, ctgov_narms, ctgov_sponsor_exact,
  retrieval_timestamp, provenance_verified, t1_compliant, mismatch_note
"""

import csv, json, os, re
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
LOOKUP_JSON = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
ENRICHMENT_CACHE = os.path.join(DATA_DIR, "ctgov_enrichment_cache.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_ctgov_enriched.csv")

# New columns to add
NEW_COLUMNS = [
    "nct_id", "ctgov_startdate", "ctgov_completiondate", "ctgov_status",
    "ctgov_enrollment", "ctgov_masking", "ctgov_primary_endpoint",
    "ctgov_has_placebo_arm", "ctgov_narms", "ctgov_sponsor_exact",
    "retrieval_timestamp", "provenance_verified", "t1_compliant", "mismatch_note"
]


def extract_fields_from_study(study_data, catalyst_date=None):
    """Extract required fields from a CT.gov study JSON response.

    Args:
        study_data: The protocolSection of a CT.gov study response
        catalyst_date: YYYY-MM-DD string for T-1 compliance check

    Returns:
        dict with all NEW_COLUMNS fields populated
    """
    result = {col: "" for col in NEW_COLUMNS}

    if not study_data or not isinstance(study_data, dict):
        result["mismatch_note"] = "no_data"
        return result

    # Navigate the nested structure
    proto = study_data.get("protocolSection", study_data)

    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    sponsor = proto.get("sponsorCollaboratorsModule", {})
    design = proto.get("designModule", {})
    outcomes = proto.get("outcomesModule", {})
    arms_mod = proto.get("armsInterventionsModule", {})

    # NCT ID
    result["nct_id"] = ident.get("nctId", "")

    # Start date
    start_struct = status.get("startDateStruct", {})
    result["ctgov_startdate"] = start_struct.get("date", "")

    # Primary completion date
    completion_struct = status.get("primaryCompletionDateStruct", {})
    result["ctgov_completiondate"] = completion_struct.get("date", "")

    # Overall status
    result["ctgov_status"] = status.get("overallStatus", "")

    # Enrollment
    enroll_info = design.get("enrollmentInfo", {})
    result["ctgov_enrollment"] = enroll_info.get("count", "")

    # Masking
    design_info = design.get("designInfo", {})
    masking_info = design_info.get("maskingInfo", {})
    result["ctgov_masking"] = masking_info.get("masking", "NONE")

    # Primary endpoint
    primary_outcomes = outcomes.get("primaryOutcomes", [])
    if primary_outcomes:
        ep_text = primary_outcomes[0].get("measure", "")
        # Truncate to 500 chars for CSV sanity
        result["ctgov_primary_endpoint"] = ep_text[:500] if ep_text else ""

    # Placebo arm detection
    arm_groups = arms_mod.get("armGroups", [])
    has_placebo = 0
    for arm in arm_groups:
        arm_type = arm.get("type", "").upper()
        arm_label = arm.get("label", "").lower()
        arm_desc = arm.get("description", "").lower()
        interventions = " ".join(arm.get("interventionNames", [])).lower()
        if "placebo" in arm_type or "placebo" in arm_label or "placebo" in interventions:
            has_placebo = 1
            break
    result["ctgov_has_placebo_arm"] = has_placebo

    # Number of arms
    result["ctgov_narms"] = len(arm_groups) if arm_groups else ""

    # Exact sponsor
    lead_sponsor = sponsor.get("leadSponsor", {})
    result["ctgov_sponsor_exact"] = lead_sponsor.get("name", "")

    # Retrieval timestamp
    result["retrieval_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # T-1 compliance check
    if catalyst_date:
        first_posted = status.get("studyFirstPostDateStruct", {}).get("date", "")
        if first_posted:
            try:
                posted_dt = datetime.strptime(first_posted[:10], "%Y-%m-%d")
                catalyst_dt = datetime.strptime(catalyst_date[:10], "%Y-%m-%d")
                days_before = (catalyst_dt - posted_dt).days
                result["t1_compliant"] = 1 if days_before >= 30 else 0
                if days_before < 30:
                    result["mismatch_note"] = f"posted_only_{days_before}d_before_catalyst"
            except ValueError:
                result["t1_compliant"] = ""
                result["mismatch_note"] = "date_parse_error"
        else:
            result["t1_compliant"] = ""
            result["mismatch_note"] = "no_first_posted_date"

    # Provenance verified (set to 1 if we got an NCT ID back)
    result["provenance_verified"] = 1 if result["nct_id"] else 0

    return result


def build_search_query(row):
    """Build a CT.gov search query from a dataset row."""
    drug = row.get("drug", "").strip()
    indication = row.get("indication", "").strip()
    ticker = row.get("ticker", "").strip()
    name = row.get("name", "").strip()

    # Extract drug name (before parenthetical study name)
    drug_clean = re.sub(r'\s*-\s*\(.*?\)\s*', '', drug).strip()
    # Also extract study acronym if present
    study_match = re.search(r'\(([A-Z0-9-]+)\)', drug)
    acronym = study_match.group(1) if study_match else ""

    # Build query parts
    parts = []
    if drug_clean:
        # Use first drug name if combination
        first_drug = drug_clean.split(" plus ")[0].split(" and ")[0].split("/")[0].strip()
        parts.append(first_drug)
    if indication:
        # Simplify indication
        ind_clean = re.sub(r'\(.*?\)', '', indication).strip()
        ind_short = ind_clean.split(",")[0].strip()[:60]
        parts.append(ind_short)

    query = " ".join(parts)
    return query, drug_clean, acronym


def load_enrichment_cache():
    """Load incrementally saved enrichment results."""
    if os.path.exists(ENRICHMENT_CACHE):
        with open(ENRICHMENT_CACHE) as f:
            return json.load(f)
    return {}


def save_enrichment_cache(cache):
    """Save enrichment results incrementally."""
    with open(ENRICHMENT_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def save_enriched_csv(rows, enrichments):
    """Save the final enriched CSV."""
    # Get original columns from first row
    orig_columns = list(rows[0].keys())
    all_columns = orig_columns + NEW_COLUMNS

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns, extrasaction="ignore")
        writer.writeheader()

        for i, row in enumerate(rows):
            enriched = enrichments.get(str(i), {col: "" for col in NEW_COLUMNS})
            combined = {**row, **enriched}
            writer.writerow(combined)

    return OUTPUT_CSV


def generate_summary(rows, enrichments):
    """Generate summary statistics."""
    total = len(rows)
    verified = sum(1 for e in enrichments.values() if e.get("provenance_verified") == 1)
    t1_compliant = sum(1 for e in enrichments.values() if e.get("t1_compliant") == 1)
    t1_unknown = sum(1 for e in enrichments.values() if e.get("t1_compliant") == "")
    rejected = sum(1 for e in enrichments.values() if "unverifiable" in str(e.get("mismatch_note", "")))
    no_match = sum(1 for e in enrichments.values() if not e.get("nct_id"))

    summary = {
        "total_rows": total,
        "verified": verified,
        "verified_pct": f"{verified/total*100:.1f}%",
        "t1_compliant": t1_compliant,
        "t1_compliant_pct": f"{t1_compliant/total*100:.1f}%",
        "t1_unknown": t1_unknown,
        "rejected": rejected,
        "rejected_pct": f"{rejected/total*100:.1f}%",
        "no_nct_match": no_match,
        "no_match_pct": f"{no_match/total*100:.1f}%",
        "enriched_so_far": len(enrichments),
        "remaining": total - len(enrichments),
    }
    return summary


if __name__ == "__main__":
    # Load dataset
    rows = []
    with open(READOUT_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print(f"Loaded {len(rows)} events")

    # Load existing NCT matches
    with open(LOOKUP_JSON) as f:
        lookup = json.load(f)
    matched = lookup.get("matched", {})
    print(f"Pre-matched: {len(matched)} events with NCT IDs")

    # Load enrichment cache
    cache = load_enrichment_cache()
    print(f"Already enriched: {len(cache)} events")

    # Prepare batches
    need_get = []  # Have NCT ID, need get_study
    need_search = []  # No NCT ID, need search

    for i in range(len(rows)):
        if str(i) in cache:
            continue  # Already done
        if str(i) in matched and matched[str(i)].get("nct_id"):
            need_get.append((i, matched[str(i)]["nct_id"]))
        else:
            need_search.append(i)

    print(f"Need get_study: {len(need_get)}")
    print(f"Need search: {len(need_search)}")

    # Print first 20 search queries
    print("\nSample search queries:")
    for idx in need_search[:20]:
        row = rows[idx]
        query, drug, acronym = build_search_query(row)
        print(f"  [{idx}] query=\"{query}\" acronym=\"{acronym}\" date={row['date']}")
