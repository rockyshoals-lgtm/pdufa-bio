#!/usr/bin/env python3
"""
ODIN "Coordinate Descent" Optimizer (v17.1 - Fixed Scope)
=========================================================
- FIXED: 'SCAN_RANGE' variable scope error.
- DETERMINISTIC POLISHING.
- Takes the Best Config.
- Generates thousands of "What-If" scenarios.
- Greedily accepts any change that improves Brier Score.
"""

import os
import sys
import time
import argparse
import csv
import json
import numpy as np
import pandas as pd

# --- 1. INITIALIZATION ---
print("--- ODIN COORDINATE DESCENT INITIALIZING ---", flush=True)

try:
    import cupy as cp
    CUPY_AVAILABLE = True
    print("   [OK] CuPy detected. GPU Acceleration ENABLED.")
except ImportError:
    CUPY_AVAILABLE = False
    print("   [WARNING] CuPy not found. CPU Mode (Slow).")
    cp = np

# --- CONFIGURATION ---
DEFAULT_DATA_FILE = "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv"
DEFAULT_SEED_FILE = "odin_gaussian_topN.csv"
OUTPUT_DIR = "cd_results"
FP_PENALTY = 2.0
MAX_CYCLES = 50  
SCAN_STEPS = 200 
INITIAL_SCAN_RANGE = 0.02 # Starting range

PARAM_TO_FEATURE_MAP = {
    "w_btd": "btd", "w_orphan": "orphan", "w_priority": "priority_review",
    "w_fast_track": "fast_track", "w_accel": "accelerated_approval",
    "w_prior_crl": "prior_crl", "w_sponsor_exp": "sponsor_exp",
    "w_sponsor_inexp": "sponsor_inexp", "w_mfg": "manufacturing_risk",
    "w_form483": "form_483_issues", "w_ema_cmc": "ema_cmc_flag",
    "w_cmc_ext": "cmc_extension_flag", "w_app_supp": "app_supp",
    "w_app_ped": "app_ped", "w_adcom_high": "adcom_high",
    "w_adcom_mid": "adcom_mid", "w_adcom_low": "adcom_low",
    "ta_pain": "ta_pain", "ta_oph": "ta_oph", "ta_onc": "ta_onc",
    "ta_infdx": "ta_infdx", "ta_other": "ta_other"
}

NON_WEIGHT_PARAMS = ["base_prob", "t1_cut", "t2_cut", "t3_cut"]

MAX_CONSTRAINTS = {
    "w_prior_crl": 0.0, "w_mfg": 0.0, "w_ema_cmc": 0.0, "w_cmc_ext": 0.0,
    "w_sponsor_inexp": 0.0, "w_app_ped": 0.0, "w_adcom_low": 0.0, "w_form483": 0.0
}

# --- DATA LOADING ---
def _infer_y(series: pd.Series) -> np.ndarray:
    s = series.astype(str).str.strip().str.upper()
    pos = s.isin(["APPROVAL", "APPROVED", "YES", "Y", "TRUE", "T", "1", "SUCCESS"])
    return np.where(pos, 1, 0).astype(np.int8)

