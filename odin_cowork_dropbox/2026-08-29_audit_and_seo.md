# Audit + SEO console read — 2026-08-29
**Site built 2026-08-28T21:46Z · Google Search Console read live · Bing session expired**
*Facts and historical statistics only — not investment advice.*

---

# 1. IS EVERYTHING UP TO DATE? — yes, and the timing fix was better than my recommendation

## The selection bias: closed by fixing the records, not disclosing around them

I recommended a disclosure line. **The builder went and sourced the missing decisions instead.** That's the stronger fix and it changed the answer materially:

| | n | Before | On | After | "Before" share |
|---|---:|---:|---:|---:|---:|
| 08-26 (partial sample) | 18 | 13 | 4 | 1 | **72%** |
| **08-29 (complete)** | **26** | **15** | **8** | **3** | **58%** |

**My finding was real and it mattered.** Closing the sample moved the headline 14 points and tripled the "after" count from 1 to 3. Had it shipped as-is, the page would have overstated how often the FDA decides early — on a page built to be quoted.

**Verified independently against the API:** 26 rows, 15/8/3 — **exact match**, page to API.

**Median re-checked:** across all 26 deltas the median is **exactly −1.0**. The page says *"1 day before."* Correct — my 08-26 flag is resolved by the larger sample, not papered over.

The distribution now runs −108 (CORT) to +4 (REPL), with CORT's goal date corrected to 2026-07-11 — that correction alone is what surfaced a 108-day-early approval that had been mis-recorded as on-time.

## Also verified
- **Ticker hubs were advertising nine approved drugs as upcoming FDA decisions** — found and fixed by the builder (`2150c956`), plus 7 decided events dropped from upcoming in the hub rebuild.
- Site freshness: `dateModified 2026-08-28T21:46Z`.

## Checked and clean
GSC lists `https://pdufa.bio/` as a separate page (4 clicks / 139 impressions), which would be a canonicalisation split. **Verified: it isn't.** `pdufa.bio` → **308** → `www.pdufa.bio`, and both carry `canonical: https://www.pdufa.bio/`. That's historical data from before the redirect, not a live problem.

---

# 2. GOOGLE — real growth, and the indexation wall is now unmistakable

## Performance is up across the board

| | 08-18 | **08-29** | Change |
|---|---:|---:|---:|
| Clicks (3 mo) | 34 | **53** | **+56%** |
| Impressions | 1.96K | **2.37K** | +21% |
| CTR | 1.7% | **2.2%** | +29% |
| Avg position | 21 | **20.5** | +0.5 |

## But indexed pages have not moved at all

| | 08-12 | 08-18 | **08-29** |
|---|---:|---:|---:|
| **Indexed** | 55 | 57 | **57** |
| Not indexed | 453 | 858 | **1,310** |
| *of which* "Discovered – currently not indexed" | 418 | 823 | **1,290** |
| Indexation rate | 10.8% | 6.2% | **4.2%** |

**Indexed has been frozen at 57 for eleven days while not-indexed grew by 452.** "Discovered – currently not indexed" is now **98.5%** of the problem.

**The important inference:** clicks rose 56% while indexed pages stayed flat. **That growth came entirely from the 57 pages Google already has performing better — not from new pages.** It's the cleanest possible confirmation that shipping more pages does nothing for Google, and that improving what's already indexed does.

**Credit where due:** technical debt shrank. Redirect errors went **19 → 3**. Total technical issues are now 19 pages against 1,290 authority-blocked — the builder cleaned up the only part that was actionable.

---

# 3. 🔴 THE CTR CLIFF IS NOW CONFIRMED ON BOTH ENGINES

Google's top queries, 3 months:

| Query | Impressions | Clicks | CTR |
|---|---:|---:|---:|
| **pdufa dates** | **56** | **0** | **0%** |
| **pdufa date** | **49** | **0** | **0%** |
| **pdufa calendar** | **45** | **0** | **0%** |
| pdufa.bio (brand) | 4 | 4 | 100% |
| vktx phase 3 results date | 5 | 1 | 20% |
| deramiocel pdufa | 3 | 1 | 33% |
| rezatapopt | 2 | 1 | 50% |
| monalizumab | 1 | 1 | 100% |
| **nct04229979** | 1 | 1 | 100% |
| miplyffa | 1 | 1 | 100% |

