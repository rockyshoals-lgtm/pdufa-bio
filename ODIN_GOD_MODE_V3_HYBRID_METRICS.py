#!/usr/bin/env python3
"""
ODIN GOD MODE V6 — GPU CONFIG SEARCH ENGINE (RTX 4070 / CUDA) - T-1 LEAKAGE FIX
--------------------------------------------------------------------------------
CRITICAL FIX FROM V5:
  - FIXED manufacturing_risk T-1 LEAKAGE
  - Old feature had 47.7% CRL rate (derived from post-decision CRL reasons)
  - New feature uses modality_complexity (Small Molecule flag) - T-1 safe
  - New feature has 15.1% CRL rate (legitimate pre-decision signal)
  - Adjusted w_mfg_pen bounds from [-0.70,-0.20] to [-0.15,-0.02]
  - Signal is ~5x weaker but CLEAN (no data leakage)

CHANGES FROM V5:
  1. FIXED T-1 leakage in manufacturing_risk feature
  2. Updated bounds for w_mfg_pen, w_mfg_amp, i_mfg_inexp
  3. Added documentation of T-1 compliance for all features

INHERITED FROM V5:
  - Fixed FP normalization bug (was /25, now dynamic /n_crl)
  - Excel (.xlsx) file support
  - --recall_min constraint to prevent over-conservative models
  - Objective balances Brier, F1, and Specificity

T-1 COMPLIANCE VERIFICATION:
  All features used in scoring are available BEFORE PDUFA decision:
  - btd, orphan, priority, fast, accel: Designations granted during development
  - exp/inexp: Historical sponsor approval count
  - mfg (NOW): Small molecule modality flag (known at IND stage)
  - therapeutic area flags: Known from drug development
  - adcom_vote_pct: AdCom occurs before PDUFA
  - class1_cmc, des_trap: Protocol flags (currently always 0)

Inputs:
  - ODIN_PDUFA_1349_GPU_READY_T1_FIXED.csv (or .xlsx or .npz)

Outputs:
  - JSON of top configurations (by objective + constraints)

"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional

import numpy as np

# --------------------------
# GPU import + device info
# --------------------------
try:
    import cupy as cp
    from cupy import cuda
except Exception as e:
    print("❌ CuPy is required for GPU mode.")
    print("   Install with: pip install cupy-cuda12x")
    print(f"   Import error: {e}")
    sys.exit(1)


# --------------------------
# FUSED CUDA KERNEL
# --------------------------
SCORING_KERNEL = cp.RawKernel(r"""
extern "C" __global__
void fused_score_kernel(
    // Feature arrays (length N)
    const int* __restrict__ btd,
    const int* __restrict__ orphan,
    const int* __restrict__ priority,
    const int* __restrict__ fast,
    const int* __restrict__ accel,
    const int* __restrict__ exp,
    const int* __restrict__ inexp,
    const int* __restrict__ mfg,
    const int* __restrict__ pain,
    const int* __restrict__ cns,
    const int* __restrict__ onco,
    const int* __restrict__ inf,
    const int* __restrict__ stack,
    const int* __restrict__ class1_cmc,
    const int* __restrict__ des_trap,
    const float* __restrict__ adcom_pct,
    const int* __restrict__ y_true,

    // Parameter arrays (length B)
    const float* __restrict__ p_base,
    const float* __restrict__ p_threshold,
    const float* __restrict__ w_btd,
    const float* __restrict__ w_orphan,
    const float* __restrict__ w_priority,
    const float* __restrict__ w_fast,
    const float* __restrict__ w_accel,
    const float* __restrict__ w_exp,
    const float* __restrict__ w_stack,
    const float* __restrict__ w_mfg_pen,
    const float* __restrict__ w_mfg_amp,
    const float* __restrict__ adj_pain,
    const float* __restrict__ adj_cns,
    const float* __restrict__ adj_cns_amp,
    const float* __restrict__ adj_onco,
    const float* __restrict__ adj_inf,
    const float* __restrict__ w_adcom,
    const float* __restrict__ i_mfg_inexp,
    const float* __restrict__ w_des_trap,

    // Outputs (length B)
    float* __restrict__ out_brier,
    int* __restrict__ out_tp,
    int* __restrict__ out_fp,
    int* __restrict__ out_tn,
    int* __restrict__ out_fn,

    // Dimensions
    int N, int B
) {
    int config_idx = blockIdx.x;
    if (config_idx >= B) return;

    // Load params into registers
    float base = p_base[config_idx];
    float thr  = p_threshold[config_idx];

    float pw_btd      = w_btd[config_idx];
    float pw_orphan   = w_orphan[config_idx];
    float pw_priority = w_priority[config_idx];
    float pw_fast     = w_fast[config_idx];
    float pw_accel    = w_accel[config_idx];
    float pw_exp      = w_exp[config_idx];
    float pw_stack    = w_stack[config_idx];

    float pw_mfg_pen  = w_mfg_pen[config_idx];
    float pw_mfg_amp  = w_mfg_amp[config_idx];
    float pi_mfg_inexp = i_mfg_inexp[config_idx];

    float padj_pain   = adj_pain[config_idx];
    float padj_cns    = adj_cns[config_idx];
    float padj_cns_amp = adj_cns_amp[config_idx];
    float padj_onco   = adj_onco[config_idx];
    float padj_inf    = adj_inf[config_idx];

    float pw_adcom    = w_adcom[config_idx];
    float pw_des_trap = w_des_trap[config_idx];

    // Shared reduction buffers
    __shared__ float s_brier[256];
    __shared__ int s_tp[256];
    __shared__ int s_fp[256];
    __shared__ int s_tn[256];
    __shared__ int s_fn[256];

    int tid = threadIdx.x;

    float local_brier = 0.0f;
    int local_tp = 0, local_fp = 0, local_tn = 0, local_fn = 0;

    // Each thread processes multiple samples
    for (int i = tid; i < N; i += blockDim.x) {

        // P001 override: class-1 CMC resubmission
        float prob;
        if (class1_cmc[i] == 1) {
            prob = 0.995f;
        } else {
            float score = base;

            // Core designation boosts
            score += btd[i]      * pw_btd;
            score += orphan[i]   * pw_orphan;
            score += priority[i] * pw_priority;
            score += fast[i]     * pw_fast;
            score += accel[i]    * pw_accel;

            // Experience
            score += exp[i] * pw_exp;

            // Stack (simple linear)
            score += ((float)stack[i]) * pw_stack;

            // P003 designation trap
            score += des_trap[i] * pw_des_trap;

            // Manufacturing interaction (inexp amplifies penalty)
            float eff_pen = pw_mfg_pen * (1.0f + (pi_mfg_inexp - 1.0f) * inexp[i]);
            score += mfg[i] * eff_pen * pw_mfg_amp;

            // Therapeutic areas
            score += pain[i] * padj_pain;
            score += onco[i] * padj_onco;
            score += inf[i]  * padj_inf;

            // CNS interaction (amplify if inexperienced)
            float cns_adj = padj_cns + (padj_cns_amp * inexp[i]);
            score += cns[i] * cns_adj;

            // AdCom vote (0..1)
            score += adcom_pct[i] * pw_adcom;

            // Clamp probability
            prob = fminf(0.99f, fmaxf(0.01f, score));
        }

        int truth = y_true[i];
        int pred = (prob >= thr) ? 1 : 0;

        float diff = prob - (float)truth;
        local_brier += diff * diff;

        local_tp += (pred == 1 && truth == 1);
        local_fp += (pred == 1 && truth == 0);
        local_tn += (pred == 0 && truth == 0);
        local_fn += (pred == 0 && truth == 1);
    }

    // Reduce
    s_brier[tid] = local_brier;
    s_tp[tid] = local_tp;
    s_fp[tid] = local_fp;
    s_tn[tid] = local_tn;
    s_fn[tid] = local_fn;
    __syncthreads();

    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            s_brier[tid] += s_brier[tid + s];
            s_tp[tid] += s_tp[tid + s];
            s_fp[tid] += s_fp[tid + s];
            s_tn[tid] += s_tn[tid + s];
            s_fn[tid] += s_fn[tid + s];
        }
        __syncthreads();
    }

    if (tid == 0) {
        out_brier[config_idx] = s_brier[0] / (float)N;
        out_tp[config_idx] = s_tp[0];
        out_fp[config_idx] = s_fp[0];
        out_tn[config_idx] = s_tn[0];
        out_fn[config_idx] = s_fn[0];
    }
}
""", "fused_score_kernel")


@dataclass
class Bounds:
    low: float
    high: float


def _device_banner(device_id: int = 0) -> None:
    d = cuda.Device(device_id)
    d.use()
    props = cp.cuda.runtime.getDeviceProperties(device_id)
    name = props["name"].decode() if isinstance(props["name"], (bytes, bytearray)) else str(props["name"])
    free_mem, total_mem = d.mem_info
    sm = props.get("multiProcessorCount", "?")
    cc_major = props.get("major", "?")
    cc_minor = props.get("minor", "?")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 GPU: {name}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 VRAM: {total_mem/1e9:.1f} GB ({free_mem/1e9:.1f} GB free)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 SMs: {sm} | CC: {cc_major}.{cc_minor}")


class ODINRTXV6Engine:
    """GPU search engine - V6 with T-1 LEAKAGE FIX."""

    def __init__(
        self,
        data_path: str,
        batch_size: int,
        seed: int,
        device_id: int,
        split: str,
        precision_min: float,
        recall_min: float,
        topk: int,
        objective: str,
    ) -> None:
        self.data_path = data_path
        self.batch_size = int(batch_size)
        self.seed = int(seed)
        self.device_id = int(device_id)
        self.split = split
        self.precision_min = float(precision_min)
        self.recall_min = float(recall_min)
        self.topk = int(topk)
        self.objective = str(objective).lower().strip()

        _device_banner(self.device_id)

        self.bounds: Dict[str, Bounds] = self._default_bounds()
        self.param_names: List[str] = list(self.bounds.keys())

        # Best configs (CPU-side list)
        self.top: List[Dict[str, Any]] = []

        # Load data -> CPU numpy -> filter -> GPU arrays
        self._load_data()

        # Preallocate buffers
        self._allocate()

        # RNG
        self.rng = cp.random.default_rng(self.seed)

    def _default_bounds(self) -> Dict[str, Bounds]:
        return {
            # Base and threshold - allow lower thresholds for better recall
            "p_base": Bounds(0.70, 0.92),
            "p_threshold": Bounds(0.40, 0.85),  # Lowered from 0.50-0.90

            "w_btd": Bounds(0.02, 0.16),
            "w_orphan": Bounds(0.00, 0.10),
            "w_priority": Bounds(0.02, 0.16),
            "w_fast": Bounds(0.00, 0.12),
            "w_accel": Bounds(0.00, 0.12),

            "w_exp": Bounds(0.00, 0.16),
            "w_stack": Bounds(0.00, 0.05),

            # T-1 FIX: manufacturing_risk now = simple_modality_risk (Small Molecule flag)
            # Old feature had ~11.5x CRL lift (LEAKAGE), new has ~1.4x (legitimate)
            # Bounds scaled down accordingly - penalty is much smaller
            "w_mfg_pen": Bounds(-0.15, -0.01),   # Was [-0.70, -0.20] - REDUCED
            "w_mfg_amp": Bounds(1.0, 1.5),        # Was [1.0, 2.0] - REDUCED
            "i_mfg_inexp": Bounds(0.9, 1.3),      # Was [0.9, 1.5] - REDUCED

            "adj_pain": Bounds(-0.55, -0.05),
            "adj_cns": Bounds(-0.35, 0.10),
            "adj_cns_amp": Bounds(-0.45, -0.05),
            "adj_onco": Bounds(-0.02, 0.20),
            "adj_inf": Bounds(-0.02, 0.25),

            "w_adcom": Bounds(0.00, 0.35),
            "w_des_trap": Bounds(-0.25, -0.03),
        }

    def _load_npz(self, path: str) -> Dict[str, np.ndarray]:
        data = dict(np.load(path))
        needed = [
            "y_true","btd","orphan","priority","fast","accel","exp","inexp","mfg",
            "pain","cns","onco","inf","stack","class1_cmc","des_trap","adcom_pct","split_code"
        ]
        missing = [k for k in needed if k not in data]
        if missing:
            raise ValueError(f"NPZ missing keys: {missing}")
        return data

    def _split_to_code(self, split: str) -> Optional[int]:
        split = split.lower().strip()
        if split in ("all","*", "any"):
            return None
        if split.startswith("train"):
            return 0
        if split.startswith("val"):
            return 1
        if split.startswith("test"):
            return 2
        raise ValueError("split must be one of: train, val, test, all")

    def _load_data(self) -> None:
        import pandas as pd
        
        path = self.data_path
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        if path.lower().endswith(".npz"):
            d = self._load_npz(path)

            split_code = d["split_code"].astype(np.int8)
            target_split = self._split_to_code(self.split)
            if target_split is None:
                mask = np.ones_like(split_code, dtype=bool)
            else:
                mask = (split_code == target_split)

            def filt(arr, dtype=None):
                out = arr[mask]
                return out.astype(dtype) if dtype is not None else out

            self.y_true = filt(d["y_true"], np.int32)
            self.N = int(self.y_true.shape[0])

            self.feat = {
                "btd": filt(d["btd"], np.int32),
                "orphan": filt(d["orphan"], np.int32),
                "priority": filt(d["priority"], np.int32),
                "fast": filt(d["fast"], np.int32),
                "accel": filt(d["accel"], np.int32),
                "exp": filt(d["exp"], np.int32),
                "inexp": filt(d["inexp"], np.int32),
                "mfg": filt(d["mfg"], np.int32),
                "pain": filt(d["pain"], np.int32),
                "cns": filt(d["cns"], np.int32),
                "onco": filt(d["onco"], np.int32),
                "inf": filt(d["inf"], np.int32),
                "stack": filt(d["stack"], np.int32),
                "class1_cmc": filt(d["class1_cmc"], np.int32),
                "des_trap": filt(d["des_trap"], np.int32),
                "adcom_pct": filt(d["adcom_pct"], np.float32),
            }

        else:
            # Support both CSV and Excel files
            if path.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(path, sheet_name='ODIN_PDUFA_1349_GPU_READY')
            else:
                df = pd.read_csv(path)

            target_split = self._split_to_code(self.split)
            if target_split is not None:
                smap = {"train_2020_2023":0, "val_2024":1, "test_2025_2026":2}
                code = df["split_default"].map(smap).fillna(-1).astype(np.int8)
                df = df.loc[code == target_split].copy()

            if "outcome_binary" in df.columns:
                y = pd.to_numeric(df["outcome_binary"], errors="coerce").fillna(0).astype(np.int32).values
            elif "outcome" in df.columns:
                up = df["outcome"].astype(str).str.upper()
                y = up.isin(["APPROVAL","APPROVED","1","TRUE","YES"]).astype(np.int32).values
            else:
                raise ValueError("Data must contain outcome_binary or outcome")

            self.y_true = y
            self.N = int(y.shape[0])

            def get_int(col: str, default: int = 0) -> np.ndarray:
                if col not in df.columns:
                    return np.full(self.N, default, dtype=np.int32)
                return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(np.int32).values

            def get_float(col: str, default: float = 0.0) -> np.ndarray:
                if col not in df.columns:
                    return np.full(self.N, default, dtype=np.float32)
                return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(np.float32).values

            ta = df["therapeutic_area"].astype(str).str.lower() if "therapeutic_area" in df.columns else pd.Series([""]*self.N)
            pain = ta.str.contains("pain", na=False).astype(np.int32).values
            cns  = ta.str.contains("cns", na=False).astype(np.int32).values
            onco = ta.str.contains("oncol", na=False).astype(np.int32).values
            inf  = ta.str.contains("infect", na=False).astype(np.int32).values

            had_adcom = get_int("had_adcom", 0)
            adcom_pct = get_float("adcom_vote_pct", 0.0) / 100.0
            adcom_pct = np.where(had_adcom == 1, adcom_pct, 0.0).astype(np.float32)

            exp = get_int("experienced_sponsor", 0)
            exp = (exp > 0).astype(np.int32)
            inexp = (1 - exp).astype(np.int32)

            self.feat = {
                "btd": get_int("btd", 0),
                "orphan": get_int("orphan", 0),
                "priority": get_int("priority_review", 0),
                "fast": get_int("fast_track", 0),
                "accel": get_int("accelerated_approval", 0),
                "exp": exp,
                "inexp": inexp,
                "mfg": get_int("manufacturing_risk", 0),
                "pain": pain,
                "cns": cns,
                "onco": onco,
                "inf": inf,
                "stack": get_int("designation_stack_count", 0),
                "class1_cmc": get_int("class1_cmc_resubmission_flag", 0),
                "des_trap": get_int("designation_trap_flag", 0),
                "adcom_pct": adcom_pct,
            }

        # Calculate class distribution
        self.n_approved = int(self.y_true.sum())
        self.n_crl = self.N - self.n_approved
        self.base_rate = self.n_approved / self.N

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📥 Loaded N={self.N} rows for split='{self.split}' from: {os.path.basename(path)}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Distribution: {self.n_approved} approvals, {self.n_crl} CRLs ({self.base_rate*100:.1f}% approval rate)")

        # Feature validation
        print(f"\n📋 FEATURE VALIDATION:")
        for name, arr in self.feat.items():
            if name == "adcom_pct":
                n_nonzero = (arr > 0).sum()
                print(f"   {name}: {n_nonzero} non-zero ({n_nonzero/self.N*100:.1f}%)")
            elif name == "stack":
                print(f"   {name}: mean={arr.mean():.2f}, max={arr.max()}")
            else:
                n_ones = arr.sum()
                print(f"   {name}: {n_ones} ones ({n_ones/self.N*100:.1f}%)")

        # Move to GPU
        self.gpu = {
            k: cp.asarray(v, dtype=(cp.float32 if k == "adcom_pct" else cp.int32))
            for k, v in self.feat.items()
        }
        self.y_true_gpu = cp.asarray(self.y_true, dtype=cp.int32)

    def _allocate(self) -> None:
        B = self.batch_size
        self.param = {name: cp.empty(B, dtype=cp.float32) for name in self.param_names}
        self.out_brier = cp.empty(B, dtype=cp.float32)
        self.out_tp = cp.empty(B, dtype=cp.int32)
        self.out_fp = cp.empty(B, dtype=cp.int32)
        self.out_tn = cp.empty(B, dtype=cp.int32)
        self.out_fn = cp.empty(B, dtype=cp.int32)

    def _fill_uniform(self, buf: cp.ndarray, low: float, high: float) -> None:
        try:
            self.rng.uniform(low, high, size=buf.size, dtype=cp.float32, out=buf)
            return
        except TypeError:
            pass
        except Exception:
            pass

        try:
            r = self.rng.random(buf.size, dtype=cp.float32)
        except TypeError:
            r = self.rng.random(buf.size).astype(cp.float32)

        buf[:] = r
        buf *= (high - low)
        buf += low

    def _sample_params(self) -> None:
        for name, b in self.bounds.items():
            self._fill_uniform(self.param[name], b.low, b.high)

    def _launch(self) -> None:
        B = self.batch_size
        threads = 256
        blocks = (B,)

        SCORING_KERNEL(
            blocks, (threads,),
            (
                self.gpu["btd"], self.gpu["orphan"], self.gpu["priority"], self.gpu["fast"], self.gpu["accel"],
                self.gpu["exp"], self.gpu["inexp"],
                self.gpu["mfg"], self.gpu["pain"], self.gpu["cns"], self.gpu["onco"], self.gpu["inf"],
                self.gpu["stack"], self.gpu["class1_cmc"], self.gpu["des_trap"],
                self.gpu["adcom_pct"], self.y_true_gpu,

                self.param["p_base"], self.param["p_threshold"],
                self.param["w_btd"], self.param["w_orphan"], self.param["w_priority"], self.param["w_fast"], self.param["w_accel"],
                self.param["w_exp"], self.param["w_stack"],
                self.param["w_mfg_pen"], self.param["w_mfg_amp"],
                self.param["adj_pain"], self.param["adj_cns"], self.param["adj_cns_amp"], self.param["adj_onco"], self.param["adj_inf"],
                self.param["w_adcom"], self.param["i_mfg_inexp"], self.param["w_des_trap"],

                self.out_brier, self.out_tp, self.out_fp, self.out_tn, self.out_fn,
                self.N, B
            )
        )

    def _objective(self):
        # ---- Metrics (vectorized on GPU) ----
        eps = 1e-9
        tp = self.out_tp.astype(cp.float32)
        fp = self.out_fp.astype(cp.float32)
        tn = self.out_tn.astype(cp.float32)
        fn = self.out_fn.astype(cp.float32)

        precision = tp / (tp + fp + eps)
        recall = tp / (tp + fn + eps)
        specificity = tn / (tn + fp + eps)

        # F1 score = harmonic mean of precision and recall
        f1 = 2 * (precision * recall) / (precision + recall + eps)

        # Matthews correlation coefficient (more informative under imbalance)
        denom = cp.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn) + eps)
        mcc = ((tp * tn) - (fp * fn)) / denom

        # Apply BOTH constraints: precision >= min AND recall >= min
        valid = (precision >= self.precision_min) & (recall >= self.recall_min)
        if not cp.any(valid):
            return None

        idx = cp.where(valid)[0]
        b = self.out_brier[idx]
        f = f1[idx]
        s = specificity[idx]
        m = mcc[idx]
        fpc = fp[idx]

        # FP rate normalized by actual CRL count (0..1)
        fp_rate = cp.minimum(fpc / float(self.n_crl), 1.0)

        # ---- Objective formulations ----
        # (1) balanced: weighted sum (good default)
        # (2) avoid_fp: aggressively minimize FP (dominant term), then prefer calibration + MCC
        # (3) spec_at_prec: maximize specificity given the precision constraint, then calibration
        obj_mode = self.objective
        if obj_mode == "balanced":
            # 35% calibration (Brier), 25% MCC, 25% F1, 15% specificity
            obj = ((1.0 - b) * 0.35) + (m * 0.25) + (f * 0.25) + (s * 0.15)
        elif obj_mode == "avoid_fp":
            # Lexicographic-ish: FP dominates, then specificity, then calibration, then MCC
            # Big coefficients make FP reduction the primary driver.
            obj = ((1.0 - fp_rate) * 1000.0) + (s * 10.0) + ((1.0 - b) * 5.0) + (m * 1.0)
        elif obj_mode == "spec_at_prec":
            # If your goal is specifically: "maximize specificity at precision>=X"
            obj = (s * 1000.0) + ((1.0 - b) * 10.0) + (m * 1.0)
        elif obj_mode == "calibration":
            # Calibration-first (Brier dominates), with light tie-breaks
            obj = ((1.0 - b) * 1000.0) + (m * 10.0) + (s * 1.0)
        else:
            raise ValueError(f"Unknown --objective '{self.objective}'. Use: balanced | avoid_fp | spec_at_prec | calibration")
        return idx, obj

    def _harvest_topk(self) -> None:
        res = self._objective()
        if res is None:
            return
        idx, obj = res

        k = min(self.topk, int(obj.shape[0]))
        if k <= 0:
            return

        part = cp.argpartition(obj, -k)[-k:]
        top_local = part[cp.argsort(obj[part])][::-1]

        for j in top_local:
            real_idx = int(idx[int(j)])

            brier = float(self.out_brier[real_idx].get())
            tp = int(self.out_tp[real_idx].get())
            fp = int(self.out_fp[real_idx].get())
            tn = int(self.out_tn[real_idx].get())
            fn = int(self.out_fn[real_idx].get())

            precision = tp / (tp + fp + 1e-9)
            recall = tp / (tp + fn + 1e-9)
            specificity = tn / (tn + fp + 1e-9)
            f1 = 2 * (precision * recall) / (precision + recall + 1e-9)
            mcc_denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5 + 1e-9
            mcc = ((tp * tn) - (fp * fn)) / mcc_denom

            item = {
                "score": float(obj[int(j)].get()),
                "metrics": {
                    "brier": brier,
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1": float(f1),
                    "mcc": float(mcc),
                    "specificity": float(specificity),
                    "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                    "n_approved": self.n_approved,
                    "n_crl": self.n_crl,
                },
                "params": {k: float(self.param[k][real_idx].get()) for k in self.param_names},
            }
            self.top.append(item)

        self.top.sort(key=lambda x: x["score"], reverse=True)
        self.top = self.top[: self.topk]

    def run(self, iterations: int, report_every_s: float = 2.0) -> None:
        B = self.batch_size
        batches = (int(iterations) + B - 1) // B
        total = batches * B

        print(f"\n🔥 SEARCH: {total:,} iterations ({batches:,} batches) | batch={B:,}")
        print(f"   Constraints: precision >= {self.precision_min}, recall >= {self.recall_min}")
        print("   (Warmup kernel compile happens on first launch.)")

        # Warmup
        self._sample_params()
        self._launch()
        cp.cuda.Device().synchronize()

        start = time.time()
        last = start
        processed = 0

        for bi in range(batches):
            self._sample_params()
            self._launch()
            self._harvest_topk()
            processed += B

            now = time.time()
            if now - last >= report_every_s:
                elapsed = now - start
                rate_m = processed / elapsed / 1e6
                pct = 100.0 * (bi + 1) / batches
                if self.top:
                    best_f1 = self.top[0]["metrics"]["f1"]
                    best_str = f"F1={best_f1:.4f}"
                else:
                    best_str = "—"
                print(f"\r   [{pct:5.1f}%] {processed/1e9:.2f}B | {rate_m:6.1f} M it/s | best {best_str}", end="", flush=True)
                last = now

        cp.cuda.Device().synchronize()
        total_time = time.time() - start
        final_rate = total / total_time / 1e6
        print(f"\n\n✅ COMPLETE | {total/1e9:.2f}B iters | {total_time:.1f}s | {final_rate:.1f} M it/s")

    def save(self, out_json: str) -> None:
        print("\n🏆 TOP CONFIGS:")
        print("-" * 100)
        print(f"{'#':>3} {'score':>8} {'brier':>8} {'prec':>6} {'recall':>6} {'F1':>6} {'MCC':>6} {'spec':>6} {'FP':>4} {'FN':>4} {'thr':>6}")
        print("-" * 100)
        for i, r in enumerate(self.top, 1):
            m = r["metrics"]
            print(
                f"{i:>3} {r['score']:>8.5f} {m['brier']:>8.5f} {m['precision']:>6.3f} {m['recall']:>6.3f} "
                f"{m['f1']:>6.3f} {m['mcc']:>6.3f} {m['specificity']:>6.3f} {m['fp']:>4} {m['fn']:>4} {r['params']['p_threshold']:>6.3f}"
            )
        print("-" * 100)

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(self.top, f, indent=2)
        print(f"💾 Saved: {out_json}")

    def narrow_bounds_around_best(self, frac: float = 0.10, min_span: float = 0.005) -> None:
        if not self.top:
            return
        best = self.top[0]["params"]
        new_bounds = {}
        for k, b in self.bounds.items():
            v = float(best[k])
            span = max(abs(v) * frac, min_span)
            new_bounds[k] = Bounds(v - span, v + span)
        self.bounds = new_bounds
        print(f"🎯 Narrowed bounds around best (±{frac*100:.0f}% or ≥{min_span}).")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=str, default="ODIN_PDUFA_1349_GPU_READY_T1_FIXED.csv",
                   help="Path to .csv, .xlsx, or .npz dataset.")
    p.add_argument("--split", type=str, default="train", help="train | val | test | all")
    p.add_argument("--device", type=int, default=0, help="CUDA device id (default 0).")
    p.add_argument("--seed", type=int, default=7, help="RNG seed.")
    p.add_argument("--batch", type=int, default=2_500_000, help="Configs per GPU batch.")
    p.add_argument("--iters", type=int, default=1_000_000_000, help="Total iterations for Phase 1.")
    p.add_argument("--iters2", type=int, default=500_000_000, help="Total iterations for Phase 2 (refinement).")
    p.add_argument("--precision_min", type=float, default=0.90, help="Constraint: minimum precision (default 0.90).")
    p.add_argument("--recall_min", type=float, default=0.85, help="Constraint: minimum recall (default 0.85).")
    p.add_argument(
        "--objective",
        type=str,
        default="balanced",
        help="Objective: balanced | avoid_fp | spec_at_prec | calibration",
    )
    p.add_argument("--topk", type=int, default=10, help="Keep top K configs.")
    p.add_argument("--out", type=str, default="ODIN_TOP_CONFIGS_V6_T1_FIXED.json", help="Output JSON path.")
    p.add_argument("--no_phase2", action="store_true", help="Skip Phase 2 refinement.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    engine = ODINRTXV6Engine(
        data_path=args.data,
        batch_size=args.batch,
        seed=args.seed,
        device_id=args.device,
        split=args.split,
        precision_min=args.precision_min,
        recall_min=args.recall_min,
        topk=args.topk,
        objective=args.objective,
    )

    print("\n" + "="*72)
    print("⚔️  PHASE 1: GLOBAL SEARCH")
    print("="*72)
    engine.run(args.iters)

    if not engine.top:
        print("❌ No configs met constraints. Try lowering --precision_min or --recall_min.")
        sys.exit(2)

    if args.no_phase2:
        engine.save(args.out)
        return

    print("\n" + "="*72)
    print("🎯 PHASE 2: LOCAL REFINEMENT")
    print("="*72)
    engine.narrow_bounds_around_best(frac=0.10, min_span=0.005)
    engine.run(args.iters2)

    engine.save(args.out)


if __name__ == "__main__":
    main()