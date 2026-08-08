# ODIN v6 / GUNGNIR v30 — Monitor Report v9
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | -7.5% vs v5 (worse) | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

### Key Observations — No Changes Since v8

Champions remain **ODIN v6.1.0** (Brier 0.1102) and **GUNGNIR v30.1.0** (Brier 0.1008). No new deploy configs or model checkpoints detected since last run.

**ODIN v6.1**: Ridge C=15.0, 32 forward-selected features. 7 new features over v5 baseline: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Holdout AUC 0.897, trained on 1,845 events with 358-event holdout.

**GUNGNIR v30.1**: Ridge(70%)+Trees(30%) blend, 26 features. Clean, interpretable feature set spanning drug journey signals, trial design markers, therapeutic area, and modality. The 56.9% Brier improvement over v29 is the largest single-version jump in GUNGNIR history.

### Autonomous Optimizer Status

The `models/model_registry/` directory contains 8 champion checkpoints (`champion_r00001` through `champion_r00241`) and an `ensemble_pool/` directory, consistent with the autonomous optimizer runs that produced v6.1 and v30.1. No new checkpoints have appeared since the last monitor run. The optimizer appears idle.

---

## 2. Production MCP Scoring — DISABLED

The 9realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) remain **disabled in connector settings**. Cannot compare production v5/v29 scores against v6.1/v30.1 predictions.

**Action Required**: Re-enable 9realms MCP connector to resume production score monitoring and drift detection.

---

## 3. FinBrain MCP — PARAMETER INCOMPATIBILITY (Persistent)

FinBrain MCP `req` parameter still expects a Pydantic model instance that cannot be constructed through the MCP tool interface. All ticker-specific calls fail with validation errors. This is unchanged from v8.

**Action Required**: FinBrain MCP needs a schema fix or connector update to accept plain JSON objects.

**Deferred checks**:
- VRTX insider transactions (PDUFA 2026-03-28, 3 days away)
- LLY insider transactions (orforglipron Phase 3 readouts)
- ABBV insider transactions

---

## 4. ClinicalTrials.gov Validation

### Vertex — Vanzacaftor/Tezacaftor/Deutivacaftor (Cystic Fibrosis)

VRTX PDUFA is **March 28, 2026** (3 days away). ClinicalTrials.gov shows 6 registered trials for the VNZ/TEZ/D-IVA combination:

| NCT ID | Title | Phase | Enrollment | Status |
|--------|-------|-------|------------|--------|
| NCT06154447 | VX-828 evaluation in CF participants | Phase 1 | 255 | Recruiting |
| NCT06298709 | Granule bioavailability/food effect | Phase 1 | 34 | Completed |
| NCT05867147 | QT/QTc interval study | Phase 1 | 56 | Completed |
| NCT07349394 | Rosuvastatin PK interaction | Phase 1 | 18 | Active, not recruiting |
| NCT05844449 | Long-term safety/efficacy (1yr+) | Phase 3 | 174 | Enrolling by invitation |

The Phase 3 long-term safety study (NCT05844449, n=174) is enrolling by invitation with primary completion in July 2029, indicating confidence in the drug's trajectory. ODIN v5 would rate this as high-conviction given VRTX's experienced sponsor status, BTD, and priority review designations.

### Eli Lilly — Orforglipron (Obesity/T2D)

ClinicalTrials.gov shows 9 registered trials. Key Phase 3 programs:

| NCT ID | Title | Phase | Enrollment | Status |
|--------|-------|-------|------------|--------|
| NCT05869903 | ATTAIN-1: Obesity/overweight with comorbidities | Phase 3 | 3,127 | Active, not recruiting |
| NCT05872620 | Obesity/overweight with T2D | Phase 3 | 1,613 | Completed |
| NCT06109311 | T2D with insulin glargine | Phase 3 | 546 | Completed |
| NCT07153471 | Obesity/overweight with knee OA | Phase 3 | 800 | Recruiting |

**Critical signal**: NCT05869903 (ATTAIN-1, n=3,127) is the pivotal obesity trial — status is "Active, not recruiting" with primary completion July 2025. This trial has likely read out or will imminently. NCT05872620 (n=1,613, T2D+obesity) and NCT06109311 (n=546, insulin combo) are both marked **Completed**. Orforglipron readouts are a major GUNGNIR scoring opportunity.

---

## 5. Upcoming High-Priority Catalysts

| Catalyst | Ticker | Type | Date | Model | Priority |
|----------|--------|------|------|-------|----------|
| VNZ/TEZ/D-IVA CF approval | VRTX | PDUFA | 2026-03-28 | ODIN | HIGH — 3 days |
| Orforglipron obesity readout | LLY | Phase 3 | Q1-Q2 2026 | GUNGNIR | HIGH — imminent |

---

## 6. Recommended Next Steps

1. **Re-enable 9realms MCP** — Production scoring is critical for drift monitoring. The v6.1 and v30.1 champions cannot be validated against live production scores while the connector is disabled.

2. **Fix FinBrain MCP parameter schema** — The Pydantic model serialization issue blocks all ticker-level data (insider trades, sentiment, analyst ratings). This data would enrich feature engineering for v6.2/v30.2.

3. **Score VRTX PDUFA (March 28)** — Once MCP is re-enabled, run `odin_score` for VNZ/TEZ/D-IVA to get the production v5 probability. Expected T1/T2 given VRTX's strong profile (BTD + priority review + experienced sponsor).

4. **Score LLY orforglipron** — Run `gungnir_score` once Phase 3 results are announced. The ATTAIN-1 trial (n=3,127) is the key catalyst.

5. **Consider v6.2/v30.2 optimization** — Both champions show dramatic improvements with fewer features. Potential next steps include cross-validation stability testing, ensemble weight tuning for GUNGNIR's Ridge/Trees blend, and adding temporal features from recent approval rate trends.

6. **Deploy v6.1 to production MCP** — The current MCP server runs v5. A deployment plan should be drafted to swap in v6.1 weights while maintaining backward compatibility.

---

## 7. System Health

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | OK | `odin_v6_1_deploy.json` present and valid |
| GUNGNIR v30.1 deploy config | OK | `gungnir_v30_1_deploy.json` present and valid |
| Model registry | OK | 8 champion checkpoints + ensemble pool |
| 9realms MCP | DISABLED | Connector settings need update |
| FinBrain MCP | BROKEN | `req` parameter schema incompatibility |
| ClinicalTrials.gov MCP | OK | Successfully queried VRTX and LLY trials |
| Autonomous optimizer | IDLE | No new checkpoints since last run |

---

*Report generated automatically by scheduled monitor task. Next run will check for new optimizer output and re-attempt disabled/broken MCP connections.*

*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
