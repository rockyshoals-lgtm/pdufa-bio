# ODIN v6 / GUNGNIR v30 Optimization Monitor Report (v2)
**Date:** 2026-03-25 15:30 UTC | **Automated Scheduled Run**

---

## 1. Champion Model Status

### ODIN v6.1.0 — PDUFA Approval Scoring (CHAMPION)

| Metric | v5 (prod) | v6.0.0 | v6.1.0 (champion) |
|--------|-----------|--------|-------------------|
| Brier | 0.1210 | 0.1378 | **0.1102** |
| AUC | 0.9007 | 0.859 | 0.897 |
| Features | 25 | 65 | 32 |
| Architecture | Ridge C=1.5 | Multi-ensemble | Ridge C=15, isotonic |

**Brier improvement over v5:** +8.92% (0.1210 → 0.1102)

v6.1 added 7 features over v5's 25: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. The Ridge C=15 approach significantly outperformed v6.0's 65-feature kitchen-sink ensemble, which actually regressed vs v5.

### GUNGNIR v30.1.0 — Phase Readout Scoring (CHAMPION — STAGING ONLY)

| Metric | v29.0.0 (prod) | v30.0.0 | v30.1.0 (champion) |
|--------|----------------|---------|-------------------|
| Brier | 0.2339 | 0.1394 | **0.1008** |
| AUC | 0.6439 | 0.8219 | N/A |
| Features | 82 | 109 | 26 |
| Architecture | 6-strategy ensemble | Multi-ensemble + FT-Transformer | Ridge C=30 |

**Brier improvement over v29:** +56.9% (0.2339 → 0.1008)

**⚠️ CAUTION FLAG REMAINS:** The 56.9% improvement is extraordinary. This model should NOT be promoted to production until a full leakage audit and independent temporal cross-validation are completed.

### Pattern: Simplicity Wins
Both champions follow the same pattern: dramatically fewer features + simple Ridge regression crushes complex multi-model ensembles. v6.1 (32 features) beats v6.0 (65 features). v30.1 (26 features) beats v30.0 (109 features).

---

## 2. Autonomous Optimizer Status

### LightGBM Champion Ladder (Legacy — Feb 28 to Mar 1)
- 8 champion promotions across ~241 rounds
- Best AUC: 0.8852 (round 241) — but Brier degraded to 0.2057
- Best Brier: 0.1546 (round 5)
- AUC/Brier divergence indicates overfitting to rank ordering
- Heavy reliance on `v1067_minus_v1070` (importance 9009) — possible stacked-score leakage risk

### Annealing Optimizer (Legacy — Jan 29)
- Last checkpoint: `annealing_checkpoint_v95.json` (2026-01-29)
- Champion: ODIN v94 config (2026-01-29)
- No new runs detected since January

### No New Optimizer Activity Since Last Check
All optimizer directories show no new files since last monitoring cycle. The v6.1 and v30.1 deploy configs (timestamped today ~13:30 UTC) appear to be the most recent outputs.

---

## 3. MCP Connector Status

| Connector | Status | Issue |
|-----------|--------|-------|
| 9realms MCP | ❌ DISABLED | `odin_score`, `gungnir_score`, `system_status` all disabled in connector settings |
| FinBrain MCP | ❌ BROKEN | Pydantic serialization error — `req` param receives string instead of dict object |
| ClinicalTrials.gov MCP | ✅ WORKING | Successfully querying trial data |

**Action required:** Re-enable 9realms MCP and fix FinBrain MCP serialization to restore full monitoring capability.

---

## 4. ClinicalTrials.gov Catalyst Validation

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (Cystic Fibrosis)
- **NCT06154447** (VX-828): RECRUITING, 255 enrolled, primary completion **2026-04-23** (imminent)
- **NCT06299709**: Bioavailability/food effect study — COMPLETED (34 participants)
- **NCT05867147**: QT/QTc study — COMPLETED (56 participants)
- 8 total matching trials — robust pipeline with near-term completion milestones

### LLY — Orforglipron (Obesity / GLP-1)
- **NCT05869903** (ATTAIN): Phase 3 obesity, 3,127 enrolled, ACTIVE_NOT_RECRUITING, completion **2025-07** (results likely available or imminent)
- **NCT05872620**: Phase 3 obesity + T2D, 1,613 enrolled — COMPLETED (2025-08)
- **NCT07153471**: Phase 3 OA of the knee, RECRUITING, 800 planned, completion 2028-04
- **NCT06109311**: Phase 3 T2D + insulin, 546 enrolled — COMPLETED (2025-09)
- 9 total trials — extensive Phase 3 program with multiple completed readouts

Both high-conviction catalysts have confirmed active/completed registrational programs.

---

## 5. Recommendations

### Immediate (This Cycle)
1. **Promote ODIN v6.1 to production** — Clean 8.9% Brier improvement, parsimonious 32-feature Ridge model, validated on 358-event holdout. Ready for deployment.
2. **Audit GUNGNIR v30.1** — Run leave-one-year-out temporal CV. Check holdout/train overlap. Verify all 26 features are T-1 compliant. Do NOT promote until verified.
3. **Re-enable 9realms MCP** — Production scoring blind without it.
4. **Fix FinBrain MCP** — File bug on Pydantic `req` parameter serialization.

### Next Optimization Steps
5. **ODIN v6.2**: Isotonic calibration tuning on v6.1; explore `sponsor_rolling_approval_rate` interaction terms; try ElasticNet with the 32-feature set.
6. **GUNGNIR v30.2 (if v30.1 validates)**: Try ElasticNet; add CTGOV real features from v29's cache to the 26-feature Ridge; explore temperature scaling.
7. **Switch LGB optimizer objective** from AUC to Brier to fix the AUC/Brier divergence issue.

### Strategic
8. **Adopt Ridge-first policy** for all future model versions — complex ensembles are consistently losing to well-tuned Ridge on these datasets.
9. **Feature count budget**: Cap at ~30 features per model. Both champions prove parsimony > complexity.

---

*Automated monitoring report. Next scheduled run will re-attempt all MCP connections.*
*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
