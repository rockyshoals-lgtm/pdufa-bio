# ODIN Options Module Development - Session Handoff
**Date:** 2026-01-25
**Status:** PLANNING COMPLETE - READY FOR IMPLEMENTATION
**Priority:** HIGH

---

## SESSION SUMMARY

This session developed a comprehensive options trading strategy framework for ODIN v9.0 to complement PDUFA predictions with actionable options recommendations. The framework synthesizes research from 6 uploaded documents covering 13,800+ clinical trials and establishes the theoretical and practical foundation for automated options entry/exit timing.

---

## DOCUMENTS ANALYZED (All in /mnt/user-data/uploads/)

| File | Lines | Key Content |
|------|-------|-------------|
| `Biotech_Stock_Catalyst_Analysis_Framework.md` | 358 | Historical price patterns 2000-2026, run-up statistics, post-catalyst reversals |
| `Biotech_UOA_and_Option_Data.md` | 365 | UOA detection, Golden Sweep criteria, API implementation pseudocode |
| `Biotech_Options__Timing__Volatility__Profit.md` | ~300 | IV crush mechanics, 4-phase volatility cycle |
| `Biotech_Options_Trading_Strategy.md` | ~300 | (Duplicate of above) |
| `Biotech_Options_Trading_Strategy__1_.md` | ~300 | (Duplicate of above) |
| `OPTIONS_DECISION_QUICKREF` | 303 | Executive decision guide, strategy comparison |
| `catalyst-surge-cheatsheet` | 263 | Entry/exit checklists, position sizing |

---

## THE 4-PHASE VOLATILITY CYCLE (Core Framework)

### Phase 1: Stealth Entry (T-60 to T-45)
- **Status:** "Dead Zone" - catalyst too far for retail attention
- **Action:** BUY OTM calls at baseline IV (<30th percentile)
- **Target strikes:** 15-20% OTM
- **Typical cost:** ~$1.50/contract (historical baseline)
- **Rationale:** Buying "cheap insurance" before IV ramp begins

### Phase 2: Smart Money & IV Ramp (T-30 to T-14)
- **Status:** Institutional accumulation, Golden Sweeps appear
- **IV Inflation:** 40% → 150%+
- **Profit driver:** Vega pumps premium even if stock flat
- **Action:** Monitor volume spikes, potentially add to position
- **Example:** $1.50 call → $4.50 (+200%) from IV alone

### Phase 3: Danger Zone & Peak Premium (T-7 to T-1)
- **Status:** Peak hype, retail rush, premiums "priced for perfection"
- **CRITICAL ACTION:** SELL 50-75% of position
- **Typical gain at this point:** +100% to +433%
- **Trap:** Buying here = paying maximum IV, vulnerable to crush
- **"Free Roll":** Keep 10-20% "moonbag" funded by house money only

### Phase 4: Event & IV Crush (T-0)
- **Phenomenon:** IV collapses 150% → 40% instantly
- **Math:** Option value = Intrinsic + Extrinsic (time + volatility)
- **Result:** Even +20% stock jump may mean -90% option loss if bought at T-7
- **GOLDEN RULE:** NEVER hold through T-0 unless using house money

---

## KEY INSIGHT: IV MORE POWERFUL THAN PRICE

**Example Scenario:**
```
Stock: $100 → $112 (+12%)
Option at T-7 (high IV): +300% gain potential
Option at T+0 (post-crush): +20% gain actual
IV CRUSH COST: -280% in foregone gains

Breakdown:
- T-7 value: +50% from stock drift + 250% from IV ramp = +300%
- T+0 value: +12% from stock move - 200% from IV crush = +12% net
```

Most traders buy at T-7, hold through T+0 → miss entire +300% move.

---

## GOLDEN SWEEP DETECTION CRITERIA

Smart money footprint (T-30 to T-14):

1. **Volume > Open Interest × 2** - New positioning, not closing
2. **OTM strikes** - 10-20% above spot price (aggressive target)
3. **Short expiry** - Expires <30 days after catalyst (precision timing)
4. **Ask-side execution** - Urgent buying, not patient limit orders

