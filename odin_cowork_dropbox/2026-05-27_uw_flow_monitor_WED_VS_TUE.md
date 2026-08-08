# DAILY UW FLOW MONITOR — 2026-05-27 (WED vs TUE)

**Scan type:** Smart-money rotation pulse check (CMPX-pattern detector).
**Compared:** 2026-05-27 (today) vs 2026-05-26 (prior trading day).
**Universe:** 16 active T-21 candidates across PDUFAs / readouts / imminent catalysts.
**Headline:** **RED=5  YELLOW=2  GREEN=9** — heavy bearish rotation across CRDF / ACHV / TSHA / AVTX / WVE.

---

## Verified facts

Source: Unusual Whales `uw_flow_features` (live MCP pull) at 2026-05-27 ~3:30pm ET. T-1 compliant: all features are public UW endpoint readings from today's session.

| Ticker | Class | NetCallPrem | NetPutPrem | CallAB | PutAB | CallVol-Z | GEX | DP 5d |
|--------|-------|------------:|-----------:|-------:|------:|----------:|----:|------:|
| CRDF | **RED** | -12,587 | 896 | 0.15 | 11.00 | +0.38 | 349,376 | 51,401 |
| MNKD | **YELLOW** | -251,581 | -2,504 | 1.48 | 0.47 | +0.71 | 566,903 | 30,000 |
| ACHV | **RED** | -37,241 | 0 | 0.21 | 1.00 | -0.24 | 23,504 | 0 |
| VERA | **GREEN** | 13,813 | 13,958 | 2.39 | 5.23 | -0.26 | 55,922 | 79,645 |
| ARQT | **GREEN** | 5,327 | -1,520 | 1.42 | 0.00 | -0.83 | 108,669 | 69,788 |
| UNCY | **GREEN** | -12,313 | 6,837 | 0.45 | 0.82 | +1.57 | 0 | 25,000 |
| IRON | **GREEN** | 225 | 0 | 1.00 | 1.00 | -0.99 | 22,242 | 4,787 |
| CABA | **GREEN** | 27,075 | 2,953 | 1.28 | 5.27 | +0.27 | 139,530 | 380,224 |
| TRDA | **GREEN** | -37 | 0 | 0.00 | 1.00 | -0.93 | 920 | 0 |
| NMRA | **GREEN** | -9,807 | -47 | 0.10 | 0.00 | -0.69 | 243,824 | 0 |
| TSHA | **RED** | -8,820 | -747 | 0.02 | 0.20 | -0.89 | 980,850 | 18,590 |
| VRDN | **GREEN** | -2,856 | 300 | 0.80 | 1.00 | -0.16 | -14,741 | 43,230 |
| AVTX | **RED** | 140 | 8,148 | 1.00 | 36.67 | -0.99 | 5 | 25,192 |
| ZBIO | **YELLOW** | -6,305 | -455 | 0.00 | 1.88 | -0.41 | 230 | 11,536 |
| WVE | **RED** | -11,834 | 7,841 | 0.31 | 32.17 | -0.93 | 15,972 | 50,395 |
| AXSM | **GREEN** | 54,694 | -9,354 | 1.09 | 6.69 | -0.48 | 594 | 119,828 |

Snapshot saved to `uw_daily_snapshots.json` (now 18 entries).

---

## Inferred interpretation

Five names flipped or worsened to RED today, the highest count since the 5/22 RED=6 rotation that preceded the Memorial-Day weekend. The defining pattern is **aggressive put buying at the ask combined with collapsing call premium**:

