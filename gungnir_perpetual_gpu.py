#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR PERPETUAL GPU RUNNER v2.0                                         ║
║  Nonstop GPU-accelerated hyperparameter search                             ║
║                                                                            ║
║  Runs ALL NIGHT. Every cycle:                                              ║
║    1. GPU sweep: 5,000+ models trained in parallel                         ║
║    2. Tier boundary sweep: 2,100 configs evaluated                         ║
║    3. Walk-forward validation: top 20 retrained on 70/30 split             ║
║    4. Compare vs best ever → save if new apex                              ║
║    5. Randomize grid slightly → explore new regions next cycle             ║
║    6. Log everything to disk                                               ║
║                                                                            ║
║  Usage:                                                                    ║
║    python gungnir_perpetual_gpu.py                   Run forever           ║
║    python gungnir_perpetual_gpu.py --cycles 50       Run N cycles          ║
║    python gungnir_perpetual_gpu.py --combos 10000    More combos/cycle     ║
║    python gungnir_perpetual_gpu.py --best            Show best ever        ║
║    python gungnir_perpetual_gpu.py --history          Show run history     ║
║                                                                            ║
║  Output dir: ~/gungnir_data/                                               ║
║    best_config.json     — Best model ever found (weights + metrics)        ║
║    run_history.jsonl    — Every cycle logged (append-only)                 ║
║    top_10_configs.json  — Current top 10 leaderboard                       ║
║    walkforward_log.jsonl — Every WF validation result                      ║
║                                                                            ║
║  Requires: pip install torch --index-url                                   ║
║            https://download.pytorch.org/whl/cu121                          ║
║                                                                            ║
║  Built for pdufa.bio — RTX 4070 target — Feb 2026                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import hashlib
import itertools
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

from gungnir_honing_engine import (
    load_phase_events,
    precompute_features,
    FEATURE_NAMES,
    INITIAL_WEIGHTS,
    PARAM_BOUNDS,
    MONOTONIC_CONSTRAINTS,
    sigmoid,
)

__version__ = "2.0.0"


# ═══════════════════════════════════════════════════════════════
#  DATA DIR
# ═══════════════════════════════════════════════════════════════

def get_data_dir() -> str:
    d = str(Path.home() / "gungnir_data")
    os.makedirs(d, exist_ok=True)
    return d


# ═══════════════════════════════════════════════════════════════
#  HYPERPARAMETER GRID — With jitter for exploration
# ═══════════════════════════════════════════════════════════════

# Base grids (cycle 1)
LR_BASE     = [0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]
L2_BASE     = [0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05]
BLOGIT_BASE = [-0.5, -0.3, -0.1, 0.0, 0.12, 0.25, 0.4, 0.6, 0.8, 1.0]
TIER1_BASE  = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
TIER4_BASE  = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

# Strategy distribution — heavily biased toward exploiting current best
# "platform" = current best weights (the thing we're climbing from)
STRATEGY_DISTRIBUTION = {
    # 80% exploitation: start from best + variations
    "platform":       0.35,   # Exact best weights, different lr/l2
    "noisy_small":    0.20,   # Best + small gaussian noise (σ=0.02)
    "noisy_medium":   0.15,   # Best + medium noise (σ=0.08)
    "noisy_large":    0.10,   # Best + large noise (σ=0.20) — bigger jumps
    # 15% semi-exploitation: derived from best
    "half_platform":  0.05,   # 50% of best weights
    "negative":       0.03,   # Negated best (adversarial probe)
    "initial":        0.02,   # Gungnir v4.0 starting weights
    # 5% wild exploration: escape local optima
    "zero":           0.03,   # Tabula rasa
    "random":         0.07,   # Fully random weights
}


def jitter_grid(base: list, jitter_pct: float = 0.15, seed: int = 0) -> list:
    """Add random jitter to grid values for exploration."""
    rng = random.Random(seed)
    result = []
    for v in base:
        if v == 0:
            # For zero, add small random offset
            j = rng.uniform(-0.005, 0.005)
        else:
            j = v * rng.uniform(-jitter_pct, jitter_pct)
        result.append(round(v + j, 6))
    # Also inject a few fully random points
    lo, hi = min(base), max(base)
    for _ in range(3):
        result.append(round(rng.uniform(lo, hi), 6))
    return sorted(set(result))


# ═══════════════════════════════════════════════════════════════
#  BEST CONFIG TRACKER — Persistent across all cycles
# ═══════════════════════════════════════════════════════════════

