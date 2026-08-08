#!/usr/bin/env python3
"""
ODIN Position Sizer v3.0
========================
Kelly Criterion-based position sizing with ODIN integration

Features:
- Kelly Criterion calculation using ODIN approval probabilities
- Fractional Kelly (0.25x) for safety
- Position modifiers based on:
  - CMC/Manufacturing risk
  - Cheapness score
  - Prior CRL history
  - Therapeutic area complexity
  - Liquidity conditions

Usage:
    sizer = PositionSizer(portfolio_value=100000)
    result = sizer.calculate(
        ticker="RCKT",
        approval_prob=0.71,
        expected_return=3.0,
        mfg_risk_score=0.0,
        cheapness_score=85,
        prior_crl=True
    )
    print(result['dollar_amount'])  # How much to allocate
"""

import json
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class RiskLevel(Enum):
    CONSERVATIVE = 0.20  # 20% of Kelly
    MODERATE = 0.25      # 25% of Kelly (default)
    AGGRESSIVE = 0.35    # 35% of Kelly


@dataclass
class PositionResult:
    """Position sizing result"""
    ticker: str
    portfolio_value: float
    
    # Kelly calculation
    raw_kelly_fraction: float
    fractional_kelly: float
    risk_level: RiskLevel
    
    # Modifiers applied
    cmc_modifier: float
    cheapness_modifier: float
    prior_crl_modifier: float
    therapeutic_modifier: float
    liquidity_modifier: float
    
    # Final allocation
    combined_modifier: float
    final_allocation_pct: float
    dollar_amount: float
    max_contracts: int
    
    # Risk limits
    max_loss_dollar: float
    max_loss_pct: float
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "portfolio_value": self.portfolio_value,
            "kelly": {
                "raw_fraction": round(self.raw_kelly_fraction, 4),
                "fractional_kelly": round(self.fractional_kelly, 4),
                "risk_level": self.risk_level.name
            },
            "modifiers": {
                "cmc": self.cmc_modifier,
                "cheapness": self.cheapness_modifier,
                "prior_crl": self.prior_crl_modifier,
                "therapeutic": self.therapeutic_modifier,
                "liquidity": self.liquidity_modifier,
                "combined": round(self.combined_modifier, 2)
            },
            "allocation": {
                "percentage": round(self.final_allocation_pct * 100, 2),
                "dollar_amount": round(self.dollar_amount, 2),
                "max_contracts": self.max_contracts
            },
            "risk_limits": {
                "max_loss_dollar": round(self.max_loss_dollar, 2),
                "max_loss_pct": round(self.max_loss_pct * 100, 2)
            }
        }