- **CRDF (RED, was GREEN)** — Cleanest CMPX-pattern flip. Yesterday: +$5,415 net call premium with call A/B 7.19 (anyone could see the bullish positioning). Today: net call premium flipped to -$12,587 AND put A/B exploded from 0.15 to 11.00. Two-axis simultaneous reversal. Call vol z-score still positive (+0.38) so volume is THERE — it just rotated direction. PDUFA is the imminent catalyst; this is the textbook sell-the-news warning. **Action: review CRDF position; consider trimming or tightening stop ahead of next session.**
- **ACHV (RED, was YELLOW)** — Call premium flipped +$484 → -$37,241 (huge magnitude relative to ticker). Call A/B collapsed 1.36 → 0.21 (sellers hitting bid). Already on Pre-Investment Discovery BLOCK per prior session memory; this is corroborating, not actionable for new entry.
- **TSHA (RED, was YELLOW)** — Call premium +$1,117 → -$8,820, call A/B collapsed 5.00 → 0.02 (extreme call selling). GEX expanded $695K → $980K but the directional signal is unambiguously bearish despite the dealer hedge support. **Action: review TSHA position size.**
- **AVTX (RED, was RED)** — Stayed RED with put A/B JUMP 3.79 → 36.67 — extreme aggressive put buying second day running. Net call premium did rebound +$140 (cosmetic) but offset by +$8,148 net put premium. Call vol z-score collapsed -0.12 → -0.99 (smart money exited calls). **Action: AVTX position should already be flat or being trimmed per prior RED.**
- **WVE (RED, was GREEN)** — Surprise rotation. Put A/B 0.01 → 32.17 (massive aggressive put bid-hit). Call vol z-score +0.16 → -0.93 — biggest single-day call-volume collapse on the board. Imminent catalyst per monitor list. **Action: review WVE position.**

YELLOWS:
- **MNKD** — Call premium kept deteriorating from already-bad -$89K to -$252K. Put A/B normalized 1.77 → 0.47 (not aggressive put buying), so this is more "calls getting sold" than "puts getting bought". One-axis bearish, not the full CMPX pattern. Watch.
- **ZBIO** — Mild deterioration; put A/B rose 0.66 → 1.88 (warning shot, not yet a jump).

GREENS WORTH FLAGGING:
- **UNCY** — Net call premium still negative -$12K but call_vol_z RECOVERED -0.43 → +1.57 (volume is back). Net put premium did flip -$7,277 → +$6,837 which is bullish (puts being sold). Mixed but improving. Position context: UNCY is a primary concentrated holding per [[concentrated_account_regime_2026-05-18]].
- **CABA** — Net call premium +$27K, call A/B 1.28, sweep ratio 14% — clean bullish on the call side. Put A/B 5.27 is elevated but net put premium is also positive +$2,953 (puts being sold not bought). Healthy.
- **AXSM** — Biggest absolute net call premium on the board (+$54,694) and net put premium negative (-$9,354) = clean bullish two-axis.

---

## Unresolved gaps

- **Timestamp granularity:** UW MCP returns end-of-day cumulative; cannot decompose "last 4-6 hours" the way the CMPX postmortem identified. RED flips here are EOD net — directionally aligned with CMPX-style risk but not as precise. Intraday tooling would tighten the window.
- **Position sizes not in scope:** Task does not include account state, so "trim 30-50%" recommendations are advisory; David needs to size against actual cost basis at next session open.
- **CRDF prior class was GREEN with call A/B 7.19** — that prior-day reading was itself an outlier (extreme bullish). The reversal is large in part because the starting point was extreme. Mean-reversion alone could explain part of the flip; CMPX-pattern interpretation is the conservative read.
- **AVTX put A/B 36.67** — this kind of ratio implies tiny volume on the other side; with low absolute volumes a single block can dominate the ratio. Validate against absolute notional before sizing decisions.
- **TRDA** has effectively zero options activity (alerts_5d=0). GREEN classification is a default, not a positive signal.

---

## Red-team objections

