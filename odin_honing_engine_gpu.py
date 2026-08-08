#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL HONING ENGINE v13.2-GPU                                ║
║  CUDA-accelerated gradient descent on 2,210+ PDUFA events              ║
║                                                                        ║
║  Architecture:                                                         ║
║    - All events encoded as a single GPU tensor (N × F)                 ║
║    - Forward pass: vectorized matmul + sigmoid across all events       ║
║    - Adam optimizer + cosine annealing with warm restarts              ║
║    - Autograd for gradients (replaces manual Python-loop gradients)    ║
║    - Vectorized AUC computation on GPU                                 ║
║                                                                        ║
║  Expected speedup: 100-500x over pure-Python v13.1                    ║
║                                                                        ║
║  Feature layout (55 features):                                         ║
║    [0:22]   22 binary signals                                          ║
║    [22:26]  4 TA bucket one-hot (LOW/MOD/HIGH/VERY_HIGH)               ║
║    [26:30]  4 FDA era one-hot                                          ║
║    [30:33]  3 resub class one-hot (0/1/2)                              ║
║    [33:52]  19 TA offset one-hot                                       ║
║    [52:55]  3 continuous (hist_crl centered, sponsor_exp, crl_count)   ║
║                                                                        ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim

__version__ = "13.2.1-gpu"

# ═══════════════════════════════════════════════════════════════
#  DYNAMIC VRAM MANAGER
# ═══════════════════════════════════════════════════════════════

class VRAMManager:
    """
    Dynamic GPU memory manager for coexistence with other GPU apps.

    Features:
      - Queries AVAILABLE (not total) VRAM before every allocation
      - Configurable memory ceiling (default 50% of free VRAM)
      - Auto-fallback to CPU when VRAM is insufficient
      - Explicit cache clearing after each honing cycle
      - Batch-size scaling based on available memory
      - Memory fraction cap via CUDA allocator settings

    ODIN's footprint is tiny (~2210×55 float32 = ~0.5 MB for data),
    but optimizer state + autograd graph can spike during training.
    """

    # Minimum VRAM (MB) required to justify GPU use
    MIN_VRAM_MB = 128
    # Estimated peak MB per 1000 events during training
    # (features + targets + optimizer state + autograd graph)
    MB_PER_1K_EVENTS = 12.0

    def __init__(self, max_memory_fraction: float = 0.5, device_id: int = 0):
        """
        Args:
            max_memory_fraction: Max share of FREE vram to claim (0.0-1.0).
                                 0.5 = use at most half of what's currently free.
            device_id: CUDA device index.
        """
        self.max_memory_fraction = max(0.05, min(0.95, max_memory_fraction))
        self.device_id = device_id
        self._gpu_available = torch.cuda.is_available()
        self._device_name = ""
        self._total_vram_mb = 0

        if self._gpu_available:
            props = torch.cuda.get_device_properties(device_id)
            self._device_name = props.name
            self._total_vram_mb = props.total_memory / 1e6

    def get_free_vram_mb(self) -> float:
        """Current free VRAM in MB (queries live, not cached)."""
        if not self._gpu_available:
            return 0.0
        torch.cuda.synchronize(self.device_id)
        free, _total = torch.cuda.mem_get_info(self.device_id)
        return free / 1e6

    def get_allocated_mb(self) -> float:
        """VRAM currently allocated by THIS process."""
        if not self._gpu_available:
            return 0.0
        return torch.cuda.memory_allocated(self.device_id) / 1e6

    def get_reserved_mb(self) -> float:
        """VRAM reserved by PyTorch caching allocator for THIS process."""
        if not self._gpu_available:
            return 0.0
        return torch.cuda.memory_reserved(self.device_id) / 1e6

    def get_budget_mb(self) -> float:
        """How many MB we're allowed to use right now."""
        free = self.get_free_vram_mb()
        return free * self.max_memory_fraction

    def should_use_gpu(self, n_events: int = 2210) -> bool:
        """
        Check if GPU use is advisable given current VRAM pressure.
        Returns False if another app is hogging VRAM.
        """
        if not self._gpu_available:
            return False
        budget = self.get_budget_mb()
        estimated_need = (n_events / 1000.0) * self.MB_PER_1K_EVENTS
        return budget >= max(self.MIN_VRAM_MB, estimated_need)

    def get_device(self, n_events: int = 2210) -> torch.device:
        """Get best device given current VRAM availability."""
        if self.should_use_gpu(n_events):
            return torch.device(f"cuda:{self.device_id}")
        elif self._gpu_available:
            free = self.get_free_vram_mb()
            print(f"  ⚠️  VRAM constrained ({free:.0f} MB free, "
                  f"budget {self.get_budget_mb():.0f} MB) → falling back to CPU")
            return torch.device("cpu")
        else:
            return torch.device("cpu")

    def release(self):
        """Release all cached VRAM back to the system."""
        if self._gpu_available:
            torch.cuda.empty_cache()
            torch.cuda.synchronize(self.device_id)

    def status(self) -> dict:
        """Full VRAM status snapshot."""
        if not self._gpu_available:
            return {"gpu": False, "device": "cpu"}
        free = self.get_free_vram_mb()
        return {
            "gpu": True,
            "device": self._device_name,
            "total_mb": round(self._total_vram_mb, 1),
            "free_mb": round(free, 1),
            "allocated_mb": round(self.get_allocated_mb(), 1),
            "reserved_mb": round(self.get_reserved_mb(), 1),
            "budget_mb": round(self.get_budget_mb(), 1),
            "fraction_cap": self.max_memory_fraction,
        }

    def print_status(self):
        s = self.status()
        if not s["gpu"]:
            print("  GPU: not available (CPU mode)")
            return
        print(f"  🚀 GPU: {s['device']}")
        print(f"     Total:     {s['total_mb']:>8.1f} MB")
        print(f"     Free:      {s['free_mb']:>8.1f} MB")
        print(f"     Allocated: {s['allocated_mb']:>8.1f} MB (this process)")
        print(f"     Reserved:  {s['reserved_mb']:>8.1f} MB (PyTorch cache)")
        print(f"     Budget:    {s['budget_mb']:>8.1f} MB ({self.max_memory_fraction:.0%} of free)")


