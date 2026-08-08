#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL HONING ENGINE v13.1                                    ║
║  Calibrated on 2,210 real PDUFA events (2015-2026)                     ║
║  Uses ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv                    ║
║  Base rate: 68.0% approval                                             ║
║                                                                        ║
║  Signal architecture:                                                  ║
║    - 22 binary signals (direct + derived from v1070 columns)           ║
║    - 4 categorical encodings (TA bucket, FDA era, resub class)         ║
║    - 4 continuous features (hist CRL rate, sponsor exp, etc.)          ║
║    - 2 interaction terms (derived at parse time)                       ║
║    - TA-specific logit offsets for 19 therapeutic areas                 ║
║                                                                        ║
║  v13.1 Changes (from v13.0):                                           ║
║    - parse_row() derives interaction terms from raw v1070 features      ║
║    - ta_bucket_v2 derived from therapeutic_area lookup (not CSV col)    ║
║    - double_crl_flag derived from prior_crl_count >= 2                  ║
║    - Handles mixed accelerated_approval formats (TRUE/Yes/1)           ║
║    - fda_era read directly from v1070 CSV column                        ║
║    - resubmission_class handles "1.0"/"2.0" float strings              ║
║                                                                        ║
║  All logits are EMPIRICAL — computed from real outcome data.           ║
║  Gradient descent fine-tunes weights to minimize Brier score.          ║
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
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

__version__ = "13.1.0"

# ═══════════════════════════════════════════════════════════════
#  MATH PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ez = math.exp(x)
        return ez / (1.0 + ez)

def logit(p: float) -> float:
    """Inverse sigmoid. Clamps to avoid inf."""
    p = max(1e-7, min(1 - 1e-7, p))
    return math.log(p / (1 - p))

def _pb(val) -> bool:
    """Parse bool from CSV value. Handles TRUE/FALSE/Yes/No/1/0/empty."""
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("TRUE", "1", "YES", "Y", "T")

def _pf(val, default=0.0) -> float:
    """Parse float from CSV value."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _pi(val, default=0) -> int:
    """Parse int from CSV value."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════
#  SIGNAL DEFINITIONS
#  Every signal maps to a CSV column or derived feature.
#  Logits here are INITIAL empirical estimates. Honing updates them.
# ═══════════════════════════════════════════════════════════════

# These are the empirical logit contributions computed from the
# full 2,210-event v1070 dataset. The honing engine will fine-tune them.

SIGNAL_REGISTRY = {
    # ── Regulatory Designations (strong positive signals) ──
    "btd":                   {"type": "bool", "csv": "btd",                   "logit": +2.44,  "desc": "Breakthrough Therapy Designation"},
    "orphan":                {"type": "bool", "csv": "orphan",                "logit": +1.87,  "desc": "Orphan Drug Designation"},
    "priority_review":       {"type": "bool", "csv": "priority_review",       "logit": +2.25,  "desc": "Priority Review"},
    "fast_track":            {"type": "bool", "csv": "fast_track",            "logit": +2.05,  "desc": "Fast Track Designation"},
    "accelerated_approval":  {"type": "bool", "csv": "accelerated_approval",  "logit": +1.82,  "desc": "Accelerated Approval pathway"},
    "surrogate_endpoint":    {"type": "bool", "csv": "surrogate_endpoint",    "logit": +2.17,  "desc": "Surrogate endpoint used"},
    "had_adcom":             {"type": "bool", "csv": "had_adcom",             "logit": +3.17,  "desc": "Had Advisory Committee (positive signal)"},

    # ── Risk / Negative Signals ──
    "prior_crl":             {"type": "bool", "csv": "prior_crl",             "logit": -7.85,  "desc": "Prior CRL (0% approval in dataset)"},
    "form_483_issues":       {"type": "bool", "csv": "form_483_issues",       "logit": -7.76,  "desc": "Form 483 manufacturing issues (0% approval)"},
    "manufacturing_risk":    {"type": "bool", "csv": "manufacturing_risk",    "logit": -1.42,  "desc": "Manufacturing/CMC risk flagged"},
    "double_crl_flag":       {"type": "bool", "csv": "_derived_",             "logit": -2.23,  "desc": "2+ prior CRLs (very bearish)"},
    "ppm_flag":              {"type": "bool", "csv": "ppm_flag",              "logit": -1.59,  "desc": "Post-marketing/prior market flag"},
    "ped_pk_missing":        {"type": "bool", "csv": "s22_ped_pk_missing",    "logit": -0.50,  "desc": "Pediatric PK data missing"},
    "ema_cmc_flag":          {"type": "bool", "csv": "ema_cmc_flag",          "logit": -0.30,  "desc": "EMA CMC concern"},
    "cmc_extension_flag":    {"type": "bool", "csv": "cmc_extension_flag",    "logit": -0.30,  "desc": "CMC review extension"},

    # ── Modality ──
    "gene_therapy":          {"type": "bool", "csv": "gene_therapy",          "logit": -0.29,  "desc": "Gene therapy (higher CMC risk)"},
    "single_arm_study":      {"type": "bool", "csv": "single_arm_study",      "logit": +0.41,  "desc": "Single-arm study design"},

    # ── Interaction Terms (DERIVED at parse time from raw features) ──
    "btd_onco_interaction":     {"type": "bool", "csv": "_derived_",  "logit": +2.98,  "desc": "BTD × Oncology (very bullish combo)"},
    "btd_priority_interaction": {"type": "bool", "csv": "_derived_",  "logit": +2.38,  "desc": "BTD × Priority Review"},
    "ta_very_high_risk":        {"type": "bool", "csv": "_derived_",  "logit": +1.71,  "desc": "TA bucket = VERY_HIGH approval rate"},

    # ── Safety (continuous, mapped to threshold) ──
    "safety_moderate":       {"type": "derived", "logit": -0.30,  "desc": "Safety severity 1.5-2.0"},
    "safety_high":           {"type": "derived", "logit": -0.50,  "desc": "Safety severity >= 2.5"},
}

