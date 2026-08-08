#!/usr/bin/env python3
"""
Processes CT.gov MCP API results and saves to enrichment cache.
Called incrementally as batches of MCP results arrive.
"""
import json, os, re
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ENRICHMENT_CACHE = os.path.join(DATA_DIR, "ctgov_enrichment_cache.json")
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
LOOKUP_JSON = os.path.join(DATA_DIR, "ctgov_training_lookup.json")


def extract_from_protocol(proto, catalyst_date=None):
    """Extract enrichment fields from a CT.gov protocolSection."""
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    sponsor = proto.get("sponsorCollaboratorsModule", {})
    design = proto.get("designModule", {})
    outcomes = proto.get("outcomesModule", {})
    arms_mod = proto.get("armsInterventionsModule", {})

    nct_id = ident.get("nctId", "")
    start_date = status.get("startDateStruct", {}).get("date", "")
    completion_date = status.get("primaryCompletionDateStruct", {}).get("date", "")
    overall_status = status.get("overallStatus", "")
    enrollment = design.get("enrollmentInfo", {}).get("count", "")
    masking = design.get("designInfo", {}).get("maskingInfo", {}).get("masking", "NONE")

    # Primary endpoint
    primary_outcomes = outcomes.get("primaryOutcomes", [])
    primary_ep = primary_outcomes[0].get("measure", "") if primary_outcomes else ""

    # Placebo detection
    arm_groups = arms_mod.get("armGroups", [])
    has_placebo = 0
    for arm in arm_groups:
        arm_type = arm.get("type", "").upper()
        arm_label = arm.get("label", "").lower()
        interventions = " ".join(arm.get("interventionNames", [])).lower()
        if "placebo" in arm_type or "placebo" in arm_label or "placebo" in interventions:
            has_placebo = 1
            break

    n_arms = len(arm_groups)
    sponsor_exact = sponsor.get("leadSponsor", {}).get("name", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # T-1 compliance
    first_posted = status.get("studyFirstPostDateStruct", {}).get("date", "")
    t1_compliant = ""
    mismatch_note = ""
    if catalyst_date and first_posted:
        try:
            posted_dt = datetime.strptime(first_posted[:10], "%Y-%m-%d")
            catalyst_dt = datetime.strptime(catalyst_date[:10], "%Y-%m-%d")
            days_before = (catalyst_dt - posted_dt).days
            t1_compliant = 1 if days_before >= 30 else 0
            if days_before < 30:
                mismatch_note = f"posted_only_{days_before}d_before_catalyst"
        except ValueError:
            mismatch_note = "date_parse_error"
    elif not first_posted:
        mismatch_note = "no_first_posted_date"

    return {
        "nct_id": nct_id,
        "ctgov_startdate": start_date,
        "ctgov_completiondate": completion_date,
        "ctgov_status": overall_status,
        "ctgov_enrollment": enrollment,
        "ctgov_masking": masking,
        "ctgov_primary_endpoint": primary_ep[:500],
        "ctgov_has_placebo_arm": has_placebo,
        "ctgov_narms": n_arms,
        "ctgov_sponsor_exact": sponsor_exact,
        "retrieval_timestamp": timestamp,
        "provenance_verified": 1,
        "t1_compliant": t1_compliant,
        "mismatch_note": mismatch_note,
    }


def process_search_response(response_json, nct_to_rows, rows):
    """Process a search API response and update enrichment cache.

    Args:
        response_json: The raw JSON from clinicaltrials_search_studies
        nct_to_rows: dict mapping NCT ID -> list of row indices
        rows: the full dataset rows

    Returns:
        dict of {row_index_str: enrichment_dict}
    """
    results = {}
    studies = response_json.get("pagedStudies", {}).get("studies", [])

    for study in studies:
        proto = study.get("protocolSection", {})
        nct_id = proto.get("identificationModule", {}).get("nctId", "")

        if nct_id in nct_to_rows:
            for row_idx in nct_to_rows[nct_id]:
                catalyst_date = rows[row_idx].get("date", "")
                enrichment = extract_from_protocol(proto, catalyst_date)
                results[str(row_idx)] = enrichment

    return results


def process_unmatched_search(response_json, row_idx, row):
    """Process a search API response for an unmatched row.

    Returns the best matching study's enrichment, or empty if no match.
    """
    studies = response_json.get("pagedStudies", {}).get("studies", [])
    if not studies:
        return {
            "nct_id": "",
            "ctgov_startdate": "", "ctgov_completiondate": "",
            "ctgov_status": "", "ctgov_enrollment": "",
            "ctgov_masking": "", "ctgov_primary_endpoint": "",
            "ctgov_has_placebo_arm": "", "ctgov_narms": "",
            "ctgov_sponsor_exact": "",
            "retrieval_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "provenance_verified": 0,
            "t1_compliant": "",
            "mismatch_note": "no_ctgov_match_found",
        }

    # Take best match (first result)
    proto = studies[0].get("protocolSection", {})
    catalyst_date = row.get("date", "")
    enrichment = extract_from_protocol(proto, catalyst_date)

    # Verify match quality
    drug_name = row.get("drug", "").lower()
    study_title = proto.get("identificationModule", {}).get("briefTitle", "").lower()
    interventions = [i.get("name", "").lower() for i in
                     proto.get("armsInterventionsModule", {}).get("interventions", [])]
    all_intervention_text = " ".join(interventions)

    # Check if drug name appears in title or interventions
    drug_first = re.sub(r'\s*-\s*\(.*?\)', '', drug_name).split(" plus ")[0].split("/")[0].strip()
    drug_words = drug_first.split()[:2]  # First 2 words
    match_score = sum(1 for w in drug_words if w in study_title or w in all_intervention_text)

    if match_score == 0:
        enrichment["provenance_verified"] = 0
        enrichment["mismatch_note"] = (enrichment.get("mismatch_note", "") +
                                        ";drug_name_not_in_study").strip(";")

    return enrichment


if __name__ == "__main__":
    import csv
    rows = []
    with open(READOUT_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    cache = {}
    if os.path.exists(ENRICHMENT_CACHE):
        with open(ENRICHMENT_CACHE) as f:
            cache = json.load(f)

    print(f"Total rows: {len(rows)}")
    print(f"Currently enriched: {len(cache)}")
    print(f"Remaining: {len(rows) - len(cache)}")
