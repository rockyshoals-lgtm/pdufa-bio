#!/usr/bin/env python3
"""
ODIN v9.4 GPU Optimizer - Dynamic Memory Management Edition
============================================================
Optimized for RTX 4070 (12GB VRAM, 5888 CUDA cores)
With ADAPTIVE VRAM MANAGEMENT

DATASET: ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv (1,934 events)

Key Enhancements:
- DYNAMIC VRAM monitoring with automatic batch adjustment
- Startup memory scan to detect available resources
- Adaptive batch sizing that scales up/down during scan
- Memory fragmentation recovery with pool compaction
- Enhanced OOM recovery with exponential backoff
- Real-time memory pressure monitoring

Usage:
    python odin_v94_gpu_optimizer_dynamic.py --configs 100000000
    python odin_v94_gpu_optimizer_dynamic.py --quick
    python odin_v94_gpu_optimizer_dynamic.py --billion

Author: ODIN Development Team
Version: 9.4.1 (Dynamic Memory Edition)
Date: 2026-01-29
"""

import numpy as np
import pandas as pd
import json
import time
import math
import argparse
import os
import gc
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# DATASET PATH - UPDATED FOR v4_2_AUDITED
# =============================================================================
DEFAULT_DATASET_PATH = r"C:\Users\dcmoo\Documents\Python\ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv"

# Fallback paths for different environments
DATASET_CANDIDATES = [
    DEFAULT_DATASET_PATH,
    r"C:\Users\dcmoo\Documents\Python\ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv",
    r".\ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv",
    r"ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv",
    r"ODIN_ENRICHED_PDUFA_1904_v4_ENHANCED.csv",
    r"ODIN_v4_FIXED_DATASET.csv",
]

# =============================================================================
# GPU INITIALIZATION WITH DETAILED MEMORY SCAN
# =============================================================================

GPU_AVAILABLE = False
GPU_PROPS = {}
mempool = None
pinned_mempool = None

try:
    import cupy as cp
    GPU_AVAILABLE = True
    
    # Get detailed GPU properties
    dev_id = cp.cuda.Device().id
    props = cp.cuda.runtime.getDeviceProperties(dev_id)
    
    GPU_PROPS = {
        'name': props['name'].decode('utf-8'),
        'total_memory': props['totalGlobalMem'],
        'multiprocessor_count': props['multiProcessorCount'],
        'max_threads_per_block': props['maxThreadsPerBlock'],
        'warp_size': props['warpSize'],
        'memory_clock_rate': props.get('memoryClockRate', 0),
        'memory_bus_width': props.get('memoryBusWidth', 0),
    }
    
    mempool = cp.get_default_memory_pool()
    pinned_mempool = cp.get_default_pinned_memory_pool()
    
    print("=" * 70)
    print("🖥️  GPU MEMORY SCAN RESULTS")
    print("=" * 70)
    print(f"   Device:             {GPU_PROPS['name']}")
    print(f"   Total VRAM:         {GPU_PROPS['total_memory'] / (1024**3):.2f} GB")
    print(f"   SM Count:           {GPU_PROPS['multiprocessor_count']}")
    print(f"   Max Threads/Block:  {GPU_PROPS['max_threads_per_block']}")
    
    # Initial free memory scan
    free_mem, total_mem = cp.cuda.runtime.memGetInfo()
    print(f"   Available VRAM:     {free_mem / (1024**3):.2f} GB ({100*free_mem/total_mem:.1f}%)")
    print("=" * 70)
    
except ImportError:
    print("⚠️  CuPy not available - using CPU (NumPy)")
    cp = np


# =============================================================================
# DYNAMIC MEMORY MANAGER
# =============================================================================

