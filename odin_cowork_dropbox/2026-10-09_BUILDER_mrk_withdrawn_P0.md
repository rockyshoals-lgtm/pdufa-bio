# Builder: MRK I-DXd is "Withdrawn"; the watchers now hear withdrawals, extensions and refusals to file
**2026-10-09, written ~23:30 Pacific on 10-08 = 02:30 Eastern on 10-09. CI times UTC.** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

Answers the 10-08 audit, order items 0, 1, 2 and the Enspryng/sweep facts for item 5.

## 0. P0: ifinatamab deruxtecan

**Verified** from merck.com (primary source): "Ifinatamab Deruxtecan Biologics License Application for Certain Patients with Previously Treated Extensive-Stage Small Cell Lung Cancer Voluntarily Withdrawn".
* Dated September 25, 2026, 4:30 pm EDT; Business Wire newsitemid 20260925284187.
* The release says: "The decision to withdraw the BLA is based on discussions with the U.S. Food and Drug Administration (FDA) that data supporting the application, including from the IDeate-Lung01 Phase 2 trial, do not satisfy requirements needed to support an accelerated approval for the proposed indication."

**Data** (`apply_1009_mrk_withdrawn.py`):
* `pdufa_mrk_2026-10-10` now has `st: "Withdrawn"`, a new status, served by the API as `status: "Withdrawn"`.
* It has no `dcd` or `oc`, so the API's `decision_date` is null. `days_to_decision` was dropped.
* New fields: `withdrawn_date` 2026-09-25, `withdrawn_by`, `withdrawn_source`, `withdrawn_source_url` (the Merck release) and `withdrawn_quote`.
* The goal date 2026-10-10 and its 10-Q source are kept.
* `url` is now `/pdufa/MRK-ifinatamab-deruxtecan`.
* `_lib.mjs` exposes `withdrawn_date`, `withdrawn_source`, `withdrawn_source_url` and `withdrawn_quote`.
* The row also left `api/data.js` SLATE (the homepage forward list), which held 40 rows and now holds 39.

**One rule everywhere:** a row is closed when it is Decided **or Withdrawn**. The pending selectors were patched in 17 builders:
* homepage freshness, `build_freshness_stamp` (next_*), event-page generator, today page, condition pages, hub FAQ (both counts), screener, both calendar-window normalisers;
* moved-date refresh, `/pdufa/{TICKER}` index, calendar reconcile, goal-date-passed, ticker hubs, drug pages, `/fda-this-month`;
* the CI slate sweep (`build_slate_from_crawl.py --sweep-only`), which now also drops Withdrawn rows.

A withdrawal is not a decision. It never enters the timing statistic, which still requires Decided, and stays at 31.

**Surfaces:**
* **`build_withdrawn_pages.py`** (new; in CI before breadcrumbs, and in the local chain twice):
  * Rewrites `/pdufa/MRK-ifinatamab-deruxtecan`. Title: "MRK ifinatamab deruxtecan BLA withdrawn Sep 25, 2026, before Oct 10, 2026 PDUFA date | pdufa.bio".
  * Fact-first lede: who withdrew it, when, fifteen days before the goal date, and why, quoted and linked.
  * Key-facts card and a 4-question FAQ plus FAQPage, led by "Was ifinatamab deruxtecan approved?".
  * **No Event schema, no countdown, no run-up.**
  * Marks the calendar rows `data-dec data-wd`, labelled "Withdrawn Sep 25, 2026".
* **`/fda-this-month`:** a new "Withdrawn before a decision" section. The row is out of "Still ahead" and out of every count.
* **`/pdufa/MRK`** reads "MRK has no FDA decision date ahead … 1 application was withdrawn".
  * `build_pdufa_ticker_index.py` now rebuilds the generated index for tickers with **no** upcoming row. Before, those pages froze on their last state.
  * This also refreshed 11 other stale index pages.
* **`/drug/ifinatamab-deruxtecan`:** "Application withdrawn · Sep 25, 2026", and the indication is no longer listed as "under review".
* **`.ics` feeds** (static and API): the event title says "WITHDRAWN 2026-09-25 (no FDA decision)".

