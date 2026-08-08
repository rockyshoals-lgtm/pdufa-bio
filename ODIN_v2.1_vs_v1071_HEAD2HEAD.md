# ODIN v2.1 vs v1070/v1067 — Head-to-Head Validation Report

**Generated:** 2026-03-01
**Dataset:** ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv
**Events:** 2,210 total (2,203 with known outcomes)
**Outcome Split:** 1,498 APPROVAL / 705 CRL
**Date Range:** Jan 2017 → Sep 2025

---

## Model Comparison

| Metric | v1067 Logistic | v1070 Logistic | ODIN MCP v10.2 | **ODIN v2.1 LGB** |
|--------|---------------|---------------|----------------|-------------------|
| Architecture | Logistic Regression | Logistic Regression | Honed Logistic (55w) | LightGBM (45 feat) |
| AUC | 0.8940 | 0.8849 | 0.9085 | **0.9193** |
| Brier Score | — | 0.1228 | 0.0968 | **0.0764** |
| Tier4 Precision (≥0.85) | — | 94.8% (831 events) | — | 78.3% (WF) |
| Walk-Forward? | No (in-sample) | No (in-sample) | Yes | **Yes** |

### v2.1 Walk-Forward Yearly AUCs
| Year | AUC |
|------|-----|
| 2021 | 0.9357 |
| 2022 | 0.9259 |
| 2023 | 0.8902 |
| 2024 | 0.9185 |
| 2025 | 0.9264 |

### Delta Analysis
- **v2.1 vs v1070:** +0.0344 AUC (walk-forward vs in-sample — actual edge is larger)
- **v2.1 vs MCP v10.2:** +0.0108 AUC (both walk-forward)
- **Brier improvement:** v2.1 (0.0764) vs v1070 (0.1228) → **37.8% reduction in calibration error**

---

## GUNGNIR v1.1 LGB Champion

| Metric | GUNGNIR MCP v25 | **GUNGNIR v1.1 LGB** |
|--------|----------------|---------------------|
| Architecture | Island-Model Evolutionary | LightGBM (56 feat) |
| WF AUC | 0.988 | **0.9976** |
| Brier | 0.031 | 0.0643 |
| Tier4 Precision | — | **98.7%** |
| Dataset | 2,000 readouts | 2,000 readouts |

### Top Features (by importance)
1. indication_positive_rate (287)
2. catalyst_text_len (210)
3. sentiment_composite (102)
4. primary_endpoint_met (72)
5. price_at_catalyst (65)

---

## Champion Model Specifications

### ODIN v2.1 LGB
- **Params:** num_leaves=126, lr=0.146, n_estimators=805, max_depth=-1
- **Regularization:** L1=0.0005, L2=0.00003, min_gain=0.108
- **Bagging:** fraction=0.772, freq=9
- **Feature fraction:** 0.776
- **Engineered features (15):** base_rate_ta_sq, btd_x_oncology, cash_x_experienced, desig_x_experienced, insider_x_social, is_class1_resub, is_gene_therapy, is_hoeg_era, is_neurology, is_ophthalmology, is_pain, log_ae, orphan_x_desig_stack, pr_x_experienced, year
- **Top importances:** publications_12m (322), ae_count_12m (168), sponsor_prior_approvals (113), year (93), cash_runway_months (85)

### GUNGNIR v1.1 LGB
- **Params:** num_leaves=9, lr=0.056, n_estimators=484, max_depth=2
- **Regularization:** L1=1.5e-08, L2=0.274
- **Bagging:** fraction=0.965, freq=6
- **Feature fraction:** 0.406
- **Engineered features (18):** blockbuster_convenience, cns_phase3_strong, complete_response_rare, cr_immunology, cr_phase3, endpoint_met_phase3, endpoint_x_safety, indication_positive_rate, is_recent_year, moonshot_composite, price_adj_sentiment, refractory_immunotherapy, refractory_onco_rr, sentiment_composite, small_cap_phase3_clean, stage_freq, ta_immunology_phase3, ta_oncology_phase2

---

## SHA-256 Integrity Hashes

```
dataset:              261b0765519dcaddc1be6bec82ed9603098e558b794dbc517da621c8f0f5076a
odin_lgb_champion:    5d41360ac41585ea9024b5a18e24b2d317e3bc52675d321932405447822b24d0
gungnir_lgb_champion: 3f62db7ec91b0706049c77f7bd0ba07658b07c0c176a97f262737246a559d2bb
champion_ladder:      0d39358ca16723e11e33159e0f9d62fb969081479daf3b8d0c87ccba8c1f4b58
```

---

## Conclusion

ODIN v2.1 LGB is a clear upgrade over all logistic regression variants on the 2,210-event dataset. Walk-forward AUC of 0.9193 with consistent yearly performance (0.89-0.94 range) confirms generalization. Brier score of 0.0764 indicates well-calibrated probabilities. Recommended for immediate deployment to pdufa.bio.
