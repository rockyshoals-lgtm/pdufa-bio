# pdufa.bio — Re-Audit #2 (delta since last check)
**Date:** 2026-07-10 · **Method:** live browser + raw-HTML fetch + SERP re-test
**Baseline:** `pdufa_bio_reaudit_2026-07-10.md`
Product-strategy use only; not investment advice.

---

## TL;DR
**One new thing shipped; the three flagged issues are all still open; one of the earlier "fixes" turns out to be skin-deep.**

- ✅ **New progress — readout staleness signals are live (partial B3).** The readouts calendar now shows **195 "Awaiting data" status tags** and **80 "updated Xmo ago"** freshness flags (e.g. "updated 4mo ago" … "updated 47mo ago"). This is the freshness half of the TheraRadar-grade upgrade and it's a real, visible improvement. (Confidence grading still absent.)
- ⚠️ **The three issues from last re-audit are unchanged** — canonical/host mess, un-regenerated sitemap, and the stale "ODIN Scores" Google listing. No movement on any.
- 🔴 **New finding — the readouts cleanup (Q6) is only client-side.** The server-rendered HTML still contains the erroneous rows in **visible markup**; JS strips them after load. Users see clean; crawlers don't.
- ✅ **All prior wins are holding** — no regressions.

---

## What changed since the last re-audit

| Item | Last re-audit | Now | Verdict |
|---|---|---|---|
| **B3 — readout confidence/staleness** | ❌ none | ⚠️ **Staleness shipped**: 195 "Awaiting data" + 80 "updated Xmo ago" flags rendered | **Partial win** — freshness live; confidence grade still missing |
| Canonical `/calendar` vs `/pdufa-calendar` | ❌ non-www vs www mismatch | ❌ **still** `/calendar`→`https://pdufa.bio/calendar` (non-www), `/pdufa-calendar`→www | **Unchanged — still open** |
| Sitemap | ❌ 170 URLs, non-www, missing new pages | ❌ **still** 170 URLs, non-www, no `/conferences` `/adcomm` `/pdufa-calendar` | **Unchanged — still open** |
| Stale "ODIN Scores" SERP title | ⚠️ cached | ⚠️ **still** showing "…& ODIN Scores \| PDUFA.BIO" in Google | **Unchanged — still open** |
| B4 — unified filter | ❌ | ❌ no filter controls on `/calendar` | **Still not done** |
| B6 — API | ❌ `/api` 404 | ❌ `/api/v1/pdufa` → 404 | **Still not done** |

## Wins still holding (no regressions)
- `/pdufa/CORT`, `/pdufa/OTLK` → **200**; `/conferences`, `/adcomm` → **200**.
- Pricing still **$10/mo · $100/yr** (rendered).
- SEO sustained: pdufa.bio `/pdufa-calendar` **still on page 1** for "PDUFA calendar 2026 upcoming FDA decision dates" (~position 8, with BiopharmaWatch/FDA Tracker/BPIQ/MarketBeat/RTTNews).
- Rendered readouts page is clean of the bad drug-indication pairs (for users).

---

## New finding — the readouts fix is cosmetic, not data-level 🔴

The Q6 "sanity-filter" removed the bad rows from what **users** see, but not from what **crawlers** see:

- **Raw server HTML** of `/readouts` still contains `Vaping Cessation`, `Custirsen`, and `Poliomyelitis` — and I confirmed the string sits in **visible markup**, not a hidden `<script>`/JSON blob.
- **Rendered DOM** (post-JS): those rows are stripped, so the on-screen list looks clean.
- **Implication:** the erroneous pairings (e.g. "ACHV Custirsen — Vaping Cessation") are still in the server-rendered HTML that Googlebot indexes on first fetch. The accuracy defect was hidden client-side, not corrected at the data source.
- **Fix:** clean the readouts at the **data layer** (correct or drop the bad ClinicalTrials.gov condition mappings before render) so the SSR HTML is also clean. A client-side filter is not enough for an accuracy-first product whose whole pitch is "most accurate."
- **Done when:** `curl`-equivalent raw HTML of `/readouts` contains none of the known bad pairings.

*(Positive side note: the staleness flags now expose just how old some estimates are — "updated 47mo ago," "38mo," "32mo," "26mo." Surfacing that is the right, honest call; it also argues for pruning or refreshing the most stale rows.)*

---

## The still-open list, unchanged and worth repeating

These are the same cheap, high-value fixes from the last re-audit — none have been actioned:

1. **Canonical → www everywhere.** `/calendar` must self-canonical to `https://www.pdufa.bio/calendar` (currently non-www); keep `/pdufa-calendar` canonicalized to `/calendar`. *(~15 min)*
2. **Regenerate the sitemap** on the www host, including `/conferences`, `/adcomm`, `/pdufa-calendar`, and all new detail pages; resubmit in Search Console. *(~15 min)*
3. **Flush the stale "ODIN Scores" title.** Live pages are clean; request re-indexing of `/pdufa-calendar` and add a guard so internal model language (ODIN / approval-probability) can never enter public `<title>`/meta — it contradicts the "no approval %" brand. *(~15 min + reindex wait)*

Then the remaining big bets when capacity allows: **B3 confidence grade** (staleness is done — add a confidence tier), **B4 unified cross-event filter**, **B6 API**, plus **mobile QA** (still not visually confirmed) and confirming **B5 backlink** outreach is running.

---

## Bottom line
Momentum continues — readout freshness flags are a genuine, visible upgrade and the page-1 ranking is holding. But the builder hasn't touched the three ~15-minute SEO-hygiene items that are throttling how fast the new pages compound, and the readouts "cleanup" turns out to be client-side only, so the accuracy defect is still crawlable. Priority order is unchanged: **canonical + sitemap + kill the ODIN listing first** (cheap, protective, compounding), then finish the readouts fix at the data layer, then the optional big bets.

---
## Sources (re-verified live 2026-07-10)
pdufa.bio `/`, `/calendar`, `/pdufa-calendar`, `/readouts`, `/conferences`, `/adcomm`, `/pricing`, `/pdufa/CORT`, `/pdufa/OTLK`, `/sitemap.xml` — https://www.pdufa.bio/ · SERP: Google "PDUFA calendar 2026 upcoming FDA decision dates" (2026-07-10).
*Informational product-strategy analysis. Not investment advice.*
