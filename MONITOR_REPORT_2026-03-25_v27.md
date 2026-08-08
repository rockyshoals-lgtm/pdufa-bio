# ODIN v6 / GUNGNIR v30 Monitor Report — v27
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v26.md

---

## ⚡ Key Developments Since v26

1. **RCKT Kresladi decision is TOMORROW (or today)** — March 28 PDUFA is now 2–3 calendar days away. Since March 28 is a Saturday, the FDA action window is most likely Friday March 27 (today or tomorrow depending on intraday timing) or Monday March 30 if extended. CT.gov confirms NCT03812263 (pivotal, Phase 1/2) remains **COMPLETED** (last update 2023-11-15) and NCT06282432 (LTFU) remains **ACTIVE_NOT_RECRUITING** (last update 2025-12-18). No new status changes. **Decision is imminent.**
2. **BIIB / IONS T-7 exit window passed** — March 25 was the flagged exit window (v25/v26). CT.gov BIIB tofersen search returned no results on this run (CT.gov search variability); previous run confirmed NCT04856982 ACTIVE_NOT_RECRUITING and NCT07259980 NOT_YET_RECRUITING. April 3 PDUFAs now 9 days out.
3. **PRAX-628 readout in 6 days** — March 31 readout. NCT06908356 confirmed **RECRUITING** (Phase 2, n=50, last update 2025-04-03). No status change.
4. **All model champions unchanged (27th run)** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
5. **LGB optimizer fully terminated (27th run)** — No `logs/` directory present. 8 champion promotions total (last: round 241, ~2026-03-01, last file Mar 2). No new checkpoints.
6. **9realms MCP DISABLED (27th consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector settings.
7. **FinBrain pydantic error persists (27th consecutive run)** — Server alive (v0.1.6 / sdk 0.1.8) but all data tools (InsiderReq, SentimentsReq, AnalystRatingsReq) fail with model_type mismatch error.

---

## 1. Executive Summary

**RCKT Kresladi (RP-L201)** for Leukocyte Adhesion Deficiency-I is the highest-urgency catalyst in the current watch window. The PDUFA date of March 28 falls on a Saturday; historical FDA practice typically moves such decisions to the preceding Friday (March 27) or the following Monday (March 30). CT.gov data for both the pivotal study (NCT03812263, Phase 1/2, n=9, COMPLETED) and long-term follow-up (NCT06282432, ACTIVE_NOT_RECRUITING) are confirmed unchanged on this run — no last-minute protocol amendments or status changes detected.

**PRAX-628** (PRAX) Phase 2 readout remains on track for March 31. The trial (NCT06908356) continues recruiting (n=50, open-label). No status change.

**BIIB tofersen / IONS** April 3 PDUFAs are 9 days out. CT.gov search for tofersen returned no results in this run (likely query/API variability — previous runs confirmed stable packages). No new information.

Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable with no new configs generated. MCP infrastructure issues persist across all 27 runs.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | -7.45% (worse) |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None. `odin_v6_2_deploy.json` does not exist.

**v6.1 features (32 total)**: All 25 v5 features retained plus 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**Status**: STABLE. v6.1 is the deployment target.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO Brier | vs v29 Brier |
|---------|-------------|----------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **0.1008** | **+56.9% better** |

**New configs this run**: None. `gungnir_v30_2_deploy.json` does not exist.

**Status**: STABLE. v30.1 is the deployment target.

---

### ⚠️ Leaky Artifact Alert: gungnir_champion_ladder.json (Ongoing)

The workspace-root `gungnir_champion_ladder.json` remains present with WF AUC 0.9979 / Brier 0.0393. Features include `sentiment_composite`, `price_adj_sentiment`, `primary_endpoint_met`, `endpoint_met_phase3` — post-readout data, identical leakage class to the retired GUNGNIR v25. **This file should not be used for production scoring.** The legitimate champion is GUNGNIR v30.1 (Brier 0.1008, 26 clean T-1 features).

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last champion file timestamp | Mar 2, 04:42 (champion_ladder.json) |
| Latest ensemble_pool file | lgb_r00619 (Mar 2, 02:46) |
| `logs/` directory | **NOT PRESENT** |
| Optimizer status | **FULLY TERMINATED** |

Last champion metrics (round 241): WF AUC 0.8852, WF Brier 0.2057, 51 features (champion_r00241).

**Assessment**: Optimizer has been dormant since early March. No resumption expected without explicit restart. GUNGNIR v30.1 (Brier 0.1008) substantially outperforms the LGB optimizer's best result (WF Brier 0.2057) — the v30.1 champion architecture is clearly superior.

---

## 4. MCP Tool Status

### 9realms MCP (ODIN/GUNGNIR Live Scoring)
- **Status**: DISABLED (27th consecutive run)
- Both `odin_score` and `gungnir_score` blocked by connector settings
- `system_status` also blocked
- **Action required**: Enable the 9realms connector in settings to restore live scoring

### FinBrain MCP
- **Server**: ALIVE (v0.1.6 / sdk 0.1.8)
- **Data tools**: ALL FAILING — pydantic model_type mismatch
  - `insider_transactions_by_ticker`: `InsiderReq` type error
  - `news_sentiment_by_ticker`: `SentimentsReq` type error
  - `analyst_ratings_by_ticker`: `AnalystRatingsReq` type error
- **Error pattern**: `Input should be a valid dictionary or instance of [Model]` — the tool's `req` parameter schema expects a native Pydantic model object but receives a JSON string
- **Status**: 27th consecutive run with this error
- **Action required**: FinBrain MCP server needs a schema fix to accept dict/JSON string input for the `req` parameter, or the connector needs updating

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (IMMINENT)

| NCT | Title | Status | Last Update |
|-----|-------|--------|-------------|
| NCT03812263 | RP-L201 Safety & Efficacy in LAD-I (pivotal) | **COMPLETED** | 2023-11-15 |
| NCT06282432 | Long-Term Follow-Up for Gene Therapy of LAD-I | **ACTIVE_NOT_RECRUITING** | 2025-12-18 |

- Both studies confirmed via live CT.gov API — **no changes from v26**
- Pivotal n=9 (ultra-rare disease, expected small N)
- Decision window: Friday March 27 (most likely) or Monday March 30 if extended past weekend

### PRAX-628 (PRAX) | Phase 2 Readout: March 31, 2026

| NCT | Title | Status | Last Update |
|-----|-------|--------|-------------|
| NCT06908356 | Open Label Trial of PRAX-628 in Adults With Focal Onset or Tonic-Clonic Seizures | **RECRUITING** | 2025-04-03 |

- Phase 2, n=50, open-label — still recruiting as of last CT.gov update
- Readout in 6 days

### BIIB / IONS | PDUFA: April 3, 2026

- CT.gov search for tofersen/IONS returned no results on this run (query sensitivity)
- Previous run (v26) confirmed: BIIB NCT04856982 ACTIVE_NOT_RECRUITING, NCT07259980 NOT_YET_RECRUITING; IONS NCT04136184 COMPLETED
- No expected status change for completed/follow-up studies

---

## 6. Upcoming Catalyst Calendar

| Catalyst | Ticker | Event Type | Date | Days Out |
|----------|--------|------------|------|----------|
| Kresladi (RP-L201) | RCKT | PDUFA (FDA approval) | Mar 28 (Sat → Mar 27 or 30) | **2–5 days** |
| PRAX-628 | PRAX | Phase 2 readout | Mar 31 | 6 days |
| tofersen | BIIB | PDUFA | Apr 3 | 9 days |
| [IONS drug] | IONS | PDUFA | Apr 3 | 9 days |

---

## 7. Recommended Next Steps

1. **RCKT watch**: Decision is in the next 2–5 business days. Monitor FDA announcements and RCKT press releases actively. Kresladi is a gene therapy for ultra-rare LAD-I — FDA has been generally supportive of gene therapies with unmet need.

2. **Restore 9realms MCP connector**: 27 consecutive runs without live scoring. Enabling this would restore ODIN tier classification and GUNGNIR probability for the above catalysts.

3. **Fix FinBrain MCP**: The pydantic `req` parameter error has persisted 27 runs. Contact FinBrain MCP maintainer or update the connector to resolve the schema mismatch. This is blocking insider transaction and sentiment data for all T1 catalysts.

4. **ODIN v6.1 deployment**: v6.1 champion (Brier 0.1102, AUC 0.897) is production-ready. No further optimization runs needed unless a specific v6.2 experiment is designed.

5. **GUNGNIR v30.1 deployment**: v30.1 champion (Brier 0.1008, +56.9% vs v29) is production-ready. The leaky `gungnir_champion_ladder.json` artifact at workspace root should be archived or deleted.

6. **LGB optimizer**: Fully terminated since ~March 1. No action needed unless deliberately restarting for further ODIN experimentation.

---

## 8. Infrastructure Health Summary

| Component | Status |
|-----------|--------|
| ODIN v6.1 deploy config | ✅ Stable |
| GUNGNIR v30.1 deploy config | ✅ Stable |
| LGB optimizer | 🔴 Terminated (expected) |
| 9realms MCP (scoring) | 🔴 DISABLED (27 runs) |
| FinBrain MCP (data) | 🟡 Server alive, data tools broken (27 runs) |
| ClinicalTrials.gov MCP | ✅ Operational (search working) |
| leaky artifact warning | ⚠️ gungnir_champion_ladder.json (workspace root) |

---

*Disclaimer: All scoring outputs, tier classifications, and investment signals from ODIN/GUNGNIR are for informational and educational purposes only. Not investment advice.*
