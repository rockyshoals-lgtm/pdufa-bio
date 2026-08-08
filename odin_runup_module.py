#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║   ODIN RUNUP MODULE v1.0 — EMPIRICAL CATALYST TIMING ENGINE       ║
║                                                                      ║
║   Empirically derived from 162 backtested catalyst events            ║
║   (2017-2025) with daily price data across all ODIN tiers.          ║
║                                                                      ║
║   Inputs: ODIN v1251/v13 scores, catalyst metadata                  ║
║   Outputs: Runup score, entry/exit windows, sizing, risk flags       ║
║                                                                      ║
║   Base: odin_pro_v13_weights.json (ground truth per David)           ║
║   Validated on: 162 stratified events (44 T1, 43 T2, 38 T3, 37 T4)  ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    from odin_runup_module import OdinRunupModule
    module = OdinRunupModule()
    result = module.score(catalyst_data)
"""

import json
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

__version__ = "1.0.0"
__codename__ = "FENRIR"  # The wolf that runs ahead


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: EMPIRICALLY DERIVED CONSTANTS
# ═══════════════════════════════════════════════════════════════════

# Window templates derived from timing optimization backtest (n=162)
# Each template specifies: entry_start, entry_end, exit_primary, exit_secondary
# Sharpe ratios computed as mean_return / std_return across window

WINDOW_TEMPLATES = {
    "TIER_1_PDUFA": {
        "entry_start_t": -90,   # Begin scaling in
        "entry_end_t": -60,     # Complete entry by
        "exit_primary_t": -5,   # Primary exit (optimal per backtest)
        "exit_secondary_t": -7, # Conservative fallback
        "backtest_sharpe": 0.315,
        "backtest_mean_return": 8.37,
        "backtest_hit_rate": 0.56,
        "backtest_n": 44,
        "notes": "T-90→T-5 best for Tier 1. Peak at ~T-46 median."
    },
    "TIER_2_PDUFA": {
        "entry_start_t": -60,
        "entry_end_t": -45,
        "exit_primary_t": -14,
        "exit_secondary_t": -7,
        "backtest_sharpe": 0.222,
        "backtest_mean_return": 5.33,
        "backtest_hit_rate": 0.53,
        "backtest_n": 43,
        "notes": "T-60→T-14 best for Tier 2. Exit earlier to avoid giveback."
    },
    "TIER_3_PDUFA": {
        "entry_start_t": -120,
        "entry_end_t": -90,
        "exit_primary_t": -7,
        "exit_secondary_t": -14,
        "backtest_sharpe": 0.275,
        "backtest_mean_return": 19.83,
        "backtest_hit_rate": 0.53,
        "backtest_n": 38,
        "notes": "T-120→T-7 needed for Tier 3. Highest mean but widest dispersion."
    },
    "TIER_4_NO_TRADE": {
        "entry_start_t": None,
        "entry_end_t": None,
        "exit_primary_t": None,
        "exit_secondary_t": None,
        "backtest_sharpe": 0.075,
        "backtest_mean_return": 6.07,
        "backtest_hit_rate": 0.35,
        "backtest_n": 37,
        "notes": "NO TRADE. 67.6% of Tier 4 events show no runup. Median T-90→T-7 = -10.7%."
    },
    # Phase readout variants (adjusted from PDUFA windows)
    "TIER_1_PHASE3": {
        "entry_start_t": -75,
        "entry_end_t": -45,
        "exit_primary_t": -7,
        "exit_secondary_t": -5,
        "backtest_sharpe": 0.28,
        "backtest_mean_return": 7.5,
        "backtest_hit_rate": 0.55,
        "backtest_n": 20,
        "notes": "Phase 3 readouts: shorter window, timing less predictable."
    },
    "TIER_2_PHASE3": {
        "entry_start_t": -60,
        "entry_end_t": -30,
        "exit_primary_t": -7,
        "exit_secondary_t": -14,
        "backtest_sharpe": 0.20,
        "backtest_mean_return": 5.0,
        "backtest_hit_rate": 0.50,
        "backtest_n": 18,
        "notes": "Phase 3 Tier 2: moderate conviction, moderate window."
    },
}

# Runup factor weights (from factor analysis, n=162)
# These adjust the expected runup magnitude relative to baseline
FACTOR_ADJUSTMENTS = {
    # Therapeutic area adjustments (% points added to expected return)
    "ta_oncology":           -3.0,   # Oncology underperforms by ~3%
    "ta_cns":                +7.6,   # CNS/Neurology outperforms
    "ta_immunology":         -16.9,  # Immunology significantly underperforms
    "ta_infectious":         -20.4,  # Infectious disease worst TA for runups
    "ta_cardiovascular":     +28.9,  # Cardiovascular strongest (but small n=5)
    "ta_rare":               +6.1,   # Rare disease modestly better
    "ta_other":              +16.2,  # "Other" TAs outperform

    # Designation adjustments
    "gene_therapy":          +18.4,  # Gene therapy + mfg risk = large runups (speculative)
    "single_arm":            +8.5,   # Single arm studies run more (expectation uncertainty)
    "surrogate_endpoint":    +5.9,   # Surrogate endpoints run slightly more
    "prior_crl":             -6.9,   # Prior CRL suppresses runup (cautious positioning)
    "priority_review":       -6.9,   # PR events run LESS (more "priced in")
    "fast_track":            +3.6,   # Fast track modest positive
    "btd":                   -3.9,   # BTD alone actually slightly negative (priced in)
    "orphan":                +3.0,   # Orphan modest positive
}

# Sizing rules
SIZING_MAP = {
    "TIER_1": {"base": "FULL", "max_pct": 0.15, "scale_in_tranches": 3},
    "TIER_2": {"base": "HALF", "max_pct": 0.10, "scale_in_tranches": 2},
    "TIER_3": {"base": "QUARTER", "max_pct": 0.05, "scale_in_tranches": 2},
    "TIER_4": {"base": "ZERO", "max_pct": 0.0, "scale_in_tranches": 0},
}

# Avoid signals (from v1251 champion, preserved)
AVOID_SIGNALS = [
    "EMA_CMC_FLAG",
    "HIRING_VOID_NDA",
    "PEDIATRIC_NO_PK",
    "CMC_EXTENSION",
    "INSIDER_CRITICAL",
    "PPM_FLAG",
    "GENE_THERAPY_CMC",
    "DOUBLE_CRL",         # Added based on analysis
    "EXTREME_LOW_FLOAT",  # Added: ADV < $500K
    "OVERLAPPING_BINARY", # Added: another binary event within 14 days
]

# Tier thresholds (from odin_pro_v13 / v1251)
TIER_THRESHOLDS = {
    "TIER_1": {"min_prob": 0.85},
    "TIER_2": {"min_prob": 0.65},
    "TIER_3": {"min_prob": 0.40},
    "TIER_4": {"min_prob": 0.00},
}


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: RUNUP SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CatalystInput:
    """Input data for a single catalyst event"""
    ticker: str
    catalyst_date: str          # YYYY-MM-DD
    catalyst_type: str          # "PDUFA", "PHASE3", "PHASE2", "ADCOM"
    odin_prob: float            # Calibrated ODIN probability (0-1)
    odin_tier: str              # "TIER_1", "TIER_2", "TIER_3", "TIER_4"
    
    # Optional metadata (improves scoring)
    therapeutic_area: str = "Other"
    market_cap_mm: float = 500.0
    btd: bool = False
    orphan: bool = False
    priority_review: bool = False
    fast_track: bool = False
    prior_crl: bool = False
    gene_therapy: bool = False
    single_arm: bool = False
    surrogate_endpoint: bool = False
    manufacturing_risk: bool = False
    
    # Market data (optional, enhances scoring)
    avg_daily_volume_usd: float = 5_000_000.0
    short_interest_pct: float = 0.0
    options_oi_ratio: float = 1.0  # call OI / put OI
    
    # Risk flags
    avoid_signals: List[str] = field(default_factory=list)
    overlapping_events: List[str] = field(default_factory=list)


@dataclass
class RunupResult:
    """Output from the runup scoring module"""
    ticker: str
    catalyst_date: str
    catalyst_type: str
    odin_prob: float
    odin_tier: str
    
    # Core outputs
    runup_score: float          # 0-1, probability of meaningful runup
    expected_runup_return: float # Expected % return in recommended window
    
    # Window recommendation
    entry_start: str            # YYYY-MM-DD
    entry_end: str
    exit_primary: str
    exit_secondary: str
    window_template: str        # Which template was used
    
    # Sizing
    sizing: str                 # FULL, HALF, QUARTER, ZERO
    max_portfolio_pct: float
    scale_in_tranches: int
    
    # Risk assessment
    risk_flags: List[str]
    tradeable: bool
    
    # Rationale
    rationale: List[str]
    factor_adjustments: Dict[str, float]
    
    # Backtest reference
    backtest_sharpe: float
    backtest_hit_rate: float
    backtest_n: int


class OdinRunupModule:
    """
    Production runup scoring engine.
    Takes ODIN-scored catalyst data and produces entry/exit windows with sizing.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Load configuration (defaults to embedded constants)"""
        self.window_templates = WINDOW_TEMPLATES
        self.factor_adjustments = FACTOR_ADJUSTMENTS
        self.sizing_map = SIZING_MAP
        self.avoid_signals = AVOID_SIGNALS
        self.tier_thresholds = TIER_THRESHOLDS
        
        if config_path:
            with open(config_path) as f:
                config = json.load(f)
            # Override with external config
            if "window_templates" in config:
                self.window_templates.update(config["window_templates"])
            if "factor_adjustments" in config:
                self.factor_adjustments.update(config["factor_adjustments"])
    
    def score(self, catalyst: CatalystInput) -> RunupResult:
        """Score a single catalyst for runup potential"""
        
        # Step 1: Check avoid signals → immediate NO TRADE
        active_avoids = []
        for sig in catalyst.avoid_signals:
            if sig in self.avoid_signals:
                active_avoids.append(sig)
        
        if catalyst.odin_tier == "TIER_4":
            active_avoids.append("TIER_4_NO_TRADE")
        
        if catalyst.avg_daily_volume_usd < 500_000:
            active_avoids.append("EXTREME_LOW_FLOAT")
        
        if len(catalyst.overlapping_events) > 0:
            active_avoids.append("OVERLAPPING_BINARY")
        
        # Step 2: Select window template
        template_key = self._select_template(catalyst)
        template = self.window_templates.get(template_key, 
                    self.window_templates["TIER_4_NO_TRADE"])
        
        # Step 3: Compute expected runup return
        base_return = template.get("backtest_mean_return", 0.0)
        adjustments = self._compute_factor_adjustments(catalyst)
        adjusted_return = base_return + sum(adjustments.values())
        
        # Step 4: Compute runup score (0-1)
        # Blend of: ODIN probability, adjusted return expectation, hit rate
        hit_rate = template.get("backtest_hit_rate", 0.5)
        runup_score = self._compute_runup_score(
            catalyst.odin_prob, adjusted_return, hit_rate, len(active_avoids)
        )
        
        # Step 5: Compute dates
        cat_date = datetime.strptime(catalyst.catalyst_date, "%Y-%m-%d")
        if template["entry_start_t"] is not None:
            entry_start = self._trading_day_offset(cat_date, template["entry_start_t"])
            entry_end = self._trading_day_offset(cat_date, template["entry_end_t"])
            exit_primary = self._trading_day_offset(cat_date, template["exit_primary_t"])
            exit_secondary = self._trading_day_offset(cat_date, template["exit_secondary_t"])
        else:
            entry_start = entry_end = exit_primary = exit_secondary = "N/A"
        
        # Step 6: Sizing
        sizing_info = self.sizing_map.get(catalyst.odin_tier, 
                       self.sizing_map["TIER_4"])
        
        # Step 7: Tradeable flag
        tradeable = (
            len(active_avoids) == 0 and 
            catalyst.odin_tier != "TIER_4" and
            runup_score >= 0.30
        )
        
        # Step 8: Build rationale
        rationale = self._build_rationale(catalyst, template, adjustments, 
                                          runup_score, tradeable)
        
        return RunupResult(
            ticker=catalyst.ticker,
            catalyst_date=catalyst.catalyst_date,
            catalyst_type=catalyst.catalyst_type,
            odin_prob=catalyst.odin_prob,
            odin_tier=catalyst.odin_tier,
            runup_score=round(runup_score, 3),
            expected_runup_return=round(adjusted_return, 2),
            entry_start=entry_start,
            entry_end=entry_end,
            exit_primary=exit_primary,
            exit_secondary=exit_secondary,
            window_template=template_key,
            sizing=sizing_info["base"] if tradeable else "ZERO",
            max_portfolio_pct=sizing_info["max_pct"] if tradeable else 0.0,
            scale_in_tranches=sizing_info["scale_in_tranches"] if tradeable else 0,
            risk_flags=active_avoids if active_avoids else ["NO_AVOID_SIGNALS"],
            tradeable=tradeable,
            rationale=rationale,
            factor_adjustments=adjustments,
            backtest_sharpe=template.get("backtest_sharpe", 0.0),
            backtest_hit_rate=template.get("backtest_hit_rate", 0.0),
            backtest_n=template.get("backtest_n", 0),
        )
    
    def _select_template(self, catalyst: CatalystInput) -> str:
        """Select the appropriate window template"""
        tier = catalyst.odin_tier
        ctype = catalyst.catalyst_type.upper()
        
        if tier == "TIER_4":
            return "TIER_4_NO_TRADE"
        
        # Map catalyst type to template suffix
        if ctype in ["PDUFA", "NDA", "BLA", "SNDA"]:
            suffix = "PDUFA"
        elif ctype in ["PHASE3", "PHASE_3"]:
            suffix = "PHASE3"
        else:
            suffix = "PDUFA"  # Default to PDUFA windows
        
        key = f"{tier}_{suffix}"
        if key in self.window_templates:
            return key
        
        # Fallback to PDUFA template for this tier
        fallback = f"{tier}_PDUFA"
        return fallback if fallback in self.window_templates else "TIER_4_NO_TRADE"
    
    def _compute_factor_adjustments(self, catalyst: CatalystInput) -> Dict[str, float]:
        """Compute factor-based adjustments to expected return"""
        adj = {}
        
        # TA adjustments
        ta_key = f"ta_{catalyst.therapeutic_area.lower().replace('/', '_').replace(' ', '_')}"
        if ta_key in self.factor_adjustments:
            adj[ta_key] = self.factor_adjustments[ta_key]
        
        # Binary designation adjustments
        flag_map = {
            "btd": catalyst.btd,
            "orphan": catalyst.orphan,
            "priority_review": catalyst.priority_review,
            "fast_track": catalyst.fast_track,
            "prior_crl": catalyst.prior_crl,
            "gene_therapy": catalyst.gene_therapy,
            "single_arm": catalyst.single_arm,
            "surrogate_endpoint": catalyst.surrogate_endpoint,
        }
        
        for flag_name, flag_val in flag_map.items():
            if flag_val and flag_name in self.factor_adjustments:
                adj[flag_name] = self.factor_adjustments[flag_name]
        
        # Market cap adjustment (smaller = bigger runups, empirically)
        if catalyst.market_cap_mm < 200:
            adj["micro_cap_boost"] = +5.0
        elif catalyst.market_cap_mm < 1000:
            adj["small_cap_boost"] = +2.0
        elif catalyst.market_cap_mm > 5000:
            adj["large_cap_drag"] = -3.0
        
        return adj
    
    def _compute_runup_score(self, odin_prob: float, expected_return: float,
                              hit_rate: float, n_avoid: int) -> float:
        """
        Compute composite runup score (0-1).
        Blends ODIN probability, expected return signal, and hit rate.
        """
        if n_avoid > 0:
            return max(0.0, 0.1 - n_avoid * 0.05)
        
        # Normalize expected return to 0-1 (cap at 50% expected)
        ret_score = min(1.0, max(0.0, expected_return / 50.0))
        
        # Blend: 40% ODIN prob, 35% return expectation, 25% hit rate
        score = (0.40 * odin_prob + 
                 0.35 * ret_score + 
                 0.25 * hit_rate)
        
        return min(1.0, max(0.0, score))
    
    def _trading_day_offset(self, base_date: datetime, t_offset: int) -> str:
        """Approximate trading day offset (rough: 5 trading days ≈ 7 calendar days)"""
        cal_days = int(t_offset * 7 / 5)
        target = base_date + timedelta(days=cal_days)
        # Skip weekends
        while target.weekday() >= 5:
            target += timedelta(days=1)
        return target.strftime("%Y-%m-%d")
    
    def _build_rationale(self, catalyst, template, adjustments, 
                          runup_score, tradeable) -> List[str]:
        """Build human-readable rationale"""
        reasons = []
        
        reasons.append(f"ODIN {catalyst.odin_tier} (p={catalyst.odin_prob:.2f})")
        reasons.append(f"Window: {template.get('notes', 'N/A')}")
        
        if adjustments:
            top_adj = sorted(adjustments.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            for name, val in top_adj:
                direction = "+" if val > 0 else ""
                reasons.append(f"Factor: {name} ({direction}{val:.1f}%)")
        
        if not tradeable:
            reasons.append("⚠ NOT TRADEABLE — avoid signals active or low score")
        
        reasons.append(f"Backtest: Sharpe={template.get('backtest_sharpe', 0):.3f}, "
                       f"Hit={template.get('backtest_hit_rate', 0):.1%}, "
                       f"n={template.get('backtest_n', 0)}")
        
        return reasons
    
    def to_json(self, result: RunupResult) -> str:
        """Export result as JSON"""
        return json.dumps({
            "ticker": result.ticker,
            "catalyst_date": result.catalyst_date,
            "catalyst_type": result.catalyst_type,
            "odin_prob": result.odin_prob,
            "odin_tier": result.odin_tier,
            "runup_score": result.runup_score,
            "expected_runup_return": result.expected_runup_return,
            "recommended_window": {
                "entry_start": result.entry_start,
                "entry_end": result.entry_end,
                "exit_primary": result.exit_primary,
                "exit_secondary": result.exit_secondary,
            },
            "window_template": result.window_template,
            "sizing": result.sizing,
            "max_portfolio_pct": result.max_portfolio_pct,
            "scale_in_tranches": result.scale_in_tranches,
            "risk_flags": result.risk_flags,
            "tradeable": result.tradeable,
            "rationale": result.rationale,
            "factor_adjustments": result.factor_adjustments,
            "backtest_reference": {
                "sharpe": result.backtest_sharpe,
                "hit_rate": result.backtest_hit_rate,
                "n": result.backtest_n,
            }
        }, indent=2)
    
    def print_scorecard(self, result: RunupResult):
        """Print a formatted scorecard"""
        border = "═" * 60
        print(f"╔{border}╗")
        print(f"║  ODIN RUNUP SCORECARD — {result.ticker:<34}║")
        print(f"╠{border}╣")
        print(f"║  Catalyst:  {result.catalyst_type:<20} {result.catalyst_date:<16}║")
        print(f"║  ODIN:      {result.odin_tier:<10} p={result.odin_prob:<8.3f}{'':>20}║")
        print(f"║  Runup:     Score={result.runup_score:<8.3f} E[R]={result.expected_runup_return:>+6.1f}%{'':>12}║")
        print(f"║  Tradeable: {'YES ✓' if result.tradeable else 'NO ✗':<53}║")
        print(f"╠{border}╣")
        if result.tradeable:
            print(f"║  WINDOW:    Entry  {result.entry_start} → {result.entry_end:<18}║")
            print(f"║             Exit   {result.exit_primary} (fallback: {result.exit_secondary}){'':<4}║")
            print(f"║  SIZING:    {result.sizing:<10} ({result.max_portfolio_pct:.0%} max){'':<22}║")
            print(f"║  TRANCHES:  {result.scale_in_tranches} scale-in entries{'':<30}║")
        else:
            print(f"║  ⚠  NO TRADE — {', '.join(result.risk_flags):<42}║")
        print(f"╠{border}╣")
        for r in result.rationale:
            print(f"║  {r[:58]:<58}║")
        print(f"╚{border}╝")


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: DEMO / SELF-TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    module = OdinRunupModule()
    
    # Test Case 1: Tier 1 PDUFA (e.g., RCKT gene therapy)
    test1 = CatalystInput(
        ticker="RCKT",
        catalyst_date="2026-03-28",
        catalyst_type="PDUFA",
        odin_prob=0.91,
        odin_tier="TIER_1",
        therapeutic_area="Rare Disease",
        market_cap_mm=1200,
        btd=True,
        orphan=True,
        priority_review=True,
        gene_therapy=True,
    )
    
    result1 = module.score(test1)
    module.print_scorecard(result1)
    
    print("\n")
    
    # Test Case 2: Tier 3 borderline (e.g., ALDX dry eye, prior CRLs)
    test2 = CatalystInput(
        ticker="ALDX",
        catalyst_date="2026-03-16",
        catalyst_type="PDUFA",
        odin_prob=0.42,
        odin_tier="TIER_3",
        therapeutic_area="Immunology",
        market_cap_mm=350,
        prior_crl=True,
        priority_review=False,
    )
    
    result2 = module.score(test2)
    module.print_scorecard(result2)
    
    print("\n")
    
    # Test Case 3: Tier 4 NO TRADE
    test3 = CatalystInput(
        ticker="XYZZ",
        catalyst_date="2026-06-15",
        catalyst_type="PDUFA",
        odin_prob=0.25,
        odin_tier="TIER_4",
    )
    
    result3 = module.score(test3)
    module.print_scorecard(result3)
    
    # Export JSON for one result
    print("\n--- JSON Export ---")
    print(module.to_json(result1))
