#!/usr/bin/env python3
"""
ODIN v9.4 GPU Optimizer with Simulated Annealing
=================================================
Like code breaking: Start broad, progressively narrow around best solutions.

Key improvements over random search:
1. TEMPERATURE SCHEDULE: Start hot (full range), cool down (narrow focus)
2. LOCAL REFINEMENT: Exploit regions around best configs found
3. ADAPTIVE RESTART: If stuck, restart with random perturbation of best
4. ELITE POPULATION: Track top N configs and search around them

Usage:
    python odin_v94_gpu_annealing_optimizer.py
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

# GPU setup - LAZY initialization to avoid hanging on import
GPU_AVAILABLE = None
cp = None

# Set to True to skip GPU entirely and use CPU
FORCE_CPU = False  # <-- Set to True if GPU keeps hanging

def init_gpu():
    """Initialize GPU. Call this once at start of optimization."""
    global GPU_AVAILABLE, cp
    
    if GPU_AVAILABLE is not None:
        return GPU_AVAILABLE
    
    # Check for forced CPU mode
    if FORCE_CPU:
        print("⚠️ FORCE_CPU=True - Using NumPy (CPU only)", flush=True)
        cp = np
        GPU_AVAILABLE = False
        return False
    
    print("Checking GPU availability...", flush=True)
    print("   (If this hangs, set FORCE_CPU=True at line 37)", flush=True)
    
    try:
        # Use subprocess with timeout to test if cupy can import
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c", "import cupy; print('ok')"],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        if result.returncode != 0 or 'ok' not in result.stdout:
            raise Exception(f"CuPy test failed: {result.stderr}")
        
        # If subprocess worked, now import for real
        print("   CuPy subprocess test passed, importing...", flush=True)
        import cupy as _cp
        
        # Quick GPU test
        print("   Testing GPU allocation...", flush=True)
        test = _cp.zeros(100)
        del test
        _cp.get_default_memory_pool().free_all_blocks()
        
        cp = _cp
        GPU_AVAILABLE = True
        print(f"✅ CuPy available - GPU acceleration enabled", flush=True)
        
    except subprocess.TimeoutExpired:
        print("⚠️ CuPy import timed out (30s) - falling back to NumPy", flush=True)
        cp = np
        GPU_AVAILABLE = False
        
    except Exception as e:
        print(f"⚠️ GPU not available ({e}) - falling back to NumPy", flush=True)
        cp = np
        GPU_AVAILABLE = False
    
    return GPU_AVAILABLE

# =============================================================================
# CONFIGURATION
# =============================================================================

# Dataset path - Auto-detect or specify manually
DATASET_PATH = None  # Will auto-detect

def find_dataset():
    """Auto-find ODIN dataset file."""
    
    # Common locations
    search_paths = [
        r"C:\Users\dcmoo\Documents\*.csv",
        r"C:\Users\dcmoo\Documents\Python\*.csv",
        r"C:\Users\dcmoo\Downloads\*.csv",
        r".\*.csv",
    ]
    
    # Patterns to match (in priority order)
    patterns = [
        "ODIN_v4_2_AUDITED",
        "ODIN_v4_FIXED", 
        "ODIN_ENRICHED_PDUFA",
        "ODIN_v4",
        "pdufa",
    ]
    
    all_csvs = []
    for search in search_paths:
        all_csvs.extend(glob.glob(search))
    
    # Find best match
    for pattern in patterns:
        for csv_path in all_csvs:
            if pattern.lower() in csv_path.lower():
                return csv_path
    
    # If nothing found, list what's available
    if all_csvs:
        print("Available CSV files:")
        for f in all_csvs[:10]:
            print(f"  - {f}")
    
    return None

# Output
OUTPUT_DIR = Path("odin_optimization_output")
CHECKPOINT_FILE = OUTPUT_DIR / "annealing_checkpoint.json"

# Optimization settings
TOTAL_ITERATIONS = 1_000_000_000  # 1 billion
INITIAL_BATCH_SIZE = None  # Auto-detect based on VRAM
MIN_BATCH_SIZE = 10_000
MAX_BATCH_SIZE = 100_000  # Much lower for 12GB VRAM

# Memory safety
VRAM_SAFETY_MARGIN = 0.6  # Use only 60% of free VRAM
BYTES_PER_CONFIG = 500   # Estimated bytes per config (conservative)

# Annealing schedule
INITIAL_TEMPERATURE = 1.0      # Full parameter range
FINAL_TEMPERATURE = 0.01       # 1% of range (very focused)
COOLING_RATE = 0.9995          # Slow cooling
REHEAT_THRESHOLD = 50_000_000  # Reheat if no improvement for 50M configs

# Elite population
ELITE_SIZE = 20                # Track top 20 configs
LOCAL_SEARCH_PROB = 0.7        # 70% of time, search near elites

# =============================================================================
# PARAMETER BOUNDS (same as before)
# =============================================================================

PARAM_NAMES = [
    'btd_weight', 'orphan_weight', 'priority_review_weight', 'fast_track_weight',
    'accelerated_approval_weight', 'adcom_high_boost', 'adcom_mid_penalty',
    'adcom_low_penalty', 'prior_crl_penalty', 'class1_resubmission_boost',
    'class2_resubmission_penalty', 'experienced_sponsor_boost',
    'inexperienced_sponsor_penalty', 'manufacturing_risk_penalty',
    'form_483_penalty', 'modality_penalty', 'ta_adjustment_weight',
    'tier1_threshold', 'tier2_threshold'
]

# Bounds: [min, max] - WIDENED for better exploration
PARAM_BOUNDS = np.array([
    [0.00, 0.15],   # btd_weight
    [0.00, 0.12],   # orphan_weight
    [0.00, 0.15],   # priority_review_weight
    [0.00, 0.10],   # fast_track_weight
    [0.00, 0.10],   # accelerated_approval_weight
    [0.00, 0.20],   # adcom_high_boost
    [-0.15, 0.00],  # adcom_mid_penalty
    [-0.30, -0.05], # adcom_low_penalty
    [-0.20, 0.00],  # prior_crl_penalty
    [0.05, 0.25],   # class1_resubmission_boost
    [-0.15, 0.05],  # class2_resubmission_penalty (allow small positive)
    [0.00, 0.12],   # experienced_sponsor_boost
    [-0.15, 0.00],  # inexperienced_sponsor_penalty
    [-0.25, 0.00],  # manufacturing_risk_penalty
    [-0.15, 0.00],  # form_483_penalty
    [-0.12, 0.00],  # modality_penalty
    [0.5, 1.5],     # ta_adjustment_weight
    [0.78, 0.92],   # tier1_threshold
    [0.60, 0.80],   # tier2_threshold
], dtype=np.float32)

N_PARAMS = len(PARAM_NAMES)

# Feasibility constraints
TIER1_MIN = 0.78
TIER2_MAX = 0.80
TIER1_APPROVAL_MIN = 0.90
TIER4_CRL_MIN = 0.50

# =============================================================================
# VRAM DETECTION AND BATCH SIZE CALCULATION
# =============================================================================

def detect_vram_and_batch_size(n_events: int) -> tuple:
    """
    Detect available VRAM and calculate safe initial batch size.
    
    Memory per batch: ~(batch_size * n_events * 4 bytes * 15 arrays)
    For 1349 events: ~81KB per config in batch
    
    Returns:
        (total_vram_gb, free_vram_gb, safe_batch_size)
    """
    if not GPU_AVAILABLE or cp is None:
        return (0, 0, 10_000)  # CPU fallback
    
    try:
        # Get GPU memory info
        free_bytes, total_bytes = cp.cuda.Device().mem_info
        total_gb = total_bytes / 1e9
        free_gb = free_bytes / 1e9
        
        print(f"\n🖥️  GPU VRAM Detection:", flush=True)
        print(f"   Total VRAM: {total_gb:.1f} GB", flush=True)
        print(f"   Free VRAM:  {free_gb:.1f} GB", flush=True)
        print(f"   Used VRAM:  {(total_gb - free_gb):.1f} GB", flush=True)
        
        # VERY CONSERVATIVE memory calculation
        # Each (batch, events) array uses: batch * events * 4 bytes
        # We need ~15 such arrays during scoring
        bytes_per_config = n_events * 4 * 15
        
        # Use only 25% of free memory
        usable_bytes = free_gb * 1e9 * 0.25
        safe_batch = int(usable_bytes / bytes_per_config)
        
        # Hard cap at 50,000 for 12GB cards
        safe_batch = max(MIN_BATCH_SIZE, min(50_000, safe_batch))
        
        print(f"   Events: {n_events}", flush=True)
        print(f"   Bytes/config estimate: {bytes_per_config:,} ({bytes_per_config/1024:.1f} KB)", flush=True)
        print(f"   Safe batch size: {safe_batch:,}", flush=True)
        
        return (total_gb, free_gb, safe_batch)
        
    except Exception as e:
        print(f"⚠️  VRAM detection failed: {e}", flush=True)
        return (0, 0, 10_000)  # Very conservative fallback


def clear_gpu_memory():
    """Clear GPU memory cache."""
    if GPU_AVAILABLE and cp is not None:
        try:
            cp.get_default_memory_pool().free_all_blocks()
            cp.get_default_pinned_memory_pool().free_all_blocks()
        except:
            pass


# =============================================================================
# DATA LOADING
# =============================================================================

def load_dataset(path: str) -> dict:
    """Load and prepare dataset for GPU."""
    print(f"📂 Loading dataset: {path}")
    df = pd.read_csv(path)
    print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
    
    # Encode outcome
    df['outcome_binary'] = (df['outcome'].str.upper().str.contains('APPROV')).astype(np.float32)
    
    # Fill missing values
    bool_cols = ['btd', 'orphan', 'priority_review', 'fast_track', 'had_adcom',
                 'prior_crl', 'form_483_issues', 'manufacturing_risk', 'experienced_sponsor']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(np.float32)
    
    df['adcom_vote_pct'] = df['adcom_vote_pct'].fillna(0).astype(np.float32)
    df['resubmission_class'] = df['resubmission_class'].fillna(0).astype(np.float32)
    df['sponsor_prior_approvals'] = df['sponsor_prior_approvals'].fillna(0).astype(np.float32)
    
    # Accelerated approval encoding
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
    
    # Modality encoding
    modality_high_risk = ['Cell/Gene Therapy', 'Gene Therapy', 'RNA Therapy']
    df['is_high_risk_modality'] = df['modality'].isin(modality_high_risk).astype(np.float32)
    
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
        'is_high_risk_modality': xp.asarray(df['is_high_risk_modality'].values, dtype=xp.float32),
    }
    
    return data


# =============================================================================
# ANNEALING PARAMETER GENERATION
# =============================================================================

class AnnealingSearch:
    """Simulated annealing search with elite population."""
    
    def __init__(self, bounds: np.ndarray, elite_size: int = 20):
        self.bounds = bounds
        self.n_params = len(bounds)
        self.elite_size = elite_size
        
        # Elite population: (score, params) tuples, sorted by score (lower is better)
        self.elites = []
        
        # Temperature
        self.temperature = INITIAL_TEMPERATURE
        
        # Stats
        self.configs_since_improvement = 0
        self.total_improvements = 0
        
    def add_elite(self, score: float, params: np.ndarray):
        """Add a config to elite population if good enough."""
        self.elites.append((score, params.copy()))
        self.elites.sort(key=lambda x: x[0])
        if len(self.elites) > self.elite_size:
            self.elites = self.elites[:self.elite_size]
        self.configs_since_improvement = 0
        self.total_improvements += 1
        
    def get_best(self):
        """Get best elite."""
        if self.elites:
            return self.elites[0]
        return None
        
    def generate_batch(self, batch_size: int, xp=np) -> 'array':
        """Generate batch of parameter configs using annealing strategy."""
        
        params = xp.zeros((batch_size, self.n_params), dtype=xp.float32)
        bounds_gpu = xp.asarray(self.bounds, dtype=xp.float32)
        ranges = bounds_gpu[:, 1] - bounds_gpu[:, 0]
        
        if not self.elites or xp.random.random() > LOCAL_SEARCH_PROB:
            # EXPLORATION: Random within temperature-scaled range
            # At T=1.0, full range. At T=0.01, 1% of range centered on best
            
            if self.elites:
                # Center on best elite
                center = xp.asarray(self.elites[0][1], dtype=xp.float32)
            else:
                # Center on middle of bounds
                center = (bounds_gpu[:, 0] + bounds_gpu[:, 1]) / 2
            
            # Temperature-scaled random perturbation
            scale = ranges * self.temperature
            noise = xp.random.uniform(-0.5, 0.5, size=(batch_size, self.n_params)).astype(xp.float32)
            params = center + noise * scale
            
        else:
            # EXPLOITATION: Search near random elite
            n_from_each = batch_size // len(self.elites) + 1
            idx = 0
            
            for score, elite_params in self.elites:
                if idx >= batch_size:
                    break
                    
                n_this = min(n_from_each, batch_size - idx)
                elite_gpu = xp.asarray(elite_params, dtype=xp.float32)
                
                # Small perturbation around elite (5-20% of range based on temperature)
                local_scale = ranges * (0.05 + 0.15 * self.temperature)
                noise = xp.random.uniform(-0.5, 0.5, size=(n_this, self.n_params)).astype(xp.float32)
                params[idx:idx+n_this] = elite_gpu + noise * local_scale
                idx += n_this
        
        # Clip to bounds
        params = xp.clip(params, bounds_gpu[:, 0], bounds_gpu[:, 1])
        
        return params
    
    def cool_down(self):
        """Apply cooling schedule."""
        self.temperature = max(FINAL_TEMPERATURE, self.temperature * COOLING_RATE)
        
    def maybe_reheat(self, configs_tested: int):
        """Reheat if stuck for too long."""
        self.configs_since_improvement += configs_tested
        
        if self.configs_since_improvement > REHEAT_THRESHOLD:
            old_temp = self.temperature
            self.temperature = min(1.0, self.temperature * 5)  # 5x reheat
            print(f"\n   🔥 REHEAT: {old_temp:.4f} → {self.temperature:.4f} (stuck for {self.configs_since_improvement:,} configs)")
            self.configs_since_improvement = 0


# =============================================================================
# GPU SCORING (same as before but optimized)
# =============================================================================

def score_batch_gpu(params: 'array', data: dict, xp=None) -> tuple:
    """
    Score a batch of parameter configs on GPU.
    
    CRITICAL: All outputs must be 1D arrays of shape (batch_size,)
    """
    if xp is None:
        xp = cp if GPU_AVAILABLE else np
    
    batch_size = params.shape[0]
    n_events = data['n_events']
    
    # Extract parameters as 1D arrays - shape (batch_size,)
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
    modality_pen = params[:, 15]
    ta_weight = params[:, 16]
    tier1_thresh = params[:, 17]
    tier2_thresh = params[:, 18]
    
    # Build probability matrix (batch_size, n_events)
    probs = xp.full((batch_size, n_events), 0.867, dtype=xp.float32)
    
    # Use outer product for proper broadcasting: (batch,) x (events,) -> (batch, events)
    probs += xp.outer(btd_w, data['btd'].astype(xp.float32))
    probs += xp.outer(orphan_w, data['orphan'].astype(xp.float32))
    probs += xp.outer(pr_w, data['priority_review'].astype(xp.float32))
    probs += xp.outer(ft_w, data['fast_track'].astype(xp.float32))
    probs += xp.outer(aa_w, data['has_accelerated'].astype(xp.float32))
    
    # AdCom adjustments
    had_adcom = data['had_adcom'].astype(xp.float32)
    adcom_pct = data['adcom_vote_pct']
    high_vote = ((adcom_pct >= 0.65) * had_adcom)
    mid_vote = (((adcom_pct >= 0.50) & (adcom_pct < 0.65)) * had_adcom)
    low_vote = ((adcom_pct < 0.50) * had_adcom)
    
    probs += xp.outer(adcom_high, high_vote)
    probs += xp.outer(adcom_mid, mid_vote)
    probs += xp.outer(adcom_low, low_vote)
    
    # Prior CRL / Resubmission
    probs += xp.outer(prior_crl_p, data['prior_crl'].astype(xp.float32))
    class1_mask = (data['resubmission_class'] == 1).astype(xp.float32)
    class2_mask = (data['resubmission_class'] == 2).astype(xp.float32)
    probs += xp.outer(class1_boost, class1_mask)
    probs += xp.outer(class2_pen, class2_mask)
    
    # Sponsor experience
    probs += xp.outer(exp_sponsor, data['experienced_sponsor'].astype(xp.float32))
    inexperienced = (data['sponsor_prior_approvals'] == 0).astype(xp.float32)
    probs += xp.outer(inexp_sponsor, inexperienced)
    
    # Manufacturing risk
    probs += xp.outer(mfg_risk, data['manufacturing_risk'].astype(xp.float32))
    probs += xp.outer(form483, data['form_483_issues'].astype(xp.float32))
    
    # Modality & TA
    probs += xp.outer(modality_pen, data['is_high_risk_modality'].astype(xp.float32))
    probs += xp.outer(ta_weight, data['ta_adjustment'])
    
    # Clip probabilities
    probs = xp.clip(probs, 0.01, 0.99)
    
    # Brier scores - shape (batch_size,)
    outcomes = data['outcomes']
    brier_per_event = (probs - outcomes) ** 2
    brier_scores = xp.mean(brier_per_event, axis=1)
    
    # Free memory
    del brier_per_event
    
    # Tier masks - (batch, events)
    # Use reshape for proper broadcasting
    t1_t = tier1_thresh.reshape(-1, 1)  # (batch, 1)
    t2_t = tier2_thresh.reshape(-1, 1)  # (batch, 1)
    
    tier1_mask = (probs >= t1_t)  # (batch, events)
    tier4_mask = (probs < t2_t)   # (batch, events)
    
    # Free probs
    del probs
    
    # Counts and rates - shape (batch_size,)
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
    
    # Free tier masks
    del tier1_mask, tier4_mask
    
    # Feasibility - ALL operations on 1D arrays of shape (batch_size,)
    # Each comparison produces shape (batch_size,)
    f1 = (tier1_thresh >= TIER1_MIN)
    f2 = (tier2_thresh <= TIER2_MAX)
    f3 = (tier1_thresh > tier2_thresh)
    f4 = (tier1_approval_rates >= TIER1_APPROVAL_MIN)
    f5 = (tier4_crl_rates >= TIER4_CRL_MIN)
    f6 = (tier1_counts >= 10)
    f7 = (tier4_counts >= 5)
    
    feasible = f1 & f2 & f3 & f4 & f5 & f6 & f7
    
    # CRITICAL: Ensure feasible is 1D
    assert feasible.ndim == 1, f"feasible must be 1D, got shape {feasible.shape}"
    assert feasible.shape[0] == batch_size, f"feasible shape {feasible.shape} != batch_size {batch_size}"
    
    # Clean up GPU memory
    if GPU_AVAILABLE:
        xp.get_default_memory_pool().free_all_blocks()
    
    return brier_scores, feasible, tier1_approval_rates, tier4_crl_rates


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

def run_optimization():
    """Run annealing-based optimization."""
    
    print("=" * 60, flush=True)
    print("ODIN v9.4 GPU ANNEALING OPTIMIZER - STARTING", flush=True)
    print("=" * 60, flush=True)
    
    # Initialize GPU first
    init_gpu()
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    xp = cp if GPU_AVAILABLE else np
    
    # Find dataset
    global DATASET_PATH
    if DATASET_PATH is None:
        print("Looking for dataset...", flush=True)
        DATASET_PATH = find_dataset()
        if DATASET_PATH is None:
            print("❌ ERROR: Could not find ODIN dataset file.", flush=True)
            print("   Please set DATASET_PATH manually at top of script.", flush=True)
            print("   Looking for files like: ODIN_v4_2_AUDITED.csv, ODIN_v4_FIXED.csv", flush=True)
            sys.exit(1)
        print(f"✅ Auto-detected dataset: {DATASET_PATH}", flush=True)
    
    # Load data
    print("Loading dataset...", flush=True)
    df = load_dataset(DATASET_PATH)
    
    # Detect VRAM and calculate safe batch size BEFORE GPU transfer
    total_vram, free_vram, safe_batch = detect_vram_and_batch_size(len(df))
    
    # Clear any existing GPU allocations
    clear_gpu_memory()
    
    # Now transfer data to GPU
    print("Transferring data to GPU...", flush=True)
    data = prepare_gpu_data(df)
    print(f"✅ Data transferred to GPU ({data['n_events']} events)", flush=True)
    
    # Re-check memory after data transfer
    if GPU_AVAILABLE:
        free_after = cp.cuda.Device().mem_info[0] / 1e9
        print(f"   VRAM after data load: {free_after:.1f} GB free")
        
        # Recalculate batch size - VERY CONSERVATIVE for RTX 4070
        n_events = len(df)
        bytes_per_config = n_events * 4 * 15  # 15 arrays of float32
        usable_bytes = free_after * 1e9 * 0.25  # Only use 25%
        safe_batch = int(usable_bytes / bytes_per_config)
        
        # Hard cap for 12GB cards
        safe_batch = max(MIN_BATCH_SIZE, min(50_000, safe_batch))
        print(f"   Adjusted batch size: {safe_batch:,}")
    
    # Initialize annealing search
    searcher = AnnealingSearch(PARAM_BOUNDS, elite_size=ELITE_SIZE)
    
    # Tracking
    best_score = float('inf')
    best_params = None
    best_metrics = None
    
    total_tested = 0
    total_feasible = 0
    batch_size = safe_batch  # Use calculated safe batch size
    
    start_time = time.time()
    last_progress = time.time()
    last_checkpoint = time.time()
    
    print(f"\n{'='*70}")
    print(f"ODIN v9.4 ANNEALING OPTIMIZER")
    print(f"{'='*70}")
    print(f"Target: {TOTAL_ITERATIONS:,} configurations")
    print(f"Temperature: {INITIAL_TEMPERATURE} → {FINAL_TEMPERATURE}")
    print(f"Elite population: {ELITE_SIZE}")
    print(f"{'='*70}\n")
    
    while total_tested < TOTAL_ITERATIONS:
        # Dynamic batch sizing based on VRAM
        if GPU_AVAILABLE:
            try:
                free_mem = cp.cuda.Device().mem_info[0] / 1e9
                
                if free_mem < 1.0:
                    # Critical - clear cache and reduce batch
                    clear_gpu_memory()
                    batch_size = max(MIN_BATCH_SIZE, int(batch_size * 0.5))
                    print(f"\n   ⚠️ Low VRAM ({free_mem:.1f}GB) - batch reduced to {batch_size:,}")
                elif free_mem < 2.0:
                    batch_size = max(MIN_BATCH_SIZE, int(batch_size * 0.8))
                elif free_mem > 4.0 and batch_size < MAX_BATCH_SIZE:
                    batch_size = min(MAX_BATCH_SIZE, int(batch_size * 1.1))
            except:
                pass  # Continue with current batch size
        
        try:
            # Generate batch using annealing strategy
            params = searcher.generate_batch(batch_size, xp)
            
            # Score batch
            brier_scores, feasible, t1_rates, t4_rates = score_batch_gpu(params, data, xp)
        except Exception as e:
            if 'OutOfMemory' in str(type(e).__name__) or 'memory' in str(e).lower():
                # Out of memory - reduce batch and retry
                clear_gpu_memory()
                batch_size = max(MIN_BATCH_SIZE, int(batch_size * 0.5))
                print(f"\n   💾 OOM - batch reduced to {batch_size:,}")
                continue
            else:
                raise e
        
        # Find best feasible - transfer to CPU first
        if GPU_AVAILABLE:
            feasible_mask = feasible.get()
            brier_np = brier_scores.get()
            params_np = params.get()
        else:
            feasible_mask = feasible
            brier_np = brier_scores
            params_np = params
        
        # Verify shape is 1D
        if feasible_mask.ndim != 1:
            print(f"\n⚠️  Shape error: feasible_mask has shape {feasible_mask.shape}, expected 1D")
            feasible_mask = feasible_mask.flatten()
        
        if len(feasible_mask) != batch_size:
            print(f"\n⚠️  Size mismatch: feasible={len(feasible_mask)}, batch={batch_size}")
            clear_gpu_memory()
            continue
        
        # Find feasible indices
        feasible_indices = np.where(feasible_mask)[0]
        
        total_tested += batch_size
        total_feasible += len(feasible_indices)
        
        if len(feasible_indices) > 0:
            # Transfer tier rates if not already done
            if GPU_AVAILABLE:
                t1_np = t1_rates.get()
                t4_np = t4_rates.get()
            else:
                t1_np = t1_rates
                t4_np = t4_rates
            
            feasible_briers = brier_np[feasible_indices]
            best_idx_in_feasible = np.argmin(feasible_briers)
            best_idx = feasible_indices[best_idx_in_feasible]
            batch_best_score = feasible_briers[best_idx_in_feasible]
            
            # Check for improvement
            if batch_best_score < best_score:
                improvement_pct = (best_score - batch_best_score) / best_score * 100 if best_score < float('inf') else 100
                
                best_score = batch_best_score
                best_params = params_np[best_idx].copy()
                best_metrics = {
                    'brier_score': float(batch_best_score),
                    'tier1_approval_rate': float(t1_np[best_idx]),
                    'tier4_crl_rate': float(t4_np[best_idx]),
                    'temperature': searcher.temperature
                }
                
                # Add to elite population
                searcher.add_elite(batch_best_score, best_params)
                
                print(f"\n   🎯 IMPROVEMENT #{searcher.total_improvements}: {best_score:.5f} (+{improvement_pct:.2f}%) @ T={searcher.temperature:.4f}")
                print(f"      Tier1 Approval: {best_metrics['tier1_approval_rate']*100:.1f}% | Tier4 CRL: {best_metrics['tier4_crl_rate']*100:.1f}%")
        
        # Cool down
        searcher.cool_down()
        
        # Check for reheat
        searcher.maybe_reheat(batch_size)
        
        # Progress report
        if time.time() - last_progress > 10:
            elapsed = time.time() - start_time
            rate = total_tested / elapsed
            eta = (TOTAL_ITERATIONS - total_tested) / rate / 60
            feasibility_rate = total_feasible / total_tested * 100
            
            free_mem = 0
            if GPU_AVAILABLE:
                try:
                    free_mem = cp.cuda.Device().mem_info[0] / 1e9
                    # Periodic memory cleanup every progress report
                    if free_mem < 3.0:
                        clear_gpu_memory()
                except:
                    pass
            
            print(f"Progress | Tested: {total_tested:>12,} | Feas: {feasibility_rate:>5.1f}% | Best: {best_score:.5f} | "
                  f"T: {searcher.temperature:.4f} | Batch: {batch_size:,} | VRAM: {free_mem:.1f}GB | "
                  f"{rate/1000:.0f}K/s | ETA: {eta:.1f}m")
            
            last_progress = time.time()
        
        # Checkpoint
        if time.time() - last_checkpoint > 300:  # Every 5 minutes
            save_checkpoint(searcher, best_score, best_params, best_metrics, total_tested)
            last_checkpoint = time.time()
    
    # Final results
    print(f"\n{'='*70}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total tested: {total_tested:,}")
    print(f"Total feasible: {total_feasible:,} ({total_feasible/total_tested*100:.1f}%)")
    print(f"Total improvements: {searcher.total_improvements}")
    print(f"Best Brier score: {best_score:.5f}")
    print(f"\nBest parameters:")
    
    if best_params is not None:
        for i, name in enumerate(PARAM_NAMES):
            print(f"  {name}: {best_params[i]:.4f}")
        
        # Save final config
        save_champion_config(best_params, best_metrics, total_tested, searcher.total_improvements)
    
    return best_score, best_params, best_metrics


def save_checkpoint(searcher, best_score, best_params, best_metrics, total_tested):
    """Save optimization checkpoint."""
    checkpoint = {
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
    
    print(f"   💾 Checkpoint saved ({len(searcher.elites)} elites)")


def save_champion_config(params, metrics, total_tested, total_improvements):
    """Save champion configuration."""
    config = {
        'version': '9.4-annealing',
        'optimization': {
            'method': 'simulated_annealing',
            'configs_tested': total_tested,
            'improvements_found': total_improvements,
            'timestamp': datetime.now().isoformat()
        },
        'performance': metrics,
        'champion_params': {name: float(params[i]) for i, name in enumerate(PARAM_NAMES)}
    }
    
    output_path = OUTPUT_DIR / f"ODIN_v94_CHAMPION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Champion config saved: {output_path}")


if __name__ == "__main__":
    print("Script starting...", flush=True)
    run_optimization()
