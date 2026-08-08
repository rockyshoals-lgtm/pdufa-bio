#!/usr/bin/env python3
"""
Ablation: Test v35 feature categories individually against the v33 baseline.
Uses the FIXED v35 script (T-1 compliant sponsor/indication).
Tests: base_only, +endpoint, +timing, +stringency, +intervention, +sponsor_type, +interactions, +all
"""
import os, sys, json, csv, math, warnings, re
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = "/sessions/loving-nifty-dirac/mnt/Python/9realms"
sys.path.insert(0, DATA_DIR)

# We need to extract the feature engineering + walk-forward from v35_train
# Rather than duplicating 900 lines, let's surgically test by importing the module
# and filtering feature columns

from ctgov_v35_features import get_ctgov_v35_features, load_ctgov_data

# Define v35 feature categories
V35_CATEGORIES = {
    "endpoint": ["ep_is_os", "ep_is_pfs", "ep_is_orr", "ep_is_safety", "ep_is_biomarker", 
                  "ep_is_pk_pd", "ep_is_qol", "num_primary_outcomes", "num_secondary_outcomes", 
                  "num_total_outcomes", "ep_count_ratio"],
    "timing": ["primary_timeframe_days", "log_primary_timeframe", "time_to_primary_completion",
               "time_to_readout_days", "study_duration_planned"],
    "stringency": ["inclusion_criteria_count", "exclusion_criteria_count", "total_criteria_count",
                    "log_elig_text_length", "stringency_score", "elig_text_length"],
    "intervention": ["has_drug", "has_biological", "has_genetic", "has_combination",
                      "has_active_comparator"],
    "comparator": ["has_sham_comparator", "comparator_richness"],
    "sponsor_type": ["is_industry", "is_nih", "is_academic", "has_industry_collab",
                      "is_fda_regulated_drug", "num_collaborators"],
    "enrollment": ["is_actual_enrollment", "healthy_volunteers"],
    "interactions": ["phase3_x_os", "phase3_x_orr", "phase3_x_biomarker", "phase2_x_biomarker",
                     "onc_x_pk_pd", "industry_x_double_blind", "industry_x_randomized",
                     "academic_x_single_arm", "stringency_x_large_trial", "biomarker_x_enrollment",
                     "phase3_x_surrogate_x_biomarker"],
}

# Quick approach: run the fixed v35 training script but control which v35 features to include
# We'll modify ctgov_v35_features to only return specific categories

import ctgov_v35_features as mod
_orig_fn = mod.get_ctgov_v35_features

def make_filtered_fn(allowed_prefixes):
    """Create a filtered version that only returns features matching allowed categories."""
    def filtered_fn(row, ctgov_data=None):
        all_feats = _orig_fn(row, ctgov_data)
        if not allowed_prefixes:
            return {}
        allowed_keys = set()
        for cat in allowed_prefixes:
            allowed_keys.update(V35_CATEGORIES.get(cat, []))
        return {k: v for k, v in all_feats.items() if k in allowed_keys}
    return filtered_fn

# For efficiency, we'll just test a few key combos
test_configs = [
    ("base_only", []),
    ("+endpoint", ["endpoint"]),
    ("+stringency", ["stringency"]),
    ("+interactions", ["interactions"]),
    ("+endpoint+interactions", ["endpoint", "interactions"]),
    ("+all_v35", list(V35_CATEGORIES.keys())),
]

print("="*80)
print("v35 CATEGORY ABLATION (fixed, T-1 compliant)")
print("="*80)

for config_name, categories in test_configs:
    # Patch the module
    if categories:
        mod.get_ctgov_v35_features = make_filtered_fn(categories)
    else:
        mod.get_ctgov_v35_features = lambda row, ctgov_data=None: {}
    
    # Run the training script and capture just the WF AUC
    # We need to exec it in a subprocess to avoid variable pollution
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(DATA_DIR, "gungnir_v35_train.py")],
        capture_output=True, text=True, timeout=300,
        cwd=DATA_DIR
    )
    
    # Parse AUC from output
    output = result.stdout + result.stderr
    auc_line = [l for l in output.split('\n') if 'Walk-forward AUC:' in l]
    brier_line = [l for l in output.split('\n') if 'Walk-forward Brier:' in l]
    feat_line = [l for l in output.split('\n') if 'Features:' in l and 'Events' not in l]
    
    auc = auc_line[0].split(':')[-1].strip() if auc_line else "?"
    brier = brier_line[0].split(':')[-1].strip() if brier_line else "?"
    n_feat = feat_line[0].split(':')[-1].strip() if feat_line else "?"
    
    print(f"  {config_name:30s}  Features={n_feat:>4s}  AUC={auc}  Brier={brier}")

# Restore original
mod.get_ctgov_v35_features = _orig_fn
print("\nDone.")