**Guard `tests/test_no_withdrawn_upcoming.py`** checks every Withdrawn row against:
* `build-info.json` next_*, the SLATE and the homepage board;
* the calendar markers, the `/fda-this-month` "Still ahead" section, and the event-page marker with no Event schema;
* any published sentence that names the drug next to pending-tense language.

Proof on the rendered output:
* **12** failures before the rebuild: the run while I was building found the board, build-info, `/fda-this-month`, `/pdufa/MRK`, `/ticker/MRK`, the drug page and the condition page all still naming the decision.
* **0** after.
* Planted and reverted: see section 4.

## 1. The watchers hear the other outcomes

`watch_sponsor_newswire.py` now has `OTHER_OUTCOME` and `outcome_kind()`. It recognises **withdrawal**, **goal-date extension or major amendment**, and **refuse to file**, but only in a headline that names an application.
* Such a headline is a lead whatever else it says.
* The lead text carries its kind, and leads are quarantined per row as before.
* `watch_edgar_8k.py` uses the same classifier sentence by sentence.

Guard `tests/test_watchers_hear_withdrawals.py`:
* The real Merck headline, planted against every armed row plus an Upcoming copy of the MRK row, arms **only** `pdufa_mrk_2026-10-10`.
* Extension, major-amendment and refuse-to-file headlines are classified.
* "Merck Withdraws 2026 Revenue Guidance Range" and two readout headlines are ignored.
* Proved: OK before; FAIL ("armed nothing") with the classifier switched off; OK again.

## 2. The two silent large caps

`_sponsor_feeds.json` has a dated note for each. Tried on 2026-10-09 from the builder machine with the watcher User-Agent:

* **MRK**
  * `merck.com/feed/` and `/media/news/feed/` return an RSS shell with 0 items; `/news/feed/` returns 404; `wp-json/wp/v2/posts` returns `[]`.
  * **`merck.com/media/news/` (HTML) returns 200 with dated headlines.** It carried the 09-25 withdrawal.
* **RHHBY**
  * `gene.com/rss/press-releases.xml` returns 404.
  * **`gene.com/media/press-releases` (HTML table with data-date) returns 200.** It carried the 10-08 Tecentriq approval.
* The watcher now reads `html:` feed entries with a parser per host. Tested from the builder machine:
  * Merck: 10 items, and the 09-25 item is classified "withdrawal".
  * Genentech: 524 items. Old ones fall outside the 10-day window.
* Roche's own roche.com releases are still uncovered.
* Untested: whether the GitHub runner's IP gets the same 200. The watcher prints "feed unreachable" if it does not, and the next CI log will show it.

**Correction to my 10-08 note.** I wrote that Genentech had posted no Tecentriq approval release. It had: gene.com, 2026-10-08, "FDA Approves Genentech's Tecentriq in Combination With a Fluoropyrimidine and Oxaliplatin …". It is now the row's `announcement_url` (`apply_1009_tecentriq_release.py`). The decision source remains the FDA notice.

## Sweep: 17 upcoming rows, Oct 15 to Nov 30

Read 2026-10-09 (Eastern), sponsor newsrooms and EDGAR only (8-Ks and 10-Qs; GSK 6-Ks). Result: **no withdrawal, no refusal to file, no decision, and no new extension. Every goal date stands.**

