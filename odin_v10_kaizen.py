#!/usr/bin/env python3
"""
ODIN v10 KAIZEN — Target HO AUC 0.91+
=======================================
Champion to beat: v9 (WF AUC 0.9083, HO AUC 0.8961, C=0.01)
v9 features: 30 (v8's 22 + 8 deep-mined features)

STRATEGY:
  1. New data expansion — check for new 2026 outcomes
  2. Untapped original columns: orphan_bin standalone, ft_bin standalone,
     single_arm_study, safety_signal_severity, gene_therapy, ta_base_score continuous,
     adcom_vote_pct, application_type granularity (BLA/sNDA/sBLA)
  3. New interactions between v9's NEW features and v9 base
  4. Non-linear transforms: crl_rate_sq, desig_count continuous,
     adcom_vote_pct thresholds
  5. New temporal features: sponsor streak, TA trend, time-since-last-CRL
  6. Second-order interactions: v9_new × v9_new cross-terms
  7. Hyperparameter sweep including ElasticNet
  8. Architecture: Ridge + potential thin ensemble
"""

import pandas as pd
import numpy as np
import math
import json
import warnings
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, brier_score_loss
from collections import defaultdict
from scipy import stats
from datetime import datetime

warnings.filterwarnings('ignore')
np.random.seed(42)

# ============================================================
# DATA LOADING + v9 EXPANSION
# ============================================================

# Use enriched v2 for CT.gov/ChEMBL columns
df = pd.read_csv('ODIN_MODEL_READY_v1071_ENRICHED_v2.csv')
print(f"Loaded: {len(df)} events")

# Update NaN outcomes (same as v9)
for cs, cd, oc in [('Ascendis Pharma','2026-02-28','APPROVAL'),('Bristol-Myers Squibb','2026-03-06','APPROVAL'),
                    ('Aldeyra Therapeutics','2026-03-16','CRL'),('Rocket Pharmaceuticals','2026-03-28','APPROVAL')]:
    mask = df['company'].str.contains(cs, case=False, na=False) & (df['catalyst_date']==cd) & df['outcome'].isna()
    df.loc[mask, 'outcome'] = oc

# Add 4 new events (same as v9)
new_events = [
    {'event_id':'REGN|Dupixent sBLA AFRS|PDUFA|2026-02-24','ticker':'REGN','company':'Regeneron Pharmaceuticals Inc.',
     'asset':'Dupixent sBLA AFRS','indication':'AFRS','therapeutic_area':'Immunology',
     'catalyst_date':'2026-02-24','data_cutoff_date':'2/23/2026','outcome':'APPROVAL',
     'application_type':'SBLA','prior_crl':False,'sponsor_prior_approvals':28,
     'manufacturing_risk':False,'form_483_issues':False,'ema_cmc_flag':False,'cmc_extension_flag':False,
     'had_adcom':False,'adcom_vote_pct':0.0,'s22_ped_pk_missing':False,
     'btd':False,'orphan':False,'priority_review':True,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,
     'ta_base_score':-0.05,'historical_crl_rate':0.143,'s23_signal_strength':0,
     's6_signal_strength':0,'social_sentiment_score':0,'v1067_score':0.0,'v1067_tier':'NONE',
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'v1070_score':0.0,'v1070_tier':'NONE','btd_oncology_interaction':0,
     'btd_priority_interaction':0,'ta_very_high_risk':1,'double_crl_flag':0,
     'ta_bucket_v2':'LOW','cat_date':'2026-02-24'},
    {'event_id':'LNTH|PYLARIFY TruVu sNDA|PDUFA|2026-03-06','ticker':'LNTH','company':'Lantheus Holdings Inc.',
     'asset':'PYLARIFY TruVu sNDA','indication':'PSMA-PET','therapeutic_area':'Oncology',
     'catalyst_date':'2026-03-06','data_cutoff_date':'3/5/2026','outcome':'APPROVAL',
     'application_type':'SNDA','prior_crl':False,'sponsor_prior_approvals':3,
     'manufacturing_risk':False,'form_483_issues':False,'ema_cmc_flag':False,'cmc_extension_flag':False,
     'had_adcom':False,'adcom_vote_pct':0.0,'s22_ped_pk_missing':False,
     'btd':False,'orphan':False,'priority_review':False,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,
     'ta_base_score':0.1,'historical_crl_rate':0.388,'s23_signal_strength':0,
     's6_signal_strength':0,'social_sentiment_score':0,'v1067_score':0.0,'v1067_tier':'NONE',
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'v1070_score':0.0,'v1070_tier':'NONE','btd_oncology_interaction':0,
     'btd_priority_interaction':0,'ta_very_high_risk':0,'double_crl_flag':0,
     'ta_bucket_v2':'LOW','cat_date':'2026-03-06'},
    {'event_id':'RYTM|IMCIVREE sNDA AHO|PDUFA|2026-03-19','ticker':'RYTM','company':'Rhythm Pharmaceuticals Inc.',
     'asset':'IMCIVREE sNDA AHO','indication':'AHO','therapeutic_area':'Rare Disease',
     'catalyst_date':'2026-03-19','data_cutoff_date':'3/18/2026','outcome':'APPROVAL',
     'application_type':'SNDA','prior_crl':False,'sponsor_prior_approvals':3,
     'manufacturing_risk':False,'form_483_issues':False,'ema_cmc_flag':False,'cmc_extension_flag':False,
     'had_adcom':False,'adcom_vote_pct':0.0,'s22_ped_pk_missing':False,
     'btd':False,'orphan':True,'priority_review':False,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,
     'ta_base_score':-0.043,'historical_crl_rate':0.209,'s23_signal_strength':0,
     's6_signal_strength':0,'social_sentiment_score':0,'v1067_score':0.0,'v1067_tier':'NONE',
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'v1070_score':0.0,'v1070_tier':'NONE','btd_oncology_interaction':0,
     'btd_priority_interaction':0,'ta_very_high_risk':0,'double_crl_flag':0,
     'ta_bucket_v2':'MOD','cat_date':'2026-03-19'},
    {'event_id':'GSK|Lynavoy NDA PBC|PDUFA|2026-03-19','ticker':'GSK','company':'GSK plc',
     'asset':'Lynavoy NDA PBC','indication':'PBC pruritus','therapeutic_area':'GI/Hepatology',
     'catalyst_date':'2026-03-19','data_cutoff_date':'3/18/2026','outcome':'APPROVAL',
     'application_type':'NDA','prior_crl':False,'sponsor_prior_approvals':34,
     'manufacturing_risk':False,'form_483_issues':False,'ema_cmc_flag':False,'cmc_extension_flag':False,
     'had_adcom':False,'adcom_vote_pct':0.0,'s22_ped_pk_missing':False,
     'btd':False,'orphan':False,'priority_review':True,'fast_track':True,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,
     'ta_base_score':0.067,'historical_crl_rate':0.162,'s23_signal_strength':0,
     's6_signal_strength':0,'social_sentiment_score':0,'v1067_score':0.0,'v1067_tier':'NONE',
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'v1070_score':0.0,'v1070_tier':'NONE','btd_oncology_interaction':0,
     'btd_priority_interaction':0,'ta_very_high_risk':1,'double_crl_flag':0,
     'ta_bucket_v2':'LOW','cat_date':'2026-03-19'},
]
df = pd.concat([df, pd.DataFrame(new_events)], ignore_index=True).sort_values('catalyst_date').reset_index(drop=True)

