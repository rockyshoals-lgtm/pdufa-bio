# ODIN PDUFA Dataset Multi-AI Audit & Enrichment Protocol
## Version: 2026-02-04 | Dataset: 1,933 Events | Target: 2026 PDUFA Completeness

---

# 🔴 CRITICAL RULES FOR ALL AI PARTICIPANTS

1. **T-1 COMPLIANCE**: All feature data must reflect ONLY information available BEFORE the FDA decision date
2. **SOURCE EVERYTHING**: Every data point requires a verifiable source URL or document reference
3. **NO FABRICATION**: If you cannot verify something, mark it as "UNVERIFIED" or "REQUIRES_VERIFICATION"
4. **NO HALLUCINATION**: Do not guess dates, outcomes, or designations - leave blank if unknown
5. **AUDITABILITY**: Your output will be reviewed by another AI - format for machine parsing

---

# 📋 CURRENT DATASET STATE

**File**: `ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv`
**Total Events**: 1,933 (1,600 Approvals, 333 CRLs)
**Years**: 2002-2026
**2026 Events Currently**: 3

### Existing 2026 Records:
| Ticker | Asset | PDUFA Date | Outcome |
|--------|-------|------------|---------|
| EBS | OTC NARCAN Nasal Spray w/ carrying case | 2026-01-14 | APPROVAL |
| FBIO | ZYCUBO (copper histidinate) | 2026-01-13 | APPROVAL |
| ATRA | EBVALLO (Tabelecleucel/ATA-129) | 2026-01-12 | CRL |

### Known 2026 Events NOT Yet in Dataset:
- **AQST** - CRL received (Anaphylax epinephrine sublingual film)
- **PHAR** - CRL received (need to identify product)

### Existing Records for These Tickers:
- **AQST**: 4 prior records (2020-2024) - most recent: Libervant approval 2024-04-29
- **PHAR**: 1 prior record - Leniolisib approval 2023-03-24
- **FBIO**: 8 prior records (2020-2026) - ZYCUBO Jan 2026 already captured

---

# 🟣 PROMPT 1: PERPLEXITY (Research & Fact-Check Specialist)

Copy everything below to Perplexity:

---

## ODIN PDUFA 2026 Research Task - Perplexity

You are the Research & Fact-Check Specialist for the ODIN biotech catalyst prediction system. Your role is to find and verify ALL FDA PDUFA decisions from 2026.

### YOUR SPECIFIC DUTIES:
1. Find ALL 2026 FDA drug approvals (NDA, BLA, sNDA, sBLA)
2. Find ALL 2026 Complete Response Letters (CRLs)
3. Verify regulatory designations for each (BTD, Orphan, Priority Review, Fast Track)
4. Cross-reference multiple sources for accuracy

### KNOWN 2026 EVENTS TO VERIFY/EXPAND:
- FBIO/ZYCUBO (copper histidinate) - APPROVAL ~Jan 13, 2026
- EBS/NARCAN OTC - APPROVAL ~Jan 14, 2026  
- ATRA/EBVALLO - CRL ~Jan 12, 2026
- AQST - CRL (Anaphylax) - NEED DATE AND DETAILS
- PHAR - CRL - NEED PRODUCT, DATE, AND DETAILS

### SEARCH THESE SOURCES:
1. FDA.gov - Drugs@FDA, Novel Drug Approvals, BLA Approvals
2. Company press releases (investor relations pages)
3. SEC EDGAR 8-K filings (CRLs are material events)
4. BioPharmCatalyst.com PDUFA calendar
5. Endpoints News, STAT News, FiercePharma

### OUTPUT FORMAT (JSON for each event):
```json
{
  "ticker": "AQST",
  "company": "Aquestive Therapeutics",
  "asset": "Anaphylax (epinephrine sublingual film)",
  "indication": "Emergency treatment of anaphylaxis",
  "therapeutic_area": "Allergy/Immunology",
  "catalyst_date": "YYYY-MM-DD",
  "outcome": "CRL",
  "btd": false,
  "orphan": false,
  "priority_review": true,
  "fast_track": false,
  "modality": "Small Molecule",
  "prior_crl": false,
  "crl_reason_if_known": "CMC issues",
  "sources": [
    {"type": "FDA", "url": "https://...", "accessed": "2026-02-04"},
    {"type": "Press Release", "url": "https://...", "accessed": "2026-02-04"}
  ],
  "confidence": "HIGH",
  "notes": "Any relevant context"
}
```