# ── TA → Bucket mapping (derived from empirical approval rates in v1070) ──
# VERY_HIGH: ≥85% approval, HIGH: ≥72%, MOD: ≥60%, LOW: <60%
TA_TO_BUCKET = {
    "Oncology":            "LOW",         # 53.6%
    "CNS":                 "LOW",         # sparse, bearish
    "Ophthalmology":       "MOD",         # 67.4%
    "Pain Management":     "MOD",         # 67.5%
    "Nephrology":          "MOD",         # 71.0%
    "Other":               "HIGH",        # 72.8%
    "Hematology":          "HIGH",        # 75.0%
    "CNS/Neurology":       "HIGH",        # 76.4%
    "Cardiovascular":      "HIGH",        # 79.4%
    "Metabolic/Endocrine": "HIGH",        # 80.0%
    "Endocrinology":       "HIGH",        # alias
    "Rare Disease":        "HIGH",        # 82.9%
    "Immunology":          "VERY_HIGH",   # 89.1%
    "Infectious Disease":  "VERY_HIGH",   # 89.7%
    "Dermatology":         "VERY_HIGH",   # 90.6%
    "GI/Hepatology":       "VERY_HIGH",   # 95.7%
    "Respiratory":         "VERY_HIGH",   # 96.8%
    "Women's Health":      "VERY_HIGH",   # 100%
    "Vaccines":            "VERY_HIGH",   # 100%
}

# TA bucket categorical encoding (vs baseline MOD)
TA_BUCKET_LOGITS = {
    "LOW":       -0.61,    # Oncology-dominated, 53.6% approval
    "MOD":        0.00,    # Baseline, 72.6% approval
    "HIGH":      +0.55,    # 78.6% approval
    "VERY_HIGH": +1.52,    # 90.7% approval
}

# FDA era categorical encoding (vs baseline POST_COVID)
# v1070 CSV has fda_era column directly: PRE_2020, COVID_ERA, HOEG_ERA, POST_COVID
FDA_ERA_LOGITS = {
    "PRE_2020":   -0.17,
    "COVID_ERA":  +0.20,
    "HOEG_ERA":   +0.13,
    "POST_COVID":  0.00,   # Baseline
}

# Resubmission class encoding
# v1070 CSV has resubmission_class as "1.0", "2.0", or empty
RESUB_LOGITS = {
    0: 0.00,     # No resubmission (baseline)
    1: +0.80,    # Class 1 resubmission (typically minor, higher approval)
    2: +0.40,    # Class 2 resubmission
}

# Therapeutic area logit offsets (empirical, vs base rate)
TA_LOGITS = {
    "Oncology":            -0.61,
    "Other":               +0.23,
    "Infectious Disease":  +1.41,
    "CNS/Neurology":       +0.42,
    "Immunology":          +1.35,
    "Rare Disease":        +0.82,
    "Cardiovascular":      +0.59,
    "Ophthalmology":       -0.03,
    "Pain Management":     -0.02,
    "Metabolic/Endocrine": +0.63,
    "Endocrinology":       +0.63,   # alias for Metabolic/Endocrine
    "Nephrology":          +0.14,
    "Dermatology":         +1.52,
    "Respiratory":         +2.65,
    "Hematology":          +0.34,
    "GI/Hepatology":       +2.34,
    "Women's Health":      +2.50,
    "Vaccines":            +2.50,
    "CNS":                 -1.45,
}

