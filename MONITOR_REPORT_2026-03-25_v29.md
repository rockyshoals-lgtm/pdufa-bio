# ODIN v6 / GUNGNIR v30 Monitor Report — v29
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v28.md

---

## ⚡ Key Developments Since v28

1. **XENE X-TOLE2 COMPLETED on CT.gov** — NEW FINDING this run. NCT05614063 (X-TOLE2, Phase 3, Azetukalner for focal-onset seizures) now shows status **COMPLETED** with primary completion **2026-01-12** and study completion **2026-02-03**. The ODIN 2026 database listed this as a "March 2026" readout — trial has already completed enrollment and data collection. Results have not yet been posted to CT.gov (`has_results: false`). A data readout announcement from Xenon (XENE) is imminent or potentially already occurred.
2. **KPTI SENTRY trial — CT.gov search inconclusive** — A specific "SENTRY" selinexor Phase 3 trial in multiple myeloma from Karyopharm was not found on CT.gov by any search path. The closest active Karyopharm/selinexor/MM Phase 3 is NCT05028348 (SPd vs EloPd, European Myeloma Network, primary completion **2026-03**, ACTIVE_NOT_RECRUITING). The SENTRY readout listed in the ODIN database for March 2026 may be this trial or may not yet have a CT.gov registration.
3. **RCKT Kresladi decision imminent (3 days)** — March 28 PDUFA falls on Saturday; FDA action expected Friday March 27 or Monday March 30. NCT03812263 (pivotal Phase 1/2) remains **COMPLETED** (n=9, completed 2023-09-12). NCT06282432 (LTFU) remains **ACTIVE_NOT_RECRUITING** (15-year follow-up ongoing through 2036). No amendments or status changes detected.
4. **BIIB tofersen April 3 PDUFA confirmed sNDA pattern** — CT.gov re-confirms two post-approval-era studies: NCT07294144 (Phase 2, non-SOD1 ALS, Washington University, RECRUITING since Dec 2025) and NCT07223723 (Phase 4 Chinese PMS, Biogen, RECRUITING since Dec 2025, brand name Qalsody). The presence of a Phase 4 PMS study using the approved trade name confirms this is a supplemental NDA, not an initial approval. NCT04856982 (ATLAS Phase 3, presymptomatic SOD1-ALS) remains ACTIVE_NOT_RECRUITING (primary completion 2027-08).
5. **PRAX-628 readout March 31 — status discrepancy noted** — NCT06908356 shows status **RECRUITING** but primary completion date is **2025-07** (past). This discrepancy likely means: (a) the CT.gov entry has not been updated post-completion, or (b) the enrollment period extended. The March 31 readout timing would be consistent with results from a trial whose data collection completed mid-2025.
6. **All model champions unchanged (29th run)** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
7. **9realms MCP DISABLED (29th consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector settings.
8. **FinBrain pydantic error persists (29th consecutive run)** — Same `InsiderReq` / `SentimentsReq` / `AnalystRatingsReq` model_type mismatch. No FinBrain data retrievable.

---

## 1. Executive Summary

**XENE (Xenon Pharmaceuticals)** is the biggest new signal this run. X-TOLE2 (NCT05614063, Phase 3, azetukalner in focal-onset seizures) completed January 12, 2026. The ODIN 2026 database shows a March 2026 readout window, meaning a data announcement may arrive any day or may have already occurred quietly. No results on CT.gov yet. Xenon investors should watch for a press release. Azetukalner (XEN1101) is a Kv7 potassium channel opener; the original X-TOLE Phase 3 showed significant seizure frequency reduction, and X-TOLE2 was the confirmatory study.

**KPTI (Karyopharm Therapeutics)** SENTRY readout is listed for March 2026 but the exact CT.gov trial is not directly identifiable. The likeliest match is NCT05028348 (SPd vs EloPd, RRMM, primary completion 2026-03), though the sponsor is European Myeloma Network, not Karyopharm. The "SENTRY" naming likely refers to a Karyopharm-sponsored investigational cohort or combination trial not yet registered under that acronym.

**RCKT Kresladi** is 3 days from PDUFA (March 28 Saturday → March 27 or March 30 action). All CT.gov data stable — no last-minute amendments. The pivotal trial (n=9) met its endpoints; all prior Karyopharm checks indicate high approval probability profile (rare disease gene therapy, BTD, orphan, priority review, surrogate endpoint, completed pivotal).

**PRAX-628** readout March 31 — CT.gov shows RECRUITING status with a past primary completion date (2025-07), which is a common CT.gov update lag. Open-label Phase 2 design (single-arm, 50 subjects, 8-week treatment period). Results could be positive (mechanism-validated GABA-A modulator) but open-label design limits comparison-controlled interpretation.

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

**Architecture insight**: v6.0's GPU ensemble (LGB+XGB+CatBoost+TabNet+Ridge, 65 features) hurt performance vs v5 despite adding 40 features and GPU compute — classic overfitting on a ~1,800-event training set. v6.1's forward selection from 65 → 32 features + slightly stronger Ridge regularization (C=15 vs C=1.5 in v5) plus isotonic calibration recovered the gain and then some. This is a strong signal that for PDUFA prediction with ~2K events, parsimonious linear models dominate deep ensembles.

**Status**: STABLE. v6.1 is the deployment target.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO Brier | vs v29 Brier |
|---------|-------------|----------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **0.1008** | **+56.9% better** |

**New configs this run**: None. `gungnir_v30_2_deploy.json` does not exist.

**v30.1 features (26 total, abbreviated names from deploy config)**: `has_ppm`, `des_orr`, `mod_cell_therapy`, `des_primary_ep`, `orr_x_onc`, `year`, `ta_n3_log`, `drug_last`, `ta_oncology`, `des_rct`, `drug_n_log`, `has_conf`, `des_pfs`, `sp_sr`, `mod_antibody`, `month`, `era_post24`, `ta_infectious`, `competitive`, `ta_rare`, `p3_x_cns`, `des_topline`, `j_last_neg`, `des_surrogate`, `is_asco`, `mod_gene_therapy`.

**Status**: STABLE. v30.1 is the deployment target.

---

### ⚠️ Leaky Artifact Alert: gungnir_champion_ladder.json (Ongoing)

`models/lgb_champions/champion_ladder.json` remains with WF AUC 0.9979 / Brier 0.0393 and post-readout features. **Do not use.** Confirmed leakage class identical to retired GUNGNIR v25. Legitimate champion is GUNGNIR v30.1 (Brier 0.1008, 26 clean T-1 features).

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last champion file | Mar 2, 04:42 (round 241) |
| Latest ensemble_pool file | lgb_r00619 (Mar 2, 02:46) |
| `logs/` directory | **NOT PRESENT** |
| Optimizer status | **FULLY TERMINATED** |

No new model checkpoint files since the last run. The LGB autonomous optimizer has been fully stopped since ~March 2, 2026. No further rounds expected without manual restart.

---

## 4. 9realms MCP Live Scoring

**Status: DISABLED (29th consecutive run)**

All three tools (`odin_score`, `gungnir_score`, `system_status`) returned: *"This tool has been disabled in your connector settings."* No live scores obtainable this run.

**Recommended action**: Re-enable the 9realms MCP connector in Cowork connector settings to restore live scoring capability.

---

## 5. FinBrain Market Intelligence

**Status: BROKEN — pydantic error (29th consecutive run)**

All three FinBrain tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker`) continue to fail with:
> `Input should be a valid dictionary or instance of [Req type]`

This is a server-side serialization bug in the FinBrain MCP connector. No data retrievable for RCKT, BIIB, VRTX, LLY, ABBV, or any other ticker.

**Recommended action**: Update or reinstall the FinBrain MCP connector. The `req` parameter needs to accept a JSON object rather than requiring a typed Pydantic instance.

---

## 6. ClinicalTrials.gov Catalyst Intelligence

### 6a. RCKT — Kresladi (RP-L201), LAD-I Gene Therapy
**PDUFA: March 28, 2026 (Saturday → FDA action likely March 27 or March 30)**

| Study | Status | Last Event |
|-------|--------|------------|
| NCT03812263 (Phase 1/2 pivotal) | **COMPLETED** | Primary completion 2023-09-12, n=9 |
| NCT06282432 (LTFU observational) | **ACTIVE_NOT_RECRUITING** | 15-year follow-up, completion 2036-10-04 |

No changes from prior runs. The pivotal study has been fully complete since September 2023. Both sites (UCLA, Madrid, London GOSH) remain on record. No amendments, no new study registrations.

**ODIN profile** (estimated from known features): BTD ✓, Orphan ✓, Priority Review ✓, Surrogate endpoint ✓, Gene therapy ✓, Small sponsor (1 prior approval). High T1/T2 approval probability profile — rare pediatric gene therapy with complete unmet need and 9/9 patient data.

---

### 6b. BIIB — Tofersen (Qalsody), ALS-SOD1 sNDA
**PDUFA: April 3, 2026**

| Study | Status | Notes |
|-------|--------|-------|
| NCT04856982 (ATLAS presymptomatic Phase 3) | **ACTIVE_NOT_RECRUITING** | n=158, primary completion 2027-08 |
| NCT07294144 (Phase 2, non-SOD1 expansion) | **RECRUITING** | Washington University, n=30, start Dec 2025 |
| NCT07223723 (Phase 4 PMS China) | **RECRUITING** | Biogen sponsor, n=12, uses "Qalsody" trade name |

The presence of an active Phase 4 post-marketing surveillance study explicitly using the approved brand name "Qalsody" (NCT07223723) confirms this April 3 PDUFA is almost certainly an sNDA/label extension, not an initial approval decision. Reduced binary risk but also less upside asymmetry compared to a first approval.

---

### 6c. PRAX — PRAX-628, Focal/Generalized Seizures
**Readout: ~March 31, 2026**

| Study | Status | Completion Date |
|-------|--------|-----------------|
| NCT06908356 (Phase 2 open-label) | **RECRUITING** | Primary completion listed **2025-07** (past) |

Status discrepancy: RECRUITING status with a July 2025 primary completion date is a CT.gov update lag. The trial has likely completed its 8-week treatment period. Open-label, n=50, single-arm (30mg PRAX-628), seizure frequency reduction as primary endpoint. No results posted yet.

Design note: Open-label single-arm design means no placebo comparison — any readout will report responder rates and median % seizure frequency reduction without a control arm. Positive data would need to compare favorably to historical controls for the compound to advance to a controlled Phase 3.

---

### 6d. ⭐ NEW: XENE — Azetukalner (X-TOLE2), Focal-Onset Seizures
**Readout expected: March 2026 (trial already completed)**

| Study | Status | Completion Date |
|-------|--------|-----------------|
| NCT05614063 (X-TOLE2, Phase 3 RCT) | **COMPLETED** | Primary completion **2026-01-12**, full completion **2026-02-03** |

**NEW FINDING this run.** X-TOLE2 is a rigorous Phase 3 RCT: randomized, double-blind, placebo-controlled, 3-arm (XEN1101 25mg : 15mg : Placebo), n=380, 12-week treatment period at ~125 global sites. Primary endpoint: median percent change in monthly focal seizure frequency. No results posted to CT.gov.

The original X-TOLE study (NCT05614063 predecessor) demonstrated statistically significant seizure reduction. If X-TOLE2 replicates, this sets up NDA filing for azetukalner in focal-onset epilepsy — a large commercial market.

**GUNGNIR profile** (estimated from v30.1 features): Phase 3 ✓, RCT design ✓, CNS TA, surrogate endpoint (seizure frequency), no prior negative, medium-cap sponsor. Likely T2–T3 (moderate confidence positive) given the open Kv7 mechanism and clean predecessor data.

**Watch for**: XENE press release or conference presentation (likely AESNET, AES Annual Meeting, or direct PR). The 6–8 week lag between completion (Feb 3) and readout announcement puts the data window squarely in March–April 2026.

---

### 6e. KPTI — Selinexor SENTRY, Multiple Myeloma
**Readout expected: March 2026 (CT.gov trial not confirmed)**

No direct CT.gov registration found under "SENTRY" for Karyopharm/selinexor in MM. Closest match: NCT05028348 (SPd vs EloPd, Phase 3, RRMM, European Myeloma Network, primary completion 2026-03, ACTIVE_NOT_RECRUITING). This could be the trial referenced in the ODIN 2026 database under the SENTRY name, or SENTRY could refer to a Karyopharm-sponsored trial not yet registered.

**Recommended action**: Monitor KPTI press releases and investor relations for SENTRY data timing. If this is an EU-sponsored trial (NCT05028348), NDA filing implications for Karyopharm would depend on the data package and whether they have FDA filing rights.

---

## 7. Upcoming Catalyst Pipeline (from ODIN 2026 Database)

| Ticker | Drug | Indication | Catalyst | Timing | ⭐ |
|--------|------|-----------|----------|--------|----|
| RCKT | Kresladi (RP-L201) | LAD-I | **PDUFA Decision** | **Mar 28** | ⭐⭐⭐⭐ |
| PRAX | PRAX-628 | Focal/PGTCS | Phase 2 readout | **Mar 31** | ⭐⭐⭐ |
| KPTI | Selinexor | Multiple myeloma | SENTRY Ph3 readout | **March 2026** | ⭐⭐⭐⭐ |
| XENE | Azetukalner | Focal seizures | X-TOLE2 Ph3 readout | **March 2026** | ⭐⭐⭐⭐ |
| BIIB | Tofersen | ALS-SOD1 (sNDA) | **PDUFA Decision** | **Apr 3** | ⭐⭐⭐⭐ |
| MLCL | Annamycin | AML | MIRACLE Ph2B/3 | Q1 2026 | ⭐⭐⭐ |
| TVTX | Filspari | IgAN | PDUFA (past: Jan 13) | Already past | ⭐⭐⭐⭐ |
| FBIO | CUTX-101 | TBD | PDUFA (past: Jan 14) | Already past | ⭐⭐ |
| AZN | Zanidatamab | HER2+ gastric | HERIZON-GEA-01 | Early Jan (past) | ⭐⭐⭐⭐ |
| NVLN | Zidesamtinib | ALK+ NSCLC | Ph2 readout + NDA filing | Q2–Q3 | ⭐⭐⭐⭐ |

---

## 8. Infrastructure Status Summary

| System | Status | Consecutive Failures |
|--------|--------|---------------------|
| 9realms MCP (odin_score, gungnir_score) | ❌ DISABLED | 29 |
| FinBrain MCP (insider, sentiment, analyst) | ❌ PYDANTIC ERROR | 29 |
| ClinicalTrials.gov MCP (primary connector) | ❌ SCHEMA ERROR | 1 (new this run) |
| ClinicalTrials.gov MCP (alt connector) | ✅ WORKING | — |
| ODIN v6.1 deploy config | ✅ STABLE | — |
| GUNGNIR v30.1 deploy config | ✅ STABLE | — |
| LGB Autonomous Optimizer | ⛔ TERMINATED | Since Mar 2 |

**Note**: The primary CT.gov MCP (`clinicaltrialsgov` connector) returned schema errors on both `get_study` (NCT ID format validation) and `search_studies` (output schema mismatch). The alternate connector (`edca76d9` UUID) worked correctly for all queries this run.

---

## 9. Recommended Next Optimization Steps

### Model Development
1. **ODIN v6.2 candidate**: Explore adding `manufacturing_risk_score` (continuous) and `safety_signal_severity` (ordinal) as replacements for binary flags. The current v6.1 dropped these from v6.0 features — a graded version may recover signal without overfitting.
2. **GUNGNIR v30.2 candidate**: Add CTGOV real data features back to the 26-feature v30.1 base. v29 used 82 features including 10 CTGOV real features; v30.1 dropped all CTGOV features. Selective reintroduction of `ctgov_real_enrollment`, `ctgov_has_withdrawals`, and `ctgov_placebo` (top CTGOV coefficients from v29) to v30.1's 26 features could push Brier below 0.10.
3. **LGB Optimizer restart**: Consider re-running 200–400 additional rounds starting from champion_r00241 weights with updated feature set from v6.1 selection. The optimizer has been idle since March 2.

### Infrastructure
1. **Re-enable 9realms MCP** in connector settings — currently blocking all live ODIN/GUNGNIR scoring.
2. **Fix FinBrain MCP** pydantic serialization error — the `req` parameter needs schema update to accept dict input.
3. **Monitor primary CT.gov MCP** for schema fix — currently falling back to alternate connector.

### Immediate Watchlist (next 7 days)
- **March 27–30**: RCKT Kresladi PDUFA outcome — highest near-term binary event
- **March 31**: PRAX-628 Phase 2 readout
- **March–April**: XENE X-TOLE2 data announcement (trial completed Feb 3, no results yet)
- **March–April**: KPTI SENTRY data announcement
- **April 3**: BIIB tofersen sNDA outcome

---

*Report generated by automated odin-gungnir-monitor scheduled task. All investment content is for informational and educational purposes only and does not constitute investment advice.*
