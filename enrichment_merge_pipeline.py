#!/usr/bin/env python3
"""
9 Realms Enrichment Merge Pipeline
===================================
Merges all enrichment data sources into training datasets:
  1. CT.gov v2 lookup → GUNGNIR (1,624 matched events → 14 trial design features)
  2. CT.gov ODIN lookup → ODIN (50 matched 2023-2026 events → trial design features)
  3. ChEMBL drug cache → GUNGNIR + ODIN (57 drugs → mechanism/target features)
  4. FinBrain sentiment → BIFROST tickers (50 tickers → sentiment/analyst/PCR)

Output: Enriched CSVs ready for kaizen feature testing.
"""

import json, csv, os, re
from collections import Counter, defaultdict
from datetime import datetime

BASE = "/sessions/loving-nifty-dirac/mnt/Python/9realms"

def load_json(path):
    with open(os.path.join(BASE, path)) as f:
        return json.load(f)

def load_csv(path):
    with open(os.path.join(BASE, path), 'r') as f:
        return list(csv.DictReader(f))

def save_csv(rows, path, fieldnames=None):
    if not rows:
        print(f"  WARNING: No rows to save for {path}")
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    full = os.path.join(BASE, path)
    with open(full, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved {len(rows)} rows × {len(fieldnames)} cols → {path}")

# ─────────────────────────────────────────────
# 1. GUNGNIR + CT.gov v2 merge
# ─────────────────────────────────────────────
def merge_gungnir_ctgov():
    print("\n" + "="*60)
    print("1. GUNGNIR + CT.gov v2 Merge")
    print("="*60)

    gungnir = load_csv("enriched_gungnir_dataset.csv")
    ctgov = load_json("ctgov_training_lookup_v2.json")
    matched = ctgov["matched"]

    # CT.gov features to merge
    ctgov_features = [
        'nct_id', 'enrollment', 'n_arms', 'is_randomized', 'is_double_blind',
        'is_placebo', 'masking_rigor', 'has_dmc', 'ep_hard', 'ep_surrogate',
        'n_sites', 'n_countries', 'is_global', 'has_withdrawals', 'phase'
    ]
    # Derived features
    derived = [
        'ct_log_enrollment', 'ct_n_per_arm', 'ct_log_n_per_arm',
        'ct_is_rigorous', 'ct_is_global_large', 'ct_log_n_sites',
        'ct_has_ctgov_match'
    ]

    import math

    merged_count = 0
    imputed_count = 0

    # Compute phase-average imputation values
    phase_stats = defaultdict(lambda: defaultdict(list))
    for idx_str, ct in matched.items():
        idx = int(idx_str)
        if idx < len(gungnir):
            row = gungnir[idx]
            stage = row.get('Stage', '')
            for feat in ['enrollment', 'n_arms', 'n_sites', 'n_countries', 'masking_rigor']:
                val = ct.get(feat)
                if val is not None:
                    phase_stats[stage][feat].append(float(val))

    phase_avg = {}
    for stage in phase_stats:
        phase_avg[stage] = {}
        for feat in phase_stats[stage]:
            vals = phase_stats[stage][feat]
            phase_avg[stage][feat] = sum(vals) / len(vals) if vals else 0

    # Global averages as fallback
    global_avg = {}
    for feat in ['enrollment', 'n_arms', 'n_sites', 'n_countries', 'masking_rigor']:
        all_vals = []
        for stage in phase_stats:
            all_vals.extend(phase_stats[stage][feat])
        global_avg[feat] = sum(all_vals) / len(all_vals) if all_vals else 0

    for i, row in enumerate(gungnir):
        idx_str = str(i)
        if idx_str in matched:
            ct = matched[idx_str]
            merged_count += 1

            # Raw features
            for feat in ctgov_features:
                row[f'ct_{feat}'] = ct.get(feat, '')

            # Derived features
            enroll = float(ct.get('enrollment', 0) or 0)
            n_arms = float(ct.get('n_arms', 1) or 1)
            n_sites = float(ct.get('n_sites', 0) or 0)

            row['ct_log_enrollment'] = round(math.log1p(enroll), 4)
            row['ct_n_per_arm'] = round(enroll / max(n_arms, 1), 1)
            row['ct_log_n_per_arm'] = round(math.log1p(enroll / max(n_arms, 1)), 4)
            row['ct_is_rigorous'] = 1 if (ct.get('is_randomized') and ct.get('is_double_blind') and ct.get('is_placebo')) else 0
            row['ct_is_global_large'] = 1 if (ct.get('is_global') and n_sites >= 20) else 0
            row['ct_log_n_sites'] = round(math.log1p(n_sites), 4)
            row['ct_has_ctgov_match'] = 1
        else:
            imputed_count += 1
            # Phase-average imputation
            stage = row.get('Stage', '')
            avg = phase_avg.get(stage, global_avg)

            for feat in ctgov_features:
                if feat in ['enrollment', 'n_arms', 'n_sites', 'n_countries', 'masking_rigor']:
                    row[f'ct_{feat}'] = round(avg.get(feat, global_avg.get(feat, 0)), 1)
                elif feat in ['is_randomized', 'is_double_blind', 'is_placebo', 'has_dmc', 'ep_hard', 'ep_surrogate', 'is_global', 'has_withdrawals']:
                    row[f'ct_{feat}'] = ''  # Missing binary features left empty
                else:
                    row[f'ct_{feat}'] = ''

            enroll = avg.get('enrollment', global_avg.get('enrollment', 100))
            n_arms = avg.get('n_arms', global_avg.get('n_arms', 2))
            n_sites = avg.get('n_sites', global_avg.get('n_sites', 10))

            row['ct_log_enrollment'] = round(math.log1p(enroll), 4)
            row['ct_n_per_arm'] = round(enroll / max(n_arms, 1), 1)
            row['ct_log_n_per_arm'] = round(math.log1p(enroll / max(n_arms, 1)), 4)
            row['ct_is_rigorous'] = ''
            row['ct_is_global_large'] = ''
            row['ct_log_n_sites'] = round(math.log1p(n_sites), 4)
            row['ct_has_ctgov_match'] = 0

    print(f"  CT.gov matched: {merged_count}/{len(gungnir)} ({100*merged_count/len(gungnir):.1f}%)")
    print(f"  Phase-avg imputed: {imputed_count}")

    # Get all fieldnames
    fieldnames = list(gungnir[0].keys())
    save_csv(gungnir, "enriched_gungnir_dataset_v2.csv", fieldnames)
    return gungnir

# ─────────────────────────────────────────────
# 2. GUNGNIR + ChEMBL merge
# ─────────────────────────────────────────────
def clean_drug_name(raw):
    """Extract core drug name from GUNGNIR drug strings like
    'ABECMA (IDECABTAGENE VICLEUCEL) - (KARMMA-9)'"""
    # Take first token before " - (" or " ("
    name = raw.strip()
    # Remove trial name (parenthetical at end with dash prefix)
    name = re.sub(r'\s*-\s*\(.*?\)\s*$', '', name)
    # If there's still a parenthetical with the generic name, try both
    paren_match = re.search(r'\(([^)]+)\)', name)
    generic = paren_match.group(1).strip() if paren_match else None
    brand = re.sub(r'\s*\(.*?\)\s*', '', name).strip()
    return brand.upper(), (generic.upper() if generic else None)

def merge_gungnir_chembl(gungnir_rows):
    print("\n" + "="*60)
    print("2. GUNGNIR + ChEMBL Merge")
    print("="*60)

    chembl = load_json("chembl_enrichment_cache.json")

    # Build lookup by uppercase drug name
    drug_lookup = {}
    for drug_name, data in chembl.items():
        drug_lookup[drug_name.upper()] = data

    chembl_features = [
        'chembl_molecule_type', 'chembl_max_phase', 'chembl_first_in_class',
        'chembl_is_biologic', 'chembl_target_class', 'chembl_mechanism_type',
        'chembl_has_approved_competitor', 'chembl_has_match'
    ]

    matched = 0
    for row in gungnir_rows:
        brand, generic = clean_drug_name(row.get('Drug', ''))

        # Try brand name, then generic, then partial match
        cdata = drug_lookup.get(brand)
        if not cdata and generic:
            cdata = drug_lookup.get(generic)
        if not cdata:
            # Try partial match — check if any chembl key is IN the brand name
            for cname, cval in drug_lookup.items():
                if cname in brand or brand in cname:
                    cdata = cval
                    break

        if cdata:
            matched += 1
            row['chembl_molecule_type'] = cdata.get('molecule_type', '')
            row['chembl_max_phase'] = cdata.get('max_phase', '')
            row['chembl_first_in_class'] = cdata.get('first_in_class', 0)
            row['chembl_is_biologic'] = cdata.get('is_biologic', 0)
            row['chembl_target_class'] = cdata.get('target_class', '')
            row['chembl_mechanism_type'] = cdata.get('mechanism_type', '')
            row['chembl_has_approved_competitor'] = cdata.get('has_approved_competitor', 0)
            row['chembl_has_match'] = 1
        else:
            for feat in chembl_features:
                row[feat] = '' if feat != 'chembl_has_match' else 0

    print(f"  ChEMBL matched: {matched}/{len(gungnir_rows)} ({100*matched/len(gungnir_rows):.1f}%)")

    fieldnames = list(gungnir_rows[0].keys())
    save_csv(gungnir_rows, "enriched_gungnir_dataset_v2.csv", fieldnames)
    return gungnir_rows

# ─────────────────────────────────────────────
# 3. ODIN + CT.gov merge
# ─────────────────────────────────────────────
def merge_odin_ctgov():
    print("\n" + "="*60)
    print("3. ODIN + CT.gov Merge")
    print("="*60)

    odin = load_csv("ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
    odin_ctgov = load_json("odin_ctgov_lookup.json")
    matches = odin_ctgov.get("matches", [])

    # Build lookup by ticker+asset combo
    ct_lookup = {}
    for m in matches:
        key = f"{m.get('odin_ticker', '')}|{m.get('odin_drug', '')}"
        ct_lookup[key] = m
        # Also index by ticker alone (for partial matching)
        ct_lookup[m.get('odin_ticker', '')] = m

    import math

    odin_ct_features = [
        'ct_nct_id', 'ct_enrollment', 'ct_num_arms', 'ct_is_randomized',
        'ct_is_double_blind', 'ct_has_placebo', 'ct_has_dmc', 'ct_num_sites',
        'ct_log_enrollment', 'ct_log_num_sites', 'ct_has_ctgov_match'
    ]

    matched = 0
    for row in odin:
        ticker = row.get('ticker', '')
        asset = row.get('asset', '')
        key = f"{ticker}|{asset}"

        m = ct_lookup.get(key) or ct_lookup.get(ticker)

        if m:
            matched += 1
            enrollment = m.get('enrollment', 0) or 0
            num_arms = m.get('num_arms', 2) or 2
            num_sites = m.get('num_sites', 0) or 0

            row['ct_nct_id'] = m.get('nct_id', '')
            row['ct_enrollment'] = enrollment
            row['ct_num_arms'] = num_arms
            row['ct_is_randomized'] = 1 if m.get('allocation', '') == 'RANDOMIZED' else 0
            row['ct_is_double_blind'] = 1 if 'DOUBLE' in str(m.get('blinding', '')).upper() else 0
            row['ct_has_placebo'] = 1 if m.get('placebo_control') else 0
            row['ct_has_dmc'] = 1 if m.get('has_dmc') else 0
            row['ct_num_sites'] = num_sites
            row['ct_log_enrollment'] = round(math.log1p(float(enrollment)), 4)
            row['ct_log_num_sites'] = round(math.log1p(float(num_sites)), 4)
            row['ct_has_ctgov_match'] = 1
        else:
            for feat in odin_ct_features:
                row[feat] = '' if feat != 'ct_has_ctgov_match' else 0

    print(f"  CT.gov matched: {matched}/{len(odin)} ({100*matched/len(odin):.1f}%)")
    print(f"  (2023+ events: {sum(1 for r in odin if r.get('catalyst_date','') >= '2023')})")

    fieldnames = list(odin[0].keys())
    save_csv(odin, "ODIN_MODEL_READY_v1071_ENRICHED_v2.csv", fieldnames)
    return odin

# ─────────────────────────────────────────────
# 4. ODIN + ChEMBL merge
# ─────────────────────────────────────────────
def merge_odin_chembl(odin_rows):
    print("\n" + "="*60)
    print("4. ODIN + ChEMBL Merge")
    print("="*60)

    chembl = load_json("chembl_enrichment_cache.json")
    drug_lookup = {k.upper(): v for k, v in chembl.items()}

    matched = 0
    for row in odin_rows:
        asset = row.get('asset', '').upper()
        # Try to match asset name to ChEMBL
        cdata = None
        for cname, cval in drug_lookup.items():
            if cname in asset or asset.startswith(cname):
                cdata = cval
                break

        if cdata:
            matched += 1
            row['chembl_molecule_type'] = cdata.get('molecule_type', '')
            row['chembl_is_biologic'] = cdata.get('is_biologic', 0)
            row['chembl_target_class'] = cdata.get('target_class', '')
            row['chembl_first_in_class'] = cdata.get('first_in_class', 0)
            row['chembl_has_match'] = 1
        else:
            row['chembl_molecule_type'] = ''
            row['chembl_is_biologic'] = ''
            row['chembl_target_class'] = ''
            row['chembl_first_in_class'] = ''
            row['chembl_has_match'] = 0

    print(f"  ChEMBL matched: {matched}/{len(odin_rows)} ({100*matched/len(odin_rows):.1f}%)")

    fieldnames = list(odin_rows[0].keys())
    save_csv(odin_rows, "ODIN_MODEL_READY_v1071_ENRICHED_v2.csv", fieldnames)
    return odin_rows

# ─────────────────────────────────────────────
# 5. Summary report
# ─────────────────────────────────────────────
def coverage_report(gungnir_rows, odin_rows):
    print("\n" + "="*60)
    print("ENRICHMENT COVERAGE REPORT")
    print("="*60)

    g_ctgov = sum(1 for r in gungnir_rows if r.get('ct_has_ctgov_match') == 1)
    g_chembl = sum(1 for r in gungnir_rows if r.get('chembl_has_match') == 1)
    o_ctgov = sum(1 for r in odin_rows if r.get('ct_has_ctgov_match') == 1)
    o_chembl = sum(1 for r in odin_rows if r.get('chembl_has_match') == 1)

    print(f"\n  GUNGNIR ({len(gungnir_rows)} events):")
    print(f"    CT.gov v2:  {g_ctgov}/{len(gungnir_rows)} ({100*g_ctgov/len(gungnir_rows):.1f}%)")
    print(f"    ChEMBL:     {g_chembl}/{len(gungnir_rows)} ({100*g_chembl/len(gungnir_rows):.1f}%)")
    print(f"    New CT.gov features: 15 raw + 7 derived = 22")
    print(f"    New ChEMBL features: 7")

    print(f"\n  ODIN ({len(odin_rows)} events):")
    print(f"    CT.gov:     {o_ctgov}/{len(odin_rows)} ({100*o_ctgov/len(odin_rows):.1f}%)")
    print(f"    ChEMBL:     {o_chembl}/{len(odin_rows)} ({100*o_chembl/len(odin_rows):.1f}%)")
    print(f"    New CT.gov features: 11")
    print(f"    New ChEMBL features: 5")

    g_cols = len(list(gungnir_rows[0].keys()))
    o_cols = len(list(odin_rows[0].keys()))
    print(f"\n  Output files:")
    print(f"    enriched_gungnir_dataset_v2.csv: {len(gungnir_rows)} × {g_cols}")
    print(f"    ODIN_MODEL_READY_v1071_ENRICHED_v2.csv: {len(odin_rows)} × {o_cols}")

    # ChEMBL target class distribution (GUNGNIR)
    tc_dist = Counter(r.get('chembl_target_class', '') for r in gungnir_rows if r.get('chembl_has_match') == 1)
    print(f"\n  ChEMBL target class distribution (GUNGNIR matched):")
    for tc, count in tc_dist.most_common(10):
        print(f"    {tc or 'unknown'}: {count}")

    return {
        'gungnir_ctgov': g_ctgov,
        'gungnir_chembl': g_chembl,
        'odin_ctgov': o_ctgov,
        'odin_chembl': o_chembl,
        'gungnir_total': len(gungnir_rows),
        'odin_total': len(odin_rows)
    }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("9 REALMS ENRICHMENT MERGE PIPELINE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Step 1: GUNGNIR + CT.gov
    gungnir_rows = merge_gungnir_ctgov()

    # Step 2: GUNGNIR + ChEMBL (on already CT.gov-enriched data)
    gungnir_rows = merge_gungnir_chembl(gungnir_rows)

    # Step 3: ODIN + CT.gov
    odin_rows = merge_odin_ctgov()

    # Step 4: ODIN + ChEMBL
    odin_rows = merge_odin_chembl(odin_rows)

    # Step 5: Coverage report
    report = coverage_report(gungnir_rows, odin_rows)

    # Save report
    report['timestamp'] = datetime.now().isoformat()
    with open(os.path.join(BASE, "enrichment_merge_report.json"), 'w') as f:
        json.dump(report, f, indent=2)

    print("\n✓ Pipeline complete.")
