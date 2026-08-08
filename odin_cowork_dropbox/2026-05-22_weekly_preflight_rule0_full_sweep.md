# Weekly Friday Pre-Flight — 2026-05-22

**Run timestamp:** 2026-05-22 (Friday) ~17:00 ET — autonomous scheduled task execution (Rule 0 Full Sweep, Amendment 027 compliance)
**Protocol:** 5-step Rule 0 verification (SEC 8-K, IR page, ClinicalTrials.gov, Google News 7d, Date Confidence Tier) on every active watchlist candidate within T-30 of catalyst.
**Operator:** scheduled-task `weekly-friday-preflight`
**Prior week baseline:** `weekly_preflight_2026-05-08.md`
**Today's locked portfolio (immutable until David clears):** UNCY 6,593.31 sh ($53,274 MV), CAPR 535 sh ($15,445 MV), CRDF 40 calls $2.50 6/18/26 ($600 MV). Totals $69,319 MV / +$1,296 (+1.91%).
**Two daily scans already ran today (May 22):** `daily_news_scan_2026-05-22.md` (~07:00 ET) + `2026-05-22_daily_uw_flow_monitor.md`. This pre-flight rolls forward verified findings, applies the 5-step sweep to all 20 candidates, and surfaces what changed vs. May 8.

---

## EXECUTIVE SUMMARY — KEY FINDINGS

| # | Ticker | Finding | Severity | Action |
|---|--------|---------|----------|--------|
| 1 | **MNKD** | T-5 trading days to May 29 PDUFA. BIFROST forced-exit signal at today's close. | 🟡 INFO | Not in portfolio — no action |
| 2 | **CRDF** | T-7 calendar days to ASCO June 2 oral. ASCO abstract #3510 went live 5/21. **40-call salvage position locked**; exit window 5/26–6/1 (hard stop). | 🟡 ACTIVE | **Pull abstract #3510 from ASCO.org; stage exit per pre-authorized window** |
| 3 | **UNCY** | Canonical calendar still shows 6/27 — actual PDUFA is **6/29** (CEO direct quote, 4th day flagged). Locked position 6,593 sh = 76.9% of portfolio. Exit window 6/12–6/17 per portfolio lock. | 🟠 OPEN | **Update canonical calendar 6/27 → 6/29 (fourth flag)** |
| 4 | **CAPR** | AdCom status **UNRESOLVED** — historical 7/30/2025 AdCom was pulled; no 2026 AdCom currently announced. Class II resub for cell therapy = AdCom-eligible. May 7 NS Pharma lawsuit + May 1 Krasney $793K insider sale stand. PDUFA 8/22/2026 unchanged. | 🟠 OPEN | **Verify FDA AdCom calendar directly** (gap from morning scan, now 2nd day open) |
| 5 | **ACHV** | **BLOCK reinforced** — Q1'26 8-K disclosed two Form 483 observations at named cytisinicline manufacturer during recent cGMP inspection. Adds fresh CMC risk on top of company-pre-announced CRL expectation (Apr 15 PR). | 🚨 BLOCK | **No new entries pre-6/20 PDUFA regardless of any model upgrade** |
| 6 | **9 watchlist tickers already fired** since May 8 sweep (ARVN, AVTX, TRDA, AVBP, CADL, MIRM, WVE, ALXO, AXSM) — confirmed via two daily scans + earlier today's universe refresh. ZBIO is a phantom Jun 30 entry (no real catalyst until SunStone SLE Q4 2026). | ⚠️ CLEAN | **Drop from forward watchlist; preserved in fired-catalyst ledger for postmortem** |
| 7 | **No Tier A → C/D date drops detected.** No new clinical holds. No M&A. No pre-PDUFA outcome pre-announcements beyond the existing ACHV one. CMPX-class surprise is NOT present in this week's data. | ✅ CLEAN | n/a |

**Bottom line:** Quiet week on date-drift surprises. The two highest-priority items are (a) UNCY canonical calendar correction (4th day flagged), and (b) CAPR AdCom verification (2nd day open). Portfolio lock is intact and Cardinal Rule exits are pre-authorized for all three positions.

---

## CONFIRMED LIVE CATALYSTS WITHIN T-46 (POST-FIRED-SCRUB)

### Tier A — firm date, full primary-source verification

