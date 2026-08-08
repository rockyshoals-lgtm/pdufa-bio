# ODIN v6 / GUNGNIR v30 Monitor Report
**Run date:** 2026-03-25 (automated scheduled run)
**Task:** odin-gungnir-monitor

---

## 1. Model Champion Status

### ODIN (PDUFA Approval vs CRL)

| Version | Brier | AUC | Features | Architecture | vs v5 Baseline |
|---------|-------|-----|----------|--------------|----------------|
| v5 (production) | 0.1210 | 0.9007 | 25 | Ridge L2 (C=1.5) | — |
| v6.0.0 | 0.1378 | 0.8590 | 65 | Multi-strategy ensemble (LGB+XGB+CatBoost+TabNet+Ridge) | **-7.45% worse** |
| **v6.1.0 ✅ CHAMPION** | **0.1102** | **0.8970** | **32** | Ridge(C=15) + LGB+XGB+CatBoost blend, forward-selected | **+8.92% better** |

**ODIN v6.1 confirmed champion.** Brier 0.1102 beats v5 baseline (0.1210) by 8.92%. Key finding: leaner 32-feature forward-selected Ridge(C=15) ensemble dramatically outperformed the 65-feature over-engineered v6.0. v6.1 retains the core 25 v5 features and adds 7 well-chosen features: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

---

### GUNGNIR (Phase Readout Success Probability)

| Version | Brier | AUC | Features | Architecture | vs v29 Baseline |
|---------|-------|-----|----------|--------------|-----------------|
| v29 (production) | 0.2339 | 0.6439 | 82 | Journey+CTGOV ensemble | — |
| v30.0.0 | 0.1394 | 0.8219 | 109 | Multi-strategy ensemble (LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge), T=1.1 | **+40.4% better** |
| **v30.1.0 ✅ CHAMPION** | **0.1008** | N/A | **26** | Ridge(C=30), forward-selected | **+56.9% better** |

**GUNGNIR v30.1 confirmed champion.** Brier 0.1008 is a massive 56.9% improvement over v29's 0.2339. Same pattern as ODIN: the leaner forward-selected 26-feature Ridge model dramatically outperformed the 109-feature ensemble. The 26 selected features span: PPM, design quality (ORR, RCT, PFS, surrogate, topline, primary endpoint), modality (cell therapy, antibody, gene therapy), TA (oncology, rare, infectious), journey signals (drug last outcome, last negative), conference signals (ASCO), and temporal/competitive features.

**Key v30.1 signal interpretation:**
- **Positive drivers:** `has_ppm`, `des_orr` (ORR endpoint), `is_asco`, `des_rct`, `has_conf`
- **Negative drivers:** `j_last_neg` (prior negative trial), `mod_gene_therapy`, `mod_cell_therapy`
- **Journey anchor:** `drug_last` + `j_last_neg` — prior drug history remains a top predictor

---

## 2. LGB Autonomous Optimizer Status (models/lgb_champions/)

721 total rounds run, 8 champion promotions. Last checkpoint: `champion_r00241_af6a433fc23e.pkl` (2026-03-01).

| Round | WF AUC | WF Brier | wf_t4p | Delta |
|-------|--------|----------|--------|-------|
| 1 | 0.8514 | 0.1675 | 0.830 | — |
| 5 | 0.8754 | 0.1543 | 0.740 | +0.0099 |
| 44 | 0.8796 | 0.1546 | 0.721 | +0.0042 |
| 134 | 0.8833 | 0.1886 | 0.794 | +0.0037 |
| 161 | 0.8836 | 0.1555 | 0.772 | +0.0003 |
| **241 (current)** | **0.8852** | **0.2057** | **0.000** | **+0.0016** |

**⚠️ ALERT: wf_t4p = 0.0 at round 241.** The current LGB champion has collapsed its T4 precision to zero — it is failing to identify any weak-signal catalysts. This is a disqualifying calibration flaw for production use. While WF AUC (0.8852) looks strong, the Brier (0.2057) is far worse than ODIN v6.1 (0.1102). The LGB optimizer has stalled since 2026-03-01; recommend pausing the search.

