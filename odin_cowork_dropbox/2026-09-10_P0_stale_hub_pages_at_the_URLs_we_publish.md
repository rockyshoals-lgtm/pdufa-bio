# P0: every hub page serves a June snapshot at the URL our sitemap publishes
**2026-09-10. All measurements forced-revalidation (`cache: 'reload'`), `age: 0`, `x-vercel-cache: MISS`. Live site.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE FINDING

**`https://www.pdufa.bio/calendar` and `https://www.pdufa.bio/calendar/` are two different pages.** The one without the trailing slash is a snapshot from **June 27**. It returns HTTP 200, it carries `robots: index,follow`, and **it is the URL in our sitemap and in every internal link on the site.**

| | `/calendar` (sitemap + all internal links) | `/calendar/` |
|---|---|---|
| `last-modified` | **Sat, 27 Jun 2026** | Thu, 10 Sep 2026 |
| size | **17,271 bytes** | 87,881 bytes |
| `<title>` | "2026 FDA PDUFA Calendar" | "2026 FDA PDUFA Calendar: **97 Dates, Updated Daily**" |
| explainer ("10-month goal") | **0** | 1 |
| "does not publish an official ... calendar" | **0** | 1 |
| month naming sentences | **0** | 4 |
| lede "This page lists 97 FDA decision dates" | **absent** | present |
| `/fda-decision/` links (decided rows) | **0** | 49 |
| navigation | **"Calendar Readouts Devices Decisions Approvals/yr Trial odds ..."** | current nav |
| canonical | `https://pdufa.bio/...` (non-www) | `https://www.pdufa.bio/...` |

The stale page still shows a navigation bar containing **"Trial odds"**, a menu item we removed, and it dates the GSK/SPRO decision to 2026-06-18 where the current data says 06-17.

## It is not just the calendar

I tested fifteen paths. Every hub that existed in June or July has the split:

```
/calendar                     no-slash 27 Jun 2026   17,271 b   |  slash 10 Sep 2026   87,881 b
/decisions                    no-slash 28 Jun 2026   51,753 b   |  slash 10 Sep 2026  145,103 b
/readouts                     no-slash 28 Jun 2026  194,243 b   |  slash 10 Sep 2026  179,442 b
/conferences                  no-slash 10 Jul 2026   11,297 b   |  slash 10 Sep 2026   84,636 b
/research                     no-slash 10 Jul 2026    5,700 b   |  slash 10 Sep 2026   17,339 b
/learn/what-is-a-pdufa-date   no-slash 28 Jun 2026    9,412 b   |  slash 10 Sep 2026   17,353 b
```

And every page created **after** the problem began is clean at both URLs:

```
/crl              10 Sep / 10 Sep      /fda-this-month    10 Sep / 10 Sep
/drug/camizestrant 10 Sep / 10 Sep     /pdufa/TLX         10 Sep / 10 Sep
```

That is the signature of **old flat files left behind in the deployment**. The hubs were once generated as flat files at their no-slash paths; the build later moved to directory output (`/calendar/index.html`); the old files were never deleted. Vercel serves the leftover flat file for the no-slash request and the current directory index for the slash request. Newer pages have no leftover, so they match.

---

# 2. WHAT THIS EXPLAINS

**`/learn/what-is-a-pdufa-date` is the clearest case, and it is one I have been getting wrong for five audits.**

| | no-slash (crawled) | slash (current) |
|---|---|---|
| title | "What Is a PDUFA Date? FDA Decision Dates" | "What Is a PDUFA Date? **FDA Goal Dates Explained, With 2026 Data**" |
| description | generic, no statistic | "...In 2026, **20 of 32 sourced decisions came early**." |
| timing statistic in body | **absent** | present |

I have flagged that page as "zero clicks at position 8 on our own core term" in five consecutive audits and kept prescribing internal links. **The page search engines actually have is a June 28 version that contains none of the work.** The prescription was not wrong; the diagnosis never went deep enough.

**It also explains the three things I could not account for:**

1. **Why the Bing answer box quotes five competitors and not us.** The explainer shipped September 5. Bing has never fetched a URL containing it. My "the box may be an authority filter, re-test Sept 13" hypothesis was wrong; there was nothing to filter.
2. **Why our SERP freshness stamp reads older than novapharmanews.** Our `/calendar` sends `last-modified: Sat, 27 Jun 2026`.
3. **Why Google's indexed count sits at 57 and impressions rise while clicks stay flat.** The indexed hubs are June-vintage and thin. It also explains the split `www` / non-`www` impressions in the Generative AI report: the stale pages carry a non-www canonical, the current ones carry www.

