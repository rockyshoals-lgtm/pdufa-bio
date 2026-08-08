# ODIN Dataset Integrity Report

**Generated:** 2026-01-24  
**Dataset:** ODIN_ENRICHED_PDUFA_1349_v2.csv  
**Version:** 8.12 (P001 Corrected)

---

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| Total PDUFA Events | 1,349 | ✓ |
| Approvals | 1,169 (86.7%) | ✓ |
| CRLs | 180 (13.3%) | ✓ |
| Resubmissions Detected | 106 | ✓ |
| LunarCrush Coverage | 4.7% | ⚠ |

### 🚨 CRITICAL FINDING: P001 Signal Miscalibration

| Signal | Claimed | Actual | Impact |
|--------|---------|--------|--------|
| P001 (Class 1 CMC Resubmission) | 99.5% approval | **69.4% approval** | REMOVED override, converted to PENALTY |

---

## A) Data Integrity Audit

### Row Count Verification
- **Expected:** 1,349 PDUFA events
- **Actual:** 1,349 PDUFA events ✓
- **Duplicates:** None detected

### Outcome Distribution
| Outcome | Count | Percentage |
|---------|-------|------------|
| APPROVAL | 1,169 | 86.7% |
| CRL | 180 | 13.3% |

### Date Range
- **Earliest:** 2020-01-08
- **Latest:** 2026-01-14
- **Future events (2026):** 4 events (prospective targets)

---

## B) Resubmission Detection (CRITICAL FIX)

### Problem Identified
Raw CSV had `prior_crl=FALSE` and `resubmission_class=NaN` for ALL 1,349 events.

### Solution Implemented
Event chain analysis to detect resubmissions by tracking same asset+company over time.

### Results
| Category | Count | Approval Rate | vs Baseline |
|----------|-------|---------------|-------------|
| First Cycle | 1,243 | 87.9% | +1.2pp |
| Class 1 CMC Resubmission | 72 | **69.4%** | -17.3pp |
| Class 2 Clinical Resubmission | 34 | 79.4% | -7.3pp |

### P001 Signal Correction
```
OLD CONFIG (WRONG):
  p001_override: 0.995  # Claims 99.5% approval

NEW CONFIG (CORRECTED):
  w_resub_class1: [-0.25, 0.00]  # Treated as PENALTY signal
  # Rationale: 69.4% < 86.7% baseline, so negative contribution
```

---

## C) Feature Coverage Analysis

### High Coverage Features (✓)

| Feature | Coverage | Notes |
|---------|----------|-------|
| outcome | 100% | Binary |
| btd | 18.0% | 95.1% approval rate |
| orphan | 24.5% | 90.3% approval rate |
| priority_review | 45.7% | Positive signal |
| fast_track | 35.9% | Positive signal |
| accelerated_approval | 14.9% | Positive signal |
| experienced_sponsor | 49.7% | Positive signal |
| designation_stack_count | 56.6% | Mean: 1.39 |
| manufacturing_risk | 21.1% | **52.3% approval** (critical penalty) |
| had_adcom | 3.6% | Low volume |

### Therapeutic Area Distribution

| Area | Events | Approval Rate | Signal |
|------|--------|---------------|--------|
| Oncology | 414 (30.7%) | 87.2% | Neutral |
| Other | 457 (33.9%) | 86.8% | Neutral |
| CNS/Neurology | 94 (7.0%) | 83.0% | Slight penalty |
| Immunology | 85 (6.3%) | 89.4% | Slight bonus |
| Rare Disease | 67 (5.0%) | 91.0% | Bonus |
| Cardiovascular | 42 (3.1%) | 81.0% | Penalty |
| Ophthalmology | 34 (2.5%) | 82.4% | Penalty |
| Pain | 31 (2.3%) | 74.2% | **Strong penalty** |
| Nephrology | 28 (2.1%) | 78.6% | Penalty |

### Low Coverage Signals (⚠ Need Enrichment)

| Signal | Coverage | Source | Priority |
|--------|----------|--------|----------|
| social_total | 4.7% | LunarCrush | HIGH |
| cluster_sell | 0.0% | FinBrain | HIGH |
| pcr_extreme | 0.0% | FinBrain | HIGH |
| void_6mo | 0.0% | Indeed | HIGH |
| pub_volume | 0.0% | PubMed | MEDIUM |
| trial_velocity | 0.0% | ClinicalTrials | MEDIUM |
| herg_risk | 0.0% | ChEMBL | LOW |
| logp_risk | 0.0% | ChEMBL | LOW |

