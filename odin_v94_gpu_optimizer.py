#!/usr/bin/env python3
"""
ODIN v9.4 GPU Optimizer - Billion-Parameter Search with CuPy
=============================================================
Optimized for RTX 4070 (12GB VRAM, 5888 CUDA cores)

Key Changes from v9.3:
- NEW: Prior CRL count multiplier (2 CRLs = 1.4x penalty)
- NEW: Modality-indication interaction matrix
- NEW: Indication-specific overrides (RCKT calibrated)
- FIX: Class 2 resubmission changed to BOOST (+0.04)
- NEW: Enhanced modality complexity weights
- NEW: Improvement logger (tracks every config that beats previous best)

Features:
- Dynamic VRAM auto-tuning for any GPU
- Streaming metrics computation (no full C×N matrices)
- OOM backoff with automatic batch/chunk reduction
- Checkpoint/resume capability
- Progress logging with ETA
- Top-K tracking for config diversity

Usage:
    python odin_v94_gpu_optimizer.py --configs 1000000000 --batch-size 2500000
    python odin_v94_gpu_optimizer.py --configs 100000000 --quick  # Quick scan
    python odin_v94_gpu_optimizer.py --resume checkpoint.npz     # Resume

Author: ODIN Development Team
Version: 9.4.0
Date: 2026-01-29
"""

import numpy as np
import pandas as pd
import json
import time
import math
import argparse
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')

# Try to import CuPy for GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
    print(f"✅ CuPy detected - GPU acceleration enabled")
    dev_id = cp.cuda.Device().id
    props = cp.cuda.runtime.getDeviceProperties(dev_id)
    gpu_name = props['name'].decode('utf-8')
    vram_total = props['totalGlobalMem'] / (1024**3)
    print(f"   Device: {gpu_name}")
    print(f"   VRAM: {vram_total:.1f} GB")
    mempool = cp.get_default_memory_pool()
    pinned_mempool = cp.get_default_pinned_memory_pool()
except ImportError:
    GPU_AVAILABLE = False
    cp = np  # Fallback to NumPy
    mempool = None
    pinned_mempool = None
    print("⚠️ CuPy not available - using CPU (NumPy)")


# =============================================================================
# UTILITIES (PROGRESS LOGGING + MEMORY AUTO-TUNING)
# =============================================================================

def _format_bytes(n: int) -> str:
    """Human-readable bytes."""
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:,.1f}{unit}" if unit != "B" else f"{n:,.0f}{unit}"
        n /= 1024.0
    return f"{n:,.1f}PB"


def _gpu_mem_info() -> Tuple[int, int]:
    """Return (free_bytes, total_bytes) for the active CUDA device."""
    if not GPU_AVAILABLE:
        return (0, 0)
    free_b, total_b = cp.cuda.runtime.memGetInfo()
    return int(free_b), int(total_b)


