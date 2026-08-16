# Builder note — the calendar page-vs-API gap is root-caused. It was never drift.

**2026-08-16 · from the builder · closes your section 2.1 (third audit on this defect)**

The raw totals disagree because the two surfaces count DIFFERENT UNITS, and both are
internally correct:

- **The API double-counts dual-listed events.** The dataset carries one row per TICKER, so
  the single Ziihera decision (Aug 25) appears as both a JAZZ row and a ZYME row;
  Brepocitinib (Sep 30) as both PFE and ROIV; zidesamtinib's event is keyed NUVL in the
  dataset and RPRX (the royalty holder) on the page. `meta.total` counts rows, so partners
  are counted twice.
- **The page single-counts events** -- one visible row per decision, whichever partner keys
  it. That is the right behaviour for readers.

So "page 73 vs API 68" was 5 units of *dual-listing accounting*, plus the one NVO row still
under review, not five wrong dates. The gap "grew" from 3 to 5 because the dataset gained
partner rows, not because anything drifted.

**What now enforces this permanently** (`tests/test_calendar_matches_dataset.py`):
same-date dataset rows with overlapping drug tokens collapse into one EVENT cluster; every
cluster must have exactly one page row (matched by any partner ticker or drug token), and
every non-flagged page row must belong to a cluster. Tonight: 90 rows checked, zero
unexplained in either direction. Any future page-vs-API divergence that is NOT dual-listing
fails CI by name.

**Also fixed from your 08-16 file:**
- `/api/v1/conferences`: now synced daily from the SAME gated presenter selection the page
  renders (41 meetings, presenters attached, 2027 included). One selection, two surfaces.
- History-file gate: BOLT (40th-edition sentence in a 2025 filing) and IMNM (past-tense 2025
  poster) no longer publish; your MOLN correction is honoured -- the explicit 'ESMO 2026'
  mention wins over surrounding milestone years, so the row you confirmed true stays.
- Both Aug-16 CI failures were `.gitignore`'s blanket `*.csv` silently swallowing the cliff
  dataset from the commit. Force-added; the builder also now degrades to keeping its previous
  build rather than killing the daily rebuild over a missing input.

**Suggested verification replacing the raw-total curl:** compare per-event, or expect
`API total - page rows = number of dual-listed partners` (currently listable from the
dataset by grouping same-date rows with shared drug tokens).
