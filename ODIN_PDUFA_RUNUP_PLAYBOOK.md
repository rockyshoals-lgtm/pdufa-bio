# ODIN PDUFA Catalyst Runup Trading Playbook
## Actionable Strategies for Pre-Decision Momentum Trading

**Version:** 1.0  
**Date:** 2026-02-01  
**Research Sources:** Perplexity Architecture + Web Supplementation

---

## Executive Summary

This playbook operationalizes the research from the ODIN Phase 2 T-45 PDUFA Runup Research Architecture. The core insight: **most profit is captured in the pre-decision runup, not the approval itself**. Historical examples show +97% to +367% gains during runup periods versus frequent selloffs post-approval.

**Cardinal Rule:** Never hold through the FDA decision. Exit T-10 to T-5.

---

## STRATEGY 1: Momentum Runup Trade (PRIMARY)

### Setup
- **Entry Window:** T-60 to T-45 (when PDUFA date confirmed, institutional positioning begins)
- **Target Return:** 8-15% median, with outliers >100%
- **Position Type:** Long equity or ITM/ATM calls (2-3 month expiry)

### Entry Criteria (REQUIRE ≥4 of 6)
| # | Criterion | Source |
|---|-----------|--------|
| 1 | PDUFA date officially confirmed | FDA/company PR |
| 2 | Market cap $100M - $2B | Sweet spot for retail attention |
| 3 | Binary outcome (NDA/BLA, not sNDA) | Higher catalyst impact |
| 4 | Prior positive Phase 3 data | Foundation for approval thesis |
| 5 | No prior CRL or efficacy-related CRL addressed | Risk filter |
| 6 | Options available with reasonable liquidity | ≥500 OI on near-money strikes |

### Exit Rules (NON-NEGOTIABLE)
```
PRIMARY EXIT: T-10 to T-7
- Lock in gains before IV peak and binary risk
- Options: Sell regardless of P/L

EARLY EXIT TRIGGERS:
- 20% gain achieved → Sell 50% position
- Negative news (manufacturing delay, RTOR issues) → Exit immediately
- Competitor approval in same indication → Reassess within 24h

STOP LOSS: 15% from entry (accept as cost of binary exposure)
```

### Position Sizing
- **Maximum:** 5% of portfolio per catalyst
- **Recommended:** 2-3% for new traders
- **Basket approach:** 8-12 positions across different PDUFA dates

---

## STRATEGY 2: Vol-Expansion Straddle (ODIN SPECIALTY)

### Theory
IV expands dramatically T-45 → T-1 (often from <50% to 150-400%). Capture this expansion, exit before IV crush.

### 4-Phase Volatility Cycle
```
Phase 1 (T-60 to T-45): IV below 30th percentile historical → BUY
Phase 2 (T-45 to T-20): IV expansion begins → HOLD
Phase 3 (T-20 to T-7): IV acceleration, peak pricing → SELL WINDOW
Phase 4 (T-7 to T+1): Maximum IV, then crush → DO NOT HOLD
```

### Execution
1. **Entry:** Buy ATM straddle when 30-day IV < 60% (or <30th %ile for ticker)
2. **Target:** IV doubles (100% IV expansion = ~70-150% straddle gain)
3. **Exit:** T-10 to T-7, regardless of stock direction
4. **Risk:** If IV doesn't expand (rare), maximum loss = premium paid

### Position Sizing
- Maximum 3% portfolio per straddle
- 20% stop loss (straddle value decline)

---

## STRATEGY 3: CRL Early Warning Short (ADVANCED)

### Multi-Signal Framework
Require ≥3 of 5 red flags before initiating short:

| Signal | Source | Weight |
|--------|--------|--------|
| IV term spread inverted (30d IV > 90d IV) | Options chain | 25% |
| Discretionary insider sales ratio >0.6 | SEC Form 4 | 25% |
| Late sales cluster (>50% in final 14 days) | SEC Form 4 | 20% |
| Price peaked T-15, declining toward PDUFA | Chart | 15% |
| Negative SSOF (signed small order flow) | L2 data | 15% |

### Execution
- **Entry:** T-7 to T-3 when signals align
- **Position:** Short equity, buy puts, or sell call spreads
- **Target:** 15-25% gain (typical CRL gap = -30% to -50%)
- **Exit:** Day before PDUFA or early FDA announcement
- **Position Size:** 2% maximum (lower conviction trade)

### Risk Controls
- Never short BTD+Orphan+Priority Review stacks (96%+ approval rate)
- Never short resubmissions with Class 1 designation
- Accept 100% loss on short if approval occurs

