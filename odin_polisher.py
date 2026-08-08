#!/usr/bin/env python3
"""
ODIN "Polisher" Search (v15.0)
==============================
- LOADS 'odin_sniper_topN.csv'.
- CALCULATES the 'Centroid' (Mean) of the Top 50 tied configs.
- ADDS 'Brier Score' (MSE) as a tie-breaker to force convergence.
- SEARCHES a tiny radius around the optimal center.
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
print("--- ODIN POLISHER INITIALIZING ---", flush=True)

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
DEFAULT_SEED_FILE = "odin_sniper_topN.csv"  # PREVIOUS SNIPER RESULTS
OUTPUT_DIR = "polisher_results"
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

# Strict Monotonicity Constraints
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
    
    # Check Columns
    for c in list(PARAM_TO_FEATURE_MAP.keys()): pass 

    # Outcome
    out_col = next((c for c in ["outcome", "Outcome", "label", "y"] if c in df.columns), None)
    if not out_col: raise ValueError("No outcome column found.")
    y = _infer_y(df[out_col])
    
    # Feature Construction
    feats = {}
    
    # 1. Booleans
    bool_cols = ["btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
                 "had_adcom", "prior_crl", "manufacturing_risk", "form_483_issues",
                 "ema_cmc_flag", "cmc_extension_flag"]
    for c in bool_cols:
        if c not in df.columns: df[c] = False
        feats[c] = df[c].fillna(False).astype(str).str.upper().isin(["1", "TRUE", "T", "YES", "Y"]).astype(np.float32).values

    # 2. Sponsor
    if "sponsor_prior_approvals" not in df.columns: df["sponsor_prior_approvals"] = 0
    prior = df["sponsor_prior_approvals"].fillna(0).astype(float).values
    feats["sponsor_exp"] = (prior >= 5).astype(np.float32)
    feats["sponsor_inexp"] = (prior <= 0).astype(np.float32)

    # 3. Apps
    if "application_type" not in df.columns: df["application_type"] = ""
    app = df["application_type"].fillna("").astype(str).str.upper()
    feats["app_supp"] = (app.str.contains("SNDA") | app.str.contains("SBLA")).astype(np.float32).values
    feats["app_ped"] = app.str.contains("PED").astype(np.float32).values

    # 4. Adcom
    if "had_adcom" not in feats: feats["had_adcom"] = np.zeros(len(df), dtype=np.float32)
    had_adcom = feats["had_adcom"].astype(bool)
    if "adcom_vote_pct" not in df.columns: df["adcom_vote_pct"] = 0
    vote = df["adcom_vote_pct"].fillna(0).astype(float).values
    feats["adcom_high"] = (had_adcom & (vote >= 0.65)).astype(np.float32)
    feats["adcom_mid"] = (had_adcom & (vote >= 0.50) & (vote < 0.65)).astype(np.float32)
    feats["adcom_low"] = (had_adcom & (vote < 0.50)).astype(np.float32)

    # 5. TA
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

def get_polisher_box(df: pd.DataFrame, current_best_df=None):
    """
    Calculates the CENTROID (Mean) of the Top 50 and creates a tiny box around it.
    """
    combined_df = df
    if current_best_df is not None and not current_best_df.empty:
        combined_df = pd.concat([df, current_best_df], ignore_index=True)
    
    if "odin_score" in combined_df.columns:
        # Sort by Score (Desc) THEN Brier (Asc) if available
        # But Brier might not be in the file yet, so just Score
        combined_df = combined_df.sort_values("odin_score", ascending=False)
    
    # Focus on Top 50
    top_df = combined_df.head(50)
    
    param_names = list(PARAM_TO_FEATURE_MAP.keys()) + NON_WEIGHT_PARAMS
    mins, maxs = [], []
    is_empty = len(top_df) == 0

    for p in param_names:
        if is_empty or p not in top_df.columns:
            if "prob" in p or "cut" in p:
                low, high = 0.01, 0.99
            else:
                low, high = -0.1, 0.1
        else:
            # POLISHER STRATEGY: Use Mean +/- Small Deviation
            vals = top_df[p].values
            mean_val = np.mean(vals)
            
            # Tiny radius: 5% of the range or 0.05 absolute, whichever is smaller
            # This "Locks in" the parameter
            radius = 0.05 
            
            low, high = mean_val - radius, mean_val + radius
        
        # Constraints
        if p in MAX_CONSTRAINTS:
            limit = MAX_CONSTRAINTS[p]
            low = min(low, limit)
            high = min(high, limit)
        if "prob" in p or "cut" in p:
            low = max(0.01, min(low, 0.99))
            high = max(0.01, min(high, 0.99))
            
        mins.append(low); maxs.append(high)
        
    return param_names, np.array(mins, dtype=np.float32), np.array(maxs, dtype=np.float32)

def generate_random_batch(batch_size, mins, maxs):
    rnd = cp.random.random((batch_size, len(mins)), dtype=cp.float32)
    span = cp.asarray(maxs - mins)
    lower = cp.asarray(mins)
    return (span * rnd) + lower

def print_final_json(best_config):
    print("\n" + "="*40)
    print("      FINAL POLISHED ODIN CONFIG      ")
    print("="*40)
    clean_config = {k: v for k, v in best_config.items() 
                   if k in PARAM_TO_FEATURE_MAP or k in NON_WEIGHT_PARAMS}
    print(json.dumps(clean_config, indent=4))
    print("="*40 + "\n")

# --- MAIN ---
def main():
    print("3. Starting POLISHER execution loop...", flush=True)
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
    else:
        print("   [WARNING] Seed file not found. Starting FRESH.")
        seed_df = pd.DataFrame(columns=list(PARAM_TO_FEATURE_MAP.keys()))
        
    param_names, mins, maxs = get_polisher_box(seed_df)
    
    # Batch Calc
    batch_size = 50_000
    if CUPY_AVAILABLE:
        mem = cp.cuda.runtime.memGetInfo()[0]
        rows = X_cpu.shape[0]
        bytes_per_cfg = (rows * 10) + 128 
        batch_size = int((mem * 0.8) / bytes_per_cfg)
        batch_size = max(10000, min(batch_size, 500_000))
    
    print(f"\n--- LAUNCHING POLISHER SEARCH ---")
    print(f"Target Iterations: {TOTAL_ITERS:,}")
    print(f"Batch Size: {batch_size:,}")
    print(f"Output: {OUTPUT_DIR}/odin_polisher_topN.csv\n")
    
    top_configs = []
    if not seed_df.empty:
        top_configs = seed_df.head(200).to_dict('records')
        # Add brier score to existing records if missing (default to 1.0)
        for c in top_configs:
             if "brier_score" not in c: c["brier_score"] = 1.0

    start_time = time.time()
    total_processed = 0
    
    while total_processed < TOTAL_ITERS:
        
        # ZOOM
        if total_processed > 0 and total_processed % ZOOM_INTERVAL < batch_size:
            print(f"\n[ZOOM] Re-centering on Mean of Top 50...")
            current_best_df = pd.DataFrame(top_configs)
            _, mins, maxs = get_polisher_box(seed_df, current_best_df)
            print("       Search space optimized.\n")

        try:
            batch_vals = generate_random_batch(batch_size, mins, maxs)
            
            B = batch_size
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
            
            valid_mask = (t1_n >= 1200) & (t1_n <= 2000)
            if not valid_mask.any(): 
                total_processed += batch_size
                continue
            
            idx = cp.where(valid_mask)[0]
            
            v_t1_tp = cp.sum(is_t1[idx] & (y_gpu == 1), axis=1)
            v_t1_fp = cp.sum(is_t1[idx] & (y_gpu == 0), axis=1)
            v_scores = v_t1_tp - (FP_PENALTY * v_t1_fp)
            v_rates = v_t1_tp / cp.maximum(t1_n[idx], 1.0)
            
            # --- BRIER SCORE CALCULATION (Tie Breaker) ---
            # MSE = (Prob - Y)^2
            # Broadcast y_gpu (Events,) to (B_valid, Events)
            # This is expensive so we only do it for valid configs
            # We calculate mean over events for each config
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
            
            # SORT: 1. Score (Desc), 2. Brier (Asc)
            # Tuple sort in Python does this naturally if we negate Score
            top_configs.sort(key=lambda x: (-x["odin_score"], x["brier_score"]))
            top_configs = top_configs[:200]
            
            total_processed += batch_size
            
            if total_processed % (batch_size * 10) == 0:
                elapsed = time.time() - start_time
                rate = total_processed / max(elapsed, 0.1)
                best_s = top_configs[0]["odin_score"] if top_configs else 0
                best_b = top_configs[0]["brier_score"] if top_configs else 1.0
                print(f"Processed: {total_processed:,} | {rate:,.0f} cfg/s | Best Score: {best_s:.1f} (Brier: {best_b:.4f})")
                
            if total_processed % (batch_size * 50) == 0:
                 out_path = os.path.join(OUTPUT_DIR, "odin_polisher_topN.csv")
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

    out_path = os.path.join(OUTPUT_DIR, "odin_polisher_topN.csv")
    pd.DataFrame(top_configs).to_csv(out_path, index=False)
    
    if top_configs:
        print_final_json(top_configs[0])
    
    print(f"\nDONE. Results saved to {out_path}")

if __name__ == "__main__":
    main()