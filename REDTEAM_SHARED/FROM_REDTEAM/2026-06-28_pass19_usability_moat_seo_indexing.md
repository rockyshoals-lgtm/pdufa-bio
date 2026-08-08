# pdufa.bio — Pass 19 · Usability · Moat · SEO + "how many pages are indexed?" · 2026-06-28

Live re-audit after the builder's latest content push. Verified against the live site (Chrome) and **Google Search Console** (property `sc-domain:pdufa.bio`). Focus: usability, competitive moat, SEO. Legend: ✅ good · ⚠️ fix · 🔴 urgent.

---

## ⭐ Direct answer: how many pages are indexed?

**11.** Per GSC Page-Indexing (last update 6/11/26): **11 indexed · 25 not-indexed · 36 total known to Google.** Your sitemap lists **170** URLs — so **~134 of them Google hasn't even processed**, and only **11** can actually be served in search.

| GSC bucket | Count |
|---|---|
| **Indexed** | **11** |
| Not indexed — **Redirect error** | 17 |
| Not indexed — Page with redirect | 3 |
| Not indexed — Crawled, currently not indexed | 5 |
| **Total known to Google** | **36** |
| URLs in sitemap (live, real pages) | **170** |

This is the single most important finding in the audit, and it outranks everything else below.

---

## 🔴 The headline: Google is indexing the WRONG product, and almost none of the right one

Every `site:pdufa.bio` probe returns the **old ODIN product**, not the current site:
- `/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar` — **all 404 on the live site**, all still indexed, all titled *"…AI Approval Scores / ODIN Scores."*
- The homepage's cached snippet still reads *"ODIN AI approval probability scores… TIER_1 predictions have a 93.6% approval rate."*

So the pages Google shows biotech investors are (a) **charter-violating** (the exact "approval probability / 93.6%" framing your live `/why-no-approval-probability` and `/methodology` pages exist to repudiate), and (b) **partly dead** (404s). Meanwhile the on-charter site — and the builder's brand-new content — is effectively invisible. **You are being out-ranked on your own domain by the product you discontinued.**

### Root cause — CORRECTED after direct testing (see ticket `pass19b`)
⚠️ My first take here said "apex 308-redirects to www, so switch to www." **That was wrong** — built on a stale assumption from earlier passes. I then fetched both hosts directly:
- `https://pdufa.bio/decisions` → **200**, canonical apex, links apex.
- `https://www.pdufa.bio/decisions` → **200 (NO redirect)**, canonical apex, links www.
- Both roots → 200. **Neither host redirects.** Both serve identical content.

So the real situation: **both apex and www serve 200 with no redirect**, while canonical tags + sitemap + robots all consistently point to **apex**. The fix is therefore the *opposite* of what I first wrote — **add** a `301 www → apex` to collapse to one host (apex is already the canonical everywhere), *not* "switch to www."
- Compounding: **two sitemaps submitted** — apex `pdufa.bio/sitemap.xml` (170, read Jun 25) + a **stale `www.pdufa.bio/sitemap.xml` (35, read Feb 25)** from the old build.
- Also: the "11 indexed" GSC snapshot is dated **Jun 11** — *before* the Jun-25 sitemap and the latest content push — so it lags the live site and is likely already improving. Combined with **zero backlinks** (new domain = slow crawl), low indexing is partly just discovery time, not only a config bug.

**Full builder fix is in the dedicated ticket → `2026-06-28_pass19b_TICKET_canonical_host_indexing.md`** (301 www→apex, root-relative links, drop stale sitemap, 410 the ghosts, dedupe `/pricing.html`, then re-submit + request-index).

> **Why I did NOT mass request-index today:** with two hosts both serving 200 and a duplicate-content signal unresolved, and with the indexing snapshot predating the new sitemap, request-indexing now is premature — do it *after* the host consolidation ships (ticket step "After deploy").

## ✅ GSC actions I took this pass (Chrome, your logged-in property)
- **Submitted temporary-removals for the 3 dead ODIN ghost URLs** (`/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar`) — all three now "Processing request" in GSC → Removals. Covers www + non-www + http/https. Reversible anytime. This pulls the forbidden "93.6% approval" snippets out of Search within days.
- **Did NOT** delete sitemaps, change settings, or request-index (see box above — premature until the host fix ships).

### Builder's GSC follow-ups (AFTER the host/canonical fix is deployed)
1. Re-submit the corrected (www) sitemap; remove the stale 35-page `www` sitemap entry.
2. URL-Inspect → Request Indexing the ~10 priority pages (homepage, `/calendar`, `/decisions`, `/readouts`, `/methodology`, top `/pdufa/[ticker]`, `/learn/what-is-a-pdufa-date`).
3. Validate-fix the "Redirect error" and "Page with redirect" groups in GSC → Pages.

### Old ODIN ghosts — DONE in GSC this pass (durable fix still needed in code)
`/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar` (all 404 live, all titled "…AI Approval Scores," all showing "93.6%"). **I submitted GSC temporary-removals for all three today** (blocks them from Search ~6 months; reversible). That stops the brand-damaging snippets fast — but it's a 6-month patch. **Durable fix (builder):** return **410 Gone** (or 301 to `/calendar`) so they drop permanently.
3. **~134 undiscovered URLs.** Confirm the sitemap is actually submitted and read (GSC → Sitemaps), referenced in `robots.txt`, and that deep pages are internally linked from indexed hubs. Then **Request indexing** for the ~15–20 priority URLs (homepage, `/calendar`, `/decisions`, top `/pdufa/[ticker]`, `/learn/what-is-a-pdufa-date`) to prime the pump.
4. **`/pricing` + `/pricing.html` both in sitemap** = duplicate. Pick one canonical, 301 the other, drop the loser from the sitemap.

