# Stress Test — Everything
**2026-07-12** · Recall measured · Panels stress-tested · *Not investment advice.*

---

# 🔴 STOP: do not rebuild `/research/conference-runup` from the EDGAR crawler

The builder's stated next step is *"rebuild `/research/conference-runup` from the deepened set."*
**That would silently break the study.** Here is the proof.

## 1. Measured presenter recall — the number we never had

I used your **AACR 2026 presenter list from the scored-catalyst pipeline** (an independent source — *not* EDGAR-derived) as ground truth, and intersected it with what the EDGAR crawler found.

| | AACR 2026 | AAN 2026 |
|---|---|---|
| Ground-truth presenters | 43 | 7 |
| Crawler found | 41 | 12 |
| **Overlap (true positives)** | **23** | **5** |
| **RECALL** | **53.5%** | **71.4%** |

**The EDGAR crawler catches barely half of known AACR presenters.**

And note the crawler *also* found **18 tickers the ground truth lacks** (ARVN, BNTX, FATE, GH, GLUE, GSK, MRNA…). **Neither source is complete.** Two independent pipelines agree on 23 names while each holds ~20 the other misses. The true presenter count is likely **60+**, and each source sees ~55–70% of it.

> **"98.5% coverage" means 98.5% of the conferences in our registry. Actual presenter recall is ~54%.** The builder called this exactly right. Now it's quantified.

## 2. The mechanism — and it's directional, not random

| Cap tier | recall |
|---|---|
| nano | 50% |
| micro | 62% |
| small | 56% |
| **mid** | **33%** |
| **large** | **40%** |

| | recall |
|---|---|
| **under $2B** | **57%** |
| **over $2B** | **38%** |

**Missed, by size:** RHHBY ($319B) · MRK ($304B) · JAZZ ($12B) · IDYA ($2.7B) · ZLAB ($2.4B)

**The cause is structural, not a bug:**
> A poster at AACR is **material** to a $200M biotech — it files an 8-K.
> It is **immaterial** to Merck or Roche — no 8-K, no filing.
> **SEC EDGAR full-text search cannot see a presentation that was never filed.**

No number of search phrases fixes this. It is a property of the source.

## 3. Why rebuilding from the crawler would move the headline

**The published study is 49.2% large-cap:**

| cap tier | share of published study |
|---|---|
| **large** | **49.2%** |
| micro | 16.1% |
| small | 15.3% |
| mid | 14.4% |
| nano | 5.0% |

The crawler recovers only **38%** of >$2B names. So a rebuild would **strip out roughly half the large-caps** and re-weight the sample toward micro/small — **the cohort with the widest dispersion and the most positive medians.**

**The headline numbers would shift — and it would look like a finding, when it is purely a sampling artifact.** A run-up "appearing" because you dropped the large-caps is exactly the error this whole research programme exists to debunk.

### The rule
> **Never change the sampling frame and the published number in the same step.**
> If the universe changes, publish the *old* and *new* numbers side by side, with the recall figure, and say why they differ.

## 4. The fix: multi-source, then measure
1. **EDGAR alone is not enough** (~54% recall, biased against large-cap).
2. **Add press releases** — `fmp_press` is *already a source in your own `catalysts_public.csv` pipeline*. Companies that don't file an 8-K still issue a PR.
3. **Add conference abstract databases** (ASCO and AACR both publish searchable abstract lists) — that's the only true ground truth.
4. **Publish the recall number per conference and per cap tier on the page.** *"We catch ~54% of AACR presenters via SEC filings, and only 38% of companies over $2B, because a poster isn't material to Merck."* That's another corrections-grade honesty move no competitor would make.

---

# ✅ Stress tests that PASSED

| Test | Result |
|---|---|
| **ANE removal impact on headline** | median **−0.03% → −0.01%** — a **0.01pp** shift. **My ANE bug corrupted the by-conference *table*, not the headline.** Reassuring. |
| Unified panel — nulls / future dates | 0 null tickers, 0 null dates, **0 future-dated events** ✅ |
| Unified panel — run-up bounds | all within [−94.4%, +395.4%] — no impossible values ✅ |
| Readout master — move bounds | p1 −80.8% / p99 +159.5% — sane ✅ |
| **Readout master — SI lookahead** | **min lag = 1 day** ✅ zero lookahead confirmed |
| SI panel — negatives | 0 negative short quantities, 0 negative DTC ✅ |
| Stale SI | 0 rows with lag > 60d ✅ |

---

# 🟠 New issues found

### 1. Unified panel: **202 duplicate rows** on `(ticker, date, catalyst_type)`
Dedupe before it feeds anything published.

### 2. SI panel: **73,050 rows with days-to-cover > 100** (~18% of sample)
Legitimate for very illiquid nano-caps, but **absurd on a page**: *"Short interest: 4,200 days to cover"* destroys credibility instantly.
**Fix:** cap the *display* at e.g. `>60d` → *"very illiquid"*, and never render a raw DTC above ~30 without context.

### 3. Crawler output still unfixed (unchanged from last pass)
**5 fabricated events** (AUTL/COGT→ASH, CRBP→ESMO, CTMX→SITC, CELC→SABCS — all from 2025 source text) · **32 duplicates** · **3 residual ANE rows**. Crawler not yet re-run.

---

# The order (revised)

1. 🔴 **Fabrication guard** — must land before any conference publish (`llms.txt` is live).
2. 🔴 **Do NOT rebuild the study from EDGAR alone.** Multi-source first, or publish old + new side by side with the recall number.
3. 🔴 **Update CLAUDE.md** — ODIN v14 → v19-PRUNE. The memory file still mandates a leaked model.
4. 🟠 Dedupe the unified panel (202) and the crawler output (32).
5. 🟠 Cap the DTC display.
6. 🟠 Measure recall against the real ASCO/AACR abstract lists — the only true ground truth.
7. 🟠 `/ticker/{TICKER}` hubs — still 404, still the biggest SEO left.

---

## The one-line summary
**The dataset is sound; the *sampling frame* is the risk.** Every integrity test on the panels passed — no lookahead, no impossible values, no nulls, and my ANE bug turned out to be cosmetic. But the EDGAR crawler sees **54% of presenters and only 38% of large-caps**, and rebuilding a 49%-large-cap study on top of it would move the headline for reasons that have nothing to do with the market.

*Facts and historical statistics only. Not investment advice.*
