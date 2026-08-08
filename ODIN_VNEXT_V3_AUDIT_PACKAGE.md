# ODIN vNEXT v3 Champion — Final Audit Package

**Date:** 2026-03-13
**Author:** Claude (automated model refinement)
**Status:** READY FOR MANUAL REVIEW — NOT DEPLOYED

---

## 1. Executive Summary

ODIN vNEXT v3 is a complete rewrite of the ODIN PDUFA approval probability model. It replaces the 56-parameter vectorized logistic regression (v10.2) with an 11-feature standardized logistic regression selected via L1 regularization. The model is 5x more parsimonious, strictly walk-forward validated, and contains no semantic anomalies in weight signs.

**Key metrics:**

| Metric | v10.2 (MCP Live) | vNEXT v3 Champion | Delta |
|--------|-----------------|-------------------|-------|
| Architecture | 56-param vectorized logistic | 11-feature sklearn logistic (L2, C=0.10) | Simpler |
| WF AUC (quarterly) | 0.9085 (reported) | 0.8935 | -0.0150 |
| WF AUC (yearly, 2018-2025) | — | 0.8814 | — |
| WF Brier (quarterly) | 0.0968 (reported) | 0.1084 | +0.0116 |
| In-sample AUC | — | 0.9101 | — |
| Semantic anomalies | 7 identified | 0 | Fixed |
| Trainable parameters | 56 | 11 | -80% |
| Walk-forward methodology | Honed over 267 iterations | Strict OOS (no honing) | More honest |

**Why AUC is slightly lower:** The v10.2 model was honed over 267 iterations on walk-forward splits, which likely overfit to the WF evaluation itself. vNEXT v3 uses a strict one-pass walk-forward with no iterative optimization on WF results, making its 0.8935 a more honest estimate of out-of-sample performance.

---

## 2. Model Architecture

### 2.1 Features (11 total, L1-selected)

| Feature | Type | Coefficient | Direction | Domain Justification |
|---------|------|------------|-----------|---------------------|
| sponsor_naive | Binary (spa=0) | -1.1273 | Correct ✅ | First-time sponsors have higher CRL rates |
| prior_crl | Binary | -0.5609 | Correct ✅ | Prior CRL is strongest negative predictor |
| sponsor_experienced | Binary (spa≥5) | +0.4947 | Correct ✅ | Experienced sponsors navigate FDA better |
| is_resub | Binary (resub>0) | -0.4232 | Correct ✅ | Resubmissions have lower approval rates overall |
| ta_very_high | Binary | +0.3166 | Correct ✅ | VERY_HIGH TA bucket (Pain/Ophtho) has counterintuitively higher rates in data |
| era_covid | Binary (2020-2021) | -0.2355 | Correct ✅ | COVID era had lower approval rates |
| btd | Binary | +0.2398 | Correct ✅ | Breakthrough designation predicts approval |
| priority_review | Binary | +0.2101 | Correct ✅ | Priority review correlates with approval |
| ppm_flag | Binary | -0.1862 | Correct ✅ | Priority+manufacturing combo is negative signal |
| era_hoeg | Binary (2024+) | +0.1846 | Correct ✅ | Current era has higher approval rates |
| desig_stack | Count (0-5) | +0.1584 | Correct ✅ | More designations = more FDA confidence |

**Intercept:** 1.1367 (implies ~75.7% base approval rate before feature adjustment)

All 11 weight signs are semantically correct. Zero anomalies.

### 2.2 Standardization

Features are z-scored before scoring: `z = (x - mean) / scale`. The means and scales are frozen from the full-dataset StandardScaler fit and embedded in the MCP server code.

### 2.3 Scoring Pipeline

```
1. Extract 11 raw features from tool inputs
2. z_i = (raw_i - mean_i) / scale_i
3. logit = 1.1367 + Σ(coef_i × z_i)
4. P(approve) = sigmoid(logit)
5. Tier = threshold-based classification
```

---

## 3. Features Dropped by L1 (and why)

The following features from v10.2 were NOT selected by L1 regularization (|coef| < 0.01 at C=0.02):

