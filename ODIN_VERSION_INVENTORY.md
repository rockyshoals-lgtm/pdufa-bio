# ODIN Version Inventory & Conflict Analysis

**Generated:** 2026-03-13
**Purpose:** Comprehensive diff of all discovered ODIN versions to inform vNEXT design

---

## 1. Version Registry

| Version | Architecture | WF AUC | WF Brier | Val AUC | Val Brier | Trainable Weights | Walk-Forward? | Status |
|---------|-------------|--------|----------|---------|-----------|-------------------|---------------|--------|
| v1071 stable | Logistic (flat) | — | — | ~0.89 | ~0.12 | 33 | No (in-sample) | Superseded |
| v1251 CORNERSTONE | Logistic (flat) | 0.9082 | 0.0888 | 0.9190 | 0.1002 | 44 | Yes | **CHAMPION** |
| v1349/v1249 | Logistic (flat) | 0.9063 | 0.0876 | 0.9002 | 0.1005 | 44 | Yes | Overhoned |
| MCP v10.2 embedded | Vectorized logistic | 0.9085 | 0.0968 | — | — | 56 | Yes | **LIVE IN MCP** |
| ULTIMATE V2.0 | Layered on v1251 | — | — | — | — | 44+30 new | Not tested | Experimental |
| v2.1 LGB | LightGBM | 0.9193 | 0.0764 | — | — | 45 features | Yes | Best AUC/Brier |

---

## 2. Weight Comparison Table (Key Parameters)

| Parameter | v1071 stable | v1251 CORNER | v1349 | MCP embedded | Notes |
|-----------|-------------|--------------|-------|--------------|-------|
| **base_logit** | 1.48 | 1.6878 | 1.4766 | vectorized | v1251 highest base |
| **snda_base_penalty** | -0.43 | -3.00 | -3.00 | — | v1251 7x stronger than v1071 |
| **prior_crl_penalty** | -3.88 | -3.00 | -3.88 | binary signal | v1251 weaker than v1071/v1349 |
| **inexperienced_sponsor_penalty** | -0.83 | -0.50 | -0.83 | binary signal | v1251 weakened |
| **manufacturing_risk_penalty** | -0.19 | **-0.0001** | -0.19 | binary signal | ⚠️ v1251 effectively ZERO |
| **form_483_penalty** | -1.00 | -1.50 | -1.00 | binary signal | v1251 strengthened |
| **adcom_low_penalty** | **-0.77** | **-0.0001** | -0.0001 | — | ⚠️ v1251/v1349 killed this signal |
| **adcom_mid_penalty** | -0.67 | -0.52 | -0.67 | — | Moderate across versions |
| **adcom_high_boost** | 3.32 | 3.20 | 3.32 | — | Consistent |
| **btd_weight** | 0.32 | 0.15 | 0.32 | binary signal | v1251 halved |
| **orphan_weight** | 0.04 | 0.10 | 0.04 | binary signal | v1251 doubled |
| **priority_review_weight** | **0.75** | **2.53** | 2.55 | binary signal | ⚠️ v1251 3.4x v1071 |
| **fast_track_weight** | 1.20 | 0.80 | 1.20 | binary signal | v1251 reduced |
| **accelerated_approval_weight** | ~0 | 0.35 | ~0 | binary signal | v1251 added signal |
| **class1_resubmission_boost** | **+0.43** | **-1.38** | -1.40 | — | ⚠️ SIGN FLIPPED in v1251 |
| **experienced_sponsor_boost** | 1.29 | 1.10 | 1.29 | — | Similar |
| **single_arm_study_penalty** | -0.34 | **-3.60** | -0.34 | binary signal | ⚠️ v1251 10x stronger |
| **surrogate_endpoint_penalty** | -0.16 | -0.50 | -0.16 | binary signal | v1251 3x stronger |
| **gene_therapy_penalty** | -1.48 | -2.00 | -1.48 | binary signal | v1251 strengthened |
| **indication_onc_boost** | -0.88 | **-0.93** | -0.88 | TA offset | ⚠️ Negative "boost" in all |
| **ta_low_risk_boost** | -1.79 | **-1.87** | -1.79 | TA offset | ⚠️ Negative "boost" in all |
| **social_weight** | 0.66 | **0.12** | 0.66 | — | v1251 suppressed social |
| **s23_insider_weight** | 0.41 | 0.30 | 0.41 | — | v1251 reduced |
| **s6_hiring_weight** | 0.92 | 0.50 | 0.92 | — | v1251 halved |

### Interaction Terms (v1251+ only)

| Interaction | v1251 CORNER | v1349 | Direction | Semantic Check |
|-------------|-------------|-------|-----------|----------------|
| ix_prior_crl_x_mfg_risk | -0.50 | -0.28 | Correct (double penalty) | ✅ |
| ix_prior_crl_x_form483 | -0.80 | -0.48 | Correct (double penalty) | ✅ |
| ix_gene_therapy_x_mfg_risk | -0.60 | -0.34 | Correct (double penalty) | ✅ |
| ix_inexperienced_x_mfg_risk | -2.50 | -3.00 | Correct (double penalty) | ✅ |
| ix_single_arm_x_surrogate | -0.30 | -0.13 | Correct (double penalty) | ✅ |
| ix_btd_x_single_arm | **+2.16** | +2.16 | ⚠️ BTD offsets single-arm penalty | Plausible |

