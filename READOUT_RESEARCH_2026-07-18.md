# Phase-readout research — 2026-07-18 (Saturday)

Built from your two uploads: **historical_2026-07-18.xlsx** (4,177 catalysts since Jan 2025) and
**fda_2026-07-18.xlsx** (657 forward 2026 catalysts, BiopharmaCatalyst). All prices from FMP
daily bars. Every number here is a **daily-close** reaction — it *understates* the intraday
spike you actually trade, so treat magnitudes as a floor.

---

## 1. How often does a readout happen? (your recurring question, finally measured)

```
ALL phase readouts, all caps, all stages:     ~40 per week
   Phase 2   15.3/wk      Phase 1   8.3/wk
   Phase 3   12.3/wk      preclinical (skip) 3.8/wk
```

But raw count isn't what you asked — you asked how often a **good** one happens. From 1,754
readouts with price history (2025–2026), confirmed two independent ways:

```
                     in the sample (346 tickers)    scaled to whole market
readout pops >= 15%        2.8 / week                   ~4-5 / week
readout pops >= 25%        1.6 / week                   ~2-3 / week

median winners (>=15%) in a week:  2
weeks with ZERO >=15% pop:  4 out of 81   (95% of weeks have at least one)
```

**So a tradeable readout that pops ≥15% shows up 3–5 times a week across the market, and almost
every week has at least one.** That is enough to build the second trade around — but it is a
*few times a week*, not every morning. Some days there won't be one worth taking, and forcing it
is how the second trade turns into chasing squirrels.

---

## 2. The base rate — and why it's the whole game

This is the most important table in the file:

```
1,754 phase readouts, reaction within 2 days:
   median absolute move        7.6%
   MEAN signed move           +3.3%     <-- readouts barely go up on average
   P(up >= 15%)               12.8%
   P(up >= 25%)                7.2%
   P(crash <= -25%)            6.4%
```

**A phase readout is +3.3% on average. Only 1 in 8 pops ≥15%. One in 16 crashes ≥25%.** The edge
was never "readouts go up" — they mostly don't. The edge is **catching the 13% that pop and not
being in the 6% that crash.** That is exactly what the 📋 filter + fast exit is for, and this
data is the reason your "sell the news / get out when red dominates" instinct is correct: the
average readout gives you almost nothing to hold for.

**By stage — this may change what you prioritise:**

```
             median |move|   P(up>=15%)
Phase 1          9.0%           14%      <- moves MORE than Phase 3
Phase 2          8.9%           14%
Phase 3          5.4%           10%      <- the big binary, but priced-in / large-cap
```

Phase 1 and 2 readouts move **harder** than Phase 3. The Phase 3s are the household-name
binaries, but they're bigger caps and more anticipated, so the surprise — and the move — is
smaller. Your small/mid Phase 1/2 readouts are the right hunting ground.

**By price tier** (heavy caveat — only 113 of 1,754 rows had a usable price, so n is thin):

```
$2-5    P(up>=15%) 38%   <- best hit rate, but n=21
$5-15   P(up>=15%) 15%
<$2     median move 13.5% but lower hit rate (pump-and-fade territory)
```

Directionally this matches everything else: the cheap tier is where the big percentage moves
live. But the price column is mostly empty in this file, so I won't oversell it — the all-cap
base rate above is the honest one.

---

## 3. What we're missing vs BiopharmaCatalyst

```
BPC forward H2-2026 readouts:      501
   we already cover:               275   (55%)
   real gaps (not in our list):    226
   names WE have that BPC doesn't:   85   (our CT.gov leading edge)
```

**But 226 overstates it.** BPC's dates are **quarter buckets**, which is the date error you
flagged — proven in the data:

```
   "2026-09-30"  really means  "3Q 2026"
   "2026-12-31"  really means  "2H 2026" / "4Q"
   "2026-08-31"  really means  "mid-2026" / "summer"
```

Row after row lands exactly on a quarter-end with text like *"topline data due in 3Q 2026"* — or
worse, *"preclinical data presented at SAWC 2025"* dated to 2026-08-31. So BPC is a useful
**source of candidate names**, not a source of dates.

**Real near-term gaps worth adding** (small/mid, genuine H2 readouts): CRBP (Ph1b, summer),
NTHI (Ph2a, Aug), CABA (Ph1/2, mid — *you hold this*), NGNE, AVBP (Ph3), MNKD (Ph1b INFLO, 3Q),
BOLT, DWTX, ALT (3Q topline). **Conference-dated and therefore reliable**: SANA (EASD Oct 2),
XNCR/CATX (ESMO Oct 23), AGEN (ESMO Oct 25).

And 85 names we have that BPC hasn't dated yet — that's our CT.gov primary-completion-date edge
working as intended (we see the data-lock before they publish a date).

---

## 4. Miner improvements shipped today

**Quarter-bucket detection** (`readout_scan.py`). A date on Mar 31 / Jun 30 / Sep 30 / Dec 31 /
Aug 31 with period language nearby is now flagged **quarter precision** and relabelled `Q3 2026`
instead of being trusted as `September 30`. A genuinely specific day (a conference talk, "on
Sep 30 at 8am ET", a PDUFA) still passes as a real day. 13/13 tests, built on the actual BPC
rows that exposed the trap.

**Three new phrases** (`phrases_readout.txt`), mined from the 3,215 historical readout
descriptions: `proof of concept`, and dose-expansion cohort language. The rest of our vocabulary
(topline, primary endpoint met/missed, statistically significant, interim) was **confirmed
correct** by the mining — the historical file is BPC's own summaries, so it validates our signal
words rather than adding many new ones.

**Recommended next** (not done yet): ingest the ~200 deduped BPC gap names as *candidates*, then
run EDGAR/CT.gov to get their real dates — never trust BPC's quarter buckets as the readout date.

---

## 5. The honest caveats

- **Daily-close reactions understate the intraday move** you trade. Floors, not ceilings.
- **346 of 611 tickers** fetched (dead hostnames hung the rest); the base rates are stable but
  the market-wide per-week scale-up is a ballpark.
- **Price-tier breakdown is thin** (113 rows) — don't build position sizing on the $2-5 = 38%
  number until we confirm it on more data.
- **One vendor's log.** BPC's classification and dates have known errors; we used it for names
  and signal words, not as ground truth.

---

## Bottom line

A readout worth trading pops ≥15% **3–5 times a week** across the market — real, but not daily.
The average readout is **+3.3%**, so the money is entirely in filtering (📋 real catalyst,
Phase 1/2, small/mid, cheap) and exiting fast, not in holding. That is the second trade, and the
data backs the shape of it you already sketched.

*Informational only. Not investment advice.*
