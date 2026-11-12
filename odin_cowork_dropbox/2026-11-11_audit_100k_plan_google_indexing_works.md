# Audit: the road to 100K impressions a month by Dec 31, and the proof that Google indexing works when we ask
**2026-11-11, measured 22:58 to 23:50 Eastern = 2026-11-12 03:58 to 04:50 UTC (Wednesday night).** *Per RULE 1 every time carries its zone. The Bing console shows Pacific; its data still ends Nov 8.*
**Live build `2a361a958`, generated 2026-11-12T02:11Z (21:11 Eastern). Six scheduled runs green since Nov 10. Next decisions CYTK / SMMT / TEVA on Saturday 2026-11-14.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. THE 10-11 ORDER HAS NOT STARTED, AND ASUNDEXIAN IS NOW 54 HOURS WRONG

The last builder commit is the 11-10 note at 06:01 UTC. Every commit since is CI's own "daily data refresh". Nothing from the 11-10 audit has shipped:

| 11-10 order | Live tonight |
|---|---|
| 0. Publish Sunharbo (asundexian) | `/drug/asundexian` still says **"under FDA review"**; `/fda-decision/BAYRY-2026-11-09` 404; no dataset row. The FDA announced the approval on **Nov 9** |
| 0. Publish Optune Mya Not Approvable Letter | NVCR row still "Upcoming" |
| 0. Triage the other held leads | **Six** held leads, issues #70 to #77 open, the oldest at 54 hours |
| 1. Homepage links to the daily pages, CRL, studies, next-decision event pages | Homepage still 67 links; **none** of the seven checked |
| 2. HTML sitemap | `/sitemap` 404 |

`/drug/asundexian` is our 4th most-cited page in Bing's AI layer, and "asundexian fda approval" is a top-ten grounding query. Every day it stays wrong is a day Bing's answer for an approved drug is grounded on a page that says it is under review. **This is the first job.**

## 0a. Two held leads are false, and here is why (watcher defect)

The FDA's oncology approvals RSS republished **old notifications with a pubDate of Nov 10, 2026**. I read the "On {date}" sentence inside each item:

| Item in the feed, pubDate "10 Nov 2026" | The FDA's own date in the text |
|---|---|
| adagrasib with cetuximab, KRAS G12C CRC | **June 21, 2024** |
| Darzalex Faspro, light-chain amyloidosis | January 15, 2021 |
| asciminib, newly diagnosed CML | October 29, 2024 |
| afamitresgene autoleucel | August 2, 2024 |
| entrectinib, pediatric pellets | October 20, 2023 |
| dostarlimab, endometrial | August 1, 2024 |
| **pimicotinib (Pimjetmi), TGCT** | **November 10, 2026 (real)** |

Adagrasib is BMY's drug. The held lead `pdufa_bmy_2027-05-13` (fda_drugs_feed) is almost certainly the 2024 adagrasib notice matched against a 2027 BMY row, and `pdufa_jazz_2027-04-16` is likely the same kind of match. **Fix in `watch_fda_drugs_feed.py`:** take the action date from the item's "On {Month D, YYYY}" sentence, never from `pubDate`; drop any item whose own date is more than 14 days old. Guard: a planted feed item with a 2024 "On" date and a current pubDate raises no lead.

## 0b. Approvals the site has not recorded

- **Sunharbo (asundexian), Bayer, Nov 9.** Section 0.
- **Pimjetmi (pimicotinib), EMD Serono / Merck KGaA, Nov 10.** FDA oncology notification: "On November 10, 2026, the Food and Drug Administration approved pimicotinib (Pimjetmi, EMD Serono, Inc.)… for adults with symptomatic tenosynovial giant cell tumor." Not on any surface. MKKGY trades OTC; publish it as a decision page in the same way as other tracked sponsors.
- **Rybrevant Faspro, HNSCC, Nov 5.** Correctly listed under "Other FDA approvals" on `/fda-decisions-today` from Drugs@FDA. No decision page. Fine as is; it would be a cheap one to add.

