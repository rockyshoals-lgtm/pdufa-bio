#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ODIN HONING ENGINE v4.9                             ║
║   CRS-Only + Diverse Seeds + Weighted Ensemble + Basin Hopping         ║
║                                                                         ║
║  Changes from v4.8:                                                     ║
║   1. DROP Adam — confirmed useless in 3 runs (best 0.148→CRS to 0.112)║
║   2. FIX Ensemble diversity: seeds 2+ use anchor+noise(0.15) not       ║
║      best_w+noise(0.01) → genuinely different CRS starting points      ║
║   3. FIX Ensemble weighting: inverse-Brier weighted mean (better runs  ║
║      get more influence instead of simple average)                      ║
║   4. ADD Basin Hopping: after CRS+SWP, restart from N random anchor   ║
║      perturbations to escape local optima (global search)              ║
║   5. ADD Domain floors: indication_pain(0.10), novice_risk_ta(0.30),  ║
║      social(0.05), odin_weight cap(0.70)                               ║
║   6. OPT: SWP temperature decay (simulated annealing schedule)         ║
║                                                                         ║
║  Usage:                                                                 ║
║    python odin_honing_engine.py                          # fresh run    ║
║    python odin_honing_engine.py --resume                 # continue     ║
║    python odin_honing_engine.py --anchor my_weights.json # new anchor  ║
║    python odin_honing_engine.py --config my_config.json  # custom cfg  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import json
import os
import sys
import time
import argparse
import warnings
from datetime import datetime
from copy import deepcopy

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTS — override with --config or --anchor
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_ANCHOR  = "odin_v1134_anchor.json"
DEFAULT_DATA    = "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv"
DEFAULT_CONFIG  = "odin_honing_config.json"
STATE_FILE      = "odin_honing_state.json"
HISTORY_FILE    = "odin_honing_history.csv"
OUTPUT_HONED    = "odin_v1134_honed.json"
OUTPUT_ENSEMBLE = "odin_v1134_honed_ensemble.json"

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE NAMES — must match anchor JSON keys (order matters)
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "base_logit",
    "snda_base_penalty",
    "snda_pediatric_base_penalty",
    "prior_crl_penalty",
    "inexperienced_sponsor_penalty",
    "manufacturing_risk_penalty",
    "form_483_penalty",
    "ema_cmc_flag_penalty",
    "cmc_extension_penalty",
    "adcom_mid_penalty",
    "adcom_low_penalty",
    "s22_pediatric_pk_penalty",
    "btd_weight",
    "orphan_weight",
    "priority_review_weight",
    "fast_track_weight",
    "accelerated_approval_weight",
    "class1_resubmission_boost",
    "experienced_sponsor_boost",
    "adcom_high_boost",
    "ta_adjustment_weight",
    "s23_insider_weight",
    "s6_hiring_weight",
    "social_weight",
    "odin_weight",
    "hint_weight",
    "hint_crl_rate_penalty",
    "ta_high_risk_penalty",
    "ta_mod_risk_penalty",
    "ta_low_risk_boost",
    "indication_pain_penalty",
    "indication_onc_boost",
    "novice_sponsor_high_risk_ta_penalty",
    "gene_therapy_penalty",
    "single_arm_study_penalty",
    "surrogate_endpoint_penalty",
    "prior_crl_count_penalty",
    "safety_severity_penalty",
    "ppm_penalty",
    "eu_approved_boost",
    "eu_approved_2026_penalty",
    "psychedelics_penalty",
    "hoeg_era_constant",
    "accel_approval_2025plus_penalty",
    "experienced_sponsor_2026_reduction",
    # ── v1071 architectural features ──────────────────────────────────────────
    "btd_oncology_boost",          # [45] BTD × Oncology interaction (+2.18 logit)
    "ta_very_high_boost",          # [46] TA VERY_HIGH bucket (Resp/ID/Derm/Immuno/GI, 90%+ approval)
    "double_crl_penalty",          # [47] 2+ prior CRLs (20.4% approval — non-linear cliff)
    # ── v1108 interaction features (plateau-breakers) ─────────────────────────
    "ix_prior_crl_x_mfg_risk",    # [48] Prior CRL × Manufacturing Risk
    "ix_prior_crl_x_form483",     # [49] Prior CRL × Form 483 issues
    "ix_gene_therapy_x_mfg_risk", # [50] Gene Therapy × Manufacturing Risk
    "ix_inexperienced_x_mfg_risk",# [51] Inexperienced Sponsor × Manufacturing Risk
    "ix_single_arm_x_surrogate",  # [52] Single-Arm Study × Surrogate Endpoint
    "ix_btd_x_single_arm",        # [53] BTD × Single-Arm Study (tension)
]

# Sign constraints: +1 = must be positive, -1 = must be negative, 0 = free
SIGN_CONSTRAINTS = {
    "base_logit": +1,
    "snda_base_penalty": -1,
    "snda_pediatric_base_penalty": -1,
    "prior_crl_penalty": -1,
    "inexperienced_sponsor_penalty": -1,
    "manufacturing_risk_penalty": -1,
    "form_483_penalty": -1,
    "ema_cmc_flag_penalty": -1,
    "cmc_extension_penalty": -1,
    "adcom_mid_penalty": -1,
    "adcom_low_penalty": -1,
    "s22_pediatric_pk_penalty": -1,
    "btd_weight": +1,
    "orphan_weight": +1,        # domain: orphan = positive signal
    "priority_review_weight": +1,
    "fast_track_weight": +1,    # domain: fast track = positive signal
    "accelerated_approval_weight": +1,
    "class1_resubmission_boost": 0,  # can go either way
    "experienced_sponsor_boost": +1,
    "adcom_high_boost": +1,
    "ta_adjustment_weight": 0,
    "s23_insider_weight": +1,
    "s6_hiring_weight": +1,
    "social_weight": +1,
    "odin_weight": +1,
    "hint_weight": +1,          # [25] uses hist_approval_rate = (1 - crl_rate), positive = good
    "hint_crl_rate_penalty": -1, # [26] uses hist_crl_rate directly, negative = bad
    "ta_high_risk_penalty": -1,
    "ta_mod_risk_penalty": -1,
    "ta_low_risk_boost": 0,
    "indication_pain_penalty": -1,
    "indication_onc_boost": 0,
    "novice_sponsor_high_risk_ta_penalty": -1,
    "gene_therapy_penalty": -1,
    "single_arm_study_penalty": -1,
    "surrogate_endpoint_penalty": -1,
    "prior_crl_count_penalty": -1,
    "safety_severity_penalty": -1,
    "ppm_penalty": -1,
    "eu_approved_boost": +1,
    "eu_approved_2026_penalty": -1,
    "psychedelics_penalty": -1,
    "hoeg_era_constant": -1,
    "accel_approval_2025plus_penalty": -1,
    "experienced_sponsor_2026_reduction": -1,
    # v1071 architectural features
    "btd_oncology_boost":  +1,  # interaction must be positive (96.8% approval)
    "ta_very_high_boost":  +1,  # very high TA = higher approval probability
    "double_crl_penalty":  -1,  # 2+ CRLs = catastrophic (20.4% approval)
    # v1108 interaction features
    "ix_prior_crl_x_mfg_risk":    -1,  # 100% CRL rate (70 events) — MONSTER penalty
    "ix_prior_crl_x_form483":     -1,  # 100% CRL rate (69 events) — MONSTER penalty
    "ix_gene_therapy_x_mfg_risk": -1,  # 40% CRL (1.2× base) — moderate penalty
    "ix_inexperienced_x_mfg_risk":-1,  # 92% CRL rate (115 events) — STRONG penalty
    "ix_single_arm_x_surrogate":   0,  # FREE — 7% CRL = APPROVAL signal (acc. pathway)
    "ix_btd_x_single_arm":         0,  # FREE — 4.7% CRL = APPROVAL signal (BTD blessed design)
}

