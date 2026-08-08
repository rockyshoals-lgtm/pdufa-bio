# Gungnir v35 CT.gov Feature Engineering

## Overview

This document describes the **34 new CT.gov features** wired into Gungnir v35, expanding the model from v33's 14 CT.gov features to 48 total (plus 10 pre-built interactions = 58 features from CT.gov).

**Files:**
- `ctgov_v35_features.py` — Feature engineering module (standalone, T-1 compliant)
- `ctgov_v35_analysis.json` — Coverage stats, null rates, data quality report
- This document — Hypothesis and design rationale

**Key Stats:**
- **34 new features** from 37 unused CT.gov columns
- **100% coverage** for 30 features; 62.4% for primary_timeframe_days
- **10 interaction features** capturing phase × endpoint, sponsor × design synergies
- **45 total features** returned by `get_ctgov_v35_features()` function

---

## Feature Categories

### 1. ENDPOINT GRANULARITY (10 features)

**Binary Endpoint Indicators (7):**
- `ep_is_os` — Overall Survival endpoint
- `ep_is_pfs` — Progression-Free Survival endpoint
- `ep_is_orr` — Objective Response Rate endpoint
- `ep_is_safety` — Safety endpoint
- `ep_is_biomarker` — Biomarker endpoint
- `ep_is_pk_pd` — Pharmacokinetic/Pharmacodynamic endpoint
- `ep_is_qol` — Quality of Life endpoint

**Outcome Counts (3):**
- `num_primary_outcomes` — Number of primary endpoints
- `num_secondary_outcomes` — Number of secondary endpoints
- `num_total_outcomes` — Total outcome measures (sum)

**Rationale:**
- **OS (Gold Standard):** Overall survival is the most rigorous clinical endpoint, especially in oncology. Trials with OS endpoints have lower uncertainty about real clinical benefit. Signal: **positive correlation with approval**.
- **PFS (Intermediate):** Faster to read than OS, intermediate clinically. Good for solid tumors. Signal: **slightly positive, variable by TA**.
- **ORR (Binary):** Binary response (yes/no) is quick to measure but more variable than OS. Requires hard imaging criteria. Signal: **positive in early phase, risky in late phase**.
- **Safety Endpoint:** Often measured in unblinded fashion, lower scientific bar. Unusual as primary endpoint. Signal: **negative — suggests program maturity issue**.
- **Biomarker/PK-PD:** Mechanistic endpoints, not directly clinical. Good for early PoC but risky as pivotal. Signal: **negative in phase 3, positive in phase 1/2**.
- **QoL:** Subjective, highly placebo-sensitive. Hard to show superiority. Signal: **negative for efficacy trials, positive for supportive care**.
- **Endpoint Count:** More endpoints = more opportunities to "slice the data" and find significance. Signal: **slight negative (data dredging risk)** unless tightly focused (low count).

---

### 2. TRIAL TIMING (3 features)

- `primary_timeframe_days` — Days from baseline to primary endpoint measurement (62.4% coverage)
- `time_start_to_primary_completion` — Total planned trial duration for primary endpoint (100% coverage)
- `time_to_readout_days` — Calendar days from study start to actual readout event (100% coverage)

**Rationale:**
- **Long Timeframe (e.g., 2 years for OS):** Robust data, lower variance, but high calendar risk (delays hurt credibility). Signal: **neutral to positive** (rigorous but slow).
- **Short Timeframe (e.g., 12 weeks for ORR):** Quick signal, higher variance, may not capture durability. Signal: **depends on phase; positive for phase 2, risky for phase 3**.
- **Calendar Delay:** `time_to_readout_days` captures recruitment slowness, dropout issues, statistical delays. Delays often correlate with negative results or data quality issues. Signal: **negative correlation** (long delays = bad luck or unblinding).

**Imputation (when primary_timeframe_days is missing):**
- Phase 1: 30 days (safety escalation)
- Phase 2: 84 days (~3 months for PoC)
- Phase 3: 365 days (~1 year for OS/PFS)

---

