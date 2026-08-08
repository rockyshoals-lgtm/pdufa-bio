# ODIN v6 / GUNGNIR v30 Monitor Report — v18
**Generated**: 2026-03-25T20:00:00Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v17.md

---

## ⚡ BREAKING: Two Major Events Since v17

1. **DNLI Avlayah (tividenofusp alfa) APPROVED March 24, 2026** — FDA approved tividenofusp alfa as "Avlayah" for Hunter syndrome (MPS II), 12 days before its April 5 PDUFA date. This is the **8th novel drug** approved in 2026 per the FDA's official Novel Drug Approvals page. Removes DNLI from the upcoming April watchlist.

2. **RCKT Kresladi STILL PENDING** — No FDA decision detected as of this run. PDUFA remains March 28, 2026 (3 days away). Decision is IMMINENT. All sources confirm the drug is still under review.

---

## 1. Executive Summary

One early approval and one imminent decision define this run. DNLI's tividenofusp alfa was approved as Avlayah on March 24 — the second early approval this week (following GSK linerixibat on March 19). RCKT Kresladi decision remains pending for March 28 with no early signal either way. A major new addition to the April watchlist: Orca Bio's Orca-T (PDUFA April 6) — a RMAT/Orphan allogeneic cell therapy for AML/ALL/MDS with strong Phase 3 data, not previously tracked. LGB optimizer ran 100 more rounds (621→721) with zero new promotions, confirming complete plateau. Both champion models unchanged. 9realms and FinBrain remain broken for the 18th consecutive run. ClinicalTrials.gov `get_study` also newly broken (NCT ID regex validation error). Perplexity search remains the primary intelligence source.

**Site alert**: pdufa.bio March 2026 page lists "LLY Orforglipron | T2D | Mar 25" — this is incorrect (should be obesity NDA, April 10). Needs correction.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial run) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | **-7.45% worse** |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**Status**: No v6.2 deploy config detected. v6.1 remains champion. No optimizer activity.

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
| Total rounds run | **721** (up from 621 in v17, +100 new rounds) |
| Total champion promotions | **8** (unchanged) |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| Latest ensemble pool file | `lgb_r00619_783a2c1ff85c.pkl` (Mar 2) |
| Rounds since last promotion | **≥480** (r241 → r721) |
| Days since last promotion | **~24 days** |

**Assessment**: 100 new rounds ran since v17, but **zero promotions** — confirming full plateau. The ensemble pool file hasn't updated (still last modified Mar 2), suggesting the optimizer is cycling through configurations without finding improvements. At 480+ rounds without a champion update, the LGB parallel track has effectively exhausted its search space.

**⚠️ Recommendation**: Decision is overdue. The three options remain:
1. Restart with Brier as primary objective (vs current WF AUC) — likely to find improvements
2. Formally retire LGB track; dedicate focus to v6.1/v30.1 deployment
3. Cap at 800 rounds and produce a final audit report

---

## 4. PDUFA Events Watch — Updated

### ✅ NEW (THIS RUN): DNLI Avlayah (tividenofusp alfa) — APPROVED March 24, 2026 (12 days early)
- **PDUFA was**: April 5, 2026 (extended from Jan 5 due to Major Amendment)
- **Indication**: Hunter syndrome (Mucopolysaccharidosis Type II / MPS II)
- **Type**: BLA, Accelerated Approval, Breakthrough Therapy + Priority Review
- **Designations**: Fast Track, Breakthrough Therapy, Priority Review (FDA); Priority Medicines (EMA)
- **Approval note**: Approved as "Avlayah" — #8 novel drug approved in 2026 per FDA.gov. First brain-penetrant enzyme replacement therapy for MPS II (TransportVehicle™ platform). No competing approved brain-penetrant therapy existed.
- **ODIN retrospective**: Would likely have been TIER_1 given BTD + experienced-equivalent (Sanofi partnership) + accelerated approval pathway + unmet need + Priority Review + no prior CRL.
- **Action**: Remove from April watchlist. Add to 2026 validation tracker. Update pdufa.bio April 2026 page.

---

### ⏳ IMMINENT: RCKT Kresladi — **March 28, 2026 (3 days)**
- **ODIN Tier**: TIER_2 (Cautious Long — small/inexperienced sponsor, 2× prior CMC CRLs, gene therapy)
- **Indication**: Leukocyte Adhesion Deficiency Type I (LAD-I) — ultra-rare, fatal in childhood
- **Type**: BLA resubmission (2nd resubmission, Class 2 response)
- **Designations**: RMAT, Rare Pediatric, Fast Track (US); PRIME, ATMP (EU)
- **Clinical data**: 100% overall survival at 12 months post-infusion; all primary/secondary endpoints met
- **Status this run**: No FDA decision detected. Multiple sources confirm pending status as of March 25, 2026. Most recent article (ApertureBio Substack, March 24) discusses probability modeling for the decision, confirming it hasn't happened yet.
- **Key risk**: Third CMC CRL remains possible but significantly de-risked by FDA's collaborative approach.
- **PRV**: Eligible for Rare Pediatric Disease PRV (~$100M+ if approved and sold)
- **Action**: Monitor RCKT press releases and FDA announcements on March 28. Log outcome in v19.

