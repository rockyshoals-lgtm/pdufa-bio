#!/usr/bin/env python3
"""
GUNGNIR v51 HEIMDALL Red Team Kaizen
=======================================
Test if HEIMDALL phase outcome classifier improves v49-ARCH Gungnir ensemble.

SCHEMA NOTES:
- Gungnir dataset (gungnir_readout_ctgov_enriched.csv):
  Columns: ticker, name, drug, indication, stage, date, outcome, ta, phase, ... (1,752 rows)
  No 'event_id' column. Use 'ticker' for merge.
  'date' column needs parsing to extract year.

- HEIMDALL panel (heimdall_v1_scored_panel_honest.csv):
  Columns: event_id, ticker, company, asset, indication, ta, stage_clean, catalyst_date, year,
           parsed_outcome, outcome_binary, heimdall_p, heimdall_tier (3,522 rows)
  Only 760 rows have non-NaN heimdall_p (OOS test set). 2,761 rows have NaN (train/val masked).

MERGE STRATEGY:
1. Load both panels
2. Merge on 'ticker' (common column)
3. Create 3-way temporal split using Gungnir 'date' + HEIMDALL 'year':
   - Extract year from Gungnir 'date' column
   - train: year <= 2023
   - val: year in [2024]
   - test: year >= 2024 (but also filtered to only 760 HEIMDALL OOS rows with non-NaN heimdall_p)
4. Train v49 baseline (without heimdall_p)
5. Train v51 variant (with heimdall_p feature)
6. Compare test AUC, Brier, and 20-seed stability
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
import json
import os
from datetime import datetime

# Paths
BASE_PATH = r"C:\Users\dcmoo\Documents\Python\9realms\Odin Perfection"
GUNGNIR_PATH = os.path.join(BASE_PATH, "gungnir_readout_ctgov_enriched.csv")
HEIMDALL_PATH = os.path.join(BASE_PATH, "heimdall_v1_scored_panel_honest.csv")
OUTPUT_PATH = os.path.join(BASE_PATH, "gungnir_v51_heimdall_results.json")
DEPLOY_PATH = os.path.join(BASE_PATH, "gungnir_v51_heimdahl_deploy.json")

print("[v51 KAIZEN] Loading datasets...")

# Load Gungnir
gdf = pd.read_csv(GUNGNIR_PATH)
print(f"  Gungnir shape: {gdf.shape}")
print(f"  Gungnir columns: {list(gdf.columns[:15])}...")

# Load HEIMDALL
hdf = pd.read_csv(HEIMDALL_PATH)
print(f"  HEIMDALL shape: {hdf.shape}")
print(f"  HEIMDALL columns: {list(hdf.columns)}")

# Parse year from Gungnir 'date' column
# Assuming format like "2024-05-15" or similar
gdf['date'] = pd.to_datetime(gdf['date'], errors='coerce')
gdf['year'] = gdf['date'].dt.year
print(f"  Gungnir year range: {gdf['year'].min()} to {gdf['year'].max()}")
print(f"  Gungnir NaT dates: {gdf['year'].isna().sum()}")

# Merge on ticker
print("\n[v51 KAIZEN] Merging HEIMDALL OOS scores with Gungnir...")
merged = gdf.merge(
    hdf[['ticker', 'heimdall_p', 'heimdall_tier']],
    on='ticker',
    how='left',
    suffixes=('_gungnir', '_heimdall')
)
print(f"  Merged shape: {merged.shape}")
print(f"  heimdall_p non-NaN count: {merged['heimdall_p'].notna().sum()}")

# Create 3-way temporal split
# Important: Only use HEIMDALL OOS rows (non-NaN heimdall_p) for test set
train_mask = (merged['year'] <= 2023) & (merged['heimdall_p'].isna())  # train on all ≤2023 without HEIMDALL scores
val_mask = (merged['year'] == 2024) & (merged['heimdall_p'].isna())     # val on 2024 without HEIMDALL scores
test_mask = (merged['year'] >= 2024) & (merged['heimdall_p'].notna())   # test on ≥2024-07 WITH HEIMDALL OOS scores

train_indices = merged[train_mask].index
val_indices = merged[val_mask].index
test_indices = merged[test_mask].index

print(f"\n[v51 KAIZEN] Temporal split:")
print(f"  Train: {len(train_indices)} (year <= 2023)")
print(f"  Val: {len(val_indices)} (year == 2024)")
print(f"  Test: {len(test_indices)} (year >= 2024 with HEIMDALL OOS scores)")

# Combine train+val for training (standard ML practice)
trainval_mask = train_mask | val_mask
trainval_indices = merged[trainval_mask].index

# Target variable
target_col = 'met_primary'  # Assumes Gungnir has binary outcome column
if target_col not in merged.columns:
    # Try alternatives
    for alt in ['outcome_binary', 'outcome', 'primary_outcome', 'success']:
        if alt in merged.columns:
            target_col = alt
            break
    print(f"  Using target column: {target_col}")
else:
    print(f"  Using target column: {target_col}")

# Feature engineering
# v49-ARCH baseline features (existing Gungnir features)
v49_base_features = [
    'pre_price', 'log_price', 'd0_price', 'd1_price', 'd5_price',
    'ret_0d', 'ret_1d', 'ret_2d', 'ret_5d', 'primary_ret_pct'
]

# Filter to available columns
available_features = [f for f in v49_base_features if f in merged.columns]
print(f"\n[v51 KAIZEN] Available baseline features: {len(available_features)}")
print(f"  Features: {available_features}")

# Fill NaN in features
X_trainval = merged.loc[trainval_indices, available_features].fillna(0)
X_test = merged.loc[test_indices, available_features].fillna(0)

# Add HEIMDALL feature for v51 variant
X_trainval_v51 = X_trainval.copy()
X_trainval_v51['heimdall_p'] = merged.loc[trainval_indices, 'heimdall_p'].fillna(0.5)  # impute with neutral

X_test_v51 = X_test.copy()
X_test_v51['heimdall_p'] = merged.loc[test_indices, 'heimdall_p'].fillna(0.5)

# Target
y_trainval = merged.loc[trainval_indices, target_col].values
y_test = merged.loc[test_indices, target_col].values

print(f"\n[v51 KAIZEN] Target variable distributions:")
print(f"  Train+Val: {np.mean(y_trainval):.4f} positive rate ({np.sum(y_trainval)} positive)")
print(f"  Test: {np.mean(y_test):.4f} positive rate ({np.sum(y_test)} positive)")

# Scale features
scaler_v49 = StandardScaler()
X_trainval_scaled = scaler_v49.fit_transform(X_trainval)
X_test_scaled = scaler_v49.transform(X_test)

scaler_v51 = StandardScaler()
X_trainval_v51_scaled = scaler_v51.fit_transform(X_trainval_v51)
X_test_v51_scaled = scaler_v51.transform(X_test_v51)

print(f"\n[v51 KAIZEN] Feature scaling complete")
print(f"  v49 train shape: {X_trainval_scaled.shape}")
print(f"  v51 train shape: {X_trainval_v51_scaled.shape}")

# Train v49 baseline (Ridge C=0.015, as per spec)
print(f"\n[v51 KAIZEN] Training v49 baseline (Ridge LR, C=0.015)...")
model_v49 = LogisticRegression(
    penalty='l2',
    C=0.015,
    solver='lbfgs',
    max_iter=5000,
    random_state=42
)
model_v49.fit(X_trainval_scaled, y_trainval)

# Predict on test
y_pred_v49_proba = model_v49.predict_proba(X_test_scaled)[:, 1]
auc_v49 = roc_auc_score(y_test, y_pred_v49_proba)
brier_v49 = brier_score_loss(y_test, y_pred_v49_proba)

print(f"  v49 test AUC: {auc_v49:.4f}")
print(f"  v49 test Brier: {brier_v49:.4f}")

# Train v51 variant with HEIMDALL
print(f"\n[v51 KAIZEN] Training v51 with HEIMDALL feature...")
model_v51 = LogisticRegression(
    penalty='l2',
    C=0.015,
    solver='lbfgs',
    max_iter=5000,
    random_state=42
)
model_v51.fit(X_trainval_v51_scaled, y_trainval)

# Predict on test
y_pred_v51_proba = model_v51.predict_proba(X_test_v51_scaled)[:, 1]
auc_v51 = roc_auc_score(y_test, y_pred_v51_proba)
brier_v51 = brier_score_loss(y_test, y_pred_v51_proba)

print(f"  v51 test AUC: {auc_v51:.4f}")
print(f"  v51 test Brier: {brier_v51:.4f}")

# Delta
auc_delta = auc_v51 - auc_v49
brier_delta = brier_v51 - brier_v49  # negative is better (lower Brier)

print(f"\n[v51 KAIZEN] Baseline vs HEIMDAHL comparison:")
print(f"  AUC delta: {auc_delta:+.4f} ({auc_delta/auc_v49*100:+.2f}%)")
print(f"  Brier delta: {brier_delta:+.4f} ({brier_delta/brier_v49*100:+.2f}%)")

# Stability test: 20 random seeds
print(f"\n[v51 KAIZEN] Running 20-seed stability test...")
auc_v49_seeds = []
auc_v51_seeds = []

for seed in range(20):
    m49 = LogisticRegression(penalty='l2', C=0.015, solver='lbfgs', max_iter=5000, random_state=seed)
    m49.fit(X_trainval_scaled, y_trainval)
    auc_v49_seeds.append(roc_auc_score(y_test, m49.predict_proba(X_test_scaled)[:, 1]))

    m51 = LogisticRegression(penalty='l2', C=0.015, solver='lbfgs', max_iter=5000, random_state=seed)
    m51.fit(X_trainval_v51_scaled, y_trainval)
    auc_v51_seeds.append(roc_auc_score(y_test, m51.predict_proba(X_test_v51_scaled)[:, 1]))

auc_v49_seeds = np.array(auc_v49_seeds)
auc_v51_seeds = np.array(auc_v51_seeds)

print(f"  v49 AUC mean ± std: {np.mean(auc_v49_seeds):.4f} ± {np.std(auc_v49_seeds):.4f}")
print(f"  v51 AUC mean ± std: {np.mean(auc_v51_seeds):.4f} ± {np.std(auc_v51_seeds):.4f}")
print(f"  v51 wins: {np.sum(auc_v51_seeds > auc_v49_seeds)}/20 seeds")

# Paired t-test
from scipy.stats import ttest_rel
t_stat, p_value = ttest_rel(auc_v51_seeds, auc_v49_seeds)
print(f"  Paired t-test: t={t_stat:.4f}, p={p_value:.4e}")

# Save results
results = {
    "kaizen": "gungnir_v51_heimdahl_redteam",
    "timestamp": datetime.now().isoformat(),
    "test_split": {
        "n_train_val": len(trainval_indices),
        "n_test": len(test_indices),
        "test_positive_rate": float(np.mean(y_test))
    },
    "v49_baseline": {
        "test_auc": float(auc_v49),
        "test_brier": float(brier_v49),
        "seed_mean_auc": float(np.mean(auc_v49_seeds)),
        "seed_std_auc": float(np.std(auc_v49_seeds))
    },
    "v51_heimdahl": {
        "test_auc": float(auc_v51),
        "test_brier": float(brier_v51),
        "seed_mean_auc": float(np.mean(auc_v51_seeds)),
        "seed_std_auc": float(np.std(auc_v51_seeds))
    },
    "comparison": {
        "auc_delta": float(auc_delta),
        "auc_delta_pct": float(auc_delta/auc_v49*100),
        "brier_delta": float(brier_delta),
        "brier_delta_pct": float(brier_delta/brier_v49*100),
        "v51_wins_out_of_20": int(np.sum(auc_v51_seeds > auc_v49_seeds)),
        "paired_t_stat": float(t_stat),
        "paired_t_pvalue": float(p_value)
    },
    "features": {
        "v49_baseline": available_features,
        "v51_added": ["heimdall_p"]
    }
}

with open(OUTPUT_PATH, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n[v51 KAIZEN] Results saved to {OUTPUT_PATH}")

# Print final verdict
print(f"\n" + "="*60)
print(f"VERDICT: {'HEIMDAHL IMPROVES v49' if auc_delta > 0.001 else 'HEIMDAHL DOES NOT IMPROVE v49'}")
print(f"  AUC: {auc_v49:.4f} → {auc_v51:.4f} ({auc_delta:+.4f})")
print(f"  Stability: {np.sum(auc_v51_seeds > auc_v49_seeds)}/20 seeds favor v51 (p={p_value:.4e})")
print(f"="*60)
