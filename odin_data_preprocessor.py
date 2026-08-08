#!/usr/bin/env python3
"""ODIN Data Preprocessor - Converts raw CSV to 44-feature NumPy array for GPU optimizer."""

import numpy as np
import pandas as pd
import json
import argparse
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

N_FEATURES = 44

COL_IDX = {
    'outcome': 0, 'btd': 1, 'orphan': 2, 'priority': 3, 'fast_track': 4, 'accel': 5,
    'experienced': 6, 'stack_count': 7, 'mfg_risk': 8, 'had_adcom': 9, 'adcom_vote': 10,
    'prior_crl': 11, 'resubmission_class': 12, 'first_cycle': 13,
    'ta_onco': 14, 'ta_inf': 15, 'ta_cns': 16, 'ta_rare': 17, 'ta_pain': 18,
    'ta_cardio': 19, 'ta_nephro': 20, 'ta_ophthal': 21,
    'mod_sm': 22, 'mod_antibody': 23, 'mod_adc': 24, 'mod_cell': 25, 'mod_gene': 26,
    'social_total': 27, 'cluster_sell': 28, 'pcr_extreme': 29, 'pub_volume': 30,
    'trial_velocity': 31, 'divergence': 32, 'eu_not_us': 33, 'post_sell': 34,
    'trial_design_risk': 35, 'genetic_support': 36, 'proctor_risk': 37,
    'void_6mo': 38, 'hiring_slope': 39, 'herg_risk': 40, 'logp_risk': 41,
    'timeline_delay': 42, 'single_trial': 43,
}

@dataclass
class EnrichmentData:
    lunarcrush: Dict = None
    finbrain: Dict = None
    
    def get_social_total(self, ticker: str) -> float:
        if self.lunarcrush and ticker in self.lunarcrush:
            return self.lunarcrush[ticker].get('social_total', 0.0)
        return 0.0

