"""
Cross-Engine Integration Scorecard (April 2026)
================================================

Purpose
-------
The 9Realms stack now has 9+ scoring engines (ODIN, Gungnir, BIFROST v4 timing,
BIFROST Explosion v5.5, BIFROST Options v1.2→v1.3, Conference Overlay, Smart
Money, UOA, SENTINEL, MJOLNIR). Each was kaizen'd independently. This scorecard
answers:

  * Which overlays COMPOUND vs CANCEL each other?
  * What is each engine's HONEST (not inflated) AUC?
  * What is each engine's proper USAGE (rank-only vs calibrated probability)?
  * Which combinations are empirically supported by backtests?
  * Where are the orthogonality gaps?

Output: /sessions/confident-serene-ptolemy/mnt/9realms/cross_engine_scorecard.json
"""

import json
from pathlib import Path

OUT_PATH = Path("/sessions/confident-serene-ptolemy/mnt/9realms/cross_engine_scorecard.json")

scorecard = {
    "version": "1.0.0",
    "generated": "2026-04-18",
    "purpose": "Honest integration map of every 9Realms scoring engine after overnight kaizen.",

    "engines": {

        "ODIN_v14": {
            "domain": "PDUFA outcome probability (approve vs CRL)",
            "reported_auc": 0.9363,
            "honest_auc":   0.8995,
            "inflation_bp": 368,
            "inflation_cause": "C hyperparameter selected on holdout during kaizen",
            "status": "DEPLOYED in MCP (rankings valid, probabilities optimistic)",
            "usage": "Use for RANKING PDUFAs. Do not trust absolute probability for Kelly sizing. T1 vs T4 ordinal gap is real.",
            "superseded_by": "ODIN_v15 honest (test AUC 0.870 under 3-way split discipline) — not yet promoted to MCP"
        },
        "ODIN_v15_honest": {
            "domain": "PDUFA outcome — honest 3-way split",
            "honest_test_auc":  0.870,
            "honest_val_auc":   0.855,
            "honest_brier":     0.127,
            "best_C": 0.25,
            "n_features": 50,
            "new_features_vs_v14": ["chembl_biologic"],
            "status": "BUILT, logged in 9realms, NOT YET DEPLOYED to MCP",
            "usage": "Reference model for honest calibration baseline. Promote when next MCP refresh ships.",
            "next": "v16 kaizen: mine untapped CT.gov + ChEMBL columns (ct_num_arms, ct_is_double_blind, ct_has_dmc, chembl_first_in_class) under strict 3-way split"
        },
        "Gungnir_v46": {
            "domain": "Phase readout outcome probability (positive vs negative/flat)",
            "reported_auc":      0.8135,
            "honest_test_auc":   0.7841,
            "honest_final_ho_auc": 0.7551,
            "inflation_bp": 294,
            "inflation_cause_bp_v2": 584,
            "inflation_cause": "Greedy forward feature selection + C tuning touched validation/test sets",
            "status": "DEPLOYED in MCP (rankings valid)",
            "usage": "Use for RANKING readouts. Phase 1/2 positive prediction is strongest sub-signal.",
            "next": "v47 honest rebuild with enriched_gungnir_dataset_v3.csv under strict 3-way split"
        },
        "BIFROST_v4_timing": {
            "domain": "Runup entry/exit window + magnitude prediction + Kelly sizing",
            "wf_sharpe": 5.45,
            "wf_win_rate": 70.8,
            "wf_max_dd_pct": -4.9,
            "note": "v5_tier dependency confirmed leaked — outcome-conditional separation perfect 2020-2025. DROP v5_tier as a filter; re-score under v14/v15 with strict T-1.",
            "status": "DEPLOYED with caveat",
            "usage": "Timing + sizing rules reliable; v5_score filter must be replaced with v14 filter.",
            "next": "Retrain BIFROST v4.1 with ODIN v15 honest tiers (not v9/v10)."
        },
        "BIFROST_Explosion_v5_5": {
            "domain": "Post-PDUFA |D1 move| > 25% probability",
            "reported_auc": 0.9487,
            "honest_auc":   0.8861,
            "inflation_bp": 626,
            "inflation_cause": "Greedy forward selection on test AUC",
            "status": "DEPLOYED, rankings valid",
            "v56_attempt": "v5.6 P3 failed (-70bp)",
            "usage": "Position-sizing MULTIPLIER only. 2.0x SNIPER, 1.5x ELEVATED, 1.0x NORMAL, 0.8x QUIET.",
            "next": "v5.7 kaizen — test IV/term-structure features, historical SI proxy, conference × ODIN interactions"
        },
        "BIFROST_Options_v1_3": {
            "domain": "Options P&L edge on catalyst runup (T-14 → T-1 ATM calls)",
            "honest_n_trades": 804,
            "headline_finding": "The advertised PDUFA Small/Mid Approve strategy DOES NOT beat zero at any honest fill level. The ONE robust edge is Phase 1/2 positive readout ATM T-14→T-1.",
            "sole_robust_edge": {
                "name": "Phase 1/2 positive readout",
                "n": 36,
                "mid_avg_pct": 45.09,
                "real_40_avg_pct": 33.73,
                "mid_ci_95": [12.0, 80.4],
                "win_pct": 58.3,
                "ex_top5_mid_pct": 16.4,
                "robustness": "CI entirely above zero at MID and REAL_40; survives top-5 trim"
            },
            "new_v13_discovery_1_odin_inversion": {
                "T1_plus_T2_PDUFA_MID_pct": -6.73,
                "T3_plus_T4_PDUFA_MID_pct": +14.32,
                "gap_pp": 21.05,
                "interpretation": "ODIN tier is INVERTED for options. Premium pays for uncertainty, not quality. Never filter options entries by ODIN tier."
            },
            "new_v13_discovery_2_iv_cheapness_fails": {
                "Q1_cheapest_iv_avg_pct": 21.8,
                "Q1_mid_return_pct": -19.88,
                "Q5_priciest_iv_avg_pct": 187.8,
                "Q5_mid_return_pct": +9.61,
                "interpretation": "Low-IV options are deep-OTM lottery tickets that expire worthless. 'IV cheapness' as sole entry filter is WRONG."
            },
            "new_v13_discovery_3_oi_sweet_spot": {
                "oi_lt_50_mid_pct":    +3.87,
                "oi_100_500_mid_pct":  +9.98,
                "oi_500_2000_mid_pct": -14.67,
                "oi_gte_2000_mid_pct": -14.51,
                "interpretation": "OI 100-500 is the sweet spot. High-OI options (>=500) are large-cap hedging flow with negative edge. Avoid."
            },
            "new_v13_discovery_4_lotto_micro": {
                "name": "LOTTO_micro_PDUFA_liquid (cap_tier in micro/nano, OI>=50, spread<=30)",
                "n": 32,
                "mid_pct": +56.23,
                "real_40_pct": +37.58,
                "mid_ci_95": [8.6, 110.2],
                "ex_top5_mid_pct": +1.15,
                "win_pct": 59.4,
                "caveat": "Robust to top-5 trim (barely positive ex-top-5). Live only at small size (1% max)."
            },
            "new_v13_discovery_5_iv_change_is_the_real_signal": {
                "q1_most_crush_mid_pct":  -14.56,
                "q5_most_expand_mid_pct": +17.36,
                "q5_ci_95": [3.0, 31.6],
                "interpretation": "IV expansion drives option P&L. Ex-post obvious but confirms options edge ≈ positioning before IV pop."
            },
            "status": "UPDATED. v1.3 results logged in 9realms. v1.2 memo remains canonical external document.",
            "next": "Promote LOTTO_micro + CORE_Phase12 as live playbooks. Kill ODIN tier filter for options."
        },
        "Conference_Overlay_v1": {
            "domain": "Conference presentation multiplicative boost",
            "signal_strength": "+13.5% positive rate lift (90.2% vs 76.7%, p=7.88e-21)",
            "status": "DEPLOYED, robust signal",
            "usage": "Apply AFTER Gungnir scoring. Multiplicative (not additive).",
            "compounds_with": ["Smart_Money_v1", "BIFROST_v4_timing"],
            "cancels_with": [],
            "next": "Integrate as a PROPER Gungnir feature (v47 candidate)."
        },
        "Smart_Money_v1": {
            "domain": "Institutional/insider conviction multiplicative boost",
            "components": ["God Tier funds", "insider buys", "analyst consensus", "structural (fallen angel / confirmatory)"],
            "status": "DEPLOYED, anecdotally validated (KOD, ALXO, CABA)",
            "usage": "Apply AFTER ODIN/Gungnir. Multiplicative.",
            "compounds_with": ["Conference_Overlay_v1", "BIFROST_v4_timing"],
            "cancels_with": ["UOA_v1_1 QUIET_BULLISH (both mean 'retail' — do not double-penalize)"],
            "next": "Automate data ingestion (FinBrain MCP Pydantic bug blocks this)."
        },
        "UOA_v1_1": {
            "domain": "Unusual options activity boost/penalty",
            "backtest_n": 976,
            "backtest_source": "ORATS T-14 snapshots",
            "status": "DEPLOYED, calibrated",
            "gold_signal": "ELEVATED × MIXED (88.2% approval, n=51, +16.5 pp lift, +12% boost)",
            "penalty_signal": "QUIET × BULLISH (63.0% approval, n=108, -8.8 pp lift, -8% penalty — retail noise)",
            "usage": "Apply AFTER ODIN/Gungnir. Multiplicative.",
            "compounds_with": ["Smart_Money_v1 (when NOT QUIET×BULL)"],
            "cancels_with": ["ODIN tier filter for OPTIONS (UOA signal != ODIN signal)"],
            "next": "Automate ORATS live scan; test as Gungnir feature."
        },
        "SENTINEL_v1_1": {
            "domain": "Alt-data 7-component overlay",
            "honest_2025_auc": 0.50,
            "best_component_auc": 0.523,
            "status": "RANK-ONLY (do not modify probabilities)",
            "usage": "Tie-breaker WITHIN existing tiers. Do not use as probability modifier.",
            "caveat": "Honest 2025 holdout showed near-random AUC. Raw-sum combiner is noise.",
            "next": "Either find orthogonal data source or retire."
        },
        "MJOLNIR_v1": {
            "domain": "Entry timing (alternative to BIFROST v4 static matrix)",
            "honest_performance": "Did not outperform BIFROST v4 baseline under 3-way split",
            "status": "NOT DEPLOYED",
            "next": "Needs rewrite or retirement."
        },
        "IIS_v1": {
            "domain": "Interim inflation / small-N flag",
            "components": ["INVERTED_DOSE_RESPONSE (manual)", "TINY_N_INTERIM (auto)", "EARLY_REPORTER_BIAS (auto)", "COMBINED_DOSE_HEADLINE (NLP)", "ANALYST_DOWNGRADE (manual)", "CASH_RUNWAY_PRESSURE (manual)"],
            "status": "DEPLOYED as OVERLAY (not Gungnir feature)",
            "usage": "Flag interim-inflated readouts. IIS_HIGH (46+) = NO TRADE.",
            "next": "Test as Gungnir v47 feature (subset that auto-detects)."
        }
    },

    "integration_matrix": {
        "description": "How to stack engines for a single catalyst. Rows = signal engine, Cols = trade style.",
        "PDUFA_equity": [
            "1. ODIN v14/v15 → tier + probability (RANK ONLY for probability)",
            "2. BIFROST v4 → entry window + Kelly size (replace v5_score filter with v14 tier)",
            "3. BIFROST Explosion v5.5 → position SIZE MULTIPLIER (2x/1.5x/1x/0.8x)",
            "4. Smart Money Overlay → multiplicative boost 0-30%",
            "5. Conference Overlay → multiplicative boost 0-20% (if conference adjacent)",
            "6. UOA Overlay → multiplicative boost/penalty -8% to +12%",
            "7. SENTINEL → tie-breaker within tier (ranking only)"
        ],
        "PDUFA_options": [
            "1. SKIP ODIN as entry filter — tier is INVERTED for options.",
            "2. Use cap_tier filter: micro/nano only (LOTTO_micro playbook) with OI>=50, spread<=30, 1% max size.",
            "3. Small/mid/large PDUFA options: AVOID (v1.3 shows negative edge at all honest fills).",
            "4. BIFROST Explosion v5.5 — SNIPER (>=20% prob) can bump size ceiling from 1% to 2%.",
            "5. Never trade large-cap PDUFA options (theta destroys)."
        ],
        "Readout_equity": [
            "1. Gungnir v46 → probability + tier (RANK ONLY)",
            "2. Conference Overlay (if applicable) — compounds reliably",
            "3. Smart Money Overlay",
            "4. UOA Overlay",
            "5. IIS Overlay — HIGH = NO TRADE regardless of other scores"
        ],
        "Readout_options": [
            "1. SKIP ODIN (doesn't apply to readouts anyway).",
            "2. CORE EDGE = Phase 1/2 positive readout ATM T-14 → T-1. MID +45%, REAL_40 +34%, n=36, win 58.3%.",
            "3. Gungnir v46 filter: probability >= 0.70 (refine with v47 honest).",
            "4. OI >= 100, spread <= 25%, entry_iv_pct 40-180 (mid quintiles).",
            "5. Size 1-3% based on Gungnir probability. No BIFROST Explosion multiplier for readouts (not trained on readouts).",
            "6. Phase 2b, Phase 3 positive, Phase 2a = AVOID (v1.3 confirms negative).",
            "7. EXIT T-1. Never hold through."
        ]
    },

    "orthogonality_map": {
        "description": "Do the overlay signals correlate or are they orthogonal?",
        "confirmed_orthogonal_pairs": [
            ["Conference_Overlay_v1", "Smart_Money_v1"],
            ["Conference_Overlay_v1", "UOA_v1_1"],
            ["BIFROST_Explosion_v5_5", "ODIN_v14 probability"],
            ["IIS_v1", "everything else (IIS is a veto, not a probability)"]
        ],
        "correlated_pairs_be_careful": [
            ["Smart_Money_v1 (institutional)", "UOA_v1_1 (ELEVATED tiers)", "both respond to institutional positioning — do not double-count"],
            ["SENTINEL social component", "UOA_v1_1 QUIET_BULLISH", "both can signal retail hype"],
            ["Conference_Overlay_v1", "Gungnir v46 conference feature (v40+)", "v46 already has conference — overlay is a small residual lift"]
        ],
        "dangerous_stacks": [
            "Smart_Money + UOA + SENTINEL all firing at max → likely >30% combined boost. Cap at +25% total multiplicative boost on any single position."
        ]
    },

    "honest_calibration_discipline": {
        "rule_1": "Three-way split (train ≤ year-2, val year-1, test year 0). No hyperparameter tuning on val+test merged.",
        "rule_2": "Greedy forward selection done on validation ONLY, never test.",
        "rule_3": "Every backtest segment reports MID + REAL_40 side-by-side with bootstrap 95% CI (n_boot=2000, seed=42).",
        "rule_4": "Segments n < 30 flagged not-live-tradeable.",
        "rule_5": "Top-5 trim robustness check for every edge claim.",
        "rule_6": "Probability outputs for ranking ONLY unless model was trained under rule_1 and calibration Brier was computed on test."
    },

    "next_kaizen_priorities": [
        "ODIN v16: mine untapped CT.gov (ct_num_arms, ct_is_double_blind, ct_has_dmc, ct_log_num_sites) + ChEMBL (chembl_first_in_class, chembl_target_class) columns under 3-way split",
        "Gungnir v47: honest rebuild with enriched_gungnir_dataset_v3.csv + conference as PROPER feature (not overlay) + IIS auto-detected subset",
        "BIFROST v4.1: retrain with ODIN v15 honest tiers (kill v5_score leak)",
        "BIFROST Explosion v5.7: IV/term-structure features, historical SI proxy, conference × ODIN interactions",
        "Options v1.4: survivorship bias check (nano caps, illiquid strikes), ORATS term-structure tilt as alt filter, regime-specific playbooks",
        "SENTINEL v2: find orthogonal data source (13F changes, FDA calendar leaks, analyst consensus dynamics) or retire"
    ]
}

OUT_PATH.write_text(json.dumps(scorecard, indent=2, default=str))
print(f"WROTE: {OUT_PATH}")
print(f"size: {OUT_PATH.stat().st_size:,} bytes")
print()
print("Engines mapped:", len(scorecard["engines"]))
print("Integration stacks:", len(scorecard["integration_matrix"]) - 1)
print("Next kaizen priorities:", len(scorecard["next_kaizen_priorities"]))
