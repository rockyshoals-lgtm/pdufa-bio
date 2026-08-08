# pdufa.bio — Pass 7 · Verify prior items + new action list · 2026-06-25

Re-audited live (Chrome + Vercel + real SERP/index) after the latest build + the 10 GSC index requests. This confirms what's fixed, what's **still open from prior passes**, and the next action items.

## ✅ VERIFIED FIXED this round (don't re-flag)
- **The old ODIN project is DELETED (the big one).** Vercel now shows only `pdufa-bio-staging` + `odin`; the old `pdufa-bio` project is gone. Old ODIN URLs (`/vnda-pdufa`, `/track-record`) now return **404** — they no longer serve the per-drug-PoA content. This closes the guardrail exposure *and* removes the index-pollution at the source. **Biggest cleanup of the engagement.**
- **Canonical host (redirect half):** apex `pdufa.bio` → `www.pdufa.bio` is a **308 permanent redirect**. Good.
- **`/pricing` is the new product:** Free / $29 Pro, "we will never fake an approval probability," links to a "here's why" page. Pro promises the watchlist + **weekly digest** (the email value prop is now stated — but not yet captured anywhere; see C4).
- Still holding from prior passes: hero-card bug fixed, modals fixed, "Snapshot · updated" wording, `/` + `/calendar` cache purged + look-inside tape, `/learn` (7), `/sources`, `/research`.
- You requested 10 pages for indexing in GSC — correct move for the **new** pages.

## ⚠️ STILL OPEN — page-1 levers from the Pass-6b plan that did NOT ship
The old product is *removed*, but the *winnable new pages* aren't built yet. We've deleted the negative; we haven't added the positive.

**A2 — old URLs are bare 404, not 301/410.** 404 deindexes slowly and passes **zero** link equity. Upgrade:
- **301** the highest-value old slugs to their new equivalents — `/vnda-pdufa` → `/fda-decision/VNDA-2026-02-20` (or `/pdufa/VNDA`); the old `/pricing`, `/calendar`, "data-provenance" → new `/pricing`, `/calendar`, `/sources`.
- **410 Gone** the ones with no equivalent (`/track-record`, `/odin*`, the runup-heatmap, "ODIN engine/score" pages) so Google drops them fast.
- *You'll need the full old-slug list* — pull it from GSC "Pages" (indexed) or the old repo's routes. *Acceptance: every old URL 301s or 410s; none bare-404.*

**A3 — purge the stale index.** Google still shows the old ODIN pages (Hávamál homepage, "ODIN AI approval probability," `4.8★(47)`). The 10 index requests help the *new* pages; the *old* ones need: GSC **Removals** on the worst (the "ODIN predicted 89.7%" VNDA page, "ODIN Engine," "Pricing Free to Elite"), plus the 301/410s above so re-crawl drops them. *Acceptance: `site:pdufa.bio` no longer returns ODIN/probability pages or the star ratings.*

**A4 — cookie half not done.** The redirect works, but the gate "remember me" cookie isn't scoped to the registrable domain, so unlocking on one host drops on the other. Set `Domain=.pdufa.bio`. *Acceptance: unlock persists across apex+www.*

**B1 — month-archive pages: NOT shipped.** `/calendar` is still one long scroll; no `/calendar/2026/[month]` and no month-picker. **This is the #1 structural SEO move** (CatalystAlert ranks with month pages) and doubles as the retail month-picker. Build `/calendar/2026/[month]` + `/readouts/2026/[month]` (server-rendered, prev/next, "About PDUFA dates in [Month] 2026" blurb, `ItemList`+`FAQPage`+`BreadcrumbList` schema, linked from each `/calendar` month header).