# Domain floors: minimum absolute magnitude enforced post-update.
# Prevents optimizer from zeroing out weights with strong domain priors.
# Format: weight_name -> (min_abs_value, direction)  direction matches sign constraint
DOMAIN_FLOORS = {
    "surrogate_endpoint_penalty": 0.15,   # v1085 drifted to -0.021 (domain: must penalize)
    "hoeg_era_constant":          0.10,   # v1085 drifted to -0.052 (FDA era shift is real)
    "safety_severity_penalty":    0.15,   # v1085 drifted to -0.264 — ok, but floor it
    "single_arm_study_penalty":   0.15,   # fragile, keep grounded
    "gene_therapy_penalty":       0.10,   # fragile, keep grounded
    "orphan_weight":              0.04,   # was nudged to 0.05, keep there
    "fast_track_weight":          0.03,   # domain validated positive
    "hint_weight":                0.15,   # new decoupled feature, needs minimum signal
    "hint_crl_rate_penalty":      0.20,   # must remain meaningful penalty
    # v4.9 additions — recurring zero-drift weights
    "indication_pain_penalty":    0.10,   # v1086 drifted to -0.062 (pain has ~30% CRL rate)
    "novice_sponsor_high_risk_ta_penalty": 0.30,  # v1086 shrunk 75% to -0.243 (compound risk)
    "social_weight":              0.05,   # positive signal even if sparse; don't zero it
    # v1108 interaction features — need floors to prevent zeroing out
    "ix_prior_crl_x_mfg_risk":    0.10,
    "ix_prior_crl_x_form483":     0.10,
    "ix_gene_therapy_x_mfg_risk": 0.15,
    "ix_inexperienced_x_mfg_risk":0.10,
    # ix_single_arm_x_surrogate: no floor (FREE sign, optimizer finds level)
    # ix_btd_x_single_arm: no floor (FREE sign)
}

