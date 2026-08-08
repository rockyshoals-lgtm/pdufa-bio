# ODIN MIGRATION FILE — January 31, 2026 (v2)
**Transfer Point:** Post-v10 completion, pre-validation of Gemini/Perplexity audit  
**Role:** Claude as Lead Researcher in 4-AI system  
**Dataset:** v4.2 AUDITED (1,934 events) — USE THIS, NOT the 1,349 version

---

## ⚠️ CRITICAL: CORRECT DATASET

**USE:** `ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv` (1,934 events)  
**DO NOT USE:** `ODIN_ENRICHED_PDUFA_1349_v2.csv` (outdated)

| Metric | Value |
|--------|-------|
| Total Events | 1,934 |
| Approvals | 1,601 (82.78%) |
| CRLs | 333 (17.22%) |
| Year Range | 2002-2026 |
| Outcome Labels | `APPROVAL` / `CRL` |

---

## ⚠️ CRITICAL: API KEY REFERENCE

**IMMUTABLE DOCUMENTATION:** `ODIN_API_KEYS_REFERENCE.md`

All API keys stored as environment variables:
```
FMP_API_KEY          — Form 4, 13F, stock data (300 calls/min)
FINBRAIN_API_KEY     — Sentiment, predictions
LUNARCRUSH_API_KEY   — Social metrics
OPENFDA_API_KEY      — Drug approvals, labels
PATENTSVIEW_API_KEY  — Patent data
FDA_OIIWEB_API_KEY   — FDA facility data
CENSUS_API_KEY       — Economic data
OPENAI_API_KEY       — GPT models
GEMINI_API_KEY       — Gemini models
```

**ChatGPT MUST:** Read keys via `os.environ.get('KEY_NAME')`, never hardcode.

---

## CURRENT STATE SUMMARY

### Model Evolution (Complete)
| Version | Brier Score | Key Feature | Status |
|---------|-------------|-------------|--------|
| Baseline | 0.1156 | - | Reference |
| v9.7 | 0.0961 | Insider signals (S21-S24) | ✅ Complete |
| v9.8 | 0.0946 | Designation ceiling + dampening | ✅ BEST BASE |
| v9.9/v9.9b | 0.109/0.111 | CMC risk (FAILED) | ❌ Rejected |
| **v10.0 UNIFIED** | 0.0946 | v9.8 base + v9.7 insider signals | ✅ PRODUCTION |

### Critical Discoveries Made
1. **Designation ceiling critical** — High-designation events (3+) were overconfident by 6.6pp; fixed with 10pp cap + progressive dampening
2. **Complex modalities are SAFER** — Cell/Gene (7% CRL) vs Small Molecule (15% CRL) — opposite of initial hypothesis
3. **manufacturing_risk field has data leakage** — 11.6x lift is impossible, excluded from model
4. **Insider signals work** — AQST downgraded 10pp due to SEVERE_BEARISH (C-suite selling)

### H1 2026 Active Predictions
```
Ticker  PDUFA       Prob   Tier              Insider          Alert
AQST    2026-01-31  83.5%  T3_LEAN_LONG     SEVERE_BEARISH   ⚠️ (TODAY)
APTO    2026-02-08  97.9%  T1_STRONG_BUY    BULLISH          ✅
INDV    2026-02-15  84.4%  T3_LEAN_LONG     BULLISH          ✅
PRAX    2026-02-28  76.8%  T5_AVOID         BEARISH          ⚠️
GLSI    2026-03-01  99.0%  T1_STRONG_BUY    STRONG_BULLISH   ✅
THTX    2026-03-15  99.0%  T1_STRONG_BUY    NO_DATA          
INCY    2026-04-15  98.3%  T1_STRONG_BUY    BEARISH          ⚠️
SWTX    2026-04-26  93.1%  T2_BUY           NO_DATA          
MIRM    2026-05-01  99.0%  T1_STRONG_BUY    NEUTRAL          
SPRY    2026-05-22  79.3%  T4_NEUTRAL       BEARISH          ⚠️
ICPT    2026-06-15  99.0%  T1_STRONG_BUY    NO_DATA          
```

---

## 4-AI SYSTEM ROLES

| AI | Role | Responsibility |
|----|------|----------------|
| **Claude** | Lead Researcher | Validation, backtesting, research authority, final approval |
| **Gemini** | Data Acquisition | 13F filings, historical data pulls, bulk research |
| **Perplexity** | Real-time Intelligence | News, current events, web search, literature review |
| **ChatGPT** | Implementation | Python code, module building, automation scripts |

### Rules of Engagement
1. **ChatGPT ONLY implements what Claude approves** — no freelancing
2. **Gemini provides data, does not interpret** — Claude validates
3. **Perplexity provides intelligence, does not recommend weights** — Claude decides
4. **All API code must reference `ODIN_API_KEYS_REFERENCE.md`**

---

## PENDING VALIDATION TASKS

### Task 1: Specialist Fund Backtest (HIGH PRIORITY)
**Question:** Do specialist fund positions actually predict FDA approvals?

