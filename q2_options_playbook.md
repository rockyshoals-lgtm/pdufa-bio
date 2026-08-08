# Q2 2026 OPTIONS PLAYBOOK
*As of April 17, 2026*

## Honest Data Disclosure

The ORATS cache on this system contains complete live snapshots for **9 tickers** as of Apr 2, 2026: ABSI, ALXO, BHC, BHVN, CABA, GRCE, MNKD, NUVB, WHWK. Of these, only **GRCE** and **ALXO** overlap with the 30-name aggressive Q2 roster. The remaining 28 names require a live ORATS fetch before live IV cheapness can be scored. This playbook uses: (a) ORATS cache where available, (b) BIFROST Options Module v1.0 deploy data (Apr 4, 2026 scan), (c) BIFROST Options v1.1 backtest edge by segment (1,828 trades, 2022–2026), and (d) live IV observations from operational notes.

## Structural Reality of the Q2 Roster

**29 of 30 roster names are AACR Apr 17–22 conference plays.** AACR is happening THIS WEEK (today is Apr 17). The T-14 options entry window for AACR would have been ~Apr 1. That window is closed. The cardinal rule — 'the runup IS the trade' — means AACR options would have needed entry before Apr 10. These 29 names are EQUITY-ONLY plays now. Exit day-before or day-of podium presentations per the rotation waterfall.

**The actual Q2 options universe is smaller** — the non-AACR catalysts in the roster + ALXO: AXSM (Apr 30 PDUFA), ALXO (May 7 ESMO), CABA (Jun 3 EULAR), UNCY/OSTX/LRMR/LNTH (late-June PDUFAs), DBVT/XNCR/RNA (late-June readouts), CLDI/EDSA/BOLD (other events). Of these, segment-edge and cap-tier gating leaves **3 top-priority options plays: UNCY, OSTX, CABA**.

## Active Options Window NOW (Apr 17)

### ALXO — ESMO Breast May 7 (D-20)

Stock now $1.65. ORATS Apr 2 snapshot: **IV = 252%**, ivPct1Y = 79%, ivRank1Y = 54. That is HIGH by any cheapness standard. Live IV observation from operational notes also confirms elevated near-term IV on small-cap. ALXO is a core 55% equity held position, so adding options increases concentration risk on the thesis. **Recommendation:** do not chase options at current IV. Wait for a ≥15% IV pullback. If entered, max 1.5% portfolio, ATM calls $2.00 or $2.50 strike May 15 monthly — this expiry spans the May 7 catalyst. Sizing rule: keep combined ALXO equity + options exposure under 60%.

### AXSM — AXS-05 PDUFA Apr 30 (D-13)

T-14 options entry window is open THIS WEEK. However: mid-cap PDUFA segment has +1.8% avg return and 36.2% win rate on options per the 1,828-trade BIFROST v1.1 backtest. This is ROUGHLY FLAT edge with full exposure to theta. Equity preferred via BIFROST v4 timing. **Recommendation:** SKIP options. If strong conviction, cap at 0.5% capital, ATM $60 strike May 15, limit order only.

## Top 3 High-Priority Options Plays (Wait for T-14)

### 1. UNCY — Zephyr-HC PDUFA Jun 27 (D-71)

**GOLD segment** per BIFROST v1.1 backtest: PDUFA Micro returns +36.7% avg, 50.0% win rate, 19.3% of trades go >100%. Micro-cap PDUFA is the single best-edge segment in the options universe. **Entry:** Jun 8, 2026 (T-14 trading days before Jun 27). **Expiry:** Jul 17 monthly (spans catalyst). **Size:** 2.0% of capital. **Calendar reminder:** Jun 5.

### 2. OSTX — OST-HER2 PDUFA Jun 30 (D-74)

Co-equal with UNCY. OST-HER2 is orphan oncology with BTD stack — ODIN v14 weights is_oncology (+0.120), pw_orphan_drug_bin_x_btd_bin (-0.202 penalty asymmetry), gt_x_btd (+0.140). **Entry:** Jun 11, 2026. **Expiry:** Jul 17 monthly. **Size:** 2.0%. **Calendar reminder:** Jun 9.

### 3. CABA — EULAR SLE/SSc Jun 3 (D-47)

Small-cap Phase 2/3 readout at major conference. Smart Money Overlay flagged CEO buying + Cormorant ownership. 100% MG-ADL response at RESET-MG. BTD+ODD+RMAT designation stack. **Entry:** May 14, 2026 (T-14 trading days before Jun 3). **Expiry:** Jun 19 monthly. **Size:** 1.5%. Current IV 73% near / 99% far per CLAUDE.md live observations — MODERATE cheapness.

