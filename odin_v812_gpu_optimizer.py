#!/usr/bin/env python3
"""
ODIN v8.12 GPU-Accelerated Scoring Engine (P001 CORRECTED)
===========================================================

Comprehensive biotech catalyst prediction system with 48 optimizable parameters.
Designed for RTX 4070 (12GB VRAM, 5888 CUDA cores, 46 SMs).

CRITICAL CORRECTION from v8.11:
- P001 override REMOVED (actual 69.4% vs claimed 99.5%)
- Class 1 CMC resubmission now treated as PENALTY signal
- Added w_resub_class1 parameter with bounds [-0.25, 0.00]

Usage:
    python odin_v812_gpu_optimizer.py --dataset odin_processed_v8.npy --configs 1000000000

Author: ODIN Research Authority
Version: 8.12 (P001 Corrected)
Date: 2026-01-24
"""

import numpy as np
import json
import time
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# GPU SETUP
# =============================================================================

try:
    import cupy as cp
    GPU_AVAILABLE = True
    # Get GPU properties using correct CuPy API
    device = cp.cuda.Device(0)
    props = cp.cuda.runtime.getDeviceProperties(0)
    GPU_NAME = props['name'].decode() if isinstance(props['name'], bytes) else props['name']
    GPU_VRAM = device.mem_info[1] / 1e9
    print(f"✓ CuPy GPU acceleration: {GPU_NAME} ({GPU_VRAM:.1f} GB)")
except ImportError:
    cp = np
    GPU_AVAILABLE = False
    GPU_NAME = "CPU"
    GPU_VRAM = 0
    print(f"⚠ CuPy not installed, using NumPy CPU fallback")
except Exception as e:
    cp = np
    GPU_AVAILABLE = False
    GPU_NAME = "CPU"
    GPU_VRAM = 0
    print(f"⚠ GPU unavailable ({e}), using NumPy CPU fallback")


# =============================================================================
# CONSTANTS
# =============================================================================

N_FEATURES = 44
N_PARAMS = 48

# Column indices for input data array
COL_IDX = {
    # Core outcomes and designations (0-13)
    'outcome': 0,
    'btd': 1,
    'orphan': 2,
    'priority': 3,
    'fast_track': 4,
    'accel': 5,
    'experienced': 6,
    'stack_count': 7,
    'mfg_risk': 8,
    'had_adcom': 9,
    'adcom_vote': 10,
    'prior_crl': 11,
    'resubmission_class': 12,
    'first_cycle': 13,
    
    # Therapeutic areas (14-21)
    'ta_onco': 14,
    'ta_inf': 15,
    'ta_cns': 16,
    'ta_rare': 17,
    'ta_pain': 18,
    'ta_cardio': 19,
    'ta_nephro': 20,
    'ta_ophthal': 21,
    
    # Modality (22-26)
    'mod_sm': 22,
    'mod_antibody': 23,
    'mod_adc': 24,
    'mod_cell': 25,
    'mod_gene': 26,
    
    # MCP/Social signals (27-37)
    'social_total': 27,
    'cluster_sell': 28,
    'pcr_extreme': 29,
    'pub_volume': 30,
    'trial_velocity': 31,
    'divergence': 32,
    'eu_not_us': 33,
    'post_sell': 34,
    'trial_design_risk': 35,
    'genetic_support': 36,
    'proctor_risk': 37,
    
    # Forensic signals (38-43)
    'void_6mo': 38,
    'hiring_slope': 39,
    'herg_risk': 40,
    'logp_risk': 41,
    'timeline_delay': 42,
    'single_trial': 43,
}

