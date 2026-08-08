# External research — audited findings (for the builder)

_Informational and educational only — not investment advice. Odin Catalyst LLC._

**What this is:** third-party research (Gemini / Perplexity) on intraday surge continuation, **after audit**.
I independently verified every load-bearing citation before including it here — checked the source exists and
actually says what was claimed. Only vetted, decision-relevant findings are below. Practitioner blog claims are
kept **only** as clearly-labeled hypotheses to backtest, never as evidence.

**Audit status — Round 1 (Perplexity), audited 2026-07-01.** All five load-bearing academic/regulatory
sources confirmed REAL and fairly represented. Two corrections noted below. (Gemini round to be appended.)

---

## Verified findings worth using

| # | Finding | Source (verified) | Strength | Relation to our study | Builder action |
|---|---------|-------------------|----------|-----------------------|----------------|
| 1 | Among small-cap ≥20% opening-gap names, **moderate gaps (20–50%) had higher same-day win rates (~49.7%) than large gaps (>50%: ~42–44%)** — bigger gaps continue *less*. | Suomela, *Momentum Gap and Go*, Turku UAS bachelor thesis, 2024 (374 NYSE small-caps, 1 yr) | Med | **Corroborates** our "big early moves exhaust" (50%+ first-hour → ~39% continued) | Keep the move-size penalty; treat >50% early moves as lower-probability |
| 2 | Intraday **opening-range-breakout momentum is real but regime- and threshold-dependent** — profitable mainly in volatile states, sensitive to parameters. | Holmberg, Lönnbark & Lundström, *Finance Research Letters* 10(1):27–33, 2013 (peer-reviewed) | High | **Refines** — our high continuation rates are conditional on regime/filters, not universal | Add a volatility/regime variable; don't present continuation % as regime-independent |
| 3 | In that 374-stock sample, **trading volume had minimal correlation with gap-day profitability** — volume was not a strong predictor. | Suomela, ibid. | Med | **Challenges** our inverse-volume result — *but* different metric (whole-day volume vs P&L, not first-hour RVOL vs continuation) | Treat our volume→continuation signal as a **hypothesis**; prove it adds out-of-sample lift vs a price-only model before trusting it |
| 4 | **LULD trading halts hit small (Tier-2) stocks far more, cluster in the first 15 min, and most reverse quickly** (liquidity-gap pauses often revert toward pre-pause price). | SEC DERA, *"Limit Up–Limit Down" Pilot Plan and Associated Events*, 2017 (regulator, large sample) | High | **Refines** — halts truncate/reverse intraday moves even on real demand | Add halt/LULD flags; down-weight continuation odds for names hitting multiple limit states early |
| 5 | **Micro-cap pump-and-dumps are common; 81% of accounts in organized social-media pumps lost money or broke even**; moves driven by concentrated turnover from a few accounts. | ASIC Report 732, *Pump and dump of micro-cap securities*, 14 Jul 2022 (regulator) | High | **Supports** caution — some explosive gainers are manipulation, not momentum | Add a manipulation-risk flag (tiny cap, thin pre-event liquidity, social surge, concentrated turnover); down-weight those |
| 6 | Return decomposition: **past-intraday-return portfolios show momentum (no long-run reversal); overnight returns show none.** News drives overnight; trading drives intraday. | Barardehi, Bogousslavsky & Muravyev, *Review of Financial Studies* (forthcoming), SSRN 4069509 | High | **Neutral→supportive** of intraday momentum existing; cautions against generalizing our micro-cap result to the broad cross-section | Model overnight gap vs first-hour drift vs rest-of-day separately |