class BestConfigTracker:
    """Persists the best model ever found across all cycles."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.best = None
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.best = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.best, f, indent=2, default=str)

    def check_and_update(self, candidate: dict) -> bool:
        """
        Compare candidate against best ever.
        Primary: test_auc (walk-forward generalization).
        Tiebreaker: test_brier.
        Returns True if new best.
        """
        c_auc = candidate.get("test_auc", candidate.get("auc", 0))
        c_brier = candidate.get("test_brier", candidate.get("brier", 1))

        is_new = False
        if self.best is None:
            is_new = True
        else:
            b_auc = self.best.get("test_auc", self.best.get("auc", 0))
            b_brier = self.best.get("test_brier", self.best.get("brier", 1))
            if c_auc > b_auc + 0.0005:
                is_new = True
            elif abs(c_auc - b_auc) <= 0.0005 and c_brier < b_brier - 0.0005:
                is_new = True

        if is_new:
            self.best = {
                **candidate,
                "crowned_at": datetime.now(timezone.utc).isoformat(),
            }
            self.save()
        return is_new

    def print_best(self):
        if not self.best:
            print("  No best config found yet. Run a sweep first.")
            return
        b = self.best
        print(f"\n  ╔══════════════════════════════════════════════════════╗")
        print(f"  ║  ⚔️  GUNGNIR ALL-TIME BEST CONFIG                   ║")
        print(f"  ╚══════════════════════════════════════════════════════╝")
        print(f"  Crowned:        {b.get('crowned_at', '?')[:19]}Z")
        print(f"  Cycle:          {b.get('cycle', '?')}")
        if b.get("test_auc"):
            print(f"  Test AUC:       {b['test_auc']:.6f}  ← walk-forward (30% holdout)")
            print(f"  Test Brier:     {b['test_brier']:.6f}")
            print(f"  Train AUC:      {b.get('train_auc', '?'):.6f}")
            print(f"  Overfit delta:  {b.get('overfit_delta', 0):+.4f}")
        else:
            print(f"  AUC:            {b.get('auc', '?'):.6f}")
            print(f"  Brier:          {b.get('brier', '?'):.6f}")
        print(f"  LR:             {b.get('lr', '?')}")
        print(f"  L2:             {b.get('l2', '?')}")
        print(f"  Init:           {b.get('init_strategy', '?')}")
        print(f"  T1 boundary:    ≥{b.get('tier_1_boundary', 0.70)}")
        print(f"  T4 boundary:    <{b.get('tier_4_boundary', 0.20)}")

        # Tier stats
        tiers = b.get("tiers", {})
        for t in ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]:
            s = tiers.get(t, {})
            if s.get("n", 0) > 0:
                print(f"  {t}: n={s['n']:>5}  pos={s['pos_rate']:.1%}")

        # Top weights
        w = b.get("weights", {}).get("features", {})
        if w:
            sorted_w = sorted(w.items(), key=lambda x: abs(x[1]), reverse=True)
            print(f"\n  Top 10 features:")
            for fname, wt in sorted_w[:10]:
                arrow = "↑" if wt > 0 else "↓"
                print(f"    {arrow} {fname:<30s} {wt:+.4f}")


# ═══════════════════════════════════════════════════════════════
#  TOP-10 LEADERBOARD — Running best across all cycles
# ═══════════════════════════════════════════════════════════════

class Leaderboard:
    """Maintains top-10 configs across all cycles."""

    def __init__(self, filepath: str, max_entries: int = 10):
        self.filepath = filepath
        self.max_entries = max_entries
        self.entries = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.entries = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.entries, f, indent=2, default=str)

    def submit(self, candidate: dict) -> int:
        """
        Submit a config. Returns rank (1-based) if it made the leaderboard, 0 otherwise.
        """
        c_auc = candidate.get("test_auc", candidate.get("auc", 0))
        entry = {**candidate, "submitted_at": datetime.now(timezone.utc).isoformat()}

        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.get("test_auc", e.get("auc", 0)), reverse=True)
        self.entries = self.entries[:self.max_entries]
        self.save()

        # Return rank if still in list
        for i, e in enumerate(self.entries):
            if e.get("submitted_at") == entry["submitted_at"]:
                return i + 1
        return 0

    def print_board(self):
        print(f"\n  ╔═══════════════════════════════════════════════════════════════╗")
        print(f"  ║  TOP {self.max_entries} LEADERBOARD                                        ║")
        print(f"  ╚═══════════════════════════════════════════════════════════════╝")
        if not self.entries:
            print("  (empty)")
            return
        print(f"  {'#':>3s} │ {'Test AUC':>8s} │ {'Brier':>6s} │ {'LR':>6s} │ "
              f"{'L2':>6s} │ {'Init':>8s} │ {'Cycle':>5s} │ {'T1≥':>4s} │ {'T4<':>4s}")
        print(f"  {'─'*3}─┼─{'─'*8}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*6}─┼─"
              f"{'─'*8}─┼─{'─'*5}─┼─{'─'*4}─┼─{'─'*4}")
        for i, e in enumerate(self.entries):
            auc = e.get("test_auc", e.get("auc", 0))
            bri = e.get("test_brier", e.get("brier", 0))
            print(f"  {i+1:>3d} │ {auc:>.6f} │ {bri:>.4f} │ {e.get('lr',0):>6.4f} │ "
                  f"{e.get('l2',0):>6.4f} │ {e.get('init_strategy','?'):>8s} │ "
                  f"{e.get('cycle','?'):>5s} │ {e.get('tier_1_boundary',0.7):>.2f} │ "
                  f"{e.get('tier_4_boundary',0.2):>.2f}")


# ═══════════════════════════════════════════════════════════════
#  RUN HISTORY — Append-only JSONL log
# ═══════════════════════════════════════════════════════════════

class RunHistory:
    """Append-only log of every cycle."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def log(self, entry: dict):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def read_all(self) -> list:
        if not os.path.exists(self.filepath):
            return []
        entries = []
        with open(self.filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def count(self) -> int:
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath, "r") as f:
            return sum(1 for _ in f)


# ═══════════════════════════════════════════════════════════════
#  GPU BATCH TRAINER (from gungnir_gpu_sweep.py — inlined)
# ═══════════════════════════════════════════════════════════════

