# Morning-Runner strategy — reality check (FINAL, n=1,880)

_Informational and educational only — not investment advice. Odin Catalyst LLC._

**The question:** catch a small/micro-cap gapping up, get in around the 9:30 open, ride the momentum, and
sell for a profit within an hour or two. Does 2 years of data support it?

**Method:** every small/micro-cap US name (≤$2B) that gapped up ≥20% at the open (a 9:30-observable trigger,
so **no close-selection bias**) — 1,987 events, 1,880 with full intraday. Entry = 9:30 open. Because micro-cap
returns are extremely fat-tailed, **read the medians, not the means** — a few names that run hundreds of
percent make the averages lie (see red-team note below).

## Verdict: as conceived, it does not have a tradeable edge — the move is a pre-market event
On the full sample the **median stock had 100% of its whole day's move (prior close → day high) already done
by the pre-market high.** By 9:30 the run is over; the regular-session buyer is late, and the typical trade
fades.

## The core numbers (medians; entry at the 9:30 open)

| Exit rule | median % | win rate |
|---|---|---|
| Sell at the exact 30-min high *(impossible — reference)* | +6.9% | 93% |
| Exit 10:00 | −2.5% | 38% |
| Exit noon | −2.7% | 39% |
| **+10% take-profit, else noon** *(best realistic long)* | **+5.0%** | 56% |
| 10% trailing stop | −2.0% | 39% |
| Hold to close | −3.8% | 41% |

Only the +10% take-profit rule has a positive median (it banks the winners), and even it is roughly flat on
the mean. Every other realistic long exit loses for the typical trade. The high usually lands early — **62% of
these names put in their morning high by 10:00**, then bleed.

## The three slices you asked for

**1) Confirmation entry (wait, only trade if still green at 10:00): doesn't rescue it.**
Entering *at 10:00 after confirmation*, the median trade still loses (−0.8% by 10:30, −1.4% by noon; ~43% win).
⚠️ The auto-report's glowing "+11%/+13%, 100% win" confirmation table is **look-ahead bias** — it selects names
already up at 10:00 and then reports they were up at 10:00. Not tradeable. Ignore it.

**2) Subset slicing: no bucket clearly pays.**
By gap size, all negative medians and bigger gaps are worse (20–40%: −1.5%; 40–70%: −5.1%; 120%+: −5.5%).
By first-hour volume, only the **3–5× ADV** bucket is ~breakeven (+0.8% median, 52% win, n=178) — one bucket out
of many tested, so most likely noise, not signal.

**3) Short side: positive median but a catastrophic tail — a minefield, not a green light.**
Shorting the open gap and covering fast (by 10:00) was **+2.5% median, ~60% win** (gross) — the mirror image of
the fade. But the mean tells the real story: holding the short to the close averaged **−264%** because the rare
runners squeeze shorts to ruin. Add 100–1000% borrow fees (if you can even locate shares), LULD halts (you
can't cover mid-halt), and this is a fundamentally different, dangerous book. Not a recommendation.

## Red-team notes (why the raw reports can mislead)
- **Use medians.** The raw `morning_report.md` calls "hold to close (+263.7% mean)" the *best* expectancy — that's
  a handful of lottery outcomes, not an edge; the median is −3.8%.
- **Confirmation table = look-ahead.** As above.
- **Survivorship.** Universe is currently-listed names only, so faded/delisted pump-and-dumps are missing — real
  numbers are **worse** than shown.
- **Before costs, optimistic fills.** Micro-cap spreads, slippage, halts, and especially pre-market illiquidity
  mean realized results trail these figures.

## What this means for the build
- **The scanner is an *alert*, not a buy signal.** Surface the mover fast; do not imply "buy the open and ride."
- **Don't ship any of these as a live long edge** — none cleared the bar on honest medians.
- **The only forward-honest path** is the prospective log in `SURGE_RADAR.md`: record first-hour movers live with
  real fills and outcomes, and let a genuine edge (if one exists) prove itself before it sizes a dollar.

## Artifacts (in `assets/surge-study/`)
`morning_report.md` + `morning_exit_timing.png`, `premarket_report.md`, `morning_slices_report.md`, the event
CSVs (`morning_events.csv`, `premarket_events.csv`), and scripts `surge_study_phase5_morning.py`,
`surge_study_phase6_premarket.py`, `morning_slices.py`.