## Candidate features to BACKTEST (practitioner lore — hypotheses, not evidence)
Sourced from trading blogs / indicator authors (TradingView RVOL, JournalPlus, Tickerdaily, TradeWink,
DayTradeLab, AlgoPandas). No peer-reviewed backing — test each in a leakage-free backtest before trusting:
- **Float rotation** (intraday volume ÷ float), not just volume ÷ ADV: ~2–3× = strong/tradable, >5× = blow-off/exhaustion risk. Plausibly a better normalizer than ADV for low-float names.
- **RVOL bands:** ~1× "quiet," 2–3× "expansion," ≥5× "climax/exhaustion." Rhymes with our finding but is un-backtested.
- **VWAP + close-in-range continuation cue:** above VWAP AND within ~3% of the day high AND relvol >2 = continuation candidate; failure to reclaim VWAP + close in lower half = fade. (This matches our close-in-range signal.)
- **Exhaustion-bar exit:** a bar with ≥4× its recent average volume that closes in the lower half of its range often marks a local top within 1–3 bars.

## Corrections to the raw Perplexity output
- The ORB paper is **Finance Research Letters (2013)**, authors **Holmberg, Lönnbark & Lundström** — Perplexity's table mislabeled it "Journal of Banking & Finance" and dropped the third author.
- Perplexity framed the RFS "Day and Night" paper as *challenging* intraday momentum. It actually finds intraday-return momentum **persists** — so it's neutral-to-supportive, not a refutation. Use it for the day/night split, not as evidence against us.
- The gold-futures ORB thesis (Sönnert, Umeå) Perplexity cited is tangential (single commodity) — not used here.

## Methodology upgrades to adopt (agreed by the research + our own caveats)
1. **Point-in-time universe incl. delisted names** — fixes survivorship (our biggest bias).
2. **Define events prospectively** (e.g., all names gapping ≥X% at the open, regardless of where they close) — removes selection-on-outcome. This is exactly the prospective-logging plan in `SURGE_RADAR.md`.
3. **Regime variables** (VIX, micro-cap turnover, retail-activity proxy) + out-of-sample across years — 2020–21 was an unusually manic micro-cap tape.
4. **Realistic slippage / partial fills / halts** — micro-cap execution can erase a paper edge.

## Sources (verified)
- Suomela, *Momentum Gap and Go* — https://www.theseus.fi/handle/10024/875321
- Holmberg, Lönnbark & Lundström, *Assessing the profitability of intraday opening range breakout strategies*, Finance Research Letters 2013 — https://ideas.repec.org/a/eee/finlet/v10y2013i1p27-33.html
- Barardehi, Bogousslavsky & Muravyev, *What Drives Momentum and Reversal? Evidence from Day and Night Signals*, RFS — https://doi.org/10.2139/ssrn.4069509
- SEC DERA, *"Limit Up–Limit Down" Pilot Plan and Associated Events* — https://www.sec.gov/files/dera-luld-white-paper.pdf
- ASIC Report 732, *Pump and dump of micro-cap securities* — https://www.asic.gov.au/regulatory-resources/find-a-document/reports/rep-732-pump-and-dump-of-micro-cap-securities/

_Bottom line: the external evidence corroborates "big moves exhaust" and adds two real risk features (halts,
manipulation), but the specific volume→continuation edge is not independently established — one academic
sample found volume uninformative. Treat our volume rule as a hypothesis and validate it prospectively,
leakage-free, before it drives any live sizing._


---

# Round 2 — Gemini (audited 2026-07-01)

**Audit status: all load-bearing citations verified REAL and fairly represented.** Gemini's sourcing was
stronger than expected; one citation I initially suspected was fabricated turned out to be a genuine second
SEC paper.

Verified:
- **Gao, Han, Li & Zhou, "Market Intraday Momentum," *Journal of Financial Economics* 129(2), 2018** — SPY 1993–2013, first half-hour predicts last half-hour; stronger on high-volume/high-volatility/news days. REAL.
- **Lou, Polk & Skouras, "A Tug of War: Overnight vs Intraday Expected Returns," *JFE* 134(1), 2019** — momentum profits accrue **overnight**; intraday shows offsetting **reversal**. REAL.
- **SEC DERA LULD** — TWO real papers exist: Moise & Flaherty ("…Associated Events," used in Round 1) *and* Hughes, Ritter & Zhang ("…Extraordinary Transitory Volatility," cited by Gemini). Gemini's cite is legit, not fabricated.
- **German pump-and-dump study** — it's **Leuz, Meyer, Muhn, Soltes & Hackethal, "Who Falls Prey to the Wolf of Wall Street?"** (NBER w24083 / Management Science 2023): 470 schemes, 110,000+ investors, ~8% participate, avg loss ~30%. Gemini quoted the stats accurately but didn't name the paper.