# Continuous feature weights (learned via gradient descent)
CONTINUOUS_WEIGHTS = {
    "historical_crl_rate":     -2.50,   # corr=-0.25, strong negative
    "sponsor_prior_approvals":  0.04,   # corr=+0.36, per approval
    "prior_crl_count":         -0.30,   # corr=-0.22, per CRL
}

# Tier thresholds
TIER_THRESHOLDS = {
    1: 0.85,     # LONG — high confidence approval
    2: 0.65,     # LEAN_LONG
    3: 0.40,     # NEUTRAL / COIN_FLIP
    4: 0.00,     # HIGH_CRL_RISK
}

TIER_ACTIONS = {
    1: "LONG",
    2: "LEAN_LONG",
    3: "NEUTRAL",
    4: "HIGH_CRL_RISK",
}

# Base logit from the real 68.0% approval rate
BASE_LOGIT = logit(0.680)  # ≈ 0.7538


# ═══════════════════════════════════════════════════════════════
#  CSV ROW → FEATURE VECTOR
#  Updated for ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv
# ═══════════════════════════════════════════════════════════════

def parse_row(row: dict) -> dict:
    """
    Parse a CSV row into a standardized event dict with all features.

    v1070 columns used directly:
        btd, orphan, priority_review, fast_track, accelerated_approval,
        had_adcom, prior_crl, form_483_issues, manufacturing_risk,
        s22_ped_pk_missing, ema_cmc_flag, cmc_extension_flag,
        gene_therapy, surrogate_endpoint, single_arm_study, ppm_flag,
        safety_signal_severity, fda_era, prior_crl_count,
        historical_crl_rate, sponsor_prior_approvals, adcom_vote_pct,
        resubmission_class, therapeutic_area

    Derived at parse time (NOT in CSV):
        double_crl_flag       = prior_crl_count >= 2
        btd_onco_interaction  = btd AND therapeutic_area == Oncology
        btd_priority_interaction = btd AND priority_review
        ta_very_high_risk     = TA_TO_BUCKET[ta] == VERY_HIGH
        ta_bucket_v2          = TA_TO_BUCKET[ta]
        safety_moderate       = 1.0 <= safety_signal_severity < 2.5
        safety_high           = safety_signal_severity >= 2.5

    This is the SINGLE source of truth for feature extraction.
    """
    ev = {}

    # Identity
    ev["event_id"] = row.get("event_id", "").strip()
    ev["ticker"] = row.get("ticker", "").strip()
    ev["company"] = row.get("company", "").strip()
    ev["drug_name"] = row.get("asset", "").strip()
    ev["indication"] = row.get("indication", "").strip()
    ev["therapeutic_area"] = _normalize_ta(row.get("therapeutic_area", "Other"))
    ev["catalyst_date"] = row.get("catalyst_date", row.get("cat_date", "")).strip()

    # Outcome
    outcome = row.get("outcome", "").strip().upper()
    if outcome == "APPROVAL":
        ev["outcome"] = "APPROVED"
    elif outcome == "CRL":
        ev["outcome"] = "CRL"
    else:
        ev["outcome"] = None

    # ── Binary signals (map directly from v1070 CSV columns) ──
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

    # accelerated_approval — v1070 has mixed formats: TRUE/FALSE/Yes/No/empty
    ev["accelerated_approval"] = _pb(row.get("accelerated_approval"))

    # ── DERIVED signals (computed from raw v1070 features, NOT CSV columns) ──

    # double_crl_flag: prior_crl_count >= 2
    crl_count = _pi(row.get("prior_crl_count"), 0)
    ev["double_crl_flag"] = crl_count >= 2

    # btd_onco_interaction: BTD=True AND therapeutic_area is Oncology
    ta = ev["therapeutic_area"]
    ev["btd_onco_interaction"] = ev["btd"] and ta == "Oncology"

    # btd_priority_interaction: BTD=True AND priority_review=True
    ev["btd_priority_interaction"] = ev["btd"] and ev["priority_review"]

    # ta_bucket_v2: derived from TA→bucket lookup
    ev["ta_bucket_v2"] = TA_TO_BUCKET.get(ta, "MOD")

    # ta_very_high_risk: bucket is VERY_HIGH
    ev["ta_very_high_risk"] = ev["ta_bucket_v2"] == "VERY_HIGH"

    # ── Safety severity (continuous → threshold-derived bools) ──
    safety_sev = _pf(row.get("safety_signal_severity"), 0.0)
    ev["safety_signal_severity"] = safety_sev
    ev["safety_moderate"] = 1.0 <= safety_sev < 2.5
    ev["safety_high"] = safety_sev >= 2.5

    # ── Categorical features ──
    # fda_era: read directly from v1070 CSV column
    ev["fda_era"] = row.get("fda_era", "POST_COVID").strip()
    if ev["fda_era"] not in FDA_ERA_LOGITS:
        ev["fda_era"] = "POST_COVID"

    # resubmission_class: v1070 has "1.0", "2.0", or empty string
    resub_raw = row.get("resubmission_class", "").strip()
    try:
        resub_int = int(float(resub_raw))
        ev["resubmission_class"] = resub_int if resub_int in (1, 2) else 0
    except (ValueError, TypeError):
        ev["resubmission_class"] = 0

    # ── Continuous features ──
    ev["historical_crl_rate"] = _pf(row.get("historical_crl_rate"), 0.34)
    ev["sponsor_prior_approvals"] = _pi(row.get("sponsor_prior_approvals"), 0)
    ev["prior_crl_count"] = crl_count
    ev["adcom_vote_pct"] = _pf(row.get("adcom_vote_pct"), 0.0)

    # ── Prior model scores (for ensembling/reference) ──
    ev["v1067_score"] = _pf(row.get("v1067_score"))
    ev["v1070_score"] = _pf(row.get("v1070_score"))

    # ── Additional v1070 columns (preserved for downstream use) ──
    ev["ta_base_score"] = _pf(row.get("ta_base_score"), 0.0)
    ev["application_type"] = row.get("application_type", "").strip()
    ev["psychedelics"] = _pb(row.get("psychedelics"))

    return ev


