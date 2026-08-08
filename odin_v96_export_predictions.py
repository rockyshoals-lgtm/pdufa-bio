#!/usr/bin/env python3
"""
ODIN v9.6 - Export Tier Predictions for Full Dataset
=====================================================
Generates predictions and tier assignments for all events.

Usage:
    python odin_v96_export_predictions.py
    python odin_v96_export_predictions.py path/to/data.csv
"""

import pandas as pd
import numpy as np
import sys
import os
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Try importing optional dependencies
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

# HINT therapeutic area adjustments
HINT_TA = {
    "Pain Management": -0.286, "Hematology": -0.224, "Nephrology": -0.177,
    "Ophthalmology": -0.131, "CNS/Neurology": -0.098, "Cardiovascular": -0.081,
    "Metabolic/Endocrine": -0.067, "Rare Disease": -0.043, "Other": -0.019,
    "Immunology": 0.016, "Dermatology": 0.028, "Oncology": 0.061,
    "GI/Hepatology": 0.067, "Respiratory": 0.090, "Infectious Disease": 0.103,
    "Vaccines": 0.133, "Women's Health": 0.133,
}

# T-1 COMPLIANT modality complexity proxy
MODALITY_COMPLEXITY = {
    "Small Molecule": 0.0, "Peptide": 0.2, "Antibody": 0.3,
    "ADC": 0.5, "RNA Therapy": 0.6, "Cell/Gene Therapy": 0.8, "Vaccine": 0.2,
}

# Tier thresholds
TIER_THRESHOLDS = [
    (0.95, 1.00, "T1_STRONG_LONG"),
    (0.90, 0.95, "T2_LONG"),
    (0.85, 0.90, "T3_CAUTIOUS"),
    (0.80, 0.85, "T4_NEUTRAL"),
    (0.70, 0.80, "T5_AVOID"),
    (0.00, 0.70, "T6_STRONG_SHORT"),
]


def find_data_file():
    """Find the data file."""
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            return filepath
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    possible_names = [
        "ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv",
        "odin_enriched_pdufa_v4_2_audited.csv",
        "ODIN_v4_2.csv",
    ]
    
    for name in possible_names:
        if os.path.exists(name):
            return name
    
    print("Error: Could not find data file.")
    print("Usage: python odin_v96_export_predictions.py <path_to_csv>")
    sys.exit(1)


def load_and_prepare_data(filepath):
    """Load and prepare data with T-1 compliance."""
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} events from {os.path.basename(filepath)}")
    
    # Convert boolean columns
    bool_cols = ['btd', 'orphan', 'priority_review', 'fast_track', 'had_adcom', 
                 'experienced_sponsor', 'prior_crl', 'first_cycle', 'form_483_issues']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes']).astype(float)
    
    if 'accelerated_approval' in df.columns:
        df['accelerated_approval'] = df['accelerated_approval'].astype(str).str.lower().isin(['true', '1', 'yes']).astype(float)
    
    # Numeric columns
    df['adcom_vote_pct'] = pd.to_numeric(df['adcom_vote_pct'], errors='coerce').fillna(0)
    df['sponsor_prior_approvals'] = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
    df['designation_stack_count'] = pd.to_numeric(df['designation_stack_count'], errors='coerce').fillna(0)
    df['resubmission_class'] = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
    
    # T-1 COMPLIANT: modality_complexity (NOT manufacturing_risk!)
    df['modality_complexity'] = df['modality'].map(MODALITY_COMPLEXITY).fillna(0.3)
    df['ta_adjustment'] = df['therapeutic_area'].map(HINT_TA).fillna(0)
    
    # Target
    df['target'] = (df['outcome'].str.upper() == 'APPROVAL').astype(float)
    
    return df


