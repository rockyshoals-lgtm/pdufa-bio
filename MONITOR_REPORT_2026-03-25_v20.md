# ODIN v6 / GUNGNIR v30 Monitor Report — v20
**Generated**: 2026-03-25T21:30:00Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v19.md

---

## ⚡ Key Developments Since v19

1. **RCKT Kresladi decision T-3 days** — March 28 PDUFA is now 3 days away. ClinicalTrials.gov confirms pivotal trial NCT03812263 (RP-L201, n=9) completed with LTFU study (NCT06282432) remaining ACTIVE_NOT_RECRUITING as of Dec 18, 2025. No early FDA action detected.
2. **All champion models unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain in place. No new deploy configs found (no v6.2, no v30.2).
3. **LGB optimizer confirmed fully plateaued** — No `models/` or `logs/` directories exist in workspace. All optimizer artifacts remain from early March. Formally stalled at round 721 / 8 promotions / last promotion March 1.
4. **FinBrain pydantic error persists** — Health endpoint is healthy (MCP v0.1.6, SDK v0.1.8) but all data tools fail with `InsiderReq`/`SentimentsReq` model type validation error. 20th consecutive broken run.
5. **9realms MCP still disabled** — ODIN/GUNGNIR live scoring unavailable. 20th consecutive run.

---

## 1. Executive Summary

This run sits at the final window before the RCKT Kresladi (Leukocyte Adhesion Deficiency Type I gene therapy) FDA decision on March 28. No early action (approval or CRL) was detected via any available channel. The ClinicalTrials.gov search confirms the clinical evidence base is solid: the pivotal Phase 1/2 trial (NCT03812263) is COMPLETED with n=9 patients and the Long-Term Follow-Up study is ACTIVE, which is consistent with BLA resubmission requirements. No new model improvements emerged — both ODIN v6.1 and GUNGNIR v30.1 remain champions. MCP infrastructure remains partially broken (9realms disabled, FinBrain API schema failure), though ClinicalTrials.gov search queries remain functional for targeted lookups.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | **-7.45% worse** |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None. No `odin_v6_2_deploy.json` detected.

**7 new features vs v5**: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

**Status**: STABLE. v6.1 is the deployment target.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v29 Brier |
|---------|-------------|----------|---------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.8219 | 0.1394 | **+40.4% better** |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **N/A** | **0.1008** | **+56.9% better** |

**New configs this run**: None. No `gungnir_v30_2_deploy.json` detected.

**Notable v30.1 features**: `drug_last`, `sp_sr`, `j_last_neg`, `era_post24`, `des_surrogate`, `orr_x_onc`, `is_asco`, `competitive`, `mod_gene_therapy` — a tight 26-feature ensemble that dramatically outperforms v29's 82-feature build.

**Status**: STABLE. v30.1 is the deployment target.

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last promotion | Round 241 (~2026-03-01) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| `models/` directory | **DOES NOT EXIST** |
| `logs/` directory | **DOES NOT EXIST** |
| Rounds since last promotion | **≥480** |
| Days since last promotion | **~24 days** |

**Assessment**: The optimizer has fully stalled. No new activity this run. The absence of `models/` and `logs/` directories (not just empty — non-existent) confirms the optimizer process has terminated. The LGB challenger (`lightgbm_challenger_v1.pkl`, `CURRENT_BEST.pkl`) achieved WF Brier 0.2057, which is meaningfully worse than v30.1's HO Brier 0.1008, and the LGB track did not reach champion status.

**⚠️ Action Needed**: Formally retire the LGB optimizer track. The v30.1 result makes further LGB iteration low-priority. Recommend:
1. Archive `lightgbm_challenger_v1.pkl` and `CURRENT_BEST.pkl` as non-champion artifacts
2. Begin MCP server integration work for v6.1 and v30.1
3. If further GUNGNIR optimization is desired, restart with Brier as primary objective rather than WF AUC

---

## 4. MCP Infrastructure Status

| Tool | Status | Details |
|------|--------|---------|
| 9realms `odin_score` | ❌ DISABLED | 20th consecutive run. Connector disabled in settings. |
| 9realms `gungnir_score` | ❌ DISABLED | 20th consecutive run. Connector disabled in settings. |
| 9realms `system_status` | ❌ DISABLED | 20th consecutive run. |
| FinBrain `health` | ✅ OK | v0.1.6 MCP / v0.1.8 SDK — server is up |
| FinBrain `insider_transactions` | ❌ BROKEN | `InsiderReq` pydantic model type error. 20th run. |
| FinBrain `news_sentiment` | ❌ BROKEN | `SentimentsReq` pydantic model type error. 20th run. |
| FinBrain `analyst_ratings` | ❌ BROKEN (inferred) | Same schema issue expected. |
| ClinicalTrials.gov `search_studies` | ✅ FUNCTIONAL | Targeted searches working. |
| ClinicalTrials.gov `get_study` | ❌ BROKEN | NCT ID regex validation bug (fails on valid 8-digit IDs). 3rd run. |

**FinBrain root cause**: The MCP server expects native Python model instances (`InsiderReq`, `SentimentsReq`) but the MCP protocol layer is passing JSON strings. This is a server-side deserialization bug — requires a fix to the FinBrain MCP server's tool handler to accept dict input and construct model instances internally.