### VERIFICATION REQUIREMENTS:
- Approval dates: Must match FDA approval letter or FDA.gov database
- CRL dates: Must match company press release or 8-K filing date
- Designations: Verify from FDA orphan drug database, BTD list, or approval letters
- If conflicting sources, note the discrepancy and list all sources

### DO NOT:
- Guess or estimate dates
- Assume designations without verification
- Include drugs still awaiting decision (only DECIDED outcomes)
- Confuse PDUFA target dates with actual decision dates

### DELIVERABLE:
Complete JSON array of ALL 2026 PDUFA decisions you can verify, with sources for each field. Include approvals AND CRLs from January 1, 2026 through February 4, 2026.

---

# 🟢 PROMPT 2: GEMINI (SEC Filing & Regulatory Document Specialist)

Copy everything below to Gemini:

---

## ODIN PDUFA 2026 SEC/Regulatory Audit - Gemini

You are the SEC Filing & Regulatory Document Specialist for the ODIN biotech catalyst prediction system. Your role is to extract precise regulatory data from official filings.

### YOUR SPECIFIC DUTIES:
1. Search SEC EDGAR for 8-K filings announcing PDUFA outcomes in 2026
2. Extract exact decision dates from regulatory filings
3. Identify CRL reasons from company disclosures
4. Verify sponsor experience (prior FDA approvals)
5. Find any AdCom meeting results related to 2026 decisions

### PRIORITY TARGETS:
1. **AQST (Aquestive Therapeutics)** - Find 8-K for Anaphylax CRL
   - Need: Exact CRL date, CRL reason, any resubmission timeline
   
2. **PHAR (Pharming Group)** - Find 8-K or 6-K for recent CRL
   - Note: Foreign company, may file 6-K instead of 8-K
   - Need: Product name, exact date, CRL reason
   
3. **ATRA (Atara Biotherapeutics)** - Verify EBVALLO CRL details
   - Need: Confirm Jan 12 date, CRL reason

4. **Cross-verify** FBIO and EBS approval dates against SEC filings

### SEC EDGAR SEARCH STRATEGY:
- Search: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
- Form types: 8-K, 6-K (foreign issuers), 10-K, 10-Q
- Keywords in filings: "Complete Response Letter", "CRL", "FDA approval", "PDUFA"
- Date range: January 1, 2026 to present

### OUTPUT FORMAT (JSON for each finding):
```json
{
  "ticker": "AQST",
  "sec_filing_type": "8-K",
  "filing_date": "YYYY-MM-DD",
  "sec_url": "https://www.sec.gov/Archives/edgar/...",
  "event_type": "CRL",
  "decision_date": "YYYY-MM-DD",
  "product_name": "Anaphylax",
  "crl_reason_verbatim": "Quote from filing if CRL",
  "management_commentary": "Any relevant quotes about path forward",
  "resubmission_plans": "Timeline if mentioned",
  "extracted_data": {
    "prior_approvals_mentioned": 2,
    "adcom_referenced": false,
    "manufacturing_issues_mentioned": true
  },
  "confidence": "HIGH",
  "extraction_notes": "Any ambiguities or caveats"
}
```

### ALSO SEARCH FOR:
- FDA Advisory Committee (AdCom) transcripts for any 2026 meetings
- FDA Warning Letters or Form 483s issued in late 2025/early 2026 to these companies
- Any FDA Refuse to File letters in 2026

### VERIFICATION STANDARD:
- All dates must come from official SEC filings or FDA documents
- Quote exact language when describing CRL reasons
- Note if information is from management discussion vs. formal disclosure

### DO NOT:
- Use press releases as primary source (Perplexity handles those)
- Infer CRL reasons - only use explicitly stated reasons
- Include speculative resubmission timelines unless officially stated

### DELIVERABLE:
Complete JSON array of SEC-sourced regulatory events with document links and verbatim extracts for all 2026 PDUFA decisions you can find.

---

# 🔵 PROMPT 3: CHATGPT (Code Implementation & Data Integration Specialist)

Copy everything below to ChatGPT:

---

## ODIN PDUFA 2026 Data Integration Task - ChatGPT

You are the Code Implementation & Data Integration Specialist for the ODIN biotech catalyst prediction system. Your role is to write Python code that integrates research findings into the master dataset.

