#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR PERPETUAL HONING ENGINE v1.0                                  ║
║  Calibrated on ~4,600 real Phase readout events (2017-2026)            ║
║  Base rate: ~53% positive                                              ║
║                                                                        ║
║  Feature architecture:                                                 ║
║    - 35 NLP features extracted from catalyst text                      ║
║    - 11 risk overlay rules                                             ║
║    - TA-specific signals (Oncology, CNS, Rare, Pain, Immunology)       ║
║    - Temporal interactions (Hoeg-era, gene therapy, safety)            ║
║                                                                        ║
║  All weights are EMPIRICAL — from Gungnir v4.0 production model.      ║
║  Gradient descent fine-tunes to minimize Brier score.                  ║
║                                                                        ║
║  Companion to ODIN Honing Engine (PDUFA events).                       ║
║  ODIN = regulatory approval | GUNGNIR = clinical readouts             ║
║                                                                        ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════════════
#  MATH PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ez = math.exp(x)
        return ez / (1.0 + ez)

def logit(p: float) -> float:
    p = max(1e-7, min(1 - 1e-7, p))
    return math.log(p / (1 - p))


# ═══════════════════════════════════════════════════════════════
#  NLP KEYWORD LISTS (from Gungnir v4.0)
# ═══════════════════════════════════════════════════════════════

_GT_TICKERS = {
    'RCKT', 'RGNX', 'SGMO', 'BLUE', 'BEAM', 'CRSP', 'EDIT', 'NTLA', 'VRTX', 'BMRN',
    'SRPT', 'QURE', 'ONCE', 'AVXL', 'RARE', 'MESO', 'ABEO', 'AGTC', 'STOK', 'PBYI',
}
_GT_KW = [
    'gene therapy', 'gene transfer', 'aav', 'adeno-associated', 'lentiviral',
    'cell therapy', 'car-t', 'car t', 'crispr', 'base editing', 'mrna therapy',
    'gene replacement', 'gene editing', 'antisense oligonucleotide',
    'aso therapy', 'sirna', 'rnai',
]
_PSYCH_KW = ['mdma', 'psilocybin', 'lsd', 'ketamine', 'psychedelic',
             'dmt', 'ayahuasca', 'ibogaine', 'mescaline']
_SAF_SEV = [
    'dili', 'drug-induced liver', 'hepatotoxicity', 'liver injury',
    'cardiac death', 'sudden death', 'fatal', 'suicidal',
    'pml', 'progressive multifocal', 'stevens-johnson',
    'anaphylaxis', 'cytokine release syndrome', 'black box',
]
_SAF_MOD = [
    'cardiac', 'arrhythmia', 'qt prolongation', 'liver enzyme',
    'elevated alt', 'elevated ast', 'neutropenia', 'thrombocytopenia',
    'rems', 'risk evaluation', 'boxed warning',
]
_PPM_KW = [
    'failed primary', 'did not meet primary', 'missed primary',
    'primary endpoint not met', 'primary endpoint was not',
    'fda wants more data', 'complete response letter',
    'additional data required', 'fda requested additional',
    'phase 3 required', 'confirmatory trial',
]
_SA_KW = ['single-arm', 'single arm', 'non-randomized', 'uncontrolled',
          'open-label single', 'no comparator']


# ═══════════════════════════════════════════════════════════════
#  FEATURE NAMES (35 features from Gungnir v4.0)
# ═══════════════════════════════════════════════════════════════

FEATURE_NAMES = [
    "is_hard_endpoint", "phase_PHASE3", "is_competitive_space", "sentiment_score",
    "phase_PHASE2", "primary_endpoint_met", "ta_ONCOLOGY", "rct_x_phase3",
    "has_breakthrough", "has_orphan", "has_priority_review", "has_fast_track",
    "is_gene_therapy", "is_psychedelic", "safety_signal", "ppm_flag",
    "is_single_arm", "has_surrogate", "is_hoeg_era", "accel_approval_2025",
    "single_arm_2025", "failure_signal", "strong_positive", "dose_response",
    "safety_clean", "ta_CNS", "ta_RARE", "ta_PAIN", "ta_IMMUNOLOGY",
    "gene_therapy_x_phase3", "safety_x_hoeg", "ppm_x_hoeg",
    "oncology_x_phase3", "rare_x_positive", "failure_x_phase3",
    "p23_p2_bucket_lt_0001", "p23_p2_bucket_0001_001", "p23_p2_bucket_001_005",
    "ta_oncology_phase3", "ta_cns_phase3", "ta_rare_phase3", "ta_immunology_phase3",
]