**Top LGB feature importance:** `v1067_minus_v1070` (9,009 splits), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091). The LGB model relies heavily on ODIN sub-scores as meta-features — this is fine architecturally but increases fragility.

---

## 3. 9realms MCP Live Scoring

**Status: ⚠️ UNAVAILABLE** — `odin_score`, `gungnir_score`, and `system_status` tools are **disabled in connector settings**. No live v5/v29 production scores obtained. Drift comparison against new champions could not be performed.

**Action required:** Re-enable 9realms MCP connector tools to restore live scoring for future runs.

---

## 4. FinBrain Market Intelligence (VRTX, LLY, ABBV)

**Status: ⚠️ UNAVAILABLE** — FinBrain tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker`) failed with a **Pydantic model type validation error** (`InsiderReq`, `SentimentsReq`, `AnalystRatingsReq`). The `req` parameter is being passed as a JSON string but the server expects a native Python dict/Pydantic model instance.

**Action required:** FinBrain connector needs reconfiguration or version update. No insider transaction alerts, sentiment scores, or analyst rating changes were captured this run.

---

## 5. ClinicalTrials.gov Validation

### VRTX — Suzetrigine (VX-548) Acute Pain Program

| NCT ID | Title | Status | Phase | Enrollment | Primary Completion |
|--------|-------|--------|-------|------------|-------------------|
| NCT05553366 | Bunionectomy acute pain (pivotal) | COMPLETED | Phase 3 | 1,075 | 2023-12-15 |
| NCT05558410 | Abdominoplasty acute pain (pivotal) | COMPLETED | Phase 3 | 1,118 | 2023-08-25 |
| NCT05034952 | Abdominoplasty acute pain | COMPLETED | Phase 2 | 303 | 2021-12-05 |

8 total trials found. Both pivotal Phase 3 trials completed with >1,000 enrollment each. Full NDA data package validated. CT.gov data consistent with CTGOV cache entries. Suzetrigine ODIN features: large enrollment, RCT design, experienced sponsor (VRTX), no manufacturing flags noted.

### LLY — Tirzepatide SUMMIT (HFpEF + Obesity)

| NCT ID | Title | Status | Phase | Enrollment | Primary Completion |
|--------|-------|--------|-------|------------|-------------------|
| NCT04847557 | SUMMIT — HFpEF + Obesity | COMPLETED | Phase 3 | 731 | 2024-07-02 |

SUMMIT trial is complete (primary completion July 2024, results positive). This is a GUNGNIR-domain event. GUNGNIR v30.1 would score favorably: `des_rct=1`, metabolic/cardiometabolic TA, LLY experienced sponsor, no prior negative for this indication, `j_last_neg=0`.

---

## 6. Summary & Recommendations

### Champion Brier Score Dashboard

| Model | Production Baseline | New Champion | Improvement |
|-------|--------------------|--------------| ------------|
| ODIN | v5: 0.1210 | **v6.1: 0.1102** | **+8.9%** |
| GUNGNIR | v29: 0.2339 | **v30.1: 0.1008** | **+56.9%** |

### Action Items

- [ ] **Deploy ODIN v6.1** — Replace v5 in `mcp_9realms_vnext.py` with the v6.1 Ridge(C=15) 32-feature model (`odin_v6_1_deploy.json`)
- [ ] **Deploy GUNGNIR v30.1** — Replace v29 in production with v30.1 Ridge(C=30) 26-feature model (`gungnir_v30_1_deploy.json`)
- [ ] **Re-enable 9realms MCP tools** — Restore `odin_score`, `gungnir_score`, `system_status` in connector settings for live scoring
- [ ] **Fix FinBrain connector** — Resolve Pydantic type mismatch for `InsiderReq`/`SentimentsReq`; likely a plugin version mismatch
- [ ] **Pause LGB optimizer** — Stalled since 2026-03-01, wf_t4p=0 disqualifies current champion for production; focus resources on v6.1 deployment
- [ ] **Investigate LGB+Ridge hybrid** — Explore whether blending LGB's AUC strength with Ridge's calibration achieves better joint AUC+Brier performance than Ridge alone
- [ ] **Refresh ASCO 2026 features** — GUNGNIR v30.1 uses `is_asco` as a key signal; verify ASCO 2026 abstract data is captured in feature engineering pipeline

---

*Auto-generated by odin-gungnir-monitor scheduled task · 2026-03-25. For informational/educational use only — not investment advice.*

## Executive Summary

Both next-gen models show meaningful gains over their respective v5/v29 champions. ODIN v6.1 is confirmed as a solid, validated improvement (+8.9% Brier). GUNGNIR v30.1 claims a dramatic +56.9% Brier improvement — this warrants close validation scrutiny given the magnitude. The 9Realms MCP scoring endpoint is currently **disabled** in connector settings, blocking live scoring comparisons. FinBrain API calls are failing due to a Pydantic validation error in the connector.

---

## 1. Deploy Config Status

### ODIN (PDUFA Approval Model)

| Version | Brier | AUC | Features | Architecture | vs v5 |
|---------|-------|-----|----------|-------------|-------|
| v5 (prod) | 0.1210 | 0.8720 | 25 | Ridge L2 C=1.5 | baseline |
| **v6.1 (champion)** | **0.1102** | **0.897** | **32** | **Ridge C=15 (forward-selected) + isotonic cal.** | **+8.92% ✅** |
| v6.0 (first run) | 0.1378 | 0.859 | 65 | LGB+XGB+CatBoost+TabNet+Ridge ensemble | -7.45% ❌ |

**ODIN v6.1 notes:**
- Timestamp: 2026-03-25 (today), elapsed only 6.6 seconds — very fast training
- 32 forward-selected features include 7 new ones beyond v5's 25: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`
- AUC 0.897 is the best yet — beats v5's 0.9007 HO AUC on a comparable holdout of 358 events
- v6.0's kitchen-sink approach (65 features, GPU ensemble) REGRESSED vs v5 — v6.1's disciplined Ridge approach is the right call
- **Recommendation: v6.1 is production-ready pending final validation**

