# BUILDER ORDER, consolidated: every open item from the audits of 09-14 through 10-03, ranked
**Auditor, 2026-10-03, 19:00 UTC = 15:00 Eastern.** *Per RULE 1 every time carries its zone.*
**Live build `9fa6bc890`, generated 2026-09-27T23:32:47Z. CI has failed 17 consecutive runs (#222 to #238).**
*Facts and build mechanics only. Not investment advice.*

This document replaces the ORDER tables in the 09-26, 09-27 and 10-03 audits. Items already shipped and verified live are listed once in section 7 so nobody redoes them. Everything else is here, in the order I would work it.

**Standing rules for every item:** facts only, no approval odds or predictions; no early or late margin unless both the goal date and the action date come from a document that states them; never call a CRL a rejection; no em dashes in published copy; every guard proved 0 → planted 1 → 0 on the rendered output, not the source data.

---

# TIER 0: UNBLOCK THE SITE TODAY

## 0.1 Work the blocking queue (the site has been frozen since 2026-09-27 23:32 UTC)

**Cause:** step 40, "Early-approval watch against FDA's own feed," exits 1 on unreviewed leads; every later step (other watchers, rebuild, commit, deploy) is skipped. Seventeen blocking issues (#2 to #18) were opened and none was read.

**The four leads, each verified against the FDA:**

| Lead | Verdict | Action |
|---|---|---|
| ABBV tavapadon (row `pdufa_abbv_2026-12-31`) ← AbbVie *"U.S. FDA Approves AbbVie's JUVMO™ (tavapadon) for Parkinson's Disease"* (issues #2, #3, #5, #6) | **REAL.** Drugs@FDA **NDA 220415** ORIG-1, approved, `submission_status_date` **2026-09-25**; letter `https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/220415Orig1s000ltr.pdf` (posted 09-29). AbbVie announced 2026-09-28 on PR Newswire | **Publish.** Decided / Approved; `fda_action_date` 2026-09-25 with the letter as `fda_action_source_url`; announcement 09-28. Goal date never sourced, so `goal_unsourced`, **no margin**. Brand JUVMO; AbbVie's wording: first selective D1/D5 receptor agonist approved for adults with Parkinson's disease; U.S. availability expected October 2026. Add to `/fda-approval-letters` (n 38 → 39). Ack key from issue #2 |
| RHHBY Enspryng (TED, goal 10-15) ← FDA notice *"FDA Approves First Treatment for MCT8 Deficiency"* (issue #4) | **FALSE.** Different drug and disease; matched on the token "thyroid" | Ack in `_fda_drugs_feed_ack.json` |
| AGIO mitapivat (RISE UP, goal 11-01) ← Drugs@FDA SUPPL-7 approved 2026-09-28 (issues #7 to #18) | **NON-EVENT.** Supplement class **MANUF (CMC)**, a manufacturing change, not the sickle-cell efficacy sNDA | Ack in `_fda_watch_ack.json` |
| RHHBY giredestrant + everolimus (goal 12-18) ← "everolimus" ORIG-1 approved 2026-09-21 (issues #7 to #18) | **FALSE.** **ANDA 220597, Novitium Pharma**, a generic everolimus; matched on the combination partner | Ack in `_fda_watch_ack.json` |

**Then:** dispatch the workflow; read the sponsor-feed and FDA-drugs-feed step output, **which has not run since 2026-09-30** and may hold further leads; close issues #2 to #18 with a one-line reason each.

**Acceptance:** a green scheduled run; `/build-info.json` `built` is today; `/pdufa/ABBV-tavapadon` and the API row say Approved with the FDA date; AACR Pancreatic (ended 09-28) and ASTRO (ended 09-30) no longer say "In progress"; EASD and WMS no longer say "Scheduled"; home and `/calendar` stamps are today.

**Context for the page:** JUVMO is the **second of the five unbacked rows to be settled by an FDA approval** rather than a ruling (Kerendia, approved 09-16, was the first). Both carried "December 2026" placeholders. `juvmo pdufa` already shows **13 Google impressions at position 7.0** landing on a page that says "pending."

---

# TIER 1: MAKE THIS IMPOSSIBLE TO REPEAT

This is the second multi-day outage from the same guard (2026-09-11 to 09-14, and 2026-09-28 to now). The principle, verify then publish, is right. Three things around it are wrong.

| # | Item | Evidence | Acceptance |
|---|---|---|---|
| **1.1** | **Quarantine, don't blockade.** A lead holds only its own row and the pages that render it, at their current state, and still opens its issue. Everything else rebuilds and deploys | One real approval plus three false leads froze prices, conference statuses, readouts and 450+ unrelated rows for six days | A planted lead on one event leaves that row unchanged and the rest of the site deploys; guard proves it |
| **1.2** | **Escalation that reaches a person.** After two consecutive held runs, send email to David (SMTP secret in Actions), and add `held_since` and `held_leads` to `/build-info.json` | 17 issues, all unread. The GitHub inbox is not a channel | A replay of 2026-09-28 produces one email the same day and a non-null `held_since` |
| **1.3** | **Tighten the matchers, four rules:** (a) an **ANDA** never matches an armed NDA/BLA event; (b) ignore supplement classes **MANUF/CMC and labeling-only** when the armed event is an efficacy filing; (c) on combination rows match the **investigational drug only**, never the partner; (d) a disease match needs the indication phrase or two specific tokens, never a lone organ word such as "thyroid" | 3 of 4 leads this week fail one of these rules; precision was 25% | Replays of the three false leads produce zero leads; the JUVMO release still produces one |
| **1.4** | **Honest freshness in the API.** Add `meta.data_built_at` (the build time) beside `as_of`, and have every freshness stamp read it | Today `/api/v1/*` reports `as_of: 2026-10-03` over data built 2026-09-27 | No API response can report a date newer than its data without saying so |
| **1.5** | **Time-derived statuses at request time.** Conference "In progress / Ended" and PDUFA "Awaiting" depend only on today's Eastern date and fixed data, like `next_days` does now. Compute them when served | A held build left two finished congresses "In progress" | With the build held, a congress whose end date has passed renders "Ended" |

---

# TIER 2: CURRENCY AND SPEED ON DECISION DAYS

The answer box on a new approval goes to whoever publishes one clean, FDA-dated sentence first. In two weeks it went to **trialfriend.com** (Atebrioz), **simianx.ai** and **allsci.com** (zilurgisertib), and **breakoutbiotechstocks.com** (JUVMO). None is more accurate than we are; each was faster.

| # | Item | Evidence | Acceptance |
|---|---|---|---|
| **2.1** | **Fact-first first sentence on every decision page, not only FDA-notice ones.** Extend the 09-27 `rewrite_decision_snippets` rule to every Approved page: "{Brand} ({INN}) was approved by the FDA on {FDA action date} for {indication}" where the action date is FDA-sourced; "the FDA announced its approval of ... on {date}" where only an FDA notice exists | The JUVMO box sentence: *"The FDA approved AbbVie's Juvmo (tavapadon) on September 25 for Parkinson's disease in adults, the 43rd novel drug approval of 2026..."* | JUVMO's page leads with that shape on its first publish |
| **2.2** | **Running novel-approval count** on each new-molecular-entity decision page: "the Nth novel drug approval of 2026, per the FDA's Novel Drug Approvals list," linked | The winning JUVMO sentence used exactly this; we hold the data | Count equals the FDA's Novel Drug Approvals 2026 page on every NME page |
| **2.3** | **Brand alias on approval.** When a decision publishes, the drug page, the event page and the API row carry the brand in title, `alternateName` and FAQ the same run (`atebrioz`, `juvmo`) | `juvmo pdufa` 13 impressions to a "pending" page | The brand string appears on all three surfaces in the publishing run |
| **2.4** | **Sponsor-feed coverage.** 8 of 33 armed sponsors have a feed. Merck and Roche/Genentech publish no RSS: cover MRK through EDGAR 8-K polling every run (Merck files), and RHHBY through the FDA "What's New: Drugs" feed (Roche is not an SEC registrant). Add feeds for every sponsor with a goal in the next 60 days | MRK Oct 10 and RHHBY Oct 9 / Oct 15 rest on feeds we cannot read | Each sponsor with a goal before 2026-12-03 has a working feed, an EDGAR poll, or a recorded reason |
| **2.5** | **Resolve the "0 press items scanned" line** in the drug-page watch (your 09-27 retraction left its cause unknown) and keep `BLIND` reporting on every watcher | A watcher that reads nothing must say so, not print a zero | `_watch_health.json` shows a successful read for every pass in the last run |
| 2.6 | **Gazyva (obinutuzumab), idiopathic nephrotic syndrome, approved 2026-09-25**, listed by the FDA feed as untracked. Add a decision page, sourced to the FDA notice and the Drugs@FDA letter when posted | Large-cap approval with no page on the site | Page live, FDA-sourced |
| 2.7 | **Atebrioz action date.** When Drugs@FDA posts the letter, the 09-26 re-check (item 5 of that ORDER) should re-admit MIRM/INCY to the timing study automatically | No letter as of Drugs@FDA's 2026-10-02 update | Confirm it re-enters without hand work |

---

# TIER 3: SEO, BING AND AI CITATIONS

**Where we stand (Bing data to 2026-09-30; Google to 2026-09-29):**
- **Bing AI citations 10.1K** (from 8.8K), average cited pages 23, **38 grounding queries** (from 31). Monday 2026-09-28 was the series high at 553 citations and 58 average cited pages.
- **Bing web:** 674 clicks, 27.4K impressions; Sept 28 to 30 impressions about 20% above the prior week. `pdufa date` position **5.18**, `pdufa calendar` 4.04 with 19 clicks.
- **Google:** 27 clicks, 3.33K impressions, position 7.5. **Head terms sit on pages six to seven** (`pdufa calendar` 55.4, `pdufa date` 69.7, `what is a pdufa date` 78.4) while drug names rank 1 to 7. Google is an authority problem on head terms; **per-drug pages are the Google strategy.**
- The stall's effect is **not yet visible** in data through Sept 30. Oct 1 to 3 lands in two to three days.

| # | Item | Evidence | Acceptance |
|---|---|---|---|
| **3.1** | **The `09/28/2026 - approval completed` grounding query.** New, 60 citations, **50% share**, almost certainly an automated agent asking what was approved that day, on the day JUVMO was announced and our site was frozen. Make sure a date-scoped answer exists: `/fda-this-month` and `/fda-approval-letters` should state, per day, what the FDA approved, by FDA action date | We are cited for "what was approved on this date" | After unblock, both pages list JUVMO under 2026-09-25 with the letter |
| **3.2** | **`fda approval letters`** is a live grounding query at 13.04% share; the hub shipped 09-27. Link it from every decision page's source line and from `/decisions` | One new page, one live query | Inbound links from all decision pages; share re-read in two weeks |
| **3.3** | **Readout hubs are working; keep feeding them.** Rare-disease readouts 126 → 258 citations at 46.99% share after `/readouts/rare-disease` launched; oncology readouts 58.77%. The ceiling is tagging: **58% of forward readouts carry no therapeutic area.** Back-fill by hand, never by keyword widening (the custirsen lesson) | Two content-to-channel chains proven | Untagged share below 30% with no row tagged by name match |
| **3.4** | **Conference pages.** AASLD (45 Bing impressions, position 9.13) and SABCS pages exist and are now linked from the hub (09-27). Add a one-sentence fact-first lede with dates and location to each per-conference page | Queries arriving at the bottom of page one | Lede present on all upcoming conference pages |
| 3.5 | **Watch `pdufa date` share.** The row reads 22.92% on two consecutive reads, so it has not refreshed; do not treat it as flat | Frozen console rows recur (also the PFE, daraonrasib, camizestrant and rusfertide keyword rows) | Re-read when it moves |

---

# TIER 4: DATA AND MOAT, CARRIED

| # | Item | Status / evidence |
|---|---|---|
| 4.1 | **13F specialist-fund block** on decision and drug pages, from `Odin Perfection/v382_checkpoints/phase1_god_tier_holdings.json` (48,361 records) and `_god_tier_13f_cache.json`. Open the file and confirm as-of dates before writing a sentence | Identified 09-05; queued four times. The lowest-risk moat item: quarterly public filings, no caveat needed |
| 4.2 | **AdComm historical calendar** from `Odin Perfection/fda_adcom_historical_meetings_2020-2026.csv` (140 Federal Register notices, columns `pub_date,title,doc_num,fr_url,abstract`). Parse committee and meeting date from text; **notices only, no votes, no company or drug**; votes stay hand-sourced | `/adcomm` lists 2 meetings |
| 4.3 | **Orange Book `exclusivity.txt`** into `/patent-cliff`: regulatory exclusivity expiry is an earlier, different cliff than patent expiry | Apparently unused |
| 4.4 | **`daily/NEW_*.csv`** (51+ daily files from 2026-07-15) into `/pdufa-date-changes` | The data accrues daily |
| 4.5 | **CRL letter text** beyond the nine linked pages: deficiency headings, read from the PDF, never pasted from OCR | 457 of 458 letters carry text |
| 4.6 | **22 readout leads (#52)** and the **13 Estimated readouts the 09-14 re-sync moved into the past** | Need a treatment ruling |
| 4.7 | **Six truncated decision-page drug names (#65 NEW-1)**; fix the title builder, not the instances | Recurred on Kerendia 09-23 |
| 4.8 | **Housekeeping:** confirm `adcom_baserate_v1.json` (hand-typed `yes_rate` values) has moved out of every build path; grep build scripts for `full database.xml` (DrugBank, CC BY-NC, commercial licence required); fix or remove `smart_money_v2_cache.json` (truncated), `ctgov_t1_raw_studies.json` (0 bytes), `fda_adcom_federal_register.json` (FEMA and railroad notices) | 09-20 sweep |

---

# FOR DAVID (not builder actions)

1. **Who reads the blocking alert?** Item 1.2 sends email to you. If someone else should get it, say who.
2. **Exclude `Documents\Python\9realms` from Google Drive backup.** The sync client deleted 133 pages mid-build on 09-20 and has recurred on three days. Until it is excluded, only CI builds are trustworthy.
3. **The three remaining unbacked rows:** AZN Ultomiris (IgAN), NVO CagriSema, NVO Mim8. Two of the original five (Kerendia, JUVMO) were approved months before our "December 2026" placeholders. My recommendation stands: withdraw the forward day, keep the drug pages.
4. **Bing Webmaster sign-in** has dropped three times this month; each time the audit loses the AI-citation read.
5. **Long titles:** leave them (auditor and builder agree).

---

# RE-TESTS I WILL RUN

| When | What |
|---|---|
| After the unblock | Green run; tavapadon live with FDA date; conference statuses current; issues closed |
| Bing data through 2026-10-03 (about 10-05 to 10-06) | Weekday AI citations and impressions for Oct 1 to 3 against Sept 28 to 30: the measured cost of the stall |
| 2026-10-09 | RHHBY Tecentriq decision day: time from FDA action to our page, and who holds the answer box |
| When Drugs@FDA posts Atebrioz | MIRM/INCY re-enter the timing study automatically |

---

# 7. ALREADY SHIPPED AND VERIFIED LIVE (do not redo)

- Timing statistic **29: 18 early / 10 on the day / 1 late, median 3 days before**, on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing` and `/llms.txt`; "29 of 29 action dates from the FDA's own record" (verified 09-27, re-derived by hand).
- `fda_action_date` from Drugs@FDA for every decided CDER row, CBER from FDA letters/notices; excluded rows re-checked every run.
- `/fda-approval-letters`, 38 FDA actions, 7 announced later than the FDA acted (verified 10-03).
- Atebrioz published on MIRM and INCY with fact-first snippets sourced to the FDA notice; Pharming lower-dose Joenja PDUFA 2027-01-30; next pointer to RHHBY 2026-10-09.
- FDA "What's New: Drugs" feed watcher; sponsor-newswire watcher (8 of 33 sponsors).
- Aggregator-source guard (no StockTitan or similar as primary source).
- AASLD and SABCS conference pages linked from the hub; dates verified against the organisers (AASLD 2026-11-05 to 09, Denver; SABCS 2026-12-08 to 11, San Antonio).
- Haymarket's October roundup checked row by row against ours: **identical dates** (Tecentriq Oct 9, ifinatamab Oct 10, satralizumab Oct 15, bepirovirsen Oct 26, INO-3107 Oct 30); we also carry phentolamine Oct 17. Closed.
- `/build-info.json` computes `next_days` per request, with `as_of_eastern` and `served_at`.

---
*Sources for the Tier 0 verdicts: GitHub Actions runs #214 to #238 and issues #2 to #18 read live 2026-10-03; openFDA Drugs@FDA queries for NDA 220415 (tavapadon) and ANDA 220597 (everolimus), `last_updated` 2026-10-02; AbbVie release of 2026-09-28 read in full. Console figures from Bing Webmaster (to 2026-09-30) and Google Search Console (to 2026-09-29), read live 2026-10-03. Not investment advice.*
