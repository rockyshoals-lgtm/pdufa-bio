import sys
from pathlib import Path

# Ensure the module under /mnt/data is importable when running pytest from anywhere.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from odin_v101 import calculate_social_signals, score_pdufa_event


def test_btd_orphan_oncology_should_be_tier1_high_prob():
    event = {
        "btd": True,
        "orphan": True,
        "therapeutic_area": "Oncology",
        "sponsor_prior_approvals": 10,
        "designation_stack_count": 3,
    }
    result = score_pdufa_event(event)
    assert result["tier"] == "TIER_1"
    assert result["probability"] > 0.95  # should clamp to 0.99 in this case


def test_pain_management_no_designations_should_be_tier3_or_4_low_prob():
    event = {
        "btd": False,
        "orphan": False,
        "priority_review": False,
        "therapeutic_area": "Pain Management",
        "sponsor_prior_approvals": 2,
        "designation_stack_count": 0,
    }
    result = score_pdufa_event(event)
    assert result["tier"] in ["TIER_3", "TIER_4"]
    assert result["probability"] < 0.65


def test_adcom_vote_pct_accepts_percent_input():
    event = {
        "had_adcom": True,
        "adcom_vote_pct": 65,  # percent-style input should normalize to 0.65
        "therapeutic_area": "Oncology",
        "sponsor_prior_approvals": 1,
    }
    result = score_pdufa_event(event)
    assert result["signals"].get("S6_adcom_high") == pytest.approx(0.08)
    # 0.827 + 0.08 + (0.06 * 0.83)
    assert result["probability"] == pytest.approx(0.827 + 0.08 + (0.06 * 0.83), abs=1e-6)
    assert result["tier"] == "TIER_1"
def test_prior_crl_class1_applies_penalty_then_boost():
    event = {
        "prior_crl": True,
        "resubmission_class": 1,
        "sponsor_prior_approvals": 1,
        "therapeutic_area": "Oncology",
    }
    result = score_pdufa_event(event)
    # -0.085 + 0.157 = +0.072 net (plus TA adjustment for Oncology)
    assert result["signals"].get("S9_prior_crl") == pytest.approx(-0.085)
    assert result["signals"].get("S10_class1_boost") == pytest.approx(0.157)
    expected = 0.827 + (-0.085 + 0.157) + (0.06 * 0.83)
    assert result["probability"] == pytest.approx(expected, abs=1e-6)
    assert result["tier"] == "TIER_1"
def test_probability_clamps_to_0_99_upper():
    event = {
        "btd": True,
        "orphan": True,
        "priority_review": True,
        "fast_track": True,
        "accelerated_approval": True,
        "therapeutic_area": "Vaccines",
        "sponsor_prior_approvals": 10,
        "designation_stack_count": 5,
        "had_adcom": True,
        "adcom_vote_pct": 0.9,
    }
    result = score_pdufa_event(event)
    assert result["probability"] == 0.99


def test_probability_clamps_to_0_01_lower():
    event = {
        "therapeutic_area": "Pain Management",
        "had_adcom": True,
        "adcom_vote_pct": 0.3,
        "prior_crl": True,
        "resubmission_class": 2,
        "sponsor_prior_approvals": 0,
        "manufacturing_risk": True,
        "form_483_issues": True,
        "designation_stack_count": 0,
    }
    result = score_pdufa_event(event)
    assert result["probability"] == 0.01
    assert result["tier"] == "TIER_4"


def test_unknown_therapeutic_area_has_no_s16_adjustment():
    event = {"therapeutic_area": "Totally Unknown TA"}
    result = score_pdufa_event(event)
    assert "S16_therapeutic_area" not in result["signals"]


def test_social_signals_rules():
    lc = {
        "sentiment_score": 80,
        "engagements_24h": 2500,
        "engagements_daily_avg": 500,
        "galaxy_score": 20,
    }
    sigs = calculate_social_signals(lc)
    # S17 +0.03 (sentiment >=75)
    assert sigs["s17_social_sentiment"] == pytest.approx(0.03)
    # S18 +0.02 (ratio=5.0 and sentiment >=70)
    assert sigs["s18_engagement_spike"] == pytest.approx(0.02)
    # S19 not triggered (ratio=5.0)
    assert sigs["s19_social_silence"] == pytest.approx(0.0)
    # S20 triggered (galaxy<35 and sentiment>=60)
    assert sigs["s20_smart_money_divergence"] == pytest.approx(-0.02)
