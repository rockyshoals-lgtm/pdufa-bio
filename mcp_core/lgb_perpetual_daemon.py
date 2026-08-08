#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — PERPETUAL LightGBM AUTO-ML DAEMON                           ║
║                                                                          ║
║  Runs 24/7 as a background process. Each round:                          ║
║    1. Optuna Bayesian search for hyperparameters                         ║
║    2. Feature co-evolution (auto-engineer + select)                      ║
║    3. Walk-forward validation (no temporal leakage)                      ║
║    4. Ensemble stacking (blend top-K checkpoints)                        ║
║    5. Champion ladder (never regresses — only promotes)                  ║
║                                                                          ║
║  Kill switch: create STOP file in 9realms/ to gracefully halt.           ║
║  Logs: alerts/lgb_daemon_log.txt                                         ║
║  Champions: models/lgb_champions/                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import math
import os
import pickle
import sys
import time
import hashlib
import itertools
import logging
import signal
import traceback
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import lightgbm as lgb
import numpy as np
import optuna
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import StratifiedKFold

# Kaizen adaptive intelligence
try:
    from kaizen_engine import KaizenTracker
    KAIZEN_ENABLED = True
except ImportError:
    KAIZEN_ENABLED = False

# AI-in-the-loop advisor
try:
    from ai_advisor import AIAdvisor, load_ai_feature_overrides, clear_ai_feature_overrides
    AI_ADVISOR_AVAILABLE = True
except ImportError:
    AI_ADVISOR_AVAILABLE = False

optuna.logging.set_verbosity(optuna.logging.WARNING)

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
REALMS_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REALMS_ROOT / "data"
MODELS_DIR = REALMS_ROOT / "models"
CHAMPIONS_DIR = MODELS_DIR / "lgb_champions"
VALIDATION_DIR = REALMS_ROOT / "validation"
ALERTS_DIR = REALMS_ROOT / "alerts"
STOP_FILE = REALMS_ROOT / "STOP"

DATASET_PATH = REALMS_ROOT / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
LADDER_PATH = CHAMPIONS_DIR / "champion_ladder.json"
ENSEMBLE_DIR = CHAMPIONS_DIR / "ensemble_pool"

for d in [CHAMPIONS_DIR, ENSEMBLE_DIR, ALERTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════
LOG_PATH = ALERTS_DIR / "lgb_daemon_log.txt"
# Force UTF-8 on Windows to handle emoji in log messages
_fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
_sh = logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_fh, _sh],
)
log = logging.getLogger("lgb_daemon")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
SLEEP_BETWEEN_ROUNDS = 5        # seconds pause between rounds (tuned: faster iteration)
OPTUNA_TRIALS_PER_ROUND = 40    # Bayesian trials per evolution round (tuned: wider search)
ENSEMBLE_POOL_SIZE = 10         # top-K models to keep for stacking (tuned: richer ensemble)
FEATURE_MUTATION_RATE = 0.3     # prob of adding/removing a feature each round (adaptive via Kaizen)
WF_MIN_YEAR = 2021              # walk-forward starts here
WF_MIN_TRAIN = 50               # minimum training samples
WF_MIN_TEST = 10                # minimum test samples
MAX_ROUNDS = 999_999            # safety cap (effectively infinite)
PROMOTE_THRESHOLD_AUC = 0.0003  # tuned: slightly lower bar = faster champion ladder fills
KAIZEN_DIR = REALMS_ROOT / "kaizen"

# graceful shutdown
SHUTDOWN = False
def _signal_handler(sig, frame):
    global SHUTDOWN
    log.info("⚡ Shutdown signal received — finishing current round...")
    SHUTDOWN = True
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════

# Base columns from ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv (2,210 events)
BASE_FEATURES = [
    # Core regulatory designations
    "btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
    "sponsor_prior_approvals",
    # AdCom
    "had_adcom", "adcom_vote_pct",
    # Manufacturing / CMC risk
    "manufacturing_risk", "form_483_issues", "ema_cmc_flag", "cmc_extension_flag",
    # Prior CRL history
    "prior_crl", "prior_crl_count", "double_crl_flag",
    # Resubmission
    "resubmission_class",
    # Therapeutic area signals
    "ta_base_score", "historical_crl_rate", "ta_very_high_risk", "ta_bucket_v2",
    # Signal strength / model scores
    "s22_ped_pk_missing", "s23_signal_strength", "s6_signal_strength",
    "social_sentiment_score",
    "v1067_score", "v1070_score",
    # Binary flags
    "gene_therapy", "psychedelics", "surrogate_endpoint", "single_arm_study",
    "safety_signal_severity", "ppm_flag", "fda_era",
    # Pre-computed interactions
    "btd_oncology_interaction", "btd_priority_interaction",
]

BOOL_COLS = {
    "btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
    "had_adcom", "manufacturing_risk", "prior_crl",
    "form_483_issues", "ema_cmc_flag", "cmc_extension_flag",
    "double_crl_flag", "gene_therapy", "psychedelics",
    "surrogate_endpoint", "single_arm_study", "ppm_flag",
    "ta_very_high_risk", "s22_ped_pk_missing",
}

