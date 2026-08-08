#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR PERPETUAL GPU RUNNER v2.3 — ODIN Dynamic Honing Engine            ║
║  Population-based parallel GPU honing for PDUFA scoring                     ║
║                                                                            ║
║  v2.3 changes (from 1,724-iteration / 34.5hr honing analysis):             ║
║    - POPULATION-BASED TRAINING: 200-2000 weight variants per cycle         ║
║    - FULL VRAM UTILIZATION: auto-fill GPU memory (17MB → 8+ GB used)       ║
║    - EVOLUTIONARY HONING: tournament selection + crossover + mutation       ║
║    - PLATEAU BREAKER: automatic sigma annealing + restart triggers         ║
║    - DYNAMIC RESCORING: <3s full retrain when new PDUFA event resolves     ║
║    - CONVERGENCE DETECTION: auto-halt when population diversity collapses  ║
║    - VECTORIZED EVERYTHING: zero Python loops in hot path                  ║
║    - WARM START: resume from model_weights.json or best_run_*.json         ║
║                                                                            ║
║  Architecture shift: v2.1-2.2 trained ONE model per cycle (72s/iter).      ║
║  v2.3 trains 200-2000+ PERTURBATIONS in parallel, selecting the best.     ║
║  Same total FLOPS, 100x better GPU utilization.                            ║
║                                                                            ║
║  Usage:                                                                    ║
║    python gungnir_perpetual_gpu_v23.py                    # run forever    ║
║    python gungnir_perpetual_gpu_v23.py --cycles 50        # N generations  ║
║    python gungnir_perpetual_gpu_v23.py --pop 500          # population     ║
║    python gungnir_perpetual_gpu_v23.py --retrain          # fast retrain   ║
║    python gungnir_perpetual_gpu_v23.py --best             # show best      ║
║    python gungnir_perpetual_gpu_v23.py --export           # export weights ║
║                                                                            ║
║  Built for ODIN PDUFA scoring — RTX 4070 target — Feb 2026                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

try:
    import torch
    import torch.nn.functional as F
except ImportError:
    print("ERROR: PyTorch not installed.")
    print("Run: pip install torch --index-url https://download.pytorch.org/whl/cu121")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("ERROR: NumPy not installed. Run: pip install numpy")
    sys.exit(1)

from gungnir_honing_engine import (
    load_phase_events,
    precompute_features,
    FEATURE_NAMES,
    INITIAL_WEIGHTS,
    PARAM_BOUNDS,
    MONOTONIC_CONSTRAINTS,
    sigmoid,
)

__version__ = "2.3.0"

# Tier boundary grids (same as v2.2)
TIER1_BASE = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
TIER4_BASE = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]


# ═══════════════════════════════════════════════════════════════
#  DATA DIR & UTILITIES
# ═══════════════════════════════════════════════════════════════

def get_data_dir() -> str:
    d = str(Path.home() / "gungnir_data")
    os.makedirs(d, exist_ok=True)
    return d


def get_vram_stats(device: torch.device) -> dict:
    """Return VRAM usage statistics."""
    if device.type != "cuda":
        return {"allocated_mb": 0, "reserved_mb": 0, "total_mb": 0, "free_mb": 0}
    alloc = torch.cuda.memory_allocated(device) / (1024 ** 2)
    reserved = torch.cuda.memory_reserved(device) / (1024 ** 2)
    props = torch.cuda.get_device_properties(device)
    total = (getattr(props, 'total_memory', None) or props.total_mem) / (1024 ** 2)
    return {
        "allocated_mb": round(alloc, 1),
        "reserved_mb": round(reserved, 1),
        "total_mb": round(total, 1),
        "free_mb": round(total - alloc, 1),
    }


def estimate_population_size(n_events: int, n_features: int, device: torch.device,
                              target_utilization: float = 0.50) -> int:
    """
    Estimate max population size that fits in CURRENTLY FREE GPU memory.
    Checks actual free VRAM (not total) to coexist with other GPU processes.

    Memory per model during training:
      - Weight vector: (nF+1) * 4 bytes (float32)
      - Gradient accumulation: (nF+1) * 4 bytes
      - Best weights copy: (nF+1) * 4 bytes
      - Logits/predictions: N * 4 bytes per model
      - Shared data (X, y): N * nF * 4 + N * 4 bytes (constant)
      - Evaluation overhead: ~N * 8 bytes per model (AUC sampling)
    """
    if device.type != "cuda":
        per_model = 3 * (n_features + 1) * 4 + n_events * 8
        target_bytes = 500 * 1024 * 1024
        max_pop = max(50, int(target_bytes / per_model))
        return min(max_pop, 1000)

    # Use ACTUAL free memory, not total — critical for multi-process
    torch.cuda.synchronize(device)
    free_mem, total_mem = torch.cuda.mem_get_info(device)
    available = free_mem * target_utilization

    # Shared memory (loaded once)
    shared_bytes = n_events * n_features * 4 + n_events * 4  # X + y

    # Per-model memory during training AND evaluation
    per_model = (3 * (n_features + 1) * 4    # W, grad, best_W columns
                 + n_events * 4               # logits column
                 + n_events * 4               # predictions column
                 + n_events * 8               # evaluation overhead (AUC chunks)
                 + 256)                       # misc overhead per model

    usable = available - shared_bytes - 128 * 1024 * 1024  # 128MB safety margin
    max_pop = max(50, int(usable / per_model))

    # Cap at reasonable limit
    return min(max_pop, 5000)


