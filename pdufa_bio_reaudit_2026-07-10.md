# pdufa.bio — Re-Audit (post-build verification)
**Date:** 2026-07-10 · **Method:** live browser re-inspection + raw-HTML fetch + SERP re-tests
**Baseline:** `pdufa_bio_competitive_audit_2026-07-10.md` + `pdufa_bio_builder_tickets.md`
Product-strategy use only; not investment advice.

---

## TL;DR — the builder shipped the core, and it's already paying off

**The headline win:** pdufa.bio now **ranks on page 1 of Google for the non-branded head term "PDUFA calendar 2026"** (`/pdufa-calendar`, ~position 8, alongside BiopharmaWatch, FDA Tracker, BPIQ, MarketBeat, RTTNews). At the last audit it was **absent from every head-term SERP.** That is the single most important change — the on-page work is now converting to visibility.

**All six quick wins are effectively done; two of the six big bets shipped.** The self-inflicted 404s are gone, the detail pages exist, the readouts feed is de-noised, hub pages carry schema, pricing matches the brief ($10/$100), and **Conferences + AdComm are live** — so the "three-in-one calendar" is now literally true (PDUFA + readouts + conferences), plus a bonus AdComm calendar.

**But three concrete issues remain or were newly introduced** — all cheap to fix, and one is a brand-risk: (1) a **canonical/host mess** made slightly worse by a duplicate `/pdufa-calendar` page; (2) the **sitemap was never regenerated** (still non-www, still 170 URLs, missing the new pages); (3) Google's **cached listing still advertises "ODIN Scores / approval probability"** for pdufa.bio — off-brand and contradicting the "no approval %" positioning, even though the live page is clean.

---

## Ticket-by-ticket verification

| Ticket | Status | Evidence (verified live 2026-07-10) |
|---|---|---|
| **Q1** — Fix broken `/pdufa/{TICKER}` links | ✅ **DONE** | Crawled all 49 homepage internal links: **0 return 4xx** (was: CORT/OTLK/VTRS 404). |
| **Q2** — Generate missing detail pages | ✅ **DONE** | `/pdufa/CORT` → 200, `/pdufa/OTLK` → 200, `/pdufa/VTRS` → 200 (all were 404). |
| **Q3** — Schema + meta on hub pages | ✅ **DONE** | `/calendar` → `ItemList`+`BreadcrumbList`; `/readouts` → `ItemList`; `/conferences` → `ItemList`; `/adcomm` → `ItemList`. All now have meta descriptions (was: `/readouts` had none). *Minor: homepage still `WebSite`-only — optional to add `ItemList` to the "next decisions" block.* |
| **Q4** — www canonical + sitemap host | ⚠️ **PARTIAL** | Homepage canonical is www ✅ — **but** `/calendar` self-canonicalizes to **non-www** (`https://pdufa.bio/calendar`) while `/pdufa-calendar` canonicalizes to **www**. Sitemap still emits **non-www** URLs. Host signals still inconsistent. |
| **Q5** — Lock pricing | ✅ **DONE** | Pricing page now reads **$100/yr or $10/mo** — matches the brief (was $15/$120). Free tier unchanged and still genuinely open. |
| **Q6** — Sanity-filter readouts | ✅ **DONE** | The four flagged bad rows are **gone**: "Vaping Cessation," "Poliomyelitis," "SBI-100…Obesity," "Custirsen" all absent from `/readouts`. |
| **B1** — Conference calendar | ✅ **SHIPPED** | `/conferences` → 200, in nav. Title "2026 Biotech Conference Calendar — ASCO, ESMO, ASH & more." Real events w/ dates, location, TA, presenter counts (ESMO Oct 23–27 Madrid ✓, ESC Aug 28–31 Munich ✓). `ItemList` schema. Clean on-brand UI. |
| **B2** — AdComm calendar | ✅ **SHIPPED** | `/adcomm` → 200, in nav. Title "2026 FDA AdComm Calendar — Advisory Committee Meeting Dates." Federal-Register-sourced, `ItemList` schema. *Thin (2 meetings), but that's inherent — AdComms are announced ~4–6 weeks out.* |
| **B3** — Readouts confidence/staleness grade | ❌ **NOT DONE** | No confidence grade, no per-row staleness/last-updated flag. Still raw "estimated primary-completion windows." (Bad rows removed, but no grading — TheraRadar still ahead here.) |
| **B4** — Unified cross-event filter bar | ❌ **NOT DONE** | No filter/search controls found on `/calendar` (no ticker/TA/phase/type/date-range filter). |
| **B5** — Backlink engine off run-up study | ➖ **UNVERIFIABLE** | Can't confirm off-site outreach from here; recommend the owner confirm. |
| **B6** — Public data API | ❌ **NOT DONE** | `/api`, `/api/v1/pdufa` → 404. |

**Scorecard delta:** on the core dimensions, pdufa.bio moves up on **SEO (3 → 4)** — it now ranks for the head term, ships hub-page schema, and has closed the coverage gap with conferences + AdComm. UX/UI/Value are unchanged (UI still the cleanest in the set; UX still lacks the unified filter). New estimated total: **~15–16/20**, now at parity with BPIQ/TheraRadar and ahead of FDA Tracker and RTTNews.

