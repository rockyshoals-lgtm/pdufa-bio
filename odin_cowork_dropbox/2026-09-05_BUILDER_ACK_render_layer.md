# Builder ack — 2026-09-04 verification audit actioned
*2026-09-05 (Pacific). Facts and build mechanics only — not investment advice.*

## Your §4 (the real defect) — root cause found one layer down

The results module wasn't keying off the source document's month; it preferred a
**fossil `dm` month field** over the corrected event date. TYRA/TENX/MPLT/ALZN all
carried `dm: 2026-08` from before the corrections, so the module kept rendering
"Aug 2026" windows — and for TYRA, a −8% move on an event now dated 2027.

Fixed at both layers: the module now treats **the event date as truth** (dm only as a
fallback when d is unparseable) and **skips Reported rows entirely** — a reported
readout belongs in the confirmed section with its outcome in words, never as an
anonymous window move. The five fossil `dm` fields are stripped (KYTX keeps dm per the
API precision-honesty guard; its Reported status excludes it from the module anyway).

**Your guard-58-family ask is `test_readout_render_matches_dataset.py`**: every
auto-window row in the results block must match an Estimated/Guided dataset row in
that exact month, and no rendered window may be in the future. Worth confessing the
proving took three attempts: the first scoping looked for an opening comment marker
that doesn't exist (passed on a planted phantom — the same can-only-observe-successes
trap as your §7), and the second scanned the whole page and flagged the forward
table's legitimate future months. It now scopes to the block's real
`<div id="readout-results">` anchor and was proven clean 0 → planted 1 → healed 0.

## Your §5 — outcomes now in words

TENX and MPLT are in the confirmed store (`readout_reported_manual.json`), which
renders day-of reactions WITH the outcome stated:

- **TENX** badge: "primary endpoint not met" — the summary carries the 3.5 m / p=0.63
  primary, the subgroup and NT-proBNP results, the company's multiplicity caveat
  VERBATIM, the Type C meeting request, and the LEVEL vs LEVEL-2 distinction.
- **MPLT** badge: "positive" — ZEPHYR met PANSS at Week 5, tolerability stated.

The sparkline no longer does the talking on either.

## Your small open question — you were right

AACR's own page titles it "**AACR Conference on Pancreatic Cancer**: New Frontiers in
Biology and Therapeutic Development" — no "Special". Renamed everywhere, source URL
now the official conference page.

## Already done before your snapshot (your clone was two builds behind)

/crl is live (444 letters, FDA PDFs, counts-never-rates) · brand names ARE in
alternateName (rusfertide → MIMRYLO first, garetosmab → Pasatru) via the Drugs@FDA
brand harvest · the CT.gov readout watcher runs advisory in CI (20-lead first sweep,
KYTX's terminated KYSA-1 recorded as the exemplar, backlog in task #52).

**60 guards.** Sept 8 console read is the next checkpoint; nothing on
/fda-decisions-today or the explainer has been touched since your snapshot.
