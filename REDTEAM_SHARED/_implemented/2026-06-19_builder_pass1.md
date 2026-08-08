# BUILDER — implemented from Red Team Pass 1 (2026-06-19)

Shipped & live. Do **not** re-flag these.

## P0
- **#1 LOA tile removed (advice-risk closed).** The `LOA 87%` numeric tile is GONE from the web dashboard tape card (`.tfacts`) — replaced with a neutral **avg-daily-volume** tile. Cohort approval rate now appears **only** inside the collapsed "Base-rate context," relabeled **"Cohort approval rate (history)"** (web + app).
- **#4 Contrast + zoom.** Card-context muted color bumped for AA: dashboard `--mut2 #7e95b6 → #9bb0d0`; app + SEO pages `#7890b3 → #94a9c9`. Confirmed `user-scalable=no` is NOT present in the live app (the LAYOUT_AUDIT doc was stale; pinch-zoom works).

## P1
- **#6 /learn hub shipped** with 4 sourced explainers: **/learn/what-is-a-pdufa-date** (flagship), **/learn/what-is-a-crl**, **/learn/fda-advisory-committee-adcom**, **/learn/priority-review-vs-standard-review** (FAQ + Breadcrumb schema). Added **"Learn"** to the global nav and internal-linked the flagship + approvals-by-year from every per-event page.
- **#7 Calendar de-cluttered.** Partner tickers now **co-listed once** ("GSK / SPRO · Tebipenem…"); **word-boundary truncation** (no more mid-word cuts); the 2026-12-31 placeholder pile now renders as **"Q4 2026 (est.)"**.
- **#8 Approvals published + archive split.** `/decisions` is now a 3-way split: **/decisions/approvals** (236 pages) + **/decisions/crl** (102) + combined `/decisions`. Was CRL-only (20). Unverified outcomes are honestly labeled **"price-only"** (not "source-verified"). Sitemap grew 112 → **437 URLs**.
- **#M2 App chip priority reordered:** Outcome → **CASH<6mo → REG SLIP** → IV CRUSH → Vol rich/low → ±exp move (material company risk now out-ranks premium context).
- Softened the per-event dead-end CTA wording (kept the gate; added /learn + approval-rate internal links above it).

## Deferred / needs a decision (still open for you to push on)
- **#2 "Kill coming soon" + free look-inside** — CONFLICT: the owner explicitly chose a gated "coming soon" teaser. Not changed unilaterally; owner is deciding whether to open a free preview. Re-argue it if you think it's worth overriding.
- **#3 `title=` → tap/click popovers** across the gated app (mobile caveats) — not yet; bigger refactor.
- **#5 Email/alert capture** on per-event pages — needs a backend/service decision; only softened copy + added internal links so far.
- **#9 Today/Historic segmented control + "Filters ▾" drawer** — not yet.
- **#10 "What changed since last visit" + alerts/watchlist-notify spine** — not yet (the retention spine; needs infra).
- Also open: W6 "Live→Snapshot" wording, W8 sort options, M1 demote/rename High-visibility, M3 promote "Sourced" chip, M4 Calendar/Alerts tab rethink, M7 onboarding coachmark, M8 detail-sheet "Context" block (AdCom/earnings/conference — waiting on the crawler data), `/sources` page + CSV/API, dynamic per-event OG images.

_Re-audit anytime; I'll keep logging here._

---
## Pass 1b (same day, after owner approved "free look-inside")
- **#2 Free "look inside" — SHIPPED.** The public landing now shows a real, above-the-fold **preview tape** of the 12 soonest upcoming FDA decisions (T-minus pill, ticker, cap, drug, PDUFA date, cohort move), each row linking to its free public `/pdufa/<slug>` page + "see the whole calendar / recent approvals." Gate still in place for the full live `/today` + `/app` (owner: paywall stays closed until launch). **SEO title fixed** (dropped "(coming soon)" → keyword title); hero chip reworded "Live · private beta."
- **#9 Today/Historic segmented control — SHIPPED.** The two view toggles are now a filled gold segmented control with a "View" label + divider, visually separated from the filter chips (was camouflaged among ~15 chips).
- **#3/W4/M3 Tap-popovers — SHIPPED (web).** All 13 `title=` caveats on the web dashboard (LOA-context, Vol, Sourced, slip, ⓘ) now open as tap/click popovers — reachable on mobile-web + keyboard, not just desktop hover. (The app has 0 `title=` — its caveats are inline/`<details>`, so nothing to convert there.)

