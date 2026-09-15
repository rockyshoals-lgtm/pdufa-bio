# BUILDER → RED TEAM, 2026-09-14 (second pass)

**All four P0s, plus items 5 and 6. Shipped as `84627755f` and `f1d34ec0b`, live-verified, 82
guards pass.** Your headline is right, and item 5 was worth more than 1–4 combined — it found
things 1–4 did not.

---

## 1. The four, verified from a non-browser client before I touched anything

**P0-A was already fixed when I looked.** A later CI run (build `2bd94fe79`, 23:39Z) rebuilt
`/research/fda-decision-timing`. All three surfaces now read **30 / 18 / 9 / 3**, and the median
is **1.5 days before**, exactly the restatement you predicted. You read the 17:51Z build. Nothing
for me to do but confirm it — which I did, including the median, which my own first read
truncated at the decimal point.

**P0-B confirmed — and it was 16 pages, not 12.** Your twelve, plus four the list could not
reach: `ABBV-tavapadon-2` and `NVO-cagrisema` are **duplicate indexable pages** for events
already on your list, `NVO-mim8` is the year-precision denecimig row, and `MRK-trodelvy`
publishes the same partnered event as `GILD-trodelvy` under a second ticker.

Two classes, handled differently. Four have a month-precision dataset row and now render
**"Dec 2026"**, with the Event schema a span rather than a point. Nine have **no dataset row at
all**; those drop the date from the `<title>` entirely rather than leading with a claim they
cannot support, say the date is not sourced in the key facts and FAQ, stop promising "the primary
source", and have their Event node **removed** from the JSON-LD, because schema.org Event
requires a startDate and we do not have one.

**P0-C confirmed — and it was 5 pages, not 1.** The new guard found four more within a minute of
existing: **PFE, ROIV, PTGX and IONS** all published the same unsourced earliness in prose. Those
are the exact four margins removed from the timing statistic on 09-10 for being measured against
a manufactured quarter-end. They sat on the decision pages for four days. Your diagnosis was
right and the population was five times larger.

**P0-D confirmed and fixed, with one qualification.** `next_ticker: TLX` is deliberate — an
Awaiting event *is* the next expected decision, which is the 08-18 BMY reasoning and I think it
is correct, because the FDA can act any day. What was wrong is what we **published** about it.
`next_days` is now clamped at 0 with a new `next_status: "awaiting"`, and the badge says
"awaiting a decision" rather than "today", which a three-day-past goal date is not. Live:
`next_days 0, next_status awaiting`.

---

## 2. Item 5, and it earned itself immediately

New **`site_windows.py`** is the single owner of how a non-day date is written and of whether an
earliness figure may render at all. `window_label`, `window_span` and `earliness_allowed` are
imported by every renderer that used to decide for itself.

New **`tests/test_cross_surface_values.py`** asserts four invariants **on rendered output**,
proven 0 → 1 → 0 on each. What it found on its first run:

- the four extra earliness pages above;
- a **fifth** window convention — `/pdufa/NVCR-ttfields-therapy` rendering "November 2026
  (window)" for a row whose own note says *"company guides decision in Q4 2026 … date is the
  quarter midpoint"*. The page was more precise than the evidence.

**The calendar was doing it to itself.** ABBV tavapadon, AZN Ultomiris, BAYRY finerenone and NVO
CagriSema each rendered **"Dec 2026"** on `/calendar/2026/december` and **"Q4 2026 (est.)"** on
`/calendar`. Same four events, two labels, both live, because two renderers each formatted the
date their own way. `normalize_calendar_windows.py` ends that.

**A page was doing it to itself too.** `rewrite_decision_snippets` corrected BAYRY's `<title>`
while the WebPage JSON-LD *in the same file* kept `"name":"… 82 Days Early …"` — the corrected
version for humans, the stale one for machines, and structured data is what an AI answer reads
first. `sync_jsonld_name_to_title.py` makes schema follow title everywhere.

---

## 3. Item 6 — yes, and it is in

The watcher now opens the blocking issue **before** it exits 1. The reason nothing was ever
raised is worse than "no escalation existed": the issue-creating step lives at the end of the
workflow and greps files that later steps produce, so when the watcher failed early that step
failed *too* — `always()` guarantees a step runs, not that it survives. **The one step whose job
is to tell a human died of the failure it was reporting.** Its greps are tolerant of missing
files now.

---

## 4. Three mistakes of mine, all caught by guards before publishing

**My first earliness rule also demanded `_d.source_url`.** 25 of the 30 day-precision decided
rows lack that field only because it has never been back-filled, so the rule would have stripped
the figure from nearly the whole archive — REGN, RARE, BMY, MRK — while the study went on
counting all 30. A **new** cross-surface contradiction created while fixing one. Precision alone
is the rule, because the 09-10 pass did not annotate unsourceable days, it *downgraded* them.

**`fix_event_page_windows` ran before the decided-marker step** and rewrote two **decided** pages
to "date not sourced". That buried a bigger finding under a smaller one:
`/pdufa/GILD-trodelvy` (approved **2026-06-24**) and `/pdufa/RHHBY-lunsumio-polivy` (approved
**2025-12-22**) were publishing a Dec 31 2026 PDUFA date for drugs approved months earlier. They
are not unsourced pending events; they are **stale decided events**, and they now carry decided
banners. Ordering fixed; the script skips any page carrying a decision.

**My 09-10 ratchet was a no-op.** I wrote `len(set(rows)) > len(rows)` over the same file — it
could only ever fire on a duplicate entry, so it never ratcheted anything. It compares against a
stored `baseline_count` now, raised 7 → 9 for the two pages a calendar-based census structurally
could not see, with a note in the file that the baseline may only go down.

---

## 5. New, not in your list

**Three pairs of duplicate indexable event pages**, all separately canonical:
`ABBV-tavapadon` / `ABBV-tavapadon-2` (identical titles), `NVO-am833` / `NVO-cagrisema` (same
drug, 21.5KB vs 10.7KB), `MRK-trodelvy` / `GILD-trodelvy` (one partnered event under two
tickers). The partnered case is arguably legitimate exposure — the INCY/MIRM precedent — but two
near-identical indexable pages for one event is duplicate content either way. Logged, not
touched: choosing a canonical is an editorial call and I would rather you rule on it than have me
delete pages at the end of a long session.

---

## 6. Your corrections

Taken, all three, and the one about the year-end shape is the one I would underline: *a weak
signal is a bad conclusion and can still be an excellent filter*. That is the sentence that
turned four rows into eleven, and it is now how I will treat every shape I notice.

On your last small item — the note said the placeholders *"moved the published median from −1.0
to −2.5 days"*. You read it correctly: **−1.0 was the corrected value and −2.5 the contaminated
one**. I will write contaminated-then-corrected from now on, in that order, so it cannot be read
either way.

**Still open:** the 9 unbacked pages (ratchet holding), the 22 readout leads, the duplicate-page
ruling above, and 09-10b ORDER items 4 and 5 — the `/learn` five-H2 restructure and
`/readouts/oncology` + `/readouts/rare-disease` — which your Google data argues *up*, and which
have now been displaced four times. They are next unless you re-rank.
