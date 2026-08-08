#!/usr/bin/env python3
"""
ODIN v9.2 GPU Billion-Parameter Optimization
=============================================
Optimized for NVIDIA RTX 4070 (12GB VRAM, 5888 CUDA cores)

Usage:
    python odin_v92_gpu_optimizer.py

Requirements:
    pip install cupy-cuda12x pandas numpy tqdm

Expected runtime: ~15-30 minutes for 1 billion configurations
"""

import numpy as np
import pandas as pd
import json
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Try to import CuPy for GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
    device = cp.cuda.Device()
    mem_info = device.mem_info
    print(f"✅ CuPy detected - GPU acceleration enabled")
    print(f"   Device ID: {device.id}")
    print(f"   Memory: {mem_info[1] / 1e9:.1f} GB total, {mem_info[0] / 1e9:.1f} GB free")
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️ CuPy not found - falling back to CPU (slower)")
    cp = np  # Fallback to numpy

# =============================================================================
# CONFIGURATION
# =============================================================================

# Optimization settings
TOTAL_CONFIGS = 1_000_000_000  # 1 billion configurations
CHECKPOINT_INTERVAL = 100_000_000  # Save progress every 100M configs
MEMORY_CHECK_INTERVAL = 100_000_000  # Re-check memory every 100M configs
MEMORY_SAFETY_FACTOR = 0.60  # Use only 60% of free memory to be safe
MIN_BATCH_SIZE = 50_000  # Minimum batch size
MAX_BATCH_SIZE = 5_000_000  # Maximum batch size

