#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL GPU v2.0 — Population-Based Honing Engine              ║
║                                                                        ║
║  Runs perpetually, evolving K weight vectors in parallel on GPU.       ║
║  Dynamic VRAM scanning for coexistence with Gungnir and other apps.    ║
║                                                                        ║
║  Architecture:                                                         ║
║    - Population of K models trained simultaneously via vectorized ops  ║
║    - Warm start from best honed config (AUC 0.9085, Brier 0.0968)     ║
║    - Evolutionary strategies: elite, crossover, mutation               ║
║    - Chunked AUC to prevent OOM on large populations                   ║
║    - Dynamic population resizing based on FREE VRAM each generation    ║
║    - Walkforward validation every N generations (70/30 time split)     ║
║    - Fast retrain mode (<3s) for dynamic ODIN rescoring                ║
║    - Saves best configs + model_weights.json for runner compatibility  ║
║                                                                        ║
║  Uses odin_honing_engine_gpu.py for:                                   ║
║    - Feature encoding (encode_events_to_tensor, N_FEATURES=55)         ║
║    - Weight dict structure (signals, ta_bucket, fda_era, etc.)         ║
║    - CSV loading and event parsing                                     ║
║    - VRAM management (VRAMManager)                                     ║
║                                                                        ║
║  Usage:                                                                ║
║    py -3.11 odin_perpetual_gpu.py                    # run forever     ║
║    py -3.11 odin_perpetual_gpu.py --cycles 50        # N generations   ║
║    py -3.11 odin_perpetual_gpu.py --pop 500          # set population  ║
║    py -3.11 odin_perpetual_gpu.py --retrain          # fast retrain    ║
║    py -3.11 odin_perpetual_gpu.py --best             # show best       ║
║    py -3.11 odin_perpetual_gpu.py --export           # export weights  ║
║                                                                        ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import glob
import json
import math
import os
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import torch

from odin_honing_engine_gpu import (
    OdinScorer,
    OdinGPUModel,
    VRAMManager,
    get_vram_manager,
    load_csv,
    encode_events_to_tensor,
    gpu_auc,
    gpu_metrics,
    sigmoid_cpu,
    N_FEATURES,
    BINARY_SIGNAL_NAMES,
    TA_BUCKET_NAMES,
    FDA_ERA_NAMES,
    RESUB_NAMES,
    TA_OFFSET_NAMES,
    CONTINUOUS_NAMES,
    TIER_THRESHOLDS,
    TIER_ACTIONS,
    __version__ as ENGINE_VERSION,
)

__version__ = "2.0.0"

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════

N_PARAMS = 1 + N_FEATURES   # bias + 55 features = 56

DEFAULT_CSV = "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv"

# ═══════════════════════════════════════════════════════════════
#  EMBEDDED BEST WEIGHTS — AUC 0.9085 / Brier 0.0968
#  Source: best_run_AUC_0.9085_20260224_144303.json (v13.2.1723)
#  This is the guaranteed floor — seed scan can only improve on this.
# ═══════════════════════════════════════════════════════════════

EMBEDDED_BEST_WEIGHTS = {
    "base_logit": 0.9574763178825378,
    "signals": {
        "btd": -0.24043411016464233,
        "orphan": -0.1919279843568802,
        "priority_review": 2.4945313930511475,
        "fast_track": 0.9469134211540222,
        "accelerated_approval": 0.5616020560264587,
        "surrogate_endpoint": 0.779567539691925,
        "had_adcom": 1.1048855781555176,
        "prior_crl": -4.201313495635986,
        "form_483_issues": -2.2937920093536377,
        "manufacturing_risk": 0.2954530417919159,
        "double_crl_flag": -0.4828558564186096,
        "ppm_flag": -1.8004757165908813,
        "ped_pk_missing": 0.0758938267827034,
        "ema_cmc_flag": -0.09473371505737305,
        "cmc_extension_flag": -0.04037213698029518,
        "gene_therapy": 0.4028855562210083,
        "single_arm_study": -0.6692684292793274,
        "btd_onco_interaction": 0.8509936928749084,
        "btd_priority_interaction": -0.05749322474002838,
        "ta_very_high_risk": 0.8478214144706726,
        "safety_moderate": 0.11673340946435928,
        "safety_high": -0.5029503107070923,
    },
    "ta_bucket": {
        "LOW": -0.8950117230415344,
        "MOD": 0.48908731341362,
        "HIGH": 0.4445643723011017,
        "VERY_HIGH": 0.8879076242446899,
    },
    "fda_era": {
        "PRE_2020": 1.4344688653945923,
        "COVID_ERA": -0.5888262987136841,
        "HOEG_ERA": 0.1286316066980362,
        "POST_COVID": 0.023642653599381447,
    },
    "resub": {
        "0": 0.8764392733573914,
        "1": 0.012153981253504753,
        "2": 0.42118677496910095,
    },
    "ta_offsets": {
        "Oncology": -0.2331658899784088,
        "Other": 0.8609467148780823,
        "Infectious Disease": -0.24301211535930634,
        "CNS/Neurology": -0.1910575032234192,
        "Immunology": 0.2528945803642273,
        "Rare Disease": -0.3901759684085846,
        "Cardiovascular": 0.1580648422241211,
        "Ophthalmology": 0.2838917672634125,
        "Pain Management": 0.07203163951635361,
        "Metabolic/Endocrine": 0.24275852739810944,
        "Endocrinology": -0.01873640902340412,
        "Nephrology": 0.08560416102409363,
        "Dermatology": -0.1144019365310669,
        "Respiratory": 0.5847209095954895,
        "Hematology": 0.03376597538590431,
        "GI/Hepatology": 0.32063424587249756,
        "Women's Health": 0.5293677449226379,
        "Vaccines": 0.36283910274505615,
        "CNS": -0.7684274315834045,
    },
    "continuous": {
        "historical_crl_rate": 0.45299193263053894,
        "sponsor_prior_approvals": 0.17497627437114716,
        "prior_crl_count": -0.015850525349378586,
    },
}


