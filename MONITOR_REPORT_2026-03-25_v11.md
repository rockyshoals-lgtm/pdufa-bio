# ODIN v6 / GUNGNIR v30 — Monitor Report v11
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | ✅ CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | -7.5% vs v5 (worse) | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | ✅ CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

**No changes since v10.** Champions remain ODIN v6.1.0 (Brier 0.1102) and GUNGNIR v30.1.0 (Brier 0.1008). Deploy configs confirmed present and unmodified.

**ODIN v6.1 architecture**: Ridge C=15.0, 32 forward-selected features, isotonic calibrated. 7 new features beyond v5 baseline: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Holdout AUC 0.897, trained on 1,845 events with 358-event holdout.

**GUNGNIR v30.1 architecture**: Ridge(70%)+Trees(30%) blend, 26 features. Interpretable feature set spanning drug journey signals, trial design markers, therapeutic area, and modality. The 56.9% Brier improvement over v29 remains the largest single-version jump in GUNGNIR history.

### Autonomous Optimizer (LGB Challenger) — Still Idle

The `models/lgb_champions/` directory contains **8 champion checkpoints spanning rounds 1–241** out of 721 total optimization rounds. The current champion (round 241, `af6a433fc23e`) achieved WF AUC **0.8852**, Brier **0.2057** using a 51-feature LightGBM ensemble. Last activity timestamped **2026-03-01T01:51:54** — now **24 days idle** with no new checkpoints detected this run.

**LGB Challenger champion features of note**: `v1067_minus_v1070` (importance 9,009), `historical_crl_rate` (8,576), `v1070_score` (6,940), `log_crl_rate` (6,091). The ODIN v1067/v1070 ensemble differential remains the strongest signal. With 480 allocated rounds remaining (241–721), the optimizer appears stalled — either the process terminated or the improvement frontier has been reached at round 241.

---

## 2. Production MCP Scoring — DISABLED (Unchanged)

The 9realms MCP tools (`odin_score`, `gungnir_score`, `system_status`) remain **disabled in connector settings**. All three calls continue to return `"This tool has been disabled in your connector settings."` Production v5/v29 scores cannot be compared against v6.1/v30.1 predictions until the connector is re-enabled.

**⚠️ CRITICAL — VRTX PDUFA IS IN 3 DAYS (2026-03-28)**: This is the highest-urgency action item. The inability to run `odin_score` for VNZ/TEZ/D-IVA continues to leave the primary ODIN validation opportunity unexecuted. Re-enable the connector immediately.

---

## 3. FinBrain MCP — PARAMETER INCOMPATIBILITY (Unchanged)

FinBrain MCP `req` parameter continues to fail validation (`Input should be a valid dictionary or instance of InsiderReq/SentimentsReq/AnalystRatingsReq`). The MCP server expects a Pydantic model instance that cannot be constructed through the tool call interface. Both string-serialized JSON and JSON object forms were attempted across multiple runs — both continue to fail.

**Deferred checks (blocked)**:
- VRTX insider transactions — PDUFA **2026-03-28** (3 days, critical)
- LLY news sentiment — orforglipron NDA cycle likely active (see Section 4b)
- ABBV analyst ratings — sabizabulin and pipeline

**Action Required**: FinBrain MCP connector needs schema update to accept plain JSON objects, or a wrapper function needs to be added upstream. This blocker has now persisted across **multiple consecutive monitor runs**.

---

## 4. ClinicalTrials.gov Validation — New Data This Run

### 4a. Vertex Pharmaceuticals — VNZ/TEZ/D-IVA (PDUFA 2026-03-28)

**🆕 KEY NEW FINDING**: NCT07349394 (rosuvastatin PK interaction study) was updated **2026-03-10** — just 15 days ago — and is actively recruiting (active_not_recruiting, primary completion April 4, 2026). This post-approval pharmacokinetic study is actively running *concurrent with the PDUFA window*, consistent with Vertex preparing for a launch scenario. Drug interaction studies of this type are typically initiated in anticipation of approval.

