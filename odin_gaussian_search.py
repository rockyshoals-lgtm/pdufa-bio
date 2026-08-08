#!/usr/bin/env python3
"""
ODIN "Gaussian Cloud" Search (v16.1 - Fixed Paths & Annealing)
==============================================================
- FIX: Automatically finds 'odin_polisher_topN.csv' in subfolders.
- FEATURE: Simulated Annealing (Sigma decays from 0.05 -> 0.01).
  This starts with a wider search and "freezes" into the perfect optimum.
- OPTIMIZATION: Prioritizes Brier Score (Confidence) since Accuracy is maxed.
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
print("--- ODIN GAUSSIAN CLOUD SEARCH INITIALIZING ---", flush=True)

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
OUTPUT_DIR = "gaussian_results"
FP_PENALTY = 2.0
TOTAL_ITERS = 50_000_000  # 50 Million
ZOOM_INTERVAL = 5_000_000 

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

# --- PATH FINDER ---
def find_seed_file():
    candidates = [
        "odin_polisher_topN.csv",
        "polisher_results/odin_polisher_topN.csv",
        "odin_sniper_topN.csv",
        "sniper_results/odin_sniper_topN.csv"
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

# --- GAUSSIAN LOGIC ---

def get_gaussian_params(df: pd.DataFrame):
    if df.empty:
        print("[ERROR] Seed file empty.")
        sys.exit(1)
        
    # Sort: High Score first, then Low Brier
    if "brier_score" in df.columns:
        df = df.sort_values(by=["odin_score", "brier_score"], ascending=[False, True])
    elif "odin_score" in df.columns:
        df = df.sort_values("odin_score", ascending=False)
        
    best_row = df.iloc[0]
    param_names = list(PARAM_TO_FEATURE_MAP.keys()) + NON_WEIGHT_PARAMS
    means = []
    
    for p in param_names:
        if p in best_row:
            means.append(best_row[p])
        else:
            means.append(0.0)
            
    return param_names, np.array(means, dtype=np.float32)

def generate_gaussian_batch(batch_size, means, sigma):
    # X ~ N(mean, sigma)
    noise = cp.random.standard_normal((batch_size, len(means)), dtype=cp.float32)
    batch = cp.asarray(means) + (noise * sigma)
    return batch

def print_final_json(best_config):
    print("\n" + "="*40)
    print("      FINAL GAUSSIAN CONFIG      ")
    print("="*40)
    clean_config = {k: v for k, v in best_config.items() 
                   if k in PARAM_TO_FEATURE_MAP or k in NON_WEIGHT_PARAMS}
    print(json.dumps(clean_config, indent=4))
    print("="*40 + "\n")

# --- MAIN ---
def main():
    print("3. Starting GAUSSIAN CLOUD execution loop...", flush=True)
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

    # Auto-Locate Seed
    seed_path = find_seed_file()
    if seed_path:
        print(f"   Loading seed file: {seed_path}")
        seed_df = pd.read_csv(seed_path)
    else:
        print("[ERROR] Seed file (odin_polisher_topN.csv) not found in current folder or subfolders.")
        sys.exit(1)
        
    param_names, means = get_gaussian_params(seed_df)
    
    # Pre-calc constraint indices for speed
    constraint_indices = []
    constraint_limits = []
    for idx, p in enumerate(param_names):
        if p in MAX_CONSTRAINTS:
            constraint_indices.append(idx)
            constraint_limits.append(MAX_CONSTRAINTS[p])

    # Batch Calc
    batch_size = 50_000
    if CUPY_AVAILABLE:
        mem = cp.cuda.runtime.memGetInfo()[0]
        rows = X_cpu.shape[0]
        bytes_per_cfg = (rows * 10) + 128 
        batch_size = int((mem * 0.8) / bytes_per_cfg)
        batch_size = max(10000, min(batch_size, 500_000))
    
    print(f"\n--- LAUNCHING GAUSSIAN CLOUD ---")
    print(f"Target Iterations: {TOTAL_ITERS:,}")
    print(f"Batch Size: {batch_size:,}")
    print(f"Output: {OUTPUT_DIR}/odin_gaussian_topN.csv\n")
    
    top_configs = seed_df.head(200).to_dict('records')
    for c in top_configs:
         if "brier_score" not in c: c["brier_score"] = 1.0

    start_time = time.time()
    total_processed = 0
    
    # Annealing Params
    start_sigma = 0.05
    end_sigma = 0.01
    
    while total_processed < TOTAL_ITERS:
        
        # ZOOM / RE-CENTER
        if total_processed > 0 and total_processed % ZOOM_INTERVAL < batch_size:
            print(f"\n[ZOOM] Re-centering Cloud on Best Config...")
            current_best_df = pd.DataFrame(top_configs)
            _, means = get_gaussian_params(current_best_df)
            print("       Center updated.")

        # DYNAMIC SIGMA (Annealing)
        progress = total_processed / TOTAL_ITERS
        current_sigma = start_sigma - (progress * (start_sigma - end_sigma))

        try:
            batch_vals = generate_gaussian_batch(batch_size, means, current_sigma)
            
            # Enforce Constraints
            for i, c_idx in enumerate(constraint_indices):
                limit = constraint_limits[i]
                batch_vals[:, c_idx] = cp.minimum(batch_vals[:, c_idx], limit)
            
            # Eval
            B = batch_size
            n_weights = len(PARAM_TO_FEATURE_MAP)
            
            W = batch_vals[:, :n_weights]
            base_probs = batch_vals[:, n_weights].reshape(B, 1)
            t1_cuts = batch_vals[:, n_weights + 1].reshape(B, 1)
            
            # Clamp Probs/Cuts to valid range
            batch_vals[:, n_weights:] = cp.clip(batch_vals[:, n_weights:], 0.01, 0.99)
            
            log_mult = cp.log1p(cp.clip(W, -0.999, 10.0))
            log_prod = log_mult @ X_gpu.T
            probs = base_probs * cp.exp(log_prod)
            probs = cp.clip(probs, 0.01, 0.99)
            
            if avoid_mask_gpu.any():
                probs[:, avoid_mask_gpu] = cp.minimum(probs[:, avoid_mask_gpu], 0.49)
                
            is_t1 = probs >= t1_cuts
            t1_n = cp.sum(is_t1, axis=1)
            
            valid_mask = (t1_n >= 1200) & (t1_n <= 2000)
            if not valid_mask.any(): 
                total_processed += batch_size
                continue
            
            idx = cp.where(valid_mask)[0]
            
            v_t1_tp = cp.sum(is_t1[idx] & (y_gpu == 1), axis=1)
            v_t1_fp = cp.sum(is_t1[idx] & (y_gpu == 0), axis=1)
            v_scores = v_t1_tp - (FP_PENALTY * v_t1_fp)
            v_rates = v_t1_tp / cp.maximum(t1_n[idx], 1.0)
            
            # Brier Score (MSE)
            diff_sq = (probs[idx] - y_gpu) ** 2
            v_brier = cp.mean(diff_sq, axis=1)
            
            res_scores = cp.asnumpy(v_scores)
            res_rates = cp.asnumpy(v_rates)
            res_n = cp.asnumpy(t1_n[idx])
            res_brier = cp.asnumpy(v_brier)
            res_vals = cp.asnumpy(batch_vals[idx])
            
            new_configs = []
            for i in range(len(res_scores)):
                cfg = {k: float(res_vals[i,j]) for j,k in enumerate(param_names)}
                cfg["odin_score"] = float(res_scores[i])
                cfg["t1_hit_rate"] = float(res_rates[i])
                cfg["t1_n"] = int(res_n[i])
                cfg["brier_score"] = float(res_brier[i])
                new_configs.append(cfg)
                
            top_configs.extend(new_configs)
            # Sort by Score (Desc), Brier (Asc)
            top_configs.sort(key=lambda x: (-x["odin_score"], x["brier_score"]))
            top_configs = top_configs[:200]
            
            total_processed += batch_size
            
            if total_processed % (batch_size * 10) == 0:
                elapsed = time.time() - start_time
                rate = total_processed / max(elapsed, 0.1)
                best_s = top_configs[0]["odin_score"] if top_configs else 0
                best_b = top_configs[0]["brier_score"] if top_configs else 1.0
                print(f"Processed: {total_processed:,} | Sigma: {current_sigma:.3f} | Best Score: {best_s:.1f} (Brier: {best_b:.4f})")
                
            if total_processed % (batch_size * 50) == 0:
                 out_path = os.path.join(OUTPUT_DIR, "odin_gaussian_topN.csv")
                 pd.DataFrame(top_configs).to_csv(out_path, index=False)

        except cp.cuda.memory.OutOfMemoryError:
            print(f"\n[!] OOM. Halving batch size...")
            cp.get_default_memory_pool().free_all_blocks()
            batch_size = int(batch_size / 2)
            if batch_size < 100: break
            continue
            
        except KeyboardInterrupt:
            print("\n[STOP] User stopped script.")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            break

    out_path = os.path.join(OUTPUT_DIR, "odin_gaussian_topN.csv")
    pd.DataFrame(top_configs).to_csv(out_path, index=False)
    
    if top_configs:
        print_final_json(top_configs[0])
    
    print(f"\nDONE. Results saved to {out_path}")

if __name__ == "__main__":
    main()