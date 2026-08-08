"""
HINT BACKTEST - ALL ODIN VERIFIED WINS (Complete Ledger)
=========================================================
ALL 28+ verified wins from ODIN COMPLETE VERIFIED WINS LEDGER (2026-01-19)

Includes:
- 8 UTC-Timestamped (10/5/25+)
- 9 Additional Verified Approvals
- 2 Pre-10/5/25 Timestamped  
- 10 CRL Predictions Correct
- 5 CEWS Signals Validated

Small molecules only (HINT training domain).
Excluded: Cell therapies, mAbs, siRNA, gene therapies, oncolytic viruses, peptides, biosimilars
"""

import sys
sys.path.insert(0, r"C:\Users\dcmoo\Documents\Python\hint_models")

import torch
from transformers import AutoTokenizer, AutoModel
import pubchempy as pcp
from datetime import datetime

print("="*100)
print("HINT COMPREHENSIVE BACKTEST - ALL ODIN VERIFIED WINS")
print("Source: ODIN_COMPLETE_VERIFIED_WINS_LEDGER_2026-01-19")
print("="*100)

# ============================================================================
# BioBERT Encoder
# ============================================================================
class BioBERTEncoder:
    def __init__(self):
        print("Loading BioBERT...", end=" ", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model.eval()
        print("OK")
    
    def encode(self, text):
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            return outputs.last_hidden_state[:, 0, :]

def protocol2feature_live(protocol, encoder):
    protocol = protocol.lower()
    lines = [l.strip() for l in protocol.split('\n') if l.strip()]
    inc_idx = next((i for i, l in enumerate(lines) if 'inclusion' in l), 0)
    exc_idx = next((i for i, l in enumerate(lines) if 'exclusion' in l), len(lines))
    inclusion = lines[inc_idx:exc_idx] if inc_idx < exc_idx else lines
    exclusion = lines[exc_idx:] if exc_idx < len(lines) else []
    
    if inclusion:
        inc_embeds = torch.cat([encoder.encode(s) for s in inclusion[:5]], 0)
    else:
        inc_embeds = torch.zeros(1, 768)
    if exclusion:
        exc_embeds = torch.cat([encoder.encode(s) for s in exclusion[:5]], 0)
    else:
        exc_embeds = torch.zeros(1, 768)
    return inc_embeds, exc_embeds

# ============================================================================
# SMILES Cache - ALL verified wins
# ============================================================================
SMILES_CACHE = {
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION A: UTC-TIMESTAMPED (10/5/25+)
    # ═══════════════════════════════════════════════════════════════════════
    
    # TS-001: MIST | Etripamil
    "etripamil": "CC(C)OC1=CC=C(C=C1)CCN2CCCC2C3=CC=C(C=C3)OC(C)(C)C(=O)N",
    
    # TS-002: SNDX | Revumenib
    "revumenib": "CC1=CC(=CC(=C1)C2=CC=C(C=C2)CN3C(=O)C(=NC3=O)C4=CC=CC=C4F)C5=CN=C(N=C5)N",
    
    # TS-003: CAPR | Deramiocel - SKIP (cell therapy)
    
    # TS-004: VNDA | Tradipitant
    "tradipitant": "CC1=CC(=NO1)C2=CC=C(C=C2)CN3C(=O)C(=CC4=CC=C(C=C4)C(F)(F)F)N=C(N)N3",
    
    # TS-005: OMER | Narsoplimab - SKIP (mAb)
    
    # TS-006: CORT | Relacorilant
    "relacorilant": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=CC=C3C(=O)O)C(C)(C)C4=CC=C(C=C4)F",
    
    # TS-007: FBIO | CUTX-101 - SKIP (copper histidinate)
    
    # TS-008: ATRA | Tabelecleucel - SKIP (cell therapy)
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION B: ADDITIONAL VERIFIED APPROVALS
    # ═══════════════════════════════════════════════════════════════════════
    
    # APP-001: KURA | Ziftomenib
    "ziftomenib": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CC6=C(C=C5)N=CN6",
    
    # APP-002: ARWR | Plozasiran - SKIP (siRNA)
    
    # APP-003: AGIO | Mitapivat
    "mitapivat": "CC1=C(C=CC(=C1)S(=O)(=O)NC2=CC=C(C=C2)F)C(=O)NC3=NC=C(S3)C4=CC=CC=N4",
    
    # APP-004: CYTK | Aficamten
    "aficamten": "CC1=C(C=C(C=C1)OCC2=CC=C(C=C2)F)NC(=O)N3CCC(CC3)C4=NN=C(O4)C",
    
    # APP-005: INVA | Zoliflodacin
    "zoliflodacin": "CC1=CC2=C(C=C1)N3C=C(C(=O)C4=C3C(=NC(=C4)F)N2)C(=O)NCC5=CC=CC=C5F",
    
    # APP-006: CSL | Garadacimab - SKIP (mAb)
    
    # APP-007: NVS | Remibrutinib
    "remibrutinib": "C#CC1=CC=C(C=C1)C2=NN3C(=N2)C=CC(=C3N)C(=O)NC4=CC=C(C=C4)C(C)(C)C#N",
    
    # APP-008: GILD | Lenacapavir
    "lenacapavir": "CC(C)(C)C1=NC(=C(C=C1)F)C2=CC(=C(C(=C2)F)NS(=O)(=O)C3CC3)N4CCC(CC4)(CO)NC(=O)C(F)(F)C5=CC(=C(C=C5)Cl)F",
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION C: PRE-10/5/25 TIMESTAMPED
    # ═══════════════════════════════════════════════════════════════════════
    
    # TS-PRE-001: TOVX | VCN-01 - SKIP (oncolytic virus)
    # TS-PRE-002: PGEN | Papzimeos - SKIP (gene-modified cell therapy)
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION D: CRL PREDICTIONS CORRECT
    # ═══════════════════════════════════════════════════════════════════════
    
    # CRL-002: PTCT | Vatiquinone
    "vatiquinone": "COC1=C(C=CC(=C1)CC(C)C(=O)O)OC",
    
    # CRL-003: OTLK | ONS-5010 - SKIP (biosimilar bevacizumab)
    # CRL-004: REPL | RP1 - SKIP (oncolytic virus)
    
    # CRL-005: ALDX | Reproxalap
    "reproxalap": "CC1=CC=C(C=C1)C(=O)NC2=CC(=C(C=C2)N3C=CN=C3)C(=O)NC4=CC=CC=C4C(=O)O",
    
    # CRL-006: TLX | TLX101 - SKIP (radiopharmaceutical)
    
    # CRL-007: MITO | Elamipretide (peptide - may work)
    "elamipretide": "CC(C)CC(NC(=O)C(CC1=CC=CC=C1)NC(=O)C(CC2=CN=CN2)N)C(=O)NC(CCCNC(=N)N)C(=O)N",
    
    # CRL-008: UNCY | Oxylanthanum - SKIP (inorganic)
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION E: CEWS SIGNALS VALIDATED
    # ═══════════════════════════════════════════════════════════════════════
    
    # CEWS-001: BHVN | Troriluzole
    "troriluzole": "FC1=CC=C(C=C1)C2=NC(=NO2)SCC(=O)NCC3=CC=CC=C3",
    
    # CEWS-002: RGNX | RGX-121 - SKIP (gene therapy)
    # CEWS-003: FBIO | CUTX-101 - SKIP (copper histidinate)
    
    # CEWS-004: AQST | Anaphylm (epinephrine)
    "epinephrine": "CNCC(C1=CC(=C(C=C1)O)O)O",
    
    # CEWS-005: TVTX | Sparsentan
    "sparsentan": "CCCC1=NC2=CC(=CC=C2N1CC3=CC=C(C=C3)C4=CC=CC=C4C5=NNN=N5)C(=O)O",
}

