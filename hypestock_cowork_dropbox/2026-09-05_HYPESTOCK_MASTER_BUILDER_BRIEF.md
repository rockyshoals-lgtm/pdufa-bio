# HYPESTOCK.ORG — MASTER BUILDER BRIEF (v1, 2026-09-05)

**Classification: BUILD PACK.** From the trading-side research assistant. Same working model
as pdufa.bio: this dropbox is the channel, `INDEX.md` is the log, briefs are directives,
audits will follow builds. Domain is registered and David controls DNS. Host on Vercel.

---

## 1. What hypestock.org IS (and is not)

**IS:** the public research arm of a working momentum desk. Studies, playbooks, and
statistics about how hype stocks actually behave — earnings rockets, gap continuation,
runner anatomy, fade mechanics — derived from tens of thousands of measured events. The
voice: quantified, honest about base rates, allergic to guru-speak. Every claim carries its
n and its p-value. The moat is the same as pdufa.bio's: we publish numbers nobody else has
because nobody else measured them.

**IS NOT (v1):** a live board, a quote site, a signals service, or a paid product. No live
prices, no real-time movers, no alerts. That version requires market-data redistribution
licenses we do not hold (see §3 — this is a hard wall, not a preference).

## 2. Launch information architecture

```
/                       Home: latest study + the flagship stat wall (see §4)
/studies/               The library. One URL per study, dated, with methodology sections.
/playbooks/             Actionable-format rewrites: "The Gap Playbook", "The AH-Pop Fade",
                        "The Day-2 Scalp Lane", "The Reverse-Split Tell"
/glossary/              gap, o2h, fade, rvol, float rotation, AH pop, BMO/AMC ... one URL
                        per term (the pdufa.bio glossary SEO play, repeated)
/about + /methodology   Who, how measured, data sources, and the disclaimer doctrine
```

SEO thesis (proven on pdufa.bio): long-tail question pages win. "do stocks that gap up
keep going", "what percent of earnings movers continue the next day", "why do after hours
spikes fade at the open" — our studies ARE the answers, with numbers. Same JSON-LD,
FAQ-markup, freshness-stamp treatment the builder already knows.

## 3. THE LICENSING WALL — read before writing a single data table

David asked whether our current APIs can power the site since we are not charging.
**Answer: no, and free-vs-paid is irrelevant.** The restriction is on DISPLAY TO THIRD
PARTIES, not on revenue:

- Polygon individual plans: data "solely for personal, non-business use"; redistribution
  requires written authorization and their business tier.
- FMP: no public display or redistribution without a separate Data Display & Licensing
  Agreement.
- Unusual Whales / ORATS / BiopharmaCatalyst: internal use; do not republish.

**Therefore, hard rules for this site:**
1. **NEVER render raw market data**: no price tables, no quote strips, no per-ticker OHLC,
   no live or delayed movers lists sourced from our feeds.
2. **Derived aggregate statistics are OK** — "58.3% of +10% earnings gappers touched +5%
   from the open (n=103, Aug 2026)" is research output, transformed and non-substitutive
   for the underlying feed. This is the entire content model.
3. **Charts = TradingView embed widgets only.** TradingView carries the display licenses;
   we never serve price data ourselves.
4. **Per-ticker examples in studies**: keep them (a study needs its GRRR and its KLRS),
   but as narrative with at most the headline % move — never reconstructable data series.
5. Public-domain sources (SEC EDGAR, ClinicalTrials.gov) are unrestricted; cite them.
6. If we later want a live board, that is a LICENSING PROJECT first (Polygon business
   tier or an exchange-licensed vendor), not a build project. Do not soft-launch one.

## 4. Content pack v1 (`content_pack_v1\`) — 11 pieces, publish order

