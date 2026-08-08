# pdufa.bio — Re-Audit #5 (FRESH, cache-busted)
**Date:** 2026-07-10 (fetched 21:32 UTC) · **Method:** live Chrome, cache-busted `no-store` fetches on every claim
Product-strategy use only; not investment advice.

> **Correction up front:** several items my last two audits reported as "still open" were **stale cached reads on my end.** Re-fetched with cache-busting, they are **fixed.** Below is the true current state, with each claim re-verified live this pass.

---

## Corrections — items I wrongly reported open (now confirmed FIXED)

| Item | What I said last time | Fresh, cache-busted truth (2026-07-10) |
|---|---|---|
| **Canonical host** | "`/calendar` self-canonicals to non-www" | ✅ **Fixed.** `/calendar` → `https://www.pdufa.bio/calendar`; `/pdufa-calendar` → www `/calendar`; `/` → www. **All www, consistent.** |
| **Sitemap** | "170 URLs, non-www, missing conferences/adcomm" | ✅ **Regenerated.** **330 URLs**, host **`www.pdufa.bio`**, and **includes `/conferences` and `/adcomm`.** `robots.txt` points to the www sitemap. |
| **Readouts cleanup "cosmetic only"** | "bad rows still in server HTML" | ✅ **Now clean at the data layer.** A no-store raw fetch of `/readouts` contains **none** of the bad pairings (Vaping Cessation / Poliomyelitis / Custirsen / SBI-100-Obesity). Staleness flags ("Awaiting data", "updated Xmo ago") still present. |
| **OG/favicon** | flagged as missing (D4) | ✅ Favicon present; `og:image` present on homepage. |

**My error:** the browser was serving me cached copies of `sitemap.xml` and the page `<head>` on prior passes, so I read old canonical/sitemap values. Cache-busting (`?cb=timestamp` + `cache:'no-store'`) fixed it. Apologies for the stale calls — thanks for catching it.

---

## The one "ODIN" item — clarified (not a live-site defect)
- **Live site is clean.** No "ODIN" or approval-probability text in the `<title>` or `<meta description>` of `/`, `/calendar`, or `/pdufa-calendar` (verified fresh).
- The only place "…& ODIN Scores" still appears is **Google's cached SERP listing** for `/pdufa-calendar`. That's **search-index lag**, not something on the site — it resolves when Google re-crawls (can be nudged via Search Console "Request indexing," but can't be force-flushed instantly).
- **Net:** treat this as "done on the site; waiting on Google," not "open."

---

## Current true state — verified live this pass

### ✅ Confirmed working
- **SEO hygiene:** canonical www-consistent · sitemap 330 URLs/www/with new sections · robots→www sitemap · readouts clean in SSR · no ODIN in live meta.
- **Type system:** headings **Space Grotesk**, data **IBM Plex Mono** (tabular numerics).
- **Data-viz:** **22 run-up sparklines** — one on every "Next FDA Decisions" card and every "Recently Decided" row.
- **Search:** ⌘K global search live.
- **API:** `/api/v1/pdufa` → 200. **Ranking:** still page 1 for "PDUFA calendar 2026 …".
- **Coverage:** PDUFA + Readouts + Conferences + AdComm all live and in the sitemap.

### ❌ Genuinely still open (re-verified fresh — these are NOT stale)
| Item | Fresh evidence | Priority |
|---|---|---|
| **Nav grouping + mobile menu** | Header still **11 flat links**, **no dropdown**, **no hamburger/mobile-nav element in the DOM**. (Mobile viewport can't be forced in this tool — needs real-device confirmation, but no mobile-nav component exists at desktop render.) | **High** |
| **Tap targets** | **31 of 61** interactive elements < 40px tall (mobile-ergonomics; desktop reading, so caveated). | **Medium** |
| **Header brand mark** | Logo is still a **plain text wordmark** — no inline icon/mark (favicon exists, but the header has no logomark). | **Low–Med** |
| **Calendar heatmap (D7)** | **0 heatmap cells** — not shipped. | **Med (signature)** |
| **Cohort mini-distribution (D8)** | `±X% cohort` still a flat number, no distribution viz. | **Med** |
| **CWV/font hardening (D10)** | Not verified — confirm self-hosted fonts use `font-display:swap` + preload/subset so Space Grotesk/IBM Plex don't cost LCP/CLS. | **Med** |

---

## Revised standing
The builder has now closed **all three SEO-hygiene items** (I'd been under-crediting them due to cache), cleaned the readouts at the data layer, and shipped the core design signature (type system + sparkline tape + search). **On the live site, the "cleanest, most complete, most accurate, technically-sound" claim is essentially earned** — PDUFA/readouts/conferences/adcomm all live, schema + sitemap + canonical all correct, and the UI now out-crafts the field.

**What actually remains is a short, mostly-mobile list:** (1) group the nav + ship a hamburger/drawer, (2) hit 44px tap targets + real-device mobile QA, (3) add a header logomark, (4) the two remaining signature visualizations (calendar heatmap, cohort distribution), and (5) a CWV font-loading check. None are blockers; items 1–2 are the highest-value because mobile is the last rough surface.

---
## Sources (all cache-busted, live 2026-07-10 21:32 UTC)
pdufa.bio `/`, `/calendar`, `/pdufa-calendar`, `/readouts`, `/sitemap.xml`, `/robots.txt`, `/api/v1/pdufa` (fetched with `?cb=<ts>` + `cache:'no-store'`) — https://www.pdufa.bio/ · SERP: Google "PDUFA calendar 2026 upcoming FDA decision dates" (note: SERP title is Google-cached, not live).