# All possible engineered features (the daemon toggles subsets on/off)
ALL_ENGINEERED = {
    # Simple derived
    "is_resubmission":       lambda r: 1.0 if str(r.get("resubmission_class","") or "").strip() else 0.0,
    "is_class1_resub":       lambda r: 1.0 if str(r.get("resubmission_class","") or "").strip() == "1" else 0.0,
    "is_oncology":           lambda r: 1.0 if (r.get("therapeutic_area","") or "").lower() == "oncology" else 0.0,
    "is_neurology":          lambda r: 1.0 if (r.get("therapeutic_area","") or "").lower() in ("neurology","cns","psychiatry") else 0.0,
    "is_pain":               lambda r: 1.0 if "pain" in (r.get("therapeutic_area","") or "").lower() else 0.0,
    "is_ophthalmology":      lambda r: 1.0 if "ophthal" in (r.get("therapeutic_area","") or "").lower() else 0.0,
    "is_rare_disease":       lambda r: 1.0 if "rare" in (r.get("therapeutic_area","") or "").lower() else 0.0,
    "is_hoeg_era":           lambda r: 1.0 if _year(r) >= 2024 else 0.0,
    "year":                  lambda r: float(_year(r)),
    # Interaction terms using v1071 columns
    "prior_crl_x_ta_base":   lambda r: _bfloat(r,"prior_crl") * _fval(r,"ta_base_score"),
    "btd_x_oncology":        lambda r: _bfloat(r,"btd") * (1.0 if (r.get("therapeutic_area","") or "").lower()=="oncology" else 0.0),
    "mfg_x_prior_crl":       lambda r: _bfloat(r,"manufacturing_risk") * _bfloat(r,"prior_crl"),
    "mfg_x_483":             lambda r: _bfloat(r,"manufacturing_risk") * _bfloat(r,"form_483_issues"),
    "orphan_x_surrogate":    lambda r: _bfloat(r,"orphan") * _bfloat(r,"surrogate_endpoint"),
    "single_arm_x_safety":   lambda r: _bfloat(r,"single_arm_study") * _fval(r,"safety_signal_severity"),
    "gene_x_cmc":            lambda r: _bfloat(r,"gene_therapy") * _bfloat(r,"cmc_extension_flag"),
    "crl_count_x_ta_risk":   lambda r: _fval(r,"prior_crl_count") * _fval(r,"historical_crl_rate"),
    "s23_x_s6":              lambda r: _fval(r,"s23_signal_strength") * _fval(r,"s6_signal_strength"),
    "v1070_x_social":        lambda r: _fval(r,"v1070_score") * _fval(r,"social_sentiment_score"),
    # Polynomial / ratio features
    "ta_base_sq":            lambda r: _fval(r,"ta_base_score") ** 2,
    "log_sponsor_approvals": lambda r: math.log1p(_fval(r,"sponsor_prior_approvals")),
    "log_crl_rate":          lambda r: math.log1p(_fval(r,"historical_crl_rate")),
    "v1067_minus_v1070":     lambda r: _fval(r,"v1067_score") - _fval(r,"v1070_score"),
    "safety_sq":             lambda r: _fval(r,"safety_signal_severity") ** 2,
}

# ═══════════════════════════════════════════════════════════════
# FEATURE DISCOVERY ENGINE — auto-discovers new signal interactions
# ═══════════════════════════════════════════════════════════════

# Numeric columns eligible for pairwise interactions & transforms
_NUMERIC_COLS = [
    "sponsor_prior_approvals", "adcom_vote_pct",
    "prior_crl_count", "resubmission_class",
    "ta_base_score", "historical_crl_rate",
    "s23_signal_strength", "s6_signal_strength", "social_sentiment_score",
    "v1067_score", "v1070_score",
    "safety_signal_severity", "ta_bucket_v2",
]

# Boolean columns eligible for AND/OR combinations
_BOOL_DISCOVERY_COLS = [
    "btd", "orphan", "priority_review", "fast_track", "accelerated_approval",
    "had_adcom", "manufacturing_risk", "prior_crl",
    "form_483_issues", "ema_cmc_flag", "cmc_extension_flag",
    "double_crl_flag", "gene_therapy", "psychedelics",
    "surrogate_endpoint", "single_arm_study", "ppm_flag",
    "ta_very_high_risk", "s22_ped_pk_missing",
]

DISCOVERED_FEATURES_PATH = KAIZEN_DIR / "discovered_features.json"
DISCOVERY_NEW_PER_ROUND = 6         # new random candidates per round
DISCOVERY_MAX_POOL = 120            # max total discovered features in pool
DISCOVERY_PRUNE_AFTER_ROUNDS = 30   # prune underperformers after this many rounds
DISCOVERY_MIN_APPEARANCES = 5       # min tries before eligible for pruning

def _make_product(a, b):
    """Generate a product interaction lambda."""
    return lambda r: _fval(r, a) * _fval(r, b)

def _make_bool_product(a, b):
    """Generate a boolean AND interaction lambda."""
    return lambda r: _bfloat(r, a) * _bfloat(r, b)

def _make_bool_or(a, b):
    """Generate a boolean OR interaction lambda."""
    return lambda r: max(_bfloat(r, a), _bfloat(r, b))

def _make_ratio(a, b):
    """Generate a ratio lambda (a / (b + eps))."""
    return lambda r: _fval(r, a) / (_fval(r, b) + 0.001)

def _make_diff(a, b):
    """Generate a difference lambda (a - b)."""
    return lambda r: _fval(r, a) - _fval(r, b)

def _make_log(a):
    """Generate a log1p transform lambda."""
    return lambda r: math.log1p(abs(_fval(r, a)))

def _make_square(a):
    """Generate a square transform lambda."""
    return lambda r: _fval(r, a) ** 2

def _make_sqrt(a):
    """Generate a sqrt transform lambda."""
    return lambda r: math.sqrt(abs(_fval(r, a)))

def _make_num_x_bool(num_col, bool_col):
    """Generate numeric * boolean interaction."""
    return lambda r: _fval(r, num_col) * _bfloat(r, bool_col)

# Transform type registry — each returns (name, lambda, description)
_TRANSFORM_TYPES = {
    "product":    {"gen": _make_product,    "arity": 2, "pool": "numeric",  "fmt": "{a}_x_{b}"},
    "ratio":      {"gen": _make_ratio,      "arity": 2, "pool": "numeric",  "fmt": "{a}_div_{b}"},
    "diff":       {"gen": _make_diff,        "arity": 2, "pool": "numeric",  "fmt": "{a}_minus_{b}"},
    "bool_and":   {"gen": _make_bool_product,"arity": 2, "pool": "bool",     "fmt": "{a}_and_{b}"},
    "bool_or":    {"gen": _make_bool_or,     "arity": 2, "pool": "bool",     "fmt": "{a}_or_{b}"},
    "num_x_bool": {"gen": _make_num_x_bool,  "arity": 2, "pool": "mixed",   "fmt": "{a}_x_{b}"},
    "log":        {"gen": _make_log,         "arity": 1, "pool": "numeric",  "fmt": "log_{a}"},
    "square":     {"gen": _make_square,      "arity": 1, "pool": "numeric",  "fmt": "sq_{a}"},
    "sqrt":       {"gen": _make_sqrt,        "arity": 1, "pool": "numeric",  "fmt": "sqrt_{a}"},
}


