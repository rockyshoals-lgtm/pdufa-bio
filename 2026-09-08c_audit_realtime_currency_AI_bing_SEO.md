# Audit, 2026-09-08 11:45 Pacific (real-time cadence resumes): currency, AI citations, Bing, SEO
**Live build `2026-09-08T16:09:15Z` commit `fa5d08330`. Consoles read 11:00 PT today (Bing through Sept 6). Every claim below checked live with `Cache-Control: no-cache`.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. CURRENCY

| Gate | Result |
|---|---|
| Live build | 16:09Z today (07:15 dispatch + 09:07 push) |
| API `as_of` | 2026-09-08 (cannot fail today, not credited) |
| Past-goal day-precision PDUFAs undecided | **0** |
| Past Guided readouts without outcome | **0** |
| Past conferences not marked Ended | **1: ERS (Sept 5) still `Scheduled`** |
| Next decision | TLX 2026-09-11, 3 days |

**One new thing I can now say first-hand: I reproduced the CDN stale-body problem the builder documented Sunday.** At 11:24 PT, two hours after the 16:09Z deploy, a cache-busted fetch of `/calendar` returned a body with `dateModified 2026-09-06T15:50:29+00:00` (a Sept 6 body, still in the old UTC stamp format) while the response headers said `last-modified Tue, 08 Sep 2026 16:27:42`. Four fetches at 11:40 PT all returned the correct Sept 8 body (etag `66a18a2b`, md5 matches). So for at least part of two hours after a deploy, some requests get a two-day-old calendar. This has a direct SEO cost, covered in section 3.

---

# 2. WHAT THE CHANNELS SAID AT 11:00 PT (unchanged since the scheduler review; restated as the baseline for this cadence)

| Channel | 3-month total | Leading indicator |
|---|---|---|
| Bing search | **317 clicks, 10.7K impressions, 2.97% CTR** | Sept 3 record 698 impressions; Sept 4 to 6: 446 / 239 / 278 |
| Bing AI citations | **3.7K, 15 avg cited pages** | **grounding queries 19, flat two weeks**; daily citations 348 / 255 / 279 → 178 / 79 / 87 |
| Bing answer box, `pdufa dates 2026` | organic #1 | **not cited**; box cites biomednexus, medswitcher, novapharmanews ×2, assyro |
| Google search | 53 clicks, 3.2K impressions, 1.7% CTR, position 19, 162 queries | clicks flat four reads running |
| **Google Generative AI** (first read) | **58 impressions, 15 pages** | homepage 48 (www 38 + non-www 10) |

---

# 3. WHAT I FOUND TODAY THAT DIRECTLY COSTS CLICKS OR CITATIONS

These are new, verified, and each maps to a number in the table above.

## 3.1 Camizestrant's snippet does not say it was approved (29 Bing impressions, 0 clicks)

The drug we are the top AI source on (82 citations, 32% share), approved Sept 4, published Sept 5, earns 29 Bing web impressions at position 4.62 and **zero clicks**. The reason is the snippet:

> title: `Camizestrant: FDA Decision Dates & Catalyst History | pdufa.bio`
> description: `Camizestrant: FDA catalyst dates and outcomes. For AstraZeneca PLC. Every date and decision links its primary source. Facts only.`

Nothing about the approval, the date, or the brand. The body says "The FDA approved it on Sep 4, 2026… as Etcamah"; the SERP never sees it. **Scale:** 564 drug pages; 244 state an approval in the body; **18 of those still carry the generic description**, camizestrant among them. The other 226 were fixed in the 09-05 batch, so this is a residue, but it sits on the highest-value page in the set.

## 3.2 The explainer we most need to rank carries a stale statistic in its meta description

`/learn/what-is-a-pdufa-date`, the page that should own `pdufa` (874 impressions at 0.46%) and `what is a pdufa date`:

> description: `…In 2026, **15 of 26** sourced decisions came early.`

`/calendar` says **32 decisions, 20 early**. Same statistic, two numbers, and the stale one is in the snippet Bing and Google display. This is the two-surfaces problem the builder fixed on `/calendar` by importing the timing page's own `collect()`; the `/learn` meta was not on that path.

## 3.3 Our freshness stamp is right at the origin and stale at the edge

`novapharmanews` shows "17 hours ago" on the Bing SERP against our "1 day ago", on a day our build was more recent than theirs is likely to be. The origin emits the correct `dateModified` / `og:updated_time` (16:09Z today). But the CDN body I got at 11:24 PT carried Sept 6. If Bingbot fetched in that window it saw a two-day-old stamp, and the SERP shows what the crawler saw. **The post-deploy verifier the builder queued Sunday is now an SEO item, not only a correctness item.** Purging the CDN cache for the top 20 URLs on every deploy is the direct fix.

## 3.4 The answer box wants named drugs in sentences, and we have them in a table

medswitcher.com entered the box cited for: *"CagriSema for chronic weight management… estimated for Q2 2026"*, *"Survodutide, Retatrutide, Pivlicaftor, and Relutrigine"*. Our calendar has more of those names, sourced, in table rows. The Saturday explainer supplied the definitional sentences (10-month, 6-month, 3-month, "FDA does not publish"); the box is now also quoting drug-name sentences we don't have. `/fda-this-month` already writes them for September; the calendar's month headings each carry one count sentence but no drug names.

