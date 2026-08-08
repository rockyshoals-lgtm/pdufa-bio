#!/usr/bin/env python3
"""
ChEMBL Enrichment Cache Loader for ODIN v10 / GUNGNIR v39 Integration

Usage:
    from chembl_enrichment_loader import ChEMBLEnrichmentLoader

    loader = ChEMBLEnrichmentLoader('chembl_enrichment_cache.json')

    # Get features for a drug
    features = loader.get_features('Pembrolizumab')

    # Merge with training data
    df_enriched = loader.enrich_dataframe(df, drug_column='asset')
"""

import json
import pandas as pd
from typing import Dict, Optional, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChEMBLEnrichmentLoader:
    """Load and apply ChEMBL enrichment cache to training datasets."""

    def __init__(self, cache_path: str):
        """
        Initialize loader with cache file.

        Args:
            cache_path: Path to chembl_enrichment_cache.json
        """
        with open(cache_path, 'r') as f:
            self.cache = json.load(f)

        self.logger = logger
        self.logger.info(f"Loaded ChEMBL cache with {len(self.cache)} drugs")

        # Build lookup variants (exact + normalized)
        self.cache_lower = {k.lower(): v for k, v in self.cache.items()}

    def get_features(self, drug_name: str, strict: bool = False) -> Optional[Dict]:
        """
        Get ChEMBL features for a drug.

        Args:
            drug_name: Drug name (case-insensitive)
            strict: If True, only exact matches; else try fuzzy match

        Returns:
            Dict of features or None if not found
        """
        # Exact match
        if drug_name in self.cache:
            return self.cache[drug_name]

        # Case-insensitive match
        drug_lower = drug_name.lower()
        if drug_lower in self.cache_lower:
            return self.cache_lower[drug_lower]

        if not strict:
            # Partial match (substring)
            for key, val in self.cache_lower.items():
                if key in drug_lower or drug_lower in key:
                    self.logger.warning(f"Fuzzy match: '{drug_name}' -> '{key}'")
                    return val

        return None

    def expand_features(self, features: Dict) -> Dict:
        """
        Expand raw cache features to ODIN/GUNGNIR model features.

        Args:
            features: Raw features from cache

        Returns:
            Expanded feature dict with categorical encodings
        """
        expanded = features.copy()

        # Target class encoding
        target_class_map = {
            'kinase': 1,
            'gpcr': 2,
            'enzyme': 3,
            'receptor_tyrosine_kinase': 4,
            'immune_checkpoint': 5,
            'growth_factor': 6,
            'ion_channel': 7,
            'immune_receptor': 8,
            'immune_cell': 9,
        }
        target_class = features.get('target_class', 'other')
        expanded['chembl_target_class_code'] = target_class_map.get(target_class, 0)

        # One-hot target class
        for target_class_name in target_class_map.keys():
            expanded[f'chembl_target_class_{target_class_name}'] = \
                1 if target_class == target_class_name else 0

        # Mechanism type encoding
        mechanism_type_map = {
            'inhibitor': 1,
            'antagonist': 2,
            'agonist': 3,
            'activator': 4,
            'modulator': 5,
            'antagonist_antibody': 6,
            'bispecific_antibody': 7,
            'antibody_drug_conjugate': 8,
            'cell_therapy': 9,
        }
        mech_type = features.get('mechanism_type', 'other')
        expanded['chembl_mechanism_code'] = mechanism_type_map.get(mech_type, 0)

        # One-hot mechanism type
        for mech_name in mechanism_type_map.keys():
            expanded[f'chembl_mech_{mech_name}'] = \
                1 if mech_type == mech_name else 0

        # Multi-target indicator
        num_mechanisms = len(features.get('mechanisms', []))
        expanded['chembl_num_targets'] = num_mechanisms
        expanded['chembl_is_multi_target'] = 1 if num_mechanisms > 1 else 0

        # Biologic type breakdown (for GUNGNIR)
        mol_type = features.get('molecular_type', 'unknown')
        expanded['chembl_is_antibody'] = 1 if mol_type == 'antibody' else 0
        expanded['chembl_is_car_t'] = 1 if mol_type == 'cell_therapy' else 0
        expanded['chembl_is_adc'] = \
            1 if 'drug_conjugate' in mech_type else 0
        expanded['chembl_is_bispecific'] = \
            1 if 'bispecific' in mech_type else 0

        # Competition indicators
        expanded['chembl_has_competitor'] = features.get('has_approved_competitor', 0)
        expanded['chembl_first_in_class'] = features.get('first_in_class', 0)

        # Small molecule properties (if present)
        if 'ro5_violations' in features:
            expanded['chembl_ro5_violations'] = features['ro5_violations']
            expanded['chembl_ro5_compliant'] = 1 if features['ro5_violations'] <= 1 else 0

        if 'alogp' in features:
            expanded['chembl_alogp'] = features['alogp']
            expanded['chembl_alogp_optimal'] = 1 if 1 <= features['alogp'] <= 3 else 0

        return expanded

    def enrich_dataframe(
        self,
        df: pd.DataFrame,
        drug_column: str = 'asset',
        expand: bool = True,
        fill_value: float = -999.0,
    ) -> pd.DataFrame:
        """
        Add ChEMBL features to a dataframe.

        Args:
            df: Input dataframe (must contain drug_column)
            drug_column: Column name containing drug names
            expand: If True, create expanded feature set
            fill_value: Value to use for missing drugs

        Returns:
            DataFrame with added ChEMBL features
        """
        df = df.copy()

        # Get features for each drug
        enrichment_rows = []
        for idx, row in df.iterrows():
            drug_name = row[drug_column]

            # Look up in cache
            features = self.get_features(drug_name)

            if features:
                if expand:
                    features = self.expand_features(features)
                enrichment_rows.append(features)
            else:
                # Create null feature dict
                enrichment_rows.append({})

        # Create enrichment dataframe
        enrichment_df = pd.DataFrame(enrichment_rows)

        # Identify all possible columns
        if expand:
            # Predict common expanded columns
            common_cols = [
                'chembl_target_class_code', 'chembl_mechanism_code',
                'chembl_is_biologic', 'chembl_num_targets', 'chembl_is_multi_target',
                'chembl_first_in_class', 'chembl_has_competitor',
                'chembl_is_antibody', 'chembl_is_car_t', 'chembl_is_adc', 'chembl_is_bispecific',
                'chembl_ro5_violations', 'chembl_ro5_compliant',
                'chembl_alogp', 'chembl_alogp_optimal',
            ]
        else:
            common_cols = [
                'chembl_id', 'molecule_type', 'max_phase', 'first_approval',
                'first_in_class', 'is_biologic', 'target_class',
                'mechanism_type', 'has_approved_competitor',
            ]

        # Fill missing columns with fill_value
        for col in common_cols:
            if col not in enrichment_df.columns:
                enrichment_df[col] = fill_value
            elif enrichment_df[col].dtype in ['float64', 'int64']:
                enrichment_df[col] = enrichment_df[col].fillna(fill_value)

        # Concatenate with original
        df_enriched = pd.concat([df.reset_index(drop=True),
                                 enrichment_df.reset_index(drop=True)],
                                axis=1)

        # Log coverage
        matched = enrichment_df['chembl_id'].notna().sum()
        coverage = 100 * matched / len(df)
        self.logger.info(f"Enrichment coverage: {matched}/{len(df)} ({coverage:.1f}%)")

        return df_enriched

    def get_feature_importance_hints(self) -> Dict[str, List[str]]:
        """Return expected feature importance hints for ODIN/GUNGNIR."""
        return {
            'odin_expected_strong': [
                'chembl_is_biologic',  # Antibodies have different approval rates
                'chembl_first_in_class',  # Novel targets = higher risk/reward
                'chembl_target_class_code',  # Kinase vs GPCR vs enzyme = different risk profiles
                'chembl_mechanism_code',  # Inhibitor vs antagonist vs agonist = different mechanisms
            ],
            'odin_expected_moderate': [
                'chembl_has_competitor',  # Crowded market lowers approval
                'chembl_num_targets',  # Multi-target = broader profile
                'chembl_ro5_violations',  # Drug-like properties affect PK/safety
            ],
            'gungnir_expected_strong': [
                'chembl_is_antibody',  # Immune endpoints differ
                'chembl_is_multi_target',  # Broader mechanism = harder endpoints
                'chembl_first_in_class',  # Novel targets = harder to validate
            ],
            'gungnir_expected_moderate': [
                'chembl_is_car_t',  # Unique readout challenges (CRS, expansion)
                'chembl_target_class_code',  # Immune vs kinase endpoints differ
            ],
        }

    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the cache."""
        drugs = list(self.cache.values())

        return {
            'total_drugs': len(self.cache),
            'small_molecules': sum(1 for d in drugs if not d.get('is_biologic')),
            'biologics': sum(1 for d in drugs if d.get('is_biologic')),
            'first_in_class': sum(1 for d in drugs if d.get('first_in_class')),
            'approved': sum(1 for d in drugs if d.get('max_phase') == 4),
            'target_classes': list(set(d.get('target_class') for d in drugs)),
            'mechanism_types': list(set(d.get('mechanism_type') for d in drugs)),
            'year_range': (
                min(d.get('first_approval', 2026) for d in drugs if d.get('first_approval')),
                max(d.get('first_approval', 1997) for d in drugs if d.get('first_approval')),
            ),
        }


if __name__ == '__main__':
    # Example usage
    loader = ChEMBLEnrichmentLoader('chembl_enrichment_cache.json')

    # Print summary
    stats = loader.summary_stats()
    print("\nCache Summary:")
    for key, val in stats.items():
        print(f"  {key}: {val}")

    # Print feature importance hints
    print("\nExpected Feature Importance:")
    hints = loader.get_feature_importance_hints()
    for model, features in hints.items():
        print(f"\n  {model}:")
        for feat in features:
            print(f"    - {feat}")

    # Example: enrich ODIN dataset
    print("\nExample: Enriching ODIN dataset...")
    odin_df = pd.read_csv('ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv', nrows=100)
    odin_enriched = loader.enrich_dataframe(odin_df, drug_column='asset', expand=True)
    print(f"Original shape: {odin_df.shape}")
    print(f"Enriched shape: {odin_enriched.shape}")
    print(f"New columns: {[c for c in odin_enriched.columns if 'chembl' in c]}")
