#!/usr/bin/env python3
"""
Processes MCP search results for unmatched rows (no pre-assigned NCT ID).
Reads saved result files tagged with 'unmatched' prefix, finds best match,
verifies match quality, and saves to enrichment cache.
"""
import csv, json, os, re, glob
from datetime import datetime, timezone
from ctgov_batch_processor import extract_from_protocol

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHMENT_CACHE = os.path.join(DATA_DIR, "ctgov_enrichment_cache.json")
UNMATCHED_QUEUE = os.path.join(DATA_DIR, "unmatched_search_queue.json")
RESULTS_DIR = "/sessions/loving-nifty-dirac/mnt/.claude/projects/-sessions-loving-nifty-dirac/5db8cef9-079f-4c70-b43a-b59f077bd5d4/tool-results"

def load_rows():
    rows = []
    with open(READOUT_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def match_study_to_drug(study, drug_name, indication=""):
    """Score how well a CT.gov study matches a drug/indication pair."""
    proto = study.get("protocolSection", {})
    title = proto.get("identificationModule", {}).get("briefTitle", "").lower()
    official_title = proto.get("identificationModule", {}).get("officialTitle", "").lower()

    arms_mod = proto.get("armsInterventionsModule", {})
    interventions = [i.get("name", "").lower() for i in arms_mod.get("interventions", [])]
    all_intervention_text = " ".join(interventions)

    conditions = [c.lower() for c in proto.get("conditionsModule", {}).get("conditions", [])]
    all_conditions = " ".join(conditions)

    # Clean drug name
    drug_clean = re.sub(r'\s*-\s*\(.*?\)', '', drug_name).strip().lower()
    drug_clean = re.sub(r'\s*\(.*?\)', '', drug_clean).strip()
    first_drug = drug_clean.split(" plus ")[0].split("/")[0].strip()

    score = 0
    # Drug name in title (+3)
    if first_drug and first_drug in title:
        score += 3
    elif first_drug and first_drug in official_title:
        score += 2
    # Drug name in interventions (+2)
    if first_drug and first_drug in all_intervention_text:
        score += 2
    # Indication match (+1)
    if indication:
        ind_clean = re.sub(r'\(.*?\)', '', indication).strip().lower()
        ind_words = ind_clean.split()[:3]
        ind_match = sum(1 for w in ind_words if len(w) > 3 and (w in all_conditions or w in title))
        score += min(ind_match, 2)

    return score

def process_search_result_for_unmatched(result_file, query_info, rows, cache):
    """Process a search result file for unmatched rows."""
    try:
        with open(result_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return 0

    studies = data.get("pagedStudies", {}).get("studies", [])
    if not studies:
        studies = data.get("studies", [])

    if not studies:
        # No results - mark all rows as no match
        new = 0
        for idx in query_info["rows"]:
            if str(idx) not in cache:
                cache[str(idx)] = {
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
                new += 1
        return new

    # Score each study against drug/indication
    drug = query_info.get("drug", "")
    row0 = rows[query_info["rows"][0]]
    indication = row0.get("indication", "")

    best_study = None
    best_score = 0
    for study in studies:
        score = match_study_to_drug(study, drug, indication)
        if score > best_score:
            best_score = score
            best_study = study

    if not best_study:
        best_study = studies[0]

    new = 0
    for idx in query_info["rows"]:
        if str(idx) not in cache:
            row = rows[idx]
            catalyst_date = row.get("date", "")
            proto = best_study.get("protocolSection", {})
            enrichment = extract_from_protocol(proto, catalyst_date)

            # Add match quality flag
            if best_score < 2:
                enrichment["provenance_verified"] = 0
                enrichment["mismatch_note"] = (enrichment.get("mismatch_note", "") +
                    ";low_match_score").strip(";")

            cache[str(idx)] = enrichment
            new += 1

    return new

if __name__ == "__main__":
    rows = load_rows()

    cache = {}
    if os.path.exists(ENRICHMENT_CACHE):
        with open(ENRICHMENT_CACHE) as f:
            cache = json.load(f)

    print(f"Cache before: {len(cache)}")
    print(f"Total rows: {len(rows)}")
    print(f"Remaining: {len(rows) - len(cache)}")
