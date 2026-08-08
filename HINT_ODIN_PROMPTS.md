# 📋 AI PROMPTS: HINT-ODIN Integration Deep Dive

Copy each prompt to the appropriate AI and run in parallel for maximum insight.

---

## 1️⃣ CLAUDE PROMPT (Engineering - Build the Integration)

```
You are an expert Python engineer building production biotech ML systems.

TASK: Create a production-ready HINT-ODIN integration layer.

BACKGROUND:
- ODIN v9.4: Regulatory FDA approval prediction model (odin_v94_scoring.py)
- HINT: Deep learning clinical trial outcome model (separate PyTorch)
- Goal: Ensemble combining both for 87.5% accuracy (vs 75% HINT alone)
- Scope: Small molecules only (HINT's training domain)

CURRENT STATE:
- ODIN and HINT are completely separate
- No HINT model loading in ODIN code
- No SMILES/ICD-10 processing
- No ensemble blending logic
- Historical backtest shows potential: 70/30 ODIN/HINT = 87.5% accuracy on 16 cases

YOUR TASK - 3 Deliverables:

DELIVERABLE 1: hint_wrapper.py (200-300 lines)
Create a clean interface layer that:
1. Loads HINT Phase III checkpoint from: C:\Users\dcmoo\Documents\Python\hint_models\save_model\phase_III.ckpt
2. Loads BioBERT tokenizer: dmis-lab/biobert-base-cased-v1.1
3. Implements get_smiles(drug_name) → SMILES string
   - Cache results locally (smiles_cache.json)
   - Use pubchempy library for PubChem lookup
   - Handle "drug not found" gracefully
4. Implements get_icd10(indication) → ICD-10 code mapping
   - Basic mapping for common indications (provided in hint_backtest_all_wins.py)
5. Implements score(drug_name, indication, trial_protocol=None) → float (0.0-1.0)
   - Extract protocol features if provided
   - Call HINT model.forward()
   - Return probability clamped [0.01, 0.99]
6. Implement batch scoring with caching
   - Don't reload model for each event
   - Cache SMILES results across batch
   - Add error handling (missing SMILES, invalid drugs)

DELIVERABLE 2: odin_v94_scoring.py modifications
Update the existing file to:
1. Import hint_wrapper at top
2. Add batch_score_with_hint() function that:
   - Takes DataFrame as input (like existing batch_score)
   - For each row:
     a. Calculate ODIN score (existing logic)
     b. If modality='Small Molecule' or 'Peptide': Calculate HINT score
     c. Blend: ensemble = 0.70*odin_prob + 0.30*hint_prob
     d. Add columns: hint_probability, ensemble_probability, ensemble_tier
   - Returns DataFrame with new columns
3. Add conflict detection function:
   - Flag when |ODIN - HINT| > 0.20 (disagreement)
   - Log: "CAUTION: ODIN 85%, HINT 25% - Review conflict"
   - Useful for catching approval bias or regulatory red flags

DELIVERABLE 3: ODIN_v94_CONFIG.json updates
Add sections:
1. "hint_config" with paths and parameters
2. "ensemble_settings": odin_weight: 0.70, hint_weight: 0.30
3. "decision_matrix" from migration package:
   - >85% ODIN + >75% HINT = STRONG_BUY
   - >85% ODIN + <45% HINT = CAUTION
   - etc.

TESTING:
1. Validate on 5 known cases from hint_backtest_all_wins.py:
   - MIST Etripamil (APPROVED): HINT ~85%, ODIN 82% → Ensemble ~83%
   - ALDX Reproxalap (CRL): HINT 88%, ODIN 10% → Ensemble ~40% (catch conflict!)
   - MITO Elamipretide (CRL): HINT 38%, ODIN 20% → Ensemble ~22% (correct)
   
2. Spot check 3 results:
   - Does ensemble improve CRL detection? (should be yes)
   - Does ensemble maintain high approval accuracy? (should be yes)
   - Are conflicts properly flagged? (should be yes)

CONSTRAINTS:
- Use only libraries already in ODIN/HINT environments
- No external APIs except PubChem (via pubchempy)
- Error handling for missing data (no drug found, no protocol)
- Type hints on all functions
- Docstrings explaining each method
- Performance: batch processing should handle 1,933 events in <5 min

DELIVER:
1. hint_wrapper.py (complete, runnable)
2. Code diff for odin_v94_scoring.py (show new functions only)
3. JSON addition for ODIN_v94_CONFIG.json
4. Test results on 5 validation cases
5. Brief summary: "Integration complete. Ensemble accuracy 87.5%. Conflicts properly detected."
```

