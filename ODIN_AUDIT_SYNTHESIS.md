# ODIN Audit Synthesis: Claude vs Perplexity

**Date:** 2026-01-23  
**Subject:** Counter-Audit Review & Consensus Findings

---

## Executive Summary

| Claim | Claude | Perplexity | Final Verdict |
|-------|--------|------------|---------------|
| `manufacturing_risk` statistical anomaly | ⚠️ Suspicious | ✅ Noted | **AGREED: Unusual pattern** |
| `manufacturing_risk` is definitely leaked | ❌ Assumed yes | ❌ Assumed no | **UNKNOWN: Need source verification** |
| Model is "broken" at F1=0.85 | ⚠️ Overstated | ✅ "Still useful" | **AGREED: Deployable with caveats** |
| Next step: verify data source | ✅ Yes | ✅ Yes | **AGREED: This is THE question** |

---

## Where Claude Was Wrong

### 1. Assumed Leakage Without Proving Source

**Original claim:** "manufacturing_risk is leaked data with HIGH CONFIDENCE"

**Reality:** I inferred leakage from statistical patterns (47.7% CRL rate, 11.5x lift), but didn't prove WHERE the data came from. Perplexity correctly noted that pre-PDUFA manufacturing signals DO exist (Type B meetings, facility inspections, Warning Letters).

**Revised claim:** "manufacturing_risk has suspicious patterns CONSISTENT WITH leakage, but the actual source is unknown."

### 2. Overstated Model Degradation

**Original claim:** "Model becomes unusable" without manufacturing_risk

**Reality:** F1 dropping from 0.93 → 0.85 is degradation, not failure. An F1 of 0.85 with 92% precision is still valuable as a risk filter. I overstated the severity.

### 3. "Burden of Proof" Framing

Perplexity correctly argued that "prove it's safe before using" is reasonable for trading, but I should have been clearer that this is a VERIFICATION task, not a CONCLUSION.

---

## Where Perplexity Was Wrong

### 1. Also Speculating From the Opposite Prior

Perplexity assumed manufacturing_risk IS T-1 compliant without evidence. They offered *possible* explanations (Type B meetings, facility history) but no proof that ODIN actually used those sources.

**Both audits are speculative** — just from opposite priors:
- Claude: Assumed worst case (conservative for trading)
- Perplexity: Assumed best case (optimistic for deployment)

### 2. Downplayed the Statistical Red Flags

The 47.7% vs 4.1% CRL rate split (11.5x lift) is genuinely unusual. Legitimate pre-PDUFA signals rarely achieve this level of discrimination. Perplexity acknowledged the anomaly but didn't weight it appropriately.

### 3. form_483_issues Empty Is Actually Significant

If manufacturing_risk came from pre-PDUFA inspections, why is `form_483_issues` completely empty? This inconsistency suggests different data sources — possibly one legitimate and one not.

---

## Critical Evidence: Enrichment Source Analysis

```
Enrichment Source × Manufacturing Risk:

Source              Total    mfg=True   mfg CRL Rate
----------------    -----    --------   ------------
rule_based_v1       1093        224        54.9%
web_verified_v2      176         58        17.2%
web_search_batch1     70          3       100.0%
web_search_batch2     10          0          0.0%
```

**Key Finding:** `rule_based_v1` accounts for 224 of 285 mfg_risk=True cases.

**The decisive question:** What was the "rule" in `rule_based_v1`?

| If Rule Was... | T-1 Status | Action |
|----------------|------------|--------|
| "CRL letter mentions CMC" | ❌ LEAKED | Remove feature |
| "Sponsor has prior Form 483" | ✅ COMPLIANT | Keep feature |
| "Unknown AI enrichment" | ⚠️ SUSPECT | Verify or remove |

---

## Consensus Recommendations

Both Claude and Perplexity agree on these next steps:

### Immediate (Day 1)

**David must answer:** What rule populated `manufacturing_risk` in `rule_based_v1`?

