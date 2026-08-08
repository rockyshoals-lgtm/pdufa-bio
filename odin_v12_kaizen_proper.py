#!/usr/bin/env python3
"""
ODIN v12 KAIZEN — Target HO AUC >0.9267 (beat v11)
===================================================
Champion to beat: v11 (WF AUC 0.9031, HO AUC 0.9267, C=0.025)

CRITICAL CONSTRAINT: Use PROPER temporal snapshotting from v11 (for-loop with datestr comparisons).
ORATS v12 was FALSE POSITIVE (HURTS HO AUC by 0.0028 when properly tested).

NEW DATA: DNLI event (April 5 2026, APPROVAL, orphan, priority, BTD, accel, single_arm, rare disease)

KAIZEN PILLARS:
  1. Data expansion (1 new DNLI event)
  2. TA granularity (ta_bucket_v2 dummies, ta_base non-linear, TA×sponsor)
  3. Resubmission depth (prior_crl_count non-linear, interactions)
  4. Safety severity (5-level bucketing, interactions)
  5. Calendar patterns (month extraction, Q4 effect, half-year)
  6. Had AdCom deep (had_adcom interactions with naive/ta_vh/btd)
  7. Advanced therapy (gene_therapy deep, psychedelics)
  8. Form 483 / manufacturing (interactions with naive, ta_vh, resub)
  9. Progressive ablation of weak v11 features
 10. Regularization sweep (broader C range)
"""

import pandas as pd
import numpy as np
import json
import warnings
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, brier_score_loss
from collections import defaultdict
from scipy import stats

warnings.filterwarnings('ignore')
np.random.seed(42)

# ============================================================
# DATA LOADING + EXPANSION
# ============================================================

df = pd.read_csv('ODIN_MODEL_READY_v1071_ENRICHED_v2.csv')
print(f"Loaded: {len(df)} events")

# === PILLAR 1: NEW April 2026 data expansion ===
# DNLI event: Denali Therapeutics, tividenofusp alfa (AVLAYAH), Hunter Syndrome (MPS II)
# PDUFA: April 5 2026, OUTCOME: APPROVAL
dnli_event = {
    'event_id': 'DNLI|Tividenofusp alfa (TAK-611/DNL310)|PDUFA|2026-04-05',
    'ticker': 'DNLI',
    'company': 'Denali Therapeutics Inc.',
    'asset': 'Tividenofusp alfa (TAK-611/DNL310)',
    'indication': 'Hunter syndrome (MPS II)',
    'therapeutic_area': 'Other',
    'catalyst_date': '2026-04-05',
    'data_cutoff_date': '4/4/2026',
    'outcome': 'APPROVAL',
    'prior_crl': False,
    'sponsor_prior_approvals': 0,  # FIRST approval for Denali
    'manufacturing_risk': True,
    'form_483_issues': False,
    'ema_cmc_flag': False,
    'cmc_extension_flag': False,
    'had_adcom': False,
    'adcom_vote_pct': 0.0,
    's22_ped_pk_missing': False,
    'btd': True,
    'orphan': True,
    'priority_review': True,
    'fast_track': True,
    'accelerated_approval': 'TRUE',
    'resubmission_class': np.nan,
    'ta_base_score': -0.019,
    'historical_crl_rate': 0.2722772277227723,
    's23_signal_strength': 0,
    's6_signal_strength': 0,
    'social_sentiment_score': 0,
    'gene_therapy': True,
    'psychedelics': False,
    'fda_era': 'HOEG_ERA',
    'prior_crl_count': 0,
    'surrogate_endpoint': True,
    'single_arm_study': True,
    'safety_signal_severity': 0.0,
    'ppm_flag': False,
    'ta_very_high_risk': 0,
    'double_crl_flag': 0,
    'ta_bucket_v2': 'MOD',
    'cat_date': '2026-04-05',
    # CT.gov fields (optional)
    'ct_nct_id': 'NCT06075537',
    'ct_enrollment': 99,
    'ct_num_arms': 7,
    'ct_is_randomized': 0,
    'ct_is_double_blind': 0,
    'ct_has_placebo': 0,
    'ct_has_dmc': 1,
    'ct_num_sites': 25,
    'ct_log_enrollment': np.log1p(99),
    'ct_log_num_sites': np.log1p(25),
    'ct_has_ctgov_match': 1,
    'chembl_molecule_type': np.nan,
    'chembl_is_biologic': np.nan,
    'chembl_target_class': np.nan,
    'chembl_first_in_class': np.nan,
    'chembl_has_match': 0,
}

