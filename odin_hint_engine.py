#!/usr/bin/env python3
"""
ODIN/HINT Dual Prediction Engine
=================================
Combines two complementary prediction approaches for FDA PDUFA outcomes:

ODIN (Outcome Determination Intelligence Network):
  - Regulatory designation signals (BTD, Orphan, Priority Review, etc.)
  - Sponsor experience and manufacturing complexity
  - AdCom vote outcomes
  
HINT (Historical INdication Tracking):
  - Therapeutic area historical CRL rates
  - Indication-specific difficulty adjustments
  - Era-weighted historical baselines

Ensemble modes:
  - ODIN_ONLY: Pure designation-based scoring
  - HINT_ONLY: Pure indication difficulty
  - WEIGHTED: Configurable blend (default 70% ODIN, 30% HINT)
  - OVERRIDE: HINT dominates for high-risk TAs, ODIN otherwise

Usage:
  from odin_hint_engine import OdinHintEngine
  
  engine = OdinHintEngine()
  result = engine.predict(event_dict)
  batch_results = engine.predict_batch(dataframe)
"""

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

class EnsembleMode(Enum):
    ODIN_ONLY = "odin_only"
    HINT_ONLY = "hint_only"
    WEIGHTED = "weighted"
    OVERRIDE = "override"  # HINT for high-risk TAs, ODIN otherwise

class RiskTier(Enum):
    TIER_1 = "TIER_1"  # High confidence approval
    TIER_2 = "TIER_2"  # Likely approval
    TIER_3 = "TIER_3"  # Uncertain
    TIER_4 = "TIER_4"  # Elevated CRL risk

# =============================================================================
# HINT: Historical Indication Tracking
# =============================================================================

# CRL rates by therapeutic area (from 1,350-record T-1 compliant dataset)
HINT_TA_CRL_RATES = {
    # HIGH RISK (CRL > 25%)
    "Pain Management": 0.419,      # 41.9% CRL - HIGHEST RISK
    "Hematology": 0.357,           # 35.7% CRL
    "Nephrology": 0.310,           # 31.0% CRL
    "Ophthalmology": 0.265,        # 26.5% CRL
    
    # MODERATE RISK (CRL 15-25%)
    "CNS/Neurology": 0.232,        # 23.2% CRL
    "Cardiovascular": 0.214,       # 21.4% CRL
    "Metabolic/Endocrine": 0.200,  # 20.0% CRL
    "Rare Disease": 0.176,         # 17.6% CRL
    "Other": 0.152,                # 15.2% CRL
    
    # LOW RISK (CRL < 15%)
    "Immunology": 0.118,           # 11.8% CRL
    "Dermatology": 0.105,          # 10.5% CRL
    "Psychiatry": 0.100,           # 10.0% CRL (estimated)
    "Oncology": 0.072,             # 7.2% CRL
    "GI/Hepatology": 0.067,        # 6.7% CRL
    "Respiratory": 0.043,          # 4.3% CRL
    "Infectious Disease": 0.030,   # 3.0% CRL
    "Women's Health": 0.000,       # 0% CRL (small n)
    "Vaccines": 0.000,             # 0% CRL
}

HINT_TA_RISK_TIERS = {
    "HIGH_RISK": ["Pain Management", "Hematology", "Nephrology", "Ophthalmology"],
    "MOD_RISK": ["CNS/Neurology", "Cardiovascular", "Metabolic/Endocrine", "Rare Disease", "Other"],
    "LOW_RISK": ["Immunology", "Dermatology", "Psychiatry", "Oncology", "GI/Hepatology", 
                 "Respiratory", "Infectious Disease", "Women's Health", "Vaccines"]
}

# Modality CRL rates
HINT_MODALITY_CRL_RATES = {
    "Small Molecule": 0.151,       # 15.1% CRL - baseline
    "Antibody": 0.119,             # 11.9% CRL
    "Peptide": 0.120,              # 12.0% CRL
    "ADC": 0.100,                  # 10.0% CRL (limited data)
    "Cell/Gene Therapy": 0.070,    # 7.0% CRL (but high mfg risk)
    "RNA Therapy": 0.073,          # 7.3% CRL
    "Vaccine": 0.000,              # 0% CRL
}

