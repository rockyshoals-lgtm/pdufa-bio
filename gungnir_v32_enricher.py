#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v32 DATA ENRICHER — Pull ChEMBL + PubMed + CT.gov signals
================================================================================
Enriches 1,752 training events + 848 catalysts with:
  1. ChEMBL: drug mechanism, target class, molecule type, max_phase, first_in_class
  2. PubMed: publication count (proxy for scientific confidence/evidence base)
  3. CT.gov MCP: richer trial metadata (complements existing cache)

Output: gungnir_v32_enrichment.json — per-drug enrichment data for v32 training
"""

import csv, json, math, os, re, sys, time, hashlib
from collections import defaultdict, Counter
import urllib.request, urllib.parse

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
CATALYST_SCORES = os.path.join(DATA_DIR, "catalyst_scores_v31.json")
ENRICHMENT_CACHE = os.path.join(DATA_DIR, "gungnir_v32_enrichment.json")

CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# =============================================================================
# DRUG NAME NORMALIZATION
# =============================================================================

def normalize_drug(name):
    """Normalize drug name for lookup — strip trial names, formulations, etc."""
    if not name:
        return ""
    # Take first part before " - " or " (" which is usually the drug name
    name = name.split(" - ")[0].split(" (")[0].strip()
    # Remove common suffixes
    name = re.sub(r"\s+(injection|tablets?|capsules?|oral|iv|sc|im|topical|cream|gel|solution|suspension|ophthalmic|nasal|inhaler|patch)\b", "", name, flags=re.I)
    # Remove brand name markers
    name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    # Take the INN/generic name (usually the first word if compound)
    # But keep multi-word names like "dupilumab" or "pembrolizumab"
    return name.strip()


# =============================================================================
# CHEMBL ENRICHMENT
# =============================================================================

def search_chembl(drug_name):
    """Search ChEMBL for a drug and return key properties."""
    if not drug_name or len(drug_name) < 3:
        return None

    # Clean the name
    clean = normalize_drug(drug_name)
    if not clean or len(clean) < 3:
        return None

    try:
        # Search by molecule synonym
        params = urllib.parse.urlencode({
            "molecule_synonyms__molecule_synonym__icontains": clean,
            "format": "json",
            "limit": 3,
        })
        url = f"{CHEMBL_API}/molecule.json?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Gungnir-v32-Enricher/1.0",
            "Accept": "application/json"
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        molecules = data.get("molecules", [])
        if not molecules:
            # Try direct name search
            params2 = urllib.parse.urlencode({
                "pref_name__icontains": clean,
                "format": "json",
                "limit": 3,
            })
            url2 = f"{CHEMBL_API}/molecule.json?{params2}"
            req2 = urllib.request.Request(url2, headers={
                "User-Agent": "Gungnir-v32-Enricher/1.0",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                data2 = json.loads(resp2.read().decode("utf-8"))
            molecules = data2.get("molecules", [])

        if not molecules:
            return None

        mol = molecules[0]
        props = mol.get("molecule_properties") or {}

        result = {
            "chembl_id": mol.get("molecule_chembl_id"),
            "pref_name": mol.get("pref_name"),
            "molecule_type": mol.get("molecule_type"),  # Small molecule, Antibody, Protein, etc.
            "max_phase": mol.get("max_phase"),           # 0-4 (4=approved)
            "first_approval": mol.get("first_approval"),
            "first_in_class": mol.get("first_in_class", 0),
            "oral": 1 if mol.get("oral") else 0,
            "parenteral": 1 if mol.get("parenteral") else 0,
            "black_box_warning": 1 if mol.get("black_box_warning") else 0,
            "natural_product": mol.get("natural_product", 0),
            "withdrawn": 1 if mol.get("withdrawn_flag") else 0,
            "orphan": mol.get("orphan", 0),
            "prodrug": mol.get("prodrug", 0),
            # Molecular properties (small molecules only)
            "mw": props.get("full_mwt"),
            "alogp": props.get("alogp"),
            "psa": props.get("psa"),
            "hba": props.get("hba"),
            "hbd": props.get("hbd"),
            "ro5_violations": props.get("num_ro5_violations"),
            "qed": props.get("qed_weighted"),
            "aromatic_rings": props.get("aromatic_rings"),
        }
        return result

    except Exception as e:
        return {"error": str(e)[:100]}


def get_mechanism(chembl_id):
    """Get mechanism of action for a ChEMBL molecule."""
    if not chembl_id:
        return []
    try:
        url = f"{CHEMBL_API}/mechanism.json?molecule_chembl_id={chembl_id}&format=json&limit=10"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Gungnir-v32-Enricher/1.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        mechanisms = []
        for mech in data.get("mechanisms", []):
            mechanisms.append({
                "action_type": mech.get("action_type"),
                "mechanism_of_action": mech.get("mechanism_of_action"),
                "target_chembl_id": mech.get("target_chembl_id"),
                "direct_interaction": mech.get("direct_interaction"),
                "disease_efficacy": mech.get("disease_efficacy"),
            })
        return mechanisms
    except:
        return []


# =============================================================================
# PUBMED PUBLICATION COUNT
# =============================================================================

def get_pubmed_count(drug_name, indication=""):
    """Get PubMed publication count for a drug (proxy for evidence base)."""
    if not drug_name or len(drug_name) < 3:
        return 0

    clean = normalize_drug(drug_name)
    if not clean:
        return 0

    try:
        # Search for drug name in clinical context
        query = f'"{clean}"[Title/Abstract] AND (clinical trial OR phase OR efficacy OR safety)'
        if indication and len(indication) > 3:
            # Also try with indication for specificity
            ind_clean = indication.split(",")[0].strip()[:50]
            query = f'"{clean}"[Title/Abstract] AND "{ind_clean}"[Title/Abstract]'

        params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "rettype": "count",
            "retmode": "json",
        })
        url = f"{PUBMED_API}/esearch.fcgi?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Gungnir-v32/1.0"})

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        count = int(data.get("esearchresult", {}).get("count", 0))
        return count

    except:
        return -1  # Error indicator


# =============================================================================
# MAIN ENRICHMENT PIPELINE
# =============================================================================

def main():
    print("=" * 80)
    print("GUNGNIR v32 DATA ENRICHER")
    print("=" * 80)

    # Load existing cache
    cache = {}
    if os.path.exists(ENRICHMENT_CACHE):
        with open(ENRICHMENT_CACHE) as f:
            cache = json.load(f)
        print(f"[CACHE] Loaded {len(cache)} existing entries")

    # Collect all unique drugs from training data + catalysts
    drugs = {}  # drug_key -> {drug_name, indication, ticker}

    # From training data
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            drug = r.get("drug", "").strip()
            if drug:
                key = normalize_drug(drug).lower()[:40]
                if key and len(key) >= 3:
                    drugs[key] = {
                        "drug": drug,
                        "indication": r.get("indication", ""),
                        "ticker": r.get("ticker", ""),
                    }

    # From catalyst scores
    if os.path.exists(CATALYST_SCORES):
        with open(CATALYST_SCORES) as f:
            catalysts = json.load(f)
        for c in catalysts:
            drug = c.get("drug", "").strip()
            if drug:
                key = normalize_drug(drug).lower()[:40]
                if key and len(key) >= 3:
                    drugs[key] = {
                        "drug": drug,
                        "indication": c.get("indication", ""),
                        "ticker": c.get("ticker", ""),
                    }

    print(f"[DRUGS] {len(drugs)} unique drugs to enrich")

    # Filter out already cached
    to_enrich = {k: v for k, v in drugs.items() if k not in cache}
    print(f"[TODO] {len(to_enrich)} drugs need enrichment ({len(cache)} cached)")

    if not to_enrich:
        print("[DONE] All drugs already enriched!")
        return 0

    # Enrich in batches
    total = len(to_enrich)
    done = 0
    errors = 0

    for drug_key, drug_info in to_enrich.items():
        drug_name = drug_info["drug"]
        indication = drug_info["indication"]

        # ChEMBL lookup
        chembl = search_chembl(drug_name)
        time.sleep(0.3)  # Rate limit

        # Get mechanism if we found a ChEMBL ID
        mechanisms = []
        if chembl and chembl.get("chembl_id") and "error" not in chembl:
            mechanisms = get_mechanism(chembl["chembl_id"])
            time.sleep(0.2)

        # PubMed publication count
        pub_count = get_pubmed_count(drug_name, indication)
        time.sleep(0.35)  # NCBI rate limit (3/sec without API key)

        # Also get drug-only count (broader)
        pub_count_broad = get_pubmed_count(drug_name)
        time.sleep(0.35)

        # Store enrichment
        cache[drug_key] = {
            "drug_name": drug_name,
            "indication": indication,
            "ticker": drug_info["ticker"],
            "chembl": chembl or {},
            "mechanisms": mechanisms,
            "n_mechanisms": len(mechanisms),
            "mechanism_types": list(set(m.get("action_type", "") for m in mechanisms if m.get("action_type"))),
            "pubmed_count_specific": pub_count,        # drug + indication
            "pubmed_count_broad": pub_count_broad,      # drug only
        }

        done += 1
        if chembl and "error" in chembl:
            errors += 1

        if done % 25 == 0 or done == total:
            # Save checkpoint
            with open(ENRICHMENT_CACHE, "w") as f:
                json.dump(cache, f, indent=1)
            pct = done / total * 100
            print(f"  [{done}/{total}] ({pct:.0f}%) enriched, {errors} errors — last: {drug_name[:30]}")

    # Final save
    with open(ENRICHMENT_CACHE, "w") as f:
        json.dump(cache, f, indent=1)

    # Summary
    has_chembl = sum(1 for v in cache.values() if v.get("chembl") and v["chembl"].get("chembl_id"))
    has_mech = sum(1 for v in cache.values() if v.get("n_mechanisms", 0) > 0)
    has_pubmed = sum(1 for v in cache.values() if v.get("pubmed_count_broad", 0) > 0)

    print(f"\n{'='*80}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'='*80}")
    print(f"  Total drugs: {len(cache)}")
    print(f"  ChEMBL match: {has_chembl} ({has_chembl/len(cache)*100:.0f}%)")
    print(f"  Has mechanism: {has_mech} ({has_mech/len(cache)*100:.0f}%)")
    print(f"  Has PubMed pubs: {has_pubmed} ({has_pubmed/len(cache)*100:.0f}%)")

    # Show molecule type distribution
    mol_types = Counter(v.get("chembl", {}).get("molecule_type") for v in cache.values() if v.get("chembl", {}).get("molecule_type"))
    print(f"\n  Molecule types: {dict(mol_types)}")

    # Show mechanism types
    all_mechs = Counter()
    for v in cache.values():
        for mt in v.get("mechanism_types", []):
            all_mechs[mt] += 1
    print(f"  Top mechanism types: {dict(all_mechs.most_common(10))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
