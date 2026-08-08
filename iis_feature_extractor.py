#!/usr/bin/env python3
"""
================================================================================
IIS FEATURE EXTRACTOR v1.0 — Interim Inflation Score Feature Pipeline
================================================================================
Extracts IIS-relevant features from historical readout events for Gungnir v34.
Hybrid approach: auto-detects what it can, flags events needing manual review.

AUTO-DETECTABLE:
  - is_interim (NLP on catalyst text + stage)
  - is_topline (NLP on catalyst text)
  - n_per_arm_estimate (CT.gov enrollment / n_arms)
  - is_small_n (n_per_arm < 20)
  - has_prior_readout_same_drug (journey index)
  - days_since_prior_readout (journey index)
  - stock_reaction_on_readout (D0 return from price data)
  - smart_money_rejection (positive outcome + negative D0 return)
  - is_combined_dose_text (NLP for "combined" / "pooled" dose language)

NEEDS MANUAL REVIEW:
  - dose_response_inverted (requires reading the actual data)
  - headline_is_combined_dose (requires decomposition of press release)
  - interim_pct_patients_evaluated (requires reading press release)
  - cash_runway_months (requires financial data)
  - comparator_timepoint_matched (requires domain expertise)

OUTPUT:
  - iis_features_auto.json — Auto-detected features per event
  - iis_manual_review.json — Events flagged for manual annotation
  - iis_v34_training_features.csv — Ready-to-merge feature columns for v34

USAGE:
  python iis_feature_extractor.py
"""

import csv, json, math, os, re, sys
from collections import defaultdict
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_gungnir_dataset.csv")
CTGOV_TRAINING = os.path.join(DATA_DIR, "ctgov_training_lookup.json")
MOMENTUM_CACHE = os.path.join(DATA_DIR, "readout_momentum_cache.json")