def build_init_weights(strategy: str, base_logit: float,
                       platform: dict = None) -> list:
    """
    Build weight vector from a strategy.
    'platform' = current best weights we're building on top of.
    SAFETY: platform-dependent strategies ALWAYS fall back to INITIAL_WEIGHTS
    if platform is missing — never to zeros.
    """
    nf = len(FEATURE_NAMES)
    rng = random.Random()

    # Resolve platform: if missing or empty, fall back to INITIAL_WEIGHTS
    effective_platform = None
    if platform and platform.get("features"):
        n_active = sum(1 for v in platform["features"].values() if abs(v) > 0.001)
        if n_active > 0:
            effective_platform = platform

    if effective_platform is None:
        # Safety net: use INITIAL_WEIGHTS so we never start from zeros
        effective_platform = INITIAL_WEIGHTS

    feats = effective_platform.get("features", {})
    base_w = [feats.get(f, 0.0) for f in FEATURE_NAMES]

    if strategy == "platform":
        w = list(base_w)
    elif strategy == "noisy_small":
        w = [v + rng.gauss(0, 0.02) for v in base_w]
    elif strategy == "noisy_medium":
        w = [v + rng.gauss(0, 0.08) for v in base_w]
    elif strategy == "noisy_large":
        w = [v + rng.gauss(0, 0.20) for v in base_w]
    elif strategy == "half_platform":
        w = [v * 0.5 for v in base_w]
    elif strategy == "negative":
        w = [-v for v in base_w]
    elif strategy == "initial":
        iw = INITIAL_WEIGHTS["features"]
        w = [iw.get(f, 0.0) for f in FEATURE_NAMES]
    elif strategy == "random":
        w = [rng.gauss(0, 0.3) for _ in range(nf)]
    elif strategy == "zero":
        w = [0.0] * nf
    else:
        # Unknown strategy — use platform rather than zeros
        w = list(base_w)

    return [base_logit] + w


def gpu_train_batch(X: torch.Tensor, y: torch.Tensor, configs: list,
                    max_epochs: int = 5000, patience: int = 300,
                    convergence: float = 1e-7, log_interval: int = 1000,
                    quiet: bool = False) -> list:
    """Train K models in parallel on GPU with bounds + monotonic constraints.
    Returns list of result dicts with composite fitness."""
    device = X.device
    N, nF = X.shape
    K = len(configs)

    # Build tensors
    W = torch.zeros(nF + 1, K, device=device)
    lr_vec = torch.zeros(K, device=device)
    l2_vec = torch.zeros(K, device=device)

    for i, cfg in enumerate(configs):
        w = cfg["init_weights"]
        W[:, i] = torch.tensor(w, dtype=torch.float32, device=device)
        lr_vec[i] = cfg["lr"]
        l2_vec[i] = cfg["l2"]

    # ── Build bounds tensors (applied after every gradient step) ──
    # W layout: row 0 = base_logit, rows 1..nF = features
    lo_bounds = torch.full((nF + 1,), -float('inf'), device=device)
    hi_bounds = torch.full((nF + 1,), float('inf'), device=device)
    for j, fname in enumerate(FEATURE_NAMES):
        if fname in PARAM_BOUNDS:
            lo_bounds[j + 1] = PARAM_BOUNDS[fname][0]
            hi_bounds[j + 1] = PARAM_BOUNDS[fname][1]

    # ── Build monotonic constraint index pairs ──
    # (hi_idx, lo_idx) where W[hi_idx] >= W[lo_idx] must hold
    mono_pairs = []
    for hi_name, lo_name in MONOTONIC_CONSTRAINTS:
        hi_idx = FEATURE_NAMES.index(hi_name) + 1  # +1 for base_logit offset
        lo_idx = FEATURE_NAMES.index(lo_name) + 1
        mono_pairs.append((hi_idx, lo_idx))

    best_brier = torch.full((K,), float('inf'), device=device)
    best_W = W.clone()
    no_improve = torch.zeros(K, dtype=torch.int32, device=device)
    active = torch.ones(K, dtype=torch.bool, device=device)
    y_col = y.unsqueeze(1)

    t0 = time.time()
    final_epoch = 0

    for epoch in range(max_epochs):
        final_epoch = epoch

        logits = X @ W[1:, :] + W[0, :].unsqueeze(0)
        P = torch.sigmoid(logits)
        brier_per = ((P - y_col) ** 2).mean(dim=0)

        error = P - y_col
        deriv = P * (1.0 - P)
        grad_factor = 2.0 * error * deriv / N
        grad_w = X.t() @ grad_factor
        grad_b = grad_factor.sum(dim=0)
        grad_w += l2_vec.unsqueeze(0) * W[1:, :]

        lr_active = lr_vec * active.float()
        W[0, :] -= lr_active * grad_b
        W[1:, :] -= lr_active.unsqueeze(0) * grad_w

        # ── Enforce parameter bounds (broadcast across K models) ──
        W.clamp_(min=lo_bounds.unsqueeze(1), max=hi_bounds.unsqueeze(1))

        # ── Enforce monotonic constraints ──
        for hi_idx, lo_idx in mono_pairs:
            # Where hi < lo, snap both to midpoint
            violation = W[hi_idx, :] < W[lo_idx, :]
            if violation.any():
                mid = (W[hi_idx, violation] + W[lo_idx, violation]) * 0.5
                W[hi_idx, violation] = mid
                W[lo_idx, violation] = mid

        improved = (brier_per < best_brier - convergence) & active
        best_brier = torch.where(improved, brier_per, best_brier)
        best_W[:, improved] = W[:, improved]
        no_improve = torch.where(improved, torch.zeros_like(no_improve), no_improve + 1)
        active = active & (no_improve < patience)

        if not active.any():
            break

        if not quiet and epoch % log_interval == 0:
            n_active = active.sum().item()
            min_b = best_brier[best_brier < float('inf')].min().item()
            eps = (epoch + 1) / (time.time() - t0) if time.time() > t0 else 0
            print(f"    Epoch {epoch:>5d} | Active: {n_active:>5d}/{K} | "
                  f"Best Brier: {min_b:.6f} | {eps:.0f} ep/s")

    elapsed = time.time() - t0
    if not quiet:
        print(f"    Done: {final_epoch+1} epochs in {elapsed:.1f}s")

    # ── Compute AUC for all models ──
    logits_final = X @ best_W[1:, :] + best_W[0, :].unsqueeze(0)
    P_final = torch.sigmoid(logits_final)

    pos_mask = (y == 1.0)
    neg_mask = (y == 0.0)
    P_pos = P_final[pos_mask, :]
    P_neg = P_final[neg_mask, :]
    n_pos, n_neg = P_pos.shape[0], P_neg.shape[0]

    if n_pos > 0 and n_neg > 0 and n_pos * n_neg * K <= 5_000_000:
        conc = (P_pos.unsqueeze(1) > P_neg.unsqueeze(0)).float()
        tied = (P_pos.unsqueeze(1) == P_neg.unsqueeze(0)).float()
        auc_scores = (conc.sum(dim=(0, 1)) + 0.5 * tied.sum(dim=(0, 1))) / (n_pos * n_neg)
    else:
        ns = 200_000
        pi = torch.where(pos_mask)[0]
        ni = torch.where(neg_mask)[0]
        rp = pi[torch.randint(n_pos, (ns,), device=device)]
        rn = ni[torch.randint(n_neg, (ns,), device=device)]
        auc_scores = ((P_final[rp] > P_final[rn]).float().mean(dim=0) +
                       0.5 * (P_final[rp] == P_final[rn]).float().mean(dim=0))

    acc_scores = ((P_final >= 0.5).float() == y_col).float().mean(dim=0)

    # ── Composite fitness: AUC (primary) + calibration (secondary) ──
    # Calibration: how well does mean predicted prob match actual positive rate?
    # Bucket into deciles, measure mean absolute difference
    base_rate = y.mean().item()
    mean_pred = P_final.mean(dim=0)  # per model
    cal_error = (mean_pred - base_rate).abs()  # global calibration gap

    # Composite: 60% AUC + 25% (1-Brier) + 15% (1-cal_error)
    composite = (0.60 * auc_scores +
                 0.25 * (1.0 - best_brier) +
                 0.15 * (1.0 - cal_error.clamp(0, 1)))

    # Package
    best_W_cpu = best_W.cpu().numpy()
    best_brier_cpu = best_brier.cpu().numpy()
    auc_cpu = auc_scores.cpu().numpy()
    acc_cpu = acc_scores.cpu().numpy()
    composite_cpu = composite.cpu().numpy()

    results = []
    for i, cfg in enumerate(configs):
        w_vec = best_W_cpu[:, i].tolist()
        results.append({
            "config_id": i,
            "lr": cfg["lr"],
            "l2": cfg["l2"],
            "init_strategy": cfg["meta"].get("init_strategy", "?"),
            "base_logit_init": cfg["meta"].get("base_logit_init", 0),
            "brier": round(float(best_brier_cpu[i]), 6),
            "auc": round(float(auc_cpu[i]), 6),
            "accuracy": round(float(acc_cpu[i]), 6),
            "fitness": round(float(composite_cpu[i]), 6),
            "weights": {
                "base_logit": round(w_vec[0], 6),
                "features": {fname: round(w_vec[j + 1], 6)
                             for j, fname in enumerate(FEATURE_NAMES)},
            },
        })
    return results


