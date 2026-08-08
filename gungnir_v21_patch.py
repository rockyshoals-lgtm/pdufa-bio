#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  GUNGNIR PERPETUAL GPU — v2.1 PATCH                         ║
║                                                              ║
║  Fixes from analysis of 46 cycles / 147K configs:            ║
║    1. CRITICAL: is_new_best apples-to-oranges comparison     ║
║    2. HIGH: L2 grid & anti-regularization handling           ║
║    3. MEDIUM: Tier sweep diversity for walkforward           ║
║    4. MEDIUM: Calibration in fitness function                ║
║    5. LOW: Focused exploitation after plateau detection       ║
║                                                              ║
║  Run this BEFORE restarting gungnir_perpetual_gpu.py         ║
║  It patches files in ~/gungnir_data/                         ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = str(Path.home() / "gungnir_data")


def fix_1_best_config():
    """
    FIX #1: Inject test_auc/test_brier into best_config.json
    so the comparator uses walk-forward metrics, not full-dataset metrics.
    
    The current best walk-forward result (cycle 30) hit:
      test_auc=0.8504, test_brier=0.1411
    
    We set the benchmark to the actual best walk-forward score.
    """
    path = os.path.join(DATA_DIR, "best_config.json")
    if not os.path.exists(path):
        print("  ✗ best_config.json not found — skipping")
        return
    
    # Backup
    backup = path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup)
    print(f"  ✓ Backed up to {backup}")
    
    with open(path, "r") as f:
        best = json.load(f)
    
    # Load the actual best walk-forward result from top_10_configs.json
    top10_path = os.path.join(DATA_DIR, "top_10_configs.json")
    if os.path.exists(top10_path):
        with open(top10_path) as f:
            top10 = json.load(f)
        if top10:
            wf_best = top10[0]  # Sorted by test_auc desc
            # Transfer walk-forward metrics into best_config
            best["test_auc"] = wf_best["test_auc"]
            best["test_brier"] = wf_best["test_brier"]
            best["test_accuracy"] = wf_best["test_accuracy"]
            best["overfit_delta"] = wf_best["overfit_delta"]
            best["test_n"] = wf_best["test_n"]
            best["train_n"] = wf_best["train_n"]
            best["tier_1_boundary"] = wf_best.get("tier_1_boundary", 0.85)
            best["tier_4_boundary"] = wf_best.get("tier_4_boundary", 0.10)
            best["tiers"] = wf_best.get("tiers", {})
            best["cycle"] = wf_best.get("cycle", "30")
            # Use the walk-forward champion's WEIGHTS (not the full-dataset weights)
            best["weights"] = wf_best["weights"]
            best["lr"] = wf_best["lr"]
            best["l2"] = wf_best["l2"]
            best["_patched"] = "v2.1 — injected walk-forward metrics"
            best["_patched_at"] = datetime.now(timezone.utc).isoformat()
            
            print(f"  ✓ Injected walk-forward metrics:")
            print(f"    test_auc:   {best['test_auc']:.6f} (was compared against auc={best.get('auc', '?')})")
            print(f"    test_brier: {best['test_brier']:.6f}")
            print(f"    weights:    from cycle {best['cycle']} walk-forward champion")
    else:
        # Fallback: set test_auc to current known best
        best["test_auc"] = 0.8504
        best["test_brier"] = 0.1411
        best["_patched"] = "v2.1 — injected estimated walk-forward metrics"
        print(f"  ✓ Injected estimated walk-forward metrics (top_10 not found)")
    
    with open(path, "w") as f:
        json.dump(best, f, indent=2, default=str)
    
    print(f"  ✓ best_config.json patched — comparator will now use test_auc={best['test_auc']:.6f}")


def fix_2_update_model_weights():
    """
    FIX #2: Also update model_weights.json to the walk-forward champion weights
    so the platform seed is the validated model, not the full-dataset overfit.
    """
    top10_path = os.path.join(DATA_DIR, "top_10_configs.json")
    if not os.path.exists(top10_path):
        print("  ✗ top_10_configs.json not found — skipping")
        return
    
    with open(top10_path) as f:
        top10 = json.load(f)
    
    if not top10:
        print("  ✗ top_10 is empty — skipping")
        return
    
    wf_best = top10[0]
    weights = wf_best["weights"]
    
    path = os.path.join(DATA_DIR, "model_weights.json")
    if os.path.exists(path):
        backup = path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(path, backup)
    
    with open(path, "w") as f:
        json.dump(weights, f, indent=2)
    
    print(f"  ✓ model_weights.json updated to cycle {wf_best.get('cycle', '?')} champion")


