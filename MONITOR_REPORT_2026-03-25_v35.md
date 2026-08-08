# ODIN v6 / GUNGNIR v30 — Monitor Report v35
**Date:** 2026-03-25 | **Scheduled Run**

---

## 1. Champion Model Status

### ODIN v6.1.0 (PDUFA Scoring)
| Metric | v5 Baseline | v6.0.0 | v6.1.0 (Champion) |
|--------|------------|--------|-------------------|
| Holdout Brier | 0.1210 | 0.1378 | **0.1102** |
| Holdout AUC | 0.9007 | 0.859 | **0.897** |
| Features | 25 | 65 | **32** |
| Architecture | Ridge L2 C=1.5 | Multi-ensemble (LGB+XGB+Cat+TabNet+Ridge) | **Ridge C=15.0** |
| Training Events | 2,203 | 1,845 | 1,845 |
| Holdout Events | 358 | 358 | 358 |

**Key Insight:** v6.1 dramatically simplified from v6.0's 65-feature multi-ensemble down to a clean 32-feature Ridge model — and improved Brier by 20% (0.1378 → 0.1102). The 7 new features over v5's 25 include: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Simpler is better — Ridge continues to dominate tree-based approaches for PDUFA scoring.

### GUNGNIR v30.1.0 (Phase Readout Scoring)
| Metric | v29 Baseline | v30.0.0 | v30.1.0 (Champion) |
|--------|-------------|---------|-------------------|
| Brier | 0.2339 | (multi-ensemble) | **0.1008** |
| Features | 82 | 109 | **26** |
| Architecture | 6-strategy ensemble + meta-learner | Multi-ensemble (LGB+XGB+Cat+FT+TabNet+Ridge) | **Ridge(70%)+Trees(30%)** |

**Key Insight:** v30.1 achieved a stunning 56.9% Brier improvement over v29. Like ODIN, the winning strategy was aggressive feature reduction (109 → 26 features) and simpler architecture. The 26 retained features focus on: trial design signals (`des_rct`, `des_pfs`, `des_orr`, `des_surrogate`, `des_topline`, `des_primary_ep`), therapeutic area (`ta_oncology`, `ta_infectious`, `ta_rare`), drug journey (`drug_last`, `drug_n_log`, `j_last_neg`), modality (`mod_cell_therapy`, `mod_antibody`, `mod_gene_therapy`), and context (`year`, `month`, `era_post24`, `is_asco`, `has_conf`, `competitive`).

---

## 2. Autonomous Optimizer Status (LightGBM Challenger)

The LGB champion ladder in `models/lgb_champions/` shows **721 total rounds** with **8 promotions**:

| Round | WF AUC | WF Brier | Features | Key Innovation |
|-------|--------|----------|----------|----------------|
| 1 | 0.8514 | 0.1675 | 46 | Baseline LGB |
| 5 | 0.8754 | 0.1543 | 51 | +log_crl_rate |
| 44 | 0.8796 | 0.1546 | 52 | +log_sponsor_approvals |
| 134 | 0.8833 | 0.1886 | 50 | +is_rare_disease |
| 241 | **0.8852** | 0.2057 | 51 | +btd_x_oncology, +v1067_minus_v1070 |

**Current LGB Champion (Round 241):** WF AUC 0.8852, but Brier 0.2057 — significantly worse calibration than Ridge v6.1 (0.1102). The LGB optimizer maximizes AUC, not Brier, which explains the divergence. Top feature importances: `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940).

**Note:** No new optimizer rounds detected since March 1, 2026. The optimizer appears to have plateaued after 721 rounds.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| `odin_score` | **DISABLED** | Connector settings block execution |
| `gungnir_score` | **DISABLED** | Connector settings block execution |
| `system_status` | **DISABLED** | Connector settings block execution |
| FinBrain (insider/sentiment/analyst) | **PARAM ERROR** | `req` parameter expects Pydantic model, string rejected |
| ClinicalTrials.gov | **WORKING** | Successfully returned orforglipron Phase 3 data |

**Action Required:** 9realms MCP tools and FinBrain tools need connector re-enablement to support live scoring and market intelligence.

---

## 4. ClinicalTrials.gov Validation

Successfully queried for **orforglipron** (LLY oral GLP-1 agonist):
- **NCT05313802** — Phase 1 multiple dose study in healthy overweight/obese (COMPLETED)
- Multiple Phase 3 ATTAIN trials confirmed in database
- Trial design data available for GUNGNIR CTGOV cache validation

---

## 5. Recommendations

### Immediate
1. **Re-enable 9realms MCP connector** — ODIN/GUNGNIR scoring tools are disabled, blocking live catalyst scoring
2. **Fix FinBrain parameter format** — The `req` parameter needs proper Pydantic model instantiation; current JSON string format is rejected
3. **Resume LGB optimizer** — 721 rounds completed but AUC-focused. Consider switching objective to Brier minimization

### Model Development
4. **ODIN v6.1 is production-ready** — Brier 0.1102 is the best ever achieved (+8.9% over v5). Recommend deploying to MCP server
5. **GUNGNIR v30.1 needs validation** — Brier 0.1008 (56.9% improvement) is extraordinary. Recommend thorough leakage audit before deployment:
   - Verify all 26 features are T-1 compliant
   - Check `drug_last` and `j_last_neg` journey features use strict temporal ordering
   - Validate holdout is truly unseen (post-2025-01-01)
6. **Feature simplification trend confirmed** — Both v6.1 (32 features) and v30.1 (26 features) beat their bloated predecessors. Ridge regularization + forward selection > complex ensembles
7. **LGB challenger AUC 0.8852 is interesting** — Could be useful as an ensemble component if calibrated properly. The `v1067_minus_v1070` feature (score differential) and `v1070_x_social` interaction are novel signals worth investigating for v6.2

---

## 6. Model Lineage Summary

```
ODIN:   v5 (Brier 0.1210) → v6.0 (0.1378, regression) → v6.1 (0.1102, CHAMPION ✓)
GUNGNIR: v29 (Brier 0.2339) → v30.0 (bloated) → v30.1 (0.1008, CHAMPION ✓)
LGB:    Round 1 (AUC 0.8514) → ... → Round 241 (AUC 0.8852, 721 total rounds)
```

---

*This is an automated monitoring report. All investment-related content is informational/educational only and does not constitute investment advice.*
