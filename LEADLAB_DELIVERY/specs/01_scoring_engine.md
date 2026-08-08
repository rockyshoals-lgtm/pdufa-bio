# 01 — Unbiased scoring engine (replaces the survivorship table)

**Goal:** Rate every mover with a real, unbiased base rate — P(this name reaches +25% intraday) —
instead of the old survivorship-biased continuation table.

**Data source:** No live call — the surface is precomputed in `lib/scoring_grid.json`
(from LEADLAB: Polygon whole-market grouped-daily, incl. delisted tickers; 5,810 gap-up
ticker-days + 641 with pre-market minute data). Regenerate via `research/make_grid.py`.

**Logic / scoring (already implemented in `lib/scoring.mjs`):**
- `scoreOpen(movePct, relvol)` → `{p, n, basis}` via the gap×relvol grid; falls back to the
  gap marginal when a cell has <12 samples, then to base rate. Gap edges [3,5,10,20,40],
  rel-vol edges [0,1,2,5,10].
- `scorePremarket(pmMovePct, relvol)` → same shape, pre-market surface.
- `classify({p, movePct, relvol})` → tier + flags. Tiers **PRIME / BUILDING / WATCH / NOISE**
  (tuned "earlier, accept more noise"): PRIME = ROCKET or p≥0.70; BUILDING = p≥0.40 or
  (move≥10% and relvol≥2×); WATCH = p≥0.15; else NOISE. Flags: **ROCKET** (big move AND
  heavy volume), **VOL_NO_PRICE** (relvol≥10× while move<10% — volume before price),
  **EXHAUSTION_RISK** (move≥50% on thin volume), **CONTROLLED**.
- Emits legacy tier names (HIGH_ODDS/MODERATE/FADE_RISK) as `tier` for UI compatibility, plus
  `tier_new` for the richer label.

**UI / UX:** No change required for compat (legacy `tier` + `cont_odds_pct` preserved). See spec 04
for the richer tier display.

**Acceptance criteria:**
- [ ] `node --check api/surges.js` passes; `import('../lib/scoring.mjs')` resolves in the Vercel build.
- [ ] `/api/surges` during market hours returns a rated board; big thin movers carry EXHAUSTION_RISK.
- [ ] Odds match the grid (e.g. 10–20% gap × 5–10× relvol ≈ 55%).
- [ ] Handles null `avgVolume` (FMP usually null) → `basis: "gap_only"`, no crash.

**Priority:** P0.

**Deploy / key needs:** Uses existing `FMP_API_KEY`. New file `lib/`. Already staged in
`pdufa_site_src/`. Owner-gated deploy.