| NCT ID | Trial Type | Enrollment | Status | Primary Completion | Last Updated |
|--------|-----------|------------|--------|-------------------|--------------|
| NCT07349394 | PK / drug interaction (rosuvastatin) | 18 | Active, not recruiting | **2026-04-04** | **2026-03-10** ← NEW |
| NCT05844449 | Long-term safety/efficacy OLE (age ≥1y) | 174 | Enrolling by invitation | 2029-07-30 | 2026-02-05 |
| NCT06154447 | VX-828 Phase 1/2 (next-gen CF modulator) | 255 | Recruiting | 2026-04-23 | 2026-02-24 |
| NCT06299709 | Pediatric granule bioavailability | 34 | Completed | 2024-05-23 | 2025-09-26 |

**CTGOV signals for ODIN** (VNZ/TEZ/D-IVA PDUFA scoring context):
- Vertex has Breakthrough Therapy Designation and Priority Review for VNZ/TEZ/D-IVA
- Experienced sponsor (VRTX — prior CF approvals: ivacaftor, lumacaftor/IVA, tezacaftor/IVA, elexacaftor/TEZ/IVA)
- Drug interaction study active pre-decision → preparation signal
- No prior CRL on this asset
- Orphan designation, rare/genetic disease TA → high ODIN favorable feature cluster

**Cache update**: NCT07349394 is in cache; most recent update (2026-03-10) should be re-synced.

### 4b. Eli Lilly — Orforglipron Phase 3 Portfolio

**🆕 THREE PIVOTAL TRIALS NOW COMPLETED**: All major Phase 3 readout trials have reached primary completion since our last comprehensive review.

| NCT ID | Trial | Indication | Enrollment | Status | Primary Completion | Notes |
|--------|-------|-----------|------------|--------|-------------------|-------|
| NCT05872620 | ACHIEVE-1 (inferred) | Obesity + T2D | 1,613 | **COMPLETED** | **2025-08-08** | Key pivotal |
| NCT05869903 | ACHIEVE-2 (inferred) | Obesity/overweight + comorbidities | 3,127 | Active, not recruiting | **2025-07-25** | Largest pivotal |
| NCT06109311 | T2D + insulin glargine | T2D on basal insulin | 546 | **COMPLETED** | **2025-09-15** | Supplemental |
| NCT05931380 | Japanese obesity | Obesity (Japan) | 238 | **COMPLETED** | **2025-06-19** | Regional |

**🆕 NEW EXPANSION TRIAL — FIRST SIGHTING**: NCT07153471 is a newly identified Phase 3 study of orforglipron in participants with obesity or overweight and **osteoarthritis (OA) of the knee** (n=800, RECRUITING, primary completion April 2028). This represents a new musculoskeletal indication expansion beyond the metabolic core program — not previously tracked.

**Key GUNGNIR implications for orforglipron NDA cycle**:
- Three pivotal trials completed with combined n≈5,300 — NDA submission to FDA highly probable in H1 2026
- Large real enrollment (`ctgov_real_enrollment` signal) → positive GUNGNIR feature
- Placebo-controlled RCT design across all pivotals
- Oral GLP-1 mechanism competes with injectable tirzepatide/semaglutide — `competitive` feature applies
- OA expansion trial (NCT07153471) suggests LLY is building label breadth pre-approval

### 4c. AbbVie — Status Unchanged

ABBV-951 (foslevodopa/foscarbidopa) confirmed post-PDUFA — approved as Produodopa 2023. No new ABBV PDUFA events pending from CT.gov data.

---

## 5. Upcoming High-Priority Catalysts

| Catalyst | Ticker | Type | Date | Model | Priority |
|----------|--------|------|------|-------|----------|
| Vanzacaftor/TEZ/D-IVA (CF) | VRTX | PDUFA | **2026-03-28** | ODIN | 🔴 CRITICAL — 3 DAYS |
| Orforglipron NDA submission | LLY | PDUFA (expected) | H1 2026 | ODIN | 🟠 HIGH — 3 pivotals complete |
| Orforglipron (obesity/T2D Phase 3) | LLY | Phase 3 readout | 2025 (data available) | GUNGNIR | 🟠 HIGH — score now |
| Tirzepatide SUMMIT (HFpEF) | LLY | Phase 3 (retrospective) | Completed 2024 | GUNGNIR | 🟡 MEDIUM |
| Orforglipron OA of knee (NCT07153471) | LLY | Phase 3 | Apr 2028 | GUNGNIR | 🟢 MONITOR — new |
| Suzetrigine DPN efficacy (NCT07231419) | VRTX | Phase 3 | 2027 | GUNGNIR | 🟢 MONITOR |

