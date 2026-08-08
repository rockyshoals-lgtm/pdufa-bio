# Conference Run-up Study — 2022-06 → 2026-02
**Built:** 2026-07-11 · **n = 220 conference-presenter events · 1,531 baseline readout events · 142 unique tickers**
**Data:** Gungnir readout universe (conference-tagged via catalyst text) + cached D-30/D-20/D-10/D-5/D-1 and D+1/D+5 price series.
*Facts and historical statistics only. Not investment advice.*

---

## ⚠️ Headline: there is no systematic conference run-up.

This is not the result we expected, and it **contradicts the internal Conference Overlay v1.0 numbers.** It is also, I think, the most valuable thing we could possibly publish.

| Window (price at D-1 vs D-N) | Conference presenters | Baseline (non-conference readouts) | Significance |
|---|---|---|---|
| **30-day run-up** | **median −0.79%** (n=219) | median 0.00% (n=1,529) | **p = 0.924 — indistinguishable** |
| 20-day | median −0.18% | 0.00% | — |
| 10-day | median −0.56% | +0.03% | — |
| **5-day run-up** | **median +0.72%** (n=220) | +0.14% (n=1,531) | p = 0.062 — marginal, not significant |

**Conference presenters do not, on the median, run up into their presentation.** A Mann-Whitney test against the non-conference baseline returns **p = 0.924** for the 30-day window — statistically indistinguishable from any other readout event.

---

## The mean is a lie — the tails are the whole story

| 30-day run-up (all presenters, n=219) | |
|---|---|
| **Mean** | **+5.56%** |
| **Median** | **−0.79%** |
| Std dev | 31.8% |
| Min / Max | −81.1% / **+228.2%** |

The positive *mean* is generated almost entirely by a right tail. The typical presenter goes nowhere.

**Distribution of 30-day run-up:**

| Ran up ≥ | Share of presenters |
|---|---|
| +50% | 6.4% (n=14) |
| **+25%** | **15.5% (n=34)** |
| +10% | 26.5% (n=58) |
| 0% (any gain) | **47.0%** — *worse than a coin flip* |

---

## Micro/small-cap — what retail actually trades (n=108–109)

| Window | Median | p25 | p75 | Mean |
|---|---|---|---|---|
| 30-day run-up | **−0.10%** | −13.60% | **+27.45%** | +9.98% |
| 20-day | +0.81% | −7.32% | +16.00% | +6.97% |
| 10-day | 0.00% | −5.66% | +8.88% | +4.15% |
| **5-day** | **+1.25%** | −3.23% | +8.01% | +3.78% |
| Event day (D-1→D+1) | −0.74% | −5.83% | +4.88% | +2.60% |
| **D-1 → D+5** | **−2.66%** | −11.86% | +7.23% | +1.55% |

**The two numbers that matter:**
- **26.6%** of micro/small presenters ran up **≥25%** in 30 days *(the WHWK-type outcome)*
- **11.9%** fell **≥25%** in the same window

So: roughly **1 in 4** delivers a big run-up, **1 in 8** hurts badly, and the middle half spans **−13.6% to +27.5%.** That is a fat-tailed lottery, not an edge.

**Note on post-event drift:** micro/small median is **−2.66% by D+5**. Whatever move happens tends to fade. (Observation, not advice.)

---

## By conference (30-day run-up, n≥5) — treat as directional only

| Conference | n | Median | p25 | p75 |
|---|---|---|---|---|
| ASCO-GI | 5 | +10.20% | −6.89% | +40.75% |
| SITC | 10 | +9.19% | −7.47% | +31.08% |
| AACR | 8 | +6.90% | −13.34% | +29.22% |
| ASH | 36 | +2.81% | −6.54% | +9.22% |
| WCLC | 7 | +0.09% | −4.19% | +2.73% |
| ASCO | 45 | −0.58% | −5.20% | +13.46% |
| EHA | 15 | −0.90% | −9.98% | +3.08% |
| AASLD | 6 | −3.49% | −12.42% | +10.67% |
| EASL | 7 | −3.68% | −8.70% | +3.24% |
| ASCO-GU | 6 | −4.30% | −7.15% | −2.32% |
| ESMO | 38 | −4.87% | −11.17% | +4.00% |
| AHA | 5 | −19.30% | −29.41% | +4.78% |

**Do not over-read these.** Most cells have n < 15. AACR/SITC/ASCO-GI look positive, but with n=5–10 and p75–p25 spreads of 40+ points, these are noise-dominated. **Publish with n visible, or not at all.**

