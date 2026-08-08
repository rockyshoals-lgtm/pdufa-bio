# ODIN / GUNGNIR Monitor Report
**Run date:** 2026-03-25
**Task:** odin-gungnir-monitor (automated scheduled run)
**Status:** ⚠️ Partial — 9realms MCP scoring tools disabled; FinBrain connector serialization issue; ClinicalTrials.gov data retrieved

---

## 1. Deploy Config Status

### ODIN

| Version | Brier | AUC | Features | Architecture | vs v5 Baseline |
|---------|-------|-----|----------|--------------|----------------|
| **v6.1 (CHAMPION)** | **0.1102** | **0.897** | **32** | **Ridge C=15, forward-selected, isotonic calibrated** | **+8.92% ✅** |
| v6.0 | 0.1378 | 0.859 | 65 | Multi-strategy GPU ensemble (LGB+XGB+CatBoost+TabNet+Ridge) | -7.45% ❌ |
| v5 baseline | 0.1210 | 0.9007 | 25 | Ridge L2 C=1.5 | — |

**Key finding:** ODIN v6.1 is the confirmed champion. The massive GPU ensemble in v6.0 *hurt* performance (−7.45% Brier, −1.45% AUC) — likely overfitting on 65 features with a 1,845-event training set. v6.1's return to a simpler 32-feature Ridge C=15 with forward selection and isotonic calibration recovered the gain. **7 new features beyond v5's 25** were retained by forward selection: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

---

### GUNGNIR

| Version | Brier | AUC | Features | Architecture | vs v29 Baseline |
|---------|-------|-----|----------|--------------|-----------------|
| **v30.1 (CHAMPION)** | **0.1008** | N/A | **26** | **Ridge C=30, forward-selected** | **+56.9% ✅** |
| v30.0 | 0.1394 | 0.8219 | 109 | Multi-strategy GPU ensemble (LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge) | +40.4% ✅ |
| v29 baseline | 0.2339 | 0.6439 | 82 | Ridge+Trees ensemble, CTGOV real data | — |

**Key finding:** GUNGNIR v30.1 is a generational improvement. Like ODIN, the v30.0 GPU ensemble was a useful step but v30.1's stripped-down 26-feature forward-selected Ridge C=30 pushed Brier from 0.1394 → 0.1008, a **56.9% Brier improvement** over v29. The 26 retained features lean heavily on journey signals (`drug_last`, `j_last_neg`, `sp_sr`), trial design (`des_rct`, `des_surrogate`, `des_orr`), and modality (`mod_cell_therapy`, `mod_antibody`, `mod_gene_therapy`).

---

## 2. LGB Autonomous Optimizer (models/lgb_champions/)

A separate autonomous LGB optimizer has been running and produced **721 rounds** with **8 champion promotions**. Current champion (round 241, timestamp 2026-03-01):

