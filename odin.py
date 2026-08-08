"""
ODIN v10.6.3 "HONEST" OPTIMIZER
===============================
- FIX: Solved CuPy TypeError (using .item() for logging).
- CORE: Logistic Regression (Sigmoid) Probability Model.
- HONESTY: Strict Time-Series Split (Train on Past, Test on Future).
"""

import numpy as np
import pandas as pd
import time
import json
import warnings
import sys

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
TRAIN_SPLIT_PCT = 0.70  # Strict 70/30 Past/Future split
BATCH_SIZE = 100_000
N_BATCHES = 200         # 20 Million Configs

# --- PARAMETER DEFINITIONS (LOG-ODDS SCALE) ---
# Sign: 1 (Pos), -1 (Neg)
PARAMS_DEF = [
    # Base Rate (Bias Term in Logits)
    ("base_logit", 1, -0.5, 2.0), 
    
    # Penalties (MUST BE NEGATIVE)
    ("snda_base_penalty", -1, 0.1, 0.8),
    ("snda_pediatric_base_penalty", -1, 0.2, 1.0),
    ("prior_crl_penalty", -1, 0.5, 2.0),
    ("inexperienced_sponsor_penalty", -1, 0.3, 1.5),
    ("manufacturing_risk_penalty", -1, 0.3, 1.2),
    ("form_483_penalty", -1, 0.2, 1.0),
    ("ema_cmc_flag_penalty", -1, 0.5, 2.0),
    ("cmc_extension_penalty", -1, 0.2, 1.0),
    ("adcom_mid_penalty", -1, 0.1, 0.8),
    ("adcom_low_penalty", -1, 0.5, 2.0),
    ("s22_pediatric_pk_penalty", -1, 0.3, 1.5),
    
    # Boosts (MUST BE POSITIVE)
    ("btd_weight", 1, 0.1, 0.8),
    ("orphan_weight", 1, 0.1, 0.8),
    ("priority_review_weight", 1, 0.1, 0.8),
    ("fast_track_weight", 1, 0.0, 0.5), 
    ("accelerated_approval_weight", 1, 0.0, 0.5),
    ("class1_resubmission_boost", 1, 0.3, 1.2),
    ("experienced_sponsor_boost", 1, 0.1, 0.6),
    ("adcom_high_boost", 1, 0.3, 1.5),
    
    # Scalars (Multipliers for signals)
    ("ta_adjustment_weight", 1, 0.2, 1.5),
    ("s23_insider_weight", 1, 0.0, 1.5),
    ("s6_hiring_weight", 1, 0.0, 1.5),
    ("social_weight", 1, 0.0, 0.5)
]

PARAM_NAMES = [p[0] for p in PARAMS_DEF]
# Compile Constraints
PARAM_SIGNS = cp.array([p[1] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[1] for p in PARAMS_DEF], dtype=np.float32)
PARAM_MINS = cp.array([p[2] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[2] for p in PARAMS_DEF], dtype=np.float32)
PARAM_MAXS = cp.array([p[3] for p in PARAMS_DEF], dtype=cp.float32) if GPU_AVAILABLE else np.array([p[3] for p in PARAMS_DEF], dtype=np.float32)

