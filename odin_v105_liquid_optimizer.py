#!/usr/bin/env python3
"""
ODIN v10.5 "Liquid" Optimizer (v10.5.2 - Robust Data Types)
===========================================================
- FIXED: Handles columns containing strings "False"/"True" instead of real booleans.
- FIXED: Handles columns containing mixed text/numbers without crashing.
- ARCHITECTURE: Optimizes Raw Score separation (AUC/Brier).
- DYNAMIC TIERS: Automatically sets Tier 1 to the Top N% of scores found.
"""

import numpy as np
import pandas as pd
import time
import json
import pickle
from sklearn.isotonic import IsotonicRegression
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
OUTPUT_FILE = "odin_v105_optimized.csv"
CALIBRATOR_FILE = "odin_v105_calibrator.pkl"
BATCH_SIZE = 100_000
N_BATCHES = 100  # 10 Million total
TARGET_TIER1_PCT = 0.20 

# Features 
PARAM_KEYS = [
    "base_approval_rate", "snda_base_penalty", "snda_pediatric_base_penalty",
    "btd_weight", "orphan_weight", "priority_review_weight", "fast_track_weight", "accelerated_approval_weight",
    "adcom_high_boost", "adcom_mid_penalty", "adcom_low_penalty",
    "prior_crl_penalty", "class1_resubmission_boost", "experienced_sponsor_boost", "inexperienced_sponsor_penalty",
    "manufacturing_risk_penalty", "form_483_penalty", "ema_cmc_flag_penalty", "cmc_extension_penalty",
    "ta_adjustment_weight", "s23_insider_weight", "s6_hiring_weight", "s22_pediatric_pk_penalty", "social_weight"
]

# Constraints (1=Pos, -1=Neg, 0=Free)
PARAM_CONSTRAINTS = np.array([
    1, -1, -1,
    1, 1, 1, 1, 1,
    1, -1, -1,
    -1, 1, 1, -1,
    -1, -1, -1, -1,
    1, 1, 1, -1, 1
], dtype=np.float32)

class OdinLiquidEngine:
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
        X[:, 0] = 1.0 # Base rate bias
        
        # --- ROBUST HELPERS ---
        def get_bool(col):
            """Converts mixed types (bool/str/int) to 0.0/1.0 safely."""
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            # Force to string, uppercase, check against True set
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_values = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_values).astype(int).values.astype(np.float32)
            
        def get_val(col):
            """Converts mixed types to float safely, coercing errors to 0.0."""
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app_type_series(df):
            # Try multiple variations of the column name
            candidates = ['application_type', 'ApplicationType', 'app_type', 'catalyst_type', 'applicationText']
            for c in candidates:
                if c in df.columns:
                    return df[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N) 

        # 1. Base Penalties
        app = get_app_type_series(df)
        X[:, 1] = (app.str.contains('SNDA') | app.str.contains('SBLA')).astype(float)
        X[:, 2] = (app.str.contains('PEDIATRIC')).astype(float)
        
        # 2. Designations
        X[:, 3] = get_bool('btd')
        X[:, 4] = get_bool('orphan')
        X[:, 5] = get_bool('priority_review')
        X[:, 6] = get_bool('fast_track')
        X[:, 7] = get_bool('accelerated_approval')
        
        # 3. AdCom
        had_adcom = get_bool('had_adcom')
        vote = get_val('adcom_vote_pct')
        vote = np.where(vote > 1, vote/100, vote)
        
        X[:, 8] = had_adcom * (vote >= 0.65)
        X[:, 9] = had_adcom * ((vote >= 0.50) & (vote < 0.65))
        X[:, 10] = had_adcom * (vote < 0.50)
        
        # 4. CRL/Sponsor
        X[:, 11] = get_bool('prior_crl')
        
        if 'resubmission_class' in df: X[:, 12] = (get_val('resubmission_class') == 1).astype(float)
        
        prior = get_val('sponsor_prior_approvals')
        X[:, 13] = (prior >= 5).astype(float)
        X[:, 14] = (prior == 0).astype(float)
        
        # 5. CMC
        X[:, 15] = get_bool('manufacturing_risk')
        X[:, 16] = get_bool('form_483_issues')
        X[:, 17] = get_bool('ema_cmc_flag')
        X[:, 18] = get_bool('cmc_extension_flag')
        
        # 6. TA & New Signals
        X[:, 19] = get_val('ta_base_score')
        X[:, 20] = get_val('s23_signal_strength')
        X[:, 21] = get_val('s6_signal_strength')
        X[:, 22] = get_bool('s22_ped_pk_missing')
        X[:, 23] = get_val('social_sentiment_score')
        
        # Y Target
        y_col = 'outcome'
        if 'outcome' not in df.columns:
            if 'Outcome' in df.columns: y_col = 'Outcome'
            elif 'approved' in df.columns: y_col = 'approved'
            elif 'label' in df.columns: y_col = 'label'
            
        if y_col in df.columns:
            y_raw = df[y_col].astype(str).str.upper()
            y = y_raw.isin(['APPROVED', '1', 'TRUE', 'YES']).astype(float).values
        else:
            print("[WARNING] No Outcome/Label column found! Setting target to 0.")
            y = np.zeros(N, dtype=np.float32)
        
        return X, y

    def _build_avoids(self, df):
        mask = np.ones(len(df), dtype=np.float32)
        
        # Use robust helpers here too
        def get_bool_local(col):
            if col not in df.columns: return np.zeros(len(df), dtype=bool)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_values = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_values).values

        bad = np.zeros(len(df), dtype=bool)
        bad |= get_bool_local('ema_cmc_flag')
        bad |= get_bool_local('s22_ped_pk_missing')
            
        mask[bad] = 0.0
        return mask

    def optimize_batch(self, batch_weights):
        # 1. Calc Raw Scores
        scores = cp.matmul(batch_weights, self.X.T)
        scores *= self.hard_avoid_mask 
        
        # 3. Probabilities (Linear Clamp)
        probs = cp.clip(scores, 0.01, 0.99)
        
        # 4. Objective: Minimize Brier Score
        diff = probs - self.y
        brier = cp.mean(diff ** 2, axis=1)
        
        # 5. Separation (Proxy for AUC)
        y_sum = cp.sum(self.y)
        neg_sum = cp.sum(1-self.y)
        
        if y_sum > 0: score_pos = cp.sum(probs * self.y, axis=1) / y_sum
        else: score_pos = 0.0
            
        if neg_sum > 0: score_neg = cp.sum(probs * (1-self.y), axis=1) / neg_sum
        else: score_neg = 0.0
            
        separation = score_pos - score_neg
        
        # Final Fitness
        fitness = separation - (2.0 * brier)
        
        return fitness, brier

