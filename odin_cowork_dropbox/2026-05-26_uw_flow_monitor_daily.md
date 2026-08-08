# DAILY UW FLOW MONITOR — 2026-05-26 (TUE vs FRI 2026-05-22)

**Run type:** scheduled_daily_uw_flow_monitor_TUE_VS_FRI (first post–Memorial Day session)
**Prior trading day:** 2026-05-22 (5/25 was holiday NOOP, byte-identical to 5/22)
**Source:** mcp__9realms__uw_flow_features for 16 monitor tickers
**Persistence:** Amendment 034 (Daily Autoscan Persistence) + Amendment 033 (Cowork Dropbox) + Daily Scan Mirror

---

## ⚠️ HEADLINE — 3 NEW REDs, 5 REDs RECOVERED

**NEW RED today (was not RED on 5/22):** AXSM, CABA, **UNCY (PORTFOLIO-CRITICAL — 50% of $75K concentrated regime)**
**RED → recovered (GREEN/YELLOW):** MNKD, NMRA, TSHA, VRDN, WVE
**Persistent RED:** AVTX (4th consecutive session)

| Bucket | Count | Tickers |
|---|---|---|
| 🟢 GREEN | 6 | CRDF, IRON, MNKD, TRDA, WVE, ZBIO |
| 🟡 YELLOW | 6 | ACHV, ARQT, NMRA, TSHA, VERA, VRDN |
| 🔴 RED | 4 | AVTX, AXSM, CABA, **UNCY** |

---

## VERIFIED FACTS (UW raw readings — see snapshot JSON for full per-ticker)

### 🔴 RED — actionable

**UNCY 🔴 GREEN → RED** *(PDUFA Jun 29 2026, T-34d; 50% of locked portfolio per Amendment 031)*
- Flag: `CALL_PREM_FLIP_BEAR (+$2,063 → -$8,912)`
- net_call -$8,912, net_put -$7,277 (BOTH negative = call selling + put selling)
- put_ab 0.00 → 1.29 (defensive positioning, but modest)
- GEX = 0 (thin options — **noise risk**)
- DP unchanged at zero
- **Verdict:** Real rotation but in thin-OI name. Asymmetric portfolio risk justifies action even with low-confidence signal.

**CABA 🔴 YELLOW → RED** *(EULAR Jun 3-6, T-8d; RESET-MG + H1 RESET-SLE/SSc)*
- Flag: `PUT_AB_JUMP_42.6x (1.01 → 42.86)` — **extreme** defensive positioning
- net_call +$7,083 (still positive) but net_put +$8,823 (puts being BOUGHT at ask, hard)
- bull-bear -$1,740 (now net bearish)
- call_ab collapsed 4.04 → 1.02 (call buying faded)
- **Verdict:** Heaviest defensive flow of the session. Hard to read as anything but pre-EULAR insurance / smart-money hedging.

**AXSM 🟡 YELLOW → RED**
- Flag: `CALL_PREM_FLIP_BEAR (+$182,442 → -$35,334)` — $217K swing
- net_put -$98,670 (put SELLING — caveat: bull_minus_bear still +$63K)
- 34 DP prints / $117K 5d volume
- **Verdict:** Headline call buying gone. Put-selling moderates the bear read but the $217K call-prem swing is the real signal — caught the CMPX-style flip.

**AVTX 🔴 RED → RED** *(persistent 4th day)*
- Flag: `PUT_AB_HIGH (3.79)` — cooled from 30.43 but still elevated
- net_call -$27,036 (worsened from -$5,560)
- DP normalized from $587K to $65K
- **Verdict:** Put pressure cooled but call premium kept deteriorating. No relief.

### 🟢 RED RECOVERIES (institutional re-positioning bullish)

