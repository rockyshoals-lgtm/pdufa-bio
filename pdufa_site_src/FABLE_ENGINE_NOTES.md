# pdufa.bio — new scanner engine (Fable, 2026-07-03) — BUILD & STAGE (do NOT deploy without David's "go")

Backed by the LEADLAB study (`Momentum Scanner/research/leadlab/LEADLAB_FINDINGS.md`).
The odds are now **unbiased base rates** (winners AND losers, incl. delisted names), and the
board can go live **pre-market** — the earliness unlock.

## What changed
- **`lib/scoring.mjs` + `lib/scoring_grid.json`** (NEW) — the empirical `P(+25% intraday)` surface
  (open gap×relvol and pre-market move×relvol), plus `scoreOpen()`, `scorePremarket()`, `classify()`.
  Tiers tuned "earlier, accept more noise": **PRIME / BUILDING / WATCH / NOISE**, with flags
  **ROCKET** (move AND heavy volume), **VOL_NO_PRICE** (volume before price — early tell),
  **EXHAUSTION_RISK** (huge move, thin volume), **CONTROLLED**. Emits legacy tier names too, so the
  current UI keeps working.
- **`api/surges.js`** (REWRITTEN; backup `api/surges.js.bak_fable`) — regular-session board now scores
  off the unbiased grid instead of the survivorship table. Min move lowered 8%→5% (earlier). Falls back
  to move-only when FMP `avgVolume` is null (it usually is).
- **`api/premarket.js`** (NEW) — pre-market board, 4:00–9:30am ET. FMP `batch-aftermarket-quote` over a
  candidate watchlist (prior-session movers/actives) → pre-market move vs prev close → pre-market grid.
- **`api/build-watchlist.js`** (NEW) — nightly cron: pulls the Unusual Whales screener
  (`/api/screener/stocks`) for small-caps' 30-day avg volume → caches an **ADV map** in KV. This is what
  turns on pre-market **relative volume** (and thus the 91.8% confluence signal). Needs `UW_API_KEY`.
- **`surges.html`** (PATCHED; backup `surges.html.bak_fable`) — the pre-market window now renders the live
  pre-market board (was a blank "opens at 9:30"); copy updated to the unbiased-base-rate + pre-market framing.
- **`vercel.json`** (PATCHED; backup `vercel.json.bak_fable`) — added `/premarket` route, pre-market cron warms,
  and the nightly `build-watchlist` cron; both APIs `noindex`.

## Env vars needed in Vercel (names only)
`FMP_API_KEY` (already set), `UW_API_KEY` (for the ADV map / confluence), `KV_REST_API_URL/TOKEN`
(or Upstash — already set), and `CRON_SECRET` (guards `build-watchlist`). No secrets are committed.

## Deploy (David's machine only)
```
cd 9realms\pdufa_site_src
vercel --prod
```
Then hit `/api/build-watchlist?key=<CRON_SECRET>` once to seed the ADV map, and check
`/api/premarket` during pre-market and `/api/surges` during the session.

## Verified (real data, this session)
- `lib/scoring.mjs` self-test + cross-module import resolve.
- `api/surges.js` end-to-end on real FMP gainers (scores + flags correct; move-only fallback confirmed).
- `api/premarket.js` end-to-end on real FMP aftermarket quotes (pm move + THIN + EXHAUSTION flags correct).
- `node --check` passes on all three API files; `vercel.json` is valid JSON.

## Still pending (in priority order)
1. **Seed the ADV map** (`UW_API_KEY` + run `build-watchlist`) → unlocks pre-market rel-vol + confluence ROCKET. Biggest remaining signal.
2. **Extend the base-rate history** — re-run `pull_grouped.py` for more months/quarters, `build_universe.py`, `make_grid.py`, drop the new `scoring_grid.json` into `lib/`. The grid is a drop-in.
3. **Confirm the UW screener response field name** for 30-day avg volume (`avg30_volume` assumed) against a live call before relying on the map.
4. Optional: true market-cap filter (Polygon grouped-daily has no shares outstanding; current small-cap filter is a price/mcap proxy). Wire mcap from the UW/FMP map.
5. Optional UI: distinct pre-market styling + the new PRIME/BUILDING/WATCH labels (engine already emits `tier_new`).
