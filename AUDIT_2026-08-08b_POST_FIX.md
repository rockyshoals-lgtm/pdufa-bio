# Post-fix audit — redirects, /drug pages, and the crawl-budget question
**2026-08-08 (evening) · Cowork session · Amendment 033 filing**
*Live HTTP verification from origin. ⚠️ Search Console and Bing Webmaster Tools could not be read this round — see §5.*

---

# 1. ✅ THE REDIRECT FIX SHIPPED — all 13 resolved

Every URL that was redirecting into a 404 now lands on a live, sensible destination:

| Legacy URL | Now resolves to | Status |
|---|---|---|
| `/pdufa-calendar-2026` | `/calendar` | ✅ 200 |
| `/verv-verv101-pdufa` | `/calendar` | ✅ 200 |
| `/vnda-pdufa`, `/vnda-vqw-pdufa` | `/pdufa/VNDA` | ✅ 200 |
| `/meso-ryoncil-pdufa`, `/leaderboard`, `/record` | `/decisions` | ✅ 200 |
| `/q1-2026-oncology-pdufa-dates` | `/condition/cancer` | ✅ 200 |
| `/tools` | `/screener` | ✅ 200 |
| `/intel`, `/trade`, `/heatmap` | `/research` | ✅ 200 |
| `/feed` | `/developers` | ✅ 200 |

Mapping choices are sensible — each legacy slug goes somewhere topically related rather than dumping everything on the homepage, which is what preserves the link equity.

**From `www`, these are single-hop** (`/tools` → `/screener`, 1 hop). From bare `pdufa.bio` they're 2 hops (non-www → www → destination), which is normal and fine.

**Still to do:** click **VALIDATE FIX** on the "Redirect error" issue in GSC. Without it the 19 sit in a *Failed* state until Google re-crawls them on its own schedule; validation puts them in a priority queue. This is the one step that converts the fix into a signal.

---

# 2. ✅ 313 `/drug/` PAGES SHIPPED — and the crawl path is correct

The recommendation was to build drug-name pages because GSC click data proved they convert (`monalizumab` 1/1, `miplyffa` 1/1, `deramiocel pdufa` 1/2 — 50–100% CTR). **313 are live.**

**Crawl path checks out.** I initially suspected these were orphaned like the ticker pages were — they aren't. `/drug` ("Drug Index") is in the **sitewide nav on every page**, and `/drug` links to all 313. So every drug page is **2 clicks from anywhere on the site**. That's the structure the ticker pages lacked for months.

**Slug quality is good:** only **2 of 313** are junk — `aasld-the` and `acr-convergence`, both conference names that leaked through the drug filter. 0.6% error rate; the junk-name guard is clearly working. Delete those two.

---

# 3. 🟡 WHAT'S WEAK ABOUT THE NEW PAGES

| Issue | Detail |
|---|---|
| **Thin** | `/drug/monalizumab` **230 words**, `/drug/deramiocel` **255 words**. That is the same 179–209-word profile the ticker pages had when Google declined to index them. Thin templated pages at scale is the exact pattern that produced the 421 backlog. |
| **Schema is minimal** | Only `WebPage` + `WebSite`. No `Drug` schema (schema.org has a `Drug` type — `activeIngredient`, `manufacturer`, `clinicalPharmacology`), no `FAQPage`, no `BreadcrumbList`. `Drug` schema on a drug page is free entity-binding and nobody in the category is using it. |
| **`dateModified` format regressed** | `/drug/deramiocel` = `2026-08-08T18:37:32+00:00` (correct), `/drug/monalizumab` = `2026-08-08` (date-only). Same inconsistency flagged this morning, now reproduced in the new template. Date-only cannot express "3 hours ago". |
| **Coverage gap on a proven converter** | **`/drug/miplyffa` → 404.** Miplyffa is one of only three drug queries that has ever earned us a click (1 click / 1 impression, 100% CTR). Neither the brand (`miplyffa`) nor the generic (`arimoclomol`) has a page. Also missing: `galinpepimut-s` — the SLS asset, on the site's single highest-profile tracker. |

**The miplyffa gap is the one to fix first.** We built 313 pages and missed one of the three drugs we have documented proof converts.

