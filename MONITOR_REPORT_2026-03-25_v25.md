# ODIN v6 / GUNGNIR v30 Monitor Report — v25
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v24.md

---

## ⚡ Key Developments Since v24

1. **RCKT Kresladi decision T-2 DAYS** — March 28 PDUFA is now 2 days away. NCT03812263 (pivotal) remains **COMPLETED**, NCT06282432 (LTFU) remains **ACTIVE_NOT_RECRUITING**. No change in study status, no early FDA action detected. Decision is imminent.
2. **PRAX-628 readout T-5 DAYS** — March 31 readout approaching. NCT06908356 still **RECRUITING** (n=50, open-label). No status change detected.
3. **BIIB tofersen T-8 days** — April 3 PDUFA. NCT07259980 (post-market registry) status confirmed **NOT_YET_RECRUITING** — unchanged from v24. NCT04856982 (pre-symptomatic SOD1) remains **ACTIVE_NOT_RECRUITING** — unchanged.
4. **IONS eplontersen T-8 days** — April 3 PDUFA. NCT04136184 (NEURO-TTRansform pivotal) remains **COMPLETED**. NCT05071300 (long-term safety) remains **ACTIVE_NOT_RECRUITING** — unchanged.
5. **CORT relacorilant unchanged** — Both Phase 3 trials (NCT03697109 GRACE, NCT04308590 GRADIENT) remain **COMPLETED**. July 11 PDUFA on track.
6. **PRAX vormatrigine NCT07287163 clarified** — CT.gov confirms this is an **Open Label Extension** study (not Phase 2/3 as previously characterized). Title: "Open Label Extension Clinical Trial of Vormatrigine in Adult Patients With Epilepsy." Status: ENROLLING_BY_INVITATION. Correction from v24 language.
7. **All model champions unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
8. **LGB optimizer fully terminated (25th run)** — No `logs/` directory. No new champion files in `models/`. Fully dormant at 721 rounds, 8 promotions.
9. **9realms MCP DISABLED (25th consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector setting.
10. **FinBrain pydantic error persists (25th consecutive run)** — Server alive (v0.1.6 / sdk 0.1.8) but all data tools fail with `InsiderReq`/`SentimentsReq`/`AnalystRatingsReq` model_type mismatch.

---

## 1. Executive Summary

RCKT's March 28 Kresladi decision is now 2 days away — the final monitoring check before the event. CT.gov shows both key studies (NCT03812263 pivotal and NCT06282432 LTFU) are fully stable with no status changes. No early FDA signals detected. For the April 3 double-header (BIIB tofersen + IONS eplontersen), all CT.gov data remains unchanged from v24 — the new BIIB post-market registry (NCT07259980) is still NOT_YET_RECRUITING and unchanged in description. CORT relacorilant (July 11 PDUFA) data package also fully stable.

One correction from v24: the PRAX vormatrigine study NCT07287163 is confirmed to be an **open label extension**, not a Phase 2/3 trial — CT.gov title specifies "Open Label Extension Clinical Trial." This makes it a post-Phase 2 long-term safety/efficacy continuation, not a new pivotal readout event. It remains on the GUNGNIR watch list but should be categorized accordingly.

Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable. MCP infrastructure issues persist at 25 consecutive runs.

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

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF Brier | 0.2057 |
| Rounds since last promotion | ≥480 |
| Days since last promotion | ~24 days |
| `logs/` directory | DOES NOT EXIST |

**Assessment**: Fully terminated. LGB track best (0.2057 WF) comprehensively beaten by GUNGNIR v30.1 (0.1008 HO). No restart warranted.

**⚠️ Action pending (25th recommendation)**: Archive `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.

---

## 4. Live MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms `odin_score` | ❌ DISABLED | 25th consecutive run. Connector setting blocks tool. |
| 9realms `gungnir_score` | ❌ DISABLED | 25th consecutive run. |
| 9realms `system_status` | ❌ DISABLED | 25th consecutive run. |
| FinBrain `health` | ✅ ALIVE | v0.1.6 / sdk 0.1.8 — server responding. |
| FinBrain `insider_transactions_by_ticker` | ❌ SCHEMA ERROR | Pydantic `InsiderReq` model_type mismatch. 25th consecutive failure. |
| FinBrain `news_sentiment_by_ticker` | ❌ SCHEMA ERROR | Pydantic `SentimentsReq` model_type mismatch. 25th consecutive failure. |
| FinBrain `analyst_ratings_by_ticker` | ❌ SCHEMA ERROR | Pydantic `AnalystRatingsReq` model_type mismatch. 25th consecutive failure. |
| ClinicalTrials.gov `search_studies` | ⚠️ SCHEMA ERROR | `fields` parameter now failing with output schema mismatch. Single `get_study` calls working. |
| ClinicalTrials.gov `get_study` (single NCT) | ✅ OK | Single NCT ID string works. Array input still fails regex. |

**FinBrain root cause (persistent)**: MCP server expects `req` as pre-instantiated pydantic model instance; protocol serializes as JSON string. Fix requires server-side change.

**ClinicalTrials.gov `search_studies` regression**: `fields` parameter array now triggers output schema mismatch error that was not present in prior runs. `get_study` single-NCT calls remain fully functional. All catalyst validation completed via `get_study`.

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (**T-2 DAYS — DECISION IMMINENT**)

| Study | Status | Notes |
|-------|--------|-------|
| NCT03812263 (Phase 1/2 pivotal) | **COMPLETED** | LAD-I gene therapy (RP-L201 / Chim-CD18-WPRE). Autologous CD34+ cells, lentiviral vector, ITGB2 gene. Unchanged. |
| NCT06282432 (Long-term follow-up) | **ACTIVE_NOT_RECRUITING** | LTFU continuation. No status changes. |

**Assessment**: No changes detected from v24. Full data package intact. No early FDA action, no advisory committee, no hold signals. Gene therapy for severe pediatric LAD-I rare disease — ODIN T2/T3 candidate (small n, single-arm, surrogate endpoint but BTD + rare pediatric priority designation). Decision in 2 days.

---

### BIIB — Tofersen (Qalsody) | PDUFA: April 3, 2026 (T-8 days)

| Study | Status | Notes |
|-------|--------|-------|
| NCT04856982 (Pre-symptomatic SOD1) | **ACTIVE_NOT_RECRUITING** | n=158. Phase 3 placebo-controlled. Unchanged. |
| NCT07259980 (Post-market registry) | **NOT_YET_RECRUITING** | 7-year observational registry via Precision-ALS / ALS NHC. Unchanged from v24. |

**Assessment**: Stable. Post-market registry (NCT07259980) confirms Biogen is engaged commercially with post-AA commitments for Qalsody. T-7 exit window was flagged as March 25 in v24 — today is March 25, action window is now.

---

### IONS — Eplontersen (Wainua) | PDUFA: April 3, 2026 (T-8 days)

| Study | Status | Notes |
|-------|--------|-------|
| NCT04136184 (NEURO-TTRansform pivotal) | **COMPLETED** | n=168 hATTR-PN. Unchanged. |
| NCT05071300 (Long-term safety OLE) | **ACTIVE_NOT_RECRUITING** | n=151. Unchanged. |

**Assessment**: Stable. Clean data package. T-7 exit window flagged as today in v24.

---

### PRAX — PRAX-628 Phase 2 | Readout: March 31, 2026 (T-5 days)

| Study | Status | Enrollment | Notes |
|-------|--------|-----------|-------|
| NCT06908356 (Phase 2, focal/tonic-clonic) | **RECRUITING** | n=50 | Open-label. Unchanged from v24. |

**GUNGNIR v30.1 assessment**: Skeptical. `des_rct=0` (open-label, no placebo control), small n=50, early-phase design. High-risk readout. Score likely T3/T4.

---

### PRAX — Vormatrigine (NCT07287163) | Timing: TBD

| Study | Status | Enrollment | Notes |
|-------|--------|-----------|-------|
| NCT07287163 (OLE, focal/tonic-clonic/PGTC) | **ENROLLING_BY_INVITATION** | Unspecified | **CORRECTION: OLE (not Ph2/3)** — last updated 2025-12-17 |

**v24 correction**: Previously characterized as "Phase 2/3." CT.gov confirms this is an **Open Label Extension** of vormatrigine (PRAX-562, Nav1.6 blocker) — no new pivotal readout imminent. Remains a GUNGNIR future watch list item for when a Phase 2/3 pivotal readout is eventually initiated.

---

### CORT — Relacorilant | PDUFA: July 11, 2026 (T+108 days)

| Study | Status | Notes |
|-------|--------|-------|
| NCT03697109 (GRACE, Cushing DM/HTN) | **COMPLETED** | Phase 3 RCT, placebo-controlled. Unchanged. |
| NCT04308590 (GRADIENT, adrenal adenomas) | **COMPLETED** | Phase 3 RCT, placebo-controlled. Unchanged. |

**Assessment**: Strong dual Phase 3 data package, both double-blind placebo-controlled. ODIN T1/T2 candidate. No new CT.gov activity. Long runway to PDUFA.

---

## 6. Upcoming Deployment Calendar

| Date | Ticker | Event | Type | Status |
|------|--------|-------|------|--------|
| **March 25 (TODAY)** | BIIB | T-7 exit window | PDUFA Apr 3 | ⚠️ FINAL ACTION WINDOW |
| **March 25 (TODAY)** | IONS | T-7 exit window | PDUFA Apr 3 | ⚠️ FINAL ACTION WINDOW |
| **March 28** | RCKT | Kresladi FDA Decision | PDUFA | **T-2 DAYS — IMMINENT** |
| March 31 | PRAX | PRAX-628 Phase 2 readout | Phase readout | T-5 days |
| April 1 | TGTX | Pipeline event (TBD) | TBD | Basis unverified — no CT.gov evidence |
| April 3 | BIIB | Tofersen PDUFA decision | PDUFA | T-8 days |
| April 3 | IONS | Eplontersen PDUFA decision | PDUFA | T-8 days |
| TBD 2026 | PRAX | Vormatrigine OLE (NCT07287163) | OLE (not pivotal) | Watch list — OLE only |
| July 11 | CORT | Relacorilant PDUFA | PDUFA | T+108 days |

---

## 7. Recommended Next Steps

1. **BIIB / IONS T-7 action TODAY (FINAL)**: March 25 is the flagged exit window for both April 3 PDUFA events. If positions are held, this is the last same-day window notice — next run will be post-window.
2. **RCKT final pre-decision check complete**: No new CT.gov signals. All pre-decision monitoring done. Watch for Rocket press release or FDA advisory communication on/around March 28.
3. **PRAX-628 readout in 5 days**: Open-label Phase 2 (n=50, no RCT design) — GUNGNIR v30.1 would score skeptically. Pre-position strategy should account for high uncertainty.
4. **Enable 9realms MCP connector**: 25 consecutive disabled runs. Live ODIN/GUNGNIR scoring remains unavailable for every monitor run since inception. No live scoring data has ever been collected.
5. **Fix FinBrain MCP pydantic schema**: 25 consecutive data-collection failures. Zero insider flow, sentiment, or analyst data ever collected. Server-side fix: accept `req` as plain dict.
6. **Deploy ODIN v6.1 to MCP server**: Update `mcp_9realms_vnext.py` with v6.1 Ridge C=15 coefficients (32 features). v5 still running in production.
7. **Deploy GUNGNIR v30.1 to MCP server**: Update with Ridge C=30 + Trees 70/30 blend (26 features).
8. **Archive LGB optimizer artifacts (25th recommendation)**: Move `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.
9. **Correct PRAX vormatrigine classification**: Update any tracking documents to reflect NCT07287163 as OLE (not Phase 2/3). No imminent pivotal readout for vormatrigine.
10. **Clarify TGTX April 1 basis**: No CT.gov evidence found for active TGTX pipeline event. Confirm manually — likely commercial or milestone event.

---

## 8. Model Integrity Reminder

- **ODIN v6.1** is for **PDUFA events ONLY** (approval vs. CRL). Do not apply to phase readouts.
- **GUNGNIR v30.1** is for **phase readouts ONLY** (positive vs. negative). Do not apply to PDUFA decisions.
- All features are T-1 compliant (knowable before the event date).
- v5 (ODIN) and v29 (GUNGNIR) remain active production baselines until MCP server is updated with v6.1 and v30.1.

---

*This report is generated automatically by the odin-gungnir-monitor scheduled task. All data is for informational and research purposes only — not investment advice.*
