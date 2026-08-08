# ODIN v6 / GUNGNIR v30 Monitor Report — v19
**Generated**: 2026-03-25T21:00:00Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v18.md

---

## ⚡ Key Developments Since v18

1. **RCKT Kresladi still PENDING** — No FDA decision detected as of this run (March 25, 2026). Decision due in **3 days on March 28**. Multiple sources dated March 25 confirm still under review.
2. **LNTH June 29 confirmed** — CheckRare listed LNTH-2501 at March 29, potentially causing confusion. Confirmed: Lantheus officially announced a 3-month extension on March 17, 2026 — PDUFA is June 29, 2026 (manufacturing data review, not efficacy/safety). No new concern.
3. **No new FDA novel drug approvals since v18** — FDA.gov 2026 tracker still shows 8 approvals through March 24. Avlayah remains the most recent.
4. **All champion models unchanged.** ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain in place. LGB optimizer still plateaued at round 241.

---

## 1. Executive Summary

A quiet run between decision windows. RCKT Kresladi is the singular focus — decision imminent for March 28, 3 days away, with no early signal (approval or CRL) detected. An important data reconciliation was performed this run: CheckRare's PDUFA calendar had listed LNTH-2501 at March 29, 2026, creating a potential false upcoming catalyst. This was cross-checked against Lantheus' own press release (March 17, 2026) which officially confirmed the 3-month extension to June 29 — consistent with v18 data. All MCP infrastructure failures continue from v18 (9realms disabled: 19 runs; FinBrain broken: 19 runs; CTGOV get_study broken: 2nd run). Perplexity remains the sole active intelligence source.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial run) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | **-7.45% worse** |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**Status**: No v6.2 deploy config detected. v6.1 remains champion. No optimizer activity since v18.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v29 Brier |
|---------|-------------|----------|---------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 (initial run) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.8219 | 0.1394 | **+40.4% better** |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **N/A** | **0.1008** | **+56.9% better** |

**Status**: No v30.2 deploy config detected. v30.1 remains champion. No optimizer activity since v18.

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged from v18) |
| Total champion promotions | **8** (unchanged) |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| Latest ensemble pool file | `lgb_r00619_783a2c1ff85c.pkl` (Mar 2 — unchanged) |
| Rounds since last promotion | **≥480** |
| Days since last promotion | **~24 days** |
| `models/lgb_champions/CURRENT_BEST.pkl` last modified | **March 1** (unchanged) |

**Assessment**: No new optimizer activity observed this run. The `CURRENT_BEST.pkl` timestamp and all champion files remain at March 1–2 dates — the optimizer has either completed its run or stalled. Zero promotions in 480+ rounds confirms full plateau.

**⚠️ Decision overdue.** Three options remain:
1. Restart with Brier as primary objective (vs current WF AUC) — likely to find improvements
2. Formally retire LGB track; focus on v6.1/v30.1 deployment
3. Cap at 800 rounds and produce a final audit report

---

## 4. PDUFA Events Watch — Updated for v19

### ⏳ IMMINENT: RCKT Kresladi — **March 28, 2026 (3 days)**
- **ODIN Tier**: TIER_2 (Cautious Long)
- **Indication**: Leukocyte Adhesion Deficiency Type I (LAD-I) — ultra-rare, fatal in childhood
- **Type**: BLA resubmission (2nd resubmission, Class 2 response)
- **Designations**: RMAT, Rare Pediatric, Fast Track (US); PRIME, ATMP (EU)
- **Clinical data**: 100% overall survival at 12 months post-infusion; all primary/secondary endpoints met; well tolerated with no treatment-related SAEs
- **Status this run**: **No FDA decision detected** as of March 25, 2026. Kavout.com article dated March 25, 2026 states "all eyes are now on March 28." Multiple sources confirm still under review.
- **Key risk**: Third CMC CRL possible but significantly de-risked by FDA's collaborative approach and BLA acceptance in Oct 2025.
- **PRV**: Eligible for Rare Pediatric Disease PRV (~$100M+ if approved)
- **Action**: Log outcome in v20. This is the primary focus of the next run.

---

### 🔄 DATA CORRECTION: LNTH June 29 Confirmed (Not March 29)

**CheckRare** listed `3.29.2026` for LNTH-2501 (Gallium-68 edotreotide). This is **outdated**.

Per Lantheus Holdings press release dated **March 17, 2026** (GlobeNewsWire): The FDA extended the NDA review for LNTH-2501 by 3 months to **June 29, 2026**, to allow additional time to review manufacturing-related information. The company explicitly confirmed: *"This standard review extension is not related to the efficacy or safety data of LNTH-2501."*

The v18 watchlist date of June 29 was **correct**. CheckRare data lags. LNTH TIER_1 conviction unchanged — manufacturing-only delay, no clinical concerns.

---

