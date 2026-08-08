#!/usr/bin/env python3
"""
ODIN v9.5 GPU Optimizer - Production Ready
===========================================
Fixes from v9.4 analysis + support for v4.2 audited dataset (1,934 records)

KEY CHANGES FROM v9.4:
1. TIER4_CRL_MIN = 0.70 (was 0.50) - Force CRL detection
2. TIER4_COUNT_MIN = 15 (was 5) - Statistical significance
3. Composite scoring: Balance Brier + Tier4 CRL
4. Expanded bounds for parameters that hit limits
5. RNA Therapy separate penalty (55.6% CRL rate!)
6. Era weighting for pre/post-2020 bias
7. Warm start from v9.1 champion

Usage:
    python odin_v95_gpu_optimizer.py
"""

print("[1/5] Loading standard libs...", flush=True)
import os
import sys
import json
import time
import glob
from datetime import datetime
from pathlib import Path

print("[2/5] Loading numpy...", flush=True)
import numpy as np

print("[3/5] Loading pandas...", flush=True)
import pandas as pd

print("[4/5] Imports complete!", flush=True)

# GPU setup - LAZY initialization
GPU_AVAILABLE = None
cp = None
FORCE_CPU = False  # Set True to skip GPU

def init_gpu():
    """Initialize GPU with timeout protection."""
    global GPU_AVAILABLE, cp
    
    if GPU_AVAILABLE is not None:
        return GPU_AVAILABLE
    
    if FORCE_CPU:
        print("⚠️ FORCE_CPU=True - Using NumPy", flush=True)
        cp = np
        GPU_AVAILABLE = False
        return False
    
    print("Checking GPU availability...", flush=True)
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c", "import cupy; print('ok')"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0 or 'ok' not in result.stdout:
            raise Exception(f"CuPy test failed: {result.stderr}")
        
        print("   CuPy test passed, importing...", flush=True)
        import cupy as _cp
        
        test = _cp.zeros(100)
        del test
        _cp.get_default_memory_pool().free_all_blocks()
        
        cp = _cp
        GPU_AVAILABLE = True
        print(f"✅ GPU acceleration enabled", flush=True)
        
    except Exception as e:
        print(f"⚠️ GPU not available ({e}) - using NumPy", flush=True)
        cp = np
        GPU_AVAILABLE = False
    
    return GPU_AVAILABLE


# =============================================================================
# CONFIGURATION - v9.5 IMPROVEMENTS
# =============================================================================

# Dataset - YOUR LOCAL PATH
DATASET_PATH = r"C:\Users\dcmoo\Documents\Python\ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv"

# Output
OUTPUT_DIR = Path(r"C:\Users\dcmoo\Documents\Python\odin_optimization_output")
CHECKPOINT_FILE = OUTPUT_DIR / "annealing_checkpoint_v95.json"

# Optimization settings
TOTAL_ITERATIONS = 1_000_000_000  # 1 billion
MIN_BATCH_SIZE = 10_000
MAX_BATCH_SIZE = 100_000

# Annealing schedule
INITIAL_TEMPERATURE = 1.0
FINAL_TEMPERATURE = 0.01
COOLING_RATE = 0.9995
REHEAT_THRESHOLD = 50_000_000

# Elite population
ELITE_SIZE = 25  # Increased from 20
LOCAL_SEARCH_PROB = 0.7


# =============================================================================
# v9.5 CONSTRAINTS (TIGHTENED)
# =============================================================================

TIER1_MIN = 0.80              # Was 0.78
TIER2_MAX = 0.75              # Was 0.80 - tightened
TIER1_APPROVAL_MIN = 0.92     # Was 0.90
TIER4_CRL_MIN = 0.70          # CRITICAL: Was 0.50
TIER4_COUNT_MIN = 15          # Was 5

# Composite scoring weights
COMPOSITE_WEIGHTS = {
    'brier': 1.0,
    'tier4_crl': 0.35,        # Heavy weight on CRL detection
    'tier4_target': 0.85,     # Target 85% CRL rate
}


