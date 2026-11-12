# Audit: Google has indexed 56 of our 1,654 pages, and the reason is on our homepage. Also: an FDA approval has sat in quarantine for 30 hours on our fourth most-cited page
**2026-11-10, measured 23:20 Eastern to 00:15 Eastern Nov 11 = 2026-11-11 04:20 to 05:15 UTC (Tuesday night).** *Per RULE 1 every time carries its zone. Bing console shows Pacific; Google Search Console dates are Pacific-day.*
**Live build `10143572b`, generated 2026-11-11T01:05Z (20:05 Eastern). API 505 rows. Last three scheduled runs green. Next decisions CYTK / SMMT / TEVA, Saturday 2026-11-14.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. P0: six held leads, two of them real FDA actions from Monday

`/build-info.json` `held_leads`, with GitHub issues #70 to #77 open:

| Lead | Held since (UTC) | What the builder's own 11-10 note found |
|---|---|---|
| `drug:asundexian` | Nov 9, 22:50 | **Real.** FDA press announcement Nov 9: **Sunharbo (asundexian) 50 mg approved**, first factor XIa inhibitor, Bayer. Not published |
| `pdufa_nvcr_2026-11-15` | Nov 9, 20:50 | **Real.** Novocure 8-K Nov 9: FDA **Not Approvable Letter** on the Optune Mya PMA. Not published |
| `drug:enflonsia` | Nov 10, 17:27 | unverified |
| `pdufa_jazz_2027-04-16` | Nov 10, 17:27 | unverified (FDA drugs feed) |
| `pdufa_bmy_2027-05-13` | Nov 10, 19:26 | unverified (FDA drugs feed) |
| `pdufa_capr_2026-08-22` | Nov 11, 01:00 | unverified (EDGAR); CAPR's goal is Nov 22 |

**Why asundexian is the urgent one.** `/drug/asundexian` is our **fourth most-cited page in Bing's AI layer (665 citations)**; "asundexian fda approval" is a top-ten grounding query (165 citations) and "asundexian pdufa date" is our highest share on any drug (58.54%). The live page tonight is titled "Asundexian: FDA Decision Dates & Catalyst History" and says **"under FDA review"**, 30 hours after the FDA announced the approval. The dataset has no asundexian row at all. `/fda-decisions-today` says "the most recent was INO's VOCERYQ… October 30". Every AI answer about asundexian that grounds on us today is wrong, on the page that earns us the most trust.

The builder verified both on the night of Nov 9 to 10 and wrote "both need decision records next". They did not get them. **Publish both now:**
- **Sunharbo:** `/fda-decision/BAYRY-2026-11-09`, FDA day from the FDA's announcement, `goal_unsourced` (no sponsor-stated goal day), no margin, not in the census. The drug page leads "The FDA approved Sunharbo (asundexian) on November 9, 2026".
- **Optune Mya:** the outcome is a **Not Approvable Letter on a PMA**, a device outcome. Not a CRL and not a "rejection". New outcome label, the 8-K sentence quoted, the NVCR row closed. It must not enter the CRL counts.
- Then triage the other four the same day. A held lead older than 24 hours on a page with more than 100 AI citations should escalate by itself; add the page's citation rank (a static list of the top 25 pages is enough) to the ESCALATION issue.

---

# 1. GOOGLE: THE REAL PICTURE

## 1a. The email

"Redirect error: 19 pages validated as fixed" is real and good; the Page indexing report shows Redirect error "Passed", 3 pages remaining. It is also the smallest number on the page.

## 1b. Page indexing report (last update Nov 5)

| | Pages |
|---|---|
| **Indexed** | **56** |
| **Not indexed** | **1,580** |
| of which **Discovered – currently not indexed** | **1,562** |
| Page with redirect | 9 |
| Not found (404) | 5 |
| Redirect error | 3 |
| Alternate with canonical / Crawled not indexed | 1 / 1 |

Sitemap: `sitemap.xml`, read Nov 10, **Success, 1,654 discovered**. So Google knows every URL and has indexed 3.4% of them. For the 1,562, "Last crawled" is **N/A**: Google has never fetched them.

**What is indexed (all 56 read):** the homepage, `/calendar` and six month pages, `/conferences`, `/screener`, `/decisions`, `/readouts`, `/research`, `/methodology`, `/developers`, `/pricing`, `/tickers`, ~20 big-pharma `/ticker/` hubs, a handful of bare `/pdufa/{TICKER}` pages from August. **What is not:** `/fda-decisions-today`, `/fda-approval-decisions-this-week`, `/crl`, `/research/fda-decision-timing`, `/calendar/2027`, **every one of the 60 current event pages** (CYTK, SMMT, TEVA…), **every decision page since August** (Tecentriq, Enspryng, Anktiva…), all conference pages, all drug pages but two.