**By year (30d median):** 2022 −3.83% (n=32) · 2023 −0.58% (n=77) · 2024 −1.00% (n=70) · 2025 +0.54% (n=39). No trend.

---

## 🚨 This contradicts Conference Overlay v1.0 — do not publish the old numbers

| Metric | Overlay v1.0 claim | This study |
|---|---|---|
| Nano/micro D-30→D-1 | **median +4.88%**, win rate 58.5% | **median −0.51%** (micro/nano, n=55); micro+small combined **−0.10%** |
| Small-cap D-5→D-1 | median +3.02%, win rate 66.7% | **median +2.27%** (n=54) — *this one roughly holds* |

The **5-day small-cap figure reproduces** (+2.27% vs +3.02% claimed). The **30-day micro/nano figure does not** — it flips from +4.88% to −0.51%.

**Likely causes of the gap (needs resolution before anything ships):**
1. **Selection bias** — the overlay's sample may be drawn from *scored/selected* presenters (the trade list), not all conference-tagged events.
2. **Mean vs median** — our micro/small *mean* is +9.98%; a mean reported as a median would explain the direction of the error.
3. **Anchor mismatch** — we anchor on the date the conference data was reported; the overlay anchors on the conference *start* date.

Until that's resolved, **the +4.88% / win-rate numbers should not be published, used in the Conference Overlay, or shown to users.**

---

## About WHWK

WHWK (AACR, April 2026) falls **outside this sample** — the Gungnir readout universe ends 2026-02, so it isn't in the 220.

But the honest read: **a +25% conference run-up is exactly what the right tail of this distribution looks like.** 26.6% of micro/small presenters gained ≥25% in 30 days. WHWK was a real win, and it was also a *frequent-enough tail outcome* — not evidence of a systematic edge. One winner drawn from a fat-tailed distribution is not a strategy. (This is precisely why the study is worth publishing.)

---

## Limitations — state these publicly

1. **Coverage is 2022-06 → 2026-02, not 2020.** No presenter source exists in the data for 2020–21. *(Backfill would require ingesting company PR archives or ASCO/ASH/ESMO abstract archives — see next steps.)*
2. **Anchor = the date the conference data was reported**, not the official conference start date, and **not the abstract/title-drop date** — which is very likely the true catalyst and sits weeks earlier. **This is the single biggest methodological gap.** A dual-anchor rebuild (abstract-drop *and* conference start) could materially change the 30-day picture.
3. **Selection bias:** the universe is "readout events whose data was presented at a conference" — i.e. conditioned on the data being newsworthy. It is **not** "all companies that presented."
4. **Presentation type unusable** — 215/220 came back "unspecified"; the catalyst text doesn't reliably encode oral/poster/late-breaking. Needs a real presenter/abstract source.
5. Small per-conference n. Don't slice thinner than reported.

---

## What to do with this

**Publish it.** This is a genuinely original, honest research page that no competitor has, and it *is* the brand:

> **"Do biotech stocks run up into medical conferences? We checked 220 presentations. Mostly, no."**

- Median presenter: **flat**. Statistically indistinguishable from any other readout (p=0.92).
- The average is positive only because **1 in 6** presenters moves >25%.
- **1 in 4** micro/small presenters ran ≥25%; **1 in 8** fell ≥25%.
- Whatever move happens tends to **fade by D+5**.

This lands perfectly on "facts, not edge claims" — it's the anti-hype research page, it's link-bait for biotech media, it protects users, and it directly justifies why pdufa.bio refuses to sell probability scores. **It is also the strongest possible argument for keeping the Conference Overlay internal and out of the public product.**

### Next steps to strengthen it
1. **Dual-anchor rebuild** (abstract-drop date + conference start date) — the biggest potential change to the result.
2. **Reconcile the +4.88% discrepancy** with Conference Overlay v1.0.
3. **Backfill 2020–21** via a presenter source (PR archives / abstract archives).
4. Add a proper **presenter universe** (all presenters, not just newsworthy readouts) to kill the selection bias.

---
## Files
- `conf_study/conference_events_raw.csv` — 250 conference-tagged events (ticker, anchor, conference, cap tier, stage)
- `conf_study/conference_runup_events.csv` — **220 events with full run-up windows** (the publishable dataset)
- `conf_study/baseline_runup_events.csv` — 1,531 non-conference readout baseline
- `conf_study/RESULTS.txt` — raw output
- `conf_study/study.py` — reproducible script

*Facts and historical statistics only — no trade recommendations, no outcome probabilities. Not investment advice.*