Still open: email/alert capture (#5, needs backend), "what changed"/alerts spine (#10), W6 wording, W8 sort, M1 demote High-visibility, M7 coachmark, M8 Context block (waiting on crawler), CSV/API, dynamic OG images.

---
## Pass 1c (same day) — SEO content expansion
- **`/sources` page — SHIPPED.** Institutional-trust page: primary sources (FDA/SEC/CT.gov/FMP/ORATS), ~5×/day cadence, coverage + honest "price-only vs verified" labeling, "not affiliated with FDA / no per-drug probabilities." Closes red-team open item "/sources page."
- **`/research` hub + first data study — SHIPPED.** `/research/pdufa-stock-run-up-by-market-cap` is an **original-data** asset computed from our 694-PDUFA cohort: decision-day median |move| by cap (Micro 7.2% / Small 3.4% / Mid 2.4% / Large 1.0%, cleanly monotonic) + T-120 run-up by cap. Each bar shows **n=** (150/131/101/312) and an **honest caveat** that run-up is non-monotonic (Mid>Small) — leaning into the provenance wedge instead of hiding the messy result. Dataset JSON-LD + Breadcrumb schema. This is a linkable/citeable asset for the #1 (programmatic) + #2 (honest-provenance) plays.
- **3 more `/learn` explainers — SHIPPED.** `what-happens-to-a-stock-on-a-pdufa-date` (uses cohort base rates, high commercial intent), `accelerated-approval-explained`, `pdufa-vs-bsufa-vs-gdufa`. `/learn` hub now lists 7; all carry FAQPage + Breadcrumb schema. "Research" added to global nav.
- Site is now **443 indexable pages** (was 437). All facts-only; FDA-disclaimer + not-investment-advice footer on every page; noindex still scoped only to /today + /app + /api.
- **Deploy:** built + verified locally in `pdufa_staging`; not yet pushed (owner pushes via new `deploy_site.bat`, or it folds into the crawler redeploy).

Still open: email/alert capture (#5, needs backend), "what changed"/alerts spine (#10), W6 wording, W8 sort, M1 demote High-visibility, M7 coachmark, M8 Context block (waiting on crawler), CSV/API export, dynamic per-event OG images.

---
## Pass 2 + 2b implemented (2026-06-19, same day)
Verified your Pass-2 findings myself before acting; here's what shipped:
- **§D (2b) per-drug `loa`/`pop` in `/api/data` — FIXED (guardrail).** You were right: GSK (Large) and SPRO (Micro) both carried `loa`/`pop` 87.58 = same drug → per-drug PoA, not a cap cohort. Renaming to `cohort_loa` would've been a lie, so I **stripped both fields entirely** (37 instances) from the embedded snapshot AND added a destructure guard (`({loa,pop,...c})`) so the handler can never re-emit them. UI consumed neither. The legit cohort move-by-cap (`hist`) stays.
- **§0b "Coming soon" meta/OG/Twitter — FIXED.** Title was already clean; `meta description`, `og:title/description`, `twitter:title/description` all said "Coming soon" → rewritten keyword-rich, no "coming soon" anywhere. (Verified live via cache-bust.)
- **§2b archive overclaim — FIXED.** "Past approvals & CRLs with the reason and a primary-source link" → "Past **CRLs** with the reason and a primary-source link; **approvals** are source-linked as we verify them." Explore tile reconciled too.
- **§2a thin 236 approval pages — FIXED (noindex, not enrich).** Historic file has **0/694** drug/indication (that data comes from the crawler), so enrich wasn't possible yet. Instead: the **318 thin pages (236 approvals + 82 unverified CRLs) are now `noindex,follow` and pulled from the sitemap**; only the **20 source-verified CRLs stay indexed**. Empty "Note —" row now hidden. Sitemap **443 → 125**. Will flip back to indexed + enriched once the crawler lands drug/indication.
- **§2c/2d — FIXED.** Tape now **self-updates client-side** from each row's embedded date (fixes "1days"→"1 day", marks "today", hides passed rows — so it never goes stale). Every `/learn` page gets a **Related** cross-link block (4 sibling explainers + calendar + decisions).
- **§0 stale CDN — ROOT-CAUSED + MITIGATED.** Confirmed real: bare `/` and `/calendar` were pinned to old edge entries (cached with a long `s-maxage` from a prior config); new deploys don't evict them. Added **`Cache-Control: max-age=0, s-maxage=300, stale-while-revalidate=600`** on all 16 HTML route patterns → prevents recurrence + bounds self-heal. `/` already healed live (saw new headers + fresh body, `x-vercel-cache: HIT`); `/calendar` self-heals as its old TTL lapses. Couldn't force an instant CDN purge (no purge tool in the Vercel MCP); not launch-blocking since the paywall is still closed.
- **§A (2b) old `pdufa-bio` project still owns the apex — OWNER ACTION (can't do via MCP).** Confirmed 3 projects (`pdufa-bio-staging` live, `pdufa-bio` old Next.js per-drug, `odin`). The MCP can't detach a domain. Owner must remove `pdufa.bio` + `www.pdufa.bio` from the OLD `pdufa-bio` project's Domains and noindex/delete its deployments, so a rollback/promote can never flip the apex to the per-drug-PoA product.

Deployed + verified (cache-bust) at ~22:40 UTC. Still open: §A owner action; email/alert capture (#5); #10 alerts spine; W6/W8/M1/M7/M8; CSV/API; dynamic OG images; cohort-cadence wording reconcile (10-min poll vs 5×/day crons — they DO exist in vercel.json, contra 2b).
