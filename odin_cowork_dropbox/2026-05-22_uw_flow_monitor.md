# DAILY UW FLOW MONITOR — 2026-05-22 (FRI vs THU)

**Scan type:** Smart-money rotation pulse check (CMPX-pattern detector).  
**Compared:** 2026-05-22 (today) vs 2026-05-21 (prior).  
**Universe:** 16 active T-21 candidates across PDUFAs / readouts / imminent catalysts.  
**Headline:** **RED=6  YELLOW=3  GREEN=7** — heavy rotation day.

## Verified facts

Source: Unusual Whales `uw_flow_features` + `uw_darkpool_ticker` pulled at 2026-05-22 ~3:30pm ET.

| Ticker | Class | NetCallPrem | NetPutPrem | CallAB | PutAB | CallVol-Z | GEX | DP 5d |
|--------|-------|------------:|-----------:|-------:|------:|----------:|----:|------:|
| ACHV | **GREEN** | 29,428 | 290 | 4.58 | 1.00 | -0.48 | 32,230 | 31,551 |
| ARQT | **GREEN** | 0 | 0 | 1.00 | 1.00 | -1.00 | 57,823 | 190,194 |
| AVTX | **RED** | -5,560 | 13,213 | 0.04 | 30.43 | -0.94 | 8 | 587,192 |
| AXSM | **YELLOW** | 182,442 | -20,976 | 1.18 | 0.08 | -0.71 | 2,808 | 139,150 |
| CABA | **YELLOW** | 19,310 | 781 | 4.04 | 1.01 | -0.59 | 130,005 | 40,000 |
| CRDF | **GREEN** | 13,079 | -164 | 3.81 | 0.00 | +1.10 | 315,503 | 0 |
| IRON | **GREEN** | 0 | 0 | 1.00 | 1.00 | -1.00 | 21,740 | 121,059 |
| MNKD | **RED** | -164,658 | -1,233 | 0.50 | 6.98 | +0.66 | 644,459 | 156,158 |
| NMRA | **RED** | -8,662 | -61 | 1.16 | 0.75 | +1.21 | 260,432 | 0 |
| TRDA | **GREEN** | 100 | -40 | 1.00 | 0.00 | -0.87 | 848 | 0 |
| TSHA | **RED** | -946 | 7,105 | 0.07 | 50.20 | -0.93 | 882,506 | 0 |
| UNCY | **GREEN** | 2,063 | -275 | 0.84 | 0.00 | -0.78 | 0 | 0 |
| VERA | **GREEN** | -662 | -680 | 0.19 | 0.20 | +0.05 | 59,861 | 20,915 |
| VRDN | **RED** | -8,193 | -210 | 0.78 | 2.33 | -0.52 | -5,962 | 831,967 |
| WVE | **RED** | -14,911 | -1,341 | 0.47 | 0.00 | -0.72 | 12,453 | 43,183 |
| ZBIO | **YELLOW** | 282 | -12,361 | 0.31 | 0.10 | -0.69 | 230 | 0 |

## Inferred interpretation

### RED — smart money rotating OUT (review position)

**AVTX** — net_call 5273->-5560; put_ab 0.07->30.43; call_ab 2.23->0.04; call_vol_z -0.51->-0.94; gex 0->8; dp_vol 200229->587192

- Flags: AGGRESSIVE_PUT_BUYING_TODAY (put_ab=30.4, net_put_prem=$13213), BEARISH_FLOW (bull_minus_bear=-18773, call_ab=0.04), CALL_PREM_FLIP_POS_TO_NEG (5273->-5560) RED, DP_SPIKE_2.9x (200229->587192), PUT_AB_JUMP_434.7x (0.07->30.43) RED
- Dark-pool spot-check: DP 300K block at $16.50 hit at bid ($16.47/$16.54) = $4.95M sold at bid. 5 large blocks 60K-300K, declining prices. Put_ab 30.4, net put premium $13K. RED CONFIRMED — institutions distributing.

**MNKD** — net_call -45713->-164658; put_ab 1.32->6.98; call_ab 1.31->0.50; call_vol_z 0.02->0.66; gex 613829->644459; dp_vol 33859->156158

- Flags: DP_SPIKE_4.6x (33859->156158), PUT_AB_JUMP_5.3x (1.32->6.98) RED
- Dark-pool spot-check: DP 84,000 share block at $3.35 hitting bid ($3.35/$3.36) = selling pressure. Combined with put_ab 6.98 + net call premium -$165K. RED CONFIRMED — bearish rotation.

**NMRA** — net_call 4898->-8662; put_ab 0.01->0.75; call_ab 1.30->1.16; call_vol_z -0.14->1.21; gex 241268->260432; dp_vol 97944->0

- Flags: CALL_PREM_FLIP_POS_TO_NEG (4898->-8662) RED, DP_DRY_UP (97944->0)
- Dark-pool spot-check: No dark pool prints today (dp_vol_5d=0). Call premium FLIPPED positive->negative (+$4,898 -> -$8,662). Yesterday DP was $98K, today $0 = dried up. Smart money taking profits or hedging.

