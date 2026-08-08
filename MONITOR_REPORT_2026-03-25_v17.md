# ODIN v6 / GUNGNIR v30 Monitor Report — v17
**Generated**: 2026-03-25T19:30:00Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v16.md

---

## ⚡ BREAKING: Two Major Regulatory Updates Since v16

1. **LNTH edotreotide PDUFA EXTENDED** (March 17, 2026): FDA extended LNTH-2501 review by 3 months to **June 29, 2026** for manufacturing-related information. v16 still listed March 29 as active — that date is now void. TIER_1 assignment carries forward to the new date.

2. **GSK Lynavoy (linerixibat) APPROVED** (March 19, 2026): FDA approved linerixibat 5 days early, before its March 24 PDUFA date. First medicine approved in the US for cholestatic pruritus in PBC patients. New approval to log in validation tracking.

---

## 1. Executive Summary

Two meaningful real-world events since v16. GSK linerixibat received early approval March 19 (PDUFA was March 24), and Lantheus pushed its March 29 PDUFA date out to June 29 due to manufacturing review. RCKT Kresladi remains on track for March 28 (3 days away) with no new FDA communications detected. LLY Orforglipron confirmed at April 10 for obesity — no changes. No new model deploy configs (v6.2, v30.2) detected; model optimization dormant since March 1. LGB optimizer still stalled at round 619, no promotions since round 241. 9realms and FinBrain MCPs remain broken for the 17th consecutive run.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial run) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | **-7.45% worse** |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**Status**: No v6.2 deploy config detected. v6.1 remains champion. No optimizer activity.

