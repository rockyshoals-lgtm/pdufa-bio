# Data moat expansion + ⛔ NAV FREEZE DIRECTIVE
**2026-08-29 · every idea below feasibility-tested against live data before recommending**
*Facts and historical statistics only — not investment advice.*

---

# ⛔ PART 0 — NAV FREEZE (answering "is this in the audit?")

**Yes — it's in `2026-08-29d`, in two places.** But it was inside a phased plan and a risk list, and it needs to be unmissable. Restating it as a standalone directive:

> ## 🔒 DO NOT CHANGE THE NAVIGATION UNTIL 1 JANUARY 2027
>
> No renaming. No reordering. No adding or removing top-level items. No changing the dropdown groupings.
>
> **Why:** FDA Tracker holds Bing #1 for "pdufa calendar" with a **nine-link sitelink block**. We are **#2 with none**. Sitelinks are the single visible difference at the top of that SERP, and Bing awards them for a *stable*, shallow, clearly-labelled hub structure observed consistently over months. The current nav — Calendar · Decisions · Readouts · Patents · [Explore] · [Research] · API — is exactly the shape that earns them.
>
> **The clock starts from the last change.** Every edit resets it. Four months of stability is the asset.
>
> **Frozen:** the nav bar, its labels, its order, its groupings, and the URLs behind them.
> **Not frozen:** page content, titles, meta descriptions, schema, internal links inside pages.

---

# PART 1 — 🥇 THE BIGGEST WIN IS ALREADY BUILT AND INVISIBLE

**68 of 82 API records carry cohort run-up statistics — and not one is displayed to a reader.**

```
GET /api/v1/pdufa  →  cohort_move_median_pct, cohort_move_p25_pct,
                      cohort_move_p75_pct, cohort_n
example: GSK  median 0%  ·  p25 −0.93%  ·  p75 +1.03%  ·  n = 790
```

On `/pdufa/CAPR-deramiocel` the words *cohort*, *median*, *typical* and *similar* appear **zero times**.

**This is the single most-wanted number in retail biotech and we computed it, stored it, and never rendered it.** "What does a stock like this normally do into a PDUFA?" is the question behind every catalyst trade.

**Ship it as a block on every event page:**

> **What stocks like this have done**
> Across **790 comparable PDUFA events** (same market-cap tier, T-30 to T-1), the median move was **0%**. Half landed between **−0.93%** and **+1.03%**.
> This is what happened historically to similar events. It is not a forecast for this one.

That framing is on-brand: a distribution with its **n**, an explicit refusal to predict, and a fact competitors don't have. It also feeds the AI-citation engine — *"what is the average run-up before a PDUFA date"* is a live query family with no sourced answer anywhere.

**Cost: rendering work only. The data is already there.**

---

# PART 2 — 🥈 THE PDUFA DATE-CHANGE TRACKER (proven feasible today)

**No competitor can build this without a time machine. We already have the data and didn't know it.**

The daily rebuild means **90 dataset snapshots sit in git**. I reconstructed a real date change from them:

```
2026-08-22   CAPR PDUFA = 2026-08-22
2026-08-23   CAPR PDUFA = 2026-08-22
2026-08-24   CAPR PDUFA = 2026-08-22   ← last day at the old date
2026-08-24   CAPR PDUFA = 2026-11-22   ← extension observed
2026-08-25 … 2026-08-29  = 2026-11-22
```

**Every PDUFA date change since the daily rebuilds began is recoverable, with the date we first observed it.** No record carries a `prior_date` field — but git *is* the field.

**Build `/pdufa-date-changes`:**
- Every observed change: drug, company, old date, new date, days moved, date first observed
- Per-event pages get a "Date history" block
- Backfill from git; going forward, write a `date_history[]` array into the dataset so it stops depending on archaeology

**Why it's a moat:** it requires having watched daily for months. A competitor starting today needs until 2027 to match it. And it answers questions nobody serves — *"has [drug]'s PDUFA date changed"*, *"how often does the FDA extend a review"*, *"what happens to the stock when a PDUFA date slips"*.

**It also feeds the alerts engine** you need for Pro. Date-change detection is the same diff.

---

# PART 3 — 🥉 CASH CUSHION AT THE CATALYST

I tested my first framing — *"companies whose cash runs out before their catalyst"* — and it returns **zero rows**. Good thing I checked; it would have shipped as an empty page.