### ⏳ WATCH: BIIB/IONS High-Dose Nusinersen — **April 3, 2026 (9 days)**
- **Status**: Confirmed. Biogen (Nasdaq: BIIB) and Ionis (IONS) reaffirmed at MDA conference (March 8–11, 2026) that the FDA decision is expected by **April 3, 2026**.
- **Data**: DEVOTE Phase 2/3 published in *Nature Medicine* (Feb 4, 2026). Pivotal cohort (n=75 infants) met primary endpoint; 26.19-point improvement on CHOP-INTEND vs matched sham (p<0.0001). 68% reduction in death/permanent ventilation.
- **Context**: Already approved in Japan, EU, Switzerland. This is a supplemental BLA; prior CRL in 2023. Strong data suggests low CRL risk.
- **ODIN note**: Supplemental BLA with strong data and prior global approvals → likely TIER_1 or TIER_2 if formally scored.

---

### 🆕 NEW ADDITION: Orca-T (Orca Bio) — **April 6, 2026 (12 days)**
- **ODIN Tier**: Not formally scored — private company, no ticker
- **Indication**: AML, ALL, MDS
- **Type**: BLA, Priority Review, RMAT + Orphan Drug Designation
- **Status**: BLA accepted (per CheckRare). No FDA action yet.
- **Clinical**: Phase 3 Precision-T — 78% vs 38% GVHD-free survival at 1 year (HR 0.26, p<0.00001)

---

### ⏳ WATCH: LLY Orforglipron (obesity) — **April 10, 2026 (16 days)**
- **ODIN Tier**: TIER_1 (Highest-conviction upcoming catalyst)
- **Type**: NDA, Commissioner's National Priority Voucher
- **Background**: BioSpace confirmed (Jan 15, 2026) FDA extended from initial March 28 to **April 10, 2026** as the revised target action date. Previously confirmed in v18.
- **Data**: ATTAIN-1 (NEJM Sep 2025): ~12% weight loss at max dose. ATTAIN-MAINTAIN (Dec 2025): maintained weight loss after injectable transition. Strong commercial differentiation from oral semaglutide (no food/water restriction, once daily).
- **Conviction**: TIER_1 maintained. Novo's oral semaglutide (Wegovy pill) approved, but market large enough for multiple oral GLP-1s.
- **⚠️ pdufa.bio ERROR still active**: March 2026 page incorrectly lists "LLY | Orforglipron | T2D | Mar 25." Confirmed PDUFA is **April 10 for obesity**. Needs correction.

---

### 📋 Complete Upcoming Pipeline — v19

| Date | Ticker | Drug | Indication | ODIN Tier | Notes |
|------|--------|------|-----------|-----------|-------|
| Mar 28 | RCKT | Kresladi | LAD-I (gene therapy) | TIER_2 | **IMMINENT — 3 days** |
| Apr 3 | BIIB/IONS | Nusinersen (high dose) | Spinal Muscular Atrophy | TIER_1/2 (est.) | Supplemental; strong data |
| Apr 6 | Orca Bio | Orca-T | AML/ALL/MDS | N/A (private) | Strong P3; cell therapy CMC risk |
| Apr 10 | LLY | Orforglipron | Obesity | TIER_1 | Top conviction |
| Apr 10 | REPL | RP1 (vusolimogene) | Advanced melanoma | TBD | Priority review |
| Apr 30 | AXSM | AXS-05 | Major Depressive Disorder | TBD | Supplemental |
| Jun 29 | LNTH | Ga68-edotreotide (LNTH-2501) | GEP-NETs PET imaging | TIER_1 | Mfg delay — confirmed June 29 |

---

## 5. ODIN Model Validation — 2026 Tracker (Updated)

| Event | PDUFA | ODIN Tier | Outcome | Correct? |
|-------|-------|-----------|---------|----------|
| BMY Sotyktu (deucravacitinib) PsA | Mar 6 | TIER_1 | ✅ APPROVED | ✅ |
| RYTM Imcivree HO | Mar 19 | TIER_2 | ✅ APPROVED | ✅ |
| GSK Lynavoy (linerixibat) PBC | Mar 19 (early) | TIER_1/2 (retro) | ✅ APPROVED | ✅ (retro) |
| DNLI Avlayah (tividenofusp alfa) | Apr 5 → Mar 24 (early) | TIER_1 (retro) | ✅ APPROVED | ✅ (retro) |
| RCKT Kresladi LAD-I | Mar 28 | TIER_2 | ⏳ PENDING | — |
| LNTH edotreotide (extended) | ~~Mar 29~~ → Jun 29 | TIER_1 | ⏳ PENDING | — |
| LLY Orforglipron obesity | Apr 10 | TIER_1 | ⏳ PENDING | — |

**YTD approval rate (confirmed tracked events)**: 4 approvals from 4 tracked events = **100%**