# =============================================================================
# v9.5 PARAMETER BOUNDS (EXPANDED + FIXED)
# =============================================================================

PARAM_NAMES = [
    'btd_weight', 'orphan_weight', 'priority_review_weight', 'fast_track_weight',
    'accelerated_approval_weight', 'adcom_high_boost', 'adcom_mid_penalty',
    'adcom_low_penalty', 'prior_crl_penalty', 'class1_resubmission_boost',
    'class2_resubmission_penalty', 'experienced_sponsor_boost',
    'inexperienced_sponsor_penalty', 'manufacturing_risk_penalty',
    'form_483_penalty', 'rna_therapy_penalty', 'gene_therapy_penalty',
    'ta_adjustment_weight', 'era_weight',
    'tier1_threshold', 'tier2_threshold'
]

# Bounds with v9.4 lessons applied
PARAM_BOUNDS = np.array([
    [0.00, 0.20],   # btd_weight - EXPANDED (v9.4 hit 0.116)
    [0.00, 0.10],   # orphan_weight
    [0.00, 0.15],   # priority_review_weight
    [0.00, 0.08],   # fast_track_weight
    [0.00, 0.12],   # accelerated_approval_weight - EXPANDED
    [0.00, 0.25],   # adcom_high_boost - EXPANDED (v9.4 hit 0.20)
    [-0.20, 0.00],  # adcom_mid_penalty - EXPANDED
    [-0.35, -0.08], # adcom_low_penalty - FORCE MINIMUM PENALTY
    [-0.25, 0.00],  # prior_crl_penalty - EXPANDED
    [0.05, 0.30],   # class1_resubmission_boost - EXPANDED
    [-0.20, 0.00],  # class2_resubmission_penalty - FIXED (no positive)
    [0.00, 0.15],   # experienced_sponsor_boost - EXPANDED
    [-0.18, 0.00],  # inexperienced_sponsor_penalty - EXPANDED
    [-0.35, 0.00],  # manufacturing_risk_penalty - EXPANDED (v9.4 hit -0.25)
    [-0.18, 0.00],  # form_483_penalty - EXPANDED
    [-0.40, -0.10], # rna_therapy_penalty - NEW! (55.6% CRL rate)
    [-0.15, 0.00],  # gene_therapy_penalty
    [0.5, 1.2],     # ta_adjustment_weight - TIGHTENED (v9.4 chose 0.86)
    [0.00, 0.12],   # era_weight - NEW (post-2020 boost)
    [0.80, 0.92],   # tier1_threshold - TIGHTENED LOWER
    [0.55, 0.72],   # tier2_threshold - TIGHTENED
], dtype=np.float32)

N_PARAMS = len(PARAM_NAMES)


# =============================================================================
# v9.1 CHAMPION - WARM START SEED
# =============================================================================

V91_CHAMPION = np.array([
    0.0573,   # btd_weight
    0.0377,   # orphan_weight  
    0.0845,   # priority_review_weight
    0.0291,   # fast_track_weight
    0.0483,   # accelerated_approval_weight
    0.0812,   # adcom_high_boost
    -0.0623,  # adcom_mid_penalty
    -0.1894,  # adcom_low_penalty
    -0.0845,  # prior_crl_penalty
    0.1567,   # class1_resubmission_boost
    -0.0512,  # class2_resubmission_penalty
    0.0534,   # experienced_sponsor_boost
    -0.0678,  # inexperienced_sponsor_penalty
    -0.1234,  # manufacturing_risk_penalty
    -0.0712,  # form_483_penalty
    -0.25,    # rna_therapy_penalty (NEW - estimated from 55.6% CRL)
    -0.06,    # gene_therapy_penalty
    0.829,    # ta_adjustment_weight
    0.05,     # era_weight (NEW)
    0.858,    # tier1_threshold
    0.68,     # tier2_threshold (adjusted for new param order)
], dtype=np.float32)

V91_BRIER = 0.08864


# =============================================================================
# VRAM DETECTION
# =============================================================================