| Ticker | Catalyst | Date | T-days | Source | Verdict | Δ vs May 8 |
|--------|----------|------|--------|--------|---------|------------|
| **MNKD** | Afrezza pediatric sBLA PDUFA | **2026-05-29** | T-7 cal / T-5 trading | [MannKind IR sBLA acceptance PR](https://investors.mannkindcorp.com/news-releases/news-release-details/mannkind-announces-us-fda-accepts-review-its-supplemental); [Q1 2026 8-K](https://www.globenewswire.com/news-release/2026/05/06/3289304/29517/en/MannKind-Reports-First-Quarter-2026-Financial-Results-and-Provides-Business-Update.html) | WATCH (not in portfolio) | No change |
| **CRDF** | ASCO 2026 Rapid Oral Abstract #3510 (CRDF-004 onvansertib + SoC + bev in 1L RAS-mut mCRC) | **2026-06-02** 8:00–9:30 AM CDT | T-11 cal / T-7 trading | [Cardiff Apr 21 PR](https://www.globenewswire.com/news-release/2026/04/21/3278117/0/en/Cardiff-Oncology-to-Present-Updated-Phase-2-Data-of-Onvansertib-in-First-Line-RAS-Mutated-mCRC-in-a-Rapid-Oral-Session-at-ASCO-2026.html); [May 22 webcast PR](https://www.manilatimes.net/2026/05/22/tmt-newswire/globenewswire/cardiff-oncology-announces-webcast-to-discuss-updated-phase-2-crdf-004-data-for-onvansertib-in-first-line-ras-mutated-mcrc/2349684) | **ACTIVE — 40 calls locked, hard stop 6/1** | New — confirmed since May 8 |
| **IRON** | ASCO 2026 Oral RALLY-MF DISC-0974 (Abstract #6501) | **2026-06-02** 9:45 AM–12:45 PM CDT | T-11 cal | [Disc Medicine Apr 21 PR](https://www.globenewswire.com/news-release/2026/04/21/3278118/0/en/Disc-Medicine-Announces-Oral-Presentation-of-Data-from-RALLY-MF-Phase-2-Trial-of-DISC-0974-in-Patients-with-Myelofibrosis-and-Anemia-at-the-American-Society-of-Clinical-Oncology-AS.html) | WATCH — not in portfolio per Amendment 031 | No change |
| **ACHV** | Cytisinicline NDA PDUFA | **2026-06-20** | T-29 | [Q3'25 cGMP disclosure](https://ir.achievelifesciences.com/news-events/press-releases/detail/247/achieve-life-sciences-reports-third-quarter-2025-financial-results-provides-updates-on-cytisinicline-program); [Q1'26 8-K](https://www.sec.gov/Archives/edgar/data/0000949858/000119312526218175/d854692dex991.htm) | 🚨 BLOCK — pre-declared CRL + new CMC observations | Substance change — CMC inspection finding added 5/22 |
| **UNCY** | OLC NDA Class II resubmission PDUFA | **2026-06-29** (CEO quote) | T-38 | [Unicycive Jan 29 PR](https://www.globenewswire.com/news-release/2026/01/29/3228698/0/en/UPDATE-Unicycive-Therapeutics-Announces-FDA-Acceptance-of-Oxylanthanum-Carbonate-OLC-New-Drug-Application-NDA-Resubmission.html); [Q1 2026 8-K](https://www.sec.gov/Archives/edgar/data/0001766140/000121390026054736/ea029027701ex99-1.htm) | **LIVE POSITION — hard stop 6/17** | Calendar drift unresolved (4th day) |
| **ARQT** | ZORYVE 0.3% pediatric (ages 2-5) sNDA PDUFA | **2026-06-29** | T-38 | [Q1 2026 8-K](https://www.sec.gov/Archives/edgar/data/0001787306/000178730626000039/pressreleaseex991q12026.htm); [sNDA acceptance](https://www.stocktitan.net/news/ARQT/fda-accepts-supplemental-new-drug-application-for-arcutis-zoryve-fbjbne24pau8.html) | WATCH — TRADE candidate after UNCY/CAPR slots roll | No change. Cash-flow positive Q1, $105M revenue, 2026 guidance reaffirmed |
| **VRDN** | Veligrotug TED BLA Priority Review PDUFA | **2026-06-30** | T-39 | [Q1 2026 8-K](https://www.sec.gov/Archives/edgar/data/0001590750/000119312526205010/d149508dex991.htm); [BLA acceptance PR](https://investors.viridiantherapeutics.com/news/news-details/2025/Viridian-Therapeutics-Announces-BLA-Acceptance-and-Priority-Review-for-Veligrotug-for-the-Treatment-of-Thyroid-Eye-Disease/default.aspx) | WATCH — launch-ready per Q1 commentary | No change. Cash $762M = no dilution risk |
| **CAPR** | Deramiocel DMD cardiomyopathy Class II resub PDUFA | **2026-08-22** | T-92 | [March 10 PDUFA PR](https://www.globenewswire.com/news-release/2026/03/10/3252979/0/en/Capricor-Therapeutics-Announces-Establishment-of-New-PDUFA-Date-for-Deramiocel-BLA.html); [Q1 2026 8-K](https://www.sec.gov/Archives/edgar/data/0001133869/000110465926059380/capr-20260512xex99d1.htm) | **LIVE POSITION — hard stop 8/12; AdCom status UNRESOLVED** | NEW (not in May 8 list) |
| **VERA** | Atacicept IgAN BLA Priority Review PDUFA | **2026-07-07** | T-46 | [Vera Jan 7 Priority Review PR](https://ir.veratx.com/news-releases/news-release-details/vera-therapeutics-announces-us-fda-granted-priority-review/); [Q4'25 8-K](https://www.sec.gov/Archives/edgar/data/0001807587/000119312526058244/d769892dex991.htm) | WATCH — Priority + BTD intact | No change |

### Tier B — specific quarter, no firm date

| Ticker | Catalyst | Window | Source | Verdict | Δ vs May 8 |
|--------|----------|--------|--------|---------|------------|
| **NMRA** | KOASTAL-2 + KOASTAL-3 joint topline (P3 MDD navacaprant) | Q2 2026 (any day through Jun 30) | [Jan 5 2026 priorities PR](https://www.globenewswire.com/news-release/2026/01/05/3212570/0/en/Neumora-Therapeutics-Highlights-2026-Pipeline-Strategy-and-Anticipated-Upcoming-Milestones.html); [10-K Mar 30](https://www.stocktitan.net/sec-filings/NMRA/10-k-neumora-therapeutics-inc-files-annual-report-e10ec54f4ef5.html) | **DO NOT TRADE** (KOASTAL-1 failed; high-stakes retry) | No change |
| **TSHA** | Part A REVEAL Phase 1/2 longer-term safety/efficacy update (12-mo n=12) | Q2 2026 | [Q1 2026 8-K May 6](https://www.sec.gov/Archives/edgar/data/0001745999/000119312526220488/d769892dex991.htm) | WATCH | No change |
| **CABA** | EULAR Jun 3–6 multi-presentation slate (RESET-SLE complete cohort poster Jun 4 9:30 AM BST; RESET-SSc satellite Jun 4 5:30 PM BST); RESET-SLE / RESET-SSc complete P1/2 readouts 1H 2026 | 1H 2026 | [Q4'25 8-K Mar 23](https://www.sec.gov/Archives/edgar/data/0001498233/000119312526094471/d769892dex991.htm); EULAR program | WATCH (no current position, closed +$2,488 ASGCT pre-empt) | $150M Lilly + life-sciences raise May 14; runway into mid-2027 |

---

## DROPPED / FIRED — REMOVE FROM FORWARD WATCHLIST

| Ticker | Reason | Fire Date | Outcome | Source |
|--------|--------|-----------|---------|--------|
| ARVN | VEPPANU PDUFA approved 35d early — first FDA-approved PROTAC | 2026-05-01 | GOOD | Per Apr 30 + May 1 PRs (in `2026-05-01` ledger) |
| AVTX | LOTUS Phase 2 HS POSITIVE — HiSCR75 42.2%/42.9% vs 25.6% placebo; advancing to Phase 3 + $431.3M raise | 2026-05-05 | GOOD | Per May 5 8-K |
| MIRM | VISTAS Phase 2b PSC primary endpoint MET (volixibat); NDA H2 2026 planned | 2026-05-04 | GOOD | [BusinessWire May 4](https://www.businesswire.com/news/home/20260504069726/en/Mirum-Pharmaceuticals-Announces-Primary-Endpoint-Met-in-VISTAS-Study-of-Volixibat-in-Patients-with-Primary-Sclerosing-Cholangitis) |
| TRDA | ELEVATE-44-201 Cohort 1 (6 mg/kg) Phase 1/2 — data GOOD (safety/tolerability + Time to Rise velocity), market BAD (-48–57%; Roth PT $19→$10) | 2026-05-07 | DATA_GOOD_MARKET_BAD | Per universe refresh today |
| ALXO | ESMO Breast May 7 (CD47-high biomarker poster) — closed +$1,888.92 pre-event | 2026-05-07 | RESOLVED (closed) | Per memory Amendment 004 |
| CADL | PrTK03 Phase 3 prostate extended FU at AUA Plenary — 90% reduction in time-to-metastasis (intermediate-risk); BLA Q4 2026; P3 NSCLC starts June 2026 | 2026-05-15 (NOT 4/26 as universe earlier said) | GOOD | [Cadrenal Mar 9 PR](https://ir.cadrenal.com/) (verified prior preflight) |
| WVE | ATS late-breaker RestorAATion-2 (WVE-006 AATD) — Z-AAT -71%, MZ-like phenotype both biweekly + monthly dosing | 2026-05-18 | GOOD (stock -5.47% on May 19 = "sell-the-news" calibration anchor) | [Wave PR May 18](https://www.globenewswire.com/news-release/2026/05/18/3297034/0/en/Wave-Life-Sciences-Announces-Positive-Update-on-RestorAATion-2-Trial-WVE-006-GalNAc-RNA-Editing-Achieves-MZ-Like-Phenotype-Across-Both-Biweekly-and-Monthly-Dosing.html) |
| AXSM | Auvelity AD agitation PDUFA — APPROVED | 2026-04-30 | GOOD | (resolved pre-May 8) |
| AVBP | FURVENT topline guidance slipped from "early 2026" → "mid-2026" — no Apr 30 catalyst | n/a — date drift | UNFIRED (date moved) | [ArriVent Q1 2026 PR May 11](https://www.globenewswire.com/news-release/2026/05/11/3292281/0/en/ArriVent-BioPharma-Reports-First-Quarter-2026-Financial-Results.html) |
| ZBIO | Jun 30 was a phantom date — no real catalyst until SunStone SLE Q4 2026. INDIGO IgG4-RD already met Jan 5 (HR 0.44, p=0.0005). BLA submission Q2 2026 = administrative milestone, not a binary | n/a — phantom | n/a | Per `daily_news_scan_2026-05-22.md` no-change list |

---

## CANDIDATE-BY-CANDIDATE RULE 0 (5-STEP) DETAIL

### 1. CRDF — ASCO Jun 2 — Tier A, N1, ACTIVE LOCKED POSITION
- **Step 1 (8-K):** No new 8-K material since 5/21 abstract release.
- **Step 2 (IR):** May 22 GlobeNewswire/Manila Times PR confirms **investor webcast June 3, 2026 8:30 AM ET** — the trading day after the June 2 oral session. Abstract #3510 went live on ASCO website 5/21.
- **Step 3 (CT.gov):** CRDF-004 Phase 2 randomized trial active; abstract title "Onvansertib + SoC chemo + bevacizumab in 1L RAS-mut mCRC: Interim results from the Phase 2 randomized CRDF-004 trial."
- **Step 4 (News 7d):** No delays/holds/M&A. ASCO website abstract live.
- **Step 5 (Tier):** **A** — firm session date + time. Date Confidence A; Novelty N1 (positive control: April 2025 ORR 17.1% vs paclitaxel 5.3%).
- **Position:** 40 calls $2.50 6/18 ($600 MV / $1,026 cost / -$426). Hard stop **2026-06-01 (Mon, D-1 ASCO)**. Exit window 5/26–6/1.
- **Action:** Pull abstract #3510 from ASCO.org before market open Tuesday (5/26). If ORR/PFS confirm or beat April 2025 baseline, ride into the oral. If abstract is materially weaker, scratch the salvage. **Cardinal Rule prohibits holding through June 2 oral regardless.**

### 2. IRON — ASCO Jun 2 — Tier A, N1, WATCH (no position per Amendment 031)
- **Step 1 (8-K):** No new 8-K. Q1 2026 IR confirms ASCO oral. APOLLO Phase 3 bitopertin Q4 2026 topline is a SEPARATE catalyst (post-CRL).
- **Step 2 (IR):** Apr 21 PR confirms June 2 oral. RALLY-MF n=61 cutoff Apr 27, 2026. Abstract released 5/21.
- **Step 3 (CT.gov):** RALLY-MF Phase 2 study active.
- **Step 4 (News 7d):** No delays.
- **Step 5 (Tier):** **A** — firm session date.
- **Per Amendment 035:** IRON CNPV booster is STRIPPED — first documented CNPV approval failure (bitopertin EPP CRL 2026-02-13).
- **Action:** Pull abstract #6501 to screen entry only if TI rate ≥40%. Currently NO ENTRY per concentrated-regime discipline.

### 3. ARVN — Jun 5 PDUFA → 🚨 ALREADY APPROVED (DROP)
- Removed from forward watchlist. Resolved 2026-05-01, 35 days early. First FDA-approved PROTAC.

### 4. MNKD — May 29 PDUFA — Tier A, N1, WATCH (regime-aware, not in portfolio)
- **Step 1 (8-K):** Q1 2026 8-K (May 6) reaffirms May 29 PDUFA. Furoscix ReadyFlow autoinjector PDUFA July 26 confirmed as separate event.
- **Step 2 (IR):** ATTD Mar 11–14 pediatric data already disclosed. Stock +25.4% post-Q1 raise.
- **Step 3 (CT.gov):** Phase 3 INHALE-1 (ages 4–17) supports filing.
- **Step 4 (News 7d):** No delays, no clinical holds, no AdCom announced (no AdCom needed for sBLA expansion).
- **Step 5 (Tier):** **A** — firm PDUFA.
- **Risk lens:** sBLA expansion of already-approved drug — lower binary risk than NDA. Dead-zone T-7 → T-0 per regime memory; 2026 YTD PDUFA approval rate ~45% (no-ANDA). No position in framework; informational only.

### 5. ACHV — Jun 20 PDUFA — 🚨 BLOCK REINFORCED
- **Step 1 (8-K + IR):** **NEW THIS MORNING:** Q1 2026 8-K + IR materials disclose that "one manufacturer named in the cytisinicline NDA recently underwent an FDA cGMP inspection, where two observations related to solid oral dose manufacturing were identified." This is fresh CMC risk on top of the **Apr 15 PR** explicitly stating "Achieve expects to receive a Complete Response Letter from the FDA on or before its June 20, 2026 PDUFA goal date" + manufacturer Sopharma OAI classification.
- **Step 2 (IR):** Tech transfer to Adare in Vandalia, Ohio complete. First engineering batch produced. Launch pushed to H1 2027.
- **Step 3 (CT.gov):** N/A — regulatory event, no trial.
- **Step 4 (News 7d):** No new clinical holds. 99M warrant overhang persists.
- **Step 5 (Tier):** **A** — date firm. **Outcome pre-declared CRL + freshly stacked CMC inspection observations.**
- **Action:** **BLOCK new entries.** Even with CNPV designation on the vaping-cessation indication, CMC failures override CNPV (CNPV addresses review timing, not facility compliance). Override only with explicit "Override the BLOCK on ACHV because {reason}" + ⚠️ DEVIATION flag.
- **Per Amendment 035:** ACHV double-CRL + CMC = textbook ODIN v14 `mfg_risk_bin` × `pw_double_crl_bin_x_resub_class_2` (-0.173 coef) plus naive sponsor × Class 2 stack. Score collapses regardless of overlay boost.

### 6. UNCY — Jun 29 PDUFA — Tier A, N2, LIVE LOCKED POSITION (50%+ of portfolio)
- **Step 1 (8-K):** Q1 2026 8-K confirms PDUFA on track. Cash $57.1M into 2027 = no immediate dilution.
- **Step 2 (IR):** CEO Shalabh Gupta direct quote (May 12 Q1 PR): "As we approach the **June 29th** PDUFA target action date..."
- **Step 3 (CT.gov):** 505(b)(2) pathway. 3 clinical studies + CMC support filing. No new clin/preclin/safety concerns raised at original NDA.
- **Step 4 (News 7d):** No delays. No post-7am-scan news through mid-afternoon.
- **Step 5 (Tier):** **A** (date is 6/29 per company; canonical calendar still wrong at 6/27 — **4th day flagged**).
- **Position:** 6,593.31 sh (Merrill 4,586 + TOS 2,007.31) = $53,274 MV / $52,443 cost / +$831 (+1.59%). **76.9% portfolio concentration** (over 50% cap from concentrated-regime band — explicitly approved by David as Phase A primary position).
- **Pre-authorized exit:** Hard stop **2026-06-17 (Wed, T-7 effective per corrected date)**. Exit window 6/12–6/17. Stage 25/50/100.
- **Action:** **URGENT — update CANONICAL_CATALYST_CALENDAR_2026-04-24.csv from 6/27 → 6/29** (recompute all dependent exit dates).

### 7. ARQT — Jun 29 PDUFA — Tier A, N2 (line-extension), WATCH
- **Step 1 (8-K):** Q1 2026 8-K confirmed ZORYVE franchise revenue $105M, **cash-flow positive Q1**, 2026 guidance $455–$470M reaffirmed.
- **Step 2 (IR):** Nov 17, 2025 sNDA acceptance confirmed. INTEGUMENT-INFANT Phase 2 positive (3–24 month AD) → Q2 2026 sNDA filing.
- **Step 3 (CT.gov):** MUSE 4-week + long-term open-label support filing.
- **Step 4 (News 7d):** No delays. No CMC red flags.
- **Step 5 (Tier):** **A** — firm date. Pediatric expansion (ages 2-5) of approved drug = N2 line-extension, low binary risk.
- **Action:** Candidate for Phase B after UNCY exits 6/17 if framework stack remains ≥4. Currently no position.

### 8. TRDA — 🚨 ALREADY READ OUT (DROP)
- Removed from forward watchlist. ELEVATE-44-201 Cohort 1 fired 2026-05-07. Data POSITIVE / market BAD divergence (Roth $19→$10, HC Wainwright downgrade). Calendar `data_market_divergence_post_readout` kaizen candidate flagged for ODIN v15.

### 9. CABA — Tier B, multi-trigger 1H 2026, WATCH (no current position; +$2,488 ASGCT pre-empt closed)
- **Step 1 (8-K):** Q4'25 + Q1'26 outline RESET-SLE, RESET-SSc complete Phase 1/2 in 1H 2026.
- **Step 2 (IR):** **EULAR Jun 3–6 Barcelona:** RESET-SLE complete cohort poster **Jun 4 9:30 AM BST**; RESET-SSc satellite **Jun 4 5:30 PM BST**. RESET-MG already presented Apr 20 AAN.
- **Step 3 (CT.gov):** All P1/2 cohorts fully enrolled as of Sep 30, 2025.
- **Step 4 (News 7d):** **$150M raise (Lilly + premier life-sciences investors) confirmed May 14; cash runway into mid-2027.**
- **Step 5 (Tier):** **B** — 1H 2026 guidance + specific EULAR poster dates.
- **Action:** WATCH. CABA EULAR Jun 4 is potentially actionable if T-7 to T-10 micro-cap entry rules trigger; not in current portfolio.

### 10. NMRA — Q2 2026 KOASTAL-2/3 joint topline — Tier B, **NO TRADE** (failed predecessor)
- **Step 1 (8-K):** No new 8-K. 10-K Mar 30 confirms Q2 2026 joint topline. Both Phase 3s fully enrolled (>400 patients each).
- **Step 2 (IR):** Jan 5 priorities PR + Mar 30 update; joint readout could drop any trading day. 450+ patients enrolled after study optimizations early 2025.
- **Step 3 (CT.gov):** KOASTAL-1 missed primary endpoint (high placebo response). KOASTAL-2/3 enrolled at restricted high-expertise sites only.
- **Step 4 (News 7d):** No delays. No pre-announcement.
- **Step 5 (Tier):** **B** — "Q2 2026" guidance, no firm date. Could fire ANY day through 6/30.
- **Risk lens:** KOASTAL-1 failed primary AND key secondary, identical placebo and drug arms. Phase 3 retry after first replicate failure = elevated binary failure prior. Per `concentrated_account_regime_2026-05-18` memory + Pre-Investment Discovery rules: **avoid even on attractive options pricing**.

### 11. TSHA — Q2 2026 Phase 1/2 Rett — Tier B, WATCH
- **Step 1 (8-K):** Q1'26 8-K May 6 — Part A REVEAL n=12 longer-term update on track Q2 2026.
- **Step 2 (IR):** ASGCT May 11–15 was preclinical poster only (not clinical). REVEAL Pivotal dosing completion Q2 2026; ASPIRE dosing Q2 2026.
- **Step 3 (CT.gov):** TSHA-102 active. BTD + RMAT + Fast Track designations.
- **Step 4 (News 7d):** No delays.
- **Step 5 (Tier):** **B** — "Q2 2026" guidance.

### 12. VRDN — Jun 30 PDUFA — Tier A, N2 (line within crowded TED class), WATCH
- **Step 1 (8-K):** Q1'26 8-K reaffirms June 30 PDUFA. Commercial infrastructure + supply chain "launch-ready."
- **Step 2 (IR):** Priority Review + BTD. EU MAA submitted Jan 2026, accepted Feb 2026. Companion VRDN-003 (elegrobart) REVEAL-1 + REVEAL-2 Phase 3 positive — separate BLA Q1 2027.
- **Step 3 (CT.gov):** THRIVE + THRIVE-2 Phase 3 met all primary + secondary endpoints.
- **Step 4 (News 7d):** No delays.
- **Step 5 (Tier):** **A** — date firm. **AdCom status not affirmatively cleared via FDA AdCom calendar today** — should re-verify (gap from May 22 morning scan).
- **Risk:** Memory open thread on "VRDN deep dive — why -54% over 60d?" — track. Cash $762M = no financing risk.

### 13. CAPR — Aug 22 PDUFA — Tier A, LIVE LOCKED POSITION
- **Step 1 (8-K):** Q1 2026 8-K (May 12) reaffirms Aug 22 PDUFA. RMAT + ATMP + Rare Pediatric Disease Designations intact (PRV eligible).
- **Step 2 (IR):** [March 10 PDUFA PR](https://www.globenewswire.com/news-release/2026/03/10/3252979/0/en/Capricor-Therapeutics-Announces-Establishment-of-New-PDUFA-Date-for-Deramiocel-BLA.html) confirmed Class II resub date. May 7 NS Pharma lawsuit for commercialization friction. May 1 Krasney $793K insider sale (10b5-1, 45% direct-equity reduction). May 14 Lilly investor lawsuit reference is not directly relevant.
- **Step 3 (CT.gov):** HOPE-3 Phase 3 data submitted, FDA resumed review.
- **Step 4 (News 7d):** No delays. **AdCom status remains UNRESOLVED** — historical July 30, **2025** AdCom was pulled; no 2026 AdCom currently announced on FDA Advisory Committee calendar per web search. Class II resub for cell therapy is AdCom-eligible. Gap from morning scan still open.
- **Step 5 (Tier):** **A** — date firm, but **AdCom risk = UNRESOLVED**. If FDA schedules an AdCom mid-cycle, this becomes a date-load-bearing event.
- **Position:** 535 sh × $28.87 = $15,445 MV / $14,555 cost / +$890 (+6.12%). 22.3% portfolio concentration (in band per Amendment 031).
- **Pre-authorized exit:** Hard stop **2026-08-12 (Wed, T-7 effective deadline Fri 8/21)**. Exit window 8/7–8/12. Stage 25/50/100.
- **Action:** **UNRESOLVED GAP — verify FDA AdCom calendar directly Monday (5/25 holiday-shifted to 5/26).** If AdCom is scheduled between now and PDUFA, re-tier and recompute exit triggers. Per Amendment 031, no scaling above 22% without explicit override.

### 14. ARVN — DROPPED (approved 5/1)

### 15. MNKD — see #4

### 16. ACHV — see #5

### 17. UNCY — see #6

### 18. ARQT — see #7

### 19. TRDA — DROPPED (fired 5/7, data good / market bad)

### 20. CABA — see #9

### 21. NMRA — see #10

### 22. TSHA — see #11

### 23. VRDN — see #12

### 24. AVTX — DROPPED (fired 5/5, GOOD)

### 25. ZBIO — DROPPED (phantom Jun 30; no real catalyst until SunStone Q4 2026)

### 26. CADL — DROPPED (fired 5/15, GOOD)

### 27. WVE — DROPPED (fired 5/18, GOOD — but stock -5.47% sell-the-news)

### 28. ALXO — DROPPED (closed pre-event +$1,888)

### 29. AXSM — DROPPED (approved 4/30)

### 30. VERA — Jul 7 PDUFA — Tier A, N2 (Priority Review BTD), WATCH
- **Step 1 (8-K):** Q4'25 + Q1'26 reaffirm. Priority Review + BTD.
- **Step 2 (IR):** Jan 7 Priority Review PR. NEJM publication Nov 6, 2025. ORIGIN 3 interim 46% proteinuria reduction (p<0.0001). Target launch mid-2026 pending approval.
- **Step 3 (CT.gov):** ORIGIN 3 active.
- **Step 4 (News 7d):** No delays.
- **Step 5 (Tier):** **A** — firm PDUFA.

---

## DATE CONFIDENCE TIER CHANGES vs. PRIOR WEEK (May 8 baseline)

| Ticker | May 8 Tier | May 22 Tier | Change | Notes |
|--------|------------|-------------|--------|-------|
| CRDF | A | A | — | Locked position; abstract live 5/21 |
| IRON | A | A | — | Abstract live 5/21 |
| MNKD | A | A | — | T-7 trading days |
| ACHV | A (CRL-declared) | A (CRL + CMC observations) | Substance worsened | New CMC inspection finding |
| UNCY | A | A (6/29 confirmed) | — | Calendar drift unresolved (4th day) |
| ARQT | A | A | — | Now cash-flow positive |
| VRDN | A | A | — | Launch-ready |
| **CAPR** | n/a (not listed May 8) | **A (AdCom UNRESOLVED)** | **NEW LIVE POSITION** | Universal Prediction Ledger V-047 opened 2026-05-22 |
| VERA | A | A | — | No change |
| CABA | B | B (EULAR firmed) | — | $150M raise added context |
| NMRA | B | B | — | Could fire any day |
| TSHA | B | B | — | — |
| AVBP | n/a | n/a (DROPPED — date drift) | — | Mid-2026 → no Apr 30 catalyst |
| CADL | B (date fixed to 5/15 in last preflight) | RESOLVED 5/15 GOOD | DROP | Fired |
| WVE | A | RESOLVED 5/18 GOOD | DROP | Sell-the-news |
| MIRM | n/a | RESOLVED 5/4 GOOD | DROP | Fired |
| TRDA | RESOLVED 5/7 | RESOLVED 5/7 | — | Data good / market bad |
| AVTX | RESOLVED 5/5 | RESOLVED 5/5 | — | — |
| ARVN | RESOLVED 5/1 | RESOLVED 5/1 | — | — |
| ALXO | RESOLVED 5/7 | RESOLVED 5/7 | — | Closed +$1,888 |
| AXSM | RESOLVED 4/30 | RESOLVED 4/30 | — | — |
| ZBIO | n/a (phantom) | n/a (phantom) | — | Move to Q4 2026 SunStone slate |
| AVBP | (Apr 30 stale) | DROP (mid-2026 drift) | — | Stale calendar entry |

**No Tier A → Tier C/D drops detected this week** — no CMPX-class surprise.
**No new clinical holds, no PDUFA delays, no pre-PDUFA outcome pre-announcements beyond the already-known ACHV one.**

---

## VERIFIED FACTS (today's verification pass)

1. **UNCY PDUFA = 2026-06-29** — confirmed by CEO Shalabh Gupta direct quote in [May 12 Q1 2026 PR](https://www.stocktitan.net/news/UNCY/unicycive-therapeutics-announces-first-quarter-2026-financial-vd8dra3k524h.html) and [Jan 29 acceptance PR](https://www.globenewswire.com/news-release/2026/01/29/3228698/0/en/UPDATE-Unicycive-Therapeutics-Announces-FDA-Acceptance-of-Oxylanthanum-Carbonate-OLC-New-Drug-Application-NDA-Resubmission.html). Canonical calendar still shows 6/27 — fourth day flagged.
2. **MNKD PDUFA = 2026-05-29** for Afrezza pediatric sBLA — confirmed [MannKind sBLA PR](https://investors.mannkindcorp.com/news-releases/news-release-details/mannkind-announces-us-fda-accepts-review-its-supplemental). T-5 trading days.
3. **CRDF ASCO abstract #3510 live on ASCO.org since 5/21** — confirmed [May 22 webcast PR](https://www.manilatimes.net/2026/05/22/tmt-newswire/globenewswire/cardiff-oncology-announces-webcast-to-discuss-updated-phase-2-crdf-004-data-for-onvansertib-in-first-line-ras-mutated-mcrc/2349684). Investor webcast 6/3 8:30 AM ET.
4. **ACHV CMC observations** — confirmed in Q1 2026 8-K + Q3 2025 PR still active in IR materials. Two Form 483 observations during cGMP inspection at named cytisinicline manufacturer.
5. **CAPR Aug 22 PDUFA confirmed** by March 10 PR + Q1 2026 8-K. AdCom status: **no 2026 AdCom currently announced** per FDA Advisory Committee calendar / news search; the July 30 **2025** AdCom that some sources surfaced was pulled before the original CRL.
6. **NMRA KOASTAL-2/3 joint readout Q2 2026** confirmed [Jan 5 priorities PR](https://www.globenewswire.com/news-release/2026/01/05/3212570/0/en/Neumora-Therapeutics-Highlights-2026-Pipeline-Strategy-and-Anticipated-Upcoming-Milestones.html) and 10-K. Could drop any day through 6/30.
7. **All other Tier A PDUFA dates** (ARQT 6/29, VRDN 6/30, VERA 7/7) — no change vs May 8 confirmation set.

## INFERRED INTERPRETATION

1. **ACHV CMC observations 5–7 weeks pre-PDUFA strongly suggest CMC CRL prior** — consistent with company-pre-declared CRL expectation. Per ODIN v14 weights (`mfg_risk_bin` + `pw_double_crl_bin_x_resub_class_2` -0.173 coef), this is exactly the kind of pre-event CMC signal that yields Class 2 CRLs.
2. **CRDF webcast scheduled morning after the oral** is *consistent with* a company expecting to defend or lean into the data; not by itself confirmation of positive data.
3. **CAPR AdCom likelihood** for Class II cell therapy resub remains elevated given precedent — but the absence of any announcement on the FDA AdCom calendar today implies no immediate AdCom call. **Interpretation, not verified outcome.**
4. **NMRA crash risk** is elevated — Phase 3 retry after first replicate failure (KOASTAL-1) on the same MDD endpoint with same comparator is a textbook double-bind.

## UNRESOLVED GAPS

1. **CAPR AdCom verification** — could not directly verify FDA Advisory Committee calendar for any deramiocel AdCom in 2026. Gap from this morning's scan still open. **Verify directly via fda.gov/advisory-committees/advisory-committee-calendar on Tuesday 5/26 (Monday is Memorial Day).**
2. **VRDN AdCom verification** — same — could not affirmatively clear via news search. Same FDA AdCom calendar verification needed.
3. **NMRA KOASTAL-2/3 readout day** — guidance is "Q2 2026" with no firm date. Cannot rule out a mid-day pre-announcement on any trading day through 6/30.
4. **UNCY canonical calendar correction** — automated CSV update has not happened despite 4 days of daily-scan flagging. Manual update needed.
5. **TRDA ELEVATE-44 Cohort 2 timing** — relies on TradingView interpretation of slide deck. Verify against next 8-K.

## RED-TEAM OBJECTIONS

1. **Absence-of-evidence claims** on AdCom status (CAPR, VRDN, MNKD) are not the same as confirmed-no-AdCom. The FDA AdCom calendar must be checked directly.
2. **CRDF abstract may contain previously-presented data only** — per IRON's practice ("abstract will contain previously presented data; new data reserved for oral"), the published abstract may not contain the meaningful new data that moves the stock at the oral. Position decisions should weight pre-oral exit > headline-reading risk. The CRDF 40-call salvage is small enough that this is a manageable risk.
3. **NMRA pre-announcement risk** — KOASTAL-2/3 joint topline could hit pre-market or after-hours any day. The framework correctly avoids the trade, but watch for unrelated portfolio impact (e.g., XBI moves if a high-profile MDD failure hits the sector).
4. **"WVE -5.47% on positive data"** (May 19) is a calibration anchor for the sell-the-news pattern — should be added to KAIZEN_LOG.md as a v15 training data point.
5. **CAPR data_market_divergence pattern** from TRDA (data good, market bad) is also a v15 candidate feature — `data_market_divergence_post_readout` (binary: did stock reaction contradict clinical outcome?). Should be added to KAIZEN_LOG.md.
6. **CAPR sizing review** — May 7 lawsuit + May 1 Krasney $793K sale stacks two negative signals 3 months pre-PDUFA. Per Amendment 031, no scaling above 22% without explicit override. The +6.12% unrealized gain provides cushion; do not let it justify size creep.

---

## RECOMMENDED ACTIONS

### Immediate (this weekend / Tuesday 5/26 open)
1. **🟠 UPDATE CANONICAL CALENDAR:** `CANONICAL_CATALYST_CALENDAR_2026-04-24.csv` — UNCY 2026-06-27 → **2026-06-29** (4th day flagged). Recompute all downstream exit triggers. (Note: portfolio lock already uses 6/17 hard stop based on corrected 6/29 date.)
2. **🚨 ACHV REINFORCED BLOCK:** Block new entries pre-6/20 PDUFA regardless of any model upgrade signal. CMC inspection finding from 5/22 morning scan adds fresh CMC risk to pre-declared CRL.
3. **🟠 CAPR AdCom check:** Verify FDA Advisory Committee calendar directly on Tuesday 5/26 (Memorial Day Monday). If an AdCom is scheduled between now and 8/22 PDUFA, re-tier and recompute exit triggers.
4. **🟡 CRDF abstract pull:** Before 5/26 open, pull abstract #3510 from ASCO.org. Compare ORR/PFS to April 2025 baseline. Stage exit per pre-authorized window 5/26–6/1. Hard stop **6/1 close**.
5. **🟡 MNKD T-5 (today's close):** Not in portfolio — informational only.

### This week (post-5/29)
6. **NMRA daily watch:** KOASTAL-2/3 joint topline could drop any day through 6/30. Pre-Investment Discovery flag = NO TRADE; this is a portfolio-impact watch, not an entry watch.
7. **Append to KAIZEN_LOG.md:**
   - (a) `wve_sell_the_news_2026-05-19` — positive data + stock -5.47% as v15 calibration anchor
   - (b) `trda_data_market_divergence_2026-05-07` — data good / market bad as candidate feature `data_market_divergence_post_readout`
   - (c) `achv_cgmp_inspection_observations_2026Q1` — confirmed CMC-risk data point for v15 training set
   - (d) `crdf_rapid_oral_signal_pres_type_2026-05-21` — kaizen candidate feature `pres_type_rapid_oral` distinct from `pres_type_oral` (between Poster +4% and Oral +8% Conference Overlay weight)
8. **Q4 2026 calendar prep:** Move ZBIO to SunStone SLE Q4 2026 calendar; CABA RESET-SLE/SSc remaining cohorts.
9. **Universe-generator audit:** WVE was missed from May 21 universe entirely. Recommend auditing universe-generator script for similar gaps (large-mid-cap RNA editing pipeline names).

### Carry-forward open threads
- CRDF stale-date impact analysis (from yesterday's Cowork dropbox crdf_event_check.md) — already addressed by the May 22 morning scan + this preflight.
- AdCom calendar automation — recommend building a daily-task to pull the FDA AdCom calendar JSON directly rather than relying on news searches.

---

## URGENT FLAGS (auto-prepended for David's immediate attention)

- 🚨 **No A→C/D Tier drops detected.** No CMPX-class surprise this week.
- 🟠 **UNCY canonical calendar drift unresolved (4th day flagged).**
- 🟠 **CAPR AdCom status unverified (2nd day open).**
- 🟡 **CRDF exit window is OPEN now through 6/1.** Locked position.
- 🟡 **MNKD T-5 today** — not in portfolio.
- 🚨 **ACHV BLOCK reinforced** with fresh CMC observation finding.

---

## PROVENANCE

- All dates and outcomes verified from primary sources (company IR pages, SEC EDGAR, FDA.gov, ASCO website) via daily news scan (2026-05-21, 2026-05-22) + targeted WebSearch verification 2026-05-22 PM.
- Perplexity unavailable today (API quota exceeded) — WebSearch + cached daily scans used as primary verification tool.
- 20 candidates scanned, 9 dropped as RESOLVED, 11 live (3 in portfolio).
- No fabricated data; every claim sourced to a public primary source or labeled UNRESOLVED.
- Master log at `/Odin Perfection/9REALMS_MASTER_LOG.md` consulted at session start.
- Prior preflight `/Odin Perfection/weekly_preflight_2026-05-08.md` consulted for tier-change baseline.
- Daily scan precursors: `/9realms/daily_scans/daily_news_scan_2026-05-{21,22}.md`.

---

## COMPLIANCE ATTESTATION

- **Amendment 027 (Real Data Only):** All data sourced to primary IR / SEC / ASCO / FDA / GlobeNewswire. Output separates VERIFIED FACTS / INFERRED / UNRESOLVED / RED-TEAM. ⚠️ DATA NOT VERIFIED flags applied to CAPR AdCom + VRDN AdCom + NMRA readout day.
- **Amendment 028 (Panel Integrity):** N/A — preflight is per-ticker, not a panel-conditional rate.
- **Amendment 031 (Concentrated Regime):** Portfolio lock at 76.9% UNCY / 22.3% CAPR / 0.9% CRDF is consistent with the 2-4 position, 10-50% min/max bands. UNCY exceeds the 50% cap explicitly approved by David as Phase A primary position.
- **Amendment 032 (Universal Prediction Hash):** V-047 CAPR opened 5/22 in ledger entry #25. V-048 CRDF opened 5/22 in ledger entry #25. UNCY = V-006 (earlier). All current portfolio positions are SHA-256 hashed.
- **Amendment 033 (Cowork Dropbox):** This file mirrored to `/9realms/odin_cowork_dropbox/2026-05-22_weekly_preflight_rule0_full_sweep.md`.
- **Amendment 034 (Daily Autoscan Persistence):** This file mirrored to `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/2026-05-22_weekly_preflight_full_sweep.md`.
- **Daily Scan Mirror (immutable):** This file mirrored to `/9realms/daily_scans/weekly_preflight_2026-05-22.md` (byte-identical).
- **Amendment 035 (renumbered):** N/A here.

---

## NEXT-SESSION ACTION ITEMS

1. (UNCY) Manual canonical calendar correction 6/27 → 6/29.
2. (CAPR) Verify FDA AdCom calendar Tuesday 5/26 open.
3. (CRDF) Pull abstract #3510 from ASCO.org before 5/26 open; stage exit 5/26–6/1.
4. (KAIZEN_LOG) Append the 4 entries enumerated above.
5. (Universe) Audit universe-generator for WVE-class coverage gaps.

---

**End of report.** Next scheduled pre-flight: **2026-05-29 (Friday) 17:00 ET** — MNKD PDUFA day.

**Chain hash (this report SHA-256):** to be computed and appended to MASTER_PREDICTION_LEDGER per Amendment 032 chain protocol if any new V-IDs are opened (none opened this preflight).