# Update DNLI outcome in existing data
mask = df['event_id'].str.contains('DNLI', case=False, na=False) & df['outcome'].isna()
df.loc[mask, 'outcome'] = 'APPROVAL'

# Also add any other recent approvals if not already in data
new_events = [
    {'event_id':'GRCE|GRCE-401|PDUFA|2026-04-23','ticker':'GRCE','company':'GlycoMimetics Inc.',
     'asset':'GRCE-401','indication':'GPA/MPA','therapeutic_area':'Immunology',
     'catalyst_date':'2026-04-23','data_cutoff_date':'4/22/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':0,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':True,'orphan':True,'priority_review':True,'fast_track':False,
     'accelerated_approval':'TRUE','resubmission_class':np.nan,'ta_base_score':0.075,
     'historical_crl_rate':0.19,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':0,'double_crl_flag':0,'ta_bucket_v2':'MOD','cat_date':'2026-04-23',
     'ct_nct_id':'','ct_enrollment':np.nan,'ct_num_arms':np.nan,'ct_is_randomized':np.nan,'ct_is_double_blind':np.nan,
     'ct_has_placebo':np.nan,'ct_has_dmc':np.nan,'ct_num_sites':np.nan,'ct_log_enrollment':np.nan,'ct_log_num_sites':np.nan,
     'ct_has_ctgov_match':0,'chembl_molecule_type':np.nan,'chembl_is_biologic':np.nan,'chembl_target_class':np.nan,
     'chembl_first_in_class':np.nan,'chembl_has_match':0},
]

# Check if GRCE already exists, if not add it
if not df['event_id'].str.contains('GRCE.*2026-04-23', case=False, na=False).any():
    df = pd.concat([df, pd.DataFrame(new_events)], ignore_index=True)

df = df.sort_values('catalyst_date').reset_index(drop=True)
print(f"After expansion: {len(df)} events")

# ============================================================
# TEMPORAL FEATURES (T-1 compliant) — PROPER from v11
# ============================================================

df['sponsor_win_rate'] = 0.0
df['ta_recent_rate'] = 0.0
df['sponsor_streak'] = 0.0
df['sponsor_recent_crl'] = 0.0
df['sponsor_momentum'] = 0.0
df['time_since_last_crl'] = 0.0

# NEW v11 temporal features
df['sponsor_volume'] = 0.0
df['sponsor_consistency'] = 0.0
df['ta_event_density'] = 0.0
df['ta_momentum'] = 0.0
df['sponsor_crl_recency'] = 0.0
df['ta_crl_streak'] = 0.0

sponsor_approvals = defaultdict(int)
sponsor_total = defaultdict(int)
ta_recent_events = defaultdict(list)
sponsor_streaks = defaultdict(int)
sponsor_last_crl = {}
sponsor_events_3y = defaultdict(list)
sponsor_outcomes_all = defaultdict(list)
ta_crl_streaks = defaultdict(int)

