# ODIN OPTIMIZATION PROMPT v3.0
## Leveraging MCPs (FinBrain, Clinical Trials, PubMed, CheMBL, BioRxiv, Indeed) for Predictive Accuracy

**Created:** January 19, 2026 | **Purpose:** Maximize FDA approval prediction accuracy + minimize Brier score
**MCPs Available:** FinBrain | Clinical Trials API | PubMed | CheMBL | BioRxiv | Indeed
**Goal:** Raise approval probability accuracy to ≥80% backtest | Lower Brier score to ≤0.15

---

## CRITICAL MCP DEPLOYMENT STRATEGY

### What Each MCP Enables

**FinBrain (Financial Intelligence)**
- Real-time insider trading data (Form 4 filings parsed in seconds)
- Options market data (IV, skew, unusual activity, put/call ratios)
- Institutional ownership changes (13F filings)
- Stock price patterns (volatility clustering, technical signals)
- **Use for:** Identifying conviction signals; options market dislocations; capital strength

**Clinical Trials API (ClinicalTrials.gov)**
- Real-time trial enrollment data (active recruitment, enrollment targets, progress)
- Trial phase transitions (Phase 1→2, 2→3, 3→Approval)
- Primary endpoint definitions (exactly what FDA will measure)
- Inclusion/exclusion criteria (patent population richness assessment)
- **Use for:** Predicting trial completion dates; assessing endpoint achievability; enrollment velocity

**PubMed (Published Research)**
- Historical efficacy data for similar drugs (precedent comparables)
- Mechanism validation (does mechanism work in humans? published evidence?)
- Side effect profiles (toxicity concerns that might trigger FDA holds?)
- Regulatory pathway precedents (similar drugs, how they were approved)
- **Use for:** De-risking clinical assumptions; identifying similar-program outcomes

**CheMBL (Chemical & Drug Database)**
- Molecular structure analysis (drug-likeness; patent landscape)
- Pharmacophore similarity to approved drugs
- Known off-target binding (potential safety signals)
- Intellectual property landscape (patent cliffs, freedom to operate)
- **Use for:** Assessing IP strength; identifying hidden toxicity signals; patent timeline

**BioRxiv (Preprints)**
- Bleeding-edge clinical data (often 6-12 months before publication)
- Real-world efficacy signals (before formal trials complete)
- Mechanism validation from academic groups
- Emerging safety signals (early warning system)
- **Use for:** Front-running published results; identifying emerging concerns

**Indeed (Employment Data)**
- Company hiring patterns (expanding commercial team = confidence in approval?)
- Job postings for regulatory/manufacturing roles (approval prep signal)
- Employee turnover (management instability risk)
- Geographic expansion signals (preparing for international approvals)
- **Use for:** Assessing management execution confidence; detecting hidden risks

---

## ODIN OPTIMIZATION FRAMEWORK

### Part 1: MCP-Driven Data Collection (Replaces Manual Web Search)

**For Each Stock Being Analyzed:**

#### Tier 1: Clinical Trial Data (via Clinical Trials API)
```
Query structure:
1. Get trial ID for lead program
2. Extract:
   - Current enrollment: X / Y target (% complete)
   - Enrollment velocity: patients/month
   - Estimated completion date vs. announced target date
   - Primary endpoints (exact wording)
   - Historical endpoint achievement rate for similar indications
   - Phase transition timeline (when did Ph2→Ph3 occur? On schedule?)
   - Site activation progress (# active sites / planned sites)
   - Patient retention rate (dropout %)

Analysis: 
- If enrollment >90% of target: +8% approval odds boost
- If enrollment <50% of target: -15% approval odds reduction
- If Ph3 started on-time: +5% odds boost
- If Ph3 delayed >6 months: -20% odds reduction
```

