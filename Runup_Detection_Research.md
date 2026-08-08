# Detecting Stock Runups at Inception — Research Brief

*Prepared for 9 Realms momentum scanner development. July 2026.*
*Informational/educational only — not investment advice.*

---

## Executive summary

The core empirical finding across the literature is that **the earliest, most reliable runup signals are not price itself — they are the footprints informed traders leave in adjacent markets (options, the securities-lending tape, insider filings) and in the *texture* of the early price/volume move.** Price momentum is real but it is a lagging confirmation; by the time a stock is obviously "up," the informational edge has largely decayed.

Five signals clear the bar of being (a) academically validated with real effect sizes, (b) genuinely *leading* rather than coincident, and (c) buildable from your FMP + Unusual Whales data:

1. **Unusual options activity before catalysts** — leads by 1 day to 3 weeks; the single best-documented biotech edge.
2. **Securities-lending pressure (borrow fee + utilization) into a catalyst** — the "coiled spring" setup; the only *timely* short-interest signal.
3. **Move texture: gradual drift toward the 52-week high on modest/institutional volume** — the "frog-in-the-pan" early-stage signature.
4. **Opportunistic / cluster insider buying in small caps** — retains alpha *after* it's public, on a days-to-months horizon.
5. **Attention & retail-order-flow spikes (Google SVI, retail imbalance)** — lead by ~1–12 weeks, best as a confirmation layer.

A critical, counterintuitive theme: **high volume is a double-edged sword.** A volume spike predicts higher returns at the monthly horizon (high-volume return premium), but high *turnover on an already-winning stock* marks the LATE, reversal-prone stage. The cleanest early-runup profile is a quiet, continuous drift — not a high-turnover gap-up blowoff.

---

## 1. Unusual options activity — the strongest leading edge

Options traders with an information advantage move *before* the stock, and the effect is strongest exactly where you operate: small caps with binary catalysts.

- **Biotech, directly on point.** Across 352 FDA drug decisions (1996–2016), implied-volatility spreads, call volume, and call order imbalance are significantly elevated in the **five trading days before** the announcement and predict the announcement-day return — with abnormal volume *much larger for small firms* (Bohmann & Patel 2022, *JBFA*). A companion study on 319 FDA advisory-committee meetings finds abnormal options volume appearing weeks earlier, timed to *nonpublic* report-creation dates, and it predicts the approve/reject direction (Wu, Borochin & Golec 2024, *JCF*).
- **General predictability.** Low buyer-initiated put-call ratios predict >40 bps next-day and >1% next-week returns (Pan & Poteshman 2006, *RFS*). Expensive calls relative to puts (deviations from put-call parity) predict ~50 bps/week, ~26%/yr (Cremers & Weinbaum 2010, *JFQA*). Option prices lead equity prices around news events (Jin/Livnat/Zhang 2012; Weinbaum et al. 2023).
- **Magnitude vs direction.** The option/stock volume ratio (O/S) rises before earnings and predicts the *size* of the coming move, not its sign (Roll, Schwartz & Subrahmanyam 2010) — useful for position sizing, not long/short direction.
- **M&A analog.** ~25% of takeovers show abnormal pre-announcement call volume, concentrated in short-dated OTM calls (Augustin, Brenner & Subrahmanyam 2019, *Mgmt Sci*).

**Lead time:** 1 day to ~3 weeks. **Direction:** upside = low put/call, high IV-spread, OTM call volume/imbalance, positive net call premium.
**False-positive caveat:** Only ~25% of even high-information M&A events show a detectable options lead — meaning *absence* of a signal means little, and academic alphas are cross-sectional averages, not per-name hit rates. Most single "unusual activity" flags are noise.

**→ Build from Unusual Whales:** `uw_options_volume` (call/put volume & premium, vol/OI ratios), `uw_flow_alerts` (sweeps), `uw_greek_exposure`. You already have `uoa_score` — the literature validates its design; weight **net call premium** and **vol/OI on the event-dated expiry** most heavily, and *require* the underlying to be small/mid-cap for the biotech effect.

## 2. Short-interest dynamics — the coiled-spring setup

Most clean SI alphas are *short*-side (heavily shorted stocks underperform). The *upside* use is the inverse: a heavily-shorted stock that meets good news becomes a self-reinforcing short-covering rally.

