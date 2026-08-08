#!/usr/bin/env python3
"""
Extract structured trial features from CT.gov trial details.
Handles masking rigor scoring, endpoint classification, site/country counting.
"""

import json
import re

def classify_endpoint(endpoint_text):
    """Classify endpoint as hard (OS/mortality/MACE) or surrogate."""
    if not endpoint_text:
        return False, False
    
    text = endpoint_text.lower()
    
    # Hard endpoints
    hard_keywords = [
        "overall survival", "mortality", "death", "os",
        "major adverse cardiac event", "mace",
        "myocardial infarction", "stroke",
        "hospitalization", "disease progression"
    ]
    
    # Surrogate endpoints
    surrogate_keywords = [
        "response rate", "orr", "objective response",
        "progression-free survival", "pfs",
        "biomarker", "viral load", "immune response",
        "quality of life", "pain score"
    ]
    
    is_hard = any(kw in text for kw in hard_keywords)
    is_surrogate = any(kw in text for kw in surrogate_keywords)
    
    return is_hard, is_surrogate

def extract_masking_rigor(masking_type):
    """Score masking rigor: 0=none, 1=single, 2=double, 3=triple, 4=quad."""
    if not masking_type:
        return 0
    
    m = masking_type.upper()
    
    if "NONE" in m:
        return 0
    elif "SINGLE" in m:
        return 1
    elif "DOUBLE" in m or "DOUBLE-BLIND" in m:
        return 2
    elif "TRIPLE" in m:
        return 3
    elif "QUAD" in m:
        return 4
    else:
        # Fallback: assume some masking
        return 1

def extract_features_from_trial(trial_dict):
    """Extract structured features from CT.gov trial dict."""
    
    # Basic identification
    nct_id = trial_dict.get("nct_id", "NOT_FOUND")
    
    if nct_id == "NOT_FOUND":
        return {
            "nct_id": "NOT_FOUND",
            "enrollment": 0,
            "n_arms": 0,
            "is_randomized": 0,
            "is_double_blind": 0,
            "is_placebo": 0,
            "masking_rigor": 0,
            "has_dmc": 0,
            "ep_hard": 0,
            "ep_surrogate": 0,
            "n_sites": 0,
            "n_countries": 0,
            "is_global": 0,
            "has_withdrawals": 0,
            "phase": ""
        }
    
    # Enrollment
    enrollment = trial_dict.get("enrollment", 0) or 0
    
    # Phase
    phases = trial_dict.get("phase", [])
    phase_str = "PHASE" + str(phases[-1][-1]) if phases and phases[-1][-1].isdigit() else ""
    
    # Randomization
    is_randomized = 1 if "randomized" in trial_dict.get("title", "").lower() else 0
    
    # Masking
    masking = trial_dict.get("design_masking", "NONE") if isinstance(trial_dict, dict) else "NONE"
    masking_rigor = extract_masking_rigor(masking)
    is_double_blind = 1 if masking_rigor >= 2 else 0
    
    # Placebo — check in interventions and arm labels
    is_placebo = 0
    interventions = trial_dict.get("interventions", [])
    if isinstance(interventions, list):
        is_placebo = 1 if any("placebo" in str(i).lower() for i in interventions) else 0
    
    # Number of arms
    n_arms = len(trial_dict.get("arms", [])) if "arms" in trial_dict else 0
    
    # Data monitoring committee
    has_dmc = 1 if trial_dict.get("data_monitoring_committee") else 0
    
    # Endpoints
    primary_outcomes = trial_dict.get("primary_outcomes", [])
    primary_ep_text = ""
    if primary_outcomes:
        primary_ep_text = primary_outcomes[0].get("measure", "") if isinstance(primary_outcomes[0], dict) else str(primary_outcomes[0])
    
    ep_hard, ep_surrogate = classify_endpoint(primary_ep_text)
    
    # Locations
    locations = trial_dict.get("locations", [])
    n_sites = len([l for l in locations if isinstance(l, dict)]) if locations else 0
    
    # Countries
    countries = set()
    if locations:
        for loc in locations:
            if isinstance(loc, dict) and "country" in loc:
                countries.add(loc["country"])
    n_countries = len(countries)
    is_global = 1 if n_countries > 1 else 0
    
    return {
        "nct_id": nct_id,
        "enrollment": int(enrollment),
        "n_arms": int(n_arms),
        "is_randomized": int(is_randomized),
        "is_double_blind": int(is_double_blind),
        "is_placebo": int(is_placebo),
        "masking_rigor": int(masking_rigor),
        "has_dmc": int(has_dmc),
        "ep_hard": int(ep_hard),
        "ep_surrogate": int(ep_surrogate),
        "n_sites": int(n_sites),
        "n_countries": int(n_countries),
        "is_global": int(is_global),
        "has_withdrawals": 0,  # Not in API response
        "phase": phase_str
    }

if __name__ == "__main__":
    # Test with the GC012F trial
    test_trial = {
        "nct_id": "NCT06235229",
        "enrollment": 110,
        "phase": ["PHASE1", "PHASE2"],
        "title": "A Phase I/II Clinical Study of Chimeric Antigen Receptor T-cell Therapy Targeting CD19 and BCMA (GC012F) in Patients With Relapsed/Refractory Multiple Myeloma",
        "primary_outcomes": [
            {"measure": "Phase 1: Dose-limiting toxicities", "time_frame": "28 days"},
            {"measure": "Phase 2: Overall response rate", "time_frame": "2 years"}
        ],
        "locations": [
            {"country": "China", "city": "Beijing"},
            {"country": "China", "city": "Shanghai"}
        ]
    }
    
    features = extract_features_from_trial(test_trial)
    print(json.dumps(features, indent=2))
