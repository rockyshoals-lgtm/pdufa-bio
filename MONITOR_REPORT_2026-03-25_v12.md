# ODIN v6 / GUNGNIR v30 — Monitor Report v12
**Date**: 2026-03-25 | **Run**: Scheduled Automated Monitor

---

## ⚠️ CRITICAL CORRECTION vs v11 — PDUFA Ticker Mismatch

**The March 28 PDUFA was for LLY (orforglipron), NOT VRTX.**

Prior reports v1–v11 incorrectly listed "Vanzacaftor/TEZ/D-IVA (VRTX)" as the March 28, 2026 PDUFA catalyst. This is wrong on two counts:
1. **ALYFTREK (vanzacaftor/tezacaftor/deutivacaftor) was already FDA-approved on December 20, 2024** — well before this monitoring period began.
2. **The March 28 date belonged to orforglipron (LLY)**, which was set as an accelerated internal target. That date has since been extended to **April 10, 2026** (see Section 4).

All prior PDUFA urgency flags ("🔴 CRITICAL — 3 DAYS") for VRTX VNZ/TEZ/D-IVA should be disregarded. The correct upcoming T1 catalyst is **LLY orforglipron, PDUFA April 10, 2026** (16 days away).

---

## 1. Model Status Summary

| Model | Version | Brier Score | vs Baseline | AUC | Features | Status |
|-------|---------|-------------|-------------|-----|----------|--------|
| **ODIN** | v6.1.0 | **0.1102** | +8.9% vs v5 (0.1210) | 0.897 | 32 | ✅ CHAMPION |
| **ODIN** | v6.0.0 | 0.1378 | −7.5% vs v5 | 0.859 | 65 | Retired |
| **GUNGNIR** | v30.1.0 | **0.1008** | +56.9% vs v29 (0.2339) | — | 26 | ✅ CHAMPION |
| **GUNGNIR** | v30.0.0 | 0.1394 | +40.4% vs v29 | 0.822 | 109 | Retired |

**No model changes since v11.** Deploy configs confirmed present and unmodified.

**ODIN v6.1 architecture**: Ridge C=15.0, 32 forward-selected features, isotonic calibrated. 7 new features beyond v5 baseline: `year`, `sponsor_rolling_approval_rate`, `adcom_x_pr`, `sponsor_volume_log`, `month`, `experienced_x_low_crl`, `spa_mid`. Holdout AUC 0.897, trained on 1,845 events, 358-event holdout.

**GUNGNIR v30.1 architecture**: Ridge(70%)+Trees(30%) blend, 26 features. The 56.9% Brier improvement over v29 remains the largest single-version jump in GUNGNIR history.

### Autonomous Optimizer (LGB Challenger) — Still Idle

The `models/lgb_champions/` directory still shows **8 champion checkpoints spanning rounds 1–241** with last activity timestamped **2026-03-01T01:51:54** — now **24 days idle**, unchanged from v11. No new checkpoint files detected. The ensemble pool contains 7 models (rounds 44–241). The optimizer process appears terminated or stalled with 480 rounds (241–721) remaining.

---

## 2. MCP Tool Status

| Tool | Status | Notes |
|------|--------|-------|
| **9realms MCP** | 🔴 DISABLED | Blocked by connector settings — `system_status`, `odin_score`, `gungnir_score` all return "tool disabled" error |
| **FinBrain MCP** | 🔴 BROKEN | Persistent Pydantic `req` schema incompatibility. All three tools (`insider_transactions_by_ticker`, `news_sentiment_by_ticker`, `analyst_ratings_by_ticker`) reject string-serialized JSON with `Input should be a valid dictionary or instance of [Model]` — server expects native dict, MCP layer serializes to string. **11th consecutive failed run.** |
| **ClinicalTrials.gov MCP** | 🔴 DEGRADED | New error this run: `data must have required property 'pagedStudies'` — schema mismatch between MCP output and validator. Both `clinicaltrials_search_studies` and `clinicaltrials_get_study` failing. **Regression from v11 (was ✅ OK).** |
| **Perplexity MCP** | ✅ OK | Used successfully for catalyst research; 3 queries executed |

