# ODIN Backtest Enrichment & Signal-Discovery Packet
**Prepared for cross-research + verification (Claude, Gemini, Perplexity).**  
**Date:** 2026-01-22  
**Owner:** ODIN / PDUFA backtest pipeline (GPU brute-force + MCP enrichment)

---

## 1) Objective

We have a large historical FDA catalyst dataset (PDUFA-style outcomes) and a GPU-accelerated configuration search engine (billions of configs). The **goal is to improve out-of-sample performance** (especially **false-positive reduction**: CRLs predicted as approvals) while preserving:

- **T−1 cutoff rule:** every feature must be computable using information available **no later than 1 day before the event** (no leakage).
- **Calibration-first:** improve **Brier / log loss** and avoid overconfident scores.
- **Speed:** enable extremely large-scale config search (billions of runs) on a single RTX 4070 (12 GB VRAM).

This packet summarizes current results, validated/partially validated enrichment signals, known dataset gaps, and proposes **new candidate data feeds + metrics** to research and verify.

---

## 2) Current GPU Brute-Force Run Snapshot (Train Split)

**Command (example):**  
`python ODIN_GOD_MODE_V5_GPU_ENGINE_CORRECTED.py --data ODIN_PDUFA_1349_GPU_READY.csv --split train --iters 1000000000`

**Hardware:** RTX 4070 (12.9 GB VRAM; ~11.6 GB free at run start)

**Train split size:** N = 843  
**Class balance:** 714 approvals, 129 CRLs (**84.7% approval rate**)

### Observed best train configuration (stable across repeated huge searches)
- **F1 ≈ 0.9427**
- **Precision ≈ 0.953**
- **Recall ≈ 0.933**
- **Specificity ≈ 0.744**
- **FP = 33**, **FN = 48**
- **Threshold (“thr”) ≈ 0.80–0.88** (top configs differ mostly by thr)
- **Brier ≈ 0.06495** (NOTE: verify how Brier is computed in this engine; confirm it uses probabilities and not discretized labels)

**Throughput:** ~50M iterations/sec; ~20 seconds for 1B iters; ~10 seconds for 0.5B refinement.

### Interpretation
- The search appears to hit a **performance plateau** where top configs are nearly identical.
- This strongly suggests that **new features / signals** (not more brute-force weight search) are needed to materially improve specificity / reduce FPs.

---

## 3) Dataset Feature Sanity Notes (From Run Output)

Feature validation snapshot (train split; % of rows with value 1):
- btd: 20.4%
- orphan: 25.0%
- priority: 45.8%
- fast: 37.8%
- accel: 14.2%
- exp: 54.0%
- inexp: 46.0%
- mfg: 20.0%
- pain: 2.3%
- cns: 7.1%
- onco: 28.4%
- inf: 12.1%
- stack: mean=1.43, max=5
- **class1_cmc: 0.0% (ALL ZERO)**
- **des_trap: 0.0% (ALL ZERO)**
- adcom_pct: 4.5% non-zero

### Actionable concern to verify
If `class1_cmc` and `des_trap` are intended to be meaningful, **they currently provide no learning signal** in the train split as printed.  
Research tasks:
1) Confirm whether the features are genuinely absent in history, or missing due to ingestion/ETL.
2) If missing: define extraction rules and backfill (T−1 safe).

---

## 4) “MCP” Pattern Findings (Backtested / Partially Validated)

These patterns were proposed to reduce ODIN false positives (CRLs predicted as approvals). Some were backtested with historical-queryable sources; others are **prospective-only** due to lack of historical data coverage.

### P1 — Insider Cluster Sell (FinBrain) *(prospective-only; no historical backtest yet)*
- Idea: clustered discretionary C-suite selling before catalyst can flag hidden risk.
- Requires: historical Form 4 / insider transaction availability with timestamps.

### P2 — Extreme Options Put/Call Ratio (FinBrain) *(prospective-only; no historical backtest yet)*
- Idea: very high P/C ratio can indicate strong bearish positioning and elevated CRL/delay risk.
- Requires: historical options data with timestamped P/C.

### P3 — Publication Volume (PubMed) **(backtestable historically)**
- Rule concept: very low PubMed article count for drug/target/indication may correlate with higher failure/CRL risk.
- This is imperfect (some high-publication programs still fail), but may catch a subset of FPs.

### P4 — Trial Velocity / Duration (ClinicalTrials.gov) **(backtestable historically)**
- Rule concept: extreme long time from trial start to PDUFA can indicate chronic execution issues / weak effect size / operational risks.