**Notable Q1 2026 CRLs** (external tracking, not in ODIN watchlist):
- Atara tabelecleucel (EBV+ PTLD) → CRL Jan 10
- Pharming leniolisib (APDS) → CRL Jan 31
- REGENXBIO clemidsogene/RGX-121 (MPS II) → CRL Feb 8
- Disc Medicine bitopertin (EPP) → CRL Feb 13
- Chiesi idebenone (LHON) → CRL Feb 28

**FDA 2026 YTD Novel Approvals (per FDA.gov, March 25, 2026)**: 8 total — Zycubo, Adquey, Bysanti, Loargys, Yuviwel, Lynavoy, Icotyde, Avlayah.

---

## 6. Infrastructure MCP Status — Run #19

| Tool | Status | Consecutive Failures | Error |
|------|--------|---------------------|-------|
| 9realms `odin_score` | ❌ DISABLED | **19** | "This tool has been disabled in your connector settings" |
| 9realms `gungnir_score` | ❌ DISABLED | **19** | Same |
| 9realms `system_status` | ❌ DISABLED | **19** | Same |
| FinBrain `insider_transactions_by_ticker` | ❌ BROKEN | **19** | Pydantic v2: `InsiderReq` model_type validation error |
| FinBrain `news_sentiment_by_ticker` | ❌ BROKEN | **19** | Pydantic v2: `SentimentsReq` model_type validation error |
| FinBrain `analyst_ratings_by_ticker` | ❌ BROKEN | **19** | Pydantic v2: `AnalystRatingsReq` model_type validation error |
| ClinicalTrials.gov `get_study` | ❌ BROKEN | **2** | NCT ID regex validation error ("NCT ID must be 8 digits") |
| ClinicalTrials.gov `search_studies` | ❌ BROKEN | **2** | Returns 0 results for known valid drug names (marnetegragene) |
| Perplexity `perplexity_search` | ✅ WORKING | — | **Primary intelligence source** — all key data retrieved |

**Note**: ClinicalTrials.gov `search_studies` now appears fully broken — returned 0 results for "marnetegragene autotemcel LAD-I Rocket Pharmaceuticals," a query that should unambiguously return NCT03812263. Previously returned partial results. This is now a 2-tool failure for CTGOV.

---

## 7. What's New vs v18

1. **⏳ RCKT still pending** — No FDA action as of March 25. Kavout.com March 25 analysis article confirms still awaiting decision. Outcome logged in v20 after March 28.
2. **🔄 LNTH data correction** — CheckRare showed March 29 but June 29 is confirmed via Lantheus March 17 press release. No new risk; manufacturing extension only.
3. **✅ BIIB nusinersen April 3 confirmed** — Biogen confirmed at MDA conference (March 5, 2026) that FDA decision is expected by April 3. DEVOTE data published in *Nature Medicine*. Strong data profile.
4. **📊 FDA.gov 2026 tracker verified** — Still at 8 novel approvals through March 24. No new approvals in the window between Avlayah (Mar 24) and this run (Mar 25).
5. **🔧 CTGOV search_studies now fully broken** — search_studies returned 0 results (previously partial), adding to CTGOV tool failures.
6. **🔢 19th consecutive failure** — 9realms and FinBrain counters increment.

---

## 8. Recommended Actions

| Priority | Action | Owner |
|----------|--------|-------|
| 🔴 HIGH | **Log RCKT March 28 outcome in v20** — approval/CRL; update 2026 tracker | Auto / David |
| 🔴 HIGH | **Re-enable 9realms MCP connector** — 19 runs without ODIN/GUNGNIR production scoring | David |
| 🟡 MEDIUM | **Fix pdufa.bio March 2026 page**: LLY Orforglipron listed as T2D/Mar 25 → should be obesity/Apr 10 | David |
| 🟡 MEDIUM | **Add BIIB/IONS high-dose nusinersen** to pdufa.bio April 2026 page (Apr 3, TIER_1/2 estimate) | David |
| 🟡 MEDIUM | **Confirm Orca-T on pdufa.bio** April 2026 page (Apr 6, private sponsor) | David |
| 🟡 MEDIUM | **Formally decide LGB optimizer fate** — 480+ rounds without improvement; restart (Brier objective), retire, or cap at 800 | David |
| 🟡 MEDIUM | **File FinBrain bug** — Pydantic v2 model_type validation error; 19 consecutive failures | David |
| 🟡 MEDIUM | **File ClinicalTrials.gov bug** — Both `get_study` (regex error) and `search_studies` (0 results) now broken | David |
| 🟢 LOW | Score BIIB high-dose nusinersen with ODIN (once 9realms re-enabled): supplemental + strong global approvals → likely TIER_1/2 | David |
| 🟢 LOW | Build ODIN feature profiles for REPL RP1 (Apr 10) and AXSM AXS-05 (Apr 30) | David |

---

*This report is generated by an automated monitoring agent. All investment-related content is informational/educational only and does not constitute investment advice. Consult a financial advisor before making investment decisions.*
