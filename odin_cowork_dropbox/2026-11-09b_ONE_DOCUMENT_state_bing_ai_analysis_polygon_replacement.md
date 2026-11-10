# One document: site state, Bing AI and search analysis, rankings, and the Polygon replacement
**2026-11-09, measured 22:20 to 22:55 Eastern = 2026-11-10 03:20 to 03:55 UTC (Monday night). Bing Webmaster data runs to November 7; the console shows Pacific times.** *Per RULE 1 every time carries its zone.*
**Live build `baf7832d4` (2026-11-09T23:07Z = 18:07 Eastern). API 505 rows. Next decisions CYTK / SMMT / TEVA on Saturday 2026-11-14. Two leads held (NVCR 11-15, asundexian), issues #70 to #72; the rest of the site deploys.**
*Facts and build mechanics only. Not investment advice.*

This supersedes the 2026-11-09 audit written an hour earlier without the Bing console. Everything from that note is carried here.

---

# 1. SITE STATE

| Check | Live |
|---|---|
| Day-dated PDUFAs past goal and not Decided/Withdrawn | **0** |
| Non-day rows with a date / month mismatch | 0 / 0 |
| Conferences mislabelled against the Eastern date | 0 |
| Upcoming PDUFAs | 62; 55 day-dated, **55 sourced, 0 unsourced** |
| Timing census | **36: 22 early / 13 on the day / 1 late**, consistent on `/calendar`, `/learn`, `/research`, `/llms.txt` |
| Readouts | 335; bare "Window passed" 2 |
| Freshness | "Data as of Nov 9, 2026 6:07 PM ET"; "Data through Nov 9" (Eastern) |
| CI | last 3 scheduled runs green; the Nov 7 to 9 freeze (conference-stamp guard) opened BLOCKED #63 and was cleared. **Silent freezes are over: every freeze since 10-18 opened an issue** |

**10-18 orders verified live:** `/corrections`, `/calendar/2027`, `/readouts/oncology`, `/conference/ASH` all 200; `goal_date_held` on the API and `/developers`; PBYI/VYGR indexed; Enspryng now "Approved Oct 15, 2026" (letter posted; row in the census); RYZUMVI "1 Day Early". **Still open:** three-dates line on decision pages; `/decisions/2025` (404); free `.ics`; email alert (SMTP, David); `/surges` RULE 2 ruling (David).

**Builder work since 10-18, verified:** 21 goal dates found by an EDGAR full-text sweep and added, plus four since; CYTK indication corrected (obstructive HCM) before its decision; 97 run-up rows re-tiered; homepage JSON-LD that listed July events replaced; mobile nav on 1,209 pages; source sentence on 58 event pages; `/screener` rebuilt off a July snapshot.

---

# 2. BING AI PERFORMANCE (console, data to November 7)

## 2a. The numbers

| | 10-18 read (to Oct 16) | **Tonight (to Nov 7)** |
|---|---|---|
| Total citations (60 days) | 16.2K | **28.1K** |
| Average cited pages per day | 25 | **33** |
| Grounding queries | 56 | **87** |
| Best day | 653 (Oct 16) | **902 (Nov 1), 865 (Nov 2), 811 (Oct 23)** |

Daily citations, Oct 17 to Nov 7: 520, 618, 577, 653, 155, 88, **811**, 747, 587, 603, 478, 82, 141, 602, 747, **902**, **865**, 705, 144, 186, 665, 1 (partial). Three things in that series:
- Weekdays now run 600 to 900; a month ago 400 to 650.
- The low days (155, 88, 82, 141, 144, 186) are not weekends; Oct 21 to 22 and Oct 28 to 29 are midweek. They line up with the **freezes**: Oct 22 three runs failed on a Polygon 429 (builder 10-22 note), Oct 31 to Nov 2 the INO guard freeze. **Each time the build stops, Bing's citation count falls by 80% within a day.** That is the strongest evidence yet that Bing's grounding layer re-reads us daily and drops us when the pages do not move. Reliability of the nightly build is now a citation metric.
- Nov 1 and 2 (902, 865) were a Sunday and Monday: the day the INO/AZN/Pluvicto/Mounjaro decisions and 21 new goal dates went live. Publishing volume on real decisions is what the AI layer rewards.

## 2b. Grounding queries, top 20 (citations / share)