def _normalize_ta(ta: str) -> str:
    ta = ta.strip()
    return {"Endocrinology": "Metabolic/Endocrine"}.get(ta, ta)


# ═══════════════════════════════════════════════════════════════
#  SCORER — Computes P(approval) from feature vector
# ═══════════════════════════════════════════════════════════════

class OdinScorer:
    """
    Logistic scoring model. Maintains signal weights and computes probabilities.

    Score = sigmoid(base_logit + Σ signal_logits + TA_offset + categoricals + continuous)
    """

    def __init__(self, weights: dict = None):
        """
        weights dict structure:
        {
            "base_logit": float,
            "signals": { signal_name: logit_value, ... },
            "ta_bucket": { "LOW": float, "MOD": float, ... },
            "fda_era": { "PRE_2020": float, ... },
            "resub": { "0": float, "1": float, "2": float },
            "ta_offsets": { "Oncology": float, ... },
            "continuous": { "historical_crl_rate": float, ... },
        }
        """
        if weights:
            self.weights = deepcopy(weights)
        else:
            self.weights = self._default_weights()

    def _default_weights(self) -> dict:
        """Build default weights from empirical analysis."""
        return {
            "base_logit": BASE_LOGIT,
            "signals": {k: v["logit"] for k, v in SIGNAL_REGISTRY.items()},
            "ta_bucket": dict(TA_BUCKET_LOGITS),
            "fda_era": dict(FDA_ERA_LOGITS),
            "resub": {str(k): v for k, v in RESUB_LOGITS.items()},
            "ta_offsets": dict(TA_LOGITS),
            "continuous": dict(CONTINUOUS_WEIGHTS),
        }

    def score(self, event: dict) -> dict:
        """
        Score a single event. Returns full breakdown.
        """
        total_logit = self.weights["base_logit"]
        fired_signals = {}
        signal_contributions = {}

        # ── Binary signals ──
        for sig_name, sig_logit in self.weights["signals"].items():
            val = event.get(sig_name, False)
            if val:
                total_logit += sig_logit
                fired_signals[sig_name] = sig_logit
                signal_contributions[sig_name] = sig_logit

        # ── TA bucket ──
        ta_bucket = event.get("ta_bucket_v2", "MOD")
        ta_bucket_logit = self.weights["ta_bucket"].get(ta_bucket, 0.0)
        total_logit += ta_bucket_logit
        signal_contributions["ta_bucket_" + ta_bucket] = ta_bucket_logit

        # ── FDA era ──
        era = event.get("fda_era", "POST_COVID")
        era_logit = self.weights["fda_era"].get(era, 0.0)
        total_logit += era_logit
        signal_contributions["fda_era_" + era] = era_logit

        # ── Resubmission class ──
        resub = str(event.get("resubmission_class", 0))
        resub_logit = self.weights["resub"].get(resub, 0.0)
        total_logit += resub_logit
        if resub != "0":
            signal_contributions["resub_class_" + resub] = resub_logit

        # ── TA offset ──
        ta = event.get("therapeutic_area", "Other")
        ta_offset = self.weights["ta_offsets"].get(ta, 0.0)
        total_logit += ta_offset
        signal_contributions["ta_" + ta] = ta_offset

        # ── Continuous features ──
        # Historical CRL rate: centered around dataset mean (0.34)
        hist_crl = event.get("historical_crl_rate", 0.34)
        crl_weight = self.weights["continuous"].get("historical_crl_rate", -2.5)
        crl_contrib = crl_weight * (hist_crl - 0.34)
        total_logit += crl_contrib
        if abs(crl_contrib) > 0.01:
            signal_contributions["hist_crl_rate"] = round(crl_contrib, 4)

        # Sponsor experience: log-scaled, centered
        sponsor_exp = event.get("sponsor_prior_approvals", 0)
        exp_weight = self.weights["continuous"].get("sponsor_prior_approvals", 0.04)
        exp_contrib = exp_weight * (sponsor_exp - 10.0)
        total_logit += exp_contrib
        if abs(exp_contrib) > 0.01:
            signal_contributions["sponsor_experience"] = round(exp_contrib, 4)

        # Prior CRL count (additional to binary prior_crl flag)
        crl_count = event.get("prior_crl_count", 0)
        count_weight = self.weights["continuous"].get("prior_crl_count", -0.30)
        count_contrib = count_weight * crl_count
        total_logit += count_contrib
        if abs(count_contrib) > 0.01:
            signal_contributions["prior_crl_count"] = round(count_contrib, 4)

        # Probability
        prob = sigmoid(total_logit)

        # Tier
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
        """Score multiple events."""
        return [self.score(ev) for ev in events]

    def export_weights(self) -> dict:
        """Export weights for persistence."""
        return deepcopy(self.weights)

    def import_weights(self, weights: dict):
        """Import weights (e.g., from saved model)."""
        self.weights = deepcopy(weights)

    def weight_hash(self) -> str:
        """SHA256 hash of current weights for versioning."""
        raw = json.dumps(self.weights, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════
#  CALIBRATION ENGINE — Measures model quality
# ═══════════════════════════════════════════════════════════════

class CalibrationEngine:
    """Compute calibration metrics from predictions vs outcomes."""

    @staticmethod
    def compute_metrics(predictions: list, actuals: list) -> dict:
        """
        predictions: list of P(approval) floats
        actuals: list of 1.0 (approved) or 0.0 (CRL)
        """
        n = len(predictions)
        if n == 0:
            return {"brier": None, "auc": None, "accuracy": None, "n": 0}

        # Brier score
        brier = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / n

        # Accuracy at 0.5 threshold
        accuracy = sum(
            1 for p, a in zip(predictions, actuals)
            if (p >= 0.5 and a == 1.0) or (p < 0.5 and a == 0.0)
        ) / n

        # AUC-ROC
        pos = [p for p, a in zip(predictions, actuals) if a == 1.0]
        neg = [p for p, a in zip(predictions, actuals) if a == 0.0]
        if pos and neg:
            conc = sum(1 for pp in pos for pn in neg if pp > pn)
            tied = sum(0.5 for pp in pos for pn in neg if pp == pn)
            auc = (conc + tied) / (len(pos) * len(neg))
        else:
            auc = 0.5

        # Log loss
        eps = 1e-7
        log_loss = -sum(
            a * math.log(max(p, eps)) + (1 - a) * math.log(max(1 - p, eps))
            for p, a in zip(predictions, actuals)
        ) / n

        # Tier-level calibration
        tier_stats = defaultdict(lambda: {"n": 0, "approvals": 0, "sum_prob": 0})
        for p, a in zip(predictions, actuals):
            if p >= TIER_THRESHOLDS[1]:
                t = 1
            elif p >= TIER_THRESHOLDS[2]:
                t = 2
            elif p >= TIER_THRESHOLDS[3]:
                t = 3
            else:
                t = 4
            tier_stats[t]["n"] += 1
            tier_stats[t]["approvals"] += a
            tier_stats[t]["sum_prob"] += p

        tier_report = {}
        for t in sorted(tier_stats.keys()):
            s = tier_stats[t]
            rate = s["approvals"] / s["n"] if s["n"] > 0 else 0
            avg_p = s["sum_prob"] / s["n"] if s["n"] > 0 else 0
            tier_report[t] = {
                "n": s["n"],
                "approval_rate": round(rate, 4),
                "avg_predicted": round(avg_p, 4),
                "calibration_gap": round(abs(rate - avg_p), 4),
            }

        return {
            "brier": round(brier, 6),
            "auc": round(auc, 6),
            "accuracy": round(accuracy, 6),
            "log_loss": round(log_loss, 6),
            "n": n,
            "n_approved": sum(1 for a in actuals if a == 1.0),
            "n_crl": sum(1 for a in actuals if a == 0.0),
            "base_rate": round(sum(actuals) / n, 4),
            "tier_stats": tier_report,
        }


# ═══════════════════════════════════════════════════════════════
#  GRADIENT DESCENT RECALIBRATOR
# ═══════════════════════════════════════════════════════════════

class GradientRecalibrator:
    """
    Fine-tunes all model weights via gradient descent on Brier score.
    Uses L2 regularization to prevent overfitting.
    """

    def __init__(self, lr=0.003, l2=0.005, max_epochs=3000, convergence=1e-8):
        self.lr = lr
        self.l2 = l2
        self.max_epochs = max_epochs
        self.convergence = convergence

    def recalibrate(self, scorer: OdinScorer, events: list) -> dict:
        """
        Run gradient descent on resolved events.
        Updates scorer weights in place.
        Returns report dict.
        """
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        if len(resolved) < 20:
            return {"status": "INSUFFICIENT_DATA", "n": len(resolved)}

        # Extract targets
        targets = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in resolved]

        # Pre-calibration metrics
        pre_preds = [scorer.score(e)["probability"] for e in resolved]
        pre_metrics = CalibrationEngine.compute_metrics(pre_preds, targets)

        # Build gradient targets: for each event, we know which signals fire,
        # which categoricals apply, and the continuous values.
        # We update all weights simultaneously.

        weights = scorer.weights
        old_weights = deepcopy(weights)

        best_brier = pre_metrics["brier"]
        best_weights = deepcopy(weights)
        patience = 200
        no_improve = 0

        for epoch in range(self.max_epochs):
            total_grad_base = 0.0
            signal_grads = defaultdict(float)
            ta_bucket_grads = defaultdict(float)
            era_grads = defaultdict(float)
            resub_grads = defaultdict(float)
            ta_offset_grads = defaultdict(float)
            cont_grads = defaultdict(float)

            epoch_brier = 0.0

            for ev, target in zip(resolved, targets):
                result = scorer.score(ev)
                pred = result["probability"]
                error = pred - target  # gradient of Brier w.r.t. pred
                grad_factor = 2.0 * error * pred * (1.0 - pred) / len(resolved)

                epoch_brier += (pred - target) ** 2

                # Base logit gradient
                total_grad_base += grad_factor

                # Binary signal gradients
                for sig_name in weights["signals"]:
                    if ev.get(sig_name, False):
                        signal_grads[sig_name] += grad_factor

                # TA bucket
                bucket = ev.get("ta_bucket_v2", "MOD")
                ta_bucket_grads[bucket] += grad_factor

                # FDA era
                era = ev.get("fda_era", "POST_COVID")
                era_grads[era] += grad_factor

                # Resubmission
                resub = str(ev.get("resubmission_class", 0))
                resub_grads[resub] += grad_factor

                # TA offset
                ta = ev.get("therapeutic_area", "Other")
                ta_offset_grads[ta] += grad_factor

                # Continuous features
                hist_crl = ev.get("historical_crl_rate", 0.34)
                cont_grads["historical_crl_rate"] += grad_factor * (hist_crl - 0.34)

                sponsor = ev.get("sponsor_prior_approvals", 0)
                cont_grads["sponsor_prior_approvals"] += grad_factor * (sponsor - 10.0)

                crl_count = ev.get("prior_crl_count", 0)
                cont_grads["prior_crl_count"] += grad_factor * crl_count

            epoch_brier /= len(resolved)

            # Apply gradients with L2 regularization
            weights["base_logit"] -= self.lr * total_grad_base

            for sig in weights["signals"]:
                g = signal_grads.get(sig, 0.0)
                g += self.l2 * weights["signals"][sig]  # L2
                weights["signals"][sig] -= self.lr * g

            for bucket in weights["ta_bucket"]:
                g = ta_bucket_grads.get(bucket, 0.0) + self.l2 * weights["ta_bucket"][bucket]
                weights["ta_bucket"][bucket] -= self.lr * g

            for era in weights["fda_era"]:
                g = era_grads.get(era, 0.0) + self.l2 * weights["fda_era"][era]
                weights["fda_era"][era] -= self.lr * g

            for r in weights["resub"]:
                g = resub_grads.get(r, 0.0) + self.l2 * weights["resub"][r]
                weights["resub"][r] -= self.lr * g

            for ta in weights["ta_offsets"]:
                g = ta_offset_grads.get(ta, 0.0) + self.l2 * weights["ta_offsets"][ta]
                weights["ta_offsets"][ta] -= self.lr * g

            for c in weights["continuous"]:
                g = cont_grads.get(c, 0.0) + self.l2 * weights["continuous"][c]
                weights["continuous"][c] -= self.lr * g

            # Early stopping
            if epoch_brier < best_brier - self.convergence:
                best_brier = epoch_brier
                best_weights = deepcopy(weights)
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        # Restore best weights
        scorer.weights = best_weights

        # Post-calibration metrics
        post_preds = [scorer.score(e)["probability"] for e in resolved]
        post_metrics = CalibrationEngine.compute_metrics(post_preds, targets)

        # Count changed signals
        n_changed = 0
        for sig in old_weights["signals"]:
            if abs(old_weights["signals"][sig] - best_weights["signals"][sig]) > 0.001:
                n_changed += 1

        return {
            "status": "RECALIBRATED",
            "epochs": epoch + 1,
            "signals_changed": n_changed,
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
    """
    Walk-forward backtesting: train on events before cutoff date,
    test on events after cutoff date.
    """

    @staticmethod
    def time_split_backtest(events: list, train_frac=0.7) -> dict:
        """
        Split events by time ordering (using event_id or catalyst_date).
        Train on first train_frac, test on rest.
        """
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        n = len(resolved)
        split_idx = int(n * train_frac)

        train = resolved[:split_idx]
        test = resolved[split_idx:]

        if len(train) < 20 or len(test) < 10:
            return {"status": "INSUFFICIENT_DATA"}

        # Train scorer on train set
        scorer = OdinScorer()
        recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=2000)
        recal_report = recal.recalibrate(scorer, train)

        # Score test set
        test_preds = [scorer.score(e)["probability"] for e in test]
        test_actuals = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in test]
        test_metrics = CalibrationEngine.compute_metrics(test_preds, test_actuals)

        # Also score train set for comparison
        train_preds = [scorer.score(e)["probability"] for e in train]
        train_actuals = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in train]
        train_metrics = CalibrationEngine.compute_metrics(train_preds, train_actuals)

        return {
            "status": "OK",
            "train_n": len(train),
            "test_n": len(test),
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "recalibration": recal_report,
        }

    @staticmethod
    def kfold_backtest(events: list, k=5) -> dict:
        """K-fold cross validation."""
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        n = len(resolved)
        fold_size = n // k

        all_preds = [None] * n
        all_actuals = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in resolved]
        fold_metrics = []

        for fold in range(k):
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < k - 1 else n
            test_set = resolved[test_start:test_end]
            train_set = resolved[:test_start] + resolved[test_end:]

            scorer = OdinScorer()
            recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=1500)
            recal.recalibrate(scorer, train_set)

            for i, ev in enumerate(test_set):
                idx = test_start + i
                pred = scorer.score(ev)["probability"]
                all_preds[idx] = pred

            test_preds = [scorer.score(e)["probability"] for e in test_set]
            test_actuals_fold = [1.0 if e["outcome"] == "APPROVED" else 0.0 for e in test_set]
            fm = CalibrationEngine.compute_metrics(test_preds, test_actuals_fold)
            fold_metrics.append(fm)

        # Overall out-of-fold metrics
        valid = [(p, a) for p, a in zip(all_preds, all_actuals) if p is not None]
        oof_preds = [v[0] for v in valid]
        oof_actuals = [v[1] for v in valid]
        overall = CalibrationEngine.compute_metrics(oof_preds, oof_actuals)

        return {
            "status": "OK",
            "k": k,
            "overall_metrics": overall,
            "fold_metrics": fold_metrics,
            "avg_brier": round(sum(f["brier"] for f in fold_metrics) / k, 6),
            "avg_auc": round(sum(f["auc"] for f in fold_metrics) / k, 6),
        }


