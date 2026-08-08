# ODIN v9.4 - Perplexity Calibration Fixes

## Changes from v9.1 Champion

| Fix | Issue | v9.1 Value | v9.4 Value | Impact |
|-----|-------|------------|------------|--------|
| #1 | Constraint feasibility | 34.1% | Kept + safeguard | Optimizer health |
| #2 | CRL count multiplier | None | 1.0/1.2/1.5x | RCKT 2 CRLs |
| #2 | Gene therapy penalty | None | -0.06 | Modality risk |
| #3 | ADCOM mid threshold | Implicit | Explicit 0.50 | Granularity |
| #4 | Modality-indication | None | Full matrix | Drug-specific |
| #5 | Indication overrides | None | 6 overrides | Specific drugs |
| #6 | Orphan weight | 0.0377 | 0.04 | Restored |
| #7 | Class2 resubmission | -0.0512 penalty | +0.04 boost | Direction fix |

## Validation Results

| Case | v9.3 (broken) | v9.4 | Target | Status |
|------|---------------|------|--------|--------|
| RCKT | 83% | 72.4% | 70-75% | ✅ |
| BMY | Correct | 99% | 90%+ | ✅ |
| Standard | Correct | 85.1% | ~85% | ✅ |
| Pain Mgmt | Unknown | 58.0% | 55-65% | ✅ |

## RCKT Breakdown (v9.4)

```
Base approval rate:           86.7%
+ orphan:                     +4.0%
+ priority_review:            +8.5%
- prior_crl (2 CRLs × 1.2):   -7.2%
+ class2_resubmission:        +4.0%
- inexperienced_sponsor:      -5.0%
- manufacturing_risk:         -4.0%  (reduced for gene therapy)
- modality_complexity:        -6.0%
- therapeutic_area:           -3.6%
- modality_indication:        -2.0%
- indication_override:        -3.0%
─────────────────────────────────────
TOTAL ADJUSTMENT:            -14.3%
FINAL PREDICTION:             72.4%
```

## Files

- `ODIN_v94_CONFIG.json` - Configuration file
- `odin_v94_scoring.py` - Scoring module

## Usage

```python
from odin_v94_scoring import score_event, batch_score

# Single event
result = score_event(event_dict)
print(f"Probability: {result['probability']:.1%}")
print(f"Tier: {result['tier']}")

# Batch scoring
df_scored = batch_score(df)
```
