"""
ODIN v10.6.1 "IRONCLAD" OPTIMIZER (Debugged & Hardened)
=======================================================
- FIX 1: Aggressive Target (Y) loading handles "1.0", "Success", "Approved", etc.
- FIX 2: Relaxed Thresholds (0.65 score, 5 count) to allow conservative models.
- HONESTY: Strict Time-Series Split (Train on Past, Test on Future).
- SANITY: Enforces Hard Sign Constraints (Boosts > 0, Penalties < 0).
"""

import numpy as np
import pandas as pd
import time
import json
import warnings
import sys
from dataclasses import dataclass

# Suppress warnings
warnings.filterwarnings("ignore")

# Try CuPy for GPU
try:
    import cupy as cp
    GPU_AVAILABLE = True
    print("[ODIN] GPU Acceleration: ENABLED (CuPy)")
except ImportError:
    import numpy as cp
    GPU_AVAILABLE = False
    print("[ODIN] GPU Acceleration: DISABLED (Running on CPU)")

# --- CONFIG ---
DATA_FILE = "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv"
OUTPUT_FILE = "odin_v106_honest_config.json"
TRAIN_SPLIT_PCT = 0.75  # 75% Train, 25% Test
BATCH_SIZE = 100_000
N_BATCHES = 200         # 20 Million Configs Total

# --- VALIDITY CONSTRAINTS (Relaxed) ---
# We accept models that separate well, even if raw scores are conservative.
VALID_SCORE_THRESH = 0.65  
VALID_COUNT_THRESH = 5     
VALID_SEP_THRESH = 0.001   # Must be positive (Winners > Losers)

# --- PARAMETER DEFINITIONS (Name, Sign, Min, Max) ---
# Sign: 1 (Pos), -1 (Neg), 0 (Free)
PARAMS_DEF = [
    # Base Rate (Conservative Range)
    ("base_approval_rate", 1, 0.40, 0.90),
    
    # Penalties (MUST BE NEGATIVE)
    ("snda_base_penalty", -1, 0.00, 0.15),
    ("snda_pediatric_base_penalty", -1, 0.00, 0.20),
    ("prior_crl_penalty", -1, 0.05, 0.30),
    ("inexperienced_sponsor_penalty", -1, 0.01, 0.20),
    ("manufacturing_risk_penalty", -1, 0.05, 0.25),
    ("form_483_penalty", -1, 0.01, 0.20),
    ("ema_cmc_flag_penalty", -1, 0.05, 0.35),
    ("cmc_extension_penalty", -1, 0.01, 0.20),
    ("adcom_mid_penalty", -1, 0.01, 0.20),
    ("adcom_low_penalty", -1, 0.10, 0.45),
    ("s22_pediatric_pk_penalty", -1, 0.05, 0.35),
    
    # Boosts (MUST BE POSITIVE)
    ("btd_weight", 1, 0.01, 0.20),
    ("orphan_weight", 1, 0.01, 0.20),
    ("priority_review_weight", 1, 0.01, 0.20),
    ("fast_track_weight", 1, 0.00, 0.15), 
    ("accelerated_approval_weight", 1, 0.00, 0.15),
    ("class1_resubmission_boost", 1, 0.05, 0.30),
    ("experienced_sponsor_boost", 1, 0.01, 0.15),
    ("adcom_high_boost", 1, 0.05, 0.30),
    
    # Scalars (0.0 to 1.0)
    ("ta_adjustment_weight", 1, 0.10, 1.0),
    ("s23_insider_weight", 1, 0.00, 0.30),
    ("s6_hiring_weight", 1, 0.00, 0.30),
    ("social_weight", 1, 0.00, 0.10) 
]

PARAM_NAMES = [p[0] for p in PARAMS_DEF]
# Pre-compile constraints for GPU
PARAM_SIGNS = cp.array([p[1] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[1] for p in PARAMS_DEF], dtype=np.float32)
PARAM_MINS = cp.array([p[2] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[2] for p in PARAMS_DEF], dtype=np.float32)
PARAM_MAXS = cp.array([p[3] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[3] for p in PARAMS_DEF], dtype=np.float32)

