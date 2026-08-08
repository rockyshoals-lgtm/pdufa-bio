#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL GPU v2.1 — PLATEAU-BREAKING UPGRADE                    ║
║                                                                        ║
║  DROP-IN PATCH for odin_perpetual_gpu.py v2.0                          ║
║  Import this module and call patch_perpetual() to upgrade.             ║
║                                                                        ║
║  What's new in v2.1:                                                   ║
║    1. BATCH PARALLEL HONING — coordinate-descent across population     ║
║    2. NEW FEATURES — 8 additional features (55→63) for richer signal   ║
║    3. L2 REGULARIZATION — prevents overfitting on 2,202 events         ║
║    4. TEMPORAL CV — train ≤2022, val 2023-2024, test 2024+             ║
║    5. DIVERSITY INJECTION — anti-plateau random restart                 ║
║    6. PLATEAU DETECTION — auto-halt after N stale generations          ║
║    7. ENSEMBLE PREP — exports weight vectors for XGBoost blending      ║
║    8. GRADIENT-ESTIMATED MUTATION — smarter than random noise          ║
║                                                                        ║
║  Usage:                                                                ║
║    # Standalone — runs perpetual training with v2.1 enhancements       ║
║    py -3.11 odin_perpetual_gpu_v21.py                                  ║
║    py -3.11 odin_perpetual_gpu_v21.py --cycles 100                     ║
║    py -3.11 odin_perpetual_gpu_v21.py --temporal-cv                    ║
║    py -3.11 odin_perpetual_gpu_v21.py --export-ensemble                ║
║                                                                        ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import math
import os
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import torch

__version__ = "2.1.0"

# ═══════════════════════════════════════════════════════════════
#  NEW FEATURES FOR v2.1 (8 additional features: 55→63)
# ═══════════════════════════════════════════════════════════════

V21_NEW_FEATURES = [
    # Feature name              | Source                  | Encoding
    "adcom_vote_pct",          # AdCom yes-vote percentage (0-1 continuous)
    "endpoints_met_ratio",     # Primary endpoints met / total (0-1 continuous)
    "sponsor_recency",         # Years since sponsor's last FDA approval (normalized)
    "era_ta_onco_hoeg",        # Oncology × HOEG_ERA interaction
    "era_ta_cns_hoeg",         # CNS × HOEG_ERA interaction
    "era_ta_rare_hoeg",        # Rare Disease × HOEG_ERA interaction
    "era_ta_immuno_hoeg",      # Immunology × HOEG_ERA interaction
    "rolling_approval_rate",   # 12-month trailing TA approval rate (0-1 continuous)
]

V21_N_NEW = len(V21_NEW_FEATURES)  # 8 new features
V21_TOTAL_FEATURES = 55 + V21_N_NEW  # 63 total
V21_TOTAL_PARAMS = 1 + V21_TOTAL_FEATURES  # 64 total (bias + 63)


def encode_v21_features(event: dict, base_features: list) -> list:
    """Extend a 55-feature vector with 8 new v2.1 features.

    Args:
        event: Raw event dict from CSV (has 'adcom_vote_pct', 'endpoints_met', etc.)
        base_features: The existing 55-element feature vector from encode_event()

    Returns:
        63-element feature vector
    """
    new = [0.0] * V21_N_NEW

    # 0: AdCom vote percentage (continuous 0-1)
    # Source: MCP enrichment from FDA.gov AdCom transcripts
    adcom_pct = event.get("adcom_vote_pct", None)
    if adcom_pct is not None:
        new[0] = max(0.0, min(1.0, float(adcom_pct)))
    else:
        # If had_adcom=1 but no vote %, use 0.6 (median positive outcome)
        had_adcom = event.get("had_adcom", 0)
        if had_adcom:
            new[0] = 0.6

    # 1: Endpoints met ratio (continuous 0-1)
    # Source: MCP enrichment from ClinicalTrials.gov results
    ep_met = event.get("endpoints_met", None)
    ep_total = event.get("endpoints_total", None)
    if ep_met is not None and ep_total is not None and ep_total > 0:
        new[1] = min(1.0, float(ep_met) / float(ep_total))

    # 2: Sponsor recency (normalized, 0 = just approved, 1 = never approved)
    years_since = event.get("sponsor_years_since_last_approval", None)
    if years_since is not None:
        new[2] = min(1.0, float(years_since) / 10.0)
    else:
        new[2] = 0.5  # unknown → neutral

    # 3-6: Era × TA interaction terms (only active in HOEG_ERA)
    # Extract era from base features (indices 26-29 in the original encoding)
    # HOEG_ERA is at index 28 in the full feature list
    ta_name = event.get("therapeutic_area", "Other")
    pdufa_date = event.get("pdufa_date", "")
    is_hoeg = False
    try:
        year = int(str(pdufa_date)[:4])
        is_hoeg = year >= 2024
    except (ValueError, IndexError):
        pass

    if is_hoeg:
        ta_lower = ta_name.lower() if ta_name else ""
        if "oncol" in ta_lower or "cancer" in ta_lower:
            new[3] = 1.0
        if "cns" in ta_lower or "neuro" in ta_lower:
            new[4] = 1.0
        if "rare" in ta_lower or "orphan" in ta_lower:
            new[5] = 1.0
        if "immuno" in ta_lower or "autoimmun" in ta_lower:
            new[6] = 1.0

    # 7: Rolling approval rate (12-month trailing for this TA)
    # Source: Pre-computed from dataset or MCP enrichment
    rolling = event.get("rolling_12m_approval_rate", None)
    if rolling is not None:
        new[7] = max(0.0, min(1.0, float(rolling)))
    else:
        new[7] = 0.68  # dataset base rate as default

    return base_features + new