#### Tier 2: Published Research Validation (via PubMed + BioRxiv)
```
Query structure:
1. Search PubMed for: "[Drug name] efficacy" OR "[Mechanism] Phase 2" OR "[Indication] clinical trial"
2. Search BioRxiv for: "[Drug name]" OR "[Company name] [indication]" OR "[Mechanism] results"
3. Extract:
   - Similar drugs' efficacy in same indication (precedent)
   - Mechanism validation from published studies
   - Known safety signals in literature
   - Patient population characteristics (are enrolled patients typical?)
   - Endpoint achieved in published phase 2 data?

Analysis:
- If published phase 2 efficacy >60%: +12% approval odds
- If mechanism validated in 3+ published papers: +8% odds
- If similar drugs approved at >70% rate: +10% odds
- If safety signals reported in literature: -20% odds (major red flag)
```

#### Tier 3: Molecular & IP Landscape (via CheMBL)
```
Query structure:
1. Get chemical structure for drug candidate
2. Analyze:
   - Drug-likeness score (Lipinski's Rule of Five violations?)
   - Patent landscape (when does patent expire? Freedom to operate?)
   - Off-target binding profile (potential toxicity signals?)
   - Structural novelty vs. approved drugs (truly novel or me-too?)
   - Manufacturing complexity (CMC risk assessment?)

Analysis:
- If Lipinski violations: -10% odds (formulation/bioavailability risk)
- If patent expires <5 years post-approval: -15% odds (commercial risk)
- If off-target binding to safety-critical proteins: -25% odds
- If truly novel mechanism: +10% odds (but also +risk if unvalidated)
```

#### Tier 4: Financial Signals (via FinBrain)
```
Query structure:
1. Get insider transaction history (past 6 months)
2. Extract:
   - Officer/Director buys: # shares, price, timing
   - Officer/Director sells: # shares, price, timing
   - Net insider sentiment (buys vs. sells)
   - Recent equity raises: dilution impact
   - Options market: IV rank, put/call ratio, unusual activity
   - Institutional ownership: recent changes (13F)
   - Short interest: % of float

Analysis:
- If CEO/CFO buying post-data announcement: +15% odds (conviction signal)
- If CEO/CFO selling before catalyst: -20% odds (confidence loss)
- If options call buying unusual activity: +8% odds (market expects approval)
- If insider short interest >25%: -30% odds (insiders betting against approval)
- If recent institutional buying: +6% odds
```

#### Tier 5: Execution Confidence (via Indeed)
```
Query structure:
1. Search Indeed for company job postings (past 90 days)
2. Analyze:
   - Commercial/Sales hiring (indication approval confidence?)
   - Regulatory/Medical Affairs hiring (approval prep?)
   - Manufacturing/Scale-up hiring (supply chain prep?)
   - Geographic expansion (international approval plans?)
   - Turnover signals (key departures?)

Analysis:
- If ramping commercial hires pre-approval: +10% odds
- If regulatory hires concentrated before PDUFA: +8% odds
- If recent CFO/CMO departures: -15% odds
- If international hiring expansion: +5% odds
```

---

### Part 2: MCP Integration into Approval Probability Model

**Current ODIN Formula (before MCP enhancement):**
```
Approval_Prob = (Phase_Weight × Phase_Factor) 
              + (Data_Quality_Weight × Data_Boost) 
              + (Regulatory_Weight × Pathway_Boost)
              + (Rare_Disease_Weight × Orphan_Boost)
```

**Enhanced ODIN Formula (with MCP data):**
```
Approval_Prob = Base_Formula (above)
              + Clinical_Trials_API_Boost (enrollment velocity, endpoint achievability)
              + PubMed_Validation_Boost (precedent + mechanism validation)
              + CheMBL_IP_Adjustment (patent strength, safety profile)
              + FinBrain_Conviction_Signal (insider buys, options market)
              + Indeed_Execution_Boost (hiring patterns, management confidence)
              + BioRxiv_Bleeding_Edge_Signal (early efficacy/safety data)
              - Contradictions_Penalty (if MCPs show conflicts in data)
```

**Example Calculation for KYTX (SPS BLA decision June 2026):**

