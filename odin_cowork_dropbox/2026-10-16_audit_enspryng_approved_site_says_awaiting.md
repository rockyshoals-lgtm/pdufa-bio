# Audit: Enspryng was approved; the site says "Awaiting". Everything the builder published on 10-15 checks out against the FDA
**2026-10-16, measured 01:53 to 02:10 Eastern = 05:53 to 06:10 UTC (Friday, the morning after the goal date).** *Per RULE 1 every time carries its zone.*
**Live build `7b0456259`, generated 2026-10-16T02:03:12Z (22:03 Eastern, Oct 15). API 475 rows: 91 PDUFA, 340 Readout, 42 Conference, 2 AdComm. `/build-info.json` (computed per request): `as_of_eastern` 2026-10-16, `next_ticker` RHHBY, `next_status` "awaiting", `days_since_goal` 1, `held_leads` [].**
*Facts and build mechanics only. Not investment advice.*

---

# 0. P0: Enspryng (satralizumab) for thyroid eye disease is approved

**Primary source:** Genentech release, gene.com, dateline **"South San Francisco, CA -- October 15, 2026"**: "Genentech, a member of the Roche Group (SIX: RO, ROP; OTCQX: RHHBY), announced today that the U.S. Food and Drug Administration (FDA) has approved Enspryng (satralizumab-mwge) for the treatment of adults with thyroid eye disease (TED), providing patients with the first and only at-home subcutaneous treatment option." It is the top row of the gene.com press-release listing the watcher reads.
https://www.gene.com/media/press-releases/15137/2026-10-15/fda-approves-genentechs-enspryng-a-first

Roche issued the same news on roche.com; Yahoo Finance, Morningstar (Dow Jones) and others carry it.

**Live state at 01:53 Eastern:**

- API row `pdufa_rhhby_2026-10-15`: status **Awaiting**, `decision_date` null.
- build-info: next decision RHHBY, "awaiting".
- `/fda-decisions-today`: "No FDA decision on a tracked application has been published today, October 15, 2026. The most recent was IBRX's ANKTIVA..."
- Weekly page: Enspryng "October 15, 2026 today" under "Still ahead this week".
- `/calendar`: "In October the FDA is due to decide on Enspryng (RHHBY, Oct 15)".
- `held_leads` is empty.

**When it was released, honestly:** I cannot pin it. Bing labels the gene.com page "1 day ago", the roche.com release "49 minutes ago", Yahoo's copy "40 minutes ago", and an earlier SERP "4h" and "5h", all within ten minutes of each other. That is enough to say it reached the wires late on October 15 Eastern. It is not enough to say it was public before the 22:03 Eastern build. The builder's 21:10 Eastern check found nothing on gene.com. So this is not yet a proven watcher miss.

**The test is the next scheduled run (10:00 UTC = 06:00 Eastern).** If that run does not hold a `drug_pages` or `sponsor_newswire` lead for `pdufa_rhhby_2026-10-15`, the gene.com JSON-LD reader missed a release that sat at the top of its own listing, and that is the finding. Either way, **do not wait for the schedule: dispatch now and publish.**

**How to publish it (the house rules for this case):**

- **FDA action date.** openFDA `drugsfda` for BLA 761149 shows `last_updated` 2026-10-14 and no new supplement, so the FDA's own day is not on record yet. Use the Jaypirca pattern:
  - `decision_date` 2026-10-15 from the release;
  - `fda_action_date` null until Drugs@FDA posts the supplement letter;
  - `decision_date_unsourced` true;
  - **no early or late margin, and the row does not enter the timing statistic** until the letter is posted.
  - The page says "Genentech announced on October 15, 2026 that the FDA approved…" and "pdufa.bio holds no FDA record of the action day yet". `sync_fda_action_dates.py` swaps the letter date in when it appears.
- **Page.**
  - Title: `/fda-decision/RHHBY-2026-10-15`, "Enspryng (satralizumab) Approved for Thyroid Eye Disease, Announced Oct 15, 2026 | RHHBY FDA Decision | pdufa.bio".
  - Body: SatraGO-1 and SatraGO-2 in Genentech's words (the sentence already on the event page), and a sibling link to the MOGAD row (goal Jan 10, 2027).
  - FAQ, led by "Was Enspryng approved for thyroid eye disease?".
- **David, after the deploy:** Bing Webmaster → URL Inspection → Request indexing for the decision page and `/fda-decisions-today` (runbook step 4 from 10-13).
- **Search position tonight:**
  - Bing, "enspryng fda approval thyroid eye disease date": roche.com, gene.com, Yahoo, Morningstar, and trialfriend's pre-decision post. pdufa.bio is not on the first page.
  - The trialfriend post still says "the FDA is due to decide". A dated FDA-sourced page published today can overtake it. One published tomorrow probably cannot.

---

# 1. THE BUILDER'S 10-13 AND 10-15 NOTES: VERIFIED

**10-13 order, all live.**

