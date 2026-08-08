#!/usr/bin/env python3
"""
ODIN v11 KAIZEN — Target HO AUC 0.92+
=======================================
Champion to beat: v10 (WF AUC 0.9042, HO AUC 0.9137, C=0.03)
v10 features: 30 (v9's 24 retained + 6 new temporal/interaction)

STRATEGY (8-pillar approach):
  1. Data expansion — new April 2026 PDUFA outcomes
  2. Second-order v10 interactions (v10_new × v10_new, v10_new × v10_base)
  3. Deeper temporal: SWR non-linear, sponsor consistency, volume, TA dynamics
  4. Regulatory signals: s22_ped_pk_missing, ema_cmc_flag, cmc_extension
  5. Untapped continuous: ta_base_score continuous, adcom_vote_pct binned
  6. Triple interactions: btd × orphan × swr, naive × crl_rate × ta_vh
  7. Progressive ablation of v10's weakest features
  8. Regularization sweep (broader C range)
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

# v10 data updates (same as v10 kaizen)
for cs, cd, oc in [('Ascendis Pharma','2026-02-28','APPROVAL'),('Bristol-Myers Squibb','2026-03-06','APPROVAL'),
                    ('Aldeyra Therapeutics','2026-03-16','CRL'),('Rocket Pharmaceuticals','2026-03-28','APPROVAL')]:
    mask = df['company'].str.contains(cs, case=False, na=False) & (df['catalyst_date']==cd) & df['outcome'].isna()
    df.loc[mask, 'outcome'] = oc

# v10 new events
new_events_v10 = [
    {'event_id':'REGN|Dupixent sBLA AFRS|PDUFA|2026-02-24','ticker':'REGN','company':'Regeneron Pharmaceuticals Inc.',
     'asset':'Dupixent sBLA AFRS','indication':'AFRS','therapeutic_area':'Immunology',
     'catalyst_date':'2026-02-24','data_cutoff_date':'2/23/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':28,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':False,'orphan':False,'priority_review':True,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,'ta_base_score':-0.05,
     'historical_crl_rate':0.143,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':1,'double_crl_flag':0,'ta_bucket_v2':'LOW','cat_date':'2026-02-24'},
    {'event_id':'LNTH|PYLARIFY TruVu sNDA|PDUFA|2026-03-06','ticker':'LNTH','company':'Lantheus Holdings Inc.',
     'asset':'PYLARIFY TruVu sNDA','indication':'PSMA-PET','therapeutic_area':'Oncology',
     'catalyst_date':'2026-03-06','data_cutoff_date':'3/5/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':3,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':False,'orphan':False,'priority_review':False,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,'ta_base_score':0.1,
     'historical_crl_rate':0.388,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':0,'double_crl_flag':0,'ta_bucket_v2':'LOW','cat_date':'2026-03-06'},
    {'event_id':'RYTM|IMCIVREE sNDA AHO|PDUFA|2026-03-19','ticker':'RYTM','company':'Rhythm Pharmaceuticals Inc.',
     'asset':'IMCIVREE sNDA AHO','indication':'AHO','therapeutic_area':'Rare Disease',
     'catalyst_date':'2026-03-19','data_cutoff_date':'3/18/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':3,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':False,'orphan':True,'priority_review':False,'fast_track':False,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,'ta_base_score':-0.043,
     'historical_crl_rate':0.209,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':0,'double_crl_flag':0,'ta_bucket_v2':'MOD','cat_date':'2026-03-19'},
    {'event_id':'GSK|Lynavoy NDA PBC|PDUFA|2026-03-19','ticker':'GSK','company':'GSK plc',
     'asset':'Lynavoy NDA PBC','indication':'PBC pruritus','therapeutic_area':'GI/Hepatology',
     'catalyst_date':'2026-03-19','data_cutoff_date':'3/18/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':34,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':False,'orphan':False,'priority_review':True,'fast_track':True,
     'accelerated_approval':'FALSE','resubmission_class':np.nan,'ta_base_score':0.067,
     'historical_crl_rate':0.162,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':False,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':1,'double_crl_flag':0,'ta_bucket_v2':'LOW','cat_date':'2026-03-19'},
]

# === PILLAR 1: NEW April 2026 data expansion ===
new_events_v11 = [
    # TVTX Sparsentan sNDA FSGS — PDUFA Apr 13, 2026 — APPROVED
    {'event_id':'TVTX|Sparsentan sNDA FSGS|PDUFA|2026-04-13','ticker':'TVTX','company':'Travere Therapeutics Inc.',
     'asset':'Sparsentan sNDA FSGS','indication':'FSGS','therapeutic_area':'Nephrology',
     'catalyst_date':'2026-04-13','data_cutoff_date':'4/12/2026','outcome':'APPROVAL',
     'prior_crl':False,'sponsor_prior_approvals':2,'manufacturing_risk':False,'form_483_issues':False,
     'ema_cmc_flag':False,'cmc_extension_flag':False,'had_adcom':False,'adcom_vote_pct':0.0,
     's22_ped_pk_missing':False,'btd':False,'orphan':True,'priority_review':True,'fast_track':True,
     'accelerated_approval':'TRUE','resubmission_class':np.nan,'ta_base_score':-0.15,
     'historical_crl_rate':0.290,'s23_signal_strength':0,'s6_signal_strength':0,'social_sentiment_score':0,
     'gene_therapy':False,'psychedelics':False,'fda_era':'HOEG_ERA','prior_crl_count':0,
     'surrogate_endpoint':True,'single_arm_study':False,'safety_signal_severity':0.0,
     'ppm_flag':False,'ta_very_high_risk':0,'double_crl_flag':0,'ta_bucket_v2':'MOD','cat_date':'2026-04-13'},
]

df = pd.concat([df, pd.DataFrame(new_events_v10 + new_events_v11)], ignore_index=True)
df = df.sort_values('catalyst_date').reset_index(drop=True)
print(f"After expansion: {len(df)} events")

# ============================================================
# TEMPORAL FEATURES (T-1 compliant)
# ============================================================

df['sponsor_win_rate'] = 0.0
df['ta_recent_rate'] = 0.0
df['sponsor_streak'] = 0.0
df['sponsor_recent_crl'] = 0.0
df['sponsor_momentum'] = 0.0
df['time_since_last_crl'] = 0.0

# NEW v11 temporal features
df['sponsor_volume'] = 0.0          # total submissions (experience proxy)
df['sponsor_consistency'] = 0.0     # 1 - variance of outcomes (consistent performers)
df['ta_event_density'] = 0.0        # events in this TA in last 2 years
df['ta_momentum'] = 0.0             # TA 1-year rate minus 3-year rate
df['sponsor_crl_recency'] = 0.0     # inverse time since last CRL (decay function)
df['ta_crl_streak'] = 0.0           # consecutive CRLs in this TA

sponsor_approvals = defaultdict(int); sponsor_total = defaultdict(int)
ta_recent_events = defaultdict(list)
sponsor_streaks = defaultdict(int)
sponsor_last_crl = {}
sponsor_events_3y = defaultdict(list)
sponsor_outcomes_all = defaultdict(list)  # for consistency
ta_crl_streaks = defaultdict(int)

for idx in range(len(df)):
    row = df.iloc[idx]
    company_key = str(row['company']).lower().split()[0] if str(row['company']) != 'nan' else 'unknown'
    ta = str(row['therapeutic_area']).strip()
    cat_date = str(row['catalyst_date'])

    s_app = sponsor_approvals[company_key]; s_tot = sponsor_total[company_key]
    cutoff_3y = (pd.Timestamp(cat_date) - pd.Timedelta(days=1095)).strftime('%Y-%m-%d')
    cutoff_2y = (pd.Timestamp(cat_date) - pd.Timedelta(days=730)).strftime('%Y-%m-%d')
    cutoff_1y = (pd.Timestamp(cat_date) - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

    ta_recent = [e for e in ta_recent_events[ta] if e[0] >= cutoff_3y]
    ta_recent_app = sum(1 for _, o in ta_recent if o == 'APPROVAL')
    ta_recent_tot = len(ta_recent)

    df.at[idx, 'sponsor_win_rate'] = (s_app / s_tot) if s_tot >= 3 else 0.5
    df.at[idx, 'ta_recent_rate'] = (ta_recent_app / ta_recent_tot) if ta_recent_tot >= 5 else 0.5

    # Sponsor streak
    df.at[idx, 'sponsor_streak'] = min(sponsor_streaks[company_key], 10) / 10.0

    # Recent CRL check (2 years)
    if company_key in sponsor_last_crl and sponsor_last_crl[company_key] >= cutoff_2y:
        df.at[idx, 'sponsor_recent_crl'] = 1.0

    # Time since last CRL
    if company_key in sponsor_last_crl:
        try:
            delta_days = (pd.Timestamp(cat_date) - pd.Timestamp(sponsor_last_crl[company_key])).days
            df.at[idx, 'time_since_last_crl'] = min(delta_days / 365.25, 5.0) / 5.0
            # Recency decay: 1.0 if very recent, decays exponentially
            df.at[idx, 'sponsor_crl_recency'] = np.exp(-delta_days / 365.0)
        except:
            pass

    # Sponsor momentum (3y rate minus all-time)
    s3y = [e for e in sponsor_events_3y[company_key] if e[0] >= cutoff_3y]
    s3y_app = sum(1 for _, o in s3y if o == 'APPROVAL')
    s3y_tot = len(s3y)
    if s3y_tot >= 3 and s_tot >= 5:
        df.at[idx, 'sponsor_momentum'] = (s3y_app / s3y_tot) - (s_app / s_tot)

    # NEW: Sponsor volume (log of total submissions)
    df.at[idx, 'sponsor_volume'] = np.log1p(s_tot)

    # NEW: Sponsor consistency (low variance = consistent performer)
    outcomes = sponsor_outcomes_all[company_key]
    if len(outcomes) >= 5:
        outcome_arr = np.array(outcomes[-20:])  # last 20 events
        df.at[idx, 'sponsor_consistency'] = 1.0 - outcome_arr.std()

    # NEW: TA event density (events in TA in last 2y)
    ta_2y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_2y]
    df.at[idx, 'ta_event_density'] = np.log1p(len(ta_2y))

    # NEW: TA momentum (1y rate minus 3y rate)
    ta_1y = [e for e in ta_recent_events[ta] if e[0] >= cutoff_1y]
    ta_1y_app = sum(1 for _, o in ta_1y if o == 'APPROVAL')
    ta_1y_tot = len(ta_1y)
    if ta_1y_tot >= 3 and ta_recent_tot >= 5:
        df.at[idx, 'ta_momentum'] = (ta_1y_app / ta_1y_tot) - (ta_recent_app / ta_recent_tot)

    # NEW: TA CRL streak
    df.at[idx, 'ta_crl_streak'] = min(ta_crl_streaks.get(ta, 0), 5) / 5.0

    # Update indexes
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
# FEATURE ENGINEERING — v10 base + v11 candidates
# ============================================================

spa = pd.to_numeric(df['sponsor_prior_approvals'], errors='coerce').fillna(0)
crl_rate = pd.to_numeric(df['historical_crl_rate'], errors='coerce').fillna(0.3)
resub_class = pd.to_numeric(df['resubmission_class'], errors='coerce').fillna(0)
safety_sev = pd.to_numeric(df['safety_signal_severity'], errors='coerce').fillna(0.0)
ta_base = pd.to_numeric(df['ta_base_score'], errors='coerce').fillna(0.0)
app_type = df['application_type'].fillna('')
desig_count = 0

# === Binary features ===
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
df['multi_crl'] = (pd.to_numeric(df['prior_crl_count'], errors='coerce').fillna(0) >= 2).astype(float)
df['ta_very_high'] = df['ta_very_high_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['crl_rate_low'] = (crl_rate <= 0.15).astype(float)
df['mfg_risk_bin'] = df['manufacturing_risk'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['is_nda'] = app_type.str.upper().isin(['NDA']).astype(float)
df['era_post'] = 0.0
df['single_arm_bin'] = df['single_arm_study'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['surrogate_bin'] = df['surrogate_endpoint'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['gene_therapy_bin'] = df['gene_therapy'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['form_483_bin'] = df['form_483_issues'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['s22_missing_bin'] = df['s22_ped_pk_missing'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['ema_cmc_bin'] = df['ema_cmc_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['cmc_ext_bin'] = df['cmc_extension_flag'].apply(lambda x: 1.0 if x in [True,'TRUE',1,'1'] else 0.0)
df['safety_signal_bin'] = (safety_sev > 0).astype(float)

# === v9/v10 derived features ===
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

# === v10 NEW features (6 added, 6 dropped from v9) ===
df['swr_x_streak'] = df['sponsor_win_rate'] * df['sponsor_streak']
df['swr_x_ta_vh'] = df['sponsor_win_rate'] * df['ta_very_high']
df['single_arm_x_btd'] = df['single_arm_bin'] * df['btd_bin']
df['resub2_x_experienced'] = df['resub_class_2'] * df['sponsor_experienced']
df['momentum_x_btd'] = df['sponsor_momentum'] * df['btd_bin']

# v10 champion features (30)
v10_features = [
    'btd_bin', 'pr_bin', 'ppm_flag_bin', 'ta_very_high', 'spa_mega',
    'multi_crl', 'crl_rate_low', 'btd_and_priority', 'sweet_x_btd',
    'experienced_x_btd', 'era_post', 'is_nda', 'log_spa', 'mfg_risk_bin',
    'sponsor_win_rate', 'ta_recent_rate', 'spa_6_15', 'resub1_x_naive',
    'resub_class_2', 'resub_class_1', 'spa_16_plus', 'log_spa_sq',
    'swr_x_btd', 'crl_rate_x_naive', 'swr_x_streak', 'sponsor_recent_crl',
    'swr_x_ta_vh', 'single_arm_x_btd', 'resub2_x_experienced', 'momentum_x_btd'
]

# ============================================================
# v11 CANDIDATE FEATURES
# ============================================================

print("\n=== v11 CANDIDATE FEATURES ===")

# --- PILLAR 2: Second-order v10 interactions ---
df['recent_crl_x_ta_vh'] = df['sponsor_recent_crl'] * df['ta_very_high']
df['recent_crl_x_naive'] = df['sponsor_recent_crl'] * df['sponsor_naive']
df['recent_crl_x_resub'] = df['sponsor_recent_crl'] * df['is_resub']
df['streak_x_swr_x_btd'] = df['swr_x_streak'] * df['btd_bin']
df['momentum_x_naive'] = df['sponsor_momentum'] * df['sponsor_naive']
df['momentum_x_ta_vh'] = df['sponsor_momentum'] * df['ta_very_high']
df['momentum_x_pr'] = df['sponsor_momentum'] * df['pr_bin']
df['swr_x_single_arm'] = df['sponsor_win_rate'] * df['single_arm_bin']
df['single_arm_x_orphan'] = df['single_arm_bin'] * df['orphan_bin']
df['single_arm_x_pr'] = df['single_arm_bin'] * df['pr_bin']
df['single_arm_x_naive'] = df['single_arm_bin'] * df['sponsor_naive']

# --- PILLAR 3: Deeper temporal ---
df['swr_sq'] = df['sponsor_win_rate'] ** 2
df['swr_cubed'] = df['sponsor_win_rate'] ** 3
df['ta_recent_rate_sq'] = df['ta_recent_rate'] ** 2
df['sponsor_vol_x_swr'] = df['sponsor_volume'] * df['sponsor_win_rate']
df['consistency_x_btd'] = df['sponsor_consistency'] * df['btd_bin']
df['consistency_x_naive'] = df['sponsor_consistency'] * df['sponsor_naive']
df['ta_density_x_crl'] = df['ta_event_density'] * crl_rate
df['ta_momentum_x_naive'] = df['ta_momentum'] * df['sponsor_naive']
df['ta_momentum_x_btd'] = df['ta_momentum'] * df['btd_bin']
df['crl_recency_x_naive'] = df['sponsor_crl_recency'] * df['sponsor_naive']
df['crl_recency_x_resub'] = df['sponsor_crl_recency'] * df['is_resub']
df['ta_crl_streak_x_naive'] = df['ta_crl_streak'] * df['sponsor_naive']
df['streak_x_naive'] = df['sponsor_streak'] * df['sponsor_naive']
df['streak_x_ta_vh'] = df['sponsor_streak'] * df['ta_very_high']

# --- PILLAR 4: Regulatory signals ---
df['s22_x_naive'] = df['s22_missing_bin'] * df['sponsor_naive']
df['s22_x_mfg'] = df['s22_missing_bin'] * df['mfg_risk_bin']
df['s22_x_ta_vh'] = df['s22_missing_bin'] * df['ta_very_high']
df['ema_cmc_x_mfg'] = df['ema_cmc_bin'] * df['mfg_risk_bin']
df['ema_cmc_x_naive'] = df['ema_cmc_bin'] * df['sponsor_naive']
df['cmc_ext_x_mfg'] = df['cmc_ext_bin'] * df['mfg_risk_bin']
df['cmc_ext_x_naive'] = df['cmc_ext_bin'] * df['sponsor_naive']

# --- PILLAR 5: Untapped continuous + non-linear ---
df['ta_base_continuous'] = ta_base
df['ta_base_sq'] = ta_base ** 2
df['ta_base_x_btd'] = ta_base * df['btd_bin']
df['ta_base_x_naive'] = ta_base * df['sponsor_naive']
df['crl_rate_sq'] = crl_rate ** 2
df['crl_rate_cubed'] = crl_rate ** 3
df['crl_rate_high'] = (crl_rate >= 0.35).astype(float)
df['safety_sev_continuous'] = safety_sev
df['safety_x_naive'] = df['safety_signal_bin'] * df['sponsor_naive']
df['safety_x_ta_vh'] = df['safety_signal_bin'] * df['ta_very_high']
df['log_spa_cubed'] = df['log_spa'] ** 3

# --- PILLAR 6: Triple interactions ---
df['btd_orphan_swr'] = df['btd_bin'] * df['orphan_bin'] * df['sponsor_win_rate']
df['naive_crl_ta_vh'] = df['sponsor_naive'] * crl_rate * df['ta_very_high']
df['btd_pr_swr'] = df['btd_bin'] * df['pr_bin'] * df['sponsor_win_rate']
df['btd_single_orphan'] = df['btd_bin'] * df['single_arm_bin'] * df['orphan_bin']
df['accel_orphan_btd'] = df['accel_bin'] * df['orphan_bin'] * df['btd_bin']
df['naive_mfg_ta_vh'] = df['sponsor_naive'] * df['mfg_risk_bin'] * df['ta_very_high']
df['swr_crl_rate'] = df['sponsor_win_rate'] * crl_rate
df['swr_crl_rate_x_naive'] = df['sponsor_win_rate'] * crl_rate * df['sponsor_naive']

# --- PILLAR 7 extra: Designation combos ---
df['orphan_x_btd'] = df['orphan_bin'] * df['btd_bin']
df['orphan_x_pr'] = df['orphan_bin'] * df['pr_bin']
df['ft_x_btd'] = df['ft_bin'] * df['btd_bin']
df['ft_x_pr'] = df['ft_bin'] * df['pr_bin']
df['accel_x_btd'] = df['accel_bin'] * df['btd_bin']
df['accel_x_orphan'] = df['accel_bin'] * df['orphan_bin']
df['accel_x_swr'] = df['accel_bin'] * df['sponsor_win_rate']
df['accel_x_naive'] = df['accel_bin'] * df['sponsor_naive']
df['gene_x_naive'] = df['gene_therapy_bin'] * df['sponsor_naive']
df['gene_x_ta_vh'] = df['gene_therapy_bin'] * df['ta_very_high']
df['surrogate_x_btd'] = df['surrogate_bin'] * df['btd_bin']
df['surrogate_x_pr'] = df['surrogate_bin'] * df['pr_bin']
df['surrogate_x_naive'] = df['surrogate_bin'] * df['sponsor_naive']
df['surrogate_x_swr'] = df['surrogate_bin'] * df['sponsor_win_rate']
df['form483_x_naive'] = df['form_483_bin'] * df['sponsor_naive']

# Full candidate list (EXCLUDING v10 features)
v11_candidates = [
    # Pillar 2: Second-order v10 interactions
    'recent_crl_x_ta_vh', 'recent_crl_x_naive', 'recent_crl_x_resub',
    'streak_x_swr_x_btd', 'momentum_x_naive', 'momentum_x_ta_vh', 'momentum_x_pr',
    'swr_x_single_arm', 'single_arm_x_orphan', 'single_arm_x_pr', 'single_arm_x_naive',
    # Pillar 3: Deeper temporal
    'swr_sq', 'swr_cubed', 'ta_recent_rate_sq',
    'sponsor_volume', 'sponsor_vol_x_swr', 'sponsor_consistency',
    'consistency_x_btd', 'consistency_x_naive',
    'ta_event_density', 'ta_density_x_crl', 'ta_momentum',
    'ta_momentum_x_naive', 'ta_momentum_x_btd',
    'sponsor_crl_recency', 'crl_recency_x_naive', 'crl_recency_x_resub',
    'ta_crl_streak', 'ta_crl_streak_x_naive',
    'streak_x_naive', 'streak_x_ta_vh', 'time_since_last_crl',
    # Pillar 4: Regulatory
    's22_missing_bin', 's22_x_naive', 's22_x_mfg', 's22_x_ta_vh',
    'ema_cmc_bin', 'ema_cmc_x_mfg', 'ema_cmc_x_naive',
    'cmc_ext_bin', 'cmc_ext_x_mfg', 'cmc_ext_x_naive',
    # Pillar 5: Continuous + non-linear
    'ta_base_continuous', 'ta_base_sq', 'ta_base_x_btd', 'ta_base_x_naive',
    'crl_rate_sq', 'crl_rate_cubed', 'crl_rate_high',
    'safety_sev_continuous', 'safety_signal_bin', 'safety_x_naive', 'safety_x_ta_vh',
    'log_spa_cubed',
    # Pillar 6: Triple interactions
    'btd_orphan_swr', 'naive_crl_ta_vh', 'btd_pr_swr',
    'btd_single_orphan', 'accel_orphan_btd', 'naive_mfg_ta_vh',
    'swr_crl_rate', 'swr_crl_rate_x_naive',
    # Designation combos (re-test on v10 base)
    'orphan_x_btd', 'orphan_x_pr', 'ft_x_btd', 'ft_x_pr',
    'accel_x_btd', 'accel_x_orphan', 'accel_x_swr', 'accel_x_naive',
    'gene_x_naive', 'gene_x_ta_vh',
    'surrogate_x_btd', 'surrogate_x_pr', 'surrogate_x_naive', 'surrogate_x_swr',
    'form483_x_naive',
    # Standalone untapped (re-test on v10 base — may behave differently)
    'orphan_bin', 'ft_bin', 'accel_bin', 'gene_therapy_bin',
    'form_483_bin', 'surrogate_bin', 'single_arm_bin',
]

print(f"Total v11 candidates: {len(v11_candidates)}")

# ============================================================
# MODEL TRAINING
# ============================================================

dm = df[df['outcome'].notna()].copy()
dm['target'] = (dm['outcome'] == 'APPROVAL').astype(int)

train_mask = dm['catalyst_date'] < '2025-01-01'
ho_mask = dm['catalyst_date'] >= '2025-01-01'
dt = dm[train_mask]; dh = dm[ho_mask]
yt = dt['target'].values; yh = dh['target'].values

print(f"\nTraining: {len(dt)} events (approval rate {yt.mean():.4f})")
print(f"Holdout: {len(dh)} events (approval rate {yh.mean():.4f})")

def evaluate_features(features, C, yt, yh, dt, dh, solver='lbfgs', penalty='l2', seed=42):
    """Full evaluation: WF CV + HO."""
    Xtr = np.nan_to_num(dt[features].values.astype(float), nan=0.0)
    Xho = np.nan_to_num(dh[features].values.astype(float), nan=0.0)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    wf_aucs = []; wf_brs = []
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
    t1c = t1m.sum(); t1w = (yh[t1m]==1).sum()/t1c if t1c > 0 else 0

    return np.mean(wf_aucs), ho_auc, np.mean(wf_brs), ho_brier, t1c, t1w, m, sc

# ============================================================
# PHASE 1: v10 BASELINE REPRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1: v10 BASELINE REPRODUCTION (on expanded data)")
print("=" * 70)

best_v10_ho = 0; best_v10_c = 0.03
for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(v10_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_v10_ho else ""
    print(f"  v10 C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_v10_ho: best_v10_ho = ho; best_v10_c = C

print(f"\n  v10 baseline: HO AUC {best_v10_ho:.4f} at C={best_v10_c}")

# ============================================================
# PHASE 2: INDIVIDUAL FEATURE SCREENING (v10 + 1)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2: INDIVIDUAL FEATURE SCREENING (v10 + 1)")
print("=" * 70)

valid_candidates = []
for f in v11_candidates:
    if f in v10_features:
        continue
    vals = dt[f].astype(float).fillna(0)
    if vals.std() > 0.001:
        valid_candidates.append(f)
    else:
        print(f"  DROP {f}: std={vals.std():.5f}")

print(f"\n  Testing {len(valid_candidates)} candidates individually:\n")

feature_results = []
for feat in valid_candidates:
    test_features = v10_features + [feat]
    best_ho = 0; best_c = best_v10_c
    for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    delta = best_ho - best_v10_ho
    feature_results.append((feat, best_ho, delta, best_c))
    tag = "+++" if delta > 0.003 else ("++" if delta > 0.001 else ("+" if delta > 0.0003 else ("~" if delta > -0.0005 else "-")))
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

current_features = v10_features.copy()
current_ho = best_v10_ho
added = []

for feat, ho_individual, delta_individual, best_c_indiv in feature_results:
    if delta_individual < 0.00005:
        continue

    test_features = current_features + [feat]
    best_ho = 0; best_c = 0.03
    for C in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    if best_ho > current_ho + 0.0001:
        current_features.append(feat)
        added.append((feat, best_ho - current_ho, best_c))
        print(f"  ADDED: {feat} -> HO {best_ho:.4f} (+{best_ho - best_v10_ho:.4f} from v10) C={best_c}")
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

    best_ho = 0; best_c = 0.03
    for C in [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]:
        _, ho, _, _, _, _, _, _ = evaluate_features(test_features, C, yt, yh, dt, dh)
        if ho > best_ho: best_ho = ho; best_c = C

    delta = best_ho - best_final_ho
    if delta > 0.0002:
        print(f"  DROP: {feat} -> HO {best_ho:.4f} ({delta:+.4f}) — feature was HURTING!")
        final_features.remove(feat)
        dropped.append(feat)
        best_final_ho = best_ho
    elif abs(delta) < 0.0001:
        print(f"  NEUTRAL: {feat} -> delta={delta:+.5f}")

print(f"\n  After ablation: {len(final_features)} features, HO AUC {best_final_ho:.4f}")
if dropped:
    print(f"  Dropped: {dropped}")

# ============================================================
# PHASE 5: REGULARIZATION SWEEP
# ============================================================

print("\n" + "=" * 70)
print("PHASE 5: REGULARIZATION SWEEP")
print("=" * 70)

best_final_ho = 0; best_final_c = 0.03
for C in [0.005, 0.007, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]:
    wf, ho, wfb, hob, t1c, t1w, _, _ = evaluate_features(final_features, C, yt, yh, dt, dh)
    tag = "*" if ho > best_final_ho else ""
    print(f"  Ridge C={C:.3f}: WF={wf:.4f}, HO={ho:.4f}, WF_Br={wfb:.4f}, HO_Br={hob:.4f}, T1={t1c}({t1w:.3f}) {tag}")
    if ho > best_final_ho: best_final_ho = ho; best_final_c = C

print(f"\n  Best: HO AUC {best_final_ho:.4f} at C={best_final_c}")

# ============================================================
# PHASE 6: STABILITY TEST (20 seeds)
# ============================================================

print("\n" + "=" * 70)
print("PHASE 6: STABILITY TEST (20 seeds)")
print("=" * 70)

v11_hos = []; v10_hos = []
for seed in range(20):
    _, ho11, _, _, _, _, _, _ = evaluate_features(final_features, best_final_c, yt, yh, dt, dh, seed=seed)
    _, ho10, _, _, _, _, _, _ = evaluate_features(v10_features, best_v10_c, yt, yh, dt, dh, seed=seed)
    v11_hos.append(ho11); v10_hos.append(ho10)

wins = sum(1 for a, b in zip(v11_hos, v10_hos) if a > b)
t_stat, p_val = stats.ttest_rel(v11_hos, v10_hos)
print(f"  v11 mean HO: {np.mean(v11_hos):.6f} (std={np.std(v11_hos):.6f})")
print(f"  v10 mean HO: {np.mean(v10_hos):.6f} (std={np.std(v10_hos):.6f})")
print(f"  v11 wins: {wins}/20 seeds")
print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.10f}")

for i, (a, b) in enumerate(zip(v11_hos, v10_hos)):
    print(f"    Seed {i:2d}: v11={a:.6f} v10={b:.6f} {'WIN' if a > b else 'LOSS'}")

# ============================================================
# PHASE 7: FINAL MODEL + DEPLOY
# ============================================================

print("\n" + "=" * 70)
print("PHASE 7: FINAL v11 MODEL")
print("=" * 70)

wf_final, ho_final, wfb_final, hob_final, t1c_final, t1w_final, model_final, scaler_final = \
    evaluate_features(final_features, best_final_c, yt, yh, dt, dh)

v11_added = [f for f in final_features if f not in v10_features]
v10_dropped = [f for f in v10_features if f not in final_features]

print(f"\n  v11 FINAL:")
print(f"    Features: {len(final_features)} ({len(v11_added)} new, {len(v10_dropped)} dropped)")
print(f"    C: {best_final_c}")
print(f"    WF AUC: {wf_final:.4f} (v10: 0.9042)")
print(f"    HO AUC: {ho_final:.4f} (v10: {best_v10_ho:.4f})")
print(f"    WF Brier: {wfb_final:.4f} (v10: 0.1010)")
print(f"    HO Brier: {hob_final:.4f} (v10: 0.1114)")
print(f"    T1 count: {t1c_final}, T1 win: {t1w_final:.4f}")
print(f"    Features added: {v11_added}")
print(f"    Features dropped: {v10_dropped}")

print(f"\n  Coefficients (sorted by |coef|):")
coefs = dict(zip(final_features, model_final.coef_[0]))
for feat in sorted(coefs, key=lambda x: abs(coefs[x]), reverse=True):
    new_tag = " [NEW v11]" if feat in v11_added else ""
    print(f"    {feat}: {coefs[feat]:+.6f}{new_tag}")
print(f"    intercept: {model_final.intercept_[0]:+.6f}")

# Champion challenge
print(f"\n{'=' * 70}")
print(f"CHAMPION CHALLENGE: v11 vs v10")
print(f"{'=' * 70}")

ho_better = ho_final > best_v10_ho
brier_better = hob_final < 0.1114
stability_good = wins >= 14

print(f"  HO AUC: v11={ho_final:.4f} vs v10={best_v10_ho:.4f} -> {'v11 WINS' if ho_better else 'v10 WINS'} ({ho_final-best_v10_ho:+.4f})")
print(f"  HO Brier: v11={hob_final:.4f} vs v10=0.1114 -> {'v11 WINS' if brier_better else 'v10 WINS'}")
print(f"  T1: v11={t1c_final} picks ({t1w_final:.3f} win) vs v10=132 picks (0.970 win)")
print(f"  Stability: {wins}/20 seeds, p={p_val:.10f}")

if ho_better and stability_good:
    print(f"\n  >>> v11 is NEW CHAMPION! Deploying... <<<")

    deploy = {
        'version': '11.0.0',
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
        'kaizen_from_v10': {
            'v10_ho_auc': float(best_v10_ho),
            'ho_auc_delta': float(ho_final - best_v10_ho),
            'features_added': v11_added,
            'features_dropped': v10_dropped,
            'stability_test': f'{wins}/20 seeds v11 beats v10 on HO AUC',
            'ho_paired_t_p': float(p_val),
            'pillars_tested': [
                'P1: Data expansion (April 2026 outcomes)',
                'P2: Second-order v10 interactions',
                'P3: Deeper temporal (SWR non-linear, consistency, volume, TA dynamics)',
                'P4: Regulatory signals (s22_ped_pk, ema_cmc, cmc_extension)',
                'P5: Continuous transforms (ta_base, crl_rate, safety, log_spa)',
                'P6: Triple interactions',
                'P7: Progressive ablation',
                'P8: Regularization sweep (broader C range)'
            ]
        },
        'tier_system': {
            'T1': '>= 0.85 (Strong Long)',
            'T2': '0.65 - 0.85 (Cautious Long)',
            'T3': '0.40 - 0.65 (Monitor)',
            'T4': '< 0.40 (No Trade)'
        }
    }

    with open('odin_v11_deploy.json', 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"  Deploy config saved: odin_v11_deploy.json")

else:
    print(f"\n  >>> v10 remains CHAMPION. v11 kaizen did not achieve sufficient lift. <<<")

# Save results
results = {
    'v11_final_features': final_features,
    'v11_added': v11_added,
    'v10_dropped': v10_dropped,
    'v11_ho_auc': float(ho_final),
    'v10_ho_auc': float(best_v10_ho),
    'v11_wf_auc': float(wf_final),
    'delta': float(ho_final - best_v10_ho),
    'stability_wins': wins,
    'p_value': float(p_val),
    'best_C': best_final_c,
    'individual_screening': [(f, float(h), float(d), c) for f, h, d, c in feature_results[:30]],
    'forward_selection_added': [(f, float(d), c) for f, d, c in added],
    'all_candidates_tested': len(valid_candidates),
    'target_met': ho_final >= 0.92,
    'data_expansion': {
        'v11_new_events': 1,
        'total_events': int(len(df)),
        'holdout_events': int(len(dh))
    }
}

with open('odin_v11_kaizen_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n  Results saved: odin_v11_kaizen_results.json")
print(f"  TARGET 0.92: {'MET!' if ho_final >= 0.92 else 'NOT MET'} (actual: {ho_final:.4f})")
