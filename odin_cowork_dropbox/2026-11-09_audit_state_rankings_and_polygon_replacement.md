# Audit: current state, AI and search rankings, and replacing Polygon for prices
**2026-11-09, measured 22:20 to 22:40 Eastern = 2026-11-10 03:20 to 03:40 UTC (Monday night).** *Per RULE 1 every time carries its zone.*
**Live build `baf7832d4`, generated 2026-11-09T23:07:27Z (18:07 Eastern). API 505 rows: 120 PDUFA, 335 Readout, 43 Conference, 2 AdComm. Next decisions CYTK / SMMT / TEVA, 2026-11-14 (Saturday). Two leads held since 20:50 UTC (NVCR 11-15 via 8-K; asundexian drug page), issues #70 to #72 open; the rest of the site deploys.**
*Facts and build mechanics only. Not investment advice.*

**Client note:** Bing Webmaster has signed out again, so there are no console numbers (AI Performance, Search Performance) in this audit. Bing rankings below are read from live SERPs. Google Search Console was signed in. **David: sign in to Bing Webmaster and say so; I will read the AI Performance report and append.**

---

# 1. STATE: CLEAN, AND THREE WEEKS OF BUILDER WORK VERIFIED

| Check | Live |
|---|---|
| Day-dated PDUFAs past goal and not Decided/Withdrawn | **0** |
| Non-day rows with a date / month mismatch | 0 / 0 |
| Conferences mislabelled against the Eastern date | 0 |
| Upcoming PDUFAs | 62; **55 day-dated, 55 sourced; 0 unsourced** (the AZN/NVO trio is resolved: Ultomiris approved Oct 21, Mim8 and CagriSema re-sourced to Novo's 6-Ks) |
| Timing census | **36: 22 early / 13 on the day / 1 late**, consistent on `/calendar`, `/learn`, `/research`, `/llms.txt` |
| Readouts | 335 rows; bare "Window passed" 2 |
| Freshness | "Data as of Nov 9, 2026 6:07 PM ET"; badge "Data through Nov 9" (the UTC-date defect the builder found 11-08 is fixed) |
| Today page | "No FDA decision… published today, November 9, 2026" |
| GitHub | last 3 scheduled runs green; 6 failures Nov 7 to 9 were the conference-stamp guard (BLOCKED #63, closed). **The silent-freeze fix works: every freeze since 10-18 opened a BLOCKED issue** (#54, #63) |

**Orders from the 10-18 audit, checked live:** `/corrections` 200; `/calendar/2027` 200; `/readouts/oncology` 200; `/conference/ASH` 200; `goal_date_held` on the API and `/developers`; PBYI and VYGR hubs now `index,follow`; Enspryng page now "Approved Oct 15, 2026" (the FDA letter posted and the row entered the census); RYZUMVI "Approved Oct 16, 2026, 1 Day Early". **Not done:** `/decisions/2025` (404); the three-dates line on decision pages (Enspryng page does not render "FDA day: …"); free `.ics`; email alert (blocked on SMTP, David's).

**Builder work since 10-18 I verified live or against its sources:** 21 goal dates found on no surface by an EDGAR full-text sweep and added (11-03); four more 11-05 to 11-08 (URGN, COGT AdvSM, VSTM, Mim8/CagriSema re-sourcing); the CYTK indication corrected from non-obstructive to obstructive HCM five days before its decision; 97 run-up rows that had no market-cap tier backfilled; the homepage JSON-LD that still listed July events replaced; mobile nav on 1,209 pages; source line with the sponsor's own sentence on 58 event pages; `/screener` rebuilt from the dataset after sitting on a July snapshot; `/surges` noindexed (a hypestock product on pdufa.bio: **RULE 2, David's ruling still open**).

One thing to watch: the INO Voceryq decision was published Oct 30 on the goal date, but Bing's AI answer for "upcoming fda decisions november 2026" now says "Voceryq … (Nov 3, 2026)". Bing is dating it from a later article, not from us. The decision page should lead with the FDA's own day in its first sentence, which is the three-dates line already ordered.

---

# 2. RANKINGS

## 2a. Bing, organic (live SERPs tonight)

| Query | pdufa.bio | Who is above us |
|---|---|---|
| `pdufa calendar` | **#2 and #4** | **fdatracker.com** #1 |
| `pdufa dates 2026` | **#1 and #5** | none |
| `fda calendar 2026` | #4 | biopharmawatch #1, fdatracker #2, fda.gov #3 |
| `aficamten pdufa date` (this week's decision) | **#1 and #3** | none; Cytokinetics IR #2 |
| `upcoming fda decisions november 2026` | **#1** | none |

Two names that were not in the 10-18 competitor set are now above or beside us: **fdatracker.com** (#1 for `pdufa calendar`, #2 for `pdufa dates 2026`, #2 for `fda calendar 2026`) and **catalystalert.io** (holds the AI answer for `aficamten pdufa date` with "label update based on MAPLE-HCM"). The builder should profile both the way the 10-18 audit profiled the other ten; I have not yet.

## 2b. Bing, AI answers

- `pdufa dates 2026`: the answer opens with *"The 2026 PDUFA calendar on pdufa.bio lists 104 FDA decision dates from June–December 2026, updated daily, with each entry linked to its FDA or company source."* That sentence is ours and it is **stale** (the live calendar says 25 through December plus 37 for 2027). It is lifted from a cached `/calendar` lede. The ordered-submission work is in; this is Bing's re-grounding lag, which only Request indexing in the console beats.
- `upcoming fda decisions november 2026`: 7 pdufa.bio citations in the answer.
- `aficamten pdufa date`: catalystalert.io holds the answer box, with the correct obstructive-HCM wording. Our page says the same since 11-05. On Saturday the page that states the FDA day first will take it.

## 2c. Google Search Console, 28 days to ~Nov 7

**20 clicks, 1.75K impressions, 1.1%, position 10.1.** On 10-18 it was 27 / 2.98K / 7.7. Impressions down 41%, position down 2.4 places. This is the first clear decline in any channel this autumn, and it coincides with a Google core-update window; it also coincides with 1,900 pages receiving a new nav block and og image. Not actionable yet beyond watching; if the 28-day window to Nov 21 is still down, the builder should diff which pages lost impressions (Search Console → Pages, compare periods).

---

# 3. REPLACING POLYGON

## 3a. What Polygon does for us today

- `polygon_enrich.py` (workflow step "Refresh prices / market caps, forward catalysts only"): daily aggregates (`/v2/aggs/ticker/{t}/range/…`) for ~70 forward tickers, plus `/v3/reference/tickers/{t}` for market cap, plus `prev` close. The builder's 11-05 note: **~25 minutes per run at the free-tier rate**. Polygon's free tier is 5 calls a minute, end-of-day only, and on 10-22 a 429 failed three runs. (Polygon rebranded as Massive in 2025; the API and limits are the same.)
- `build_stock_runup.py`, `extend_runup_study.py`, `sls_daily.py`, `build_sls_*`: the run-up series (T-120 to T+30) and the SLS pages. Cached in `stock_runup_cache.json` (63 tickers, daily closes).
- Seven other scripts reference it incidentally.

## 3b. Yahoo: the honest answer is no, for CI

- Yahoo Finance has **no official API**. `yfinance` and every "free Yahoo" library scrape an undocumented endpoint (`query2.finance.yahoo.com/v8/finance/chart`) behind a cookie-and-crumb handshake that Yahoo changes without notice; it broke repeatedly in 2024 and 2025.
- Yahoo rate-limits and blocks datacenter IP ranges. **GitHub Actions runners are a datacenter range**, and 429/403 from Yahoo inside Actions is a well-known failure mode. A nightly build that depends on it will freeze the site on a random night, which is exactly the class of failure the quarantine and BLOCKED issues were built to stop.
- Yahoo's terms prohibit scraping and redistribution. pdufa.bio publishes derived series (run-up charts, cohort medians) on a public site with a paid tier. That is a licensing exposure the free price is not worth.
- It is fine for David's local notebook work. It is not fine as the price source of record for the site.

## 3c. The replacement is already in the workflow: FMP

- `FMP_API_KEY` is already a repo secret, already used for the 97-row market-cap backfill (11-03) and as the price fallback when Polygon stalls (10-23), and the code already calls `financialmodelingprep.com/stable/historical-price-eod/full` and `/stable/quote`.
- I tested it tonight through the FMP connector: `historical-price-eod-light` for CYTK returned closes through **today (Nov 9)**; a batch quote for ten of our smallest tickers (PYPD, SLS, CAPR, SVRA, PVLA, BLTE, APMD, ETON, IRD, RHHBY) returned all ten. Coverage of the nano/micro end is there. The `/stable/` endpoints are FMP's paid API (Starter plan and up), which the working key confirms.
- Paid FMP plans allow hundreds of requests per minute, so the 25-minute Polygon step becomes well under a minute, and the batch-quote endpoint fetches every forward ticker's price and volume in one call.

**Order for the builder:**
1. `polygon_enrich.py` → FMP: `historical-price-eod-full` for the daily series (it includes adjusted close, which Polygon's aggs did not; use `adjClose` consistently and say so on `/methodology`), `batch-quote-short` for the day's prices, and `/stable/profile` (or `market-capitalization`) for market cap. Keep the Polygon code path behind a flag for one week as the fallback, then delete it.
2. `build_stock_runup.py` / `extend_runup_study.py` / `sls_daily.py`: same swap. Rebuild `stock_runup_cache.json` from FMP for the 63 tickers and **diff the closes against the Polygon cache before switching**: any day whose close differs by more than 0.5% gets listed in the note. Splits and ADR ratios are where the two will disagree.
3. One guard: the price step must fetch every forward ticker or fail loudly with the ticker names (the 10-22 pattern was an empty-close 429 that failed three runs silently).
4. Record which plan the key is on and its request limit in `_sponsor_coverage.json` or the workflow header, so the next person does not guess.

## 3d. If a zero-cost second source is wanted

For a fallback that costs nothing and does not scrape:
- **Alpaca Market Data (free tier):** official API, free key with an account, daily bars back to 2016, 200 requests a minute. Its free feed is IEX-only, so **volumes are partial** (IEX's share of the tape); closes are fine for our use. Best free option for a CI fallback.
- **Stooq:** free end-of-day CSV with no key (`stooq.com/q/d/l/?s=cytk.us&i=d`). Good for large and mid caps; coverage of the smallest tickers and ADRs is patchy, and there is an informal daily quota. Usable as a last-resort close-of-day check, not as the series of record.
- Not suitable: Alpha Vantage (25 requests a day), EODHD free (20 a day), Finnhub free (no US daily candles), Twelve Data free (800 credits a day; workable but another key to manage for no gain over Alpaca).

**My recommendation:** FMP primary (already paid for, already wired), Alpaca free as the automated fallback, Polygon removed. Yahoo nowhere in the pipeline.

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Polygon → FMP** (3c), with the close-by-close diff in the note; Alpaca free fallback; guard that names missing tickers | Price step under 2 minutes in CI; diff table in the note; a planted missing ticker fails the guard with its name |
| **2** | **Three-dates line on every decision page** (carried from 10-18): "FDA day: {letter date} · Announced: {sponsor} {date} · Goal: {source} {date}" | Enspryng and Voceryq pages render it; guard |
| **3** | Profile **fdatracker.com** and **catalystalert.io** (2a) as on 10-18; report what they source and how fresh they are | Two profiles in the next note |
| **4** | `/decisions/2025` and `/decisions/2026` year pages (carried) | 200 with counts and margin column |
| **5** | Saturday 11-14: three goal dates (CYTK, SMMT, TEVA). Weekend goal dates usually act on the Friday; watch Friday 11-13 from the morning. Same runbook | Decision pages the day of the record |
| 6 | David: Bing Webmaster sign-in (then I read AI Performance); SMTP for the free alert; `/surges` RULE 2 ruling; VERCEL_TOKEN if still unauthenticated; the two held leads #70/#71 are the builder's to verify |  |

---

# 5. BOTTOM LINE

**The site is current, fully sourced, and self-reporting its freezes.** Every day-dated upcoming decision has a sponsor sentence behind it, the census is at 36 and consistent, and three weeks of builder sweeps found and fixed real gaps (21 unpublished goal dates, a wrong indication on this week's decision, a July snapshot on the screener).

**Rankings:** first or second on Bing for the head terms and for this week's decision; a new competitor, fdatracker.com, is ahead on `pdufa calendar`. Google has slipped for the first time this autumn and needs a page-level diff in two weeks.

**Polygon:** replace it with FMP, which is already paid for, already in the workflow, and returned today's prices for our smallest tickers in my test tonight. Not Yahoo: no API, blocks CI runners, and its terms do not allow what the site does with the data.

---
*Site read from Chrome with `cache: 'reload'`, 2026-11-10 03:20 to 03:40 UTC, against build `baf7832d4`. GitHub Actions and Issues via the public API. Bing SERPs read live. Google Search Console (28 days) read live. FMP tested through the FMP connector (CYTK daily history; ten-ticker batch quote). Bing Webmaster not read (signed out). Not investment advice.*
