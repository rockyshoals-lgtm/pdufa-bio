# ODIN v6 / GUNGNIR v30 — Monitoring Report
**Date:** 2026-03-25 | **Run type:** Scheduled automated monitor

---

## 1. Model Status Summary

### ODIN (PDUFA Scoring)

| Version | Brier | AUC | Features | Architecture | Status |
|---------|-------|-----|----------|-------------|--------|
| **v5 (production)** | 0.1210 | 0.9007 | 25 | Ridge L2 C=1.5 | PRODUCTION CHAMPION |
| v6.0 | 0.1378 | 0.859 | 65 | LGB+XGB+CatBoost+TabNet+Ridge ensemble | **REGRESSION** (−7.5% Brier) |
| **v6.1** | **0.1102** | 0.897 | 32 | Ridge C=15 (forward-selected) | **NEW CHAMPION CANDIDATE** (+8.9% Brier) |

**Key finding:** ODIN v6.0's kitchen-sink 65-feature ensemble *overfit* and regressed vs v5. The v6.1 pivot to a simpler Ridge C=15 with 32 forward-selected features recovered and beat v5 by 8.9% on Brier. The 7 new features beyond v5's 25 are: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**Concern:** v6.1 AUC (0.897) is slightly below v5 AUC (0.9007) despite better Brier. This suggests improved calibration but slightly weaker discrimination. Worth investigating whether isotonic calibration is compressing the score distribution.

### GUNGNIR (Phase Readout Scoring)

| Version | Brier | AUC | Features | Architecture | Status |
|---------|-------|-----|----------|-------------|--------|
| **v29.0.0 (production)** | 0.2339 | 0.6439 | 82 | 6-strategy ensemble + meta-learner | PRODUCTION CHAMPION |
| v30.0 | 0.1394 | 0.8219 | 109 | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | +40.4% Brier improvement |
| **v30.1** | **0.1008** | — | 26 | Ridge(70%)+Trees(30%) blend | **NEW CHAMPION CANDIDATE** (+56.9% Brier) |

**Key finding:** GUNGNIR v30.1's Brier of 0.1008 is a massive improvement — from 0.2339 to 0.1008 is a 56.9% drop. The feature count dropped from 109 (v30.0) to just 26, suggesting heavy feature selection eliminated noise. The architecture is a Ridge(70%)+Trees(30%) blend, much simpler than v30.0's 6-model GPU ensemble.

**Caution flag:** A 56.9% Brier improvement is extraordinary. Before promoting to production, rigorous validation is needed:
- Verify temporal split integrity (strict T-1 compliance on all 26 features)
- Check for any accidental outcome leakage in new features (`drug_last`, `j_last_neg`, `sp_sr`)
- Run bootstrap confidence intervals on the holdout
- Verify the holdout set is identical between v29 and v30.1 (same 548 events?)

---

## 2. LightGBM Autonomous Optimizer (Legacy)

The `models/lgb_champions/` directory shows a completed optimization run from Feb 28–Mar 2:
- **241 rounds** completed, **8 champion promotions**
- Final champion: WF AUC 0.8852, WF Brier 0.2057 (round 241, hash `af6a433fc23e`)
- 51 features including engineered features (`v1067_minus_v1070`, `v1070_x_social`, etc.)
- Top importance: `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940)
- **Note:** This appears to be an ODIN-family LGB model, but its Brier (0.2057) is worse than v5 Ridge (0.1210). The LGB optimizer prioritized AUC over calibration.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | Connector settings have disabled these tools |
| FinBrain MCP (insider, sentiment, ratings) | **PARAM ERROR** | `req` parameter expects Pydantic model, serialization fails |
| ClinicalTrials.gov MCP | **WORKING** | Successfully queried trial data |

**Action needed:** 9realms MCP tools need to be re-enabled in connector settings. FinBrain MCP has a parameter schema mismatch that needs investigation.

---

## 4. ClinicalTrials.gov Catalyst Data

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (CF)
- **NCT06153447** (VX-828): Phase 1, RECRUITING, n=255, primary completion 2026-04-23
- **NCT06299709**: Phase 1 bioavailability study, COMPLETED (n=34)
- PDUFA date is **tomorrow (2026-03-26)** — this is a live catalyst

### LLY — Orforglipron (Obesity)
- **NCT05872620** (ATTAIN): Phase 3, COMPLETED (n=1,613), primary completion 2025-08-08 — readout should be available
- **NCT07153471**: Phase 3 in obesity + knee OA, RECRUITING (n=800), completion 2028-04
- Multiple Phase 3 programs active; oral GLP-1 is highest-profile pipeline asset

---

## 5. Recommendations

### Immediate (This Week)
1. **Re-enable 9realms MCP** — Production scoring tools are disabled; cannot verify v5/v29 production outputs
2. **VRTX PDUFA tomorrow** — Score VRTX through ODIN v5 production once MCP is re-enabled; this is the most imminent catalyst
3. **Fix FinBrain parameter schema** — The `req` parameter serialization issue blocks all insider/sentiment/ratings queries

### Model Validation (Before Any Promotion)
4. **ODIN v6.1 validation checklist:**
   - Confirm holdout set is identical 358 events as v5
   - Run 5-fold temporal CV to confirm Brier < 0.115 across folds
   - Investigate AUC drop (0.897 vs 0.9007) — is isotonic calibration compressing tails?
   - Test tier spread: does v6.1 maintain T1≥85% approval rate and T4≤40%?

5. **GUNGNIR v30.1 validation checklist (HIGH PRIORITY):**
   - 56.9% Brier improvement demands skepticism — verify no leakage
   - Audit `drug_last`, `j_last_neg`, `sp_sr` features for temporal integrity
   - Confirm holdout is same 548 events as v30.0 (not a subset)
   - Run permutation importance to identify if improvement comes from 1-2 dominant features
   - Bootstrap 95% CI on Brier to quantify uncertainty

### Next Optimization Steps
6. **ODIN v6.2 ideas:** Try ElasticNet blend with Ridge C=15 as anchor; explore `sponsor_rolling_approval_rate` interactions
7. **GUNGNIR v30.2 ideas:** If v30.1 validates clean, try adding CTGOV real data features back (v29 had 10 CTGOV features) to the lean 26-feature Ridge backbone

---

*Report generated automatically. All model outputs are informational/educational and do not constitute investment advice.*