**Conceptual Python:**
```python
def find_golden_sweep(ticker, catalyst_date):
    chain = fmp.get_option_chain(ticker)
    for contract in chain:
        if catalyst_date < contract.expiry < catalyst_date + 30:
            if contract.volume > contract.open_interest * 2:
                if contract.strike > current_price * 1.15:
                    # GOLDEN SWEEP DETECTED
                    return True
```

---

## HISTORICAL STATISTICS (From Research)

### Pre-Catalyst Run-Up (T-120 to T-0):
- Positive Phase 3 data: **+13.7%** average drift (p=0.03 at 60-day window)
- Failures: Flat or slightly negative
- Statistical significance: Evidence of insider positioning

### Announcement Day Returns:
| Catalyst | Positive Outcome | Negative Outcome |
|----------|------------------|------------------|
| Phase 2 | +12% | -16% |
| Phase 3 | +11% | -22% |
| PDUFA Approval | +5-9% | N/A |
| PDUFA CRL | N/A | -20-35% |

### Pre-Announcement Run-Up:
| Catalyst | Median | Range |
|----------|--------|-------|
| Phase 2 | +12% | +4% to +24% |
| Phase 3 | +9% | +3% to +18% |
| PDUFA | +7% | +2% to +15% |

### IV Benchmarks for Biotech:
- **Baseline IV (no catalyst):** 40-60%
- **T-30 IV (catalyst approaching):** 80-120%
- **T-7 IV (peak premium):** 150-200%+
- **T+0 IV (post-crush):** 40-60% (back to baseline)

---

## RISK MANAGEMENT STRATEGIES

### Strategy A: Pre-Run Capture (SAFEST - RECOMMENDED)
- Entry: T-60, Exit: T-7
- Win rate: 70-75%
- Avg return: +300-500% per trade
- Zero binary event exposure

### Strategy B: Vertical Spread (Debit Spread)
- Buy expected strike + Sell higher strike
- Benefit: Selling offsets IV crush on long position
- Cost: 17% cheaper than naked call
- Use when: IV already elevated (Phase 2/3)

### Strategy C: Straddle/Strangle (Pure Volatility)
- Buy ATM call + ATM put
- Win condition: Stock move must exceed "Expected Move"
- Use only when: Market underestimating impact

---

## ODIN OPTIONS MODULE - IMPLEMENTATION REQUIREMENTS

### Data Sources Needed:

1. **Historical IV Data** (for baseline/percentile calculations)
   - FMP API: Historical options data endpoint
   - Need: IV percentile at T-60, T-30, T-14, T-7, T-0
   - Compute: Rolling 52-week IV percentile

2. **Current Options Chain** (for real-time monitoring)
   - FMP API: Live option chain with volume, OI, IV by strike
   - FinBrain API: Put/call ratio (already cached for 293 tickers)
   - Track: Volume spikes, Golden Sweep detection

3. **Historical Price Action** (for IV ramp modeling)
   - Polygon API: Minute-level price data T-60 to T+1
   - Compute: Average IV progression curve by therapeutic area

4. **Sentiment & Flow** (for divergence detection)
   - FinBrain: Insider transactions, analyst ratings (cached)
   - LunarCrush: Social sentiment (14/293 complete)

### IV Percentile Calculation:
```python
def calculate_iv_percentile(ticker, current_iv, lookback_days=252):
    """
    IV Percentile = (Days with IV < Current IV) / Total Days * 100
    
    Interpretation:
    - <25%: Options CHEAP - BUY strategies
    - 25-75%: NEUTRAL
    - >75%: Options EXPENSIVE - SELL strategies or avoid
    """
    historical_iv = get_historical_iv(ticker, lookback_days)
    days_below = sum(1 for iv in historical_iv if iv < current_iv)
    return (days_below / len(historical_iv)) * 100
```

### IV Rank Calculation:
```python
def calculate_iv_rank(current_iv, iv_high_52w, iv_low_52w):
    """
    IV Rank = (Current IV - 52W Low) / (52W High - 52W Low) * 100
    
    Shows where IV sits in its 52-week range.
    """
    return (current_iv - iv_low_52w) / (iv_high_52w - iv_low_52w) * 100
```

