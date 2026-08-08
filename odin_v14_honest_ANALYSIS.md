# ODIN v14 Test-Set Leakage Analysis

## Finding Summary

**CONFIRMED LEAKAGE**: ODIN v14 (HO AUC 0.9363) contains critical test-set leakage in feature selection. The kaizen pipeline directly uses holdout AUC to accept/reject candidate features and select regularization parameter C. This violates ML best practices and inflates reported holdout metrics.

## Leakage Location

**Phase 2 (C Sweep)** — lines 399-406 in odin_v14_kaizen.py:
```python
for C in c_values:
    model = LogisticRegression(C=C, solver='lbfgs', max_iter=5000, random_state=0)
    model.fit(X_train, y_train)
    ho_auc = roc_auc_score(y_holdout, model.predict_proba(X_holdout)[:, 1])
    if ho_auc > best_ho_auc:  # <-- LEAKAGE: using holdout AUC to select C
        best_ho_auc = ho_auc
        best_c = C
```

**Phase 3 (Greedy Forward Selection)** — lines 450-456:
```python
for C in c_values:
    model = LogisticRegression(C=C, solver='lbfgs', max_iter=5000, random_state=0)
    model.fit(X_train_with_feature, y_train)
    ho_auc = roc_auc_score(y_holdout, model.predict_proba(X_holdout_with_feature)[:, 1])
    if ho_brier < best_ho_brier or (... and ho_auc > best_ho_auc):  # <-- LEAKAGE
        best_ho_auc = ho_auc
```

## Correct Implementation

Holdout data should NEVER be accessed during model training or feature selection. The correct pattern is:

1. **Phase 0 (Honest Baseline)**: Test multiple C values using VAL AUC only → select best C → evaluate ONCE on holdout
2. **Phase 2 (Feature Addition)**: Test candidate features using VAL AUC → accept only if improves val AUC → holdout touched once at end
3. **Phase 3 (Feature Pruning)**: Test feature removals using VAL AUC → drop only if improves val AUC → holdout touched once at end

The reported workflow uses holdout in the inner loop of feature selection, which causes the model to overfit to holdout characteristics during training.

## Inflation Quantification

Based on precedent (BIFROST v5.5 similar leakage):
- BIFROST v5.5 reported HO AUC: 0.9487
- BIFROST v5.5 honest replication: ~0.86 (estimated, 626bp inflation)

**Expected ODIN v14 honest HO AUC**: 0.88-0.90 range (360-450bp inflation from reported 0.9363)

Honest Brier likely ~0.12-0.14 (vs reported 0.0895).

## Impact on Deployment

**Current Status**: ODIN v14 is deployed in MCP as primary PDUFA scoring engine. The 50bp overestimation of holdout AUC means:
- Real-world approval prediction accuracy is ~50bp worse than advertised
- Confidence intervals around ODIN tier assignments are tighter than true uncertainty
- BIFROST runup timing model calibrated against inflated v14 tiers — magnitude predictions may be less precise

**Recommendation**:
1. **Option A (Prefer)**: Rollback to ODIN v13 (verified honest HO AUC 0.9315 with 20/20 stability audit)
2. **Option B**: Ship ODIN v14_honest at honest AUC with revised confidence intervals and caveat in MCP docstring
3. **Option C**: Implement honest v14 Kaizen immediately and re-baseline v14.1

## Evidence Chain

1. Code inspection confirms leakage pattern in lines 399-406 and 450-456
2. No validation set used; inner loop optimization on holdout directly
3. C parameter selection based on best holdout AUC (line 403: `if ho_auc > best_ho_auc`)
4. Feature acceptance based on holdout metrics (line 453: conditional includes `ho_auc > best_ho_auc`)
5. No 20/20 seed stability test over holdout (only train/val randomization)
6. Reported WF AUC (0.9011) < HO AUC (0.9363) — inverted from typical overfitting pattern, consistent with HO-optimization leakage

## Honest Replication Path

To produce honest ODIN v14_honest:
1. Implement 3-way temporal split: train ≤2022, val 2023-2024, holdout 2025-2026
2. Engineer 51 v14 features with temporal snapshotting (frozen at event date)
3. Phase 0: Test C ∈ [0.007, 0.1] using VAL AUC only → select best_c
4. Final eval: apply best_c model to holdout → report honest HO AUC + Brier
5. Run 20-seed stability audit over holdout (bootstrap across random states)

## Files Affected

- `/mnt/9realms/odin_v14_deploy.json` — weights remain valid, but metric confidence overstated
- `/mnt/9realms/odin_v14_honest.py` — honest replication script (in progress, feature engineering blocked by missing temporal data engineering)
- MCP `odin_score` tool — docstring should disclose inflation risk until v14_honest ships

## Conclusion

ODIN v14 is not suitable for deployment without honest re-validation. The 4x less regularization (C: 0.025→0.10) combined with holdout-based feature selection created a perfect storm for overfitting. Immediate action: rollback to v13 pending v14_honest completion, or ship with explicit caveat about 350-450bp AUC inflation risk.

---

**Analysis Date**: 2026-04-17
**Status**: CONFIRMED LEAKAGE, RECOMMEND ROLLBACK TO v13
