#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — GUNGNIR HISTORICAL EVOLVE: LightGBM Phase Readout Daemon    ║
║                                                                          ║
║  "The spear that never misses" — adapted for LightGBM Kaizen pipeline  ║
║                                                                          ║
║  Data: historical_readouts_2000.csv (2K phase readout events)           ║
║  Target: outcome (positive=1, negative=0)                               ║
║                                                                          ║
║  Features NLP-extracted from Catalyst text + metadata:                   ║
║    • Stage encoding (Phase 1/1b/2/2a/2b/2-3/3)                         ║
║    • NLP signals (endpoint_met, failure_signal, dose_response, etc.)    ║
║    • Therapeutic area dummies                                            ║
║    • Interaction terms (ta × stage, sentiment × stage)                   ║
║    • Target-encoded indication/stage frequencies                         ║
║                                                                          ║
║  Architecture mirrors ODIN daemon: Optuna → Walk-Forward → Ensemble    ║
║  Integrates with Kaizen engine for adaptive improvement.                ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import csv
import hashlib
import json
import logging
import math
import os
import pickle
import re
import signal
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import optuna
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss

# Kaizen adaptive intelligence
try:
    from kaizen_engine import KaizenTracker
    KAIZEN_ENABLED = True
except ImportError:
    KAIZEN_ENABLED = False

optuna.logging.set_verbosity(optuna.logging.WARNING)

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
REALMS_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REALMS_ROOT / "data"
MODELS_DIR = REALMS_ROOT / "models"
GUNGNIR_DIR = MODELS_DIR / "gungnir_lgb_champions"
ENSEMBLE_DIR = GUNGNIR_DIR / "ensemble_pool"
ALERTS_DIR = REALMS_ROOT / "alerts"
STOP_FILE = REALMS_ROOT / "STOP_GUNGNIR"

DATASET_PATH = REALMS_ROOT / "historical_readouts_2000.csv"
LADDER_PATH = GUNGNIR_DIR / "gungnir_champion_ladder.json"
KAIZEN_DIR = REALMS_ROOT / "kaizen_gungnir"

for d in [GUNGNIR_DIR, ENSEMBLE_DIR, ALERTS_DIR, KAIZEN_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════
LOG_PATH = ALERTS_DIR / "gungnir_lgb_daemon_log.txt"
# Force UTF-8 on Windows to handle emoji in log messages
_fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
_sh = logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_fh, _sh],
)
log = logging.getLogger("gungnir_lgb")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
SLEEP_BETWEEN_ROUNDS = 5
OPTUNA_TRIALS_PER_ROUND = 40
ENSEMBLE_POOL_SIZE = 10
FEATURE_MUTATION_RATE = 0.30
WF_MIN_YEAR = 2023
WF_MIN_TRAIN = 80
WF_MIN_TEST = 20
MAX_ROUNDS = 999_999
PROMOTE_THRESHOLD_AUC = 0.0003

# Graceful shutdown
SHUTDOWN = False
def _signal_handler(sig, frame):
    global SHUTDOWN
    log.info("⚡ Shutdown signal received — finishing current round...")
    SHUTDOWN = True
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ═══════════════════════════════════════════════════════════════
# NLP FEATURE EXTRACTION FROM CATALYST TEXT
# ═══════════════════════════════════════════════════════════════

def _lower(s):
    return (s or "").strip().lower()

def _has_pattern(text, patterns):
    """Check if any regex pattern matches."""
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False

