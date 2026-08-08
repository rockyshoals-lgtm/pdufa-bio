# BIOTECH_ENGINE — catalyst analyzer (port target)

Reference UI: `/assets/biotech_catalyst_analyzer.html` ("The Anatomy of Alpha: Biotech Catalyst Analyzer").

## What it is today
A **client-only** dashboard. It opens a WebSocket to `/ws` on its host and renders whatever JSON array is
pushed. There is **no backend, no scoring, no data source** in the file. Two panes:
- **High-Score Alerts** — names with `hype_score ≥ 75`.
- **Biotech Watchlist (30–180 day catalysts)** — all names, sorted by `hype_score`, click → modal with score breakdown.

## Data contract (what the UI already expects)
The frontend consumes an **array** of objects with this exact shape (from the uploaded JS):
```jsonc
{
  "ticker": "ABCD",
  "name": "Company, Inc.",
  "price": 12.34,
  "changesPercentage": -1.2,        // note the 's' — matches the UI field
  "marketCap": 1200000000,          // shown as $B
  "hype_score": 0-100,              // drives sort, color, and the ≥75 alert
  "pdufa_date": "2026-09-15",       // days-until computed from this
  "breakdown": { "Driver label": "value", "…": "…" }   // shown line-by-line in the modal
}
```
Color tiers: `>75` red, `>50` yellow, else green. Alert threshold: `hype_score ≥ 75`.

## Retool
1. **Drop the WebSocket.** Replace `App.ws.connect()` with a **poll of Supabase `latest_snapshot` where `engine='biotech'`** every ~30–60s (same pattern as the momentum tab). Simpler and needs no socket server. Keep the existing card/modal rendering.
2. **Feed it from ODIN.** Populate `hype_score` / `pdufa_date` / `breakdown` from the ODIN biotech engine; `price` / `changesPercentage` / `marketCap` from FMP `quote`.
3. Publish the array as the `payload` for `engine='biotech'` on the same cadence design (biotech data moves slowly — a **daily** or hourly refresh is plenty; it does not need the 60s fast lane).

## ODIN integration — sources (⚠️ confirm before building)
ODIN is the biotech PDUFA scoring engine and lives **separately** from the momentum scanner:
- Engine + data: `9realms\Odin Perfection\` (and caches like `catalysts_out\`, `odin_catalyst_scan_output\`).
- MCP tools available in this workspace: `odin_score`, `odin_rank` (plus `odin_score_v16/v19`), `system_status`. `odin_rank` can produce a ranked list of scored PDUFA events.
- Site already ships a `historic.json` in `pdufa_site_src\` — check whether a forward PDUFA calendar already exists there or in `catalysts_out\`.

**Open decision (needs the owner's confirmation):**
- **Which PDUFA calendar** feeds the 30–180 day watchlist? (a file/table in `Odin Perfection\` / `catalysts_out\`, the site's own calendar data, or generated live via `odin_rank`.)
- **What maps to `hype_score`?** Candidates: ODIN approval **probability × 100**, or the ODIN **tier/investment score**. Pick one and keep it consistent. `breakdown` = the top ODIN score drivers for that event (feature contributions / designations / sponsor track record, etc.).

Until that's confirmed, the biotech tab can ship as a **stub** (BUILD_SPEC Open Decision #2) — momentum tab goes live first, biotech wires in once the calendar + score mapping are pinned.

## Keep separate from momentum
This engine is the biotech/catalyst world (ODIN / GUNGNIR / BIFROST). It shares only the **delivery
plumbing** (Supabase store + Vercel frontend). Do **not** couple the scoring code paths — the momentum radar
is a standalone whole-market tool. Same disclaimer applies: informational/educational only.
