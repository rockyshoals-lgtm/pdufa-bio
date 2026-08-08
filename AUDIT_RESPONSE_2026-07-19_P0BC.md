# P0-B and P0-C — closed, deployed, verified live (2026-07-19)

## 🔴 P0-B — API claimed day precision on 299 month estimates: FIXED

**Confirmed the defect exactly:** all 299 readouts sat on the **15th** of their month — the entire
distribution — every one tagged `date_precision:"day"`. That is not 299 companies picking
mid-month; it is the month **midpoint** used as a sortable stand-in for a ClinicalTrials.gov
primary-completion estimate. The rendered page said so honestly ("Jun 2026 (est.)" + a shift
disclaimer); the API contradicted its own page, and `/llms.txt` is live.

**Fix (`api/v1/dataset.mjs` + `api/v1/_lib.mjs`):**
- 299 readouts → `dp:"month"` + new `dm:"YYYY-MM"`; `d` kept as the documented sortable midpoint
- `_lib.mjs` CORE now emits **`date_month`**, with an inline note that `date` must never be
  rendered as a hard day unless `date_precision === 'day'`
- **The 99 genuine days were left alone** — 83 PDUFA (26 distinct days-of-month), 2 AdComm,
  14 Conference. Only rows that were *both* on the 15th *and* status `Estimated` were downgraded.

**Live:** 299 readouts `month` + `date_month`; 83 PDUFA still `day`; 0 readouts missing `date_month`.

**Guard:** `tests/test_api_precision_honesty.py` — fails if >60% of a type's day-precision dates
share one day-of-month, if any `Estimated` row claims `day`, if a `month` row lacks `dm`, or if the
API stops emitting `date_month`. Verified by restoring the defect: exit 1.

---

## 🔴 P0-C — flagship page contradicting itself: FIXED, and it was worse than reported

All **8** figures the audit flagged were stale; I reproduced source truth exactly from
`conf_study/conference_runup_PUBLISHED.csv` and corrected each:

| figure | was | now (source truth) |
|---|---|---|
| event day | −0.63% | **−0.56%** |
| D-1 → D+5 | −1.74% | **−1.59%** |
| D-1 → D+10 | −2.00% | **−1.93%** |
| mean D-30 | +5.89% | **+5.53%** |
| ran up 50%+ | 6.5% | **6.2%** |
| ran up 25%+ | 15.8% | **15.7%** |
| fell 25%+ | 8.4% | **8.6%** |
| std dev | 33.6% | **33.5%** |

Three of these lived in the **JSON-LD FAQ** — the surface Google and AI crawlers read, where a
stale number outlives the page.

### The audit was wrong on one point, and it matters
> *"the cap-tier table cannot be reconciled at all"*

It reconciles **exactly**. The audit compared against `cap_tier_final` (841 rows) in
`conference_runup_FULL_v2.csv`. The page's table comes from **`cap_tier_pit`** — the
*point-in-time* column — in `conference_runup_PUBLISHED.csv`: nano 108 · micro 260 · small 298 ·
mid 116 · large 323 = **1,105**, with **exactly 320 null**, matching the page cell-for-cell
including all five medians. `cap_tier_final` is the **superseded hindsight column** that
`/corrections` already publicly disowned — the audit measured against the retracted methodology.

### What was actually wrong there was worse
The JSON-LD FAQ mixed **three different cuts in one answer**:
- nano **−7.11% (n=121)** → from `conference_runup_FULL_v3.csv`
- small **+3.28%**, micro **+2.14%** → from **`cap_tier_final`, the hindsight column**
- the table beside it → from `PUBLISHED.cap_tier_pit`

So the structured data told Google and every LLM that **micro-caps "fare best" (+2.14%)** using a
methodology the site had itself retracted. On the correct point-in-time tiers micro-caps are
**negative (−1.95%)** — the claim inverts. Rewritten from the one canonical dataframe:

> nano **−7.86% (n=108)** · mid **+3.45% (n=116)** · small **+2.75% (n=298)** · micro **−1.95% (n=260)**

### Disclosure added (the audit's valid underlying point)
The cap-tier table covered 1,105 of 1,425 presentations and never said so. Now stated plainly:
market cap at presentation date is known for **1,105 of 1,425**; the other **320** are excluded and
the rows sum to 1,105, not 1,425.

**Guard:** `tests/test_research_figures_match_source.py` recomputes every published figure from
`PUBLISHED.csv` and fails on drift; bans the superseded −7.11 / +2.14 / +3.28 from being presented
as **current** while still allowing them as the "before" value in a correction narrative
(context-aware, same pattern as the SEO guard). Both behaviours verified.

---

## ⚠️ One discrepancy left for you — `/corrections` says −7.11%

The `/corrections` log states the nano figure moved *"from −9.84% to −7.11%"*. The **published**
point-in-time cut is **−7.86% (n=108)**; −7.11% (n=121) came from the intermediate `FULL_v3` cut.
I aligned the **research page's** methodology note to the published value, but I did **not**
retroactively edit the corrections log — silently rewriting a published correction is exactly the
thing that log exists to prevent. Your call whether to amend it with a dated note.

---

## Guard suite now 7, all passing
`research-figures-match-source` · `api-precision-honesty` · `no-ticker-fanout` ·
`no-fabricated-conferences` · `crawler-no-regression` · `seo-invariants` · `si-display-cap`

## Remaining from AUDIT_2026-07-19
| # | Item |
|---|---|
| 4 | 🔴 **P0-D** — `/conferences` says "256 presentations" (study says 1,425); only 2 of 14 conferences show a presenter; the restored 715-row/39-conference dataset is still unpublished; `"1 presenters"` pluralisation bug |
| 5 | 🟠 Homepage `ItemList`/`Event` schema (zero structured data on the highest-authority page) |
| 6 | 🟠 `as_of` off-by-one; `/api`→`/developers`; **13** null-drug rows (audit said 10); `NVCR` has a non-ISO date `2026-Q4`; auto-flip past-dated estimates to "Awaiting data" |
| 7 | 🟠 Differentiate `/` from `/calendar` to resolve the canonical conflict |
