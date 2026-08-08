# LEADLAB — Leading-Signal Momentum Study (Fable, 2026-07-03)

_Informational / educational only — NOT investment advice. Real data only._

## The one-line result
**The move is detectable before it runs.** Of every small/micro-cap that eventually
surged **+25% intraday**, **83% were already up ≥10% by 9:00am** (30 min before the open)
and **69% by 8:00am** (90 min before). Pre-market gap **× relative volume** is a clean,
unbiased leading signal — and the old engine, which waited for a **+8% regular-session
move**, was structurally late.

## Why this study exists (what was broken)
The prior surge study (`surge_study_report.md`, 2,980 events) is **survivorship-biased**:
its universe is *currently-listed* names, so surges from since-delisted pump-and-dumps
are missing, and it only ever looked at **winners** — there was **no control group**, so it
could describe what winners looked like but never answer *"if I see signal X, how often does
a surge actually follow?"* (precision / false-positive rate).

## What I built to fix it
1. **Unbiased whole-market universe** — Polygon `grouped-daily` (one call = the entire US
   market's OHLCV for a day). Crucially, Polygon **retains tickers that later delisted**, so
   the set includes **winners, losers, and since-delisted names**. 44 trading days pulled;
   after a 20-day ADV burn-in that yields **24 event-days, 5,810 small/micro gap-up ticker-days**.
2. **Leading pre-market layer** — FMP 1-minute **extended-hours** bars (from 04:00 ET) for a
   stratified sample of **641 gap-up events (winners AND losers)**, to compute pre-market
   gap, pre-market volume, and opening 1/5-minute velocity.
3. **Scoring grid** — empirical `P(hit +25% intraday vs prev close)` on both surfaces,
   exported to `scoring_grid.json` and embedded in the live engine.

Data filters: price ≥ $0.30, ≤ $60 open, market-cap proxy ≤ $3B, open gap ≥ 3%, $50k+ dollar volume.

## Result 1 — the OPEN-session base-rate surface (unbiased, n=5,810)
`P(intraday +25% vs prior close)` by open gap and relative volume (20-day ADV):

| gap ↓ / rel-vol → | <1× | 1–2× | 2–5× | 5–10× | 10×+ |
|---|---|---|---|---|---|
| **3–5%**   | 1% | 2% | 7% | 16% | 40% |
| **5–10%**  | 2% | 5% | 13% | 27% | 44% |
| **10–20%** | 12% | 18% | 31% | 55% | 71% |
| **20–40%** | 88% | 78% | 87% | 89% | 100% |
| **40%+**   | — | — | — | — | 100% |

Marginals: gap alone — 3–5%→**2.6%**, 5–10%→**6.3%**, 10–20%→**27%**, 20–40%→**90.6%**, 40%+→**100%**.
Rel-vol alone — <1×→**1.9%**, 2–5×→**16.6%**, 10–20×→**62.9%**, 20×+→**79.8%**.
**Overall base rate of *any* ≥3% gap-up reaching +25% intraday: 9.9%** — i.e. most "surges" are noise;
gap size × volume is what separates the ~10% that run from the ~90% that don't.

## Result 2 — the PRE-MARKET leading surface (n=641, with controls)
`P(intraday +25%)` by the **9:00am** pre-market move — **fires ~30 min before the open**:

| pre-market 9:00 move | n | P(+25%) |
|---|---|---|
| 3–5%   | 86  | 1.2% |
| 5–10%  | 129 | 10.9% |
| 10–20% | 95  | **47.4%** |
| 20–40% | 51  | **92.2%** |
| 40%+   | 68  | **100%** |

**Confluence is the gold signal:** pre-market 9:00 move ≥10% **AND** rel-vol ≥3×
→ **91.8%** hit +25% (n=147). Move-alone or volume-alone is far weaker. Pre-market
cumulative volume is itself predictive (30% → 84% across volume buckets) — this is the
**"volume before price"** tell.

## Result 3 — earliness (the prime directive)
Of the 198 sampled events that hit +25% intraday:
- **83%** were already **≥10%** by **9:00am**; **60%** already **≥20%**.
- **69%** were already **≥10%** by **8:00am** (90 minutes before the open).

Precision at a ≥10% trigger: **pre-market 9:00 ≥10% → 74.8%** (n=214, fires ~30 min earlier)
vs **open gap ≥10% → 61.7%** (n=295, fires at 9:30). Earlier *and* more precise.

## Red-team (see `redteam.py`)
- **Temporal stability:** base rates hold across the window's two halves (gap 10–20%: 27.5% vs 26.2%; gap 20%+: 96.3% vs 93.1%; gap 3–5%: 2.5% vs 2.8%).
- **No look-ahead:** gap uses strictly-prior close; rel-vol uses trailing 20d; pre-market uses only ≤09:00 prints; the +25% label is the (future) outcome. All signals are known at/before the moment they'd fire.
- **Survivorship:** materially reduced vs the old study (Polygon retains delisted names). Residual: names delisted *before* the window.
- **Honest limitations:**
  1. **Window is ~1 month** (2026-06-09 → 07-02, 24 event-days). Sample of *events* is large (5,810) but the *calendar* window is short and regime-specific. The `pull_grouped.py` puller is resumable — **extend it to multiple quarters** before over-trusting exact cell values. The *method* is the durable deliverable; the grid should keep growing.
  2. **Odds = "reaches +25% at some point intraday," not "from your entry."** Intraday path/timing isn't modeled; realized entry P&L is lower and depends on fills. The old morning-exit studies still govern *when to exit*.
  3. **Pre-market micro-cap liquidity is thin** — quotes can be a few shares wide and often not executable. Pre-market numbers are the least-realizable in the product.
  4. 5 of 25 gap×relvol cells have <20 samples; the engine falls back to the 1-D marginal there.

## Files (in `Momentum Scanner/research/leadlab/`)
- `pull_grouped.py` → `cache_grouped/` — Polygon whole-market puller (resumable, 5/min).
- `build_universe.py` → `universe.csv` — unbiased gap-up universe + outcomes.
- `make_sample.py` → `sample_events.csv`; `pull_premarket_fast.py` → `premarket_features.csv` — pre-market layer.
- `analyze_baserates.py`, `analyze_leading.py`, `redteam.py` — analysis.
- `make_grid.py` → `scoring_grid.json` — the surface the live engine embeds.
