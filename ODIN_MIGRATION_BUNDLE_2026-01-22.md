# ODIN Migration Bundle - 2026-01-22
## Session Handoff Document

---

## 🎯 CURRENT STATE

### Active Process Running
**ODIN_API_ENRICHMENT_V4.py is currently running** on the full 1,349-row PDUFA dataset.
- Started: ~23:00 PST
- Rate: ~4.7s/row
- ETA: ~1.75 hours total
- Location: User's local machine (C:\Users\dcmoo\Documents\Python\)

### What Just Completed
1. ✅ Fixed all API endpoint issues (FMP stable migration, OpenFDA, ClinicalTrials v2)
2. ✅ Created ImportGenius BOL parser and search list
3. ✅ All 6 APIs tested and working

---

## 📁 FILES CREATED THIS SESSION

### In Claude Outputs (/mnt/user-data/outputs/)
| File | Purpose | Status |
|------|---------|--------|
| `ODIN_API_ENRICHMENT_V4.py` | Main enrichment script (fixed) | ✅ Delivered |
| `ODIN_IMPORTGENIUS_BOL_PARSER.py` | Parse ImportGenius CSV exports | ✅ Delivered |
| `ODIN_IMPORTGENIUS_SEARCH_LIST.csv` | 60 prioritized company searches | ✅ Delivered |
| `ODIN_IMPORTGENIUS_DAILY_WORKSHEET.md` | Day-by-day search guide | ✅ Delivered |

### On User's Machine (Expected Locations)
| File | Path |
|------|------|
| Main PDUFA dataset | `C:\Users\dcmoo\Documents\Python\ODIN_PDUFA_1349_GPU_READY.csv` |
| Enrichment output | `C:\Users\dcmoo\Documents\Python\ODIN_ENRICHED.csv` (being created) |
| V4 Script | `C:\Users\dcmoo\Documents\Python\ODIN_API_ENRICHMENT_V4.py` |

---

## 🔑 API CREDENTIALS (User has these configured)

```
FMP_API_KEY=kyI0t6mDZD1YBTfxtKZSgkp6eILZR3v6
FINBRAIN_API_KEY=5813fe19-a03c-4873-a7be-354315c39b80
LUNARCRUSH_API_KEY=wyy0sr5cpo91napnt6cz6rtynmkmurndcr9bbdtd
OPENFDA_API_KEY=j3eLDwnktH7CPacXZe0HrBaUdMbCBcudUt3iDXoc
```

---

## 🔧 CRITICAL FIXES APPLIED IN V4

### 1. Drug Name Cleaning
```python
def clean_name(name: str) -> str:
    cleaned = re.sub(r'\s*\([^)]*\)', '', name)  # Remove (generic)
    cleaned = re.sub(r'[^\w\s\-]', '', cleaned)   # Alphanumeric only
    return cleaned.strip()
```
Applied to ALL drug/company names before API calls.

### 2. T-1 Date Compliance
All date-based queries now use `cutoff_date` (from dataset) and look BACKWARD:
```python
end_date = min(cutoff_date, datetime.now())  # Never search future
start_date = end_date - timedelta(days=months * 30)
```

### 3. OpenFDA Field Fix
Changed from `generic_name` (fails) to `medicinalproduct` (works):
```python
params = {'search': f'patient.drug.medicinalproduct:"{clean_name}"', ...}
```

### 4. ClinicalTrials.gov API v2 Syntax
Changed from `filter.phase=PHASE3` (400 error) to:
```python
params = {'filter.advanced': f'AREA[Phase]{api_phase}', 'countTotal': 'true', ...}
```

### 5. FMP Stable Endpoints
Migrated from deprecated `/api/v3/` to `/stable/`:
- `/stable/cash-flow-statement`
- `/stable/key-metrics`

---

## 📊 SIGNALS BEING ENRICHED (V4)

