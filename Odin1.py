#!/usr/bin/env python3
"""
ODIN v9.0 Billion Search — Adaptive Exploration with Sobol Coverage

Fixes for "stuck" optimization:
1. Sobol quasi-random sequences for better parameter space coverage
2. Adaptive local refinement around top configs (70% of samples)
3. Stagnation detection - increases exploration when stuck
4. Diversity bonus in fitness
5. Progress shows improvements, not just best
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import hashlib
import platform
import gc
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd

# =============================================================================
# Sobol Sequence Generator (quasi-random for better coverage)
# =============================================================================

class SobolGenerator:
    """Simple Sobol sequence generator for quasi-random sampling"""
    
    # Direction numbers for first 30 dimensions (from Joe & Kuo)
    DIRECTION_NUMBERS = [
        [1], [1, 1], [1, 3, 1], [1, 1, 1], [1, 3, 3], [1, 3, 5, 13],
        [1, 1, 5, 5], [1, 3, 7, 11], [1, 1, 3, 15], [1, 3, 1, 15],
        [1, 1, 7, 7], [1, 3, 7, 5], [1, 1, 1, 9], [1, 3, 3, 9],
        [1, 1, 5, 11], [1, 3, 5, 7], [1, 1, 7, 13], [1, 3, 7, 1],
        [1, 1, 1, 3], [1, 3, 3, 5], [1, 1, 5, 15], [1, 3, 5, 3],
        [1, 1, 7, 9], [1, 3, 7, 15], [1, 1, 1, 13], [1, 3, 3, 15],
        [1, 1, 5, 1], [1, 3, 5, 9], [1, 1, 7, 3], [1, 3, 7, 13],
    ]
    
    def __init__(self, dim: int, seed: int = 0):
        self.dim = min(dim, 30)
        self.bits = 30
        self.scale = 2.0 ** self.bits
        
        # Initialize direction vectors
        self.V = np.zeros((self.bits, self.dim), dtype=np.uint32)
        for d in range(self.dim):
            m = self.DIRECTION_NUMBERS[d] if d < len(self.DIRECTION_NUMBERS) else [1]
            for i in range(self.bits):
                if i < len(m):
                    self.V[i, d] = m[i] << (self.bits - i - 1)
                else:
                    self.V[i, d] = self.V[i - len(m), d] ^ (self.V[i - len(m), d] >> len(m))
                    for k in range(1, len(m)):
                        self.V[i, d] ^= ((m[k] >> (len(m) - k - 1)) & 1) * self.V[i - k, d]
        
        self.x = np.zeros(self.dim, dtype=np.uint32)
        self.index = seed
        # Skip to seed position
        for _ in range(seed):
            self._next_point()
    
    def _next_point(self):
        c = 0
        n = self.index
        while n & 1:
            n >>= 1
            c += 1
        c = min(c, self.bits - 1)
        self.x ^= self.V[c]
        self.index += 1
        return self.x / self.scale
    
    def generate(self, n: int) -> np.ndarray:
        """Generate n quasi-random points in [0, 1]^dim"""
        points = np.zeros((n, self.dim), dtype=np.float32)
        for i in range(n):
            points[i] = self._next_point()
        return points


# =============================================================================
# GPU Detection
# =============================================================================

def detect_gpu():
    gpu_info = {"available": False, "name": "N/A", "vram_total_gb": 0.0, "vram_free_gb": 0.0}
    try:
        import cupy as cp
        _ = cp.array([1, 2, 3])
        dev = cp.cuda.Device()
        props = cp.cuda.runtime.getDeviceProperties(dev.id)
        free, total = cp.cuda.runtime.memGetInfo()
        gpu_info["available"] = True
        gpu_info["name"] = props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"])
        gpu_info["vram_total_gb"] = total / (1024**3)
        gpu_info["vram_free_gb"] = free / (1024**3)
        return True, cp, gpu_info
    except Exception as e:
        gpu_info["error"] = str(e)
        return False, None, gpu_info


def get_free_vram_gb(cp_module):
    try:
        free, _ = cp_module.cuda.runtime.memGetInfo()
        return free / (1024**3)
    except:
        return 0.0


def calculate_safe_batch_size(n_rows: int, free_vram_gb: float, safety_factor: float = 0.4) -> int:
    bytes_per_config = n_rows * 8 + 64
    available_bytes = free_vram_gb * (1024**3) * safety_factor
    max_batch = int(available_bytes / bytes_per_config)
    return max(10_000, min(max_batch, 500_000))


# =============================================================================
# Data Loading
# =============================================================================

def load_json_any(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Not found: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return json.loads(raw.decode("utf-8", errors="replace"))


def resolve_labels(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, int]:
    label_col = None
    for c in ["outcome", "label", "decision"]:
        if c in df.columns:
            label_col = c
            break
    if not label_col:
        raise ValueError("No label column")
    
    raw = df[label_col].fillna("").astype(str).str.upper()
    y = np.full((len(raw),), -1, dtype=np.int8)
    y[raw.isin(["APPROVAL", "APPROVED"]).to_numpy()] = 1
    y[raw.isin(["CRL", "COMPLETE RESPONSE LETTER"]).to_numpy()] = 0
    keep = (y >= 0)
    return y[keep], keep.astype(bool), int(np.sum(~keep))


# =============================================================================
# Feature Construction
# =============================================================================

FEATURE_KEYS = [
    "w_btd", "w_orphan", "w_priority", "w_fast", "w_accel", "w_exp", "w_stack",
    "w_form483", "w_form483_oai", "w_s22_cmc", "w_s23_trend", "w_prior_cmc_crl", "w_cmc_hiring",
    "adj_pain", "adj_cns", "adj_onco", "adj_inf",
    "adj_cns_amp", "w_adcom", "w_des_trap",
    "w_s17_sentiment", "w_s18_engagement", "w_s19_silence", "w_s20_divergence",
]
EXTRA_KEYS = ["p_base", "p_threshold"]


def build_features(df: pd.DataFrame, lunarcrush: Dict) -> np.ndarray:
    n = len(df)
    def col_float(name, default=0.0):
        return df[name].fillna(default).astype(np.float32).to_numpy() if name in df.columns else np.full((n,), default, dtype=np.float32)
    def col_bool(name):
        return df[name].fillna(False).astype(bool).astype(np.float32).to_numpy() if name in df.columns else np.zeros((n,), dtype=np.float32)
    
    btd = col_bool("btd")
    orphan = col_bool("orphan")
    priority = col_bool("priority_review")
    fast = col_bool("fast_track")
    accel = col_float("accelerated_approval", 0.0)
    exp = col_bool("experienced_sponsor")
    stack = col_float("designation_stack_count", 0.0)
    form483 = col_bool("form_483_issues")
    form483_oai = col_float("form_483_oai_flag", 0.0)
    cmc_scaled = col_float("cmc_citation_count", 0.0)
    insp_trend = col_float("inspection_trend", 0.0)
    cmc_hiring = col_float("cmc_hiring_signal", 0.0)
    
    prior_crl = col_bool("prior_crl")
    prior_reason = df["prior_crl_reason"].fillna("").astype(str).str.lower() if "prior_crl_reason" in df.columns else pd.Series([""] * n)
    prior_cmc_crl = prior_crl * prior_reason.str.contains(r"cmc|chemistry|manufactur", na=False).astype(np.float32).to_numpy()
    
    ta = df["therapeutic_area"].fillna("").astype(str).str.lower() if "therapeutic_area" in df.columns else pd.Series([""] * n)
    is_pain = ta.str.contains("pain", na=False).astype(np.float32).to_numpy()
    is_cns = ta.str.contains(r"cns|neuro|psych", na=False).astype(np.float32).to_numpy()
    is_onco = ta.str.contains(r"onc|cancer|tumor", na=False).astype(np.float32).to_numpy()
    is_inf = ta.str.contains(r"infect|viral|bacter", na=False).astype(np.float32).to_numpy()
    
    had_adcom = col_bool("had_adcom")
    vote = col_float("adcom_vote_pct", 50.0)
    vote_scaled = had_adcom * ((vote - 50.0) / 50.0)
    cns_adcom = is_cns * had_adcom
    trap = (stack >= 4).astype(np.float32) * (1.0 - exp)
    
    s17, s18, s19, s20 = [np.zeros((n,), dtype=np.float32) for _ in range(4)]
    if lunarcrush:
        tickers = df["ticker"].fillna("").astype(str).to_numpy()
        for i, t in enumerate(tickers):
            if t in lunarcrush:
                lc = lunarcrush[t]
                s17[i] = float(lc.get("s17_social_sentiment", 0) or 0)
                s18[i] = float(lc.get("s18_engagement_spike", 0) or 0)
                s19[i] = float(lc.get("s19_social_silence", 0) or 0)
                s20[i] = float(lc.get("s20_smart_money_divergence", 0) or 0)
    
    return np.stack([
        btd, orphan, priority, fast, accel, exp, stack,
        form483, form483_oai, cmc_scaled, insp_trend, prior_cmc_crl, cmc_hiring,
        is_pain, is_cns, is_onco, is_inf, cns_adcom, vote_scaled, trap,
        s17, s18, s19, s20,
    ], axis=1).astype(np.float32)


# =============================================================================
# Bounds & Adaptive Sampling
# =============================================================================

BOUNDS = {
    "p_base": (0.65, 0.95), "p_threshold": (0.65, 0.95),
    "w_btd": (-0.10, 0.20), "w_orphan": (-0.10, 0.15), "w_priority": (-0.10, 0.15),
    "w_fast": (-0.10, 0.15), "w_accel": (-0.15, 0.15), "w_exp": (-0.05, 0.20), "w_stack": (-0.10, 0.10),
    "w_form483": (-0.40, 0.10), "w_form483_oai": (-0.50, 0.10), "w_s22_cmc": (-0.40, 0.05),
    "w_s23_trend": (-0.10, 0.40), "w_prior_cmc_crl": (-0.40, 0.10), "w_cmc_hiring": (-0.30, 0.15),
    "adj_pain": (-0.35, 0.10), "adj_cns": (-0.25, 0.15), "adj_onco": (-0.15, 0.20), "adj_inf": (-0.10, 0.20),
    "adj_cns_amp": (-0.25, 0.15), "w_adcom": (-0.30, 0.40), "w_des_trap": (-0.40, 0.10),
    "w_s17_sentiment": (-0.15, 0.20), "w_s18_engagement": (-0.15, 0.20),
    "w_s19_silence": (-0.30, 0.10), "w_s20_divergence": (-0.25, 0.10),
}


def sample_configs_adaptive(rng: np.random.Generator, sobol: SobolGenerator, n: int, 
                            param_keys: List[str], hall: List[Dict],
                            explore_ratio: float = 0.3, sigma: float = 0.15) -> np.ndarray:
    """
    Adaptive sampling with three modes:
    1. Sobol quasi-random exploration (explore_ratio * 0.5)
    2. Pure random exploration (explore_ratio * 0.5)  
    3. Local refinement around best configs (1 - explore_ratio)
    """
    P = len(param_keys)
    lo = np.array([BOUNDS.get(k, (-0.1, 0.1))[0] for k in param_keys], dtype=np.float32)
    hi = np.array([BOUNDS.get(k, (-0.1, 0.1))[1] for k in param_keys], dtype=np.float32)
    span = hi - lo
    
    out = np.zeros((n, P), dtype=np.float32)
    
    n_sobol = int(n * explore_ratio * 0.5)
    n_random = int(n * explore_ratio * 0.5)
    n_local = n - n_sobol - n_random
    
    # 1. Sobol quasi-random for systematic coverage
    if n_sobol > 0:
        sobol_points = sobol.generate(n_sobol)
        # Extend to full dimension if needed
        if sobol_points.shape[1] < P:
            extra = rng.random((n_sobol, P - sobol_points.shape[1]), dtype=np.float32)
            sobol_points = np.hstack([sobol_points, extra])
        out[:n_sobol] = lo + sobol_points[:, :P] * span
    
    # 2. Pure random for diversity
    if n_random > 0:
        out[n_sobol:n_sobol+n_random] = lo + rng.random((n_random, P), dtype=np.float32) * span
    
    # 3. Local refinement around best configs
    if n_local > 0 and hall:
        # Pick from top configs
        seed_params = [e["params"] for e in hall[:min(20, len(hall))]]
        seed_mat = np.array([[float(s.get(k, 0.0)) for k in param_keys] for s in seed_params], dtype=np.float32)
        
        pick_idx = rng.integers(0, len(seed_mat), size=n_local)
        base = seed_mat[pick_idx]
        
        # Gaussian perturbation
        noise = rng.standard_normal((n_local, P)).astype(np.float32) * sigma * span
        out[n_sobol+n_random:] = np.clip(base + noise, lo, hi)
    elif n_local > 0:
        # No hall yet, use random
        out[n_sobol+n_random:] = lo + rng.random((n_local, P), dtype=np.float32) * span
    
    # Shuffle to mix exploration and refinement
    rng.shuffle(out, axis=0)
    return out


# =============================================================================
# Metrics
# =============================================================================

def safe_mcc(tp, fp, tn, fn, xp):
    num = tp * tn - fp * fn
    denom = xp.sqrt(xp.maximum((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn), xp.float32(1e-12)))
    return num / denom


def pack_entry(params, metrics, fitness):
    h = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    return {"run_hash": h, "params": params, "metrics": metrics, "fitness": fitness,
            "timestamp": datetime.now(timezone.utc).isoformat()}


# =============================================================================
# Main
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="ODIN v9.0 Billion Search - Adaptive Exploration")
    ap.add_argument("--data", required=True)
    ap.add_argument("--lunarcrush", default="")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--iters", type=int, default=1_000_000_000)
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--min-precision", type=float, default=0.89)
    ap.add_argument("--min-recall", type=float, default=0.80)
    ap.add_argument("--device", choices=["auto", "cpu", "gpu"], default="auto")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--topk", type=int, default=100)
    ap.add_argument("--explore-ratio", type=float, default=0.30, help="Fraction for global exploration (default 0.30)")
    # New arguments for resume and checkpointing
    ap.add_argument("--resume", default=None, help="Resume from checkpoint in given directory (expects checkpoint.json)")
    ap.add_argument("--save-interval", type=int, default=0, help="Save progress every N processed configs (0 to disable)")
    # Optional initial sigma for adaptive local search
    ap.add_argument("--sigma-initial", type=float, default=0.15, help="Initial sigma for local Gaussian perturbation")
    args = ap.parse_args()
    
    os.makedirs(args.outdir, exist_ok=True)
    
    print("=" * 70)
    print("ODIN v9.0 BILLION SEARCH — Adaptive Exploration Edition")
    print("=" * 70)
    
    # GPU detection
    has_gpu, cp, gpu_info = detect_gpu()
    use_gpu = (args.device != "cpu") and has_gpu
    
    if use_gpu:
        print(f"GPU: {gpu_info['name']} ({gpu_info['vram_free_gb']:.1f}GB free)")
        xp = cp
    else:
        print("Using CPU")
        xp = np
    
    # Load data
    print("\nLoading data...")
    df = pd.read_csv(args.data)
    y, keep_mask, dropped = resolve_labels(df)
    if dropped:
        df = df.loc[keep_mask].reset_index(drop=True)
    
    y_pos, y_neg = int((y == 1).sum()), int((y == 0).sum())
    print(f"  {len(df)} rows: {y_pos} approvals, {y_neg} CRLs")
    
    lunarcrush = {}
    for path in [args.lunarcrush, "lunarcrush_cache.json"]:
        if path and os.path.exists(path):
            try:
                lunarcrush = load_json_any(path)
                print(f"  LunarCrush: {len(lunarcrush)} tickers")
                break
            except:
                pass
    
    F_np = build_features(df, lunarcrush)
    n_rows, n_features = F_np.shape
    
    # Transfer to GPU
    if use_gpu:
        F = xp.asarray(F_np, dtype=xp.float32)
        y_xp = xp.asarray(y.astype(np.float32))
        cp.cuda.Stream.null.synchronize()
    else:
        F = F_np.astype(np.float32)
        y_xp = y.astype(np.float32)
    
    y1 = (y_xp > 0.5).astype(xp.float32)
    y0 = (y_xp <= 0.5).astype(xp.float32)
    n_rows_f = xp.float32(n_rows)
    y_pos_f = xp.float32(y_pos)
    y_neg_f = xp.float32(y_neg)
    y_mean_f = xp.float32(y.mean())
    
    param_keys = FEATURE_KEYS + EXTRA_KEYS
    key_to_idx = {k: i for i, k in enumerate(param_keys)}
    w_idx = [key_to_idx[k] for k in FEATURE_KEYS]
    
    # Batch sizing
    if args.batch > 0:
        batch_size = args.batch
    elif use_gpu:
        free_vram = get_free_vram_gb(cp)
        batch_size = calculate_safe_batch_size(n_rows, free_vram)
    else:
        batch_size = 100_000
    
    # Warm-up
    print(f"\n  Testing batch size {batch_size:,}...")
    for attempt in range(5):
        try:
            if use_gpu:
                cp.get_default_memory_pool().free_all_blocks()
            test = np.random.rand(batch_size, len(param_keys)).astype(np.float32)
            W = test[:, w_idx].T
            if use_gpu:
                W = xp.asarray(W, dtype=xp.float32)
            pmat = F.dot(W)
            pred = (pmat > 0.5).astype(xp.float32)
            _ = xp.sum(pred, axis=0)
            del pmat, pred, W, test
            if use_gpu:
                cp.get_default_memory_pool().free_all_blocks()
            print(f"  ✓ Batch size {batch_size:,} OK")
            break
        except:
            batch_size = max(10_000, batch_size // 2)
            print(f"  ✗ Reducing to {batch_size:,}")
    
    # Initialize
    rng = np.random.default_rng(args.seed)
    # Sigma for local perturbation (adaptive)
    sigma = float(args.sigma_initial)
    # Sobol generator (we'll restore state if resuming)
    sobol_seed = args.seed
    sobol = SobolGenerator(dim=min(len(param_keys), 30), seed=sobol_seed)
    total = args.iters
    processed = 0
    best_entry = None
    hall = []
    t0 = time.time()

    # Tracking
    last_improvement = 0
    stagnation_batches = 0
    explore_ratio = args.explore_ratio
    total_feasible = 0
    unique_fp_counts = set()

    # Resume from checkpoint if requested
    if args.resume:
        ckpt_file = os.path.join(args.resume, "checkpoint.json")
        if os.path.exists(ckpt_file):
            try:
                with open(ckpt_file, "r") as f:
                    ckpt = json.load(f)
                processed = ckpt.get("processed", 0)
                best_entry = ckpt.get("best_entry")
                hall = ckpt.get("hall", [])
                explore_ratio = ckpt.get("explore_ratio", explore_ratio)
                stagnation_batches = ckpt.get("stagnation_batches", 0)
                sigma = ckpt.get("sigma", sigma)
                # Restore RNG state
                state = ckpt.get("rng_state")
                if state:
                    rng = np.random.default_rng()
                    rng.bit_generator.state = state
                # Restore Sobol index by using seed equal to index (skip ahead)
                sobol_index = ckpt.get("sobol_index", 0)
                sobol = SobolGenerator(dim=min(len(param_keys), 30), seed=sobol_index)
                unique_fp_counts = set(ckpt.get("unique_fp_counts", []))
                print(f"Resumed from {ckpt_file} at processed={processed}")
            except Exception as e:
                print(f"⚠ Could not load checkpoint {ckpt_file}: {e}")

    print(f"\n  Exploration ratio: {explore_ratio*100:.0f}% global, {(1-explore_ratio)*100:.0f}% local refinement")
    print(f"  Initial sigma: {sigma}")

    print("\n" + "=" * 70)
    print(f"Starting: {total:,} iterations | Batch: {batch_size:,}")
    print("=" * 70 + "\n")

    batch_num = 0
    
    while processed < total:
        cur = min(batch_size, total - processed)
        
        try:
            # Adaptive sampling with adjustable sigma
            params_mat = sample_configs_adaptive(
                rng, sobol, cur, param_keys, hall,
                explore_ratio=explore_ratio, sigma=sigma
            )
            
            W = params_mat[:, w_idx].T
            p_base = params_mat[:, key_to_idx["p_base"]]
            p_thr = params_mat[:, key_to_idx["p_threshold"]]
            
            if use_gpu:
                W = xp.asarray(W, dtype=xp.float32)
                p_base = xp.asarray(p_base, dtype=xp.float32)
                p_thr = xp.asarray(p_thr, dtype=xp.float32)
            
            # Core computation
            pmat = p_base[None, :] + F.dot(W)
            pmat = xp.clip(pmat, 0.001, 0.999)
            
            sum_p = xp.sum(pmat, axis=0)
            sum_p2 = xp.sum(pmat * pmat, axis=0)
            sum_py = xp.sum(pmat * y1[:, None], axis=0)
            
            pred = (pmat >= p_thr[None, :]).astype(xp.float32)
            tp = xp.sum(pred * y1[:, None], axis=0)
            fp = xp.sum(pred * y0[:, None], axis=0)
            
            del pmat, pred
            
            # Metrics
            brier = (sum_p2 / n_rows_f) - 2.0 * (sum_py / n_rows_f) + y_mean_f
            fn = y_pos_f - tp
            tn = y_neg_f - fp
            
            precision = tp / xp.maximum(tp + fp, 1e-12)
            recall = tp / xp.maximum(tp + fn, 1e-12)
            f1 = 2.0 * precision * recall / xp.maximum(precision + recall, 1e-12)
            specificity = tn / xp.maximum(tn + fp, 1e-12)
            mcc = safe_mcc(tp, fp, tn, fn, xp)
            
            # Feasibility
            feasible = (precision >= args.min_precision) & (recall >= args.min_recall)
            
            # Fitness with multiple objectives
            fit = xp.where(
                feasible,
                # Primary: minimize FP
                xp.float64(1e9) - 1e6 * fp.astype(xp.float64) 
                # Secondary: minimize Brier
                - 1e5 * brier.astype(xp.float64)
                # Tertiary: maximize MCC (balance)
                + 1e4 * mcc.astype(xp.float64) 
                # Quaternary: maximize specificity
                + 1e3 * specificity.astype(xp.float64)
                # Fifth: maximize F1
                + 100.0 * f1.astype(xp.float64),
                xp.float64(-1e18),
            )
            
            # Get top configs
            fit_cpu = cp.asnumpy(fit) if use_gpu else fit
            
            n_feasible_batch = int(np.sum(fit_cpu > -1e17))
            total_feasible += n_feasible_batch
            
            topM = min(256, cur)
            top_idx = np.argpartition(-fit_cpu, kth=max(0, topM - 1))[:topM]
            top_idx = top_idx[np.argsort(-fit_cpu[top_idx])]
            
            def cpu_vec(arr):
                return cp.asnumpy(arr) if use_gpu else np.asarray(arr)
            
            improved = False
            for idx in top_idx:
                if fit_cpu[idx] < -1e17:
                    continue
                params = {k: float(params_mat[idx, key_to_idx[k]]) for k in param_keys}
                fp_val = int(cpu_vec(fp)[idx])
                unique_fp_counts.add(fp_val)
                
                metrics = {
                    "precision": float(cpu_vec(precision)[idx]),
                    "recall": float(cpu_vec(recall)[idx]),
                    "f1": float(cpu_vec(f1)[idx]),
                    "specificity": float(cpu_vec(specificity)[idx]),
                    "mcc": float(cpu_vec(mcc)[idx]),
                    "brier": float(cpu_vec(brier)[idx]),
                    "tp": int(cpu_vec(tp)[idx]),
                    "fp": fp_val,
                }
                entry = pack_entry(params, metrics, float(fit_cpu[idx]))
                
                if best_entry is None or entry["fitness"] > best_entry["fitness"]:
                    best_entry = entry
                    improved = True
                    last_improvement = processed
                
                hall.append(entry)
            
            # Deduplicate hall (keep best per hash AND per FP count for diversity)
            by_hash = {}
            by_fp = {}
            for e in hall:
                h = e["run_hash"]
                fp_val = e["metrics"]["fp"]
                if h not in by_hash or e["fitness"] > by_hash[h]["fitness"]:
                    by_hash[h] = e
                if fp_val not in by_fp or e["fitness"] > by_fp[fp_val]["fitness"]:
                    by_fp[fp_val] = e
            
            # Merge: unique by hash, plus best per FP for diversity
            combined = list(by_hash.values())
            for e in by_fp.values():
                if e["run_hash"] not in by_hash:
                    combined.append(e)
            
            hall = sorted(combined, key=lambda x: x["fitness"], reverse=True)[:args.topk]
            
            processed += cur
            batch_num += 1
            
            # Stagnation detection and adaptive sigma
            if improved:
                stagnation_batches = 0
                # When improvement occurs, tighten local search by reducing sigma
                sigma = max(0.01, sigma * 0.8)
            else:
                stagnation_batches += 1
            
            # Increase exploration and broaden sigma if stagnant for many batches
            if stagnation_batches > 50:
                explore_ratio = min(0.8, explore_ratio + 0.1)
                sigma = min(0.4, sigma * 1.5)
                stagnation_batches = 0
                print(f"\n  ⚠ Stagnation detected! Increasing exploration to {explore_ratio*100:.0f}% and sigma to {sigma:.3f}\n")
            
            # Cleanup
            del W, p_base, p_thr, sum_p, sum_p2, sum_py, tp, fp, tn, fn
            del precision, recall, f1, specificity, mcc, brier, fit, feasible
            
            if use_gpu and batch_num % 5 == 0:
                cp.get_default_memory_pool().free_all_blocks()
            
        except Exception as e:
            if "OutOfMemory" in str(type(e).__name__):
                batch_size = max(10_000, batch_size * 2 // 3)
                print(f"\n  ⚠ OOM! Reducing batch to {batch_size:,}")
                if use_gpu:
                    cp.get_default_memory_pool().free_all_blocks()
                gc.collect()
                continue
            raise
        
        # Progress
        elapsed = time.time() - t0
        pct = 100.0 * processed / total
        speed = processed / max(1e-9, elapsed)
        eta = (total - processed) / max(1, speed)
        eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta/60:.1f}m" if eta < 3600 else f"{eta/3600:.1f}h"
        
        m = hall[0]["metrics"] if hall else {}
        
        # Diversity info
        fp_range = f"FP range: {min(unique_fp_counts)}-{max(unique_fp_counts)}" if unique_fp_counts else ""
        
        vram_str = ""
        if use_gpu:
            try:
                free = get_free_vram_gb(cp)
                vram_str = f"VRAM:{free:.1f}GB"
            except:
                pass
        
        improved_str = "★" if improved else " "
        
        print(
            f"[{pct:5.2f}%]{improved_str} {processed:,} | {speed:,.0f}/s | ETA:{eta_str} | {vram_str} | "
            f"best(fp={m.get('fp', -1)}, spec={m.get('specificity', 0):.4f}, mcc={m.get('mcc', 0):.4f}) | "
            f"uniq_fp:{len(unique_fp_counts)} exp:{explore_ratio*100:.0f}% sigma:{sigma:.3f}"
        )

        # Periodic checkpoint saving
        if args.save_interval > 0 and processed > 0 and (processed % args.save_interval) == 0:
            checkpoint = {
                "processed": processed,
                "best_entry": best_entry,
                "hall": hall,
                "explore_ratio": explore_ratio,
                "stagnation_batches": stagnation_batches,
                "sigma": sigma,
                "sobol_index": sobol.index,
                "rng_state": rng.bit_generator.state,
                "unique_fp_counts": list(unique_fp_counts)
            }
            ckpt_path = os.path.join(args.outdir, "checkpoint.json")
            tmp_path = ckpt_path + ".tmp"
            try:
                with open(tmp_path, "w") as f:
                    json.dump(checkpoint, f)
                os.replace(tmp_path, ckpt_path)
                # Also save best and hall
                if best_entry:
                    with open(os.path.join(args.outdir, "best.json"), "w") as f:
                        json.dump(best_entry, f)
                with open(os.path.join(args.outdir, "hall_of_fame.json"), "w") as f:
                    json.dump(hall, f)
                # Append to progress file
                progress = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_sampled": processed,
                    "total_feasible": total_feasible,
                    "best_brier": best_entry["metrics"]["brier"] if best_entry else None,
                    "batch_size": batch_size,
                    "explore_ratio": explore_ratio,
                    "sigma": sigma,
                    "top_fp_range": [min(unique_fp_counts) if unique_fp_counts else 0,
                                      max(unique_fp_counts) if unique_fp_counts else 0]
                }
                with open(os.path.join(args.outdir, "progress.jsonl"), "a") as f:
                    f.write(json.dumps(progress) + "\n")
                print(f"\n  ✓ Saved checkpoint at {processed:,} configs (sigma={sigma:.3f}, explore={explore_ratio:.2f})\n")
            except Exception as e:
                print(f"\n  ⚠ Failed to save checkpoint: {e}\n")
    
    # Final output
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    
    elapsed = time.time() - t0
    print(f"\nProcessed {processed:,} in {elapsed:.1f}s ({processed/elapsed:,.0f} cfg/s)")
    print(f"Total feasible configs found: {total_feasible:,}")
    print(f"Unique FP values explored: {sorted(unique_fp_counts)}")
    
    if best_entry:
        m = best_entry["metrics"]
        print(f"\nBest: Prec={m['precision']:.4f} Rec={m['recall']:.4f} Spec={m['specificity']:.4f} "
              f"MCC={m['mcc']:.4f} FP={m['fp']}")
        
        with open(os.path.join(args.outdir, "best.json"), "w") as f:
            json.dump(best_entry, f, indent=2)
    
    # Save hall with FP diversity info
    print(f"\nHall of Fame ({len(hall)} configs):")
    fp_in_hall = sorted(set(e["metrics"]["fp"] for e in hall))
    print(f"  FP values in hall: {fp_in_hall}")
    
    with open(os.path.join(args.outdir, "hall_of_fame.json"), "w") as f:
        json.dump(hall, f, indent=2)
    
    # Summary by FP
    print("\nBest config per FP count:")
    by_fp_best = {}
    for e in hall:
        fp_val = e["metrics"]["fp"]
        if fp_val not in by_fp_best or e["fitness"] > by_fp_best[fp_val]["fitness"]:
            by_fp_best[fp_val] = e
    
    for fp_val in sorted(by_fp_best.keys())[:10]:
        m = by_fp_best[fp_val]["metrics"]
        print(f"  FP={fp_val:3d}: Prec={m['precision']:.4f} Rec={m['recall']:.4f} Spec={m['specificity']:.4f} MCC={m['mcc']:.4f}")
    
    print(f"\nSaved to {args.outdir}/")


if __name__ == "__main__":
    main()
