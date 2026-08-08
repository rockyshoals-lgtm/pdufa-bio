# 05 — Extend the base-rate history (ongoing accuracy)

**Goal:** Grow the base-rate grid from ~1 month of event-days to multiple quarters/years so the
cell values are regime-robust. The method is fixed; only the data window grows.

**Data source:** Polygon grouped-daily (free tier, **5 calls/min**), via `research/pull_grouped.py`
(resumable, cached). Then `build_universe.py` → `make_grid.py`. Reads `POLYGON_API_KEY`.

**Logic:** Increase `N_TRADING_DAYS` in `pull_grouped.py`; re-run in bursts (5/min limit).
Rebuild `universe.csv` and `scoring_grid.json`; drop the new grid into `pdufa_site_src/lib/`
(and `staged_engine/lib/`). The grid is a drop-in — no engine code change.

**Acceptance criteria:**
- [ ] `scoring_grid.json.meta.events` grows; temporal-stability check (`redteam.py`) still holds.
- [ ] Live engine picks up the new grid with only a file swap + redeploy.

**Priority:** P2 (do after P0/P1; run periodically).

**Deploy / key needs:** `POLYGON_API_KEY` (research only, not the site). Data refresh, then redeploy.
