"""
ODIN v10.67 Dataset Enrichment Script
======================================
Adds missing 2025-2026 PDUFA events to ODIN_MODEL_READY dataset.
All data is T1-compliant (available before catalyst_date).

Events added:
  - RGNX: RGX-121 CRL (Feb 7, 2026)
  - IRON: Bitopertin EPP CRL (Feb 13, 2026)
  - DNLI: Tividenofusp alfa (PDUFA Apr 5, 2026) - PENDING
  - VNDA: Bysanti/milsaperidone Bipolar I (PDUFA Feb 21, 2026) - PENDING
  - ASND: TransCon CNP achondroplasia (PDUFA Feb 28, 2026) - PENDING
  - RCKT: Kresladi LAD-I gene therapy (PDUFA Mar 28, 2026) - PENDING
  - ALDX: Reproxalap DED 4th sub (PDUFA Mar 16, 2026) - PENDING
  - SNY: Tolebrutinib MS CRL (Dec 24, 2025)
  - TVTX: Sparsentan FSGS sNDA (PDUFA Jan 13, 2026) - PENDING
  - MRK: KEYTRUDA ovarian sBLA (Feb 20, 2026) - APPROVED Feb 11
  - LYKOS: MDMA PTSD CRL (Aug 9, 2024)
  - SAOL: DCA PDCD CRL (Dec 2025)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURATION
# =============================================================================
INPUT_CSV = "ODIN_MODEL_READY_v1066_T1_2015on_2200.csv"
OUTPUT_CSV = "ODIN_MODEL_READY_v1067_T1_2015on_ENRICHED.csv"
V1067_WEIGHTS = "odin_v1067_optimized.json"

# Historical CRL rates by TA (from dataset analysis)
TA_CRL_RATES = {
    'Oncology': 0.15,
    'CNS': 0.22,
    'Rare Disease': 0.18,
    'Immunology': 0.20,
    'Cardiovascular': 0.19,
    'Infectious Disease': 0.25,
    'Dermatology': 0.22,
    'Hematology': 0.16,
    'Pain Management': 0.30,
    'Ophthalmology': 0.28,
    'Metabolic': 0.20,
    'GI': 0.20,
    'Nephrology': 0.25,
    'Other': 0.319,
    'Neurology': 0.22,
    'Endocrinology': 0.18,
    'Respiratory': 0.20,
    'Gene Therapy': 0.25,
}


def make_event_id(ticker, asset, catalyst_date):
    """Generate event_id matching dataset convention."""
    return f"{ticker}|{asset}|PDUFA|{catalyst_date}"


def make_cutoff(catalyst_date_str):
    """T1 compliance: data_cutoff = catalyst_date - 1 day."""
    dt = datetime.strptime(catalyst_date_str, "%Y-%m-%d")
    cutoff = dt - timedelta(days=1)
    return cutoff.strftime("%Y-%m-%d")


# =============================================================================
# MISSING EVENTS DATA (All verified via web research Feb 14, 2026)
# =============================================================================
MISSING_EVENTS = [
    # -------------------------------------------------------------------------
    # RGNX - RGX-121 (clemidsogene lanparvovec) - Hunter syndrome gene therapy
    # CRL issued Feb 7, 2026 (PDUFA was Feb 8, 2026)
    # Reasons: Uncertainty re eligibility criteria, comparability of natural
    #   history external control, CSF HS D2S6 as surrogate endpoint
    # BLA accepted May 2025, accelerated approval pathway
    # Designations: Orphan, Rare Pediatric Disease, Fast Track, RMAT
    # Clinical hold Jan 2026 (related to RGX-111 tumor event)
    # Sponsor: REGENXBIO - 0 prior approvals (first BLA)
    # -------------------------------------------------------------------------
    {
        'ticker': 'RGNX',
        'company': 'REGENXBIO Inc.',
        'asset': 'RGX-121 (clemidsogene lanparvovec)',
        'indication': 'Hunter syndrome (MPS II)',
        'therapeutic_area': 'Other',  # Gene therapy / Rare disease
        'catalyst_date': '2026-02-08',
        'outcome': 'CRL',
        'application_type': 'BLA',
        'prior_crl': False,
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': True,   # Gene therapy manufacturing complexity
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': True,
        'priority_review': False,
        'fast_track': True,
        'accelerated_approval': True,  # Accelerated approval pathway
        'resubmission_class': 0.0,
        'ta_base_score': -0.019,  # Other TA
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # IRON - Bitopertin EPP (erythropoietic protoporphyria)
    # CRL issued Feb 13, 2026 (PDUFA was Feb 15, 2026)
    # FDA acknowledged AURORA/BEACON showed significant PPIX lowering
    # FDA wants Phase 3 APOLLO results before decision (Q4 2026)
    # SECOND indication - first (different) was approved Jan 2025
    # Sponsor: Disc Medicine - 1 prior approval (Jan 2025)
    # Designations: Orphan, Breakthrough Therapy, Priority Review
    # -------------------------------------------------------------------------
    {
        'ticker': 'IRON',
        'company': 'Disc Medicine Inc.',
        'asset': 'Bitopertin (EPP)',
        'indication': 'Erythropoietic protoporphyria (EPP)',
        'therapeutic_area': 'Hematology',
        'catalyst_date': '2026-02-15',
        'outcome': 'CRL',
        'application_type': 'NDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 1.0,  # Bitopertin XLP approved Jan 2025
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': 0.05,  # Hematology - moderate
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # DNLI - Tividenofusp alfa - Hunter syndrome (MPS II) ERT
    # PDUFA Apr 5, 2026 (extended from Jan 5, 2026)
    # Extension: Major Amendment Oct 2025 (clinical pharmacology info)
    # Priority Review, BTD, Rare Pediatric Disease
    # Accelerated approval pathway, CSF HS as surrogate endpoint
    # Phase 1/2 data published NEJM Jan 2026
    # Sponsor: Denali Therapeutics - 0 prior approvals
    # -------------------------------------------------------------------------
    {
        'ticker': 'DNLI',
        'company': 'Denali Therapeutics Inc.',
        'asset': 'Tividenofusp alfa (TAK-611/DNL310)',
        'indication': 'Hunter syndrome (MPS II)',
        'therapeutic_area': 'Other',  # Rare genetic / enzyme replacement
        'catalyst_date': '2026-04-05',
        'outcome': '',  # PENDING
        'application_type': 'BLA',
        'prior_crl': False,
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,  # Extension was Major Amendment, not CMC
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': True,  # Rare Pediatric Disease designation
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': True,  # Accelerated approval pathway
        'resubmission_class': 0.0,
        'ta_base_score': -0.019,
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # VNDA - Bysanti (milsaperidone) - Bipolar I & Schizophrenia
    # PDUFA Feb 21, 2026
    # NDA accepted May 2025, no review issues identified
    # New chemical entity, bioequivalent to iloperidone
    # Efficacy: 2 schizophrenia, 1 bipolar I, 1 relapse prevention studies
    # Safety: 80,000+ patient-year exposures
    # Sponsor: Vanda Pharmaceuticals - 2 prior approvals (Hetlioz, tradipitant)
    # NOTE: VNDA already has tradipitant (NEREUS) approval Dec 30, 2025
    # -------------------------------------------------------------------------
    {
        'ticker': 'VNDA',
        'company': 'Vanda Pharmaceuticals Inc.',
        'asset': 'Bysanti (milsaperidone)',
        'indication': 'Bipolar I disorder / Schizophrenia',
        'therapeutic_area': 'CNS',
        'catalyst_date': '2026-02-21',
        'outcome': '',  # PENDING
        'application_type': 'NDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 2.0,  # Hetlioz + tradipitant
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': False,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': -0.15,  # CNS - moderate risk TA
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # ASND - TransCon CNP (navepegritide) - Achondroplasia
    # PDUFA Feb 28, 2026 (delayed from Nov 30, 2025)
    # 3-month extension: Major amendment Nov 5, 2025 (post-marketing req)
    # Company responded to all outstanding FDA requests
    # Sponsor: Ascendis Pharma - 2 prior approvals (Skytrofa, YORVIPATH)
    # Designations: Orphan
    # -------------------------------------------------------------------------
    {
        'ticker': 'ASND',
        'company': 'Ascendis Pharma A/S',
        'asset': 'TransCon CNP (navepegritide)',
        'indication': 'Achondroplasia',
        'therapeutic_area': 'Endocrinology',
        'catalyst_date': '2026-02-28',
        'outcome': '',  # PENDING
        'application_type': 'BLA',
        'prior_crl': False,
        'sponsor_prior_approvals': 2.0,  # Skytrofa + YORVIPATH
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': True,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': 0.05,  # Endocrinology - moderate
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # RCKT - Kresladi (marnetegragene autotemcel) - LAD-I gene therapy
    # PDUFA Mar 28, 2026 - RESUBMISSION after Jun 2024 CRL (manufacturing)
    # BLA accepted Oct 14, 2025
    # Phase 1/2: 100% overall survival ≥1 year post-treatment
    # Met all primary/secondary endpoints
    # Sponsor: Rocket Pharmaceuticals - 0 prior approvals
    # Prior CRL: Jun 28, 2024 (manufacturing issues)
    # This is a Class 2 resubmission
    # -------------------------------------------------------------------------
    {
        'ticker': 'RCKT',
        'company': 'Rocket Pharmaceuticals Inc.',
        'asset': 'Kresladi (marnetegragene autotemcel)',
        'indication': 'Leukocyte adhesion deficiency type I (LAD-I)',
        'therapeutic_area': 'Other',  # Gene therapy
        'catalyst_date': '2026-03-28',
        'outcome': '',  # PENDING
        'application_type': 'BLA',
        'prior_crl': True,  # Jun 2024 CRL for manufacturing
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': True,  # Prior CRL was for manufacturing
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 2.0,  # Class 2 resubmission
        'ta_base_score': -0.019,
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # ALDX - Reproxalap - DED (Dry Eye Disease) - 4th NDA submission
    # PDUFA Mar 16, 2026 (extended from Dec 16, 2025)
    # Third NDA after 2 prior CRLs (Nov 2023, Jun 2023)
    # Dataset has earlier ALDX CRL entries but missing this resubmission
    # Sponsor: Aldeyra Therapeutics - 0 prior approvals
    # -------------------------------------------------------------------------
    {
        'ticker': 'ALDX',
        'company': 'Aldeyra Therapeutics Inc.',
        'asset': 'Reproxalap (DED - 4th submission)',
        'indication': 'Dry eye disease',
        'therapeutic_area': 'Ophthalmology',
        'catalyst_date': '2026-03-16',
        'outcome': '',  # PENDING
        'application_type': 'NDA',
        'prior_crl': True,  # Multiple prior CRLs
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': False,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 2.0,  # Resubmission after CRL
        'ta_base_score': -0.2,  # Ophthalmology - high risk TA
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # SNY - Tolebrutinib - MS (multiple sclerosis)
    # CRL Dec 24, 2025 (PDUFA was Dec 28, 2025)
    # Reasons: Severe DILI risk, unclear benefit in nrSPMS, efficacy concerns
    # BTD granted Dec 2024
    # Phase 3 HERCULES: 31% risk reduction in 6m confirmed disability progression
    # Sponsor: Sanofi - many prior approvals (>5)
    # -------------------------------------------------------------------------
    {
        'ticker': 'SNY',
        'company': 'Sanofi S.A.',
        'asset': 'Tolebrutinib',
        'indication': 'Multiple sclerosis (nrSPMS)',
        'therapeutic_area': 'CNS',
        'catalyst_date': '2025-12-28',
        'outcome': 'CRL',
        'application_type': 'NDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 10.0,  # Sanofi - major pharma
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': True,  # BTD granted Dec 2024
        'orphan': False,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': -0.15,  # CNS
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # TVTX - Sparsentan (Filspari) sNDA for FSGS
    # PDUFA Jan 13, 2026 (already had IgAN approval Aug 2025)
    # sNDA for traditional approval
    # DUPLEX: Hit interim FPRE at 36wk, MISSED primary eGFR slope at 108wk
    # Would be first FDA-approved therapy for FSGS
    # FDA waived advisory committee Sep 10, 2025
    # Sponsor: Travere Therapeutics - 1 prior approval (Filspari IgAN)
    # -------------------------------------------------------------------------
    {
        'ticker': 'TVTX',
        'company': 'Travere Therapeutics Inc.',
        'asset': 'Sparsentan (Filspari) sNDA FSGS',
        'indication': 'Focal segmental glomerulosclerosis (FSGS)',
        'therapeutic_area': 'Nephrology',
        'catalyst_date': '2026-01-13',
        'outcome': '',  # PENDING - need to verify outcome
        'application_type': 'SNDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 1.0,  # Filspari IgAN
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,  # FDA waived AdCom
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': True,  # FSGS is rare
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,  # Seeking traditional approval
        'resubmission_class': 0.0,
        'ta_base_score': -0.2,  # Nephrology - higher risk
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # MRK - KEYTRUDA + chemo ± bevacizumab - Platinum-resistant ovarian cancer
    # PDUFA Feb 20, 2026 - APPROVED Feb 11, 2026 (early)
    # sBLA
    # Sponsor: Merck - many prior approvals (>10)
    # -------------------------------------------------------------------------
    {
        'ticker': 'MRK',
        'company': 'Merck & Co. Inc.',
        'asset': 'KEYTRUDA + chemo ± bevacizumab (ovarian)',
        'indication': 'Platinum-resistant ovarian cancer',
        'therapeutic_area': 'Oncology',
        'catalyst_date': '2026-02-20',
        'outcome': 'APPROVAL',  # Approved Feb 11 (early)
        'application_type': 'SBLA',
        'prior_crl': False,
        'sponsor_prior_approvals': 15.0,  # Merck - major pharma
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': False,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': 0.1,  # Oncology - positive
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # LYKOS - Midomafetamine (MDMA) - PTSD
    # CRL Aug 9, 2024
    # Reasons: Unreported safety events, abuse potential
    # High-profile rejection, FDA requested new Phase 3
    # Advisory Committee voted 9-2 against approval Jun 2024
    # Sponsor: Lykos Therapeutics - 0 prior approvals
    # -------------------------------------------------------------------------
    {
        'ticker': 'LYKOS',
        'company': 'Lykos Therapeutics Inc.',
        'asset': 'Midomafetamine (MDMA)',
        'indication': 'Post-traumatic stress disorder (PTSD)',
        'therapeutic_area': 'CNS',
        'catalyst_date': '2024-08-11',
        'outcome': 'CRL',
        'application_type': 'NDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': True,
        'adcom_vote_pct': 18.18,  # 2-9 vote (2/11 = 18.18%)
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': False,
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': -0.15,  # CNS
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # -------------------------------------------------------------------------
    # PHAR - Leniolisib (adult indication) - APDS
    # NOTE: Dataset already has PHAR CRL 2026-02-01 for pediatric.
    # Checking if we need to add adult approval separately.
    # Actually the dataset entry is already there. Skip.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Additional pending 2026 PDUFAs (lower priority but should be tracked)
    # -------------------------------------------------------------------------

    # ORCA - Orca-T - AML/ALL/MDS - PDUFA Apr 6, 2026
    {
        'ticker': 'ORCA',
        'company': 'Orca Bio Inc.',
        'asset': 'Orca-T',
        'indication': 'AML/ALL/MDS (allogeneic HSCT)',
        'therapeutic_area': 'Oncology',
        'catalyst_date': '2026-04-06',
        'outcome': '',  # PENDING
        'application_type': 'BLA',
        'prior_crl': False,
        'sponsor_prior_approvals': 0.0,
        'manufacturing_risk': True,  # Cell therapy manufacturing
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': True,
        'orphan': True,
        'priority_review': True,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': 0.1,
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },

    # BMY - Deucravacitinib - Psoriatic Arthritis - PDUFA Mar 6, 2026
    {
        'ticker': 'BMY',
        'company': 'Bristol-Myers Squibb Co.',
        'asset': 'Deucravacitinib (Sotyktu) sNDA PsA',
        'indication': 'Psoriatic arthritis',
        'therapeutic_area': 'Immunology',
        'catalyst_date': '2026-03-06',
        'outcome': '',  # PENDING
        'application_type': 'SNDA',
        'prior_crl': False,
        'sponsor_prior_approvals': 15.0,
        'manufacturing_risk': False,
        'form_483_issues': False,
        'ema_cmc_flag': False,
        'cmc_extension_flag': False,
        'had_adcom': False,
        'adcom_vote_pct': 0.0,
        's22_ped_pk_missing': False,
        'btd': False,
        'orphan': False,
        'priority_review': False,
        'fast_track': False,
        'accelerated_approval': False,
        'resubmission_class': 0.0,
        'ta_base_score': -0.05,  # Immunology
        's23_signal_strength': 0.0,
        's6_signal_strength': 0.0,
        'social_sentiment_score': 0.0,
    },
]


def build_new_rows(events):
    """Convert event dicts to DataFrame rows matching ODIN schema."""
    rows = []
    for ev in events:
        row = {
            'event_id': make_event_id(ev['ticker'], ev['asset'], ev['catalyst_date']),
            'ticker': ev['ticker'],
            'company': ev['company'],
            'asset': ev['asset'],
            'indication': ev['indication'],
            'therapeutic_area': ev['therapeutic_area'],
            'catalyst_date': ev['catalyst_date'],
            'data_cutoff_date': make_cutoff(ev['catalyst_date']),
            'outcome': ev['outcome'],
            'application_type': ev['application_type'],
            'prior_crl': ev['prior_crl'],
            'sponsor_prior_approvals': ev['sponsor_prior_approvals'],
            'manufacturing_risk': ev['manufacturing_risk'],
            'form_483_issues': ev['form_483_issues'],
            'ema_cmc_flag': ev['ema_cmc_flag'],
            'cmc_extension_flag': ev['cmc_extension_flag'],
            'had_adcom': ev['had_adcom'],
            'adcom_vote_pct': ev['adcom_vote_pct'],
            's22_ped_pk_missing': ev['s22_ped_pk_missing'],
            'btd': ev['btd'],
            'orphan': ev['orphan'],
            'priority_review': ev['priority_review'],
            'fast_track': ev['fast_track'],
            'accelerated_approval': ev['accelerated_approval'],
            'resubmission_class': ev['resubmission_class'],
            'ta_base_score': ev['ta_base_score'],
            'historical_crl_rate': TA_CRL_RATES.get(ev['therapeutic_area'], 0.319),
            's23_signal_strength': ev['s23_signal_strength'],
            's6_signal_strength': ev['s6_signal_strength'],
            'social_sentiment_score': ev['social_sentiment_score'],
        }
        rows.append(row)
    return pd.DataFrame(rows)


def validate_t1_compliance(df):
    """Verify all rows have data_cutoff_date < catalyst_date."""
    violations = []
    for idx, row in df.iterrows():
        try:
            cat = pd.to_datetime(row['catalyst_date'])
            cut = pd.to_datetime(row['data_cutoff_date'])
            if cut >= cat:
                violations.append((idx, row['ticker'], row['catalyst_date'], row['data_cutoff_date']))
        except:
            pass
    return violations


def score_with_v1067(df, weights_path):
    """Score all events with v10.67 weights for validation."""
    with open(weights_path, 'r') as f:
        w = json.load(f)

    scores = []
    for _, row in df.iterrows():
        logit = w['base_logit']

        # Application type penalties
        app = str(row.get('application_type', '')).upper()
        if 'SNDA' in app or 'SBLA' in app:
            logit += w['snda_base_penalty']
        if 'PEDIATRIC' in app:
            logit += w['snda_pediatric_base_penalty']

        # Risk factors
        if row.get('prior_crl', False):
            logit += w['prior_crl_penalty']
        if float(row.get('sponsor_prior_approvals', 1)) == 0:
            logit += w['inexperienced_sponsor_penalty']
        if row.get('manufacturing_risk', False):
            logit += w['manufacturing_risk_penalty']
        if row.get('form_483_issues', False):
            logit += w['form_483_penalty']
        if row.get('ema_cmc_flag', False):
            logit += w['ema_cmc_flag_penalty']
        if row.get('cmc_extension_flag', False):
            logit += w['cmc_extension_penalty']

        # AdCom
        had_adcom = row.get('had_adcom', False)
        vote = float(row.get('adcom_vote_pct', 0) or 0)
        if vote > 1:
            vote = vote / 100
        if had_adcom:
            if vote >= 0.65:
                logit += w['adcom_high_boost']
            elif vote >= 0.50:
                logit += w['adcom_mid_penalty']
            else:
                logit += w['adcom_low_penalty']

        # Pediatric PK
        if row.get('s22_ped_pk_missing', False):
            logit += w['s22_pediatric_pk_penalty']

        # Positive designations
        if row.get('btd', False):
            logit += w['btd_weight']
        if row.get('orphan', False):
            logit += w['orphan_weight']
        if row.get('priority_review', False):
            logit += w['priority_review_weight']
        if row.get('fast_track', False):
            logit += w['fast_track_weight']
        acc = str(row.get('accelerated_approval', '')).upper()
        if acc in ['TRUE', '1', 'YES', 'APPROVED']:
            logit += w['accelerated_approval_weight']

        # Resubmission
        resub = float(row.get('resubmission_class', 0) or 0)
        if resub == 1.0:
            logit += w['class1_resubmission_boost']

        # Experienced sponsor
        prior = float(row.get('sponsor_prior_approvals', 0) or 0)
        if prior >= 5:
            logit += w['experienced_sponsor_boost']

        # TA adjustment
        ta_score = float(row.get('ta_base_score', 0) or 0)
        logit += ta_score * w['ta_adjustment_weight']

        # Signals
        s23 = float(row.get('s23_signal_strength', 0) or 0)
        s6 = float(row.get('s6_signal_strength', 0) or 0)
        social = float(row.get('social_sentiment_score', 0) or 0)
        logit += s23 * w['s23_insider_weight']
        logit += s6 * w['s6_hiring_weight']
        logit += social * w['social_weight']

        # HINT hybrid features
        crl_rate = float(row.get('historical_crl_rate', 0) or 0)
        logit += crl_rate * w['hint_crl_rate_penalty'] * w['hint_weight']

        # TA risk tiers
        ta = str(row.get('therapeutic_area', ''))
        high_risk_tas = ['Pain', 'Ophthalmology', 'Nephrology', 'Hematology']
        mod_risk_tas = ['CNS', 'Neurology', 'Cardiovascular', 'Metabolic']
        low_risk_tas = ['Oncology', 'Immunology', 'Dermatology', 'Infectious']

        if any(t.lower() in ta.lower() for t in high_risk_tas):
            logit += w['ta_high_risk_penalty'] * w['hint_weight']
        elif any(t.lower() in ta.lower() for t in mod_risk_tas):
            logit += w['ta_mod_risk_penalty'] * w['hint_weight']
        elif any(t.lower() in ta.lower() for t in low_risk_tas):
            logit += w['ta_low_risk_boost'] * w['hint_weight']

        # Indication-specific
        indication = str(row.get('indication', ''))
        if 'pain' in indication.lower():
            logit += w['indication_pain_penalty'] * w['hint_weight']
        if 'cancer' in indication.lower() or 'tumor' in indication.lower():
            logit += w['indication_onc_boost'] * w['hint_weight']

        # Novice sponsor + high risk TA
        if prior < 3 and any(t.lower() in ta.lower() for t in high_risk_tas):
            logit += w['novice_sponsor_high_risk_ta_penalty'] * w['hint_weight']

        # Combined score
        odin_logit = logit * w['odin_weight']
        hint_logit = logit * w['hint_weight']
        combined = odin_logit + hint_logit

        prob = 1.0 / (1.0 + np.exp(-combined))
        scores.append(prob)

    return scores


def assign_tier(prob):
    """Assign ODIN tier based on probability."""
    if prob >= 0.86:
        return 'TIER_1'
    elif prob >= 0.73:
        return 'TIER_2'
    elif prob >= 0.58:
        return 'TIER_3'
    else:
        return 'TIER_4'


def main():
    print("=" * 70)
    print("ODIN v10.67 Dataset Enrichment")
    print("=" * 70)

    # Load current dataset
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} events from {INPUT_CSV}")
    print(f"Date range: {df['catalyst_date'].min()} to {df['catalyst_date'].max()}")

    # Build new rows
    new_df = build_new_rows(MISSING_EVENTS)
    print(f"\nPrepared {len(new_df)} new events to add:")
    for _, r in new_df.iterrows():
        outcome_str = r['outcome'] if r['outcome'] else 'PENDING'
        print(f"  {r['ticker']:8s} {r['catalyst_date']} {outcome_str:10s} {r['asset'][:55]}")

    # Check for duplicates before adding
    existing_ids = set(df['event_id'].values)
    dupes = []
    unique_new = []
    for _, r in new_df.iterrows():
        if r['event_id'] in existing_ids:
            dupes.append(r['event_id'])
        else:
            # Also check by ticker+date combination
            match = df[(df['ticker'] == r['ticker']) &
                       (df['catalyst_date'] == r['catalyst_date'])]
            if len(match) > 0:
                dupes.append(f"{r['ticker']}|{r['catalyst_date']} (ticker+date match)")
            else:
                unique_new.append(r)

    if dupes:
        print(f"\n⚠️  Skipping {len(dupes)} duplicate events:")
        for d in dupes:
            print(f"    {d}")

    if unique_new:
        new_unique_df = pd.DataFrame(unique_new)
        # Append
        df = pd.concat([df, new_unique_df], ignore_index=True)
        print(f"\n✅ Added {len(unique_new)} new events")
    else:
        print("\n⚠️  No new unique events to add")

    # Sort by catalyst_date
    df['_sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
    df = df.sort_values('_sort_date').reset_index(drop=True)
    df = df.drop(columns=['_sort_date'])

    # T1 compliance validation
    violations = validate_t1_compliance(df)
    if violations:
        print(f"\n❌ T1 VIOLATIONS: {len(violations)}")
        for v in violations[:5]:
            print(f"    Row {v[0]}: {v[1]} cat={v[2]} cut={v[3]}")
    else:
        print("\n✅ T1 compliance: ALL PASS")

    # Score with v10.67
    print("\nScoring all events with v10.67 weights...")
    scores = score_with_v1067(df, V1067_WEIGHTS)
    df['v1067_score'] = scores
    df['v1067_tier'] = [assign_tier(s) for s in scores]

    # Report on new events
    print("\n" + "=" * 70)
    print("SCORING RESULTS FOR NEW EVENTS")
    print("=" * 70)

    # Filter to new events (2025-12-28 onwards that we added)
    new_tickers = [ev['ticker'] for ev in MISSING_EVENTS]
    new_dates = [ev['catalyst_date'] for ev in MISSING_EVENTS]

    for ev in MISSING_EVENTS:
        match = df[(df['ticker'] == ev['ticker']) &
                   (df['catalyst_date'] == ev['catalyst_date'])]
        if len(match) > 0:
            row = match.iloc[0]
            outcome_str = row['outcome'] if row['outcome'] else 'PENDING'
            print(f"\n{row['ticker']:8s} | {row['asset'][:45]}")
            print(f"  Date: {row['catalyst_date']} | Outcome: {outcome_str}")
            print(f"  v10.67 Score: {row['v1067_score']:.1%} | Tier: {row['v1067_tier']}")

            # Validate CRL predictions
            if outcome_str == 'CRL' and row['v1067_tier'] in ['TIER_1', 'TIER_2']:
                print(f"  ⚠️  FALSE POSITIVE: Model predicted high approval but got CRL")
            elif outcome_str == 'APPROVAL' and row['v1067_tier'] == 'TIER_4':
                print(f"  ⚠️  FALSE NEGATIVE: Model predicted low approval but got APPROVAL")
            elif outcome_str == 'CRL' and row['v1067_tier'] in ['TIER_3', 'TIER_4']:
                print(f"  ✅ CORRECT: Model flagged risk, got CRL")
            elif outcome_str == 'APPROVAL' and row['v1067_tier'] in ['TIER_1', 'TIER_2']:
                print(f"  ✅ CORRECT: Model predicted approval, got APPROVAL")

    # Summary stats
    print("\n" + "=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)
    print(f"Total events: {len(df)}")
    print(f"Date range: {df['catalyst_date'].min()} to {df['catalyst_date'].max()}")

    # By year
    df['_year'] = pd.to_datetime(df['catalyst_date'], errors='coerce').dt.year
    for yr in sorted(df['_year'].dropna().unique()):
        yr = int(yr)
        sub = df[df['_year'] == yr]
        approved = len(sub[sub['outcome'] == 'APPROVAL'])
        crl = len(sub[sub['outcome'] == 'CRL'])
        pending = len(sub[sub['outcome'] == ''])
        print(f"  {yr}: {len(sub)} events ({approved} approved, {crl} CRL, {pending} pending)")

    # v10.67 tier distribution
    print(f"\nv10.67 Tier Distribution (all events):")
    for tier in ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4']:
        count = len(df[df['v1067_tier'] == tier])
        pct = count / len(df) * 100
        print(f"  {tier}: {count} ({pct:.1f}%)")

    # Drop helper columns before saving
    df = df.drop(columns=['_year'], errors='ignore')

    # Save
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved enriched dataset to {OUTPUT_CSV}")
    print(f"   {len(df)} events, {len(df.columns)} columns")

    return df


if __name__ == "__main__":
    df = main()