---

# 4. ⚠️ THE STRATEGIC RISK: 787 URLs INTO AN 11% CRAWL BUDGET

The sitemap has gone **472 → 787 URLs (+67%)**.

As of this morning Google had crawled ~51 of 472 (**11%**), with **421 never fetched at all** (`Last crawled: N/A`). We have now added 315 more URLs to that queue.

This can go one of two ways:
- **Good:** the redirect fix removes the quality drag, crawl budget rises, and the drug pages — which are genuinely useful and well-linked — get picked up.
- **Bad:** 315 additional thin pages dilute an already-rationed budget and *reinforce* the "lots of thin templated URLs" signal that caused the rationing.

**Which one happens depends mostly on §3 (depth) and on whether the redirect validation is submitted.** The pages need to be worth crawling, not just present.

Concretely, I'd:
1. **Not add any more URL families** until the 421 starts falling. Sequencing matters more than volume right now.
2. **Thicken the drug template** toward 400–600 words: mechanism, sponsor, indication, every catalyst for that drug with dates and outcomes, linked decision pages, cohort context, and an FAQ block.
3. Consider `noindex` on drug pages with only one thin catalyst row until they have something to say — 150 strong pages beat 313 weak ones.

Also still open from this morning: `/calendar/2027/*` month pages remain in the sitemap with **282–291 words and zero events** (a 2027 set plus the earlier 2026 ones). `/changelog` was correctly removed. ✅

---

# 5. ⚠️ COULD NOT READ EITHER CONSOLE THIS ROUND

The Claude-in-Chrome extension disconnected mid-audit and did not recover across three retries, so **I could not read Google Search Console or Bing Webmaster Tools.** Everything above is live HTTP verification, which is unaffected.

**Unanswered, and worth checking as soon as Chrome is back:**
1. **Has "Discovered – currently not indexed" moved off 421?** This is the single number that tells us whether the redirect fix worked. Last read: 421, with 51 indexed.
2. **Has the "Redirect error" bucket cleared or been re-validated?** It was *Failed* as of 7/24; the underlying URLs are now fixed, so it should be validated manually.
3. **Bing Webmaster Tools data should now be live** — it was still "processing, up to 48 hours" when set up on the 7th. That unlocks: indexed-page count, URL submission quota, and **AI Performance / Citation Share**, which is the instrument for the AI-citation metric we still have no measurement for.
4. **Are `/sls`, `/tickers`, `/vktx` now in Bing's index?** They were submitted via IndexNow on the 7th and still absent 24h later — the 72h mark is the meaningful check.

---

# 6. WHERE THIS LEAVES US

**Shipped and verified:** redirect→404s fixed with sensible mappings · 313 drug pages with a correct 2-click crawl path · `/changelog` out of the sitemap · `/calendar/2025` archive · junk-slug filter working at 99.4%.

**Do next, in order:**

| # | Action | Why |
|---|---|---|
| 1 | **Click VALIDATE FIX on the GSC Redirect error issue** | Converts a shipped fix into a re-crawl signal; without it the fix sits unnoticed |
| 2 | **Build `/drug/miplyffa` (+ `arimoclomol`) and `/drug/galinpepimut-s`** | We missed a documented 100%-CTR converter and the SLS lead asset |
| 3 | **Delete `aasld-the` and `acr-convergence`** | Conference names masquerading as drugs |
| 4 | **Standardise `dateModified` to full ISO-8601 + offset** in the drug template | Regression from this morning's fix |
| 5 | **Thicken the drug template to 400–600 words + `Drug`/`FAQPage`/`BreadcrumbList` schema** | Thin-at-scale is what caused the 421 in the first place |
| 6 | **Hold on new URL families until 421 starts falling** | Don't add supply to a rationed budget |
| 7 | **Read both consoles** (§5) | Four open questions, all decision-relevant |

**One-line read:** the technical fixes landed and the drug-page bet is well-executed structurally — the crawl path is right, which is the part that was wrong last time — but we've just raised the sitemap 67% on a domain where Google has crawled 11%, so the next move is depth and validation, not more pages.

---
*Facts and historical statistics only. Not investment advice.*
