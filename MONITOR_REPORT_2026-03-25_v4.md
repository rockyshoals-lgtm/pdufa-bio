# ODIN v6 / GUNGNIR v30 Optimization Monitor Report (v4)
**Date:** 2026-03-25 ~20:00 UTC | **Automated Scheduled Run**

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
**Status:** STABLE — No new checkpoints or changes detected since v3 report. v6.1 remains champion.

Key v6.1 additions over v5: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

### GUNGNIR v30.1.0 — Phase Readout Scoring (CHAMPION — STAGING ONLY)

| Metric | v29.0.0 (prod) | v30.0.0 | v30.1.0 (champion) |
|--------|----------------|---------|-------------------|
| Brier | 0.2339 | 0.1394 | **0.1008** |
| AUC | 0.6439 | 0.8219 | N/A |
| Features | 82 | 109 | 26 |
| Architecture | 6-strategy ensemble | Multi-ensemble + FT-Transformer | Ridge C=30 |

**Brier improvement over v29:** +56.9% (0.2339 → 0.1008)
**Status:** STABLE — No new checkpoints detected. **CAUTION FLAG REMAINS** — 56.9% improvement requires full leakage audit before production promotion.

### Pattern Confirmation: Simplicity Wins
Both champions: dramatically fewer features + simple Ridge regression crushes complex multi-model ensembles. v6.0→v6.1 cut features from 65→32; v30.0→v30.1 cut from 109→26.

---

## 2. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms (`odin_score`, `gungnir_score`, `system_status`) | **DISABLED** | Connector settings have all 9realms tools disabled this run |
| FinBrain (insider, sentiment, ratings) | **ERROR** | Pydantic serialization issue — `req` param expects model instance, not JSON string |
| ClinicalTrials.gov | **WORKING** | Successfully querying trial data |

**Action needed:** 9realms MCP connector needs to be re-enabled for production scoring. FinBrain MCP has a persistent parameter format issue that should be investigated.

---

## 3. Optimizer Infrastructure

| Check | Result |
|-------|--------|
| `models/` directory | Present — contains `lgb_champions/`, `model_registry/`, `lightgbm_challenger_v1.pkl`, `v1071_GOLD_STANDARD.pkl` |
| `logs/` directory | **Not found** — no optimizer iteration logs detected |
| New checkpoints since v3 | **None** — no new `.pkl` or `.json` files in models/ |

No autonomous optimizer runs appear to be active. The models/ directory timestamps are from Feb 28 – Mar 13, indicating no recent optimizer activity.

---

## 4. ClinicalTrials.gov Validation — Key Catalysts

### Suzetrigine (VRTX) — Pain / PDUFA Candidate
12 total trials found. Key active/recruiting studies:

| NCT ID | Title | Status | N | Masking | Primary Completion |
|--------|-------|--------|---|---------|-------------------|
| NCT06696443 | Long-term safety/effectiveness in DPN | ACTIVE_NOT_RECRUITING | 455 | Open-label | 2027-01-25 |
| NCT07231419 | Efficacy/safety for DPN pain | RECRUITING | 734 | Quadruple-blind | 2027-04-06 |
| NCT05553366 | Acute pain post-bunionectomy (Ph3) | COMPLETED | 1,075 | Double-blind | 2023-12-15 |
| NCT05558410 | Acute pain post-abdominoplasty (Ph3) | COMPLETED | 1,118 | Quadruple-blind | 2023-08-25 |

**Note:** Suzetrigine already FDA-approved (Jan 2025) for acute pain. New DPN trials (NCT07231419) are for label expansion — NDA supplement potential for 2027+.

### Orforglipron (LLY) — Obesity / Phase 3
9 total trials found. Key studies:

| NCT ID | Title | Status | N | Masking | Primary Completion |
|--------|-------|--------|---|---------|-------------------|
| NCT05869903 | ATTAIN — Obesity/overweight with comorbidities | ACTIVE_NOT_RECRUITING | 3,127 | Double-blind | 2025-07-25 |
| NCT05872620 | Obesity/overweight + T2D | COMPLETED | 1,613 | Double-blind | 2025-08-08 |
| NCT07153471 | Obesity/overweight + knee OA | RECRUITING | 800 | Single-blind | 2028-04 |

**Note:** The pivotal ATTAIN trial (N=3,127) has primary completion dated July 2025 — readout likely already occurred or imminent. This is the key GUNGNIR scoring candidate.

---

## 5. Insider Trading & Sentiment

**FinBrain MCP unavailable this run** due to parameter serialization error. Unable to pull insider transactions, news sentiment, or analyst ratings for VRTX, LLY, ABBV. This is a recurring issue — the MCP expects Pydantic model instances rather than JSON-serialized dictionaries.

---

## 6. Summary & Recommendations

### Current State
- **ODIN v6.1:** Brier 0.1102 — STABLE champion, +8.9% over v5 production
- **GUNGNIR v30.1:** Brier 0.1008 — STABLE champion (staging), +56.9% over v29 production
- **No new optimizer activity** since last monitoring run
- **9realms MCP disabled** — cannot verify production scoring drift

### Recommended Next Steps

1. **Re-enable 9realms MCP** — Production scoring tools are disabled. Need these for drift monitoring and live score comparisons.

2. **Fix FinBrain MCP serialization** — The `req` parameter expects a Pydantic model instance. Either the MCP server needs a fix to accept JSON dicts, or the calling convention needs updating.

3. **GUNGNIR v30.1 leakage audit** — The 56.9% improvement flag remains unresolved. Before promoting to production, need:
   - Verify all 26 features are T-1 compliant (knowable before readout)
   - Check for any outcome-derived features in the training pipeline
   - Validate the Brier score with a fresh temporal split

4. **Monitor orforglipron readout** — The ATTAIN trial (NCT05869903, N=3,127) primary completion was July 2025. If data hasn't been announced, this is a high-priority GUNGNIR scoring candidate.

5. **Restart autonomous optimizer** — No optimizer logs or new checkpoints detected. Consider restarting optimization runs for both models to explore further feature engineering.

---

*Report generated automatically by scheduled monitor task. Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
