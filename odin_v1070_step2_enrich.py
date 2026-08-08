#!/usr/bin/env python3
"""
ODIN v10.70 Step 2: Populate Dead Features
==========================================
- manufacturing_risk: Auto-flag gene therapy + known CMC CRL assets
- resubmission_class: Time-gap heuristic for true resubmissions

Input:  ODIN_MODEL_READY_v1070_STEP1_ENRICHED.csv (2210 events, 36 cols)
Output: ODIN_MODEL_READY_v1070_STEP2_ENRICHED.csv (2210 events, 36 cols)

Signal Validation:
  manufacturing_risk=True:  CRL=60.3% (N=126) vs 30.3% baseline → +30pp lift
  resubmission_class=2:    CRL=70.4% (N=135) vs 28.5% first-filing → +42pp lift
  resubmission_class=1:    CRL=48.1% (N=104) vs 28.5% first-filing → +20pp lift

Author: ODIN Engineering (v10.70 expansion)
Date: 2026-02-14
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
INPUT_FILE = "ODIN_MODEL_READY_v1070_STEP1_ENRICHED.csv"
OUTPUT_FILE = "ODIN_MODEL_READY_v1070_STEP2_ENRICHED.csv"

# Pure-play gene therapy companies (ALL products are GT/cell therapy)
PURE_PLAY_GT_TICKERS = {
    'RCKT', 'RGNX', 'SGMO', 'BEAM', 'CRSP', 'EDIT', 'NTLA',
    'QURE', 'ABEO', 'ONCE', 'BLUE',
}

# CMC-related asset keywords (non-GT products with known manufacturing issues)
CMC_ASSET_KEYWORDS = [
    'primatene', 'cortrophin', 'brixadi', 'cyclophosphamide', 'bortezomib',
    'acetaminophen injection', 'cefazolin', 'romidepsin', 'daptomycin',
    'theragrastim', 'epinephrine injection', 'meloxicam injection',
    'naloxone', 'fosphenytoin',
]

# Resubmission classification threshold (days)
RESUB_GAP_THRESHOLD = 240  # ≤ 240 days = Class 2 (rushed), > 240 = Class 1 (addressed)


def normalize_asset(asset_str):
    """Normalize asset name for drug-level matching."""
    if pd.isna(asset_str):
        return ''
    s = str(asset_str).lower().strip()
    if '(' in s:
        s = s.split('(')[0].strip()
    words = s.split()
    return words[0] if words else s


def extract_indication_keywords(ind_str):
    """Extract disease keywords from indication text."""
    if pd.isna(ind_str):
        return set()
    s = str(ind_str).lower()
    for w in ['of', 'the', 'in', 'for', 'with', 'and', 'or', 'to', 'a', 'an']:
        s = s.replace(f' {w} ', ' ')
    return set(s.split())


def populate_manufacturing_risk(df):
    """
    Auto-populate manufacturing_risk based on:
    1. gene_therapy=True (inherent CMC complexity)
    2. Pure-play GT company tickers
    3. Known CMC-related asset keywords
    
    KEY: Asset-level, NOT ticker-level for diversified companies.
    BMRN Roctavian (GT) → True, BMRN VOXZOGO (peptide) → False
    """
    gt_mask = df['gene_therapy'] == True
    ticker_mask = df['ticker'].isin(PURE_PLAY_GT_TICKERS)
    
    asset_mask = df['asset'].apply(
        lambda x: any(kw in str(x).lower() for kw in CMC_ASSET_KEYWORDS)
        if pd.notna(x) else False
    )
    
    df['manufacturing_risk'] = gt_mask | ticker_mask | asset_mask
    return df


def populate_resubmission_class(df):
    """
    Classify resubmissions using time-gap heuristic.
    
    KEY FINDING: Short gaps correlate with WORSE outcomes (serial failure),
    long gaps correlate with BETTER outcomes (company addressed issues).
    
    Class 1 (long gap >240d): Company took time → 48.1% CRL
    Class 2 (short gap ≤240d): Rushed/serial failure → 70.4% CRL
    NaN: First filing or parallel indication → 28.5% CRL
    
    Only classifies TRUE resubmissions (same drug + similar indication).
    """
    df['_norm_asset'] = df['asset'].apply(normalize_asset)
    crl_events = df[df['outcome'] == 'CRL'].sort_values('catalyst_date')
    
    # Reset resubmission_class
    df['resubmission_class'] = np.nan
    
    for idx, row in df[df['prior_crl_count'] > 0].iterrows():
        norm_asset = row['_norm_asset']
        event_date = row['catalyst_date']
        
        # Find prior CRL events for same drug
        prior_crls = crl_events[
            (crl_events['_norm_asset'] == norm_asset) &
            (crl_events['catalyst_date'] < event_date)
        ]
        
        if len(prior_crls) == 0:
            continue
        
        most_recent = prior_crls.iloc[-1]
        gap_days = (event_date - most_recent['catalyst_date']).days
        
        # Check indication overlap
        event_ind = extract_indication_keywords(row['indication'])
        crl_ind = extract_indication_keywords(most_recent['indication'])
        ind_overlap = len(event_ind & crl_ind) >= 2 if event_ind and crl_ind else False
        
        # Determine if this is a TRUE resubmission
        is_true_resub = (
            (row.get('prior_crl') == True) or
            (ind_overlap and gap_days <= 730)
        )
        
        if is_true_resub:
            if gap_days > RESUB_GAP_THRESHOLD:
                df.loc[idx, 'resubmission_class'] = 1.0  # Long gap → better prognosis
            else:
                df.loc[idx, 'resubmission_class'] = 2.0  # Short gap → worse prognosis
    
    df.drop('_norm_asset', axis=1, inplace=True)
    return df


def validate(df):
    """Print signal validation summary."""
    outcomes = df[df['outcome'].isin(['APPROVAL', 'CRL'])]
    baseline = (outcomes['outcome'] == 'CRL').mean()
    
    print(f"\n{'Signal':<40s} {'N':>5s} {'CRL%':>7s} {'Lift':>8s}")
    print("-" * 65)
    
    signals = [
        ("manufacturing_risk=True", outcomes['manufacturing_risk'] == True),
        ("manufacturing_risk=False", outcomes['manufacturing_risk'] == False),
        ("resubmission_class=1 (long gap)", outcomes['resubmission_class'] == 1.0),
        ("resubmission_class=2 (short gap)", outcomes['resubmission_class'] == 2.0),
        ("resubmission_class=NaN (first filing)", outcomes['resubmission_class'].isna()),
    ]
    
    for name, mask in signals:
        subset = outcomes[mask]
        n = len(subset)
        if n == 0:
            continue
        crl_rate = (subset['outcome'] == 'CRL').mean()
        lift = (crl_rate - baseline) * 100
        print(f"  {name:<38s} {n:>5d} {crl_rate:>6.1%} {lift:>+7.1f}pp")
    
    print(f"\n  Baseline: {baseline:.1%} (N={len(outcomes)})")


def main():
    print("ODIN v10.70 Step 2: Populate Dead Features")
    print("=" * 50)
    
    # Load Step 1 output
    df = pd.read_csv(INPUT_FILE)
    df['catalyst_date'] = pd.to_datetime(df['catalyst_date'])
    print(f"Loaded: {INPUT_FILE} ({len(df)} rows, {len(df.columns)} cols)")
    
    # Step 2A: manufacturing_risk
    print("\n--- Step 2A: manufacturing_risk ---")
    before = df['manufacturing_risk'].sum()
    df = populate_manufacturing_risk(df)
    after = df['manufacturing_risk'].sum()
    print(f"  Before: {before} True → After: {after} True (+{after-before})")
    
    # Step 2B: resubmission_class
    print("\n--- Step 2B: resubmission_class ---")
    df = populate_resubmission_class(df)
    c1 = (df['resubmission_class'] == 1.0).sum()
    c2 = (df['resubmission_class'] == 2.0).sum()
    print(f"  Class 1 (long gap): {c1}")
    print(f"  Class 2 (short gap): {c2}")
    print(f"  NaN (first/parallel): {df['resubmission_class'].isna().sum()}")
    
    # Validate
    validate(df)
    
    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Saved: {OUTPUT_FILE}")
    print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")


if __name__ == "__main__":
    main()