# Era adjustments (FDA has become more lenient)
HINT_ERA_ADJUSTMENTS = {
    "pre_2015": 0.05,    # +5% CRL risk
    "2015_2019": 0.02,   # +2% CRL risk
    "2020_plus": 0.00,   # baseline (current era)
}

# HIGH-RISK INDICATIONS (granular indication-level patterns)
# These override TA-level estimates when matched
HINT_HIGH_RISK_INDICATIONS = {
    # 100% CRL in dataset - automatic TIER_4
    "Postoperative pain following bunionectomy surgery": 1.00,
    "Postoperative pain": 0.80,  # Generalized
    
    # >40% CRL
    "Inflammatory diseases": 0.75,
    "Parkinson's disease": 0.50,
    "Major depressive disorder (MDD)": 0.40,
    "Chronic spontaneous urticaria (CSU)": 0.40,
    "Migraine": 0.40,
    
    # 30-40% CRL
    "Dry eye disease": 0.33,
    "Hypercholesterolemia": 0.33,
    "Schizophrenia": 0.29,
}

# TA + MODALITY interaction adjustments (additive to base TA rate)
HINT_TA_MODALITY_INTERACTIONS = {
    ("Pain Management", "Small Molecule"): 0.014,      # 43.3% vs 41.9% base
    ("Hematology", "Small Molecule"): 0.027,           # 38.5% vs 35.7% base
    ("Metabolic/Endocrine", "Small Molecule"): 0.078,  # 27.8% vs 20.0% base
    ("Ophthalmology", "Antibody"): 0.035,              # 30.0% vs 26.5% base
    ("Other", "Cell/Gene Therapy"): 0.048,             # 20.0% vs 15.2% base
    # Favorable combinations
    ("Oncology", "Antibody"): -0.020,                  # Lower than base
    ("Infectious Disease", "Vaccine"): -0.030,         # Very favorable
}

# SPONSOR EXPERIENCE + TA interaction (multiplicative risk factors)
# novice = 1-2 approvals, expert = 5+
HINT_SPONSOR_TA_INTERACTIONS = {
    # Dangerous combinations (novice + high-risk TA)
    ("novice", "Pain Management"): 0.433,    # vs 41.9% base
    ("novice", "Nephrology"): 0.421,         # vs 31.0% base
    ("novice", "Hematology"): 0.357,         # same as base (already high)
    ("novice", "CNS/Neurology"): 0.292,      # vs 23.2% base
    ("novice", "Ophthalmology"): 0.286,      # vs 26.5% base
    ("novice", "Cardiovascular"): 0.235,     # vs 21.4% base
    ("novice", "Rare Disease"): 0.233,       # vs 17.6% base
    ("novice", "Immunology"): 0.231,         # vs 11.8% base
    
    # Expert sponsors in risky areas (still elevated but better)
    ("expert", "Ophthalmology"): 0.231,      # vs 26.5% base (better)
    ("expert", "Metabolic/Endocrine"): 0.200, # same as base
}

# =============================================================================
# ODIN: Designation-based Scoring
# =============================================================================

# Default ODIN weights (from v6 optimization on clean dataset)
# These will be overridden if champion_config.json is loaded
DEFAULT_ODIN_WEIGHTS = {
    "btd": 0.40,              # 4.9% CRL when present
    "orphan": -0.15,          # Suppressor variable (correlated with other designations)
    "priority_review": 0.15,  # 9.5% CRL when present
    "accelerated_approval": 0.35,  # 6.5% CRL when present
    "had_adcom": 0.20,        # Very rare, usually positive
    "adcom_vote_pct": 0.01,   # Per percentage point
    "sponsor_experienced": 0.50,   # 7.2% CRL vs 19% for novice
    "sponsor_low_exp": -0.45,      # 19% CRL
    "high_risk_ta": -0.70,         # 27.2% CRL
    "low_risk_ta": 0.55,           # 6.2% CRL
    "modality_complexity": -0.05,  # Small negative per level
}

DEFAULT_ODIN_BIAS = 1.875  # Calibrated for 86.7% base rate