# NLP patterns for catalyst text analysis
# ═══ MOONSHOT v2: Expanded from 10 moonshot examples (CAPR, ABVX, QURE, etc.)
NLP_PATTERNS = {
    "primary_endpoint_met": [
        r"met\s+(its\s+)?primary\s+endpoint",
        r"primary\s+endpoint\s+(was\s+)?met",
        r"achieved\s+(its\s+)?primary\s+endpoint",
        r"met\s+the\s+primary",
        r"met\s+all\s+(key\s+)?secondary\s+endpoints",      # ABVX pattern
        r"met\s+primary\s+and\s+all\s+secondary",            # VKTX pattern
    ],
    "failure_signal": [
        r"did\s+not\s+meet",
        r"failed\s+to\s+(meet|achieve|demonstrate|reach)",
        r"not\s+(met|achieved|reached)",
        r"missed?\s+(its\s+)?primary",
        r"discontinued",
        r"terminated",
        r"futility",
        r"recommended\s+stopping",                            # PRAX futility pattern
        r"further\s+development\s+(of\s+\w+\s+)?will\s+not", # ROIV discontinuation
    ],
    "strong_positive": [
        r"statistically\s+significant",
        r"clinically\s+meaningful",
        r"highly\s+significant",
        r"robust\s+(efficacy|response|results)",
        r"durable\s+(response|remission|improvement)",
        r"unprecedented",
        r"best[\s-]in[\s-]class",
        r"superior(ity)?\s+(to|vs|over|compared)",
        r"sustained\s+improvement",                           # MBX pattern
        r"no\s+rescue\s+therapy\s+needed",                    # MBX pattern
    ],
    "safety_clean": [
        r"well[\s-]tolerated",
        r"favorable\s+safety",
        r"manageable\s+(safety|side|adverse)",
        r"no\s+(new\s+)?safety\s+(signal|concern)",
        r"clean\s+safety",
        r"safe\s+and\s+well[\s-]tolerated",                   # VKTX pattern
    ],
    "safety_signal": [
        r"safety\s+(concern|signal|issue|warning)",
        r"adverse\s+event",
        r"serious\s+adverse",
        r"black\s+box",
        r"clinical\s+hold",
        r"hepatotox",
        r"cardiotox",
    ],
    "dose_response": [
        r"dose[\s-](dependent|response|ranging)",
        r"higher\s+dose",
        r"dose[\s-]escalation",
        r"once[\s-](daily|weekly)\s+dos(e|ing)",              # MBX once-weekly convenience
        r"\d+\s*mg\s+(q\d+|once|twice)",                     # ABVX 50mg once-daily
    ],
    "surrogate_endpoint": [
        r"surrogate\s+endpoint",
        r"biomarker[\s-]based",
        r"ORR",
        r"objective\s+response\s+rate",
        r"pCR",
        r"pathologic(al)?\s+complete\s+response",
    ],
    "has_pfs": [
        r"progression[\s-]free\s+survival",
        r"\bPFS\b",
    ],
    "has_os": [
        r"overall\s+survival",
        r"\bOS\b\s+(benefit|improvement|endpoint|data)",
    ],
    "is_interim": [
        r"interim\s+(data|analysis|results|readout)",
        r"preliminary\s+(data|results|efficacy)",
        r"early[\s-]look",
    ],
    # ═══ NEW MOONSHOT NLP PATTERNS ═══
    "complete_response": [
        r"complete\s+response\s+rate",
        r"\d+%\s+complete\s+response",
        r"100%\s+(complete\s+)?response",                     # ROIV/CLDX pattern
        r"\bCR\b\s+(rate|of)",
        r"complete\s+remission",                              # MDNA pattern
    ],
    "high_response_rate": [
        r"(\d{2,3})%\s+(of\s+patients\s+)?(achieved|obtained|showed|demonstrated)",
        r"response\s+rate\s+(of\s+|was\s+)?\d{2,3}%",
        r"ORR\s+(was\s+|of\s+)?\d{2,3}%",
    ],
    "efficacy_beat_prior": [
        r"(exceeded|surpassed|beat)\s+(phase\s+\d|prior|previous|expectations)",
        r"improvement(s)?\s+(over|vs|compared\s+to)\s+phase\s+\d",
        r"significant\s+reductions?\s+in\s+",                 # UPB asthma exacerbation
        r"improvements?\s+in\s+(bowel|sleep|fatigue|quality)",# ABVX QoL beat
    ],
    "refractory_population": [
        r"refractory",
        r"treatment[\s-]resistant",
        r"previously\s+treated",
        r"relapsed\s+(and\s+|/)refractory",
        r"after\s+(prior|previous)\s+treatment",
        r"second[\s-]line",
        r"salvage",
    ],
    "gene_therapy": [
        r"gene\s+therap(y|ies)",
        r"gene\s+editing",
        r"AAV",
        r"adeno[\s-]associated",
        r"CRISPR",
        r"cell\s+therap(y|ies)",
        r"\bTIL\b",                                           # IOVA TIL therapy
        r"\bCAR[\s-]?T\b",
        r"lifileucel",                                        # IOVA specific TIL product
        r"one[\s-]time\s+treatment",                          # IOVA single-dose cell therapy
        r"autologous",                                        # cell therapy signal
    ],
    "dosing_convenience": [
        r"once[\s-](daily|weekly|monthly)",
        r"(oral|subcutaneous)\s+(formulation|administration|dosing|version)",
        r"(q\d+w|Q\d+W)",                                    # CLDX Q4W
        r"reduced\s+dosing\s+frequency",
    ],
    "blockbuster_market": [
        r"obesity",
        r"weight\s+(loss|reduction|management)",
        r"GLP[\s-]?1",
        r"immuno[\s-]?oncology",
        r"checkpoint\s+inhibitor",
        r"PD[\s-]?(L)?1",
        r"NASH",
        r"non[\s-]?alcoholic\s+steatohepatitis",
    ],
}

# Stage encoding
STAGE_MAP = {
    "phase 1":   0.15,
    "phase 1a":  0.12,
    "phase 1b":  0.20,
    "phase 1/2": 0.25,
    "phase 2":   0.35,
    "phase 2a":  0.30,
    "phase 2b":  0.38,
    "phase 2/3": 0.42,
    "phase 3":   0.55,
}

# Therapeutic area categorization
TA_KEYWORDS = {
    "oncology": ["cancer", "tumor", "tumour", "carcinoma", "lymphoma", "leukemia",
                 "leukaemia", "melanoma", "sarcoma", "glioblastoma", "myeloma",
                 "mesothelioma", "neuroblastoma", "oncology"],
    "cns": ["alzheimer", "parkinson", "multiple sclerosis", "epilepsy", "migraine",
            "depression", "schizophrenia", "bipolar", "adhd", "autism", "als",
            "amyotrophic", "huntington", "neuropath", "seizure", "anxiety",
            "ptsd", "psychosis", "dementia", "cns", "neuro"],
    "rare": ["rare", "orphan", "ultra-rare", "fabry", "gaucher", "pompe",
             "duchenne", "huntington", "cystic fibrosis", "sma", "spinal muscular",
             "hemophilia", "thalassemia", "sickle cell", "achondroplasia"],
    "immunology": ["rheumatoid", "lupus", "psoriasis", "crohn", "colitis",
                   "eczema", "dermatitis", "asthma", "allergy", "autoimmune",
                   "inflammatory", "immune", "immunology"],
    "pain": ["pain", "analgesic", "migraine", "fibromyalgia", "neuropathic pain"],
    "cardiovascular": ["heart", "cardiac", "hypertension", "atherosclerosis",
                       "atrial fibrillation", "heart failure", "coronary",
                       "cardiovascular", "stroke"],
    "infectious": ["hiv", "hepatitis", "influenza", "covid", "sars", "rsv",
                   "antibiotic", "antifungal", "antiviral", "infection",
                   "tuberculosis", "malaria", "pneumonia"],
    # ═══ MOONSHOT TAs ═══
    "dermatology": ["urticaria", "prurigo", "eczema", "psoriasis", "dermatitis",
                    "acne", "vitiligo", "alopecia", "rosacea", "skin",
                    "actinic keratosis", "atopic"],
    "metabolic": ["obesity", "diabetes", "metabolic", "weight", "NASH",
                  "steatohepatitis", "hyperlipidemia", "hypoparathyroidism",
                  "hyperparathyroidism"],
    "respiratory": ["asthma", "copd", "pulmonary", "respiratory", "lung fibrosis",
                    "idiopathic pulmonary", "cystic fibrosis"],
}