class PositionSizer:
    """
    ODIN Position Sizer
    
    Calculates position size using Kelly Criterion with safety modifiers.
    Integrates ODIN approval probabilities for optimal sizing.
    """
    
    # Therapeutic area complexity multipliers
    THERAPEUTIC_MODIFIERS = {
        "default": 1.0,
        "oncology": 0.9,           # High competition, complex endpoints
        "rare_disease": 1.0,       # Regulatory support, clear endpoints
        "gene_therapy": 0.6,       # Manufacturing complexity, novel
        "cell_therapy": 0.6,       # Manufacturing complexity
        "cns": 0.7,                # High failure rate historically
        "pain": 0.5,               # Very high failure rate, abuse liability
        "cardiovascular": 0.85,    # Large trials, clear endpoints
        "infectious_disease": 0.9, # Variable, depends on pathogen
        "metabolic": 0.9,          # Generally well-understood
        "respiratory": 0.85,       # Clear endpoints
        "ophthalmology": 0.95,     # Small trials, clear endpoints
    }
    
    # Default expected returns by outcome
    DEFAULT_RETURNS = {
        "win": 3.0,   # +300% expected on approval
        "loss": -0.5  # -50% expected on CRL (options)
    }
    
    def __init__(self, portfolio_value: float, 
                 risk_level: RiskLevel = RiskLevel.MODERATE,
                 max_single_position_pct: float = 0.15,
                 monthly_loss_limit_pct: float = 0.05):
        """
        Initialize position sizer
        
        Args:
            portfolio_value: Total portfolio value
            risk_level: Conservative/Moderate/Aggressive Kelly fraction
            max_single_position_pct: Maximum single position (default 15%)
            monthly_loss_limit_pct: Monthly drawdown limit (default 5%)
        """
        self.portfolio_value = portfolio_value
        self.risk_level = risk_level
        self.max_single_position = max_single_position_pct
        self.monthly_loss_limit = monthly_loss_limit_pct
    
    def calculate(self, 
                  ticker: str,
                  approval_prob: float,
                  expected_return: float = None,
                  mfg_risk_score: float = 0.0,
                  cheapness_score: int = 50,
                  prior_crl: bool = False,
                  therapeutic_area: str = "default",
                  bid_ask_spread_pct: float = 0.02,
                  option_price: float = 1.50) -> PositionResult:
        """
        Calculate position size for a trade
        
        Args:
            ticker: Stock symbol
            approval_prob: ODIN approval probability (0-1)
            expected_return: Expected return multiple if win (default 3.0)
            mfg_risk_score: Manufacturing/CMC risk (0-1)
            cheapness_score: Cheapness analysis score (0-100)
            prior_crl: Whether drug has prior CRL history
            therapeutic_area: For complexity modifier
            bid_ask_spread_pct: Current bid-ask spread
            option_price: Price per contract for contract calculation
            
        Returns:
            PositionResult with sizing details
        """
        if expected_return is None:
            expected_return = self.DEFAULT_RETURNS["win"]
        
        # Step 1: Calculate raw Kelly fraction
        raw_kelly = self._kelly_criterion(
            win_prob=approval_prob,
            win_return=expected_return,
            loss_return=self.DEFAULT_RETURNS["loss"]
        )
        
        # Step 2: Apply fractional Kelly (safety)
        fractional_kelly = raw_kelly * self.risk_level.value
        
        # Step 3: Calculate modifiers
        cmc_mod = self._cmc_modifier(mfg_risk_score)
        cheap_mod = self._cheapness_modifier(cheapness_score)
        crl_mod = self._prior_crl_modifier(prior_crl)
        ther_mod = self._therapeutic_modifier(therapeutic_area)
        liq_mod = self._liquidity_modifier(bid_ask_spread_pct)
        
        # Step 4: Combine modifiers (multiplicative)
        combined = cmc_mod * cheap_mod * crl_mod * ther_mod * liq_mod
        
        # Step 5: Calculate final allocation
        final_pct = fractional_kelly * combined
        
        # Step 6: Apply caps
        final_pct = min(final_pct, self.max_single_position)
        final_pct = max(final_pct, 0.005)  # Minimum 0.5%
        
        # Step 7: Calculate dollar amount and contracts
        dollar_amount = self.portfolio_value * final_pct
        max_contracts = int(dollar_amount / (option_price * 100))
        
        # Step 8: Risk limits
        max_loss = dollar_amount  # Options can go to zero
        max_loss_pct = max_loss / self.portfolio_value
        
        return PositionResult(
            ticker=ticker,
            portfolio_value=self.portfolio_value,
            raw_kelly_fraction=raw_kelly,
            fractional_kelly=fractional_kelly,
            risk_level=self.risk_level,
            cmc_modifier=cmc_mod,
            cheapness_modifier=cheap_mod,
            prior_crl_modifier=crl_mod,
            therapeutic_modifier=ther_mod,
            liquidity_modifier=liq_mod,
            combined_modifier=combined,
            final_allocation_pct=final_pct,
            dollar_amount=dollar_amount,
            max_contracts=max_contracts,
            max_loss_dollar=max_loss,
            max_loss_pct=max_loss_pct
        )
    
    def _kelly_criterion(self, win_prob: float, 
                         win_return: float, 
                         loss_return: float) -> float:
        """
        Kelly Criterion formula
        
        f* = (b*p - q) / b
        
        Where:
            f* = fraction of capital to risk
            b = net odds (win_return as multiple)
            p = probability of winning
            q = probability of losing (1-p)
        """
        p = win_prob
        q = 1 - p
        b = win_return
        
        # Handle edge cases
        if b <= 0:
            return 0.0
        
        kelly = (b * p - q) / b
        
        # Kelly can be negative if edge is negative
        return max(kelly, 0.0)
    
    def _cmc_modifier(self, mfg_risk_score: float) -> float:
        """
        CMC/Manufacturing risk modifier
        
        74% of CRLs are CMC-related, so this is critical.
        """
        if mfg_risk_score <= 0.15:
            return 1.0   # Low risk - full allocation
        elif mfg_risk_score <= 0.25:
            return 0.85  # Moderate risk
        elif mfg_risk_score <= 0.40:
            return 0.70  # Elevated risk
        elif mfg_risk_score <= 0.50:
            return 0.50  # High risk - half size
        else:
            return 0.25  # Extreme risk - quarter size
    
    def _cheapness_modifier(self, cheapness_score: int) -> float:
        """
        Cheapness score modifier
        
        Higher score = better entry timing = larger position
        """
        if cheapness_score >= 80:
            return 1.20  # Exceptional entry - 20% larger
        elif cheapness_score >= 70:
            return 1.10  # Great entry
        elif cheapness_score >= 60:
            return 1.00  # Good entry - full size
        elif cheapness_score >= 50:
            return 0.85  # Fair entry
        elif cheapness_score >= 40:
            return 0.70  # Weak entry
        else:
            return 0.50  # Poor entry - half size
    
    def _prior_crl_modifier(self, prior_crl: bool) -> float:
        """
        Prior CRL history modifier
        
        Prior CRLs increase uncertainty even if resolved.
        """
        if prior_crl:
            return 0.80  # 20% reduction for prior CRL
        return 1.0
    
    def _therapeutic_modifier(self, therapeutic_area: str) -> float:
        """
        Therapeutic area complexity modifier
        
        Some areas have structurally higher failure rates.
        """
        return self.THERAPEUTIC_MODIFIERS.get(
            therapeutic_area.lower(), 
            self.THERAPEUTIC_MODIFIERS["default"]
        )
    
    def _liquidity_modifier(self, bid_ask_spread_pct: float) -> float:
        """
        Liquidity modifier based on bid-ask spread
        
        Wide spreads = difficult exits = smaller positions
        """
        if bid_ask_spread_pct <= 0.02:
            return 1.0   # Tight spread - full size
        elif bid_ask_spread_pct <= 0.03:
            return 0.90  # Moderate spread
        elif bid_ask_spread_pct <= 0.05:
            return 0.75  # Wide spread
        else:
            return 0.50  # Very wide - half size or skip
    
    def check_portfolio_limits(self, positions: list) -> Dict:
        """
        Check if proposed positions fit within portfolio limits
        
        Args:
            positions: List of PositionResult objects
            
        Returns:
            Dict with limit status and warnings
        """
        total_allocation = sum(p.final_allocation_pct for p in positions)
        total_dollars = sum(p.dollar_amount for p in positions)
        max_potential_loss = sum(p.max_loss_dollar for p in positions)
        
        warnings = []
        
        # Check total allocation
        if total_allocation > 0.50:
            warnings.append(f"Total allocation ({total_allocation:.0%}) exceeds 50% limit")
        
        # Check concentration
        largest_position = max(p.final_allocation_pct for p in positions)
        if largest_position > self.max_single_position:
            warnings.append(f"Largest position ({largest_position:.0%}) exceeds {self.max_single_position:.0%} limit")
        
        # Check monthly loss limit
        max_loss_pct = max_potential_loss / self.portfolio_value
        if max_loss_pct > self.monthly_loss_limit:
            warnings.append(f"Max potential loss ({max_loss_pct:.0%}) exceeds monthly limit ({self.monthly_loss_limit:.0%})")
        
        return {
            "within_limits": len(warnings) == 0,
            "total_allocation_pct": round(total_allocation * 100, 1),
            "total_dollars": round(total_dollars, 2),
            "max_potential_loss_pct": round(max_loss_pct * 100, 1),
            "position_count": len(positions),
            "warnings": warnings
        }


