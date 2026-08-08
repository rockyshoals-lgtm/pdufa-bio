# ODIN Honing Engine — Performance Rating & Plateau Diagnosis

**Version:** 13.2.1723 (best) → 13.2.1725 (latest)
**Date:** February 24, 2026
**Dataset:** n = 2,202 PDUFA events (1,497 approved / 705 CRL)
**Parameters:** 53 trainable weights
**Runtime:** 34.5 hours, 1,724 iterations, GPU-forced (cuda:0)

---

## Rating: A-

Up from B+ (v2.1 GPU runner) and B- (original). The CPU honing engine has pushed the model from AUC 0.8847 → 0.9085 on the full training dataset, with Brier dropping from 0.1124 → 0.0968. This is an excellent logistic regression model for 53 parameters on 2,202 binary outcomes.

### Why A- and not A

The model is well-converged and the weights are clinically sensible, but three factors prevent a full A:

1. **No holdout validation** — AUC 0.9085 is on training data. The v2.1 walkforward test AUC was 0.8686, implying ~0.04 AUC overfitting gap. True out-of-sample performance is likely 0.86–0.88.
2. **Plateau reached** — Last 124 iterations changed 0 signals. The last meaningful improvement was at iteration ~1600. The engine is spinning.
3. **Base rate drift unresolved** — Every iteration fires BASE_RATE_SHIFT (recent 82% vs historical 67.7%), but the model can't fix this structurally because it's a dataset composition issue, not a weight issue.

---

## Run Summary

| Metric | Start (iter 0) | Current (iter 1724) | Delta |
|--------|---------------|---------------------|-------|
| AUC | 0.8847 | 0.9085 | +0.0238 |
| Brier | 0.1124 | 0.0968 | −0.0156 |
| Accuracy | — | 88.4% | — |
| Log Loss | — | 0.391 | — |
| Brier Skill Score | — | 0.555 | — |

### Progression Phases

| Phase | Iterations | AUC Gain | Rate |
|-------|-----------|----------|------|
| Rapid climb | 0–100 | +0.0146 | 14.6 bps/100 iter |
| Stall | 100–300 | +0.0001 | 0.1 bps/100 iter |
| Slow grind | 300–800 | +0.0057 | 11.4 bps/100 iter |
| Diminishing | 800–1500 | +0.0032 | 4.6 bps/100 iter |
| Terminal plateau | 1500–1724 | +0.0009 | 4.0 bps/100 iter |

### Convergence Evidence

- **Last 20 iterations AUC spread:** 0.000329 (essentially noise)
- **Last 124 iterations signals changed:** avg 0.9, only 5/124 iterations active
- **Recalibration improvements:** 170/1,724 iterations actually improved Brier (9.9% hit rate)
- **Last 50 iterations Brier change:** −0.000000 (zero)
- **Weight vector distance** (best vs 3rd-best run): 0.100 L2, max single Δ = 0.039

---

## Plateau Diagnosis

### Why 0.9085 Is the Ceiling

**Root cause: Irreducible error from missing features and inherent noise.**

#### 1. Dataset Constraint (Primary)

With n = 2,202 events and 53 parameters (params/sample = 0.024), the model has reasonable capacity. But the effective degrees of freedom are lower than 53 because many features are mutually exclusive categoricals:

- 19 TA offsets (one-hot, each applies to ~50–200 events)
- 4 FDA era buckets (one-hot)
- 3 resub levels (one-hot)
- 4 TA risk buckets (one-hot)

Effective free parameters ≈ 22 signals + 3 continuous + ~5 structural intercepts = **~30 independent parameters**. At AUC 0.9085, the model correctly orders ~91% of all approval/CRL pairs. The remaining ~9% are cases where the 30 features genuinely cannot distinguish approval from CRL.

#### 2. Missing Signal Categories

The model has no features for:

- **Clinical trial results quality** (effect size, p-values, number of endpoints met) — the single strongest predictor of FDA decisions, but requires manual extraction
- **Advisory committee vote count** (the model has binary `had_adcom` but not the actual vote percentage)
- **Competitor landscape** (is there already an approved drug in the same indication?)
- **Political/policy climate** (beyond the crude `fda_era` bucket)
- **Application quality signals** (REMS requirements, pediatric study adequacy beyond `ped_pk_missing`)
- **Patent cliff / commercial urgency** — not relevant to FDA but correlated with sponsor investment in approval

#### 3. Inherent Stochasticity

Some FDA decisions are genuinely unpredictable from pre-decision features:

- Late-breaking safety signals discovered during review
- Manufacturing inspections finding unexpected issues
- Policy shifts between filing and decision (especially during transitions)
- Advisory committee dynamics (personality of chair, public testimony impact)
- Congressional/media pressure on specific drugs

These represent the **Bayes error rate** — the minimum possible error for any model using only pre-decision information. We estimate this at AUC ≈ 0.92–0.94 for the current feature set.

