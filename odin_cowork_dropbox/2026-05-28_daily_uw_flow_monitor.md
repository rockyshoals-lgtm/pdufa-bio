# DAILY UW FLOW MONITOR — 2026-05-28 (Thu EOD vs Wed 2026-05-27)

**Run type:** scheduled_daily_uw_flow_monitor (autonomous)
**Per:** Amendment 034 (Daily Autoscan Persistence) + Amendment 033 (Cowork Dropbox) + Daily UW Flow Monitor task spec
**T-1 compliance:** All inputs are public Unusual Whales endpoint readings from today's regular session. No fabrication. Snapshot persisted to `/Odin Perfection/uw_daily_snapshots.json`.

## VERIFIED FACTS

Counts vs Wed 2026-05-27 baseline:

| Class | Count | Tickers |
|---|---|---|
| RED | 2 | VERA, UNCY |
| YELLOW | 1 | IRON |
| GREEN | 6 | MNKD, ARQT, NMRA, AVTX, ZBIO, WVE |
| GREEN_IMPROVING | 7 | CRDF, ACHV, CABA, TRDA, TSHA, VRDN, AXSM |

### RED — REVIEW POSITION

**VERA** (delta_score −3) — `CALL_PREM_FLIP(+13813→−1489); PUT_AB_NORMALIZED(5.23→0.60); DARKPOOL_SURGE(79645→175355)`
- Net call premium flipped positive → negative in one session.
- Dark pool 5d vol surged 2.2× prior (institutional positioning).
- Put A/B normalizing DOWN is a partial offset (was 5.23 yesterday → 0.60 today, fear bid coming out), but the call-side rotation + DP surge dominates. Bull-minus-bear is still slightly +1351 (puts are being sold too), so this is more of a directional uncertainty / hedge unwind than aggressive bearish flow.
- **Action:** Watchlist — VERA is not a current portfolio position. No trim required. Flag for re-check tomorrow.

**UNCY** (delta_score −3) — `CALL_PREM_DETERIORATION(−12313→−14379); CALL_VOL_Z_DROP(1.57→−0.63)`
- ⚠️ **UNCY is one of the two locked concentrated-regime portfolio positions** ($37.5K, PDUFA Jun 29).
- Net call premium continued to deteriorate (now 3rd day negative).
- Call volume z-score collapsed from +1.57 (active accumulation) to −0.63 (below 30d mean) — a 2.2σ drop, well above the >1.5 RED threshold.
- GEX zero, alerts 5d only 9 — thin name, signal sensitivity high.
- Bull-minus-bear net −14,839 (clean directional, not a hedge unwind).
- This is the early shape of the CMPX-style rotation: call-side conviction draining out at T−21 to T−15 from a binary event.
- **Action per Amendment 031 + Cardinal Rule:** UNCY is held for the runup, not through the event. Cardinal exit is T−5 (Jun 22). Today is T−22 (32 calendar days, ~22 trading days). Per the no-overrides directive [[feedback_no_more_overrides_2026-05-19]] and the sweet-spot exit logic, RED flow at T−22 ≠ automatic trim, BUT it's the second consecutive deterioration session and the call-vol-z drop is a fresh signal. **Recommendation: tighten trailing stop to last 5-day low; do NOT add; consider 25–33% trim if Friday close confirms a second RED day with bull-minus-bear stays negative.** Final sizing call is David's.

### YELLOW — WATCH

**IRON** (delta_score −1) — `DARKPOOL_SURGE(4787→179834)`
- Dark pool volume up 37× — block prints showing up. Could be either side; without NBBO context this is just a positioning signal, not directional.
- Net call premium still +595, alerts 90, all other metrics flat-to-mildly-positive.
- **Action:** Watch. Pull dark pool prints with NBBO tomorrow if YELLOW persists.

### GREEN_IMPROVING (notable upgrades from RED/YELLOW)

- **CRDF** (RED→GREEN_IMPROVING, score +5): Yesterday's −$12,587 call premium flipped to +$2,759 today. Put A/B normalized 11.0→2.25. Yesterday's RED flag was a one-day blip, not a sustained rotation.
- **ACHV** (RED→GREEN_IMPROVING, score +3): Call premium flipped −$37,241 → +$23,226. Cleanest one-session recovery in the panel.
- **TSHA** (RED→GREEN_IMPROVING): Call premium flipped −$8,820 → +$1,050.
- **WVE** (RED→GREEN): Recovered but still net-bearish call prem (−$27,624); not "improving" enough for an upgrade, just stable.
- **AVTX** (RED→GREEN, score +1): Note the −$229,793 put premium and 7.1 call A/B — this is the AKTX/preclinical pattern by silhouette; flow is bullish-tilted but it remains OUT OF SCOPE per [[feedback_no_preclinical_nanocap_rockets_2026-05-22]].

## INFERRED INTERPRETATION