---

## 5. PDUFA Events Watch

### ⏳ IMMINENT: RCKT — Kresladi (RP-L201) — **March 28, 2026 (3 days)**

| Field | Data |
|-------|------|
| **ODIN Tier** | TIER_2 (Cautious Long) |
| **Indication** | Leukocyte Adhesion Deficiency Type I (LAD-I) — ultra-rare, fatal pediatric immunodeficiency |
| **Type** | BLA resubmission (2nd resubmission, Class 2 response) |
| **Designations** | RMAT, Rare Pediatric Disease, Fast Track (US); PRIME, ATMP (EU) |
| **Pivotal trial** | NCT03812263 — Phase 1/2, COMPLETED, n=9 |
| **LTFU** | NCT06282432 — ACTIVE_NOT_RECRUITING, last updated Dec 18 2025 ✓ |
| **Key efficacy** | 100% overall survival at 12 months; all primary/secondary endpoints met |
| **Safety** | No treatment-related SAEs reported |
| **FDA status** | Under review — no early action detected |
| **Key risk** | Third CMC CRL remains possible; prior 2 CRLs were manufacturing-related |

**ClinicalTrials.gov corroboration (new this run)**: The LTFU study (NCT06282432) was updated December 18, 2025 — 3+ months after BLA resubmission acceptance in October 2025. This is consistent with ongoing patient follow-up in support of the BLA, and no unexpected status changes (e.g., suspension) were observed. Supports approval scenario.

---

### 📅 NEXT CATALYST: LNTH (Lantheus) — June 29, 2026

- **Drug**: LNTH-2501 (PSMA-targeted radiopharmaceutical)
- **Status**: Manufacturing data review — 3-month extension from prior date
- **Note**: CheckRare had listed March 29 erroneously; Lantheus press release (March 17, 2026) confirmed June 29 extension
- **Risk profile**: Manufacturing/CMC review only — no efficacy/safety concerns flagged

---

### 📋 2026 PDUFA Watch List (Beyond RCKT/LNTH)

No new catalysts detected this run. Monitoring continues. The v20 report focuses on the RCKT decision window.

---

## 6. Insider Trading & Sentiment (FinBrain)

**Status**: ALL TOOLS BROKEN — pydantic deserialization error on all data endpoints.

Requested tickers: RCKT, VRTX, LLY, ABBV
Result: Unable to retrieve insider transactions, news sentiment, or analyst ratings for any ticker.

**FinBrain health check**: Server UP (v0.1.6). The issue is isolated to tool parameter handling, not network connectivity.

**Workaround for next run**: The FinBrain MCP server needs a patch. Until fixed, insider/sentiment data is unavailable through this pipeline. Manual monitoring of SEC Form 4 filings for RCKT recommended ahead of March 28 decision.

---

## 7. Optimization Recommendations

### Immediate (before RCKT decision March 28)
- [ ] Manually review RCKT Form 4 filings on SEC.gov (FinBrain unavailable)
- [ ] Prepare ODIN v6.1 post-decision update — record actual outcome in training dataset

### Short-term (this week)
- [ ] Fix FinBrain MCP: patch `insider_transactions_by_ticker` and `news_sentiment_by_ticker` to accept dict and construct pydantic model internally
- [ ] Fix ClinicalTrials.gov `get_study` NCT ID regex validation bug
- [ ] Re-enable 9realms MCP connector in settings

### Medium-term (this month)
- [ ] Formally retire LGB optimizer track; archive non-champion PKL files
- [ ] Begin MCP server integration work for ODIN v6.1 (replaces v5 in production)
- [ ] Begin MCP server integration work for GUNGNIR v30.1 (replaces v29 in production)
- [ ] GUNGNIR v30.1 feature audit: validate 26 features for T-1 compliance before deployment

### Model Improvement Opportunities
- **ODIN v6.2 ideas**: Incorporate 2025 decision outcomes (post-cutoff enrichment); explore FDA reviewer cycle time as a feature
- **GUNGNIR v30.2 ideas**: Add conference-specific features (ASCO 2026 season approaching); update drug journey data through Q1 2026

---

## 8. Summary Scorecard

| Metric | Value | Status |
|--------|-------|--------|
| ODIN champion | v6.1 | ✅ Stable |
| ODIN Brier vs v5 | +8.92% improvement | ✅ |
| GUNGNIR champion | v30.1 | ✅ Stable |
| GUNGNIR Brier vs v29 | +56.9% improvement | ✅ |
| New model versions this run | 0 | — |
| Optimizer active | No (stalled at round 721) | ⚠️ |
| 9realms MCP | Disabled | ❌ |
| FinBrain MCP | Broken (pydantic) | ❌ |
| ClinicalTrials.gov search | Functional | ✅ |
| Imminent catalysts | RCKT March 28 | ⏳ |
| Early FDA action detected | None | — |

---

*Report auto-generated by ODIN/GUNGNIR monitoring pipeline. All model metrics are from offline validation. ODIN v6.1 and GUNGNIR v30.1 are not yet in production — v5 and v29 remain live in the 9realms MCP server.*

*This report is for informational and research purposes only. Not investment advice.*