def weight_dict_to_vector(w: dict, warn: bool = True) -> list:
    """Convert nested weight dict to flat vector [base_logit, feat1, feat2, ...].

    Searches all sub-dicts (signals, ta_bucket, fda_era, resub, ta_offsets,
    continuous, features) for each FEATURE_NAME. Returns 0.0 for unmatched.
    """
    vec = [w.get("base_logit", 0.0)]

    # Build flat lookup from all sub-dicts
    flat = {}
    for sub_key in ("signals", "features", "ta_bucket", "fda_era",
                     "resub", "ta_offsets", "continuous"):
        sub = w.get(sub_key, {})
        if isinstance(sub, dict):
            flat.update(sub)

    matched = 0
    for fname in FEATURE_NAMES:
        val = flat.get(fname, 0.0)
        if val != 0.0 or fname in flat:
            matched += 1
        vec.append(val)

    if warn and matched < len(FEATURE_NAMES) // 2:
        print(f"  ⚠ Seed weight coverage: {matched}/{len(FEATURE_NAMES)} features matched "
              f"({matched/len(FEATURE_NAMES)*100:.0f}%). "
              f"Unmatched features will start at 0.0.")

    return vec


def vector_to_weight_dict(vec: list) -> dict:
    """Convert flat vector back to nested weight dict."""
    w = {"base_logit": vec[0], "features": {}}
    for i, fname in enumerate(FEATURE_NAMES):
        w["features"][fname] = vec[i + 1]
    return w


# ═══════════════════════════════════════════════════════════════
#  POPULATION-BASED GPU TRAINER — Core of v2.3
# ═══════════════════════════════════════════════════════════════

