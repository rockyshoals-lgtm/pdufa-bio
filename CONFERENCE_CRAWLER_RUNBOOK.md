# ConferencePresentation crawler — built 2026-07-11 (P2-1)

**The moat leak is closed.** The pipeline now harvests *who presents where*, continuously.

## Files
| File | What |
|---|---|
| `conference_presentations.py` | The extractor — alias table, presentation-type detection, date resolution |
|  `conf_registry.json` | 43 conferences with per-year dates, **derived from our own 1,425-event history** (not hardcoded) |
| `catalyst_crawler.py` | Wired in: new `ConferencePresentation` type + 3 new schema columns |

## Run it
```bash
python3 catalyst_crawler.py --tickers your_universe.txt --out ./catalysts_out
```
Two outputs:
- **upcoming** presentations → the normal catalyst feed (`catalysts_public.csv`)
- **everything incl. history** → `catalysts_out/conference_presentations_history.csv` (append + dedupe)

That second file is the point. History is what makes this a **compounding asset** rather than
another snapshot. Every run deepens the conference study.

## The three design decisions worth knowing

**1. The date comes from the conference, not the filing.**
A PR says *"XYZ to present Phase 2 data at ASCO 2026"* and almost never states a date. So we detect
the *conference*, then resolve the date from the registry. Two precisions:
- `date_basis=observed` → we have that conference-year in the registry → **day** precision, confidence 0.75
- `date_basis=projected` → we know the conference's typical week but not that year's exact date →
  **month** precision, confidence 0.55

We never invent a specific day. We know EHA is mid-June; we don't claim to know it's the 14th.

**2. Search on the conference name, not on "to present at".**
The generic verb drags in every investor-conference 8-K on EDGAR — Liberty Media, Labcorp,
insurance carriers. Anchoring on the meeting name (`"American Society of Clinical Oncology"`)
returns almost exclusively biotech PRs. Verified: 22 hits from 40 docs, all real biotechs
(Vir, BioNTech, GRAIL, Legend, Fate, Immatics, Cardiff Oncology), orals correctly detected.

**3. Conferences get a strict date test — no PDUFA grace window.**
`is_upcoming()` deliberately keeps a recently-passed PDUFA for 45 days so its outcome
(approval/CRL) gets captured. A conference has **no pending outcome**: once it's happened it is
*history* (→ the study), not *calendar*. Using the shared helper would have put a June ASCO on the
July calendar. Caught in testing.

## What it records — and what it refuses to
Records the **facts**: conference, presentation type (oral / late-breaking / plenary / poster),
abstract number, date + how we know it.

It does **not** weight, score, or rank them. Presentation type is a fact about selectivity, not a
signal. **Conference Overlay v1.0 is RETIRED/REFUTED** — it claimed nano/micro +4.88% when the
actual nano median is **−9.84%**; `conference_score` now returns a refutation notice.

## Known limits (state these, don't paper over them)
- **Anchor is the conference start**, not the abstract/title-drop date. The abstract drop is itself
  a price event weeks earlier. Dual-anchor is the next upgrade.
- **Selection bias**: we capture presenters who *filed about it*. A company that presents quietly
  won't appear.
- **Projected dates are month-precision on purpose.** Don't upgrade them to day without a source.
- The full SEC backfill is slow (throttled, large 8-Ks). Run it locally, not in a sandbox.

## Next
Backfill the 2026 gaps by running the crawler with `--since 2025-11-01`:
ASCO26 (was 6 events), EHA26 (0), ADA26 (0), ASCO-GU26 (0), ACC (0), ENDO (0).
Then rebuild `/research/conference-runup` from the deepened dataset.
