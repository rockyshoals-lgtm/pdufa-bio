#!/usr/bin/env python3
"""
ODIN v37.6 Runner
=================
Runs the ODIN v37.6 Multi-Head engine on a catalyst dataset.

Fix applied:
- Removed invalid SimplePriorTable import
- Engine now relies on internal priors + calibration registry
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

# ✅ FIXED IMPORTS
from odin_v37_engine import OdinV37MultiHead, CalibrationRegistry
from odina import generate_scatter_plot


def parse_args():
    parser = argparse.ArgumentParser(description="Run ODIN v37.6 on catalyst dataset")
    parser.add_argument("--input", required=True, help="Path to catalyst CSV / JSON / JSONL")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--model", default="ODIN_v37.6_HYBRID_HUNTER")
    parser.add_argument("--tag", default=None)
    return parser.parse_args()


def load_events(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".json":
        return pd.read_json(path)
    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)
    raise ValueError(f"Unsupported input format: {path}")


def main():
    args = parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[ODIN v37.6] Loading catalysts...")
    df = load_events(input_path)

    print(f"[ODIN v37.6] Loaded {len(df)} events")

    # Calibration registry (append-only)
    registry_path = out_dir / "calibration_registry.jsonl"
    registry = CalibrationRegistry(registry_path)

    # Initialize engine
    engine = OdinV37MultiHead(
        model_name=args.model,
        calibration_registry=registry
    )

    predictions = []
    ledger_path = out_dir / "ledger_forecasts.jsonl"

    print("[ODIN v37.6] Scoring events...")
    for _, row in df.iterrows():
        event = row.to_dict()
        result = engine.predict(event)

        predictions.append(result)

        # Append-only ledger write
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

    # Save predictions table
    pred_df = pd.DataFrame(predictions)
    pred_csv = out_dir / "predictions.csv"
    pred_df.to_csv(pred_csv, index=False)

    print(f"[ODIN v37.6] Predictions written to {pred_csv}")

    # Generate scatter plot (required by ODIN baseline)
    try:
        generate_scatter_plot(
            df=pred_df,
            out_dir=out_dir,
            title=f"ODIN v37.6 — {args.tag or 'Run'}"
        )
        print("[ODIN v37.6] Scatter plot generated")
    except Exception as e:
        print(f"[ODIN v37.6] Scatter plot skipped: {e}")

    # Write run metadata
    meta = {
        "model": args.model,
        "tag": args.tag,
        "input_file": str(input_path),
        "n_events": len(df),
        "generated_utc": datetime.utcnow().isoformat() + "Z"
    }

    with open(out_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("[ODIN v37.6] Run complete.")


if __name__ == "__main__":
    main()
