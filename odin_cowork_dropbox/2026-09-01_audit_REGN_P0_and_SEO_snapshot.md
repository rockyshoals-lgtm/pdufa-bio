# Audit — 2026-09-01 · REGN P0 + SEO snapshot
**Site built 2026-09-01T16:11Z · both consoles read live · REGN verified against primary source**
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — 🔴 P0: WE ARE SHOWING "AWAITING" ON AN APPROVED DRUG

**You asked whether the REGN PDUFA got approved. It did — and our site doesn't know.**

| | |
|---|---|
| **Approved** | **2026-08-19** as **PASATRU™ (garetosmab-grts)** |
| Indication | Fibrodysplasia ossificans progressiva (FOP), adults |
| Goal date | 2026-08-31 — **approved 12 days early** |
| Basis | Phase 3 OPTIMA — ≥90% reduction in new HO lesions at 56 weeks vs placebo |
| **Our site says** | **goal 2026-08-31 · status "Awaiting" · outcome `None` · decision_date `None`** |
| **Stale by** | **13 days** |

Primary source: [Regeneron newsroom release](https://newsroom.regeneron.com/news-releases/news-release-details/pasatrutm-garetosmab-grts-first-and-only-fda-approved-treatment), corroborated by [Big Molecule Watch](https://www.bigmoleculewatch.com/2026/08/28/fda-approves-regenerons-pasatru-garetosmab-grts-for-fibrodysplasia-ossificans-progressiva/) and [STAT](https://www.statnews.com/2026/08/19/regeneron-fop-garetosmab-fda-approval-pasatru/).

## Why this one hurts more than most

`/pdufa/REGN-garetosmab` is **one of the best-converting pages on the site.** From today's Bing data:

```
garetosmab pdufa   ·  12 impressions  ·  4 clicks  ·  33.33% CTR  ·  position 2.00
```

**People are searching this exact term, finding us at position 2, clicking a third of the time — and being told the decision is still pending on a drug approved thirteen days ago.**

## Root cause — and it's structural, not a one-off miss

**The decided-sweep is keyed on the goal date.** It looks for events whose target date has passed. Garetosmab was approved **12 days before** its goal date, so the sweep had no reason to look at it until Aug 31 — and then only flagged it "Awaiting" rather than going to check.

**That logic is backwards for this dataset.** Our own record shows **15 early decisions** and a **median of −1 day**. Early is the norm. A sweep triggered by the goal date is structurally late for the majority of decisions.

**Fix:** scan armed names for approval news from **BLA/NDA acceptance onward**, not from the goal date. The builder's recent `EARLY_WINDOW 270→180` change is pointed at this; it needs to cover the pre-goal window specifically.

## The good news
**REGN is the only stale row.** I scanned every event whose goal date has passed:

```
events past goal date with no recorded outcome: 1  (REGN, 1 day past goal)
early decisions already on record: 15
```

Detection generally works. This is one gap in the trigger logic, not a broken pipeline.

## And it costs us content, not just accuracy
A **12-day-early approval** is exactly what `/research/fda-decision-timing` exists to document — and it's missing from the n=27 sample. Publishing it takes the sample to 28 and adds a strong data point to the "FDA decides early" thesis.

---

# PART 2 — PREVIOUS ITEMS: WHAT LANDED

| Item | Status |
|---|---|
| **openFDA CRL refresh 439 → 458** | ✅ `CRL_corpus_openFDA_2026-08-29.json` — Approved 309, **Unapproved 130 → 149** (all 19 new records are unapproved, consistent with FDA's release pattern) |
| **FAQPage on `/decisions/crl`** | ✅ **Q=4** (was 0) |
| **FAQPage on `/decisions/approvals`** | ✅ **Q=3** (was 0) |
| CRL FAQ handles the denominator trap | ✅ **better than I specified** — see below |
| Link the FDA letters | ❌ **still 0 fda.gov links, 0 PDF links** |
| `/crl` hub | ❌ 404 |
| Lede vs link count | ❌ still 47 vs 44 (and 89 vs 88 on approvals) |
| `Drug` schema on 544 pages | ❌ not started |
| `/pdufa-date-changes` | ❌ 404 |

**The CRL FAQ answer is the best writing on the site this week** — it explains the *mechanism* of the bias, which I hadn't specified:

> *"Many do: 309 of the 458 published letters belong to applications the FDA later approved. **That count is not an approval rate** — the FDA's first transparency releases were letters for products it had since approved…"*

That's the denominator doctrine applied correctly and explained to a reader.

---

# PART 3 — SEO SNAPSHOT

## Bing — accelerating

| | Aug 26 | **Aug 30** | Δ |
|---|---:|---:|---:|
| Clicks | 195 | **236** | +21% |
| Impressions | 6.4K | **7.5K** | +17% |
| CTR | 3.04% | **3.16%** | — |
| Keywords ranked | 321 | **389** | +21% |

## Bing AI citations — still compounding

| | Aug 26 | **Aug 30** | Δ |
|---|---:|---:|---:|
| Citations | 1.6K | **2.2K** | **+37%** |
| Grounding queries | 16 | **18** | +2 |
| Avg cited pages | 12 | **13** | — |

Peak day **Aug 27: 330 citations.** Head terms keep growing: `pdufa date` 91 → **159** citations (20.70% share), `fda calendar 2026` 49 → **74** (20.67%). `zanidatamab pdufa date` still holds **100%**.

## Google — impressions up, everything else flat

| | Aug 29 | **Sep 1** |
|---|---:|---:|
| Clicks | 53 | **53** |
| Impressions | 2.37K | **2.55K** |
| CTR | 2.2% | 2.1% |
| Avg position | 20.5 | 20.5 |
| **Indexed** | **57** | **57** — flat 12+ days |
| Discovered, not indexed | 1,290 | **1,346** |

## 🔴 The Google reframe: per-query positions are now visible, and they are far worse than the average suggests

| Query | Impressions | Clicks | **Position** |
|---|---:|---:|---:|
| pdufa dates | 60 | 0 | **69.1** |
| pdufa date | 49 | 0 | **81.5** |
| pdufa calendar | 47 | 0 | **62.0** |
| deramiocel pdufa | 3 | 1 | 79.0 |

**We are not at position 20 on the head terms. We are at positions 62–82** — pages 7 to 9. The "average position 20.5" is dragged up entirely by entity queries.

And those entity queries are perfect:

| Query | Position | CTR |
|---|---:|---:|
| pdufa.bio | **1.0** | **100%** |
| monalizumab | **4.0** | **100%** |
| nct04229979 | **6.0** | **100%** |
| miplyffa | **10.0** | **100%** |
| vktx phase 3 results date | 10.6 | 20% |

**Where we reach Google's top 10, we convert at 20–100%. On head terms we're on page seven.** That settles it: on Google, the head terms are not a 2026 target and pursuing them wastes the quarter. **Every Google click we have came from an entity query.**

---

# PART 4 — 🟢 THE NEW SIGNAL: a "today" query family is emerging on BOTH surfaces

This appeared simultaneously in Bing web search and Bing AI citations, and we have no page for it:

| Query | Bing web | AI citations |
|---|---|---|
| **`fda approvals today pdufa`** | 30 impressions · 4 clicks · **13.33% CTR** · position 3.77 | **36 citations · 28.57% share** |
| `gilead pdufa today` | 10 impressions · 1 click · 10.00% · position 2.30 | — |

**People are asking what the FDA decided *today*, and both the search index and the answer engine are already sending them to us — with no page built for the question.**

**Build `/today`** (or `/fda-decisions-today`): what decided today, what's decided this week, what's due next. Dynamic by construction, so it refreshes daily — which also feeds the freshness signal that already shows "4 hours ago" against competitors on the SERP.

**This is the highest-conviction new content opportunity in the data**, because demand is proven on two independent surfaces before we've built anything.

---

# PART 5 — HOW TO KEEP THE MOMENTUM

## Bing + AI citations — keep doing what's working, and remove the friction
1. **Fix REGN today.** A 33%-CTR page serving a 13-day-stale answer damages exactly the trust the citation engine rewards.
2. **Build `/today`.** Proven demand on both surfaces, zero competition.
3. **`Drug` schema + `alternateName` on 544 pages.** Still the biggest unexploited non-link lever — `FAQPage` says "there's a Q&A here"; `Drug` says "this page **is** the entity."
4. **Link the 458 CRL letters.** Primary-source documents we hold and don't cite.
5. **Publish the early-decision story.** Garetosmab at −12 days is a strong addition to the n=27 timing sample.

## Google — stop fighting the head terms
6. **Every Google click came from an entity query at position 1–10.** Double down on drug, ticker and NCT pages; abandon "pdufa calendar" as a 2026 Google target.
7. **Indexed has been frozen at 57 for twelve days** while not-indexed grew to 1,346. More pages will not move Google — and you're handling the links side, which is the only lever that will.
8. **PAA capture** remains the cheapest page-one route without authority: Google's own box asks *"Does FDA approve before the PDUFA date?"* and we hold the only sourced answer.

## Standing
⛔ **Nav frozen until 2027-01-01** (guard 51). Every edit resets the sitelink clock.

---

# BOTTOM LINE

**Garetosmab was approved on 19 August as PASATRU — twelve days early — and our site still says "Awaiting."** It's the only stale row, but it's on a page converting at 33% CTR at position 2. The root cause is worth fixing properly: the decided-sweep triggers on the goal date, and with 15 early decisions on record and a median of −1 day, **early is the norm — so a goal-date trigger is structurally late.**

**Bing is compounding** — 236 clicks, **2.2K AI citations (+37%)**, 389 keywords. **Google is not:** 57 indexed pages, flat for twelve days, and the head terms sit at **positions 62–82**, not 20. Every Google click you have came from an entity query at position 1–10.

**And the data handed you a new one:** `fda approvals today pdufa` is now converting at **13.33% CTR** and holding **28.57% citation share** — for a page that doesn't exist. Demand proven on two independent surfaces, no competitor serving it. Build `/today`.

---
*Both consoles read live 2026-09-01. REGN approval verified against Regeneron's own release. Not investment advice.*