- **MNKD 🔴 → 🟢** (PDUFA Fri May 29, **T-3d** — danger window). net_call -$165K → -$89K (still bearish but halved), put_ab 6.98 → 1.77, call_vol_z surged 0.66 → **1.92** (new aggressive call vol), DP $156K → $107K. **Mixed read — RED→GREEN is rule-driven; nuance is bearish flow MODERATED, not reversed.** Recommend: re-poll 5/27 + 5/28 closely; if put_ab pops again in last 24h before PDUFA = exit signal per CMPX postmortem.
- **TSHA 🔴 → 🟡**. put_ab collapsed 50.20 → 0.00, call_ab surged 0.07 → 5.00 (aggressive call buying), DP block printed 75K shares, net_call flipped positive. Genuine bullish rotation.
- **WVE 🔴 → 🟢**. call_vol_z normalized -0.72 → +0.16, put_ab essentially zero. Flow neutralized.
- **VRDN 🔴 → 🟡**. DP normalized $832K → $198K. GEX still negative & deteriorating (-$5,962 → -$11,795) — kept YELLOW.
- **NMRA 🔴 → 🟡**. put_ab cooled 0.75 → 0.15, but call_vol_z DROPPED -1.94 (1.21 → -0.73) — call interest faded. Mixed.

### 🟢 GREEN — stable / improving

- **CRDF GREEN → GREEN**. call_ab jumped 3.81 → **7.19** = institutional accumulation continuing. Strongest flow of the session.
- **IRON GREEN → GREEN**. DP normalized. Quiet.
- **TRDA GREEN → GREEN**. Zero flow (no options activity).
- **ZBIO 🟡 → 🟢**. Quieted. No flags.

### 🟡 YELLOW — watch

- **ACHV GREEN → YELLOW**. GEX deterioration 32K → 22K (-30%); call buying faded 4.58 → 1.36.
- **VERA GREEN → YELLOW**. DP 2.7x spike (20K → 56K); call_vol_z dropped to -0.53.
- **ARQT GREEN → YELLOW**. DP 3.4x spike $190K → **$655K** — huge institutional block activity. Could be accumulation OR distribution; need print-by-print read.

---

## INFERRED INTERPRETATION

1. **UNCY is the single most important data point.** 50% of the $75K concentrated regime is now flagged RED on flow. Even though GEX=0 (thin options) reduces signal strength, the asymmetric risk to the portfolio means action is warranted. Cardinal Rule + Amendment 031: position must exit before binary regardless, and PDUFA is T-34 — flow turning bearish 5 weeks early matches the smart-money-front-runs-retail pattern.

2. **CABA's 42.6x put_ab spike is the most extreme single-day defensive positioning in this monitor's history.** With EULAR T-8 and a "Catalyst LongHold" archetype already shipped, this is consistent with hedging by holders, not necessarily directional selling. But it is too large to ignore.

3. **AXSM caught a textbook CMPX-style flip** — the precise pattern the monitor was built to detect. Call premium swung $217K negative in a single session.

4. **MNKD's recovery 3 days before PDUFA is the highest-stakes call of this report.** RED→GREEN by rules, but the underlying signals are net_call still -$89K (deeply bearish), and the recovery hinges on put_ab cooling + a single high call_vol_z print. Treat as YELLOW in practice — re-check 5/27 EOD and 5/28 EOD; another put_ab spike in last 24h pre-event = CMPX repeat.

5. **5 RED-recoveries in one session is unusual.** Possible post-Memorial-Day mean reversion / dealers re-marking inventory. Treat all recoveries as low-confidence until confirmed by a second session.

---

## UNRESOLVED GAPS

- UW endpoints return aggregated 5d / 30d figures; no intraday timestamp on this poll. Cannot distinguish morning vs afternoon rotation within the session.
- GEX values for thin-OI names (UNCY=0, ZBIO=230, AVTX=8, TRDA=1259, AXSM=3419) carry low signal — these are noise-prone.
- CABA's 42.86 put_ab is so extreme it could be a single fat-finger trade rather than systematic positioning. Recommend cross-check via uw_oi_change tomorrow to see if a specific strike printed.
- The DP_SPIKE_75000x flag on TSHA is a divide-by-zero artifact (prior was 0). Real signal is the 75K-share block, not the ratio.
- Did NOT poll uw_oi_change or uw_darkpool_ticker for print-level detail. Could enrich tomorrow's run if RED tickers persist.

---

## RED-TEAM OBJECTIONS

