#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ODIN GUNGNIR v4.0                                    ║
║                    Readout Scoring Engine                                ║
║                                                                          ║
║  "The spear that never misses"                                           ║
║                                                                          ║
║  Kaizen: K9→K10→K11→K12→K13→K14→K15→K16→K17→K18→K19                    ║
║  Sharpe: 3.99 | T1 Win Rate: 96.9% | T4 Loss Rate: 93.8%              ║
║  Walk-forward validated on 1,732 events (2023-2026)                      ║
╚══════════════════════════════════════════════════════════════════════════╝

USAGE:
    # Command line — interactive scoring
    python gungnir.py

    # Command line — score a specific event
    python gungnir.py --ticker ACME --catalyst "Phase 3 met primary endpoint..."

    # As a module
    from gungnir import GungnirScorer
    scorer = GungnirScorer()                          # logistic-only
    scorer = GungnirScorer("xgb_model_v3.json")       # full ensemble
    result = scorer.score("Phase 3 met primary endpoint of PFS...",
                          ticker="ACME", drug="acmecillin",
                          indication="breast cancer", stage="Phase 3",
                          date="2026-02-16")
    scorer.print_scorecard(result)

ARCHITECTURE:
    Input → 35 NLP features → [Sign-Constrained Logistic + XGBoost] →
    Stacker → ML Score → Gungnir Risk Overlay → Final Score → Tier

