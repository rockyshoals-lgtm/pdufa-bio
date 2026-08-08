# GUNGNIR v41 KAIZEN — ORATS Options/IV Features Testing Report

**Date**: 2026-04-04  
**Status**: Complete  
**Outcome**: ORATS features do NOT improve phase readout outcome prediction

---

## Executive Summary

Tested 12 ORATS-derived options/IV features from the BIFROST v5.2 Explosion Detector to see if they improve Gungnir v40's phase readout outcome prediction. All 12 features HURT the model across the board.

- **v40 Baseline AUC**: 0.7599 (125 features)
- **v41 Best Feature**: -0.0002 AUC (worse than baseline)
- **Coverage**: 1,033/1,752 events (59.0%) had ORATS options data
- **Verdict**: ORATS signals detect MAGNITUDE of moves, not DIRECTION/OUTCOME

---

## Key Finding: Signal Mismatch

**BIFROST v5.2 optimizes for**: P(|D1| > 25%) — post-catalyst magnitude prediction  
**GUNGNIR optimizes for**: P(positive outcome) — approval likelihood

These are **orthogonal signals**.

- High IV expands before big moves — whether up or down
- Low spread/high OI indicates options traders expect volatility — not directional bias
- IV metrics capture *uncertainty/activity*, not *approval probability*

---

## Deep Audit Results (All 12 Features)

| Feature | WF AUC | ΔAUC | Status | Notes |
|---------|--------|------|--------|-------|
| v41_iv_x_phase3 | 0.7597 | -0.0002 | FLAT | Least harmful; still negative |
| v41_iv_x_micro | 0.7590 | -0.0009 | HURTS | Phase 3 micro-cap interaction fails |
| v41_has_options | 0.7589 | -0.0010 | HURTS | Binary options availability is noise |
| v41_options_x_phase2 | 0.7589 | -0.0011 | HURTS | Options × Phase 2 doesn't capture outcome |
| v41_entry_spread_pct | 0.7589 | -0.0011 | HURTS | Spread width unrelated to approval |
| v41_oi_high | 0.7588 | -0.0011 | HURTS | High OI doesn't predict success |
| v41_entry_oi | 0.7585 | -0.0014 | HURTS | Continuous OI also fails |
| v41_iv_high | 0.7582 | -0.0018 | HURTS | High IV (>100%) is actually negative |
| v41_spread_tight | 0.7581 | -0.0019 | HURTS | Tight spreads add noise |
| v41_iv_low | 0.7571 | -0.0029 | HURTS | Low IV (<50%) harmful |
| v41_iv_x_small | 0.7554 | -0.0045 | HURTS | Small-cap IV interaction worst-case |
| v41_entry_iv_pct | 0.7553 | -0.0047 | HURTS | Raw IV pct is the worst feature |

---

## Analysis

### Why did BIFROST features fail for GUNGNIR?

1. **BIFROST signals volatility/surprise magnitude**
   - High IV before readout = market unsure about outcome
   - Large spread = options traders pricing uncertainty
   - High OI = active options market = binary event

2. **GUNGNIR needs approval probability signals**
   - IV expands whether approval or CRL equally
   - Options market assumes 50/50 by design (ATM)
   - Spread width reflects liquidity, not approval odds

3. **BIFROST advantages (post-catalyst moves)**
   - Surprise × volatility interactions drive D1 magnitude
   - IV crush occurs regardless of direction
   - Options Greeks (gamma) benefit from vol expansion

4. **Why Gungnir doesn't benefit**
   - Gungnir already has phase/size/designation/journey features
   - These provide directional approval signals
   - Options data is purely *magnitude-based*
   - Adding magnitude features introduces noise

---

## Phase 2: Greedy Forward Selection

**Result**: No features passed initial audit (ΔAUC > +0.0005), so greedy selection was skipped.

---

## Coverage Analysis

- **Total events**: 1,752
- **ORATS coverage**: 1,033 events (59.0%)
- **Impact of missing data**: Imputed as zeros, creating 39 events with all v41 features = 0

The 59% coverage is lower than BIFROST's use case (options backtest only includes events with viable options chains). Missing data imputation doesn't harm other models (Ridge/XGB are robust to zeros), but the signal itself isn't predictive.

---

## Diagnostic: Why is raw IV pct (-0.0047 AUC) the worst?

Raw IV at T-14 has **zero relationship** to approval probability:

- **High IV scenario**: Market expects big move either direction
  - Could be "risky drug, big upside if approved" (positive for approval)
  - Could be "binary readout, 50/50 odds, high volatility" (neutral)
  - Could be "weak sponsor, uncertain manufacturing" (negative)

- **Low IV scenario**: Market expects small move
  - Could be "expected approval, already priced in" (positive)
  - Could be "obscure indication, no one cares" (negative)

**Conclusion**: IV level is agnostic to approval. BIFROST's advantage is that it trades the *runup* regardless of direction — explosion detection doesn't require outcome knowledge.

---

## Implications for Future Work

### What WOULD work for Gungnir?

- **Analyst sentiment on approval odds** (if available T-1)
- **Precedent-based approval rates** (similar drug, TA, sponsor history)
- **Regulatory signal features** (BTD, orphan, priority review — already in v40)
- **Manufacturing risk indicators** (supply chain, CMC flags)

### Why BIFROST works where Gungnir doesn't:

BIFROST's entire premise: **"Win if you can time the entry/exit around the runup, regardless of outcome."**

- Explosive moves happen on BOTH approvals and CRLs
- IV expansion + gamma scalp = positive expected value in magnitude
- Spread tightening = reduced hedging costs

Gungnir's premise: **"Predict whether the drug will be approved or not."**

- Approval requires regulatory science signals, not market noise
- IV metrics measure uncertainty, not approval probability
- Options market is efficient → no edge in direction prediction from vol alone

---

## Recommendation

**v40 remains the Gungnir champion.**

**Do NOT pursue ORATS integration for outcome prediction.** The feature families are orthogonal:
- BIFROST: magnitude/explosion (post-catalyst moves)
- GUNGNIR: direction/approval (outcome prediction)

Future Gungnir kaizen should focus on:
1. **Regulatory science features** (manufacturing risk, safety signals)
2. **Precedent-based priors** (TA-level approval rates, sponsor track record)
3. **Endpoint robustness** (trial design indicators already being tested)

BIFROST integration is complete and optimal. Gungnir should stick to non-market features.

---

## Files

- **Script**: `gungnir_v41_kaizen_orats.py`
- **Results**: `gungnir_v41_kaizen_results.json`
- **Data sources**:
  - `enriched_gungnir_dataset_v2.csv` (1,752 training events)
  - `options_backtest_v2_results.json` (1,033 readout trades with ORATS data)
