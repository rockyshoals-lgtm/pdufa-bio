# ODIN v6 / GUNGNIR v30 — Monitor Report v14
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## ⚠️ CRITICAL CALENDAR CORRECTION — LLY Orforglipron T2D PDUFA "March 25" IS A DATA ERROR

**pdufa.bio lists LLY Orforglipron for Type 2 Diabetes with a PDUFA date of March 25, 2026 (TODAY), rated ODIN TIER_1. This entry is INCORRECT and should be removed or corrected immediately.**

**Evidence confirming no T2D NDA has been filed:**
- Lilly official press release (Feb 26, 2026, Investor Relations): *"Lilly has submitted orforglipron to regulators in over 40 countries, with submission for **type 2 diabetes in the U.S. planned later this year**."*
- MedCentral (Feb 11, 2026): *"Eli Lilly plans to submit an additional application to the FDA this year for orforglipron in type 2 diabetes."*
- Lilly FAQ page (Oct 2025): *"Lilly plans to submit orforglipron for regulatory review for the treatment of overweight or obesity in **2025**, and for type 2 diabetes in **2026**."*
- ACHIEVE-4 (NCT06192108) completed Sep 2025; ACHIEVE-3 Lancet published Feb 26, 2026. T2D submission requires these data, which were only available in late 2025/Q1 2026.

**What IS active:**
- **Orforglipron (Obesity) NDA — PDUFA April 10, 2026**: Active FDA review under Commissioner's National Priority Voucher program. Extended from March 28. Q2 2026 action expected. CEO David Ricks confirmed "at pace" at JPM (Jan 14, 2026).

**Required pdufa.bio action:** Remove the March 25 LLY T2D entry. It has no NDA filed. Ensure the April 10 obesity PDUFA entry is present and active. The T2D NDA, when submitted ~mid-2026, would yield a ~Q4 2026 or early 2027 PDUFA.

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | ✅ CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | −7.5% vs v5 | 0.859 | 65 | ❌ Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | ✅ CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | ❌ Retired |

**No model changes since v13.** Both deploy configs confirmed present and unmodified.