That is why Google gives us 20 clicks a month while Bing gives 1,300. It is not a ranking problem. The pages are not in the index.

## 1c. Why: crawl stats and links

- **Crawl stats, 90 days:** 2,210 requests total, about 25 a day. **95% "Refresh", 5% "Discovery".** Google spends its small budget re-fetching the 56 pages it knows and almost nothing on new ones. Response time 152 ms, 94% 200s: the server is not the problem. 10% of requests go to JSON.
- **External links:** **89 in total, from five sites** (biotechtracker.dev 28, synbiomatica.com 24, theclosingprint.net 24, debao.com 4, nexus-signal.com 2), to five pages. Google allots crawl by demand, and demand is links.
- **Internal links, as Google sees them:** 710 in total; the best-linked page has 55. With 56 indexed pages that means Google's whole view of our site is the nav.
- **The cause we control.** URL Inspection on `/fda-decisions-today`, `/crl` and `/pdufa/SMMT-ivonescimab` each says **"Referring page: None detected"**. I checked the static HTML:

| Page | Linked from the homepage HTML | Linked from `/calendar` HTML |
|---|---|---|
| `/fda-decisions-today` | **no** | **no** |
| `/fda-approval-decisions-this-week` | **no** | **no** |
| `/crl` | **no** | **no** |
| `/research/fda-decision-timing` | **no** | yes |
| `/decisions/2026`, `/corrections`, `/fda-approval-letters`, `/readouts/oncology` | **no** | **no** |
| `/pdufa/CYTK-aficamten`, `/pdufa/SMMT-ivonescimab` (Saturday's decisions) | **no** | yes |
| `/calendar/2027` | yes | yes |

**The homepage carries 67 internal links, and none of them goes to the daily pages, the CRL database, the studies, or the event pages of the next decisions on its own "Next FDA decisions" board** (those rows are either script-rendered or link to ticker hubs). There is no HTML sitemap (`/sitemap` 404). Bing does not care: it takes URLs from IndexNow and the sitemap. Google does: it crawls by following links from pages it trusts, and from our two strongest pages it cannot reach most of the site.

## 1d. Performance

28 days: **20 clicks, 1.41K impressions, 1.4% CTR, position 11.4** (1.75K / 10.1 last night's window; 2.98K / 7.7 on Oct 18). Still sliding. With 56 pages indexed there is little to slide from; the fix is 1c, not titles.

## 1e. What I did tonight in Google

Requested indexing through URL Inspection (each confirmed "Indexing requested, added to a priority crawl queue"): `/fda-decisions-today`, `/pdufa/CYTK-aficamten`, `/pdufa/SMMT-ivonescimab`, `/pdufa/TEVA-igalmi`, `/calendar/2027`, `/fda-approval-decisions-this-week`, `/research/fda-decision-timing`. `/crl` was requested but I did not see the confirmation; treat as unconfirmed. Google allows roughly ten a day, so this is a tap, not a pipe. **Do not submit `/drug/asundexian` to anyone until it is correct.**

---

# 2. BING (console, data to November 8)

One more day of data than last night; nothing has moved. AI: **28.2K citations, 87 grounding queries**, Nov 7 665; `asundexian fda approval` 155 → **165**; "free tracker" query 117 → 125. Web: **1.3K clicks / 56.3K impressions**; Nov 8 (Sunday) 12 clicks / 382. `fda complete response letter november 2026` 39 → **53** impressions, still 0 clicks; the new `/crl/2026/november` page exists for it now.

**Submitted to Bing tonight** (quota was 60; CI's 17:09 Pacific batch had sent 40 with the hubs first): `/decisions/2026`, `/decisions/2025`, `/decisions/approvals`, `/decisions/crl`, `/crl`, `/crl/2026/october`, `/crl/2026/november`, `/clinical-trial-success-rates`, `/drug/camizestrant`, `/drug/rusfertide`, `/conference/ASCO`, `/ASCO-GU`, `/AACR`, `/research/fda-decision-timing`, `/methodology`. 45 left.

---

# 3. THE BUILDER'S 11-10 NOTE: VERIFIED

- **Polygon → FMP is live and held through three scheduled runs.** Price step 13 seconds in CI (23 minutes before). The builder was right to refuse my `adjClose` suggestion: that is FMP's dividend-adjusted series and would have shifted every run-up figure on dividend payers against a study built on split-only closes. **Retracted.** The close-by-close diff (17,349 closes, 87 differences, 86 of them AZN before its Feb 2 ADR-to-ordinary switch) is exactly the evidence asked for.
- BLOCKED issues now carry "Days since last green deploy"; #73 proved it.
- `/calendar` lede: "24 FDA PDUFA goal dates are still ahead in 2026, the next on November 14, 2026, and 37 more are already set for 2027…". Live and guarded.
- `/decisions/2025`, `/decisions/2026`, `/crl/2026/october`, `/methodology`, `/pdufa/NVO-mim8` ("not announced") all 200. `/clinical-trial-success-rates` corrected against BIO's 2011–2020 report (the caption had the 2006–2015 sample).
- Currency otherwise clean: 0 past-due, 55 of 55 day-dated upcoming rows sourced, census 36: 22/13/1.
- Carried by the builder and still open: `_crl_capture_series.json` is not in the workflow's `git add` list, so the series stopped at Oct 18.

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **0** | **Publish Sunharbo (asundexian) and the Optune Mya Not Approvable Letter today; triage the other four held leads** (§0). ESCALATION issues name the page's AI-citation rank | `/drug/asundexian` leads with the approval and its FDA day; decision page 200; `held_leads` ≤ 1; NVCR row closed with a device-letter label, outside the CRL counts |
| **1** | **Homepage links, in static HTML:** (a) every row of "Next FDA decisions" is an `<a href>` to its event page; (b) a "Today and this week" block linking `/fda-decisions-today` and `/fda-approval-decisions-this-week`; (c) a "Recent FDA decisions" block with the last 10 decision pages; (d) a footer on every page linking `/crl`, `/fda-approval-letters`, `/corrections`, `/research/fda-decision-timing`, `/decisions/2026`, `/readouts/oncology`, `/calendar/2027`, `/conferences` | Guard: every indexable URL in the sitemap is reachable by `<a href>` within **3 clicks of `/`** in built HTML; prints the orphan count (expect hundreds today), must be 0. 0 → planted orphan → 0 |
| **2** | **HTML sitemap at `/sitemap`**: one page (or a few) listing every indexable URL by section, linked from the footer | 200; in the footer; counted by the reachability guard |
| **3** | **Related links on every leaf page:** an event page links its ticker hub, drug page, month page and the 3 nearest decisions; a decision page links its event page, drug page, the year page and the 3 previous decisions; a drug page links its sponsor's hub and every decision | Median inbound internal links per indexable page ≥ 5 (print the distribution) |
| **4** | **Sitemap hygiene for crawl budget:** `<lastmod>` only on real content change (done 10-13; confirm the nightly "lastmod == today" count is in the dozens); drop `noindex` and redirected URLs from the sitemap (the report still shows 9 "Page with redirect" and 5 404s); `Disallow: /build-info.json` and the non-`/api/v1/` JSON that takes 10% of Googlebot's requests | Next-audit crawl stats: Discovery share above 20% |
| **5** | **A daily Google list for David or me:** the build writes `_google_request_indexing.txt` with the 10 highest-value non-indexed URLs (new decision pages first, then this week's event pages), since Google's Indexing API is not open to this content type and URL Inspection allows about 10 a day | File written each run; I or David work it down |
| **6** | **Links from outside** (10-17b §3, still the root of Google's low crawl demand): the CC-BY census CSV and `/corrections` exist; add the "Cite this page" line to decision and study pages. David: one note to the three sites already linking us (biotechtracker.dev, synbiomatica.com, theclosingprint.net) is worth more than any on-page change | Cite line live; David's call on outreach |
| 7 | `_crl_capture_series.json` into `git add`; remove `POLYGON_API_KEY` after Nov 17 | |
| 8 | Saturday 11-14 runbook (CYTK, SMMT, TEVA); watch Friday | Decision pages the day of the record |
| 9 | David: SMTP; `/surges` ruling; Alpaca keys (optional) | |

---

# 5. BOTTOM LINE

**Bing and its AI layer: 28K citations and climbing, fed by IndexNow and a sitemap.** That channel is working, with one live wound: our most-watched drug page says "under FDA review" a day and a half after the FDA approved the drug. Publish it first.

**Google: 56 pages indexed out of 1,654, and the email about 19 fixed redirects is a footnote to that.** Google has never fetched the other 1,562 because it crawls by links, we have 89 inbound links from five sites, and our own homepage does not link to the today page, the CRL database, the studies, or the event pages of this week's decisions. The first of those takes months to change. The last one takes an afternoon, and it is the highest-value search work left on the site.

---
*Site read from Chrome with `cache: 'reload'`, 2026-11-11 04:20 to 05:15 UTC, against build `10143572b`. Google Search Console read live: Page indexing (updated 11/5), indexed-pages list (all 56), Sitemaps, Crawl stats (to 11/8), Links, Performance (28 days), URL Inspection on 8 URLs. Bing Webmaster AI Performance, Search Performance (to 11/8) and URL Submission read live. GitHub via the public API. Requested Google indexing for 7 URLs (1 more unconfirmed); submitted 15 URLs to Bing. Not investment advice.*
