# `latest\` — the live feed. Builder: READ THIS FOLDER, not the dated snapshots.

This folder is refreshed automatically by the final step of David's readout chain
(`READOUT_RESEARCH.bat`, step 7/8) every time it runs — typically every few days, sometimes
several times a day. Check `manifest.json` first: it carries the publish timestamp
(**local Pacific**), per-file row counts, the GOLD/FIRM/SOFT split, the number of conflict
rows awaiting human review, and how many dates were pulled EARLIER since the previous BPC
export. If `published_at` is older than ~4 days, ping David to run the chain.

| file | what it is |
|---|---|
| `readout_gold_dates.csv` | **THE PUBLISHABLE SET.** Every forward catalyst, graded. Ingest this. |
| `conference_presenters.csv` | Our EDGAR presenter miner (fresh, small/mid-cap edge). |
| `readout_date_drift.csv` | Dates that MOVED between the two newest BPC exports. `moved=EARLIER` rows are urgent — the catalyst arrives sooner than any calendar built on the old file. |
| `readout_calendar.csv` | Merged working view with smart-money columns (context). |
| `readout_forward.csv` | Raw EDGAR guidance rows with `window_precision`. |
| `ctgov_readouts.csv` | CT.gov primary-completion dates with `pcd_precision`. |
| `conf_registry.json` | Observed congress dates (source of all conference DAY dates). |

## Rendering rules (unchanged, non-negotiable — full rationale in `..\2026-08-29g_READOUT_CONFERENCE_PIPELINE_HANDOFF.md`)

1. `precision` below `DAY` is a bucket. Render "Q4 2026" / "September 2026" / "2H 2026" —
   **never a fabricated calendar day**.
2. `confidence`: GOLD = externally checkable (congress agenda / FDA-assigned) — publish as a
   hard date. FIRM = company-stated day in an SEC filing — publish with attribution.
   SOFT = bucket only.
3. `conflict` non-empty = two sources disagree on the same drug — surface it, never silently
   pick one.
4. Every catalyst page carries the disclaimer: informational/educational, not investment advice.

The dated `..\data_2026-08-29\` folder is a frozen snapshot from the day the pipeline was
handed off. Useful as history; already stale. This folder is the feed.
