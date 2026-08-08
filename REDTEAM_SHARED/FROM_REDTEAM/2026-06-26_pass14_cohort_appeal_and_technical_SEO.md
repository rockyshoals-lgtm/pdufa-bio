# pdufa.bio — Pass 14 · Cohort appeal + technical SEO (builder optimization detail) · 2026-06-26

Fresh live audit (Chrome). Part 1 = how the site appeals to / converts each cohort right now. Part 2 = a technical SEO teardown with concrete numbers and the exact fixes.

---

## PART 1 — Cohort appeal & conversion (live)

| Cohort | What's working | The gap | The #1 lift |
|---|---|---|---|
| **Retail** | Homepage "look inside" tape is calm + welcoming; calendar is clean; tone is hype-free (a real edge vs MarketBeat/CatalystAlert) | **No reason to come back** — there's still no email/alert capture anywhere, and the only CTA is the gated "private beta." A nervous beginner gets oriented, then leaves with no hook. | **Email / "notify me before this date" capture** on every per-event + a weekly "what's hitting" digest. This is the single biggest retail conversion + retention lever, and it's still missing. |
| **Active traders** | The gated app has the real depth (catalyst-scoped options, IV-crush, T-120 run-up, Silent-Shift) — genuinely unique | **The value is hidden behind the gate.** A trader landing from Google sees a thin public facts page, not the options/run-up depth (that's Pro). The funnel never shows them the goods. Plus still no AdCom dates / earnings-proximity / "Context" block. | **Surface a trader teaser publicly** (e.g., "options imply a bigger-than-usual move" line + a blurred run-up preview on the per-event page) so search traffic sees the edge → converts to Pro. Then add the AdCom/Context data. |
| **Institutions** | `/coverage` is **best-in-class** — coverage counts, 98% primary-source-linked, source breakdown, date-precision tags, explicit limitations, and radical honesty ("46% PDUFA recall," "dropped 268 no-drug-name rows"). `/methodology` + `/sources` + `/research` reinforce it. No competitor does this. | **No conversion path and a completeness gap.** API is "on the roadmap" (institutions want it now), there's **no Enterprise tier** on `/pricing`, no "request API access / contact" CTA on `/coverage`, and **only 46% of PDUFAs are captured.** | **Ship a documented read-only API + an Enterprise tier + a "request access" CTA on `/coverage`.** (Note: the data is already public via `/api/data` — so a documented free API + a gated Pro tier is mostly packaging.) And close the recall gap (Part 2). |

**The through-line:** all three cohorts hit the same wall — there's no *next step*. Retail can't subscribe to alerts, traders can't see the depth without the gate, institutions can't request the API. **Every cohort needs a low-friction CTA the site doesn't yet offer.** Fixing the funnel (capture + teaser + API request) is higher-leverage right now than any single feature.

---

## PART 2 — Technical SEO teardown (concrete, builder-actionable)

### Measured this pass
| Page | Title len | Meta desc len | Words | Schema | Verdict |
|---|---|---|---|---|---|
| `/` (home) | **95** ❌ | **190** ❌ | 613 | Organization + WebSite ✅ (no SearchAction) | titles/meta too long; only 1 H2 |
| `/pdufa/UNCY` | **83** ❌ | **232** ❌ | **420** (thin) | **NO_TYPE** ❌ (broken) | the big one — see below |
| `/coverage` | **75** ❌ | **213** ❌ | 385 | **none** ❌ | add Dataset schema |
| `/calendar/2026/september` | ok | — | — | FAQPage ✅ (no ItemList/Breadcrumb) | good |
| `/condition/obesity-metabolic` | ok | — | — | FAQPage + ItemList ✅ | good |
Load speed is fine (per-event TTFB ~300 ms, fully loaded <400 ms) — performance is not the problem.

### Fix list (highest leverage first)

**1. [P1] Fix the per-event JSON-LD — it's broken (`NO_TYPE`).** Every `/pdufa/[ticker]` page ships a `<script type="application/ld+json">` with **no `@type`**, so it provides **zero** rich-result value. The homepage's schema is fine (a proper `@graph`), so this is a per-event *template* bug. Emit valid schema, e.g. a `@graph` with **FAQPage + BreadcrumbList + Event** (the PDUFA date as an `Event`). Validate every template in Google's Rich Results Test before shipping.

**2. [P1] Shorten titles to ≤60 chars, keyword-front-loaded (sitewide).** Currently 75–95. Examples:
- Per-event: `UNCY PDUFA Date: Oxylanthanum Carbonate (OLC) — FDA Decision 2026-06-29 | pdufa.bio` (83) → **`UNCY PDUFA date — OLC, Jun 29 2026 | pdufa.bio`** (~46).
- Home: `pdufa.bio — the biotech FDA-catalyst tape: PDUFA dates, run-up history & verified FDA decisions` (95) → **`2026 FDA PDUFA Calendar — Dates & Run-up History | pdufa.bio`** (~58, leads with the keyword, not the brand).
- Coverage: → **`Data Coverage & Integrity | pdufa.bio`** (~37).

**3. [P1] Trim meta descriptions to ≤155 chars** (currently 190–232; they truncate). Per-event template example (~150): *"UNCY's FDA PDUFA date is Jun 29, 2026 for Oxylanthanum Carbonate (kidney disease). See the T-120 run-up, cap-tier base rates, and the primary source."*

**4. [P0-for-coverage] Close the 46% PDUFA recall gap.** `/coverage` admits the crawler catches **only ~46% of real PDUFAs** vs a reference set. That means **more than half your potential `/pdufa/[ticker]` pages — and the long-tail rankings + the per-event experience that go with them — don't exist.** Improving crawler recall is simultaneously the biggest **SEO expansion** (more indexable pages) and the biggest **institutional-completeness** win. Same for the **268 rows missing drug names** (backfill them).

**5. [P1] Add the missing structured data:**
- Homepage `WebSite` → add a **`SearchAction`** (`potentialAction`) to enable a Google sitelinks search box.
- `/coverage` → add **`Dataset`** schema (it's literally a dataset summary).
- Month pages → add **`ItemList` + `BreadcrumbList`** (they have FAQPage only; conditions already got ItemList — bring to parity).

**6. [P1] Per-event content depth + internal links (carry-over, still open).** 420 words is thin vs the press releases you're outranking-for. Add the sourced story block (CRL/cash/plain-English), and **bidirectional internal links**: each `/pdufa/[ticker]` should link to its `/condition/[disease]` and `/calendar/2026/[month]` (the hubs link in; the per-event page links back to neither). Refresh the per-event chart (still dated `2026-06-19`).

**7. [P1] Build on-site `/readout/[id]` pages.** Condition + `/readouts` rows still leak ~27/31 links off-site to ClinicalTrials.gov because no on-site readout pages exist. This is the single biggest remaining internal-link leak.

**8. [P1] Homepage → hub links + GSC Removals.** Homepage still doesn't link `/learn`, `/research`, `/readouts` (add them — especially `/research`). And the old ODIN ghost (`Runup Heatmap`, `ODIN Engine`, `VNDA 89.7%`, 4.8★) is still indexed — **GSC Removals** on those URLs.

**9. [P2] New surfaces (expansion):** `/this-week` (FDA decisions this week — recurring intent, always fresh), an **AdCom calendar**, `/calendar/2027`, and a sitewide browse-footer mesh (all conditions + months linked from every page).

**10. [P2] Homepage heading depth + dynamic OG images.** Only 1 H2 on the homepage — add 2–3 keyworded H2 sections. Ship per-page OG images (ticker + date + sparkline) for the share/PR play.

### Reminder — the security P0 is still open
`/api/data` is still public/un-authed (200, full dataset, no creds); `/api/data.js` still live. Gate it (or free/pro split) before charging for Pro. (pass 11/12/13.)

---

## Top of the stack
1. **[P0] Gate `/api/data`** (security).
2. **[P1] Fix per-event JSON-LD (`NO_TYPE`) + shorten all titles/metas** — easy, sitewide, high-value.
3. **[P1] Close the 46% PDUFA-recall gap + backfill 268 missing drug names** — biggest SEO *and* institutional win.
4. **[P1] Email/alert capture (retail), trader teaser (trader), API + Enterprise tier + request-CTA (institution)** — the funnel each cohort is missing.
5. **[P1] On-site `/readout/` pages + per-event depth/bidirectional links + homepage→hub links + GSC Removals.**
6. **[P2] `/this-week`, AdCom calendar, `/calendar/2027`, browse mesh, OG images, SearchAction/Dataset schema.**

**Verdict:** the site is *trustworthy and well-built* — the institutional trust layer (`/coverage`) is genuinely category-leading, and the SEO architecture is sound. The gains now are **(a) the broken per-event schema + long titles (quick, sitewide), (b) the 46% coverage gap (the page-count ceiling), and (c) a real conversion CTA for each cohort** (alerts / teaser / API). Do those and the foundation finally starts converting traffic into retail habit, Pro upgrades, and institutional leads.

*— Red Team Pass 14 (cohort appeal + technical SEO; live via Chrome).*
