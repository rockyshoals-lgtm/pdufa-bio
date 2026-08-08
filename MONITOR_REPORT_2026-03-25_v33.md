# ODIN v6 & GUNGNIR v30 — Monitoring Report v33
**Date:** 2026-03-25 | **Automated Run**

---

## 1. Champion Model Status

### ODIN v6.1.0 (PDUFA Scoring)
| Metric | v5 Baseline | v6.0 | v6.1 (Champion) |
|--------|------------|------|------------------|
| **Brier** | 0.1210 | 0.1378 | **0.1102** |
| **AUC** | 0.9007 | 0.859 | 0.897 |
| Features | 25 | 65 | 32 |
| Architecture | Ridge L2 (C=1.5) | Multi-strategy ensemble | Ridge (C=15.0) |
| Training Events | 2,203 | 1,845 | 1,845 |

**Key Insight:** v6.1 recovered from v6.0's overfitting problem (65 features → 32 via forward selection). Brier improved **8.9%** over v5 baseline. The simpler Ridge(C=15) architecture outperforms the complex ensemble from v6.0.

**v6.1 New Features (vs v5):** `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid` (7 new features added to v5's 25-feature base).

### GUNGNIR v30.1.0 (Phase Readout Scoring)
| Metric | v29 Baseline | v30.0 | v30.1 (Champion) |
|--------|-------------|-------|-------------------|
| **Brier** | 0.2339 | 0.1394 | **0.1008** |
| **AUC** | 0.6439 | 0.8219 | N/A |
| Features | 82 | 109 | 26 |
| Architecture | 6-strategy ensemble | Multi-strategy (LGB+XGB+Cat+FT+TabNet+Ridge) | Ridge(70%)+Trees(30%) |
| Training Events | 2,937 | 1,223 | N/A |

**Key Insight:** v30.1 achieved a massive **56.9% Brier improvement** over v29. Feature reduction from 109 → 26 eliminated overfitting. The Ridge+Trees blend is dramatically more calibrated than v30.0's complex ensemble.

**v30.1 Notable Features:** `has_ppm`, `des_orr`, `mod_cell_therapy`, `drug_last`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `sp_sr`, `era_post24`, `competitive`, `j_last_neg`, `is_asco`, `mod_gene_therapy` — lean, interpretable feature set.

---

## 2. Model Checkpoints & Logs

- **models/ directory:** No new checkpoint files since last check. Contains `lgb_champions/`, `model_registry/`, `lightgbm_challenger_v1.pkl`, and `v1071_GOLD_STANDARD.pkl`.
- **logs/ directory:** Does not exist — no optimizer iteration logs found.
- **Training scripts present:** `odin_v6_train.py`, `odin_v6_gpu_optimizer.py`, `gungnir_v30_train.py`

**Status:** No autonomous optimizer runs detected since last report. Models are stable at v6.1 / v30.1.

---

## 3. Production MCP Scoring

**9realms MCP tools are currently DISABLED** in connector settings. Unable to run production v5/v27 scores for drift comparison.

- `odin_score` → disabled
- `gungnir_score` → disabled
- `system_status` → disabled

**Action Required:** Re-enable 9realms MCP connector to resume production scoring comparisons.

---

## 4. FinBrain Market Intelligence

**FinBrain MCP has a parameter serialization issue** — the `req` parameter expects a Pydantic model object but receives a JSON string. All calls to `insider_transactions_by_ticker`, `news_sentiment_by_ticker`, and `analyst_ratings_by_ticker` for VRTX, LLY, and ABBV failed.

**Action Required:** Fix FinBrain MCP connector parameter handling (Pydantic model deserialization).

---

## 5. ClinicalTrials.gov Validation

### Orforglipron (LLY) — Phase 3 Obesity
| NCT ID | Title | Status | Enrollment | Primary Completion |
|--------|-------|--------|------------|-------------------|
| NCT05872620 | Orforglipron in obesity + T2D | **COMPLETED** | 1,613 | 2025-08-08 |
| NCT05869903 | Orforglipron in obesity/overweight + comorbidities | **ACTIVE, NOT RECRUITING** | 3,127 | 2025-07-25 |
| NCT07153471 | Orforglipron in obesity + OA knee | RECRUITING | 800 | 2028-04 |
| NCT06109311 | Orforglipron + insulin glargine in T2D | **COMPLETED** | 546 | 2025-09-15 |

**Signal:** The two pivotal Phase 3 trials (n=1,613 and n=3,127) have completed or are past primary completion dates. Topline readouts should be imminent or already reported. This is a high-priority GUNGNIR catalyst to watch.

### Vanzacaftor/Tezacaftor/Deutivacaftor (VRTX) — Cystic Fibrosis
| NCT ID | Title | Status | Enrollment | Primary Completion |
|--------|-------|--------|------------|-------------------|
| NCT05844449 | Long-term safety/efficacy in CF (1yr+) | ENROLLING BY INVITATION | 174 | 2029-07-30 |
| NCT06154447 | VX-828 evaluation in CF | RECRUITING | 255 | 2026-04-23 |
| NCT06299709 | Bioavailability/food effect granule formulation | COMPLETED | 34 | 2024-05-23 |
| NCT07349394 | PK study with rosuvastatin | ACTIVE, NOT RECRUITING | 18 | 2026-04-04 |

**Signal:** VRTX has the next-generation CF triple combo well into the regulatory pipeline. Supportive PK studies completed/completing. PDUFA date imminent (2026-03-28).

---

## 6. Summary & Recommendations

### Current Champions
| Model | Brier | vs Baseline | Status |
|-------|-------|-------------|--------|
| **ODIN v6.1** | 0.1102 | +8.9% vs v5 (0.1210) | STABLE |
| **GUNGNIR v30.1** | 0.1008 | +56.9% vs v29 (0.2339) | STABLE |

### Blockers
1. **9realms MCP disabled** — cannot compare production (v5/v27) vs new model (v6.1/v30.1) scores
2. **FinBrain MCP broken** — Pydantic serialization error prevents insider/sentiment/analyst data retrieval

### Recommended Next Steps
1. **Re-enable 9realms MCP** to resume production drift monitoring
2. **Fix FinBrain connector** parameter handling for insider transaction monitoring
3. **Update CLAUDE.md** to reflect v6.1 and v30.1 as new champions (currently references v5 and v29)
4. **Deploy v6.1 to MCP server** — Replace v5 in `mcp_9realms_vnext.py` with v6.1 weights (32-feature Ridge C=15)
5. **Deploy v30.1 to MCP server** — Replace v29 GUNGNIR with v30.1 weights (26-feature Ridge+Trees blend)
6. **Monitor LLY orforglipron** — Pivotal Phase 3 trials completed, topline readout is a high-conviction GUNGNIR event
7. **Monitor VRTX PDUFA 03/28** — Imminent decision date, score with ODIN v6.1 once MCP re-enabled
8. **Consider v6.2 exploration** — Test whether adding ClinicalTrials.gov real trial data (à la GUNGNIR v29's CTGOV innovation) improves ODIN further

---

*Report generated automatically. 9realms MCP and FinBrain MCP require attention for full monitoring capability.*

*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