### P5 — Analyst–Insider Divergence (FinBrain + analyst ratings) *(prospective-only; no historical backtest yet)*
- Idea: analysts bullish while insiders sell and/or options skew bearish can be a strong “too optimistic” warning.

### P6 — EU ≠ US Approval (ChEMBL / EMA vs FDA status) **(backtestable historically)**
- Idea: EMA approval does not guarantee FDA approval; may create false confidence.

### P7 — Selling Timing (FinBrain) *(prospective-only; no historical backtest yet)*
- Idea: selling after approval can be “profit-taking” and not bearish; selling before catalyst can be bearish.

### “Designation Trap” (P003 extension)
- Definition: **designation_stack ≥ 4 + inexperienced sponsor** → higher CRL risk than expected.
- Goal: reduce the “too many designations = must be safe” false-confidence failure mode.

> **Important:** The above must be treated as hypotheses unless a strict historical backtest exists. Where a backtest exists, verify sample size, query method, and leakage controls.

---

## 5) “VOID Signal” (Indeed Hiring / Commercial Readiness)

A strong recent (small-sample) signal was reported:
- **If the catalyst is near (e.g., <6–9 months) and there is near-zero commercial hiring**, this can be a bearish signal (delay/CRL risk).
- Caveat: some companies intentionally delay commercial hiring until approval; needs an “intentional strategy” override and careful interpretation.

Research tasks:
- Determine if historical hiring/posting data is obtainable (Indeed does not guarantee deep history).
- If not, define prospective collection plan and how to store T−1 snapshots.

---

## 6) Candidate New Data / Metrics to Research (High Priority)

Below are candidate signals that may improve specificity and/or calibration. The research request is to identify:  
(1) strong evidence it correlates with regulatory outcomes,  
(2) whether it can be computed historically with timestamps, and  
(3) how to implement in a T−1 safe way.

### A) FDA / Regulatory-process signals (T−1 safe if sourced from press releases + FDA calendars)
1) **Deficiency letters / “FDA identified deficiencies” communications** (press releases)
2) **Major amendments** / PDUFA extensions / 3-month delays (press releases, FDA)
3) **AdCom scheduled vs waived vs cancelled** (FDA calendar / press releases)
4) **Prior CRL reason categories** (CMC vs clinical vs safety) and resubmission class signals (where available)

### B) Manufacturing / Quality / Inspection risk (may be very strong if reliably obtainable)
1) **Form 483 / Warning Letter linkage to sponsor or manufacturing sites** within a time window pre-catalyst
2) **Inspection classification (NAI/VAI/OAI)** for relevant sites (if public + linkable)
3) **CMC complexity proxies** (drug-device combo, sterile injectables, gene therapy, etc.)

### C) Trial design quality + execution flags (ClinicalTrials.gov + publications)
1) **Single pivotal trial** vs multiple trials
2) **Surrogate endpoints** vs clinical endpoints
3) **Geographic distribution** (US-heavy vs ex-US heavy)
4) **Enrollment delays**, amendments, late timeline slips
5) **Effect size / p-value margin** if public pre-catalyst (often not)

### D) Scientific validation signals (PubMed / genetics)
1) **Genetic / GWAS evidence** for target–indication link
2) **Recent publication velocity** (last 12–24 months) vs total volume
3) **Preprint activity** (bioRxiv/medRxiv) — potential early warning/interest signal

### E) Chemistry / Developability (ChEMBL, public ADMET resources)
1) **Toxicity risk proxies**: logP, MW, TPSA, rule-of-5 violations, toxicophores (where available)
2) **Modality-specific developability**: e.g., gene therapy manufacturing difficulty, CMC risk
3) **“Reference class anchor”**: compare to similar historical compounds/modalities and anchor base probability to that class

### F) Market microstructure (FinBrain or other)
1) **IV skew** (put IV vs call IV)
2) **Volatility regime changes** pre-event
3) **Insider buy magnitude** and clustering (strong bullish)
4) **Analyst rating dispersion** and revision rate

---

## 7) Metrics to Add (Beyond F1)

Because the dataset is imbalanced (≈85% approvals), relying on F1 alone can mislead. Research and recommend:

1) **Brier Score** (primary calibration metric)
2) **Log loss / cross-entropy**
3) **ECE (Expected Calibration Error)** and reliability diagrams
4) **Specificity at fixed precision** (e.g., maximize specificity subject to precision ≥ 0.95)
5) **Precision@K** (if the system is used to select top opportunities)
6) **Cost-sensitive objective** tuned to how much a FP costs vs FN