- **Timeliness is everything.** FINRA exchange short interest is **biweekly and published ~7 business days late** — a stale, coincident indicator. Securities-lending analytics (borrow fee, utilization, shares-on-loan) update **daily** and are the only real-time-usable short signals. Borrow-fee *spikes* are the earliest tape.
- **Utilization is the top squeeze determinant** (shares-on-loan ÷ lendable supply), positive and significant in every regression; squeeze probability rises with spread, turnover, and volume and falls with analyst coverage and size (Allen, Haas, Pirovano & Tengulov 2025, *JBF*). ~25% of stocks experience a squeeze in a given year.
- **Days-to-cover** predicts returns better than raw short ratio (~1.2%/month long-short; Hong et al. 2015) and mechanically governs *how violent* a squeeze becomes.
- **Rising borrow demand** predicts ~-2.98% next-month return (short side; Cohen, Diether & Malloy 2007) — inverted, it flags where a positive surprise is maximally violent.

**Lead time:** borrow-market shifts ~1 month; the squeeze itself is coincident with the catalyst (day 0–5).
**Best composite:** high SI-%-float **AND** high days-to-cover **AND** rising utilization **AND** spiking borrow fee, into a scheduled positive catalyst.

**→ Build:** UW short-data endpoints (`get_short_data_by_ticker`, `get_short_volume_ratio_by_ticker`) + FMP `shares-float`. **Honesty flag from your own notes:** your `short_interest_snapshot.json` is a single April-2026 snapshot applied retroactively — that is lookahead bias. Honest backtesting needs *historical daily* borrow-fee/utilization snapshots, not one static number.

## 3. Move texture — distinguishing early runups from late blowoffs

This is the most actionable and least-appreciated cluster: *how* a stock is moving tells you whether you're early or late.

- **Frog-in-the-pan (continuous vs discrete).** Runups built from many small daily moves produce far more persistent momentum than runups from a few big jumps: over a 6-month hold, continuation falls **monotonically from 8.86% (continuous) to 2.91% (discrete)** (Da, Gurun & Warachka 2014, *RFS*; figures verified against the paper). A quiet, steady drift predicts a bigger subsequent move than a dramatic gap. **→ Compute a daily-information-discreteness metric: sign-consistency of daily returns over the formation window (% up-days, or |cumulative| ÷ Σ|daily|).**
- **52-week-high proximity dominates raw momentum.** Nearness to the 52-week high is a *stronger* predictor of 6-month returns than past returns; controlling for it cuts standard momentum profit roughly in half (George & Hwang 2004, *JoF*), and these returns don't reverse long-run. **→ You already have `pct_of_52w_high`; the research says weight it heavily and favor names breaking to *new* highs.**
- **Early vs late stage via turnover.** Low-turnover winners sustain continuation up to 3 years; high-turnover winners *reverse* in years 2–3 (Lee & Swaminathan 2000, *JoF*). **High turnover on a winner = late-stage fade risk.**
- **High-volume return premium.** Top-5-of-50-day volume spikes → ~0.53%/month (VW) next-month outperformance, *stronger* when the spike is NOT accompanied by an extreme same-day price move (Gervais, Kaniel & Mingelgrin 2001, *JoF*).
- **Volume composition.** Abnormal-volume events dominated by *institutional* positioning predict outperformance; retail-dominated spikes do not.
- **PEAD.** After an earnings surprise, drift continues ~60 trading days (>6% top-vs-bottom hedge) — a usable multi-week window once a catalyst has *started* the move.

**Synthesis — the ideal early-runup fingerprint:** a gradual price drift *toward/through* the 52-week high, on *modest or institutional* volume, built from *many small up-days* rather than one gap. That is the opposite of the retail "gap-and-go" pattern most scanners chase.

**→ Build entirely from FMP EOD history you already pull in Stage 2:** add (a) discreteness/continuity score, (b) up-day ratio, (c) turnover percentile, (d) a "new-52w-high" flag.

## 4. Insider & institutional footprints — public signals that still pay