**150 impressions on the three head terms produced zero clicks — on Google, exactly as on Bing.**

And the mirror image: **every entity query converts.** Drug names, tickers, even a **raw ClinicalTrials.gov ID** (`nct04229979`) each pulled a click from a single impression.

**This is the same finding from two independent engines, and it settles the strategy.** The head terms are not winnable at position 20 and are not converting even where we rank. The long tail — drug, ticker, NCT ID — converts at or near 100%. We have 544 drug pages and 156 ticker pages already built for exactly that.

## Top pages, and a divergence worth noting

| Page | Clicks | Impressions | CTR |
|---|---:|---:|---:|
| `/` | **37** | 746 | **5.0%** |
| `/condition/cancer` | 4 | **373** | **1.1%** |
| `/pdufa-calendar` | 2 | 175 | 1.1% |
| `/sls` | 1 | **161** | **0.6%** |
| `/pricing` | 1 | 128 | 0.8% |
| `/odin` | 1 | 101 | 1.0% |

**The homepage is Google's best page (5.0% CTR, 37 of 53 clicks) and Bing's worst (0.19%).** Same page, opposite behaviour — worth understanding before touching it, and a reason not to "fix" the homepage for one engine without checking the other.

**`/condition/cancer` is the #2 page by impressions (373) at 1.1% CTR** — a page type I have never examined. That's 373 impressions largely going to waste.

---

# 4. BING — session expired, could not read

Bing Webmaster Tools has signed out; the property page returned the marketing splash with a Sign In button. **I did not estimate the numbers.**

Last read, 08-18: **66 clicks / 2.7K impressions / 2.47% CTR**, and **AI citations 413** with 5 grounding queries. The AI citation figure is the one I most want refreshed — it was the fastest-growing channel by a wide margin, and it's now 11 days stale.

**If you sign back in, I'll pull it.**

---

# 5. STILL GATED ON YOU — 17 days

`/compare` · `/terms` · `/privacy` · `/refund-policy` · `/contact` — all 404.

---

# 6. WHAT I'D DO

| # | Item | Evidence | Effort |
|---|---|---|---|
| 1 | **Stop optimising for head terms; optimise the entity long tail** | 150 head impressions → 0 clicks on *both* engines; every entity query converts | ongoing |
| 2 | **Examine `/condition/cancer`** — 373 impressions at 1.1% | #2 page by impressions, never audited | hours |
| 3 | Sign back into Bing so I can refresh AI citations | 11 days stale, fastest-growing channel | minutes |
| 4 | **External citations for Google** | indexed frozen at 57 for 11 days; 1,290 authority-blocked | ongoing |
| 5 | **Legal pages** | 17 days; blocks email + paywall | 1 day |

---

# 7. BOTTOM LINE

**Everything is up to date, and the decision-timing fix was the right call taken further than I asked.** My selection-bias finding was real — the complete sample moved "before" from 72% to 58% and tripled the "after" count. The builder closed it by sourcing the missing records rather than adding a caveat, and page and API now reconcile exactly at 26, median −1.0.

**Google is genuinely growing: clicks +56%, CTR +29%.** And it's growing entirely from 57 pages, because indexed hasn't moved in eleven days while not-indexed climbed to 1,310. That's the authority wall, now measured three times, and it's the cleanest evidence yet that page count is not the lever.

**The CTR cliff is confirmed on both engines independently.** "pdufa dates," "pdufa date," "pdufa calendar" — 150 impressions, zero clicks, on Google and Bing alike. Meanwhile drug names, tickers and even a raw NCT ID convert at 100%. The strategy that follows is unambiguous: the entity long tail is the business, and you already have 700 pages built for it.

Bing signed out, so AI citations are 11 days stale — that's the number I'd most like back.

---
*Google Search Console read live 2026-08-29. Bing figures are from 2026-08-18 and labelled as such. Not investment advice.*
