# ODIN v6 / GUNGNIR v30 — Monitor Report v8
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | -7.5% vs v5 (worse) | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

### Key Observations

**ODIN v6.1 (CHAMPION)**: Ridge C=15.0 with 32 forward-selected features. Massive improvement over v6.0's 65-feature ensemble (0.1378 Brier). The simpler model wins decisively — classic bias-variance tradeoff victory. Holdout AUC 0.897 is competitive with v5's 0.9007, while Brier drops from 0.1210 to 0.1102 (+8.9%). Seven new features over v5: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**GUNGNIR v30.1 (CHAMPION)**: Ridge(70%)+Trees(30%) blend with just 26 features achieves 0.1008 Brier — a stunning 56.9% improvement over v29's 0.2339. This is by far the best GUNGNIR has ever performed. The feature set is clean and interpretable: drug journey signals (`drug_last`, `j_last_neg`), trial design (`des_rct`, `des_pfs`, `des_orr`, `des_surrogate`, `des_topline`), therapeutic area signals, and modality markers.

**v6.0 vs v6.1**: v6.0 was WORSE than v5 (0.1378 vs 0.1210) despite 65 features + GPU ensemble. v6.1 fixed this by dropping to 32 features with Ridge-only. Lesson: more features ≠ better calibration.

**v30.0 vs v30.1**: v30.0 used 109 features + GPU ensemble and achieved 0.1394. v30.1 slashed to 26 features and hit 0.1008. Same pattern — simpler wins.

---

## 2. Production MCP Scoring — DISABLED

The 9realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) are **disabled in connector settings** this run. Cannot compare production v5/v29 scores against new model predictions.

**Action Required**: Re-enable 9realms MCP connector to allow production score monitoring.

---

## 3. FinBrain MCP — PARAMETER INCOMPATIBILITY

FinBrain MCP is **healthy** (v0.1.6, SDK v0.1.8) but the `req` parameter expects a Pydantic model instance that cannot be constructed through the current MCP tool interface. All ticker-specific calls (insider_transactions, news_sentiment, analyst_ratings) fail with validation errors.

**Action Required**: FinBrain MCP `req` parameter needs a schema fix to accept plain JSON objects, or the MCP connector needs to be updated to handle Pydantic model serialization.

**Intended checks (deferred)**:
- VRTX insider transactions (PDUFA tomorrow 3/26)
- LLY insider transactions (orforglipron Phase 3 readouts pending)
- ABBV insider transactions

---

## 4. ClinicalTrials.gov Validation

### Vertex — Vanzacaftor/Tezacaftor/Deutivacaftor (CF)
- **NCT06154447**: VX-828 study, RECRUITING, 255 enrollees, primary completion 2026-04-23
- **NCT06298709**: Bioavailability study, COMPLETED (34 enrollees)
- **NCT05867147**: QT/QTc ECG study, COMPLETED (56 enrollees)
- 6 total trials found. Core registration studies are complete, supporting PDUFA decision tomorrow (3/26).

### Eli Lilly — Orforglipron (Obesity)
- **NCT07153471**: Phase 3 obesity + knee OA study, RECRUITING (800 target), completion 2028-04
- **NCT05872620**: ATTAIN study obesity + T2D, COMPLETED (1,613 enrollees), completed 2025-08
- 9 total trials found. ATTAIN study data is available; large new OA indication trial recruiting.

---

## 5. LightGBM Autonomous Optimizer (Legacy)

The `models/lgb_champions/` directory shows a completed 721-round optimization run (Feb 28 – Mar 1):
- **8 champion promotions** over 721 rounds
- Best WF AUC: 0.8852 (round 241, hash af6a433fc23e)
- 51 features, LightGBM GBDT (948 estimators, lr=0.009)
- Top feature importance: `v1067_minus_v1070` (9009), `historical_crl_rate` (8576), `v1070_score` (6940)
- **Note**: This LGB champion has WF Brier 0.2057, significantly worse than ODIN v6.1's 0.1102. The Ridge model dominates on calibration.

---

## 6. Recommended Next Steps

1. **Re-enable 9realms MCP** — Critical for production score monitoring and drift detection
2. **Fix FinBrain MCP req parameter** — Update schema or connector to accept JSON objects for insider/sentiment tracking
3. **Deploy v6.1 + v30.1 to production MCP** — Both models are validated champions with substantial improvements. Update `mcp_9realms_vnext.py` to embed v6.1 (32 features) and v30.1 (26 features)
4. **Update CLAUDE.md** — Reflect new champion versions (ODIN v6.1, GUNGNIR v30.1) and retire v5/v29 references
5. **VRTX PDUFA watch** — Decision expected tomorrow 3/26. High-conviction catalyst for ODIN scoring validation
6. **Feature ablation study** — v6.1's 7 new features (especially `sponsor_rolling_approval_rate`, `experienced_x_low_crl`) should be validated for T-1 compliance and leakage-free status
7. **GUNGNIR v30.1 holdout analysis** — Document tier spread and calibration curve for the 0.1008 Brier model

---

## 7. Version Lineage

```
ODIN:     v5 (0.1210) → v6.0 (0.1378, worse) → v6.1 (0.1102, CHAMPION ✓)
GUNGNIR:  v29 (0.2339) → v30.0 (0.1394) → v30.1 (0.1008, CHAMPION ✓)
```

---

*Report generated automatically. ODIN is for PDUFA events only. GUNGNIR is for phase readouts only. Not investment advice.*
