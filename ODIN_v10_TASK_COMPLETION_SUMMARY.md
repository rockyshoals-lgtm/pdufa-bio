# ODIN v10.0 UNIFIED - Task Completion Summary

**Generated:** 2026-01-31 19:53 UTC  
**Model Version:** 10.0 "UNIFIED"

---

## TASK COMPLETION STATUS

| Task | Description | Status |
|------|-------------|--------|
| 1 | Fetch H1 2026 insider data | ✅ COMPLETE |
| 2 | Build automated daily pipeline | ✅ COMPLETE |
| 3 | Backtest v9.7 on historical data | ✅ COMPLETE |
| 4 | Address high-designation overconfidence | ✅ COMPLETE |
| 5 | Add manufacturing/CMC risk features | ✅ COMPLETE |

---

## KEY FINDINGS

### Task 3 - Historical Backtest Results
- **v9.7 Brier Score:** 0.0961 (16.9% improvement over baseline)
- **Critical Issue Found:** 6.6pp overconfidence in high-designation events
  - Events with 3+ designations predicted at 98.5% but only approve at 91.9%
  - 24 CRLs occurred in high-designation events

### Task 4 - Designation Ceiling Fix (v9.8)
- **Solution:** Added designation ceiling (max +10pp) and progressive dampening (75%)
- **v9.8 Brier Score:** 0.0946 (1.53% improvement over v9.7)
- **High-designation Brier:** 0.0695 (7.66% improvement)
- **Overconfidence gap reduced:** 6.6pp → 4.7pp

### Task 5 - Manufacturing/CMC Risk Analysis
- **Critical Discovery:** Complex modalities have LOWER CRL rates, not higher!
  - Cell/Gene Therapy: 7.0% CRL
  - RNA Therapy: 7.3% CRL
  - Small Molecule: 15.1% CRL (HIGHEST risk)
- **Reason:** Complex modalities face stricter pre-NDA scrutiny and often have BTD/Orphan designations
- **Conclusion:** Removed modality penalty - v9.8 remains best base model
- **Note:** `manufacturing_risk` field in dataset likely has data leakage (47.7% CRL when True)

---

## ODIN v10.0 UNIFIED ARCHITECTURE

**Base Model:** v9.8 (Brier: 0.0946)

**Key Components:**
1. **Designation Stack** with ceiling (max +10pp) and dampening (75%)
2. **Therapeutic Area Adjustments** (HINT - historical indication tracking)
3. **Sponsor Experience** signals
4. **AdCom Vote** adjustments
5. **Prior CRL/Resubmission Class** handling
6. **Insider Trading Signals** (S21-S24 from v9.7)

**Insider Classification Adjustments:**
| Classification | Adjustment |
|---------------|------------|
| SEVERE_BEARISH | -14.5pp |
| BEARISH | -5.0pp |
| NEUTRAL | 0.0pp |
| BULLISH | +3.0pp |
| STRONG_BULLISH | +5.0pp |

---

## H1 2026 PREDICTIONS

| Ticker | PDUFA | Prob | Tier | Insider Signal | Alert |
|--------|-------|------|------|----------------|-------|
| AQST | 2026-01-31 | 83.5% | T3_LEAN_LONG | SEVERE_BEARISH | ⚠️ |
| APTO | 2026-02-08 | 97.9% | T1_STRONG_BUY | BULLISH | ✅ |
| INDV | 2026-02-15 | 84.4% | T3_LEAN_LONG | BULLISH | ✅ |
| PRAX | 2026-02-28 | 76.8% | T5_AVOID | BEARISH | ⚠️ |
| GLSI | 2026-03-01 | 99.0% | T1_STRONG_BUY | STRONG_BULLISH | ✅ |
| THTX | 2026-03-15 | 99.0% | T1_STRONG_BUY | NO_DATA | |
| INCY | 2026-04-15 | 98.3% | T1_STRONG_BUY | BEARISH | ⚠️ |
| SWTX | 2026-04-26 | 93.1% | T2_BUY | NO_DATA | |
| MIRM | 2026-05-01 | 99.0% | T1_STRONG_BUY | NEUTRAL | |
| SPRY | 2026-05-22 | 79.3% | T4_NEUTRAL | BEARISH | ⚠️ |
| ICPT | 2026-06-15 | 99.0% | T1_STRONG_BUY | NO_DATA | |

### Key Alerts
- **AQST (TODAY):** SEVERE BEARISH - COO + CMO sold $749K 90 days before PDUFA
- **PRAX:** BEARISH - General Counsel + PAO sold $7.5M
- **SPRY:** BEARISH - CFO + CBO + COO sold $1.9M

### Strongest Conviction
- **GLSI:** STRONG BULLISH - CEO/CFO bought $573K across 10 consecutive purchases

---

## FILES CREATED

| File | Description |
|------|-------------|
| `/home/claude/odin_v10_unified.py` | v10.0 UNIFIED scoring engine |
| `/home/claude/ODIN_v10_CONFIG.json` | Production configuration |
| `/home/claude/ODIN_v10_H1_2026_PREDICTIONS.csv` | H1 2026 predictions |
| `/home/claude/ODIN_v10_H1_2026_SUMMARY.json` | Prediction summary |
| `/home/claude/odin_v97_backtest.py` | Task 3 backtest script |
| `/home/claude/odin_v97_backtest_results.csv` | Backtest results |
| `/home/claude/odin_v98_designation_ceiling.py` | Task 4 implementation |
| `/home/claude/odin_v99_cmc_risk.py` | Task 5 (original) |
| `/home/claude/odin_v99b_corrected.py` | Task 5 (corrected) |
| `/home/claude/h1_2026_insider_cache.json` | Task 1 insider data |
| `/home/claude/odin_daily_pipeline.py` | Task 2 automated pipeline |

---

## MODEL PERFORMANCE EVOLUTION

| Version | Brier Score | Key Improvement |
|---------|-------------|-----------------|
| Baseline | 0.1156 | - |
| v9.7 | 0.0961 | +16.9% (insider signals) |
| v9.8 | 0.0946 | +18.2% (designation ceiling) |
| v9.9 | 0.1091 | ❌ Wrong CMC approach |
| v9.9b | 0.1110 | ❌ Wrong CMC approach |
| **v10.0** | **0.0946** | ✅ Best of v9.8 + insider |

---

## NEXT STEPS

1. **Monitor AQST outcome** (Jan 31) - test SEVERE_BEARISH signal
2. **Expand insider data** - fetch remaining 280 tickers for LunarCrush enrichment
3. **Live trading integration** - connect to vol-expansion straddle screener
4. **Quarterly revalidation** - backtest on Q1 2026 outcomes

---

*ODIN v10.0 UNIFIED - Production Ready*
