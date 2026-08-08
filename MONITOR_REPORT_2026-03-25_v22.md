# ODIN v6 / GUNGNIR v30 Monitor Report — v22
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v21.md

---

## ⚡ Key Developments Since v21

1. **RCKT Kresladi decision T-3 days** — March 28 PDUFA remains imminent. ClinicalTrials.gov reconfirms: NCT03812263 (RP-L201, n=9) status COMPLETED (last updated Nov 2023), LTFU study NCT06282432 ACTIVE_NOT_RECRUITING (last updated Dec 18, 2025). No early FDA action detected. Pivotal package intact.
2. **CORT Phase 3 data revalidated** — ClinicalTrials.gov confirms both Phase 3 studies COMPLETED: NCT03697109 (Cushing Syndrome, n=152, last updated Jul 2025) and NCT04308590 (adrenal adenomas, n=137, last updated Sep 2025). July 11, 2026 PDUFA remains well-supported.
3. **PRAX-628 CT.gov note** — Search returns only Phase 2 activity (NCT06908356, RECRUITING, n=50, last updated Apr 2025). No NDA-level filing data on CT.gov. March 31 deployment entry appears to be based on Phase 2 readout — classified GUNGNIR territory, not ODIN.
4. **TGTX April 1 entry** — CT.gov search returned no active trials for TGTX/ublituximab pipeline. Ublituximab (Briumvi) is already FDA-approved. April 1 entry may relate to a next-generation pipeline asset or line extension — needs clarification from deployment plan source.
5. **All model champions unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No v6.2 or v30.2 configs detected.
6. **LGB optimizer confirmed stalled (22nd run)** — Champion ladder unchanged at round 241 / 8 promotions / last promotion 2026-03-01. Fully terminated.
7. **9realms MCP disabled (22nd consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector settings.
8. **FinBrain pydantic error persists (22nd consecutive run)** — Health endpoint returns OK (v0.1.6 / SDK 0.1.8), but all data tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`) fail with pydantic model_type validation error on `req` parameter. Schema mismatch between MCP server and SDK.

---

## 1. Executive Summary

This is the final monitor run before the RCKT Kresladi (RP-L201, Leukocyte Adhesion Deficiency Type I) FDA decision on March 28. ClinicalTrials.gov reconfirms the pivotal picture is unchanged: Phase 1/2 COMPLETED (n=9), long-term follow-up ACTIVE_NOT_RECRUITING. The near-term deployment calendar is active — PRAX (March 31 entry, Phase 2 readout) and TGTX (April 1, pipeline status unclear) are up next. Corcept's relacorilant (CORT, July 11 PDUFA) continues to show the strongest Phase 3 completion profile on CT.gov. Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable with no new optimizer activity. MCP infrastructure issues are unchanged and are not blockers to manual scoring.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | -7.45% (worse) |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None. No `odin_v6_2_deploy.json` found.

**v6.1 features (32 total)**: All 25 v5 features retained, plus 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**Status**: STABLE. v6.1 is the deployment target. MCP server update to embed v6.1 coefficients is the outstanding deployment action.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO Brier | vs v29 Brier |
|---------|-------------|----------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **0.1008** | **+56.9% better** |

**New configs this run**: None. No `gungnir_v30_2_deploy.json` found.

**v30.1 key features (26 total)**: `drug_last`, `sp_sr`, `j_last_neg`, `era_post24`, `des_surrogate`, `orr_x_onc`, `is_asco`, `competitive`, `mod_gene_therapy`, `has_ppm`, `des_orr`, `mod_cell_therapy`, `des_primary_ep`, `year`, `ta_n3_log`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `des_pfs`, `mod_antibody`, `month`, `ta_infectious`, `ta_rare`, `p3_x_cns`, `des_topline`, `mod_gene_therapy` (26 features — tight, no CTGOV dependency).

**Status**: STABLE. v30.1 is the deployment target.

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

**⚠️ Recommended action**: Archive `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, and `champion_ladder.json` to cold storage. Close out the LGB track formally.

---

## 4. Live MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms `odin_score` | ❌ DISABLED | 22nd consecutive run. Connector setting blocks tool. |
| 9realms `gungnir_score` | ❌ DISABLED | Same as above. |
| 9realms `system_status` | ❌ DISABLED | Same as above. |
| FinBrain `health` | ✅ OK | Server v0.1.6, SDK v0.1.8 — alive. |
| FinBrain `insider_transactions_by_ticker` | ❌ SCHEMA ERROR | Pydantic `InsiderReq` model_type mismatch on `req` param. |
| FinBrain `news_sentiment_by_ticker` | ❌ SCHEMA ERROR | Pydantic `SentimentsReq` model_type mismatch. |
| FinBrain `analyst_ratings_by_ticker` | ❌ SCHEMA ERROR | Pydantic `AnalystRatingsReq` model_type mismatch. |
| ClinicalTrials.gov search | ✅ OK | Working normally. |
| ClinicalTrials.gov get_study | ⚠️ PARTIAL | 8-digit NCT ID regex validation fails array input; single string input also errored. Search API used as workaround. |

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (T-3 DAYS)

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT03812263 (Phase 1/2 pivotal) | COMPLETED | n=9 | Nov 15, 2023 |
| NCT06282432 (Long-term follow-up) | ACTIVE_NOT_RECRUITING | n=9 | Dec 18, 2025 |

**Assessment**: Data package fully intact. No last-minute trial status changes. LTFU study update (Dec 2025) confirms ongoing patient follow-up, typical for gene therapy NDA. No early FDA action signals.

**ODIN signal**: Gene therapy, rare disease (LAD-I), single-arm Phase 1/2 with n=9, no prior CRL, surrogate endpoint (CD18 expression + infection rate). This is a high-stakes rare pediatric gene therapy — ODIN T2/T3 range likely due to small n and single-arm design, but rare disease pathway may support priority.

---

### CORT — Relacorilant | PDUFA: July 11, 2026

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT03697109 (Phase 3, Cushing syndrome) | COMPLETED | n=152 | Jul 16, 2025 |
| NCT04308590 (Phase 3, adrenal adenomas) | COMPLETED | n=137 | Sep 4, 2025 |

**Assessment**: Two Phase 3 RCTs both COMPLETED with solid enrollment. Placebo-controlled. Data package strong. July 11 PDUFA is a high-quality T1/T2 ODIN candidate.

---

### PRAX — PRAX-628 | Entry: March 31, 2026

| Study | Status | Enrollment | Last Updated |
|-------|--------|-----------|--------------|
| NCT06908356 (Phase 2, focal/tonic-clonic seizures) | RECRUITING | n=50 | Apr 3, 2025 |

**Assessment**: Only Phase 2 data found on CT.gov. No NDA on file. March 31 deployment entry is a GUNGNIR (phase readout) signal, not an ODIN play. Phase 2 readout for PRAX-628 in epilepsy. Small study (n=50), recruiting, no topline signal yet.

---

### TGTX | Entry: April 1, 2026

**Assessment**: CT.gov search returned no active TGTX pipeline trials for ublituximab or related agents. Ublituximab (Briumvi) is already FDA-approved (December 2022) for relapsing MS. April 1 entry may relate to: (a) a next-generation pipeline asset (U2 or combination therapy), (b) a label extension, or (c) possible earnings/commercial milestone. **Recommend manual verification of April 1 deployment basis from source calendar.**

---

## 6. Upcoming Deployment Calendar (Per v21 Report)

| Date | Ticker | Event | Type | Action |
|------|--------|-------|------|--------|
| **March 25 (TODAY)** | BIIB | T-7 exit window open | PDUFA Apr 3 | Exit |
| **March 25 (TODAY)** | IONS | T-7 exit window open | PDUFA Apr 3 | Exit |
| March 28 | RCKT | Kresladi FDA Decision | PDUFA | Decision Day |
| March 31 | PRAX | PRAX-628 Phase 2 readout | Phase readout | Entry |
| April 1 | TGTX | Pipeline event (TBD) | TBD | Entry |
| April 3 | BIIB | PDUFA decision | PDUFA | Decision Day |
| April 3 | IONS | PDUFA decision | PDUFA | Decision Day |
| July 11 | CORT | Relacorilant PDUFA | PDUFA | Decision Day |

---

## 7. Recommended Next Steps

1. **RCKT final check (March 26–27)**: Run one more monitor pass before decision day. Watch for any FDA advisory committee surprise, early approval, or CRL signal on biotech news feeds.
2. **Enable 9realms MCP connector**: 22 consecutive disabled runs is a significant data gap. Live ODIN/GUNGNIR scoring would allow automated T1/T2/T3/T4 tier assignment for each catalyst above.
3. **Fix FinBrain pydantic schema**: The fix is in the MCP server — the `req` parameter needs to accept a dict directly, not require a pre-instantiated pydantic model. This is a one-line fix in `mcp_finbrain.py` (or equivalent). Insider flow data for VRTX, LLY, ABBV would significantly enrich feature monitoring.
4. **Clarify TGTX April 1 basis**: What asset/event drives the April 1 entry signal? If it's a phase readout for a pipeline asset, run GUNGNIR on it.
5. **Archive LGB optimizer artifacts**: Formally close out the LGB track. Move `lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`, and `champion_ladder.json` to an `archive/lgb_optimizer/` folder.
6. **Begin v6.1 MCP deployment**: Update `mcp_9realms_vnext.py` to embed v6.1 coefficients (Ridge C=15, 32 features) and replace v5 weights. This is the key outstanding deployment action.
7. **Begin v30.1 MCP deployment**: Same for GUNGNIR v30.1 (Ridge C=30 + Trees 70/30 blend, 26 features).

---

## 8. Model Integrity Reminder

- ODIN v6.1 is for **PDUFA events ONLY** (approval vs. CRL). Do not apply to phase readouts.
- GUNGNIR v30.1 is for **phase readouts ONLY** (positive vs. negative). Do not apply to PDUFA decisions.
- All features are T-1 compliant (knowable before the event date).
- v5 (ODIN) and v29 (GUNGNIR) remain active production baselines until MCP server is updated.

---

*This report is generated automatically by the odin-gungnir-monitor scheduled task. All data is for informational and research purposes only — not investment advice.*