---

## PREDICTION OUTPUT FORMAT

For each PDUFA event, ODIN should output:

```markdown
## OPTIONS STRATEGY RECOMMENDATION

**Ticker:** ABBV
**PDUFA Date:** March 15, 2026
**ODIN PoS:** 87% (Approval likely)

### Current Status (as of Jan 25, 2026)
- Current IV: 78% (38th percentile - MODERATE)
- Days to PDUFA: T-49
- Entry window: OPEN (T-60 to T-45)

### Recommended Trade
- Action: BUY Feb 21 $185 Calls
- Entry price: $2.10-$2.50/contract
- Contracts: 2-3 (0.5% position size)
- Entry timing: Next IV dip below 30th percentile

### IV Forecast
| Days to PDUFA | IV (Projected) | Status |
|---------------|----------------|--------|
| T-49 (now) | 78% | Wait for dip |
| T-30 | 105% | HOLD |
| T-14 | 140% | MONITOR |
| T-7 | 175% | EXIT HERE |
| T-0 | 50% | CRUSH |

### Expected Outcomes
- Exit at T-7: +320% gain (historical median)
- Hold through T-0 (NOT RECOMMENDED): -85% loss risk
- Win probability: 87% (ODIN PoS) × 0.85 (execution) = 74%

### Risk Management
- Max loss: $525 (2-3 contracts × $2.50 × 100)
- Position size: 0.5% of portfolio
- Exit discipline: MANDATORY sell at T-7

### Supporting Signals
✅ S24: Insider cluster buy (4 insiders, $2.3M)
✅ S21: Bullish PCR (0.42)
✅ S17: Galaxy score spike (+35%)
⚠️ K01: No C-suite liquidation
⚠️ K02: PCR not extreme
```

---

## INTEGRATION WITH EXISTING ODIN SIGNALS

Options module triggers when:
- ODIN PoS >75% (high confidence prediction)
- S21-S23 (PCR signals): Bullish PCR <0.5 OR extreme spike >3.0
- S24-S28 (Insider signals): Cluster buy ≥3 insiders OR whale >$100K
- S17-S20 (Social signals): Galaxy score spike OR smart money divergence
- Kill switches NOT triggered: K01 (C-suite liquidation), K02 (extreme PCR)

---

## VALIDATION FRAMEWORK

Backtest on 2020-2024 PDUFA events:
1. Identify all events where ODIN PoS >75%
2. Simulate Phase 1 entry (T-60 at <30% IV percentile)
3. Simulate Phase 3 exit (T-7)
4. Compute: Win rate, avg return, max drawdown, Sharpe ratio
5. Compare to: Stock-only strategy, hold-through-event strategy
6. **Required thresholds:** Win rate >70%, avg return >250%

---

## API IMPLEMENTATION CHECKLIST

### FMP API Endpoints Needed:
- [ ] `GET /v3/historical-price-full/{symbol}` - Historical prices
- [ ] `GET /v3/option-chain/{symbol}` - Current options chain
- [ ] `GET /v4/option-chain/{symbol}` - Historical options (if available)
- [ ] Rate limiting: Implement exponential backoff

### FinBrain API (Already Cached for 293 tickers):
- [x] Put/call ratio - `/v1/put-call-ratio`
- [x] Insider transactions - `/v1/insider-trades`
- [x] Analyst ratings - `/v1/analyst-ratings`
- [x] LinkedIn metrics - `/v1/linkedin-metrics`

### LunarCrush API (14/293 complete):
- [ ] Complete remaining 280 tickers
- [ ] Sentiment scores for divergence detection

---

## EXISTING ODIN ASSETS REFERENCED

| File | Location | Purpose |
|------|----------|---------|
| `odin_enrichment_cache.json` | `/mnt/user-data/outputs/` | 293 tickers with FinBrain data |
| `ODIN_MASTER_LOGIC_AUDIT.md` | `/mnt/user-data/outputs/` | 37 signals specification |
| `ODIN_SIGNAL_SPECIFICATION_v9.md` | `/mnt/user-data/outputs/` | Billion-config parameters |
| `lunarcrush_cache.json` | `/mnt/project/` | 14 tickers with social data |
| `ODIN_ENRICHED_PDUFA_1349_v2.csv` | `/mnt/project/` | 1,349 PDUFA events |