- Every "today" page uses Eastern time. At 22:03 Eastern the today page read "today, October 15".
- `TZ: America/New_York` is now set for the whole rebuild job. That catches the ~25 builders that still called `dt.date.today()`, and `test_today_is_eastern.py` fails if the line is removed.
- Root cause of the 1,000-page lastmod churn: a hash regex that left a stray comma.
- Search submission is ordered: hubs first, then the Bing batch at 40, with retry on the quota remainder.
- VTRS/IRD are one page. VTRS canonicalises to IRD and both API rows link it.

**10-15: Anktiva** (`/fda-decision/IBRX-2026-10-14`, "Approved Oct 14, 2026, 84 Days Early").

- The FDA notice and both 8-Ks (goal Jan 6, 2027; announcement Oct 14) state their dates, so the margin is publishable.
- The statistic moved to **32: 21 early / 10 on the day / 1 late**, consistent on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing` and `/llms.txt`.

**10-15: thirteen corrected or new decision pages.** I checked five against openFDA tonight. Every action date matches exactly:

| Page | Site | Drugs@FDA |
|---|---|---|
| `PFE-2026-10-07` Tukysa | Oct 7 | NDA 213411 S-10 AP 20261007, efficacy |
| `AMGN-2026-10-09` Repatha | Oct 9 | BLA 125522 S-47 AP 20261009, efficacy |
| `TEVA-2026-10-08` Weltruza | Oct 8 | NDA 219007 ORIG-1 AP 20261008 |
| `BMY-2026-09-30` Camzyos (was "June 1") | Sep 30 | NDA 214998 S-13 AP 20260930, efficacy |
| `NVS-2026-10-06` Rhapsido | Oct 6 | NDA 218436 S-1 AP 20261006, efficacy |

The retired slugs redirect: `BMY-2026-06-01` and `ZVRA-2026-06-08` both return a redirect. The MOGAD goal date (Jan 10, 2027, Genentech 09-09 release) is a row and a page.

**This was the most important correction pass the site has had.** Four published "approvals" were not approvals: a Miplyffa Orange Book patent listing on three tickers, a Canalevia effectiveness topline, and a Papzimeos page with no FDA action behind it. Camzyos was dated to its acceptance day. These had sat under every guard and every audit, including mine. The method was right: the builder re-read everything the archive sync could not match, against primary sources only.

**One correction inside the builder's note.** It says the quarantine "blocked every deploy for a day" on 10-15 (six red runs, live stuck on the 10-14 23:39 UTC build). That is the second time a held lead has frozen the whole site; the 09-28 freeze was the first. The fix and its replay test are the right shape. Watch the next held lead specifically: it is the only real test of "a lead holds only its own row".

---

# 2. CURRENCY

| Check | Live |
|---|---|
| Day-dated PDUFAs past goal and not Decided/Withdrawn | **1: Enspryng, Awaiting (section 0)** |
| Rows carrying a date at non-day precision / month mismatch | 0 / 0 |
| Conferences mislabelled against the Eastern date | 0 |
| Upcoming PDUFAs | 40; 34 day-dated, 34 sourced |
| Next after Enspryng | IRD/VTRS phentolamine 10-17 (Saturday), GSK bepirovirsen 10-26, INO-3107 10-30 |
| Readouts | 340 rows; bare "Window passed" 2; dated "no topline as of" 79; sponsor release 6; Reported 14 |
| Freshness strip | "Data as of Oct 15, 2026 10:03 PM ET" |

## 2a. The calendar's month sentences are not in date order, and November lists five of eleven

- **October:** "Enspryng (RHHBY, Oct 15), Bepirovirsen (GSK, **Oct 26**), MR-141 (IRD/VTRS, **Oct 17**) and INO-3107 (INO, Oct 30)."
- **November:** "Ivonescimab… (SMMT, Nov 14), BBP-418 (BBIO, Nov 27), Giredestrant (RHHBY, Nov 30), Povetacicept (VRTX, Nov 30) and Aficamten (CYTK, **Nov 14**)."

November holds **eleven** pending rows: AGIO 11-01, BTAI 11-14, CYTK 11-14, SMMT 11-14, CAPR 11-22, SVRA 11-22, BBIO 11-27, GSK neladalkib (Nov, month), COGT 11-30, RHHBY 11-30, VRTX 11-30. The sentence names five and reads as complete. It is the sentence an AI answer will lift for "FDA decisions November 2026".

**Fix:** sort by date. Then either name every row, or say "including" and state the count ("Eleven FDA goal dates fall in November, including…"). Guard: the sentence's dates are non-decreasing, and its count equals the month's pending rows.

## 2b. Approvals still absent

The builder lists September approvals that have no page:

- AZN Tagrisso S-35 (09-14)
- LLY Onswik NME (09-23)
- Eisai Lenvima S-35 (09-24)
- MRK Welireg S-13 (09-24)
- LLY Olumiant S-9 (09-25)
- Teva Degevma (09-25)
- Azurity Lamlique (09-25)
- smaller sponsors

**Onswik is a novel approval** and belongs in the novel-approvals count. Backfill from the FDA letters, same method as 10-15.

---

# 3. SEO, BING AND AI CITATIONS

## 3a. Bing AI Performance, data to October 14: series high

| | Oct 9 | Oct 10 (Sat) | Oct 11 (Sun) | **Oct 12** | **Oct 13** | **Oct 14** |
|---|---|---|---|---|---|---|
| AI citations | 387 | 152 | 77 | **618** | **520** | **618** |
| Cited pages | 52 | 16 | 19 | 57 | 50 | 50 |

**618 is the highest day in the 60-day series** (previous high 553 on Sep 28), and it happened twice this week.

- Totals: **14.9K** citations (13.2K on 10-13) and **50 grounding queries** (46).
- `pdufa date`: **1.2K** citations at 22.95%.
- `pdufa dates`: 103 → **125** citations (35.82% share).
- Oncology-readouts query: 243 → 279, but its share fell 55.48% → **51.48%**. Someone else is being cited there now. Watch it next read.
- `fda calendar 2026`: 380 citations, 26.21% share. This is the fifth consecutive read with its share slipping.

## 3b. Bing web, data to October 14

- Totals: **892 clicks / 37.4K impressions / 2.39%**.
- **Oct 13: 1.0K impressions. Oct 14: 1.1K impressions and 24 clicks.** These are the two highest impression days in the series. The hub-first submission went live on 10-13.
- `fda approval decision biotech`: **477 impressions, 0 clicks**, position 6.86. The weekly page is indexed but still not winning this query. Its title is "FDA approval decisions this week: Oct 12 to Oct 18, 2026". Add "biotech" to the description and the h1 sub-line ("FDA approval decisions for biotech and pharma this week"); the query includes the word and our page does not.

## 3c. Moves, ranked by expected gain

1. **Section 0, today.** A decision page from the FDA-day rules, published within the hour, then Request indexing in Bing Webmaster. Every approval the site published within hours (Tecentriq, Rhapsido, Anktiva) is now in Bing's "this week" answer as a pdufa.bio citation.
2. **The month sentences (2a).** They are the most liftable text on `/calendar`, and November's is incomplete.
3. **Novel approval backfill (2b).** "FDA novel approvals 2026" counts are a citation magnet, and the count is only as good as its completeness.
4. **`fda calendar 2026` share is slipping.** The `/calendar` title is "PDUFA Dates 2026: FDA Decision Calendar, Updated Daily"; the query is "fda calendar 2026". Lead the title with "FDA Calendar 2026: PDUFA Dates and FDA Decisions, Updated Daily". The h1 can stay.
5. **The weekly page and "biotech" (3b).**

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **0** | **Publish Enspryng TED now** from the release with `decision_date_unsourced`, no margin, out of the statistic until Drugs@FDA posts. Then report whether the 06:00 Eastern scheduled run held the lead on its own | `/fda-decision/RHHBY-2026-10-15` 200; API row Decided; `/fda-decisions-today` and the weekly page list it; the note says "watcher held it at {UTC}" or "watcher did not see it, because…" |
| **1** | Calendar month sentences: date order, complete or counted | Oct and Nov sentences sorted; Nov states 11; guard 0 → 1 → 0 |
| **2** | September approvals backfill from FDA letters, Onswik first | Each page dated by Drugs@FDA; novel count updated |
| **3** | `/calendar` title leads with "FDA Calendar 2026"; weekly page description names biotech | Titles live; re-read share on the next audit |
| **4** | Next held lead: confirm only its own row freezes (the 10-15 fix) | Note records that the deploy went green while the lead was held |
| 5 | Saturday 10-17: IRD/VTRS phentolamine. Same runbook; a weekend goal date usually means a Friday action | Decision page same day as the record |
| 6 | Carried: `goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; 20 nct-mismatch readouts; 131 registry rows (recommend: watch list only); `build_sitemap.py --no-state` | |

---

# 5. BOTTOM LINE

**The data underneath is the best it has been.** Every decision page I tested matches the FDA's own record to the day. Four false "approvals" are gone. The timezone trap is closed at the job level instead of page by page. Search submission is ordered, and Bing answered with its two best impression days and its two best citation days.

**The surface is one release behind.** Enspryng was approved on its goal date, and at 2 a.m. the site still calls it Awaiting. That may be timing rather than a miss. The next scheduled run will say which, but the page should not wait for it.

---
*Site read from a browser client with `cache: 'reload'`, 2026-10-16 05:53 to 06:10 UTC, against build `7b0456259`. Genentech release read on gene.com. openFDA `drugsfda` read live for BLA 761149, NDA 213411, BLA 125522, NDA 219007, NDA 214998 and NDA 218436. Bing Webmaster AI Performance and Search Performance (data to 2026-10-14) and Bing SERPs read live. Not investment advice.*
