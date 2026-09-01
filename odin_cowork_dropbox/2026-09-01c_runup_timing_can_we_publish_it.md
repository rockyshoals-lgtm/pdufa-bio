# Can we publish *when* the run-up happened, and stay fact-based?
**2026-09-01 · computed from `runup_t120_cache.json`, 1,738 events**
*Facts and historical statistics only — not investment advice.*

---

# THE SHORT ANSWER

**Yes — but not as a "peak," because the data does not support one.**

I computed the curve before answering. The result argues against the framing more strongly than any compliance concern would.

---

# WHAT THE DATA ACTUALLY SHOWS

Cumulative median return vs a T-120 baseline, **n = 1,738 events**:

| Offset | n | **median** | p25 | p75 | spread |
|---|---:|---:|---:|---:|---:|
| T-120 | 1,723 | 0.00% | 0.00% | 0.00% | 0 |
| T-60 | 1,735 | 0.81% | −10.30% | +13.02% | 23 pts |
| T-30 | 1,738 | 1.20% | −13.29% | +16.18% | 29 pts |
| T-25 | 1,738 | 1.34% | −13.82% | +17.09% | 31 pts |
| T-10 | 1,738 | 1.76% | −14.49% | +19.16% | 34 pts |
| **T-5** | 1,738 | **2.56%** | **−14.07%** | **+19.90%** | **34 pts** |
| T-0 | 1,738 | 1.38% | −16.06% | +19.43% | 35 pts |

## Three things follow, and they kill the "peak" framing

**1. The median "peak" is 2.56%.** That is the highest point on a curve that wanders between 0.26% and 2.56% across the entire T-60 → T-0 stretch. **It is a peak the way the tallest ripple on a flat pond is a peak.**

**2. The dispersion at that point is 34 points wide** — p25 −14.07%, p75 +19.90%. **The spread is thirteen times the median.** Half of all events land outside a range that wide. A reader told "the run-up peaks at T-5, +2.6%" would have no idea that a quarter of events were down 14% or more at that same moment.

**3. The only monotonic thing in the table is the dispersion.** p25 falls 0 → −16%, p75 rises 0 → +19%, while the median barely moves. **The real finding is that uncertainty widens as the decision approaches, not that price drifts up.**

---

# SO WHAT *CAN* WE PUBLISH?

The honest, useful, and genuinely differentiated version is the dispersion — not the drift.

> **What happened to these stocks before the decision**
> Across **1,738 FDA decisions**, the typical stock was **up about 1–3%** in the four months before its decision date — but the range widened steadily as the date approached. At five trading days out, the middle half of events sat between **−14.1%** and **+19.9%**.
>
> The typical move stays small. **What grows is the spread.**
>
> This is what happened historically. It is not a prediction for any individual event.

That is fact-based, it carries its n, it shows the quartiles rather than hiding them, and it tells a reader the thing that is actually true — which a peak would not.

---

# THE LINE, STATED PLAINLY

The question isn't whether the number is true. It's whether the *shape* of the statement contains an instruction.

| Framing | Verdict |
|---|---|
| "Median cumulative return by day, with quartiles, n=1,738" | ✅ **descriptive** — a measurement |
| "The run-up peaks at T-5" | ⚠️ **implies precision the data lacks** — six other days are within noise |
| "Enter T-14, exit T-1" | ❌ **instruction** — this is BIFROST's internal vocabulary and must not appear publicly |

**A distribution describes. A timing recommendation instructs.** The difference is not the underlying data — it is that a peak-timing claim answers *"when should I have exited?"*, which is one word away from *"when should I exit?"*

**Rules if this ships:**
1. **Publish the whole curve**, never a single "best" day.
2. **Quartiles at every point.** A median-only chart on this data would be actively misleading.
3. **n at every point** — and note it varies (1,723 at T-120 vs 1,738 at T-0).
4. **No action vocabulary**: no *entry*, *exit*, *window*, *optimal*, *best day*.
5. **State the composition** — this pools approvals and CRLs, all cap tiers. Splitting by outcome would measure something different and is worth doing separately.

---

# ⚠️ TWO CAVEATS ON MY OWN NUMBERS

**1. This is my indicative computation, not the site's validated study.** It should be recomputed through the production pipeline before anything publishes. The published Conference Overlay figure (nano/micro D-30→D-1, 4.88% median, 58.5% win) uses a different cohort and method and is not directly comparable.

**2. My baseline is T-120 = 0 by construction, which mechanically guarantees the spread widens.** Any cumulative-return-from-a-fixed-baseline chart does this. That does not make the widening false — but it means the widening is partly an artefact of the framing, and a rolling N-day return would not show it the same way. **The builder should test both framings and publish whichever is honest about that property**, with the convention stated on the chart.

---

# BOTTOM LINE

**Showing when the run-up happened stays fact-based — but the honest version of that chart says there is no meaningful peak.**

The median tops out at **2.56% at T-5**, on a curve that is flat from T-60, with an interquartile range at that point of **−14.1% to +19.9%**. Publishing "the run-up peaks at T-5" would be true in the narrow sense and misleading in every sense that matters — the same failure as collapsing CAPR's asymmetric cohort into "±1%."

**Publish the dispersion instead.** *"The typical move stays small; what grows is the spread"* is a real finding, it's more useful to a retail reader than a peak would be, and no competitor has the 1,738-event series to say it.

---
*Computed 2026-09-01 from the local run-up cache; recompute through the production pipeline before publishing. Not investment advice.*
