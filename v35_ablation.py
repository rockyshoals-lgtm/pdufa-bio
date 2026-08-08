#!/usr/bin/env python3
"""
Quick ablation: Run v35 pipeline with ONLY v33 base features (drop all 45 v35 features).
This isolates whether the AUC jump comes from:
  A) v35 CT.gov features (45 new)
  B) v35 training code path differences vs original v33
  C) XGB_SLOW architecture (500 trees, lr=0.02)
"""
import subprocess, sys, os

# Monkey-patch the v35 features module to return empty dict
# Then run the full pipeline
patch_code = '''
import ctgov_v35_features as mod
_orig = mod.get_ctgov_v35_features
def _stub(row, ctgov_data=None):
    return {}
mod.get_ctgov_v35_features = _stub
'''

# Alternative: read gungnir_v35_train.py source, patch the feature engineering
# to skip v35 features, and exec it

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

# We'll import v35 train code and override the feature module
import importlib
import ctgov_v35_features
ctgov_v35_features.get_ctgov_v35_features = lambda row, ctgov_data=None: {}

# Now run the training by importing it (exec the script)
print("="*80)
print("ABLATION: v35 pipeline with v35 features DISABLED (should give ~103 features)")
print("="*80)

# Just exec the whole v35 script
exec(open(os.path.join(DATA_DIR, "gungnir_v35_train.py")).read())