| # | source file | publish as | note |
|---|---|---|---|
| 1 | `PLUS5_STUDY_2026-08-28.md` | flagship: "The +5% Study" (split into 2: gap edition + intraday edition) | headline stats: \|gap\|≥10 → 57.2% vs \|gap\|≤3 → 19.0% (n=5,470, p=5e-95); gap predicts RANGE not direction |
| 2 | `_earnings5_study_raw_output.txt` | "Do Earnings Rockets Keep Going?" (I draft below, §5) | the newest study; strongest question-match for SEO |
| 3 | `HOW_THE_ALGOS_WORK_playbook.md` | "How Momentum Algos Actually Work" | editorial pass required (strip internal tool names) |
| 4 | `MONDAY_PLAYBOOK.md` | "The Monday Earnings Playbook" | genericize; remove live watchlist names |
| 5 | `Runner_DNA_Study_week_of_2026-07-20.md` | "Anatomy of a Runner" | pair with runner-agent DNA stats: median gap +44%, median high +104%, median fade −38%, 60% under 10M shares |
| 6 | `RUNUP_ANATOMY_2026-07-21.md` | "Anatomy of a Run-Up" | |
| 7 | `REVERSE_SPLIT_EDGE.md` | "The Reverse-Split Tell" | |
| 8 | `THE_925_LOCK.md` | "The 9:25 Lock" | |
| 9 | `SERIAL_PUMPER_2026-07-09.md` | "Serial Pumpers: the Repeat-Runner Effect" | 23/138 tickers ran on multiple days; DFNS ×5 |
| 10 | `Getting_Ahead_Of_The_Crowd_2026-08-01.md` | "Getting Ahead of the Crowd" | |
| 11 | `CONTINUATION_ENGINE_2026-07-09.md` | "Continuation: When Runners Keep Running" | merge with the Day-2 numbers in §5 |

**Editorial doctrine for ALL pieces (non-negotiable):**
- Strip: personal P&L, account sizes, position sizes, broker names, internal file paths,
  internal system names (nest_egg, ODIN, GUNGNIR, board URLs). "Our scanner" is fine.
- Strip live/forward watchlists and any named forward trade. Historical examples stay.
- Keep: every n, every %, every p-value, every date range, every honest negative result
  (the null results are credibility gold — publish the "LLM verdicts predict nothing" and
  "earnings reactions don't persist per company" findings as their own piece later).
- Every page footer: "Educational and informational only. Not investment advice. Trading
  involves substantial risk of loss." No exceptions, no page without it.
- No performance claims, no "we made X%", no implied track record.

## 5. Draft core stats for piece #2 — "Do Earnings Rockets Keep Going?" (837 events, Aug 8–28 2026)

- 41.6% of earnings reporters touched +5% from the open on their reaction day; only 20.4%
  closed up 5%+; ~half closed green at all. **The touch is common; the hold is rare.**
- Rockets (gap ≥ +10%): 58.3% touched +5% from the open vs 39.2% for everything else
  (p=2.5e-04). But median open-to-close was +0.2% and 40% faded to −3% or worse.
- **The BMO/AH asymmetry (the headline):** same-morning gap-up rockets closed green 61.7%
  (median o2c +1.7%); overnight AH-pop rockets closed green only 42.9% (median −2.6%),
  and HALF faded ≥3%. Identical touch rate (~58%). The open auction prices the AH pop;
  a morning gap is still moving. **Scalp both; only the morning kind ever earned a hold.**
- Dumps (gap ≤ −5%): 59.0% touched +5% from the open — the bounce is as tradeable as the
  rocket.
- Day 2: big movers gapped up again only ~48% of the time and median day-2 o2c was −1.5%
  — continuation-as-a-hold is dead. But day-2 touch rate was 37–39% vs 19% baseline: a
  2x relative edge, strictly as a scalp.
- Methodology notes to publish: reaction-day identification (87% agreement vs labeled
  subset), $1 price / $2M dollar-volume floors, |gap|>60% corporate-action guard, daily
  bars (intraday path not modeled).

## 6. Cadence + refresh

v1 is static content — no live feed, so no `latest\` auto-publish yet. When a study
refreshes (the earnings study reruns in ~5 min from cache), I file the updated numbers
here as a dated drop and the builder updates the page + freshness stamp. Target: one new
or refreshed study every 1–2 weeks. The null-results piece and the "12 sessions of
tape lessons" retro are the next two in the queue.

## 7. Open items for David (the builder should not start these)

1. Vercel: create the hypestock project / confirm the builder agent has access.
2. DNS: point hypestock.org at Vercel when the builder has a preview up.
3. Editorial sign-off: pieces #3 and #4 need his read after the internal-name strip.
4. Decide the byline/brand voice (anonymous desk? "the 9 Realms desk"? affects About page).

*All site content: educational/informational only, not investment advice.*
