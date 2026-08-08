# ODIN Gungnir Phase 2→3 Patch — Engineering Audit

## Verdict: Solid Framework, 7 Critical Upgrades Required

The Perplexity/Claude JSON spec (`ODIN_Gungnir_Phase23_Patch_v1.0`) is architecturally sound — frozen base weights, monotonic p-value constraints, calibration anchoring are all correct patterns. But the implementation will **waste your 4070 GPU** and produce **unreliable weights** due to sample size issues and missing signals.

---

## CRITICAL ISSUE 1: P-Value Buckets Have N=1-2 Samples

The spec's core features are 3 p-value buckets (`<0.001`, `0.001-0.01`, `0.01-0.05`). Our text-extracted data from 357 labeled pairs shows:

| Bucket | N | P3 Hit Rate |
|--------|:-:|:-:|
| p < 0.001 | **1** | 100% |
| 0.001–0.01 | **1** | 100% |
| 0.01–0.05 | **2** | 100% |
| ≥ 0.05 | **1** | 0% |

Even with the manually audited 72 pairs (Perplexity's dataset), you'd get maybe 8–15 per bucket. Fitting 3 weight parameters on 8–15 samples **will overfit**. The monotonic constraint helps but can't fix a fundamental sample size problem.

**Fix:** Collapse to a single binary feature `has_significant_p2` (p < 0.05 vs not) until the audited dataset reaches 200+ pairs per bucket.

---

## CRITICAL ISSUE 2: Coordinate Descent Doesn't Use the GPU

The spec proposes `coordinate_descent_with_random_restarts` (200 iterations × 10 restarts × 7 parameters). This is ~14,000 forward passes through a logistic function — takes <1 second on CPU. Your 4070 with 12GB VRAM and 5,888 CUDA cores sits completely idle.

**Fix:** Replace with PyTorch neural net ensemble + Optuna TPE hyperparameter search. A single overnight run on the 4070 can evaluate 2,000+ neural architectures across 5-fold CV.

---

## CRITICAL ISSUE 3: Missing the Top 4 Proven Signals

Our V3 SHAP analysis (validated on real 2025 outcomes: TIER_1 = 87% hit, TIER_3 = 23%) showed these top signals:

| Rank | Feature | SHAP | In Spec? |
|:-:|---|:-:|:-:|
| 1 | `odin_sponsor_prior_approvals` | 0.529 | **NO** |
| 2 | `f_gap_months` (P2→P3 time gap) | 0.399 | **NO** |
| 3 | `odin_ta_base_score` | 0.306 | **NO** |
| 4 | `odin_historical_crl_rate` | 0.281 | **NO** |
| 5 | `f_sponsor_pdufa_count` | 0.156 | **NO** |
| 6 | `f_sponsor_approval_rate` | 0.133 | **NO** |
| 7 | `f_p2_durability` | 0.074 | **NO** |

The spec's 7 features (3 p-value buckets + 4 TA adjustments) rank **below** all of these. Adding the spec's features while ignoring the top 7 is like tuning the radio while the engine is missing.

**Fix:** Include all 30 V3 features as candidates. Let the neural net learn which matter.

---

## CRITICAL ISSUE 4: No Cross-Validation in the Optimizer

The spec optimizes on the full Phase 3 backtest, then "calibrates" against the 72-pair audit. There's no train/test split. With 7 parameters and 72 samples, you will overfit.

**Fix:** 5-fold stratified CV within every optimization step. Optuna handles this natively.

---

## CRITICAL ISSUE 5: Frozen Weights Assumption Is Wrong

The spec freezes ALL existing Gungnir weights and only optimizes 7 new ones. But adding features changes the optimal values of existing ones due to multicollinearity. For example, if `ta_ONCOLOGY` already has weight -0.25, adding `ta_oncology_phase3` creates collinearity that biases both estimates.

**Fix:** Fine-tune the full weight vector with a stronger L2 penalty that anchors to Gungnir V1071 values. This lets weights shift slightly while preventing catastrophic forgetting. The frozen weights the spec lists should have a 10x higher L2 penalty than new features, not be literally frozen.

---

## CRITICAL ISSUE 6: Calibration Constraints Are Statistically Meaningless

The spec requires `|model P3 success(<0.001) − empirical| ≤ 0.05`. With N=8-15 per bucket, a 95% CI for the empirical rate spans ±20-30%. Constraining to ±5% is fitting to noise.

**Fix:** Use Bayesian calibration with Beta priors informed by the full 357-pair dataset. Apply calibration post-hoc via Platt scaling or isotonic regression, not as hard constraints during optimization.

---

## CRITICAL ISSUE 7: No Uncertainty Quantification

The spec outputs point estimates. For trading P3 readouts, you need prediction intervals. A point estimate of 72% means nothing without knowing if the 95% CI is [65%, 79%] or [40%, 95%].

**Fix:** Monte Carlo dropout in the neural net ensemble + conformal prediction intervals.

---

## Upgraded Architecture for 4070 GPU

```
┌─────────────────────────────────────────────────────────┐
│  ODIN Gungnir Phase 2→3 Patch v2.0 — GPU Architecture   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  DATA: 357 labeled pairs, 30 features (V3 proven set)   │
│  + 72 audited p-values merged as enrichment             │
│                                                         │
│  MODELS (PyTorch GPU):                                  │
│    1. MLP Ensemble (5 architectures × 5 seeds)          │
│    2. TabNet (attention-based, GPU native)               │
│    3. GBM (LightGBM GPU mode)                           │
│                                                         │
│  OPTIMIZER: Optuna TPE (2000 trials overnight)          │
│    - 5-fold stratified CV                               │
│    - Time-split holdout validation                      │
│    - Bayesian calibration post-hoc                      │
│                                                         │
│  OUTPUTS:                                               │
│    - Ensemble prediction ± conformal interval           │
│    - SHAP feature importance (GPU accelerated)          │
│    - JSON patch for Gungnir production config           │
│    - Calibration curves + reliability diagrams          │
└─────────────────────────────────────────────────────────┘
```

---

## What to Keep From the Original Spec

1. **Monotonic p-value constraint** — correct (when sample size permits)
2. **Phase-3-only scope** — correct, prevents contaminating non-P3 predictions
3. **L2 regularization toward initial weights** — correct pattern
4. **Calibration against audited dataset** — correct, but use Bayesian not hard constraints
5. **TA adjustment features** — useful, but supplement with `ta_base_score` (continuous) rather than relying solely on binary flags
