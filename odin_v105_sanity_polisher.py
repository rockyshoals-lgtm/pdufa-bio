#!/usr/bin/env python3
"""
ODIN v10.5 "Sanity Polisher" (v10.5.3)
======================================
- FIXES: "Runaway Weights" (Social=1.75) from the previous run.
- CONSTRAINTS: Enforces 'Common Sense' bounds (Social <= 0.15, BTD >= 0.02).
- ALGORITHM: Coordinate Descent (Greedy Stepwise Optimization).
- GOAL: Restore interpretability and lower Brier score below 0.20.
"""

import numpy as np
import pandas as pd
import time
import json
import pickle
from dataclasses import dataclass

# Try CuPy
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    import numpy as cp
    GPU_AVAILABLE = False
    print("Warning: CuPy not found. CPU Mode.")

# --- CONFIG ---
DATA_FILE = "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv"
SEED_FILE = "odin_v105_optimized.csv"
OUTPUT_FILE = "odin_v105_polished.csv"

# Params mapping
PARAM_KEYS = [
    "base_approval_rate", "snda_base_penalty", "snda_pediatric_base_penalty",
    "btd_weight", "orphan_weight", "priority_review_weight", "fast_track_weight", "accelerated_approval_weight",
    "adcom_high_boost", "adcom_mid_penalty", "adcom_low_penalty",
    "prior_crl_penalty", "class1_resubmission_boost", "experienced_sponsor_boost", "inexperienced_sponsor_penalty",
    "manufacturing_risk_penalty", "form_483_penalty", "ema_cmc_flag_penalty", "cmc_extension_penalty",
    "ta_adjustment_weight", "s23_insider_weight", "s6_hiring_weight", "s22_pediatric_pk_penalty", "social_weight"
]

# --- SANITY BOUNDS (Min, Max) ---
# None = No limit
SANITY_BOUNDS = {
    "base_approval_rate": (0.30, 0.80), # Allow going lower than 0.50
    "social_weight": (0.0, 0.15),       # Hard cap on social
    "btd_weight": (0.02, 0.20),         # Force relevance
    "orphan_weight": (0.02, 0.20),
    "priority_review_weight": (0.02, 0.20),
    "s23_insider_weight": (0.0, 0.40),  # Cap insider influence
    "s6_hiring_weight": (0.0, 0.40),    # Cap hiring influence
}

class OdinPolisherEngine:
    def __init__(self, df):
        self.X, self.y = self._build_matrix(df)
        self.hard_avoid_mask = self._build_avoids(df)
        if GPU_AVAILABLE:
            self.X = cp.asarray(self.X)
            self.y = cp.asarray(self.y)
            self.hard_avoid_mask = cp.asarray(self.hard_avoid_mask)

    def _build_matrix(self, df):
        N = len(df)
        X = np.zeros((N, len(PARAM_KEYS)), dtype=np.float32)
        X[:, 0] = 1.0 
        
        def get_bool(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_values = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_values).astype(int).values.astype(np.float32)
            
        def get_val(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app_type_series(df):
            candidates = ['application_type', 'ApplicationType', 'app_type', 'catalyst_type', 'applicationText']
            for c in candidates:
                if c in df.columns: return df[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N) 

        # 1. Base
        app = get_app_type_series(df)
        X[:, 1] = (app.str.contains('SNDA') | app.str.contains('SBLA')).astype(float)
        X[:, 2] = (app.str.contains('PEDIATRIC')).astype(float)
        
        # 2. Designations
        X[:, 3] = get_bool('btd'); X[:, 4] = get_bool('orphan'); X[:, 5] = get_bool('priority_review')
        X[:, 6] = get_bool('fast_track'); X[:, 7] = get_bool('accelerated_approval')
        
        # 3. AdCom
        had_adcom = get_bool('had_adcom')
        vote = get_val('adcom_vote_pct'); vote = np.where(vote > 1, vote/100, vote)
        X[:, 8] = had_adcom * (vote >= 0.65)
        X[:, 9] = had_adcom * ((vote >= 0.50) & (vote < 0.65))
        X[:, 10] = had_adcom * (vote < 0.50)
        
        # 4. CRL/Sponsor
        X[:, 11] = get_bool('prior_crl')
        if 'resubmission_class' in df: X[:, 12] = (get_val('resubmission_class') == 1).astype(float)
        prior = get_val('sponsor_prior_approvals')
        X[:, 13] = (prior >= 5).astype(float); X[:, 14] = (prior == 0).astype(float)
        
        # 5. CMC
        X[:, 15] = get_bool('manufacturing_risk'); X[:, 16] = get_bool('form_483_issues')
        X[:, 17] = get_bool('ema_cmc_flag'); X[:, 18] = get_bool('cmc_extension_flag')
        
        # 6. TA & New Signals
        X[:, 19] = get_val('ta_base_score')
        X[:, 20] = get_val('s23_signal_strength')
        X[:, 21] = get_val('s6_signal_strength')
        X[:, 22] = get_bool('s22_ped_pk_missing')
        X[:, 23] = get_val('social_sentiment_score')
        
        # Y Target
        y_col = 'outcome'
        if 'outcome' not in df.columns:
            for c in ['Outcome', 'approved', 'label']:
                if c in df.columns: y_col = c; break
        
        if y_col in df.columns:
            y_raw = df[y_col].astype(str).str.upper()
            y = y_raw.isin(['APPROVED', '1', 'TRUE', 'YES']).astype(float).values
        else:
            y = np.zeros(N, dtype=np.float32)
        
        return X, y

    def _build_avoids(self, df):
        mask = np.ones(len(df), dtype=np.float32)
        def get_bool_local(col):
            if col not in df.columns: return np.zeros(len(df), dtype=bool)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_values = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_values).values

        bad = np.zeros(len(df), dtype=bool)
        bad |= get_bool_local('ema_cmc_flag')
        bad |= get_bool_local('s22_ped_pk_missing')
        bad |= get_bool_local('s23_risk_critical')
        mask[bad] = 0.0
        return mask

    def evaluate_one(self, config_vec):
        # 1. Calc Raw Scores
        # Vec (P,) @ X.T (P, N) -> (N,)
        scores = config_vec @ self.X.T
        scores *= self.hard_avoid_mask 
        
        # 3. Probabilities (Linear Clamp)
        probs = cp.clip(scores, 0.01, 0.99)
        
        # 4. Objective: Brier Score
        diff = probs - self.y
        brier = cp.mean(diff ** 2)
        
        return float(brier)