---

## 2️⃣ CHATGPT PROMPT (Data Architecture & Integration Path)

```
You are a data scientist designing the data integration strategy for a biotech ML ensemble.

TASK: Plan the data architecture for HINT-ODIN integration on 1,933 historical events.

PROBLEM STATEMENT:
- Dataset: ODIN_ENRICHED_PDUFA_v4_2.csv (1,933 FDA approval events)
- Current columns: [31 features related to regulatory pathway]
- Want to add: HINT clinical trial model predictions
- Constraint: HINT only works on small molecules
- Unknown: How many of 1,933 are small molecules?

YOUR ANALYSIS SHOULD ADDRESS:

1. DATA PROFILING
   - Count by modality in the 1,933 events
   - Filter: How many are "Small Molecule" or "Peptide"?
   - Filter: How many are NOT eligible (biologics, gene therapy, etc.)?
   - Output: % coverage ("HINT can score X% of dataset")

2. FEATURE MAPPING
   - ODIN has: indication, therapeutic_area, modality, sponsor_prior_approvals, etc.
   - HINT requires: drug SMILES, ICD-10 code, trial protocol text
   - Mapping task:
     a) ODIN.indication → ICD-10 code? (use mapping from hint_backtest_all_wins.py)
     b) ODIN.asset (drug name) → SMILES via PubChem? (easy, via pubchempy)
     c) ODIN dataset has trial protocol? (Need to check - likely NO)
   - Output: Data transformation pipeline

3. MISSING DATA STRATEGY
   - Scenario A: Drug SMILES not in PubChem (how often?)
   - Scenario B: Trial protocol text not in ODIN dataset (how do we get it?)
   - Scenario C: Indication doesn't map to ICD-10 (fallback to "R69" general code?)
   - Output: Fallback logic for each scenario

4. CACHING & PERFORMANCE
   - Challenge: Scoring 1,933 events × SMILES lookup = slow
   - Solution: Build persistent SMILES cache (JSON file)
   - Questions:
     a) Should we pre-compute all SMILES once? (Time estimate?)
     b) Or cache incrementally as we score?
     c) How to refresh cache if PubChem updates drugs?
   - Output: Caching architecture & timing estimate

5. VALIDATION LOGIC
   - Before scoring 1,933 events, validate on subset
   - Recommendation: Batch 1 (validate), Batch 2-5 (production)
   - Batch 1 should include:
     a) Known approvals (MIST, AGIO, NVS, GILD)
     b) Known CRLs (ALDX, MITO, BHVN)
     c) Edge cases (missing protocol, rare drugs)
   - Output: Validation checklist

6. DATA QUALITY METRICS
   - For the 1,933 events, calculate:
     a) % with valid SMILES (must have >= 95%)
     b) % with ICD-10 mapping (target 100% with fallback)
     c) % with trial protocol (likely <20%?)
   - Decision rule: If SMILES coverage <90%, delay full batch scoring

7. DOWNSTREAM INTEGRATION
   - Once HINT scores computed, dataset will have:
     - odin_v94_probability (existing)
     - hint_probability (new)
     - ensemble_probability = 0.70*odin + 0.30*hint (new)
     - ensemble_tier (new)
     - conflict_flag (YES/NO) (new)
   - Questions:
     a) Should old columns stay for comparison?
     b) What should default be if HINT not applicable (use ODIN only)?
     c) How to export for downstream trading?
   - Output: Final dataset schema

DELIVERABLES:
1. Data profiling report: "X% of 1,933 are small molecules, HINT covers Y% with fallbacks"
2. Feature mapping table: ODIN column → HINT input (3 rows: SMILES, ICD-10, Protocol)
3. Missing data handling: 3 scenarios with fallback logic
4. Caching architecture: JSON structure, refresh strategy
5. Validation plan: Batches, edge cases, metrics
6. Final schema: All new columns that will be added
7. Risk assessment: Where is integration likely to fail?
8. Time estimate: Hours to enrich full 1,933 dataset

CONTEXT:
- HINT backtest used only 16 small molecules (from larger wins ledger)
- Current effort is to scale to full 1,933 historical dataset
- Need to understand data gaps BEFORE Claude starts coding
```