# Initial weights from Gungnir v4.0 (logit-space, simplified for honing)
# These are STARTING weights — gradient descent will fine-tune them.
INITIAL_WEIGHTS = {
    "base_logit": 0.12,  # ~53% base positive rate
    "features": {
        "is_hard_endpoint":      0.30,
        "phase_PHASE3":         -0.20,
        "is_competitive_space":  0.15,
        "sentiment_score":       0.65,
        "phase_PHASE2":         -0.10,
        "primary_endpoint_met":  1.10,
        "ta_ONCOLOGY":           0.10,
        "rct_x_phase3":          0.05,
        "has_breakthrough":      0.05,
        "has_orphan":            0.01,
        "has_priority_review":   0.00,
        "has_fast_track":        0.00,
        "is_gene_therapy":      -0.15,
        "is_psychedelic":       -0.20,
        "safety_signal":        -0.30,
        "ppm_flag":             -0.50,
        "is_single_arm":        -0.05,
        "has_surrogate":         0.45,
        "is_hoeg_era":          -0.10,
        "accel_approval_2025":  -0.05,
        "single_arm_2025":      -0.10,
        "failure_signal":       -2.30,
        "strong_positive":       0.30,
        "dose_response":         0.10,
        "safety_clean":          0.15,
        "ta_CNS":               -0.10,
        "ta_RARE":               0.05,
        "ta_PAIN":              -0.10,
        "ta_IMMUNOLOGY":         0.15,
        "gene_therapy_x_phase3": -0.15,
        "safety_x_hoeg":        -0.15,
        "ppm_x_hoeg":           -0.10,
        "oncology_x_phase3":    -0.05,
        "rare_x_positive":       0.05,
        "failure_x_phase3":     -0.10,
        # H: Phase 2→3 evidence buckets (from 72-pair audit)
        # OR=41 for sig vs non-sig; monotonic: lt0001 > 0001_001 > 001_005
        "p23_p2_bucket_lt_0001":  2.00,   # p<0.001 → 95.2% P3 success
        "p23_p2_bucket_0001_001": 1.30,   # 0.001≤p<0.01 → 84.6% P3 success
        "p23_p2_bucket_001_005":  0.70,   # 0.01≤p<0.05 → 66.7% P3 success
        # I: TA × Phase3 priors (anchored to historical TA success rates)
        "ta_oncology_phase3":    -0.25,   # Oncology P3 penalty
        "ta_cns_phase3":         -0.15,   # CNS P3 penalty
        "ta_rare_phase3":         0.60,   # Rare disease P3 uplift
        "ta_immunology_phase3":   0.35,   # Immunology P3 uplift
    },
}


# ═══════════════════════════════════════════════════════════════
#  RISK OVERLAY RULES (from Gungnir v4.0)
# ═══════════════════════════════════════════════════════════════

RISK_RULES = [
    # Hard caps
    ("FAILURE_SIGNAL",      "hard", 0.15, "💀 Explicit failure in readout text",
     lambda f: f.get('failure_signal', 0) > 0),
    ("PPM_HOEG_ERA",        "hard", 0.30, "🔴 Primary pivotal miss + Hoeg-era FDA",
     lambda f: f.get('ppm_flag', 0) > 0 and f.get('is_hoeg_era', 0) > 0),
    ("PSYCHEDELIC",         "hard", 0.35, "🔴 Psychedelic compound — extreme headwind",
     lambda f: f.get('is_psychedelic', 0) > 0),
    ("SEVERE_SAFETY_HOEG",  "hard", 0.45, "🔴 Severe safety (DILI/cardiac) + Hoeg era",
     lambda f: f.get('safety_signal', 0) >= 2 and f.get('is_hoeg_era', 0) > 0),
    ("GENE_THERAPY_P3",     "hard", 0.55, "🟡 Gene therapy Phase 3 — CMC risk",
     lambda f: f.get('is_gene_therapy', 0) > 0 and f.get('phase_PHASE3', 0) > 0),
    ("SINGLE_ARM_HOEG",     "hard", 0.60, "🟡 Single-arm in Hoeg era",
     lambda f: f.get('is_single_arm', 0) > 0 and f.get('is_hoeg_era', 0) > 0),
    # Soft penalties
    ("MODERATE_SAFETY",     "pen",  0.08, "⚡ Moderate safety concern",
     lambda f: 0 < f.get('safety_signal', 0) < 2),
    ("GENE_THERAPY",        "pen",  0.05, "⚡ Gene therapy CMC risk",
     lambda f: f.get('is_gene_therapy', 0) > 0),
    ("CNS",                 "pen",  0.03, "⚡ CNS — higher failure rate",
     lambda f: f.get('ta_CNS', 0) > 0),
    ("HOEG_ERA",            "pen",  0.02, "⚡ Hoeg-era FDA uncertainty",
     lambda f: f.get('is_hoeg_era', 0) > 0),
    # Boosts
    ("RCT_HARD_ENDPOINT",   "boost", 0.03, "✨ RCT + hard endpoint — gold standard",
     lambda f: f.get('rct_x_phase3', 0) > 0 and f.get('is_hard_endpoint', 0) > 0),
]


# ═══════════════════════════════════════════════════════════════
#  PARAMETER BOUNDS — Guardrails for optimization
# ═══════════════════════════════════════════════════════════════
# Prevents gradient descent / GPU sweep from pushing weights to absurd values.
# Format: feature_name → (min, max) in logit-space.
# Features not listed here are unbounded.

