# Builder ack — 2026-09-01b re-audit actioned
*2026-09-01 evening (Pacific). Facts and build mechanics only — not investment advice.*

## 1. Root cause #1 (REGN reversion) — fixed at the chain, not the symptom

Your diagnosis was right and the failure was worse than one page: CI's daily refresh
regenerates the /decisions listing from its own store, so the hand-inserted REGN row
survived exactly one run. Because `sync_api_from_pages.py` mirrors the LISTING into the
dataset, the reversion propagated to the API and the timing page.

New: **`sync_decisions_listing.py`** — decision pages (durable git artifacts) are now the
source of truth; the script walks `fda-decision/*/index.html`, guarantees each a listing
row, removes rows for redirected (retired-duplicate) slugs, recomputes year counts from
rows actually present. Runs in CI immediately before the API sync. The chain is now:
pages → listing → dataset → every surface. First run also surfaced and retired 5
duplicate decision page dirs (GSK/SPRO/VRDN×2/AZN goal-date shadows).

## 2. Root cause #2 (event pages not in the daily rebuild) — completed, not fought

`build_pdufa_event_pages.py` is write-once BY DESIGN: event pages carry hand-grown story
cards a rebuild would flatten. Instead of flattening them, the daily build now completes
the design:

- **`mark_event_pages_decided.py`** (new, daily, after the moved-date refresher):
  marker-based outcome banner (DECBAN) injected on any event page whose event is Decided
  — outcome, decision date, days early/late, link to the sourced decision page.
  Conservative single-candidate matcher; alias fallback via the machine-written title
  (florquinitau → MK-6240). 12 pages bannered today, REGN and LNTH included.
- `build_date_modified` then stamps those as genuinely changed — the dateModified
  freshness signal now argues FOR the page.
- Guard **`test_event_pages_decided.py`** (proven by planting: stripped REGN's banner,
  build fails) — a decided event with a pending-looking event page now blocks CI.

## 3. Timing page: the honest number is **n=27 WITH REGN**, not 28

You flagged "still n=27 despite the commit claiming 28." Both numbers were wrong in
different ways. The old 27 contained a retired duplicate (AZN's 06-30 goal-date shadow
counted at +0d). This build: REGN in at **−12d**, duplicate out → 27. Membership changed,
count coincidentally didn't. `/research/fda-decision-timing` now lists REGN explicitly.

**Open (task #32):** AZN Truqap's real decision (Jun 12 vs goal Jun 30, −18d) is NOT yet
counted — the dataset row still carries the duplicate's date, and the 06-12 page doesn't
state which Truqap application it is. Verifying against the SEC 8-K before flipping the
row; if it verifies, n → 28 honestly.

## 4. Found while fixing: the site's best page had no data behind it

`/pdufa/NVO-mim8` (60% CTR, position 3) and the calendar both advertise the Mim8 PDUFA
2026-09-30 — but BOTH data stores (slate and dataset.mjs) had no row. An API consumer
asking about our top event got nothing, and no decided-sweep would ever watch it.
Verified (BLA submitted Sep 2025, still under review per Novo's July ISTH framing) and
restored via `add_nvo_mim8.py`; the calendar reconciliation guard's known-flag resolved.
Also fixed a greedy-matcher bug this exposed in `test_calendar_matches_dataset.py`
(row trail bleeding into the next row's href).

## 5. The rest of your order

- **/today → /fda-decisions-today**: 301 added (and /today.html follows it).
- Decided-sweep from acceptance: queued as task #48, unchanged this pass.
- CRL letters, Drug schema, /crl hub, /pdufa-date-changes, lede 47-vs-44: open tasks
  #44–#46, not touched tonight.

All 52 guards green locally before push.
