import sys
sys.path.insert(0, r"C:\Users\dcmoo\Documents\Python\hint_models")

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

print("="*60)
print("HINT + ODIN Integration Test (Custom Protocol Encoder)")
print("="*60)

# Custom BioBERT encoder (replaces broken pickle file)
class BioBERTEncoder:
    def __init__(self):
        print("    Loading BioBERT...")
        self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        self.model.eval()
        print("    ✓ BioBERT loaded")
    
    def encode(self, text):
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
            outputs = self.model(**inputs)
            # Use [CLS] token embedding (768-dim)
            return outputs.last_hidden_state[:, 0, :]

def protocol2feature_live(protocol, encoder):
    """Encode protocol on-the-fly with BioBERT"""
    protocol = protocol.lower()
    lines = [l.strip() for l in protocol.split('\n') if l.strip()]
    
    # Split into inclusion/exclusion
    inc_idx = next((i for i, l in enumerate(lines) if 'inclusion' in l), 0)
    exc_idx = next((i for i, l in enumerate(lines) if 'exclusion' in l), len(lines))
    
    inclusion = lines[inc_idx:exc_idx] if inc_idx < exc_idx else lines
    exclusion = lines[exc_idx:] if exc_idx < len(lines) else []
    
    # Encode
    if inclusion:
        inc_embeds = torch.cat([encoder.encode(s) for s in inclusion[:10]], 0)  # Limit to 10
    else:
        inc_embeds = torch.zeros(1, 768)
    
    if exclusion:
        exc_embeds = torch.cat([encoder.encode(s) for s in exclusion[:10]], 0)
    else:
        exc_embeds = torch.zeros(1, 768)
    
    return inc_embeds, exc_embeds

# Load BioBERT
print("\n[1] Loading BioBERT encoder...")
biobert = BioBERTEncoder()

# Load HINT model
print("\n[2] Loading HINT Phase III...")
import icd10
from HINT.model import HINTModel
model = torch.load(
    r"C:\Users\dcmoo\Documents\Python\hint_models\save_model\phase_III.ckpt",
    map_location='cpu',
    weights_only=False
)
model.eval()
print(f"    ✓ HINT model loaded")

# Test case: Sotorasib for NSCLC
print("\n[3] Test Case: Sotorasib + NSCLC")
test_drug = {
    "name": "Sotorasib (Lumakras)",
    "smiles": "C=CC(=O)N1CCC(CC1)N2C3=NC=NC(=C3C(=C2C)F)N4CCC(CC4)OC",
    "icd10": "C34.90",
    "criteria": """Inclusion Criteria:
Adults 18 years or older
KRAS G12C mutation confirmed
Locally advanced or metastatic NSCLC
At least one prior systemic therapy
ECOG performance status 0-1
Exclusion Criteria:
Prior treatment with KRAS G12C inhibitor
Active brain metastases
Severe hepatic impairment"""
}

print(f"    Drug: {test_drug['name']}")
print(f"    ICD-10: {test_drug['icd10']}")

# Preprocess
print("\n[4] Encoding inputs...")
smiles_input = [[test_drug['smiles']]]
icd_input = [[[test_drug['icd10']]]]
criteria_feature = protocol2feature_live(test_drug['criteria'], biobert)
criteria_input = [criteria_feature]
print(f"    ✓ All inputs encoded")

# Run inference
print("\n[5] Running HINT inference...")
with torch.no_grad():
    try:
        output = model.forward(
            smiles_lst2=smiles_input,
            icdcode_lst3=icd_input,
            criteria_lst=criteria_input
        )
        
        if isinstance(output, torch.Tensor):
            if output.max() > 1 or output.min() < 0:
                prob = torch.sigmoid(output).item()
            else:
                prob = output.item() if output.numel() == 1 else output[0].item()
        else:
            prob = float(output)
            
        print(f"\n    🎯 HINT Prediction: {prob:.1%} approval probability")
        
        if prob >= 0.65:
            signal = "BULLISH"
        elif prob <= 0.45:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
        print(f"    📊 Signal: {signal}")
        
    except Exception as e:
        print(f"    ✗ Inference error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)