---

## PREVIOUS SESSION TRANSCRIPTS

| Session | File | Content |
|---------|------|---------|
| LLM API Integration | `/mnt/transcripts/2026-01-25-06-12-07-odin-llm-api-integration-planning.txt` | 7 working APIs, CRL parser |
| FinBrain Enrichment | `/mnt/transcripts/2026-01-25-06-49-40-odin-finbrain-enrichment-complete.txt` | 293 tickers enriched |
| Master Logic Audit | `/mnt/transcripts/2026-01-25-06-51-23-odin-master-logic-signal-audit.txt` | 37 signals, 2.4B configs |
| Options Strategy | `/mnt/transcripts/2026-01-25-06-55-04-odin-options-strategy-framework.txt` | This session (compacted) |

---

## PENDING ACTIONS (Priority Order)

### Immediate (This Session Goal):
1. **Build IV percentile calculator** - 52-week rolling for all 293 tickers
2. **Create IV ramp forecast model** - Segment by therapeutic area
3. **Implement Golden Sweep detector** - Volume > OI × 2, OTM, ask-side

### Short-term:
4. Pull FMP historical IV data (2-year lookback, 293 tickers)
5. Integrate options recommendations into ODIN output format
6. Backtest on 2020-2024 events (validate >70% win rate)

### Medium-term:
7. Complete LunarCrush expansion (280 remaining tickers)
8. Compute S21-S28 signals from FinBrain cache
9. Launch billion-config optimization
10. Process 180 CRLs with OpenAI parser

---

## KEY FORMULAS REFERENCE

### IV Percentile (Preferred):
```
IV_Percentile = (Days_Below_Current_IV / 252) × 100
```

### IV Rank:
```
IV_Rank = (Current_IV - 52W_Low) / (52W_High - 52W_Low) × 100
```

### Vol/OI Ratio (Golden Sweep):
```
Signal = Volume / Open_Interest > 2.0
```

### Moneyness:
```
Moneyness = (Strike - Stock_Price) / Stock_Price
OTM_Target = Moneyness > 0.10 (10%+ out of the money)
```

### Expected Value:
```
EV = (Win_Prob × Avg_Win) - (Loss_Prob × Avg_Loss)
Example: (0.72 × 300%) - (0.28 × 100%) = +188%
```

---

## RESUME INSTRUCTIONS

To continue this work in a new session:

1. **Upload this handoff file** to provide full context
2. **Reference key files:**
   - `/mnt/user-data/outputs/odin_enrichment_cache.json` (293 tickers)
   - `/mnt/project/ODIN_ENRICHED_PDUFA_1349_v2.csv` (1,349 PDUFAs)
   - `/mnt/user-data/uploads/finbrain_cache.json` (FinBrain raw data)

3. **Start with:** "Continue ODIN Options Module development - build IV percentile calculator and Golden Sweep detector"

4. **Next coding task:** Create Python module that:
   - Fetches historical IV from FMP API
   - Calculates rolling 52-week IV percentile
   - Detects Golden Sweeps in current options chain
   - Outputs formatted options recommendations

---

## CRITICAL RULES (Memorize)

1. **Buy Phase 1 ONLY** (T-60 to T-45, IV <30th percentile)
2. **Exit T-7** (no exceptions) - Sell 50-75% of position
3. **NEVER hold through T-0** - IV crush destroys value
4. **Position size: 0.5-1%** per trade maximum
5. **Monthly loss limit: 5%** - Stop trading if hit
6. **Golden Sweep = Signal** - Vol > OI × 2, OTM, ask-side
7. **Divergence is gold** - High UOA + Low sentiment = contrarian opportunity

---

**Status:** READY FOR IMPLEMENTATION
**Next Step:** Build IV percentile calculator and Golden Sweep detector
**Estimated Completion:** 2-3 sessions for full options module
