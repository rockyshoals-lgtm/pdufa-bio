#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  9REALMS MODEL EVOLVER                                           ║
║                                                                  ║
║  Generates candidate model variants by perturbing V2 weights     ║
║  and evaluating against the v1071 gold standard.                 ║
║                                                                  ║
║  Evolution strategy:                                             ║
║    1. Load current champion from model_registry/                 ║
║    2. Generate N candidates with weight perturbations            ║
║    3. Score each on the holdout dataset                          ║
║    4. Return best candidate if it beats current champion         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import copy
import csv
import json
import math
import os
import pickle
import random
import sys
from datetime import datetime
from pathlib import Path

REALMS_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REALMS_ROOT / "models"
REGISTRY_DIR = MODELS_DIR / "model_registry"
DATA_DIR = REALMS_ROOT / "data"

sys.path.insert(0, str(MODELS_DIR))


# ── Weight perturbation strategies ─────────────────────────────────

MUTABLE_WEIGHTS = [
    "ceo_tone_bullish_boost",
    "ceo_tone_cautious_penalty",
    "ceo_tone_silent_penalty",
    "quiet_review_boost",
    "s17_sentiment_weight",
    "s18_engagement_spike_weight",
    "s19_social_silence_weight",
    "s20_smart_money_divergence_weight",
    "social_master_amplifier",
    "amendment_count_penalty",
    "endpoint_change_penalty",
    "pi_bad_history_penalty",
    "zero_enroller_penalty",
    "expectation_gap_weight",
    "high_expectation_penalty",
    "ix_prior_crl_x_ceo_bullish",
    "ix_prior_crl_x_quiet_review",
    "ix_gene_therapy_x_experienced",
    "ix_orphan_x_single_arm",
]


def perturb_weights(base_weights: dict, strategy: str = "gaussian",
                    magnitude: float = 0.05, seed: int = None) -> dict:
    """Generate a perturbed copy of V2 weights.

    Strategies:
      gaussian: Add N(0, magnitude) to each mutable weight
      uniform:  Add U(-magnitude, +magnitude) to each
      targeted: Perturb only one weight group (CEO, social, ops, IX)
    """
    rng = random.Random(seed)
    new_w = copy.deepcopy(base_weights)

    if strategy == "targeted":
        # Pick a random group
        groups = {
            "ceo": ["ceo_tone_bullish_boost", "ceo_tone_cautious_penalty",
                     "ceo_tone_silent_penalty", "quiet_review_boost"],
            "social": ["s17_sentiment_weight", "s18_engagement_spike_weight",
                       "s19_social_silence_weight", "s20_smart_money_divergence_weight",
                       "social_master_amplifier"],
            "ops": ["amendment_count_penalty", "endpoint_change_penalty",
                    "pi_bad_history_penalty", "zero_enroller_penalty"],
            "ix": ["ix_prior_crl_x_ceo_bullish", "ix_prior_crl_x_quiet_review",
                   "ix_gene_therapy_x_experienced", "ix_orphan_x_single_arm"],
        }
        group_name = rng.choice(list(groups.keys()))
        targets = groups[group_name]
    else:
        targets = MUTABLE_WEIGHTS

    for key in targets:
        if key not in new_w:
            continue
        if strategy == "gaussian":
            delta = rng.gauss(0, magnitude)
        elif strategy == "uniform":
            delta = rng.uniform(-magnitude, magnitude)
        elif strategy == "targeted":
            delta = rng.gauss(0, magnitude * 2)  # Larger perturbation for targeted
        else:
            delta = 0
        new_w[key] = round(new_w[key] + delta, 6)

    return new_w


def generate_candidates(base_weights: dict, n_candidates: int = 3,
                        seed: int = None) -> list:
    """Generate N candidate weight sets from base."""
    rng = random.Random(seed)
    candidates = []
    strategies = ["gaussian", "uniform", "targeted"]

    for i in range(n_candidates):
        strategy = strategies[i % len(strategies)]
        magnitude = rng.uniform(0.02, 0.10)
        c_seed = rng.randint(0, 999999)
        new_w = perturb_weights(base_weights, strategy, magnitude, c_seed)
        candidates.append({
            "version": f"candidate_{i+1}",
            "strategy": strategy,
            "magnitude": round(magnitude, 4),
            "seed": c_seed,
            "weights": new_w,
        })

    return candidates


def _bflag(row, col):
    """Parse boolean from CSV column."""
    v = row.get(col, "")
    if isinstance(v, bool):
        return v
    return str(v).strip().upper() in ("TRUE", "1", "YES", "T")


def _floatval(val, default=0.0):
    try:
        v = val.strip() if isinstance(val, str) else str(val)
        return float(v) if v else default
    except (ValueError, TypeError):
        return default


def _intval(val, default=0):
    try:
        v = val.strip() if isinstance(val, str) else str(val)
        return int(float(v)) if v else default
    except (ValueError, TypeError):
        return default