# ═══════════════════════════════════════════════════════════════
#  TIER SWEEP + WALK-FORWARD (from gpu_sweep — inlined)
# ═══════════════════════════════════════════════════════════════

def sweep_tiers(results: list, X: torch.Tensor, y: torch.Tensor,
                top_n: int = 50) -> list:
    """Sweep tier boundaries on top N training results (ranked by fitness)."""
    sorted_r = sorted(results, key=lambda r: r.get("fitness", r["auc"]), reverse=True)[:top_n]
    y_np = y.cpu().numpy()
    all_configs = []

    for rank, res in enumerate(sorted_r):
        w = res["weights"]
        W_vec = torch.tensor(
            [w["base_logit"]] + [w["features"].get(f, 0.0) for f in FEATURE_NAMES],
            dtype=torch.float32, device=X.device)
        preds = torch.sigmoid(X @ W_vec[1:] + W_vec[0]).cpu().numpy()

        for t1, t4 in itertools.product(TIER1_BASE, TIER4_BASE):
            if t4 >= t1:
                continue
            tiers = {"TIER_1": [], "TIER_2": [], "TIER_3": [], "TIER_4": []}
            for p, a in zip(preds, y_np):
                tier = ("TIER_1" if p >= t1 else "TIER_2" if p >= 0.50 else
                        "TIER_3" if p >= t4 else "TIER_4")
                tiers[tier].append(a)

            tier_stats = {}
            for t, vals in tiers.items():
                tier_stats[t] = {"n": len(vals), "pos_rate": round(sum(vals)/len(vals), 4) if vals else 0.0}

            t1_n = tier_stats["TIER_1"]["n"]
            t1_pos = tier_stats["TIER_1"]["pos_rate"]
            t4_n = tier_stats["TIER_4"]["n"]
            t4_pos = tier_stats["TIER_4"]["pos_rate"]

            if t1_n < 20 or t4_n < 20:
                tier_score = 0.0
            else:
                tier_score = (t1_pos * 0.4 + (1.0 - t4_pos) * 0.3 +
                              min(t1_n / 500, 1.0) * 0.15 + min(t4_n / 500, 1.0) * 0.15)

            all_configs.append({
                **res,
                "tier_1_boundary": t1,
                "tier_4_boundary": t4,
                "tiers": tier_stats,
                "tier_score": round(tier_score, 6),
                "composite_score": round(res.get("fitness", res["auc"]) * 0.5 + tier_score * 0.5, 6),
            })

    all_configs.sort(key=lambda c: c["composite_score"], reverse=True)
    return all_configs