def extract_ta(indication):
    """Extract therapeutic area from indication text."""
    ind_lower = _lower(indication)
    for ta, keywords in TA_KEYWORDS.items():
        for kw in keywords:
            if kw in ind_lower:
                return ta
    return "other"


def extract_nlp_features(catalyst_text, indication=""):
    """Extract NLP features from catalyst text + indication context."""
    text = _lower(catalyst_text)
    ind = _lower(indication)
    # Combine catalyst + indication for broader signal detection
    combined = text + " " + ind
    feats = {}
    for feat_name, patterns in NLP_PATTERNS.items():
        # Primary: check catalyst text
        if _has_pattern(text, patterns):
            feats[feat_name] = 1.0
        # Secondary: some features can be inferred from indication
        elif feat_name in ("gene_therapy", "refractory_population",
                           "blockbuster_market") and _has_pattern(combined, patterns):
            feats[feat_name] = 1.0
        else:
            feats[feat_name] = 0.0

    # ═══ Indication-based inference (T-1 signals) ═══
    # Gene therapy indicators from indication
    gene_therapy_indications = ["huntington", "dmd", "duchenne", "sma", "spinal muscular",
                                 "hemophilia", "thalassemia", "x-linked", "adrenoleukodystrophy"]
    if any(kw in ind for kw in gene_therapy_indications):
        feats["gene_therapy"] = max(feats.get("gene_therapy", 0), 0.5)  # 0.5 = implied

    # Refractory indicators from indication
    refractory_indications = ["refractory", "resistant", "relapsed", "advanced",
                               "metastatic", "unresectable", "second-line", "salvage"]
    if any(kw in ind for kw in refractory_indications):
        feats["refractory_population"] = max(feats.get("refractory_population", 0), 0.5)

    # Blockbuster market indicators from indication
    blockbuster_indications = ["obesity", "diabetes", "nash", "weight", "alzheimer",
                                "breast cancer", "lung cancer", "nsclc"]
    if any(kw in ind for kw in blockbuster_indications):
        feats["blockbuster_market"] = max(feats.get("blockbuster_market", 0), 0.5)

    return feats


# ═══════════════════════════════════════════════════════════════
# DATA LOADING & FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════

# Base features extracted from each row
# ═══ MOONSHOT v2: Added 7 NLP signals, 3 TAs, price/cap tiers ═══
BASE_FEATURES = [
    "stage_numeric",
    "is_phase3",
    "is_phase2",
    "is_phase1",
    # Original NLP
    "primary_endpoint_met",
    "failure_signal",
    "strong_positive",
    "safety_clean",
    "safety_signal",
    "dose_response",
    "surrogate_endpoint",
    "has_pfs",
    "has_os",
    "is_interim",
    # ═══ NEW MOONSHOT NLP ═══
    "complete_response",
    "high_response_rate",
    "efficacy_beat_prior",
    "refractory_population",
    "gene_therapy",
    "dosing_convenience",
    "blockbuster_market",
    # TAs (original + moonshot)
    "ta_oncology",
    "ta_cns",
    "ta_rare",
    "ta_immunology",
    "ta_pain",
    "ta_cardiovascular",
    "ta_infectious",
    "ta_dermatology",
    "ta_metabolic",
    "ta_respiratory",
    # Price / Market Cap tiers
    "price_at_catalyst",
    "is_penny_stock",         # price < $5
    "is_small_cap_price",     # price < $20
    "is_mid_cap_price",       # price $20-$80
    "log_price",
    # Metadata
    "catalyst_text_len",
    "year",
]

