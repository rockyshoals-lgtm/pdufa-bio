# Post-build audit + information architecture: patents and plain-language
**2026-08-12 (second pass, ~18:10 UTC) · every line below re-verified against live pages today**
*Facts and historical statistics only — not investment advice.*

---

# 1. SCORECARD — what shipped, what didn't

| § | Item | Status | Evidence (live, cache-busted) |
|---|---|---|---|
| 2.1 | `FAQPage` on 10 hubs | ✅ **DONE** | `FAQPage=1` on all 10 + homepage. Was 0/10. |
| 2.2 | Drug Q&A 2 → 5–6 | ✅ **DONE** | rusfertide 5, deramiocel 5, mk-6240 4, zoryve 6, semaglutide 3, monalizumab 3 |
| 2.3 | `Dataset` schema | ✅ **DONE** | `/research` = 4, `/developers` = 1 |
| 3 | Freshness / countdown | ✅ **DONE (differently)** | `dateModified` now **2026-08-12T18:00** sitewide (was 08-08 on `/calendar`). Implemented as relative tokens ("tomorrow") + live counts, not "in N days" — **better**, and it makes the stamp honest. |
| 4.2 | Drug pages 400–600w | ✅ **DONE** | 421–587w (was 337–380) |
| — | Plain-language spec | ✅ **DONE** | Violations fixed at source; CI **guard 41** |
| — | Conflict-marker guard | ✅ **DONE** | **guard 42** (after an S1 that reached production — see §3) |
| — | `BreadcrumbList` sitewide | ✅ **DONE** | commit `bec2d6f` |
| **1.1** | **Bing legacy API migration** | 🔴 **NOT DONE** | `grep -c "api.svc/json" bing_rank_report.py` → **2**. **19 days.** |
| 4.1 | Per-event PDUFA URLs | ❌ not done | `/pdufa/LNTH-2026-08-13` → 404 |
| 4.3 | `/compare/` pilot | ❌ not done | 404 |
| — | Patent cliff | ❌ not started | `/patent-cliff`, `/patents`, `/exclusivity` all 404 |
| 2.4 | Weekly grounding review | ⏳ process — can't verify externally | |

**The builder cleared essentially the whole citation program in one pass.** The one thing with a hard clock — the Bing API migration — is the one thing untouched, and it's now 19 days out. That's the only item I'd call urgent.

---

# 2. 🔴 NEW DEFECT — our page and our API state different numbers

**Severity S2.** Found while fact-checking the new FAQ answers.

`/calendar` publishes, and now marks up as a **quotable `FAQPage` answer**:

> *"67 FDA decision dates are on the 2026 calendar; 52 are still ahead as of August 12, 2026."*

Our own public API, asked for the identical window:

```bash
curl -s "https://www.pdufa.bio/api/v1/pdufa?from=2026-06-01&to=2026-12-31&limit=500"
# meta.total = 64   (page says 67)
# Upcoming  = 46    (page says 52)
```
`meta.total=64, returned=64` — no truncation, no pagination artifact.

**Two separate problems:**

**(a) The counts contradict.** Page 67/52, API 64/46. The page's internal arithmetic is self-consistent (52 ahead + 14 decided + 1 lapsed = 67), so the page believes itself — but one of our two public surfaces is wrong. This is exactly what `test_decided_consistency.py` exists to prevent, and it is **worse now than last week**, because the number is wrapped in `FAQPage` schema. We have deliberately made it the sentence an AI engine lifts.

**(b) The FAQ drops the scope qualifier.** The page body says:

> "This page lists 67 FDA decision dates covering **June 2026 to December 2026**."

The FAQ answer says "on the **2026 calendar**". Half a year silently becomes a full year. An engine quoting us would assert something we never checked. This is a §1.4 violation of the spec the builder just implemented — the number is right for its window, and the window went missing.

**Fix:** derive the FAQ numbers from the same query the API answers, and keep the window in the sentence: *"67 FDA decision dates are listed for June–December 2026; 52 are still ahead as of August 12, 2026."* Then add a CI guard asserting page count == API count for the same window. **Mechanical, no judgement — it belongs in the guard set.**

---

# 3. RED TEAM — the plain-language work holds

Swept the never-say table across `/`, `/calendar`, `/decisions`, `/drug/rusfertide`, `/drug/deramiocel`, `/drug/zoryve`, `/ticker/RARE`, `/adcomm`, `/glossary`, `/learn/why-cross-trial-comparisons-mislead`:

```
CRL…rejection | rejection letter | FDA rejected | was rejected
| denied approval | cure rate | success rate      →  0 hits, all 10 pages
```

The `/decisions` answer is the best thing on the site:

> *"We do not publish an overall approval rate. 307 of the 457 records are price-inferred, and a rate computed over unverified outcomes would be false precision; outcome counts are shown for verified records only."*

That is a refusal written to be quoted. Keep it exactly as-is.

**One thing to sit with:** commit `ab953ae` records that raw git conflict markers were live on the homepage for a full day, through 41 semantic guards, and were caught by *you*, not by CI. The lesson the builder drew is right — every guard checked meaning, none checked for the artifact git itself leaves. Guard 42 closes it. I'd add the general form: **guards that assert what must be true never catch what should never appear.** Worth one cheap "does this page contain anything that is obviously not prose" check.

## Corrections to my own findings this session
Per §2.5 of the protocol, loudly:
1. **I initially reported the public API as failing.** Wrong — the 400s were caused by *my own* cache-buster param. All five documented endpoints return 200 with full payloads. The strict validation is good design: it names the bad param, lists the valid ones, links docs, returns a `request_id`.
2. **My calendar row-parsing regex produced 32 phantom page-vs-API discrepancies** by crossing row boundaries and pairing each date with the next row's ticker. Discarded entirely. The 67-vs-64 finding in §2 does **not** depend on it — it comes from the page's own printed sentence against `meta.total`.

## Minor, real
- **`/api/v1/dataset.mjs` returns HTTP 500** (`FUNCTION_INVOCATION_FAILED`, 5/5 probes, no params). **S4** — nothing links it (`/developers`, `/llms.txt`, `/research`, `/sitemap.xml` all have 0 references), so no user or crawler path reaches it. Route it away or make it 404 rather than 500.

---

# 4. INFORMATION ARCHITECTURE

## 4.1 The constraint nobody has named: the nav is full

```
Calendar · Decisions · Readouts · Run-up · Stocks · Drug Index · Conferences ·
Advisory Committees · Screener · Research · API · SLS tracker · Account · Pro
```

**14 items.** Patents would be 15. Past roughly 7, a nav stops being navigation and becomes a list — people scan it, fail to build a mental model, and fall back to search. So the real question isn't "does Patents get a tab," it's **"what are the five things this site does?"**

I'd group:

| Group | Contains | Why |
|---|---|---|
| **Calendar** | Calendar, Decisions, Readouts, AdComm, Conferences | dated events — *what happens when* |
| **Explore** | Drug Index, Stocks, Screener | entity lookup — *tell me about X* |
| **Patents** ⭐ | Patent cliff hub | *new* — a different clock |
| **Research** | Research, Run-up, **Learn, Glossary, Methodology** | evidence + how we know |
| **API** | Developers | machine access |

`SLS tracker` is a campaign, not a section — it belongs on the homepage, not in permanent nav. Account/Pro sit right-aligned, outside the content nav.

**14 → 5.** And Patents arrives with room instead of being crammed in.

## 4.2 Patents: yes, its own tab — your instinct is right

Four reasons it can't be a sub-page of anything existing:

1. **Different clock.** Everything on the site today is measured in days-to-catalyst. A cliff is measured in *years*. It doesn't belong in a calendar.
2. **Different question.** The site answers "will this be approved?" A cliff answers "what happens to this company's revenue, and what might they buy." Different reader, different session.
3. **Different source and cadence.** Orange Book, refreshed monthly, no key. Everything else is FDA/SEC continuous.
4. **It's big.** ~1,319 brand NDAs with unexpired patents; **427** losing exclusivity 2026–2031. That's larger than several existing sections.

**Structure:**
```
/patent-cliff                    hub — by year · by company · by area
/patent-cliff/2027               "64 drugs lose patent protection in 2027"
/patent-cliff/company/abbvie     AbbVie's 14
/patent-cliff/oncology           therapeutic-area cut
/drug/{name}  →  "Patent protection" module on the 310 existing pages
```

**Hub *and* inline — not either/or.** The hub wins the "2027 patent cliff" queries; the module deepens 310 pages that already rank and already get cited. The module is the higher-value half.

**On naming**, per the spec: "patent cliff" is jargon, but it's also the phrase people type. Same resolution as PDUFA — **jargon in the URL and title because that's the query; plain English in the H1 subtitle.**

> # 2027 Patent Cliff
> **64 drugs lose their patent protection in 2027.** This is the earliest date a generic could enter — not a guarantee one will.

