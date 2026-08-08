# LEADLAB Delivery — Momentum Leading-Signal Engine for pdufa.bio
**From:** Fable (research)  ·  **For:** the builder agent  ·  **Date:** 2026-07-03
**Status:** research complete, engine written + self-tested on real data, STAGED not deployed.

## TL;DR for the builder
The surge scanner now scores off **unbiased base rates** (winners AND losers, incl. delisted
names) and can run **pre-market** — catching movers ~30–90 min before the old "+8% intraday"
trigger. The engine files are already written and verified; your job is to **review, integrate,
and stage for David's deploy** (owner-gated). Full build specs are in `specs/` (also copied to
`pdufa_bio_build/INBOX/`), numbered by priority.

## The result (why this matters)
Of every small/micro-cap that eventually surged +25% intraday, **83% were already up ≥10% by
9:00am**. Confluence — **pre-market move ≥10% AND rel-vol ≥3× → 91.8%** hit +25%. And only
**9.9%** of *all* ≥3% gap-ups actually surge, so gap×volume is what filters noise. Details +
red-team in `LEADLAB_FINDINGS.md`.

## What's in this folder
- `LEADLAB_FINDINGS.md` — the research report (data, base-rate tables, earliness, red-team, caveats).
- `scoring_grid.json` — the empirical P(+25% intraday) surface the engine embeds.
- `FABLE_ENGINE_NOTES.md` — build + deploy notes, env vars, verification, pending items.
- `staged_engine/` — the ready engine files (identical to what's staged in `pdufa_site_src/`):
  - `lib/scoring.mjs` + `lib/scoring_grid.json` — scoring module + grid.
  - `api/surges.js` — rewritten regular-session board (backup at `pdufa_site_src/api/surges.js.bak_fable`).
  - `api/premarket.js` — NEW pre-market board.
  - `api/build-watchlist.js` — NEW nightly UW ADV-map / watchlist cron.
- `specs/` — numbered, build-ready specs (SPEC_FORMAT compliant). Same files are in `pdufa_bio_build/INBOX/`.
- `research/` — reproducible pipeline: scripts + `universe.csv` (5,810 unbiased events),
  `premarket_features.csv` (641 events), and the grid builder. Re-runnable to extend history.

## Source of truth
The live deploy source is `9realms/pdufa_site_src/`. The `staged_engine/` copies here are for
reference/review. `vercel.json` in `pdufa_site_src/` is already patched (routes + crons); backup
at `vercel.json.bak_fable`.

## Ground rules (unchanged)
Real data only · educational, NOT investment advice · API keys via env vars only · no deploy
without David's explicit go.