| Source | Signal | Description |
|--------|--------|-------------|
| FMP | `fmp_cash_runway_years` | Years of cash at current burn |
| FMP | `fmp_rd_intensity` | R&D spend / Revenue |
| FMP | `fmp_debt_to_equity` | Leverage ratio |
| FinBrain | `finbrain_sentiment` | AI sentiment score |
| FinBrain | `finbrain_insider_activity` | Insider trading signals |
| FinBrain | `finbrain_analyst_consensus` | Analyst ratings |
| OpenFDA | `openfda_adverse_events_12m` | Adverse event count |
| OpenFDA | `openfda_warning_letters` | Warning letter flag |
| ClinicalTrials | `ct_phase1_count` | Phase 1 trial count |
| ClinicalTrials | `ct_phase2_count` | Phase 2 trial count |
| ClinicalTrials | `ct_phase3_count` | Phase 3 trial count |
| ClinicalTrials | `ct_sponsor_recruiting` | Sponsor's active trials |
| PubMed | `pubmed_publications_12m` | Publication count |
| LunarCrush | `lc_galaxy_score` | Social sentiment |
| LunarCrush | `lc_alt_rank` | Alternative ranking |
| LunarCrush | `lc_social_dominance` | Social share of voice |

---

## 📋 IMPORTGENIUS INTEGRATION (NEW)

### User's Subscription
- Plan: Basic ($149/mo)
- Limit: 20 searches/day
- API: Not available (Enterprise only)

### Workflow
1. User manually searches companies in ImportGenius web UI
2. Exports results to CSV
3. Runs BOL parser: `python ODIN_IMPORTGENIUS_BOL_PARSER.py -i bol_exports/ -p pdufa.csv -o enriched.csv`

### Signals from BOL Data
| Signal | Description |
|--------|-------------|
| `bol_total_shipments` | Total pharma shipments |
| `bol_api_shipments` | API/drug substance imports |
| `bol_cmo_shipments` | Contract manufacturer activity |
| `bol_geographic_risk` | China/India exposure (0-1) |
| `bol_scale_up_ratio` | Recent vs historical volume |
| `bol_china_pct` | % shipments from China |
| `bol_india_pct` | % shipments from India |

### Priority Search List
60 companies with manufacturing risk flags, organized by PDUFA date.
Top priorities: ATRA, OTLK, CORT, OMER, AMRX, DSNKY (Dec 2025 - Jan 2026 PDUFAs)

---

## 🎯 NEXT STEPS (After Enrichment Completes)

1. **Validate enrichment output** - Check for missing values, API failures
2. **Run ImportGenius searches** - 20/day for top 60 companies
3. **Parse BOL data** - Extract supply chain signals
4. **Merge all signals** - Combine V4 enrichment + BOL data
5. **Re-run GPU optimization** - Test new features with 1B iteration sweep
6. **Compare to baseline** - Current champion: F1=0.943, Brier=0.0650

---

## 📜 TRANSCRIPT REFERENCES

| File | Contents |
|------|----------|
| `/mnt/transcripts/2026-01-22-07-09-34-odin-api-enrichment-debugging-v4.txt` | This session (API fixes, ImportGenius) |
| `/mnt/transcripts/2026-01-22-05-49-22-fmp-api-migration-enrichment-fix.txt` | Previous session (FMP migration) |

---

## 🧠 KEY PROJECT CONTEXT

### ODIN Overview
- **Purpose**: Predict FDA PDUFA outcomes (Approval vs CRL)
- **Dataset**: 1,349 PDUFA events (2020-2026)
- **Baseline**: 86.7% approval rate
- **Champion Model**: 0.88008 score, 0.0650 Brier, 0.943 F1

### Critical Constraints
- **T-1 Compliance**: All features must use only pre-decision information
- **No Data Leakage**: Original `manufacturing_risk` had leakage (replaced with `modality_complexity`)
- **Manufacturing drives CRLs**: 74% of CRLs are CMC-related

### GPU Optimization
- Hardware: RTX 4070 (12GB VRAM, 5,888 CUDA cores)
- Framework: CuPy with fused CUDA kernels
- Throughput: 50.5M iterations/sec achieved

---

## ⚠️ KNOWN ISSUES

1. **FinBrain 404s**: Expected - no data for smaller biotech tickers
2. **Some tickers missing from FMP**: Small-cap biotechs may not have financials
3. **LunarCrush coverage**: Varies by ticker popularity

---

## 🚀 TO RESUME IN NEW CHAT

1. Upload this document
2. Ask: "Continue ODIN development from migration bundle"
3. Check if V4 enrichment completed
4. Review enriched dataset quality
5. Proceed with ImportGenius searches or GPU optimization