def detect_vram_and_batch_size(n_events: int) -> tuple:
    """Detect VRAM and calculate safe batch size."""
    if not GPU_AVAILABLE or cp is None:
        return (0, 0, 10_000)
    
    try:
        free_bytes, total_bytes = cp.cuda.Device().mem_info
        total_gb = total_bytes / 1e9
        free_gb = free_bytes / 1e9
        
        print(f"\n🖥️  GPU VRAM: {total_gb:.1f}GB total, {free_gb:.1f}GB free", flush=True)
        
        # Conservative: 15 arrays per config
        bytes_per_config = n_events * 4 * 15
        usable_bytes = free_gb * 1e9 * 0.25  # 25% of free
        safe_batch = int(usable_bytes / bytes_per_config)
        safe_batch = max(MIN_BATCH_SIZE, min(50_000, safe_batch))
        
        print(f"   Safe batch size: {safe_batch:,}", flush=True)
        return (total_gb, free_gb, safe_batch)
        
    except Exception as e:
        print(f"⚠️  VRAM detection failed: {e}", flush=True)
        return (0, 0, 10_000)


def clear_gpu_memory():
    """Clear GPU memory cache."""
    if GPU_AVAILABLE and cp is not None:
        try:
            cp.get_default_memory_pool().free_all_blocks()
            cp.get_default_pinned_memory_pool().free_all_blocks()
        except:
            pass


# =============================================================================
# DATA LOADING - v9.5 WITH ERA AND MODALITY SPLITS
# =============================================================================

def load_dataset(path: str) -> pd.DataFrame:
    """Load and prepare dataset."""
    print(f"📂 Loading dataset: {path}")
    df = pd.read_csv(path)
    print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
    
    # Outcome encoding
    df['outcome_binary'] = df['outcome'].str.upper().str.contains('APPROV').astype(np.float32)
    
    # Boolean features
    bool_cols = ['btd', 'orphan', 'priority_review', 'fast_track', 'had_adcom',
                 'prior_crl', 'form_483_issues', 'manufacturing_risk', 'experienced_sponsor']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool).astype(np.float32)
    
    # Numeric features
    df['adcom_vote_pct'] = df['adcom_vote_pct'].fillna(0).astype(np.float32)
    df['resubmission_class'] = df['resubmission_class'].fillna(0).astype(np.float32)
    df['sponsor_prior_approvals'] = df['sponsor_prior_approvals'].fillna(0).astype(np.float32)
    
    # Accelerated approval
    if 'accelerated_approval' in df.columns:
        df['has_accelerated'] = (~df['accelerated_approval'].isna() & 
                                  (df['accelerated_approval'] != 'No')).astype(np.float32)
    else:
        df['has_accelerated'] = 0.0
    
    # TA encoding
    ta_adjustments = {
        'Pain Management': -0.286, 'Hematology': -0.224, 'Nephrology': -0.177,
        'Ophthalmology': -0.131, 'CNS/Neurology': -0.098, 'Cardiovascular': -0.081,
        'Metabolic/Endocrine': -0.067, 'Rare Disease': -0.043, 'Other': -0.019,
        'Immunology': 0.016, 'Dermatology': 0.028, 'Oncology': 0.061,
        'GI/Hepatology': 0.067, 'Respiratory': 0.090, 'Infectious Disease': 0.103,
        'Vaccines': 0.133, "Women's Health": 0.133
    }
    df['ta_adjustment'] = df['therapeutic_area'].map(ta_adjustments).fillna(0).astype(np.float32)
    
    # v9.5: Separate modality columns
    df['is_rna_therapy'] = (df['modality'] == 'RNA Therapy').astype(np.float32)
    df['is_gene_therapy'] = df['modality'].isin(['Cell/Gene Therapy', 'Gene Therapy']).astype(np.float32)
    
    # v9.5: Era encoding (post-2020 has much lower CRL rate)
    df['is_post_2020'] = (df['year'] >= 2020).astype(np.float32)
    
    # Stats
    n_crl = (df['outcome_binary'] == 0).sum()
    n_approval = (df['outcome_binary'] == 1).sum()
    print(f"   Outcomes: {n_approval} approvals, {n_crl} CRLs ({n_crl/len(df)*100:.1f}% CRL rate)")
    print(f"   RNA Therapy: {df['is_rna_therapy'].sum():.0f} events")
    print(f"   Post-2020: {df['is_post_2020'].sum():.0f} events ({df['is_post_2020'].mean()*100:.1f}%)")
    
    return df