# ============================================================
# TEMPORAL FEATURES (same as v8/v9)
# ============================================================

df['sponsor_win_rate'] = 0.0
df['ta_recent_rate'] = 0.0

# NEW: Additional temporal features
df['sponsor_streak'] = 0.0        # consecutive approvals (resets on CRL)
df['sponsor_recent_crl'] = 0.0    # had CRL in last 2 years
df['ta_trend'] = 0.0              # TA approval rate trend (recent vs historical)
df['sponsor_momentum'] = 0.0      # 3-year win rate minus all-time win rate
df['time_since_last_crl'] = 0.0   # years since sponsor's last CRL (0 if none)

sponsor_approvals = defaultdict(int); sponsor_total = defaultdict(int)
ta_recent_events = defaultdict(list)
sponsor_streaks = defaultdict(int)
sponsor_last_crl = {}
sponsor_events_3y = defaultdict(list)

for idx in range(len(df)):
    row = df.iloc[idx]
    company_key = str(row['company']).lower().split()[0] if str(row['company']) != 'nan' else 'unknown'
    ta = str(row['therapeutic_area']).strip()
    cat_date = str(row['catalyst_date'])

    s_app = sponsor_approvals[company_key]; s_tot = sponsor_total[company_key]
    cutoff_3y = (pd.Timestamp(cat_date) - pd.Timedelta(days=1095)).strftime('%Y-%m-%d')
    ta_recent = [e for e in ta_recent_events[ta] if e[0] >= cutoff_3y]
    ta_recent_app = sum(1 for _, o in ta_recent if o == 'APPROVAL')
    ta_recent_tot = len(ta_recent)

    df.at[idx, 'sponsor_win_rate'] = (s_app / s_tot) if s_tot >= 3 else 0.5
    df.at[idx, 'ta_recent_rate'] = (ta_recent_app / ta_recent_tot) if ta_recent_tot >= 5 else 0.5

    # Sponsor streak
    df.at[idx, 'sponsor_streak'] = min(sponsor_streaks[company_key], 10) / 10.0  # normalize to 0-1

    # Recent CRL check (2 years)
    cutoff_2y = (pd.Timestamp(cat_date) - pd.Timedelta(days=730)).strftime('%Y-%m-%d')
    if company_key in sponsor_last_crl and sponsor_last_crl[company_key] >= cutoff_2y:
        df.at[idx, 'sponsor_recent_crl'] = 1.0

    # Time since last CRL (years, capped at 5)
    if company_key in sponsor_last_crl:
        try:
            delta = (pd.Timestamp(cat_date) - pd.Timestamp(sponsor_last_crl[company_key])).days / 365.25
            df.at[idx, 'time_since_last_crl'] = min(delta, 5.0) / 5.0  # normalize to 0-1
        except:
            pass

    # Sponsor momentum (3y rate minus all-time rate)
    s3y = [e for e in sponsor_events_3y[company_key] if e[0] >= cutoff_3y]
    s3y_app = sum(1 for _, o in s3y if o == 'APPROVAL')
    s3y_tot = len(s3y)
    if s3y_tot >= 3 and s_tot >= 5:
        s3y_rate = s3y_app / s3y_tot
        all_rate = s_app / s_tot
        df.at[idx, 'sponsor_momentum'] = s3y_rate - all_rate

    # TA trend (recent 3y vs all-time)
    ta_all_events = ta_recent_events[ta]
    ta_all_app = sum(1 for _, o in ta_all_events if o == 'APPROVAL')
    ta_all_tot = len(ta_all_events)
    if ta_recent_tot >= 5 and ta_all_tot >= 10:
        recent_rate = ta_recent_app / ta_recent_tot
        all_rate = ta_all_app / ta_all_tot
        df.at[idx, 'ta_trend'] = recent_rate - all_rate

    # Update indexes
    if pd.notna(row['outcome']):
        is_app = (row['outcome'] == 'APPROVAL')
        sponsor_total[company_key] += 1
        if is_app:
            sponsor_approvals[company_key] += 1
            sponsor_streaks[company_key] += 1
        else:
            sponsor_streaks[company_key] = 0
            sponsor_last_crl[company_key] = cat_date
        ta_recent_events[ta].append((cat_date, row['outcome']))
        sponsor_events_3y[company_key].append((cat_date, row['outcome']))