class OdinIroncladEngine:
    def __init__(self, df):
        # 1. Sort by Date (Prevention of Leakage)
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)
            print(f"[ODIN] Sorted {len(df)} events by date.")
        else:
            print("[ODIN] WARNING: No date column. Assuming index implies time.")

        # 2. Build Matrix (Robust)
        self.X, self.y = self._build_matrix(df)
        self.hard_avoid_mask = self._build_avoids(df)
        
        # DEBUG: Verify Labels
        pos_count = np.sum(self.y) if not GPU_AVAILABLE else cp.sum(self.y).item()
        print(f"[DEBUG] Positive Labels Found: {int(pos_count)}")
        if pos_count == 0:
            print("[CRITICAL] No positive labels found! Check csv 'outcome' column.")
            sys.exit(1)

        # 3. Time-Series Split
        split_idx = int(len(df) * TRAIN_SPLIT_PCT)
        
        self.X_train = self.X[:split_idx]
        self.y_train = self.y[:split_idx]
        self.mask_train = self.hard_avoid_mask[:split_idx]
        
        self.X_test = self.X[split_idx:]
        self.y_test = self.y[split_idx:]
        self.mask_test = self.hard_avoid_mask[split_idx:]
        
        print(f"[ODIN] Split: {len(self.y_train)} Train | {len(self.y_test)} Test")
        
        if GPU_AVAILABLE:
            self.X_train = cp.asarray(self.X_train)
            self.y_train = cp.asarray(self.y_train)
            self.mask_train = cp.asarray(self.mask_train)
            self.X_test = cp.asarray(self.X_test)
            self.y_test = cp.asarray(self.y_test)
            self.mask_test = cp.asarray(self.mask_test)

    def _build_matrix(self, df):
        N = len(df)
        X = np.zeros((N, len(PARAM_NAMES)), dtype=np.float32)
        X[:, 0] = 1.0 # Bias
        
        # --- ROBUST HELPERS ---
        def get_bool(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            # Handle "True", "1", "1.0", "Yes"
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_vals = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_vals).astype(int).values.astype(np.float32)
            
        def get_val(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app_type_series(df):
            candidates = ['application_type', 'ApplicationType', 'app_type', 'catalyst_type']
            for c in candidates:
                if c in df.columns: return df[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N) 

        # --- FEATURE MAPPING ---
        app = get_app_type_series(df)
        
        # Penalties (Col 1-11)
        X[:, 1] = (app.str.contains('SNDA') | app.str.contains('SBLA')).astype(float)
        X[:, 2] = (app.str.contains('PEDIATRIC')).astype(float)
        X[:, 3] = get_bool('prior_crl')
        
        prior = get_val('sponsor_prior_approvals')
        X[:, 4] = (prior == 0).astype(float) # Inexp Penalty
        
        X[:, 5] = get_bool('manufacturing_risk')
        X[:, 6] = get_bool('form_483_issues')
        X[:, 7] = get_bool('ema_cmc_flag')
        X[:, 8] = get_bool('cmc_extension_flag')
        
        had_adcom = get_bool('had_adcom')
        vote = get_val('adcom_vote_pct')
        vote = np.where(vote > 1, vote/100, vote)
        X[:, 9] = had_adcom * ((vote >= 0.50) & (vote < 0.65)) # Mid Penalty
        X[:, 10] = had_adcom * (vote < 0.50) # Low Penalty
        X[:, 11] = get_bool('s22_ped_pk_missing')

        # Boosts (Col 12-19)
        X[:, 12] = get_bool('btd')
        X[:, 13] = get_bool('orphan')
        X[:, 14] = get_bool('priority_review')
        X[:, 15] = get_bool('fast_track')
        X[:, 16] = get_bool('accelerated_approval')
        
        if 'resubmission_class' in df: X[:, 17] = (get_val('resubmission_class') == 1).astype(float)
        X[:, 18] = (prior >= 5).astype(float) # Exp Boost
        X[:, 19] = had_adcom * (vote >= 0.65) # High Boost
        
        # Scalars (Col 20-23)
        X[:, 20] = get_val('ta_base_score')
        X[:, 21] = get_val('s23_signal_strength')
        X[:, 22] = get_val('s6_signal_strength')
        X[:, 23] = get_val('social_sentiment_score')

        # --- ROBUST TARGET PARSING ---
        y_col = 'outcome'
        if 'outcome' not in df.columns:
            for c in ['Outcome', 'approved', 'label', 'result', 'y']:
                if c in df.columns: y_col = c; break
        
        if y_col in df.columns:
            y_raw = df[y_col].astype(str).str.strip().str.upper()
            # Clean floating point strings "1.0" -> "1"
            y_raw = y_raw.str.replace(r'\.0$', '', regex=True)
            positives = {'APPROVED', '1', 'TRUE', 'YES', 'SUCCESS', 'PASS'}
            y = y_raw.isin(positives).astype(float).values
        else:
            y = np.zeros(N, dtype=np.float32)
            
        return X, y

    def _build_avoids(self, df):
        mask = np.ones(len(df), dtype=np.float32)
        # Robust local bool helper
        def get_bool_local(col):
            if col not in df.columns: return np.zeros(len(df), dtype=bool)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_vals = {'TRUE', '1', '1.0', 'YES', 'Y', 'T'}
            return s.isin(true_vals).values

        bad = np.zeros(len(df), dtype=bool)
        bad |= get_bool_local('ema_cmc_flag')
        bad |= get_bool_local('s22_ped_pk_missing')
        bad |= get_bool_local('s23_risk_critical')
        mask[bad] = 0.0
        return mask

    def evaluate_batch(self, configs, use_test_set=False):
        """
        Runs configs on X. Returns Brier, Separation, T1 Count.
        Does NOT look at Test data unless use_test_set=True.
        """
        X = self.X_test if use_test_set else self.X_train
        y = self.y_test if use_test_set else self.y_train
        mask = self.mask_test if use_test_set else self.mask_train
        
        # 1. Score = Config @ X.T
        scores = cp.matmul(configs, X.T)
        scores *= mask # Zero out avoids
        probs = cp.clip(scores, 0.01, 0.99)
        
        # 2. Brier Score (MSE)
        diff = probs - y
        brier = cp.mean(diff ** 2, axis=1)
        
        # 3. Separation (Approx AUC)
        y_sum = cp.sum(y)
        neg_sum = cp.sum(1-y)
        
        # Safe Division
        score_pos = cp.sum(probs * y, axis=1) / cp.maximum(y_sum, 1.0)
        score_neg = cp.sum(probs * (1-y), axis=1) / cp.maximum(neg_sum, 1.0)
        separation = score_pos - score_neg
        
        # 4. Count > Threshold
        t1_count = cp.sum(probs > VALID_SCORE_THRESH, axis=1)
        
        return brier, separation, t1_count

def generate_honest_configs(n):
    """
    Generates random configs respecting Sign and Magnitude constraints.
    """
    mags = cp.random.uniform(PARAM_MINS, PARAM_MAXS, (n, len(PARAM_NAMES))).astype(cp.float32) if GPU_AVAILABLE else np.random.uniform(PARAM_MINS, PARAM_MAXS, (n, len(PARAM_NAMES))).astype(np.float32)
    
    # Apply Signs
    # Where sign is 0, default to positive magnitude (or modify logic if we want free params)
    # Here we treat 0 as 1 for simplicity unless spec changes
    signs = PARAM_SIGNS
    signs = cp.where(signs == 0, 1, signs) if GPU_AVAILABLE else np.where(signs == 0, 1, signs)
    
    configs = mags * signs
    return configs

def main():
    print("[ODIN] Loading Data...")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    engine = OdinIroncladEngine(df)
    
    best_train_brier = 1.0
    best_config_vec = None
    
    print(f"[ODIN] Starting HONEST search ({N_BATCHES} x {BATCH_SIZE})...")
    
    for i in range(N_BATCHES):
        # 1. Generate Valid Configs
        configs = generate_honest_configs(BATCH_SIZE)
        
        # 2. Evaluate on TRAIN ONLY
        brier_train, sep_train, t1_train = engine.evaluate_batch(configs, use_test_set=False)
        
        # 3. Filter (Separation must be positive, some T1s found)
        if GPU_AVAILABLE:
            valid_mask = (t1_train > VALID_COUNT_THRESH) & (sep_train > VALID_SEP_THRESH)
            if not valid_mask.any(): 
                if i == 0:
                    max_t1 = cp.max(t1_train)
                    max_sep = cp.max(sep_train)
                    print(f"   [DEBUG] Batch 0 rejected. Max T1 Count: {max_t1}, Max Sep: {max_sep}")
                continue
            
            # Select Best
            filtered_brier = brier_train[valid_mask]
            best_idx_local = cp.argmin(filtered_brier)
            real_indices = cp.where(valid_mask)[0]
            best_idx = real_indices[best_idx_local]
            
            candidate_vec = configs[best_idx]
            cand_brier = float(brier_train[best_idx])
            cand_sep = float(sep_train[best_idx])
        else:
            valid_mask = (t1_train > VALID_COUNT_THRESH) & (sep_train > VALID_SEP_THRESH)
            if not valid_mask.any(): continue
            filtered_brier = brier_train[valid_mask]
            best_idx_local = np.argmin(filtered_brier)
            real_indices = np.where(valid_mask)[0]
            best_idx = real_indices[best_idx_local]
            candidate_vec = configs[best_idx]
            cand_brier = float(brier_train[best_idx])
            cand_sep = float(sep_train[best_idx])

        # 4. Update Global Best (Based on TRAIN performance)
        if cand_brier < best_train_brier:
            best_train_brier = cand_brier
            best_config_vec = candidate_vec
            
            # 5. TEST CHECK (For logging only - NO LEAKAGE)
            vec_reshaped = candidate_vec.reshape(1, -1)
            brier_test, sep_test, _ = engine.evaluate_batch(vec_reshaped, use_test_set=True)
            
            print(f"Batch {i}: Train Brier={cand_brier:.4f} (Sep={cand_sep:.3f}) | [TEST: Brier={float(brier_test):.4f} Sep={float(sep_test):.3f}]")

    print("\n[ODIN] Optimization Complete.")
    
    if best_config_vec is not None:
        final_dict = {}
        vec_cpu = cp.asnumpy(best_config_vec) if GPU_AVAILABLE else best_config_vec
        for idx, key in enumerate(PARAM_NAMES):
            final_dict[key] = float(vec_cpu[idx])
            
        print(json.dumps(final_dict, indent=2))
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(final_dict, f, indent=2)
        print(f"Saved to {OUTPUT_FILE}")
    else:
        print("Failed to find valid config.")

if __name__ == "__main__":
    main()