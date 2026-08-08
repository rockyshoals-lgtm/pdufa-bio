from __future__ import annotations
import argparse, json, os, time
from typing import Dict, Any, List

import numpy as np

from io_utils import load_dataset, ensure_dir, dataset_fingerprint, run_hash
from odin_score import score_probs, compute_metrics, fitness_from_metrics
from config_space import infer_bounds_from_top_configs, perturb_params, random_params

CODE_TAG = "ODIN_v38.a_billion_search_v1"

def load_top_configs(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Path to T-1 safe dataset CSV")
    ap.add_argument("--top-configs", required=True, help="Path to ODIN_TOP_CONFIGS_V5.json")
    ap.add_argument("--outdir", required=True, help="Output directory")
    ap.add_argument("--iters", type=int, default=50_000_000, help="Total iterations")
    ap.add_argument("--batch", type=int, default=250_000, help="Iterations per report batch")
    ap.add_argument("--min-precision", type=float, default=0.94, help="Hard precision floor")
    ap.add_argument("--explore-frac", type=float, default=0.10, help="Fraction of samples drawn uniformly (global) vs local refine")
    ap.add_argument("--sigma-frac", type=float, default=0.08, help="Local perturb strength as fraction of bound span")
    args = ap.parse_args()

    ensure_dir(args.outdir)
    ensure_dir(os.path.join(args.outdir, "runs"))
    ensure_dir(os.path.join(args.outdir, "reports"))

    df, cols = load_dataset(args.data)
    # --- label normalization (robust: handles strings, pandas StringDtype, categories, numeric) ---
    label_raw = df[cols.label]
    s = label_raw.fillna("").astype(str).str.strip().str.upper()

    # Initialize all unknown
    y = np.full(len(s), -1, dtype=np.int8)

    # Exact mappings (fast path)
    POS_EXACT = {"1","APPROVAL","APPROVED","APPROVE","ACCEPTED","POSITIVE","TENTATIVE APPROVAL","FULL APPROVAL"}
    NEG_EXACT = {
        "0","CRL","COMPLETE RESPONSE","COMPLETE RESPONSE LETTER",
        "REJECT","REJECTION","REFUSE","RTF","REFUSE TO FILE",
        "WITHDRAWN","WITHDRAWAL","DELAY","DEFERRED","NEGATIVE","DENIED","NOT APPROVED"
    }

    pos_mask = s.isin(POS_EXACT)
    neg_mask = s.isin(NEG_EXACT)
    y[pos_mask.to_numpy()] = 1
    y[neg_mask.to_numpy()] = 0

    # Substring/pattern mappings (handles e.g. "APPROVAL (WITH REMS)", "CRL ISSUED", etc.)
    # Apply only where still unknown.
    unk = (y == -1)
    if unk.any():
        s_unk = s[unk]
        # Positive if contains APPROV (but not "NOT APPROVED")
        pos2 = s_unk.str.contains("APPROV", regex=False) & (~s_unk.str.contains("NOT APPROV", regex=False))
        # Negative patterns
        neg2 = (
            s_unk.str.contains("CRL", regex=False) |
            s_unk.str.contains("COMPLETE RESPONSE", regex=False) |
            s_unk.str.contains("REFUSE TO FILE", regex=False) |
            s_unk.str.contains("RTF", regex=False) |
            s_unk.str.contains("REJECT", regex=False) |
            s_unk.str.contains("WITHDRAW", regex=False) |
            s_unk.str.contains("DENIED", regex=False) |
            s_unk.str.contains("NOT APPROV", regex=False)
        )

        # write back
        idx = s_unk.index.to_numpy()
        y[idx[pos2.to_numpy()]] = 1
        y[idx[neg2.to_numpy()]] = 0

    # Drop remaining unknown labels
    keep = (y != -1)
    dropped = int((~keep).sum())
    if keep.sum() == 0:
        # show a helpful message
        vc = s.value_counts().head(30).to_dict()
        raise ValueError(f"Could not map any labels to 0/1. Top label values: {vc}")

    df = df.loc[keep].reset_index(drop=True)
    y = y[keep]

    print(f"Resolved label column: {cols.label} | dtype={label_raw.dtype} | dropped_unknown={dropped}")
    print("Label counts:", {0: int((y==0).sum()), 1: int((y==1).sum())})

    top_cfgs = load_top_configs(args.top_configs)
    bounds = infer_bounds_from_top_configs(top_cfgs, pad_frac=0.20)
    seeds = [c["params"] for c in top_cfgs]

    data_fp = dataset_fingerprint(args.data)

    best = None
    best_fit = -1e18
    start = time.time()

    report_path = os.path.join(args.outdir, "reports", "progress.jsonl")
    best_path = os.path.join(args.outdir, "reports", "best.json")

    def eval_params(params: Dict[str, float]) -> Dict[str, Any]:
        p = score_probs(df, cols, params)
        thr = float(params.get("p_threshold", 0.85))
        m = compute_metrics(y, p, thr)
        fit = fitness_from_metrics(m, args.min_precision)
        return {"fitness": fit, "metrics": m.__dict__, "params": params}

    i = 0
    last_flush = time.time()
    with open(report_path, "a") as f:
        while i < args.iters:
            batch_n = min(args.batch, args.iters - i)
            for _ in range(batch_n):
                if np.random.rand() < args.explore_frac:
                    params = random_params(bounds)
                else:
                    base = seeds[np.random.randint(0, len(seeds))]
                    params = perturb_params(base, bounds, sigma_frac=args.sigma_frac)

                res = eval_params(params)
                fit = res["fitness"]
                if fit > best_fit:
                    best_fit = fit
                    best = res
                    payload = {
                        "code_tag": CODE_TAG,
                        "data_fingerprint": data_fp,
                        "run_hash": run_hash(res["params"], data_fp, CODE_TAG),
                        **res
                    }
                    tmp = best_path + ".tmp"
                    with open(tmp, "w") as bf:
                        json.dump(payload, bf, indent=2, sort_keys=True)
                    os.replace(tmp, best_path)

                if (time.time() - last_flush) > 2.0:
                    elapsed = time.time() - start
                    rate = (i + 1) / elapsed if elapsed else 0.0
                    f.write(json.dumps({
                        "i": i,
                        "elapsed_s": elapsed,
                        "iter_per_s": rate,
                        "best_fitness": best_fit,
                        "best_fp": best["metrics"]["fp"] if best else None,
                        "best_brier": best["metrics"]["brier"] if best else None,
                        "best_precision": best["metrics"]["precision"] if best else None,
                    }) + "\n")
                    f.flush()
                    last_flush = time.time()

                i += 1

            elapsed = time.time() - start
            rate = i / elapsed if elapsed else 0.0
            if best:
                print(f"[{i/args.iters:6.2%}] i={i:,} | {rate/1e6:6.2f} M it/s | best_fit={best_fit:,.1f} | "
                      f"prec={best['metrics']['precision']:.3f} fp={best['metrics']['fp']} brier={best['metrics']['brier']:.5f} mcc={best['metrics']['mcc']:.3f}")
            else:
                print(f"[{i/args.iters:6.2%}] i={i:,} | {rate/1e6:6.2f} M it/s | best=None")

    print("DONE. Best written to:", best_path)
    print("Progress log:", report_path)

if __name__ == "__main__":
    main()
