# ChEMBL Enrichment Cache Integration Guide

## Overview
This guide documents the ChEMBL enrichment cache built from 16 representative drugs across the 9 Realms training datasets (ODIN and GUNGNIR). The cache provides mechanism of action, target class, and molecular characteristics for feature engineering in both scoring engines.

## Cache Location
`chembl_enrichment_cache.json`

## Drugs Included (16 total)
- **Approved Small Molecules (7)**: Sparsentan, Deucravacitinib, Niraparib, Mitapivat, Alectinib, Imiquimod, Troriluzole
- **Approved Biologics (8)**: Pembrolizumab, Amivantamab, Trastuzumab deruxtecan, Semaglutide, Mosunetuzumab, Bevacizumab gamma, Daratumumab, Teriparatide
- **Cell Therapy (1)**: Idecabtagene vicleucel

## Data Fields

### Core Identifiers
- `chembl_id`: ChEMBL database identifier (CHEMBL prefix)
- `molecule_type`: Classification (small_molecule, antibody, cell_therapy, protein, gene)
- `max_phase`: Highest clinical phase reached (0-4, where 4 = approved)
- `first_approval`: Year of first regulatory approval

### Mechanism Features
- `first_in_class`: Binary (1 = novel target class, 0 = competitor exists)
- `is_biologic`: Binary (1 = monoclonal antibody/protein/cell therapy, 0 = small molecule)
- `target_class`: Primary target category
  - kinase, gpcr, enzyme, receptor_tyrosine_kinase
  - immune_checkpoint, growth_factor, ion_channel
  - immune_receptor, immune_cell
- `mechanism_type`: Type of interaction
  - inhibitor, antagonist, agonist, activator, modulator
  - antagonist_antibody, bispecific_antibody, antibody_drug_conjugate
  - cell_therapy
- `has_approved_competitor`: Binary (1 = same target has approved competitors)
- `mechanisms`: Array of mechanism details
  - `action`: INHIBITOR, ANTAGONIST, AGONIST, ACTIVATOR, MODULATOR, OTHER
  - `target`: Target protein or pathway name

### Molecular Properties (Small Molecules Only)
- `ro5_violations`: Count of Lipinski Rule-of-Five violations (0-2 typical for approved drugs)
- `alogp`: Calculated lipophilicity (optimal for oral drugs: 1-3)

## Integration with ODIN v9

### Recommended New Features

```python
# 1. Target Class Encoding (categorical → onehot)
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
    'other': 0
}

# 2. Mechanism Type Encoding
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
    'other': 0
}

# 3. Binary Features
chembl_is_biologic = drug_data['is_biologic']
chembl_first_in_class = drug_data['first_in_class']
chembl_has_competitor = drug_data['has_approved_competitor']

# 4. Multi-target Detection
chembl_num_targets = len(drug_data['mechanisms'])
chembl_is_multi_target = 1 if chembl_num_targets > 1 else 0

# 5. Small Molecule Properties
chembl_ro5_violations = drug_data.get('ro5_violations', None)
chembl_alogp = drug_data.get('alogp', None)
```

### Expected AUC Impact
- **Baseline ODIN v9 (current)**: WF AUC 0.9083, HO AUC 0.8961
- **Projected with target_class + mechanism_type**: +0.005-0.010 on holdout
- **Rationale**: Target class and mechanism type capture intrinsic biology (risk/approval correlation)
  - First-in-class kinase inhibitors differ from first-in-class antibodies
  - Multi-target drugs have different risk profiles than single-target
  - Enzymatic vs receptor mechanisms show different PK/safety patterns

## Integration with GUNGNIR v38.0.0

### Recommended New Features for Phase Readout Prediction

```python
# 1. Biologic Type Expansion
gungnir_is_antibody = 1 if drug_data['molecule_type'] == 'antibody' else 0
gungnir_is_car_t = 1 if drug_data['molecule_type'] == 'cell_therapy' else 0
gungnir_is_bispecific = 1 if 'bispecific' in drug_data['mechanism_type'] else 0
gungnir_is_adc = 1 if 'drug_conjugate' in drug_data['mechanism_type'] else 0

# 2. Target Class for Efficacy Prediction
gungnir_target_class_kinase = 1 if drug_data['target_class'] == 'kinase' else 0
gungnir_target_class_immune = 1 if 'immune' in drug_data['target_class'] else 0

# 3. Competitive Landscape
gungnir_crowded_target = drug_data['has_approved_competitor']
gungnir_first_in_class = drug_data['first_in_class']

# 4. Mechanism Characteristics
gungnir_is_cytotoxic = 1 if 'topoisomerase' in str(drug_data['mechanisms']) else 0
gungnir_immune_activation = 1 if 'agonist' in drug_data['mechanism_type'] else 0
```

### Expected AUC Impact
- **Baseline GUNGNIR v38.0.0 (current)**: WF AUC 0.7568, HO AUC not reported separately
- **Projected with biologic expansion + target_class**: +0.003-0.008 on holdout
- **Rationale**: Phase readout success rates vary dramatically by mechanism
  - Antibodies in immuno-oncology have different endpoints (DCR, ORR) than small molecule kinase inhibitors (RECIST)
  - CAR-T cell therapies have unique safety profiles (CRS) affecting readout interpretation
  - Bispecific antibodies show different dosing/scheduling patterns

## Data Quality Notes

### Coverage
- **16 drugs**: Represents ~1% of ODIN training set (1,479 unique drugs)
- **2023-2026 focus**: Emphasis on recent catalysts in test/holdout sets
- **All approved**: 15/16 at max_phase 4 (only Troriluzole is Phase 3)

### Limitations
1. Small sample size (16 drugs) → generalization risk
2. Recency bias toward 2014+ approvals (older drugs underrepresented)
3. Success bias (only approved/advancing drugs in cache; failed programs excluded)
4. Limited to ChEMBL-indexed molecules (~85% of biotech drugs)

### Expansion Strategy
To improve coverage and reduce bias:
1. **Batch 2**: Add 20-30 drugs from 2015-2020 events (historical validation)
2. **Batch 3**: Add failed Phase 3/CRL programs (negative examples for calibration)
3. **Batch 4**: Add rare mechanism types (gene therapy, oligonucleotides, etc.)

## Implementation Checklist

### For ODIN v10 Kaizen
- [ ] Merge cache into training pipeline
- [ ] Create target_class, mechanism_type features (one-hot or ordinal)
- [ ] Test on WF (1,845 events)
- [ ] Measure impact on holdout AUC (366 events)
- [ ] Run stability across 10 random seeds
- [ ] If AUC gain > 0.003, include in v10

### For GUNGNIR v39 Kaizen
- [ ] Expand cache with biologic classifications
- [ ] Test bispecific_antibody, car_t, adc features separately
- [ ] Measure impact on phase readout prediction
- [ ] Check interaction with indication_density, ta_recent_rate
- [ ] Compare against CT.gov features (may be redundant)

## References

### ChEMBL API Used
- `drug_search(drug_name, max_phase=4)`: Find approved drugs
- `compound_search(name)`: Fallback for non-standard names
- `get_mechanism(molecule_chembl_id)`: Extract mechanism details

### External Data
- **Source dates**: March 2026 ChEMBL v34
- **ODIN dataset**: 2,203 events (2015-2026), 1,479 unique drugs
- **GUNGNIR dataset**: 2,022 phase readout events (2022-2026)

## Contact & Updates
Cache last updated: 2026-03-29
Next sync recommended: Q3 2026 (post-June FDA PDUFA cycle)
Maintainer: 9 Realms Data Team