Also recommend evaluation regimes:
- **Time-split validation** (train on earlier years, test on later years) to prevent temporal leakage and to reflect real deployment.
- **Repeated CV** to estimate uncertainty.

---

## 8) Verification Tasks for Claude / Gemini / Perplexity

### Task 1 — Validate each claimed signal with sources
For each signal (VOID hiring, cluster sell, options P/C, publication volume, trial velocity, EU≠US, designation trap):
- Find at least **2–3 reputable sources** (papers, FDA guidance, reputable analytics or regulatory references).
- Confirm directionality and any known confounders.

### Task 2 — Determine historical data availability + best sources
For each candidate signal, answer:
- Is the data available historically back to at least 2010 (ideally earlier)?
- Can it be retrieved programmatically and timestamped (API or bulk dumps)?
- What are licensing/cost constraints?

### Task 3 — Identify leakage risks
For each feature, define:
- What timestamp is used?
- How to guarantee **T−1** availability?
- How to handle press releases posted after market close, or corrections?

### Task 4 — Suggest concrete implementation schema
Provide a proposed schema:
- Column names to add to ODIN_PDUFA dataset
- Data types, allowed missingness
- Example extraction rules

### Task 5 — Propose “best next 5 features” prioritization
Rank features by:
1) Expected FP reduction impact
2) Historical backtest feasibility
3) Implementation cost/complexity

---

## 9) Prompt to Use in Claude / Gemini / Perplexity

Copy/paste the prompt below into each system (and attach this packet + any referenced ODIN configs/logs).

---

### PROMPT START

You are a research and verification engine. Your job is to **verify** the claims in the attached ODIN packet and identify **new data sources, features, and evaluation metrics** that could improve out-of-sample prediction of FDA PDUFA outcomes (approval vs CRL/delay), under strict constraints.

**Hard constraints:**
- All features must be computable using data available **no later than T−1 day** before the event (no leakage).
- The goal is calibration-first: minimize **Brier / log loss** and reduce false positives (CRLs predicted approvals).
- Provide citations for any factual claims and prefer primary/authoritative sources (FDA, peer-reviewed papers, official APIs/docs).

**What to produce:**

1) **Claim verification table**
For each signal in the packet (VOID hiring, insider cluster sell, options P/C, publication volume, trial velocity, EU≠US, designation trap), provide:
- What the claim is
- Evidence quality (strong/moderate/weak)
- Supporting sources (citations)
- Known confounders / failure cases

2) **Historical data feasibility table**
For each candidate feature class (FDA communications, inspections/Form 483, AdCom calendar, ClinicalTrials design flags, PubMed genetic evidence, ChEMBL developability, hiring data, options/insider data):
- Is historical data realistically obtainable?
- Best sources/APIs
- Earliest reliable coverage date
- Licensing/cost notes
- How to enforce T−1 cutoff

3) **Top 10 new features (ranked)**
For each recommended feature:
- Exact definition and how to compute it
- Expected direction (approval ↑ / CRL ↑)
- Suggested thresholds or transforms
- Suggested initial weight range (if additive scoring) or model feature type (if ML)
- Expected benefit (qualitative; do NOT hallucinate exact Brier improvements)

4) **Evaluation metric recommendations**
- Which metrics to optimize and why (Brier, log loss, specificity@precision, ECE)
- Recommended validation scheme (time-split CV, holdout, bootstrapping)

5) **Implementation blueprint**
- A proposed dataset schema: columns to add, types, missingness handling
- A step-by-step ETL plan with checkpoints to avoid leakage
- Any open-source libraries or datasets to accelerate implementation

Be explicit about uncertainty. If you cannot find sources for a claim, say so.

### PROMPT END

---

## 10) Attachments & References (Recommended to include in uploads)

If possible, attach these ODIN artifacts along with this packet:
- ODIN MCP session handoff, MCP backtest report, MCP synthesis summary
- ODIN v8.8/v8.9/v8.10 configuration JSONs
- Any run logs (GPU engine output, REALOPT logs)

(If a model has upload limits, provide only the packet + the top 1–2 config JSONs + the MCP backtest report.)

---

## 11) Notes / Known Ambiguities to Resolve

- **Brier score mismatch risk:** the GPU engine reports very low Brier on train; ODIN MCP documents discuss higher Brier on broader evaluation sets. Confirm identical definition, dataset split, and probability computation.
- **Feature sparsity:** `class1_cmc` and `des_trap` showed 0 ones in the run output. Confirm whether these are truly absent or missing.
- **Prospective-only features:** FinBrain and Indeed-based signals may not backtest historically; define a prospective data collection protocol if needed.

---

**End of packet.**