### YOUR SPECIFIC DUTIES:
1. Parse JSON outputs from Perplexity and Gemini
2. Validate data against schema requirements
3. Generate properly formatted CSV rows
4. Implement T-1 compliance checks
5. Create audit trail documentation

### CURRENT DATASET SCHEMA (33 columns):
```python
schema = {
    "event_id": "str",           # Format: "TICKER|ASSET|PDUFA|YYYY-MM-DD"
    "ticker": "str",
    "company": "str",
    "asset": "str",
    "indication": "str",
    "therapeutic_area": "str",   # Oncology, CNS, Cardiovascular, Allergy/Immunology, etc.
    "catalyst_date": "str",      # YYYY-MM-DD (FDA decision date)
    "catalyst_type": "str",      # Always "PDUFA" for this dataset
    "data_cutoff_date": "str",   # YYYY-MM-DD (MUST BE catalyst_date - 1 day)
    "outcome": "str",            # "APPROVAL" or "CRL"
    "btd": "bool",
    "orphan": "bool",
    "priority_review": "bool",
    "fast_track": "bool",
    "accelerated_approval": "str",
    "designation_stack_count": "int",  # Count of btd+orphan+priority+fast_track
    "had_adcom": "bool",
    "adcom_vote_pct": "float",   # NaN if no AdCom
    "adcom_date": "str",         # NaN if no AdCom
    "prior_crl": "bool",
    "prior_crl_reason": "str",   # Only populated if prior_crl=True
    "resubmission_class": "float",  # 1 or 2 if resubmission, NaN if first cycle
    "first_cycle": "bool",
    "form_483_issues": "bool",   # Default False (hard to verify T-1)
    "manufacturing_risk": "bool", # ALWAYS FALSE (compromised feature - never set True)
    "sponsor_prior_approvals": "float",
    "experienced_sponsor": "str", # "True" if sponsor_prior_approvals >= 3
    "modality": "str",           # Small Molecule, Antibody, Cell/Gene Therapy, RNA Therapy, ADC, Peptide, Vaccine
    "year": "int",
    "enrichment_source": "str",  # Use "MULTI_AI_2026_ENRICHMENT_v1"
    "enrichment_confidence": "str",  # HIGH, MEDIUM, LOW
    "crl_notes": "str",          # CRL reason - ONLY for CRL outcomes
    "modality_complexity": "str" # HIGH (RNA/Cell-Gene/ADC), MEDIUM (Antibody/Vaccine), LOW (Small Molecule/Peptide)
}
```

### PYTHON CODE REQUIREMENTS:

```python
import pandas as pd
from datetime import datetime, timedelta
import json

def validate_t1_compliance(row):
    """Ensure data_cutoff_date is exactly 1 day before catalyst_date"""
    catalyst = pd.to_datetime(row['catalyst_date'])
    cutoff = pd.to_datetime(row['data_cutoff_date'])
    return (catalyst - cutoff).days == 1

def calculate_modality_complexity(modality):
    """Assign complexity based on manufacturing difficulty"""
    high = ['RNA Therapy', 'Cell/Gene Therapy', 'ADC']
    medium = ['Antibody', 'Vaccine']
    if modality in high: return 'HIGH'
    if modality in medium: return 'MEDIUM'
    return 'LOW'

def generate_event_id(row):
    """Create unique event identifier"""
    asset_short = row['asset'][:30] if len(row['asset']) > 30 else row['asset']
    return f"{row['ticker']}|{asset_short}|PDUFA|{row['catalyst_date']}"

def calculate_designation_stack(row):
    """Count regulatory designations"""
    return sum([
        row.get('btd', False) == True,
        row.get('orphan', False) == True,
        row.get('priority_review', False) == True,
        row.get('fast_track', False) == True
    ])

def create_data_cutoff_date(catalyst_date):
    """Generate T-1 compliant cutoff date"""
    catalyst = pd.to_datetime(catalyst_date)
    cutoff = catalyst - timedelta(days=1)
    return cutoff.strftime('%Y-%m-%d')

def merge_ai_findings(perplexity_json, gemini_json):
    """
    Merge research from both AIs into validated records.
    
    PRIORITY RULES:
    - Dates: Gemini SEC data > Perplexity (SEC filings are authoritative)
    - CRL Reasons: Gemini verbatim quotes > Perplexity summaries
    - Designations: Cross-validate, flag if disagreement
    - General info: Perplexity for discovery, Gemini for verification
    """
    # Implementation here
    pass

def check_for_duplicates(new_records, existing_csv_path):
    """
    Check against existing dataset for duplicates.
    Match on: ticker + catalyst_date (primary key effectively)
    """
    existing = pd.read_csv(existing_csv_path)
    existing_keys = set(zip(existing['ticker'], existing['catalyst_date']))
    
    duplicates = []
    new_unique = []
    for record in new_records:
        key = (record['ticker'], record['catalyst_date'])
        if key in existing_keys:
            duplicates.append(record)
        else:
            new_unique.append(record)
    
    return new_unique, duplicates

def generate_audit_trail(record, perplexity_sources, gemini_sources):
    """Create audit documentation for each record"""
    return {
        "event_id": record['event_id'],
        "added_timestamp": datetime.now().isoformat(),
        "perplexity_sources": perplexity_sources,
        "gemini_sources": gemini_sources,
        "validation_checks": {
            "t1_compliant": validate_t1_compliance(record),
            "manufacturing_risk_false": record['manufacturing_risk'] == False,
            "crl_notes_valid": (record['outcome'] == 'CRL') == bool(record.get('crl_notes')),
            "designation_stack_correct": record['designation_stack_count'] == calculate_designation_stack(record)
        },
        "confidence": record['enrichment_confidence']
    }
```

