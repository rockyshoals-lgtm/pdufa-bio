# SEO / Bing / AI-citation audit, 2026-10-11, with ranked actions
**Measured ~12:45 to 14:10 Pacific = 15:45 to 17:10 Eastern (Sunday).** *RULE 1.*
*Build and search mechanics only. Not investment advice.*

**Inputs.** Bing SERPs read live in the in-app browser (signed out, US). The rendered tree `pdufa_site_src/` as of `e62560970` (1,433 indexable pages, 252 noindex by design). The sitemap (1,429 URLs), `llms.txt`, `robots.txt`, the CI ping step. Bing Webmaster Tools data was NOT available: not signed in, and `BING_WEBMASTER_API_KEY` exists only as a CI secret, not locally. Everything below that needs query or crawl stats is therefore inferred from SERPs and the rendered tree, and action 7 fixes that gap.

## What Bing shows today (the part that matters for citations)

| Query | What a user sees | Our position | Problem |
|---|---|---|---|
| fda approval decision biotech | AI answer box listing Winrevair (Sept 21), Camzyos Sept 30 "upcoming", Atebrioz "pending", Tecentriq Oct 9 "next" | cited, but from a stale crawl | Camzyos and Tecentriq are decided on the site; the answer box is quoting pages Bing crawled before 10-01 |
| fda approval decisions this week | Same stale answer box | `/fda-approval-decisions-this-week` (built 10-10) not in results | New page not yet crawled; sitemap lastmod says 2026-10-10 |
| pdufa calendar | fdatracker #1, us #2 organic, snippet "1 day ago" | #2 | Snippet freshness is good; title tag could carry the month |
| enspryng pdufa date | roche.com answer box; us #1 organic ahead of biopharmsignal | #1 | Bing still shows the OLD description ("RHHBY's FDA PDUFA target...") although the live page now reads "Roche's Enspryng supplemental BLA... goal date..." : not recrawled since the 10-10 rewrite |

Reading: the site ranks; the index is 1 to 10 days behind the site on the pages that change. For a decisions site that lag is the whole problem, because the AI answer box quotes whatever the last crawl held.

## On-site findings (rendered tree)

1. **Descriptions that start "TK's FDA PDUFA target is..."**: 68 indexable `/pdufa/` pages still carry the old template (7 of them "TK's FDA PDUFA date is not sourced for..."; e.g. `/pdufa/ABBV-rinvoq`, `/pdufa/AZN-gefurulimab`, `/pdufa/LLY`, `/pdufa/MRK-trodelvy`, `/pdufa/NVS`). The 10-10 rewrite fixed the pages with an event-page sentence in `_event_trial_facts.json`; the rest fall through to `build_pdufa_event_pages.py` line 100. A description that says "not sourced" is a description that asks not to be cited. (Earlier count of 111 included noindex twins; 68 is the indexable figure.)
2. **Duplicate title**: resolved in the 10-10 push. "COGT PDUFA date: Bezuclastinib, Dec 30, 2026" is now on one page (`/pdufa/COGT-bezuclastinib-summit`); `/pdufa/COGT-bezuclastinib` reads Nov 30 (PEAK). Verified on the tree, nothing to do.
3. **Canonical not self**: 1 page. Listed in the on-site script output; builder to resolve (it is a twin that should either be noindex or self-canonical).
4. **Schema coverage** (indexable pages): BreadcrumbList 1,427, FAQPage 1,365, Drug 549, Event 109, Dataset 6. The weekly page carries FAQPage + BreadcrumbList but no `ItemList`/`Event` for the decisions it lists and no `dateModified` visible to Bing other than `article:modified_time`.
5. **`modified_time`**: 1,299 pages stamped 2026-10, 114 in 09, 17 in 08, 3 none. The same timestamp (2026-10-10T13:51:06-04:00) is on the home page, the calendar and the weekly page: it is the build time, not the content-change time. Bing reads this; a site-wide identical stamp every day is a signal it learns to ignore.
6. **Internal linking**: 48 orphan indexable pages (no inbound internal link), among them `/calendar/2025`, `/clinical-trial-success-rates`, `/coverage`, `/pdufa/ABBV`, `/pdufa/AZN-camizestrant`; 628 pages with exactly one inbound link. Page mix: drug 550, fda-decision 360, ticker 238, pdufa 134.
7. **Page weight**: median 16 KB (good), median inline CSS 2.9 KB; outliers `/patent-cliff/exclusivity` 347 KB and `/readouts` 161 KB.
8. **Sitemap**: 1,429 URLs, one file; 42 daily / 402 weekly / 985 monthly. `lastmod` on the weekly page is 2026-10-10. The 24 `sitemap.xml.bak_*` files sit inside the deployed tree (harmless to crawlers, untidy).
9. **llms.txt**: 82 lines, 4.9 KB, written for AI assistants, states that the API needs no key. It does not name the weekly page, the today page, or the withdrawn status, and carries no "last updated" line.
10. **Push channel**: `ping_search_engines.py` runs IndexNow + Bing SubmitUrlBatch + Search Console in CI after each rebuild (bing.com/ping is 410). What it submits is not logged in a readable place; whether the weekly page was in the 10-10 batch cannot be confirmed from here.

