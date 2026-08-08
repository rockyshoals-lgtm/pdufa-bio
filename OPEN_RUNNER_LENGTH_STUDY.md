# How long does an opening runner actually run?

*297 opening runners, 6 sessions of our own tape (7/14 through 7/21). Regular hours only.
Informational and educational. Not investment advice.*

**Definition used:** a name that was up 3% or more off its 09:30 price within the first 30
minutes, and went on to run at least 8%. Peak measured before 16:00. Bad prints filtered
(a lone tick more than 18% off both neighbours is dropped).

---

## The headline number, and why it is not the useful one

**Median time from ignition to peak: 216 minutes. About three and a half hours.**

That number surprised me and it should probably surprise you too, because it says the
opposite of what "momentum fades fast" implies. The full distribution:

```
share that peak within N minutes of ignition
  <=  5 min     2.7%
  <= 15 min     7.7%
  <= 30 min    13.1%
  <= 60 min    20.9%
  <= 120 min   31.6%
```

**Roughly 4 out of 5 opening runners are still making new highs an hour after they turn on.**
The peak clusters at 13:00 and 15:00, not at 10:00.

So the average opening runner is not a spike. It is a grind.

---

## But the size of the run flips it

```
run 8-15%     n=209   median 217 min   give-back  -4.0%
run 15-30%    n=70    median 216 min   give-back  -7.8%
run 30-60%    n=13    median 133 min   give-back -19.8%
```

The bigger it runs, the **sooner** it tops and the **harder** it gives back. And at the
extreme it is faster still:

```
VIVK  +322%   peaked  46 min after ignition   gave back -63%
NVVE   +62%   peaked  42 min                  gave back -37%
HAO    +38%   peaked  56 min                  gave back -31%
SOBR   +33%   peaked  18 min                  gave back -16%
CPHI +1355%   peaked 262 min                  gave back -38%
```

**The two populations are different animals.** The slow +10% grinder runs all session and
barely gives anything back. The violent one tops inside an hour and surrenders a third to two
thirds of it. You do not trade the first kind. You trade the second kind.

---

## The number that actually matters for your exits

**Once it peaks, the median name gives back HALF the entire run in 18.5 minutes.**

25th percentile is 5.8 minutes. So on a quarter of them, half the run is gone in under six
minutes.

That is the asymmetry that makes your discipline correct. The run up is slow and forgiving.
The roll over is fast and it does not warn you. You get hours to be right and minutes to be
wrong.

---

## What this says about how you are actually trading

Your holds are 15 minutes. The median runner peaks at 216. On the face of it you are leaving
enormous amounts on the table, and on KUST and KSCP you demonstrably were — both kept going
after you sold.

I want to be careful here, because there is an obvious wrong conclusion available: "hold
longer." The data does not support that as a rule, for three reasons.

1. **You cannot tell which population you are in at minute 15.** The +10% all-day grinder and
   the +300% 46-minute blowoff look identical when they ignite. The only thing that
   distinguishes them is what happens later.
2. **The give-back is concentrated in exactly the names you pick.** You are drawn to the
   violent ones, which is where the -20% to -63% give-backs live. The gentle -4% give-back
   belongs to the slow names you would never take.
3. **Nine green sessions is the evidence.** The exit rule is what produced them, and it was
   produced by a smaller sample than this study but a more relevant one: your trades.

The honest framing is not "hold longer," it is **"a runner that is still going at minute 60
has earned a second look."** 79% of them are still climbing at that point. That is a case for
a re-entry rule, not for abandoning the exit.

---

## Two other things worth knowing

**15% of opening runners made a higher high after 16:00.** Extended hours is not a rounding
error on these names. CPHI is the example you already saw hit 15 in after hours.

**7/22 produced zero qualifying opening runners.** Not because the market was quiet, it
obviously was not. Because the radar was down through the open, so there is no tape to
measure. That is independent confirmation of what the outage cost, and it is why the watchdog
is the top of the build list.

---

## What I would build off this

1. **A "still running at +60" flag.** 79% of runners are still climbing an hour after
   ignition, and that is a materially different setup from the ignition itself. Worth
   measuring as a second entry, separate from the first.
2. **A velocity split on the board.** Fast ignition and slow ignition end in different places.
   If we can separate them live, the exit target should differ between them.
3. **Extend the sample.** Six sessions and 297 names is enough to see the shape, not enough to
   trust the tails. Every day we run adds to it now that the study is cached per day.

---

*Odin Catalyst LLC*