**Note**: All production scoring (ODIN `odin_score`, GUNGNIR `gungnir_score`) remains blocked. The 9realms MCP running ODIN v5 in production has now been disabled for the full duration of this monitoring run series.

---

## 3. ABBV — Insider Signal (via Perplexity)

FinBrain MCP is unavailable, but Perplexity search surfaced the following insider activity:

**AbbVie (ABBV)** — SVP David Ryan Purdue **sold 5,230 shares** at $233.56/share for a total of **$1,221,518.80**, filed March 4, 2026. Following the sale, Purdue directly owned 2,654 shares — a **66.34% decrease** in his personal holding. The stock traded down ~1% on the day of the disclosure (March 10, 2026 report date).

**ODIN context**: ABBV-951 (foslevodopa/foscarbidopa) was approved as Produodopa in 2023 — no pending ABBV PDUFA events. This insider sale is noted for the record but does not affect current ODIN scoring pipeline. No new ABBV PDUFA events identified.

---

## 4. 🆕 LLY Orforglipron — PDUFA Date Update (CRITICAL)

### Timeline correction

Previous reports placed orforglipron at a March 28, 2026 PDUFA. This was based on internal FDA accelerated-review tracking. The confirmed update:

- **Original statutory deadline**: May 20, 2026
- **Accelerated internal target (Reuters, Jan 2026)**: March 28, 2026
- **Revised target action date (BioSpace, Jan 15, 2026)**: **April 10, 2026** — FDA extended its review for orforglipron and three other "Commissioner's National Priority Voucher" awardees

**Current status as of March 25, 2026**: April 10, 2026 PDUFA — **16 days away**.

### ACHIEVE-3 Phase 3 Head-to-Head Results (published Feb 26, 2026 in *The Lancet*)

The ACHIEVE-3 trial was the first head-to-head Phase 3 comparison of orforglipron vs. oral semaglutide in adults with T2D on metformin. Results:

- Orforglipron **outperformed oral semaglutide on primary and ALL key secondary endpoints**
- Greater A1C reduction, more weight loss, no food/water timing restrictions
- Lilly CEO David Ricks: "FDA action on obesity expected next quarter" (Q2 2026), describing review as moving "at pace"
- Orforglipron submitted to **40+ countries globally**; T2D submission to US planned later in 2026

**GUNGNIR implications for ACHIEVE-3**: This is a completed positive Phase 3 readout. GUNGNIR v30.1 features that would apply: `des_rct` (RCT design ✅), `des_primary_ep` (primary endpoint met ✅), `des_orr` (not applicable — metabolic endpoint), `competitive` (high — vs semaglutide), `drug_last` (prior orforglipron data positive ✅), `ta_oncology` (no — metabolic TA), `era_post24` (2026 ✅). Score pending MCP restoration.

### ODIN implications for NDA (obesity)

The orforglipron NDA for obesity has been filed and is under active FDA review (PDUFA April 10, 2026). ODIN v5/v6.1 scoring features that apply:
- `btd_bin`: No (not breakthrough designation for obesity indication)
- `pr_bin`: Yes (priority review via national voucher)
- `sponsor_experienced`: Yes (LLY — experienced NDA sponsor)
- `is_nda`: Yes
- `prior_crl_bin`: No
- `ta_very_high`: Metabolic/obesity — moderate-high TA tier
- `surrogate`: No — weight loss and A1C are validated endpoints, not traditional surrogate
- `era_post`: Yes (2026)

**ODIN v5 production score**: Cannot run — MCP disabled. Estimated tier: **T1–T2** range given experienced sponsor, priority review, strong efficacy data, no prior CRL, no safety signals. Recommend running `odin_score` immediately upon MCP restoration.

---

## 5. 🆕 VRTX — Corrected Pipeline Status

### ALYFTREK: Already Approved (December 20, 2024)

Vanzacaftor/tezacaftor/deutivacaftor (ALYFTREK) received **FDA approval on December 20, 2024** — 13 days before its January 2, 2025 PDUFA date. This was a commercial launch event, not a pending catalyst. All prior monitor reports referencing this as an upcoming PDUFA are in error.

