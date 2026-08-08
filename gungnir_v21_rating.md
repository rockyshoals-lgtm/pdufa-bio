# GUNGNIR Perpetual GPU v2.1 — Post-2862 Cycle Rating

## Run Summary (Updated)

| Metric | v2.0 (46 cycles) | v2.1 (2,862 cycles) | Delta |
|---|---|---|---|
| Total cycles | 46 | 2,862 | +62× |
| Total configs trained | 147,459 | 9,186,749 | +62× |
| Runtime | 5.5 hours | 26.5 hours | — |
| Cycle time | ~480s | ~26s | **18× faster** |
| Best walk-forward test AUC | 0.8504 | **0.8686** | +0.0182 |
| Best walk-forward test Brier | 0.1411 | **0.1347** | -0.0064 |
| Best overfit delta | 0.0473 | **0.0310** | -0.0163 |
| New bests found | 0/46 | 18/2,862 | Fixed (partially) |
| Versions logged (CPU honing) | — | 316 | — |

---

## Rating: **B+ (Strong engine, diminishing returns, untapped speed)**

v2.1 fixed the critical comparison bug (18 new bests now register) and dramatically reduced cycle time from ~480s to ~26s. The engine found legitimate improvement: +0.018 AUC, -0.016 overfit delta. But it's now firmly in the plateau zone — the last 2,000 cycles gained essentially nothing. The engine is spending 95% of its compute on cycles that produce no improvement.

---

## What v2.1 Fixed (vs v2.0 analysis)

### ✅ Bug #1: Apples-to-Oranges Comparison — PARTIALLY FIXED
18 new bests were found (vs 0 in v2.0), confirming the fix works. However, `is_new_best: false` still appears on 2,844/2,862 cycles. The 0.0005 AUC threshold for "new best" is appropriate given the noise level.

### ✅ Speed: 18× Faster Cycles
Cycle time dropped from ~480s to ~26s around cycle 51. This is the single biggest win — it allowed 62× more configs to be explored in only 5× more wall-clock time.

### ⚠️ Bug #2: Negative L2 — STILL PRESENT BUT CONTAINED
Top 10 configs still show L2 from -0.006 to +0.011. The model has learned to use anti-regularization effectively (overfit delta dropped from 0.047 to 0.031), but this remains a calibration risk in production. The v2.1 tail calibration penalty (10% fitness weight) is helping.

### ⚠️ Bug #3: Tier Sweep Bias — PARTIALLY FIXED
T1=0.85 still dominates (9/10 top configs), but T1=0.90 and T1=0.70 now appear. The coverage bonus and forced diversity are working, just not enough to overcome T1=0.85's natural advantage at this dataset size.

---

## Performance Analysis

### The Plateau Problem
```
Cycle     1 → AUC 0.8440  (cold start)
Cycle    51 → AUC 0.8640  (rapid improvement phase, +0.020 in 50 cycles)
Cycle   287 → AUC 0.8637  (plateau begins)
Cycle  2862 → AUC 0.8665  (2,575 cycles gained +0.003)
```

The engine hit its ceiling at cycle ~50-100 and has been making negligible progress since. From cycle 287 onwards, 2,575 cycles × 3,211 configs = **8.3 million configs were trained for +0.003 AUC gain**. This is a textbook case of hyperparameter search exhaustion.

### CPU Honing vs GPU Honing
The versions.json shows 316 CPU honing iterations converging to AUC=0.8809 on full data. Meanwhile GPU walk-forward peaks at 0.8686 on 30% holdout. The ~0.012 gap (0.881 - 0.869) is the expected generalization gap for this dataset size, confirming both engines are finding the same optimum from different directions.

### Converged Hyperparameters (2,862 cycles)
| Parameter | Top-10 Range | Interpretation |
|---|---|---|
| Learning rate | 0.005–0.031 | Wide — LR doesn't matter much at convergence |
| L2 | -0.006 to +0.011 | Both directions work — model is over-parameterized |
| Init strategy | noisy_small, noisy_medium | Small perturbations from platform dominate |
| T1 boundary | 0.85 (9/10), 0.90, 0.70 | High-confidence tier confirmed |
| T4 boundary | 0.05 (10/10) | Strict no-trade gate locked in |

---

## Key Bottlenecks Identified

### 1. Wasted Cycles (95%+ of compute is unproductive)
The engine doesn't detect plateaus. It runs the same expensive 4-step pipeline (generate → train → tier sweep → walkforward) whether it's cycle 5 or cycle 2,500. After the plateau, the walkforward step (which re-trains 20 models) is pure waste on most cycles.

### 2. Fixed Batch Size (3,211 configs)
The engine always trains exactly 3,211 configs regardless of available VRAM. On an RTX 4070 (12GB), with this small model (4,596 events × ~40 features), the GPU is barely utilized. The data tensors are ~1.4MB total. You could train 50,000+ configs per batch.

### 3. Serial Tier Sweep (Python loops)
The tier sweep iterates 50 models × 25 tier combos = 1,250 configs in a Python for-loop with per-element comparisons. This could be fully vectorized in numpy/torch.

### 4. Redundant Walk-Forward
20 nearly-identical models are retrained from scratch on 70% data every cycle. Given the top-10 AUC spread is only 0.0007 (0.8680–0.8686), most of these are testing the same model with noise.

### 5. No Adaptive Exploration
The strategy distribution is fixed at 88% exploitation / 12% exploration regardless of plateau depth. After 2,500 stale cycles, exploration should dominate.

---

## Remaining Improvement Vectors

The engine has exhausted hyperparameter search. Further gains require:

1. **Feature engineering** — new signals, interaction terms, temporal features
2. **Ensemble methods** — blend top 5 models (expected +0.005-0.010 AUC)
3. **Data expansion** — more events, better outcome labeling
4. **Calibration optimization** — Platt scaling, isotonic regression post-training
5. **Temporal cross-validation** — expanding window instead of fixed 70/30 split
