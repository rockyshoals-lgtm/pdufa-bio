# 02 — Pre-market board (the earliness unlock)

**Goal:** Show a live board of pre-market gappers (4:00–9:30am ET) so surges are caught ~30–90 min
before the open, instead of the old blank "opens at 9:30" screen.

**Data source (all real, existing keys):**
- Candidate watchlist: FMP `biggest-gainers` ∪ `most-actives` (prior session; names with overnight
  interest). Env `FMP_API_KEY`.
- Static context: FMP `batch-quote?symbols=...` → read `previousClose`, `marketCap`, `name`.
- Live extended-hours: FMP `batch-aftermarket-quote?symbols=...` → read `bidPrice`,`askPrice`
  (use mid), `volume` (pre-market cumulative), `bidSize`/`askSize` (thinness).
- Optional ADV map (spec 03) from KV key `adv_map` → enables pre-market rel-vol.
- Refresh ~20s (edge-cached `s-maxage=20`).

**Logic / scoring (implemented in `api/premarket.js`):**
- `pm_move = mid/previousClose - 1`; keep names with `pm_move ≥ 5%`, price ≥ $0.30, mcap ≤ $3B.
- `relvol = amVolume / adv` (adv from `adv_map`, else `base.avgVolume`, else null).
- Score with `scorePremarket(pm_move, relvol)` + `classify(...)`. Flag `THIN_QUOTE` when bid/ask size <5.
- Emits fields shaped for the existing card renderer (`chg`,`move`=pm_move, legacy `tier`).

**UI / UX:** Reuse the dark card board. On `session==='PRE_OPEN'`, `surges.html` calls
`/api/premarket` and renders it (already patched; backup `surges.html.bak_fable`). Panel title →
"Pre-Market Board (4:00–9:30am ET)". Show a **thin-liquidity warning** on THIN_QUOTE names.

**Acceptance criteria:**
- [ ] Pre-market: `/api/premarket` returns gappers with `pm_move`, `cont_odds_pct`, `tier`, flags.
- [ ] Outside 4:00–9:30am ET returns the empty-with-note shape (no stale board).
- [ ] `relvol_enabled` reflects whether the ADV map is present.
- [ ] Thin micro-cap names visibly flagged; disclaimer about pre-market illiquidity shown.

**Priority:** P0.

**Deploy / key needs:** New serverless fn `api/premarket.js`; new route `/premarket` + cron warms
(already in `vercel.json`). Existing `FMP_API_KEY`. Owner-gated deploy.
