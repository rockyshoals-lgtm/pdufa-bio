# ODIN v6 / GUNGNIR v30 Monitoring Report
**Run Date:** 2026-03-25 | **Automated Scheduled Task**

---

## 1. Champion Scorecard

| Engine | Version | Brier Score | Baseline Brier | Improvement | AUC | Features | Architecture |
|--------|---------|------------|---------------|-------------|-----|----------|-------------|
| ODIN | v6.1 ✅ CHAMPION | **0.1102** | v5: 0.1210 | +8.92% | 0.897 | 32 (forward-selected) | Ridge C=15, isotonic calibrated |
| GUNGNIR | v30.1 ✅ CHAMPION | **0.1008** | v29: 0.2339 | +56.9% | — | 26 (forward-selected) | Ridge(70%) + Trees(30%) blend |

---

## 2. Deploy Config Review

### ODIN: v6.0 → v6.1 Progression

**v6.0 (First run, 2026-03-25T13:26)** — ❌ REGRESSED vs v5
- Architecture: Complex multi-strategy ensemble (LGB + XGB + CatBoost + TabNet + Ridge), GPU
- Features: 65 (bloated, including many low-signal interactions)
- Holdout Brier: **0.1378** (v5 was 0.1210 → **-7.45% regression**)
- Holdout AUC: 0.859 (v5 was 0.8717 → -1.45% regression)
- T1 rate: 93.2%, T4 rate: 25.4%
- Lesson: Complexity didn't help; over-parameterized ensemble overfit on training tail