---

## New / remaining issues (all cheap, ranked)

### 1. 🔴 Canonical + duplicate-page mess *(highest priority — actively confuses Google)*
- The builder added a **second page, `/pdufa-calendar`, that duplicates `/calendar`** — identical `<title>` ("2026 FDA PDUFA Calendar | pdufa.bio") and H1.
- Their canonicals **disagree on host**: `/calendar` → `https://pdufa.bio/calendar` (**non-www**); `/pdufa-calendar` → `https://www.pdufa.bio/calendar` (**www**). The site *serves* www.
- **Net effect:** Google gets conflicting canonical hosts and two URLs for the same term (keyword cannibalization).
- **Fix:** Pick **www** everywhere. Make `/calendar` self-canonical to `https://www.pdufa.bio/calendar`; keep `/pdufa-calendar` canonicalized to `/calendar` (that part is correct); make every canonical tag + sitemap URL use www.
- **Done when:** every page's canonical uses www and there's exactly one canonical target per unique page.

### 2. 🔴 Sitemap not regenerated *(the new pages can't be discovered)*
- `sitemap.xml` is unchanged: **still 170 URLs, still non-www**, and contains **no `/conferences`, no `/adcomm`, no `/pdufa-calendar`** entries.
- The new pages exist but aren't in the sitemap — so crawlers may take longer to find/rank them.
- **Fix:** Regenerate the sitemap (www host) to include conferences, conference detail pages, adcomm, and any new PDUFA detail pages. Resubmit in Search Console.
- **Done when:** sitemap host = www, and includes every live hub + detail page.

### 3. 🟠 Stale, off-brand "ODIN Scores" title in Google's index *(brand + compliance risk)*
- Google's live SERP listing for `/pdufa-calendar` still reads **"PDUFA Calendar 2026: Upcoming FDA Drug Approval Dates & ODIN Scores | PDUFA.BIO,"** and search summaries repeat "scored by ODIN AI, 93.6% accuracy, approval probability."
- **The live page is clean** — I fetched the raw HTML: current title is "2026 FDA PDUFA Calendar | pdufa.bio," no ODIN/approval-probability in title or meta, the footer still says "no individual-drug approval probabilities," and `/why-no-approval-probability` is intact. So this is a **stale cached entry** from a prior version that briefly carried ODIN branding.
- **Why it matters:** the entire differentiation thesis is "facts, not approval odds." A Google listing advertising "ODIN approval-probability scores" undercuts that and flirts with an approval-claim/"not investment advice" tension.
- **Fix:** Confirm no ODIN/approval-probability strings remain anywhere in public metadata (they currently don't), then request re-indexing of `/pdufa-calendar` in Search Console to flush the cached title. Add a guard so internal model language (ODIN) can never leak into public `<title>`/meta.
- **Done when:** the SERP title matches the clean live title.

### 4. 🟡 Still open from the big-bet list (schedule, not urgent)
- **B3** readouts confidence/staleness grading — the one place TheraRadar still beats pdufa.bio on the readouts calendar.
- **B4** unified cross-event filter — now more valuable since there are 3 event types + AdComm to filter across.
- **B6** public API.
- **B5** backlink engine — confirm it's running; it's the durable lever for holding the new rankings.
- **AdComm depth** — only 2 meetings; keep the Federal Register ingest current so it fills in.
- **Mobile QA** — still not visually confirmed on a real phone (flagged last audit).

---

## Bottom line

The builder executed the "stop the bleeding + complete the coverage" half of the plan cleanly, and it produced the intended result: **pdufa.bio is now visible on page 1 for its head term for the first time, with a genuinely complete three-in-one calendar and the cleanest UI in the category.** What's left is (a) a 30-minute canonical/sitemap cleanup that's currently throttling how fast the new pages rank, (b) flushing one off-brand cached Google title, and (c) the three optional big bets (readout grading, unified filter, API) that turn "ranks and complete" into "owns the category." The differentiation thesis — cleanest, most accurate, most complete, cheapest, no approval-odds — is now defensible on the live site; the priority is protecting it (canonical hygiene + kill the stale ODIN listing) and pressing the SEO advantage before BiopharmaWatch's authority reasserts.

---

## Sources (re-verified live 2026-07-10)
- pdufa.bio: `/`, `/calendar`, `/pdufa-calendar`, `/readouts`, `/conferences`, `/adcomm`, `/pricing`, `/why-no-approval-probability`, `/pdufa/CORT`, `/pdufa/OTLK`, `/pdufa/VTRS`, `/sitemap.xml` — https://www.pdufa.bio/
- SERP re-tests (Google, 2026-07-10): "PDUFA calendar 2026 upcoming FDA decision dates" (pdufa.bio `/pdufa-calendar` now page 1), "biotech conference calendar 2026," "pdufa.bio PDUFA calendar."
- Conference-date corroboration: ASCO/ESMO official calendars (ESMO Oct 23–27 Madrid; ESC Aug 28–31 Munich).
*Informational product-strategy analysis. Not investment advice.*