class FeatureDiscoveryEngine:
    """
    Auto-discovers new feature interactions beyond the hand-crafted ALL_ENGINEERED pool.

    Each round, generates random candidate interactions from BASE_FEATURES columns,
    tracks which ones contribute to champion promotions, and prunes underperformers.
    Successful discoveries are persisted and reused across sessions.
    """

    def __init__(self, persist_path=None):
        self.persist_path = persist_path or DISCOVERED_FEATURES_PATH
        self.pool = {}           # name -> {"transform": str, "args": list, "lambda": callable,
                                 #          "hits": int, "appearances": int, "round_added": int}
        self._load()

    def _load(self):
        """Load persisted discovered features."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path) as f:
                    data = json.load(f)
                for name, meta in data.get("features", {}).items():
                    lam = self._rebuild_lambda(meta["transform"], meta["args"])
                    if lam is not None:
                        self.pool[name] = {
                            "transform": meta["transform"],
                            "args": meta["args"],
                            "lambda": lam,
                            "hits": meta.get("hits", 0),
                            "appearances": meta.get("appearances", 0),
                            "round_added": meta.get("round_added", 0),
                        }
                log.info(f"  🔬 Discovery engine loaded {len(self.pool)} persisted features")
            except Exception as e:
                log.warning(f"  ⚠ Failed to load discovered features: {e}")

    def _rebuild_lambda(self, transform, args):
        """Reconstruct lambda from serialized transform type + args."""
        spec = _TRANSFORM_TYPES.get(transform)
        if not spec:
            return None
        try:
            if spec["arity"] == 1:
                return spec["gen"](args[0])
            elif spec["arity"] == 2:
                return spec["gen"](args[0], args[1])
        except Exception:
            return None

    def save(self):
        """Persist discovered feature pool to JSON."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"features": {}}
        for name, meta in self.pool.items():
            data["features"][name] = {
                "transform": meta["transform"],
                "args": meta["args"],
                "hits": meta["hits"],
                "appearances": meta["appearances"],
                "round_added": meta["round_added"],
            }
        data["pool_size"] = len(self.pool)
        data["saved_at"] = datetime.now().isoformat()
        with open(self.persist_path, "w") as f:
            json.dump(data, f, indent=2)

    def generate_candidates(self, rng, n=DISCOVERY_NEW_PER_ROUND, round_num=0):
        """Generate N random new feature candidates not already in pool or ALL_ENGINEERED."""
        existing = set(self.pool.keys()) | set(ALL_ENGINEERED.keys())
        new_features = {}
        attempts = 0
        max_attempts = n * 20  # avoid infinite loops

        while len(new_features) < n and attempts < max_attempts:
            attempts += 1
            transform = rng.choice(list(_TRANSFORM_TYPES.keys()))
            spec = _TRANSFORM_TYPES[transform]

            if spec["pool"] == "numeric":
                cols = _NUMERIC_COLS
            elif spec["pool"] == "bool":
                cols = _BOOL_DISCOVERY_COLS
            elif spec["pool"] == "mixed":
                # First arg is numeric, second is bool
                num_col = rng.choice(_NUMERIC_COLS)
                bool_col = rng.choice(_BOOL_DISCOVERY_COLS)
                name = f"d_{spec['fmt'].format(a=num_col, b=bool_col)}"
                if name in existing or name in new_features:
                    continue
                lam = spec["gen"](num_col, bool_col)
                new_features[name] = {
                    "transform": transform,
                    "args": [num_col, bool_col],
                    "lambda": lam,
                    "hits": 0,
                    "appearances": 0,
                    "round_added": round_num,
                }
                continue

            if spec["arity"] == 1:
                col = rng.choice(cols)
                name = f"d_{spec['fmt'].format(a=col)}"
                if name in existing or name in new_features:
                    continue
                lam = spec["gen"](col)
                new_features[name] = {
                    "transform": transform,
                    "args": [col],
                    "lambda": lam,
                    "hits": 0,
                    "appearances": 0,
                    "round_added": round_num,
                }
            elif spec["arity"] == 2:
                idxs = rng.choice(len(cols), 2, replace=False)
                a, b = cols[idxs[0]], cols[idxs[1]]
                name = f"d_{spec['fmt'].format(a=a, b=b)}"
                if name in existing or name in new_features:
                    continue
                lam = spec["gen"](a, b)
                new_features[name] = {
                    "transform": transform,
                    "args": [a, b],
                    "lambda": lam,
                    "hits": 0,
                    "appearances": 0,
                    "round_added": round_num,
                }

        # Add to pool (only if room remains)
        added = []
        for name, meta in new_features.items():
            if len(self.pool) < DISCOVERY_MAX_POOL:
                self.pool[name] = meta
                added.append(name)

        return added  # Only return names that were actually added to pool

    def get_all_lambdas(self):
        """Return dict of name -> lambda for all discovered features in the pool."""
        return {name: meta["lambda"] for name, meta in self.pool.items()}

    def record_appearance(self, feat_name):
        """Track that a discovered feature was tried."""
        if feat_name in self.pool:
            self.pool[feat_name]["appearances"] += 1

    def record_hit(self, feat_name):
        """Track that a discovered feature appeared in a champion."""
        if feat_name in self.pool:
            self.pool[feat_name]["hits"] += 1

    def get_feature_scores(self):
        """Return discovered features sorted by win rate (hits / appearances)."""
        scored = []
        for name, meta in self.pool.items():
            apps = meta["appearances"]
            hits = meta["hits"]
            win_rate = hits / max(apps, 1)
            scored.append((name, win_rate, hits, apps))
        scored.sort(key=lambda x: (-x[1], -x[2]))
        return scored

    def prune_underperformers(self, current_round):
        """Remove features with 0 hits after sufficient appearances."""
        to_remove = []
        for name, meta in self.pool.items():
            age = current_round - meta["round_added"]
            if (age >= DISCOVERY_PRUNE_AFTER_ROUNDS and
                    meta["appearances"] >= DISCOVERY_MIN_APPEARANCES and
                    meta["hits"] == 0):
                to_remove.append(name)

        for name in to_remove:
            del self.pool[name]

        if to_remove:
            log.info(f"  🧹 Pruned {len(to_remove)} underperforming discovered features")
        return to_remove

    def get_pool_names(self):
        """Return list of all discovered feature names."""
        return list(self.pool.keys())