**Methodology:**
```python
# USE 1,934 EVENT DATASET
for each PDUFA in ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv:
    check 13F filings T-90 days before catalyst_date
    flag if Perceptive/RTW/RA Capital/Baker Bros held position
    compare approval rates: specialist_cohort vs. baseline (82.78%)
```

**Expected output:** Empirical weights based on actual predictive power

### Task 2: Google Trends Correlation (MEDIUM PRIORITY)
**Question:** Does search interest correlate with PDUFA outcomes?

### Task 3: Insider Classification Parser (READY FOR CHATGPT)
**Approved logic — ChatGPT implements this:**
```python
import os

# API KEY HANDLING (MANDATORY)
FMP_API_KEY = os.environ.get('FMP_API_KEY')
if not FMP_API_KEY:
    raise ValueError("FMP_API_KEY not set in environment")

def classify_insider_transaction(form4_data: dict) -> str:
    """
    Classify Form 4 as administrative vs. discretionary.
    Administrative transactions are IGNORED for sentiment scoring.
    """
    footnotes = form4_data.get('footnotes', '').lower()
    
    # Administrative (IGNORE)
    if any(x in footnotes for x in [
        '10b5-1', 
        'rule 10b5-1',
        'tax withholding',
        'rsu vesting',
        'option exercise'
    ]):
        return 'ADMINISTRATIVE'
    
    # Discretionary - check materiality
    pct_of_holdings = form4_data['shares_traded'] / form4_data['total_holdings']
    
    if form4_data['transaction_type'] == 'SELL':
        if pct_of_holdings > 0.20:
            return 'SEVERE_DISCRETIONARY_SELL'  # -14.5pp
        elif pct_of_holdings > 0.05:
            return 'DISCRETIONARY_SELL'  # -5pp
        else:
            return 'MINOR_SELL'  # ignore
    
    return 'BUY'
```

---

## GEMINI/PERPLEXITY AUDIT STATUS

| Module | Claude Verdict | Status |
|--------|----------------|--------|
| 1. Insider 10b5-1 classification | ✅ APPROVED | Ready for ChatGPT |
| 2. Specialist fund weights | ⚠️ NEEDS BACKTEST | Weights arbitrary |
| 3. Google Trends signals | ⚠️ NEEDS VALIDATION | Unproven |
| 4. Revenue forecasting | ❌ DEFERRED | Out of scope |
| 5. Catalyst calendar expansion | ✅ APPROVED | Add IRON, RNA, KOD |
| 6. S2S ratio (retail trap) | ⚠️ NEEDS VALIDATION | Novel concept |

---

## KEY FILES

### MASTER DATASET (USE THIS)
```
/home/claude/ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv
- 1,934 events (2002-2026)
- Outcomes: APPROVAL / CRL
- Baseline: 82.78% approval, 17.22% CRL
```

### API REFERENCE (IMMUTABLE)
```
/home/claude/ODIN_API_KEYS_REFERENCE.md
- All API endpoints
- Rate limits
- Code patterns
- ChatGPT MUST reference this
```

### Model Files
```
/home/claude/odin_v10_unified.py          — Production scoring engine
/home/claude/ODIN_v10_CONFIG.json         — Configuration
/home/claude/ODIN_v10_H1_2026_PREDICTIONS.csv — H1 predictions
/home/claude/h1_2026_insider_cache.json   — Insider data cache
```

---

## ODIN v10 CHAMPION CONFIGURATION

```json
{
  "version": "10.0",
  "base_model": "v9.8",
  "brier_score": 0.0946,
  "dataset": "ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv",
  "dataset_size": 1934,
  "baseline_approval_rate": 0.8278,
  "components": {
    "designation_ceiling": {
      "max_total_boost": 0.10,
      "dampening_factor": 0.75
    },
    "insider_signals": {
      "SEVERE_BEARISH": -0.145,
      "BEARISH": -0.05,
      "NEUTRAL": 0.0,
      "BULLISH": 0.03,
      "STRONG_BULLISH": 0.05
    },
    "excluded": ["manufacturing_risk", "modality_adjustments"]
  },
  "tier_thresholds": {
    "T1_STRONG_BUY": 0.92,
    "T2_BUY": 0.85,
    "T3_LEAN_LONG": 0.78,
    "T4_NEUTRAL": 0.65,
    "T5_AVOID": 0.50,
    "T6_STRONG_SHORT": 0.0
  }
}
```

---

## IMMEDIATE NEXT STEPS

| AI | Task | Deliverable |
|----|------|-------------|
| **Claude** | Backtest specialist funds on 1,934 events | Empirical weights |
| **Gemini** | Pull 13F data for 4 funds (2020-2025) | Structured position data |
| **Perplexity** | GT literature + AQST status today | Research summary |
| **ChatGPT** | Implement insider classifier | Python module |

---

## TRANSCRIPT REFERENCE
Full conversation history: `/mnt/transcripts/2026-01-31-22-11-29-odin-v10-five-tasks-completion.txt`

---

**Migration Created:** 2026-01-31 23:00 PST  
**Dataset:** v4.2 AUDITED (1,934 events)  
**Next Chat:** Continue with specialist fund backtest on correct dataset