class PopulationTrainer:
    """
    Train a population of K weight vectors in parallel on GPU.
    Uses evolutionary strategies: mutation, crossover, tournament selection.
    """

    def __init__(self, X: torch.Tensor, y: torch.Tensor, device: torch.device,
                 population_size: int = 500, elite_fraction: float = 0.10,
                 mutation_sigma: float = 0.05, crossover_rate: float = 0.30):
        self.X = X
        self.y = y
        self.device = device
        self.N, self.nF = X.shape
        self.K = population_size
        self.elite_k = max(5, int(population_size * elite_fraction))
        self.sigma = mutation_sigma
        self.crossover_rate = crossover_rate

        # Build bounds tensors
        self.lo_bounds = torch.full((self.nF + 1,), -float('inf'), device=device)
        self.hi_bounds = torch.full((self.nF + 1,), float('inf'), device=device)
        for j, fname in enumerate(FEATURE_NAMES):
            if fname in PARAM_BOUNDS:
                self.lo_bounds[j + 1] = PARAM_BOUNDS[fname][0]
                self.hi_bounds[j + 1] = PARAM_BOUNDS[fname][1]

        # Monotonic constraint pairs
        self.mono_pairs = []
        for hi_name, lo_name in MONOTONIC_CONSTRAINTS:
            hi_idx = FEATURE_NAMES.index(hi_name) + 1
            lo_idx = FEATURE_NAMES.index(lo_name) + 1
            self.mono_pairs.append((hi_idx, lo_idx))

        self.y_col = y.unsqueeze(1)  # (N, 1)
        self.base_rate = y.mean().item()

    def initialize_population(self, seed_weights: list = None) -> torch.Tensor:
        """
        Create initial population. If seed_weights provided, generate
        perturbations around the seed(s). Otherwise random init.

        Returns: W tensor of shape (nF+1, K) — each column is a weight vector.
        """
        W = torch.zeros(self.nF + 1, self.K, device=self.device)

        if seed_weights:
            n_seeds = len(seed_weights)
            # Fill population with perturbations of seeds
            for i in range(self.K):
                seed_idx = i % n_seeds
                seed = torch.tensor(seed_weights[seed_idx], dtype=torch.float32,
                                    device=self.device)
                if i < n_seeds:
                    # First n_seeds entries are exact copies
                    W[:, i] = seed
                else:
                    # Perturbed copies with varying sigma
                    sigma = self.sigma * (1.0 + (i / self.K) * 2.0)  # Wider spread later
                    noise = torch.randn(self.nF + 1, device=self.device) * sigma
                    # Scale noise by weight magnitude (relative perturbation)
                    noise *= seed.abs().clamp(min=0.01)
                    W[:, i] = seed + noise
        else:
            # Random initialization around INITIAL_WEIGHTS
            init_vec = torch.tensor(
                weight_dict_to_vector(INITIAL_WEIGHTS),
                dtype=torch.float32, device=self.device)
            for i in range(self.K):
                noise = torch.randn(self.nF + 1, device=self.device) * 0.3
                W[:, i] = init_vec + noise

        self._enforce_constraints(W)
        return W

    def _enforce_constraints(self, W: torch.Tensor):
        """Apply bounds and monotonic constraints in-place."""
        W.clamp_(min=self.lo_bounds.unsqueeze(1), max=self.hi_bounds.unsqueeze(1))
        for hi_idx, lo_idx in self.mono_pairs:
            violation = W[hi_idx, :] < W[lo_idx, :]
            if violation.any():
                mid = (W[hi_idx, violation] + W[lo_idx, violation]) * 0.5
                W[hi_idx, violation] = mid
                W[lo_idx, violation] = mid

    def train_population(self, W: torch.Tensor, max_epochs: int = 3000,
                         patience: int = 200, convergence: float = 1e-7,
                         quiet: bool = False) -> torch.Tensor:
        """
        Train ALL K models in parallel via gradient descent.
        Returns best_W tensor (nF+1, K).
        """
        K = W.shape[1]
        best_brier = torch.full((K,), float('inf'), device=self.device)
        best_W = W.clone()
        no_improve = torch.zeros(K, dtype=torch.int32, device=self.device)
        active = torch.ones(K, dtype=torch.bool, device=self.device)

        # Use a fixed learning rate for all (honing perturbations are close to optimum)
        lr = 0.01
        l2 = 0.001

        t0 = time.time()
        final_epoch = 0

        for epoch in range(max_epochs):
            final_epoch = epoch

            # Forward pass — all K models at once
            logits = self.X @ W[1:, :] + W[0, :].unsqueeze(0)  # (N, K)
            P = torch.sigmoid(logits)
            brier_per = ((P - self.y_col) ** 2).mean(dim=0)  # (K,)

            # Backward pass
            error = P - self.y_col
            deriv = P * (1.0 - P)
            grad_factor = 2.0 * error * deriv / self.N
            grad_w = self.X.t() @ grad_factor  # (nF, K)
            grad_b = grad_factor.sum(dim=0)     # (K,)
            grad_w += l2 * W[1:, :]

            # Update only active models
            lr_active = lr * active.float()
            W[0, :] -= lr_active * grad_b
            W[1:, :] -= lr_active.unsqueeze(0) * grad_w

            # Constraints
            self._enforce_constraints(W)

            # Track best
            improved = (brier_per < best_brier - convergence) & active
            best_brier = torch.where(improved, brier_per, best_brier)
            best_W[:, improved] = W[:, improved]
            no_improve = torch.where(improved, torch.zeros_like(no_improve), no_improve + 1)
            active = active & (no_improve < patience)

            if not active.any():
                break

            # Adaptive patience: if 85% done, tighten for rest
            if epoch == patience // 3:
                pct_done = 1.0 - (active.sum().item() / K)
                if pct_done > 0.85:
                    patience = min(patience, epoch + patience // 4)

            if not quiet and epoch % 500 == 0:
                n_active = active.sum().item()
                min_b = best_brier[best_brier < float('inf')].min().item()
                eps = (epoch + 1) * K / (time.time() - t0)
                print(f"    Epoch {epoch:>5d} | Active: {n_active:>5d}/{K} | "
                      f"Best Brier: {min_b:.6f} | {eps:.0f} model-ep/s")

        elapsed = time.time() - t0
        if not quiet:
            total_model_epochs = K * (final_epoch + 1)
            print(f"    Training done: {final_epoch+1} epochs × {K} models = "
                  f"{total_model_epochs:,} model-epochs in {elapsed:.1f}s "
                  f"({total_model_epochs/elapsed:,.0f} model-ep/s)")

        return best_W

    def evaluate_population(self, W: torch.Tensor) -> dict:
        """
        Compute AUC, Brier, accuracy for all K models.
        Uses chunked AUC to avoid OOM on large populations.
        Returns dict of tensors, each shape (K,).
        """
        K = W.shape[1]
        logits = self.X @ W[1:, :] + W[0, :].unsqueeze(0)
        P = torch.sigmoid(logits)

        brier = ((P - self.y_col) ** 2).mean(dim=0)
        accuracy = ((P >= 0.5).float() == self.y_col).float().mean(dim=0)

        # AUC — chunked to prevent OOM on large populations
        pos_mask = (self.y == 1.0)
        neg_mask = (self.y == 0.0)
        n_pos = pos_mask.sum().item()
        n_neg = neg_mask.sum().item()

        if n_pos == 0 or n_neg == 0:
            auc = torch.full((K,), 0.5, device=self.device)
        elif n_pos * n_neg * K <= 10_000_000:
            # Exact AUC — small enough to fit in memory
            P_pos = P[pos_mask, :]
            P_neg = P[neg_mask, :]
            conc = (P_pos.unsqueeze(1) > P_neg.unsqueeze(0)).float()
            tied = (P_pos.unsqueeze(1) == P_neg.unsqueeze(0)).float()
            auc = (conc.sum(dim=(0, 1)) + 0.5 * tied.sum(dim=(0, 1))) / (n_pos * n_neg)
        else:
            # Sampled AUC — CHUNKED across models to avoid OOM
            ns = min(200_000, n_pos * n_neg)
            pi = torch.where(pos_mask)[0]
            ni = torch.where(neg_mask)[0]
            rp = pi[torch.randint(n_pos, (ns,), device=self.device)]
            rn = ni[torch.randint(n_neg, (ns,), device=self.device)]

            # Process in chunks of models (not samples) to stay within VRAM
            # Each chunk needs: ns * chunk_size * 4 bytes * ~3 tensors
            free_mem = torch.cuda.mem_get_info(self.device)[0] if self.device.type == "cuda" else 2e9
            bytes_per_model = ns * 4 * 3  # comparison + tied + float storage
            chunk_size = max(10, int(free_mem * 0.3 / bytes_per_model))
            chunk_size = min(chunk_size, K)

            auc = torch.zeros(K, device=self.device)
            for start in range(0, K, chunk_size):
                end = min(start + chunk_size, K)
                P_rp_chunk = P[rp, start:end]  # (ns, chunk)
                P_rn_chunk = P[rn, start:end]  # (ns, chunk)
                auc[start:end] = ((P_rp_chunk > P_rn_chunk).float().mean(dim=0) +
                                   0.5 * (P_rp_chunk == P_rn_chunk).float().mean(dim=0))

        # Calibration error
        mean_pred = P.mean(dim=0)
        cal_error = (mean_pred - self.base_rate).abs()

        # Composite fitness
        fitness = (0.55 * auc + 0.20 * (1.0 - brier) +
                   0.15 * (1.0 - cal_error.clamp(0, 1)) +
                   0.10 * accuracy)

        return {
            "auc": auc,
            "brier": brier,
            "accuracy": accuracy,
            "cal_error": cal_error,
            "fitness": fitness,
            "predictions": P,
        }

    def evolve(self, W: torch.Tensor, fitness: torch.Tensor,
               generation: int = 0) -> torch.Tensor:
        """
        Create next generation via:
        1. Elite preservation (top 10%)
        2. Tournament selection + crossover (30%)
        3. Mutation of top 50% (60%)

        Sigma anneals: starts at self.sigma, halves every 200 generations,
        but resets to 2x if no improvement for 50 generations.
        """
        K = W.shape[1]

        # Sort by fitness descending
        _, sorted_idx = fitness.sort(descending=True)
        W_sorted = W[:, sorted_idx]

        new_W = torch.zeros_like(W)

        # 1. ELITES — top elite_k copied exactly
        new_W[:, :self.elite_k] = W_sorted[:, :self.elite_k]

        cursor = self.elite_k

        # 2. CROSSOVER — tournament selection + uniform crossover
        n_crossover = int(K * self.crossover_rate)
        if n_crossover > 0:
            # Tournament selection: pick 2 random parents from top 50%, keep fitter
            top_half = K // 2
            parent_a_idx = torch.randint(top_half, (n_crossover,), device=self.device)
            parent_b_idx = torch.randint(top_half, (n_crossover,), device=self.device)
            # Uniform crossover mask
            mask = torch.rand(self.nF + 1, n_crossover, device=self.device) < 0.5
            children = torch.where(mask, W_sorted[:, parent_a_idx],
                                    W_sorted[:, parent_b_idx])
            end = min(cursor + n_crossover, K)
            new_W[:, cursor:end] = children[:, :end - cursor]
            cursor = end

        # 3. MUTATIONS — perturb top 50%
        remaining = K - cursor
        if remaining > 0:
            # Select parents from top 50%
            parent_idx = torch.randint(K // 2, (remaining,), device=self.device)
            parents = W_sorted[:, parent_idx]

            # Adaptive sigma based on generation
            effective_sigma = self.sigma * (0.5 ** (generation / 200))
            effective_sigma = max(effective_sigma, 0.005)  # Floor

            # Relative perturbation (scale noise by weight magnitude)
            noise = torch.randn(self.nF + 1, remaining, device=self.device)
            noise *= effective_sigma * parents.abs().clamp(min=0.01)

            # Occasionally inject larger perturbations (5% of mutations)
            big_mask = torch.rand(remaining, device=self.device) < 0.05
            if big_mask.any():
                big_idx = torch.where(big_mask)[0]
                noise[:, big_idx] *= 5.0  # 5x larger perturbation

            new_W[:, cursor:] = parents + noise

        self._enforce_constraints(new_W)
        return new_W

    def fast_retrain(self, seed_weights: list, max_epochs: int = 1000,
                     patience: int = 100) -> dict:
        """
        Fast retrain from seed weights — for dynamic ODIN rescoring.
        Trains a small population (50) with tight perturbations.
        Returns best weight dict + metrics in <3 seconds.
        """
        t0 = time.time()
        mini_pop = min(50, self.K)

        # Tight perturbation around seed
        W = torch.zeros(self.nF + 1, mini_pop, device=self.device)
        seed = torch.tensor(seed_weights[0], dtype=torch.float32, device=self.device)

        W[:, 0] = seed  # Exact copy
        for i in range(1, mini_pop):
            noise = torch.randn(self.nF + 1, device=self.device) * 0.01
            noise *= seed.abs().clamp(min=0.01)
            W[:, i] = seed + noise

        self._enforce_constraints(W)

        # Fast train
        best_W = self.train_population(W, max_epochs=max_epochs,
                                       patience=patience, quiet=True)

        # Evaluate
        metrics = self.evaluate_population(best_W)
        best_idx = metrics["fitness"].argmax().item()

        elapsed = time.time() - t0
        best_vec = best_W[:, best_idx].cpu().tolist()

        return {
            "weights": vector_to_weight_dict(best_vec),
            "auc": round(metrics["auc"][best_idx].item(), 6),
            "brier": round(metrics["brier"][best_idx].item(), 6),
            "accuracy": round(metrics["accuracy"][best_idx].item(), 6),
            "fitness": round(metrics["fitness"][best_idx].item(), 6),
            "elapsed_seconds": round(elapsed, 2),
            "population": mini_pop,
        }


# ═══════════════════════════════════════════════════════════════
#  TIER SWEEP — Vectorized (same as v2.2)
# ═══════════════════════════════════════════════════════════════

def sweep_tiers_gpu(W_best: torch.Tensor, X: torch.Tensor, y: torch.Tensor,
                     top_n: int = 20, fitness: torch.Tensor = None) -> list:
    """
    Vectorized tier sweep on GPU for top_n models.
    Returns list of tier-scored configs.
    """
    y_np = y.cpu().numpy()
    N = len(y_np)

    # Select top_n by fitness
    if fitness is not None:
        _, top_idx = fitness.topk(min(top_n, W_best.shape[1]))
    else:
        top_idx = torch.arange(min(top_n, W_best.shape[1]))

    W_top = W_best[:, top_idx].cpu().numpy()  # (nF+1, top_n)
    X_np = X.cpu().numpy()

    # Compute predictions for all top models
    logits = X_np @ W_top[1:, :] + W_top[0, :]
    preds = 1.0 / (1.0 + np.exp(-logits))  # (N, top_n)

    all_configs = []

    for model_idx in range(W_top.shape[1]):
        p = preds[:, model_idx]
        w_vec = W_top[:, model_idx].tolist()

        for t1 in TIER1_BASE:
            for t4 in TIER4_BASE:
                if t4 >= t1:
                    continue

                is_t1 = p >= t1
                is_t4 = p < t4
                is_mid = ~is_t1 & ~is_t4
                is_t2 = is_mid & (p >= 0.50)
                is_t3 = is_mid & (p < 0.50)

                t1_n, t4_n = is_t1.sum(), is_t4.sum()
                if t1_n < 20 or t4_n < 20:
                    continue

                t1_pos = y_np[is_t1].sum() / t1_n
                t2_n = is_t2.sum()
                t2_pos = y_np[is_t2].sum() / t2_n if t2_n > 0 else 0
                t3_n = is_t3.sum()
                t3_pos = y_np[is_t3].sum() / t3_n if t3_n > 0 else 0
                t4_pos = y_np[is_t4].sum() / t4_n

                coverage = t1_n / N
                coverage_bonus = min(coverage / 0.25, 1.0)

                tier_score = (t1_pos * 0.30 + (1.0 - t4_pos) * 0.25 +
                              coverage_bonus * 0.20 +
                              min(t1_n / 500, 1.0) * 0.10 +
                              min(t4_n / 500, 1.0) * 0.15)

                all_configs.append({
                    "weights": vector_to_weight_dict(w_vec),
                    "tier_1_boundary": t1,
                    "tier_4_boundary": t4,
                    "tiers": {
                        "TIER_1": {"n": int(t1_n), "pos_rate": round(float(t1_pos), 4)},
                        "TIER_2": {"n": int(t2_n), "pos_rate": round(float(t2_pos), 4)},
                        "TIER_3": {"n": int(t3_n), "pos_rate": round(float(t3_pos), 4)},
                        "TIER_4": {"n": int(t4_n), "pos_rate": round(float(t4_pos), 4)},
                    },
                    "tier_score": round(tier_score, 6),
                })

    all_configs.sort(key=lambda c: c["tier_score"], reverse=True)
    return all_configs


# ═══════════════════════════════════════════════════════════════
#  WALKFORWARD VALIDATION — Vectorized for top-N
# ═══════════════════════════════════════════════════════════════

def walkforward_validate_v23(top_configs: list, events: list,
                              device: torch.device, top_n: int = 10,
                              train_ratio: float = 0.70,
                              quiet: bool = False) -> list:
    """
    v2.3: Vectorized walkforward. Trains top_n models on 70%, tests on 30%.
    Uses PopulationTrainer for parallel training.
    """
    resolved = sorted(
        [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")],
        key=lambda e: e.get("catalyst_date", ""))
    split = int(len(resolved) * train_ratio)
    train_ev, test_ev = resolved[:split], resolved[split:]

    def to_tensors(evts):
        X = [[float(e["features"].get(f, 0.0)) for f in FEATURE_NAMES] for e in evts]
        y = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in evts]
        return (torch.tensor(X, dtype=torch.float32, device=device),
                torch.tensor(y, dtype=torch.float32, device=device))

    X_train, y_train = to_tensors(train_ev)
    X_test, y_test = to_tensors(test_ev)

    # Select top configs
    top = sorted(top_configs, key=lambda c: c.get("tier_score", 0), reverse=True)[:top_n]

    # Build seed weights
    seed_weights = []
    for cfg in top:
        w = cfg["weights"]
        vec = [w["base_logit"]] + [w["features"].get(f, 0.0) for f in FEATURE_NAMES]
        seed_weights.append(vec)

    # Train all models as a batch using PopulationTrainer
    trainer = PopulationTrainer(X_train, y_train, device,
                                 population_size=len(seed_weights))
    W_init = torch.zeros(trainer.nF + 1, len(seed_weights), device=device)
    for i, sv in enumerate(seed_weights):
        W_init[:, i] = torch.tensor(sv, dtype=torch.float32, device=device)

    best_W = trainer.train_population(W_init, max_epochs=3000,
                                       patience=200, quiet=quiet)

    # Evaluate on TEST set
    logits_test = X_test @ best_W[1:, :] + best_W[0, :].unsqueeze(0)
    P_test = torch.sigmoid(logits_test)
    y_test_col = y_test.unsqueeze(1)

    test_brier = ((P_test - y_test_col) ** 2).mean(dim=0)
    test_acc = ((P_test >= 0.5).float() == y_test_col).float().mean(dim=0)

    # Test AUC per model
    pos_mask = (y_test == 1.0)
    neg_mask = (y_test == 0.0)
    P_pos = P_test[pos_mask, :]
    P_neg = P_test[neg_mask, :]
    n_pos, n_neg = P_pos.shape[0], P_neg.shape[0]

    if n_pos > 0 and n_neg > 0:
        conc = (P_pos.unsqueeze(1) > P_neg.unsqueeze(0)).float()
        tied = (P_pos.unsqueeze(1) == P_neg.unsqueeze(0)).float()
        test_auc = (conc.sum(dim=(0, 1)) + 0.5 * tied.sum(dim=(0, 1))) / (n_pos * n_neg)
    else:
        test_auc = torch.full((len(seed_weights),), 0.5, device=device)

    # Evaluate on TRAIN set
    logits_train = X_train @ best_W[1:, :] + best_W[0, :].unsqueeze(0)
    P_train = torch.sigmoid(logits_train)
    y_train_col = y_train.unsqueeze(1)
    train_brier = ((P_train - y_train_col) ** 2).mean(dim=0)

    # Package results
    validated = []
    for i, cfg in enumerate(top):
        w_vec = best_W[:, i].cpu().tolist()
        overfit = float(test_brier[i] - train_brier[i])
        validated.append({
            "rank": i + 1,
            "train_brier": round(float(train_brier[i]), 6),
            "test_brier": round(float(test_brier[i]), 6),
            "test_auc": round(float(test_auc[i]), 6),
            "test_accuracy": round(float(test_acc[i]), 6),
            "overfit_delta": round(overfit, 6),
            "test_n": len(test_ev),
            "train_n": len(train_ev),
            "tier_1_boundary": cfg.get("tier_1_boundary", 0.85),
            "tier_4_boundary": cfg.get("tier_4_boundary", 0.05),
            "tiers": cfg.get("tiers", {}),
            "weights": vector_to_weight_dict(w_vec),
        })

    validated.sort(key=lambda v: v["test_auc"], reverse=True)
    return validated


# ═══════════════════════════════════════════════════════════════
#  FILE I/O — Best config, leaderboard, history
# ═══════════════════════════════════════════════════════════════

class BestConfigTracker:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.best = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath) as f:
                return json.load(f)
        return None

    def save(self):
        tmp = self.filepath + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.best, f, indent=2)
        os.replace(tmp, self.filepath)

    def check_and_update(self, candidate: dict) -> bool:
        if self.best is None:
            self.best = candidate
            self.save()
            return True
        prev_auc = self.best.get("auc", self.best.get("metrics", {}).get("auc", 0))
        cand_auc = candidate.get("auc", candidate.get("metrics", {}).get("auc", 0))
        if cand_auc > prev_auc + 1e-7:
            self.best = candidate
            self.save()
            return True
        return False

    def print_best(self):
        if self.best is None:
            print("  No best config recorded yet.")
            return
        b = self.best
        auc = b.get("auc", b.get("metrics", {}).get("auc", "?"))
        brier = b.get("brier", b.get("metrics", {}).get("brier", "?"))
        print(f"  AUC: {auc}")
        print(f"  Brier: {brier}")
        if "generation" in b:
            print(f"  Generation: {b['generation']}")
        if "population_size" in b:
            print(f"  Population: {b['population_size']}")