class DynamicMemoryManager:
    """
    Manages GPU memory dynamically, adjusting batch sizes based on real-time
    memory availability and pressure.
    """
    
    def __init__(self, target_utilization: float = 0.85, 
                 min_batch_size: int = 50_000,
                 max_batch_size: int = 5_000_000):
        """
        Args:
            target_utilization: Target fraction of free VRAM to use (0.85 = 85%)
            min_batch_size: Minimum batch size floor
            max_batch_size: Maximum batch size ceiling
        """
        self.target_utilization = target_utilization
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.current_batch_size = max_batch_size
        self.current_chunk_size = 128
        
        # Tracking
        self.oom_count = 0
        self.successful_batches = 0
        self.batch_history = []  # (batch_size, success, memory_used)
        self.last_adjustment_time = time.time()
        self.adjustment_cooldown = 5.0  # seconds
        
        # Memory stats
        self.peak_memory_used = 0
        self.last_free_memory = 0
        self.memory_headroom_gb = 1.5  # Reserve 1.5GB headroom
        
        if GPU_AVAILABLE:
            self._initial_scan()
    
    def _initial_scan(self) -> None:
        """Perform initial memory scan and set conservative batch size."""
        self._free_pools()
        
        free_bytes, total_bytes = cp.cuda.runtime.memGetInfo()
        self.last_free_memory = free_bytes
        
        # Calculate safe working memory (leave headroom)
        headroom_bytes = int(self.memory_headroom_gb * 1024**3)
        safe_working_memory = max(0, free_bytes - headroom_bytes)
        
        # Estimate memory per config (rough: ~200 bytes per config for our use case)
        bytes_per_config = 200  # Conservative estimate
        
        # Calculate initial batch size
        estimated_safe_batch = int(safe_working_memory / bytes_per_config)
        estimated_safe_batch = max(self.min_batch_size, 
                                   min(self.max_batch_size, estimated_safe_batch))
        
        # Start at 70% of estimated safe batch (conservative)
        self.current_batch_size = int(estimated_safe_batch * 0.70)
        
        print(f"\n🧠 DYNAMIC MEMORY MANAGER INITIALIZED")
        print(f"   Free VRAM:          {free_bytes / (1024**3):.2f} GB")
        print(f"   Reserved Headroom:  {self.memory_headroom_gb:.1f} GB")
        print(f"   Safe Working:       {safe_working_memory / (1024**3):.2f} GB")
        print(f"   Initial Batch Size: {self.current_batch_size:,}")
        print(f"   Target Utilization: {self.target_utilization*100:.0f}%")
    
    def _free_pools(self) -> None:
        """Free CuPy memory pools."""
        if not GPU_AVAILABLE:
            return
        try:
            if mempool is not None:
                mempool.free_all_blocks()
            if pinned_mempool is not None:
                pinned_mempool.free_all_blocks()
            cp.cuda.runtime.deviceSynchronize()
        except Exception:
            pass
    
    def get_memory_status(self) -> Dict:
        """Get current GPU memory status."""
        if not GPU_AVAILABLE:
            return {'free': 0, 'total': 0, 'used': 0, 'utilization': 0}
        
        free_bytes, total_bytes = cp.cuda.runtime.memGetInfo()
        used_bytes = total_bytes - free_bytes
        
        return {
            'free': free_bytes,
            'total': total_bytes,
            'used': used_bytes,
            'utilization': used_bytes / total_bytes if total_bytes > 0 else 0,
            'free_gb': free_bytes / (1024**3),
            'used_gb': used_bytes / (1024**3),
        }
    
    def should_increase_batch(self) -> bool:
        """Check if we should try increasing batch size."""
        if not GPU_AVAILABLE:
            return False
        
        # Don't adjust if cooldown not elapsed
        if time.time() - self.last_adjustment_time < self.adjustment_cooldown:
            return False
        
        # Need at least 10 successful batches before considering increase
        if self.successful_batches < 10:
            return False
        
        # Check memory utilization
        status = self.get_memory_status()
        current_util = status['utilization']
        
        # If we're using less than 70% of target, consider increasing
        if current_util < (self.target_utilization * 0.70):
            return True
        
        return False
    
    def get_optimal_batch_size(self) -> Tuple[int, int]:
        """
        Get optimal batch size based on current memory state.
        Returns (batch_size, chunk_size).
        """
        if not GPU_AVAILABLE:
            return (self.current_batch_size, self.current_chunk_size)
        
        status = self.get_memory_status()
        free_gb = status['free_gb']
        
        # If memory is getting tight, reduce batch size
        if free_gb < self.memory_headroom_gb * 1.2:
            new_batch = int(self.current_batch_size * 0.80)
            new_batch = max(self.min_batch_size, new_batch)
            if new_batch < self.current_batch_size:
                self.current_batch_size = new_batch
                self.last_adjustment_time = time.time()
                print(f"   📉 Memory pressure - batch reduced to {new_batch:,}")
        
        # If we have excess memory and conditions are good, try increasing
        elif self.should_increase_batch():
            new_batch = int(self.current_batch_size * 1.15)
            new_batch = min(self.max_batch_size, new_batch)
            if new_batch > self.current_batch_size:
                self.current_batch_size = new_batch
                self.last_adjustment_time = time.time()
                print(f"   📈 Memory available - batch increased to {new_batch:,}")
        
        return (self.current_batch_size, self.current_chunk_size)
    
    def report_batch_success(self, batch_size: int, memory_used: int = 0) -> None:
        """Report a successful batch execution."""
        self.successful_batches += 1
        self.batch_history.append((batch_size, True, memory_used))
        if memory_used > self.peak_memory_used:
            self.peak_memory_used = memory_used
    
    def report_oom(self, batch_size: int) -> Tuple[int, int]:
        """
        Report an OOM error and get recovered batch/chunk sizes.
        Uses exponential backoff for repeated OOMs.
        """
        self.oom_count += 1
        self.batch_history.append((batch_size, False, 0))
        self.successful_batches = 0  # Reset success counter
        
        # Free memory pools
        self._free_pools()
        gc.collect()
        
        # Exponential backoff based on recent OOM count
        recent_ooms = sum(1 for _, success, _ in self.batch_history[-10:] if not success)
        backoff_factor = 0.70 ** min(recent_ooms, 3)  # 0.70, 0.49, 0.34
        
        new_batch = int(batch_size * backoff_factor)
        new_batch = max(self.min_batch_size, new_batch)
        
        # If batch is already at minimum, reduce chunk size
        if new_batch <= self.min_batch_size and self.current_chunk_size > 32:
            self.current_chunk_size = max(32, int(self.current_chunk_size * 0.75))
            print(f"   ⚠️  OOM #{self.oom_count} - chunk reduced to {self.current_chunk_size}")
        
        self.current_batch_size = new_batch
        self.last_adjustment_time = time.time()
        
        print(f"   ⚠️  OOM #{self.oom_count} - batch reduced to {new_batch:,} "
              f"(backoff factor: {backoff_factor:.2f})")
        
        return (self.current_batch_size, self.current_chunk_size)
    
    def periodic_maintenance(self, batch_idx: int, maintenance_interval: int = 25) -> None:
        """Perform periodic memory maintenance."""
        if not GPU_AVAILABLE:
            return
        
        if (batch_idx + 1) % maintenance_interval == 0:
            self._free_pools()
            gc.collect()
    
    def get_stats_summary(self) -> str:
        """Get summary statistics string."""
        total_batches = len(self.batch_history)
        success_rate = 100 * self.successful_batches / max(total_batches, 1)
        
        status = self.get_memory_status()
        
        return (f"Batches: {total_batches} | Success Rate: {success_rate:.0f}% | "
                f"OOMs: {self.oom_count} | VRAM: {status['used_gb']:.1f}/{status['free_gb']:.1f}GB")


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for the GPU optimizer."""
    # Search parameters
    total_configs: int = 100_000_000
    batch_size: int = 2_500_000  # Initial; dynamically adjusted
    event_chunk_size: int = 128  # Initial; dynamically adjusted
    progress_log_every: int = 10_000_000
    
    # Dynamic memory settings
    target_memory_utilization: float = 0.85
    min_batch_size: int = 50_000
    max_batch_size: int = 5_000_000
    memory_headroom_gb: float = 1.5
    
    # Objectives and constraints (v9.4 calibrated)
    primary_objective: str = 'brier'
    min_tier4_count: int = 15
    min_tier4_crl_rate: float = 0.50
    min_crl_recall: float = 0.55
    
    # Checkpoint settings
    checkpoint_interval: int = 50
    checkpoint_path: str = 'odin_v94_checkpoint.npz'
    
    # Output settings
    output_dir: str = 'odin_output'
    champion_config_path: str = 'ODIN_v94_CHAMPION_CONFIG.json'
    improvement_log_path: str = 'odin_v94_improvements.log'


# =============================================================================
# v9.4 PARAMETER BOUNDS (PATCHED FOR HIGHER FEASIBILITY)
# =============================================================================

PARAMETER_BOUNDS = {
    # Designation weights
    'btd_weight': (0.02, 0.12),
    'orphan_weight': (0.01, 0.08),
    'priority_review_weight': (0.03, 0.15),
    'fast_track_weight': (0.01, 0.06),
    'accelerated_approval_weight': (0.02, 0.08),
    
    # AdCom adjustments
    'adcom_high_boost': (0.04, 0.15),
    'adcom_mid_penalty': (-0.12, 0.0),
    'adcom_low_penalty': (-0.25, -0.10),
    
    # Prior CRL / Resubmission (PATCHED bounds for feasibility)
    'prior_crl_base_penalty': (-0.18, -0.08),  # WIDENED from (-0.15, -0.04)
    'crl_count_multiplier_2': (1.2, 1.8),
    'crl_count_multiplier_3': (1.5, 2.2),
    'crl_count_multiplier_4plus': (1.8, 2.8),
    'class1_resubmission_boost': (0.10, 0.22),
    'class2_resubmission_boost': (0.02, 0.08),
    
    # Sponsor experience
    'experienced_sponsor_boost': (0.02, 0.10),
    'inexperienced_sponsor_penalty': (-0.12, -0.03),
    
    # Modality adjustments
    'gene_therapy_penalty': (-0.12, -0.02),
    'cell_therapy_penalty': (-0.10, -0.01),
    'rna_therapy_penalty': (-0.10, -0.01),
    
    # Modality-indication interaction
    'modality_indication_weight': (0.3, 1.2),
    
    # Therapeutic area adjustment (PATCHED for feasibility)
    'ta_adjustment_weight': (0.85, 1.2),  # NARROWED from (0.6, 1.1)
    
    # Indication override weight
    'indication_override_weight': (0.5, 1.5),
    
    # Tier thresholds (PATCHED for feasibility)
    'tier1_threshold': (0.82, 0.92),
    'tier2_threshold': (0.68, 0.80),
    'tier3_threshold': (0.58, 0.68),  # RAISED from (0.52, 0.65)
}

PARAMETER_NAMES = list(PARAMETER_BOUNDS.keys())
N_PARAMS = len(PARAMETER_NAMES)

# Therapeutic area adjustments (from v9.1 historical data)
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

# Modality adjustments
MODALITY_ADJUSTMENTS = {
    "Small Molecule": 0.00,
    "Peptide": -0.01,
    "Antibody": -0.02,
    "ADC": -0.04,
    "Vaccine": +0.02,
    "Biosimilar": +0.03,
    "RNA Therapy": -0.05,
    "Cell Therapy": -0.05,
    "Cell/Gene Therapy": -0.06,
    "Gene Therapy": -0.06,
}

# Modality-Indication Interactions
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

# Indication-specific overrides
INDICATION_OVERRIDES = {
    "leukocyte adhesion deficiency": -0.05,
    "lad-i": -0.05,
    "sickle cell": -0.04,
    "beta-thalassemia": -0.04,
    "myelodysplastic": -0.03,
    "acute myeloid leukemia": -0.03,
    "opioid use disorder": -0.05,
    "opioid-induced constipation": -0.04,
    "chronic pain": -0.04,
    "postoperative pain": -0.05,
    "diabetic kidney": -0.04,
    "iga nephropathy": -0.04,
    "lupus nephritis": -0.03,
    "dry eye": -0.03,
    "diabetic macular edema": -0.03,
    "geographic atrophy": -0.03,
    "spinal muscular atrophy": +0.02,
    "nsclc": +0.01,
    "breast cancer": +0.01,
    "melanoma": +0.01,
    "multiple myeloma": +0.01,
}


# =============================================================================
# UTILITIES
# =============================================================================

def _format_bytes(n: int) -> str:
    """Human-readable bytes."""
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:,.1f}{unit}" if unit != "B" else f"{n:,.0f}{unit}"
        n /= 1024.0
    return f"{n:,.1f}PB"


def _append_log(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


# =============================================================================
# DATA LOADING
# =============================================================================

def load_and_preprocess_data(csv_path: str) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Load PDUFA dataset and convert to GPU-ready arrays."""
    csv_path = os.path.expanduser(os.path.expandvars(csv_path))
    
    # Try multiple locations
    if not os.path.exists(csv_path):
        for candidate in DATASET_CANDIDATES:
            if os.path.exists(candidate):
                csv_path = candidate
                break
        else:
            raise FileNotFoundError(
                f"Could not find dataset CSV.\n"
                f"Expected: {DEFAULT_DATASET_PATH}\n"
                f"Please ensure ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv is in the correct location."
            )
    
    print(f"\n📂 Loading: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')
    print(f"   Events: {len(df)}")
    
    # Encode outcome
    df['outcome_binary'] = df['outcome'].str.upper().isin(['APPROVED', 'APPROVAL']).astype(int)
    
    # Encode therapeutic area
    ta_list = list(TA_ADJUSTMENTS.keys())
    df['ta_idx'] = df['therapeutic_area'].apply(
        lambda x: ta_list.index(x) if x in ta_list else ta_list.index('Other')
    )
    
    # Encode modality
    df['modality_adj'] = df['modality'].map(MODALITY_ADJUSTMENTS).fillna(0.0)
    df['modality_lower'] = df['modality'].str.lower().fillna('')
    df['is_gene_therapy'] = df['modality_lower'].str.contains('gene').astype(np.float32)
    df['is_cell_therapy'] = df['modality_lower'].str.contains('cell').astype(np.float32)
    df['is_rna_therapy'] = df['modality_lower'].str.contains('rna').astype(np.float32)
    
    # Compute interactions
    df['indication_lower'] = df['indication'].str.lower().fillna('')
    df['ta_lower'] = df['therapeutic_area'].str.lower().fillna('')
    
    def compute_interaction(row):
        total = 0.0
        modality = row['modality_lower']
        indication = row['indication_lower']
        ta = row['ta_lower']
        for (mod_key, ind_key), penalty in MODALITY_INDICATION_INTERACTIONS.items():
            if mod_key.lower() in modality and (ind_key.lower() in indication or ind_key.lower() in ta):
                total += penalty
        return total
    
    df['interaction_penalty'] = df.apply(compute_interaction, axis=1)
    
    # Indication overrides
    def compute_indication_override(indication):
        indication = str(indication).lower()
        for k, v in INDICATION_OVERRIDES.items():
            if k.lower() in indication:
                return v
        return 0.0
    
    df['indication_override'] = df['indication'].apply(compute_indication_override)
    
    # Prior CRL count (infer from data)
    if 'prior_crl_count' not in df.columns:
        df['prior_crl_count'] = df['prior_crl'].fillna(False).astype(int)
    
    # Build feature matrix
    features = np.column_stack([
        df['btd'].fillna(False).astype(bool).astype(np.float32).values,
        df['orphan'].fillna(False).astype(bool).astype(np.float32).values,
        df['priority_review'].fillna(False).astype(bool).astype(np.float32).values,
        df['fast_track'].fillna(False).astype(bool).astype(np.float32).values,
        df['accelerated_approval'].fillna(False).astype(bool).astype(np.float32).values,
        df['had_adcom'].fillna(False).astype(bool).astype(np.float32).values,
        (pd.to_numeric(df.get('adcom_vote_pct', 0.0), errors='coerce')
           .fillna(0.0)
           .apply(lambda x: x/100.0 if x > 1.0 else x)
           .clip(0.0, 1.0)
           .values.astype(np.float32)),
        df['prior_crl'].fillna(False).astype(bool).astype(np.float32).values,
        df['prior_crl_count'].fillna(0).values.astype(np.float32),
        df['resubmission_class'].fillna(0).values.astype(np.float32),
        df['sponsor_prior_approvals'].fillna(0).values.astype(np.float32),
        df['ta_idx'].values.astype(np.float32),
        df['modality_adj'].values.astype(np.float32),
        df['is_gene_therapy'].values.astype(np.float32),
        df['is_cell_therapy'].values.astype(np.float32),
        df['is_rna_therapy'].values.astype(np.float32),
        df['interaction_penalty'].values.astype(np.float32),
        df['indication_override'].values.astype(np.float32),
    ]).astype(np.float32)
    
    labels = df['outcome_binary'].values.astype(np.float32)
    
    n_approved = labels.sum()
    n_crl = len(labels) - n_approved
    print(f"   Approvals: {int(n_approved)} ({100*n_approved/len(labels):.1f}%)")
    print(f"   CRLs:      {int(n_crl)} ({100*n_crl/len(labels):.1f}%)")
    print(f"   Features:  {features.shape[1]} columns")
    
    # Check resubmission_class population
    resub_count = (df['resubmission_class'] > 0).sum()
    print(f"   Resubmissions: {resub_count} events")
    
    return features, labels, df


def get_ta_adjustment_array() -> np.ndarray:
    """Get TA adjustments as array indexed by ta_idx."""
    ta_list = list(TA_ADJUSTMENTS.keys())
    return np.array([TA_ADJUSTMENTS[ta] for ta in ta_list], dtype=np.float32)


# =============================================================================
# GPU SCORING KERNEL
# =============================================================================

def generate_random_params(n_configs: int, xp=np) -> np.ndarray:
    """Generate random parameter configurations within bounds."""
    params = xp.zeros((n_configs, N_PARAMS), dtype=xp.float32)
    for i, name in enumerate(PARAMETER_NAMES):
        low, high = PARAMETER_BOUNDS[name]
        params[:, i] = xp.random.uniform(low, high, n_configs).astype(xp.float32)
    return params


def gpu_batch_score_v94(params, features, ta_adjustments, xp=cp):
    """v9.4 Vectorized scoring with all features."""
    n_configs = params.shape[0]
    n_events = features.shape[0]
    
    # Extract parameters
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
    class2_boost = params[:, 13]
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
    
    # Extract features
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
    
    # Base probability
    probs = xp.full((n_configs, n_events), 0.867, dtype=xp.float32)
    
    # Designations
    probs += xp.outer(btd_w, btd)
    probs += xp.outer(orphan_w, orphan)
    probs += xp.outer(pr_w, pr)
    probs += xp.outer(ft_w, ft)
    probs += xp.outer(aa_w, aa)
    
    # AdCom
    adcom_high_mask = (had_adcom * (adcom_vote >= 0.65)).astype(xp.float32)
    adcom_mid_mask = (had_adcom * (adcom_vote >= 0.50) * (adcom_vote < 0.65)).astype(xp.float32)
    adcom_low_mask = (had_adcom * (adcom_vote < 0.50) * (adcom_vote > 0)).astype(xp.float32)
    probs += xp.outer(adcom_high, adcom_high_mask)
    probs += xp.outer(adcom_mid, adcom_mid_mask)
    probs += xp.outer(adcom_low, adcom_low_mask)
    
    # Prior CRL with multiplier
    crl_1_mask = (prior_crl * (crl_count <= 1)).astype(xp.float32)
    crl_2_mask = (prior_crl * (crl_count == 2)).astype(xp.float32)
    crl_3_mask = (prior_crl * (crl_count == 3)).astype(xp.float32)
    crl_4plus_mask = (prior_crl * (crl_count >= 4)).astype(xp.float32)
    
    probs += xp.outer(prior_crl_base, crl_1_mask)
    probs += xp.outer(prior_crl_base * crl_mult_2, crl_2_mask)
    probs += xp.outer(prior_crl_base * crl_mult_3, crl_3_mask)
    probs += xp.outer(prior_crl_base * crl_mult_4plus, crl_4plus_mask)
    
    # Resubmission class (both boosts in v9.4)
    class1_mask = (prior_crl * (resub_class == 1)).astype(xp.float32)
    class2_mask = (prior_crl * (resub_class == 2)).astype(xp.float32)
    probs += xp.outer(class1_boost, class1_mask)
    probs += xp.outer(class2_boost, class2_mask)
    
    # Sponsor experience
    exp_mask = (sponsor_approvals >= 5).astype(xp.float32)
    inexp_mask = (sponsor_approvals == 0).astype(xp.float32)
    probs += xp.outer(exp_sponsor, exp_mask)
    probs += xp.outer(inexp_sponsor, inexp_mask)
    
    # Modality
    probs += modality_adj
    probs += xp.outer(gene_pen, is_gene)
    probs += xp.outer(cell_pen, is_cell)
    probs += xp.outer(rna_pen, is_rna)
    
    # Modality-indication interaction
    probs += xp.outer(mod_ind_w, interaction_pen)
    
    # Therapeutic area
    ta_adj_values = ta_adjustments[ta_idx]
    probs += xp.outer(ta_w, ta_adj_values)
    
    # Indication override
    probs += xp.outer(ind_override_w, ind_override)
    
    # Clamp
    probs = xp.clip(probs, 0.01, 0.99)
    
    return probs


def compute_metrics_streaming(params, features, ta_adjustments, labels, 
                              event_chunk_size: int = 128, xp=cp):
    """Memory-efficient metrics computation."""
    n_configs = params.shape[0]
    n_events = features.shape[0]
    chunk = max(16, min(int(event_chunk_size), n_events))

    brier_sum = xp.zeros((n_configs,), dtype=xp.float32)
    tier4_counts = xp.zeros((n_configs,), dtype=xp.int32)
    tier4_crl_counts = xp.zeros((n_configs,), dtype=xp.int32)
    crls_below_85 = xp.zeros((n_configs,), dtype=xp.int32)

    crl_mask_all = (labels < 0.5)
    total_crls = xp.sum(crl_mask_all).astype(xp.float32)

    t3 = params[:, 24]

    for start in range(0, n_events, chunk):
        end = min(start + chunk, n_events)
        feat_chunk = features[start:end]
        lab_chunk = labels[start:end]
        crl_chunk = (lab_chunk < 0.5)

        probs = gpu_batch_score_v94(params, feat_chunk, ta_adjustments, xp=xp)

        diff = probs - lab_chunk
        diff *= diff
        brier_sum += xp.sum(diff, axis=1).astype(xp.float32)

        t4 = probs < t3[:, None]
        tier4_counts += xp.sum(t4, axis=1).astype(xp.int32)
        tier4_crl_counts += xp.sum(t4 & crl_chunk[None, :], axis=1).astype(xp.int32)

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


def apply_constraints(brier_scores, metrics, config: OptimizerConfig, xp=cp):
    """Apply constraints and return penalized scores."""
    feasible = xp.ones(len(brier_scores), dtype=xp.bool_)
    
    feasible &= (metrics['tier4_counts'] >= config.min_tier4_count)
    feasible &= (metrics['tier4_crl_rate'] >= config.min_tier4_crl_rate)
    feasible &= (metrics['crl_recall'] >= config.min_crl_recall)
    
    penalized_scores = xp.where(feasible, brier_scores, xp.ones_like(brier_scores))
    
    return penalized_scores, feasible


# =============================================================================
# IMPROVEMENT LOGGER
# =============================================================================

class ImprovementLogger:
    """Logs every configuration that beats the previous best."""
    
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.improvement_count = 0
        
        header = "timestamp,improvement_num,brier_score,improvement_pct,tier4_count,tier4_crl_rate,crl_recall,params_json"
        _append_log(self.log_path, header)
    
    def log_improvement(self, brier_score: float, previous_best: float,
                        metrics: dict, params: np.ndarray) -> None:
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
        
        print(f"   🎯 IMPROVEMENT #{self.improvement_count}: {previous_best:.5f} → {brier_score:.5f} "
              f"({improvement_pct:+.2f}%)")


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

def run_optimization(csv_path: str, config: OptimizerConfig,
                     resume_from: Optional[str] = None) -> dict:
    """Main optimization loop with dynamic memory management."""
    print("\n" + "=" * 70)
    print("ODIN v9.4 GPU OPTIMIZER - DYNAMIC MEMORY EDITION")
    print("=" * 70)
    print(f"Dataset:            {csv_path}")
    print(f"Target configs:     {config.total_configs:,}")
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

    # Initialize components
    improvement_logger = ImprovementLogger(improvement_log_path)
    memory_manager = DynamicMemoryManager(
        target_utilization=config.target_memory_utilization,
        min_batch_size=config.min_batch_size,
        max_batch_size=config.max_batch_size
    )

    # Load data
    features_np, labels_np, df = load_and_preprocess_data(csv_path)
    ta_adjustments_np = get_ta_adjustment_array()

    # Transfer to GPU
    if GPU_AVAILABLE:
        features = cp.asarray(features_np)
        labels = cp.asarray(labels_np)
        ta_adjustments = cp.asarray(ta_adjustments_np)
        print(f"\n✅ Data transferred to GPU")
    else:
        features = features_np
        labels = labels_np
        ta_adjustments = ta_adjustments_np

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
        print(f"\n📂 Resuming from: {resume_from}")
        checkpoint = np.load(resume_from, allow_pickle=True)
        best_score = float(checkpoint['best_score'])
        best_params = checkpoint['best_params']
        total_tested = int(checkpoint['total_tested'])
        total_feasible = int(checkpoint.get('total_feasible', 0))
        print(f"   Resumed at tested={total_tested:,}, best={best_score:.5f}")

    progress_every = int(config.progress_log_every)
    next_log_at = ((total_tested // progress_every) + 1) * progress_every if progress_every > 0 else 0

    if not os.path.exists(progress_log_path):
        _append_log(progress_log_path, "timestamp,tested,feasible,feasible_rate,best_brier,cfg_per_sec,eta_sec,batch_size,vram_used_gb")

    print("\n" + "-" * 70)
    print("Starting optimization with dynamic memory management...")
    print("-" * 70)

    batch_idx = 0
    oom = getattr(cp.cuda.memory, "OutOfMemoryError", RuntimeError) if GPU_AVAILABLE else RuntimeError

    while total_tested < config.total_configs:
        remaining = config.total_configs - total_tested
        
        # Get dynamically adjusted batch size
        current_batch, current_chunk = memory_manager.get_optimal_batch_size()
        current_batch = min(current_batch, remaining)

        batch_start = time.time()

        # Retry loop for OOM
        while True:
            try:
                params = generate_random_params(current_batch, xp=xp)

                brier_scores, metrics = compute_metrics_streaming(
                    params=params,
                    features=features,
                    ta_adjustments=ta_adjustments,
                    labels=labels,
                    event_chunk_size=current_chunk,
                    xp=xp
                )

                if GPU_AVAILABLE:
                    batch_best_raw = float(cp.min(brier_scores).get())
                else:
                    batch_best_raw = float(np.min(brier_scores))
                
                if batch_best_raw < best_raw_brier:
                    best_raw_brier = batch_best_raw

                penalized_scores, feasible = apply_constraints(brier_scores, metrics, config, xp=xp)
                
                # Report success to memory manager
                mem_status = memory_manager.get_memory_status()
                memory_manager.report_batch_success(current_batch, mem_status['used'])
                break

            except oom:
                current_batch, current_chunk = memory_manager.report_oom(current_batch)
                
                if current_batch < config.min_batch_size:
                    raise RuntimeError("Batch size below minimum; cannot continue.")

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

        # Update global best
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

            improvement_logger.log_improvement(batch_best_score, best_score, 
                                               new_best_metrics, new_best_params)
            best_score = batch_best_score
            best_params = new_best_params
            best_metrics = new_best_metrics

        # Top-K update
        if total_tested >= next_log_at:
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
            mem_status = memory_manager.get_memory_status()

            print(f"Progress | Tested: {total_tested:12,} | "
                  f"Feasible: {feasibility_rate:5.1f}% | "
                  f"Best: {best_score:.5f} | "
                  f"Batch: {current_batch:,} | "
                  f"VRAM: {mem_status['used_gb']:.1f}GB | "
                  f"{configs_per_sec:,.0f} cfg/s | "
                  f"ETA: {eta_sec/60:.1f}m")

            _append_log(progress_log_path,
                f"{datetime.now().isoformat()},{total_tested},{total_feasible},"
                f"{feasibility_rate/100.0:.6f},{best_score:.8f},{avg_cps:.2f},{eta_sec:.1f},"
                f"{current_batch},{mem_status['used_gb']:.2f}")

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

        # Periodic memory maintenance
        memory_manager.periodic_maintenance(batch_idx)

        batch_idx += 1

    total_time = time.time() - start_time

    # Final results
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"Total configs tested:  {total_tested:,}")
    print(f"Feasible configs:      {total_feasible:,} ({100*total_feasible/max(total_tested,1):.1f}%)")
    print(f"Total improvements:    {improvement_logger.improvement_count}")
    print(f"Total OOMs recovered:  {memory_manager.oom_count}")
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
        'version': '9.4.1',
        'optimization_date': datetime.now().isoformat(),
        'dataset': csv_path,
        'total_configs_tested': total_tested,
        'feasible_configs': total_feasible,
        'feasibility_rate': total_feasible / max(total_tested, 1),
        'total_improvements': improvement_logger.improvement_count,
        'oom_recoveries': memory_manager.oom_count,
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

    # Save top-K configs
    topk_path = os.path.join(config.output_dir, 'odin_v94_top100_configs.json')
    top_configs = []
    for i in range(min(len(top_scores), top_k)):
        if top_scores[i] < 1.0:
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
    parser = argparse.ArgumentParser(
        description='ODIN v9.4 GPU Optimizer - Dynamic Memory Management Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python odin_v94_gpu_optimizer_dynamic.py --quick           # Quick 1M scan
  python odin_v94_gpu_optimizer_dynamic.py --configs 100000000  # 100M scan
  python odin_v94_gpu_optimizer_dynamic.py --billion         # 1B full scan
  python odin_v94_gpu_optimizer_dynamic.py --resume checkpoint.npz
        """
    )
    
    parser.add_argument('--configs', type=int, default=100_000_000,
                        help='Total configurations to test (default: 100M)')
    parser.add_argument('--batch-size', type=int, default=2_500_000,
                        help='Initial batch size (auto-tuned)')
    parser.add_argument('--min-batch-size', type=int, default=50_000,
                        help='Minimum batch size floor')
    parser.add_argument('--max-batch-size', type=int, default=5_000_000,
                        help='Maximum batch size ceiling')
    parser.add_argument('--memory-headroom', type=float, default=1.5,
                        help='VRAM headroom to reserve in GB')
    parser.add_argument('--target-utilization', type=float, default=0.85,
                        help='Target VRAM utilization (0.0-1.0)')
    
    parser.add_argument('--min-tier4-count', type=int, default=15,
                        help='Min TIER_4 count constraint')
    parser.add_argument('--min-tier4-crl-rate', type=float, default=0.50,
                        help='Min TIER_4 CRL rate')
    parser.add_argument('--min-crl-recall', type=float, default=0.55,
                        help='Min CRL recall at 85%% threshold')
    
    parser.add_argument('--csv', type=str, default=DEFAULT_DATASET_PATH,
                        help='Path to PDUFA dataset')
    parser.add_argument('--output-dir', type=str, default='odin_output',
                        help='Output directory')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from checkpoint file')
    
    parser.add_argument('--quick', action='store_true',
                        help='Quick mode (1M configs)')
    parser.add_argument('--billion', action='store_true',
                        help='Billion config mode (1B configs)')
    
    args = parser.parse_args()
    
    # Configure optimizer
    opt_config = OptimizerConfig(
        total_configs=args.configs,
        batch_size=args.batch_size,
        min_batch_size=args.min_batch_size,
        max_batch_size=args.max_batch_size,
        memory_headroom_gb=args.memory_headroom,
        target_memory_utilization=args.target_utilization,
        output_dir=args.output_dir,
        min_tier4_count=args.min_tier4_count,
        min_tier4_crl_rate=args.min_tier4_crl_rate,
        min_crl_recall=args.min_crl_recall,
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