def prepare_gpu_data(df: pd.DataFrame) -> dict:
    """Transfer data to GPU."""
    xp = cp if GPU_AVAILABLE else np
    
    data = {
        'n_events': len(df),
        'outcomes': xp.asarray(df['outcome_binary'].values, dtype=xp.float32),
        'btd': xp.asarray(df['btd'].values, dtype=xp.float32),
        'orphan': xp.asarray(df['orphan'].values, dtype=xp.float32),
        'priority_review': xp.asarray(df['priority_review'].values, dtype=xp.float32),
        'fast_track': xp.asarray(df['fast_track'].values, dtype=xp.float32),
        'has_accelerated': xp.asarray(df['has_accelerated'].values, dtype=xp.float32),
        'had_adcom': xp.asarray(df['had_adcom'].values, dtype=xp.float32),
        'adcom_vote_pct': xp.asarray(df['adcom_vote_pct'].values, dtype=xp.float32),
        'prior_crl': xp.asarray(df['prior_crl'].values, dtype=xp.float32),
        'resubmission_class': xp.asarray(df['resubmission_class'].values, dtype=xp.float32),
        'experienced_sponsor': xp.asarray(df['experienced_sponsor'].values, dtype=xp.float32),
        'sponsor_prior_approvals': xp.asarray(df['sponsor_prior_approvals'].values, dtype=xp.float32),
        'form_483_issues': xp.asarray(df['form_483_issues'].values, dtype=xp.float32),
        'manufacturing_risk': xp.asarray(df['manufacturing_risk'].values, dtype=xp.float32),
        'ta_adjustment': xp.asarray(df['ta_adjustment'].values, dtype=xp.float32),
        # v9.5 new columns
        'is_rna_therapy': xp.asarray(df['is_rna_therapy'].values, dtype=xp.float32),
        'is_gene_therapy': xp.asarray(df['is_gene_therapy'].values, dtype=xp.float32),
        'is_post_2020': xp.asarray(df['is_post_2020'].values, dtype=xp.float32),
    }
    
    return data


# =============================================================================
# ANNEALING SEARCH
# =============================================================================

