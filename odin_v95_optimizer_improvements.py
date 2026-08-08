#!/usr/bin/env python3
"""
ODIN v9.5 Optimizer Improvements
================================
Fixes identified in v9.4 annealing run analysis.

KEY CHANGES FROM v9.4:
1. MULTI-OBJECTIVE SCORING - Balance Brier + Tier4 CRL
2. TIGHTENED CONSTRAINTS - Tier4 CRL >= 70% (was 50%)
3. EXPANDED BOUNDS - Allow parameters that hit limits
4. ERA WEIGHTING - Account for pre/post-2020 bias
5. COMPOSITE OBJECTIVE - Penalize low Tier4 CRL in scoring

Copy these changes into the main optimizer script.
"""

# =============================================================================
# FIX 1: TIGHTENED FEASIBILITY CONSTRAINTS
# =============================================================================
# Current values (line 206-209 in v9.4):
# TIER1_MIN = 0.78
# TIER2_MAX = 0.80
# TIER1_APPROVAL_MIN = 0.90
# TIER4_CRL_MIN = 0.50  # <-- TOO WEAK!

# IMPROVED constraints:
TIER1_MIN = 0.78
TIER2_MAX = 0.80
TIER1_APPROVAL_MIN = 0.92       # Tightened from 0.90
TIER4_CRL_MIN = 0.70            # KEY FIX: Was 0.50, now 0.70
TIER4_COUNT_MIN = 15            # NEW: Ensure enough Tier4 events for statistical significance


# =============================================================================
# FIX 2: EXPANDED PARAMETER BOUNDS
# =============================================================================
# Several parameters hit bounds in v9.4 - they want more room

PARAM_BOUNDS_V95 = {
    # Designation weights
    'btd_weight':               (0.00, 0.20),   # Expanded from 0.15 (v9.4 hit 0.116)
    'orphan_weight':            (0.00, 0.12),   # Keep
    'priority_review_weight':   (0.00, 0.15),   # Keep  
    'fast_track_weight':        (0.00, 0.10),   # Keep
    'accelerated_approval_weight': (0.00, 0.12), # Expanded from 0.10
    
    # AdCom (v9.4 hit upper bound on high_boost)
    'adcom_high_boost':         (0.00, 0.25),   # Expanded from 0.20
    'adcom_mid_penalty':        (-0.20, 0.00),  # Expanded from -0.15
    'adcom_low_penalty':        (-0.35, -0.08), # TIGHTENED LOWER: Force meaningful penalty
    
    # Prior CRL / Resubmission
    'prior_crl_penalty':        (-0.25, 0.00),  # Expanded from -0.20
    'class1_resubmission_boost': (0.05, 0.30),  # Expanded from 0.25
    'class2_resubmission_penalty': (-0.20, 0.00), # Expanded from -0.15, removed positive
    
    # Sponsor
    'experienced_sponsor_boost':  (0.00, 0.15),  # Expanded from 0.12
    'inexperienced_sponsor_penalty': (-0.18, 0.00), # Expanded from -0.15
    
    # Manufacturing (v9.4 hit -0.25 bound)
    'manufacturing_risk_penalty': (-0.35, 0.00), # Expanded from -0.25
    'form_483_penalty':          (-0.18, 0.00),  # Expanded from -0.15
    
    # Modality - now separate penalties
    'gene_therapy_penalty':      (-0.15, 0.00),  # NEW: Specific to gene therapy
    'cell_therapy_penalty':      (-0.12, 0.00),  # NEW: Specific to cell therapy
    
    # TA weight
    'ta_adjustment_weight':      (0.5, 1.2),     # Tightened from 1.5 (v9.4 chose 0.86)
    
    # Era weight (NEW)
    'era_weight':                (0.0, 0.15),    # NEW: Boost for post-2020 era
    
    # Tier thresholds
    'tier1_threshold':           (0.80, 0.92),   # Tightened lower from 0.78
    'tier2_threshold':           (0.58, 0.75),   # Tightened upper from 0.80
}


# =============================================================================
# FIX 3: MULTI-OBJECTIVE COMPOSITE SCORE
# =============================================================================

