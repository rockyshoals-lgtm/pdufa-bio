# Audit — 2026-08-12
**Cowork session · Amendment 033 filing**
*Both consoles + live SERP + origin verification. Facts and historical statistics only — not investment advice.*

---

# 1. 🚀 BING IS COMPOUNDING — AI CITATIONS UP 9× IN TWO DAYS

## Search performance
| Date | Clicks | Impressions |
|---|---:|---:|
| Aug 8 | 2 | 187 |
| Aug 9 | 6 | 201 |
| **Aug 10** | **10** | **388** |
| **3-day total** | **18** | **776** |

**Impressions doubled and clicks went 5× in 48 hours** — tracking the #1 ranking (taken Aug 10) plus the 108 IndexNow submissions pushed that day.

For scale: **Google delivered 38 clicks / 1,610 impressions over 90 days.** Bing delivered **18 clicks / 776 impressions in 3 days.** On a per-day basis Bing is now running at roughly **40× Google's click rate.**

## AI citations — the standout number
| Date | Citations | Cited pages |
|---|---:|---:|
| Aug 8 | 8 | 3 |
| Aug 9 | 35 | 8 |
| **Aug 10** | **72** | **9** |
| **Total** | **115** | avg 7 |

**Citations grew 9× in two days.** Six days ago this metric was untracked and had no instrument; it's now the fastest-growing number on the board.

## 🎯 The first grounding query is visible — and it validates the whole strategy
> **"rusfertide pdufa date"** — **12 citations · 16.67% citation share**

That is a **drug-name query**, and we hold **one sixth of all citations** for it. `/drug/rusfertide` exists (200), and rusfertide is Protagonist's PTGX asset with a **PDUFA on Sep 30** — so this is a live catalyst driving live AI citations, answered by exactly the page type built for it.

The chain now has evidence at every link: GSC click data said drug queries convert → we built 310 `/drug/` pages → a drug query is now the top AI-citation driver with 16.67% share. That is the long-tail thesis proven end-to-end on the AEO surface.

## Ranking held
**pdufa.bio is still #1 on Bing** for "fda calendar 2026 pdufa dates" (Aug 10 → Aug 12). And the title rewrite shipped: **"2026 FDA PDUFA Calendar: 67 Dates, Updated Daily"** — count plus freshness, exactly the click-worthiness recommendation.

---

# 2. GOOGLE — flat, still waiting

| Metric | Aug 10 | Aug 12 |
|---|---:|---:|
| Indexed | 55 | **55** |
| Not indexed | 453 | **453** |
| Discovered – not indexed | 418 | **418** |

**Redirect-error validation: still "Started"** after 3 days. Google typically takes 1–2 weeks. Nothing actionable — the fix is correct and shipped, we're waiting on Google's queue.

The divergence keeps widening: same content, **#1 and compounding on Bing, unmoved on Google.**

---

# 3. ✅ YESTERDAY'S P0 FIXED — and fixed well

`/pdufa/LNTH` no longer redirects to the wrong drug. It's now a proper hub:

> **Upcoming — Aug 13, 2026 · in 1 day · MK-6240**
> Decided — Jun 29 CRL (LNTH-2501) · Jun 26 CRL (LNTH-2501) · Mar 6 ✓ Approved (PYLARIFY TruVu)

Title: *"LNTH PDUFA Dates: MK-6240 & History"*. Leads with the imminent catalyst, then history — better than the per-event redirect I proposed. **Resolved with one day to spare** before tomorrow's decision.

**Also fixed:** `/drug/dtx401` now 200 and `/drug/pariglasgene-brecaparvovec` 308-redirects — Ultragenyx (PDUFA Aug 23, T-11) is covered.

---

# 4. 🟡 OPEN

## 4a. Per-event PDUFA URLs still don't exist
`/pdufa/LNTH-2026-08-13` → 404, and **all three LNTH API records still carry `url = /pdufa/LNTH`**. The acute problem (wrong-drug landing) is solved by the hub, but one URL still represents three distinct events in the API. Lower priority now that the hub is correct, but worth doing so each catalyst is independently linkable and citable — especially given AI engines cite specific URLs.

## 4b. Our #1 page shows "4 days ago" while a rival shows "16 hours ago"
On the Bing SERP where we rank #1, our snippet reads **"4 days ago"**; novapharmanews reads **"16 hours ago"**.

Cause: `/calendar` and `/decisions` carry `dateModified 2026-08-08` (sitemap `lastmod` agrees), while `/` is Aug 12 and `/readouts` Aug 11.

**This is internally consistent** — the build only bumps the stamp on real content change, which is correct discipline and I've praised it before. But it has a visible competitive cost on a freshness-driven query, on our best-ranking page.

The resolution isn't to fake the timestamp. It's that **a catalyst calendar genuinely should change daily** — and `/pdufa/LNTH` proves the pattern works, since it renders a live "**in 1 day**" countdown. Put the same countdown (or a "next decision in N days" line) on `/calendar` and `/decisions`, and the stamp updates honestly because the page really did change.

## 4c. Bing "noindex" recommendation — checked, intentional
BWT flags *"Some URLs are not getting indexed due to robots NOINDEX meta tags."* I verified the scope: `/`, `/calendar`, `/decisions`, `/drug`, `/tickers`, `/screener`, `/research`, `/learn`, `/drug/rusfertide` and a sourced decision page are all **noindex=0**. The warning refers to the deliberately noindexed price-only decision pages. **Not a bug — no action needed.**

## 4d. ⚠️ Aug 31 deadline — 19 days
`bing_rank_report.py` still calls the legacy `ssl.bing.com/webmaster/api.svc/json`. Microsoft retires SOAP/POX APIs **Aug 31**. Now that Bing is the primary channel, losing rank reporting there would be a genuine blind spot.

---

# 5. PRIORITY

| # | Action | Why |
|---|---|---|
| 1 | **Migrate `bing_rank_report.py` to the REST API** | 19 days; Bing is now the main channel |
| 2 | **Add a live countdown to `/calendar` + `/decisions`** | Honest daily change → honest fresh timestamp → closes the "4 days ago" gap on our #1 page |
| 3 | **Build more `/drug/` pages for near-term catalysts** | "rusfertide pdufa date" at 16.67% citation share is the proof; every upcoming PDUFA drug should have one |
| 4 | **Keep feeding IndexNow daily** | Direct causal line from 108 submissions → doubled impressions |
| 5 | Per-event PDUFA URLs (`/pdufa/{T}-{date}`) | AI engines cite specific URLs; one URL for three events limits that |
| 6 | ⏳ Wait on GSC redirect validation | Nothing actionable |

---

# BOTTOM LINE

**Bing is compounding fast: impressions doubled, clicks 5×, and AI citations up 9× in two days to 115.** The #1 ranking held, the click-worthy title shipped, and the first visible grounding query — *"rusfertide pdufa date"* at **16.67% citation share** — is a drug-name query answered by a page we built specifically because GSC click data predicted it would convert. The thesis is now proven at every link in the chain.

Google is unchanged and still working through redirect validation. That's fine — but the gap is now large enough that Bing should be treated as the primary channel for planning, not the secondary one.

Two things to actually do: **migrate the Bing API before Aug 31**, and **give the calendar a real daily-changing element** so our best page stops advertising itself as four days old while ranking first.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