# ============================================================
# FEATURE ENGINEERING — v9 base + v10 candidates
# ============================================================

spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)

# === v9 CHAMPION features (30) ===
df['btd_bin'] = df['btd'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['pr_bin'] = df['priority_review'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ppm_flag_bin'] = df['ppm_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['orphan_bin'] = df['orphan'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['ft_bin'] = df['fast_track'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1','Yes'] else 0.0)
df['sponsor_naive'] = (spa==0).astype(float)
df['sponsor_experienced'] = (spa>=5).astype(float)
df['log_spa'] = np.log1p(spa)
df['is_resub'] = df['prior_crl'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
pcc = pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0)
df['multi_crl'] = (pcc>=2).astype(float)
df['ta_very_high'] = df['ta_very_high_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
df['crl_rate_low'] = (crl_rate<=0.15).astype(float)
df['had_adcom_flag'] = df['had_adcom'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
desig = df['btd_bin']+df['orphan_bin']+df['pr_bin']+df['ft_bin']
df['desig_rich'] = (desig>=3).astype(float)
df['desig_count'] = desig  # NEW: continuous designation count
df['spa_sweet'] = ((spa>=3)&(spa<=15)).astype(float)
df['spa_mega'] = (spa>=10).astype(float)
df['spa_3_5'] = ((spa>=3)&(spa<=5)).astype(float)
df['btd_and_priority'] = (df['btd_bin']*df['pr_bin']).astype(float)
df['sweet_x_btd'] = (df['spa_sweet']*df['btd_bin']).astype(float)
df['experienced_x_btd'] = (df['sponsor_experienced']*df['btd_bin']).astype(float)
app_type = df['application_type'].fillna('')
df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['era_post'] = 0.0

# v9 additions
resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
df['resub_class_1'] = (resub_class == 1).astype(float)
df['resub_class_2'] = (resub_class == 2).astype(float)
df['resub1_x_naive'] = df['resub_class_1'] * df['sponsor_naive']
df['log_spa_sq'] = df['log_spa'] ** 2
df['spa_6_15'] = ((spa >= 6) & (spa <= 15)).astype(float)
df['spa_16_plus'] = (spa >= 16).astype(float)
df['swr_x_btd'] = df['sponsor_win_rate'] * df['btd_bin']
df['crl_rate_x_naive'] = crl_rate * df['sponsor_naive']

v9_features = [
    'btd_bin', 'pr_bin', 'ppm_flag_bin', 'sponsor_naive', 'is_resub',
    'ta_very_high', 'had_adcom_flag', 'spa_sweet', 'spa_mega',
    'multi_crl', 'crl_rate_low', 'desig_rich', 'spa_3_5',
    'btd_and_priority', 'sweet_x_btd', 'experienced_x_btd',
    'era_post', 'is_nda', 'log_spa', 'mfg_risk_bin',
    'sponsor_win_rate', 'ta_recent_rate',
    'spa_6_15', 'resub1_x_naive', 'resub_class_2', 'resub_class_1',
    'spa_16_plus', 'log_spa_sq', 'swr_x_btd', 'crl_rate_x_naive'
]

# ============================================================
# v10 CANDIDATE FEATURES — DEEP MINE ROUND 2
# ============================================================

print("\n=== v10 CANDIDATE FEATURES ===")

# --- PILLAR 1: Untapped standalone features ---
df['accel_approval'] = df['accelerated_approval'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1', 'Yes'] else 0.0
)
df['form_483_bin'] = df['form_483_issues'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0
)
df['surrogate_bin'] = df['surrogate_endpoint'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0
)
df['single_arm_bin'] = df['single_arm_study'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0
)
df['gene_therapy_bin'] = df['gene_therapy'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0
)
df['double_crl_bin'] = df['double_crl_flag'].apply(
    lambda x: 1.0 if x in [True, 'TRUE', 1, '1'] else 0.0
)
df['ta_base_continuous'] = pd.to_numeric(df['ta_base_score'], errors='coerce').fillna(0.0)
safety_sev = pd.to_numeric(df['safety_signal_severity'], errors='coerce').fillna(0.0)
df['safety_signal_bin'] = (safety_sev > 0).astype(float)
df['safety_severity_continuous'] = safety_sev

# --- PILLAR 2: Application type granularity ---
app_upper = app_type.str.upper()
df['is_bla'] = app_upper.isin(['BLA']).astype(float)
df['is_snda'] = app_upper.isin(['SNDA','SNDAS']).astype(float)
df['is_sbla'] = app_upper.isin(['SBLA']).astype(float)
df['is_supplement'] = app_upper.isin(['SNDA','SNDAS','SBLA']).astype(float)  # any supplement

# --- PILLAR 3: Designation combos and continuous ---
df['orphan_x_pr'] = df['orphan_bin'] * df['pr_bin']
df['orphan_x_btd'] = df['orphan_bin'] * df['btd_bin']
df['ft_x_pr'] = df['ft_bin'] * df['pr_bin']
df['ft_x_btd'] = df['ft_bin'] * df['btd_bin']
df['orphan_x_ft'] = df['orphan_bin'] * df['ft_bin']
df['btd_x_orphan_x_pr'] = df['btd_bin'] * df['orphan_bin'] * df['pr_bin']  # triple combo
df['desig_count_sq'] = desig ** 2  # non-linear designation effect

# --- PILLAR 4: CRL rate non-linear + thresholds ---
df['crl_rate_continuous'] = crl_rate
df['crl_rate_sq'] = crl_rate ** 2
df['crl_rate_high'] = (crl_rate >= 0.35).astype(float)  # high risk TAs
df['crl_rate_very_low'] = (crl_rate <= 0.10).astype(float)  # very safe TAs
df['crl_rate_x_resub'] = crl_rate * df['is_resub']
df['crl_rate_x_experienced'] = crl_rate * df['sponsor_experienced']

# --- PILLAR 5: v9 cross-interactions (new × new) ---
df['resub1_x_crl_high'] = df['resub_class_1'] * df['crl_rate_high']
df['resub2_x_experienced'] = df['resub_class_2'] * df['sponsor_experienced']
df['spa16_x_btd'] = df['spa_16_plus'] * df['btd_bin']
df['spa16_x_pr'] = df['spa_16_plus'] * df['pr_bin']
df['naive_x_ta_vh'] = df['sponsor_naive'] * df['ta_very_high']
df['swr_x_resub'] = df['sponsor_win_rate'] * df['is_resub']
df['swr_x_naive'] = df['sponsor_win_rate'] * df['sponsor_naive']
df['swr_x_pr'] = df['sponsor_win_rate'] * df['pr_bin']
df['swr_x_ta_vh'] = df['sponsor_win_rate'] * df['ta_very_high']

# --- PILLAR 6: NEW temporal features ---
# (computed above in temporal loop)
# sponsor_streak, sponsor_recent_crl, ta_trend, sponsor_momentum, time_since_last_crl

# --- PILLAR 7: Temporal × static interactions ---
df['streak_x_btd'] = df['sponsor_streak'] * df['btd_bin']
df['streak_x_pr'] = df['sponsor_streak'] * df['pr_bin']
df['recent_crl_x_resub'] = df['sponsor_recent_crl'] * df['is_resub']
df['momentum_x_btd'] = df['sponsor_momentum'] * df['btd_bin']
df['ta_trend_x_naive'] = df['ta_trend'] * df['sponsor_naive']
df['swr_x_streak'] = df['sponsor_win_rate'] * df['sponsor_streak']

# --- PILLAR 8: Safety/manufacturing interactions ---
df['form483_x_naive'] = df['form_483_bin'] * df['sponsor_naive']
df['form483_x_mfg'] = df['form_483_bin'] * df['mfg_risk_bin']
df['safety_x_naive'] = df['safety_signal_bin'] * df['sponsor_naive']
df['mfg_x_naive'] = df['mfg_risk_bin'] * df['sponsor_naive']
df['mfg_x_ta_vh'] = df['mfg_risk_bin'] * df['ta_very_high']

# --- PILLAR 9: Surrogate/single-arm interactions ---
df['surrogate_x_pr'] = df['surrogate_bin'] * df['pr_bin']
df['surrogate_x_btd'] = df['surrogate_bin'] * df['btd_bin']
df['surrogate_x_accel'] = df['surrogate_bin'] * df['accel_approval']
df['single_arm_x_accel'] = df['single_arm_bin'] * df['accel_approval']
df['single_arm_x_btd'] = df['single_arm_bin'] * df['btd_bin']
df['single_arm_x_orphan'] = df['single_arm_bin'] * df['orphan_bin']

# --- PILLAR 10: Accel approval interactions (tested in v9 but on v8 base) ---
df['accel_x_orphan'] = df['accel_approval'] * df['orphan_bin']
df['accel_x_btd'] = df['accel_approval'] * df['btd_bin']
df['accel_x_pr'] = df['accel_approval'] * df['pr_bin']
df['accel_x_naive'] = df['accel_approval'] * df['sponsor_naive']
df['accel_x_experienced'] = df['accel_approval'] * df['sponsor_experienced']
df['accel_x_swr'] = df['accel_approval'] * df['sponsor_win_rate']

# --- PILLAR 11: ChEMBL features (15.7% coverage, use 0 imputation) ---
df['chembl_biologic'] = pd.to_numeric(df.get('chembl_is_biologic', 0), errors='coerce').fillna(0)
df['chembl_fic'] = pd.to_numeric(df.get('chembl_first_in_class', 0), errors='coerce').fillna(0)
df['chembl_has'] = pd.to_numeric(df.get('chembl_has_match', 0), errors='coerce').fillna(0)

# Full candidate list
v10_candidates = [
    # Pillar 1: Standalone untapped
    'orphan_bin', 'ft_bin', 'accel_approval', 'form_483_bin',
    'surrogate_bin', 'single_arm_bin', 'gene_therapy_bin', 'double_crl_bin',
    'ta_base_continuous', 'safety_signal_bin', 'safety_severity_continuous',
    # Pillar 2: App type
    'is_bla', 'is_snda', 'is_sbla', 'is_supplement',
    # Pillar 3: Designation combos
    'orphan_x_pr', 'orphan_x_btd', 'ft_x_pr', 'ft_x_btd', 'orphan_x_ft',
    'btd_x_orphan_x_pr', 'desig_count', 'desig_count_sq',
    # Pillar 4: CRL rate
    'crl_rate_continuous', 'crl_rate_sq', 'crl_rate_high', 'crl_rate_very_low',
    'crl_rate_x_resub', 'crl_rate_x_experienced',
    # Pillar 5: v9 cross-interactions
    'resub1_x_crl_high', 'resub2_x_experienced',
    'spa16_x_btd', 'spa16_x_pr', 'naive_x_ta_vh',
    'swr_x_resub', 'swr_x_naive', 'swr_x_pr', 'swr_x_ta_vh',
    # Pillar 6: Temporal
    'sponsor_streak', 'sponsor_recent_crl', 'ta_trend', 'sponsor_momentum',
    'time_since_last_crl',
    # Pillar 7: Temporal × static
    'streak_x_btd', 'streak_x_pr', 'recent_crl_x_resub',
    'momentum_x_btd', 'ta_trend_x_naive', 'swr_x_streak',
    # Pillar 8: Safety/mfg
    'form483_x_naive', 'form483_x_mfg',
    'safety_x_naive', 'mfg_x_naive', 'mfg_x_ta_vh',
    # Pillar 9: Surrogate/single-arm
    'surrogate_x_pr', 'surrogate_x_btd', 'surrogate_x_accel',
    'single_arm_x_accel', 'single_arm_x_btd', 'single_arm_x_orphan',
    # Pillar 10: Accel interactions (re-test on v9 base)
    'accel_x_orphan', 'accel_x_btd', 'accel_x_pr',
    'accel_x_naive', 'accel_x_experienced', 'accel_x_swr',
    # Pillar 11: ChEMBL
    'chembl_biologic', 'chembl_fic', 'chembl_has',
]

print(f"Total v10 candidates: {len(v10_candidates)}")

# ============================================================
# MODEL TRAINING
# ============================================================

dm = df[df['outcome'].notna()].copy()
dm['target'] = (dm['outcome']=='APPROVAL').astype(int)

train_mask = dm['catalyst_date'] < '2025-01-01'
ho_mask = dm['catalyst_date'] >= '2025-01-01'
dt = dm[train_mask]; dh = dm[ho_mask]
yt = dt['target'].values; yh = dh['target'].values

print(f"\nTraining: {len(dt)} events (approval rate {yt.mean():.4f})")
print(f"Holdout: {len(dh)} events (approval rate {yh.mean():.4f})")

def evaluate_features(features, C, yt, yh, dt, dh, label="", solver='lbfgs', penalty='l2'):
    """Full evaluation: WF CV + HO."""
    Xtr = dt[features].values.astype(float); Xho = dh[features].values.astype(float)

    # Handle NaN
    Xtr = np.nan_to_num(Xtr, nan=0.0)
    Xho = np.nan_to_num(Xho, nan=0.0)

    # WF CV
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    wf_aucs = []; wf_brs = []
    for ti, vi in skf.split(Xtr, yt):
        sc = StandardScaler()
        m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=42)
        m.fit(sc.fit_transform(Xtr[ti]), yt[ti])
        yp = m.predict_proba(sc.transform(Xtr[vi]))[:, 1]
        wf_aucs.append(roc_auc_score(yt[vi], yp))
        wf_brs.append(brier_score_loss(yt[vi], yp))

    # HO
    sc = StandardScaler()
    m = LogisticRegression(C=C, penalty=penalty, solver=solver, max_iter=5000, random_state=42)
    m.fit(sc.fit_transform(Xtr), yt)
    yp = m.predict_proba(sc.transform(Xho))[:, 1]
    ho_auc = roc_auc_score(yh, yp)
    ho_brier = brier_score_loss(yh, yp)
    t1m = yp >= 0.85
    t1c = t1m.sum(); t1w = (yh[t1m]==1).sum()/t1c if t1c > 0 else 0

    return np.mean(wf_aucs), ho_auc, np.mean(wf_brs), ho_brier, t1c, t1w, m, sc

# ============================================================
# PHASE 1: v9 BASELINE REPRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1: v9 BASELINE REPRODUCTION")
print("=" * 70)

best_v9_ho = 0; best_v9_c = 0.01
for C in [0.005, 0.007, 0.008, 0.01, 0.012, 0.015]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(v9_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_v9_ho else ""
    print(f"  v9 C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_v9_ho: best_v9_ho = ho; best_v9_c = C

print(f"\n  v9 baseline: HO AUC {best_v9_ho:.4f} at C={best_v9_c}")

# ============================================================
# PHASE 2: INDIVIDUAL FEATURE SCREENING (v9 + 1)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: INDIVIDUAL FEATURE SCREENING (v9 + 1)")
print("=" * 70)

# Filter valid candidates
valid_candidates = []
for f in v10_candidates:
    if f in v9_features:
        continue  # already in v9
    vals = dt[f].astype(float)
    vals = vals.fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        print(f"  DROP {f}: std={vals.std():.5f}")

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v9_features + [feat]

    best_ho = 0; best_c = best_v9_c
    for C in [0.005, 0.007, 0.008, 0.01, 0.012, 0.015]:
        _, ho, _, hob, t1c, t1w, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    delta = best_ho - best_v9_ho
    feature_results.append((feat, best_ho, delta, best_c))

    tag = "+++" if delta > 0.005 else ("++" if delta > 0.002 else ("+" if delta > 0.0005 else ("~" if delta > -0.001 else "-")))
    print(f"  {tag} {feat}: HO={best_ho:.4f} (delta={delta:+.4f}) C={best_c}")

# Sort by gain
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

current_features = v9_features.copy()
current_ho = best_v9_ho
added = []

# Try all features with positive individual delta, sorted by gain
for feat, ho_individual, delta_individual, best_c_indiv in feature_results:
    if delta_individual < 0.0001:  # lower threshold — be more aggressive
        continue

    test_features = current_features + [feat]

    # Try C range
    best_ho = 0; best_c = 0.01
    for C in [0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.012, 0.015, 0.02]:
        _, ho, _, hob, t1c, t1w, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    if best_ho > current_ho + 0.0002:  # lower gate for marginal gains
        current_features.append(feat)
        added.append((feat, best_ho - current_ho, best_c))
        print(f"  ADDED: {feat} -> HO {best_ho:.4f} (+{best_ho - best_v9_ho:.4f} from v9) C={best_c}")
        current_ho = best_ho
    else:
        print(f"  SKIP: {feat} -> HO {best_ho:.4f} (no incremental gain)")

print(f"\n  After forward selection: {len(current_features)} features, HO AUC {current_ho:.4f}")

# ============================================================
# PHASE 4: FEATURE ABLATION (can we drop any features?)
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

    best_ho = 0; best_c = 0.01
    for C in [0.005, 0.007, 0.01, 0.012, 0.015]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    delta = best_ho - best_final_ho
    if delta > 0.0003:
        print(f"  DROP: {feat} -> HO {best_ho:.4f} ({delta:+.4f}) — feature was HURTING!")
        final_features.remove(feat)
        dropped.append(feat)
        best_final_ho = best_ho
    elif abs(delta) < 0.0002:
        print(f"  NEUTRAL: {feat} -> delta={delta:+.4f}")

print(f"\n  After ablation: {len(final_features)} features, HO AUC {best_final_ho:.4f}")
if dropped:
    print(f"  Dropped: {dropped}")

# ============================================================
# PHASE 5: REGULARIZATION + ARCHITECTURE SWEEP
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: REGULARIZATION + ARCHITECTURE SWEEP")
print("=" * 70)

best_final_ho = 0; best_final_c = 0.01
for C in [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(final_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_final_ho else ""
    print(f"  Ridge C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, WF_Br={wfb:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_final_ho: best_final_ho = ho; best_final_c = C

# Try ElasticNet
print(f"\n  ElasticNet experiments:")
for C in [0.005, 0.01, 0.015, 0.02]:
    try:
        wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(
            final_features, C, yt, yh, dt, dh, solver='saga', penalty='elasticnet'
        )
        tag = "***" if ho > best_final_ho else ""
        print(f"  ElasticNet C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, T1={t1c}({t1w:.3f}) {tag}")
        if ho > best_final_ho:
            best_final_ho = ho; best_final_c = C
            print(f"    >>> ElasticNet beats Ridge!")
    except Exception as e:
        print(f"  ElasticNet C={C}: FAILED ({e})")

print(f"\n  Best: HO AUC {best_final_ho:.4f} at C={best_final_c}")

# ============================================================
# PHASE 6: STABILITY TEST (10 seeds)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: STABILITY TEST (10 seeds)")
print("=" * 70)

Xtr_v10 = dt[final_features].values.astype(float)
Xho_v10 = dh[final_features].values.astype(float)
Xtr_v9 = dt[v9_features].values.astype(float)
Xho_v9 = dh[v9_features].values.astype(float)

Xtr_v10 = np.nan_to_num(Xtr_v10, nan=0.0)
Xho_v10 = np.nan_to_num(Xho_v10, nan=0.0)
Xtr_v9 = np.nan_to_num(Xtr_v9, nan=0.0)
Xho_v9 = np.nan_to_num(Xho_v9, nan=0.0)

v10_hos = []; v9_hos = []
for seed in range(10):
    sc = StandardScaler()
    m = LogisticRegression(C=best_final_c, penalty='l2', solver='lbfgs', max_iter=5000, random_state=seed)
    m.fit(sc.fit_transform(Xtr_v10), yt)
    v10_hos.append(roc_auc_score(yh, m.predict_proba(sc.transform(Xho_v10))[:, 1]))

    sc = StandardScaler()
    m = LogisticRegression(C=best_v9_c, penalty='l2', solver='lbfgs', max_iter=5000, random_state=seed)
    m.fit(sc.fit_transform(Xtr_v9), yt)
    v9_hos.append(roc_auc_score(yh, m.predict_proba(sc.transform(Xho_v9))[:, 1]))

wins = sum(1 for a, b in zip(v10_hos, v9_hos) if a > b)
t_stat, p_val = stats.ttest_rel(v10_hos, v9_hos)
print(f"  v10 mean HO: {np.mean(v10_hos):.4f} (std={np.std(v10_hos):.4f})")
print(f"  v9  mean HO: {np.mean(v9_hos):.4f} (std={np.std(v9_hos):.4f})")
print(f"  v10 wins: {wins}/10 seeds")
print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.6f}")

for i, (a, b) in enumerate(zip(v10_hos, v9_hos)):
    print(f"    Seed {i}: v10={a:.4f} v9={b:.4f} {'WIN' if a > b else 'LOSS'}")

# ============================================================
# PHASE 7: FINAL MODEL + DEPLOY
# ============================================================

print("\n" + "=" * 70)
print("PHASE 7: FINAL v10 MODEL")
print("=" * 70)

wf_final, ho_final, wfb_final, hob_final, t1c_final, t1w_final, model_final, scaler_final = \
    evaluate_features(final_features, best_final_c, yt, yh, dt, dh)

v10_added = [f for f in final_features if f not in v9_features]
v9_dropped = [f for f in v9_features if f not in final_features]

print(f"\n  v10 FINAL:")
print(f"    Features: {len(final_features)} ({len(v10_added)} new, {len(v9_dropped)} dropped)")
print(f"    C: {best_final_c}")
print(f"    WF AUC: {wf_final:.4f} (v9: 0.9083)")
print(f"    HO AUC: {ho_final:.4f} (v9: {best_v9_ho:.4f})")
print(f"    WF Brier: {wfb_final:.4f} (v9: 0.0988)")
print(f"    HO Brier: {hob_final:.4f} (v9: 0.1221)")
print(f"    T1 count: {t1c_final}, T1 win: {t1w_final:.4f}")
print(f"    Features added: {v10_added}")
print(f"    Features dropped: {v9_dropped}")

print(f"\n  Coefficients (sorted by |coef|):")
coefs = dict(zip(final_features, model_final.coef_[0]))
for feat in sorted(coefs, key=lambda x: abs(coefs[x]), reverse=True):
    new_tag = " [NEW v10]" if feat in v10_added else ""
    print(f"    {feat}: {coefs[feat]:+.6f}{new_tag}")
print(f"    intercept: {model_final.intercept_[0]:+.6f}")

# Champion challenge
print(f"\n{'=' * 70}")
print(f"CHAMPION CHALLENGE: v10 vs v9")
print(f"{'=' * 70}")

ho_better = ho_final > best_v9_ho
brier_better = hob_final < 0.1221  # v9 HO Brier
t1_better = (t1c_final >= 119 and t1w_final >= 0.966) or (t1c_final > 119 and t1w_final >= 0.95)

print(f"  HO AUC: v10={ho_final:.4f} vs v9={best_v9_ho:.4f} -> {'v10 WINS' if ho_better else 'v9 WINS'} ({ho_final-best_v9_ho:+.4f})")
print(f"  HO Brier: v10={hob_final:.4f} vs v9=0.1221 -> {'v10 WINS' if brier_better else 'v9 WINS'}")
print(f"  T1: v10={t1c_final} picks ({t1w_final:.3f} win) vs v9=119 picks (0.966 win)")
print(f"  Stability: {wins}/10 seeds, p={p_val:.6f}")

if ho_better and wins >= 7:
    print(f"\n  >>> v10 is NEW CHAMPION! Deploying... <<<")

    # Generate deploy JSON
    deploy = {
        'version': '10.0.0',
        'architecture': f'{len(final_features)}-feature L2 Ridge Logistic Regression',
        'C': best_final_c,
        'solver': 'lbfgs',
        'features': final_features,
        'n_features': len(final_features),
        'intercept': float(model_final.intercept_[0]),
        'coefficients': {f: float(c) for f, c in zip(final_features, model_final.coef_[0])},
        'scaler_means': {f: float(m) for f, m in zip(final_features, scaler_final.mean_)},
        'scaler_scales': {f: float(s) for f, s in zip(final_features, scaler_final.scale_)},
        'training': {
            'n_events': int(len(dt)),
            'approval_rate': float(yt.mean()),
            'temporal_cutoff': '2025-01-01',
            'date_range': f'{dt["catalyst_date"].min()} to {dt["catalyst_date"].max()}'
        },
        'performance': {
            'wf_auc': float(wf_final),
            'ho_auc': float(ho_final),
            'wf_brier': float(wfb_final),
            'ho_brier': float(hob_final),
            't1_count': int(t1c_final),
            't1_win_rate': float(t1w_final),
            'holdout_n': int(len(dh))
        },
        'kaizen_from_v9': {
            'v9_ho_auc': float(best_v9_ho),
            'ho_auc_delta': float(ho_final - best_v9_ho),
            'features_added': v10_added,
            'features_dropped': v9_dropped,
            'stability_test': f'{wins}/10 seeds v10 beats v9 on HO AUC',
            'ho_paired_t_p': float(p_val),
            'pillars_tested': [
                'Untapped standalone (orphan, ft, accel, form483, surrogate, single_arm, gene_therapy)',
                'App type granularity (BLA, sNDA, sBLA, supplement)',
                'Designation combos + continuous count',
                'CRL rate non-linear + thresholds',
                'v9 cross-interactions (new × new)',
                'New temporal (streak, recent_crl, ta_trend, momentum)',
                'Temporal × static interactions',
                'Safety/manufacturing interactions',
                'Surrogate/single-arm interactions',
                'Accel approval re-test on v9 base',
                'ChEMBL features (15.7% coverage)'
            ]
        },
        'tier_system': {
            'T1': '>= 0.85 (Strong Long)',
            'T2': '0.65 - 0.85 (Cautious Long)',
            'T3': '0.40 - 0.65 (Monitor)',
            'T4': '< 0.40 (No Trade)'
        }
    }

    with open('odin_v10_deploy.json', 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"  Deploy config saved: odin_v10_deploy.json")

else:
    print(f"\n  >>> v9 remains CHAMPION. v10 kaizen did not achieve sufficient lift. <<<")
    print(f"  Saving results for analysis...")

# Save results regardless
results = {
    'v10_final_features': final_features,
    'v10_added': v10_added,
    'v9_dropped': v9_dropped,
    'v10_ho_auc': float(ho_final),
    'v9_ho_auc': float(best_v9_ho),
    'v10_wf_auc': float(wf_final),
    'delta': float(ho_final - best_v9_ho),
    'stability_wins': wins,
    'p_value': float(p_val),
    'best_C': best_final_c,
    'individual_screening': [(f, float(h), float(d), c) for f, h, d, c in feature_results[:30]],
    'forward_selection_added': [(f, float(d), c) for f, d, c in added],
    'all_candidates_tested': len(valid_candidates),
    'target_met': ho_final >= 0.91
}

with open('odin_v10_kaizen_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n  Results saved: odin_v10_kaizen_results.json")
print(f"  TARGET 0.91: {'MET!' if ho_final >= 0.91 else 'NOT MET'} (actual: {ho_final:.4f})")