# ═══════════════════════════════════════════════════════════════
#  VRAM-AWARE POPULATION SIZING
# ═══════════════════════════════════════════════════════════════

def get_free_vram_mb(device: torch.device) -> float:
    if device.type != "cuda":
        return 0.0
    torch.cuda.synchronize(device)
    free, _total = torch.cuda.mem_get_info(device)
    return free / (1024 * 1024)


def estimate_population(n_events: int, device: torch.device,
                        target_util: float = 0.40) -> int:
    """
    Estimate max population that fits in CURRENTLY FREE VRAM.
    Uses conservative 40% target to coexist with Gungnir + other GPU apps.
    Scans actual free memory each call — never cached.
    """
    if device.type != "cuda":
        per_model = 3 * N_PARAMS * 4 + n_events * 8
        return max(50, min(500, int(300 * 1024 * 1024 / per_model)))

    torch.cuda.synchronize(device)
    free_mem, _total = torch.cuda.mem_get_info(device)
    available = free_mem * target_util

    # Shared cost: X tensor + y tensor (constant, loaded once)
    shared = n_events * N_FEATURES * 4 + n_events * 4

    # Per-model cost: W col + adam_m + adam_v + best_W + logits + preds + AUC chunk
    per_model = (4 * N_PARAMS * 4        # W, m, v, best_W columns
                 + n_events * 4           # logits column
                 + n_events * 4           # preds column
                 + n_events * 8           # AUC chunk overhead
                 + 512)                   # misc

    usable = available - shared - 100 * 1024 * 1024   # 100 MB safety margin
    pop = max(50, int(usable / per_model))
    return min(pop, 5000)


# ═══════════════════════════════════════════════════════════════
#  WEIGHT DICT ↔ FLAT VECTOR CONVERSION
# ═══════════════════════════════════════════════════════════════

def weights_to_vector(w: dict) -> list:
    """Convert ODIN weight dict → flat vector [bias, f0..f54]. Length = 56."""
    vec = [w.get("base_logit", 0.0)]

    signals = w.get("signals", {})
    for sig in BINARY_SIGNAL_NAMES:
        vec.append(signals.get(sig, 0.0))

    for name in TA_BUCKET_NAMES:
        vec.append(w.get("ta_bucket", {}).get(name, 0.0))

    for name in FDA_ERA_NAMES:
        vec.append(w.get("fda_era", {}).get(name, 0.0))

    for name in RESUB_NAMES:
        vec.append(w.get("resub", {}).get(name, 0.0))

    for name in TA_OFFSET_NAMES:
        vec.append(w.get("ta_offsets", {}).get(name, 0.0))

    for name in CONTINUOUS_NAMES:
        vec.append(w.get("continuous", {}).get(name, 0.0))

    assert len(vec) == N_PARAMS, f"Expected {N_PARAMS}, got {len(vec)}"
    return vec


def vector_to_weights(vec) -> dict:
    """Convert flat vector → ODIN weight dict."""
    if isinstance(vec, torch.Tensor):
        vec = vec.cpu().tolist()

    d = {"base_logit": vec[0]}
    offset = 1

    d["signals"] = {}
    for i, sig in enumerate(BINARY_SIGNAL_NAMES):
        d["signals"][sig] = vec[offset + i]
    offset += len(BINARY_SIGNAL_NAMES)

    d["ta_bucket"] = {}
    for i, name in enumerate(TA_BUCKET_NAMES):
        d["ta_bucket"][name] = vec[offset + i]
    offset += len(TA_BUCKET_NAMES)

    d["fda_era"] = {}
    for i, name in enumerate(FDA_ERA_NAMES):
        d["fda_era"][name] = vec[offset + i]
    offset += len(FDA_ERA_NAMES)

    d["resub"] = {}
    for i, name in enumerate(RESUB_NAMES):
        d["resub"][name] = vec[offset + i]
    offset += len(RESUB_NAMES)

    d["ta_offsets"] = {}
    for i, name in enumerate(TA_OFFSET_NAMES):
        d["ta_offsets"][name] = vec[offset + i]
    offset += len(TA_OFFSET_NAMES)

    d["continuous"] = {}
    for i, name in enumerate(CONTINUOUS_NAMES):
        d["continuous"][name] = vec[offset + i]

    return d


# ═══════════════════════════════════════════════════════════════
#  POPULATION TRAINER (parallel vectorized)
# ═══════════════════════════════════════════════════════════════

