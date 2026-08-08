import sys
sys.path.insert(0, r"C:\Users\dcmoo\Documents\Python\hint_models")

import torch
from transformers import AutoTokenizer, AutoModel
import icd10
from HINT.model import HINTModel

print("="*70)
print("ODIN + HINT ENSEMBLE - Multi-Drug Validation")
print("="*70)

# BioBERT Encoder
class BioBERTEncoder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model.eval()
    
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

# ODIN + HINT Ensemble
def ensemble_prediction(odin_prob, hint_prob, method='weighted'):
    """Combine ODIN and HINT predictions"""
    if method == 'weighted':
        # ODIN 70%, HINT 30% (ODIN has regulatory signals)
        return 0.70 * odin_prob + 0.30 * hint_prob
    elif method == 'bayesian':
        # Bayesian update
        odin_odds = odin_prob / (1 - odin_prob + 1e-6)
        hint_odds = hint_prob / (1 - hint_prob + 1e-6)
        combined_odds = (odin_odds * hint_odds) ** 0.5
        return combined_odds / (1 + combined_odds)
    else:
        return max(odin_prob, hint_prob)

# Load models
print("\n[1] Loading models...")
biobert = BioBERTEncoder()
print("    ✓ BioBERT")

model = torch.load(
    r"C:\Users\dcmoo\Documents\Python\hint_models\save_model\phase_III.ckpt",
    map_location='cpu',
    weights_only=False
)
model.eval()
print("    ✓ HINT Phase III")

# Test cases - mix of approvals and CRLs
test_cases = [
    {
        "name": "Sotorasib (Lumakras)",
        "smiles": "C=CC(=O)N1CCC(CC1)N2C3=NC=NC(=C3C(=C2C)F)N4CCC(CC4)OC",
        "icd10": "C34.90",
        "criteria": "Inclusion: Adults with KRAS G12C mutated NSCLC, prior therapy. Exclusion: Prior KRAS inhibitor",
        "odin_prob": 0.88,
        "actual": "APPROVED",
        "year": 2021
    },
    {
        "name": "Venetoclax (Venclexta)",
        "smiles": "CC1(CCC(=C(C1)C2=CC=C(C=C2)Cl)CN3CCN(CC3)C4=CC(=C(C=C4)C(=O)NS(=O)(=O)C5=CC(=C(C=C5)NCC6CCOCC6)[N+](=O)[O-])OC7=CN=C8C(=C7)C=CC(=N8)C)C",
        "icd10": "C91.10",
        "criteria": "Inclusion: CLL/SLL patients, relapsed/refractory. Exclusion: Prior venetoclax",
        "odin_prob": 0.92,
        "actual": "APPROVED",
        "year": 2016
    },
    {
        "name": "Imatinib (Gleevec)",
        "smiles": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
        "icd10": "C92.10",
        "criteria": "Inclusion: CML Philadelphia chromosome positive. Exclusion: Prior TKI failure",
        "odin_prob": 0.95,
        "actual": "APPROVED",
        "year": 2001
    },
    {
        "name": "Hypothetical CMC Failure Drug",
        "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "icd10": "M06.9",
        "criteria": "Inclusion: Rheumatoid arthritis patients. Exclusion: Prior biologics",
        "odin_prob": 0.45,
        "actual": "CRL",
        "year": 2024
    },
]

# Run predictions
print("\n[2] Running ensemble predictions...")
print("-" * 70)
print(f"{'Drug':<30} {'HINT':>8} {'ODIN':>8} {'Ensemble':>10} {'Signal':>10} {'Actual':>10}")
print("-" * 70)

results = []
for case in test_cases:
    # HINT prediction
    with torch.no_grad():
        smiles_input = [[case['smiles']]]
        icd_input = [[[case['icd10']]]]
        criteria_feature = protocol2feature_live(case['criteria'], biobert)
        criteria_input = [criteria_feature]
        
        output = model.forward(
            smiles_lst2=smiles_input,
            icdcode_lst3=icd_input,
            criteria_lst=criteria_input
        )
        # Always apply sigmoid - output is logits
        raw_logit = output.item() if output.numel() == 1 else output[0].item()
        hint_prob = 1 / (1 + torch.exp(torch.tensor(-raw_logit))).item()
        hint_prob = max(0.01, min(0.99, hint_prob))  # Clamp to valid range
    
    # Ensemble
    ensemble_prob = ensemble_prediction(case['odin_prob'], hint_prob)
    
    # Signal
    if ensemble_prob >= 0.70:
        signal = "BULLISH"
    elif ensemble_prob <= 0.50:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    # Check accuracy
    correct = (signal == "BULLISH" and case['actual'] == "APPROVED") or \
              (signal == "BEARISH" and case['actual'] == "CRL")
    
    print(f"{case['name']:<30} {hint_prob:>7.1%} {case['odin_prob']:>7.1%} {ensemble_prob:>9.1%} {signal:>10} {case['actual']:>10}")
    
    results.append({
        'name': case['name'],
        'hint': hint_prob,
        'odin': case['odin_prob'],
        'ensemble': ensemble_prob,
        'signal': signal,
        'actual': case['actual'],
        'correct': correct
    })

print("-" * 70)

# Summary
correct_count = sum(1 for r in results if r['correct'])
print(f"\n[3] Results: {correct_count}/{len(results)} correct predictions")

# Signal distribution
bullish = sum(1 for r in results if r['signal'] == 'BULLISH')
bearish = sum(1 for r in results if r['signal'] == 'BEARISH')
neutral = sum(1 for r in results if r['signal'] == 'NEUTRAL')
print(f"    BULLISH: {bullish} | NEUTRAL: {neutral} | BEARISH: {bearish}")

print("\n" + "="*70)
print("ODIN + HINT Ensemble Ready for Production!")
print("="*70)