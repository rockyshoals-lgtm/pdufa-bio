import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Try to import CuPy for GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    import numpy as cp
    GPU_AVAILABLE = False
    print("Warning: CuPy not found. Running on CPU (slower).")

# ==========================================
# 1. CONFIGURATION SPACE DEFINITION
# ==========================================
# These keys map directly to the vector indices for optimization
PARAM_KEYS = [
    # Base Rates
    "base_approval_rate",           # 0
    "snda_base_penalty",            # 1
    "snda_pediatric_base_penalty",  # 2
    # Designations
    "btd_weight",                   # 3
    "orphan_weight",                # 4
    "priority_review_weight",       # 5
    "fast_track_weight",            # 6
    "accelerated_approval_weight",  # 7
    # AdCom
    "adcom_high_boost",             # 8
    "adcom_mid_penalty",            # 9
    "adcom_low_penalty",            # 10
    # CRL / Sponsor
    "prior_crl_penalty",            # 11
    "class1_resubmission_boost",    # 12
    "experienced_sponsor_boost",    # 13
    "inexperienced_sponsor_penalty",# 14
    # CMC (S12)
    "manufacturing_risk_penalty",   # 15
    "form_483_penalty",             # 16
    "ema_cmc_flag_penalty",         # 17
    "cmc_extension_penalty",        # 18
    # TA Adjustment Scalar
    "ta_adjustment_weight",         # 19
    # New v10.4 Signals
    "s23_insider_weight",           # 20
    "s6_hiring_weight",             # 21
    "s22_pediatric_pk_penalty",     # 22
    # Social
    "social_weight"                 # 23
]

# Constraints: 1 = Boost (>=0), -1 = Penalty (<=0), 0 = Free
PARAM_CONSTRAINTS = np.array([
    1, -1, -1,  # Base, SNDA, Ped
    1, 1, 1, 1, 1, # Designations
    1, -1, -1, # AdCom
    -1, 1, 1, -1, # CRL/Sponsor
    -1, -1, -1, -1, # CMC
    1, # TA scalar (usually positive scalar on the lookup table)
    1, 1, -1, # Insider/Hiring weights (apply to signal score), PedPK penalty
    1 # Social
], dtype=np.float32)