# ==================== APPROVAL-WEIGHTED VOLATILITY ====================

def calculate_adjusted_volatility(raw_event_vol: float, 
                                   approval_prob: float) -> Dict:
    """
    ODIN-adjusted event volatility
    
    Standard volatility trading assumes 50/50 odds.
    ODIN provides actual probabilities, so we adjust.
    
    Formula:
        σ_adjusted = σ_raw × √[2 × p × (1-p)]
    
    Args:
        raw_event_vol: Event volatility from IV term structure (decimal)
        approval_prob: ODIN approval probability (0-1)
        
    Returns:
        Dict with raw, adjusted vol, and interpretation
    """
    import math
    
    p = approval_prob
    adjustment_factor = math.sqrt(2 * p * (1 - p))
    adjusted_vol = raw_event_vol * adjustment_factor
    
    ratio = raw_event_vol / adjusted_vol if adjusted_vol > 0 else 1.0
    
    # Interpretation
    if ratio > 1.3:
        signal = "UNDERPRICED"
        action = "BUY"
        detail = f"Market pricing {raw_event_vol*100:.0f}% but only {adjusted_vol*100:.0f}% needed"
    elif ratio > 1.1:
        signal = "FAIR"
        action = "TACTICAL"
        detail = f"Market fairly pricing event volatility"
    else:
        signal = "OVERPRICED"
        action = "SKIP"
        detail = f"Market overpricing volatility; IV crush risk"
    
    return {
        "raw_event_vol": round(raw_event_vol, 3),
        "adjusted_event_vol": round(adjusted_vol, 3),
        "adjustment_factor": round(adjustment_factor, 3),
        "raw_to_adjusted_ratio": round(ratio, 2),
        "signal": signal,
        "action": action,
        "detail": detail
    }