ODIN_FEATURES = [
    "btd", "orphan", "priority_review", "accelerated_approval",
    "had_adcom", "adcom_vote_pct",
    "sponsor_experienced", "sponsor_low_exp",
    "high_risk_ta", "low_risk_ta", "modality_complexity"
]

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PredictionResult:
    """Result of a single prediction."""
    # Core predictions
    odin_prob: float           # ODIN-only probability
    hint_prob: float           # HINT-only probability
    ensemble_prob: float       # Combined probability
    
    # Classification
    tier: RiskTier
    ta_risk_tier: str          # HIGH_RISK, MOD_RISK, LOW_RISK
    
    # Confidence & metadata
    confidence: str            # HIGH, MEDIUM, LOW
    key_factors: List[str]     # Top contributing factors
    warnings: List[str]        # Any risk flags
    
    # Debug info
    odin_adjustments: Dict[str, float] = field(default_factory=dict)
    hint_adjustments: Dict[str, float] = field(default_factory=dict)


@dataclass 
class EngineConfig:
    """Configuration for the dual engine."""
    # Ensemble settings
    mode: EnsembleMode = EnsembleMode.WEIGHTED
    odin_weight: float = 0.40  # Optimal: 40% ODIN
    hint_weight: float = 0.60  # Optimal: 60% HINT
    
    # Tier thresholds
    tier1_threshold: float = 0.92
    tier2_threshold: float = 0.85
    tier3_threshold: float = 0.70
    
    # Override settings (for OVERRIDE mode)
    override_ta_threshold: float = 0.25  # TAs with CRL > 25% use HINT
    
    # ODIN weights (can be loaded from champion config)
    odin_weights: Dict[str, float] = field(default_factory=lambda: DEFAULT_ODIN_WEIGHTS.copy())
    odin_bias: float = DEFAULT_ODIN_BIAS
    
    # HINT settings
    hint_era_weight: float = 1.0      # How much to apply era adjustments
    hint_modality_weight: float = 0.5  # How much to blend modality signal


# =============================================================================
# MAIN ENGINE
# =============================================================================

