# ODIN v6 / GUNGNIR v30 Monitor Report — v24
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v23.md

---

## ⚡ Key Developments Since v23

1. **RCKT Kresladi decision T-3 days** — March 28 PDUFA remains imminent. CT.gov confirms both NCT03812263 (pivotal, COMPLETED) and NCT06282432 (LTFU, ACTIVE_NOT_RECRUITING) are **unchanged** from v23. No early FDA action detected.
2. **BIIB tofersen — NEW observational registry detected** — NCT07259980 ("Long-Term Safety of Tofersen in SOD1-ALS") posted NOT_YET_RECRUITING with last update 2026-03-02 (3 weeks ago). This is a 7-year post-market registry via the Precision-ALS programme and ALS/MND NHC consortium. Consistent with post-accelerated-approval commitments. Does not affect the April 3 PDUFA decision but confirms active post-approval infrastructure.
3. **IONS eplontersen pipeline stable** — NCT05071300 (long-term safety) remains ACTIVE_NOT_RECRUITING (last updated 2025-12-04, n=151). NCT04136184 (NEURO-TTRansform pivotal) remains COMPLETED (last updated 2024-12-13). No new study activity detected for April 3 catalyst.
4. **PRAX vormatrigine Phase 2/3 detected** — NEW: NCT07287163 ("Vormatrigine in Adult Patients With Epilepsy"), ENROLLING_BY_INVITATION, n=700, last updated 2025-12-17. Large study by Praxis — separate from PRAX-628. Adds to PRAX watch list.
5. **PRAX-628 Phase 2 unchanged** — NCT06908356 still RECRUITING (n=50, last updated 2025-04-03). March 31 readout remains on track. No acceleration or early termination signals.
6. **All model champions unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
7. **LGB optimizer fully terminated (24th run)** — No logs/ directory, no new champion files in models/. Fully dormant.
8. **9realms MCP disabled (24th consecutive run)** — All ODIN/GUNGNIR live scoring blocked.
9. **FinBrain pydantic error persists (24th consecutive run)** — Server alive (v0.1.6 / sdk 0.1.8) but all data tools fail with `InsiderReq`/`SentimentsReq`/`AnalystRatingsReq` model_type mismatch.

---

## 1. Executive Summary

The system is now 3 days from the RCKT Kresladi (RP-L201) FDA decision on March 28. CT.gov confirms both pivotal studies are fully intact and unchanged — no early action signals, no FDA advisory updates. For the April 3 BIIB/IONS decisions, a meaningful new datapoint has emerged: Biogen filed a new long-term observational registry (NCT07259980) for tofersen/Qalsody on 2026-03-02, consistent with post-accelerated-approval commitments for SOD1-ALS. This does not predict the April 3 outcome but confirms commercial and regulatory engagement remains active. IONS eplontersen data package is stable. A new large Praxis study (vormatrigine, n=700) has been detected, adding a second watchlist item for the PRAX pipeline beyond PRAX-628.

Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable. MCP infrastructure issues persist at 24 consecutive runs. FinBrain and 9realms MCP remain fully offline for data collection purposes.

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

**v30.1 key features (26 total)**: `drug_last`, `sp_sr`, `j_last_neg`, `era_post24`, `des_surrogate`, `orr_x_onc`, `is_asco`, `competitive`, `mod_gene_therapy`, `has_ppm`, `des_orr`, `mod_cell_therapy`, `des_primary_ep`, `year`, `ta_n3_log`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `des_pfs`, `mod_antibody`, `month`, `ta_infectious`, `ta_rare`, `p3_x_cns`, `des_topline`.

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