class ODINPreprocessor:
    def __init__(self, enrichment: EnrichmentData = None):
        self.enrichment = enrichment or EnrichmentData()
    
    def encode_bool(self, series: pd.Series) -> np.ndarray:
        result = np.zeros(len(series), dtype=np.float32)
        for i, val in enumerate(series):
            if pd.isna(val):
                result[i] = 0.0
            elif isinstance(val, bool):
                result[i] = 1.0 if val else 0.0
            elif isinstance(val, str):
                result[i] = 1.0 if val.upper() in ('TRUE', 'YES', '1') else 0.0
            else:
                result[i] = float(bool(val))
        return result
    
    def detect_resubmissions(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        n = len(df)
        prior_crl = np.zeros(n, dtype=np.float32)
        resubmission_class = np.zeros(n, dtype=np.float32)
        first_cycle = np.ones(n, dtype=np.float32)
        
        df = df.copy()
        df['catalyst_date_parsed'] = pd.to_datetime(df['catalyst_date'], format='%m/%d/%Y', errors='coerce')
        df['asset_key'] = df['asset'].str.lower().str.strip()
        df['company_key'] = df['company'].str.lower().str.strip()
        df['_row_idx'] = range(n)
        
        for (asset_key, company_key), group in df.groupby(['asset_key', 'company_key']):
            if len(group) <= 1:
                continue
            group = group.sort_values('catalyst_date_parsed')
            events = group.to_dict('records')
            prior_crl_count = 0
            prior_crl_reason = ''
            
            for i, event in enumerate(events):
                row_idx = event['_row_idx']
                if prior_crl_count > 0:
                    prior_crl[row_idx] = 1.0
                    first_cycle[row_idx] = 0.0
                    reason = str(prior_crl_reason).upper()
                    if 'CMC' in reason and 'CLINICAL' not in reason:
                        resubmission_class[row_idx] = 1.0
                    else:
                        resubmission_class[row_idx] = 2.0
                if event['outcome'] == 'CRL':
                    prior_crl_count += 1
                    prior_crl_reason = event.get('prior_crl_reason', '')
        
        detected = (prior_crl == 1).sum()
        class1 = (resubmission_class == 1).sum()
        class2 = (resubmission_class == 2).sum()
        print(f"✓ Detected {detected} resubmissions: {class1} Class 1 (CMC), {class2} Class 2 (Clinical)")
        return {'prior_crl': prior_crl, 'resubmission_class': resubmission_class, 'first_cycle': first_cycle}
    
    def map_therapeutic_area(self, ta: str) -> Dict[str, float]:
        result = {f'ta_{k}': 0.0 for k in ['onco', 'inf', 'cns', 'rare', 'pain', 'cardio', 'nephro', 'ophthal']}
        if pd.isna(ta):
            return result
        ta_lower = ta.lower()
        if any(x in ta_lower for x in ['oncol', 'cancer', 'tumor', 'hematol', 'leukemia', 'lymphoma']):
            result['ta_onco'] = 1.0
        elif any(x in ta_lower for x in ['immun', 'inflam', 'autoimmun', 'rheumat']):
            result['ta_inf'] = 1.0
        elif any(x in ta_lower for x in ['cns', 'neuro', 'psych', 'brain', 'alzheim', 'parkinson']):
            result['ta_cns'] = 1.0
        elif any(x in ta_lower for x in ['rare', 'orphan', 'genetic']):
            result['ta_rare'] = 1.0
        elif any(x in ta_lower for x in ['pain', 'analgesi', 'anesthes']):
            result['ta_pain'] = 1.0
        elif any(x in ta_lower for x in ['cardio', 'cardiol', 'heart', 'vascular']):
            result['ta_cardio'] = 1.0
        elif any(x in ta_lower for x in ['nephro', 'renal', 'kidney']):
            result['ta_nephro'] = 1.0
        elif any(x in ta_lower for x in ['ophthal', 'eye', 'retina', 'vision']):
            result['ta_ophthal'] = 1.0
        return result
    
    def map_modality(self, mod: str) -> Dict[str, float]:
        result = {f'mod_{k}': 0.0 for k in ['sm', 'antibody', 'adc', 'cell', 'gene']}
        if pd.isna(mod):
            result['mod_sm'] = 1.0
            return result
        mod_lower = mod.lower()
        if any(x in mod_lower for x in ['gene therap', 'aav', 'viral vector']):
            result['mod_gene'] = 1.0
        elif any(x in mod_lower for x in ['cell therap', 'car-t', 'car t']):
            result['mod_cell'] = 1.0
        elif any(x in mod_lower for x in ['adc', 'antibody-drug', 'conjugate']):
            result['mod_adc'] = 1.0
        elif any(x in mod_lower for x in ['antibod', 'monoclonal', 'mab', 'vaccine']):
            result['mod_antibody'] = 1.0
        else:
            result['mod_sm'] = 1.0
        return result
    
    def process(self, df: pd.DataFrame) -> np.ndarray:
        n = len(df)
        data = np.zeros((n, N_FEATURES), dtype=np.float32)
        
        # Outcome
        data[:, COL_IDX['outcome']] = np.where(df['outcome'].str.upper() == 'APPROVAL', 1.0, 0.0)
        
        # Designations
        data[:, COL_IDX['btd']] = self.encode_bool(df['btd'])
        data[:, COL_IDX['orphan']] = self.encode_bool(df['orphan'])
        data[:, COL_IDX['priority']] = self.encode_bool(df['priority_review'])
        data[:, COL_IDX['fast_track']] = self.encode_bool(df['fast_track'])
        
        # Accelerated approval
        accel = df['accelerated_approval'].fillna('').astype(str).str.upper()
        data[:, COL_IDX['accel']] = np.where(accel.isin(['TRUE', 'YES', '1', 'ACCELERATED']), 1.0, 0.0)
        
        # Sponsor experience
        data[:, COL_IDX['experienced']] = self.encode_bool(df['experienced_sponsor'])
        data[:, COL_IDX['stack_count']] = pd.to_numeric(df['designation_stack_count'], errors='coerce').fillna(0).values
        
        # Manufacturing risk
        data[:, COL_IDX['mfg_risk']] = self.encode_bool(df['manufacturing_risk'])
        
        # AdCom
        data[:, COL_IDX['had_adcom']] = self.encode_bool(df['had_adcom'])
        adcom_vote = pd.to_numeric(df['adcom_vote_pct'], errors='coerce').fillna(50) / 100.0
        data[:, COL_IDX['adcom_vote']] = adcom_vote.values.astype(np.float32)
        
        # Resubmissions (DETECTED)
        resub_data = self.detect_resubmissions(df)
        data[:, COL_IDX['prior_crl']] = resub_data['prior_crl']
        data[:, COL_IDX['resubmission_class']] = resub_data['resubmission_class']
        data[:, COL_IDX['first_cycle']] = resub_data['first_cycle']
        
        # Therapeutic areas
        for i, ta in enumerate(df['therapeutic_area']):
            ta_map = self.map_therapeutic_area(ta)
            for key, val in ta_map.items():
                data[i, COL_IDX[key]] = val
        
        # Modalities
        for i, mod in enumerate(df['modality']):
            mod_map = self.map_modality(mod)
            for key, val in mod_map.items():
                data[i, COL_IDX[key]] = val
        
        # Social signals from enrichment
        social_matched = 0
        for i, ticker in enumerate(df['ticker']):
            social = self.enrichment.get_social_total(ticker)
            if social != 0:
                data[i, COL_IDX['social_total']] = social
                social_matched += 1
        print(f"✓ LunarCrush signals matched: {social_matched}/{n} tickers ({100*social_matched/n:.1f}%)")
        
        # Placeholder signals
        for sig in ['cluster_sell', 'pcr_extreme', 'pub_volume', 'trial_velocity', 'divergence',
                   'eu_not_us', 'post_sell', 'trial_design_risk', 'genetic_support', 'proctor_risk',
                   'void_6mo', 'hiring_slope', 'herg_risk', 'logp_risk', 'timeline_delay', 'single_trial']:
            data[:, COL_IDX[sig]] = 0.0
        
        return data
    
    def validate(self, data: np.ndarray, df: pd.DataFrame) -> Dict:
        n, f = data.shape
        assert f == N_FEATURES, f"Feature count mismatch: {f} != {N_FEATURES}"
        
        outcomes = data[:, COL_IDX['outcome']]
        approvals = (outcomes == 1).sum()
        crls = (outcomes == 0).sum()
        
        print(f"✓ Outcome distribution: {approvals} approvals ({100*approvals/n:.1f}%), {crls} CRLs ({100*crls/n:.1f}%)")
        
        # Feature coverage
        coverage = {}
        low_coverage = []
        for name, idx in COL_IDX.items():
            col = data[:, idx]
            cov = 100 * (col != 0).sum() / n
            coverage[name] = cov
            if cov < 1.0 and name != 'outcome':
                low_coverage.append(name)
        
        if low_coverage:
            print(f"⚠ Low coverage features (<1%): {low_coverage}")
        
        return {'coverage': coverage, 'approvals': int(approvals), 'crls': int(crls)}


def main():
    parser = argparse.ArgumentParser(description='ODIN Data Preprocessor')
    parser.add_argument('csv_path', help='Path to CSV file')
    parser.add_argument('--output', '-o', default='odin_processed.npy', help='Output .npy path')
    parser.add_argument('--lunarcrush', help='Path to LunarCrush cache JSON')
    parser.add_argument('--finbrain', help='Path to FinBrain cache JSON')
    parser.add_argument('--report', help='Path to save report markdown')
    args = parser.parse_args()
    
    # Load enrichment
    enrichment = EnrichmentData()
    if args.lunarcrush and Path(args.lunarcrush).exists():
        with open(args.lunarcrush) as f:
            enrichment.lunarcrush = json.load(f)
        print(f"✓ Loaded LunarCrush cache: {len(enrichment.lunarcrush)} tickers")
    
    if args.finbrain and Path(args.finbrain).exists():
        with open(args.finbrain) as f:
            enrichment.finbrain = json.load(f)
        print(f"✓ Loaded FinBrain cache: {len(enrichment.finbrain)} tickers")
    else:
        print("⚠ No FinBrain cache - insider signals will be zero")
    
    # Load and process
    df = pd.read_csv(args.csv_path)
    print(f"✓ Loaded {len(df)} PDUFA events from {args.csv_path}")
    
    preprocessor = ODINPreprocessor(enrichment)
    data = preprocessor.process(df)
    validation = preprocessor.validate(data, df)
    
    # Save
    np.save(args.output, data)
    print(f"✓ Saved processed data to {args.output}")
    
    # Report
    if args.report:
        with open(args.report, 'w') as f:
            f.write(f"# ODIN Data Preprocessing Report\n\n")
            f.write(f"**Source:** {args.csv_path}\n")
            f.write(f"**Total Events:** {len(df)}\n")
            f.write(f"**Approvals:** {validation['approvals']}\n")
            f.write(f"**CRLs:** {validation['crls']}\n\n")
            f.write(f"## Feature Coverage\n")
            f.write(f"| Feature | Coverage |\n|---------|----------|\n")
            for name, cov in sorted(validation['coverage'].items()):
                status = "✓" if cov >= 1 else "⚠"
                f.write(f"| {name} | {cov:.1f}% {status} |\n")
        print(f"✓ Saved report to {args.report}")
    
    print(f"\n{'='*60}")
    print(f"Preprocessing complete!")
    print(f"Output shape: {data.shape}")
    print(f"Ready for GPU optimizer")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
