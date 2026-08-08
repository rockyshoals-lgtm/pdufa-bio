#!/usr/bin/env python3
"""
+==========================================================================+
|  GUNGNIR v25 -- PERPETUAL GPU PHASE READOUT OPTIMIZER                   |
|  "The spear that never misses"                                         |
|                                                                        |
|  Phase 2/3 Clinical Trial Readout Prediction Engine                    |
|  Predicts positive/negative outcome from catalyst text + metadata      |
|                                                                        |
|  DATA: historical_readouts_2000.csv (2,000 phase readout events)       |
|        Features NLP-extracted from Catalyst text + Stage/Indication    |
|                                                                        |
|  ARCHITECTURE:                                                         |
|    * Island Model: CMA-ES + DE/rand + DE/best + Perturbation          |
|    * Custom CUDA kernels for fused sigmoid+brier                       |
|    * Dynamic VRAM -- fills all available GPU memory                     |
|    * L2 regularization + multi-objective fitness (AUC+Brier+Acc+ECE)  |
|    * Hall of Fame ensemble with diversity pressure                     |
|    * Cosine annealing warm restarts to escape local optima             |
|                                                                        |
|  v25 BOTTLENECK FIXES (from Gen-586 analysis):                         |
|    BN1: safety_clean sign unlocked (+1 forced) -- was locked negative  |
|    BN2: has_priority_review sign unlocked -- mixed NME/sNDA signal     |
|         + priority_review_nme interaction (pr ? ~supplemental proxy)  |
|    BN3: ta_cns_phase2 added -- CNS P2 38.1% rate was invisible         |
|                                                                        |
|  SEED (v24 gen 17460):                                                 |
|    AUC: 0.988 | Brier: 0.031 | Acc: 0.970 | Fitness: 0.960           |
+==========================================================================+
"""

import numpy as np
import json
import time
import os
import sys
import gc
import re
import signal
import math
import warnings
from datetime import datetime, timezone
from collections import deque
from typing import Dict, List, Tuple, Optional

warnings.filterwarnings("ignore")

# ============================================================================
# GPU / CPU BACKEND
# ============================================================================

GPU_AVAILABLE = False
GPU_NAME = "N/A"
GPU_VRAM_TOTAL_GB = 0.0

try:
    import cupy as cp
    from cupy.cuda import Device
    _t = cp.array([1.0, 2.0])
    _ = float(cp.sum(_t)); del _t
    GPU_AVAILABLE = True
    dev = Device(0)
    GPU_NAME = cp.cuda.runtime.getDeviceProperties(0)["name"].decode()
    GPU_VRAM_TOTAL_GB = dev.mem_info[1] / (1024**3)
    print(f"[GUNGNIR v25] GPU: {GPU_NAME} | VRAM: {GPU_VRAM_TOTAL_GB:.1f} GB | ENABLED")
except (ImportError, Exception) as e:
    import numpy as cp
    print(f"[GUNGNIR v25] GPU: DISABLED ({e}) -- running on CPU")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    sys.exit("[FATAL] pandas required -- pip install pandas")

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_FILE = "historical_readouts_2000.csv"
OUTPUT_BEST = "gungnir_v25_best.json"
OUTPUT_HISTORY = "gungnir_v25_run_history.jsonl"
OUTPUT_HALL_OF_FAME = "gungnir_v25_hall_of_fame.json"
OUTPUT_PROMOTION_LOG = "gungnir_v25_promotions.csv"
SEED_CONFIG = "gungnir_v24_best.json"   # Seed from v24 gen 17460
FEATURE_MATRIX_CACHE = "gungnir_v25_feature_matrix.npz"

TRAIN_PCT = 0.60
VAL_PCT   = 0.20

VRAM_USAGE_TARGET   = 0.85
VRAM_SAFETY_FLOOR_MB = 512
VRAM_POLL_INTERVAL  = 25

N_ISLANDS           = 4
MIGRATION_INTERVAL  = 25
WARM_RESTART_INTERVAL = 500

CMAES_SIGMA0          = 0.15
CMAES_POPULATION_FACTOR = 6
DE_F_RANGE  = (0.4, 1.0)
DE_CR_RANGE = (0.1, 0.9)
PERTURB_RADIUS_START = 0.20
PERTURB_RADIUS_END   = 0.005
PERTURB_RADIUS_CYCLE = 2000

FITNESS_AUC_WEIGHT   = 0.35
FITNESS_BRIER_WEIGHT = 0.45
FITNESS_ACC_WEIGHT   = 0.10
FITNESS_CAL_WEIGHT   = 0.10
L2_LAMBDA            = 0.0005
COMPOSITE_ALPHA      = 0.55

HOF_SIZE              = 50
HOF_DIVERSITY_THRESH  = 0.05

SAVE_INTERVAL       = 10
LOG_INTERVAL         = 1
CHECKPOINT_INTERVAL = 100


# ============================================================================
# FEATURE NAMES -- must match v23 config keys exactly for seed loading
# ============================================================================

FEATURE_NAMES = [
    "base_logit",
    # --- Phase one-hots ---
    "phase_PHASE3",
    "phase_PHASE2",
    "is_hard_endpoint",
    "is_competitive_space",
    "sentiment_score",
    "primary_endpoint_met",
    "ta_ONCOLOGY",
    "rct_x_phase3",
    "has_breakthrough",
    "has_orphan",
    "has_priority_review",
    "has_fast_track",
    "is_gene_therapy",
    "is_psychedelic",
    "safety_signal",
    "ppm_flag",
    "is_single_arm",
    "has_surrogate",
    "is_hoeg_era",
    "accel_approval_2025",
    "single_arm_2025",
    "failure_signal",
    "strong_positive",
    "dose_response",
    "safety_clean",
    "ta_CNS",
    "ta_RARE",
    "ta_PAIN",
    "ta_IMMUNOLOGY",
    "gene_therapy_x_phase3",
    "safety_x_hoeg",
    "ppm_x_hoeg",
    "oncology_x_phase3",
    "rare_x_positive",
    "failure_x_phase3",
    "p23_p2_bucket_lt_0001",
    "p23_p2_bucket_0001_001",
    "p23_p2_bucket_001_005",
    "ta_oncology_phase3",
    "ta_cns_phase3",
    "ta_rare_phase3",
    "ta_immunology_phase3",
    # --- NEW v24 features (expand search surface) ---
    "is_discontinued",
    "is_interim",
    "has_pfs",
    "has_orr_cr",
    "is_placebo_controlled",
    "is_combination",
    "has_secondary_met",
    "is_large_cap",
    "ta_RESPIRATORY",
    "ta_CARDIOVASCULAR",
    "ta_METABOLIC",
    "is_antibody",
    "phase_PHASE1",
    "phase_PHASE2B",
    "phase_PHASE1_2",
    "discontinued_x_phase3",
    "orr_x_oncology",
    "large_cap_x_phase3",
    "interim_x_phase2",
    # --- v25 BOTTLENECK FIXES ---
    # BN2: Priority review split (NME proxy vs supplemental proxy)
    "priority_review_x_phase3",   # PR in late-stage = more likely NME = strongly positive
    "priority_review_x_phase2",   # PR in mid-stage = could go either way, softer signal
    # BN3: CNS Phase 2 -- 38.1% success rate, was invisible to model
    "ta_cns_phase2",              # CNS ? Phase2 interaction (high failure penalty)
    "ta_cns_phase2b",             # CNS ? Phase2B (separate bucket)
]

N_PARAMS = len(FEATURE_NAMES)


