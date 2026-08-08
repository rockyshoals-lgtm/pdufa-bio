# ODIN vNEXT v3 vs v10.2 — Head-to-Head Validation Report

**Date:** 2026-03-13
**Test Set:** 358 events, Jan 2025 – Feb 2026 (with known outcomes)
**Methodology:** vNEXT uses dataset pre-computed columns; v10.2 uses v1070_score column

---

## 1. Summary Metrics

| Metric | v10.2 (v1070_score) | vNEXT v3 | Delta | Winner |
|--------|-------------------|----------|-------|--------|
| AUC | 0.8519 | 0.8884 | +0.0365 | **vNEXT** |
| Brier Score | 0.1381 | 0.1148 | -0.0233 | **vNEXT** |
| Classification Accuracy (P>0.5) | 84.4% | 85.2% | +0.8pp | **vNEXT** |
| Event-level wins | 60 | 298 | — | **vNEXT** |

**Conclusion:** vNEXT v3 outperforms v10.2 on all key metrics when evaluated on the 2025+ holdout period. The improvement is most pronounced in AUC (+0.0365) and calibration (Brier -0.0233).

---

## 2. Avoid Signal Verification

All 7 avoid signals correctly force TIER_4 regardless of probability:

| Signal | Base Prob | With Signal | Tier | Status |
|--------|-----------|-------------|------|--------|
| ppm_flag | 0.9880 | 0.9361 | T4 | ✅ |
| gene_therapy_cmc | 0.9880 | 0.9880 | T4 | ✅ |
| ema_cmc_flag | 0.9880 | 0.9880 | T4 | ✅ |
| hiring_void_nda | 0.9880 | 0.9880 | T4 | ✅ |
| pediatric_no_pk | 0.9880 | 0.9880 | T4 | ✅ |
| cmc_extension_active | 0.9880 | 0.9880 | T4 | ✅ |
| insider_critical_sell | 0.9880 | 0.9880 | T4 | ✅ |

Note: ppm_flag is the only avoid signal that also appears as a model feature (coef=-0.1862), so it affects probability as well as forcing T4. The other 6 are pure override signals.

---

## 3. API Backward Compatibility

| Test | Parameters | Result | Status |
|------|-----------|--------|--------|
| Full 22-param payload (ALDX) | All v10.2 params | P=0.0966, T4 | ✅ |
| Minimal payload (4 required) | ticker, drug_name, TA, pdufa_date | P=0.9459, T1 | ✅ |
| Max designations (5/5 stack) | All desigs + spa=50 + Ophtho | P=0.9954, T1 | ✅ |
| Worst case | prior_crl + ppm + naive + resub + COVID | P=0.0009, T4 | ✅ |
| Extra/unknown params | New fields silently ignored | P=0.9747, T1 | ✅ |
| GUNGNIR v25 | Positive readout text | P=0.9915 | ✅ |

---

## 4. Notable Findings

### 4.1 sponsor_prior_approvals Data Quality Issue

Major pharma companies (JNJ, MRK, PFE, NVS) show mixed spa values in the dataset — some events have spa=0, others have spa=40+. This is likely a data collection artifact where spa wasn't consistently filled for all events.

**Impact:** 45 approval events in 2025+ have spa=0, leading vNEXT to classify them as sponsor_naive (P ≈ 0.34). The model's logic is correct — spa=0 companies have a 16.9% approval rate vs 94.5% for spa≥5 — but production scoring should ensure spa is properly populated.

**Recommendation:** Add a data validation step that cross-references ticker→sponsor mapping to flag spa=0 for known large pharma companies.

### 4.2 TA Resolution Gap (MCP Tool Layer)

The MCP tool's freetext TA resolver lacks keywords for some indications:
- "Glaucoma" → misses Ophthalmology (only has "ophthalmology", "retinal", "macular")
- "Bipolar I disorder / Schizophrenia" → hits "bipolar" correctly
- "Achondroplasia" → misses Rare Disease
- "Menkes disease" → misses Rare Disease

**Fix needed:** Add ~15 more keywords to ODIN_TA_MAP for better freetext coverage. This only affects MCP API calls; dataset-based scoring uses pre-computed ta_bucket_v2.

### 4.3 Score Distribution

vNEXT v3 produces a wider score distribution than v10.2, with more confident extreme calls:

- vNEXT scores below 0.15: 41 events (mostly CRLs — correct)
- vNEXT scores above 0.90: 147 events (mostly approvals — correct)
- v10.2 tends to cluster in 0.40-0.80 range

### 4.4 Key Event Comparisons (2026)

| Ticker | Date | Outcome | v10.2 | vNEXT | Notes |
|--------|------|---------|-------|-------|-------|
| VNDA | 2/21/2026 | APPROVAL | 0.6410 T3 | 0.8635 T1 | vNEXT correctly confident |
| MRK | 2/20/2026 | APPROVAL | 0.7976 T2 | 0.9459 T1 | vNEXT correctly confident |
| IRON | 2/15/2026 | CRL | 0.7152 T3 | 0.8265 T2 | Both miss — ppm_flag + btd confuses both |
| AQST | 2/2/2026 | CRL | 0.3034 T4 | 0.0847 T4 | vNEXT more confident on CRL |
| EBS | 1/14/2026 | APPROVAL | 0.5034 T4 | 0.8635 T1 | vNEXT dramatically better |

---

## 5. Approval Checklist Progress

| # | Item | Status |
|---|------|--------|
| 1 | Review all 11 feature coefficients and signs | ✅ All correct (see audit package) |
| 2 | Verify tier thresholds match trading strategy | ⏳ User review needed |
| 3 | Confirm TIER_2 action change (CAUTIOUS LONG) | ⏳ User review needed |
| 4 | Run self-test | ✅ All 5 assertions passed |
| 5 | Score recent PDUFAs head-to-head | ✅ 358 events, vNEXT wins on all metrics |
| 6 | Verify avoid signals | ✅ All 7 signals force T4 |
| 7 | API backward compatibility | ✅ All 6 tests passed |
| 8 | Deploy to staging / FastMCP handshake | ⏳ Manual step |
| 9 | Monitor first week of production | ⏳ Post-deployment |

---

## 6. Recommended Pre-Deployment Fixes

1. **Add TA keywords** to `ODIN_TA_MAP`: "glaucoma" → Ophthalmology, "achondroplasia" → Rare Disease, "menkes" → Rare Disease, "protoporphyria" → Rare Disease, "anaphylaxis" → Immunology, "dry eye" → Ophthalmology, "aml" → Oncology
2. **Add spa validation** in tool layer: warn if spa=0 for tickers known to be large pharma
3. **Test with live Claude Desktop config** to verify FastMCP handshake

---

*Generated by automated validation pipeline. All scores reproducible from dataset + embedded model weights.*