class OdinVectorizedEvaluator:
    def __init__(self, events_df: pd.DataFrame):
        """
        Prepares the Feature Matrix X from the raw dataframe.
        """
        self.events_df = events_df
        self.X, self.y = self._build_feature_matrix(events_df)
        self.hard_avoid_mask = self._build_hard_avoids(events_df)
        
        # Move to GPU if available
        if GPU_AVAILABLE:
            self.X = cp.asarray(self.X)
            self.y = cp.asarray(self.y)
            self.hard_avoid_mask = cp.asarray(self.hard_avoid_mask)

    def _build_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Constructs the (N_events, N_params) matrix X.
        Each column corresponds exactly to PARAM_KEYS.
        """
        N = len(df)
        X = np.zeros((N, len(PARAM_KEYS)), dtype=np.float32)
        
        # Helper for bool columns
        def get_bool(col):
            # Check if column exists, else return 0
            if col not in df.columns:
                return np.zeros(N, dtype=np.float32)
            # Handle string 'TRUE'/'FALSE', booleans, and 0/1 integers
            return df[col].fillna(False).astype(str).str.upper().isin(['TRUE', '1', 'YES']).astype(float).values

        # 0. Base Rate (Bias term)
        X[:, 0] = 1.0 
        
        # 1. App Type Penalties
        # FIXED: Force string conversion to avoid AttributeErrors on numbers
        if 'application_type' in df.columns:
            app_type = df['application_type'].fillna('').astype(str).str.upper()
            X[:, 1] = (app_type.str.contains('SNDA') | app_type.str.contains('SBLA')).astype(float)
            X[:, 2] = (app_type.str.contains('PEDIATRIC')).astype(float)
        else:
            X[:, 1] = 0.0
            X[:, 2] = 0.0

        # 2. Designations (S1-S5)
        X[:, 3] = get_bool('btd')
        X[:, 4] = get_bool('orphan')
        X[:, 5] = get_bool('priority_review')
        X[:, 6] = get_bool('fast_track')
        X[:, 7] = get_bool('accelerated_approval')

        # 3. AdCom
        had_adcom = get_bool('had_adcom')
        if 'adcom_vote_pct' in df.columns:
            vote = df['adcom_vote_pct'].fillna(0).astype(float).values
            # Normalize vote if > 1
            vote = np.where(vote > 1.0, vote / 100.0, vote)
            
            X[:, 8] = had_adcom * (vote >= 0.65) # High
            X[:, 9] = had_adcom * ((vote >= 0.50) & (vote < 0.65)) # Mid
            X[:, 10] = had_adcom * (vote < 0.50) # Low
        else:
            X[:, 8:11] = 0.0

        # 4. Prior CRL / Sponsor
        X[:, 11] = get_bool('prior_crl') # Penalty
        
        # Class 1 resub logic (often stored as resubmission_class == 1)
        if 'resubmission_class' in df.columns:
            resub = df['resubmission_class'].fillna(0).astype(float).values
            X[:, 12] = (resub == 1).astype(float)
        else:
            X[:, 12] = 0.0
        
        if 'sponsor_prior_approvals' in df.columns:
            prior_apps = df['sponsor_prior_approvals'].fillna(0).astype(float).values
            X[:, 13] = (prior_apps >= 5).astype(float) # Exp Boost
            X[:, 14] = (prior_apps == 0).astype(float) # Inexp Penalty
        else:
            X[:, 13:15] = 0.0

        # 5. CMC (S12)
        X[:, 15] = get_bool('manufacturing_risk')
        X[:, 16] = get_bool('form_483_issues')
        X[:, 17] = get_bool('ema_cmc_flag')
        X[:, 18] = get_bool('cmc_extension_flag')

        # 6. TA Adjustment (S16)
        # We assume 'ta_base_score' is pre-calculated in DF based on the lookup table
        if 'ta_base_score' in df.columns:
            X[:, 19] = df['ta_base_score'].fillna(0).astype(float).values
        else:
            X[:, 19] = 0.0 

        # 7. New Signals (S23, S6, S22)
        X[:, 20] = df.get('s23_signal_strength', pd.Series(0, index=df.index)).fillna(0).values
        X[:, 21] = df.get('s6_signal_strength', pd.Series(0, index=df.index)).fillna(0).values
        X[:, 22] = get_bool('s22_ped_pk_missing') 

        # 8. Social
        X[:, 23] = df.get('social_sentiment_score', pd.Series(0, index=df.index)).fillna(0).values

        # Labels - Try multiple column names for target
        target_col = None
        for col in ['outcome', 'approved', 'outcome_bin', 'y']:
            if col in df.columns:
                target_col = col
                break
        
        if target_col:
            # Clean outcome to 0/1
            # Assuming 'Approved' = 1, else 0, or already 0/1
            y_raw = df[target_col].astype(str).str.upper()
            # Common positive labels
            positives = ['1', '1.0', 'TRUE', 'APPROVED', 'YES']
            y = y_raw.isin(positives).astype(float).values
        else:
            print("Warning: No outcome column found. Setting y to zeros.")
            y = np.zeros(N, dtype=np.float32)
        
        return X, y

    def _build_hard_avoids(self, df: pd.DataFrame) -> np.ndarray:
        """
        Creates a mask (1=Keep, 0=Avoid) for Hard Avoid logic (S22, S12, S23).
        """
        mask = np.ones(len(df), dtype=np.float32)
        
        def get_bool_series(col):
            if col not in df.columns: return pd.Series(False, index=df.index)
            return df[col].fillna(False).astype(str).str.upper().isin(['TRUE', '1', 'YES'])

        # Hard Avoid Logic from v10.4 Spec
        ema_flag = get_bool_series('ema_cmc_flag')
        ped_pk = get_bool_series('s22_ped_pk_missing')
        
        # Insider Critical is tricky if not pre-calculated
        # We look for a flag or signal strength < some threshold
        insider_crit = get_bool_series('s23_risk_critical') 
        
        avoid_idx = ema_flag | ped_pk | insider_crit
        mask[avoid_idx] = 0.0
        return mask

    def evaluate_batch(self, configs: np.ndarray, t1_band_min=1200, fp_penalty=2.0):
        """
        Evaluates a batch of configuration vectors.
        configs: (Batch_Size, N_Params + 3) -> Last 3 cols are T1/T2/T3 cuts
        """
        # Separate Weights (W) and Thresholds (T)
        W = configs[:, :len(PARAM_KEYS)]
        thresholds = configs[:, len(PARAM_KEYS):] # [T1, T2, T3]
        
        # 1. Compute Raw Scores (Batch x Events)
        # W (B, P) @ X.T (P, N) -> (B, N)
        raw_scores = cp.matmul(W, self.X.T)
        
        # 2. Apply Hard Avoids
        # Zero out scores for hard-avoid events
        scores = raw_scores * self.hard_avoid_mask
        
        # 3. Clamp
        probs = cp.clip(scores, 0.01, 0.99)
        
        # 4. Metrics
        # Brier Score (MSE)
        diff = probs - self.y
        brier = cp.mean(diff ** 2, axis=1)
        
        # Tier 1 Analysis
        t1_cuts = thresholds[:, 0][:, None] # Broadcast to (B, 1)
        is_t1 = probs >= t1_cuts
        
        t1_n = cp.sum(is_t1, axis=1)
        t1_tp = cp.sum(is_t1 & (self.y == 1), axis=1)
        t1_fp = cp.sum(is_t1 & (self.y == 0), axis=1)
        
        # Hit Rate
        t1_hit_rate = t1_tp / cp.maximum(t1_n, 1.0)
        
        # Scalar Objective
        # Reward TP, Penalize FP heavily
        objective = t1_tp - (fp_penalty * t1_fp)
        
        # Coverage Constraint Penalty
        # If t1_n < min, apply huge penalty
        coverage_penalty = cp.where(t1_n < t1_band_min, -1000.0, 0.0)
        
        final_score = objective + coverage_penalty
        
        return {
            "score": final_score,
            "brier": brier,
            "t1_hit_rate": t1_hit_rate,
            "t1_n": t1_n
        }

# Utility functions for Config <-> Vector
def config_to_vector(config_dict: Dict) -> np.ndarray:
    vec = []
    for k in PARAM_KEYS:
        vec.append(config_dict.get(k, 0.0))
    # Append thresholds
    vec.append(config_dict.get('tier1_threshold', 0.85))
    vec.append(config_dict.get('tier2_threshold', 0.75))
    vec.append(config_dict.get('tier3_threshold', 0.65))
    return np.array(vec, dtype=np.float32)

def vector_to_config(vec: np.ndarray) -> Dict:
    cfg = {}
    for i, k in enumerate(PARAM_KEYS):
        cfg[k] = float(vec[i])
    cfg['tier1_threshold'] = float(vec[-3])
    cfg['tier2_threshold'] = float(vec[-2])
    cfg['tier3_threshold'] = float(vec[-1])
    return cfg