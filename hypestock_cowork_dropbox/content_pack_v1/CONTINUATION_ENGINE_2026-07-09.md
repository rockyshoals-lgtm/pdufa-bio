# Continuation Engine — self-learning momentum-day-trade layer (2026-07-09)
**Educational/operational record. Not investment advice.**

## The strategy it serves (David, verbatim intent)
Intraday only — **never hold overnight.** Buy a runner *as it's going up*, ride first-day momentum to a **set % target**, sell the same day. Don't buy everything — buy only the names with the **highest odds of continuing the run**. The program must **evolve and self-learn** from its own hits and misses.

## What was built
`continuation_learn.py` — a self-learning continuation-odds engine wired into `momentum_radar.py`:
- **`seed`** — builds a prior from the project's **2,983-event surge history** (`surge_forward_features.csv` + `surge_intraday_features.csv`). Honest forward label = *continued_2pct* (kept going ≥2% **after** the first hour). Base rate **80.3%**.
- **`log`** — the radar appends every first-flag (with features) to `flag_events/<date>.jsonl` during the session.
- **`resolve`** — after the close, pulls each flagged name's **real intraday path from its flag price** and labels it **WIN** (hit +target before −stop) / **LOSS**, with MFE/MAE + time. Appends unbiased outcomes to `outcomes.jsonl`.
- **`train`** — rebuilds `continuation_model.json` = prior buckets + **live outcomes weighted 6×** (they're the true decision distribution). Live data increasingly dominates → self-learning.
- **`score`** — per live flag returns **cont_odds (0–100), tier, target, stop**.

In the radar: every board row now gets a **Cont%**, the board **sorts by continuation odds first** (the "which to buy" signal outranks raw move), the strongest get a **🎯 badge**, and each flag is logged for tonight's retrain. The all-day `.bat` runs `resolve` + `train` at the close, so **the model gets smarter every day**.

## The signal (robust, survivorship-resistant)
From the honest forward label:
- **Early relative volume is INVERSE.** Low first-30-min vol/ADV continues **92%**; 1–2× → 80%; **10×+ → 55%** (blow-off tops). The engine penalizes extreme rel-vol and flags `blowoff_risk` — matches the radar's EXHAUSTION_RISK logic.
- **Bigger gaps continue LESS** (25–40% gap → 84%; 70%+ → 72%).
- **Holding the first hour is ~95% deterministic** (held → 95% continue; faded → 0%). The first hour is the tell.

## Live-loop proof + today's critical finding (real data)
Backfilled today's **52 tradeable catches** → resolved → trained. Base recalibrated **80.3% → 74.4%** (live decisions are harder than the survivorship-biased prior — exactly why we let live data reweight it).

**The actionable lesson — stop width, not selection, was the killer today:**

| Target / Stop | Hit target **before** stop | Target reachable at all |
|---|---|---|
| +7% / −4% | **15%** | 29% |
| +7% / −8% | 21% | 29% |
| **+5% / −3%** | **23%** | **54%** |
| +10% / −8% | 15% | 19% |

- TRAX (MFE **+39%**), FBRX (+30%), WRAP (+29%), LASR (+22%) all **ran huge — but a −4% stop knocked you out first.** Names that ran ≥+20% had median **MAE −9.2%** → they *need a wide stop or a better entry.*
- Chasing the **first +5% bar is a poor entry** (median MFE only +5.2%, MAE −4.2%) — you buy the spike and eat the pullback.
- **A modest +5% target is 54% reachable** vs 29% for +7%.

**Implication for the strategy:** the edge is **selection + modest target + volatility-sized stop (or a better entry — wait for a first-hour hold / shallow pullback, not the first spike).** The model now handles *selection* (rank by cont-odds, penalize blow-offs); the target/stop is your dial, and the nightly resolve will learn which buckets actually hit +target before stop from *real logged entries* going forward.

## How it self-learns, each day
1. Radar logs every flag with features (live).
2. Close → `resolve` labels WIN/LOSS from real intraday (`outcomes.jsonl` grows).
3. `train` folds outcomes in (6× weight) → `continuation_model.json` recalibrates.
4. Next session, cont_odds reflects everything learned. `calibrating` flag drops off once live_n ≥ 120.

## Red-team / honest caveats
- **Prior is survivorship-biased HIGH** (history = already-surged days). We expose `calibrating: true` until enough live outcomes accrue — before then cont_odds is a **rank, not a trustworthy probability**.
- **Today's backfill used a chase entry** (first +5% bar) + a bar-order stop-first assumption → the 15–23% win rates are a **pessimistic floor**; live logging at the true flag moment + better exits should improve it.
- Fills/slippage/borrow not modeled. Small live sample (n=52). Nanos excluded from scoring by design.
- Everything is local, real-data, educational — not investment advice.

## Files
`continuation_learn.py` (engine) · `continuation_model.json` (seed + live) · `flag_events/<date>.jsonl` · `outcomes.jsonl` (growing memory) · `momentum_radar.py` (integrated, Cont% + 🎯 + sort + logging) · `run_radar_allday.bat` (nightly resolve+train) · this note.