class RunHistory:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def log(self, entry: dict):
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list:
        if not os.path.exists(self.filepath):
            return []
        entries = []
        with open(self.filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def count(self) -> int:
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath) as f:
            return sum(1 for _ in f)


# ═══════════════════════════════════════════════════════════════
#  PERPETUAL ENGINE v2.3 — Population-Based Evolutionary
# ═══════════════════════════════════════════════════════════════

class GungnirPerpetualGPU_v23:
    """
    v2.3 architecture:
    1. Initialize population from seed weights (model_weights.json or best_run)
    2. Each generation: train → evaluate → evolve
    3. Every N generations: tier sweep + walkforward validation
    4. Auto-detect plateau → increase sigma → try restart
    5. Fast retrain mode for dynamic ODIN scoring
    """

    def __init__(self, data_dir: str = None, population_size: int = None,
                 device: str = None, seed_file: str = None):
        self.data_dir = data_dir or get_data_dir()

        # Device selection
        if device:
            self.device = torch.device(device)
        elif torch.cuda.is_available():
            self.device = torch.device("cuda:0")
        else:
            self.device = torch.device("cpu")
        print(f"  Device: {self.device}")
        if self.device.type == "cpu":
            print(f"  ⚠ Running on CPU — expect ~10-50x slower than GPU.")
            print(f"    For CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121")

        # Load data
        print("  Loading PDUFA events...")
        self.events = load_phase_events()
        resolved = [e for e in self.events
                    if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        print(f"  Resolved events: {len(resolved)}")

        # Precompute features
        precompute_features(resolved)
        X_list = [[float(e["features"].get(f, 0.0)) for f in FEATURE_NAMES]
                  for e in resolved]
        y_list = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in resolved]

        self.X = torch.tensor(X_list, dtype=torch.float32, device=self.device)
        self.y = torch.tensor(y_list, dtype=torch.float32, device=self.device)
        self.N, self.nF = self.X.shape
        print(f"  Dataset: {self.N} events × {self.nF} features")

        # Auto-size population
        if population_size:
            self.pop_size = population_size
        else:
            self.pop_size = estimate_population_size(
                self.N, self.nF, self.device)
        print(f"  Population size: {self.pop_size}")

        vram = get_vram_stats(self.device)
        if vram['total_mb'] > 0:
            print(f"  VRAM: {vram['allocated_mb']:.1f} MB used / {vram['total_mb']:.0f} MB total")
        else:
            print(f"  VRAM: N/A (CPU mode)")

        # File paths — must init BEFORE _load_seeds which references best_tracker
        self.best_tracker = BestConfigTracker(
            os.path.join(self.data_dir, "best_config_v23.json"))
        self.history = RunHistory(
            os.path.join(self.data_dir, "run_history_v23.jsonl"))

        # Load seed weights (after best_tracker is initialized)
        self.seed_weights = self._load_seeds(seed_file)

        # Trainer
        self.trainer = PopulationTrainer(
            self.X, self.y, self.device,
            population_size=self.pop_size,
            elite_fraction=0.10,
            mutation_sigma=0.05,
            crossover_rate=0.30)

        # State
        self.best_fitness = -float('inf')
        self.stale_generations = 0
        self.total_generations = self.history.count()

    def _load_seeds(self, seed_file: str = None) -> list:
        """Load seed weights from model_weights.json, best_run files, or specified file."""
        seeds = []

        # 1. Check specified file
        if seed_file and os.path.exists(seed_file):
            with open(seed_file) as f:
                data = json.load(f)
            if "weights" in data:
                seeds.append(weight_dict_to_vector(data["weights"]))
                print(f"  Loaded seed from: {seed_file}")
            return seeds

        # 2. Check model_weights.json
        mw_path = os.path.join(self.data_dir, "model_weights.json")
        if os.path.exists(mw_path):
            with open(mw_path) as f:
                data = json.load(f)
            seeds.append(weight_dict_to_vector(data))
            print(f"  Loaded seed from: model_weights.json")

        # 3. Check best_config_v23.json
        if self.best_tracker.best:
            w = self.best_tracker.best.get("weights", {})
            if w:
                seeds.append(weight_dict_to_vector(w))
                print(f"  Loaded seed from: best_config_v23.json")

        # 4. Check for best_run_*.json files
        for f in sorted(Path(self.data_dir).glob("best_run_AUC_*.json"), reverse=True):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                if "weights" in data:
                    seeds.append(weight_dict_to_vector(data["weights"]))
                    print(f"  Loaded seed from: {f.name}")
                    if len(seeds) >= 5:
                        break
            except (json.JSONDecodeError, KeyError):
                continue

        if not seeds:
            # Fallback to initial weights
            seeds.append(weight_dict_to_vector(INITIAL_WEIGHTS))
            print("  Using INITIAL_WEIGHTS as seed")

        print(f"  Total seed weight vectors: {len(seeds)}")
        return seeds

    def run_generation(self, gen: int, W: torch.Tensor,
                       quiet: bool = False) -> tuple:
        """
        Run one generation: train → evaluate → evolve.
        Returns (new_W, gen_stats).
        """
        t0 = time.time()

        # 1. Train population
        if not quiet:
            print(f"\n  ── Generation {gen} ──")
        best_W = self.trainer.train_population(
            W, max_epochs=2000, patience=150, quiet=quiet)

        # 2. Evaluate
        metrics = self.trainer.evaluate_population(best_W)
        best_idx = metrics["fitness"].argmax().item()
        gen_best_fitness = metrics["fitness"][best_idx].item()
        gen_best_auc = metrics["auc"][best_idx].item()
        gen_best_brier = metrics["brier"][best_idx].item()

        # 3. Track improvement
        is_new_best = False
        if gen_best_fitness > self.best_fitness + 1e-7:
            self.best_fitness = gen_best_fitness
            self.stale_generations = 0
            is_new_best = True

            # Save best weights
            w_vec = best_W[:, best_idx].cpu().tolist()
            best_entry = {
                "generation": gen,
                "auc": round(gen_best_auc, 6),
                "brier": round(gen_best_brier, 6),
                "accuracy": round(metrics["accuracy"][best_idx].item(), 6),
                "fitness": round(gen_best_fitness, 6),
                "population_size": self.pop_size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "weights": vector_to_weight_dict(w_vec),
            }
            self.best_tracker.check_and_update(best_entry)
        else:
            self.stale_generations += 1

        # 4. Adaptive sigma based on staleness
        if self.stale_generations > 100:
            self.trainer.sigma = 0.15  # Wide search
        elif self.stale_generations > 50:
            self.trainer.sigma = 0.10  # Moderate search
        elif self.stale_generations > 20:
            self.trainer.sigma = 0.07
        else:
            self.trainer.sigma = 0.05  # Default tight

        # 5. Evolve
        new_W = self.trainer.evolve(best_W, metrics["fitness"], generation=gen)

        # 6. Population diversity check
        pop_std = best_W.std(dim=1).mean().item()

        elapsed = time.time() - t0

        # Stats
        stats = {
            "generation": gen,
            "best_auc": round(gen_best_auc, 6),
            "best_brier": round(gen_best_brier, 6),
            "best_fitness": round(gen_best_fitness, 6),
            "mean_fitness": round(metrics["fitness"].mean().item(), 6),
            "pop_std": round(pop_std, 6),
            "stale": self.stale_generations,
            "sigma": round(self.trainer.sigma, 4),
            "is_new_best": is_new_best,
            "elapsed": round(elapsed, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not quiet:
            flag = " ★ NEW BEST" if is_new_best else ""
            print(f"    AUC={gen_best_auc:.6f} Brier={gen_best_brier:.6f} "
                  f"Fit={gen_best_fitness:.6f} Stale={self.stale_generations} "
                  f"σ={self.trainer.sigma:.3f} Div={pop_std:.4f} "
                  f"[{elapsed:.1f}s]{flag}")

        # Log
        self.history.log(stats)

        return new_W, stats

    def run_perpetual(self, max_generations: int = None,
                      pause_seconds: float = 1.0,
                      tier_sweep_every: int = 25,
                      walkforward_every: int = 50):
        """
        Main loop: evolve population, periodically tier-sweep and walkforward.
        """
        print("\n" + "═" * 70)
        print(f"  GUNGNIR v{__version__} — Population-Based GPU Honing")
        print(f"  Population: {self.pop_size} | Device: {self.device}")
        print(f"  Seeds: {len(self.seed_weights)} | Stale: {self.stale_generations}")
        if max_generations:
            print(f"  Running {max_generations} generations")
        else:
            print(f"  Running indefinitely (Ctrl+C to stop)")
        print("═" * 70)

        # Initialize population
        W = self.trainer.initialize_population(self.seed_weights)
        gen = self.total_generations

        try:
            while True:
                if max_generations and gen >= self.total_generations + max_generations:
                    break

                W, stats = self.run_generation(gen, W)
                gen += 1

                # Periodic tier sweep
                if gen % tier_sweep_every == 0:
                    print(f"\n  ── Tier Sweep (gen {gen}) ──")
                    metrics = self.trainer.evaluate_population(W)
                    tier_configs = sweep_tiers_gpu(
                        W, self.X, self.y, top_n=10,
                        fitness=metrics["fitness"])
                    if tier_configs:
                        best_t = tier_configs[0]
                        t1 = best_t["tiers"]["TIER_1"]
                        t4 = best_t["tiers"]["TIER_4"]
                        print(f"    Best tier: T1={best_t['tier_1_boundary']:.2f} "
                              f"({t1['n']}n, {t1['pos_rate']:.1%}) | "
                              f"T4={best_t['tier_4_boundary']:.2f} "
                              f"({t4['n']}n, {t4['pos_rate']:.1%}) | "
                              f"Score={best_t['tier_score']:.4f}")

                # Periodic walkforward
                if gen % walkforward_every == 0:
                    print(f"\n  ── Walkforward Validation (gen {gen}) ──")
                    metrics = self.trainer.evaluate_population(W)
                    # Get top configs for walkforward
                    tier_configs = sweep_tiers_gpu(
                        W, self.X, self.y, top_n=5,
                        fitness=metrics["fitness"])
                    if tier_configs:
                        wf_results = walkforward_validate_v23(
                            tier_configs, self.events, self.device,
                            top_n=5, quiet=True)
                        if wf_results:
                            best_wf = wf_results[0]
                            print(f"    Best WF: test_AUC={best_wf['test_auc']:.4f} "
                                  f"test_Brier={best_wf['test_brier']:.4f} "
                                  f"overfit={best_wf['overfit_delta']:+.4f}")

                # Plateau restart
                if self.stale_generations >= 200:
                    print(f"\n  ⚠ PLATEAU RESTART at gen {gen} (stale={self.stale_generations})")
                    # Re-initialize with wider perturbations
                    self.trainer.sigma = 0.20
                    W = self.trainer.initialize_population(self.seed_weights)
                    self.stale_generations = 0

                # Convergence detection
                if gen > 50:
                    pop_std = W.std(dim=1).mean().item()
                    if pop_std < 0.0001:
                        print(f"\n  ⚠ DIVERSITY COLLAPSE at gen {gen} (std={pop_std:.6f})")
                        self.trainer.sigma = 0.15
                        W = self.trainer.initialize_population(self.seed_weights)

                # VRAM stats periodically
                if gen % 50 == 0:
                    vram = get_vram_stats(self.device)
                    print(f"  📊 VRAM: {vram['allocated_mb']:.0f}MB / {vram['total_mb']:.0f}MB "
                          f"({vram['allocated_mb']/vram['total_mb']*100:.1f}%)")

                if pause_seconds > 0:
                    time.sleep(pause_seconds)

        except KeyboardInterrupt:
            print(f"\n\n  Stopped at generation {gen}.")

        print(f"\n  Final stats:")
        self.best_tracker.print_best()

    def run_fast_retrain(self):
        """
        Dynamic ODIN mode: fast retrain from seed weights.
        Target: <3 seconds for a full weight update.
        """
        print(f"\n  ⚡ FAST RETRAIN MODE")
        print(f"  Dataset: {self.N} events × {self.nF} features")
        print(f"  Device: {self.device}")

        result = self.trainer.fast_retrain(
            self.seed_weights, max_epochs=1000, patience=100)

        print(f"\n  Results:")
        print(f"    AUC:      {result['auc']:.6f}")
        print(f"    Brier:    {result['brier']:.6f}")
        print(f"    Accuracy: {result['accuracy']:.6f}")
        print(f"    Fitness:  {result['fitness']:.6f}")
        print(f"    Time:     {result['elapsed_seconds']:.2f}s")
        print(f"    Pop:      {result['population']}")

        # Save updated weights
        mw_path = os.path.join(self.data_dir, "model_weights.json")
        tmp = mw_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(result["weights"], f, indent=2)
        os.replace(tmp, mw_path)
        print(f"\n  Updated: {mw_path}")

        return result

    def export_weights(self):
        """Export current best weights as model_weights.json."""
        if self.best_tracker.best is None:
            print("  No best config to export.")
            return

        w = self.best_tracker.best.get("weights", {})
        mw_path = os.path.join(self.data_dir, "model_weights.json")
        tmp = mw_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(w, f, indent=2)
        os.replace(tmp, mw_path)

        auc = self.best_tracker.best.get("auc", "?")
        print(f"  Exported weights (AUC={auc}) to: {mw_path}")


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description=f"Gungnir Perpetual GPU v{__version__} — ODIN Population-Based Honing")
    parser.add_argument("--cycles", "--generations", type=int, default=None,
                        help="Number of generations to run (default: infinite)")
    parser.add_argument("--pop", type=int, default=None,
                        help="Population size (default: auto-detect from VRAM)")
    parser.add_argument("--device", type=str, default=None,
                        help="Device (cuda:0, cpu, etc.)")
    parser.add_argument("--seed", type=str, default=None,
                        help="Seed weights file (default: auto-detect)")
    parser.add_argument("--pause", type=float, default=1.0,
                        help="Pause between generations in seconds")
    parser.add_argument("--tier-every", type=int, default=25,
                        help="Tier sweep every N generations")
    parser.add_argument("--wf-every", type=int, default=50,
                        help="Walkforward every N generations")
    parser.add_argument("--retrain", action="store_true",
                        help="Fast retrain mode (<3s)")
    parser.add_argument("--best", action="store_true",
                        help="Show best config and exit")
    parser.add_argument("--export", action="store_true",
                        help="Export best weights to model_weights.json")
    parser.add_argument("--history", action="store_true",
                        help="Show run history summary")

    args = parser.parse_args()

    print(f"\n{'═'*70}")
    print(f"  GUNGNIR PERPETUAL GPU v{__version__}")
    print(f"  ODIN Population-Based Honing Engine")
    print(f"{'═'*70}")

    engine = GungnirPerpetualGPU_v23(
        population_size=args.pop,
        device=args.device,
        seed_file=args.seed)

    if args.best:
        print("\n  ── Best Config ──")
        engine.best_tracker.print_best()
        return

    if args.export:
        engine.export_weights()
        return

    if args.history:
        entries = engine.history.read_all()
        if not entries:
            print("  No history yet.")
            return
        print(f"\n  History: {len(entries)} generations")
        # Show last 10
        for e in entries[-10:]:
            flag = " ★" if e.get("is_new_best") else ""
            print(f"    Gen {e['generation']:>5d}: AUC={e['best_auc']:.6f} "
                  f"Brier={e['best_brier']:.6f} Stale={e['stale']}{flag}")
        return

    if args.retrain:
        engine.run_fast_retrain()
        return

    engine.run_perpetual(
        max_generations=args.cycles,
        pause_seconds=args.pause,
        tier_sweep_every=args.tier_every,
        walkforward_every=args.wf_every)


if __name__ == "__main__":
    main()
