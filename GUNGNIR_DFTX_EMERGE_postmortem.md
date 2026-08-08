# GUNGNIR Post-Mortem — DFTX / DT120 (MM120, LSD) EMERGE Phase 3 MDD

**Event:** June 22, 2026 — Definium Therapeutics (DFTX, formerly MindMed/MNMD) EMERGE Phase 3 of
DT120 ODT (lysergide D-tartrate / LSD, formerly MM120) in Major Depressive Disorder **hit its
primary + all key secondary endpoints** (p<0.0001, +8.1-pt placebo-adjusted MADRS, ~35% vs 7%
response, clean safety). Stock **+~50–55%** on ~6× volume.

---

## 1. What we had on record: nothing — and that's the real finding

DFTX appears in **zero** of our scored catalyst files (`catalyst_scores_v31…v44.json`). We never
produced a GUNGNIR prediction for this readout. Not because the model would have missed it — because
of **data-plumbing failures upstream of the model**:

1. **Pipeline lag.** Our last scoring run was **v44 (April 2026)**. DFTX first entered our crawl on
   **June 21, 2026**. Catalysts get crawled but the scorer was never re-run on the fresh set → no score.
2. **Rebrand / alias fracture.** MindMed→Definium (**MNMD→DFTX**, Jan 15 2026) and **MM120→DT120**
   split the entity. Our crawler created **duplicate, conflicting rows** under the same SEC CIK
   (0001813814): some correct (DT120, MDD, CT.gov), some with the **old name and garbled metadata**
   — e.g. indication tagged *"Psilocybin assisted therapy / Suicidal Ideation"* (wrong drug, wrong
   indication). A scorer ingesting those rows would have mis-featured the event.
3. **Date smear.** The actual EMERGE MDD readout was represented as a vague "2H 2026" window, while
   the explicit dated DT120 rows pointed at **GAD (Nov 2026)** and a *different* MDD Phase 3
   ("Ascend," 2027). The catalyst that popped was scattered across mislabeled rows.

## 2. What we'd have gotten RIGHT (reconstruction)

Re-running the **v46 champion's Ridge backbone** (M1 = 90% of the binary ensemble) on the documented
pre-readout state (`gungnir_dftx_postmortem.py`):

| Output | Reconstruction | Actual |
|---|---|---|
| **P(positive)** | **93.6%** | Hit (p<0.0001) ✅ |
| **P(GOOD+ ≥15% move)** | **90.4%** | +~55% ✅ |
| **P(CRASH ≤ −30%)** | **14.8%** | No crash ✅ |

The model's logic lines up with the outcome. Dominant drivers (binary head):

- **`v46_p1_ch2_moa_agonist` (+1.07)** + **`ch_is_agonist` (+0.55)** — LSD is a well-characterized
  5-HT2A **agonist**; the model rewards defined, validated mechanisms. *(Biggest positive.)*
- **Journey block (+0.69 combined)** — prior **positive Phase 2b GAD** (JAMA-published) + BTD →
  `journey_last_positive`, `journey_success_rate`, `journey_had_positive` all fire.
- **`nlp_topline` (+0.40)** — full topline data, **not interim** (the model penalizes interim).
- It **correctly applied the depression headwind** — **`v41_placebo_x_cns` (−0.67)** + **`ta_cns`
  (−0.21)** (high placebo response in MDD) — and *still* landed ~94%.
- **Designations actually dragged the binary head DOWN** (`designation_count` −1.0), so the positive
  call is **robust** — it is **not** propped up by BTD.

The crawler, despite the metadata mess, **did surface the company and the DT120 MDD program from
primary sources** (CT.gov + SEC) — the catalyst was within reach.

## 3. What we'd have gotten WRONG / blind spots

- **Magnitude was a short squeeze, not just "positive."** The +55% was amplified by **~31% short
  interest + a 52-week-high breakout**. GUNGNIR predicts *direction* and P(GOOD+), but has **no
  readout-specific squeeze/magnitude model** (the PDUFA stack's BIFROST explosion detector uses short
  interest; the readout stack does not). We'd have said "big positive likely," under-sizing *how* big.
- **`designation_count` is fragile.** It swings from **−1.0** (binary head) to **+4.0** (GOOD+ head)
  — one sparse feature moving GOOD+ by ~4 logits. P(GOOD+) is the soft number here.
- **Agonist is a thin-data extrapolation.** Agonist MOA is only **1.8%** of training events; the
  +1.07 driver is a confident bet on sparse support. Right this time, fragile in general.

## 4. How to improve readout predictions (ranked, actionable)

1. **Auto-re-score the fresh crawl.** Run the GUNGNIR scorer nightly over `catalysts_public.csv` so
   every crawled readout carries a live score. *This single fix would have produced a ~94% call.*
2. **Entity/alias resolution by CIK.** Map ticker/name/drug aliases (MNMD↔DFTX, MM120↔DT120) on SEC
   CIK; dedup rows by CIK + drug so rebrands don't fracture or dirty the calendar.
3. **Metadata QA gate before scoring.** Reject/flag rows where drug→modality→indication are
   inconsistent (an LSD/MDD asset tagged "psilocybin/suicidal ideation" should never reach the model).
   Validate modality via ChEMBL/INN stem.
4. **Add a readout short-squeeze magnitude overlay.** Port the explosion-detector short-interest +
   52w-high features to readouts. DFTX (~31% SI, at highs) would have flagged as an outsized-move setup.
5. **De-fragilize `designation_count`** in the GOOD+ head — winsorize, or split into BTD / fast-track
   / orphan binaries so no single sparse feature dominates.
6. **Grow the psychedelic/agonist cohort.** LSD/psilocybin/MDMA readouts are now a recurring cluster;
   add a `psychedelic_class` feature and backfill so the model isn't extrapolating from 1.8% support.

---

*Reconstruction = v46 Ridge backbone (90% of the binary ensemble) on documented T-1 inputs; XGBoost
(10%) omitted; unknown trial-design features held at training mean. Not a logged historical
prediction. Informational/educational only — not investment advice.*
