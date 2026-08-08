# ODIN v6 / GUNGNIR v30 — Monitor Report v13
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## ⚠️ CRITICAL NEW FINDING vs v12 — LLY Orforglipron T2D PDUFA = TODAY (March 25, 2026)

**pdufa.bio** (9realms' own site) lists **LLY orforglipron for Type 2 Diabetes with PDUFA date March 25, 2026 — TODAY.** This appears to be a separate NDA from the obesity indication (PDUFA April 10, 2026). The v12 report only tracked the obesity NDA. If the T2D NDA is real and active, the FDA action window may be open right now.

**Context**:
- pdufa.bio March 2026 page (published Feb 23, 2026, post-dating the Jan 15 BioSpace extension report): `2026-03-25|LLY|Orforglipron|Type 2 Diabetes|Endocrinology|TIER_1`
- April 10, 2026 = obesity NDA PDUFA (extended by FDA from March 28 via priority voucher program)
- Lilly's own site (Oct 2025): ACHIEVE-4 T2D data expected Q1 2026; T2D NDA submission planned for 2026
- **If the T2D NDA was submitted late 2025 and received priority review, a March 25 PDUFA is feasible**

**Action required immediately**: Confirm whether orforglipron received FDA approval or CRL for T2D today. Run `odin_score` upon MCP restoration. Update pdufa.bio calendar if date has passed without action.

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | ✅ CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | −7.5% vs v5 | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | ✅ CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

**No model changes since v12.** Both deploy configs confirmed present and unmodified.

**ODIN v6.1 architecture**: Ridge C=15.0, 32 forward-selected features (v5's 25 + 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`), isotonic calibrated. Holdout AUC 0.897, trained on 1,845 events, 358-event holdout.

**GUNGNIR v30.1 architecture**: Ridge(70%)+Trees(30%) blend, 26 features including `j_last_neg`, `des_rct`, `des_orr`, `era_post24`, `drug_last`. The 56.9% Brier improvement over v29 remains the largest single-version jump in GUNGNIR history.

### Autonomous Optimizer (LGB Challenger) — Still Idle

The `models/lgb_champions/` directory shows **8 champion checkpoints spanning rounds 1–241**, last activity **2026-03-01T01:51:54** — now **24 days idle**, identical to v12. No new checkpoint files have appeared. The optimizer is terminated or stalled at round 241/721 (480 rounds remaining). The AUC improvement curve had flattened significantly between rounds 161 (0.8836) and 241 (0.8852) — a delta of only +0.0016 over 80 rounds.

**LGB Champion Ladder Summary** (from `champion_ladder.json`):

| Round | WF AUC | WF Brier | Key Eng. Features |
|-------|--------|----------|-------------------|
| 1 | 0.8514 | 0.1675 | desig_x_experienced, gene_x_cmc, is_hoeg_era |
| 5 | 0.8754 | 0.1543 | +log_crl_rate, +s23_x_s6 |
| 44 | 0.8796 | 0.1546 | +is_class1_resub, +is_ophthalmology |
| 134 | 0.8833 | 0.1886 | +is_rare_disease, +mfg_x_prior_crl |
| 161 | 0.8836 | 0.1555 | +s23_x_s6 |
| **241** | **0.8852** | 0.2057 | +btd_x_oncology, +is_oncology, +is_pain |

Top feature importances: `v1067_minus_v1070` (9,009), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091). The dominance of ODIN score differentials and CRL rate signals confirms the ensemble is anchoring on ODIN v5's core logic.

---

## 2. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| **9realms MCP** | 🔴 DISABLED | All tools disabled — `system_status`, `odin_score`, `gungnir_score` blocked. **13th consecutive failed run.** |
| **FinBrain MCP** | 🔴 BROKEN | Pydantic `InsiderReq` / `SentimentsReq` / `AnalystRatingsReq` schema still rejecting string-serialized JSON. **13th consecutive failed run.** |
| **ClinicalTrials.gov MCP** | ✅ **RESTORED** | `pagedStudies` schema error from v12 is **resolved**. Both `clinicaltrials_search_studies` queries returned valid responses. **Regression from v12 reversed.** |
| **Perplexity MCP** | ✅ OK | 3 queries executed successfully for catalyst research and insider data |

---

## 3. LLY Orforglipron — CRITICAL PDUFA UPDATE

### Two Separate Indications — Both in Active Review

| NDA | Indication | PDUFA Date | Status |
|-----|-----------|------------|--------|
| Orforglipron (T2D) | Type 2 Diabetes | **March 25, 2026 — TODAY** | Per pdufa.bio; FDA action pending |
| Orforglipron (obesity) | Overweight/Obesity | **April 10, 2026** | Extended from March 28 via priority voucher |

**T2D NDA context**: pdufa.bio lists March 25, 2026 as the PDUFA date for the T2D indication. The site was updated as of February 23, 2026 — after the BioSpace January 15 report confirming the obesity NDA extension to April 10. Lilly confirmed ACHIEVE-4 (T2D Phase 3) data expected Q1 2026, with T2D submission planned for 2026. If submitted Q4 2025 with priority review, March 25, 2026 (6-month review) is mechanistically possible.

**Obesity NDA context (confirmed)**: FDA extended review for orforglipron obesity and three other priority voucher awardees. April 10, 2026 PDUFA confirmed by Reuters (internal FDA documents). Lilly CEO David Ricks characterized review as "moving at pace" (JPM, Jan 14, 2026). Q2 2026 approval expected. Medicare obesity drug coverage begins April 2026.

### Phase 3 Program Summary (via ClinicalTrials.gov — RESTORED MCP)

| NCT ID | Trial | Status | n | Completion |
|--------|-------|--------|---|------------|
| NCT06192108 | vs Dapagliflozin (T2D) | COMPLETED | 962 | Sep 2025 |
| NCT05971940 | T2D diet/exercise | COMPLETED | 559 | Apr 2025 |
| NCT06649045 | Obesity + Sleep Apnea (Phase 3) | ACTIVE_NOT_RECRUITING | 600 | Nov 2026 |
| NCT06824051 | Obesity/overweight (Phase 1) | COMPLETED | 120 | Jan 2026 |
| NCT05882032 | Liver function PK (Phase 1) | COMPLETED | 29 | Nov 2024 |

**Total CT.gov studies for orforglipron: 46.** Phase 3 efficacy data is complete for T2D (vs dapagliflozin, n=962, completed Sep 2025) and multiple obesity trials. All supporting the NDA package.

### ODIN v5/v6.1 Feature Assessment (manual, MCP blocked)

| Feature | Value | Rationale |
|---------|-------|-----------|
| `is_nda` | 1 | NDA filing |
| `pr_bin` | 1 | Priority review (national voucher) |
| `btd_bin` | 0 | No BTD for metabolic indication |
| `prior_crl_bin` | 0 | No prior CRL |
| `sponsor_experienced` | 1 | LLY (>10 prior approvals) |
| `surrogate` | 0 | Validated endpoints (A1C, weight loss) |
| `ta_very_high` | 0 | Metabolic/endocrinology ≠ oncology/CNS tier |
| `era_post` | 1 | 2026 era |
| `had_adcom_flag` | 0 | No AdCom convened (yet) |

**Estimated ODIN tier: T1 (high probability, ≥0.85)** — experienced sponsor, priority review, no prior CRL, strong Phase 3 package, robust commercial precedent (semaglutide GLP-1 class). Score pending MCP restoration.

---

## 4. 🆕 VRTX Povetacicept — BLA Completion Imminent (CRITICAL UPDATE)

### Phase 3 RAINIER Week 36 Interim — Announced March 9, 2026

Vertex published positive Week 36 RAINIER interim data on March 9, 2026, and simultaneously confirmed **BLA completion by end of March 2026** (this week).

**Key efficacy data (pre-specified interim, n=199)**:
- Primary endpoint met: **52.0% reduction in 24-hour UPCR** from baseline; **49.8% reduction vs placebo**
- Secondary endpoints (both alpha-controlled): Gd-IgA1 reduction **79.3% vs placebo**; hematuria resolution **85.1% treated vs 23.4% placebo**
- Safety: No serious treatment-related adverse events; no deaths
- Subgroup consistency confirmed

**BLA status** (per March 9, 2026 press release):
- FDA granted rolling review of BLA
- Multiple modules already submitted during rolling review
- **Full BLA submission to be completed by end of March 2026** — TODAY or imminently
- Priority review voucher applied: 6-month review (vs 10-month standard)
- **If BLA filed by March 31, PDUFA ≈ September–October 2026**

**ClinicalTrials.gov confirmation** (via restored MCP):
- **NCT06564142**: "Evaluation of Efficacy of Povetacicept in Adults With IgAN" — ACTIVE_NOT_RECRUITING, n=605, sponsor: Alpine Immune Sciences Inc (Vertex subsidiary), primary completion Jan 30, 2028 (full 2-year eGFR endpoint). The accelerated approval pathway is based on the Week 36 surrogate data (UPCR reduction), not the Week 104 final analysis.

**ODIN v6.1 Feature Assessment for Povetacicept BLA (manual)**:

| Feature | Value | Rationale |
|---------|-------|-----------|
| `btd_bin` | 1 | BTD granted for IgAN |
| `pr_bin` | 1 | Priority review voucher applied |
| `prior_crl_bin` | 0 | No prior CRL |
| `sponsor_experienced` | 1 | VRTX (experienced: CFTR franchise) |
| `is_resub` | 0 | First submission |
| `surrogate` | 1 | Accelerated approval on UPCR (surrogate) |
| `ta_very_high` | 0 | Rare renal (IgAN) — not oncology tier |
| `had_adcom_flag` | 0 | No AdCom announced yet |
| `spa_sweet` | ? | Unknown SPA status |
| `era_post` | 1 | 2026 era |

**Estimated ODIN tier: T1 (strong long)** — BTD + priority review + experienced sponsor + positive interim + no prior CRL + accelerated approval surrogate pathway. Very high approval probability for accelerated approval. Add to scoring queue when MCP restored.

---

## 5. LLY Insider Activity — Updated (via Perplexity / SEC Form 4)

FinBrain MCP remains broken. Perplexity surfaced the following recent LLY insider activity:

**March 16, 2026 — Multiple Director Option Awards** (routine): Sulzberger (Director, 5 options @ $989.12), Luciano (Director, 16 options), Fyrwald (Director, 10 options), Alvarez (Director, 13 options). All routine director compensation, no material signal.

**February 16, 2026 — Executive Option Exercises** (pre-PDUFA): Multiple C-suite exercises at ~$1,040/share — Zakrowski (SVP Finance, 184 shares), Montarce (EVP/CFO, 368 shares), Custer (EVP/President, 207 shares), Brown (EVP, 391 shares). All exercises with concurrent tax withholding — standard RSU/option vesting events, not discretionary sales.

**Congressional Trading Activity** (Quiver Quantitative):
- Rep. David Taylor (R-OH): **Bought** Feb 26, 2026 ($1K–$15K) — bullish signal 17 days before T2D PDUFA
- Sen. Angus King (I-ME): Sold Feb 13, 2026 ($1K–$15K) — minor
- Rep. Ro Khanna (D-CA): Bought Jan 23, 2026 ($1K–$15K) — pre-PDUFA accumulation

**Net insider signal for LLY**: **Modestly bullish** — Congressional buying activity in Jan–Feb 2026 preceding the March 25 T2D PDUFA, no material C-suite discretionary selling. Executive transactions were routine vesting exercises. This is a positive pre-decision signal, though dollar amounts are small.

---

## 6. Updated Catalyst Priority Table

| Catalyst | Ticker | Type | Date | Model | Priority | Δ vs v12 |
|----------|--------|------|------|-------|----------|----------|
| Orforglipron (T2D NDA) | LLY | PDUFA | **2026-03-25 — TODAY** | ODIN | 🔴 CRITICAL — TODAY | 🆕 NEW — missed in v12 |
| Orforglipron (obesity NDA) | LLY | PDUFA | **2026-04-10** | ODIN | 🔴 CRITICAL — 16 days | Unchanged |
| Povetacicept (IgAN BLA complete) | VRTX | BLA → PDUFA | BLA ~Mar 31 → PDUFA ~Sep 2026 | ODIN | 🟠 HIGH — BLA this week | 🆕 UPDATED (March 9 RAINIER data published) |
| Orforglipron ACHIEVE-3 Phase 3 | LLY | Completed readout | Feb 26, 2026 | GUNGNIR | 🟠 HIGH — score now | Unchanged |
| Orforglipron OA knee (NCT07153471) | LLY | Phase 3 | Apr 2028 | GUNGNIR | 🟢 MONITOR | Unchanged |
| Orforglipron obesity + sleep apnea | LLY | Phase 3 | Nov 2026 | GUNGNIR | 🟢 MONITOR | 🆕 Confirmed in CT.gov |
| Inaxaplin AMKD NDA | VRTX | Phase 3 → NDA | 2026–2027 | ODIN | 🟢 MONITOR | Unchanged |
| Suzetrigine DPN Phase 3 | VRTX | Phase 3 | 2026–2027 | GUNGNIR | 🟢 MONITOR | Unchanged |

---

## 7. Recommended Next Steps

1. **IMMEDIATE — Confirm LLY orforglipron T2D PDUFA outcome** — Today is March 25, 2026, the pdufa.bio-listed PDUFA date for the T2D indication. Determine if the FDA issued an approval, CRL, or extension. Update pdufa.bio calendar and ODIN database accordingly. This is the highest-urgency single action.

2. **Score orforglipron (T2D NDA) via ODIN** — Re-enable 9realms MCP and run `odin_score` for LLY orforglipron T2D. Compare v5 production score vs v6.1 deploy config predictions. Log outcome for model validation.

3. **Score orforglipron (obesity NDA) via ODIN** — April 10, 2026 is 16 days away. Score separately under the obesity/metabolic indication context.

4. **Add povetacicept to ODIN scoring queue** — BLA completing this week. BTD + priority review + accelerated approval surrogate = strong T1 candidate. Score via `odin_score` immediately upon MCP restoration.

5. **Score ACHIEVE-3 via GUNGNIR** — Positive Phase 3 readout (Feb 26, 2026, *The Lancet*). Run `gungnir_score` to validate GUNGNIR v30.1 against a known positive outcome. Key features: `des_rct`=1, `des_primary_ep`=1, `competitive`=1 (vs semaglutide), `drug_last`=positive, `era_post24`=1.

6. **Update pdufa.bio calendar** — The March 25 T2D date needs to be confirmed and either marked as outcome-resolved or updated. The obesity date (April 10) is correct per BioSpace.

7. **Fix FinBrain MCP** — 13th consecutive failure. The fix is clear: the Pydantic `InsiderReq`, `SentimentsReq`, and `AnalystRatingsReq` models need to accept native dict input, not string-serialized JSON. Patch the MCP server or update the wrapper to deserialize before passing to Pydantic.

8. **Decide on LGB Challenger** — 24 days idle at round 241/721. AUC improvement has flattened (+0.0016 over last 80 rounds). Recommend declaring WF AUC 0.8852 as the LGB ceiling and retiring this challenger run. Start a fresh optimizer run with different feature engineering hypotheses or different architecture if further improvement is needed.

9. **Deploy ODIN v6.1 to production MCP** — The v6.1 deploy config is self-contained (Ridge C=15, 32 features, isotonic calibrated). With TWO LLY PDUFA events approaching, running production scoring on v5 is leaving performance on the table. The drop-in replacement MCP update should take <1 hour.

---

## 8. System Health

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ OK | Brier 0.1102, AUC 0.897, 32 features — unchanged |
| GUNGNIR v30.1 deploy config | ✅ OK | Brier 0.1008, 26 features — unchanged |
| LGB Challenger optimizer | ⏸️ IDLE | Round 241/721, WF AUC 0.8852, last run 2026-03-01 (24 days) — recommend retiring |
| Model registry | ✅ OK | 8 champion checkpoints (rounds 1–241) + 7-model ensemble pool |
| 9realms MCP | 🔴 DISABLED | Connector blocked — all scoring tools unavailable (13th run) |
| FinBrain MCP | 🔴 BROKEN | Pydantic schema bug — 13th consecutive failed run |
| ClinicalTrials.gov MCP | ✅ **RESTORED** | pagedStudies schema error resolved — **upgraded from 🔴 DEGRADED** |
| Perplexity MCP | ✅ OK | Functional — 3 queries executed |

---

## 9. Δ Changes vs v12

- **🔴 CRITICAL**: LLY orforglipron T2D PDUFA = March 25, 2026 (TODAY) per pdufa.bio. This is a separate NDA from the obesity indication (April 10). Missed in v12.
- **🆕 VRTX povetacicept RAINIER Week 36 results**: Announced March 9, 2026. Positive on all pre-specified endpoints. BLA completion by end of March (this week). PDUFA ~September–October 2026 with priority review voucher.
- **🆕 CT.gov data validated**: RAINIER trial confirmed (NCT06564142, n=605, ACTIVE_NOT_RECRUITING). Orforglipron Phase 3 vs dapagliflozin (n=962) confirmed COMPLETED Sep 2025. Obesity+sleep apnea Phase 3 (n=600) active.
- **🆕 LLY insider activity**: Director option awards March 16, 2026 (routine). Congressional buying in Jan–Feb 2026 pre-PDUFA (modestly bullish). No material discretionary selling.
- **✅ ClinicalTrials.gov MCP RESTORED**: Schema error from v12 resolved. Now returning valid pagedStudies results.
- **FinBrain MCP**: Still broken — 13th consecutive run.
- **9realms MCP**: Still disabled — 13th consecutive run.
- **Models**: No changes. Champions remain ODIN v6.1 / GUNGNIR v30.1.
- **Optimizer**: No new checkpoints. Still at round 241/721.

---

*Report v13 generated automatically by scheduled monitor task (2026-03-25).*

*Next run priorities: Confirm orforglipron T2D FDA outcome (TODAY), confirm povetacicept BLA filed, score both catalysts via ODIN/GUNGNIR upon MCP restoration, score orforglipron obesity NDA before April 10 PDUFA.*

*⚠️ Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