def create_features(df):
    """Create T-1 compliant feature set."""
    f = pd.DataFrame()
    
    f['btd'] = df['btd']
    f['orphan'] = df['orphan']
    f['priority_review'] = df['priority_review']
    f['fast_track'] = df['fast_track']
    f['accelerated_approval'] = df['accelerated_approval']
    f['designation_stack'] = df['designation_stack_count']
    f['had_adcom'] = df['had_adcom']
    f['adcom_vote_pct'] = df['adcom_vote_pct']
    f['experienced_sponsor'] = df['experienced_sponsor']
    f['sponsor_prior_log'] = np.log1p(df['sponsor_prior_approvals'])
    f['prior_crl'] = df['prior_crl']
    f['resubmission_class'] = df['resubmission_class']
    f['first_cycle'] = df['first_cycle']
    f['modality_complexity'] = df['modality_complexity']
    f['form_483_issues'] = df['form_483_issues']
    f['ta_adjustment'] = df['ta_adjustment']
    f['year_norm'] = (df['year'] - 2018) / 8
    
    # Interactions
    f['ta_x_sponsor_prior'] = df['ta_adjustment'] * f['sponsor_prior_log']
    f['ta_x_exp_sponsor'] = df['ta_adjustment'] * df['experienced_sponsor']
    f['btd_x_orphan'] = df['btd'] * df['orphan']
    f['btd_x_priority'] = df['btd'] * df['priority_review']
    f['year_x_ta'] = f['year_norm'] * df['ta_adjustment']
    f['modality_x_ta'] = df['modality_complexity'] * df['ta_adjustment']
    
    # Polynomials
    f['sponsor_prior_sq'] = f['sponsor_prior_log'] ** 2
    f['ta_adjustment_sq'] = df['ta_adjustment'] ** 2
    
    # Risk indicators
    f['high_risk'] = ((df['ta_adjustment'] < -0.1) & (df['experienced_sponsor'] == 0)).astype(float)
    f['low_risk'] = ((df['ta_adjustment'] > 0.05) & (df['sponsor_prior_approvals'] >= 5)).astype(float)
    
    # TA one-hot
    for ta in ['Pain Management', 'Hematology', 'Oncology', 'CNS/Neurology', 
               'Ophthalmology', 'Infectious Disease', 'Cardiovascular']:
        col_name = f'ta_{ta.replace(" ", "_").replace("/", "_")}'
        f[col_name] = (df['therapeutic_area'] == ta).astype(float)
    
    return f


def assign_tier(prob):
    """Assign tier based on probability."""
    for low, high, tier_name in TIER_THRESHOLDS:
        if low <= prob < high:
            return tier_name
    return "T6_STRONG_SHORT"


def get_trading_signal(tier):
    """Get trading signal from tier."""
    signals = {
        "T1_STRONG_LONG": "STRONG LONG",
        "T2_LONG": "LONG",
        "T3_CAUTIOUS": "CAUTIOUS LONG",
        "T4_NEUTRAL": "NEUTRAL",
        "T5_AVOID": "AVOID",
        "T6_STRONG_SHORT": "STRONG SHORT",
    }
    return signals.get(tier, "UNKNOWN")