# ==================== QUICK SIZING FUNCTION ====================

def quick_position_size(ticker: str,
                        portfolio_value: float,
                        approval_prob: float,
                        mfg_risk_score: float = 0.0,
                        cheapness_score: int = 50,
                        therapeutic_area: str = "default") -> Dict:
    """
    Quick position sizing for a single trade
    
    Args:
        ticker: Stock symbol
        portfolio_value: Total portfolio value
        approval_prob: ODIN approval probability
        mfg_risk_score: CMC risk (0-1)
        cheapness_score: Entry timing score (0-100)
        therapeutic_area: For complexity adjustment
        
    Returns:
        Dict with position sizing
    """
    sizer = PositionSizer(portfolio_value)
    result = sizer.calculate(
        ticker=ticker,
        approval_prob=approval_prob,
        mfg_risk_score=mfg_risk_score,
        cheapness_score=cheapness_score,
        therapeutic_area=therapeutic_area
    )
    return result.to_dict()


# ==================== MAIN ====================

if __name__ == "__main__":
    print("ODIN Position Sizer v3.0")
    print("=" * 50)
    
    # Example: $100K portfolio
    portfolio = 100000
    sizer = PositionSizer(portfolio)
    
    # Test cases
    test_cases = [
        {
            "ticker": "RCKT",
            "approval_prob": 0.71,
            "mfg_risk_score": 0.0,
            "cheapness_score": 85,
            "prior_crl": True,
            "therapeutic_area": "gene_therapy"
        },
        {
            "ticker": "DNLI",
            "approval_prob": 0.84,
            "mfg_risk_score": 0.15,
            "cheapness_score": 72,
            "prior_crl": False,
            "therapeutic_area": "rare_disease"
        },
        {
            "ticker": "TVTX",
            "approval_prob": 0.65,
            "mfg_risk_score": 0.10,
            "cheapness_score": 60,
            "prior_crl": False,
            "therapeutic_area": "default"
        }
    ]
    
    positions = []
    
    for tc in test_cases:
        result = sizer.calculate(**tc)
        positions.append(result)
        
        print(f"\n{tc['ticker']} Position Sizing:")
        print(f"  ODIN Approval Prob: {tc['approval_prob']*100:.0f}%")
        print(f"  Raw Kelly: {result.raw_kelly_fraction*100:.1f}%")
        print(f"  Fractional Kelly: {result.fractional_kelly*100:.1f}%")
        print(f"  Modifiers:")
        print(f"    CMC: {result.cmc_modifier:.2f}")
        print(f"    Cheapness: {result.cheapness_modifier:.2f}")
        print(f"    Prior CRL: {result.prior_crl_modifier:.2f}")
        print(f"    Therapeutic: {result.therapeutic_modifier:.2f}")
        print(f"    Combined: {result.combined_modifier:.2f}")
        print(f"  Final Allocation: {result.final_allocation_pct*100:.1f}%")
        print(f"  Dollar Amount: ${result.dollar_amount:,.0f}")
        print(f"  Max Contracts: {result.max_contracts}")
    
    print("\n" + "=" * 50)
    print("Portfolio Limits Check:")
    limits = sizer.check_portfolio_limits(positions)
    print(f"  Total Allocation: {limits['total_allocation_pct']}%")
    print(f"  Total Dollars: ${limits['total_dollars']:,.0f}")
    print(f"  Max Potential Loss: {limits['max_potential_loss_pct']}%")
    print(f"  Within Limits: {limits['within_limits']}")
    if limits['warnings']:
        print(f"  Warnings: {limits['warnings']}")
    
    print("\n" + "=" * 50)
    print("Volatility Adjustment Example (RCKT):")
    vol_adj = calculate_adjusted_volatility(
        raw_event_vol=1.15,  # 115% event vol from term structure
        approval_prob=0.71   # ODIN says 71% approval
    )
    print(f"  Raw Event Vol: {vol_adj['raw_event_vol']*100:.0f}%")
    print(f"  Adjusted Vol: {vol_adj['adjusted_event_vol']*100:.0f}%")
    print(f"  Ratio: {vol_adj['raw_to_adjusted_ratio']}x")
    print(f"  Signal: {vol_adj['signal']} → {vol_adj['action']}")
    print(f"  Detail: {vol_adj['detail']}")