class AnnealingSearch:
    """Simulated annealing with elite population and warm start."""
    
    def __init__(self, bounds: np.ndarray, elite_size: int = 25):
        self.bounds = bounds
        self.n_params = len(bounds)
        self.elite_size = elite_size
        self.elites = []
        self.temperature = INITIAL_TEMPERATURE
        self.configs_since_improvement = 0
        self.total_improvements = 0
        
    def add_elite(self, score: float, params: np.ndarray):
        """Add config to elite population."""
        self.elites.append((score, params.copy()))
        self.elites.sort(key=lambda x: x[0])
        if len(self.elites) > self.elite_size:
            self.elites = self.elites[:self.elite_size]
        self.configs_since_improvement = 0
        self.total_improvements += 1
        
    def warm_start(self, score: float, params: np.ndarray):
        """Initialize with known-good config."""
        # Clip to current bounds
        clipped = np.clip(params, self.bounds[:, 0], self.bounds[:, 1])
        self.elites.append((score, clipped))
        print(f"   🌡️ Warm start with score {score:.5f}")
        
    def generate_batch(self, batch_size: int, xp=np) -> 'array':
        """Generate parameter batch using annealing."""
        params = xp.zeros((batch_size, self.n_params), dtype=xp.float32)
        bounds_gpu = xp.asarray(self.bounds, dtype=xp.float32)
        ranges = bounds_gpu[:, 1] - bounds_gpu[:, 0]
        
        if not self.elites or xp.random.random() > LOCAL_SEARCH_PROB:
            # Exploration
            if self.elites:
                center = xp.asarray(self.elites[0][1], dtype=xp.float32)
            else:
                center = (bounds_gpu[:, 0] + bounds_gpu[:, 1]) / 2
            
            scale = ranges * self.temperature
            noise = xp.random.uniform(-0.5, 0.5, size=(batch_size, self.n_params)).astype(xp.float32)
            params = center + noise * scale
            
        else:
            # Exploitation around elites
            n_from_each = batch_size // len(self.elites) + 1
            idx = 0
            
            for score, elite_params in self.elites:
                if idx >= batch_size:
                    break
                    
                n_this = min(n_from_each, batch_size - idx)
                elite_gpu = xp.asarray(elite_params, dtype=xp.float32)
                
                local_scale = ranges * (0.05 + 0.15 * self.temperature)
                noise = xp.random.uniform(-0.5, 0.5, size=(n_this, self.n_params)).astype(xp.float32)
                params[idx:idx+n_this] = elite_gpu + noise * local_scale
                idx += n_this
        
        params = xp.clip(params, bounds_gpu[:, 0], bounds_gpu[:, 1])
        return params
    
    def cool_down(self):
        self.temperature = max(FINAL_TEMPERATURE, self.temperature * COOLING_RATE)
        
    def maybe_reheat(self, configs_tested: int):
        self.configs_since_improvement += configs_tested
        if self.configs_since_improvement > REHEAT_THRESHOLD:
            old_temp = self.temperature
            self.temperature = min(1.0, self.temperature * 5)
            print(f"\n   🔥 REHEAT: {old_temp:.4f} → {self.temperature:.4f}")
            self.configs_since_improvement = 0


# =============================================================================
# GPU SCORING - v9.5 WITH NEW PARAMETERS
# =============================================================================