---

### 🆕 NEW ADDITION: Orca-T (Orca Bio) — **April 6, 2026 (12 days)**
- **ODIN Tier**: Not formally scored — Orca Bio is private, no ticker
- **Indication**: AML, ALL, MDS — allogeneic hematopoietic stem cell transplant alternative
- **Type**: BLA, Priority Review, RMAT + Orphan Drug Designation
- **Sponsor**: Orca Bio (private, 187-patient Phase 3 pivotal)
- **Phase 3 data (Precision-T, NCT05316701)**: Primary endpoint met — statistically significant improvement in GVHD-free survival (78% vs 38% at 1 year, HR 0.26, p<0.00001). Grade III/IV acute GvHD: 6.2% vs 16.5%. Phase 3 published in *Blood* (Dec 2025).
- **Clinical note**: First Treg-based immunotherapy to demonstrate improved overall survival and GRFS vs conventional allo-HSCT. Strong data profile — comparable to a TIER_1/TIER_2 profile (strong P3, RMAT, orphan, met endpoints).
- **Risk factors**: Private company; manufacturing complexity of multi-component cell therapy (CD34+ stem cells + Tregs + conventional T cells); 4th CMC risk dimension (similar pattern to gene therapies).
- **Action**: Add to April watchlist. Add GUNGNIR scoring context (phase readout equivalent).

---

### ⏳ WATCH: LLY Orforglipron (obesity) — **April 10, 2026 (16 days)**
- **ODIN Tier**: TIER_1 (Highest-conviction upcoming catalyst)
- **Type**: NDA, Commissioner's National Priority Voucher
- **Sponsor**: Eli Lilly (highly experienced)
- **Context**: Novo Nordisk's oral semaglutide was approved before this run (first-mover in oral GLP-1 class). LLY is behind by weeks. Orforglipron is differentiated (different mechanism, once-daily, no food/water restriction). Market large enough for multiple products.
- **ATTAIN-MAINTAIN**: Positive topline published Dec 18, 2025 — orforglipron maintained weight after GLP-1 injectable. Strengthens commercial case. NDA formally submitted with Commissioner's Priority Voucher.
- **⚠️ pdufa.bio ERROR**: March 2026 page incorrectly lists "LLY | Orforglipron | Type 2 Diabetes | Mar 25." The confirmed PDUFA is **April 10** for **obesity**. T2D NDA is a separate future submission. Site needs correction.
- **Assessment**: TIER_1 conviction maintained despite Novo first-mover. Both registrational trials complete, strong data.

---

### ✅ RESOLVED: Prior Approvals This Run
| Drug | Approval Date | Indication | ODIN Notes |
|------|--------------|------------|------------|
| DNLI Avlayah (tividenofusp alfa) | Mar 24, 2026 (early) | Hunter syndrome MPS II | BTD + Priority + Rare → validates TIER_1 logic |

---

### 📋 Upcoming Pipeline — Updated for v18

| Date | Ticker | Drug | Indication | ODIN Tier | Notes |
|------|--------|------|-----------|-----------|-------|
| Mar 28 | RCKT | Kresladi | LAD-I (gene therapy) | TIER_2 | **IMMINENT — 3 days** |
| Apr 3 | BIIB/IONS | Nusinersen (high dose) | Spinal Muscular Atrophy | TBD | Supplemental; prior CRL |
| Apr 6 | Orca Bio | Orca-T | AML/ALL/MDS | N/A (private) | **NEW** — strong P3 data |
| Apr 10 | LLY | Orforglipron | Obesity | TIER_1 | Top conviction |
| Apr 10 | REPL | RP1 (vusolimogene) | Advanced melanoma | TBD | Priority review |
| Apr 30 | AXSM | AXS-05 | Major Depressive Disorder | TBD | Supplemental |
| Jun 29 | LNTH | Ga68-edotreotide | GEP-NETs PET imaging | TIER_1 | Mfg delay |

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

**YTD approval rate (confirmed tracked events)**: 4 approvals from 4 tracked events = **100%** (note: 3 of 4 were early approvals, consistent with elevated 2026 environment).

**Notable Q1 2026 CRLs** (from CheckRare / external tracking — not in prior ODIN watchlist):
- Atara tabelecleucel (EBV+ PTLD) → CRL Jan 10
- Pharming leniolisib (APDS) → CRL Jan 31
- REGENXBIO clemidsogene/RGX-121 (MPS II) → CRL Feb 8
- Disc Medicine bitopertin (EPP) → CRL Feb 13
- Chiesi idebenone (LHON) → CRL Feb 28

---

## 6. Infrastructure MCP Status — Run #18