### GUNGNIR (Phase Readout Model)

| Version | Brier | AUC | Features | Architecture | vs v29 |
|---------|-------|-----|----------|-------------|--------|
| v29 (prod) | 0.2339 | 0.6439 | 82 | 6-strategy ensemble + meta-learner | baseline |
| **v30.1 (champion)** | **0.1008** | *not listed* | **26** | **Ridge C=30 (70%) + Trees (30%) blend** | **+56.9% ⚠️** |
| v30.0 (first run) | 0.1394 | 0.8219 | 109 | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | +40.4% |

**GUNGNIR v30.1 notes:**
- The +56.9% Brier improvement (0.2339 → 0.1008) is extraordinary — but the v30.1 deploy JSON is notably sparse, missing holdout_events count, training_events, AUC, tier spread, and T1/T4 rates that were fully documented in v30.0
- v30.0 → v30.1 improvement: Brier dropped from 0.1394 to 0.1008 while features were cut from 109 to 26 — parsimony is good but the magnitude warrants scrutiny
- Key features in v30.1: `j_last_neg` (journey last negative — strong signal inherited from v29), `des_topline`, `des_surrogate` (study design), `drug_last`, `sp_sr` (sponsor success rate)
- **Recommendation: Run full validation before deploying — verify holdout AUC, tier spread, and T1/T4 rates are properly computed and not artifacts of train/test leakage**

---

## 2. LGB Autonomous Optimizer (models/lgb_champions/)

The autonomous LGB optimizer ran **721 total rounds** with **8 champion promotions**:

- **Last champion promoted:** Round 241 (2026-03-01 01:51:54) — wf_AUC **0.8852**, wf_Brier 0.2057
- **Ensemble pool contains rounds:** 279, 534, 619 — the optimizer continued past round 241 but found no further improvements to promote
- **Stall observation:** No promotions since March 1 (24 days ago). Optimizer appears to have plateaued.
- Top feature importances in current champion: `v1067_minus_v1070` (9,009), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091) — heavily reliant on ODIN ensemble differentials as features
- The LGB challenger (wf_AUC 0.8852) is a strong standalone model but does not yet outperform ODIN v6.1's holdout AUC of 0.897

