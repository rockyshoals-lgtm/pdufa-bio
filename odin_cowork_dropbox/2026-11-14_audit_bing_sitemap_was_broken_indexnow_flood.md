# Red-team audit: the two "failing URLs" were a symptom. Bing could not read our sitemap for a week (fixed tonight), and we are flooding IndexNow with 50 times what Bing crawls
**2026-11-14, measured 23:04 Eastern to 00:20 Eastern Nov 15 = 2026-11-15 04:04 to 05:20 UTC (Saturday night, the CYTK / SMMT / TEVA goal day).** *Per RULE 1 every time carries its zone. Bing console times are Pacific.*
**Live build `71a6b6993`, generated 2026-11-15T00:42Z (19:42 Eastern). API 507 rows. Six scheduled runs green. 0 held leads, 0 open issues.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE TWO "FAILING" URLS

`/fda-decision/INO-2026-10-30` and `/pdufa/BBIO-infigratinib` are listed in Bing Webmaster → Recommendations under **"Important pages missing in sitemaps" (High, 2 pages)**.

**Neither page is failing.** Checked from the browser and from a second, non-browser client:

| Check | INO-2026-10-30 | BBIO-infigratinib |
|---|---|---|
| HTTP status | 200 | 200 |
| robots meta | index,follow | index,follow |
| canonical | itself | itself |
| JSON-LD | 2 blocks, both parse | 2 blocks, both parse |
| In `sitemap.xml` | **yes** | **yes** |
| Bing URL Inspection | "Indexed successfully"; 1 issue: Title too long | "Indexed successfully"; no issues |

**The real cause was one screen away.** Bing Webmaster → Sitemaps showed:

| Sitemap | Last crawl | Status | URLs |
|---|---|---|---|
| `https://www.pdufa.bio/sitemap.xml` | **11/7/2026** | **Error: "We encountered an issue when we tried to download this sitemap"** | **0** |
| `https://pdufa.bio/sitemap.xml` (apex, discovered in March) | 6/8/2026 | Success | 47 |

Bing failed to download the sitemap on Nov 7, during the Nov 6 to 9 freeze, and **never retried**. For a week Bing's only readable sitemap was a 47-URL file from June. Any page newer than that looked "missing from sitemaps"; these two were simply the ones Bing ranked as important.

**I validated the live sitemap:** 200, `application/xml`, 246,832 bytes, well-formed, 1,685 URLs, 0 duplicates, 0 bad `lastmod`, 0 future dates. **I then pressed Re-submit. Bing now shows: Success, last crawl 11/15/2026, 1.7K URLs discovered.** The recommendation should clear on Bing's next scan.

**Builder orders from this:**
1. **Nobody watches Bing's view of the sitemap.** `ping_search_engines.py` submits the sitemap to Google's API only. Add a Bing sitemap submit each run (Bing Webmaster API `SubmitFeed`, same key as SubmitUrlBatch) and print the response.
2. **Why did the Nov 7 download fail?** The sitemap is served as a static file. Check the Vercel logs for a bingbot request to `/sitemap.xml` on Nov 7 (5xx, timeout, or a deploy in flight). If it cannot be found, say so.
3. **Remove the stale apex sitemap** from Bing (David, in the console: Sitemaps → the `pdufa.bio/sitemap.xml` row → delete). Its 47 URLs are a June snapshot on the non-canonical host.
4. **A stale `middleware.ts` sits in the repo root** with `MAINTENANCE_MODE = true` (dated Aug 3). It is not in the deployed site directory and the site serves normally, but a file that would lock the whole site if it were ever picked up should be deleted.

---

# 2. P1: WE ARE FLOODING INDEXNOW

Bing Webmaster → IndexNow → Insights:

| | 90 days |
|---|---|
| **URLs submitted via IndexNow** | **517,900** |
| URLs Bing crawled from them | 11,100 |
| URLs indexed from them | 11,000 |
| Submitted in the **last 4 hours** | **2,900** |
| Recent days | 11.8K, 7.3K, 6.7K, 4.5K, 3.1K |