# ============================================================================
# V23 BEST CONFIG (seed)
# ============================================================================

V23_BEST_FEATURES = {
    "base_logit": 0.3462955057621002,
    "is_hard_endpoint": -0.3365704417228699,
    "phase_PHASE3": 0.4670355021953583,
    "is_competitive_space": -0.17558380961418152,
    "sentiment_score": 1.4679408073425293,
    "phase_PHASE2": 0.3700968623161316,
    "primary_endpoint_met": 2.4717113971710205,
    "ta_ONCOLOGY": -0.7907258868217468,
    "rct_x_phase3": -0.08367640525102615,
    "has_breakthrough": 2.15628719329834,
    "has_orphan": 0.6186434030532837,
    "has_priority_review": -0.29634177684783936,
    "has_fast_track": 3.5862936973571777,
    "is_gene_therapy": -0.3958682119846344,
    "is_psychedelic": 0.31883153319358826,
    "safety_signal": -0.13183791935443878,
    "ppm_flag": -1.5974276065826416,
    "is_single_arm": 0.11841743439435959,
    "has_surrogate": 1.2399005889892578,
    "is_hoeg_era": 0.4480471611022949,
    "accel_approval_2025": 0.2740075886249542,
    "single_arm_2025": -0.044836174696683884,
    "failure_signal": -3.5416975021362305,
    "strong_positive": 0.9473345279693604,
    "dose_response": 0.4639851748943329,
    "safety_clean": 0.45,          # BN1 FIX: was -1.137 (encoding bug) -- clean safety IS positive
    "ta_CNS": -0.05,               # Base CNS penalty (most of signal now in cns_phase2)
    "ta_RARE": 1.061905860900879,
    "ta_PAIN": -0.010551675222814083,
    "ta_IMMUNOLOGY": 0.16691027581691742,
    "gene_therapy_x_phase3": -0.07750821113586426,
    "safety_x_hoeg": -0.2723233997821808,
    "ppm_x_hoeg": -0.5550639033317566,
    "oncology_x_phase3": 0.2469012439250946,
    "rare_x_positive": 0.11126620322465897,
    "failure_x_phase3": -0.9167983531951904,
    "p23_p2_bucket_lt_0001": 1.5855114459991455,
    "p23_p2_bucket_0001_001": 0.5755207538604736,
    "p23_p2_bucket_001_005": 0.021341858431696892,
    "ta_oncology_phase3": -0.21190723776817322,
    "ta_cns_phase3": -0.4557994306087494,
    "ta_rare_phase3": 0.4439097046852112,
    "ta_immunology_phase3": 0.5111908912658691,
}


def config_to_vec(config_dict: dict) -> np.ndarray:
    """Convert config dict to ordered weight vector. Missing features get small random init."""
    vec = np.zeros(N_PARAMS, dtype=np.float32)
    if "weights" in config_dict:
        flat = {"base_logit": config_dict["weights"]["base_logit"]}
        flat.update(config_dict["weights"].get("features", {}))
    else:
        flat = config_dict

    for i, name in enumerate(FEATURE_NAMES):
        if name in flat:
            vec[i] = flat[name]
        elif i > 0:
            vec[i] = np.random.randn() * 0.05
    return vec


