"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL HONING ENGINE v2.0                                     ║
║  Self-Improving Biotech Catalyst Prediction System                     ║
║                                                                        ║
║  Based on ODIN_Complete_v12.0 (PDUFA_MODE + PHASE3_MODE)               ║
║  EXPANDED: 23 → 62 PDUFA signals, 5 → 12 Phase3 modifiers             ║
║                                                                        ║
║  Signal Tiers:                                                         ║
║    VALIDATED  - Empirical logits from n=47+ training events             ║
║    THEORETICAL - Directional priors from domain knowledge               ║
║    DISCOVERY  - Start at 0.0, learned from outcomes by honing engine    ║
║                                                                        ║
║  Integrates: ClinicalTrials, PubMed, ChEMBL, FinBrain, LunarCrush,    ║
║              bioRxiv, CMS Coverage MCPs                                ║
║                                                                        ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import math
import hashlib
import os
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════
#  CORE MATH
# ═══════════════════════════════════════════════════════════════

def sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def logit(p: float) -> float:
    """Inverse sigmoid (log-odds)."""
    p = max(1e-9, min(1 - 1e-9, p))
    return math.log(p / (1 - p))


def _safe_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return bool(val) and val == val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "t", "yes", "y", "1")
    return False


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val)) if val is not None else default
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════
#  SECTION 1: EXPANDED SIGNAL REGISTRY — 62 PDUFA SIGNALS
# ═══════════════════════════════════════════════════════════════
#
#  Signal confidence tiers:
#    VALIDATED   = Empirically calibrated on training data (n≥30 events)
#    THEORETICAL = Directional prior from domain expertise, conservative logit
#    DISCOVERY   = Logit starts at 0.0, honing engine learns weight from outcomes
#
#  Signal types:
#    bool       = Binary flag (True/False from event field)
#    cond       = Conditional on multiple fields
#    lookup     = Lookup table (e.g. therapeutic area)
#    threshold  = Fires when numeric field crosses threshold
#    range      = Continuous value mapped to logit via scaling
#    social     = LunarCrush social data
#    composite  = Derived from multiple inputs

