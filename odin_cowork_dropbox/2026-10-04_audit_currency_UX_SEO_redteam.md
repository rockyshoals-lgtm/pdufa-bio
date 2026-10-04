# Audit: the site is current again, the stall cost less than feared, and the new pages need a reader's eye more than a verifier's
**2026-10-04, measured 16:42 to 17:40 UTC = 12:42 to 13:40 Eastern (Sunday).** *Per RULE 1 every time carries its zone.*
**Live build `1e3a9bacf`, generated 2026-10-04T16:35:21Z. `held_since` null, `held_leads` empty. API 459 rows.**
*Facts and build mechanics only. Not investment advice.*

**A method note first.** `web_fetch` returned yesterday's `/build-info.json` byte for byte this morning, including `served_at: 2026-10-03T18:12:27Z`, which cannot be a live response. The tool caches within a session. Every figure below was read from a browser client with `cache: 'reload'`, and the two new pages were read **rendered on a 375-pixel phone viewport**, not as text. Two of this audit's findings were only visible that way.

---

# 1. CURRENCY: CLEAN, AND THE STATISTIC MOVED CORRECTLY

| Check | Live |
|---|---|
| Build | today, 16:35 UTC; three green CI runs on 10-03 and one today |
| Held leads | none |
| Day-precision PDUFAs past goal and undecided | **0** |
| Rows with a date at non-day precision | **0** |
| Conferences mislabelled against today's Eastern date | **0** (AACR-PANC, ASTRO, EASD now Ended; WMS In progress) |
| Upcoming PDUFAs with `source_url` | 39 of 42; the three without are AZN Ultomiris, NVO CagriSema, NVO Mim8 |
| Next decision | RHHBY Tecentriq, 2026-10-09, `next_days: 5`, correct for Oct 4 Eastern |
| JUVMO | `Decided / Approved`, `fda_action_date 2026-09-25`, announcement 09-28, `goal_unsourced` |