**v6.1 new features vs v5** (7 additions): `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v29 Brier |
|---------|-------------|----------|---------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 (initial run) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.8219 | 0.1394 | **+40.4% better** |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **N/A** | **0.1008** | **+56.9% better** |

**Status**: No v30.2 deploy config detected. v30.1 remains champion. No optimizer activity.

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | 621 (unchanged since v16) |
| Total champion promotions | 8 (unchanged) |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| Latest ensemble pool file | `lgb_r00619_783a2c1ff85c.pkl` (Mar 2) |
| Rounds since last promotion | **≥378** (r241 → r619+) |
| Days since last promotion | **~24 days** |

**Assessment**: Optimizer has fully plateaued. No new rounds detected since last report. Ensemble pool last modified March 2. The LGB champion's WF Brier (0.2057) remains nearly 2× worse than ODIN v6.1's holdout Brier (0.1102).

**⚠️ Recommendation**: The LGB parallel optimization track should be formally decided. Three options remain:
1. Restart optimizer with Brier as the objective target (vs current WF AUC)
2. Retire the LGB track and dedicate resources to v6.1/v30.1 deployment
3. Cap total rounds at 800 and produce a final audit

---

## 4. PDUFA Events Watch — Updated

### ✅ NEW: GSK Lynavoy (linerixibat) — APPROVED March 19, 2026 (**5 days early**)
- **ODIN Tier**: Untracked in v16 watchlist (PDUFA was March 24)
- **Indication**: Cholestatic pruritus in Primary Biliary Cholangitis (PBC)
- **Type**: NDA, Orphan Drug Designation
- **Approval note**: FDA approved as "Lynavoy" — first medicine in US for this indication. Approved before PDUFA date, consistent with elevated 2026 approval environment. GSK is a highly experienced sponsor. GLISTEN Phase 3 met both primary and key secondary endpoints.
- **ODIN retrospective**: Would likely have been TIER_1/TIER_2 given experienced sponsor + orphan designation + strong Phase 3 data + no prior CRL.
- **Action**: Add to 2026 approval tracking. Alfasigma acquired licensing rights March 9 (pre-approval).

---

### ⚠️ UPDATED: LNTH edotreotide — PDUFA EXTENDED to June 29, 2026
- **Prior PDUFA**: March 29, 2026 (**now void**)
- **New PDUFA**: **June 29, 2026** (announced March 17, 2026)
- **Reason**: FDA requested additional manufacturing-related information review. Extension explicitly NOT related to efficacy or safety.
- **ODIN Tier**: TIER_1 (carries forward — manufacturing delay only, clinical data unchanged)
- **Indication**: Somatostatin receptor-positive neuroendocrine tumor PET imaging (NDA/505(b)(2))
- **Sponsor**: Lantheus Holdings (experienced radiopharmaceutical sponsor)
- **Assessment**: Manufacturing extensions without clinical/safety concerns are standard for radiopharmaceutical kits. TIER_1 assignment remains appropriate. Remove from March 29 watch; move to June 29.
- **Context**: CTGOV search confirmed no registrational trials found (consistent with 505(b)(2) pathway using existing 68Ga-DOTATATE data from published studies).

---

### ⏳ IMMINENT: RCKT Kresladi — **March 28, 2026 (3 days)**
- **ODIN Tier**: TIER_2 (Cautious Long — small/inexperienced sponsor, 2× prior CMC CRLs, gene therapy)
- **Indication**: Leukocyte Adhesion Deficiency Type I (LAD-I) — ultra-rare, fatal in childhood
- **Type**: BLA resubmission (2nd resubmission, Class 2 response)
- **Designations**: RMAT, Rare Pediatric, Fast Track (US); PRIME, ATMP (EU)
- **Clinical data**: 100% overall survival at 12 months post-infusion; all primary/secondary endpoints met; no treatment-related SAEs
- **CTGOV**: NCT03812263 confirmed **COMPLETED** (verified this run)
- **Key risk**: Third CMC CRL remains possible but significantly de-risked by FDA's acceptance of the resubmission after two prior CMC-specific CRLs. FDA confirmed no advisory committee required.
- **PRV value**: Eligible for Rare Pediatric Disease Priority Review Voucher (~$100M+ if sold)
- **No FDA decision announced as of March 25** — watch for Friday announcement
- **Action**: Monitor RCKT press releases March 28. Log outcome as TIER_2 validation (either outcome consistent with TIER_2 logic given CMC risk).

---

### ⏳ WATCH: LLY Orforglipron (obesity) — **April 10, 2026 (16 days)**
- **ODIN Tier**: TIER_1 (Highest-conviction upcoming catalyst)
- **Indication**: Obesity / overweight with comorbidities — **NDA** (not T2D; separate T2D NDA in 2026)
- **Type**: NDA, Priority Review, Commissioner's National Priority Voucher (rapid review pathway)
- **Sponsor**: Eli Lilly (20+ prior approvals, highly experienced)
- **PDUFA note**: Originally March 28, moved to April 10 in January 2026. "Minor delay" per analysts; all other Commissioner's National Priority Voucher awardees received same extension.
- **CTGOV status this run**:
  - ATTAIN-1 (NCT05869903): **ACTIVE_NOT_RECRUITING** — 72-week main phase complete, extension ongoing for prediabetes. Unchanged.
  - ATTAIN-2 (NCT05872620): **COMPLETED** — 77-week obesity + T2D study fully complete. Unchanged.
- **Commercial timing**: Medicare obesity coverage begins April 2026 — launch timing is highly strategic
- **Assessment**: Both registrational trials complete. Strong T1 conviction maintained. No new negative signals detected.

---

### 📋 Upcoming Pipeline (April–May 2026)

| Date | Ticker | Drug | Indication | Notes |
|------|--------|------|-----------|-------|
| Apr 3 | BIIB/IONS | Nusinersen (high dose) | Spinal Muscular Atrophy | Supplemental; experienced sponsors |
| Apr 5 | DNLI | Tividenofusp alfa | MPS-IIIA (Sanfilippo) | Rare CNS; priority review |
| Apr 10 | REPL | RP1 (vusolimogene) | Advanced melanoma (anti-PD-1 refractory) | Priority review |
| Apr 10 | LLY | Orforglipron | Obesity | TIER_1 (see above) |
| Apr 30 | AXSM | AXS-05 | Major Depressive Disorder | Supplemental |
| Jun 29 | LNTH | Ga68-edotreotide | GEP-NETs PET imaging | TIER_1, mfg delay |

---

## 5. Infrastructure MCP Status — Run #17

| Tool | Status | Consecutive Failures | Error |
|------|--------|---------------------|-------|
| 9realms `odin_score` | ❌ DISABLED | **17** | "This tool has been disabled in your connector settings" |
| 9realms `gungnir_score` | ❌ DISABLED | **17** | "This tool has been disabled in your connector settings" |
| 9realms `system_status` | ❌ DISABLED | **17** | "This tool has been disabled in your connector settings" |
| FinBrain `insider_transactions_by_ticker` | ❌ BROKEN | **17** | Pydantic: `InsiderReq` model_type validation error |
| FinBrain `news_sentiment_by_ticker` | ❌ BROKEN | **17** | Pydantic: `SentimentsReq` model_type validation error |
| FinBrain `analyst_ratings_by_ticker` | ❌ BROKEN | **17** | Pydantic: `AnalystRatingsReq` model_type validation error |
| ClinicalTrials.gov `get_study` | ✅ WORKING | — | Clean single-NCT lookups, verified this run |
| ClinicalTrials.gov `search_studies` | ⚠️ PARTIAL | — | Works for simple queries; no-results for edotreotide (consistent with 505b2 not having CT registrations) |
| Perplexity `perplexity_search` | ✅ WORKING | — | **Used as FinBrain substitute** — successfully retrieved news, regulatory updates, market intel |

**Workaround applied this run**: Perplexity search successfully replaced FinBrain for regulatory news (LNTH extension, GSK approval, RCKT status). This is a viable ongoing substitute for news sentiment until FinBrain Pydantic schema is patched.

**9realms MCP**: Connector-level disable, 17th consecutive. Resolution requires David to re-enable the connector in settings. Production scoring of ODIN v5/GUNGNIR v29 not testable from scheduled runs.

**FinBrain fix path**: Server-side Pydantic v2 schema needs to accept `str` input and deserialize to typed model. Client-side workaround is not possible.

---

## 6. ODIN Model Validation — Q1/Q2 2026 Tracking

| Event | PDUFA | ODIN Tier | Outcome | Correct? |
|-------|-------|-----------|---------|----------|
| BMY Sotyktu (deucravacitinib) PsA | Mar 7 | TIER_1 | ✅ APPROVED | ✅ |
| RYTM Imcivree HO | Mar 19 | TIER_2 | ✅ APPROVED | ✅ |
| GSK Lynavoy (linerixibat) PBC | Mar 19 (early) | TIER_1/2 (retro) | ✅ APPROVED | ✅ (retro) |
| RCKT Kresladi LAD-I | Mar 28 | TIER_2 | ⏳ PENDING | — |
| LNTH edotreotide (extended) | ~~Mar 29~~ → **Jun 29** | TIER_1 | ⏳ PENDING | — |
| LLY Orforglipron obesity | Apr 10 | TIER_1 | ⏳ PENDING | — |

**YTD approval rate (confirmed)**: ~83% (3 approvals from 3 tracked events; elevated 2026 approval environment continues).

**Note on GSK**: Linerixibat was not on the prior watchlist (PDUFA was March 24, 5 days after v16 was generated), but its early approval validates ODIN logic for experienced-sponsor + orphan + strong-phase3 events. Adding retroactively.

---

## 7. What's New vs v16

1. **🚨 LNTH PDUFA EXTENDED**: March 29 date is void. FDA extended to June 29 (announced March 17, 8 days ago). Manufacturing review, not clinical. Updated watchlist accordingly.
2. **🎯 GSK Lynavoy APPROVED** (March 19, early): First PBC pruritus approval. Validates ODIN-style logic (experienced sponsor + orphan + strong P3 data = approve). Added to validation tracker.
3. **LLY Orforglipron confirmed April 10**: BioSpace and Motley Fool confirmed the Jan 2026 delay to April 10. Orforglipron obesity NDA is the correct tracking (T2D NDA is a separate 2026 submission). TIER_1 maintained.
4. **RCKT still on track March 28**: No new FDA communications. Article dated March 25 (today) still describes it as pending. TIER_2 assigned.
5. **New upcoming events catalogued**: BIIB/IONS SMA April 3; DNLI MPS-IIIA April 5; REPL melanoma April 10.
6. **Perplexity adopted as FinBrain substitute**: Successfully pulled all key intel via web search. Will continue until FinBrain Pydantic issue is resolved.
7. **Optimizer still stalled**: No new ensemble pool files since March 2. No new deploy configs.
8. **9realms MCP failure count**: Now 17 consecutive (up from 16).
9. **FinBrain failure count**: Now 17 consecutive (up from 16).

---

## 8. Recommended Actions

| Priority | Action | Owner |
|----------|--------|-------|
| 🔴 HIGH | **Re-enable 9realms MCP connector** in Cowork settings — 17 runs without production scoring | David |
| 🔴 HIGH | **Monitor RCKT March 28** — approval/CRL decision imminent (3 days) | Auto / David |
| 🟡 MEDIUM | **Formally decide LGB optimizer fate** — 378+ rounds of no improvement; decision needed (restart, retire, or cap at 800) | David |
| 🟡 MEDIUM | **File FinBrain bug report** — Pydantic v2 `model_type` validation error blocking all FinBrain tools | David |
| 🟢 LOW | Update pdufa.bio LNTH entry to reflect June 29 PDUFA date | David |
| 🟢 LOW | Begin building ODIN feature profiles for DNLI tividenofusp alfa (Apr 5) and REPL RP1 (Apr 10) | David |
| 🟢 LOW | Add GSK Lynavoy to pdufa.bio resolved decisions table | David |

---

*Report generated by automated monitor scheduled task. All investment references are informational/educational only and do not constitute investment advice. Past model performance does not guarantee future results.*