def compute_composite_score(
    brier_score: float,
    tier1_approval_rate: float,
    tier4_crl_rate: float,
    tier4_count: int,
    weights: dict = None
) -> float:
    """
    Multi-objective scoring function that balances:
    - Brier score (lower is better) - calibration quality
    - Tier4 CRL rate (higher is better) - CRL detection
    - Tier1 approval rate (higher is better) - approval confidence
    
    The goal is to find configs that are BOTH well-calibrated AND 
    have strong Tier4 CRL detection.
    
    Returns: composite score (LOWER is better)
    """
    if weights is None:
        weights = {
            'brier': 1.0,           # Primary objective
            'tier4_crl': 0.3,       # Strong penalty for poor CRL detection
            'tier1_approval': 0.1,  # Small reward for high Tier1 accuracy
            'tier4_count': 0.1,     # Reward for sufficient Tier4 events
        }
    
    # Base: Brier score (lower is better)
    score = brier_score * weights['brier']
    
    # Tier4 CRL bonus (higher CRL rate = lower composite score)
    # Target: 85% CRL rate, penalize below 70%
    tier4_bonus = (0.85 - tier4_crl_rate) * weights['tier4_crl']
    if tier4_crl_rate < 0.70:
        # Heavy penalty for falling below 70%
        tier4_bonus += (0.70 - tier4_crl_rate) * 0.5
    score += tier4_bonus
    
    # Tier1 approval bonus (higher is better)
    tier1_penalty = (0.96 - tier1_approval_rate) * weights['tier1_approval']
    score += max(0, tier1_penalty)  # Only penalize if below 96%
    
    # Tier4 count bonus - reward having enough events
    if tier4_count < 20:
        count_penalty = (20 - tier4_count) / 100 * weights['tier4_count']
        score += count_penalty
    
    return score


def score_batch_with_composite(params, data, xp, composite_weights=None):
    """
    Enhanced scoring that returns composite multi-objective scores.
    
    REPLACE the find-best logic in main loop with:
        composite_scores = compute_composite_scores(brier, t1_rates, t4_rates, t4_counts)
        best_idx = np.argmin(composite_scores[feasible_indices])
    """
    # ... standard scoring ...
    # Then compute composite:
    
    # Example integration:
    """
    # In main optimization loop, replace:
    best_idx_in_feasible = np.argmin(feasible_briers)
    
    # With:
    composite_scores = []
    for i in feasible_indices:
        comp = compute_composite_score(
            brier_np[i], t1_np[i], t4_np[i], t4_counts_np[i]
        )
        composite_scores.append(comp)
    best_idx_in_feasible = np.argmin(composite_scores)
    """
    pass


# =============================================================================
# FIX 4: MODALITY-SPECIFIC PENALTIES (replace single modality_penalty)
# =============================================================================

def compute_modality_adjustment(modality: str, params: dict) -> float:
    """
    Compute modality-specific risk adjustment.
    
    Gene therapy and cell therapy have distinct risk profiles
    that should be captured separately.
    """
    modality_map = {
        'Gene Therapy': params.get('gene_therapy_penalty', -0.08),
        'Cell/Gene Therapy': params.get('gene_therapy_penalty', -0.08),
        'Cell Therapy': params.get('cell_therapy_penalty', -0.06),
        'RNA Therapy': params.get('gene_therapy_penalty', -0.08) * 0.5,  # Half of gene therapy
        'Small Molecule': 0.0,  # Baseline
        'Antibody': 0.02,       # Slightly favorable (from historical data)
        'Peptide': 0.0,
        'Vaccine': 0.05,        # Most favorable (0% CRL historically)
        'ADC': 0.0,
    }
    return modality_map.get(modality, 0.0)


# For GPU batch processing, update data preparation:
def prepare_gpu_data_v95(df):
    """Enhanced data prep with separate modality columns."""
    # ... existing code ...
    
    # NEW: Separate modality columns
    df['is_gene_therapy'] = df['modality'].isin([
        'Gene Therapy', 'Cell/Gene Therapy'
    ]).astype(float)
    
    df['is_cell_therapy'] = (df['modality'] == 'Cell Therapy').astype(float)
    
    # ERA: Pre-2020 vs Post-2020
    df['is_post_2020'] = (df['year'] >= 2020).astype(float)
    
    return df


# =============================================================================
# FIX 5: ERA WEIGHTING
# =============================================================================

def compute_era_adjustment(year: int, params: dict) -> float:
    """
    Account for era bias: Pre-2020 had 27% CRL rate vs 13.5% post-2020.
    
    This structural shift should be captured in the model.
    """
    if year >= 2020:
        return params.get('era_weight', 0.05)  # Boost for modern era
    return 0.0


# In GPU scoring, add:
"""
# Era adjustment
probs += xp.outer(era_weight, data['is_post_2020'])
"""


# =============================================================================
# FIX 6: IMPROVED FEASIBILITY CHECK
# =============================================================================