# ============================================================================
# ICD-10 Mapping - ALL indications
# ============================================================================
ICD10_MAP = {
    # Cardiovascular
    "psvt": "I47.1",
    "paroxysmal supraventricular tachycardia": "I47.1",
    "ohcm": "I42.1",
    "obstructive hcm": "I42.1",
    "hypertrophic cardiomyopathy": "I42.1",
    
    # Oncology/Hematology
    "aml": "C92.00",
    "acute myeloid leukemia": "C92.00",
    "r/r npm1-mutant aml": "C92.00",
    "r/r aml npm1": "C92.00",
    "r/r aml with npm1 mutation": "C92.00",
    
    # GI/Nausea
    "motion sickness": "T75.3",
    "motion sickness prevention": "T75.3",
    "nausea": "R11.0",
    
    # Metabolic/Endocrine
    "cushing": "E24.9",
    "cushing's syndrome": "E24.9",
    "hypercortisolism": "E24.9",
    
    # Hematology
    "thalassemia": "D56.9",
    "alpha/beta-thalassemia anemia": "D56.9",
    "alpha thalassemia": "D56.0",
    "beta thalassemia": "D56.1",
    
    # Neurological
    "friedreich ataxia": "G11.11",
    "friedreich's ataxia": "G11.11",
    "cerebellar ataxia": "G11.9",
    "spinocerebellar ataxia": "G11.1",
    
    # Ophthalmology
    "dry eye": "H04.121",
    "dry eye disease": "H04.121",
    
    # Infectious Disease
    "gonorrhea": "A54.9",
    "uncomplicated urogenital gonorrhea": "A54.00",
    "hiv prep": "Z20.6",
    "hiv": "B20",
    
    # Dermatology/Allergy
    "csu": "L50.1",
    "chronic spontaneous urticaria": "L50.1",
    "anaphylaxis": "T78.2",
    
    # Renal
    "fsgs": "N04.1",
    "focal segmental glomerulosclerosis": "N04.1",
    
    # Mitochondrial
    "barth syndrome": "E71.121",
    "primary mitochondrial myopathy": "G71.3",
}