def load_and_prep_data(filepath: str):
    if not os.path.exists(filepath):
        print(f"[ERROR] Dataset not found: {filepath}")
        sys.exit(1)
        
    print(f"   Loading dataset: {filepath}")
    df = pd.read_csv(filepath)
    
    for c in list(PARAM_TO_FEATURE_MAP.keys()): pass 

    out_col = next((c for c in ["outcome", "Outcome", "label", "y"] if c in df.columns), None)
    if not out_col: raise ValueError("No outcome column found.")
    y = _infer_y(df[out_col])
    
    feats = {}
    bool_cols = ["btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
                 "had_adcom", "prior_crl", "manufacturing_risk", "form_483_issues",
                 "ema_cmc_flag", "cmc_extension_flag"]
    for c in bool_cols:
        if c not in df.columns: df[c] = False
        feats[c] = df[c].fillna(False).astype(str).str.upper().isin(["1", "TRUE", "T", "YES", "Y"]).astype(np.float32).values

    if "sponsor_prior_approvals" not in df.columns: df["sponsor_prior_approvals"] = 0
    prior = df["sponsor_prior_approvals"].fillna(0).astype(float).values
    feats["sponsor_exp"] = (prior >= 5).astype(np.float32)
    feats["sponsor_inexp"] = (prior <= 0).astype(np.float32)

    if "application_type" not in df.columns: df["application_type"] = ""
    app = df["application_type"].fillna("").astype(str).str.upper()
    feats["app_supp"] = (app.str.contains("SNDA") | app.str.contains("SBLA")).astype(np.float32).values
    feats["app_ped"] = app.str.contains("PED").astype(np.float32).values

    if "had_adcom" not in feats: feats["had_adcom"] = np.zeros(len(df), dtype=np.float32)
    had_adcom = feats["had_adcom"].astype(bool)
    if "adcom_vote_pct" not in df.columns: df["adcom_vote_pct"] = 0
    vote = df["adcom_vote_pct"].fillna(0).astype(float).values
    feats["adcom_high"] = (had_adcom & (vote >= 0.65)).astype(np.float32)
    feats["adcom_mid"] = (had_adcom & (vote >= 0.50) & (vote < 0.65)).astype(np.float32)
    feats["adcom_low"] = (had_adcom & (vote < 0.50)).astype(np.float32)

    if "therapeutic_area" not in df.columns: df["therapeutic_area"] = ""
    ta = df["therapeutic_area"].fillna("").astype(str)
    feats["ta_pain"] = (ta == "Pain Management").astype(np.float32).values
    feats["ta_oph"] = (ta == "Ophthalmology").astype(np.float32).values
    feats["ta_onc"] = (ta == "Oncology").astype(np.float32).values
    feats["ta_infdx"] = (ta == "Infectious Disease").astype(np.float32).values
    feats["ta_other"] = (~ta.isin(["Pain Management", "Ophthalmology", "Oncology", "Infectious Disease"])).astype(np.float32).values

    ordered_keys = list(PARAM_TO_FEATURE_MAP.keys())
    ordered_feats = [PARAM_TO_FEATURE_MAP[k] for k in ordered_keys]
    X_list = [feats[fname] for fname in ordered_feats]
    X = np.stack(X_list, axis=1).astype(np.float32)
    
    return X, y

# --- LOGIC ---

def get_best_config(df: pd.DataFrame):
    if df.empty:
        print("[ERROR] Seed file empty.")
        sys.exit(1)
    
    if "brier_score" in df.columns:
        df = df.sort_values(by=["odin_score", "brier_score"], ascending=[False, True])
    else:
        df = df.sort_values("odin_score", ascending=False)
        
    best_row = df.iloc[0]
    param_names = list(PARAM_TO_FEATURE_MAP.keys()) + NON_WEIGHT_PARAMS
    
    config = []
    for p in param_names:
        if p in best_row: config.append(float(best_row[p]))
        else: config.append(0.0)
            
    return param_names, np.array(config, dtype=np.float32)

def generate_scan_batch(current_config, scan_range, steps, param_names):
    n_params = len(current_config)
    batch_size = n_params * steps
    batch = np.tile(current_config, (batch_size, 1))
    
    row = 0
    for i in range(n_params):
        val = current_config[i]
        p_name = param_names[i]
        low = val - scan_range
        high = val + scan_range
        
        if p_name in MAX_CONSTRAINTS:
            limit = MAX_CONSTRAINTS[p_name]
            low = min(low, limit)
            high = min(high, limit)
            
        if "prob" in p_name or "cut" in p_name:
            low = max(0.01, min(low, 0.99))
            high = max(0.01, min(high, 0.99))
            
        perturbations = np.linspace(low, high, steps, dtype=np.float32)
        batch[row:row+steps, i] = perturbations
        row += steps
        
    return cp.asarray(batch, dtype=cp.float32)

def print_final_json(best_vals, param_names):
    print("\n" + "="*40)
    print("      FINAL COORDINATE DESCENT CONFIG      ")
    print("="*40)
    clean_config = {k: float(best_vals[i]) for i, k in enumerate(param_names)}
    print(json.dumps(clean_config, indent=4))
    print("="*40 + "\n")

