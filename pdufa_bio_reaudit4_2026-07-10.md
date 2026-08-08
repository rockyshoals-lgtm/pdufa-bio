# pdufa.bio — Re-Audit #4 (post design-build)
**Date:** 2026-07-10 · **Lens:** UX / UI / SEO · **Method:** live browser + DOM/CSS probes + SERP re-test
**Baseline:** `pdufa_bio_design_battleplan_2026-07-10.md`
Product-strategy use only; not investment advice.

---

## TL;DR — the design battle plan largely landed; the site now *looks like the category winner*

The builder executed the highest-impact design moves, and the difference is dramatic. pdufa.bio now has a **real type identity, data-viz on every row, and global search** — it reads like a precision "catalyst terminal," not a tidy blog. This is the biggest single-audit quality jump in the series.

**But the same three ~15-minute SEO-hygiene fixes are still open for a fifth straight audit**, and mobile (hamburger + tap targets) is still unaddressed.

---

## What shipped since last audit ✅

| Battle-plan ticket | Status | Evidence (live 2026-07-10) |
|---|---|---|
| **D2 — Type system** | ✅ **SHIPPED** | `@font-face` now loads **Space Grotesk** (headings — confirmed on h1 across home + detail), **IBM Plex Mono** (data/numerics), **museo-sans** (body). The generic system-font look is gone. Single biggest perceived-quality gain. |
| **D5 — Sparkline on every row** | ✅ **SHIPPED** | 22 inline-SVG sparklines on the homepage: a green/red run-up mini-chart now sits on **every "Next FDA Decisions" card and every "Recently Decided" row.** The homepage finally *is* "the tape." |
| **D6 — Global search / ⌘K** | ✅ **SHIPPED** | Persistent "Search ⌘K" control present on home + detail pages. |
| **D1 — Nav overflow bug** | ✅ **FIXED** | Detail-page nav consolidated to **8 items on a single row** (Calendar · Conferences · AdComm · Decisions · Screener · Research · Pro) — the previous 11-item wrap-into-the-logo bug is gone. |
| **B6 — API** (prior) | ✅ still live | `/api/v1/pdufa` → 200. |

**Design standing now:** pdufa.bio has moved from "cleanest but plain" to **"most distinctive instrument in the category."** The tabular-mono data language + sparkline tape + search-first entry is a combination **no competitor has** — it now plausibly out-designs even TheraRadar on the "trader instrument" axis, while remaining far cleaner than RTTNews/FDA Tracker/MarketBeat. On a refreshed scorecard, **UI moves 4 → 5** and UX ticks up with global search.

---

## What's still open ❌

### Design (from the battle plan)
| Ticket | Status | Note |
|---|---|---|
| **D1 (full)** — grouped nav + mobile menu | 🟡 partial | Overflow fixed, but homepage nav is still **11 flat items**, no dropdown grouping, and **no hamburger/mobile-menu component** in the DOM. Home and detail navs still differ slightly (home adds Run-up/Readouts/API). |
| **D3** — 44px tap targets | ❌ | Still **31 of 61** interactive elements render under 40px tall. |
| **D4** — brand mark | ❌ | Header logo is still a plain text wordmark; no icon mark. (Favicon/OG images not confirmed — worth checking.) |
| **D7** — calendar heatmap | ❌ | Not shipped. |
| **D8** — cohort mini-distribution | ❌ | `±X% cohort` is still a flat number, not a distribution. |
| **D9 / D10** — motion polish + CWV/font hardening | ❔ | Not verified; verify self-hosted fonts use `font-display:swap` + preload so the new type doesn't hurt LCP/CLS. |

### SEO hygiene — **still all three open (5th audit running)**
- `/calendar` still self-canonicals to **non-www** (`https://pdufa.bio/calendar`); `/pdufa-calendar` → www. **Inconsistent.**
- Sitemap still **170 URLs, non-www**, and still **missing `/conferences`, `/adcomm`, `/pdufa-calendar`.**
- Google still shows the stale, off-brand **"…& ODIN Scores | PDUFA.BIO"** title for `/pdufa-calendar` (live page is clean; needs re-index + a guard against ODIN/approval-probability strings in public meta).

*(Ranking held: `/pdufa-calendar` is still page 1 for "PDUFA calendar 2026 upcoming FDA decision dates.")*

---

## The recurring pattern (worth flagging to the owner)
Across five audits the builder has reliably shipped **features and visible design** (API, Screener, staleness flags, type system, sparklines, search) but has **never once done the three cheap SEO-hygiene fixes** — canonical, sitemap, stale-title flush. These are ~1 hour total, they're the highest ROI work left, and they directly gate how fast the (now much better-looking) pages climb. Recommend making them a hard blocker on the next deploy rather than an optional ticket.

---

## Priority for the next cycle
1. **The three SEO-hygiene fixes** — canonical → www everywhere; regenerate sitemap (www + conferences/adcomm/pdufa-calendar); request re-index to flush the ODIN title. *(~1 hr, force it.)*
2. **Mobile: hamburger + drawer, and 44px tap targets** — the design is now desktop-beautiful but mobile ergonomics are still the weakest, unverified surface. Needs real-device QA.
3. **D4 brand mark + per-event OG images** — cheap recognition/CTR win to match the new visual polish.
4. **D7 calendar heatmap + D8 cohort distribution** — the remaining signature data-viz that would put the design clearly ahead of everyone.
5. Confirm **font-loading is CWV-safe** (swap + preload + subset) so the new typefaces help, not hurt, Core Web Vitals.

**Bottom line:** design-wise, pdufa.bio just went from parity to pole position — the type system + sparkline tape + search are exactly the differentiators that beat TheraRadar and StockTitan on craft. Close out mobile, the brand mark, and the stubborn SEO plumbing, and the "cleanest, most distinctive, most complete, cheapest" claim is fully earned.

---
## Sources (live 2026-07-10)
pdufa.bio `/`, `/calendar`, `/pdufa/CELC`, `/pdufa-calendar`, `/sitemap.xml`, `/api/v1/pdufa` — https://www.pdufa.bio/ · SERP: Google "PDUFA calendar 2026 upcoming FDA decision dates." Fonts/nav/tap-target/sparkline findings from live DOM + computed-style probes.
