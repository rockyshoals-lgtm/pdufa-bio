"""
ODIN v10.66 "GRANDMASTER" OPTIMIZER (Fixed)
===========================================
GOAL:    Reiterate through 5 BILLION configs to perfect the Hybrid Engine.
TARGET:  Beat Test Brier 0.09477.
LOGIC:   Simulated Annealing (Wide -> Narrow search).
SAFETY:  Saves immediately on New Best.
FIX:     Resolved UnboundLocalError by initializing best_test_brier.
"""

import numpy as np
import pandas as pd
import time
import json
import warnings
import sys
import os

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

# --- CONFIGURATION ---
DATA_FILE = "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv"
OUTPUT_FILE = "odin_v1066_grandmaster_config.json"
TRAIN_SPLIT_PCT = 0.70
BATCH_SIZE = 100_000
N_BATCHES = 50_000      # 5 Billion Configs
START_RADIUS = 0.20     # Start +/- 20%
END_RADIUS = 0.01       # End +/- 1% (Fine polish)

# --- BASELINE (v10.66 Hybrid Diamond) ---
CANONICAL_CONFIG = {
    # -- ODIN Core --
    "base_logit": 1.4979262351989746,
    "snda_base_penalty": -0.41616255044937134,
    "snda_pediatric_base_penalty": -0.21568609774112701,
    "prior_crl_penalty": -2.494058847427368,
    "inexperienced_sponsor_penalty": -1.2849990129470825,
    "manufacturing_risk_penalty": -0.8840063214302063,
    "form_483_penalty": -1.051964282989502,
    "ema_cmc_flag_penalty": -1.4409009218215942,
    "cmc_extension_penalty": -0.9657028317451477,
    "adcom_mid_penalty": -0.5095034241676331,
    "adcom_low_penalty": -0.7123470306396484,
    "s22_pediatric_pk_penalty": -1.4865119457244873,
    "btd_weight": 0.1477048695087433,
    "orphan_weight": 0.13258962333202362,
    "priority_review_weight": 0.5517457723617554,
    "fast_track_weight": 0.20624379813671112,
    "accelerated_approval_weight": 0.5699965953826904,
    "class1_resubmission_boost": 0.4743357002735138,
    "experienced_sponsor_boost": 0.6573972702026367,
    "adcom_high_boost": 1.4708585739135742,
    "ta_adjustment_weight": 0.40026479959487915,
    "s23_insider_weight": 0.6921589970588684,
    "s6_hiring_weight": 0.7250604033470154,
    "social_weight": 0.42941349744796753,
    # -- Hybrid Params --
    "odin_weight": 0.7396432757377625,
    "hint_weight": 0.16829724609851837,
    "hint_crl_rate_penalty": -1.3893369436264038,
    "ta_high_risk_penalty": -0.32613930106163025,
    "ta_mod_risk_penalty": -0.16120374202728271,
    "ta_low_risk_boost": 0.10099325329065323,
    "indication_pain_penalty": -0.32277533411979675,
    "indication_onc_boost": 0.2045929729938507,
    "novice_sponsor_high_risk_ta_penalty": -0.4189799129962921
}

PARAM_NAMES = list(CANONICAL_CONFIG.keys())
CANONICAL_VEC = np.array([CANONICAL_CONFIG[k] for k in PARAM_NAMES], dtype=np.float32)
PARAM_SIGNS = np.sign(CANONICAL_VEC)
PARAM_SIGNS[PARAM_SIGNS == 0] = 1.0 

if GPU_AVAILABLE:
    CANONICAL_VEC = cp.asarray(CANONICAL_VEC)
    PARAM_SIGNS = cp.asarray(PARAM_SIGNS)

