"""
ODIN v10.1 — FDA PDUFA approval probability scoring

Implements the validated ODIN v10.1 additive probability model with:
- S1-S5 designations
- S6-S8 Advisory Committee (AdCom) vote adjustment
- S9-S11 prior CRL + resubmission class
- S12-S13 sponsor experience
- S14-S15 manufacturing risk
- S16 therapeutic area adjustment (with validated dampening factor)
- S17-S20 optional LunarCrush social sentiment signals (external data is passed in)
- S21 specialist composite (+0.03 if >=2 specialist-pattern signals)

No external API calls are performed in this module.

Specification source: ODIN_V101_CHATGPT_ENGINEERING_SPEC.md (Jan 31, 2026)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Union
import json


# =========== REQUIRED INPUT SCHEMA (DOC) ===========
# Included for reference and validation in downstream pipelines.
EVENT_SCHEMA = {
    # Core identifiers
    "event_id": str,  # Unique ID
    "ticker": str,  # Stock ticker
    "catalyst_date": str,  # PDUFA date (YYYY-MM-DD)

    # Designations (boolean)
    "btd": bool,
    "orphan": bool,
    "priority_review": bool,
    "fast_track": bool,
    "accelerated_approval": bool,
    "designation_stack_count": int,

    # AdCom
    "had_adcom": bool,
    "adcom_vote_pct": Optional[float],  # 0.0-1.0 (or 0-100 accepted)

    # Prior CRL
    "prior_crl": bool,
    "resubmission_class": Optional[int],  # 1 or 2

    # Sponsor
    "sponsor_prior_approvals": int,

    # Manufacturing
    "manufacturing_risk": bool,
    "form_483_issues": bool,

    # Classification
    "therapeutic_area": str,
    "modality": str,

    # Outcome (training/validation only)
    "outcome": Optional[str],  # 'APPROVAL' or 'CRL'
}

LUNARCRUSH_SCHEMA = {
    "sentiment_score": Optional[int],  # 0-100
    "engagements_24h": Optional[int],
    "engagements_daily_avg": Optional[int],
    "galaxy_score": Optional[float],
    "alt_rank": Optional[int],
}


# =========== THERAPEUTIC AREA ADJUSTMENTS (S16) ===========
TA_ADJUSTMENTS: Dict[str, float] = {
    "Pain Management": -0.30,
    "Ophthalmology": -0.25,
    "Nephrology": -0.22,
    "Hematology": -0.18,
    "CNS/Neurology": -0.10,
    "Cardiovascular": -0.08,
    "Metabolic/Endocrine": -0.07,
    "Other": -0.06,
    "Rare Disease": -0.04,
    "Immunology": +0.02,
    "Dermatology": +0.03,
    "Oncology": +0.06,
    "GI/Hepatology": +0.07,
    "Respiratory": +0.09,
    "Infectious Disease": +0.10,
    "Vaccines": +0.13,
    "Women's Health": +0.13,
}

TA_RISK_TIERS = {
    "HIGH_RISK": ["Pain Management", "Ophthalmology", "Nephrology", "Hematology"],
    "MOD_RISK": ["CNS/Neurology", "Cardiovascular", "Metabolic/Endocrine", "Other", "Rare Disease"],
    "LOW_RISK": [
        "Immunology",
        "Dermatology",
        "Oncology",
        "GI/Hepatology",
        "Respiratory",
        "Infectious Disease",
        "Vaccines",
        "Women's Health",
    ],
}

SOCIAL_SIGNAL_THRESHOLDS = {
    "s17_bullish_sentiment": 75,
    "s17_bearish_sentiment": 40,
    "s17_bullish_weight": 0.03,
    "s17_bearish_weight": -0.02,
    "s18_engagement_spike_ratio": 2.5,
    "s18_engagement_spike_weight": 0.02,
    "s19_silence_ratio": 0.3,
    "s19_silence_weight": -0.02,
    "s20_divergence_galaxy_threshold": 35,
    "s20_divergence_weight": -0.02,
}

TIER_EXPECTED_PERFORMANCE = {
    "tier1_approval_rate": 0.956,
    "tier4_crl_rate": 0.857,
    "crl_recall_at_85": 0.767,
}


@dataclass(frozen=True)
class OdinV101Config:
    """ODIN v10.1 configuration (validated).

    Notes:
        - This is an additive model in probability space.
        - Clamp is applied to keep probability within [0.01, 0.99].
    """

    # Base
    base_approval_rate: float = 0.827

    # Designations (S1-S5) — UPDATED
    btd_weight: float = 0.12
    orphan_weight: float = 0.10
    priority_review_weight: float = 0.085
    fast_track_weight: float = 0.03
    accelerated_approval_weight: float = 0.05

    # AdCom (S6-S8)
    adcom_high_threshold: float = 0.65
    adcom_high_boost: float = 0.08
    adcom_mid_threshold: float = 0.50
    adcom_mid_penalty: float = -0.06
    adcom_low_penalty: float = -0.19

    # Prior CRL / Resubmission (S9-S11)
    prior_crl_penalty: float = -0.085
    class1_resubmission_boost: float = 0.157
    class2_resubmission_penalty: float = -0.05

    # Sponsor (S12-S13)
    experienced_sponsor_boost: float = 0.05
    inexperienced_sponsor_penalty: float = -0.07

    # Manufacturing (S14-S15)
    manufacturing_risk_penalty: float = -0.12
    form_483_penalty: float = -0.07

    # TA adjustment weight / dampening (S16)
    ta_adjustment_weight: float = 0.83

    # Specialist composite (S21)
    specialist_composite_bonus: float = 0.03

    # Tier thresholds
    tier1_threshold: float = 0.858
    tier2_threshold: float = 0.734
    tier3_threshold: float = 0.578

    # Clamp bounds
    clamp_min: float = 0.01
    clamp_max: float = 0.99


Number = Union[int, float]


def _to_bool(value: Any) -> bool:
    """Best-effort conversion for common truthy/falsey representations."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        # Handle NaN
        if isinstance(value, float) and value != value:  # noqa: E711
            return False
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "t", "yes", "y", "1"}:
            return True
        if v in {"false", "f", "no", "n", "0", ""}:
            return False
    return bool(value)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:  # noqa: E711
            return default
        return int(value)
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return default
        try:
            return int(float(v))
        except ValueError:
            return default
    return default


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value:  # noqa: E711
            return default
        return float(value)
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return default
        try:
            return float(v)
        except ValueError:
            return default
    return default