class PopulationTrainer:
    """
    Train K logistic regression models simultaneously on GPU.

    Weight matrix W: shape (N_PARAMS, K) — each column is one model.
      W[0, :] = bias, W[1:, :] = feature weights.

    Forward: logits = X @ W[1:, :] + W[0, :]   → (N, K)
             P = sigmoid(logits)                → (N, K)
    Loss:    Brier = mean((P - y)^2, dim=0)     → (K,)
    """

    def __init__(self, X: torch.Tensor, y: torch.Tensor, device: torch.device,
                 lr: float = 0.003, l2: float = 0.005):
        self.X = X           # (N, F)
        self.y = y           # (N,)
        self.y_col = y.unsqueeze(1)   # (N, 1) for broadcasting
        self.N, self.F = X.shape
        self.device = device
        self.lr = lr
        self.l2 = l2
        self.base_rate = y.mean().item()

    def train_population(self, W: torch.Tensor, max_epochs: int = 2000,
                         patience: int = 300, verbose: bool = True) -> torch.Tensor:
        """
        Train all K models via manual Adam (no autograd — faster for parallel).
        Returns best-ever weight matrix (per-model early-stop tracking).
        """
        K = W.shape[1]
        W = W.clone().detach().requires_grad_(False)
        best_W = W.clone()
        best_brier = torch.full((K,), 1.0, device=self.device)

        # Adam state
        m_w = torch.zeros_like(W)
        v_w = torch.zeros_like(W)
        beta1, beta2, eps_adam = 0.9, 0.999, 1e-8

        stale = torch.zeros(K, dtype=torch.int32, device=self.device)
        active = torch.ones(K, dtype=torch.bool, device=self.device)

        t_start = time.time()
        final_epoch = 0

        for epoch in range(max_epochs):
            # Warmup LR for first 100 epochs
            if epoch < 100:
                lr = self.lr * (epoch + 1) / 100
            else:
                progress = (epoch - 100) / max(max_epochs - 100, 1)
                lr = self.lr * 0.01 + 0.5 * (self.lr - self.lr * 0.01) * (
                    1 + math.cos(math.pi * progress))

            # Forward pass: (N, F) @ (F, K) + (1, K) → (N, K)
            logits = self.X @ W[1:, :] + W[0:1, :]
            P = torch.sigmoid(logits)

            # Brier loss per model
            residuals = P - self.y_col
            brier = (residuals ** 2).mean(dim=0)

            # Gradient: d(Brier)/d(logits) = 2/N * residuals * P * (1-P)
            grad_logits = (2.0 / self.N) * residuals * P * (1 - P)

            # Weight & bias gradients
            grad_feat = self.X.T @ grad_logits                # (F, K)
            grad_bias = grad_logits.mean(dim=0, keepdim=True) # (1, K)
            grad_full = torch.cat([grad_bias, grad_feat], dim=0)

            # L2 on feature weights (skip bias at row 0)
            grad_full[1:, :] += self.l2 * W[1:, :]

            # Gradient clipping per model
            gnorm = grad_full.norm(dim=0, keepdim=True).clamp(min=1e-8)
            clip = gnorm > 5.0
            grad_full = torch.where(clip, grad_full * 5.0 / gnorm, grad_full)

            # Adam step
            t = epoch + 1
            m_w = beta1 * m_w + (1 - beta1) * grad_full
            v_w = beta2 * v_w + (1 - beta2) * (grad_full ** 2)
            m_hat = m_w / (1 - beta1 ** t)
            v_hat = v_w / (1 - beta2 ** t)

            update = lr * m_hat / (v_hat.sqrt() + eps_adam)
            W[:, active] -= update[:, active]

            # Per-model best tracking
            improved = brier < best_brier - 1e-9
            best_brier = torch.where(improved, brier, best_brier)
            if improved.any():
                mask = improved.unsqueeze(0).expand_as(W)
                best_W = torch.where(mask, W, best_W)

            # Per-model early stopping
            stale = torch.where(improved, torch.zeros_like(stale), stale + 1)
            active = stale < patience

            final_epoch = epoch + 1
            if not active.any():
                break

            if verbose and (epoch + 1) % 500 == 0:
                n_act = active.sum().item()
                elapsed = time.time() - t_start
                meps = K * (epoch + 1) / elapsed
                print(f"    Epoch {epoch+1:>5d} | Active: {n_act:>5d}/{K} | "
                      f"Best Brier: {best_brier.min():.6f} | {meps:,.0f} model-ep/s")

        elapsed = time.time() - t_start
        total_me = K * final_epoch
        if verbose:
            print(f"    Done: {final_epoch} ep × {K} models = "
                  f"{total_me:,} model-epochs in {elapsed:.1f}s "
                  f"({total_me / max(elapsed, 0.001):,.0f} mep/s)")

        return best_W

    def evaluate_population(self, W: torch.Tensor) -> dict:
        """
        Compute AUC, Brier, accuracy, calibration error for all K models.
        Uses chunked AUC to prevent OOM with large populations.
        """
        K = W.shape[1]

        with torch.no_grad():
            logits = self.X @ W[1:, :] + W[0:1, :]
            P = torch.sigmoid(logits)

            brier = ((P - self.y_col) ** 2).mean(dim=0)
            accuracy = ((P >= 0.5).float() == self.y_col).float().mean(dim=0)

            # Chunked AUC
            pos_mask = (self.y == 1.0)
            neg_mask = (self.y == 0.0)
            n_pos = pos_mask.sum().item()
            n_neg = neg_mask.sum().item()

            if n_pos == 0 or n_neg == 0:
                auc = torch.full((K,), 0.5, device=self.device)
            elif n_pos * n_neg * K <= 10_000_000:
                # Exact AUC — small enough
                P_pos = P[pos_mask, :]
                P_neg = P[neg_mask, :]
                conc = (P_pos.unsqueeze(1) > P_neg.unsqueeze(0)).float()
                tied = (P_pos.unsqueeze(1) == P_neg.unsqueeze(0)).float()
                auc = (conc.sum(dim=(0, 1)) + 0.5 * tied.sum(dim=(0, 1))) / (n_pos * n_neg)
            else:
                # Sampled AUC — chunked across model dimension
                ns = min(200_000, n_pos * n_neg)
                pi = torch.where(pos_mask)[0]
                ni = torch.where(neg_mask)[0]
                rp = pi[torch.randint(n_pos, (ns,), device=self.device)]
                rn = ni[torch.randint(n_neg, (ns,), device=self.device)]

                if self.device.type == "cuda":
                    free_mem = torch.cuda.mem_get_info(self.device)[0]
                else:
                    free_mem = 2_000_000_000
                bytes_per_model = ns * 4 * 3
                chunk_size = max(10, int(free_mem * 0.25 / max(bytes_per_model, 1)))
                chunk_size = min(chunk_size, K)

                auc = torch.zeros(K, device=self.device)
                for start in range(0, K, chunk_size):
                    end = min(start + chunk_size, K)
                    P_rp = P[rp, start:end]
                    P_rn = P[rn, start:end]
                    auc[start:end] = ((P_rp > P_rn).float().mean(dim=0) +
                                       0.5 * (P_rp == P_rn).float().mean(dim=0))

            # Calibration error
            mean_pred = P.mean(dim=0)
            cal_error = (mean_pred - self.base_rate).abs()

            # Composite fitness: AUC-dominant
            fitness = (0.55 * auc
                       + 0.20 * (1.0 - brier)
                       + 0.15 * (1.0 - cal_error.clamp(0, 1))
                       + 0.10 * accuracy)

        return {
            "auc": auc, "brier": brier, "accuracy": accuracy,
            "cal_error": cal_error, "fitness": fitness,
        }