---

## D) Signal Validation Summary

### ✓ VALIDATED (Dataset-Supported)

| Signal | Mechanism | Evidence |
|--------|-----------|----------|
| BTD | +bonus | 95.1% vs 86.7% baseline (+8.4pp) |
| Orphan | +bonus | 90.3% vs 86.7% baseline (+3.6pp) |
| Mfg Risk | **-penalty** | 52.3% vs 86.7% baseline (-34.4pp) |
| Rare Disease TA | +bonus | 91.0% vs 86.7% baseline (+4.3pp) |
| Pain TA | -penalty | 74.2% vs 86.7% baseline (-12.5pp) |
| Class 1 CMC Resub | **-penalty** | 69.4% vs 86.7% baseline (-17.3pp) |

### ⚠ UNVALIDATED (Need Enrichment)

| Signal | Hypothesized Effect | Status |
|--------|---------------------|--------|
| VOID (hiring freeze) | Strong penalty | No Indeed data |
| Cluster insider sell | Penalty | No FinBrain data |
| PCR extreme | Penalty | No FinBrain data |
| Publication volume | Varies | No PubMed data |
| Trial timeline delay | Penalty | No ClinicalTrials data |

### ❌ INVALIDATED (Removed)

| Signal | Original Claim | Actual | Action |
|--------|----------------|--------|--------|
| P001 Override | 99.5% approval | 69.4% approval | REMOVED, converted to penalty |

---

## E) T-1 Compliance Audit

### ✓ SAFE (Pre-Decision Information)

| Feature | Rationale |
|---------|-----------|
| btd, orphan, fast_track, priority | Granted during development |
| accelerated_approval | Pathway announced at filing |
| experienced_sponsor | Historical record |
| therapeutic_area, modality | Fixed at filing |
| had_adcom, adcom_vote | AdCom occurs pre-decision |
| prior_crl (detected) | Chain analysis uses past events only |
| resubmission_class (detected) | Derived from prior CRL reason |

### ⚠ NEEDS VERIFICATION

| Feature | Concern | Recommendation |
|---------|---------|----------------|
| manufacturing_risk | May be derived from CRL reasons | Verify source is Form 483, not CRL letters |

---

## F) Optimization Test Results

### CPU Test (1M Configurations)

| Metric | V7 Baseline | V8.12 Test | Change |
|--------|-------------|------------|--------|
| Brier | 0.120 | **0.0897** | -25.3% |
| Specificity | 41.2% | **90.0%** | +118% |
| Precision | 89.4% | **97.72%** | +9.3% |
| F1 | 0.943 | 0.788 | -16.4%* |

*F1 decrease due to conservative threshold (precision-specificity tradeoff)

### Best Configuration Found
```
p_base: 0.854
p_threshold: 0.818
w_social: -1.077
w_btd: 0.062
w_mfg_pen: -0.298
w_resub_class1: -0.108  # P001 PENALTY (validated)
```

---

## G) Recommendations

### IMMEDIATE (Before Production)

1. ✅ **Remove P001 0.995 override** - DONE (converted to penalty)
2. ⏳ **Audit manufacturing_risk T-1 compliance** - Verify source
3. ⏳ **Set baseline to 0.867** - Matches dataset

### HIGH PRIORITY (This Week)

4. **Expand LunarCrush coverage** - Currently 4.7%, target 50%+
5. **Enrich FinBrain signals** - Insider trading, options PCR
6. **Enrich Indeed VOID signal** - Hiring freeze detection

### MEDIUM PRIORITY (This Month)

7. **Full GPU optimization run** - 1B+ configs on RTX 4070
8. **Cross-validation analysis** - Time-series split validation
9. **Out-of-sample testing** - 2026 Q1 events as holdout

---

## H) Files Generated

| File | Purpose |
|------|---------|
| `odin_processed_v8.npy` | 44-feature array (1349, 44) |
| `odin_data_preprocessor.py` | Data pipeline with resubmission detection |
| `ODIN_PREPROCESSING_REPORT.md` | Feature coverage report |
| `ODIN_DATASET_INTEGRITY_REPORT.md` | This document |

---

**Report End**