**⚠️ Action pending (24th recommendation)**: Archive `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.

---

## 4. Live MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms `odin_score` | ❌ DISABLED | 24th consecutive run. Connector setting blocks tool. |
| 9realms `gungnir_score` | ❌ DISABLED | 24th consecutive run. |
| 9realms `system_status` | ❌ DISABLED | 24th consecutive run. |
| FinBrain `health` | ✅ ALIVE | v0.1.6 / sdk 0.1.8 — server responding. |
| FinBrain `insider_transactions_by_ticker` | ❌ SCHEMA ERROR | Pydantic `InsiderReq` model_type mismatch. 24th consecutive failure. |
| FinBrain `news_sentiment_by_ticker` | ❌ SCHEMA ERROR | Pydantic `SentimentsReq` model_type mismatch. 24th consecutive failure. |
| FinBrain `analyst_ratings_by_ticker` | ❌ SCHEMA ERROR | Pydantic `AnalystRatingsReq` model_type mismatch. 24th consecutive failure. |
| ClinicalTrials.gov `search_studies` | ✅ OK | Working normally. Primary external data source. |
| ClinicalTrials.gov `get_study` | ✅ OK | Single NCT ID string input works (array input fails regex). |

**FinBrain root cause (persistent)**: The MCP server expects `req` as a pre-instantiated pydantic model instance, but the protocol serializes it as a JSON string. Fix requires server-side change: accept `req` as a plain dict and construct the model internally. No client-side workaround is possible.

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (**T-3 DAYS — DECISION IMMINENT**)

| Study | Status | Notes |
|-------|--------|-------|
| NCT03812263 (Phase 1/2 pivotal) | **COMPLETED** | LAD-I gene therapy (RP-L201 / Chim-CD18-WPRE). Autologous CD34+ cells, lentiviral vector. Unchanged. |
| NCT06282432 (Long-term follow-up) | **ACTIVE_NOT_RECRUITING** | LTFU continuation. No status changes since v23. |

**Assessment**: No changes detected. Full data package intact. No early FDA action, no advisory committee, no hold signals. Gene therapy for severe pediatric rare disease — ODIN would score T3/T2 due to small n=9, single-arm design, but surrogate endpoint + rare pediatric priority designation may support T2 classification. Decision in 3 days.

---

### BIIB — Tofersen (Qalsody) | PDUFA: April 3, 2026

| Study | Status | Last Updated | Notes |
|-------|--------|-------------|-------|
| NCT03070119 (Long-term tofersen) | COMPLETED | 2025-08-29 | n=139 |
| NCT04856982 (Pre-symptomatic SOD1) | ACTIVE_NOT_RECRUITING | 2025-03-07 | n=158 |
| **NCT07259980** (Post-market registry) | **NOT_YET_RECRUITING** | **2026-03-02** | **NEW — 7-year obs. registry** |

**NEW — NCT07259980**: Biogen filed a new observational registry-based post-market safety study for tofersen/Qalsody on 2026-03-02 (3 weeks ago). 7-year study tracking long-term safety of participants via Precision-ALS and ALS/MND NHC consortia. This is consistent with FDA post-accelerated-approval commitments and does not predict the April 3 outcome. It does confirm active commercial-stage regulatory engagement for Qalsody.

**T-9 days to PDUFA. T-7 exit window was flagged as TODAY in v23** — action may already be taken.

---

### IONS — Eplontersen (Wainua) | PDUFA: April 3, 2026

| Study | Status | Last Updated | Notes |
|-------|--------|-------------|-------|
| NCT04136184 (NEURO-TTRansform pivotal) | COMPLETED | 2024-12-13 | n=168 hATTR-PN |
| NCT05071300 (Long-term safety) | ACTIVE_NOT_RECRUITING | 2025-12-04 | n=151 |

**Assessment**: Stable. NEURO-TTRansform pivotal data complete; long-term study ongoing. No new CT.gov activity since v23. T-9 days to PDUFA.

---

### PRAX — PRAX-628 Phase 2 | Readout: March 31, 2026 (**T-6 DAYS**)

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT06908356 (Phase 2, focal/tonic-clonic) | RECRUITING | n=50 | 2025-04-03 |

**Assessment**: Unchanged. Open-label Phase 2 (no placebo control). GUNGNIR v30.1 would score this skeptically: `des_rct=0` (no RCT), small open-label n=50, `mod_gene_therapy=0`, early-stage. High-risk readout.

**NEW — PRAX Vormatrigine (NCT07287163)**: ENROLLING_BY_INVITATION, n=700, last updated 2025-12-17. Large Phase 2/3-scale epilepsy study for vormatrigine (PRAX-562, Nav1.6 blocker). Completely separate from PRAX-628. Adding to GUNGNIR future watch list alongside PRAX-628 — vormatrigine readout timing TBD.

---

### CORT — Relacorilant | PDUFA: July 11, 2026

| Study | Status | Last Updated |
|-------|--------|-------------|
| NCT03697109 (Phase 3, Cushing syndrome) | COMPLETED | Jul 16, 2025 |
| NCT04308590 (Phase 3, adrenal adenomas) | COMPLETED | Sep 4, 2025 |

**Assessment**: Unchanged. Strong dual Phase 3 data package. ODIN T1/T2 candidate. No new CT.gov activity.

---

## 6. Upcoming Deployment Calendar

| Date | Ticker | Event | Type | Status |
|------|--------|-------|------|--------|
| **March 25 (TODAY)** | BIIB | T-7 exit window | PDUFA Apr 3 | ⚠️ ACTION WINDOW |
| **March 25 (TODAY)** | IONS | T-7 exit window | PDUFA Apr 3 | ⚠️ ACTION WINDOW |
| **March 28** | RCKT | Kresladi FDA Decision | PDUFA | **T-3 DAYS — IMMINENT** |
| March 31 | PRAX | PRAX-628 Phase 2 readout | Phase readout | T-6 days |
| April 1 | TGTX | Pipeline event (TBD) | TBD | Basis still unverified |
| April 3 | BIIB | Tofersen PDUFA decision | PDUFA | T-9 days |
| April 3 | IONS | Eplontersen PDUFA decision | PDUFA | T-9 days |
| TBD 2026 | PRAX | Vormatrigine Phase 2/3 | Phase readout | Watch list (new) |
| July 11 | CORT | Relacorilant PDUFA | PDUFA | T+108 days |

---

## 7. Recommended Next Steps

1. **BIIB / IONS T-7 action TODAY (REPEAT)**: Deployment calendar flags March 25 as the exit window for BIIB and IONS. If not acted on in v23, this is the final same-day notice.
2. **RCKT final pre-decision check (March 26–28)**: One more run before March 28. No new CT.gov signals currently — watch for any FDA advisory communication or Rocket press release.
3. **Enable 9realms MCP connector**: 24 consecutive disabled runs. Live ODIN/GUNGNIR scoring remains unavailable for every run since monitor inception.
4. **Fix FinBrain MCP pydantic schema**: Server alive, data blocked. Requires server-side change to accept `req` as plain dict. 24 consecutive data-collection failures means zero insider flow, sentiment, or analyst data has ever been collected.
5. **Deploy ODIN v6.1 to MCP server**: Update `mcp_9realms_vnext.py` with v6.1 Ridge C=15 coefficients (32 features). v5 still running in production.
6. **Deploy GUNGNIR v30.1 to MCP server**: Update with Ridge C=30 + Trees 70/30 blend (26 features).
7. **Archive LGB optimizer artifacts (24th recommendation)**: Move `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.
8. **Clarify TGTX April 1 basis**: No CT.gov evidence found for active TGTX pipeline event. Likely commercial or milestone event — confirm manually.
9. **Add vormatrigine to GUNGNIR watch list**: NCT07287163, n=700, ENROLLING_BY_INVITATION. Large Praxis study — when Ph2/3 readout approaches, score with GUNGNIR v30.1.

---

## 8. Model Integrity Reminder

- **ODIN v6.1** is for **PDUFA events ONLY** (approval vs. CRL). Do not apply to phase readouts.
- **GUNGNIR v30.1** is for **phase readouts ONLY** (positive vs. negative). Do not apply to PDUFA decisions.
- All features are T-1 compliant (knowable before the event date).
- v5 (ODIN) and v29 (GUNGNIR) remain active production baselines until MCP server is updated with v6.1 and v30.1.

---

*This report is generated automatically by the odin-gungnir-monitor scheduled task. All data is for informational and research purposes only — not investment advice.*
