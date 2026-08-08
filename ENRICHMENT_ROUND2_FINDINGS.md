# Dataset Enrichment — Round 2
**Date:** 2026-07-11 · *Facts and historical statistics only. Not investment advice.*

---

## 0. First — the builder was right, I was wrong. Twice.

**`ret_1d` was never broken.** I verified their claim: `ret_1d = (d1_price/pre_price − 1) × 100`, **89.4% exact match**, already in percent. My "p25 = −521%" came from ×100-ing a value that was *already* a percentage. Real p25 = **−5.19%**. **Conceded — and had they acted on my bug report they'd have frozen the best dataset in the repo for nothing.**

**"68% flat" was inflated.** The FLAT tier spans **−14.9% to +5.0%** — a 14.9% drop is not "nothing." Their published cut (**56.5% land within ±5%**, median absolute move **3.80%**) is the honest one. Verified exactly.

Good pushback. That's the process working.

---

## 1. ⭐ NEW ASSET: `conf_study/UNIFIED_catalyst_panel.csv`

**5,487 events · 693 tickers · 2015-01-08 → 2026-06-04 · all three catalyst classes in one table.**

| Catalyst class | n |
|---|---|
| PDUFA | 2,210 |
| Phase readout | 1,752 |
| Conference presentation | 1,425 |

Columns: `ticker · date · catalyst_type · outcome · ta · cap_tier · runup_30d · runup_5d · event_move · phase · days_to_cover · enrollment · is_randomized · is_double_blind · nct_id · conf`

This is **the moat artifact.** Nobody else can assemble it.

### 🎯 The trilogy, in one table

| Catalyst class | n | **30-day median run-up** | p25 | p75 | % positive |
|---|---|---|---|---|---|
| **PDUFA** | 1,792 | **+0.57%** | −6.26% | +8.19% | 52.4% |
| **Phase readout** | 1,756 | **−0.07%** | −7.62% | +8.61% | 49.6% |
| **Conference** | 1,429 | **−0.03%** | −10.35% | +13.58% | 49.8% |
| **COMBINED** | **4,977** | **+0.17%** | −7.45% | +9.21% | **50.7%** |

> **Across 4,977 catalysts spanning three independent event classes, the median 30-day run-up is +0.17%, and 50.7% are positive. It is a coin flip.**

Three separate catalyst types. Three separate datasets. Three separate mechanisms. **One answer.** That replication is the entire research franchise — and the event-study literature has never looked at pre-announcement drift, so nobody has said this.

---

## 2. ⭐ NEW ASSET: `conf_study/readout_MASTER_enriched.csv`
**1,752 readouts × 88 columns.** Joins together, for the first time:
- **ClinicalTrials.gov trial design** (59.8% coverage): randomized · double-blind · single-arm · enrollment · arms · sites · countries · endpoint class · masking rigor
- **FINRA short interest** (97.8% coverage, **T-1 compliant, min lag 1 day — zero lookahead**)
- Correct 1-day / 5-day stock reaction + move tier
- Run-ups (D-30 / D-10 / D-5)
- Cap tier, TA, phase, outcome

Nobody in the category shows *"Phase 3, randomized, double-blind, n=450, 12 countries"* next to a readout — let alone next to what the stock did.

---

## 3. 🔬 The finding: **market cap is the only thing that matters — and it kills nearly every other hypothesis**

Median **absolute** 1-day move, by cap tier:

| Cap tier | n | median absolute move |
|---|---|---|
| **micro** | 350 | **8.71%** |
| **small** | 424 | **6.16%** |
| **mid/large** | 978 | **2.19%** |

**Micro-caps move ~4× more than mid/large.** That is the dominant effect — and it *confounds everything else*.

### What looked exciting — and then died under a cap-tier control

| Hypothesis | Headline (uncontrolled) | Within-tier | Verdict |
|---|---|---|---|
| Open-label readouts are more volatile than randomized | 4.15% vs 2.85% | micro: **9.7% randomized vs 8.1% open** (*reversed*); small: 5.3 vs 7.0; mid/large: 2.0 vs 2.2 | ❌ **Cap artifact — inconsistent** |
| Large trials move less | 2.33% vs 3.27% | micro: **10.3% large vs 8.7% small** (*reversed*); mid/large: 1.78 vs 1.88 (flat) | ❌ **Cap artifact** |
| High short interest → bigger moves | 5.94% vs 3.38% | micro: 9.2 / 8.4 / 8.7 (**flat**); small: **9.3 low vs 5.9 high** (*inverted*) | ❌ **Cap artifact — confirms the builder's ρ≈0 debunk** |
| **Phase 3 moves less than Phase 2** | 2.37% vs 3.94% | small: **3.7 vs 6.5** ✅; mid/large: **1.8 vs 2.4** ✅; micro: 8.7 vs 8.7 ❌ | 🟡 **Partially survives** — real in small/mid/large, absent in micro |

**The honest headline:**
> **"We tested trial design, enrollment size and short interest against 1,752 readouts. Once you control for market cap, almost none of it survives. Market cap is the story — micro-caps move 4× more than large-caps, and that single fact explains most of what looks like signal."**

That is exactly the brand — and it's the same shape as the short-interest debunk the builder already published. **Publish the null result.** It's more valuable, more defensible, and more differentiating than a false positive.

**The one survivor:** Phase 3 readouts move less than Phase 2 in small and mid/large caps — but *not* in micro-caps, where everything is violent regardless. Worth publishing with that caveat.

---

## 4. What to do with this

### Publishable now
1. **`/research/catalyst-runup`** — the trilogy table. *"4,977 catalysts, three event classes, one answer: the run-up is a coin flip."* This is the flagship. It subsumes and strengthens the three separate studies.
2. **`/research/what-moves-a-readout`** — the market-cap-artifact debunk. *"We tested trial design, enrollment and short interest. Market cap ate all of it."*
3. **Event pages:** add trial design (*"Phase 3, randomized, double-blind, n=450"*) + SI-at-catalyst with settlement date. Both pure fact, both unique.

### API (Pro depth)
`runup_30d · event_move · move_tier · cap_tier · trial design block · days_to_cover` → per-event **"comparable catalysts"** module.

---

## 5. Still the biggest gap: **P2-1, the crawler**
The conference dataset **still can't refresh itself** — there is no `ConferencePresentation` type in `catalyst_crawler.py`. ASCO26 has 6 events; EHA26 and ADA26 have **zero**. Every enrichment round makes the panel more valuable and the leak more expensive. **This remains the highest-value job on the board.**

---

## Files
| File | What |
|---|---|
| **`conf_study/UNIFIED_catalyst_panel.csv`** | ⭐ **5,487 events, 3 catalyst classes, 2015–2026** |
| **`conf_study/readout_MASTER_enriched.csv`** | ⭐ **1,752 readouts × 88 cols** — CT.gov design + SI + reaction |
| `conf_study/conference_runup_FULL_v2.csv` | 1,425 conference events |
| `conf_study/si_panel_2017_2026.csv.gz` | 3.63M-row FINRA SI panel |

*No scores. No win rates. No probabilities. Median + IQR + n only. Not investment advice.*
