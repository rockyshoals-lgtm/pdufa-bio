#!/usr/bin/env python3
"""
Process unmatched trial batches and extract ClinicalTrials.gov features.
Handles the 70-event unmatched batches and outputs structured JSON results.
"""

import json
import sys
import os

def extract_trial_features(trial_dict):
    """Extract structured features from a CT.gov trial dict."""
    
    features = {
        "nct_id": trial_dict.get("nct_id", "NOT_FOUND"),
        "enrollment": trial_dict.get("enrollment", 0) or 0,
        "n_arms": trial_dict.get("n_arms", 0) or 0,
        "is_randomized": 1 if trial_dict.get("is_randomized") else 0,
        "is_double_blind": 1 if trial_dict.get("is_double_blind") else 0,
        "is_placebo": 1 if trial_dict.get("is_placebo") else 0,
        "masking_rigor": trial_dict.get("masking_rigor", 0) or 0,
        "has_dmc": 1 if trial_dict.get("has_dmc") else 0,
        "ep_hard": 1 if trial_dict.get("ep_hard") else 0,
        "ep_surrogate": 1 if trial_dict.get("ep_surrogate") else 0,
        "n_sites": trial_dict.get("n_sites", 0) or 0,
        "n_countries": trial_dict.get("n_countries", 0) or 0,
        "is_global": 1 if trial_dict.get("is_global") else 0,
        "has_withdrawals": trial_dict.get("has_withdrawals", 0) or 0,
        "phase": trial_dict.get("phase", "")
    }
    
    return features

def process_batch(input_file, output_file):
    """Process a batch of unmatched trials and extract features."""
    
    with open(input_file, 'r') as f:
        input_data = json.load(f)
    
    results = {}
    
    for idx_str, event_data in input_data.items():
        if isinstance(event_data, dict) and "trial_data" in event_data:
            trial_data = event_data["trial_data"]
            results[idx_str] = extract_trial_features(trial_data)
        elif isinstance(event_data, dict):
            # Assume event_data is the trial dict itself
            results[idx_str] = extract_trial_features(event_data)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total = len(results)
    matched = sum(1 for v in results.values() if v["nct_id"] != "NOT_FOUND")
    unmatched = total - matched
    
    print(f"Processed {input_file}: {total} total | {matched} matched | {unmatched} NOT_FOUND")
    print(f"Output saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python process_unmatched_batches.py <input.json> <output.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    process_batch(input_file, output_file)
