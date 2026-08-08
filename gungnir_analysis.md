# GUNGNIR Perpetual GPU Honing — Analysis & Rating

## Run Summary
| Metric | Value |
|---|---|
| Total cycles | 46 |
| Total configs trained | 147,459 |
| Runtime | ~5.5 hours (07:57 → 13:36 UTC) |
| Best walk-forward test AUC | **0.8504** (cycle 30) |
| Best walk-forward test Brier | **0.1411** (cycle 30) |
| Best overfit delta | 0.0473 |
| New best ever found? | **NO — 0/46 cycles** |

---

## Rating: **B- (Good engine, critical bugs preventing progress)**

The optimizer is fundamentally well-engineered. GPU batch training, walk-forward validation, tier sweeping, leaderboard tracking — all solid. But it has three bugs that wasted most of those 147K configs.

---

## Bug #1: CRITICAL — Apples-to-Oranges `is_new_best` Comparison 🔴

**The platform `best_config.json` was never beaten because it CAN'T be beaten.**

```
best_config.json:  auc = 0.880932  (scored on FULL dataset, n=4596)
Walk-forward top:  test_auc = 0.8504  (scored on 30% held-out, n=1379)
```

The comparator `check_and_update()` falls back to `self.best.get("test_auc", self.best.get("auc", 0))`. Since `best_config.json` has no `test_auc` field, it uses the full-dataset `auc = 0.881`. Walk-forward candidates can never hit 0.881 on 30% of the data — that's like comparing a student's exam score to their homework score where they had the answer key.

**Impact:** The engine thought it was failing when it was actually working fine. 0.8504 test AUC on a 70/30 time split with 4% overfit is **excellent**.

**Fix:** Inject `test_auc` into `best_config.json` OR create a separate walk-forward benchmark.

---

## Bug #2: HIGH — Negative L2 Anti-Regularization 🟠

**All 10 top configs have negative L2 (range: -0.002 to -0.005).**

The L2 grid starts at `[0.0, 0.0005, ...]` but jitter on `v=0` generates `uniform(-0.005, 0.005)`, creating accidental negative L2 values. Negative L2 = anti-regularization = weights GROW each epoch instead of shrinking.

The weights confirm this: walk-forward top weights are **2-3x larger** than platform weights across the board. `failure_signal` hit the -4.0 bound. `primary_endpoint_met` hit the +2.5 bound. `sentiment_score` grew from 0.57 to 1.45.

**Why it "works":** With a strong prior signal (platform weights are good), weight inflation amplifies correct patterns. Overfit delta is only 0.047-0.049 because the signal is real. But this is fragile — on new data, inflated weights will overshoot predictions into extreme probability tails.

**Impact:** Models look good in walk-forward but will be poorly calibrated in production (probabilities bunched at 0 and 1 instead of distributed).

**Fix:** Explicitly add controlled negative L2 values to the grid, but cap at -0.003 and add calibration metrics to the fitness function.

---

## Bug #3: MEDIUM — Tier Sweep Bias Toward Extreme Boundaries 🟡

**Walk-forward only ever saw tier_1_boundary=0.85.** Out of 7 options (0.55→0.85), the tier sweep's composite score formula heavily rewards high T1 positive rates, which are trivially maximized by setting T1=0.85 (only ultra-confident predictions qualify). This means we never validated whether T1=0.75 or 0.70 might capture more tradeable events at still-high confidence.

**Tier 4** converged to 0.10 (most restrictive), which is good — it means the model is comfortable calling more things "no trade."

**Fix:** Either force diversity in tier boundary selection for walkforward, or restructure the tier_score formula to penalize excessively small T1 buckets.

---

## What the Optimizer DID Find (The Good News)

Despite the bugs, 46 cycles of 3,200 configs each produced consistent signal:

### Converged Hyperparameters
| Parameter | Converged Range | Interpretation |
|---|---|---|
| Learning rate | 0.014–0.020 | Moderate — not too aggressive |
| L2 | -0.002 to -0.005 | Anti-regularization helps (but needs validation) |
| Init strategy | platform + noisy_small | Exploiting current best works |
| T1 boundary | 0.85 | High confidence tier |
| T4 boundary | 0.10 | Strict no-trade gate |

### Key Feature Discoveries
- **p23_p2_bucket_lt_0001** (P2 p<0.001): Weight ~1.0 — strongest new feature
- **p23_p2_bucket_0001_001** (P2 p<0.01): Weight ~0.6 — strong
- **ta_rare_phase3**: Weight ~0.4 — rare disease Phase 3 boost confirmed
- **ta_immunology_phase3**: Weight ~0.25 — immunology Phase 3 boost confirmed
- **is_competitive_space**: Flipped sign from +0.009 to -0.176 — competition hurts
- **dose_response**: Grew 3.7x — dose-response data matters more than initially weighted

### Tier Performance (Best Config, Test Set n=1,379)
| Tier | N | Positive Rate | Assessment |
|---|---|---|---|
| TIER_1 | 309 | 92.2% | ✅ Excellent |
| TIER_2 | 622 | 75.9% | ✅ Solid |
| TIER_3 | 230 | 42.2% | ✅ Appropriate |
| TIER_4 | 218 | 1.4% | ✅ Excellent |

---

## Plateau Analysis

The optimizer hit its ceiling around cycle 7 (AUC=0.8497) and only squeezed 0.0007 more through 39 additional cycles. This is classic diminishing returns in hyperparameter search. The remaining gains are in:

1. **Feature engineering** (not hyperparameter tuning)
2. **Calibration** (not raw AUC)
3. **Data quality** (more events, better labels)
4. **Ensemble approaches** (combining top 5 models)
