# MOMENTUM_ENGINE — scoring spec (port target)

Reference implementation: `/assets/momentum_meme_scanner_v1.py`. This doc restates its logic so it can be
ported to a serverless function faithfully. Real example output: `/assets/sample_momentum_scan.json`.
`clamp(x)` = min/max to `[0,1]` unless bounds given.

> Apply the **`avgVolume` fix** from `DATA_SOURCES.md` when porting — relative volume must come from
> `/stable/profile.averageVolume`, not `/stable/quote`.

## Pipeline

1. **Universe** = FMP `biggest-gainers` (top 60) ∪ `most-actives` (top 60) ∪ the UW flow-alerts firehose tickers. Dedupe. Drop symbols with `.^/` or length > 5.
2. **UOA firehose aggregation** (one UW call → per-ticker aggregate): sum `total_premium`; split ask-side premium into `call_ask`/`put_ask` by `type`; count `has_sweep`; track max `volume_oi_ratio`; keep only `issue_type ∈ {Common Stock, ADR}`.
3. **Candidate filter** (per universe name): fetch quote; require `MIN_PRICE ≤ price ≤ MAX_PRICE`; require `marketCap ≤ MAX_MARKET_CAP` (micro/nano only). Keep if **mover** OR **has_uoa**:
   - `mover` = liquid AND `|dayChange%| ≥ MIN_DAY_CHANGE_PCT`. *(Liquidity gate: use today's `volume` — or cached `profile.averageVolume` — NOT the missing `quote.avgVolume`.)*
   - `has_uoa` = ticker in firehose with aggregated `premium ≥ UOA_TICKER_MIN_PREM`.
   - Cap at `ENRICH_LIMIT` candidates.
4. **Enrich + score** each candidate (below), sort by `max(score, uoa_score)` desc, publish.

## Scoring (momentum score 0–100)

Weights `W`: **price 25 · volume 20 · options 15 · short 15 · news 15 · social 10.**

| Component | Formula | Flags |
|---|---|---|
| **price** | `W.price * clamp(chg / 30)` | `PRICE_PARABOLIC` if `chg ≥ 20` |
| **volume** | `relv = vol / avgVolume`; `W.volume * clamp(relv / VOL_SPIKE_HIGH)` | `VOLUME_EXPLOSION` if `relv ≥ 5` |
| **options** | from `options-volume`: `spike = call_vol / avg_30d_call_vol`, `cpr = call_vol/(call_vol+put_vol)`; `osc = 0.7*clamp(spike/OPT_SPIKE_HIGH) + 0.3*clamp((cpr-0.5)/0.4)`; if ≥3 per-name sweeps → `osc += 0.15`; `W.options * osc` | `OPTIONS_SPIKE` if `spike ≥ 4`; `CALL_SWEEPS` |
| **short** | `pfs` = % float short (÷100 if >1), `dtc` = days-to-cover; `0.6*clamp(pfs/SHORT_FLOAT_HIGH) + 0.4*clamp(dtc/DTC_HIGH)`; `W.short * that` | `HIGH_SHORT_INTEREST` if `pfs ≥ 0.20` |
| **news** | within `NEWS_LOOKBACK_DAYS`: if headline hits catalyst keywords → `nsc = 0.6 + 0.1*hits` else `0.3`; `W.news * clamp(nsc)`; then `+2` per analyst upgrade in last 7d (cap `W.news`) | `FRESH_CATALYST` if `nsc ≥ 0.6`; `ANALYST_UPGRADE_xN` |
| **social** | weighted blend of live sources (`LunarCrush 0.40 / Reddit 0.35 / StockTwits 0.25`, renormalized over live ones), `W.social * clamp(blend)`. Secondary, capped at 10%. | `REDDIT_BUZZ`, `STOCKTWITS_BULLISH`, `LUNARCRUSH_HIGH_GALAXY` |

`score = sum(components)` rounded to 0.1.

## UOA score (separate 0–100) + bias

From the firehose aggregate for the ticker:
```
netd      = call_ask - put_ask
bias      = BULLISH if netd>0 else BEARISH if netd<0 else MIXED
conv      = clamp(|netd| / premium)
uoa_score = min(100, 40*clamp(premium/UOA_PREM_HIGH)
                    + 20*clamp(sweeps/4)
                    + 20*clamp(max_vol_oi/10)
                    + 20*conv)
```
The UOA score also **raises** the options component: `options = max(options, W.options * clamp(uoa_score/100))`.
Flags: `UOA_$<prem>_<bias>`, `SWEEP_CLUSTER` if `sweeps ≥ 3`, `VOL>>OI` if `max_vol_oi ≥ 10`.
UOA-only names (big flow, no stock move yet) qualify at `premium ≥ UOA_TICKER_MIN_PREM` and max out at `UOA_PREM_HIGH`.

## 🚀 ROCKET rule (the headline signal)

```
vol_hot = relv >= VOL_SPIKE_HIGH            # abnormal VOLUME (needs the avgVolume fix!)
opt_hot = options >= 0.6*W.options OR uoa_score >= 50
          OR any flag in {OPTIONS_SPIKE, CALL_SWEEPS, SWEEP_CLUSTER}
ROCKET  = vol_hot AND opt_hot               # volume AND options firing together
```
Default the dashboard sort to **ROCKETs first**, then by `max(score, uoa_score)`. (Dashboard backlog: add a min-UOA-premium slider.)

## `kind` classification

`UOA_LEADER` (uoa_score≥60 & price+vol comps<20) · `MEME_SQUEEZE` (short≥9 & social≥5 & vol≥10) ·
`NEWS_EXPLOSION` (news≥9 & price+vol≥22) · `MOMENTUM` (price+vol≥24) · `WATCH` (score≥35 or uoa_score≥50) · else `NOISE`.
`biotech=true` if sector/industry matches {healthcare, biotechnology, pharmaceutical, drug, life sciences} — those route to the biotech engine.

## Config knobs

| Const | Default | Meaning |
|---|---|---|
| `MAX_MARKET_CAP` | `300_000_000` | micro/nano only; `None` = all caps |
| `MIN_PRICE`/`MAX_PRICE` | `0.50`/`5000` | price band |
| `MIN_DAY_CHANGE_PCT` | `5.0` | mover threshold |
| `VOL_SPIKE_HIGH` | `5.0` | rel-vol that = volume explosion / ROCKET leg |
| `OPT_SPIKE_HIGH` | `4.0` | options-volume spike multiple |
| `SHORT_FLOAT_HIGH` / `DTC_HIGH` | `0.20` / `5.0` | squeeze thresholds |
| `UOA_MIN_PREMIUM` | `150_000` | ignore single alerts below this |
| `UOA_TICKER_MIN_PREM` | `300_000` | aggregated premium for a UOA-only name to qualify |
| `UOA_PREM_HIGH` | `2_000_000` | premium that maxes the UOA score |
| `ENRICH_LIMIT` / `TOP_N_PER_LIST` | `70` / `60` | candidate + universe caps |
| `NEWS_LOOKBACK_DAYS` | `2` | catalyst headline window |
| `W` | 25/20/15/15/15/10 | component weights |

## Output payload (what the frontend/Supabase stores)

Top level: `{ generated, n, weights, social_weights, disclaimer, results: [...] }`.
Each result:
```jsonc
{
  "ticker": "…", "score": 0-100, "uoa_score": 0-100, "uoa_bias": "BULLISH|BEARISH|MIXED|",
  "rocket": true, "uoa_premium": 0, "kind": "MOMENTUM|UOA_LEADER|MEME_SQUEEZE|NEWS_EXPLOSION|WATCH|NOISE",
  "biotech": false, "price": 0, "day_change_pct": 0, "rel_volume": 0,
  "components": { "price":0,"volume":0,"options":0,"short":0,"news":0,"social":0 },
  "flags": ["ROCKET","VOLUME_EXPLOSION", "…"], "headline": "…",
  "sector": "…", "market_cap": 0, "mcap_tier": "nano|micro|small|mid|large",
  "social_sources": ["stocktwits","lunarcrush"], "social_detail": { … }
}
```
See `/assets/sample_momentum_scan.json` for a full real example (2026-06-29).

## Red-team notes to preserve in the rebuild
- **Real data only** — never fabricate tickers/prices/flow. If a value can't be verified, exclude it.
- Guard against: stale quotes, ticker collisions, split adjustments, thin/illiquid names (untradeable spreads / no listed options), look-ahead bias, double-counting a name that's in both a mover list and the firehose.
- Social is secondary and capped — never presented as proof.
- A single short-interest snapshot applied to history = look-ahead; only use point-in-time SI.