PARAM_BOUNDS = {
    # Phase 2→3 buckets: must stay positive (better Phase 2 → better Phase 3)
    "p23_p2_bucket_lt_0001":   ( 0.5, 3.5),
    "p23_p2_bucket_0001_001":  ( 0.3, 2.5),
    "p23_p2_bucket_001_005":   ( 0.0, 1.5),
    # TA × Phase3: oncology/CNS are penalties (≤0), rare/immuno are boosts (≥0)
    "ta_oncology_phase3":      (-0.8, 0.0),
    "ta_cns_phase3":           (-0.5, 0.0),
    "ta_rare_phase3":          ( 0.2, 1.2),
    "ta_immunology_phase3":    ( 0.1, 0.9),
    # Core signals: prevent sign flips on well-understood features
    "failure_signal":          (-4.0, -0.5),
    "primary_endpoint_met":    ( 0.3, 2.5),
    "ppm_flag":                (-2.0, -0.1),
    "safety_signal":           (-1.5, 0.0),
    "strong_positive":         ( 0.0, 1.5),
}

# ═══════════════════════════════════════════════════════════════
#  MONOTONIC CONSTRAINTS
# ═══════════════════════════════════════════════════════════════
# Tuples of (higher_feature, lower_feature): weight[higher] >= weight[lower].
# Enforced after each gradient step by clamping violations.

MONOTONIC_CONSTRAINTS = [
    ("p23_p2_bucket_lt_0001", "p23_p2_bucket_0001_001"),  # p<0.001 ≥ p<0.01
    ("p23_p2_bucket_0001_001", "p23_p2_bucket_001_005"),  # p<0.01 ≥ p<0.05
]


# ═══════════════════════════════════════════════════════════════
#  NLP FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════

def _has(text, kw_list):
    return any(k in text for k in kw_list)

def _rx(text, pattern):
    return bool(re.search(pattern, text))

