# Console status — Google + Bing, read live
**2026-08-09 · Cowork session · Amendment 033 filing**
*Both consoles read directly. Not investment advice.*

---

# 1. GOOGLE SEARCH CONSOLE — moving, slowly, in the right direction

| Metric | 08-07 | **now** | Δ |
|---|---:|---:|---|
| **Indexed** | 51 | **55** | **+4** |
| Not indexed | 456 | **453** | −3 |
| **Discovered – currently not indexed** | 421 | **418** | **−3** |
| Crawled – not indexed | 3 | 3 | — |

**The important change isn't the counts — it's this:**

| Issue | Validation status |
|---|---|
| **Redirect error (19)** | **Failed → ✅ STARTED** |
| Not found 404 (5) | Started |
| Duplicate canonical (1) | Started |
| Page with redirect (6) | Failed |
| Crawled – not indexed (3) | Failed |

**Re-validation on the redirect fix is running.** That was the #1 open action from yesterday, and it's now in Google's queue rather than sitting in a two-week-old *Failed* state. Those 19 URLs all resolve to 200 now, so this should clear — that's the thing to re-check in ~1 week.

Movement is real but small (+4 indexed). Expected: GSC lags several days, and the redirect fix landed hours ago.

---

# 2. BING WEBMASTER TOOLS — now live, and the numbers reframe the picture

## 2.1 🔥 Bing delivers ~10× Google's impressions

| | Google | Bing |
|---|---:|---:|
| Impressions | **1,610 / 90 days** (≈18/day) | **187 in one day** (Aug 8) |
| Clicks | 38 / 90 days | 2 in one day |

Bing is producing roughly **ten times Google's daily impression volume**. We rank #3 there and off page 1 on Google, so this is consistent — but seeing it quantified changes where effort should go. **We have been optimising for, and measuring by, our weaker channel.**

## 2.2 🎯 AI citations — we finally have a number

**AI Performance (Copilot + Bing AI answers + partners), Aug 8:**
- **Total citations: 8**
- **Avg. cited pages: 3**

This was listed as *"AI citations — untracked, instrument this now"* in the 08-07 strategy with no instrument. **Now it's instrumented and non-zero.** Query-level breakdown still shows "no data available" (sample processing), but the baseline exists: **8 citations / 3 pages**. That is the AEO metric to grow.

## 2.3 URL submission — a large, underused lever

- **URLs submitted today: 12**
- **Quota left today: 88**

Bing allows **~100 URL submissions per day** against Google's ~10. On the engine where we already rank #3, we are using **12%** of a lever that is 10× larger than Google's. Nine URLs were submitted manually yesterday (18:06–18:13), including the new `/learn/why-cross-trial-comparisons-mislead`, `/drug`, `/calendar/2025`, `/tickers`, `/vktx`, `/sls`.

**Recommendation:** wire the daily job to push changed URLs through Bing's **Submission API** as well as IndexNow, and actually use the 100/day. This is the cheapest indexing capacity available to us anywhere.

## 2.4 Two gaps in BWT
- **IndexNow panel shows the "Get Started" marketing page** — no submissions attributed, despite `api.indexnow.org` returning HTTP 200 for 178 URLs. Either attribution lags, or the key/host isn't binding to this property. Worth a look, since IndexNow is the automated channel.
- **Site Explorer: "No data available"** — indexed-URL count still populating. Re-check in a day.

## 2.5 ⚠️ Dated breakage: legacy Bing API retires **Aug 31, 2026**
BWT banner: *"Legacy SOAP and POX APIs will be retired on August 31, 2026. Migrate to our REST APIs."*

**`bing_rank_report.py` calls `https://ssl.bing.com/webmaster/api.svc/json` — that is the legacy endpoint.** It will stop working on Aug 31. Three weeks' notice; migrate it to the REST API.

---

# 3. ✅ SHIPPED SINCE YESTERDAY

- **`/learn/why-cross-trial-comparisons-mislead`** is live — **848 words**, titled *"Why you can't compare two drugs' trial results, and what you can compare instead."* This was the "killer module" from the comparative-efficacy strategy, and it shipped as a standalone explainer. Exactly the right asset: on-brand, genuinely educational, and the most AI-citable thing on the site.
- **`/calendar/2025`** historical archive live.
- All 13 redirect→404s resolving (verified yesterday).
- 313 `/drug/` pages with correct 2-click crawl path.

**Not yet built:** `/compare/` pages (404) — the per-drug comparison tables. The explainer landed first, which is the right order: publish the methodology, then the comparisons that honour it.

---

# 4. WHAT TO DO NEXT

| # | Action | Why |
|---|---|---|
| 1 | **Use Bing's 100/day submission quota** — wire the Submission API into the daily job | 10× Google's lever, on the engine where we rank #3, currently 12% used |
| 2 | **Migrate `bing_rank_report.py` off the legacy API** | Hard deadline **Aug 31, 2026** |
| 3 | **Add `Article`/`FAQPage` schema to the cross-trial explainer** | It's our most citable page and emits only `WebPage`+`WebSite` |
| 4 | **Investigate why BWT shows no IndexNow attribution** | The automated channel may not be crediting to this property |
| 5 | **Re-check GSC redirect validation in ~1 week** | Confirms whether clearing the quality signal moves the 418 |
| 6 | Still open from yesterday: `/drug/miplyffa` + `/drug/galinpepimut-s` 404s; 2 conference-name slugs; `dateModified` format; thin 230–255w drug template | Unchanged |

---

# 5. BOTTOM LINE

Google is inching (51→55 indexed, 421→418 discovered) and the redirect re-validation is finally **running** rather than failed — that's the meaningful change, and its effect shows up next week.

The bigger news is Bing. Now that the data has populated it shows **187 impressions in a single day against Google's ~18**, **8 AI citations** giving us our first real AEO baseline, and **88 unused URL submissions per day** on the engine where we're already top-3. We have been measuring ourselves almost entirely in the console of our weaker channel.

One dated risk to book: the Bing rank reporter runs on an API Microsoft retires **August 31**.

---
*Facts and historical statistics only. Not investment advice.*