---

## STRATEGY 4: Resubmission Recovery (POST-CRL)

### Setup
After manufacturing/CMC-only CRL (NOT efficacy failure):

1. **Wait for:** Company announces specific timeline for resubmission
2. **Entry:** When resubmission accepted (typically -40% to -60% from pre-CRL)
3. **Target:** Recovery toward 70-80% of pre-CRL level
4. **Exit:** T-10 before resubmission PDUFA

### Qualification Criteria
- CRL explicitly cited CMC/manufacturing issues ONLY
- No efficacy or safety concerns
- Company has financial runway (>18 months cash)
- Experienced sponsor (previous approvals)

### Position Sizing
- 5% maximum (higher conviction than initial PDUFA)
- Longer holding period = more volatility exposure

---

## ODIN Integration: Signal Hierarchy

From ODIN v9.1 champion config, prioritize events with:

### Tier 1 Targets (≥85% probability → AGGRESSIVE SIZING)
- BTD + Orphan + Priority Review stack
- Experienced sponsor (>5 prior approvals)
- Vaccines or Infectious Disease TA
- Class 1 resubmission

### Tier 2 Targets (70-85% probability → STANDARD SIZING)
- BTD OR Priority Review (not both)
- Oncology/GI therapeutic areas
- No prior CRL

### Tier 4 Avoids (<55% probability → NO POSITION OR SHORT)
- Pain Management TA (41.9% CRL rate)
- Hematology/Nephrology TA (>30% CRL rate)
- First-time sponsor
- Prior efficacy-related CRL
- Manufacturing complexity flags

---

## Data Sources & Tools

### Free Resources
| Resource | URL | Use Case |
|----------|-----|----------|
| BiopharmCatalyst | biopharmcatalyst.com | PDUFA calendar |
| RTTNews FDA Calendar | rttnews.com/corpinfo/fdacalendar.aspx | Backup calendar |
| Merlintrader | merlintrader.com | Catalyst tracking |
| FDA Drugs@FDA | accessdata.fda.gov/scripts/cder/daf/ | Official decisions |
| SEC EDGAR | sec.gov/edgar | Form 4 insider filings |

### ODIN Enrichment Stack
| Source | API Key Env | Use Case |
|--------|-------------|----------|
| FMP | FMP_API_KEY | Price data, fundamentals |
| FinBrain | FINBRAIN_API_KEY | Options flow, insider signals |
| LunarCrush | LUNARCRUSH_API_KEY | Social sentiment |
| OpenFDA | OPENFDA_API_KEY | Drug data validation |

---

## Weekly Execution Workflow

### Monday: Screening
```bash
1. Pull BiopharmCatalyst PDUFA calendar (T-45 to T-90 window)
2. Filter for: Market cap >$100M, NDA/BLA decisions, options available
3. Cross-reference ODIN predictions for tier classification
4. Flag any insider transactions from prior week (SEC EDGAR)
```

### Tuesday-Wednesday: Due Diligence
```bash
1. Read FDA briefing documents (if available)
2. Check AdCom history/recommendations
3. Verify manufacturing site inspection status
4. Score therapeutic area risk (HINT adjustments)
5. Check LunarCrush sentiment classification
```

### Thursday: Position Entry
```bash
1. Enter positions for qualified T-45 to T-60 events
2. Set price alerts for exit triggers
3. Calculate position sizes (max 5% per event)
4. Document entry rationale for each position
```

### Friday: Portfolio Review
```bash
1. Check all positions approaching T-10 → Exit window opens
2. Review any FDA early communications
3. Update tracking spreadsheet with weekly P/L
4. Scan for new PDUFA dates announced
```

---

## Risk Management Rules

### Portfolio Level
- Maximum 25% of portfolio in catalyst trades simultaneously
- Maximum 5 concurrent PDUFA positions
- Minimum 50% cash reserve for unexpected opportunities

### Position Level
- Never exceed 5% on single PDUFA event
- Accept 15-20% loss as stop (binary nature makes tighter stops impractical)
- Take 50% profit at +20% gain, let remainder ride to T-10

### Behavioral Rules
- **NEVER** hold through FDA decision (no exceptions)
- **NEVER** average down on catalyst positions
- **NEVER** chase entries after T-30 (IV already elevated)
- **ALWAYS** verify PDUFA date from official FDA sources before entry

---

## Example Trade Walkthrough