# v4.9: Magnitude caps — prevents upward drift in positive weights
MAGNITUDE_CAPS = {
    "odin_weight":             0.85,
    "snda_base_penalty":       3.00,   # still monotone, let it breathe
    "ta_adjustment_weight":    0.06,   # TIGHT cap — recurring sign flip, effectively freeze
    "priority_review_weight":  2.55,
    "psychedelics_penalty":    0.05,   # accept near-zero
    "hint_weight":             1.20,
    "ppm_penalty":             3.80,   # still moving
    "fast_track_weight":       1.20,   # moving up, let it explore
    # v1071 architectural features — wide caps to let optimizer find level
    "btd_oncology_boost":      3.50,   # data shows +2.18 interaction, give room
    "ta_very_high_boost":      2.50,   # data shows +1.50, give room
    "double_crl_penalty":      3.00,   # data shows -2.11, give room
    # v1108 interaction features — cap to prevent overshoot on sparse combos
    "ix_prior_crl_x_mfg_risk":    3.00,
    "ix_prior_crl_x_form483":     3.00,
    "ix_gene_therapy_x_mfg_risk": 4.00,
    "ix_inexperienced_x_mfg_risk":3.00,
    "ix_single_arm_x_surrogate":  3.00,
    "ix_btd_x_single_arm":        2.50,
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def load_data(path: str) -> tuple:
    """Load CSV and return (X, y, dates) arrays."""
    df = pd.read_csv(path, low_memory=False)
    print(f"[Data] Loaded {len(df)} rows from {path}")

    # Label
    df['label'] = (df['outcome'].str.upper() == 'APPROVAL').astype(float)

    # Catalyst year for time splits
    df['year'] = pd.to_datetime(df['catalyst_date'], errors='coerce').dt.year.fillna(2020).astype(int)

    rows = []
    for _, r in df.iterrows():
        x = build_feature_vector(r)
        rows.append(x)

    X = np.array(rows, dtype=np.float32)
    y = df['label'].values.astype(np.float32)
    dates = df['year'].values

    print(f"[Data] Features: {X.shape[1]}, Approvals: {y.sum():.0f}/{len(y)} ({y.mean():.1%})")
    return X, y, dates


def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _is_true(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ('true', '1', 'yes')
    return False


def build_feature_vector(r) -> list:
    """Map one CSV row → 54-element feature vector matching FEATURE_NAMES."""

    app_type = str(r.get('application_type', '')).upper()
    is_snda = 'SNDA' in app_type or 'SUPPL' in app_type or '505(B)(2)' in app_type
    is_ped   = _is_true(r.get('s22_ped_pk_missing', False))
    ta       = str(r.get('therapeutic_area', '')).lower()
    ind      = str(r.get('indication', '')).lower()
    era      = str(r.get('fda_era', '')).lower()

    # AdCom
    adcom    = _is_true(r.get('had_adcom', False))
    vote_pct = _safe_float(r.get('adcom_vote_pct', np.nan), default=np.nan)

    adcom_high = adcom and np.isfinite(vote_pct) and vote_pct >= 65
    adcom_mid  = adcom and np.isfinite(vote_pct) and 50 <= vote_pct < 65
    adcom_low  = adcom and np.isfinite(vote_pct) and vote_pct < 50

    # Sponsor experience
    prior_approvals = _safe_float(r.get('sponsor_prior_approvals', 0), 0)
    inexperienced   = prior_approvals == 0
    experienced     = prior_approvals >= 5

    # CRL
    prior_crl       = _is_true(r.get('prior_crl', False))
    crl_count       = _safe_float(r.get('prior_crl_count', 0), 0)
    resub_class     = _safe_float(r.get('resubmission_class', np.nan), np.nan)
    class1_resub    = prior_crl and np.isfinite(resub_class) and resub_class == 1

    # TA risk bucket
    ta_score     = _safe_float(r.get('ta_base_score', 0), 0)
    hist_crl_rate= _safe_float(r.get('historical_crl_rate', 0), 0)
    ta_high_risk = ta_score < -0.10
    ta_mod_risk  = -0.10 <= ta_score < 0.0
    ta_low_risk  = ta_score >= 0.0

    # Indication flags
    pain_ind     = any(w in ind for w in ['pain', 'analgesic', 'opioid'])
    onc_ind      = any(w in ind for w in ['cancer', 'oncol', 'tumor', 'leukemia', 'lymphoma', 'melanoma'])

    # Special flags
    gene_therapy = _is_true(r.get('gene_therapy', False))
    psychedelics = _is_true(r.get('psychedelics', False))
    ppm          = _is_true(r.get('ppm_flag', False))
    single_arm   = _is_true(r.get('single_arm_study', False))
    surrogate    = _is_true(r.get('surrogate_endpoint', False))
    safety_sev   = _safe_float(r.get('safety_signal_severity', 0), 0)

    # EU approval context
    eu_approved       = 'eu_approved' in str(r.get('accelerated_approval', '')).lower()
    eu_approved_2026  = eu_approved and int(r.get('year', 2020)) >= 2026

    # Hoeg era (FDA stricter from 2023+)
    hoeg_era     = 'hoeg' in era or int(r.get('year', 2020)) >= 2023
    accel_2025   = _is_true(r.get('accelerated_approval', False)) and int(r.get('year', 2020)) >= 2025

    # Novice sponsor in high-risk TA
    novice_high_risk_ta = inexperienced and ta_high_risk

    # Experienced sponsor 2026+ (slightly reduced boost due to FDA pressure)
    exp_2026 = experienced and int(r.get('year', 2020)) >= 2026

    # Signal scores (continuous)
    s23 = _safe_float(r.get('s23_signal_strength', 0), 0)
    s6  = _safe_float(r.get('s6_signal_strength', 0), 0)
    soc = _safe_float(r.get('social_sentiment_score', 0), 0)
    odin= _safe_float(r.get('v1070_score', r.get('v1067_score', 0)), 0)

    # FIXED in v4.8: hint features are now DECOUPLED
    # [25] hint_weight: uses hist_approval_rate = (1 - hist_crl_rate)
    #      → weight is POSITIVE, higher approval rate TA = boost
    # [26] hint_crl_rate_penalty: uses hist_crl_rate directly
    #      → weight is NEGATIVE, higher CRL rate TA = penalty
    # Previously both used hist_crl_rate → they partially cancelled (bug)
    hist_approval_rate = max(0.0, 1.0 - hist_crl_rate)  # [25]
    # hist_crl_rate already computed above                # [26]

    # TA adjustment (continuous score × weight)
    ta_adj = ta_score

    vec = [
        1.0,                            # [0]  base_logit (intercept)
        float(is_snda and not is_ped),  # [1]  snda_base_penalty
        float(is_snda and is_ped),      # [2]  snda_pediatric_base_penalty
        float(prior_crl),               # [3]  prior_crl_penalty
        float(inexperienced),           # [4]  inexperienced_sponsor_penalty
        float(_is_true(r.get('manufacturing_risk', False))),  # [5]
        float(_is_true(r.get('form_483_issues', False))),     # [6]
        float(_is_true(r.get('ema_cmc_flag', False))),        # [7]
        float(_is_true(r.get('cmc_extension_flag', False))),  # [8]
        float(adcom_mid),               # [9]
        float(adcom_low),               # [10]
        float(is_ped),                  # [11] s22_pediatric_pk_penalty
        float(_is_true(r.get('btd', False))),         # [12] btd_weight
        float(_is_true(r.get('orphan', False))),      # [13] orphan_weight
        float(_is_true(r.get('priority_review', False))), # [14]
        float(_is_true(r.get('fast_track', False))),  # [15]
        float(_is_true(r.get('accelerated_approval', False)) and not accel_2025),  # [16]
        float(class1_resub),            # [17] class1_resubmission_boost
        float(experienced),             # [18] experienced_sponsor_boost
        float(adcom_high),              # [19] adcom_high_boost
        ta_adj,                         # [20] ta_adjustment_weight (continuous)
        s23,                            # [21] s23_insider_weight (continuous)
        s6,                             # [22] s6_hiring_weight (continuous)
        soc,                            # [23] social_weight (continuous)
        odin,                           # [24] odin_weight (continuous)
        hist_approval_rate,             # [25] hint_weight (1 - hist_crl_rate = approval rate, positive)
        hist_crl_rate,                  # [26] hint_crl_rate_penalty (crl rate directly, negative)
        float(ta_high_risk),            # [27] ta_high_risk_penalty
        float(ta_mod_risk),             # [28] ta_mod_risk_penalty
        float(ta_low_risk),             # [29] ta_low_risk_boost
        float(pain_ind),                # [30] indication_pain_penalty
        float(onc_ind),                 # [31] indication_onc_boost
        float(novice_high_risk_ta),     # [32] novice_sponsor_high_risk_ta_penalty
        float(gene_therapy),            # [33] gene_therapy_penalty
        float(single_arm),              # [34] single_arm_study_penalty
        float(surrogate),               # [35] surrogate_endpoint_penalty
        min(crl_count, 3),              # [36] prior_crl_count_penalty (continuous, capped)
        min(safety_sev, 3),             # [37] safety_severity_penalty (continuous)
        float(ppm),                     # [38] ppm_penalty
        float(eu_approved),             # [39] eu_approved_boost
        float(eu_approved_2026),        # [40] eu_approved_2026_penalty
        float(psychedelics),            # [41] psychedelics_penalty
        float(hoeg_era),                # [42] hoeg_era_constant
        float(accel_2025),              # [43] accel_approval_2025plus_penalty
        float(exp_2026),                # [44] experienced_sponsor_2026_reduction
        # ── v1071 architectural features ────────────────────────────────────
        float(_is_true(r.get('btd', False)) and
              str(r.get('therapeutic_area', '')).strip() == 'Oncology'),   # [45] btd_oncology_boost
        float(str(r.get('therapeutic_area', '')).strip() in
              ('Respiratory', 'GI/Hepatology', 'Dermatology',
               'Infectious Disease', 'Immunology')),                        # [46] ta_very_high_boost
        float(min(_safe_float(r.get('prior_crl_count', 0), 0), 5) >= 2),  # [47] double_crl_penalty
        # ── v1108 interaction features ──────────────────────────────────────
        float(prior_crl and _is_true(r.get('manufacturing_risk', False))),  # [48] ix_prior_crl_x_mfg_risk
        float(prior_crl and _is_true(r.get('form_483_issues', False))),     # [49] ix_prior_crl_x_form483
        float(gene_therapy and _is_true(r.get('manufacturing_risk', False))),# [50] ix_gene_therapy_x_mfg_risk
        float(inexperienced and _is_true(r.get('manufacturing_risk', False))),# [51] ix_inexperienced_x_mfg_risk
        float(single_arm and surrogate),                                     # [52] ix_single_arm_x_surrogate
        float(_is_true(r.get('btd', False)) and single_arm),                # [53] ix_btd_x_single_arm
    ]

    assert len(vec) == len(FEATURE_NAMES), f"Feature vector len {len(vec)} != {len(FEATURE_NAMES)}"
    return vec


# ─────────────────────────────────────────────────────────────────────────────
# SCORING MODEL
# ─────────────────────────────────────────────────────────────────────────────

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


def predict(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Logit-space prediction: logit = X @ w (first col is bias via base_logit feature)."""
    logits = X @ w
    return sigmoid(logits)


def brier_score(y_true, y_pred):
    return np.mean((y_pred - y_true) ** 2)


def log_loss(y_true, y_pred, eps=1e-7, label_smooth=0.0):
    if label_smooth > 0:
        y_true = y_true * (1 - label_smooth) + 0.5 * label_smooth
    p = np.clip(y_pred, eps, 1 - eps)
    return -np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))


def roc_auc(y_true, y_pred):
    """Simple AUC via trapezoid."""
    order = np.argsort(-y_pred)
    y_sorted = y_true[order]
    npos = y_sorted.sum()
    nneg = len(y_sorted) - npos
    if npos == 0 or nneg == 0:
        return 0.5
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    tpr = tp / npos
    fpr = fp / nneg
    try:
        return np.trapezoid(tpr, fpr)
    except AttributeError:
        return np.trapz(tpr, fpr)


def combined_loss(y_true, y_pred, brier_weight=0.3, label_smooth=0.02):
    ll = log_loss(y_true, y_pred, label_smooth=label_smooth)
    bs = brier_score(y_true, y_pred)
    return (1 - brier_weight) * ll + brier_weight * bs


# ─────────────────────────────────────────────────────────────────────────────
# CALIBRATION — Platt Scaling (replaces overfit PAV isotonic)
# ─────────────────────────────────────────────────────────────────────────────

def fit_platt(y_true, y_pred, n_iter=2000, lr=0.05):
    """
    Platt scaling: fit a + b*logit(p) via gradient descent.
    Far less prone to overfitting on small val sets than PAV isotonic,
    which mapped 50% of v1085 val predictions to exactly 1.0.
    """
    p = np.clip(y_pred, 1e-7, 1 - 1e-7)
    logits = np.log(p / (1 - p))
    y = y_true.astype(np.float64)

    # Initialize: a=0, b=1 (identity transform)
    a, b = 0.0, 1.0

    for _ in range(n_iter):
        p_cal = 1.0 / (1.0 + np.exp(-(a + b * logits)))
        p_cal = np.clip(p_cal, 1e-7, 1 - 1e-7)
        err = p_cal - y
        da = np.mean(err)
        db = np.mean(err * logits)
        a -= lr * da
        b -= lr * db

    return {"type": "platt", "a": float(a), "b": float(b)}


def apply_platt(y_pred, cal):
    p = np.clip(y_pred, 1e-7, 1 - 1e-7)
    logits = np.log(p / (1 - p))
    a = cal.get("a", 0.0)
    b = cal.get("b", 1.0)
    return 1.0 / (1.0 + np.exp(-(a + b * logits)))


def fit_isotonic(y_true, y_pred):
    """PAV isotonic — kept for backward compatibility but NOT used as primary."""
    n = len(y_pred)
    order = np.argsort(y_pred)
    y_sorted = y_true[order]
    pred_sorted = y_pred[order]

    blocks = [[y_sorted[i], 1, pred_sorted[i]] for i in range(n)]
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(blocks) - 1:
            if blocks[i][0] / max(blocks[i][1], 1e-9) > blocks[i+1][0] / max(blocks[i+1][1], 1e-9):
                merged = [blocks[i][0] + blocks[i+1][0],
                          blocks[i][1] + blocks[i+1][1],
                          (blocks[i][2] + blocks[i+1][2]) / 2]
                blocks[i] = merged
                blocks.pop(i+1)
                changed = True
            else:
                i += 1

    x_thresh, y_vals = [], []
    for b in blocks:
        y_vals.append(b[0] / max(b[1], 1e-9))
        x_thresh.append(b[2])

    return {"type": "isotonic", "x_thresholds": x_thresh, "y_values": y_vals}


def apply_isotonic(y_pred, cal):
    if cal.get("type") == "platt":
        return apply_platt(y_pred, cal)
    x = np.array(cal["x_thresholds"])
    y = np.array(cal["y_values"])
    return np.interp(y_pred, x, y)


def fit_calibration(y_true, y_pred, method="platt"):
    """Fit calibration and return the model that improves Brier, or None."""
    if method == "platt":
        cal = fit_platt(y_true, y_pred)
        p_cal = apply_platt(y_pred, cal)
    else:
        cal = fit_isotonic(y_true, y_pred)
        p_cal = apply_isotonic(y_pred, cal)

    # Sanity check: no more than 10% of predictions should be exactly 0 or 1
    n_extreme = np.sum((p_cal < 0.001) | (p_cal > 0.999))
    pct_extreme = n_extreme / len(p_cal)
    if pct_extreme > 0.10:
        return None, p_cal, f"REJECTED: {pct_extreme:.0%} extreme predictions (overfit)"

    return cal, p_cal, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# SIGN CONSTRAINT ENFORCEMENT
# ─────────────────────────────────────────────────────────────────────────────

def build_sign_mask():
    """Returns array of +1 / -1 / 0 per feature."""
    return np.array([SIGN_CONSTRAINTS.get(f, 0) for f in FEATURE_NAMES], dtype=np.float32)


def build_floor_mask():
    """Returns array of minimum absolute values per feature (0 = no floor)."""
    return np.array([DOMAIN_FLOORS.get(f, 0.0) for f in FEATURE_NAMES], dtype=np.float32)


def build_cap_mask():
    """Returns array of maximum absolute values per feature (0 = no cap beyond mag_clamp)."""
    return np.array([MAGNITUDE_CAPS.get(f, 0.0) for f in FEATURE_NAMES], dtype=np.float32)


def enforce_signs(w: np.ndarray, mask: np.ndarray, mag_clamp: float = 5.0,
                  floor_mask: np.ndarray = None, cap_mask: np.ndarray = None) -> np.ndarray:
    w = w.copy()
    for i, s in enumerate(mask):
        if s > 0:
            w[i] = max(w[i], 1e-6)
        elif s < 0:
            w[i] = min(w[i], -1e-6)
    # Domain floor enforcement: minimum absolute magnitude
    if floor_mask is not None:
        for i, floor in enumerate(floor_mask):
            if floor > 0:
                sign = SIGN_CONSTRAINTS.get(FEATURE_NAMES[i], 0)
                if sign > 0 and w[i] < floor:
                    w[i] = floor
                elif sign < 0 and w[i] > -floor:
                    w[i] = -floor
    # v4.9: Magnitude cap enforcement — prevents upward drift in specific weights
    if cap_mask is not None:
        for i, cap in enumerate(cap_mask):
            if cap > 0:
                w[i] = np.clip(w[i], -cap, cap)
    if mag_clamp > 0:
        w = np.clip(w, -mag_clamp, mag_clamp)
    return w


# ─────────────────────────────────────────────────────────────────────────────
# GRADIENT COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_gradient(X, y, w, anchor_w, cfg):
    """Compute combined loss gradient with anchor L2 regularization."""
    p = predict(X, w)
    bw = cfg.get('brier_loss_weight', 0.3)
    ls = cfg.get('label_smooth', cfg.get('label_smoothing', 0.02))

    y_smooth = y * (1 - ls) + 0.5 * ls

    # Log-loss gradient
    ll_grad = X.T @ (p - y_smooth) / len(y)

    # Brier gradient
    br_grad = 2 * X.T @ ((p - y) * p * (1 - p)) / len(y)

    # Combined
    grad = (1 - bw) * ll_grad + bw * br_grad

    # Anchor L2 (pull toward anchor)
    l2 = cfg.get('anchor_l2', 0.001)
    grad += l2 * (w - anchor_w)

    return grad


# ─────────────────────────────────────────────────────────────────────────────
# WALK-FORWARD VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward_eval(X, y, dates, w, n_folds=5):
    """Time-based walk-forward: train on past, test on next fold."""
    years = np.sort(np.unique(dates))
    fold_size = max(1, len(years) // n_folds)

    aucs, briers = [], []
    for fold in range(n_folds):
        cutoff_idx = fold_size * (fold + 1)
        train_years = set(years[:cutoff_idx])
        test_years  = set(years[cutoff_idx:cutoff_idx + fold_size])
        if not test_years:
            continue

        tr_mask = np.array([d in train_years for d in dates])
        te_mask = np.array([d in test_years  for d in dates])

        if tr_mask.sum() < 10 or te_mask.sum() < 5:
            continue

        p_te = predict(X[te_mask], w)
        aucs.append(roc_auc(y[te_mask], p_te))
        briers.append(brier_score(y[te_mask], p_te))

    return (np.mean(aucs) if aucs else 0.5,
            np.mean(briers) if briers else 0.25)


# ─────────────────────────────────────────────────────────────────────────────
# CRS — Coordinate Random Search
# ─────────────────────────────────────────────────────────────────────────────

def run_crs(X_tr, y_tr, X_val, y_val, w_init, anchor_w, cfg, sign_mask, floor_mask=None,
            X_all=None, y_all=None, dates_all=None, cap_mask=None):
    """Coordinate random search over individual weights.
    v4.8: CRS objective now includes walk-forward Brier term.
    """
    w = w_init.copy()
    bw       = cfg.get('crs_brier_weight', 0.5)
    aw       = cfg.get('crs_auc_weight', 0.3)
    tw       = cfg.get('crs_train_weight', 0.2)
    wf_w     = cfg.get('crs_wf_weight', 0.3)        # NEW: walk-forward contribution
    sweeps   = cfg.get('crs_sweeps', 30)             # tripled from 10
    trials   = cfg.get('crs_trials_per_weight', 60)  # tripled from 20
    sigma    = cfg.get('crs_initial_sigma', 0.025)
    decay    = cfg.get('crs_sigma_decay', 0.90)
    min_sig  = cfg.get('crs_min_sigma', 0.003)
    mag_clamp= cfg.get('crs_magnitude_clamp', 4.0)
    anc_lam  = cfg.get('crs_anchor_lambda', 0.001)   # tighter: was 0.001, prevents drift
    wf_folds = cfg.get('wf_folds', 5)

    # Pre-compute WF fold masks (expensive, do once)
    wf_masks = []
    if X_all is not None and wf_w > 0:
        years = np.sort(np.unique(dates_all))
        fold_size = max(1, len(years) // wf_folds)
        for fold in range(min(wf_folds, 3)):  # only first 3 folds for speed
            cutoff_idx = fold_size * (fold + 1)
            tr_y = set(years[:cutoff_idx])
            te_y = set(years[cutoff_idx:cutoff_idx + fold_size])
            if not te_y:
                continue
            tr_m = np.array([d in tr_y for d in dates_all])
            te_m = np.array([d in te_y for d in dates_all])
            if tr_m.sum() >= 10 and te_m.sum() >= 5:
                wf_masks.append((tr_m, te_m))

    def score(ww):
        p_tr  = predict(X_tr, ww)
        p_val = predict(X_val, ww)
        val_b = brier_score(y_val, p_val)
        val_a = roc_auc(y_val, p_val)
        tr_b  = brier_score(y_tr, p_tr)
        anchor_pen = anc_lam * np.sum((ww - anchor_w)**2)
        s = bw * val_b - aw * val_a + tw * tr_b + anchor_pen
        # Walk-forward component (use cached fold masks)
        if wf_masks and wf_w > 0:
            wf_briers = [brier_score(y_all[te_m], predict(X_all[te_m], ww))
                         for _, te_m in wf_masks]
            s += wf_w * np.mean(wf_briers)
        return s

    best_score = score(w)
    total_improved = 0

    for sweep in range(sweeps):
        order = np.random.permutation(len(w))
        for idx in order:
            s_constraint = sign_mask[idx]
            floor = floor_mask[idx] if floor_mask is not None else 0.0
            best_val = w[idx]
            for _ in range(trials):
                delta = np.random.randn() * sigma
                candidate = w[idx] + delta
                # Sign constraint
                if s_constraint > 0:
                    candidate = max(candidate, max(1e-6, floor))
                elif s_constraint < 0:
                    candidate = min(candidate, min(-1e-6, -floor))
                # Magnitude clamp
                candidate = np.clip(candidate, -mag_clamp, mag_clamp)
                # v5.0 MAGNITUDE_CAPS + v5.0.2 sign guard + v5.0.3 near-zero freeze
                if cap_mask is not None:
                    cap = cap_mask[idx]
                    if cap > 0:
                        candidate = np.clip(candidate, -cap, cap)
                s_mask = sign_mask[idx]
                if s_mask > 0 and candidate < 1e-6:
                    candidate = 1e-6
                elif s_mask < 0 and candidate > -1e-6:
                    candidate = -1e-6
                w_trial = w.copy()
                w_trial[idx] = candidate
                s = score(w_trial)
                if s < best_score:
                    best_score = s
                    best_val = candidate
                    total_improved += 1
            w[idx] = best_val
        sigma = max(min_sig, sigma * decay)

    return w, total_improved


# ─────────────────────────────────────────────────────────────────────────────
# SWP — Stochastic Weight Perturbation
# ─────────────────────────────────────────────────────────────────────────────

def run_swp(X_tr, y_tr, X_val, y_val, w_init, cfg, sign_mask, floor_mask=None, cap_mask=None):
    """Random walk with accept/reject on validation brier."""
    w = w_init.copy()
    best_w = w.copy()
    best_brier = brier_score(y_val, predict(X_val, w))

    iterations = cfg.get('swp_iterations', 8000)
    sigma      = cfg.get('swp_sigma', 0.007)
    decay      = cfg.get('swp_sigma_decay', 0.9998)

    for i in range(iterations):
        idx     = np.random.randint(len(w))
        delta   = np.random.randn() * sigma
        w_new   = w.copy()
        w_new[idx] += delta

        # Sign constraint
        s = sign_mask[idx]
        floor = floor_mask[idx] if floor_mask is not None else 0.0
        if s > 0:
            w_new[idx] = max(w_new[idx], max(1e-6, floor))
        elif s < 0:
            w_new[idx] = min(w_new[idx], min(-1e-6, -floor))
        # v5.0 caps + v5.0.3 sign guard in SWP
        if cap_mask is not None:
            cap = cap_mask[idx]
            if cap > 0:
                w_new[idx] = np.clip(w_new[idx], -cap, cap)
        if s > 0 and w_new[idx] < 1e-6:
            w_new[idx] = 1e-6
        elif s < 0 and w_new[idx] > -1e-6:
            w_new[idx] = -1e-6

        b = brier_score(y_val, predict(X_val, w_new))
        if b < best_brier:
            best_brier = b
            best_w = w_new.copy()
            w = w_new
        elif b < best_brier * 1.002:  # allow small regression
            w = w_new

        sigma *= decay

    return best_w


# ─────────────────────────────────────────────────────────────────────────────
# ADAM OPTIMIZER
# ─────────────────────────────────────────────────────────────────────────────

class AdamOptimizer:
    def __init__(self, w0, cfg):
        self.w   = w0.copy()
        self.mw  = np.zeros_like(w0)
        self.vw  = np.zeros_like(w0)
        self.mb  = 0.0
        self.vb  = 0.0
        self.b1  = cfg.get('beta1', 0.9)
        self.b2  = cfg.get('beta2', 0.999)
        self.eps = cfg.get('eps', 1e-8)
        self.b1_pow = 1.0
        self.b2_pow = 1.0
        self.step = 0
        self.noise_sigma = cfg.get('gradient_noise_sigma', 0.0001)
        self.noise_decay = cfg.get('gradient_noise_decay', 0.95)
        self.clip = cfg.get('grad_clip', 5.0)

    def update(self, grad, lr):
        self.step += 1
        self.b1_pow *= self.b1
        self.b2_pow *= self.b2

        # Optional gradient noise
        if self.noise_sigma > 0:
            noise = np.random.randn(*grad.shape) * self.noise_sigma
            grad = grad + noise
            self.noise_sigma *= self.noise_decay

        # Clip gradient
        if self.clip > 0:
            gnorm = np.linalg.norm(grad)
            if gnorm > self.clip:
                grad = grad * self.clip / gnorm

        self.mw = self.b1 * self.mw + (1 - self.b1) * grad
        self.vw = self.b2 * self.vw + (1 - self.b2) * grad**2

        mw_hat = self.mw / (1 - self.b1_pow)
        vw_hat = self.vw / (1 - self.b2_pow)

        self.w -= lr * mw_hat / (np.sqrt(vw_hat) + self.eps)
        return self.w

    def load_state(self, state):
        self.mw     = np.array(state['mw'])
        self.vw     = np.array(state['vw'])
        self.b1_pow = state['beta1_pow']
        self.b2_pow = state['beta2_pow']
        self.step   = state['step']


# ─────────────────────────────────────────────────────────────────────────────
# TOP-K SNAPSHOT ENSEMBLE
# ─────────────────────────────────────────────────────────────────────────────

class SnapshotEnsemble:
    def __init__(self, k=15):
        self.k = k
        self.snapshots = []  # list of (val_brier, step, w)

    def maybe_add(self, step, w, val_brier):
        self.snapshots.append((val_brier, step, w.copy()))
        self.snapshots.sort(key=lambda x: x[0])
        if len(self.snapshots) > self.k:
            self.snapshots = self.snapshots[:self.k]

    def ensemble_weights(self):
        if not self.snapshots:
            return None
        if len(self.snapshots) == 1:
            return self.snapshots[0][2].copy()
        # v4.9: inverse-Brier weighted mean — better runs contribute more
        briers = np.array([s[0] for s in self.snapshots])
        ws     = np.array([s[2] for s in self.snapshots])
        # Weight = 1/brier, normalized
        inv_b = 1.0 / (briers + 1e-9)
        inv_b = inv_b / inv_b.sum()
        return (inv_b[:, None] * ws).sum(axis=0)

    def best_weights(self):
        if not self.snapshots:
            return None
        return self.snapshots[0][2].copy()

    def best_brier(self):
        if not self.snapshots:
            return float('inf')
        return self.snapshots[0][0]


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING PHASES
# ─────────────────────────────────────────────────────────────────────────────

def get_lr_schedule(cfg):
    """Returns list of (phase_name, lr, n_steps) tuples.
    v4.9: Adam dropped entirely. Confirmed useless in 3 consecutive runs:
      v1085: Adam best 0.14851, anchor 0.11975 — CRS rescued to 0.12375
      v1086: Adam best 0.13037, anchor 0.12375 — CRS rescued to 0.11200
    Total of 58 Adam steps produced 1 improvement. Budget moved to CRS+basin hopping.
    Set skip_adam=False in config to re-enable (not recommended).
    """
    if cfg.get('skip_adam', True):
        return []   # Skip Adam entirely → go straight to CRS
    schedule = []
    for cycle in range(cfg.get('phase1_cycles', 1)):
        schedule.append(('EXPLORE', cfg.get('phase1_lr', 0.0005),
                         cfg.get('phase1_steps_per_cycle', 100)))
    for cycle in range(cfg.get('phase2_cycles', 1)):
        schedule.append(('REFINE', cfg.get('phase2_lr', 0.0001),
                         cfg.get('phase2_steps_per_cycle', 150)))
    return schedule


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY WRITER
# ─────────────────────────────────────────────────────────────────────────────

class HistoryWriter:
    def __init__(self, path, resume=False):
        self.path = path
        self.fh = None
        mode = 'a' if resume else 'w'
        self.fh = open(path, mode, buffering=1)
        if not resume or os.path.getsize(path) == 0:
            self.fh.write("Timestamp,Step,Cycle,Phase,LR,Train_Brier,Train_LogLoss,"
                          "Train_AUC,Val_Brier,Val_LogLoss,Val_AUC,Best_Val_Brier,Improved\n")

    def write(self, ts, step, cycle, phase, lr, tr_b, tr_ll, tr_auc,
              val_b, val_ll, val_auc, best_b, improved):
        self.fh.write(f"{ts},{step},{cycle},{phase},{lr:.8f},"
                      f"{tr_b:.8f},{tr_ll:.8f},{tr_auc:.4f},"
                      f"{val_b:.8f},{val_ll:.8f},{val_auc:.4f},"
                      f"{best_b:.8f},{'YES' if improved else 'no'}\n")

    def close(self):
        if self.fh:
            self.fh.close()


# ─────────────────────────────────────────────────────────────────────────────
# SAVE / LOAD STATE
# ─────────────────────────────────────────────────────────────────────────────

def save_state(path, adam, best_w, best_b, ensemble, step, phase, cfg, trainable_mask):
    state = {
        "step": step,
        "w": adam.w.tolist(),
        "b": 0.0,
        "mw": adam.mw.tolist(),
        "vw": adam.vw.tolist(),
        "mb": 0.0,
        "vb": 0.0,
        "beta1_pow": adam.b1_pow,
        "beta2_pow": adam.b2_pow,
        "best_val_brier": best_b,
        "best_val_logloss": 0.0,
        "best_step": step,
        "best_w": best_w.tolist(),
        "best_b": 0.0,
        "steps_since_improvement": 0,
        "snapshots": [{"step": s[1], "w": s[2].tolist(), "b": 0.0, "val_brier": s[0]}
                      for s in ensemble.snapshots],
        "trainable_mask": trainable_mask.tolist(),
        "config": cfg,
    }
    with open(path, 'w') as f:
        json.dump(state, f, cls=NumpyEncoder)


class NumpyEncoder(json.JSONEncoder):
    """Handle numpy scalars and arrays for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def weights_to_json(w, anchor, iso_cal, metadata):
    """Package weights into output JSON matching honed model format."""
    skip = {'_anchor_source','_baseline_val_brier','_baseline_wf_auc',
            'honing_metadata','isotonic_calibration'}
    out = {}
    for i, name in enumerate(FEATURE_NAMES):
        out[name] = float(w[i])
    out['_anchor_source'] = anchor.get('_anchor_source', 'unknown')
    out['_baseline_val_brier'] = anchor.get('_baseline_val_brier', 0.0)
    out['_baseline_wf_auc'] = anchor.get('_baseline_wf_auc', 0.0)
    out['honing_metadata'] = metadata
    out['isotonic_calibration'] = iso_cal
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TRAINING LOOP
# ─────────────────────────────────────────────────────────────────────────────

# ── Performance Rating System ─────────────────────────────────────────────────
def get_performance_rating(val_brier, wf_brier):
    """Rate model performance with custom tier names."""
    score = min(val_brier, wf_brier) if wf_brier > 0 else val_brier
    TIERS = [
        (0.075, "SHAWN TIER",            "👑 GOAT STATUS — The All-Seeing Eye of ODIN"),
        (0.080, "David's Inner Circle",   "🔥 Elite — Approaching omniscience"),
        (0.085, "Valkyrie Tier",          "⚡ Exceptional — Worthy of Valhalla"),
        (0.090, "Gungnir Tier",           "🎯 Excellent — The spear that never misses"),
        (0.095, "Huginn & Muninn Tier",   "🐦 Strong — Thought & Memory working overtime"),
        (0.100, "Einherjar Tier",         "⚔️  Solid — Battle-tested warrior"),
        (0.105, "Midgard Tier",           "🌍 Decent — Respectable mortal performance"),
        (0.110, "Bifrost Tier",           "🌈 OK — Bridge between mediocre and good"),
        (0.115, "Loki Tier",              "🃏 Meh — Trickster energy, unreliable"),
        (0.120, "Fenrir Tier",            "🐺 Bad — Chained up for a reason"),
        (0.130, "Ragnarok Tier",          "💀 Terrible — End times approaching"),
        (9.999, "TAD & TBALL TIER",       "🗑️  ABSOLUTE GARBAGE — Delete and start over"),
    ]
    for threshold, name, desc in TIERS:
        if score < threshold:
            return name, desc
    return TIERS[-1][1], TIERS[-1][2]


def train(args):
    # ── Load config ──────────────────────────────────────────────────────────
    cfg_path = args.config if args.config else DEFAULT_CONFIG
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = json.load(f)
        print(f"[Config] Loaded {cfg_path}")
    else:
        print(f"[Config] {cfg_path} not found, using defaults")
        cfg = {}

    # ── Load anchor ──────────────────────────────────────────────────────────
    anchor_path = args.anchor if args.anchor else DEFAULT_ANCHOR
    with open(anchor_path) as f:
        anchor = json.load(f)
    print(f"[Anchor] Loaded {anchor_path}")

    # Build anchor weight vector
    skip = {'_anchor_source','_baseline_val_brier','_baseline_wf_auc',
            'honing_metadata','isotonic_calibration'}
    anchor_w = np.array([float(anchor.get(name, 0.0)) for name in FEATURE_NAMES],
                        dtype=np.float64)

    # Apply feature prior nudges from config
    nudges = cfg.get('feature_prior_nudges', {})
    for fname, nudge in nudges.items():
        if fname in FEATURE_NAMES:
            idx = FEATURE_NAMES.index(fname)
            if abs(anchor_w[idx]) < abs(nudge):  # only nudge if currently near-zero
                anchor_w[idx] = nudge
                print(f"[Nudge] {fname}: {anchor_w[idx]:.4f} (was near-zero)")

    # ── Load data ────────────────────────────────────────────────────────────
    data_path = args.data if args.data else DEFAULT_DATA
    X, y, dates = load_data(data_path)

    # Train/val split (time-based: last val_frac years = val)
    val_frac = cfg.get('val_frac', 0.2)
    year_cutoff = np.percentile(dates, (1 - val_frac) * 100)
    tr_mask  = dates <= year_cutoff
    val_mask = dates > year_cutoff
    print(f"[Split] Train: {tr_mask.sum()}, Val: {val_mask.sum()} (cutoff year ~{year_cutoff:.0f})")

    X_tr, y_tr = X[tr_mask], y[tr_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    sign_mask = build_sign_mask()
    floor_mask = build_floor_mask()
    cap_mask = build_cap_mask()
    trainable_mask = np.ones(len(FEATURE_NAMES), dtype=np.float32)

    # ── Initialize or resume ─────────────────────────────────────────────────
    w0 = anchor_w.copy()
    adam = AdamOptimizer(w0, cfg)
    ensemble = SnapshotEnsemble(k=cfg.get('top_k_snapshots', 15))
    best_val_brier = float('inf')
    best_w = w0.copy()
    global_step = 0
    start_phase_idx = 0

    if args.resume and os.path.exists(STATE_FILE):
        print(f"[Resume] Loading {STATE_FILE}")
        with open(STATE_FILE) as f:
            state = json.load(f)
        w0 = np.array(state['w'])
        adam.w = w0.copy()
        adam.load_state(state)
        best_w = np.array(state['best_w'])
        best_val_brier = state['best_val_brier']
        global_step = state['step']
        # Restore ensemble snapshots
        for snap in state.get('snapshots', []):
            ensemble.maybe_add(snap['step'], np.array(snap['w']), snap['val_brier'])
        print(f"[Resume] Restored step {global_step}, best brier {best_val_brier:.5f}")

    # ── History writer ───────────────────────────────────────────────────────
    hw = HistoryWriter(HISTORY_FILE, resume=args.resume)

    # ── LR schedule ─────────────────────────────────────────────────────────
    schedule = get_lr_schedule(cfg)
    eval_every = cfg.get('eval_every', 25)
    patience   = cfg.get('patience', 200)
    stall_thresh = cfg.get('stall_threshold', 1e-7)
    steps_since_improve = 0
    snap_every = cfg.get('snapshot_every', 25)

    print(f"\n[Honing] Starting from step {global_step}")
    print(f"[Honing] Schedule: {[(p, n) for p, lr, n in schedule]}")
    print(f"[Honing] Target: val Brier < {anchor.get('_baseline_val_brier', 0.13):.5f}")

    t_start = time.time()

    for phase_name, lr, n_steps in schedule:
        print(f"\n{'='*60}")
        print(f"Phase: {phase_name}  LR={lr:.2e}  Steps={n_steps}")
        print(f"{'='*60}")
        steps_since_improve = 0

        for step in range(1, n_steps + 1):
            global_step += 1

            # Gradient step
            grad = compute_gradient(X_tr, y_tr, adam.w, anchor_w, cfg)
            adam.update(grad, lr)

            # Sign constraints + domain floors
            adam.w = enforce_signs(adam.w, sign_mask,
                                   mag_clamp=cfg.get('magnitude_clamp', 5.0),
                                   floor_mask=floor_mask,
                                   cap_mask=cap_mask)

            # Evaluate
            if step % eval_every == 0:
                p_val = predict(X_val, adam.w)
                p_tr  = predict(X_tr,  adam.w)

                val_b  = brier_score(y_val, p_val)
                val_ll = log_loss(y_val, p_val)
                val_auc= roc_auc(y_val, p_val)
                tr_b   = brier_score(y_tr, p_tr)
                tr_ll  = log_loss(y_tr, p_tr)
                tr_auc = roc_auc(y_tr, p_tr)

                improved = val_b < best_val_brier - stall_thresh
                if improved:
                    best_val_brier = val_b
                    best_w = adam.w.copy()
                    steps_since_improve = 0
                else:
                    steps_since_improve += eval_every

                ensemble.maybe_add(global_step, adam.w, val_b)

                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                hw.write(ts, global_step, 0, phase_name, lr,
                         tr_b, tr_ll, tr_auc,
                         val_b, val_ll, val_auc,
                         best_val_brier, improved)

                elapsed = time.time() - t_start
                print(f"  [{phase_name}] Step {global_step:>5} | "
                      f"Val Brier={val_b:.5f} | AUC={val_auc:.4f} | "
                      f"Train={tr_b:.5f} | Best={best_val_brier:.5f} "
                      f"{'✓' if improved else ' '} | {elapsed:.0f}s")

            # Snapshot
            if step % snap_every == 0:
                save_state(STATE_FILE, adam, best_w, best_val_brier,
                           ensemble, global_step, phase_name, cfg, trainable_mask)

            # Patience check in POLISH
            if phase_name == 'POLISH' and steps_since_improve >= patience:
                print(f"  [Patience] {patience} steps without improvement — exiting POLISH early")
                break

    # ── Post-loop: CRS ───────────────────────────────────────────────────────
    # Reset ensemble — Adam snapshots may be early/noisy. Rebuild from CRS/SWP only.
    post_ensemble = SnapshotEnsemble(k=cfg.get('top_k_snapshots', 15))
    post_ensemble.maybe_add(global_step, best_w.copy(), best_val_brier)

    if cfg.get('crs_enabled', True):
        n_runs = cfg.get('multi_seed_runs', 3)
        print(f"\n[CRS] Running coordinate random search "
              f"({cfg.get('crs_sweeps',30)} sweeps × {cfg.get('crs_trials_per_weight',60)} trials × {n_runs} runs)...")
        crs_candidates = []
        for crs_run in range(n_runs):
            if crs_run == 0:
                # First run: start from current best
                seed_w = best_w.copy()
            else:
                # v4.9 FIX: Diverse seeds from ANCHOR + large noise, not best_w + tiny noise.
                # This gives CRS genuinely different starting points to explore.
                diverse_sigma = cfg.get('crs_diverse_seed_sigma', 0.15)
                seed_w = anchor_w + np.random.randn(*anchor_w.shape) * diverse_sigma
            seed_w = enforce_signs(seed_w, sign_mask, cfg.get('magnitude_clamp', 5.0),
                                   floor_mask, cap_mask)
            w_c, n_imp = run_crs(X_tr, y_tr, X_val, y_val, seed_w, anchor_w, cfg, sign_mask,
                                 floor_mask=floor_mask, cap_mask=cap_mask,
                                 X_all=X, y_all=y, dates_all=dates)
            b_c = brier_score(y_val, predict(X_val, w_c))
            crs_candidates.append((b_c, w_c, n_imp))
            post_ensemble.maybe_add(global_step + 1000 + crs_run, w_c, b_c)

        best_crs = min(crs_candidates, key=lambda x: x[0])
        crs_brier, w_crs, n_improved = best_crs
        print(f"[CRS] Brier: {best_val_brier:.5f} → {crs_brier:.5f} "
              f"({sum(c[2] for c in crs_candidates)} improvements across {n_runs} runs)")
        if crs_brier < best_val_brier:
            best_val_brier = crs_brier
            best_w = w_crs

    # ── Post-loop: SWP ───────────────────────────────────────────────────────
    if cfg.get('swp_enabled', True):
        print(f"\n[SWP] Running stochastic weight perturbation...")
        w_swp = run_swp(X_tr, y_tr, X_val, y_val, best_w, cfg, sign_mask, floor_mask=floor_mask, cap_mask=cap_mask)
        p_swp = predict(X_val, w_swp)
        swp_brier = brier_score(y_val, p_swp)
        print(f"[SWP] Brier: {best_val_brier:.5f} → {swp_brier:.5f}")
        if swp_brier < best_val_brier:
            best_val_brier = swp_brier
            best_w = w_swp
        post_ensemble.maybe_add(global_step + 2000, w_swp, swp_brier)

    # ── v4.9: Basin Hopping — global search after local convergence ──────────
    n_hops = cfg.get('basin_hops', 5)
    hop_sigma = cfg.get('basin_hop_sigma', 0.20)
    if n_hops > 0:
        print(f"\n[BasinHop] {n_hops} restarts from anchor+noise(σ={hop_sigma}) → CRS each...")
        hop_best_brier = best_val_brier
        hop_best_w = best_w.copy()
        for hop in range(n_hops):
            # Large perturbation from anchor — not from current best (escape local minimum)
            hop_w = anchor_w + np.random.randn(*anchor_w.shape) * hop_sigma
            hop_w = enforce_signs(hop_w, sign_mask, cfg.get('magnitude_clamp', 5.0),
                                  floor_mask, cap_mask)
            # Mini-CRS from this new starting point
            hop_cfg = dict(cfg)
            hop_cfg['crs_sweeps'] = max(8, cfg.get('crs_sweeps', 30) // 3)
            hop_cfg['crs_trials_per_weight'] = max(20, cfg.get('crs_trials_per_weight', 60) // 3)
            w_hop, _ = run_crs(X_tr, y_tr, X_val, y_val, hop_w, anchor_w, hop_cfg, sign_mask,
                               floor_mask=floor_mask, cap_mask=cap_mask,
                               X_all=X, y_all=y, dates_all=dates)
            b_hop = brier_score(y_val, predict(X_val, w_hop))
            post_ensemble.maybe_add(global_step + 4000 + hop, w_hop, b_hop)
            status = ''
            if b_hop < hop_best_brier:
                hop_best_brier = b_hop
                hop_best_w = w_hop
                status = ' ← NEW BEST'
            print(f"  [Hop {hop+1}/{n_hops}] Brier={b_hop:.5f}{status}")
        if hop_best_brier < best_val_brier:
            print(f"[BasinHop] Improved: {best_val_brier:.5f} → {hop_best_brier:.5f}")
            swp_cfg = dict(cfg)
            swp_cfg['swp_iterations'] = min(5000, cfg.get('swp_iterations', 8000) // 4)
            swp_cfg['swp_sigma'] = cfg.get('swp_sigma', 0.008) * 0.6
            hop_refined = run_swp(X_tr, y_tr, X_val, y_val, hop_best_w, swp_cfg,
                                  sign_mask, floor_mask=floor_mask, cap_mask=cap_mask)
            b_refined = brier_score(y_val, predict(X_val, hop_refined))
            if b_refined < hop_best_brier:
                print(f"  [BasinHop→SWP] Refined: {hop_best_brier:.5f} → {b_refined:.5f}")
                hop_best_brier = b_refined
                hop_best_w = hop_refined
            best_val_brier = hop_best_brier
            best_w = hop_best_w
        else:
            print(f"[BasinHop] No improvement (best still {best_val_brier:.5f})")

    # Always include final best in post-ensemble
    post_ensemble.maybe_add(global_step + 3000, best_w.copy(), best_val_brier)

    # ── Walk-forward eval ────────────────────────────────────────────────────
    print("\n[Walk-Forward] Evaluating...")
    wf_auc, wf_brier = walk_forward_eval(X, y, dates, best_w,
                                          n_folds=cfg.get('wf_folds', 5))
    print(f"[Walk-Forward] AUC={wf_auc:.4f}  Brier={wf_brier:.5f}")

    # Ensemble weights — built only from post-CRS/SWP candidates
    ens_w = post_ensemble.ensemble_weights()
    if ens_w is not None:
        p_ens = predict(X_val, ens_w)
        ens_brier = brier_score(y_val, p_ens)
        ens_auc   = roc_auc(y_val, p_ens)
        print(f"[Ensemble] {len(post_ensemble.snapshots)} candidates | "
              f"AUC={ens_auc:.4f}  Brier={ens_brier:.5f}")
        # If ensemble is worse than best single, fall back
        if ens_brier > best_val_brier * 1.01:
            print(f"[Ensemble] Ensemble worse than best single — using best single for output")
            ens_w = best_w.copy()
            ens_brier = best_val_brier
    else:
        ens_brier = best_val_brier
        ens_w = best_w

    # ── Calibration (Platt scaling — replaces overfit PAV isotonic) ──────────
    iso_cal = None
    cal_brier = best_val_brier
    cal_wf_brier = wf_brier
    if cfg.get('isotonic_calibration', True):
        print("\n[Calibration] Fitting Platt scaling...")
        p_val_best = predict(X_val, best_w)

        # Try Platt first; fall back to PAV isotonic if rejected
        cal_candidate, p_cal, status = fit_calibration(y_val, p_val_best, method="platt")
        if cal_candidate is None:
            print(f"[Calibration] Platt: {status} — trying isotonic fallback")
            cal_candidate, p_cal, status = fit_calibration(y_val, p_val_best, method="isotonic")
            if cal_candidate is None:
                print(f"[Calibration] Isotonic: {status} — skipping calibration")

        if cal_candidate is not None:
            cal_brier_candidate = brier_score(y_val, p_cal)
            gain = best_val_brier - cal_brier_candidate
            print(f"[Calibration] Val Brier: {best_val_brier:.5f} → {cal_brier_candidate:.5f} "
                  f"(gain={gain:.5f}, method={cal_candidate.get('type','?')}, status={status})")

            if gain > 0:
                iso_cal = cal_candidate
                cal_brier = cal_brier_candidate
                print(f"[Calibration] ✓ Applied")

                # Calibrated walk-forward
                cal_briers = []
                years = np.sort(np.unique(dates))
                fold_size = max(1, len(years) // cfg.get('wf_folds', 5))
                for fold in range(cfg.get('wf_folds', 5)):
                    cutoff_idx = fold_size * (fold + 1)
                    tr_y = set(years[:cutoff_idx])
                    te_y = set(years[cutoff_idx:cutoff_idx + fold_size])
                    if not te_y:
                        continue
                    tr_m = np.array([d in tr_y for d in dates])
                    te_m = np.array([d in te_y  for d in dates])
                    if tr_m.sum() < 10 or te_m.sum() < 5:
                        continue
                    p_te = predict(X[te_m], best_w)
                    p_te_cal = apply_platt(p_te, iso_cal) if iso_cal.get('type') == 'platt' \
                               else apply_isotonic(p_te, iso_cal)
                    cal_briers.append(brier_score(y[te_m], p_te_cal))
                cal_wf_brier = np.mean(cal_briers) if cal_briers else wf_brier
                print(f"[Calibration] WF Brier (calibrated): {cal_wf_brier:.5f}")
            else:
                print(f"[Calibration] ✗ Hurts val Brier — inheriting anchor calibration")
                iso_cal = anchor.get('isotonic_calibration', None) or {}
                cal_brier = best_val_brier
        else:
            iso_cal = anchor.get('isotonic_calibration', None) or {}
    else:
        iso_cal = anchor.get('isotonic_calibration', {})
        cal_wf_brier = wf_brier

    # ── Package outputs ───────────────────────────────────────────────────────
    ts_now = datetime.now().isoformat()
    metadata = {
        "engine_version": "5.1.0",
        "timestamp": ts_now,
        "anchor_file": anchor_path,
        "data_file": data_path,
        "model_type": "pdufa",
        "baseline_val_brier": float(anchor.get('_baseline_val_brier', 0.0)),
        "baseline_val_auc": float(anchor.get('_baseline_wf_auc', 0.0)),
        "final_val_brier": float(best_val_brier),
        "final_val_auc": float(wf_auc),
        "brier_improvement": float(float(anchor.get('_baseline_val_brier', best_val_brier)) - best_val_brier),
        "walk_forward_mean_auc": float(wf_auc),
        "walk_forward_mean_brier": float(wf_brier),
        "rounds_completed": 1,
        "calibrated_val_brier": float(cal_brier),
        "calibration_gain": float(best_val_brier - cal_brier),
        "calibrated_wf_brier_mean": float(cal_wf_brier),
    }

    honed_out = weights_to_json(best_w, anchor, iso_cal or {}, metadata)
    with open(OUTPUT_HONED, 'w') as f:
        json.dump(honed_out, f, indent=2, cls=NumpyEncoder)
    print(f"\n[Output] Saved honed weights → {OUTPUT_HONED}")

    ens_metadata = dict(metadata)
    ens_metadata['type'] = 'ensemble_top_k'
    ens_out = weights_to_json(ens_w, anchor, iso_cal or {}, ens_metadata)
    with open(OUTPUT_ENSEMBLE, 'w') as f:
        json.dump(ens_out, f, indent=2, cls=NumpyEncoder)
    print(f"[Output] Saved ensemble weights → {OUTPUT_ENSEMBLE}")

    # Final save of state
    save_state(STATE_FILE, adam, best_w, best_val_brier,
               ensemble, global_step, 'DONE', cfg, trainable_mask)

    # ── Summary ───────────────────────────────────────────────────────────────
    tier_name, tier_desc = get_performance_rating(best_val_brier, cal_wf_brier)
    anchor_brier = float(anchor.get('_baseline_val_brier', best_val_brier))
    total_improvement = anchor_brier - best_val_brier
    pct_improvement = (total_improvement / anchor_brier * 100) if anchor_brier > 0 else 0
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  HONING COMPLETE                                                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  Val Brier (uncal):     {best_val_brier:.5f}                                   ║
║  Val Brier (calibrated):{cal_brier:.5f}                                   ║
║  Walk-Forward AUC:      {wf_auc:.4f}                                    ║
║  WF Brier (calibrated): {cal_wf_brier:.5f}                                   ║
║  Total steps:           {global_step:<10}                                 ║
║  Improvement:           {total_improvement:+.5f} ({pct_improvement:+.1f}%)                           ║
║  Output:                {OUTPUT_HONED:<45}║
║  Ensemble:              {OUTPUT_ENSEMBLE:<45}║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  PERFORMANCE RATING:  {tier_name:<44}║
║  {tier_desc:<65}║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    hw.close()
    return best_w, best_val_brier


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ODIN Honing Engine v5.1 (Interactions)")
    parser.add_argument('--resume',  action='store_true', help='Resume from state file')
    parser.add_argument('--anchor',  type=str, default=None, help='Anchor weights JSON')
    parser.add_argument('--data',    type=str, default=None, help='Training data CSV')
    parser.add_argument('--config',  type=str, default=None, help='Honing config JSON')
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ODIN HONING ENGINE v5.1 — Interaction Features                 ║
║  CRS-Primary + Platt Cal + Interactions (54 weights)            ║
╠══════════════════════════════════════════════════════════════╣
║  Anchor:  {(args.anchor or DEFAULT_ANCHOR):<50}║
║  Data:    {(args.data or DEFAULT_DATA):<50}║
║  Config:  {(args.config or DEFAULT_CONFIG):<50}║
║  Resume:  {str(args.resume):<50}║
╚══════════════════════════════════════════════════════════════╝
""")

    train(args)


if __name__ == '__main__':
    main()