def walkforward_validate(top_configs: list, events: list, device: torch.device,
                         top_n: int = 20, train_ratio: float = 0.70,
                         quiet: bool = False) -> list:
    """Re-train top N on 70%, test on 30%."""
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

    top = sorted(top_configs, key=lambda c: c.get("composite_score", c.get("auc", 0)),
                 reverse=True)[:top_n]

    configs = []
    for r in top:
        configs.append({
            "lr": r["lr"], "l2": r["l2"],
            "init_weights": [r["weights"]["base_logit"]] +
                            [r["weights"]["features"].get(f, 0.0) for f in FEATURE_NAMES],
            "meta": {"init_strategy": r.get("init_strategy", "?"),
                     "base_logit_init": r.get("base_logit_init", 0)},
        })

    train_results = gpu_train_batch(X_train, y_train, configs,
                                     max_epochs=5000, patience=300,
                                     log_interval=2000, quiet=quiet)

    validated = []
    for i, (tr, orig) in enumerate(zip(train_results, top)):
        w = tr["weights"]
        W_vec = torch.tensor(
            [w["base_logit"]] + [w["features"].get(f, 0.0) for f in FEATURE_NAMES],
            dtype=torch.float32, device=device)
        tp = torch.sigmoid(X_test @ W_vec[1:] + W_vec[0])

        test_brier = ((tp - y_test) ** 2).mean().item()
        test_acc = ((tp >= 0.5).float() == y_test).float().mean().item()

        pp = tp[y_test == 1.0]
        pn = tp[y_test == 0.0]
        if len(pp) > 0 and len(pn) > 0:
            c = (pp.unsqueeze(1) > pn.unsqueeze(0)).float()
            t = (pp.unsqueeze(1) == pn.unsqueeze(0)).float()
            test_auc = ((c.sum() + 0.5 * t.sum()) / (len(pp) * len(pn))).item()
        else:
            test_auc = 0.5

        # Compute tiers on test set
        tp_np = tp.cpu().numpy()
        yt_np = y_test.cpu().numpy()
        t1b = orig.get("tier_1_boundary", 0.70)
        t4b = orig.get("tier_4_boundary", 0.20)
        tiers = {"TIER_1": [], "TIER_2": [], "TIER_3": [], "TIER_4": []}
        for p, a in zip(tp_np, yt_np):
            tier = ("TIER_1" if p >= t1b else "TIER_2" if p >= 0.50 else
                    "TIER_3" if p >= t4b else "TIER_4")
            tiers[tier].append(a)
        tier_stats = {}
        for tn, vals in tiers.items():
            tier_stats[tn] = {"n": len(vals), "pos_rate": round(sum(vals)/len(vals), 4) if vals else 0.0}

        validated.append({
            "rank": i + 1,
            "lr": tr["lr"], "l2": tr["l2"],
            "init_strategy": tr["init_strategy"],
            "train_brier": tr["brier"], "train_auc": tr["auc"],
            "test_brier": round(test_brier, 6),
            "test_auc": round(test_auc, 6),
            "test_accuracy": round(test_acc, 6),
            "test_n": len(test_ev), "train_n": len(train_ev),
            "overfit_delta": round(tr["auc"] - test_auc, 4),
            "tier_1_boundary": t1b, "tier_4_boundary": t4b,
            "tiers": tier_stats,
            "weights": tr["weights"],
        })

    validated.sort(key=lambda v: v["test_auc"], reverse=True)
    return validated


# ═══════════════════════════════════════════════════════════════
#  PERPETUAL ENGINE — The main loop
# ═══════════════════════════════════════════════════════════════