| Row | Status | Read |
|---|---|---|
| RHHBY Enspryng TED 10-15 | stands | gene.com/media/press-releases; 09-09 MOGAD release still refers to the TED review |
| IRD/VTRS MR-141 10-17 | stands | ir.opusgtx.com, newsroom.viatris.com; IRD 10-Q 08-06 "PDUFA action date of October 17, 2026" |
| GSK bepirovirsen 10-26 | stands | gsk.com press releases, GSK 6-K 07-28 "decision expected from the FDA by 26 October 2026", ir.ionis.com |
| INO INO-3107 10-30 | stands | ir.inovio.com; 8-K 08-12 "toward a PDUFA target action date of October 30, 2026" |
| AGIO mitapivat 11-01 | stands | investor.agios.com; 8-K 07-30 |
| BTAI IGALMI 11-14 | stands; **sponsor in Chapter 11 since 08-27, asset sale to Teva** | ir.bioxceltherapeutics.com 08-28: "continuing to support the sNDA with a PDUFA date of November 14, 2026" |
| CYTK aficamten 11-14 | stands | ir.cytokinetics.com; 10-Q 08-06 |
| SMMT ivonescimab 11-14 | stands | smmttx.com; 8-K 09-28 repeats Nov 14 |
| NVCR TTFields Q4 | stands | investor.novocure.com; release 07-23 "(Q4 2026)" |
| CAPR deramiocel | extended 08-24 to **11-22** (major amendment); no further change | capricor.com 10-05 "PDUFA Target Action Date November 22, 2026" |
| SVRA MOLBREEVI 11-22 | stands (April major amendment) | 10-Q 08-11 |
| BBIO BBP-418 11-27 | stands | investor.bridgebio.com 10-05 |
| NUVL neladalkib 11-27 | stands; **sponsor now GSK** (acquired 07-15, Form 15 07-27) | GSK 6-K 07-28: "PDUFA date anticipated in November 2026". **No primary source read gives the 27th.** Ruling needed: keep the Royalty Pharma-quoted day or widen the row to the month. |
| COGT bezuclastinib GIST 11-30 | stands | investors.cogentbio.com; release 08-10 |
| REGN cemdisiran Nov | stands | investor.regeneron.com; release 07-30 |
| RHHBY giredestrant 11-30 | stands | gene.com 09-30: "PDUFA goal date … November 30, 2026" |
| VRTX povetacicept 11-30 | stands | news.vrtx.com; release 08-03 |

**Enspryng (item 5 source facts),** verbatim from Genentech's June 29, 2026 release:
* "For the primary endpoint of proptosis (bulging eyes) response at week 24, 53% of patients treated with Enspryng in SatraGO-2 achieved a proptosis reduction compared to 23% of patients treated with placebo, meeting statistical significance."
* "Similarly, in the SatraGO-1 trial, 49% of patients achieved a proptosis response compared to 31% in the placebo arm. While this numerical improvement did not meet statistical significance, …"

The event page copy is not yet written.

## Not done in this pass

* Order items 3, 4, 6 and 7: the UX order (stylesheet first), the weekly decisions page, the rulings, and the NOINDEX list.
* Item 5: the copy on `/pdufa/RHHBY-enspryng`.
* This was the P0 pass.

## Live check after the first push, and three leaks fixed (appended ~23:55 Pacific = 02:55 Eastern)

Commit `c3eb05f23`, CI run 37894041908, green.

**Live and correct:**
* build-info: next RHHBY 2026-10-15, `held_since` null.
* API: `status: "Withdrawn"`.
* Event page: withdrawn title and lede, no Event schema.
* Homepage board: no I-DXd.
* `/fda-this-month`: the withdrawn section.
* `/drug/ifinatamab-deruxtecan`: "Application withdrawn".

**Still wrong live, and my guard missed two of the three. Retracting the "0" it reported:**
1. **`/calendar` month sentence:** "In October the FDA is due to decide on Ifinatamab deruxtecan (MRK, Oct 10)".
   * Cause: in CI, `inject_calendar_explainer` runs at the "mark decided" step, long before `build_withdrawn_pages`, so the row was not yet marked.
   * Fix: `build_withdrawn_pages.py` now also runs immediately after `mark_calendar_decided` (CI and local).
2. **`/ticker/MRK` FAQ:** "The next catalyst for Merck & Co., Inc. is Ifinatamab deruxtecan (I-DXd) (PDUFA)".
   * Cause: `build_ticker_faq.py` (CI only) filtered `not in ("decided",)`, a form my search missed.
   * Fix: patched to also exclude withdrawn.
3. **API `days_to_decision: 1`:** a CI enrichment step re-stamps it.
   * Fix: `_lib.mjs` serves `days_to_decision: null` for any Withdrawn or Decided row.

**Guard tightened:**
* It now checks a window around every mention instead of splitting sentences. "Merck & Co., Inc." had split the FAQ sentence.
* Added vocabulary: "due to decide", "expected to decide", "decision is expected", "days to decision".
* Proved on the live pages: 0 on the local rebuild → **planted the live `/ticker/MRK` and `/calendar` HTML: FAIL 2** → reverted: 0.
