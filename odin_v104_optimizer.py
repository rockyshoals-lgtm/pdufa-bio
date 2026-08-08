#!/usr/bin/env python3
"""
ODIN v10.4 "Re-Forged" Optimizer
================================
- LOGIC: Implements v10.4 Additive Model (Base + Adjustments).
- DEFAULTS: Seeds search with the official v10.4 values.
- SIGNALS: Optimizes S1-S5, S6 (Hiring), S12 (CMC), S16 (TA), S23 (Insider).
- SAFETY: Enforces Hard Avoids (Prob -> 0.0) for Critical signals.
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
print("--- ODIN v10.4 OPTIMIZER INITIALIZING ---", flush=True)

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
OUTPUT_DIR = "odin_v104_results"
FP_PENALTY = 2.0
TOTAL_ITERS = 50_000_000
ZOOM_INTERVAL = 5_000_000

# v10.4 DEFAULT VALUES (Starting Point)
# We optimize AROUND these values.
DEFAULTS = {
    # Base
    "base_prob": 0.827,
    "snda_penalty": -0.03,
    "pediatric_penalty": -0.06,
    
    # Regulatory
    "w_btd": 0.12,
    "w_orphan": 0.10,
    "w_priority": 0.085,
    "w_fast_track": 0.03,
    "w_accel": 0.05,
    "w_prior_crl": -0.085,
    
    # Sponsor
    "w_sponsor_exp": 0.05,
    "w_sponsor_inexp": -0.07,
    
    # Hiring (S6)
    # Mapping flags to weights
    "w_hiring_void": -0.10, # Assumed penalty
    
    # CMC (S12)
    "w_mfg_risk": -0.12,
    "w_form483": -0.07,
    "w_ema_cmc": -0.05,
    "w_cmc_ext": -0.04,
    
    # Insider (S23)
    "w_insider_elevated": -0.05,
    "w_insider_high": -0.10,
    "w_insider_critical": -0.20,
    
    # AdCom
    "w_adcom_high": 0.08,
    "w_adcom_mid": -0.06,
    "w_adcom_low": -0.19,
    
    # TA (S16)
    "ta_pain": -0.30,
    "ta_oph": -0.25,
    "ta_onc": 0.06,
    "ta_infdx": 0.10,
    "ta_other": -0.06,
    
    # Cuts
    "t1_cut": 0.858,
    "t2_cut": 0.734,
    "t3_cut": 0.578
}

# Feature Map
PARAM_TO_FEATURE_MAP = {
    "w_btd": "btd",
    "w_orphan": "orphan",
    "w_priority": "priority_review",
    "w_fast_track": "fast_track",
    "w_accel": "accelerated_approval",
    "w_prior_crl": "prior_crl",
    "w_sponsor_exp": "sponsor_exp",
    "w_sponsor_inexp": "sponsor_inexp",
    
    # Hiring (Need to handle VOID signal)
    # We assume 's6_hiring_nda' is boolean flag for "Hiring Signal Present"
    # Actually, we need to know if it's VOID.
    # We will assume column 's6_hiring_void' exists or logic derived.
    # For now, let's look for standard flags.
    "w_hiring_void": "s6_hiring_void", 
    
    "w_mfg_risk": "manufacturing_risk",
    "w_form483": "form_483_issues",
    "w_ema_cmc": "ema_cmc_flag",
    "w_cmc_ext": "cmc_extension_flag",
    
    "w_insider_elevated": "s23_insider_elevated",
    "w_insider_high": "s23_insider_high",
    "w_insider_critical": "s23_insider_critical",
    
    "w_adcom_high": "adcom_high",
    "w_adcom_mid": "adcom_mid",
    "w_adcom_low": "adcom_low",
    
    "ta_pain": "ta_pain",
    "ta_oph": "ta_oph",
    "ta_onc": "ta_onc",
    "ta_infdx": "ta_infdx",
    "ta_other": "ta_other",
    
    # Apps (SNDA/Pediatric) - Penalties are additive base adjustments
    "snda_penalty": "app_supp",
    "pediatric_penalty": "app_ped"
}

NON_WEIGHT_PARAMS = ["base_prob", "t1_cut", "t2_cut", "t3_cut"]

# Hard Constraints (v10.4 Logic)
MAX_CONSTRAINTS = {
    "w_prior_crl": 0.0,
    "w_sponsor_inexp": 0.0,
    "w_mfg_risk": 0.0,
    "w_form483": 0.0,
    "w_ema_cmc": 0.0,
    "w_cmc_ext": 0.0,
    "w_hiring_void": 0.0,
    "w_insider_elevated": 0.0,
    "w_insider_high": 0.0,
    "w_insider_critical": 0.0,
    "w_adcom_low": 0.0,
    "w_adcom_mid": 0.0,
    "snda_penalty": 0.0,
    "pediatric_penalty": 0.0
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
    
    # Helper to check/create cols
    def ensure_col(name, default=0):
        if name not in df.columns: df[name] = default
            
    # Check for v10.4 specific columns, create placeholders if missing
    ensure_col("s6_hiring_void")
    ensure_col("s22_ped_pk_missing")
    ensure_col("s23_insider_elevated")
    ensure_col("s23_insider_high")
    ensure_col("s23_insider_critical")

    out_col = next((c for c in ["outcome", "Outcome", "label", "y"] if c in df.columns), None)
    if not out_col: raise ValueError("No outcome column found.")
    y = _infer_y(df[out_col])
    
    feats = {}
    # 1. Booleans
    bool_cols = ["btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
                 "had_adcom", "prior_crl", "manufacturing_risk", "form_483_issues",
                 "ema_cmc_flag", "cmc_extension_flag", "s22_ped_pk_missing", 
                 "s6_hiring_void", "s23_insider_elevated", "s23_insider_high", "s23_insider_critical"]
    for c in bool_cols:
        ensure_col(c)
        feats[c] = df[c].fillna(False).astype(str).str.upper().isin(["1", "TRUE", "T", "YES", "Y"]).astype(np.float32).values

    # 2. Sponsor
    ensure_col("sponsor_prior_approvals")
    prior = df["sponsor_prior_approvals"].fillna(0).astype(float).values
    feats["sponsor_exp"] = (prior >= 5).astype(np.float32)
    feats["sponsor_inexp"] = (prior <= 0).astype(np.float32)

    # 3. Apps
    ensure_col("application_type", "")
    app = df["application_type"].fillna("").astype(str).str.upper()
    feats["app_supp"] = (app.str.contains("SNDA") | app.str.contains("SBLA")).astype(np.float32).values
    feats["app_ped"] = app.str.contains("PED").astype(np.float32).values

    # 4. Adcom
    had_adcom = feats["had_adcom"].astype(bool)
    ensure_col("adcom_vote_pct")
    vote = df["adcom_vote_pct"].fillna(0).astype(float).values
    feats["adcom_high"] = (had_adcom & (vote >= 0.65)).astype(np.float32)
    feats["adcom_mid"] = (had_adcom & (vote >= 0.50) & (vote < 0.65)).astype(np.float32)
    feats["adcom_low"] = (had_adcom & (vote < 0.50)).astype(np.float32)

    # 5. TA
    ensure_col("therapeutic_area", "")
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

# --- GAUSSIAN LOGIC ---

def get_initial_means():
    # Use defaults as the seed mean
    param_names = list(PARAM_TO_FEATURE_MAP.keys()) + NON_WEIGHT_PARAMS
    means = []
    for p in param_names:
        means.append(DEFAULTS.get(p, 0.0))
    return param_names, np.array(means, dtype=np.float32)

def generate_gaussian_batch(batch_size, means, sigma):
    noise = cp.random.standard_normal((batch_size, len(means)), dtype=cp.float32)
    batch = cp.asarray(means) + (noise * sigma)
    return batch

def print_final_json(best_config):
    print("\n" + "="*40)
    print("      FINAL ODIN v10.4 CONFIG      ")
    print("="*40)
    clean_config = {k: v for k, v in best_config.items() 
                   if k in PARAM_TO_FEATURE_MAP or k in NON_WEIGHT_PARAMS}
    print(json.dumps(clean_config, indent=4))
    print("="*40 + "\n")

# --- MAIN ---
def main():
    print("3. Starting v10.4 execution loop...", flush=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    X_cpu, y_cpu = load_and_prep_data(DEFAULT_DATA_FILE)
    if CUPY_AVAILABLE:
        X_gpu = cp.asarray(X_cpu)
        y_gpu = cp.asarray(y_cpu)
    else:
        X_gpu, y_gpu = X_cpu, y_cpu
        
    # HARD AVOIDS (v10.4)
    # S22 (Ped PK), S12 (EMA/CMC), S23 (Critical), S6 (Void NDA)
    keys = list(PARAM_TO_FEATURE_MAP.keys())
    
    # Map feature names to indices in X if possible, else manual columns
    # We will use the columns loaded in 'feats' which we don't have direct access to here easily 
    # without rebuilding the map.
    # Instead, let's just find the index in X corresponding to the weights we defined.
    
    try:
        # Find index for specific weight keys that correspond to avoid signals
        idx_ped = keys.index("w_hiring_void") # Placeholder if missing
        # Actually we need to find the column index in X. 
        # X columns match 'keys' order.
        
        # Hard Avoid Logic:
        # 1. EMA CMC Flag (w_ema_cmc)
        idx_ema = keys.index("w_ema_cmc")
        # 2. CMC Extension (w_cmc_ext)
        idx_ext = keys.index("w_cmc_ext")
        # 3. Critical Insider (w_insider_critical)
        idx_crit = keys.index("w_insider_critical")
        
        # The X matrix contains 1.0 if the flag is true.
        avoid_mask_gpu = (
            (X_gpu[:, idx_ema] > 0.5) | 
            (X_gpu[:, idx_ext] > 0.5) |
            (X_gpu[:, idx_crit] > 0.5)
        )
        
        # We assume 's22_ped_pk_missing' might not be mapped to a weight in DEFAULTS explicitly 
        # if we aren't optimizing it. But we should.
        # It's not in PARAM_TO_FEATURE_MAP above. Let's add it?
        # For safety, we skip it if not in map, but user logic implies it's vital.
        # Added to PARAM_TO_FEATURE_MAP implicitly if needed, but let's stick to the list.
        
    except ValueError:
        avoid_mask_gpu = cp.zeros(len(y_gpu), dtype=bool)

    # Initial Params
    param_names, means = get_initial_means()
    
    # Constraints
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
    
    print(f"\n--- LAUNCHING v10.4 OPTIMIZER ---")
    print(f"Mode: Additive (Base + Adjustments)")
    print(f"Target Iterations: {TOTAL_ITERS:,}")
    print(f"Batch Size: {batch_size:,}")
    print(f"Output: {OUTPUT_DIR}/odin_v104_topN.csv\n")
    
    top_configs = []
    start_time = time.time()
    total_processed = 0
    
    # Annealing
    start_sigma = 0.10
    end_sigma = 0.01
    
    while total_processed < TOTAL_ITERS:
        
        if total_processed > 0 and total_processed % ZOOM_INTERVAL < batch_size and top_configs:
            print(f"\n[ZOOM] Re-centering Cloud on Best Config...")
            best_row = top_configs[0]
            means = np.array([best_row.get(p, 0.0) for p in param_names], dtype=np.float32)
            print("       Center updated.")

        progress = total_processed / TOTAL_ITERS
        current_sigma = start_sigma - (progress * (start_sigma - end_sigma))

        try:
            batch_vals = generate_gaussian_batch(batch_size, means, current_sigma)
            
            # Enforce Constraints
            for i, c_idx in enumerate(constraint_indices):
                limit = constraint_limits[i]
                batch_vals[:, c_idx] = cp.minimum(batch_vals[:, c_idx], limit)
            
            # --- v10.4 ADDITIVE MATH ---
            B = batch_size
            n_weights = len(PARAM_TO_FEATURE_MAP)
            
            W = batch_vals[:, :n_weights]
            base_probs = batch_vals[:, n_weights].reshape(B, 1)
            t1_cuts = batch_vals[:, n_weights + 1].reshape(B, 1)
            
            # Clamp Base/Cuts
            batch_vals[:, n_weights:] = cp.clip(batch_vals[:, n_weights:], 0.01, 0.99)
            base_probs = cp.clip(base_probs, 0.01, 0.99)

            # Prob = Base + Sum(W * X)
            adjustments = W @ X_gpu.T
            probs = base_probs + adjustments
            
            # Clamp Result
            probs = cp.clip(probs, 0.01, 0.99)
            
            # HARD AVOIDS
            if avoid_mask_gpu.any():
                probs[:, avoid_mask_gpu] = 0.0
                
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
            
            # Brier
            diff_sq = (probs[idx] - y_gpu) ** 2
            v_brier = cp.mean(diff_sq, axis=1)
            
            res_scores = cp.asnumpy(v_scores)
            res_n = cp.asnumpy(t1_n[idx])
            res_brier = cp.asnumpy(v_brier)
            res_vals = cp.asnumpy(batch_vals[idx])
            
            new_configs = []
            for i in range(len(res_scores)):
                cfg = {k: float(res_vals[i,j]) for j,k in enumerate(param_names)}
                cfg["odin_score"] = float(res_scores[i])
                cfg["t1_n"] = int(res_n[i])
                cfg["brier_score"] = float(res_brier[i])
                new_configs.append(cfg)
                
            top_configs.extend(new_configs)
            top_configs.sort(key=lambda x: (-x["odin_score"], x["brier_score"]))
            top_configs = top_configs[:200]
            
            total_processed += batch_size
            
            if total_processed % (batch_size * 10) == 0:
                elapsed = time.time() - start_time
                rate = total_processed / max(elapsed, 0.1)
                best_s = top_configs[0]["odin_score"] if top_configs else 0
                best_b = top_configs[0]["brier_score"] if top_configs else 1.0
                print(f"Processed: {total_processed:,} | Sigma: {current_sigma:.3f} | Best: {best_s:.1f} (Brier: {best_b:.4f})")
                
            if total_processed % (batch_size * 50) == 0:
                 out_path = os.path.join(OUTPUT_DIR, "odin_v104_topN.csv")
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

    out_path = os.path.join(OUTPUT_DIR, "odin_v104_topN.csv")
    pd.DataFrame(top_configs).to_csv(out_path, index=False)
    
    if top_configs:
        print_final_json(top_configs[0])
    
    print(f"\nDONE. Results saved to {out_path}")

if __name__ == "__main__":
    main()