def _normalize_vote_pct(adcom_vote_pct: Any) -> Optional[float]:
    """Normalize AdCom vote pct to 0.0-1.0.

    Accepts:
        - 0.0-1.0 floats
        - 0-100 numeric or numeric-string percentages (e.g., 65 => 0.65)
    """
    vote = _to_float(adcom_vote_pct, default=None)
    if vote is None:
        return None
    if vote > 1.0 and vote <= 100.0:
        return vote / 100.0
    return vote


def clamp_probability(prob: float, config: OdinV101Config) -> float:
    return max(config.clamp_min, min(config.clamp_max, prob))


def classify_tier(probability: float, config: OdinV101Config) -> str:
    if probability >= config.tier1_threshold:
        return "TIER_1"
    if probability >= config.tier2_threshold:
        return "TIER_2"
    if probability >= config.tier3_threshold:
        return "TIER_3"
    return "TIER_4"


def calculate_social_signals(lunarcrush_data: Mapping[str, Any]) -> Dict[str, float]:
    """Calculate S17-S20 social signals from LunarCrush-like data.

    Uses thresholds from SOCIAL_SIGNAL_THRESHOLDS constant.

    Returns:
        Dict with 's17_social_sentiment', 's18_engagement_spike',
        's19_social_silence', 's20_smart_money_divergence'
    """
    signals: Dict[str, float] = {
        "s17_social_sentiment": 0.0,
        "s18_engagement_spike": 0.0,
        "s19_social_silence": 0.0,
        "s20_smart_money_divergence": 0.0,
    }

    sentiment_raw = lunarcrush_data.get("sentiment_score")
    sentiment = _to_int(sentiment_raw, default=-1)
    sentiment_val: Optional[int] = None if sentiment < 0 else sentiment

    engagements_24h = _to_float(lunarcrush_data.get("engagements_24h"), default=0.0) or 0.0
    engagements_avg = _to_float(lunarcrush_data.get("engagements_daily_avg"), default=1.0) or 1.0
    galaxy_score = _to_float(lunarcrush_data.get("galaxy_score"), default=None)

    # Engagement ratio used for S18 and S19
    engagement_ratio: Optional[float] = None
    if engagements_avg and engagements_avg > 0:
        engagement_ratio = engagements_24h / engagements_avg

    # S17: Social Sentiment
    if sentiment_val is not None:
        if sentiment_val >= SOCIAL_SIGNAL_THRESHOLDS["s17_bullish_sentiment"]:
            signals["s17_social_sentiment"] = float(SOCIAL_SIGNAL_THRESHOLDS["s17_bullish_weight"])
        elif sentiment_val <= SOCIAL_SIGNAL_THRESHOLDS["s17_bearish_sentiment"]:
            signals["s17_social_sentiment"] = float(SOCIAL_SIGNAL_THRESHOLDS["s17_bearish_weight"])

    # S18: Engagement Spike (bullish if high engagement + positive sentiment)
    if engagement_ratio is not None and sentiment_val is not None:
        if (
            engagement_ratio >= SOCIAL_SIGNAL_THRESHOLDS["s18_engagement_spike_ratio"]
            and sentiment_val >= 70
        ):
            signals["s18_engagement_spike"] = float(SOCIAL_SIGNAL_THRESHOLDS["s18_engagement_spike_weight"])

    # S19: Social Silence (bearish if unusually low engagement)
    if engagement_ratio is not None:
        if engagement_ratio <= SOCIAL_SIGNAL_THRESHOLDS["s19_silence_ratio"]:
            signals["s19_social_silence"] = float(SOCIAL_SIGNAL_THRESHOLDS["s19_silence_weight"])

    # S20: Smart Money Divergence (bearish if low galaxy score despite positive sentiment)
    if galaxy_score is not None and sentiment_val is not None:
        if (
            galaxy_score < SOCIAL_SIGNAL_THRESHOLDS["s20_divergence_galaxy_threshold"]
            and sentiment_val >= 60
        ):
            signals["s20_smart_money_divergence"] = float(SOCIAL_SIGNAL_THRESHOLDS["s20_divergence_weight"])

    return signals


