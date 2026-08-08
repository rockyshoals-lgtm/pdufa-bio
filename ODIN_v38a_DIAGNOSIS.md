# 🤖 ODIN v38a Backtest Analysis: Overfitting Detected
**Model**: ODIN_v38a_patch11_gpu_rowchunk_reportevery_mccsafe  
**Status**: 🔴 **DO NOT TRADE YET - Class Imbalance Problem**  

---

## INSTANT DIAGNOSIS

Your model has **classic overfitting from class imbalance**:

✅ **Precision**: 99.1% (looks amazing, but misleading)  
❌ **Recall**: 9.9% (missing 90% of actual CRLs - CRITICAL ISSUE)  
❌ **F1 Score**: 0.180 (below any trading threshold)  
❌ **MCC**: 0.113 (barely better than random)  

**Translation**: Model learned "never predict CRL" = high precision when it does, but misses 90% of the signal.

---

## THE PROBLEM IN 30 SECONDS

### Your Dataset

```
Total decisions: 1349
Approvals:      1169 (86.6%)
CRLs:           180 (13.4%)

Imbalance ratio: 6.5:1 (approvals heavily outnumber CRLs)
```

### What Your Model Does

```
Actual CRLs:    180
Model predicts CRL: 117 times total (116 correct, 1 wrong)
Model misses:   1053 CRLs (90.1% miss rate)

Result:
- When model says "CRL" → 99.1% correct
- But it only says "CRL" 8.7% of the time
- You MISS 90% of actual CRLs
```

### Why This Happens

```
Unbalanced loss function:
- Model learns "just predict approval" → 86.6% accuracy for free
- Threshold climbs to p_threshold = 0.9878 (98.78% confidence required!)
- Only makes CRL predictions when EXTREMELY confident
- Gets those few predictions right (high precision)
- But misses the vast majority (low recall)

This is the classic overfitting signature.
```

---

## THE METRICS EXPLAINED

### Confusion Matrix

```
              PREDICTED
            Approval  CRL
ACTUAL Approval 1169   0
       CRL      1053  116

Key Issue:
FN (False Negatives): 1053 ← You're losing money on these
                            (predicting approval, actually CRL)
```

### Each Metric's Story

| Metric | Score | Meaning | Problem |
|--------|-------|---------|---------|
| **Precision** | 99.1% | "When model says CRL, is it right?" | Misleading - only says CRL 117 times |
| **Recall** | 9.9% | "Does it catch all CRLs?" | NO - misses 90% |
| **F1 Score** | 0.180 | "Balanced metric?" | Terrible (need >0.40) |
| **MCC** | 0.113 | "True correlation?" | Barely better than random |
| **Specificity** | 99.4% | "Good at approvals?" | Yes, but not the goal |

### F1 Score Is The Truth Teller

```
F1 = harmonic mean of precision and recall
F1 = 2 × (Precision × Recall) / (Precision + Recall)
F1 = 2 × (0.991 × 0.099) / (0.991 + 0.099)
F1 = 0.180

F1 scale:
1.0 = perfect
0.6 = tradeable
0.3 = weak
0.0 = random

Your F1 = 0.180 = WEAK (not tradeable)
```

---

## THE ROOT CAUSE

### p_threshold is Way Too High

```
Your setting:  p_threshold = 0.9878
Normal range:  0.50 ± 0.20

What this means:
- 0.50 = "50% confident = predict CRL"
- 0.70 = "70% confident = predict CRL"
- 0.9878 = "99% confident = predict CRL" ← ABSURDLY HIGH

Result:
- Model only makes CRL predictions when almost certain
- Gets those right (99% precision)
- But never predicts CRL most of the time (9.9% recall)
```

### Manufacturing Amp Weight Is Dominant

```
w_mfg_amp = 2.87 ← Massive weight on manufacturing issues

This tells you:
- Model learned "manufacturing defects = CRL" strongly
- Probably overfitting to manufacturing data in training set
- Real-world CRLs have many other causes
```

### Base Probability Is Wrong

```
p_base = 0.517 ← 51.7% of decisions are CRL

Reality: FDA approval success rate = 85-90% (CRL rate = 10-15%)
Your model assumes: 51.7% CRL rate (!!)

This is backwards and suggests:
- Class imbalance not handled in training
- Model learning from corrupted or skewed dataset
```

---

## THE SOLUTION