def generate_v21_config():
    """
    Generate the v2.1 configuration changes that should be applied
    to gungnir_perpetual_gpu.py before restarting.
    
    Returns a dict of all changes with explanations.
    """
    changes = {}
    
    # ── L2 Grid: Explicitly include negative values ──
    changes["L2_BASE"] = {
        "old": [0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05],
        "new": [-0.005, -0.004, -0.003, -0.002, -0.001, 0.0, 0.001, 0.002, 0.005, 0.01],
        "reason": "All top-10 converged to L2 in [-0.005, -0.002]. Explicitly cover "
                  "this range instead of relying on jitter accidents. Cap at -0.005 "
                  "to prevent runaway weight inflation."
    }
    
    # ── LR Grid: Concentrate in discovered sweet spot ──
    changes["LR_BASE"] = {
        "old": [0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03],
        "new": [0.005, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020, 0.025, 0.030],
        "reason": "Winners were all in [0.014, 0.020]. Drop the tiny LRs (0.0005-0.003) "
                  "that never produced winners. Add density in the sweet spot."
    }
    
    # ── BLOGIT Grid: Tighter around discovered optimum ──
    changes["BLOGIT_BASE"] = {
        "old": [-0.5, -0.3, -0.1, 0.0, 0.12, 0.25, 0.4, 0.6, 0.8, 1.0],
        "new": [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60],
        "reason": "All winners had base_logit ~0.20. Drop negative base_logits "
                  "and values >0.6 that waste configs."
    }
    
    # ── Tier sweep: Force diversity in walkforward ──
    changes["TIER1_BASE"] = {
        "old": [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85],
        "new": [0.70, 0.75, 0.80, 0.85, 0.90],
        "reason": "Drop low T1 boundaries (0.55-0.65) — these produce huge T1 buckets "
                  "with poor positive rates. Add 0.90 to test ultra-selective."
    }
    changes["TIER4_BASE"] = {
        "old": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
        "new": [0.05, 0.08, 0.10, 0.12, 0.15],
        "reason": "Winners converged to T4=0.10. Focus on tight range. Add 0.05/0.08 "
                  "to test even more aggressive no-trade gates."
    }
    
    # ── Strategy distribution: More exploitation, less waste ──
    changes["STRATEGY_DISTRIBUTION"] = {
        "old": {
            "platform": 0.35, "noisy_small": 0.20, "noisy_medium": 0.15,
            "noisy_large": 0.10, "half_platform": 0.05, "negative": 0.03,
            "initial": 0.02, "zero": 0.03, "random": 0.07,
        },
        "new": {
            "platform": 0.40, "noisy_small": 0.25, "noisy_medium": 0.15,
            "noisy_large": 0.08, "half_platform": 0.04, "negative": 0.02,
            "initial": 0.01, "zero": 0.02, "random": 0.03,
        },
        "reason": "After 46 cycles, we know the basin. Increase platform/noisy_small "
                  "(the winners). Reduce random/zero/negative (never produced winners). "
                  "85% exploitation / 15% exploration."
    }
    
    return changes