#### 4. Logistic Model Limitations

The linear-in-log-odds assumption limits interaction modeling. The model has two explicit interactions (`btd_onco_interaction`, `btd_priority_interaction`), but other potentially valuable interactions are unmodeled:

- Prior CRL × resubmission class (partially captured but could be richer)
- TA × era interactions (e.g., oncology during COVID had different dynamics)
- Sponsor experience × drug complexity
- Surrogate endpoint × therapeutic area

A tree-based ensemble (XGBoost/LightGBM) would automatically discover these but at the cost of interpretability — a non-trivial tradeoff for a scoring engine that needs to explain its reasoning to traders.

---

## Weight Analysis — What the Model Learned

### Top 5 Strongest Signals (by absolute logistic weight)

| Signal | Weight | Direction | Interpretation |
|--------|--------|-----------|----------------|
| prior_crl | −4.201 | Strong negative | Prior CRL is the #1 predictor of another CRL |
| priority_review | +2.494 | Strong positive | Priority review = strong FDA engagement |
| form_483_issues | −2.294 | Strong negative | Manufacturing inspection flags kill approvals |
| ppm_flag | −1.800 | Strong negative | Post-marketing commitments flag correlates with trouble |
| had_adcom | +1.105 | Moderate positive | Having an AdCom (and surviving it) is net positive |

### Critical Disagreements with ODIN v10.1 Skill

| Signal | ODIN Skill | Honed Model | Resolution |
|--------|-----------|-------------|------------|
| BTD | +0.12 (pro) | −0.240 (anti) | BTD correlates with harder drugs. Positive effect captured by `btd_onco_interaction` (+0.851) instead |
| Orphan | +0.10 (pro) | −0.192 (anti) | Similar: orphan drugs are riskier. The positive effect is absorbed into `ta_offsets` for rare disease-heavy TAs |
| Manufacturing risk | −0.12 (anti) | +0.295 (pro) | Likely: "manufacturing_risk" flag is set for complex manufacturing, which correlates with novel/innovative drugs that tend to get approved. The *actual* manufacturing kill signal is `form_483_issues` (−2.294) |

**Recommendation:** Update the ODIN skill file to reflect honed weights. The additive probability model in the skill is a simplified approximation; the logistic weights are more accurate.

### Base Rate Issue

- **ODIN skill states:** 82.7% base approval rate
- **Actual data:** 68.0% (1,497/2,202)
- **Drift alert:** Recent rate 82%, historical 67.7%

The 82.7% figure appears to come from a recent subset. The full dataset spanning multiple FDA eras has a 68% rate. The `fda_era` weights handle this: `PRE_2020` gets +1.434 (higher approval era) while `COVID_ERA` gets −0.589 (lower approval era). The base_logit of 0.957 corresponds to a ~72% base probability, which makes sense as a blend.

---

## GPU Performance Profile

| Metric | Value |
|--------|-------|
| Device | cuda:0 |
| VRAM allocated | 17.6 MB (constant) |
| Epochs/sec | 552–1,412 (avg 906) |
| Time/iteration | 43–7,732s (avg 72s, median 64s) |
| Total runtime | 34.5 hours |
| GPU-forced iterations | 1,353/1,725 (78%) |

### GPU Utilization Problem

**VRAM allocated: 17.6 MB on a 12 GB GPU = 0.15% utilization.**

This is the single biggest optimization opportunity. The honing engine trains a single logistic model (53 params × 2,202 samples) per iteration. This is ~400KB of data. The GPU is being used as a slightly faster CPU.

---

## Recommendations

### Immediate (v2.3)

1. **Batch parallel honing** — Train 100–500 weight perturbations simultaneously on GPU instead of one at a time. At 17.6 MB per model, you can fit 500+ models in 12 GB VRAM.
2. **Population-based training** — Instead of sequential point mutations, maintain a population of 50–200 weight vectors and evolve them in parallel. Tournament selection + crossover + mutation. All vectorizable on GPU.
3. **Automatic plateau detection → halt** — When signals_changed = 0 for 50 consecutive iterations, stop wasting compute.

### Medium-term (Feature Engineering)

4. **Add AdCom vote percentage** as continuous feature (currently binary)
5. **Add trial endpoint met count** (primary endpoints met / total primary endpoints)
6. **Add sponsor recency** (years since last approval, not just count)
7. **Add era × TA interaction terms** (6–8 additional features)

### Long-term (Architecture)

8. **Ensemble with gradient-boosted trees** — Train both logistic + XGBoost, blend predictions. Trees capture interactions automatically.
9. **Temporal cross-validation** — Train on pre-2023, validate on 2023–2024, test on 2024–2025. More realistic than full-dataset AUC.
10. **Dynamic recalibration API** — When a new PDUFA resolves, retrain in <10 seconds and push updated weights to production.
