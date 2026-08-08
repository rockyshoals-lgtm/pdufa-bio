#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  9REALMS — ALDX STRESS GRID                                     ║
║                                                                  ║
║  Tests all CEO tone × quiet_review × market_regime combinations  ║
║  for ALDX (2×CRL ophthalmology) to prove V2 module sensitivity  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import sys
from pathlib import Path

REALMS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REALMS_ROOT / "models"))

from ULTIMATE_ODIN_V2 import (
    UltimateOdinScorer, UltimateSignals, CeoTone, MarketRegime
)


def make_aldx_signals(ceo_tone=CeoTone.NEUTRAL, quiet_review=False,
                      regime=MarketRegime.NORMAL) -> UltimateSignals:
    """Create ALDX base signals with configurable V2 modules."""
    return UltimateSignals(
        btd=False, orphan=False, priority_review=False, fast_track=False,
        accelerated_approval=False,
        experienced_sponsor=False, inexperienced_sponsor=True, sponsor_approvals=0,
        is_snda=False, is_snda_pediatric=False, is_class1_resubmission=False,
        single_arm=False, surrogate_endpoint=False,
        prior_crl=True, prior_crl_count=2, double_crl=True,
        manufacturing_risk=False, form_483=False,
        ema_cmc_flag=False, cmc_extension=False,
        adcom_high=False, adcom_mid=False, adcom_low=False,
        safety_severity=0, ppm_flag=False,
        therapeutic_area="ophthalmology",
        is_oncology=False, is_gene_therapy=False, is_psychedelic=False,
        is_pain=False, is_hoeg_era=True, pdufa_year=2026,
        eu_approved=False, pediatric_no_pk=False,
        insider_signal=0, hiring_signal=0, social_signal=0,
        historical_crl_rate=0.29,
        avoid_override=False,
        # V2 module overrides
        ceo_tone=ceo_tone,
        quiet_review=quiet_review,
        market_regime=regime,
    )


def run_stress_grid():
    scorer = UltimateOdinScorer()
    output_dir = REALMS_ROOT / "validation"
    output_dir.mkdir(exist_ok=True)

    # Build grid: CEO tone × quiet_review × regime
    ceo_tones = [CeoTone.SILENT, CeoTone.CAUTIOUS, CeoTone.NEUTRAL, CeoTone.BULLISH]
    quiet_opts = [False, True]
    regimes = [MarketRegime.CRISIS, MarketRegime.BEAR, MarketRegime.NORMAL, MarketRegime.BULL]

    # v1071 baseline (no V2 modules = NEUTRAL, no quiet review, NORMAL)
    baseline_sig = make_aldx_signals(CeoTone.NEUTRAL, False, MarketRegime.NORMAL)
    baseline_result = scorer.score(baseline_sig)
    v1071_prob = baseline_result["probability"]

    results = []
    for ceo in ceo_tones:
        for quiet in quiet_opts:
            for regime in regimes:
                sig = make_aldx_signals(ceo, quiet, regime)
                result = scorer.score(sig)
                prob = result["probability"]
                tier = result["tier"]
                delta_pp = round((prob - v1071_prob) * 100, 1)
                results.append({
                    "ceo_tone": ceo.value,
                    "quiet_review": int(quiet),
                    "market_regime": regime.value,
                    "v1071_prob": round(v1071_prob, 4),
                    "v2_prob": round(prob, 4),
                    "v2_tier": tier,
                    "delta_pp": delta_pp,
                    "tier_change": f"T{baseline_result['tier']}→T{tier}",
                })

    # Save CSV
    csv_path = output_dir / "ALDX_STRESS_GRID.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Save summary JSON
    summary = {
        "baseline_v1071": round(v1071_prob, 4),
        "best_case": max(r["v2_prob"] for r in results),
        "worst_case": min(r["v2_prob"] for r in results),
        "bullish_quiet_normal": next(
            r["v2_prob"] for r in results
            if r["ceo_tone"] == "bullish" and r["quiet_review"] == 1
            and r["market_regime"] == "NORMAL"
        ),
        "total_configurations": len(results),
        "configurations_above_10pct": sum(1 for r in results if r["v2_prob"] >= 0.10),
        "configurations_tier_upgrade": sum(
            1 for r in results if r["v2_tier"] < baseline_result["tier"]
        ),
    }
    summary_path = output_dir / "ALDX_STRESS_SUMMARY.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Print
    print(f"\n{'='*80}")
    print(f"  ALDX STRESS GRID — {len(results)} configurations")
    print(f"{'='*80}")
    print(f"  Baseline (v1071 equiv): {v1071_prob:.4f} ({baseline_result['tier']})")
    print(f"\n  {'CEO Tone':<12} {'Quiet':<7} {'Regime':<10} {'V2 Prob':>8} {'Tier':>6} {'Delta':>8}")
    print(f"  {'-'*12} {'-'*7} {'-'*10} {'-'*8} {'-'*6} {'-'*8}")
    for r in results:
        marker = "✓" if r["v2_prob"] >= 0.10 else " "
        print(f"  {r['ceo_tone']:<12} {r['quiet_review']:<7} {r['market_regime']:<10} "
              f"{r['v2_prob']:>8.4f} {r['v2_tier']:>5}  {r['delta_pp']:>+7.1f}pp {marker}")

    print(f"\n  Saved: {csv_path}")
    print(f"  Saved: {summary_path}")
    return results


if __name__ == "__main__":
    run_stress_grid()
