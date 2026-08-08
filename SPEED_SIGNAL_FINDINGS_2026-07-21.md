# Getting Faster — what the tick data says we can and can't fire on

Tested two candidate "early triggers" that would let us act *before* the 60-second GO bar closes.
Both were measured on the 0.6s tick tape (7/17, 7/20, 7/21), ~565K–694K samples each. Both
**failed** — and the failure is the finding, because it stops us building a machine that fires
you into mean-reverting noise. *Informational only. Not investment advice.*

---

## 1. `utr` (buy/sell tick imbalance) — REJECTED as a trigger

Thesis: "buyers winning right now" → keeps going up. **The data says the opposite.** Forward
120s return is monotonic in `utr`, the *wrong* way:

```
SELLERS  <0.40    +0.09%   54% green
buyers 0.55-0.70  -0.05%   45%
SCREAM  0.85+     -0.17%   47%
high − low utr:   -0.17pp   ← backwards
```

A run of upticks is usually the *local top* of a micro-swing — buyers just spent themselves
lifting offers and the next tick fades. Classic bid-ask bounce / short-term mean reversion. **If
we triggered entries on high `utr`, we'd be buying local tops.**

## 2. `vsurge` (volume surge) — REJECTED as a directional trigger

Thesis: "volume leads price" → a surge predicts the up-leg. **Also mean-reverts**, and harder
when paired with an up-move (the "switch" shape):

```
surge WITH up-move:   avg fwd 120s
quiet <1x     +0.00%
high 4-8x     -0.41%   41% green
HEAVY 8-20x   -0.60%   37% green
```

BUT — one true thing hides inside it: **median MFE rises with volume** (+0.28% quiet →
+0.45–0.49% heavy). High-volume moments have bigger moves available *in both directions*. So a
volume surge predicts **volatility, not direction.**

---

## What this actually teaches us (and it's a lot)

1. **Neither raw tick-imbalance nor raw volume-surge predicts continuation.** At the 60s→120s
   scale, both fade. "Fire the instant volume/ticks spike" would fire into chop most of the time.
2. **Volume surge = expect a big move, both ways.** It's a *bracket-width / position-sizing*
   input, not a buy signal. This is exactly why your limit-and-leave discipline is correct: the
   surge says "violent, both directions" — so you get in, feel it, and exit on a limit rather
   than betting the direction off the surge.
3. **The filter that separates a winner from noise is PRICE CONFIRMATION.** The GO hard-push
   works (validated 30.8% vs 10%) precisely because it requires the price to have *already
   broken* +3% — that break is what filters out the surges that mean-revert. We cannot safely
   drop price confirmation to gain speed.

## So how do we actually get faster? Keep the confirmation, shrink the clock.

The legitimate speed win is **not** an earlier leading signal (there isn't one that holds) — it's
running the *same price-confirmed logic on a faster clock*:

- **15-second micro-bars (task #79) is now the primary path.** Instead of waiting for FMP's
  1-minute bar to close, aggregate our own 0.6s ticks into 15s micro-bars and run the +X%-on-
  volume hard-push on those. Same confirmation, clock cut 60s → 15s. That is a real, honest
  ~45-second gain that does NOT sacrifice the filter.
- **Polygon** helps the *other* latency (vendor batching during bursts), independently.
- **`utr` / `vsurge` are demoted** from "trigger" to "context": vsurge sizes the bracket (big
  vol = wider stop, expect violence); utr, if anything, is a mild *fade/exit* hint (high utr =
  near a local top), the opposite of an entry.

## Roadmap change

- #77 `utr` test → **DONE, rejected** (mean-reverts).
- #78 fire vsurge+utr before GO → **rejected by the data.** Superseded: they don't lead.
- #79 15-second micro-bars → **PROMOTED to the primary "faster than humans" build.** Validate
  first: does a 15s-confirmed push catch the same up-legs as the 1-min GO, just earlier? Then
  build.

**The meta-lesson, same as the chart feed today:** measuring before building just saved us from
shipping two signals that would have quietly lost money. The fastest wrong entry is still wrong.
