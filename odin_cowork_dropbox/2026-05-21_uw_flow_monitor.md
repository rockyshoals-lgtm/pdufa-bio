# UW Flow Monitor — 2026-05-21 (THU vs WED)

**Run date:** 2026-05-21 (~3:30 PM ET)
**Run type:** scheduled_daily_uw_flow_monitor
**Source chat:** cowork_odin_perfection
**Cross-references:** uw_daily_snapshots.json (now 14 snapshots, baseline 2026-04-30)

## Summary

| Bucket | Count | Tickers |
|--------|-------|---------|
| 🟢 GREEN | 8 | ARQT, UNCY, IRON, CABA, TRDA, NMRA, AVTX, WVE |
| 🟡 YELLOW | 7 | CRDF, MNKD, ACHV, VERA, TSHA, VRDN, ZBIO |
| 🔴 RED | 1 | AXSM |

## ✅ VERIFIED FACTS

Pulled live UW flow features for all 16 monitor tickers via `mcp__9realms__uw_flow_features` (UW data ~15-min delayed).

### 🔴 RED — AXSM
- `PUT_AB_JUMP_4.0x` (0.77 → 3.05) — aggressive put buying
- `DP_SPIKE_3.6x` (30,724 → 111,919 5-day dark pool volume)
- Net call premium **-$966,633**, net put premium **+$145,257**, bull-bear **-$1,111,890**
- Action: REVIEW POSITION — trim 30-50% before next session or set tight trailing stop

### 🟡 YELLOW (selected highlights)
- **CRDF** — `PUT_AB_JUMP_11.7x` (0.17 → 2.00). NOTE: catalyst date error in monitor list — actual readout is **June 2**, not May 21 (see `2026-05-21_crdf_event_check.md`)
- **MNKD** (PDUFA 5/29, T-6) — `PUT_AB_JUMP_7.4x` + DP dry-up
- **VRDN** — `CALL_PREM_FLIP_POS_TO_NEG` (+$36K → -$5K) + DP dry-up
- **VERA** — `CALL_PREM_FLIP_POS_TO_NEG`
- **TSHA** — DP dry-up but call_ab aggressive buy (mixed)
- **ZBIO** — `CALL_VOL_Z_DROP_1.73` (3.07 → 1.34) — at the protocol threshold
- **ACHV** — DP dry-up only

### 🟢 GREEN — Notables
- **UNCY** (PDUFA 6/29) — flow within normal band, no rotation
- **CABA** — net call +$14.7K, call AB 2.36 (aggressive buying)
- **AVTX** — bull-bear +$140K (heavy put selling)
- **WVE** — bull-bear +$16.9K, call AB 1.60

## 🔎 INFERRED INTERPRETATION

- ZBIO is one bad session away from a RED flag — watch tomorrow
- MNKD T-7 BIFROST exit window opens 2026-05-22 regardless of UW signal
- AXSM RED pattern matches CMPX postmortem precursor — aggressive put rotation with DP spike
- Multiple call-premium flips today (VERA, VRDN) suggest broader risk-off rotation in mid-cap biotech

## ⚠️ UNRESOLVED GAPS

- AXSM is on monitor list but actual portfolio inclusion is unconfirmed in current Cowork context
- CRDF entry on monitor list was based on stale May 21 date — should be re-anchored to June 2

## 🔴 RED-TEAM OBJECTIONS

1. UW data is ~15-min delayed; intraday final-hour rotation may not be captured
2. Single-day flag is noisy — pattern matters more than one print; cross-check with 2+ days of YELLOW before downgrading to RED
3. PUT_AB_JUMP on near-zero baseline (CRDF $40 of put premium) is statistically weak — flag with care

## Actionable Takeaway

- AXSM: immediate position review if held
- MNKD: tighten stop, T-7 exit window opens tomorrow
- ZBIO: re-scan tomorrow; one more weakening session → RED
- CRDF: re-anchor monitor to June 2

## Sources

- `mcp__9realms__uw_flow_features` (live UW data)
- Prior snapshot: `uw_daily_snapshots.json` entry 2026-05-20
- Companion JSON: `2026-05-21_uw_flow_monitor.json`
