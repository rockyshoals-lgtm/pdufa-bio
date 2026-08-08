# 03 — Nightly ADV map / watchlist (unlocks pre-market rel-vol + confluence)

**Goal:** Cache a nightly {TICKER: {adv, mcap}} map so the pre-market board can compute
relative volume — the "move AND volume" confluence that hit +25% intraday **91.8%** of the time.

**Data source:** Unusual Whales stock screener `GET https://api.unusualwhales.com/api/screener/stocks`,
auth `Authorization: Bearer $UW_API_KEY`. Params: `max_marketcap=3000000000`,
`min_underlying_price=0.30`, `issue_types=Common Stock`, `order=volume`, `order_direction=desc`,
`limit=250`, `offset=0..4`. Read `ticker`, **`avg30_volume`** (30-day avg volume — VERIFY field name
on first live call), `marketcap`. Cache to KV key `adv_map` (ex 36h) + `adv_map_built` timestamp.

**Logic:** Implemented in `api/build-watchlist.js`. Auth via `CRON_SECRET` (Bearer or `?key=`).
Iterate 5 pages, build the map, `kv.set('adv_map', map, {ex: 60*60*36})`.

**UI / UX:** None (backend). `api/premarket.js` reads `adv_map` automatically.

**Acceptance criteria:**
- [ ] `GET /api/build-watchlist?key=$CRON_SECRET` returns `{built, names, pages}` with names in the hundreds+.
- [ ] Wrong/missing secret → 401. Missing `UW_API_KEY` → 500 with clear error.
- [ ] After a run, `/api/premarket` shows `relvol_enabled: true` and populated `relvol`.
- [ ] **VERIFY** the UW response field for 30-day avg volume is `avg30_volume`; if not, fix the one line.

**Priority:** P1 (biggest remaining signal — turns on confluence ROCKET pre-market).

**Deploy / key needs:** New serverless fn + nightly cron `0 23 * * 1-5` (already in `vercel.json`).
Needs **`UW_API_KEY`** and **`CRON_SECRET`** in Vercel env. Owner-gated.
