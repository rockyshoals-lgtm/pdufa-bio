#!/usr/bin/env python3
"""
ODIN v6 GPU Optimizer - 11 T-1 Compliant Features
==================================================
Fast simulated annealing with dynamic VRAM management.

Features (11 total):
  - btd, orphan, priority_review, accelerated_approval, had_adcom, adcom_vote_pct
  - sponsor_experienced, sponsor_novice, high_risk_ta, low_risk_ta, modality_complexity

Expected: ~6.8% Brier improvement (vs 3% with 6 features)

Usage:
  python odin_v6_gpu_optimizer.py --csv ODIN_v5_T1_COMPLIANT.csv
  python odin_v6_gpu_optimizer.py --csv ODIN_v5_T1_COMPLIANT.csv --max-configs 500000000
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

HIGH_RISK_TAS = ['Pain Management', 'Hematology', 'Nephrology', 'Ophthalmology', 
                 'CNS/Neurology', 'Cardiovascular']
LOW_RISK_TAS = ['Oncology', 'Infectious Disease', 'Vaccines', 'GI/Hepatology', 
                'Respiratory', 'Dermatology']

FEATURES = [
    'btd', 'orphan', 'priority_review', 'accelerated_approval', 
    'had_adcom', 'adcom_vote_pct',
    'sponsor_experienced', 'sponsor_novice', 
    'high_risk_ta', 'low_risk_ta', 
    'modality_complexity'
]

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived T-1 compliant features."""
    df = df.copy()
    
    # Sponsor experience buckets
    df['sponsor_experienced'] = (df['sponsor_prior_approvals'] >= 5).astype(float)
    df['sponsor_novice'] = (df['sponsor_prior_approvals'] == 0).astype(float)
    
    # Therapeutic area risk tiers
    df['high_risk_ta'] = df['therapeutic_area'].isin(HIGH_RISK_TAS).astype(float)
    df['low_risk_ta'] = df['therapeutic_area'].isin(LOW_RISK_TAS).astype(float)
    
    # Ensure modality_complexity exists
    if 'modality_complexity' not in df.columns:
        modality_map = {
            'Small Molecule': 0, 'Vaccine': 0,
            'Antibody': 1, 'Peptide': 1,
            'ADC': 2,
            'RNA Therapy': 3,
            'Cell/Gene Therapy': 4
        }
        df['modality_complexity'] = df['modality'].map(modality_map).fillna(0)
    
    return df

# =============================================================================
# GPU DETECTION & DYNAMIC VRAM
# =============================================================================

def get_device_and_batch_size():
    """Detect GPU and calculate optimal batch size based on available VRAM."""
    try:
        import cupy as cp
        mempool = cp.get_default_memory_pool()
        mempool.free_all_blocks()
        
        device = cp.cuda.Device(0)
        free_vram = device.mem_info[0] / 1e9
        total_vram = device.mem_info[1] / 1e9
        
        # Dynamic batch sizing: use 60% of free VRAM
        # Each config needs: 11 floats (weights) + 1 float (bias) + 1 float (brier) = 52 bytes
        # Plus working memory for matrix ops
        bytes_per_config = 52 + 200  # Conservative estimate with working memory
        target_vram = free_vram * 0.6 * 1e9
        batch_size = int(target_vram / bytes_per_config)
        batch_size = min(batch_size, 10_000_000)  # Cap at 10M
        batch_size = max(batch_size, 500_000)     # Floor at 500K
        
        print(f"[GPU] {device.name} | {free_vram:.1f}/{total_vram:.1f} GB free | batch={batch_size:,}")
        return 'cuda', batch_size, cp
        
    except Exception as e:
        print(f"[CPU] CUDA unavailable ({e}), using NumPy")
        return 'cpu', 100_000, np

# =============================================================================
# CORE OPTIMIZER
# =============================================================================

def sigmoid(x, xp):
    """Numerically stable sigmoid."""
    return 1 / (1 + xp.exp(-xp.clip(x, -500, 500)))

def brier_score(probs, y_true, xp):
    """Calculate Brier score."""
    return xp.mean((probs - y_true) ** 2)