Until #1–#2 are fixed, **new content will keep not-indexing** no matter how much the builder ships. This is the bottleneck.

---

## ✅ What the builder shipped (verified live, all 200, all ODIN-free)

Real, on-charter expansion — this is good work:
- **`/decisions`** — "FDA Decisions Archive: Approvals & CRLs," 2,918 words, **356 internal links** (a real hub). CRLs *with reasons*, approvals source-linked.
- **`/fda-decision/[TICKER-DATE]` ×20** — per-outcome pages (e.g., `IBRX…CRL`, `PHAR…CRL`), ~620 words each. Captures post-decision "did X get approved?" search demand. This is the readout-detail idea, executed for decisions.
- **`/devices`** — "2026 FDA Medical Device Calendar." New vertical (expands TAM beyond drugs).
- **`/clinical-trial-success-rates`** & **`/fda-approval-rate`** — head-term informational SEO content (1,150 words each, BreadcrumbList+FAQPage).
- **`/methodology`** — "Facts, Not Approval Predictions." Reinforces the differentiator.
- **`/pricing`** — **Pro tier is live: Free $0 / Pro $29.** Reads on-brand ("the calm, sourced biotech-catalyst tape").

---

## 👥 Usability

**Good (verified on live mobile + desktop):**
- Homepage hero is sharp and differentiated: **"The biotech FDA-catalyst tape. Facts, not advice."** Subcopy names the actual value (live price/options, run-up history, cohort base rates, registry monitoring, source-verified archive).
- **Mobile is clean** — the old hero-card P0 is gone. Cards are scannable: countdown (1 DAY) · ticker · cap badge (Micro/Mid/Large) · drug · PDUFA date · "±% cohort." Good spacing/legibility on a 390px viewport.
- Homepage now cross-links the new surfaces (Decisions Archive / Methodology / Research cards) — better internal discovery.

**Fix:**
- ⚠️ **"±7% cohort" is unlabeled.** To a retail novice it's ambiguous (and risks reading like a return forecast — the one thing you don't want). Add a tap/tooltip: *"typical pre-decision run-up for this market-cap cohort — not a prediction."*
- ⚠️ **Homepage = ~7,189 words under a single `<h2>`.** Thin heading hierarchy hurts a11y and on-page SEO. Section the long scroll with real H2s.
- ⚠️ **`/devices` is thin (570 words, no schema)** — looks half-finished. Enrich or `noindex` until it's real; a thin page in the index dilutes quality signals.
- ⚠️ **`/readouts` = 7,716 words, ~17 internal links, no schema, and rows still have no on-site detail page** — equity leaks to ClinicalTrials.gov and you miss an `ItemList` rich result. The `/readout/[id]` gap persists.

---

## 🛡️ Competitive moat

**Widening (genuinely):** the push moves you from "a calendar" to "the source-verified FDA *outcome* database." A CRL-reasons archive + per-decision pages + a devices vertical + original research (success-rates, approval-rate) is a different, more defensible position than BioPharmCatalyst / BPIQ / CatalystAlert, who are calendars. The **CRL-with-reasons** archive in particular is rare and is exactly what institutions value. The **"facts, not odds"** stance is a brand moat against the AI-percent crowd — and against your own old ODIN ghosts.

**The moat risk isn't a competitor — it's discovery.** A moat nobody can find isn't compounding:
- None of this is indexed (see headline), so it earns no search traffic and no topical authority.
- Still **zero backlinks** (the pass10a digital-PR kit is un-actioned), so neither authority nor crawl-discovery is being primed.
- Net: the product is pulling ahead while its visibility goes backward. Fixing indexing + starting the backlink push is what converts the moat into traffic.

---

## 🔧 SEO — technical (new pages)
| Item | Status |
|---|---|
| BreadcrumbList/FAQPage on new content pages · Event on per-event | ✅ |
| `/decisions` hub (356 internal links — strong crawl path *once indexed*) | ✅ |
| `/devices`, `/readouts`, `/pricing` JSON-LD | ❌ none — add `ItemList` (devices/readouts), `Product`+`Offer`+`FAQ` (pricing) |
| Homepage heading hierarchy (1× H2 / 7k words) | ⚠️ add section H2s |
| Homepage `SearchAction` · `/coverage` `Dataset` schema | ❌ still open from Pass 14 |
| `/pricing` vs `/pricing.html` canonical | ❌ duplicate |

---

## 🎯 Do-next (delta this pass — full list in the tracker)
1. 🔴 **Fix indexing (builder)** — consolidate to ONE host: both apex+www serve 200 today, so **301-redirect www → apex** (apex is already the canonical everywhere), make internal links root-relative, drop the stale 35-page www sitemap, 410 the 3 ghosts, dedupe `/pricing.html`. *Then* re-submit + request-index. Full spec in ticket **`pass19b`**. (GSC ghost removals already done.) Note: low indexing is also partly discovery-lag + zero backlinks, not only config.
2. ⚠️ Add schema to `/devices`, `/readouts`, `/pricing`; section the homepage with H2s.
3. ⚠️ Label the "±% cohort" figure; enrich or `noindex` `/devices`.
4. ⚠️ Build `/readout/[id]` pages (stop leaking readout equity to CT.gov).
5. ▶️ Start the digital-PR/backlink push (kit `pass10a`) — now compounded by the new research pages, which are linkable assets.

## Net
The builder's content is good and the product moat is widening — but **Google still indexes only 11 pages and still ranks the discontinued ODIN product (with forbidden "93.6% approval" snippets) ahead of the real site.** The highest-leverage work on the board is no longer "make more pages" — it's **get the existing pages indexed and kill the ghosts.** Until then, every new page ships into the void.

*— Red Team Pass 19 (usability · moat · SEO · indexing).*