# Parameter indices for optimization array
PARAM_IDX = {
    # Core parameters (0-14)
    'p_base': 0,
    'p_threshold': 1,
    'w_social': 2,
    'w_btd': 3,
    'w_orphan': 4,
    'w_priority': 5,
    'w_fast': 6,
    'w_accel': 7,
    'w_exp': 8,
    'w_stack': 9,
    'w_mfg_pen': 10,
    'w_mfg_amp': 11,
    'i_mfg_inexp': 12,
    'w_adcom': 13,
    'w_des_trap': 14,
    
    # Therapeutic area adjustments (15-23)
    'adj_onco': 15,
    'adj_inf': 16,
    'adj_cns': 17,
    'adj_cns_amp': 18,
    'adj_rare': 19,
    'adj_pain': 20,
    'adj_cardio': 21,
    'adj_nephro': 22,
    'adj_ophthal': 23,
    
    # MCP pattern weights (24-36)
    'w_p002_cluster': 24,
    'w_p003_des_trap_ext': 25,
    'w_p1_insider': 26,
    'w_p2_pcr': 27,
    'w_p3_pubvol': 28,
    'w_p4_velocity': 29,
    'w_p5_divergence': 30,
    'w_p6_eu_not_us': 31,
    'w_p7_post_sell': 32,
    'w_s1_trial_design': 33,
    'w_s4_genetic': 34,
    'w_s5_proctor': 35,
    'w_resub_class1': 36,  # P001 CORRECTED: Now a PENALTY signal
    
    # Forensic signal weights (37-47)
    'w_void_6mo': 37,
    'w_void_9mo': 38,
    'w_void_12mo': 39,
    'w_hiring_slope': 40,
    'w_herg': 41,
    'w_logp': 42,
    'w_timeline_delay': 43,
    'w_single_trial': 44,
    'w_us_site': 45,
    'w_pub_velocity': 46,
    'w_mod_penalty': 47,
}


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class SignalBounds:
    """Parameter search bounds for optimization."""
    
    # Core parameters
    p_base: Tuple[float, float] = (0.55, 0.92)
    p_threshold: Tuple[float, float] = (0.45, 0.92)
    w_social: Tuple[float, float] = (-2.0, 12.0)  # EXPANDED for social signal testing
    w_btd: Tuple[float, float] = (0.00, 0.15)
    w_orphan: Tuple[float, float] = (-0.08, 0.12)
    w_priority: Tuple[float, float] = (0.00, 0.12)
    w_fast: Tuple[float, float] = (0.00, 0.08)
    w_accel: Tuple[float, float] = (0.00, 0.12)
    w_exp: Tuple[float, float] = (-0.05, 0.12)
    w_stack: Tuple[float, float] = (-0.05, 0.05)
    w_mfg_pen: Tuple[float, float] = (-0.45, -0.05)  # Strong negative (52% vs 87%)
    w_mfg_amp: Tuple[float, float] = (0.5, 3.0)
    i_mfg_inexp: Tuple[float, float] = (0.5, 2.5)
    w_adcom: Tuple[float, float] = (0.05, 0.60)
    w_des_trap: Tuple[float, float] = (-0.25, 0.00)
    
    # Therapeutic area adjustments
    adj_onco: Tuple[float, float] = (-0.05, 0.15)
    adj_inf: Tuple[float, float] = (-0.05, 0.15)
    adj_cns: Tuple[float, float] = (-0.15, 0.10)
    adj_cns_amp: Tuple[float, float] = (-0.20, 0.10)
    adj_rare: Tuple[float, float] = (-0.05, 0.15)
    adj_pain: Tuple[float, float] = (-0.30, 0.00)  # 74% vs 87%
    adj_cardio: Tuple[float, float] = (-0.20, 0.05)
    adj_nephro: Tuple[float, float] = (-0.20, 0.05)
    adj_ophthal: Tuple[float, float] = (-0.15, 0.05)
    
    # MCP pattern weights
    w_p002_cluster: Tuple[float, float] = (-0.40, 0.00)
    w_p003_des_trap_ext: Tuple[float, float] = (-0.25, 0.00)
    w_p1_insider: Tuple[float, float] = (-0.15, 0.00)
    w_p2_pcr: Tuple[float, float] = (-0.15, 0.00)
    w_p3_pubvol: Tuple[float, float] = (-0.20, 0.00)
    w_p4_velocity: Tuple[float, float] = (-0.20, 0.00)
    w_p5_divergence: Tuple[float, float] = (-0.30, 0.00)
    w_p6_eu_not_us: Tuple[float, float] = (-0.15, 0.00)
    w_p7_post_sell: Tuple[float, float] = (0.00, 0.15)
    w_s1_trial_design: Tuple[float, float] = (-0.20, 0.00)
    w_s4_genetic: Tuple[float, float] = (0.00, 0.35)
    w_s5_proctor: Tuple[float, float] = (-0.20, 0.00)
    
    # P001 CORRECTED: Class 1 CMC resubmission = PENALTY (69.4% vs 86.7% baseline)
    w_resub_class1: Tuple[float, float] = (-0.25, 0.00)
    
    # Forensic signal weights
    w_void_6mo: Tuple[float, float] = (-0.60, 0.00)
    w_void_9mo: Tuple[float, float] = (-0.30, 0.00)
    w_void_12mo: Tuple[float, float] = (-0.15, 0.00)
    w_hiring_slope: Tuple[float, float] = (0.00, 0.20)
    w_herg: Tuple[float, float] = (-0.25, 0.00)
    w_logp: Tuple[float, float] = (-0.15, 0.00)
    w_timeline_delay: Tuple[float, float] = (-0.20, 0.00)
    w_single_trial: Tuple[float, float] = (-0.15, 0.00)
    w_us_site: Tuple[float, float] = (-0.10, 0.05)
    w_pub_velocity: Tuple[float, float] = (0.00, 0.10)
    w_mod_penalty: Tuple[float, float] = (-0.20, 0.00)