REQUIRES: numpy (only hard dependency)
OPTIONAL: xgboost (for full ensemble; falls back to logistic-only)
"""

import numpy as np
import re
import sys
import os
from datetime import datetime

try:
    import xgboost as xgb
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

__version__ = "4.0.0"
__codename__ = "Gungnir"


# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED MODEL WEIGHTS (trained on 2,000 readouts, K15 sign-constrained)
# ═══════════════════════════════════════════════════════════════════════════

_FEATURE_NAMES = [
    "is_hard_endpoint", "phase_PHASE3", "is_competitive_space", "sentiment_score",
    "phase_PHASE2", "primary_endpoint_met", "ta_ONCOLOGY", "rct_x_phase3",
    "has_breakthrough", "has_orphan", "has_priority_review", "has_fast_track",
    "is_gene_therapy", "is_psychedelic", "safety_signal", "ppm_flag",
    "is_single_arm", "has_surrogate", "is_hoeg_era", "accel_approval_2025",
    "single_arm_2025", "failure_signal", "strong_positive", "dose_response",
    "safety_clean", "ta_CNS", "ta_RARE", "ta_PAIN", "ta_IMMUNOLOGY",
    "gene_therapy_x_phase3", "safety_x_hoeg", "ppm_x_hoeg",
    "oncology_x_phase3", "rare_x_positive", "failure_x_phase3",
]

# XGB gets all features except failure_signal (index 21)
_XGB_FEATURES = [f for f in _FEATURE_NAMES if f != "failure_signal"]

# Features whose raw values are NEGATED before logistic scoring
_FLIP_INDICES = [12, 13, 14, 15, 16, 18, 19, 20, 21, 29, 30, 31, 34]

# Logistic regression: intercept + 35 raw coefficients (on sign-flipped features)
_LOGIT_INTERCEPT = 2.6706550270853344
_LOGIT_COEFS = np.array([
    0.28401221675386085,   # is_hard_endpoint
   -0.27742001964156815,   # phase_PHASE3
    0.13990581198256632,   # is_competitive_space
    0.6440484683332778,    # sentiment_score
   -0.1687717370124852,    # phase_PHASE2
    1.1106238836577542,    # primary_endpoint_met
    0.09060296391104013,   # ta_ONCOLOGY
    0.0,                   # rct_x_phase3
    0.0,                   # has_breakthrough
    0.005278119344333123,  # has_orphan
    0.0,                   # has_priority_review
    0.0,                   # has_fast_track
    0.0,                   # is_gene_therapy (flipped)
   -0.037485737666899985,  # is_psychedelic (flipped)
    0.08130147715257206,   # safety_signal (flipped)
    0.33088735537873676,   # ppm_flag (flipped)
    0.0,                   # is_single_arm (flipped)
    0.7319199685165179,    # has_surrogate
    0.08300571640304522,   # is_hoeg_era (flipped)
    0.0,                   # accel_approval_2025 (flipped)
   -0.0054009657898306095, # single_arm_2025 (flipped)
    2.33662799996217,      # failure_signal (flipped)
    0.0,                   # strong_positive
    0.0,                   # dose_response
    0.0,                   # safety_clean
    0.0,                   # ta_CNS
    0.005278119344333123,  # ta_RARE
   -0.07054296051055892,   # ta_PAIN
    0.14708450304950216,   # ta_IMMUNOLOGY
   -0.043778015605151537,  # gene_therapy_x_phase3 (flipped)
   -0.04952285880274948,   # safety_x_hoeg (flipped)
    0.0,                   # ppm_x_hoeg (flipped)
   -0.010359405049272605,  # oncology_x_phase3
    0.0,                   # rare_x_positive
    0.0,                   # failure_x_phase3 (flipped)
])

# StandardScaler params (fitted on sign-flipped training data)
_SCALER_MEAN = np.array([
    0.284, 0.391, 0.144, 0.122, 0.3845, 0.0915, 0.413, 0.0495,
    0.0, 0.001, 0.0, 0.001, -0.026, -0.005, -0.0165, -0.0235,
    -0.0035, 0.183, -0.2935, -0.001, -0.003, -0.2105, 0.162, 0.01,
    0.0345, 0.0545, 0.001, 0.016, 0.054, -0.004, -0.0035, -0.007,
    0.13, 0.0005, -0.0925,
])

_SCALER_SCALE = np.array([
    0.4509368026675065, 0.4879743845736105, 0.35108973211986544,
    0.3272858078193985, 0.4864768750927424, 0.2883188339321583,
    0.49237282622012896, 0.2169095433585144, 1.0, 0.03160696125855835,
    1.0, 0.03160696125855705, 0.1591351626762579, 0.07053367989833026,
    0.1556526581848192, 0.15148514778683433, 0.05905717568594122,
    0.38666652298847703, 0.4553655125281409, 0.03160696125855705,
    0.05469003565550381, 0.4076637707719462, 0.36845081082825554,
    0.09949874371066124, 0.18250958878919224, 0.22700165197637004,
    0.03160696125855835, 0.12547509713086583, 0.22601769842204655,
    0.06311893535223659, 0.06699067099230668, 0.08337265738838204,
    0.33630343441600313, 0.022355088906108683, 0.2897304782034476,
])

# Stacker meta-learner (combines XGB + logistic)
_STACK_INTERCEPT = -3.4446824510912446
_STACK_XGB_COEF = 1.7246781860583205
_STACK_LOGIT_COEF = 5.794570609672386


# ═══════════════════════════════════════════════════════════════════════════
# KEYWORD LISTS
# ═══════════════════════════════════════════════════════════════════════════

_GT_TICKERS = {
    'RCKT','RGNX','SGMO','BLUE','BEAM','CRSP','EDIT','NTLA','VRTX','BMRN',
    'SRPT','QURE','ONCE','AVXL','RARE','MESO','ABEO','AGTC','STOK','PBYI',
}
_GT_KW = [
    'gene therapy','gene transfer','aav','adeno-associated','lentiviral',
    'cell therapy','car-t','car t','crispr','base editing','mrna therapy',
    'gene replacement','gene editing','antisense oligonucleotide',
    'aso therapy','sirna','rnai',
]
_PSYCH_KW = ['mdma','psilocybin','lsd','ketamine','psychedelic',
             'dmt','ayahuasca','ibogaine','mescaline']
_SAF_SEV = [
    'dili','drug-induced liver','hepatotoxicity','liver injury',
    'cardiac death','sudden death','fatal','suicidal',
    'pml','progressive multifocal','stevens-johnson',
    'anaphylaxis','cytokine release syndrome','black box',
]
_SAF_MOD = [
    'cardiac','arrhythmia','qt prolongation','liver enzyme',
    'elevated alt','elevated ast','neutropenia','thrombocytopenia',
    'rems','risk evaluation','boxed warning',
]
_PPM_KW = [
    'failed primary','did not meet primary','missed primary',
    'primary endpoint not met','primary endpoint was not',
    'fda wants more data','complete response letter',
    'additional data required','fda requested additional',
    'phase 3 required','confirmatory trial',
]
_SA_KW = ['single-arm','single arm','non-randomized','uncontrolled',
          'open-label single','no comparator']


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def _has(text, kw_list):
    return any(k in text for k in kw_list)

def _rx(text, pattern):
    return bool(re.search(pattern, text))

def extract_features(catalyst, ticker="", drug="", indication="", stage="", date="2026-01-01"):
    """Extract 35 features from readout text + metadata. Returns (vector, dict)."""
    cat = catalyst.lower()
    tk = ticker.upper()
    stg = stage.lower()
    combined = f"{cat} {drug.lower()} {indication.lower()}"

    try:
        dt = datetime.strptime(str(date)[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        dt = datetime(2026, 1, 1)

    f = {}
    # A: Core signals
    f['is_hard_endpoint']    = float(_rx(cat, r'pfs|progression-free survival|os|overall survival|mace|mortality|death'))
    f['phase_PHASE3']        = float(_rx(f"{cat} {stg}", r'phase\s*3|phase\s*iii'))
    f['is_competitive_space']= float(_rx(cat, r'versus|vs\.|compared to|soc|standard of care|competitor|head-to-head'))
    f['sentiment_score']     = float(_rx(cat, r'robust|meaningful|clinically\s+meaningful|impressive|remarkable|outstanding|transformative|unprecedented'))
    f['phase_PHASE2']        = float(_rx(f"{cat} {stg}", r'phase\s*2|phase\s*ii'))
    f['primary_endpoint_met']= float(_rx(cat, r'met\s+(primary|main)\s+endpoint|achieved\s+primary|primary\s+endpoint\s+(met|achieved|reached|positive)'))
    f['ta_ONCOLOGY']         = float(_rx(combined, r'oncology|cancer|tumor|malignancy|chemotherapy|immunotherapy|carcinoma|lymphoma|leukemia|melanoma|sarcoma'))
    _rct = float(_rx(cat, r'randomized|rct|controlled|double-blind|placebo'))
    f['rct_x_phase3']        = _rct * f['phase_PHASE3']

    # B: Regulatory designations
    f['has_breakthrough']    = float(_rx(cat, r'breakthrough\s+therapy|btd|breakthrough\s+designation'))
    f['has_orphan']          = float(_rx(combined, r'orphan|rare\s+disease|ultra-rare|ultra\s+rare'))
    f['has_priority_review'] = float(_rx(cat, r'priority\s+review|priority\s+designation'))
    f['has_fast_track']      = float(_rx(cat, r'fast\s+track|fasttrack|accelerated\s+approval'))

    # C: Risk flags
    f['is_gene_therapy']     = float(_has(combined, _GT_KW) or tk in _GT_TICKERS)
    f['is_psychedelic']      = float(_has(combined, _PSYCH_KW))
    f['safety_signal']       = float(_has(combined, _SAF_SEV)) * 2.0 + float(_has(combined, _SAF_MOD)) * 1.0
    f['ppm_flag']            = float(_has(combined, _PPM_KW))
    f['is_single_arm']       = float(_has(combined, _SA_KW))
    f['has_surrogate']       = float(_rx(cat, r'surrogate|biomarker\s+endpoint|orr\b|objective\s+response|pathologic.*complete.*response|pcr\b'))

    # D: Temporal
    f['is_hoeg_era']         = float(dt >= datetime(2025, 1, 1))
    f['accel_approval_2025'] = f['has_fast_track'] * f['is_hoeg_era']
    f['single_arm_2025']     = f['is_single_arm'] * f['is_hoeg_era']

    # E: Readout quality
    f['failure_signal']      = float(_rx(cat, r'failed|did\s+not\s+meet|discontinued|halted|stopped|terminated|futility|negative|missed|not\s+met'))
    f['strong_positive']     = float(_rx(cat, r'statistically\s+significant|highly\s+significant|p\s*[<≤]\s*0\.0[0-5]|p\s*[<≤]\s*0\.001|exceeded|surpassed'))
    f['dose_response']       = float(_rx(cat, r'dose[- ]?dependent|dose[- ]?response|higher\s+dose|all\s+doses'))
    f['safety_clean']        = float(_rx(cat, r'well[- ]?tolerated|favorable\s+safety|clean\s+safety|no\s+serious\s+adverse|no.*sae'))

    # F: TA risk
    f['ta_CNS']              = float(_rx(combined, r'\bcns\b|alzheimer|parkinson|schizophrenia|depression|bipolar|epilepsy|seizure|multiple\s+sclerosis|\bms\b|neurolog'))
    f['ta_RARE']             = float(_rx(combined, r'rare\s+disease|orphan|ultra-rare|genetic\s+disorder|inherited|lysosomal|enzyme\s+replacement'))
    f['ta_PAIN']             = float(_rx(combined, r'\bpain\b|analgesic|migraine|nociceptive|neuropathic\s+pain|fibromyalgia'))
    f['ta_IMMUNOLOGY']       = float(_rx(combined, r'autoimmune|rheumatoid|lupus|psoriasis|atopic\s+dermatitis|crohn|colitis|inflammatory'))

    # G: Interactions
    f['gene_therapy_x_phase3'] = f['is_gene_therapy'] * f['phase_PHASE3']
    f['safety_x_hoeg']        = f['safety_signal']  * f['is_hoeg_era']
    f['ppm_x_hoeg']           = f['ppm_flag']       * f['is_hoeg_era']
    f['oncology_x_phase3']    = f['ta_ONCOLOGY']    * f['phase_PHASE3']
    f['rare_x_positive']      = f['ta_RARE']        * f['strong_positive']
    f['failure_x_phase3']     = f['failure_signal']  * f['phase_PHASE3']

    vec = np.array([f[n] for n in _FEATURE_NAMES])
    return vec, f


# ═══════════════════════════════════════════════════════════════════════════
# GUNGNIR RISK OVERLAY
# ═══════════════════════════════════════════════════════════════════════════

_RULES = [
    # Hard caps (most severe first)
    ("FAILURE_SIGNAL",      "hard", 0.15, "💀 Explicit failure in readout text",
     lambda f: f.get('failure_signal',0) > 0),
    ("PPM_HOEG_ERA",        "hard", 0.30, "🔴 Primary pivotal miss + Hoeg-era FDA",
     lambda f: f.get('ppm_flag',0) > 0 and f.get('is_hoeg_era',0) > 0),
    ("PSYCHEDELIC",         "hard", 0.35, "🔴 Psychedelic compound — extreme headwind",
     lambda f: f.get('is_psychedelic',0) > 0),
    ("SEVERE_SAFETY_HOEG",  "hard", 0.45, "🔴 Severe safety (DILI/cardiac) + Hoeg era",
     lambda f: f.get('safety_signal',0) >= 2 and f.get('is_hoeg_era',0) > 0),
    ("GENE_THERAPY_P3",     "hard", 0.55, "🟡 Gene therapy Phase 3 — CMC risk",
     lambda f: f.get('is_gene_therapy',0) > 0 and f.get('phase_PHASE3',0) > 0),
    ("SINGLE_ARM_HOEG",     "hard", 0.60, "🟡 Single-arm in Hoeg era",
     lambda f: f.get('is_single_arm',0) > 0 and f.get('is_hoeg_era',0) > 0),
    # Soft penalties
    ("MODERATE_SAFETY",     "pen",  0.08, "⚡ Moderate safety concern",
     lambda f: 0 < f.get('safety_signal',0) < 2),
    ("GENE_THERAPY",        "pen",  0.05, "⚡ Gene therapy CMC risk",
     lambda f: f.get('is_gene_therapy',0) > 0),
    ("CNS",                 "pen",  0.03, "⚡ CNS — higher CRL rate",
     lambda f: f.get('ta_CNS',0) > 0),
    ("HOEG_ERA",            "pen",  0.02, "⚡ Hoeg-era FDA uncertainty",
     lambda f: f.get('is_hoeg_era',0) > 0),
    # Boosts
    ("RCT_HARD_ENDPOINT",   "boost",0.03, "✨ RCT + hard endpoint — gold standard",
     lambda f: f.get('rct_x_phase3',0) > 0 and f.get('is_hard_endpoint',0) > 0),
]

def _apply_overlay(ml_score, features):
    """Apply Gungnir risk rules. Returns (final_score, tier, fired_rules)."""
    cap = 1.0
    penalty = 0.0
    fired = []
    for name, rtype, value, desc, cond in _RULES:
        try:
            if not cond(features): continue
        except Exception: continue
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
    tier = "TIER_1" if score >= 0.70 else "TIER_2" if score >= 0.50 else "TIER_3" if score >= 0.35 else "TIER_4"
    return score, tier, cap if cap < 1.0 else None, penalty, fired


# ═══════════════════════════════════════════════════════════════════════════
# SCORER
# ═══════════════════════════════════════════════════════════════════════════

_TRADE = {
    "TIER_1": ("LONG",          "HIGH",     "100%", "T-5"),
    "TIER_2": ("CAUTIOUS LONG", "MODERATE", "50%",  "T-7"),
    "TIER_3": ("AVOID",         "LOW",      "—",    "—"),
    "TIER_4": ("NO TRADE",      "VERY LOW", "—",    "—"),
}

def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class GungnirScorer:
    """
    Production readout scorer.

    Usage:
        scorer = GungnirScorer()                     # logistic-only
        scorer = GungnirScorer("xgb_model_v3.json")  # full ensemble
        result = scorer.score("Phase 3 met primary endpoint...",
                              ticker="ACME", indication="breast cancer")
        scorer.print_scorecard(result)
    """

    def __init__(self, xgb_path=None):
        """Load scorer. Optionally provide path to XGBoost model file."""
        self.xgb_model = None
        if xgb_path and _HAS_XGB and os.path.exists(xgb_path):
            self.xgb_model = xgb.Booster()
            self.xgb_model.load_model(xgb_path)
        self.mode = "ensemble" if self.xgb_model else "logistic-only"

    def _score_logistic(self, vec):
        feat = vec.copy()
        for i in _FLIP_INDICES:
            feat[i] = -feat[i]
        scaled = (feat - _SCALER_MEAN) / _SCALER_SCALE
        return float(_sigmoid(_LOGIT_INTERCEPT + np.dot(_LOGIT_COEFS, scaled)))

    def _score_xgb(self, vec):
        if not self.xgb_model: return None
        xvec = np.array([[vec[i] for i, f in enumerate(_FEATURE_NAMES) if f != "failure_signal"]])
        dm = xgb.DMatrix(xvec, feature_names=_XGB_FEATURES)
        return float(self.xgb_model.predict(dm)[0])

    def _contributions(self, vec, fdict):
        feat = vec.copy()
        for i in _FLIP_INDICES:
            feat[i] = -feat[i]
        scaled = (feat - _SCALER_MEAN) / _SCALER_SCALE
        contribs = _LOGIT_COEFS * scaled
        active = [(n, fdict[n], float(contribs[i]))
                  for i, n in enumerate(_FEATURE_NAMES) if fdict.get(n, 0) != 0]
        active.sort(key=lambda x: abs(x[2]), reverse=True)
        return active[:10]

    def score(self, catalyst, ticker="", drug="", indication="", stage="", date="2026-01-01"):
        """
        Score a readout event.

        Args:
            catalyst:   str — The readout text (press release, headline, etc.)
            ticker:     str — Stock ticker
            drug:       str — Drug/asset name
            indication: str — Disease indication
            stage:      str — Trial phase (e.g. "Phase 3")
            date:       str — Catalyst date YYYY-MM-DD

        Returns:
            dict with: tier, final_score, ml_score, trade, risk_flags, etc.
        """
        vec, fdict = extract_features(catalyst, ticker, drug, indication, stage, date)

        logit_p = self._score_logistic(vec)
        xgb_p = self._score_xgb(vec)

        if xgb_p is not None:
            ml_p = float(_sigmoid(_STACK_INTERCEPT + _STACK_XGB_COEF * xgb_p + _STACK_LOGIT_COEF * logit_p))
        else:
            ml_p = logit_p

        final, tier, hard_cap, soft_pen, rules = _apply_overlay(ml_p, fdict)
        action, confidence, sizing, exit_day = _TRADE[tier]
        contribs = self._contributions(vec, fdict)

        # Collect signals
        pos_signals = []
        if fdict.get('primary_endpoint_met'): pos_signals.append("✅ Primary endpoint met")
        if fdict.get('strong_positive'):      pos_signals.append("✅ Statistically significant")
        if fdict.get('safety_clean'):         pos_signals.append("✅ Clean safety profile")
        if fdict.get('has_surrogate'):        pos_signals.append("✅ Surrogate endpoint")
        if fdict.get('has_breakthrough'):     pos_signals.append("✅ Breakthrough designation")
        if fdict.get('dose_response'):        pos_signals.append("✅ Dose-response")
        if fdict.get('has_orphan'):           pos_signals.append("✅ Orphan designation")
        if fdict.get('sentiment_score'):      pos_signals.append("✅ Strong positive language")

        risk_flags = [r['desc'] for r in rules if r['type'] in ('CAP', 'PEN')]

        return {
            "tier": tier, "final_score": round(final, 4),
            "ml_score": round(ml_p, 4),
            "logistic": round(logit_p, 4),
            "xgboost": round(xgb_p, 4) if xgb_p is not None else None,
            "hard_cap": hard_cap, "soft_penalty": round(soft_pen, 4),
            "action": action, "confidence": confidence,
            "sizing": sizing, "exit": exit_day,
            "positive_signals": pos_signals, "risk_flags": risk_flags,
            "rules_fired": rules, "contributions": contribs,
            "mode": self.mode,
            "ticker": ticker, "drug": drug,
            "indication": indication, "date": date,
            "active_features": sum(1 for v in fdict.values() if v != 0),
        }

    def print_scorecard(self, r):
        """Pretty-print a scorecard to stdout."""
        W = 72
        print(f"\n{'═'*W}")
        print(f"  ODIN GUNGNIR v4.0 — READOUT SCORECARD  ({r['mode']})")
        print(f"{'═'*W}")
        print(f"  Ticker: {r['ticker']:12s}  Drug: {r['drug']}")
        print(f"  Indication: {r['indication']:8s}  Date: {r['date']}")

        print(f"\n  SCORES:")
        print(f"    Logistic:  {r['logistic']:.1%}")
        if r['xgboost'] is not None:
            print(f"    XGBoost:   {r['xgboost']:.1%}")
        print(f"    ML Score:  {r['ml_score']:.1%}")
        if r['hard_cap'] is not None:
            print(f"    Hard Cap:  {r['hard_cap']:.0%} ← RISK OVERRIDE")
        if r['soft_penalty'] != 0:
            print(f"    Penalties: {-r['soft_penalty']:+.0%}")
        print(f"    ► FINAL:   {r['final_score']:.1%}")

        print(f"\n  ┌{'─'*46}┐")
        print(f"  │  TIER:   {r['tier']:35s}│")
        print(f"  │  ACTION: {r['action']:35s}│")
        print(f"  │  SIZING: {r['sizing']:35s}│")
        print(f"  │  EXIT:   {r['exit']:35s}│")
        print(f"  └{'─'*46}┘")

        if r['positive_signals']:
            print(f"\n  POSITIVE SIGNALS:")
            for s in r['positive_signals']: print(f"    {s}")

        if r['risk_flags']:
            print(f"\n  RISK FLAGS:")
            for f in r['risk_flags']: print(f"    {f}")

        if r['rules_fired']:
            print(f"\n  GUNGNIR RULES:")
            for rule in r['rules_fired']:
                if rule['type'] == 'CAP':
                    print(f"    🛡️  {rule['name']}: cap={rule['value']:.0%}")
                elif rule['type'] == 'PEN':
                    print(f"    ⚡ {rule['name']}: {rule['value']:+.0%}")
                elif rule['type'] == 'BOOST':
                    print(f"    ✨ {rule['name']}: +{rule['value']:.0%}")

        if r['contributions']:
            print(f"\n  TOP FEATURE CONTRIBUTIONS:")
            for name, val, contrib in r['contributions']:
                arrow = '↑' if contrib > 0 else '↓'
                print(f"    {arrow} {name:>28s} = {val:.1f}  ({contrib:+.3f})")

        print(f"\n  Active features: {r['active_features']}/35")
        print(f"{'═'*W}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def _interactive():
    """Interactive scoring mode."""
    # Find XGB model
    xgb_path = None
    for p in ['xgb_model_v3.json', 'xgb_model_v4.json']:
        if os.path.exists(p):
            xgb_path = p
            break

    scorer = GungnirScorer(xgb_path)
    print(f"\n⚔️  ODIN GUNGNIR v4.0 — Interactive Scorer")
    print(f"   Mode: {scorer.mode}")
    print(f"   Type 'quit' to exit.\n")

    while True:
        print("─" * 72)
        catalyst = input("  Catalyst text: ").strip()
        if catalyst.lower() in ('quit', 'exit', 'q'): break
        if not catalyst: continue

        ticker     = input("  Ticker []:     ").strip()
        drug       = input("  Drug []:       ").strip()
        indication = input("  Indication []: ").strip()
        stage      = input("  Stage []:      ").strip()
        date       = input("  Date [2026-01-01]: ").strip() or "2026-01-01"

        result = scorer.score(catalyst, ticker, drug, indication, stage, date)
        scorer.print_scorecard(result)
        print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ODIN Gungnir v4.0 — Readout Scorer")
    parser.add_argument("--catalyst", "-c", help="Catalyst text to score")
    parser.add_argument("--ticker", "-t", default="", help="Stock ticker")
    parser.add_argument("--drug", "-d", default="", help="Drug name")
    parser.add_argument("--indication", "-i", default="", help="Disease indication")
    parser.add_argument("--stage", "-s", default="", help="Trial phase")
    parser.add_argument("--date", default="2026-01-01", help="Catalyst date YYYY-MM-DD")
    parser.add_argument("--xgb", default=None, help="Path to XGBoost model file")
    parser.add_argument("--demo", action="store_true", help="Run demo cases")
    args = parser.parse_args()

    # Find XGB
    xgb_path = args.xgb
    if not xgb_path:
        for p in ['xgb_model_v3.json', 'xgb_model_v4.json']:
            if os.path.exists(p):
                xgb_path = p
                break

    if args.demo:
        scorer = GungnirScorer(xgb_path)
        demos = [
            ("Phase 3 randomized double-blind placebo-controlled trial met primary endpoint of "
             "progression-free survival. Statistically significant (p<0.001). Well-tolerated. "
             "Clinically meaningful.", "ACME", "acmecillin", "breast cancer", "Phase 3", "2026-02-16"),
            ("Phase 3 gene therapy lentiviral gene transfer for LAD-I. Single-arm study. "
             "Rare disease. Prior complete response letter. Manufacturing concerns.",
             "RCKT", "RP-L201", "leukocyte adhesion deficiency", "Phase 3", "2026-02-16"),
            ("Phase 3 trial for depression. Did not meet primary endpoint. Failed to show "
             "statistical significance. Discontinued.",
             "FAIL", "failamab", "depression", "Phase 3", "2026-02-16"),
            ("Phase 3 GEMINI trial for tolebrutinib in multiple sclerosis. Hepatotoxicity — "
             "drug-induced liver injury (DILI). FDA REMS likely. Elevated ALT and liver enzyme.",
             "SNY", "tolebrutinib", "multiple sclerosis", "Phase 3", "2025-08-20"),
            ("Phase 3 MAPP2 MDMA-assisted therapy for PTSD. FDA advisory committee voted against. "
             "Cardiac safety concerns. Single-arm open-label extension.",
             "MDRX", "MDMA", "PTSD", "Phase 3", "2025-01-15"),
        ]
        print(f"\n⚔️  ODIN GUNGNIR v4.0 — Demo ({scorer.mode})\n")
        for cat, tk, dr, ind, stg, dt in demos:
            result = scorer.score(cat, tk, dr, ind, stg, dt)
            scorer.print_scorecard(result)
        # Summary
        print(f"\n{'═'*72}")
        print(f"  {'Case':>45s} {'ML':>7s} {'Final':>7s} {'Tier':>8s}")
        print(f"  {'─'*70}")
        for cat, tk, dr, ind, stg, dt in demos:
            r = scorer.score(cat, tk, dr, ind, stg, dt)
            label = f"{tk} {dr[:20]}"
            print(f"  {label:>45s} {r['ml_score']:>7.1%} {r['final_score']:>7.1%} {r['tier']:>8s}")
        print(f"{'═'*72}")
        return

    if args.catalyst:
        scorer = GungnirScorer(xgb_path)
        result = scorer.score(args.catalyst, args.ticker, args.drug,
                              args.indication, args.stage, args.date)
        scorer.print_scorecard(result)
    else:
        _interactive()


if __name__ == "__main__":
    main()
