# Moat build pack + date-accuracy doctrine
**2026-08-29 · every figure below verified against source data or the live site on this date**
*Facts and historical statistics only — not investment advice.*

---

# PART 0 — WHY DATES ARE THE PRODUCT

Everything we are building rests on one claim: **when pdufa.bio prints a date, it is right, and you can see where it came from.**

That claim is the moat. Competitors have more traffic, older domains and bigger teams. None of them can say it, because none of them stores provenance. The moment we print one wrong date with confidence, the entire archive becomes "another calendar."

**So the accuracy rules below are not overhead on the moat. They *are* the moat.**

## The six date rules — non-negotiable

**1. Never conflate a goal date with an actual date.**
The PDUFA goal date is the FDA's deadline. The decision date is when the agency acted. **They are different fields and must never share one.** Our 2026 records carry `d` (goal) and `dcd` (decision); every new surface must carry both or explicitly state which one it shows.

**2. Never invent precision.**
`DAY` · `MONTH` · `QUARTER` · `HALF`. A source that says "Q4 2026" renders **"Q4 2026"**, never December 31. *(BPC parks a large share of its forward rows on New Year's Eve; that is exactly the failure we sell against.)*

**3. Every published date names its source.**
FDA notice, SEC filing, company release, or organiser agenda. A date with no source is either labelled unsourced or is not published. `/decisions` already does this — **305 sourced · 109 inferred · 46 unsourced** of 460. Extend the same three-state labelling to every new date surface.

**4. Date changes are recorded, never overwritten.**
When CAPR moved from 2026-08-22 to 2026-11-22, the old date is not wrong — it is *history*. Overwriting it destroys the most valuable series we own. Write `date_history[]`; never mutate in place.

**5. Timezone is declared before any timestamp is compared.**
Per RULE 1 in `CLAUDE.md`: this machine runs Pacific, the market runs Eastern, FMP is Eastern, Polygon is UTC. **State the zone before comparing.** This has corrupted four studies already.

**6. Publish counts, not rates, until the denominator is a census.**
Two live examples of the trap:
- **Decision timing:** the sourced-only sample showed 72% "before"; the full dated set showed 54%. Fixed by *sourcing the missing records*, not by disclosing around the gap.
- **CRLs:** 309 of 439 letters belong to later-approved applications. That is **not** "70% of CRLs end in approval" — the FDA releases all letters for an application *when it approves it*, so approved applications are structurally over-represented. **Counts only.**

---

# PART 1 — WHAT IS ALREADY TRUE (verified today)

| Asset | Verified state |
|---|---|
| `/research/fda-decision-timing` | **live, n=27** — 15 before · 9 on · 3 after · median **−1 day** · 945 words · `FAQPage` 3 Q |
| `/decisions` | **460 records — 305 sourced, 109 inferred, 46 unsourced** |
| Decision pages on disk | **464** (2025: **316**, 2026: **148**) |
| `dataset.mjs` | 453 records; **27 decided, all 2026, all carrying both goal and decision dates** |
| CRL corpus (openFDA, June pull) | **439 letters · 309 Approved / 130 Unapproved · NDA 324 / BLA 100 · 327 unique applications · 79 with more than one letter · 2002–2026** |
| `/decisions/crl` | live, 44 links, lede claims 47, **`FAQPage` Q=0**, **0 fda.gov links** |
| Cohort run-up data | **68 of 82** API records carry `cohort_n`; rendered inconsistently |
| Git dataset snapshots | **90** — CAPR's 08-22 → 11-22 change recoverable |
| Run-up study | **1,838 events** |
| CI guards | **51** (nav freeze = guard 51) |

---

# PART 2 — THE FIVE MOAT PLAYS

Each has a verified data position, an accuracy requirement, and a reason no competitor can copy it.

## 🥇 1. Extend decision timing to 2025 — **feasible, but it is a JOIN project**

**This is the single highest-value extension available, and I checked the feasibility rather than assuming it.**

*What I found:* the 2025 decision pages carry the **actual** date but **not** the goal date — 0 of 12 sampled contain goal-date language. The goal dates exist separately in the ODIN join (`_decisions_join_slim.csv`, 2,210 rows, **345 for 2025**). Our 316 2025 decision pages and those 345 goal dates are **not joined into records carrying both**.

**So this is not a rendering task.** It is: join 2025 goal dates to 2025 outcomes → **verify each pair against a primary source** → publish.

**Accuracy requirement:** every pair sourced before it counts, exactly as the 27 2026 rows were. Do not inherit ODIN-join dates unverified — that corpus is a modelling set whose coverage grows ~7× across years and **is not a census**.

**The payoff:** ~316 more decisions would take the sample from 27 to potentially 340+, and unlock a question with no public answer anywhere:

> **"Is the FDA deciding earlier than it used to?"**

Year-over-year median days-early, from primary sources. Nobody can answer that without both dates on both years.

## 🥈 2. The CRL corpus — link the letter, then join the outcome

**Verified:** 439 letters, **309 Approved / 130 Unapproved**, 79 applications with more than one letter. The site links **zero** of them.

**Two builds:**

**(a) Link the FDA letter on all 47 existing CRL pages.** Takes a page from *"we say it was a CRL"* to *"here is the FDA's letter."* Cheapest provenance upgrade on the board.

**(b) `/crl` hub answering the question retail actually asks:**
> *"The FDA has published 439 Complete Response Letters. 309 belong to applications that were later approved; 130 belong to applications still unapproved. 79 applications received more than one letter."*

**Accuracy requirements:**
- **Use the openFDA API pull, not the PDF scrape.** Verified side by side: openFDA has 0% missing dates and 0% missing company names; the PDF parse has **38% missing dates and 40% missing companies, plus 43% containing header junk** like `"OMPLETE RESPONSE January 15, 2025 Atara Biotherapeutics"`.
- **Counts, never a rate** (Rule 6).
- **Never call a CRL a rejection** — guard 41 must be inherited.
- Add `application_number` to our decision records so the join is deterministic rather than fuzzy on company+date.

## 🥉 3. The date-change tracker — a moat measured in elapsed time

**Verified:** 90 dataset snapshots in git; I reconstructed CAPR's extension from them (08-22 held through Aug 24, then 11-22).

**Build `/pdufa-date-changes`:** drug, company, old date, new date, days moved, **date first observed**.

**Accuracy requirement:** publish *"first observed on"*, not *"changed on"* — we know when **we** saw it, not when the FDA acted, unless a filing states it. That distinction is the difference between a fact and an assumption.

**Why uncopyable:** it requires having watched daily for months. A competitor starting today needs until 2027.

## 4. The cohort block — built, computed, and leaking value

**Verified:** 68 of 82 API records carry `cohort_n`. `/pdufa/REGN-garetosmab` renders it; **`/pdufa/CAPR-deramiocel` renders nothing despite holding `n=274, p25 −3.99%, p75 +2.75%`.**

**Two fixes:**
- **Render on every page that has the data.**
- **Stop collapsing the distribution to "±1%".** REGN is symmetric (−0.93/+1.03); **CAPR is downside-skewed (−3.99/+2.75)**. The skew is the signal.

**Accuracy requirement:** always print **n**, always print p25 and p75, and always state it is history for similar events — not a forecast for this one.

## 5. "When does the run-up peak?" — the best unpublished asset

**Verified:** 1,838 events with T-120→T+5 daily series.

*"When should I have been in?"* has no sourced public answer. Published as history with n attached, it is factual and uncopyable.

**Accuracy requirement:** disclose the cohort definition and the n on the chart itself, not in a footnote. State the window convention (trading days vs calendar days) explicitly — that ambiguity is how run-up studies mislead.

---

# PART 3 — GUARDS TO ADD

Accuracy that isn't enforced decays. Each of these is mechanical:

| Guard | Asserts |
|---|---|
| **52 — goal ≠ actual** | no record renders a goal date where a decision date is meant, or vice versa |
| **53 — precision honesty** | nothing below DAY precision renders as a calendar day |
| **54 — source-state completeness** | every published date is sourced, inferred, or unsourced — never unlabelled |
| **55 — date immutability** | a changed date appends to `date_history[]`; in-place mutation fails the build |
| **56 — no rate over a non-census** | a `%` adjacent to a decision/CRL count requires a declared inclusion rule |
| **57 — n-adjacency** | any median or quartile renders with its `n` in the same block |

Guard 41 (CRL ≠ rejection) and guard 51 (nav freeze) already stand.

---

# PART 4 — BUILD ORDER

| # | Action | Effort | Accuracy gate |
|---|---|---|---|
| 1 | Refresh openFDA CRL pull; retire the PDF index | hours | use API fields only |
| 2 | Add `application_number` to decision records | hours | typed (`NDA 215344`) |
| 3 | Link the FDA letter on 47 CRL pages | 1 day | letter must match app + date |
| 4 | `FAQPage` on `/decisions/crl` + `/decisions/approvals` | hours | counts only, no rates |
| 5 | Fix the cohort block — every page, p25/p75, with n | hours | n in the same block |
| 6 | `/crl` hub — 439 · 309 / 130 · 79 multi | 1 day | counts only |
| 7 | `/pdufa-date-changes` + `date_history[]` | 2 days | "first observed", not "changed" |
| 8 | **2025 timing join** — 316 outcomes × 345 goal dates | 3–4 days | **every pair sourced before it counts** |
| 9 | Per-letter pages `/crl/{app}-{date}` | 2 days | FDA URL on every page |
| 10 | Run-up peak study | 1 day | cohort + n + window convention stated |
| 11 | Guards 52–57 | 1 day | — |
| 12 | Reconcile `/decisions/crl` lede (47 vs 44 links) | minutes | — |

---

# PART 5 — HOW WE SAY IT

The accuracy work only converts to trust if the reader sees it. Two sentences already do this better than anything else on the site:

> *"305 of 460 FDA decisions in this archive link to a primary source. 109 are inferred from the share-price reaction and 46 carry no source; all three states are labelled on every row."*

> *"We do not publish an overall approval rate… a rate computed over unverified outcomes would be false precision."*

**Put the first one on the homepage.** It is the most quotable thing we own, it is verifiably true, and it invites a comparison no competitor survives.

---

# BOTTOM LINE

**The moat is not the data. It is that every date carries its source, and that we refuse to publish the ones that don't.**

Five plays, all verified as feasible today:
1. **2025 timing extension** — the highest-value one, and it's a *join* project, not rendering: the 2025 pages hold actual dates, the goal dates live separately, and **every pair must be sourced before it counts**.
2. **CRL corpus** — 439 letters, **309 came back**, and we link none of them. Use the openFDA API; the PDF scrape loses 38% of dates and 40% of companies.
3. **Date-change tracker** — 90 git snapshots, uncopyable, and it must say *"first observed"*.
4. **Cohort block** — computed, partly rendered, and flattening the skew that matters.
5. **Run-up peak** — 1,838 events, no public answer anywhere.

And six rules that make all of it defensible: never conflate goal with actual, never invent precision, always name the source, never overwrite a date, declare the timezone, and **publish counts until the denominator is a census.**

---
*Every figure in this document was verified against source data or the live site on 2026-08-29. Not investment advice.*