def score_batch_gpu(params: 'array', data: dict, xp=None) -> tuple:
    """Score batch with v9.5 parameters."""
    if xp is None:
        xp = cp if GPU_AVAILABLE else np
    
    batch_size = params.shape[0]
    n_events = data['n_events']
    
    # Extract parameters (v9.5 order)
    btd_w = params[:, 0]
    orphan_w = params[:, 1]
    pr_w = params[:, 2]
    ft_w = params[:, 3]
    aa_w = params[:, 4]
    adcom_high = params[:, 5]
    adcom_mid = params[:, 6]
    adcom_low = params[:, 7]
    prior_crl_p = params[:, 8]
    class1_boost = params[:, 9]
    class2_pen = params[:, 10]
    exp_sponsor = params[:, 11]
    inexp_sponsor = params[:, 12]
    mfg_risk = params[:, 13]
    form483 = params[:, 14]
    rna_pen = params[:, 15]       # NEW
    gene_pen = params[:, 16]      # NEW  
    ta_weight = params[:, 17]
    era_weight = params[:, 18]    # NEW
    tier1_thresh = params[:, 19]
    tier2_thresh = params[:, 20]
    
    # Build probability matrix
    probs = xp.full((batch_size, n_events), 0.828, dtype=xp.float32)  # Updated base rate
    
    # Designations
    probs += xp.outer(btd_w, data['btd'])
    probs += xp.outer(orphan_w, data['orphan'])
    probs += xp.outer(pr_w, data['priority_review'])
    probs += xp.outer(ft_w, data['fast_track'])
    probs += xp.outer(aa_w, data['has_accelerated'])
    
    # AdCom
    had_adcom = data['had_adcom']
    adcom_pct = data['adcom_vote_pct']
    high_vote = ((adcom_pct >= 0.65) * had_adcom)
    mid_vote = (((adcom_pct >= 0.50) & (adcom_pct < 0.65)) * had_adcom)
    low_vote = ((adcom_pct < 0.50) * had_adcom)
    
    probs += xp.outer(adcom_high, high_vote)
    probs += xp.outer(adcom_mid, mid_vote)
    probs += xp.outer(adcom_low, low_vote)
    
    # Prior CRL / Resubmission
    probs += xp.outer(prior_crl_p, data['prior_crl'])
    class1_mask = (data['resubmission_class'] == 1).astype(xp.float32)
    class2_mask = (data['resubmission_class'] == 2).astype(xp.float32)
    probs += xp.outer(class1_boost, class1_mask)
    probs += xp.outer(class2_pen, class2_mask)
    
    # Sponsor
    probs += xp.outer(exp_sponsor, data['experienced_sponsor'])
    inexperienced = (data['sponsor_prior_approvals'] == 0).astype(xp.float32)
    probs += xp.outer(inexp_sponsor, inexperienced)
    
    # Manufacturing
    probs += xp.outer(mfg_risk, data['manufacturing_risk'])
    probs += xp.outer(form483, data['form_483_issues'])
    
    # v9.5: Modality-specific penalties
    probs += xp.outer(rna_pen, data['is_rna_therapy'])
    probs += xp.outer(gene_pen, data['is_gene_therapy'])
    
    # TA adjustment
    probs += xp.outer(ta_weight, data['ta_adjustment'])
    
    # v9.5: Era adjustment
    probs += xp.outer(era_weight, data['is_post_2020'])
    
    # Clip
    probs = xp.clip(probs, 0.01, 0.99)
    
    # Brier scores
    outcomes = data['outcomes']
    brier_per_event = (probs - outcomes) ** 2
    brier_scores = xp.mean(brier_per_event, axis=1)
    del brier_per_event
    
    # Tier masks
    t1_t = tier1_thresh.reshape(-1, 1)
    t2_t = tier2_thresh.reshape(-1, 1)
    
    tier1_mask = (probs >= t1_t)
    tier4_mask = (probs < t2_t)
    del probs
    
    # Counts and rates
    tier1_counts = xp.sum(tier1_mask, axis=1)
    tier4_counts = xp.sum(tier4_mask, axis=1)
    
    tier1_approvals = xp.sum(tier1_mask * outcomes, axis=1)
    tier1_approval_rates = xp.where(tier1_counts > 0, 
                                     tier1_approvals / tier1_counts, 
                                     xp.ones(batch_size, dtype=xp.float32))
    
    tier4_crls = xp.sum(tier4_mask * (1 - outcomes), axis=1)
    tier4_crl_rates = xp.where(tier4_counts > 0,
                                tier4_crls / tier4_counts,
                                xp.zeros(batch_size, dtype=xp.float32))
    
    del tier1_mask, tier4_mask
    
    # v9.5: Tightened feasibility
    f1 = (tier1_thresh >= TIER1_MIN)
    f2 = (tier2_thresh <= TIER2_MAX)
    f3 = (tier1_thresh > tier2_thresh + 0.05)  # Require 5% gap
    f4 = (tier1_approval_rates >= TIER1_APPROVAL_MIN)
    f5 = (tier4_crl_rates >= TIER4_CRL_MIN)    # Now 0.70
    f6 = (tier1_counts >= 10)
    f7 = (tier4_counts >= TIER4_COUNT_MIN)     # Now 15
    
    feasible = f1 & f2 & f3 & f4 & f5 & f6 & f7
    
    if GPU_AVAILABLE:
        xp.get_default_memory_pool().free_all_blocks()
    
    return brier_scores, feasible, tier1_approval_rates, tier4_crl_rates, tier4_counts


# =============================================================================
# COMPOSITE SCORING - v9.5
# =============================================================================

def compute_composite_score(brier: float, tier4_crl: float) -> float:
    """
    Multi-objective score: Brier + Tier4 CRL penalty.
    Lower is better.
    """
    score = brier * COMPOSITE_WEIGHTS['brier']
    
    # Tier4 CRL bonus (higher CRL = lower score)
    tier4_penalty = (COMPOSITE_WEIGHTS['tier4_target'] - tier4_crl) * COMPOSITE_WEIGHTS['tier4_crl']
    
    # Heavy penalty below 70%
    if tier4_crl < 0.70:
        tier4_penalty += (0.70 - tier4_crl) * 0.5
    
    return score + tier4_penalty


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

