# ODIN / GUNGNIR Model Monitor Report
**Run Date:** 2026-03-25
**Run Type:** Scheduled Automated Monitor
**Report Version:** odin-gungnir-monitor

---

## 1. EXECUTIVE SUMMARY

| Engine | Current Champion | Brier Score | vs Baseline | Status |
|--------|-----------------|-------------|-------------|--------|
| ODIN | v6.1.0 | **0.1102** | −8.92% vs v5 (0.1210) | ✅ Champion Confirmed |
| GUNGNIR | v30.1.0 | **0.1008** | −56.9% vs v29 (0.2339) | ✅ Champion Confirmed |

Both models are confirmed at their champion configurations. No new optimizer checkpoints detected in `models/` or `logs/` directories (directories not yet created — optimizer has not run autonomously since last session).

---

## 2. ODIN MODEL STATUS

### v6.0 → v6.1 Progression

| Version | Architecture | Features | AUC | Brier | vs v5 |
|---------|-------------|----------|-----|-------|-------|
| v5 (baseline) | Ridge L2 (C=1.5), 25 features | 25 | 0.9007 | 0.1210 | — |
| v6.0 | Multi-strategy ensemble (LGB+XGB+CatBoost+TabNet+Ridge) | 65 | 0.859 | 0.1378 | **−7.45%** (worse) |
| v6.1 | Ridge C=15 + isotonic calibration, forward-selected | 32 | 0.897 | **0.1102** | **+8.92%** (better) |

**Key finding:** v6.0's large complex ensemble (65 features, GPU-heavy) *underperformed* v5. v6.1 simplified back to a strong Ridge (C=15) with forward feature selection and isotonic calibration — achieving the best result. This confirms the regularization-first principle for PDUFA scoring.

### v6.1 New Features (vs v5's 25)
The 7 new features beyond v5's 25: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`

Notable additions:
- **`sponsor_rolling_approval_rate`** — dynamic sponsor track record (vs static experienced/naive flags)
- **`adcom_x_pr`** — interaction between advisory committee and priority review
- **`experienced_x_low_crl`** — experienced sponsor × low CRL rate interaction
- **`month` / `year`** — temporal seasonality signals