class OdinHintEngine:
    """
    Dual ODIN/HINT prediction engine for FDA PDUFA outcomes.
    
    Example:
        engine = OdinHintEngine()
        
        # Single prediction
        event = {
            'btd': True,
            'orphan': True,
            'priority_review': True,
            'therapeutic_area': 'Oncology',
            'modality': 'Antibody',
            'sponsor_prior_approvals': 15,
        }
        result = engine.predict(event)
        print(f"Approval probability: {result.ensemble_prob:.1%}")
        print(f"Tier: {result.tier.value}")
        
        # Batch prediction
        df = pd.read_csv('pdufa_events.csv')
        results_df = engine.predict_batch(df)
    """
    
    def __init__(self, config: Optional[EngineConfig] = None, 
                 champion_path: Optional[str] = None):
        """
        Initialize the engine.
        
        Args:
            config: Engine configuration (uses defaults if None)
            champion_path: Path to champion_config.json from optimizer
        """
        self.config = config or EngineConfig()
        
        # Load champion weights if provided
        if champion_path and Path(champion_path).exists():
            self._load_champion_config(champion_path)
        
        # Pre-compute TA risk mappings
        self._ta_to_risk = {}
        for risk_tier, tas in HINT_TA_RISK_TIERS.items():
            for ta in tas:
                self._ta_to_risk[ta] = risk_tier
    
    def _load_champion_config(self, path: str):
        """Load optimized weights from champion config (supports v6 optimizer format)."""
        with open(path) as f:
            champion = json.load(f)
        
        # Handle v6 optimizer format
        if 'weights' in champion and 'features' in champion:
            weights = dict(zip(champion['features'], champion['weights']))
            self.config.odin_weights = weights
            self.config.odin_bias = champion.get('bias', DEFAULT_ODIN_BIAS)
            best_brier = champion.get('best_brier', champion.get('final_brier', 'N/A'))
            print(f"✓ Loaded v6 champion: Brier={best_brier:.6f if isinstance(best_brier, float) else best_brier}")
        
        # Handle legacy format
        elif 'champion_params' in champion:
            params = champion['champion_params']
            # Map legacy param names to new feature names
            legacy_map = {
                'btd_weight': 'btd',
                'orphan_weight': 'orphan',
                'priority_review_weight': 'priority_review',
                'accelerated_approval_weight': 'accelerated_approval',
                'adcom_high_boost': 'had_adcom',  # Simplified mapping
            }
            for legacy_name, new_name in legacy_map.items():
                if legacy_name in params:
                    self.config.odin_weights[new_name] = params[legacy_name]
            print(f"✓ Loaded legacy champion config")
        
        else:
            print(f"⚠ Unknown config format in {path}")
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any warnings."""
        warnings = []
        
        # Check weight sum
        if abs(self.config.odin_weight + self.config.hint_weight - 1.0) > 0.01:
            warnings.append(f"Weights don't sum to 1.0: {self.config.odin_weight} + {self.config.hint_weight}")
        
        # Check bias calibration
        expected_base_prob = 1 / (1 + np.exp(-self.config.odin_bias))
        if abs(expected_base_prob - 0.867) > 0.05:
            warnings.append(f"Bias gives base rate {expected_base_prob:.1%}, expected ~86.7%")
        
        # Check for missing weights
        for feature in ODIN_FEATURES:
            if feature not in self.config.odin_weights:
                warnings.append(f"Missing weight for feature: {feature}")
        
        return warnings
    
    def _engineer_features(self, event: dict) -> dict:
        """Add derived features to event."""
        event = event.copy()
        
        # Sponsor experience
        prior_approvals = event.get('sponsor_prior_approvals', 0)
        event['sponsor_experienced'] = 1.0 if prior_approvals >= 5 else 0.0
        event['sponsor_low_exp'] = 1.0 if prior_approvals < 3 else 0.0
        
        # TA risk tiers
        ta = event.get('therapeutic_area', 'Other')
        event['high_risk_ta'] = 1.0 if ta in HINT_TA_RISK_TIERS['HIGH_RISK'] else 0.0
        event['low_risk_ta'] = 1.0 if ta in HINT_TA_RISK_TIERS['LOW_RISK'] else 0.0
        
        # Modality complexity
        modality = event.get('modality', 'Small Molecule')
        modality_map = {
            'Small Molecule': 0, 'Vaccine': 0,
            'Antibody': 1, 'Peptide': 1,
            'ADC': 2, 'RNA Therapy': 3,
            'Cell/Gene Therapy': 4
        }
        event['modality_complexity'] = modality_map.get(modality, 0)
        
        return event
    
    def _score_odin(self, event: dict) -> Tuple[float, Dict[str, float]]:
        """
        Calculate ODIN probability using designation-based scoring.
        
        Returns:
            Tuple of (probability, adjustments_dict)
        """
        event = self._engineer_features(event)
        adjustments = {}
        
        # Build feature vector
        logit = self.config.odin_bias
        
        for feature in ODIN_FEATURES:
            raw_value = event.get(feature, 0)
            
            # Handle NaN/None values
            if raw_value is None or (isinstance(raw_value, float) and np.isnan(raw_value)):
                value = 0.0
            else:
                value = float(raw_value)
            
            weight = self.config.odin_weights.get(feature, 0)
            
            if value != 0 and weight != 0:
                contribution = value * weight
                logit += contribution
                adjustments[feature] = contribution
        
        # Sigmoid with NaN check
        if np.isnan(logit):
            logit = self.config.odin_bias  # Fallback to base rate
            
        prob = 1 / (1 + np.exp(-np.clip(logit, -500, 500)))
        
        return float(prob), adjustments
    
    def _score_hint(self, event: dict) -> Tuple[float, Dict[str, float]]:
        """
        Calculate HINT probability using hierarchical historical patterns.
        
        Hierarchy:
        1. Specific indication (if in high-risk list)
        2. Sponsor + TA interaction (if available)
        3. TA + Modality interaction
        4. Base TA rate
        
        Returns:
            Tuple of (probability, adjustments_dict)
        """
        adjustments = {}
        
        # Get event attributes
        indication = event.get('indication', '')
        ta = event.get('therapeutic_area', 'Other')
        modality = event.get('modality', 'Small Molecule')
        year = event.get('year', 2024)
        prior_approvals = event.get('sponsor_prior_approvals', 0)
        
        # Determine sponsor tier
        if prior_approvals >= 5:
            sponsor_tier = 'expert'
        elif prior_approvals >= 3:
            sponsor_tier = 'mid'
        else:
            sponsor_tier = 'novice'
        
        # === HIERARCHICAL CRL RATE LOOKUP ===
        
        # Level 1: Check high-risk indication (most specific)
        indication_crl = None
        for ind_pattern, crl_rate in HINT_HIGH_RISK_INDICATIONS.items():
            if ind_pattern.lower() in indication.lower():
                indication_crl = crl_rate
                adjustments['indication_match'] = ind_pattern
                adjustments['indication_crl'] = crl_rate
                break
        
        # Level 2: Sponsor + TA interaction
        sponsor_ta_key = (sponsor_tier, ta)
        sponsor_ta_crl = HINT_SPONSOR_TA_INTERACTIONS.get(sponsor_ta_key)
        if sponsor_ta_crl is not None:
            adjustments['sponsor_ta_interaction'] = sponsor_ta_crl
        
        # Level 3: TA + Modality interaction
        ta_mod_key = (ta, modality)
        ta_mod_adj = HINT_TA_MODALITY_INTERACTIONS.get(ta_mod_key, 0.0)
        if ta_mod_adj != 0:
            adjustments['ta_modality_adj'] = ta_mod_adj
        
        # Level 4: Base TA rate
        base_ta_crl = HINT_TA_CRL_RATES.get(ta, 0.133)
        adjustments['base_ta_crl'] = base_ta_crl
        
        # === COMBINE HIERARCHICALLY ===
        
        if indication_crl is not None:
            # Specific indication overrides everything
            final_crl = indication_crl
            adjustments['crl_source'] = 'indication'
        elif sponsor_ta_crl is not None:
            # Sponsor + TA interaction (already accounts for TA base)
            final_crl = sponsor_ta_crl + ta_mod_adj
            adjustments['crl_source'] = 'sponsor_ta'
        else:
            # Base TA + modality adjustment
            final_crl = base_ta_crl + ta_mod_adj
            adjustments['crl_source'] = 'ta_modality'
        
        # Era adjustment (always applies)
        if year < 2015:
            era_adj = HINT_ERA_ADJUSTMENTS['pre_2015']
        elif year < 2020:
            era_adj = HINT_ERA_ADJUSTMENTS['2015_2019']
        else:
            era_adj = HINT_ERA_ADJUSTMENTS['2020_plus']
        era_adj *= self.config.hint_era_weight
        
        if era_adj != 0:
            final_crl += era_adj
            adjustments['era_adj'] = era_adj
        
        # Clamp and convert
        final_crl = np.clip(final_crl, 0.01, 0.99)
        approval_prob = 1.0 - final_crl
        adjustments['final_crl'] = final_crl
        
        return float(approval_prob), adjustments
    
    def _determine_tier(self, prob: float) -> RiskTier:
        """Classify probability into risk tier."""
        if prob >= self.config.tier1_threshold:
            return RiskTier.TIER_1
        elif prob >= self.config.tier2_threshold:
            return RiskTier.TIER_2
        elif prob >= self.config.tier3_threshold:
            return RiskTier.TIER_3
        else:
            return RiskTier.TIER_4
    
    def _get_key_factors(self, odin_adj: dict, hint_adj: dict, event: dict) -> List[str]:
        """Extract top contributing factors for explanation."""
        factors = []
        
        # ODIN factors (designation-based)
        sorted_odin = sorted(odin_adj.items(), key=lambda x: abs(x[1]), reverse=True)
        for feat, val in sorted_odin[:3]:
            if val > 0.1:
                factors.append(f"ODIN {feat}: +{val:.2f} (favorable)")
            elif val < -0.1:
                factors.append(f"ODIN {feat}: {val:.2f} (risk)")
        
        # HINT factors (indication-based)
        crl_source = hint_adj.get('crl_source', 'ta_modality')
        
        if crl_source == 'indication':
            ind_match = hint_adj.get('indication_match', '')
            ind_crl = hint_adj.get('indication_crl', 0)
            factors.insert(0, f"⚠️ HINT: '{ind_match}' = {ind_crl:.0%} historical CRL")
        elif crl_source == 'sponsor_ta':
            sponsor_ta_crl = hint_adj.get('sponsor_ta_interaction', 0)
            factors.append(f"HINT sponsor×TA: {sponsor_ta_crl:.0%} CRL (interaction)")
        
        # General TA insight
        ta = event.get('therapeutic_area', 'Other')
        base_crl = hint_adj.get('base_ta_crl', 0.133)
        final_crl = hint_adj.get('final_crl', base_crl)
        
        if final_crl > 0.30:
            factors.append(f"HINT '{ta}': {final_crl:.0%} CRL (VERY HIGH RISK)")
        elif final_crl > 0.20:
            factors.append(f"HINT '{ta}': {final_crl:.0%} CRL (elevated risk)")
        elif final_crl < 0.08:
            factors.append(f"HINT '{ta}': {final_crl:.0%} CRL (favorable)")
        
        return factors
    
    def _get_warnings(self, event: dict, odin_prob: float, hint_prob: float) -> List[str]:
        """Generate warning flags."""
        warnings = []
        
        # Divergence warning
        if abs(odin_prob - hint_prob) > 0.15:
            if odin_prob > hint_prob:
                warnings.append(f"⚠️ DIVERGENCE: ODIN={odin_prob:.0%} but HINT={hint_prob:.0%} (historical patterns worse)")
            else:
                warnings.append(f"ℹ️ DIVERGENCE: HINT={hint_prob:.0%} but ODIN={odin_prob:.0%} (designations worse)")
        
        # High-risk indication check
        indication = event.get('indication', '')
        for ind_pattern, crl_rate in HINT_HIGH_RISK_INDICATIONS.items():
            if ind_pattern.lower() in indication.lower():
                if crl_rate >= 0.50:
                    warnings.append(f"🚨 HIGH-RISK INDICATION: '{ind_pattern}' has {crl_rate:.0%} historical CRL")
                break
        
        # High-risk TA
        ta = event.get('therapeutic_area', 'Other')
        if ta in HINT_TA_RISK_TIERS['HIGH_RISK']:
            warnings.append(f"⚠️ HIGH RISK TA: {ta} (>25% historical CRL)")
        
        # Novice + high-risk TA combo
        prior_approvals = event.get('sponsor_prior_approvals', 0)
        sponsor_tier = 'novice' if prior_approvals < 3 else ('expert' if prior_approvals >= 5 else 'mid')
        
        if sponsor_tier == 'novice' and ta in HINT_TA_RISK_TIERS['HIGH_RISK']:
            warnings.append(f"🚨 DANGEROUS COMBO: Novice sponsor + {ta} = very high CRL risk")
        
        # Pain Management + Small Molecule (historically worst combo)
        modality = event.get('modality', 'Small Molecule')
        if ta == 'Pain Management' and modality == 'Small Molecule':
            warnings.append("⚠️ Pain Management + Small Molecule: 43% historical CRL rate")
        
        # Prior CRL
        if event.get('prior_crl'):
            warnings.append("Prior CRL on record")
        
        # Manufacturing signals
        if event.get('form_483_issues'):
            warnings.append("Form 483 manufacturing issues flagged")
        
        return warnings
    
    def predict(self, event: dict) -> PredictionResult:
        """
        Generate prediction for a single PDUFA event.
        
        Args:
            event: Dictionary with event features
            
        Returns:
            PredictionResult with probabilities and metadata
        """
        # Score with both engines
        odin_prob, odin_adj = self._score_odin(event)
        hint_prob, hint_adj = self._score_hint(event)
        
        # Ensemble based on mode
        ta = event.get('therapeutic_area', 'Other')
        ta_risk = self._ta_to_risk.get(ta, 'MOD_RISK')
        
        if self.config.mode == EnsembleMode.ODIN_ONLY:
            ensemble_prob = odin_prob
        elif self.config.mode == EnsembleMode.HINT_ONLY:
            ensemble_prob = hint_prob
        elif self.config.mode == EnsembleMode.OVERRIDE:
            # Use HINT for high-risk TAs, ODIN otherwise
            ta_crl = HINT_TA_CRL_RATES.get(ta, 0.133)
            if ta_crl >= self.config.override_ta_threshold:
                ensemble_prob = hint_prob * 0.6 + odin_prob * 0.4
            else:
                ensemble_prob = odin_prob * 0.8 + hint_prob * 0.2
        else:  # WEIGHTED
            ensemble_prob = (odin_prob * self.config.odin_weight + 
                           hint_prob * self.config.hint_weight)
        
        # Classify
        tier = self._determine_tier(ensemble_prob)
        
        # Confidence based on agreement and tier
        prob_spread = abs(odin_prob - hint_prob)
        if prob_spread < 0.05 and tier in [RiskTier.TIER_1, RiskTier.TIER_4]:
            confidence = "HIGH"
        elif prob_spread < 0.10:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Explanations
        key_factors = self._get_key_factors(odin_adj, hint_adj, event)
        warnings = self._get_warnings(event, odin_prob, hint_prob)
        
        return PredictionResult(
            odin_prob=odin_prob,
            hint_prob=hint_prob,
            ensemble_prob=ensemble_prob,
            tier=tier,
            ta_risk_tier=ta_risk,
            confidence=confidence,
            key_factors=key_factors,
            warnings=warnings,
            odin_adjustments=odin_adj,
            hint_adjustments=hint_adj,
        )
    
    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate predictions for a DataFrame of events.
        
        Args:
            df: DataFrame with event features
            
        Returns:
            DataFrame with added prediction columns
        """
        results = []
        
        for _, row in df.iterrows():
            event = row.to_dict()
            result = self.predict(event)
            results.append({
                'odin_prob': result.odin_prob,
                'hint_prob': result.hint_prob,
                'ensemble_prob': result.ensemble_prob,
                'tier': result.tier.value,
                'ta_risk_tier': result.ta_risk_tier,
                'confidence': result.confidence,
                'n_warnings': len(result.warnings),
            })
        
        result_df = pd.DataFrame(results)
        return pd.concat([df.reset_index(drop=True), result_df], axis=1)
    
    def explain(self, event: dict) -> str:
        """Generate human-readable explanation of prediction."""
        result = self.predict(event)
        
        lines = [
            "=" * 60,
            "ODIN/HINT PREDICTION REPORT",
            "=" * 60,
            "",
            f"Asset: {event.get('asset', 'Unknown')}",
            f"Company: {event.get('company', 'Unknown')}",
            f"Indication: {event.get('indication', 'Unknown')}",
            f"Therapeutic Area: {event.get('therapeutic_area', 'Unknown')}",
            "",
            "--- PREDICTIONS ---",
            f"ODIN (Designation-based):  {result.odin_prob:.1%}",
            f"HINT (Indication-based):   {result.hint_prob:.1%}",
            f"ENSEMBLE:                  {result.ensemble_prob:.1%}",
            "",
            f"TIER: {result.tier.value} | TA Risk: {result.ta_risk_tier} | Confidence: {result.confidence}",
            "",
        ]
        
        if result.key_factors:
            lines.append("--- KEY FACTORS ---")
            for factor in result.key_factors:
                lines.append(f"  • {factor}")
            lines.append("")
        
        if result.warnings:
            lines.append("--- WARNINGS ---")
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        # Trading guidance
        lines.append("--- TRADING GUIDANCE ---")
        if result.tier == RiskTier.TIER_1:
            lines.append("  HIGH CONFIDENCE APPROVAL - Consider long exposure")
        elif result.tier == RiskTier.TIER_4:
            lines.append("  ELEVATED CRL RISK - Consider avoiding or hedging")
        else:
            lines.append("  UNCERTAIN - Size position conservatively")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_predict(event: dict, mode: str = "weighted") -> dict:
    """
    Quick prediction without instantiating engine.
    
    Args:
        event: Event dictionary
        mode: 'odin', 'hint', 'weighted', or 'override'
        
    Returns:
        Dict with probability and tier
    """
    mode_map = {
        'odin': EnsembleMode.ODIN_ONLY,
        'hint': EnsembleMode.HINT_ONLY,
        'weighted': EnsembleMode.WEIGHTED,
        'override': EnsembleMode.OVERRIDE,
    }
    
    config = EngineConfig(mode=mode_map.get(mode, EnsembleMode.WEIGHTED))
    engine = OdinHintEngine(config=config)
    result = engine.predict(event)
    
    return {
        'probability': result.ensemble_prob,
        'tier': result.tier.value,
        'odin_prob': result.odin_prob,
        'hint_prob': result.hint_prob,
        'confidence': result.confidence,
        'warnings': result.warnings,
    }


