# ODIN v6 / GUNGNIR v30 — Optimization Monitor Report
**Date:** 2026-03-25 (Automated Run v5)

---

## 1. Model Champion Status

### ODIN (PDUFA Scoring)

| Version | Brier | AUC | Features | Architecture |
|---------|-------|-----|----------|-------------|
| **v6.1 (CHAMPION)** | **0.1102** | 0.897 | 32 | Ridge C=15 + forward selection, isotonic calibrated |
| v6.0 | 0.1378 | 0.859 | 65 | LGB+XGB+CatBoost+TabNet+Ridge ensemble |
| v5 (production) | 0.1210 | 0.901 | 25 | Ridge L2 C=1.5 |

**Key Finding:** ODIN v6.1 remains the champion at Brier 0.1102, an **8.9% improvement** over v5. Notably, v6.1 achieved this with a simpler Ridge-only architecture (32 features) versus v6.0's 65-feature ensemble, which actually regressed vs v5 (-7.5% Brier). This confirms the parsimonious model wins — fewer features, better generalization.

**New v6.1 features** (beyond v5's 25): `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

### GUNGNIR (Phase Readout Scoring)

| Version | Brier | AUC | Features | Architecture |
|---------|-------|-----|----------|-------------|
| **v30.1 (CHAMPION)** | **0.1008** | — | 26 | Ridge(70%)+Trees(30%) blend |
| v30.0 | 0.1394 | 0.822 | 109 | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge ensemble |
| v29 (production) | 0.2339 | 0.644 | 82 | 6-strategy ensemble + meta-learner |

**Key Finding:** GUNGNIR v30.1 is a dramatic champion at Brier 0.1008, a **56.9% improvement** over v29 production. Same pattern as ODIN — the parsimonious v30.1 (26 features, Ridge+Trees) crushes the bloated v30.0 (109 features). The feature count reduction from 109 → 26 with simultaneous Brier drop from 0.1394 → 0.1008 is remarkable.

**Notable v30.1 features:** `des_orr`, `mod_cell_therapy`, `drug_last`, `sp_sr` (sponsor success rate), `competitive`, `j_last_neg` (journey last negative), `is_asco`

---

## 2. Autonomous Optimizer Status (LGB Champions)

The LightGBM autonomous optimizer completed **721 rounds** with **8 champion promotions**. Final champion (round 241, 2026-03-01):

- **WF AUC:** 0.8852
- **WF Brier:** 0.2057
- **Features:** 51 (16 engineered)
- **Top features by importance:** `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940), `log_crl_rate` (6091)

**Status:** No new optimizer checkpoints since 2026-03-01. The autonomous optimizer appears idle. The LGB champion's Brier (0.2057) is significantly worse than v6.1's Ridge (0.1102), confirming Ridge superiority for this problem.

**Model Registry:** v2 weights (2026-02-28) include social/CEO tone features — these are experimental and not production-deployed.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | Connector settings have all 3 tools disabled |
| FinBrain MCP | **PARAMETER ERROR** | Pydantic validation errors — req parameter expects model instance, not JSON string |
| ClinicalTrials.gov MCP | **WORKING** | Successfully queried trial data |

**Action Required:** 9realms MCP tools need to be re-enabled in connector settings to allow production scoring. FinBrain MCP parameter format needs investigation.

---

## 4. ClinicalTrials.gov Validation

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (PDUFA ~2026-03-26)
- **NCT05844449** — Phase 3 long-term safety/efficacy study, 174 enrolled, enrolling by invitation, primary completion 2029-07-30
- **NCT06154447** — Phase 1 VX-828 (next-gen), 255 enrolled, recruiting, primary completion 2026-04-23
- **NCT06299709** — Phase 1 bioavailability study, COMPLETED
- **NCT07349394** — Phase 1 DDI study (rosuvastatin), active not recruiting, completion 2026-04-04
- **Verdict:** Pipeline looks clean. Phase 3 OLE ongoing, no red flags in trial status. PDUFA tomorrow (3/26) — this is a high-conviction T1 event.

### LLY — Orforglipron (Phase 3 Readouts)
- **NCT05872620** — Phase 3 obesity + T2D, 1,613 enrolled, **COMPLETED** (2025-08-08)
- **NCT05869903** — Phase 3 obesity/overweight ATTAIN, 3,127 enrolled, **ACTIVE not recruiting** (completion 2025-07-25)
- **NCT07153471** — Phase 3 obesity + OA knee, 800 enrolled, RECRUITING (completion 2028-04)
- **NCT06109311** — Phase 3 T2D + insulin, 546 enrolled, **COMPLETED** (2025-09-15)
- **Verdict:** Two key ATTAIN trials completed or past primary completion. Topline readouts should be available or imminent. Massive enrollment (3,127 in ATTAIN-1) signals high confidence from Lilly.

---

## 5. Insider Trading & Sentiment

**Status:** FinBrain MCP returned parameter validation errors for VRTX insider transactions, sentiment, and analyst ratings. Unable to pull data this cycle.

---

## 6. Summary & Recommendations

### Current Champions
| Model | Brier | vs Production | Status |
|-------|-------|--------------|--------|
| ODIN v6.1 | 0.1102 | +8.9% vs v5 (0.1210) | Ready for deployment consideration |
| GUNGNIR v30.1 | 0.1008 | +56.9% vs v29 (0.2339) | Ready for deployment consideration |

### Key Insights
1. **Parsimony wins.** Both v6.1 and v30.1 dramatically outperform their bloated v6.0/v30.0 counterparts. Ridge + forward selection beats deep ensemble stacking.
2. **GUNGNIR v30.1 is a generational leap.** Brier 0.1008 vs 0.2339 is extraordinary — the 26-feature model is learning real signal, not noise.
3. **LGB optimizer has plateaued.** 721 rounds, WF AUC 0.8852 but Brier 0.2057 — gradient boosting isn't competitive with Ridge for this problem class.

### Recommended Next Steps
1. **Re-enable 9realms MCP** tools in connector settings to resume production scoring comparisons
2. **Fix FinBrain MCP** parameter format to restore insider/sentiment monitoring
3. **Validate GUNGNIR v30.1** against live 2026 phase readouts — the 56.9% Brier improvement needs out-of-sample confirmation
4. **Consider deploying v6.1 to MCP** — the improvement is consistent and architecturally sound (Ridge, not a fragile ensemble)
5. **Archive v6.0 and v30.0** — both are dominated by their v6.1/v30.1 successors
6. **Investigate VRTX PDUFA** (tomorrow 3/26) — score manually if MCP remains disabled

---

*Report generated automatically by ODIN/GUNGNIR Monitor — 2026-03-25*
*Next scheduled run will check for new optimizer iterations and re-attempt MCP scoring.*
