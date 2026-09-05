# 🧬 Runner DNA — what the +100% movers shared (week of 7/20–7/24)

*22 stocks ran +100% intraday from prior close this week (≥$500k day dollar-volume). Educational, not investment advice.*

## The profile is astonishingly consistent

| Trait | Finding |
|---|---|
| **Price** | median prior close **$1.40** · 9/22 under $1 · 21/22 under $5 · only 1 above $5 |
| **Market cap** | median **$6M** · **17/22 under $50M** · ZERO above $300M — these are nano-caps |
| **Float rotation** | median **19.6× the entire float in one day** · max 739× (INLF) · 19/22 rotated ≥1× |
| **Security type** | 22/22 common stock (no ETFs) |
| **Country** | **14/22 China / HK / Singapore (64%)** — CN 10, HK 2, SG 2 |
| **Fade from high** | median **−36%** · only 9/22 closed within 25% of the high |
| **Repeat offenders** | OMH ran twice in one week (7/21 and 7/24) |

**The archetype in one sentence:** a **sub-$2, sub-$50M-cap micro (often Chinese) whose entire float churns 20+ times in a day, spikes 100–2000%, then gives back a third or more.** That's not a company story — it's a float mechanic.

## The most important discovery: the biggest ones DON'T gap

The runners split ~50/50 into two archetypes — but they are not equal:

- **Gap-and-go (12/22):** opens up big (+25% to +300%), continues. These you catch pre-market.
- **Intraday ignition (10/22):** opens *flat*, then detonates mid-session. **And the biggest movers of the week were ALL ignitions:**
  - **CPHI**: gap −5%, then **+2,131% from the open**
  - **STAK**: gap −7%, then **+876% from the open** (ignited ~1pm ET)
  - ADVB +125%, PN +132%, PAVS +143%, ZBAO +143%, ANPA +117%, JZXN +106%, DFNS +109% — all opened flat.

**Our pre-market gap scanning structurally cannot see these** — they look like nothing at the open. The edge is detecting the *ignition* (sudden float rotation + price/volume acceleration from a quiet base), not the gap.

## Float rotation is the king feature

Median **19.6×**. The extremes map to the extremes: INLF 739× (+118%), ZCMD 112× (+714% intraday), KIDZ 136×, VIVK 212×. When a nano-cap's whole float trades 20+ times, there is no supply left to absorb buyers — the price goes vertical. We already compute `float_rot`; this week says it's **the** dominant runner signal, and its *escalation through the day* is the live ignition tell.

## What to add / tune in the momentum scanner

Ranked by expected value:

1. **🔥 INTRADAY-IGNITION detector (the big gap).** Flag a name that was quiet, then in a short window shows *float rotation crossing ~1–3× AND price/volume accelerating from a flat base.* This is the only way to catch the CPHI/STAK-class monsters early — they never gap. Highest-value add on the board.

2. **🧬 RUNNER-DNA composite flag.** One badge when a name matches the confirmed profile: **price < $5, mcap < $50M, float_rot ≥ 1× (climbing), dollar-vol exploding.** When all align, it's a prime runner candidate — float it to the top and fire the runner alarm earlier.

3. **🇨🇳 Origin + recent-IPO tags.** Country was a real signal (64% CN/HK/SG). A "CN micro" / "recent IPO (<12mo, low float by construction)" tag tells you the *character* instantly — these run violently and fade violently.

4. **Feed this week's 21 into the serial-pumper registry.** OMH already repeated. These names recur; pre-loading them means they light up faster next time.

## The other half of the truth — this is also a danger map

Median fade −36%; two-thirds closed well off the high. **This exact profile is what burned you on MSS** ($1M cap micro, collapsed −28%). So the same flag that says "biggest gainer" also says **"violent, size down, have your exit ready."** The scanner should surface these *with* the risk context, not as a green light — which is why the ignition flag pairs naturally with the **exit engine** and the **liquidity/size guardrail** still on the build list.

---
*n = 22, one week — suggestive, not proven. The right move is to log runners daily and let this dataset grow, same as the PR-lag study.*
