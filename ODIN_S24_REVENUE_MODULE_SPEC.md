# ODIN S24 Revenue Impact Module - Engineering Specification

**Version:** 1.0  
**Author:** Claude (Research Authority)  
**For:** ChatGPT (Engineering Implementation)  
**Date:** 2026-02-03  

---

## Executive Summary

This specification defines the S24 Revenue Impact Signal for ODIN v10.4. The signal captures the relationship between a drug's revenue potential and stock price reaction magnitude to FDA decisions. Research validates that revenue/market cap ratio strongly predicts abnormal returns, with small biotechs (<$500M market cap) showing 2-5x larger reactions.

**Key Insight:** A $2B peak sales drug for a $500M company (4.0x ratio) will move stock 3-5x more than the same drug for a $50B company (0.04x ratio).

---

## 1. Signal Definition

### S24_REVENUE_IMPACT

| Parameter | Value |
|-----------|-------|
| Signal ID | S24 |
| Signal Name | Revenue Impact Factor |
| Category | Commercial Potential |
| Direction | Position Sizing (not approval probability) |
| Data Type | Continuous ratio + categorical tier |
| Update Frequency | Pre-PDUFA (T-30 minimum) |

### Core Formula

```python
revenue_impact_ratio = peak_sales_estimate / market_cap
```

Where:
- `peak_sales_estimate`: Analyst consensus or calculated peak annual revenue (USD)
- `market_cap`: Current market capitalization at T-30 (USD)

---

## 2. Tier Classification System

### Revenue Impact Tiers (R1-R4)

```python
REVENUE_TIERS = {
    "R1_HIGH_IMPACT": {
        "ratio_min": 2.0,
        "ratio_max": float('inf'),
        "description": "Transformational - stock could 3x+ on approval",
        "position_multiplier": 1.5,
        "expected_move_approval": "+150% to +400%",
        "expected_move_crl": "-60% to -80%"
    },
    "R2_MODERATE_IMPACT": {
        "ratio_min": 0.5,
        "ratio_max": 2.0,
        "description": "Significant - material stock movement expected",
        "position_multiplier": 1.2,
        "expected_move_approval": "+30% to +150%",
        "expected_move_crl": "-30% to -60%"
    },
    "R3_LOW_IMPACT": {
        "ratio_min": 0.1,
        "ratio_max": 0.5,
        "description": "Modest - stock moves but not transformational",
        "position_multiplier": 1.0,
        "expected_move_approval": "+10% to +30%",
        "expected_move_crl": "-15% to -30%"
    },
    "R4_MINIMAL_IMPACT": {
        "ratio_min": 0.0,
        "ratio_max": 0.1,
        "description": "Negligible - large cap or small drug",
        "position_multiplier": 0.7,
        "expected_move_approval": "+2% to +10%",
        "expected_move_crl": "-5% to -15%"
    }
}
```

### Market Cap Size Modifier

Small biotechs show amplified reactions. Apply this modifier to expected moves:

```python
MARKET_CAP_MODIFIERS = {
    "MICRO": {"max_cap": 300_000_000, "volatility_mult": 2.5},      # <$300M
    "SMALL": {"max_cap": 1_000_000_000, "volatility_mult": 1.8},    # $300M-$1B
    "MID": {"max_cap": 10_000_000_000, "volatility_mult": 1.2},     # $1B-$10B
    "LARGE": {"max_cap": float('inf'), "volatility_mult": 1.0}      # >$10B
}
```

---

## 3. Peak Sales Estimation Methods

### Method Priority (use first available)

```python
ESTIMATION_METHODS = [
    {
        "priority": 1,
        "method": "ANALYST_CONSENSUS",
        "source": "EvaluatePharma, GlobalData, SEC filings",
        "confidence": 0.9,
        "description": "Multiple analyst estimates averaged"
    },
    {
        "priority": 2,
        "method": "COMPANY_GUIDANCE",
        "source": "10-K, investor presentations, earnings calls",
        "confidence": 0.75,
        "description": "Management's stated peak sales target"
    },
    {
        "priority": 3,
        "method": "COMPARABLE_DRUG",
        "source": "Historical drug launches in same indication",
        "confidence": 0.6,
        "description": "Benchmark against similar approved drugs"
    },
    {
        "priority": 4,
        "method": "EPIDEMIOLOGY_CALC",
        "source": "Patient population × pricing × market share",
        "confidence": 0.5,
        "description": "Bottom-up patient-based calculation"
    }
]
```