def vec_to_config(vec, generation=0, metrics=None):
    v = vec if isinstance(vec, np.ndarray) else cp.asnumpy(vec)
    return {
        "generation": generation, **(metrics or {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "weights": {"base_logit": float(v[0]),
                    "features": {FEATURE_NAMES[i]: float(v[i]) for i in range(1, N_PARAMS)}},
    }


np.random.seed(42)
CANONICAL_VEC = config_to_vec(V23_BEST_FEATURES)

PARAM_SIGNS = np.sign(CANONICAL_VEC).astype(np.float32)
PARAM_SIGNS[0] = 0.0
for i, name in enumerate(FEATURE_NAMES):
    if name not in V23_BEST_FEATURES:
        PARAM_SIGNS[i] = 0.0

# ============================================================================
# PARAM_SIGNS EXPLICIT OVERRIDES -- Fix known bad sign constraints
# ============================================================================
_IDX = {n: i for i, n in enumerate(FEATURE_NAMES)}

# BN1 FIX: safety_clean was locked NEGATIVE due to v23 encoding bug.
#          A clean safety profile should INCREASE approval probability.
#          Explicitly force +1 so optimizer can find the correct direction.
PARAM_SIGNS[_IDX["safety_clean"]] = +1.0

# BN2 FIX: has_priority_review was locked NEGATIVE because it mixed two
#          populations (NME = high approval signal, sNDA = routine supplement).
#          Unlock it (0 = no constraint) and let the new interaction terms
#          (priority_review_x_phase3 / x_phase2) carry the differentiated signal.
PARAM_SIGNS[_IDX["has_priority_review"]] = 0.0

# BN3: New features -- no constraint, let optimizer find directions freely.
PARAM_SIGNS[_IDX["ta_cns_phase2"]]          = 0.0
PARAM_SIGNS[_IDX["ta_cns_phase2b"]]         = 0.0
PARAM_SIGNS[_IDX["priority_review_x_phase3"]] = 0.0
PARAM_SIGNS[_IDX["priority_review_x_phase2"]] = 0.0



# ============================================================================
# NLP FEATURE ENGINEERING
# ============================================================================

_RE = {
    "met_primary":     re.compile(r"met\s+(?:its?\s+)?primary\s+endpoint|primary\s+endpoint\s+met|trial\s+met", re.I),
    "failure":         re.compile(r"fail|did\s+not\s+meet|missed|not\s+met|not\s+reach|negative\s+result", re.I),
    "stat_sig":        re.compile(r"statistic(?:ally)?\s+significant|p\s*[=<\u2264]\s*0\.\d", re.I),
    "strong_pos":      re.compile(r"robust|compelling|impressive|exceptional|highly\s+significant|strong\s+efficac|transformative|substantial\s+improvement", re.I),
    "dose_response":   re.compile(r"dose.?respon|dose.?depend|higher\s+dose", re.I),
    "safety_signal":   re.compile(r"safety\s*(?:concern|signal|issue)|serious\s+adverse|hepatotoxic|cardiotoxic|death|fatal", re.I),
    "safety_clean":    re.compile(r"well.?tolerat|safety\s+(?:profile\s+)?(?:was\s+)?(?:favorable|consistent|manageable)|no\s+(?:new\s+)?(?:serious|safety)", re.I),
    "hard_endpoint":   re.compile(r"overall\s+survival|(?:^|\W)os(?:\W|$)|mortality|death\s+rate|all.?cause|mace|major\s+adverse\s+card", re.I),
    "surrogate":       re.compile(r"surrogate|biomarker|(?:^|\W)orr(?:\W|$)|(?:^|\W)pfs(?:\W|$)|(?:^|\W)efs(?:\W|$)|response\s+rate|tumor\s+(?:reduction|shrink)", re.I),
    "single_arm":      re.compile(r"single.?arm|uncontrolled", re.I),
    "discontinued":    re.compile(r"discontinu|terminat(?:ed|ion)", re.I),
    "interim":         re.compile(r"interim|preliminar", re.I),
    "pfs":             re.compile(r"progression.?free|(?:^|\W)pfs(?:\W|$)", re.I),
    "orr_cr":          re.compile(r"overall\s+response|(?:^|\W)orr(?:\W|$)|complete\s+respon|(?:^|\W)cr\s+(?:rate|of)", re.I),
    "placebo":         re.compile(r"placebo", re.I),
    "combination":     re.compile(r"combination|combo|combin", re.I),
    "secondary_met":   re.compile(r"secondary\s+(?:endpoint|outcome)s?\s+(?:were\s+)?met|met\s+(?:key\s+)?secondary|all\s+secondary", re.I),
    "mixed":           re.compile(r"mixed|inconsistent|one\s+endpoint\s+not|secondary\s+not\s+met", re.I),
    "breakthrough":    re.compile(r"breakthrough|btd", re.I),
    "orphan":          re.compile(r"orphan\s+(?:drug|design)", re.I),
    "fast_track":      re.compile(r"fast\s+track", re.I),
    "priority_review": re.compile(r"priority\s+review", re.I),
    "gene_therapy":    re.compile(r"gene\s*therap|aav|crispr|base\s*edit|lentivir", re.I),
    "psychedelic":     re.compile(r"psilocybin|mdma|lsd|ketamine|psychedel|5-meo", re.I),
    "pval_tiny":       re.compile(r"p\s*[=<\u2264]\s*0\.000[1-9]|p\s*[<\u2264]\s*\.0001", re.I),
    "pval_small":      re.compile(r"p\s*[=<\u2264]\s*0\.00[1-9]|p\s*[<\u2264]\s*\.001", re.I),
    "pval_med":        re.compile(r"p\s*[=<\u2264]\s*0\.0[0-4]\d|p\s*[<\u2264]\s*\.05", re.I),
}

_TA = {
    "ta_ONCOLOGY":       re.compile(r"cancer|tumor|tumour|lymphoma|leukemia|leukaemia|melanoma|carcinoma|myeloma|sarcoma|glioma|glioblastoma|mesothelioma|oncolog|nsclc|solid\s+tumor|hepatocellular|cholangiocarcinoma|neuroblastoma|renal\s+cell|bladder|prostate\s+(?!hyper)|breast(?!\s*feed)|ovarian|pancreatic|colorectal|gastric|esophag|thymoma|squamous|basal\s+cell", re.I),
    "ta_CNS":            re.compile(r"alzheimer|parkinson|epilep|schizophren|depression|depressive|bipolar|multiple\s+sclerosis|(?:^|\W)als(?:\W|$)|amyotrophic|huntington|migraine|neuropath|dementia|seizure|psychi|anxiety|ptsd|adhd|narcolep|stroke", re.I),
    "ta_RARE":           re.compile(r"duchenne|sma|spinal\s+muscular|huntington|sickle\s+cell|cystic\s+fibrosis|hemophilia|fabry|gaucher|pompe|achondroplasia|mps|mucopolysaccharid|rare|orphan|lysosom|ataxia|dystrophy|niemann|thalassemia", re.I),
    "ta_PAIN":           re.compile(r"\bpain\b|fibromyalg|analges|nocicepti", re.I),
    "ta_IMMUNOLOGY":     re.compile(r"lupus|rheumatoid|crohn|colitis|psoria|atopic|asthma|eczema|inflam|autoimmun|immunolog|ibd|gvhd|graft|dermati|ankylos|vasculit", re.I),
    "ta_RESPIRATORY":    re.compile(r"asthma|copd|pulmonary|lung\s+(?!cancer)|respiratory|idiopathic\s+pulm|ipf|bronchi", re.I),
    "ta_CARDIOVASCULAR": re.compile(r"heart\s+fail|cardiovascul|cardiac|atrial|hypertens|atheroscl|thrombos|angina|myocardial|cardiomyopath|arrhythm|aortic", re.I),
    "ta_METABOLIC":      re.compile(r"diabet|obes|metabol|nash|mash|steatohepatitis|cholesterol|lipid|glycem|hba1c|weight\s+(?:loss|manage)", re.I),
}

LARGE_CAP_NAMES = {"merck", "astrazeneca", "bristol-myers", "pfizer", "roche", "eli lilly",
                   "abbvie", "novartis", "johnson & johnson", "gsk", "gilead", "amgen",
                   "takeda", "genmab", "regeneron", "sanofi", "astellas", "bayer"}

COMPETITIVE_INDICATIONS = {"non-small cell lung cancer", "nsclc", "acute myeloid leukemia",
                           "aml", "major depressive disorder", "mdd", "alzheimer",
                           "chronic pain", "amyotrophic lateral sclerosis", "als"}


def engineer_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    N = len(df)
    X = np.zeros((N, N_PARAMS), dtype=np.float32)
    X[:, 0] = 1.0
    idx = {n: i for i, n in enumerate(FEATURE_NAMES)}

    text  = df["Catalyst"].fillna("").str.lower().values
    stage = df["Stage"].fillna("").values
    indic = df["Indication"].fillna("").str.lower().values
    drug  = df["Drug"].fillna("").str.lower().values
    name  = df["Name"].fillna("").str.lower().values
    year  = df["year"].fillna(2023).astype(int).values
    outcome = (df["outcome"].str.lower() == "positive").astype(np.float32).values

    for row in range(N):
        t, s, ind, d, nm, yr = text[row], stage[row], indic[row], drug[row], name[row], year[row]
        sl = s.lower().strip()

        # Phase
        if sl == "phase 3":              X[row, idx["phase_PHASE3"]] = 1.0
        elif sl in ("phase 2","phase 2a"): X[row, idx["phase_PHASE2"]] = 1.0
        elif sl == "phase 2b":           X[row, idx["phase_PHASE2B"]] = 1.0
        elif sl in ("phase 1","phase 1a","phase 1b"): X[row, idx["phase_PHASE1"]] = 1.0
        elif sl == "phase 1/2":          X[row, idx["phase_PHASE1_2"]] = 1.0

        # Text signals
        if _RE["met_primary"].search(t):   X[row, idx["primary_endpoint_met"]] = 1.0
        if _RE["failure"].search(t):       X[row, idx["failure_signal"]] = 1.0
        if _RE["strong_pos"].search(t) or _RE["stat_sig"].search(t): X[row, idx["strong_positive"]] = 1.0
        if _RE["dose_response"].search(t): X[row, idx["dose_response"]] = 1.0
        if _RE["safety_signal"].search(t): X[row, idx["safety_signal"]] = 1.0
        if _RE["safety_clean"].search(t):  X[row, idx["safety_clean"]] = 1.0
        if _RE["hard_endpoint"].search(t): X[row, idx["is_hard_endpoint"]] = 1.0
        if _RE["surrogate"].search(t):     X[row, idx["has_surrogate"]] = 1.0
        if _RE["single_arm"].search(t):    X[row, idx["is_single_arm"]] = 1.0
        if _RE["discontinued"].search(t):  X[row, idx["is_discontinued"]] = 1.0
        if _RE["interim"].search(t):       X[row, idx["is_interim"]] = 1.0
        if _RE["pfs"].search(t):           X[row, idx["has_pfs"]] = 1.0
        if _RE["orr_cr"].search(t):        X[row, idx["has_orr_cr"]] = 1.0
        if _RE["placebo"].search(t):       X[row, idx["is_placebo_controlled"]] = 1.0
        if _RE["combination"].search(t):   X[row, idx["is_combination"]] = 1.0
        if _RE["secondary_met"].search(t): X[row, idx["has_secondary_met"]] = 1.0
        if _RE["mixed"].search(t):
            X[row, idx["failure_signal"]] = max(X[row, idx["failure_signal"]], 0.5)

        # Sentiment score
        sent = 0.0
        if _RE["met_primary"].search(t):   sent += 0.4
        if _RE["stat_sig"].search(t):      sent += 0.3
        if _RE["strong_pos"].search(t):    sent += 0.3
        if _RE["safety_clean"].search(t):  sent += 0.1
        if _RE["orr_cr"].search(t):        sent += 0.2
        if _RE["pfs"].search(t):           sent += 0.15
        if _RE["secondary_met"].search(t): sent += 0.1
        if _RE["failure"].search(t):       sent -= 0.6
        if _RE["safety_signal"].search(t): sent -= 0.3
        if _RE["discontinued"].search(t):  sent -= 0.8
        if _RE["mixed"].search(t):         sent -= 0.2
        X[row, idx["sentiment_score"]] = np.clip(sent, -1.0, 1.0)

        # P-value buckets
        if _RE["pval_tiny"].search(t):     X[row, idx["p23_p2_bucket_lt_0001"]] = 1.0
        elif _RE["pval_small"].search(t):  X[row, idx["p23_p2_bucket_0001_001"]] = 1.0
        elif _RE["pval_med"].search(t):    X[row, idx["p23_p2_bucket_001_005"]] = 1.0

        # Designations
        if _RE["breakthrough"].search(t):    X[row, idx["has_breakthrough"]] = 1.0
        if _RE["orphan"].search(t):          X[row, idx["has_orphan"]] = 1.0
        if _RE["fast_track"].search(t):      X[row, idx["has_fast_track"]] = 1.0
        if _RE["priority_review"].search(t): X[row, idx["has_priority_review"]] = 1.0

        # Drug modality
        if _RE["gene_therapy"].search(d) or _RE["gene_therapy"].search(t): X[row, idx["is_gene_therapy"]] = 1.0
        if _RE["psychedelic"].search(d) or _RE["psychedelic"].search(t):   X[row, idx["is_psychedelic"]] = 1.0
        if re.search(r"antibod|mab\b|-mab\b", d):                          X[row, idx["is_antibody"]] = 1.0

        # Therapeutic area
        for ta_name, ta_re in _TA.items():
            if ta_re.search(ind):
                X[row, idx[ta_name]] = 1.0

        # Competitive space
        if any(kw in ind for kw in COMPETITIVE_INDICATIONS): X[row, idx["is_competitive_space"]] = 1.0

        # Large cap
        if any(lc in nm for lc in LARGE_CAP_NAMES): X[row, idx["is_large_cap"]] = 1.0

        # Temporal
        if yr >= 2024: X[row, idx["is_hoeg_era"]] = 1.0
        if yr >= 2025: X[row, idx["accel_approval_2025"]] = 1.0

    # ppm_flag
    cc = df["Name"].value_counts()
    prolific = set(cc[cc >= 10].index)
    for row in range(N):
        if df.iloc[row]["Name"] in prolific:
            X[row, idx["ppm_flag"]] = 1.0

    # Interaction terms
    p3 = X[:, idx["phase_PHASE3"]]
    p2 = X[:, idx["phase_PHASE2"]]
    X[:, idx["rct_x_phase3"]]          = X[:, idx["is_placebo_controlled"]] * p3
    X[:, idx["oncology_x_phase3"]]     = X[:, idx["ta_ONCOLOGY"]] * p3
    X[:, idx["ta_oncology_phase3"]]    = X[:, idx["ta_ONCOLOGY"]] * p3
    X[:, idx["ta_cns_phase3"]]         = X[:, idx["ta_CNS"]] * p3
    X[:, idx["ta_rare_phase3"]]        = X[:, idx["ta_RARE"]] * p3
    X[:, idx["ta_immunology_phase3"]]  = X[:, idx["ta_IMMUNOLOGY"]] * p3
    X[:, idx["gene_therapy_x_phase3"]] = X[:, idx["is_gene_therapy"]] * p3
    X[:, idx["failure_x_phase3"]]      = X[:, idx["failure_signal"]] * p3
    X[:, idx["safety_x_hoeg"]]         = X[:, idx["safety_signal"]] * X[:, idx["is_hoeg_era"]]
    X[:, idx["ppm_x_hoeg"]]            = X[:, idx["ppm_flag"]] * X[:, idx["is_hoeg_era"]]
    X[:, idx["rare_x_positive"]]       = X[:, idx["ta_RARE"]] * X[:, idx["strong_positive"]]
    X[:, idx["single_arm_2025"]]       = X[:, idx["is_single_arm"]] * X[:, idx["accel_approval_2025"]]
    X[:, idx["discontinued_x_phase3"]] = X[:, idx["is_discontinued"]] * p3
    X[:, idx["orr_x_oncology"]]        = X[:, idx["has_orr_cr"]] * X[:, idx["ta_ONCOLOGY"]]
    X[:, idx["large_cap_x_phase3"]]    = X[:, idx["is_large_cap"]] * p3
    X[:, idx["interim_x_phase2"]]      = X[:, idx["is_interim"]] * p2

    # v25 BN2: Priority review split by phase (NME proxy = Phase3, supplemental proxy = Phase2)
    X[:, idx["priority_review_x_phase3"]] = X[:, idx["has_priority_review"]] * p3
    X[:, idx["priority_review_x_phase2"]] = X[:, idx["has_priority_review"]] * p2

    # v25 BN3: CNS ? Phase2 -- captures 38.1% P2 success rate (worst TA)
    p2b = X[:, idx["phase_PHASE2B"]]
    X[:, idx["ta_cns_phase2"]]  = X[:, idx["ta_CNS"]] * p2
    X[:, idx["ta_cns_phase2b"]] = X[:, idx["ta_CNS"]] * p2b

    return X, outcome


# ============================================================================
# DATA LOADING
# ============================================================================

def load_dataset():
    data_path = None
    for c in [DATA_FILE, f"data/{DATA_FILE}", os.path.expanduser(f"~/{DATA_FILE}")]:
        if os.path.exists(c):
            data_path = c; break
    if not data_path:
        sys.exit(f"[FATAL] Cannot find {DATA_FILE}")

    print(f"[DATA] Loading: {data_path}")
    df = pd.read_csv(data_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    print(f"[DATA] {len(df)} events | Pos rate: {(df['outcome']=='positive').mean():.3f}")

    print(f"[DATA] Engineering {N_PARAMS} features...")
    X, y = engineer_features(df)

    # Diagnostics
    for i, nm in enumerate(FEATURE_NAMES[1:], 1):
        nz = (X[:, i] != 0).sum()
        if nz > 0:
            pr = y[X[:, i] != 0].mean()
            print(f"  {nm:30s}: {nz:5d} nonzero ({pr:.0%} pos)")

    N = len(df)
    n_tr = int(N * TRAIN_PCT); n_va = int(N * VAL_PCT)
    X_tr, y_tr = X[:n_tr], y[:n_tr]
    X_va, y_va = X[n_tr:n_tr+n_va], y[n_tr:n_tr+n_va]
    X_te, y_te = X[n_tr+n_va:], y[n_tr+n_va:]
    print(f"[DATA] Train: {len(y_tr)} ({y_tr.mean():.3f}) | Val: {len(y_va)} ({y_va.mean():.3f}) | Test: {len(y_te)} ({y_te.mean():.3f})")
    return X_tr, y_tr, X_va, y_va, X_te, y_te


# ============================================================================
# VRAM MANAGER
# ============================================================================

class VRAMManager:
    def __init__(self):
        self.batch_size = 1000; self.oom_count = 0
    def available_mb(self):
        if not GPU_AVAILABLE: return 8192.0
        try: f, _ = cp.cuda.Device(0).mem_info; return f / (1024**2)
        except: return 2048.0
    def optimal_batch(self, n_params, n_samples):
        usable = max(self.available_mb() * VRAM_USAGE_TARGET - VRAM_SAFETY_FLOOR_MB, 256)
        per = (n_params*4) + (n_samples*4*2) + 200
        t = int((usable*1024*1024)/per)
        t = max(100, min(t, 10_000_000))
        t = min(t, int(self.batch_size*1.2)) if t > self.batch_size else t
        self.batch_size = t; return t
    def handle_oom(self):
        self.oom_count += 1; self.batch_size = max(100, int(self.batch_size*0.5))
        if GPU_AVAILABLE: cp.get_default_memory_pool().free_all_blocks(); cp.get_default_pinned_memory_pool().free_all_blocks()
        gc.collect(); print(f"  [OOM #{self.oom_count}] Batch -> {self.batch_size:,}"); return self.batch_size
    def report(self):
        if GPU_AVAILABLE:
            f,t = cp.cuda.Device(0).mem_info; print(f"  [VRAM] {(t-f)/(1024**3):.1f}/{t/(1024**3):.1f} GB | Batch: {self.batch_size:,}")


# ============================================================================
# CUDA KERNELS
# ============================================================================

if GPU_AVAILABLE:
    SIGMOID_BRIER_KERNEL = cp.RawKernel(r'''
    extern "C" __global__ void sigmoid_brier_batch(
        const float* __restrict__ configs, const float* __restrict__ features,
        const float* __restrict__ labels, float* __restrict__ brier_out,
        float* __restrict__ logloss_out, float* __restrict__ acc_out,
        const int B, const int N, const int P) {
        int b = blockIdx.x * blockDim.x + threadIdx.x;
        if (b >= B) return;
        float bs=0, ll=0; int cor=0;
        for (int n=0; n<N; n++) {
            float logit=0;
            for (int p=0; p<P; p++) logit += configs[b*P+p] * features[n*P+p];
            float pred = 1.0f/(1.0f+expf(-logit));
            pred = fminf(fmaxf(pred,1e-7f),1.0f-1e-7f);
            float y=labels[n], d=pred-y;
            bs += d*d;
            ll -= y*logf(pred)+(1.0f-y)*logf(1.0f-pred);
            if ((pred>=0.5f)==(y>=0.5f)) cor++;
        }
        brier_out[b]=bs/(float)N; logloss_out[b]=ll/(float)N; acc_out[b]=(float)cor/(float)N;
    }''', 'sigmoid_brier_batch')

    PREDS_KERNEL = cp.RawKernel(r'''
    extern "C" __global__ void compute_preds(
        const float* __restrict__ configs, const float* __restrict__ features,
        float* __restrict__ preds_out, const int B, const int N, const int P) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int b=idx/N, n=idx%N;
        if (b>=B||n>=N) return;
        float logit=0;
        for (int p=0; p<P; p++) logit += configs[b*P+p] * features[n*P+p];
        preds_out[b*N+n] = 1.0f/(1.0f+expf(-logit));
    }''', 'compute_preds')


# ============================================================================
# EVAL ENGINE
# ============================================================================

class EvalEngine:
    def __init__(self, X_tr, y_tr, X_va, y_va, X_te=None, y_te=None):
        xp = cp if GPU_AVAILABLE else np
        self.P = X_tr.shape[1]; self.splits = {}
        for nm, X, y in [("train",X_tr,y_tr),("val",X_va,y_va),("test",X_te,y_te)]:
            if X is not None:
                Xg = xp.asarray(X, dtype=xp.float32); yg = xp.asarray(y, dtype=xp.float32)
                self.splits[nm] = (Xg, yg, len(y), xp.where(yg>0.5)[0], xp.where(yg<=0.5)[0])

    def _get(self, s): return self.splits[s]

    def eval_batch(self, configs, split="train"):
        X, y, N, _, _ = self._get(split)
        xp = cp if (GPU_AVAILABLE and isinstance(configs, cp.ndarray)) else np
        B, P = configs.shape[0], self.P
        if GPU_AVAILABLE and isinstance(configs, cp.ndarray):
            br = cp.empty(B,dtype=cp.float32); ll = cp.empty(B,dtype=cp.float32); ac = cp.empty(B,dtype=cp.float32)
            SIGMOID_BRIER_KERNEL(((B+255)//256,),(256,),(configs,X,y,br,ll,ac,B,N,P))
            return br, ll, ac
        logits = configs @ X.T
        preds = 1/(1+np.exp(-np.clip(logits,-30,30))); preds = np.clip(preds,1e-7,1-1e-7)
        return np.mean((preds-y)**2,axis=1), -np.mean(y*np.log(preds)+(1-y)*np.log(1-preds),axis=1), np.mean((preds>=0.5)==(y>=0.5),axis=1).astype(np.float32)

    def auc_batch(self, configs, split="train"):
        X, y, N, pi, ni = self._get(split)
        np_, nn_ = len(pi), len(ni)
        xp = cp if (GPU_AVAILABLE and isinstance(configs, cp.ndarray)) else np
        if np_==0 or nn_==0: return xp.full(configs.shape[0],0.5,dtype=xp.float32)
        if GPU_AVAILABLE and isinstance(configs, cp.ndarray):
            B = configs.shape[0]; pa = cp.empty((B,N),dtype=cp.float32)
            tot = B*N; PREDS_KERNEL(((tot+255)//256,),(256,),(configs,X,pa,B,N,self.P))
        else:
            pa = 1/(1+np.exp(-np.clip(configs @ X.T,-30,30)))
        pp, pn = pa[:,pi], pa[:,ni]
        if np_*nn_ <= 50000:
            c = (pp[:,:,None]>pn[:,None,:]).astype(xp.float32)
            t = (pp[:,:,None]==pn[:,None,:]).astype(xp.float32)
            return xp.mean(c+0.5*t, axis=(1,2))
        ns = min(5000, np_*nn_)
        si = xp.random.randint(0,np_,size=ns); sj = xp.random.randint(0,nn_,size=ns)
        return xp.mean((pp[:,si]>pn[:,sj]).astype(xp.float32)+0.5*(pp[:,si]==pn[:,sj]).astype(xp.float32),axis=1)

    def ece_batch(self, configs, split="train", nb=10):
        X, y, N, _, _ = self._get(split)
        xp = cp if (GPU_AVAILABLE and isinstance(configs, cp.ndarray)) else np
        preds = 1/(1+xp.exp(-xp.clip(configs @ X.T,-30,30)))
        ece = xp.zeros(configs.shape[0],dtype=xp.float32)
        edges = xp.linspace(0,1,nb+1)
        for i in range(nb):
            m = (preds>=edges[i])&(preds<edges[i+1])
            c = xp.sum(m,axis=1).astype(xp.float32); sc = xp.maximum(c,1.0)
            ece += (c/N)*xp.abs(xp.sum(preds*m,axis=1)/sc - xp.sum(y[None,:]*m,axis=1)/sc)
        return ece

    def fitness(self, configs, split="train", return_parts=False):
        xp = cp if (GPU_AVAILABLE and isinstance(configs, cp.ndarray)) else np
        br, ll, ac = self.eval_batch(configs, split)
        auc = self.auc_batch(configs, split)
        ece = self.ece_batch(configs, split)
        l2 = L2_LAMBDA * xp.sum(configs**2, axis=1)
        f = FITNESS_AUC_WEIGHT*auc + FITNESS_BRIER_WEIGHT*(1-br) + FITNESS_ACC_WEIGHT*ac + FITNESS_CAL_WEIGHT*(1-ece) - l2
        return (f, auc, br, ac, ece, ll) if return_parts else f

    def composite(self, configs):
        return COMPOSITE_ALPHA*self.fitness(configs,"train") + (1-COMPOSITE_ALPHA)*self.fitness(configs,"val")


# ============================================================================
# SIGN ENFORCEMENT (CuPy-safe)
# ============================================================================

def enforce_signs(pop):
    xp = cp if (GPU_AVAILABLE and isinstance(pop, cp.ndarray)) else np
    signs = xp.asarray(PARAM_SIGNS, dtype=xp.float32)
    ab = xp.abs(pop)
    pop = xp.where((signs > 0)[None,:], ab, pop)
    pop = xp.where((signs < 0)[None,:], -ab, pop)
    return pop


# ============================================================================
# ISLANDS
# ============================================================================

class CMAESIsland:
    def __init__(self, seed, n, pop=None):
        self.n, self.name = n, "CMA-ES"
        self.lam = pop or (CMAES_POPULATION_FACTOR*n); self.mu = self.lam//2
        xp = self.xp = cp if GPU_AVAILABLE else np
        self.mean = xp.asarray(seed.copy(), dtype=xp.float32)
        self.sigma = CMAES_SIGMA0
        self.C = xp.eye(n, dtype=xp.float32)
        self.pc = xp.zeros(n, dtype=xp.float32); self.ps = xp.zeros(n, dtype=xp.float32)
        rw = xp.log(xp.float32(self.mu+0.5)) - xp.log(xp.arange(1,self.mu+1,dtype=xp.float32))
        self.weights = rw/xp.sum(rw)
        self.mueff = 1.0/float(xp.sum(self.weights**2))
        self.cc = (4+self.mueff/n)/(n+4+2*self.mueff/n)
        self.cs = (self.mueff+2)/(n+self.mueff+5)
        self.c1 = 2/((n+1.3)**2+self.mueff)
        self.cmu = min(1-self.c1, 2*(self.mueff-2+1/self.mueff)/((n+2)**2+self.mueff))
        self.damps = 1+2*max(0,math.sqrt((self.mueff-1)/(n+1))-1)+self.cs
        self.chiN = math.sqrt(n)*(1-1/(4*n)+1/(21*n**2))
        self.gen = 0

    def sample(self, pop_size=None):
        xp = self.xp; lam = pop_size or self.lam
        try:
            ev, evec = xp.linalg.eigh(self.C); ev = xp.maximum(ev,1e-10); D = xp.sqrt(ev)
        except: D = xp.ones(self.n,dtype=xp.float32); evec = xp.eye(self.n,dtype=xp.float32)
        return self.mean[None,:] + self.sigma * (xp.random.randn(lam,self.n).astype(xp.float32)*D[None,:]) @ evec.T

    def update(self, pop, fitvals):
        xp = self.xp; si = xp.argsort(-fitvals); sel = pop[si[:self.mu]]
        old = self.mean.copy(); self.mean = xp.sum(self.weights[:,None]*sel, axis=0)
        try:
            ev, evec = xp.linalg.eigh(self.C); ev = xp.maximum(ev,1e-10)
            isC = evec @ xp.diag(1/xp.sqrt(ev)) @ evec.T
        except: isC = xp.eye(self.n,dtype=xp.float32)
        self.ps = (1-self.cs)*self.ps + math.sqrt(self.cs*(2-self.cs)*self.mueff)*(isC@(self.mean-old))/self.sigma
        hsig = float(xp.linalg.norm(self.ps))/math.sqrt(1-(1-self.cs)**(2*(self.gen+1)))/self.chiN < 1.4+2/(self.n+1)
        self.pc = (1-self.cc)*self.pc + hsig*math.sqrt(self.cc*(2-self.cc)*self.mueff)*(self.mean-old)/self.sigma
        art = (sel-old[None,:])/self.sigma
        self.C = (1-self.c1-self.cmu)*self.C + self.c1*(self.pc[:,None]@self.pc[None,:]+(1-hsig)*self.cc*(2-self.cc)*self.C) + self.cmu*(art.T@xp.diag(self.weights)@art)
        self.C = (self.C+self.C.T)/2
        self.sigma *= math.exp((self.cs/self.damps)*(float(xp.linalg.norm(self.ps))/self.chiN-1))
        self.sigma = max(0.001, min(self.sigma, 2.0)); self.gen += 1


class DEIsland:
    def __init__(self, seed, n, pop_size, strategy="rand1"):
        xp = cp if GPU_AVAILABLE else np
        self.xp, self.n, self.NP, self.strategy, self.name = xp, n, pop_size, strategy, f"DE/{strategy}"
        sg = xp.asarray(seed, dtype=xp.float32)
        self.pop = sg[None,:] + xp.random.randn(pop_size,n).astype(xp.float32)*0.1*xp.abs(sg[None,:])
        self.pop[0] = sg; self.fit = xp.full(pop_size,-999.0,dtype=xp.float32); self.best_idx = 0
        self.F = xp.random.uniform(DE_F_RANGE[0],DE_F_RANGE[1],size=pop_size).astype(xp.float32)
        self.CR = xp.random.uniform(DE_CR_RANGE[0],DE_CR_RANGE[1],size=pop_size).astype(xp.float32)

    def trial(self):
        xp, NP, D = self.xp, self.NP, self.n
        r1,r2,r3 = xp.random.randint(0,NP,size=NP), xp.random.randint(0,NP,size=NP), xp.random.randint(0,NP,size=NP)
        if self.strategy=="rand1":
            mut = self.pop[r1]+self.F[:,None]*(self.pop[r2]-self.pop[r3])
        else:
            r4 = xp.random.randint(0,NP,size=NP)
            mut = self.pop[self.best_idx][None,:]+self.F[:,None]*(self.pop[r1]-self.pop[r2])+self.F[:,None]*(self.pop[r3]-self.pop[r4])
        mask = xp.random.rand(NP,D).astype(xp.float32) < self.CR[:,None]
        mask[xp.arange(NP), xp.random.randint(0,D,size=NP)] = True
        return xp.where(mask, mut, self.pop)

    def select(self, trial_pop, trial_fit):
        xp = self.xp; b = trial_fit >= self.fit
        self.pop = xp.where(b[:,None], trial_pop, self.pop)
        self.fit = xp.where(b, trial_fit, self.fit)
        self.best_idx = int(xp.argmax(self.fit))
        w = ~b; nw = int(xp.sum(w))
        if nw > 0:
            self.F[w] = xp.random.uniform(DE_F_RANGE[0],DE_F_RANGE[1],size=nw).astype(xp.float32)
            self.CR[w] = xp.random.uniform(DE_CR_RANGE[0],DE_CR_RANGE[1],size=nw).astype(xp.float32)
        return int(xp.sum(b))


class PerturbIsland:
    def __init__(self, seed, n, pop_size):
        xp = cp if GPU_AVAILABLE else np
        self.xp, self.n, self.NP, self.name = xp, n, pop_size, "Perturbation"
        self.best = xp.asarray(seed, dtype=xp.float32)
        self.signs = xp.asarray(PARAM_SIGNS, dtype=xp.float32)
        self.gen = 0

    def generate(self):
        xp = self.xp
        cyc = (self.gen%PERTURB_RADIUS_CYCLE)/PERTURB_RADIUS_CYCLE
        r = PERTURB_RADIUS_END+0.5*(PERTURB_RADIUS_START-PERTURB_RADIUS_END)*(1+math.cos(math.pi*cyc))
        fac = xp.random.uniform(1-r,1+r,size=(self.NP,self.n)).astype(xp.float32)
        pop = xp.abs(self.best)[None,:]*fac
        has_sign = (self.signs != 0).astype(xp.float32)
        signed = xp.abs(pop)*self.signs[None,:]
        pop = xp.where(has_sign[None,:] > 0.5, signed, pop)
        pop[:,0] = self.best[0]+xp.random.randn(self.NP).astype(xp.float32)*r*0.5
        return pop


# ============================================================================
# HALL OF FAME
# ============================================================================

class HallOfFame:
    def __init__(self, mx=HOF_SIZE):
        self.vecs, self.fits, self.meta, self.mx = [],[],[],mx
    def try_add(self, vec, fit, meta=None):
        v = vec if isinstance(vec,np.ndarray) else cp.asnumpy(vec)
        for i,ev in enumerate(self.vecs):
            if np.linalg.norm(v-ev)/(np.linalg.norm(ev)+1e-8) < HOF_DIVERSITY_THRESH:
                if fit > self.fits[i]: self.vecs[i],self.fits[i],self.meta[i]=v.copy(),fit,meta
                return
        if len(self.vecs)<self.mx: self.vecs.append(v.copy()); self.fits.append(fit); self.meta.append(meta)
        else:
            wi=int(np.argmin(self.fits))
            if fit>self.fits[wi]: self.vecs[wi],self.fits[wi],self.meta[wi]=v.copy(),fit,meta
    def ensemble(self, engine, split="val", k=10):
        if not self.vecs: return None
        xp = cp if GPU_AVAILABLE else np; k=min(k,len(self.vecs))
        si=np.argsort(self.fits)[::-1][:k]
        batch=xp.asarray(np.stack([self.vecs[i] for i in si]),dtype=xp.float32)
        w=np.array([self.fits[i] for i in si]); w=w/w.sum(); wg=xp.asarray(w,dtype=xp.float32)
        X,y,N,_,_=engine._get(split)
        preds=1/(1+xp.exp(-xp.clip(batch@X.T,-30,30)))
        ep=xp.sum(wg[:,None]*preds,axis=0)
        return {"brier":float(xp.mean((ep-y)**2)),"accuracy":float(xp.mean((ep>=0.5).astype(xp.float32)==y)),"k":k}
    def export(self):
        return {"size":len(self.vecs),"best_fitness":max(self.fits) if self.fits else 0,
                "configs":[{"fitness":self.fits[i],"weights":self.vecs[i].tolist()} for i in range(len(self.vecs))]}


# ============================================================================
# PERSISTENCE
# ============================================================================

def save_best(vec, gen, engine, hof):
    xp = cp if GPU_AVAILABLE else np
    v = vec if isinstance(vec,np.ndarray) else cp.asnumpy(vec)
    vg = xp.asarray(v,dtype=xp.float32).reshape(1,-1)
    metrics = {}
    for sp in ["train","val","test"]:
        try:
            f,a,b,ac,e,_ = engine.fitness(vg,sp,return_parts=True)
            metrics.update({f"{sp}_fitness":float(f[0]),f"{sp}_auc":float(a[0]),f"{sp}_brier":float(b[0]),f"{sp}_accuracy":float(ac[0]),f"{sp}_ece":float(e[0])})
        except: pass
    comp = COMPOSITE_ALPHA*metrics.get("train_fitness",0)+(1-COMPOSITE_ALPHA)*metrics.get("val_fitness",0)
    ens = hof.ensemble(engine,"val")
    if ens: metrics["ensemble_val_brier"]=ens["brier"]; metrics["ensemble_val_accuracy"]=ens["accuracy"]
    cfg = {"generation":gen,"auc":metrics.get("val_auc",0),"brier":metrics.get("val_brier",0),
           "accuracy":metrics.get("val_accuracy",0),"fitness":comp,
           "timestamp":datetime.now(timezone.utc).isoformat(),"all_metrics":metrics,
           "weights":{"base_logit":float(v[0]),"features":{FEATURE_NAMES[i]:float(v[i]) for i in range(1,N_PARAMS)}}}
    tmp=OUTPUT_BEST+".tmp"
    with open(tmp,"w") as f: json.dump(cfg,f,indent=2)
    os.replace(tmp, OUTPUT_BEST); return cfg

def log_history(gen, m):
    with open(OUTPUT_HISTORY,"a") as f: f.write(json.dumps({"gen":gen,"ts":datetime.now(timezone.utc).isoformat(),**m})+"\n")

def log_promotion(gen, m, island):
    hdr = not os.path.exists(OUTPUT_PROMOTION_LOG)
    with open(OUTPUT_PROMOTION_LOG,"a") as f:
        if hdr: f.write("ts,gen,island,composite,train_brier,val_brier,train_auc,val_auc\n")
        f.write(f"{datetime.now(timezone.utc).isoformat()},{gen},{island},{m.get('composite',0):.6f},{m.get('train_brier',0):.6f},{m.get('val_brier',0):.6f},{m.get('train_auc',0):.6f},{m.get('val_auc',0):.6f}\n")

def load_seed():
    # Try to load v25 best first (already has correct N_PARAMS)
    if os.path.exists(OUTPUT_BEST):
        try:
            d=json.load(open(OUTPUT_BEST)); v=config_to_vec(d)
            print(f"[SEED] Resuming v25: gen={d.get('generation',0)}, fit={d.get('fitness',0):.6f}"); return v, d.get("generation",0)
        except: pass
    # Fall back to v24 seed -- config_to_vec handles missing new features with small random init
    if os.path.exists(SEED_CONFIG):
        try:
            d=json.load(open(SEED_CONFIG)); v=config_to_vec(d)
            print(f"[SEED] v24 seed (gen {d.get('generation',0)}): fit={d.get('fitness',0):.6f}")
            print(f"[SEED] {N_PARAMS - len(d.get('weights',{}).get('features',{}))-1} new params initialized with small random noise")
            return v, 0
        except Exception as e: print(f"[SEED] v24 load failed: {e}")
    print("[SEED] Using hardcoded v23 canonical with v25 fixes applied")
    return CANONICAL_VEC.copy(), 0


# ============================================================================
# MAIN LOOP
# ============================================================================

def run():
    print(f"\n{'='*72}\n  GUNGNIR v25 -- PHASE READOUT OPTIMIZER\n  Features: {N_PARAMS} | GPU: {GPU_AVAILABLE}\n  v25 Fixes: BN1(safety_clean sign) + BN2(priority_review unlock) + BN3(cns_phase2)\n{'='*72}\n")

    X_tr, y_tr, X_va, y_va, X_te, y_te = load_dataset()
    engine = EvalEngine(X_tr, y_tr, X_va, y_va, X_te, y_te)
    seed, start_gen = load_seed()

    xp = cp if GPU_AVAILABLE else np
    sg = xp.asarray(seed,dtype=xp.float32).reshape(1,-1)
    seed_comp = float(engine.composite(sg)[0])
    f,a,b,ac,e,_ = engine.fitness(sg,"val",return_parts=True)
    print(f"\n[SEED] Composite: {seed_comp:.6f} | Val AUC: {float(a[0]):.4f} Brier: {float(b[0]):.4f} Acc: {float(ac[0]):.4f}")

    vram = VRAMManager()
    n_samp = max(X_tr.shape[0], X_va.shape[0])
    ipop = max(vram.optimal_batch(N_PARAMS, n_samp)//N_ISLANDS, 50)
    print(f"[ISLANDS] Per-island pop: {ipop:,}")

    islands = [CMAESIsland(seed,N_PARAMS,pop=min(ipop,CMAES_POPULATION_FACTOR*N_PARAMS)),
               DEIsland(seed,N_PARAMS,ipop,"rand1"), DEIsland(seed,N_PARAMS,ipop,"best2"),
               PerturbIsland(seed,N_PARAMS,ipop)]
    for i in islands: print(f"  * {i.name}")

    hof = HallOfFame(HOF_SIZE); hof.try_add(seed, seed_comp, {"gen":start_gen})
    best_comp, best_vec, best_gen = seed_comp, seed.copy(), start_gen
    total_cfgs, total_impr, stale = 0, 0, 0
    isl_impr = {i.name:0 for i in islands}; t0 = time.time()

    stop = [False]
    def _sig(s,f): print("\n[SHUTDOWN]..."); stop[0]=True
    signal.signal(signal.SIGINT, _sig); signal.signal(signal.SIGTERM, _sig)
    print(f"\n{'='*72}\n  RUNNING -- Ctrl+C to stop\n{'='*72}\n")

    gen = start_gen
    while not stop[0]:
        gen += 1
        if gen%VRAM_POLL_INTERVAL==0: ipop=max(vram.optimal_batch(N_PARAMS,n_samp)//N_ISLANDS,50)

        for island in islands:
            try:
                if isinstance(island, CMAESIsland):
                    pop=enforce_signs(island.sample(ipop)); fit=engine.composite(pop)
                    island.update(pop,fit); bi=int(xp.argmax(fit)); bf=float(fit[bi]); bv=pop[bi]; total_cfgs+=len(pop)
                elif isinstance(island, DEIsland):
                    tr=enforce_signs(island.trial()); fit=engine.composite(tr); island.select(tr,fit)
                    bf=float(xp.max(island.fit)); bv=island.pop[island.best_idx]; total_cfgs+=island.NP
                elif isinstance(island, PerturbIsland):
                    pop=enforce_signs(island.generate()); fit=engine.composite(pop)
                    bi=int(xp.argmax(fit)); bf=float(fit[bi]); bv=pop[bi]
                    if bf>best_comp: island.best=bv.copy()
                    island.gen+=1; total_cfgs+=island.NP

                if bf > best_comp:
                    imp=bf-best_comp; best_comp=bf
                    best_vec = bv if isinstance(bv,np.ndarray) else cp.asnumpy(bv)
                    best_gen=gen; total_impr+=1; stale=0
                    isl_impr[island.name]=isl_impr.get(island.name,0)+1
                    hof.try_add(best_vec, best_comp, {"gen":gen,"island":island.name})
                    for o in islands:
                        if isinstance(o, PerturbIsland): o.best=xp.asarray(best_vec,dtype=xp.float32)
                    print(f"  \u2605 Gen {gen:6d} [{island.name:12s}] NEW BEST: {best_comp:.6f} (+{imp:.6f})")
                    log_promotion(gen, {"composite":best_comp}, island.name)
            except (cp.cuda.memory.OutOfMemoryError if GPU_AVAILABLE else MemoryError):
                ipop=vram.handle_oom()
            except Exception as ex:
                print(f"  [ERROR] {island.name}: {ex}")

        stale += 1

        if gen%MIGRATION_INTERVAL==0:
            bg = xp.asarray(best_vec, dtype=xp.float32)
            for island in islands:
                if isinstance(island,DEIsland):
                    wi=int(xp.argmin(island.fit)); island.pop[wi]=bg.copy(); island.fit[wi]=xp.float32(best_comp)
                elif isinstance(island,CMAESIsland): island.mean=0.9*island.mean+0.1*bg
                elif isinstance(island,PerturbIsland): island.best=bg.copy()

        if gen%WARM_RESTART_INTERVAL==0:
            wn=min(isl_impr,key=isl_impr.get)
            for isl in islands:
                if isl.name==wn:
                    if isinstance(isl,DEIsland):
                        sg2=xp.asarray(best_vec,dtype=xp.float32)
                        isl.pop=sg2[None,:]+xp.random.randn(isl.NP,N_PARAMS).astype(xp.float32)*0.15*xp.abs(sg2[None,:])
                        isl.pop=enforce_signs(isl.pop); isl.fit=xp.full(isl.NP,-999.0,dtype=xp.float32)
                    elif isinstance(isl,CMAESIsland):
                        isl.sigma=CMAES_SIGMA0; isl.C=xp.eye(N_PARAMS,dtype=xp.float32); isl.mean=xp.asarray(best_vec,dtype=xp.float32)
                    print(f"  [RESTART] {isl.name}"); break

        elapsed=time.time()-t0; cps=total_cfgs/max(elapsed,1)
        if gen%LOG_INTERVAL==0: log_history(gen, {"fitness":best_comp,"cfgs":total_cfgs,"cps":cps,"stale":stale})
        if gen%SAVE_INTERVAL==0:
            save_best(best_vec,gen,engine,hof)
            with open(OUTPUT_HALL_OF_FAME,"w") as f: json.dump(hof.export(),f,indent=2)
        if gen%10==0:
            print(f"  Gen {gen:6d} | Best: {best_comp:.6f} | Cfgs: {total_cfgs:>12,} | {cps:,.0f}/s | Stale: {stale} | Impr: {total_impr} | {elapsed/3600:.1f}h")
        if gen%100==0:
            vram.report()
            ens=hof.ensemble(engine,"val")
            if ens: print(f"  [ENSEMBLE] Val Brier: {ens['brier']:.6f} | Acc: {ens['accuracy']:.4f}")
            for nm,cnt in sorted(isl_impr.items(),key=lambda x:-x[1]): print(f"  [ISLAND] {nm}: {cnt}")

    print("\n[SHUTDOWN] Saving...")
    cfg=save_best(best_vec,gen,engine,hof)
    with open(OUTPUT_HALL_OF_FAME,"w") as f: json.dump(hof.export(),f,indent=2)
    elapsed=time.time()-t0
    print(f"\n{'='*72}\n  GUNGNIR v25 -- FINAL\n{'='*72}")
    print(f"  Gens: {gen:,} | Cfgs: {total_cfgs:,} | Impr: {total_impr} | {elapsed/3600:.2f}h | {cps:,.0f}/s")
    print(f"  BEST FITNESS: {best_comp:.6f} (gen {best_gen})")
    for k,v in cfg.get("all_metrics",{}).items(): print(f"    {k}: {v:.6f}")
    ens=hof.ensemble(engine,"test")
    if ens: print(f"  Ensemble Test: Brier={ens['brier']:.6f} Acc={ens['accuracy']:.4f}")
    print(f"{'='*72}\n  SK\u00C5L! \U0001FA93\u26A1\n{'='*72}\n")

if __name__=="__main__":
    print(f"[GUNGNIR v25] Python {sys.version.split()[0]} | NumPy {np.__version__}"+(f" | CuPy {cp.__version__}" if GPU_AVAILABLE else "")+f" | Params: {N_PARAMS}")
    print(f"[v25 FIXES] BN1: safety_clean={PARAM_SIGNS[_IDX['safety_clean']:_IDX['safety_clean']+1]} | BN2: priority_review={PARAM_SIGNS[_IDX['has_priority_review']:_IDX['has_priority_review']+1]} | BN3: cns_phase2 added")
    run()
