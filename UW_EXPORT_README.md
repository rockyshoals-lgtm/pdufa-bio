# UW bulk export — dark pool + option flow for all 2026 catalysts

**Built 2026-07-21, before the UW subscription lapses.** Grabs everything UW has for our
**134 tradeable catalyst tickers** (rest of 2026), at full depth, and saves raw JSON to disk.

## Do this (2 steps, ~1 minute of your time, then leave it running)
1. Open `Odin Perfection\.env_master`, add one line, save:
   ```
   UW_API_KEY=your_unusualwhales_token
   ```
   (from unusualwhales.com → Settings → API. The exporter also accepts the names
   `UNUSUAL_WHALES_API_KEY`, `UNUSUALWHALES_API_KEY`, or `UW_TOKEN`.)
2. **Double-click `run_uw_export.bat`.** It first prints which endpoints your account can reach
   (discovery), then pulls everything. Leave the window open; it runs a while. If it stops
   (rate limit / sleep / network), just double-click again — it's **resumable** and skips files
   already saved.

## What it pulls (per ticker, verified against the UW OpenAPI today)
- **Dark pool** — `/api/darkpool/{ticker}`, paginated backward via `older_than`, 500/page, up to
  8,000 prints/ticker, ALL premium (not just blocks). The thing you named first.
- **Options flow** — `flow-alerts` captured two ways (`/api/stock/{t}/flow-alerts` **and**
  `/api/option-trades/flow-alerts?ticker_symbol={t}`), plus `flow-per-strike`, `flow-per-expiry`,
  `net-prem-ticks`, `greek-flow`. This IS the per-ticker option tape — UW has **no**
  `/api/stock/{t}/option-trades` path (404); the only raw tape is `/api/option-trades/full-tape/{date}`,
  which is market-wide and gigabytes/day, not per-catalyst, so it's intentionally not pulled.
- **Greeks / GEX** — `greek-exposure` (2-year daily history), by `strike`, by `expiry`,
  `gex-levels`, `greek-flow`, `spot-exposures`.
- **Premium / volume / OI** — `net-prem-ticks`, `options-volume`, `oi-change`.
- **Vol / IV** — `volatility/term-structure`, `iv-rank`, `atm-chains`, `interpolated-iv`, `max-pain`.
- **Reference** — `option-contracts`, `insider-buy-sells`, `info`.
- **Market-wide** — recent dark pool + market flow alerts.

Verified live today via the MCP tools: both dark pool and flow return for our catalyst names
(MNKD dark-pool blocks; flow alerts on VTRS, INSM, ARWR, MDGL, VRTX, NVO, PFE, GILD, VKTX, LLY,
SYRE, RMD…). The exporter captures all of it in full to disk.

## Output
```
uw_export_2026/
  <TICKER>/darkpool.json           # deep, paginated
  <TICKER>/greek_exposure.json     # 2y daily
  <TICKER>/flow_alerts.json  option_trades.json  net_prem_ticks.json  ...
  _market/darkpool_recent.json  flow_alerts_market.json
  _log.csv                         # per-request HTTP status (audit trail)
  _MANIFEST.json                   # tickers, valid endpoints, request count
```
Raw JSON, one file per (ticker, endpoint) — ready to load into pandas for the BIFROST/UOA/smart-money
work later.

## Notes
- **Read-only.** It only GETs data and writes files. No trades, no account changes.
- Tune with `--rps` (default 3/sec — safe; raise if your UW tier allows), `--workers` (5),
  `--dp-max` (8000 dark-pool prints/ticker). Subset with `--tickers MNKD CAPR OTLK`.
- Conference codes (ASH, ESMO, SABCS…) and the bad `IRD`/`GH` rows are filtered out — 134 real tickers.
- **Why a script and not the chat tools:** the MCP tools return data into the chat one page at a
  time; a script with your key pulls in parallel, paginates to exhaustion, and persists everything
  without passing it through a conversation. It's the only way to get *all* of it before cutoff.

## If you can't add the key in time
Tell me and I'll pull a prioritized snapshot (near-term catalysts first) straight through the MCP
tools this session and save what I can — smaller, but captured before access ends.
