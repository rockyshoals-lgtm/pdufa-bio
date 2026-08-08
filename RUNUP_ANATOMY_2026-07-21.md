# The Anatomy of a Runup — what our two-day data actually says

Built from the 9 winning trades (Mon + Tue), today's tape, float/split/sector enrichment, and
the 90-cycle CPHI halt log. *Informational and educational only. Not investment advice.*

---

## The one finding that matters: FLOAT ROTATION is the discriminator

Every explosive mover shared one trait, and every steady name lacked it. Rotation = today's
volume ÷ shares actually available to trade (float).

| ticker | day move | float | rotation | what it was |
|---|---|---|---|---|
| **CPHI** | +1382% intraday | 2.3M | **34.6x** | explosive |
| **VIVK** | +322% | 162k | **847x** | explosive |
| **DFNS** | +96% | 96k | **211x** | explosive |
| **ADVB** (Mon) | +62% | 154k | **11.3x** | explosive |
| POET | +12% | 90.5M | 0.2x | staircase |
| AEHR | +28% | 29.7M | 0.2x | staircase |
| AGEN | +12% | 37.8M | 0.1x | staircase |
| NUVB (Mon) | +3% | 254M | 0.0x | staircase |

**The line is clean and there are no exceptions in our data: rotation ≥ 5x with a float under
~3M = explosive; rotation ≤ 0.2x = a steady grind.** Nothing landed in between.

This is the answer to the question you asked all day in different forms — "is this a real
hold or a pumper?" You were sorting them correctly by feel (rotated out of VIVK/DFNS in
minutes, wanted to hold POET/AEHR all day). Float rotation is that instinct as a number. It
belongs on the board as a column, and it's the core of task #75.

**A caveat, stated plainly:** rotation needs a live, correct float. Post-split names report
broken market caps right now (VIVK shows a $1M cap, DFNS $2M — both wrong). The *float* numbers
held up today, but this is exactly why the daily ticker-hygiene pass matters — stale float
would corrupt the one metric that works.

---

## WHO — the profile of an exploder

- **Tiny float.** All four explosives were under 3M shares available. Three under 165k.
- **Low price.** All under $10 at ignition. Cheap shares + tiny float = a few million dollars
  moves the whole thing.
- **Sector is noise.** Healthcare, Energy, Industrials all appeared. The mechanism is
  structural (float), not fundamental (what the company does).
- **Reverse splits over-represented.** 2 of 4 (VIVK 1-for-20 on 7/17, DFNS 1-for-125 on 7/20)
  had split within days. A reverse split *creates* the tiny float that fuels the move.

---

## WHEN — mid-morning, not the bell

First cross above +20% on the day:

```
CPHI   09:46      VIVK   10:10      DFNS   10:32      AEHR   10:32
```

Ignition clustered **09:46–10:32 ET**, not at the 9:30 open. Peaks came much later — CPHI at
13:58, DFNS at 11:52, AEHR at 16:35. This matters for the strategy: the biggest names were
catchable well after the bell, which is more support for opening the trading window past 10:30
rather than treating the day as won or lost in the first hour.

---

## WHAT an explosion looks like — CPHI, 90 halts

The halt recorder caught **90 halt/resume cycles** on CPHI. This is the richest single-name
dataset we have and it settles two things.

**Direction on a resume is a coin flip:** 49 up, 40 down, median gap +0.7%. But the tails are
enormous — best reopen +68.3%, worst −29.8%.

**The actionable pattern — halt duration predicts violence:**

```
halts ≥ 5 min  →  median |reopen gap|  21.2%
halts < 1 min  →  median |reopen gap|   2.3%
```

A long freeze is the market failing to find a clearing price, and it reopens with a big swing
in *either* direction. The six most violent reopens were all 300s+ freezes (+68%, +42%, +41%,
−30%, +30%, +28%). **A long halt is a "brace" signal, not a "buy" signal** — you cannot know
which way it breaks, only that it will break hard.

CPHI's true intraday peak was **+1382%** (0.91 → ~13.5), confirmed independently by both the
tape and the halt ladder. Your $823 came off a bounce during the *collapse* from that peak, not
the run up — which is why refusing to chase it all morning was correct.

---

## What this changes

1. **Float rotation becomes a board column** (task #75) — the single best pumper-vs-hold tell.
2. **A long-halt "brace" flag** — when the halt badge ships (task #68), tag freezes over ~5 min
   as elevated-risk reopens.
3. **The trading window stays open past 10:30** — the biggest names ignited mid-morning and
   peaked into the afternoon.
4. **Ticker hygiene runs daily** — because the one metric that works (rotation) depends on a
   float that stale data would poison.

---

*Figures from our own tape and trade records. Past results are not a guide to future returns.
Informational and educational only; not investment advice.*
