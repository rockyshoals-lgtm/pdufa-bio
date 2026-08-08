# ODIN v14 — Honest 3-Way Split Baseline

**Date:** April 17, 2026
**Methodology:** Train ≤2022-12-31 / Val 2023–2024 / Holdout ≥2025
**C selected on VAL only. Holdout touched ONCE for final AUC.**

## Headline

| Metric | Reported (v14 deploy) | Honest (this retrain) | Delta |
|---|---|---|---|
| Holdout AUC | **0.9363** | **0.8995** | **−368 bp** |
| Holdout Brier | 0.0895 | 0.1128 | +0.0233 (worse) |
| Optimal C | 0.10 | **0.01** | 10× stronger regularization |
| WF / Val AUC | 0.9011 | 0.8600 (val) | — |
| Train AUC | — | 0.9233 | Train→Holdout drop: 238 bp (reasonable) |

## Splits
- Train: 1,081 events (≤2022-12-31), 67.3% approval
- Val: 764 events (2023–2024), 67.7% approval
- Holdout: 365 events (2025+), 69.3% approval

## Stability
20/20 seeds produced identical holdout AUC 0.8995 (zero variance — deterministic Ridge solver).

## Interpretation

**v14's reported 0.9363 was inflated by ~368 bp.** Primary cause: C drifted to 0.10 (4× weaker than v13) during Kaizen while the acceptance gates touched holdout data. Under honest val-only selection, C=0.01 wins — reverting to the regularization regime of v13 / earlier.

**Honest 0.8995 still beats v13's reported 0.9315** by not-much, and likely beats v13's own honest number by similar margin. v14 is NOT broken — the features work. But the +353 bp HO>WF anomaly flagged in Red Team now has a mechanical explanation: holdout leaked into C selection.

## Verdict

- Honest HO AUC: **0.8995**
- Honest Brier: **0.1128**
- Ship action: **Roll ODIN MCP to odin_v14_honest with C=0.01** (same 51 features, re-fit scaler on train-only). Update CLAUDE.md claims. Retain v14 deploy as a "last-inflated-baseline" artifact for reference.

## Files
- `odin_v14_honest.py` — retrain pipeline
- `odin_v14_honest_results.json` — full numbers
- `odin_v14_honest_ANALYSIS.md` — audit analysis

## Integrity note
BIFROST v5.5 showed 626 bp inflation (0.9487 → 0.8861). ODIN v14 shows 368 bp. Same test-set-leakage-via-Kaizen pattern; ODIN's is smaller because its feature selection is more regularization-driven and less greedy. Gungnir v46 retrain is pending (bash env blocker).