def evaluate_candidate(candidate_weights: dict, holdout_path: str) -> dict:
    """Score a candidate weight set on the holdout dataset.

    Returns metrics dict with AUC, Brier, Tier4_Precision.
    Uses ODIN_ENRICHED_1349.csv column names (matching benchmark_v1071.py).
    """
    from ULTIMATE_ODIN_V2 import (
        UltimateOdinScorer, UltimateSignals, CeoTone, MarketRegime, W_ULTIMATE
    )

    # Create scorer with modified weights
    scorer = UltimateOdinScorer()
    # Override the W_ULTIMATE in the scorer
    original_w = dict(W_ULTIMATE)

    # Monkey-patch for this evaluation
    import ULTIMATE_ODIN_V2 as mod
    for k, v in candidate_weights.items():
        if k in mod.W_ULTIMATE:
            mod.W_ULTIMATE[k] = v

    # Score holdout
    with open(holdout_path) as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("outcome", "").strip()]

    labels = []
    scores = []
    for row in rows:
        outcome = row["outcome"].strip().upper()
        if outcome not in ("APPROVAL", "CRL"):
            continue
        labels.append(1 if outcome == "APPROVAL" else 0)

        # Derived fields (mirrors benchmark_v1071.py score_v2)
        spa = _intval(row.get("sponsor_prior_approvals", "0"))
        experienced = _bflag(row, "experienced_sponsor") or spa >= 3
        adcom_pct = _floatval(row.get("adcom_vote_pct", "0"))
        had_adcom = _bflag(row, "had_adcom")
        ta = row.get("therapeutic_area", "Other")
        modality = (row.get("modality", "") or "").strip().lower()
        is_gene = modality in ("gene therapy", "gene_therapy", "cell therapy", "cell_therapy")

        cat_date = row.get("catalyst_date", "")
        try:
            year = int(cat_date[:4]) if cat_date else 2024
        except ValueError:
            year = 2024

        # Map base_rate_ta to historical CRL rate
        base_rate = _floatval(row.get("base_rate_ta", "0.87"))
        hist_crl = max(0, 1.0 - base_rate) if base_rate > 0.5 else 0.13

        sig = UltimateSignals(
            btd=_bflag(row, "btd"),
            orphan=_bflag(row, "orphan"),
            priority_review=_bflag(row, "priority_review"),
            fast_track=_bflag(row, "fast_track"),
            accelerated_approval=_bflag(row, "accelerated_approval"),
            experienced_sponsor=experienced,
            inexperienced_sponsor=not experienced,
            sponsor_approvals=spa,
            is_snda=False,
            is_snda_pediatric=False,
            is_class1_resubmission=(str(row.get("resubmission_class", "") or "").strip() == "1"),
            single_arm=False,
            surrogate_endpoint=False,
            prior_crl=_bflag(row, "prior_crl"),
            prior_crl_count=1 if _bflag(row, "prior_crl") else 0,
            double_crl=False,
            manufacturing_risk=_bflag(row, "manufacturing_risk"),
            form_483=_bflag(row, "form_483_issues"),
            ema_cmc_flag=False,
            cmc_extension=False,
            adcom_high=(had_adcom and adcom_pct >= 65),
            adcom_mid=(had_adcom and 50 <= adcom_pct < 65),
            adcom_low=(had_adcom and adcom_pct < 50 and adcom_pct > 0),
            safety_severity=0.0,
            ppm_flag=False,
            therapeutic_area=ta.lower() if ta else "other",
            is_oncology=(ta.strip().lower() == "oncology"),
            is_gene_therapy=is_gene,
            is_psychedelic=False,
            is_pain=("pain" in (ta or "").lower()),
            is_hoeg_era=(year >= 2024),
            pdufa_year=year,
            eu_approved=False,
            pediatric_no_pk=False,
            insider_signal=_floatval(row.get("insider_net_90d", "0")),
            hiring_signal=0.0,
            social_signal=_floatval(row.get("social_sentiment_avg", "0")),
            historical_crl_rate=hist_crl,
            avoid_override=False,
            ceo_tone=CeoTone.NEUTRAL,
            quiet_review=False,
            market_regime=MarketRegime.NORMAL,
        )
        result = scorer.score(sig)
        scores.append(result["probability"])

    # Restore original weights
    for k, v in original_w.items():
        mod.W_ULTIMATE[k] = v

    # Compute metrics
    from benchmark_v1071 import compute_auc, compute_brier, tier4_precision, tier1_precision
    return {
        "AUC": round(compute_auc(labels, scores), 4),
        "Brier": round(compute_brier(labels, scores), 4),
        "Tier4_Precision": round(tier4_precision(labels, scores), 4),
        "Tier1_Precision": round(tier1_precision(labels, scores), 4),
    }


def save_champion(candidate: dict, metrics: dict, version_tag: str):
    """Save a new champion to the model registry."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model_name": f"ULTIMATE_ODIN_{version_tag}",
        "created": datetime.utcnow().isoformat(),
        "strategy": candidate.get("strategy", "unknown"),
        "magnitude": candidate.get("magnitude", 0),
        "metrics": metrics,
        "weights": candidate["weights"],
    }

    pkl_path = REGISTRY_DIR / f"{version_tag}.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

    json_path = REGISTRY_DIR / f"{version_tag}_weights.json"
    with open(json_path, "w") as f:
        json.dump(candidate["weights"], f, indent=2)

    print(f"  Saved champion: {pkl_path}")
    return pkl_path


if __name__ == "__main__":
    from ULTIMATE_ODIN_V2 import W_ULTIMATE
    candidates = generate_candidates(dict(W_ULTIMATE), n_candidates=3, seed=42)
    for c in candidates:
        print(f"  {c['version']}: strategy={c['strategy']}, mag={c['magnitude']}")
        print(f"    ceo_bullish: {c['weights'].get('ceo_tone_bullish_boost', '?')}")
    print(f"\n  Generated {len(candidates)} candidates")