**The timing statistic is now 30: 19 early / 10 on the day / 1 late**, on `/calendar`, `/learn` and the study page, and the study says "30 of 30 action dates" from FDA records. Atebrioz re-entered on its own when Drugs@FDA posted NDA 221198 (approved Fri 09-25 against a Sat 09-26 goal from Mirum's 8-K, 1 day early). That is the 09-26 re-check rule working without a hand on it, which is the behaviour the TLX case was supposed to produce.

**I checked that re-entry against the rule, not just the arithmetic.** Both dates come from documents that state them (FDA letter, sponsor 8-K), so the row qualifies. 19 + 10 + 1 = 30 ✓.

**One currency gap remains, and it is a day old.** The FDA approved **Jaypirca (pirtobrutinib) for first-line CLL/SLL on 2026-10-02** (FDA "What's New: Drugs", 15:31 Eastern). The builder flagged it for a ruling. `/fda-decision/LLY-2026-10-02` **404s**. Bing's answer box for it already cites lilly.com, targetedonc.com and ascopost.com; we are absent. The ruling is simple: it is an FDA-dated efficacy supplement on a tracked sponsor, exactly Gazyva's shape, so publish it the same way, `goal_unsourced`, no margin.

---

# 2. RED TEAM OF THE 10-03 SHIPMENT

The builder shipped 25 items in two passes with 128 local guards. The verifiers passed 15 of 15 and 16 of 16. I went looking for what a verifier cannot see.

## 2a. Verified correct, first-hand

- **13F block, RVMD.** The page states Baker Bros. Advisors reported **11,443,357 shares of RVMD ($2.14 billion)**. I opened the filing: accession `0001104659-26-097191`, `infotable.xml`, period 2026-06-30, filed 2026-08-14: `Revolution Medicines, Inc. ... sshPrnamt 11443357 ... value 2143111899`. **Exact.**
- **JUVMO decision page** reads, in order: APPROVED badge, "JUVMO (tavapadon) was approved by the FDA on September 25, 2026 for Parkinson's disease in adults, the 43rd novel drug approval of 2026 on the FDA's Novel Drug Approvals list," then AbbVie's own framing attributed to AbbVie, then the key facts with **FDA decision date 2026-09-25 and Announced 2026-09-28 on separate lines**, then "FDA record of the action" with the NDA 220415 letter linked. That is the best decision page on the site and the template every other one should converge on.
- **Exclusivity cliff**: 861 table rows against "855" in the title (the difference is header and group rows; the data count matches the builder's 858 minus three that ended Oct 1 to 3). First row: Zoryve NPP exclusivity ends **Oct 5, 2026**, tomorrow. The "not a generic launch" disclosure is present.
- **Gazyva** published with its own calendar row; Tecentriq still pending; the lupus page unbannered.

## 2b. Defects found, ranked

### P0 (UX): `/patent-cliff/exclusivity` renders with no stylesheet

On a phone the page opens as a **raw list of nav links a full screen tall** before the headline appears. I diagnosed it rather than guessed: every page inlines its CSS in two `<style>` blocks; on `/patent-cliff` the first block is **1,351 characters**, on `/patent-cliff/exclusivity` it is **373**. The new template shipped a stub stylesheet with no nav, header or table rules. `/fda-approval-letters` also carries only two inline blocks and no `fonts.css` link; it needs the same check. **Guard:** every indexable page's first `<style>` block must contain the shared nav rules (match on a known selector), proved by planting the stub.

### P1 (UX, accuracy of presentation): `/adcomm` contradicts itself on one screen

The lede says *"This page lists 2 FDA advisory committee meetings covering July 2026."* The FAQ says *"2 advisory committee meetings are documented."* Then, **below the FAQ**, a section headed "187 Federal Register notices" lists meetings from 2020 to 2026, including **the same two July CTGTAC meetings** (FR 2026-13096 for Jul 29, FR 2026-13810 for Jul 30) that appear with votes at the top, unjoined. The page title and meta description still describe an "upcoming" calendar. A reader sees a page that says two, then shows 187. Fix: one count in the lede ("187 notices since 2020; 2 with hand-sourced votes"), the FR notice row linked from each voted meeting, the history above the FAQ, and the title and description rewritten for what the page now is. **Guard:** no page states two different counts of the same thing.

### P1 (UX): the 13F block is the right data in the wrong shape

One paragraph, five funds, ten numbers, pinned under the "Primary source" line at the very bottom of the page, with no heading. On a phone it is a wall. The caveat sentence ("13F reports list long positions at quarter end, are due 45 days later, and show no short positions or later trades") is exactly right and should stay. Render it as a small table under a heading ("Specialist biotech funds holding RVMD, 13F for the quarter ended June 30, 2026"), fund / shares / value, with the caveat beneath and the filing linked per row. **Two data risks the filing itself shows:** Baker Bros' table includes a **Celcuity 2.75% convertible note** (`sshPrnamtType PRN`) and a **Surrozen warrant**. The builder says only long common positions are used; the guard should assert `sshPrnamtType == SH` and a `titleOfClass` of common stock on every published row, so a note or warrant can never be reported as shares.

### P1 (SEO): the page now holds 81 FDA actions and is titled "38"

Not quite: `/fda-approval-letters` title read "38 FDA Decisions" when I opened it yesterday and the body now says 81 after the archive dating. I did not re-read the title today and will not assert it is stale; the builder should confirm the title, h1 and the Dataset schema all carry the live count from one owner, the same cure as the run-up study size.

### P2 (UX, every page): the freshness strip now reads three dates

"Updated October 3, 2026 · next FDA decision in 5 days RHHBY · data rebuilt Oct 4, 12:35 PM ET." The first and third disagree by a day, correctly (page content changed Oct 3; data rebuilt Oct 4), but a reader cannot know that convention. Rename the first to "Page updated" and the third to "Data as of", or drop the page date on pages whose content is generated.

### P2 (UX): the chart caption contradicts the key facts

JUVMO's run-up caption says "FDA decision 9/28/26" and marks the chart "PDUFA 9/28/26". The key facts say the FDA decided on 9/25 and AbbVie announced on 9/28. The chart is keyed on the announcement day because that is when the price could react, which is defensible, but the caption should say "announced 9/28/26 (FDA action 9/25/26)". **Guard:** no caption may call the announcement day the "FDA decision" when `fda_action_date` differs.

### P2 (UX): the floating "Search ⌘K" pill covers content on mobile

It sits over the bottom-right corner on every screenshot, overlapping the primary-source link on the JUVMO page and the table header on `/adcomm`. ⌘K is a desktop affordance; on a phone it should collapse to an icon or hide on scroll.

### P2 (accuracy of description): exclusivity lede

"855 FDA regulatory exclusivities on brand-name drugs (NDAs) end between October 4, 2026 and December 31, 2031." The table's first row ends Oct 5. Fine today; tomorrow the sentence is stale unless the start date is computed at build. Confirm it is.

---

# 3. SEO, BING AND AI CITATIONS

## 3a. The stall's cost, measured

Bing data now runs through **October 2**, the first two days the site was frozen with no update at all (Sept 28 to 30 were at most three days stale).

| | Sept 28 | Sept 29 | Sept 30 | Oct 1 | Oct 2 |
|---|---|---|---|---|---|
| AI citations | 553 | 356 | 256 | **403** | **225** |
| Avg cited pages | 58 | 53 | 42 | 41 | 36 |
| Web impressions | 827 | 843 | 774 | **905** | 587 |
| Web clicks | 20 | 20 | 19 | 16 | 18 |

**No measurable penalty.** Oct 1 was a strong day on both series. Oct 2 is softer, and Friday Oct 2 against Friday Sept 25 (253 citations, 601 impressions) is roughly flat. The weekend data (Oct 3 to 4) is not in yet. The frozen pages were still accurate for everything except JUVMO, and search engines reward accuracy over churn on a six-day horizon. **That is reassuring and it should not be over-read:** the cost of the stall was the JUVMO answer box and the Gazyva and Jaypirca pages that did not exist, which the console cannot see.

Totals: AI citations **10.8K** (from 10.1K), average cited pages 24, grounding queries **40** (from 38). Bing web **708 clicks, 28.9K impressions, 2.45% CTR**.

## 3b. Movers in the keyword table

- **`fda approval decision biotech`: 36 → 166 impressions in one week, position 7.99, 0 clicks.** That is a new head-term-class query arriving at the bottom of page one and converting nothing. Worth a look at which page ranks and whether its snippet answers the query.
- A new row **`fda calendar 2026: drug approvals, trial results & biotech ...`** at 40 impressions, position 6.83: that string is a competitor's page title being searched as a query, almost certainly MarketBeat's or Haymarket's. People are searching for a rival's page by name and we appear for it.
- `pdufa date` position 5.17, `pdufa calendar` 4.04 with 19 clicks, both holding.
- `aasld 2026` 56 impressions at 9.16, still climbing; the conference page lede shipped 10-03.

## 3c. Grounding queries

Top ten unchanged in rank: `pdufa date` 863 (22.92%, row still not refreshed), `fda calendar 2026` 359 (27.11%), rare-disease readouts **267 (46.76%)**, oncology readouts **201 (58.26%)**, `pdufa dates` 83 (36.56%), `09/28/2026 - approval completed` 60 (50.00%). Two new queries entered the long tail that I could not page to in this window.

## 3d. Google

The console window has not advanced since yesterday (Sept 2 to 29); yesterday's read stands: 27 clicks, 3.33K impressions, position 7.5, head terms on pages six to seven, drug names at 1 to 7, `juvmo pdufa` 13 impressions.

---

# 4. KAIZEN: WHAT THIS WEEK TEACHES ABOUT HOW WE BUILD

1. **A verifier that passes 16 of 16 can ship a page with no stylesheet.** Every verifier this month has asserted text and structure. None has asserted that a page *renders*. One rendered-page check per new template (a headless screenshot, or at minimum "the first `<style>` block contains the nav rules") would have caught the exclusivity page before a reader did.
2. **New sections get appended below the FAQ.** The AdComm history, the 13F block and the FDA-record block all landed at the bottom of their pages, after the FAQ and the source line, because that is where an injector can safely append. The result is pages whose most valuable new content is where the fewest readers reach. Injectors need a named slot above the FAQ.
3. **Every new dataset should ship as a table, not a paragraph.** The 13F paragraph, the CRL "sections addressed" column and the exclusivity table show the difference: the table is scannable and quotable per row; the paragraph is neither.
4. **The re-check rule earned its keep without anyone watching it.** Atebrioz re-entering the statistic automatically is the first time a correctness mechanism fixed a published number on its own. That pattern (record the gap, re-query every run, re-admit on evidence) should be the model for the three unbacked rows too: poll EDGAR and Drugs@FDA for them every run so the next placeholder is retired by a document, not by a ruling.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Publish Jaypirca** (LLY, pirtobrutinib, first-line CLL/SLL, FDA notice 2026-10-02 15:31 ET), Gazyva's treatment: FDA-sourced, `goal_unsourced`, fact-first lede, novel-approval count not applicable (supplement) | `/fda-decision/LLY-2026-10-02` live; on `/fda-this-month` under Oct 2 |
| **2** | **Fix the exclusivity page stylesheet**, and check `/fda-approval-letters` and every page built by a new template this week. Guard: first `<style>` block contains the shared nav selector | Phone screenshot shows the header and headline above the fold |
| **3** | **Reconcile `/adcomm`**: one count, history above the FAQ, voted meetings joined to their FR notice rows, title and description rewritten for a historical calendar | No two counts on the page disagree; CAPR and REPL appear once each with vote and FR link |
| **4** | **13F block as a table under a heading**, above the FAQ, caveat retained, filing linked per row; guard asserts `SH` and common-stock class on every published row | RVMD page shows the table; a planted PRN row is refused |
| **5** | **One owner for the `/fda-approval-letters` count** in title, h1 and schema | All three equal the live row count |
| **6** | **Freshness strip labels**: "Page updated" and "Data as of" | Both labels present on home, `/calendar` and a decision page |
| 7 | Chart caption: "announced {date} (FDA action {date})" where they differ; guard | JUVMO caption corrected |
| 8 | Mobile: collapse the ⌘K search pill to an icon below 480px | No overlap with content in a 375px screenshot of JUVMO and `/adcomm` |
| 9 | Exclusivity lede start date computed at build | Tomorrow's build reads "between October 5, 2026 and..." |
| 10 | Look at which page ranks for `fda approval decision biotech` (166 impressions, 0 clicks) and give it a snippet that answers the query | Snippet names a decision and a date |
| 11 | **Poll EDGAR and Drugs@FDA every run for the three unbacked rows** (AZN Ultomiris, NVO CagriSema, NVO Mim8) and retire the placeholder on evidence | A planted approval record retires the row's forward listing automatically |
| 12 | Carry: SMTP secrets for the escalation email (David); Google Drive exclusion (David) | |

---

# 6. BOTTOM LINE

**The site is back, correct, and better sourced than it has ever been.** Every structural check is clean, the flagship statistic grew by a row through a mechanism rather than a hand, and the one 13F number I pulled from the SEC matched to the share. The stall cost less in search than I expected: October 1 was a strong day on every series.

**What the verifiers missed is what a reader sees.** A new page shipped with no stylesheet. A hub says "2 meetings" above a list of 187. The most valuable new data on 438 pages sits in an unheaded paragraph below the source line. None of these is a data error, and all of them are the first thing a visitor notices. Items 2 through 8 are presentation, and presentation is where the next gains are, because the data layer is now largely won.

**And a decision from two days ago is a 404 on our site while three competitors hold its answer box.** Item 1.

---
*Live site read from a browser client with `cache: 'reload'` and rendered on a 375px viewport, 2026-10-04 16:42 to 17:40 UTC. Baker Bros 13F verified at SEC accession 0001104659-26-097191. Bing Webmaster read live (data through 2026-10-02); Google Search Console unchanged since 10-03 (data through 2026-09-29). Not investment advice.*