class GungnirPerpetualGPU:
    """
    Runs nonstop. Each cycle:
    1. Generate configs (with jitter for exploration)
    2. GPU batch train all models in parallel
    3. Tier boundary sweep on top 50
    4. Walk-forward validate top 20
    5. Compare champion vs best ever
    6. Log everything
    7. Sleep briefly, then repeat
    """

    def __init__(self, data_dir: str = None, combos_per_cycle: int = 5000,
                 max_epochs: int = 5000, patience: int = 300):
        self.data_dir = data_dir or get_data_dir()
        self.combos = combos_per_cycle
        self.max_epochs = max_epochs
        self.patience = patience

        # Persistent state
        self.best_tracker = BestConfigTracker(os.path.join(self.data_dir, "best_config.json"))
        self.leaderboard = Leaderboard(os.path.join(self.data_dir, "top_10_configs.json"))
        self.history = RunHistory(os.path.join(self.data_dir, "run_history.jsonl"))
        self.wf_log = RunHistory(os.path.join(self.data_dir, "walkforward_log.jsonl"))

        # Device
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            gpu = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / 1e9
            print(f"  GPU: {gpu} ({vram:.1f} GB VRAM)")
        else:
            self.device = torch.device("cpu")
            print(f"  Device: CPU (no CUDA)")

        # Load data once
        print("  Loading Phase readout data...")
        events = load_phase_events(verbose=True)
        self.events = precompute_features(events, verbose=True)
        resolved = [e for e in self.events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        self.N = len(resolved)

        # Build full-data tensors
        X_list = [[float(e["features"].get(f, 0.0)) for f in FEATURE_NAMES] for e in resolved]
        y_list = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in resolved]
        self.X = torch.tensor(X_list, dtype=torch.float32, device=self.device)
        self.y = torch.tensor(y_list, dtype=torch.float32, device=self.device)

        print(f"  Data: {self.N} events × {len(FEATURE_NAMES)} features on {self.device}")
        print(f"  Positive rate: {self.y.mean().item():.3f}")

        # Load platform weights (best > honed > initial)
        self.platform = self._load_platform()
        if self.platform:
            src = self.platform.get("_source", "unknown")
            base = self.platform.get("base_logit", 0)
            n_nonzero = sum(1 for v in self.platform.get("features", {}).values() if abs(v) > 0.001)
            print(f"  Platform:   {src} (base_logit={base:.4f}, {n_nonzero} active features)")
            print(f"  ✓ All cycles will build from this platform — never starting from scratch")
        else:
            print(f"  Platform:   COLD START (no saved weights found)")
            print(f"  First cycle will use Gungnir v4.0 initial weights as seed")

        self.cycle_count = self.history.count()

    def _load_platform(self) -> dict:
        """
        Load the best available weights as the platform for all training.
        Priority: best_config.json > model_weights.json > honed_weights.json > initial.
        VALIDATES that loaded weights have actual non-zero features.
        """

        def _validate(w: dict, label: str) -> bool:
            """Check that weights dict is usable."""
            if not w or not isinstance(w, dict):
                print(f"    ✗ {label}: empty or invalid")
                return False
            feats = w.get("features")
            if not feats or not isinstance(feats, dict):
                print(f"    ✗ {label}: no 'features' key")
                return False
            n_active = sum(1 for v in feats.values() if abs(v) > 0.001)
            if n_active == 0:
                print(f"    ✗ {label}: all weights are zero — skipping")
                return False
            return True

        # 1. Best config from prior GPU sweeps (highest priority)
        best_path = os.path.join(self.data_dir, "best_config.json")
        if os.path.exists(best_path):
            try:
                with open(best_path, "r") as f:
                    best = json.load(f)
                if best and best.get("weights") and _validate(best["weights"], "best_config.json"):
                    w = deepcopy(best["weights"])
                    auc_str = best.get('test_auc', best.get('auc', '?'))
                    cycle_str = best.get('cycle', '?')
                    w["_source"] = f"best_config.json (AUC={auc_str}, cycle={cycle_str})"
                    return w
            except (json.JSONDecodeError, KeyError) as e:
                print(f"    ✗ best_config.json corrupted: {e}")

        # 2. Saved model weights from CPU runner / prior GPU runs
        mw_path = os.path.join(self.data_dir, "model_weights.json")
        if os.path.exists(mw_path):
            try:
                with open(mw_path, "r") as f:
                    w = json.load(f)
                if _validate(w, "model_weights.json"):
                    w = deepcopy(w)
                    w["_source"] = "model_weights.json"
                    return w
            except (json.JSONDecodeError, KeyError) as e:
                print(f"    ✗ model_weights.json corrupted: {e}")

        # 3. Honed weights file (from one-shot honing)
        candidates = [
            "gungnir_honed_weights.json",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "gungnir_honed_weights.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    with open(c, "r") as f:
                        w = json.load(f)
                    if _validate(w, c):
                        w = deepcopy(w)
                        w["_source"] = f"honed_weights ({os.path.basename(c)})"
                        return w
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"    ✗ {c} corrupted: {e}")

        # 4. Fall back to Gungnir v4.0 initial weights (guaranteed valid)
        w = deepcopy(INITIAL_WEIGHTS)
        w["_source"] = "INITIAL_WEIGHTS (Gungnir v4.0 — cold start)"
        return w

    def _generate_configs(self, cycle: int) -> list:
        """
        Generate configs for this cycle.
        80% exploit current platform, 15% semi-exploit, 5% wild exploration.
        Every cycle jitters the lr/l2/base_logit grids for fresh territory.
        """
        seed = cycle * 1000 + int(time.time()) % 1000

        lr_grid = jitter_grid(LR_BASE, 0.15, seed)
        l2_grid = jitter_grid(L2_BASE, 0.15, seed + 1)
        bl_grid = jitter_grid(BLOGIT_BASE, 0.10, seed + 2)

        # If platform has a known good base_logit, concentrate around it
        if self.platform and self.platform.get("base_logit") is not None:
            best_bl = self.platform["base_logit"]
            # Add tight cluster around the best base_logit
            rng = random.Random(seed + 3)
            for _ in range(5):
                bl_grid.append(round(best_bl + rng.gauss(0, 0.05), 6))
            bl_grid = sorted(set(bl_grid))

        # Build configs using strategy distribution
        rng = random.Random(seed + 4)
        strategies = list(STRATEGY_DISTRIBUTION.keys())
        strat_weights = [STRATEGY_DISTRIBUTION[s] for s in strategies]

        # Total combos from grid
        grid_combos = list(itertools.product(lr_grid, l2_grid, bl_grid))
        rng.shuffle(grid_combos)

        configs = []
        for lr, l2, bl in grid_combos:
            # Pick strategy based on distribution
            strat = rng.choices(strategies, weights=strat_weights, k=1)[0]
            init_w = build_init_weights(strat, bl, self.platform)
            configs.append({
                "lr": lr, "l2": l2, "init_weights": init_w,
                "meta": {"init_strategy": strat, "base_logit_init": bl},
            })

        # Sample if too many
        if len(configs) > self.combos:
            configs = rng.sample(configs, self.combos)

        # Ensure at least some exact platform configs (the "control group")
        n_exact = max(50, self.combos // 20)
        for lr, l2 in rng.sample(list(itertools.product(lr_grid, l2_grid)),
                                  min(n_exact, len(lr_grid) * len(l2_grid))):
            bl = self.platform.get("base_logit", 0.25) if self.platform else 0.25
            init_w = build_init_weights("platform", bl, self.platform)
            configs.append({
                "lr": lr, "l2": l2, "init_weights": init_w,
                "meta": {"init_strategy": "platform", "base_logit_init": bl},
            })

        # Final trim
        if len(configs) > self.combos:
            configs = configs[:self.combos]

        # Log strategy distribution for this cycle
        strat_counts = {}
        for c in configs:
            s = c["meta"]["init_strategy"]
            strat_counts[s] = strat_counts.get(s, 0) + 1
        platform_pct = sum(v for k, v in strat_counts.items()
                           if k not in ("zero", "random", "initial")) / len(configs) * 100
        strat_str = " | ".join(f"{k}:{v}" for k, v in sorted(strat_counts.items(), key=lambda x: -x[1]))
        print(f"    {len(configs)} configs — {platform_pct:.0f}% from platform")
        print(f"    Mix: {strat_str}")

        return configs

    def run_cycle(self, cycle: int) -> dict:
        """Run one complete sweep cycle."""
        t0 = time.time()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n  {'━'*70}")
        print(f"  CYCLE #{cycle}  |  {ts}")
        print(f"  {'━'*70}")

        # 1. Generate configs
        configs = self._generate_configs(cycle)

        # Compute strategy mix for logging
        strat_counts = {}
        for c in configs:
            s = c["meta"]["init_strategy"]
            strat_counts[s] = strat_counts.get(s, 0) + 1
        platform_pct = sum(v for k, v in strat_counts.items()
                           if k not in ("zero", "random", "initial")) / max(len(configs), 1) * 100

        # 2. GPU train
        print(f"  [2/4] GPU batch training ({len(configs)} models, {platform_pct:.0f}% from platform)...")
        results = gpu_train_batch(self.X, self.y, configs,
                                   max_epochs=self.max_epochs,
                                   patience=self.patience,
                                   log_interval=1000)
        results.sort(key=lambda r: r.get("fitness", r["auc"]), reverse=True)
        top_auc = results[0]["auc"]
        top_brier = results[0]["brier"]
        top_fitness = results[0].get("fitness", 0)
        print(f"    Top fitness: {top_fitness:.6f}  (AUC={top_auc:.6f}  Brier={top_brier:.6f})")

        # 3. Tier sweep
        print(f"  [3/4] Tier boundary sweep (top 50)...")
        tier_configs = sweep_tiers(results, self.X, self.y, top_n=50)
        print(f"    {len(tier_configs)} tier configs evaluated")

        # 4. Walk-forward
        print(f"  [4/4] Walk-forward validation (top 20)...")
        validated = walkforward_validate(tier_configs, self.events,
                                          self.device, top_n=20, quiet=True)

        # Results
        champion = validated[0] if validated else None
        is_new_best = False

        if champion:
            champion["cycle"] = str(cycle)
            is_new_best = self.best_tracker.check_and_update(champion)
            rank = self.leaderboard.submit(champion)

            # Log walk-forward results
            for v in validated[:5]:
                v["cycle"] = str(cycle)
                self.wf_log.log(v)

        elapsed = time.time() - t0

        # Update platform for next cycle — always build from the best
        if self.best_tracker.best and self.best_tracker.best.get("weights"):
            self.platform = deepcopy(self.best_tracker.best["weights"])
            self.platform["_source"] = f"best_config.json (cycle {cycle})"
            # Also save as model_weights.json for the CPU runner to pick up
            weights_path = os.path.join(self.data_dir, "model_weights.json")
            clean_weights = {k: v for k, v in self.platform.items() if k != "_source"}
            with open(weights_path, "w") as f:
                json.dump(clean_weights, f, indent=2)

        # Log cycle
        cycle_log = {
            "cycle": cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "configs_trained": len(configs),
            "tier_configs": len(tier_configs),
            "top_train_auc": top_auc,
            "top_train_brier": top_brier,
            "top_train_fitness": top_fitness,
            "platform_source": self.platform.get("_source", "unknown"),
            "platform_pct": round(platform_pct, 1),
            "strategy_mix": strat_counts,
        }
        if champion:
            cycle_log.update({
                "champion_test_auc": champion["test_auc"],
                "champion_test_brier": champion["test_brier"],
                "champion_overfit": champion["overfit_delta"],
                "is_new_best": is_new_best,
                "leaderboard_rank": rank,
                "champion_lr": champion["lr"],
                "champion_l2": champion["l2"],
                "champion_init": champion.get("init_strategy", "?"),
            })

        self.history.log(cycle_log)

        # Print summary
        star = "  ★ NEW ALL-TIME BEST!" if is_new_best else ""
        print(f"\n  ┌─ CYCLE #{cycle} RESULT ──────────────────────────────┐")
        if champion:
            print(f"  │  Test AUC:    {champion['test_auc']:.6f}   "
                  f"(train: {champion['train_auc']:.6f})       │")
            print(f"  │  Test Brier:  {champion['test_brier']:.6f}   "
                  f"(overfit: {champion['overfit_delta']:+.4f})       │")
            print(f"  │  Config:      lr={champion['lr']} l2={champion['l2']}"
                  f"{'':>13s}│")
            # Tier stats
            for tn in ["TIER_1", "TIER_4"]:
                ts = champion.get("tiers", {}).get(tn, {})
                if ts.get("n", 0) > 0:
                    print(f"  │  {tn}:      n={ts['n']:>4}  pos={ts['pos_rate']:.1%}"
                          f"{'':>22s}│")
        print(f"  │  Time:        {elapsed:.1f}s  ({len(configs)} models)"
              f"{'':>17s}│")
        print(f"  │  {star:50s}│")
        print(f"  └──────────────────────────────────────────────────┘")

        return cycle_log

    def run_perpetual(self, max_cycles: int = None, pause_seconds: float = 5.0):
        """Run forever (or N cycles). The overnight grinder."""
        start_cycle = self.cycle_count + 1

        print(f"\n  {'═'*70}")
        print(f"  ⚔️  GUNGNIR PERPETUAL GPU ENGINE v{__version__}")
        print(f"  {'═'*70}")
        print(f"  Mode:       {'PERPETUAL' if max_cycles is None else f'{max_cycles} cycles'}")
        print(f"  Combos:     {self.combos}/cycle")
        print(f"  Epochs:     {self.max_epochs}/model")
        print(f"  Patience:   {self.patience}")
        print(f"  Data:       {self.N} events")
        print(f"  Device:     {self.device}")
        print(f"  Output:     {self.data_dir}/")

        # Resume state
        prior = start_cycle - 1
        if prior > 0:
            print(f"\n  ╔══════════════════════════════════════════════════╗")
            print(f"  ║  RESUMING from cycle {prior:>5d}                       ║")
            print(f"  ╚══════════════════════════════════════════════════╝")
            print(f"  Prior cycles:  {prior}")
            print(f"  Models tested: ~{prior * self.combos:,}")
        else:
            print(f"\n  FIRST RUN — starting from scratch")

        if self.best_tracker.best:
            b = self.best_tracker.best
            auc = b.get('test_auc', b.get('auc', 0))
            brier = b.get('test_brier', b.get('brier', 0))
            crowned = b.get('crowned_at', '?')[:19]
            print(f"  Best so far: AUC={auc:.6f}  Brier={brier:.6f}  (cycle {b.get('cycle','?')}, {crowned})")
        else:
            print(f"  Best so far: (none — this is the first sweep)")

        src = self.platform.get("_source", "unknown") if self.platform else "none"
        print(f"  Platform:    {src}")
        print(f"\n  Press Ctrl+C to stop. Progress saved after EVERY cycle.\n")

        cycle = start_cycle
        total_t0 = time.time()

        try:
            while True:
                if max_cycles and (cycle - start_cycle) >= max_cycles:
                    break

                self.run_cycle(cycle)
                cycle += 1

                # Brief pause to let GPU cool
                if pause_seconds > 0:
                    time.sleep(pause_seconds)

        except KeyboardInterrupt:
            print(f"\n\n  Interrupted after {cycle - start_cycle} cycles "
                  f"({(time.time()-total_t0)/60:.1f} min)")

        # Final summary
        total_elapsed = time.time() - total_t0
        total_cycles = cycle - start_cycle
        print(f"\n  {'═'*70}")
        print(f"  SESSION SUMMARY")
        print(f"  {'═'*70}")
        print(f"  Cycles:      {total_cycles}")
        print(f"  Total time:  {total_elapsed/60:.1f} min ({total_elapsed/3600:.1f} hr)")
        print(f"  Models:      ~{total_cycles * self.combos:,}")
        if total_cycles > 0:
            print(f"  Per cycle:   {total_elapsed/total_cycles:.1f}s avg")

        self.best_tracker.print_best()
        self.leaderboard.print_board()


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Gungnir Perpetual GPU Runner v2.0")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Max cycles (default: run forever)")
    parser.add_argument("--combos", type=int, default=5000,
                        help="Training combos per cycle (default: 5000)")
    parser.add_argument("--epochs", type=int, default=5000,
                        help="Max epochs per model (default: 5000)")
    parser.add_argument("--patience", type=int, default=300,
                        help="Early stopping patience (default: 300)")
    parser.add_argument("--pause", type=float, default=5.0,
                        help="Seconds between cycles (default: 5)")
    parser.add_argument("--data-dir", default=None, help="Data directory")
    parser.add_argument("--best", action="store_true", help="Show best config and exit")
    parser.add_argument("--leaderboard", action="store_true", help="Show top 10 and exit")
    parser.add_argument("--history", action="store_true", help="Show run history and exit")
    parser.add_argument("--cpu", action="store_true", help="Force CPU")
    args = parser.parse_args()

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    data_dir = args.data_dir or get_data_dir()

    # Quick lookups (no data loading needed)
    if args.best:
        bt = BestConfigTracker(os.path.join(data_dir, "best_config.json"))
        bt.print_best()
        return
    if args.leaderboard:
        lb = Leaderboard(os.path.join(data_dir, "top_10_configs.json"))
        lb.print_board()
        return
    if args.history:
        rh = RunHistory(os.path.join(data_dir, "run_history.jsonl"))
        entries = rh.read_all()
        print(f"\n  Run history: {len(entries)} cycles")
        print(f"  {'Cycle':>5s} │ {'Test AUC':>8s} │ {'Brier':>6s} │ {'Overfit':>7s} │ "
              f"{'Time':>5s} │ {'Best?':>5s} │ {'Timestamp':>19s}")
        print(f"  {'─'*5}─┼─{'─'*8}─┼─{'─'*6}─┼─{'─'*7}─┼─{'─'*5}─┼─{'─'*5}─┼─{'─'*19}")
        for e in entries[-50:]:
            star = "★" if e.get("is_new_best") else ""
            print(f"  {e.get('cycle','?'):>5} │ "
                  f"{e.get('champion_test_auc',0):>.6f} │ "
                  f"{e.get('champion_test_brier',0):>.4f} │ "
                  f"{e.get('champion_overfit',0):>+.4f} │ "
                  f"{e.get('elapsed_seconds',0):>5.0f}s │ "
                  f"{star:>5s} │ "
                  f"{e.get('timestamp','')[:19]}")
        return

    # Full run
    engine = GungnirPerpetualGPU(
        data_dir=data_dir,
        combos_per_cycle=args.combos,
        max_epochs=args.epochs,
        patience=args.patience,
    )
    engine.run_perpetual(max_cycles=args.cycles, pause_seconds=args.pause)


if __name__ == "__main__":
    main()