**The framing that works is cushion remaining when the decision lands:**

| Ticker | Catalyst | Months away | Runway | **Cushion after** | Cap |
|---|---|---:|---:|---:|---|
| **BTAI** | 2026-11-14 | 2.5 | 3.6 mo | **1.1 mo** | Nano |
| **INO** | 2026-10-30 | 2.0 | 5.4 mo | **3.4 mo** | Micro |
| BFRI | 2026-09-28 | 1.0 | 8.1 mo | 7.1 mo | Nano |
| INBX | 2027-04-14 | 7.5 | 14.7 mo | 7.2 mo | Small |

Distribution across the 26 events with data: **2 under 6 months**, 4 at 6–12, 20 above 12.

**Only two names qualify — and that's the point.** BTAI walks into an FDA decision with roughly **five weeks of cash on the other side**. Every retail trader in that name wants that number and no site publishes it.

**Caveat to disclose:** `cash_runway_months` is present on **26 of 55** upcoming events (**47%**). Publish the covered subset, state the coverage, and never imply the uncovered names are safe.

---

# PART 4 — TESTED AND NOT VIABLE YET

**AdComm → decision concordance.** *"How often does the FDA follow its advisory committee?"* is a superb question with high citation value. **The API holds 2 adcomm events.** Not a dataset. Revisit when the archive reaches ~30.

---

# PART 5 — THE STRATEGIC SHAPE OF THE MOAT

Every competitor can copy a calendar. What none of them can copy:

| Asset | Why it can't be copied |
|---|---|
| **289 of 461 decisions with primary sources** | months of manual verification, and the sourcing rate is published |
| **26/26 goal-vs-actual decision timing** | needs both dates, sourced |
| **1,833-event run-up study** | needs price history joined to catalyst history |
| **Cohort distributions with n=790** | ⬅ **already computed, not yet shown** |
| **90 daily snapshots → date changes** | ⬅ **requires having started months ago** |
| 427-drug patent cliff with ATC families | Orange Book + RxClass join |
| Conference presenters mined from filings | SEC mining with an edition gate |

**The pattern: our moat is time-series and provenance, not coverage.** Anyone can list dates. Only we can say *what changed, when we saw it, where it came from, and what happened last time* — with the sample size attached.

**Lean into that.** The tagline is already true: *nobody else shows their work.*

---

# PART 6 — DO THIS, IN THIS ORDER

| # | Item | Cost | Why |
|---|---|---|---|
| **0** | **🔒 FREEZE THE NAV until 1 Jan 2027** | zero | the sitelink block is the gap to Bing #1 |
| 1 | Render the cohort block on every event page | rendering only | best-value data on the site, currently invisible |
| 2 | Backfill `/pdufa-date-changes` from git; add `date_history[]` going forward | 2 days | uncopyable, and it's the alerts engine |
| 3 | Cash-cushion view over the 47% covered, coverage stated | 1 day | BTAI at 1.1 months is a headline nobody has |
| 4 | Capture the four Google PAA questions verbatim | hours | cheapest page-one entry without domain authority |
| 5 | `/condition` hub FAQ (Question=0) | hours | every other hub has one |
| 6 | Watch `/condition/cancer` position after the 75% word cut | monitor | only uncontrolled change in the last batch |
| — | AdComm concordance | deferred | 2 events; revisit at ~30 |

---

# BOTTOM LINE

**Yes, the nav freeze is in the plan — and it's now a standalone directive at the top of this document.** It is the cheapest thing on the board and the one most likely to be broken by accident.

**The best data you have is already built and nobody can see it.** 68 event records carry cohort run-up distributions with n=790, and the words *median* and *cohort* appear zero times on the event pages. That's a rendering task, not a data task, and it answers the question every catalyst trader actually asks.

**The best data you could build is sitting in git.** 90 daily snapshots make every PDUFA date change recoverable — I pulled CAPR's Aug 22 → Nov 22 extension out of history to prove it. That's a moat measured in elapsed time, which is the only kind a competitor can't buy.

And I killed one of my own ideas before it shipped: "cash runs out before the catalyst" returns zero rows. The version that works — **BTAI facing an FDA decision with 1.1 months of cash on the far side** — is narrower, real, and far more useful.

---
*All figures verified against the live API and git history, 2026-08-29. Not investment advice.*