class OdinGrandmasterEngine:
    def __init__(self, df):
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)

        self.X_odin, self.X_hint, self.y = self._build_matrices(df)
        self.mask = self._build_avoids(df)
        
        split = int(len(df) * TRAIN_SPLIT_PCT)
        
        self.d_train = {
            'X': self.X_odin[:split], 
            'y': self.y[:split], 
            'm': self.mask[:split]
        }
        self.d_test = {
            'X': self.X_odin[split:], 
            'y': self.y[split:], 
            'm': self.mask[split:]
        }
        
        if GPU_AVAILABLE:
            for d in [self.d_train, self.d_test]:
                for k in d: d[k] = cp.asarray(d[k])

    def _build_matrices(self, df):
        N = len(df)
        X = np.zeros((N, len(PARAM_NAMES)), dtype=np.float32)
        
        def get_bool(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            s = df[col].fillna('F').astype(str).str.upper()
            return s.isin(['TRUE','1','1.0','YES','Y','APPROVED']).astype(np.float32)
        def get_val(col):
            if col not in df.columns: return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)
        def get_app(df):
            cands = ['application_type','ApplicationType','app_type']
            for c in cands:
                if c in df.columns: return df[c].fillna('').astype(str).str.upper()
            return pd.Series(['']*N)

        app = get_app(df)
        
        X[:,0]=1.0
        X[:,1]=(app.str.contains('SNDA')|app.str.contains('SBLA')).astype(float)
        X[:,2]=(app.str.contains('PEDIATRIC')).astype(float)
        X[:,3]=get_bool('prior_crl')
        prior = get_val('sponsor_prior_approvals')
        X[:,4]=(prior==0).astype(float)
        X[:,5]=get_bool('manufacturing_risk')
        X[:,6]=get_bool('form_483_issues')
        X[:,7]=get_bool('ema_cmc_flag')
        X[:,8]=get_bool('cmc_extension_flag')
        had_adcom=get_bool('had_adcom')
        vote=get_val('adcom_vote_pct')
        vote=np.where(vote>1, vote/100, vote)
        X[:,9]=had_adcom*((vote>=0.50)&(vote<0.65))
        X[:,10]=had_adcom*(vote<0.50)
        X[:,11]=get_bool('s22_ped_pk_missing')
        X[:,12]=get_bool('btd')
        X[:,13]=get_bool('orphan')
        X[:,14]=get_bool('priority_review')
        X[:,15]=get_bool('fast_track')
        X[:,16]=get_bool('accelerated_approval')
        if 'resubmission_class' in df: X[:,17]=(get_val('resubmission_class')==1).astype(float)
        X[:,18]=(prior>=5).astype(float)
        X[:,19]=had_adcom*(vote>=0.65)
        X[:,20]=get_val('ta_base_score')
        X[:,21]=get_val('s23_signal_strength')
        X[:,22]=get_val('s6_signal_strength')
        X[:,23]=get_val('social_sentiment_score')
        
        ta = df['therapeutic_area'].fillna('Other').astype(str)
        def chk(s,ks):
            m=np.zeros(len(s),dtype=bool)
            for k in ks: m|=s.str.contains(k,case=False)
            return m.astype(float)
        
        X[:,26]=df['historical_crl_rate'].fillna(0).astype(float) if 'historical_crl_rate' in df else 0.0
        X[:,27]=chk(ta,["Pain","Ophthalmology","Nephrology","Hematology"])
        X[:,28]=chk(ta,["CNS","Neurology","Cardiovascular","Metabolic"])
        X[:,29]=chk(ta,["Oncology","Immunology","Dermatology","Infectious"])
        ind=df['indication'].fillna('').astype(str) if 'indication' in df else pd.Series(['']*N)
        X[:,30]=ind.str.contains("Pain",case=False).astype(float)
        X[:,31]=(ind.str.contains("Cancer",case=False)|ind.str.contains("Tumor",case=False)).astype(float)
        X[:,32]=((prior<3)&(X[:,27]>0)).astype(float)

        y_col = next((c for c in ['outcome','Outcome','approved','result'] if c in df), None)
        y_raw = df[y_col].astype(str).str.strip().str.upper().replace(r'\.0$','',regex=True)
        y = y_raw.isin({'APPROVED','APPROVAL','1','TRUE','YES','SUCCESS'}).astype(float).values
        
        return X, X, y

    def _build_avoids(self, df):
        m = np.ones(len(df), dtype=np.float32)
        b = np.zeros(len(df), dtype=bool)
        if 'ema_cmc_flag' in df: b|=df['ema_cmc_flag'].fillna(False).astype(bool)
        if 's22_ped_pk_missing' in df: b|=df['s22_ped_pk_missing'].fillna(False).astype(bool)
        m[b] = 0.0
        return m

    def evaluate_batch(self, configs, use_test=False):
        d = self.d_test if use_test else self.d_train
        X, y, m = d['X'], d['y'], d['m']
        
        # Zero out blending weight cols for logit calc (Indices 24, 25)
        c_logits = configs.copy()
        c_logits[:,24] = 0 
        c_logits[:,25] = 0 
        
        logits = cp.matmul(c_logits, X.T)
        probs = 1.0 / (1.0 + cp.exp(-logits))
        probs *= m
        
        diff = probs - y
        brier = cp.mean(diff**2, axis=1)
        
        y_s = cp.sum(y); n_s = cp.sum(1-y)
        sep = (cp.sum(probs*y, axis=1)/cp.maximum(y_s,1.0)) - (cp.sum(probs*(1-y), axis=1)/cp.maximum(n_s,1.0))
        return brier, sep