def apply_sanity_bounds(config_vec):
    """Clips vector to min/max defined in SANITY_BOUNDS."""
    for i, key in enumerate(PARAM_KEYS):
        if key in SANITY_BOUNDS:
            min_val, max_val = SANITY_BOUNDS[key]
            current = config_vec[i]
            if min_val is not None: current = max(current, min_val)
            if max_val is not None: current = min(current, max_val)
            config_vec[i] = current
    return config_vec

def main():
    print("Loading...")
    try:
        df = pd.read_csv(DATA_FILE)
        seed_df = pd.read_csv(SEED_FILE)
    except Exception as e: 
        print(f"Failed to load: {e}")
        return

    engine = OdinPolisherEngine(df)
    
    # Init from seed
    best_config_dict = seed_df.iloc[0].to_dict()
    current_vec = np.array([best_config_dict.get(k, 0.0) for k in PARAM_KEYS], dtype=np.float32)
    
    # 1. Force Sanity INITIAL Check
    print("Applying initial sanity clamps...")
    current_vec = apply_sanity_bounds(current_vec)
    if GPU_AVAILABLE: current_vec_gpu = cp.asarray(current_vec)
    else: current_vec_gpu = current_vec
        
    current_brier = engine.evaluate_one(current_vec_gpu)
    print(f"Starting Brier (Sanitized): {current_brier:.5f}")
    
    # --- COORDINATE DESCENT ---
    # Scan each param, step up/down, keep if better
    
    step_sizes = [0.05, 0.01, 0.005, 0.001]
    
    for step in step_sizes:
        print(f"\n--- Polishing with step size {step} ---")
        improved = True
        while improved:
            improved = False
            for i, key in enumerate(PARAM_KEYS):
                original_val = current_vec[i]
                best_val_for_param = original_val
                
                # Try Up and Down
                candidates = [original_val - step, original_val + step]
                
                for cand in candidates:
                    # Check Sanity
                    test_vec = current_vec.copy()
                    test_vec[i] = cand
                    test_vec = apply_sanity_bounds(test_vec) # Re-clamp to be safe
                    
                    # Eval
                    if GPU_AVAILABLE: tv_gpu = cp.asarray(test_vec)
                    else: tv_gpu = test_vec
                    
                    brier = engine.evaluate_one(tv_gpu)
                    
                    if brier < current_brier:
                        current_brier = brier
                        current_vec = test_vec # Accept change
                        best_val_for_param = test_vec[i]
                        improved = True
                        # print(f"   Improved {key}: {best_val_for_param:.4f} (Brier: {current_brier:.5f})")
                        
    # Final Output
    print(f"\nFinal Brier: {current_brier:.5f}")
    
    final_config = {k: float(current_vec[i]) for i, k in enumerate(PARAM_KEYS)}
    
    # Calculate Thresholds on Final Score Distribution
    if GPU_AVAILABLE: final_vec_gpu = cp.asarray(current_vec)
    else: final_vec_gpu = current_vec
    
    scores = final_vec_gpu @ engine.X.T
    scores = cp.asnumpy(scores) if GPU_AVAILABLE else scores
    
    final_config['tier1_threshold'] = float(np.percentile(scores, 80))
    final_config['tier2_threshold'] = float(np.percentile(scores, 60))
    final_config['tier3_threshold'] = float(np.percentile(scores, 40))
    final_config['brier_score'] = float(current_brier)
    
    print(json.dumps(final_config, indent=2))
    pd.DataFrame([final_config]).to_csv(OUTPUT_FILE, index=False)
    print("Done.")

if __name__ == "__main__":
    main()