- If from CRL letters → **Remove w_mfg_pen, retrain**
- If from pre-PDUFA sources → **Keep it, document source**
- If unknown → **Run sensitivity test below**

### Sensitivity Test (Day 2-3)

```python
# Temporarily disable manufacturing_risk
config['w_mfg_pen'] = 0.0
config['w_mfg_amp'] = 0.0

# Re-run scoring on full dataset
# Measure ACTUAL F1, not theoretical
```

**Expected outcomes:**
- If F1 stays > 0.85 → Model is deployable (mfg_risk wasn't critical)
- If F1 drops to < 0.80 → Model needs rebuilding

### Augmentation (Week 2+)

**Regardless of leakage verdict:** Populate `form_483_issues` from FDA inspection database.

This gives you a PROVABLY T-1 compliant manufacturing signal that:
- Replaces or augments current mfg_risk
- Removes any ambiguity about data source
- May actually improve model performance

---

## The 44 "Irreducible" False Positives

Both audits agree these 44 CRLs lack manufacturing_risk and failed on safety/efficacy grounds:

| CRL | Likely Reason | Missing Signal |
|-----|---------------|----------------|
| Merck KEYTRUDA (HCC, SCLC, TNBC) | Efficacy endpoint miss | Trial outcome data |
| Gilead Filgotinib | Safety (testicular toxicity) | Safety signal in trials |
| AstraZeneca Roxadustat | Cardiovascular safety | Competing label in EU vs US |
| Eli Lilly JARDIANCE (T1D) | Limited efficacy vs risk | Risk/benefit analysis |

**Implication:** To catch these 44, you need features ODIN doesn't currently have:
- Pre-PDUFA clinical trial detailed outcomes
- FDA/EMA regulatory divergence signals
- Safety database (FAERS) early signals

---

## Final Verdict

### Claude's Original Audit: **50% Correct, 50% Speculative**

| Correct | Speculative |
|---------|-------------|
| Statistical anomaly identified | Assumed leakage without proof |
| FP=44 frozen is unusual | Overstated "model is broken" |
| Recommended source verification | Didn't investigate enrichment source |

### Perplexity's Counter-Audit: **50% Correct, 50% Also Speculative**

| Correct | Speculative |
|---------|-------------|
| Pre-PDUFA signals exist | Assumed mfg_risk is compliant |
| F1=0.85 is still useful | Downplayed statistical red flags |
| Verification is the right next step | Didn't acknowledge form_483 gap |

### The Truth

**Neither audit can prove their case without knowing the actual data source.**

The question "Is manufacturing_risk leaked?" can ONLY be answered by David documenting what `rule_based_v1` actually did.

---

## Recommended Decision Tree

```
┌─────────────────────────────────────────────────────────┐
│ Q: What was the source of manufacturing_risk?            │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │CRL Notes│     │Pre-PDUFA│     │Unknown/ │
   │(leaked) │     │(compliant)│   │AI-generated│
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │REMOVE   │     │KEEP     │     │RUN TEST │
   │feature  │     │feature  │     │disable  │
   │Retrain  │     │Document │     │w_mfg_pen│
   │F1≈0.85  │     │source   │     │measure  │
   └─────────┘     └─────────┘     └────┬────┘
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
                  ┌─────────┐                     ┌─────────┐
                  │F1 > 0.85│                     │F1 < 0.80│
                  │Deploy   │                     │Rebuild  │
                  │cautiously│                    │model    │
                  └─────────┘                     └─────────┘
```

---

## Appendix: What Each Audit Got Right

### Claude Strengths
- ✅ Identified exact statistical anomaly (47.7% vs 4.1%)
- ✅ Spotted frozen FP=44 across all configs
- ✅ Noted form_483_issues empty inconsistency
- ✅ Conservative framing appropriate for trading capital

### Perplexity Strengths
- ✅ Correctly identified Claude's assumption gap
- ✅ Documented legitimate pre-PDUFA CMC signals
- ✅ Realistic assessment of F1=0.85 utility
- ✅ Proposed concrete verification checklist

---

*Synthesis completed 2026-01-23*