### 3. TRIAL STRINGENCY (4 features)

- `inclusion_criteria_count` — Number of inclusion criteria
- `exclusion_criteria_count` — Number of exclusion criteria (mostly 0; artifact)
- `total_criteria_count` — Sum of inclusion + exclusion
- `log_elig_text_length` — Log-transformed character count of eligibility text

**Derived Feature:**
- `stringency_score` = `inclusion_criteria_count` + 2×`exclusion_criteria_count` + 0.001×`elig_text_length`

**Rationale:**
- **Restrictive Eligibility:** Complex inclusion/exclusion criteria limit enrollable population → smaller N, slower accrual, more homogeneous cohort. Signal: **slight negative** (smaller trials are riskier, but more focused).
- **Eligibility Text Length:** Longer text suggests detailed specifications (e.g., biomarker requirements, organ function thresholds), indicating a refined population. Signal: **neutral to positive** (better phenotyping).
- **Interaction with Trial Size:** Stringent criteria + small enrollment = high risk of recruitment failure or underpowered analysis. Signal: captured via interaction features.

---

### 4. INTERVENTION TYPES (5 features)

- `has_drug` — Intervention is a small-molecule drug or oral agent
- `has_biological` — Intervention includes biologic (antibody, protein, cytokine)
- `has_genetic` — Intervention has genetic component (gene therapy, ASO, siRNA)
- `has_combination` — Trial tests multi-agent combination therapy
- `has_active_comparator` — Has active drug control (vs placebo-only or no intervention)

**Rationale:**
- **Drug vs Biologic:** Different manufacturing complexity, immunogenicity risk, regulatory pathway. Signal: **neutral** (depends on TA).
- **Genetic:** High novelty, often single-arm designs, regulatory uncertainty. Signal: **mixed** (innovative but risky).
- **Combination Therapy:** Two or more mechanisms = higher toxicity/complexity risk, but potentially broader efficacy signal. Signal: **slight negative** (safety profile risk).
- **Active Comparator:** Harder to show superiority than placebo-controlled (smaller effect sizes needed). Signal: **slight negative** (higher bar to clear).

---

### 5. COMPARATOR DESIGN (2 features)

- `has_sham_comparator` — Has sham/device control (less common; surgical/device trials)
- `comparator_richness` = `has_active_comparator` + `has_sham_comparator` (0, 1, or 2)

**Rationale:**
- **Sham Control:** Mainly for surgical/device trials. Rare in pharma. Hard to blind. Signal: **neutral to negative** (more complex logistics).
- **Richness:** More comparison arms = more learning but higher complexity, potential for underpowering individual arms. Signal: **slight negative** (sample size dilution).

---

### 6. SPONSOR TYPE & COLLABORATION (6 features)

- `is_industry` — Sponsored by pharma/biotech company
- `is_nih` — Sponsored by NIH/government agency
- `is_academic` — Sponsored by academic institution
- `has_industry_collab` — Has industry collaboration (co-sponsor or collaborator)
- `is_fda_regulated_drug` — Drug is FDA-regulated (vs investigational)
- `num_collaborators` — Count of co-sponsors/collaborators

**Rationale:**
- **Industry Sponsor:** Higher regulatory scrutiny, greater resources, more rigorous statistical planning. Signal: **positive** (FDA-friendly designs).
- **NIH/Academic:** Variable quality; can be rigorous (NIH) or exploratory (academic). Signal: **neutral** (mixed outcomes).
- **Industry Collaboration:** Shared accountability, more resources, better CMC. Signal: **positive** (de-risks single-sponsor bias).
- **FDA-Regulated:** Drug is approved or has known safety profile. Signal: **positive** (lower regulatory risk).
- **Multiple Sponsors:** Risk-sharing, but also requires consensus (slower decision-making). Signal: **slight negative** (coordination complexity).

---

### 7. ENROLLMENT & RECRUITMENT (2 features)

- `is_actual_enrollment` — Trial reports actual enrollment (vs estimated/projected)
- `healthy_volunteers` — Trial includes healthy volunteers

