# P0-D — /conferences: closed, deployed, verified live

## Fixed
| Defect | Now |
|---|---|
| Promo card cited **"256 presentations"** | **1,425** — the real study n |
| **"1 presenters"** pluralisation bug | "1 presenter" / "0 presenters", correct on all 14 |
| Only **2 of 14** conferences showed any presenter figure | **All 14** carry an accurate count |
| ESC + ESMO showed **"1 presenter"** with nothing behind it | Both **0** — the dataset has zero rows for either upcoming meeting |
| Restored 715-row dataset unpublished | Published — announced presenters **and** per-conference history |
| API served **n=256, median −0.23%** on every conference | Aligned to the published study: **n=1,425, median −0.03%** |

Live: 14/14 cards show a count; ASH, CTAD, SABCS, SITC show **1 presenter** each; detail pages
list the company and the history block.

## The audit's premise needed correcting
> *"The restored 715-row / 39-conference crawler output has not been published."*

Implying publication would fill the upcoming calendar. It does not. **The dataset is
overwhelmingly historical:** of 715 rows, only **4** are dated today or later — one each for ASH
(CRSP), CTAD (CRVO), SABCS (OLMA), SITC (BOLT). ESMO has 67 rows, every one from the 2023, 2024
and 2025 meetings and **none** for the upcoming Oct-2026 meeting.

That is not a gap in the data, it is the calendar working as intended: abstract lists are released
close to the event, which is exactly what the detail pages already said honestly — *"Presenter list
populates as abstracts are released."*

**So the presenter mapping for upcoming conferences genuinely does not exist yet**, and publishing
four names is all the data honestly supports. Claiming otherwise would have been the same class of
error as the fabricated conference dates.

## What the dataset *is* good for — now published
The unpublished value was the **history**, and it is substantial. Each conference detail page now
carries a sourced coverage line, e.g.:

> **ASH** — 49 biotech presentations by 38 companies across 3 past meetings (2023–2025)
> **ESMO** — 67 presentations by 50 companies across 3 meetings
> **SITC** — 32 by 25 · **AASLD** — 20 by 14 · **ACR** — 13 by 13 · **SABCS** — 11 by 10 ·
> **ECTRIMS** — 10 by 5 · **ASN** — 9 by 7 · **WCLC** — 8 by 8 · **CTAD** — 2 by 2

Every figure counted from `catalysts_out/conference_presentations_history.csv`. Each links to the
run-up study. **ESC gets no history block — it has zero rows, so it says nothing.**

## Bonus defect found: the API contradicted the page again
Every Conference record shipped `cohort_n: 256, median −0.23%` — *identical across all 14*, so not
a per-conference statistic at all. It matches **no defensible subset** of the published study (the
14 tracked conferences are 589 rows, not 256); it was the same stale cut the promo card was
quoting. Realigned to the published figures with explicit provenance:

```json
{"window":"D-30 to D-1","anchor":"conference start","median_pct":-0.03,"n":1425,
 "source":"/research/conference-runup","scope":"all tracked conference presentations 2017-2026"}
```

That is the third API-vs-page divergence this pass (after P0-B's precision and P0-C's figures) —
the audit's own conclusion holds: *the site tells the truth; the data feeding it does not always.*

## Files
`fix_conferences_p0d.py` (idempotent, `--dry-run`) · `conferences/index.html` ·
`conference/{14}/index.html` · `api/v1/dataset.mjs`

## Guard suite: 7, all passing
research-figures-match-source · api-precision-honesty · no-ticker-fanout ·
no-fabricated-conferences · crawler-no-regression · seo-invariants · si-display-cap

---

## All four P0s from AUDIT_2026-07-19 are now closed
| | Item | Status |
|---|---|---|
| 1 | Ticker fan-out (BNTX/CTMX/EVAX/MIRM + 4 more found) | ✅ live, guarded, `/corrections` |
| 2 | API day-precision on 299 month estimates | ✅ live, guarded |
| 3 | conference-runup figures from one dataframe | ✅ live, guarded |
| 4 | /conferences 256→1,425 + presenter data | ✅ live |

## Remaining (🟠 P1/P2)
| # | Item |
|---|---|
| 5 | Homepage `ItemList`/`Event` schema — highest-authority page emits zero event structured data |
| 6 | `as_of` off-by-one · `/api`→`/developers` 404 · **13** null-drug rows · `NVCR` non-ISO date `2026-Q4` · auto-flip past-dated estimates to "Awaiting data" |
| 7 | Differentiate `/` from `/calendar` to resolve the canonical conflict |
