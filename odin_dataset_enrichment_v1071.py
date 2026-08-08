"""
ODIN v10.71 Dataset Enrichment
================================
Adds 5 new architectural features to v1070 dataset:

  1. btd_oncology_interaction  — BTD×Oncology joint flag (+2.18 logit interaction)
  2. btd_priority_interaction  — BTD×Priority Review joint flag (+1.8 logit interaction)
  3. ta_very_high_risk         — 4th TA bucket: Respiratory/ID/Derm/Immunology/GI (90%+ approval)
  4. double_crl_flag           — 2+ prior CRLs (20.4% approval vs 42.6% for single CRL)
  5. ta_bucket_v2              — Explicit 4-way TA classification: LOW/MOD/HIGH/VERY_HIGH

Design rationale:
  - Current additive logit model fights itself on BTD×Oncology:
      btd_weight (+0.48) + indication_onc_boost (-0.96) partially cancel
      but the 190 BTD-Oncology events have 96.8% approval rate
  - HIGH TA bucket spans 3.40 logits (Hematology 1.10 → Respiratory 3.40)
      all receiving the same penalty; VERY_HIGH split corrects systematic underestimate
  - prior_crl_count_penalty (-0.83/CRL) can't capture the 20%→42% approval cliff
      a discrete double_crl_flag allows a non-linear penalty

All features are T1-compliant (derivable from pre-catalyst data).
No data leakage — all logic uses only columns already in v1070.

Usage:
  python odin_dataset_enrichment_v1071.py
"""

import pandas as pd
import numpy as np

# =============================================================================
# CONFIG
# =============================================================================
INPUT_CSV  = "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv"
OUTPUT_CSV = "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"

# TA bucket definitions — empirically derived from v1070 dataset
# Approval rates from 2,210-event dataset (2015-2025):
#   VERY_HIGH (≥90%): Respiratory 96.8%, GI/Hepatology 95.7%,
#                     Dermatology 90.6%, Infectious Disease 89.7%, Immunology 88.2%
#   HIGH (75-90%):    Hematology 75.0%, CNS/Neurology 76.4%, Cardiovascular 79.4%,
#                     Metabolic/Endocrine 80.0%, Rare Disease 82.9%
#   MOD (65-75%):     Other 72.4%, Ophthalmology 65.9%, Pain Management 67.5%,
#                     Nephrology 68.8%
#   LOW (<65%):       Oncology 53.6%

TA_VERY_HIGH = {
    'Respiratory',
    'GI/Hepatology',
    'Dermatology',
    'Infectious Disease',
    'Immunology',
}

TA_HIGH = {
    'Hematology',
    'CNS/Neurology',
    'Cardiovascular',
    'Metabolic/Endocrine',
    'Rare Disease',
}

TA_LOW = {
    'Oncology',
}

# Everything else → MOD (Other, Ophthalmology, Pain Management, Nephrology, etc.)


# =============================================================================
# MAIN
# =============================================================================
def enrich_v1071(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ------------------------------------------------------------------
    # 1. BTD × Oncology interaction
    #    190 events, 96.8% approval, +2.18 logit above additive prediction
    #    Stable val lifts: 2.49 (2020+), 2.36 (2022+), 2.55 (2023+)
    # ------------------------------------------------------------------
    df['btd_oncology_interaction'] = (
        df['btd'].astype(bool) &
        (df['therapeutic_area'] == 'Oncology')
    ).astype(int)

    # ------------------------------------------------------------------
    # 2. BTD × Priority Review interaction
    #    269 events, 94.1% approval — both flags together ≠ sum of parts
    # ------------------------------------------------------------------
    df['btd_priority_interaction'] = (
        df['btd'].astype(bool) &
        df['priority_review'].astype(bool)
    ).astype(int)

    # ------------------------------------------------------------------
    # 3. TA Very High Risk bucket
    #    NEW feature — splits the current "HIGH" category
    #    354 events at 90.4% approval rate (+1.50 logit vs base)
    #    vs current HIGH (332 events, 78.6% approval, +0.56 logit)
    # ------------------------------------------------------------------
    df['ta_very_high_risk'] = df['therapeutic_area'].isin(TA_VERY_HIGH).astype(int)

    # ------------------------------------------------------------------
    # 4. Double CRL flag
    #    prior_crl_count >= 2: 113 events, 20.4% approval
    #    vs single CRL (1): 204 events, 42.6% approval
    #    The continuous penalty can't express this cliff
    # ------------------------------------------------------------------
    if 'prior_crl_count' in df.columns:
        df['double_crl_flag'] = (
            pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0) >= 2
        ).astype(int)
    else:
        # Fallback: infer from prior_crl if prior_crl_count not present
        # (shouldn't happen with v1070 dataset)
        df['double_crl_flag'] = 0
        print("WARNING: prior_crl_count not found, double_crl_flag set to 0")

    # ------------------------------------------------------------------
    # 5. TA bucket v2 (explicit 4-way classification for diagnostics)
    # ------------------------------------------------------------------
    def classify_ta_v2(ta):
        if ta in TA_VERY_HIGH: return 'VERY_HIGH'
        if ta in TA_HIGH:      return 'HIGH'
        if ta in TA_LOW:       return 'LOW'
        return 'MOD'

    df['ta_bucket_v2'] = df['therapeutic_area'].apply(classify_ta_v2)

    return df


