# Momentum / Meme / UOA Radar

Whole-market momentum, meme, and unusual-options scanner. **Self-contained and separate
from the biotech catalyst system** (ODIN / GUNGNIR / BIFROST / HEIMDALL live in
`../Odin Perfection/`). Nothing here depends on the biotech code, and vice-versa.

_Informational and educational only — not investment advice. Owned/operated by Odin Catalyst LLC._

---

## What it does
Scans the **whole market** (FMP movers ∪ Unusual Whales all-sector flow firehose), filters
to **micro + nano caps only** (≤ $300M — the high-torque "rocket zone"), and scores each
name 0–100 on momentum plus a separate 0–100 unusual-options (UOA) score. Flags
**🚀 ROCKETS** = abnormal volume **AND** unusual options firing at the same time.

## Files
| File | Purpose |
|---|---|
| `momentum_meme_scanner_v1.py` | The scanner. Writes `momentum_scan_latest.{json,js}` + a timestamped `momentum_scan_<ts>.json` each run. |
| `momentum_meme_dashboard.html` | Live dashboard. Loads `momentum_scan_latest.js`; auto-refreshes every 60s. |
| `run_momentum_radar.bat` | Background runner — re-scans every 5 min during US market hours. |
| `momentum_scan_latest.json` / `.js` | Most recent scan (the `.js` is the dashboard data twin). |
| `momentum_scan_2026-06-29_*.json` | Historical scan snapshots. |

## Setup (one time)
API keys are read from **environment variables only — never hardcoded.** In cmd/PowerShell,
then restart the terminal:

```
setx FMP_API_KEY "your_fmp_key"          REM required (universe + quotes + news)
setx UW_API_KEY  "your_unusualwhales_token"   REM required (flow firehose + UOA)
setx LUNARCRUSH_API_KEY "..."            REM optional (social blend)
setx REDDIT_CLIENT_ID "..."              REM optional
setx REDDIT_CLIENT_SECRET "..."          REM optional
```
Social sources auto-skip if their keys are absent. StockTwits uses a public endpoint (no key).

## Run
- **Continuous (recommended):** double-click `run_momentum_radar.bat` — loops every 5 min,
  market hours only, and rewrites the dashboard data. Open `momentum_meme_dashboard.html`
  and toggle **auto 60s** on; it refreshes itself.
- **One-shot:** `python momentum_meme_scanner_v1.py`
- **Manual loop:** `python momentum_meme_scanner_v1.py --loop 5 --market-hours`

## Config knobs (top of `momentum_meme_scanner_v1.py`)
| Setting | Default | Meaning |
|---|---|---|
| `MAX_MARKET_CAP` | `300_000_000` | Cap ceiling — micro/nano only. Set `None` to scan all caps. |
| `W` | price 25 / volume 20 / options 15 / short 15 / news 15 / social 10 | Momentum score component weights. |
| `SOCIAL_WEIGHTS` | lunarcrush 0.40 / reddit 0.35 / stocktwits 0.25 | Blend for the (secondary) social component. |
| `VOL_SPIKE_HIGH` | `5.0` | Relative-volume multiple that counts as a volume explosion (and the 🚀 volume leg). |
| `OPT_SPIKE_HIGH` | `4.0` | Options-volume spike multiple that counts as an options explosion. |
| `UOA_TICKER_MIN_PREM` | `300_000` | Aggregated premium needed for a UOA-only name to qualify. |
| `UOA_PREM_HIGH` | `2_000_000` | Aggregated premium that maxes the UOA score. |

## What 🚀 ROCKET means
A name is tagged ROCKET when it shows **≥5× relative volume** AND **unusual options activity**
(options spike, call sweeps, sweep cluster, or UOA score ≥ 50) in the same scan — i.e. price
and the options tape are moving together, not just one of them.

## Notes
- Social (LunarCrush / Reddit / StockTwits) is a **secondary** signal, capped at 10% of the
  momentum score — never treated as proof.
- UOA volume isn't confirmed positioning until the next open-interest update.
- IV/options analytics for the biotech side use `../Odin Perfection/uw_iv.py` (ORATS was
  canceled 2026-06-29). This scanner doesn't need it.
