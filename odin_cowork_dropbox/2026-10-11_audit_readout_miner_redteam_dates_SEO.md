# Audit: red team of the phase-readout miner, the three calendars checked against primary sources, and the next search moves
**2026-10-11, measured 14:49 to 15:00 Eastern = 18:49 to 19:00 UTC (Sunday). Miner output timestamp 2026-10-11T15:34:51Z = 08:34 Pacific = 11:34 Eastern.** *Per RULE 1 every time carries its zone.*
**Live build `e62560970`, generated 2026-10-10T17:51:07Z (13:51 Eastern Saturday). API 460 rows: 90 PDUFA, 327 Readout, 42 Conference, 2 AdComm. `held_leads` []. Next decision RHHBY 2026-10-15, `next_days` 4.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE 10-10 BUILDER ORDER, VERIFIED LIVE

Every acceptance line in the builder's 10-10 note holds on the live site, cache-busted: Rhapsido `/fda-decision/NVS-2026-10-06` FDA-dated to Oct 6 with the Novartis Oct 7 announcement noted; `/pdufa/RHHBY-giredestrant-evera` "Dec 18, 2026" and `/pdufa/COGT-bezuclastinib-summit` "Dec 30, 2026", each naming its sibling; neladalkib re-windowed to "Nov 2026" on the GSK 6-K; Enspryng page carries the fact-first description, the SatraGO-1/SatraGO-2 sentence, Event `startDate 2026-10-15`, and a 10-10 timestamp; `/patent-cliff/exclusivity` stylesheet 1,412 characters (was 373); `/adcomm` states one count (187 notices, 2 votes); RVMD 13F is a headed table; `/fda-approval-decisions-this-week` is live with Tecentriq and Rhapsido under "Decided this week (2)" and Enspryng under next week.

On the Event-schema claim in my 10-10 audit: the builder is right. My regex required `"startDate":"` with no space; the page writes `"startDate": "`. The 09-02 timestamps on 20 pending pages are true content dates and should stay. Retracted.

Two small things the pass left behind:

- **Freshness strip reads "Data as of the last rebuild"** on every page. The order asked for the rebuild time in Eastern; the string is a placeholder, not a time. One token.
- **`/readouts` meta description ends mid-sentence:** "...Estimated primary-completion windows from." Bing shows descriptions verbatim.

---

# 2. THE THREE CALENDARS AGAINST PRIMARY SOURCES

## 2a. PDUFA: clean

