# ODIN Optimization Audit Report

**Audit Date:** 2026-01-23  
**Files Audited:** `best.json`, `hall_of_fame.json` (50 configs)  
**Dataset:** `ODIN_ENRICHED_PDUFA_1349_v2.csv` (1,349 events)  
**Config Version:** ODIN_v38a_patch12_hof_stats_meta

---

## Executive Summary

| Category | Status | Details |
|----------|--------|---------|
| Dataset Integrity | ✅ PASS | 1,349 rows, 1,169 approvals, 180 CRLs - all verified |
| Metric Calculations | ✅ PASS | All metrics (F1, MCC, precision, recall, specificity) verified |
| Confusion Matrix | ✅ PASS | TP+FN=1169, FP+TN=180 - consistent |
| T-1 Compliance | ⛔ **FAIL** | `manufacturing_risk` is leaked from post-decision CRL letters |
| Parameter Sanity | ⚠️ REVIEW | `p_base` at 96.67% vs 86.66% historical (intentional anchor) |

---

## 1. Dataset Validation ✅

```
PDUFA Dataset Summary:
  Total Events:  1,349
  Approvals:     1,169 (86.66%)
  CRLs:          180 (13.34%)
  
Model Claims Match: ✓ All counts verified
```

---

## 2. Best Configuration Metrics ✅

| Metric | Value | Verified |
|--------|-------|----------|
| F1 Score | 0.9303 | ✅ |
| Precision | 0.9600 | ✅ |
| Recall | 0.9025 | ✅ |
| Specificity | 0.7556 | ✅ |
| MCC | 0.5759 | ✅ |
| Brier Score | 0.0694 | ✅ |

### Confusion Matrix
```
                    Predicted
                 Approve    CRL
Actual Approve    1,055     114  (FN = 9.8%)
Actual CRL           44     136  (TN = 75.6%)
```

---

## 3. ⛔ CRITICAL: T-1 Compliance Violation

### The Problem: `manufacturing_risk` is Leaked Data

**Evidence:**

1. **Source Mismatch:**
   - `form_483_issues` = 0 True values (empty field)
   - `manufacturing_risk` = 285 True values
   - **Conclusion:** manufacturing_risk is NOT from pre-PDUFA Form 483 inspections

2. **Impossible Predictive Power:**
   - CRL rate when `mfg_risk=True`: **47.7%** (136/285)
   - CRL rate when `mfg_risk=False`: **4.1%** (44/1064)
   - **Lift: 11.5x** — This is impossibly high for pre-decision data

3. **Perfect FP Alignment:**
   - Model's irreducible FP = 44
   - CRLs without manufacturing_risk = 44
   - **Exact match** confirms mfg_risk is the sole CRL discriminator

4. **CRL Notes Confirm Source:**
   ```
   mfg_risk=True CRLs with CMC/manufacturing in notes: 24
   Sample notes: "Chemistry, Manufacturing, Controls..."
   ```

### The Leakage Mechanism

```
POST-DECISION DATA (leaked)           PRE-DECISION DATA (valid)
─────────────────────────────         ────────────────────────────
CRL letter says "CMC issues"   →      Form 483 inspection findings
manufacturing_risk = True       ✗      form_483_issues = True ✓

The field was populated AFTER knowing the FDA decision,
making it useless for live prediction.
```

### Impact Assessment

| Scenario | Specificity | F1 | Notes |
|----------|-------------|-----|-------|
| With mfg_risk (current) | 75.6% | 0.93 | Artificially inflated |
| Without mfg_risk (realistic) | ~24% | ~0.85 | 136 TN → FP |

---

## 4. Parameter Analysis

### Key Parameters (Best Config)

| Parameter | Value | Interpretation |
|-----------|-------|----------------|
| `p_base` | 0.9667 | Mathematical anchor (not probability) |
| `p_threshold` | 0.8726 | Decision boundary |
| `w_mfg_pen` | **-0.7200** | ⚠️ Near-binary classifier (LEAKED) |
| `w_adcom` | +0.3612 | Strong AdCom influence |
| `w_priority` | +0.1420 | Priority Review boost |
| `w_fast` | +0.1134 | Fast Track boost |
| `w_btd` | +0.1031 | BTD boost |
| `w_accel` | +0.0839 | Accelerated Approval boost |

### Therapeutic Area Adjustments

| Area | Adjustment | Direction |
|------|------------|-----------|
| Infectious Disease | +0.2626 | Favorable |
| Oncology | +0.2077 | Favorable |
| CNS | +0.0252 | Slight favorable |
| Pain | -0.0836 | Unfavorable |

---

## 5. Hall of Fame Consistency ✅

```
Total Configs: 50
All trained on same dataset: ✓
Data fingerprint consistent: ✓

Metric Ranges:
  F1:          0.9155 - 0.9308
  Brier:       0.0694 - 0.0697
  MCC:         0.5288 - 0.5775
  Specificity: 0.7556 (constant)
  FP:          44 (constant across ALL configs)
```

**Note:** The constant FP=44 confirms these are the "irreducible" CRLs that lack the leaked manufacturing_risk flag.

---

## 6. Recommendations

### Immediate Actions

1. **Remove `manufacturing_risk` from scoring**
   - Set `w_mfg_pen = 0` and `w_mfg_amp = 0`
   - Re-run optimization

2. **Populate `form_483_issues` with T-1 compliant data**
   - Source: FDA Form 483 inspection database (pre-PDUFA)
   - Source: FDA Warning Letters database
   - Source: Import Alert database

3. **Add alternative pre-PDUFA CMC signals**
   - CDMO shipping data (supply chain signals)
   - Prior CMC-related CRLs for same facility
   - Public FDA inspection classifications (OAI/VAI/NAI)

### Re-Optimization Expected Outcomes

| Metric | Current (Leaked) | Expected (Clean) |
|--------|------------------|------------------|
| F1 | 0.93 | 0.85-0.88 |
| Specificity | 75.6% | 25-40% |
| Precision | 96.0% | 90-92% |

---

## 7. Files Verified

| File | Status | Notes |
|------|--------|-------|
| `best.json` | ✅ Valid structure | Champion config |
| `hall_of_fame.json` | ✅ Valid structure | 50 configs |
| `ODIN_ENRICHED_PDUFA_1349_v2.csv` | ✅ Correct counts | T-1 issue in mfg_risk |
| `lunarcrush_cache.json` | ✅ 100% coverage | 298 tickers, ready for merge |

---

## Appendix: The 44 Irreducible FPs

These CRLs have NO manufacturing_risk flag and represent the model's prediction floor:

1. Eli Lilly - JARDIANCE (T1D) - 3/20/2020
2. AbbVie - ABICIPAR (AMD) - 6/26/2020  
3. Merck - KEYTRUDA+LENVIMA (HCC) - 7/8/2020 [BTD+Orphan+Priority]
4. Gilead - Filgotinib (RA) - 8/18/2020
5. Merck - KEYTRUDA (SCLC) - 3/1/2021 [BTD+Orphan+Priority]
6. Merck - KEYTRUDA (TNBC) - 3/29/2021 [BTD+Orphan+Priority]
7. Sanofi - TZIELD (T1D) - 7/6/2021
8. Incyte - Zynyz (Anal Cancer) - 7/23/2021
9. AstraZeneca - Roxadustat (CKD Anemia) - 8/11/2021
10. Takeda - Eohilia (EoE) - 12/21/2021

**Pattern:** Many have strong designation stacks but failed on safety/efficacy grounds that current features don't capture.

---

*Report generated by Claude ODIN Research Authority*
