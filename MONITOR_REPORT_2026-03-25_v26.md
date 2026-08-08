# ODIN v6 / GUNGNIR v30 Monitor Report — v26
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v25.md

---

## ⚡ Key Developments Since v25

1. **RCKT Kresladi decision in 3 days** — March 28 PDUFA is now 3 calendar days away (note: March 28 is a Saturday; FDA decisions on weekend PDUFA dates typically land by close of Friday March 27 or extended to Monday March 30 — watch closely). NCT03812263 (pivotal) remains **COMPLETED**, NCT06282432 (LTFU) remains **ACTIVE_NOT_RECRUITING**. No status changes. Decision is imminent.
2. **BIIB / IONS T-7 window is TODAY** — v25 flagged March 25 as the exit window for both April 3 PDUFA events. This remains the same-day window in v26. Both CT.gov packages confirmed stable: BIIB NCT04856982 (ACTIVE_NOT_RECRUITING), NCT07259980 (NOT_YET_RECRUITING); IONS NCT04136184 (COMPLETED).
3. **PRAX-628 readout T-5 days** — March 31 readout. NCT06908356 still **RECRUITING** (n=50, open-label). No change.
4. **All model champions unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
5. **LGB optimizer fully terminated (26th run)** — No `logs/` directory. 8 champion promotions total (last: round 241, ~2026-03-01). No new checkpoints beyond what was logged in v25.
6. **gungnir_champion_ladder.json flagged** — A workspace-root `gungnir_champion_ladder.json` file exists (separate from `models/lgb_champions/champion_ladder.json`) showing a GUNGNIR LGB candidate with AUC 0.9979 / Brier 0.0393 (round 9, 59 features). This file's top features — `sentiment_composite`, `price_adj_sentiment`, `primary_endpoint_met`, `indication_positive_rate`, `endpoint_met_phase3` — strongly suggest post-readout data leakage identical to the v25 GUNGNIR leak that was retired. This file should be treated as a leaky artifact and NOT used for production scoring.
7. **9realms MCP DISABLED (26th consecutive run)** — All ODIN/GUNGNIR live scoring blocked.
8. **FinBrain pydantic error persists (26th consecutive run)** — Server alive (v0.1.6 / sdk 0.1.8) but all data tools fail with `InsiderReq`/`SentimentsReq` model_type mismatch.

---

## 1. Executive Summary

RCKT's Kresladi (RP-L201) FDA decision is the most imminent catalyst in the watch list — March 28 is 3 calendar days out, though the actual FDA action window may come Friday March 27 (if PDUFA is moved to prior business day) or Monday March 30 (if extended). All CT.gov data for the pivotal study (NCT03812263, COMPLETED) and LTFU (NCT06282432, ACTIVE_NOT_RECRUITING) remain fully stable — no new status changes detected in this run.

The v25-flagged BIIB/IONS T-7 exit window falls today (March 25). Both April 3 PDUFA data packages are confirmed unchanged from v25 via CT.gov.

One new artifact concern: the workspace-root `gungnir_champion_ladder.json` file exhibits AUC 0.9979 — an almost certainly leaky score, given features encode post-readout outcomes (sentiment, endpoint_met). This file predates GUNGNIR v30 and should be archived or deleted to avoid confusion with the legitimate v30.1 champion (Brier 0.1008).

Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable. MCP infrastructure issues persist across 26 consecutive runs.

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

### ⚠️ Leaky Artifact Alert: gungnir_champion_ladder.json

A file `gungnir_champion_ladder.json` exists at the workspace root (not to be confused with `models/lgb_champions/champion_ladder.json`). It records a GUNGNIR LGB candidate with:
- WF AUC: **0.9979** (suspiciously near-perfect)
- WF Brier: **0.0393**
- Features: `sentiment_composite`, `price_adj_sentiment`, `primary_endpoint_met`, `indication_positive_rate`, `endpoint_met_phase3`, `os_phase3`, `phase3_efficacy_beat`, `strong_positive_phase3`