@dataclass
class ScoringCaps:
    """Hard caps for probability clamping."""
    max_positive_adj: float = 0.25
    max_negative_adj: float = -0.50
    void_hard_cap: float = 0.40
    min_probability: float = 0.05
    max_probability: float = 0.95
    # P001 REMOVED - no longer using 0.995 override
    fatal_flaw_cap: float = 0.30


@dataclass 
class OptimizationConfig:
    """Optimization run settings."""
    batch_size: int = 750_000  # Memory-optimized for RTX 4070 12GB VRAM
    total_configs: int = 1_000_000_000
    early_stop_patience: int = 100
    report_interval: int = 10
    save_top_n: int = 100
    objective_weights: Dict[str, float] = field(default_factory=lambda: {
        'brier': -0.30,
        'f1': 0.25,
        'specificity': 0.35,
        'precision': 0.10,
    })


# =============================================================================
# SCORING ENGINE
# =============================================================================

def batch_score_vectorized(data, params, caps: ScoringCaps, xp=np):
    """
    Vectorized batch scoring - GPU accelerated with memory optimization.
    
    Args:
        data: (n_events, N_FEATURES) array
        params: (n_configs, N_PARAMS) array
        caps: ScoringCaps instance
        xp: cupy or numpy
    
    Returns:
        probs: (n_configs, n_events) probabilities
        preds: (n_configs, n_events) binary predictions
    """
    n_events = data.shape[0]
    n_configs = params.shape[0]
    
    # Pre-allocate output array and reusable temp buffer
    probs = xp.empty((n_configs, n_events), dtype=xp.float32)
    temp = xp.empty((n_configs, n_events), dtype=xp.float32)
    
    # Initialize with base probability
    probs[:] = params[:, PARAM_IDX['p_base'], None]
    
    # === CORE DESIGNATION SIGNALS (in-place) ===
    xp.multiply(params[:, PARAM_IDX['w_btd'], None], data[None, :, COL_IDX['btd']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_orphan'], None], data[None, :, COL_IDX['orphan']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_priority'], None], data[None, :, COL_IDX['priority']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_fast'], None], data[None, :, COL_IDX['fast_track']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_accel'], None], data[None, :, COL_IDX['accel']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_exp'], None], data[None, :, COL_IDX['experienced']], out=temp)
    probs += temp
    
    xp.multiply(params[:, PARAM_IDX['w_stack'], None], data[None, :, COL_IDX['stack_count']], out=temp)
    probs += temp
    
    # === MANUFACTURING RISK (with amplifier for inexperienced sponsors) ===
    # mfg_base * mfg_amp
    xp.multiply(params[:, PARAM_IDX['w_mfg_pen'], None], data[None, :, COL_IDX['mfg_risk']], out=temp)
    temp *= params[:, PARAM_IDX['w_mfg_amp'], None]
    probs += temp
    
    # interaction term: i_mfg_inexp * mfg_risk * (1 - experienced)
    inexp_mask = 1 - data[:, COL_IDX['experienced']]
    xp.multiply(params[:, PARAM_IDX['i_mfg_inexp'], None], data[None, :, COL_IDX['mfg_risk']], out=temp)
    temp *= inexp_mask[None, :]
    probs += temp
    
    # === ADCOM VOTE ===
    adcom_effect = (data[:, COL_IDX['adcom_vote']] - 0.5) * data[:, COL_IDX['had_adcom']]
    xp.multiply(params[:, PARAM_IDX['w_adcom'], None], adcom_effect[None, :], out=temp)
    probs += temp
    
    # === THERAPEUTIC AREA ADJUSTMENTS ===
    for adj_name, col_name in [
        ('adj_onco', 'ta_onco'), ('adj_inf', 'ta_inf'), ('adj_cns', 'ta_cns'),
        ('adj_rare', 'ta_rare'), ('adj_pain', 'ta_pain'), ('adj_cardio', 'ta_cardio'),
        ('adj_nephro', 'ta_nephro'), ('adj_ophthal', 'ta_ophthal')
    ]:
        xp.multiply(params[:, PARAM_IDX[adj_name], None], data[None, :, COL_IDX[col_name]], out=temp)
        probs += temp
    
    # === DESIGNATION TRAP (high designations + inexperienced sponsor) ===
    des_trap_flag = ((data[:, COL_IDX['stack_count']] >= 4) * 
                     (1 - data[:, COL_IDX['experienced']])).astype(xp.float32)
    xp.multiply(params[:, PARAM_IDX['w_des_trap'], None], des_trap_flag[None, :], out=temp)
    probs += temp
    
    # === SOCIAL SIGNALS ===
    xp.multiply(params[:, PARAM_IDX['w_social'], None], data[None, :, COL_IDX['social_total']], out=temp)
    probs += temp
    
    # === MCP PATTERN SIGNALS ===
    for w_name, col_name in [
        ('w_p002_cluster', 'cluster_sell'), ('w_p2_pcr', 'pcr_extreme'),
        ('w_p3_pubvol', 'pub_volume'), ('w_p4_velocity', 'trial_velocity'),
        ('w_p5_divergence', 'divergence'), ('w_p6_eu_not_us', 'eu_not_us'),
        ('w_p7_post_sell', 'post_sell'), ('w_s1_trial_design', 'trial_design_risk'),
        ('w_s4_genetic', 'genetic_support'), ('w_s5_proctor', 'proctor_risk')
    ]:
        xp.multiply(params[:, PARAM_IDX[w_name], None], data[None, :, COL_IDX[col_name]], out=temp)
        probs += temp
    
    # === P001 CORRECTED: Class 1 CMC Resubmission as PENALTY ===
    class1_mask = ((data[:, COL_IDX['prior_crl']] == 1) & 
                   (data[:, COL_IDX['resubmission_class']] == 1)).astype(xp.float32)
    xp.multiply(params[:, PARAM_IDX['w_resub_class1'], None], class1_mask[None, :], out=temp)
    probs += temp
    
    # === FORENSIC SIGNALS ===
    for w_name, col_name in [
        ('w_void_6mo', 'void_6mo'), ('w_hiring_slope', 'hiring_slope'),
        ('w_herg', 'herg_risk'), ('w_logp', 'logp_risk'),
        ('w_timeline_delay', 'timeline_delay'), ('w_single_trial', 'single_trial')
    ]:
        xp.multiply(params[:, PARAM_IDX[w_name], None], data[None, :, COL_IDX[col_name]], out=temp)
        probs += temp
    
    # === HARD CAPS ===
    # VOID hard cap (zero commercial hiring = max 40%)
    void_mask = data[:, COL_IDX['void_6mo']] > 0.5
    probs[:, void_mask] = xp.minimum(probs[:, void_mask], caps.void_hard_cap)
    
    # Clamp to valid probability range
    xp.clip(probs, caps.min_probability, caps.max_probability, out=probs)
    
    # Generate binary predictions
    preds = (probs >= params[:, PARAM_IDX['p_threshold'], None]).astype(xp.float32)
    
    # Free temp buffer
    del temp
    
    return probs, preds


def compute_metrics(probs, preds, outcomes, xp=np):
    """Compute classification metrics for all configurations."""
    outcomes_2d = outcomes[None, :].astype(xp.float32)
    
    tp = xp.sum((preds == 1) & (outcomes_2d == 1), axis=1).astype(xp.float32)
    fp = xp.sum((preds == 1) & (outcomes_2d == 0), axis=1).astype(xp.float32)
    tn = xp.sum((preds == 0) & (outcomes_2d == 0), axis=1).astype(xp.float32)
    fn = xp.sum((preds == 0) & (outcomes_2d == 1), axis=1).astype(xp.float32)
    
    precision = tp / xp.maximum(tp + fp, 1e-10)
    recall = tp / xp.maximum(tp + fn, 1e-10)
    f1 = 2 * precision * recall / xp.maximum(precision + recall, 1e-10)
    specificity = tn / xp.maximum(tn + fp, 1e-10)
    brier = xp.mean((probs - outcomes_2d) ** 2, axis=1)
    
    mcc_num = tp * tn - fp * fn
    mcc_denom = xp.sqrt(xp.maximum((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn), 1e-10))
    mcc = mcc_num / mcc_denom
    
    return {
        'brier': brier, 'precision': precision, 'recall': recall,
        'f1': f1, 'specificity': specificity, 'mcc': mcc,
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn
    }


def compute_objective(metrics, weights, xp=np):
    """Compute weighted objective score (higher = better)."""
    return (
        weights.get('brier', -0.30) * metrics['brier'] +
        weights.get('f1', 0.25) * metrics['f1'] +
        weights.get('specificity', 0.35) * metrics['specificity'] +
        weights.get('precision', 0.10) * metrics['precision']
    )


# =============================================================================
# OPTIMIZER CLASS
# =============================================================================

class ODINOptimizer:
    """Multi-phase ODIN parameter optimizer."""
    
    def __init__(self, data: np.ndarray,
                 bounds: SignalBounds = None,
                 caps: ScoringCaps = None,
                 config: OptimizationConfig = None):
        
        self.bounds = bounds or SignalBounds()
        self.caps = caps or ScoringCaps()
        self.config = config or OptimizationConfig()
        
        # Setup compute backend
        self.use_gpu = GPU_AVAILABLE
        self.xp = cp if self.use_gpu else np
        
        # Transfer data to GPU
        if self.use_gpu:
            self.data = cp.asarray(data, dtype=cp.float32)
        else:
            self.data = data.astype(np.float32)
        
        self.outcomes = self.data[:, COL_IDX['outcome']]
        self.n_events = data.shape[0]
        
        # Tracking
        self.best_params = None
        self.best_score = -np.inf
        self.best_metrics = None
        self.top_configs = []
        
        # Build bounds arrays
        self._build_bounds_arrays()
        
        # Stats
        n_approvals = int((self.outcomes == 1).sum())
        n_crls = self.n_events - n_approvals
        
        # Memory estimate (with in-place ops: probs + temp + preds + params)
        mem_per_batch_gb = (self.config.batch_size * self.n_events * 4 * 3 + 
                            self.config.batch_size * N_PARAMS * 4) / 1e9
        
        print(f"\n{'='*60}")
        print(f"ODIN v8.12 Optimizer Initialized (P001 CORRECTED)")
        print(f"{'='*60}")
        print(f"  Events: {self.n_events:,} ({n_approvals} approvals, {n_crls} CRLs)")
        print(f"  Base rate: {100*n_approvals/self.n_events:.1f}%")
        print(f"  Compute: {'GPU (' + GPU_NAME + ')' if self.use_gpu else 'CPU'}")
        print(f"  Parameters: {N_PARAMS}")
        print(f"  Batch size: {self.config.batch_size:,}")
        print(f"  Est. GPU memory/batch: {mem_per_batch_gb:.1f} GB")
        print(f"{'='*60}")
    
    def _build_bounds_arrays(self):
        """Convert bounds dataclass to arrays for vectorized sampling."""
        bounds_list = []
        for idx in range(N_PARAMS):
            # Find param name for this index
            param_name = None
            for name, i in PARAM_IDX.items():
                if i == idx:
                    param_name = name
                    break
            
            if param_name and hasattr(self.bounds, param_name):
                bounds_list.append(getattr(self.bounds, param_name))
            else:
                bounds_list.append((0.0, 1.0))
        
        self.bounds_array = np.array(bounds_list, dtype=np.float32)
        self.bounds_low = self.bounds_array[:, 0]
        self.bounds_high = self.bounds_array[:, 1]
    
    def generate_random_params(self, n: int) -> np.ndarray:
        """Generate n random parameter configurations within bounds."""
        params = np.random.uniform(
            self.bounds_low, self.bounds_high,
            size=(n, N_PARAMS)
        ).astype(np.float32)
        return params
    
    def evaluate_batch(self, params: np.ndarray):
        """Evaluate a batch of configurations."""
        xp = self.xp
        
        if self.use_gpu:
            params_gpu = cp.asarray(params, dtype=cp.float32)
        else:
            params_gpu = params
        
        probs, preds = batch_score_vectorized(self.data, params_gpu, self.caps, xp)
        metrics = compute_metrics(probs, preds, self.outcomes, xp)
        scores = compute_objective(metrics, self.config.objective_weights, xp)
        
        if self.use_gpu:
            scores = cp.asnumpy(scores)
            metrics = {k: cp.asnumpy(v) for k, v in metrics.items()}
            # Free GPU memory
            del probs, preds, params_gpu
            cp.get_default_memory_pool().free_all_blocks()
        
        return scores, metrics
    
    def run_global_search(self, n_configs: int = None):
        """Run global random search optimization."""
        n_configs = n_configs or self.config.total_configs
        batch_size = self.config.batch_size
        n_batches = (n_configs + batch_size - 1) // batch_size
        
        print(f"\n{'='*60}")
        print(f"GLOBAL SEARCH: {n_configs:,} configurations")
        print(f"Batches: {n_batches:,} x {batch_size:,}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        configs_tested = 0
        no_improve_count = 0
        
        for batch_idx in range(n_batches):
            # Generate and evaluate batch
            batch_params = self.generate_random_params(batch_size)
            scores, metrics = self.evaluate_batch(batch_params)
            
            # Track top configs
            top_indices = np.argsort(scores)[-self.config.save_top_n:]
            for idx in top_indices:
                self.top_configs.append({
                    'params': batch_params[idx].copy(),
                    'score': scores[idx],
                    'metrics': {k: v[idx] for k, v in metrics.items()}
                })
            
            # Keep only top N overall
            self.top_configs.sort(key=lambda x: x['score'], reverse=True)
            self.top_configs = self.top_configs[:self.config.save_top_n]
            
            # Update best
            best_idx = np.argmax(scores)
            if scores[best_idx] > self.best_score:
                self.best_score = scores[best_idx]
                self.best_params = batch_params[best_idx].copy()
                self.best_metrics = {k: v[best_idx] for k, v in metrics.items()}
                no_improve_count = 0
            else:
                no_improve_count += 1
            
            configs_tested += batch_size
            
            # Progress report
            if (batch_idx + 1) % self.config.report_interval == 0:
                elapsed = time.time() - start_time
                rate = configs_tested / elapsed
                eta = (n_configs - configs_tested) / rate if rate > 0 else 0
                
                print(f"Batch {batch_idx+1:,}/{n_batches:,} | "
                      f"Best: {self.best_score:.5f} | "
                      f"Brier: {self.best_metrics['brier']:.4f} | "
                      f"F1: {self.best_metrics['f1']:.4f} | "
                      f"Spec: {self.best_metrics['specificity']:.3f} | "
                      f"Prec: {self.best_metrics['precision']:.3f} | "
                      f"Rate: {rate/1e6:.2f}M/s | "
                      f"ETA: {eta/60:.1f}m")
            
            # Early stopping
            if no_improve_count >= self.config.early_stop_patience:
                print(f"\n⚠ Early stopping after {no_improve_count} batches without improvement")
                break
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"OPTIMIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"  Configs tested: {configs_tested:,}")
        print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  Rate: {configs_tested/elapsed/1e6:.2f}M configs/second")
        print(f"\nBest Configuration:")
        print(f"  Objective Score: {self.best_score:.5f}")
        print(f"  Brier Score: {self.best_metrics['brier']:.4f}")
        print(f"  Precision: {self.best_metrics['precision']:.4f}")
        print(f"  Recall: {self.best_metrics['recall']:.4f}")
        print(f"  F1 Score: {self.best_metrics['f1']:.4f}")
        print(f"  Specificity: {self.best_metrics['specificity']:.4f}")
        print(f"  MCC: {self.best_metrics['mcc']:.4f}")
        print(f"  TP: {int(self.best_metrics['tp'])}, FP: {int(self.best_metrics['fp'])}, "
              f"TN: {int(self.best_metrics['tn'])}, FN: {int(self.best_metrics['fn'])}")
        print(f"{'='*60}")
        
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'best_metrics': self.best_metrics,
            'configs_tested': configs_tested,
            'elapsed': elapsed,
            'top_configs': self.top_configs[:10],
        }
    
    def save_results(self, path: str):
        """Save optimization results to JSON."""
        params_dict = {}
        for name, idx in PARAM_IDX.items():
            params_dict[name] = float(self.best_params[idx])
        
        results = {
            'version': '8.12-P001-corrected',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'note': 'P001 override REMOVED - Class 1 CMC resubmission now penalty signal',
            'parameters': params_dict,
            'metrics': {
                'brier': float(self.best_metrics['brier']),
                'precision': float(self.best_metrics['precision']),
                'recall': float(self.best_metrics['recall']),
                'f1': float(self.best_metrics['f1']),
                'specificity': float(self.best_metrics['specificity']),
                'mcc': float(self.best_metrics['mcc']),
                'tp': int(self.best_metrics['tp']),
                'fp': int(self.best_metrics['fp']),
                'tn': int(self.best_metrics['tn']),
                'fn': int(self.best_metrics['fn']),
            },
            'objective_score': float(self.best_score),
            'top_10_configs': [
                {
                    'score': float(c['score']),
                    'brier': float(c['metrics']['brier']),
                    'specificity': float(c['metrics']['specificity']),
                    'precision': float(c['metrics']['precision']),
                }
                for c in self.top_configs[:10]
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to {path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ODIN v8.12 GPU Optimizer (P001 Corrected)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--dataset', required=True, help='Path to processed .npy file')
    parser.add_argument('--configs', type=int, default=1_000_000_000, help='Total configs to test')
    parser.add_argument('--batch-size', type=int, default=750_000, help='Configs per GPU batch (750K optimal for 12GB VRAM)')
    parser.add_argument('--output', default='odin_v812_optimized.json', help='Output JSON path')
    parser.add_argument('--early-stop', type=int, default=100, help='Early stop patience (batches)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"\nLoading dataset: {args.dataset}")
    data = np.load(args.dataset)
    print(f"Shape: {data.shape}")
    
    # Validate
    assert data.shape[1] == N_FEATURES, f"Expected {N_FEATURES} features, got {data.shape[1]}"
    
    # Configure
    config = OptimizationConfig(
        batch_size=args.batch_size,
        total_configs=args.configs,
        early_stop_patience=args.early_stop,
    )
    
    # Optimize
    optimizer = ODINOptimizer(data, config=config)
    results = optimizer.run_global_search()
    
    # Save
    optimizer.save_results(args.output)
    
    print(f"\n✓ Optimization complete!")
    print(f"  Run: python {__file__} --dataset {args.dataset} --configs {args.configs}")


if __name__ == '__main__':
    main()
