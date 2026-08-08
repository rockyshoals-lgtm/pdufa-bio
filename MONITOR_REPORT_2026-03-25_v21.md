# ODIN v6 / GUNGNIR v30 Monitor Report — v21
**Generated**: 2026-03-25T22:00:00Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v20.md

---

## ⚡ Key Developments Since v20

1. **RCKT Kresladi decision T-3 days** — March 28 PDUFA remains on track. ClinicalTrials.gov reconfirms NCT03812263 (RP-L201, n=9) COMPLETED with LTFU study (NCT06282432) ACTIVE_NOT_RECRUITING (last updated Dec 11, 2025). No early FDA action detected.
2. **BIIB / IONS exits open TODAY** — Per deployment plan, both BIIB (PDUFA Apr 3) and IONS (PDUFA Apr 3) have exit windows active as of March 25. Deployment plan targets T-7 exit.
3. **CORT (Relacorilant) pivotal package confirmed strong** — ClinicalTrials.gov shows two completed Phase 3 studies: NCT03697109 (Cushing Syndrome, n=152, completed Apr 2024) and NCT04308590 (adrenal adenomas, n=137, completed Sep 2024). PDUFA July 11, 2026. Solid RCT with placebo arms, strong enrollment.
4. **All champion models unchanged** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain in place. No v6.2 or v30.2 configs detected.
5. **LGB optimizer confirmed stalled** — Champion ladder unchanged at round 241 / 8 promotions / last promotion March 1. `models/` and `logs/` root directories remain absent. Optimizer fully terminated.
6. **FinBrain pydantic error persists** — 21st consecutive broken run. Health endpoint confirms server is live (v0.1.6) but all data tools fail with `InsiderReq`/`SentimentsReq`/`AnalystRatingsReq` model_type validation error. Issue is in MCP server's pydantic model deserialization.
7. **9realms MCP still disabled** — ODIN/GUNGNIR live scoring blocked by connector settings. 21st consecutive run.

---

## 1. Executive Summary

This is the penultimate monitor run before the RCKT Kresladi (Leukocyte Adhesion Deficiency Type I, lentiviral gene therapy) FDA decision on March 28. ClinicalTrials.gov reconfirms the pivotal clinical picture: Phase 1/2 study COMPLETED (n=9, Sep 2023), long-term follow-up ACTIVE. No early FDA signal detected. Separately, deployment calendar flags two important trading exits today (BIIB, IONS) and upcoming entries next week (PRAX March 31, TGTX April 1). Corcept's relacorilant (CORT, July 11 PDUFA) was validated with strong Phase 3 completion data. MCP infrastructure issues continue — 9realms disabled, FinBrain schema-broken — but are not blockers to manual scoring or deployment planning.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | -7.45% (worse) |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None. No `odin_v6_2_deploy.json` detected.

**v6.1 new features vs v5 (7 added)**: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

**Note**: v6.0's 65-feature overfit ensemble was decisively beaten by v6.1's parsimonious Ridge C=15 configuration, consistent with regularization being the key lever on this relatively small dataset (2,203 events).

**Status**: STABLE. v6.1 is the deployment target. MCP server update needed.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v29 Brier |
|---------|-------------|----------|---------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.8219 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **N/A** | **0.1008** | **+56.9% better** |

**New configs this run**: None. No `gungnir_v30_2_deploy.json` detected.

**v30.1 key features**: `drug_last`, `sp_sr`, `j_last_neg`, `era_post24`, `des_surrogate`, `orr_x_onc`, `is_asco`, `competitive`, `mod_gene_therapy` — a tight 26-feature blend that dramatically outperforms v29's 82-feature CTGOV-enriched architecture.

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
| `models/` root directory | **DOES NOT EXIST** |
| `logs/` root directory | **DOES NOT EXIST** |
| Rounds since last promotion | **≥480** |
| Days since last promotion | **~24 days** |
| LGB challenger best Brier | 0.2057 vs. v30.1's 0.1008 |

**Assessment**: Fully stalled and terminated. The LGB track (WF Brier 0.2057) was comprehensively beaten by v30.1's Ridge+Trees approach (HO Brier 0.1008). The absence of `models/` and `logs/` root directories confirms the optimizer process exited cleanly.