**And a correction I owe.** Most of my hub verifications were fetched with a trailing slash, because that is the form I happened to use in curl. Those readings were accurate about the page and silent about the artifact crawlers fetch. Every "the explainer is live" and "the month sentences are live" in the last week is true of `/calendar/` and false of `/calendar`. The work shipped; it just never reached an audience.

---

# 3. WHAT TO DO, IN ORDER

| # | Action | Acceptance |
|---|---|---|
| **1** | **Delete the leftover flat files from the build output**, so the no-slash path resolves to the same artifact as the slash path. This is the fix; everything else is mitigation. | `/calendar` and `/calendar/` return identical bytes and the same `last-modified`; same for `/decisions`, `/readouts`, `/conferences`, `/research`, `/learn/*` |
| **2** | **Guard it.** For every URL in the sitemap, assert the no-slash and slash forms return the same content hash, or that one 308s to the other. | new test proved 0 → planted 1 → healed 0; runs in CI after the build |
| **3** | **Fix the canonical host.** The stale pages canonicalise to non-www; the sitemap lists 169 of 170 URLs as `https://pdufa.bio/...` while the site 308s non-www to www. Sitemap and canonical should both be www. | every `<loc>` is `https://www.pdufa.bio/...`; every canonical matches its own URL |
| **4** | **Re-submit the affected URLs** to Bing (IndexNow) and Google once 1 to 3 are live. | IndexNow 200 for the hub set; URLs requested in Search Console |
| 5 | Re-test the Bing answer box **one week after** the crawl, not before. The Sept 13 date I set is now meaningless because the content was never fetched. | new baseline date recorded |

Item 1 is worth more than every content item on the open list combined. Two and a half months of work on the hubs has been invisible to search engines, and the fix is deleting stale files.

---

# 4. THE REST OF TODAY'S SWEEP

**Currency, forced revalidation:** API `as_of` 2026-09-09 (today's rebuild ran at 10:03 ET and the pages carry it; the API's own stamp trails by a day and is worth a look). Past-goal day-precision PDUFAs undecided **0**. Past Guided readouts without outcome **0**. Manufactured non-day dates **0**. Blank company names **2** (CNTA, as reported). ERS correctly "In progress" through today.

**TLX decides tomorrow.** The row reads `2026-09-11, Upcoming, TLX101-Px (Pixclara)`, and the page now describes it correctly as a PET imaging agent. Ready.

**`/build-info.json` is its own instance of the same bug.** Six consecutive forced-revalidation fetches returned `last-modified: Sat, 08 Aug 2026` and a body naming **LNTH on 2026-08-13** as the next decision, with no `commit` field, which places it before the September 8 change that added one. Same leftover-artifact signature. Any monitor reading it sees a site that last built a month ago.

**The four December 31 PDUFAs** I flagged yesterday all carry real indications (ABBV tavapadon in early Parkinson's, AZN Ultomiris in IgA nephropathy, BAYRY finerenone in T1D with CKD, NVO CagriSema in obesity), so they are real programmes rather than junk rows. All four are still self-sourced and all four sit on New Year's Eve. **Still unverified against filings**; they remain the top data item after the hub fix.

---

# BOTTOM LINE

**Everything we have shipped to the hub pages since late June has been invisible to search engines, because the URL in our sitemap serves a leftover June snapshot.** `/calendar` sends a 17 KB page from June 27 with no explainer, no month sentences, no decided rows, and a navigation bar advertising "Trial odds". The 88 KB current page exists only at `/calendar/`, which nothing links to. Six of the fifteen paths I tested have the split, and they are exactly the pages that existed before the build changed shape.

**This single fault explains the three channel puzzles I have been circling for two weeks**: the answer box quoting competitors, our freshness stamp reading older than a clone's, and Google impressions rising while clicks and indexed count stand still.

**And it corrects me.** I verified those pages with a trailing slash and reported them live. They were live at a URL no crawler visits. The content work was right; I never checked that it was reachable.

Delete the leftover files, guard the two forms against each other, fix the canonical host, then re-submit. Everything else on the open list can wait behind it.

---
*All figures measured 2026-09-10 with forced revalidation, age 0, MISS. Not investment advice.*