def calculate_specialist_signal(event: Mapping[str, Any], config: OdinV101Config) -> float:
    """S21 specialist composite bonus.

    Returns +specialist_composite_bonus if >=2 signals are present:
      - btd
      - orphan
      - therapeutic_area in {'Rare Disease','Oncology'}
      - designation_stack_count >= 3
    """
    ta = str(event.get("therapeutic_area", "") or "")
    specialist_count = sum(
        [
            _to_bool(event.get("btd", False)),
            _to_bool(event.get("orphan", False)),
            ta in {"Rare Disease", "Oncology"},
            _to_int(event.get("designation_stack_count", 0), default=0) >= 3,
        ]
    )
    return config.specialist_composite_bonus if specialist_count >= 2 else 0.0


def score_pdufa_event(
    event: Mapping[str, Any],
    config: Optional[OdinV101Config] = None,
    lunarcrush_data: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Score a PDUFA event using ODIN v10.1.

    Args:
        event: Mapping with PDUFA features (see EVENT_SCHEMA).
        config: OdinV101Config (defaults used if None).
        lunarcrush_data: Optional LunarCrush-like data dict (S17-S20).

    Returns:
        Dict with probability, tier, risk tier, and a signal breakdown.
    """
    if config is None:
        config = OdinV101Config()

    prob = float(config.base_approval_rate)
    signals: Dict[str, float] = {}

    # =========== DESIGNATION SIGNALS (S1-S5) ===========
    if _to_bool(event.get("btd")):
        prob += config.btd_weight
        signals["S1_btd"] = config.btd_weight

    if _to_bool(event.get("orphan")):
        prob += config.orphan_weight
        signals["S2_orphan"] = config.orphan_weight

    if _to_bool(event.get("priority_review")):
        prob += config.priority_review_weight
        signals["S3_priority_review"] = config.priority_review_weight

    if _to_bool(event.get("fast_track")):
        prob += config.fast_track_weight
        signals["S4_fast_track"] = config.fast_track_weight

    if _to_bool(event.get("accelerated_approval")):
        prob += config.accelerated_approval_weight
        signals["S5_accelerated"] = config.accelerated_approval_weight

    # =========== ADCOM SIGNALS (S6-S8) ===========
    if _to_bool(event.get("had_adcom")):
        vote = _normalize_vote_pct(event.get("adcom_vote_pct"))
        if vote is not None:
            if vote >= config.adcom_high_threshold:
                prob += config.adcom_high_boost
                signals["S6_adcom_high"] = config.adcom_high_boost
            elif vote >= config.adcom_mid_threshold:
                prob += config.adcom_mid_penalty
                signals["S7_adcom_mid"] = config.adcom_mid_penalty
            else:
                prob += config.adcom_low_penalty
                signals["S8_adcom_low"] = config.adcom_low_penalty

    # =========== PRIOR CRL / RESUBMISSION (S9-S11) ===========
    if _to_bool(event.get("prior_crl")):
        prob += config.prior_crl_penalty
        signals["S9_prior_crl"] = config.prior_crl_penalty

        resub_class = _to_int(event.get("resubmission_class"), default=0)
        if resub_class == 1:
            prob += config.class1_resubmission_boost
            signals["S10_class1_boost"] = config.class1_resubmission_boost
        elif resub_class == 2:
            prob += config.class2_resubmission_penalty
            signals["S11_class2_penalty"] = config.class2_resubmission_penalty

    # =========== SPONSOR EXPERIENCE (S12-S13) ===========
    prior_approvals = _to_int(event.get("sponsor_prior_approvals", 0), default=0)
    if prior_approvals >= 5:
        prob += config.experienced_sponsor_boost
        signals["S12_experienced"] = config.experienced_sponsor_boost
    elif prior_approvals == 0:
        prob += config.inexperienced_sponsor_penalty
        signals["S13_inexperienced"] = config.inexperienced_sponsor_penalty

    # =========== MANUFACTURING RISK (S14-S15) ===========
    if _to_bool(event.get("manufacturing_risk")):
        prob += config.manufacturing_risk_penalty
        signals["S14_mfg_risk"] = config.manufacturing_risk_penalty

    if _to_bool(event.get("form_483_issues")):
        prob += config.form_483_penalty
        signals["S15_form_483"] = config.form_483_penalty

    # =========== THERAPEUTIC AREA (S16) ===========
    ta = str(event.get("therapeutic_area", "Other") or "Other")
    ta_base = TA_ADJUSTMENTS.get(ta, 0.0)
    ta_adj = ta_base * config.ta_adjustment_weight
    if ta_adj != 0:
        prob += ta_adj
        signals["S16_therapeutic_area"] = ta_adj

    # =========== SOCIAL SENTIMENT (S17-S20) ===========
    if lunarcrush_data:
        social_signals = calculate_social_signals(lunarcrush_data)
        for key, val in social_signals.items():
            if val != 0:
                prob += val
                signals[key.upper()] = val

    # =========== SPECIALIST COMPOSITE (S21) ===========
    s21 = calculate_specialist_signal(event, config)
    if s21 != 0:
        prob += s21
        signals["S21_specialist_composite"] = s21

    # =========== CLAMP & CLASSIFY ===========
    prob = clamp_probability(prob, config)
    tier = classify_tier(prob, config)

    # =========== TA RISK TIER ===========
    ta_risk = "UNKNOWN"
    if ta in TA_RISK_TIERS["HIGH_RISK"]:
        ta_risk = "HIGH_RISK"
    elif ta in TA_RISK_TIERS["MOD_RISK"]:
        ta_risk = "MOD_RISK"
    elif ta in TA_RISK_TIERS["LOW_RISK"]:
        ta_risk = "LOW_RISK"

    return {
        "version": "10.1",
        "probability": prob,
        "tier": tier,
        "ta_risk_tier": ta_risk,
        "therapeutic_area": ta,
        "signals": signals,
        "signal_count": len(signals),
        "total_adjustment": prob - float(config.base_approval_rate),
    }


def batch_score_dataset(
    df,
    config: Optional[OdinV101Config] = None,
    lunarcrush_cache: Optional[Mapping[str, Mapping[str, Any]]] = None,
):
    """Score an entire pandas DataFrame of events and return a DataFrame of results.

    Expected DF columns (at minimum): event_id, ticker, plus scoring fields.
    If lunarcrush_cache is provided, it should be a dict: {ticker: lunarcrush_data_dict}.
    """
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("batch_score_dataset requires pandas to be installed.") from e

    if config is None:
        config = OdinV101Config()

    results = []
    for _, row in df.iterrows():
        event = row.to_dict()
        ticker = str(event.get("ticker", "") or "")
        lc_data = lunarcrush_cache.get(ticker) if lunarcrush_cache else None
        result = score_pdufa_event(event, config, lc_data)
        results.append(
            {
                "event_id": event.get("event_id"),
                "odin_v101_probability": result["probability"],
                "odin_v101_tier": result["tier"],
                "odin_v101_ta_risk": result["ta_risk_tier"],
                "odin_v101_signals": json.dumps(result["signals"], sort_keys=True),
            }
        )

    return pd.DataFrame(results)


def export_v101_config(config: OdinV101Config, filepath: str) -> None:
    """Export config JSON for cross-session persistence.

    The output structure matches the provided ODIN_V101_CONFIG.json format.
    """
    data = {
        "version": "10.1",
        "validated_date": "2026-01-31",
        "validation_summary": {
            "dataset_size": 1934,
            "baseline_approval_rate": 0.8278,
            "specialist_cohort_approval": 0.901,
            "z_score": 7.24,
            "p_value": 4.6e-13,
            "brier_score_target": 0.085,
        },
        "parameters": {
            **{k: v for k, v in asdict(config).items() if k not in {"clamp_min", "clamp_max"}},
            "experienced_sponsor_threshold": 5,
            "specialist_composite_threshold": 2,
        },
        "tier_thresholds": {
            "tier1": config.tier1_threshold,
            "tier2": config.tier2_threshold,
            "tier3": config.tier3_threshold,
        },
        "tier_expected_performance": TIER_EXPECTED_PERFORMANCE,
        "therapeutic_area_adjustments": TA_ADJUSTMENTS,
        "ta_risk_tiers": TA_RISK_TIERS,
        "social_signal_thresholds": SOCIAL_SIGNAL_THRESHOLDS,
        "specialist_proxy_definition": {
            "description": "Event matches specialist fund investment patterns",
            "criteria": [
                "btd == True",
                "orphan == True",
                "therapeutic_area in ['Rare Disease', 'Oncology']",
                "designation_stack_count >= 3",
            ],
            "composite_trigger": "2+ criteria must be met for S21 bonus",
        },
        "signal_registry": {
            "S1": {"name": "BTD", "field": "btd", "weight": config.btd_weight, "type": "boolean"},
            "S2": {"name": "Orphan", "field": "orphan", "weight": config.orphan_weight, "type": "boolean"},
            "S3": {"name": "Priority Review", "field": "priority_review", "weight": config.priority_review_weight, "type": "boolean"},
            "S4": {"name": "Fast Track", "field": "fast_track", "weight": config.fast_track_weight, "type": "boolean"},
            "S5": {"name": "Accelerated Approval", "field": "accelerated_approval", "weight": config.accelerated_approval_weight, "type": "boolean"},
            "S6": {"name": "AdCom High", "condition": "adcom_vote_pct >= 0.65", "weight": config.adcom_high_boost, "type": "conditional"},
            "S7": {"name": "AdCom Mid", "condition": "0.50 <= adcom_vote_pct < 0.65", "weight": config.adcom_mid_penalty, "type": "conditional"},
            "S8": {"name": "AdCom Low", "condition": "adcom_vote_pct < 0.50", "weight": config.adcom_low_penalty, "type": "conditional"},
            "S9": {"name": "Prior CRL", "field": "prior_crl", "weight": config.prior_crl_penalty, "type": "boolean"},
            "S10": {"name": "Class 1 Resubmission", "condition": "prior_crl AND resubmission_class == 1", "weight": config.class1_resubmission_boost, "type": "conditional"},
            "S11": {"name": "Class 2 Resubmission", "condition": "prior_crl AND resubmission_class == 2", "weight": config.class2_resubmission_penalty, "type": "conditional"},
            "S12": {"name": "Experienced Sponsor", "condition": "sponsor_prior_approvals >= 5", "weight": config.experienced_sponsor_boost, "type": "conditional"},
            "S13": {"name": "Inexperienced Sponsor", "condition": "sponsor_prior_approvals == 0", "weight": config.inexperienced_sponsor_penalty, "type": "conditional"},
            "S14": {"name": "Manufacturing Risk", "field": "manufacturing_risk", "weight": config.manufacturing_risk_penalty, "type": "boolean"},
            "S15": {"name": "Form 483 Issues", "field": "form_483_issues", "weight": config.form_483_penalty, "type": "boolean"},
            "S16": {"name": "Therapeutic Area", "field": "therapeutic_area", "weight": "lookup * 0.83", "type": "lookup"},
            "S17": {"name": "Social Sentiment", "source": "lunarcrush", "weight": "±0.02-0.03", "type": "external"},
            "S18": {"name": "Engagement Spike", "source": "lunarcrush", "weight": SOCIAL_SIGNAL_THRESHOLDS["s18_engagement_spike_weight"], "type": "external"},
            "S19": {"name": "Social Silence", "source": "lunarcrush", "weight": SOCIAL_SIGNAL_THRESHOLDS["s19_silence_weight"], "type": "external"},
            "S20": {"name": "Smart Money Divergence", "source": "lunarcrush", "weight": SOCIAL_SIGNAL_THRESHOLDS["s20_divergence_weight"], "type": "external"},
            "S21": {"name": "Specialist Composite", "condition": "specialist_count >= 2", "weight": config.specialist_composite_bonus, "type": "composite"},
        },
        "changelog": {
            "v10.1": {
                "date": "2026-01-31",
                "changes": [
                    "BTD weight increased from 0.06 to 0.12 (validated: 96.3% approval)",
                    "Orphan weight increased from 0.04 to 0.10 (validated: 92.8% approval)",
                    "Ophthalmology penalty increased from -0.131 to -0.25 (30.4% CRL)",
                    "Pain Management penalty increased from -0.286 to -0.30 (29.5% CRL)",
                    "Added S21 Specialist Composite signal (+0.03)",
                    "Added S17-S20 LunarCrush social signals",
                    "Validation: p=4.6e-13 on 1,934 events",
                ],
            }
        },
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def load_v101_config(filepath: str) -> OdinV101Config:
    """Load a config exported by export_v101_config() or the provided ODIN_V101_CONFIG.json.

    Only parameters that exist in OdinV101Config are applied; unknown keys are ignored.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    params = data.get("parameters", {})
    allowed = {field.name for field in OdinV101Config.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    cleaned = {k: v for k, v in params.items() if k in allowed}
    return OdinV101Config(**cleaned)
