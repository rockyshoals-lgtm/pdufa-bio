# Audit: the "next FDA decision" on our homepage was withdrawn 13 days ago, and I missed it twice
**2026-10-08, measured 23:06 to 23:25 Eastern = 2026-10-09 03:06 to 03:25 UTC (Thursday night).** *Per RULE 1 every time carries its zone.*
**Live build `64c4368df`, generated 2026-10-09T01:55:34Z (21:55 Eastern). `held_since` null, `held_leads` []. API 460 rows, `as_of_eastern` 2026-10-08, `data_built_at` matches the build.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. P0: MRK ifinatamab deruxtecan, 2026-10-10, is not a pending decision

**The site says, tonight, on the homepage strip, the home "Next FDA decisions" list, `/build-info.json` (`next_ticker: MRK, next_days: 2`), `/pdufa/MRK-ifinatamab-deruxtecan`, and the API row `pdufa_mrk_2026-10-10` (status Upcoming, `days_to_decision: 2`): the FDA decides on I-DXd for ES-SCLC on Saturday.**

**Primary source:** Merck news release, **September 25, 2026, 4:30 pm EDT**, "Ifinatamab Deruxtecan Biologics License Application for Certain Patients with Previously Treated Extensive-Stage Small Cell Lung Cancer Voluntarily Withdrawn." Quote: "The decision to withdraw the BLA is based on discussions with the U.S. Food and Drug Administration (FDA) that data supporting the application, including from the IDeate-Lung01 Phase 2 trial, do not satisfy requirements needed to support an accelerated approval for the proposed indication." Daiichi Sankyo issued the same release. Fierce (09-28), Oncozine (09-27), OncoDaily (09-26), allsci (09-28) all carried it. A Bing News headline three days old reads "...As MRK Withdraws Application".
https://www.merck.com/news/ifinatamab-deruxtecan-biologics-license-application-for-certain-patients-with-previously-treated-extensive-stage-small-cell-lung-cancer-voluntarily-withdrawn/

**Thirteen days.** The withdrawal landed on the Friday before the six-day site freeze. The freeze was diagnosed and lifted; this was never seen. The row's source is the Merck 10-Q of 2026-05-04, and the page's `article:modified_time` is 2026-09-18.

## Why nothing caught it

1. **No watcher has the word.** `watch_sponsor_newswire.py` `DECISION` regex matches `approv*`, `complete response`, `CRL`, `accelerated approval`, `clearance`. Not `withdraw*`, not `extension`/`extended` (PDUFA goal extensions, which Capricor and Praxis both announced this year), not `major amendment`, not `refuse to file`. The EDGAR 8-K and FDA-feed watchers cannot catch a withdrawal at all: the FDA never announces one, and a large cap does not file an 8-K for it.
2. **MRK has no newswire feed.** `_sponsor_feeds.json` note (09-27): "merck.com refuses non-browser clients... Covered by the FDA feeds and EDGAR passes only." So the only sponsor that could have told us is the one we are not listening to. RHHBY carries the same note. These are our two largest-cap upcoming rows.
3. **My own misses.** The 10-04 and 10-06 audits each ran the past-due, precision, conference and `source_url` invariants and declared currency clean. None of those invariants can see a row that is current, sourced, day-precise and **no longer exists**. I searched Bing for Tecentriq both nights and never searched the row behind it. The audit's currency section needs a check I was not running: for every upcoming row inside 30 days, search the sponsor's name plus the drug plus "withdraw OR extension OR amendment" and read the first page. I ran it tonight for the next three rows after MRK (Enspryng 10-15, bepirovirsen 10-26, INO-3107 10-30): all three still stand on current sponsor or trade coverage. I did not run it for the fourteen rows from 11-01 to 11-30.

## What to publish

The row is a fact-only site's best kind of row: a sourced goal date, then a sourced withdrawal, both with dates. Treat it like a decision, not a deletion:

- Status **Withdrawn** (new status, API-visible), `decision_date` null, new `withdrawn_date 2026-09-25`, `withdrawn_source_url` the Merck release. Keep the goal date and its 10-Q source. The row must leave Upcoming, leave the `next_*` computation, and leave the homepage strip tonight.
- `/pdufa/MRK-ifinatamab-deruxtecan` lede: "Merck and Daiichi Sankyo withdrew the BLA on September 25, 2026, fifteen days before its October 10, 2026 goal date, after FDA discussions that the IDeate-Lung01 data do not support accelerated approval." Title "MRK ifinatamab deruxtecan BLA withdrawn Sep 25, 2026, before Oct 10 PDUFA date | pdufa.bio". FAQ: "Was ifinatamab deruxtecan approved?" answered with the withdrawal.
- `/calendar`, `/fda-this-month`, `/decisions`, `/ticker/MRK`, `/drug/ifinatamab-deruxtecan`: show the row under its own label. A withdrawn application is neither Approved nor CRL; it is not in the 31-decision timing statistic and must not enter it.
- Guard: `test_no_withdrawn_upcoming.py`, a withdrawn id can never render as Upcoming on any surface, 0 → planted 1 → 0.

---

# 1. CURRENCY, everything else: CLEAN

| Check | Live |
|---|---|
| Day-precision PDUFAs past goal and undecided | **0** |
| Rows at non-day precision carrying a `date` | **0** |
| Conferences mislabelled against the Eastern date | **0** |
| Upcoming PDUFAs with `source_url` | 38 of 41 (AZN Ultomiris, NVO CagriSema, NVO Mim8 remain unbacked) |
| Tecentriq | API row `pdufa_rhhby_2026-10-09` Decided, `decision_date` and `fda_action_date` 2026-10-08, goal 2026-10-09; `/fda-decision/RHHBY-2026-10-08` 200, title "Approved Oct 8, 2026, 1 Day Early", fact-first description, FAQPage present; `/pdufa/RHHBY-tecentriq` reads "decided this application on October 8, 2026, 1 day before its October 9, 2026 goal date" |
| Timing statistic | **31: 20 early / 10 on the day / 1 late** on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing`; median "2 days before the goal date" |
| Quarantine | lifted; both watchers 0 unreviewed leads in CI |

**Tecentriq verified against the builder's note and the FDA.** The FDA oncology notification is dated October 8, 2026 and Bing's answer box carries its first sentence verbatim. We are not in the Tecentriq answer box (the FDA is, as it should be) and not on the first page for "tecentriq fda approval colon cancer october 2026": fda.gov, morningglorysciences (3 hours old), CURE, Oncology Nursing News. Our page is nine hours old at the time of reading; re-test Friday.

The builder's two fixes are right. Judging margins per row rather than per ticker was a real defect: a ticker with one `goal_unsourced` decision and one fully sourced decision would otherwise have the sourced page gated by the unsourced one.

---

# 2. UX: the 10-04 order is now four days unworked

Verified from the browser with `cache: 'reload'`, all unchanged from 10-04 and 10-06:

| Item | Live state, 10-08 |
|---|---|
| 2. `/patent-cliff/exclusivity` stylesheet | first `<style>` block **373 characters** (`/patent-cliff`: 1,351). Renders unstyled on a phone |
| 3. `/adcomm` lede | "This page lists **2** FDA advisory committee meetings covering July 2026" above 187 notices |
| 4. RVMD 13F block | no `<table>` within 600 characters of "Baker Bros"; still a paragraph |
| 6. Freshness strip | "Updated October 8, 2026 · next FDA decision on the calendar..." with no "Page updated" / "Data as of" split |

Items 7 to 10 are not addressed in any builder note. Three builder notes have landed since the order (10-04 Jaypirca, 10-08 Tecentriq, plus CI rebuilds); each worked a decision, none worked the order. Decisions come first and that is correct, but the exclusivity page has now been a raw link list on phones for a week.

---

# 3. SEO, BING AND AI CITATIONS

## 3a. Bing AI Performance, data to October 6

| | Oct 1 | Oct 2 | Oct 3 (Sat) | Oct 4 (Sun) | **Oct 5** | **Oct 6** |
|---|---|---|---|---|---|---|
| AI citations | 403 | 225 | 96 | 50 | **384** | **337** |
| Cited pages | 41 | 36 | 13 | 10 | **40** | **37** |

Totals 11.6K citations (10.9K on 10-06), 24 average cited pages, **44 grounding queries (40)**. The weekday series is back at its pre-freeze level.

**`pdufa date` finally moved**: 863 → **958** citations, share 22.92% → 22.87%. The row had been frozen for four reads; it is live again, and the share is flat, not falling. `fda calendar 2026` 362 → 371, share 26.97% → **26.58%** (fourth consecutive drift down). `pdufa dates` 93 → 98 (36.47% → 35.64%).

**Four new grounding queries, all from the FDA-record work:** `fda approval letters` 18 citations (13.04% share), `fda complete response letter database` 18 (15.79%), `mim8 approval` 30 (20.83%), and `09/28/2026 - approval completed` 60 citations at **50.00% share**, which is a Copilot user asking what was approved on September 28 and getting us half the time (JUVMO and Emcitate). That last row is the clearest evidence yet that dated decision pages are what the AI layer wants.

## 3b. Bing Search Performance, data to October 6

Totals 762 clicks, 31.1K impressions, 2.45% CTR. Oct 5: 21 clicks / 817 impressions. **Oct 6: 26 clicks / 958 impressions**, the second-highest click day in the 60-day series (28 on Sep 9).

| Keyword | Impressions | Clicks | Position | 10-06 |
|---|---|---|---|---|
| pdufa | 2.0K | 9 | 6.16 | |
| pdufa date | 709 | 9 | 5.16 | |
| **fda approval decision biotech** | **250** | **0** | 6.76 | 172 / 0 |
| pdufa calendar | 146 | 20 (13.7%) | 4.02 | |
| fda pdufa calendar | 15 | 7 (46.7%) | 3.73 | |

`fda approval decision biotech` is now 250 impressions at 0 clicks, up 45% in two days. **Tonight's SERP answers the 10-04 question.** Bing shows an AI answer box compiled from rttnews, Yahoo and Asianet; organic 1 MarketBeat, 2 RTTNews, 3 biopharmawatch; pdufa.bio is not on page one as rendered (position 6.76 is an average across variants). The answer box is stale: it lists Winrevair "PDUFA Sept 21, 2026" and Camzyos "Sept 30, 2026" under "Major Upcoming FDA Decisions" on October 8. The query wants a page titled and led as "FDA approval decisions this week: {dates}" with the week's decided and pending rows, each dated. `/fda-decisions-today` and `/fda-this-month` are adjacent; neither is titled for the query. One page, rebuilt daily, would take this.

Bing Webmaster also flags "Some URLs are not getting indexed due to robots NOINDEX meta tags." If those are the Pro or utility pages, fine; the builder should list which URLs carry NOINDEX and confirm each is intended.

## 3c. Google Search Console, 28 days to October 6

29 clicks, 3.11K impressions, 0.9% CTR, position **7.3** (7.2 on 10-04). Top queries: brand 9 clicks, denecimig 2, juvmo pdufa 1 / 13 impressions, `pdufa date` 0 / 15. Flat; nothing to act on this week.

## 3d. Competitors, as seen tonight

- **GSK bepirovirsen (10-26): we hold the Bing answer box** with the FAQ text. Note the box quotes "Dates are company/FDA-sourced and can slip. Verify against primary filings." That sentence is doing work and should stay.
- **Enspryng TED (10-15): trialfriend.com (Oct 2 post) and ophthalmologytimes hold the answer box**; we are absent. Their copy names SatraGO-1 and SatraGO-2 with the response rates. Our page has the date and the Genentech source. The event page should carry the two trial names and the primary endpoint result as stated in Genentech's June 29 release, which is already the row's source.
- **INO-3107 (10-30): bioradar.io** is new, published one day ago, title "INO-3107 PDUFA Date (Oct 30, 2026): What Inovio's Filings Show." Filings-first copy aimed at exactly our position. novapharmanews and biopharmsignal also ahead. Our `/pdufa/INO` and `/pdufa/INO-...` both appear lower on the page.
- **MRK (10-10): we hold the Bing answer box for "ifinatamab deruxtecan pdufa date october 10 2026."** The box reads "MRK's FDA PDUFA date is Oct 10 2026... See the T-120 run-up, cap-tier." That is the P0 above, cited by Bing's AI layer under our name. Fixing the row fixes the box on the next crawl; until then we are the source of a wrong answer.

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **0** | **MRK ifinatamab: Withdrawn status, dated and sourced, off every upcoming surface, out of `next_*`.** Then sweep the 16 other upcoming rows through 11-30 for withdrawals and goal extensions by reading each sponsor's newsroom, and record the check date per row | `/build-info.json` `next_ticker` RHHBY 10-15; API row status Withdrawn with `withdrawn_date 2026-09-25`; guard 0 → 1 → 0; a note listing the 16 rows with the newsroom URL read and date read |
| **1** | **Teach the watchers the other three outcomes**: `withdraw*`, `extension`/`extended`/`major amendment`, `refuse to file`. Each becomes a quarantined lead for its own row, like an approval | Planted Merck headline arms the MRK row and only the MRK row |
| **2** | **The two silent large caps.** MRK and RHHBY have no feed. Merck's release page serves a browser UA; the watcher sends a UA that names pdufa.bio. Try the Business Wire feed for Merck (the release carries a BW newsitemid) and gene.com's press-release listing for Roche, and record what each refuses | `_sponsor_feeds.json` MRK and RHHBY carry a working feed or a dated note of what was tried |
| **3** | **Work the 10-04 UX order, items 2 to 10.** Stylesheet first | Phone render of `/patent-cliff/exclusivity` shows header and headline; `/adcomm` states one count; RVMD 13F is a headed table |
| **4** | **`fda approval decision biotech` (250 impressions, 0 clicks):** one page titled "FDA approval decisions this week" rebuilt daily, dated rows, decided and pending | Page live, in the sitemap, pinged; impressions on the query convert above 0 within two weeks |
| **5** | **Enspryng before 10-15**: SatraGO-1 and SatraGO-2 named with the primary-endpoint results as Genentech states them, on `/pdufa/RHHBY-enspryng` | Page carries both trial names and the source sentence |
| 6 | Rulings carried: `goal_date_held:false` on `goal_unsourced` rows; Jaypirca SUPPL-5 letter date; RXC-005 / LY3527727 aliases | |
| 7 | NOINDEX list from Bing Webmaster, each URL confirmed intended | |
| 8 | David: SMTP secrets; Google Drive exclusion; the three unbacked rows (AZN Ultomiris, NVO CagriSema, NVO Mim8) | |

---

# 5. BOTTOM LINE

**Tecentriq was published within hours, dated from the FDA, one row per decision, with the statistic consistent on every surface. That is the system working.**

**The system has a blind spot the size of a withdrawn BLA.** Every watcher listens for approvals and CRLs. None listens for the third and fourth outcomes, withdrawal and goal extension, and the two largest sponsors on the calendar have no newswire feed at all. The result is that for thirteen days, including tonight, the homepage names a decision that will not happen, and Bing's AI answer repeats it under our name. I audited currency twice in that window and called it clean both times, because my checks test whether a row is late, not whether it is still real. That check is now in the audit, and item 0 is the work.

**Search is up:** best weekday citations since the freeze, four new grounding queries from the FDA-record pages, `pdufa date` moving again, and a 50% citation share on "what was approved on 09/28". The next gains are the 250-impression zero-click query and the two answer boxes (Enspryng, INO-3107) that competitors hold with trial-level copy we already have in our sources.

---
*Site read from a browser client with `cache: 'reload'`, 2026-10-09 03:06 to 03:25 UTC, against build `64c4368df`. Merck release read from merck.com. Bing Webmaster AI Performance and Search Performance (data to 2026-10-06) and Google Search Console (28 days to 2026-10-06) read live. Bing SERPs for Tecentriq, ifinatamab, Enspryng, bepirovirsen, INO-3107 and "fda approval decision biotech" read live. Not investment advice.*