**⚠️ Action Needed**:
- Formally retire LGB optimizer track
- Archive `lightgbm_challenger_v1.pkl` and `CURRENT_BEST.pkl` as non-champion artifacts
- Begin MCP server integration for v6.1 and v30.1
- If further GUNGNIR optimization desired, restart with Brier as primary objective

---

## 4. MCP Infrastructure Status

| Component | Status | Notes |
|-----------|--------|-------|
| 9realms MCP (ODIN score) | ❌ **DISABLED** | Blocked by connector settings — 21st consecutive run |
| 9realms MCP (GUNGNIR score) | ❌ **DISABLED** | Same connector block |
| 9realms MCP (system_status) | ❌ **DISABLED** | Same connector block |
| FinBrain health | ✅ OK | v0.1.6 / SDK 0.1.8 |
| FinBrain insider_transactions | ❌ **BROKEN** | Pydantic `InsiderReq` model_type error — 21st run |
| FinBrain news_sentiment | ❌ **BROKEN** | Pydantic `SentimentsReq` model_type error — 21st run |
| FinBrain analyst_ratings | ❌ **BROKEN** | Pydantic `AnalystRatingsReq` model_type error — 21st run |
| ClinicalTrials.gov search | ✅ **PARTIAL** | Simple queries work; complex filter queries fail schema validation |
| ClinicalTrials.gov get_study | ❌ **BROKEN** | "NCT ID must be 8 digits" — NCT IDs with 8-digit suffixes rejected |

**FinBrain diagnosis**: The MCP server receives the `req` parameter as a JSON string rather than a deserialized Pydantic model instance. This is a server-side deserialization bug — the MCP layer is not converting the JSON string to the expected model type before calling the handler. Fix requires updating `finbrain-mcp-server` to explicitly call `InsiderReq.model_validate_json(req)` or similar.

**ClinicalTrials.gov diagnosis**: The `get_study` tool rejects valid NCT IDs (e.g., NCT03812263) claiming they need 8 digits — NCT03812263 has 8 digits after the "NCT" prefix but the validator may be checking the full string length. The search tool schema validation failures appear when using `filter` + `fields` combinations with certain query structures.

---

## 5. Upcoming Catalyst Calendar & ClinicalTrials.gov Validation

### Immediate Horizon (Next 30 Days)

| PDUFA Date | Ticker | Trade Action | Tier | Cap | Notes |
|------------|--------|-------------|------|-----|-------|
| **2026-03-28** | **RCKT** | ⏰ **DECISION IN 3 DAYS** | — | Nano | Kresladi (RP-L201), LAD-I gene therapy, BLA |
| 2026-04-03 | BIIB | 🔴 **EXIT TODAY (T-7)** | TIER_1 | MEGA | Exit window closes March 25 |
| 2026-04-03 | IONS | 🔴 **EXIT TODAY (T-7)** | TIER_1 | LARGE | Exit window closes March 25 |
| 2026-04-19 | PRAX | 📅 Entry opens March 31 | TIER_2 | LARGE | Entry window opens in 6 days |
| 2026-04-21 | TGTX | 📅 Entry opens April 1 | TIER_2 | SMALL/MID | Entry opens in 7 days |
| 2026-04-30 | BHC | 📅 Entry opens April 10 | TIER_2 | SMALL/MID | — |

### ClinicalTrials.gov Validations This Run

**RCKT — NCT03812263 (RP-L201, LAD-I)**
- Status: COMPLETED ✅
- Enrollment: n=9 (rare disease, expected small n)
- Phase: 1/2 (pivotal for ultra-rare)
- Primary completion: September 12, 2023
- Sponsor: Rocket Pharmaceuticals Inc.
- LTFU (NCT06282432): ACTIVE_NOT_RECRUITING, last updated December 11, 2025
- Assessment: Clinical package intact. FDA has been reviewing for ~2+ years. Decision due March 28.

**CORT — Relacorilant (Cushing Syndrome, PDUFA July 11, 2026)**
- NCT03697109: Phase 3 COMPLETED, n=152, Apr 2024, RCT with placebo
- NCT04308590: Phase 3 COMPLETED, n=137, Sep 2024, RCT with placebo (adrenal adenomas)
- Combined pivotal n=289 with two indications — strong regulatory package
- Assessment: Dual Phase 3 completions with placebo control. CORT PDUFA July 11 well-supported by clinical data.

---

## 6. Upcoming Catalyst Detail (Deployment Plan — Full 2026)