## Ranked actions

| # | Action | Why first | Acceptance |
|---|---|---|---|
| 1 | **Push changed pages, not the sitemap, through IndexNow every build**: the list of pages whose rendered HTML hash changed since the last commit (decision pages that flipped to Decided/Withdrawn, the weekly page, the today page, the home page, the calendar). Log the submitted URLs and the HTTP response into `_DATA/indexnow_log.jsonl`. | The answer box is quoting a stale crawl; this is the only lever that shortens the lag | Log shows `/fda-approval-decisions-this-week` and `/fda-decision/RHHBY-2026-10-08` submitted with 200/202; Bing cache date on those pages moves within 72 h |
| 2 | **Rewrite the 68 remaining "TK's FDA PDUFA target" descriptions** in `build_pdufa_event_pages.py` to the fact-first form already used by the enriched pages: "{Sponsor}'s {drug} {application type} for {indication} has an FDA goal date of {date}, per {source}." For the 7 unsourced rows: "{Sponsor}'s {drug} ({indication}): FDA decision date not yet sourced; sponsor, indication and filing status with links." Never "not sourced" as the opening clause. | A description is what the answer box quotes; "ABBV's FDA PDUFA date is not sourced" is anti-citation copy | grep of rendered `/pdufa/*/index.html` for `^[A-Z]{1,6}&#x27;s FDA PDUFA` = 0; guard `test_description_fact_first` 0 → planted 1 → 0 |
| 3 | **Make `article:modified_time` and `dateModified` the content-change time**, not the build time: hash the main content block, store last-change per page in `_DATA/page_mtimes.json`, stamp only when the hash changes. | 1,299 pages stamped the same minute is a freshness signal Bing discounts; the pages that DID change (RHHBY, MRK, NVS) deserve a stamp that stands out | Home page and an unchanged drug page carry different stamps after a build with no content change; guard |
| 4 | **Weekly page schema**: add an `ItemList` of the week's decisions (each item an `Event` with `startDate` = FDA action date and `url` = the decision page), keep FAQPage. Title: keep. Add the page to `llms.txt` and the home page nav strip (nav itself is frozen; the "this week" strip is content). | It is the page built to be the answer for "fda approval decisions this week"; today it has no machine-readable list | `"@type":"ItemList"` present; Event count = decided rows in the week; guard |
| 5 | **Link the 48 orphans and lift the 628 single-link pages**: a "Related" block on every `/pdufa/` and `/fda-decision/` page (same ticker, same indication, same month) built by `enrich_event_pages.py` SIB, and a year archive strip on `/calendar` linking `/calendar/2025`. | Orphans are crawled late and rarely; single-link pages are one build away from orphan | Orphan count 0; pages with 1 inbound < 200; guard on the link graph |
| 6 | **Trim `/patent-cliff/exclusivity` (347 KB)**: move the table rows past the first 100 into a JSON the page fetches, or paginate by year. `/readouts` (161 KB) the same once over 200 KB. | Bing's renderer budget; the page is also the one that shipped unstyled on 10-04 | Page < 120 KB; test_header_styled still green |
| 7 | **Store `BING_WEBMASTER_API_KEY` in local `.env`** (David) so `bing_rank_report.py` can pull `GetQueryStats` / `GetPageStats` / `GetCrawlStats` daily into `_DATA/bing_stats/`, and the builder reports crawl-date lag per changed page. | Every finding above is inferred; the next audit should be measured | A daily file in `_DATA/bing_stats/` with queries, clicks, impressions, crawl errors |
| 8 | **`llms.txt`**: add a "Last updated: {date}" line, the weekly and today pages, the `Withdrawn` status definition, and a one-line pointer to `/api/v1/` with the row fields. | AI crawlers read this first; it is 10 days behind the site's own vocabulary | Rendered llms.txt names all three statuses and both pages |
| 9 | Housekeeping: delete the 24 `sitemap.xml.bak_*` files and the inert `indexnow_submit.py` + stray key file `6ef4cc566664898aa2939aaee0d174c1.txt` from the deployed tree; resolve the 1 canonical-not-self page. | Noise in the crawl and in the repo | None of these paths in the deployed tree |
| 10 | Title tag for `/calendar`: "PDUFA calendar: {Month YYYY} FDA decision dates | pdufa.bio", regenerated monthly. | fdatracker holds #1 on "pdufa calendar" with a dated title; ours is undated | Title carries the current month; guard |

Not recommended: anything that changes the frozen nav before 2027-01-01; any description that adds odds or predictions; adding aggregators as sources to earn links.

**Carried, still David's:** `goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP secrets; Google Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; Bing Webmaster key in `.env` (action 7).