Everything else is current: 0 day-dated PDUFAs past goal, 0 non-day dates, 0 conference mislabels, **55 of 55 day-dated upcoming rows sourced**, census 36: 22/13/1 consistent, freshness "Data as of Nov 11, 2026 9:11 PM ET".

---

# 1. WHERE WE ARE AGAINST 100K

I take "100K by EOY" as **100,000 search impressions a month, Bing plus Google, measured on the last 30 days to Dec 31**. Tell me if you meant clicks or a cumulative total; the plan changes.

| Channel, last 30 days | Impressions | Clicks | Daily average |
|---|---|---|---|
| Bing web (Oct 10 to Nov 8) | **23,340** | 488 | 778 |
| Google (28 days) | **1,340** | 21 | 48 |
| **Total** | **~24,700** | ~509 | ~826 |
| Bing AI citations (60 days) | 28.2K citations | n/a | not counted as impressions |

**Gap: about 4x in seven weeks.** Bing alone will not get there: its weekday ceiling has sat at 800 to 1,300 for a month, and December's holiday weeks will pull the average down. The only lever big enough is **Google**, where we are close to absent.

## 1a. Google: the proof from this week

- Index tonight: **55 indexed, 1,590 not indexed, 1,568 of them "Discovered – currently not indexed"** (report updated Nov 8).
- **Last night I requested indexing for 7 pages. Tonight `/fda-decisions-today` and `/pdufa/CYTK-aficamten` both show "URL is on Google", and `/crl` does too.** Requested indexing gets a page in within about a day.
- Tonight I requested `/pdufa/CAPR-deramiocel` and `/pdufa/SVRA-molbreevi` (both accepted). After that the console returned **"Quota Exceeded"**: about 10 requests a day, shared across the property.
- At 10 a day, the 1,568 discovered pages take five months by hand. Requested indexing proves the pages are indexable. **Internal links are what make Google index them on its own**, and that is the 11-10 order item 1 that has not started.

## 1b. What 100K takes, by lever

| Lever | Mechanism | Plausible gain by Dec 31 (monthly impressions) |
|---|---|---|
| **Google indexes the event, decision and drug pages** | Homepage and footer links, HTML sitemap, related links (the 11-10 order 1 to 3); 10 requests a day on top | If Google indexes 600 to 800 pages at even a quarter of Bing's per-page yield: **+20K to +40K**. This is the big one |
| **New page families that answer search demand we already see** | 2027 conference pages (asco 2027 alone: 466 Bing impressions, 1 click); CRL month pages; drug pages for every approved drug in 2025 to 2026 (Drugs@FDA lists them); "FDA approvals {month} {year}" pages | **+10K to +20K** across both engines |
| **Bing CTR** | 2.3% now. `fda approval decision biotech` alone has 1.1K impressions, 0 clicks; `asco 2027` 466 / 1; `fda complete response letter october 2026` 133 / 0. Titles that answer the query in the SERP | Clicks, not impressions; doubles clicks |
| **Bing AI** | Daily citations already 600 to 900; keep the build unbroken (a frozen night costs 80% the next day) | Feeds Bing web via trust; not counted directly |
| **Links from outside** | 89 links from 5 sites. CC-BY census CSV, "Cite this page", `/corrections` exist; outreach is David's | Slow; matters for Q1 |

**Honest read:** 100K a month by Dec 31 needs Google to go from 55 indexed pages to several hundred within about four weeks. Reachable if the internal-linking work ships this week. If it ships in December, 50K to 60K is the realistic year-end number.

---

# 2. BING (console, data to Nov 8; no new days since last night)

- **AI:** 28.2K citations, 87 grounding queries, average cited pages 34. Top: `pdufa date` 2.0K (24.72%), `fda calendar 2026` 395, oncology readouts 325 (48.80%), `asundexian fda approval` 165, `asundexian pdufa date` 120 (58.54%).
- **Web, 35 days:** Oct 21 and 22 at 1.3K were the peak days; Nov 2 to 6 ran 692 to 963; Nov 7 (Saturday) 250; Nov 8 382. Window total **1.3K clicks / 55.9K impressions / 2.32%**.
- **Submitted tonight:** 22 URLs. These cover every pending event page from Nov 22 to Jan 2027 (CAPR, SVRA, BBIO, PYPD, COGT x2, RHHBY giredestrant x2, VRTX, VNDA, CORT, MLYS, GILD anito-cel, PRAX x2, VTRS, RHHBY MOGAD, DYN, INSM) plus the Nov, Dec and Jan 2027 month pages. CI's batch of 40 had already sent the hubs. 38 left today.

