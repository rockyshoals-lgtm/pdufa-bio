# ODIN v6 / GUNGNIR v30 Optimization Monitor Report (v3)
**Date:** 2026-03-25 ~16:00 UTC | **Automated Scheduled Run**

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
**Status:** No changes since last check. v6.1 remains champion with 32 forward-selected features and Ridge C=15.

Key v6.1 additions over v5: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

### GUNGNIR v30.1.0 — Phase Readout Scoring (CHAMPION — STAGING ONLY)

| Metric | v29.0.0 (prod) | v30.0.0 | v30.1.0 (champion) |
|--------|----------------|---------|-------------------|
| Brier | 0.2339 | 0.1394 | **0.1008** |
| AUC | 0.6439 | 0.8219 | N/A |
| Features | 82 | 109 | 26 |
| Architecture | 6-strategy ensemble | Multi-ensemble + FT-Transformer | Ridge C=30 |

**Brier improvement over v29:** +56.9% (0.2339 → 0.1008)
**Status:** No changes since last check. **CAUTION FLAG REMAINS** — 56.9% improvement requires full leakage audit before production promotion.

### Pattern Confirmation: Simplicity Wins
Both champions: dramatically fewer features + simple Ridge regression crushes complex multi-model ensembles.

---

## 2. MCP Tool Status

### 9realms MCP (odin_score, gungnir_score, system_status)
**STATUS: DISABLED** — All three 9realms MCP tools returned "This tool has been disabled in your connector settings." Production scoring via MCP is currently offline. This means no live v5 production scores can be compared against v6.1 candidates.

**Action needed:** Re-enable 9realms MCP connector to resume production score tracking and drift monitoring.

### FinBrain MCP (insider_transactions, news_sentiment, analyst_ratings)
**STATUS: PARAMETER FORMAT ERROR** — All FinBrain calls failed with Pydantic validation errors. The `req` parameter expects a dict/instance of InsiderReq/SentimentsReq but receives a string. This appears to be a serialization incompatibility.

**Action needed:** Investigate FinBrain MCP parameter passing format. The `req` schema is untyped (`{}`) which may cause issues.

### ClinicalTrials.gov MCP
**STATUS: OPERATIONAL** — Successfully queried trial data.

---

## 3. ClinicalTrials.gov Validation

### Suzetrigine (VRTX) — PDUFA Catalyst
- **NCT05553366** — Phase 3 bunionectomy acute pain, N=1,075, COMPLETED (2023-12-15)
- **NCT05558410** — Phase 3 abdominoplasty acute pain, N=1,118, COMPLETED (2023-08-25)
- **NCT05661734** — Open-label safety study, N=258, COMPLETED
- All pivotal trials completed. Suzetrigine was approved Jan 2026 — CTGOV data consistent.

### Orforglipron (LLY) — GUNGNIR Phase Readout Catalyst
- **NCT05313802** — Phase 1/2 healthy overweight, N=72, COMPLETED
- **NCT07153471** — Phase 3 obesity + knee OA, N=800, RECRUITING (expected completion 2028-04)
- **NCT05872620** — Phase 3 obesity + T2D, N=1,613, COMPLETED (2025-08-08)
- 9 total trials found. Multiple Phase 3 trials completed or recruiting — active pipeline confirmation.

---

## 4. Autonomous Optimizer Status

### LightGBM Champion Ladder (Legacy — Feb 28 to Mar 1)
- 8 champion promotions across 241 rounds (721 total iterations)
- Best WF AUC: 0.8852 (round 241, current champion) — but Brier degraded to 0.2057
- Best WF Brier: 0.1543 (round 5, early run)
- AUC/Brier divergence confirms overfitting to rank ordering, not calibration
- Top feature importance: `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940)
- **Stacked-score leakage risk**: Heavy reliance on v1067/v1070 stacked scores — these may encode holdout information

### No New Checkpoints
- No new files detected in `models/` since March 2, 2026
- No `logs/` directory exists — optimizer logging not configured
- The autonomous optimizer appears to have halted after round 241

---

## 5. Summary & Recommendations

### Current Standings (No Change)
| Model | Champion | Brier | vs Production | Status |
|-------|----------|-------|---------------|--------|
| ODIN | v6.1.0 | 0.1102 | +8.9% vs v5 | Ready for promotion |
| GUNGNIR | v30.1.0 | 0.1008 | +56.9% vs v29 | Staging — needs audit |

### Recommended Next Steps

1. **Re-enable 9realms MCP** — Production scoring is offline. Critical for drift monitoring between v5 (prod) and v6.1 (candidate).

2. **Fix FinBrain MCP parameter format** — Insider trading and sentiment data cannot be pulled. Investigate the untyped `req` parameter schema.

3. **GUNGNIR v30.1 Leakage Audit** — The 56.9% Brier improvement is extraordinary. Priority tasks:
   - Verify all 26 features are T-1 compliant (knowable before readout)
   - Run k-fold temporal cross-validation (not just single split)
   - Check for target leakage through `drug_last`, `j_last_neg`, `sp_sr` features
   - Compare calibration curves v29 vs v30.1

4. **ODIN v6.1 Promotion Path** — 8.9% Brier improvement is credible. Prepare MCP server update to embed v6.1 weights alongside v5 for A/B comparison.

5. **Create `logs/` directory** — Configure optimizer to write iteration logs for better monitoring.

6. **LightGBM Optimizer Restart** — Consider restarting with Brier as primary objective (not AUC) given the AUC/Brier divergence observed.

---

*Report generated automatically by ODIN/GUNGNIR monitoring task.*
*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
