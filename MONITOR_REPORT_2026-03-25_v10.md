# ODIN v6 / GUNGNIR v30 — Monitor Report v10
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | ✅ CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | -7.5% vs v5 (worse) | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | ✅ CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

### Key Observations — No Changes Since v9

Champions remain **ODIN v6.1.0** (Brier 0.1102) and **GUNGNIR v30.1.0** (Brier 0.1008). No new deploy configs or model checkpoints detected since last run. Both deploy configs confirmed present and valid.

**ODIN v6.1 architecture**: Ridge C=15.0, 32 forward-selected features, isotonic calibrated. 7 new features beyond v5 baseline: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Holdout AUC 0.897, trained on 1,845 events with 358-event holdout.

**GUNGNIR v30.1 architecture**: Ridge(70%)+Trees(30%) blend, 26 features. Interpretable feature set spanning drug journey signals, trial design markers, therapeutic area, and modality. The 56.9% Brier improvement over v29 remains the largest single-version jump in GUNGNIR history.

### Autonomous Optimizer (LGB Challenger) — Still Idle

The `models/lgb_champions/` directory contains 8 champion checkpoints spanning rounds 1–241 out of 721 total optimization rounds. The current champion (round 241, `af6a433fc23e`) achieved WF AUC **0.8852**, Brier **0.2057** using a 51-feature LightGBM ensemble. Last activity timestamped **2026-03-01T01:51:54**. No new checkpoints since v9.

**LGB Challenger champion features of note**: `v1067_minus_v1070` (importance 9,009), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091). The ODIN v1067/v1070 ensemble differential is the strongest signal, consistent with v6's `sponsor_rolling_approval_rate` and multi-model ensemble findings. The optimizer appears **idle** — no further runs detected.

---

## 2. Production MCP Scoring — DISABLED (Unchanged)

The 9realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) remain **disabled in connector settings**. All three calls return `"This tool has been disabled in your connector settings."` Production v5/v29 scores cannot be compared against v6.1/v30.1 predictions until the connector is re-enabled.

**Action Required**: Re-enable 9realms MCP connector to resume production scoring and drift monitoring.

---

## 3. FinBrain MCP — PARAMETER INCOMPATIBILITY (Unchanged)

FinBrain MCP `req` parameter continues to fail validation (`Input should be a valid dictionary or instance of InsiderReq/SentimentsReq/AnalystRatingsReq`). The MCP server expects a Pydantic model instance that cannot be constructed through the tool call interface. Both string-serialized JSON and JSON object forms were attempted — both failed.

**Deferred checks (blocked)**:
- VRTX insider transactions — PDUFA **2026-03-28** (3 days out, critical timing)
- LLY news sentiment — orforglipron and tirzepatide pipeline catalysts
- ABBV analyst ratings — sabizabulin and other upcoming events

**Action Required**: FinBrain MCP connector needs schema update to accept plain JSON objects, or a wrapper function needs to be added upstream.

---

## 4. ClinicalTrials.gov Validation — New Data This Run

### 4a. Vertex Pharmaceuticals — Suzetrigine (Pain)

Three Phase 3 trials found. Key new finding this run: **NCT07231419** is a newly registered efficacy trial for diabetic peripheral neuropathy (DPN), recruiting as of this run, expected primary completion April 2027. This is incremental to the DPN program and not yet in the CTGOV cache.

| NCT ID | Indication | Enrollment | Design | Status | Primary Endpoint |
|--------|-----------|------------|--------|--------|-----------------|
| NCT05553366 | Acute pain (bunionectomy) | 1,075 | RCT, double-blind | Completed | SPID48 (pain score vs placebo) |
| NCT06696443 | DPN (long-term safety) | 455 | Open-label | Active, not recruiting | AEs/SAEs |
| NCT07231419 | DPN (efficacy) | 734 | RCT, quadruple-blind | **Recruiting** | NPRS pain score Δ at Week 12 |

**CTGOV signals for GUNGNIR** (suzetrigine DPN efficacy — NCT07231419):
- Placebo-controlled RCT (randomized) → `ctgov_placebo = 1`, `des_rct = 1`
- Quadruple masking → high masking rigor
- n=734 → `ctgov_real_enrollment = 734` (meaningful size)
- Primary endpoint: continuous pain score → not OS/ORR
- Sponsor: Vertex Pharmaceuticals (experienced, large-cap)
- Note: This trial is not yet in `ctgov_cache.json` (newly registered as NCT07231419)

**Cache update recommended**: Add NCT07231419 (suzetrigine/DPN) to `ctgov_cache.json`.

### 4b. Eli Lilly — Tirzepatide (HFpEF and Obesity)

Two Phase 3 programs found with materially different profiles.

| NCT ID | Trial | Indication | Enrollment | Status | Primary Endpoint |
|--------|-------|-----------|------------|--------|-----------------|
| NCT04847557 | SUMMIT | HFpEF + Obesity | 731 | **Completed** | KCCQ-CSS Δ + composite HF outcomes |
| NCT05556512 | SURMOUNT-MMO | Obesity (MACE) | 15,374 | Active, not recruiting | MACE composite (CV death, MI, stroke, HF, revasc.) |

