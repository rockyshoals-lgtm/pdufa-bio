import numpy as np
import pandas as pd
import time
import json  # <--- FIXED: Added missing import
from odin_vectorized_v104 import OdinVectorizedEvaluator, PARAM_KEYS, PARAM_CONSTRAINTS, vector_to_config

# --- CONFIG ---
DATA_FILE = "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv"
BATCH_SIZE = 100_000
N_BATCHES = 100 # Total 10 Million
OUTPUT_FILE = "odin_v104_optimized.csv"

# CONSTRAINT SETTINGS
# We relax the minimum T1 count slightly to ensure the optimizer starts finding solutions
MIN_TIER_1_COUNT = 800 

def generate_constrained_batch(batch_size, n_params):
    """
    Generates random weights respecting domain constraints.
    """
    # 1. Random uniform initialization (-0.5 to 0.5)
    batch = np.random.uniform(-0.5, 0.5, (batch_size, n_params))
    
    # 2. Apply Constraints
    # PARAM_CONSTRAINTS: 1 (Pos), -1 (Neg), 0 (Free)
    
    # Force Positive (Boosts) -> abs()
    pos_mask = (PARAM_CONSTRAINTS == 1)
    batch[:, pos_mask] = np.abs(batch[:, pos_mask])
    
    # Force Negative (Penalties) -> -abs()
    neg_mask = (PARAM_CONSTRAINTS == -1)
    batch[:, neg_mask] = -np.abs(batch[:, neg_mask])
    
    # 3. Special handling for Base Rate (Index 0)
    # OPTIMIZATION: Shifted range up to [0.70, 0.98] to ensure we hit Tier 1 thresholds
    batch[:, 0] = np.random.uniform(0.70, 0.98, batch_size)
    
    # 4. Append Thresholds (3 cols)
    # T1 > T2 > T3
    # Generate 3 randoms, sort them, assign in reverse order
    thresholds = np.random.uniform(0.50, 0.95, (batch_size, 3))
    thresholds.sort(axis=1)
    thresholds = thresholds[:, ::-1] # Flip so T1 is highest
    
    return np.hstack([batch, thresholds])

def main():
    print("Loading Data...")
    try:
        df = pd.read_csv(DATA_FILE)
        # Ensure dummy columns exist if raw data is missing them
        required_cols = ['btd', 'orphan', 'priority_review', 'fast_track', 'accelerated_approval',
                         'had_adcom', 'prior_crl', 'class1_resub', 'manufacturing_risk',
                         'form_483_issues', 'ema_cmc_flag', 'cmc_extension_flag',
                         's22_ped_pk_missing', 'outcome', 'application_type']
        for c in required_cols:
            if c not in df.columns: df[c] = 0
            
        evaluator = OdinVectorizedEvaluator(df)
        print(f"Evaluator Ready. X shape: {evaluator.X.shape}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    best_score = -9999
    best_config = None
    
    print(f"Starting Search: {N_BATCHES * BATCH_SIZE} configs...")
    print(f"Targeting > {MIN_TIER_1_COUNT} Tier 1 events...")
    
    start_time = time.time()
    
    for i in range(N_BATCHES):
        # Generate
        batch_vecs = generate_constrained_batch(BATCH_SIZE, len(PARAM_KEYS))
        
        # Evaluate (on GPU if available)
        if 'cupy' in str(type(evaluator.X)):
            import cupy as cp
            batch_vecs = cp.asarray(batch_vecs)
            
        results = evaluator.evaluate_batch(batch_vecs, t1_band_min=MIN_TIER_1_COUNT)
        
        # Find best in batch
        scores = results['score']
        # Move to CPU for max search
        if 'cupy' in str(type(scores)): scores = scores.get()
            
        max_idx = np.argmax(scores)
        max_score = scores[max_idx]
        
        if max_score > best_score:
            best_score = max_score
            # Extract config vector
            if 'cupy' in str(type(batch_vecs)):
                best_vec = batch_vecs[max_idx].get()
            else:
                best_vec = batch_vecs[max_idx]
                
            best_config = vector_to_config(best_vec)
            
            # Add metrics
            metrics = {
                'odin_score': float(max_score),
                'brier': float(results['brier'][max_idx]),
                't1_hit_rate': float(results['t1_hit_rate'][max_idx]),
                't1_n': int(results['t1_n'][max_idx])
            }
            best_config.update(metrics)
            
            print(f"Batch {i}: New Best! Score={best_score:.1f} | HitRate={metrics['t1_hit_rate']:.3f} (N={metrics['t1_n']}) | Brier={metrics['brier']:.4f}")

    print("Search Complete.")
    if best_config:
        print("Top Config:")
        print(json.dumps(best_config, indent=2))
        # Save to file
        pd.DataFrame([best_config]).to_csv(OUTPUT_FILE, index=False)
        print(f"Saved to {OUTPUT_FILE}")
    else:
        print("No valid configuration found. Try relaxing t1_band_min or checking data.")

if __name__ == "__main__":
    main()