### VALIDATION RULES (MUST IMPLEMENT):
1. `catalyst_date` must be <= 2026-02-04 (no future dates)
2. `data_cutoff_date` = `catalyst_date` - 1 day (ALWAYS)
3. `designation_stack_count` = sum of [btd, orphan, priority_review, fast_track]
4. `manufacturing_risk` = False (ALWAYS - feature is neutralized)
5. `crl_notes` only populated if outcome = "CRL"
6. `prior_crl_reason` only populated if prior_crl = True
7. Check for existing records before adding (avoid duplicates)
8. `year` must match year from `catalyst_date`

### DELIVERABLES:
1. Python script that processes Perplexity + Gemini JSON outputs
2. Validated new records in CSV format matching existing schema exactly
3. Audit trail JSON for each new record
4. Summary report of additions and any flagged issues

### DO NOT:
- Modify existing records (append only)
- Set manufacturing_risk to True (compromised feature)
- Add records without source documentation
- Assume missing fields - flag them for Claude's review

---

# 🟡 PROMPT 4: CLAUDE (Lead Researcher & Final Auditor)

Use this for the aggregation phase after receiving outputs from Perplexity and Gemini:

---

## ODIN PDUFA 2026 Final Audit & Aggregation Task - Claude

You are the Lead Researcher and Final Auditor for the ODIN biotech catalyst prediction system. 

### INPUTS YOU WILL RECEIVE:
1. **Perplexity JSON**: Web research findings with sources
2. **Gemini JSON**: SEC filing extracts with document links

### YOUR AUDIT CHECKLIST FOR EACH RECORD:

#### Source Verification:
- [ ] At least 2 independent sources confirm the outcome
- [ ] Decision date confirmed by official source (FDA.gov or SEC filing)
- [ ] Regulatory designations verified from FDA databases
- [ ] Company/ticker mapping is correct

#### T-1 Compliance Check:
- [ ] All designation data (BTD, Orphan, etc.) was public BEFORE decision date
- [ ] No post-decision information in pre-decision fields
- [ ] data_cutoff_date is exactly catalyst_date - 1 day
- [ ] manufacturing_risk is FALSE
- [ ] crl_notes only populated for CRL outcomes

#### Data Quality:
- [ ] No duplicate events (check existing 1,933 records)
- [ ] Therapeutic area classification is consistent with dataset conventions
- [ ] Modality classification is accurate
- [ ] prior_crl status matches historical records in dataset

### DISCREPANCY RESOLUTION HIERARCHY:
1. **SEC Filing** (highest authority for dates and outcomes)
2. **FDA.gov Database** (highest for designations and approval info)
3. **Company Press Release** (good for context, verify against above)
4. **News Sources** (lowest - use only for discovery, not confirmation)

