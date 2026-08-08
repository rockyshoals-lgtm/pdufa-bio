# ODIN v6 / GUNGNIR v30 Monitor Report — v23
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v22.md

---

## ⚡ Key Developments Since v22

1. **RCKT Kresladi decision T-3 days** — March 28 PDUFA is imminent. No changes to ClinicalTrials.gov trial status since v22. Pivotal package (NCT03812263, COMPLETED, n=9) and LTFU (NCT06282432, ACTIVE_NOT_RECRUITING) remain unchanged. No early FDA action signals detected.
2. **BIIB / IONS T-7 exit window open TODAY** — Per deployment calendar, today (March 25) is the T-7 exit window for both BIIB and IONS ahead of their April 3 PDUFA decisions. Action recommended.
3. **Vertex next-gen CF pipeline confirmed active** — ClinicalTrials.gov search confirms VX-828 Phase 1 trial (NCT06154447) is actively RECRUITING as of February 2026, with estimated PCD April 23, 2026. Triple combination (VX-828 + tezacaftor + deutivacaftor / VX-118) in healthy and CF participants. This is Vertex's next-generation CFTR modulator program beyond vanzacaftor. No NDA imminent — GUNGNIR future watch list.
4. **LLY SUMMIT trial confirmed COMPLETED** — NCT04847557 (tirzepatide in HFpEF/obesity, Phase 3, RCT, placebo-controlled, Eli Lilly) shows status COMPLETED. Primary completion July 2024. Results published; positive readout already known. No active ODIN/GUNGNIR signal at this time — historical data point for model validation.
5. **All model champions unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
6. **LGB optimizer confirmed terminated (23rd run)** — No logs/ directory, no new champion. Round 241 / 8 promotions / last promotion 2026-03-01. Fully terminated.
7. **9realms MCP disabled (23rd consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector settings.
8. **FinBrain pydantic error persists (23rd consecutive run)** — All FinBrain data tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker`) continue to fail with pydantic `model_type` validation error on the `req` parameter. Server is alive (v0.1.6) but schema mismatch prevents any data retrieval.

---

## 1. Executive Summary

The system enters a critical 3-day window before the RCKT Kresladi (RP-L201) FDA decision on March 28. ClinicalTrials.gov reconfirms the pivotal picture is completely unchanged from v22 — both studies hold their status, and no FDA early action signals have been detected. Simultaneously, BIIB and IONS are entering their T-7 exit windows today per the deployment calendar. The next-generation Vertex pipeline (VX-828 triple combo) has been confirmed active on CT.gov with April 2026 PCD, providing a future GUNGNIR watchlist entry. LLY's SUMMIT tirzepatide HFpEF trial is fully completed and provides a retrospective model validation data point. Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable with no new optimizer activity. MCP infrastructure issues persist at 23 consecutive runs and remain the primary operational gap.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | -7.45% (worse) |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None detected. `odin_v6_2_deploy.json` does not exist.

**v6.1 features (32 total)**: All 25 v5 features retained, plus 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**Status**: STABLE. v6.1 is the deployment target. Outstanding action: update `mcp_9realms_vnext.py` to embed v6.1 Ridge coefficients.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO Brier | vs v29 Brier |
|---------|-------------|----------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **0.1008** | **+56.9% better** |

**New configs this run**: None detected. `gungnir_v30_2_deploy.json` does not exist.

**v30.1 key features (26 total)**: `drug_last`, `sp_sr`, `j_last_neg`, `era_post24`, `des_surrogate`, `orr_x_onc`, `is_asco`, `competitive`, `mod_gene_therapy`, `has_ppm`, `des_orr`, `mod_cell_therapy`, `des_primary_ep`, `year`, `ta_n3_log`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `des_pfs`, `mod_antibody`, `month`, `ta_infectious`, `ta_rare`, `p3_x_cns`, `des_topline` (26 features — tight, no CTGOV dependency).

**Status**: STABLE. v30.1 is the deployment target. Outstanding action: update `mcp_9realms_vnext.py` to embed v30.1 Ridge+Trees blend.

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| Rounds since last promotion | ≥480 |
| Days since last promotion | ~24 days |
| `logs/` directory | DOES NOT EXIST |

**Assessment**: Fully terminated. LGB track best Brier (0.2057 WF) is comprehensively beaten by GUNGNIR v30.1 (0.1008 HO). No restart warranted.

**⚠️ Action pending**: Archive `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, and `champion_ladder.json` to `archive/lgb_optimizer/` cold storage. This action is recommended for the 23rd consecutive run.

---

## 4. Live MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms `odin_score` | ❌ DISABLED | 23rd consecutive run. Connector setting blocks tool. |
| 9realms `gungnir_score` | ❌ DISABLED | Same as above. |
| 9realms `system_status` | ❌ DISABLED | Same as above. |
| FinBrain `insider_transactions_by_ticker` | ❌ SCHEMA ERROR | Pydantic `InsiderReq` model_type mismatch on `req` param. 23rd consecutive failure. |
| FinBrain `news_sentiment_by_ticker` | ❌ SCHEMA ERROR | Pydantic `SentimentsReq` model_type mismatch. 23rd consecutive failure. |
| FinBrain `analyst_ratings_by_ticker` | ❌ SCHEMA ERROR | Pydantic `AnalystRatingsReq` model_type mismatch. 23rd consecutive failure. |
| ClinicalTrials.gov `search_studies` | ✅ OK | Working normally. Used as primary external data source. |
| ClinicalTrials.gov `get_study` | ⚠️ PARTIAL | Single NCT ID lookup works; array input fails regex validation. |

**FinBrain root cause**: The `req` parameter needs to be passed as a native pydantic model instance, but the MCP protocol serializes parameters as JSON strings. The fix requires the MCP server to accept `req` as a plain dict and construct the model internally. This is a server-side change, not a client-side workaround.

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (**T-3 DAYS — DECISION IMMINENT**)

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT03812263 (Phase 1/2 pivotal) | COMPLETED | n=9 | Nov 15, 2023 |
| NCT06282432 (Long-term follow-up) | ACTIVE_NOT_RECRUITING | n=9 | Dec 18, 2025 |

**Assessment**: No changes since v22. Pivotal data package fully intact. LTFU study active and updated Dec 2025 — routine follow-up activity consistent with gene therapy NDA. No early FDA action detected. Decision on March 28.

**ODIN context**: Gene therapy for rare pediatric disease (LAD-I), single-arm Phase 1/2 (n=9), surrogate endpoint, no prior CRL, sponsor naive in rare gene therapy NDA filing. ODIN would likely classify this T3/T2 due to single-arm design and small n — rare disease priority pathway may push it toward T2.

---

### CORT — Relacorilant | PDUFA: July 11, 2026

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT03697109 (Phase 3, Cushing syndrome) | COMPLETED | n=152 | Jul 16, 2025 |
| NCT04308590 (Phase 3, adrenal adenomas) | COMPLETED | n=137 | Sep 4, 2025 |

**Assessment**: Unchanged from v22. Two Phase 3 RCTs, both COMPLETED with solid enrollment and recent data package updates. Placebo-controlled. Strong ODIN T1/T2 profile. No new CT.gov activity detected.

---

### PRAX — PRAX-628 | Entry: March 31, 2026

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT06908356 (Phase 2, focal/tonic-clonic seizures) | RECRUITING | n=50 | Apr 3, 2025 |

**Assessment**: Only Phase 2 activity on CT.gov. This is a GUNGNIR (phase readout) signal, not an ODIN play. Small study (n=50), still recruiting. Phase 2 readout expected March 31.

---

### TGTX | Entry: April 1, 2026

**Assessment**: No active TGTX pipeline trials found on CT.gov. Ublituximab (Briumvi) is FDA-approved (Dec 2022). April 1 entry basis remains unverified — likely a commercial or pipeline milestone, not an ODIN or GUNGNIR scoring event. Manual verification still recommended.

---

### BIIB / IONS | PDUFA: April 3, 2026 — **T-7 EXIT WINDOW TODAY**

**Assessment**: Per deployment calendar, March 25 is the T-7 window to exit positions ahead of April 3 PDUFA decisions for both BIIB and IONS. No CT.gov validation was run this pass (validated in prior runs). No early action signals noted.

---

### NEW: Vertex VX-828 (Next-Gen CF) | Pipeline Watch

| Study | Status | Enrollment | PCD |
|-------|--------|-----------|-----|
| NCT06154447 (Phase 1, VX-828 triple combo) | RECRUITING | N/A | Apr 23, 2026 (est.) |

**Assessment**: VX-828 in triple combination with tezacaftor/deutivacaftor or VX-118 — Vertex's next-generation CFTR modulator. Phase 1 in healthy subjects and CF patients. PCD estimated April 2026. This is early-stage; no PDUFA timeline yet. Adding to GUNGNIR future watch list for Phase 2 readout monitoring.

---

### LLY SUMMIT — Tirzepatide in HFpEF | Retrospective Validation Point

| Study | Status | Sponsor | Completion |
|-------|--------|---------|-----------|
| NCT04847557 (Phase 3 RCT) | COMPLETED | Eli Lilly | July 2024 |

**Assessment**: SUMMIT trial completed with positive results (HFpEF + obesity, tirzepatide vs placebo). Double-blind, placebo-controlled RCT. Eli Lilly experienced sponsor. This is a strong retrospective validation data point for GUNGNIR v30.1 — features like `des_rct`, `mod_antibody` (GLP-1 is peptide/small molecule), `era_post24`, and `sp_sr` would all score favorably. Confirms v30.1 feature set captures real positive signals. Not an active scoring event.

---

## 6. Upcoming Deployment Calendar

| Date | Ticker | Event | Type | Status |
|------|--------|-------|------|--------|
| **March 25 (TODAY)** | BIIB | T-7 exit window | PDUFA Apr 3 | ⚠️ ACTION TODAY |
| **March 25 (TODAY)** | IONS | T-7 exit window | PDUFA Apr 3 | ⚠️ ACTION TODAY |
| **March 28** | RCKT | Kresladi FDA Decision | PDUFA | **T-3 DAYS** |
| March 31 | PRAX | PRAX-628 Phase 2 readout | Phase readout | Approaching |
| April 1 | TGTX | Pipeline event (TBD) | TBD | Basis unverified |
| April 3 | BIIB | PDUFA decision | PDUFA | T-9 days |
| April 3 | IONS | PDUFA decision | PDUFA | T-9 days |
| July 11 | CORT | Relacorilant PDUFA | PDUFA | T+108 days |

---

## 7. Recommended Next Steps

1. **BIIB / IONS T-7 action TODAY**: Deployment calendar flags March 25 as the exit window for BIIB and IONS positions ahead of April 3 PDUFA decisions. Review positions against ODIN tier assignment and runup data.
2. **RCKT final monitoring (March 26–28)**: Run one more check before decision day. Watch for any FDA advisory or early approval/CRL signal. RCKT decision is the primary near-term catalyst.
3. **Enable 9realms MCP connector**: 23 consecutive disabled runs. Live ODIN/GUNGNIR scoring remains unavailable. This is the highest-priority infrastructure action.
4. **Fix FinBrain MCP pydantic schema**: Server-side change needed — `req` parameter must accept plain dict, not require pre-instantiated pydantic model. 23 consecutive failures means no insider flow, sentiment, or analyst data has been collected since monitor inception.
5. **Deploy v6.1 to MCP server**: Update `mcp_9realms_vnext.py` to embed v6.1 coefficients (Ridge C=15, 32 features). v5 is still running in production.
6. **Deploy v30.1 to MCP server**: Update GUNGNIR in `mcp_9realms_vnext.py` to Ridge C=30 + Trees 70/30 blend with 26 features.
7. **Archive LGB optimizer artifacts**: 23rd recommendation to move `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, `champion_ladder.json` → `archive/lgb_optimizer/`.
8. **Clarify TGTX April 1 basis**: What asset/event drives this deployment entry?
9. **Add VX-828 to GUNGNIR watch list**: Phase 1 PCD is April 2026. Phase 2 readout will be a GUNGNIR scoring event when it occurs.

---

## 8. Model Integrity Reminder

- **ODIN v6.1** is for **PDUFA events ONLY** (approval vs. CRL). Do not apply to phase readouts.
- **GUNGNIR v30.1** is for **phase readouts ONLY** (positive vs. negative). Do not apply to PDUFA decisions.
- All features are T-1 compliant (knowable before the event date).
- v5 (ODIN) and v29 (GUNGNIR) remain active production baselines until MCP server is updated with v6.1 and v30.1.

---

*This report is generated automatically by the odin-gungnir-monitor scheduled task. All data is for informational and research purposes only — not investment advice.*
