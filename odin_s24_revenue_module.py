"""
ODIN S24 Revenue Impact Module - Implementation Stub
=====================================================
Version: 1.0
For: ChatGPT Engineering Implementation

This file contains the core implementation structure. ChatGPT should:
1. Complete the data collection functions
2. Add API integrations
3. Implement validation logic
4. Connect to ODIN scoring pipeline
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from enum import Enum
import os

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class RevenueTier(Enum):
    R1_HIGH_IMPACT = "R1"      # ratio >= 2.0x
    R2_MODERATE_IMPACT = "R2"  # 0.5x <= ratio < 2.0x
    R3_LOW_IMPACT = "R3"       # 0.1x <= ratio < 0.5x
    R4_MINIMAL_IMPACT = "R4"   # ratio < 0.1x

class MarketCapSize(Enum):
    MICRO = "MICRO"   # <$300M
    SMALL = "SMALL"   # $300M-$1B
    MID = "MID"       # $1B-$10B
    LARGE = "LARGE"   # >$10B

class EstimationMethod(Enum):
    ANALYST_CONSENSUS = "ANALYST_CONSENSUS"
    COMPANY_GUIDANCE = "COMPANY_GUIDANCE"
    COMPARABLE_DRUG = "COMPARABLE_DRUG"
    EPIDEMIOLOGY_CALC = "EPIDEMIOLOGY_CALC"

# Tier thresholds
TIER_THRESHOLDS = {
    "R1": 2.0,
    "R2": 0.5,
    "R3": 0.1,
    "R4": 0.0
}

# Market cap thresholds (USD)
MARKET_CAP_THRESHOLDS = {
    "MICRO": 300_000_000,
    "SMALL": 1_000_000_000,
    "MID": 10_000_000_000
}

# Position multipliers by tier
POSITION_MULTIPLIERS = {
    RevenueTier.R1_HIGH_IMPACT: 1.5,
    RevenueTier.R2_MODERATE_IMPACT: 1.2,
    RevenueTier.R3_LOW_IMPACT: 1.0,
    RevenueTier.R4_MINIMAL_IMPACT: 0.7
}

# Volatility multipliers by market cap
VOLATILITY_MULTIPLIERS = {
    MarketCapSize.MICRO: 2.5,
    MarketCapSize.SMALL: 1.8,
    MarketCapSize.MID: 1.2,
    MarketCapSize.LARGE: 1.0
}

# Expected move ranges by tier (approval_low, approval_high, crl_low, crl_high)
EXPECTED_MOVES = {
    RevenueTier.R1_HIGH_IMPACT: (1.5, 4.0, -0.8, -0.6),
    RevenueTier.R2_MODERATE_IMPACT: (0.3, 1.5, -0.6, -0.3),
    RevenueTier.R3_LOW_IMPACT: (0.1, 0.3, -0.3, -0.15),
    RevenueTier.R4_MINIMAL_IMPACT: (0.02, 0.1, -0.15, -0.05)
}

# Revenue adjustment multipliers
REVENUE_MULTIPLIERS = {
    "first_in_class": 1.5,
    "best_in_class": 1.3,
    "unmet_need_high": 1.4,
    "novel_mechanism": 1.6,
    "orphan_pricing": 1.3,
    "global_rights": 1.2,
    "me_too": 0.6,
    "crowded_market": 0.7,
    "generic_threat_near": 0.5,
    "limited_geography": 0.7,
    "partnership_split": 0.5,
    "big_pharma_sponsor": 0.5,
    "acquisition_target": 1.3
}

# =============================================================================
# COMPARABLE DRUG DATABASE
# =============================================================================

COMPARABLE_DRUGS = {
    # Oncology
    "NSCLC_1L": {"drug": "Keytruda", "peak_sales": 25_000_000_000, "patients": 230_000, "price": 175_000},
    "NSCLC_2L": {"drug": "Opdivo", "peak_sales": 8_000_000_000, "patients": 115_000, "price": 150_000},
    "HER2_BREAST": {"drug": "Herceptin", "peak_sales": 7_500_000_000, "patients": 40_000, "price": 70_000},
    "MELANOMA_1L": {"drug": "Keytruda", "peak_sales": 5_000_000_000, "patients": 100_000, "price": 175_000},
    "AML": {"drug": "Venclexta", "peak_sales": 2_500_000_000, "patients": 20_000, "price": 120_000},
    
    # CNS
    "ALZHEIMERS": {"drug": "Leqembi", "peak_sales": 5_000_000_000, "patients": 6_500_000, "price": 26_500},
    "DEPRESSION_TRD": {"drug": "Spravato", "peak_sales": 1_500_000_000, "patients": 2_800_000, "price": 20_000},
    "PARKINSONS": {"drug": "Nuplazid", "peak_sales": 800_000_000, "patients": 1_000_000, "price": 30_000},
    "EPILEPSY": {"drug": "Epidiolex", "peak_sales": 1_200_000_000, "patients": 200_000, "price": 32_500},
    
    # Rare Disease
    "DMD": {"drug": "Exondys 51", "peak_sales": 500_000_000, "patients": 15_000, "price": 300_000},
    "SMA": {"drug": "Spinraza", "peak_sales": 2_100_000_000, "patients": 25_000, "price": 750_000},
    "DANON": {"drug": None, "peak_sales": 300_000_000, "patients": 300, "price": 2_000_000},  # Gene therapy
    "EPP": {"drug": "Scenesse", "peak_sales": 200_000_000, "patients": 10_000, "price": 50_000},
    "HUNTER_MPS2": {"drug": "Elaprase", "peak_sales": 700_000_000, "patients": 2_000, "price": 500_000},
    
    # GI
    "GASTROPARESIS": {"drug": None, "peak_sales": 1_000_000_000, "patients": 5_000_000, "price": 15_000},  # First-in-class
    "IBD_UC": {"drug": "Entyvio", "peak_sales": 5_000_000_000, "patients": 1_000_000, "price": 40_000},
    "CROHNS": {"drug": "Stelara", "peak_sales": 4_000_000_000, "patients": 800_000, "price": 50_000},
    
    # Cardiology
    "HEART_FAILURE": {"drug": "Entresto", "peak_sales": 6_000_000_000, "patients": 6_000_000, "price": 15_000},
    "HOCM": {"drug": "Camzyos", "peak_sales": 2_000_000_000, "patients": 100_000, "price": 90_000},
    
    # Hematology
    "SICKLE_CELL": {"drug": "Casgevy", "peak_sales": 2_000_000_000, "patients": 100_000, "price": 2_200_000},
    "HEMOPHILIA_A": {"drug": "Hemlibra", "peak_sales": 4_000_000_000, "patients": 30_000, "price": 500_000},
}

# =============================================================================
# CORE DATA CLASS
# =============================================================================

@dataclass
class RevenueAnalysis:
    """Revenue impact analysis for a PDUFA event."""
    
    # Required fields
    ticker: str
    asset: str
    indication: str
    pdufa_date: str
    peak_sales_estimate: float
    market_cap: float
    estimation_method: str
    estimation_confidence: float
    
    # Optional fields
    peak_sales_low: Optional[float] = None
    peak_sales_high: Optional[float] = None
    shares_outstanding: Optional[float] = None
    stock_price_t30: Optional[float] = None
    estimation_sources: List[str] = field(default_factory=list)
    
    # Drug characteristics
    is_first_in_class: bool = False
    is_best_in_class: bool = False
    is_orphan: bool = False
    unmet_need_level: str = "MODERATE"  # HIGH, MODERATE, LOW
    competitive_landscape: str = "MODERATE"  # CLEAR, MODERATE, CROWDED
    has_partnership_split: bool = False
    is_big_pharma: bool = False
    is_acquisition_target: bool = False
    
    # Calculated fields (set in __post_init__)
    adjusted_peak_sales: float = field(init=False)
    revenue_impact_ratio: float = field(init=False)
    revenue_tier: RevenueTier = field(init=False)
    market_cap_size: MarketCapSize = field(init=False)
    position_multiplier: float = field(init=False)
    multipliers_applied: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    analysis_date: datetime = field(default_factory=datetime.now)
    analyst: str = "ODIN_S24"
    
    def __post_init__(self):
        """Calculate all derived fields."""
        self._apply_multipliers()
        self._calculate_ratio()
        self._classify_tier()
        self._classify_market_cap()
        self._calculate_position_multiplier()
    
    def _apply_multipliers(self):
        """Apply revenue adjustment multipliers."""
        mult = 1.0
        self.multipliers_applied = {}
        
        if self.is_first_in_class:
            mult *= REVENUE_MULTIPLIERS["first_in_class"]
            self.multipliers_applied["first_in_class"] = REVENUE_MULTIPLIERS["first_in_class"]
        elif self.is_best_in_class:
            mult *= REVENUE_MULTIPLIERS["best_in_class"]
            self.multipliers_applied["best_in_class"] = REVENUE_MULTIPLIERS["best_in_class"]
        
        if self.is_orphan:
            mult *= REVENUE_MULTIPLIERS["orphan_pricing"]
            self.multipliers_applied["orphan_pricing"] = REVENUE_MULTIPLIERS["orphan_pricing"]
        
        if self.unmet_need_level == "HIGH":
            mult *= REVENUE_MULTIPLIERS["unmet_need_high"]
            self.multipliers_applied["unmet_need_high"] = REVENUE_MULTIPLIERS["unmet_need_high"]
        
        if self.competitive_landscape == "CROWDED":
            mult *= REVENUE_MULTIPLIERS["crowded_market"]
            self.multipliers_applied["crowded_market"] = REVENUE_MULTIPLIERS["crowded_market"]
        
        if self.has_partnership_split:
            mult *= REVENUE_MULTIPLIERS["partnership_split"]
            self.multipliers_applied["partnership_split"] = REVENUE_MULTIPLIERS["partnership_split"]
        
        if self.is_big_pharma:
            mult *= REVENUE_MULTIPLIERS["big_pharma_sponsor"]
            self.multipliers_applied["big_pharma_sponsor"] = REVENUE_MULTIPLIERS["big_pharma_sponsor"]
        
        if self.is_acquisition_target:
            mult *= REVENUE_MULTIPLIERS["acquisition_target"]
            self.multipliers_applied["acquisition_target"] = REVENUE_MULTIPLIERS["acquisition_target"]
        
        self.adjusted_peak_sales = self.peak_sales_estimate * mult
    
    def _calculate_ratio(self):
        """Calculate revenue/market cap ratio."""
        self.revenue_impact_ratio = (
            self.adjusted_peak_sales / self.market_cap 
            if self.market_cap > 0 else 0.0
        )
    
    def _classify_tier(self):
        """Classify into revenue tier."""
        ratio = self.revenue_impact_ratio
        if ratio >= TIER_THRESHOLDS["R1"]:
            self.revenue_tier = RevenueTier.R1_HIGH_IMPACT
        elif ratio >= TIER_THRESHOLDS["R2"]:
            self.revenue_tier = RevenueTier.R2_MODERATE_IMPACT
        elif ratio >= TIER_THRESHOLDS["R3"]:
            self.revenue_tier = RevenueTier.R3_LOW_IMPACT
        else:
            self.revenue_tier = RevenueTier.R4_MINIMAL_IMPACT
    
    def _classify_market_cap(self):
        """Classify market cap size."""
        cap = self.market_cap
        if cap < MARKET_CAP_THRESHOLDS["MICRO"]:
            self.market_cap_size = MarketCapSize.MICRO
        elif cap < MARKET_CAP_THRESHOLDS["SMALL"]:
            self.market_cap_size = MarketCapSize.SMALL
        elif cap < MARKET_CAP_THRESHOLDS["MID"]:
            self.market_cap_size = MarketCapSize.MID
        else:
            self.market_cap_size = MarketCapSize.LARGE
    
    def _calculate_position_multiplier(self):
        """Calculate position sizing multiplier."""
        base = POSITION_MULTIPLIERS[self.revenue_tier]
        
        # Adjust for market cap volatility (reduce for micro caps)
        cap_adj = {
            MarketCapSize.MICRO: 0.8,
            MarketCapSize.SMALL: 1.0,
            MarketCapSize.MID: 1.1,
            MarketCapSize.LARGE: 1.0
        }
        
        self.position_multiplier = base * cap_adj[self.market_cap_size]
    
    def get_expected_move(self, outcome: str) -> Tuple[float, float]:
        """Get expected stock move range for outcome."""
        base = EXPECTED_MOVES[self.revenue_tier]
        vol_mult = VOLATILITY_MULTIPLIERS[self.market_cap_size]
        
        if outcome.upper() == "APPROVAL":
            return (base[0] * vol_mult, base[1] * vol_mult)
        else:  # CRL
            return (base[2] * vol_mult, base[3] * vol_mult)
    
    def to_dict(self) -> dict:
        """Export to dictionary for JSON serialization."""
        approval_move = self.get_expected_move("APPROVAL")
        crl_move = self.get_expected_move("CRL")
        
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
            "estimation_sources": self.estimation_sources,
            "multipliers_applied": self.multipliers_applied,
            "characteristics": {
                "first_in_class": self.is_first_in_class,
                "best_in_class": self.is_best_in_class,
                "orphan": self.is_orphan,
                "unmet_need": self.unmet_need_level,
                "competition": self.competitive_landscape
            },
            "expected_move_approval": f"+{approval_move[0]*100:.0f}% to +{approval_move[1]*100:.0f}%",
            "expected_move_crl": f"{crl_move[0]*100:.0f}% to {crl_move[1]*100:.0f}%",
            "analysis_date": self.analysis_date.isoformat(),
            "analyst": self.analyst
        }
    
    def to_json(self, filepath: str = None) -> str:
        """Export to JSON string or file."""
        data = self.to_dict()
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        return json.dumps(data, indent=2)


# =============================================================================
# DATA COLLECTION FUNCTIONS (ChatGPT to implement)
# =============================================================================

def get_market_cap(ticker: str) -> Optional[float]:
    """
    Get current market cap for ticker.
    
    TODO: Implement using available APIs:
    - FinBrain predictions (implied from price target)
    - Yahoo Finance API
    - FMP API
    - Web scrape as fallback
    
    Returns:
        Market cap in USD, or None if unavailable
    """
    # IMPLEMENTATION PLACEHOLDER
    # ChatGPT: Use web_search or available APIs
    raise NotImplementedError("ChatGPT to implement")


def get_analyst_peak_sales(ticker: str, asset: str) -> Optional[dict]:
    """
    Get analyst consensus peak sales estimate.
    
    TODO: Implement using:
    - SEC 10-K/10-Q filings (search for "peak sales")
    - Investor presentations
    - Analyst reports from FinBrain
    - BioPharma Dive articles
    
    Returns:
        dict with peak_sales, sources, confidence
    """
    # IMPLEMENTATION PLACEHOLDER
    raise NotImplementedError("ChatGPT to implement")


def get_comparable_estimate(indication: str, characteristics: dict) -> dict:
    """
    Get peak sales estimate from comparable drugs.
    
    Args:
        indication: Disease indication key (e.g., "GASTROPARESIS")
        characteristics: dict with first_in_class, efficacy_advantage, etc.
    
    Returns:
        dict with estimated_peak_sales, comparable_drug, confidence
    """
    if indication not in COMPARABLE_DRUGS:
        return {
            "error": f"No comparable for {indication}",
            "suggestion": "Use epidemiology calculation"
        }
    
    comp = COMPARABLE_DRUGS[indication]
    base = comp["peak_sales"]
    
    mult = 1.0
    adjustments = {}
    
    if characteristics.get("first_in_class"):
        mult *= 1.5
        adjustments["first_in_class"] = 1.5
    if characteristics.get("efficacy_advantage"):
        mult *= 1.2
        adjustments["efficacy_advantage"] = 1.2
    if characteristics.get("safety_advantage"):
        mult *= 1.1
        adjustments["safety_advantage"] = 1.1
    if characteristics.get("convenience"):  # Oral vs IV
        mult *= 1.15
        adjustments["convenience"] = 1.15
    if characteristics.get("me_too"):
        mult *= 0.3
        adjustments["me_too"] = 0.3
    
    return {
        "comparable_drug": comp["drug"],
        "comparable_peak_sales": base,
        "estimated_peak_sales": base * mult,
        "multiplier": mult,
        "adjustments": adjustments,
        "confidence": 0.6,
        "methodology": "COMPARABLE_DRUG"
    }


def calculate_from_epidemiology(
    patient_population: int,
    diagnosis_rate: float,
    treatment_rate: float,
    market_share_peak: float,
    annual_price: float
) -> dict:
    """
    Bottom-up peak sales calculation.
    
    Args:
        patient_population: Total patients with condition
        diagnosis_rate: % who get diagnosed
        treatment_rate: % of diagnosed who get treated
        market_share_peak: Expected peak market share
        annual_price: Annual treatment cost per patient
    
    Returns:
        dict with peak_sales, methodology, confidence
    """
    addressable = patient_population * diagnosis_rate * treatment_rate
    peak_patients = addressable * market_share_peak
    peak_sales = peak_patients * annual_price
    
    return {
        "patient_population": patient_population,
        "addressable_patients": addressable,
        "peak_patients": peak_patients,
        "peak_sales": peak_sales,
        "annual_price": annual_price,
        "market_share_peak": market_share_peak,
        "methodology": "EPIDEMIOLOGY_CALC",
        "confidence": 0.5
    }


# =============================================================================
# ODIN INTEGRATION
# =============================================================================

def integrate_with_odin(
    odin_tier: str,
    revenue_analysis: RevenueAnalysis,
    base_position: float = 10000.0
) -> dict:
    """
    Integrate revenue analysis with ODIN approval tier for position sizing.
    
    Args:
        odin_tier: ODIN approval tier (TIER_1 to TIER_4)
        revenue_analysis: RevenueAnalysis object
        base_position: Base position size in USD
    
    Returns:
        dict with final position, risk flags, recommendation
    """
    # ODIN tier multipliers
    odin_mults = {
        "TIER_1": 1.0,
        "TIER_2": 0.8,
        "TIER_3": 0.5,
        "TIER_4": 0.0  # HARD AVOID
    }
    
    odin_mult = odin_mults.get(odin_tier, 0.5)
    rev_mult = revenue_analysis.position_multiplier
    
    # Combined multiplier
    combined = odin_mult * rev_mult
    
    # Risk flags
    rev_tier = revenue_analysis.revenue_tier.value
    
    if rev_tier == "R1" and odin_tier in ["TIER_3", "TIER_4"]:
        combined *= 0.5  # Extra caution
        risk_flag = "HIGH_RISK_MISMATCH"
        recommendation = "REDUCE or AVOID - High revenue impact but low approval confidence"
    elif rev_tier == "R1" and odin_tier == "TIER_1":
        combined *= 1.2
        risk_flag = "OPTIMAL_OPPORTUNITY"
        recommendation = "MAXIMIZE - High revenue impact with high approval confidence"
    elif odin_tier == "TIER_4":
        risk_flag = "HARD_AVOID"
        recommendation = "DO NOT TRADE - ODIN TIER_4 is hard avoid regardless of revenue"
        combined = 0.0
    else:
        risk_flag = "STANDARD"
        recommendation = "PROCEED with standard sizing"
    
    final_position = base_position * combined
    
    # Expected value calculation
    approval_probs = {"TIER_1": 0.96, "TIER_2": 0.85, "TIER_3": 0.70, "TIER_4": 0.40}
    prob = approval_probs.get(odin_tier, 0.5)
    
    move_up = revenue_analysis.get_expected_move("APPROVAL")
    move_down = revenue_analysis.get_expected_move("CRL")
    
    expected_value = prob * move_up[0] + (1 - prob) * move_down[1]
    
    return {
        "ticker": revenue_analysis.ticker,
        "asset": revenue_analysis.asset,
        "pdufa_date": revenue_analysis.pdufa_date,
        "odin_tier": odin_tier,
        "revenue_tier": rev_tier,
        "base_position": base_position,
        "odin_multiplier": odin_mult,
        "revenue_multiplier": rev_mult,
        "combined_multiplier": round(combined, 3),
        "final_position": round(final_position, 2),
        "risk_flag": risk_flag,
        "recommendation": recommendation,
        "approval_probability": prob,
        "expected_value_pct": round(expected_value * 100, 1),
        "expected_move_approval": f"+{move_up[0]*100:.0f}% to +{move_up[1]*100:.0f}%",
        "expected_move_crl": f"{move_down[0]*100:.0f}% to {move_down[1]*100:.0f}%"
    }


# =============================================================================
# VALIDATION TARGETS
# =============================================================================

VALIDATION_TARGETS = [
    {
        "ticker": "IRON",
        "company": "Disc Medicine",
        "asset": "bitopertin",
        "indication": "EPP",
        "pdufa_date": "2026-02-15",
        "therapeutic_area": "Rare Disease",
        "comparable_key": "EPP",
        "notes": "Orphan drug for erythropoietic protoporphyria"
    },
    {
        "ticker": "VNDA",
        "company": "Vanda Pharmaceuticals",
        "asset": "tradipitant",
        "indication": "Gastroparesis",
        "pdufa_date": "2026-02-28",
        "therapeutic_area": "GI/Hepatology",
        "comparable_key": "GASTROPARESIS",
        "notes": "First-in-class for gastroparesis (no approved drugs)"
    },
    {
        "ticker": "RCKT",
        "company": "Rocket Pharmaceuticals",
        "asset": "RP-A501",
        "indication": "Danon Disease",
        "pdufa_date": "2026-03-28",
        "therapeutic_area": "Rare Disease",
        "comparable_key": "DANON",
        "notes": "Gene therapy, ~300 US patients, $2M+ pricing expected"
    },
    {
        "ticker": "DNLI",
        "company": "Denali Therapeutics",
        "asset": "DNL310",
        "indication": "Hunter Syndrome (MPS II)",
        "pdufa_date": "2026-04-05",
        "therapeutic_area": "Rare Disease",
        "comparable_key": "HUNTER_MPS2",
        "notes": "Competing with Elaprase ($700M peak sales)"
    }
]


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Test module with sample data."""
    print("=" * 70)
    print("ODIN S24 REVENUE IMPACT MODULE - TEST")
    print("=" * 70)
    
    # Test case: Small biotech with transformational drug
    test_analysis = RevenueAnalysis(
        ticker="IRON",
        asset="bitopertin",
        indication="EPP",
        pdufa_date="2026-02-15",
        peak_sales_estimate=200_000_000,  # $200M (placeholder)
        market_cap=500_000_000,  # $500M (placeholder)
        estimation_method="COMPARABLE_DRUG",
        estimation_confidence=0.6,
        is_first_in_class=False,
        is_orphan=True,
        unmet_need_level="HIGH",
        competitive_landscape="CLEAR"
    )
    
    print("\n--- Test Case: IRON (bitopertin) ---")
    print(json.dumps(test_analysis.to_dict(), indent=2))
    
    # Test ODIN integration
    print("\n--- ODIN Integration (TIER_2 scenario) ---")
    integration = integrate_with_odin("TIER_2", test_analysis, base_position=10000)
    print(json.dumps(integration, indent=2))
    
    # Test comparable lookup
    print("\n--- Comparable Drug Lookup: GASTROPARESIS ---")
    comp = get_comparable_estimate("GASTROPARESIS", {"first_in_class": True})
    print(json.dumps(comp, indent=2))
    
    print("\n" + "=" * 70)
    print("MODULE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
