# Mid-Day Audit — Thursday, July 23, 2026

*Informational and educational. Not investment advice.*

## The day so far

Three clean trades, all green, all confirmed flat:

| Ticker | P&L | Return | Note |
|---|---|---|---|
| NVVE (leg 1) | +$717.25 | +13.3% | float squeeze, sold into the halt resume |
| NVVE (leg 2) | +$174.72 | +3.9% | re-entry, quick leg |
| SKYQ | +$703.33 | +11.6% | base-and-breakout, cleanest of the day |
| VIVK | ~flat | −0.5% | penny scratch, exited a faded nano before it dropped |

**Day: ~+$1,595, three green, one scratch, zero red.** And critically — a keystroke-error-free day. Every exit confirmed flat. The one lesson from yesterday (KUST sell-all misfire) held.

The one that got away: PAVS. Order was in at ~$4, broker rejected it (call-the-desk restriction on a 2x-reverse-split nano). It ran to $9.48. Real missed fill, not a hindsight fantasy — fix is to pre-clear reverse-split names with the desk before the open.

---

## Board detection-lag study — David's question answered

**Question:** "It seems the surge is already well into it before it populates on the board. How far did they run before they hit the board?"

**Measured across 810 board snapshots today, 381 names.**

### The blunt number
Of the 47 names that ran +30%+, the median one was **already up +30% the first time it appeared in the board data**, with **~69% of its eventual move already gone.** So the intuition is real.

### But it splits into two very different causes

**Cause 1 — Pre-market gappers (NOT a board lag).**
Names like LGCL (+85% at 04:05) and PAVS (+98% at 08:03) gapped overnight, before the session opened. They appear "already up huge" because the move finished before the bell. No scanner can catch a move that already happened. These names heavily inflate the 69% figure.

**Cause 2 — Intraday igniters (the board caught these EARLY).**
Names that ignited *during* the session were surfaced well:

```
NVVE   entered top-10 at +7%   → ran to +71%
VIVK   entered top-10 at +8%   → ran to +52%
SKYQ   entered top-10 at +16%  → ran to +51%
```

On the names that ignited live, the board flagged them with 40–65% of the move still ahead. That's the board working.

### The real, fixable finding
The lag is a **universe/inclusion problem, not a ranking problem.**

- "First in data" move (+30% median) ≈ "first in top-10" move (+32.5% median).
- Because those two are nearly equal, names are **not being buried below the fold** — they're genuinely **absent from the scanner** until they've already surged ~30%.
- Names pre-loaded in the morning universe (NVVE, VIVK, SKYQ) were tracked from their base and caught early. Names *not* pre-loaded weren't added until ~+30%.
- Same root cause as the AEHR/DNTH invisibility fixed last week: the universe is too narrow.

**The fix:** lower the intraday add-threshold so a fresh, non-pre-loaded name enters the scanner at ~+8–10% instead of ~+30%. That closes most of the gap on exactly the names David is noticing, without touching the ranking (which is already working).

### Honest caveats
- The board_timeline covers today through mid-day; the study will sharpen with a full session.
- "Move" is measured vs previous close, so overnight gaps count as move — that's why gappers look extreme.
- The +20–30% "solid runners" bucket showed 83% of the move gone at first appearance — worse than the big nanos, because their surge score builds more slowly and trips the inclusion threshold later. The add-threshold fix helps these most.

---

## What I'd change (pending David's OK)
1. **Lower the intraday universe add-threshold** (+30% → ~+10%) so fresh igniters appear sooner. This is the direct fix for the detection lag.
2. **Reverse-split / broker-restricted flag** on the board so PAVS-type names are pre-cleared with the desk before the open, not discovered on a rejected order.
3. Both are targeted, evidence-backed changes — not guesses.

---

*Odin Catalyst LLC*