def check_feasibility_v95(
    tier1_thresh, tier2_thresh,
    tier1_approval_rate, tier4_crl_rate,
    tier1_count, tier4_count
):
    """
    Enhanced feasibility with stricter Tier4 requirements.
    """
    feasible = (
        (tier1_thresh >= TIER1_MIN) &
        (tier2_thresh <= TIER2_MAX) &
        (tier1_thresh > tier2_thresh + 0.05) &  # CHANGED: Require 5% gap
        (tier1_approval_rate >= TIER1_APPROVAL_MIN) &
        (tier4_crl_rate >= TIER4_CRL_MIN) &      # KEY: Now 0.70
        (tier1_count >= 10) &
        (tier4_count >= TIER4_COUNT_MIN)         # NEW: >= 15 events
    )
    return feasible


# =============================================================================
# FIX 7: CHECKPOINT RESUME WITH ELITES
# =============================================================================

def load_checkpoint_and_resume(checkpoint_path: str, searcher):
    """
    Resume from checkpoint with elite population intact.
    """
    import json
    
    with open(checkpoint_path, 'r') as f:
        checkpoint = json.load(f)
    
    # Restore elites
    searcher.elites = [
        (score, np.array(params)) 
        for score, params in checkpoint.get('elites', [])
    ]
    
    # Restore temperature
    searcher.temperature = checkpoint.get('temperature', 0.5)
    
    # Restore stats
    searcher.total_improvements = checkpoint.get('total_improvements', 0)
    
    print(f"✅ Resumed from checkpoint:")
    print(f"   Total tested: {checkpoint['total_tested']:,}")
    print(f"   Best score: {checkpoint['best_score']:.5f}")
    print(f"   Elites: {len(searcher.elites)}")
    print(f"   Temperature: {searcher.temperature:.4f}")
    
    return checkpoint['total_tested'], checkpoint['best_score'], checkpoint.get('best_params')


# =============================================================================
# FIX 8: PARAMETER NAME UPDATE (for v9.5)
# =============================================================================

PARAM_NAMES_V95 = [
    'btd_weight', 'orphan_weight', 'priority_review_weight', 'fast_track_weight',
    'accelerated_approval_weight', 'adcom_high_boost', 'adcom_mid_penalty',
    'adcom_low_penalty', 'prior_crl_penalty', 'class1_resubmission_boost',
    'class2_resubmission_penalty', 'experienced_sponsor_boost',
    'inexperienced_sponsor_penalty', 'manufacturing_risk_penalty',
    'form_483_penalty', 
    'gene_therapy_penalty',      # NEW: replaces modality_penalty
    'cell_therapy_penalty',      # NEW
    'ta_adjustment_weight',
    'era_weight',                # NEW
    'tier1_threshold', 
    'tier2_threshold'
]


# =============================================================================
# SUMMARY OF CHANGES
# =============================================================================
"""
ODIN v9.5 OPTIMIZER IMPROVEMENTS SUMMARY
========================================

1. TIER4_CRL_MIN: 0.50 → 0.70
   - Non-negotiable: Tier4 must detect CRLs at 70%+ rate

2. COMPOSITE OBJECTIVE:
   - Balance Brier score + Tier4 CRL rate
   - Heavy penalty for Tier4 CRL < 70%

3. EXPANDED BOUNDS:
   - btd_weight: 0.15 → 0.20
   - adcom_high_boost: 0.20 → 0.25  
   - manufacturing_risk: -0.25 → -0.35
   - adcom_low_penalty: lower bound -0.08 (force meaningful penalty)

4. MODALITY GRANULARITY:
   - Replaced single modality_penalty with:
     - gene_therapy_penalty
     - cell_therapy_penalty

5. ERA WEIGHTING:
   - Added era_weight for post-2020 baseline shift

6. TIER4 COUNT MINIMUM:
   - New constraint: tier4_count >= 15

7. THRESHOLD GAP:
   - tier1_thresh > tier2_thresh + 0.05

8. CHECKPOINT RESUME:
   - Properly restore elites, temperature, progress

EXPECTED OUTCOME:
- Brier: ~0.082-0.085 (slight regression acceptable)
- Tier4 CRL: ≥75% (target 85%)
- Tier1 Approval: ≥94%
"""


if __name__ == "__main__":
    print("ODIN v9.5 Optimizer Improvements")
    print("=" * 50)
    print("\nKey changes:")
    print("1. TIER4_CRL_MIN raised to 70% (was 50%)")
    print("2. Multi-objective composite scoring")
    print("3. Expanded parameter bounds")
    print("4. Separate gene/cell therapy penalties")
    print("5. Era weighting (pre/post-2020)")
    print("\nCopy these improvements into the main optimizer script.")