def main():
    print("=" * 70)
    print("ODIN v9.6 - EXPORT TIER PREDICTIONS")
    print("=" * 70)
    
    filepath = find_data_file()
    df = load_and_prepare_data(filepath)
    
    features = create_features(df)
    y = df['target'].values
    
    print(f"\nTraining stacking ensemble on {len(df)} events...")
    
    scaler = StandardScaler()
    X = scaler.fit_transform(features.values)
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Base models
    models = {
        'LogisticRegression_L2': LogisticRegression(C=1.0, max_iter=2000, random_state=42),
        'LogisticRegression_L1': LogisticRegression(C=0.5, penalty='l1', solver='saga', max_iter=2000, random_state=42),
        'LogisticRegression_EN': LogisticRegression(C=0.5, penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=2000, random_state=42),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            min_samples_leaf=20, subsample=0.7, random_state=42
        ),
        'MLP': MLPClassifier(
            hidden_layer_sizes=(32, 16), alpha=1.0,
            learning_rate_init=0.01, max_iter=500, random_state=42
        ),
    }
    
    if HAS_XGB:
        models['XGBoost'] = xgb.XGBClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            min_child_weight=20, subsample=0.7, colsample_bytree=0.7,
            reg_alpha=1.0, reg_lambda=2.0, random_state=42,
            use_label_encoder=False, eval_metric='logloss'
        )
    
    if HAS_LGB:
        models['LightGBM'] = lgb.LGBMClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            min_child_samples=20, subsample=0.7, colsample_bytree=0.7,
            reg_alpha=1.0, reg_lambda=2.0, random_state=42, verbose=-1
        )
    
    # Generate OOF predictions
    oof_predictions = {}
    for name, model in models.items():
        print(f"  Training {name}...", end=" ", flush=True)
        oof_pred = cross_val_predict(model, X, y, cv=cv, method='predict_proba')[:, 1]
        oof_predictions[name] = oof_pred
        print("done")
    
    # Stacking with extended features
    model_names = list(oof_predictions.keys())
    meta_features = np.column_stack([oof_predictions[name] for name in model_names])
    meta_features_extended = np.hstack([meta_features, X])
    
    print("  Training meta-learner...", end=" ", flush=True)
    meta_lr = LogisticRegression(C=5.0, max_iter=1000, random_state=42)
    final_probs = cross_val_predict(meta_lr, meta_features_extended, y, cv=cv, method='predict_proba')[:, 1]
    print("done")
    
    # Assign tiers
    df['odin_probability'] = final_probs
    df['odin_tier'] = df['odin_probability'].apply(assign_tier)
    df['trading_signal'] = df['odin_tier'].apply(get_trading_signal)
    
    # Calculate actual outcome for historical events
    df['actual_outcome'] = df['outcome'].str.upper()
    df['prediction_correct'] = ((df['odin_probability'] >= 0.5) & (df['actual_outcome'] == 'APPROVAL')) | \
                               ((df['odin_probability'] < 0.5) & (df['actual_outcome'] == 'CRL'))
    
    # Select output columns
    output_cols = [
        'event_id', 'ticker', 'company', 'asset', 'indication', 
        'therapeutic_area', 'catalyst_date', 'year',
        'btd', 'orphan', 'priority_review', 'fast_track',
        'prior_crl', 'resubmission_class', 'modality',
        'actual_outcome', 'odin_probability', 'odin_tier', 'trading_signal',
        'prediction_correct'
    ]
    
    # Filter to available columns
    output_cols = [c for c in output_cols if c in df.columns]
    output_df = df[output_cols].copy()
    
    # Sort by probability descending
    output_df = output_df.sort_values('odin_probability', ascending=False)
    
    # Export
    output_file = 'ODIN_v96_TIER_PREDICTIONS.csv'
    output_df.to_csv(output_file, index=False)
    
    print(f"\n{'='*70}")
    print(f"EXPORTED: {output_file}")
    print(f"{'='*70}")
    
    # Summary statistics
    print(f"\n[TIER DISTRIBUTION]")
    print(f"{'Tier':<20} {'Count':>8} {'Approval%':>12} {'Trading Signal':<15}")
    print("-" * 60)
    
    for low, high, tier_name in TIER_THRESHOLDS:
        mask = output_df['odin_tier'] == tier_name
        count = mask.sum()
        if count > 0:
            appr_rate = (output_df.loc[mask, 'actual_outcome'] == 'APPROVAL').mean() * 100
            signal = get_trading_signal(tier_name)
            print(f"{tier_name:<20} {count:>8} {appr_rate:>11.1f}% {signal:<15}")
    
    print(f"\n[ACCURACY METRICS]")
    brier = np.mean((final_probs - y) ** 2)
    accuracy = output_df['prediction_correct'].mean() * 100
    print(f"  Brier Score: {brier:.5f}")
    print(f"  Accuracy: {accuracy:.1f}%")
    
    # Upcoming events (future dates)
    try:
        output_df['catalyst_date'] = pd.to_datetime(output_df['catalyst_date'], errors='coerce')
        today = pd.Timestamp.now()
        upcoming = output_df[output_df['catalyst_date'] > today].sort_values('catalyst_date')
        
        if len(upcoming) > 0:
            print(f"\n[UPCOMING PDUFA EVENTS]")
            print(f"{'Ticker':<8} {'Date':<12} {'Prob':>8} {'Tier':<18} {'Signal':<15}")
            print("-" * 65)
            for _, row in upcoming.head(20).iterrows():
                date_str = row['catalyst_date'].strftime('%Y-%m-%d') if pd.notna(row['catalyst_date']) else 'N/A'
                print(f"{row['ticker']:<8} {date_str:<12} {row['odin_probability']:>7.1%} {row['odin_tier']:<18} {row['trading_signal']:<15}")
    except Exception:
        pass
    
    print(f"\n+ Full predictions saved to {output_file}")
    
    return output_df


if __name__ == "__main__":
    results = main()