## 3.5 Google's AI surfaces a URL that 404s

`/odin-track-record` appears in Google's Generative AI report (1 impression) and returns 404. `/odin` correctly 308s to `/why-no-approval-probability`. Same redirect, one line.

## 3.6 Still open from earlier audits, still costing

- `/learn/what-is-a-pdufa-date` internal links from drug and event pages: **fifth audit, not done**. The page has one Google AI impression and zero Bing clicks at position 8.
- `pfizer pfe pdufa dates fda approval decisions 2026 2027`: 82 impressions, position 3.23, **0 clicks**; `/company/pfizer` 404.
- `<caption>` on `/calendar` grids: **0**.
- UNCY case study (12 sources, fully drafted in 09-06f): not built.
- Brand names in `alternateName` for historical approvals (PASATRU, LYTENAVA): unverified since Sept 3.

---

# 4. ORDER (real-time; P0 first; each with the check I will run when David says "done")

| # | Item | Mechanism | Acceptance |
|---|---|---|---|
| **1** | **Fix the 18 approved-drug pages with generic meta** (camizestrant first): description = the approval sentence with brand and date | 29 impressions at 0 clicks on our top AI entity; snippet is the whole problem | `/drug/camizestrant` description contains "approved", "September 4, 2026", "Etcamah"; count of approved pages with the generic string = 0 |
| **2** | **`/learn/what-is-a-pdufa-date` meta and body read the same timing numbers as `/calendar`**, from the same `collect()` | stale stat in the snippet of our core explainer | description contains the calendar's current n and early count; guard: the two pages' numbers are equal |
| **3** | **CDN purge on deploy for the top 20 URLs + the post-deploy verifier** | SERP freshness stamp; correctness | verifier script named with one run's output; a cache-busted fetch within 5 min of deploy returns the new `dateModified` |
| **4** | **ERS → `Ended`**, and whatever let ESC flip but not ERS | currency gate | API row `Ended`; `/conferences` lists it under past |
| **5** | **`/odin-track-record` → 308 `/why-no-approval-probability`** | Google AI surfaces it; it 404s | curl shows 308 with that Location |
| 6 | **One drug-name sentence under each `/calendar` month heading** ("In October the FDA is due to decide on X (TICKER, date), Y…", top 3 to 5 by market cap, sourced) + `<caption>` on each grid | the medswitcher shape the answer box is quoting | each month heading followed by a sentence naming ≥3 drugs with dates; `grep -c '<caption'` = grid count |
| 7 | **Internal links to `/learn/what-is-a-pdufa-date`** on first "PDUFA" in every drug and event page | fifth audit; cheapest authority transfer available | random 20 drug + 10 event pages each contain the href |
| 8 | **`/company/{slug}`** for sponsors with ≥2 events | 82 impressions at 3.23 with 0 clicks | `/company/pfizer` 200, title answers the query |
| 9 | **UNCY case study** per 09-06f | the no-probabilities policy as a worked, sourced example; 5 citation-shaped sentences | acceptance list in 09-06f §5 |
| 10 | Brand `alternateName` backfill check | entity breadth | `/drug/garetosmab` contains "Pasatru"; 20-page sample ≥18 |

Items 1, 2, 4, 5 are each under an hour. Items 1 and 2 are the only ones that change a number in the console within days.

---

# 5. HOW I WILL AUDIT FROM HERE

No scheduler. When David says the builder is done, I run the acceptance checks above against the live build, read the consoles if Chrome is open, and write the next ORDER. The two dated re-tests I owe:

- **Sept 13: Bing `pdufa dates 2026` answer box.** If we are still absent a week after shipping the exact sentences it quotes, the box is an authority filter and weight shifts to Google-authority items (API as link magnet, `Dataset` schema on the studies).
- **Next console read: grounding queries.** 19 for two weeks. Items 1, 8, 9, 10 are the ones that add entities; if the count has not moved a week after they ship, the entity thesis needs revisiting.

---

# BOTTOM LINE

**The site is current on every gate but ERS, and the channels are up on every total and flat on every leading indicator.** Bing clicks 317, AI citations 3.7K, Google impressions 3.2K; grounding queries 19 for a second week, Google clicks 53 for a fourth read, and the Bing answer box still quoting five other sites two days after we shipped the sentences it uses.

**Today's new findings are all snippet-level and all cheap.** The drug we are the top AI source for earns 29 Bing impressions and zero clicks because its description never says it was approved. The explainer we most need to rank tells the SERP "15 of 26" while the calendar says 32. And I reproduced, first-hand, the CDN serving a two-day-old calendar two hours after a deploy, which is why our freshness stamp reads older than a competitor's on a day we built later. None of those is a build problem; each is one file.

**The entity work that moves grounding queries has not shipped since Saturday.** Company pages, the UNCY case study, brand backfill, and the internal links to the explainer (fifth audit) are still the items that add breadth, and breadth is the number that has stopped moving.

---
*Verified live 2026-09-08 11:45 PT. Consoles read 11:00 PT; Bing publishes through Sept 6 and revises recent days. Not investment advice.*