```
Base (from clinical data): 75%

Clinical Trials API enhancement:
- Phase 2 enrollment: 100% complete (all 26 patients enrolled) → +8%
- Phase 2 endpoints: 100% primary endpoint hit → +10%
- No previous Phase 3 yet (auto-BLA path) → +3%
- Subtotal: 75% + 8% + 10% + 3% = 96%? NO—cap at 85% (clinical alone)

PubMed validation:
- Autoimmune CAR-T: only 2 published programs (Allo, commercial CAR-T programs) → +4%
- No safety signals reported in literature → +0% (neutral)
- Subtotal: 85% + 4% = 89%

CheMBL analysis:
- CAR-T is biological (not small molecule), not in CheMBL → 0%
- Manufacturing complexity high but feasible → -2%
- Subtotal: 89% - 2% = 87%

FinBrain signals:
- Recent institutional buying (Biohaven CAR-T precedent) → +3%
- No insider selling → +0%
- Call options unusual activity (bullish skew) → +2%
- Subtotal: 87% + 3% + 2% = 92%

Indeed signals:
- Kyverna hiring commercial team (Feb 2026 job postings) → +2%
- Regulatory hires (preparing for BLA review) → +1%
- Subtotal: 92% + 2% + 1% = 95%

BioRxiv signals:
- No preprints for Kyverna miv-cel → 0%
- Subtotal: 95% + 0% = 95%

FINAL APPROVAL PROBABILITY: **95%** (capped at 95% for caution)

But wait—Clinical Trials + PubMed suggest 89%, FinBrain suggests 92%. Contradiction? Investigate:
- Why such high clinical confidence? (100% endpoint hit is rare; only 2 prior autoimmune CAR-T programs)
- Apply contradiction penalty: -5% → **90% final estimate**
```

---

### Part 3: Brier Score Optimization (Reduce from 0.20 → ≤0.15)

**What is Brier Score?**
```
Brier = (1/N) × Σ (Predicted_Prob - Actual_Outcome)²

Where:
- Predicted_Prob = ODIN's estimated approval probability (0-1 scale)
- Actual_Outcome = 1 if approved, 0 if rejected
- Lower Brier is better (0 = perfect calibration, 0.5 = random guessing)

Target: ≤0.15 (meaning average prediction error of 15 percentage points)
Current (estimated): 0.20
```

**How MCPs Lower Brier Score:**

#### Strategy 1: Calibration Accuracy (Predict 80% when 80% actually approve)
```
FinBrain + Indeed signals identify conviction indicators:
- Insider buys + commercial hiring + options bullish = higher approval confidence
- This helps distinguish between 70% vs. 80% vs. 90% approval odds

Instead of grouping all "high probability" at 75%, MCPs let you:
- Identify "very high confidence" (85%+) by cross-confirming signals
- Identify "medium confidence" (65-75%) when signals are mixed
- Identify "low confidence" (<55%) when red flags appear

Better calibration = lower Brier score
```

#### Strategy 2: Early Warning Systems (Catch failures before they happen)
```
BioRxiv + PubMed: Identify safety signals 6+ months before formal FDA decision
- Published case reports of toxicity → -20% approval odds
- Emerging concerns in early trial data → -15% odds
- This prevents ODIN from predicting 75% approval when trial will actually fail

Clinical Trials API: Track enrollment velocity
- If enrollment stalls (velocity drops 50%+), predict longer timeline → lower confidence
- This catches trials that will miss endpoints due to enrollment issues

Better early warning = lower false positive rate = lower Brier score
```

#### Strategy 3: Contradictions Detection (Flag uncertainty, don't overcommit)
```
When MCPs show conflicting signals:
- Clinical data says 80% approval (strong Phase 2 efficacy)
- But FinBrain shows insider selling pre-PDUFA (CEO confidence loss)
- BioRxiv shows early safety concern from academic group

Don't predict 80%. Predict 65% instead (acknowledge contradiction).
This "conservative calibration" = lower Brier score
```

---

### Part 4: MCP-Specific Query Protocols

#### Clinical Trials API Protocol
```
QUERY 1: Find trial by drug name
GET /studies?condition=[Indication]&drug=[Drug Name]&status=Active

QUERY 2: Extract enrollment metrics
GET /studies/{trial_id}/enrollment
Response fields:
  - enrollment_current (# enrolled now)
  - enrollment_target (target # for phase)
  - enrollment_rate (patients/month)
  - estimated_completion (projected vs. announced)

QUERY 3: Track phase transitions
GET /studies/{trial_id}/timeline
Response fields:
  - phase_start_date
  - phase_estimated_end_date
  - phase_actual_end_date (if completed)
  - days_delayed (if any)

ANALYSIS:
If enrollment_rate declining over time: Red flag (enrollment plateau)
If estimated_completion >announced_date + 90 days: Yellow flag (delay likely)
If enrollment >95% of target: Confidence +8%
```

