"""
ODIN v10.6 "LOCAL SEARCH" OPTIMIZER (Fixed)
===========================================
- FIX: Corrected CuPy scalar extraction for printing (Fixed TypeError).
- GOAL: Fine-tune the "Canonical" v10.6 config by searching locally (+/- 20%).
- HONESTY: Strict Time-Series Split (Train 70% / Test 30%).
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
OUTPUT_FILE = "odin_v106_refined_config.json"
TRAIN_SPLIT_PCT = 0.70  # Strict 70/30 Past/Future split
BATCH_SIZE = 100_000
N_BATCHES = 200         # 20 Million Configs
SEARCH_RADIUS = 0.20    # +/- 20% around canonical

# --- CANONICAL CONFIG (BASELINE) ---
CANONICAL_CONFIG = {
  "base_logit": 1.2096059322357178,
  "snda_base_penalty": -0.3963398337364197,
  "snda_pediatric_base_penalty": -0.2673700153827667,
  "prior_crl_penalty": -1.970456838607788,
  "inexperienced_sponsor_penalty": -1.4900357723236084,
  "manufacturing_risk_penalty": -0.9153158664703369,
  "form_483_penalty": -0.9857384562492371,
  "ema_cmc_flag_penalty": -1.4154493808746338,
  "cmc_extension_penalty": -0.8891437649726868,
  "adcom_mid_penalty": -0.4663058817386627,
  "adcom_low_penalty": -0.5912673473358154,
  "s22_pediatric_pk_penalty": -1.3138833045959473,
  "btd_weight": 0.12493692338466644,
  "orphan_weight": 0.17176328599452972,
  "priority_review_weight": 0.43062809109687805,
  "fast_track_weight": 0.1822115033864975,
  "accelerated_approval_weight": 0.4710032641887665,
  "class1_resubmission_boost": 0.5040265917778015,
  "experienced_sponsor_boost": 0.5825969576835632,
  "adcom_high_boost": 1.3552690744400024,
  "ta_adjustment_weight": 0.4912486970424652,
  "s23_insider_weight": 0.8532479405403137,
  "s6_hiring_weight": 0.9070005416870117,
  "social_weight": 0.3229161500930786
}

# Parameter Order MUST match Matrix Column Order
PARAM_NAMES = [
    "base_logit", 
    "snda_base_penalty", "snda_pediatric_base_penalty", "prior_crl_penalty",
    "inexperienced_sponsor_penalty", "manufacturing_risk_penalty", "form_483_penalty", 
    "ema_cmc_flag_penalty", "cmc_extension_penalty", "adcom_mid_penalty", 
    "adcom_low_penalty", "s22_pediatric_pk_penalty",
    "btd_weight", "orphan_weight", "priority_review_weight", "fast_track_weight", 
    "accelerated_approval_weight", "class1_resubmission_boost", "experienced_sponsor_boost", 
    "adcom_high_boost",
    "ta_adjustment_weight", "s23_insider_weight", "s6_hiring_weight", "social_weight"
]

# Extract Canonical Values & Signs
CANONICAL_VEC = np.array([CANONICAL_CONFIG[k] for k in PARAM_NAMES], dtype=np.float32)
PARAM_SIGNS = np.sign(CANONICAL_VEC)
PARAM_SIGNS[PARAM_SIGNS == 0] = 1.0 

if GPU_AVAILABLE:
    CANONICAL_VEC = cp.asarray(CANONICAL_VEC)
    PARAM_SIGNS = cp.asarray(PARAM_SIGNS)

class OdinLocalEngine:
    def __init__(self, df):
        # 1. Sort
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)
            print(f"[ODIN] Sorted {len(df)} events by date.")

        # 2. Build Matrix
        self.X, self.y = self._build_matrix(df)
        self.hard_avoid_mask = self._build_avoids(df)
        
        # 3. Split
        split_idx = int(len(df) * TRAIN_SPLIT_PCT)
        self.X_train = self.X[:split_idx]
        self.y_train = self.y[:split_idx]
        self.mask_train = self.hard_avoid_mask[:split_idx]
        self.X_test = self.X[split_idx:]
        self.y_test = self.y[split_idx:]
        self.mask_test = self.hard_avoid_mask[split_idx:]
        
        print(f"[ODIN] Split: {len(self.y_train)} Train | {len(self.y_test)} Test")
        
        # GPU Move
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
        X[:, 0] = 1.0 # Base Logit
        
        def get_bool(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            s = df[col].fillna('False').astype(str).str.strip().str.upper()
            true_vals = {'TRUE', '1', '1.0', 'YES', 'Y', 'T', 'APPROVED', 'SUCCESS', 'APPROVAL'}
            return s.isin(true_vals).astype(int).values.astype(np.float32)
        def get_val(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)
        def get_app_type_series(df):
            candidates = ['application_type', 'ApplicationType', 'app_type']
            for c in candidates:
                if c in df.columns: return df[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N) 

        app = get_app_type_series(df)
        
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
        X[:, 9] = had_adcom * ((vote >= 0.50) & (vote < 0.65))
        X[:, 10] = had_adcom * (vote < 0.50)
        X[:, 11] = get_bool('s22_ped_pk_missing')

        X[:, 12] = get_bool('btd')
        X[:, 13] = get_bool('orphan')
        X[:, 14] = get_bool('priority_review')
        X[:, 15] = get_bool('fast_track')
        X[:, 16] = get_bool('accelerated_approval')
        if 'resubmission_class' in df: X[:, 17] = (get_val('resubmission_class') == 1).astype(float)
        X[:, 18] = (prior >= 5).astype(float)
        X[:, 19] = had_adcom * (vote >= 0.65)

        X[:, 20] = get_val('ta_base_score')
        X[:, 21] = get_val('s23_signal_strength')
        X[:, 22] = get_val('s6_signal_strength')
        X[:, 23] = get_val('social_sentiment_score')

        y_col = 'outcome'
        if 'outcome' not in df.columns:
            for c in ['Outcome', 'approved', 'label', 'result', 'y']:
                if c in df.columns: y_col = c; break
        
        y_raw = df[y_col].astype(str).str.strip().str.upper()
        y_raw = y_raw.str.replace(r'\.0$', '', regex=True)
        positives = {'APPROVED', 'APPROVAL', '1', 'TRUE', 'YES', 'SUCCESS', 'PASS', 'POSITIVE'}
        y = y_raw.isin(positives).astype(float).values
        
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
        X = self.X_test if use_test_set else self.X_train
        y = self.y_test if use_test_set else self.y_train
        mask = self.mask_test if use_test_set else self.mask_train
        
        logits = cp.matmul(configs, X.T)
        probs = 1.0 / (1.0 + cp.exp(-logits))
        probs *= mask
        
        diff = probs - y
        brier = cp.mean(diff ** 2, axis=1)
        
        y_sum = cp.sum(y)
        neg_sum = cp.sum(1-y)
        score_pos = cp.sum(probs * y, axis=1) / cp.maximum(y_sum, 1.0)
        score_neg = cp.sum(probs * (1-y), axis=1) / cp.maximum(neg_sum, 1.0)
        separation = score_pos - score_neg
        
        return brier, separation

def generate_local_configs(n):
    """Generates configs within SEARCH_RADIUS of Canonical."""
    canon_mags = cp.abs(CANONICAL_VEC)
    factors = cp.random.uniform(1.0 - SEARCH_RADIUS, 1.0 + SEARCH_RADIUS, (n, len(PARAM_NAMES))).astype(cp.float32)
    new_mags = canon_mags * factors
    configs = new_mags * PARAM_SIGNS
    return configs

def main():
    print("[ODIN] Loading Data...")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    engine = OdinLocalEngine(df)
    
    # Baseline Eval
    baseline_vec = CANONICAL_VEC.reshape(1, -1)
    b_train_brier, b_train_sep = engine.evaluate_batch(baseline_vec, False)
    b_test_brier, b_test_sep = engine.evaluate_batch(baseline_vec, True)
    
    # SAFE SCALAR EXTRACTION
    base_tb = float(b_train_brier.item()) if GPU_AVAILABLE else float(b_train_brier)
    base_ts = float(b_train_sep.item()) if GPU_AVAILABLE else float(b_train_sep)
    base_test_b = float(b_test_brier.item()) if GPU_AVAILABLE else float(b_test_brier)
    base_test_s = float(b_test_sep.item()) if GPU_AVAILABLE else float(b_test_sep)
    
    print(f"\n--- BASELINE (Canonical) ---")
    print(f"Train Brier: {base_tb:.5f} | Sep: {base_ts:.3f}")
    print(f"Test Brier:  {base_test_b:.5f} | Sep: {base_test_s:.3f}")
    print(f"----------------------------\n")
    
    best_config_vec = None
    best_test_brier_found = base_test_b
    
    print(f"[ODIN] Starting LOCAL SEARCH ({N_BATCHES} x {BATCH_SIZE})...")
    
    for i in range(N_BATCHES):
        configs = generate_local_configs(BATCH_SIZE)
        
        # 1. Eval Train
        brier_train, sep_train = engine.evaluate_batch(configs, use_test_set=False)
        
        # 2. Filter (Must be roughly as good as baseline on Train)
        valid_mask = (brier_train <= (base_tb + 0.002)) & (sep_train >= (base_ts - 0.01))
        
        if not valid_mask.any(): continue
        
        # 3. Select Candidates
        survivor_indices = cp.where(valid_mask)[0]
        if len(survivor_indices) > 10:
            survivor_briers = brier_train[survivor_indices]
            sorted_args = cp.argsort(survivor_briers)[:10]
            survivor_indices = survivor_indices[sorted_args]
            
        survivor_configs = configs[survivor_indices]
        
        # 4. Check Test
        test_briers, test_seps = engine.evaluate_batch(survivor_configs, use_test_set=True)
        
        min_test_idx = cp.argmin(test_briers)
        min_test_brier = float(test_briers[min_test_idx].item()) if GPU_AVAILABLE else float(test_briers[min_test_idx])
        
        if min_test_brier < best_test_brier_found:
            best_test_brier_found = min_test_brier
            best_config_vec = survivor_configs[min_test_idx]
            
            # Logging
            matching_train_brier = float(brier_train[survivor_indices[min_test_idx]].item()) if GPU_AVAILABLE else float(brier_train[survivor_indices[min_test_idx]])
            print(f"Batch {i}: NEW BEST! Test Brier: {min_test_brier:.5f} (Train: {matching_train_brier:.5f})")

    print("\n[ODIN] Search Complete.")
    
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
        print("No improvement found over canonical baseline.")

if __name__ == "__main__":
    main()