- **WF AUC: 0.8852** (up from 0.8514 at round 1)
- **WF Brier: 0.2057** (note: higher Brier than v6.1's 0.1102 — different metric regime / dataset)
- **51 features**, including 16 engineered features: `btd_x_oncology`, `v1067_minus_v1070`, `v1070_x_social`, `log_crl_rate`, `desig_x_experienced`, `single_arm_x_safety`, `orphan_x_surrogate`, `prior_crl_x_base_rate`
- ⚠️ **`wf_t4p = 0.0` at round 241** — T4 purity has collapsed entirely

**Assessment:** The LGB optimizer's WF AUC trajectory is solid (+3.4pp over 241 rounds), but Brier is worse than v6.1 Ridge and T4 purity of 0.0 is disqualifying for production use. This track would benefit from adding a Brier or T4-purity term to the champion promotion criterion.

**Model Registry v2.20260228** also found in `models/model_registry/`. Contains social sentiment/overlay weights: `quiet_review_boost` (+0.239), `ix_prior_crl_x_quiet_review` (+0.358), `endpoint_change_penalty` (−0.224), `pi_bad_history_penalty` (−0.332), `ceo_tone_bullish_boost` (+0.166). This appears to be an NLP/social signal overlay layer.

---

## 3. 9realms MCP Scoring — DISABLED ❌

**Status: Tools disabled in connector settings**

The `odin_score`, `gungnir_score`, and `system_status` tools are currently disabled. Production drift checks against known benchmarks could not be performed this run.

Attempted benchmark calls (blocked):
- ODIN: VRTX / vanzacaftor-tezacaftor-deutivacaftor / respiratory / PDUFA 2026-01-17 (known T1 event)
- GUNGNIR: LLY / tirzepatide / HFpEF Phase 3 SUMMIT

**Recommended action:** Re-enable 9realms MCP tools in connector settings to restore live production scoring checks on future runs.

---

## 4. FinBrain MCP — Health OK, Data Tools Broken ⚠️

- **Server health:** ✅ OK (mcp v0.1.6, SDK v0.1.8)
- **Insider / sentiment / analyst tools:** ❌ Serialization error

The connector bridge is serializing the `req` parameter as a JSON string rather than passing it as a native Python dict. All three data tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker`) fail with: `Input should be a valid dictionary or instance of [Model]Req [input_type=str]`.

No insider transaction or sentiment data was retrievable for VRTX, LLY, or ABBV this run.

**Recommended action:** Update the FinBrain MCP connector to accept and deserialize string-encoded JSON for `req`, or fix the bridge serialization layer to pass native dict objects.

---

## 5. ClinicalTrials.gov — Data Retrieved ✅

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (VNZ/TEZ/D-IVA)

| NCT | Status | Phase | Enrollment | Notes |
|-----|--------|-------|------------|-------|
| NCT05844449 | ENROLLING_BY_INVITATION | Phase 3 | 174 | Long-term safety/efficacy, age 1+. Post-approval extension. |
| NCT06154447 | RECRUITING | Phase 1 | 255 | VX-828 next-gen CF modulator. |
| NCT07349394 | ACTIVE_NOT_RECRUITING | Phase 1 | 18 | PK drug interaction (rosuvastatin). |

**Assessment:** VNZ/TEZ/D-IVA is in long-term follow-up (no near-term binary catalyst). Next-gen CF modulator VX-828 is in Phase 1 recruiting — pipeline development to monitor. VRTX is in a post-catalyst holding pattern on this asset.

---

### LLY — Tirzepatide

| NCT | Status | Phase | Enrollment | Notes |
|-----|--------|-------|------------|-------|
| NCT04847557 (SUMMIT) | **COMPLETED** | Phase 3 | 731 | HFpEF + obesity. Primary endpoint met. |
| NCT05556512 (SURMOUNT-5) | ACTIVE_NOT_RECRUITING | Phase 3 | **15,374** | Morbidity/mortality in obesity. Long-term CV outcomes. |

**Assessment:** SUMMIT (HFpEF) completed positive. SURMOUNT-5 is one of the largest active Phase 3 trials in the monitored universe at 15,374 enrolled. This morbidity/mortality readout is a major upcoming LLY catalyst — GUNGNIR v30.1 would score this favorably given RCT design, large enrollment, positive drug journey streak, experienced sponsor.

---

### ABBV — Navitoclax

| NCT | Status | Phase | Enrollment | Notes |
|-----|--------|-------|------------|-------|
| NCT04468984 | ACTIVE_NOT_RECRUITING | Phase 3 | 330 | Navitoclax + ruxolitinib vs BAT in R/R myelofibrosis. |

**Assessment:** AbbVie's navitoclax Phase 3 in myelofibrosis is enrolled and not recruiting — readout window is approaching (likely Q2–Q3 2026). BCL-2 inhibition in ruxolitinib-resistant MF is differentiated, but the competitive landscape is a GUNGNIR risk factor. Flag for active monitoring.

---

## 6. Upcoming PDUFA Events (from odin_v6_catalysts.json snapshot)

From the 490-event curated database (note: mined 2026-01-10, may not reflect Q1 2026 new filings):

| Ticker | Asset | Indication | PDUFA Date | BTD | Orphan | PR | Notes |
|--------|-------|------------|------------|-----|--------|-----|-------|
| FBIO | CUTX-101 | Menkes Disease | 2025-01-14 | ✅ | ✅ | ✅ | Class 1 CMC resubmission |
| VKTX | VK2735 | Obesity | 2025-01-27 | ❌ | ❌ | ❌ | GLP-1 oral NDA |
| AQST | Anaphylm | Anaphylaxis | 2025-01-31 | ❌ | ❌ | ❌ | Sublingual epinephrine |
| BMRN | Voxzogo | Hypochondroplasia | 2025-02-16 | ❌ | ✅ | ❌ | sNDA expansion |
| VALN | VLA15 | Lyme Disease Vaccine | 2026-02-28 | ❌ | ❌ | ❌ | BLA, Pfizer partnership |

*These dates are from the curated calendar; 2025-dated entries are historical. Calendar refresh needed for current 2026 events.*

---

## 7. Recommended Next Steps

### Immediate (High Priority)
1. **Re-enable 9realms MCP tools** — Production drift checks are fully blocked. Highest priority fix.
2. **Fix FinBrain connector serialization** — `req` parameter bug prevents insider/sentiment enrichment for all three data tools.

### Model Development
3. **LGB optimizer T4 purity** — Round 241 champion has `wf_t4p = 0.0`. Add Brier or T4 purity as a secondary champion criterion to prevent T4 collapse.
4. **GUNGNIR v30.1 + CTGOV** — v30.0 config shows `ctgov_cache_used: false`. The real CTGOV trial design features that boosted v29 are absent in v30.1. A v30.2 pass adding CTGOV features to the 26-feature forward-selected base could push Brier below 0.1008.
5. **Social overlay integration** — Consider integrating v2.20260228 social/CEO tone signals as candidate features in ODIN v6.2 forward selection pass.

### Data / Pipeline
6. **Refresh PDUFA calendar** — `odin_future_catalysts_2026.json` last mined 2026-01-10. ~75 days of new filings may be missing. Trigger a re-mine.
7. **Flag SURMOUNT-5 (LLY)** — NCT05556512, 15,374 enrolled tirzepatide morbidity/mortality trial, active and nearing primary completion. Add to GUNGNIR watch list.
8. **Flag ABBV navitoclax readout** — NCT04468984, 330 enrolled, ACTIVE_NOT_RECRUITING. Readout likely Q2–Q3 2026. Score with GUNGNIR v30.1.

---

## Summary Scorecard

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ Confirmed | Brier 0.1102, +8.92% vs v5 |
| GUNGNIR v30.1 deploy config | ✅ Confirmed | Brier 0.1008, +56.9% vs v29 |
| LGB optimizer checkpoints | ✅ Found | 721 rounds, AUC 0.8852; T4 purity issue |
| 9realms MCP live scoring | ❌ Disabled | Re-enable connector |
| FinBrain insider/sentiment | ❌ Broken | `req` serialization bug |
| ClinicalTrials.gov | ✅ Retrieved | VRTX, LLY, ABBV trial data current |
| PDUFA calendar currency | ⚠️ Stale | Last mined 2026-01-10, refresh needed |

---

*Informational/educational only — not investment advice.*
*Generated: 2026-03-25 | ODIN v6.1 champion | GUNGNIR v30.1 champion*