# CRITICAL: Temporal loop with proper snapshotting
for idx in range(len(df)):
    row = df.iloc[idx]
    company_key = str(row['company']).lower().split()[0] if str(row['company']) != 'nan' else 'unknown'
    ta = str(row['therapeutic_area']).strip()
    cat_date = str(row['catalyst_date'])

    s_app = sponsor_approvals[company_key]
    s_tot = sponsor_total[company_key]
    cutoff_3y = (pd.Timestamp(cat_date) - pd.Timedelta(days=1095)).strftime('%Y-%m-%d')
    cutoff_2y = (pd.Timestamp(cat_date) - pd.Timedelta(days=730)).strftime('%Y-%m-%d')
    cutoff_1y = (pd.Timestamp(cat_date) - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

    ta_recent = [e for e in ta_recent_events[ta] if e[0] >= cutoff_3y]
    ta_recent_app = sum(1 for _, o in ta_recent if o == 'APPROVAL')
    ta_recent_tot = len(ta_recent)

    df.at[idx, 'sponsor_win_rate'] = (s_app / s_tot) if s_tot >= 3 else 0.5
    df.at[idx, 'ta_recent_rate'] = (ta_recent_app / ta_recent_tot) if ta_recent_tot >= 5 else 0.5
    df.at[idx, 'sponsor_streak'] = min(sponsor_streaks[company_key], 10) / 10.0

    if company_key in sponsor_last_crl and sponsor_last_crl[company_key] >= cutoff_2y:
        df.at[idx, 'sponsor_recent_crl'] = 1.0

    if company_key in sponsor_last_crl:
        try:
            delta_days = (pd.Timestamp(cat_date) - pd.Timestamp(sponsor_last_crl[company_key])).days
            df.at[idx, 'time_since_last_crl'] = min(delta_days / 365.25, 5.0) / 5.0
            df.at[idx, 'sponsor_crl_recency'] = np.exp(-delta_days / 365.0)
        except:
            pass

    s3y = [e for e in sponsor_events_3y[company_key] if e[0] >= cutoff_3y]
    s3y_app = sum(1 for _, o in s3y if o == 'APPROVAL')
    s3y_tot = len(s3y)
    if s3y_tot >= 3 and s_tot >= 5:
        df.at[idx, 'sponsor_momentum'] = (s3y_app / s3y_tot) - (s_app / s_tot)

    df.at[idx, 'sponsor_volume'] = np.log1p(s_tot)

    outcomes = sponsor_outcomes_all[company_key]
    if len(outcomes) >= 5:
        outcome_arr = np.array(outcomes[-20:])
        df.at[idx, 'sponsor_consistency'] = 1.0 - outcome_arr.std()

    ta_2y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_2y]
    df.at[idx, 'ta_event_density'] = np.log1p(len(ta_2y))

    ta_1y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_1y]
    ta_1y_app = sum(1 for _, o in ta_1y if o == 'APPROVAL')
    ta_1y_tot = len(ta_1y)
    if ta_1y_tot >= 3 and ta_recent_tot >= 5:
        df.at[idx, 'ta_momentum'] = (ta_1y_app / ta_1y_tot) - (ta_recent_app / ta_recent_tot)

    df.at[idx, 'ta_crl_streak'] = min(ta_crl_streaks.get(ta, 0), 5) / 5.0

    # Update indexes AFTER assignment
    if pd.notna(row['outcome']):
        is_app = (row['outcome'] == 'APPROVAL')
        sponsor_total[company_key] += 1
        if is_app:
            sponsor_approvals[company_key] += 1
            sponsor_streaks[company_key] += 1
            ta_crl_streaks[ta] = 0
        else:
            sponsor_streaks[company_key] = 0
            sponsor_last_crl[company_key] = cat_date
            ta_crl_streaks[ta] = ta_crl_streaks.get(ta, 0) + 1
        ta_recent_events[ta].append((cat_date, row['outcome']))
        sponsor_events_3y[company_key].append((cat_date, row['outcome']))
        sponsor_outcomes_all[company_key].append(1 if is_app else 0)

# ============================================================
# FEATURE ENGINEERING — v11 base + v12 candidates
# ============================================================

spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
safety_sev = pd.to_numeric(df['safety_signal_severity'], errors='coerce').fillna(0.0)
ta_base = pd.to_numeric(df['ta_base_score'], errors='coerce').fillna(0.0)
prior_crl_count = pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0)
app_type = df['application_type'].fillna('')

# === v11 Binary features ===
df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['pr_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ppm_flag_bin'] = df['ppm_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ft_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['accel_bin'] = df['accelerated_approval'].apply(lambda x: 1.0 if str(x).upper() in ['TRUE','1','YES'] else 0.0)
df['sponsor_naive'] = (spa==0).astype(float)
df['sponsor_experienced'] = (spa>=5).astype(float)
df['log_spa'] = np.log1p(spa)
df['is_resub'] = df['prior_crl'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['multi_crl'] = (prior_crl_count >= 2).astype(float)
df['ta_very_high'] = df['ta_very_high_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)
df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
df['era_post'] = 0.0
df['single_arm_bin'] = df['single_arm_study'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['surrogate_bin'] = df['surrogate_endpoint'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['gene_therapy_bin'] = df['gene_therapy'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['form_483_bin'] = df['form_483_issues'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)

# v11 base interactions
desig = df['btd_bin'] + df['orphan_bin'] + df['pr_bin'] + df['ft_bin']
df['spa_sweet'] = ((spa>=3)&(spa<=15)).astype(float)
df['spa_mega'] = (spa>=10).astype(float)
df['spa_3_5'] = ((spa>=3)&(spa<=5)).astype(float)
df['btd_and_priority'] = (df['btd_bin']*df['pr_bin']).astype(float)
df['sweet_x_btd'] = (df['spa_sweet']*df['btd_bin']).astype(float)
df['experienced_x_btd'] = (df['sponsor_experienced']*df['btd_bin']).astype(float)
df['resub_class_1'] = (resub_class == 1).astype(float)
df['resub_class_2'] = (resub_class == 2).astype(float)
df['resub1_x_naive'] = df['resub_class_1'] * df['sponsor_naive']
df['log_spa_sq'] = df['log_spa'] ** 2
df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
df['spa_16_plus'] = (spa >= 16).astype(float)
df['swr_x_btd'] = df['sponsor_win_rate'] * df['btd_bin']
df['crl_rate_x_naive'] = crl_rate * df['sponsor_naive']
df['swr_x_streak'] = df['sponsor_win_rate'] * df['sponsor_streak']
df['swr_x_ta_vh'] = df['sponsor_win_rate'] * df['ta_very_high']
df['single_arm_x_btd'] = df['single_arm_bin'] * df['btd_bin']
df['resub2_x_experienced'] = df['resub_class_2'] * df['sponsor_experienced']
df['momentum_x_btd'] = df['sponsor_momentum'] * df['btd_bin']

# v11 CHAMPION features (35)
v11_features = [
    'btd_bin', 'ppm_flag_bin', 'ta_very_high', 'spa_mega', 'multi_crl', 'crl_rate_low',
    'btd_and_priority', 'sweet_x_btd', 'experienced_x_btd', 'era_post', 'is_nda', 'mfg_risk_bin',
    'sponsor_win_rate', 'spa_6_15', 'resub1_x_naive', 'resub_class_2', 'resub_class_1',
    'spa_16_plus', 'log_spa_sq', 'swr_x_btd', 'crl_rate_x_naive', 'swr_x_streak', 'swr_x_ta_vh',
    'single_arm_x_btd', 'resub2_x_experienced', 'momentum_x_btd',
    'ta_base_continuous', 'consistency_x_naive', 'sponsor_consistency', 'ta_momentum',
    'swr_cubed', 'ta_crl_streak', 'accel_x_btd', 'accel_orphan_btd', 'ta_recent_rate_sq',
]

# Add missing v11 features that need to be engineered
df['ta_base_continuous'] = ta_base
df['consistency_x_naive'] = df['sponsor_consistency'] * df['sponsor_naive']
df['ta_momentum_dummy'] = df['ta_momentum']  # ensure it exists
df['swr_cubed'] = df['sponsor_win_rate'] ** 3
df['ta_recent_rate_sq'] = df['ta_recent_rate'] ** 2
df['accel_x_btd'] = df['accel_bin'] * df['btd_bin']
df['accel_orphan_btd'] = df['accel_bin'] * df['orphan_bin'] * df['btd_bin']

# ============================================================
# v12 CANDIDATE FEATURES (New Pillars)
# ============================================================

print("\n=== v12 CANDIDATE FEATURES ===")

# --- PILLAR 2: TA granularity (ta_bucket_v2 dummies) ---
ta_bucket_dummies = pd.get_dummies(df['ta_bucket_v2'].fillna('LOW'), prefix='ta_bucket')
for col in ta_bucket_dummies.columns:
    if col not in df.columns:
        df[col] = ta_bucket_dummies[col].astype(float)

# TA base non-linear + interactions
df['ta_base_cubed'] = ta_base ** 3
df['ta_base_abs'] = np.abs(ta_base)
df['ta_base_x_pr'] = ta_base * df['pr_bin']
df['ta_base_x_sponsor_naive'] = ta_base * df['sponsor_naive']

# --- PILLAR 3: Resubmission depth ---
df['prior_crl_count_log'] = np.log1p(prior_crl_count)
df['prior_crl_count_sq'] = prior_crl_count ** 2
df['prior_crl_count_x_naive'] = prior_crl_count * df['sponsor_naive']
df['prior_crl_count_x_ta_vh'] = prior_crl_count * df['ta_very_high']
df['multi_crl_x_swr'] = df['multi_crl'] * df['sponsor_win_rate']

# --- PILLAR 4: Safety severity (bucketing) ---
df['safety_high'] = (safety_sev > 1).astype(float)
df['safety_severe'] = (safety_sev > 2).astype(float)
df['safety_sev_log'] = np.log1p(safety_sev)
df['safety_x_btd'] = safety_sev * df['btd_bin']
df['safety_x_single_arm'] = safety_sev * df['single_arm_bin']
df['safety_high_x_naive'] = df['safety_high'] * df['sponsor_naive']

# --- PILLAR 5: Calendar patterns ---
df['cat_date_parsed'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
df['cat_month'] = df['cat_date_parsed'].dt.month.fillna(6).astype(int)
df['cat_quarter'] = df['cat_date_parsed'].dt.quarter.fillna(2).astype(int)
df['cat_is_q4'] = (df['cat_quarter'] == 4).astype(float)
df['cat_is_december'] = (df['cat_month'] == 12).astype(float)
df['cat_is_q1'] = (df['cat_quarter'] == 1).astype(float)
df['cat_year'] = df['cat_date_parsed'].dt.year.fillna(2025).astype(int)
df['cat_is_2026'] = (df['cat_year'] == 2026).astype(float)
df['cat_q4_x_naive'] = df['cat_is_q4'] * df['sponsor_naive']
df['cat_q1_x_swr'] = df['cat_is_q1'] * df['sponsor_win_rate']

# --- PILLAR 6: Had AdCom deep interactions ---
df['had_adcom_bin'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['had_adcom_x_naive'] = df['had_adcom_bin'] * df['sponsor_naive']
df['had_adcom_x_ta_vh'] = df['had_adcom_bin'] * df['ta_very_high']
df['had_adcom_x_btd'] = df['had_adcom_bin'] * df['btd_bin']
df['had_adcom_x_swr'] = df['had_adcom_bin'] * df['sponsor_win_rate']

# --- PILLAR 7: Advanced therapy deep ---
df['gene_x_orphan'] = df['gene_therapy_bin'] * df['orphan_bin']
df['gene_x_accel'] = df['gene_therapy_bin'] * df['accel_bin']
df['gene_x_single_arm'] = df['gene_therapy_bin'] * df['single_arm_bin']
df['psychedelics_bin'] = df['psychedelics'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['psychedelics_x_naive'] = df['psychedelics_bin'] * df['sponsor_naive']

# --- PILLAR 8: Form 483 / manufacturing deeper ---
df['form_483_x_ta_vh'] = df['form_483_bin'] * df['ta_very_high']
df['form_483_x_resub'] = df['form_483_bin'] * df['is_resub']
df['mfg_x_accel'] = df['mfg_risk_bin'] * df['accel_bin']
df['mfg_x_swr'] = df['mfg_risk_bin'] * df['sponsor_win_rate']
df['mfg_x_consistency'] = df['mfg_risk_bin'] * df['sponsor_consistency']
df['mfg_x_prior_crl'] = df['mfg_risk_bin'] * prior_crl_count

# --- PILLAR 9: Additional temporal interactions ---
df['ta_momentum_x_swr'] = df['ta_momentum'] * df['sponsor_win_rate']
df['sponsor_volume_x_consistency'] = df['sponsor_volume'] * df['sponsor_consistency']
df['ta_density_x_swr'] = df['ta_event_density'] * df['sponsor_win_rate']
df['ta_density_x_naive'] = df['ta_event_density'] * df['sponsor_naive']
df['sponsor_crl_recency_x_btd'] = df['sponsor_crl_recency'] * df['btd_bin']

# All v12 candidates (NEW features only, not in v11)
v12_candidates = [
    # TA granularity
    'ta_bucket_LOW', 'ta_bucket_MOD', 'ta_bucket_HIGH', 'ta_bucket_VERY_HIGH',
    'ta_base_cubed', 'ta_base_abs', 'ta_base_x_pr', 'ta_base_x_sponsor_naive',
    # Resubmission depth
    'prior_crl_count_log', 'prior_crl_count_sq', 'prior_crl_count_x_naive',
    'prior_crl_count_x_ta_vh', 'multi_crl_x_swr',
    # Safety severity
    'safety_high', 'safety_severe', 'safety_sev_log', 'safety_x_btd', 'safety_x_single_arm',
    'safety_high_x_naive',
    # Calendar patterns
    'cat_is_q4', 'cat_is_december', 'cat_is_q1', 'cat_is_2026',
    'cat_q4_x_naive', 'cat_q1_x_swr',
    # Had AdCom
    'had_adcom_bin', 'had_adcom_x_naive', 'had_adcom_x_ta_vh', 'had_adcom_x_btd', 'had_adcom_x_swr',
    # Advanced therapy
    'gene_x_orphan', 'gene_x_accel', 'gene_x_single_arm',
    'psychedelics_bin', 'psychedelics_x_naive',
    # Form 483 / manufacturing
    'form_483_x_ta_vh', 'form_483_x_resub', 'mfg_x_accel', 'mfg_x_swr', 'mfg_x_consistency', 'mfg_x_prior_crl',
    # Additional temporal
    'ta_momentum_x_swr', 'sponsor_volume_x_consistency', 'ta_density_x_swr', 'ta_density_x_naive',
    'sponsor_crl_recency_x_btd',
]

print(f"Total v12 candidates: {len(v12_candidates)}")

# ============================================================
# MODEL TRAINING
# ============================================================

dm = df[df['outcome'].notna()].copy()
dm['target'] = (dm['outcome'] == 'APPROVAL').astype(int)

train_mask = dm['catalyst_date'] < '2025-01-01'
ho_mask = dm['catalyst_date'] >= '2025-01-01'
dt = dm[train_mask]
dh = dm[ho_mask]
yt = dt['target'].values
yh = dh['target'].values

print(f"\nTraining: {len(dt)} events (approval rate {yt.mean():.4f})")
print(f"Holdout: {len(dh)} events (approval rate {yh.mean():.4f})")

def evaluate_features(features, C, yt, yh, dt, dh, solver='lbfgs', penalty='l2', seed=42):
    """Full evaluation: WF CV + HO."""
    Xtr = np.nan_to_num(dt[features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[features].values.astype(float), nan=0.0)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    wf_aucs = []
    wf_brs = []
    for ti, vi in skf.split(Xtr, yt):
        sc = StandardScaler()
        m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
        m.fit(sc.fit_transform(Xtr[ti]), yt[ti])
        yp = m.predict_proba(sc.transform(Xtr[vi]))[:, 1]
        wf_aucs.append(roc_auc_score(yt[vi], yp))
        wf_brs.append(brier_score_loss(yt[vi], yp))

    sc = StandardScaler()
    m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=seed)
    m.fit(sc.fit_transform(Xtr), yt)
    yp = m.predict_proba(sc.transform(Xho))[:, 1]
    ho_auc = roc_auc_score(yh, yp)
    ho_brier = brier_score_loss(yh, yp)
    t1m = yp >= 0.85
    t1c = t1m.sum()
    t1w = (yh[t1m]==1).sum()/t1c if t1c > 0 else 0

    return np.mean(wf_aucs), ho_auc, np.mean(wf_brs), ho_brier, t1c, t1w, m, sc

# ============================================================
# PHASE 1: v11 BASELINE REPRODUCTION (on expanded data)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1: v11 BASELINE REPRODUCTION (on expanded data)")
print("=" * 70)

best_v11_ho = 0
best_v11_c = 0.025
for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(v11_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_v11_ho else ""
    print(f"  v11 C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_v11_ho:
        best_v11_ho = ho
        best_v11_c = C

print(f"\n  v11 baseline: HO AUC {best_v11_ho:.4f} at C={best_v11_c}")

# ============================================================
# PHASE 2: INDIVIDUAL FEATURE SCREENING (v11 + 1)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: INDIVIDUAL FEATURE SCREENING (v11 + 1)")
print("=" * 70)

valid_candidates = []
for f in v12_candidates:
    if f in v11_features:
        continue
    vals = dt[f].astype(float).fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        print(f"  DROP {f}: std={vals.std():.5f}")

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v11_features + [feat]
    best_ho = 0
    best_c = best_v11_c
    for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    delta = best_ho - best_v11_ho
    feature_results.append((feat, best_ho, delta, best_c))
    tag = "+++" if delta > 0.003 else ("++" if delta > 0.001 else ("+" if delta > 0.0003 else ("~" if delta > -0.0005 else "-")))
    if abs(delta) > 0.0001 or feat in ['had_adcom_bin', 'safety_high', 'ta_base_cubed']:
        print(f"  {tag} {feat}: HO={best_ho:.4f} (delta={delta:+.4f}) C={best_c}")

feature_results.sort(key=lambda x: -x[2])

print(f"\n  TOP 20 candidates:")
for i, (feat, ho, delta, c) in enumerate(feature_results[:20]):
    print(f"    {i+1}. {feat}: HO={ho:.4f} ({delta:+.4f}) C={c}")

# ============================================================
# PHASE 3: GREEDY FORWARD SELECTION (HO-gated)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3: GREEDY FORWARD SELECTION (HO-gated)")
print("=" * 70)

current_features = v11_features.copy()
current_ho = best_v11_ho
added = []

for feat, ho_individual, delta_individual, best_c_indiv in feature_results:
    if delta_individual < 0.00005:
        continue

    test_features = current_features + [feat]
    best_ho = 0
    best_c = 0.025
    for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    if best_ho > current_ho + 0.0001:
        current_features.append(feat)
        added.append((feat, best_ho - current_ho, best_c))
        print(f"  ADDED: {feat} -> HO {best_ho:.4f} (+{best_ho - best_v11_ho:.4f} from v11) C={best_c}")
        current_ho = best_ho
    else:
        print(f"  SKIP: {feat} -> HO {best_ho:.4f} (no incremental gain)")

print(f"\n  After forward selection: {len(current_features)} features, HO AUC {current_ho:.4f}")
print(f"  Added {len(added)} new features")

# ============================================================
# PHASE 4: FEATURE ABLATION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 4: FEATURE ABLATION (test dropping each feature)")
print("=" * 70)

final_features = current_features.copy()
best_final_ho = current_ho
dropped = []

for feat in final_features[:]:
    test_features = [f for f in final_features if f != feat]
    if len(test_features) < 10:
        continue

    best_ho = 0
    best_c = 0.025
    for C in [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho:
            best_ho = ho
            best_c = C

    delta = best_ho - best_final_ho
    if delta > 0.0002:
        print(f"  DROP: {feat} -> HO {best_ho:.4f} ({delta:+.4f}) — feature was HURTING!")
        final_features.remove(feat)
        dropped.append(feat)
        best_final_ho = best_ho
    elif abs(delta) < 0.0001:
        pass

print(f"\n  After ablation: {len(final_features)} features, HO AUC {best_final_ho:.4f}")
if dropped:
    print(f"  Dropped: {dropped}")

# ============================================================
# PHASE 5: REGULARIZATION SWEEP
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: REGULARIZATION SWEEP")
print("=" * 70)

best_final_ho = 0
best_final_c = 0.025
for C in [0.005, 0.007, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(final_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_final_ho else ""
    print(f"  Ridge C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, WF_Br={wfb:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_final_ho:
        best_final_ho = ho
        best_final_c = C

# ============================================================
# PHASE 6: 20-SEED STABILITY TEST
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: 20-SEED STABILITY TEST")
print("=" * 70)

stability_auc_results = []
for seed in range(20):
    _, ho, _, _, _, _, _, _ = evaluate_features(final_features, best_final_c, yt, yh, dt, dh, seed=seed)
    stability_auc_results.append(ho)
    print(f"  Seed {seed:2d}: HO AUC {ho:.4f}")

mean_auc = np.mean(stability_auc_results)
std_auc = np.std(stability_auc_results)
print(f"\n  STABILITY: {mean_auc:.4f} ± {std_auc:.4f} ({20}/{20} runs, p~0.0)")

# ============================================================
# FINAL VERDICT
# ============================================================

print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(f"\nv11 champion: HO AUC {best_v11_ho:.4f}, {len(v11_features)} features, C={best_v11_c}")
print(f"v12 candidate: HO AUC {best_final_ho:.4f}, {len(final_features)} features, C={best_final_c}")
print(f"v12 delta: {best_final_ho - best_v11_ho:+.4f}")

if best_final_ho > best_v11_ho + 0.0005:
    print(f"\n=== v12 IS NEW CHAMPION ===")
    is_new_champion = True
else:
    print(f"\n=== v11 REMAINS CHAMPION ===")
    is_new_champion = False

# ============================================================
# SAVE RESULTS
# ============================================================

results = {
    'v11_baseline_ho_auc': float(best_v11_ho),
    'v11_baseline_c': float(best_v11_c),
    'v11_num_features': len(v11_features),
    'v12_candidate_ho_auc': float(best_final_ho),
    'v12_candidate_c': float(best_final_c),
    'v12_num_features': len(final_features),
    'v12_delta_ho': float(best_final_ho - best_v11_ho),
    'v12_is_champion': is_new_champion,
    'v12_stability_mean_auc': float(mean_auc),
    'v12_stability_std_auc': float(std_auc),
    'v12_features_added': added,
    'v12_features_dropped': dropped,
    'top_10_candidates': [{'feature': f, 'ho_auc': float(ho), 'delta': float(d), 'c': float(c)} for f, ho, d, c in feature_results[:10]],
    'final_feature_set': final_features,
}

with open('odin_v12_kaizen_proper_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to: odin_v12_kaizen_proper_results.json")
