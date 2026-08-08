# ODIN v6 / GUNGNIR v30 Monitor Report — v28
**Generated**: 2026-03-25 (automated scheduled run)
**Previous report**: MONITOR_REPORT_2026-03-25_v27.md

---

## ⚡ Key Developments Since v27

1. **RCKT Kresladi decision is 3 days out** — March 28 PDUFA confirmed imminent. CT.gov NCT03812263 (pivotal, Phase 1/2) remains **COMPLETED** (no status change from v27). NCT06282432 (LTFU) remains **ACTIVE_NOT_RECRUITING** (no change). Both confirmed via live CT.gov API this run.
2. **BIIB tofersen post-approval expansion detected** — New CT.gov entries surfaced: NCT07294144 "Tofersen in Non-SOD1 ALS" (Phase 2, **RECRUITING**, last update 2026-02-09) and NCT07223723 "Long-Term Safety of Tofersen (Qalsody) in Chinese Participants" (Phase 4, **RECRUITING**, last update 2026-01-20). The brand name "Qalsody" in NCT07223723 confirms tofersen already carries an approved US trade name. This suggests the April 3 BIIB PDUFA may be a supplemental/label expansion rather than an initial approval.
3. **PRAX-628 readout in 6 days** — March 31. NCT06908356 remains **RECRUITING** (no change from v27).
4. **All model champions unchanged (28th run)** — ODIN v6.1 (Brier 0.1102) and GUNGNIR v30.1 (Brier 0.1008) remain stable. No `odin_v6_2_deploy.json` or `gungnir_v30_2_deploy.json` detected.
5. **LGB optimizer fully terminated (28th run)** — No `logs/` directory. 721 total rounds, 8 promotions, last champion round 241 (~2026-03-01). No new checkpoints.
6. **9realms MCP DISABLED (28th consecutive run)** — All ODIN/GUNGNIR live scoring blocked by connector settings.
7. **FinBrain pydantic error persists (28th consecutive run)** — Same `InsiderReq` / `SentimentsReq` / `AnalystRatingsReq` model_type mismatch. No data retrievable.

---

## 1. Executive Summary

**RCKT Kresladi (RP-L201)** for Leukocyte Adhesion Deficiency-I is the highest-urgency catalyst. The March 28 PDUFA falls on a Saturday; FDA action is expected Friday March 27 (today) or Monday March 30. CT.gov confirms both studies (pivotal + LTFU) are unchanged — no last-minute amendments.

**BIIB tofersen** — a notable new signal this run: two post-approval-era studies (Phase 4 Chinese registry + Phase 2 non-SOD1 expansion) are now recruiting on CT.gov, and both reference the approved brand name "Qalsody." This means the April 3 PDUFA is almost certainly a supplemental NDA (sNDA) or label update, not an initial approval — which slightly reduces binary risk but also limits upside.

**PRAX-628** (PRAX) Phase 2 remains on track for March 31. NCT06908356 still recruiting.

Both model champions (ODIN v6.1, GUNGNIR v30.1) remain stable. No new optimization configs. Infrastructure issues (9realms MCP disabled, FinBrain broken) continue at 28 consecutive runs.

---

## 2. Model Champion Status

### ODIN v6 — PDUFA Approval Scoring

| Version | Architecture | Features | HO AUC | HO Brier | vs v5 Brier |
|---------|-------------|----------|---------|----------|-------------|
| v5 (prod baseline) | Ridge L2 C=1.5 | 25 | 0.9007 | 0.1210 | — |
| v6.0 (initial) | LGB+XGB+CatBoost+TabNet+Ridge ensemble | 65 | 0.859 | 0.1378 | -7.45% (worse) |
| **v6.1 (CHAMPION)** | **Ridge C=15.0, isotonic calibrated** | **32** | **0.897** | **0.1102** | **+8.92% better** |

**New configs this run**: None. `odin_v6_2_deploy.json` does not exist.

