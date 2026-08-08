#!/usr/bin/env python3
"""
Processes saved MCP CT.gov result files into enrichment cache.
Reads JSON result files, extracts fields, maps to dataset rows.
"""
import csv, json, os, sys, glob
from ctgov_batch_processor import extract_from_protocol

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
LOOKUP_JSON = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
ENRICHMENT_CACHE = os.path.join(DATA_DIR, "ctgov_enrichment_cache.json")
RESULTS_DIR = "/sessions/loving-nifty-dirac/mnt/.claude/projects/-sessions-loving-nifty-dirac/5db8cef9-079f-4c70-b43a-b59f077bd5d4/tool-results"

def load_rows():
    rows = []
    with open(READOUT_CSV) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def load_nct_to_rows():
    with open(LOOKUP_JSON) as f:
        lookup = json.load(f)
    matched = lookup.get("matched", {})
    nct_to_rows = {}
    for row_idx, info in matched.items():
        nct_id = info.get("nct_id", "")
        if nct_id:
            if nct_id not in nct_to_rows:
                nct_to_rows[nct_id] = []
            nct_to_rows[nct_id].append(row_idx)
    return nct_to_rows

def process_result_file(filepath, rows, nct_to_rows, cache):
    """Process a single MCP result file and update cache."""
    with open(filepath) as f:
        data = json.load(f)

    new_entries = 0
    # Handle both get_study and search_studies response formats
    studies = data.get("studies", [])
    if not studies:
        paged = data.get("pagedStudies", {})
        studies = paged.get("studies", [])

    for study in studies:
        proto = study.get("protocolSection", {})
        nct_id = proto.get("identificationModule", {}).get("nctId", "")

        if nct_id in nct_to_rows:
            for row_idx in nct_to_rows[nct_id]:
                if row_idx not in cache:
                    catalyst_date = rows[int(row_idx)].get("date", "")
                    enrichment = extract_from_protocol(proto, catalyst_date)
                    cache[row_idx] = enrichment
                    new_entries += 1

    return new_entries

def process_all_results():
    rows = load_rows()
    nct_to_rows = load_nct_to_rows()

    # Load existing cache
    cache = {}
    if os.path.exists(ENRICHMENT_CACHE):
        with open(ENRICHMENT_CACHE) as f:
            cache = json.load(f)

    print(f"Rows: {len(rows)}, Matched NCTs: {len(nct_to_rows)}, Existing cache: {len(cache)}")

    # Find all result files
    result_files = glob.glob(os.path.join(RESULTS_DIR, "*.txt"))
    total_new = 0

    for fpath in sorted(result_files):
        try:
            new = process_result_file(fpath, rows, nct_to_rows, cache)
            if new > 0:
                print(f"  {os.path.basename(fpath)}: +{new} entries")
                total_new += new
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  SKIP {os.path.basename(fpath)}: {e}")

    # Save updated cache
    with open(ENRICHMENT_CACHE, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"\nTotal new entries: {total_new}")
    print(f"Cache size: {len(cache)}")

    # Count remaining
    all_matched_rows = set()
    for row_list in nct_to_rows.values():
        all_matched_rows.update(row_list)
    cached_matched = set(cache.keys()) & all_matched_rows
    print(f"Matched rows enriched: {len(cached_matched)}/{len(all_matched_rows)}")
    print(f"Remaining matched: {len(all_matched_rows) - len(cached_matched)}")

    return cache

if __name__ == "__main__":
    process_all_results()