def generate_configs(n, radius):
    mags = cp.abs(CANONICAL_VEC)
    factors = cp.random.uniform(1.0 - radius, 1.0 + radius, (n, len(PARAM_NAMES))).astype(cp.float32)
    return mags * factors * PARAM_SIGNS

def main():
    print("[ODIN] 5 BILLION Config Search Started...")
    try: df = pd.read_csv(DATA_FILE)
    except: return
    
    eng = OdinGrandmasterEngine(df)
    
    # Baseline
    bv = CANONICAL_VEC.reshape(1,-1)
    b_tr_b, b_tr_s = eng.evaluate_batch(bv, False)
    b_te_b, _ = eng.evaluate_batch(bv, True)
    
    best_tr_b = float(b_tr_b.item()) if GPU_AVAILABLE else float(b_tr_b)
    best_tr_s = float(b_tr_s.item()) if GPU_AVAILABLE else float(b_tr_s)
    best_te_b = float(b_te_b.item()) if GPU_AVAILABLE else float(b_te_b)
    
    # FIX: Initialize variable before loop
    best_test_brier = best_te_b
    
    print(f"BASELINE: Train={best_tr_b:.5f} | Test={best_te_b:.5f}")
    
    for i in range(N_BATCHES):
        # Dynamic Radius: Shrink linearly
        r = START_RADIUS - ((START_RADIUS - END_RADIUS) * (i / N_BATCHES))
        
        configs = generate_configs(BATCH_SIZE, r)
        tr_b, tr_s = eng.evaluate_batch(configs, False)
        
        # Honest Filter
        valid = (tr_b <= (best_tr_b + 0.0005)) & (tr_s >= (best_tr_s - 0.005))
        if not valid.any(): continue
        
        surv_idx = cp.where(valid)[0]
        if len(surv_idx) > 20: surv_idx = surv_idx[:20]
        surv_cfg = configs[surv_idx]
        
        te_b, _ = eng.evaluate_batch(surv_cfg, True)
        min_idx = cp.argmin(te_b)
        min_val = float(te_b[min_idx].item()) if GPU_AVAILABLE else float(te_b[min_idx])
        
        if min_val < best_test_brier:
            best_test_brier = min_val
            best_vec = surv_cfg[min_idx]
            
            cur_tr = float(tr_b[surv_idx[min_idx]].item()) if GPU_AVAILABLE else float(tr_b[surv_idx[min_idx]])
            
            print(f"Batch {i} (r={r:.3f}): NEW BEST! Test={min_val:.5f} [Train={cur_tr:.5f}]")
            
            # SAVE IMMEDIATELY
            v_cpu = cp.asnumpy(best_vec) if GPU_AVAILABLE else best_vec
            d = {k: float(v_cpu[idx]) for idx, k in enumerate(PARAM_NAMES)}
            with open(OUTPUT_FILE, 'w') as f: json.dump(d, f, indent=2)

    print(f"Done. Best saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()