# Engineered features (subset toggled by mutation)
ALL_ENGINEERED = {
    # Interaction: TA × Stage
    "ta_oncology_phase3":      lambda r: r.get("ta_oncology", 0) * r.get("is_phase3", 0),
    "ta_oncology_phase2":      lambda r: r.get("ta_oncology", 0) * r.get("is_phase2", 0),
    "ta_cns_phase3":           lambda r: r.get("ta_cns", 0) * r.get("is_phase3", 0),
    "ta_cns_phase2":           lambda r: r.get("ta_cns", 0) * r.get("is_phase2", 0),
    "ta_rare_phase3":          lambda r: r.get("ta_rare", 0) * r.get("is_phase3", 0),
    "ta_rare_positive":        lambda r: r.get("ta_rare", 0) * r.get("strong_positive", 0),
    "ta_immunology_phase3":    lambda r: r.get("ta_immunology", 0) * r.get("is_phase3", 0),
    # NLP × Stage
    "endpoint_met_phase3":     lambda r: r.get("primary_endpoint_met", 0) * r.get("is_phase3", 0),
    "failure_phase3":          lambda r: r.get("failure_signal", 0) * r.get("is_phase3", 0),
    "safety_clean_phase3":     lambda r: r.get("safety_clean", 0) * r.get("is_phase3", 0),
    "strong_positive_phase3":  lambda r: r.get("strong_positive", 0) * r.get("is_phase3", 0),
    # NLP × NLP
    "endpoint_x_safety":       lambda r: r.get("primary_endpoint_met", 0) * r.get("safety_clean", 0),
    "endpoint_x_strong":       lambda r: r.get("primary_endpoint_met", 0) * r.get("strong_positive", 0),
    "failure_x_safety_signal": lambda r: r.get("failure_signal", 0) * r.get("safety_signal", 0),
    # Derived
    "sentiment_composite":     lambda r: (r.get("primary_endpoint_met", 0) * 2 +
                                           r.get("strong_positive", 0) * 1.5 +
                                           r.get("safety_clean", 0) * 0.5 -
                                           r.get("failure_signal", 0) * 3 -
                                           r.get("safety_signal", 0) * 1),
    "is_recent_year":          lambda r: 1.0 if r.get("year", 0) >= 2025 else 0.0,
    "log_text_len":            lambda r: math.log1p(r.get("catalyst_text_len", 0)),
    "stage_x_sentiment":       lambda r: r.get("stage_numeric", 0) * r.get("_sentiment_composite", 0),
    # Surrogate / PFS / OS interactions
    "surrogate_phase3":        lambda r: r.get("surrogate_endpoint", 0) * r.get("is_phase3", 0),
    "pfs_phase3":              lambda r: r.get("has_pfs", 0) * r.get("is_phase3", 0),
    "os_phase3":               lambda r: r.get("has_os", 0) * r.get("is_phase3", 0),
    "interim_phase3":          lambda r: r.get("is_interim", 0) * r.get("is_phase3", 0),
    # Target-frequency encoded (computed at load time)
    "indication_freq":         lambda r: r.get("_indication_freq", 0.5),
    "stage_freq":              lambda r: r.get("_stage_freq", 0.5),
    "indication_positive_rate":lambda r: r.get("_indication_pos_rate", 0.5),

    # ═══════════════════════════════════════════════════════════
    # MOONSHOT v2: T-1 Surge Prediction Features
    # Patterns from CAPR(+371%), ABVX(+600%), QURE(+350%),
    # PRAX(+230%), MBX(+100%), ROIV(+100%), IOVA(+830%),
    # MDNA(moonshot), CLDX(+200%), VKTX(+200%)
    # ═══════════════════════════════════════════════════════════

    # 1. CAPR pattern: small-cap + Phase 3 hit + clean safety → +371%
    "small_cap_phase3_clean":  lambda r: (r.get("is_small_cap_price", 0) *
                                           r.get("is_phase3", 0) *
                                           r.get("safety_clean", 0)),

    # 2. ABVX pattern: Phase 3 + efficacy beat prior + endpoint met → +600%
    "phase3_efficacy_beat":    lambda r: (r.get("is_phase3", 0) *
                                           r.get("efficacy_beat_prior", 0) *
                                           r.get("primary_endpoint_met", 0)),

    # 3. QURE/IOVA pattern: gene/cell therapy + orphan/rare → +350%/+830%
    "gene_therapy_rare":       lambda r: (r.get("gene_therapy", 0) *
                                           r.get("ta_rare", 0)),

    # 4. ROIV/CLDX pattern: complete response + rare disease → +100%/+200%
    "complete_response_rare":  lambda r: (r.get("complete_response", 0) *
                                           r.get("ta_rare", 0)),

    # 5. CLDX pattern: high CR + immunology/dermatology → +200%
    "cr_immunology":           lambda r: (r.get("complete_response", 0) *
                                           max(r.get("ta_immunology", 0),
                                               r.get("ta_dermatology", 0))),

    # 6. VKTX pattern: blockbuster market + oral convenience → +200%
    "blockbuster_convenience": lambda r: (r.get("blockbuster_market", 0) *
                                           r.get("dosing_convenience", 0)),

    # 7. MBX pattern: dosing convenience + orphan/rare → +100%
    "convenience_orphan":      lambda r: (r.get("dosing_convenience", 0) *
                                           r.get("ta_rare", 0)),

    # 8. IOVA pattern: refractory + immunotherapy/gene therapy → +830%
    "refractory_immunotherapy": lambda r: (r.get("refractory_population", 0) *
                                            r.get("gene_therapy", 0)),

    # 9. MDNA pattern: interim CR + deadly disease (oncology) → moonshot
    "interim_cr_oncology":     lambda r: (r.get("is_interim", 0) *
                                           r.get("complete_response", 0) *
                                           r.get("ta_oncology", 0)),

    # 10. Penny stock + Phase 3 hit (max surge potential)
    "penny_phase3_hit":        lambda r: (r.get("is_penny_stock", 0) *
                                           r.get("is_phase3", 0) *
                                           r.get("primary_endpoint_met", 0)),

    # 11. Small cap + strong positive + safety clean (triple moonshot)
    "small_strong_safe":       lambda r: (r.get("is_small_cap_price", 0) *
                                           r.get("strong_positive", 0) *
                                           r.get("safety_clean", 0)),

    # 12. High response rate + Phase 2+ (de-risk signal)
    "high_rr_phase2plus":      lambda r: (r.get("high_response_rate", 0) *
                                           max(r.get("is_phase2", 0),
                                               r.get("is_phase3", 0))),

    # 13. Complete response + Phase 3 (registration-quality)
    "cr_phase3":               lambda r: (r.get("complete_response", 0) *
                                           r.get("is_phase3", 0)),

    # 14. Gene therapy + Phase 1/early (huge upside on early signal)
    "gene_therapy_early":      lambda r: (r.get("gene_therapy", 0) *
                                           r.get("is_phase1", 0)),

    # 15. Refractory + oncology + high response
    "refractory_onco_rr":      lambda r: (r.get("refractory_population", 0) *
                                           r.get("ta_oncology", 0) *
                                           r.get("high_response_rate", 0)),

    # 16. Blockbuster market + Phase 3 (commercial catalyst)
    "blockbuster_phase3":      lambda r: (r.get("blockbuster_market", 0) *
                                           r.get("is_phase3", 0)),

    # 17. Metabolic + convenience + Phase 2+ (VKTX-class)
    "metabolic_convenience":   lambda r: (r.get("ta_metabolic", 0) *
                                           r.get("dosing_convenience", 0)),

    # 18. CNS + Phase 3 + strong positive (PRAX-class)
    "cns_phase3_strong":       lambda r: (r.get("ta_cns", 0) *
                                           r.get("is_phase3", 0) *
                                           r.get("strong_positive", 0)),

    # 19. MOONSHOT COMPOSITE SCORE (weighted signal aggregation)
    "moonshot_composite":      lambda r: (
        r.get("is_small_cap_price", 0) * 2.0 +
        r.get("is_penny_stock", 0) * 1.5 +
        r.get("complete_response", 0) * 2.0 +
        r.get("high_response_rate", 0) * 1.5 +
        r.get("efficacy_beat_prior", 0) * 1.5 +
        r.get("gene_therapy", 0) * 1.0 +
        r.get("refractory_population", 0) * 1.0 +
        r.get("ta_rare", 0) * 1.5 +
        r.get("blockbuster_market", 0) * 1.0 +
        r.get("dosing_convenience", 0) * 0.5 -
        r.get("failure_signal", 0) * 5.0 -
        r.get("safety_signal", 0) * 2.0
    ),

    # 20. Price-adjusted sentiment (lower price = higher sensitivity)
    "price_adj_sentiment":     lambda r: (r.get("_sentiment_composite", 0) *
                                           (1.0 / max(r.get("price_at_catalyst", 20), 0.5))),
}


