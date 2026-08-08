# ODIN v6 / GUNGNIR v30 — Monitor Report v31
**Date:** 2026-03-25 | **Automated Run**

---

## 1. Model Champion Status

### ODIN v6.1.0 (PDUFA Scoring) — CHAMPION
| Metric | v5 Baseline | v6.0.0 | v6.1.0 (Champion) |
|--------|-------------|--------|---------------------|
| Brier Score | 0.1210 | 0.1378 | **0.1102** |
| AUC | 0.9007 | 0.859 | **0.897** |
| Brier Improvement | — | -7.5% (regression) | **+8.9%** |
| Features | 25 | 65 | 32 |
| Architecture | Ridge L2 (C=1.5) | Multi-ensemble (LGB+XGB+CatBoost+TabNet+Ridge) | **Ridge C=15.0** |

**Key Insight:** v6.1 recovered from v6.0's overfit. The 65→32 feature reduction and return to Ridge-dominant architecture fixed the v6.0 regression. v6.1 now beats v5 by 8.9% on Brier.

**New v6.1 Features (vs v5):** `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid` (7 new features added to v5's 25).

### GUNGNIR v30.1.0 (Phase Readout Scoring) — CHAMPION
| Metric | v29 Baseline | v30.0.0 | v30.1.0 (Champion) |
|--------|-------------|---------|---------------------|
| Brier Score | 0.2339 | 0.1394 | **0.1008** |
| AUC | 0.6439 | 0.8219 | N/A |
| Brier Improvement | — | +40.4% | **+56.9%** |
| Features | 82 | 109 | 26 |
| Architecture | 6-strategy ensemble + meta-learner | Multi-ensemble (6 models) + temp scaling | **Ridge C=30** |

**Key Insight:** Massive improvement. v30.1 cut Brier by 57% vs v29 with only 26 features (down from 109 in v30.0). The Ridge-dominant architecture again outperforms complex ensembles. This is a paradigm-level improvement for phase readout prediction.

**Notable v30.1 Features:** `des_orr`, `mod_cell_therapy`, `des_primary_ep`, `orr_x_onc`, `drug_last`, `drug_n_log`, `has_conf`, `des_pfs`, `sp_sr`, `j_last_neg`, `des_surrogate`, `is_asco` — strong mix of design, journey, and conference signals.

---

## 2. Optimizer History (LGB Champion Ladder)

The autonomous LightGBM optimizer ran **721 total rounds** with **8 champion promotions** (last run: 2026-03-01).

| Round | WF AUC | WF Brier | Features | Key Change |
|-------|--------|----------|----------|------------|
| 1 | 0.8514 | 0.1675 | 46 | Initial champion |
| 5 | 0.8754 | 0.1543 | 51 | +log_crl_rate |
| 44 | 0.8796 | 0.1546 | 52 | +is_ophthalmology, +log_sponsor_approvals |
| 134 | 0.8833 | 0.1886 | 50 | +is_rare_disease, +mfg_x_prior_crl |
| 241 | **0.8852** | 0.2057 | 51 | +btd_x_oncology, +is_oncology (final) |

**Top 5 Feature Importances (Round 241):** `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940), `log_crl_rate` (6091), `v1067_score` (2686).

**Note:** The LGB optimizer's best AUC (0.885) still trails ODIN v6.1's Ridge AUC (0.897), and its Brier (0.206) is worse than v6.1 (0.110). Ridge remains superior for ODIN.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | Connector settings block all 9realms tools |
| FinBrain MCP (insider, sentiment, analyst) | **PARAM ERROR** | Pydantic validation rejects all `req` params (serialization bug) |
| ClinicalTrials.gov MCP | **WORKING** | Successfully queried trial data |

**Action Required:** 9realms MCP tools need to be re-enabled in connector settings. FinBrain MCP has a parameter serialization bug — the `req` parameter is being passed as a string instead of an object by the connector layer.

---

## 4. ClinicalTrials.gov Validation

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (PDUFA ~2026-03-28)
- **NCT06154447**: Phase 1, evaluating VX-828 in healthy participants and CF patients. RECRUITING. Enrollment: 255. Primary completion: 2026-04-23.
- **NCT06298709**: Phase 1 bioavailability/food effect study. COMPLETED (2024).
- **NCT05867147**: Phase 1 QTc study. COMPLETED (2023).
- 6 total trials found. PDUFA is imminent (3 days away).

### LLY — Orforglipron (Phase 3 Readouts)
- **NCT07153471**: Phase 3 ATTAIN trial — orforglipron in obesity + knee OA. RECRUITING. Enrollment: 800. Primary completion: 2028-04.
- **NCT05872620**: Phase 3 — orforglipron in obesity + T2D. **COMPLETED** (2025-08). Enrollment: 1,613. This is likely the ATTAIN-1 dataset.
- 9 total trials found across phases.

---

## 5. Summary & Recommendations

### Current State
Both ODIN v6.1 and GUNGNIR v30.1 represent significant advances over their predecessors. The consistent finding across both models is that **simpler Ridge architectures with fewer, well-selected features outperform complex multi-model ensembles**. This is a strong signal that the feature engineering is doing the heavy lifting, not model complexity.

### Recommended Next Steps

1. **Fix MCP Connectivity:**
   - Re-enable 9realms MCP tools in connector settings to allow production scoring validation
   - Report FinBrain Pydantic serialization bug (req param passed as string, not dict)

2. **ODIN v6.2 Exploration:**
   - v6.1 Brier (0.1102) is strong but AUC dropped slightly from v5 (0.897 vs 0.901). Try C-value sweep around 15.0 (e.g., 10–20 range)
   - Consider adding `sponsor_rolling_approval_rate` interactions
   - The LGB optimizer's top feature `v1067_minus_v1070` (model score delta) could be interesting as a meta-feature for Ridge

3. **GUNGNIR v30.2 Exploration:**
   - v30.1's Brier of 0.1008 is exceptional. Validate on out-of-time data beyond 2025-01 cutoff
   - The 26-feature Ridge(C=30) model should be stress-tested with bootstrap resampling
   - Consider adding CTGOV real trial features from v29 — the v30 deploy shows `ctgov_cache_used: false`

4. **Imminent Catalyst Alert:**
   - **VRTX PDUFA on 2026-03-28** (3 days). This is a high-priority scoring event. Production ODIN scoring is blocked by MCP being disabled.

---

*Report generated automatically. 9realms MCP and FinBrain MCP were unavailable this run. ClinicalTrials.gov data successfully retrieved.*

**Disclaimer:** This is informational/educational content, not investment advice.