**Rationale:**
- **Actual Enrollment:** Real > estimated; some trials miss enrollment targets. Actual reported = credible. Signal: **positive** (transparency).
- **Healthy Volunteers:** Unusual for phase 2/3 efficacy trials (more common in phase 1/PK studies). May signal safety study or special population. Signal: **mixed** (depends on context).

---

## Interaction Features (10 total)

**Phase × Endpoint Interactions (4):**
- `phase3_x_os` — Phase 3 + OS endpoint = pivotal trial with gold standard endpoint
  - Signal: **strong positive** (most rigorous design)
- `phase3_x_orr` — Phase 3 + ORR endpoint = pivotal with binary endpoint
  - Signal: **positive** (ORR is acceptable for fast-moving cancers like lymphoma)
- `phase3_x_biomarker` — Phase 3 + biomarker endpoint = risky
  - Signal: **negative** (mechanistic endpoint in pivotal setting = unusual, suggests unmet need)
- `phase2_x_biomarker` — Phase 2 + biomarker endpoint = expected
  - Signal: **positive** (appropriate for PoC in early phase)

**Oncology Signals (1):**
- `onc_x_pk_pd` — Oncology + PK/PD endpoint = mechanistic only
  - Signal: **negative** (no clinical endpoint in oncology = underdeveloped program)

**Sponsor × Design Interactions (3):**
- `industry_x_double_blind` — Industry + double-blind = gold standard
  - Signal: **positive** (FDA-preferred design)
- `industry_x_randomized` — Industry + randomized = rigorous
  - Signal: **positive** (reduces bias)
- `academic_x_single_arm` — Academic + single-arm = common exploratory design
  - Signal: **neutral to positive** (appropriate for early PoC, but higher risk)

**Design × Complexity Interactions (2):**
- `stringency_x_large_trial` — Restrictive eligibility + large N = gold standard
  - Signal: **positive** (refined population + statistical power)
- `biomarker_x_enrollment` — Biomarker endpoint × log(enrollment) = complexity signal
  - Signal: **slight negative** (biomarkers become harder to interpret in large, heterogeneous trials)

---

## Data Quality

**Coverage:**
- **100% for 30 features** — Fully populated, no missing values
- **62.4% for `primary_timeframe_days`** — Not always reported; imputed with phase-specific medians

**Data Types:**
- **Binary (0/1):** 17 features (endpoint types, sponsor class, intervention types, enrollment flags)
- **Counts (0-N):** 8 features (num_outcomes, num_collaborators, etc.)
- **Continuous:** 6 features (timeframe_days, elig_text_length, stringency_score)

**Assumptions:**
- `exclusion_criteria_count` = 0 for all trials (likely CT.gov data generation artifact; placeholder)
- Primary timeframe missing → phase-specific median imputation (conservative)
- All features are **T-1 compliant** (knowable at D-1, before readout event)

---

## Integration with v33 Pipeline

**Current v33 CT.gov Features (14):**
```
ctgov_is_double_blind, ctgov_is_placebo, ctgov_is_randomized, ctgov_masking_rigor,
ctgov_has_dmc, ctgov_has_withdrawals, ctgov_enrollment, ctgov_n_arms,
ctgov_n_sites, ctgov_n_countries, ctgov_is_global, ctgov_real,
ctgov_ep_hard, ctgov_ep_surrogate
```

**v35 New Features (34):**
All start with `ctgov_v35_*` prefix to avoid conflicts with v33 features.

**Usage in Training Pipeline:**

```python
from ctgov_v35_features import load_ctgov_data, get_ctgov_v35_features

# Load once
ctgov_data = load_ctgov_data()  # ~50MB in memory

# For each readout event
for row in readout_rows:
    v35_features = get_ctgov_v35_features(row, ctgov_data)
    # Merge with v33 features
    all_features = {**v33_features, **v35_features}
```

**Expected AUC Impact:**
- v33 baseline: AUC 0.7241 (103 features)
- v35 estimate: AUC 0.730–0.745 (134 features)
  - Conservative: +0.5pp (endpoint specificity signal)
  - Optimistic: +2pp (sponsor + timing + stringency interactions)

