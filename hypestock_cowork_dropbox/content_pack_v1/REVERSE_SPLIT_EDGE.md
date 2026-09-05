# ⚡ The Reverse-Split Edge — v2.9.0

**Your hypothesis was right, and it's the strongest base rate we've found.**
*Educational / informational only. Not investment advice. You make every decision.*

---

## The measurement

40 randomly-sampled US reverse splits (2026-01 → 2026-06), max gain within 45 days of the effective date:

| Metric | Result |
|---|---|
| Median max-gain | **+31.2%** |
| Reached +30% | **50%** |
| Reached +50% | **38%** |
| Reached +100% | **18%** |
| **Median days from split → peak** | **4 trading days** |

The blowups: SKYQ 1-for-8 → **+470%** · SXTP 1-for-4 → **+329%** · AIOS 1-for-20 → **+309%** ·
EUDA 1-for-20 → +262% · DRCT +194% · AGGID 1-for-500 → +147%.

**NVVE is the archetype.** 1-for-18 reverse split effective **2026-07-06** → **+107% on 2026-07-10**.
Four days. Its entire float ended at **11,283 shares**, and it traded **1,577× that float**.

---

## The mechanism (why this isn't a coincidence)

A reverse split doesn't change the company — it changes the **share count**. A 1-for-18 collapses the
float by 18×. NVVE's float went to eleven thousand shares. When real buying shows up, there is
physically almost nothing to buy. Price is the only thing that can move.

This is why the biggest nano rockets we've caught have **no news**. We kept looking for a catalyst.
The catalyst was structural.

---

## ⚠️ The trap — and the rule that follows from it

Look at our own live watchlist today: −15.9%, −16.5%, −17.2%, **−51.7%**.

**Most freshly-split names bleed.** Reverse splits are done by companies in *trouble* — it's usually a
listing-compliance maneuver, and a lot of these names eventually go to zero. The +31% median is a
**max-gain** figure: it says the spike is *available*, not that the stock is up.

So:

> ### The split is the SETUP. The volume is the TRIGGER.
> **Never buy the split. Buy the ignition in a name that recently split.**

NVVE did not run because it split on 7/6. It ran because on day 5 the **volume showed up** and rotated
its collapsed float 1,577×. Setup **AND** trigger. Never one alone.

The engine enforces this as a hard `AND` — the conviction boost only fires on split-recency **and**
live volume/rotation:

```
split alone (no volume)   -> 43   (no boost)
volume alone (no split)   -> 65
split + volume  (AND)     -> 77   (+12 boost)   <-- the only one that counts
stale split + volume      -> 65   (no boost)
```

---

## What the radar now does

- **`reverse_split_watch.py`** pulls FMP's **splits calendar** (structured, exact effective dates —
  far more reliable than scraping news) and keeps a watchlist of every US reverse split, enriched
  with market cap, float, rotation, price and today's move. **Sorted by market cap, smallest first** —
  that's where the squeeze lives. It also shows **upcoming** splits (negative age), so you see the
  spring being loaded *before* it's live.
- **`⚡ REVERSE-SPLIT WATCH` panel** (console + dashboard) with a `STATUS` column:
  `watch` → `hot window (≤7d)` → `live on board` → **`🔥 IGNITING — setup + trigger`**.
  Only that last one is the trade.
- **News crawler** gained a `REV_SPLIT` category that catches the *announcement* (which lands before
  the effective date). It deliberately **bypasses the noise filter**, because reverse splits are
  routinely buried in admin PRs ("Results of Annual Meeting and Reverse Stock Split") that the filter
  would otherwise eat. Verified 10/10 on real headlines.
- **Conviction** gains +12 only on the `AND`. **`log_flag`** now records `split_days`, `split_ratio`,
  `split_hot`, `split_ignition`, so the nightly kaizen grades the thesis itself:

```
by REVERSE SPLIT (setup vs. setup+trigger — the split alone should NOT be enough):
   SPLIT+IGNITION   n=..  avg MFE ..  reached +30% ..
   hot, no vol      n=..  ...
   split >7d ago    n=..  ...
   no split         n=..  ...
```

**If `hot, no vol` ever outperforms `SPLIT+IGNITION`, the thesis is wrong and I'll tell you.**

---

## Monday

The `⚡` panel is at the top of the board, smallest cap first. Watch for `🔥 IGNITING`.
Everything else on that list is a spring that hasn't been released — and may never be.

Spread is brutal on these (20–40% on a nano). **Limit orders only. Size small. Never hold.**
These are squeeze scalps in structurally broken companies, and the exit discipline matters more here
than anywhere else in the system.