def run_optimization(
    X: np.ndarray,
    y: np.ndarray,
    max_configs: int = 1_000_000_000,
    stall_limit: int = 100_000_000,
    sigma_init: float = 0.8,
    output_dir: str = ".",
    csv_path: str = "unknown"
):
    """
    GPU-accelerated simulated annealing optimizer.
    
    Strategy:
    - Start with random perturbations around base rate
    - Anneal sigma when improvements found
    - Early stop after stall_limit configs without improvement
    """
    device, batch_size, xp = get_device_and_batch_size()
    
    n_samples, n_features = X.shape
    
    # Move data to GPU
    if device == 'cuda':
        X_gpu = xp.asarray(X.astype(np.float32))
        y_gpu = xp.asarray(y.astype(np.float32))
    else:
        X_gpu, y_gpu = X.astype(np.float32), y.astype(np.float32)
    
    # Initialize from base rate
    base_rate = float(y.mean())
    base_logit = float(np.log(base_rate / (1 - base_rate)))
    baseline_brier = base_rate * (1 - base_rate)
    
    # Current best
    best_weights = xp.zeros(n_features, dtype=xp.float32)
    best_bias = xp.float32(base_logit)
    best_brier = xp.float32(baseline_brier)
    
    # Annealing parameters
    sigma = sigma_init
    sigma_bias = sigma_init
    sigma_decay = 0.995
    sigma_boost = 1.02
    min_sigma = 0.01
    
    # Tracking
    configs_done = 0
    configs_since_improvement = 0
    improvements = []
    start_time = time.time()
    last_log = start_time
    
    # Output files
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    progress_log = output_dir / "progress.log"
    best_configs_file = output_dir / "best_configs.jsonl"
    
    def log_progress(msg):
        with open(progress_log, 'a') as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def save_best(event="new_best"):
        record = {
            "event": event,
            "best_brier": float(best_brier),
            "bias": float(best_bias),
            "weights": [float(w) for w in best_weights],
            "configs_done": configs_done,
            "sigma": sigma,
            "sigma_bias": sigma_bias,
            "utc": datetime.now(timezone.utc).isoformat()
        }
        with open(best_configs_file, 'a') as f:
            f.write(json.dumps(record) + "\n")
        return record
    
    # Initial log
    log_progress(f"start | rows={n_samples} | features={FEATURES} | device={device}")
    log_progress(f"baseline_brier={baseline_brier:.8f} | base_rate={base_rate:.4f}")
    save_best("init_base_rate")
    
    # Main optimization loop
    while configs_done < max_configs and configs_since_improvement < stall_limit:
        # Generate batch of candidates
        if device == 'cuda':
            # Perturb weights
            weight_noise = xp.random.normal(0, sigma, (batch_size, n_features)).astype(xp.float32)
            bias_noise = xp.random.normal(0, sigma_bias, batch_size).astype(xp.float32)
            
            candidate_weights = best_weights + weight_noise
            candidate_bias = best_bias + bias_noise
            
            # Calculate predictions for all candidates
            # Shape: (batch_size, n_samples)
            logits = candidate_bias[:, None] + xp.dot(candidate_weights, X_gpu.T)
            probs = sigmoid(logits, xp)
            
            # Brier scores
            briers = xp.mean((probs - y_gpu) ** 2, axis=1)
            
            # Find best in batch
            best_idx = xp.argmin(briers)
            batch_best_brier = briers[best_idx]
            
            # Update if improved
            if batch_best_brier < best_brier:
                improvement = float((best_brier - batch_best_brier) / best_brier * 100)
                best_brier = batch_best_brier
                best_weights = candidate_weights[best_idx].copy()
                best_bias = candidate_bias[best_idx]
                configs_since_improvement = 0
                sigma *= sigma_decay
                sigma_bias *= sigma_decay
                
                record = save_best("new_best")
                improvements.append(record)
                
                if improvement > 0.001:
                    log_progress(f"NEW BEST | brier={float(best_brier):.8f} | +{improvement:.4f}% | sigma={sigma:.4f}")
            else:
                configs_since_improvement += batch_size
                # Boost sigma if stuck
                if configs_since_improvement > 10_000_000 and sigma < sigma_init:
                    sigma = min(sigma * sigma_boost, sigma_init)
                    sigma_bias = min(sigma_bias * sigma_boost, sigma_init)
        
        else:
            # CPU fallback (slower)
            for _ in range(batch_size):
                candidate_weights = best_weights + np.random.normal(0, sigma, n_features).astype(np.float32)
                candidate_bias = best_bias + np.random.normal(0, sigma_bias)
                
                logits = candidate_bias + np.dot(X_gpu, candidate_weights)
                probs = sigmoid(logits, np)
                candidate_brier = brier_score(probs, y_gpu, np)
                
                if candidate_brier < best_brier:
                    best_brier = candidate_brier
                    best_weights = candidate_weights.copy()
                    best_bias = candidate_bias
                    configs_since_improvement = 0
                    sigma *= sigma_decay
                    sigma_bias *= sigma_decay
                    save_best("new_best")
                else:
                    configs_since_improvement += 1
        
        configs_done += batch_size
        
        # Periodic logging
        now = time.time()
        if now - last_log >= 1.0:
            elapsed = now - start_time
            rate = configs_done / elapsed
            
            if device == 'cuda':
                free_vram = xp.cuda.Device(0).mem_info[0] / 1e9
            else:
                free_vram = 0
            
            import psutil
            free_ram = psutil.virtual_memory().available / 1e9
            
            log_progress(
                f"progress | configs_done={configs_done:,} | best_brier={float(best_brier):.8f} | "
                f"sigma={sigma:.4f} | rate={rate/1e6:.1f}M/s | free_ram={free_ram:.2f}GB | free_vram={free_vram:.2f}GB"
            )
            last_log = now
    
    # Finalize
    elapsed = time.time() - start_time
    reason = "max_configs" if configs_done >= max_configs else "stall_reached"
    
    improvement_pct = (baseline_brier - float(best_brier)) / baseline_brier * 100
    
    # Save final champion
    champion = {
        "version": "ODIN_v6",
        "features": FEATURES,
        "n_features": n_features,
        "best_brier": float(best_brier),
        "baseline_brier": float(baseline_brier),
        "improvement_pct": improvement_pct,
        "bias": float(best_bias),
        "weights": [float(w) for w in best_weights],
        "configs_done": configs_done,
        "elapsed_seconds": elapsed,
        "reason": reason,
        "device": device,
        "utc_finished": datetime.now(timezone.utc).isoformat()
    }
    
    with open(output_dir / "champion_config.json", 'w') as f:
        json.dump(champion, f, indent=2)
    
    # Save run metadata
    meta = {
        "csv": csv_path,
        "features": FEATURES,
        "rows": n_samples,
        "max_configs": max_configs,
        "stall_limit": stall_limit,
        "sigma_init": sigma_init,
        "device": device,
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "utc_started": datetime.now(timezone.utc).isoformat()
    }
    
    with open(output_dir / "run_meta.json", 'w') as f:
        json.dump(meta, f, indent=2)
    
    log_progress(f"FINISHED | reason={reason} | brier={float(best_brier):.8f} | improvement={improvement_pct:.2f}%")
    
    return champion