- **Calibration risk:** Classification thresholds are heuristic, not backtested against a forward-return panel. Prior monitors have produced RED=6 days followed by no catalyst burn — base rate of false positives is non-trivial.
- **Date verification not done here:** Task is flow-only; we have NOT re-verified catalyst dates today per [[feedback_verify_pdufa_dates_2026-05-21]]. Any "act before next session" framing assumes the catalyst window hasn't already passed. CRDF / MNKD / ACHV / WVE catalysts should be re-confirmed before sizing changes.
- **Override risk per [[feedback_no_more_overrides_2026-05-19]]:** This scan is informational. It does NOT authorize new entries. It can support trim/exit decisions on already-open positions per Cardinal Rule (no hold-through binary) but cannot justify reversal trades.
- **Single-day comparison limitation:** A T-1 vs T-0 flip is one data point. Sustained 2-day rotation is the higher-conviction signal. Re-running tomorrow (5/28) will tell us whether CRDF/WVE/TSHA hold the bearish posture.
- **GEX interpretation:** Several names show GEX expanding alongside bearish flow (CRDF, TSHA, MNKD). Positive GEX typically means dealers absorb moves — the flow's bearish signal is therefore partially dampened by dealer mechanics. AVTX GEX is effectively zero, so put-buying there has no dealer cushion.

---

## NEXT-SESSION ACTION ITEMS

1. **CRDF** — Two-axis CMPX-pattern flip (call prem flipped + put A/B jumped 73x). REVIEW position size pre-open; consider trim 30-50% or tighter trailing stop. Re-verify CRDF PDUFA date and remaining DTE before action.
2. **WVE** — Surprise GREEN→RED rotation with biggest call-volume collapse (Δ -1.09 std). REVIEW; same trim/stop calculus as CRDF.
3. **TSHA** — Call A/B collapsed 5.00 → 0.02. REVIEW position; even with positive GEX support, directional flow is unambiguous.
4. **AVTX** — Second day RED with put A/B doubling 3.79 → 36.67. If still open, exit per prior session's RED.
5. **ACHV** — Already on Pre-Investment Discovery BLOCK (no entry); no portfolio action needed, but record as confirming the BLOCK.
6. **MNKD / ZBIO** — Watch; one more day of deterioration would trip to RED.
7. **Tomorrow (Thursday 5/28):** Re-run monitor; persistence of RED flags across two sessions is the higher-conviction signal vs single-day flip.
8. **Cross-check:** Mirror this file to `/9realms/odin_cowork_dropbox/` per Amendment 033 and to `/9realms/daily_scans/` per Amendment 022.

---

## Compliance attestation

- [x] **Amendment 015** — Output structured as Verified / Inferred / Gaps / RedTeam / Actionable.
- [x] **Amendment 022** — File will be mirrored to `/9realms/daily_scans/daily_news_scan_2026-05-27.md` companion (this is a flow scan not a news scan; mirroring as `uw_flow_monitor` variant).
- [x] **Amendment 033** — File will be mirrored to `/9realms/odin_cowork_dropbox/2026-05-27_uw_flow_monitor.md`.
- [x] **Amendment 034** — Dated `.md` written to `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/2026-05-27_daily_uw_flow_monitor.md`.
- [x] **IMMUTABLE REAL DATA ONLY (2026-05-15)** — All values from live UW MCP pull; no estimates; gaps explicitly labeled.
- [x] **Amendment 019 (no overrides)** — Scan is informational; does not propose new entries.
- [x] **Amendment 031 (concentrated regime)** — Recommendations are trim/exit only on existing positions; no new entries proposed.

Chain master (placeholder for next ledger append): to be hashed at session end.

---

## Source links

- Live MCP pull: `mcp__9realms__uw_flow_features` × 16 tickers, 2026-05-27 ~3:30pm ET.
- Prior baseline: `/Odin Perfection/uw_daily_snapshots.json` entry `2026-05-26`.
- Persisted snapshot: `/Odin Perfection/uw_daily_snapshots.json` entry `2026-05-27` (18 total).
- Task spec: scheduled-task `daily-uw-flow-monitor` (per uploads/SKILL.md).
