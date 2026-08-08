# ODIN v6 / GUNGNIR v30 Monitor Report
**Run Date:** 2026-03-25 (latest automated scheduled task run)
**Task:** odin-gungnir-monitor

---

## 1. Model Champion Status

### ODIN v6.1.0 — PDUFA Approval Scoring (CHAMPION)

| Version | Brier | AUC | Features | Architecture | vs v5 Baseline |
|---------|-------|-----|----------|-------------|----------------|
| v5 (production) | 0.1210 | 0.9007 | 25 | Ridge L2 (C=1.5) | baseline |
| v6.0 (first run) | 0.1378 | 0.8590 | 65 | LGB+XGB+CatBoost+TabNet+Ridge | **–7.5% (worse)** |
| **v6.1 (champion)** | **0.1102** | **0.8970** | **32** | **Ridge (C=15.0)** | **+8.9% improvement** |

**Key insight:** The v6.0 ensemble over-parameterized with 65 features and hurt performance. v6.1 corrected this by pruning to 32 forward-selected features with a simpler Ridge architecture — confirming that regularized simplicity beats complex ensembles on this dataset size.

**7 new v6.1 features** beyond v5 base 25: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

---

### GUNGNIR v30.1.0 — Phase Readout Scoring (CHAMPION)

| Version | Brier | AUC | Features | Architecture | vs v29 Baseline |
|---------|-------|-----|----------|-------------|-----------------|
| v29 (production) | 0.2339 | 0.6439 | 82 | 6-strategy ensemble + meta-learner | baseline |
| v30.0 (first run) | 0.1394 | 0.8219 | 109 | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | +40.4% improvement |
| **v30.1 (champion)** | **0.1008** | **n/a** | **26** | **Ridge(70%)+Trees(30%) blend** | **+56.9% improvement** |

**Key insight:** Same pattern as ODIN — simpler model with fewer features dramatically outperforms the complex ensemble. 26 carefully selected features with Ridge C=30 beats 109 features.

⚠️ **LEAKAGE AUDIT RECOMMENDED**: The 56.9% Brier improvement is extraordinary. While legitimate (feature pruning + simpler model), the magnitude warrants verifying all 26 features are strictly T-1 compliant. Specifically audit journey features (`drug_last`, `j_last_neg`, `sp_sr`) for strict temporal `<` ordering.

---

## 2. LGB Autonomous Optimizer Status

- **Total rounds completed:** 721
- **Total promotions:** 8
- **Last promotion:** Round 241 (March 1, 2026)
- **Status:** ⏹️ **CONVERGED** — ~480 consecutive non-improving rounds since last promotion
- **Best WF AUC:** 0.8852 (R241) | **WF Brier:** 0.2057

**Note:** The LGB optimizer's WF Brier (0.2057) is significantly worse than ODIN v6.1's holdout Brier (0.1102). The optimizer maximized AUC at the cost of calibration. Different validation schemes (walk-forward vs. single holdout) make direct comparison imperfect, but the calibration gap is notable.

No new checkpoint files detected — most recent files dated March 1–2, 2026.

---

## 3. MCP Connector Status

| Tool | Status | Impact |
|------|--------|--------|
| 9realms `odin_score` | ❌ **DISABLED** | Cannot score catalysts against production v5 |
| 9realms `gungnir_score` | ❌ **DISABLED** | Cannot score readouts against production v29 |
| 9realms `system_status` | ❌ **DISABLED** | Cannot verify engine health |
| FinBrain (all data tools) | ❌ **PARAMETER ERROR** | Pydantic schema mismatch on `req` param |
| ClinicalTrials.gov MCP | ✅ **AVAILABLE** | Not tested this run (validated prior run) |

---

## 4. Prior Run Findings (Still Relevant)

- **CUTX-101 (FBIO)**: Confirmed APPROVED_FOR_MARKETING (2026-03-02). ODIN v5 correctly flagged as high-probability. Should be logged in outcome database.
- **VRTX VX-828**: Next-gen CFTR modulator in Phase 1 (completing April 2026). Pipeline successor to VNZ/TEZ/D-IVA.
- **LLY TRAILBLAZER-ALZ 3**: 2,996-patient P3 in preclinical AD prevention. Horizon November 2027.
- **ABBV Upadacitinib SLE**: 1,000-patient P3 recruiting. Primary completion March 2027.

---

## 5. Recommendations

| Priority | Action |
|----------|--------|
| 🔴 Critical | **Re-enable 9realms MCP connector** — all production scoring is offline, cannot compare v5/v29 production vs v6.1/v30.1 candidates |
| 🔴 Critical | **Fix FinBrain MCP schema** — insider/sentiment/analyst monitoring non-functional |
| 🟡 High | **Run leakage audit on GUNGNIR v30.1** — 56.9% improvement warrants T-1 verification on all 26 features |
| 🟡 High | **Promote ODIN v6.1 to production** — clean 8.9% Brier improvement, simpler architecture |
| 🟡 High | **Promote GUNGNIR v30.1 to production** — pending leakage audit clearance |
| 🟢 Low | **Declare LGB optimizer complete** — converged after 721 rounds with no improvement in 480+ rounds |
| 🟢 Monitor | Upcoming catalysts: VX-828 (Apr 2026), ABBV SLE P3 (Mar 2027), LLY ALZ3 (Nov 2027) |

---

## 6. Next Steps for This Monitor

On next scheduled run:
1. Re-attempt 9realms MCP scoring (if re-enabled)
2. Re-attempt FinBrain insider/sentiment queries (if schema fixed)
3. Check for any new optimizer checkpoints or deploy configs
4. Validate CTGOV cache against live API for upcoming Q2 2026 catalysts

---

*Automated monitoring report. ODIN = PDUFA events only. GUNGNIR = Phase readouts only. All content is informational/educational, not investment advice.*