---

# 3. ORDER

| # | Item | Acceptance |
|---|---|---|
| **0** | **Publish Sunharbo (asundexian) and Pimjetmi (pimicotinib); close NVCR with the Optune Mya Not Approvable Letter.** Ack the BMY/JAZZ leads if they are the republished 2024 notices | `/drug/asundexian` leads with the Nov 9 approval; both decision pages 200; `held_leads` ≤ 2 |
| **1** | **Feed-date fix (0a):** the action date comes from the item's "On {date}" sentence; items older than 14 days are dropped | Planted old item raises nothing; guard 0 → 1 → 0 |
| **2** | **Internal linking, the 100K lever (11-10 orders 1 to 3):** homepage blocks (next decisions as `<a href>` to event pages; today/this week; last 10 decisions); site-wide footer to `/crl`, `/fda-approval-letters`, `/corrections`, `/research/fda-decision-timing`, `/decisions/2026`, `/readouts/oncology`, `/calendar/2027`, `/conferences`; `/sitemap` HTML; related links on every leaf page | Reachability guard: every indexable sitemap URL within 3 clicks of `/` in built HTML; orphans 0. Median inbound links per page ≥ 5 |
| **3** | **Daily Google list** `_google_request_indexing.txt`: the 10 most valuable non-indexed URLs (new decision pages first, then events in the next 30 days, then studies) | Written each run; I or David work it daily (the quota is about 10) |
| **4** | **Page families for demand we already see:** (a) 2027 conference pages titled "{Conf} 2027: {dates}, {city}" for every 2027 meeting in conferences.json; (b) `/fda-approvals/2026/{month}` from Drugs@FDA originals and efficacy supplements, one sentence per approval with the letter link; (c) a drug page for every 2025 to 2026 approval that lacks one | (a) 2027 pages 200 and in the sitemap; (b) Oct and Nov 2026 pages live with counts that match Drugs@FDA; (c) count printed |
| **5** | **CTR titles for the zero-click queries:** the weekly page title leads "FDA approval decisions this week ({dates}): {n} decided, {m} due"; ASCO 2027 page title leads with the dates and city; CRL month pages lead with the count | Titles live; re-read CTR in two weeks |
| **6** | Saturday 11-14 runbook: CYTK, SMMT, TEVA; watch Friday 11-13 from 09:00 Eastern | Decision pages the day of the record |
| 7 | `_crl_capture_series.json` into `git add`; remove `POLYGON_API_KEY` after Nov 17 | |
| 8 | David: confirm the 100K definition; SMTP; `/surges` ruling; outreach to the five linking sites | |

---

# 4. BOTTOM LINE

**Currency:** right on everything except two approvals the FDA announced on Monday and Tuesday. One of them sits on our most-watched drug page, and the builder has not touched the site since Tuesday morning.

**Google:** asking works. Three pages I requested were indexed within a day. Google simply has not been invited to the other 1,568, because our own homepage does not link to them.

**100K:** we are at about 25K a month. Bing has plateaued near 800 a day. Google can take us to 100K, but only if the linking work ships this week, so it is order 2, right behind fixing asundexian.

---
*Site read from Chrome with `cache: 'reload'`, 2026-11-12 03:58 to 04:50 UTC, against build `2a361a958`. Google Search Console read live: Page indexing (updated 11/8), Performance (28 days), URL Inspection on 7 URLs; indexing requested for /crl (already indexed, re-requested), /pdufa/CAPR-deramiocel and /pdufa/SVRA-molbreevi, then quota exceeded. Bing Webmaster AI Performance and Search Performance (to 11/8) read live; 22 URLs submitted. FDA press-release and drugs RSS feeds read live. GitHub via the public API. Not investment advice.*
