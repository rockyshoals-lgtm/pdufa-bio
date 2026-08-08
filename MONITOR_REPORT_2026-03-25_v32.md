# ODIN v6 & GUNGNIR v30 Optimization Monitor Report
**Date:** 2026-03-25 | **Report Version:** v32 | **Run Type:** Scheduled Automated

---

## 1. Champion Model Status

### ODIN v6.1.0 (PDUFA Scoring) — CHAMPION
| Metric | v5 Baseline | v6.0.0 | v6.1.0 (Champion) |
|--------|------------|--------|-------------------|
| **Brier** | 0.1210 | 0.1378 | **0.1102** |
| **AUC** | 0.9007 | 0.859 | 0.897 |
| **Improvement** | — | -7.5% (regression) | **+8.9%** |
| **Features** | 25 | 65 | 32 |
| **Architecture** | Ridge L2 C=1.5 | Multi-strategy ensemble | Ridge C=15.0 |

**Key Insight:** v6.1 achieved the best Brier score by simplifying from v6.0's 65-feature ensemble back to a focused 32-feature Ridge model with C=15.0. The 7 new features over v5 include: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Parsimony wins — v6.0's 65-feature ensemble actually regressed vs v5.

### GUNGNIR v30.1.0 (Phase Readout Scoring) — CHAMPION
| Metric | v29 Baseline | v30.0.0 | v30.1.0 (Champion) |
|--------|-------------|---------|-------------------|
| **Brier** | 0.2339 | 0.1394 | **0.1008** |
| **AUC** | 0.6439 | 0.8219 | — |
| **Improvement** | — | +40.4% | **+56.9%** |
| **Features** | 82 | 109 | 26 |
| **Architecture** | 6-strategy ensemble | Multi-strategy ensemble | Ridge(70%)+Trees(30%) |

**Key Insight:** Massive improvement. v30.1 cut features from 109 to just 26 while achieving a 56.9% Brier improvement over v29. The Ridge+Trees blend with aggressive feature selection crushed the complex ensemble approach. Notable features: `drug_last` (journey), `sp_sr` (sponsor success rate), `competitive`, `j_last_neg` (journey last negative), `des_rct` (RCT design).

---

## 2. LightGBM Autonomous Optimizer Status

The autonomous LightGBM optimizer ran **721 total rounds** with **8 champion promotions** (from champion_ladder.json):

| Round | WF AUC | WF Brier | Key Innovation |
|-------|--------|----------|----------------|
| 1 | 0.8514 | 0.1675 | Initial baseline |
| 5 | 0.8754 | 0.1543 | +log_crl_rate |
| 44 | 0.8796 | 0.1546 | +log_sponsor_approvals |
| 134 | 0.8833 | 0.1886 | +rare_disease, mfg_x_prior_crl |
| 161 | 0.8836 | 0.1555 | +s23_x_s6 interaction |
| **241** | **0.8852** | **0.2057** | **Final champion** (btd_x_oncology, v1067_minus_v1070) |

**Current LGB Champion:** AUC 0.8852, 51 features, 948 estimators. Top feature by importance: `v1067_minus_v1070` (9,009 splits). No new checkpoints since March 1.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| **9realms MCP** (odin_score, gungnir_score) | **DISABLED** | Connector settings block all 3 tools |
| **FinBrain MCP** | **PARAM ERROR** | All endpoints returning Pydantic validation errors on `req` parameter |
| **ClinicalTrials.gov MCP** | **OPERATIONAL** | Successfully queried orforglipron and vanzacaftor trials |

**Action Required:** 9realms MCP needs to be re-enabled in connector settings. FinBrain MCP has a parameter schema mismatch — the `req` field expects a dict instance but receives a string.

---

## 4. ClinicalTrials.gov Validation

### Orforglipron (LLY) — Phase 3 Obesity
- **NCT05872620** — Obesity + T2D, n=1,613, **COMPLETED** (primary completion Aug 2025)
- **NCT05869903** — Obesity + comorbidities, n=3,127, **ACTIVE_NOT_RECRUITING** (primary completion Jul 2025)
- **NCT07153471** — Obesity + knee OA, n=800, **RECRUITING** (primary completion Apr 2028)

**Validation:** Core Phase 3 trials (ATTAIN program) have completed or are nearing completion. Readout expected. Trial sizes robust (1,613 and 3,127 patients).

### Vanzacaftor/Tezacaftor/Deutivacaftor (VRTX) — CF
- **NCT06154447** — VX-828 evaluation in CF, n=255, **RECRUITING** (primary completion Apr 2026)
- **NCT06298709** — Granule formulation bioavailability, n=34, **COMPLETED**
- **NCT05867147** — QT/QTc interval study, n=56, **COMPLETED**

**Validation:** Supportive studies completed. PDUFA date imminent (March 30, 2026).

---

## 5. Summary & Recommendations

### Current State
Both v6.1 and v30.1 represent significant advances through **feature reduction and simpler architectures**. The pattern is clear: focused Ridge-based models with 26-32 features outperform complex ensembles with 65-109 features.

### Recommended Next Steps

1. **Re-enable 9realms MCP** — Production scoring is currently unavailable; connector settings need updating to restore odin_score, gungnir_score, and system_status tools.

2. **Fix FinBrain MCP parameter schema** — The `req` parameter validation is failing across all endpoints. This blocks insider transaction monitoring for high-conviction catalysts.

3. **Deploy v6.1 to MCP server** — The current MCP server still runs v5 weights. v6.1's 32-feature Ridge (C=15.0) should be integrated into `mcp_9realms_vnext.py` as the new production ODIN engine.

4. **Deploy v30.1 to MCP server** — Similarly, GUNGNIR production still runs the v29 ensemble. v30.1's Ridge(70%)+Trees(30%) blend with 26 features needs deployment.

5. **Explore v6.2 opportunities** — The LGB optimizer's top features (`v1067_minus_v1070`, `historical_crl_rate`) suggest score-differential and historical rate features could further improve v6.1's Ridge backbone. Consider adding `sponsor_rolling_approval_rate` interactions.

6. **GUNGNIR v30.2 exploration** — v30.1's 26 features are highly selective. Consider testing CTGOV real data features (from v29's cache of 1,576 drugs) as additional signals in the Ridge+Trees framework.

---

*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*

*Report generated automatically by ODIN/GUNGNIR monitoring task.*
