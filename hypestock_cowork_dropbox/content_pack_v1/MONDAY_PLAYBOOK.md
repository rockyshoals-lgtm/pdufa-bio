# Monday Playbook — Momentum Radar v2.3
**Educational/operational record. Not investment advice. You make every decision.**

The whole edge, from all our data, comes down to **three levers you already named:**
**(1) enter after the open · (2) enter early · (3) exit with discipline.** v2.3 makes them mechanical.

---

## The one number that matters
The same setup, entered at two different points:

| Setup | Reached +5% after entry | +8% | +15% |
|---|---|---|---|
| **Pre-market pop** (buy the 6:30 gap) | **31%** | 17% | 9% |
| **Regular session, holding highs** (buy the open igniter) | **99%** | 98% | 94% |

Same names, opposite outcome. **It's not the stock — it's when you enter.** Buy the regular-session rocket as it's *still rising off the open*, never the extended pre-market pop. (The 99% is the ceiling — the price *traded* that high; you still need a clean entry and an exit before the fade to capture it. NVVE +117% and SUNE +77% Friday were exactly this: open igniters, disciplined exits, both green.)

---

## Nanos & micros: the stop and the spread are the whole game
These are where the biggest runs live — and where you get killed if you're careless. Two rules, both now enforced by the board:

**1. The stop must breathe.** Our micro picks routinely drew down **before** they ran:

| Ticker | Drawdown first | Then ran to |
|---|---|---|
| WRAP | −11.6% | **+31.3%** |
| ISPR | −12.2% | +10.1% |
| AHG | −17.2% | — |

A flat −5% stop is **noise** on a $1.50 stock — it guarantees you're shaken out of the winners. The board now uses a **volatility-sized stop** (~0.6× the name's own intraday range): WRAP's 25% range → a **15% stop**, which survives the −11.6% dip and catches the +31%. Tight mid-caps still get a 5% stop.

**2. LIMIT ORDERS ONLY — the spread will eat you.** Real quotes:

| Ticker | Spread |
|---|---|
| AAPL | 0.13% |
| WRAP | **6.09%** ⚠️ WIDE |
| ABLV | **42.73%** 🔴 EXTREME |

A market order on a 42% spread is a disaster before the trade even starts. The board now shows the **real bid/ask spread** on every name and tags WIDE/EXTREME with a **LIMIT-ONLY** flag. Size small on those.

**Also: we now log EVERY name we find, nanos included.** (We previously never recorded nanos at all — we were blind to the highest-magnitude band. Fixed.)

## The veil: volume must BUILD, not front-load
The single sharpest signal we've found. The monsters **start quiet and build**; the duds **dump their volume in the first 30 minutes and die.**