---

## Example Feature Vector

For NCT trial with:
- Phase 3, Oncology, Randomized, Double-blind, Placebo-controlled
- OS endpoint, 2 years timeframe
- 500 patient enrollment
- Industry sponsor
- 25 inclusion criteria

Expected feature values:
```
ctgov_v35_ep_is_os: 1
ctgov_v35_ep_is_pfs: 0
ctgov_v35_num_primary_outcomes: 1
ctgov_v35_num_secondary_outcomes: 5
ctgov_v35_primary_timeframe_days: 730
ctgov_v35_time_to_primary_completion: 730
ctgov_v35_inclusion_criteria_count: 25
ctgov_v35_stringency_score: 25.0
ctgov_v35_has_active_comparator: 0
ctgov_v35_is_industry: 1
ctgov_v35_is_fda_regulated_drug: 1
ctgov_v35_phase3_x_os: 1
ctgov_v35_industry_x_double_blind: 1
ctgov_v35_biomarker_x_enrollment: 0
```

---

## Files Reference

### `ctgov_v35_features.py`

**Functions:**
- `load_ctgov_data(csv_path)` → dict keyed by NCT ID
- `get_ctgov_v35_features(row, ctgov_data)` → dict of 45 features with `ctgov_v35_*` prefix
- `engineer_batch(readout_rows, ctgov_data)` → dict of feature dicts for batch processing
- `compute_coverage_stats(ctgov_data)` → dict with coverage % per column

**Self-test:**
```bash
python ctgov_v35_features.py  # Loads data, engineers first trial, prints stats
```

### `ctgov_v35_analysis.json`

Structure:
```json
{
  "metadata": {
    "version": "3.5",
    "module": "ctgov_v35_features.py",
    "purpose": "37 unused CT.gov columns → 34 new features",
    "generation_date": "2026-03-28"
  },
  "summary": {
    "total_ctgov_trials": 18524,
    "v35_new_features_total": 34,
    "features_with_100pct_coverage": 30,
    "features_by_category": {...}
  },
  "by_category": {
    "endpoint_granularity": {...},
    "trial_timing": {...},
    "trial_stringency": {...},
    "intervention_types": {...},
    "comparator_design": {...},
    "sponsor_collaboration": {...},
    "enrollment_recruitment": {...}
  },
  "all_features": {
    "ep_is_os": {
      "description": "Overall Survival endpoint — gold standard...",
      "coverage_pct": 100.0,
      "null_rate_pct": 0.0,
      "data_type": "numeric",
      "unique_count": 2,
      ...
    },
    ...
  }
}
```

---

## Next Steps for v35 Training

1. **Merge v35 features into training pipeline:**
   - Load `ctgov_v35_features.py` module
   - Call `get_ctgov_v35_features()` for each readout event
   - Combine with v33's 103 features → 143 feature total

2. **Feature selection / ablation:**
   - Test which v35 features actually improve AUC
   - Interactions (phase3_x_os, industry_x_double_blind) likely strongest
   - Timing features (primary_timeframe_days) may need log-transformation

3. **Validation:**
   - Walk-forward test on 1,752 events (same as v33)
   - Compare AUC: v33 (0.7241) vs v35 (expected 0.730+)
   - If < 0.72, likely overfitting; trim weakest features

4. **Deployment:**
   - Update `gungnir_v35_deploy.json` with new feature names
   - Update catalyst scorer to use 143 features
   - Score all 2026 catalysts with v35 model

---

## References

- CT.gov API: https://clinicaltrials.gov/api/v2/
- Trial design papers: NEJM reviews on trial methodology
- GUNGNIR v33 model card: `gungnir_v33_deploy.json`
- Previous ablations: `v32_ablation.py` (shows sponsor_sr + indication_density helped)

---

**Module Version:** 3.5
**Last Updated:** 2026-03-28
**Status:** Ready for integration into v35 training pipeline
