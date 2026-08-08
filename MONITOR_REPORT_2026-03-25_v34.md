# ODIN v6 & GUNGNIR v30 — Optimization Monitor Report
**Run**: v34 | **Date**: 2026-03-25 | **Status**: Automated Scheduled Check

---

## 1. Champion Model Status

### ODIN v6.1.0 (PDUFA Scoring) — CHAMPION
| Metric | Value | vs v5 Baseline |
|--------|-------|----------------|
| Holdout Brier | **0.1102** | +8.9% improvement (v5: 0.1210) |
| Holdout AUC | 0.897 | — |
| Architecture | Ridge C=15.0, 32 forward-selected features, isotonic calibrated |
| Training Events | 1,845 (cutoff 2025-01-01) |
| Holdout Events | 358 |

**New v6.1 Features** (7 beyond v5's 25): `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

### ODIN v6.0.0 (Initial Run — Superseded)
| Metric | Value | vs v5 Baseline |
|--------|-------|----------------|
| Holdout Brier | 0.1378 | **-7.45% WORSE** than v5 |
| Holdout AUC | 0.859 | -1.45% worse than v5 |
| Architecture | Multi-strategy ensemble (LGB+XGB+CatBoost+TabNet+Ridge), 65 features |

**Assessment**: v6.0 over-engineered with 65 features and GPU-heavy ensemble — classic overfitting. v6.1 correctly reverted to Ridge with aggressive feature selection (32 features), recovering the Brier advantage.

---

### GUNGNIR v30.1.0 (Phase Readout Scoring) — CHAMPION
| Metric | Value | vs v29 Baseline |
|--------|-------|-----------------|
| Champion Brier | **0.1008** | +56.9% improvement (v29: 0.2339) |
| Architecture | Ridge C=30, 26 features |
| Key Features | `has_ppm`, `des_orr`, `mod_cell_therapy`, `drug_last`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `des_pfs`, `sp_sr` |

### GUNGNIR v30.0.0 (Initial Run — Superseded)
| Metric | Value | vs v29 Baseline |
|--------|-------|-----------------|
| Holdout Brier | 0.1394 | +40.4% improvement |
| Holdout AUC | 0.8219 | +27.6% improvement (v29: 0.6439) |
| Architecture | Multi-strategy ensemble (LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge), 109 features |
| Holdout Events | 548 |

**Assessment**: Same pattern — v30.0 threw 109 features at a GPU ensemble and got good results. v30.1 stripped to 26-feature Ridge and crushed Brier from 0.1394 → 0.1008. Simpler models win on calibration.

---

## 2. LightGBM Autonomous Optimizer (models/lgb_champions/)

The autonomous LightGBM optimizer ran **721 rounds** (Feb 28 – Mar 2) with **8 champion promotions**:

| Round | WF AUC | WF Brier | Key Innovation |
|-------|--------|----------|----------------|
| 1 | 0.8514 | 0.1675 | Baseline with gene_x_cmc, orphan_x_surrogate |
| 5 | 0.8754 | 0.1543 | Added log_crl_rate, dropped oncology |
| 44 | 0.8796 | 0.1546 | Added ophthalmology, sponsor approvals |
| 134 | 0.8833 | 0.1886 | Rare disease features, mfg_x_prior_crl |
| 161 | 0.8836 | 0.1555 | s23_x_s6 interaction |
| **241** | **0.8852** | **0.2057** | **Current champion** — btd_x_oncology, v1067_minus_v1070 |

**Top Features by Importance**: `v1067_minus_v1070` (9,009), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091)

**Concern**: The LGB champion (round 241) has WF AUC 0.8852 but Brier 0.2057 — decent discrimination but poor calibration. The earlier round 5 champion had better calibration (Brier 0.1543). This confirms the Ridge approach in v6.1 (Brier 0.1102) is far superior for calibrated probability output.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | Connector settings block all 3 tools |
| FinBrain MCP (insider, sentiment, analyst) | **PARAMETER ERROR** | Pydantic validation — `req` parameter needs dict/object, serialization issue |
| ClinicalTrials.gov MCP | **WORKING** | Successfully queried orforglipron and vanzacaftor trials |

**Action Required**: 9realms MCP needs re-enabling in connector settings to run production scoring comparisons. FinBrain MCP has a serialization bug where the `req` parameter is received as a string instead of a dict.

---

## 4. ClinicalTrials.gov Validation

### Orforglipron (LLY) — Phase 3 Obesity
- **NCT05872620**: Phase 3 in obesity + T2D, COMPLETED (enrollment: 1,613, double-blind, randomized). Primary completion: 2025-08-08.
- **NCT07153471**: Phase 3 in obesity + knee OA, RECRUITING (enrollment: 800, single-masked, randomized). Primary completion: 2028-04.
- 9 total trials found in ClinicalTrials.gov for orforglipron obesity.

### Vanzacaftor/Tezacaftor/Deutivacaftor (VRTX) — CF
- **NCT05844449**: Long-term safety/efficacy OLE, ENROLLING BY INVITATION (174 participants, open-label). Primary completion: 2029-07-30.
- **NCT06299709**: Bioavailability study, COMPLETED (34 participants).
- PDUFA date: **2026-03-26 (TOMORROW)** — This is a high-conviction ODIN T1 candidate.

---

## 5. Summary & Recommendations

### Current Champions (No Change From Last Report)
- **ODIN v6.1.0**: Brier 0.1102 (8.9% better than v5) — Ridge C=15, 32 features
- **GUNGNIR v30.1.0**: Brier 0.1008 (56.9% better than v29) — Ridge C=30, 26 features

### Key Findings This Run
1. **No new model checkpoints** since Mar 2 (LGB optimizer stopped at round 721). No logs/ directory exists.
2. **9realms MCP is disabled** — cannot compare v5/v29 production scores against v6.1/v30.1 new model predictions. This is the highest-priority fix.
3. **FinBrain MCP has a parameter serialization bug** — the `req` parameter is failing Pydantic validation. Needs MCP server-side fix or updated tool schema.
4. **VRTX PDUFA is TOMORROW (Mar 26)** — vanzacaftor triple combo for CF. Historical VRTX CF approvals are extremely high-confidence.

### Recommended Next Steps
1. **Re-enable 9realms MCP** in connector settings to allow production scoring.
2. **Fix FinBrain MCP** parameter serialization (req dict vs string issue).
3. **Deploy v6.1 and v30.1 to production** if not already done — both significantly beat their baselines.
4. **Consider v6.2 iteration**: The LGB optimizer found `v1067_minus_v1070` and `historical_crl_rate` as strong signals — these could be tested as additional Ridge features in v6.2.
5. **GUNGNIR v30.2**: Explore adding CTGOV real data features (not used in v30.0/v30.1) — v29's CTGOV cache has 1,576 drugs with real trial design data that could further improve the 26-feature Ridge.
6. **Monitor VRTX PDUFA outcome** (Mar 26) for immediate holdout validation.

---

*Report generated automatically by the ODIN/GUNGNIR optimization monitor. Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
