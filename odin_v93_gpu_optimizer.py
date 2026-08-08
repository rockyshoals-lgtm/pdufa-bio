#!/usr/bin/env python3
"""
ODIN v9.3 GPU Optimizer - Billion-Parameter Search with CuPy
=============================================================
Optimized for RTX 4070 (12GB VRAM, 5888 CUDA cores)

Key Changes from v9.2:
- REMOVED: manufacturing_risk (T-1 leakage, p<10^-80)
- ADDED: modality_complexity_weight (T-1 compliant proxy)
- ADDED: temporal_backtest_mode (disabled during optimization)

Usage:
    python odin_v93_gpu_optimizer.py --configs 1000000000 --batch-size 500000
    python odin_v93_gpu_optimizer.py --configs 100000000 --quick  # Quick scan
    python odin_v93_gpu_optimizer.py --resume checkpoint.npz     # Resume from checkpoint

Author: ODIN Development Team
Version: 9.3.0
Date: 2026-01-28
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
    print(f"   Device: {gpu_name}")
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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def autotune_gpu_batching(config: 'OptimizerConfig', n_events: int) -> None:
    """
    Auto-tune (batch_size, event_chunk_size) to fit the detected free VRAM.
    Uses a small allocation probe to avoid guesswork.

    Notes:
    - Treats config.batch_size as an UPPER BOUND (user request).
    - Chooses the largest chunk size that can still run a large batch.
    """
    if not GPU_AVAILABLE:
        return

    # Clear pools for an accurate free-mem reading.
    try:
        if mempool is not None:
            mempool.free_all_blocks()
        if pinned_mempool is not None:
            pinned_mempool.free_all_blocks()
    except Exception:
        pass

    free0, total0 = _gpu_mem_info()
    print("\n🧠 GPU memory scan:")
    print(f"   VRAM total: { _format_bytes(total0) } | free: { _format_bytes(free0) }")

    requested_batch = int(getattr(config, "batch_size", 2500000))
    requested_chunk = int(getattr(config, "event_chunk_size", 128))

    # Candidate chunk sizes (bigger chunk => fewer iterations, but higher VRAM).
    chunk_candidates = [requested_chunk, 256, 192, 128, 96, 64, 48, 32]
    # Deduplicate, keep <= n_events, sort descending.
    chunk_candidates = sorted({c for c in chunk_candidates if 1 <= c <= n_events}, reverse=True)

    best = None  # (batch, chunk)
    oom = getattr(cp.cuda.memory, "OutOfMemoryError", RuntimeError)

    for chunk in chunk_candidates:
        batch = requested_batch
        # Probe down until we fit.
        while batch >= 10_000:
            try:
                # Probe allocations roughly matching peak per-chunk memory use:
                # - params (C,P)
                # - probs chunk (C,chunk)
                # - temp diff/outer (C,chunk)
                # - a couple boolean masks (C,chunk)
                _p = cp.empty((batch, N_PARAMS), dtype=cp.float32)
                _a = cp.empty((batch, chunk), dtype=cp.float32)
                _b = cp.empty((batch, chunk), dtype=cp.float32)
                _m1 = cp.empty((batch, chunk), dtype=cp.bool_)
                _m2 = cp.empty((batch, chunk), dtype=cp.bool_)
                cp.cuda.runtime.deviceSynchronize()

                # Success — record and cleanup.
                del _p, _a, _b, _m1, _m2
                if mempool is not None:
                    mempool.free_all_blocks()
                if pinned_mempool is not None:
                    pinned_mempool.free_all_blocks()

                best = (batch, chunk)
                break
            except oom:
                # Reduce batch and try again.
                try:
                    if mempool is not None:
                        mempool.free_all_blocks()
                    if pinned_mempool is not None:
                        pinned_mempool.free_all_blocks()
                except Exception:
                    pass
                batch = int(batch * 0.80)
            except Exception:
                # Unexpected error; re-raise.
                raise

        if best is not None:
            break

    if best is None:
        # Last resort — keep something tiny instead of failing later.
        config.batch_size = min(requested_batch, 50_000)
        config.event_chunk_size = min(requested_chunk, 64)
        print(f"⚠️ Auto-tune fallback: batch_size={config.batch_size:,}, event_chunk_size={config.event_chunk_size}")
        return

    config.batch_size, config.event_chunk_size = best

    free1, total1 = _gpu_mem_info()
    used1 = total1 - free1
    print("✅ Auto-tuned batching:")
    print(f"   event_chunk_size: {config.event_chunk_size}")
    print(f"   batch_size:       {config.batch_size:,} (requested max: {requested_batch:,})")
    print(f"   VRAM in use now:  { _format_bytes(used1) } | free: { _format_bytes(free1) }")

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
    
    # Objectives and constraints
    primary_objective: str = 'brier'  # 'brier', 'f1', 'precision'
    min_tier4_count: int = 20         # Minimum TIER_4 events for meaningful CRL detection
    min_tier4_crl_rate: float = 0.70  # Minimum CRL rate in TIER_4
    min_crl_recall: float = 0.60      # Minimum CRL recall at 85% threshold
    
    # Checkpoint settings
    checkpoint_interval: int = 50     # Save checkpoint every N batches
    checkpoint_path: str = 'odin_v93_checkpoint.npz'
    
    # Output settings
    output_dir: str = os.path.join(os.getcwd(), 'odin_output')
    champion_config_path: str = 'ODIN_v93_CHAMPION_CONFIG.json'
    results_path: str = 'odin_v93_optimization_results.csv'


# Parameter bounds for v9.3 (19 parameters to optimize)
PARAMETER_BOUNDS = {
    # Designation weights
    'btd_weight': (0.02, 0.12),
    'orphan_weight': (0.01, 0.08),
    'priority_review_weight': (0.03, 0.15),
    'fast_track_weight': (0.01, 0.06),
    'accelerated_approval_weight': (0.02, 0.08),
    
    # Synergy bonuses
    'btd_pr_synergy': (0.05, 0.18),
    'triple_designation_bonus': (0.03, 0.12),
    
    # AdCom adjustments
    'adcom_positive_boost': (0.04, 0.15),
    'adcom_negative_penalty': (-0.25, -0.08),
    
    # Prior CRL / Resubmission
    'prior_crl_base_penalty': (-0.18, -0.04),
    'class1_resubmission_boost': (0.08, 0.22),
    'class2_resubmission_penalty': (-0.12, -0.02),
    
    # Sponsor experience
    'experienced_sponsor_boost': (0.02, 0.10),
    'inexperienced_sponsor_penalty': (-0.12, -0.03),
    
    # NEW: Modality complexity (replaces manufacturing_risk)
    'modality_complexity_weight': (-0.15, -0.02),
    
    # Therapeutic area adjustment
    'ta_adjustment_weight': (0.5, 1.2),
    
    # Tier thresholds
    'tier1_threshold': (0.82, 0.92),
    'tier2_threshold': (0.68, 0.80),
    'tier3_threshold': (0.52, 0.65),
}

PARAMETER_NAMES = list(PARAMETER_BOUNDS.keys())
N_PARAMS = len(PARAMETER_NAMES)

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

# Modality complexity scores (T-1 compliant - based on inherent process difficulty)
MODALITY_COMPLEXITY = {
    "Small Molecule": 0.00,
    "Peptide": 0.15,
    "Antibody": 0.30,
    "ADC": 0.45,
    "Vaccine": 0.50,
    "RNA Therapy": 0.55,
    "Cell/Gene Therapy": 0.65,
}

# Indication-specific overrides (high-risk indications)
INDICATION_OVERRIDES = {
    "opioid use disorder": -0.184,
    "opioid-induced constipation": -0.184,
    "chronic pain": -0.184,
    "sickle cell disease": -0.150,
    "beta-thalassemia": -0.150,
    "acute myeloid leukemia": -0.120,
    "myelodysplastic syndromes": -0.120,
    "diabetic kidney disease": -0.130,
    "iga nephropathy": -0.130,
    "lupus nephritis": -0.130,
    "dry eye disease": -0.100,
    "diabetic macular edema": -0.100,
    "geographic atrophy": -0.100,
}


# =============================================================================
# DATA LOADING AND PREPROCESSING
# =============================================================================

def load_and_preprocess_data(csv_path: str) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Load PDUFA dataset and convert to GPU-ready arrays.
    
    Returns:
        features: (N, F) array of numeric features
        labels: (N,) array of binary outcomes (1=approved, 0=CRL)
        df: Original DataFrame for reference
    """
    # Resolve CSV path (Windows/WSL-safe)
    csv_path = os.path.expanduser(os.path.expandvars(csv_path))
    if not os.path.exists(csv_path):
        base = os.path.basename(csv_path)
        candidates = [
            csv_path,
            os.path.join(os.getcwd(), base),
            os.path.join(os.path.dirname(__file__), base),
        ]
        # Also try common ODIN dataset filenames in cwd/script dir
        common = [
            'ODIN_ENRICHED_PDUFA_1349_v2.csv',
            'ODIN_ENRICHED_PDUFA_1349_v3_LUNARCRUSH.csv',
            'ODIN_ENRICHED_PDUFA_1349_v3.csv',
        ]
        for fname in common:
            candidates.append(os.path.join(os.getcwd(), fname))
            candidates.append(os.path.join(os.path.dirname(__file__), fname))
        for c in candidates:
            if os.path.exists(c):
                csv_path = c
                break
        else:
            tried = "\n".join("  - " + c for c in candidates)
            raise FileNotFoundError(
                (
                    "Could not find dataset CSV. You passed: {0}\n"
                    "Tried these locations:\n{1}\n\n"
                    "Fix: run with --csv \"C:\\path\\to\\your\\dataset.csv\" (Windows) "
                    "or set environment variable ODIN_CSV_PATH."
                ).format(csv_path, tried)
            )
    print(f"\n📂 Loading data from {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')
    print(f"   Loaded {len(df)} events")
    
    # Encode outcome (handle both APPROVAL and APPROVED spellings)
    df['outcome_binary'] = df['outcome'].str.upper().isin(['APPROVED', 'APPROVAL']).astype(int)
    
    # Encode therapeutic area to index
    ta_list = list(TA_ADJUSTMENTS.keys())
    df['ta_idx'] = df['therapeutic_area'].apply(
        lambda x: ta_list.index(x) if x in ta_list else ta_list.index('Other')
    )
    
    # Encode modality to complexity score
    df['modality_complexity'] = df['modality'].map(MODALITY_COMPLEXITY).fillna(0.0)
    
    # Check for indication overrides
    df['indication_lower'] = df['indication'].str.lower().fillna('')
    df['indication_override'] = df['indication_lower'].apply(
        lambda x: next((v for k, v in INDICATION_OVERRIDES.items() if k in x), 0.0)
    )
    
    # Build feature matrix
    # Order: btd, orphan, pr, ft, aa, had_adcom, adcom_vote, prior_crl, 
    #        resubmission_class, sponsor_approvals, ta_idx, modality_complexity,
    #        indication_override, has_btd_pr
    
    features = np.column_stack([
        df['btd'].fillna(False).astype(bool).astype(np.float32).values,                    # 0
        df['orphan'].fillna(False).astype(bool).astype(np.float32).values,                 # 1
        df['priority_review'].fillna(False).astype(bool).astype(np.float32).values,        # 2
        df['fast_track'].fillna(False).astype(bool).astype(np.float32).values,             # 3
        df['accelerated_approval'].fillna(False).astype(bool).astype(np.float32).values,  # 4
        df['had_adcom'].fillna(False).astype(bool).astype(np.float32).values,              # 5
        (pd.to_numeric(df.get('adcom_vote_norm', df.get('adcom_vote_pct', 0.0)), errors='coerce')
           .fillna(0.0)
           .apply(lambda x: x/100.0 if x>1.0 else x)
           .clip(0.0, 1.0)
           .values.astype(np.float32)),                       # 6 (0-1)
        df['prior_crl'].fillna(False).astype(bool).astype(np.float32).values,              # 7
        df['resubmission_class'].fillna(0).values,                   # 8
        df['sponsor_prior_approvals'].fillna(0).values,              # 9
        df['ta_idx'].values,                                         # 10
        df['modality_complexity'].values,                            # 11
        df['indication_override'].values,                            # 12
        ((df['btd'].fillna(False).astype(bool)) & (df['priority_review'].fillna(False).astype(bool))).astype(np.float32).values,  # 13 (btd+pr)
        df['designation_stack_count'].fillna(0).values,              # 14
    ]).astype(np.float32)
    
    labels = df['outcome_binary'].values.astype(np.float32)
    
    # Summary stats
    n_approved = labels.sum()
    n_crl = len(labels) - n_approved
    print(f"   Outcomes: {int(n_approved)} approved ({100*n_approved/len(labels):.1f}%), "
          f"{int(n_crl)} CRL ({100*n_crl/len(labels):.1f}%)")
    print(f"   Features: {features.shape[1]} columns")
    
    return features, labels, df


def get_ta_adjustment_array() -> np.ndarray:
    """Get TA adjustments as array indexed by ta_idx."""
    ta_list = list(TA_ADJUSTMENTS.keys())
    return np.array([TA_ADJUSTMENTS[ta] for ta in ta_list], dtype=np.float32)


# =============================================================================
# GPU-ACCELERATED SCORING KERNEL
# =============================================================================

def generate_random_params(n_configs: int, xp=np) -> np.ndarray:
    """Generate random parameter configurations within bounds."""
    params = xp.zeros((n_configs, N_PARAMS), dtype=xp.float32)
    
    for i, name in enumerate(PARAMETER_NAMES):
        low, high = PARAMETER_BOUNDS[name]
        params[:, i] = xp.random.uniform(low, high, n_configs).astype(xp.float32)
    
    return params


def gpu_batch_score(params: 'cp.ndarray', features: 'cp.ndarray', 
                    ta_adjustments: 'cp.ndarray', xp=cp) -> 'cp.ndarray':
    """
    Vectorized scoring for all parameter configs and all events.
    
    Args:
        params: (C, P) array of C parameter configurations with P parameters
        features: (N, F) array of N events with F features
        ta_adjustments: (T,) array of TA adjustments
    
    Returns:
        probs: (C, N) array of predicted probabilities
    """
    n_configs = params.shape[0]
    n_events = features.shape[0]
    
    # Extract parameters (C,) arrays
    btd_w = params[:, 0]
    orphan_w = params[:, 1]
    pr_w = params[:, 2]
    ft_w = params[:, 3]
    aa_w = params[:, 4]
    btd_pr_syn = params[:, 5]
    triple_bonus = params[:, 6]
    adcom_pos = params[:, 7]
    adcom_neg = params[:, 8]
    prior_crl_pen = params[:, 9]
    class1_boost = params[:, 10]
    class2_pen = params[:, 11]
    exp_sponsor = params[:, 12]
    inexp_sponsor = params[:, 13]
    mod_complex_w = params[:, 14]
    ta_w = params[:, 15]
    t1_thresh = params[:, 16]
    t2_thresh = params[:, 17]
    t3_thresh = params[:, 18]
    
    # Extract features (N,) arrays
    btd = features[:, 0]
    orphan = features[:, 1]
    pr = features[:, 2]
    ft = features[:, 3]
    aa = features[:, 4]
    had_adcom = features[:, 5]
    adcom_vote = features[:, 6]
    prior_crl = features[:, 7]
    resub_class = features[:, 8]
    sponsor_approvals = features[:, 9]
    ta_idx = features[:, 10].astype(xp.int32)
    mod_complexity = features[:, 11]
    ind_override = features[:, 12]
    has_btd_pr = features[:, 13]
    desig_count = features[:, 14]
    
    # Base probability
    base_prob = 0.867
    
    # Initialize probability matrix (C, N)
    probs = xp.full((n_configs, n_events), base_prob, dtype=xp.float32)
    
    # Designation contributions: (C, 1) * (1, N) -> (C, N) via broadcasting
    probs += xp.outer(btd_w, btd)
    probs += xp.outer(orphan_w, orphan)
    probs += xp.outer(pr_w, pr)
    probs += xp.outer(ft_w, ft)
    probs += xp.outer(aa_w, aa)
    
    # BTD+PR synergy
    probs += xp.outer(btd_pr_syn, has_btd_pr)
    
    # Triple designation bonus (3+ designations)
    triple_mask = (desig_count >= 3).astype(xp.float32)
    probs += xp.outer(triple_bonus, triple_mask)
    
    # AdCom: positive vote (>=65%) vs negative (<50%)
    adcom_positive_mask = (had_adcom * (adcom_vote >= 0.65)).astype(xp.float32)
    adcom_negative_mask = (had_adcom * (adcom_vote < 0.50) * (adcom_vote > 0)).astype(xp.float32)
    probs += xp.outer(adcom_pos, adcom_positive_mask)
    probs += xp.outer(adcom_neg, adcom_negative_mask)
    
    # Prior CRL
    probs += xp.outer(prior_crl_pen, prior_crl)
    
    # Resubmission class
    class1_mask = (prior_crl * (resub_class == 1)).astype(xp.float32)
    class2_mask = (prior_crl * (resub_class == 2)).astype(xp.float32)
    probs += xp.outer(class1_boost, class1_mask)
    probs += xp.outer(class2_pen, class2_mask)
    
    # Sponsor experience
    exp_mask = (sponsor_approvals >= 5).astype(xp.float32)
    inexp_mask = (sponsor_approvals == 0).astype(xp.float32)
    probs += xp.outer(exp_sponsor, exp_mask)
    probs += xp.outer(inexp_sponsor, inexp_mask)
    
    # Modality complexity (NEW - replaces manufacturing_risk)
    # mod_complex_w is negative, mod_complexity is 0-0.65
    probs += xp.outer(mod_complex_w, mod_complexity)
    
    # Therapeutic area adjustment
    ta_adj_values = ta_adjustments[ta_idx]  # (N,)
    probs += xp.outer(ta_w, ta_adj_values)
    
    # Indication-specific overrides
    probs += ind_override  # Broadcast (N,) to (C, N)
    
    # Clamp probabilities
    probs = xp.clip(probs, 0.01, 0.99)
    
    return probs



def compute_metrics_streaming(params: np.ndarray,
                              features: np.ndarray,
                              ta_adjustments: np.ndarray,
                              labels: np.ndarray,
                              event_chunk_size: int = 128,
                              xp=cp) -> Tuple[np.ndarray, dict]:
    """
    Memory-efficient metrics computation that never materializes a (C, N) full probs matrix.
    It scores events in chunks of size `event_chunk_size` and accumulates:
      - Brier score
      - Tier4 count
      - Tier4 CRL rate
      - CRL recall @85%
    """
    n_configs = params.shape[0]
    n_events = features.shape[0]
    chunk = max(16, int(event_chunk_size))
    chunk = min(chunk, n_events)

    # Accumulators
    brier_sum = xp.zeros((n_configs,), dtype=xp.float32)
    tier4_counts = xp.zeros((n_configs,), dtype=xp.int32)
    tier4_crl_counts = xp.zeros((n_configs,), dtype=xp.int32)
    crls_below_85 = xp.zeros((n_configs,), dtype=xp.int32)

    # Masks
    crl_mask_all = (labels < 0.5)  # outcome_binary: 1=approved, 0=CRL
    total_crls = xp.sum(crl_mask_all).astype(xp.float32)

    # Thresholds (per-config)
    t3 = params[:, 18]  # (C,)

    # Stream over event chunks
    for start in range(0, n_events, chunk):
        end = min(start + chunk, n_events)
        feat_chunk = features[start:end]
        lab_chunk = labels[start:end]
        crl_chunk = (lab_chunk < 0.5)  # bool (chunk,)

        # Score this chunk: returns (C, chunk)
        probs = gpu_batch_score(params, feat_chunk, ta_adjustments, xp=xp)

        # Brier accumulation
        diff = probs - lab_chunk  # broadcast
        diff *= diff
        brier_sum += xp.sum(diff, axis=1).astype(xp.float32)

        # Tier4 (prob < t3)
        t4 = probs < t3[:, None]
        tier4_counts += xp.sum(t4, axis=1).astype(xp.int32)
        tier4_crl_counts += xp.sum(t4 & crl_chunk[None, :], axis=1).astype(xp.int32)

        # CRL recall at 85% threshold
        low = probs < 0.85
        crls_below_85 += xp.sum(low & crl_chunk[None, :], axis=1).astype(xp.int32)

        # Encourage early frees (helps with VRAM fragmentation under long runs)
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



def compute_metrics(probs: np.ndarray, labels: np.ndarray,
                    params: np.ndarray, xp=cp) -> Tuple[np.ndarray, dict]:
    """
    DEPRECATED in v9.3-WIN: full (C,N) metrics are VRAM-expensive.
    Kept for API compatibility, but not used by the optimizer.
    """
    # Fall back to streaming (requires features/ta_adjustments, so this wrapper cannot reproduce metrics).
    raise RuntimeError("compute_metrics() is deprecated. Use compute_metrics_streaming().")


def apply_constraints(brier_scores: np.ndarray, metrics: dict, 
                      config: OptimizerConfig, xp=cp) -> np.ndarray:
    """
    Apply constraints and return penalized scores.
    Infeasible configs get score of 1.0 (worst possible Brier).
    """
    feasible = xp.ones(len(brier_scores), dtype=xp.bool_)
    
    # Constraint 1: Minimum TIER_4 count
    feasible &= (metrics['tier4_counts'] >= config.min_tier4_count)
    
    # Constraint 2: Minimum TIER_4 CRL rate
    feasible &= (metrics['tier4_crl_rate'] >= config.min_tier4_crl_rate)
    
    # Constraint 3: Minimum CRL recall
    feasible &= (metrics['crl_recall'] >= config.min_crl_recall)
    
    # Penalize infeasible configs
    penalized_scores = xp.where(feasible, brier_scores, xp.ones_like(brier_scores))
    
    return penalized_scores, feasible


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================


def run_optimization(csv_path: str, config: OptimizerConfig,
                     resume_from: Optional[str] = None) -> dict:
    """
    Main optimization loop with GPU acceleration.

    Enhancements (Windows hardened):
      - Progress logging every `config.progress_log_every` configs tested
      - GPU VRAM scan + auto-tuned batch sizing and event chunk sizing
      - Memory-efficient streaming metric computation (no (C,N) full matrices)
      - Dynamic OOM backoff (reduces batch_size and/or chunk size on the fly)
    """
    print("\n" + "=" * 70)
    print("ODIN v9.3 GPU OPTIMIZER")
    print("=" * 70)
    print(f"Target configs:     {config.total_configs:,}")
    print(f"Requested batch max:{config.batch_size:,}")
    print(f"Primary objective:  {config.primary_objective}")
    print("Constraints:")
    print(f"  - Min TIER_4 count:    {config.min_tier4_count}")
    print(f"  - Min TIER_4 CRL rate: {config.min_tier4_crl_rate:.0%}")
    print(f"  - Min CRL recall:      {config.min_crl_recall:.0%}")

    xp = cp if GPU_AVAILABLE else np

    os.makedirs(config.output_dir, exist_ok=True)
    progress_log_path = os.path.join(config.output_dir, "progress.log")

    # Load data
    features_np, labels_np, df = load_and_preprocess_data(csv_path)
    ta_adjustments_np = get_ta_adjustment_array()

    # Transfer to GPU if available
    if GPU_AVAILABLE:
        features = cp.asarray(features_np)
        labels = cp.asarray(labels_np)
        ta_adjustments = cp.asarray(ta_adjustments_np)
        print(f"\n✅ Data transferred to GPU")
        print(f"   Features: {features.shape}, Labels: {labels.shape}")

        # Auto-tune batching based on real free VRAM and event count
        autotune_gpu_batching(config, n_events=int(features.shape[0]))
    else:
        features = features_np
        labels = labels_np
        ta_adjustments = ta_adjustments_np

    # Report effective settings after auto-tune
    est_batches = math.ceil(config.total_configs / max(1, config.batch_size))
    print("\nEffective settings:")
    print(f"  - Batch size:         {config.batch_size:,}")
    print(f"  - Event chunk size:   {getattr(config, 'event_chunk_size', 128)}")
    print(f"  - Estimated batches:  {est_batches:,}")
    print(f"  - Progress log every: {getattr(config, 'progress_log_every', 10_000_000):,} configs")

    # Initialize tracking
    best_score = 1.0              # best FEASIBLE (penalized) score
    best_raw_brier = 1.0          # best RAW (unconstrained) brier
    last_batch_raw = 1.0           # best RAW in the most recent batch
    best_params = None
    best_metrics = None
    total_tested = 0
    total_feasible = 0
    start_time = time.time()

    # Top-K tracking
    top_k = 100
    top_scores = np.ones(top_k, dtype=np.float32)
    top_params = np.zeros((top_k, N_PARAMS), dtype=np.float32)

    # Resume from checkpoint if specified
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

    # Progress logging cadence
    progress_every = int(getattr(config, "progress_log_every", 10_000_000))
    next_log_at = ((total_tested // progress_every) + 1) * progress_every if progress_every > 0 else 0

    # Write log header once
    if not os.path.exists(progress_log_path):
        _append_log(progress_log_path, "timestamp,tested,feasible,feasible_rate,best_brier,cfg_per_sec,eta_sec,gpu_free_bytes,gpu_total_bytes")

    print("\n" + "-" * 70)
    print("Starting optimization...")
    print("-" * 70)

    # Main loop (dynamic batch sizing supported)
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

                # Score + metrics (streaming)
                brier_scores, metrics = compute_metrics_streaming(
                    params=params,
                    features=features,
                    ta_adjustments=ta_adjustments,
                    labels=labels,
                    event_chunk_size=getattr(config, "event_chunk_size", 128),
                    xp=xp
                )

                # Track best RAW brier (even if constraints eliminate everything)
                if GPU_AVAILABLE:
                    batch_best_raw = float(cp.min(brier_scores).get())
                else:
                    batch_best_raw = float(np.min(brier_scores))
                last_batch_raw = batch_best_raw
                if batch_best_raw < best_raw_brier:
                    best_raw_brier = batch_best_raw

                # Apply constraints
                penalized_scores, feasible = apply_constraints(brier_scores, metrics, config, xp=xp)
                break

            except oom:
                # Dynamic backoff: shrink batch first, then chunk size
                if GPU_AVAILABLE:
                    try:
                        if mempool is not None:
                            mempool.free_all_blocks()
                        if pinned_mempool is not None:
                            pinned_mempool.free_all_blocks()
                    except Exception:
                        pass

                old_batch = current_batch
                old_chunk = int(getattr(config, "event_chunk_size", 128))

                # Reduce batch size
                current_batch = int(max(10_000, current_batch * 0.70))

                # If batch already small, reduce chunk size too
                if current_batch <= 50_000 and old_chunk > 32:
                    new_chunk = max(32, int(old_chunk * 0.75))
                    config.event_chunk_size = new_chunk

                print("⚠️ GPU OOM detected — backing off:")
                print(f"   batch_size: {old_batch:,} -> {current_batch:,}")
                if int(getattr(config, 'event_chunk_size', old_chunk)) != old_chunk:
                    print(f"   event_chunk_size: {old_chunk} -> {config.event_chunk_size}")

                # Also lower the global cap so next batches match
                config.batch_size = min(config.batch_size, current_batch)

                if current_batch < 10_000:
                    raise RuntimeError("Batch size reduced below 10k; cannot continue safely.")

        # Transfer back to CPU for tracking
        if GPU_AVAILABLE:
            penalized_scores_cpu = cp.asnumpy(penalized_scores)
            feasible_cpu = cp.asnumpy(feasible)
            params_cpu = cp.asnumpy(params)
            tier4_counts_cpu = cp.asnumpy(metrics['tier4_counts'])
            tier4_crl_rate_cpu = cp.asnumpy(metrics['tier4_crl_rate'])
            crl_recall_cpu = cp.asnumpy(metrics['crl_recall'])
        else:
            penalized_scores_cpu = penalized_scores
            feasible_cpu = feasible
            params_cpu = params
            tier4_counts_cpu = metrics['tier4_counts']
            tier4_crl_rate_cpu = metrics['tier4_crl_rate']
            crl_recall_cpu = metrics['crl_recall']

        # Update statistics
        batch_feasible = int(feasible_cpu.sum())
        total_tested += current_batch
        total_feasible += batch_feasible

        # Find best in batch
        batch_best_idx = int(np.argmin(penalized_scores_cpu))
        batch_best_score = float(penalized_scores_cpu[batch_best_idx])

        # Update global best
        if batch_best_score < best_score:
            best_score = batch_best_score
            best_params = params_cpu[batch_best_idx].copy()
            best_metrics = {
                'tier4_count': int(tier4_counts_cpu[batch_best_idx]),
                'tier4_crl_rate': float(tier4_crl_rate_cpu[batch_best_idx]),
                'crl_recall': float(crl_recall_cpu[batch_best_idx]),
            }

        # Update top-K (vectorized): merge candidates below current worst
        worst = top_scores[-1]
        cand_idx = np.where(penalized_scores_cpu < worst)[0]
        if cand_idx.size:
            cand_scores = penalized_scores_cpu[cand_idx]
            cand_params = params_cpu[cand_idx]
            merged_scores = np.concatenate([top_scores, cand_scores]).astype(np.float32)
            merged_params = np.concatenate([top_params, cand_params]).astype(np.float32)
            keep_idx = np.argpartition(merged_scores, top_k - 1)[:top_k]
            keep_idx = keep_idx[np.argsort(merged_scores[keep_idx])]
            top_scores = merged_scores[keep_idx]
            top_params = merged_params[keep_idx]

        batch_time = time.time() - batch_start
        configs_per_sec = current_batch / max(batch_time, 1e-9)

        # Progress print + log every N configs
        if progress_every > 0 and total_tested >= next_log_at:
            while total_tested >= next_log_at:
                next_log_at += progress_every

            elapsed = time.time() - start_time
            avg_cps = total_tested / max(elapsed, 1e-9)
            remaining_cfgs = config.total_configs - total_tested
            eta_sec = remaining_cfgs / max(avg_cps, 1e-9)
            feasibility_rate = 100.0 * total_feasible / max(total_tested, 1)

            free_b, total_b = _gpu_mem_info() if GPU_AVAILABLE else (0, 0)

            print(f"Progress | Tested: {total_tested:12,} | "
                  f"Feasible: {feasibility_rate:5.1f}% | "
                  f"Best Brier: {best_score:.5f} | "
                  f"Best Raw: {best_raw_brier:.5f} | "
                  f"Batch Raw: {last_batch_raw:.5f} | "
                  f"Last batch: {configs_per_sec:,.0f} cfg/s | "
                  f"Avg: {avg_cps:,.0f} cfg/s | "
                  f"ETA: {eta_sec/60:.1f}m")

            if total_feasible == 0 and total_tested >= progress_every:
                print("⚠️ Note: Feasible remains 0.0% so far. This means *all* configs are failing at least one constraint,"
                      " so the optimizer is printing the penalized score (1.00000)."
                      " If this persists, the constraints may be too strict for the current feature set.")
                print("   Quick diagnostic: the most common blocker is min_tier4_crl_rate. Try running with a lower value, e.g.:"
                      " --min-tier4-crl-rate 0.35")

            _append_log(
                progress_log_path,
                f"{datetime.now().isoformat()},{total_tested},{total_feasible},{feasibility_rate/100.0:.6f},{best_score:.8f},{avg_cps:.2f},{eta_sec:.1f},{free_b},{total_b}"
            )

        # Periodic checkpoint (by batch count, but safe under dynamic batching)
        if (batch_idx + 1) % config.checkpoint_interval == 0:
            checkpoint_path = os.path.join(config.output_dir, config.checkpoint_path)
            np.savez(checkpoint_path,
                     best_score=best_score,
                     best_params=best_params,
                     total_tested=total_tested,
                     total_feasible=total_feasible,
                     top_scores=top_scores,
                     top_params=top_params)
            print(f"   💾 Checkpoint saved: {checkpoint_path}")

        # Periodically clear GPU pools to reduce fragmentation
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
    print(f"Total time:            {total_time/60:.1f} minutes")
    print(f"Average throughput:    {total_tested/max(total_time,1e-9):,.0f} configs/sec")

    print("\n🏆 CHAMPION CONFIGURATION")
    if best_params is None:
        raise RuntimeError("No feasible configurations found; try relaxing constraints or quick mode.")
    print(f"   Brier Score:      {best_score:.5f}")
    print(f"   TIER_4 Count:     {best_metrics['tier4_count']}")
    print(f"   TIER_4 CRL Rate:  {best_metrics['tier4_crl_rate']:.1%}")
    print(f"   CRL Recall @85%:  {best_metrics['crl_recall']:.1%}")

    # Create champion config dict
    champion_config = {
        'version': '9.3',
        'optimization_date': datetime.now().isoformat(),
        'total_configs_tested': total_tested,
        'feasible_configs': total_feasible,
        'feasibility_rate': total_feasible / max(total_tested, 1),
        'performance': {
            'brier_score': float(best_score),
            'baseline_brier': 0.0996,
            'improvement_pct': 100 * (0.0996 - best_score) / 0.0996,
            'tier4_count': best_metrics['tier4_count'],
            'tier4_crl_rate': best_metrics['tier4_crl_rate'],
            'crl_recall_at_85': best_metrics['crl_recall'],
        },
        'champion_params': {name: float(best_params[i]) for i, name in enumerate(PARAMETER_NAMES)},
        'therapeutic_area_adjustments': TA_ADJUSTMENTS,
        'modality_complexity': MODALITY_COMPLEXITY,
        'indication_overrides': INDICATION_OVERRIDES,
        'constraints': {
            'min_tier4_count': config.min_tier4_count,
            'min_tier4_crl_rate': config.min_tier4_crl_rate,
            'min_crl_recall': config.min_crl_recall,
        },
        'optimizer': {
            'batch_size': int(config.batch_size),
            'event_chunk_size': int(getattr(config, "event_chunk_size", 128)),
            'progress_log_every': int(getattr(config, "progress_log_every", 10_000_000)),
            'checkpoint_interval_batches': int(config.checkpoint_interval),
        }
    }

    # Save champion config
    champion_path = os.path.join(config.output_dir, config.champion_config_path)
    with open(champion_path, 'w', encoding='utf-8') as f:
        json.dump(champion_config, f, indent=2)

    print(f"\n💾 Champion config saved to: {champion_path}")
    print(f"📝 Progress log: {progress_log_path}")

    return champion_config


def validate_champion(csv_path: str, config_path: str):
    """
    Validate champion config on the dataset and generate detailed report.
    """
    print("\n" + "=" * 70)
    print("CHAMPION VALIDATION")
    print("=" * 70)
    
    # Load config
    with open(config_path) as f:
        config = json.load(f)
    
    params = config['champion_params']
    print(f"Loaded config v{config['version']}")
    
    # Load data
    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')
    
    # Score each event
    def score_event(row):
        prob = 0.867
        
        # Designations
        if row.get('btd'): prob += params['btd_weight']
        if row.get('orphan'): prob += params['orphan_weight']
        if row.get('priority_review'): prob += params['priority_review_weight']
        if row.get('fast_track'): prob += params['fast_track_weight']
        if row.get('accelerated_approval') == True or str(row.get('accelerated_approval', '')).upper() in ('YES', 'TRUE'):
            prob += params['accelerated_approval_weight']
        
        # BTD+PR synergy
        if row.get('btd') and row.get('priority_review'):
            prob += params['btd_pr_synergy']
        
        # Triple designation
        if row.get('designation_stack_count', 0) >= 3:
            prob += params['triple_designation_bonus']
        
        # AdCom
        if row.get('had_adcom') and row.get('adcom_vote_pct'):
            vote = row['adcom_vote_pct']
            try:
                vote = float(vote)
            except Exception:
                vote = 0.0
            if vote > 1.0:
                vote = vote / 100.0
            if vote >= 0.65:
                prob += params['adcom_positive_boost']
            elif vote < 0.50:
                prob += params['adcom_negative_penalty']
        
        # Prior CRL
        if row.get('prior_crl'):
            prob += params['prior_crl_base_penalty']
            if row.get('resubmission_class') == 1:
                prob += params['class1_resubmission_boost']
            elif row.get('resubmission_class') == 2:
                prob += params['class2_resubmission_penalty']
        
        # Sponsor experience
        approvals = row.get('sponsor_prior_approvals', 0)
        if approvals >= 5:
            prob += params['experienced_sponsor_boost']
        elif approvals == 0:
            prob += params['inexperienced_sponsor_penalty']
        
        # Modality complexity
        mod = row.get('modality', 'Small Molecule')
        complexity = MODALITY_COMPLEXITY.get(mod, 0.0)
        prob += params['modality_complexity_weight'] * complexity
        
        # Therapeutic area
        ta = row.get('therapeutic_area', 'Other')
        ta_adj = TA_ADJUSTMENTS.get(ta, 0.0)
        prob += params['ta_adjustment_weight'] * ta_adj
        
        # Indication override
        indication = str(row.get('indication', '')).lower()
        for k, v in INDICATION_OVERRIDES.items():
            if k in indication:
                prob += v
                break
        
        prob = max(0.01, min(0.99, prob))
        
        # Tier
        if prob >= params['tier1_threshold']:
            tier = 'TIER_1'
        elif prob >= params['tier2_threshold']:
            tier = 'TIER_2'
        elif prob >= params['tier3_threshold']:
            tier = 'TIER_3'
        else:
            tier = 'TIER_4'
        
        return prob, tier
    
    df['prob'], df['tier'] = zip(*df.apply(score_event, axis=1))
    df['outcome_binary'] = df['outcome'].str.upper().isin(['APPROVED', 'APPROVAL']).astype(int)
    
    # Metrics
    brier = np.mean((df['prob'] - df['outcome_binary']) ** 2)
    
    print(f"\nOverall Brier Score: {brier:.5f}")
    
    # Tier breakdown
    print("\nTier Breakdown:")
    print("-" * 50)
    for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
        tier_df = df[df['tier'] == tier]
        n = len(tier_df)
        if n > 0:
            approved = tier_df['outcome_binary'].sum()
            crl = n - approved
            approval_rate = approved / n
            print(f"{tier}: {n:4d} events | {approved:3.0f} approved | "
                  f"{crl:3.0f} CRL | {100*approval_rate:.1f}% approval")
    
    # CRL recall
    crls = df[df['outcome_binary'] == 0]
    crls_below_85 = len(crls[crls['prob'] < 0.85])
    crl_recall = crls_below_85 / len(crls) if len(crls) > 0 else 0
    print(f"\nCRL Recall @85%: {crl_recall:.1%} ({crls_below_85}/{len(crls)})")
    
    return df


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='ODIN v9.3 GPU Optimizer')
    parser.add_argument('--configs', type=int, default=100_000_000,
                        help='Total configurations to test (default: 100M)')
    parser.add_argument('--batch-size', type=int, default=2_500_000,
                        help='Batch size (default: 2.5M, fits 12GB VRAM)')
    parser.add_argument('--min-tier4-count', type=int, default=None,
                        help='Override min TIER_4 count constraint (e.g., 20)')
    parser.add_argument('--min-tier4-crl-rate', type=float, default=None,
                        help='Override min TIER_4 CRL rate (0-1). Example: 0.35')
    parser.add_argument('--min-crl-recall', type=float, default=None,
                        help='Override min CRL recall (0-1). Example: 0.60')
    parser.add_argument('--progress-every', type=int, default=None,
                        help='Log progress every N configs (default: 10,000,000)')
    parser.add_argument('--csv', type=str,
                        default=os.environ.get('ODIN_CSV_PATH') or os.path.join(os.path.dirname(__file__), 'ODIN_ENRICHED_PDUFA_1349_v2.csv'),
                        help='Path to PDUFA dataset (or set ODIN_CSV_PATH)')
    parser.add_argument('--output-dir', type=str,
                        default=os.environ.get('ODIN_OUTPUT_DIR') or os.path.join(os.getcwd(), 'odin_output'),
                        help='Output directory for checkpoints/logs (or set ODIN_OUTPUT_DIR)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from checkpoint file')
    parser.add_argument('--quick', action='store_true',
                        help='Quick mode (100K configs, looser constraints)')
    parser.add_argument('--validate', type=str, default=None,
                        help='Validate existing config instead of optimizing')
    
    args = parser.parse_args()
    
    if args.validate:
        validate_champion(args.csv, args.validate)
        return
    
    # Configure optimizer
    opt_config = OptimizerConfig(
        total_configs=args.configs,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
    )
    
    if args.quick:
        print("⚡ QUICK MODE - Reduced search space")
        opt_config.total_configs = 100_000
        opt_config.batch_size = 50_000
        opt_config.min_tier4_count = 10
        opt_config.min_tier4_crl_rate = 0.35  # v9.3 feature set cannot reach 0.60+ on v2 dataset
        opt_config.min_crl_recall = 0.50
    

    # Apply overrides (CLI) for constraints / progress logging
    if args.min_tier4_count is not None:
        opt_config.min_tier4_count = int(args.min_tier4_count)
    if args.min_tier4_crl_rate is not None:
        opt_config.min_tier4_crl_rate = float(args.min_tier4_crl_rate)
    if args.min_crl_recall is not None:
        opt_config.min_crl_recall = float(args.min_crl_recall)
    if args.progress_every is not None:
        opt_config.progress_log_every = int(args.progress_every)

    # Run optimization
    champion = run_optimization(args.csv, opt_config, resume_from=args.resume)
    
    # Validate champion
    champion_path = os.path.join(opt_config.output_dir, opt_config.champion_config_path)
    validate_champion(args.csv, champion_path)


if __name__ == '__main__':
    main()