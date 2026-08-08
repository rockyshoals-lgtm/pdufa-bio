# Builder response to Red Team Pass 14 (cohort appeal + technical SEO) · 2026-06-26

## SHIPPED THIS PASS — live + verified on the apex (Chrome)
Technical-SEO teardown items 1-3 + 5 done **sitewide** via two idempotent post-processors
(`seo_pass14_fixups.py` + `seo_pass14b_generic.py`), deployed to production, verified live:

- **[P1] Per-event JSON-LD NO_TYPE — FIXED, and sitewide.** Root cause: pages shipped TWO bare-array
  `ld+json` blocks (the base `[BreadcrumbList,FAQPage]` + the Pass-13 `[BreadcrumbList,Event]`), so a
  parser reading the first block saw an array with no top-level `@type`, and there were two conflicting
  BreadcrumbLists. Fix: collapse to ONE `@graph` (BreadcrumbList + FAQPage + Event) per event. The same
  bare-array bug existed on the 338 `/fda-decision/*` pages and others — normalized them too.
  **Sitewide scan after: 699 pages, 0 bare-array / 0 parse-error / 0 NO_TYPE.** UNCY live = `@graph[BreadcrumbList+FAQPage+Event]`.
- **[P1] Titles ≤60, keyword-front-loaded — sitewide.** Was 205 pages >60. Now 0. e.g. UNCY 83→46
  ("UNCY PDUFA date — OLC, Jun 29 2026 | pdufa.bio"); home 99→60; coverage 84→37.
- **[P1] Meta descriptions ≤155 — sitewide.** Was 251 pages >155. Now 0.
- **[P1] Missing structured data:** `/coverage` now carries **Dataset** schema (creator, CC-BY-4.0,
  temporalCoverage 2024/2026); month pages now carry **ItemList + BreadcrumbList** (parity with conditions).
- **[carry-over, confirmed LIVE] Per-event bidirectional hub links + story depth** (Pass-13) are live:
  UNCY links to `/calendar/2026/june` and a condition page + has the CRL/cash story block.
- **Durability:** wired both post-processors into `run_crawler_full.sh` + `.bat` as the final SEO step,
  so a future crawl→rebuild re-applies them.

## SECURITY P0 — already closed (audit note was stale)
The Pass-14 reminder says `/api/data` is still public. It is **not** — gating was activated earlier this
session. Verified live this pass with a **cookie-less** fetch: `pro_gating:true, pro:false, no opt` (scraper
gets calendar facts only; the gated app still gets full Pro data). The audit ran before activation.

## CONSCIOUSLY SKIPPED (with reasons — need a decision)
- **SearchAction (item 5):** Pass-13 *correctly removed* it because there's no working search endpoint.
  Adding a sitelinks SearchAction that points at a URL which doesn't actually search is worse than omitting
  (Google sends users to a page that ignores the query). **Need a real `/search` or `/calendar?q=` filter
  first**, then it's a 1-line add. Flagging the Pass-13 vs Pass-14 conflict for your call.
- **Condition mis-categorization (noticed, not an audit item):** UNCY (a kidney/phosphate drug) links to
  `/condition/obesity-metabolic` because there's no nephrology/renal bucket. Recommend either adding a
  `/condition/renal-nephrology` page or dropping the condition pill for unmapped indications.

## NOT DONE — bigger builds (owner-decision or multi-session); recommended order
1. **[P1] Crawler 46% PDUFA recall + 268 missing drug names.** Biggest SEO *and* institutional win
   (every recovered PDUFA = a new indexable `/pdufa/` page). This is crawler work (task #42), a dedicated build.
2. **[P1] On-site `/readout/[id]` pages.** Biggest remaining internal-link leak (~27/31 off-site to CT.gov).
3. **[P1] Funnel CTAs** — each needs a decision before I build:
   - Retail **email/alert capture**: pick a provider (Formspree / ConvertKit / Vercel KV + a function). Then I wire it on every per-event + a weekly digest.
   - Trader **public teaser** (implied-move line + blurred run-up): I can surface the options-implied move publicly per event.
   - Institution **API docs + "request access" CTA + Enterprise tier**: the data is already public via `/api/data`, so this is mostly packaging + a contact path + a pricing decision.
4. **[P1] Per-event chart refresh** (static SVG dated 2026-06-19) — needs a price-data regen pass.
5. **[P2] New surfaces:** `/this-week`, AdCom calendar, `/calendar/2027`, homepage H2s + browse-footer mesh, dynamic OG images.
6. **[owner] GSC Removals** on the old ODIN ghost URLs (Search Console action).

**Bottom line:** the quick, sitewide, high-value SEO items (broken schema + long titles/metas + coverage
Dataset + month ItemList) are shipped and verified; the security P0 is confirmed closed. The remaining work
is the 46% recall gap, on-site readout pages, and a real conversion CTA per cohort — the last of which needs
your pick on an email provider + Enterprise pricing before I build it.

*— Builder, Pass 14.*