def run_optimization():
    """Run v9.5 optimization."""
    
    print("=" * 60, flush=True)
    print("ODIN v9.5 GPU OPTIMIZER - STARTING", flush=True)
    print("=" * 60, flush=True)
    
    init_gpu()
    OUTPUT_DIR.mkdir(exist_ok=True)
    xp = cp if GPU_AVAILABLE else np
    
    # Load data
    df = load_dataset(DATASET_PATH)
    total_vram, free_vram, safe_batch = detect_vram_and_batch_size(len(df))
    
    clear_gpu_memory()
    data = prepare_gpu_data(df)
    print(f"✅ Data on GPU ({data['n_events']} events)", flush=True)
    
    # Initialize searcher with warm start
    searcher = AnnealingSearch(PARAM_BOUNDS, elite_size=ELITE_SIZE)
    searcher.warm_start(V91_BRIER, V91_CHAMPION)
    
    # Tracking
    best_score = V91_BRIER
    best_composite = float('inf')
    best_params = V91_CHAMPION.copy()
    best_metrics = {'brier_score': V91_BRIER, 'tier4_crl_rate': 0.857}
    
    total_tested = 0
    batch_size = safe_batch
    
    start_time = time.time()
    last_progress = time.time()
    last_checkpoint = time.time()
    
    print(f"\n{'='*70}")
    print(f"ODIN v9.5 OPTIMIZATION")
    print(f"{'='*70}")
    print(f"Target: {TOTAL_ITERATIONS:,} configurations")
    print(f"Dataset: {len(df):,} events ({(1-df['outcome_binary'].mean())*100:.1f}% CRL)")
    print(f"Constraints: Tier4 CRL ≥ {TIER4_CRL_MIN*100:.0f}%, Tier4 count ≥ {TIER4_COUNT_MIN}")
    print(f"{'='*70}\n")
    
    while total_tested < TOTAL_ITERATIONS:
        # Dynamic batch sizing
        if GPU_AVAILABLE:
            try:
                free_mem = cp.cuda.Device().mem_info[0] / 1e9
                if free_mem < 1.0:
                    clear_gpu_memory()
                    batch_size = max(MIN_BATCH_SIZE, int(batch_size * 0.5))
                elif free_mem > 4.0 and batch_size < MAX_BATCH_SIZE:
                    batch_size = min(MAX_BATCH_SIZE, int(batch_size * 1.1))
            except:
                pass
        
        try:
            params = searcher.generate_batch(batch_size, xp)
            brier_scores, feasible, t1_rates, t4_rates, t4_counts = score_batch_gpu(params, data, xp)
        except Exception as e:
            if 'memory' in str(e).lower():
                clear_gpu_memory()
                batch_size = max(MIN_BATCH_SIZE, int(batch_size * 0.5))
                continue
            raise e
        
        # Transfer to CPU
        if GPU_AVAILABLE:
            feasible_mask = feasible.get()
            brier_np = brier_scores.get()
            params_np = params.get()
            t1_np = t1_rates.get()
            t4_np = t4_rates.get()
            t4_counts_np = t4_counts.get()
        else:
            feasible_mask = feasible
            brier_np = brier_scores
            params_np = params
            t1_np = t1_rates
            t4_np = t4_rates
            t4_counts_np = t4_counts
        
        feasible_indices = np.where(feasible_mask)[0]
        total_tested += batch_size
        
        if len(feasible_indices) > 0:
            # v9.5: Composite scoring
            feasible_briers = brier_np[feasible_indices]
            feasible_t4_crl = t4_np[feasible_indices]
            
            composite_scores = np.array([
                compute_composite_score(b, t4) 
                for b, t4 in zip(feasible_briers, feasible_t4_crl)
            ])
            
            best_idx_in_feasible = np.argmin(composite_scores)
            best_idx = feasible_indices[best_idx_in_feasible]
            batch_best_composite = composite_scores[best_idx_in_feasible]
            batch_best_brier = feasible_briers[best_idx_in_feasible]
            
            if batch_best_composite < best_composite:
                improvement_pct = (best_composite - batch_best_composite) / best_composite * 100 if best_composite < float('inf') else 100
                
                best_composite = batch_best_composite
                best_score = batch_best_brier
                best_params = params_np[best_idx].copy()
                best_metrics = {
                    'brier_score': float(batch_best_brier),
                    'composite_score': float(batch_best_composite),
                    'tier1_approval_rate': float(t1_np[best_idx]),
                    'tier4_crl_rate': float(t4_np[best_idx]),
                    'tier4_count': int(t4_counts_np[best_idx]),
                    'temperature': searcher.temperature
                }
                
                searcher.add_elite(batch_best_composite, best_params)
                
                print(f"\n   🎯 IMPROVEMENT #{searcher.total_improvements}")
                print(f"      Brier: {best_score:.5f} | Composite: {best_composite:.5f}")
                print(f"      Tier1: {best_metrics['tier1_approval_rate']*100:.1f}% | Tier4 CRL: {best_metrics['tier4_crl_rate']*100:.1f}% ({best_metrics['tier4_count']} events)")
        
        searcher.cool_down()
        searcher.maybe_reheat(batch_size)
        
        # Progress
        if time.time() - last_progress > 10:
            elapsed = time.time() - start_time
            rate = total_tested / elapsed
            eta = (TOTAL_ITERATIONS - total_tested) / rate / 60
            feasibility_pct = len(feasible_indices) / batch_size * 100
            
            print(f"Progress | {total_tested:>12,} | Feas: {feasibility_pct:>5.1f}% | "
                  f"Brier: {best_score:.5f} | T4 CRL: {best_metrics.get('tier4_crl_rate', 0)*100:.1f}% | "
                  f"T: {searcher.temperature:.4f} | {rate/1000:.0f}K/s | ETA: {eta:.1f}m")
            last_progress = time.time()
        
        # Checkpoint
        if time.time() - last_checkpoint > 300:
            save_checkpoint(searcher, best_score, best_params, best_metrics, total_tested)
            last_checkpoint = time.time()
    
    # Final
    print(f"\n{'='*70}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total tested: {total_tested:,}")
    print(f"Best Brier: {best_score:.5f}")
    print(f"Best Tier4 CRL: {best_metrics.get('tier4_crl_rate', 0)*100:.1f}%")
    
    if best_params is not None:
        print(f"\nBest parameters:")
        for i, name in enumerate(PARAM_NAMES):
            print(f"  {name}: {best_params[i]:.4f}")
        
        save_champion_config(best_params, best_metrics, total_tested, searcher.total_improvements)
    
    return best_score, best_params, best_metrics


