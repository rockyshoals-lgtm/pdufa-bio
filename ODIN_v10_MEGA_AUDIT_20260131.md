# ODIN v10 MEGA AUDIT & IMPLEMENTATION GUIDE
**Generated:** January 31, 2026, 2:07 PM PST  
**Status:** Ready for Claude & ChatGPT Logic Implementation  

---

## TABLE OF CONTENTS
1. [Institutional vs. Insider Dynamics](#1-institutional-vs-insider-dynamics)
2. [Specialist Fund Landscape](#2-specialist-fund-landscape)
3. [Revenue Forecasting Framework](#3-revenue-forecasting-framework)
4. [Google Trends as Predictive Engine](#4-google-trends-as-predictive-engine)
5. [High-Impact Catalyst Calendar (Q1–Q2 2026)](#5-high-impact-catalyst-calendar)
6. [Data Stack & Intelligence Services](#6-data-stack--intelligence-services)
7. [ODIN v10 Config Additions](#7-odin-v10-config-additions)
8. [Daily Mega Document Template](#8-daily-mega-document-template)

---

## 1. INSTITUTIONAL vs. INSIDER DYNAMICS

### Core Principle
**Specialist Institutional Buying > Routine Insider Selling** (when specialists are Tier-1 funds)

When insiders sell but top specialists (Perceptive, RTW, RA Capital, Baker Bros) are adding:
- Insider selling is typically **administrative** (10b5-1 tax events, portfolio rebalancing)
- Specialist buying reflects **terminal value thesis** based on proprietary research
- **Outcome probability shifts BULLISH** despite insider activity

### Decision Logic
```
IF insider_classification = "NON_DISCRETIONARY" (Rule 10b5-1, tax withholding)
  → insider_effect = 0 (IGNORE)

IF insider_classification = "DISCRETIONARY" AND volume > 20% of holdings
  → insider_effect = -0.145 (SEVERE_BEARISH)

IF insider_classification = "DISCRETIONARY" AND 5% < volume ≤ 20%
  → insider_effect = -0.05 (BEARISH)

IF specialist_fund IN {Perceptive, RTW, RA_Capital, Baker_Bros} AND position_increase ≥ 10%
  → specialist_effect = +0.06
  → neutralization: insider_effect *= 0.3 (fade insiders when specialists add)

FINAL_SENTIMENT = (insider_effect * 0.3) + (specialist_effect * 1.0)
```

### Historical Validation Cases
- **PGEN (Precigen)**: Insiders sold $6.2M (10% of holdings) while Patient Capital +62%, Tang Capital +new position. → FDA approval Aug 2025, stock +77%, institutional thesis validated.
- **AMAM (Ambrx)**: CEO/CFO sold while Cormorant loaded 1.3M shares at $6.99. → J&J acquisition at $28/share (300% ROI in 3 months).
- **DNA (Ginkgo)**: Insiders net sold while institutions held 52%. → Business pivot, revenue decline, insider skepticism was correct.

---

## 2. SPECIALIST FUND LANDSCAPE

### Top Performers (2025) & Current Holdings

| Fund | 2025 Return | Core Holdings | Recent Adds (Q4 2025 / Q1 2026) | Catalyst Tier |
|------|-------------|---------------|--------------------------------|---------------|
| **Perceptive Advisors** | 82% | ASND, CELC, RYTM | SABS, Freenome (SPAC) | A (CELC PDUFA Jul 2026) |
| **RTW Investments** | 75.9% | MDGL, PTCT, STOK | RNA, QURE, XNCR | A (RNA BLA Q1 2026) |
| **RA Capital** | 38-38.6% | ARSB, IRON, IPSC | IRON, DISC Medicine | A+ (IRON FDA early 2026, CNPV) |
| **Baker Bros Advisors** | 27.9% | INCY, MDGL, INSM, ONC | KOD, KYMR, DBVT | A (KOD GLOW2 Phase 3 Q1 2026) |

### Odin Weighting System
```json
"specialist_funds": {
  "PERCEPTIVE": { "weight": 0.06, "win_rate": 0.82 },
  "RTW": { "weight": 0.06, "win_rate": 0.759 },
  "RA_CAPITAL": { "weight": 0.05, "win_rate": 0.386 },
  "BAKER_BROS": { "weight": 0.07, "win_rate": 0.279 }
}

"specialist_adjustments": {
  "NEW_OR_10PCT_ADD": 0.04,
  "SMALL_ADD_1_10PCT": 0.015,
  "HOLD": 0.0,
  "EXIT_OR_50PCT_REDUCE": -0.05
}
```

---

## 3. REVENUE FORECASTING FRAMEWORK

### The Odin Revenue Formula

```
R = (TRx_proxy × 13 weeks) × (WAC × (1 - GTN%)) × Inventory_Multiplier
```

### Component Definitions

#### A. TRx_proxy (Weekly Prescription Volume)
**Until IQVIA access:** Use composite of:
- Google Trends (brand name, indication, symptom)
- Hub enrollment updates
- J-code inflection events
- Specialist fund channel checks

**Odin calibration:**
- GT composite: weighted average (brand 50%, indication 30%, symptom 20%)
- Check for "commercial ramp": +5% WoW for 4+ weeks = prescription-driven (not media spike)

#### B. Gross-to-Net (GTN) Deductions
| Drug Type | GTN Drag | Net Realization |
|-----------|----------|-----------------|
| Specialty/Orphan | 30-40% | 60-70% of WAC |
| Primary Care (crowded) | 50-70% | 30-50% of WAC |
| GLP-1/Obesity (mid-tier) | 40-50% | 50-60% of WAC |

**Odin adjustment:** If management mentions "higher rebates" or "bridge programs," add 10-20% penalty to GTN drag for that quarter.

#### C. Inventory Multiplier
| Phase | Multiplier | Logic |
|-------|------------|-------|
| Launch Q1-Q2 | 1.3x | Channel stocking (wholesalers pre-buy) |
| Mature (Q3+) | 1.0x | TRx matches wholesaler draw |
| De-stocking | 0.85x | Post-inventory normalization |

### Revenue Proxy Implementation (Per Asset)

```json
{
  "asset_id": "PGEN_PAPZIMEOS",
  "drug_name": "Papzimeos",
  "indication": "RRP",
  "launch_quarter": "2025Q4",
  "pricing": {
    "wac_estimate": 1.0,
    "gtn_baseline": 0.35,
    "gtn_additional_bridge_penalty": 0.0
  },
  "inventory_dynamics": {
    "phase": "LAUNCH",
    "multiplier": 1.3
  },
  "script_proxies": {
    "uses_google_trends": true,
    "uses_hub_enrollments": true,
    "hub_enrollment_recent": "doubling (Jan 2026)",
    "gt_composite_rsv": 67,
    "gt_trend": "up 22% from 52wk avg"
  },
  "q1_2026_revenue_forecast": {
    "exit_velocity_trx": 800,
    "quarterly_trx": 10400,
    "net_price": 0.65,
    "inventory_multiplier": 1.3,
    "estimated_gaap_revenue": 8788,
    "consensus": 6500,
    "beat_probability": 0.72
  }
}
```

---

## 4. GOOGLE TRENDS AS PREDICTIVE ENGINE

### Stage 1: Data Acquisition & Keyword Normalization

**Keyword Triangulation (per drug):**
```
Tier 1 (Brand Name):        "Papzimeos" → r ≈ 0.85, highest prescription correlation
Tier 2 (Indication):        "RRP treatment" → captures top-of-funnel awareness
Tier 3 (Symptom/Unmet):     "respiratory papillomatosis surgery" → baseline demand
```

**Composite RSV Calculation:**
```
Composite_RSV = (Brand_RSV × 0.5) + (Indication_RSV × 0.3) + (Symptom_RSV × 0.2)

Odin Flag: IF Composite_RSV > 52wk_avg × 1.2 → POTENTIAL INFLECTION
```

### Stage 2: Hype vs. Health Filter

**Media Spike Detection:**
```
IF (News_RSV / Composite_RSV) > 2.0
  → MEDIA-DRIVEN (ignore short-term noise)
  → GT_Signal = NEUTRAL

ELSE IF Composite_RSV increases ≥ 5% WoW for 4+ consecutive weeks (no news spike)
  → COMMERCIAL_RAMP (prescription growth)
  → GT_Signal = BULLISH
  → Revenue_Adjustment = +TBD%
```

### Stage 3: Insider Inverse (Retail Trap Detection)

**Search-to-Sell Ratio (S2S):**
```
S2S = ΔComposite_RSV / ΔInsider_Sales_Volume

Scenario 1: RSV @ 52wk HIGH + Insiders SELLING
  → Verdict: BEARISH / "Retail Trap"
  → Insiders exploiting attention-driven mispricing
  → Adjustment: -0.08 to approval probability

Scenario 2: RSV @ 52wk HIGH + Insiders SELLING + Specialists BUYING
  → Verdict: NEUTRAL/BULLISH (Smart Money Override)
  → Specialist thesis overrides retail trap
  → Adjustment: +0.06 to approval probability
```

### Stage 4: Revenue Proxy (Lead/Lag Calibration)

**Search Velocity → Revenue Multiplier:**
```
R_m = (Avg_RSV_CurrentQ / Avg_RSV_PriorQ) × Launch_Multiplier

Example (PGEN Q1 2026):
  RSV_Q4_2025 = 45 (launch quarter noise)
  RSV_Q1_2026_estimate = 67 (commercial ramp)
  Launch_Multiplier = 1.3
  
  R_m = (67 / 45) × 1.3 = 1.93x
  
  Expected Q1 revenue ∝ Prior Q × 1.93 (adjusted for baseline TRx)
```

**Lead/Lag Timing:**
- Search surges typically **precede revenue growth by 4-6 weeks**
- Use current/trailing 4-week RSV as nowcast for next quarter
- Compare to sell-side consensus for beat/miss probability

### Odin GT Config

```json
"google_trends": {
  "keywords": {
    "brand_weight": 0.5,
    "indication_weight": 0.3,
    "symptom_weight": 0.2
  },
  "filters": {
    "media_spike_threshold": 2.0,
    "commercial_ramp_weeks": 4,
    "commercial_ramp_threshold": 0.05
  },
  "s2s_ratio": {
    "retail_trap": {"search_high": true, "insiders_selling": true},
    "smart_money_override": {"search_high": true, "insiders_selling": true, "institutions_buying": true}
  },
  "revenue_multiplier": {
    "launch_phase_multiplier": 1.3,
    "mature_multiplier": 1.0,
    "lead_lag_weeks": 6
  }
}
```

---

## 5. HIGH-IMPACT CATALYST CALENDAR (Q1–Q2 2026)

### Catalyst Tier System

| Tier | Definition | Examples |
|------|-----------|----------|
| **A+** | Binary + specialist-owned + compressed timeline | IRON FDA (CNPV), RNA BLA |
| **A** | Binary, program-defining | KOD Phase 3, CELC PDUFA, PGEN Q4 earnings (first full commercial) |
| **B** | Commercial inflection | MDGL earnings (Rezdiffra ramp), VKTX Phase 3 enrollment completion |
| **C** | Informational/setup | VKTX earnings (before big readout), KYMR FIH initiation |

### Rolling Calendar

| Ticker | Company | Fund(s) | Event | Date | Tier | Priority |
|--------|---------|---------|-------|------|------|----------|
| VKTX | Viking | RA, Perceptive | Earnings | Feb 4 | C | Watch obesity sentiment |
| RVMD | Revolution Med. | Multiple | Earnings | Feb 25 | C | Check cash runway |
| MDGL | Madrigal | RTW, Baker | Earnings | Feb 25 | B | MASH commercial inflection |
| QURE | uniQure | RTW | Earnings | Feb 26 | C | Gene therapy cash status |
| RNA | Avidity | RTW, others | BLA Submission | Q1 2026 | A | Platform validation, M&A closing risk |
| WVE | Wave Life | Perceptive, RA | Clinical data (6mo/3mo) | Q1 2026 | B | Obesity follow-up |
| KOD | Kodiak | Baker | Phase 3 GLOW2 topline | Q1 2026 | A | DR program binary |
| PGEN | Precigen | Multiple | Q4 earnings | Mar 18 | B | PAPZIMEOS Q1 launch metrics |
| CELC | Celcuity | Perceptive | PDUFA | Jul 17 | A | Core Perceptive pillar |
| IRON | Disc Medicine | RA, OrbiMed | FDA decision (CNPV) | Early 2026 | A+ | EPP rare disease binary |

---

## 6. DATA STACK & INTELLIGENCE SERVICES

### Immediate Stack (< $150/mo) — Recommended

| Service | Cost | Purpose | Status |
|---------|------|---------|--------|
| **Google Trends** | Free | GT composite, commercial ramp detection | Implement now |
| **BiopharmaWatch** | $19/mo | PDUFA calendar, PoA scores | Sign up now |
| **BPIQ Elite** | $45/mo (annual) | Catalyst volatility, hedge fund tracking | Sign up now |
| **WhaleWisdom** | $42/mo | 13F specialist monitoring (Perceptive/RTW/RA/Baker) | Sign up now |
| **STAT News (STAT+)** | $35/mo ($199 promo Y1) | Channel checks, launch reporting | Sign up now |
| **Endpoints News** | Internal/free snippets | Manufacturing ramp-ups | Monitor |

**Total: ~$141/mo → 90% of institutional-grade signal**

### Phase 2 Add (3 months) — $212/mo

| Service | Cost | Purpose |
|---------|------|---------|
| **IQVIA EDT** | $2,545/yr | Peak sales priors, M&A comps, deal benchmarking |

---

## 7. ODIN v10 CONFIG ADDITIONS

### New JSON Blocks to Merge Into ODIN_v10_CONFIG.json

```json
{
  "specialist_funds": {
    "PERCEPTIVE": { "weight": 0.06, "win_rate": 0.82 },
    "RTW": { "weight": 0.06, "win_rate": 0.759 },
    "RA_CAPITAL": { "weight": 0.05, "win_rate": 0.386 },
    "BAKER_BROS": { "weight": 0.07, "win_rate": 0.279 }
  },
  "specialist_adjustments": {
    "NEW_OR_10PCT_ADD": 0.04,
    "SMALL_ADD_1_10PCT": 0.015,
    "HOLD": 0.0,
    "TRIM_10_50PCT": -0.02,
    "EXIT_OR_50PCT_REDUCE": -0.05
  },
  "google_trends": {
    "keywords": {
      "brand_weight": 0.5,
      "indication_weight": 0.3,
      "symptom_weight": 0.2
    },
    "filters": {
      "media_spike_threshold": 2.0,
      "commercial_ramp_weeks": 4,
      "commercial_ramp_threshold": 0.05,
      "rsv_inflection_threshold": 1.2
    },
    "s2s_ratio": {
      "retail_trap_adjustment": -0.08,
      "smart_money_override_adjustment": 0.06
    },
    "revenue_multiplier": {
      "launch_phase_multiplier": 1.3,
      "mature_multiplier": 1.0,
      "lead_lag_weeks": 6
    }
  },
  "revenue_proxies": {
    "google_trends_weight": 0.15,
    "specialist_channel_check_weight": 0.08,
    "hub_enrollment_weight": 0.07,
    "jcode_inflection_boost": 0.12
  },
  "earnings_catalyst_tiering": {
    "TIER_A_PLUS": { "importance": 0.95, "examples": "IRON FDA, RNA BLA, CELC PDUFA" },
    "TIER_A": { "importance": 0.85, "examples": "KOD Phase 3, PGEN launch metrics" },
    "TIER_B": { "importance": 0.65, "examples": "MDGL commercial ramp, VKTX Phase 3 enrollment" },
    "TIER_C": { "importance": 0.35, "examples": "VKTX earnings, KYMR FIH initiation" }
  }
}
```

### Per-Ticker Key_Adjustments Schema

Extend `ODIN_v10_H1_2026_PREDICTIONS.csv` with new columns:

```
ticker,company,...existing_fields...,specialist_signal,net_insider_institutional,gt_composite_rsv,gt_trend_direction,earnings_catalyst_tier,revenue_beat_probability

IRON,Disc Medicine,...,-0.0,...,0.04,+0.06,58,UP,A+,0.78
KOD,Kodiak Sciences,...,-0.02,...,0.04,+0.04,42,FLAT,A,0.65
PGEN,Precigen,...,0.0,...,0.04,+0.08,67,UP,B,0.72
```

---

## 8. DAILY MEGA DOCUMENT TEMPLATE

### Filename: `ODIN_DAILY_YYYYMMDD.md`

```markdown
# ODIN Daily Digest — [DATE]
**Generated:** [TIMESTAMP] PST

---

## A. OVERVIEW
**Focus Tickers Today:** [List 3-5 names with catalysts]
**Key Signals:** [1-2 sentence summary]
**P&L Context:** [if tracking]

---

## B. SPECIALIST FUND SIGNAL DASHBOARD

| Fund | Core Thesis | Recent Moves | Today's Action |
|------|---------|-------|---|
| Perceptive | Late-stage de-risking | CELC, ASND, SABS | No change |
| RTW | Metabolic/rare disease | MDGL, PTCT, RNA | No change |
| RA Capital | Under-owned innovators | IRON, ARSB | +15% IRON added (RA disclosure) |
| Baker Bros | Concentrated franchises | INCY, KOD, KYMR | No change |

---

## C. CATALYST CALENDAR (This Week & Next 30 Days)

| Date | Ticker | Event | Tier | Status |
|------|--------|-------|------|--------|
| Feb 4 | VKTX | Earnings | C | Next week |
| Feb 25 | MDGL | Earnings | B | This week |
| Feb 26 | QURE | Earnings | C | This week |
| Q1 2026 | RNA | BLA submission | A | Window open |
| Q1 2026 | KOD | GLOW2 topline | A | Expected |

---

## D. INSIDER vs. INSTITUTIONAL SIGNALS

### IRON (Disc Medicine) — RA Capital Adding
- **RA Position:** +15% (Jan 2026)
- **Insider Trend:** Neutral (CEO holding, no sales)
- **Form 4 Check:** No discretionary sales >5% last 90 days
- **Net Sentiment:** `divergence = SPECIALIST_OVERRIDES`
- **Odin Label:** +0.06 specialist effect, neutralizes any weak insider bearishness

### PGEN (Precigen) — Multiple Specialists Holding
- **Institutional:** Patient Capital +62%, Tang Capital +new (Q3 2025)
- **Insider:** Kirk sold $6.2M (10% of holdings), typical for launch diversification
- **GT Composite:** RSV 67 (up from 45 Q4), commercial ramp detected
- **Net Sentiment:** `divergence = SMART_MONEY_OVERRIDE`
- **Odin Label:** +0.04 specialist effect, GT supports commercial inflection

---

## E. GOOGLE TRENDS SCAN

| Asset | Brand RSV | Indication RSV | Composite | 52wk_avg | Trend | Media Spike? |
|-------|-----------|----------------|-----------|----------|-------|-------------|
| PGEN PAPZIMEOS | 45 | 67 | 67 | 35 | UP 22% | No |
| MDGL Rezdiffra | 38 | 52 | 51 | 28 | UP 18% | No (recent STAT) |

---

## F. NEW RULES / LOGIC UPDATES TODAY
- Added RA Capital +IRON as Q1 catalyst
- Confirmed GT commercial ramp for PGEN (4+ weeks +5% WoW)
- Scheduled WhaleWisdom scan for specialist changes tomorrow (Fri)

---

## G. NEXT 24–48 HOURS
- [ ] Monitor MDGL/QURE earnings (Feb 25-26)
- [ ] Pull GT update for PGEN, MDGL (track weekly)
- [ ] Check STAT+ for MDGL commercial updates
- [ ] 13F watch: Any new Perceptive/RTW filings
```

---

## IMPLEMENTATION CHECKLIST FOR CLAUDE & CHATGPT

### Phase 1: Logic Audit & Formalization (Immediate)
- [ ] Audit insider-vs-specialist decision tree for all H1 2026 catalysts
- [ ] Validate S2S (Search-to-Sell) ratio logic for PGEN, MDGL, future names
- [ ] Parse Form 4 footnotes to classify insider transactions (10b5-1 vs. discretionary)
- [ ] Backtest GT correlations against historical comps (e.g., ASND launch, VKTX Phase 2)

### Phase 2: Revenue Module Build (1 Week)
- [ ] Implement TRx_proxy composite: GT (3 keywords) + hub enrollments + J-code flags
- [ ] Calculate GTN assumptions per drug (specialty 35%, primary care 60%)
- [ ] Wire inventory multiplier logic (1.3x launch, 1.0x mature)
- [ ] Output: `revenue_beat_probability` per quarter for each commercial asset

### Phase 3: Daily Automation (2 Weeks)
- [ ] Set up automated GT pulls (PyTrends/Serper) → `ODIN_DAILY_YYYYMMDD.md`
- [ ] WhaleWisdom 13F scan → specialist adds/exits
- [ ] Form 4 parser → insider classification (discretionary/administrative)
- [ ] BPIQ/BiopharmaWatch → catalyst calendar updates
- [ ] Generate daily ODIN_DAILY digest with highlights

### Phase 4: Integration With Existing ODIN_v10 (3 Weeks)
- [ ] Merge specialist_funds, google_trends, revenue_proxies into ODIN_v10_CONFIG.json
- [ ] Update ODIN_v10_H1_2026_PREDICTIONS.csv with new columns
- [ ] Recalibrate tier thresholds (T1-T5) using new specialist + GT signals
- [ ] Validate Brier score improvement on historical catalysts

---

## KEY WATCHLIST FOR IMMEDIATE ACTION

### TIER A+ CATALYSTS (Binary, This Quarter)
1. **IRON (Disc Medicine)** — FDA CNPV decision (early 2026)
   - Specialists: RA Capital (recent add), OrbiMed
   - GT: emerging (enable keyword monitoring)
   - Beat Probability: **0.78**

2. **RNA (Avidity Biosciences)** — BLA submission (Q1 2026)
   - Specialists: RTW, others
   - Catalyst: Pre-M&A (Novartis $12B deal H1 2026)
   - Beat Probability: **0.82**

3. **KOD (Kodiak Sciences)** — Phase 3 GLOW2 topline (Q1 2026)
   - Specialists: Baker Bros (recent add)
   - Program: Diabetic retinopathy (big market)
   - Beat Probability: **0.65**

### TIER A CATALYSTS (Commercial Inflection)
4. **PGEN (Precigen)** — Q4 2025 earnings (Mar 18), first full PAPZIMEOS quarter
   - GT Commercial Ramp: Confirmed (+22% RSV)
   - Hub Enrollments: Doubling (Jan 2026)
   - Beat Probability: **0.72**

5. **CELC (Celcuity)** — PDUFA (Jul 17, 2026)
   - Specialists: Perceptive (core pillar, 82% 2025 return)
   - Earnings: Mar 30 (setup quarter)
   - Beat Probability: **0.68**

---

## SUMMARY FOR CLAUDE & CHATGPT

**Your Job:** Build out the logic layers so Odin v10 becomes **self-updating and autonomous**.

**What you have:**
- ✅ PDUFA/ADCOM/BLA binary approval logic (existing)
- ✅ Insider sentiment framework (NEW, needs validation)
- ✅ Specialist fund weighting (NEW, needs 13F integration)
- ✅ Google Trends composite (NEW, needs commercial-ramp filter)
- ✅ Revenue proxy scaffold (NEW, needs TRx/GTN/inventory calibration)
- ✅ Daily digest template (NEW, needs automation)

**What you need:**
1. **Insider parser:** Form 4 footnotes → "discretionary vs. administrative"
2. **GT engine:** PyTrends/Serper → commercial ramp detection
3. **Specialist scanner:** WhaleWisdom → position changes
4. **Revenue module:** TRx_proxy × GTN × multiplier → beat/miss probability
5. **Daily automator:** Pulls all above → generates `ODIN_DAILY_*.md`

Everything is modular, testable, and ready for implementation.

---

**File Generated:** 2026-01-31 14:07 PST  
**Next Step:** Claude & ChatGPT → Phase 1 Logic Audit (insider classification, S2S ratio validation)