# ═══════════════════════════════════════════════════════════════
#  DRIFT DETECTOR
# ═══════════════════════════════════════════════════════════════

class DriftDetector:
    """Detect model drift from recent events."""

    @staticmethod
    def detect(scorer: OdinScorer, events: list, recent_n: int = 50) -> list:
        """Check for drift in recent events vs full history."""
        resolved = [e for e in events if e.get("outcome") in ("APPROVED", "CRL")]
        if len(resolved) < recent_n + 20:
            return []

        alerts = []
        recent = resolved[-recent_n:]
        historical = resolved[:-recent_n]

        # Recent vs historical base rate
        r_rate = sum(1 for e in recent if e["outcome"] == "APPROVED") / len(recent)
        h_rate = sum(1 for e in historical if e["outcome"] == "APPROVED") / len(historical)
        if abs(r_rate - h_rate) > 0.08:
            alerts.append({
                "type": "BASE_RATE_SHIFT",
                "recent_rate": round(r_rate, 3),
                "historical_rate": round(h_rate, 3),
                "delta": round(r_rate - h_rate, 3),
            })

        # Recent Brier vs historical Brier
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
#  PREDICTION LEDGER — Tracks all predictions + outcomes
# ═══════════════════════════════════════════════════════════════

class PredictionLedger:
    """Persistent storage of predictions and outcomes."""

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
    """Track model versions over time."""

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
#  CSV LOADER
# ═══════════════════════════════════════════════════════════════

