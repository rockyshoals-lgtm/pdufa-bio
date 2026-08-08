# 2026-07-20 — P0-A was incomplete. Fixed sitewide, plus P1 items.

## 🔴 The important finding: P0-A only fixed the data layer

Yesterday I removed the fan-out rows from `api/data.js` and reported P0-A closed. **It was not.**
The homepage, screener, August calendar and condition pages are **static pre-rendered HTML with
the events baked in** — the same no-generator debt as `/calendar`. So:

> **The live homepage was still showing ALPMY, BNTX and CTMX on the 2026-08-17 Keytruda + Padcev
> decision** — the exact defect the audit called "the most serious accuracy defect found in this
> engagement" — on the highest-authority page on the domain.

Worse, because the data layer had been corrected, the *real* sponsors were gone from those pages
while the three wrong companies remained.

**Lesson recorded:** fixing `api/data.js` does not fix this site. Every removal has to be swept
across the static surfaces too. Surfaces found carrying the phantoms:

| Surface | What it held |
|---|---|
| `index.html` | 3 rendered event rows (ALPMY, BNTX, CTMX) |
| `screener/index.html` | an **embedded JSON dataset** with 10 stale rows |
| `calendar/2026/august/index.html` | a row **and** JSON-LD `ItemList` entries |
| `condition/cancer/index.html` | a row |
| `index_redesign.html` | a row |
| `pdufa/{BNTX,CTMX,EVAX,MIRM,ALPMY}/` | 5 standalone detail pages |

**All cleaned, deployed, verified live.** The phantom detail pages are retired and 301'd:
BNTX/CTMX/EVAX/MIRM → `/calendar` (never real events); **ALPMY → `/fda-decision/MRK-2026-07-10`**
(real co-owner, decided event). Screener JSON re-validated (396 rows parse). August JSON-LD
re-validated. Sitemap 528 → **523**.

Also purged from the screener while there: the decided **MRK/PFE 2026-08-17** rows and the
**ONC/RPRX** non-applicant rows.

---

## 🟠 #5 — Homepage event schema: DONE
The highest-authority URL emitted `WebSite` only and **zero** `Event` data while rendering the
next decisions with dates and tickers. Now carries an `ItemList` of **7 `Event`s** built from the
rows it actually renders (so it cannot drift from the page), each with `startDate`,
`eventStatus`, FDA as `organizer`, and a "facts only, not investment advice" description.
Verified live: `numberOfItems: 7`, 7 `"@type":"Event"` in the page.

The count is 7 rather than 10 because three of the ten rows *were the phantoms*.

## 🟠 #6 — `/api` 404: DONE
The nav labels a link "API" and `/api` returned **404**. Now **301 → `/developers`** (verified 200).

## 🟠 #6 — `as_of` off-by-one: NOT a bug
The audit saw `as_of: "2026-07-20"` on 2026-07-19 and read it as tomorrow's date. Checked live:
`as_of` and `refreshed_utc` both track the **UTC** date, and the endpoint is refreshed by cron
five times daily. On 2026-07-20 it reads `2026-07-20` with `refreshed_utc: 2026-07-20 17:49 UTC`.
The audit was run from a timezone behind UTC. **No change made** — stamping UTC is correct for a
data feed; if anything is owed here it is a one-line note on `/developers` that timestamps are UTC.

---

## Guard suite: 7, all passing
no-ticker-fanout · api-precision-honesty · research-figures-match-source ·
no-fabricated-conferences · crawler-no-regression · seo-invariants · si-display-cap

> **Gap the guards still have:** every one of them reads the **data layer**
> (`api/data.js`, `dataset.mjs`, the CSVs). None reads the **static HTML**. That is precisely why
> P0-A looked closed while the homepage was still wrong. A `test_static_pages_match_slate.py` —
> asserting no rendered `/pdufa/{TICKER}` row exists that is absent from the slate — is the
> missing guard, and I would make it the next thing shipped.

---

## Remaining
| # | Item |
|---|---|
| 6 | **13 null-drug rows** (MRK, GSK, IONS, CYTK, COGT, ANAB, GILD×2, NVCR, NUVB, IBRX, ARQT, PHVS) render a decision with no drug; **NVCR** carries a non-ISO date `2026-Q4`; past-dated estimates should auto-flip to "Awaiting data" |
| 7 | Differentiate `/` from `/calendar` to resolve the "Duplicate, Google chose different canonical" flag |
| — | `test_static_pages_match_slate.py` (see gap above) |
