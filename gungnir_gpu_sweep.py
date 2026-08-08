#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR GPU HYPERPARAMETER SWEEP v1.0                                     ║
║  Massively parallel model training on CUDA                                 ║
║                                                                            ║
║  Trains THOUSANDS of logistic regression models simultaneously on GPU.     ║
║  Each combo = different (lr, l2, base_logit_init, weight_init_strategy).   ║
║  Then evaluates all trained models × tier_boundary combos.                 ║
║                                                                            ║
║  Requires: PyTorch with CUDA  (pip install torch)                          ║
║  Target:   NVIDIA RTX 4070 (12GB VRAM) — fits 10K+ combos easily          ║
║                                                                            ║
║  Usage:                                                                    ║
║    python gungnir_gpu_sweep.py                     Full sweep              ║
║    python gungnir_gpu_sweep.py --combos 5000       Custom combo count      ║
║    python gungnir_gpu_sweep.py --epochs 8000       More epochs             ║
║    python gungnir_gpu_sweep.py --best 20           Show top 20 configs     ║
║    python gungnir_gpu_sweep.py --export best.json  Export best weights     ║
║                                                                            ║
║  Built for pdufa.bio — Feb 2026                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import itertools
import json
import math
import os
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

try:
    import torch
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("ERROR: PyTorch not installed. Run: pip install torch --index-url https://download.pytorch.org/whl/cu121")
    sys.exit(1)

# Import from Gungnir engine for data loading and feature extraction
from gungnir_honing_engine import (
    load_phase_events,
    precompute_features,
    FEATURE_NAMES,
    INITIAL_WEIGHTS,
    sigmoid,
)

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════════════
#  HYPERPARAMETER GRID
# ═══════════════════════════════════════════════════════════════

# Training hyperparameters (these affect gradient descent)
LR_GRID = [0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]
L2_GRID = [0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05]

# Base logit initialization (sets prior positive rate)
BASE_LOGIT_GRID = [-0.5, -0.3, -0.1, 0.0, 0.12, 0.25, 0.4, 0.6, 0.8, 1.0]

# Weight initialization strategies
INIT_STRATEGIES = {
    "honed":     "Start from current honed weights",
    "initial":   "Start from Gungnir v4.0 initial weights",
    "zero":      "Start from zero (tabula rasa)",
    "half":      "Start from 50% of honed weights",
    "negative":  "Start from negated honed weights (adversarial)",
}

# Tier boundary sweep (evaluated AFTER training — no GPU cost)
TIER_1_GRID = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
TIER_4_GRID = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]


# ═══════════════════════════════════════════════════════════════
#  DATA PREPARATION
# ═══════════════════════════════════════════════════════════════

def prepare_data(device: torch.device) -> tuple:
    """
    Load Phase events, extract features, build GPU tensors.
    Returns: X (N x F), y (N,), feature_names
    """
    print("  Loading Phase readout data...")
    events = load_phase_events(verbose=True)
    events = precompute_features(events, verbose=True)

    resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
    print(f"  Resolved events: {len(resolved)}")

    N = len(resolved)
    F = len(FEATURE_NAMES)

    # Build feature matrix
    X_np = []
    y_np = []
    for e in resolved:
        row = [float(e["features"].get(fname, 0.0)) for fname in FEATURE_NAMES]
        X_np.append(row)
        y_np.append(1.0 if e["outcome"] == "POSITIVE" else 0.0)

    X = torch.tensor(X_np, dtype=torch.float32, device=device)  # (N, F)
    y = torch.tensor(y_np, dtype=torch.float32, device=device)  # (N,)

    print(f"  Feature matrix: {X.shape[0]} x {X.shape[1]} on {device}")
    print(f"  Positive rate: {y.mean().item():.3f}")

    return X, y, resolved


# ═══════════════════════════════════════════════════════════════
#  WEIGHT INITIALIZATION
# ═══════════════════════════════════════════════════════════════