### Step 1: Fix Class Imbalance (CRITICAL)

```python
# Current: unweighted loss
loss = model.calculate_loss(y_true, y_pred)

# Fixed: weighted loss
class_weights = {
    'approval': 1.0,
    'crl': 6.5  # Weight rare class by imbalance ratio
}
loss = weighted_loss(y_true, y_pred, class_weights)
```

**Expected impact**: Recall 9.9% → 40-60%

### Step 2: Optimize For F1, Not Fitness Score

```
Current: Maximize fitness (raw genetic algorithm score)
Problem: Leads to overfitting on validation set

Fixed: Maximize F1 score (0-1 scale)
Reason: F1 naturally balances precision and recall
```

**Expected impact**: F1 0.18 → 0.40-0.55

### Step 3: Constraint p_threshold

```
Current range: 0.9878 (anything goes)
Fixed range: 0.20 - 0.70 (reasonable bounds)

This prevents future runs from being over-conservative
```

**Expected impact**: Threshold drops to 0.30-0.50 naturally

### Step 4: Cross-Validate

```
Current: Single train/test split
Problem: Can overfit to specific validation set

Fixed: 5-fold cross-validation
- Train on 4 folds, test on 1
- Repeat 5 times
- Average metrics across all folds

Result: Eliminates validation overfitting, stabilizes metrics
```

**Expected impact**: More honest F1 score, identifies overfitting

### Step 5: Calculate ROC-AUC

```
Generate ROC curve and calculate AUC score

AUC tells you:
- 0.5 = random
- 0.7 = decent discriminative ability
- 0.8 = good
- 0.9 = excellent

If AUC < 0.70, model doesn't have tradeable signal
```

**Expected impact**: Understand true model capability

---

## TRADING IMPLICATIONS

### Current State: DO NOT TRADE

**Why**:
- Recall = 9.9% → You're long into 90% of CRLs (massive losses)
- F1 = 0.18 → Below any reasonable trading threshold
- MCC = 0.113 → Model barely more predictive than random

**Expected P&L**: Negative (losing money)

### After Fixes: POSSIBLY TRADEABLE

**If you reach F1 > 0.40**:
- Recall improves to 40-60% (actually catch some CRLs)
- Precision drops to 20-30% (more false alarms, acceptable)
- Balanced enough to test on real price data

**Still need to validate**:
1. **Forward-looking**: Does model predict CRL BEFORE market knows? (most important)
2. **Profitability**: Do caught CRLs profit > losses from false alarms?
3. **Walk-forward test**: Test on newest data not in training set

---

## PRIORITY CHECKLIST

### Do This Immediately (Today)

- [ ] Implement weighted loss function (30 min)
- [ ] Change optimization metric to F1 (15 min)
- [ ] Set p_threshold constraint: 0.20-0.70 (10 min)

### Do This Soon (This Week)

- [ ] Retrain model with fixes (1-2 hours)
- [ ] Run 5-fold cross-validation (2-3 hours)
- [ ] Calculate ROC-AUC curve (30 min)

### Do This Before Trading (This Month)

- [ ] Walk-forward validation on recent data
- [ ] Test on price data (see if CRL predictions move stock)
- [ ] Paper trade for 1-2 weeks
- [ ] Only then go live

---

## EXPECTED METRICS AFTER FIXES

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| **Precision** | 99.1% | 20-30% | ✅ Accepts more CRLs |
| **Recall** | 9.9% | 40-60% | ✅ Catches more CRLs |
| **F1 Score** | 0.180 | 0.40-0.55 | ✅ Tradeable range |
| **MCC** | 0.113 | 0.25-0.35 | ✅ More predictive |
| **p_threshold** | 0.9878 | 0.30-0.50 | ✅ More reasonable |

---

## BOTTOM LINE

Your Odin model is **overfitted to the "never predict CRL" strategy**. This works great for precision (almost never wrong) but fails completely for recall (missing 90% of signals).

**The fix is straightforward**: 
1. Use weighted loss function
2. Optimize F1 instead of fitness
3. Retrain in 2-4 hours

**Timeline to trading-ready**: 1 week (with validation)

**Conviction**: 95% confident this is the issue (classic class imbalance signature)

---

**Analysis Date**: January 24, 2026  
**Code**: ODIN_v38a_patch11_gpu_rowchunk_reportevery_mccsafe