0 day-dated rows past goal; 0 non-day rows carrying a date; 0 month/date disagreements; 34 day-dated upcoming rows, 34 sourced, 34 of 34 resolve to a page whose title carries the date (the builder's new guard, confirmed by my own pass). Remaining unbacked: AZN Ultomiris and NVO CagriSema (2026-12, month), NVO Mim8 (no month). David's items.

## 2b. Conferences: dates verified, three spot-checked against the organiser

| Conference | Site | Organiser |
|---|---|---|
| AAO 2026 | 2026-10-09, status "In progress" on Oct 11 | aao.org: New Orleans, Oct 9 to 12. **Correct, including the live status** |
| ESMO 2026 | 2026-10-23 | esmo.org: Madrid, Oct 23 to 27. **Correct** |
| ASH 2026 | 2026-12-12 | hematology.org: New Orleans, Dec 12 to 15. **Correct** |

0 conferences mislabelled against the Eastern date. The API serves a start date and no end date (`date_end` absent), so "In progress" has to be computed from a duration the API does not expose; a consumer cannot reproduce the status. Add `date_end`.

## 2c. Readouts: this is the weak calendar, and the new miner is aimed at it

Live: 327 Readout rows, **every one at month precision with `date: null`**. Status mix: Estimated 186, Guided 31, Window passed 72, Completed per registry 28, Terminated 6, Reported 4. By month: 134 rows sit in June to September 2026, already over; `/readouts` says "This page lists 252 expected clinical trial readouts covering July 2026 to December 2027" and its month strip starts at "Jun '26 14, Jul 33, Aug 40, Sep 47". On October 11, a reader opens the readout calendar and the first four months shown are gone. **72 rows say "Window passed" with no outcome and no date on which we last checked.** That is the readouts equivalent of the MRK row: current-looking, sourced, and not resolved.

---

# 3. RED TEAM: `phase_readout_miner.py` output of 2026-10-11 (971 rows; 216 new)

What it is: CT.gov queried by primary-completion date across the whole registry (709 rows), SEC EDGAR guidance scan (237 rows), FMP press for conference slots (25 rows). The design note is right that the old sponsor-list path was structurally blind, and the registry-wide query is the correct fix. The output is not publishable yet. In order of damage:

**R1. The 237 company-guidance rows carry no drug (237 of 237), no phase (237 of 237) and no trial name (178 of 237).** A row that says "KPTI, 2026-H2, readout, from an 8-K" cannot go on a page. The guidance sentence is in the filing the row links; the miner must extract the program named in the same sentence or discard the row. These are the only rows in the file with a company's own word behind them, so they are the ones worth the work.

**R2. 129 of those 237 guidance rows are labelled PAST and would be dropped.** Every "2026-H2" (65) and "2026-Q4" (64) row has `imminence: PAST` and negative `days_to_readout` because the tier takes the window's near edge (July 1, October 1) and today is past it. A window that contains today is the most imminent kind there is. Rule: `days_to_readout = max(0, near_edge - today)` while `far_edge >= today`; PAST only when the far edge has passed. This single bug hides the 129 most actionable rows in the file.

**R3. 409 CT.gov rows are at DAY precision.** The miner's own docstring says CT.gov-derived rows get month precision because "primary completion date is NOT the readout date". The output contradicts it: JNJ apalutamide "2026-10-12, day, IMMINENT, 1 day". Published, that is a fabricated readout day. The site's current rule (month windows for registry dates) is the honest one; the miner must emit `date_precision: month` for every `ctgov_pcd` row regardless of the registry's day.

**R4. Ticker resolution by sponsor-name fragment produces wrong listings.** `SUNI` for "Sun Pharmaceutical Industries, Inc." resolves through an SEC entry titled "SUN"; `RHHBY` for Chugai Pharmaceutical (a separately listed company Roche part-owns); `JNJ` for Janssen is fine, but the method cannot tell the two cases apart. 158 of 276 tickers fail a sponsor-word-in-registrant-name check. Rule: accept a ticker only when the SEC registrant name shares a distinctive token with the sponsor, or the sponsor is a known subsidiary in a hand list; otherwise emit the row unmapped (the miner already has `--listed-only`).

**R5. `is_catalyst` lets through trials that are not readouts anyone trades or cites:** a Sun Pharma ivermectin-cream comparison against Soolantra (a bioequivalence study), 158 Phase 1-only trials, 58 trials with enrollment under 20, big-pharma single-arm Phase 1 cohorts. Add: exclude bioequivalence / bioavailability / formulation / PK-only / healthy-volunteer titles; Phase 1-only requires an industry sponsor and enrollment ≥ 20 or a company guidance match.

**R6. The 25 conference rows have `catalyst_type` empty and are dated to the meeting's first day** (ESMO rows at Oct 23). The note says so, which is honest; but a row with no type will be filtered by every consumer. Set `catalyst_type: ConferencePresentation`, keep the first-day date at `date_precision: window` with the meeting's end date, and pull the session day from the abstract programme where ESMO/ASH publish it.

**R7. The miner is not a superset of what the site already knows.** 13 tickers the site holds as Guided (company guidance from SEC filings: ALNY, ATAI, CRIS, IPSC, KYNB, MTVA, SKYE, TYRA and five more) have no company-guidance row in the miner. The EDGAR pass is capped (`max_docs=1200`, 450-day lookback) and missed them. Merge, do not replace: `readout_merge.py` must keep every site row the miner lacks.

**R8. Overlap with the live calendar is small:** the site's 182 readout NCTs and the miner's 709 overlap on 70. Of the miner's 242 IMMINENT/NEAR CT.gov rows, 31 are on the site. So the miner would add roughly 200 near-term registry rows, most of them big-pharma Phase 1/2 completion dates (R5), and would still not fix the 72 "Window passed" rows (R9).

**R9. What the miner does well and the site needs today: the "ALREADY READ OUT" pass.** `ro_already_read_out_083509.csv` found 8 rows whose sponsor has already published topline (MoonLake IZAR-1, 2026-08-10, for example) while the registry still says a future date. Run that pass over the site's 72 "Window passed" and 28 "Completed per registry" rows. Each resolves to one of three: **Reported** (link the release, date it), **No topline as of {date}** (dated, re-checked nightly), or **Terminated** (registry). That turns the weakest surface into one that says what it knows and when it last looked.

**Verdict:** the miner is the right architecture with five correctness bugs (R1 to R5) that make its current output unpublishable, one gap (R7) that makes a straight replacement a regression, and one feature (R9) the site should take today.

---

# 4. SEO, BING AND AI CITATIONS

## 4a. Numbers, data to October 9

| | Oct 6 | Oct 7 | Oct 8 | **Oct 9** |
|---|---|---|---|---|
| AI citations | 337 | 482 | 469 | **387** |
| Cited pages | 37 | 58 | 58 | **52** |
| Web impressions | 958 | 909 | 921 | **722** |
| Web clicks | 26 | 21 | 26 | **21** |

Totals: AI **13.0K** citations (12.6K yesterday), 25 average cited pages, **46 grounding queries** (44). Web **830 clicks / 33.7K impressions / 2.46%**. `pdufa date` 1.1K at **23.03%** (third read in a row holding or rising). `fda complete response letter database` **doubled, 18 → 36** citations. `fda approval decision biotech` **387 impressions, 0 clicks** (250 on Friday); the weekly page went live Saturday and cannot have been indexed for this read. Re-test Wednesday.

## 4b. Improvement items, ranked by expected citation gain

1. **Resolve the 72 "Window passed" readouts (R9).** The oncology-readouts grounding query already gives us 56.81% share from a page whose rows are months stale. A readout page that states outcomes with dates is the one an AI layer keeps citing after the window closes.
2. **`/readouts` lede and strip start at the current month.** "covering July 2026" on October 11 is a freshness signal against us on every crawl. Past-month rows move to a "Recent windows" section below, each with its resolution from item 1.
3. **One page per conference with the organiser's dates, location, and the presenting companies we can source**, titled "{Conference} 2026: {dates}, {city}: biotech presenters". `aasld 2026` has 80 impressions at position 9.28 and `aasld conference 2026` 24 at 9.96 with 0 clicks; `sabcs 2026` 16 at 9.50. A dated page per meeting is the standard move and we have the rows.
4. **Enspryng, Thursday.** The page is ready. The day of the decision, publish within the hour from the FDA record (the gene.com HTML listing now feeds the watcher; the FDA press RSS is first for most approvals). The Tecentriq answer box went to fda.gov and a three-hour-old blog; being second-fastest with the FDA's own sentence is the realistic target.
5. **`date_end` in the API** (2b) and the two text fixes in section 1. Small, and each one is a thing a machine reader hits.
6. **CRL database query (36 citations, 15.79% share):** `/crl` or wherever the 458-record corpus lives should carry the phrase "complete response letter database" in title and h1 if it does not already, and state the count and the FDA release-policy caveat in the first sentence.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Miner fixes R2, R3, R1, R4, R5, R6 before any merge**; R7 merge rule in `readout_merge.py` | Re-run: 0 guidance rows without a drug; 0 `ctgov_pcd` rows at day precision; 0 PAST rows whose window contains today; every mapped ticker passes the registrant-name check; a run on the 13 site-Guided tickers keeps all 13 |
| **2** | **Run the already-read-out pass over the 100 past-window site rows** and publish each as Reported / No topline as of {date} / Terminated | `/readouts` shows 0 bare "Window passed"; every past-window row carries a dated resolution |
| **3** | `/readouts` starts at October; past months below with resolutions; fix the description sentence | Lede names the current month; description ends in a full sentence |
| **4** | Conference pages, one per meeting, organiser-dated; `date_end` in the API | `/conference/aasld-2026` 200 with Nov 5 to 9 (verify on aasld.org) and presenters; API conference rows carry `date_end` |
| **5** | Freshness strip: real rebuild time in Eastern | "Data as of Oct 11, 2026 1:51 PM ET" |
| 6 | Enspryng decision-day plan (section 4b item 4) | Decision page within 60 minutes of the FDA record |
| 7 | Carried: `goal_date_held`, Jaypirca letter date, RXC-005 aliases; David: SMTP, Drive, AZN/NVO sources | |

---

# 6. BOTTOM LINE

**PDUFA and conference calendars: tight.** Every pending decision has a sourced date and a page that states it; conference dates match the organisers on all three I checked, and the live status is right to the day.

**Readouts: the loose calendar, and the new miner is the right tool pointed at it, not yet safe to fire.** Its company-guidance rows have no drug names, its tiering hides the 129 rows that matter most, and it would publish registry completion days as readout days. Fix those five things and merge rather than replace. Meanwhile, its already-read-out pass is exactly what the 72 "Window passed" rows on the live site need.

**Search: 13K citations, 46 grounding queries, `pdufa date` share rising three reads running.** The next gains are on the readout surface and on dated conference pages, both of which are rows we already hold.

---
*Site read from a browser client with `cache: 'reload'`, 2026-10-11 18:49 to 19:00 UTC, against build `e62560970`. Miner output read from `daily/readouts_~0,8.csv`, `daily/NEW_2026-10-11.csv`, `ro_already_read_out_083509.csv` (written 2026-10-11T15:34:51Z) and `phase_readout_miner.py`. Conference dates read on aao.org, esmo.org and hematology.org via Bing. Bing Webmaster AI Performance and Search Performance (data to 2026-10-09) read live. Not investment advice.*
