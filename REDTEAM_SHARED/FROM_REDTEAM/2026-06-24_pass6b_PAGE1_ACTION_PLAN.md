# pdufa.bio — PAGE-1 ACTION PLAN (for the builder) · 2026-06-24

**Goal:** get pdufa.bio onto Google page 1 for its core terms. This is an implementation checklist — each item is concrete enough to build without a follow-up. Verified live via Chrome (real SERPs + `site:pdufa.bio` index).

## THE UNLOCK (read first)
pdufa.bio is **not on page 1** for "PDUFA calendar 2026," "what is a PDUFA date," or "UNCY PDUFA date." The reason is now pinpointed: **Google's index is stale and still contains the OLD ODIN per-drug-probability product.** `site:pdufa.bio` returns the old Hávamál homepage, an old **"Pricing: Free to Elite,"** **"ODIN Engine – FDA Probability Scoring,"** **"PDUFA Calendar … with ODIN AI approval probability scores,"** **"VNDA … ODIN predicted 89.7% TIER_1 approval probability,"** an **"ODIN Track Record – 53 Verified Predictions,"** a **"PDUFA Runup Heatmap,"** all with `4.8★(47)` review rich-results. Only `/calendar` shows as freshly crawled.

The live pages are the new facts product (verified: `/pricing` is now "never fake an approval probability," Free/$29 Pro). **So the live site is correct — Google just hasn't re-crawled, and is ranking/representing the old ODIN tool.** This is simultaneously an **SEO identity crisis** and a **guardrail/brand exposure** (Google is serving "ODIN predicted 89.7% approval probability" snippets under your name). **Fixing the index is the #1 page-1 lever.** Do Workstream A first.

---

## WORKSTREAM A — Fix the index (highest leverage; do first)

**A1. Detach the old project from the domain (owner action — still not done, §A from Pass 2b).**
Remove `pdufa.bio` + `www.pdufa.bio` from the OLD `pdufa-bio` Vercel project's Domains; pause/delete its deployments. Until this is done, a re-crawl or rollback can serve old ODIN content on the apex. *Acceptance: only `pdufa-bio-staging` holds the domain.*

**A2. Inventory + redirect/kill every old URL.** For each old-product URL still in the index, do one of:
- **301** to the new equivalent if one exists (e.g., old `/pricing` → new `/pricing`; old VNDA-ODIN page → `/fda-decision/VNDA-2026-02-20` or `/pdufa/VNDA`; old calendar → `/calendar`).
- **410 Gone** if there is no equivalent (e.g., `/odin`, ODIN-engine/score pages, `/track-record`, the runup-heatmap, any "ODIN approval probability" page). 410 makes Google drop them fast.
- **Strip old `Review`/`AggregateRating` schema** (the `4.8★(47)`) sitewide — it's from the old product and is false on the new pages.
*Acceptance: every old ODIN/pricing-tier/track-record/heatmap URL 301s or 410s; no `AggregateRating` in the new markup.*

**A3. Google Search Console push (owner + builder).**
- Verify GSC for **both** `https://www.pdufa.bio` and `https://pdufa.bio` (or a Domain property covering both).
- Submit the **fresh sitemap**; confirm it lists the new pages (not the old).
- **Request Indexing** (URL Inspection) on the priority set: `/`, `/calendar`, `/learn/what-is-a-pdufa-date`, `/decisions/approvals`, `/research/pdufa-stock-run-up-by-market-cap`, `/pricing`, top 10 `/pdufa/[ticker]` pages.
- Use **Removals** to fast-purge the worst stale PoA URLs (the ODIN-probability and VNDA-89.7% pages) so they stop representing the brand.
*Acceptance: `site:pdufa.bio` shows new titles (no "ODIN approval probability") within ~2–3 weeks.*

**A4. Pick ONE canonical host + fix the cookie.**
Choose `www` (recommended, it's what's serving) or apex; 301 the other consistently; self-referencing `<link rel=canonical>` on every page to the chosen host; scope the gate cookie `Domain=.pdufa.bio` so the unlock spans apex+www (fixes the logout-on-redirect bug). *Acceptance: no apex↔www flip-flop; one host in GSC; unlock persists across both.*

---

## WORKSTREAM B — Structural pages (winnable long-tail; do second)

**B1. Month-archive pages — the top structural move (CatalystAlert already ranks with these).**
Build server-rendered `/calendar/2026/[month]` and `/readouts/2026/[month]`, Jan–Dec, with prev/next month nav and a count.
- **Title:** `[Month] 2026 PDUFA Dates — FDA Decisions That Month | pdufa.bio`
- **H1:** `[Month] 2026 PDUFA Dates`
- **Body:** the month's events (server-rendered, linked to `/pdufa/[ticker]`), an 80-word "About PDUFA dates in [Month] 2026" blurb, and an FAQ.
- **Schema:** `ItemList` + `FAQPage` + `BreadcrumbList`.
- **Internal-link** each month header on `/calendar` → its month page; cross-link prev/next.
- *Doubles as the retail month-picker.* *Acceptance: 24 indexable month pages; linked from /calendar; in sitemap.*

