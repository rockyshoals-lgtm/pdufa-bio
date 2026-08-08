# Daily Catalyst News Scan — 2026-05-14

**Scan time:** 2026-05-14 07:00 ET (automated)
**Watchlist size:** 24 active tickers
**Rule 0a enforcement:** ACTIVE
**Scan scope:** 8-Ks, topline announcements, delays, acquisitions, clinical holds (past 24h–30d windows)
**Session path note:** scheduled task references `/sessions/elegant-gracious-ramanujan/...` but live session is `dazzling-bold-allen`; outputs written to canonical `/Odin Perfection/` folder.

---

## HIGH PRIORITY ALERTS

### 1. AVBP — DEAD TICKER, must be REMOVED from canonical calendar
- **Source:** SEC S-4/A, Goodwin Law announcement, PitchBook
- **Detail:** Aerovate Therapeutics (AVBP) completed all-stock merger with Jade Biosciences on **April 28-29, 2025**. The combined company began trading as **JBIO** on April 29, 2025. AVBP also did a 1-for-35 reverse split (30.0M → 0.8M shares) and paid $69.6M ($2.40/share) special cash dividend.
- **Watchlist:** "AVBP — already reported Apr 30" is STALE / hallucinated. There is no live AVBP biotech catalyst — the ticker no longer exists as a biotech.
- **Action:** REMOVE AVBP from `CANONICAL_CATALYST_CALENDAR_2026-04-24.csv`. Investigate whether the prior catalyst row was for FURVENT topline (which is **Aerami/Verona Pharma**, not Aerovate). The 5/12 KAIZEN entry referencing "AVBP FURVENT" needs ticker reconciliation.

### 2. AVTX — Phase 2 LOTUS topline ALREADY FIRED on 2026-05-05 (POSITIVE)
- **Source:** Avalo Therapeutics press release 2026-05-05; ir.avalotx.com detail/220
- **Detail:** Phase 2 LOTUS hit primary endpoint at BOTH doses. HiSCR75: 42.2% (150 mg) / 42.9% (300 mg) vs **25.6% placebo**. Significant on key secondaries (HiSCR50, HiSCR90, IHS4, abscess/inflammatory nodule count, pain). Advancing to Phase 3.
- **Watchlist says:** "Jun 30 Phase 2 HS" → STALE by 39 days
- **Action:** Remove AVTX Jun 30 row from canonical calendar. Catalyst already cleared positively. Re-tag forward catalyst = Phase 3 initiation (timing TBD).

### 3. MIRM — VISTAS Phase 2b ALREADY FIRED on 2026-05-04 (POSITIVE)
- **Source:** Mirum BusinessWire press release 2026-05-04; stocktitan 8-K filing 2d0c16d8a3f8
- **Detail:** Volixibat hit primary endpoint in PSC. **2.72-point ItchRO improvement vs 1.08 placebo, placebo-adjusted Δ 1.64, p<0.0001**. n=158 (111 primary cohort moderate-to-severe + 47 secondary mild). Pre-NDA meeting summer 2026; NDA filing planned H2 2026. Stock +12.6% on the day.
- **Watchlist says:** "Jun 30 Phase 2b PSC" → STALE by ~57 days
- **Action:** Remove MIRM Jun 30 row from canonical calendar. Re-tag forward catalyst = NDA acceptance / PDUFA assignment H2 2026.