# --- MAIN ---
def main():
    print("3. Starting COORDINATE DESCENT loop...", flush=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    X_cpu, y_cpu = load_and_prep_data(DEFAULT_DATA_FILE)
    if CUPY_AVAILABLE:
        X_gpu = cp.asarray(X_cpu)
        y_gpu = cp.asarray(y_cpu)
    else:
        X_gpu, y_gpu = X_cpu, y_cpu
        
    keys = list(PARAM_TO_FEATURE_MAP.keys())
    i_ema = keys.index("w_ema_cmc")
    i_ext = keys.index("w_cmc_ext")
    avoid_mask_gpu = (X_gpu[:, i_ema] > 0.5) | (X_gpu[:, i_ext] > 0.5)

    print(f"   Loading seed file: {DEFAULT_SEED_FILE}")
    if os.path.exists(DEFAULT_SEED_FILE):
        seed_df = pd.read_csv(DEFAULT_SEED_FILE)
    elif os.path.exists("gaussian_results/" + DEFAULT_SEED_FILE):
        seed_df = pd.read_csv("gaussian_results/" + DEFAULT_SEED_FILE)
    else:
        print("[ERROR] Seed file not found.")
        sys.exit(1)
        
    param_names, current_config = get_best_config(seed_df)
    
    # Initialize LOCAL tracking vars
    best_score = -1.0
    best_brier = 100.0
    current_scan_range = INITIAL_SCAN_RANGE
    
    print(f"\n--- LAUNCHING CD OPTIMIZER ---")
    print(f"Cycles: {MAX_CYCLES}")
    print(f"Scan Precision: {SCAN_STEPS} steps per param")
    
    for cycle in range(MAX_CYCLES):
        
        # 1. Generate Batch using LOCAL current_scan_range
        batch_vals = generate_scan_batch(current_config, current_scan_range, SCAN_STEPS, param_names)
        B = batch_vals.shape[0]
        
        # 2. Eval
        n_weights = len(PARAM_TO_FEATURE_MAP)
        W = batch_vals[:, :n_weights]
        base_probs = batch_vals[:, n_weights].reshape(B, 1)
        t1_cuts = batch_vals[:, n_weights + 1].reshape(B, 1)
        
        log_mult = cp.log1p(cp.clip(W, -0.999, 10.0))
        log_prod = log_mult @ X_gpu.T
        probs = base_probs * cp.exp(log_prod)
        probs = cp.clip(probs, 0.01, 0.99)
        
        if avoid_mask_gpu.any():
            probs[:, avoid_mask_gpu] = cp.minimum(probs[:, avoid_mask_gpu], 0.49)
            
        is_t1 = probs >= t1_cuts
        t1_n = cp.sum(is_t1, axis=1)
        
        # Filter T1 Constraints
        valid_mask = (t1_n >= 1200) & (t1_n <= 2000)
        
        if not valid_mask.any():
            print("Warning: All variations violated T1 constraints.")
            continue
            
        idx = cp.where(valid_mask)[0]
        v_probs = probs[idx]
        v_is_t1 = is_t1[idx]
        v_t1_n = t1_n[idx]
        
        v_t1_tp = cp.sum(v_is_t1 & (y_gpu == 1), axis=1)
        v_t1_fp = cp.sum(v_is_t1 & (y_gpu == 0), axis=1)
        v_scores = v_t1_tp - (FP_PENALTY * v_t1_fp)
        
        diff_sq = (v_probs - y_gpu) ** 2
        v_brier = cp.mean(diff_sq, axis=1)
        
        # 3. Find Winner
        res_scores = cp.asnumpy(v_scores)
        res_brier = cp.asnumpy(v_brier)
        valid_indices_cpu = cp.asnumpy(idx)
        
        # Sort: Score Desc -> Brier Asc
        # lexsort keys are reversed order: primary key is last
        # We want: Max Score, then Min Brier
        # So we sort by (Brier, -Score)
        sort_idx = np.lexsort((res_brier, -res_scores))
        
        best_idx_local = sort_idx[0]
        best_global_idx = valid_indices_cpu[best_idx_local]
        
        new_score = res_scores[best_idx_local]
        new_brier = res_brier[best_idx_local]
        
        # 4. Update?
        improved = False
        
        if cycle == 0:
            improved = True
        elif new_score > best_score:
            improved = True
        elif new_score == best_score and new_brier < best_brier:
            improved = True
            
        if improved:
            best_score = new_score
            best_brier = new_brier
            current_config = cp.asnumpy(batch_vals[best_global_idx])
            print(f"Cycle {cycle+1}: Improved! Score: {best_score:.1f} | Brier: {best_brier:.6f}")
        else:
            print(f"Cycle {cycle+1}: No improvement. (Best: {best_score:.1f}, {best_brier:.6f})")
            current_scan_range *= 0.8
            print(f"   -> Reducing scan range to {current_scan_range:.5f}")
            
    # Done
    out_path = os.path.join(OUTPUT_DIR, "odin_cd_final.csv")
    
    final_dict = {k: float(current_config[i]) for i, k in enumerate(param_names)}
    final_dict["odin_score"] = float(best_score)
    final_dict["brier_score"] = float(best_brier)
    
    pd.DataFrame([final_dict]).to_csv(out_path, index=False)
    
    print_final_json(current_config, param_names)
    print(f"DONE. Saved to {out_path}")

if __name__ == "__main__":
    main()