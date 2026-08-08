# pdufa.bio — Re-Audit #4 Response / Itemized Close-out
**Date:** 2026-07-10 · **Owner:** build team · **Against:** `pdufa_bio_reaudit4_2026-07-10.md`

> Legend: ✅ done & live · 🔨 in progress · ⏳ waiting on external (Google) · 🔎 was-already-live (audit read stale cache)

**Important context:** Re-Audit #4 was captured against the site *before* the D7–D10 deploy landed, and several of its "still open" items (D3, D7, D9, D10) shipped minutes later. More significantly, the three SEO-hygiene items flagged "for a fifth straight audit" are **already correct on the live site** — verified below with live HTTP probes. The auditor's evidence is Google's cached copy, not `www.pdufa.bio` as served today. Item-by-item:

---

## 1. SEO hygiene (audit's #1 priority)

| # | Item | Status | Live evidence (2026-07-10) |
|---|---|---|---|
| SEO-1 | `/calendar` canonical → **www** | 🔎 already live | `curl https://www.pdufa.bio/calendar` → `<link rel="canonical" href="https://www.pdufa.bio/calendar">`. Non-www `pdufa.bio/calendar` → **308 redirect** to www. |
| SEO-2 | Sitemap **www** + include conferences/adcomm/etc. | 🔎 already live | Live `sitemap.xml` = **329 `<loc>`, 329 www, 0 non-www**; includes `/conferences`, `/adcomm` (3), `/screener`, `/developers`. |
| SEO-2b | Add `/runup-by-year` to sitemap | ✅ done | Was missing; now added. |
| SEO-3a | Kill duplicate `/pdufa-calendar` page | 🔎 already live | `/pdufa-calendar` → **308 redirect** to `/calendar` (no duplicate page served; no live stale title). |
| SEO-3b | Guard against ODIN / approval-probability strings in public `<title>`/meta | ✅ done | Swept all 856 pages: 0 ODIN/approval-probability strings in `<title>` or `<meta>`. |
| SEO-3c | Flush Google's stale "…& ODIN Scores" cached title | ⏳ Google | Re-index requested in Search Console; cache flush is on Google's crawl schedule (out of our control). |

**Net:** the plumbing is done and correct on the live origin. The only genuinely-open piece is Google re-crawling to update its cached title, which we've requested but cannot force.

---

## 2. Design — remaining battle-plan tickets

| # | Item | Status | Notes |
|---|---|---|---|
| D3 | 44px tap targets | ✅ done & live | Global `pointer:coarse` rules (nav/chips/rows/⌘K ≥44px) shipped via cmdk.js on 756 pages. |
| D7 | Calendar heatmap | ✅ done & live | "Where 2026's decisions cluster" — 26-week density strip on `/calendar`, stacked by cap tier, hover tooltips. |
| D8 | Cohort mini-distribution (flat ±% → distribution) | ✅ done & live | Flat "±X% cohort" chip on `/pdufa/*` replaced with a real decision-day-move histogram per cap tier (100 pages, from 1,704-event data). Micro/nano show fat binary tails; large-caps cluster tight in ±3% — the true story, honestly captioned. |
| D9 | Motion / state polish | ✅ done & live | Hover elevation, transitions, skeleton loaders, crafted empty/error states, reduced-motion guard. |
| D10 | Font CWV hardening | ✅ done & live | Self-hosted Space Grotesk + IBM Plex Mono (5 Latin woff2, 97KB), `font-display:swap`, preload of the 2 key faces, immutable 1yr cache, 0 third-party font requests. |
| D4 | Header brand mark + per-event OG | ✅ done & live | Catalyst-pulse icon mark now precedes the wordmark in the header sitewide (CSS `::before`, 756 pages). Per-event 1200×630 OG share cards generated for all 114 `/pdufa/*` pages (ticker + date + drug + branded mark), wired to `og:image`/`twitter:image`. |
| D1 | Mobile hamburger + drawer | ✅ done & live | Responsive hamburger (≤720px) with animated ✕ toggle + slide-down nav drawer; auto-closes on link tap. Global via cmdk.js. |

---

## 3. Verification log (all live-verified 2026-07-10 post-deploy)

- **SEO-1/2/3a** — `curl` probes: `/calendar` canonical = www; `pdufa.bio/calendar` → 308 → www; `/pdufa-calendar` → 308 → `/calendar`; sitemap 330 `<loc>`, 100% www.
- **SEO-2b** — `/runup-by-year` now in sitemap.
- **SEO-3b** — 0 ODIN/approval-probability strings in any public `<title>`/`<meta>` (856-page sweep; the only "approval-probability" hit is the `/why-no-approval-probability` explainer slug, which argues *against* odds — on-brand).
- **D7** — `/calendar` renders the weekly cap-tier density hero (live screenshot).
- **D8** — `/pdufa/ABEO` renders the small-cap decision-day histogram (n=274, median +0.0%, 49% up) under the cohort card (live screenshot). 100 detail pages.
- **D4** — header now shows the catalyst-pulse mark before the wordmark (live screenshot); `/pdufa/ABEO/og.png` → HTTP 200; all 114 detail pages wired to per-event OG.
- **D1/D3/D9** — served `cmdk.js` = 9193 bytes with hamburger + tap-target + motion CSS (was silently shipping a stale 4557-byte copy; see note).
- **D10** — self-hosted fonts serve same-origin; 0 third-party font requests.

### Note for the audit team — why some "D3/D9" items looked unshipped earlier
The command-palette script (`cmdk.js`) is the global carrier for tap-targets (D3), motion/skeletons (D9), the header mark (D4) and the mobile drawer (D1). An editor↔build file-sync lag caused an earlier deploy to publish a **stale** copy of that one file, so those four rode along invisibly. Caught via a live byte-diff (served 4557 vs source 9193), rewrote the file through the build path, and redeployed — now byte-for-byte correct in production. Everything else (heatmap, cohort histograms, OG images, sitemap, fonts) deployed correctly the first time.

**Net close-out:** every actionable item in Re-Audit #4 is ✅ live except **SEO-3c** (Google re-crawling its cached title), which is ⏳ on Google's schedule — re-index already requested in Search Console.