These features directly encode post-readout outcomes — this is the same class of data leakage that caused GUNGNIR v25 to be retired (AUC 0.988, also fake). This artifact predates the GUNGNIR v30 training run and should be **archived or deleted** to prevent confusion. The legitimate production champion remains GUNGNIR v30.1 (Brier 0.1008, 26 clean T-1 features).

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

**⚠️ Action pending (26th recommendation)**: Archive `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.

---

## 4. Live MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms `odin_score` | ❌ DISABLED | 26th consecutive run. Connector setting blocks tool. |
| 9realms `gungnir_score` | ❌ DISABLED | 26th consecutive run. |
| 9realms `system_status` | ❌ DISABLED | 26th consecutive run. |
| FinBrain `health` | ✅ ALIVE | v0.1.6 / sdk 0.1.8 — server responding. |
| FinBrain `insider_transactions_by_ticker` | ❌ SCHEMA ERROR | Pydantic `InsiderReq` model_type mismatch. 26th consecutive failure. |
| FinBrain `news_sentiment_by_ticker` | ❌ SCHEMA ERROR | Pydantic `SentimentsReq` model_type mismatch. 26th consecutive failure. |
| FinBrain `analyst_ratings_by_ticker` | ❌ NOT ATTEMPTED | Known schema error, skipped to conserve call budget. |
| ClinicalTrials.gov `get_study` (single NCT) | ✅ OK | All 6 catalyst studies fetched successfully. |
| ClinicalTrials.gov array input | ❌ REGEX FAIL | Array NCT IDs still fail regex validation. Single string only. |

**FinBrain root cause (persistent)**: MCP server expects `req` as pre-instantiated pydantic model instance; protocol serializes as JSON string. Fix requires server-side change.

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (**T-3 DAYS — DECISION IMMINENT**)

| Study | Status | Notes |
|-------|--------|-------|
| NCT03812263 (Phase 1/2 pivotal) | **COMPLETED** ✅ | LAD-I gene therapy. Autologous CD34+, lentiviral vector, ITGB2 gene. **UNCHANGED from v25.** |
| NCT06282432 (Long-term follow-up) | **ACTIVE_NOT_RECRUITING** ✅ | LTFU continuation. **UNCHANGED from v25.** |

**Assessment**: No changes detected. Full data package intact. Gene therapy for severe pediatric LAD-I rare disease — BTD + orphan designation, single-arm surrogate endpoint, small n. ODIN T2/T3 range. March 28 falls on Saturday — FDA action likely by Friday March 27 close of business or pushed to Monday March 30.

---

### BIIB — Tofersen (Qalsody) | PDUFA: April 3, 2026 (T-9 days)

| Study | Status | Notes |
|-------|--------|-------|
| NCT04856982 (Pre-symptomatic SOD1) | **ACTIVE_NOT_RECRUITING** ✅ | n=158. Phase 3 placebo-controlled. **UNCHANGED from v25.** |
| NCT07259980 (Post-market registry) | **NOT_YET_RECRUITING** ✅ | 7-year observational registry. **UNCHANGED from v25.** |

**Assessment**: Stable. T-7 exit window is today (March 25) per v25 strategy note.

---

### IONS — Eplontersen (Wainua) | PDUFA: April 3, 2026 (T-9 days)

| Study | Status | Notes |
|-------|--------|-------|
| NCT04136184 (NEURO-TTRansform pivotal) | **COMPLETED** ✅ | n=168 hATTR-PN. **UNCHANGED from v25.** |

**Assessment**: Stable. T-7 exit window is today per v25 strategy note.

---

### PRAX — PRAX-628 Phase 2 | Readout: March 31, 2026 (T-5 days)

| Study | Status | Enrollment | Notes |
|-------|--------|-----------|-------|
| NCT06908356 (Phase 2, focal/tonic-clonic) | **RECRUITING** ✅ | n=50 | Open-label. **UNCHANGED from v25.** |

**GUNGNIR v30.1 assessment**: Skeptical. `des_rct=0` (open-label, no placebo control), small n=50, early-phase design. High-risk readout. Expected T3/T4 score.

---

### CORT — Relacorilant | PDUFA: July 11, 2026 (T+107 days)

Not re-checked this run (stable through v25). Next check recommended at T-30 (June 11).

---

## 6. Upcoming Deployment Calendar

| Date | Ticker | Event | Type | Status |
|------|--------|-------|------|--------|
| **March 25 (TODAY)** | BIIB | T-7 exit window | PDUFA Apr 3 | ⚠️ SAME-DAY ACTION WINDOW |
| **March 25 (TODAY)** | IONS | T-7 exit window | PDUFA Apr 3 | ⚠️ SAME-DAY ACTION WINDOW |
| **March 27–28** | RCKT | Kresladi FDA Decision | PDUFA | **IMMINENT — watch Fri/Mon** |
| March 31 | PRAX | PRAX-628 Phase 2 readout | Phase readout | T-5 days |
| April 3 | BIIB | Tofersen PDUFA decision | PDUFA | T-9 days |
| April 3 | IONS | Eplontersen PDUFA decision | PDUFA | T-9 days |
| TBD 2026 | PRAX | Vormatrigine OLE (NCT07287163) | OLE (not pivotal) | Watch list — OLE only |
| July 11 | CORT | Relacorilant PDUFA | PDUFA | T+107 days |

---

## 7. Recommended Next Steps

1. **RCKT decision is effectively here**: March 28 falls on a Saturday. FDA may communicate by Friday March 27 EOB or push to Monday March 30. Monitor Rocket Pharmaceuticals press releases. No new CT.gov signals — data package fully intact going into decision.
2. **BIIB / IONS T-7 window is TODAY**: v25 and v26 both flag March 25 as the last same-day exit window for the April 3 double-header. This is the final notice from the monitor.
3. **Archive `gungnir_champion_ladder.json`**: The workspace-root file with AUC 0.9979 is a leaky artifact. Move to `archive/leaky/` or delete. Only GUNGNIR v30.1 (Brier 0.1008) should be treated as a valid champion.
4. **Enable 9realms MCP connector**: 26 consecutive disabled runs. Live ODIN/GUNGNIR scoring has never been collected via this monitor.
5. **Fix FinBrain MCP pydantic schema**: 26 consecutive data-collection failures. Server-side fix: accept `req` as plain dict instead of requiring a pre-instantiated pydantic model.
6. **Deploy ODIN v6.1 to MCP server**: Update `mcp_9realms_vnext.py` with v6.1 Ridge C=15 coefficients (32 features). v5 still running in production.
7. **Deploy GUNGNIR v30.1 to MCP server**: Update with Ridge C=30 + Trees 70/30 blend (26 features).
8. **Archive LGB optimizer artifacts (26th recommendation)**: Move `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `models/lgb_champions/champion_ladder.json` → `archive/lgb_optimizer/`.
9. **Clarify TGTX April 1 basis**: No CT.gov evidence found across any run. Likely commercial/milestone event — confirm manually.

---

## 8. Model Integrity Reminder

- **ODIN v6.1** is for **PDUFA events ONLY** (approval vs. CRL). Do not apply to phase readouts.
- **GUNGNIR v30.1** is for **phase readouts ONLY** (positive vs. negative). Do not apply to PDUFA decisions.
- All features are T-1 compliant (knowable before the event date).
- v5 (ODIN) and v29 (GUNGNIR) remain active production baselines until MCP server is updated with v6.1 and v30.1.
- `gungnir_champion_ladder.json` (workspace root, AUC 0.9979) is a **leaky artifact** — do not use for production scoring.

---

*This report is generated automatically by the odin-gungnir-monitor scheduled task. All data is for informational and research purposes only — not investment advice.*