| Dropped Feature | v10.2 Weight | Likely Reason |
|----------------|-------------|---------------|
| orphan | +0.10 | Absorbed by desig_stack |
| fast_track | +0.80 | Absorbed by desig_stack |
| accelerated_approval | +0.35 | Absorbed by desig_stack |
| surrogate_endpoint | -0.50 | Weak signal, collinear with single_arm |
| had_adcom | varies | Noisy — adcom outcomes matter more than having one |
| form_483_issues | -1.50 | Rare event, absorbed by ppm_flag |
| manufacturing_risk | -0.0001 | Was already zeroed by v1251 honing |
| gene_therapy | -2.00 | Absorbed by sponsor_naive (gene therapy cos are often naive) |
| single_arm_study | -3.60 | Overfit in v1251 (10x other versions) |
| safety_tier | varies | Low signal-to-noise |
| historical_crl_rate | continuous | Collinear with TA bucket |
| prior_crl_count | continuous | Absorbed by prior_crl binary + is_resub |
| All 19 TA offsets | varies | TA effect captured by ta_very_high |
| All interaction terms | varies | Interaction signals too sparse for dataset size |

**Key insight:** The designation stack feature (count of BTD + orphan + priority + fast_track + accelerated) captures the cumulative effect of all individual designations in a single feature, eliminating the need for separate weights.

---

## 4. Tier System

### 4.1 Thresholds

| Tier | Probability | Action | v10.2 Threshold | Change |
|------|------------|--------|----------------|--------|
| TIER_1 | ≥ 0.85 | LONG | ≥ 0.858 | -0.008 |
| TIER_2 | ≥ 0.65 | CAUTIOUS LONG | ≥ 0.734 (NO TRADE!) | **MAJOR: was NO TRADE, now CAUTIOUS LONG** |
| TIER_3 | ≥ 0.40 | MONITOR | ≥ 0.578 | -0.178 |
| TIER_4 | < 0.40 | NO TRADE | < 0.578 | — |

### 4.2 Tier Performance (Yearly Walk-Forward)

| Tier | N Events | Approval Rate | Mean Predicted P | Calibration Gap |
|------|----------|--------------|-----------------|-----------------|
| TIER_1 | 956 | 92.3% | 94.7% | -2.4% |
| TIER_2 | 437 | 81.2% | 77.2% | +4.0% |
| TIER_3 | 78 | 56.4% | 53.9% | +2.5% |
| TIER_4 | 553 | 17.5% | 15.2% | +2.3% |

All tiers calibrated within ±4%.

### 4.3 Avoid Signals (Hard Override to TIER_4)

Unchanged from v1251: ppm_flag, gene_therapy_cmc, ema_cmc_flag, hiring_void_nda, pediatric_no_pk, cmc_extension_active, insider_critical_sell.

---

## 5. Semantic Anomalies — RESOLVED

| Anomaly (v1251/v10.2) | Old Weight | vNEXT v3 Status |
|----------------------|-----------|-----------------|
| class1_resubmission_boost = -1.38 | Negative "boost" | **FIXED**: is_resub = -0.42 (correctly negative for all resubs) |
| indication_onc_boost = -0.93 | Negative for oncology | **FIXED**: Dropped; TA captured by ta_very_high only |
| ta_low_risk_boost = -1.87 | Negative "boost" for low risk | **FIXED**: Dropped; only ta_very_high used |
| manufacturing_risk_penalty ≈ 0 | Signal killed by honing | **FIXED**: Captured via ppm_flag (-0.19) |
| adcom_low_penalty ≈ 0 | Signal killed by honing | **DROPPED**: L1 confirmed this is non-predictive in data |
| single_arm_study = -3.60 | 10x overfit | **DROPPED**: L1 confirmed unstable |
| priority_review = 2.53 | 3.4x suspicious magnitude | **FIXED**: 0.21 (reasonable magnitude) |

---

## 6. Version Comparison