**TSHA** — net_call 267->-946; put_ab 1.00->50.20; call_ab 2.33->0.07; call_vol_z -0.99->-0.93; gex 612062->882506; dp_vol 24000->0

- Flags: AGGRESSIVE_PUT_BUYING_TODAY (put_ab=50.2, net_put_prem=$7105), PUT_AB_JUMP_50.2x (1.00->50.20) RED
- Dark-pool spot-check: No dark pool prints today (dp_vol_5d=0). Pure options-driven RED: put_ab 50.2x (extreme), net put premium $7,105 vs net call premium -$946. Aggressive put buying in TSHA. Likely positioning for adverse catalyst news or hedge.

**VRDN** — net_call -5251->-8193; put_ab 0.01->2.33; call_ab 0.70->0.78; call_vol_z -0.05->-0.52; gex -9143->-5962; dp_vol 60347->831967

- Flags: DP_SPIKE_13.8x (60347->831967), PUT_AB_JUMP_233.3x (0.01->2.33) RED
- Dark-pool spot-check: DP blocks: 3x 152,100 shares VWAP avg-price-trades + 109,338 sweep, prices declining from $18.04 -> $17.24 throughout session. Mid-day blocks at $17.70 hit at/below NBBO bid ($17.62/$17.68) = institutional selling. GEX -5,961 (short gamma). RED CONFIRMED — smart money EXITING.

**WVE** — net_call 15193->-14911; put_ab 0.13->0.00; call_ab 1.60->0.47; call_vol_z -0.23->-0.72; gex 10762->12453; dp_vol 82908->43183

- Flags: BEARISH_FLOW (bull_minus_bear=-13570, call_ab=0.47), CALL_PREM_FLIP_POS_TO_NEG (15193->-14911) RED
- Dark-pool spot-check: DP $43K, modest. BEARISH_FLOW: bull_minus_bear -$13,570 with call_ab 0.47 (selling calls). Call premium flipped +$15K -> -$15K. Yesterday GREEN with call premium flip bullish — TODAY THE FLIP REVERSED.

### YELLOW — flow weakening (monitor)

**AXSM** — net_call -966633->182442; put_ab 3.05->0.08; call_ab 0.43->1.18; call_vol_z 0.94->-0.71; gex 2469->2808; dp_vol 111919->139150

- Flags: CALL_PREM_FLIP_NEG_TO_POS_BULLISH (-966633->182442), CALL_VOL_Z_DROP_1.65 (0.94->-0.71)

**CABA** — net_call 14680->19310; put_ab 0.01->1.01; call_ab 2.36->4.04; call_vol_z -0.15->-0.59; gex 148199->130005; dp_vol 204879->40000

- Flags: DP_DRY_UP (204879->40000)

**ZBIO** — net_call -1181->282; put_ab 0.61->0.10; call_ab 0.77->0.31; call_vol_z 1.34->-0.69; gex 230->230; dp_vol 0->0

- Flags: CALL_VOL_Z_DROP_2.03 (1.34->-0.69)

### GREEN — flow stable or improving

- **ACHV** — call_ab 4.58, put_ab 1.00, net_bull +29,138. CALL_AB_AGGRESSIVE_BUY (0.46->4.58), CALL_PREM_FLIP_NEG_TO_POS_BULLISH (-15624->29428)
- **ARQT** — call_ab 1.00, put_ab 1.00, net_bull +0. No rotation flags.
- **CRDF** — call_ab 3.81, put_ab 0.00, net_bull +13,243. CALL_AB_AGGRESSIVE_BUY (1.19->3.81)
- **IRON** — call_ab 1.00, put_ab 1.00, net_bull +0. No rotation flags.
- **TRDA** — call_ab 1.00, put_ab 0.00, net_bull +140. No rotation flags.
- **UNCY** — call_ab 0.84, put_ab 0.00, net_bull +2,338. CALL_PREM_FLIP_NEG_TO_POS_BULLISH (-5571->2063)
- **VERA** — call_ab 0.19, put_ab 0.20, net_bull +18. No rotation flags.

## Gaps

- UW `uw_flow_features` returns single-day net premium aggregates; intraday timing (was the flip morning vs. last hour?) not captured. The CMPX postmortem specifically called out the *last 4-6 hours* as the load-bearing window — this scan can only confirm directional flip, not intraday tick.
- Dark pool spot-check pulled only for the 3 highest-impact RED tickers (VRDN/MNKD/AVTX). TSHA/NMRA/WVE classified RED on options flow alone — no dark-pool confirmation.
- ARQT/IRON/TRDA showed `0` net premium with `1.0` ab ratios — likely **stale or thin data** (sweep returned defaults). Treat their GREEN classification as 'no signal' rather than 'positive signal'.
- GEX time-series (charm/vanna/dealer hedging trajectory) not pulled this scan — `uw_total_gex` snapshot only.
- No price-action cross-reference (yfinance/Polygon). Flow flips should be sanity-checked against the actual close once data is available.

## Red-team objections