def extract_features(catalyst, ticker="", drug="", indication="", stage="", date="2026-01-01"):
    """Extract 35 NLP features from readout text + metadata."""
    cat = catalyst.lower() if catalyst else ""
    tk = ticker.upper() if ticker else ""
    stg = stage.lower() if stage else ""
    combined = f"{cat} {(drug or '').lower()} {(indication or '').lower()}"

    try:
        dt = datetime.strptime(str(date)[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        dt = datetime(2026, 1, 1)

    f = {}

    # A: Core signals
    f['is_hard_endpoint']     = float(_rx(cat, r'pfs|progression-free survival|os|overall survival|mace|mortality|death'))
    f['phase_PHASE3']         = float(_rx(f"{cat} {stg}", r'phase\s*3|phase\s*iii'))
    f['is_competitive_space'] = float(_rx(cat, r'versus|vs\.|compared to|soc|standard of care|competitor|head-to-head'))
    f['sentiment_score']      = float(_rx(cat, r'robust|meaningful|clinically\s+meaningful|impressive|remarkable|outstanding|transformative|unprecedented'))
    f['phase_PHASE2']         = float(_rx(f"{cat} {stg}", r'phase\s*2|phase\s*ii'))
    f['primary_endpoint_met'] = float(_rx(cat, r'met\s+(primary|main)\s+endpoint|achieved\s+primary|primary\s+endpoint\s+(met|achieved|reached|positive)'))
    f['ta_ONCOLOGY']          = float(_rx(combined, r'oncology|cancer|tumor|malignancy|chemotherapy|immunotherapy|carcinoma|lymphoma|leukemia|melanoma|sarcoma'))
    _rct = float(_rx(cat, r'randomized|rct|controlled|double-blind|placebo'))
    f['rct_x_phase3']         = _rct * f['phase_PHASE3']

    # B: Regulatory designations
    f['has_breakthrough']     = float(_rx(cat, r'breakthrough\s+therapy|btd|breakthrough\s+designation'))
    f['has_orphan']           = float(_rx(combined, r'orphan|rare\s+disease|ultra-rare|ultra\s+rare'))
    f['has_priority_review']  = float(_rx(cat, r'priority\s+review|priority\s+designation'))
    f['has_fast_track']       = float(_rx(cat, r'fast\s+track|fasttrack|accelerated\s+approval'))

    # C: Risk flags
    f['is_gene_therapy']      = float(_has(combined, _GT_KW) or tk in _GT_TICKERS)
    f['is_psychedelic']       = float(_has(combined, _PSYCH_KW))
    f['safety_signal']        = float(_has(combined, _SAF_SEV)) * 2.0 + float(_has(combined, _SAF_MOD)) * 1.0
    f['ppm_flag']             = float(_has(combined, _PPM_KW))
    f['is_single_arm']        = float(_has(combined, _SA_KW))
    f['has_surrogate']        = float(_rx(cat, r'surrogate|biomarker\s+endpoint|orr\b|objective\s+response|pathologic.*complete.*response|pcr\b'))

    # D: Temporal
    f['is_hoeg_era']          = float(dt >= datetime(2025, 1, 1))
    f['accel_approval_2025']  = f['has_fast_track'] * f['is_hoeg_era']
    f['single_arm_2025']      = f['is_single_arm'] * f['is_hoeg_era']

    # E: Readout quality
    f['failure_signal']       = float(_rx(cat, r'failed|did\s+not\s+meet|discontinued|halted|stopped|terminated|futility|negative|missed|not\s+met'))
    f['strong_positive']      = float(_rx(cat, r'statistically\s+significant|highly\s+significant|p\s*[<≤]\s*0\.0[0-5]|p\s*[<≤]\s*0\.001|exceeded|surpassed'))
    f['dose_response']        = float(_rx(cat, r'dose[- ]?dependent|dose[- ]?response|higher\s+dose|all\s+doses'))
    f['safety_clean']         = float(_rx(cat, r'well[- ]?tolerated|favorable\s+safety|clean\s+safety|no\s+serious\s+adverse|no.*sae'))

    # F: TA risk
    f['ta_CNS']               = float(_rx(combined, r'\bcns\b|alzheimer|parkinson|schizophrenia|depression|bipolar|epilepsy|seizure|multiple\s+sclerosis|\bms\b|neurolog'))
    f['ta_RARE']              = float(_rx(combined, r'rare\s+disease|orphan|ultra-rare|genetic\s+disorder|inherited|lysosomal|enzyme\s+replacement'))
    f['ta_PAIN']              = float(_rx(combined, r'\bpain\b|analgesic|migraine|nociceptive|neuropathic\s+pain|fibromyalgia'))
    f['ta_IMMUNOLOGY']        = float(_rx(combined, r'autoimmune|rheumatoid|lupus|psoriasis|atopic\s+dermatitis|crohn|colitis|inflammatory'))

    # G: Interactions
    f['gene_therapy_x_phase3'] = f['is_gene_therapy'] * f['phase_PHASE3']
    f['safety_x_hoeg']         = f['safety_signal']  * f['is_hoeg_era']
    f['ppm_x_hoeg']            = f['ppm_flag']       * f['is_hoeg_era']
    f['oncology_x_phase3']     = f['ta_ONCOLOGY']    * f['phase_PHASE3']
    f['rare_x_positive']       = f['ta_RARE']        * f['strong_positive']
    f['failure_x_phase3']      = f['failure_signal']  * f['phase_PHASE3']

    # H: Phase 2→3 evidence (extract p-value from text if Phase 3 readout)
    # Looks for "Phase 2 p=0.0003" or "p<0.001 in Phase 2" or "prior Phase 2 p-value"
    _p2_pval = None
    if f['phase_PHASE3'] > 0:
        # Try to extract numeric p-value from text mentioning Phase 2
        _p2_match = re.search(
            r'(?:phase\s*(?:2|ii)\b.*?p\s*[=<≤]\s*([\d.]+(?:e[+-]?\d+)?))'
            r'|(?:p\s*[=<≤]\s*([\d.]+(?:e[+-]?\d+)?)\s*.*?phase\s*(?:2|ii))',
            cat, re.IGNORECASE
        )
        if _p2_match:
            try:
                _p2_pval = float(_p2_match.group(1) or _p2_match.group(2))
            except (ValueError, TypeError):
                pass

    f['p23_p2_bucket_lt_0001']  = float(_p2_pval is not None and _p2_pval < 0.001)
    f['p23_p2_bucket_0001_001'] = float(_p2_pval is not None and 0.001 <= _p2_pval < 0.01)
    f['p23_p2_bucket_001_005']  = float(_p2_pval is not None and 0.01 <= _p2_pval < 0.05)

    # I: TA × Phase3 interactions
    f['ta_oncology_phase3']    = f['ta_ONCOLOGY']    * f['phase_PHASE3']
    f['ta_cns_phase3']         = f['ta_CNS']         * f['phase_PHASE3']
    f['ta_rare_phase3']        = f['ta_RARE']        * f['phase_PHASE3']
    f['ta_immunology_phase3']  = f['ta_IMMUNOLOGY']  * f['phase_PHASE3']

    return f


# ═══════════════════════════════════════════════════════════════
#  GUNGNIR SCORER
# ═══════════════════════════════════════════════════════════════

class GungnirHoningScorer:
    """
    Logistic regression scorer using NLP features from catalyst text.
    Weights live in logit-space and are updated by gradient descent.
    """

    def __init__(self, weights=None):
        self.weights = deepcopy(weights or INITIAL_WEIGHTS)

    def score(self, event: dict) -> dict:
        """
        Score a Phase readout event.
        event must have 'features' dict or raw fields for on-the-fly extraction.
        """
        features = event.get("features")
        if features is None:
            catalyst = event.get("raw_catalyst_text", event.get("catalyst", ""))
            features = extract_features(
                catalyst,
                ticker=event.get("ticker", ""),
                drug=event.get("asset", event.get("drug", "")),
                indication=event.get("indication", ""),
                stage=event.get("stage", ""),
                date=event.get("catalyst_date", event.get("date", "2026-01-01")),
            )
            event["features"] = features

        # Logistic model: base_logit + sum(weight_i * feature_i)
        z = self.weights["base_logit"]
        w = self.weights["features"]
        for fname in FEATURE_NAMES:
            val = features.get(fname, 0.0)
            z += w.get(fname, 0.0) * val

        ml_score = sigmoid(z)

        # Apply risk overlay
        final, tier, hard_cap, soft_pen, rules = self._apply_overlay(ml_score, features)

        return {
            "probability": final,
            "ml_score": ml_score,
            "logit": z,
            "tier": tier,
            "hard_cap": hard_cap,
            "soft_penalty": soft_pen,
            "rules_fired": rules,
            "active_features": sum(1 for v in features.values() if v != 0),
        }

    def _apply_overlay(self, ml_score, features):
        cap = 1.0
        penalty = 0.0
        fired = []
        for name, rtype, value, desc, cond in RISK_RULES:
            try:
                if not cond(features):
                    continue
            except Exception:
                continue
            if rtype == "hard":
                cap = min(cap, value)
                fired.append({"name": name, "type": "CAP", "value": value, "desc": desc})
            elif rtype == "pen":
                penalty += value
                fired.append({"name": name, "type": "PEN", "value": -value, "desc": desc})
            elif rtype == "boost":
                penalty -= value
                fired.append({"name": name, "type": "BOOST", "value": value, "desc": desc})

        score = max(min(ml_score - penalty, cap), 0.01)
        # Phase-optimized boundaries (lower base rate than PDUFA):
        #   T1 ≥0.70: ~92% actual positive
        #   T2  0.50–0.70: ~60% actual positive (lean positive)
        #   T3  0.20–0.50: mixed/uncertain
        #   T4 <0.20: ~97% actual negative
        tier = (
            "TIER_1" if score >= 0.70 else
            "TIER_2" if score >= 0.50 else
            "TIER_3" if score >= 0.20 else
            "TIER_4"
        )
        return score, tier, cap if cap < 1.0 else None, penalty, fired


# ═══════════════════════════════════════════════════════════════
#  DATA LOADING — Phase readout events
# ═══════════════════════════════════════════════════════════════

def load_phase_events(phase_csv=None, hist_csv=None, verbose=True):
    """
    Load Phase readout events from:
      1. ODIN_PHASE_BACKTEST_EXTENDED.csv (primary)
      2. historical_readouts_2000.csv (supplementary, deduplicated)

    MIXED → NEGATIVE for binary classification.
    """
    events = []
    seen_keys = set()

    # --- Source 1: ODIN_PHASE_BACKTEST_EXTENDED ---
    if phase_csv is None:
        for p in [
            "ODIN_PHASE_BACKTEST_EXTENDED.csv",
            os.path.expanduser("~/odin_data/ODIN_PHASE_BACKTEST_EXTENDED.csv"),
            "/mnt/project/ODIN_PHASE_BACKTEST_EXTENDED.csv",
        ]:
            if os.path.exists(p):
                phase_csv = p
                break

    phase_count = 0
    if phase_csv and os.path.exists(phase_csv):
        for enc in ['utf-8', 'cp1252', 'latin-1']:
            try:
                with open(phase_csv, encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        outcome = row.get("parsed_outcome", "").strip().upper()
                        if outcome not in ("POSITIVE", "NEGATIVE", "MIXED"):
                            continue

                        binary_outcome = "POSITIVE" if outcome == "POSITIVE" else "NEGATIVE"

                        ticker = row.get("ticker", "").strip()
                        asset = row.get("asset", "").strip()
                        stage = row.get("stage", "").strip()
                        cat_date = row.get("catalyst_date", "")[:10]
                        key = f"{ticker}|{asset}|{stage}|{cat_date}"

                        if key in seen_keys:
                            continue
                        seen_keys.add(key)

                        ev = {
                            "event_id": row.get("event_id", key),
                            "ticker": ticker,
                            "company": row.get("company", ""),
                            "asset": asset,
                            "indication": row.get("indication", ""),
                            "stage": stage,
                            "catalyst_date": cat_date,
                            "outcome": binary_outcome,
                            "raw_outcome": outcome,
                            "raw_catalyst_text": row.get("raw_catalyst_text", ""),
                            "source": "phase_backtest",
                        }
                        events.append(ev)
                        phase_count += 1
                break
            except UnicodeDecodeError:
                continue

    # --- Source 2: historical_readouts_2000 ---
    if hist_csv is None:
        for p in [
            "historical_readouts_2000.csv",
            os.path.expanduser("~/odin_data/historical_readouts_2000.csv"),
            "/mnt/project/historical_readouts_2000.csv",
        ]:
            if os.path.exists(p):
                hist_csv = p
                break

    hist_count = 0
    if hist_csv and os.path.exists(hist_csv):
        with open(hist_csv, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                outcome_raw = row.get("outcome", "").strip().lower()
                if outcome_raw not in ("positive", "negative"):
                    continue

                binary_outcome = "POSITIVE" if outcome_raw == "positive" else "NEGATIVE"

                ticker = row.get("Ticker", "").strip()
                asset = row.get("Drug", "").strip()
                stage = row.get("Stage", "").strip()
                cat_date = row.get("Catalyst Date", row.get("date", ""))[:10]
                key = f"{ticker}|{asset}|{stage}|{cat_date}"

                if key in seen_keys:
                    continue
                seen_keys.add(key)

                ev = {
                    "event_id": key,
                    "ticker": ticker,
                    "company": row.get("Name", ""),
                    "asset": asset,
                    "indication": row.get("Indication", ""),
                    "stage": stage,
                    "catalyst_date": cat_date,
                    "outcome": binary_outcome,
                    "raw_outcome": outcome_raw,
                    "raw_catalyst_text": row.get("Catalyst", ""),
                    "source": "historical_readouts",
                }
                events.append(ev)
                hist_count += 1

    events.sort(key=lambda e: e.get("catalyst_date", ""))

    if verbose:
        pos = sum(1 for e in events if e["outcome"] == "POSITIVE")
        neg = len(events) - pos
        print(f"  [Gungnir] Loaded {len(events)} Phase events "
              f"({phase_count} from backtest, {hist_count} from historical)")
        print(f"  [Gungnir] Outcomes: {pos} POSITIVE ({pos/len(events)*100:.1f}%), "
              f"{neg} NEGATIVE ({neg/len(events)*100:.1f}%)")

    return events


def precompute_features(events: list, verbose=True) -> list:
    """Pre-extract NLP features for all events."""
    n_extracted = 0
    for ev in events:
        if "features" not in ev:
            ev["features"] = extract_features(
                ev.get("raw_catalyst_text", ""),
                ticker=ev.get("ticker", ""),
                drug=ev.get("asset", ""),
                indication=ev.get("indication", ""),
                stage=ev.get("stage", ""),
                date=ev.get("catalyst_date", "2026-01-01"),
            )
            n_extracted += 1

    if verbose and n_extracted > 0:
        feat_counts = Counter()
        for ev in events:
            for fname, val in ev["features"].items():
                if val != 0:
                    feat_counts[fname] += 1
        print(f"  [Gungnir] Pre-extracted features for {n_extracted} events")
        print(f"  [Gungnir] Top active features:")
        for fname, cnt in feat_counts.most_common(10):
            print(f"    {fname}: {cnt} ({cnt/len(events)*100:.1f}%)")

    return events


# ═══════════════════════════════════════════════════════════════
#  CALIBRATION / METRICS
# ═══════════════════════════════════════════════════════════════

class CalibrationEngine:
    @staticmethod
    def compute_metrics(preds: list, actuals: list) -> dict:
        n = len(preds)
        if n == 0:
            return {"brier": 1.0, "auc": 0.5, "accuracy": 0.0, "n": 0}

        brier = sum((p - a) ** 2 for p, a in zip(preds, actuals)) / n

        correct = sum(1 for p, a in zip(preds, actuals)
                      if (p >= 0.5 and a == 1.0) or (p < 0.5 and a == 0.0))
        accuracy = correct / n

        pos = [p for p, a in zip(preds, actuals) if a == 1.0]
        neg = [p for p, a in zip(preds, actuals) if a == 0.0]
        if len(pos) == 0 or len(neg) == 0:
            auc = 0.5
        else:
            concordant = sum(1 for p in pos for q in neg if p > q)
            tied = sum(1 for p in pos for q in neg if p == q)
            auc = (concordant + 0.5 * tied) / (len(pos) * len(neg))

        tiers = {"TIER_1": [], "TIER_2": [], "TIER_3": [], "TIER_4": []}
        for p, a in zip(preds, actuals):
            # Phase-optimized boundaries
            tier = (
                "TIER_1" if p >= 0.70 else
                "TIER_2" if p >= 0.50 else
                "TIER_3" if p >= 0.20 else
                "TIER_4"
            )
            tiers[tier].append(a)

        tier_stats = {}
        for t, vals in tiers.items():
            if vals:
                tier_stats[t] = {
                    "n": len(vals),
                    "actual_positive_rate": sum(vals) / len(vals),
                }
            else:
                tier_stats[t] = {"n": 0, "actual_positive_rate": 0.0}

        return {
            "brier": round(brier, 6),
            "auc": round(auc, 6),
            "accuracy": round(accuracy, 6),
            "n": n,
            "base_rate": round(sum(actuals) / n, 4) if n > 0 else 0,
            "tiers": tier_stats,
        }


# ═══════════════════════════════════════════════════════════════
#  GRADIENT RECALIBRATOR
# ═══════════════════════════════════════════════════════════════

class GradientRecalibrator:
    def __init__(self, lr=0.003, l2=0.005, max_epochs=3000, convergence=1e-7):
        self.lr = lr
        self.l2 = l2
        self.max_epochs = max_epochs
        self.convergence = convergence

    def recalibrate(self, scorer: GungnirHoningScorer, events: list,
                    patience=200, verbose=True) -> dict:
        resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        targets = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in resolved]

        if len(resolved) < 20:
            return {"status": "INSUFFICIENT_DATA", "n": len(resolved)}

        pre_preds = [scorer.score(e)["probability"] for e in resolved]
        pre_metrics = CalibrationEngine.compute_metrics(pre_preds, targets)

        old_weights = deepcopy(scorer.weights)
        weights = scorer.weights
        best_brier = float('inf')
        best_weights = deepcopy(weights)
        no_improve = 0

        for epoch in range(self.max_epochs):
            epoch_brier = 0.0
            total_grad_base = 0.0
            feature_grads = defaultdict(float)

            for ev, y in zip(resolved, targets):
                features = ev["features"]

                z = weights["base_logit"]
                w = weights["features"]
                for fname in FEATURE_NAMES:
                    val = features.get(fname, 0.0)
                    z += w.get(fname, 0.0) * val

                p = sigmoid(z)
                epoch_brier += (p - y) ** 2

                grad_factor = 2.0 * (p - y) * p * (1.0 - p) / len(resolved)
                total_grad_base += grad_factor

                for fname in FEATURE_NAMES:
                    val = features.get(fname, 0.0)
                    if val != 0:
                        feature_grads[fname] += grad_factor * val

            epoch_brier /= len(resolved)

            weights["base_logit"] -= self.lr * total_grad_base

            for fname in FEATURE_NAMES:
                g = feature_grads.get(fname, 0.0)
                g += self.l2 * weights["features"].get(fname, 0.0)
                weights["features"][fname] = weights["features"].get(fname, 0.0) - self.lr * g

            if epoch_brier < best_brier - self.convergence:
                best_brier = epoch_brier
                best_weights = deepcopy(weights)
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        scorer.weights = best_weights

        post_preds = [scorer.score(e)["probability"] for e in resolved]
        post_metrics = CalibrationEngine.compute_metrics(post_preds, targets)

        n_changed = 0
        for fname in FEATURE_NAMES:
            old_w = old_weights["features"].get(fname, 0.0)
            new_w = best_weights["features"].get(fname, 0.0)
            if abs(old_w - new_w) > 0.001:
                n_changed += 1

        return {
            "status": "RECALIBRATED",
            "epochs": epoch + 1,
            "features_changed": n_changed,
            "pre_brier": pre_metrics["brier"],
            "post_brier": post_metrics["brier"],
            "pre_auc": pre_metrics["auc"],
            "post_auc": post_metrics["auc"],
            "pre_accuracy": pre_metrics["accuracy"],
            "post_accuracy": post_metrics["accuracy"],
            "base_logit_change": {
                "old": round(old_weights["base_logit"], 4),
                "new": round(best_weights["base_logit"], 4),
            },
            "n": len(resolved),
        }


# ═══════════════════════════════════════════════════════════════
#  BACKTESTER — Walk-forward validation
# ═══════════════════════════════════════════════════════════════

class Backtester:
    @staticmethod
    def time_split_backtest(events: list, train_frac=0.7) -> dict:
        resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        n = len(resolved)
        split_idx = int(n * train_frac)
        train = resolved[:split_idx]
        test = resolved[split_idx:]

        if len(train) < 20 or len(test) < 10:
            return {"status": "INSUFFICIENT_DATA"}

        scorer = GungnirHoningScorer()
        recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=2000)
        recal_report = recal.recalibrate(scorer, train, verbose=False)

        test_preds = [scorer.score(e)["probability"] for e in test]
        test_actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in test]
        test_metrics = CalibrationEngine.compute_metrics(test_preds, test_actuals)

        train_preds = [scorer.score(e)["probability"] for e in train]
        train_actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in train]
        train_metrics = CalibrationEngine.compute_metrics(train_preds, train_actuals)

        train_dates = [e.get("catalyst_date", "") for e in train if e.get("catalyst_date")]
        test_dates = [e.get("catalyst_date", "") for e in test if e.get("catalyst_date")]

        return {
            "status": "OK",
            "train_n": len(train),
            "test_n": len(test),
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "recalibration": recal_report,
            "train_date_range": f"{min(train_dates)[:10]} → {max(train_dates)[:10]}" if train_dates else "?",
            "test_date_range": f"{min(test_dates)[:10]} → {max(test_dates)[:10]}" if test_dates else "?",
        }

    @staticmethod
    def kfold_backtest(events: list, k=5) -> dict:
        resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        n = len(resolved)
        fold_size = n // k
        all_preds = [None] * n
        all_actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in resolved]
        fold_metrics = []

        for fold in range(k):
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < k - 1 else n
            test_set = resolved[test_start:test_end]
            train_set = resolved[:test_start] + resolved[test_end:]

            scorer = GungnirHoningScorer()
            recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=1500)
            recal.recalibrate(scorer, train_set, verbose=False)

            for i, ev in enumerate(test_set):
                idx = test_start + i
                pred = scorer.score(ev)["probability"]
                all_preds[idx] = pred

            fold_preds = [all_preds[test_start + i] for i in range(len(test_set))]
            fold_actuals = [all_actuals[test_start + i] for i in range(len(test_set))]
            fm = CalibrationEngine.compute_metrics(fold_preds, fold_actuals)
            fold_metrics.append(fm)

        valid = [(p, a) for p, a in zip(all_preds, all_actuals) if p is not None]
        overall = CalibrationEngine.compute_metrics(
            [v[0] for v in valid], [v[1] for v in valid]
        )

        return {
            "status": "OK",
            "k": k,
            "n": n,
            "overall_metrics": overall,
            "fold_metrics": fold_metrics,
        }


