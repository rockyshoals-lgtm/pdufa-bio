#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                ODIN PERPETUAL HONING ENGINE v4.0                            ║
║                Self-Contained Convergent Optimizer                           ║
║                                                                              ║
║  FIXES from v1-v3:                                                           ║
║   • v1 diverged (LR 0.002 too high, stall detection too tight)              ║
║   • v3 best at step ~200 then diverged → micro-cycles, aggressive stops     ║
║   • v1079 weights exploded → sign constraints + magnitude clamping          ║
║                                                                              ║
║  Architecture:                                                               ║
║   Phase 1: Exploration (micro-cycles of 200 steps, cosine LR)               ║
║   Phase 2: Refinement (longer cycles, decaying LR envelope)                  ║
║   Phase 3: Polishing (ultra-low LR until convergence)                        ║
║   + Top-K ensemble snapshots throughout                                      ║
║                                                                              ║
║  Supports: PDUFA logit-space models (v10.66+)                               ║
║            Phase/BTA readout models (v2.x)                                   ║
║            Gungnir NLP readout models                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import json
import os
import sys
import csv
import math
import copy
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

__version__ = "4.0.0"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    # --- Three-Phase LR Schedule ---
    "phase1_lr": 0.0005,        # Exploration peak LR
    "phase1_cycles": 5,         # Number of micro-cycles
    "phase1_steps_per_cycle": 200,  # Steps per micro-cycle (matches empirical sweet spot)

    "phase2_lr": 0.0001,        # Refinement peak LR
    "phase2_cycles": 10,        # Number of longer cycles
    "phase2_steps_per_cycle": 500,

    "phase3_lr": 0.00001,       # Polishing LR
    "phase3_max_steps": 5000,   # Max steps for final polish

    # --- Adam ---
    "beta1": 0.9,
    "beta2": 0.999,
    "eps": 1e-8,
    "grad_clip": 5.0,

    # --- Anchoring ---
    "anchor_l2": 0.003,         # L2 penalty toward anchor weights
    "anchor_b": 0.003,          # L2 penalty toward anchor bias/intercept

    # --- Convergence ---
    "patience": 300,            # Steps without improvement → end current phase
    "stall_threshold": 1e-7,    # Minimum improvement to count
    "max_total_steps": 50000,   # Hard ceiling

    # --- Validation ---
    "val_frac": 0.2,            # Time-split validation fraction
    "eval_every": 25,           # Evaluate every N steps

    # --- Ensemble ---
    "top_k_snapshots": 10,      # Keep top K checkpoints
    "snapshot_every": 25,       # Snapshot frequency

    # --- Guardrails ---
    "sign_constrained": True,   # Enforce original sign direction
    "magnitude_clamp": 3.0,     # Max ratio vs anchor weight (0=off)
    "weight_clip": 0.0,         # Absolute weight clip (0=off)

    # --- Self-Learning Loop ---
    "self_improve_rounds": 20,  # Max self-improvement iterations
    "self_improve_min_gain": 1e-5,  # Min Brier improvement per round
}


# ═══════════════════════════════════════════════════════════════════════════════
# ADAM OPTIMIZER (self-contained, no external dependencies)
# ═══════════════════════════════════════════════════════════════════════════════