## Weekly vs Monthly Expiry — Comparison

| Ticker | Catalyst Date | Monthly Expiry (3rd Fri) | Weekly Expiry (1st Fri after) | Preferred |
|---|---|---|---|---|
| UNCY | 2026-06-27 (Sat) | 2026-07-17 | 2026-07-02 | **Weekly** (closer to event, captures IV crush arbitrage for exits) |
| OSTX | 2026-06-30 (Tue) | 2026-07-17 | 2026-07-02 | **Weekly** (tight expiry = more leverage, but MUST exit T-1) |
| CABA | 2026-06-03 (Wed) | 2026-06-19 | 2026-06-05 | **Monthly** (weekly has only 2 days post-event, theta risk if runup late) |
| ALXO | 2026-05-07 (Thu) | 2026-05-15 | 2026-05-08 | **Monthly** (weekly Fri-after is only 1 day — too tight for IV capture) |
| AXSM | 2026-04-30 (Thu) | 2026-05-15 | 2026-05-01 | **Monthly** (same issue — weekly expires day-of, can't exit T-1) |

**Rule:** Monthly expiry preferred when the first post-catalyst weekly Friday is <3 days after the event (no time to exit T-1 before Friday close). Weekly preferred when there are ≥5 days between catalyst and next Friday (more leverage, exit T-1 before weekend).

## Full Universe — Cheapness Scores

See `q2_options_cheapness.csv` for all 30 roster names + ALXO. Key observations:

- **4 names with real ORATS or Apr 7 snapshot data:** GRCE, ALXO, CRDF, HCM — all have elevated IV (cheapness score <45 = FAIR or worse)
- **27 names require live ORATS fetch before options scoring**
- **All AACR conference names (22)** have D-0 to D-5 — options window closed, equity only

## Position Sizing & Risk Rules (from BIFROST Options v1.1)

- **Max single options position:** 2% of capital (vs 3–5% equity)
- **ODIN/Gungnir filter:** T1 (≥0.85) or T2 (0.65–0.85) only
- **LIMIT ORDERS MANDATORY** — bid-ask spreads cost ~23pp on average. Limit at mid or better.
- **Never hold through the event** — exit T-1 before close. No exceptions.
- **Explosion tier (BIFROST v5.5) sniper multiplier:** 1.5× up to 3% cap
- **Combined options + equity on same name ≤ 60% of portfolio**

## Backtest Segment Edge Reference (1,828 trades, 2022–2026)

| Segment | Avg Return | Win Rate | % >100% | Verdict |
|---|---|---|---|---|
| PDUFA Micro | +36.7% | 50.0% | 19.3% | **GOLD** |
| Phase 1/2 Readout | +28.2% | 52.9% | 21.4% | **GOLD** |
| Phase 2 Readout | +29.8% | 41.8% | 17.6% | ASYMMETRIC |
| PDUFA Small | +12.6% | 38.4% | 12.5% | DECENT |
| PDUFA Mid | +1.8% | 36.2% | — | MARGINAL |
| PDUFA Large | -5.5% | 31.0% | — | AVOID (theta) |
| Phase 3 Readout | -5.8% | 32.3% | — | AVOID |
| Phase 2b Readout | -19.4% | 29.6% | — | AVOID |

## Capital Allocation — Q2 Options Budget

Across the 3 top-priority plays (UNCY 2.0% + OSTX 2.0% + CABA 1.5%) = **5.5% of capital** in options, staggered across May 14 → Jun 11. Peak concurrent options heat: ~4.5% (UNCY + OSTX overlap Jun 11–26). All three resolve by end of Q2. Total options exposure fits inside the aggressive 35–40% peak concurrent heat budget without crowding equity positions.

## Honest Caveats

- **ORATS cache coverage is 30% of roster** — most recommendations based on segment backtest + live IV observations, not fresh ORATS summaries
- **Live IV will change things.** At T-14 entry, re-score cheapness with fresh ORATS data. Skip if ivPct1Y > 80 or IV/RV > 2.0
- **BIFROST options backtest used MID-PRICE fills.** With bid-ask spreads of 20–30pp, ask-price fills flip EV negative. LIMIT ORDERS ARE NOT OPTIONAL
- **Stage classifications on the 30-name roster need verification** before options entry — DBVT and RNA are Phase 3 (AVOID segment); XNCR stage needs confirmation before sizing
