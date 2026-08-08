# Daily UW Flow Monitor — Smart Money Rotation Detection (Cowork dropbox mirror)

- **Date:** 2026-06-02 (Tuesday) · **Run:** 15:30 ET scheduled pulse
- **Scan type:** uw_flow_monitor · **Run type:** DAILY_DIFF_VS_2026-05-29 (TUE vs FRI; Mon 6/1 not scanned → 2-session delta)
- **Source:** `mcp__9realms__uw_flow_features` (UW addon v1.0, HTTP 200) · **Universe:** 16 active T-21 names
- **Primary write:** `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/2026-06-02_uw_flow_monitor.md` · **Snapshot:** `/Odin Perfection/uw_daily_snapshots.json`

## BOTTOM LINE
5 RED / 6 YELLOW / 4 GREEN / 1 NA. Two textbook CMPX flips on possibly-held names: **CABA** (call distribution into EULAR 6/4, T-2) and **VRDN** (call flip + 4.4x dark-pool surge + negative GEX). **MNKD's** record -$602K call dump is **non-actionable** — it was APPROVED 5/29 (post-event unwind). Held concentrated **UNCY** cooled 96% off its 5/29 spike but is not yet a sell trigger.

## VERIFIED FACTS (live UW data)
UW HTTP 200; all 16 tickers returned data, **no 503s** (TRDA had zero options flow → 10 features).

| Ticker | Class | Prior | net_call$ | bmb$ | call_ab | put_ab | DP 5d | Note |
|---|---|---|---|---|---|---|---|---|
| MNKD | RED_DEEPENING | RED | -602,575 | -598,953 | 0.34 | 1.05 | 164,512 | Largest dump ever — POST-APPROVAL, non-actionable |
| ACHV | RED_FLIP | GREEN | -45,345 | -45,390 | 0.31 | 1.0 | 0 | Call flip +15.5K→-45K; PIPE overhang |
| CABA | RED_FLIP | YELLOW | -25,571 | -24,437 | 0.63 | 0.0 | 82,670 | HELD; flip into EULAR 6/4 (T-2) |
| TSHA | RED_DEEPENING | YELLOW | -18,123 | -18,123 | 0.10 | 1.0 | 68,042 | 90% of calls hit bid |
| VRDN | RED_FLIP | GREEN_IMPR | -22,082 | -10,132 | 0.68 | 0.0 | 339,816 | CMPX cluster + neg GEX -7,634 |
| CRDF | YELLOW | YELLOW | -1,814 | +2,818 | 0.50 | 0.04 | 0 | HELD; mild call distribution, tiny |
| ARQT | YELLOW | RED | +453 | +238 | 2.0 | 1.0 | 383,691 | Tiny flip + DP +87% (30 prints) |
| ZBIO | YELLOW | RED | -605 | +12,725 | 0.30 | 0.78 | 44,963 | Put fear unwound; no call demand |
| UNCY | YELLOW_COOLING | GREEN_IMPR | +12,602 | +9,794 | 1.90 | 7.5 | 17,520 | HELD; -96% off spike + put_ab 7.5 |
| AXSM | YELLOW_MIXED | RED | +101,288 | +1,862 | 2.19 | 4.73 | 68,123 | $101K calls + $99K puts = straddle |
| AVTX | YELLOW_THIN | YELLOW | +9,051 | +858 | 7.25 | 2.35 | 7,984 | Thin two-sided; OUT OF SCOPE |
| NMRA | GREEN | GREEN_IMPR | +13,680 | +19,566 | 32.08 | 0.52 | 0 | Extreme bid-lift + puts sold |
| WVE | GREEN_IMPROVING | YELLOW | +458 | +7,376 | 1.15 | 0.44 | 160,722 | bmb flip + vol/DP surge |
| VERA | GREEN_CAVEAT | GREEN_IMPR | +14,614 | +11,130 | 1.43 | 7.0 | 44,227 | Bullish calls; put_ab 7.0 caveat |
| IRON | GREEN_LOW_CONV | NA | +6,402 | +6,402 | 5.0 | 1.0 | 13,627 | Bullish emergence, low volume |
| TRDA | NA | NA | 0 | 0 | 1.0 | 1.0 | 17,710 | Illiquid |

## INFERRED INTERPRETATION
- **3 new RED flips:** ACHV, CABA, VRDN.
- **CABA (held, top priority):** bmb +$8,765 → -$24,437, call_ab 3.49 → 0.63, puts closed — pre-event de-risk into EULAR 6/4 RESET-SLE/SSc. Cardinal Rule already mandates exit before the binary.
- **VRDN (high priority):** cleanest CMPX cluster — call flip, DP +340% (14 prints), volume surge, negative GEX (dealers short gamma → downside acceleration).
- **MNKD non-actionable:** approved 5/29; -$602K dump is post-approval unwind, not held.
- **UNCY (held concentrated, watch):** 5/29 was an 11.9σ anomaly; today normalizes to ordinary bullish + minor put hedge. Not a sell trigger. Cardinal exit T-5.
- **Bullish:** NMRA (call_ab 32 + puts sold, imminent readout), WVE (bmb flip + surge), VERA (bullish calls, positive FDA-alignment 8-K, PDUFA 7/7).

## UNRESOLVED GAPS
- Mon 6/1 not scanned → 2-session delta. Dark-pool direction unknown for VRDN/ARQT/WVE (no NBBO). UNCY exact PDUFA date ambiguous (Jun 27 vs 29). Held-status of CRDF inferred.

## RED-TEAM OBJECTIONS
- MNKD is a rotation false-positive (post-approval) — interpretation overrides the raw RED.
- CABA flip could be position-squaring, but bmb sign-flip + imminent binary make de-risk the conservative read.
- Thin-name extreme ratios (UNCY/VERA put_ab 7.0–7.5) are on tiny put dollars = flags, not dollar-weighted bearishness.
- AXSM "recovery" is a two-sided straddle, not directional.

## ACTIONABLE
1. **CABA — REVIEW POSITION (held):** trim/exit before EULAR 6/4 per Cardinal Rule.
2. **VRDN — REVIEW POSITION:** trim 30–50% if held; tighten stop; pull NBBO next session.
3. **UNCY (held) — monitor:** confirm PDUFA date; Cardinal exit T-5.
4. **CRDF (held) — monitor:** ASCO 6/2 sell-the-news fade; plan Cardinal exit.
5. **NMRA — track** (GREEN flow, imminent); any entry must pass stacked-signal + hash-ledger gate.
6. **MNKD — no action** (approved; drop from pre-event watch).

## COMPLIANCE
Real data only; no fabrication. Verified/Inferred/Gaps/Red-Team separated per Amendment 015. Snapshot JSON-validated (21 entries; a transient NUL-padding write artifact was repaired this run). No trades executed. Today snapshot SHA-256: `e543a88aecba98eca9b616d9b0e5a1bb43d7f46d97a69a999971ef6dfc1910ed`.