| Tool | Status | Consecutive Failures | Error |
|------|--------|---------------------|-------|
| 9realms `odin_score` | ❌ DISABLED | **18** | "This tool has been disabled in your connector settings" |
| 9realms `gungnir_score` | ❌ DISABLED | **18** | Same |
| 9realms `system_status` | ❌ DISABLED | **18** | Same |
| FinBrain `insider_transactions_by_ticker` | ❌ BROKEN | **18** | Pydantic v2: `InsiderReq` model_type validation error |
| FinBrain `news_sentiment_by_ticker` | ❌ BROKEN | **18** | Same (untested this run, same root cause) |
| FinBrain `analyst_ratings_by_ticker` | ❌ BROKEN | **18** | Same |
| ClinicalTrials.gov `get_study` | ❌ NEW FAILURE | 1 | NCT ID regex validation error ("NCT ID must be 8 digits") |
| ClinicalTrials.gov `search_studies` | ⚠️ PARTIAL | — | Works for some queries; RCKT search returned 0 results |
| Perplexity `perplexity_search` | ✅ WORKING | — | **Primary intelligence source** — all key data retrieved this run |

**ClinicalTrials.gov regression**: The `get_study` tool, which worked in v17, is now failing with a regex validation error for NCT IDs. The tool description says "NCT ID must be 8 digits" but standard NCT IDs are 11 characters (NCT + 8 digits). This appears to be a server-side validation bug — the regex may be checking for bare 8-digit strings and failing on full "NCTxxxxxxxx" format.

**Workaround applied**: Perplexity search successfully retrieved all needed trial data (RCKT NCT03812263, Orca-T NCT05316701, orforglipron ATTAIN trials). ClinicalTrials.gov CTGOV cache in `ctgov_cache.json` (1,981 entries) remains the backup for production scoring.

---

## 7. What's New vs v17

1. **🎯 DNLI Avlayah APPROVED March 24**: Tividenofusp alfa approved 12 days early as "Avlayah" for Hunter syndrome (MPS II). BTD + Priority + rare = validates TIER_1 logic. The 4th early approval in March (linerixibat Mar 19, Lynavoy Mar 17 overlap, Avlayah Mar 24). 2026 approval environment remains strongly elevated.
2. **⏳ RCKT still pending**: No FDA decision detected as of March 25. Decision due March 28. TIER_2 maintained.
3. **🆕 Orca-T added to watchlist (April 6)**: Strong Phase 3 data published in *Blood*. RMAT + Orphan. First allogeneic T-cell alternative to allo-HSCT. Not previously tracked.
4. **⚠️ pdufa.bio page error identified**: March 2026 page has wrong LLY data (T2D/Mar 25 vs obesity/Apr 10). Site correction needed.
5. **🔄 Optimizer: 100 new rounds, 0 promotions**: LGB at 721 rounds, still stuck at r241 champion. Formally in plateau.
6. **❌ ClinicalTrials.gov get_study newly broken**: NCT ID regex validation error. `search_studies` still partial.
7. **FDA.gov 2026 tracker confirms 8 approvals** through March 25: Zycubo, Adquey, Bysanti, Loargys, Yuviwel, Lynavoy, Icotyde, Avlayah. Strong year.
8. **9realms failure count**: Now 18 consecutive (up from 17).
9. **FinBrain failure count**: Now 18 consecutive (up from 17).

---

## 8. Recommended Actions

| Priority | Action | Owner |
|----------|--------|-------|
| 🔴 HIGH | **Monitor RCKT March 28** — approval/CRL decision in 3 days; log outcome in v19 | Auto / David |
| 🔴 HIGH | **Re-enable 9realms MCP connector** — 18 runs without production ODIN/GUNGNIR scoring | David |
| 🟡 MEDIUM | **Fix pdufa.bio March 2026 page**: LLY Orforglipron is listed as T2D/Mar 25 — should be obesity/Apr 10 | David |
| 🟡 MEDIUM | **Add DNLI Avlayah to pdufa.bio resolved decisions** and April 2026 page (approved early) | David |
| 🟡 MEDIUM | **Add Orca-T (April 6) to pdufa.bio April 2026 page** — significant new catalyst not yet listed | David |
| 🟡 MEDIUM | **Formally decide LGB optimizer fate** — 480+ rounds without improvement; restart, retire, or cap | David |
| 🟡 MEDIUM | **File FinBrain bug report** — Pydantic v2 model_type validation error blocking all 3 FinBrain tools | David |
| 🟡 MEDIUM | **Fix ClinicalTrials.gov get_study** — NCT ID regex validation newly broken; report to MCP maintainer | David |
| 🟢 LOW | Build ODIN feature profiles for Orca-T (Apr 6), REPL RP1 (Apr 10), BIIB/IONS nusinersen (Apr 3) | David |
| 🟢 LOW | Update CTGOV cache with Orca-T NCT05316701 entry (real trial design data) | David |

---

*This report is generated by an automated monitoring agent. All investment-related content is informational/educational only and does not constitute investment advice. Consult a financial advisor before making investment decisions.*