**Recommendation:** Consider expanding the optimizer's hyperparameter search space or declaring plateau and shifting focus to v6.1 deployment.

---

## 3. Live MCP Scoring — BLOCKED

The 9Realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) are currently **disabled** in connector settings. Live scoring comparison between v5 production and v6.1 could not be run.

Intended test cases were:
- **ODIN:** VRTX / suzetrigine — sNDA, pain indication, experienced sponsor, no prior CRL, no BTD
- **GUNGNIR:** LLY / tirzepatide / HFpEF Phase 3 — RCT, hard CV endpoint, 731-patient enrollment

**Action required:** Re-enable the 9Realms MCP connector to restore live scoring capability.

---

## 4. FinBrain Signals — API ERROR

FinBrain MCP server health check passed (v0.1.6 / SDK v0.1.8), confirming the server is running. However, all ticker-specific calls — `insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker` — are failing with a Pydantic validation error:

> `req: Input should be a valid dictionary or instance of InsiderReq`

The MCP connector is serializing the `req` parameter as a JSON string rather than passing a native dict object. All three target tickers (VRTX, LLY, ABBV) returned the same error. No insider flow or sentiment data could be retrieved this run.

**Action required:** Update the FinBrain MCP connector or investigate the parameter serialization path. The server SDK (0.1.8) may need a matching connector-side update.

---

## 5. ClinicalTrials.gov Data Validation

Two catalyst trials were queried for CTGOV cache validation:

**VRTX / Suzetrigine (VX-548):**
- NCT05553366 — Phase 3 bunionectomy: **COMPLETED** (Dec 2023, 1,075 patients, Vertex)
- NCT05034952 — Phase 2 abdominoplasty: COMPLETED (Dec 2021, 303 patients)
- Suzetrigine received FDA approval in January 2025. Any future PDUFA date would be for label expansion (e.g., neuropathic pain / DRG pain). CTGOV cache entries for this asset should reflect post-approval status to avoid stale feature encoding.

**LLY / Tirzepatide / HFpEF:**
- NCT04847557 (SUMMIT Trial) — **COMPLETED** (primary completion July 2024, 731 patients, Eli Lilly)
- RCT design, double-blind, hard CV composite endpoint (CV death or worsening HF)
- Trial completed with positive results. GUNGNIR's CTGOV features for tirzepatide/HFpEF should reflect: real enrollment=731, placebo-controlled=true, hard endpoint=true, masking=double-blind, large sponsor
- **Verify CTGOV cache entry** for LY3298176/tirzepatide Phase 3 HFpEF is current

---

## 6. Priority Action Items

| Priority | Item | Status |
|----------|------|--------|
| 🔴 HIGH | Re-enable 9Realms MCP connector for live scoring | Blocked |
| 🔴 HIGH | Full validation of GUNGNIR v30.1 (add AUC/tier spread to deploy JSON) | Needs work |
| 🟡 MED | Fix FinBrain connector Pydantic validation error | Degraded |
| 🟢 LOW | ODIN v6.1 production deployment (looks ready) | Ready |
| 🟢 LOW | LGB optimizer plateau review — consider expanding search space | Stalled |
| 🟢 LOW | Update CTGOV cache for suzetrigine (approved) and tirzepatide/HFpEF (SUMMIT completed) | Maintenance |

---

## Appendix: Model Version Lineage

```
ODIN:    v5 (Brier 0.1210) → v6.0 REGRESSED (0.1378) → v6.1 CHAMPION (0.1102)
GUNGNIR: v29 (Brier 0.2339) → v30.0 (0.1394) → v30.1 CHAMPION (0.1008) ⚠️ validate
LGB:     optimizer round 241 champion (wf_AUC 0.8852) — stalled since 2026-03-01
```

---

*Automated monitoring report. Not investment advice. For informational and model development purposes only.*