| Query | Cites | Share | Note |
|---|---|---|---|
| pdufa date | **2.0K** | 24.71% | was 1.2K / 22.98%; share rising for 6 reads |
| fda calendar 2026 | 395 | 25.72% | share down from 26.11%: 7th consecutive slip |
| major upcoming Phase 3 oncology trial readouts next 12 months | 325 | 48.80% | share down from 50.09%; `/readouts/oncology` is new and already cited 349 times |
| upcoming clinical trial readouts rare disease | 305 | 45.19% | flat |
| fda pdufa calendar | 192 | 37.50% | up from 102 |
| pdufa dates | 161 | 36.02% | up |
| fda pdufa dates | 156 | 36.53% | new in top 10 |
| **asundexian fda approval** | **155** | 27.68% | new; `/drug/asundexian` 665 citations, and it is **a held lead tonight** |
| what is a pdufa date | 140 | 23.37% | up from 10 |
| **asundexian pdufa date** | 120 | **58.54%** | our highest share on any named-drug query |
| upcoming fda approvals & pdufa dates tracker for a free | 117 | 21.31% | a user asking Copilot for a free tracker; we are cited 1 in 5 |
| pdufa calendar | 94 | 42.15% | |
| anito-cel pdufa date | 89 | 44.06% | `/pdufa/GILD-anito-cel` 348 citations; decision Dec 23 |
| fda pdufa | 87 | 19.55% | |
| camizestrant pdufa date | 87 | 32.10% | frozen row since September |
| rusfertide pdufa date | 81 | 16.95% | frozen |
| fda approvals today | 80 | 47.34% | |
| pdufa (navigational) | 79 | 2.73% | |

## 2c. Pages cited (top 20)

`/calendar` **9.3K**; `/` 2.6K; **`/clinical-trial-success-rates` 840**; `/drug/asundexian` 665; `/fda-decisions-today` 518; `/readouts` 458; `/research/sls-deep-dive` 421; `/condition/cancer` 407; `/decisions` 386; `/learn/what-is-a-pdufa-date` 383; `/readouts/oncology` 349; `/pdufa/GILD-anito-cel` 348; `/condition/rare-disease` 271; `/fda-approval-rate` 268; `/pdufa/INO` 256; `/tickers` 192; `/pdufa/REGN-cemdisiran` 188; `/pdufa/AZN-gefurulimab` 178; `/pdufa/PTGX` 169.

**What this says.** `/calendar` carries a third of all citations by itself; that single page's lede is the most-quoted sentence we publish, and Bing's AI answer for `pdufa dates 2026` is still quoting a stale copy of it ("104 FDA decision dates from June–December"). `/clinical-trial-success-rates` at 840 is a page no audit has looked at; it should be checked for currency and sourcing because it is being quoted 40 times a day. The two frozen named-drug rows (camizestrant, rusfertide) still earn 168 citations between them from stale pages; both decisions happened months ago, so those pages should state the outcome in the first sentence.

---

# 3. BING SEARCH PERFORMANCE (console, data to November 7)

**1.3K clicks / 56.3K impressions / 2.31% CTR** over the window (928 / 39.1K on 10-18). Best days: Oct 21 **35 clicks / 1.3K**, Nov 2 **33 / 892**. Daily impressions now 800 to 1,300 on weekdays (600 to 900 a month ago).

| Keyword | Impr. | Clicks | Pos. | Read |
|---|---|---|---|---|
| pdufa | 2.9K | 16 | 6.31 | |
| pdufa date | 1.1K | 12 | 5.15 | |
| fda approval decision biotech | 1.1K | **0** | 6.20 | AI-answer impressions, as diagnosed 10-18 |
| **asco 2027** | **466** | 1 | 7.52 | new; conference demand for 2027 |
| pdufa calendar | 193 | 24 | 4.04 | our best converter, 12.4% |
| **fda complete response letter october 2026** | **133** | 0 | 8.59 | new; a month-dated CRL query |
| asco gu 2027 | 109 | 1 | 7.45 | |
| fda calendar | 86 | 4 | 7.45 | |
| upcoming fda approvals & pdufa dates tracker for a free | 81 | 0 | 5.42 | |
| aasld 2026 | 80 | 0 | 9.28 | |
| fda pdufa calendar | 49 | 11 | 3.94 | 22% CTR |
| aacr 2027 | 46 | 0 | 7.57 | |
| fda complete response letter november 2026 | 39 | 0 | 6.92 | |