The site has 1,685 URLs. We submit **every URL several times a day**: `ping_search_engines.py` sends "the priority list followed by the rest" (`MAX_URLS = 8000`) to **two endpoints** (`api.indexnow.org` and `bing.com/indexnow`, which share the same back end), on three scheduled runs a day. That is roughly 1,685 × 2 × 3 ≈ 10K a day. Tonight's sitemap shows only **220 URLs with today's `lastmod`**, so about 87% of each submission is pages that did not change.

Bing crawls **2%** of what we send. IndexNow's own documentation says to submit only URLs that were added, updated or deleted, and that excessive submission can get a key ignored. The builder's own docstring in the same file says bulk submission "trains the engine to ignore" us. The 10-13 fix ordered the list; it did not shorten it.

**Order:** IndexNow gets **only URLs whose content hash changed in this run** (plus new and deleted URLs), to **one** endpoint (`api.indexnow.org` fans out to Bing). Print the count each run. Guard: the IndexNow payload is a subset of this run's changed-hash set; a run with no changes submits nothing. Expected volume: a few hundred a day, not ten thousand.

---

# 3. CURRENCY

| Check | Live |
|---|---|
| **Today's goals: CYTK aficamten, SMMT ivonescimab, TEVA IGALMI** | All three still "Upcoming" at 23:04 Eastern on the goal day. **No decision found:** Bing News shows "FDA decision due today" (6 hours old) for aficamten and nothing newer for ivonescimab or IGALMI. No held leads. They become "Awaiting" at Eastern midnight, as designed. Weekend goal dates often resolve Monday; watch from Monday 07:00 Eastern |
| Day-dated PDUFAs past goal and undecided (before today) | 0 |
| Non-day rows with a date / month mismatch | 0 / 0 |
| Conferences mislabelled | 0 |
| Upcoming PDUFAs | 58; 55 day-dated, **55 sourced** |
| Census | 36: 22 / 13 / 1, consistent |
| Asundexian | `/drug/asundexian` titled "Sunharbo (asundexian) FDA Approval: Approved Nov 9, 2026". **Fixed** |
| Pimjetmi, Optune Mya, Gazyva pMN (Nov 13) | All published; Gazyva correctly `decision_date_unsourced` |
| Freshness | "Data as of Nov 14, 2026 7:42 PM ET" |

**The builder's 11-11 and 11-13 work, verified live:**
- Homepage now 102 links (67 before); `/sitemap` 200; the builder reports all 1,654 URLs within 3 clicks and 0 orphans.
- Polygon is fully removed; FMP price step 12 seconds.
- Feed-date fix in, and it caught a second republished notice (Trodelvy 2021) the day after.
- `runup_summary` in the API was **placeholder data on 68 rows** (the same five value sets repeated); it is now measured per row. That was a real integrity defect on a facts-only API, found by the builder, not by me.

The builder was also right that my 11-10 audit never reached it: the file sat uncommitted in the dropbox. **I write to the dropbox folder; I do not commit.** If the builder only reads committed notes, David needs to tell it to read the folder, or tell me to hand the file over another way.

---

# 4. BING AND AI (console, data to Nov 12)

**AI Performance.** I must correct my own series: my script dropped every daily value of 1,000 or more, so recent audits under-reported.

| | Nov 9 | Nov 10 | Nov 11 | Nov 12 |
|---|---|---|---|---|
| **AI citations** | **1.2K** | **1.1K** | 818 | **1.2K** |
| Cited pages | 64 | 84 | 67 | **92** |

**Four-figure days for the first time.** Totals: **32.4K citations** (28.2K three days ago), **101 grounding queries** (87), average cited pages 36. `pdufa date` 2.2K (24.78%); `asundexian fda approval` **296** (was 165), its share fell to 15.28% while our page was wrong, and `asundexian pdufa date` 164 at 65.86%; "free tracker" query 125 → **225**; `pdufa calendar` 214 at **49.31%**.

**Search Performance.** Totals 1.4K clicks / 59K impressions / 2.35%.

| | Nov 9 | Nov 10 | Nov 11 | Nov 12 |
|---|---|---|---|---|
| Impressions | 1.2K | 1.1K | 966 | 1.1K |
| **Clicks** | **43** | 30 | 15 | **37** |

**43 clicks on Nov 9 is the best day on record** (35 on Oct 21). `asundexian fda approval` is now a web keyword too: 53 impressions, 4 clicks.

