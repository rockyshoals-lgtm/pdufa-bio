# How the Algos Work — and How We Beat the Humans

A working reference for the 9 Realms momentum system. Goal, stated David's way: *we will not
beat the hedge funds' supercomputers, but we can beat most of the humans.* This document is how.

*Informational and educational only. Not investment, legal, or tax advice.*

---

## Part 1 — Who is actually on the tape of a runner

"Algos" is five different players. They operate on different clocks, and knowing which clock
each runs on is the whole key to where we can compete.

| player | clock | what they do | can we compete? |
|---|---|---|---|
| **HFT market-makers** | microseconds | quote the bid/ask, capture spread, pull liquidity when it's dangerous (this *causes* halts) | **No.** Colocated, sub-ms. Not our race. |
| **Momentum algos** | **seconds–minutes** | detect ignition (volume + new highs) and pile in, extending the leg | **This is the crowd we join.** |
| **Mean-reversion / fade algos** | seconds–minutes | short the extreme, bet on the snapback — the "selling at the top" | they are our counterparty on every leg |
| **News algos** | milliseconds | parse 8-Ks / wire feeds, trade before humans read | can't beat, but can *ride* what they start |
| **The human herd** | **seconds–minutes** | run "biggest gainer" scans, pour in manually | **these are the humans we beat.** |

**The one sentence that reframes everything:** we are not competing with the microsecond HFTs —
we compete to recognize the *same ignition trigger* the seconds-to-minutes crowd (momentum algos
+ the human herd) is about to react to, and be a beat ahead of the *humans* in that group.

---

## Part 2 — How the pile-in actually works (the reflexive loop)

A low-float runner is a **reflexive feedback loop**, not a trend:

1. A trigger fires — an 8-K, a halt resume, a volume spike.
2. Volume arrives. Because the float is tiny, that volume *moves the price* — buys lift the offers.
3. The move crosses thresholds momentum algos watch: **relative volume spike, new high of day,
   whole-dollar levels ($5, $10), % gainer-list ranking.**
4. Momentum algos + the human herd pile in → more volume → higher → higher scan rank → more herd.
5. Fade algos and profit-takers sell into it → the oscillation.
6. On a tiny float there isn't enough stock for everyone to *hold*, so the same pool cycles
   in/out → **it flips: up, sell, up, sell.** (David's exact observation about CPHI.)

**Why this matters for us:** the pros' own scanners key on *"relative volume compared to the
stock's typical 5-minute volume"* and *"volume pressure — buying vs selling"* (verified, see
sources). That is **precisely `vsurge` and `utr`** in our system. We are already measuring the
two things the professional momentum crowd measures. We are not behind on *what* to watch — only
on *how fast we surface it*, which Part 5 fixes.

**The trap, restated:** step 5 is not optional. The fade is built into the structure, which is
why our own pullback study found buying dips was a coin flip and why CPHI's 90 halt-resumes were
49 up / 40 down. The loop is positive-EV *on average* and violent on the tails. The limit-and-
leave rule is what converts an average edge into a survivable one.

---

## Part 3 — Halt mechanics (LULD), precisely — the CPHI machine

CPHI halted ~6 times and our recorder caught **90 halt/resume cycles**. Here is the machine that
was running, verified against the LULD plan:

- **The bands.** A stock is halted when it would trade outside a percentage band around a
  *reference price* (the 5-minute average of prints). Bands depend on price and tier:
  - Tier 2 (everything not S&P/Russell-1000) **above $3: 10%**.
  - **Lower-priced stocks get much wider bands — anything under $0.75 can move up to 75%** before
    halting. This is why CPHI, opening at $0.85, could rip enormous percentages early before its
    first halt, then halt constantly once it climbed into tighter-band territory.
- **Bands DOUBLE in the first 15 minutes (9:30–9:45) and last 25 (3:35–4:00).** A name is
  *hardest* to halt right at the open — which is exactly when the biggest, fastest moves are
  allowed to happen uninterrupted.
- **The 15-second rule.** Price entering a band is a "Limit State." If it doesn't come back
  within **15 seconds**, the exchange declares a **5-minute pause.**
- **The reopening auction.** After 5 minutes, the exchange collects buy/sell orders and finds the
  single clearing price that balances them. *That price becomes the new reference*, and fresh
  bands compute from it. **This is why a resume gaps** — the auction clears against whatever
  imbalanced book accumulated during the freeze, and on a name that just doubled, that book is
  thin and lopsided. Direction is genuinely unknowable in advance.
- **Extended halts.** If it can't find a clearing price, the collar widens and the auction
  extends another 5 minutes. Our data: freezes **≥5 min reopened with a median 21% swing** vs 2%
  for short ones — the long freezes are the market failing to agree, and they break hardest.
- **The 3:50 EOD exception.** A pause in the last 10 minutes does **not** reopen intraday — it
  goes straight to the closing auction. Any halt after ~3:50 ET means the name is done for the
  day; do not wait for a resume that isn't coming.

**Actionable:** a long halt is a *brace* signal, not a *buy* signal. When our halt badge ships,
it should show elapsed freeze time and flag anything ≥5 min as an elevated-risk reopen.

---

## Part 4 — Why the humans are slow (this is our whole edge)

We beat humans on **two** latencies, and neither is the microsecond game:

**1. Perception latency.** The manual trader opens a scanner, eyeballs the gainer list, thinks,
pulls up the ticker, decides, then types an order. That is **tens of seconds to minutes** from
"the switch flipped" to "order placed." Our system can *detect + toast* within **seconds** of the
volume surge — the alert comes to David instead of David hunting for it. That gap — machine-fast
surfacing vs human eyeball-scanning — is the majority of the edge and it is entirely ours to take.

**2. Routing latency (smaller, real).** Retail orders often route via **payment-for-order-flow**
wholesalers. Execution quality varies widely by broker (one study: **>75% of TD Ameritrade
orders filled at mid-or-better vs ~25% at Robinhood**), and price improvement averages only
**~$0.01–0.02/share**. We can't fix a broker's routing — but it's a reason **limit orders on thin
names are non-negotiable**: a market order into a PFOF wholesaler on a violent nano is where the
hidden slippage lives.

**The honest ceiling:** the news algos (ms) and HFT (µs) will always be ahead of us on the very
first tick. We are not trying to be first. We are trying to be **early to the humans** on the
sustained multi-minute leg — and that leg is driven by the same seconds-clock crowd we can match.

---

## Part 5 — The latency budget: where OUR seconds go, and how to cut them

This is the "fit it into our program and make it faster" part. Every stage from *switch flips* to
*David can act*, with the current cost and the fix.

| stage | current latency | fix | target |
|---|---|---|---|
| FMP quote poll (tape) | 0.6 s | already fast; not the bottleneck | 0.6 s |
| **FMP data itself lags in bursts** | **up to ~30–60 s on fast names** (measured on CPHI: vendor batched, dayHigh behind live) | Polygon full tape — *only after the free fixes prove GO works* | ~1–2 s |
| **GO waits for a 1-min bar to CLOSE** | **up to 60 s** by construction | **fire on `vsurge`+`utr` mid-candle**, GO as the slower confirm behind it | ~5–15 s |
| notification to David | was ~51 min (dead chart feed + no alert) | **alerter now toasts** (shipped 7/21); chart-feed self-test (shipped 7/21) | seconds |
| human decision | David's | the limit + one-trade rule already governs this | n/a |

**The single biggest free win: stop waiting for the 1-minute bar.** `vsurge` (60-second rolling
volume vs the name's own 20-min normal) and `utr` (uptick/downtick imbalance) update
*continuously* and fire *mid-candle*, off the volume that is *causing* the move — 30–60 seconds
before GO can confirm it. That is the difference between the bottom third and the top third of a
leg on a nano.

**The next win: our own micro-bars.** Instead of waiting on FMP's 1-minute bars, aggregate our
0.6 s tape ticks into **15-second micro-bars** and run hard-push detection on those. Cuts the
bar-close wait from 60 s → 15 s using data we already collect. (This is the sub-minute
aggregation idea, now with a concrete home.)

---

## Part 6 — The build list (ordered by seconds-saved per unit effort)

1. **`utr` predictive test** — does buy/sell imbalance at entry predict the next few minutes? We
   have the tape; this is a measurement, not a build. If it holds, it becomes the confirmer that
   lets us trust an early trigger without the 60 s GO wait. *Highest leverage — do first.*
2. **`vsurge` + `utr` as the loud early trigger** on /tape, firing *ahead* of GO. Demote `accel`
   (a lagging 2nd derivative) to the exit/hold decision, not entry.
3. **15-second micro-bars** from our own tick tape → hard-push detection at 15 s instead of 60 s.
4. **Halt badge with elapsed-freeze time** (Part 3) — brace flag at ≥5 min.
5. **Reopening-auction awareness** — after a resume, mark the first print; never market-order
   into it.
6. **Then, and only then, evaluate Polygon** — its one real latency argument is a complete tape
   during the exact bursts where FMP falls behind. Worth it *if* the free fixes prove the
   signals earn their keep; wasteful before.

**What we do NOT chase:** the microsecond race, colocation, beating news algos to the 8-K. That is
the supercomputers' game and it is not winnable with a retail feed. Our edge is being early to the
*humans* on the *sustained leg* — and everything above serves that.

---

## Sources

- [Limit Up-Limit Down: Price Bands, Limit States, and Pauses — LegalClarity](https://legalclarity.org/limit-up-limit-down-price-bands-limit-states-and-pauses/)
- [Nasdaq LULD FAQ](https://nasdaqtrader.com/content/MarketRegulation/LULD_FAQ.pdf)
- [Cboe Limit Up/Limit Down FAQ](https://cdn.cboe.com/resources/membership/BATS_US_Equities_Limit_Up_Limit_Down_FAQ.pdf)
- [LULD Plan (official)](https://www.luldplan.com/)
- [SEC — HFT Literature Review Part II (momentum ignition)](https://www.sec.gov/marketstructure/research/hft_lit_review_march_2014.pdf)
- [Momentum Ignition — DayTrading.com](https://www.daytrading.com/momentum-ignition)
- [Payment for Order Flow and Price Improvement — Wharton WIFPR](https://wifpr.wharton.upenn.edu/uncategorized/research-spotlight-payment-for-order-flow-and-price-improvement/)
- [Payment for Order Flow and Broker-Dealer Regulation — Congress.gov CRS](https://www.congress.gov/crs-product/IF12594)
- [Small Cap Momentum Scanner + Volume + Structure Playbook — Prodigy](https://prodigytradingteam.com/blogs/trading-blog/small-cap-momentum-trading-scanner-volume-structure-playbook)