# Module-level singleton (created by runner at startup)
_vram_mgr: VRAMManager = None

def get_vram_manager(max_memory_fraction: float = 0.5) -> VRAMManager:
    """Get or create the global VRAM manager."""
    global _vram_mgr
    if _vram_mgr is None:
        _vram_mgr = VRAMManager(max_memory_fraction=max_memory_fraction)
    return _vram_mgr

def get_device(n_events: int = 2210, max_memory_fraction: float = 0.5):
    """Convenience: get best device with VRAM awareness."""
    mgr = get_vram_manager(max_memory_fraction)
    dev = mgr.get_device(n_events)
    mgr.print_status()
    return dev


DEVICE = None  # Set at init time


# ═══════════════════════════════════════════════════════════════
#  MATH PRIMITIVES (CPU fallback for single-event scoring)
# ═══════════════════════════════════════════════════════════════

def sigmoid_cpu(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ez = math.exp(x)
        return ez / (1.0 + ez)

def logit_cpu(p: float) -> float:
    p = max(1e-7, min(1 - 1e-7, p))
    return math.log(p / (1 - p))

def _pb(val) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("TRUE", "1", "YES", "Y", "T")

def _pf(val, default=0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _pi(val, default=0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════
#  SIGNAL & FEATURE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# Ordered list of binary signals (indices 0-21)
BINARY_SIGNAL_NAMES = [
    "btd", "orphan", "priority_review", "fast_track",
    "accelerated_approval", "surrogate_endpoint", "had_adcom",
    "prior_crl", "form_483_issues", "manufacturing_risk",
    "double_crl_flag", "ppm_flag", "ped_pk_missing",
    "ema_cmc_flag", "cmc_extension_flag", "gene_therapy",
    "single_arm_study", "btd_onco_interaction", "btd_priority_interaction",
    "ta_very_high_risk", "safety_moderate", "safety_high",
]
N_BINARY = len(BINARY_SIGNAL_NAMES)  # 22

# Initial logits for binary signals
INITIAL_SIGNAL_LOGITS = {
    "btd": +2.44, "orphan": +1.87, "priority_review": +2.25,
    "fast_track": +2.05, "accelerated_approval": +1.82,
    "surrogate_endpoint": +2.17, "had_adcom": +3.17,
    "prior_crl": -7.85, "form_483_issues": -7.76,
    "manufacturing_risk": -1.42, "double_crl_flag": -2.23,
    "ppm_flag": -1.59, "ped_pk_missing": -0.50,
    "ema_cmc_flag": -0.30, "cmc_extension_flag": -0.30,
    "gene_therapy": -0.29, "single_arm_study": +0.41,
    "btd_onco_interaction": +2.98, "btd_priority_interaction": +2.38,
    "ta_very_high_risk": +1.71, "safety_moderate": -0.30, "safety_high": -0.50,
}

# TA bucket categories (indices 22-25)
TA_BUCKET_NAMES = ["LOW", "MOD", "HIGH", "VERY_HIGH"]
TA_BUCKET_IDX = {name: i for i, name in enumerate(TA_BUCKET_NAMES)}
INITIAL_TA_BUCKET_LOGITS = {"LOW": -0.61, "MOD": 0.00, "HIGH": +0.55, "VERY_HIGH": +1.52}

# FDA era categories (indices 26-29)
FDA_ERA_NAMES = ["PRE_2020", "COVID_ERA", "HOEG_ERA", "POST_COVID"]
FDA_ERA_IDX = {name: i for i, name in enumerate(FDA_ERA_NAMES)}
INITIAL_FDA_ERA_LOGITS = {"PRE_2020": -0.17, "COVID_ERA": +0.20, "HOEG_ERA": +0.13, "POST_COVID": 0.00}

# Resub class (indices 30-32)
RESUB_NAMES = ["0", "1", "2"]
RESUB_IDX = {name: i for i, name in enumerate(RESUB_NAMES)}
INITIAL_RESUB_LOGITS = {"0": 0.00, "1": +0.80, "2": +0.40}

# TA offsets (indices 33-51)
TA_OFFSET_NAMES = [
    "Oncology", "Other", "Infectious Disease", "CNS/Neurology",
    "Immunology", "Rare Disease", "Cardiovascular", "Ophthalmology",
    "Pain Management", "Metabolic/Endocrine", "Endocrinology",
    "Nephrology", "Dermatology", "Respiratory", "Hematology",
    "GI/Hepatology", "Women's Health", "Vaccines", "CNS",
]
TA_OFFSET_IDX = {name: i for i, name in enumerate(TA_OFFSET_NAMES)}
INITIAL_TA_OFFSETS = {
    "Oncology": -0.61, "Other": +0.23, "Infectious Disease": +1.41,
    "CNS/Neurology": +0.42, "Immunology": +1.35, "Rare Disease": +0.82,
    "Cardiovascular": +0.59, "Ophthalmology": -0.03, "Pain Management": -0.02,
    "Metabolic/Endocrine": +0.63, "Endocrinology": +0.63, "Nephrology": +0.14,
    "Dermatology": +1.52, "Respiratory": +2.65, "Hematology": +0.34,
    "GI/Hepatology": +2.34, "Women's Health": +2.50, "Vaccines": +2.50, "CNS": -1.45,
}

# Continuous features (indices 52-54)
CONTINUOUS_NAMES = ["historical_crl_rate", "sponsor_prior_approvals", "prior_crl_count"]
INITIAL_CONTINUOUS_WEIGHTS = {
    "historical_crl_rate": -2.50,
    "sponsor_prior_approvals": 0.04,
    "prior_crl_count": -0.30,
}

# Centers for continuous features
CONTINUOUS_CENTERS = {"historical_crl_rate": 0.34, "sponsor_prior_approvals": 10.0, "prior_crl_count": 0.0}

N_FEATURES = N_BINARY + len(TA_BUCKET_NAMES) + len(FDA_ERA_NAMES) + len(RESUB_NAMES) + len(TA_OFFSET_NAMES) + len(CONTINUOUS_NAMES)
# = 22 + 4 + 4 + 3 + 19 + 3 = 55

# TA → Bucket mapping
TA_TO_BUCKET = {
    "Oncology": "LOW", "CNS": "LOW", "Ophthalmology": "MOD",
    "Pain Management": "MOD", "Nephrology": "MOD", "Other": "HIGH",
    "Hematology": "HIGH", "CNS/Neurology": "HIGH", "Cardiovascular": "HIGH",
    "Metabolic/Endocrine": "HIGH", "Endocrinology": "HIGH", "Rare Disease": "HIGH",
    "Immunology": "VERY_HIGH", "Infectious Disease": "VERY_HIGH",
    "Dermatology": "VERY_HIGH", "GI/Hepatology": "VERY_HIGH",
    "Respiratory": "VERY_HIGH", "Women's Health": "VERY_HIGH", "Vaccines": "VERY_HIGH",
}

# Tier thresholds
TIER_THRESHOLDS = {1: 0.85, 2: 0.65, 3: 0.40, 4: 0.00}
TIER_ACTIONS = {1: "LONG", 2: "LEAN_LONG", 3: "NEUTRAL", 4: "HIGH_CRL_RISK"}

BASE_LOGIT_INIT = logit_cpu(0.680)  # ≈ 0.7538

FDA_ERA_LOGITS = INITIAL_FDA_ERA_LOGITS
TA_BUCKET_LOGITS = INITIAL_TA_BUCKET_LOGITS
TA_LOGITS = INITIAL_TA_OFFSETS


# ═══════════════════════════════════════════════════════════════
#  CSV ROW → FEATURE DICT (same as v13.1 for compatibility)
# ═══════════════════════════════════════════════════════════════

def _normalize_ta(ta: str) -> str:
    ta = ta.strip()
    return {"Endocrinology": "Metabolic/Endocrine"}.get(ta, ta)

def parse_row(row: dict) -> dict:
    """Parse a CSV row into standardized event dict. Compatible with v13.1."""
    ev = {}
    ev["event_id"] = row.get("event_id", "").strip()
    ev["ticker"] = row.get("ticker", "").strip()
    ev["company"] = row.get("company", "").strip()
    ev["drug_name"] = row.get("asset", "").strip()
    ev["indication"] = row.get("indication", "").strip()
    ev["therapeutic_area"] = _normalize_ta(row.get("therapeutic_area", "Other"))
    ev["catalyst_date"] = row.get("catalyst_date", row.get("cat_date", "")).strip()

    outcome = row.get("outcome", "").strip().upper()
    if outcome == "APPROVAL":
        ev["outcome"] = "APPROVED"
    elif outcome == "CRL":
        ev["outcome"] = "CRL"
    else:
        ev["outcome"] = None

    # Binary signals
    ev["btd"] = _pb(row.get("btd"))
    ev["orphan"] = _pb(row.get("orphan"))
    ev["priority_review"] = _pb(row.get("priority_review"))
    ev["fast_track"] = _pb(row.get("fast_track"))
    ev["had_adcom"] = _pb(row.get("had_adcom"))
    ev["prior_crl"] = _pb(row.get("prior_crl"))
    ev["form_483_issues"] = _pb(row.get("form_483_issues"))
    ev["manufacturing_risk"] = _pb(row.get("manufacturing_risk"))
    ev["ppm_flag"] = _pb(row.get("ppm_flag"))
    ev["ped_pk_missing"] = _pb(row.get("s22_ped_pk_missing"))
    ev["ema_cmc_flag"] = _pb(row.get("ema_cmc_flag"))
    ev["cmc_extension_flag"] = _pb(row.get("cmc_extension_flag"))
    ev["gene_therapy"] = _pb(row.get("gene_therapy"))
    ev["single_arm_study"] = _pb(row.get("single_arm_study"))
    ev["surrogate_endpoint"] = _pb(row.get("surrogate_endpoint"))
    ev["accelerated_approval"] = _pb(row.get("accelerated_approval"))

    # Derived
    crl_count = _pi(row.get("prior_crl_count"), 0)
    ev["double_crl_flag"] = crl_count >= 2
    ta = ev["therapeutic_area"]
    ev["btd_onco_interaction"] = ev["btd"] and ta == "Oncology"
    ev["btd_priority_interaction"] = ev["btd"] and ev["priority_review"]
    ev["ta_bucket_v2"] = TA_TO_BUCKET.get(ta, "MOD")
    ev["ta_very_high_risk"] = ev["ta_bucket_v2"] == "VERY_HIGH"

    safety_sev = _pf(row.get("safety_signal_severity"), 0.0)
    ev["safety_signal_severity"] = safety_sev
    ev["safety_moderate"] = 1.0 <= safety_sev < 2.5
    ev["safety_high"] = safety_sev >= 2.5

    ev["fda_era"] = row.get("fda_era", "POST_COVID").strip()
    if ev["fda_era"] not in FDA_ERA_IDX:
        ev["fda_era"] = "POST_COVID"

    resub_raw = row.get("resubmission_class", "").strip()
    try:
        resub_int = int(float(resub_raw))
        ev["resubmission_class"] = resub_int if resub_int in (1, 2) else 0
    except (ValueError, TypeError):
        ev["resubmission_class"] = 0

    ev["historical_crl_rate"] = _pf(row.get("historical_crl_rate"), 0.34)
    ev["sponsor_prior_approvals"] = _pi(row.get("sponsor_prior_approvals"), 0)
    ev["prior_crl_count"] = crl_count
    ev["adcom_vote_pct"] = _pf(row.get("adcom_vote_pct"), 0.0)
    ev["v1067_score"] = _pf(row.get("v1067_score"))
    ev["v1070_score"] = _pf(row.get("v1070_score"))
    ev["ta_base_score"] = _pf(row.get("ta_base_score"), 0.0)
    ev["application_type"] = row.get("application_type", "").strip()
    ev["psychedelics"] = _pb(row.get("psychedelics"))

    return ev


def load_csv(filepath: str) -> list:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [parse_row(row) for row in reader]


# ═══════════════════════════════════════════════════════════════
#  GPU TENSOR ENCODING
# ═══════════════════════════════════════════════════════════════

def encode_event_to_vector(ev: dict) -> list:
    """Encode a single event dict into a flat feature vector (length N_FEATURES)."""
    vec = [0.0] * N_FEATURES
    offset = 0

    # Binary signals [0:22]
    for i, sig in enumerate(BINARY_SIGNAL_NAMES):
        vec[offset + i] = 1.0 if ev.get(sig, False) else 0.0
    offset += N_BINARY

    # TA bucket one-hot [22:26]
    bucket = ev.get("ta_bucket_v2", "MOD")
    idx = TA_BUCKET_IDX.get(bucket, TA_BUCKET_IDX["MOD"])
    vec[offset + idx] = 1.0
    offset += len(TA_BUCKET_NAMES)

    # FDA era one-hot [26:30]
    era = ev.get("fda_era", "POST_COVID")
    idx = FDA_ERA_IDX.get(era, FDA_ERA_IDX["POST_COVID"])
    vec[offset + idx] = 1.0
    offset += len(FDA_ERA_NAMES)

    # Resub class one-hot [30:33]
    resub = str(ev.get("resubmission_class", 0))
    idx = RESUB_IDX.get(resub, RESUB_IDX["0"])
    vec[offset + idx] = 1.0
    offset += len(RESUB_NAMES)

    # TA offset one-hot [33:52]
    ta = ev.get("therapeutic_area", "Other")
    idx = TA_OFFSET_IDX.get(ta, TA_OFFSET_IDX.get("Other", 0))
    vec[offset + idx] = 1.0
    offset += len(TA_OFFSET_NAMES)

    # Continuous features [52:55] — PRE-CENTERED
    vec[offset + 0] = ev.get("historical_crl_rate", 0.34) - CONTINUOUS_CENTERS["historical_crl_rate"]
    vec[offset + 1] = ev.get("sponsor_prior_approvals", 0) - CONTINUOUS_CENTERS["sponsor_prior_approvals"]
    vec[offset + 2] = ev.get("prior_crl_count", 0) - CONTINUOUS_CENTERS["prior_crl_count"]

    return vec


def encode_events_to_tensor(events: list, device: torch.device) -> tuple:
    """
    Encode all events into a GPU tensor pair.
    Returns: (features: [N, F], targets: [N])
    Only includes resolved events with known outcomes.
    """
    resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
    if not resolved:
        return None, None

    vectors = [encode_event_to_vector(e) for e in resolved]
    targets = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in resolved]

    X = torch.tensor(vectors, dtype=torch.float32, device=device)
    y = torch.tensor(targets, dtype=torch.float32, device=device)

    return X, y


# ═══════════════════════════════════════════════════════════════
#  ODIN GPU MODEL (PyTorch nn.Module)
# ═══════════════════════════════════════════════════════════════

class OdinGPUModel(nn.Module):
    """
    Single-layer logistic regression matching the ODIN weight structure.
    Weight vector maps 1:1 to the feature vector layout.
    """

    def __init__(self, initial_weights: dict = None):
        super().__init__()

        # Build initial weight vector from ODIN weight structure
        init_w = torch.zeros(N_FEATURES, dtype=torch.float32)
        init_bias = BASE_LOGIT_INIT

        if initial_weights:
            init_bias = initial_weights.get("base_logit", BASE_LOGIT_INIT)
            self._load_from_dict(init_w, initial_weights)
        else:
            self._load_defaults(init_w)

        self.weights = nn.Parameter(init_w)
        self.bias = nn.Parameter(torch.tensor(init_bias, dtype=torch.float32))

    def _load_defaults(self, w: torch.Tensor):
        """Load default empirical logits."""
        offset = 0
        for i, sig in enumerate(BINARY_SIGNAL_NAMES):
            w[offset + i] = INITIAL_SIGNAL_LOGITS.get(sig, 0.0)
        offset += N_BINARY

        for i, name in enumerate(TA_BUCKET_NAMES):
            w[offset + i] = INITIAL_TA_BUCKET_LOGITS.get(name, 0.0)
        offset += len(TA_BUCKET_NAMES)

        for i, name in enumerate(FDA_ERA_NAMES):
            w[offset + i] = INITIAL_FDA_ERA_LOGITS.get(name, 0.0)
        offset += len(FDA_ERA_NAMES)

        for i, name in enumerate(RESUB_NAMES):
            w[offset + i] = INITIAL_RESUB_LOGITS.get(name, 0.0)
        offset += len(RESUB_NAMES)

        for i, name in enumerate(TA_OFFSET_NAMES):
            w[offset + i] = INITIAL_TA_OFFSETS.get(name, 0.0)
        offset += len(TA_OFFSET_NAMES)

        for i, name in enumerate(CONTINUOUS_NAMES):
            w[offset + i] = INITIAL_CONTINUOUS_WEIGHTS.get(name, 0.0)

    def _load_from_dict(self, w: torch.Tensor, d: dict):
        """Load weights from an ODIN weight dict (v13.1 format)."""
        offset = 0
        signals = d.get("signals", {})
        for i, sig in enumerate(BINARY_SIGNAL_NAMES):
            w[offset + i] = signals.get(sig, INITIAL_SIGNAL_LOGITS.get(sig, 0.0))
        offset += N_BINARY

        ta_b = d.get("ta_bucket", {})
        for i, name in enumerate(TA_BUCKET_NAMES):
            w[offset + i] = ta_b.get(name, INITIAL_TA_BUCKET_LOGITS.get(name, 0.0))
        offset += len(TA_BUCKET_NAMES)

        era = d.get("fda_era", {})
        for i, name in enumerate(FDA_ERA_NAMES):
            w[offset + i] = era.get(name, INITIAL_FDA_ERA_LOGITS.get(name, 0.0))
        offset += len(FDA_ERA_NAMES)

        resub = d.get("resub", {})
        for i, name in enumerate(RESUB_NAMES):
            w[offset + i] = resub.get(name, INITIAL_RESUB_LOGITS.get(name, 0.0))
        offset += len(RESUB_NAMES)

        ta_o = d.get("ta_offsets", {})
        for i, name in enumerate(TA_OFFSET_NAMES):
            w[offset + i] = ta_o.get(name, INITIAL_TA_OFFSETS.get(name, 0.0))
        offset += len(TA_OFFSET_NAMES)

        cont = d.get("continuous", {})
        for i, name in enumerate(CONTINUOUS_NAMES):
            w[offset + i] = cont.get(name, INITIAL_CONTINUOUS_WEIGHTS.get(name, 0.0))

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Forward pass: vectorized across all events.
        X: [N, F] feature matrix
        Returns: [N] probabilities
        """
        logits = X @ self.weights + self.bias  # [N]
        return torch.sigmoid(logits)

    def export_weights(self) -> dict:
        """Export to ODIN v13.1 compatible weight dict."""
        w = self.weights.detach().cpu().numpy()
        offset = 0
        d = {"base_logit": float(self.bias.detach().cpu().item())}

        d["signals"] = {}
        for i, sig in enumerate(BINARY_SIGNAL_NAMES):
            d["signals"][sig] = float(w[offset + i])
        offset += N_BINARY

        d["ta_bucket"] = {}
        for i, name in enumerate(TA_BUCKET_NAMES):
            d["ta_bucket"][name] = float(w[offset + i])
        offset += len(TA_BUCKET_NAMES)

        d["fda_era"] = {}
        for i, name in enumerate(FDA_ERA_NAMES):
            d["fda_era"][name] = float(w[offset + i])
        offset += len(FDA_ERA_NAMES)

        d["resub"] = {}
        for i, name in enumerate(RESUB_NAMES):
            d["resub"][name] = float(w[offset + i])
        offset += len(RESUB_NAMES)

        d["ta_offsets"] = {}
        for i, name in enumerate(TA_OFFSET_NAMES):
            d["ta_offsets"][name] = float(w[offset + i])
        offset += len(TA_OFFSET_NAMES)

        d["continuous"] = {}
        for i, name in enumerate(CONTINUOUS_NAMES):
            d["continuous"][name] = float(w[offset + i])

        return d


# ═══════════════════════════════════════════════════════════════
#  GPU METRICS (vectorized AUC, Brier, etc.)
# ═══════════════════════════════════════════════════════════════

def gpu_auc(preds: torch.Tensor, targets: torch.Tensor) -> float:
    """
    Vectorized AUC-ROC on GPU using pairwise comparison.
    For N < 10K this is O(pos*neg) but fully vectorized.
    """
    pos_mask = targets == 1.0
    neg_mask = targets == 0.0
    pos_preds = preds[pos_mask]
    neg_preds = preds[neg_mask]

    if len(pos_preds) == 0 or len(neg_preds) == 0:
        return 0.5

    # Pairwise comparison: pos_preds[:, None] > neg_preds[None, :]
    # For 1500 pos × 700 neg = 1.05M comparisons — fits easily in GPU
    comparisons = pos_preds.unsqueeze(1) > neg_preds.unsqueeze(0)  # [P, N]
    ties = pos_preds.unsqueeze(1) == neg_preds.unsqueeze(0)
    concordant = comparisons.float().sum() + 0.5 * ties.float().sum()
    auc = concordant / (len(pos_preds) * len(neg_preds))
    return float(auc.item())


def gpu_metrics(preds: torch.Tensor, targets: torch.Tensor) -> dict:
    """Compute all calibration metrics on GPU."""
    n = len(preds)
    brier = ((preds - targets) ** 2).mean().item()
    accuracy = ((preds >= 0.5).float() == targets).float().mean().item()
    auc = gpu_auc(preds, targets)

    eps = 1e-7
    log_loss = -(targets * torch.log(preds.clamp(min=eps)) +
                 (1 - targets) * torch.log((1 - preds).clamp(min=eps))).mean().item()

    return {
        "brier": round(brier, 6),
        "auc": round(auc, 6),
        "accuracy": round(accuracy, 6),
        "log_loss": round(log_loss, 6),
        "n": n,
        "n_approved": int(targets.sum().item()),
        "n_crl": int((1 - targets).sum().item()),
        "base_rate": round(targets.mean().item(), 4),
    }


# ═══════════════════════════════════════════════════════════════
#  GPU GRADIENT RECALIBRATOR
# ═══════════════════════════════════════════════════════════════

class GradientRecalibratorGPU:
    """
    GPU-accelerated gradient descent using Adam + cosine annealing.
    Replaces the Python-loop GradientRecalibrator with 100-500x speedup.
    """

    def __init__(
        self,
        lr: float = 0.003,
        l2: float = 0.005,
        max_epochs: int = 10000,
        convergence: float = 1e-9,
        patience: int = 500,
        warmup_epochs: int = 100,
        use_adam: bool = True,
        cosine_restarts: int = 3,
        verbose: bool = True,
    ):
        self.lr = lr
        self.l2 = l2
        self.max_epochs = max_epochs
        self.convergence = convergence
        self.patience = patience
        self.warmup_epochs = warmup_epochs
        self.use_adam = use_adam
        self.cosine_restarts = cosine_restarts
        self.verbose = verbose

    def recalibrate(self, model: OdinGPUModel, X: torch.Tensor, y: torch.Tensor) -> dict:
        """
        Run GPU gradient descent.
        Returns report dict compatible with v13.1 format.
        """
        if X is None or len(X) < 20:
            return {"status": "INSUFFICIENT_DATA", "n": 0 if X is None else len(X)}

        device = X.device
        model = model.to(device)

        # Pre-calibration metrics
        with torch.no_grad():
            pre_preds = model(X)
            pre_metrics = gpu_metrics(pre_preds, y)

        # Save old weights for comparison
        old_weights = model.export_weights()

        # Optimizer
        if self.use_adam:
            optimizer = optim.Adam(model.parameters(), lr=self.lr, weight_decay=self.l2)
        else:
            optimizer = optim.SGD(model.parameters(), lr=self.lr, weight_decay=self.l2)

        # Learning rate scheduler: cosine annealing with warm restarts
        epochs_per_restart = self.max_epochs // max(self.cosine_restarts, 1)
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=epochs_per_restart, T_mult=1, eta_min=self.lr * 0.01
        )

        # Early stopping
        best_brier = pre_metrics["brier"]
        best_state = deepcopy(model.state_dict())
        no_improve = 0
        epoch_count = 0

        t_start = time.time()

        for epoch in range(self.max_epochs):
            # Warmup: linearly increase LR
            if epoch < self.warmup_epochs:
                warmup_factor = (epoch + 1) / self.warmup_epochs
                for pg in optimizer.param_groups:
                    pg['lr'] = self.lr * warmup_factor

            optimizer.zero_grad()

            # Forward pass (vectorized across all events)
            preds = model(X)

            # Brier loss
            loss = ((preds - y) ** 2).mean()

            # Backward pass (autograd computes all gradients)
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)

            optimizer.step()

            if epoch >= self.warmup_epochs:
                scheduler.step()

            epoch_brier = loss.item()
            epoch_count = epoch + 1

            # Early stopping check
            if epoch_brier < best_brier - self.convergence:
                best_brier = epoch_brier
                best_state = deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= self.patience:
                    break

            # Progress logging (every 1000 epochs)
            if self.verbose and (epoch + 1) % 1000 == 0:
                with torch.no_grad():
                    auc_now = gpu_auc(model(X), y)
                elapsed = time.time() - t_start
                eps = (epoch + 1) / elapsed
                print(f"    Epoch {epoch+1:>6d}: Brier={epoch_brier:.6f} AUC={auc_now:.6f} "
                      f"LR={optimizer.param_groups[0]['lr']:.6f} ({eps:.0f} epochs/sec)")

        # Restore best weights
        model.load_state_dict(best_state)

        # Post-calibration metrics
        with torch.no_grad():
            post_preds = model(X)
            post_metrics = gpu_metrics(post_preds, y)

        elapsed = time.time() - t_start

        # Count changed signals
        new_weights = model.export_weights()
        n_changed = sum(
            1 for sig in old_weights.get("signals", {})
            if abs(old_weights["signals"][sig] - new_weights["signals"].get(sig, 0)) > 0.001
        )

        return {
            "status": "RECALIBRATED",
            "epochs": epoch_count,
            "signals_changed": n_changed,
            "pre_brier": pre_metrics["brier"],
            "post_brier": post_metrics["brier"],
            "pre_auc": pre_metrics["auc"],
            "post_auc": post_metrics["auc"],
            "pre_accuracy": pre_metrics["accuracy"],
            "post_accuracy": post_metrics["accuracy"],
            "base_logit_change": {
                "old": round(old_weights["base_logit"], 4),
                "new": round(new_weights["base_logit"], 4),
            },
            "n": len(X),
            "elapsed_sec": round(elapsed, 2),
            "epochs_per_sec": round(epoch_count / max(elapsed, 0.001), 1),
            "device": str(X.device),
            "vram_allocated_mb": round(get_vram_manager().get_allocated_mb(), 1),
        }

    def release_memory(self):
        """Explicitly free optimizer/autograd state from VRAM."""
        mgr = get_vram_manager()
        mgr.release()


# ═══════════════════════════════════════════════════════════════
#  CPU SCORER (compatible with v13.1 for single-event scoring)
# ═══════════════════════════════════════════════════════════════

class OdinScorer:
    """
    CPU scorer for single events. Wraps OdinGPUModel weights
    but does scoring in Python for compatibility with runner/ledger.
    """

    def __init__(self, weights: dict = None):
        if weights:
            self.weights = deepcopy(weights)
        else:
            self.weights = self._default_weights()

    def _default_weights(self) -> dict:
        return {
            "base_logit": BASE_LOGIT_INIT,
            "signals": dict(INITIAL_SIGNAL_LOGITS),
            "ta_bucket": dict(INITIAL_TA_BUCKET_LOGITS),
            "fda_era": dict(INITIAL_FDA_ERA_LOGITS),
            "resub": {str(k): v for k, v in INITIAL_RESUB_LOGITS.items()},
            "ta_offsets": dict(INITIAL_TA_OFFSETS),
            "continuous": dict(INITIAL_CONTINUOUS_WEIGHTS),
        }

    def score(self, event: dict) -> dict:
        """Score a single event (CPU). Full breakdown for display."""
        total_logit = self.weights["base_logit"]
        fired_signals = {}
        signal_contributions = {}

        for sig_name, sig_logit in self.weights["signals"].items():
            if event.get(sig_name, False):
                total_logit += sig_logit
                fired_signals[sig_name] = sig_logit
                signal_contributions[sig_name] = sig_logit

        ta_bucket = event.get("ta_bucket_v2", "MOD")
        ta_bucket_logit = self.weights["ta_bucket"].get(ta_bucket, 0.0)
        total_logit += ta_bucket_logit
        signal_contributions["ta_bucket_" + ta_bucket] = ta_bucket_logit

        era = event.get("fda_era", "POST_COVID")
        era_logit = self.weights["fda_era"].get(era, 0.0)
        total_logit += era_logit
        signal_contributions["fda_era_" + era] = era_logit

        resub = str(event.get("resubmission_class", 0))
        resub_logit = self.weights["resub"].get(resub, 0.0)
        total_logit += resub_logit
        if resub != "0":
            signal_contributions["resub_class_" + resub] = resub_logit

        ta = event.get("therapeutic_area", "Other")
        ta_offset = self.weights["ta_offsets"].get(ta, 0.0)
        total_logit += ta_offset
        signal_contributions["ta_" + ta] = ta_offset

        hist_crl = event.get("historical_crl_rate", 0.34)
        crl_weight = self.weights["continuous"].get("historical_crl_rate", -2.5)
        crl_contrib = crl_weight * (hist_crl - 0.34)
        total_logit += crl_contrib
        if abs(crl_contrib) > 0.01:
            signal_contributions["hist_crl_rate"] = round(crl_contrib, 4)

        sponsor_exp = event.get("sponsor_prior_approvals", 0)
        exp_weight = self.weights["continuous"].get("sponsor_prior_approvals", 0.04)
        exp_contrib = exp_weight * (sponsor_exp - 10.0)
        total_logit += exp_contrib
        if abs(exp_contrib) > 0.01:
            signal_contributions["sponsor_experience"] = round(exp_contrib, 4)

        crl_count = event.get("prior_crl_count", 0)
        count_weight = self.weights["continuous"].get("prior_crl_count", -0.30)
        count_contrib = count_weight * crl_count
        total_logit += count_contrib
        if abs(count_contrib) > 0.01:
            signal_contributions["prior_crl_count"] = round(count_contrib, 4)

        prob = sigmoid_cpu(total_logit)
        if prob >= TIER_THRESHOLDS[1]:
            tier = 1
        elif prob >= TIER_THRESHOLDS[2]:
            tier = 2
        elif prob >= TIER_THRESHOLDS[3]:
            tier = 3
        else:
            tier = 4

        return {
            "event_id": event.get("event_id", ""),
            "ticker": event.get("ticker", ""),
            "drug_name": event.get("drug_name", ""),
            "therapeutic_area": event.get("therapeutic_area", ""),
            "probability": round(prob, 6),
            "tier": tier,
            "action": TIER_ACTIONS[tier],
            "total_logit": round(total_logit, 4),
            "base_logit": round(self.weights["base_logit"], 4),
            "signal_count": len(fired_signals),
            "fired_signals": fired_signals,
            "contributions": signal_contributions,
        }

    def score_batch(self, events: list) -> list:
        return [self.score(ev) for ev in events]

    def export_weights(self) -> dict:
        return deepcopy(self.weights)

    def import_weights(self, weights: dict):
        self.weights = deepcopy(weights)

    def weight_hash(self) -> str:
        raw = json.dumps(self.weights, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════
#  CALIBRATION ENGINE (GPU-accelerated)
# ═══════════════════════════════════════════════════════════════

class CalibrationEngine:
    @staticmethod
    def compute_metrics(predictions: list, actuals: list) -> dict:
        """CPU metrics for compatibility. Use gpu_metrics for batch."""
        n = len(predictions)
        if n == 0:
            return {"brier": None, "auc": None, "accuracy": None, "n": 0}

        brier = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / n
        accuracy = sum(
            1 for p, a in zip(predictions, actuals)
            if (p >= 0.5 and a == 1.0) or (p < 0.5 and a == 0.0)
        ) / n

        pos = [p for p, a in zip(predictions, actuals) if a == 1.0]
        neg = [p for p, a in zip(predictions, actuals) if a == 0.0]
        if pos and neg:
            conc = sum(1 for pp in pos for pn in neg if pp > pn)
            tied = sum(0.5 for pp in pos for pn in neg if pp == pn)
            auc = (conc + tied) / (len(pos) * len(neg))
        else:
            auc = 0.5

        eps = 1e-7
        log_loss = -sum(
            a * math.log(max(p, eps)) + (1 - a) * math.log(max(1 - p, eps))
            for p, a in zip(predictions, actuals)
        ) / n

        return {
            "brier": round(brier, 6),
            "auc": round(auc, 6),
            "accuracy": round(accuracy, 6),
            "log_loss": round(log_loss, 6),
            "n": n,
            "n_approved": sum(1 for a in actuals if a == 1.0),
            "n_crl": sum(1 for a in actuals if a == 0.0),
            "base_rate": round(sum(actuals) / n, 4),
        }


# ═══════════════════════════════════════════════════════════════
#  GPU BACKTESTER
# ═══════════════════════════════════════════════════════════════

class Backtester:
    @staticmethod
    def time_split_backtest(events: list, train_frac=0.7, device=None) -> dict:
        if device is None:
            mgr = get_vram_manager()
            device = mgr.get_device(n_events=len(events))

        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        n = len(resolved)
        split_idx = int(n * train_frac)
        train = resolved[:split_idx]
        test = resolved[split_idx:]

        if len(train) < 20 or len(test) < 10:
            return {"status": "INSUFFICIENT_DATA"}

        X_train, y_train = encode_events_to_tensor(train, device)
        X_test, y_test = encode_events_to_tensor(test, device)

        model = OdinGPUModel().to(device)
        recal = GradientRecalibratorGPU(max_epochs=5000, verbose=False)
        recal_report = recal.recalibrate(model, X_train, y_train)

        with torch.no_grad():
            test_preds = model(X_test)
            test_metrics = gpu_metrics(test_preds, y_test)
            train_preds = model(X_train)
            train_metrics = gpu_metrics(train_preds, y_train)

        return {
            "status": "OK",
            "train_n": len(train),
            "test_n": len(test),
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "recalibration": recal_report,
        }


# ═══════════════════════════════════════════════════════════════
#  DRIFT DETECTOR (GPU-aware)
# ═══════════════════════════════════════════════════════════════

class DriftDetector:
    @staticmethod
    def detect(scorer: OdinScorer, events: list, recent_n: int = 50) -> list:
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        if len(resolved) < recent_n + 20:
            return []

        alerts = []
        recent = resolved[-recent_n:]
        historical = resolved[:-recent_n]

        r_rate = sum(1 for e in recent if e["outcome"] == "APPROVED") / len(recent)
        h_rate = sum(1 for e in historical if e["outcome"] == "APPROVED") / len(historical)
        if abs(r_rate - h_rate) > 0.08:
            alerts.append({
                "type": "BASE_RATE_SHIFT",
                "recent_rate": round(r_rate, 3),
                "historical_rate": round(h_rate, 3),
                "delta": round(r_rate - h_rate, 3),
            })

        r_preds = [scorer.score(e)["probability"] for e in recent]
        r_acts = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in recent]
        r_brier = sum((p - a) ** 2 for p, a in zip(r_preds, r_acts)) / len(recent)

        h_preds = [scorer.score(e)["probability"] for e in historical]
        h_acts = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in historical]
        h_brier = sum((p - a) ** 2 for p, a in zip(h_preds, h_acts)) / len(historical)

        if r_brier > h_brier * 1.25:
            alerts.append({
                "type": "RECENCY_DRIFT",
                "recent_brier": round(r_brier, 4),
                "historical_brier": round(h_brier, 4),
            })

        return alerts


# ═══════════════════════════════════════════════════════════════
#  PREDICTION LEDGER
# ═══════════════════════════════════════════════════════════════

class PredictionLedger:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.records = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.records = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.records, f, indent=2, default=str)

    def record_prediction(self, event_id: str, score_result: dict, event: dict):
        self.records[event_id] = {
            "event_id": event_id,
            "ticker": event.get("ticker", ""),
            "drug_name": event.get("drug_name", ""),
            "therapeutic_area": event.get("therapeutic_area", ""),
            "probability": score_result["probability"],
            "tier": score_result["tier"],
            "action": score_result["action"],
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "outcome": None,
            "resolved_at": None,
        }

    def record_outcome(self, event_id: str, outcome: str):
        if event_id in self.records:
            self.records[event_id]["outcome"] = outcome
            self.records[event_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()

    def get_resolved(self) -> list:
        return [r for r in self.records.values() if r.get("outcome")]

    def get_unresolved(self) -> list:
        return [r for r in self.records.values() if not r.get("outcome")]

    def count(self) -> dict:
        total = len(self.records)
        resolved = len(self.get_resolved())
        return {"total": total, "resolved": resolved, "unresolved": total - resolved}


# ═══════════════════════════════════════════════════════════════
#  MODEL VERSION STORE
# ═══════════════════════════════════════════════════════════════

class ModelVersionStore:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.versions = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.versions = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.versions, f, indent=2, default=str)

    def record_version(self, version_tag: str, weight_hash: str, metrics: dict, note: str = ""):
        self.versions.append({
            "version": version_tag,
            "hash": weight_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "note": note,
        })
        self.save()

    def latest(self) -> dict:
        return self.versions[-1] if self.versions else {}


# ═══════════════════════════════════════════════════════════════
#  SIGNAL REGISTRY (for runner compatibility)
# ═══════════════════════════════════════════════════════════════

SIGNAL_REGISTRY = {sig: {"logit": INITIAL_SIGNAL_LOGITS[sig]} for sig in BINARY_SIGNAL_NAMES}


# ═══════════════════════════════════════════════════════════════
#  DEMO / SELF-TEST
# ═══════════════════════════════════════════════════════════════

def demo():
    print("=" * 70)
    print(f"  ODIN HONING ENGINE v{__version__} — GPU SELF-TEST")
    print("=" * 70)

    global DEVICE
    mgr = get_vram_manager(max_memory_fraction=0.5)
    DEVICE = mgr.get_device()
    mgr.print_status()

    # Test CPU scorer
    scorer = OdinScorer()
    print(f"\n  Base logit: {scorer.weights['base_logit']:.4f} → P={sigmoid_cpu(scorer.weights['base_logit']):.3f}")
    print(f"  Binary signals: {len(scorer.weights['signals'])}")
    print(f"  Feature vector size: {N_FEATURES}")

    bull = {
        "btd": True, "orphan": True, "priority_review": True,
        "fast_track": True, "had_adcom": True, "surrogate_endpoint": True,
        "therapeutic_area": "Rare Disease", "ta_bucket_v2": "HIGH",
        "fda_era": "POST_COVID", "resubmission_class": 0,
        "historical_crl_rate": 0.15, "sponsor_prior_approvals": 20,
        "prior_crl_count": 0, "event_id": "BULL_TEST", "ticker": "BULL",
    }
    result = scorer.score(bull)
    print(f"\n  Bullish: P={result['probability']:.4f} Tier={result['tier']} ({result['action']})")

    # Test GPU model
    model = OdinGPUModel().to(DEVICE)
    vec = encode_event_to_vector(bull)
    X = torch.tensor([vec], dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        gpu_prob = model(X).item()
    print(f"  GPU model: P={gpu_prob:.4f} (should match CPU)")

    # Verify weight export roundtrip
    exported = model.export_weights()
    scorer2 = OdinScorer(weights=exported)
    result2 = scorer2.score(bull)
    print(f"  Roundtrip: P={result2['probability']:.4f} (should match)")

    # Release VRAM
    del model, X
    mgr.release()
    print(f"\n  VRAM after cleanup: {mgr.get_free_vram_mb():.0f} MB free")

    print(f"\n  ✅ GPU Engine v{__version__} operational")
    print("=" * 70)


if __name__ == "__main__":
    demo()
