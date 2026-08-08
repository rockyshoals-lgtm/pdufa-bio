# ODIN v6 / GUNGNIR v30 Monitoring Report
**Date:** 2026-03-25 | **Scheduled Run #2**

---

## 1. Champion Model Status

### ODIN v6.1.0 (PDUFA Scoring) — CHAMPION
| Metric | v5 Baseline | v6.0.0 | v6.1.0 (Champion) |
|--------|------------|--------|-------------------|
| Holdout Brier | 0.1210 | 0.1378 | **0.1102** |
| Holdout AUC | 0.9007 | 0.859 | **0.897** |
| Brier vs v5 | — | -7.45% (worse) | **+8.92% (better)** |

- **Architecture:** Ridge(C=15.0), 32 forward-selected features, isotonic calibrated
- **Training:** 1,845 events, 358 holdout, temporal cutoff 2025-01-01
- **Key insight:** v6.0.0 with 65 features and GPU ensemble (LGB+XGB+CatBoost+TabNet+Ridge) actually *regressed* vs v5. The simpler v6.1.0 Ridge with 32 features recovered and surpassed v5 — confirming that regularization > complexity for this dataset.
- **7 new features over v5:** year, sponsor_rolling_approval_rate, adcom_x_pr, sponsor_volume_log, month, experienced_x_low_crl, spa_mid

### GUNGNIR v30.1.0 (Phase Readout Scoring) — CHAMPION
| Metric | v29 Baseline | v30.0.0 | v30.1.0 (Champion) |
|--------|-------------|---------|-------------------|
| Holdout Brier | 0.2339 | 0.1394 | **0.1008** |
| Brier vs v29 | — | +40.4% | **+56.9%** |
| Holdout AUC | 0.6439 | 0.8219 | N/A in deploy |

- **Architecture:** Ridge(C=30) + Trees(30%) blend, 26 features
- **Key insight:** Massive Brier improvement. v30.0.0 used 109 features with GPU ensemble — already a huge leap. v30.1.0 cut to 26 features with Ridge+Trees blend and pushed Brier under 0.10 — extraordinary calibration.
- **Notable features:** drug_last (journey), sp_sr (sponsor success rate), era_post24, competitive, is_asco, des_rct, des_topline

---

## 2. Autonomous Optimizer Status

### Models Directory (checked this run):
- `models/lgb_champions/` — LightGBM champion checkpoints present
- `models/lightgbm_challenger.py` — Challenger training script (Feb 28)
- `models/lightgbm_challenger_v1.pkl` — Challenger model (~3MB, Feb 28)
- `models/v1071_GOLD_STANDARD.pkl` — ODIN gold standard reference
- `models/model_registry/` — Registry directory present

### Logs Directory:
- **NOT FOUND** — No `logs/` directory exists. Optimizer iteration logs are not being persisted.

⚠️ **No new checkpoints since Feb 28 / Mar 2** — Optimizer appears idle for 23+ days. From prior run, the LGB challenger had WF Brier of 0.2057, which is WORSE than ODIN v6.1's 0.1102. Ridge remains the clear champion.

---

## 3. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | Connector settings have tools disabled |
| FinBrain MCP (insider, sentiment, analyst) | **ERROR** | Pydantic validation: `req` expects model instance, receives JSON string |
| ClinicalTrials.gov MCP | **ERROR** | Output schema mismatch on `pagedStudies` property |

### All 3 external MCP integrations are non-functional this run.

**Action Required:**
1. **9realms MCP:** Re-enable odin_score, gungnir_score, system_status in connector settings
2. **FinBrain MCP:** Fix `req` parameter — Pydantic InsiderReq/SentimentsReq model validation rejects dict input
3. **ClinicalTrials.gov MCP:** Output schema expects `pagedStudies` property but response doesn't match

---

## 4. Optimization Trajectory

### ODIN: v5 → v6.0 → v6.1
```
v5 (baseline)  →  v6.0 (REGRESSION)  →  v6.1 (NEW CHAMPION)
Brier: 0.1210      0.1378 (-7.5%)        0.1102 (+8.9%)
Feat:  25           65                     32
Arch:  Ridge C=1.5  Deep ensemble          Ridge C=15
```

### GUNGNIR: v29 → v30.0 → v30.1
```
v29 (baseline)  →  v30.0 (IMPROVEMENT)  →  v30.1 (CHAMPION)
Brier: 0.2339       0.1394 (+40.4%)         0.1008 (+56.9%)
Feat:  82            109                      26
Arch:  6-strategy    Deep ensemble            Ridge+Trees blend
```

**Consistent pattern:** Simpler, regularized models with fewer features beat complex deep ensembles on both engines.

---

## 5. Summary & Recommendations

### Current State: CHAMPIONS STABLE, TOOLING DEGRADED

Both v6.1 (ODIN) and v30.1 (GUNGNIR) remain champion with no new challengers since early March. The models are stable, but monitoring capability is severely limited with all 3 external MCP servers non-functional.

### Priority Actions:

1. **CRITICAL: Fix MCP connectivity** — All 3 MCP integrations (9realms, FinBrain, ClinicalTrials.gov) are broken. Without production scoring, insider data, and trial validation, this monitor is limited to config file analysis.

2. **Investigate GUNGNIR v30.1 Brier 0.1008** — This is suspiciously good for phase readout prediction. Recommend walk-forward validation across multiple temporal splits to confirm it's not holdout-specific.

3. **Restart or audit LGB optimizer** — 23+ days idle with no new checkpoints. Either the process stalled or converged at a local minimum worse than Ridge.

4. **Create logs/ directory** — No iteration logs are being persisted. Critical for reproducibility.

5. **Update CLAUDE.md** — Still references v5/v29 as production champions. Should be updated once v6.1/v30.1 are validated for production deployment.

6. **ODIN v6.2 candidates:** Try C=20-50 range on Ridge; add CTGOV enrollment features from `ctgov_cache.json`.

7. **GUNGNIR v30.2 candidates:** Re-add 3-5 CTGOV real trial features (enrollment, masking, arms) that v30.0 had but v30.1 dropped.

---

*Report generated automatically by ODIN/GUNGNIR monitoring task (Run #2).*
*Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
