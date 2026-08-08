# ODIN v6 / GUNGNIR v30 Optimization Monitor Report

**Date:** 2026-03-25 | **Run:** v7 (Scheduled)

---

## 1. Champion Model Status

### ODIN v6.1.0 — PDUFA Scoring (CHAMPION)
| Metric | v5 Baseline | v6.0 | v6.1 (Champion) |
|--------|-------------|------|------------------|
| **Brier** | 0.1210 | 0.1378 | **0.1102** |
| **AUC** | 0.9007 | 0.859 | 0.897 |
| **Improvement** | — | -7.5% (regression) | **+8.9%** |
| **Features** | 25 | 65 | 32 |
| **Architecture** | Ridge L2 C=1.5 | Multi-ensemble (LGB+XGB+CatBoost+TabNet+Ridge) | Ridge C=15.0, isotonic calibrated |

**Key Observations:**
- v6.1 confirmed as champion. The simpler Ridge C=15 with 32 forward-selected features dramatically outperforms the bloated v6.0 ensemble (65 features).
- v6.0 was a regression vs v5 (Brier 0.1378 vs 0.1210), proving that adding GPU-heavy ensembles and 40+ extra features hurt generalization.
- v6.1 recovered by returning to Ridge architecture with moderate regularization (C=15 vs v5's C=1.5) and adding only 7 net new features (year, sponsor_rolling_approval_rate, adcom_x_pr, sponsor_volume_log, month, experienced_x_low_crl, spa_mid).
- All 25 original v5 features retained, confirming their durability.

### GUNGNIR v30.1.0 — Phase Readout Scoring (CHAMPION)
| Metric | v29 Baseline | v30.0 | v30.1 (Champion) |
|--------|-------------|-------|------------------|
| **Brier** | 0.2339 | 0.1394 | **0.1008** |
| **AUC** | 0.6439 | 0.8219 | N/A (not in config) |
| **Improvement** | — | +40.4% | **+56.9%** |
| **Features** | 82 | 109 | 26 |
| **Architecture** | 6-strategy ensemble + meta-learner | Multi-ensemble (LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge) | Ridge(70%)+Trees(30%) blend |

**Key Observations:**
- v30.1 is a massive improvement — Brier 0.1008 is world-class calibration for phase readout prediction.
- Same pattern as ODIN: the simpler model (26 features, Ridge+Trees blend) crushes the bloated v30.0 (109 features, 6 GPU models).
- Feature reduction from 109 → 26 suggests aggressive forward selection eliminated noise.
- Notable v30.1 features: drug_last (journey), sp_sr (sponsor success rate), j_last_neg (journey last negative), competitive, era_post24, design features (des_rct, des_pfs, des_orr, des_surrogate, des_topline).

---

## 2. Model Checkpoint Registry

**Location:** `/9realms/models/`

| File | Date | Notes |
|------|------|-------|
| champion_r00241_af6a433fc23e.pkl | Mar 1 | Latest champion (23.9 MB) — matches CURRENT_BEST.pkl |
| champion_r00161_d34def3a6738.pkl | Mar 1 | 596 KB |
| champion_r00134_13aae0970a87.pkl | Mar 1 | 6.6 MB |
| champion_r00044_36973fd30b5b.pkl | Feb 28 | 1.2 MB |
| champion_r00005_34040a0c44cc.pkl | Feb 28 | 382 KB |
| champion_r00001–r00003 | Feb 28 | Early iterations |
| LGB champion v2 | Feb 28 | lgb_champions/v2.20260228.pkl |

- **241 optimizer rounds** completed as of last run.
- No new checkpoints since March 2 (champion_ladder.json last modified Mar 2).
- Optimizer appears **idle** — no new iterations detected.

---

## 3. 9realms MCP Status

**Status: DISABLED** — All three tools (odin_score, gungnir_score, system_status) returned "This tool has been disabled in your connector settings."

- Cannot run production v5 scoring comparisons this cycle.
- **Action needed:** Re-enable 9realms MCP connector to resume live scoring checks.

---

## 4. FinBrain MCP Status

**Status: PARAMETER ERROR** — All FinBrain tools (insider_transactions, news_sentiment, analyst_ratings) returned Pydantic validation errors. The `req` parameter requires a dict/model instance but receives a string.

- Cannot pull insider trading data for VRTX, LLY, ABBV this cycle.
- **Action needed:** Investigate FinBrain MCP connector parameter serialization issue.

---

## 5. ClinicalTrials.gov — Orforglipron (LLY) Trial Data

Successfully retrieved live trial data for LLY's orforglipron (oral GLP-1):

| NCT ID | Title | Status | Enrollment | Completion |
|--------|-------|--------|------------|------------|
| NCT05869903 | Orforglipron in obesity/overweight with comorbidities | **ACTIVE_NOT_RECRUITING** | 3,127 | Jul 2025 |
| NCT05872620 | Orforglipron in obesity/overweight + T2D | **COMPLETED** | 1,613 | Aug 2025 |
| NCT06109311 | Orforglipron in T2D + insulin glargine | **COMPLETED** | 546 | Sep 2025 |
| NCT07153471 | Orforglipron in obesity/overweight + knee OA | **RECRUITING** | 800 | Apr 2028 |
| NCT05313802 | LY3502970 in healthy overweight/obese (early phase) | **COMPLETED** | 72 | Sep 2022 |

**Key signals for GUNGNIR enrichment:**
- The pivotal ACHIEVE trial (NCT05869903) enrolled 3,127 patients — large, well-powered RCT.
- Two completed trials with readouts already available (T2D + obesity).
- New OA expansion trial recruiting (800 pts, 2028 completion).
- CTGOV real data: RCT design, large enrollment, multiple completed studies = positive design signals.

---

## 6. Summary & Recommendations

### Current Champion Scores
| Model | Brier Score | vs Baseline | Status |
|-------|------------|-------------|--------|
| **ODIN v6.1** | 0.1102 | +8.9% vs v5 (0.1210) | Stable champion |
| **GUNGNIR v30.1** | 0.1008 | +56.9% vs v29 (0.2339) | Stable champion |

### Key Finding
Both models converged to the same architectural lesson: **simpler is better**. Ridge-based models with aggressive feature selection (25–32 features) consistently beat complex GPU ensembles with 65–109 features. This validates the bias-variance tradeoff on these dataset sizes (~1,800–2,000 events).

### Recommended Next Steps

1. **Re-enable 9realms MCP** — Production scoring comparison is blocked. Need to verify v5 production scores against v6.1 predictions on the same catalysts.

2. **Fix FinBrain MCP parameter format** — The `req` parameter serialization is broken. Once fixed, can pull insider trading signals for ODIN T1 catalysts.

3. **Update CLAUDE.md** — Current CLAUDE.md still references ODIN v5 and GUNGNIR v29 as champions. Should be updated to reflect:
   - ODIN v6.1 (Brier 0.1102, Ridge C=15, 32 features)
   - GUNGNIR v30.1 (Brier 0.1008, Ridge+Trees blend, 26 features)

4. **Deploy v6.1 + v30.1 to MCP server** — Replace v5/v29 weights in `mcp_9realms_vnext.py` with the new champions once validated.

5. **Investigate optimizer stall** — No new checkpoints since Mar 2 (23 days ago). Either the optimizer converged or the process died. Check if further iterations would help.

6. **CTGOV cache refresh** — Enrich upcoming 2026 catalysts with fresh ClinicalTrials.gov data. The orforglipron data shows the API is working and returning rich trial design features.

---

*Disclaimer: All model outputs are informational/educational only and do not constitute investment advice.*
*Report generated automatically by ODIN/GUNGNIR monitoring task.*