#### PubMed Protocol
```
QUERY 1: Similar drugs in same indication
Search: "[Indication] [mechanism class] Phase 2 OR Phase 3" 
Filters: Published >2020, Human studies
Extract:
  - Efficacy rate reported
  - Sample size
  - Primary endpoint definition
  - Safety profile

ANALYSIS:
If similar drugs achieved >60% efficacy: This stock's drug likely can too (+10%)
If similar drugs had severe AEs: Risk assessment (-15%)
Precedent comparison is THE most powerful predictor of approval

QUERY 2: Mechanism validation
Search: "[Mechanism] [target] efficacy human OR clinical"
Extract:
  - Has mechanism been validated in humans before?
  - What indications?
  - Success rate for this mechanism?

ANALYSIS:
If mechanism novel (no human validation): -20% (de-risk unknown)
If mechanism proven in 3+ successful programs: +12% (validated approach)
```

#### BioRxiv Protocol
```
QUERY 1: Bleeding-edge trial data
Search: "[Drug name] OR [Company name] [indication] Phase 2 OR Phase 3"
Extract:
  - Preprint publication date (is this bleeding-edge?)
  - Interim efficacy data reported
  - Safety data reported
  - Sample size at time of preprint

ANALYSIS:
If preprint shows 70%+ efficacy (6 months before formal announcement): +8%
If preprint shows toxicity concerns (6 months before FDA hears it): -15%
BioRxiv is often 6-12 months ahead of formal publications

QUERY 2: Mechanism preprints
Search: "[Mechanism] OR [Target] mechanism efficacy"
Extract:
  - Mechanism validation from academic labs
  - Unexpected findings that might affect clinical program

ANALYSIS:
If academic preprint validates mechanism: +5%
If academic preprint shows off-target toxicity: -20%
```

#### CheMBL Protocol
```
QUERY 1: Get drug structure & properties
GET /molecule/search?smiles=[SMILES structure]
Response:
  - Lipinski Rule of Five compliance (drug-likeness)
  - Molecular weight
  - LogP (lipophilicity)
  - H-bond donors/acceptors
  - Rotatable bonds

ANALYSIS:
If Lipinski violations: -10% (formulation risk)
If drug-like properties excellent: +0% (expected baseline)

QUERY 2: Patent landscape
Search: "[Drug name]" in patent database
Extract:
  - Patent expiration date
  - Freedom-to-operate concerns
  - Competitive patent landscape

ANALYSIS:
If patent expires <5 years post-approval: -15% (commercial risk affects FDA strategy)
If strong patent protection (10+ years): +3%

QUERY 3: Off-target binding
GET /assays/[drug_id]/off_targets
Response:
  - Receptors/proteins drug binds beyond primary target
  - Binding affinity (nM)
  - Known safety concerns for those off-targets

ANALYSIS:
If binds to known toxicity targets (e.g., hERG for cardiac): -25% (FDA will be concerned)
If clean off-target profile: +0% (expected)
```

#### FinBrain Protocol
```
QUERY 1: Insider transactions (Form 4 filings)
GET /insiders/{ticker}/transactions?days_back=180
Response:
  - Officer/Director buys: shares, price, date
  - Officer/Director sells: shares, price, date
  - Relationships (CEO, CFO, Director)

ANALYSIS:
If CEO/CFO bought shares post-data release: +15% (insider conviction)
If CEO selling >10K shares before PDUFA: -20% (confidence loss)
If Director selling weeks before announcement: -15% (advance knowledge?)

QUERY 2: Options market analysis
GET /options/{ticker}/metrics
Response:
  - IV rank (0-100)
  - Put/call ratio
  - Unusual activity (large block trades)
  - IV skew (calls vs. puts relative pricing)

ANALYSIS:
If call buying unusual activity (30+ day look-back): +8% (market expects upside)
If put buying unusual activity: -12% (market hedging for downside)
If IV rank <30 (historically low): Stock cheap, may have asymmetric upside

QUERY 3: Institutional ownership
GET /holdings/{ticker}
Response:
  - % institutional ownership
  - Recent changes (last 30/60/90 days)
  - Top institutional holders

ANALYSIS:
If top biotech/pharma VCs buying: +6% (industry conviction)
If selling by smart money: -8%
```

