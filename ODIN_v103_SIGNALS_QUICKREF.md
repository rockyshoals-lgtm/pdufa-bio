# ODIN v10.3 Signals Quick Reference

## Signal Summary

| Signal | Name | Weight Range | Calibration Source |
|--------|------|--------------|-------------------|
| **S23** | Insider Trading | 0.00 to **-0.10** | AQST Jan 2026 CRL |
| **S6** | Commercial Hiring | +0.02 to **-0.05** | PHAR Jan 2026 CRL |

---

## S23: Insider Trading Signal (AQST-Calibrated)

### Key Insight
**Insider selling is asymmetrically bearish** - selling signals are far more predictive than buying signals. AQST's coordinated C-suite selling was detectable 2-3 months before FDA deficiency letter disclosure.

### Trigger Thresholds (ANY triggers elevated scrutiny)

| ID | Trigger | Threshold | AQST Example |
|----|---------|-----------|--------------|
| T1 | Cumulative selling | >10% holdings in 6mo | COO sold 35% |
| T2 | Single transaction | >8% holdings | COO sold 20% Oct 15 |
| T3 | C-suite cluster | 2+ execs in 30-day window | 3 C-suite Sep-Oct |
| T4 | Same-day cluster | 3+ insiders same day | Oct 15: COO, CMO, SVP |
| T5 | No purchases | $500K+ sells, zero buys | $1.69M sells, 0 buys |
| T6 | Cluster → quiet | Selling 60-120d pre-PDUFA, then silence | Sep-Oct sales, Nov-Dec quiet |

### Score Weights

| Triggers Fired | Risk Level | Score Adjustment |
|----------------|------------|------------------|
| 0 | LOW | 0.00 |
| 1 | ELEVATED | **-0.03** |
| 2-3 | HIGH | **-0.06** |
| 4+ | CRITICAL | **-0.10** |

### Example: AQST Would Have Triggered 6/6

```
T1_CUMULATIVE: COO Jane Jung sold 35% cumulative holdings
T2_SINGLE_TXN: Oct 15 transaction = 20% of holdings
T3_CSUITE_CLUSTER: 3 C-suite in 30-day window
T4_SAME_DAY: 3 insiders (COO, CMO, SVP) on Oct 15, 2025
T5_NO_BUYS: $1,365,000 in sales, ZERO purchases
T6_CLUSTER_QUIET: Sep-Oct selling, Nov-Dec quiet period

Result: CRITICAL (-0.10)
Warning lead time: 2+ months before Jan 9 deficiency letter
```

---

## S6: Commercial Hiring Signal (PHAR-Calibrated)

### Key Insight
**Must distinguish NDA from sNDA.** PHAR's CRL for a pediatric label expansion (sNDA) does NOT validate "hiring void" hypothesis because existing commercial infrastructure (54 sales reps) made additional hiring unnecessary.

### NDA/BLA Thresholds (New Product Launch)

| Role | Bullish | Neutral | Bearish (VOID) |
|------|---------|---------|----------------|
| CCO/Commercial Leadership | ≥18mo before PDUFA | 12-18mo | <12mo or none |
| Medical Science Liaisons | ≥12mo before | 6-12mo | <6mo or none |
| Market Access | ≥15mo before | 9-15mo | <9mo or none |
| Sales Force | ≥6mo before | At approval | After approval only |

### Score Weights for NDA

| Pattern | Risk Level | Score |
|---------|------------|-------|
| Strong preparation (3-4 categories bullish) | LOW | **+0.02** |
| Adequate preparation | LOW | 0.00 |
| Weak (1 void) | ELEVATED | -0.025 |
| **Hiring void (2+ voids)** | HIGH | **-0.05** |

### sNDA/sBLA Adjustment (Label Expansion)

For sNDAs with existing commercial infrastructure:
- **Maintenance hiring = NEUTRAL** (not bearish)
- Commercial team protected in restructuring = NEUTRAL
- CCO transition = NEUTRAL
- **Only explicit commercial pullback = BEARISH (-0.02)**

### Example: PHAR Correctly Scores Neutral

```
Application: sNDA (Joenja pediatric ages 4-11)
Existing infrastructure: 54 US sales reps
CCO: New CCO Leverne Marsh hired effective Jan 1, 2026
Commercial team: Protected during Oct 2025 restructuring

Result: LOW RISK (0.00)
Rationale: sNDA with existing commercial infrastructure
```

---

## Implementation Checklist

### Data Collection (T-1 Compliant)

**S23 Insider Trading:**
- [ ] SEC Form 4 filings via FinBrain API
- [ ] 6-month lookback from PDUFA date
- [ ] All insiders, flag C-suite separately
- [ ] Track shares held before/after for % calculation

**S6 Commercial Hiring:**
- [ ] LinkedIn/Indeed job postings
- [ ] Determine application type (NDA vs sNDA)
- [ ] For sNDA: verify existing commercial infrastructure
- [ ] Track posting dates relative to PDUFA

### Integration with ODIN Scoring

```python
from odin_v103_signals import (
    analyze_insider_trading,
    analyze_commercial_hiring,
    InsiderTransaction,
    CommercialHiringData,
    ApplicationType
)

# Get S23 score
s23_result = analyze_insider_trading(
    transactions=insider_transactions,
    pdufa_date=pdufa_date
)

# Get S6 score
s6_result = analyze_commercial_hiring(
    hiring_data=hiring_data,
    months_to_pdufa=months_to_pdufa,
    application_type=ApplicationType.NDA  # or SNDA
)

# Add to base ODIN probability
total_adjustment = s23_result.score_adjustment + s6_result.score_adjustment
adjusted_probability = base_probability + total_adjustment
```

---

## Validation Summary

| Case Study | Expected | Actual | Status |
|------------|----------|--------|--------|
| AQST insider selling | CRITICAL (-0.10) | 6/6 triggers, CRITICAL | ✅ |
| Normal insider pattern | LOW (0.00) | 0 triggers, LOW | ✅ |
| NDA hiring void | HIGH (-0.05) | 2 voids, HIGH | ✅ |
| sNDA existing infrastructure (PHAR) | LOW (0.00) | NEUTRAL | ✅ |

---

## Key Takeaway

> **Insider selling provides STRONGER bearish signal than commercial hiring provides bullish signal.**
> 
> Weight asymmetry reflects that insiders have information advantages about regulatory deficiencies, while commercial preparation cannot predict unknown technical FDA issues.