def batch_score_csv(csv_path: str, output_path: Optional[str] = None,
                    champion_path: Optional[str] = None) -> pd.DataFrame:
    """
    Score a CSV file of PDUFA events.
    
    Args:
        csv_path: Input CSV path
        output_path: Output CSV path (optional)
        champion_path: Path to champion_config.json (optional)
        
    Returns:
        DataFrame with predictions
    """
    engine = OdinHintEngine(champion_path=champion_path)
    df = pd.read_csv(csv_path)
    results = engine.predict_batch(df)
    
    if output_path:
        results.to_csv(output_path, index=False)
        print(f"Saved predictions to {output_path}")
    
    return results


# =============================================================================
# CLI
# =============================================================================

def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ODIN/HINT Dual Prediction Engine")
    parser.add_argument("--csv", help="CSV file to score")
    parser.add_argument("--output", help="Output CSV path")
    parser.add_argument("--champion", help="Path to champion_config.json")
    parser.add_argument("--mode", choices=['odin', 'hint', 'weighted', 'override'],
                       default='weighted', help="Ensemble mode")
    parser.add_argument("--demo", action="store_true", help="Run demo predictions")
    
    args = parser.parse_args()
    
    if args.demo:
        # Demo predictions
        engine = OdinHintEngine()
        
        demo_events = [
            {
                'asset': 'OncoDrug',
                'company': 'BigPharma',
                'indication': 'Metastatic Melanoma',
                'therapeutic_area': 'Oncology',
                'btd': True,
                'orphan': True,
                'priority_review': True,
                'modality': 'Antibody',
                'sponsor_prior_approvals': 25,
                'year': 2024,
            },
            {
                'asset': 'PainKiller',
                'company': 'SmallBio',
                'indication': 'Postoperative pain following bunionectomy surgery',
                'therapeutic_area': 'Pain Management',
                'btd': False,
                'orphan': False,
                'priority_review': False,
                'modality': 'Small Molecule',
                'sponsor_prior_approvals': 1,
                'year': 2024,
            },
            {
                'asset': 'NeuroTherapy',
                'company': 'MidBio',
                'indication': 'Parkinson\'s disease',
                'therapeutic_area': 'CNS/Neurology',
                'btd': True,
                'orphan': False,
                'priority_review': True,
                'modality': 'Small Molecule',
                'sponsor_prior_approvals': 2,
                'year': 2024,
            },
            {
                'asset': 'GeneRx',
                'company': 'GeneTech',
                'indication': 'Rare Blood Disorder',
                'therapeutic_area': 'Hematology',
                'btd': True,
                'orphan': True,
                'priority_review': True,
                'modality': 'Cell/Gene Therapy',
                'sponsor_prior_approvals': 8,
                'year': 2024,
            },
            {
                'asset': 'InfectCure',
                'company': 'VaxCorp',
                'indication': 'HIV',
                'therapeutic_area': 'Infectious Disease',
                'btd': True,
                'orphan': False,
                'priority_review': True,
                'modality': 'Vaccine',
                'sponsor_prior_approvals': 15,
                'year': 2024,
            },
        ]
        
        for event in demo_events:
            print(engine.explain(event))
            print()
        
        return
    
    if args.csv:
        mode_map = {
            'odin': EnsembleMode.ODIN_ONLY,
            'hint': EnsembleMode.HINT_ONLY,
            'weighted': EnsembleMode.WEIGHTED,
            'override': EnsembleMode.OVERRIDE,
        }
        
        config = EngineConfig(mode=mode_map[args.mode])
        engine = OdinHintEngine(config=config, champion_path=args.champion)
        
        df = pd.read_csv(args.csv)
        results = engine.predict_batch(df)
        
        if args.output:
            results.to_csv(args.output, index=False)
            print(f"Saved to {args.output}")
        else:
            # Print summary
            print("\n" + "=" * 60)
            print("BATCH PREDICTION SUMMARY")
            print("=" * 60)
            print(f"Total events: {len(results)}")
            print(f"\nTier distribution:")
            print(results['tier'].value_counts().to_string())
            print(f"\nMean ensemble probability: {results['ensemble_prob'].mean():.1%}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()