def load_honed_weights() -> dict:
    """Try to load honed weights from known locations."""
    candidates = [
        "gungnir_honed_weights.json",
        os.path.join(str(Path.home()), "gungnir_data", "model_weights.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "gungnir_honed_weights.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r") as f:
                return json.load(f)
    return None


def build_init_weights(strategy: str, base_logit: float,
                       honed: dict = None) -> list:
    """
    Build a weight vector [base_logit, w1, w2, ..., wF] for a given strategy.
    """
    F = len(FEATURE_NAMES)

    if strategy == "honed" and honed:
        feats = honed.get("features", {})
        w = [feats.get(fname, 0.0) for fname in FEATURE_NAMES]
    elif strategy == "initial":
        feats = INITIAL_WEIGHTS["features"]
        w = [feats.get(fname, 0.0) for fname in FEATURE_NAMES]
    elif strategy == "zero":
        w = [0.0] * F
    elif strategy == "half" and honed:
        feats = honed.get("features", {})
        w = [feats.get(fname, 0.0) * 0.5 for fname in FEATURE_NAMES]
    elif strategy == "negative" and honed:
        feats = honed.get("features", {})
        w = [-feats.get(fname, 0.0) for fname in FEATURE_NAMES]
    else:
        w = [0.0] * F

    return [base_logit] + w


# ═══════════════════════════════════════════════════════════════
#  GPU BATCH TRAINER
# ═══════════════════════════════════════════════════════════════

class GPUBatchTrainer:
    """
    Trains K logistic regression models simultaneously on GPU.

    All K models share the same data (X, y) but have different:
    - Learning rates
    - L2 penalties
    - Initial weights

    The key operation per epoch:
        logits = X @ W[1:, :] + W[0, :]      # (N, K)  — all models at once
        P = sigmoid(logits)                    # (N, K)
        error = P - Y                          # (N, K)  Y is broadcast
        grad_w = X.T @ (error * P * (1-P))    # (F, K)  — all gradients at once
        grad_b = sum(error * P * (1-P))        # (K,)
        W -= lr * grad + l2 * W               # per-model lr and l2

    Memory: ~4600 events × 35 features × 10K models = ~6.4 GB → fits on 4070
    """

    def __init__(self, X: torch.Tensor, y: torch.Tensor,
                 max_epochs: int = 5000, patience: int = 300,
                 convergence: float = 1e-7, log_interval: int = 500):
        self.X = X                  # (N, F)
        self.y = y                  # (N,)
        self.N, self.F = X.shape
        self.max_epochs = max_epochs
        self.patience = patience
        self.convergence = convergence
        self.log_interval = log_interval
        self.device = X.device

    def train(self, configs: list) -> list:
        """
        Train all configs in parallel.

        configs: list of dicts with keys:
            - lr: float
            - l2: float
            - init_weights: list of floats [base, w1, ..., wF]
            - meta: dict (passed through to results)

        Returns: list of result dicts with best weights and metrics.
        """
        K = len(configs)
        F = self.F
        N = self.N

        print(f"\n  ┌─ GPU BATCH TRAINING ──────────────────────────┐")
        print(f"  │  Models:     {K:>8,d}                            │")
        print(f"  │  Events:     {N:>8,d}                            │")
        print(f"  │  Features:   {F:>8,d}                            │")
        print(f"  │  Max epochs: {self.max_epochs:>8,d}                            │")
        print(f"  │  Patience:   {self.patience:>8,d}                            │")
        print(f"  │  Device:     {str(self.device):>30s}  │")
        vram = torch.cuda.memory_allocated(self.device) / 1e9 if self.device.type == 'cuda' else 0
        print(f"  │  VRAM used:  {vram:>7.2f} GB                        │")
        print(f"  └────────────────────────────────────────────────┘")

        # Build weight matrix W: shape (F+1, K) — row 0 is bias
        W_init = torch.zeros(F + 1, K, device=self.device)
        lr_vec = torch.zeros(K, device=self.device)
        l2_vec = torch.zeros(K, device=self.device)

        for i, cfg in enumerate(configs):
            w = cfg["init_weights"]
            W_init[:, i] = torch.tensor(w, dtype=torch.float32, device=self.device)
            lr_vec[i] = cfg["lr"]
            l2_vec[i] = cfg["l2"]

        W = W_init.clone()  # (F+1, K)

        # Best tracking per model
        best_brier = torch.full((K,), float('inf'), device=self.device)
        best_W = W.clone()
        no_improve = torch.zeros(K, dtype=torch.int32, device=self.device)
        active = torch.ones(K, dtype=torch.bool, device=self.device)  # early stopping mask

        # Expand y for broadcasting: (N, 1)
        y_col = self.y.unsqueeze(1)  # (N, 1)

        t0 = time.time()
        final_epoch = 0

        for epoch in range(self.max_epochs):
            final_epoch = epoch

            # Forward pass — ALL models at once
            # logits: (N, K) = (N, F) @ (F, K) + (1, K)
            logits = self.X @ W[1:, :] + W[0, :].unsqueeze(0)

            # Sigmoid
            P = torch.sigmoid(logits)  # (N, K)

            # Brier score per model
            brier_per = ((P - y_col) ** 2).mean(dim=0)  # (K,)

            # Gradient: dBrier/dw = 2/N * sum[ (p-y)*p*(1-p)*x ]
            error = P - y_col                        # (N, K)
            deriv = P * (1.0 - P)                    # (N, K)
            grad_factor = 2.0 * error * deriv / N    # (N, K)

            # Gradient for weights: (F, K) = (F, N) @ (N, K)
            grad_w = self.X.t() @ grad_factor        # (F, K)

            # Gradient for bias: (K,)
            grad_b = grad_factor.sum(dim=0)          # (K,)

            # L2 regularization on feature weights (not bias)
            grad_w += l2_vec.unsqueeze(0) * W[1:, :]

            # Update — only active models
            lr_active = lr_vec * active.float()
            W[0, :] -= lr_active * grad_b
            W[1:, :] -= lr_active.unsqueeze(0) * grad_w

            # Track best per model
            improved = (brier_per < best_brier - self.convergence) & active
            best_brier = torch.where(improved, brier_per, best_brier)
            best_W[:, improved] = W[:, improved]
            no_improve = torch.where(improved, torch.zeros_like(no_improve), no_improve + 1)

            # Early stopping per model
            active = active & (no_improve < self.patience)

            # All converged?
            if not active.any():
                break

            # Progress log
            if epoch % self.log_interval == 0:
                n_active = active.sum().item()
                min_b = best_brier[best_brier < float('inf')].min().item()
                mean_b = best_brier[best_brier < float('inf')].mean().item()
                elapsed = time.time() - t0
                eps = (epoch + 1) / elapsed if elapsed > 0 else 0

                if self.device.type == 'cuda':
                    vram = torch.cuda.memory_allocated(self.device) / 1e9
                    print(f"  Epoch {epoch:>5d} | Active: {n_active:>5d}/{K} | "
                          f"Best Brier: {min_b:.6f} | Mean: {mean_b:.6f} | "
                          f"{eps:.0f} ep/s | VRAM: {vram:.1f}GB")
                else:
                    print(f"  Epoch {epoch:>5d} | Active: {n_active:>5d}/{K} | "
                          f"Best Brier: {min_b:.6f} | Mean: {mean_b:.6f} | "
                          f"{eps:.0f} ep/s")

        elapsed = time.time() - t0
        print(f"\n  Training complete: {final_epoch+1} epochs in {elapsed:.1f}s "
              f"({(final_epoch+1)/elapsed:.0f} ep/s)")

        # ── Compute AUC for all models ──
        # Use best weights for final scoring
        print("  Computing AUC for all models...")
        logits_final = self.X @ best_W[1:, :] + best_W[0, :].unsqueeze(0)
        P_final = torch.sigmoid(logits_final)  # (N, K)

        # AUC per model (vectorized concordance)
        auc_scores = self._batch_auc(P_final, self.y)  # (K,)

        # Accuracy per model
        acc_scores = ((P_final >= 0.5).float() == y_col).float().mean(dim=0)  # (K,)

        # Package results
        results = []
        best_W_cpu = best_W.cpu().numpy()
        best_brier_cpu = best_brier.cpu().numpy()
        auc_cpu = auc_scores.cpu().numpy()
        acc_cpu = acc_scores.cpu().numpy()

        for i, cfg in enumerate(configs):
            w_vec = best_W_cpu[:, i].tolist()
            weight_dict = {
                "base_logit": round(w_vec[0], 6),
                "features": {fname: round(w_vec[j + 1], 6)
                             for j, fname in enumerate(FEATURE_NAMES)},
            }
            results.append({
                "config_id": i,
                "lr": cfg["lr"],
                "l2": cfg["l2"],
                "init_strategy": cfg["meta"].get("init_strategy", "?"),
                "base_logit_init": cfg["meta"].get("base_logit_init", 0),
                "brier": round(float(best_brier_cpu[i]), 6),
                "auc": round(float(auc_cpu[i]), 6),
                "accuracy": round(float(acc_cpu[i]), 6),
                "weights": weight_dict,
            })

        return results

    def _batch_auc(self, P: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """
        Compute AUC for K models in parallel.
        Uses the sampling-based approximation for speed:
        Sample random pos/neg pairs and estimate concordance.
        """
        K = P.shape[1]
        pos_mask = (y == 1.0)
        neg_mask = (y == 0.0)
        n_pos = pos_mask.sum().item()
        n_neg = neg_mask.sum().item()

        if n_pos == 0 or n_neg == 0:
            return torch.full((K,), 0.5, device=P.device)

        # For exact AUC with reasonable sizes
        if n_pos * n_neg <= 5_000_000:
            # Exact: compare all pairs
            P_pos = P[pos_mask, :]  # (n_pos, K)
            P_neg = P[neg_mask, :]  # (n_neg, K)

            # Concordance: for each pair, does p_pos > p_neg?
            # (n_pos, 1, K) > (1, n_neg, K) → (n_pos, n_neg, K)
            concordant = (P_pos.unsqueeze(1) > P_neg.unsqueeze(0)).float()
            tied = (P_pos.unsqueeze(1) == P_neg.unsqueeze(0)).float()
            auc = (concordant.sum(dim=(0, 1)) + 0.5 * tied.sum(dim=(0, 1))) / (n_pos * n_neg)
            return auc  # (K,)
        else:
            # Sampling approximation for very large datasets
            n_samples = 100_000
            pos_idx = torch.where(pos_mask)[0]
            neg_idx = torch.where(neg_mask)[0]
            rand_pos = pos_idx[torch.randint(n_pos, (n_samples,), device=P.device)]
            rand_neg = neg_idx[torch.randint(n_neg, (n_samples,), device=P.device)]
            P_p = P[rand_pos, :]  # (n_samples, K)
            P_n = P[rand_neg, :]  # (n_samples, K)
            auc = (P_p > P_n).float().mean(dim=0) + 0.5 * (P_p == P_n).float().mean(dim=0)
            return auc  # (K,)


# ═══════════════════════════════════════════════════════════════
#  CONFIG GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_configs(honed_weights: dict = None,
                     max_combos: int = None) -> list:
    """
    Generate the full hyperparameter grid.

    Default grid: 10 lr × 10 l2 × 10 base_logit × 5 init = 5,000 combos
    """
    configs = []

    strategies = list(INIT_STRATEGIES.keys())
    if honed_weights is None:
        strategies = [s for s in strategies if s not in ("honed", "half", "negative")]

    for lr, l2, base_logit, strat in itertools.product(
        LR_GRID, L2_GRID, BASE_LOGIT_GRID, strategies
    ):
        init_w = build_init_weights(strat, base_logit, honed_weights)
        configs.append({
            "lr": lr,
            "l2": l2,
            "init_weights": init_w,
            "meta": {
                "init_strategy": strat,
                "base_logit_init": base_logit,
            },
        })

    print(f"  Generated {len(configs)} training configs")
    print(f"    LR: {len(LR_GRID)} values [{LR_GRID[0]}..{LR_GRID[-1]}]")
    print(f"    L2: {len(L2_GRID)} values [{L2_GRID[0]}..{L2_GRID[-1]}]")
    print(f"    Base logit: {len(BASE_LOGIT_GRID)} values [{BASE_LOGIT_GRID[0]}..{BASE_LOGIT_GRID[-1]}]")
    print(f"    Init strategies: {len(strategies)} [{', '.join(strategies)}]")

    if max_combos and len(configs) > max_combos:
        import random
        random.seed(42)
        configs = random.sample(configs, max_combos)
        print(f"  Sampled down to {len(configs)} combos")

    return configs


# ═══════════════════════════════════════════════════════════════
#  TIER BOUNDARY SWEEP (post-training, CPU — fast)
# ═══════════════════════════════════════════════════════════════

def sweep_tier_boundaries(results: list, X: torch.Tensor,
                          y: torch.Tensor, top_n: int = 50) -> list:
    """
    For the top N training results, sweep all tier boundary combos.
    This is done on CPU since it's just threshold comparisons.
    """
    print(f"\n  Sweeping tier boundaries on top {top_n} models...")
    print(f"    T1 boundaries: {TIER_1_GRID}")
    print(f"    T4 boundaries: {TIER_4_GRID}")
    print(f"    Combos per model: {len(TIER_1_GRID) * len(TIER_4_GRID)}")

    # Sort by AUC desc, take top N
    sorted_results = sorted(results, key=lambda r: r["auc"], reverse=True)
    top_results = sorted_results[:top_n]

    y_np = y.cpu().numpy()

    all_configs = []

    for rank, res in enumerate(top_results):
        # Reconstruct predictions
        w = res["weights"]
        base = w["base_logit"]
        feat_w = [w["features"].get(fname, 0.0) for fname in FEATURE_NAMES]
        W_vec = torch.tensor([base] + feat_w, dtype=torch.float32, device=X.device)

        logits = X @ W_vec[1:] + W_vec[0]
        preds = torch.sigmoid(logits).cpu().numpy()

        for t1_bound, t4_bound in itertools.product(TIER_1_GRID, TIER_4_GRID):
            if t4_bound >= t1_bound:
                continue  # Invalid: T4 boundary must be below T1

            # Compute tier stats
            tiers = {"TIER_1": [], "TIER_2": [], "TIER_3": [], "TIER_4": []}
            for p, a in zip(preds, y_np):
                tier = (
                    "TIER_1" if p >= t1_bound else
                    "TIER_2" if p >= 0.50 else
                    "TIER_3" if p >= t4_bound else
                    "TIER_4"
                )
                tiers[tier].append(a)

            tier_stats = {}
            for t, vals in tiers.items():
                if vals:
                    tier_stats[t] = {
                        "n": len(vals),
                        "pos_rate": round(sum(vals) / len(vals), 4),
                    }
                else:
                    tier_stats[t] = {"n": 0, "pos_rate": 0.0}

            # Score this config: want high T1 pos rate + low T4 pos rate + enough N
            t1_n = tier_stats["TIER_1"]["n"]
            t1_pos = tier_stats["TIER_1"]["pos_rate"]
            t4_n = tier_stats["TIER_4"]["n"]
            t4_pos = tier_stats["TIER_4"]["pos_rate"]

            # Composite score:
            # High T1 precision, low T4 leak, decent volume
            if t1_n < 20 or t4_n < 20:
                tier_score = 0.0  # Not enough events
            else:
                tier_score = (
                    t1_pos * 0.4 +                         # T1 precision
                    (1.0 - t4_pos) * 0.3 +                 # T4 negative detection
                    min(t1_n / 500, 1.0) * 0.15 +          # T1 volume
                    min(t4_n / 500, 1.0) * 0.15             # T4 volume
                )

            all_configs.append({
                "training_rank": rank + 1,
                "config_id": res["config_id"],
                "lr": res["lr"],
                "l2": res["l2"],
                "init_strategy": res["init_strategy"],
                "base_logit_init": res["base_logit_init"],
                "brier": res["brier"],
                "auc": res["auc"],
                "accuracy": res["accuracy"],
                "tier_1_boundary": t1_bound,
                "tier_4_boundary": t4_bound,
                "tiers": tier_stats,
                "tier_score": round(tier_score, 6),
                "weights": res["weights"],
            })

    # Sort by composite: AUC × 0.5 + tier_score × 0.5
    for c in all_configs:
        c["composite_score"] = round(c["auc"] * 0.5 + c["tier_score"] * 0.5, 6)

    all_configs.sort(key=lambda c: c["composite_score"], reverse=True)

    print(f"  Total tier configs evaluated: {len(all_configs)}")

    return all_configs


# ═══════════════════════════════════════════════════════════════
#  WALK-FORWARD VALIDATION ON GPU
# ═══════════════════════════════════════════════════════════════

def gpu_walkforward(results: list, events: list, device: torch.device,
                    top_n: int = 10, train_ratio: float = 0.70) -> list:
    """
    Run walk-forward validation for top N configs on GPU.
    Trains on first 70%, tests on last 30%.
    """
    print(f"\n  Walk-forward validation on top {top_n} configs...")

    resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
    resolved_sorted = sorted(resolved, key=lambda e: e.get("catalyst_date", ""))
    split = int(len(resolved_sorted) * train_ratio)

    train_events = resolved_sorted[:split]
    test_events = resolved_sorted[split:]

    # Build tensors
    def build_tensors(evts):
        X_list = [[float(e["features"].get(f, 0.0)) for f in FEATURE_NAMES] for e in evts]
        y_list = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in evts]
        return (torch.tensor(X_list, dtype=torch.float32, device=device),
                torch.tensor(y_list, dtype=torch.float32, device=device))

    X_train, y_train = build_tensors(train_events)
    X_test, y_test = build_tensors(test_events)

    sorted_results = sorted(results, key=lambda r: r.get("composite_score", r.get("auc", 0)), reverse=True)
    top_results = sorted_results[:top_n]

    # Re-train each on train set, evaluate on test set
    validated = []
    trainer = GPUBatchTrainer(X_train, y_train, max_epochs=5000,
                              patience=300, log_interval=2000)

    configs = []
    for r in top_results:
        configs.append({
            "lr": r["lr"],
            "l2": r["l2"],
            "init_weights": [r["weights"]["base_logit"]] +
                            [r["weights"]["features"].get(f, 0.0) for f in FEATURE_NAMES],
            "meta": {"init_strategy": r.get("init_strategy", "?"),
                     "base_logit_init": r.get("base_logit_init", 0)},
        })

    train_results = trainer.train(configs)

    # Evaluate on test set
    for i, (tr_res, orig) in enumerate(zip(train_results, top_results)):
        w = tr_res["weights"]
        W_vec = torch.tensor(
            [w["base_logit"]] + [w["features"].get(f, 0.0) for f in FEATURE_NAMES],
            dtype=torch.float32, device=device
        )
        test_logits = X_test @ W_vec[1:] + W_vec[0]
        test_preds = torch.sigmoid(test_logits)

        test_brier = ((test_preds - y_test) ** 2).mean().item()
        test_acc = ((test_preds >= 0.5).float() == y_test).float().mean().item()

        # Test AUC
        pos_p = test_preds[y_test == 1.0]
        neg_p = test_preds[y_test == 0.0]
        if len(pos_p) > 0 and len(neg_p) > 0:
            conc = (pos_p.unsqueeze(1) > neg_p.unsqueeze(0)).float()
            tied = (pos_p.unsqueeze(1) == neg_p.unsqueeze(0)).float()
            test_auc = ((conc.sum() + 0.5 * tied.sum()) / (len(pos_p) * len(neg_p))).item()
        else:
            test_auc = 0.5

        validated.append({
            "rank": i + 1,
            "lr": tr_res["lr"],
            "l2": tr_res["l2"],
            "init_strategy": tr_res["init_strategy"],
            "train_brier": tr_res["brier"],
            "train_auc": tr_res["auc"],
            "test_brier": round(test_brier, 6),
            "test_auc": round(test_auc, 6),
            "test_accuracy": round(test_acc, 6),
            "test_n": len(test_events),
            "train_n": len(train_events),
            "overfit_delta": round(tr_res["auc"] - test_auc, 4),
            "tier_1_boundary": orig.get("tier_1_boundary", 0.70),
            "tier_4_boundary": orig.get("tier_4_boundary", 0.20),
            "weights": tr_res["weights"],
        })

    validated.sort(key=lambda v: v["test_auc"], reverse=True)
    return validated


# ═══════════════════════════════════════════════════════════════
#  RESULTS DISPLAY
# ═══════════════════════════════════════════════════════════════

def print_top_configs(configs: list, n: int = 20, title: str = "TOP CONFIGS"):
    """Pretty-print top N configurations."""
    print(f"\n  {'═'*90}")
    print(f"  {title}")
    print(f"  {'═'*90}")
    print(f"  {'#':>3s} │ {'AUC':>6s} │ {'Brier':>6s} │ {'Acc':>5s} │ "
          f"{'LR':>6s} │ {'L2':>6s} │ {'Init':>8s} │ "
          f"{'T1_B':>4s} │ {'T1%':>5s} │ {'T1_n':>4s} │ {'T4%':>5s} │ {'T4_n':>4s}")
    print(f"  {'─'*3}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*5}─┼─{'─'*6}─┼─"
          f"{'─'*6}─┼─{'─'*8}─┼─{'─'*4}─┼─{'─'*5}─┼─{'─'*4}─┼─{'─'*5}─┼─{'─'*4}")

    for i, c in enumerate(configs[:n]):
        t1 = c.get("tiers", {}).get("TIER_1", {})
        t4 = c.get("tiers", {}).get("TIER_4", {})
        print(f"  {i+1:>3d} │ {c['auc']:>.4f} │ {c['brier']:>.4f} │ "
              f"{c.get('accuracy', 0):>.3f} │ {c['lr']:>6.4f} │ {c['l2']:>6.4f} │ "
              f"{c.get('init_strategy', '?'):>8s} │ "
              f"{c.get('tier_1_boundary', 0.7):>.2f} │ "
              f"{t1.get('pos_rate', 0)*100:>4.1f}% │ {t1.get('n', 0):>4d} │ "
              f"{t4.get('pos_rate', 0)*100:>4.1f}% │ {t4.get('n', 0):>4d}")


def print_walkforward(validated: list):
    """Pretty-print walk-forward results."""
    print(f"\n  {'═'*85}")
    print(f"  WALK-FORWARD VALIDATION (Train/Test)")
    print(f"  {'═'*85}")
    print(f"  {'#':>3s} │ {'Test AUC':>8s} │ {'Test Bri':>8s} │ "
          f"{'Trn AUC':>7s} │ {'Overfit':>7s} │ {'LR':>6s} │ {'L2':>6s} │ {'Init':>8s}")
    print(f"  {'─'*3}─┼─{'─'*8}─┼─{'─'*8}─┼─{'─'*7}─┼─{'─'*7}─┼─"
          f"{'─'*6}─┼─{'─'*6}─┼─{'─'*8}")

    for v in validated:
        flag = " ⚠️" if v["overfit_delta"] > 0.05 else ""
        print(f"  {v['rank']:>3d} │ {v['test_auc']:>.4f}   │ {v['test_brier']:>.4f}   │ "
              f"{v['train_auc']:>.4f}  │ {v['overfit_delta']:>+.4f}  │ "
              f"{v['lr']:>6.4f} │ {v['l2']:>6.4f} │ {v.get('init_strategy', '?'):>8s}{flag}")


# ═══════════════════════════════════════════════════════════════
#  EXPORT
# ═══════════════════════════════════════════════════════════════

def export_best(configs: list, validated: list, filepath: str):
    """Export the best config + walk-forward champion to JSON."""
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": f"gungnir_gpu_sweep v{__version__}",
        "total_configs_trained": len(configs) if configs else 0,
    }

    if configs:
        best = configs[0]
        output["best_overall"] = {
            "auc": best["auc"],
            "brier": best["brier"],
            "accuracy": best.get("accuracy", 0),
            "lr": best["lr"],
            "l2": best["l2"],
            "init_strategy": best.get("init_strategy"),
            "tier_1_boundary": best.get("tier_1_boundary", 0.70),
            "tier_4_boundary": best.get("tier_4_boundary", 0.20),
            "tiers": best.get("tiers", {}),
            "weights": best["weights"],
        }

    if validated:
        champ = validated[0]
        output["walkforward_champion"] = {
            "test_auc": champ["test_auc"],
            "test_brier": champ["test_brier"],
            "train_auc": champ["train_auc"],
            "overfit_delta": champ["overfit_delta"],
            "lr": champ["lr"],
            "l2": champ["l2"],
            "init_strategy": champ.get("init_strategy"),
            "tier_1_boundary": champ.get("tier_1_boundary", 0.70),
            "tier_4_boundary": champ.get("tier_4_boundary", 0.20),
            "weights": champ["weights"],
        }

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Exported to {filepath}")

    return output


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Gungnir GPU Hyperparameter Sweep v1.0")
    parser.add_argument("--combos", type=int, default=None,
                        help="Max training combos (default: full grid ~5000)")
    parser.add_argument("--epochs", type=int, default=5000,
                        help="Max epochs per model (default: 5000)")
    parser.add_argument("--patience", type=int, default=300,
                        help="Early stopping patience (default: 300)")
    parser.add_argument("--best", type=int, default=20,
                        help="Show top N configs (default: 20)")
    parser.add_argument("--validate", type=int, default=20,
                        help="Walk-forward validate top N (default: 20)")
    parser.add_argument("--export", default=None,
                        help="Export best config to JSON file")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU (skip CUDA)")
    parser.add_argument("--phase-csv", default=None, help="Phase backtest CSV")
    parser.add_argument("--hist-csv", default=None, help="Historical readouts CSV")
    args = parser.parse_args()

    print(f"\n{'═'*72}")
    print(f"  ⚔️  GUNGNIR GPU HYPERPARAMETER SWEEP v{__version__}")
    print(f"  Massively Parallel Model Training")
    print(f"{'═'*72}")

    # Device selection
    if not args.cpu and torch.cuda.is_available():
        device = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_mem / 1e9
        print(f"  GPU: {gpu_name} ({vram_total:.1f} GB VRAM)")
    else:
        device = torch.device("cpu")
        print(f"  Device: CPU {'(forced)' if args.cpu else '(no CUDA found)'}")

    # Load data
    X, y, events = prepare_data(device)

    # Load honed weights if available
    honed = load_honed_weights()
    if honed:
        print(f"  Loaded honed weights as initialization source")
    else:
        print(f"  No honed weights found — using initial + zero strategies only")

    # Generate configs
    configs = generate_configs(honed, max_combos=args.combos)

    # VRAM estimate
    K = len(configs)
    F = len(FEATURE_NAMES)
    N = X.shape[0]
    vram_est = (N * F + N * K + (F + 1) * K * 3 + K * 4) * 4 / 1e9  # float32
    print(f"  Estimated VRAM: {vram_est:.2f} GB for {K} models")

    if device.type == 'cuda' and vram_est > 10:
        print(f"  ⚠️  May exceed VRAM. Consider --combos {int(K * 8 / vram_est)}")

    # Train!
    t_start = time.time()
    trainer = GPUBatchTrainer(X, y, max_epochs=args.epochs,
                              patience=args.patience, log_interval=500)
    results = trainer.train(configs)

    # Sort by AUC
    results.sort(key=lambda r: r["auc"], reverse=True)

    print(f"\n  {'─'*60}")
    print(f"  Training complete: {len(results)} models in {time.time()-t_start:.1f}s")
    print(f"  Best AUC:   {results[0]['auc']:.6f}")
    print(f"  Best Brier: {min(r['brier'] for r in results):.6f}")

    # Tier boundary sweep
    tier_configs = sweep_tier_boundaries(results, X, y, top_n=50)

    # Display top configs
    print_top_configs(tier_configs, n=args.best)

    # Walk-forward validation
    validated = gpu_walkforward(tier_configs, events, device, top_n=args.validate)
    print_walkforward(validated)

    # Summary
    if validated:
        champ = validated[0]
        print(f"\n  {'═'*60}")
        print(f"  ⚔️  WALK-FORWARD CHAMPION")
        print(f"  {'═'*60}")
        print(f"  Test AUC:       {champ['test_auc']:.4f}")
        print(f"  Test Brier:     {champ['test_brier']:.4f}")
        print(f"  Train AUC:      {champ['train_auc']:.4f}")
        print(f"  Overfit delta:  {champ['overfit_delta']:+.4f}")
        print(f"  LR:             {champ['lr']}")
        print(f"  L2:             {champ['l2']}")
        print(f"  Init:           {champ.get('init_strategy', '?')}")
        print(f"  T1 boundary:    {champ.get('tier_1_boundary', 0.70)}")
        print(f"  T4 boundary:    {champ.get('tier_4_boundary', 0.20)}")
        print(f"  {'═'*60}")

    # Export
    export_path = args.export or os.path.join(
        str(Path.home()), "gungnir_data", "gpu_sweep_best.json"
    )
    export_best(tier_configs, validated, export_path)

    total_time = time.time() - t_start
    print(f"\n  Total sweep time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Models trained: {len(results)}")
    print(f"  Tier configs evaluated: {len(tier_configs)}")
    print(f"  Walk-forward validated: {len(validated)}")


if __name__ == "__main__":
    main()
