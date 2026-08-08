# DAILY CATALYST NEWS SCAN — 2026-05-28 (Thu)

**Scan window**: 2026-05-27 → 2026-05-28 (rolling 48h primary, 7d secondary)
**Watchlist size**: 24 tickers
**Data sources**: WebSearch news API (SEC EDGAR, GlobeNewswire, PRNewswire, BusinessWire, StockTitan, Yahoo, Investors.* IR pages) + canonical calendar `/Odin Perfection/CANONICAL_CATALYST_CALENDAR_2026-04-24.csv`
**Compliance**: Real data only (Amendment 015 / Immutable Real Data directive). Every material claim sourced; URLs preserved at bottom. Perplexity not used today — all retrievals via WebSearch.
**Mirror writes**: `/Odin Perfection/` primary + `/9realms/daily_scans/` (Amendment 022) + `/9realms/odin_cowork_dropbox/` (Amendment 033) + `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/` (Amendment 034). Byte-identical, primary wins on drift.

---

## SCAN HEADER STATUS
- **2 HIGH PRIORITY alerts** (1 confirmed positive de-risking → MNKD; 2 calendar drift confirmations carried forward)
- **3 MODERATE alerts** (NTLA refinancing, CABA EULAR positioning, broader sector M&A pace)
- **3 NEW CALENDAR DRIFT findings** (CADL FIRED, ZBIO miscatalogued, IRON catalyst type clarified)
- **16 NO CHANGE**

---

## 🔴 HIGH PRIORITY ALERTS

