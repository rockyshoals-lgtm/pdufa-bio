# pdufa.bio — Pass 13 · Re-audit + new SEO opportunities · 2026-06-26

Verified live (Chrome + Google). Good SEO progress on the new pages; the security P0 still isn't done; and there's a fresh batch of SEO upside below.

## 🔴 Security P0 — STILL not fixed (3rd check)
`/api/data` no-credentials test → **200, 35,773 bytes** (full dataset, no auth). `/api/data.js` still **200**. No free/pro split (`/api/free`, `/api/pro-data` → 404). CORS is scoped to your origin (good, but browser-only — a server-side scraper still pulls everything). **Don't charge for Pro until this endpoint is auth-gated.** (Full detail in pass 11/12.)

## ✅ SEO — verified fixed this round
- **Month pages cleaned up.** Title escape bug gone (`September 2026 FDA PDUFA decisions — FDA Calendar` renders a real em-dash); rows now link **on-site** (4 of 5 → `/pdufa/[ticker]`, building the internal graph); FAQPage schema + the `/why-no-approval-probability` link.
- **Condition pages cleaned up.** Schema now **FAQPage + ItemList**; the bad mis-tags are gone (no more "SBI-100 Ophthalmic Emulsion — Obesity," no Eylea); "disease disease" typo fixed; title scope reconciled.
- **Sitemap healthy:** **170 URLs**, covering month-calendar, readout-month, condition, per-event, research, learn, and decisions pages.
- **New pages indexing:** homepage, `/calendar`, `/coverage`, `/pricing` all show fresh in Google.

## ⚠️ Still open + 🆕 new SEO opportunities (prioritized)

**1. [P1] Old ODIN ghost is STILL in the index.** `site:pdufa.bio` still returns "PDUFA Runup Heatmap," "ODIN Engine — FDA Probability Scoring," "VNDA… ODIN predicted 89.7%," with `4.8★(47)` review stars. Google hasn't dropped them. **Use GSC → Removals** on those specific URLs to purge fast; they dilute the brand SERP and show the per-drug-PoA snippets you've worked to kill.

**2. [P1] Build on-site `/readout/[id]` pages.** Condition-page rows still leak **off-site** (27 of 31 on `/condition/obesity-metabolic` go to ClinicalTrials.gov), and `/readouts` does the same — because no on-site readout pages exist to link to. The PDUFA side got the on-site fix; the **readout side is still donating all its link equity to NIH.** Build `/readout/[ticker-nct]` detail pages (drug, trial design, phase, then a link *out* to CT.gov) and point the rows there. This recovers a huge internal-link surface and wins the "[drug] phase 2 readout" long tail.

**3. [P1] Finish per-event depth — still the long-tail closer.** `/pdufa/UNCY` is essentially unchanged: chart still dated **"2026-06-19"** (7 days stale), **no email capture**, **no related-event links**, still the gated "private beta" dead-end CTA. Add: the sourced story block (CRL/cash/plain-English), a fresh chart, email capture, and **bidirectional internal links** — each per-event page should link to its `/condition/[disease]` and `/calendar/2026/[month]` (right now the hubs link *to* per-event, but per-event links back to neither). This is what makes the page beat a press release.

**4. [P1] Homepage isn't linking to your hubs.** The homepage links to calendar, month archives, conditions, and per-event pages — but **not to `/learn`, `/research`, or `/readouts`.** Add them to the homepage nav + footer. Especially **`/research`** (your backlink asset needs link flow from the strongest page) and **`/learn`** (topical authority).

**5. [P1] Fix/verify structured data on the homepage + per-event pages.** Both returned a JSON-LD block with **no `@type`** (null/"?"). The homepage should carry **Organization + WebSite + SearchAction** (the SearchAction enables a Google sitelinks search box); per-event pages should carry **Event + BreadcrumbList + FAQPage**. Inspect and fix — broken/typeless JSON-LD earns nothing.

**6. [P2] Bring month pages to schema parity** — they have FAQPage; add **ItemList + BreadcrumbList** (conditions already got ItemList).

**7. [P2 — NEW] "FDA decisions this week" page** (`/this-week` or `/upcoming`). High recurring intent ("what FDA decisions this week"), always-fresh (great freshness signal), and a natural daily-return/retail page. Auto-built from the calendar.

**8. [P2 — NEW] AdCom calendar page** (`/fda-advisory-committee-calendar` or `/adcom`). "FDA advisory committee calendar 2026" is searched; you have the `/learn` explainer but no AdCom *calendar*. New SEO surface + the trader feature I flagged earlier.

**9. [P2 — NEW] Year pages:** `/calendar/2027` (capture next-year intent now, before competitors) and a historical `/calendar/2025`. Cheap, evergreen, link targets.

**10. [P2 — NEW] Sitewide "browse" footer mesh.** A footer (on every page) that links all conditions + all months + the hubs creates a strong internal-link mesh and helps Google crawl + understand the site architecture. Pairs with an HTML `/browse` hub page.

**11. [P3 — NEW] Dynamic per-event OG images** (ticker + date + run-up sparkline) — still not shipped; matters for the shareable "tape" and the PR push.

**12. [P3] 301 the `.html` aliases** (`/today.html`, `/app.html` still 200) and keep the GSC indexing requests flowing as new pages ship.

## Top of the stack
1. **[P0] Gate `/api/data`** (security — before Pro).
2. **[P1] On-site `/readout/` pages** (stops the biggest remaining off-site link leak).
3. **[P1] Per-event depth + bidirectional internal links** (long-tail closer).
4. **[P1] Homepage links to /learn /research /readouts + fix homepage/per-event schema.**
5. **[P1] GSC Removals on the ODIN ghost URLs.**
6. **[P2] New surfaces:** `/this-week`, AdCom calendar, `/calendar/2027`, browse-footer mesh.

**Verdict:** the new SEO architecture (month + condition + sitemap + on-site month links + the no-PoA wedge) is genuinely landing — this is the foundation done right. The next gains are **wiring** (readout pages, bidirectional links, homepage→hub links, schema) and **expansion** (this-week, AdCom, year pages) — plus the off-page PR push, which is still the only thing that takes the head terms. And gate that API.

*— Red Team Pass 13 (re-audit + new SEO; live via Chrome + Google).*