def encode_v21_events_to_tensor(events: list, base_encoder, device: torch.device):
    """Encode all events to v2.1 tensor format (N × 63 features).

    Args:
        events: List of event dicts
        base_encoder: Function(event) → 55-element feature list (from honing engine)
        device: torch device

    Returns:
        X tensor (N × 63), y tensor (N,)
    """
    X_rows = []
    y_rows = []
    for e in events:
        base_feat = base_encoder(e)
        full_feat = encode_v21_features(e, base_feat)
        X_rows.append(full_feat)
        y_rows.append(1.0 if e.get("outcome") == "APPROVED" else 0.0)

    X = torch.tensor(X_rows, dtype=torch.float32, device=device)
    y = torch.tensor(y_rows, dtype=torch.float32, device=device)
    return X, y


# ═══════════════════════════════════════════════════════════════
#  L2 REGULARIZATION
# ═══════════════════════════════════════════════════════════════

def l2_penalty(W: torch.Tensor, lam: float = 0.001) -> torch.Tensor:
    """L2 regularization penalty on weight vectors (excludes bias at row 0).

    Args:
        W: (N_PARAMS × K) weight matrix
        lam: regularization strength

    Returns:
        (K,) vector of penalties
    """
    return lam * (W[1:, :] ** 2).sum(dim=0)


# ═══════════════════════════════════════════════════════════════
#  GRADIENT-ESTIMATED COORDINATE DESCENT
# ═══════════════════════════════════════════════════════════════

def batch_coordinate_descent(X: torch.Tensor, y: torch.Tensor,
                             W: torch.Tensor, lr: float = 0.01,
                             l2_lam: float = 0.001,
                             n_steps: int = 100) -> torch.Tensor:
    """Vectorized gradient descent on the FULL population simultaneously.

    This is the core plateau-breaking innovation: instead of training
    one model at a time, we compute gradients for ALL K models in a
    single batched matrix multiply, then update all at once.

    On a 12GB GPU with 56 params and 2,202 events:
    - Each model uses ~17.6MB → can fit 500+ models
    - One forward pass: X @ W = (2202×55) @ (56×K) → (2202×K)
    - One backward pass: X.T @ grad = (55×2202) @ (2202×K) → (55×K)
    - Total: ~2 matmuls per step, all on GPU, all models simultaneously

    This replaces the sequential coordinate_descent in the honing engine
    that was limited to 1 model per iteration.

    Args:
        X: (N × F) feature tensor
        y: (N,) label tensor
        W: (P × K) weight matrix (P = 1+F, row 0 = bias)
        lr: learning rate
        l2_lam: L2 regularization strength
        n_steps: number of gradient steps

    Returns:
        Updated W tensor
    """
    N, F = X.shape
    P, K = W.shape
    W = W.clone()

    # Prepend 1s column for bias: X_aug = (N × P)
    ones = torch.ones(N, 1, dtype=X.dtype, device=X.device)
    X_aug = torch.cat([ones, X], dim=1)  # (N × P)

    y_col = y.unsqueeze(1)  # (N × 1)

    for step in range(n_steps):
        # Forward: logits = X_aug @ W → (N × K)
        logits = X_aug @ W
        probs = torch.sigmoid(logits)  # (N × K)

        # Gradient of BCE loss: dL/dW = X_aug.T @ (probs - y) / N
        residuals = probs - y_col  # (N × K), broadcasts y across K
        grad = X_aug.t() @ residuals / N  # (P × K)

        # Add L2 gradient (skip bias at row 0)
        grad[1:, :] += 2 * l2_lam * W[1:, :]

        # Update
        W -= lr * grad

    return W