### Epidemiology Calculation Formula

When analyst data unavailable:

```python
def calculate_peak_sales(
    patient_population: int,
    diagnosis_rate: float,
    treatment_rate: float,
    market_share_peak: float,
    annual_price: float,
    years_to_peak: int = 7
) -> dict:
    """
    Bottom-up peak sales calculation using Bass Diffusion Model assumptions.
    
    Returns:
        dict with peak_sales, methodology, confidence
    """
    addressable_patients = patient_population * diagnosis_rate * treatment_rate
    peak_patients = addressable_patients * market_share_peak
    peak_sales = peak_patients * annual_price
    
    return {
        "peak_sales": peak_sales,
        "addressable_patients": addressable_patients,
        "peak_patients": peak_patients,
        "methodology": "EPIDEMIOLOGY_CALC",
        "confidence": 0.5,
        "years_to_peak": years_to_peak
    }
```

### Revenue Multipliers

Apply these multipliers to base peak sales estimates:

```python
REVENUE_MULTIPLIERS = {
    # Positive factors
    "first_in_class": 1.5,
    "best_in_class": 1.3,
    "unmet_need_high": 1.4,
    "novel_mechanism": 1.6,
    "orphan_pricing": 1.3,
    "global_rights": 1.2,
    
    # Negative factors
    "me_too": 0.6,
    "crowded_market": 0.7,
    "generic_threat_near": 0.5,
    "limited_geography": 0.7,
    "partnership_split": 0.5,  # If partner takes significant revenue
    
    # Sponsor factors
    "big_pharma_sponsor": 0.5,  # Revenue already priced in
    "acquisition_target": 1.3   # Buyout premium potential
}
```

---

## 4. Data Structure

### RevenueAnalysis Class

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class RevenueTier(Enum):
    R1_HIGH_IMPACT = "R1"
    R2_MODERATE_IMPACT = "R2"
    R3_LOW_IMPACT = "R3"
    R4_MINIMAL_IMPACT = "R4"

class MarketCapSize(Enum):
    MICRO = "MICRO"      # <$300M
    SMALL = "SMALL"      # $300M-$1B
    MID = "MID"          # $1B-$10B
    LARGE = "LARGE"      # >$10B

