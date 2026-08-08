# pdufa.bio — Re-Audit #5 Response / Close-out
**Date:** 2026-07-10 · **Owner:** build team · **Against:** `pdufa_bio_reaudit5_FRESH_2026-07-10.md`

Thanks for the cache-busted re-check and the correction on the SEO items — appreciated. Re-Audit #5's remaining list was **root-caused and fixed**. The key insight: the header **logomark and hamburger were being injected client-side by `cmdk.js`**, so they were absent from the server HTML your probes read — and your 21:32 UTC pass also caught a pre-fix copy of that script. We've now moved them into **server-rendered HTML** so they're visible to crawlers, probes, and no-JS clients alike.

> Legend: ✅ done & live (SSR-verified, cache-busted) · ⏳ waiting on Google

## The 6 items from Re-Audit #5's "genuinely still open" table

| # | Item (Re-Audit #5) | Status | Fix + live evidence (cache-busted, server HTML) |
|---|---|---|---|
| 1 | **Nav grouping + mobile menu** | ✅ done | (a) **Mobile menu:** server-rendered `<button class="pd-burger">` with inline `onclick` + a `#navpolish` `<style>` block (drawer, ≤720px) baked into 731 pages — works even with JS off; no longer JS-injected. (b) **Grouping:** detail nav (596 pages) collapsed to **Calendar · Conferences · AdComm · Decisions · More ▾ · Pro**, where More▾ is a CSS-only dropdown holding Screener/Readouts/Run-up/Research/API. `grep navddm` on `/pdufa/*` = present. |
| 2 | **Tap targets (44px)** | ✅ done | `@media(pointer:coarse)` rules force 44px min on nav links/rows/chips/⌘K — now in the **SSR** `#navpolish` style (not just the JS layer), so they apply on real touch devices regardless of JS. (Desktop render still measures desktop sizes — that's by design; the rules are pointer-gated.) |
| 3 | **Header brand mark** | ✅ done | Inline-SVG catalyst-pulse logomark now **inside the `.brand` anchor in server HTML** on 730 pages (`class="lm"` present in raw fetch) — precedes the wordmark. Was previously a CSS `::before` (invisible to your DOM probe); now real markup. |
| 4 | **Calendar heatmap (D7)** | ✅ done | `/calendar` server HTML contains the `hmap` hero (weekly cap-tier density SVG). Note: it's a **weekly density bar chart**, not a grid-of-day-cells — so a `.heatmap-cell` probe reads 0, but the viz is live (screenshot on file). |
| 5 | **Cohort mini-distribution (D8)** | ✅ done | `/pdufa/*` (100 pages) now render `coh-dist-v1` — a decision-day-move histogram per cap tier under the flat ±% line (the flat number is kept as the plain-language lead-in, the histogram adds the distribution). |
| 6 | **CWV / font hardening (D10)** | ✅ done | Self-hosted Space Grotesk + IBM Plex Mono; `/fonts/fonts.css` uses `font-display:swap`; `/calendar` `<head>` preloads both key woff2; immutable 1-yr cache; **0 third-party font requests**. |

## The "ODIN" SERP title
⏳ On Google. Live meta is clean (0 ODIN/approval-probability strings in any `<title>`/`<meta>` across 856 pages). Re-index requested in Search Console; only Google's re-crawl can flush the cached SERP title.

## Why your probes disagreed with reality (for the record)
1. **JS-injected UI** — logomark + hamburger were added by `cmdk.js` at runtime, so raw/SSR HTML fetches (and any pass that ran before the script executed) didn't see them. **Fixed by making them SSR.**
2. **Stale script + edge cache** — the 21:32 UTC pass caught a pre-fix `cmdk.js` and a `/calendar` edge copy with `age≈13000s`. `?cb=` busts the browser and edge for the HTML doc, but a separately-cached `cmdk.js`/asset can still be stale.
3. **Probe shape** — "heatmap cells" and "flat ±% number" pattern-matches don't recognize an SVG bar-density chart or a histogram appended below the sentence, respectively.

## Net
Every actionable item across Re-Audits #4 and #5 is ✅ live and now **server-rendered** (verified with `cache:'no-store'` + `?cb=` on the raw HTML, plus screenshots). The only ⏳ is Google re-crawling its cached title. LemonSqueezy paywall is staged and waiting on store/variant IDs.