class OdinHonestEngine:
    def __init__(self, df):
        # 1. Sort by Date
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)
            print(f"[ODIN] Sorted {len(df)} events by date.")
        else:
            print("[ODIN] WARNING: No date column. Assuming index implies time.")

        # 2. Build Matrix
        self.X, self.y = self._build_matrix(df)
        self.hard_avoid_mask = self._build_avoids(df)
        
        # 3. Time-Series Split
        split_idx = int(len(df) * TRAIN_SPLIT_PCT)
        
        self.X_train = self.X[:split_idx]
        self.y_train = self.y[:split_idx]
        self.mask_train = self.hard_avoid_mask[:split_idx]
        
        self.X_test = self.X[split_idx:]
        self.y_test = self.y[split_idx:]
        self.mask_test = self.hard_avoid_mask[split_idx:]
        
        # Validation Checks
        pos_train = np.sum(self.y_train) if not GPU_AVAILABLE else cp.sum(self.y_train).item()
        pos_test = np.sum(self.y_test) if not GPU_AVAILABLE else cp.sum(self.y_test).item()
        
        print(f"[ODIN] Split: {len(self.y_train)} Train ({int(pos_train)} pos) | {len(self.y_test)} Test ({int(pos_test)} pos)")
        
        if pos_train < 10:
            print("[CRITICAL] Too few positive examples in training set.")
            sys.exit(1)

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
        X[:, 0] = 1.0 
        
        # --- FEATURE EXTRACTORS ---
        def get_bool(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_vals = {'TRUE', '1', '1.0', 'YES', 'Y', 'T', 'APPROVED', 'SUCCESS', 'APPROVAL'}
            return s.isin(true_vals).astype(int).values.astype(np.float32)
            
        def get_val(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app_type_series(df):
            candidates = ['application_type', 'ApplicationType', 'app_type', 'catalyst_type']
            for c in candidates:
                if c in df.columns: return df[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N) 

        # --- FILL MATRIX ---
        app = get_app_type_series(df)
        
        # Penalties
        X[:, 1] = (app.str.contains('SNDA') | app.str.contains('SBLA')).astype(float)
        X[:, 2] = (app.str.contains('PEDIATRIC')).astype(float)
        X[:, 3] = get_bool('prior_crl')
        prior = get_val('sponsor_prior_approvals')
        X[:, 4] = (prior == 0).astype(float)
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

        # Boosts
        X[:, 12] = get_bool('btd')
        X[:, 13] = get_bool('orphan')
        X[:, 14] = get_bool('priority_review')
        X[:, 15] = get_bool('fast_track')
        X[:, 16] = get_bool('accelerated_approval')
        
        if 'resubmission_class' in df: X[:, 17] = (get_val('resubmission_class') == 1).astype(float)
        X[:, 18] = (prior >= 5).astype(float) 
        X[:, 19] = had_adcom * (vote >= 0.65) 
        
        # Scalars
        X[:, 20] = get_val('ta_base_score')
        X[:, 21] = get_val('s23_signal_strength')
        X[:, 22] = get_val('s6_signal_strength')
        X[:, 23] = get_val('social_sentiment_score')

        # --- FORENSIC TARGET PARSING ---
        y_col = None
        for c in ['outcome', 'Outcome', 'approved', 'Approved', 'label', 'result', 'y', 'Y']:
            if c in df.columns: 
                y_col = c
                break
        
        if y_col is None:
            print("[CRITICAL] Could not find outcome column.")
            sys.exit(1)
            
        y_raw = df[y_col].astype(str).str.strip().str.upper()
        y_raw = y_raw.str.replace(r'\.0$', '', regex=True)
        
        positives = {'APPROVED', 'APPROVAL', '1', 'TRUE', 'YES', 'SUCCESS', 'PASS', 'POSITIVE'}
        y = y_raw.isin(positives).astype(float).values
        
        if np.sum(y) == 0:
            print("[CRITICAL] Still found 0 positive labels.")
            sys.exit(1)
            
        return X, y

    def _build_avoids(self, df):
        mask = np.ones(len(df), dtype=np.float32)
        bad = np.zeros(len(df), dtype=bool)
        
        if 'ema_cmc_flag' in df.columns: bad |= df['ema_cmc_flag'].fillna(False).astype(bool)
        if 's22_ped_pk_missing' in df.columns: bad |= df['s22_ped_pk_missing'].fillna(False).astype(bool)
        if 's23_risk_critical' in df.columns: bad |= df['s23_risk_critical'].fillna(False).astype(bool)
            
        mask[bad] = 0.0
        return mask

    def evaluate_batch(self, configs, use_test_set=False):
        """
        LOGISTIC EVALUATION
        Prob = 1 / (1 + exp(-Logits))
        """
        X = self.X_test if use_test_set else self.X_train
        y = self.y_test if use_test_set else self.y_train
        mask = self.mask_test if use_test_set else self.mask_train
        
        # 1. Logits = Config @ X.T
        logits = cp.matmul(configs, X.T)
        
        # 2. Sigmoid (Logistic Transform)
        # Prob = 1 / (1 + e^-z)
        probs = 1.0 / (1.0 + cp.exp(-logits))
        
        # Apply Hard Avoids
        probs *= mask
        
        # 3. Brier Score
        diff = probs - y
        brier = cp.mean(diff ** 2, axis=1)
        
        # 4. AUC Proxy (Separation)
        y_sum = cp.sum(y)
        neg_sum = cp.sum(1-y)
        
        score_pos = cp.sum(probs * y, axis=1) / cp.maximum(y_sum, 1.0)
        score_neg = cp.sum(probs * (1-y), axis=1) / cp.maximum(neg_sum, 1.0)
        separation = score_pos - score_neg
        
        # 5. T1 Count (Prob > 0.85)
        t1_count = cp.sum(probs > 0.85, axis=1)
        
        return brier, separation, t1_count

def generate_honest_configs(n):
    mags = cp.random.uniform(PARAM_MINS, PARAM_MAXS, (n, len(PARAM_NAMES))).astype(cp.float32) if GPU_AVAILABLE else np.random.uniform(PARAM_MINS, PARAM_MAXS, (n, len(PARAM_NAMES))).astype(np.float32)
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

    engine = OdinHonestEngine(df)
    
    best_train_brier = 1.0
    best_config_vec = None
    
    print(f"[ODIN] Starting HONEST search ({N_BATCHES} x {BATCH_SIZE})...")
    
    for i in range(N_BATCHES):
        configs = generate_honest_configs(BATCH_SIZE)
        
        # EVALUATE ON TRAIN
        brier_train, sep_train, t1_train = engine.evaluate_batch(configs, use_test_set=False)
        
        # FILTER (Honest Criteria)
        if GPU_AVAILABLE:
            valid_mask = (sep_train > 0.05) & (t1_train > 0)
            
            if not valid_mask.any(): continue
            
            # Pick best Brier among valid
            filtered_brier = brier_train[valid_mask]
            best_idx_local = cp.argmin(filtered_brier)
            real_indices = cp.where(valid_mask)[0]
            best_idx = real_indices[best_idx_local]
            
            candidate_vec = configs[best_idx]
            cand_brier = float(brier_train[best_idx])
            cand_sep = float(sep_train[best_idx])
        else:
            valid_mask = (sep_train > 0.05) & (t1_train > 0)
            if not valid_mask.any(): continue
            filtered_brier = brier_train[valid_mask]
            best_idx_local = np.argmin(filtered_brier)
            real_indices = np.where(valid_mask)[0]
            best_idx = real_indices[best_idx_local]
            candidate_vec = configs[best_idx]
            cand_brier = float(brier_train[best_idx])
            cand_sep = float(sep_train[best_idx])

        # UPDATE GLOBAL BEST (Based on TRAIN)
        if cand_brier < best_train_brier:
            best_train_brier = cand_brier
            best_config_vec = candidate_vec
            
            # LOG TEST PERFORMANCE (No Leakage, just reporting)
            vec_reshaped = candidate_vec.reshape(1, -1)
            brier_test, sep_test, _ = engine.evaluate_batch(vec_reshaped, use_test_set=True)
            
            # SAFE LOGGING (Fix for TypeError)
            test_b = float(brier_test.item()) if GPU_AVAILABLE else float(brier_test)
            test_s = float(sep_test.item()) if GPU_AVAILABLE else float(sep_test)
            
            print(f"Batch {i}: Train Brier={cand_brier:.4f} (Sep={cand_sep:.3f}) | [TEST: Brier={test_b:.4f} Sep={test_s:.3f}]")

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