---

## 3. Tier Thresholds

| Tier | v1251 CORNER | MCP v10.2 | Action (v1251) | Action (MCP) |
|------|-------------|-----------|----------------|--------------|
| TIER_1 | ≥0.85 | ≥0.858 | LONG | LONG |
| TIER_2 | ≥0.65 | ≥0.734 | CAUTIOUS LONG | **NO TRADE** |
| TIER_3 | ≥0.40 | ≥0.578 | MONITOR | MONITOR |
| TIER_4 | <0.40 | <0.578 | NO TRADE | NO TRADE |

**⚠️ CRITICAL CONFLICT:** MCP Tier 2 says "NO TRADE" while v1251 says "CAUTIOUS LONG". MCP thresholds are uniformly higher, making it more conservative.

---

## 4. Avoid Signals

| Signal | v1251 | ULTIMATE V2.0 | MCP | Notes |
|--------|-------|---------------|-----|-------|
| ppm_flag | ✅ | ✅ | ✅ | Priority Review Manufacturing (PPM) |
| gene_therapy_cmc | ✅ | ✅ | ? | Gene therapy + CMC issues |
| ema_cmc_flag | ✅ | ✅ | ? | EMA chemistry/manufacturing flag |
| hiring_void_nda | ✅ | ✅ | ? | No hiring activity near NDA |
| pediatric_no_pk | ✅ | ✅ | ? | Pediatric w/o PK data |
| cmc_extension_active | ✅ | ✅ | ? | Active CMC extension |
| insider_critical_sell | ✅ | ✅ | ? | Heavy insider selling |

---

## 5. Calibration Methods

| Version | Method | Parameters |
|---------|--------|------------|
| v1251 | Platt | a=-0.027, b=0.583 |
| v1349 | Platt | a=-0.167, b=0.651 |
| MCP v10.2 | None (raw sigmoid) | — |
| ULTIMATE V2.0 | Platt (inherits v1251) | a=-0.027, b=0.583 |

---

## 6. Semantic Anomalies (Weights That Need Investigation)

1. **class1_resubmission_boost = -1.38 (v1251)**: Class I resubmissions historically have ~90% approval rate. A negative "boost" is semantically wrong. v1071 had it correct at +0.43. Honing likely overfit to a few failed resubmissions.

2. **indication_onc_boost = -0.93**: Oncology has above-average approval rates (~75%). Negative boost contradicts domain knowledge. May be compensated by other oncology-related features.

3. **ta_low_risk_boost = -1.87**: "Low risk" therapeutic areas should get a positive boost. Sign is wrong.

4. **manufacturing_risk_penalty ≈ 0 (v1251)**: Manufacturing issues are a known CRL driver. Zero penalty is dangerous — honing killed this signal.

5. **adcom_low_penalty ≈ 0 (v1251/v1349)**: Low AdCom votes predict CRL. v1071 had -0.77. Honing killed this.

6. **single_arm_study_penalty = -3.60 (v1251)**: This is extremely strong — 10x the v1071/v1349 value. May be overfit.

7. **priority_review_weight = 2.53 (v1251)**: 3.4x stronger than v1071. Priority review is predictive but this magnitude is suspicious.

---

## 7. ULTIMATE V2.0 Additions (Not in v1251)

New signal categories added in ULTIMATE V2.0 that need evaluation:
- **Expanded Social Signals (GOD MODE V7.1)**: sentiment, engagement spikes, social silence, smart money divergence
- **CEO Tone/Qualitative Sentiment**: bullish/cautious/silent CEO signals
- **Operational Risk (v10.70)**: expanded manufacturing/quality signals
- **Expectation Gap (S25 Research)**: analyst consensus vs reality gap
- **Market Regime Detection**: BULL/NORMAL/BEAR/CRISIS multipliers
- **New Interaction Terms**: gene_therapy_x_orphan, btd_x_experienced, prior_crl_x_safety

---

## 8. Recommendation for vNEXT

**Base Architecture:** Start from v1251 CORNERSTONE (best WF AUC among logistic models, true walk-forward validated) with the following corrections:

1. **Fix semantic anomalies** — restore correct signs for class1_resubmission_boost, ta_low_risk_boost, indication_onc_boost
2. **Restore killed signals** — manufacturing_risk_penalty, adcom_low_penalty
3. **Moderate extreme weights** — cap single_arm_study_penalty, priority_review_weight to reasonable ranges
4. **Standardize tier thresholds** — resolve v1251 vs MCP conflict
5. **Add ULTIMATE V2.0 features selectively** — only those with clear domain justification
6. **Validate against v2.1 LGB** — use LGB as upper-bound benchmark (AUC 0.9193)

**Target Metrics (vNEXT):**
- WF AUC ≥ 0.910 (beat v1251's 0.9082)
- WF Brier ≤ 0.085 (beat v1251's 0.0888)
- No semantic anomalies in weight signs
- Consistent tier thresholds and actions