**v6.1 (Current champion, 2026-03-25)** — ✅ BEATS v5
- Architecture: Ridge L2 (C=15.0), forward-selected 32 features, isotonic calibration
- 7 new features over v5's 25: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`
- Holdout Brier: **0.1102** (+8.92% over v5)
- Holdout AUC: **0.897** (vs v5's 0.9007 — slight AUC dip, Brier is primary metric)
- Training: 1,845 events | Holdout: 358 events | Cutoff: 2025-01-01
- Elapsed: 6.6 seconds — highly efficient

> **Key insight:** Regularized Ridge with disciplined forward selection massively outperforms GPU ensemble. Less is more for tabular PDUFA data.

---

### GUNGNIR: v30.0 → v30.1 Progression

**v30.0 (First run, 2026-03-25T13:28)** — ✅ Large improvement, not final champion
- Architecture: 6-strategy GPU ensemble (LGB + XGB + CatBoost + FT-Transformer + TabNet + Ridge), temperature T=1.1, isotonic calibration
- Features: 109 (full set including journey + CTGOV + TA context)
- Holdout Brier: **0.1394** (+40.4% over v29's 0.2339)
- Holdout AUC: **0.8219** (vs v29's 0.6439 → +27.6pp AUC gain)
- Training: 1,223 events | Holdout: 548 events | CTGOV cache: NOT used

**v30.1 (Current champion)** — ✅ CHAMPION
- Architecture: Ridge(70%) + Trees(30%) blend, C=30, 26 features
- Brier: **0.1008** (56.9% improvement over v29; +27.8% improvement over v30.0)
- Key features retained: `j_last_neg` (journey last negative), `drug_last` (last outcome), `des_rct` (RCT design), `des_orr` (ORR endpoint), `orr_x_onc` (oncology×ORR interaction)

> **Key insight:** Same pattern as ODIN — ridge-dominant blend with aggressive forward selection dominates full GPU ensemble. Top signals: oncology design (des_orr, des_pfs, des_rct), modality (mod_cell_therapy, mod_antibody, mod_gene_therapy), and journey (j_last_neg, drug_last).

---

## 3. Autonomous LGB Optimizer (ODIN Model Registry)

- **Total rounds completed:** 721
- **Total champion promotions:** 8
- **Current champion:** Round 241 (2026-03-01T01:52)
  - WF-AUC: **0.8852** | WF-Brier: 0.2057 | 51 features
  - Top feature: `v1067_minus_v1070` (importance: 9,009) — ODIN score delta is most predictive
  - Runner-up: `historical_crl_rate` (8,576), `v1070_score` (6,940)
- **Rounds 242–721:** No further champion promotions. Challengers saved at rounds 279, 534, 619 but none beat round 241's WF-AUC.
- **Status:** ⚠️ PLATEAUED — optimizer has searched 480 additional rounds without improvement

> Note: LGB WF-Brier (0.2057) is not directly comparable to Ridge v6.1 holdout Brier (0.1102) — different validation schemes and splits.

---

## 4. MCP System Status

| Tool | Status | Notes |
|------|--------|-------|
| 9realms MCP (odin_score, gungnir_score, system_status) | ❌ DISABLED | Connector disabled — no live scoring this run |
| FinBrain MCP (insider_transactions, news_sentiment, analyst_ratings) | ⚠️ SCHEMA ERROR | req param requires InsiderReq model instance; JSON string rejected |
| ClinicalTrials.gov MCP | ✅ OPERATIONAL | Trial data returning successfully |

**Action required:** Re-enable 9realms MCP connector. Fix FinBrain InsiderReq schema passthrough.

---

## 5. ClinicalTrials.gov Validation

### Tirzepatide — Eli Lilly (LLY) | NCT05556512
- **Trial:** SURMOUNT-CVOT (Morbidity/Mortality in Obesity)
- **Status:** ACTIVE_NOT_RECRUITING | Phase: 3 | Enrollment: 15,374
- **Design:** Placebo-controlled RCT | **Primary Completion:** October 2027
- **Assessment:** Not imminent. Long-duration outcomes trial. If pre-readout scored, GUNGNIR features des_rct=1, large enrollment → favorable design profile. No near-term catalyst.

### Navitoclax + Ruxolitinib — AbbVie (ABBV)
- **NCT04468984** (Phase 3, R/R MF vs BAT): ACTIVE_NOT_RECRUITING, 330 enrolled, primary completion 2025-01-29
  - Primary completion has passed — likely in filing/FDA review phase. **Potential near-term PDUFA event.**
- **NCT04472598** (Phase 3, treatment-naive MF): COMPLETED April 2023, 252 enrolled
  - Completed Phase 3 supporting data package.
- **ODIN assessment (indicative, not scored live):** AbbVie = experienced sponsor, hematology-oncology TA (very high risk class), surrogate endpoint (spleen volume), Ph3 pivotal basis → likely T2–T3 range. Confirm PDUFA date assignment.

---

## 6. Insider Activity & Sentiment (VRTX, LLY, ABBV)

**Status: UNAVAILABLE** — FinBrain MCP parameter schema error blocked all three tickers. No insider alerts available this run.

---

## 7. Recommended Next Steps

**Immediate (high priority):**
1. Re-enable 9realms MCP connector to restore live drift tracking
2. Fix FinBrain MCP schema — InsiderReq dict passthrough broken
3. Confirm ABBV navitoclax PDUFA date — NCT04468984 primary completion was Jan 2025; BLA may be under review

**Model optimization (medium priority):**
4. ODIN LGB optimizer has plateaued at round 241 of 721. Consider new engineered features or widened hyperparameter search space.
5. Test CTGOV cache re-integration for GUNGNIR v30.1 — v30.0 didn't use it; adding real enrollment/masking data may push Brier below 0.10.
6. Investigate ODIN v6.1 AUC slight dip (0.9007→0.897) — test Platt scaling vs current isotonic calibration.

**Monitoring (ongoing):**
7. Track Q2 2026 PDUFA watchlist for T1 events (ODIN ≥0.85)
8. Refresh CTGOV cache entries for drugs with PDUFA dates in next 90 days

---

## 8. Summary Table

| Item | Status |
|------|--------|
| ODIN v6.1 champion confirmed | ✅ Brier 0.1102 (+8.92% vs v5) |
| GUNGNIR v30.1 champion confirmed | ✅ Brier 0.1008 (+56.9% vs v29) |
| LGB optimizer active | ⚠️ Plateaued at round 241/721 |
| Live MCP scoring (9realms) | ❌ Connector disabled |
| FinBrain signals (VRTX, LLY, ABBV) | ❌ Schema error |
| ClinicalTrials.gov validation | ✅ Operational |
| ABBV navitoclax Ph3 completed | ✅ Confirm PDUFA date |
| LLY tirzepatide SURMOUNT-CVOT | ⏳ Primary completion Oct 2027 |

---

*Report generated by automated ODIN/GUNGNIR monitoring task | 9 Realms / pdufa.bio*
*⚠️ Informational/research purposes only. Not investment advice.*
