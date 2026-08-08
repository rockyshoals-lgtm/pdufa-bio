import sys
sys.path.insert(0, r"C:\Users\dcmoo\Documents\Python\hint_models")

import torch
import icd10
from HINT.model import HINTModel

# Load model on GPU
print("Loading HINT Phase III on GPU...")
model = torch.load(
    r"C:\Users\dcmoo\Documents\Python\hint_models\save_model\phase_III.ckpt",
    map_location='cuda',
    weights_only=False
)
model.eval()
print(f"✓ Model on {next(model.parameters()).device}")
print(f"✓ GPU: {torch.cuda.get_device_name(0)}")

# Inspect model forward signature
import inspect
sig = inspect.signature(model.forward)
print(f"\nModel forward() parameters:")
for name, param in sig.parameters.items():
    print(f"  - {name}: {param.default if param.default != inspect.Parameter.empty else 'required'}")

# Check what encode methods exist
print("\nModel methods:")
for attr in dir(model):
    if not attr.startswith('_') and callable(getattr(model, attr)):
        print(f"  - {attr}")