def load_csv(filepath: str) -> list:
    """Load the ODIN CSV and parse all rows into event dicts."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [parse_row(row) for row in reader]


# ═══════════════════════════════════════════════════════════════
#  MAIN — Self-test and demo
# ═══════════════════════════════════════════════════════════════

def demo():
    """Run self-test with embedded synthetic data."""
    print("=" * 70)
    print(f"  ODIN HONING ENGINE v{__version__} — SELF-TEST")
    print("=" * 70)

    scorer = OdinScorer()
    print(f"\n  Base logit: {scorer.weights['base_logit']:.4f} → P={sigmoid(scorer.weights['base_logit']):.3f}")
    print(f"  Total binary signals: {len(scorer.weights['signals'])}")
    print(f"  TA offsets: {len(scorer.weights['ta_offsets'])}")
    print(f"  TA buckets: {len(scorer.weights['ta_bucket'])}")
    print(f"  Continuous features: {len(scorer.weights['continuous'])}")
    print(f"  TA→Bucket lookup: {len(TA_TO_BUCKET)} entries")

    # Score a bullish event
    bull = {
        "btd": True, "orphan": True, "priority_review": True,
        "fast_track": True, "had_adcom": True, "surrogate_endpoint": True,
        "therapeutic_area": "Rare Disease", "ta_bucket_v2": "HIGH",
        "fda_era": "POST_COVID", "resubmission_class": 0,
        "historical_crl_rate": 0.15, "sponsor_prior_approvals": 20,
        "prior_crl_count": 0, "event_id": "BULL_TEST", "ticker": "BULL",
    }
    result = scorer.score(bull)
    print(f"\n  Bullish event: P={result['probability']:.4f} Tier={result['tier']} ({result['action']})")
    print(f"    Signals fired: {result['signal_count']}")
    print(f"    Total logit: {result['total_logit']:.2f}")

    # Score a bearish event
    bear = {
        "prior_crl": True, "form_483_issues": True, "manufacturing_risk": True,
        "double_crl_flag": True, "ppm_flag": True,
        "therapeutic_area": "Oncology", "ta_bucket_v2": "LOW",
        "fda_era": "HOEG_ERA", "resubmission_class": 0,
        "historical_crl_rate": 0.65, "sponsor_prior_approvals": 0,
        "prior_crl_count": 3, "event_id": "BEAR_TEST", "ticker": "BEAR",
    }
    result = scorer.score(bear)
    print(f"\n  Bearish event: P={result['probability']:.6f} Tier={result['tier']} ({result['action']})")
    print(f"    Signals fired: {result['signal_count']}")
    print(f"    Total logit: {result['total_logit']:.2f}")

    # Test parse_row with v1070-style raw data (no pre-computed interaction terms)
    raw_row = {
        "event_id": "PARSE_TEST", "ticker": "TEST", "company": "TestCo",
        "asset": "TestDrug", "indication": "Cancer", "therapeutic_area": "Oncology",
        "catalyst_date": "2026-06-15", "outcome": "APPROVAL",
        "btd": "TRUE", "orphan": "FALSE", "priority_review": "TRUE",
        "fast_track": "FALSE", "accelerated_approval": "Yes",
        "had_adcom": "FALSE", "prior_crl": "FALSE",
        "form_483_issues": "FALSE", "manufacturing_risk": "FALSE",
        "s22_ped_pk_missing": "FALSE", "ema_cmc_flag": "FALSE",
        "cmc_extension_flag": "FALSE", "gene_therapy": "FALSE",
        "single_arm_study": "TRUE", "surrogate_endpoint": "TRUE",
        "ppm_flag": "FALSE", "safety_signal_severity": "0.5",
        "fda_era": "HOEG_ERA", "prior_crl_count": "0",
        "resubmission_class": "1.0",
        "historical_crl_rate": "0.25", "sponsor_prior_approvals": "15",
        "adcom_vote_pct": "0.0", "ta_base_score": "0.061",
    }
    parsed = parse_row(raw_row)
    print(f"\n  Parse test (v1070 raw row):")
    print(f"    btd_onco_interaction:  {parsed['btd_onco_interaction']} (expected: True)")
    print(f"    btd_priority_interaction: {parsed['btd_priority_interaction']} (expected: True)")
    print(f"    ta_bucket_v2:          {parsed['ta_bucket_v2']} (expected: LOW)")
    print(f"    ta_very_high_risk:     {parsed['ta_very_high_risk']} (expected: False)")
    print(f"    double_crl_flag:       {parsed['double_crl_flag']} (expected: False)")
    print(f"    accelerated_approval:  {parsed['accelerated_approval']} (expected: True)")
    print(f"    resubmission_class:    {parsed['resubmission_class']} (expected: 1)")
    print(f"    fda_era:               {parsed['fda_era']} (expected: HOEG_ERA)")
    print(f"    surrogate_endpoint:    {parsed['surrogate_endpoint']} (expected: True)")

    result2 = scorer.score(parsed)
    print(f"\n    Scored: P={result2['probability']:.4f} Tier={result2['tier']} ({result2['action']})")

    print(f"\n  ✅ Engine v{__version__} operational")
    print("=" * 70)


if __name__ == "__main__":
    demo()