---

## 3️⃣ GEMINI PROMPT (Strategic Business Analysis)

```
You are a strategic biotech investment advisor evaluating a new analytical capability.

QUESTION: Should ODIN incorporate HINT signals into its approval prediction system? When? How?

CONTEXT:
Your portfolio/analysis:
- RCKT: 72% ODIN → Expected 72% with HINT (agreement)
- BMY: 96% ODIN → Expected 97-98% with HINT (HINT bullish)
- JNJ: Unknown → Phase 3 readout 3/31, HINT could add clarity
- GUTS: 40-50% ODIN → HINT N/A (device, not covered)
- Historical: HINT+ODIN ensemble = 87.5% accuracy on 16 validation cases

STRATEGIC QUESTIONS:

1. COMPETITIVE ADVANTAGE
   a) HINT model is published research - does everyone have it?
   b) If you build ensemble, is this a 2-3% edge or table stakes?
   c) What do your competitors (other biotech algo traders) likely do?
   d) Is the edge defensible (your ensemble weights) or transient?
   e) Recommendation: Worth 8-12 hours of engineering time for alpha gain?

2. PORTFOLIO IMPACT QUANTIFICATION
   a) RCKT: If ODIN/HINT consensus at 72%, confidence in straddle sizing?
   b) BMY: If ensemble is 97-98%, should you take larger position?
   c) JNJ: Could HINT reduce uncertainty on Phase 3 binary? (30→20% range?)
   d) GUTS: Device not covered by HINT - leaves your analysis unchanged
   e) Calculate: Expected additional $ gain from better calibration on 2026 catalysts

3. RISK MANAGEMENT
   a) What if HINT model fails? (Error in PyTorch load, model outdated)
   b) What if HINT scores are poorly calibrated for your indications?
   c) Scenario: HINT says 75%, ODIN says 25% - which do you trust?
   d) HINT approval bias: Is 70/30 weight optimal, or should it vary?
   e) How do you handle "no HINT signal" for biologics/devices?
   f) Recommendation: Fallback strategy if HINT unavailable mid-trade?

4. ALTERNATIVE USES OF TIME
   a) 12 hours to build HINT integration = cost of opportunity
   b) Alternative: Spend 12 hours on ChatGPT/Claude/Gemini prompts for RCKT/BMY analysis instead
   c) Alternative: Enhance CEWS (insider/options signal) integration
   d) Alternative: Improve data quality on 1,933 historical dataset
   e) Which highest ROI for your specific goal (2026 PDUFA trading)?

5. VALIDATION REQUIREMENTS
   a) Backtest = 87.5% on 16 cases (small sample, potential overfitting)
   b) What forward-looking metrics prove ensemble works?
   c) How many REAL PDUFA decisions needed? (Suggest: RCKT + BMY + 3 others = 5 outcomes)
   d) Go/no-go decision: If first 5 PDUFAs show <2% ensemble improvement, kill it?
   e) Timeline: Can you afford to wait 2-3 months for validation?

6. OPERATIONAL COMPLEXITY
   a) Adding HINT = more dependencies (torch, transformers, BioBERT)
   b) System maintenance: Who maintains HINT model as PubChem/BioBERT update?
   c) Trading operation: Do you need real-time HINT scoring or batch weekly?
   d) Cost: GPU/CPU for batch processing 1,933 events × updates?
   e) Complexity debt: Is it worth the extra scaffolding?

7. HUMAN JUDGMENT LAYER
   a) HINT: 100% accuracy on approvals - too good?
   b) ODIN: 38% separation on CRLs - is this your main edge?
   c) If ensemble lowers ODIN's CRL detection, is that bad?
   d) Should you weight HINT < 30% because you trust ODIN's regulatory skepticism more?
   e) Recommendation: Should human trader override ensemble in conflicts?

8. DECISION FRAMEWORK
   Present three scenarios:

   SCENARIO A: "YES - Build Now" (if you believe HINT is differentiating)
   - Timeline: Build (2 weeks), validate (4 weeks), deploy (by mid-March)
   - Risk: Overfitting on 16 backtest cases
   - Upside: 87.5% accuracy on April+ PDUFAs

   SCENARIO B: "YES - Build, But Parallel Test First" (if you're unsure)
   - Timeline: Build (1 week), run both ODIN and ensemble on 50 events, compare
   - Risk: Delay on RCKT/BMY (already 72%, 96%)
   - Upside: Validate before betting portfolio on ensemble

   SCENARIO C: "NO - Wait / Skip Entirely" (if you think HINT is table stakes or noise)
   - Timeline: Keep ODIN standalone, refine weights instead
   - Risk: Miss 2-3% accuracy advantage
   - Upside: Simplicity, focus on other edges (CEWS, sentiment, insider)

DELIVERABLES:
1. Competitive analysis: "Is this edge defensible?"
2. Portfolio impact: "$X expected gain if we go from 72% to 73% RCKT confidence"
3. Risk scorecard: Likelihood/impact of HINT failure scenarios
4. Go/no-go framework: "Implement if Y, wait if Z, skip if W"
5. 6-month roadmap: Phased approach to ensemble integration
6. Success metrics: "We succeeded if X, failed if Y"
7. FINAL RECOMMENDATION: With confidence level (High/Medium/Low)

TONE: Strategic, quantitative, address the "why spend 12 hours here" question directly.
```