### Hypothetical: RCKT (Rocket Pharmaceuticals)
**PDUFA:** March 28, 2026 (BLA for Kresladi gene therapy)

**T-60 (Jan 27):** Screening identifies RCKT
- Market cap: ~$800M ✓
- BLA decision (gene therapy) ✓
- Prior Phase 3 data positive ✓
- ODIN prediction: Tier 2 (Cell/Gene has 93% approval but manufacturing complexity)

**T-45 (Feb 11):** Entry decision
- IV30: 72% (below 50th percentile historical) ✓
- No concerning insider sales ✓
- LunarCrush: Neutral (no red flags) ✓
- **ACTION:** Buy 3% position in stock + 1% in ATM calls (Apr expiry)

**T-20 (Mar 8):** Mid-position check
- Stock: +12% from entry ✓
- IV30: 110% (expansion underway) ✓
- No negative news ✓
- **ACTION:** Hold, set alert for T-10 exit

**T-10 (Mar 18):** Exit window opens
- Stock: +18% from entry
- IV30: 185% (near peak)
- **ACTION:** Exit full position
- **Result:** +18% equity gain, ~+85% on calls

**T+1 (Mar 29):** PDUFA outcome (we're not holding)
- Approval → Stock gaps +40%... but we already exited with profit
- CRL → Stock gaps -55%... but we're not exposed

**Key Insight:** We captured 18% of the 40% move with zero binary risk.

---

## Appendix A: Therapeutic Area Risk Adjustments

From ODIN v9.1 HINT analysis (historical CRL rates):

| Therapeutic Area | CRL Rate | Risk Tier | Adjustment |
|-----------------|----------|-----------|------------|
| Pain Management | 41.9% | HIGH | -0.286 |
| Hematology | 35.7% | HIGH | -0.224 |
| Nephrology | 31.0% | HIGH | -0.177 |
| Ophthalmology | 26.5% | HIGH | -0.131 |
| CNS/Neurology | 23.2% | MOD | -0.098 |
| Cardiovascular | 21.4% | MOD | -0.081 |
| Metabolic/Endocrine | 20.0% | MOD | -0.067 |
| Rare Disease | 17.6% | MOD | -0.043 |
| Immunology | 11.8% | LOW | +0.016 |
| Dermatology | 10.5% | LOW | +0.028 |
| Oncology | 7.2% | LOW | +0.061 |
| GI/Hepatology | 6.7% | LOW | +0.067 |
| Respiratory | 4.3% | LOW | +0.090 |
| Infectious Disease | 3.0% | LOW | +0.103 |
| Vaccines | 0% | LOW | +0.133 |

---

## Appendix B: Insider Trading Red Flags

### F013 Severity Scoring Framework
| Score Range | Interpretation | Action |
|-------------|---------------|--------|
| 0-20 | Routine (10b5-1 plan, vesting) | Ignore |
| 21-40 | Minor (tax withholding, diversification) | Note |
| 41-60 | Moderate (discretionary timing, clusters) | Caution |
| 61-80 | Elevated (late sales, CEO/CFO selling) | Strong signal |
| 81-100 | Severe (multiple insiders, unusual size) | Exit/Short |

### Key Indicators
- **Discretionary Ratio >0.6:** More than 60% of sales are non-automated
- **CEO/CFO Sales T-14:** C-suite selling within 2 weeks of PDUFA
- **Late Cluster:** >50% of all insider sales in final 2 weeks
- **Multiple Insiders:** 3+ different insiders selling same period

---

## Appendix C: Options Greeks Cheat Sheet

For vol-expansion straddle trades:

| Greek | What It Measures | Our Focus |
|-------|-----------------|-----------|
| Delta | Price sensitivity | Near-zero for ATM straddle |
| Gamma | Delta change rate | Increases as PDUFA approaches |
| Theta | Time decay | ENEMY - we lose money daily |
| Vega | IV sensitivity | FRIEND - we profit from IV expansion |

**Critical Ratio:** Vega × ΔIV > Theta × Days Held

Example: If Vega = 0.15 and IV increases 50 points, we gain $7.50/share, offsetting ~15 days of theta decay at $0.50/day.

---

## Disclaimer

This playbook is for educational and research purposes only. All strategies involve significant risk including total loss of capital. Past performance does not guarantee future results. PDUFA dates can change without notice. Always verify information from official FDA sources. Consult a licensed financial advisor before trading.

---

*Document generated from ODIN Phase 2 Research Architecture + supplemental web research.*
*Integration with existing ODIN v9.1 prediction framework for signal prioritization.*