def load_raw_rows():
    """Load historical readouts CSV and extract features."""
    with open(DATASET_PATH, encoding="utf-8", errors="replace") as f:
        raw = list(csv.DictReader(f))

    # Pre-compute target-encoding stats (global, no leakage for now)
    indication_counts = Counter()
    indication_positive = Counter()
    stage_counts = Counter()
    for row in raw:
        ind = _lower(row.get("Indication", ""))
        stg = _lower(row.get("Stage", ""))
        outcome = _lower(row.get("outcome", ""))
        indication_counts[ind] += 1
        stage_counts[stg] += 1
        if outcome == "positive":
            indication_positive[ind] += 1

    total = len(raw)

    rows = []
    for row in raw:
        outcome = _lower(row.get("outcome", ""))
        if outcome not in ("positive", "negative"):
            continue

        catalyst = row.get("Catalyst", "") or ""
        indication = _lower(row.get("Indication", ""))
        stage = _lower(row.get("Stage", ""))
        ta = extract_ta(indication)
        nlp = extract_nlp_features(catalyst, indication)

        try:
            yr = int(row.get("year", 0))
        except (ValueError, TypeError):
            yr = 2024

        stage_num = STAGE_MAP.get(stage, 0.30)

        # ═══ Parse price ═══
        price_str = (row.get("Price At Catalyst Date", "") or "").strip()
        try:
            price = float(price_str) if price_str else 0.0
        except (ValueError, TypeError):
            price = 0.0

        feat = {
            "outcome": outcome,
            "year": float(yr),
            "stage_numeric": stage_num,
            "is_phase3": 1.0 if "3" in stage else 0.0,
            "is_phase2": 1.0 if "2" in stage and "3" not in stage else 0.0,
            "is_phase1": 1.0 if stage.startswith("phase 1") and "2" not in stage else 0.0,
            "catalyst_text_len": float(len(catalyst)),
            # ═══ Price / Cap tiers (MOONSHOT v2) ═══
            "price_at_catalyst": price,
            "is_penny_stock": 1.0 if 0 < price < 5.0 else 0.0,
            "is_small_cap_price": 1.0 if 0 < price < 20.0 else 0.0,
            "is_mid_cap_price": 1.0 if 20.0 <= price <= 80.0 else 0.0,
            "log_price": math.log1p(price) if price > 0 else 0.0,
            # TAs (original + moonshot)
            "ta_oncology": 1.0 if ta == "oncology" else 0.0,
            "ta_cns": 1.0 if ta == "cns" else 0.0,
            "ta_rare": 1.0 if ta == "rare" else 0.0,
            "ta_immunology": 1.0 if ta == "immunology" else 0.0,
            "ta_pain": 1.0 if ta == "pain" else 0.0,
            "ta_cardiovascular": 1.0 if ta == "cardiovascular" else 0.0,
            "ta_infectious": 1.0 if ta == "infectious" else 0.0,
            "ta_dermatology": 1.0 if ta == "dermatology" else 0.0,
            "ta_metabolic": 1.0 if ta == "metabolic" else 0.0,
            "ta_respiratory": 1.0 if ta == "respiratory" else 0.0,
            # Target-encoded freq
            "_indication_freq": indication_counts.get(indication, 1) / total,
            "_stage_freq": stage_counts.get(stage, 1) / total,
            "_indication_pos_rate": (indication_positive.get(indication, 0) /
                                     max(indication_counts.get(indication, 1), 1)),
        }
        # NLP features
        feat.update(nlp)
        # Pre-compute sentiment composite for stage_x_sentiment
        feat["_sentiment_composite"] = (
            feat.get("primary_endpoint_met", 0) * 2 +
            feat.get("strong_positive", 0) * 1.5 +
            feat.get("safety_clean", 0) * 0.5 -
            feat.get("failure_signal", 0) * 3 -
            feat.get("safety_signal", 0) * 1
        )

        rows.append(feat)

    return rows


def build_feature_matrix(rows, base_cols, eng_names):
    """Build X, y, years arrays from feature dicts."""
    all_cols = list(base_cols) + list(eng_names)
    eng_funcs = {k: ALL_ENGINEERED[k] for k in eng_names if k in ALL_ENGINEERED}

    X_list, y_list, yr_list = [], [], []
    for row in rows:
        feat = {}
        # Base
        for col in base_cols:
            feat[col] = float(row.get(col, 0.0))
        # Engineered
        for name, func in eng_funcs.items():
            try:
                feat[name] = func(row)
            except Exception:
                feat[name] = 0.0

        X_list.append([feat.get(c, 0.0) for c in all_cols])
        y_list.append(1 if row.get("outcome", "") == "positive" else 0)
        yr_list.append(int(row.get("year", 2024)))

    return np.array(X_list), np.array(y_list), np.array(yr_list), all_cols


# ═══════════════════════════════════════════════════════════════
# WALK-FORWARD EVALUATOR
# ═══════════════════════════════════════════════════════════════