def _bflag(row, col):
    v = row.get(col, "")
    if isinstance(v, bool): return v
    return str(v).strip().upper() in ("TRUE", "1", "YES", "T")

def _bfloat(row, col):
    return 1.0 if _bflag(row, col) else 0.0

def _fval(row, col, default=0.0):
    try:
        v = row.get(col, "") if isinstance(row, dict) else row
        v = str(v).strip() if not isinstance(v, (int, float)) else v
        return float(v) if v != "" else default
    except (ValueError, TypeError):
        return default

def _year(row):
    """Extract year from catalyst_date — handles YYYY-MM-DD and M/D/YYYY formats."""
    d = (row.get("catalyst_date","") or "").strip()
    if not d:
        return 0
    try:
        # Try YYYY-MM-DD first
        if d[4:5] == "-":
            return int(d[:4])
        # Try M/D/YYYY or MM/DD/YYYY
        parts = d.split("/")
        if len(parts) == 3:
            return int(parts[2])
        # Fallback: try first 4 chars
        return int(d[:4])
    except (ValueError, IndexError):
        return 0


def load_raw_rows():
    """Load CSV rows as list of dicts."""
    with open(DATASET_PATH, encoding="utf-8", errors="replace") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("outcome","") or "").strip().upper() in ("APPROVAL","CRL")]


def build_feature_matrix(rows, base_cols, eng_names, discovery_engine=None):
    """Build X, y, years from rows + selected feature set.

    Looks up feature lambdas from ALL_ENGINEERED first, then falls back
    to the discovery engine's pool for auto-discovered features.
    """
    all_cols = list(base_cols) + list(eng_names)

    # Build combined func lookup: hand-crafted + discovered
    eng_funcs = {}
    for k in eng_names:
        if k in ALL_ENGINEERED:
            eng_funcs[k] = ALL_ENGINEERED[k]
        elif discovery_engine and k in discovery_engine.pool:
            eng_funcs[k] = discovery_engine.pool[k]["lambda"]
        # else: feature will be 0.0 (unknown name — silently skip)

    X_list, y_list, yr_list = [], [], []
    for row in rows:
        feat = {}
        # Base
        for col in base_cols:
            if col in BOOL_COLS:
                feat[col] = _bfloat(row, col)
            else:
                feat[col] = _fval(row, col)
        # Engineered + Discovered
        for name, func in eng_funcs.items():
            try:
                feat[name] = func(row)
            except Exception:
                feat[name] = 0.0

        X_list.append([feat.get(c, 0.0) for c in all_cols])
        y_list.append(1 if row.get("outcome","").strip().upper() == "APPROVAL" else 0)
        yr_list.append(_year(row))

    return np.array(X_list), np.array(y_list), np.array(yr_list), all_cols


# ═══════════════════════════════════════════════════════════════
# WALK-FORWARD EVALUATOR
# ═══════════════════════════════════════════════════════════════

def walk_forward_auc(X, y, years, params, feature_names):
    """Walk-forward AUC — the ONLY metric that matters for promotion."""
    unique_years = sorted(set(years[years > 0]))
    aucs = []
    briers = []
    t4_precs = []

    for test_year in unique_years:
        if test_year < WF_MIN_YEAR:
            continue
        train_mask = (years < test_year) & (years > 0)
        test_mask = years == test_year
        if train_mask.sum() < WF_MIN_TRAIN or test_mask.sum() < WF_MIN_TEST:
            continue

        X_tr, y_tr = X[train_mask], y[train_mask]
        X_te, y_te = X[test_mask], y[test_mask]

        p = dict(params)
        neg, pos = (y_tr==0).sum(), (y_tr==1).sum()
        p["scale_pos_weight"] = neg / max(pos, 1)

        dtrain = lgb.Dataset(X_tr, label=y_tr, feature_name=feature_names)
        dval = lgb.Dataset(X_te, label=y_te, reference=dtrain, feature_name=feature_names)

        model = lgb.train(p, dtrain, valid_sets=[dval],
                          callbacks=[lgb.log_evaluation(0)])
        preds = model.predict(X_te)

        aucs.append(roc_auc_score(y_te, preds))
        briers.append(brier_score_loss(y_te, preds))

        t4 = preds < 0.40
        if t4.sum() > 0:
            t4_precs.append((y_te[t4]==0).sum() / t4.sum())

    if not aucs:
        return {"wf_auc": 0.0, "wf_brier": 1.0, "wf_t4p": 0.0, "n_years": 0}

    return {
        "wf_auc": float(np.mean(aucs)),
        "wf_brier": float(np.mean(briers)),
        "wf_t4p": float(np.mean(t4_precs)) if t4_precs else 0.0,
        "n_years": len(aucs),
        "yearly_aucs": [round(a, 4) for a in aucs],
    }


# ═══════════════════════════════════════════════════════════════
# FEATURE CO-EVOLUTION
# ═══════════════════════════════════════════════════════════════