### Actual Upcoming VRTX Catalysts

| Catalyst | Type | Timeline | ODIN/GUNGNIR | Notes |
|----------|------|----------|--------------|-------|
| Povetacicept (IgAN) | BLA (rolling) → PDUFA | BLA filing H1 2026 → PDUFA ~H2 2026 | ODIN | BTD, accelerated approval, priority review voucher |
| Inaxaplin (AMKD) | Phase 3 → NDA | 48-week data 2026 | ODIN (future) | Enrollment complete |
| Suzetrigine DPN | Phase 3 | Enrollment complete end-2026 | GUNGNIR (future) | Nociceptor pain |
| VX-407 ADPKD | Phase 2 | Initiated 2025 | N/A | Early stage |

**Povetacicept (IgAN) — Near-term PDUFA setup**:
- Breakthrough Therapy Designation ✅
- Priority Review Voucher ✅ (6-month review from filing)
- Rolling BLA filing to complete by end-March 2026 ("BLA cut-off around March 30, 2026" per AInvest)
- Positive 36-week RAINIER Phase 3 data → accelerated approval pathway
- If BLA filed by end of March 2026, PDUFA target ≈ **September–October 2026**
- ODIN features: BTD ✅, PR ✅, experienced sponsor ✅, no prior CRL ✅, rare/renal TA ✅ → expected T1–T2

**Action item**: Add povetacicept to ODIN scoring queue. Run `odin_score` upon MCP restoration.

---

## 6. Updated Catalyst Priority Table

| Catalyst | Ticker | Type | Date | Model | Priority | Δ vs v11 |
|----------|--------|------|------|-------|----------|----------|
| Orforglipron (obesity NDA) | LLY | PDUFA | **2026-04-10** | ODIN | 🔴 CRITICAL — 16 days | 🆕 CORRECTED (was VRTX, wrong date) |
| Povetacicept (IgAN BLA filing) | VRTX | BLA → PDUFA | Filing ~Mar 30 → PDUFA ~Sep 2026 | ODIN | 🟠 HIGH — filing imminent | 🆕 NEW |
| Orforglipron (T2D obesity) | LLY | Phase 3 (ACHIEVE-3) | **Complete — Feb 26, 2026** | GUNGNIR | 🟠 HIGH — score now | 🆕 ACHIEVE-3 data published |
| Orforglipron (T2D NDA US) | LLY | NDA submission | Later 2026 | ODIN (future) | 🟡 MEDIUM | Unchanged |
| Orforglipron OA knee (NCT07153471) | LLY | Phase 3 | Apr 2028 | GUNGNIR | 🟢 MONITOR | Unchanged |
| Suzetrigine DPN efficacy | VRTX | Phase 3 | End-2026 enrollment | GUNGNIR | 🟢 MONITOR | Unchanged |
| Inaxaplin AMKD NDA | VRTX | Phase 3 → NDA | 2026–2027 | ODIN (future) | 🟢 MONITOR | Unchanged |

---

## 7. Recommended Next Steps

1. **Score orforglipron PDUFA via ODIN immediately** — April 10, 2026 is 16 days away. Re-enable the 9realms MCP and run `odin_score` for LLY orforglipron (obesity NDA) to establish the production v5 baseline and compare against v6.1 predictions. This is the highest-urgency single action.

2. **Correct ODIN database** — Remove VRTX VNZ/TEZ/D-IVA from all pending PDUFA lists. It was approved December 20, 2024. Add LLY orforglipron (obesity, PDUFA April 10, 2026) and VRTX povetacicept (IgAN, PDUFA ~Sep 2026) to the active scoring queue.

3. **Fix FinBrain MCP** — Insider/sentiment data is now unavailable for 11 consecutive runs. The Pydantic `InsiderReq` and `SentimentsReq` models are rejecting string-serialized JSON. Patch the MCP server to accept `dict` input natively, or update the MCP wrapper to deserialize the JSON string before passing to Pydantic. This is blocking pre-decision intelligence for the April 10 LLY catalyst.