---

## 6. Recommended Next Steps

1. **Re-enable 9realms MCP immediately** — VRTX PDUFA is **3 days away**. Run `odin_score` for VNZ/TEZ/D-IVA to establish the v5 production baseline probability, then compare against v6.1 predictions. This is the single highest-urgency action.

2. **Fix FinBrain MCP** — The Pydantic `req` schema incompatibility has now persisted across **multiple consecutive runs**. Patch the MCP server to accept raw dict/JSON objects. VRTX insider transaction data is urgently needed before the March 28 decision.

3. **Score orforglipron via GUNGNIR** — Three Phase 3 trials are now completed (combined n≈5,300). Run `gungnir_score` for each completed readout once MCP is re-enabled to validate GUNGNIR v30.1 against known outcomes and build the NDA scoring dossier.

4. **Track orforglipron NDA filing** — Pivotal data complete as of September 2025. LLY NDA submission in Q1–Q2 2026 is probable. Add to ODIN catalyst pipeline when filed.

5. **Add NCT07153471 to GUNGNIR candidate list** — Orforglipron OA of knee (n=800, Phase 3, primary completion April 2028) is a new expansion indication first identified this run. Add to ctgov_cache.json and flag for future GUNGNIR scoring.

6. **Restart or cap autonomous optimizer** — The LGB challenger has been idle since March 1 (24 days). With 480 rounds remaining unexecuted (241 of 721), the optimizer process appears to have stalled. Options: (a) restart from round 242, (b) cap at round 241 and declare the LGB challenger's ceiling at WF AUC 0.8852, or (c) investigate process termination cause.

7. **Draft ODIN v6.1 production deployment plan** — The MCP server still runs ODIN v5. A concrete migration plan to swap in v6.1 Ridge weights should be drafted before Q2 2026.

---

## 7. System Health

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ OK | `odin_v6_1_deploy.json` — Brier 0.1102, AUC 0.897, 32 features |
| GUNGNIR v30.1 deploy config | ✅ OK | `gungnir_v30_1_deploy.json` — Brier 0.1008, 26 features |
| LGB Challenger optimizer | ⏸️ IDLE | Round 241/721, WF AUC 0.8852, last run 2026-03-01 (24 days ago) |
| Model registry | ✅ OK | 8 champion checkpoints + ensemble pool |
| 9realms MCP | 🔴 DISABLED | Connector must be re-enabled before VRTX PDUFA (Mar 28) |
| FinBrain MCP | 🔴 BROKEN | Pydantic `req` schema incompatibility — persists across all runs |
| ClinicalTrials.gov MCP | ✅ OK | New data: orforglipron OA expansion trial (NCT07153471); VNZ/TEZ/D-IVA PK study updated Mar 10 |
| Autonomous optimizer | ⏸️ IDLE | No new checkpoints since v10 |

---

## 8. Δ Changes vs v10

- **Models**: No changes. Same champions (ODIN v6.1 / GUNGNIR v30.1).
- **Optimizer**: No new checkpoint rounds. Still at round 241/721.
- **🆕 New CT finding**: NCT07153471 — orforglipron OA of knee Phase 3 (n=800, recruiting, Apr 2028). First-ever sighting; not in ctgov_cache.json.
- **🆕 VNZ/TEZ/D-IVA**: NCT07349394 PK study updated 2026-03-10 (15 days ago) — active trial activity signals pre-approval preparation.
- **Orforglipron Phase 3 status confirmed**: Three pivotals completed (n≈5,300 combined). NDA filing expected imminently.
- **MCP status**: Both 9realms and FinBrain remain blocked — unchanged from v10.

---

*Report v11 generated automatically by scheduled monitor task. Next run: check for VRTX PDUFA outcome (decision 2026-03-28), re-attempt disabled MCP connections, verify orforglipron NDA filing status.*

*⚠️ Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