# =============================================================================
# TIER ANALYSIS
# =============================================================================

def analyze_tiers(df: pd.DataFrame, champion: dict):
    """Analyze tier performance with champion config."""
    X = df[FEATURES].fillna(0).astype(np.float32).values
    y = (df['outcome'] == 'APPROVAL').astype(np.float32).values
    
    weights = np.array(champion['weights'])
    bias = champion['bias']
    
    logits = bias + X @ weights
    probs = 1 / (1 + np.exp(-np.clip(logits, -500, 500)))
    
    df = df.copy()
    df['prob'] = probs
    
    print("\n" + "=" * 60)
    print("TIER ANALYSIS")
    print("=" * 60)
    
    # Find good thresholds
    for t1, t2, t3 in [(0.92, 0.88, 0.75), (0.90, 0.85, 0.70), (0.88, 0.82, 0.68)]:
        tier1 = df[df['prob'] >= t1]
        tier2 = df[(df['prob'] >= t2) & (df['prob'] < t1)]
        tier3 = df[(df['prob'] >= t3) & (df['prob'] < t2)]
        tier4 = df[df['prob'] < t3]
        
        t4_crl = (tier4['outcome'] == 'CRL').mean() * 100 if len(tier4) > 0 else 0
        
        if len(tier4) >= 20 and t4_crl >= 25:
            print(f"\nThresholds: TIER1≥{t1}, TIER2≥{t2}, TIER3≥{t3}")
            print(f"\n{'Tier':<8} | {'N':>6} | {'Approval%':>10} | {'CRL%':>8}")
            print("-" * 45)
            for name, tier in [('TIER_1', tier1), ('TIER_2', tier2), ('TIER_3', tier3), ('TIER_4', tier4)]:
                if len(tier) > 0:
                    approval = (tier['outcome'] == 'APPROVAL').mean() * 100
                    print(f"{name:<8} | {len(tier):>6} | {approval:>9.1f}% | {100-approval:>7.1f}%")
            break
    
    # CRL detection analysis
    print(f"\n--- CRL Detection Performance ---")
    total_crl = (df['outcome'] == 'CRL').sum()
    for threshold in [0.80, 0.75, 0.70, 0.65]:
        risky = df[df['prob'] < threshold]
        if len(risky) >= 10:
            crl_caught = (risky['outcome'] == 'CRL').sum()
            crl_rate = (risky['outcome'] == 'CRL').mean() * 100
            recall = crl_caught / total_crl * 100
            print(f"  prob < {threshold}: {len(risky):4} flagged, {crl_rate:.1f}% CRL, catches {crl_caught}/{total_crl} ({recall:.0f}%)")
    
    # Weight interpretation
    print(f"\n--- Feature Weights ---")
    for feat, w in sorted(zip(FEATURES, champion['weights']), key=lambda x: abs(x[1]), reverse=True):
        direction = "↑ APPROVAL" if w > 0 else "↓ CRL RISK"
        print(f"  {feat:<25}: {w:+.4f} ({direction})")

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ODIN v6 GPU Optimizer")
    parser.add_argument("--csv", default="ODIN_v5_T1_COMPLIANT.csv", help="Path to CSV (default: ODIN_v5_T1_COMPLIANT.csv)")
    parser.add_argument("--max-configs", type=int, default=1_000_000_000, help="Max configurations to test")
    parser.add_argument("--stall-limit", type=int, default=100_000_000, help="Stop after N configs without improvement")
    parser.add_argument("--sigma", type=float, default=0.8, help="Initial sigma for perturbations")
    parser.add_argument("--output-dir", default=".", help="Output directory for results")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing champion")
    args = parser.parse_args()
    
    # Load data
    if not os.path.exists(args.csv):
        # Try common locations
        alternatives = [
            "ODIN_v5_T1_COMPLIANT.csv",
            "./ODIN_v5_T1_COMPLIANT.csv",
            "../ODIN_v5_T1_COMPLIANT.csv",
        ]
        found = None
        for alt in alternatives:
            if os.path.exists(alt):
                found = alt
                break
        
        if found:
            args.csv = found
            print(f"Found CSV at: {found}")
        else:
            print(f"ERROR: CSV not found: {args.csv}")
            print(f"Please ensure ODIN_v5_T1_COMPLIANT.csv is in the current directory")
            print(f"Or specify path with: python odin_v6_gpu_optimizer.py --csv path/to/file.csv")
            sys.exit(1)
    
    print(f"Loading {args.csv}...")
    df = pd.read_csv(args.csv)
    print(f"  Loaded {len(df)} records")
    
    # Engineer features
    print("Engineering features...")
    df = engineer_features(df)
    
    # Verify features exist
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"ERROR: Missing features: {missing}")
        sys.exit(1)
    
    # Prepare data
    X = df[FEATURES].fillna(0).astype(np.float32).values
    y = (df['outcome'] == 'APPROVAL').astype(np.float32).values
    
    print(f"  Features: {FEATURES}")
    print(f"  X shape: {X.shape}")
    print(f"  Approval rate: {y.mean()*100:.1f}%")
    
    if args.analyze_only:
        champion_path = Path(args.output_dir) / "champion_config.json"
        if champion_path.exists():
            with open(champion_path) as f:
                champion = json.load(f)
            analyze_tiers(df, champion)
        else:
            print(f"No champion found at {champion_path}")
        return
    
    # Run optimization
    champion = run_optimization(
        X, y,
        max_configs=args.max_configs,
        stall_limit=args.stall_limit,
        sigma_init=args.sigma,
        output_dir=args.output_dir,
        csv_path=args.csv
    )
    
    # Analyze results
    analyze_tiers(df, champion)
    
    print(f"\n{'='*60}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Best Brier: {champion['best_brier']:.6f}")
    print(f"  Improvement: {champion['improvement_pct']:.2f}%")
    print(f"  Configs tested: {champion['configs_done']:,}")
    print(f"  Runtime: {champion['elapsed_seconds']:.1f}s")
    print(f"\n  Results saved to: {args.output_dir}/")

if __name__ == "__main__":
    main()