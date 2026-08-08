# pdufa.bio — Re-Audit #3 + Design Battle Plan
**Date:** 2026-07-10 · **Lens:** UX / UI / SEO-design · **Method:** live browser, DOM/CSS probes, competitor visual benchmark
Product-strategy use only; not investment advice.

---

## Part A — Re-audit delta (what moved since re-audit #2)

| Item | Status now | Note |
|---|---|---|
| **B6 — Public API** | ✅ **SHIPPED** | `/api/v1/pdufa` → **200** (was 404); nav now shows **API** + a new **Screener** tab. |
| **B4 — Screener/filter** | 🟡 **PARTIAL** | A "Screener" nav item now exists — verify it delivers true cross-event (ticker/TA/phase/type) filtering; the main `/calendar` still has no inline filter controls. |
| Canonical `/calendar` → non-www | ❌ **Still open** | `/calendar` still self-canonicals to `https://pdufa.bio/calendar`; `/pdufa-calendar` → www. Unchanged for 3 audits. |
| Sitemap (non-www, 170 URLs, missing new pages) | ❌ **Still open** | Still 170 URLs, non-www, no `/conferences` `/adcomm`. Unchanged for 3 audits. |
| Stale "ODIN Scores" SERP title | ❌ **Still open** | Google still shows the off-brand cached title. |
| Readouts errors in server HTML (SSR) | ❌ **Still open** | Cleanup remains client-side only. |

**Pattern:** the builder keeps shipping *features* (API, Screener, staleness flags) but has now skipped the **three ~15-minute SEO-hygiene fixes for three audits running.** They are the cheapest, highest-leverage work left and should be forced to the top of the queue before more features land.

**New issues found this pass (both design/IA):**
- 🔴 **Nav overflow bug.** On the detail-page template the navigation has grown to ~11 links and **wraps onto a second line that collides with the "pdufa.bio" wordmark** (verified on `/pdufa/CELC` — "odds / Learn / Research / Methodology…" underlap the logo). It looks broken.
- 🟠 **Inconsistent global nav.** The homepage nav (Calendar · Conferences · AdComm · Decisions · Run-up · Readouts · Screener · API · Research · Pro) is a **different set** from the detail-page nav (Calendar · Readouts · Devices · Decisions · Approvals/yr · Trial-odds · Learn · Research · Methodology · Coverage · Pricing). Two different menus = confusing IA and a broken sense of place.

---

## Part B — Design verdict: good bones, generic finish

**Where pdufa.bio sits today:** it is already **cleaner than every cluttered incumbent** (RTTNews, FDA Tracker, MarketBeat — ad-heavy, dated, dense with cross-sell) and **on par with the two modern players** (StockTitan's polished dark UI; TheraRadar's airy light "intelligence tool"). But "cleaner than a cluttered competitor" is not the same as "best-designed in the category." Right now pdufa.bio wins on *restraint*, not on *craft or identity*. It looks like a well-built default — not like a product with a point of view.

**The core diagnosis:** pdufa.bio has **strong structure and weak signature.** Good grid, good semantic color, good hierarchy — wrapped in the browser's default system font, with almost no data-visualization, no identity mark, and mobile/nav rough edges. It's a 7/10 that reads as "tidy," when the positioning ("the FDA-catalyst *tape*", "facts to weigh") wants a 9/10 that reads as "the professional instrument for catalyst traders."

### The seven things holding the design back (evidence-based)

