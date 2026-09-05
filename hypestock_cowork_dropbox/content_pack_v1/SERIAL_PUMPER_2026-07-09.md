# Serial-Pumper "Repeat Offender" Alert — 2026-07-09
**Educational/operational record. Not investment advice.**

## The idea (David)
Some tickers pump-and-dump over and over. Log the ones we already know, and when one of them
is pumping *again*, fire a special notification: get in on the early leg, take a quick profit,
and get out before it dumps.

## Why it works (proven on our own 2yr surge history)
Mining `surge_events_2yr.csv` (3,122 surge days, 1,107 tickers):
- **420 tickers pumped 3+ times**; **206 pumped 5+ times.** A deep, recurring bench (SDOT, MLGO, ILLR, SEGG, XCUR, NXTT, BNAI …).
- **Serial names (3+) actually have MORE early legs** — they keep going past the first hour ~80–83% of the time vs 76% for one-offs. So there's room to ride the re-ignition.
- **But they dump much harder:** serial names give back a median **−12.3%** from the day's high into the close vs −8.5% for one-timers (the hottest offenders round-trip −20% to −25%). That's exactly why it's a **fast in-and-out scalp, not a hold.**

## What was built
`serial_pumpers.py` — the repeat-offender registry + lookup engine:
- **`build`** mines the surge history **AND our own live flag logs** (`flag_events/`) for every ticker with **≥3 pumps** and writes `serial_pumpers.json`. Per name it stores: `n_pumps` (+ `n_hist`/`n_live` split), tier (**CHRONIC** 5+ / **SERIAL** 3–4), a **heat** score (0–100 = frequency + dump depth + recency), typical pump %, **typical dump off the high**, median mcap, sector, and last-pump date. (Reverse-split % artifacts filtered out.)
- **Self-growing:** each session's logged flags count as fresh pump events (deduped by date), so a name we keep flagging climbs toward the 3+ bar and **earns 🔁 on its own.** First live run already promoted 5 new names (LRMR, OTLK, SPCB, ELTX, ISPR: 2 historical + today = 3) and refreshed recency/heat on 13 more → registry 420 → **425**.
- **`lookup(ticker)`** / **`scalp_levels(price, high)`** / **`log_ignition()`** — used live by the radar.
- CLI: `python serial_pumpers.py build | show [N] | lookup TICKER`.

## Runs automatically (one click)
`run_radar_allday.bat` now rebuilds the registry at **startup** (fresh 🔁 list before the live board loads it) and **grows it at close** from the day's freshly-logged flags — fully hands-off, alongside the existing model evolve/resolve/retrain.

Wired into `momentum_radar.py`:
- Every live flag whose ticker is a known repeat offender gets a **🔁 badge** on the board (console + dashboard) and a **`REPEAT_PUMPER`** flag.
- A dedicated **🔁 Repeat-Pumper Alert panel** (top of the board, above nano/pump) lists any registry names live right now — **hottest heat first** — with the quick-scalp plan: **fixed +6% target** and a **hard "get out" level = 4% below the intraday high** (bail the instant it rolls off), plus that name's typical dump so you know what you're racing.
- Each re-ignition is appended to **`repeat_ignitions.jsonl`** so we can learn each name's real re-pump behavior over time.

## How to use it
When 🔁 lights up: it's a **known serial pump-and-dump re-igniting.** Ride the early leg to the quick
target, and **exit on the first roll-off-high** — do not wait for the top, because these dump hard
(that's the whole pattern). Never hold overnight. Nanos stay watch-only per the no-nano rule; the
scalp panel is in-band ($50M–$10B).

## Dials (top of `serial_pumpers.py`)
`MIN_PUMPS=3` (registry bar) · `CHRONIC_MIN=5` · `SCALP_TARGET_PCT=6.0` · `SCALP_EXIT_OFF_HIGH=-4.0`.

## Verified
- Registry built: 420 offenders (206 CHRONIC / 214 SERIAL); stats sanity-checked (BNGO artifact fixed 5795%→42.9%).
- Lookup + scalp levels + heat-sort simulated on synthetic boards incl. known names — correct; non-repeats excluded.
- Edited Python blocks and the dashboard JS both syntax-checked clean (isolated, to bypass the sandbox mount-truncation artifact; host file confirmed intact — DASH string closes normally).

## Caveats
- History is survivorship-flavored (already-surged days) — treat heat as a **rank**, not a probability, until live re-ignitions accrue in `repeat_ignitions.jsonl`.
- "Pump" here = a ≥ threshold surge day, which includes some legit moves; the dump metric captures the round-trip tendency but isn't a guarantee.
- Fills/slippage/halts not modeled. Educational only — you make all decisions.

## Files
`serial_pumpers.py` (new) · `serial_pumpers.json` (registry, 420 names) · `repeat_ignitions.jsonl` (grows live) · `momentum_radar.py` (🔁 badge + panel + logging) · this note.
