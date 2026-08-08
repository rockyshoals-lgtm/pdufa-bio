#!/usr/bin/env python3
"""
Bulk update batch results from a pre-populated matches dict.
This consolidates MCP search results and updates the batch files.
"""

import json
import sys

def extract_features(trial_dict):
    """Extract structured features from trial dict."""
    return {
        "nct_id": trial_dict.get("nct_id", "NOT_FOUND"),
        "enrollment": trial_dict.get("enrollment", 0) or 0,
        "n_arms": trial_dict.get("n_arms", 0) or 0,
        "is_randomized": trial_dict.get("is_randomized", 0) or 0,
        "is_double_blind": trial_dict.get("is_double_blind", 0) or 0,
        "is_placebo": trial_dict.get("is_placebo", 0) or 0,
        "masking_rigor": trial_dict.get("masking_rigor", 0) or 0,
        "has_dmc": trial_dict.get("has_dmc", 0) or 0,
        "ep_hard": trial_dict.get("ep_hard", 0) or 0,
        "ep_surrogate": trial_dict.get("ep_surrogate", 0) or 0,
        "n_sites": trial_dict.get("n_sites", 0) or 0,
        "n_countries": trial_dict.get("n_countries", 0) or 0,
        "is_global": trial_dict.get("is_global", 0) or 0,
        "has_withdrawals": trial_dict.get("has_withdrawals", 0) or 0,
        "phase": trial_dict.get("phase", "")
    }

def merge_matches(batch_num, matches_dict):
    """Merge matches into batch results file."""
    
    batch_file = f"/sessions/loving-nifty-dirac/mnt/Python/9realms/ctgov_batch_{batch_num}_results.json"
    
    # Load existing results
    with open(batch_file) as f:
        results = json.load(f)
    
    # Update with matches
    for idx_str, trial_dict in matches_dict.items():
        if idx_str in results:
            results[idx_str] = extract_features(trial_dict)
    
    # Save
    with open(batch_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total = len(results)
    matched = sum(1 for v in results.values() if v["nct_id"] != "NOT_FOUND")
    print(f"Batch {batch_num} updated: {total} total | {matched} matched | {total - matched} NOT_FOUND")

if __name__ == "__main__":
    # Manual matches discovered via MCP searches
    # Format: {batch_num: {idx_str: trial_dict}, ...}
    
    matches = {
        1: {
            "678": {  # GC012F
                "nct_id": "NCT06235229",
                "enrollment": 110,
                "n_arms": 0,
                "is_randomized": 0,
                "is_double_blind": 0,
                "is_placebo": 0,
                "masking_rigor": 0,
                "has_dmc": 0,
                "ep_hard": 1,  # Overall response rate is hard/primary
                "ep_surrogate": 0,
                "n_sites": 10,
                "n_countries": 1,
                "is_global": 0,
                "has_withdrawals": 0,
                "phase": "PHASE2"
            },
            "679": {  # ZYNLONTA
                "nct_id": "NCT05453396",
                "enrollment": 40,
                "n_arms": 1,
                "is_randomized": 0,
                "is_double_blind": 0,
                "is_placebo": 0,
                "masking_rigor": 0,
                "has_dmc": 0,
                "ep_hard": 1,  # ORR
                "ep_surrogate": 0,
                "n_sites": 1,
                "n_countries": 1,
                "is_global": 0,
                "has_withdrawals": 0,
                "phase": "PHASE2"
            }
        },
        3: {}  # Batch 3 — will add matches as discovered
    }
    
    # Apply matches
    for batch_num, batch_matches in matches.items():
        if batch_matches:
            merge_matches(batch_num, batch_matches)

