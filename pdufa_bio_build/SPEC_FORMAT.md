# How to hand the builder actionable specs (for the research-assistant Claude)

The builder actions items from `INBOX/`. To make a spec build-ready, drop **one Markdown file
per topic** into `INBOX/`, named `NN_topic.md` (e.g. `01_data_source.md`, `02_scoring.md`,
`03_ui_alerts.md`). Number them by priority order.

## Each spec file should contain
- **Goal** — one sentence: what this enables on the site.
- **Data source** — exact, real, verifiable: endpoint URL(s), the field names to read, auth
  (which key/env var — do NOT paste secrets, name the env var), rate limits, refresh cadence.
- **Logic / scoring** — concrete formulas and thresholds (not "make it good"). If it's a score,
  give the components, weights, and the 0–100 mapping.
- **UI / UX** — what it looks like and how it behaves, tied to the example's formatting
  (dark theme, cards, alert rail, modal). Screenshots/sketches welcome.
- **Acceptance criteria** — a short checklist the builder can verify ("renders < 1.5s",
  "alerts fire at score ≥ X", "handles empty feed gracefully").
- **Priority** — P0 (blocks launch) / P1 / P2.
- **Deploy / key needs** — flag anything that needs a new API key, new serverless function,
  cron change, or a live deploy. These are **owner-gated** (David's go) — the builder will
  stage, not ship, them.

## Ground rules (shared with the builder)
- **Real data only** — verifiable endpoints/fields; no invented tickers/metrics. Mark anything
  unverified as UNVERIFIED and the builder will gate it.
- **Not investment advice** — the site stays informational; keep disclaimers + the Cardinal Rule.
- **Fast + faithful** — better and faster than the uploaded example, same formatting.

## Handoff loop
1. Research Claude writes specs → `INBOX/NN_topic.md`.
2. Builder reads `INBOX/` at the start of each build session, actions in priority order, and
   logs progress in `BUILD_NOTES.md` (moving actioned specs to `INBOX/done/`).
3. Anything needing deploy or a key waits for David's explicit go.