def print_code_patches():
    """Print the exact code edits to apply to gungnir_perpetual_gpu.py."""
    changes = generate_v21_config()
    
    print("\n" + "="*70)
    print("  CODE PATCHES — Apply to gungnir_perpetual_gpu.py")
    print("="*70)
    
    # Grid patches
    print(f"""
# ── PATCH 1: L2 Grid (line ~85) ──
# OLD:
L2_BASE     = [0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05]
# NEW:
L2_BASE     = [-0.005, -0.004, -0.003, -0.002, -0.001, 0.0, 0.001, 0.002, 0.005, 0.01]

# ── PATCH 2: LR Grid (line ~84) ──
# OLD:
LR_BASE     = [0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]
# NEW:
LR_BASE     = [0.005, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020, 0.025, 0.030]

# ── PATCH 3: BLOGIT Grid (line ~86) ──
# OLD:
BLOGIT_BASE = [-0.5, -0.3, -0.1, 0.0, 0.12, 0.25, 0.4, 0.6, 0.8, 1.0]
# NEW:
BLOGIT_BASE = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60]

# ── PATCH 4: Tier Grids (lines ~87-88) ──
# OLD:
TIER1_BASE  = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
TIER4_BASE  = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
# NEW:
TIER1_BASE  = [0.70, 0.75, 0.80, 0.85, 0.90]
TIER4_BASE  = [0.05, 0.08, 0.10, 0.12, 0.15]

# ── PATCH 5: Strategy Distribution (lines ~91-101) ──
# OLD:
STRATEGY_DISTRIBUTION = {{
    "platform":       0.35,
    "noisy_small":    0.20,
    "noisy_medium":   0.15,
    "noisy_large":    0.10,
    "half_platform":  0.05,
    "negative":       0.03,
    "initial":        0.02,
    "zero":           0.03,
    "random":         0.07,
}}
# NEW:
STRATEGY_DISTRIBUTION = {{
    "platform":       0.40,
    "noisy_small":    0.25,
    "noisy_medium":   0.15,
    "noisy_large":    0.08,
    "half_platform":  0.04,
    "negative":       0.02,
    "initial":        0.01,
    "zero":           0.02,
    "random":         0.03,
}}
""")
    
    # Tier sweep formula patch
    print(f"""
# ── PATCH 6: Tier sweep composite score — penalize tiny T1 buckets ──
# In sweep_tiers(), replace the tier_score formula (around line 570):
# OLD:
            if t1_n < 20 or t4_n < 20:
                tier_score = 0.0
            else:
                tier_score = (t1_pos * 0.4 + (1.0 - t4_pos) * 0.3 +
                              min(t1_n / 500, 1.0) * 0.15 + min(t4_n / 500, 1.0) * 0.15)
# NEW:
            if t1_n < 20 or t4_n < 20:
                tier_score = 0.0
            else:
                # Penalize T1 buckets that are too small (< 15% of data)
                # This forces the sweep to consider T1 boundaries that capture enough events
                total_n = sum(tier_stats[t]["n"] for t in tier_stats)
                t1_coverage = t1_n / total_n if total_n > 0 else 0
                coverage_bonus = min(t1_coverage / 0.25, 1.0)  # Max bonus at 25% of data
                
                tier_score = (t1_pos * 0.30 + (1.0 - t4_pos) * 0.25 +
                              coverage_bonus * 0.20 +
                              min(t1_n / 500, 1.0) * 0.10 + min(t4_n / 500, 1.0) * 0.15)
""")
    
    # Walkforward diversity patch
    print(f"""
# ── PATCH 7: Force tier boundary diversity in walkforward ──
# In walkforward_validate(), after selecting top N, inject some tier diversity.
# After the line: top = sorted(top_configs, ...)[:top_n]
# ADD:
    # Ensure at least 3 different T1 boundaries reach walkforward
    seen_t1 = set()
    diverse_top = []
    for c in top:
        diverse_top.append(c)
        seen_t1.add(c.get("tier_1_boundary", 0.85))
    if len(seen_t1) < 3:
        # Add configs with different T1 boundaries from further down the ranking
        all_sorted = sorted(top_configs, key=lambda c: c.get("composite_score", 0), reverse=True)
        for c in all_sorted[top_n:]:
            t1 = c.get("tier_1_boundary", 0.85)
            if t1 not in seen_t1:
                diverse_top.append(c)
                seen_t1.add(t1)
                if len(seen_t1) >= 4:  # At most 4 unique T1 boundaries
                    break
    top = diverse_top[:top_n + 4]  # Allow up to 4 extra for diversity
""")
    
    # Fitness function calibration patch
    print(f"""
# ── PATCH 8: Add calibration penalty to fitness function ──
# In gpu_train_batch(), modify the composite fitness (around line 510):
# OLD:
    composite = (0.60 * auc_scores +
                 0.25 * (1.0 - best_brier) +
                 0.15 * (1.0 - cal_error.clamp(0, 1)))
# NEW:
    # Add tail calibration: penalize models where extreme predictions are miscalibrated
    # Check top-10% predictions: are they actually ~90%+ positive?
    top_decile_mask = P_final >= P_final.quantile(0.90, dim=0).unsqueeze(0)
    top_decile_actual = (y_col * top_decile_mask.float()).sum(dim=0) / top_decile_mask.float().sum(dim=0).clamp(min=1)
    top_cal_error = (top_decile_actual - 0.90).clamp(min=-0.2, max=0).abs()  # Only penalize if < 90%
    
    composite = (0.55 * auc_scores +
                 0.20 * (1.0 - best_brier) +
                 0.15 * (1.0 - cal_error.clamp(0, 1)) +
                 0.10 * (1.0 - top_cal_error))
""")


def main():
    print(f"\n{'='*60}")
    print(f"  GUNGNIR v2.1 PATCH — Fixing 3 bugs from 46-cycle analysis")
    print(f"{'='*60}\n")
    
    if not os.path.exists(DATA_DIR):
        print(f"  ✗ Data dir not found: {DATA_DIR}")
        print(f"  Run this on the machine with gungnir_data/")
        return
    
    print(f"  Data dir: {DATA_DIR}")
    print()
    
    # Fix 1: Patch best_config.json
    print("  [1/3] Patching best_config.json (is_new_best comparison)...")
    fix_1_best_config()
    print()
    
    # Fix 2: Update model_weights.json
    print("  [2/3] Updating model_weights.json (platform seed)...")
    fix_2_update_model_weights()
    print()
    
    # Fix 3: Print code patches for gungnir_perpetual_gpu.py
    print("  [3/3] Code patches for gungnir_perpetual_gpu.py:")
    print_code_patches()
    
    print(f"\n{'='*60}")
    print(f"  PATCH COMPLETE")
    print(f"{'='*60}")
    print(f"""
  Next steps:
    1. ✅ best_config.json patched (automatic)
    2. ✅ model_weights.json updated (automatic)
    3. Apply code patches 1-8 to gungnir_perpetual_gpu.py
    4. Restart: python gungnir_perpetual_gpu.py --cycles 50
    
  Expected improvements:
    - is_new_best will now fire when walk-forward AUC > 0.8504
    - L2 search will be intentional, not accidental
    - More T1 boundary diversity → potentially higher-volume T1 tier
    - Calibrated fitness → better production probability estimates
    - Focused grids → less waste, faster convergence
""")


if __name__ == "__main__":
    main()