### CROSS-REFERENCE EXISTING DATA:
```
AQST existing records:
- 2024-04-29: Libervant (diazepam) - pediatric - APPROVAL
- 2022-08-31: Libervant (diazepam) - APPROVAL  
- 2020-09-25: Libervant (diazepam) - CRL
- 2020-05-21: APL-130277 - APPROVAL

PHAR existing records:
- 2023-03-24: Leniolisib - APPROVAL

FBIO existing records (most recent):
- 2026-01-13: ZYCUBO (copper histidinate) - APPROVAL [already in dataset]
- 2025-10-01: ZYCUBO - CRL [prior CRL for same drug]
```

### OUTPUT FORMAT FOR VALIDATED RECORDS:
```json
{
  "validation_status": "APPROVED" | "NEEDS_HUMAN_REVIEW" | "REJECTED",
  "event_id": "TICKER|ASSET|PDUFA|YYYY-MM-DD",
  "record": {
    // Complete 33-field record ready for CSV
  },
  "validation_results": {
    "sources_checked": 3,
    "sources_agree": true,
    "t1_compliant": true,
    "duplicate_check": "PASS",
    "discrepancies": []
  },
  "audit_notes": "Summary of validation decisions"
}
```

### DISCREPANCY DOCUMENTATION:
If Perplexity and Gemini disagree:
```json
{
  "field": "catalyst_date",
  "perplexity_value": "2026-01-15",
  "gemini_value": "2026-01-16", 
  "resolution": "Used SEC 8-K filing date",
  "authority": "SEC filing URL",
  "confidence": "HIGH"
}
```

### FINAL OUTPUT:
1. Validated records ready for ChatGPT to integrate
2. Discrepancy resolution log
3. Any records requiring human review
4. Summary statistics

---

# 📊 EXECUTION WORKFLOW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ODIN 2026 ENRICHMENT WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 1: PARALLEL RESEARCH (Run simultaneously)                    │
│  ┌──────────────┐  ┌──────────────┐                                 │
│  │  PERPLEXITY  │  │    GEMINI    │                                 │
│  │  Web Search  │  │  SEC Filings │                                 │
│  │  Press/News  │  │  FDA Docs    │                                 │
│  └──────┬───────┘  └──────┬───────┘                                 │
│         │                  │                                         │
│         ▼                  ▼                                         │
│  [perplexity_output.json]  [gemini_output.json]                     │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 2: AGGREGATION & VALIDATION                                  │
│         ┌──────────────────┐                                        │
│         │      CLAUDE      │                                        │
│         │  Cross-Validate  │                                        │
│         │  Resolve Conflicts│                                       │
│         │  T-1 Compliance  │                                        │
│         └────────┬─────────┘                                        │
│                  │                                                   │
│                  ▼                                                   │
│         [validated_records.json]                                    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 3: CODE IMPLEMENTATION                                       │
│         ┌──────────────────┐                                        │
│         │     CHATGPT      │                                        │
│         │  Python Scripts  │                                        │
│         │  Schema Matching │                                        │
│         │  CSV Generation  │                                        │
│         └────────┬─────────┘                                        │
│                  │                                                   │
│                  ▼                                                   │
│         [new_records.csv] + [audit_trail.json]                      │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 4: FINAL REVIEW & MERGE                                      │
│         ┌──────────────────┐                                        │
│         │      CLAUDE      │                                        │
│         │  Final QC Check  │                                        │
│         │  Merge to Master │                                        │
│         └────────┬─────────┘                                        │
│                  │                                                   │
│                  ▼                                                   │
│    [ODIN_ENRICHED_PDUFA_FINAL.csv]                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

# ✅ COMPLETION CHECKLIST

Before finalizing the enriched dataset:

- [ ] All 2026 PDUFA decisions through Feb 4, 2026 are captured
- [ ] AQST CRL: Date confirmed, reason documented, sources linked
- [ ] PHAR CRL: Product identified, date confirmed, reason documented
- [ ] Existing records (EBS, FBIO, ATRA) verified accurate
- [ ] No duplicates with existing 1,933 records
- [ ] All records have minimum 2 source verification
- [ ] 100% T-1 compliance verified
- [ ] manufacturing_risk = FALSE for all new records
- [ ] crl_notes properly populated (only for CRLs)
- [ ] Audit trail complete and machine-readable
- [ ] Final dataset passes schema validation

---

*Protocol Version: 1.0 | Generated: 2026-02-04 | ODIN Multi-AI Collaboration System*
