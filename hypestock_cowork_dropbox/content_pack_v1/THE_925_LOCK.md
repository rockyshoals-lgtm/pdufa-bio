# The 09:25 Lock — getting ahead of the open-gate rippers

## The finding that forces it

From today's tape: **38.6% of all first-hour highs print in T+0-5 minutes.** Half are in by T+10.

A stock that "rips straight out of the gate" has therefore **already peaked before any intraday
screener can see it, rank it, and put it in front of you.** Reacting faster is a race we lose by
construction — the fastest possible reaction to a 09:30:30 move is still *after* 09:30:30, and
the modal high is at 09:32.

**The only way to be early is to already be watching the right names at 09:29:59.** Which means
deciding from pre-market state, before the move exists.

## Does pre-market state actually predict it?

> ### ⚠️ CORRECTION — the first version of this was wrong
>
> My first pass had **no stale-open guard**. It measured today's price against **yesterday's
> open** for any name that hadn't printed yet, and counted the resulting nonsense as a "rip."
> It scored **VEEE at +129.2% in the first five minutes**. VEEE's real first-5-min move is
> **+2.7%** — it ran later. `lock_grade.py` caught it: a **33% base rate on 1,161 names** is not
> credible.
>
> I reported **7/10 and 3.77x** to David off that run. **The real number is 3/10.**
> Everything below is the guarded re-run.

Ranked the universe by **pre-market gap at 09:25**, took the top 10, measured whether each
ripped ≥+5% from its open within **five minutes**:

| | TRAIN (7/13+7/14) | TEST (7/15, one shot) |
|---|---|---|
| base rate | 10.9% | **7.8%** |
| **top 10 by gap** | **4/10 (3.67x)** | **3/10 (3.83x)** — HELD |
| top 5 | 2/5 (3.67x) | 3/5 (7.67x) — HELD |
| top 20 | 5/20 (2.29x) | 3/20 (1.92x) — HELD |

**It is not "7 of 10 rip." It is three of ten — against a base rate of under 1 in 13.**
The *lift* is the real number and it survived at ~3.8x, because the inflated hit rate came with
an inflated base rate. **Most of the list will do nothing.** The point is that 3-in-10 beats
1-in-13 by a lot.

### The band story broke

| gap band | TRAIN | TEST |
|---|---|---|
| 3-8% | 0.92x | 1.04x |
| 8-15% | 3.93x | **0.95x** ← worked in train, not in test |
| 15-30% | — | **0.00x** (n=15, zero ripped) |
| 30%+ | — | **7.67x** (n=5) |

The top-N **ranking** held. The band **thresholds** did not. On the test day the entire edge
came from a handful of extreme gappers. `GAP_MIN` stays at 8 as a floor — raising it to 30
would be fitting to five names on one day, which is exactly the mistake that killed the other
324 rules.

On 7/15, **SOBR appeared on the list at 09:25** — five minutes before it moved, and it's the
name David actually traded.

### A real limitation the grader exposed

On 7/15's reconstructed lock, **6 of the 10 locked names never had a resolvable open inside the
5-minute window** — their `open` was still yesterday's. That doesn't just make them ungradeable;
it means **the live board would have shown them a dash during the very minutes the lock exists
for.** `lock_grade.py` names them rather than quietly scoring the survivors.

## What got built

At **09:25** the radar freezes the top 10 by pre-market gap (≥8%, ≥1,000 pre-market shares,
≥$0.30) to `_DATA/prebell_lock_<date>.json`, prints it to the console, and **points the fast
poller at those names before the bell**. They hold on `/tape` through **09:36**, then normal
%-from-open ranking resumes.

The hold matters: at 09:30:01 every name is ~0% from its open, so re-ranking then would sweep
the pre-bell list off the board at the exact moment it was chosen for.

**The list is written once and never rewritten.** Re-ranking it at 09:29 would quietly turn it
into a 09:29 list; re-ranking at 09:31 would be a straight lookahead. `_lock_test.py` asserts
this — a name that gaps *after* the lock cannot sneak in.

## What I could NOT test, and why it matters

**Pre-market volume looked just as good** (6/10, 3.3x on 7/15) — and I can't validate it:

- FMP's 1-min bars are **RTH only** (09:30-15:59). Confirmed. No pre-market history.
- Our tape has real pre-market volume for **exactly one day**. The `ext` overlay landed
  recently; on 7/14 the pre-market `v` is *yesterday's total* and **falls** at the bell
  (AZN: 4,465,264 at 09:25 → 157,046 at 09:35).
- UW's `ohlc` endpoint documents `market_time='pr'` and might unlock history — **untestable
  today, the daily quota is exhausted.** Worth one probe tomorrow.

So the lock ranks on the **gap alone** and shows volume as information. If UW serves pre-market
history, volume becomes testable and the lock probably gets better.

## The honest caveat

**Three days. One regime. TRAIN n=55 with SIX rippers in it.** A HELD verdict here means *keep
recording and re-test in two weeks* — not *bet on it tomorrow*. What three days can do is
**kill** an idea, and this one didn't die. That's all it has earned.

It is graded automatically every night by `lock_grade.py`, against a list frozen at 09:25 that
could not have seen the outcome. `lock_grade.py --all` shows the running record. It needs
**~10 live days** before the lift means anything.

**It is a watchlist, not a buy list.** It says where to look at 09:30. Every validated signal
we have tells you the SIZE of what's coming, never the DIRECTION — and this is no different.

---

## The other thing this turned up: the UW feed was going to die every morning

`tape_feed` polled 8 names every 1.5s = **19,200 requests/hour**. A 6.5-hour session needs
**~125,000** against UW's **40,000/day** cap — **3.1x over**.

The bid/ask would have gone dark around 11am *every day*, and `_pull()`'s bare except turned
every 429 into "no prints" — **indistinguishable from a genuinely quiet tape.** We'd have
concluded the NBBO coverage was worse than it is.

Fixed: 6 names @ 4.0s (35,100 worst case, 15,600 realistic), a hard 30,000 budget, adaptive
backoff for names that never print off-exchange, and a **loud** message when the quota is gone
so it can never masquerade as silence again.

## Tomorrow

`python preflight.py` → **67 pass, 0 fail.** Watch the console at 09:25 for the lock.