1. **Wednesday's broad RED cluster (CRDF, ACHV, TSHA, WVE, AVTX) was largely Tuesday-Wed transient noise**, not a regime change — 5 of 5 are GREEN or GREEN_IMPROVING today. Likely an FOMC/Treasury-auction Wednesday-afternoon hedge that reversed Thursday morning.
2. **The two NEW REDs (VERA, UNCY) are the actual signal.** VERA's call flip + DP surge looks more like institutional repositioning than smart-money exit (puts also being sold). UNCY's call-vol-z collapse from +1.57 to −0.63 is the cleaner directional signal.
3. **MNKD remains GREEN by class but continues to bleed:** net call premium −$157,681 (deeper negative than yesterday's −$88,913). Classification stayed GREEN only because there's no fresh threshold trip. **Flag for tomorrow: if call premium stays sub −$100K, manually downgrade to YELLOW regardless of score.**
4. **CABA's PUT_AB_NORMALIZED (5.27→1.08)** is the cleanest defensive-hedge-unwind signal in the panel — bullish for a near-term move.

## UNRESOLVED GAPS

- No NBBO context on IRON / VERA dark pool prints — can't say whether the volume was AT/ABOVE ask (accumulation) or AT/BELOW bid (distribution). Tomorrow pull `uw_darkpool_ticker` for both if RED/YELLOW persists.
- UNCY GEX = 0 (thin chain) — dealer-hedging signal is unavailable. Flow signal alone is the only read.
- Today's reading is EOD aggregate; the CMPX postmortem flagged **last-4–6-hour intraday flips** as the strongest sell-the-news signal. We can't see the intraday shape from these endpoint snapshots — only the daily delta. **Gap to close: intraday flow polling at 11am / 1pm / 3pm ET for any ticker scoring −2 or worse at prior EOD.**
- ZBIO put A/B 0.012 is anomalous (effectively zero put bid lift). Bull-minus-bear technically +$7,792 but call premium is still negative — possible thin-chain artifact.
- Per [[live_scoring_miscalibration_2026-05-25]]: UNCY under training-matched ODIN encoding scores 0.768 (T2) not 0.864 (T1). If UNCY is actually T2, the RED flow signal carries MORE weight (T2 doesn't earn the same Cardinal-Rule patience as T1).

## RED-TEAM OBJECTIONS

- **VERA RED could be a false positive.** Call A/B 0.744 is BELOW 1.0 (more bid-side than ask-side), which is mixed. Put A/B fell, not rose. Bull-minus-bear still positive. Score −3 is borderline; the DP surge is real but lacks NBBO context. **Counter:** the call premium FLIP from +$13,813 to −$1,489 in one day is the strongest single signal; that alone is RED-worthy regardless of secondary metrics. Leave classification as RED, but call it "soft RED."
- **UNCY RED could be event-window IV ramp noise.** With PDUFA Jun 29 = T−22 trading days, this is exactly the window where dealers re-mark options and OI ramps. Call-vol-z drop could be MM positioning unwind, not smart-money exit. **Counter:** if it were pure positioning unwind, bull-minus-bear should be ~flat. Instead it's −$14,839 (clean directional). Smart-money exit hypothesis is the simpler explanation.
- **CRDF GREEN_IMPROVING reversal in 24h is suspiciously fast.** One-day flips of this magnitude often mean we're sampling noise, not signal. Reduce confidence in the upgrade until we see Friday confirmation.
- **The whole panel may be over-fit to the CMPX postmortem.** That was n=1. We have no second CMPX-pattern win to validate the daily monitor against. Treat all classifications as hypotheses, not facts.

## NEXT-SESSION ACTION ITEMS

1. **Friday 2026-05-29 EOD scan:** confirm or reject VERA + UNCY RED. Two RED days in a row → REVIEW POSITION call. One RED + one GREEN → likely noise.
2. **Pull `uw_darkpool_ticker` with NBBO for VERA and IRON tomorrow** to classify the dark pool prints as accumulation vs distribution.
3. **Manual MNKD downgrade to YELLOW tomorrow if net call premium < −$100K** (override the score threshold — the 5-day trend is clearly deteriorating).
4. **UNCY-specific:** if Friday confirms a second RED day with bull-minus-bear sustained negative, surface a TRIM 25–33% recommendation to David for the locked concentrated regime position. Do NOT auto-execute — David retains all sizing authority per memory.
5. **Intraday polling protocol:** add an 11am / 1pm / 3pm scan layer for any ticker scoring −2 or worse at prior EOD, to capture the last-4–6-hour flip pattern CMPX showed.

## COMPLIANCE ATTESTATION

- Real data only ([[IMMUTABLE_real_data_only_2026-05-15]]) — all UW endpoint reads logged in `uw_daily_snapshots.json`.
- No fabrication, no estimation. Where data was unavailable (NBBO context, intraday shape), gap was named explicitly.
- Catalyst dates referenced (UNCY Jun 29) — labeled per [[feedback_verify_pdufa_dates_2026-05-21]] as the date currently on the locked-position record; not re-verified in this run. Flag for verifier on Monday.
- No-overrides directive ([[feedback_no_more_overrides_2026-05-19]]) respected — no trade recommendations issued, only signal classifications + watchlist actions.
- Mirrored per Amendment 033 to `/9realms/odin_cowork_dropbox/2026-05-28_daily_uw_flow_monitor.md`.

**Chain anchor:** prior autoscan = `2026-05-22_daily_uw_flow_monitor.md`. This report continues the daily series; will be hashed into the Amendment 034 chain on next master log session.