1. **Typography is the browser default.** `font-family` resolves to `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto…` — no custom typeface anywhere. This single fact is why the site reads "plain." *(Notably, even TheraRadar runs on system fonts — so a real type system out-designs the whole field, not just the laggards.)*
2. **No numeric/tabular treatment.** Tickers, dates, `±%`, and the hero stats — the actual *data* of the product — are set in the same proportional body font. Precision products (Bloomberg, Stripe, Linear) render numbers in a **tabular mono** so figures align and *feel* exact. pdufa.bio doesn't.
3. **Almost no data-visualization.** The only chart is the 120-day run-up line on detail pages. The calendar, readouts, and homepage are text/cards only. For a product whose pitch is *run-up history + cohort base rates*, that's a wasted signature — "clean" has tipped into "sparse."
4. **No identity / brand mark.** The logo is a plain text wordmark. TheraRadar has a radar-circle mark; pdufa.bio has none. Nothing to remember or screenshot.
5. **Navigation is overloaded, inconsistent, and mobile-fragile.** 11 flat links, no grouping, no dropdown, a wrap-into-logo bug, two different menus across page types, and **no detectable hamburger/mobile-menu component** in the DOM.
6. **Mobile ergonomics unverified and likely weak.** **31 of 61 interactive elements render under 40px tall** — below the 44px tap-target floor (WCAG 2.5.5 / Apple HIG). Combined with the missing mobile nav, mobile is the likely weakest surface (and couldn't be visually confirmed — needs real-device QA).
7. **No motion, no state polish.** No transitions, hover choreography, skeleton loaders, or empty-state craft observed — the details that separate "premium" from "template."

---

## Part C — Competitor design benchmark (where the white space is)

| Site | Aesthetic | Signature strength | Signature weakness |
|---|---|---|---|
| **RTTNews** | Dated news portal | Authority/history | Ad-heavy, cluttered, pagination, 2010s look |
| **FDA Tracker** | Generic FullCalendar widget | Familiar month grid | Flat, gray, no identity, thin |
| **MarketBeat** | Finance-portal density | Data + analyst integration | Ad noise, ticker-tape clutter |
| **StockTitan** | Polished modern dark | Real-time feel, sentiment chips | It's a news feed, not a calendar; busy |
| **BiopharmaWatch** | Feature-dense SaaS | Breadth (PoA, screeners) | Generic template, fabricated-looking testimonials |
| **TheraRadar** | Airy light "intelligence tool" | **Search-first hero, question IA, logo mark, grouped nav** | Also system fonts; no dark/terminal option; less "trader" energy |
| **pdufa.bio** | Clean dark, restrained | **Cleanest, best hierarchy, honest tone** | Generic type, no data-viz, no identity, nav/mobile rough |

**The unclaimed white space:** *nobody* in the set combines **(a) a distinctive typeface system + (b) pervasive data-visualization + (c) terminal-grade information density + (d) a genuine brand identity.** TheraRadar owns "calm intelligence tool"; the incumbents own "cluttered portal." The open, ownable territory that fits pdufa.bio's *tape* positioning is **"the Bloomberg-terminal-for-catalysts, redrawn with Linear-grade craft."** That's how you don't just tie on cleanliness — you win on design.

---

## Part D — The winning design thesis: **"The Catalyst Terminal"**

One sentence: *pdufa.bio should look and feel like a precision instrument for catalyst traders — dark, dense, data-drenched, and unmistakably branded — not like a tidy blog about FDA dates.*

Five pillars:

1. **A real type system.** Adopt a distinctive but legible pairing:
   - **Display/headings:** a modern grotesk (e.g. *Geist*, *Söhne*, *Inter Display*, or *Space Grotesk*) for hero + section heads — instant personality.
   - **Data/numerics:** a **tabular monospace** (e.g. *Geist Mono*, *IBM Plex Mono*, *Commit Mono*) for **every ticker, date, `±%`, price, and stat.** This alone will make the product read as "precise" and differentiate it from all seven competitors in one stroke.
   - Lock a type scale (e.g. 12/14/16/20/28/42/64) with tabular-nums enabled on all figures.

2. **Data-viz as the signature — everywhere, not just detail pages.**
   - **Sparkline on every row.** Each calendar card and readout/decision row gets a tiny run-up sparkline (you already generate the 120-day series — reuse it at 60×20px). Turns a text list into a "tape."
   - **Cohort context inline.** The `±X% cohort` chip becomes a mini distribution bar showing where this name's cap-tier typically moves — visual, not just a number.
   - **Calendar heatmap.** A month/quarter density heatmap (how many catalysts per week, colored by cap tier) as a hero element on `/calendar` — a screenshot-worthy signature no competitor has.
   - **Decisions archive:** approval/CRL ratio bars by TA/sponsor.

3. **One identity, everywhere.** Design a simple mark (a stylized "catalyst pulse"/candlestick-into-spark, or a PDUFA-date pin) and apply it as favicon, OG image, loading state, and empty states. Ship a proper **1200×630 OG image template per event** (ticker + date + sparkline) — huge for social/SEO click-through and brand recall.

4. **Search-first + command palette.** Steal TheraRadar's best move: a prominent **global search** ("Find any ticker, drug, or date") in the header, plus a **⌘K command palette** to jump to any ticker/date/TA. This is both a UX leap and an SEO/engagement win (internal search → better navigation signals).

5. **Fix the fundamentals that make it feel finished.**
   - **Consolidate + group the nav** to ~5 top items with dropdowns (Calendar ▾ [PDUFA · Readouts · Conferences · AdComm · Devices] · Decisions · Run-up/Research · Screener · Pro), one consistent menu across all page types, and a real **mobile hamburger + drawer.**
   - **44px minimum tap targets**; real-device mobile QA.
   - **Motion & states:** 150–200ms transitions, hover elevation on cards, skeleton loaders on data fetch, crafted empty/error states.
   - **Core Web Vitals as design discipline:** self-host the fonts (`font-display: swap`, preloaded, subset) so the new type costs nothing in LCP/CLS; keep the sparklines as inline SVG (no heavy chart lib). Good CWV is also a direct SEO ranking factor — design and SEO align here.

---

## Part E — Ranked design battlelog

Impact = effect on "best-designed / most premium in category." Effort = design+build lift.

### Quick wins (this week)
| # | Ticket | Impact | Effort |
|---|---|---|---|
| **D1** | **Fix nav overflow + unify to one grouped menu** (dropdowns; ≤5 top items; same nav on every template; add mobile hamburger + drawer). Kills the wrap-into-logo bug and the two-menu inconsistency. | **H** | **M** |
| **D2** | **Ship the type system** — self-hosted display grotesk for headings + **tabular mono for all numerics** (tickers/dates/±%/stats), `font-display:swap`, preload/subset. Biggest single perceived-quality jump. | **H** | **M** |
| **D3** | **Enforce 44px tap targets** + real-device mobile QA pass. | **M** | **L** |
| **D4** | **Add a favicon + brand mark + per-event OG images** (ticker · date · sparkline). Brand recall + social CTR. | **M** | **M** |

### Signature bets (next)
| # | Ticket | Impact | Effort |
|---|---|---|---|
| **D5** | **Sparkline on every calendar/readout/decision row** (reuse the 120-day series at ~60×20 inline SVG). Turns lists into "the tape." | **H** | **M** |
| **D6** | **Global search + ⌘K command palette** across tickers/drugs/dates/TAs. | **H** | **M–H** |
| **D7** | **Calendar heatmap hero** on `/calendar` (catalysts-per-week density by cap tier) — the screenshot-worthy signature element. | **H** | **M–H** |
| **D8** | **Cohort mini-distribution** replacing the flat `±X%` chip; **approval/CRL ratio bars** on the decisions archive. | **M** | **M** |
| **D9** | **Motion + state polish** — transitions, hover elevation, skeleton loaders, crafted empty/error states. | **M** | **M** |
| **D10** | **CWV/design hardening** — self-host fonts, inline SVG viz, lazy-load below-fold, verify LCP/CLS/INP green. | **M** | **M** |

### Still-open, non-design (force ahead of new features)
- **Canonical → www everywhere; regenerate sitemap (www, include conferences/adcomm/pdufa-calendar); flush the stale ODIN SERP title; clean readouts at the data layer.** Three audits unactioned. ~1 hour total.

---

## Part F — How we actually beat them (the one-paragraph answer)
We don't beat RTTNews/FDA Tracker/MarketBeat on design — we already have; they're cluttered and dated. The real target is **TheraRadar and StockTitan**, and we beat them by claiming the one aesthetic neither owns: **the precision "catalyst terminal."** Concretely, that's (1) a **tabular-mono data language** so every ticker/date/percentage looks engineered — a differentiator *no* competitor has; (2) **a sparkline on every row + a calendar heatmap** so the product visibly *is* the "tape" our copy promises; (3) **a real mark + per-event OG images** so it's recognizable and shareable; and (4) **search-first + ⌘K + a fixed, grouped, mobile-correct nav** so it feels faster and more considered than TheraRadar. Restraint got us to parity; **identity + data-viz + craft** is how we take the category.

*A target-state visual concept accompanies this document (rendered in chat). Informational product-strategy analysis. Not investment advice.*

---
## Sources (live 2026-07-10)
pdufa.bio `/`, `/calendar`, `/pdufa/CELC`, `/pdufa-calendar`, `/readouts`, `/sitemap.xml`, `/api/v1/pdufa` — https://www.pdufa.bio/ · Benchmark: https://theraradar.com/ · prior competitor captures (StockTitan, RTTNews, FDA Tracker, MarketBeat, BiopharmaWatch) from earlier audits this session.