**v6.1 features (32 total)**: All 25 v5 features retained plus 7 new: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`.

**Status**: STABLE. v6.1 is the deployment target.

---

### GUNGNIR v30 — Phase Readout Scoring

| Version | Architecture | Features | HO Brier | vs v29 Brier |
|---------|-------------|----------|----------|--------------|
| v29 (prod baseline) | Ridge(75%)+P3 meta, CTGOV real data | 82 | 0.2339 | — |
| v30.0 (initial) | LGB+XGB+CatBoost+FT-Transformer+TabNet+Ridge | 109 | 0.1394 | +40.4% better |
| **v30.1 (CHAMPION)** | **Ridge C=30 + Trees blend (70/30)** | **26** | **0.1008** | **+56.9% better** |

**New configs this run**: None. `gungnir_v30_2_deploy.json` does not exist.

**Status**: STABLE. v30.1 is the deployment target.

---

### ⚠️ Leaky Artifact Alert: gungnir_champion_ladder.json (Ongoing)

The workspace-root `gungnir_champion_ladder.json` remains present with WF AUC 0.9979 / Brier 0.0393 and post-readout features (`primary_endpoint_met`, `endpoint_met_phase3`, etc.) — identical leakage class to the retired GUNGNIR v25. **Do not use for production scoring.** Legitimate champion is GUNGNIR v30.1 (Brier 0.1008, 26 clean T-1 features).

---

## 3. LGB Autonomous Optimizer Status

| Metric | Value |
|--------|-------|
| Total rounds run | **721** (unchanged since v15) |
| Total champion promotions | **8** (unchanged since v15) |
| Last champion file timestamp | Mar 2, 04:42 (champion_ladder.json) |
| Latest ensemble_pool file | lgb_r00619 (Mar 2, 02:46) |
| `logs/` directory | **NOT PRESENT** |
| Optimizer status | **FULLY TERMINATED** |

Last champion metrics (round 241): WF AUC 0.8852, WF Brier 0.2057, 51 features.

**Assessment**: Optimizer dormant since ~March 1. GUNGNIR v30.1 (Brier 0.1008) substantially outperforms the LGB optimizer's best result (WF Brier 0.2057). No restart needed.

---

## 4. MCP Tool Status

### 9realms MCP (ODIN/GUNGNIR Live Scoring)
- **Status**: DISABLED (28th consecutive run)
- `odin_score`, `gungnir_score`, `system_status` all blocked by connector settings
- **Action required**: Enable the 9realms connector in settings to restore live scoring

### FinBrain MCP
- **Server**: ALIVE (v0.1.6 / sdk 0.1.8)
- **Data tools**: ALL FAILING — pydantic model_type mismatch (28th consecutive run)
  - `insider_transactions_by_ticker`: `InsiderReq` type error
  - `news_sentiment_by_ticker`: `SentimentsReq` type error
  - `analyst_ratings_by_ticker`: `AnalystRatingsReq` type error
- **Error**: `Input should be a valid dictionary or instance of [Model]` — JSON string rejected, native Pydantic object required
- **Action required**: FinBrain MCP server schema fix or connector update needed

### ClinicalTrials.gov MCP
- **Status**: ✅ OPERATIONAL (search + get_study working)
- `clinicaltrials_get_study` requires single NCT ID string (not array) per call
- All three key NCTs confirmed via live API this run

---

## 5. ClinicalTrials.gov Catalyst Validation

### RCKT — Kresladi (RP-L201) | PDUFA: March 28, 2026 (IMMINENT — 3 days)

| NCT | Title | Status | Change vs v27 |
|-----|-------|--------|---------------|
| NCT03812263 | RP-L201 Safety & Efficacy in LAD-I (pivotal, Phase 1/2) | **COMPLETED** | ✅ No change |
| NCT06282432 | Long-Term Follow-Up for Gene Therapy of LAD-I | **ACTIVE_NOT_RECRUITING** | ✅ No change |

- Pivotal n=9 (ultra-rare disease, expected small N) — Sponsor: Rocket Pharmaceuticals Inc.
- No last-minute amendments or status changes detected
- Decision window: **Friday March 27** (most likely, today) or Monday March 30

---

### PRAX-628 (PRAX) | Phase 2 Readout: March 31, 2026 (6 days)

| NCT | Title | Status | Change vs v27 |
|-----|-------|--------|---------------|
| NCT06908356 | PRAX-628 in Focal Onset or Tonic-Clonic Seizures | **RECRUITING** | ✅ No change |

- Phase 2, 30mg PRAX-628, Sponsor: Praxis Precision Medicines
- Readout in 6 days — trial still open/recruiting per CT.gov

---

### BIIB / IONS | PDUFA: April 3, 2026 (9 days)

| NCT | Title | Status | Last Update | Notes |
|-----|-------|--------|-------------|-------|
| NCT03070119 | Long-Term Evaluation of BIIB067 (Tofersen) | **COMPLETED** | 2025-08-29 | Phase 3 LTE done |
| NCT04856982 | Tofersen in Presymptomatic SOD1 ALS | **ACTIVE_NOT_RECRUITING** | 2025-03-07 | Phase 3, ongoing |
| NCT07294144 | **Tofersen in Non-SOD1 ALS** | **RECRUITING** | 2026-02-09 | 🆕 Phase 2, expansion |
| NCT07223723 | Long-Term Safety of Tofersen (Qalsody) in Chinese Participants | **RECRUITING** | 2026-01-20 | 🆕 Phase 4, post-approval China |

**🆕 New This Run**: Two previously undetected studies confirm tofersen is already approved under the trade name **Qalsody** (NCT07223723 explicitly uses "Qalsody" in the title). The April 3 BIIB PDUFA is therefore likely a **supplemental NDA** (sNDA) for a new indication or label update — not an initial approval. This is a signal change: sNDA decisions carry higher baseline approval rates (~85–90%) but more limited price-reaction upside vs. initial approval events.

---

## 6. Upcoming Catalyst Calendar

| Catalyst | Ticker | Event Type | Date | Days Out | Key Signal |
|----------|--------|------------|------|----------|------------|
| Kresladi (RP-L201) | RCKT | PDUFA (FDA approval) | Mar 28 → Mar 27 or 30 | **2–5 days** | Gene therapy, ultra-rare LAD-I, pivotal COMPLETED |
| PRAX-628 | PRAX | Phase 2 readout | Mar 31 | 6 days | Open-label, focal seizures, still recruiting |
| tofersen (Qalsody sNDA) | BIIB | sNDA (label expansion?) | Apr 3 | 9 days | Post-approval sNDA; high baseline approval rate |
| [IONS drug] | IONS | PDUFA | Apr 3 | 9 days | Details pending CT.gov confirmation |

---

## 7. Recommended Next Steps

1. **RCKT watch (URGENT)**: Decision window is today (Friday March 27) or Monday March 30. Monitor FDA press releases and RCKT investor relations. Gene therapy for ultra-rare LAD-I with unmet need — FDA has been supportive of this therapeutic class. Pivotal study (n=9) is completed, LTFU is ongoing.

2. **BIIB reassessment**: The April 3 "PDUFA" appears to be a supplemental NDA for tofersen (Qalsody), not an initial approval. This changes the risk/reward profile — sNDA decisions are high-probability approvals but typically generate muted price reactions vs. initial approvals. Confirm the specific sNDA indication (presymptomatic SOD1 ALS vs. another label expansion).

3. **Restore 9realms MCP connector**: 28 consecutive runs without live scoring. ODIN tier and GUNGNIR probability for the above catalysts are unavailable. Enable in connector settings.

4. **Fix FinBrain MCP**: 28 consecutive runs with the same pydantic schema error. The fix is in the MCP server: the `req` parameter needs to accept a plain dict in addition to the native Pydantic model class. Contact the FinBrain MCP maintainer.

5. **ODIN v6.1 deployment**: Ready for production (Brier 0.1102, AUC 0.897, 32 features). No further optimization needed.

6. **GUNGNIR v30.1 deployment**: Ready for production (Brier 0.1008, +56.9% vs v29, 26 features). Archive or delete the leaky `gungnir_champion_ladder.json` at workspace root.

---

## 8. Infrastructure Health Summary

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ Stable | No v6.2 detected |
| GUNGNIR v30.1 deploy config | ✅ Stable | No v30.2 detected |
| LGB optimizer | 🔴 Terminated | Expected; v30.1 superior |
| 9realms MCP (scoring) | 🔴 DISABLED | 28 consecutive runs |
| FinBrain MCP (data) | 🟡 Server alive, data broken | 28 consecutive runs |
| ClinicalTrials.gov MCP | ✅ Operational | Single-NCT query mode confirmed |
| Leaky artifact warning | ⚠️ gungnir_champion_ladder.json | Workspace root, post-readout features |

---

*Disclaimer: All scoring outputs, tier classifications, and investment signals from ODIN/GUNGNIR are for informational and educational purposes only. Not investment advice.*