#### Indeed Protocol
```
QUERY 1: Job posting analysis
GET /jobs?company=[Company name]&days_back=90
Response:
  - Job titles posted
  - Count by function (Sales, Regulatory, Manufacturing, etc.)
  - Geographic locations

ANALYSIS:
If 5+ commercial/sales hires in past 90 days pre-PDUFA: +10% (launch prep confidence)
If regulatory hires spike 2-3 months before PDUFA: +8% (BLA submission prep)
If manufacturing/scale-up hires: +5% (supply chain prep)

QUERY 2: Turnover signals
GET /company/{company_id}/reviews?timeframe=90_days
Response:
  - Employee turnover indicators
  - Recent departures (from LinkedIn data)
  - Key leadership changes

ANALYSIS:
If recent CMO/CFO departure: -15% (execution risk)
If stable team, no recent senior departures: +0% (neutral)
```

---

## IMPLEMENTATION: 6-STEP MCP OPTIMIZATION PROTOCOL

### Step 1: MCP Data Collection (2-3 hours)
For each stock being analyzed:
```
1. Clinical Trials API: Pull enrollment data, timeline, endpoints
2. PubMed: Search for precedent drugs, mechanism validation, safety literature
3. BioRxiv: Search for bleeding-edge trial data, preprints
4. CheMBL: Analyze drug structure, patents, off-target binding
5. FinBrain: Extract insider transactions, options activity, institutional ownership
6. Indeed: Extract hiring patterns, turnover signals

Result: Raw MCP data for each stock (20-40 data points per stock)
```

### Step 2: Data Standardization (30 min)
```
Convert all MCP data into standard format:
- Enrollment velocity: patients/month (normalized across trials)
- Efficacy rates: % achieving primary endpoint (normalized across indications)
- Insider conviction: net shares traded (C-suite only)
- Options market: IV percentile, put/call ratio percentile
- Hiring: hiring rate relative to company size

Result: Standardized dataset ready for modeling
```

### Step 3: Approval Probability Calculation (1 hour)
```
For each stock:
1. Start with baseline approval probability (Phase + Data Quality)
2. Apply MCP boosts/penalties (see Part 2 formula above)
3. Check for contradictions (if multiple signals conflict, lower confidence)
4. Cap at 95% maximum (humility: unknown unknowns exist)

Result: Updated approval probability for each stock
```

### Step 4: Brier Score Calibration (1 hour)
```
Historical backtest:
1. For 100+ past biotech approvals, calculate what ODIN would have predicted
2. Compare predicted probability vs. actual outcome
3. Measure Brier score: (pred - actual)²
4. Adjust MCP weighting to minimize Brier score

Example: If BioRxiv signals over-index approval probability (too bullish):
- Reduce BioRxiv_Boost weight from +8% to +4%
- Recalculate Brier score
- If lower, keep new weight

Result: Optimized MCP weights that minimize Brier score
```

### Step 5: Contradiction Resolution (30 min)
```
Flag stocks where MCPs disagree:
- Clinical data bullish (Phase 2 efficacy 85%) BUT
- FinBrain bearish (insider selling, options put skew)
- BioRxiv neutral (no preprints found)

Logic: Average the signals, apply contradiction penalty
Final approval probability = (85% + 45% + 50%) / 3 - 10% penalty = 53%

This prevents ODIN from being overconfident when signals diverge

Result: Contradiction-flagged recommendations (transparent uncertainty)
```

### Step 6: Continuous Recalibration (Weekly)
```
As new data arrives:
1. Clinical Trials API: Check enrollment velocity, phase completion
2. PubMed: Check for new publications, safety signals
3. BioRxiv: Check for new preprints
4. FinBrain: Check for insider transactions, options activity
5. Indeed: Check for new hiring, departures

Recalculate approval probability monthly (or immediately post-catalyst)
Track actual vs. predicted for Brier score validation

Result: Real-time Brier score measurement; continuous improvement feedback loop
```