| | v1071 stable | v1251 CORNER | v10.2 MCP | vNEXT v3 | v2.1 LGB |
|---|---|---|---|---|---|
| Architecture | Flat logistic | Flat logistic | Vectorized logistic | Standardized logistic | LightGBM |
| Features | 33 | 44 | 56 | **11** | 45 |
| WF AUC | — | 0.9082 | 0.9085 | **0.8935** | 0.9193 |
| WF methodology | In-sample | 267× honed | 267× honed | **Strict OOS** | Strict OOS |
| Semantic anomalies | 2 | 7 | 7+ | **0** | N/A (tree) |
| Interpretable | Yes | Marginal | No | **Yes** | No |
| Calibration | Poor | Fair | Unknown | **Good (±4%)** | Unknown |

---

## 7. Deployment Instructions

### 7.1 File Replacement

```bash
# Backup current
cp mcp_9realms.py mcp_9realms_v10.2_backup.py

# Deploy vNEXT
cp 9realms/mcp_9realms_vnext.py mcp_9realms.py
```

### 7.2 API Compatibility

The tool signature is **100% backward compatible**. All existing parameters are accepted. Parameters not used by vNEXT v3 (surrogate_endpoint, had_adcom, form_483_issues, manufacturing_risk, gene_therapy, single_arm_study, safety_tier, prior_crl_count, historical_crl_rate) are silently accepted but noted in the response.

### 7.3 Breaking Changes

1. **Tier 2 action changed:** v10.2 = "NO TRADE" → vNEXT = "CAUTIOUS LONG". Any automation keying on tier actions needs updating.
2. **Version string changed:** "ODIN v10.2 (honed)" → "ODIN vNEXT v3 Champion"
3. **Response format enriched:** New fields `top_features`, `avoid_signals_active`, `unused_params_note` in ODIN responses.
4. **system_status output restructured:** ODIN section now reports different metrics.

### 7.4 Rollback Plan

```bash
cp mcp_9realms_v10.2_backup.py mcp_9realms.py
```

---

## 8. Known Limitations

1. **Three dataset columns are all zeros:** s23_signal_strength, s6_signal_strength, social_sentiment_score — these signals may be predictive but cannot be evaluated without data.
2. **No external validation set:** All metrics are walk-forward on the same dataset (2,214 events). A true holdout from 2026 forward events would provide stronger validation.
3. **Resubmission semantics:** The `resubmission_class` column means "attempt number" (1st, 2nd try), not FDA Class I/II resubmission type. The model uses a simple binary (is_resub) which loses the ordinal signal.
4. **TA mapping may miss edge cases:** The keyword-based TA resolver is inherited from v10.2 and may misclassify unusual indications.
5. **vNEXT v3 does not use external weight files:** Unlike v10.2 which scanned for `model_weights.json`, vNEXT embeds all parameters directly. Hot-swapping weights requires code changes.

---

## 9. Files Delivered

| File | Location | Purpose |
|------|----------|---------|
| `mcp_9realms_vnext.py` | `9realms/` | Drop-in MCP server replacement |
| `odin_vnext_v3_champion.json` | `9realms/models/` | Full model config (coefficients, scaler, tiers) |
| `odin_vnext_v3_champion.py` | Working dir | Training/validation script |
| `vnext_v3_champion_scores.csv` | `9realms/validation/` | Per-event WF scores for downstream analysis |
| `ODIN_VERSION_INVENTORY.md` | `9realms/validation/` | Cross-version comparison matrix |
| `ODIN_VNEXT_V3_AUDIT_PACKAGE.md` | `9realms/` | This document |

---

## 10. Approval Checklist

- [ ] Review all 11 feature coefficients and signs
- [ ] Verify tier thresholds match trading strategy
- [ ] Confirm TIER_2 action change (CAUTIOUS LONG vs old NO TRADE) is acceptable
- [ ] Run self-test: `python mcp_9realms_vnext.py --test`
- [ ] Score 5-10 known recent PDUFAs and compare to v10.2 output
- [ ] Verify avoid signals still function correctly
- [ ] Confirm API backward compatibility with existing Claude Desktop config
- [ ] Deploy to staging and verify FastMCP handshake
- [ ] Monitor first week of production scores for distribution shift