**B2. Condition / vertical pages (proof: CheckRare ranks #3 for the head term with an orphan-drug page).**
Build `/condition/[slug]` for high-volume verticals: `obesity-weight-loss`, `alzheimers`, `oncology`, `rare-disease-orphan`, `nash-mash`, `cns-neuro`, `cardiometabolic`.
- **Title:** `Upcoming FDA Decisions in [Condition] — 2026 PDUFA Dates | pdufa.bio`
- **H1:** `Upcoming [Condition] FDA Decisions (2026)`
- **Body:** filtered events + a sourced explainer of why this area matters + FAQ; `ItemList`+`FAQPage` schema.
- *Also ships the retail "condition lens" (the most retail-native feature you're missing).* *Acceptance: 6–8 condition pages, linked from calendar + a "Browse by condition" nav/section.*

**B3. Re-expand the sitemap as the crawler enriches per-event pages.**
The 318 thin approval/CRL pages were `noindex`'d (sitemap 443→125). Once the crawler lands drug+indication, flip them back to `index` and re-add to the sitemap — but only when each has unique drug+indication+context (no thin pages). *Acceptance: sitemap climbs back toward 443 with enriched, indexable pages.*

---

## WORKSTREAM C — Per-event page depth (win the long tail + serve retail; do third)

The reason `/pdufa/UNCY` loses to the company PR / Seeking Alpha / Reddit: it's thin and stale. Upgrade `/pdufa/[ticker]`:

**C1. Add a sourced "The story" block** — 3–5 sentences: what the drug does in plain English, the indication precisely (UNCY = "high blood phosphate in dialysis patients," not "Kidney disease"), the regulatory history (**UNCY had a June-2025 CRL; this is the resubmission** — that's the whole thesis and it's currently missing), and cash-runway. *This is what beats a press release.*
**C2. Fix freshness** — the chart says "Price path to 2026-06-19" (~6 days stale). Rebuild per-event charts with current data on each refresh/deploy.
**C3. Related-event internal links** — "Other [condition] PDUFAs," "Other [cap-tier] decisions this month," "[TICKER] prior FDA history." (Feeds B1/B2 + engagement.)
**C4. Email / "notify me before this date" capture** — kills the gated dead-end CTA, adds the engagement/return signals Google rewards, and seeds the weekly digest the new /pricing already promises.
**C5. Schema + OG** — add `Event` (the PDUFA date) + `FAQPage` + `BreadcrumbList`; generate a dynamic OG image (ticker + date + run-up sparkline) for shareable unfurls. *Acceptance: each per-event page has the story block, fresh chart, ≥3 internal links, an email field, Event/FAQ schema, dynamic OG.*

---

## WORKSTREAM D — Off-page authority (owner/marketing — the real ranking driver; ongoing, start now)

On-page is done; **placement needs backlinks**, which haven't been started. Builder can prep the assets; owner does outreach.
- **D1. Digital PR around `/research`.** The run-up-by-cap study (with honest n + non-monotonic caveat) is genuine link-bait. Pitch it to: Endpoints News, FierceBiotech, STAT, BioPharma Dive, Seeking Alpha biotech contributors, r/biotechstocks / r/biotech, biotech Substacks (e.g., "Biotech Scholar"-type), and "best FDA calendar tool" roundup authors. Goal: get the dataset *cited with a link*.
- **D2. Directory + roundup placements.** Get listed on biotech-tool roundups and comparison pages (where BioPharmCatalyst/BPIQ appear). These are durable referral + ranking links.
- **D3. Recurring data posts = recurring links + freshness.** Ship a monthly `/research/[month]-2026-pdufa-recap` ("This month's FDA decisions, by the numbers") — pairs with B1 month pages, gives journalists a reason to cite, and feeds freshness signals.
- **D4. Claim the brand SERP.** Ensure the homepage + a short "About / who's behind this" page rank for "pdufa.bio" so a stale ODIN page never represents the brand.

---

## Sequencing (fastest path to page-1 movement)
1. **Week 1:** A1 (detach domain) + A2 (redirect/kill old URLs, strip review schema) + A3 (GSC submit + request-index + remove worst ODIN URLs) + A4 (canonical host). *This stops the old ODIN product from being your Google identity — biggest single unlock.*
2. **Week 1–2:** B1 (month pages) + B3 (re-index enriched pages). *Winnable long-tail + retail month-picker.*
3. **Week 2–3:** C1–C5 (per-event depth) + B2 (condition pages). *Win the long tail + retail clarity.*
4. **Ongoing from Week 1:** D1–D4 (backlinks/PR). *The only thing that cracks the competitive head terms long-term.*

## How we'll know it worked (re-audit checks)
- `site:pdufa.bio` shows the **new** pages (no "ODIN approval probability," no `4.8★`).
- pdufa.bio appears for **month + condition + `[ticker] PDUFA date`** long-tail first (the winnable set), then climbs "PDUFA calendar 2026" as backlinks accrue.
- GSC shows rising impressions/clicks on the new URLs and dropping on the old.

**Bottom line for the builder:** the product is good and the on-page SEO is good — you are not ranking because **Google still has the old ODIN product indexed** and you have **no structural long-tail pages, thin per-event pages, and zero backlinks.** Fix the index (A), ship month+condition pages (B), deepen per-event (C), and start PR (D). A is the unlock; do it this week.

*— Red Team Pass 6b (page-1 action plan; live SERP + index audit via connected Chrome).*