def mutate_features(current_eng, rng, discovery_engine=None):
    """Randomly add/remove engineered + discovered features.

    Pulls from both the hand-crafted ALL_ENGINEERED pool and the
    auto-discovered feature pool maintained by FeatureDiscoveryEngine.
    Discovered features with champion hits get a bias toward retention.
    AI advisor feature gate/block overrides are applied last.
    """
    # Combined mutation pool: hand-crafted + discovered
    all_eng = list(ALL_ENGINEERED.keys())
    if discovery_engine:
        all_eng += discovery_engine.get_pool_names()

    current = set(current_eng)

    for feat in all_eng:
        if rng.random() < FEATURE_MUTATION_RATE:
            if feat in current:
                # Discovered features with hits are harder to drop
                if discovery_engine and feat in discovery_engine.pool:
                    meta = discovery_engine.pool[feat]
                    if meta["hits"] > 0 and rng.random() < 0.5:
                        continue  # 50% chance to protect proven discoveries
                current.discard(feat)  # drop
            else:
                current.add(feat)      # add

    # Bias: with 15% prob, inject a random discovered feature that has never been tried
    if discovery_engine and rng.random() < 0.15:
        untried = [n for n, m in discovery_engine.pool.items()
                   if m["appearances"] == 0 and n not in current]
        if untried:
            pick = rng.choice(untried)
            current.add(pick)

    # Apply AI advisor feature gate/block overrides
    if AI_ADVISOR_AVAILABLE:
        overrides = load_ai_feature_overrides(KAIZEN_DIR)
        if overrides:
            # Force-include gated features
            for feat in overrides.get("feature_gate", []):
                if feat in all_eng:
                    current.add(feat)
            # Remove blocked features
            for feat in overrides.get("feature_block", []):
                current.discard(feat)

    # Always keep at least 'year' and 'is_hoeg_era'
    current.add("year")
    current.add("is_hoeg_era")
    return sorted(current)


# ═══════════════════════════════════════════════════════════════
# OPTUNA OBJECTIVE
# ═══════════════════════════════════════════════════════════════

def make_objective(X, y, years, feature_names):
    """Create Optuna objective that maximizes walk-forward AUC."""
    def objective(trial):
        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": trial.suggest_categorical("boosting", ["gbdt", "dart"]),
            "num_leaves": trial.suggest_int("num_leaves", 8, 128),
            "learning_rate": trial.suggest_float("lr", 0.005, 0.3, log=True),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 10),
            "min_child_samples": trial.suggest_int("min_child_samples", 3, 50),
            "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
            "min_gain_to_split": trial.suggest_float("min_gain_to_split", 0.0, 1.0),
            "max_depth": trial.suggest_int("max_depth", -1, 12),
            "verbose": -1,
            "seed": 42,
            "n_estimators": trial.suggest_int("n_estimators", 100, 1500),
            "early_stopping_rounds": 50,
        }
        if params["boosting_type"] == "dart":
            params["drop_rate"] = trial.suggest_float("drop_rate", 0.01, 0.3)
            params["skip_drop"] = trial.suggest_float("skip_drop", 0.1, 0.7)

        result = walk_forward_auc(X, y, years, params, feature_names)
        return result["wf_auc"]

    return objective


# ═══════════════════════════════════════════════════════════════
# ENSEMBLE STACKING
# ═══════════════════════════════════════════════════════════════

def train_full_model(X, y, params, feature_names):
    """Train on full data, return calibrated model."""
    p = dict(params)
    neg, pos = (y==0).sum(), (y==1).sum()
    p["scale_pos_weight"] = neg / max(pos, 1)
    if "early_stopping_rounds" in p:
        del p["early_stopping_rounds"]

    model = lgb.LGBMClassifier(**p)
    model.fit(X, y)

    calibrated = CalibratedClassifierCV(model, cv=5, method="sigmoid")
    calibrated.fit(X, y)
    return model, calibrated


def load_ensemble_pool():
    """Load all models in the ensemble pool."""
    pool = []
    for pkl_path in sorted(ENSEMBLE_DIR.glob("*.pkl")):
        try:
            with open(pkl_path, "rb") as f:
                entry = pickle.load(f)
            pool.append(entry)
        except Exception:
            pass
    return pool


def ensemble_predict(pool, X):
    """Weighted average of ensemble pool predictions."""
    if not pool:
        return None

    # Weight by walk-forward AUC
    preds_list = []
    weights = []
    for entry in pool:
        cal = entry.get("calibrated")
        if cal is None:
            continue
        try:
            p = cal.predict_proba(X)[:, 1]
            w = entry.get("wf_auc", 0.5)
            preds_list.append(p)
            weights.append(w)
        except Exception:
            continue

    if not preds_list:
        return None

    weights = np.array(weights)
    weights = weights / weights.sum()
    stacked = np.zeros(X.shape[0])
    for p, w in zip(preds_list, weights):
        stacked += p * w
    return stacked


# ═══════════════════════════════════════════════════════════════
# CHAMPION LADDER
# ═══════════════════════════════════════════════════════════════

def load_ladder():
    """Load champion ladder from disk."""
    if LADDER_PATH.exists():
        with open(LADDER_PATH) as f:
            return json.load(f)
    return {
        "current_champion": None,
        "history": [],
        "total_rounds": 0,
        "total_promotions": 0,
    }


def save_ladder(ladder):
    with open(LADDER_PATH, "w") as f:
        json.dump(ladder, f, indent=2)


def promote_champion(ladder, candidate, round_num):
    """Promote a new champion if it beats the current one."""
    old_auc = 0.0
    if ladder["current_champion"]:
        old_auc = ladder["current_champion"].get("wf_auc", 0.0)

    new_auc = candidate["wf_auc"]
    delta = new_auc - old_auc

    if delta >= PROMOTE_THRESHOLD_AUC or ladder["current_champion"] is None:
        log.info(f"🏆 NEW CHAMPION: WF AUC {new_auc:.6f} (Δ{delta:+.6f} vs {old_auc:.6f})")
        ladder["history"].append({
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "wf_auc": new_auc,
            "wf_brier": candidate.get("wf_brier"),
            "wf_t4p": candidate.get("wf_t4p"),
            "delta": round(delta, 6),
            "n_features": candidate.get("n_features"),
            "eng_features": candidate.get("eng_features"),
            "params_hash": candidate.get("params_hash"),
        })
        ladder["current_champion"] = candidate
        ladder["total_promotions"] += 1
        return True
    else:
        log.info(f"  ❌ Not promoted: {new_auc:.6f} < champion {old_auc:.6f} + {PROMOTE_THRESHOLD_AUC}")
        return False