def get_optimal_batch_size(n_events: int, n_params: int = 25) -> int:
    """
    Calculate optimal batch size based on available GPU memory.
    
    Memory estimation per config:
    - params array: n_params × 4 bytes
    - probs array: n_events × 4 bytes (this is the big one)
    - masks and intermediates: ~n_events × 4 × 15 bytes
    - overhead factor: 2x for safety
    
    Args:
        n_events: Number of PDUFA events in dataset
        n_params: Number of parameters being optimized
    
    Returns:
        Optimal batch size
    """
    if not GPU_AVAILABLE:
        return 100_000  # Conservative CPU batch size
    
    # Get current free memory
    device = cp.cuda.Device()
    free_mem, total_mem = device.mem_info
    
    # Calculate memory per config (in bytes)
    # Main cost: probs array (batch_size × n_events × 4)
    # Plus various masks and intermediates
    bytes_per_config = n_events * 4 * 20  # 20x factor for all arrays + overhead
    
    # Calculate safe batch size
    usable_memory = free_mem * MEMORY_SAFETY_FACTOR
    optimal_batch = int(usable_memory / bytes_per_config)
    
    # Clamp to reasonable bounds
    batch_size = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, optimal_batch))
    
    # Round down to nearest 10,000 for cleaner numbers
    batch_size = (batch_size // 10_000) * 10_000
    
    return max(MIN_BATCH_SIZE, batch_size)

def check_and_report_memory(context: str = "") -> Tuple[float, float, int]:
    """
    Check GPU memory and report status.
    
    Returns:
        Tuple of (free_gb, total_gb, recommended_batch_size)
    """
    if not GPU_AVAILABLE:
        return 0, 0, 100_000
    
    device = cp.cuda.Device()
    free_mem, total_mem = device.mem_info
    free_gb = free_mem / 1e9
    total_gb = total_mem / 1e9
    
    # Clear any cached memory
    cp.get_default_memory_pool().free_all_blocks()
    
    # Re-check after clearing
    free_mem, total_mem = device.mem_info
    free_gb = free_mem / 1e9
    
    batch_size = get_optimal_batch_size(1349)
    
    if context:
        print(f"  💾 Memory check ({context}): {free_gb:.1f} GB free, batch size → {batch_size:,}")
    
    return free_gb, total_gb, batch_size

# Parameter bounds for optimization
PARAM_BOUNDS = {
    # Designation weights
    'btd_weight': (0.02, 0.12),
    'orphan_weight': (0.01, 0.08),
    'priority_review_weight': (0.02, 0.10),
    'fast_track_weight': (0.01, 0.06),
    'accelerated_approval_weight': (0.01, 0.06),
    
    # Stack interactions (NEW in v9.2)
    'no_designation_penalty': (-0.10, -0.02),
    'btd_pr_synergy_bonus': (0.04, 0.15),
    'btd_alone_bonus': (0.03, 0.12),
    'full_stack_bonus': (0.02, 0.08),
    
    # AdCom
    'adcom_high_boost': (0.04, 0.15),
    'adcom_mid_penalty': (-0.12, -0.02),
    'adcom_low_penalty': (-0.25, -0.08),
    
    # Prior CRL
    'prior_crl_penalty': (-0.18, -0.05),
    'class1_resubmission_boost': (0.08, 0.22),
    'class2_resubmission_penalty': (-0.12, -0.02),
    
    # Sponsor experience (NEW non-linear in v9.2)
    'sponsor_one_approval_penalty': (-0.10, -0.02),
    'sponsor_sweet_spot_boost': (0.04, 0.15),
    'sponsor_mid_tier_penalty': (-0.08, 0.0),
    'sponsor_large_pharma_boost': (0.02, 0.10),
    
    # Manufacturing
    'form_483_penalty': (-0.15, -0.03),
    
    # TA adjustment
    'ta_adjustment_weight': (0.6, 1.2),
    
    # Temporal (NEW in v9.2)
    'temporal_2024_plus_boost': (0.01, 0.08),
    
    # Tier thresholds
    'tier1_threshold': (0.82, 0.92),
    'tier2_threshold': (0.68, 0.80),
    'tier3_threshold': (0.52, 0.65),
}

# Therapeutic area adjustments (fixed, from historical data)
TA_ADJUSTMENTS = {
    "Pain Management": -0.286,
    "Hematology": -0.224,
    "Nephrology": -0.177,
    "Ophthalmology": -0.131,
    "CNS/Neurology": -0.098,
    "Cardiovascular": -0.081,
    "Metabolic/Endocrine": -0.067,
    "Rare Disease": -0.043,
    "Other": -0.019,
    "Immunology": 0.016,
    "Dermatology": 0.028,
    "Oncology": 0.061,
    "GI/Hepatology": 0.067,
    "Respiratory": 0.090,
    "Infectious Disease": 0.103,
    "Vaccines": 0.133,
    "Women's Health": 0.133,
}

# Modality-specific manufacturing risk penalties
MODALITY_MFG_PENALTIES = {
    "Small Molecule": -0.45,
    "Antibody": -0.15,
    "Cell/Gene Therapy": -0.08,
    "RNA Therapy": -0.08,
    "Peptide": -0.12,
    "Vaccine": -0.05,
    "ADC": -0.12,
}

# =============================================================================
# DATA PREPARATION
# =============================================================================

def load_and_prepare_data(filepath: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Load dataset and convert to GPU-friendly arrays."""
    
    df = pd.read_csv(filepath, encoding='utf-8', encoding_errors='replace')
    n_events = len(df)
    
    print(f"\nLoading dataset: {n_events} events")
    
    # Create outcome array (1 = approved, 0 = CRL)
    outcomes = df['outcome'].apply(
        lambda x: 1.0 if str(x).upper() in ['APPROVED', 'APPROVAL'] else 0.0
    ).values.astype(np.float32)
    
    # Create feature matrix
    # Columns: [btd, orphan, pr, ft, aa, had_adcom, adcom_vote, prior_crl, 
    #           resub_class, sponsor_approvals, mfg_risk, form_483, 
    #           ta_idx, modality_idx, year, first_cycle]
    
    # Map TAs to indices
    ta_list = list(TA_ADJUSTMENTS.keys())
    ta_to_idx = {ta: i for i, ta in enumerate(ta_list)}
    ta_adjustments_array = np.array([TA_ADJUSTMENTS[ta] for ta in ta_list], dtype=np.float32)
    
    # Map modalities to indices
    modality_list = list(MODALITY_MFG_PENALTIES.keys())
    mod_to_idx = {mod: i for i, mod in enumerate(modality_list)}
    mod_penalties_array = np.array([MODALITY_MFG_PENALTIES[mod] for mod in modality_list], dtype=np.float32)
    
    features = np.zeros((n_events, 16), dtype=np.float32)
    
    for i, row in df.iterrows():
        features[i, 0] = float(row.get('btd', False) == True)
        features[i, 1] = float(row.get('orphan', False) == True)
        features[i, 2] = float(row.get('priority_review', False) == True)
        features[i, 3] = float(row.get('fast_track', False) == True)
        features[i, 4] = float(str(row.get('accelerated_approval', '')).lower() == 'true')
        features[i, 5] = float(row.get('had_adcom', False) == True)
        features[i, 6] = float(row.get('adcom_vote_pct', 0) or 0)
        features[i, 7] = float(row.get('prior_crl', False) == True)
        features[i, 8] = float(row.get('resubmission_class', 0) or 0)
        features[i, 9] = float(row.get('sponsor_prior_approvals', 0) or 0)
        features[i, 10] = float(row.get('manufacturing_risk', False) == True)
        features[i, 11] = float(row.get('form_483_issues', False) == True)
        
        ta = row.get('therapeutic_area', 'Other')
        features[i, 12] = ta_to_idx.get(ta, ta_to_idx['Other'])
        
        mod = row.get('modality', 'Small Molecule')
        features[i, 13] = mod_to_idx.get(mod, mod_to_idx['Small Molecule'])
        
        features[i, 14] = float(row.get('year', 2023))
        features[i, 15] = float(row.get('first_cycle', True) == True)
    
    metadata = {
        'n_events': n_events,
        'n_crls': int((outcomes == 0).sum()),
        'ta_adjustments': ta_adjustments_array,
        'mod_penalties': mod_penalties_array,
        'ta_list': ta_list,
        'modality_list': modality_list,
    }
    
    print(f"  Approvals: {int(outcomes.sum())}")
    print(f"  CRLs: {metadata['n_crls']}")
    
    return features, outcomes, metadata


# =============================================================================
# GPU SCORING KERNEL
# =============================================================================

def batch_score_gpu(features, outcomes, params, metadata):
    """
    Score all events with a batch of parameter configurations.
    
    Args:
        features: (n_events, 16) array on GPU
        outcomes: (n_events,) array on GPU
        params: (batch_size, n_params) array on GPU
        metadata: dict with TA/modality arrays
        
    Returns:
        brier_scores: (batch_size,) array
        tier4_crl_rates: (batch_size,) array
        tier4_counts: (batch_size,) array
    """
    xp = cp if GPU_AVAILABLE else np
    
    batch_size = params.shape[0]
    n_events = features.shape[0]
    
    # Extract parameters (batch_size, 1) for broadcasting
    btd_w = params[:, 0:1]
    orphan_w = params[:, 1:2]
    pr_w = params[:, 2:3]
    ft_w = params[:, 3:4]
    aa_w = params[:, 4:5]
    no_desig_pen = params[:, 5:6]
    btd_pr_syn = params[:, 6:7]
    btd_alone = params[:, 7:8]
    full_stack = params[:, 8:9]
    adcom_high = params[:, 9:10]
    adcom_mid = params[:, 10:11]
    adcom_low = params[:, 11:12]
    prior_crl_pen = params[:, 12:13]
    class1_boost = params[:, 13:14]
    class2_pen = params[:, 14:15]
    sponsor_one_pen = params[:, 15:16]
    sponsor_sweet = params[:, 16:17]
    sponsor_mid_pen = params[:, 17:18]
    sponsor_large = params[:, 18:19]
    form_483_pen = params[:, 19:20]
    ta_weight = params[:, 20:21]
    temporal_boost = params[:, 21:22]
    tier1_thresh = params[:, 22:23]
    tier2_thresh = params[:, 23:24]
    tier3_thresh = params[:, 24:25]
    
    # Extract features (1, n_events) for broadcasting
    f_btd = features[:, 0:1].T
    f_orphan = features[:, 1:2].T
    f_pr = features[:, 2:3].T
    f_ft = features[:, 3:4].T
    f_aa = features[:, 4:5].T
    f_adcom = features[:, 5:6].T
    f_adcom_vote = features[:, 6:7].T
    f_prior_crl = features[:, 7:8].T
    f_resub_class = features[:, 8:9].T
    f_sponsor_approvals = features[:, 9:10].T
    f_mfg_risk = features[:, 10:11].T
    f_form_483 = features[:, 11:12].T
    f_ta_idx = features[:, 12].astype(xp.int32)
    f_mod_idx = features[:, 13].astype(xp.int32)
    f_year = features[:, 14:15].T
    
    # Get TA and modality adjustments
    ta_adj_array = xp.asarray(metadata['ta_adjustments'])
    mod_pen_array = xp.asarray(metadata['mod_penalties'])
    
    # Base probability
    base = 0.867
    
    # Calculate probabilities (batch_size, n_events)
    probs = xp.full((batch_size, n_events), base, dtype=xp.float32)
    
    # 1. Designation weights
    probs += btd_w * f_btd
    probs += orphan_w * f_orphan
    probs += pr_w * f_pr
    probs += ft_w * f_ft
    probs += aa_w * f_aa
    
    # 2. Stack interactions
    no_desig_mask = (f_btd == 0) & (f_orphan == 0) & (f_pr == 0) & (f_ft == 0)
    btd_pr_mask = (f_btd == 1) & (f_pr == 1) & (f_orphan == 0)
    btd_alone_mask = (f_btd == 1) & (f_orphan == 0) & (f_pr == 0)
    full_stack_mask = (f_btd == 1) & (f_orphan == 1) & (f_pr == 1) & (f_ft == 1)
    
    probs += no_desig_pen * no_desig_mask
    probs += btd_pr_syn * btd_pr_mask
    probs += btd_alone * btd_alone_mask
    probs += full_stack * full_stack_mask
    
    # 3. AdCom adjustments
    adcom_high_mask = (f_adcom == 1) & (f_adcom_vote >= 0.65)
    adcom_mid_mask = (f_adcom == 1) & (f_adcom_vote >= 0.50) & (f_adcom_vote < 0.65)
    adcom_low_mask = (f_adcom == 1) & (f_adcom_vote < 0.50) & (f_adcom_vote > 0)
    
    probs += adcom_high * adcom_high_mask
    probs += adcom_mid * adcom_mid_mask
    probs += adcom_low * adcom_low_mask
    
    # 4. Prior CRL / Resubmission
    probs += prior_crl_pen * f_prior_crl
    class1_mask = (f_prior_crl == 1) & (f_resub_class == 1)
    class2_mask = (f_prior_crl == 1) & (f_resub_class == 2)
    probs += class1_boost * class1_mask
    probs += class2_pen * class2_mask
    
    # 5. Sponsor experience (non-linear)
    sponsor_one_mask = (f_sponsor_approvals == 1)
    sponsor_sweet_mask = (f_sponsor_approvals >= 2) & (f_sponsor_approvals <= 3)
    sponsor_mid_mask = (f_sponsor_approvals >= 4) & (f_sponsor_approvals <= 10)
    sponsor_large_mask = (f_sponsor_approvals > 10)
    
    probs += sponsor_one_pen * sponsor_one_mask
    probs += sponsor_sweet * sponsor_sweet_mask
    probs += sponsor_mid_pen * sponsor_mid_mask
    probs += sponsor_large * sponsor_large_mask
    
    # 6. Manufacturing risk (modality-specific)
    # mod_penalties: (n_events,) - penalty for each event based on modality
    # f_mfg_risk: (1, n_events) - broadcasts with (batch_size, n_events)
    mod_penalties = mod_pen_array[f_mod_idx]  # (n_events,)
    probs += f_mfg_risk * mod_penalties  # (1, n_events) broadcasts to (batch_size, n_events)
    
    # 7. Form 483
    probs += form_483_pen * f_form_483
    
    # 8. TA adjustment
    # ta_adjustments: (n_events,) - adjustment for each event based on therapeutic area
    # ta_weight: (batch_size, 1) - multiplier varies per config
    ta_adjustments = ta_adj_array[f_ta_idx]  # (n_events,)
    probs += ta_weight * ta_adjustments  # (batch_size, 1) * (n_events,) = (batch_size, n_events)
    
    # 9. Temporal adjustment
    year_2024_plus = (f_year >= 2024)
    probs += temporal_boost * year_2024_plus
    
    # Clamp probabilities
    probs = xp.clip(probs, 0.01, 0.99)
    
    # Calculate Brier scores
    outcomes_gpu = xp.asarray(outcomes)
    brier = xp.mean((probs - outcomes_gpu) ** 2, axis=1)
    
    # Calculate tier assignments and TIER_4 metrics
    tier4_mask = probs < tier3_thresh  # (batch_size, n_events)
    tier4_counts = xp.sum(tier4_mask, axis=1)
    
    # TIER_4 CRL rate
    crl_mask = (outcomes_gpu == 0)
    tier4_crls = xp.sum(tier4_mask & crl_mask, axis=1)
    tier4_crl_rate = xp.where(tier4_counts > 0, tier4_crls / tier4_counts, 0.0)
    
    # CRL recall at 85%
    crl_events = xp.sum(crl_mask)
    detected_crls = xp.sum((probs < 0.85) & crl_mask, axis=1)
    crl_recall = detected_crls / crl_events if crl_events > 0 else 0.0
    
    return brier, tier4_crl_rate, tier4_counts, crl_recall


# =============================================================================
# OPTIMIZATION LOOP
# =============================================================================

def generate_random_params(batch_size: int) -> np.ndarray:
    """Generate random parameter configurations within bounds."""
    param_names = list(PARAM_BOUNDS.keys())
    n_params = len(param_names)
    
    params = np.zeros((batch_size, n_params), dtype=np.float32)
    
    for i, name in enumerate(param_names):
        low, high = PARAM_BOUNDS[name]
        params[:, i] = np.random.uniform(low, high, batch_size)
    
    return params


def run_optimization(features, outcomes, metadata, total_configs=TOTAL_CONFIGS):
    """Run billion-parameter optimization with dynamic memory management."""
    
    xp = cp if GPU_AVAILABLE else np
    n_events = features.shape[0]
    
    # Initial memory check and batch size calculation
    print(f"\n{'='*70}")
    print(f"MEMORY INITIALIZATION")
    print(f"{'='*70}")
    
    if GPU_AVAILABLE:
        # Clear any existing GPU memory
        cp.get_default_memory_pool().free_all_blocks()
        
    free_gb, total_gb, current_batch_size = check_and_report_memory("initial")
    print(f"  📊 Initial batch size: {current_batch_size:,}")
    
    # Move data to GPU
    features_gpu = xp.asarray(features)
    outcomes_gpu = xp.asarray(outcomes)
    
    # Re-check after loading data
    _, _, current_batch_size = check_and_report_memory("after data load")
    
    # Best results tracking
    best_brier = float('inf')
    best_params = None
    best_metrics = None
    
    # Top 10 tracker
    top_configs = []
    
    configs_processed = 0
    start_time = time.time()
    last_memory_check = 0
    
    print(f"\n{'='*70}")
    print(f"STARTING OPTIMIZATION")
    print(f"{'='*70}")
    print(f"Total configs: {total_configs:,}")
    print(f"Initial batch size: {current_batch_size:,}")
    print(f"Parameters: {len(PARAM_BOUNDS)}")
    print(f"Memory check interval: every {MEMORY_CHECK_INTERVAL/1e6:.0f}M configs")
    print(f"{'='*70}\n")
    
    batch_idx = 0
    
    while configs_processed < total_configs:
        # Check memory and adjust batch size periodically
        if configs_processed - last_memory_check >= MEMORY_CHECK_INTERVAL:
            if GPU_AVAILABLE:
                cp.get_default_memory_pool().free_all_blocks()
            _, _, new_batch_size = check_and_report_memory(f"{configs_processed/1e6:.0f}M configs")
            
            if new_batch_size != current_batch_size:
                print(f"  ⚡ Batch size adjusted: {current_batch_size:,} → {new_batch_size:,}")
                current_batch_size = new_batch_size
            
            last_memory_check = configs_processed
        
        # Calculate actual batch size for this iteration
        remaining = total_configs - configs_processed
        actual_batch_size = min(current_batch_size, remaining)
        
        try:
            # Generate random parameters
            params = generate_random_params(actual_batch_size)
            params_gpu = xp.asarray(params)
            
            # Score all configs
            brier, tier4_crl, tier4_count, crl_recall = batch_score_gpu(
                features_gpu, outcomes_gpu, params_gpu, metadata
            )
            
            # Move results to CPU
            if GPU_AVAILABLE:
                brier_cpu = brier.get()
                tier4_crl_cpu = tier4_crl.get()
                tier4_count_cpu = tier4_count.get()
                crl_recall_cpu = crl_recall.get()
                
                # Clean up GPU memory
                del params_gpu, brier, tier4_crl, tier4_count, crl_recall
            else:
                brier_cpu = brier
                tier4_crl_cpu = tier4_crl
                tier4_count_cpu = tier4_count
                crl_recall_cpu = crl_recall
            
            # Find feasible configs (TIER_4 count >= 10, CRL rate >= 70%)
            feasible_mask = (tier4_count_cpu >= 10) & (tier4_crl_cpu >= 0.70)
            feasible_indices = np.where(feasible_mask)[0]
            
            # Update best
            if len(feasible_indices) > 0:
                feasible_brier = brier_cpu[feasible_indices]
                best_idx_in_feasible = np.argmin(feasible_brier)
                best_idx = feasible_indices[best_idx_in_feasible]
                
                if brier_cpu[best_idx] < best_brier:
                    best_brier = brier_cpu[best_idx]
                    best_params = params[best_idx].copy()
                    best_metrics = {
                        'brier': float(brier_cpu[best_idx]),
                        'tier4_crl_rate': float(tier4_crl_cpu[best_idx]),
                        'tier4_count': int(tier4_count_cpu[best_idx]),
                        'crl_recall': float(crl_recall_cpu[best_idx]),
                    }
                    
                    print(f"  🎯 NEW BEST at {configs_processed/1e6:.1f}M: Brier={best_brier:.5f}, "
                          f"T4_CRL={best_metrics['tier4_crl_rate']*100:.1f}%, "
                          f"T4_N={best_metrics['tier4_count']}")
                
                # Track top 10
                for idx in feasible_indices[:min(100, len(feasible_indices))]:
                    config_data = {
                        'params': params[idx].copy(),
                        'brier': float(brier_cpu[idx]),
                        'tier4_crl': float(tier4_crl_cpu[idx]),
                        'tier4_count': int(tier4_count_cpu[idx]),
                        'crl_recall': float(crl_recall_cpu[idx]),
                    }
                    top_configs.append(config_data)
                
                # Keep only top 10
                top_configs.sort(key=lambda x: x['brier'])
                top_configs = top_configs[:10]
            
            configs_processed += actual_batch_size
            batch_idx += 1
            
            # Progress update
            if batch_idx % 10 == 0 or batch_idx == 1:
                elapsed = time.time() - start_time
                rate = configs_processed / elapsed
                eta = (total_configs - configs_processed) / rate if rate > 0 else 0
                pct_complete = configs_processed / total_configs * 100
                
                print(f"[{pct_complete:5.1f}%] {configs_processed/1e6:.1f}M configs, "
                      f"batch={actual_batch_size:,}, "
                      f"{rate/1e6:.2f}M/sec, "
                      f"ETA: {eta/60:.1f}min, "
                      f"feasible: {len(feasible_indices)}")
            
            # Checkpoint
            if configs_processed % CHECKPOINT_INTERVAL == 0 and best_params is not None:
                save_checkpoint(best_params, best_metrics, top_configs, configs_processed)
                
        except cp.cuda.memory.OutOfMemoryError:
            # Handle OOM by reducing batch size
            print(f"  ⚠️ OOM detected! Reducing batch size from {current_batch_size:,}")
            current_batch_size = max(MIN_BATCH_SIZE, current_batch_size // 2)
            print(f"  ⚠️ New batch size: {current_batch_size:,}")
            
            # Clear GPU memory and retry
            if GPU_AVAILABLE:
                cp.get_default_memory_pool().free_all_blocks()
            continue
    
    return best_params, best_metrics, top_configs


def save_checkpoint(best_params, best_metrics, top_configs, configs_processed):
    """Save optimization checkpoint."""
    
    param_names = list(PARAM_BOUNDS.keys())
    
    checkpoint = {
        'timestamp': datetime.now().isoformat(),
        'configs_processed': configs_processed,
        'best_metrics': best_metrics,
        'best_params': {name: float(best_params[i]) for i, name in enumerate(param_names)},
        'top_10': [
            {
                'rank': i+1,
                'brier': cfg['brier'],
                'tier4_crl': cfg['tier4_crl'],
                'tier4_count': cfg['tier4_count'],
                'params': {name: float(cfg['params'][j]) for j, name in enumerate(param_names)},
            }
            for i, cfg in enumerate(top_configs)
        ]
    }
    
    filepath = f'odin_v92_checkpoint_{configs_processed//1e6:.0f}M.json'
    with open(filepath, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"  💾 Checkpoint saved: {filepath}")


def save_champion_config(best_params, best_metrics):
    """Save final champion configuration."""
    
    param_names = list(PARAM_BOUNDS.keys())
    
    config = {
        'version': '9.2',
        'optimization': {
            'method': 'GPU_random_search',
            'configs_tested': TOTAL_CONFIGS,
            'timestamp': datetime.now().isoformat(),
        },
        'performance': best_metrics,
        'champion_params': {name: float(best_params[i]) for i, name in enumerate(param_names)},
        'therapeutic_area_adjustments': TA_ADJUSTMENTS,
        'modality_mfg_penalties': MODALITY_MFG_PENALTIES,
    }
    
    filepath = 'ODIN_v92_CHAMPION_CONFIG.json'
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Champion config saved: {filepath}")
    return filepath


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("ODIN v9.2 GPU BILLION-PARAMETER OPTIMIZER")
    print("=" * 70)
    print(f"Target: {TOTAL_CONFIGS/1e9:.1f} billion configurations")
    print(f"GPU: {'ENABLED' if GPU_AVAILABLE else 'DISABLED (CPU fallback)'}")
    print("=" * 70)
    
    # Load data
    # Try project path first, then local
    try:
        features, outcomes, metadata = load_and_prepare_data(
            '/mnt/project/ODIN_ENRICHED_PDUFA_1349_v2.csv'
        )
    except:
        features, outcomes, metadata = load_and_prepare_data(
            'ODIN_ENRICHED_PDUFA_1349_v2.csv'
        )
    
    # Run optimization
    best_params, best_metrics, top_configs = run_optimization(
        features, outcomes, metadata, TOTAL_CONFIGS
    )
    
    # Save results
    if best_params is not None:
        champion_file = save_champion_config(best_params, best_metrics)
        
        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETE")
        print("=" * 70)
        print(f"\nBest Configuration:")
        print(f"  Brier Score: {best_metrics['brier']:.5f}")
        print(f"  TIER_4 CRL Rate: {best_metrics['tier4_crl_rate']*100:.1f}%")
        print(f"  TIER_4 Count: {best_metrics['tier4_count']}")
        print(f"  CRL Recall: {best_metrics['crl_recall']*100:.1f}%")
        
        print(f"\nTop 10 Configurations:")
        for i, cfg in enumerate(top_configs[:10]):
            print(f"  #{i+1}: Brier={cfg['brier']:.5f}, T4_CRL={cfg['tier4_crl']*100:.1f}%")
    else:
        print("\n⚠️ No feasible configurations found!")