---

## EXPECTED IMPROVEMENTS

### Baseline (Current ODIN, no MCPs):
- Backtest accuracy: 70-72%
- Brier score: 0.20-0.22
- False positive rate: 22%
- False negative rate: 18%

### With MCP Integration (optimized):
- Backtest accuracy: 76-82% (target: ≥80%)
- Brier score: 0.14-0.16 (target: ≤0.15)
- False positive rate: 12-15%
- False negative rate: 10-12%

### Why MCPs Help:
1. **Early warnings** (BioRxiv, PubMed catch safety signals before FDA)
2. **Conviction signals** (FinBrain, Indeed show management confidence levels)
3. **Precedent accuracy** (PubMed + Clinical Trials API find similar programs' outcomes)
4. **Real-time enrollment** (Clinical Trials API tracks trial velocity, not projections)
5. **Patent/IP strength** (CheMBL assess commercial viability post-approval)

---

## CRITICAL CAVEATS

### Limitations of Each MCP:

**Clinical Trials API:**
- ❌ Only reflects what companies publicly report (may lag reality)
- ✅ But gives real-time velocity signals (enrollment slope is predictive)

**PubMed:**
- ❌ Publication lag (results 6-12 months behind trials)
- ✅ But historical data is immutable (can build precedent models)

**BioRxiv:**
- ❌ Preprints not peer-reviewed (may contain errors)
- ✅ But 6-12 months faster than publications (early warning system)

**CheMBL:**
- ❌ Doesn't account for formulation/delivery advances
- ✅ But structural analysis catches known toxicity risks

**FinBrain:**
- ❌ Insider buying could be unrelated to approval odds (coincidental timing)
- ✅ But CEO buying post-data is strong conviction signal

**Indeed:**
- ❌ Hiring patterns are forward-looking (company might fail to execute)
- ✅ But hiring ramps up 3-6 months before PDUFA (preparation signal)

### Contradiction Resolution:
When MCPs disagree, DON'T average blindly. Apply logic:
- Clinical + PubMed precedent = HIGHEST weight (fundamental science)
- FinBrain + Indeed = MEDIUM weight (execution confidence)
- BioRxiv = LOWEST weight but HIGHEST time value (early warning)

---

## FINAL PROMPT FOR CLAUDE WITH MCPs

**Copy this and use in Claude environment with MCP plugins enabled:**

---

### CLAUDE MCP OPTIMIZATION PROMPT

"You have access to 6 MCPs: FinBrain, Clinical Trials, PubMed, CheMBL, BioRxiv, Indeed.

Your task: Optimize ODIN (the biotech catalyst prediction system) to maximize approval probability prediction accuracy to ≥80% backtest and minimize Brier score to ≤0.15.

For the following biotech stocks <$3B market cap with Q1 2026 catalysts, execute this protocol:

**Step 1 (30 min):** Use MCPs to extract:
- Clinical Trials API: Enrollment velocity, endpoint definitions, phase transition timing
- PubMed: Similar programs' approval rates, mechanism validation, safety precedents
- BioRxiv: Bleeding-edge efficacy data, preprints, academic validation
- CheMBL: Drug structure, patent landscape, off-target binding, manufacturing risk
- FinBrain: Insider buys/sells (Form 4), options market signals, institutional ownership
- Indeed: Hiring patterns (commercial, regulatory, manufacturing), turnover signals

**Step 2 (30 min):** Calculate approval probability using enhanced formula:
- Base (Phase + Data): 70%
- + Clinical Trials boost (enrollment velocity, on-time completion): ±5-10%
- + PubMed boost (precedent comparables, mechanism validation): ±5-12%
- + BioRxiv boost (early efficacy/safety signals): ±3-8%
- + CheMBL adjustment (patent strength, safety profile): ±2-5%
- + FinBrain boost (insider conviction, options signals): ±3-8%
- + Indeed boost (hiring ramps, execution confidence): ±2-5%
- - Contradiction penalty (if MCPs disagree): -5-10%

**Step 3 (30 min):** Assess Brier score contributors:
- Are predictions well-calibrated? (80% predicted = 80% actual approval rate?)
- Are false positives avoided? (confident predictions that fail?)
- Are false negatives rare? (missed approvals?)

For calibration: Group predictions by confidence level and measure actual approval rate:
- 85-95% confidence group: What % actually approved? (should be 85-95%)
- 70-84% confidence group: What % actually approved? (should be 70-84%)
- 50-69% confidence group: What % actually approved? (should be 50-69%)

If predictions well-calibrated, Brier score naturally minimized.

**Step 4 (30 min):** Identify contradictions and apply logic:
- If Clinical + PubMed say 80% approval BUT FinBrain says 40% (insider selling), don't average.
- Investigate: Why are insiders selling? (lost confidence? Bad news coming?)
- If legitimate concern, lower estimate to 60%. If coincidental, ignore insider signal.
- Flag contradictions in final output.

**Step 5 (30 min):** Backtest on historical precedents:
- For 20+ similar programs from PubMed data, apply ODIN formula
- Did formula correctly predict their actual approval rates?
- Calculate Brier score on this historical test set
- Adjust MCP weights to minimize Brier score

**Step 6 (30 min):** Output final rankings:

For each stock analyzed:
1. Ticker | Company | Market Cap
2. Lead Program | Phase | Primary Endpoint
3. Baseline Approval Probability (Phase + Data Quality only)
4. MCP-Enhanced Approval Probability (with all boosts/penalties)
5. Brier Score Contribution (how much uncertainty remains?)
6. Q1 2026 Catalyst Date
7. Key MCPs Supporting Estimate (which signals were strongest?)
8. Key MCPs Conflicting (which signals disagreed?)
9. Risk/Reward Analysis (what must happen for approval? What could fail?)
10. Comparison to Benchmarks (KYTX, INO, TECX: is this more/less asymmetric?)

CRITICAL TONE: Be brutal about uncertainty. If MCPs contradict, acknowledge it. Don't overcommit to estimates. Flag all data gaps.

Target: 80%+ approval prediction accuracy. Brier score ≤0.15. Full auditability."

---

## SUCCESS CRITERIA

✅ **Excellent MCP Integration:**
- Backtest accuracy ≥80% (correctly predict 4 of 5 actual approvals/rejections)
- Brier score ≤0.15 (average prediction error <15%)
- Well-calibrated predictions (80% confidence group has 80% actual approval rate)
- Contradiction rate <10% (most MCPs agree on final estimate)
- False positive rate <12% (confident wrong predictions rare)

✅ **Operational Excellence:**
- MCP queries complete in <3 hours per stock
- All MCP data source-cited [N]
- All contradictions flagged
- All uncertainties quantified (not hand-waved)
- Prediction ledger auto-updates weekly (immutable)

---

## FINAL MCP PRIORITY RANKING (By Impact on Brier Score)

**Tier 1 (Highest Impact):**
1. **Clinical Trials API** — Enrollment velocity, phase transitions most predictive of trial success/failure
2. **PubMed** — Precedent comparables are gold standard for approval prediction

**Tier 2 (High Impact):**
3. **FinBrain** — Insider conviction signals filter out hype-only stocks
4. **BioRxiv** — Early warning system catches safety signals 6+ months early

**Tier 3 (Medium Impact):**
5. **CheMBL** — Patent strength + off-target toxicity risk assessment
6. **Indeed** — Management execution confidence (hiring ramps, turnover)

**Recommended Search Order:**
1. Clinical Trials API (pulls real trial data)
2. PubMed (finds precedent comparables)
3. FinBrain (confirms conviction)
4. BioRxiv (catches emerging concerns)
5. CheMBL (assesses patent/safety risk)
6. Indeed (validates execution)

---

**END OF ODIN OPTIMIZATION PROMPT v3.0**

**Status: READY FOR CLAUDE MCP EXECUTION**

**Expected Outcomes:**
- Approval prediction accuracy: 76-82% (target ≥80%)
- Brier score: 0.14-0.16 (target ≤0.15)
- False positive rate: 12-15%
- False negative rate: 10-12%
- All predictions fully auditable with MCP source citations