- **VRDN dark-pool blocks are equivocal directionally.** The 3× 152,100-share avg-price-trade prints look like a VWAP execution algo (likely *one* parent order, not three independent sellers). At ~$2.65M each, plausibly a fund either entering OR exiting a position. The PRICE TRAJECTORY ($18.04 → $17.24) and the bid-side fills are what tip it bearish — but a single seller distributing into strength is consistent with profit-taking, not necessarily 'CMPX-pattern catastrophic exit'. Don't panic-trim on dark pool alone; cross-check news.
- **MNKD put_ab 6.98 + DP at bid is a strong RED — but MNKD already RED-adjacent yesterday (YELLOW with put_ab jump 7.4x).** This is *confirmation* not *new* signal. The rotation already started Thursday. Today is follow-through.
- **AVTX is a Phase 2/3 readout name with low absolute options liquidity** — `put_ab 30.4` is on small absolute dollar size ($13K net put). RED rating is correct but **don't trade off this alone** for nano/micro names; the noise floor is high.
- **TSHA put_ab 50.2** is the highest in the universe but on `0` dark pool volume and $7K net put premium — could be 1-2 large put buyers, not broad institutional rotation. Investigate single-trade hedge vs. fund-wide bearish thesis.
- **AXSM 'CALL_PREM_FLIP_NEG_TO_POS_BULLISH' (-$967K → +$182K) is dramatic** — flagged YELLOW only because of CALL_VOL_Z_DROP (1.65σ). This is arguably **GREEN with caveat**, not YELLOW. The drop in call_vol_z while net call prem flipped strongly positive could mean fewer-but-bigger directional buyers (institutional accumulation, not retail froth).
- **6 of 16 RED is unusually high (37.5%)**. Either (a) market-wide risk-off Friday into the holiday weekend (Memorial Day Mon 2026-05-25), (b) systemic biotech selloff, (c) classifier threshold too sensitive on PUT_AB_JUMP for low-baseline tickers. Recommend reviewing the AVTX/TSHA/VRDN PUT_AB_JUMP ratios — a jump from 0.01 → 2.33 (VRDN) generates a '233x' label that overstates the signal.
- **No baseline comparison vs market.** RED count is meaningless without knowing if XBI/SPX flow also rotated bearish Friday afternoon. A 6/16 RED day during a broad-market risk-off is *expected*, not *idiosyncratic to these catalyst names*.

## NEXT-SESSION ACTION ITEMS

1. **VRDN (RED, T-? catalyst):** confirm catalyst window first. If catalyst is within T-7, follow the no-hold-through-binary rule and trim 30-50% Monday open per CMPX protocol. If catalyst is T-30+, treat as profit-taking by one institution and HOLD with tightened stop. Pull `mcp__9realms__uw_greek_exposure` time series to see if charm/vanna are accelerating bearish.
2. **MNKD (RED, 2-day red sequence):** YELLOW yesterday → RED today = confirmed rotation. If position open, recommend Monday open trim 30-50%. Re-evaluate full exit at next session after price-action sanity check.
3. **AVTX (RED, $4.95M block at bid):** confirm catalyst date. If readout is within T-21, exit at Tuesday open (Tue 2026-05-26 — Mon is Memorial Day holiday). If T-21+, set 7% trailing stop.
4. **TSHA / NMRA / WVE (RED, options-only signal):** lower-conviction RED. Treat as YELLOW-plus until next session confirms. Set conservative trailing stops, do not panic-trim Friday close.
5. **AXSM (YELLOW → arguably GREEN):** the call prem flip pos is large absolute size ($182K). Consider promoting to GREEN at next-session review if call_vol_z normalizes back up.
6. **Monday is Memorial Day market holiday — no trading 2026-05-25.** Next scan: Tuesday 2026-05-26 3:30pm ET. Three trading-day gap means weekend news risk; volatility on Tuesday open will reveal which RED flags were prescient.
7. **Classifier kaizen for next version:** PUT_AB_JUMP ratio cap — when prior put_ab < 0.10, treat any jump as binary YES/NO rather than multiplicative. Avoids the 233x and 434x noise labels on AVTX/VRDN.
8. **Add XBI/SPX baseline:** include market-wide flow context to distinguish idiosyncratic RED from risk-off Friday.

## Compliance attestation

- **Real-data directive (Amendment 027 + IMMUTABLE):** All flow features pulled live from Unusual Whales addon (uw_status http 200). Dark-pool prints with NBBO context and timestamps verified. No fabrication, no simulation.
- **Daily-autoscan persistence (Amendment 034):** This file written to `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/2026-05-22_daily_uw_flow_monitor.md`. Snapshot persisted to `/Odin Perfection/uw_daily_snapshots.json` (15 dates, 191KB).
- **Cowork dropbox (Amendment 033):** Mirrored to `/9realms/odin_cowork_dropbox/2026-05-22_uw_flow_monitor.md`.
- **Format (Amendment 015):** Verified / Inferred / Gaps / Red-team / Action items.
- **Override flags:** None. All RED-flag action recs are conservative (review/trim, not market orders) and respect the no-hold-through-binary cardinal rule.

**Report SHA-256:** `c89e191e2c832e1b999217b8ca94425645910d4bb257ca0e7b45382416cfe193`