class AdamOptimizer:
    """Adam optimizer with L2 anchoring and sign constraints."""

    def __init__(self, n_params: int, anchor_w: np.ndarray, anchor_b: float,
                 config: dict, trainable_mask: Optional[np.ndarray] = None,
                 sign_ref: Optional[np.ndarray] = None):
        self.n = n_params
        self.anchor_w = anchor_w.copy()
        self.anchor_b = anchor_b

        self.w = anchor_w.copy()
        self.b = anchor_b

        self.mw = np.zeros(n_params)
        self.vw = np.zeros(n_params)
        self.mb = 0.0
        self.vb = 0.0
        self.beta1_pow = 1.0
        self.beta2_pow = 1.0

        self.config = config
        self.step = 0

        # Trainable mask: 1 = optimize, 0 = frozen
        self.trainable_mask = trainable_mask if trainable_mask is not None else np.ones(n_params)

        # Sign reference for sign constraints
        self.sign_ref = sign_ref

        # Best tracking
        self.best_val_brier = float('inf')
        self.best_val_logloss = float('inf')
        self.best_step = 0
        self.best_w = anchor_w.copy()
        self.best_b = anchor_b
        self.steps_since_improvement = 0

        # Snapshot tracking
        self.snapshots: List[dict] = []

    def update(self, grad_w: np.ndarray, grad_b: float, lr: float):
        """Single Adam step with anchoring and constraints."""
        cfg = self.config
        self.step += 1

        # Apply trainable mask
        grad_w = grad_w * self.trainable_mask

        # Add L2 anchor penalty gradients
        anchor_grad_w = cfg['anchor_l2'] * (self.w - self.anchor_w)
        anchor_grad_b = cfg['anchor_b'] * (self.b - self.anchor_b)
        grad_w = grad_w + anchor_grad_w
        grad_b = grad_b + anchor_grad_b

        # Gradient clipping
        grad_norm = np.sqrt(np.sum(grad_w**2) + grad_b**2)
        if grad_norm > cfg['grad_clip']:
            scale = cfg['grad_clip'] / (grad_norm + 1e-12)
            grad_w *= scale
            grad_b *= scale

        # Adam moments
        beta1, beta2, eps = cfg['beta1'], cfg['beta2'], cfg['eps']
        self.mw = beta1 * self.mw + (1 - beta1) * grad_w
        self.vw = beta2 * self.vw + (1 - beta2) * grad_w**2
        self.mb = beta1 * self.mb + (1 - beta1) * grad_b
        self.vb = beta2 * self.vb + (1 - beta2) * grad_b**2

        self.beta1_pow *= beta1
        self.beta2_pow *= beta2

        # Bias correction
        mw_hat = self.mw / (1 - self.beta1_pow)
        vw_hat = self.vw / (1 - self.beta2_pow)
        mb_hat = self.mb / (1 - self.beta1_pow)
        vb_hat = self.vb / (1 - self.beta2_pow)

        # Update
        self.w -= lr * mw_hat / (np.sqrt(vw_hat) + eps) * self.trainable_mask
        self.b -= lr * mb_hat / (np.sqrt(vb_hat) + eps)

        # --- Guardrails ---
        # Sign constraint: keep weights on the same side as anchor
        if cfg.get('sign_constrained') and self.sign_ref is not None:
            for i in range(self.n):
                if self.trainable_mask[i] == 0:
                    continue
                if self.sign_ref[i] > 0 and self.w[i] < 0:
                    self.w[i] = 0.0
                elif self.sign_ref[i] < 0 and self.w[i] > 0:
                    self.w[i] = 0.0

        # Magnitude clamping: don't let weights grow beyond N× anchor
        mag_clamp = cfg.get('magnitude_clamp', 0.0)
        if mag_clamp > 0:
            for i in range(self.n):
                if self.trainable_mask[i] == 0:
                    continue
                ref = abs(self.anchor_w[i])
                if ref > 0.01:  # Only clamp non-trivial weights
                    max_val = ref * mag_clamp
                    self.w[i] = np.clip(self.w[i], -max_val, max_val)

        # Hard weight clip
        if cfg.get('weight_clip', 0) > 0:
            self.w = np.clip(self.w, -cfg['weight_clip'], cfg['weight_clip'])

    def record_eval(self, val_brier: float, val_logloss: float):
        """Record validation metrics and track best."""
        improved = False
        if val_brier < self.best_val_brier - self.config['stall_threshold']:
            self.best_val_brier = val_brier
            self.best_val_logloss = val_logloss
            self.best_step = self.step
            self.best_w = self.w.copy()
            self.best_b = float(self.b)
            self.steps_since_improvement = 0
            improved = True
        else:
            self.steps_since_improvement += self.config['eval_every']
        return improved

    def take_snapshot(self, val_brier: float):
        """Take a snapshot for ensemble."""
        self.snapshots.append({
            'step': self.step,
            'w': self.w.copy(),
            'b': float(self.b),
            'val_brier': val_brier,
        })
        # Keep only top K
        self.snapshots.sort(key=lambda s: s['val_brier'])
        self.snapshots = self.snapshots[:self.config['top_k_snapshots']]

    def get_ensemble(self) -> Tuple[np.ndarray, float]:
        """Average top-K snapshots."""
        if not self.snapshots:
            return self.best_w.copy(), self.best_b

        ws = np.array([s['w'] for s in self.snapshots])
        bs = np.array([s['b'] for s in self.snapshots])
        return ws.mean(axis=0), float(bs.mean())

    @property
    def patience_exceeded(self) -> bool:
        return self.steps_since_improvement >= self.config['patience']

    def get_state(self) -> dict:
        """Full serializable state for resume."""
        return {
            'step': self.step,
            'w': self.w.tolist(),
            'b': float(self.b),
            'mw': self.mw.tolist(),
            'vw': self.vw.tolist(),
            'mb': float(self.mb),
            'vb': float(self.vb),
            'beta1_pow': float(self.beta1_pow),
            'beta2_pow': float(self.beta2_pow),
            'best_val_brier': float(self.best_val_brier),
            'best_val_logloss': float(self.best_val_logloss),
            'best_step': self.best_step,
            'best_w': self.best_w.tolist(),
            'best_b': float(self.best_b),
            'steps_since_improvement': self.steps_since_improvement,
            'snapshots': [{'step': s['step'], 'w': s['w'].tolist(),
                           'b': s['b'], 'val_brier': s['val_brier']}
                          for s in self.snapshots],
            'trainable_mask': self.trainable_mask.tolist(),
            'config': self.config,
        }

    def load_state(self, state: dict):
        """Restore from saved state."""
        self.step = state['step']
        self.w = np.array(state['w'])
        self.b = state['b']
        self.mw = np.array(state['mw'])
        self.vw = np.array(state['vw'])
        self.mb = state['mb']
        self.vb = state['vb']
        self.beta1_pow = state['beta1_pow']
        self.beta2_pow = state['beta2_pow']
        self.best_val_brier = state['best_val_brier']
        self.best_val_logloss = state.get('best_val_logloss', float('inf'))
        self.best_step = state['best_step']
        self.best_w = np.array(state['best_w'])
        self.best_b = state['best_b']
        self.steps_since_improvement = state.get('steps_since_improvement', 0)
        self.snapshots = [{'step': s['step'], 'w': np.array(s['w']),
                           'b': s['b'], 'val_brier': s['val_brier']}
                          for s in state.get('snapshots', [])]


# ═══════════════════════════════════════════════════════════════════════════════
# LOGISTIC REGRESSION LOSS & GRADIENTS
# ═══════════════════════════════════════════════════════════════════════════════

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def logistic_loss_and_grad(X, y, w, b):
    """Compute log-loss and gradients for logistic regression.

    X: (N, D) feature matrix
    y: (N,) binary labels
    w: (D,) weights
    b: scalar bias

    Returns: loss, grad_w, grad_b, predictions
    """
    N = X.shape[0]
    logits = X @ w + b
    preds = sigmoid(logits)

    # Clamp for numerical stability
    preds_safe = np.clip(preds, 1e-12, 1 - 1e-12)

    # Log-loss
    loss = -np.mean(y * np.log(preds_safe) + (1 - y) * np.log(1 - preds_safe))

    # Gradients
    errors = preds_safe - y  # (N,)
    grad_w = (X.T @ errors) / N  # (D,)
    grad_b = np.mean(errors)

    return loss, grad_w, grad_b, preds

def brier_score(preds, y):
    return np.mean((preds - y) ** 2)