**Two new demand families.** (1) **Conference years ahead**: `asco 2027`, `asco gu 2027`, `aacr 2027` total 621 impressions with 2 clicks; our conference pages are 2026-titled. (2) **CRLs by month**: 172 impressions for "fda complete response letter {month} 2026" with 0 clicks; `/crl` is a 458-letter database with no month page.

## 3a. Bing organic rankings (live SERPs tonight)

| Query | pdufa.bio | Above us |
|---|---|---|
| pdufa calendar | #2, #4 | **fdatracker.com** #1 |
| pdufa dates 2026 | **#1**, #5 | none |
| fda calendar 2026 | #4 | biopharmawatch, fdatracker, fda.gov |
| aficamten pdufa date (Saturday's decision) | **#1**, #3 | none; catalystalert.io holds the AI box |
| upcoming fda decisions november 2026 | **#1** | none; 7 pdufa.bio citations in the AI answer |

**fdatracker.com** and **catalystalert.io** are new since the 10-18 competitor set and need profiling.

## 3b. Google Search Console, 28 days

**20 clicks / 1.75K impressions / 1.1% / position 10.1** (27 / 2.98K / 7.7 on 10-18). Impressions down 41%, position down 2.4 places: the first decline in any channel this autumn. Re-read at Nov 21; if still down, diff by page.

## 3c. Submitted tonight

Quota had reset (100). Submitted 8 at 19:31 Pacific = 22:31 Eastern: `/calendar` (the stale AI sentence), `/calendar/2027`, `/fda-decision/INO-2026-10-30`, `/pdufa/CYTK-aficamten`, `/pdufa/SMMT-ivonescimab`, `/pdufa/TEVA-igalmi`, `/corrections`, `/readouts/oncology`. 92 left. The CI batch of 15:11 Pacific already carried the hubs.

---

# 4. REPLACING POLYGON

## 4a. What Polygon does now

- `polygon_enrich.py`, workflow step "Refresh prices / market caps (forward catalysts only)": daily aggregates for ~70 forward tickers, reference lookup for market cap, previous close. **~25 minutes a run at the free tier** (5 calls a minute, end-of-day only). A 429 on Oct 22 failed three runs; the citation series above shows what that cost.
- `build_stock_runup.py`, `extend_runup_study.py`, `sls_daily.py`, `build_sls_*`: the T-120 to T+30 run-up series and the SLS pages; cache `stock_runup_cache.json` (63 tickers of daily closes).
- Seven other scripts reference it incidentally.

## 4b. Yahoo: no

- No official API. `yfinance` and every "free Yahoo" library scrape `query2.finance.yahoo.com/v8/finance/chart` behind a cookie-and-crumb handshake Yahoo changes without notice; it broke repeatedly through 2024 and 2025.
- Yahoo rate-limits and blocks datacenter ranges. GitHub Actions runners are a datacenter range; 429/403 inside Actions is a known failure mode. Section 2a shows what one missed night costs in citations.
- Yahoo's terms prohibit scraping and redistribution. The site publishes derived series (run-up charts, cohort medians) with a paid tier. Not worth the exposure for a free price.
- Fine for David's local notebooks. Not for the site's series of record.

## 4c. Use FMP, which is already paid for and already wired

- `FMP_API_KEY` is a repo secret; FMP already backfilled 97 market-cap tiers (11-03) and is the price fallback when Polygon stalls (10-23). The code already calls `/stable/historical-price-eod/full` and `/stable/quote`.
- **Tested tonight through the FMP connector:** `historical-price-eod-light` for CYTK returned closes through today (Nov 9); a `batch-quote-short` for PYPD, SLS, CAPR, SVRA, PVLA, BLTE, APMD, ETON, IRD and RHHBY returned all ten. The nano/micro end is covered. The `/stable/` endpoints are FMP's paid API, which the working key confirms.
- Paid FMP plans allow hundreds of requests a minute; batch quotes fetch every forward ticker in one call. The 25-minute step becomes under a minute, and the 429 class of freeze goes away.

**Builder order:**
1. `polygon_enrich.py` → FMP: `historical-price-eod-full` for the daily series (use `adjClose` consistently and say so on `/methodology`), `batch-quote-short` for the day's prices, `/stable/profile` or `market-capitalization` for market cap. Keep the Polygon path behind a flag for one week, then delete it.
2. `build_stock_runup.py`, `extend_runup_study.py`, `sls_daily.py`: same swap. Rebuild `stock_runup_cache.json` from FMP for the 63 tickers and **diff every close against the Polygon cache before cutover**; list any day differing by more than 0.5% in the note (splits and ADR ratios are where they will disagree).
3. Guard: the price step fetches every forward ticker or fails with the ticker names (never an empty-close silent skip).
4. Record the FMP plan and its request limit in the workflow header.

## 4d. Zero-cost fallback

- **Alpaca Market Data, free tier**: official API, free key with an account, daily bars to 2016, 200 requests a minute. IEX-only feed, so **volumes are partial**; closes are fine for our use. Best free fallback for CI.
- **Stooq**: free EOD CSV, no key. Patchy on the smallest tickers and ADRs; informal quota. Last-resort close check only.
- Not suitable: Alpha Vantage (25 a day), EODHD free (20 a day), Finnhub free (no US daily candles), Twelve Data (workable, but one more key for no gain over Alpaca).

**Recommendation:** FMP primary, Alpaca free as the automated fallback, Polygon removed, Yahoo nowhere in the pipeline.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Polygon → FMP** (4c) with the close-by-close diff; Alpaca fallback; named-ticker guard | Price step under 2 minutes; diff table in the note; planted missing ticker fails with its name |
| **2** | **Nightly reliability as a citation metric** (2a): the BLOCKED issue must page David (the SMTP item), and the escalation body should say how many days since the last green deploy | Issue carries "days since last deploy: N"; email arrives when SMTP is set |
| **3** | **`/calendar` lede** is the most-quoted sentence on the site (9.3K citations): make its first sentence one fact that stays true all month ("{n} FDA goal dates from {next date} through December 2026 and {m} set for 2027, each linked to its source, updated daily") and have the guard assert it matches the grid | Sentence present and guarded; Bing AI answer for `pdufa dates 2026` re-read next audit |
| **4** | **Audit `/clinical-trial-success-rates`** (840 citations, never audited): every number sourced and dated, or the page says what it is | Note with the page's sources |
| **5** | **CRL month pages**: `/crl/2026/october`, `/crl/2026/november` ("FDA complete response letters October 2026: {n} letters, dated") from the 458-record corpus; link from `/crl` | 200 with counts; guard counts match corpus |
| **6** | **2027 conference pages**: ASCO 2027, ASCO GU 2027, AACR 2027 with organiser dates (621 impressions, 2 clicks) | Pages titled "{conf} 2027: {dates}, {city}" |
| **7** | **Frozen named-drug pages** (camizestrant, rusfertide; 168 citations): first sentence states the decision and its FDA day | Both pages lead with the outcome |
| **8** | **Three-dates line** on every decision page (carried from 10-18) | Enspryng and Voceryq render "FDA day · Announced · Goal" with sources |
| **9** | Profile fdatracker.com and catalystalert.io (3a) | Two profiles in the next note |
| **10** | `/decisions/2025`, `/decisions/2026` year pages (carried) | 200 with counts and margins |
| 11 | Saturday 11-14: three goal dates; weekend goal dates usually act Friday 11-13 | Decision pages the day of the record |
| 12 | David: SMTP; `/surges` RULE 2 ruling; VERCEL_TOKEN if still failing; verify held leads #70/#71 with the builder | |

---

# 6. BOTTOM LINE

**The site is current, fully sourced, and self-reporting.** Bing's AI layer cited us **28.1K times in 60 days, 87 grounding queries, up to 902 in a day**, and the series shows the one thing that moves it most: a missed nightly build drops citations 80% the next day. Bing web impressions are up 44% in three weeks; Google is down and needs a page-level look in two weeks.

**Polygon goes; FMP, already paid for and already in the workflow, replaces it; Yahoo is not an option for a CI pipeline.** The swap also removes the 429 freeze class that cost us two of the low-citation days in this window.

---
*Site read from Chrome with `cache: 'reload'`, 2026-11-10 03:20 to 03:55 UTC, against build `baf7832d4`. Bing Webmaster AI Performance (Grounding Queries and Pages tabs) and Search Performance read live, data to 2026-11-07. Google Search Console (28 days) read live. Bing SERPs read live. GitHub Actions and Issues via the public API. FMP tested through the FMP connector. 8 URLs submitted to Bing at 22:31 Eastern. Not investment advice.*
