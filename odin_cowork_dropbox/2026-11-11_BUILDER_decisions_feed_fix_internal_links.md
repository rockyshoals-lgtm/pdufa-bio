# Builder note: Nov 9-10 decisions published, feed-date fix, internal linking for Google, new page families
**2026-11-11 ~20:30 Pacific to 2026-11-12 ~01:00 Eastern.** *RULE 1.* *Facts and build mechanics only. Not investment advice.*
Answers the 2026-11-11 audit ("the road to 100K impressions a month") and David's "fix this" on ESCALATION #72.
David's choices: all orders 0-7; 100K means **100,000 search impressions a month (Bing + Google), last 30 days to Dec 31**.

Note on the audit's section 0: there was no 11-10 order in the builder's inbox. The last audit received was the 11-09
one, finished 11-10 (note `2026-11-10_BUILDER_red_team_1109_orders.md`), which reported asundexian and NVCR as verified
and unpublished. Both are published now.

## 0. Decisions and held leads (#70-#77, ESCALATION #72)
Read against primary sources tonight (`apply_1111_decisions.py`):
- **Sunharbo (asundexian), Bayer, approved Nov 9, 2026** (FDA press announcement). New row
  `pdufa_bayry_2026-11-09_asundexian`, decision page `/fda-decision/BAYRY-2026-11-09`. Bayer stated no goal date
  (Priority Review, May 2026): `goal_unsourced`, no margin, not in the timing census. `/drug/asundexian` now leads
  with the approval.
- **Pimjetmi (pimicotinib), EMD Serono / Merck KGaA, approved Nov 10, 2026** (FDA oncology notification). New row
  `pdufa_mkkgy_2026-11-10_pimicotinib`, page `/fda-decision/MKKGY-2026-11-10` (MKKGY closes from FMP).
- **NVCR Optune Mya: FDA Not Approvable Letter**, announced Nov 9 (Novocure 8-K EX-99.1). A device PMA letter, recorded
  as outcome "Not approvable letter", never as a CRL; `decision_date_unsourced` (the letter's own date is not public).
  `test_decided_consistency` accepts the outcome.
- Acked with reasons: #74 ENFLONSIA S-3 (letter of 2026-10-14: injection-site erythema and swelling rates in Adverse
  Reactions; not the second-RSV-season sBLA we track for March 2027); #75 entrectinib (Oct 20, 2023 notice) and #76
  Darzalex Faspro (Jan 15, 2021), both republished by the FDA feed with a Nov 10, 2026 pubDate; #77 Capricor's Q3 8-K
  (Nov 10) says "if approved" and "as we approach our PDUFA date": no approval, Nov 22 stands.

## 1. Feed-date fix
`watch_fda_drugs_feed.py` dates every item by its own "On {Month D, YYYY}" sentence and drops it when that date is more
than 14 days older than the feed date. Replayed against tonight's live feed: 8 republished notices (2021-2024) listed
as "republished, not a lead", 0 leads. The "untracked approval" regex was case-sensitive and missed "FDA approves
pimicotinib"; now case-insensitive. Guard `tests/test_fda_feed_own_date.py`: planted 2024 notice with a 2026 pubDate
raises nothing; a current notice raises one lead dated Nov 10; an item with no "On" sentence keeps its pubDate.

## 2. Internal linking (the 100K lever)
New `inject_site_links.py` (workflow step before the final sitemap):
- **Browse pdufa.bio** row above the footer on every indexable page (18 hubs: calendar, 2027, today, this week, this
  month, decisions 2026/2025, CRL, approvals by month, letters, timing study, run-up study, approval rate, readouts,
  oncology readouts, conferences, corrections, /sitemap).
- **Homepage hub:** the next 12 FDA goal dates (event pages), the latest 10 decisions (decision pages), and the
  daily pages and studies.
- **Related links** on 1,038 leaf pages: event pages link the six nearest other goal dates, their month and ticker;
  decision pages the six decisions nearest in time, their year and ticker; drug, ticker, conference and condition
  pages their six neighbours.
- **/sitemap**: HTML list of every sitemap URL (1,654) by section under each page's own title.
- Guard `tests/test_reachability.py`, on the built tree: before, 69 sitemap URLs were more than 3 clicks from / and
  45 had no inbound link; after, **all 1,654 within 3 clicks (1 at depth 0, 92 at depth 1, 1,561 at depth 2), 0
  orphans, median 8 inbound links.**

## 3. Daily Google list
`build_google_request_list.py` writes `_google_request_indexing.txt` every run: decision pages from the last 7 days,
then event pages for goal dates in the next 30 days, then hubs; it skips `_google_indexed.json` (seeded with
/fda-decisions-today, /pdufa/CYTK-aficamten, /crl) and anything requested in the last 7 days (`_google_requested.json`,
seeded with CAPR and SVRA from Nov 11). After requesting: `python build_google_request_list.py --requested <paths>`.
Today's ten start with the BAYRY and MKKGY decision pages, then SMMT and TEVA (Nov 14), BBIO, PYPD, COGT, GSK, REGN,
RHHBY.

## 4. Page families
- (a) 2027 conferences: every 2027 meeting in conferences.json already has a 2027-titled page with dates and city
  (JPM, ASCO GI, WORLD, ASCO GU, AAD, AACR, ACC, AAN, ASGCT, ATS, DDW, ASCO, EHA, EASL, ADA).
- (b) **New `/fda-approvals/{year}/{month}`**, January 2025 to November 2026 (23 pages + hub), from openFDA drugsfda
  (Drugs@FDA data): every original NDA/BLA approval and every efficacy supplement of the month, one sentence each with
  sponsor, application, action day and the FDA letter. October 2026: 16 new applications, 25 efficacy supplements
  (includes Enspryng S-8 Oct 15 and Ultomiris S-46 Oct 21). openFDA trails by about a week; the page says so.
  Titles say "New Applications", not "New Drugs" (most are new formulations, not new molecules).
- (c) Count: 268 new-application approvals in 2025-2026 per openFDA; 163 have no /drug/ page, 24 of them Type 1 new
  molecular entities. Not built tonight; the month pages give each one a sentence and a letter link meanwhile.

## 5. CTR titles
`/fda-approval-decisions-this-week` now titled "FDA approval decisions this week (Nov 9 to Nov 15, 2026): 3 decided,
3 due". ASCO 2027 already leads with "Jun 4-8, 2027, Chicago"; CRL month pages already lead with counts.

## 6. Saturday 11-14 runbook
CYTK aficamten (MAPLE-HCM sNDA), SMMT ivonescimab, TEVA IGALMI at-home sNDA. Weekend goals usually act Friday 11-13:
watch from 09:00 Eastern (06:00 Pacific): Drugs@FDA, the FDA press and drugs feeds, sponsor releases and EDGAR 8-Ks.
Each decision: dataset row Decided with FDA action day + sponsor announcement, decision page via
`build_decision_page.py`, ack the watcher lead with "published".

## 7. Housekeeping
`_crl_capture_series.json`, `_google_request_indexing.txt` and `_fda_approvals_months.json` added to the workflow's
commit list. `POLYGON_API_KEY` comes out after Nov 17.

## Still David's
Work the Google list daily (about 10 a day); SMTP; `/surges` RULE 2 ruling; outreach to the five linking sites.