# ═══════════════════════════════════════════════════════════════
# MAIN DAEMON LOOP
# ═══════════════════════════════════════════════════════════════

def run_one_round(round_num, rows, ladder, rng, discovery_engine=None):
    """Execute one full auto-ML round."""
    ts_start = time.time()

    # ── Step 0: Generate new discovery candidates ────────────
    if discovery_engine:
        new_discovered = discovery_engine.generate_candidates(rng, round_num=round_num)
        if new_discovered:
            log.info(f"  🔬 Discovery: generated {len(new_discovered)} new candidates "
                     f"(pool: {len(discovery_engine.pool)} total)")
            for nd in new_discovered[:3]:
                meta = discovery_engine.pool.get(nd)
                if meta:
                    log.info(f"     ↳ {nd} ({meta['transform']}: {meta['args']})")

    # ── Step 1: Feature mutation ─────────────────────────────
    if ladder["current_champion"] and ladder["current_champion"].get("eng_features"):
        prev_eng = ladder["current_champion"]["eng_features"]
    else:
        # Start with the original challenger feature set
        prev_eng = [
            "is_resubmission", "is_class1_resub", "is_gene_therapy",
            "is_oncology", "is_neurology", "is_pain",
            "is_hoeg_era", "year",
            "desig_x_experienced", "prior_crl_x_base_rate",
        ]

    new_eng = mutate_features(prev_eng, rng, discovery_engine=discovery_engine)

    # Separate hand-crafted vs discovered for logging
    hand_crafted = [f for f in new_eng if f in ALL_ENGINEERED]
    discovered = [f for f in new_eng if discovery_engine and f in discovery_engine.pool]
    log.info(f"  Features: {len(BASE_FEATURES)} base + {len(hand_crafted)} hand-crafted + "
             f"{len(discovered)} discovered = {len(BASE_FEATURES)+len(new_eng)} total")
    if discovered:
        log.info(f"  🔬 Discovered features active: {discovered}")

    # Track appearances for discovered features
    if discovery_engine:
        for feat in new_eng:
            discovery_engine.record_appearance(feat)

    # ── Step 2: Build feature matrix ─────────────────────────
    X, y, years, feat_names = build_feature_matrix(rows, BASE_FEATURES, new_eng, discovery_engine=discovery_engine)

    # ── Step 3: Optuna hyperparameter search ─────────────────
    study = optuna.create_study(direction="maximize",
                                 sampler=optuna.samplers.TPESampler(seed=rng.randint(0, 2**31)))

    objective = make_objective(X, y, years, feat_names)
    study.optimize(objective, n_trials=OPTUNA_TRIALS_PER_ROUND, show_progress_bar=False)

    best_params = study.best_params
    best_wf_auc = study.best_value
    log.info(f"  Optuna best WF AUC: {best_wf_auc:.6f} ({OPTUNA_TRIALS_PER_ROUND} trials)")

    # Reconstruct full params dict
    full_params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": best_params.pop("boosting", "gbdt"),
        "num_leaves": best_params.pop("num_leaves", 31),
        "learning_rate": best_params.pop("lr", 0.05),
        "feature_fraction": best_params.pop("feature_fraction", 0.8),
        "bagging_fraction": best_params.pop("bagging_fraction", 0.8),
        "bagging_freq": best_params.pop("bagging_freq", 5),
        "min_child_samples": best_params.pop("min_child_samples", 10),
        "lambda_l1": best_params.pop("lambda_l1", 1e-6),
        "lambda_l2": best_params.pop("lambda_l2", 1e-6),
        "min_gain_to_split": best_params.pop("min_gain_to_split", 0.0),
        "max_depth": best_params.pop("max_depth", -1),
        "verbose": -1,
        "seed": 42,
        "n_estimators": best_params.pop("n_estimators", 500),
    }
    if full_params["boosting_type"] == "dart":
        full_params["drop_rate"] = best_params.pop("drop_rate", 0.1)
        full_params["skip_drop"] = best_params.pop("skip_drop", 0.5)

    # ── Step 4: Full walk-forward eval with best params ──────
    wf_result = walk_forward_auc(X, y, years, {**full_params, "early_stopping_rounds": 50}, feat_names)
    log.info(f"  Walk-forward: AUC={wf_result['wf_auc']:.6f}, Brier={wf_result['wf_brier']:.6f}, "
             f"T4P={wf_result['wf_t4p']:.4f}, Years={wf_result['n_years']}")

    # ── Step 5: Train full model ─────────────────────────────
    model, calibrated = train_full_model(X, y, full_params, feat_names)

    # Feature importance
    importances = dict(zip(feat_names, [int(x) for x in model.feature_importances_]))
    top5 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    log.info(f"  Top features: {', '.join(f'{n}({v})' for n,v in top5)}")

    # Params hash for dedup
    params_hash = hashlib.md5(json.dumps(full_params, sort_keys=True).encode()).hexdigest()[:12]

    candidate = {
        "wf_auc": wf_result["wf_auc"],
        "wf_brier": wf_result["wf_brier"],
        "wf_t4p": wf_result["wf_t4p"],
        "yearly_aucs": wf_result.get("yearly_aucs", []),
        "n_features": len(feat_names),
        "eng_features": new_eng,
        "params": full_params,
        "params_hash": params_hash,
        "feature_importance": {n: v for n, v in sorted(importances.items(), key=lambda x: x[1], reverse=True)[:20]},
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
    }

    # ── Step 6: Add to ensemble pool ─────────────────────────
    pool_entry = {
        "model": model,
        "calibrated": calibrated,
        "wf_auc": wf_result["wf_auc"],
        "feature_names": feat_names,
        "eng_features": new_eng,
        "params_hash": params_hash,
        "round": round_num,
    }
    pool_path = ENSEMBLE_DIR / f"lgb_r{round_num:05d}_{params_hash}.pkl"
    with open(pool_path, "wb") as f:
        pickle.dump(pool_entry, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Prune ensemble pool to top K
    pool_files = sorted(ENSEMBLE_DIR.glob("*.pkl"), key=lambda p: p.stat().st_mtime)
    if len(pool_files) > ENSEMBLE_POOL_SIZE:
        # Load all, sort by AUC, keep top K
        pool_entries = []
        for pf in pool_files:
            try:
                with open(pf, "rb") as f:
                    e = pickle.load(f)
                pool_entries.append((pf, e.get("wf_auc", 0)))
            except Exception:
                pool_entries.append((pf, 0))

        pool_entries.sort(key=lambda x: x[1], reverse=True)
        for pf, _ in pool_entries[ENSEMBLE_POOL_SIZE:]:
            pf.unlink()
            log.info(f"  Pruned ensemble member: {pf.name}")

    # ── Step 7: Ensemble evaluation ──────────────────────────
    pool = load_ensemble_pool()
    if len(pool) >= 3:
        # Need a common feature set — use current X for simplicity
        # (In production you'd retrain with a union of features)
        ens_preds = ensemble_predict(pool, X)
        if ens_preds is not None:
            ens_auc = roc_auc_score(y, ens_preds)
            ens_brier = brier_score_loss(y, ens_preds)
            log.info(f"  Ensemble ({len(pool)} models): in-sample AUC={ens_auc:.6f}, Brier={ens_brier:.6f}")
            candidate["ensemble_auc_insample"] = round(ens_auc, 6)

    # ── Step 8: Champion ladder promotion ────────────────────
    promoted = promote_champion(ladder, candidate, round_num)

    # Track discovered feature hits on promotion
    if discovery_engine:
        if promoted:
            for feat in new_eng:
                discovery_engine.record_hit(feat)
            # Log top discovered features by win rate
            top_disc = discovery_engine.get_feature_scores()[:5]
            if top_disc:
                log.info(f"  🔬 Top discovered features: " +
                         ", ".join(f"{n}({h}/{a})" for n, wr, h, a in top_disc))

        # Periodic pruning of dead features
        if round_num % 10 == 0:
            discovery_engine.prune_underperformers(round_num)

        # Persist discoveries every round
        discovery_engine.save()

    if promoted:
        # Save champion model
        champ_path = CHAMPIONS_DIR / f"champion_r{round_num:05d}_{params_hash}.pkl"
        with open(champ_path, "wb") as f:
            pickle.dump({
                "model": model,
                "calibrated": calibrated,
                "feature_names": feat_names,
                "eng_features": new_eng,
                "params": full_params,
                "wf_result": wf_result,
                "round": round_num,
                "timestamp": datetime.now().isoformat(),
            }, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Also overwrite the "current best" symlink-style file
        best_path = CHAMPIONS_DIR / "CURRENT_BEST.pkl"
        with open(best_path, "wb") as f:
            pickle.dump({
                "model": model,
                "calibrated": calibrated,
                "feature_names": feat_names,
                "eng_features": new_eng,
                "params": full_params,
                "wf_result": wf_result,
                "round": round_num,
                "timestamp": datetime.now().isoformat(),
            }, f, protocol=pickle.HIGHEST_PROTOCOL)

    ladder["total_rounds"] = round_num
    save_ladder(ladder)

    elapsed = time.time() - ts_start
    log.info(f"  Round {round_num} complete in {elapsed:.1f}s | "
             f"Champion AUC: {ladder['current_champion']['wf_auc']:.6f} | "
             f"Promotions: {ladder['total_promotions']}/{round_num}")

    return promoted, {
        "wf_auc": wf_result["wf_auc"],
        "wf_brier": wf_result["wf_brier"],
        "wf_t4p": wf_result["wf_t4p"],
        "promoted": promoted,
        "eng_features": new_eng,
        "params_hash": params_hash,
        "elapsed_s": elapsed,
        "yearly_aucs": wf_result.get("yearly_aucs", []),
        "feature_importance": candidate.get("feature_importance", {}),
    }


def main():
    global FEATURE_MUTATION_RATE, OPTUNA_TRIALS_PER_ROUND
    log.info("=" * 70)
    log.info("  9REALMS PERPETUAL LightGBM AUTO-ML DAEMON (KAIZEN MODE)")
    log.info(f"  Started: {datetime.now().isoformat()}")
    log.info(f"  Dataset: {DATASET_PATH}")
    log.info(f"  Optuna trials/round: {OPTUNA_TRIALS_PER_ROUND}")
    log.info(f"  Ensemble pool size: {ENSEMBLE_POOL_SIZE}")
    log.info(f"  Promote threshold: +{PROMOTE_THRESHOLD_AUC} AUC")
    log.info(f"  Kaizen engine: {'ENABLED' if KAIZEN_ENABLED else 'DISABLED'}")
    log.info(f"  Stop file: {STOP_FILE}")
    log.info("=" * 70)

    # Initialize Kaizen tracker
    kaizen = None
    if KAIZEN_ENABLED:
        kaizen = KaizenTracker(KAIZEN_DIR)
        log.info(f"  改善 Kaizen tracker initialized → {KAIZEN_DIR}")
    else:
        log.info("  ⚠ Kaizen engine not found — running in legacy mode")

    # Initialize Feature Discovery Engine
    discovery = FeatureDiscoveryEngine(DISCOVERED_FEATURES_PATH)
    log.info(f"  🔬 Feature Discovery Engine initialized ({len(discovery.pool)} persisted features)")

    # Initialize AI Advisor (LLM-in-the-loop)
    ai_advisor = None
    if AI_ADVISOR_AVAILABLE:
        ai_advisor = AIAdvisor(KAIZEN_DIR, model_name="odin")
    else:
        log.info("  🤖 AI Advisor: module not available (import failed)")

    ai_override_rounds_left = 0  # Track expiry of AI feature overrides

    # Load data once
    rows = load_raw_rows()
    log.info(f"  Loaded {len(rows)} events")

    ladder = load_ladder()
    start_round = ladder["total_rounds"] + 1
    rng = np.random.RandomState(42 + start_round)

    if ladder["current_champion"]:
        log.info(f"  Resuming from round {start_round}, champion AUC: {ladder['current_champion']['wf_auc']:.6f}")
    else:
        log.info(f"  Fresh start — no champion yet")

    for round_num in range(start_round, start_round + MAX_ROUNDS):
        # Check stop conditions
        if SHUTDOWN:
            log.info("⚡ Graceful shutdown complete.")
            break
        if STOP_FILE.exists():
            log.info(f"🛑 STOP file detected at {STOP_FILE} — halting daemon.")
            STOP_FILE.unlink()  # Clean up
            break

        # Apply Kaizen adaptive config
        if kaizen:
            ac = kaizen.get_adaptive_config()
            FEATURE_MUTATION_RATE = ac["mutation_rate"]
            effective_trials = max(10, int(OPTUNA_TRIALS_PER_ROUND * ac["search_width"]))
            log.info(f"\n{'─'*60}")
            log.info(f"  ROUND {round_num} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log.info(f"  改善 Kaizen: score={kaizen.kaizen_score}, mutRate={ac['mutation_rate']:.3f}, "
                     f"temp={ac['temperature']:.2f}, trials={effective_trials}")
            log.info(f"{'─'*60}")
        else:
            effective_trials = OPTUNA_TRIALS_PER_ROUND
            log.info(f"\n{'─'*60}")
            log.info(f"  ROUND {round_num} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log.info(f"{'─'*60}")

        try:
            result = run_one_round(round_num, rows, ladder, rng, discovery_engine=discovery)
            promoted, metrics = result

            # Record in Kaizen tracker
            if kaizen:
                kaizen.record_round(
                    round_num=round_num,
                    wf_auc=metrics["wf_auc"],
                    wf_brier=metrics["wf_brier"],
                    wf_t4p=metrics["wf_t4p"],
                    promoted=metrics["promoted"],
                    eng_features=metrics["eng_features"],
                    params_hash=metrics["params_hash"],
                    elapsed_s=metrics["elapsed_s"],
                    yearly_aucs=metrics.get("yearly_aucs"),
                    feature_importance=metrics.get("feature_importance"),
                )
                log.info(f"  改善 Kaizen score: {kaizen.kaizen_score}/100 | "
                         f"Streak: {kaizen.current_streak} | "
                         f"Velocity: {kaizen.improvement_velocity:.1f}%")

            # ── AI Advisor: LLM-in-the-loop optimization ──────────
            if ai_advisor and ai_advisor.enabled and kaizen:
                should_call, trigger = ai_advisor.should_trigger(
                    round_num, kaizen.current_streak, metrics["promoted"]
                )
                if should_call:
                    try:
                        training_state = ai_advisor.get_training_state(
                            ladder, kaizen, discovery_engine=discovery
                        )
                        suggestions = ai_advisor.consult(training_state, trigger)
                        if suggestions and not suggestions.get("parse_error"):
                            applied = ai_advisor.apply_suggestions(
                                suggestions, kaizen, discovery_engine=discovery
                            )
                            if applied:
                                log.info(f"  🤖 AI Advisor applied {len(applied)} changes")
                                ai_override_rounds_left = suggestions.get("params", {}).get(
                                    "expires_rounds", 10
                                ) if "feature_gate" in applied or "feature_block" in applied else 0
                    except Exception as e:
                        log.warning(f"  🤖 AI Advisor error: {e}")

            # Expire AI feature overrides
            if ai_override_rounds_left > 0:
                ai_override_rounds_left -= 1
                if ai_override_rounds_left == 0 and AI_ADVISOR_AVAILABLE:
                    clear_ai_feature_overrides(KAIZEN_DIR)
                    log.info("  🤖 AI feature gate/block overrides expired")

        except Exception as e:
            log.error(f"  ❌ Round {round_num} FAILED: {e}")
            log.error(traceback.format_exc())
            # Don't crash the daemon — continue to next round
            time.sleep(5)
            continue

        # Sleep between rounds
        if SLEEP_BETWEEN_ROUNDS > 0:
            log.info(f"  💤 Sleeping {SLEEP_BETWEEN_ROUNDS}s before next round...")
            time.sleep(SLEEP_BETWEEN_ROUNDS)

    # Final summary
    ladder = load_ladder()
    log.info("\n" + "=" * 70)
    log.info("  DAEMON SESSION COMPLETE")
    log.info(f"  Total rounds: {ladder['total_rounds']}")
    log.info(f"  Total promotions: {ladder['total_promotions']}")
    if ladder["current_champion"]:
        log.info(f"  Champion WF AUC: {ladder['current_champion']['wf_auc']:.6f}")
        log.info(f"  Champion WF Brier: {ladder['current_champion']['wf_brier']:.6f}")
        log.info(f"  Champion Features: {ladder['current_champion']['n_features']}")
    if kaizen:
        log.info(f"  改善 Final Kaizen Score: {kaizen.kaizen_score}/100")
    # AI Advisor summary
    if ai_advisor:
        log.info(f"  🤖 AI Advisor calls: {ai_advisor.total_calls} | "
                 f"Suggestions applied: {ai_advisor.total_suggestions_applied}")
    # Discovery summary
    log.info(f"  🔬 Discovery pool: {len(discovery.pool)} features")
    top_disc = discovery.get_feature_scores()[:10]
    if top_disc:
        log.info(f"  🔬 Top discovered features:")
        for name, wr, hits, apps in top_disc:
            if hits > 0:
                log.info(f"     ↳ {name}: win_rate={wr:.2f} ({hits}/{apps})")
    discovery.save()
    log.info("=" * 70)


if __name__ == "__main__":
    main()