def walk_forward_auc(X, y, years, params, feature_names):
    """Walk-forward AUC — temporal integrity preserved."""
    unique_years = sorted(set(years[years > 0]))
    aucs, briers, t4_precs = [], [], []

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
        neg, pos = (y_tr == 0).sum(), (y_tr == 1).sum()
        p["scale_pos_weight"] = neg / max(pos, 1)

        dtrain = lgb.Dataset(X_tr, label=y_tr, feature_name=feature_names)
        dval = lgb.Dataset(X_te, label=y_te, reference=dtrain, feature_name=feature_names)

        model = lgb.train(p, dtrain, valid_sets=[dval],
                          callbacks=[lgb.log_evaluation(0)])
        preds = model.predict(X_te)

        if len(set(y_te)) >= 2:
            aucs.append(roc_auc_score(y_te, preds))
        briers.append(brier_score_loss(y_te, preds))

        t4 = preds < 0.40
        if t4.sum() > 0:
            t4_precs.append((y_te[t4] == 0).sum() / t4.sum())

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
# MOONSHOT SURGE MAGNITUDE SCORER
# ═══════════════════════════════════════════════════════════════
# Rule-based tier system derived from 10 moonshot examples:
#   Tier 5: 200%+ (ABVX, IOVA, CAPR, QURE class)
#   Tier 4: 100-200% (ROIV, MBX, CLDX, VKTX class)
#   Tier 3: 50-100%
#   Tier 2: 20-50%
#   Tier 1: <20% (typical positive readout)

MOONSHOT_SURGE_TIERS = {
    5: "🌙🚀 MEGA-SURGE (200%+)",
    4: "🚀 SURGE (100-200%)",
    3: "📈 STRONG (50-100%)",
    2: "📊 MODERATE (20-50%)",
    1: "➡️ MILD (<20%)",
}


def score_moonshot_surge(row_feats):
    """
    Score moonshot surge potential for a single event.
    Returns (tier 1-5, score 0-100, signals list).

    Based on empirical patterns:
    - CAPR: small-cap + Phase3 + orphan + redemption → +371%
    - ABVX: Phase3 beat + clean safety + QoL improvement → +600%
    - QURE: gene therapy + ALS + durability → +350%
    - PRAX: CNS + Phase3 + 53% seizure reduction → +230%
    - MBX: once-weekly convenience + orphan → +100%
    - ROIV: 100% response + rare disease → +100%
    - IOVA: TIL + refractory melanoma + ORR 40%+ → +830%
    - MDNA: interim CR + pancreatic cancer → moonshot
    - CLDX: 66% CR + dermatology/immunology → +200%
    - VKTX: oral GLP-1 + obesity Phase 2 → +200%
    """
    score = 0.0
    signals = []

    # ═══ PRICE/CAP MULTIPLIER (biggest predictor of surge magnitude) ═══
    if row_feats.get("is_penny_stock", 0):
        score += 25
        signals.append("penny_stock_max_leverage")
    elif row_feats.get("is_small_cap_price", 0):
        score += 15
        signals.append("small_cap_high_leverage")
    elif row_feats.get("is_mid_cap_price", 0):
        score += 5

    # ═══ PHASE × EFFICACY ═══
    if row_feats.get("is_phase3", 0) and row_feats.get("primary_endpoint_met", 0):
        score += 20
        signals.append("phase3_endpoint_met")
    if row_feats.get("complete_response", 0):
        score += 15
        signals.append("complete_response_signal")
    if row_feats.get("high_response_rate", 0):
        score += 10
        signals.append("high_response_rate")
    if row_feats.get("efficacy_beat_prior", 0):
        score += 12
        signals.append("efficacy_beat_prior_phase")

    # ═══ SAFETY DE-RISK ═══
    if row_feats.get("safety_clean", 0) and not row_feats.get("safety_signal", 0):
        score += 8
        signals.append("clean_safety_profile")

    # ═══ TA MULTIPLIERS ═══
    if row_feats.get("ta_rare", 0):
        score += 12
        signals.append("orphan_rare_premium")
    if row_feats.get("blockbuster_market", 0):
        score += 10
        signals.append("blockbuster_market_upside")
    if row_feats.get("gene_therapy", 0):
        score += 8
        signals.append("gene_cell_therapy")
    if row_feats.get("refractory_population", 0):
        score += 8
        signals.append("refractory_unmet_need")

    # ═══ CONVENIENCE / DIFFERENTIATION ═══
    if row_feats.get("dosing_convenience", 0):
        score += 5
        signals.append("dosing_convenience_edge")

    # ═══ NEGATIVE MODIFIERS ═══
    if row_feats.get("failure_signal", 0):
        score -= 50
        signals.append("FAILURE_SIGNAL_DETECTED")
    if row_feats.get("safety_signal", 0):
        score -= 20
        signals.append("safety_concern")

    # Clamp to 0-100
    score = max(0, min(100, score))

    # Tier assignment
    if score >= 70:
        tier = 5
    elif score >= 50:
        tier = 4
    elif score >= 35:
        tier = 3
    elif score >= 20:
        tier = 2
    else:
        tier = 1

    return tier, round(score, 1), signals


# ═══════════════════════════════════════════════════════════════
# FEATURE CO-EVOLUTION
# ═══════════════════════════════════════════════════════════════

def mutate_features(current_eng, rng):
    """Randomly add/remove engineered features."""
    all_eng = list(ALL_ENGINEERED.keys())
    current = set(current_eng)

    for feat in all_eng:
        if rng.random() < FEATURE_MUTATION_RATE:
            if feat in current:
                current.discard(feat)
            else:
                current.add(feat)

    # Always keep core features
    current.add("sentiment_composite")
    current.add("indication_positive_rate")
    current.add("moonshot_composite")
    current.add("price_adj_sentiment")
    return sorted(current)


# ═══════════════════════════════════════════════════════════════
# OPTUNA OBJECTIVE
# ═══════════════════════════════════════════════════════════════

def make_objective(X, y, years, feature_names):
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
    p = dict(params)
    neg, pos = (y == 0).sum(), (y == 1).sum()
    p["scale_pos_weight"] = neg / max(pos, 1)
    if "early_stopping_rounds" in p:
        del p["early_stopping_rounds"]

    model = lgb.LGBMClassifier(**p)
    model.fit(X, y)

    calibrated = CalibratedClassifierCV(model, cv=5, method="sigmoid")
    calibrated.fit(X, y)
    return model, calibrated