def get_icd10(indication):
    ind_lower = indication.lower().strip()
    if ind_lower in ICD10_MAP:
        return ICD10_MAP[ind_lower]
    for key, code in ICD10_MAP.items():
        if key in ind_lower or ind_lower in key:
            return code
    return "R69"

def get_smiles(drug_name):
    drug_lower = drug_name.lower().strip()
    if drug_lower in SMILES_CACHE:
        return SMILES_CACHE[drug_lower]
    try:
        results = pcp.get_compounds(drug_name, 'name')
        if results:
            smiles = results[0].isomeric_smiles or results[0].canonical_smiles
            SMILES_CACHE[drug_lower] = smiles
            return smiles
    except:
        pass
    return None

# ============================================================================
# COMPLETE TEST CASES - ALL 28+ VERIFIED WINS
# ============================================================================
ALL_WINS = [
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION A: UTC-TIMESTAMPED (10/5/25+) - 8 total, 4 small molecules
    # ═══════════════════════════════════════════════════════════════════════
    
    {
        "id": "TS-001",
        "section": "A",
        "ticker": "MIST",
        "drug": "Etripamil",
        "indication": "PSVT",
        "timestamp": "2025-10-05T16:42:11Z",
        "odin_score": 0.82,
        "actual": "APPROVED",
        "outcome_date": "2025-12-12",
        "peak_gain": "+130%",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults >=18 with documented symptomatic PSVT episodes, at least 3 episodes in past year. Exclusion: Severe cardiovascular disease, bradycardia <50 bpm, hypotension"
    },
    {
        "id": "TS-002",
        "section": "A",
        "ticker": "SNDX",
        "drug": "Revumenib",
        "indication": "r/r NPM1-mutant AML",
        "timestamp": "2025-10-05T16:49:02Z",
        "odin_score": 0.87,
        "actual": "APPROVED",
        "outcome_date": "2025-10-24",
        "peak_gain": "+51%",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with relapsed/refractory AML with confirmed NPM1 mutation, failed at least 1 prior therapy. Exclusion: Prior menin inhibitor therapy, active CNS leukemia, severe hepatic impairment"
    },
    {
        "id": "TS-004",
        "section": "A",
        "ticker": "VNDA",
        "drug": "Tradipitant",
        "indication": "Motion sickness prevention",
        "timestamp": "2025-12-13T22:00:00Z",
        "odin_score": 0.55,
        "actual": "APPROVED",
        "outcome_date": "2025-12-30",
        "peak_gain": "N/A",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults prone to motion sickness with history of symptoms during travel. Exclusion: GI motility disorders, concurrent use of antiemetics, pregnancy"
    },
    {
        "id": "TS-006",
        "section": "A",
        "ticker": "CORT",
        "drug": "Relacorilant",
        "indication": "Cushing's syndrome",
        "timestamp": "2025-12-22T03:05:54Z",
        "odin_score": 0.58,
        "actual": "CRL",
        "outcome_date": "2025-12-31",
        "crl_reason": "Insufficient efficacy evidence",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with endogenous Cushing's syndrome with confirmed hypercortisolism. Exclusion: Adrenal insufficiency, pregnancy, severe renal impairment"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION B: ADDITIONAL VERIFIED APPROVALS - 9 total, 6 small molecules
    # ═══════════════════════════════════════════════════════════════════════
    
    {
        "id": "APP-001",
        "section": "B",
        "ticker": "KURA",
        "drug": "Ziftomenib",
        "indication": "r/r AML with NPM1 mutation",
        "odin_score": 0.75,
        "actual": "APPROVED",
        "outcome_date": "2025-11-13",
        "peak_gain": "+45%",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with relapsed/refractory AML with NPM1 mutation, at least 1 prior therapy. Exclusion: Active CNS disease, prior menin inhibitor, severe organ dysfunction"
    },
    {
        "id": "APP-003",
        "section": "B",
        "ticker": "AGIO",
        "drug": "Mitapivat",
        "indication": "Alpha/beta-thalassemia anemia",
        "odin_score": 0.89,
        "actual": "APPROVED",
        "outcome_date": "2025-12-23",
        "peak_gain": "+28%",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with alpha or beta thalassemia with hemolytic anemia requiring regular monitoring. Exclusion: Transfusion-dependent thalassemia, severe hepatic impairment, pregnancy"
    },
    {
        "id": "APP-004",
        "section": "B",
        "ticker": "CYTK",
        "drug": "Aficamten",
        "indication": "Obstructive HCM",
        "odin_score": 0.77,
        "actual": "APPROVED",
        "outcome_date": "2025-12-19",
        "peak_gain": "+17%",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with symptomatic obstructive HCM, LVOT gradient >=30mmHg at rest or provoked. Exclusion: Severe heart failure NYHA IV, LVEF <55%, prior septal reduction"
    },
    {
        "id": "APP-005",
        "section": "B",
        "ticker": "INVA",
        "drug": "Zoliflodacin",
        "indication": "Uncomplicated urogenital gonorrhea",
        "odin_score": 0.85,
        "actual": "APPROVED",
        "outcome_date": "2025-12-12",
        "peak_gain": "N/A",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with uncomplicated urogenital gonorrhea confirmed by laboratory testing. Exclusion: Complicated gonococcal infection, disseminated infection, pregnancy"
    },
    {
        "id": "APP-007",
        "section": "B",
        "ticker": "NVS",
        "drug": "Remibrutinib",
        "indication": "Chronic spontaneous urticaria",
        "odin_score": 0.95,
        "actual": "APPROVED",
        "outcome_date": "2025-09-30",
        "peak_gain": "N/A",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with chronic spontaneous urticaria refractory to H1 antihistamines at approved doses. Exclusion: Active infection, immunocompromised, severe hepatic impairment"
    },
    {
        "id": "APP-008",
        "section": "B",
        "ticker": "GILD",
        "drug": "Lenacapavir",
        "indication": "HIV PrEP",
        "odin_score": 0.95,
        "actual": "APPROVED",
        "outcome_date": "2025-06-18",
        "peak_gain": "N/A",
        "modality": "small_molecule",
        "criteria": "Inclusion: HIV-negative adults at risk of HIV acquisition, willing to adhere to injection schedule. Exclusion: Prior HIV infection, severe renal impairment, active hepatitis B"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION D: CRL PREDICTIONS CORRECT - 10 total, 4 small molecules
    # ═══════════════════════════════════════════════════════════════════════
    
    {
        "id": "CRL-002",
        "section": "D",
        "ticker": "PTCT",
        "drug": "Vatiquinone",
        "indication": "Friedreich ataxia",
        "odin_score": 0.31,
        "actual": "CRL",
        "outcome_date": "2025-08-19",
        "crl_reason": "MOVE-FA trial missed primary endpoint (p=0.14)",
        "modality": "small_molecule",
        "criteria": "Inclusion: Genetically confirmed Friedreich's ataxia, ambulatory with or without assistance. Exclusion: Severe cardiomyopathy, wheelchair-bound, unable to complete assessments"
    },
    {
        "id": "CRL-005",
        "section": "D",
        "ticker": "ALDX",
        "drug": "Reproxalap",
        "indication": "Dry eye disease",
        "odin_score": 0.10,
        "actual": "CRL",
        "outcome_date": "2025-04-03",
        "crl_reason": "Baseline differences in TRANQUILITY trials",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with dry eye disease and moderate to severe ocular discomfort, Schirmer score <=10mm. Exclusion: Active eye infection, recent eye surgery, contact lens use"
    },
    {
        "id": "CRL-007",
        "section": "D",
        "ticker": "MITO",
        "drug": "Elamipretide",
        "indication": "Primary mitochondrial myopathy",
        "odin_score": 0.20,
        "actual": "CRL",
        "outcome_date": "2025-05-29",
        "crl_reason": "Clinical data and cGMP deficiencies",
        "modality": "peptide",
        "criteria": "Inclusion: Adults with genetically confirmed primary mitochondrial myopathy, able to complete 6MWT. Exclusion: Other cause of myopathy, severe cardiac involvement"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION E: CEWS SIGNALS VALIDATED - 5 total, 3 small molecules
    # ═══════════════════════════════════════════════════════════════════════
    
    {
        "id": "CEWS-001",
        "section": "E",
        "ticker": "BHVN",
        "drug": "Troriluzole",
        "indication": "Spinocerebellar ataxia",
        "odin_score": 0.40,
        "actual": "CRL",
        "outcome_date": "2025-11-04",
        "crl_reason": "Clinical trial endpoints not met",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with spinocerebellar ataxia types 1, 2, or 3, ambulatory. Exclusion: Severe swallowing difficulty, respiratory compromise, other neurological conditions"
    },
    {
        "id": "CEWS-004",
        "section": "E",
        "ticker": "AQST",
        "drug": "Epinephrine",
        "indication": "Anaphylaxis",
        "odin_score": 0.65,
        "actual": "DEFICIENCY",
        "outcome_date": "2026-01-09",
        "crl_reason": "FDA deficiency letter (PDUFA Jan 31 pending)",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults and adolescents at risk of anaphylaxis, prescribed epinephrine auto-injector. Exclusion: Allergy to epinephrine components, severe cardiovascular disease"
    },
    {
        "id": "CEWS-005",
        "section": "E",
        "ticker": "TVTX",
        "drug": "Sparsentan",
        "indication": "FSGS",
        "odin_score": 0.88,
        "actual": "DELAYED",
        "outcome_date": "2026-01-13",
        "crl_reason": "FDA requested additional information, 3-month delay",
        "modality": "small_molecule",
        "criteria": "Inclusion: Adults with FSGS and proteinuria >1g/day despite maximized ACEi/ARB. Exclusion: eGFR <30, kidney transplant recipient, other primary glomerular disease"
    },
]

# ============================================================================
# Main Backtest Function
# ============================================================================
def run_backtest():
    print(f"\n[1] Loading models...")
    biobert = BioBERTEncoder()
    
    from HINT.model import HINTModel
    model = torch.load(
        r"C:\Users\dcmoo\Documents\Python\hint_models\save_model\phase_III.ckpt",
        map_location='cpu',
        weights_only=False
    )
    model.eval()
    print("    ✓ HINT Phase III loaded")
    
    # Filter to small molecules only
    small_mol_cases = [c for c in ALL_WINS if c.get('modality') in ['small_molecule', 'peptide']]
    
    print(f"\n[2] Running HINT backtest on {len(small_mol_cases)} small molecule cases...")
    print(f"    (Excluded: cell therapies, mAbs, siRNA, gene therapies, oncolytic viruses)")
    print("-" * 120)
    print(f"{'ID':<10} {'Sec':<3} {'Ticker':<6} {'Drug':<15} {'Indication':<20} {'HINT':>7} {'ODIN':>7} {'Actual':<10} {'HINT':>8} {'Ens':>5}")
    print("-" * 120)
    
    results = []
    skipped = []
    
    for case in small_mol_cases:
        # Get SMILES
        smiles = get_smiles(case['drug'])
        if not smiles:
            skipped.append(f"{case['ticker']}/{case['drug']}: No SMILES")
            continue
        
        # Get ICD-10
        icd_code = get_icd10(case['indication'])
        
        # Run HINT
        with torch.no_grad():
            smiles_input = [[smiles]]
            icd_input = [[[icd_code]]]
            criteria_feature = protocol2feature_live(case['criteria'], biobert)
            criteria_input = [criteria_feature]
            
            try:
                output = model.forward(
                    smiles_lst2=smiles_input,
                    icdcode_lst3=icd_input,
                    criteria_lst=criteria_input
                )
                raw_logit = output.item() if output.numel() == 1 else output[0].item()
                hint_prob = 1 / (1 + torch.exp(torch.tensor(-raw_logit))).item()
                hint_prob = max(0.01, min(0.99, hint_prob))
            except Exception as e:
                skipped.append(f"{case['ticker']}/{case['drug']}: HINT error - {str(e)[:30]}")
                continue
        
        # Ensemble (70% ODIN, 30% HINT)
        ensemble_prob = 0.70 * case['odin_score'] + 0.30 * hint_prob
        
        # Classify calls
        if hint_prob >= 0.60:
            hint_call = "BULL"
        elif hint_prob <= 0.45:
            hint_call = "BEAR"
        else:
            hint_call = "NEUT"
        
        # Check correctness
        actual_positive = case['actual'] == "APPROVED"
        hint_correct = (hint_call == "BULL" and actual_positive) or \
                       (hint_call in ["BEAR", "NEUT"] and not actual_positive)
        ensemble_call_correct = (ensemble_prob >= 0.65 and actual_positive) or \
                                (ensemble_prob < 0.65 and not actual_positive)
        
        h_sym = "✓" if hint_correct else "✗"
        e_sym = "✓" if ensemble_call_correct else "✗"
        
        ind_short = case['indication'][:18] + ".." if len(case['indication']) > 20 else case['indication']
        drug_short = case['drug'][:13] + ".." if len(case['drug']) > 15 else case['drug']
        
        print(f"{case['id']:<10} {case['section']:<3} {case['ticker']:<6} {drug_short:<15} {ind_short:<20} {hint_prob:>6.1%} {case['odin_score']:>6.0%} {case['actual']:<10} {hint_call:>5} {h_sym:<1}  {e_sym:<1}")
        
        results.append({
            'id': case['id'],
            'section': case['section'],
            'ticker': case['ticker'],
            'drug': case['drug'],
            'hint_prob': hint_prob,
            'odin_prob': case['odin_score'],
            'ensemble_prob': ensemble_prob,
            'actual': case['actual'],
            'hint_call': hint_call,
            'hint_correct': hint_correct,
            'ensemble_correct': ensemble_call_correct
        })
    
    print("-" * 120)
    
    # ========================================================================
    # Summary Statistics
    # ========================================================================
    total = len(results)
    hint_correct = sum(1 for r in results if r['hint_correct'])
    ensemble_correct = sum(1 for r in results if r['ensemble_correct'])
    
    approvals = [r for r in results if r['actual'] == 'APPROVED']
    negatives = [r for r in results if r['actual'] in ['CRL', 'DELAYED', 'DEFICIENCY']]
    
    print(f"\n{'='*70}")
    print("COMPREHENSIVE BACKTEST RESULTS - ALL ODIN VERIFIED WINS")
    print(f"{'='*70}")
    print(f"\nDataset Coverage:")
    print(f"  Total ODIN Verified Wins: 28+")
    print(f"  Small Molecules Tested:   {total}")
    print(f"  Skipped (non-SM/errors):  {len(skipped)}")
    
    print(f"\n{'─'*70}")
    print("HINT STANDALONE PERFORMANCE")
    print(f"{'─'*70}")
    print(f"  Overall Accuracy:    {hint_correct}/{total} ({100*hint_correct/total:.1f}%)")
    print(f"  Approvals Correct:   {sum(1 for r in approvals if r['hint_correct'])}/{len(approvals)} ({100*sum(1 for r in approvals if r['hint_correct'])/len(approvals):.1f}%)")
    print(f"  CRLs/Neg Correct:    {sum(1 for r in negatives if r['hint_correct'])}/{len(negatives)} ({100*sum(1 for r in negatives if r['hint_correct'])/len(negatives):.1f}%)")
    
    print(f"\n{'─'*70}")
    print("ODIN + HINT ENSEMBLE (70/30)")
    print(f"{'─'*70}")
    print(f"  Overall Accuracy:    {ensemble_correct}/{total} ({100*ensemble_correct/total:.1f}%)")
    print(f"  Approvals Correct:   {sum(1 for r in approvals if r['ensemble_correct'])}/{len(approvals)}")
    print(f"  CRLs/Neg Correct:    {sum(1 for r in negatives if r['ensemble_correct'])}/{len(negatives)}")
    
    # Calibration analysis
    avg_hint_approved = sum(r['hint_prob'] for r in approvals) / len(approvals) if approvals else 0
    avg_hint_negative = sum(r['hint_prob'] for r in negatives) / len(negatives) if negatives else 0
    avg_odin_approved = sum(r['odin_prob'] for r in approvals) / len(approvals) if approvals else 0
    avg_odin_negative = sum(r['odin_prob'] for r in negatives) / len(negatives) if negatives else 0
    
    print(f"\n{'─'*70}")
    print("CALIBRATION COMPARISON")
    print(f"{'─'*70}")
    print(f"                      HINT        ODIN        Separation")
    print(f"  Avg (Approved):     {avg_hint_approved:>5.1%}       {avg_odin_approved:>5.0%}")
    print(f"  Avg (CRL/Neg):      {avg_hint_negative:>5.1%}       {avg_odin_negative:>5.0%}")
    print(f"  Separation:         {avg_hint_approved - avg_hint_negative:>5.1%}       {avg_odin_approved - avg_odin_negative:>5.0%}")
    
    if skipped:
        print(f"\n{'─'*70}")
        print(f"SKIPPED CASES ({len(skipped)}):")
        for s in skipped:
            print(f"  - {s}")
    
    # Interpretation
    print(f"\n{'='*70}")
    print("INTERPRETATION")
    print(f"{'='*70}")
    
    if avg_hint_approved > avg_hint_negative + 0.10:
        print("✓ HINT shows meaningful separation between outcomes")
        if hint_correct >= total * 0.6:
            print("✓ HINT achieves acceptable standalone accuracy")
        else:
            print("⚠ HINT standalone accuracy needs improvement")
    else:
        print("⚠ HINT shows limited separation - use as secondary signal only")
    
    if ensemble_correct >= hint_correct:
        print("✓ Ensemble improves or maintains accuracy vs HINT alone")
    else:
        print("⚠ Ensemble may not add value for this dataset")
    
    print("="*70)
    
    return results

if __name__ == "__main__":
    results = run_backtest()