| # | Entry | Exit | PDUFA | Ticker | Tier | Cap | Exp. Return |
|---|-------|------|-------|--------|------|-----|-------------|
| 2 | Feb 20 | **Mar 25** | Apr 3 | BIIB | T1 | MEGA | 1.94% |
| 3 | Mar 16 | **Mar 25** | Apr 3 | IONS | T1 | LARGE | 3.83% |
| 4 | Mar 31 | Apr 9 | Apr 19 | PRAX | T2 | LARGE | 2.10% |
| 5 | Apr 1 | Apr 14 | Apr 21 | TGTX | T2 | SMALL/MID | 2.58% |
| 6 | Apr 10 | Apr 23 | Apr 30 | BHC | T2 | SMALL/MID | 2.58% |
| 7 | Apr 21 | May 22 | Jun 2 | AZN | T1 | MEGA | 1.94% |
| 8 | Apr 24 | May 27 | Jun 5 | PFE | T1 | MEGA | 1.94% |
| 9 | Jun 2 | Jun 15 | Jun 20 | ACHV | T1 | SMALL/MID | 2.94% |
| 10 | Jun 9 | Jun 22 | Jun 27 | UNCY | T1 | SMALL/MID | 2.94% |
| 11 | Jun 17 | Jun 30 | Jul 7 | VERA | T1 | SMALL/MID | 2.94% |
| 12 | Jun 23 | Jul 2 | Jul 11 | CORT | T1 | LARGE | 3.83% |
| 13 | Jul 6 | Aug 6 | Aug 17 | BMY | T1 | MEGA | 1.94% |
| 14 | Jul 9 | Jul 22 | Jul 29 | NRXP | T1 | SMALL/MID | 2.94% |
| 15 | Jul 24 | Aug 4 | Aug 13 | LNTH | T1 | LARGE | 3.83% |
| 16 | Aug 4 | Aug 17 | Aug 22 | CAPR | T1 | SMALL/MID | 2.94% |
| 17 | Aug 10 | Sep 10 | Sep 21 | MRK | T1 | MEGA | 1.94% |
| 18 | Aug 19 | Sep 21 | Sep 30 | TAK | T1 | MEGA | 1.94% |
| 19 | Sep 10 | Sep 21 | Sep 30 | PTGX | T1 | LARGE | 3.83% |
| 20 | Sep 29 | Oct 8 | Oct 17 | VTRS | T1 | LARGE | 3.83% |

---

## 7. Recommended Next Steps

### Immediate (Today — March 25)
1. **Execute BIIB and IONS exits** per deployment plan (T-7 exit window expires today)
2. **Monitor RCKT** — FDA decision expected March 28. No early action detected; watch for FDA website update or PR wire

### Near-Term (1–2 Weeks)
3. **Open PRAX position** on March 31 — T-14 entry window opens; TIER_2 large-cap
4. **Open TGTX position** on April 1 — T-14 entry window opens; TIER_2 small/mid-cap
5. **Fix FinBrain MCP** — Update server to call `InsiderReq.model_validate(json.loads(req))` instead of passing raw string; blocks insider signal integration for 21 runs
6. **Re-enable 9realms MCP** in connector settings to restore live ODIN/GUNGNIR scoring

### Model Work (When Ready)
7. **Integrate ODIN v6.1 into MCP server** — Replace v5 production weights (mcp_9realms_vnext.py update)
8. **Integrate GUNGNIR v30.1 into MCP server** — Replace v29 production weights
9. **Formally archive LGB optimizer artifacts** — Move `models/lgb_champions/` to cold storage
10. **Consider CTGOV cache refresh** for v30.1 — v30.1 does not use CTGOV features (ctgov_cache_used=false), but updating the cache ensures future model iterations have current trial data

---

## 8. Data Integrity Notes

- ODIN v6.1: All 32 features are T-1 compliant (knowable before PDUFA event). No outcome-derived features.
- GUNGNIR v30.1: All 26 features are T-1 compliant. `drug_last` and `j_last_neg` use strict temporal ordering (prior readouts only). `era_post24` is a calendar feature.
- LGB challenger (WF Brier 0.2057) did NOT beat either v6.1 or v30.1; safely retired.
- No leakage risks identified in either champion model.

---

*This report is generated automatically for informational and research purposes. Nothing herein constitutes investment advice. All model outputs are probabilistic estimates based on historical data and should not be the sole basis for any trading decision.*