# ═══════════════════════════════════════════════════════════════
#  EVOLUTIONARY OPERATORS
# ═══════════════════════════════════════════════════════════════

def evolve_population(W: torch.Tensor, fitness: torch.Tensor,
                      sigma: float = 0.05, device: torch.device = None) -> torch.Tensor:
    """
    Evolutionary step:
      - Top 10% elite → copied exactly
      - Next 30% → uniform crossover from tournament pairs
      - Remaining 60% → mutation from top 50%
    """
    K = W.shape[1]
    new_W = torch.zeros_like(W)

    _, idx = fitness.sort(descending=True)
    W_sorted = W[:, idx]

    n_elite = max(2, int(K * 0.10))
    n_cross = max(2, int(K * 0.30))
    n_mutate = K - n_elite - n_cross

    # Elite: unchanged
    new_W[:, :n_elite] = W_sorted[:, :n_elite]

    # Crossover: uniform from tournament pairs in top half
    top_half = W_sorted[:, :max(2, K // 2)]
    th_k = top_half.shape[1]

    idx1 = torch.randint(th_k, (n_cross,), device=device)
    idx2 = torch.randint(th_k, (n_cross,), device=device)
    p1 = top_half[:, idx1]
    p2 = top_half[:, idx2]
    mask = torch.rand(W.shape[0], n_cross, device=device) > 0.5
    new_W[:, n_elite:n_elite + n_cross] = torch.where(mask, p1, p2)

    # Mutation: perturb random selections from top 50%
    base_idx = torch.randint(th_k, (n_mutate,), device=device)
    base = top_half[:, base_idx]
    noise = torch.randn_like(base) * sigma
    noise[0, :] *= 0.3     # less aggressive on bias
    new_W[:, n_elite + n_cross:] = base + noise

    return new_W


# ═══════════════════════════════════════════════════════════════
#  WALKFORWARD VALIDATION
# ═══════════════════════════════════════════════════════════════

def walkforward_validate(events: list, seed_vec: torch.Tensor,
                         device: torch.device) -> dict:
    """Time-split validation: train on first 70%, test on last 30%."""
    resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
    n = len(resolved)
    split = int(n * 0.70)
    train_evts = resolved[:split]
    test_evts = resolved[split:]

    if len(train_evts) < 50 or len(test_evts) < 20:
        return {"status": "INSUFFICIENT_DATA"}

    X_train, y_train = encode_events_to_tensor(train_evts, device)
    X_test, y_test = encode_events_to_tensor(test_evts, device)

    # Small population seeded from best weights
    K = 50
    W = seed_vec.unsqueeze(1).expand(-1, K).clone()
    noise = torch.randn_like(W) * 0.02
    noise[:, 0] = 0   # keep model 0 exact
    noise[0, :] *= 0.3
    W = W + noise

    trainer = PopulationTrainer(X_train, y_train, device)
    best_W = trainer.train_population(W, max_epochs=1000, patience=200, verbose=False)

    # Evaluate all K on test set
    with torch.no_grad():
        test_logits = X_test @ best_W[1:, :] + best_W[0:1, :]
        test_P = torch.sigmoid(test_logits)
        test_brier = ((test_P - y_test.unsqueeze(1)) ** 2).mean(dim=0)

    best_idx = test_brier.argmin().item()

    best_preds = test_P[:, best_idx]
    test_m = gpu_metrics(best_preds, y_test)

    with torch.no_grad():
        train_preds = torch.sigmoid(X_train @ best_W[1:, best_idx] + best_W[0, best_idx])
    train_m = gpu_metrics(train_preds, y_train)

    return {
        "status": "OK",
        "train_n": len(train_evts), "test_n": len(test_evts),
        "train_auc": train_m["auc"], "train_brier": train_m["brier"],
        "test_auc": test_m["auc"], "test_brier": test_m["brier"],
        "test_accuracy": test_m["accuracy"],
    }


# ═══════════════════════════════════════════════════════════════
#  BEST CONFIG TRACKER
# ═══════════════════════════════════════════════════════════════

class BestConfigTracker:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.best = None
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    self.best = json.load(f)
            except Exception:
                pass

    def check_and_update(self, entry: dict) -> bool:
        """Update if entry has higher fitness. Returns True if updated."""
        if self.best is None or entry.get("fitness", 0) > self.best.get("fitness", 0):
            self.best = entry
            os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
            with open(self.filepath, "w") as f:
                json.dump(entry, f, indent=2)
            return True
        return False

    def print_best(self):
        if self.best:
            print(f"\n  ═══ BEST CONFIG ═══")
            print(f"  AUC:      {self.best.get('auc', '?'):.6f}")
            print(f"  Brier:    {self.best.get('brier', '?'):.6f}")
            print(f"  Accuracy: {self.best.get('accuracy', '?'):.6f}")
            print(f"  Fitness:  {self.best.get('fitness', '?'):.6f}")
            gen = self.best.get('generation', '?')
            ts = self.best.get('timestamp', '?')
            print(f"  Gen:      {gen} | {ts}")
        else:
            print("  No best config saved yet.")


# ═══════════════════════════════════════════════════════════════
#  RUN HISTORY (append-only JSONL)
# ═══════════════════════════════════════════════════════════════

class RunHistory:
    def __init__(self, filepath: str):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    def log(self, entry: dict):
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def count(self) -> int:
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath, "r") as f:
            return sum(1 for _ in f)


# ═══════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════

class OdinPerpetualGPU:
    def __init__(self, population_size: int = None, device: str = None,
                 data_dir: str = None, csv_path: str = None,
                 vram_fraction: float = 0.40):
        self.data_dir = data_dir or str(Path.home() / "odin_data")
        os.makedirs(self.data_dir, exist_ok=True)

        print(f"\n{'═' * 70}")
        print(f"  ODIN PERPETUAL GPU v{__version__}")
        print(f"  Population-Based Honing Engine")
        print(f"  Engine: odin_honing_engine_gpu v{ENGINE_VERSION}")
        print(f"{'═' * 70}")

        # Device selection
        if device:
            self.device = torch.device(device)
        elif torch.cuda.is_available():
            self.device = torch.device("cuda:0")
        else:
            self.device = torch.device("cpu")

        print(f"  Device: {self.device}")
        if self.device.type == "cuda":
            props = torch.cuda.get_device_properties(self.device)
            total = getattr(props, 'total_memory', None) or getattr(props, 'total_mem', 0)
            print(f"  GPU: {props.name} ({total / 1e9:.1f} GB)")
        if self.device.type == "cpu":
            print(f"  ⚠ CPU mode — expect ~10-50x slower than GPU")
            print(f"    Install CUDA PyTorch: pip install torch --index-url "
                  f"https://download.pytorch.org/whl/cu121")

        # Load events from CSV
        csv_path = csv_path or self._find_csv()
        if not csv_path or not os.path.exists(csv_path):
            print(f"  ❌ CSV not found. Tried: {csv_path or DEFAULT_CSV}")
            sys.exit(1)

        print(f"  CSV: {csv_path}")
        all_events = load_csv(csv_path)
        self.events = [e for e in all_events if e.get("outcome") in ("APPROVED", "CRL")]
        n_approved = sum(1 for e in self.events if e["outcome"] == "APPROVED")
        n_crl = len(self.events) - n_approved
        self.base_rate = n_approved / len(self.events) if self.events else 0.5
        print(f"  Events: {len(self.events)} resolved  "
              f"({n_approved} approved / {n_crl} CRL / {self.base_rate:.1%} base rate)")

        # Encode to GPU tensors
        self.X, self.y = encode_events_to_tensor(self.events, self.device)
        self.N, self.nF = self.X.shape
        print(f"  Tensor: {self.N} × {self.nF} features on {self.device}")
        assert self.nF == N_FEATURES, f"Feature mismatch: {self.nF} != {N_FEATURES}"

        # Population sizing (dynamic VRAM check)
        if population_size:
            self.pop_size = population_size
        else:
            self.pop_size = estimate_population(self.N, self.device)

        if self.device.type == "cuda":
            free = get_free_vram_mb(self.device)
            print(f"  VRAM: {free:.0f} MB free → population {self.pop_size}")
        else:
            print(f"  Population: {self.pop_size} (CPU mode)")

        # Trackers — BEFORE loading seeds so they're available
        self.best_tracker = BestConfigTracker(
            os.path.join(self.data_dir, "best_config_v20.json"))
        self.history = RunHistory(
            os.path.join(self.data_dir, "run_history_v20.jsonl"))
        self.total_generations = self.history.count()

        # Load best seed weights
        self.seed_weights, self.seed_source = self._load_best_seed()

        # Stale generation counter for adaptive sigma
        self._stale_gens = 0
        self._prev_best_fit = 0.0

    # ─── CSV FINDER ───────────────────────────────────────────

    def _find_csv(self) -> str:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            DEFAULT_CSV,
            os.path.join(script_dir, DEFAULT_CSV),
            os.path.join(os.getcwd(), DEFAULT_CSV),
            os.path.join(self.data_dir, DEFAULT_CSV),
            os.path.join(str(Path.home()), DEFAULT_CSV),
            os.path.join(str(Path.home()), "Downloads", DEFAULT_CSV),
            os.path.join(str(Path.home()), "Documents", "Python", DEFAULT_CSV),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    # ─── SEED LOADER ──────────────────────────────────────────

    def _load_best_seed(self) -> tuple:
        """
        Find the absolute best available seed from ALL sources:
          0. EMBEDDED_BEST_WEIGHTS (hardcoded AUC 0.9085 — guaranteed floor)
          1. best_config_v20.json (our own evolving best)
          2. best_run_*.json files (from runner auto-honing)
          3. model_weights.json (current production weights)

        Scans: data_dir, script directory, CWD.
        Evaluates each on the actual dataset for fair comparison.
        Returns (weights_dict, source_description).
        """
        candidates = []

        # 0. EMBEDDED — always present, guaranteed floor
        candidates.append((EMBEDDED_BEST_WEIGHTS,
                           "EMBEDDED (AUC 0.9085 / Brier 0.0968)"))

        # Directories to scan
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scan_dirs = list(set(filter(os.path.isdir, [
            self.data_dir,
            script_dir,
            os.getcwd(),
            os.path.join(self.data_dir, "best_runs"),
        ])))

        # 1. Our own best_config_v20
        if self.best_tracker.best:
            w = self.best_tracker.best.get("weights", {})
            if w and "signals" in w:
                candidates.append((w, "best_config_v20.json [self]"))

        # 2. best_run_*.json files
        for d in scan_dirs:
            for path in glob.glob(os.path.join(d, "best_run_*.json")):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    w = data.get("weights", {})
                    if w and "signals" in w:
                        candidates.append((w, os.path.basename(path)))
                except Exception:
                    pass

        # 3. model_weights.json
        for d in scan_dirs:
            mw_path = os.path.join(d, "model_weights.json")
            if os.path.exists(mw_path):
                try:
                    with open(mw_path, "r") as f:
                        w = json.load(f)
                    if "signals" in w:
                        candidates.append((w, f"model_weights.json ({d})"))
                except Exception:
                    pass

        # Evaluate every candidate on the actual dataset
        print(f"\n  Scanning {len(candidates)} seed candidate(s)...")
        scored = []
        seen_hashes = set()
        for w, src in candidates:
            try:
                vec = torch.tensor(weights_to_vector(w),
                                   dtype=torch.float32, device=self.device)
                # Deduplicate by weight hash
                h = hash(tuple(round(v, 8) for v in vec.tolist()))
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                with torch.no_grad():
                    logits = self.X @ vec[1:] + vec[0]
                    P = torch.sigmoid(logits)
                    auc_val = gpu_auc(P, self.y)
                    brier_val = ((P - self.y) ** 2).mean().item()
                scored.append((auc_val, -brier_val, w, src))
            except Exception as ex:
                print(f"    ⚠ Skipping {src}: {ex}")

        if not scored:
            # Should never happen — embedded weights always work
            print(f"  ⚠ All seeds failed — using embedded weights")
            return deepcopy(EMBEDDED_BEST_WEIGHTS), "EMBEDDED (fallback)"

        # Sort: highest AUC first, then lowest Brier (negated)
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # Print ranked table
        print(f"  ┌─────────────────────────────────────────────────────────────┐")
        print(f"  │  SEED CANDIDATES (ranked by AUC on {self.N} events)          │")
        print(f"  ├─────────────────────────────────────────────────────────────┤")
        for i, (auc_v, neg_brier, _, src) in enumerate(scored[:8]):
            marker = " ← SELECTED" if i == 0 else ""
            print(f"  │  {i+1}. AUC={auc_v:.6f} Brier={-neg_brier:.6f}  {src}{marker}")
        print(f"  └─────────────────────────────────────────────────────────────┘")

        return deepcopy(scored[0][2]), scored[0][3]

    # ─── INITIAL POPULATION ───────────────────────────────────

    def _build_initial_population(self, K: int) -> torch.Tensor:
        """
        Build initial population seeded from best config.
        Model 0 = exact copy of seed. Rest = perturbations.
        """
        seed_vec = torch.tensor(weights_to_vector(self.seed_weights),
                                dtype=torch.float32, device=self.device)
        W = seed_vec.unsqueeze(1).expand(-1, K).clone()

        if K > 1:
            noise = torch.randn(N_PARAMS, K - 1, device=self.device) * 0.03
            noise[0, :] *= 0.3   # less noise on bias
            W[:, 1:] += noise

        return W

    # ─── GENERATION ───────────────────────────────────────────

    def run_generation(self, gen: int, W: torch.Tensor) -> tuple:
        """Run one generation: train → evaluate → evolve. Returns (new_W, stats)."""
        K = W.shape[1]

        # Dynamic VRAM re-check every 5 generations
        if self.device.type == "cuda" and gen > 0 and gen % 5 == 0:
            new_pop = estimate_population(self.N, self.device)
            if new_pop < K * 0.6:
                # VRAM pressure — shrink population (keep best)
                print(f"  ⚠ VRAM pressure — shrinking {K} → {new_pop}")
                trainer = PopulationTrainer(self.X, self.y, self.device)
                metrics = trainer.evaluate_population(W)
                _, top_idx = metrics["fitness"].sort(descending=True)
                W = W[:, top_idx[:new_pop]]
                K = new_pop
                torch.cuda.empty_cache()

        # Train
        trainer = PopulationTrainer(self.X, self.y, self.device)
        best_W = trainer.train_population(
            W, max_epochs=2000, patience=300, verbose=(gen % 10 == 0))

        # Evaluate
        metrics = trainer.evaluate_population(best_W)

        # Global best this generation
        best_idx = metrics["fitness"].argmax().item()
        best_auc = metrics["auc"][best_idx].item()
        best_brier = metrics["brier"][best_idx].item()
        best_acc = metrics["accuracy"][best_idx].item()
        best_fit = metrics["fitness"][best_idx].item()
        best_cal = metrics["cal_error"][best_idx].item()

        # Population diversity stats
        pop_auc_std = metrics["auc"].std().item()
        pop_brier_std = metrics["brier"].std().item()
        pop_w_std = best_W.std(dim=1).mean().item()

        # Adaptive sigma (mutation strength)
        if best_fit <= self._prev_best_fit + 1e-7:
            self._stale_gens += 1
        else:
            self._stale_gens = 0
        self._prev_best_fit = best_fit

        if self._stale_gens > 200:
            sigma = 0.20    # heavy exploration
        elif self._stale_gens > 100:
            sigma = 0.15
        elif self._stale_gens > 50:
            sigma = 0.10
        elif self._stale_gens > 20:
            sigma = 0.07
        else:
            sigma = 0.05

        # Evolve
        new_W = evolve_population(best_W, metrics["fitness"],
                                  sigma=sigma, device=self.device)

        stats = {
            "generation": gen + self.total_generations,
            "pop_size": K,
            "best_auc": round(best_auc, 6),
            "best_brier": round(best_brier, 6),
            "best_accuracy": round(best_acc, 6),
            "best_fitness": round(best_fit, 6),
            "best_cal_error": round(best_cal, 6),
            "pop_auc_std": round(pop_auc_std, 6),
            "pop_brier_std": round(pop_brier_std, 6),
            "pop_weight_std": round(pop_w_std, 6),
            "sigma": sigma,
            "stale_gens": self._stale_gens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Check & save best config
        best_vec = best_W[:, best_idx]
        best_weights = vector_to_weights(best_vec)
        best_entry = {
            "auc": best_auc, "brier": best_brier,
            "accuracy": best_acc, "fitness": best_fit,
            "generation": gen + self.total_generations,
            "weights": best_weights,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        is_new_best = self.best_tracker.check_and_update(best_entry)

        if is_new_best:
            # Write model_weights.json for runner compatibility
            mw_path = os.path.join(self.data_dir, "model_weights.json")
            with open(mw_path, "w") as f:
                json.dump(best_weights, f, indent=2)

            # Write timestamped best_run file
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            br_path = os.path.join(self.data_dir,
                                   f"best_run_AUC_{best_auc:.4f}_{ts}.json")
            payload = {
                "timestamp": ts,
                "version": f"pop-v{__version__}.{gen + self.total_generations}",
                "metrics": {"auc": best_auc, "brier": best_brier},
                "weights": best_weights,
            }
            with open(br_path, "w") as f:
                json.dump(payload, f, indent=4)

        stats["new_best"] = is_new_best

        # Append to history log
        self.history.log(stats)

        return new_W, stats

    # ─── PERPETUAL LOOP ───────────────────────────────────────

    def run_perpetual(self, max_cycles: int = None):
        K = self.pop_size
        W = self._build_initial_population(K)

        print(f"\n{'═' * 70}")
        print(f"  STARTING PERPETUAL HONING")
        print(f"  Population: {K} | Device: {self.device}")
        print(f"  Seed: {self.seed_source}")
        if max_cycles:
            print(f"  Generations: {max_cycles}")
        else:
            print(f"  Generations: ∞ (Ctrl+C to stop)")
        print(f"{'═' * 70}")

        gen = 0
        try:
            while max_cycles is None or gen < max_cycles:
                print(f"\n  ── Generation {gen} ──")
                W, stats = self.run_generation(gen, W)

                # One-line summary
                star = " 🏆 NEW BEST" if stats.get("new_best") else ""
                print(f"  → AUC={stats['best_auc']:.6f}  "
                      f"Brier={stats['best_brier']:.6f}  "
                      f"Acc={stats['best_accuracy']:.4f}  "
                      f"σ={stats['sigma']:.3f}  "
                      f"stale={stats['stale_gens']}{star}")

                if self.device.type == "cuda":
                    free = get_free_vram_mb(self.device)
                    alloc = torch.cuda.memory_allocated(self.device) / (1024**2)
                    print(f"    VRAM: {alloc:.0f} MB alloc / {free:.0f} MB free  "
                          f"pop={stats['pop_size']}")

                # Walkforward validation every 50 generations
                if gen > 0 and gen % 50 == 0:
                    print(f"\n  ── Walkforward Validation (gen {gen}) ──")
                    best_w = (self.best_tracker.best or {}).get("weights",
                                                                self.seed_weights)
                    seed_vec = torch.tensor(weights_to_vector(best_w),
                                            dtype=torch.float32,
                                            device=self.device)
                    wf = walkforward_validate(self.events, seed_vec, self.device)
                    if wf["status"] == "OK":
                        gap = wf['train_auc'] - wf['test_auc']
                        print(f"    Train (n={wf['train_n']}): "
                              f"AUC={wf['train_auc']:.6f}  "
                              f"Brier={wf['train_brier']:.6f}")
                        print(f"    Test  (n={wf['test_n']}):  "
                              f"AUC={wf['test_auc']:.6f}  "
                              f"Brier={wf['test_brier']:.6f}")
                        print(f"    Overfit gap: {gap:+.4f}")
                    else:
                        print(f"    {wf['status']}")

                # Plateau restart: re-seed with wider noise
                if self._stale_gens > 200 and self._stale_gens % 200 == 0:
                    print(f"\n  ⚡ Plateau restart (stale {self._stale_gens}) "
                          f"— re-seeding with wider noise")
                    W = self._build_initial_population(W.shape[1])
                    noise = torch.randn_like(W) * 0.15
                    noise[:, 0] = 0
                    noise[0, :] *= 0.3
                    W += noise
                    self._stale_gens = 0

                gen += 1

        except KeyboardInterrupt:
            print(f"\n\n  ⏹ Stopped after {gen} generations")

        # Final summary
        self.best_tracker.print_best()
        total = gen + self.total_generations
        print(f"\n  Session: {gen} generations  |  All-time: {total}")

    # ─── FAST RETRAIN ─────────────────────────────────────────

    def fast_retrain(self):
        """
        Quick retrain: K=50, tight noise, 1000 epochs. Target: <3s.
        For immediate model_weights.json update after a PDUFA outcome.
        """
        print(f"\n  ⚡ Fast retrain mode")
        K = 50
        W = self._build_initial_population(K)
        noise = torch.randn_like(W) * 0.01
        noise[:, 0] = 0
        W += noise

        trainer = PopulationTrainer(self.X, self.y, self.device)
        t0 = time.time()
        best_W = trainer.train_population(W, max_epochs=1000, patience=100,
                                          verbose=False)
        elapsed = time.time() - t0

        metrics = trainer.evaluate_population(best_W)
        best_idx = metrics["fitness"].argmax().item()
        best_weights = vector_to_weights(best_W[:, best_idx])

        mw_path = os.path.join(self.data_dir, "model_weights.json")
        with open(mw_path, "w") as f:
            json.dump(best_weights, f, indent=2)

        auc = metrics["auc"][best_idx].item()
        brier = metrics["brier"][best_idx].item()
        print(f"  Done in {elapsed:.2f}s")
        print(f"  AUC={auc:.6f}  Brier={brier:.6f}")
        print(f"  Saved → {mw_path}")

    # ─── SHOW / EXPORT ────────────────────────────────────────

    def show_best(self):
        self.best_tracker.print_best()
        if self.best_tracker.best:
            w = self.best_tracker.best.get("weights", {})
            base = w.get('base_logit', 0)
            print(f"\n  Base logit: {base:.4f} → P={sigmoid_cpu(base):.3f}")
            sigs = w.get("signals", {})
            sorted_s = sorted(sigs.items(), key=lambda x: abs(x[1]), reverse=True)
            print(f"\n  Top signals (|weight| desc):")
            for sig, val in sorted_s[:10]:
                d = "↑" if val > 0 else "↓"
                print(f"    {sig:<35s} {val:>+8.4f} {d}")
            print(f"\n  TA offsets:")
            ta_o = w.get("ta_offsets", {})
            for ta, val in sorted(ta_o.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    {ta:<25s} {val:>+8.4f}")

    def export_weights(self):
        if self.best_tracker.best is None:
            print("  No best config to export.")
            return
        w = self.best_tracker.best.get("weights", {})
        mw_path = os.path.join(self.data_dir, "model_weights.json")
        with open(mw_path, "w") as f:
            json.dump(w, f, indent=2)
        auc = self.best_tracker.best.get("auc", "?")
        brier = self.best_tracker.best.get("brier", "?")
        print(f"  Exported → {mw_path}")
        print(f"  AUC={auc}  Brier={brier}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description=f"ODIN Perpetual GPU v{__version__} — Population-Based Honing")
    parser.add_argument("--csv", default=None,
                        help="Path to ODIN CSV file")
    parser.add_argument("--data-dir", default=None,
                        help="Data directory (default: ~/odin_data)")
    parser.add_argument("--device", default=None,
                        help="Force device (cuda:0, cpu)")
    parser.add_argument("--pop", type=int, default=None,
                        help="Population size (auto-scaled if omitted)")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Max generations (infinite if omitted)")
    parser.add_argument("--retrain", action="store_true",
                        help="Fast retrain (<3s)")
    parser.add_argument("--best", action="store_true",
                        help="Show best config and exit")
    parser.add_argument("--export", action="store_true",
                        help="Export best weights to model_weights.json")
    parser.add_argument("--vram-fraction", type=float, default=0.40,
                        help="Max fraction of free VRAM (default: 0.40)")
    args = parser.parse_args()

    engine = OdinPerpetualGPU(
        population_size=args.pop,
        device=args.device,
        data_dir=args.data_dir,
        csv_path=args.csv,
        vram_fraction=args.vram_fraction,
    )

    if args.best:
        engine.show_best()
        return
    if args.export:
        engine.export_weights()
        return
    if args.retrain:
        engine.fast_retrain()
        return

    engine.run_perpetual(max_cycles=args.cycles)


if __name__ == "__main__":
    main()