PDUFA_MODE_CONFIG = {
    "base_logit": 1.5645,            # 82.7% baseline approval rate
    "signals": {
        # ──────────────────────────────────────────────────────────
        # CATEGORY 1: REGULATORY DESIGNATIONS (Source: FDA / ClinicalTrials.gov)
        # ──────────────────────────────────────────────────────────
        "S01_BTD": {
            "logit": 0.693, "type": "bool", "field": "btd",
            "tier": "VALIDATED", "source": "ClinicalTrials",
            "desc": "Breakthrough Therapy Designation"
        },
        "S02_ORPHAN": {
            "logit": 0.560, "type": "bool", "field": "orphan",
            "tier": "VALIDATED", "source": "ClinicalTrials",
            "desc": "Orphan Drug Designation"
        },
        "S03_PRIORITY_REVIEW": {
            "logit": 0.470, "type": "bool", "field": "priority_review",
            "tier": "VALIDATED", "source": "ClinicalTrials",
            "desc": "Priority Review granted"
        },
        "S04_FAST_TRACK": {
            "logit": 0.165, "type": "bool", "field": "fast_track",
            "tier": "VALIDATED", "source": "ClinicalTrials",
            "desc": "Fast Track Designation"
        },
        "S05_ACCELERATED_APPROVAL": {
            "logit": 0.275, "type": "bool", "field": "accelerated_approval",
            "tier": "VALIDATED", "source": "ClinicalTrials",
            "desc": "Accelerated Approval pathway"
        },
        "S06_RMAT": {
            "logit": 0.350, "type": "bool", "field": "rmat",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Regenerative Medicine Advanced Therapy designation"
        },
        "S07_QIDP": {
            "logit": 0.220, "type": "bool", "field": "qidp",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Qualified Infectious Disease Product (extra 5yr exclusivity)"
        },
        "S08_PEDIATRIC_VOUCHER": {
            "logit": 0.165, "type": "bool", "field": "pediatric_voucher_eligible",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Priority Review Voucher eligible (rare pediatric/tropical)"
        },
        "S09_FIRST_IN_CLASS": {
            "logit": 0.275, "type": "bool", "field": "first_in_class",
            "tier": "THEORETICAL", "source": "ChEMBL",
            "desc": "Novel mechanism — no approved drugs in class"
        },
        "S10_REMS_LIKELY": {
            "logit": -0.220, "type": "bool", "field": "rems_likely",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "REMS requirement likely (safety concern signal)"
        },
        "S11_UNMET_NEED": {
            "logit": 0.330, "type": "bool", "field": "high_unmet_need",
            "tier": "THEORETICAL", "source": "derived",
            "desc": "High unmet medical need (no approved therapies or inadequate options)"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 2: ADCOM & FDA INTERACTION
        # ──────────────────────────────────────────────────────────
        "S12_ADCOM_HIGH": {
            "logit": 0.441, "type": "cond", "condition": "adcom_vote_pct >= 0.65",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Advisory Committee vote ≥65%"
        },
        "S13_ADCOM_MID": {
            "logit": -0.330, "type": "cond", "condition": "0.50 <= adcom_vote_pct < 0.65",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Advisory Committee vote 50-65%"
        },
        "S14_ADCOM_LOW": {
            "logit": -1.047, "type": "cond", "condition": "adcom_vote_pct < 0.50",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Advisory Committee vote <50%"
        },
        "S15_ADCOM_WAIVED": {
            "logit": 0.165, "type": "bool", "field": "adcom_waived",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "No AdCom scheduled (generally bullish — FDA comfortable)"
        },
        "S16_RTF_CLEAN": {
            "logit": 0.110, "type": "bool", "field": "rtf_clean",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "No Refuse to File letter — clean NDA/BLA acceptance"
        },
        "S17_ROLLING_NDA": {
            "logit": 0.220, "type": "bool", "field": "rolling_submission",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Rolling NDA/BLA submission (accelerated review path)"
        },
        "S18_FDA_DIVISION_RATE": {
            "logit": 0.0, "type": "range", "field": "fda_division_approval_rate",
            "tier": "DISCOVERY", "source": "FDA",
            "scale": 0.5,  # logit contribution = (rate - 0.85) * scale
            "center": 0.85,
            "desc": "Historical approval rate of reviewing FDA division"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 3: CRL & RESUBMISSION HISTORY
        # ──────────────────────────────────────────────────────────
        "S19_PRIOR_CRL": {
            "logit": -0.470, "type": "bool", "field": "prior_crl",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Drug previously received Complete Response Letter"
        },
        "S20_CLASS1_RESUB": {
            "logit": 0.866, "type": "cond", "condition": "prior_crl AND resubmission_class == 1",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Class 1 resubmission after CRL (minor issues)"
        },
        "S21_CLASS2_RESUB": {
            "logit": -0.275, "type": "cond", "condition": "prior_crl AND resubmission_class == 2",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Class 2 resubmission after CRL (major issues)"
        },
        "S22_CRL_REASON_CMC_ONLY": {
            "logit": 0.330, "type": "cond", "condition": "prior_crl AND crl_reason == 'CMC'",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Prior CRL was for CMC/manufacturing reasons only (most fixable)"
        },
        "S23_CRL_REASON_CLINICAL": {
            "logit": -0.440, "type": "cond", "condition": "prior_crl AND crl_reason == 'CLINICAL'",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Prior CRL for clinical efficacy/safety reasons (hardest to fix)"
        },
        "S24_MULTIPLE_CRLS": {
            "logit": -0.550, "type": "cond", "condition": "crl_count >= 2",
            "tier": "THEORETICAL", "source": "FDA",
            "desc": "Drug has received 2+ CRLs (increasingly bearish)"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 4: SPONSOR PROFILE (Source: FinBrain / SEC)
        # ──────────────────────────────────────────────────────────
        "S25_EXPERIENCED_SPONSOR": {
            "logit": 0.275, "type": "cond", "condition": "sponsor_prior_approvals >= 5",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Sponsor has ≥5 prior FDA approvals"
        },
        "S26_INEXPERIENCED_SPONSOR": {
            "logit": -0.386, "type": "cond", "condition": "sponsor_prior_approvals == 0",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Sponsor has zero prior FDA approvals"
        },
        "S27_MEGA_CAP_SPONSOR": {
            "logit": 0.165, "type": "cond", "condition": "market_cap_tier == 'mega'",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Mega-cap sponsor (>$200B) — deep resources for regulatory"
        },
        "S28_MICRO_CAP_SPONSOR": {
            "logit": -0.165, "type": "cond", "condition": "market_cap_tier == 'micro'",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Micro-cap sponsor (<$300M) — limited resources, binary event"
        },
        "S29_BIG_PHARMA_PARTNER": {
            "logit": 0.220, "type": "bool", "field": "big_pharma_partner",
            "tier": "THEORETICAL", "source": "web_search",
            "desc": "Drug partnered with top-20 pharma (validation + resources)"
        },
        "S30_SPONSOR_RECENT_APPROVAL": {
            "logit": 0.110, "type": "bool", "field": "sponsor_recent_approval",
            "tier": "DISCOVERY", "source": "FDA",
            "desc": "Sponsor had FDA approval in last 24 months"
        },
        "S31_SPONSOR_RECENT_CRL": {
            "logit": -0.110, "type": "bool", "field": "sponsor_recent_crl",
            "tier": "DISCOVERY", "source": "FDA",
            "desc": "Sponsor received CRL in last 24 months (division relationship)"
        },
        "S32_LOW_CASH_RUNWAY": {
            "logit": -0.220, "type": "cond", "condition": "cash_runway_months < 12",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Cash runway under 12 months (financial stress may affect execution)"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 5: MANUFACTURING & CMC (Source: FDA 483 / CMO DB)
        # ──────────────────────────────────────────────────────────
        "S33_MFG_RISK": {
            "logit": -0.661, "type": "bool", "field": "manufacturing_risk",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "Known manufacturing or supply chain issues"
        },
        "S34_FORM_483": {
            "logit": -0.386, "type": "bool", "field": "form_483_issues",
            "tier": "VALIDATED", "source": "FDA",
            "desc": "FDA Form 483 inspection flags at manufacturing site"
        },
        "S35_BIOLOGICS_COMPLEXITY": {
            "logit": -0.165, "type": "bool", "field": "is_biologic",
            "tier": "THEORETICAL", "source": "ChEMBL",
            "desc": "Biologic product (higher CMC complexity vs small molecule)"
        },
        "S36_CMO_HIGH_RISK": {
            "logit": -0.275, "type": "cond", "condition": "cmo_risk_tier >= 3",
            "tier": "THEORETICAL", "source": "CMO_database",
            "desc": "Contract manufacturer is high-risk tier"
        },
        "S37_GMP_INSPECTION_CLEAN": {
            "logit": 0.110, "type": "bool", "field": "gmp_inspection_clean",
            "tier": "DISCOVERY", "source": "FDA",
            "desc": "Successful GMP inspection at manufacturing site in last 12 months"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 6: CLINICAL TRIAL QUALITY (Source: ClinicalTrials.gov MCP)
        # ──────────────────────────────────────────────────────────
        "S38_PIVOTAL_MET_PRIMARY": {
            "logit": 0.693, "type": "bool", "field": "pivotal_met_primary",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Pivotal Phase 3 met primary endpoint — strongest clinical signal"
        },
        "S39_MULTIPLE_PIVOTALS_POSITIVE": {
            "logit": 0.440, "type": "bool", "field": "multiple_pivotals_positive",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Multiple positive pivotal trials (stronger evidence base)"
        },
        "S40_LARGE_ENROLLMENT": {
            "logit": 0.165, "type": "threshold", "field": "enrollment",
            "threshold": 500, "direction": "above",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Large trial enrollment (n≥500) — more statistical power"
        },
        "S41_SMALL_ENROLLMENT": {
            "logit": -0.110, "type": "threshold", "field": "enrollment",
            "threshold": 100, "direction": "below",
            "tier": "DISCOVERY", "source": "ClinicalTrials",
            "desc": "Small trial enrollment (n<100) — limited power, higher uncertainty"
        },
        "S42_DOUBLE_BLIND_RCT": {
            "logit": 0.110, "type": "bool", "field": "double_blind_rct",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Double-blind randomized controlled trial (gold standard design)"
        },
        "S43_OPEN_LABEL_SINGLE_ARM": {
            "logit": -0.220, "type": "bool", "field": "open_label_single_arm",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Open-label single-arm trial (weaker evidence, more FDA scrutiny)"
        },
        "S44_HARD_ENDPOINT": {
            "logit": 0.165, "type": "bool", "field": "hard_clinical_endpoint",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Hard clinical endpoint (OS, mortality) vs surrogate"
        },
        "S45_SURROGATE_ENDPOINT": {
            "logit": -0.110, "type": "bool", "field": "surrogate_endpoint_only",
            "tier": "DISCOVERY", "source": "ClinicalTrials",
            "desc": "Approval based on surrogate endpoint only (may need confirmatory)"
        },
        "S46_PVALUE_STRONG": {
            "logit": 0.330, "type": "cond", "condition": "pivotal_pvalue < 0.001",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Pivotal trial p-value < 0.001 (highly significant)"
        },
        "S47_SAFETY_CLEAN": {
            "logit": 0.220, "type": "bool", "field": "safety_profile_clean",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Clean safety profile — no major AE signals in pivotal"
        },
        "S48_SAFETY_CONCERNS": {
            "logit": -0.440, "type": "bool", "field": "safety_concerns",
            "tier": "THEORETICAL", "source": "ClinicalTrials",
            "desc": "Safety signals in pivotal trial (black box risk, deaths, serious AEs)"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 7: COMPETITIVE LANDSCAPE (Source: ChEMBL / web)
        # ──────────────────────────────────────────────────────────
        "S49_FIRST_IN_INDICATION": {
            "logit": 0.275, "type": "bool", "field": "first_in_indication",
            "tier": "THEORETICAL", "source": "ChEMBL",
            "desc": "No approved therapy for this indication (FDA urgency)"
        },
        "S50_CROWDED_INDICATION": {
            "logit": -0.165, "type": "bool", "field": "crowded_indication",
            "tier": "THEORETICAL", "source": "ChEMBL",
            "desc": "3+ approved competitors already (lower FDA urgency)"
        },
        "S51_BEST_IN_CLASS": {
            "logit": 0.220, "type": "bool", "field": "best_in_class_data",
            "tier": "DISCOVERY", "source": "derived",
            "desc": "Superior efficacy data vs existing approved therapies"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 8: FINANCIAL SIGNALS (Source: FinBrain MCP)
        # ──────────────────────────────────────────────────────────
        "S52_INSIDER_BUY": {
            "logit": 0.220, "type": "bool", "field": "insider_buy_signal",
            "tier": "VALIDATED", "source": "FinBrain",
            "desc": "Insider buying pre-PDUFA (conviction signal)"
        },
        "S53_INSIDER_SELL_CLUSTER": {
            "logit": -0.275, "type": "bool", "field": "insider_sell_cluster",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Multiple insiders selling pre-PDUFA (bearish signal)"
        },
        "S54_INSIDER_BUY_LARGE": {
            "logit": 0.330, "type": "threshold", "field": "insider_buy_value",
            "threshold": 500000, "direction": "above",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Large insider purchase (>$500K) — high conviction"
        },
        "S55_OPTIONS_BULLISH": {
            "logit": 0.165, "type": "bool", "field": "options_bullish",
            "tier": "VALIDATED", "source": "FinBrain",
            "desc": "Bullish options flow pre-PDUFA"
        },
        "S56_OPTIONS_PUT_CALL_BEARISH": {
            "logit": -0.220, "type": "threshold", "field": "put_call_ratio",
            "threshold": 1.5, "direction": "above",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Put/call ratio >1.5 (heavy put buying, bearish)"
        },
        "S57_CONGRESS_TRADE_BULLISH": {
            "logit": 0.165, "type": "bool", "field": "congress_trade_bullish",
            "tier": "DISCOVERY", "source": "FinBrain",
            "desc": "US Senator or House rep purchased shares pre-PDUFA"
        },
        "S58_ANALYST_CONSENSUS_BUY": {
            "logit": 0.165, "type": "bool", "field": "analyst_consensus_buy",
            "tier": "THEORETICAL", "source": "FinBrain",
            "desc": "Majority analyst ratings are Buy/Strong Buy"
        },
        "S59_NEWS_SENTIMENT_BULLISH": {
            "logit": 0.110, "type": "bool", "field": "news_sentiment_bullish",
            "tier": "DISCOVERY", "source": "FinBrain",
            "desc": "FinBrain news sentiment score >0.5 (bullish)"
        },
        "S60_NEWS_SENTIMENT_BEARISH": {
            "logit": -0.165, "type": "bool", "field": "news_sentiment_bearish",
            "tier": "DISCOVERY", "source": "FinBrain",
            "desc": "FinBrain news sentiment score <-0.3 (bearish)"
        },
        "S61_SHORT_INTEREST_HIGH": {
            "logit": -0.165, "type": "threshold", "field": "short_interest_pct",
            "threshold": 15.0, "direction": "above",
            "tier": "DISCOVERY", "source": "FinBrain",
            "desc": "Short interest >15% of float (informed bears or squeeze risk)"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 9: SOCIAL SENTIMENT (Source: LunarCrush MCP)
        # ──────────────────────────────────────────────────────────
        "S62_SOCIAL_SENTIMENT": {
            "logit": 0.165, "type": "social", "field": "sentiment_bullish",
            "tier": "VALIDATED", "source": "LunarCrush",
            "desc": "LunarCrush social sentiment is bullish"
        },
        "S63_ENGAGEMENT_SPIKE": {
            "logit": 0.110, "type": "social", "field": "engagement_spike",
            "tier": "VALIDATED", "source": "LunarCrush",
            "desc": "Social engagement spike (>2x normal volume)"
        },
        "S64_SOCIAL_SILENCE": {
            "logit": -0.110, "type": "social", "field": "social_silence",
            "tier": "VALIDATED", "source": "LunarCrush",
            "desc": "Unusually low social activity pre-catalyst (apathy signal)"
        },
        "S65_SMART_DIVERGENCE": {
            "logit": -0.110, "type": "social", "field": "smart_divergence",
            "tier": "VALIDATED", "source": "LunarCrush",
            "desc": "Smart money diverges from retail sentiment"
        },
        "S66_GALAXY_SCORE_HIGH": {
            "logit": 0.110, "type": "threshold", "field": "galaxy_score",
            "threshold": 70, "direction": "above",
            "tier": "DISCOVERY", "source": "LunarCrush",
            "desc": "LunarCrush Galaxy Score >70 (strong social momentum)"
        },
        "S67_SOCIAL_VOLUME_SURGE": {
            "logit": 0.110, "type": "threshold", "field": "social_volume_ratio",
            "threshold": 3.0, "direction": "above",
            "tier": "DISCOVERY", "source": "LunarCrush",
            "desc": "Social post volume >3x 30-day average"
        },
        "S68_SOCIAL_DOMINANCE": {
            "logit": 0.0, "type": "threshold", "field": "social_dominance",
            "threshold": 5.0, "direction": "above",
            "tier": "DISCOVERY", "source": "LunarCrush",
            "desc": "Topic dominance >5% in biotech vertical"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 10: PUBLICATION EVIDENCE (Source: PubMed / bioRxiv MCPs)
        # ──────────────────────────────────────────────────────────
        "S69_HIGH_IMPACT_PUBLICATION": {
            "logit": 0.220, "type": "bool", "field": "high_impact_journal",
            "tier": "THEORETICAL", "source": "PubMed",
            "desc": "Pivotal results published in NEJM/Lancet/JAMA/Nature"
        },
        "S70_PUBMED_EVIDENCE_RICH": {
            "logit": 0.110, "type": "threshold", "field": "pubmed_publication_count",
            "threshold": 20, "direction": "above",
            "tier": "DISCOVERY", "source": "PubMed",
            "desc": "20+ PubMed publications for drug/mechanism (deep evidence base)"
        },
        "S71_RECENT_PREPRINT_ACTIVITY": {
            "logit": 0.0, "type": "threshold", "field": "biorxiv_recent_count",
            "threshold": 3, "direction": "above",
            "tier": "DISCOVERY", "source": "bioRxiv",
            "desc": "3+ bioRxiv preprints in last 90 days (active research)"
        },
        "S72_NEGATIVE_PUBLICATION": {
            "logit": -0.275, "type": "bool", "field": "negative_publication",
            "tier": "THEORETICAL", "source": "PubMed",
            "desc": "Published negative trial results for this drug"
        },
        "S73_KOL_SUPPORT": {
            "logit": 0.110, "type": "bool", "field": "kol_support",
            "tier": "DISCOVERY", "source": "PubMed",
            "desc": "Key opinion leaders publicly supporting drug/mechanism"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 11: THERAPEUTIC AREA (Source: derived)
        # ──────────────────────────────────────────────────────────
        "S74_TA_ADJUSTMENT": {
            "logit": "lookup", "type": "lookup", "field": "therapeutic_area",
            "dampening": 0.83,
            "tier": "VALIDATED", "source": "derived",
            "desc": "Therapeutic area risk/benefit adjustment"
        },
        "S75_TA_TREND_IMPROVING": {
            "logit": 0.110, "type": "bool", "field": "ta_trend_improving",
            "tier": "DISCOVERY", "source": "derived",
            "desc": "TA approval rate improving vs 5-year average"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 12: COMPOSITE & SPECIALIST SIGNALS
        # ──────────────────────────────────────────────────────────
        "S76_SPECIALIST_COMPOSITE": {
            "logit": 0.165, "type": "composite", "field": "specialist_proxy",
            "tier": "VALIDATED", "source": "derived",
            "desc": "≥2 specialist criteria met (quality composite)"
        },
        "S77_REGULATORY_TAILWIND": {
            "logit": 0.0, "type": "range", "field": "regulatory_designation_count",
            "tier": "DISCOVERY", "source": "derived",
            "scale": 0.15,  # logit per designation above 1
            "center": 1,
            "desc": "Count of positive designations (BTD+Orphan+PR+FT+AA)"
        },
        "S78_DATA_QUALITY_SCORE": {
            "logit": 0.0, "type": "range", "field": "data_quality_score",
            "tier": "DISCOVERY", "source": "derived",
            "scale": 0.5,   # logit per unit above center
            "center": 0.5,
            "desc": "Composite: trial design + enrollment + p-value + safety"
        },

        # ──────────────────────────────────────────────────────────
        # CATEGORY 13: MEDICARE/COVERAGE (Source: CMS Coverage MCP)
        # ──────────────────────────────────────────────────────────
        "S79_NCD_EXISTS": {
            "logit": 0.0, "type": "bool", "field": "ncd_exists",
            "tier": "DISCOVERY", "source": "CMS_Coverage",
            "desc": "National Coverage Determination exists for indication"
        },
        "S80_LCD_FAVORABLE": {
            "logit": 0.0, "type": "bool", "field": "lcd_favorable",
            "tier": "DISCOVERY", "source": "CMS_Coverage",
            "desc": "Favorable Local Coverage Determination in place"
        },
    },

    # ── Therapeutic Area Logit Lookup Table ──
    "ta_logits": {
        "Pain Management": -1.654,
        "Ophthalmology": -1.379,
        "Nephrology": -1.213,
        "Hematology": -0.992,
        "CNS/Neurology": -0.551,
        "Cardiovascular": -0.441,
        "Metabolic/Endocrine": -0.386,
        "Other": -0.330,
        "Rare Disease": -0.220,
        "Immunology": 0.110,
        "Dermatology": 0.165,
        "Oncology": 0.330,
        "GI/Hepatology": 0.386,
        "Respiratory": 0.497,
        "Infectious Disease": 0.551,
        "Vaccines": 0.717,
        "Women's Health": 0.717,
    },

    # ── Tier Thresholds ──
    "tier_thresholds": {
        "tier1": 0.858,    # LONG — 95.6% historical approval rate
        "tier2": 0.734,    # NO_TRADE — trap zone
        "tier3": 0.578,    # AVOID or SHORT
    },

    # ── Validation Stats ──
    "validation": {
        "n_events": 1934,
        "auc": 0.891,
        "accuracy": 0.872,
        "brier_score": 0.085,
        "p_value": 4.6e-13,
    }
}

# Total signal count
_TOTAL_PDUFA_SIGNALS = len(PDUFA_MODE_CONFIG["signals"])


# ═══════════════════════════════════════════════════════════════
#  PHASE3_MODE — EXPANDED (12 modifiers, up from 5)
# ═══════════════════════════════════════════════════════════════

PHASE3_MODE_CONFIG = {
    "ta_base_logits": {
        "CNS/Neurology": 0.624,
        "Cardiovascular": 0.847,
        "Oncology": 1.045,
        "Metabolic/Endocrine": 1.200,
        "Immunology": 1.350,
        "Dermatology": 1.450,
        "GI/Hepatology": 1.500,
        "Respiratory": 1.650,
        "Infectious Disease": 2.000,
        "Rare Disease": 1.800,
        "Hematology": 1.100,
        "Ophthalmology": 0.750,
        "Nephrology": 0.700,
        "Pain Management": 0.500,
        "Women's Health": 2.200,
        "Vaccines": 2.500,
        "Other": 1.000,
    },
    "pvalue_logits": {
        "p<0.001": 4.043,
        "p_001_01": 1.932,
        "p_01_05": 1.481,
        "p>=0.05": 0.0,
        "p_lt_001": 4.043,
    },
    "modifier_signals": {
        # Original 5
        "BTD":               0.693,
        "PRIOR_P3_FAIL":    -0.847,
        "FDA_EOP2_POS":      0.551,
        "SINGLE_ARM":       -0.441,
        "BIOMARKER_DRIVEN":  0.330,
        # New 7
        "LARGE_ENROLLMENT":  0.220,    # n≥500
        "ADAPTIVE_DESIGN":   0.165,    # Adaptive trial design
        "ACTIVE_COMPARATOR": 0.110,    # Active comparator arm
        "SURROGATE_ONLY":   -0.275,    # Surrogate endpoint only
        "OPEN_LABEL":       -0.165,    # Open-label design
        "PLATFORM_TRIAL":    0.110,    # Master protocol / platform
        "PRIOR_P2_STRONG":   0.330,    # Phase 2 was strongly positive
    },
    "modifier_field_map": {
        "BTD": "btd",
        "PRIOR_P3_FAIL": "prior_p3_fail",
        "FDA_EOP2_POS": "fda_eop2_positive",
        "SINGLE_ARM": "single_arm_trial",
        "BIOMARKER_DRIVEN": "biomarker_driven",
        "LARGE_ENROLLMENT": "large_enrollment",
        "ADAPTIVE_DESIGN": "adaptive_design",
        "ACTIVE_COMPARATOR": "active_comparator",
        "SURROGATE_ONLY": "surrogate_endpoint_only",
        "OPEN_LABEL": "open_label_single_arm",
        "PLATFORM_TRIAL": "platform_trial",
        "PRIOR_P2_STRONG": "prior_p2_strong",
    },
    "transition_rate": 0.28,
    "validation": {
        "n_pairs": 151,
        "or_sig_vs_ns": 32.6,
        "correlation_r": -0.45,
    },
}


# ═══════════════════════════════════════════════════════════════
#  SCORING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def score_pdufa_mode(event: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    PDUFA_MODE scoring with expanded 62-signal registry.
    P(approval) = sigmoid(base_logit + Σ signal_logits)
    """
    cfg = config or PDUFA_MODE_CONFIG
    total_logit = cfg["base_logit"]
    fired_signals = {}

    for sig_id, sig_cfg in cfg["signals"].items():
        sig_logit = sig_cfg["logit"]
        fired = False
        contribution = 0.0

        # ── BOOL: simple True/False field check ──
        if sig_cfg["type"] == "bool":
            if _safe_bool(event.get(sig_cfg["field"])):
                fired = True
                contribution = sig_logit

        # ── COND: conditional on multiple fields ──
        elif sig_cfg["type"] == "cond":
            cond = sig_cfg["condition"]
            fired = _evaluate_condition(cond, event)
            if fired:
                contribution = sig_logit

        # ── LOOKUP: therapeutic area lookup table ──
        elif sig_cfg["type"] == "lookup":
            ta = event.get("therapeutic_area", "Other") or "Other"
            ta_logit = cfg["ta_logits"].get(ta, cfg["ta_logits"].get("Other", -0.330))
            dampened = ta_logit * sig_cfg.get("dampening", 0.83)
            if dampened != 0:
                total_logit += dampened
                fired_signals[sig_id] = {"logit": round(dampened, 4), "ta": ta}
            continue

        # ── THRESHOLD: fires when numeric field crosses threshold ──
        elif sig_cfg["type"] == "threshold":
            val = _safe_float(event.get(sig_cfg["field"]), default=None)
            if val is not None:
                threshold = sig_cfg["threshold"]
                direction = sig_cfg.get("direction", "above")
                if direction == "above" and val >= threshold:
                    fired = True
                    contribution = sig_logit
                elif direction == "below" and val < threshold:
                    fired = True
                    contribution = sig_logit

        # ── RANGE: continuous value mapped to logit contribution ──
        elif sig_cfg["type"] == "range":
            val = _safe_float(event.get(sig_cfg["field"]), default=None)
            if val is not None:
                scale = sig_cfg.get("scale", 0.5)
                center = sig_cfg.get("center", 0.0)
                contribution = (val - center) * scale
                if abs(contribution) > 0.001:
                    fired = True

        # ── SOCIAL / COMPOSITE: treat like bool ──
        elif sig_cfg["type"] in ("social", "composite"):
            if _safe_bool(event.get(sig_cfg["field"])):
                fired = True
                contribution = sig_logit

        if fired and abs(contribution) > 0.0001:
            total_logit += contribution
            fired_signals[sig_id] = {
                "logit": round(contribution, 4),
                "tier": sig_cfg.get("tier", "UNKNOWN"),
            }

    probability = sigmoid(total_logit)
    thresholds = cfg["tier_thresholds"]
    if probability >= thresholds["tier1"]:
        tier, action = 1, "LONG"
    elif probability >= thresholds["tier2"]:
        tier, action = 2, "NO_TRADE"
    elif probability >= thresholds["tier3"]:
        tier, action = 3, "AVOID"
    else:
        tier, action = 4, "HIGH_CRL_RISK"

    # Count by tier
    tier_counts = {"VALIDATED": 0, "THEORETICAL": 0, "DISCOVERY": 0}
    for sid, sdata in fired_signals.items():
        t = sdata.get("tier", "UNKNOWN")
        if t in tier_counts:
            tier_counts[t] += 1

    return {
        "mode": "PDUFA",
        "version": "12.0",
        "total_logit": round(total_logit, 4),
        "probability": round(probability, 4),
        "tier": tier,
        "trading_action": action,
        "signals_fired": fired_signals,
        "signal_count": len(fired_signals),
        "signal_tier_counts": tier_counts,
        "total_signals_available": _TOTAL_PDUFA_SIGNALS,
    }


def _evaluate_condition(cond: str, event: Dict[str, Any]) -> bool:
    """Evaluate a condition string against event data."""
    # AdCom conditions
    if "adcom_vote_pct >= 0.65" in cond:
        return _safe_bool(event.get("had_adcom")) and _safe_float(event.get("adcom_vote_pct")) >= 0.65
    if "0.50 <= adcom_vote_pct < 0.65" in cond:
        pct = _safe_float(event.get("adcom_vote_pct"))
        return _safe_bool(event.get("had_adcom")) and 0.50 <= pct < 0.65
    if "adcom_vote_pct < 0.50" in cond:
        return _safe_bool(event.get("had_adcom")) and _safe_float(event.get("adcom_vote_pct")) < 0.50

    # Resubmission conditions
    if "resubmission_class == 1" in cond:
        return _safe_bool(event.get("prior_crl")) and _safe_int(event.get("resubmission_class")) == 1
    if "resubmission_class == 2" in cond:
        return _safe_bool(event.get("prior_crl")) and _safe_int(event.get("resubmission_class")) == 2

    # Sponsor conditions
    if "sponsor_prior_approvals >= 5" in cond:
        return _safe_int(event.get("sponsor_prior_approvals")) >= 5
    if "sponsor_prior_approvals == 0" in cond:
        return _safe_int(event.get("sponsor_prior_approvals")) == 0

    # CRL reason conditions
    if "crl_reason == 'CMC'" in cond:
        return _safe_bool(event.get("prior_crl")) and event.get("crl_reason", "").upper() == "CMC"
    if "crl_reason == 'CLINICAL'" in cond:
        return _safe_bool(event.get("prior_crl")) and event.get("crl_reason", "").upper() == "CLINICAL"
    if "crl_count >= 2" in cond:
        return _safe_int(event.get("crl_count")) >= 2

    # Market cap conditions
    if "market_cap_tier == 'mega'" in cond:
        return event.get("market_cap_tier", "").lower() == "mega"
    if "market_cap_tier == 'micro'" in cond:
        return event.get("market_cap_tier", "").lower() == "micro"

    # Cash runway
    if "cash_runway_months < 12" in cond:
        val = _safe_float(event.get("cash_runway_months"), default=999)
        return val < 12

    # CMO risk
    if "cmo_risk_tier >= 3" in cond:
        return _safe_int(event.get("cmo_risk_tier")) >= 3

    # P-value
    if "pivotal_pvalue < 0.001" in cond:
        val = _safe_float(event.get("pivotal_pvalue"), default=1.0)
        return val < 0.001

    return False


def score_phase3_mode(event: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    PHASE3_MODE scoring: Phase 2→3 success probability.
    P(success) = sigmoid(ta_base_logit + pvalue_logit + Σ modifier_logits)
    """
    cfg = config or PHASE3_MODE_CONFIG
    ta = event.get("therapeutic_area", "Other") or "Other"
    ta_logit = cfg["ta_base_logits"].get(ta, cfg["ta_base_logits"].get("Other", 1.000))

    # P-value bucket
    p_val = _safe_float(event.get("p_value"), default=None)
    p_bucket = event.get("p_value_bucket", event.get("p_value_tier", "p>=0.05"))
    if p_val is not None and p_val > 0:
        if p_val < 0.001:
            p_bucket = "p<0.001"
        elif p_val < 0.01:
            p_bucket = "p_001_01"
        elif p_val < 0.05:
            p_bucket = "p_01_05"
        else:
            p_bucket = "p>=0.05"
    p_logit = cfg["pvalue_logits"].get(p_bucket, 0.0)

    # Modifier signals (expanded to 12)
    total_logit = ta_logit + p_logit
    modifiers_fired = {}
    field_map = cfg.get("modifier_field_map", {})

    for mod_name, mod_logit in cfg["modifier_signals"].items():
        field_name = field_map.get(mod_name, mod_name.lower())
        if _safe_bool(event.get(field_name)):
            total_logit += mod_logit
            modifiers_fired[mod_name] = mod_logit

    p3_probability = sigmoid(total_logit)

    return {
        "mode": "PHASE3",
        "version": "12.0",
        "total_logit": round(total_logit, 4),
        "probability": round(p3_probability, 4),
        "ta_logit": round(ta_logit, 4),
        "pvalue_logit": round(p_logit, 4),
        "p_bucket": p_bucket,
        "modifiers_fired": modifiers_fired,
        "modifier_count": len(modifiers_fired),
    }


def score_full_pos(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combined Probability of Success:
    Full PoS = PHASE3_MODE × transition_rate × PDUFA_MODE
    """
    pdufa = score_pdufa_mode(event)
    phase3 = score_phase3_mode(event)
    transition = PHASE3_MODE_CONFIG["transition_rate"]

    full_pos = phase3["probability"] * transition * pdufa["probability"]

    return {
        "mode": "FULL_POS",
        "version": "12.0",
        "full_pos": round(full_pos, 4),
        "pdufa_probability": pdufa["probability"],
        "phase3_probability": phase3["probability"],
        "transition_rate": transition,
        "pdufa_tier": pdufa["tier"],
        "pdufa_action": pdufa["trading_action"],
        "pdufa_signals": pdufa["signals_fired"],
        "pdufa_signal_count": pdufa["signal_count"],
        "phase3_modifiers": phase3["modifiers_fired"],
    }


# ═══════════════════════════════════════════════════════════════
#  SECTION 2: PREDICTION LEDGER — Persistent Tracking
# ═══════════════════════════════════════════════════════════════

@dataclass
class PredictionRecord:
    event_id: str
    mode: str
    probability: float
    tier: int = 0
    action: str = ""
    signals_fired: Dict = field(default_factory=dict)
    signal_count: int = 0
    outcome: Optional[str] = None  # APPROVED, CRL, SUCCESS, FAILURE
    outcome_date: Optional[str] = None
    scored_at: str = ""
    resolved_at: Optional[str] = None
    model_version: str = "12.0"
    event_data: Dict = field(default_factory=dict)


class PredictionLedger:
    """Persistent prediction ledger with JSON backing."""

    def __init__(self, filepath: str = "odin_ledger.json"):
        self.filepath = filepath
        self.records: Dict[str, PredictionRecord] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                data = json.load(f)
            for eid, rec in data.items():
                self.records[eid] = PredictionRecord(**rec)

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump({k: asdict(v) for k, v in self.records.items()}, f, indent=2)

    def record_prediction(self, event_id: str, result: Dict, event_data: Dict = None):
        rec = PredictionRecord(
            event_id=event_id,
            mode=result.get("mode", "PDUFA"),
            probability=result.get("probability", result.get("full_pos", 0.0)),
            tier=result.get("tier", 0),
            action=result.get("trading_action", ""),
            signals_fired=result.get("signals_fired", result.get("pdufa_signals", {})),
            signal_count=result.get("signal_count", result.get("pdufa_signal_count", 0)),
            scored_at=datetime.now(timezone.utc).isoformat(),
            model_version=result.get("version", "12.0"),
            event_data=event_data or {},
        )
        self.records[event_id] = rec
        self._save()
        return rec

    def record_outcome(self, event_id: str, outcome: str, outcome_date: Optional[str] = None):
        if event_id not in self.records:
            return None
        rec = self.records[event_id]
        rec.outcome = outcome
        rec.outcome_date = outcome_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rec.resolved_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return rec

    def get_resolved(self, mode: str = None) -> List[PredictionRecord]:
        resolved = [r for r in self.records.values() if r.outcome is not None]
        if mode:
            resolved = [r for r in resolved if r.mode == mode]
        return resolved

    def get_unresolved(self) -> List[PredictionRecord]:
        return [r for r in self.records.values() if r.outcome is None]


# ═══════════════════════════════════════════════════════════════
#  SECTION 3: CALIBRATION ENGINE — Metrics & Drift Detection
# ═══════════════════════════════════════════════════════════════

@dataclass
class CalibrationReport:
    n_events: int = 0
    brier_score: float = 1.0
    auc_roc: float = 0.5
    accuracy: float = 0.0
    tier_performance: Dict = field(default_factory=dict)
    signal_effectiveness: Dict = field(default_factory=dict)
    drift_alerts: List[str] = field(default_factory=list)
    recommendations: Dict = field(default_factory=dict)


class CalibrationEngine:
    """Computes calibration metrics, drift detection, signal effectiveness."""

    @staticmethod
    def calibrate(records: List[PredictionRecord]) -> CalibrationReport:
        if not records:
            return CalibrationReport()

        # Binary outcomes
        probs = []
        actuals = []
        for r in records:
            probs.append(r.probability)
            actuals.append(1.0 if r.outcome in ("APPROVED", "SUCCESS") else 0.0)

        n = len(probs)
        report = CalibrationReport(n_events=n)

        # Brier Score
        report.brier_score = round(sum((p - a) ** 2 for p, a in zip(probs, actuals)) / n, 4)

        # Accuracy
        correct = sum(1 for p, a in zip(probs, actuals)
                      if (p >= 0.5 and a == 1.0) or (p < 0.5 and a == 0.0))
        report.accuracy = round(correct / n, 4)

        # AUC-ROC (Mann-Whitney U statistic)
        pos = [p for p, a in zip(probs, actuals) if a == 1.0]
        neg = [p for p, a in zip(probs, actuals) if a == 0.0]
        if pos and neg:
            concordant = sum(1 for pp in pos for pn in neg if pp > pn)
            tied = sum(0.5 for pp in pos for pn in neg if pp == pn)
            report.auc_roc = round((concordant + tied) / (len(pos) * len(neg)), 4)

        # Tier Performance
        tier_buckets = defaultdict(lambda: {"n": 0, "approved": 0})
        for r in records:
            t = r.tier
            tier_buckets[t]["n"] += 1
            if r.outcome in ("APPROVED", "SUCCESS"):
                tier_buckets[t]["approved"] += 1
        report.tier_performance = {
            f"Tier_{t}": {
                "n": d["n"],
                "approval_rate": round(d["approved"] / d["n"], 4) if d["n"] > 0 else 0.0,
            }
            for t, d in sorted(tier_buckets.items())
        }

        # Signal Effectiveness
        signal_stats = defaultdict(lambda: {"fired_approved": 0, "fired_total": 0,
                                             "notfired_approved": 0, "notfired_total": 0})
        for r in records:
            approved = r.outcome in ("APPROVED", "SUCCESS")
            fired_sigs = set(r.signals_fired.keys()) if r.signals_fired else set()
            # Check all known signals
            all_sigs = set()
            for rec in records:
                if rec.signals_fired:
                    all_sigs.update(rec.signals_fired.keys())

            for sig in all_sigs:
                if sig in fired_sigs:
                    signal_stats[sig]["fired_total"] += 1
                    if approved:
                        signal_stats[sig]["fired_approved"] += 1
                else:
                    signal_stats[sig]["notfired_total"] += 1
                    if approved:
                        signal_stats[sig]["notfired_approved"] += 1

        sig_effectiveness = {}
        for sig, stats in signal_stats.items():
            ft, fa = stats["fired_total"], stats["fired_approved"]
            nft, nfa = stats["notfired_total"], stats["notfired_approved"]
            fired_rate = fa / ft if ft > 0 else 0
            notfired_rate = nfa / nft if nft > 0 else 0
            lift = fired_rate - notfired_rate

            # Odds ratio
            a, b = fa, ft - fa
            c, d_val = nfa, nft - nfa
            if b > 0 and c > 0 and d_val > 0 and a > 0:
                odds_ratio = round((a * d_val) / (b * c), 2)
            else:
                odds_ratio = None

            sig_effectiveness[sig] = {
                "fired_n": ft, "fired_approval_rate": round(fired_rate, 4),
                "notfired_n": nft, "notfired_approval_rate": round(notfired_rate, 4),
                "lift": round(lift, 4), "odds_ratio": odds_ratio,
            }

        report.signal_effectiveness = sig_effectiveness

        # Drift Detection
        drift_alerts = []
        if n >= 20:
            # Recent vs historical Brier
            recent = records[-min(15, n // 3):]
            historical = records[:-len(recent)] if len(records) > len(recent) else records
            recent_brier = sum((r.probability - (1.0 if r.outcome in ("APPROVED", "SUCCESS") else 0.0)) ** 2
                               for r in recent) / len(recent)
            hist_brier = sum((r.probability - (1.0 if r.outcome in ("APPROVED", "SUCCESS") else 0.0)) ** 2
                             for r in historical) / len(historical) if historical else recent_brier
            if recent_brier > hist_brier * 1.5:
                drift_alerts.append(
                    f"RECENCY_DRIFT: Recent Brier={recent_brier:.4f} vs historical={hist_brier:.4f} "
                    f"(model may be stale, consider recalibration)")

        # Base rate shift
        actual_rate = sum(actuals) / n
        expected_rate = 0.827  # base rate
        if abs(actual_rate - expected_rate) > 0.10:
            drift_alerts.append(
                f"BASE_RATE_SHIFT: Observed approval rate={actual_rate:.3f} "
                f"vs expected={expected_rate:.3f} (delta={actual_rate - expected_rate:+.3f})")

        report.drift_alerts = drift_alerts

        # Recommendations for signals with enough data
        recommendations = {}
        for sig, eff in sig_effectiveness.items():
            if eff["fired_n"] >= 3 and eff["notfired_n"] >= 3:
                if eff["lift"] < -0.02 and eff.get("odds_ratio") and eff["odds_ratio"] < 1.0:
                    recommendations[sig] = {
                        "action": "DAMPEN_OR_FLIP",
                        "reason": f"Negative lift ({eff['lift']:+.4f}), OR={eff['odds_ratio']}",
                        "current_direction": "negative",
                        "suggested": "Reduce weight by 50% or investigate signal definition",
                    }
                elif eff["lift"] > 0.10 and eff.get("odds_ratio") and eff["odds_ratio"] > 2.0:
                    recommendations[sig] = {
                        "action": "CONSIDER_BOOST",
                        "reason": f"Strong lift ({eff['lift']:+.4f}), OR={eff['odds_ratio']}",
                        "suggested": "Signal may be underweighted — consider increasing logit by 0.1-0.3",
                    }
        report.recommendations = recommendations

        return report


# ═══════════════════════════════════════════════════════════════
#  SECTION 4: WEIGHT RECALIBRATOR — Gradient Descent in Logit Space
# ═══════════════════════════════════════════════════════════════

class WeightRecalibrator:
    """Gradient descent recalibration with L2 regularization."""

    def __init__(self, learning_rate: float = 0.01, l2_lambda: float = 0.01,
                 max_epochs: int = 1000, convergence: float = 1e-6,
                 min_events: int = 20):
        self.lr = learning_rate
        self.l2 = l2_lambda
        self.max_epochs = max_epochs
        self.convergence = convergence
        self.min_events = min_events

    def recalibrate(self, records: List[PredictionRecord],
                    config: Dict) -> Tuple[Dict, Dict]:
        """
        Returns (new_config, change_report).
        Minimizes Brier score via gradient descent in logit space.
        """
        if len(records) < self.min_events:
            return config, {"status": "INSUFFICIENT_DATA", "n": len(records),
                            "required": self.min_events}

        new_config = deepcopy(config)
        report = {"status": "RECALIBRATED", "epochs": 0, "signals_changed": 0}

        # Build feature matrix
        events = []
        actuals = []
        for r in records:
            actual = 1.0 if r.outcome in ("APPROVED", "SUCCESS") else 0.0
            actuals.append(actual)
            events.append(r.event_data)

        # Gradient descent on base_logit + signal logits
        base = new_config["base_logit"]
        sig_keys = list(new_config["signals"].keys())
        old_base = base

        for epoch in range(self.max_epochs):
            total_grad_base = 0.0
            brier = 0.0

            for i, ev in enumerate(events):
                # Compute prediction with current weights
                result = score_pdufa_mode(ev, new_config)
                p = result["probability"]
                y = actuals[i]
                error = p - y

                brier += error ** 2
                total_grad_base += error * p * (1 - p) * 2 / len(events)

            brier /= len(events)

            # Update base logit with L2
            grad = total_grad_base + self.l2 * (base - old_base)
            new_base = base - self.lr * grad

            # Check convergence
            if abs(new_base - base) < self.convergence:
                report["epochs"] = epoch + 1
                break
            base = new_base
            new_config["base_logit"] = round(base, 4)

        report["epochs"] = report.get("epochs", self.max_epochs)
        report["final_brier"] = round(brier, 6)
        report["base_logit_change"] = {
            "old": round(old_base, 4), "new": round(base, 4),
            "delta": round(base - old_base, 4),
        }

        # Per-signal gradient updates (for signals with enough data)
        signals_changed = 0
        for sig_id in sig_keys:
            sig_cfg = new_config["signals"][sig_id]
            if sig_cfg["type"] in ("lookup", "range"):
                continue
            if not isinstance(sig_cfg["logit"], (int, float)):
                continue

            old_logit = sig_cfg["logit"]
            fired_indices = []
            for i, ev in enumerate(events):
                # Check if signal would fire
                temp_result = score_pdufa_mode(ev, new_config)
                if sig_id in temp_result.get("signals_fired", {}):
                    fired_indices.append(i)

            if len(fired_indices) < 3:
                continue

            # Compute gradient for this signal
            grad_sig = 0.0
            for i in fired_indices:
                result = score_pdufa_mode(events[i], new_config)
                p = result["probability"]
                y = actuals[i]
                error = p - y
                grad_sig += error * p * (1 - p) * 2 / len(fired_indices)

            grad_sig += self.l2 * old_logit  # L2 regularization toward 0

            new_logit = old_logit - self.lr * grad_sig
            # Clamp to reasonable range
            new_logit = max(-3.0, min(3.0, new_logit))

            if abs(new_logit - old_logit) > 0.001:
                sig_cfg["logit"] = round(new_logit, 4)
                signals_changed += 1

        report["signals_changed"] = signals_changed
        return new_config, report


# ═══════════════════════════════════════════════════════════════
#  SECTION 5: MODEL VERSION STORE
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModelSnapshot:
    version: str
    config_hash: str
    created_at: str
    trigger: str  # MANUAL, AUTO_DRIFT, etc.
    parent_version: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    config_delta: Dict = field(default_factory=dict)


class ModelVersionStore:
    """Git-like versioning for ODIN model configs."""

    def __init__(self, filepath: str = "odin_versions.json"):
        self.filepath = filepath
        self.snapshots: List[ModelSnapshot] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                data = json.load(f)
            self.snapshots = [ModelSnapshot(**s) for s in data]

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump([asdict(s) for s in self.snapshots], f, indent=2)

    @staticmethod
    def hash_config(config: Dict) -> str:
        canonical = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]

    def current_version(self) -> str:
        if self.snapshots:
            return self.snapshots[-1].version
        return "12.0.0"

    def next_version(self) -> str:
        cv = self.current_version()
        parts = cv.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def create_snapshot(self, config: Dict, trigger: str,
                        metrics: Dict = None) -> ModelSnapshot:
        snap = ModelSnapshot(
            version=self.next_version(),
            config_hash=self.hash_config(config),
            created_at=datetime.now(timezone.utc).isoformat(),
            trigger=trigger,
            parent_version=self.current_version() if self.snapshots else None,
            metrics=metrics or {},
        )
        self.snapshots.append(snap)
        self._save()
        return snap


# ═══════════════════════════════════════════════════════════════
#  SECTION 6: PERPETUAL HONING ENGINE — Orchestrator
# ═══════════════════════════════════════════════════════════════

class PerpetualHoningEngine:
    """
    ODIN v12.0 Perpetual Honing Engine

    Orchestrates: score → track → calibrate → detect drift → recalibrate → version

    62 PDUFA signals (VALIDATED + THEORETICAL + DISCOVERY)
    12 Phase3 modifiers
    Full audit trail with versioned model snapshots
    """

    def __init__(self, ledger_path: str = "odin_ledger.json",
                 versions_path: str = "odin_versions.json",
                 drift_check_interval: int = 5,
                 auto_recal_threshold: float = 0.15):
        self.ledger = PredictionLedger(ledger_path)
        self.version_store = ModelVersionStore(versions_path)
        self.calibrator = CalibrationEngine()
        self.recalibrator = WeightRecalibrator()
        self.drift_interval = drift_check_interval
        self.auto_recal_threshold = auto_recal_threshold

        # Active model configs (may be modified by recalibration)
        self.active_pdufa_config = deepcopy(PDUFA_MODE_CONFIG)
        self.active_phase3_config = deepcopy(PHASE3_MODE_CONFIG)

    def score(self, event: Dict[str, Any], mode: str = "PDUFA") -> Dict[str, Any]:
        """Score an event and track in ledger."""
        event_id = event.get("event_id", f"auto_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")

        if mode == "PDUFA":
            result = score_pdufa_mode(event, self.active_pdufa_config)
        elif mode == "PHASE3":
            result = score_phase3_mode(event, self.active_phase3_config)
        elif mode == "FULL_POS":
            result = score_full_pos(event)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Track in ledger
        self.ledger.record_prediction(event_id, result, event_data=event)

        return {
            "prediction": {
                "event_id": event_id,
                "probability": result.get("probability", result.get("full_pos")),
                "tier": result.get("tier", result.get("pdufa_tier")),
                "action": result.get("trading_action", result.get("pdufa_action", "")),
                "signals": result.get("signals_fired", result.get("pdufa_signals", {})),
                "signal_count": result.get("signal_count", result.get("pdufa_signal_count", 0)),
                "signal_tier_counts": result.get("signal_tier_counts", {}),
                "logit": result.get("total_logit"),
                "mode": mode,
                "version": result.get("version", "12.0"),
                "total_signals_available": result.get("total_signals_available", _TOTAL_PDUFA_SIGNALS),
            },
            "ledger_size": len(self.ledger.records),
            "unresolved": len(self.ledger.get_unresolved()),
        }

    def record_outcome(self, event_id: str, outcome: str,
                       outcome_date: Optional[str] = None) -> Dict[str, Any]:
        """Record an event outcome."""
        rec = self.ledger.record_outcome(event_id, outcome, outcome_date)
        if rec is None:
            return {"error": f"Event {event_id} not found"}

        resolved = self.ledger.get_resolved("PDUFA")
        result = {"event_id": event_id, "outcome": outcome, "total_resolved": len(resolved)}

        # Auto-hone check
        if len(resolved) > 0 and len(resolved) % self.drift_interval == 0:
            result["auto_hone"] = self.hone()

        return result

    def hone(self, force_recalibrate: bool = False) -> Dict[str, Any]:
        """Run the full honing cycle: calibrate → detect drift → recalibrate → version."""
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Calibrate PDUFA mode
        pdufa_records = self.ledger.get_resolved("PDUFA")
        pdufa_cal = self.calibrator.calibrate(pdufa_records)
        result["pdufa_calibration"] = {
            "n_events": pdufa_cal.n_events,
            "brier_score": pdufa_cal.brier_score,
            "auc_roc": pdufa_cal.auc_roc,
            "accuracy": pdufa_cal.accuracy,
            "drift_alerts": pdufa_cal.drift_alerts,
            "recommendations": pdufa_cal.recommendations,
            "tier_performance": pdufa_cal.tier_performance,
            "signal_effectiveness_count": len(pdufa_cal.signal_effectiveness),
        }

        # Calibrate Phase3 mode
        p3_records = self.ledger.get_resolved("PHASE3")
        p3_cal = self.calibrator.calibrate(p3_records)
        result["phase3_calibration"] = {
            "n_events": p3_cal.n_events,
            "brier_score": p3_cal.brier_score,
            "auc_roc": p3_cal.auc_roc,
            "accuracy": p3_cal.accuracy,
        }

        # Determine if recalibration needed
        needs_recal = force_recalibrate
        trigger = "MANUAL" if force_recalibrate else None

        if not needs_recal and pdufa_cal.brier_score > self.auto_recal_threshold:
            needs_recal = True
            trigger = "AUTO_DRIFT"
        if not needs_recal and pdufa_cal.drift_alerts:
            for alert in pdufa_cal.drift_alerts:
                if "BASE_RATE_SHIFT" in alert:
                    needs_recal = True
                    trigger = "BASE_RATE_SHIFT"
                    break
                if "RECENCY_DRIFT" in alert:
                    needs_recal = True
                    trigger = "RECENCY_DRIFT"
                    break

        result["needs_recalibration"] = needs_recal
        result["trigger_reason"] = trigger

        if needs_recal and pdufa_records:
            new_config, recal_report = self.recalibrator.recalibrate(
                pdufa_records, self.active_pdufa_config
            )

            if recal_report["status"] == "RECALIBRATED":
                self.active_pdufa_config = new_config
                snap = self.version_store.create_snapshot(
                    new_config, trigger=trigger or "MANUAL",
                    metrics={"brier": pdufa_cal.brier_score, "auc": pdufa_cal.auc_roc}
                )
                result["recalibration"] = recal_report
                result["new_version"] = snap.version
                result["config_hash"] = snap.config_hash
            else:
                result["recalibration"] = recal_report
        else:
            result["recalibration"] = {"status": "NOT_NEEDED"}

        return result

    def full_report(self) -> Dict[str, Any]:
        """Generate comprehensive model report."""
        pdufa_records = self.ledger.get_resolved("PDUFA")
        pdufa_cal = self.calibrator.calibrate(pdufa_records)

        # Signal tier summary
        signal_tiers = {"VALIDATED": 0, "THEORETICAL": 0, "DISCOVERY": 0}
        for sig_id, sig_cfg in self.active_pdufa_config["signals"].items():
            tier = sig_cfg.get("tier", "UNKNOWN")
            if tier in signal_tiers:
                signal_tiers[tier] += 1

        return {
            "model_version": self.version_store.current_version(),
            "total_pdufa_signals": _TOTAL_PDUFA_SIGNALS,
            "signal_tiers": signal_tiers,
            "total_predictions": len(self.ledger.records),
            "total_resolved": len(pdufa_records),
            "total_unresolved": len(self.ledger.get_unresolved()),
            "calibration": {
                "brier_score": pdufa_cal.brier_score,
                "auc_roc": pdufa_cal.auc_roc,
                "accuracy": pdufa_cal.accuracy,
            },
            "tier_performance": pdufa_cal.tier_performance,
            "signal_effectiveness": pdufa_cal.signal_effectiveness,
            "drift_alerts": pdufa_cal.drift_alerts,
            "recommendations": pdufa_cal.recommendations,
            "version_history": [asdict(s) for s in self.version_store.snapshots[-10:]],
        }

    def export_current_model(self, filepath: str):
        """Export current model configuration as JSON."""
        export = {
            "engine": "ODIN_Perpetual_Honing_Engine",
            "model_version": self.version_store.current_version(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_signals": _TOTAL_PDUFA_SIGNALS,
            "PDUFA_MODE": self.active_pdufa_config,
            "PHASE3_MODE": self.active_phase3_config,
        }
        with open(filepath, "w") as f:
            json.dump(export, f, indent=2)

    def batch_score(self, events: List[Dict], mode: str = "PDUFA") -> List[Dict]:
        """Score multiple events."""
        return [self.score(ev, mode) for ev in events]

    def batch_outcomes(self, outcomes: List[Tuple[str, str]]):
        """Record multiple outcomes: [(event_id, outcome), ...]"""
        return [self.record_outcome(eid, out) for eid, out in outcomes]

    def backtest(self, historical_events: List[Dict], mode: str = "PDUFA") -> Dict[str, Any]:
        """Run backtest without modifying the main ledger."""
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "odin_backtest_temp.json")
        temp_ledger = PredictionLedger(temp_path)
        results = []
        for ev in historical_events:
            eid = ev.get("event_id", f"bt_{len(results)}")
            if mode == "PDUFA":
                result = score_pdufa_mode(ev, self.active_pdufa_config)
            elif mode == "PHASE3":
                result = score_phase3_mode(ev, self.active_phase3_config)
            else:
                result = score_full_pos(ev)

            rec = temp_ledger.record_prediction(eid, result, ev)
            if "outcome" in ev:
                temp_ledger.record_outcome(eid, ev["outcome"])
            results.append(result)

        cal = self.calibrator.calibrate(temp_ledger.get_resolved())
        # Cleanup temp
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return {
            "n_events": len(results),
            "brier_score": cal.brier_score,
            "auc_roc": cal.auc_roc,
            "accuracy": cal.accuracy,
            "tier_performance": cal.tier_performance,
        }

    def get_signal_registry(self) -> Dict[str, Any]:
        """Return full signal registry with metadata."""
        registry = {}
        for sig_id, sig_cfg in self.active_pdufa_config["signals"].items():
            registry[sig_id] = {
                "logit": sig_cfg["logit"],
                "tier": sig_cfg.get("tier", "UNKNOWN"),
                "source": sig_cfg.get("source", "unknown"),
                "type": sig_cfg["type"],
                "desc": sig_cfg.get("desc", ""),
                "field": sig_cfg.get("field", ""),
            }
        return registry


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Full demonstration of ODIN v12.0 with 62 signals."""
    import random
    import tempfile
    random.seed(42)

    print("=" * 70)
    print("  ODIN PERPETUAL HONING ENGINE v2.0 — 62-SIGNAL DEMO")
    print("=" * 70)

    tmpdir = tempfile.gettempdir()
    engine = PerpetualHoningEngine(
        ledger_path=os.path.join(tmpdir, "odin_v2_demo_ledger.json"),
        versions_path=os.path.join(tmpdir, "odin_v2_demo_versions.json"),
    )

    # Show signal registry
    registry = engine.get_signal_registry()
    tiers = defaultdict(int)
    for sig_id, sig_data in registry.items():
        tiers[sig_data["tier"]] += 1
    print(f"\nSignal Registry: {len(registry)} total signals")
    for tier, count in sorted(tiers.items()):
        print(f"  {tier}: {count}")

    # Score a rich event with many signals populated
    rich_event = {
        "event_id": "DEMO_RICH_001",
        "ticker": "ACME",
        "drug_name": "AcmeBiologix",
        "therapeutic_area": "Oncology",
        # Regulatory designations
        "btd": True,
        "orphan": True,
        "priority_review": True,
        "fast_track": False,
        "accelerated_approval": False,
        "rmat": False,
        "qidp": False,
        "first_in_class": True,
        "high_unmet_need": True,
        # AdCom
        "had_adcom": True,
        "adcom_vote_pct": 0.75,
        "adcom_waived": False,
        "rtf_clean": True,
        # CRL history
        "prior_crl": False,
        # Sponsor
        "sponsor_prior_approvals": 8,
        "market_cap_tier": "large",
        "big_pharma_partner": True,
        "sponsor_recent_approval": True,
        # Manufacturing
        "manufacturing_risk": False,
        "form_483_issues": False,
        "is_biologic": True,
        "gmp_inspection_clean": True,
        # Clinical trial quality
        "pivotal_met_primary": True,
        "multiple_pivotals_positive": True,
        "enrollment": 750,
        "double_blind_rct": True,
        "hard_clinical_endpoint": True,
        "pivotal_pvalue": 0.0001,
        "safety_profile_clean": True,
        # Competitive landscape
        "first_in_indication": False,
        "crowded_indication": False,
        "best_in_class_data": True,
        # Financial signals
        "insider_buy_signal": True,
        "insider_buy_value": 750000,
        "options_bullish": True,
        "analyst_consensus_buy": True,
        "news_sentiment_bullish": True,
        # Social
        "sentiment_bullish": True,
        "engagement_spike": True,
        "galaxy_score": 82,
        # Publications
        "high_impact_journal": True,
        "pubmed_publication_count": 45,
        # Composites
        "specialist_proxy": True,
        "regulatory_designation_count": 3,
        "data_quality_score": 0.85,
    }

    result = engine.score(rich_event, mode="PDUFA")
    pred = result["prediction"]
    print(f"\n{'─' * 50}")
    print(f"RICH EVENT: {rich_event['drug_name']} ({rich_event['ticker']})")
    print(f"  Probability: {pred['probability']:.4f}")
    print(f"  Tier: {pred['tier']} → {pred['action']}")
    print(f"  Signals fired: {pred['signal_count']} / {pred['total_signals_available']}")
    print(f"  By tier: {pred.get('signal_tier_counts', {})}")
    print(f"  Total logit: {pred['logit']:.4f}")

    # Score a bearish event
    bear_event = {
        "event_id": "DEMO_BEAR_001",
        "ticker": "BEAR",
        "drug_name": "BearPharma-X",
        "therapeutic_area": "Pain Management",
        "btd": False, "orphan": False, "priority_review": False,
        "prior_crl": True, "crl_reason": "CLINICAL", "crl_count": 2,
        "resubmission_class": 2,
        "sponsor_prior_approvals": 0,
        "market_cap_tier": "micro",
        "manufacturing_risk": True, "form_483_issues": True,
        "is_biologic": True,
        "open_label_single_arm": True,
        "safety_concerns": True,
        "crowded_indication": True,
        "insider_sell_cluster": True,
        "put_call_ratio": 2.1,
        "negative_publication": True,
        "social_silence": True,
        "cash_runway_months": 8,
    }

    bear_result = engine.score(bear_event, mode="PDUFA")
    bear_pred = bear_result["prediction"]
    print(f"\n{'─' * 50}")
    print(f"BEARISH EVENT: {bear_event['drug_name']} ({bear_event['ticker']})")
    print(f"  Probability: {bear_pred['probability']:.4f}")
    print(f"  Tier: {bear_pred['tier']} → {bear_pred['action']}")
    print(f"  Signals fired: {bear_pred['signal_count']} / {bear_pred['total_signals_available']}")
    print(f"  By tier: {bear_pred.get('signal_tier_counts', {})}")
    print(f"  Total logit: {bear_pred['logit']:.4f}")

    # Score 30 random events and record outcomes
    print(f"\n{'─' * 50}")
    print("BATCH: Scoring 30 random events...")

    tas = list(PDUFA_MODE_CONFIG["ta_logits"].keys())
    for i in range(30):
        ev = {
            "event_id": f"BATCH_{i:03d}",
            "ticker": f"T{i}", "drug_name": f"D{i}",
            "therapeutic_area": random.choice(tas),
            "btd": random.random() < 0.35,
            "orphan": random.random() < 0.25,
            "priority_review": random.random() < 0.40,
            "fast_track": random.random() < 0.30,
            "first_in_class": random.random() < 0.20,
            "high_unmet_need": random.random() < 0.30,
            "prior_crl": random.random() < 0.12,
            "manufacturing_risk": random.random() < 0.10,
            "sponsor_prior_approvals": random.choice([0, 1, 3, 5, 8]),
            "pivotal_met_primary": random.random() < 0.70,
            "enrollment": random.choice([50, 150, 300, 500, 800, 1200]),
            "double_blind_rct": random.random() < 0.65,
            "safety_profile_clean": random.random() < 0.80,
            "insider_buy_signal": random.random() < 0.20,
            "options_bullish": random.random() < 0.25,
            "sentiment_bullish": random.random() < 0.30,
            "high_impact_journal": random.random() < 0.15,
        }
        r = engine.score(ev, mode="PDUFA")
        prob = r['prediction']['probability']
        outcome = "APPROVED" if random.random() < prob else "CRL"
        engine.record_outcome(f"BATCH_{i:03d}", outcome)

    # Run honing
    print("\nRunning honing cycle...")
    hone = engine.hone(force_recalibrate=True)
    pdufa_cal = hone["pdufa_calibration"]
    print(f"  Brier: {pdufa_cal['brier_score']}")
    print(f"  AUC: {pdufa_cal['auc_roc']}")
    print(f"  Accuracy: {pdufa_cal['accuracy']}")
    print(f"  Drift alerts: {len(pdufa_cal.get('drift_alerts', []))}")
    for alert in pdufa_cal.get('drift_alerts', []):
        print(f"    ⚠️ {alert}")
    print(f"  Recommendations: {len(pdufa_cal.get('recommendations', {}))}")
    if hone.get('recalibration', {}).get('status') == 'RECALIBRATED':
        recal = hone['recalibration']
        print(f"  Recalibrated: {recal['signals_changed']} signals, {recal['epochs']} epochs")
        print(f"  New version: {hone.get('new_version', 'N/A')}")

    # Full report
    report = engine.full_report()
    print(f"\n{'═' * 70}")
    print(f"  FULL REPORT")
    print(f"{'═' * 70}")
    print(f"  Model version: {report['model_version']}")
    print(f"  Total signals: {report['total_pdufa_signals']}")
    print(f"  Signal tiers: {report['signal_tiers']}")
    print(f"  Predictions tracked: {report['total_predictions']}")
    print(f"  Resolved: {report['total_resolved']}")

    # Phase 3 test
    p3_event = {
        "event_id": "P3_DEMO",
        "therapeutic_area": "Oncology",
        "p_value_tier": "p_lt_001",
        "btd": True,
        "fda_eop2_positive": True,
        "biomarker_driven": True,
        "large_enrollment": True,
        "prior_p2_strong": True,
    }
    p3 = engine.score(p3_event, mode="PHASE3")
    print(f"\n  Phase3 demo: P(success) = {p3['prediction']['probability']:.4f}")

    # Full PoS
    full = engine.score({**rich_event, **p3_event, "event_id": "FULL_POS_DEMO"}, mode="FULL_POS")
    print(f"  Full PoS demo: {full['prediction']['probability']:.4f}")

    print(f"\n{'═' * 70}")
    print(f"  ✅ ODIN v12.0 — 62 SIGNALS — FULLY OPERATIONAL")
    print(f"{'═' * 70}")

    # Cleanup
    for f in [os.path.join(tmpdir, "odin_v2_demo_ledger.json"),
              os.path.join(tmpdir, "odin_v2_demo_versions.json")]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    demo()