- **Opportunistic insider buys.** Stripping calendar-predictable "routine" trades leaves "opportunistic" trades earning **82 bps/month value-weighted (~180 bps equal-weighted); routine trades ~zero** (Cohen, Malloy & Pomorski 2012, *JoF*; verified). Purchase side carries the signal (~6%/yr; Jeng-Metrick-Zeckhauser). **Cluster buys ~2× solo; CEO/CFO > directors.**
- **Small-cap amplification.** Insider-buy signal concentrates in small firms (~5–7% 12-month abnormal returns; Lakonishok & Lee 2001) — your universe.
- **Alpha survives publicity.** Because Form 4 files within 2 business days, purchases still predict **4–8% over 6–12 months from the public filing date.** A microcap subset (bought after >10% prior run) earned ~6.3% CAR.
- **13D activist filings — the strongest public signal.** ~7% abnormal return around filing with **no reversal** over the following year (Brav et al. 2008; Klein & Zur 2009). Passive 13G filings: ~zero.
- **13F "best ideas"** outperform ~1–2.5%/quarter, and industry-specialist funds outperform — but the **45-day reporting lag** blunts real-time use.
- **Congressional trading:** largely gone post-STOCK-Act for rank-and-file; residual only in leadership.

**Lead time:** days (Form 4 filing) to months (drift). **→ Build:** FMP `insider-trades`, UW `get_insider_transactions` / `get_congress_trades`. **Filter to opportunistic + cluster + officer-level + small-cap** — an unfiltered insider feed is mostly noise.

## 5. Attention & sentiment — a confirmation layer

- **Google search volume (SVI)** spikes predict a ~2-week price rise, then reversal within a year (Da, Engelberg & Gao 2011, *JoF*) — leads, but mean-reverts.
- **Retail order imbalance** (sub-penny TAQ) predicts ~10 bps next-week returns persisting ~12 weeks (Boehmer, Jones, Zhang & Zhang 2021, *JoF*) — *note a 2024 replication finds the effect weakened recently.*
- **News drift vs no-news reversal.** Prices drift up to ~12 months after real news; large moves *without* news reverse within a month (Chan 2003) — **a no-news price spike is a fade candidate.**
- **Media momentum** is stronger with coverage but reverses long-run (Hillert et al. 2014); daily sentiment leads then reverts (Tetlock 2007).

**Biotech-specific pre-catalyst drift.** Eventual Phase III winners rose **~27% in the 120 days before** announcement vs no move for losers (older sample). In oncology, +9.4% pre-announcement for positive trials vs −4.5% for negative (13.9pp spread, p=0.03; Rothenstein et al. 2011, *JNCI*). **Crucial nuance: trial *readouts* leak (directional pre-drift), but FDA *regulatory decisions* show weak/insignificant pre-decision drift** — so for PDUFA dates, lean on options-flow and order-imbalance signals, not raw price drift. The ASCO **abstract-release date** (days before the meeting) is itself a distinct tradeable catalyst.

**→ Build:** UW `get_dark_pool_trades` (institutional accumulation footprint), news via FMP `news`. Treat sentiment as a *tie-breaker/confirmation*, never a primary trigger.

---

## Signal ranking for the scanner

| Rank | Signal | Leads price? | Typical lead | Effect size (source) | Data source | False-positive risk |
|------|--------|:---:|:---:|---|---|:---:|
| 1 | Options flow into catalyst (net call prem, vol/OI, IV-spread) | **Yes** | 1d–3wk | +40bps next-day; ~26%/yr IV-spread; biotech T-5 predictive | UW options/flow | Med — most flags noise |
| 2 | Borrow fee + utilization spike into catalyst | **Yes** | ~1 mo | Utilization = #1 squeeze determinant | UW short data + FMP float | Med |
| 3 | Continuous drift to 52w-high, modest volume | **Yes** | Weeks | 8.86% vs 2.91% (continuous vs discrete) | FMP EOD | Low–Med |
| 4 | Opportunistic/cluster insider buys (small-cap) | **Yes** (post-filing) | Days–months | 82bps/mo VW; ~6–8%/yr from public filing | FMP/UW insider | Low if filtered |
| 5 | 13D activist filing | **Yes** (at filing) | At announce + drift | ~7%, no reversal | FMP SEC filings | Low |
| 6 | Attention/retail (SVI, retail imbalance) | Yes | 1–12 wk | ~10bps/wk; SVI ~2wk | UW/FMP + external SVI | High — reverts |
| — | High turnover on a winner | Late-stage marker | — | Reverses yrs 2–3 | FMP EOD | *Contra-signal* |
| — | Gap-up + volume, opening-range breakout | Coincides | 0 | Weak/negative in academic tests | FMP intraday | High |

---

## Recommended scanner architecture — a composite "inception score"

Rather than one signal, combine independent leading indicators into a weighted score, gated by your catalyst calendar (ODIN/Gungnir). Suggested v1 blend for the FMP+UW scanner:

- **40% — Move texture (FMP EOD, free & clean):** 52w-high proximity + continuity/discreteness score + up-day ratio + institutional-vs-retail volume proxy, *penalizing* high turnover. This is the highest-signal, lowest-cost layer and works with data you already pull.
- **30% — Options flow (UW):** net call premium + vol/OI on nearest event-dated expiry + sweep count, **gated to small/mid-cap** for the biotech effect.
- **15% — Short-squeeze fuel (UW + FMP):** utilization + borrow-fee change + days-to-cover, as an *amplifier* on names that also have a positive catalyst.
- **15% — Insider/13D (FMP/UW):** opportunistic + cluster + officer-level buys, small-cap; 13D filings as a boost.

Then **overlay your existing catalyst engines**: the literature is unanimous that these signals are strongest *conditioned on a pending event*. A high inception score on a stock with an ODIN T1 PDUFA or a Gungnir readout in the next 4–8 weeks is the highest-conviction configuration.

**Three design rules the research earns:**
1. **Reward quiet, not loud.** Down-weight high-turnover gap-ups; up-weight continuous drift. This alone differentiates you from every retail momentum scanner.
2. **Absence ≠ safety, presence ≠ certainty.** ~75% of real catalysts show no options lead; size accordingly and never trade a single flag.
3. **Only daily-updating short data is real.** Do not backtest on a static SI snapshot — it's lookahead bias (flagged in your own audit notes).

---

## Sources

Options flow: [Pan & Poteshman 2006, RFS](https://academic.oup.com/rfs/article-abstract/19/3/871/1646711) · [Cremers & Weinbaum 2010, JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/deviations-from-putcall-parity-and-stock-return-predictability/D9BA8F97580328AAFD7988B092FE5D50) · [Johnson & So 2012, JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X12000797) · [Roll, Schwartz & Subrahmanyam 2010, JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X09002347) · [Augustin, Brenner & Subrahmanyam 2019, Mgmt Sci](https://ideas.repec.org/a/inm/ormnsc/v65y2019i12p5697-5720.html) · [Bohmann & Patel 2022, JBFA — FDA](https://onlinelibrary.wiley.com/doi/full/10.1111/jbfa.12600) · [Wu, Borochin & Golec 2024, JCF — FDA advisory](https://www.sciencedirect.com/science/article/abs/pii/S092911992300144X)

Short interest / squeeze: [Boehmer, Jones & Zhang 2008, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01324.x) · [Asquith, Pathak & Ritter 2005, JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X05001170) · [Hong et al. 2015, NBER — days-to-cover](https://www.nber.org/papers/w21166) · [Cohen, Diether & Malloy 2007, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2007.01269.x) · [Allen, Haas, Pirovano & Tengulov 2025, JBF](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4526147) · [FINRA Rule 4560](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4560)

Move texture: [Gervais, Kaniel & Mingelgrin 2001, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00349) · [George & Hwang 2004, JoF](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf) · [Lee & Swaminathan 2000, JoF](https://www.lsvasset.com/pdf/research-papers/Price-Momentum-Trad-Vol-2000.pdf) · [Da, Gurun & Warachka 2014, RFS — frog in the pan](https://www3.nd.edu/~zda/Frog.pdf) · [Bernard & Thomas — PEAD](https://en.wikipedia.org/wiki/Post%E2%80%93earnings-announcement_drift)

Insider / institutional: [Cohen, Malloy & Pomorski 2012, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2012.01740.x) · [Jeng, Metrick & Zeckhauser 2003, REStat](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9919.pdf) · [Cohen, Polk & Silli — Best Ideas](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364827) · [Kacperczyk, Sialm & Zheng 2005, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2005.00785.x) · [Brav, Jiang, Partnoy & Thomas 2008, JoF — 13D](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01373.x) · [STOCK Act study 2022, JPubEc](https://www.sciencedirect.com/science/article/abs/pii/S0047272722000044)

Sentiment / biotech: [Da, Engelberg & Gao 2011, JoF — SVI](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2011.01679.x) · [Boehmer, Jones, Zhang & Zhang 2021, JoF — retail](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13033) · [Chan 2003, JFE — news/no-news](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=262452) · [Hillert, Jacobs & Müller 2014, RFS](https://academic.oup.com/rfs/article-abstract/27/12/3467/1849035) · [Tetlock 2007, JoF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2007.01232.x) · [Rothenstein et al. 2011, JNCI — oncology pre-announcement](https://academic.oup.com/jnci/article-abstract/103/20/1507/904625)