### ODIN v6.1 Architecture Details
- Ridge L2, C=15.0, 32 forward-selected features
- v5's 25 features + 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`
- Isotonic calibration applied
- Trained on 1,845 events, 358-event holdout, temporal cutoff 2025-01-01
- Holdout AUC 0.897 (+2.9pp vs v5's 0.871)

### GUNGNIR v30.1 Architecture Details
- Ridge(70%) + Trees(30%) blend, 26 features
- Key features: `j_last_neg`, `des_rct`, `des_orr`, `era_post24`, `drug_last`, `has_ppm`, `sp_sr`, `competitive`, `is_asco`
- Ridge C=30
- 56.9% Brier improvement over v29 remains the largest single-version jump in GUNGNIR history
- Note: v30.1 AUC not captured in deploy config (likely AUC < v30.0's 0.822 — ridge tradeoff for Brier)

### Autonomous LGB Optimizer — Idle for 24 Days
- Last checkpoint: Round 241, 2026-03-01T01:51:54 (now **24 days idle**, identical to v12/v13)
- 8 total champion checkpoints recorded, rounds 1–241
- Best LGB WF AUC: 0.8852, WF Brier: 0.2057 (notably worse Brier than ODIN v6.1's 0.1102)
- The high WF Brier (0.2057) vs low holdout Brier (0.1102) for ODIN v6.1 confirms the LGB optimizer is measuring on a different validation scheme (walk-forward vs temporal holdout)
- Top features: `v1067_minus_v1070` (9,009 importance), `historical_crl_rate` (8,576), `v1070_score` (6,940) — ODIN score differentials dominate
- Optimizer appears terminated or abandoned; 480 of 721 planned rounds remain unexecuted

---

## 2. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| **9realms MCP** | 🔴 DISABLED | `system_status`, `odin_score`, `gungnir_score` all blocked. **14th consecutive failed run.** |
| **FinBrain MCP** | 🔴 BROKEN | Pydantic `InsiderReq` / `SentimentsReq` / `AnalystRatingsReq` still rejecting string-serialized JSON. All 3 tools fail with same `Input should be a valid dictionary or instance of [Model]` error. **14th consecutive failed run.** Root cause: MCP server requires dict objects, not JSON strings, for `req` parameter. Fix requires server-side JSON deserialization patch. |
| **ClinicalTrials.gov MCP** | ✅ FUNCTIONAL | 4 searches executed successfully. Full results returned. Regression from v12 remains resolved. |
| **Perplexity MCP** | ✅ FUNCTIONAL | 4 searches executed successfully. |

---

## 3. Catalyst Calendar — Active PDUFA Events

### Resolved Since Last Report (as of Mar 25, 2026)

| Date | Ticker | Drug | Indication | Outcome |
|------|--------|------|-----------|---------|
| Mar 6, 2026 | BMY | Deucravacitinib (Sotyktu) | Psoriatic Arthritis (sBLA) | TIER_1 — likely APPROVED (no CRL news found) |
| Mar 20, 2026 | RYTM | Imcivree (setmelanotide) | Hypothalamic Obesity | TIER_2 — status unconfirmed |
| Mar 24, 2026 | GSK | Linerixibat | Cholestatic Pruritus (PBC) | ✅ **APPROVED** (CheckRare confirms Mar 24) |

### Upcoming PDUFA Events (Next 30 Days)

| Date | Ticker | Drug | Indication | pdufa.bio ODIN Tier | Notes |
|------|--------|------|-----------|---------------------|-------|
| **Mar 28, 2026** | **RCKT** | **Kresladi** | **LAD-I Gene Therapy** | **TIER_2** | 3 days away — resubmission after CMC CRL |
| **Mar 29, 2026** | **LNTH** | **Ga68-edotreotide** | **GEP-NETs Imaging** | **TIER_1** | 4 days away — diagnostic imaging |
| Apr 5, 2026 | DNLI | Tividenofusp alfa | MPS-IIIA (Sanfilippo) | — | Rare disease, BLA accepted |
| Apr 6, 2026 | Orca Bio | Orca-T | AML/ALL/MDS | — | Priority review, no adcom required |
| **Apr 10, 2026** | **LLY** | **Orforglipron** | **Obesity** | **TIER_1** | High-conviction — see Section 4 |
| Apr 13, 2026 | TVTX | Filspari (sparsentan) | FSGS | — | sNDA |

---

## 4. High-Priority Catalyst Deep-Dives

### RCKT Kresladi — PDUFA March 28, 2026 (3 DAYS)
**Designation**: RMAT + Rare Pediatric + Fast Track | **ODIN**: TIER_2 | **Type**: BLA Resubmission

**Clinical package**: Phase 1/2 global trial — 100% overall survival at 12 months post-infusion for all enrolled patients, 0 treatment-related serious adverse events, substantial reduction in severe infections. Disease (severe LAD-I) kills 60–75% of patients before age 2 without bone marrow transplant.

**Regulatory history**: Prior CRL was CMC-related (manufacturing/controls data). FDA accepted resubmission Oct 14, 2025. No adcom required. FDA confirmed the CMC-limited nature of the prior CRL — data package itself was not challenged.

**Risk factors**: Gene therapy + resubmission = elevated risk vs first-time NDA. Small patient population (< 100 globally) means limited post-market pharmacovigilance data. CMC issues not always fully resolved on first resubmission.

**Commercial upside if approved**: Rare Pediatric Disease PRV (worth $70–350M). Premium pricing (analogous to Zolgensma at $2.1M, Hemgenix at $3.5M).

**ODIN assessment**: TIER_2 is appropriate — resubmission + gene therapy are ODIN penalty factors. Clinical data is exceptionally strong, but CMC resubmission risk is real.

---

### LLY Orforglipron (Obesity) — PDUFA April 10, 2026 (16 DAYS)
**Designation**: Commissioner's National Priority Voucher | **ODIN**: TIER_1 | **Type**: NDA

**Clinical package (from CTGOV + Perplexity)**:
- ATTAIN-1 (NCT05869903): 3,127 patients, obesity without T2D — ACTIVE_NOT_RECRUITING, primary completion Jul 2025 ✅
- ATTAIN-2 (NCT05872620): 1,613 patients, obesity + T2D — COMPLETED Aug 2025 ✅. Results: 9.6% weight loss at 72 weeks for 36mg vs 2.5% placebo. A1C reduction up to 1.66%.
- ATTAIN-MAINTAIN (Lilly Dec 2025): Met primary endpoint for weight maintenance after transitioning from Wegovy/Zepbound
- ACHIEVE-3 (Feb 26, 2026, Lancet): Head-to-head vs oral semaglutide — orforglipron 36mg lowered A1C 2.2% vs 1.4% for oral semaglutide; weight loss 73.6% greater

**Competitive context**: Novo Nordisk's oral semaglutide (Rybelsus/oral Wegovy) launched. Orforglipron is small-molecule (no food/water timing restrictions), potentially superior adherence. ACHIEVE-3 head-to-head data published in The Lancet.

**FDA trajectory**: CNPV program. Initial March 28 target → extended to April 10. Lilly CEO: review "moving at pace." Medicare obesity coverage begins April 2026 — commercial launch alignment is perfect.

**ODIN assessment**: TIER_1 highly appropriate. Experienced sponsor (15+ prior approvals), Priority Review, strong efficacy data, major unmet need, NDA (not BLA), endocrinology (ODIN-favorable TA). Approval probability likely >90%.

---

### LNTH Ga68-edotreotide — PDUFA March 29, 2026 (4 DAYS)
**Designation**: Priority Review | **ODIN**: TIER_1 | **Type**: NDA (diagnostic)

Novel PET imaging agent for GEP-NET tumors. Complements Lutathera (Novartis) treatment pathway. Diagnostic imaging has historically high FDA approval rates. No safety concerns expected (imaging agent, not therapeutic). TIER_1 is appropriate.

---

## 5. CTGOV Cache Validation — Orforglipron

**Validation result**: Phase 3 ACHIEVE T2D trials are ALL completed and support NDA submission, but the **US T2D NDA has not been filed** as of this report date. pdufa.bio cache entry `LLY / orforglipron / T2D / 2026-03-25` should be purged.

| NCT ID | Trial | Status | n | Primary Completion | Notes |
|--------|-------|--------|---|---------------------|-------|
| NCT06192108 | ACHIEVE-4 (vs dapagliflozin) | COMPLETED | 962 | Sep 2025 | Key registrational trial |
| NCT05971940 | ACHIEVE (diet/exercise alone) | COMPLETED | 559 | Apr 2025 | |
| NCT05872620 | ACHIEVE (obesity + T2D) | COMPLETED | 1,613 | Aug 2025 | ATTAIN-2 |
| NCT06972459 | New obesity P3 | RECRUITING | 600 | Jan 2027 | Post-approval study |
| NCT06649045 | OSA + obesity | ACTIVE, NOT RECRUITING | 600 | Nov 2026 | Label extension program |

---

## 6. VRTX and ABBV Catalyst Status

### VRTX Suzetrigine (VX-548)
- **Already approved** Jan 2025 for acute pain (first-in-class Nav1.8 inhibitor)
- Phase 3 pivotal trials (NCT05553366, NCT05558410) both **COMPLETED**
- Phase 4 real-world study (NCT06887972) **COMPLETED** Nov 2025 — n=100 aesthetic/reconstructive
- New Phase 4 study (NCT07463430) not yet recruiting (planned 2027)
- **No upcoming PDUFA for VRTX** in near-term. Next catalyst: potential new indication (neuropathic pain)

### ABBV Emraclidine (CVL-231)
- **Phase 2 only** — no Phase 3 program yet for schizophrenia
- Phase 2 trials: NCT05227690 (385 pts, completed Aug 2024), NCT05227703 (391 pts, completed Sep 2024), NCT05443724 (700 pts, completed Jun 2025)
- New Phase 2 study RECRUITING (NCT07145918, 268 pts, completion Feb 2028)
- **No near-term PDUFA for ABBV emraclidine** — Phase 3 program decision pending Phase 2 readouts
- Phase 2 at 10mg and 30mg doses showed efficacy; 30mg appeared superior. Phase 3 dose selection underway.

---

## 7. Recent FDA Performance (Q1 2026 Scorecard)

Based on CheckRare and Perplexity data through March 24, 2026:

| Date | Ticker | Drug | Outcome |
|------|--------|------|---------|
| Jan 5, 2026 | SRRK | Caplacizumab | ✅ APPROVED |
| Jan 10, 2026 | ATRA | Tabelecleucel | ❌ CRL |
| Jan 13, 2026 | SNY | Cerezyme | ✅ APPROVED |
| Jan 14, 2026 | SNTL | CUTX-101 (copper histidinate) | ✅ APPROVED |
| Jan 27, 2026 | JNJ | Darzalex Faspro + D-VRd | ✅ APPROVED |
| Jan 31, 2026 | PHAR | Leniolisib | ❌ CRL |
| Feb 8, 2026 | RGNX | RGX-121 (clemidsogene) | ❌ CRL |
| Feb 13, 2026 | DSCP | Bitopertin | ❌ CRL |
| Feb 20, 2026 | ABBV | Venetoclax + Acalabrutinib | ✅ APPROVED |
| Feb 23, 2026 | PHAR | Pegzilarginase | ✅ APPROVED |
| Feb 25, 2026 | ETON | ET-600 | ✅ APPROVED |
| Feb 28, 2026 | BMRN | Palynziq (pegvaliase) | ✅ APPROVED |
| Feb 28, 2026 | ASND | Navepegritide (TransCon CNP) | ✅ APPROVED |
| Feb 28, 2026 | Chiesi | Idebenone | ❌ CRL |
| Mar 3, 2026 | Chiesi | Lomitapide | ✅ APPROVED |
| Mar 5, 2026 | JNJ | Tec-Dara (teclistamab + daratumumab) | ✅ APPROVED |
| Mar 10, 2026 | GSK | Leucovorin (Wellcovorin) | ✅ APPROVED |
| Mar 24, 2026 | GSK | Linerixibat | ✅ APPROVED |

**YTD 2026 through Mar 24**: 14 approvals, 5 CRLs → **74% approval rate** (Q1). Historical PDUFA average ~67.7%. Q1 2026 running above baseline.

---

## 8. Key Findings vs v13 — What's New

| Topic | v13 Status | v14 Update |
|-------|-----------|------------|
| LLY T2D NDA | Flagged as potential error, unknown | **CONFIRMED ERROR**: T2D NDA not filed as of Feb 26, 2026. pdufa.bio calendar entry must be removed. |
| LLY obesity (Apr 10) | Active, TIER_1 | No change — confirmed active, strong clinical package |
| GSK Linerixibat (Mar 24) | Upcoming | **APPROVED Mar 24** — TIER_1 correct |
| RCKT Kresladi (Mar 28) | Upcoming | **3 DAYS TO PDUFA** — strong data, resubmission risk |
| LNTH Ga68-edotreotide (Mar 29) | Upcoming | **4 DAYS TO PDUFA** — diagnostic, TIER_1 appropriate |
| 9realms MCP | Disabled | Still disabled (14th run) |
| FinBrain MCP | Broken | Still broken (14th run) — Pydantic schema error persists |
| LGB Optimizer | Idle 24 days | Still idle 24 days (no new activity) |
| VRTX | No PDUFA noted | Confirmed — already approved, no upcoming PDUFA |
| ABBV emraclidine | Not tracked | Phase 2 only — no near-term PDUFA |

---

## 9. Recommended Actions

### Immediate (Today)
1. **REMOVE** the LLY Orforglipron T2D entry from pdufa.bio March 2026 page and calendar. The NDA has not been filed. Leaving this entry live risks credibility and ODIN score accuracy. The entry is already rendering as "today" with no FDA action possible.
2. **CONFIRM** outcome for BMY Deucravacitinib (Mar 6 PDUFA) and RYTM Imcivree (Mar 20 PDUFA) — neither outcome was confirmed in this run. Add to "Resolved" section once confirmed.

### Near-Term (This Week)
3. **Monitor RCKT Kresladi** (PDUFA Mar 28): Watch for FDA announcement. If approved, log for ODIN model validation (TIER_2 → approval = confirm model calibration). If CRL, confirm CMC-related (model accuracy).
4. **Monitor LNTH Ga68-edotreotide** (PDUFA Mar 29): TIER_1 diagnostic imaging — high probability of approval. Confirm outcome for model validation.
5. **Add LLY Orforglipron Obesity** entry to April 2026 PDUFA calendar if not already present — PDUFA April 10, 2026, TIER_1.

### Medium-Term
6. **FinBrain MCP fix**: The `req` parameter error has persisted 14 runs. Root cause is clear: the MCP server expects a Python dict object for `InsiderReq`/`SentimentsReq`/`AnalystRatingsReq`, not a JSON string. This requires a server-side patch to JSON-deserialize string inputs, or the API documentation needs to clarify the correct calling convention.
7. **9realms MCP**: Remains disabled (14 consecutive runs). Unclear whether this is a connector settings issue or infrastructure problem. Production ODIN/GUNGNIR scoring is blocked.
8. **LGB Optimizer**: Restart or formally retire. 480 rounds remain unrun since March 1. The optimizer's best WF Brier (0.2057) is significantly worse than ODIN v6.1's holdout Brier (0.1102), suggesting the LGB approach may not be superior to the Ridge v6.1 champion on the relevant metric. Recommend formal comparison on identical validation splits before investing further compute.
9. **LLY Orforglipron T2D NDA**: Expected mid-2026 submission. Monitor Lilly investor relations for NDA filing announcement. When submitted, add to pdufa.bio calendar (~Q4 2026 or Q1 2027 PDUFA, depending on review type).

---

## 10. Summary

Both champion models (ODIN v6.1, GUNGNIR v30.1) are stable and unmodified. No optimization progress since March 1. The highest-priority operational issue is the incorrect LLY T2D PDUFA entry on pdufa.bio — the T2D NDA has not been filed as of February 26, 2026, making the March 25 "PDUFA date" fabricated. The obesity NDA is under active FDA review with PDUFA April 10.

Near-term catalysts to watch: RCKT Kresladi (March 28, TIER_2 resubmission) and LNTH Ga68-edotreotide (March 29, TIER_1 diagnostic). LLY Orforglipron obesity (April 10, TIER_1) is the highest-conviction upcoming event in the calendar.

---

*This report is for informational and research purposes only. Not investment advice. ODIN/GUNGNIR scores are probabilistic models with inherent uncertainty.*