### 4. TRDA — ELEVATE-44 Cohort 1 ALREADY FIRED on 2026-05-07 (MIXED) + ticker mis-labeled
- **Source:** Entrada Therapeutics PR 2026-05-07 (globenewswire 3289797); BioTuesdays; ChartMill
- **Detail:** TRDA is **Entrada Therapeutics**, NOT Trevi Therapeutics. Watchlist company name is wrong (Trevi = chronic cough company, different ticker).
- Cohort 1 (6 mg/kg) results: hit primary objective (dystrophin restoration / safety), favorable safety (all TEAEs mild-moderate, no SAEs, no discontinuations), all 8 participants moved to OL portion. DMC recommended Cohort 2 escalation to **12 mg/kg** (not 6).
- **Market reaction:** Stock plunged ~**48%** on the day per ChartMill — drug exposure / dystrophin quantum read as disappointing despite primary hit.
- **Watchlist says:** "Jun 30 + Aug 31 DMD ELEVATE" — Cohort 1 has fired; "Cohort 2 by YE" is the new forward catalyst (12 mg/kg, not 6).
- **Action:** Update canonical calendar — TRDA company name → Entrada Therapeutics; Cohort 1 row "fired 5/7 mixed"; Cohort 2 forward = late 2026 at 12 mg/kg dose. Tag MIXED outcome label for the runup-validation framework so post-event slide is properly attributed.

### 5. CABA — Q1 2026 results released TODAY 2026-05-14 (existing position)
- **Source:** Manila Times republication of GlobeNewswire 2026-05-14; cabalettabio.com investor releases
- **Detail:** Cabaletta filed Q1 2026 results. $117M cash at 3/31/26 → liquidity into mid-2027 (with the $150M offering proceeds layered on). Strategic priorities: rese-cel clinical expansion in myositis / lupus / SSc / PV and manufacturing scale-up.
- **Position context:** Existing CABA position. The $150M underwritten offering pricing on 5/4 was already flagged (Amendment 012 / 5/12 KAIZEN). Today's Q1 print is the official corporate update — no new dilution beyond 5/4 raise, no PDUFA-type binary, no clinical-hold language. Confirm no rese-cel safety surprise in the 10-Q before next session.
- **Action:** Read the 10-Q today for any incremental safety / discontinuation language. If clean, no position change needed. EULAR June 3-6 + RESET multi-indication mid-2026 readout remain the binaries.

---

## MODERATE ALERTS

### 6. CADL — AUA oral presentation TOMORROW 2026-05-15 (T-1)
- **Source:** Candel PR 2026-03-09 (globenewswire 3251795); stocktitan sx3zunruh1zw; Manila Times 5/14 Q1 release
- **Detail:** CAN-2409 Phase 3 prostate cancer extended follow-up data presented at **AUA 2026 Friday 5/15, 11:30-11:40 AM ET** (Hall D, Walter E. Washington Convention Center). Practice-changing/paradigm-shifting clinical trials session. Investor conference call same day **1:00 PM ET**. BLA submission targeted Q4 2026.
- **Watchlist:** Originally tagged Jun 30 Phase 3 (corrected in 5/13 scan to May 15 AUA extended FU)
- **Action:** Stand-down trade window T-1 → T+0. Modest mover expected (extended FU, not new pivotal). Monitor live for "extended benefit" magnitude vs SoC. Q1 results released today 5/14 — read for incremental color.