**Recommendations: "Title too long", High severity, 59 pages.** Bing's limit is about 70 characters; the INO page's title is 71. Decision titles end "… | {TICKER} FDA Decision | pdufa.bio", which costs 30 characters. **Order:** decision titles drop the trailing "| pdufa.bio" when the title exceeds 65 characters (Bing and Google both append the site name themselves). Guard: no indexable title over 70.

---

# 5. GOOGLE

- Page indexing report is still dated **11/8**, before the linking work shipped: 55 indexed, 1,568 "Discovered – currently not indexed". No verdict possible yet on whether links are moving it; re-read when the report passes 11/15.
- Performance, 28 days: 20 clicks, **1.16K impressions**, position 13.3 (1.34K / 12.3 three days ago). Still falling.
- **Requested indexing does work:** `/pdufa/SMMT-ivonescimab` and `/pdufa/TEVA-igalmi`, requested Nov 10, are now **"URL is on Google"**. That is 5 of 5 checked so far.
- **Requested tonight, each confirmed** (from the builder's `_google_request_indexing.txt`): `/fda-decision/BAYRY-2026-11-09`, `/drug/asundexian`, `/fda-decision/RHHBY-2026-11-13`, `/fda-decision/MKKGY-2026-11-10`, `/fda-decision/NVCR-2026-11-09`, `/pdufa/BBIO-bbp-418`, `/fda-approvals/2026/october`. Builder: mark these seven requested, and SMMT, TEVA as indexed, in `_google_requested.json` / `_google_indexed.json`. The Sunharbo decision page still showed "Referring page: None detected", which is expected until Google re-crawls the homepage.

**100K check:** Bing's last 30 days are about 25K impressions with the last four weekdays at 1.0K to 1.2K; Google about 1.2K. Unchanged picture: Bing is at a new high-water mark, and Google decides whether 100K is reachable.

---

# 6. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **IndexNow: changed URLs only, one endpoint** (§2) | Payload ⊆ this run's changed-hash set; count printed; next audit's 4-hour figure in the low hundreds |
| **2** | **Bing sitemap watched** (§1): submit the sitemap to Bing each run and log the response; investigate the Nov 7 download failure | CI log line; note on the cause or "not found" |
| **3** | **Titles ≤ 70 characters** on the 59 flagged pages (§4) | Guard 0 → 1 → 0; Bing recommendation clears |
| **4** | **Monday: CYTK, SMMT, TEVA.** If still undecided past goal, the pages say "goal date passed, no decision announced as of {date}" with the check date | Decision pages the day of the record, or dated "awaiting" text |
| **5** | Delete root `middleware.ts`; record tonight's Google requests in the state files | Done |
| **6** | Carried: "Cite this page" line; drug pages for the 24 new-molecular-entity approvals without one; `/surges` ruling | |
| 7 | David: delete the apex sitemap row in Bing; delete the `POLYGON_API_KEY` secret; make sure the builder reads uncommitted audit files in the dropbox; SMTP; outreach | |

---

# 7. BOTTOM LINE

**The two URLs were never broken.** Bing had been unable to read our sitemap since Nov 7 and was working from a 47-URL file from June. It reads all 1,685 now. Nothing in the build watches for that, and something should.

**The larger finding is the IndexNow flood:** 518K submissions for 11K crawls. It has not hurt us yet. AI citations passed 1,000 a day this week and clicks hit a record. But it is the one thing here that could get our fastest indexing channel throttled, and it is a small change to stop.

**Currency is clean.** Three decisions were due today and none has been announced; the site says so honestly.

---
*Site read from Chrome with `cache: 'reload'` and from a second non-browser client, 2026-11-15 04:04 to 05:20 UTC, against build `71a6b6993`. Bing Webmaster read live: Recommendations, Sitemaps, URL Inspection (2 URLs), IndexNow Insights, AI Performance and Search Performance (data to 11/12). Sitemap re-submitted in Bing (now Success, 1.7K URLs). Google Search Console read live: Page indexing (updated 11/8), Performance (28 days), URL Inspection on 9 URLs; indexing requested for 7. Bing News read for the three Nov 14 goals. Not investment advice.*