def main():
    print("Loading...")
    try:
        df = pd.read_csv(DATA_FILE)
        print(f"Loaded {len(df)} rows.")
    except Exception as e: 
        print(f"Failed to load data: {e}")
        return

    engine = OdinLiquidEngine(df)
    print(f"Engine Ready. X: {engine.X.shape}")
    
    best_fit = -999
    best_w = None
    best_brier = 1.0
    
    start_t = time.time()
    
    print(f"Starting search ({N_BATCHES} batches x {BATCH_SIZE})...")
    
    for i in range(N_BATCHES):
        # Generate random weights (-0.5 to 0.5)
        W = np.random.uniform(-0.5, 0.5, (BATCH_SIZE, len(PARAM_KEYS))).astype(np.float32)
        
        # Apply Constraints
        pos = (PARAM_CONSTRAINTS == 1)
        neg = (PARAM_CONSTRAINTS == -1)
        W[:, pos] = np.abs(W[:, pos])
        W[:, neg] = -np.abs(W[:, neg])
        W[:, 0] = np.random.uniform(0.60, 0.90, BATCH_SIZE) # Base rate
        
        if GPU_AVAILABLE: W = cp.asarray(W)
        
        fitness, brier = engine.optimize_batch(W)
        
        if GPU_AVAILABLE:
            fitness = fitness.get()
            brier = brier.get()
            W = W.get()
            
        idx = np.argmax(fitness)
        if fitness[idx] > best_fit:
            best_fit = fitness[idx]
            best_w = W[idx]
            best_brier = brier[idx]
            print(f"Batch {i}: New Best! Fitness={best_fit:.4f} | Brier={best_brier:.4f}")

    # Post-Process
    print("\nCalculating Dynamic Thresholds...")
    if best_w is None:
        print("No valid result found.")
        return

    # Run best weights on data
    X_np = engine.X if not GPU_AVAILABLE else cp.asnumpy(engine.X)
    scores = best_w @ X_np.T
    
    # Isotonic Calibration
    y_np = engine.y if not GPU_AVAILABLE else cp.asnumpy(engine.y)
    try:
        iso = IsotonicRegression(out_of_bounds='clip').fit(scores, y_np)
        
        # Save Calibrator
        with open(CALIBRATOR_FILE, 'wb') as f:
            pickle.dump(iso, f)
        print(f"Calibrator saved to {CALIBRATOR_FILE}")
    except Exception as e:
        print(f"Calibration failed (data issue?): {e}")
        
    # Find Cuts
    t1_cut = np.percentile(scores, 100 * (1 - TARGET_TIER1_PCT))
    t2_cut = np.percentile(scores, 100 * (1 - 0.40)) 
    t3_cut = np.percentile(scores, 100 * (1 - 0.60)) 
    
    # Output
    final_config = {k: float(best_w[i]) for i, k in enumerate(PARAM_KEYS)}
    final_config['tier1_threshold'] = float(t1_cut)
    final_config['tier2_threshold'] = float(t2_cut)
    final_config['tier3_threshold'] = float(t3_cut)
    final_config['brier_score'] = float(best_brier)
    
    print(json.dumps(final_config, indent=2))
    pd.DataFrame([final_config]).to_csv(OUTPUT_FILE, index=False)
    print("Done.")

if __name__ == "__main__":
    main()