### 7. IRON — ASCO Jun 2 program is **DISC-0974** (anti-HJV mAb), not bitopertin
- **Source:** Disc Medicine PRs 2026-04-21 (globenewswire 3278118), 2026-05-12 EHA release, Q1 2026 8-K 2026-05-05
- **Detail:** Watchlist says "Jun 2 ASCO Phase 2 myelofibrosis" → correct DATE, correct CONFERENCE, but the drug is **DISC-0974** (anti-hemojuvelin antibody for ANEMIA of myelofibrosis), NOT bitopertin. Bitopertin is the EPP program that took the 2/13 CRL (see 5/13 scan Alert #2). They are unrelated assets.
- ASCO oral session: 2026-06-02, 9:45 AM-12:45 PM CDT, presenter Naseema Gangat MBBS. n=61 patients, data cutoff 2026-04-27. RALLY-MF Phase 2.
- Additional context: Disc also has RALLY-MF anemia + DISC-0974 EHA congress data 2026-05-12, multiple presentations.
- **Action:** Update canonical calendar IRON Jun 2 row: drug = DISC-0974 (NOT bitopertin), indication = anemia of myelofibrosis, program separate from bitopertin EPP CRL. Re-validate composite score (EPP CRL is a financial drag but does not contaminate the MF anemia thesis).

### 8. NMRA — KOASTAL-2/-3 joint topline reconfirmed for Q2 2026
- **Source:** Neumora Q1 2026 release 2026-05-07 (stocktitan lucdleo3noxs); 2026 pipeline release 2026-01-05
- **Detail:** Both KOASTAL-2 and -3 fully enrolled Q1 2026 (>400 patients each, >450 evaluable per study). Joint topline expected **Q2 2026**. Kappa opioid receptor antagonist (navacaprant / NMRA-140) MDD. KOASTAL-1 already missed primary (Jan 2025 readout) — so 2 of 3 replicate studies need to hit to keep the regulatory thesis alive.
- **Watchlist:** "Jun 30 KOASTAL-2 / KOASTAL-3" — CONFIRMED on track Q2 (likely late May / June)
- **Action:** Pre-readout positioning needs to account for KOASTAL-1 miss baseline rate. Cash $147.1M into Q3 2027. Heavy binary risk asymmetry (2-of-2 needed). No size change to existing watchlist row; flag for review pre-event.

---

## NO CHANGE — CONFIRMED ON TRACK

| Ticker | Catalyst | Date | T-minus | Status |
|--------|----------|------|---------|--------|
| WVE    | ATS late-breaker WVE-006 AATD, Orlando, 4:03 PM ET | 2026-05-18 | T-4 | CONFIRMED, investor webcast 5:30 PM ET, RestorAATion-2 cohorts |
| MNKD   | Afrezza pediatric PDUFA (sBLA, ages 4-17) | 2026-05-29 | T-15 | CONFIRMED, no delay flagged |
| CRDF   | ASCO Phase 2 onvansertib RAS-mut mCRC rapid oral | 2026-06-02 08:00-09:30 CDT | T-19 | CONFIRMED, abstract #3510, abstract on ASCO site 5/21 |
| IRON   | ASCO Phase 2 oral DISC-0974 in MF anemia | 2026-06-02 09:45-12:45 CDT | T-19 | CONFIRMED, n=61, data through 4/27 |
| ACHV   | Cytisinicline PDUFA (smoking cessation NDA) | 2026-06-20 | T-37 | CONFIRMED + CNPV voucher + $180M upfront raised |
| UNCY   | OLC PDUFA (Class II resubmission) | 2026-06-29 | T-46 | CONFIRMED (NOT 6/27), $57.1M cash 3/31/26 |
| ARQT   | Pediatric ZORYVE PDUFA (ages 2-5) | 2026-06-29 | T-46 | CONFIRMED, Q1 2026 revenue $105M, cash-flow positive |
| VRDN   | Veligrotug TED BLA PDUFA | 2026-06-30 | T-47 | CONFIRMED, launch-ready, $762M cash |
| VERA   | Atacicept IgAN PDUFA | 2026-07-07 | T-54 | CONFIRMED, $596.8M cash, launch-ready |
| MNKD   | Furoscix ReadyFlow PDUFA | 2026-07-26 | T-73 | CONFIRMED |
| CAPR   | Deramiocel DMD PDUFA (Class 2 resub post-CRL) | 2026-08-22 | T-100 | CONFIRMED, HOPE-3 hit primary p=0.03 + LVEF secondary p=0.04 |
| NUVL   | Zidesamtinib ROS1 NSCLC PDUFA | 2026-09-18 | T-127 | CONFIRMED |
| CABA   | RESET multi-indication readout + EULAR Jun 3-6 | mid-2026 (~Jun 30) | T-47 | CONFIRMED (existing position), $150M raise priced 5/4 |
| TSHA   | REVEAL Part A long-term + Part B dosing update | H1 2026 (~Jun 30) | T-47 | CONFIRMED, no SAEs both doses, pivotal first dose Q4 2025 |
| ZBIO   | SunStone Phase 2 SLE topline | Q4 2026 (PUSHED from mid-2026) | ~T-150 | CONFIRMED (5/13 5/14 reaffirmed Q1 release) — re-position to Q4 |

---

## DATA QUALITY FLAGS FOR CANONICAL CALENDAR

Items to fix in `CANONICAL_CATALYST_CALENDAR_2026-04-24.csv`:

1. **AVBP** — REMOVE entire row. Ticker delisted April 2025 (merged into JBIO). Any "FURVENT" tag was likely confused with a different ticker (Verona Pharma VRNA — not on watchlist).
2. **AVTX** — REMOVE Jun 30 row. Catalyst fired 5/5/2026 positive. Re-tag forward = Phase 3 initiation TBD.
3. **MIRM** — REMOVE Jun 30 row. Catalyst fired 5/4/2026 positive. Re-tag forward = NDA filing H2 2026.
4. **TRDA** — UPDATE company name: Entrada Therapeutics (NOT Trevi). Cohort 1 fired 5/7 MIXED (primary hit, market reaction -48%). Forward Cohort 2 dose **12 mg/kg** (not 6), late 2026.
5. **IRON** — UPDATE Jun 2 ASCO row: drug = DISC-0974 (NOT bitopertin), indication = anemia of myelofibrosis (NOT myelofibrosis generally). Bitopertin EPP CRL stands per 5/13 scan.
6. **CADL** — Already corrected 5/13 to May 15 AUA + Q4 2026 BLA.
7. **NMRA** — KOASTAL is MDD (already corrected 5/13). Add KOASTAL-1 miss context for sizing.
8. **AXSM** — Still requires Apr 30 PDUFA outcome verification (open from 5/13). No outcome surfaced in today's scan.
9. **UNCY** — Date correction Jun 27 → Jun 29 (already flagged 5/13).
10. **ZBIO** — Q4 2026 re-position (already flagged 5/12 and 5/13).

---

## ADDITIONAL CONTEXT (FYI, not on watchlist)

- **BiomX (PHGE)** — FDA placed clinical hold on Phase 2b BX004 (cystic fibrosis) over third-party nebulizer device. Submitting additional manufacturer data to lift hold. Not on our watchlist but indicates current FDA scrutiny climate.
- **Kezar Life Sciences** — Cited in StatNews 4/6/2026 as a biotech that closed its doors after a 4-month FDA delay on autoimmune hepatitis program. Reinforces "FDA timelines unpredictable in 2026" theme. Not on our watchlist.
- **General FDA capacity** — multiple reports indicate Makary/Prasad-era FDA continuing to slip timelines on non-priority NDAs and cancel pre-scheduled meetings. Layer this into runup sizing (already captured in 5/1 regime-shift memory).

---

## NEXT SCAN

Tomorrow 2026-05-15 07:00 ET. Particular focus on:
- **CADL AUA presentation 5/15 11:30 AM ET + investor call 1:00 PM ET** — live event
- **WVE T-3 silence detector** — any pre-ATS leak before 5/18 4:03 PM ET data
- **MNKD T-14 to PDUFA** — watch for any pre-PDUFA 8-K / acquisition rumor
- **AXSM Apr 30 PDUFA outcome verification** (still open from 5/13)
- **CABA 10-Q deep-read** — incremental rese-cel safety language
- **NMRA pre-Q2-end** — watch for KOASTAL-2/-3 timing tightening

---

*Generated automatically. Cross-reference required against:*
- `/Odin Perfection/CANONICAL_CATALYST_CALENDAR_2026-04-24.csv`
- `/Odin Perfection/KAIZEN_LOG.md` (HIGH-PRIORITY alerts appended)
- `/Odin Perfection/9REALMS_MASTER_LOG.md` (master ledger)