OUTPUT_AUTO = os.path.join(DATA_DIR, "iis_features_auto.json")
OUTPUT_MANUAL = os.path.join(DATA_DIR, "iis_manual_review.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "iis_v34_training_features.csv")


# =============================================================================
# NLP PATTERNS FOR INTERIM / COMBINED DOSE DETECTION
# =============================================================================

INTERIM_PATTERNS = [
    r"(?i)\binterim\b",
    r"(?i)\bpreliminary\b(?!.*(?:full|final|topline))",
    r"(?i)\binitial\s+(?:data|results|analysis)",
    r"(?i)\bfirst\s+(?:data|results)\b",
    r"(?i)\b(?:~?\s*\d{1,2}%|approximately\s+\d{1,2}%|about\s+\d{1,2}%)\s*(?:of\s+)?patients?\s+(?:evaluated|analyzed|completed)",
    r"(?i)\bDSMB\b.*\b(?:interim|review)\b",
    r"(?i)\bfutility\b",
    r"(?i)\bpartial\s+(?:data|results|analysis)",
    r"(?i)\bearly\s+(?:data|results|signal|look)",
    r"(?i)\bupdated?\s+(?:data|results|analysis)\b",
]

TOPLINE_PATTERNS = [
    r"(?i)\btopline\b",
    r"(?i)\btop-line\b",
    r"(?i)\bfull\s+(?:data|results)\b",
    r"(?i)\bprimary\s+endpoint\s+(?:met|achieved|reached)",
    r"(?i)\bfailed\s+(?:to\s+)?meet\b.*primary",
    r"(?i)\bdid\s+not\s+meet\b.*primary",
]

COMBINED_DOSE_PATTERNS = [
    r"(?i)\bcombined\s+(?:dose|arm)",
    r"(?i)\bpooled\s+(?:analysis|data|dose|arm)",
    r"(?i)\ball\s+(?:treated|dose|arm).*(?:vs|versus)\s+(?:placebo|control|sham)",
    r"(?i)\b(?:medium|low|high)\s*\+\s*(?:medium|low|high)\s+dose",
    r"(?i)\bcombination\s+of\s+(?:dose|arm)",
    r"(?i)\boverall\s+(?:treated|active)\s+(?:group|arm|population)",
]

DOSE_RESPONSE_HINT_PATTERNS = [
    r"(?i)\bdose[- ]?(?:response|dependent|escalat|rang)",
    r"(?i)\b(?:low|medium|mid|high)\s+dose",
    r"(?i)\b\d+\s*mg\b.*\b\d+\s*mg\b",  # Multiple dose mentions
    r"(?i)\bcohort\s*[A-D1-4]",
    r"(?i)\barm\s*[A-D1-4]",
]

SMALL_N_HINTS = [
    r"(?i)\b(?:N\s*=\s*\d{1,2})\b",  # N = single/double digit
    r"(?i)\b(?:\d{1,2})\s+(?:patients?|subjects?)\s+(?:in|per|each)",
    r"(?i)\b(?:small|limited|pilot)\s+(?:sample|cohort|study|group|number)",
]


def detect_interim(text):
    """Detect if readout is interim vs topline/full. Returns (is_interim, confidence, evidence)."""
    if not text:
        return 0, 0.0, ""

    interim_hits = []
    for p in INTERIM_PATTERNS:
        m = re.search(p, text)
        if m:
            interim_hits.append(m.group())

    topline_hits = []
    for p in TOPLINE_PATTERNS:
        m = re.search(p, text)
        if m:
            topline_hits.append(m.group())

    if interim_hits and not topline_hits:
        return 1, 0.9, "; ".join(interim_hits)
    elif interim_hits and topline_hits:
        # Ambiguous — could be "interim topline" or "updated from interim to topline"
        return 1, 0.5, f"MIXED: interim=[{'; '.join(interim_hits)}] topline=[{'; '.join(topline_hits)}]"
    elif topline_hits:
        return 0, 0.9, "; ".join(topline_hits)
    else:
        return 0, 0.3, "NO_MATCH"


def detect_combined_dose(text):
    """Detect if headline uses combined/pooled dose language."""
    if not text:
        return 0, 0.0, ""

    hits = []
    for p in COMBINED_DOSE_PATTERNS:
        m = re.search(p, text)
        if m:
            hits.append(m.group())

    if hits:
        return 1, 0.7, "; ".join(hits)
    return 0, 0.0, ""


def detect_dose_response_hints(text):
    """Detect if text mentions dose-response patterns (flag for manual review)."""
    if not text:
        return 0, []

    hits = []
    for p in DOSE_RESPONSE_HINT_PATTERNS:
        m = re.search(p, text)
        if m:
            hits.append(m.group())

    return len(hits), hits


def detect_small_n_hints(text):
    """Detect hints of small sample size in text."""
    if not text:
        return 0, []

    hits = []
    for p in SMALL_N_HINTS:
        m = re.search(p, text)
        if m:
            hits.append(m.group())

    return len(hits), hits


def classify_stock_reaction(outcome, ret_0d, ret_1d):
    """Detect smart money rejection: positive data + negative stock reaction."""
    if outcome == "positive" and ret_0d is not None and ret_0d <= -5.0:
        return "SMART_MONEY_REJECTION", ret_0d
    if outcome == "positive" and ret_1d is not None and ret_1d <= -5.0:
        return "SMART_MONEY_REJECTION_D1", ret_1d
    if outcome == "positive" and ret_0d is not None and ret_0d <= -2.0:
        return "MILD_DISAPPOINTMENT", ret_0d
    if outcome == "negative" and ret_0d is not None and ret_0d >= 5.0:
        return "NEGATIVE_DATA_BOUNCE", ret_0d
    return "ALIGNED", ret_0d


# =============================================================================
# JOURNEY-BASED PRIOR READOUT DETECTION
# =============================================================================

def build_drug_timeline(events):
    """Build a timeline of readouts per drug for prior-readout detection."""
    # Normalize drug keys
    drug_events = defaultdict(list)
    for i, ev in enumerate(events):
        drug = ev.get("drug", "")
        # Extract base drug name (before the " - (" trial name)
        base_drug = re.split(r"\s*[-–]\s*\(", drug)[0].strip()
        drug_key = re.sub(r"[^a-z0-9]", "", base_drug.lower())[:30]
        if drug_key:
            drug_events[drug_key].append({
                "idx": i,
                "date": ev.get("date", ""),
                "outcome": ev.get("outcome", ""),
                "ticker": ev.get("ticker", ""),
            })

    # Sort each drug's events by date
    for dk in drug_events:
        drug_events[dk].sort(key=lambda x: x["date"])

    return drug_events


def compute_prior_readout_features(event_idx, event_date, drug_key, drug_events):
    """Compute days since prior readout and whether prior data exists for same drug."""
    timeline = drug_events.get(drug_key, [])

    prior = [e for e in timeline if e["date"] < event_date and e["idx"] != event_idx]

    if not prior:
        return {
            "has_prior_readout_same_drug": 0,
            "days_since_prior_readout": 0,
            "n_prior_readouts_same_drug": 0,
            "prior_readout_was_positive": 0,
        }

    latest_prior = prior[-1]
    try:
        d1 = datetime.strptime(event_date, "%Y-%m-%d")
        d2 = datetime.strptime(latest_prior["date"], "%Y-%m-%d")
        days_gap = (d1 - d2).days
    except:
        days_gap = 365  # default

    return {
        "has_prior_readout_same_drug": 1,
        "days_since_prior_readout": min(days_gap, 1095),  # cap at 3 years
        "n_prior_readouts_same_drug": len(prior),
        "prior_readout_was_positive": 1 if latest_prior["outcome"] == "positive" else 0,
    }


# =============================================================================
# CT.GOV-BASED N PER ARM ESTIMATION
# =============================================================================

def estimate_n_per_arm(ctgov_data, phase):
    """Estimate N per arm from CT.gov enrollment and n_arms."""
    if not ctgov_data or "error" in ctgov_data:
        # Phase-based defaults (median N per arm)
        defaults = {1: 25, 2: 60, 3: 200}
        return defaults.get(phase, 60), False

    enrollment = ctgov_data.get("enrollment", 0)
    n_arms = ctgov_data.get("n_arms", 2)

    if enrollment > 0 and n_arms > 0:
        n_per_arm = enrollment / n_arms
        return round(n_per_arm), True

    return 60, False


# =============================================================================
# IIS COMPOSITE SCORE
# =============================================================================

def compute_iis_score(features):
    """Compute Interim Inflation Score from extracted features."""
    score = 0
    flags = []

    # Only apply IIS logic if this IS an interim readout
    if not features.get("is_interim", 0):
        return 0, "NOT_INTERIM", flags

    # INVERTED_DOSE_RESPONSE (manual only — flag weight = 30)
    if features.get("dose_response_inverted", 0):
        score += 30
        flags.append("INVERTED_DOSE_RESPONSE")

    # TINY_N_INTERIM (auto from CT.gov — weight = 20)
    n_per_arm = features.get("n_per_arm_estimate", 999)
    if n_per_arm < 12:
        score += 20
        flags.append("TINY_N_LT_12")
    elif n_per_arm < 20:
        score += 12
        flags.append("TINY_N_LT_20")

    # MARKET_SIGNAL_ON_POSITIVE_DATA (auto — weight = 20)
    if features.get("stock_reaction_class") == "SMART_MONEY_REJECTION":
        score += 20
        flags.append("SMART_MONEY_REJECTION")
    elif features.get("stock_reaction_class") == "SMART_MONEY_REJECTION_D1":
        score += 15
        flags.append("SMART_MONEY_REJECTION_D1")
    elif features.get("stock_reaction_class") == "MILD_DISAPPOINTMENT":
        score += 8
        flags.append("MILD_DISAPPOINTMENT")

    # COMBINED_DOSE_HEADLINE (auto NLP — weight = 15)
    if features.get("is_combined_dose_text", 0):
        score += 15
        flags.append("COMBINED_DOSE_HEADLINE")

    # EARLY_REPORTER_BIAS (auto if interim — weight = 15)
    # Any interim analysis inherently has this bias
    if features.get("is_interim", 0):
        score += 10  # base penalty for all interims
        flags.append("EARLY_REPORTER_BIAS")

    # STAGNANT_SIGNAL_OVER_TIME (partially auto — weight = 8)
    if features.get("has_prior_readout_same_drug", 0):
        days = features.get("days_since_prior_readout", 999)
        if days < 400:  # Prior readout within ~13 months
            score += 8
            flags.append("STAGNANT_SIGNAL_RISK")

    # ANALYST_DOWNGRADE_PRE_READOUT (manual only — weight = 10)
    if features.get("analyst_downgrade_pre_readout", 0):
        score += 10
        flags.append("ANALYST_DOWNGRADE")

    # CASH_RUNWAY_PRESSURE (manual only — weight = 5)
    if features.get("cash_runway_months", 999) < 12:
        score += 5
        flags.append("CASH_RUNWAY_PRESSURE")

    # Tier assignment
    if score >= 66:
        tier = "IIS_TIER_4"
    elif score >= 46:
        tier = "IIS_TIER_3"
    elif score >= 21:
        tier = "IIS_TIER_2"
    else:
        tier = "IIS_TIER_1"

    return score, tier, flags


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():
    print("=" * 80)
    print("IIS FEATURE EXTRACTOR v1.0 — Interim Inflation Score Pipeline")
    print("=" * 80)

    # Step 1: Load readout analysis data (main training data)
    print("\n[LOAD] Loading readout analysis data...")
    events = []
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            events.append(r)
    print(f"  Readout events: {len(events)}")

    # Step 2: Load enriched data for catalyst text
    print("[LOAD] Loading enriched catalyst text...")
    enriched_text = {}
    with open(ENRICHED_CSV) as f:
        for r in csv.DictReader(f):
            ticker = r.get("Ticker", "").strip()
            date = r.get("date", "").strip()
            key = f"{ticker}|{date}"
            catalyst_text = r.get("Catalyst", "") or ""
            stage = r.get("Stage", "") or ""
            enriched_text[key] = {
                "catalyst_text": catalyst_text,
                "stage": stage,
            }
    print(f"  Enriched text entries: {len(enriched_text)}")

    # Step 3: Load CT.gov training lookup
    print("[LOAD] Loading CT.gov training data...")
    ctgov_lookup = {}
    if os.path.exists(CTGOV_TRAINING):
        with open(CTGOV_TRAINING) as f:
            ct_data = json.load(f)
            ctgov_lookup = ct_data.get("matched", {})
    print(f"  CT.gov matched events: {len(ctgov_lookup)}")

    # Step 4: Build drug timeline for prior readout detection
    print("[BUILD] Building drug timeline index...")
    drug_events = build_drug_timeline(events)
    print(f"  Unique drug keys: {len(drug_events)}")

    # Step 5: Process each event
    print(f"\n[EXTRACT] Processing {len(events)} events...")

    all_features = {}
    needs_manual_review = []

    interim_count = 0
    combined_dose_count = 0
    smart_money_count = 0
    small_n_count = 0

    for i, ev in enumerate(events):
        ticker = ev.get("ticker", "").strip()
        date = ev.get("date", "").strip()
        outcome = ev.get("outcome", "")
        phase = int(ev.get("phase", 2) or 2)

        # Get enriched text
        key = f"{ticker}|{date}"
        enriched = enriched_text.get(key, {})
        catalyst_text = enriched.get("catalyst_text", "")
        stage_text = enriched.get("stage", "") + " " + (ev.get("stage", "") or "")
        full_text = catalyst_text + " " + stage_text

        # Get price data
        try:
            ret_0d = float(ev.get("ret_0d", 0))
        except:
            ret_0d = 0
        try:
            ret_1d = float(ev.get("ret_1d", 0))
        except:
            ret_1d = 0

        # --- AUTO DETECT ---

        # 1. Interim detection
        is_interim, interim_conf, interim_evidence = detect_interim(full_text)

        # 2. Combined dose detection
        is_combined, combined_conf, combined_evidence = detect_combined_dose(full_text)

        # 3. Dose-response hints (for flagging)
        dose_hint_count, dose_hints = detect_dose_response_hints(full_text)

        # 4. Small N hints
        small_n_hint_count, small_n_hints_text = detect_small_n_hints(full_text)

        # 5. Stock reaction classification
        reaction_class, reaction_val = classify_stock_reaction(outcome, ret_0d, ret_1d)

        # 6. CT.gov N per arm
        ctgov_data = ctgov_lookup.get(str(i), {})
        n_per_arm, n_from_ctgov = estimate_n_per_arm(ctgov_data, phase)

        # 7. Prior readout detection
        drug = ev.get("drug", "")
        base_drug = re.split(r"\s*[-–]\s*\(", drug)[0].strip()
        drug_key = re.sub(r"[^a-z0-9]", "", base_drug.lower())[:30]
        prior_features = compute_prior_readout_features(i, date, drug_key, drug_events)

        # Compile features
        features = {
            # Auto-detected
            "is_interim": is_interim,
            "interim_confidence": round(interim_conf, 2),
            "interim_evidence": interim_evidence,
            "is_topline": 1 if not is_interim and interim_conf > 0.5 else 0,
            "is_combined_dose_text": is_combined,
            "combined_dose_confidence": round(combined_conf, 2),
            "n_per_arm_estimate": n_per_arm,
            "n_per_arm_from_ctgov": 1 if n_from_ctgov else 0,
            "is_small_n_lt20": 1 if n_per_arm < 20 else 0,
            "is_small_n_lt12": 1 if n_per_arm < 12 else 0,
            "stock_reaction_class": reaction_class,
            "stock_reaction_d0_pct": round(ret_0d, 2),
            "smart_money_rejection": 1 if "SMART_MONEY" in reaction_class else 0,
            **prior_features,

            # For v34 feature engineering (binary/numeric)
            "v34_is_interim": is_interim,
            "v34_n_per_arm_log": round(math.log(max(n_per_arm, 1)), 3),
            "v34_is_small_n": 1 if n_per_arm < 20 else 0,
            "v34_has_prior_readout": prior_features["has_prior_readout_same_drug"],
            "v34_days_since_prior_log": round(math.log(max(prior_features["days_since_prior_readout"], 1)), 3) if prior_features["days_since_prior_readout"] > 0 else 0,
            "v34_smart_money_flag": 1 if "SMART_MONEY" in reaction_class else 0,
            "v34_combined_dose_flag": is_combined,

            # Manual review fields (default 0 — to be filled in)
            "dose_response_inverted": 0,  # MANUAL
            "headline_is_combined_dose": is_combined,  # AUTO initial, MANUAL override
            "interim_pct_patients_evaluated": 0,  # MANUAL
            "cash_runway_months": 999,  # MANUAL
            "comparator_timepoint_matched": 0,  # MANUAL
            "analyst_downgrade_pre_readout": 0,  # MANUAL
        }

        # Compute IIS score (with auto-only features)
        iis_score, iis_tier, iis_flags = compute_iis_score(features)
        features["iis_score_auto"] = iis_score
        features["iis_tier_auto"] = iis_tier
        features["iis_flags"] = iis_flags

        all_features[key] = features

        # Track counts
        if is_interim:
            interim_count += 1
        if is_combined:
            combined_dose_count += 1
        if "SMART_MONEY" in reaction_class:
            smart_money_count += 1
        if n_per_arm < 20:
            small_n_count += 1

        # Flag for manual review if interim or has dose-response hints
        needs_review = False
        review_reasons = []

        if is_interim:
            needs_review = True
            review_reasons.append("IS_INTERIM")

        if dose_hint_count > 0:
            needs_review = True
            review_reasons.append(f"DOSE_HINTS: {dose_hints}")

        if "SMART_MONEY" in reaction_class:
            needs_review = True
            review_reasons.append(f"SMART_MONEY: D0={ret_0d:+.1f}%")

        if is_combined:
            needs_review = True
            review_reasons.append("COMBINED_DOSE_TEXT")

        if small_n_hint_count > 0:
            needs_review = True
            review_reasons.append(f"SMALL_N_HINTS: {small_n_hints_text}")

        if needs_review:
            needs_manual_review.append({
                "idx": i,
                "ticker": ticker,
                "date": date,
                "drug": drug,
                "outcome": outcome,
                "phase": phase,
                "catalyst_text": catalyst_text[:300],
                "review_reasons": review_reasons,
                "auto_iis_score": iis_score,
                "auto_iis_tier": iis_tier,
                "auto_flags": iis_flags,
            })

    # Step 6: Summary
    print(f"\n{'='*80}")
    print("IIS FEATURE EXTRACTION SUMMARY")
    print(f"{'='*80}")
    print(f"  Total events: {len(events)}")
    print(f"  Interim readouts detected: {interim_count} ({interim_count/len(events)*100:.1f}%)")
    print(f"  Combined dose text: {combined_dose_count}")
    print(f"  Smart money rejections: {smart_money_count}")
    print(f"  Small N (<20/arm): {small_n_count}")
    print(f"  Events flagged for manual review: {len(needs_manual_review)}")

    # IIS tier distribution (interims only)
    tier_counts = defaultdict(int)
    for key, f in all_features.items():
        tier_counts[f["iis_tier_auto"]] += 1

    print(f"\n  IIS Tier Distribution (auto-only scoring):")
    for tier in ["NOT_INTERIM", "IIS_TIER_1", "IIS_TIER_2", "IIS_TIER_3", "IIS_TIER_4"]:
        cnt = tier_counts.get(tier, 0)
        print(f"    {tier:15s}: {cnt:5d} ({cnt/len(events)*100:.1f}%)")

    # Validate against OCGN case — check how many interim + smart money cases had bad outcomes
    print(f"\n  Smart Money Rejection Validation:")
    smr_events = [(k, f) for k, f in all_features.items() if f["smart_money_rejection"]]
    if smr_events:
        # Find outcomes
        outcome_map = {f"{ev['ticker']}|{ev['date']}": ev['outcome'] for ev in events}
        smr_positive = sum(1 for k, f in smr_events if outcome_map.get(k) == "positive")
        smr_negative = sum(1 for k, f in smr_events if outcome_map.get(k) == "negative")
        print(f"    Total smart money rejections: {len(smr_events)}")
        print(f"    Called positive but sold off: {smr_positive} (outcome 'positive' but D0 <= -5%)")
        print(f"    Actually negative: {smr_negative}")
        print(f"    These are events where the market was smarter than the headline.")

    # Step 7: Write outputs
    print(f"\n[WRITE] Writing outputs...")

    # Auto features
    with open(OUTPUT_AUTO, "w") as f:
        json.dump(all_features, f, indent=2, default=str)
    print(f"  Auto features: {OUTPUT_AUTO}")

    # Manual review
    with open(OUTPUT_MANUAL, "w") as f:
        json.dump(needs_manual_review, f, indent=2, default=str)
    print(f"  Manual review: {OUTPUT_MANUAL} ({len(needs_manual_review)} events)")

    # V34 training features CSV
    v34_cols = [
        "v34_is_interim", "v34_n_per_arm_log", "v34_is_small_n",
        "v34_has_prior_readout", "v34_days_since_prior_log",
        "v34_smart_money_flag", "v34_combined_dose_flag",
        "iis_score_auto",
    ]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "date"] + v34_cols)
        for ev in events:
            key = f"{ev['ticker']}|{ev['date']}"
            feat = all_features.get(key, {})
            row = [ev["ticker"], ev["date"]] + [feat.get(c, 0) for c in v34_cols]
            writer.writerow(row)
    print(f"  V34 training CSV: {OUTPUT_CSV}")

    # Show some high-IIS interim events
    print(f"\n  Top IIS-Scored Interims (auto-detected):")
    interim_events = [(k, f) for k, f in all_features.items() if f["is_interim"]]
    interim_events.sort(key=lambda x: -x[1]["iis_score_auto"])
    for key, feat in interim_events[:20]:
        ticker = key.split("|")[0]
        date = key.split("|")[1]
        print(f"    IIS={feat['iis_score_auto']:3d} {feat['iis_tier_auto']:10s}  {ticker:8s} {date}  "
              f"N/arm={feat['n_per_arm_estimate']:4d}  SmartMoney={feat['smart_money_rejection']}  "
              f"Flags={feat['iis_flags']}")

    print(f"\n[DONE] IIS feature extraction complete.")
    print(f"  Next steps:")
    print(f"  1. Review {OUTPUT_MANUAL} — annotate dose_response_inverted, cash_runway, etc.")
    print(f"  2. Merge {OUTPUT_CSV} into v34 training pipeline")
    print(f"  3. Retrain Gungnir v34 with IIS features")

    return 0


if __name__ == "__main__":
    sys.exit(main())
