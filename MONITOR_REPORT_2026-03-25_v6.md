# ODIN v6 / GUNGNIR v30 — Optimization Monitor Report
**Date:** 2026-03-25 (Automated Run v6)

---

## 1. Model Champion Status — No Changes

### ODIN v6.1 (CHAMPION)
| Metric | Value |
|--------|-------|
| Brier | **0.1102** |
| AUC | 0.897 |
| Features | 32 (Ridge C=15, forward-selected) |
| vs v5 production | **+8.9% Brier improvement** |
| vs v6.0 (65-feature ensemble) | v6.0 regressed at 0.1378 — confirmed dead |

### GUNGNIR v30.1 (CHAMPION)
| Metric | Value |
|--------|-------|
| Brier | **0.1008** |
| Features | 26 (Ridge 70% + Trees 30% blend) |
| vs v29 production | **+56.9% Brier improvement** |
| vs v30.0 (109-feature ensemble) | v30.0 at 0.1394 — confirmed dead |

**Delta since v5 report:** No new deploy configs, no new optimizer checkpoints, no model changes. Champions stable.

---

## 2. Autonomous Optimizer — Idle

- **LGB Champions directory:** 8 champion checkpoints (rounds 1→241), last updated 2026-03-01
- **Model Registry:** v2 weights from 2026-02-28, CURRENT_BEST.pkl unchanged
- **No logs/ directory found** — optimizer is not running
- **LGB best Brier (0.2057)** remains far worse than Ridge v6.1 (0.1102)

**Verdict:** Autonomous optimizer has been idle for 24 days. No further LGB exploration warranted — Ridge dominates this problem class.

---

## 3. MCP Tool Status

| Tool | Status | Change |
|------|--------|--------|
| 9realms MCP (odin_score, gungnir_score, system_status) | **DISABLED** | No change — still disabled in connector settings |
| FinBrain MCP (insider, sentiment, analyst) | **PARAMETER ERROR** | No change — Pydantic model validation rejects all calls |
| ClinicalTrials.gov MCP | **WORKING** | Confirmed operational |

**Action still required:** Re-enable 9realms MCP tools and fix FinBrain parameter schema.

---

## 4. ClinicalTrials.gov — Live Validation

### VRTX — Vanzacaftor/Tezacaftor/Deutivacaftor (PDUFA 2026-03-26 — TOMORROW)
| NCT ID | Study | Status | Enrollment |
|--------|-------|--------|------------|
| NCT05844449 | Phase 3 long-term safety/efficacy (≥1yr) | Enrolling by invitation | 174 |
| NCT06154447 | Phase 1 VX-828 (next-gen CFTR) | Recruiting | 255 |
| NCT07349394 | Phase 1 DDI (rosuvastatin) | Active, not recruiting | 18 |
| NCT06299709 | Bioavailability/food effect | Completed | 34 |
| NCT05867147 | QT/QTc interval study | Completed | 56 |

**Assessment:** Pipeline clean. Phase 3 OLE ongoing with no safety signals flagged. Phase 1 next-gen (VX-828) recruiting normally. PDUFA decision is tomorrow — this should be a high-conviction T1 event given Vertex's strong regulatory track record with CFTR modulators.

### LLY — Orforglipron (Phase 3 Readouts)
| NCT ID | Study | Status | Enrollment |
|--------|-------|--------|------------|
| NCT05869903 | ATTAIN-1: Obesity/overweight + comorbidities | Active, not recruiting | 3,127 |
| NCT05872620 | Obesity + T2D | **Completed** | 1,613 |
| NCT06109311 | T2D + insulin glargine | **Completed** | 546 |
| NCT07153471 | Obesity + OA knee | Recruiting | 800 |

**Assessment:** Two pivotal trials completed. ATTAIN-1 (3,127 patients) past primary completion date (2025-07-25) — topline data likely already disclosed or imminent. Massive enrollment signals Lilly confidence. This is a marquee GUNGNIR scoring opportunity once MCP is re-enabled.

---

## 5. Key Insights This Cycle

1. **No model drift detected.** Deploy configs unchanged, champion Briers stable at 0.1102 (ODIN) and 0.1008 (GUNGNIR).
2. **VRTX PDUFA tomorrow (3/26).** Unable to score via MCP due to disabled tools. Manual scoring recommended.
3. **FinBrain MCP remains broken.** Insider transaction, sentiment, and analyst rating pulls all fail with Pydantic validation errors. The `req` parameter schema appears to not expose the inner model fields.
4. **LGB optimizer has been idle 24 days.** No new exploration since round 241. This is appropriate — Ridge is the winning architecture.

---

## 6. Recommended Actions (Priority Order)

1. **URGENT: Score VRTX PDUFA manually** — Decision is tomorrow. Use v5 production weights if MCP stays disabled.
2. **Re-enable 9realms MCP tools** in connector settings to restore automated scoring.
3. **Investigate FinBrain MCP parameter schema** — the `req` parameter needs proper field exposure (ticker, format, limit).
4. **Validate GUNGNIR v30.1 on live 2026 readouts** — 56.9% improvement needs out-of-sample confirmation before production deployment.
5. **Deploy ODIN v6.1 to MCP server** — consistent +8.9% improvement, architecturally sound (Ridge, not fragile ensemble), same feature family as v5.
6. **Archive v6.0 and v30.0** — both confirmed dominated by their leaner successors.

---

## 7. Champion Comparison Summary

```
ODIN:    v5 (0.1210) → v6.0 (0.1378, WORSE) → v6.1 (0.1102, CHAMPION +8.9%)
GUNGNIR: v29 (0.2339) → v30.0 (0.1394, +40.4%) → v30.1 (0.1008, CHAMPION +56.9%)
LGB:     Best 0.2057 after 721 rounds — NOT competitive
```

**Theme: Parsimony wins.** Both champions use ~25-32 features with Ridge as the backbone. The 65-109 feature deep ensembles consistently overfit. This is a strong architectural signal for future model development.

---

*Report generated automatically by ODIN/GUNGNIR Monitor — 2026-03-25 (run v6)*
*Next run: Will re-attempt MCP scoring and check for post-VRTX PDUFA outcome data.*