@dataclass
class RevenueAnalysis:
    """Revenue impact analysis for a PDUFA event."""
    
    # Identifiers
    ticker: str
    asset: str
    indication: str
    pdufa_date: str
    
    # Core metrics
    peak_sales_estimate: float          # USD
    peak_sales_low: Optional[float]     # USD (range low)
    peak_sales_high: Optional[float]    # USD (range high)
    market_cap: float                   # USD at T-30
    shares_outstanding: float
    stock_price_t30: float
    
    # Calculated fields
    revenue_impact_ratio: float = field(init=False)
    revenue_tier: RevenueTier = field(init=False)
    market_cap_size: MarketCapSize = field(init=False)
    position_multiplier: float = field(init=False)
    
    # Estimation metadata
    estimation_method: str              # ANALYST_CONSENSUS, COMPANY_GUIDANCE, etc.
    estimation_confidence: float        # 0.0 to 1.0
    estimation_sources: List[str] = field(default_factory=list)
    
    # Multipliers applied
    multipliers_applied: Dict[str, float] = field(default_factory=dict)
    adjusted_peak_sales: float = field(init=False)
    
    # Drug characteristics
    is_first_in_class: bool = False
    is_best_in_class: bool = False
    is_orphan: bool = False
    unmet_need_level: str = "MODERATE"  # HIGH, MODERATE, LOW
    competitive_landscape: str = "MODERATE"  # CLEAR, MODERATE, CROWDED
    
    # Timestamps
    analysis_date: datetime = field(default_factory=datetime.now)
    data_as_of: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self._apply_multipliers()
        self._calculate_ratio()
        self._classify_tier()
        self._classify_market_cap()
        self._calculate_position_multiplier()
    
    def _apply_multipliers(self):
        """Apply revenue multipliers to base estimate."""
        multiplier = 1.0
        
        if self.is_first_in_class:
            multiplier *= 1.5
            self.multipliers_applied["first_in_class"] = 1.5
        elif self.is_best_in_class:
            multiplier *= 1.3
            self.multipliers_applied["best_in_class"] = 1.3
            
        if self.is_orphan:
            multiplier *= 1.3
            self.multipliers_applied["orphan_pricing"] = 1.3
            
        if self.unmet_need_level == "HIGH":
            multiplier *= 1.4
            self.multipliers_applied["unmet_need_high"] = 1.4
            
        if self.competitive_landscape == "CROWDED":
            multiplier *= 0.7
            self.multipliers_applied["crowded_market"] = 0.7
        elif self.competitive_landscape == "CLEAR":
            multiplier *= 1.2
            self.multipliers_applied["clear_market"] = 1.2
            
        self.adjusted_peak_sales = self.peak_sales_estimate * multiplier
    
    def _calculate_ratio(self):
        """Calculate revenue impact ratio."""
        if self.market_cap > 0:
            self.revenue_impact_ratio = self.adjusted_peak_sales / self.market_cap
        else:
            self.revenue_impact_ratio = 0.0
    
    def _classify_tier(self):
        """Classify into revenue tier based on ratio."""
        ratio = self.revenue_impact_ratio
        if ratio >= 2.0:
            self.revenue_tier = RevenueTier.R1_HIGH_IMPACT
        elif ratio >= 0.5:
            self.revenue_tier = RevenueTier.R2_MODERATE_IMPACT
        elif ratio >= 0.1:
            self.revenue_tier = RevenueTier.R3_LOW_IMPACT
        else:
            self.revenue_tier = RevenueTier.R4_MINIMAL_IMPACT
    
    def _classify_market_cap(self):
        """Classify market cap size."""
        cap = self.market_cap
        if cap < 300_000_000:
            self.market_cap_size = MarketCapSize.MICRO
        elif cap < 1_000_000_000:
            self.market_cap_size = MarketCapSize.SMALL
        elif cap < 10_000_000_000:
            self.market_cap_size = MarketCapSize.MID
        else:
            self.market_cap_size = MarketCapSize.LARGE
    
    def _calculate_position_multiplier(self):
        """Calculate position sizing multiplier."""
        # Base multiplier from tier
        tier_multipliers = {
            RevenueTier.R1_HIGH_IMPACT: 1.5,
            RevenueTier.R2_MODERATE_IMPACT: 1.2,
            RevenueTier.R3_LOW_IMPACT: 1.0,
            RevenueTier.R4_MINIMAL_IMPACT: 0.7
        }
        base = tier_multipliers[self.revenue_tier]
        
        # Adjust for market cap volatility
        cap_adjustments = {
            MarketCapSize.MICRO: 0.8,   # Reduce for extreme volatility
            MarketCapSize.SMALL: 1.0,
            MarketCapSize.MID: 1.1,
            MarketCapSize.LARGE: 1.0
        }
        
        self.position_multiplier = base * cap_adjustments[self.market_cap_size]
    
    def get_expected_move(self, outcome: str) -> tuple:
        """
        Get expected stock move range based on tier and outcome.
        
        Args:
            outcome: "APPROVAL" or "CRL"
            
        Returns:
            Tuple of (move_low_pct, move_high_pct)
        """
        moves = {
            RevenueTier.R1_HIGH_IMPACT: {
                "APPROVAL": (1.5, 4.0),
                "CRL": (-0.8, -0.6)
            },
            RevenueTier.R2_MODERATE_IMPACT: {
                "APPROVAL": (0.3, 1.5),
                "CRL": (-0.6, -0.3)
            },
            RevenueTier.R3_LOW_IMPACT: {
                "APPROVAL": (0.1, 0.3),
                "CRL": (-0.3, -0.15)
            },
            RevenueTier.R4_MINIMAL_IMPACT: {
                "APPROVAL": (0.02, 0.1),
                "CRL": (-0.15, -0.05)
            }
        }
        
        base_move = moves[self.revenue_tier][outcome]
        
        # Apply market cap volatility modifier
        vol_mults = {
            MarketCapSize.MICRO: 2.5,
            MarketCapSize.SMALL: 1.8,
            MarketCapSize.MID: 1.2,
            MarketCapSize.LARGE: 1.0
        }
        vol_mult = vol_mults[self.market_cap_size]
        
        return (base_move[0] * vol_mult, base_move[1] * vol_mult)
    
    def to_dict(self) -> dict:
        """Export to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "asset": self.asset,
            "indication": self.indication,
            "pdufa_date": self.pdufa_date,
            "peak_sales_estimate": self.peak_sales_estimate,
            "adjusted_peak_sales": self.adjusted_peak_sales,
            "market_cap": self.market_cap,
            "revenue_impact_ratio": round(self.revenue_impact_ratio, 3),
            "revenue_tier": self.revenue_tier.value,
            "market_cap_size": self.market_cap_size.value,
            "position_multiplier": round(self.position_multiplier, 2),
            "estimation_method": self.estimation_method,
            "estimation_confidence": self.estimation_confidence,
            "multipliers_applied": self.multipliers_applied,
            "is_first_in_class": self.is_first_in_class,
            "is_orphan": self.is_orphan,
            "analysis_date": self.analysis_date.isoformat()
        }
```

---

## 5. Integration with ODIN Scoring

### S24 Signal Weight Configuration

Add to `ODIN_v10_CONFIG`:

```python
# S24 Revenue Impact - Position Sizing Signal
# NOTE: This signal does NOT affect approval probability
# It affects POSITION SIZE and EXPECTED MOVE calculations

S24_CONFIG = {
    "signal_id": "S24",
    "signal_name": "Revenue Impact Factor",
    "signal_type": "POSITION_SIZING",  # Not PROBABILITY
    "enabled": True,
    
    # Position sizing weights by tier
    "tier_weights": {
        "R1_HIGH_IMPACT": 1.5,
        "R2_MODERATE_IMPACT": 1.2,
        "R3_LOW_IMPACT": 1.0,
        "R4_MINIMAL_IMPACT": 0.7
    },
    
    # Risk adjustment for high-impact events
    "risk_adjustment": {
        "R1_reduce_on_low_approval": True,  # If TIER_3/4 approval + R1 = extra caution
        "R1_increase_on_high_approval": True  # If TIER_1 approval + R1 = maximize
    }
}
```

### Position Sizing Integration

```python
def calculate_position_size(
    base_position: float,
    odin_tier: str,
    revenue_tier: str,
    revenue_analysis: RevenueAnalysis
) -> dict:
    """
    Calculate final position size integrating ODIN approval tier with revenue impact.
    
    Args:
        base_position: Base position size in dollars
        odin_tier: ODIN approval tier (TIER_1 to TIER_4)
        revenue_tier: Revenue tier (R1 to R4)
        revenue_analysis: Full RevenueAnalysis object
        
    Returns:
        dict with position size, rationale, and risk metrics
    """
    
    # ODIN tier confidence multipliers
    odin_multipliers = {
        "TIER_1": 1.0,   # High confidence approval
        "TIER_2": 0.8,   # Moderate confidence
        "TIER_3": 0.5,   # Low confidence
        "TIER_4": 0.0    # Avoid - HARD AVOID per ODIN rules
    }
    
    # Revenue tier position multipliers
    revenue_multipliers = {
        "R1": 1.5,
        "R2": 1.2,
        "R3": 1.0,
        "R4": 0.7
    }
    
    odin_mult = odin_multipliers.get(odin_tier, 0.5)
    rev_mult = revenue_multipliers.get(revenue_tier, 1.0)
    
    # Combined multiplier
    combined_mult = odin_mult * rev_mult
    
    # Risk adjustment: High revenue + low approval confidence = danger zone
    if revenue_tier == "R1" and odin_tier in ["TIER_3", "TIER_4"]:
        combined_mult *= 0.5  # Extra caution
        risk_flag = "HIGH_RISK_MISMATCH"
    elif revenue_tier == "R1" and odin_tier == "TIER_1":
        combined_mult *= 1.2  # Maximum opportunity
        risk_flag = "OPTIMAL_OPPORTUNITY"
    else:
        risk_flag = "STANDARD"
    
    final_position = base_position * combined_mult
    
    # Calculate expected value
    approval_prob = {"TIER_1": 0.96, "TIER_2": 0.85, "TIER_3": 0.70, "TIER_4": 0.40}[odin_tier]
    move_up = revenue_analysis.get_expected_move("APPROVAL")
    move_down = revenue_analysis.get_expected_move("CRL")
    
    expected_value = (approval_prob * move_up[0] + (1 - approval_prob) * move_down[1])
    
    return {
        "base_position": base_position,
        "final_position": round(final_position, 2),
        "odin_tier": odin_tier,
        "revenue_tier": revenue_tier,
        "combined_multiplier": round(combined_mult, 3),
        "risk_flag": risk_flag,
        "expected_value_pct": round(expected_value * 100, 1),
        "expected_move_approval": f"+{move_up[0]*100:.0f}% to +{move_up[1]*100:.0f}%",
        "expected_move_crl": f"{move_down[0]*100:.0f}% to {move_down[1]*100:.0f}%"
    }
```

---

## 6. Data Collection Functions

### SEC Filing Parser

```python
import re
from typing import Optional

def extract_peak_sales_from_sec(ticker: str, filing_type: str = "10-K") -> Optional[dict]:
    """
    Extract peak sales estimates from SEC filings.
    
    Searches for patterns like:
    - "peak sales of $X billion"
    - "peak annual revenue of $X million"
    - "market opportunity of $X"
    
    Args:
        ticker: Stock ticker symbol
        filing_type: "10-K", "10-Q", "8-K", "S-1"
        
    Returns:
        dict with peak_sales, source_text, filing_date
    """
    # Regex patterns for revenue mentions
    REVENUE_PATTERNS = [
        r'peak\s+(?:annual\s+)?(?:sales|revenue)\s+(?:of\s+)?\$?([\d,.]+)\s*(billion|million|B|M)',
        r'(?:addressable|total)\s+market\s+(?:opportunity|size)\s+(?:of\s+)?\$?([\d,.]+)\s*(billion|million|B|M)',
        r'peak\s+(?:year\s+)?(?:sales|revenue)\s+(?:estimate|projection|forecast)\s+(?:of\s+)?\$?([\d,.]+)\s*(billion|million|B|M)',
        r'(?:could|may|expected\s+to)\s+reach\s+\$?([\d,.]+)\s*(billion|million|B|M)\s+(?:in\s+)?(?:peak\s+)?(?:annual\s+)?(?:sales|revenue)',
    ]
    
    # Implementation: fetch filing from SEC EDGAR, apply patterns
    # Return structured result
    pass  # ChatGPT to implement


def extract_peak_sales_from_presentation(ticker: str) -> Optional[dict]:
    """
    Extract peak sales from investor presentations.
    
    Common patterns:
    - Market opportunity slides
    - Revenue projection charts
    - Analyst day presentations
    """
    pass  # ChatGPT to implement
```

### FinBrain Integration

```python
def get_analyst_consensus(ticker: str) -> Optional[dict]:
    """
    Get analyst price targets and extract implied peak sales.
    
    Uses FinBrain MCP analyst_ratings_by_ticker.
    Calculate implied peak sales from price target and current market cap.
    """
    # Use finbrain:analyst_ratings_by_ticker MCP tool
    # Extract target prices
    # Calculate implied upside
    pass  # ChatGPT to implement


def get_market_cap(ticker: str) -> float:
    """
    Get current market cap for ticker.
    
    Uses FinBrain or public API.
    """
    pass  # ChatGPT to implement
```

### Comparable Drug Database

```python
COMPARABLE_DRUGS_DATABASE = {
    # Oncology
    "NSCLC_1L": {
        "benchmark_drug": "Keytruda",
        "peak_sales": 25_000_000_000,  # $25B
        "years_to_peak": 8,
        "patient_population": 230_000,
        "annual_price": 175_000
    },
    "NSCLC_2L": {
        "benchmark_drug": "Opdivo",
        "peak_sales": 8_000_000_000,
        "years_to_peak": 6,
        "patient_population": 115_000,
        "annual_price": 150_000
    },
    "HER2_BREAST": {
        "benchmark_drug": "Herceptin",
        "peak_sales": 7_500_000_000,
        "years_to_peak": 10,
        "patient_population": 40_000,
        "annual_price": 70_000
    },
    
    # CNS
    "ALZHEIMERS": {
        "benchmark_drug": "Leqembi",
        "peak_sales": 5_000_000_000,  # Projected
        "years_to_peak": 8,
        "patient_population": 6_500_000,
        "annual_price": 26_500
    },
    "DEPRESSION_TRD": {
        "benchmark_drug": "Spravato",
        "peak_sales": 1_500_000_000,
        "years_to_peak": 6,
        "patient_population": 2_800_000,
        "annual_price": 20_000
    },
    
    # Rare Disease
    "DMD": {
        "benchmark_drug": "Exondys 51",
        "peak_sales": 500_000_000,
        "years_to_peak": 5,
        "patient_population": 15_000,
        "annual_price": 300_000
    },
    "SMA": {
        "benchmark_drug": "Spinraza",
        "peak_sales": 2_100_000_000,
        "years_to_peak": 5,
        "patient_population": 25_000,
        "annual_price": 750_000
    },
    
    # Add more indications as needed
}


def get_comparable_peak_sales(indication: str, differentiators: dict) -> dict:
    """
    Estimate peak sales based on comparable drugs.
    
    Args:
        indication: Disease indication key
        differentiators: dict with first_in_class, efficacy_advantage, etc.
        
    Returns:
        dict with estimated_peak_sales, comparable_drug, adjustments
    """
    if indication not in COMPARABLE_DRUGS_DATABASE:
        return {"error": f"No comparable for {indication}"}
    
    comp = COMPARABLE_DRUGS_DATABASE[indication]
    base_sales = comp["peak_sales"]
    
    # Apply differentiator adjustments
    multiplier = 1.0
    if differentiators.get("first_in_class"):
        multiplier *= 1.5
    if differentiators.get("efficacy_advantage"):
        multiplier *= 1.2
    if differentiators.get("safety_advantage"):
        multiplier *= 1.1
    if differentiators.get("convenience_advantage"):  # Oral vs IV, etc.
        multiplier *= 1.15
    if differentiators.get("me_too"):
        multiplier *= 0.3  # Significant discount for me-too
        
    return {
        "comparable_drug": comp["benchmark_drug"],
        "comparable_peak_sales": base_sales,
        "estimated_peak_sales": base_sales * multiplier,
        "multiplier_applied": multiplier,
        "differentiators": differentiators,
        "methodology": "COMPARABLE_DRUG",
        "confidence": 0.6
    }
```

---

## 7. Validation Targets: Feb/Mar/Apr 2026 PDUFAs

### Target Events for Model Validation

```python
VALIDATION_TARGETS_Q1_2026 = [
    # February 2026
    {
        "ticker": "IRON",
        "company": "Disc Medicine",
        "asset": "bitopertin",
        "indication": "Erythropoietic protoporphyria (EPP)",
        "pdufa_date": "2026-02-15",
        "therapeutic_area": "Rare Disease",
        "research_tasks": [
            "Get market cap",
            "Find analyst peak sales estimates",
            "Identify comparable rare disease drugs",
            "Calculate patient population × pricing"
        ]
    },
    {
        "ticker": "VNDA",
        "company": "Vanda Pharmaceuticals",
        "asset": "tradipitant",
        "indication": "Gastroparesis",
        "pdufa_date": "2026-02-28",
        "therapeutic_area": "GI/Hepatology",
        "research_tasks": [
            "Get market cap",
            "Gastroparesis market size",
            "Competitor analysis (no approved drugs)",
            "First-in-class premium"
        ]
    },
    
    # March 2026
    {
        "ticker": "RCKT",
        "company": "Rocket Pharmaceuticals",
        "asset": "RP-A501",
        "indication": "Danon Disease",
        "pdufa_date": "2026-03-28",
        "therapeutic_area": "Rare Disease",
        "is_gene_therapy": True,
        "research_tasks": [
            "Gene therapy pricing ($2-3M typical)",
            "Danon Disease patient population (~300 US)",
            "Market cap",
            "First-in-class status"
        ]
    },
    
    # April 2026
    {
        "ticker": "DNLI",
        "company": "Denali Therapeutics",
        "asset": "tofersen",
        "indication": "Hunter Syndrome (MPS II)",
        "pdufa_date": "2026-04-05",
        "therapeutic_area": "Rare Disease",
        "research_tasks": [
            "Get market cap",
            "MPS II market size",
            "Elaprase (competitor) annual sales",
            "Partnership terms with Biogen"
        ]
    },
    
    # Add other Q1 2026 PDUFAs as discovered
]
```

---

## 8. Output Format

### JSON Schema for Revenue Analysis

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ODIN S24 Revenue Analysis",
  "type": "object",
  "required": ["ticker", "asset", "pdufa_date", "revenue_analysis"],
  "properties": {
    "ticker": {"type": "string"},
    "asset": {"type": "string"},
    "indication": {"type": "string"},
    "pdufa_date": {"type": "string", "format": "date"},
    "revenue_analysis": {
      "type": "object",
      "required": ["peak_sales_estimate", "market_cap", "revenue_impact_ratio", "revenue_tier"],
      "properties": {
        "peak_sales_estimate": {"type": "number"},
        "peak_sales_low": {"type": "number"},
        "peak_sales_high": {"type": "number"},
        "adjusted_peak_sales": {"type": "number"},
        "market_cap": {"type": "number"},
        "revenue_impact_ratio": {"type": "number"},
        "revenue_tier": {"enum": ["R1", "R2", "R3", "R4"]},
        "market_cap_size": {"enum": ["MICRO", "SMALL", "MID", "LARGE"]},
        "position_multiplier": {"type": "number"},
        "estimation_method": {"type": "string"},
        "estimation_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "estimation_sources": {"type": "array", "items": {"type": "string"}},
        "multipliers_applied": {"type": "object"},
        "expected_move_approval": {"type": "string"},
        "expected_move_crl": {"type": "string"}
      }
    },
    "odin_integration": {
      "type": "object",
      "properties": {
        "odin_tier": {"enum": ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]},
        "combined_position_multiplier": {"type": "number"},
        "risk_flag": {"type": "string"},
        "recommendation": {"type": "string"}
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "analysis_date": {"type": "string", "format": "date-time"},
        "analyst": {"type": "string"},
        "version": {"type": "string"}
      }
    }
  }
}
```

---

## 9. Implementation Checklist for ChatGPT

### Phase 1: Core Module (Priority)
- [ ] Implement `RevenueAnalysis` dataclass
- [ ] Implement tier classification logic
- [ ] Implement position multiplier calculation
- [ ] Create JSON export functionality

### Phase 2: Data Collection
- [ ] Implement market cap retrieval (use available APIs)
- [ ] Implement SEC filing parser for peak sales mentions
- [ ] Build comparable drug database lookup
- [ ] Create epidemiology calculation function

### Phase 3: Integration
- [ ] Add S24 to ODIN config
- [ ] Integrate with position sizing logic
- [ ] Create combined scoring output

### Phase 4: Validation
- [ ] Research IRON (Feb 2026) - get all data points
- [ ] Research VNDA (Feb 2026) - get all data points
- [ ] Research RCKT (Mar 2026) - get all data points
- [ ] Research DNLI (Apr 2026) - get all data points
- [ ] Calculate revenue tiers for each
- [ ] Document predictions for post-PDUFA validation

---

## 10. API References for ChatGPT

### Available MCPs
- **FinBrain**: `analyst_ratings_by_ticker`, `predictions_by_ticker`, `insider_transactions_by_ticker`
- **LunarCrush**: Social sentiment data
- **Clinical Trials**: `search_trials`, `get_trial_details`
- **Open Targets**: Disease-target associations
- **ChEMBL**: Drug/compound data

### External APIs (if available)
- SEC EDGAR for filings
- Yahoo Finance / FMP for market cap
- Web search for analyst reports

---

## Questions for David (Research Authority)

1. Should R1 events with TIER_4 ODIN score be complete AVOID or reduced position?
2. Preferred threshold for "MICRO" cap - $300M or $250M?
3. Include M&A premium factor in calculation?
4. How to handle partnership splits (50/50 revenue share)?

---

*End of Specification - Ready for ChatGPT Implementation*