def auc_score(preds, y):
    """Simple AUC computation without sklearn."""
    pos = preds[y == 1]
    neg = preds[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    # Mann-Whitney U statistic
    n_pos, n_neg = len(pos), len(neg)
    u = 0.0
    for p in pos:
        u += np.sum(p > neg) + 0.5 * np.sum(p == neg)
    return u / (n_pos * n_neg)


# ═══════════════════════════════════════════════════════════════════════════════
# PDUFA FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

class PDUFAFeatureEngine:
    """Builds feature/target matrices from ODIN_MODEL_READY CSVs."""

    # Canonical PDUFA weight parameter names (matches v10.66+ JSON structure)
    PARAM_NAMES = [
        'base_logit', 'snda_base_penalty', 'snda_pediatric_base_penalty',
        'prior_crl_penalty', 'inexperienced_sponsor_penalty',
        'manufacturing_risk_penalty', 'form_483_penalty',
        'ema_cmc_flag_penalty', 'cmc_extension_penalty',
        'adcom_mid_penalty', 'adcom_low_penalty',
        's22_pediatric_pk_penalty', 'btd_weight', 'orphan_weight',
        'priority_review_weight', 'fast_track_weight',
        'accelerated_approval_weight', 'class1_resubmission_boost',
        'experienced_sponsor_boost', 'adcom_high_boost',
        'ta_adjustment_weight', 's23_insider_weight', 's6_hiring_weight',
        'social_weight', 'odin_weight', 'hint_weight',
        'hint_crl_rate_penalty', 'ta_high_risk_penalty',
        'ta_mod_risk_penalty', 'ta_low_risk_boost',
        'indication_pain_penalty', 'indication_onc_boost',
        'novice_sponsor_high_risk_ta_penalty', 'gene_therapy_penalty',
        'single_arm_study_penalty', 'surrogate_endpoint_penalty',
        'prior_crl_count_penalty', 'safety_severity_penalty',
        'ppm_penalty', 'eu_approved_boost', 'eu_approved_2026_penalty',
        'psychedelics_penalty', 'hoeg_era_constant',
        'accel_approval_2025plus_penalty',
        'experienced_sponsor_2026_reduction',
    ]

    # High-risk TAs for the model
    HIGH_RISK_TA = {'CNS', 'PSYCHIATRY', 'PAIN', 'NEUROLOGY'}
    MOD_RISK_TA = {'CARDIOVASCULAR', 'METABOLIC', 'RESPIRATORY'}
    LOW_RISK_TA = {'ONCOLOGY', 'HEMATOLOGY', 'RARE_DISEASE', 'IMMUNOLOGY'}

    @staticmethod
    def build_features(row: dict) -> np.ndarray:
        """Build PDUFA feature vector from a single CSV row.
        Returns (D,) vector of feature contributions (pre-weight-multiply)."""

        def b(key):
            v = row.get(key, '')
            if isinstance(v, bool): return v
            return str(v).strip().lower() in ('true', '1', 'yes')

        def f(key, default=0.0):
            v = row.get(key, default)
            try: return float(v) if v != '' else default
            except: return default

        app_type = str(row.get('application_type', '')).upper()
        is_snda = 'SNDA' in app_type or 'SUPPLEMENT' in app_type
        is_ped = 'PED' in str(row.get('indication', '')).upper()
        prior_crl = b('prior_crl')
        sponsor_approvals = f('sponsor_prior_approvals', 0)
        is_inexperienced = sponsor_approvals < 3
        is_experienced = sponsor_approvals >= 5
        mfg_risk = b('manufacturing_risk')
        form_483 = b('form_483_issues')
        ema_cmc = b('ema_cmc_flag')
        cmc_ext = b('cmc_extension_flag')

        had_adcom = b('had_adcom')
        adcom_pct = f('adcom_vote_pct', 0)
        adcom_high = had_adcom and adcom_pct >= 70
        adcom_mid = had_adcom and 50 <= adcom_pct < 70
        adcom_low = had_adcom and adcom_pct < 50

        s22_missing = b('s22_ped_pk_missing')
        btd = b('btd')
        orphan = b('orphan')
        priority_review = b('priority_review')
        fast_track = b('fast_track')
        accel = str(row.get('accelerated_approval', '')).strip().lower()
        is_accel = accel in ('true', '1', 'yes', 'accelerated')
        resub = f('resubmission_class', 0)
        is_class1_resub = resub == 1

        ta = str(row.get('therapeutic_area', '')).upper()
        ta_score = f('ta_base_score', 0)
        hist_crl = f('historical_crl_rate', 0)
        s23 = f('s23_signal_strength', 0)
        s6 = f('s6_signal_strength', 0)
        social = f('social_sentiment_score', 0)

        indication = str(row.get('indication', '')).upper()
        is_pain = 'PAIN' in indication
        is_onc = any(k in indication for k in ['CANCER', 'TUMOR', 'ONCOL', 'LYMPHOMA', 'LEUKEMIA', 'MELANOMA', 'CARCINOMA'])

        is_gene_therapy = any(k in indication.lower() for k in ['gene therapy', 'gene transfer', 'aav', 'car-t'])
        is_single_arm = 'SINGLE' in str(row.get('asset', '')).upper() or 'SINGLE ARM' in indication

        is_surrogate = False  # Would need trial data
        prior_crl_count = 1 if prior_crl else 0
        safety_severity = 0  # Would need safety data
        is_ppm = False  # Would need prior pivotal miss data

        # Check for EU approval
        eu_approved = False  # Would need external data

        # Temporal features
        cat_date = str(row.get('catalyst_date', '2025-01-01'))[:10]
        try:
            dt = datetime.strptime(cat_date, '%Y-%m-%d')
        except:
            dt = datetime(2025, 1, 1)
        is_hoeg = dt >= datetime(2025, 1, 1)
        is_2026 = dt.year >= 2026
        is_psychedelic = any(k in indication.lower() for k in ['psilocybin', 'mdma', 'psychedelic', 'ketamine'])

        # Build the feature vector matching PARAM_NAMES
        # Each entry is the feature VALUE that gets multiplied by the weight
        features = np.array([
            1.0,                           # base_logit (always 1)
            float(is_snda and not is_ped), # snda_base_penalty
            float(is_snda and is_ped),     # snda_pediatric_base_penalty
            float(prior_crl),              # prior_crl_penalty
            float(is_inexperienced),       # inexperienced_sponsor_penalty
            float(mfg_risk),               # manufacturing_risk_penalty
            float(form_483),               # form_483_penalty
            float(ema_cmc),                # ema_cmc_flag_penalty
            float(cmc_ext),                # cmc_extension_penalty
            float(adcom_mid),              # adcom_mid_penalty
            float(adcom_low),              # adcom_low_penalty
            float(s22_missing),            # s22_pediatric_pk_penalty
            float(btd),                    # btd_weight
            float(orphan),                 # orphan_weight
            float(priority_review),        # priority_review_weight
            float(fast_track),             # fast_track_weight
            float(is_accel),               # accelerated_approval_weight
            float(is_class1_resub),        # class1_resubmission_boost
            float(is_experienced),         # experienced_sponsor_boost
            float(adcom_high),             # adcom_high_boost
            ta_score,                      # ta_adjustment_weight
            s23,                           # s23_insider_weight
            s6,                            # s6_hiring_weight
            social,                        # social_weight
            0.0,                           # odin_weight (ML score - computed externally)
            hist_crl,                      # hint_weight
            hist_crl,                      # hint_crl_rate_penalty
            float(ta in ' '.join(PDUFAFeatureEngine.HIGH_RISK_TA)),  # ta_high_risk_penalty
            float(ta in ' '.join(PDUFAFeatureEngine.MOD_RISK_TA)),   # ta_mod_risk_penalty
            float(ta in ' '.join(PDUFAFeatureEngine.LOW_RISK_TA)),   # ta_low_risk_boost
            float(is_pain),                # indication_pain_penalty
            float(is_onc),                 # indication_onc_boost
            float(is_inexperienced and ta in ' '.join(PDUFAFeatureEngine.HIGH_RISK_TA)),
            float(is_gene_therapy),        # gene_therapy_penalty
            float(is_single_arm),          # single_arm_study_penalty
            float(is_surrogate),           # surrogate_endpoint_penalty
            float(prior_crl_count),        # prior_crl_count_penalty
            float(safety_severity),        # safety_severity_penalty
            float(is_ppm),                 # ppm_penalty
            float(eu_approved),            # eu_approved_boost
            float(eu_approved and is_2026), # eu_approved_2026_penalty
            float(is_psychedelic),          # psychedelics_penalty
            float(is_hoeg),                # hoeg_era_constant
            float(is_accel and is_hoeg),   # accel_approval_2025plus_penalty
            float(is_experienced and is_2026),  # experienced_sponsor_2026_reduction
        ])
        return features


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE/READOUT FEATURE ENGINEERING (from Gungnir)
# ═══════════════════════════════════════════════════════════════════════════════

class PhaseFeatureEngine:
    """Extract features from historical readout text for Phase model training."""

    import re as _re

    @staticmethod
    def _has(text, kw_list):
        return any(k in text for k in kw_list)

    @staticmethod
    def _rx(text, pattern):
        import re
        return bool(re.search(pattern, text))

    @staticmethod
    def extract(row: dict, feature_names: List[str]) -> np.ndarray:
        """Extract features for Phase model from a readout CSV row."""
        cat = str(row.get('Catalyst', '')).lower()
        stg = str(row.get('Stage', '')).lower()
        ind = str(row.get('Indication', '')).lower()
        combined = f"{cat} {ind}"
        date_str = str(row.get('date', row.get('Catalyst Date', '2025-01-01')))[:10]

        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            dt = datetime(2025, 1, 1)

        rx = PhaseFeatureEngine._rx
        has = PhaseFeatureEngine._has

        f = {}
        # Phase indicators
        is_p3 = rx(f"{cat} {stg}", r'phase\s*3|phase\s*iii')
        is_p2 = rx(f"{cat} {stg}", r'phase\s*2|phase\s*ii')
        is_p1 = rx(f"{cat} {stg}", r'phase\s*1(?!\s*[/23])|phase\s*i(?!\s*[iv23])')
        is_p12 = rx(f"{cat} {stg}", r'phase\s*1[/\\]2|phase\s*i[/\\]ii')
        is_p23 = rx(f"{cat} {stg}", r'phase\s*2[/\\]3|phase\s*ii[/\\]iii')

        # Trial design
        is_rct = rx(cat, r'randomized|rct|controlled|double-blind|placebo')
        is_blinded = rx(cat, r'blind|double-blind|triple-blind')
        is_open = rx(cat, r'open-label|open label')
        is_single_arm = rx(cat, r'single.?arm|non-randomized|uncontrolled')
        is_multi_arm = rx(cat, r'multi.?arm|three.?arm|four.?arm|2:1|3:1')

        # Therapeutic area
        is_onc = rx(combined, r'oncology|cancer|tumor|malignancy|carcinoma|lymphoma|leukemia|melanoma|sarcoma')
        is_cns = rx(combined, r'\bcns\b|alzheimer|parkinson|schizophrenia|depression|bipolar|epilepsy|neurol')
        is_rare = rx(combined, r'rare\s+disease|orphan|ultra-rare|genetic|inherited|lysosomal')
        is_immuno = rx(combined, r'autoimmune|rheumatoid|lupus|psoriasis|atopic|crohn|colitis|inflammatory')
        is_cardio = rx(combined, r'cardiovascular|heart\s+failure|hypertension|atherosclerosis|cardiac')
        is_infect = rx(combined, r'infectious|hiv|hepatitis|bacterial|viral|antifungal|antibiotic')
        is_metabol = rx(combined, r'metabolic|diabetes|obesity|lipid|cholesterol|nash|nafld')
        is_hemat = rx(combined, r'hematology|anemia|hemophilia|sickle\s+cell|thalassemia|myeloma')

        # Outcome features (extracted from text at scoring time - NOT cheating)
        primary_met = rx(cat, r'met\s+(primary|main)\s+endpoint|achieved\s+primary|primary\s+endpoint\s+(met|achieved|reached|positive)')
        p_value = rx(cat, r'statistically\s+significant|p\s*[<≤]\s*0\.0[0-5]|p\s*[<≤]\s*0\.001')
        failure = rx(cat, r'failed|did\s+not\s+meet|discontinued|halted|stopped|terminated|futility|negative|missed|not\s+met')
        sentiment = rx(cat, r'robust|meaningful|clinically\s+meaningful|impressive|remarkable|transformative')
        hard_endpt = rx(cat, r'pfs|progression-free|overall\s+survival|os|mace|mortality|death')
        competitive = rx(cat, r'versus|vs\.|compared\s+to|soc|standard\s+of\s+care|head-to-head')

        # Build feature dict matching possible Phase model feature names
        f['blind_x_phase3'] = float(is_blinded and is_p3)
        f['float_ratio'] = 0.0  # Needs market data - frozen
        f['has_pubmed'] = 0.0  # Needs external data - frozen
        f['is_blinded'] = float(is_blinded)
        f['is_large_mega'] = 0.0  # Needs market data - frozen
        f['is_micro'] = 0.0  # Needs market data - frozen
        f['is_open_label'] = float(is_open)
        f['is_randomized'] = float(is_rct)
        f['is_small'] = 0.0  # Needs market data - frozen
        f['log_employees'] = 0.0  # Needs external data - frozen
        f['log_enrollment'] = 0.0  # Needs trial data - frozen
        f['log_mcap'] = 0.0  # Needs market data - frozen
        f['log_pubmed'] = 0.0  # Needs external data - frozen
        f['multi_arm'] = float(is_multi_arm)
        f['phase2_x_micro'] = 0.0  # Needs market data - frozen
        f['phase2_x_oncology'] = float(is_p2 and is_onc)
        f['phase3_x_cns'] = float(is_p3 and is_cns)
        f['phase3_x_large'] = 0.0  # Needs market data - frozen
        f['phase3_x_oncology'] = float(is_p3 and is_onc)
        f['phase3_x_rare'] = float(is_p3 and is_rare)
        f['phase3_x_small'] = 0.0  # Needs market data - frozen
        f['phase_PHASE1'] = float(is_p1)
        f['phase_PHASE1_2'] = float(is_p12)
        f['phase_PHASE2'] = float(is_p2)
        f['phase_PHASE2_3'] = float(is_p23)
        f['phase_PHASE3'] = float(is_p3)
        f['rct_x_phase3'] = float(is_rct and is_p3)
        f['single_arm'] = float(is_single_arm)
        f['single_arm_x_oncology'] = float(is_single_arm and is_onc)
        f['ta_CARDIOVASCULAR'] = float(is_cardio)
        f['ta_CNS'] = float(is_cns)
        f['ta_HEMATOLOGY'] = float(is_hemat)
        f['ta_IMMUNOLOGY'] = float(is_immuno)
        f['ta_INFECTIOUS'] = float(is_infect)
        f['ta_METABOLIC'] = float(is_metabol)
        f['ta_ONCOLOGY'] = float(is_onc)
        f['ta_RARE'] = float(is_rare)

        # Extended features (v2.2+)
        f['p_value_significant'] = float(p_value)
        f['primary_endpoint_met'] = float(primary_met)
        f['cash_runway_quarters'] = 0.0  # Frozen
        f['short_interest_pct'] = 0.0  # Frozen
        f['is_micro_cap'] = 0.0  # Frozen
        f['run_up_30d'] = 0.0  # Frozen
        f['is_lead_asset'] = 0.0  # Frozen
        f['is_hard_endpoint'] = float(hard_endpt)
        f['relative_efficacy'] = 0.0  # Frozen (complex computation)
        f['failure_signal'] = float(failure)
        f['sentiment_score'] = float(sentiment)
        f['is_orphan_designated'] = float(rx(combined, r'orphan|rare\s+disease'))
        f['regulatory_alignment'] = 0.0  # Frozen
        f['alpha_status'] = 0.0  # Frozen
        f['is_competitive_space'] = float(competitive)

        # Return in requested feature order
        return np.array([f.get(name, 0.0) for name in feature_names])


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_pdufa_data(csv_path: str, weights_json: dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load ODIN_MODEL_READY CSV → (X, y, dates).

    For PDUFA models, X is the feature contribution matrix and
    the model output is logit = X @ weights."""
    import csv as csv_mod

    with open(csv_path, encoding='utf-8-sig') as f:
        rows = list(csv_mod.DictReader(f))

    param_names = PDUFAFeatureEngine.PARAM_NAMES
    X_list, y_list, dates = [], [], []

    for row in rows:
        outcome = str(row.get('outcome', '')).strip().lower()
        if outcome not in ('approved', 'approval', 'crl', 'positive', 'negative'):
            continue
        y_val = 1.0 if outcome in ('approved', 'approval', 'positive') else 0.0

        features = PDUFAFeatureEngine.build_features(row)
        X_list.append(features)
        y_list.append(y_val)

        date_str = str(row.get('catalyst_date', row.get('date', '2020-01-01')))[:10]
        dates.append(date_str)

    return np.array(X_list), np.array(y_list), np.array(dates)


def load_phase_data(csv_path: str, weights_json: dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load historical_readouts CSV → (X, y, dates).

    For Phase models, X is the raw feature matrix that gets standardized."""
    import csv as csv_mod

    feature_names = weights_json.get('feature_names', [])
    scaler_mean = np.array(weights_json['success_model']['scaler_mean'])
    scaler_scale = np.array(weights_json['success_model']['scaler_scale'])

    with open(csv_path, encoding='utf-8-sig') as f:
        rows = list(csv_mod.DictReader(f))

    X_list, y_list, dates = [], [], []

    for row in rows:
        outcome = str(row.get('outcome', '')).strip().lower()
        if outcome not in ('positive', 'negative'):
            continue
        y_val = 1.0 if outcome == 'positive' else 0.0

        features = PhaseFeatureEngine.extract(row, feature_names)
        # Standardize
        features_scaled = (features - scaler_mean) / np.where(scaler_scale > 0, scaler_scale, 1.0)
        X_list.append(features_scaled)
        y_list.append(y_val)

        date_str = str(row.get('date', row.get('Catalyst Date', '2020-01-01')))[:10]
        dates.append(date_str)

    return np.array(X_list), np.array(y_list), np.array(dates)


def time_split(X, y, dates, val_frac=0.2):
    """Time-based train/val split."""
    sorted_idx = np.argsort(dates)
    X, y, dates = X[sorted_idx], y[sorted_idx], dates[sorted_idx]

    split_point = int(len(X) * (1 - val_frac))
    X_train, y_train = X[:split_point], y[:split_point]
    X_val, y_val = X[split_point:], y[split_point:]
    dates_train, dates_val = dates[:split_point], dates[split_point:]

    return X_train, y_train, dates_train, X_val, y_val, dates_val


def walk_forward_auc(X, y, dates, w, b, n_folds=3, model_type='pdufa'):
    """Walk-forward cross-validation AUC."""
    sorted_idx = np.argsort(dates)
    X, y, dates = X[sorted_idx], y[sorted_idx], dates[sorted_idx]

    fold_size = len(X) // (n_folds + 1)
    aucs = []

    for fold in range(n_folds):
        train_end = (fold + 1) * fold_size
        val_start = train_end
        val_end = min(val_start + fold_size, len(X))
        if val_end <= val_start:
            continue

        X_val = X[val_start:val_end]
        y_val = y[val_start:val_end]

        if model_type == 'pdufa':
            # PDUFA: logit = X @ w (w includes bias via base_logit)
            logits = X_val @ w
            preds = sigmoid(logits)
        else:
            # Phase: logit = X @ w + b
            logits = X_val @ w + b
            preds = sigmoid(logits)

        auc = auc_score(preds, y_val)
        aucs.append(auc)

    return aucs


# ═══════════════════════════════════════════════════════════════════════════════
# LR SCHEDULES
# ═══════════════════════════════════════════════════════════════════════════════

def cosine_lr(step, cycle_steps, lr_max, lr_min=1e-7):
    """Cosine annealing within a cycle."""
    t = step % cycle_steps
    return lr_min + 0.5 * (lr_max - lr_min) * (1 + math.cos(math.pi * t / cycle_steps))


# ═══════════════════════════════════════════════════════════════════════════════
# PERPETUAL HONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PerpetualHoningEngine:

    def __init__(self, data_file: str, weights_json_path: str,
                 output_json: str = "odin_honed.json",
                 state_file: str = "odin_honing_state.json",
                 history_file: str = "odin_honing_history.csv",
                 config: Optional[dict] = None):
        self.data_file = data_file
        self.weights_json_path = weights_json_path
        self.output_json = output_json
        self.state_file = state_file
        self.history_file = history_file
        self.config = {**DEFAULT_CONFIG, **(config or {})}

    def detect_model_type(self, weights: dict) -> str:
        """Detect whether weights are PDUFA (logit-space) or Phase (LR+scaler)."""
        if 'success_model' in weights and 'scaler_mean' in weights.get('success_model', {}):
            return 'phase'
        elif 'base_logit' in weights:
            return 'pdufa'
        else:
            raise ValueError("Cannot detect model type from weights JSON")

    def load_weights(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def weights_to_vector(self, weights: dict, model_type: str) -> Tuple[np.ndarray, float, List[str]]:
        """Convert weights JSON → (w_vector, bias, param_names)."""
        if model_type == 'pdufa':
            param_names = PDUFAFeatureEngine.PARAM_NAMES
            # Filter to only params that exist in weights
            param_names = [p for p in param_names if p in weights]
            w = np.array([weights[p] for p in param_names])
            return w, 0.0, param_names  # PDUFA has no separate bias (base_logit is in w)
        else:
            coefs = weights['success_model']['coefficients']
            param_names = list(coefs.keys())
            w = np.array([coefs[n] for n in param_names])
            b = weights['success_model']['intercept']
            return w, b, param_names

    def vector_to_weights(self, w: np.ndarray, b: float, param_names: List[str],
                          model_type: str, original_weights: dict) -> dict:
        """Convert optimized vector back to weights JSON."""
        result = copy.deepcopy(original_weights)
        if model_type == 'pdufa':
            for i, name in enumerate(param_names):
                result[name] = float(w[i])
        else:
            for i, name in enumerate(param_names):
                result['success_model']['coefficients'][name] = float(w[i])
            result['success_model']['intercept'] = float(b)
        return result

    def build_trainable_mask(self, param_names: List[str], model_type: str) -> np.ndarray:
        """Build mask of which weights are trainable."""
        # For PDUFA: all weights trainable
        if model_type == 'pdufa':
            return np.ones(len(param_names))

        # For Phase: freeze features requiring external data
        FROZEN_FEATURES = {
            'float_ratio', 'is_large_mega', 'is_micro', 'is_small',
            'log_employees', 'log_enrollment', 'log_mcap', 'log_pubmed',
            'has_pubmed', 'phase2_x_micro', 'phase3_x_large', 'phase3_x_small',
            'cash_runway_quarters', 'short_interest_pct', 'is_micro_cap',
            'run_up_30d', 'is_lead_asset', 'relative_efficacy',
            'regulatory_alignment', 'alpha_status',
        }
        mask = np.array([0.0 if name in FROZEN_FEATURES else 1.0
                         for name in param_names])
        return mask

    def log_progress(self, step, cycle, phase, lr, train_brier, train_ll,
                     train_auc, val_brier, val_ll, val_auc, best_brier, improved):
        """Append to CSV history."""
        exists = os.path.isfile(self.history_file)
        with open(self.history_file, 'a', newline='') as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(['Timestamp', 'Step', 'Cycle', 'Phase', 'LR',
                            'Train_Brier', 'Train_LogLoss', 'Train_AUC',
                            'Val_Brier', 'Val_LogLoss', 'Val_AUC',
                            'Best_Val_Brier', 'Improved'])
            w.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                step, cycle, phase, f"{lr:.8f}",
                f"{train_brier:.8f}", f"{train_ll:.8f}", f"{train_auc:.4f}",
                f"{val_brier:.8f}", f"{val_ll:.8f}", f"{val_auc:.4f}",
                f"{best_brier:.8f}", "YES" if improved else "no"
            ])

    @staticmethod
    def send_alert(title, message):
        try:
            if sys.platform == "darwin":
                import subprocess
                subprocess.Popen(['osascript', '-e',
                    f'display notification "{message}" with title "{title}"'])
            elif sys.platform == "win32":
                import subprocess
                subprocess.Popen(
                    f'powershell -Command "Add-Type -AssemblyName System.Windows.Forms;'
                    f'[System.Windows.Forms.MessageBox]::Show(\'{message}\', \'{title}\')"',
                    shell=True)
            else:
                import subprocess
                subprocess.Popen(['notify-send', title, message])
        except:
            pass
        print(f"\n🔔 {title}: {message}")

    def run_single_pass(self, X_train, y_train, X_val, y_val,
                        anchor_w, anchor_b, param_names, model_type,
                        config, resume_state=None):
        """Run a single optimization pass through all 3 phases.

        Returns: (best_w, best_b, best_brier, ensemble_w, ensemble_b, opt_state)
        """
        n_params = len(anchor_w)
        sign_ref = np.sign(anchor_w) if config.get('sign_constrained') else None
        mask = self.build_trainable_mask(param_names, model_type)

        opt = AdamOptimizer(n_params, anchor_w, anchor_b, config,
                           trainable_mask=mask, sign_ref=sign_ref)

        if resume_state:
            opt.load_state(resume_state)
            print(f"  📂 Resumed from step {opt.step}, best Brier: {opt.best_val_brier:.6f}")

        # Define the 3 phases
        phases = [
            ("EXPLORE",  config['phase1_lr'], config['phase1_steps_per_cycle'], config['phase1_cycles']),
            ("REFINE",   config['phase2_lr'], config['phase2_steps_per_cycle'], config['phase2_cycles']),
            ("POLISH",   config['phase3_lr'], config['phase3_max_steps'],       1),
        ]

        global_start_step = opt.step
        total_trained = 0

        for phase_name, lr_max, steps_per_cycle, n_cycles in phases:
            phase_improved = False

            for cycle in range(n_cycles):
                cycle_start_step = opt.step
                patience_at_start = opt.steps_since_improvement

                for local_step in range(steps_per_cycle):
                    # Cosine LR within cycle
                    lr = cosine_lr(local_step, steps_per_cycle, lr_max, lr_max * 0.01)

                    # Forward + backward
                    if model_type == 'pdufa':
                        loss, grad_w, grad_b, preds = logistic_loss_and_grad(
                            X_train, y_train, opt.w, 0.0)
                        grad_b = 0.0  # No separate bias for PDUFA
                    else:
                        loss, grad_w, grad_b, preds = logistic_loss_and_grad(
                            X_train, y_train, opt.w, opt.b)

                    opt.update(grad_w, grad_b, lr)
                    total_trained += 1

                    # Evaluate
                    if opt.step % config['eval_every'] == 0:
                        if model_type == 'pdufa':
                            _, _, _, train_preds = logistic_loss_and_grad(X_train, y_train, opt.w, 0.0)
                            val_loss, _, _, val_preds = logistic_loss_and_grad(X_val, y_val, opt.w, 0.0)
                        else:
                            _, _, _, train_preds = logistic_loss_and_grad(X_train, y_train, opt.w, opt.b)
                            val_loss, _, _, val_preds = logistic_loss_and_grad(X_val, y_val, opt.w, opt.b)

                        train_brier = brier_score(train_preds, y_train)
                        val_brier = brier_score(val_preds, y_val)
                        train_auc = auc_score(train_preds, y_train)
                        val_auc = auc_score(val_preds, y_val)
                        train_ll = loss
                        val_ll = val_loss

                        improved = opt.record_eval(val_brier, val_loss)
                        if improved:
                            phase_improved = True

                        # Snapshot
                        if opt.step % config['snapshot_every'] == 0:
                            opt.take_snapshot(val_brier)

                        # Log
                        self.log_progress(opt.step, cycle, phase_name, lr,
                                         train_brier, train_ll, train_auc,
                                         val_brier, val_ll, val_auc,
                                         opt.best_val_brier, improved)

                        # Status line
                        marker = "✅" if improved else "  "
                        print(f"\r  [{phase_name}] Step {opt.step:>6d} | "
                              f"LR {lr:.2e} | "
                              f"Train: B={train_brier:.6f} AUC={train_auc:.4f} | "
                              f"Val: B={val_brier:.6f} AUC={val_auc:.4f} | "
                              f"Best: {opt.best_val_brier:.6f} @{opt.best_step} {marker}",
                              end="", flush=True)

                    # Check patience within cycle
                    if opt.patience_exceeded:
                        break

                    # Hard ceiling
                    if total_trained >= config['max_total_steps']:
                        break

                # End of cycle — check if we should continue this phase
                if opt.patience_exceeded:
                    print(f"\n  ⏸  Patience exceeded in {phase_name} cycle {cycle+1}/{n_cycles}")
                    opt.steps_since_improvement = 0  # Reset for next phase
                    break

                if total_trained >= config['max_total_steps']:
                    break

            if not phase_improved:
                print(f"\n  ⏭  Phase {phase_name} produced no improvement, skipping remaining cycles")
            else:
                print(f"\n  ✨ Phase {phase_name} improved Brier to {opt.best_val_brier:.6f}")

            if total_trained >= config['max_total_steps']:
                break

        # Compute ensemble
        ens_w, ens_b = opt.get_ensemble()

        return opt.best_w, opt.best_b, opt.best_val_brier, ens_w, ens_b, opt.get_state()

    def run(self, resume=True):
        """Main entry point: perpetual self-improving loop."""
        print("\033[94m" + "=" * 70 + "\033[0m")
        print("🚀 \033[1mODIN PERPETUAL HONING ENGINE v4.0\033[0m")
        print("\033[94m" + "=" * 70 + "\033[0m")

        # Load weights
        weights = self.load_weights(self.weights_json_path)
        model_type = self.detect_model_type(weights)
        print(f"📋 Model type: {model_type.upper()}")
        print(f"📋 Data: {self.data_file}")

        w, b, param_names = self.weights_to_vector(weights, model_type)
        print(f"📋 Parameters: {len(param_names)} ({sum(self.build_trainable_mask(param_names, model_type)>0):.0f} trainable)")

        # Load data
        print("📊 Loading data...")
        if model_type == 'pdufa':
            X, y, dates = load_pdufa_data(self.data_file, weights)
        else:
            X, y, dates = load_phase_data(self.data_file, weights)

        print(f"   {len(X)} samples, {y.mean():.1%} positive, "
              f"dates {sorted(dates)[0]} → {sorted(dates)[-1]}")

        # Time split
        X_train, y_train, d_train, X_val, y_val, d_val = time_split(
            X, y, dates, self.config['val_frac'])
        print(f"   Train: {len(X_train)} ({y_train.mean():.1%} pos, {d_train[0]}→{d_train[-1]})")
        print(f"   Val:   {len(X_val)} ({y_val.mean():.1%} pos, {d_val[0]}→{d_val[-1]})")

        # Baseline evaluation
        if model_type == 'pdufa':
            _, _, _, base_preds = logistic_loss_and_grad(X_val, y_val, w, 0.0)
        else:
            _, _, _, base_preds = logistic_loss_and_grad(X_val, y_val, w, b)
        base_brier = brier_score(base_preds, y_val)
        base_auc = auc_score(base_preds, y_val)
        print(f"\n📐 Baseline: Val Brier={base_brier:.6f}, Val AUC={base_auc:.4f}")

        # Check for resume state
        resume_state = None
        if resume and os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    resume_state = json.load(f)
                print(f"📂 Found resume state (step {resume_state.get('step', '?')})")
            except:
                pass

        # ═══════════════════════════════════════════════════════════
        # SELF-IMPROVEMENT LOOP
        # ═══════════════════════════════════════════════════════════
        best_overall_brier = base_brier
        best_overall_w = w.copy()
        best_overall_b = float(b)
        current_anchor_w = w.copy()
        current_anchor_b = float(b)

        for round_num in range(1, self.config['self_improve_rounds'] + 1):
            print(f"\n{'='*70}")
            print(f"🔄 SELF-IMPROVEMENT ROUND {round_num}/{self.config['self_improve_rounds']}")
            print(f"   Anchor Brier: {best_overall_brier:.6f}")
            print(f"{'='*70}")

            # Scale down LR each round (annealing across rounds)
            round_config = dict(self.config)
            round_decay = 0.7 ** (round_num - 1)  # Each round uses 70% of previous LR
            round_config['phase1_lr'] *= round_decay
            round_config['phase2_lr'] *= round_decay
            round_config['phase3_lr'] *= round_decay

            # Only resume state on first round
            state_to_resume = resume_state if round_num == 1 else None

            # Run optimization pass
            best_w, best_b, best_brier, ens_w, ens_b, opt_state = \
                self.run_single_pass(
                    X_train, y_train, X_val, y_val,
                    current_anchor_w, current_anchor_b,
                    param_names, model_type,
                    round_config, state_to_resume)

            # Also evaluate ensemble
            if model_type == 'pdufa':
                _, _, _, ens_preds = logistic_loss_and_grad(X_val, y_val, ens_w, 0.0)
            else:
                _, _, _, ens_preds = logistic_loss_and_grad(X_val, y_val, ens_w, ens_b)
            ens_brier = brier_score(ens_preds, y_val)

            # Pick winner of this round
            if ens_brier < best_brier:
                round_w, round_b, round_brier = ens_w, ens_b, ens_brier
                round_type = "ENSEMBLE"
            else:
                round_w, round_b, round_brier = best_w, best_b, best_brier
                round_type = "BEST_SINGLE"

            improvement = best_overall_brier - round_brier
            print(f"\n  Round {round_num} result: Brier={round_brier:.6f} ({round_type})")
            print(f"  Improvement: {improvement:+.8f}")

            if improvement > self.config['self_improve_min_gain']:
                best_overall_brier = round_brier
                best_overall_w = round_w.copy()
                best_overall_b = float(round_b)
                current_anchor_w = round_w.copy()
                current_anchor_b = float(round_b)
                print(f"  ✅ New best! Updating anchor for next round.")

                # Save intermediate best
                best_weights = self.vector_to_weights(
                    best_overall_w, best_overall_b, param_names, model_type, weights)
                with open(self.output_json, 'w') as f:
                    json.dump(best_weights, f, indent=2)

                # Save state
                with open(self.state_file, 'w') as f:
                    json.dump(opt_state, f)
            else:
                print(f"  ⛔ No meaningful improvement. Convergence reached.")
                break

        # ═══════════════════════════════════════════════════════════
        # FINAL EVALUATION
        # ═══════════════════════════════════════════════════════════
        print(f"\n{'='*70}")
        print("📊 FINAL EVALUATION")
        print(f"{'='*70}")

        # Walk-forward AUC
        wf_aucs = walk_forward_auc(X, y, dates, best_overall_w, best_overall_b,
                                   n_folds=3, model_type=model_type)
        wf_mean = np.mean(wf_aucs) if wf_aucs else 0.0

        # Final val metrics
        if model_type == 'pdufa':
            _, _, _, final_preds = logistic_loss_and_grad(X_val, y_val, best_overall_w, 0.0)
        else:
            _, _, _, final_preds = logistic_loss_and_grad(X_val, y_val, best_overall_w, best_overall_b)

        final_brier = brier_score(final_preds, y_val)
        final_auc = auc_score(final_preds, y_val)

        print(f"  Baseline:    Brier={base_brier:.6f}  AUC={base_auc:.4f}")
        print(f"  Final:       Brier={final_brier:.6f}  AUC={final_auc:.4f}")
        print(f"  Improvement: Brier {base_brier - final_brier:+.6f}")
        print(f"  WF AUCs:     {[f'{a:.4f}' for a in wf_aucs]}")
        print(f"  WF Mean AUC: {wf_mean:.4f}")

        # Save final model with metadata
        final_weights = self.vector_to_weights(
            best_overall_w, best_overall_b, param_names, model_type, weights)

        # Add honing metadata
        meta_key = 'honing_metadata'
        final_weights[meta_key] = {
            'engine_version': __version__,
            'timestamp': datetime.now().isoformat(),
            'anchor_file': self.weights_json_path,
            'data_file': self.data_file,
            'model_type': model_type,
            'baseline_val_brier': float(base_brier),
            'baseline_val_auc': float(base_auc),
            'final_val_brier': float(final_brier),
            'final_val_auc': float(final_auc),
            'brier_improvement': float(base_brier - final_brier),
            'walk_forward_aucs': [float(a) for a in wf_aucs],
            'walk_forward_mean_auc': float(wf_mean),
            'rounds_completed': round_num,
            'config': {k: v for k, v in self.config.items()
                       if not callable(v)},
        }

        with open(self.output_json, 'w') as f:
            json.dump(final_weights, f, indent=2)
        print(f"\n💾 Final model → {self.output_json}")

        # Save ensemble variant
        ens_output = self.output_json.replace('.json', '_ensemble.json')
        ens_weights = self.vector_to_weights(
            ens_w, ens_b, param_names, model_type, weights)
        ens_weights[meta_key] = {**final_weights[meta_key], 'type': 'ensemble_top_k'}
        with open(ens_output, 'w') as f:
            json.dump(ens_weights, f, indent=2)
        print(f"💾 Ensemble   → {ens_output}")

        # Save final state
        with open(self.state_file, 'w') as f:
            json.dump(opt_state, f)
        print(f"💾 State      → {self.state_file}")

        self.send_alert(
            "ODIN Honing Complete",
            f"Brier: {base_brier:.4f} → {final_brier:.4f} | WF AUC: {wf_mean:.4f}")

        return self.output_json


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ODIN Perpetual Honing Engine v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Hone PDUFA model on v1066 dataset
  python odin_perpetual_honing_v4.py \\
    --data ODIN_MODEL_READY_v1066_T1_2015on_2200.csv \\
    --weights odin_pdufa_ensemble_start.json

  # Hone Phase model on historical readouts
  python odin_perpetual_honing_v4.py \\
    --data historical_readouts_2000.csv \\
    --weights odin_phase_v2_2_refined.json

  # Resume interrupted run
  python odin_perpetual_honing_v4.py \\
    --data historical_readouts_2000.csv \\
    --weights odin_phase_v2_2_refined.json \\
    --state odin_honing_state.json

  # Aggressive search with higher LR
  python odin_perpetual_honing_v4.py \\
    --data ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv \\
    --weights odin_v1078_ironclad_best.json \\
    --lr 0.001 --rounds 30
""")
    parser.add_argument("--data", required=True, help="Training CSV")
    parser.add_argument("--weights", required=True, help="Anchor weights JSON")
    parser.add_argument("--output", default="odin_honed.json", help="Output JSON")
    parser.add_argument("--state", default="odin_honing_state.json", help="State file")
    parser.add_argument("--history", default="odin_honing_history.csv", help="History CSV")
    parser.add_argument("--lr", type=float, default=None, help="Override phase1 LR")
    parser.add_argument("--rounds", type=int, default=None, help="Self-improvement rounds")
    parser.add_argument("--steps", type=int, default=None, help="Max total steps")
    parser.add_argument("--anchor-l2", type=float, default=None, help="Anchor L2 strength")
    parser.add_argument("--mag-clamp", type=float, default=None, help="Magnitude clamp ratio")
    parser.add_argument("--fresh", action="store_true", help="Ignore existing state")
    parser.add_argument("--no-sign-constraint", action="store_true", help="Disable sign constraints")

    args = parser.parse_args()
    config = dict(DEFAULT_CONFIG)

    if args.lr:
        config['phase1_lr'] = args.lr
        config['phase2_lr'] = args.lr * 0.2
        config['phase3_lr'] = args.lr * 0.02
    if args.rounds:
        config['self_improve_rounds'] = args.rounds
    if args.steps:
        config['max_total_steps'] = args.steps
    if args.anchor_l2:
        config['anchor_l2'] = args.anchor_l2
        config['anchor_b'] = args.anchor_l2
    if args.mag_clamp:
        config['magnitude_clamp'] = args.mag_clamp
    if args.no_sign_constraint:
        config['sign_constrained'] = False

    engine = PerpetualHoningEngine(
        data_file=args.data,
        weights_json_path=args.weights,
        output_json=args.output,
        state_file=args.state,
        history_file=args.history,
        config=config,
    )

    try:
        winner = engine.run(resume=not args.fresh)
        print(f"\n✅ Done. Best model: {winner}")
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted. State preserved.")
        sys.exit(0)


if __name__ == "__main__":
    main()