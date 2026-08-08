# DAILY UW FLOW MONITOR — 2026-05-29 (Fri full-session vs Thu 2026-05-28)

**Run type:** scheduled_daily_uw_flow_monitor (autonomous, no user present)
**Per:** Amendment 034 (Daily Autoscan Persistence) + Amendment 033 (Cowork Dropbox) + Daily UW Flow Monitor task spec
**Data source:** `mcp__9realms__uw_flow_features` — public Unusual Whales options/darkpool readings, full Friday regular session. No fabrication, no simulation.
**T-1 compliance:** All inputs are publicly observable pre-catalyst flow data. Snapshot persisted to `/Odin Perfection/uw_daily_snapshots.json` (snapshot #20).
**Snapshot integrity (SHA-256):** `393dedf09a32bfb0cfe73d279db75679e83c3b7365d606d09e7e683a7cd29a19`

---

## VERIFIED FACTS

Classifications vs Thu 2026-05-28 baseline (16-ticker monitor list):

| Class | Count | Tickers |
|---|---|---|
| 🔴 RED | 4 | MNKD, ARQT, ZBIO, AXSM |
| 🟡 YELLOW | 5 | CRDF, CABA, TSHA, AVTX, WVE |
| 🟢 GREEN / GREEN_IMPROVING | 5 | ACHV, VERA↑, UNCY↑, NMRA↑, VRDN↑ |
| ⚪ NA (illiquid) | 2 | IRON, TRDA |

**Key continuity:** None of the 4 RED flags are confirmed current core holdings — all are watchlist/candidate names. The two held names that registered a flow signal both moved the *right* way or stayed benign: **UNCY (held) sharply recovered RED→GREEN_IMPROVING**; **CRDF (held) is YELLOW (mild call distribution, not a bearish rotation)**.

### 🔴 RED — bearish smart-money rotation (CMPX pattern)

**AXSM** — *HIGHEST PRIORITY. Listed "imminent catalyst."*
`CALL_PREM_FLIP(+84,328→−98,081); PUT_BUYING(put_ab 3.17→2.38, +$109,349 puts bought); CALL_AB_COLLAPSE(1.90→0.11); BMB_FLIP(+57,568→−207,430); DARKPOOL 2.2×`
- Largest-magnitude rotation in the panel and a textbook sell-the-news flip: the big bullish call buying that carried Thursday's +$57K bmb vanished and reversed to aggressive call selling + heavy put buying. Bull-minus-bear swung −$265K in one session.
- **Action:** Watchlist candidate — **STAND ASIDE / NO ENTRY.** If any residual exposure exists, this is the protocol "trim 30–50% / tighten stop" signal.

**MNKD** — *PDUFA ahead. Confirms 5/28 pre-registered downgrade.*
`PUT_BUYING(put_ab 0.44→2.18, aggressive); DARKPOOL 6.9× ($181K→$1.24M); BMB −125,556 (deep negative); call_vol_z +6.88 with negative call premium = call selling into volume`
- Thursday's report pre-registered: "if call premium stays sub −$100K, downgrade to YELLOW." Today it is −$130K **and** put buying flipped aggressive **and** darkpool surged ~7× → escalate past YELLOW to RED.
- **Action:** Watchlist candidate — **STAND ASIDE.** The aggressive put bid + darkpool block surge is the institutional distribution footprint.

**ARQT**
`CALL_PREM_FLIP(+8,775→−11,180); BMB_FLIP(pos→neg); CALL_AB_COLLAPSE(0.72→0.014, near-total call selling at bid); DARKPOOL 3.6× ($57K→$205K)`
- Clean three-flag bearish cluster. call_ab 0.014 = calls being dumped into the bid.
- **Action:** Watchlist candidate — **STAND ASIDE.**

**ZBIO** — *thin name, low absolute conviction.*
`PUT_BUYING(put_ab 0.01→3.75, aggressive); PUT_PREM(−$9,302→+$12,455); BMB_FLIP(+7,792→−12,455)`
- Genuine directional bearish put rotation, but on a thin chain (alerts_5d=19, no call volume, ~$12K absolute). Directional signal is real; size of conviction is small.
- **Action:** Watchlist candidate — **STAND ASIDE.** Re-check; don't over-weight given thinness.

### 🟡 YELLOW — weakening / watch

- **CRDF** (GREEN_IMPROVING→YELLOW) — Call premium evaporated +$2,759→+$43 on *high* call volume (cvz +2.98) with call_ab 0.71 (<1 = selling at bid) = mild call distribution. Bmb still +359, no put buying, so not a bearish rotation. **HELD position (inferred) — monitor, no action.**
- **CABA** (GREEN_IMPROVING→YELLOW) — Minor net call-prem flip +$14,035→−$3,380, BUT offset: call_ab *rose* 2.29→3.49 (aggressive call buying), puts sold (put_ab 0.74), bmb stays +8,765. **Not** a CMPX pattern. **HELD position (inferred) — low concern.**
- **TSHA** — Darkpool **9.1× surge** ($19K→$173K) is the real signal but direction unknown (no NBBO). The call-prem flip +$1,050→−$2,963 is on near-zero volume (cvz −0.98 = noise). Watch; pull `uw_darkpool_ticker` NBBO if it persists.
- **AVTX** — Conflicting: put side rotated from extreme selling (−$229,793) to buying (+$59,198) and bmb flipped +$236K→−$59K, but call_ab is still 7.12 (calls bought) and put_ab only 0.99 (neutral, not aggressive). Thin. **Remains OUT OF SCOPE** (preclinical/nano pattern per `feedback_no_preclinical_nanocap_rockets`).
- **WVE** — Persistent net call selling, 3rd session (−$27,624→−$20,644, slightly less negative). put_ab rose 0.27→0.73 (puts less sold). No acute flip. Mild bearish drift — monitor.

### 🟢 GREEN / notable upgrades

- **UNCY** (RED→GREEN_IMPROVING) — **Sharp bullish reversal.** Call premium −$14,379→**+$357,215**, call_vol_z **+11.94** (massive accumulation), bmb +$356,595. **HELD concentrated-regime position (PDUFA Jun 29).** Flow conviction returned hard after two deteriorating sessions. Cardinal exit unchanged (T−5).
- **VERA** (RED→GREEN_IMPROVING) — Recovered: call prem −$1,489→+$5,968, put fear gone (put_ab 0.60→0.25). call_ab 0.434 still soft but bmb positive and improving.
- **VRDN** (GREEN_IMPROVING) — Strong acceleration: call prem +$6,763→**+$51,347**, call_ab 4.07 (very aggressive buying). DP 4.7× surge *with* bullish flow = accumulation. GEX slightly negative = up-move amplifier.
- **NMRA** (GREEN_IMPROVING) — Heavy put selling (put_ab 0.12) flipped bmb −$5,686→+$44,678.
- **ACHV** (GREEN) — Stable clean bullish (+$15,540, call_ab 1.78).

### ⚪ NA — illiquid, no tradable options signal

- **IRON** — Zero options flow today; darkpool normalized $180K→$62K.
- **TRDA** — Negligible (alerts_5d=0, premiums ~$0).

---

## INFERRED INTERPRETATION

1. **The RED cluster is concentrated in watchlist candidates, not the book.** AXSM, MNKD, ARQT, ZBIO are all names we are *not* confirmed to hold. The signal here is "do not initiate," not "trim." That keeps the framework's no-overrides discipline intact — there is nothing to act on defensively in the core book today.
2. **AXSM is the cleanest CMPX archetype this week** — bullish call positioning fully reversed to call-selling + put-buying in one session ahead of an imminent catalyst. This is exactly the rotation the monitor was built to catch (the original CMPX Friday→Monday flip). Highest-priority "no-entry" name.
3. **MNKD's downgrade was correctly pre-registered Thursday and tripped Friday** — the monitor's day-over-day memory worked as designed. The escalation (YELLOW→RED) is driven by the put_ab flip + 6.9× darkpool, not just the persistent negative call premium.
4. **UNCY's recovery is the most important read for the book.** A held concentrated position that was RED for two sessions snapped back to a +$357K call-premium accumulation day with an 11.9σ call-volume z-score. This relieves the Thursday concern about call-side conviction draining pre-PDUFA. Still exit on the runup (T−5), not through the event.
5. **VERA + CRDF show the value of day-over-day classification** — VERA's Thursday RED was a one-session blip (now recovered), and CRDF's downgrade is mild distribution, not rotation. The monitor is separating noise from genuine rotation reasonably well.

---

## UNRESOLVED GAPS

- **No NBBO direction on darkpool surges (TSHA 9.1×, MNKD 6.9×, VRDN 4.7×, ARQT 3.6×, AXSM 2.2×).** Darkpool prints have no inherent buy/sell sign without NBBO context. MNKD/ARQT/AXSM lean bearish only because they cluster with directional options flow; TSHA's surge is standalone and therefore direction-unknown. If TSHA stays YELLOW, pull `uw_darkpool_ticker` with NBBO.
- **Run timing:** executed ~6:40pm ET (post-close), so these are full-session aggregates, not a true 3:30pm intraday capture. The "last 4–6 hours pre-event" micro-rotation that the CMPX case turned on is not resolvable from EOD aggregates — only the day-level rotation is.
- **UNCY GEX = 0** (thin chain) — no dealer-hedging read; flow is the only signal.
- **Position status is inferred** from recent session memory (UNCY/CAPR/CRDF locked duo per 5/25; CABA per April book), **not independently verified today.** Holdings should be confirmed against the live ledger before any action.

---

## RED-TEAM OBJECTIONS

- **Mechanical thresholds over-fire on thin names.** ZBIO (alerts 19, ~$12K) and TSHA (cvz −0.98) trip flags on negligible volume. ZBIO kept RED only because put_ab 3.75 is genuinely directional; TSHA was held at YELLOW precisely because its "flip" is noise-level. Do not size off thin-name flags.
- **Darkpool ≠ direction.** Treating darkpool surges as bearish is an assumption; they could be accumulation. Flagged as a gap above, not asserted as fact.
- **call_ab can mislead on covered-call writing.** ARQT's call_ab 0.014 and CRDF's sub-1 call_ab could partly reflect buy-write/overwriting, not pure bearish distribution. The bmb flip (ARQT) is the harder confirmation; CRDF's bmb stayed positive, hence YELLOW not RED.
- **GREEN_IMPROVING ≠ buy signal.** UNCY/VRDN bullish accumulation does not change the Cardinal Rule (no hold-through binary) or the no-overrides directive. Flow improving is not an entry trigger by itself.
- **Survivorship in the baseline:** the prior-day classifications I compared against were themselves model outputs (e.g., MNKD was labeled GREEN Thursday despite −$157K call premium). I re-derived from raw deltas, not prior labels, to avoid inheriting a mislabel.

---

## NEXT-SESSION ACTION ITEMS

1. **AXSM, MNKD, ARQT, ZBIO** — keep on NO-ENTRY until flow stabilizes. Re-check Monday; AXSM first (imminent catalyst).
2. **TSHA** — if YELLOW persists, pull `uw_darkpool_ticker` NBBO to resolve the 9.1× darkpool surge direction.
3. **UNCY (held)** — flow conviction restored; maintain plan, Cardinal exit T−5 before Jun 29 PDUFA. Do not add on strength.
4. **CRDF (held)** — monitor the mild call distribution; downgrade to RED only if bmb turns negative with a put-side bid.
5. Confirm live holdings against the ledger before treating any RED as a "trim" vs a "stand-aside."

---

**Compliance attestation:** Real-data-only directive honored — all flow values are live Unusual Whales readings; no estimates or fabrications. Output separated into Verified / Inferred / Gaps / Red-Team per Amendment 015 + IMMUTABLE_real_data_only. Snapshot #20 persisted; SHA-256 `393dedf09a32bfb0cfe73d279db75679e83c3b7365d606d09e7e683a7cd29a19`. Mirrored to `/9realms/odin_cowork_dropbox/` per Amendment 033.