**B2 — condition pages: NOT shipped** (`/condition/obesity` → 404). Build `/condition/[slug]` for obesity, alzheimers, oncology, rare-disease/orphan, nash, cns, cardiometabolic. (CheckRare ranks #3 on the head term with an orphan vertical — proof these win.) Doubles as the retail condition lens.

**C — per-event depth: NOT shipped** (`/pdufa/UNCY` is byte-for-byte the same):
- **C1 story block** — still missing the **June-2025 CRL + resubmission** (the entire thesis), cash runway, plain-English drug. Indication still vague ("Kidney disease" vs "high blood phosphate in dialysis patients").
- **C2 freshness** — chart still says **"Price path to 2026-06-19"** (now 6 days stale).
- **C3 related-event links** — none.
- **C4 email capture** — still dead-ends at "Opens the pdufa.bio app (private beta)." The `/pricing` page promises a weekly digest; there's nowhere to sign up. Add "🔔 notify me before this date" + email.
- **C5 schema/OG** — add `Event`+`FAQPage`+`BreadcrumbList`; dynamic OG image.

## ⚠️ STILL OPEN — older items (confirmed live, not fixed)
- **Calendar data dupes (since Pass 3):** VRDN listed twice on 06-30 ("Veligrotug (VRDN-001)" + "VRDN-001," same drug/indication); GSK tebipenem shown approved 06-18 **and** pending 06-30. Dedup on (ticker + normalized-drug + date); reconcile the GSK approved/pending.
- **Plain-English indications:** raw strings remain ("Dephosphorylated Phosphatase and Tensin…", "MR-100A-01(Low dose estrogen…"). Add a human-readable layer (retail + readability).

## 🆕 NEW finding — inconsistent global nav across templates
- `/calendar`, `/pdufa/*`, `/learn` nav = **9 items**: Calendar · Readouts · Devices · Decisions · Approvals/yr · Trial odds · Learn · Research · Methodology.
- `/pricing` nav = **5 items**: Calendar · Readouts · Research · Coverage · Pricing.
Two different navs = confusing, and it fragments internal linking (Googlebot and users see different site structures per page). **Reconcile to ONE nav** (group the 9 into ~4–5 menus: Calendar▾ / Decisions▾ / Learn▾ / Pricing), and make sure **Pricing + Coverage** are reachable from every page and the data pages are reachable from `/pricing`.

## NEW ACTION ITEMS (prioritized for the builder)
1. **[P0] Finish the index cleanup (A2+A3):** 301 high-value old slugs → new equivalents, 410 the rest (no bare 404s); GSC Removals on the worst ODIN/PoA URLs. *This converts the deletion into ranking equity + a clean brand SERP.*
2. **[P0] Ship month pages (B1)** `/calendar/2026/[month]` + `/readouts/2026/[month]` — the top winnable-SEO + retail move.
3. **[P1] Ship condition pages (B2)** `/condition/[slug]` — winnable vertical SEO + retail lens.
4. **[P1] Deepen `/pdufa/[ticker]` (C1–C5):** story block (CRL/cash/plain-English), fresh chart, related links, **email capture**, Event/FAQ schema, OG image.
5. **[P1] Fix the calendar dupes** (VRDN, GSK tebipenem) and add the plain-English indication layer.
6. **[P1] One consistent global nav** across all templates; ensure Pricing/Coverage are global.
7. **[P1] Scope the gate cookie `Domain=.pdufa.bio`** (A4 cookie half).

## How we'll know it worked
- `site:pdufa.bio` returns only new pages (no ODIN/probability, no `4.8★`).
- `/calendar/2026/september`, `/condition/obesity`, etc. return 200 and appear in GSC.
- `/pdufa/[ticker]` pages carry the story + email field + are fresh-dated.
- pdufa.bio starts surfacing for month/condition/`[ticker] PDUFA date` long-tail.

**Bottom line:** the **hard cleanup is done** — the old ODIN product is deleted, the guardrail is closed, and the canonical redirect works. But the **page-1 growth work hasn't started**: no month pages, no condition pages, no per-event depth, old URLs only 404 (not 301/410), and the index is still stale. Removing the old product was necessary; now build the winnable new surface. Items 1–2 are the highest leverage — do them next.

*— Red Team Pass 7 (live verify via Chrome + Vercel + index/SERP).*