1. **Rule sensitivity.** Rules are tuned conservatively (RED requires deep bearish thresholds). 4 RED out of 16 = 25% baseline; historically the monitor has run 19-38% RED. Today's 25% is in-range, not alarmist.
2. **Mean reversion vs trend.** 5 RED-recoveries in one day raises the possibility that 5/22's RED cluster was a transient pre-holiday positioning blip rather than persistent smart-money rotation. Wait for 5/27 confirmation before reading recoveries as durable.
3. **UNCY signal strength.** The $11K call-prem swing in a name with GEX=0 is small in absolute dollars. Could be a single retail-sized trade rather than smart money. **Counter:** still triggers the rule, and asymmetric portfolio risk justifies erring conservative.
4. **MNKD T-3 timing.** Rule put MNKD in GREEN but the PDUFA timing argues for at least YELLOW. The framework says watch the **last 4-6 hours**, which is Thursday-into-Friday for a Friday May 29 PDUFA. Today's flow improvement does not predict Thursday's flow.
5. **CABA caveat.** put_ab of 42.86 is mathematically extreme but could reflect very low total put volume (high ratio on small notional). The $8,823 net_put_prem suggests modest dollar-volume — confirms the ratio is amplifying a small absolute trade.

---

## NEXT-SESSION ACTION ITEMS

**Per scheduled task instruction "For tickers with RED flag, recommend: trim 30-50% before next session, or set tighter trailing stop":**

1. **UNCY (RED, portfolio-critical, T-34 to PDUFA):**
   - Recommended action: **Set tighter trailing stop** (do NOT trim yet given signal noise on thin-OI name). Consider 12-15% trailing stop on the equity leg.
   - If RED persists on 5/27 with a second confirming flag → trim 25-30%, redeploy to CAPR or scan rotation.
   - Per Amendment 029 + concentrated-regime directive: any size change requires explicit user authorization.

2. **CABA (RED, EULAR T-8):**
   - Recommended action: **Trim 20-30% of equity** OR convert remainder to spread. put_ab 42.86 is too extreme to dismiss.
   - If user prefers full hold: tighten trailing stop to 8-10%.

3. **AXSM (RED, no portfolio position):** Watchlist only — pattern is informational for future similar setups.

4. **AVTX (RED persistent):** No portfolio position. Continue monitoring; if RED extends to 5 consecutive sessions, archive as a confirmed CMPX-pattern case study.

5. **MNKD (GREEN per rules, RED-recovery, PDUFA T-3):**
   - **Override the GREEN rating in practice — treat as YELLOW until 5/29.**
   - Poll uw_flow_features 5/27 EOD + 5/28 EOD + 5/29 morning. Cardinal Rule: full exit no later than 5/28 close per "never hold through binary."

6. **Carry: VERA, ARQT YELLOW DP spikes.** Pull uw_darkpool_ticker tomorrow to see bid/ask print direction (accumulation vs distribution).

---

## COMPLIANCE ATTESTATION

- ✅ Real data only (Amendment 027): all features from mcp__9realms__uw_flow_features live readings
- ✅ Panel integrity (Amendment 028): N/A (single-day flow read, not a rate panel)
- ✅ Cross-chat publication (Amendment 029): written to Odin Perfection + dropbox + daily_scans mirror
- ✅ Daily-autoscan persistence (Amendment 034): full report written even though no "trade" decision made
- ✅ Cowork dropbox (Amendment 033): mirrored to /9realms/odin_cowork_dropbox/
- ✅ Daily scan mirror (Amendment 022): mirrored to /9realms/daily_scans/
- ✅ Universal prediction hash (Amendment 032): N/A (monitor run, not a prediction)
- ✅ Verify PDUFA dates (feedback 2026-05-21): MNKD PDUFA = Fri 2026-05-29 (confirmed); UNCY PDUFA = Mon 2026-06-29; CABA next catalyst = EULAR Jun 3-6
- ✅ No-overrides (feedback 2026-05-19): no new entries recommended; only position-management actions on existing locked positions

---

## CHAIN HASH

Prior chain: `4f3d23a3...c774` (Amendment 035 ledger #23)
This report SHA-256 will be appended to next chain entry in master amendment ledger.

---

*Generated 2026-05-26 15:30 ET by scheduled daily UW flow monitor. Next run: 2026-05-27 15:30 ET.*