| Volume behavior | median run | hit +50% | hit +100% |
|---|---|---|---|
| **Volume BUILDING** (2nd half-hr ≥2× the first) | +47% | **45%** | 16% |
| Volume fading | +30% | 22% | 7% |
| **"Slow burn"** (first 30min = <10% of day's volume) | **+50%** | **51%** | **17%** |
| **Front-loaded blow-off** (≥50% of volume in first 30min) | +18% | **5%** | 1% |

A front-loaded name reaches +50% only **5%** of the time — that's the trap that looks exciting and isn't. The board now tracks this **live** (it scans every 2s) and shows a **Vol ↑/↓** column: **↑ = volume BUILDING** (what you want), ↓ = fading. Also why "low early volume" wins: quiet start + building volume = real accumulation.

## The exit that matters: ⛔ EXIT = volume rolled over
Pulled real Polygon minute bars on both of Friday's monsters. **The price top landed in the same 30-min block as the volume peak — every time:**

- **NVVE (+117%):** volume peaked 10:00–10:30 → price topped **$20.74 at 10:30** → both collapsed together.
- **SUNE (+77%):** volume peaked 12:00 (22% of the day) → price topped **$4.50** in that block → then faded.

So **when volume rolls over, the run is done** — that's earlier and cleaner than waiting for price to fall off the high. The board now watches this live: once a name has been **building** and its volume **rolls over**, the signal flips to a red **⛔ EXIT**. *If you're holding, that's your out.*

(Measured on Friday's flags: the volume peak and price peak land in the same block 40% of the time and **within one block 70%** of the time.)

## Grades — the setups with the most potential
Every name now gets a **CONVICTION score (0–100)** and a **grade**, combining everything: magnitude + still-rising + **volume building** + continuation odds.

| Grade | Meaning |
|---|---|
| **A+ ELITE** | Everything lines up — the highest-potential setups |
| **A STRONG** | Strong setup |
| **B FAIR** | Mixed |
| **C WEAK** | Weak — the odds aren't there |

*Information only — this grades the setup's historical characteristics, not a recommendation on any security. Every decision is yours.*

## One a day? Read the 🏆 TOP PICK (and the MAGNITUDE score)
Since you want the *biggest* mover, we optimize for magnitude, not just continuation. From the 2,983-event study, three things separate the +50% monsters from the +10% movers — and they **stack**:

| Driver | Biggest runs |
|---|---|
| **Low price** (< $2 best, < $5 good) | +46% median, 42% hit +50% |
| **Small cap** (nano < $50M, micro < $300M) | +43% median, 39% hit +50% |
| **Low early volume** (< 0.5× ADV) | +44% median, **81% hit +30%** |
| **All three stacked** (< $5 + < $300M + < 0.5×) | **87% hit +30%, 45% hit +50%** |

The board scores every rocket **MAG /100** on exactly this, and the **🏆 TOP PICK** is the single highest-magnitude name that's *also* a valid entry (rising + fresh). That's your one-a-day candidate. Top-quintile magnitude hit +50% **45%** of the time vs 21% bottom — more than double.

**Read it as:** 🏆 TOP PICK gives you the *what* (biggest expected run + valid entry), the **MAG score** tells you *how big it could go*, **cont%** tells you *how likely it continues*, and the **PLAN** tells you *the exit*. High MAG + GO signal = the trade.

⚠️ Caveat: the biggest-magnitude names are low-price nanos — that's exactly where halts, slippage, and spreads bite. Bigger upside comes with bigger risk. Size small, use limit orders, exit on the first roll-off.

## The board now tells you what to do — read the ENTRY SIGNAL column

| Signal | Meaning | Action |
|---|---|---|
| 🟢 **GO** | Regular session + still rising (holding highs, above open) + high odds/rocket + **fresh (≤20 min since flagged)** | **The entry.** This is the trade. |
| 🟠 **LATE** | Rising + high odds, but it's been running a while (a chase) | Only if you must; smaller, tighter. Odds worse than GO. |
| **WATCH** | On the board but not confirmed rising or not high-odds | Wait for it to become GO — or move on. |
| 🔵 **WATCHLIST** | Pre-market flag | **Do NOT buy the pop.** It's an early heads-up; wait for the open to confirm (it becomes GO or it fades). |
| 🔴 **SKIP** | Fading off its high, or up-big-but-flat (M&A/priced-in) | No momentum edge. Pass. |

**Age** column = minutes since we first flagged it. Lever 2 in one number: **GO + low age = your best entries.**

---

## Monday, step by step
1. **Launch `run_radar_allday.bat` early. Confirm the dashboard header reads `v2.3.0`** (an old build shows `v?` — if so, you're on stale code, relaunch).
2. **Pre-market (before 9:30):** treat the board as a **watchlist only** (everything shows WATCHLIST). Note the names, don't buy the pop.
3. **Read top-down — the panels are ordered by how early the signal is:**
   - **📰 NEWS CATALYSTS** (top) — a phase readout / FDA / M&A / earnings beat *just hit*. Earliest edge. Confirm it's rising below.
   - **🚀 LIVE ROCKETS** — up fast **and still rising right now** (incl. nanos ⚠️). Fast scalp.
   - **Main board GO rows** — rising + high-odds + fresh.
4. **Entry = a GO (or a NEWS/ROCKET name that's confirmed rising).** Enter early — GO + low age. Don't chase LATE.
5. **Exit by the PLAN column (already computed per name):**
   - **RIDE** (clean, low-vol, holding highs): let it run toward +15%, exit on the first roll-off-high.
   - **SCALP** (blow-off / nano / 10×+ vol): quick +5–8%, hard exit, **never hold.**
   - **Every trade:** the instant it rolls off its high (drops out of the top of its range / flips 📉 FADING), you're out. That single rule is the discipline.
6. **Never hold through the fade, never hold overnight.** The intraday rocket *is* the trade.

---

## What still bounds it (so you're not surprised)
- The regular-session universe is FMP's biggest-gainers + most-actives (top ~120). The **📰 news firehose** widens it by catching catalysts at the source, but a truly cold ticker can still surface late. Whole-market coverage would need the Polygon feed (open decision).
- Signals are keyword/price screens, not verified facts — glance at the headline yourself.
- The 99% is a historical ceiling, not a promise. Position size for the losers, not the winners.

## The self-check
Every night the `.bat` prints the **kaizen report** + your **trade journal** — your real hit rate, by setup, from your own fills. That's the scientific loop: trade the GO signals, log the fills, let the numbers tune the dials. It gets sharper every day.