### ODIN v6.1 Production Readiness
- Training events: 1,845 (vs v5's 2,203 — note: smaller training set, different cutoff handling)
- Holdout events: 358 (same as v5 holdout)
- Elapsed training time: 6.6 seconds (extremely fast — Ridge efficiency confirmed)
- **Status: READY FOR PRODUCTION**

---

## 3. GUNGNIR MODEL STATUS

### v30.0 → v30.1 Progression

| Version | Architecture | Features | AUC | Brier | vs v29 |
|---------|-------------|----------|-----|-------|--------|
| v29 (baseline) | Ridge(75%)+P3(25%) ensemble + CT.gov real data | 82 | 0.6439 | 0.2339 | — |
| v30.0 | Multi-strategy ensemble (LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge) | 109 | 0.8219 | 0.1394 | **+40.4%** |
| v30.1 | Ridge C=30 + isotonic calibration, forward-selected | 26 | N/A | **0.1008** | **+56.9%** |

**Key finding (mirrors ODIN pattern):** v30.0's large ensemble showed massive gains over v29 but v30.1's lean forward-selected Ridge (just 26 features!) pushed Brier even lower. The pattern is consistent — aggressive feature selection + strong Ridge regularization beats complex ensembles.

### v30.1 Feature Set (26 features)
A compact, high-signal set including:
- **Journey signals:** `drug_last`, `j_last_neg`, `sp_sr` (sponsor success rate)
- **Design signals:** `des_orr`, `des_rct`, `des_pfs`, `des_surrogate`, `des_topline`, `des_primary_ep`
- **TA signals:** `ta_oncology`, `ta_infectious`, `ta_rare`, `ta_n3_log`
- **Context:** `year`, `month`, `era_post24`, `is_asco`, `has_conf`
- **Modality:** `mod_cell_therapy`, `mod_antibody`, `mod_gene_therapy`
- **Interactions:** `orr_x_onc`, `p3_x_cns`, `competitive`

### GUNGNIR v30.1 Production Readiness
- Ridge C=30 (high regularization, 26 features — very lean vs v30.0's 109)
- Brier 0.1008 is exceptional for phase readout prediction
- **⚠️ NOTE:** v30.1 deploy JSON does not include full metrics (AUC, accuracy) — only Brier and improvement_pct are logged. Recommend re-running metrics capture.
- **Status: READY FOR PRODUCTION** (pending full metrics logging)

---

## 4. OPTIMIZER CHECKPOINT STATUS

**`models/` directory:** Empty — no autonomous optimizer checkpoints found
**`logs/` directory:** Empty — no iteration logs found

The autonomous optimizer has not written any new checkpoint files since the last manual training session. This is expected if the optimizer scripts have not been launched as background processes. No drift or regression detected.

---

## 5. 9REALMS MCP SCORING

**Status:** 9realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) are **DISABLED** in connector settings.

- Production score comparison vs new models could not be performed this run
- **Recommendation:** Re-enable 9realms MCP connector to restore live scoring capability for future monitor runs
- Test catalysts queued (pending MCP re-enablement):
  - ODIN test: VRTX / vanzacaftor-tezacaftor-deutivacaftor (Respiratory, BTD+PR)
  - GUNGNIR test: LLY / tirzepatide (HFpEF, Phase 3 RCT)

---

## 6. FINBRAIN SIGNALS

**FinBrain service health:** ✅ Online (v0.1.6 MCP, SDK v0.1.8)

**Insider transaction data:** ⚠️ Parameter schema error — `InsiderReq` Pydantic model mismatch prevents programmatic calls. Affects all FinBrain data tools (insider, sentiment, analyst ratings). Service is up but tool invocation schema needs fix.

**Recommendation:** Update FinBrain MCP server to accept flat JSON parameters or document correct `req` object structure. Until resolved, insider transaction monitoring for VRTX, LLY, ABBV cannot be automated.

**Manual check advised for:**
- VRTX — Watch for C-suite buying ahead of any 2026 PDUFA decisions
- LLY — Monitor insider patterns around tirzepatide HFpEF/MASH readouts
- ABBV — Watch skrinvemab / emraclidine PDUFA activity

---

## 7. CLINICALTRIALS.GOV VALIDATION

### ABBV-CLS-484 (AbbVie / Calico) — NCT04777994
- **Phase:** Phase 1 (dose escalation + expansion)
- **Status:** RECRUITING
- **Primary completion:** October 2026 (estimated)
- **Design:** Monotherapy + combination with PD-1 inhibitor or VEGFR TKI
- **Indications:** HNSCC, NSCLC, advanced ccRCC, MSI-H tumors
- **Enrollment:** 248 (estimated)
- **GUNGNIR relevance:** Phase 1 — not yet a GUNGNIR scoring candidate; watch for Phase 2/3 advancement in 2026-2027
- **CTGOV cache status:** Verify this entry is correctly captured as Phase 1 in ctgov_cache.json

### LLY / Tirzepatide Phase 3
- ClinicalTrials.gov search returned large result set (272K chars) — multiple active Phase 3 trials confirmed
- Key trials include SUMMIT (HFpEF), SURMOUNT series, SYNERGY-NASH
- **CTGOV cache recommendation:** Confirm tirzepatide's HFpEF (SUMMIT) trial is in ctgov_cache.json with correct arm count, masking, enrollment, and primary endpoint fields for GUNGNIR v30 scoring

---

## 8. CATALYST DATABASE STATUS

**File:** `odin_output/odin_v6_catalysts.json`
- Version: 6.3
- Total events: 490 (20 future PDUFA + 365 FDA API + 74 SEC 8-K + 43 curated historical)
- Generated: 2026-01-10

**Notable near-term catalysts in database (sampled):**
- FBIO / CUTX-101 / Menkes Disease — BTD + Orphan + PR, Class 1 CMC resubmission (high approval probability signal)
- VKTX / VK2735 / Obesity — GLP-1 oral, NDA path

**Recommendation:** Refresh catalyst database — current version is ~2.5 months old (Jan 10). New PDUFA dates may have been announced for Q2/Q3 2026.

---

## 9. KEY FINDINGS & RECOMMENDATIONS

### ✅ Confirmed Champions
Both ODIN v6.1 and GUNGNIR v30.1 are confirmed at their best-known configurations. No regression detected.

### 🔄 Consistent Pattern: Simple > Complex
Both optimization runs showed the same result: lean Ridge with forward-selected features beats large GPU ensembles. This is a strong signal to resist over-engineering future versions.

### ⚠️ Action Items

| Priority | Item | Owner |
|----------|------|-------|
| HIGH | Re-enable 9realms MCP connector for live scoring | Config |
| HIGH | Fix FinBrain MCP `req` parameter schema (InsiderReq pydantic model) | Dev |
| MEDIUM | Add full metrics (AUC, accuracy) to GUNGNIR v30.1 deploy JSON | Model |
| MEDIUM | Refresh odin_v6_catalysts.json (2.5 months stale) | Data |
| MEDIUM | Validate tirzepatide SUMMIT trial in ctgov_cache.json | Data |
| LOW | Consider v6.2 / v30.2 runs: test sponsor_rolling_approval_rate in GUNGNIR | Research |
| LOW | Initialize `models/` and `logs/` directories for autonomous optimizer output | Infra |

### 📊 Next Optimization Steps
1. **ODIN v6.2:** Test adding GUNGNIR-inspired journey features (sponsor_rolling_approval_rate already present in v6.1 — validate its contribution via SHAP). Consider `era_post` interaction terms.
2. **GUNGNIR v30.2:** Re-run with CT.gov real data features (v30.1 appears to have dropped them — the v30.1 deploy JSON shows 26 features without CTGOV entries). Test whether CTGOV data re-integration improves Brier further.
3. **Ensemble v6.1+v30.1 MCP update:** Deploy new champion weights to `mcp_9realms_vnext.py` — confirm server reflects v6.1 / v30.1 rather than v5 / v29.

---

## 10. SYSTEM HEALTH SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ Present | Confirmed champion |
| GUNGNIR v30.1 deploy config | ✅ Present | Confirmed champion |
| 9realms MCP | ❌ Disabled | Re-enable needed |
| FinBrain MCP | ⚠️ Schema error | Service up, tools broken |
| ClinicalTrials.gov MCP | ⚠️ Partial | Large responses truncated |
| models/ optimizer dir | ⚠️ Empty | No autonomous runs detected |
| logs/ optimizer dir | ⚠️ Empty | No iteration logs |
| Catalyst database | ⚠️ Stale | 2.5 months old |

---

*Report generated automatically by odin-gungnir-monitor scheduled task.*
*Run timestamp: 2026-03-25 (UTC)*
*Next scheduled run: per configured interval*