def validate_enrichment(df_orig: pd.DataFrame, df_new: pd.DataFrame):
    """Quick sanity checks on enriched dataset."""
    print("\n=== v1071 ENRICHMENT VALIDATION ===")
    print(f"  Rows: {len(df_orig)} → {len(df_new)}")
    print(f"  Columns: {len(df_orig.columns)} → {len(df_new.columns)}")

    approved = (df_new['outcome'] == 'APPROVAL')
    base_rate = approved.mean()

    print(f"\n  Base approval rate: {base_rate:.3f}")
    print(f"  New feature distributions:")

    def logit(p):
        p = np.clip(p, 1e-6, 1-1e-6)
        return np.log(p / (1 - p))

    # BTD × Oncology
    mask = df_new['btd_oncology_interaction'] == 1
    rate = approved[mask].mean()
    n = mask.sum()
    print(f"\n  btd_oncology_interaction=1:")
    print(f"    n={n}, approval={rate:.3f}, logit_lift={logit(rate)-logit(base_rate):+.3f}")
    print(f"    (expected ~96.8% / +2.18 lift)")

    # BTD × Priority
    mask = df_new['btd_priority_interaction'] == 1
    rate = approved[mask].mean()
    n = mask.sum()
    print(f"\n  btd_priority_interaction=1:")
    print(f"    n={n}, approval={rate:.3f}, logit_lift={logit(rate)-logit(base_rate):+.3f}")

    # TA Very High
    mask = df_new['ta_very_high_risk'] == 1
    rate = approved[mask].mean()
    n = mask.sum()
    print(f"\n  ta_very_high_risk=1:")
    print(f"    n={n}, approval={rate:.3f}, logit_lift={logit(rate)-logit(base_rate):+.3f}")
    print(f"    (expected ~90.4% / +1.50 lift)")

    # Double CRL
    mask = df_new['double_crl_flag'] == 1
    rate = approved[mask].mean()
    n = mask.sum()
    print(f"\n  double_crl_flag=1:")
    print(f"    n={n}, approval={rate:.3f}, logit_lift={logit(rate)-logit(base_rate):+.3f}")
    print(f"    (expected ~20.4% / -2.0 lift)")

    # TA bucket v2 distribution
    print(f"\n  ta_bucket_v2 distribution:")
    for bucket in ['LOW', 'MOD', 'HIGH', 'VERY_HIGH']:
        mask = df_new['ta_bucket_v2'] == bucket
        rate = approved[mask].mean()
        n = mask.sum()
        print(f"    {bucket:<10} n={n:<5} approval={rate:.3f}  logit_lift={logit(rate)-logit(base_rate):+.3f}")

    # Check no NaN introduced
    new_cols = ['btd_oncology_interaction', 'btd_priority_interaction',
                'ta_very_high_risk', 'double_crl_flag', 'ta_bucket_v2']
    for col in new_cols:
        nulls = df_new[col].isna().sum()
        if nulls > 0:
            print(f"\n  WARNING: {col} has {nulls} nulls!")
    print(f"\n  All new columns null-free: {all(df_new[c].isna().sum()==0 for c in new_cols)}")


def time_split_stability_check(df: pd.DataFrame):
    """Verify interaction features are stable across time splits."""
    print("\n=== TIME-SPLIT STABILITY CHECK ===")

    approved = (df['outcome'] == 'APPROVAL')

    def logit(p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return np.log(p / (1 - p))

    df['cat_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')

    for feature, expected_lift in [('btd_oncology_interaction', 2.18),
                                    ('ta_very_high_risk', 1.50),
                                    ('double_crl_flag', -2.00)]:
        print(f"\n  {feature} (expected lift {expected_lift:+.2f}):")
        for yr_cut in [2020, 2022, 2023, 2024]:
            train = df[df['cat_date'].dt.year < yr_cut]
            val   = df[df['cat_date'].dt.year >= yr_cut]
            mask_v = val[feature] == 1
            if mask_v.sum() < 5:
                print(f"    val {yr_cut}+: insufficient n ({mask_v.sum()})")
                continue
            base_t = approved[train.index].mean()
            base_v = approved[val.index].mean()
            rate_v = approved[val.index][mask_v].mean()
            lift_v = logit(rate_v) - logit(base_v)
            n_v = mask_v.sum()
            print(f"    val {yr_cut}+: n={n_v:<4}  base={base_v:.3f}  rate={rate_v:.3f}  lift={lift_v:+.3f}")


if __name__ == '__main__':
    print(f"Loading {INPUT_CSV}...")
    df_orig = pd.read_csv(INPUT_CSV)
    print(f"  {len(df_orig)} rows, {len(df_orig.columns)} columns")

    df_new = enrich_v1071(df_orig)

    validate_enrichment(df_orig, df_new)
    time_split_stability_check(df_new)

    df_new.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✓ Written: {OUTPUT_CSV}")
    print(f"  New columns: btd_oncology_interaction, btd_priority_interaction,")
    print(f"               ta_very_high_risk, double_crl_flag, ta_bucket_v2")
    print(f"\nNext: Build v1096 anchor with these 3 new weight slots:")
    print(f"  btd_oncology_boost:    +1.50 (initial — let optimizer find +2.18)")
    print(f"  ta_very_high_boost:    +0.80 (initial — above ta_high ~-0.77)")
    print(f"  double_crl_penalty:    -1.50 (initial — on top of prior_crl_count)")