## What Gemini adds beyond Round 1

| Finding | Source | Strength | Relation to our study | Builder action |
|---|---|---|---|---|
| For **individual stocks, intraday returns are structurally mean-reverting**; momentum is largely an *overnight* phenomenon (institutions/HFT provide liquidity against retail intraday momentum). | Lou/Polk/Skouras 2019 | High | **Challenges the core premise** — "buy early and ride to the close" fights the structural grain; the edge (if any) lives in a narrow sub-case, not the default | Treat continuation as the exception to prove, not the assumption; separately model overnight vs intraday |
| In **large-caps, HIGH early volume STRENGTHENS** intraday momentum (opposite of our micro-cap finding). | Gao et al. 2018 | High | **Reconciles** the contradiction: volume's sign flips by asset class — large-caps digest info (continuation), micro-caps burn float (exhaustion) | Don't port a volume rule across cap tiers; keep the micro-cap exhaustion logic micro-cap-only |
| Mechanistic causes of the fade: **LULD halts** (cluster first 15 min, break momentum, post-pause reversion), **VWAP gravitational pull** (algos fade large VWAP deviations), **ATM dilution** (silent supply wall into spikes), **short-squeeze exhaustion + 300–1000% borrow fees**, **options dealer gamma** (afternoon momentum from OMM hedging). | SEC DERA (High); rest mechanism/practitioner (Med/Low) | Mixed | **Explains** why big moves fade — gives mechanism-based features, not just correlations | Add features: LULD halt count, VWAP deviation, borrow fee / days-to-cover, ATM-shelf flag, catalyst quality |
| The **95% figure is a selection-on-outcome / look-ahead artifact** and non-tradable live. | Methodological (sound) | High | **Consensus with Round 1 + our own caveat** — this is the single most important point | Do not present continuation % as a live win rate; the prospective log is mandatory |

## CONSENSUS SYNTHESIS (both engines + audit) — what the builder should actually take

1. **"Big early moves exhaust" is corroborated** (Suomela gap-size; Gemini's float-burn/LULD/VWAP mechanisms). Keep the move-size and blow-off penalties.
2. **Our continuation rates are inflated by selection bias — they are NOT live win rates.** Both engines flag this independently. The prospective, point-in-time log (defining events at the open, including delisted names and eventual faders) is the only honest path to a tradable number.
3. **The volume→continuation edge is unproven** — one academic sample found volume uninformative (Suomela); large-caps show the *opposite* sign (Gao). Our inverse-volume rule is a **hypothesis**, plausibly real via the float-burn mechanism, but must be validated prospectively and leakage-free before it sizes anything.
4. **The default micro-cap intraday bias is mean-reversion** (Tug of War). "Hop on early and ride" is swimming against the current; any edge likely lives in a specific subset — low-relative-volume gap-and-grind, above VWAP, with a real Tier-1 catalyst, absent halts/dilution — not in chasing loud movers.
5. **Add these real risk/microstructure features** (highest-value additions): LULD halt count, VWAP deviation, float rotation, borrow fee / DTC, ATM-dilution flag, catalyst quality (verified news vs promo), pump-and-dump signature.
6. **Stats discipline:** with multiple volume thresholds tested, apply walk-forward + a multiple-testing correction (Deflated Sharpe / Bonferroni) to avoid data-snooping.

## Caveats on Gemini's output
- Some specifics are mechanism/practitioner-level, not peer-reviewed facts: "70% of pre-event accumulation within 1 hr," borrow "300–1000%," the "-67% median 120-day" figure, the Chinese "IVU" ML study, and the options-gamma "afternoon momentum" mechanism. Directionally reasonable; label as hypotheses, don't quote as established.
- Gemini's concrete "short/fade to VWAP" rules describe a **different (short) strategy** than our long-only "ride it early" book, and are phrased as trade instructions — keep them as backtest hypotheses, not recommendations. (Informational/educational only.)