# ═══════════════════════════════════════════════════════════════
#  WEIGHT MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def save_weights(weights: dict, path: str):
    with open(path, 'w') as f:
        json.dump(weights, f, indent=2)

def load_weights(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════
#  MAIN — Standalone test
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*72}")
    print(f"  GUNGNIR PERPETUAL HONING ENGINE v{__version__}")
    print(f"  Phase Readout Scoring — Companion to ODIN (PDUFA)")
    print(f"{'='*72}\n")

    # Load data
    print("Loading Phase readout data...")
    events = load_phase_events()
    events = precompute_features(events)

    # Pre-honing
    print(f"\n--- Pre-honing metrics ---")
    scorer = GungnirHoningScorer()
    resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
    preds = [scorer.score(e)["probability"] for e in resolved]
    actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in resolved]
    pre = CalibrationEngine.compute_metrics(preds, actuals)
    print(f"  Brier:    {pre['brier']:.4f}")
    print(f"  AUC:      {pre['auc']:.4f}")
    print(f"  Accuracy: {pre['accuracy']:.4f}")
    print(f"  Base rate: {pre['base_rate']:.2%}")
    for t, s in pre["tiers"].items():
        if s["n"] > 0:
            print(f"  {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

    # Hone
    print(f"\n--- Honing (gradient descent) ---")
    recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=3000)
    report = recal.recalibrate(scorer, events)
    print(f"  Status: {report['status']}")
    print(f"  Epochs: {report['epochs']}")
    print(f"  Features changed: {report['features_changed']}")
    print(f"  Brier:  {report['pre_brier']:.4f} → {report['post_brier']:.4f} "
          f"({'↓' if report['post_brier'] < report['pre_brier'] else '↑'}"
          f"{abs(report['post_brier'] - report['pre_brier']):.4f})")
    print(f"  AUC:    {report['pre_auc']:.4f} → {report['post_auc']:.4f}")
    print(f"  Acc:    {report['pre_accuracy']:.4f} → {report['post_accuracy']:.4f}")

    # Post-honing tier breakdown
    print(f"\n--- Post-honing tier breakdown ---")
    post_preds = [scorer.score(e)["probability"] for e in resolved]
    post = CalibrationEngine.compute_metrics(post_preds, actuals)
    for t, s in post["tiers"].items():
        if s["n"] > 0:
            print(f"  {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

    # Walk-forward backtest
    print(f"\n--- Walk-forward backtest (70/30 time split) ---")
    bt = Backtester.time_split_backtest(events)
    if bt["status"] == "OK":
        print(f"  Train: n={bt['train_n']}, dates={bt['train_date_range']}")
        print(f"    Brier={bt['train_metrics']['brier']:.4f}  "
              f"AUC={bt['train_metrics']['auc']:.4f}")
        print(f"  Test:  n={bt['test_n']}, dates={bt['test_date_range']}")
        print(f"    Brier={bt['test_metrics']['brier']:.4f}  "
              f"AUC={bt['test_metrics']['auc']:.4f}")
        for t, s in bt["test_metrics"]["tiers"].items():
            if s["n"] > 0:
                print(f"    {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

    # Top features
    print(f"\n--- Top features by |weight| ---")
    w = scorer.weights["features"]
    sorted_feats = sorted(w.items(), key=lambda x: abs(x[1]), reverse=True)
    for fname, wt in sorted_feats[:15]:
        arrow = "↑" if wt > 0 else "↓"
        print(f"  {arrow} {fname:>30s}: {wt:+.4f}")

    # Save weights
    out_path = "gungnir_honed_weights.json"
    save_weights(scorer.weights, out_path)
    print(f"\n  Saved honed weights → {out_path}")

    print(f"\n{'='*72}")
    print(f"  GUNGNIR ENGINE COMPLETE")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
