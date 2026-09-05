# Getting in before the crowd — what the tape actually shows

**2026-08-01 · Odin Catalyst LLC · educational analysis, not investment advice**

---

## First, the part I can't sell you

**You cannot beat HFT on latency.** They are colocated in Mahwah and Carteret, measuring round
trips in microseconds, paying for direct exchange feeds that reach them before the consolidated
tape reaches us. From a desk in California that race is unwinnable, and no study changes it.

So I threw out the speed framing and tested the sequence one instead: *a move has an order of
participants, and if institutional positioning is visible before the ignition that draws everyone
else, we don't need to be fast — we need to be watching a variable nobody else is watching.*

We have full tick-level trades and NBBO quotes from Polygon, plus a transaction count (`n`) sitting
in every 1-minute bar we already pull. `v/n` = **average trade size**, free. Big prints = block
flavour. Many small prints = a crowd.

---

## Attempt 1 — failed, and the failure was the useful part

I first measured the tape in the 15 minutes **before** the +2% cross. It reported a beautiful
result: print-count acceleration 2.60x for winners vs 1.20x for faders.

It was fake. Winners cross at minute 3. **There is no 15 minutes of regular-session tape before
minute 3.** My window function silently collapsed both windows onto the same 3 bars, making the
ratio mechanically 15/5 = 3.000. Exactly 140 of 439 rows came back at precisely 3.000 — every one
of them crossing between minute 1 and 5. The "signal" was arithmetic re-measuring cross timing,
something we already knew. 32% of the sample was fabricated.

I caught it because the medians printed as *exactly* 1.000 and *exactly* 3.000. Real ratios don't
do that.

**The structural lesson:** for the names that matter, the pre-ignition window doesn't exist inside
regular hours. It exists before the bell. That's also exactly the window you were asking about.

---

## Attempt 2 — pre-market tape DNA

Every variable fixed before 09:30. 132 names with real pre-market tape (329 of 480 dropped as too
thin — noted below). Base rate 23% reach +5% from the open.

### The block hypothesis is dead

| avg pre-market print size | n | hit +5% | lift |
|---|---|---|---|
| tiny <40 sh | 12 | 17% | 0.73x |
| 40–80 sh | 22 | 18% | 0.80x |
| 80–150 sh | 45 | 24% | 1.08x |
| 150–300 sh | 30 | 33% | 1.47x |
| **BLOCKS 300+ sh** | 23 | **13%** | **0.57x** |

Non-monotonic, and the biggest-block bucket is the *worst*. "Spot the whale's footprint and follow
it in" is not supported. Same for whether prints grow into the bell — 7% / 40% / 25% / 24%, no
story. Institutions slice parent orders into child orders that look retail-sized; that's the whole
point of an execution algo, and it means print *size* tells you very little.

### What does work: not who, but **how many**

| variable | winners | faders | ratio |
|---|---|---|---|
| pre-market shares | 72,232 | 12,716 | **5.68x** |
| pre-market print COUNT | 398 | 111 | **3.58x** |
| pre-market dollar volume | $628k | $352k | 1.78x |
| gap at the open | +3.55% | −0.34% | — |

And it's monotonic: <200 prints → 14% hit (0.60x), 200–1k → 32%, 1k–5k → **37% (1.62x)**.

### The control that decides whether this is real

Pre-market volume correlates with gapping on news, and the board already shows the gap. So: does
print count still separate **inside** a gap bucket?

| | n | hit +5% | vs its own bucket |
|---|---|---|---|
| **gapped +3%+**, 300+ prints | 14 | **79%** | 1.28x |
| gapped +3%+, <300 prints | 12 | 42% | 0.68x |
| **flat or gapped DOWN**, 300+ prints | 20 | **20%** | **1.93x** |
| flat or gapped down, <300 prints | 57 | 7% | 0.68x |

**Both directions survive.** Print count adds information on top of the gap (79% vs 42% among big
gappers), *and* the gap adds information on top of print count. They're complementary, not
redundant.

The second row is the interesting one. A name that **isn't gapping** but has heavy pre-market
participation doubles its odds — 20% vs 7%. Those are the names nobody is watching, because every
screener in retail-land sorts by gap percentage. This dovetails exactly with yesterday's finding
that 42% of intraday winners open red.

---

## The honest reframe

Your instinct was right that the volume uptick is a mix of participants — but the tradeable signal
isn't identifying *which* participant. It's that **many separate hands showing up before the bell
predicts continuation, and print count measures that better than share volume or print size does.**

Not "a whale is accumulating." Rather: *"a crowd is already forming, and the crowd hasn't finished
arriving."* We can't front-run the algos, but we can be early to the **crowd** — and the crowd is
slower, larger, and leaves a much bigger footprint.

---

## Why I am not wiring this in yet

**The sample is too small.** The headline 79% cell is **n=14**. The 1.93x cell is n=20. At those
counts a handful of names moves the number several points. Everything above is a *promising
hypothesis that survived its first control*, not a validated rule, and the difference between those
two things is the difference between the findings that held this week and the ones that died.

**Coverage is limited.** 329 of 480 names (69%) were dropped for having too thin a pre-market tape
to characterise. This can only ever apply to names that actually trade before the bell.

**What it needs:** 30–40 sessions instead of 8, which should put the key cells at n=60–80.
`premarket_tape_dna_study.py` takes a session count as its first argument — it's a single long run,
no new code. That's the next thing I'd do.

---

## Where I'd go after that

1. **Lee-Ready trade classification.** We have NBBO quotes, which we've never used. Classify every
   print as buyer- or seller-initiated by whether it hit the ask or the bid. That gives real
   directional pressure instead of raw participation — a strictly better version of the variable
   that just worked.
2. **Exchange-4 (FINRA TRF) share.** Off-exchange prints. One honest caveat: TRF is *not* clean
   dark-pool institutional — it also carries retail order flow internalized by Citadel and Virtu.
   Anyone telling you "TRF volume = smart money" is selling something. But the *ratio* of TRF to
   lit volume may still separate, and it's testable.
3. **The 15:00 window** from yesterday's study, where 42% of the money peaks and we have never
   once looked.

---

## Running tally of what's dead

Killed this week, all with data: the 4 AM thesis · revenue-beat as a filter · EPS / beat-rate ·
pre-close volume (3x) · PEAD · shallow-dip (3x, actively backwards) · **pre-cross block detection
(new)** · **prints-growing-into-the-bell (new)**.

Still standing: the 09:45/10:00 checkpoint · volume→magnitude (r = +0.67) · the unbiased AH rule ·
runner timing decay · the gap-down blind spot · and now, provisionally, pre-market print count.

*Educational and informational only. Not investment advice. I don't make trade calls — you do.*