**SUMMIT trial (NCT04847557 — COMPLETED, n=731)**:
- RCT, double-blind, placebo-controlled
- Dual co-primary: KCCQ-CSS functional improvement + HF composite event rate
- Primary completion: **July 2, 2024** — results should be available/published
- GUNGNIR signals: `des_rct=1`, `ctgov_placebo=1`, `des_pfs`-analog (composite endpoint), large experienced sponsor (LLY), phase 3
- This is a strong GUNGNIR candidate for retrospective scoring

**SURMOUNT-MMO (NCT05556512 — Active, n=15,374)**:
- Massive cardiovascular outcomes trial, primary completion October 2027
- Hard endpoint (MACE) → `des_primary_ep = hard`
- Will be a major GUNGNIR scoring event when results emerge in 2027

### 4c. AbbVie — ABBV-951 (Parkinson's Disease)

Only Phase 3 safety study found (NCT03781167, n=244, completed August 2022). This was a safety/tolerability primary endpoint trial — non-randomized, open-label. ABBV-951 (foslevodopa/foscarbidopa subcutaneous infusion) received FDA approval in 2023 as **Produodopa**. This confirms the drug is post-PDUFA and no new PDUFA events are pending for this specific compound.

---

## 5. Upcoming High-Priority Catalysts

| Catalyst | Ticker | Type | Date | Model | Priority |
|----------|--------|------|------|-------|----------|
| Vanzacaftor/TEZ/D-IVA (CF) | VRTX | PDUFA | **2026-03-28** | ODIN | 🔴 CRITICAL — 3 days |
| Orforglipron (obesity/T2D) | LLY | Phase 3 readout | Q1–Q2 2026 | GUNGNIR | 🟠 HIGH — imminent |
| Tirzepatide SUMMIT (HFpEF) | LLY | Phase 3 (retrospective) | Completed 2024 | GUNGNIR | 🟡 MEDIUM — score retrospectively |
| Suzetrigine DPN efficacy | VRTX | Phase 3 | 2027 | GUNGNIR | 🟢 MONITOR — recruiting |

---

## 6. Recommended Next Steps

1. **Re-enable 9realms MCP** — VRTX PDUFA is **3 days away**. This is the highest-urgency action. Production `odin_score` for VNZ/TEZ/D-IVA needs to run now to establish v5 baseline probability before the decision.

2. **Fix FinBrain MCP** — The `req` Pydantic schema incompatibility has now persisted across multiple monitor runs. With VRTX PDUFA imminent, missing insider transaction data is a real gap. Consider patching the MCP server to accept raw dicts.

3. **Update CTGOV cache** — Add NCT07231419 (suzetrigine/DPN, n=734, recruiting) to `ctgov_cache.json`. This is a new Vertex Phase 3 trial not yet in the cache.

4. **Score LLY SUMMIT retrospectively** — NCT04847557 completed July 2024 with n=731, dual primary endpoints, RCT. Run `gungnir_score` once MCP is re-enabled to validate GUNGNIR v30.1 on a known completed outcome.

5. **Activate v6.2/v30.2 optimization** — Both champions are stable with no new optimizer runs since March 1. Potential next directions: (a) incorporate LGB challenger's top features (`v1067_minus_v1070`, `historical_crl_rate`) into ODIN's Ridge ensemble; (b) GUNGNIR cross-validation stability testing on the 26-feature Ridge/Trees blend; (c) add `ctgov_has_withdrawals` signal to GUNGNIR from the SURMOUNT-MMO trial's ongoing status.

6. **Production deployment plan for v6.1** — The MCP server currently runs ODIN v5. A deployment plan to swap in v6.1 Ridge weights should be drafted before next quarter.

---

## 7. System Health

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ OK | `odin_v6_1_deploy.json` — Brier 0.1102, AUC 0.897, 32 features |
| GUNGNIR v30.1 deploy config | ✅ OK | `gungnir_v30_1_deploy.json` — Brier 0.1008, 26 features |
| LGB Challenger optimizer | ⏸️ IDLE | Round 241/721, WF AUC 0.8852, last run 2026-03-01 |
| Model registry | ✅ OK | 8 champion checkpoints + ensemble pool |
| 9realms MCP | 🔴 DISABLED | Connector must be re-enabled before VRTX PDUFA (Mar 28) |
| FinBrain MCP | 🔴 BROKEN | Pydantic `req` schema incompatibility — needs server-side fix |
| ClinicalTrials.gov MCP | ✅ OK | New data retrieved: VRTX/LLY/ABBV Phase 3 trials validated |
| Autonomous optimizer | ⏸️ IDLE | No new checkpoints since v9 |

---

## 8. Δ Changes vs v9

- **Models**: No changes. Same champions.
- **Optimizer**: No new checkpoint rounds. Still at round 241.
- **New CT data**: NCT07231419 (suzetrigine DPN efficacy, recruiting, n=734) — not in cache, add recommended.
- **LLY SUMMIT confirmed**: NCT04847557 COMPLETED (n=731, July 2024) — HFpEF readout available for retrospective GUNGNIR scoring.
- **ABBV-951 resolved**: Confirmed post-PDUFA (approved 2023 as Produodopa). No pending ABBV PDUFA on this compound.
- **MCP status**: Both 9realms and FinBrain remain blocked — unchanged from v9.

---

*Report v10 generated automatically by scheduled monitor task. Next run will check for VRTX PDUFA outcome (decision expected 2026-03-28) and re-attempt disabled MCP connections.*

*⚠️ Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