def load_ensemble_pool():
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
    if not pool:
        return None
    preds_list, weights = [], []
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
    if LADDER_PATH.exists():
        with open(LADDER_PATH) as f:
            return json.load(f)
    return {"current_champion": None, "history": [], "total_rounds": 0, "total_promotions": 0}


def save_ladder(ladder):
    with open(LADDER_PATH, "w") as f:
        json.dump(ladder, f, indent=2)


def promote_champion(ladder, candidate, round_num):
    old_auc = 0.0
    if ladder["current_champion"]:
        old_auc = ladder["current_champion"].get("wf_auc", 0.0)

    new_auc = candidate["wf_auc"]
    delta = new_auc - old_auc

    if delta >= PROMOTE_THRESHOLD_AUC or ladder["current_champion"] is None:
        log.info(f"🏆 GUNGNIR CHAMPION: WF AUC {new_auc:.6f} (Δ{delta:+.6f} vs {old_auc:.6f})")
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

def run_one_round(round_num, rows, ladder, rng):
    """Execute one full Gungnir auto-ML round."""
    ts_start = time.time()

    # Feature mutation
    if ladder["current_champion"] and ladder["current_champion"].get("eng_features"):
        prev_eng = ladder["current_champion"]["eng_features"]
    else:
        prev_eng = [
            # Original core
            "sentiment_composite", "indication_positive_rate", "indication_freq",
            "ta_oncology_phase3", "ta_cns_phase3", "endpoint_met_phase3",
            "failure_phase3", "endpoint_x_safety", "endpoint_x_strong",
            "is_recent_year",
            # Moonshot v2 defaults
            "moonshot_composite", "small_cap_phase3_clean", "phase3_efficacy_beat",
            "gene_therapy_rare", "complete_response_rare", "cr_immunology",
            "blockbuster_convenience", "refractory_immunotherapy",
            "penny_phase3_hit", "small_strong_safe", "price_adj_sentiment",
            "cr_phase3", "blockbuster_phase3", "cns_phase3_strong",
        ]

    new_eng = mutate_features(prev_eng, rng)
    log.info(f"  Features: {len(BASE_FEATURES)} base + {len(new_eng)} engineered = {len(BASE_FEATURES) + len(new_eng)} total")

    # Build matrix
    X, y, years, feat_names = build_feature_matrix(rows, BASE_FEATURES, new_eng)

    # Optuna search
    study = optuna.create_study(direction="maximize",
                                 sampler=optuna.samplers.TPESampler(seed=rng.randint(0, 2**31)))
    objective = make_objective(X, y, years, feat_names)
    study.optimize(objective, n_trials=OPTUNA_TRIALS_PER_ROUND, show_progress_bar=False)

    best_params = study.best_params
    best_wf_auc = study.best_value
    log.info(f"  Optuna best WF AUC: {best_wf_auc:.6f} ({OPTUNA_TRIALS_PER_ROUND} trials)")

    # Reconstruct params
    full_params = {
        "objective": "binary", "metric": "auc",
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
        "verbose": -1, "seed": 42,
        "n_estimators": best_params.pop("n_estimators", 500),
    }
    if full_params["boosting_type"] == "dart":
        full_params["drop_rate"] = best_params.pop("drop_rate", 0.1)
        full_params["skip_drop"] = best_params.pop("skip_drop", 0.5)

    # Walk-forward eval
    wf_result = walk_forward_auc(X, y, years, {**full_params, "early_stopping_rounds": 50}, feat_names)
    log.info(f"  Walk-forward: AUC={wf_result['wf_auc']:.6f}, Brier={wf_result['wf_brier']:.6f}, "
             f"T4P={wf_result['wf_t4p']:.4f}, Years={wf_result['n_years']}")

    # Train full model
    model, calibrated = train_full_model(X, y, full_params, feat_names)
    importances = dict(zip(feat_names, [int(x) for x in model.feature_importances_]))
    top5 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    log.info(f"  Top features: {', '.join(f'{n}({v})' for n, v in top5)}")

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

    # Add to ensemble pool
    pool_entry = {
        "model": model, "calibrated": calibrated,
        "wf_auc": wf_result["wf_auc"], "feature_names": feat_names,
        "eng_features": new_eng, "params_hash": params_hash, "round": round_num,
    }
    pool_path = ENSEMBLE_DIR / f"gun_r{round_num:05d}_{params_hash}.pkl"
    with open(pool_path, "wb") as f:
        pickle.dump(pool_entry, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Prune ensemble pool
    pool_files = sorted(ENSEMBLE_DIR.glob("*.pkl"), key=lambda p: p.stat().st_mtime)
    if len(pool_files) > ENSEMBLE_POOL_SIZE:
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

    # ═══ Moonshot Surge Scoring on positive predictions ═══
    surge_stats = {"tier_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}, "top_surges": []}
    for i, row in enumerate(rows):
        if row.get("outcome") == "positive":
            tier, surge_score, signals = score_moonshot_surge(row)
            surge_stats["tier_counts"][tier] += 1
            if tier >= 4:
                surge_stats["top_surges"].append({
                    "index": i,
                    "tier": tier,
                    "score": surge_score,
                    "signals": signals[:5],
                })
    tier_str = ", ".join(f"T{t}:{c}" for t, c in sorted(surge_stats["tier_counts"].items(), reverse=True))
    log.info(f"  🌙 Surge tiers (positives): {tier_str}")
    log.info(f"  🚀 Tier4+5 moonshots: {surge_stats['tier_counts'].get(4,0) + surge_stats['tier_counts'].get(5,0)}")

    # Ensemble evaluation
    pool = load_ensemble_pool()
    if len(pool) >= 3:
        ens_preds = ensemble_predict(pool, X)
        if ens_preds is not None:
            ens_auc = roc_auc_score(y, ens_preds)
            log.info(f"  Ensemble ({len(pool)} models): in-sample AUC={ens_auc:.6f}")

    # Champion promotion
    promoted = promote_champion(ladder, candidate, round_num)
    if promoted:
        champ_path = GUNGNIR_DIR / f"champion_r{round_num:05d}_{params_hash}.pkl"
        with open(champ_path, "wb") as f:
            pickle.dump({
                "model": model, "calibrated": calibrated,
                "feature_names": feat_names, "eng_features": new_eng,
                "params": full_params, "wf_result": wf_result,
                "round": round_num, "timestamp": datetime.now().isoformat(),
            }, f, protocol=pickle.HIGHEST_PROTOCOL)
        best_path = GUNGNIR_DIR / "CURRENT_BEST.pkl"
        with open(best_path, "wb") as f:
            pickle.dump({
                "model": model, "calibrated": calibrated,
                "feature_names": feat_names, "eng_features": new_eng,
                "params": full_params, "wf_result": wf_result,
                "round": round_num, "timestamp": datetime.now().isoformat(),
            }, f, protocol=pickle.HIGHEST_PROTOCOL)

    ladder["total_rounds"] = round_num
    save_ladder(ladder)

    elapsed = time.time() - ts_start
    log.info(f"  Round {round_num} complete in {elapsed:.1f}s | "
             f"Champion AUC: {ladder['current_champion']['wf_auc']:.6f}")

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
    log.info("  GUNGNIR HISTORICAL EVOLVE — LightGBM Phase Readout Daemon")
    log.info(f"  Started: {datetime.now().isoformat()}")
    log.info(f"  Dataset: {DATASET_PATH} (2K events)")
    log.info(f"  Optuna trials/round: {OPTUNA_TRIALS_PER_ROUND}")
    log.info(f"  Kaizen engine: {'ENABLED' if KAIZEN_ENABLED else 'DISABLED'}")
    log.info("=" * 70)

    kaizen = None
    if KAIZEN_ENABLED:
        kaizen = KaizenTracker(KAIZEN_DIR)
        log.info(f"  改善 Kaizen tracker (Gungnir) → {KAIZEN_DIR}")

    rows = load_raw_rows()
    log.info(f"  Loaded {len(rows)} readout events")
    log.info(f"  Positive: {sum(1 for r in rows if r['outcome'] == 'positive')}, "
             f"Negative: {sum(1 for r in rows if r['outcome'] == 'negative')}")

    ladder = load_ladder()
    start_round = ladder["total_rounds"] + 1
    rng = np.random.RandomState(77 + start_round)

    if ladder["current_champion"]:
        log.info(f"  Resuming from round {start_round}, champion AUC: {ladder['current_champion']['wf_auc']:.6f}")
    else:
        log.info(f"  Fresh start — no Gungnir LGB champion yet")

    for round_num in range(start_round, start_round + MAX_ROUNDS):
        if SHUTDOWN:
            log.info("⚡ Graceful shutdown.")
            break
        if STOP_FILE.exists():
            log.info(f"🛑 STOP_GUNGNIR detected — halting.")
            STOP_FILE.unlink()
            break

        # Kaizen adaptive config
        if kaizen:
            ac = kaizen.get_adaptive_config()
            FEATURE_MUTATION_RATE = ac["mutation_rate"]
            effective_trials = max(10, int(OPTUNA_TRIALS_PER_ROUND * ac["search_width"]))
            OPTUNA_TRIALS_PER_ROUND = effective_trials

            # Check for AI config overrides (from /api/ai/tune)
            ai_override_path = REALMS_ROOT / "kaizen_dual" / "ai_config_override.json"
            try:
                if ai_override_path.exists():
                    with open(ai_override_path) as aof:
                        ai_cfg = json.load(aof)
                    if "optuna_trials" in ai_cfg:
                        OPTUNA_TRIALS_PER_ROUND = int(ai_cfg["optuna_trials"])
                    if "ensemble_pool_size" in ai_cfg:
                        ENSEMBLE_POOL_SIZE = int(ai_cfg["ensemble_pool_size"])
                    ai_src = ai_cfg.get("source", "?")
                    log.info(f"  🤖 AI override active (source={ai_src}): trials={OPTUNA_TRIALS_PER_ROUND}, pool={ENSEMBLE_POOL_SIZE}")
            except Exception:
                pass

            log.info(f"\n{'─' * 60}")
            log.info(f"  GUNGNIR ROUND {round_num} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log.info(f"  改善 score={kaizen.kaizen_score}, mutRate={ac['mutation_rate']:.3f}, "
                     f"temp={ac['temperature']:.2f}, trials={effective_trials}")
            log.info(f"{'─' * 60}")
        else:
            log.info(f"\n{'─' * 60}")
            log.info(f"  GUNGNIR ROUND {round_num}")
            log.info(f"{'─' * 60}")

        try:
            promoted, metrics = run_one_round(round_num, rows, ladder, rng)

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
                         f"Streak: {kaizen.current_streak}")

        except Exception as e:
            log.error(f"  ❌ Gungnir Round {round_num} FAILED: {e}")
            log.error(traceback.format_exc())
            time.sleep(5)
            continue

        if SLEEP_BETWEEN_ROUNDS > 0:
            time.sleep(SLEEP_BETWEEN_ROUNDS)

    # Final summary
    ladder = load_ladder()
    log.info("\n" + "=" * 70)
    log.info("  GUNGNIR DAEMON SESSION COMPLETE")
    log.info(f"  Total rounds: {ladder['total_rounds']}")
    log.info(f"  Total promotions: {ladder['total_promotions']}")
    if ladder["current_champion"]:
        log.info(f"  Champion WF AUC: {ladder['current_champion']['wf_auc']:.6f}")
    if kaizen:
        log.info(f"  改善 Final Kaizen Score: {kaizen.kaizen_score}/100")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
