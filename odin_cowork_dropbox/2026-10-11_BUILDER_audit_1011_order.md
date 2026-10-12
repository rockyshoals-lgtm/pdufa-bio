# Builder note: the 10-11 audit (miner red team, three calendars, search), verified and actioned
**2026-10-11, work 15:10 to 18:40 Pacific = 18:10 to 21:40 Eastern (Sunday).** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

## 1. The audit, checked claim by claim

| Claim | Verdict | Evidence |
|---|---|---|
| Freshness strip reads "Data as of the last rebuild" | **True** for any reader without script (and every AI crawler): the static fallback was a placeholder; the script fills the time at view time | `build_freshness_stamp.py` line 168 |
| /readouts description ends mid-sentence ("...windows from.") | **True** | a pre-fix trim of a 180-character description; the page is a static August build |
| PDUFA calendar clean, 34/34 day rows resolve to a dated page | True (own guard, green) | `tests/test_event_page_titles_carry_date.py` |
| Conference dates match the organisers; API has no `date_end` | Dates **true** (AASLD re-read on aasld.org today: Thursday Nov 5 to Monday Nov 9, Colorado Convention Center, Denver). The field claim is **wrong**: the API serves `end_date` on every conference row (`_lib.mjs` line 147: `base.end_date = d.end`), ESC `2026-08-31`, ERS `2026-09-09`. A consumer can reproduce "In progress" | live `/api/v1/events?type=Conference` |
| 327 Readout rows at month precision, 72 "Window passed", 28 "Completed per registry" | True (my recount on the 10-10 dataset: 71 / 28 / 6 terminated at request time) | `_lib.mjs liveStatus` |
| R1: 237 guidance rows, 0 with a drug, 0 phase, 178 no trial | **True** | `daily/readouts_~0,8.csv` |
| R2: 129 of 237 guidance rows tiered PAST because the near edge is used | **True**: every 2026-H2 (65) and 2026-Q4 (64) row | same file |
| R3: 409 CT.gov rows at DAY precision | **True** | same file |
| R4: ticker by name fragment (SUNI via "Sun", Chugai as RHHBY) | **True**: `resolve_ticker` accepted any prefix match; PARENT mapped Chugai to RHHBY | `phase_readout_miner.py` |
| R5: equivalence and Phase 1-only trials pass `is_catalyst` | **True** for the ivermectin-cream comparison (no "bioequivalence" in its title); Phase 1-only had no enrolment rule | same |
| R6: 25 conference rows with empty `catalyst_type` | **True** | same |
| R7: 13 site-Guided tickers absent from the miner | **Understated**: 27 of 56 Guided tickers have no guidance row in the miner | dataset vs file |
| R9: the already-read-out pass is what the 72 rows need | Agreed; implemented as a daily step (section 3) | |

**One correction to my own 10-11 red team (ORDER note, finding "live P1").** I listed 15 drifted rows. Three of them (ANNX, ERAS, CLRB) carry an NCT that is a *different drug's* trial (`_readout_ta_manual.json` "nct_mismatch": the ANNX row is tanruprubart, the attached record is vonaprument's dry-AMD study). A registry date for another trial is not a fact about those rows, so they were correctly NOT moved; the real count is **12 moved, 6 terminated, 1 results posted**. "ANNX is the one that bites first" was wrong: the ANNX row's problem is its NCT, which stays on the hand-fix list. Retracted.

## 2. Order 1: the miner (phase_readout_miner.py, catalyst_crawler.py)

All six fixes are in, each tested against the 10-11 output offline:

| Fix | What changed | Checked |
|---|---|---|
| R1 | `guidance_program(ctx, date_pos)` names the drug (code or INN nearest the date, preceding wins), phase and indication from the same window; a row with **no drug and no trial** is rejected to `ro_guidance_unnamed_*.csv` | replay on the 237 windows: drug named for 122, phase 164, drug-or-trial 147; the other 90 would now be rejected, not emitted |
| R2 | `days_to_readout = max(0, near_edge - today)` while the far edge is ahead; PAST only when the far edge has passed | 129 rows whose window contains today stop being PAST |
| R3 | every `ctgov_pcd` row is emitted at **month** precision (`catalyst_date` = YYYY-MM; the registry's day survives in `pcd`) | 0 ctgov rows at day |
| R4 | fuzzy ticker hits need every distinctive token of the shorter name in the longer one and one token of 4+ letters; PARENT keys match longest-first (Merck KGaA no longer lands on MRK); Chugai → CHGCY | "sun pharmaceutical industries" vs "sun" → unmapped; "genentech" → RHHBY |
| R5 | `_EQUIVALENCE` (therapeutic equivalence, a "comparing ... ® ... placebo/vehicle" title, PK-only, healthy volunteers); Phase 1-only requires industry sponsor and enrolment ≥ 20 | ivermectin cream → False; 12-patient Phase 1 → False; 60-patient → True |
| R6 | conference rows carry `catalyst_type: ConferencePresentation`, `date_precision: window` and a new `window_end` column from conferences.json (organiser-verified), plus drug/phase from the release | |
| 3(b) | `catalyst_crawler.norm_any`: HALF is tested before QUARTER ("second half of 2027" was falling into the `second` → Q2 branch: that is the KZIA/BIOA/ANL bug); "mid-YYYY" → year precision; "year-end" → Q4; "by the end of" → year; "H2 2026" now parsed | 10 phrases |
| 3(e) | the already-read-out pass now also scans **company_guidance** rows (it only looked at registry rows), so a QTTB "mid-2026" row meets Q32 Bio's July 13 results headline and is killed | |

Not done: an EDGAR full-text check for a later "topline results" filing (3(e) as written). The FMP press-release pass covers the same case and is already wired; EDGAR would add a second source for sponsors FMP misses. Carried.

**R7, the merge rule.** `readout_merge.py` is the old EDGAR+CT.gov merge and never touches the site, so the rule lives in a new `merge_redteam_readouts.py`: it refuses any file without `rt_verdict`, uses only PUBLISH / PUBLISH_FIX / PUBLISH_CAVEAT rows with the `rt_*` columns, **never removes or re-dates a site row** (exits non-zero if the row count falls), adds Guided rows for programs the site lacks, moves an existing Guided row only when a later filing re-dates a window that has not yet ended, and writes conference rows to a hand-verified presenter file. Applied today:

- 13 Guided readout rows added (ANL, BIOA, DYN, EYPT DME, GPCR MAD, IMA, IRD, IVEVF, KRRO, KZIA, LSTA, PCVX OPUS-2/3, TRXB), each with the verbatim timing sentence, form and filing date; half-year windows at YEAR precision with the half kept in `_d.guided_window` (the schema has no half).
- 1 Guided row moved: TTRX GX-03 Q4 2026 → Q1 2027 per the 2026-10-07 EX-99.1, date_history written.
- 18 conference presenters (ECTRIMS 5, ESMO 3 new, ASN 2, SITC 2, AASLD VIR, ACR 2, ObesityWeek AMLX, ENA 2) in `catalysts_out/conference_presenters_VERIFIED_2026-10-11.csv`; `build_conferences.py` now reads every `VERIFIED_*.csv`. API presenter entries 42 → 60.
- The 131 registry-estimate rows were **not** merged (R5/R8: mostly big-pharma Phase 1/2 completion windows). David's ruling.

## 3. Order 2 and the live P1: passed windows say what we found

- `refresh_readout_registry.py` existed since July and was in neither the chain nor CI. It is now in both, **before** `apply_readout_registry_signals.py`, skips nct-mismatch rows, stamps `ua`, and writes a `date_history` entry per move naming the registry date, type, status and update date. Run today: 12 windows re-synced (ANIP, CERS, DWTX, ACRS, GRFS, KPTI, ALEC, ARDX, XNCR, MLTX, MBX, GOSS), 6 terminated rows annotated.
- New guard `tests/test_readout_registry_synced.py`: an Estimated row's `dm` must equal the month of the registry primary-completion date the build recorded on it. 0 → planted 1 (HUMA dm 1999-01) → 0.
- New daily step `resolve_past_readouts.py` (CI, with FMP): for every Estimated/Guided row whose window has passed it records `_d.resolution`: `sponsor_release` (the sponsor's own results headline naming the drug, dated and linked; outcome NOT summarised, that stays the human path), or `no_topline` with the check date and what was searched. Terminated rows keep the registry status. Without a key (locally) it claims nothing beyond registry results-posted dates.
- API: status strings `Sponsor release YYYY-MM-DD`, `No topline as of YYYY-MM-DD`, `Completed per registry, no topline as of YYYY-MM-DD`, `Results posted on ClinicalTrials.gov YYYY-MM-DD`; `resolution` exposed in the row.
- /readouts: the block formerly titled "Recently reported: stock move over the estimated readout window" (nothing in it was reported) is now "Readout windows that have passed: what we found, and the stock move over the window", every row carries its resolution, and the limit rose from 40 to 160 so all ~105 passed rows are listed.
- Guard `tests/test_readouts_passed_windows_resolved.py`: lede starts at the current Eastern month; every passed-window row carries a resolution phrase; description ends in a sentence; in CI (key present) more than a tenth "not yet checked" fails. 0 → planted 1 → 0. **Until the first CI run with FMP, the rows read "Window passed; not yet checked"**, which is true.

## 4. Order 3: /readouts

Lede: "This page lists 206 expected clinical trial readouts covering October 2026 to December 2027. A further 110 readouts whose window has already passed are listed below with what we found..." (`build_hub_lede.py`; the home-page count uses the same not-yet-passed set; `test_lede_matches_table` taught the two-part form). Description: "Clinical trial readouts from October 2026: drug, company, indication and source. Windows are company guidance or ClinicalTrials.gov estimates. Not advice." (155 characters, regenerated monthly). Month sections already began at October; the stale start was the lede and the strip's chart, which now follows.

## 5. Order 4: conference pages

New `build_conference_pages.py` (chain and CI, before the hub): one page per meeting in conferences.json whose end is today or later, 38 pages (24 created today: AACR, AAD, AAN, AAO, ACAAI, ACC, ACG, ADA, AHA, ASBMR, ASCO, ASCO-GI, ASCO-GU, ASGCT, ATS, DDW, EASL, EHA, ENA, ESMO-Asia, ESMO-IO, ObesityWeek, SNO, WORLD; 14 refreshed). Each title carries the organiser's dates and city ("AASLD The Liver Meeting 2026: Nov 5-9, 2026, Denver: biotech presenters | pdufa.bio"), Event schema with start/end/location/sameAs, breadcrumbs, a dates/location/organiser card, presenters each linked to their filing or release, and a separate "filings that mention" list for mined rows. Codes with spaces slug to hyphens (`/conference/ESMO-Asia`); the FAQ and run-up modules learned the slug. API conference rows now link their page instead of the hub. `date_end`: already served as `end_date`; no change.

## 6. Orders 5 and 6

- Freshness strip static text is now the real Eastern rebuild time ("Data as of Oct 11, 2026 8:44 PM ET"), script still refines it from build-info. The daily refresh commit already rewrites ~1,180 pages, so this costs nothing new; the sitemap hash excludes the block.
- /crl: title "FDA Complete Response Letter Database: 458 Released CRLs by Year", h1 "FDA complete response letter database: 458 released CRLs", first sentence states the count and that the FDA releases letters selectively.
- Enspryng decision day: hourly cron 13:00-23:00 UTC on Oct 15 added to the workflow (remove after 10-16), so the FDA press RSS / gene.com listing / openFDA watchers raise the lead within the hour of the record instead of at the next daily slot. GitHub's 1.5 to 5 h queue lag still applies: the fastest path on the day is a manual dispatch the moment the release is seen, then the quarantine issue is actioned and the page goes out from the FDA record.

## 6a. The 26 company-Guided Q3-2026 readouts, resolved against the sponsors' own exhibits

`test_guided_readouts_current` (10-day grace after a guided date) started failing on 10-11 for all 26 Q3 Guided rows. Each was read against the sponsor's 8-K/6-K exhibits on EDGAR (full-text search, 2026-07-01 to 10-11; every URL below returned 200 today). `apply_1011_guided_q3_resolutions.py`:

| Outcome | Rows | Source (EDGAR exhibit, date) |
|---|---|---|
| **Reported** (st=Reported, d=exhibit date, headline-only review, readout_reported_manual.json entry) | DFTX DT120 Panorama Phase 3 GAD, met primary and all key secondaries (EX-99.1 09-14); EVMN EVO756 Phase 2b AD, **did not meet** primary (EX-99.1 09-09); GPCR ACCG-2671 data reported positive (EX-99.1 09-08); IMMX NXC-201 NEXICART-2 interim, 89% CR (EX-99.1 09-29); IRON DISC-3405 RESTORE-PV initial results at SOHO (EX-99.1 09-10); KOD tabirafusp-ted (KSI-501) and Zenkuda met DAYBREAK primary endpoints (EX-99.1 09-28); PHVS deucrictibant CHAPTER-3 positive topline, 83% attack-rate reduction (6-K EX-99.1 09-08); TECX TX2100 Phase 1 favorable (EX-99.1 09-29); ABCL ABCL635 Phase 2 (EX-99.1 08-10, already in the manual store); ALMS LUMUS Phase 2b topline (EX-99.2 09-01): the program is **envudeucitinib in SLE**, the row's "anifrolumab" label was an extraction error and is corrected | 10 |
| **Moved** | MBRX annamycin: Part A of MIRACLE enrolment complete, data readout Q1 2027 (EX-99.1 09-29) → Guided Q1 2027 with date_history | 1 |
| **No topline as of 2026-10-11** (`_d.resolution`, EDGAR search stated; served as such; re-checked daily) | AARD, BOLT, MNKD, OCGN, PMN, PPBT, SCYX, STTK, WHWK, XENE | 10 |
| **Acked for a human reading** (the exhibit is not the readout the row guides, or the row's program is doubtful) | ALZN (09-29 exhibit is a Phase 1/2A PK-imaging poster); ROIV (brepocitinib was approved as LISRAYA 08-27; no readout); SYRE (SPY001 Part A date not in the window read; 09-08 release says PoC complete for all three); VKTX (09-22 is the Phase 2 maintenance study, not VANQUISH-2); VTGN (09-22 is PALISADE-4 OLE preliminary data) | 5 |

Outcome words are the headlines' own; no result is characterised beyond them.

## 6b. Found by the guards on the way, fixed

- **MRK I-DXd (Withdrawn, goal 2026-10-10) was badged "Awaiting" on /calendar and /calendar/2026/october** the moment its goal date passed: `mark_calendar_awaiting.py` and its guard only excluded Decided. Both now treat Withdrawn as closed (the API never called it Awaiting); the badge is removed and the guard proves 0.
- 13 new Guided rows tagged with a therapeutic area from the filing sentence (`_readout_ta_manual.json`), keeping forward-readout TA coverage at 73%.
- `test_one_date_per_page` excludes the `data-fresh-built` span: "Data as of {rebuild time}" and "Page updated {content date}" are two named facts, not two dates for one thing.

## 7. One correction to my own 10-11 SEO note
Action 3 there said 1,299 pages share one build-minute `modified_time`. The mechanism is already content-change based (`build_date_modified.py` reads `_sitemap_lastmod.json`); the shared stamps come from pages whose content did change on 10-10 (normaliser sweeps). The useful action is to stop sweeps rewriting unchanged content, not to change the stamp. Noted, not actioned.

## Carried, still David's
`goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP secrets; Google Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; Bing Webmaster key in `.env`; the 131 registry-estimate miner rows; the 20 nct-mismatch readout rows (hand fix of the NCT); EDGAR second source for 3(e).