That second sentence is non-negotiable on every cliff page. It's the LOE guard, and guard 41 already has it dormant-armed.

## 4.3 Drug explanations: the page already exists and nobody can reach it

This is the finding I didn't expect.

`/glossary` is **live, 1,525 words, 14 `DefinedTerm`s + a `DefinedTermSet`** — genuinely good work. But:

```
inbound links from sitewide nav:   /glossary 0   /learn 0   /methodology 0
/drug/rusfertide links to:  /learn/what-is-a-pdufa-date, /learn/why-cross-trial-comparisons-mislead
                            ...and NOT the glossary
```

**Three explainer surfaces, all orphaned from the nav.** So the answer to "where should drug explanations go" is partly: *they're already somewhere, and the somewhere is invisible.*

And the coverage is regulatory-only:

| Covered | **Missing — every clinical term from the spec table** |
|---|---|
| CRL, accelerated approval, breakthrough therapy, orphan, surrogate | control arm, single-arm, randomized, double-blind, placebo-controlled, primary endpoint, ORR, PFS, OS, median, hazard ratio, confidence interval, non-inferiority, 505(b)(2), Pearl Index |

"Control arm" — your exact example — **is not on the site.**

### Where explanations belong, in priority order

**1. Inline, at the point of use — this is where the value is.**
Readers land on `/drug/rusfertide` from search and never visit a glossary. When the page says "single-arm", the plain-English gloss has to be *right there*:

> The main study gave the drug to 140 patients with **no comparison group** — everyone enrolled received it.

Not a tooltip, not a link. **Written into the sentence.** A tooltip is a link with extra steps, and on mobile it's a coin flip. This costs nothing at build time because the drug pages are generated.

**2. `/glossary` as the canonical, linkable definition.**
Give every term an anchor (`/glossary#single-arm`) so drug pages can deep-link and each definition becomes individually citable. Expand to the 15 clinical terms above. Add `FAQPage` alongside the existing `DefinedTermSet` — "what is a control arm?" is a real query with a one-sentence answer, which is the exact citation unit.

**3. `/learn/{topic}` long-form** — only where the misunderstanding is expensive. `/learn/why-cross-trial-comparisons-mislead` is the model. Two or three more at most; don't dilute it.

**And put Glossary in the nav** (under Research). Three orphaned explainer pages is both a UX gap and wasted crawl equity.

---

# 5. WHAT I'D DO, IN ORDER

| # | Item | Why now | Effort |
|---|---|---|---|
| 1 | **Bing API migration** | **19 days**, primary channel | — |
| 2 | **Fix the 67-vs-64 contradiction + restore the window** | It's in FAQ schema — we're actively feeding it to engines | hours |
| 3 | Guard: page count == API count, same window | Mechanical; prevents recurrence | hours |
| 4 | Nav regroup 14 → 5, surface Glossary/Learn/Methodology | Unblocks Patents, fixes 3 orphans | half day |
| 5 | Glossary: +15 clinical terms, anchors, `FAQPage` | "what is a control arm" is a real query | 1 day |
| 6 | Inline plain-language on drug pages | 310 pages, generated, no new URLs | 1 day |
| 7 | `/patent-cliff` hub + `/drug/` module | Prototype already runs | 2–3 days |
| 8 | `/compare/` pilot (5) | Needs per-page judgement | 2 days |
| 9 | Per-event PDUFA URLs | Deferred, still right | 1 day |

**6 before 7.** The plain-language layer is the thing that makes the patent pages readable when they land — and it's the cheaper of the two.

---

# 6. THE HONEST SUMMARY

The builder shipped almost the entire citation program and the plain-language spec in a day, and the spec held under adversarial sweep — zero never-say violations across ten pages.

Two things need your attention:

**The Bing migration has 19 days and nobody has started it.** It's the only item on the site with an external deadline.

**We now publish a number our own API contradicts, and we've marked it up as a quotable answer.** The FAQ work was the right move and it's well executed — but it raises the cost of every stale figure, because a wrong sentence in `FAQPage` isn't just wrong on the page, it's *offered up* to be repeated. The countdown fix already proved the pattern for keeping figures live. The counts need the same treatment.

On patents: build it as its own section. But regroup the nav first, or it lands in a list of fifteen and nobody finds it.

On explanations: the glossary already exists, it's good, and it's unreachable and missing every clinical term. Fix reachability, add the clinical terms, and write the plain wording **into the drug pages themselves** rather than behind a link.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