4. **Fix ClinicalTrials.gov MCP** — New regression this run: `pagedStudies` property missing in output schema validation. This is likely an API version change on the CT.gov side (v2 API response format may have changed). The MCP server needs to be updated to match the new response schema.

5. **Score ACHIEVE-3 via GUNGNIR** — Orforglipron ACHIEVE-3 Phase 3 data published February 26, 2026 in *The Lancet* with positive results on all endpoints. Run `gungnir_score` for this readout once MCP is restored to validate GUNGNIR v30.1 against a known positive Phase 3 outcome and calibrate the LLY metabolic pipeline scoring.

6. **Add povetacicept to ODIN pipeline** — VRTX povetacicept BLA filing completing by end of March 2026. With BTD, priority review voucher, and accelerated approval pathway, this is a high-probability T1 or T2 candidate. Score via `odin_score` as soon as BLA is confirmed filed.

7. **Decide on LGB Challenger** — Now 24 days idle at round 241/721. With the orforglipron PDUFA approaching, a decision is needed: (a) restart optimizer from round 242, (b) declare WF AUC 0.8852 as the LGB ceiling and retire, or (c) investigate process termination. At round 241 the WF AUC improvement curve had flattened — suggest declaring LGB ceiling and closing out the challenger run.

8. **Draft ODIN v6.1 production deployment plan** — MCP still runs ODIN v5. Migration plan to v6.1 Ridge weights is overdue given April 10 PDUFA urgency. The v6.1 deploy config is self-contained and drop-in capable.

---

## 8. System Health

| Component | Status | Notes |
|-----------|--------|-------|
| ODIN v6.1 deploy config | ✅ OK | Brier 0.1102, AUC 0.897, 32 features — unchanged |
| GUNGNIR v30.1 deploy config | ✅ OK | Brier 0.1008, 26 features — unchanged |
| LGB Challenger optimizer | ⏸️ IDLE | Round 241/721, WF AUC 0.8852, last run 2026-03-01 (24 days) |
| Model registry | ✅ OK | 8 champion checkpoints (rounds 1–241) + 7-model ensemble pool |
| 9realms MCP | 🔴 DISABLED | Connector blocked — all scoring tools unavailable |
| FinBrain MCP | 🔴 BROKEN | Pydantic schema bug — 11th consecutive failed run |
| ClinicalTrials.gov MCP | 🔴 DEGRADED | New schema mismatch error (`pagedStudies`) — regression from v11 |
| Perplexity MCP | ✅ OK | Functional — used for catalyst research this run |

---

## 9. Δ Changes vs v11

- **⚠️ CRITICAL CORRECTION**: March 28 PDUFA was for LLY orforglipron, NOT VRTX. ALYFTREK was already approved December 20, 2024. All prior v11 VRTX PDUFA urgency flags were incorrect.
- **🆕 LLY orforglipron PDUFA date**: Extended to April 10, 2026 (from March 28). Now 16 days away.
- **🆕 ACHIEVE-3 results confirmed**: Orforglipron beat oral semaglutide head-to-head on all endpoints. Published in *The Lancet* February 26, 2026. Positive GUNGNIR scoring candidate.
- **🆕 VRTX povetacicept**: BLA filing completing ~March 30, 2026. PDUFA expected ~September 2026. New ODIN T1–T2 candidate added to pipeline.
- **🆕 ABBV insider selling**: SVP David Purdue sold $1.22M (5,230 shares) on March 4, 2026 — 66% reduction in personal holding.
- **ClinicalTrials.gov MCP**: Regressed from ✅ OK to 🔴 DEGRADED — new `pagedStudies` schema error.
- **Models**: No changes. Champions remain ODIN v6.1 / GUNGNIR v30.1.
- **Optimizer**: No new checkpoints. Still at round 241/721.

---

*Report v12 generated automatically by scheduled monitor task. Next run: confirm orforglipron PDUFA outcome (April 10, 2026), re-attempt MCP connection fixes, confirm povetacicept BLA filing status, score both catalysts via ODIN/GUNGNIR upon MCP restoration.*

*⚠️ Disclaimer: All model outputs are informational/educational and do not constitute investment advice.*