---

## HOW TO RUN THESE PROMPTS

**Parallel Execution (Recommended):**
1. Copy CLAUDE prompt → Claude or ChatGPT (in code mode)
2. Copy CHATGPT prompt → ChatGPT or Claude (in analysis mode)
3. Copy GEMINI prompt → Gemini

**Sequential (if you prefer):**
1. Start Claude (takes 30-45 min for code implementation)
2. While Claude runs, start ChatGPT (takes 15-20 min for data analysis)
3. While both run, start Gemini (takes 10-15 min for strategic analysis)
4. Gather outputs in 1-2 hours

---

## EXPECTED OUTPUTS

### From Claude:
✅ hint_wrapper.py (complete, importable)
✅ Code diff for odin_v94_scoring.py
✅ JSON additions for config
✅ Test results on 5 validation cases
Time: 30-45 minutes

### From ChatGPT:
✅ Data profiling (% small molecules, coverage)
✅ Feature mapping table
✅ Missing data strategy
✅ Caching architecture
✅ Validation plan
Time: 15-20 minutes

### From Gemini:
✅ Competitive advantage assessment
✅ Portfolio impact quantification
✅ Risk scenario analysis
✅ Go/no-go decision framework with recommendation
✅ 6-month implementation roadmap
Time: 10-15 minutes

---

## NEXT STEPS AFTER PROMPTS

1. **Review Claude output** - Is implementation solid?
2. **Review ChatGPT output** - What % of data is coverable?
3. **Review Gemini output** - What's the recommendation?
4. **Decision meeting** - "Do we build this?"
5. **If YES:** Deploy Claude code, test on small batch, validate on RCKT/BMY/JNJ
6. **If NO:** Stick with ODIN v9.4, focus on other alpha sources

---

## FILE REFERENCES

- Implementation: `/workspace/HINT_ODIN_INTEGRATION_ANALYSIS.md` (this document)
- HINT backtest data: `hint_backtest_all_wins.py` (16 test cases)
- HINT migration package: `ODIN_HINT_MIGRATION_PACKAGE_2026-01-27.md` (results)
- ODIN v9.4 code: `odin_v94_scoring.py` (target for integration)
- ODIN config: `ODIN_v94_CONFIG.json` (update needed)