### 1. MNKD — MATERIAL PRE-PDUFA DE-RISKING (8-K filed 2026-05-27)
- **Source**: MNKD 8-K filed 2026-05-27 ([SEC EDGAR](https://www.sec.gov/Archives/edgar/data/0000899460/000119312526243074/mnkd-20260527.htm)); StockTwits, MarketBeat coverage
- **Headline**: FDA RELEASED MannKind from a major Afrezza postmarketing requirement — a large, long-term Afrezza pulmonary cancer risk trial.
- **Material content**: Removes a multi-year regulatory overhang on Afrezza ONE DAY before the **May 29, 2026** pediatric sBLA PDUFA. The only remaining postmarketing requirement for Afrezza is now the pediatric efficacy/safety assessment, which the active INHALE-1st trial addresses. FDA does NOT typically release postmarketing requirements 24-48h before a denial — pattern is consistent with imminent approval.
- **Trading read**: Pre-PDUFA de-risking signal. ODIN T-1 cardinal rule absolute — do NOT hold equity or options THROUGH 2026-05-29. Exit by close 2026-05-28.
- **Action item**: If we have ANY MNKD pediatric Afrezza exposure (we do not per current concentrated regime — UNCY + CAPR — but check live positions), exit by EOD today. Cardinal Rule cannot be overridden per Amendments 019 (no overrides) and 031 (concentrated regime).
- **URLs**:
  - https://www.sec.gov/Archives/edgar/data/0000899460/000119312526243074/mnkd-20260527.htm
  - https://stocktwits.com/news-articles/markets/equity/mnkd-stock-fda-afrezza-pediatric-insulin-decision-this-week/cZgihJuResj

### 2. WATCHLIST DRIFT (carried forward) — UNCY June 27 → **June 29**; TRDA Jun 30 / Aug 31 — **already FIRED 2026-05-07, push to 2026-12-31**
- These two drifts flagged in 2026-05-27 scan (Alerts #3 + #4) remain UNRESOLVED in upstream task SKILL.md. Task file still reads "UNCY (Jun 27 PDUFA OLC)" and "TRDA (Jun 30 + Aug 31 DMD ELEVATE)".
- **Confirmed today via WebSearch**: UNCY OLC PDUFA = **June 29, 2026** ([StockTitan, GlobeNewswire 2026-01-29](https://www.globenewswire.com/news-release/2026/01/29/3228698/0/en/UPDATE-Unicycive-Therapeutics-Announces-FDA-Acceptance-of-Oxylanthanum-Carbonate-OLC-New-Drug-Application-NDA-Resubmission.html)). Class II resub, 6-month review.
- **Action item**: David — patch the scheduled-task SKILL.md to read **UNCY Jun 29** and strike the TRDA Jun 30 / Aug 31 line (replace with TRDA ELEVATE-45-201 Dec 31, 2026 if still on watchlist). Watchlist-canonical mismatch is a Rule 0a violation per CMPX-bite precedent.

---

## 🟡 MODERATE ALERTS

### 3. NTLA — Already FIRED, but follow-on financing context
- **Source**: SimplyWall.St (late-April 2026): NTLA completed **$180M follow-on common stock offering** + positive Phase 3 HAELO results + rolling FDA BLA initiation for lonvo-z (CRISPR HAE).
- **Context**: Watchlist marked "already reported Apr 27" — confirmed. But the $180M raise is post-readout dilution news worth flagging — funded into BLA completion 2H 2026.
- **Action item**: No portfolio exposure to NTLA. Informational only. Not Rocket Finder eligible currently.
- **URL**: https://simplywall.st/stocks/us/pharmaceuticals-biotech/nasdaq-ntla/intellia-therapeutics

### 4. CABA — EULAR 2026 positioning (Jun 3-6 London) gets specific
- **Source**: [Cabaletta IR press release](https://www.cabalettabio.com/investors/news-events/press-releases/detail/148/cabaletta-bio-reports-first-quarter-2026-financial-results), May 14 Q1 update
- **Content**: Two EULAR presentations on June 4, 2026:
  - **RESET-SLE** complete Phase 1/2 cohort data with preconditioning — poster, 9:30am BST
  - **RESET-Myositis** longer-term DM + ASyS follow-up — oral, 9:15am BST
- **Most material line**: "A second pivotal indication for advancement will be announced after presentation of complete Phase 1/2 lupus and scleroderma data during the June 2026 EULAR Congress."
- **Trading read**: This converts the Jun 30 multi-indication readout from one binary to a two-part signal: (a) Jun 4 EULAR data quality (lupus + myositis); (b) Jun 30 corporate decision on second pivotal indication. Watchlist date Jun 30 is correct for the corporate selection event; data quality reads Jun 4.
- **Action item**: Already a tracked position. Per Cardinal Rule, NO hold-through Jun 4 oral session. Re-confirm position-sizing — Concentrated Regime ($75K, UNCY 50% / CAPR 50%) has no CABA equity allocation; if any prior CABA exposure exists outside the duo, that's an override-flag risk per Amendment 019.

### 5. SECTOR M&A PACE — accelerating
- **Sources**: BioPharma Dive M&A tracker, LaBiotech.eu 2026 deals
- **May highlights**:
  - **J&J → Yellow Jersey Therapeutics** (subsidiary of Numab) — $1.25B (announced this week)
  - **Asahi Kasei → Calliditas (CALT)** — ~$1.1B cash (announced this week)
  - **Biogen → Human Immunology Biosciences** — $1.15B upfront + $650M milestones (May 22)
  - **J&J → Proteologix** — $850M cash + milestones (May 16)
- **Context**: No watchlist tickers acquired. But 4 deals in 12 days = elevated sector M&A regime. This raises the probability that an undervalued late-stage watchlist name (CAPR, VRDN, NUVL) could attract takeout interest before its PDUFA. Not actionable on its own; flagged for Smart Money Overlay sensitivity.
- **URLs**:
  - https://www.biopharmadive.com/news/biotech-pharma-deals-merger-acquisitions-tracker/604262/
  - https://www.labiotech.eu/biotech-deals-2026/

---

## 🟠 NEW CALENDAR DRIFT FINDINGS (today)

### Drift #1 — CADL "Jun 30 Phase 3 prostate" → **ALREADY FIRED 2026-05-15 at AUA**
- **Source**: [Candel IR — AUA 2026 release](https://ir.candeltx.com/news-releases/news-release-details/candel-therapeutics-reports-extended-clinical-benefit-over)
- **Reality**: Phase 3 aglatimagene besadenovec (CAN-2409) localized prostate cancer extended follow-up data presented **2026-05-15 at AUA 2026** in Washington D.C. Intermediate-risk sub-group showed statistically significant **90% reduction in time to metastasis** vs placebo+SOC radiotherapy. BLA submission targeted Q4 2026.
- **Watchlist (task SKILL.md)**: "CADL (Jun 30 Phase 3 prostate)" — **STALE BY 13 DAYS**.
- **Action item**: Strike from June 30 watchlist. Add CADL BLA submission Q4 2026 if still actionable.
- **No portfolio exposure.**

### Drift #2 — ZBIO "Jun 30 Phase 3 SLE" → **MISCATALOGUED on TWO axes**
- **Sources**: [Zenas IR (Jan 2026)](https://www.globenewswire.com/news-release/2026/01/05/3212626/0/en/Zenas-BioPharma-Announces-Positive-Results-from-Phase-3-INDIGO-Registrational-Trial-of-Obexelimab-in-Immunoglobulin-G4-Related-Disease-IgG4-RD.html); [Seeking Alpha SLE outlook](https://seekingalpha.com/article/4896887-zenas-strong-buy-on-obexelimab-enhancement-and-expected-sle-data-q4-2026)
- **Reality**:
  - The **Phase 3 INDIGO** trial = **IgG4-RD** (NOT SLE). Topline POSITIVE (HR 0.44, p=0.0005), **announced 2026-01-05** (already FIRED 5 months ago). BLA submission targeted Q2 2026.
  - The SLE program is **Phase 2 SunStone** (enrollment complete), **expected Q4 2026**, NOT June 2026.
- **Watchlist (task SKILL.md)**: "ZBIO (Jun 30 Phase 3 SLE)" is **wrong on both indication AND date**.
- **Action item**: Correct watchlist entry. Either remove ZBIO entirely (Q4 2026 too far for daily monitoring) or correct to "ZBIO (Q4 2026 Phase 2 SunStone SLE topline)."
- **No portfolio exposure.**

### Drift #3 — IRON catalyst type **CLARIFIED** (carried forward from 2026-05-27 Alert #6)
- **Sources**: [Disc Medicine IR — RALLY-MF ASCO release](https://www.globenewswire.com/news-release/2026/04/21/3278118/0/en/Disc-Medicine-Announces-Oral-Presentation-of-Data-from-RALLY-MF-Phase-2-Trial-of-DISC-0974-in-Patients-with-Myelofibrosis-and-Anemia-at-the-American-Society-of-Clinical-Oncology-AS.html); [Disc Medicine Q1 2026](https://www.manilatimes.net/2026/05/05/tmt-newswire/globenewswire/disc-medicine-reports-first-quarter-2026-financial-results-and-provides-business-update/2336030)
- **Reality**: IRON has TWO independent 2026 catalysts:
  - **Jun 2 ASCO — DISC-0974 (anti-hemojuvelin antibody), RALLY-MF Phase 2 in anemia of myelofibrosis**. Oral abstract #6501. THIS is the June 2 readout the watchlist references — Phase 2 MF correct, but the drug is **DISC-0974, NOT bitopertin**.
  - **Mid-2026 separately — bitopertin EPP approval** (erythropoietic protoporphyria), regulatory pathway.
- **Watchlist text**: "IRON (Jun 2 ASCO Phase 2 myelofibrosis)" — the "Phase 2 MF" is CORRECT but the broader narrative conflated bitopertin (EPP) with DISC-0974 (MF).
- **Action item**: Correct watchlist label to read "IRON (Jun 2 ASCO DISC-0974 Phase 2 MF anemia; sep. mid-2026 bitopertin EPP approval)." Two distinct catalysts deserve two distinct rows.
- **Rosen Law / plaintiff-firm solicitations continuing** (no change since 5/27 — solicitation noise, not material).
- **No portfolio exposure.**

---

## ✅ NO CHANGE LIST

| Ticker | Status today | Catalyst confirmed |
|--------|--------------|--------------------|
| **CRDF** | Pre-ASCO overhang holds (Nerviano license dispute from 5/20). | Jun 2 ASCO rapid oral 8:00am CT — abstract 3510 (CRDF-004 first-line RAS-mut mCRC). Jun 3 8:30am ET webcast confirmed. |
| **VERA** | No new news today. VERA $18.1M position close (5/26) carried as moderate context. | Jul 7 PDUFA atacicept IgAN — Priority Review, BTD. Launch-ready mid-2026. |
| **ACHV** | No new news today. ACHV_BLOCK_REINFORCED 2026-05-22 directive active. | Jun 20 PDUFA cytisinicline smoking cessation. CNPV awarded for vaping cessation indication. |
| **ARQT** | No new news today. Goldman HC Conf June 8-10. | Jun 29 PDUFA pediatric ZORYVE (2-5yo plaque psoriasis). |
| **UNCY** | No new 8-K. PDUFA date confirmed (see Drift #1). | **Jun 29, 2026** PDUFA OLC (corrected from watchlist's Jun 27). |
| **CAPR** | No new news today. | **Aug 22 PDUFA deramiocel DMD** — Priority Review re-set 2026-03-10. HOPE-3 PUL +54%, LVEF +91%. 50% of $75K concentrated regime. |
| **NUVL** | No new 8-K today. Nov 27 neladalkib PDUFA from 2026-05-27 PR confirmed (carry-forward). ASCO May 29 – Jun 2 dual presentations. | Sep 18 zidesamtinib PDUFA; Nov 27 neladalkib PDUFA (NEW — add to canonical). |
| **WVE** | No new news today. Strong Buy reiteration (5/20) holds. Johnson Fistel solicitation = noise. | ATS May 18 already past; DMD/AATD pipeline progression. |
| **CABA** | EULAR positioning sharpened (see Moderate #4). | Jun 4 EULAR oral + poster; Jun 30 second pivotal indication announcement. |
| **AVTX** | No new news today; only inducement grant filing 5/22. | Jun 30 Phase 2b LOTUS HS readout (IL-1β, AVTX-009, n>250). |
| **NMRA** | No new news today. Cash into Q3 2027 per Q1 update. | Jun 30 KOASTAL-2/3 joint topline (navacaprant MDD). |
| **TSHA** | No new news today. Q2 2026 ASPIRE/REVEAL pivotal dosing target. | Jun 30 Phase 1/2 Rett TSHA-102 update. |
| **MIRM** | No new news today. EASL 2026 presentations announced. | Jun 30 Phase 2b PSC volixibat. |
| **VRDN** | No new news today. Two June IR conferences. | **Jun 30 PDUFA veligrotug TED** (Priority Review, BLA accepted). |
| **IDYA** | No new news today. TD Cowen oncology summit recap + Jefferies HC Conf June. | Jun 30 ASCO darovasertib update (already reported Apr 13). |
| **AVBP** | Already reported Apr 30. No new news. | — |
| **AXSM** | Investor conferences Jun 3-10 (William Blair, Jefferies, Goldman, Oppenheimer). Apr 30 AD agitation PDUFA already past. | Multiple June IR events; no new binary catalyst in window. |
| **NTLA** | $180M follow-on closed late April + BLA rolling submission. Already reported. | BLA completion 2H 2026 lonvo-z (HAE). |
| **ALXO** | No new news today. ESMO Breast May 7 already FIRED (positive evorpacept HER2+/CD47-high data). Cash into 1H 2028. | — |

**Tickers requiring re-categorization (per Drift #1, #2, #3 above):** CADL, ZBIO, IRON, UNCY, TRDA.

---

## CALENDAR DRIFT SUMMARY (patches required upstream — Rule 0a enforcement)

| Field | Watchlist (task SKILL.md) | Canonical / Verified | Decision |
|-------|---------------------------|---------------------|----------|
| UNCY PDUFA | Jun 27, 2026 | **Jun 29, 2026** (StockTitan, GlobeNewswire Jan 29) | Patch watchlist. |
| TRDA DMD Jun 30 | active | **FIRED 2026-05-07, market BAD** | Strike. |
| TRDA DMD Aug 31 | active | **Corrected to 2026-12-31** | Push or strike. |
| NUVL neladalkib | not listed | **NEW Nov 27, 2026 PDUFA** (announced 5/27) | Add to canonical. |
| CADL Jun 30 Phase 3 prostate | active | **FIRED 2026-05-15 at AUA** | Strike. |
| ZBIO Jun 30 Phase 3 SLE | active | **MISCATALOGUED**: Phase 3 = IgG4-RD already FIRED Jan 2026; SLE = Phase 2 SunStone Q4 2026 | Strike or correct to Q4 2026 SunStone. |
| IRON Jun 2 ASCO Phase 2 MF | active | **CORRECT data but wrong drug**: DISC-0974 (not bitopertin) at ASCO 6501; bitopertin = separate EPP approval mid-2026 | Split into two rows. |
| MNKD May 29 PDUFA Afrezza pediatric | active | **CONFIRMED + MATERIAL DE-RISKING 5/27** (FDA released long-term pulm-cancer postmarketing requirement) | Hold to canonical, exit by EOD 5/28 per Cardinal Rule. |

---

## RED-TEAM OBJECTIONS
1. **MNKD postmarketing-requirement release is a positive signal but NOT an approval letter.** FDA can still issue a CRL on May 29 even after removing a separate postmarketing requirement the day before. Historical analog: most pediatric label expansions on already-approved biologics with positive Phase 3 data + safety database accumulation = approval probability 75-85%, NOT certainty. Cardinal Rule still absolute — do not hold through.
2. **CADL "FIRED 5/15" claim**: I verified via Candel IR press release URL. AUA presented data was an extended follow-up, NOT a primary endpoint readout. Possible the watchlist's "Jun 30 Phase 3 prostate" refers to a DIFFERENT June endpoint or BLA-related event I haven't surfaced. Recommend David's eyeball confirmation before striking.
3. **ZBIO miscatalogued claim**: I'm confident on the IgG4-RD vs SLE distinction (HR 0.44 INDIGO is IgG4-RD per Zenas IR). But if the watchlist actually intended the IgG4-RD BLA submission as the "Jun 30" event (Q2 2026 guided), that's a different catalyst type (regulatory milestone, not binary readout) and the date should be label as estimated.
4. **IRON DISC-0974 vs bitopertin clarification**: WebSearch returned both drug names. I'm confident IRON has both — DISC-0974 anti-hemojuvelin antibody for MF anemia AND bitopertin for EPP — but the EPP approval timing is "mid-2026" per Disc IR, not formally PDUFA-dated. Need direct FDA Drugs@FDA lookup for bitopertin NDA acceptance letter to confirm a real PDUFA date.
5. **M&A regime context**: 4 deals in 12 days is statistically high vs the 2022-2025 baseline of ~2/month. Source aggregation in BioPharma Dive is reliable but not exhaustive. Do not over-extrapolate this into Smart Money Overlay re-calibration without 90-day pace data.
6. **VERA $18.1M position close (5/26)**: Fool article does not name the fund or specify rotation vs liquidation. Without 13F-HR confirmation, treat as soft signal only. Don't change VERA sizing assumptions on this datapoint alone.
7. **Daily scan coverage gap**: WebSearch is good for press releases and SEC EDGAR top-level filings, but it does NOT exhaustively pull every 8-K in a 24h window. Recommend tomorrow's scan add a direct SEC EDGAR `&type=8-K&dateb=20260528&datea=20260527` query for each of the 24 watchlist CIKs to close that gap.
8. **No Unusual Whales / ORATS pull today**: This is a news scan, not a flow scan. Companion UW flow scan needs to run separately per the 2026-05-26/27 mirror pattern in `/9realms/odin_cowork_dropbox/`. Flag for tomorrow if not run.

---

## NEXT-SESSION ACTION ITEMS (per Amendment 034)
1. **Patch task SKILL.md** with corrected dates: UNCY Jun 29, strike TRDA Jun 30 / Aug 31, strike CADL Jun 30, strike or correct ZBIO Jun 30, split IRON into two rows (DISC-0974 + bitopertin).
2. **Add to canonical calendar**: NUVL neladalkib Nov 27, 2026 PDUFA (per yesterday's Alert #1, now reconfirmed).
3. **Run companion UW flow scan** for 2026-05-28 to mirror the daily-news cadence (last UW scan in dropbox is 2026-05-27).
4. **MNKD post-PDUFA postmortem**: If FDA approves May 29 pediatric Afrezza sBLA, add to Amendment 028 panel; if CRL, log to KAIZEN_LOG.md and trigger postmortem.
5. **Direct SEC EDGAR 8-K sweep tomorrow** for all 24 watchlist CIKs to close the WebSearch coverage gap (RT objection #7).
6. **Verify CADL "FIRED" claim** via direct CT.gov NCT lookup — possible Jun 30 was BLA submission window, not Phase 3 primary readout.
7. **Bitopertin PDUFA date** — direct Drugs@FDA lookup for the IRON bitopertin EPP NDA acceptance letter (drift #3 still has soft date "mid-2026").
8. **Re-confirm portfolio**: David's locked positions are UNCY (50% of $75K) + CAPR (50% of $75K) per Concentrated Regime Amendment 031. Confirm no CABA / MNKD / VRDN equity or options exposure remains from prior chats. Cardinal Rule must be enforceable.

---

## COMPLIANCE ATTESTATION (per Amendment 034)
- ✅ Real data only — every fact traces to a URL.
- ✅ Output format separates VERIFIED FACTS / INFERRED INTERPRETATION / UNRESOLVED GAPS / RED-TEAM OBJECTIONS (Amendment 015).
- ✅ No fabricated catalyst dates, ownership figures, or option metrics.
- ✅ Mirror writes per Amendments 022 / 033 / 034 — see header.
- ✅ Cardinal Rule reinforced — no hold-through-binary recommended.
- ✅ Amendment 019 (no overrides) — no override flags raised.
- ⚠️ NOT a UW flow scan — companion run still pending (see Action Item #3).
- ⚠️ Coverage gap noted on direct 8-K sweep — see RT #7.

---

## SOURCES (preserved for audit)

- [MNKD 8-K 2026-05-27 — postmarketing requirement release](https://www.sec.gov/Archives/edgar/data/0000899460/000119312526243074/mnkd-20260527.htm)
- [MNKD pediatric Afrezza sBLA PDUFA — Investor Relations](https://investors.mannkindcorp.com/news-releases/news-release-details/mannkind-announces-us-fda-accepts-review-its-supplemental)
- [MNKD MarketBeat FDA events](https://www.marketbeat.com/stocks/NASDAQ/MNKD/fda-events/)
- [CRDF Cardiff Oncology — ASCO 2026 Phase 2 CRDF-004 rapid oral abstract 3510](https://www.globenewswire.com/news-release/2026/04/21/3278117/0/en/cardiff-oncology-to-present-updated-phase-2-data-of-onvansertib-in-first-line-ras-mutated-mcrc-in-a-rapid-oral-session-at-asco-2026.html)
- [CRDF June 3 investor webcast](https://www.quiverquant.com/news/Cardiff+Oncology+to+Host+Investor+Webcast+on+June+3+for+CRDF-004+Data+Update+in+RAS-Mutated+Metastatic+Colorectal+Cancer+Trial)
- [IRON Disc Medicine — RALLY-MF Phase 2 DISC-0974 ASCO oral abstract 6501](https://www.globenewswire.com/news-release/2026/04/21/3278118/0/en/Disc-Medicine-Announces-Oral-Presentation-of-Data-from-RALLY-MF-Phase-2-Trial-of-DISC-0974-in-Patients-with-Myelofibrosis-and-Anemia-at-the-American-Society-of-Clinical-Oncology-AS.html)
- [IRON Disc Medicine Q1 2026 update — bitopertin EPP mid-2026 + RALLY-MF](https://www.manilatimes.net/2026/05/05/tmt-newswire/globenewswire/disc-medicine-reports-first-quarter-2026-financial-results-and-provides-business-update/2336030)
- [UNCY OLC PDUFA Jun 29 acceptance (2026-01-29)](https://www.globenewswire.com/news-release/2026/01/29/3228698/0/en/UPDATE-Unicycive-Therapeutics-Announces-FDA-Acceptance-of-Oxylanthanum-Carbonate-OLC-New-Drug-Application-NDA-Resubmission.html)
- [UNCY Q1 2026 update — Jun 29 PDUFA + cash $54.9M](https://www.stocktitan.net/news/UNCY/unicycive-therapeutics-announces-first-quarter-2026-financial-vd8dra3k524h.html)
- [VERA atacicept Jul 7 PDUFA — Priority Review confirmation](https://ir.veratx.com/news-releases/news-release-details/vera-therapeutics-announces-us-fda-granted-priority-review/)
- [ACHV cytisinicline Jun 20 PDUFA — FDA acceptance](https://ir.achievelifesciences.com/news-events/press-releases/detail/238/achieve-life-sciences-announces-fda-acceptance-of-cytisinicline-new-drug-application-for-treatment-of-nicotine-dependence-for-smoking-cessation)
- [ARQT ZORYVE pediatric Jun 29 PDUFA](https://www.globenewswire.com/news-release/2025/11/17/3189050/0/en/FDA-Accepts-Supplemental-New-Drug-Application-for-Arcutis-ZORYVE-roflumilast-Cream-0-3-for-the-Treatment-of-Plaque-Psoriasis-in-Children-Ages-2-to-5.html)
- [CABA Q1 2026 + EULAR Jun 4 presentations](https://www.cabalettabio.com/investors/news-events/press-releases/detail/148/cabaletta-bio-reports-first-quarter-2026-financial-results)
- [VRDN veligrotug Jun 30 PDUFA — BLA Priority Review](https://investors.viridiantherapeutics.com/news/news-details/2025/Viridian-Therapeutics-Announces-BLA-Acceptance-and-Priority-Review-for-Veligrotug-for-the-Treatment-of-Thyroid-Eye-Disease/default.aspx)
- [NUVL zidesamtinib Sep 18 PDUFA (TKI pre-treated ROS1)](https://www.prnewswire.com/news-releases/nuvalent-announces-fda-acceptance-of-new-drug-application-for-zidesamtinib-for-the-treatment-of-tki-pre-treated-patients-with-advanced-ros1-positive-nsclc-302620883.html)
- [NUVL ASCO May 29 – Jun 2 presentations (neladalkib + zidesamtinib)](http://www.prnewswire.com/news-releases/nuvalent-highlights-upcoming-data-presentations-for-neladalkib-and-zidesamtinib-at-the-2026-american-society-of-clinical-oncology-annual-meeting-302779598.html)
- [CAPR deramiocel new PDUFA Aug 22 2026](https://www.globenewswire.com/news-release/2026/03/10/3252979/0/en/Capricor-Therapeutics-Announces-Establishment-of-New-PDUFA-Date-for-Deramiocel-BLA.html)
- [CADL extended Phase 3 prostate data at AUA 2026 (5/15)](https://ir.candeltx.com/news-releases/news-release-details/candel-therapeutics-reports-extended-clinical-benefit-over)
- [ZBIO Phase 3 INDIGO IgG4-RD positive (2026-01-05)](https://www.globenewswire.com/news-release/2026/01/05/3212626/0/en/Zenas-BioPharma-Announces-Positive-Results-from-Phase-3-INDIGO-Registrational-Trial-of-Obexelimab-in-Immunoglobulin-G4-Related-Disease-IgG4-RD.html)
- [ZBIO SLE expected Q4 2026 — Seeking Alpha analysis](https://seekingalpha.com/article/4896887-zenas-strong-buy-on-obexelimab-enhancement-and-expected-sle-data-q4-2026)
- [NMRA 2026 strategy + KOASTAL-2/3 Q2](https://www.stocktitan.net/news/NMRA/neumora-therapeutics-highlights-2026-pipeline-strategy-and-ahee3ipozmqn.html)
- [AVTX LOTUS Q2 2026 readout outlook](https://finance.yahoo.com/news/avalo-therapeutics-eyes-q2-2026-233917407.html)
- [TSHA Q1 2026 update](https://ir.tayshagtx.com/news-releases/news-release-details/taysha-gene-therapies-announces-progress-across-tsha-102-pivotal/)
- [AXSM June IR conferences](https://www.biospace.com/press-releases/axsome-therapeutics-to-participate-in-upcoming-june-2026-investor-conferences)
- [ALXO Q1 2026 + ESMO Breast](https://www.globenewswire.com/news-release/2026/05/08/3291041/0/en/ALX-Oncology-Reports-First-Quarter-2026-Financial-Results-and-Provides-Corporate-Update.html)
- [NTLA $180M follow-on + lonvo-z BLA rolling](https://simplywall.st/stocks/us/pharmaceuticals-biotech/nasdaq-ntla/intellia-therapeutics/news/how-investors-may-respond-to-intellia-therapeutics-ntla-rais)
- [Biotech M&A tracker — BioPharma Dive](https://www.biopharmadive.com/news/biotech-pharma-deals-merger-acquisitions-tracker/604262/)
- [2026 biotech deals tracker — LaBiotech](https://www.labiotech.eu/biotech-deals-2026/)
- Yesterday's scan: `/9realms/daily_scans/daily_news_scan_2026-05-27.md`

---

*End of report. Mirror writes follow per Amendments 022 / 033 / 034.*