def save_checkpoint(searcher, best_score, best_params, best_metrics, total_tested):
    """Save checkpoint."""
    checkpoint = {
        'version': '9.5',
        'timestamp': datetime.now().isoformat(),
        'total_tested': total_tested,
        'best_score': float(best_score),
        'best_params': best_params.tolist() if best_params is not None else None,
        'best_metrics': best_metrics,
        'temperature': searcher.temperature,
        'total_improvements': searcher.total_improvements,
        'elites': [(float(s), p.tolist()) for s, p in searcher.elites]
    }
    
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"   💾 Checkpoint saved")


def save_champion_config(params, metrics, total_tested, total_improvements):
    """Save champion config."""
    config = {
        'version': '9.5',
        'optimization': {
            'method': 'simulated_annealing_composite',
            'configs_tested': total_tested,
            'improvements_found': total_improvements,
            'timestamp': datetime.now().isoformat()
        },
        'performance': metrics,
        'champion_params': {name: float(params[i]) for i, name in enumerate(PARAM_NAMES)},
        'constraints': {
            'tier4_crl_min': TIER4_CRL_MIN,
            'tier4_count_min': TIER4_COUNT_MIN,
            'tier1_approval_min': TIER1_APPROVAL_MIN
        }
    }
    
    output_path = OUTPUT_DIR / f"ODIN_v95_CHAMPION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Champion saved: {output_path}")


if __name__ == "__main__":
    print("Starting ODIN v9.5 Optimizer...", flush=True)
    run_optimization()
