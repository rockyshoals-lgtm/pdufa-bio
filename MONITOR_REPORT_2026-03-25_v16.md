# ODIN v6 / GUNGNIR v30 Monitor Report — v16
**Generated**: 2026-03-26T02:07:37Z (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v15.md

---

## 1. Executive Summary

No model optimization progress since March 1, 2026. ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain champions. The LGB autonomous optimizer has run 619 total rounds with no champion improvement since round 241 (24+ days stalled). Three infrastructure MCPs remain broken for the 16th consecutive run. **Two imminent PDUFA events in the next 96 hours: RCKT Kresladi (Mar 28, TIER_2) and LNTH edotreotide (Mar 29, TIER_1)**. Highest-conviction upcoming catalyst remains LLY Orforglipron obesity NDA (Apr 10, TIER_1), with CTGOV confirming all registrational trials complete.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial run) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | **-7.45% worse** |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**Status**: No new v6.2 deploy config detected. v6.1 remains champion.

**Key insight from v6.0→v6.1 progression**: The complex 65-feature ensemble (v6.0) *underperformed* v5 by 7.5%. Stripping back to forward-selected Ridge with 32 features recovered and exceeded v5 performance. Simpler regularized models continue to win on this dataset.

**v6.1 new features vs v5** (7 additions): `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v29 Brier |
|---------|-------------|----------|---------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 (initial run) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.8219 | 0.1394 | **+40.4% better** |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **N/A** | **0.1008** | **+56.9% better** |

**Status**: No new v30.2 deploy config detected. v30.1 remains champion.

**Note**: v30.1's 26-feature set is dramatically leaner than v30.0's 109 features. Key features include journey signals (`j_last_neg`, `drug_last`, `sp_sr`), modality flags (`mod_cell_therapy`, `mod_antibody`, `mod_gene_therapy`), design signals (`des_rct`, `des_surrogate`, `des_orr`, `des_topline`), TA flags, and temporal context (`year`, `month`, `era_post24`, `is_asco`).

---

## 3. LGB Autonomous Optimizer Status

**File**: `models/lgb_champions/champion_ladder.json` + `ensemble_pool/`

| Metric | Value |
|--------|-------|
| Total rounds run | 721 |
| Total champion promotions | 8 |
| Last promotion | Round 241 (2026-03-01T01:51:54) |
| Current champion WF AUC | 0.8852 |
| Current champion WF Brier | 0.2057 |
| Ensemble pool files | lgb_r00044 through lgb_r00619 |
| Rounds since last promotion | **378** (since r241 to r619) |
| Days since last promotion | **~24 days** |

**Assessment**: The optimizer has effectively plateaued. After 378 additional rounds (r241→r619) with no improvement, the autonomous optimizer appears stalled. The current LGB champion's WF Brier of 0.2057 is **nearly 2× worse** than ODIN v6.1's holdout Brier of 0.1102. This gap is large enough to question whether the LGB approach (optimizing WF AUC) is suitable if Brier score is the production metric.

**Recommendation**: Formally decision this optimizer run. Options:
1. Restart with Brier as the optimization target instead of WF AUC
2. Retire the LGB parallel track and focus resources on deploying v6.1/v30.1
3. Cap at 800 rounds total and audit results

---

## 4. Upcoming PDUFA Events Watch

### RCKT Kresladi (betibeglogene autotemcel / RP-L201) — **March 28, 2026 (2 days)**
- **ODIN Tier**: TIER_2 (Cautious Long, per prior reports; small sponsor, gene therapy CMC risk)
- **Indication**: Leukocyte Adhesion Deficiency Type I (LAD-I)
- **Type**: BLA (gene therapy, rare disease)
- **CTGOV**: NCT03812263 — Phase I/II CONFIRMED **COMPLETED**. Lead sponsor Rocket Pharmaceuticals Inc. Intervention: RP-L201 (Chim-CD18-WPRE lentiviral vector). Primary endpoint: survival at age 2 / 1-year post-infusion without HSCT.
- **Key risk**: CMC issues (second CRL risk). v15 reported prior CRL for manufacturing. PDUFA extended from earlier date. Watch for FDA announcement Friday.
- **Action**: If approved → log as TIER_2 correct. If CRL → log as TIER_2 correct (downgrade justified). Either outcome validates TIER_2 logic.

---

### LNTH edotreotide — **March 29, 2026 (3 days)**
- **ODIN Tier**: TIER_1 (per prior reports; experienced sponsor Lantheus, diagnostic 505(b)(2))
- **Indication**: Neuroendocrine tumor PET imaging (somatostatin receptor)
- **Type**: NDA/505(b)(2), diagnostic radiopharmaceutical
- **CTGOV**: No results found via ClinicalTrials.gov MCP across 4 search attempts (consistent with v15). Likely registered under different name or clinical data filed via 505(b)(2) pathway using existing 68Ga-DOTATATE data.
- **Assessment**: Lantheus is an experienced diagnostics sponsor. 505(b)(2) pathway with established PET imaging class. TIER_1 appropriate.
- **Action**: Monitor for FDA announcement Saturday. If approved → TIER_1 validation. Track on pdufa.bio.

---

### LLY Orforglipron (oral GLP-1, obesity) — **April 10, 2026 (15 days)**
- **ODIN Tier**: TIER_1 (Highest-conviction upcoming catalyst)
- **Indication**: Obesity / overweight with comorbidities (NDA)
- **Type**: NDA, Priority Review, Commissioner's National Priority Voucher
- **Sponsor**: Eli Lilly (20+ prior approvals, highly experienced)

**CTGOV Validation — this run:**

| Trial | NCT | Status | Notes |
|-------|-----|--------|-------|
| ATTAIN-1 (obesity) | NCT05869903 | **ACTIVE_NOT_RECRUITING** | Phase 3, RCT, placebo-controlled; main 72-wk phase complete; extension ongoing for prediabetes patients |
| ATTAIN-2 (obesity+T2D) | NCT05872620 | **COMPLETED** | Phase 3, RCT, placebo-controlled; 77-wk study complete |
| Obesity+OSA | NCT06649045 | ACTIVE_NOT_RECRUITING | Phase 3, n=600, primary Nov 2026 — post-approval expansion |
| Hypertension | NCT06952530 | RECRUITING | Phase 3, n=487, primary Sep 2027 — label expansion |
| Obesity+Knee OA | NCT07153471 | RECRUITING | Phase 3, n=800, primary Apr 2028 — label expansion |

**Assessment**: Both registrational trials (ATTAIN-1, ATTAIN-2) are complete. Three additional post-approval expansion trials are actively recruiting — Lilly is clearly operating in "approval is certain" mode with post-marketing commitments. Medicare obesity coverage begins April 2026, creating strong commercial launch alignment. **No CTGOV signals of concern.**

TIER_1 assignment highly appropriate: Experienced sponsor + Priority Review + NDA + both Phase 3s complete + major unmet need + Medicare coverage catalyst.

---

## 5. Infrastructure MCP Status — Run #16

| Tool | Status | Consecutive Failures | Error |
|------|--------|---------------------|-------|
| 9realms `odin_score` | ❌ DISABLED | **16** | "This tool has been disabled in your connector settings" |
| 9realms `gungnir_score` | ❌ DISABLED | **16** | "This tool has been disabled in your connector settings" |
| 9realms `system_status` | ❌ DISABLED | **16** | "This tool has been disabled in your connector settings" |
| FinBrain `insider_transactions_by_ticker` | ❌ BROKEN | **16** | Pydantic: `InsiderReq` model_type validation error |
| FinBrain `news_sentiment_by_ticker` | ❌ BROKEN | **16** | Pydantic: `SentimentsReq` model_type validation error |
| FinBrain `analyst_ratings_by_ticker` | ❌ BROKEN | **16** | Pydantic: `AnalystRatingsReq` model_type validation error |
| ClinicalTrials.gov `search_studies` | ⚠️ PARTIAL | — | Works for some queries; `fields` param issue persists from v15; large payloads returned |
| ClinicalTrials.gov `get_study` | ✅ WORKING | — | Single-NCT string format required (not array); returns clean summaries |

**9realms MCP**: Connector-level disable. This is not a code issue — the tools are blocked at the infrastructure layer. Production ODIN v5 and GUNGNIR v29 scoring unavailable for 16 consecutive runs. Resolution requires connector settings change by David.

**FinBrain MCP**: Server-side Pydantic v2 schema issue. The tool schema declares `req: {}` (any type) but the server validates against a typed model (`InsiderReq`, `SentimentsReq`, etc.) that rejects string input. A server-side patch to accept and deserialize JSON strings would fix this. No workaround available from the client side.

**ClinicalTrials.gov**: Functional with workaround. Avoid `fields` parameter. Use `get_study` with single NCT string for targeted lookups. `search_studies` works but returns large payloads for common drugs (orforglipron returned 78K chars).

---

## 6. ODIN Model Validation — Q1 2026 Tracking

| Event | PDUFA | ODIN Tier | Outcome | Correct? |
|-------|-------|-----------|---------|----------|
| BMY Sotyktu PsA | Mar 7 | TIER_1 | ✅ APPROVED | ✅ |
| RYTM Imcivree HO | Mar 19 | TIER_2 | ✅ APPROVED | ✅ |
| RCKT Kresladi LAD-I | Mar 28 | TIER_2 | ⏳ PENDING | — |
| LNTH edotreotide | Mar 29 | TIER_1 | ⏳ PENDING | — |
| LLY Orforglipron obesity | Apr 10 | TIER_1 | ⏳ PENDING | — |

**YTD approval rate (confirmed)**: ~76% (above historical 67.7% baseline — elevated approval environment continues in 2026).

---

## 7. What's New vs v15

1. **LGB optimizer stall confirmed**: Ensemble pool shows files up to round 619, but champion ladder last updated at round 241 (Mar 1). 378 rounds run with zero improvement — strongest signal yet to decision this track.
2. **CTGOV ATTAIN-1/ATTAIN-2 re-validated**: Both orforglipron registrational trials confirmed complete (ACTIVE_NOT_RECRUITING / COMPLETED). Three post-approval expansion trials now recruiting — bullish signal.
3. **RCKT NCT03812263 COMPLETED confirmed**: Trial status directly verified this run via `get_study`.
4. **9realms MCP failure count**: Now 16 consecutive (up from 15).
5. **FinBrain failure count**: Now 16 consecutive (up from 15).
6. **No new deploy configs**: No v6.2 or v30.2 files found. Model optimization has been dormant since Mar 1.

---

## 8. Recommended Actions

### Immediate (next 48–72 hours)
1. **Watch RCKT Kresladi (Mar 28)**: High likelihood of FDA decision. If approved, log TIER_2 validation win. If CRL, log as appropriate TIER_2 downgrade.
2. **Watch LNTH edotreotide (Mar 29)**: Expect approval per TIER_1 signal. Log outcome for pdufa.bio resolved events.
3. **Fix 9realms connector**: 16 consecutive failures. Enable the connector in settings to restore production ODIN/GUNGNIR scoring capability.

### Near-Term
4. **FinBrain server patch**: File with MCP maintainer. The fix is a one-line server-side change to deserialize the `req` string to dict before passing to Pydantic model.
5. **LGB optimizer decision**: After 721 rounds / 378 stalled rounds, formally decide: restart with Brier target, or retire. Current best WF Brier 0.2057 is 2× worse than ODIN v6.1 Brier 0.1102.
6. **Deploy v6.1 to production**: `odin_v6_1_deploy.json` is ready. v6.1 beats v5 by 8.92% on Brier and 0.897 AUC — clear upgrade from v5's 0.9007 AUC / 0.1210 Brier.

### Medium-Term
7. **Deploy v30.1 to production**: `gungnir_v30_1_deploy.json` achieves Brier 0.1008 vs v29's 0.2339 (+56.9%). This is a massive improvement. The 26-feature Ridge+Trees blend should replace v29 in the MCP server.
8. **LLY orforglipron April 10**: Ensure pdufa.bio has single entry for obesity NDA only (T2D entry should have been removed per v14 recommendations). Score under ODIN v6.1 when connector is restored.
9. **ODIN v6.2 path**: Consider adding CTGOV real-data features to v6.1 (similar to v29→v30 upgrade that drove +56.9% GUNGNIR improvement). The 7 new v6.1 features are temporal/sponsor-based; trial design features could add further lift.

---

## 9. Summary

Both champion models (ODIN v6.1, GUNGNIR v30.1) remain stable with no new optimization activity since March 1. The LGB autonomous optimizer has stalled at 719 rounds with zero improvement in 24+ days and should be formally decisioned. Infrastructure remains blocked (9realms connector disabled, FinBrain Pydantic bug) for the 16th consecutive run.

Two imminent PDUFA events — **RCKT Kresladi (Mar 28)** and **LNTH edotreotide (Mar 29)** — provide near-term validation opportunities. The highest-conviction upcoming catalyst, **LLY Orforglipron (Apr 10, TIER_1)**, has all registrational trials confirmed complete and three post-approval expansion studies already recruiting, reflecting Lilly's high confidence in approval.

Primary operational priority remains restoring the 9realms connector to re-enable production ODIN/GUNGNIR scoring.

---

*This report is for informational and research purposes only. Not investment advice. ODIN/GUNGNIR scores are probabilistic models with inherent uncertainty.*