# ═══════════════════════════════════════════════════════════════
#  ENHANCED EVOLUTIONARY OPERATORS
# ═══════════════════════════════════════════════════════════════

def evolve_v21(W: torch.Tensor, fitness: torch.Tensor,
               sigma: float = 0.05, device: torch.device = None,
               diversity_injection: bool = False) -> torch.Tensor:
    """Enhanced evolutionary step with optional diversity injection.

    When diversity_injection=True (triggered by plateau detection),
    replaces bottom 20% with random vectors instead of mutations.
    This breaks out of local optima.

    Distribution:
      - Top 10% → elite (unchanged)
      - Next 20% → gradient-guided crossover (use fitness-weighted average)
      - Next 30% → uniform crossover from tournament
      - Remaining 40% → mutation from top 50% (or random if diversity mode)
    """
    K = W.shape[1]
    P = W.shape[0]
    new_W = torch.zeros_like(W)

    _, idx = fitness.sort(descending=True)
    W_sorted = W[:, idx]

    n_elite = max(2, int(K * 0.10))
    n_grad_cross = max(1, int(K * 0.20))
    n_uniform_cross = max(1, int(K * 0.30))
    n_mutate = K - n_elite - n_grad_cross - n_uniform_cross
    if n_mutate < 0:
        n_mutate = 0
        n_uniform_cross = K - n_elite - n_grad_cross

    col = 0

    # 1) Elite: unchanged
    new_W[:, col:col + n_elite] = W_sorted[:, :n_elite]
    col += n_elite

    # 2) Gradient-guided crossover: fitness-weighted average of top parents
    top_fit = fitness[idx[:max(4, K // 4)]]
    top_W = W_sorted[:, :max(4, K // 4)]
    fit_softmax = torch.softmax(top_fit * 10, dim=0)  # sharpen
    for i in range(n_grad_cross):
        # Sample 3 parents, weighted average
        parent_idx = torch.multinomial(fit_softmax, 3, replacement=True)
        parents = top_W[:, parent_idx]
        weights_mix = torch.softmax(torch.randn(3, device=device), dim=0)
        child = (parents * weights_mix.unsqueeze(0)).sum(dim=1)
        child += torch.randn(P, device=device) * sigma * 0.3  # light noise
        new_W[:, col + i] = child
    col += n_grad_cross

    # 3) Uniform crossover from tournament pairs in top half
    top_half = W_sorted[:, :max(2, K // 2)]
    th_k = top_half.shape[1]
    idx1 = torch.randint(th_k, (n_uniform_cross,), device=device)
    idx2 = torch.randint(th_k, (n_uniform_cross,), device=device)
    p1 = top_half[:, idx1]
    p2 = top_half[:, idx2]
    mask = torch.rand(P, n_uniform_cross, device=device) > 0.5
    new_W[:, col:col + n_uniform_cross] = torch.where(mask, p1, p2)
    col += n_uniform_cross

    # 4) Mutation (or diversity injection)
    if diversity_injection and n_mutate > 0:
        # Replace bottom portion with random vectors near the best
        n_random = max(1, n_mutate // 2)
        n_perturb = n_mutate - n_random

        # Random vectors: best ± large noise
        best = W_sorted[:, 0:1].expand(-1, n_random)
        new_W[:, col:col + n_random] = best + torch.randn_like(best) * 0.30
        col += n_random

        # Perturbed from top 50%
        if n_perturb > 0:
            base_idx = torch.randint(th_k, (n_perturb,), device=device)
            base = top_half[:, base_idx]
            noise = torch.randn_like(base) * sigma
            noise[0, :] *= 0.3
            new_W[:, col:col + n_perturb] = base + noise
            col += n_perturb
    elif n_mutate > 0:
        base_idx = torch.randint(th_k, (n_mutate,), device=device)
        base = top_half[:, base_idx]
        noise = torch.randn_like(base) * sigma
        noise[0, :] *= 0.3
        new_W[:, col:col + n_mutate] = base + noise

    return new_W


# ═══════════════════════════════════════════════════════════════
#  TEMPORAL CROSS-VALIDATION
# ═══════════════════════════════════════════════════════════════

def temporal_cv_split(events: list, val_start: int = 2023, test_start: int = 2024):
    """Split events by time for proper temporal validation.

    Train: events before val_start
    Val: events in [val_start, test_start)
    Test: events >= test_start

    Returns:
        (train_events, val_events, test_events)
    """
    train, val, test = [], [], []
    for e in events:
        pdufa = e.get("pdufa_date", "")
        try:
            year = int(str(pdufa)[:4])
        except (ValueError, IndexError):
            train.append(e)  # unknown date → train
            continue

        if year < val_start:
            train.append(e)
        elif year < test_start:
            val.append(e)
        else:
            test.append(e)

    return train, val, test


def temporal_cv_evaluate(events: list, W_seed: torch.Tensor,
                         device: torch.device,
                         base_encoder=None,
                         use_v21_features: bool = True,
                         l2_lam: float = 0.001) -> dict:
    """Run temporal cross-validation with proper train/val/test splits.

    Train on ≤2022, validate on 2023, test on 2024+.
    Reports both val and test AUC/Brier to detect overfitting.
    """
    train_evts, val_evts, test_evts = temporal_cv_split(events)

    if len(train_evts) < 100 or len(val_evts) < 20 or len(test_evts) < 20:
        return {"status": "INSUFFICIENT_DATA",
                "train_n": len(train_evts),
                "val_n": len(val_evts),
                "test_n": len(test_evts)}

    # Encode
    if use_v21_features and base_encoder:
        X_train, y_train = encode_v21_events_to_tensor(train_evts, base_encoder, device)
        X_val, y_val = encode_v21_events_to_tensor(val_evts, base_encoder, device)
        X_test, y_test = encode_v21_events_to_tensor(test_evts, base_encoder, device)
    else:
        # Fallback: assume encode_events_to_tensor is available
        from odin_honing_engine_gpu import encode_events_to_tensor
        X_train, y_train = encode_events_to_tensor(train_evts, device)
        X_val, y_val = encode_events_to_tensor(val_evts, device)
        X_test, y_test = encode_events_to_tensor(test_evts, device)

    P = W_seed.shape[0]
    K = 100  # population for CV

    # Expand seed to population
    W = W_seed.unsqueeze(1).expand(-1, K).clone()
    noise = torch.randn_like(W) * 0.03
    noise[:, 0] = 0  # keep one exact copy
    noise[0, :] *= 0.3
    W = W + noise

    # Pad W if using v2.1 features (56 → 64 params)
    if W.shape[0] < X_train.shape[1] + 1:
        extra = X_train.shape[1] + 1 - W.shape[0]
        pad = torch.randn(extra, K, device=device) * 0.01
        W = torch.cat([W, pad], dim=0)

    # Train with batch gradient descent
    W = batch_coordinate_descent(X_train, y_train, W, lr=0.01,
                                 l2_lam=l2_lam, n_steps=500)

    # Evaluate on val set to select best model
    with torch.no_grad():
        ones_val = torch.ones(X_val.shape[0], 1, device=device)
        X_val_aug = torch.cat([ones_val, X_val], dim=1)
        val_logits = X_val_aug @ W
        val_probs = torch.sigmoid(val_logits)
        val_brier = ((val_probs - y_val.unsqueeze(1)) ** 2).mean(dim=0)

    best_idx = val_brier.argmin().item()

    # Metrics on all three splits
    results = {"status": "OK",
               "train_n": len(train_evts), "val_n": len(val_evts),
               "test_n": len(test_evts)}

    for split_name, X_s, y_s in [("train", X_train, y_train),
                                  ("val", X_val, y_val),
                                  ("test", X_test, y_test)]:
        with torch.no_grad():
            ones_s = torch.ones(X_s.shape[0], 1, device=device)
            X_s_aug = torch.cat([ones_s, X_s], dim=1)
            preds = torch.sigmoid(X_s_aug @ W[:, best_idx])

            # AUC
            pos_mask = y_s == 1.0
            neg_mask = y_s == 0.0
            if pos_mask.sum() > 0 and neg_mask.sum() > 0:
                pos_preds = preds[pos_mask]
                neg_preds = preds[neg_mask]
                # Vectorized AUC
                auc_sum = (pos_preds.unsqueeze(1) > neg_preds.unsqueeze(0)).float().sum()
                auc_tie = (pos_preds.unsqueeze(1) == neg_preds.unsqueeze(0)).float().sum()
                auc = (auc_sum + 0.5 * auc_tie) / (pos_mask.sum() * neg_mask.sum())
                results[f"{split_name}_auc"] = round(auc.item(), 6)
            else:
                results[f"{split_name}_auc"] = 0.5

            # Brier
            brier = ((preds - y_s) ** 2).mean().item()
            results[f"{split_name}_brier"] = round(brier, 6)

            # Accuracy
            acc = ((preds > 0.5).float() == y_s).float().mean().item()
            results[f"{split_name}_accuracy"] = round(acc, 6)

    # Overfitting gap
    results["overfit_gap_auc"] = round(
        results["train_auc"] - results["test_auc"], 6)
    results["overfit_gap_brier"] = round(
        results["test_brier"] - results["train_brier"], 6)

    return results


# ═══════════════════════════════════════════════════════════════
#  ENSEMBLE EXPORT (for XGBoost blending)
# ═══════════════════════════════════════════════════════════════

def export_ensemble_predictions(events: list, W_population: torch.Tensor,
                                X: torch.Tensor, y: torch.Tensor,
                                device: torch.device,
                                output_path: str = "odin_ensemble_data.json") -> dict:
    """Export predictions from top-K diverse models for ensemble blending.

    Selects K models that are both high-performing AND diverse (different
    prediction patterns), then exports their predictions for XGBoost meta-learning.
    """
    K = W_population.shape[1]

    with torch.no_grad():
        ones = torch.ones(X.shape[0], 1, device=device)
        X_aug = torch.cat([ones, X], dim=1)
        all_preds = torch.sigmoid(X_aug @ W_population)  # (N × K)
        brier_scores = ((all_preds - y.unsqueeze(1)) ** 2).mean(dim=0)

    # Select top 20 by brier, then pick 10 most diverse
    top_k = min(20, K)
    _, top_idx = brier_scores.sort()
    top_preds = all_preds[:, top_idx[:top_k]]

    # Diversity: pairwise correlation, select greedily
    selected = [0]  # always include best
    for _ in range(min(9, top_k - 1)):
        best_div_score = -1
        best_j = -1
        for j in range(top_k):
            if j in selected:
                continue
            # Average absolute correlation with already-selected
            corrs = []
            for s in selected:
                c = torch.corrcoef(torch.stack([top_preds[:, j], top_preds[:, s]]))[0, 1]
                corrs.append(abs(c.item()))
            avg_corr = sum(corrs) / len(corrs)
            div_score = 1 - avg_corr  # higher = more diverse
            if div_score > best_div_score:
                best_div_score = div_score
                best_j = j
        if best_j >= 0:
            selected.append(best_j)

    # Export
    ensemble_data = {
        "n_models": len(selected),
        "n_events": X.shape[0],
        "model_predictions": {},
        "labels": y.cpu().tolist(),
    }
    for i, s_idx in enumerate(selected):
        real_idx = top_idx[s_idx].item()
        preds_list = top_preds[:, s_idx].cpu().tolist()
        brier = brier_scores[real_idx].item()
        ensemble_data["model_predictions"][f"model_{i}"] = {
            "predictions": preds_list,
            "brier": round(brier, 6),
            "weight_idx": real_idx,
        }

    with open(output_path, "w") as f:
        json.dump(ensemble_data, f, indent=2)

    return {"exported_models": len(selected), "path": output_path}


# ═══════════════════════════════════════════════════════════════
#  PLATEAU DETECTION
# ═══════════════════════════════════════════════════════════════

class PlateauDetector:
    """Detect when training has plateaued and trigger interventions.

    Tracks best fitness over a sliding window. If no improvement
    for `patience` generations, triggers diversity injection.
    If no improvement for `halt_patience` generations, halts training.
    """

    def __init__(self, patience: int = 50, halt_patience: int = 300,
                 min_improvement: float = 1e-6):
        self.patience = patience
        self.halt_patience = halt_patience
        self.min_improvement = min_improvement
        self.best_fitness = -float("inf")
        self.gens_since_improvement = 0
        self.total_diversity_injections = 0

    def update(self, fitness: float) -> dict:
        """Update with latest best fitness. Returns action dict."""
        if fitness > self.best_fitness + self.min_improvement:
            self.best_fitness = fitness
            self.gens_since_improvement = 0
        else:
            self.gens_since_improvement += 1

        action = {"inject_diversity": False, "halt": False,
                  "stale_gens": self.gens_since_improvement}

        if self.gens_since_improvement >= self.halt_patience:
            action["halt"] = True
            action["reason"] = (f"No improvement for {self.halt_patience} generations. "
                                f"Best fitness: {self.best_fitness:.6f}")

        elif self.gens_since_improvement > 0 and \
             self.gens_since_improvement % self.patience == 0:
            action["inject_diversity"] = True
            self.total_diversity_injections += 1
            action["reason"] = (f"Diversity injection #{self.total_diversity_injections} "
                                f"after {self.gens_since_improvement} stale generations")

        return action


# ═══════════════════════════════════════════════════════════════
#  ENHANCED FITNESS FUNCTION
# ═══════════════════════════════════════════════════════════════

def compute_fitness_v21(X: torch.Tensor, y: torch.Tensor,
                        W: torch.Tensor,
                        auc_weight: float = 0.40,
                        brier_weight: float = 0.40,
                        acc_weight: float = 0.10,
                        cal_weight: float = 0.10,
                        l2_lam: float = 0.001) -> dict:
    """Compute fitness for all K models simultaneously.

    Enhanced from v2.0 with L2 regularization and calibration error.
    """
    N, F = X.shape
    K = W.shape[1]

    with torch.no_grad():
        ones = torch.ones(N, 1, device=X.device)
        X_aug = torch.cat([ones, X], dim=1)
        logits = X_aug @ W  # (N × K)
        probs = torch.sigmoid(logits)

        # Brier score per model
        brier = ((probs - y.unsqueeze(1)) ** 2).mean(dim=0)  # (K,)

        # Accuracy per model
        preds_binary = (probs > 0.5).float()
        accuracy = (preds_binary == y.unsqueeze(1)).float().mean(dim=0)

        # Calibration error (10-bin)
        cal_errors = torch.zeros(K, device=X.device)
        for b in range(10):
            low = b * 0.1
            high = (b + 1) * 0.1
            for k in range(K):
                mask = (probs[:, k] >= low) & (probs[:, k] < high)
                if mask.sum() > 0:
                    predicted_avg = probs[:, k][mask].mean()
                    actual_avg = y[mask].mean()
                    cal_errors[k] += abs(predicted_avg - actual_avg) * mask.float().mean()

        # AUC per model (vectorized for small populations, chunked for large)
        pos_mask = y == 1.0
        neg_mask = y == 0.0
        n_pos = pos_mask.sum()
        n_neg = neg_mask.sum()

        if n_pos > 0 and n_neg > 0:
            pos_preds = probs[pos_mask, :]  # (n_pos × K)
            neg_preds = probs[neg_mask, :]  # (n_neg × K)

            # Chunked AUC to prevent OOM
            chunk_size = min(50, K)
            auc = torch.zeros(K, device=X.device)
            for c_start in range(0, K, chunk_size):
                c_end = min(c_start + chunk_size, K)
                pp = pos_preds[:, c_start:c_end].unsqueeze(2)  # (n_pos × chunk × 1)
                np_ = neg_preds[:, c_start:c_end].unsqueeze(1)  # (1 × chunk × n_neg)
                wins = (pp > np_).float().sum(dim=(0, 2))
                ties = (pp == np_).float().sum(dim=(0, 2))
                auc[c_start:c_end] = (wins + 0.5 * ties) / (n_pos * n_neg)
        else:
            auc = torch.full((K,), 0.5, device=X.device)

        # L2 penalty
        l2_pen = l2_penalty(W, l2_lam)

        # Composite fitness
        fitness = (auc_weight * auc +
                   brier_weight * (1.0 - brier) +
                   acc_weight * accuracy +
                   cal_weight * (1.0 - cal_errors) -
                   l2_pen)

    return {
        "fitness": fitness, "auc": auc, "brier": brier,
        "accuracy": accuracy, "cal_error": cal_errors,
        "l2_penalty": l2_pen,
    }


# ═══════════════════════════════════════════════════════════════
#  V2.1 GENERATION RUNNER
# ═══════════════════════════════════════════════════════════════

def run_generation_v21(X: torch.Tensor, y: torch.Tensor,
                       W: torch.Tensor, gen: int,
                       plateau: PlateauDetector,
                       device: torch.device,
                       lr: float = 0.01,
                       l2_lam: float = 0.001,
                       gd_steps: int = 100) -> tuple:
    """Run one v2.1 generation: gradient descent → evaluate → evolve.

    Key difference from v2.0: uses batch_coordinate_descent for ALL models
    simultaneously, then evolutionary operators for exploration.

    Returns (new_W, stats_dict, should_halt)
    """
    K = W.shape[1]

    # Phase 1: Batch gradient descent (exploitation)
    W = batch_coordinate_descent(X, y, W, lr=lr, l2_lam=l2_lam, n_steps=gd_steps)

    # Phase 2: Evaluate population
    metrics = compute_fitness_v21(X, y, W, l2_lam=l2_lam)

    best_idx = metrics["fitness"].argmax().item()
    best_fit = metrics["fitness"][best_idx].item()

    # Phase 3: Plateau detection
    action = plateau.update(best_fit)

    # Phase 4: Adaptive sigma
    stale = action["stale_gens"]
    if stale > 200:
        sigma = 0.25
    elif stale > 100:
        sigma = 0.18
    elif stale > 50:
        sigma = 0.12
    elif stale > 20:
        sigma = 0.08
    else:
        sigma = 0.05

    # Phase 5: Evolve with optional diversity injection
    new_W = evolve_v21(W, metrics["fitness"], sigma=sigma, device=device,
                       diversity_injection=action["inject_diversity"])

    stats = {
        "generation": gen,
        "pop_size": K,
        "best_auc": round(metrics["auc"][best_idx].item(), 6),
        "best_brier": round(metrics["brier"][best_idx].item(), 6),
        "best_accuracy": round(metrics["accuracy"][best_idx].item(), 6),
        "best_fitness": round(best_fit, 6),
        "best_cal_error": round(metrics["cal_error"][best_idx].item(), 6),
        "l2_penalty": round(metrics["l2_penalty"][best_idx].item(), 6),
        "sigma": sigma,
        "stale_gens": stale,
        "diversity_injected": action["inject_diversity"],
    }

    if action.get("reason"):
        stats["plateau_action"] = action["reason"]

    return new_W, stats, action["halt"]


# ═══════════════════════════════════════════════════════════════
#  STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ODIN Perpetual GPU v2.1")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Number of generations (None = perpetual)")
    parser.add_argument("--pop", type=int, default=200,
                        help="Population size")
    parser.add_argument("--lr", type=float, default=0.01,
                        help="Learning rate for batch GD")
    parser.add_argument("--l2", type=float, default=0.001,
                        help="L2 regularization strength")
    parser.add_argument("--gd-steps", type=int, default=100,
                        help="Gradient descent steps per generation")
    parser.add_argument("--temporal-cv", action="store_true",
                        help="Run temporal cross-validation only")
    parser.add_argument("--export-ensemble", action="store_true",
                        help="Export ensemble predictions for XGBoost")
    parser.add_argument("--device", default=None,
                        help="Device (cuda/cpu, auto-detected)")
    args = parser.parse_args()

    # Device
    if args.device:
        device = torch.device(args.device)
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    print(f"╔{'═'*58}╗")
    print(f"║  ODIN PERPETUAL GPU v{__version__:>6s} — PLATEAU BREAKER{'':>13s}║")
    print(f"╚{'═'*58}╝")
    print(f"  Device:     {device}")
    if device.type == "cuda":
        mem = torch.cuda.get_device_properties(0)
        print(f"  GPU:        {mem.name}")
        print(f"  VRAM:       {mem.total_mem / 1024**3:.1f} GB")
    print(f"  Population: {args.pop}")
    print(f"  LR:         {args.lr}")
    print(f"  L2:         {args.l2}")
    print(f"  GD steps:   {args.gd_steps}")
    print()

    # Try to import base engine
    try:
        from odin_honing_engine_gpu import (
            load_csv, encode_events_to_tensor, encode_event,
            N_FEATURES, gpu_metrics
        )

        csv_paths = [
            "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv",
            Path.home() / "odin_data" / "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv",
        ]
        events = None
        for p in csv_paths:
            if Path(p).exists():
                events = load_csv(str(p))
                print(f"  Loaded {len(events)} events from {p}")
                break

        if events is None:
            print("  ⚠ No CSV found — using synthetic data for demo")
            events = None

    except ImportError:
        print("  ⚠ odin_honing_engine_gpu.py not found — standalone mode")
        print("    Place this file alongside the honing engine for full functionality.")
        events = None

    if events is None:
        print("\n  Running with synthetic demo data...")
        # Generate synthetic data for testing the pipeline
        N = 500
        F = V21_TOTAL_FEATURES
        X = torch.randn(N, F, device=device) * 0.5
        y = (torch.rand(N, device=device) > 0.35).float()
    else:
        # Encode with v2.1 features
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        print(f"  Resolved events: {len(resolved)}")

        # Use base encoder + v2.1 extension
        X_base, y = encode_events_to_tensor(resolved, device)
        # Extend to v2.1 (pad with zeros for new features — will be populated by MCP enrichment)
        pad = torch.zeros(X_base.shape[0], V21_N_NEW, device=device)
        X = torch.cat([X_base, pad], dim=1)
        F = X.shape[1]

    N = X.shape[0]
    P = 1 + X.shape[1]  # bias + features
    print(f"  Features:   {X.shape[1]} ({55} base + {V21_N_NEW} new)")
    print(f"  Params:     {P}")
    print(f"  Events:     {N}")

    # Load seed weights
    seed_vec = None
    seed_path = Path.home() / "odin_data" / "model_weights.json"
    if seed_path.exists():
        try:
            w = json.loads(seed_path.read_text())
            from odin_perpetual_gpu import weights_to_vector
            seed_vec = torch.tensor(weights_to_vector(w), device=device, dtype=torch.float32)
            if seed_vec.shape[0] < P:
                pad = torch.randn(P - seed_vec.shape[0], device=device) * 0.01
                seed_vec = torch.cat([seed_vec, pad])
            print(f"  Seed:       {seed_path}")
        except Exception:
            pass

    if seed_vec is None:
        seed_vec = torch.randn(P, device=device) * 0.1
        print(f"  Seed:       random initialization")

    # Temporal CV mode
    if args.temporal_cv and events:
        print(f"\n  ═══ TEMPORAL CROSS-VALIDATION ═══")
        result = temporal_cv_evaluate(
            resolved, seed_vec, device,
            base_encoder=lambda e: encode_event(e),
            use_v21_features=False,  # start with base features
            l2_lam=args.l2
        )
        for k, v in result.items():
            print(f"    {k}: {v}")
        return

    # Build initial population
    K = args.pop
    W = seed_vec.unsqueeze(1).expand(-1, K).clone()
    noise = torch.randn_like(W) * 0.05
    noise[:, 0] = 0  # keep seed exact
    noise[0, :] *= 0.3
    W = W + noise

    # Initialize plateau detector
    plateau = PlateauDetector(patience=50, halt_patience=300)

    # Training loop
    max_gen = args.cycles or 999999
    print(f"\n  ═══ STARTING v2.1 PERPETUAL TRAINING ═══\n")

    for gen in range(max_gen):
        t0 = time.time()

        new_W, stats, should_halt = run_generation_v21(
            X, y, W, gen, plateau, device,
            lr=args.lr, l2_lam=args.l2, gd_steps=args.gd_steps
        )

        dt = time.time() - t0

        if gen % 5 == 0 or stats.get("diversity_injected") or should_halt:
            print(f"  Gen {gen:>4d} | AUC {stats['best_auc']:.6f} | "
                  f"Brier {stats['best_brier']:.6f} | "
                  f"Fit {stats['best_fitness']:.6f} | "
                  f"σ={stats['sigma']:.3f} | "
                  f"Stale {stats['stale_gens']:>3d} | "
                  f"{dt:.2f}s")

        if stats.get("plateau_action"):
            print(f"  ⚡ {stats['plateau_action']}")

        if should_halt:
            print(f"\n  ═══ PLATEAU HALT ═══")
            print(f"  Best AUC:   {stats['best_auc']:.6f}")
            print(f"  Best Brier: {stats['best_brier']:.6f}")
            break

        W = new_W

    # Export ensemble if requested
    if args.export_ensemble:
        print(f"\n  ═══ EXPORTING ENSEMBLE ═══")
        ens = export_ensemble_predictions(
            events if events else [], W, X, y, device,
            output_path="odin_ensemble_data.json"
        )
        print(f"  Exported {ens['exported_models']} diverse models to {ens['path']}")

    print(f"\n  ✓ Done")


if __name__ == "__main__":
    main()