def _append_log(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for the GPU optimizer."""
    # Search parameters
    total_configs: int = 1_000_000_000
    batch_size: int = 2_500_000  # Upper bound; auto-tuned at runtime
    event_chunk_size: int = 128  # Auto-tuned with batch_size
    progress_log_every: int = 10_000_000  # Log every N configs tested
    topk_update_every: Optional[int] = None
    disable_topk: bool = False
    
    # Objectives and constraints (relaxed from v9.3 per Perplexity recommendations)
    primary_objective: str = 'brier'
    min_tier4_count: int = 15  # Relaxed from 20
    min_tier4_crl_rate: float = 0.50  # Relaxed from 0.70
    min_crl_recall: float = 0.55  # Relaxed from 0.60
    
    # Checkpoint settings
    checkpoint_interval: int = 50
    checkpoint_path: str = 'odin_v94_checkpoint.npz'
    
    # Output settings
    output_dir: str = os.path.join(os.getcwd(), 'odin_output')
    champion_config_path: str = 'ODIN_v94_CHAMPION_CONFIG.json'
    results_path: str = 'odin_v94_optimization_results.csv'
    improvement_log_path: str = 'odin_v94_improvements.log'


# =============================================================================
# v9.4 PARAMETER BOUNDS (25 parameters - expanded from v9.3's 19)
# =============================================================================

PARAMETER_BOUNDS = {
    # Designation weights (same as v9.1/9.3)
    'btd_weight': (0.02, 0.12),
    'orphan_weight': (0.01, 0.08),
    'priority_review_weight': (0.03, 0.15),
    'fast_track_weight': (0.01, 0.06),
    'accelerated_approval_weight': (0.02, 0.08),
    
    # AdCom adjustments
    'adcom_high_boost': (0.04, 0.15),
    'adcom_mid_penalty': (-0.12, 0.0),
    'adcom_low_penalty': (-0.25, -0.10),
    
    # Prior CRL / Resubmission (v9.4 changes)
    'prior_crl_base_penalty': (-0.15, -0.04),
    'crl_count_multiplier_2': (1.2, 1.8),   # NEW: multiplier for 2 CRLs
    'crl_count_multiplier_3': (1.5, 2.2),   # NEW: multiplier for 3 CRLs
    'crl_count_multiplier_4plus': (1.8, 2.8),  # NEW: multiplier for 4+ CRLs
    'class1_resubmission_boost': (0.10, 0.22),
    'class2_resubmission_boost': (0.02, 0.08),  # CHANGED: now a boost, not penalty
    
    # Sponsor experience
    'experienced_sponsor_boost': (0.02, 0.10),
    'inexperienced_sponsor_penalty': (-0.12, -0.03),
    
    # Modality adjustments (direct, not complexity-weighted)
    'gene_therapy_penalty': (-0.12, -0.02),  # NEW: direct modality
    'cell_therapy_penalty': (-0.10, -0.01),
    'rna_therapy_penalty': (-0.10, -0.01),
    
    # Modality-indication interaction weights (NEW in v9.4)
    'modality_indication_weight': (0.3, 1.2),  # Scales interaction matrix
    
    # Therapeutic area adjustment
    'ta_adjustment_weight': (0.6, 1.1),
    
    # Indication override weight (NEW)
    'indication_override_weight': (0.5, 1.5),
    
    # Tier thresholds
    'tier1_threshold': (0.82, 0.92),
    'tier2_threshold': (0.68, 0.80),
    'tier3_threshold': (0.52, 0.65),
}

PARAMETER_NAMES = list(PARAMETER_BOUNDS.keys())
N_PARAMS = len(PARAMETER_NAMES)

# Therapeutic area adjustments (fixed, from v9.1 historical data)
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

# v9.4 Modality complexity (T-1 compliant - inherent process difficulty)
MODALITY_ADJUSTMENTS = {
    "Small Molecule": 0.00,
    "Peptide": -0.01,
    "Antibody": -0.02,
    "ADC": -0.04,
    "Vaccine": +0.02,
    "Biosimilar": +0.03,
    "RNA Therapy": -0.05,  # Direct penalty
    "Cell Therapy": -0.05,
    "Cell/Gene Therapy": -0.06,
    "Gene Therapy": -0.06,  # RCKT calibrated
}

# v9.4 Modality-Indication Interaction Matrix (NEW)
# Format: (modality_contains, indication_contains) -> penalty
MODALITY_INDICATION_INTERACTIONS = {
    ("Gene", "Rare Disease"): -0.04,
    ("Gene", "Hematology"): -0.05,
    ("Gene", "CNS"): -0.04,
    ("Gene", "Neurology"): -0.04,
    ("Cell", "Rare Disease"): -0.03,
    ("Cell", "Hematology"): -0.04,
    ("Small Molecule", "Pain"): -0.04,
    ("Antibody", "CNS"): -0.02,
    ("Antibody", "Neurology"): -0.02,
    ("RNA", "Rare Disease"): -0.03,
}

# v9.4 Indication-specific overrides (RCKT calibrated)
INDICATION_OVERRIDES = {
    # HIGH RISK (genetic/blood disorders)
    "leukocyte adhesion deficiency": -0.05,
    "lad-i": -0.05,
    "sickle cell": -0.04,
    "beta-thalassemia": -0.04,
    "myelodysplastic": -0.03,
    "acute myeloid leukemia": -0.03,
    
    # HIGH RISK (pain)
    "opioid use disorder": -0.05,
    "opioid-induced constipation": -0.04,
    "chronic pain": -0.04,
    "postoperative pain": -0.05,
    
    # HIGH RISK (kidney)
    "diabetic kidney": -0.04,
    "iga nephropathy": -0.04,
    "lupus nephritis": -0.03,
    
    # HIGH RISK (eye)
    "dry eye": -0.03,
    "diabetic macular edema": -0.03,
    "geographic atrophy": -0.03,
    
    # LOW RISK (favorable indications)
    "spinal muscular atrophy": +0.02,
    "nsclc": +0.01,
    "breast cancer": +0.01,
    "melanoma": +0.01,
    "multiple myeloma": +0.01,
}


# =============================================================================
# DATA LOADING AND PREPROCESSING
# =============================================================================

def load_and_preprocess_data(csv_path: str) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Load PDUFA dataset and convert to GPU-ready arrays."""
    csv_path = os.path.expanduser(os.path.expandvars(csv_path))
    
    # Try multiple locations
    if not os.path.exists(csv_path):
        candidates = [
            csv_path,
            os.path.join(os.getcwd(), os.path.basename(csv_path)),
            os.path.join(os.path.dirname(__file__), os.path.basename(csv_path)),
        ]
        common = [
            'ODIN_ENRICHED_PDUFA_1349_v2.csv',
            'ODIN_ENRICHED_PDUFA_1904_v4.csv',
            'ODIN_v4_FIXED_DATASET.csv',
        ]
        for fname in common:
            candidates.append(os.path.join(os.getcwd(), fname))
            candidates.append(os.path.join(os.path.dirname(__file__), fname))
        
        for c in candidates:
            if os.path.exists(c):
                csv_path = c
                break
        else:
            raise FileNotFoundError(f"Could not find dataset CSV: {csv_path}")
    
    print(f"\n📂 Loading data from {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')
    print(f"   Loaded {len(df)} events")
    
    # Encode outcome
    df['outcome_binary'] = df['outcome'].str.upper().isin(['APPROVED', 'APPROVAL']).astype(int)
    
    # Encode therapeutic area to index
    ta_list = list(TA_ADJUSTMENTS.keys())
    df['ta_idx'] = df['therapeutic_area'].apply(
        lambda x: ta_list.index(x) if x in ta_list else ta_list.index('Other')
    )
    
    # Encode modality to direct adjustment
    df['modality_adj'] = df['modality'].map(MODALITY_ADJUSTMENTS).fillna(0.0)
    
    # Check modality type for interactions
    df['modality_lower'] = df['modality'].str.lower().fillna('')
    df['is_gene_therapy'] = df['modality_lower'].str.contains('gene').astype(np.float32)
    df['is_cell_therapy'] = df['modality_lower'].str.contains('cell').astype(np.float32)
    df['is_rna_therapy'] = df['modality_lower'].str.contains('rna').astype(np.float32)
    
    # Compute modality-indication interaction score
    df['indication_lower'] = df['indication'].str.lower().fillna('')
    df['ta_lower'] = df['therapeutic_area'].str.lower().fillna('')
    
    def compute_interaction(row):
        """Compute modality-indication interaction penalty."""
        total = 0.0
        modality = row['modality_lower']
        indication = row['indication_lower']
        ta = row['ta_lower']
        
        for (mod_key, ind_key), penalty in MODALITY_INDICATION_INTERACTIONS.items():
            mod_match = mod_key.lower() in modality
            ind_match = ind_key.lower() in indication or ind_key.lower() in ta
            if mod_match and ind_match:
                total += penalty
        return total
    
    df['interaction_penalty'] = df.apply(compute_interaction, axis=1)
    
    # Compute indication override score
    def compute_indication_override(indication):
        indication = str(indication).lower()
        for k, v in INDICATION_OVERRIDES.items():
            if k.lower() in indication:
                return v
        return 0.0
    
    df['indication_override'] = df['indication'].apply(compute_indication_override)
    
    # Count prior CRLs (new in v9.4 - need to infer from data or add column)
    # For now, use prior_crl as boolean; dataset may have crl_count column
    if 'prior_crl_count' not in df.columns:
        df['prior_crl_count'] = df['prior_crl'].fillna(False).astype(int)
    
    # Build feature matrix (expanded for v9.4)
    # Order matters - matches parameter extraction in scoring kernel
    features = np.column_stack([
        df['btd'].fillna(False).astype(bool).astype(np.float32).values,                    # 0
        df['orphan'].fillna(False).astype(bool).astype(np.float32).values,                 # 1
        df['priority_review'].fillna(False).astype(bool).astype(np.float32).values,        # 2
        df['fast_track'].fillna(False).astype(bool).astype(np.float32).values,             # 3
        df['accelerated_approval'].fillna(False).astype(bool).astype(np.float32).values,   # 4
        df['had_adcom'].fillna(False).astype(bool).astype(np.float32).values,              # 5
        (pd.to_numeric(df.get('adcom_vote_pct', 0.0), errors='coerce')
           .fillna(0.0)
           .apply(lambda x: x/100.0 if x > 1.0 else x)
           .clip(0.0, 1.0)
           .values.astype(np.float32)),                                                     # 6
        df['prior_crl'].fillna(False).astype(bool).astype(np.float32).values,              # 7
        df['prior_crl_count'].fillna(0).values.astype(np.float32),                         # 8 (NEW)
        df['resubmission_class'].fillna(0).values.astype(np.float32),                      # 9
        df['sponsor_prior_approvals'].fillna(0).values.astype(np.float32),                 # 10
        df['ta_idx'].values.astype(np.float32),                                            # 11
        df['modality_adj'].values.astype(np.float32),                                      # 12
        df['is_gene_therapy'].values.astype(np.float32),                                   # 13 (NEW)
        df['is_cell_therapy'].values.astype(np.float32),                                   # 14 (NEW)
        df['is_rna_therapy'].values.astype(np.float32),                                    # 15 (NEW)
        df['interaction_penalty'].values.astype(np.float32),                               # 16 (NEW)
        df['indication_override'].values.astype(np.float32),                               # 17
    ]).astype(np.float32)
    
    labels = df['outcome_binary'].values.astype(np.float32)
    
    # Summary stats
    n_approved = labels.sum()
    n_crl = len(labels) - n_approved
    print(f"   Outcomes: {int(n_approved)} approved ({100*n_approved/len(labels):.1f}%), "
          f"{int(n_crl)} CRL ({100*n_crl/len(labels):.1f}%)")
    print(f"   Features: {features.shape[1]} columns (v9.4 expanded)")
    
    return features, labels, df


def get_ta_adjustment_array() -> np.ndarray:
    """Get TA adjustments as array indexed by ta_idx."""
    ta_list = list(TA_ADJUSTMENTS.keys())
    return np.array([TA_ADJUSTMENTS[ta] for ta in ta_list], dtype=np.float32)


# =============================================================================
# GPU AUTO-TUNING
# =============================================================================

def autotune_gpu_batching(config: OptimizerConfig, n_events: int) -> None:
    """Auto-tune batch_size and event_chunk_size to fit VRAM."""
    if not GPU_AVAILABLE:
        return

    try:
        if mempool is not None:
            mempool.free_all_blocks()
        if pinned_mempool is not None:
            pinned_mempool.free_all_blocks()
    except Exception:
        pass

    free0, total0 = _gpu_mem_info()
    print("\n🧠 GPU memory scan:")
    print(f"   VRAM total: {_format_bytes(total0)} | free: {_format_bytes(free0)}")

    requested_batch = int(config.batch_size)
    requested_chunk = int(config.event_chunk_size)

    chunk_candidates = sorted({c for c in [requested_chunk, 256, 192, 128, 96, 64, 48, 32] 
                               if 1 <= c <= n_events}, reverse=True)

    best = None
    oom = getattr(cp.cuda.memory, "OutOfMemoryError", RuntimeError)

    for chunk in chunk_candidates:
        batch = requested_batch
        while batch >= 10_000:
            try:
                # Probe allocations
                _p = cp.empty((batch, N_PARAMS), dtype=cp.float32)
                _a = cp.empty((batch, chunk), dtype=cp.float32)
                _b = cp.empty((batch, chunk), dtype=cp.float32)
                _m1 = cp.empty((batch, chunk), dtype=cp.bool_)
                _m2 = cp.empty((batch, chunk), dtype=cp.bool_)
                cp.cuda.runtime.deviceSynchronize()

                del _p, _a, _b, _m1, _m2
                if mempool is not None:
                    mempool.free_all_blocks()
                if pinned_mempool is not None:
                    pinned_mempool.free_all_blocks()

                best = (batch, chunk)
                break
            except oom:
                try:
                    if mempool is not None:
                        mempool.free_all_blocks()
                    if pinned_mempool is not None:
                        pinned_mempool.free_all_blocks()
                except Exception:
                    pass
                batch = int(batch * 0.80)
            except Exception:
                raise

        if best is not None:
            break

    if best is None:
        config.batch_size = min(requested_batch, 50_000)
        config.event_chunk_size = min(requested_chunk, 64)
        print(f"⚠️ Auto-tune fallback: batch_size={config.batch_size:,}, event_chunk_size={config.event_chunk_size}")
        return

    config.batch_size, config.event_chunk_size = best

    free1, _ = _gpu_mem_info()
    print("✅ Auto-tuned batching:")
    print(f"   event_chunk_size: {config.event_chunk_size}")
    print(f"   batch_size:       {config.batch_size:,}")
    print(f"   VRAM free:        {_format_bytes(free1)}")


# =============================================================================
# GPU-ACCELERATED SCORING KERNEL (v9.4 with CRL multiplier + interactions)
# =============================================================================

def generate_random_params(n_configs: int, xp=np) -> np.ndarray:
    """Generate random parameter configurations within bounds."""
    params = xp.zeros((n_configs, N_PARAMS), dtype=xp.float32)
    
    for i, name in enumerate(PARAMETER_NAMES):
        low, high = PARAMETER_BOUNDS[name]
        params[:, i] = xp.random.uniform(low, high, n_configs).astype(xp.float32)
    
    return params


def gpu_batch_score_v94(params: 'cp.ndarray', features: 'cp.ndarray', 
                        ta_adjustments: 'cp.ndarray', xp=cp) -> 'cp.ndarray':
    """
    v9.4 Vectorized scoring with CRL count multiplier and modality-indication interactions.
    
    Args:
        params: (C, P) array of C parameter configurations with P parameters
        features: (N, F) array of N events with F features
        ta_adjustments: (T,) array of TA adjustments
    
    Returns:
        probs: (C, N) array of predicted probabilities
    """
    n_configs = params.shape[0]
    n_events = features.shape[0]
    
    # Extract parameters (C,) arrays - v9.4 order (25 params)
    btd_w = params[:, 0]
    orphan_w = params[:, 1]
    pr_w = params[:, 2]
    ft_w = params[:, 3]
    aa_w = params[:, 4]
    adcom_high = params[:, 5]
    adcom_mid = params[:, 6]
    adcom_low = params[:, 7]
    prior_crl_base = params[:, 8]
    crl_mult_2 = params[:, 9]
    crl_mult_3 = params[:, 10]
    crl_mult_4plus = params[:, 11]
    class1_boost = params[:, 12]
    class2_boost = params[:, 13]  # Now a boost!
    exp_sponsor = params[:, 14]
    inexp_sponsor = params[:, 15]
    gene_pen = params[:, 16]
    cell_pen = params[:, 17]
    rna_pen = params[:, 18]
    mod_ind_w = params[:, 19]
    ta_w = params[:, 20]
    ind_override_w = params[:, 21]
    t1_thresh = params[:, 22]
    t2_thresh = params[:, 23]
    t3_thresh = params[:, 24]
    
    # Extract features (N,) arrays
    btd = features[:, 0]
    orphan = features[:, 1]
    pr = features[:, 2]
    ft = features[:, 3]
    aa = features[:, 4]
    had_adcom = features[:, 5]
    adcom_vote = features[:, 6]
    prior_crl = features[:, 7]
    crl_count = features[:, 8]
    resub_class = features[:, 9]
    sponsor_approvals = features[:, 10]
    ta_idx = features[:, 11].astype(xp.int32)
    modality_adj = features[:, 12]
    is_gene = features[:, 13]
    is_cell = features[:, 14]
    is_rna = features[:, 15]
    interaction_pen = features[:, 16]
    ind_override = features[:, 17]
    
    # Base probability (v9.1 champion)
    base_prob = 0.867
    
    # Initialize probability matrix (C, N)
    probs = xp.full((n_configs, n_events), base_prob, dtype=xp.float32)
    
    # Designation contributions
    probs += xp.outer(btd_w, btd)
    probs += xp.outer(orphan_w, orphan)
    probs += xp.outer(pr_w, pr)
    probs += xp.outer(ft_w, ft)
    probs += xp.outer(aa_w, aa)
    
    # AdCom: high (>=65%), mid (50-65%), low (<50%)
    adcom_high_mask = (had_adcom * (adcom_vote >= 0.65)).astype(xp.float32)
    adcom_mid_mask = (had_adcom * (adcom_vote >= 0.50) * (adcom_vote < 0.65)).astype(xp.float32)
    adcom_low_mask = (had_adcom * (adcom_vote < 0.50) * (adcom_vote > 0)).astype(xp.float32)
    probs += xp.outer(adcom_high, adcom_high_mask)
    probs += xp.outer(adcom_mid, adcom_mid_mask)
    probs += xp.outer(adcom_low, adcom_low_mask)
    
    # Prior CRL with count multiplier (NEW in v9.4)
    # CRL multiplier: 1 CRL = 1.0x, 2 CRLs = mult_2, 3 CRLs = mult_3, 4+ = mult_4plus
    crl_1_mask = (prior_crl * (crl_count <= 1)).astype(xp.float32)
    crl_2_mask = (prior_crl * (crl_count == 2)).astype(xp.float32)
    crl_3_mask = (prior_crl * (crl_count == 3)).astype(xp.float32)
    crl_4plus_mask = (prior_crl * (crl_count >= 4)).astype(xp.float32)
    
    probs += xp.outer(prior_crl_base, crl_1_mask)  # 1.0x
    probs += xp.outer(prior_crl_base * crl_mult_2, crl_2_mask)  # mult_2x
    probs += xp.outer(prior_crl_base * crl_mult_3, crl_3_mask)  # mult_3x
    probs += xp.outer(prior_crl_base * crl_mult_4plus, crl_4plus_mask)  # mult_4plus
    
    # Resubmission class (both are now boosts in v9.4)
    class1_mask = (prior_crl * (resub_class == 1)).astype(xp.float32)
    class2_mask = (prior_crl * (resub_class == 2)).astype(xp.float32)
    probs += xp.outer(class1_boost, class1_mask)
    probs += xp.outer(class2_boost, class2_mask)
    
    # Sponsor experience
    exp_mask = (sponsor_approvals >= 5).astype(xp.float32)
    inexp_mask = (sponsor_approvals == 0).astype(xp.float32)
    probs += xp.outer(exp_sponsor, exp_mask)
    probs += xp.outer(inexp_sponsor, inexp_mask)
    
    # Base modality adjustment (from lookup table)
    probs += modality_adj  # Broadcast (N,) to (C, N)
    
    # Additional modality penalties (optimizable)
    probs += xp.outer(gene_pen, is_gene)
    probs += xp.outer(cell_pen, is_cell)
    probs += xp.outer(rna_pen, is_rna)
    
    # Modality-indication interaction (NEW in v9.4)
    probs += xp.outer(mod_ind_w, interaction_pen)
    
    # Therapeutic area adjustment
    ta_adj_values = ta_adjustments[ta_idx]
    probs += xp.outer(ta_w, ta_adj_values)
    
    # Indication-specific overrides
    probs += xp.outer(ind_override_w, ind_override)
    
    # Clamp probabilities
    probs = xp.clip(probs, 0.01, 0.99)
    
    return probs


def compute_metrics_streaming(params: np.ndarray,
                              features: np.ndarray,
                              ta_adjustments: np.ndarray,
                              labels: np.ndarray,
                              event_chunk_size: int = 128,
                              xp=cp) -> Tuple[np.ndarray, dict]:
    """Memory-efficient metrics computation via streaming."""
    n_configs = params.shape[0]
    n_events = features.shape[0]
    chunk = max(16, min(int(event_chunk_size), n_events))

    # Accumulators
    brier_sum = xp.zeros((n_configs,), dtype=xp.float32)
    tier4_counts = xp.zeros((n_configs,), dtype=xp.int32)
    tier4_crl_counts = xp.zeros((n_configs,), dtype=xp.int32)
    crls_below_85 = xp.zeros((n_configs,), dtype=xp.int32)

    crl_mask_all = (labels < 0.5)
    total_crls = xp.sum(crl_mask_all).astype(xp.float32)

    # Tier 3 threshold (for TIER_4 detection)
    t3 = params[:, 24]  # tier3_threshold is index 24

    for start in range(0, n_events, chunk):
        end = min(start + chunk, n_events)
        feat_chunk = features[start:end]
        lab_chunk = labels[start:end]
        crl_chunk = (lab_chunk < 0.5)

        probs = gpu_batch_score_v94(params, feat_chunk, ta_adjustments, xp=xp)

        # Brier accumulation
        diff = probs - lab_chunk
        diff *= diff
        brier_sum += xp.sum(diff, axis=1).astype(xp.float32)

        # Tier4 (prob < t3)
        t4 = probs < t3[:, None]
        tier4_counts += xp.sum(t4, axis=1).astype(xp.int32)
        tier4_crl_counts += xp.sum(t4 & crl_chunk[None, :], axis=1).astype(xp.int32)

        # CRL recall at 85% threshold
        low = probs < 0.85
        crls_below_85 += xp.sum(low & crl_chunk[None, :], axis=1).astype(xp.int32)

        del probs, diff, t4, low

    brier_scores = brier_sum / float(n_events)

    tier4_crl_rate = xp.where(
        tier4_counts > 0,
        tier4_crl_counts.astype(xp.float32) / tier4_counts.astype(xp.float32),
        xp.zeros_like(brier_scores)
    )

    crl_recall = xp.where(
        total_crls > 0,
        crls_below_85.astype(xp.float32) / total_crls,
        xp.zeros_like(brier_scores)
    )

    return brier_scores, {
        'tier4_counts': tier4_counts,
        'tier4_crl_rate': tier4_crl_rate,
        'crl_recall': crl_recall,
    }


def apply_constraints(brier_scores: np.ndarray, metrics: dict, 
                      config: OptimizerConfig, xp=cp) -> np.ndarray:
    """Apply constraints and return penalized scores."""
    feasible = xp.ones(len(brier_scores), dtype=xp.bool_)
    
    feasible &= (metrics['tier4_counts'] >= config.min_tier4_count)
    feasible &= (metrics['tier4_crl_rate'] >= config.min_tier4_crl_rate)
    feasible &= (metrics['crl_recall'] >= config.min_crl_recall)
    
    penalized_scores = xp.where(feasible, brier_scores, xp.ones_like(brier_scores))
    
    return penalized_scores, feasible


# =============================================================================
# IMPROVEMENT LOGGER (NEW in v9.4)
# =============================================================================

class ImprovementLogger:
    """Logs every configuration that beats the previous best."""
    
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.improvement_count = 0
        self.history = []
        
        # Write header
        header = "timestamp,improvement_num,brier_score,improvement_pct,tier4_count,tier4_crl_rate,crl_recall,params_json"
        _append_log(self.log_path, header)
        print(f"📝 Improvement logger initialized: {log_path}")
    
    def log_improvement(self, brier_score: float, previous_best: float,
                        metrics: dict, params: np.ndarray) -> None:
        """Log a new improvement."""
        self.improvement_count += 1
        improvement_pct = 100 * (previous_best - brier_score) / max(previous_best, 1e-9)
        
        params_dict = {name: float(params[i]) for i, name in enumerate(PARAMETER_NAMES)}
        params_json = json.dumps(params_dict)
        
        line = (f"{datetime.now().isoformat()},"
                f"{self.improvement_count},"
                f"{brier_score:.6f},"
                f"{improvement_pct:.4f},"
                f"{metrics.get('tier4_count', 0)},"
                f"{metrics.get('tier4_crl_rate', 0):.4f},"
                f"{metrics.get('crl_recall', 0):.4f},"
                f'"{params_json}"')
        
        _append_log(self.log_path, line)
        
        self.history.append({
            'brier': brier_score,
            'improvement_pct': improvement_pct,
            'params': params_dict.copy(),
            'metrics': metrics.copy()
        })
        
        print(f"   🎯 IMPROVEMENT #{self.improvement_count}: Brier {previous_best:.5f} → {brier_score:.5f} "
              f"({improvement_pct:+.2f}%)")


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

def run_optimization(csv_path: str, config: OptimizerConfig,
                     resume_from: Optional[str] = None) -> dict:
    """Main optimization loop with GPU acceleration and improvement logging."""
    print("\n" + "=" * 70)
    print("ODIN v9.4 GPU OPTIMIZER")
    print("=" * 70)
    print(f"Target configs:     {config.total_configs:,}")
    print(f"Requested batch max:{config.batch_size:,}")
    print(f"Primary objective:  {config.primary_objective}")
    print(f"Parameters:         {N_PARAMS}")
    print("Constraints:")
    print(f"  - Min TIER_4 count:    {config.min_tier4_count}")
    print(f"  - Min TIER_4 CRL rate: {config.min_tier4_crl_rate:.0%}")
    print(f"  - Min CRL recall:      {config.min_crl_recall:.0%}")

    xp = cp if GPU_AVAILABLE else np

    os.makedirs(config.output_dir, exist_ok=True)
    progress_log_path = os.path.join(config.output_dir, "progress.log")
    improvement_log_path = os.path.join(config.output_dir, config.improvement_log_path)

    # Initialize improvement logger
    improvement_logger = ImprovementLogger(improvement_log_path)

    # Load data
    features_np, labels_np, df = load_and_preprocess_data(csv_path)
    ta_adjustments_np = get_ta_adjustment_array()

    # Transfer to GPU
    if GPU_AVAILABLE:
        features = cp.asarray(features_np)
        labels = cp.asarray(labels_np)
        ta_adjustments = cp.asarray(ta_adjustments_np)
        print(f"\n✅ Data transferred to GPU")
        print(f"   Features: {features.shape}, Labels: {labels.shape}")
        autotune_gpu_batching(config, n_events=int(features.shape[0]))
    else:
        features = features_np
        labels = labels_np
        ta_adjustments = ta_adjustments_np

    est_batches = math.ceil(config.total_configs / max(1, config.batch_size))
    print("\nEffective settings:")
    print(f"  - Batch size:         {config.batch_size:,}")
    print(f"  - Event chunk size:   {config.event_chunk_size}")
    print(f"  - Estimated batches:  {est_batches:,}")

    # Initialize tracking
    best_score = 1.0
    best_raw_brier = 1.0
    best_params = None
    best_metrics = None
    total_tested = 0
    total_feasible = 0
    start_time = time.time()

    # Top-K tracking
    top_k = 100
    top_scores = np.ones(top_k, dtype=np.float32)
    top_params = np.zeros((top_k, N_PARAMS), dtype=np.float32)

    # Resume from checkpoint
    if resume_from and os.path.exists(resume_from):
        print(f"\n📂 Resuming from checkpoint: {resume_from}")
        checkpoint = np.load(resume_from, allow_pickle=True)
        best_score = float(checkpoint['best_score'])
        best_params = checkpoint['best_params']
        total_tested = int(checkpoint['total_tested'])
        total_feasible = int(checkpoint.get('total_feasible', 0))
        top_scores = checkpoint.get('top_scores', top_scores)
        top_params = checkpoint.get('top_params', top_params)
        print(f"   Resumed at tested={total_tested:,}, best_brier={best_score:.5f}")

    progress_every = int(config.progress_log_every)
    next_log_at = ((total_tested // progress_every) + 1) * progress_every if progress_every > 0 else 0

    if not os.path.exists(progress_log_path):
        _append_log(progress_log_path, "timestamp,tested,feasible,feasible_rate,best_brier,cfg_per_sec,eta_sec")

    print("\n" + "-" * 70)
    print("Starting optimization...")
    print("-" * 70)

    batch_idx = 0
    oom = getattr(cp.cuda.memory, "OutOfMemoryError", RuntimeError) if GPU_AVAILABLE else RuntimeError

    while total_tested < config.total_configs:
        remaining = config.total_configs - total_tested
        current_batch = min(config.batch_size, remaining)

        batch_start = time.time()

        # Retry loop for OOM backoff
        while True:
            try:
                params = generate_random_params(current_batch, xp=xp)

                brier_scores, metrics = compute_metrics_streaming(
                    params=params,
                    features=features,
                    ta_adjustments=ta_adjustments,
                    labels=labels,
                    event_chunk_size=config.event_chunk_size,
                    xp=xp
                )

                # Track best RAW brier
                if GPU_AVAILABLE:
                    batch_best_raw = float(cp.min(brier_scores).get())
                else:
                    batch_best_raw = float(np.min(brier_scores))
                
                if batch_best_raw < best_raw_brier:
                    best_raw_brier = batch_best_raw

                # Apply constraints
                penalized_scores, feasible = apply_constraints(brier_scores, metrics, config, xp=xp)
                break

            except oom:
                if GPU_AVAILABLE:
                    try:
                        if mempool is not None:
                            mempool.free_all_blocks()
                        if pinned_mempool is not None:
                            pinned_mempool.free_all_blocks()
                    except Exception:
                        pass

                old_batch = current_batch
                current_batch = int(max(10_000, current_batch * 0.70))

                if current_batch <= 50_000 and config.event_chunk_size > 32:
                    config.event_chunk_size = max(32, int(config.event_chunk_size * 0.75))

                print(f"⚠️ GPU OOM - backing off: batch {old_batch:,} → {current_batch:,}")
                config.batch_size = min(config.batch_size, current_batch)

                if current_batch < 10_000:
                    raise RuntimeError("Batch size below 10k; cannot continue.")

        # Update statistics
        if GPU_AVAILABLE:
            batch_feasible = int(cp.sum(feasible).get())
        else:
            batch_feasible = int(np.sum(feasible))

        total_tested += current_batch
        total_feasible += batch_feasible

        # Best in batch
        if GPU_AVAILABLE:
            batch_best_score = float(cp.min(penalized_scores).get())
        else:
            batch_best_score = float(np.min(penalized_scores))

        # Update global best and log improvement
        if batch_best_score < best_score:
            if GPU_AVAILABLE:
                batch_best_idx = int(cp.argmin(penalized_scores).get())
                new_best_params = cp.asnumpy(params[batch_best_idx]).astype(np.float32)
                new_best_metrics = {
                    'tier4_count': int(metrics['tier4_counts'][batch_best_idx].get()),
                    'tier4_crl_rate': float(metrics['tier4_crl_rate'][batch_best_idx].get()),
                    'crl_recall': float(metrics['crl_recall'][batch_best_idx].get()),
                }
            else:
                batch_best_idx = int(np.argmin(penalized_scores))
                new_best_params = params[batch_best_idx].copy()
                new_best_metrics = {
                    'tier4_count': int(metrics['tier4_counts'][batch_best_idx]),
                    'tier4_crl_rate': float(metrics['tier4_crl_rate'][batch_best_idx]),
                    'crl_recall': float(metrics['crl_recall'][batch_best_idx]),
                }

            # LOG IMPROVEMENT
            improvement_logger.log_improvement(batch_best_score, best_score, 
                                               new_best_metrics, new_best_params)

            best_score = batch_best_score
            best_params = new_best_params
            best_metrics = new_best_metrics

        # Top-K update
        if not config.disable_topk and total_tested >= next_log_at:
            k_take = min(top_k, current_batch)
            if GPU_AVAILABLE:
                idx_k = cp.argpartition(penalized_scores, k_take - 1)[:k_take]
                cand_scores = cp.asnumpy(penalized_scores[idx_k]).astype(np.float32)
                cand_params = cp.asnumpy(params[idx_k]).astype(np.float32)
            else:
                idx_k = np.argpartition(penalized_scores, k_take - 1)[:k_take]
                cand_scores = penalized_scores[idx_k].astype(np.float32)
                cand_params = params[idx_k].astype(np.float32)

            merged_scores = np.concatenate([top_scores, cand_scores])
            merged_params = np.concatenate([top_params, cand_params])
            keep_idx = np.argpartition(merged_scores, top_k - 1)[:top_k]
            keep_idx = keep_idx[np.argsort(merged_scores[keep_idx])]
            top_scores = merged_scores[keep_idx]
            top_params = merged_params[keep_idx]

        batch_time = time.time() - batch_start
        configs_per_sec = current_batch / max(batch_time, 1e-9)

        # Progress logging
        if progress_every > 0 and total_tested >= next_log_at:
            while total_tested >= next_log_at:
                next_log_at += progress_every

            elapsed = time.time() - start_time
            avg_cps = total_tested / max(elapsed, 1e-9)
            remaining_cfgs = config.total_configs - total_tested
            eta_sec = remaining_cfgs / max(avg_cps, 1e-9)
            feasibility_rate = 100.0 * total_feasible / max(total_tested, 1)

            print(f"Progress | Tested: {total_tested:12,} | "
                  f"Feasible: {feasibility_rate:5.1f}% | "
                  f"Best: {best_score:.5f} | "
                  f"Raw: {best_raw_brier:.5f} | "
                  f"{configs_per_sec:,.0f} cfg/s | "
                  f"ETA: {eta_sec/60:.1f}m | "
                  f"Improvements: {improvement_logger.improvement_count}")

            _append_log(progress_log_path,
                f"{datetime.now().isoformat()},{total_tested},{total_feasible},"
                f"{feasibility_rate/100.0:.6f},{best_score:.8f},{avg_cps:.2f},{eta_sec:.1f}")

        # Checkpoint
        if (batch_idx + 1) % config.checkpoint_interval == 0:
            checkpoint_path = os.path.join(config.output_dir, config.checkpoint_path)
            np.savez(checkpoint_path,
                     best_score=best_score,
                     best_params=best_params,
                     total_tested=total_tested,
                     total_feasible=total_feasible,
                     top_scores=top_scores,
                     top_params=top_params)
            print(f"   💾 Checkpoint saved")

        # Periodic GPU memory cleanup
        if GPU_AVAILABLE and (batch_idx + 1) % 50 == 0:
            try:
                if mempool is not None:
                    mempool.free_all_blocks()
                if pinned_mempool is not None:
                    pinned_mempool.free_all_blocks()
            except Exception:
                pass

        batch_idx += 1

    total_time = time.time() - start_time

    # Final results
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"Total configs tested:  {total_tested:,}")
    print(f"Feasible configs:      {total_feasible:,} ({100*total_feasible/max(total_tested,1):.1f}%)")
    print(f"Total improvements:    {improvement_logger.improvement_count}")
    print(f"Total time:            {total_time/60:.1f} minutes")
    print(f"Average throughput:    {total_tested/max(total_time,1e-9):,.0f} configs/sec")

    if best_params is None:
        raise RuntimeError("No feasible configurations found; try relaxing constraints.")

    print("\n🏆 CHAMPION CONFIGURATION")
    print(f"   Brier Score:      {best_score:.5f}")
    print(f"   TIER_4 Count:     {best_metrics['tier4_count']}")
    print(f"   TIER_4 CRL Rate:  {best_metrics['tier4_crl_rate']:.1%}")
    print(f"   CRL Recall @85%:  {best_metrics['crl_recall']:.1%}")

    # Create champion config
    champion_config = {
        'version': '9.4',
        'optimization_date': datetime.now().isoformat(),
        'total_configs_tested': total_tested,
        'feasible_configs': total_feasible,
        'feasibility_rate': total_feasible / max(total_tested, 1),
        'total_improvements': improvement_logger.improvement_count,
        'performance': {
            'brier_score': float(best_score),
            'baseline_brier': 0.0996,
            'v91_champion_brier': 0.08864,
            'improvement_vs_baseline_pct': 100 * (0.0996 - best_score) / 0.0996,
            'improvement_vs_v91_pct': 100 * (0.08864 - best_score) / 0.08864,
            'tier4_count': best_metrics['tier4_count'],
            'tier4_crl_rate': best_metrics['tier4_crl_rate'],
            'crl_recall_at_85': best_metrics['crl_recall'],
        },
        'champion_params': {name: float(best_params[i]) for i, name in enumerate(PARAMETER_NAMES)},
        'therapeutic_area_adjustments': TA_ADJUSTMENTS,
        'modality_adjustments': MODALITY_ADJUSTMENTS,
        'modality_indication_interactions': {
            f"{k[0]}+{k[1]}": v for k, v in MODALITY_INDICATION_INTERACTIONS.items()
        },
        'indication_overrides': INDICATION_OVERRIDES,
        'constraints': {
            'min_tier4_count': config.min_tier4_count,
            'min_tier4_crl_rate': config.min_tier4_crl_rate,
            'min_crl_recall': config.min_crl_recall,
        },
    }

    # Save champion config
    champion_path = os.path.join(config.output_dir, config.champion_config_path)
    with open(champion_path, 'w', encoding='utf-8') as f:
        json.dump(champion_config, f, indent=2)

    print(f"\n💾 Champion config saved to: {champion_path}")
    print(f"📝 Improvement log: {improvement_log_path}")
    print(f"📊 Progress log: {progress_log_path}")

    # Save top-K configs
    topk_path = os.path.join(config.output_dir, 'odin_v94_top100_configs.json')
    top_configs = []
    for i in range(min(len(top_scores), top_k)):
        if top_scores[i] < 1.0:  # Only feasible
            top_configs.append({
                'rank': i + 1,
                'brier_score': float(top_scores[i]),
                'params': {name: float(top_params[i, j]) for j, name in enumerate(PARAMETER_NAMES)}
            })
    
    with open(topk_path, 'w', encoding='utf-8') as f:
        json.dump(top_configs, f, indent=2)
    print(f"📋 Top-{len(top_configs)} configs saved to: {topk_path}")

    return champion_config


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='ODIN v9.4 GPU Optimizer - Billion Parameter Search')
    parser.add_argument('--configs', type=int, default=100_000_000,
                        help='Total configurations to test (default: 100M)')
    parser.add_argument('--batch-size', type=int, default=2_500_000,
                        help='Batch size (default: 2.5M, auto-tuned for VRAM)')
    parser.add_argument('--event-chunk-size', type=int, default=128,
                        help='Event chunk size (default: 128, auto-tuned)')
    parser.add_argument('--min-tier4-count', type=int, default=15,
                        help='Min TIER_4 count constraint (default: 15)')
    parser.add_argument('--min-tier4-crl-rate', type=float, default=0.50,
                        help='Min TIER_4 CRL rate (default: 0.50)')
    parser.add_argument('--min-crl-recall', type=float, default=0.55,
                        help='Min CRL recall at 85%% threshold (default: 0.55)')
    parser.add_argument('--progress-every', type=int, default=10_000_000,
                        help='Log progress every N configs (default: 10M)')
    parser.add_argument('--csv', type=str,
                        default=os.environ.get('ODIN_CSV_PATH', 'ODIN_ENRICHED_PDUFA_1349_v2.csv'),
                        help='Path to PDUFA dataset')
    parser.add_argument('--output-dir', type=str,
                        default=os.environ.get('ODIN_OUTPUT_DIR', 'odin_output'),
                        help='Output directory')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from checkpoint file')
    parser.add_argument('--quick', action='store_true',
                        help='Quick mode (1M configs, relaxed constraints)')
    parser.add_argument('--billion', action='store_true',
                        help='Billion config mode (1B configs)')
    
    args = parser.parse_args()
    
    # Configure optimizer
    opt_config = OptimizerConfig(
        total_configs=args.configs,
        batch_size=args.batch_size,
        event_chunk_size=args.event_chunk_size,
        output_dir=args.output_dir,
        min_tier4_count=args.min_tier4_count,
        min_tier4_crl_rate=args.min_tier4_crl_rate,
        min_crl_recall=args.min_crl_recall,
        progress_log_every=args.progress_every,
    )
    
    if args.quick:
        print("⚡ QUICK MODE - Fast validation scan")
        opt_config.total_configs = 1_000_000
        opt_config.min_tier4_count = 10
        opt_config.min_tier4_crl_rate = 0.35
        opt_config.min_crl_recall = 0.45
    
    if args.billion:
        print("🚀 BILLION MODE - Full parameter space exploration")
        opt_config.total_configs = 1_000_000_000
    
    # Run optimization
    champion = run_optimization(args.csv, opt_config, resume_from=args.resume)
    
    print("\n✅ Optimization complete!")
    print(f"   Champion Brier: {champion['performance']['brier_score']:.5f}")


if __name__ == '__main__':
    main()
