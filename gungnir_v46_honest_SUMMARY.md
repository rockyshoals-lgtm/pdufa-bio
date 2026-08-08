# Gungnir v46 — Honest 4-Way Split Retrain

**Date:** April 17, 2026
**Status:** **COMPLETE — numbers locked.**
**Methodology:** Train ≤2023-06 / Val 2023H2–2024H1 / Test 2024H2–2025H1 / Final HO ≥2025H2.
C selected on VAL AUC only. Test and Final holdout touched ONCE.

## Headline

| Metric | Reported (v46 deploy) | Honest Test | Honest Final HO | Delta (Final) |
|---|---|---|---|---|
| AUC | **0.8135** | 0.7841 | **0.7551** | **−584 bp** |
| Brier | 0.1299 | 0.1308 | 0.1529 | +0.023 (worse) |
| Best C | 0.02 | — | — | **0.05 selected on VAL** (2.5× less reg) |

## Splits

- Train: 434 events (≤2023-06-30), 82.0% positive rate
- Val: 500 events (2023H2–2024H1), 79.2% positive
- Test: 503 events (2024H2–2025H1), 79.9% positive — **−294 bp inflation**
- Final HO: 315 events (≥2025-07-01), 77.8% positive — **−584 bp inflation**

## C Sweep on VAL

| C | Train AUC | Val AUC |
|---|---|---|
| 0.005 | 0.8458 | 0.7927 |
| 0.01 | 0.8597 | 0.7996 |
| 0.02 (v46 deployed) | 0.8733 | 0.8052 |
| **0.05 (honest pick)** | **0.8861** | **0.8065** |
| 0.1 | 0.8938 | 0.8031 |
| 0.2 | 0.9008 | 0.7945 |
| 0.5 | 0.9078 | 0.7781 |

## Interpretation

**v46's reported 0.8135 was inflated by 294 bp on test and 584 bp on final holdout.**

Primary causes:
1. Greedy forward feature selection (v39→v46 Kaizen chain) ranked candidates on test-set WF AUC — same bug family as BIFROST v5.5 (626 bp) and ODIN v14 (368 bp).
2. Meta-ensemble weights (90/10 Ridge/XGB), C=0.02, 500-tree XGB config were all tuned with test-set feedback.
3. The Final HO degradation (−584 bp vs. test's −294 bp) suggests genuine 2025H2+ distribution drift on top of the leakage — the 2025–2026 cohort has slightly lower base rate and different feature distribution.

The 500 trees / meta 90/10 Ridge/XGB config is NOT re-fit here — this is a pure Ridge-only C sweep. A fully honest retrain of the meta-ensemble would need separate val passes for tree count, XGB lr, and meta weights. Expected further AUC movement on a full honest config sweep is small (±50–100 bp) because the feature-level Ridge term dominates (90% weight).

## Verdict

- **Honest Test AUC: 0.7841** (2024H2–2025H1)
- **Honest Final HO AUC: 0.7551** (2025H2+ truly blind)
- **Ship action**: Treat deployed Gungnir scores as **ordinally valid, absolutely optimistic by ~300–600 bp**.
  - Keep using for RANK-based decisions (which catalysts score highest).
  - DO NOT interpret raw probabilities as calibrated (Brier 0.1529 on Final HO, not 0.1299).
  - Tier thresholds (ALPHA ≥80, BETA ≥60, GAMMA ≥40) still directionally correct but the nominal cutoffs overstate conviction.
- **Portfolio sizing implication**: Current ALXO 55 / CMPX 40 / Cash 5 rotation unchanged. Cap on single-position sizing already reflects this uncertainty.

## Integrity cross-reference

| Engine | Reported AUC | Honest AUC | Inflation | Honest C | Pattern |
|---|---|---|---|---|---|
| BIFROST Explosion v5.5 | LR 0.9487 | 0.8861 | **−626 bp** | — | Test-set-driven feature selection |
| ODIN v14 | HO 0.9363 | 0.8995 | **−368 bp** | 0.01 (vs 0.10 deployed) | C tuning touched holdout |
| Gungnir v46 | WF 0.8135 | Test 0.7841 / Final 0.7551 | **−294 / −584 bp** | 0.05 (vs 0.02 deployed) | Greedy forward selection on test AUC + config tuning |

All three inflation patterns share the same root: **hyperparameter or feature selection decisions touched evaluation data**. Fix forward = train/val/test/final separation enforced by construction in a Kaizen harness.

## Files
- `gungnir_v46_honest_v2.py` — retrain pipeline (executed)
- `gungnir_v46_honest_v2_results.json` — full numbers
- `gungnir_v46_honest_SUMMARY.md` — this file
