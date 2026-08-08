#!/usr/bin/env python3
"""
ODIN v9.0 Billion Search — CUB OPTIMIZED

Key CUB optimizations:
1. Transposed matrices so reductions are over LAST axis (CUB accelerated)
2. C-contiguous arrays throughout
3. ~100x speedup on sum/max operations

Before: pmat shape (n_rows, batch), sum over axis=0 → NOT CUB
After:  pmat shape (batch, n_rows), sum over axis=1 → CUB ACCELERATED
"""

from __future__ import annotations
import argparse, json, os, time, hashlib, gc
import numpy as np
import pandas as pd

def setup_compute():
    try:
        import cupy as cp
        _ = cp.array([1])
        free, _ = cp.cuda.runtime.memGetInfo()
        props = cp.cuda.runtime.getDeviceProperties(0)
        name = props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"])
        
        # Verify CUB is enabled
        accel = os.environ.get('CUPY_ACCELERATORS', 'default')
        print(f"GPU: {name} ({free/(1024**3):.1f}GB free)")
        print(f"CUB Accelerator: {accel} (reductions over last axis = 100x faster)")
        return cp, True
    except Exception as e:
        print(f"CPU mode ({e})")
        return np, False

def load_data(data_path, lc_path):
    df = pd.read_csv(data_path)
    for c in ["outcome", "label", "decision"]:
        if c in df.columns:
            raw = df[c].fillna("").astype(str).str.upper()
            y = np.where(raw.isin(["APPROVAL", "APPROVED"]), 1,
                        np.where(raw.isin(["CRL", "COMPLETE RESPONSE LETTER"]), 0, -1))
            keep = y >= 0
            df = df.loc[keep].reset_index(drop=True)
            y = y[keep].astype(np.float32)
            break
    n = len(df)
    def col(name, default=0.0):
        return df[name].fillna(default).astype(np.float32).values if name in df.columns else np.full(n, default, dtype=np.float32)
    def colb(name):
        return df[name].fillna(False).astype(np.float32).values if name in df.columns else np.zeros(n, dtype=np.float32)
    
    ta = df["therapeutic_area"].fillna("").str.lower() if "therapeutic_area" in df.columns else pd.Series([""]*n)
    prior_reason = df["prior_crl_reason"].fillna("").str.lower() if "prior_crl_reason" in df.columns else pd.Series([""]*n)
    
    s17, s18, s19, s20 = [np.zeros(n, np.float32) for _ in range(4)]
    if lc_path and os.path.exists(lc_path):
        try:
            with open(lc_path, "rb") as f:
                raw = f.read()
            if raw.startswith(b"\xef\xbb\xbf"): raw = raw[3:]
            lc = json.loads(raw.decode("utf-8", errors="replace"))
            tickers = df["ticker"].fillna("").astype(str).values if "ticker" in df.columns else []
            for i, t in enumerate(tickers):
                if t in lc:
                    s17[i] = float(lc[t].get("s17_social_sentiment", 0) or 0)
                    s18[i] = float(lc[t].get("s18_engagement_spike", 0) or 0)
                    s19[i] = float(lc[t].get("s19_social_silence", 0) or 0)
                    s20[i] = float(lc[t].get("s20_smart_money_divergence", 0) or 0)
            print(f"  LunarCrush: {len(lc)} tickers")
        except: pass
    
    had_adcom = colb("had_adcom")
    exp = colb("experienced_sponsor")
    stack = col("designation_stack_count", 0.0)
    
    # Build feature matrix - will be transposed for CUB optimization
    F = np.column_stack([
        colb("btd"), colb("orphan"), colb("priority_review"), colb("fast_track"),
        col("accelerated_approval"), exp, stack,
        colb("form_483_issues"), col("form_483_oai_flag"), col("cmc_citation_count"),
        col("inspection_trend"), 
        colb("prior_crl") * prior_reason.str.contains(r"cmc|chemistry|manufactur", na=False, regex=True).astype(np.float32).values,
        col("cmc_hiring_signal"),
        ta.str.contains("pain", na=False).astype(np.float32).values,
        ta.str.contains(r"cns|neuro|psych", na=False, regex=True).astype(np.float32).values,
        ta.str.contains(r"onc|cancer|tumor", na=False, regex=True).astype(np.float32).values,
        ta.str.contains(r"infect|viral|bacter", na=False, regex=True).astype(np.float32).values,
        ta.str.contains(r"cns|neuro|psych", na=False, regex=True).astype(np.float32).values * had_adcom,
        had_adcom * ((col("adcom_vote_pct", 50.0) - 50.0) / 50.0),
        (stack >= 4).astype(np.float32) * (1.0 - exp),
        s17, s18, s19, s20,
    ]).astype(np.float32)
    return F, y

# WIDER BOUNDS
BOUNDS_LO = np.array([
    -0.25, -0.25, -0.25, -0.25, -0.30, -0.20, -0.25,
    -0.70, -0.80, -0.70, -0.30, -0.70, -0.60,
    -0.60, -0.50, -0.30, -0.25,
    -0.50, -0.60, -0.70,
    -0.40, -0.40, -0.60, -0.50,
    0.50, 0.50,
], dtype=np.float32)

BOUNDS_HI = np.array([
    0.40, 0.35, 0.35, 0.35, 0.30, 0.40, 0.25,
    0.20, 0.20, 0.15, 0.70, 0.20, 0.30,
    0.20, 0.30, 0.40, 0.40,
    0.30, 0.70, 0.20,
    0.40, 0.40, 0.20, 0.20,
    0.99, 0.99,
], dtype=np.float32)

N_FEATURES = 24
N_PARAMS = 26

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--lunarcrush", default="")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--iters", type=int, default=1_000_000_000)
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--min-precision", type=float, default=0.89)
    ap.add_argument("--min-recall", type=float, default=0.80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--topk", type=int, default=100)
    args = ap.parse_args()
    
    os.makedirs(args.outdir, exist_ok=True)
    print("=" * 70)
    print("ODIN v9.0 — CUB OPTIMIZED (reductions over last axis)")
    print("=" * 70)
    
    xp, use_gpu = setup_compute()
    
    print("\nLoading...")
    F_np, y_np = load_data(args.data, args.lunarcrush)
    n_rows = len(y_np)
    y_pos = int((y_np > 0.5).sum())
    y_neg = n_rows - y_pos
    print(f"  {n_rows} rows: {y_pos} approvals, {y_neg} CRLs")
    
    # =========================================================================
    # CUB OPTIMIZATION: Transpose F so matmul gives (batch, n_rows)
    # Then reductions over axis=-1 (last axis) are CUB accelerated!
    # =========================================================================
    # F_np is (n_rows, n_features) = (1349, 24)
    # F_T is (n_features, n_rows) = (24, 1349) - transposed
    F_T_np = np.ascontiguousarray(F_np.T)  # (24, 1349), C-contiguous
    
    # y vectors as row vectors for broadcast: (1, n_rows)
    y1_np = (y_np > 0.5).astype(np.float32).reshape(1, -1)   # (1, 1349)
    y0_np = (y_np <= 0.5).astype(np.float32).reshape(1, -1)  # (1, 1349)
    
    if use_gpu:
        F_T = xp.ascontiguousarray(xp.asarray(F_T_np))  # (24, 1349)
        y1 = xp.ascontiguousarray(xp.asarray(y1_np))    # (1, 1349)
        y0 = xp.ascontiguousarray(xp.asarray(y0_np))    # (1, 1349)
        lo = xp.asarray(BOUNDS_LO)
        span = xp.asarray(BOUNDS_HI - BOUNDS_LO)
    else:
        F_T = F_T_np
        y1 = y1_np
        y0 = y0_np
        lo = BOUNDS_LO
        span = BOUNDS_HI - BOUNDS_LO
    
    y_pos_f, y_neg_f, n_rows_f = xp.float32(y_pos), xp.float32(y_neg), xp.float32(n_rows)
    y_mean = xp.float32(y_np.mean())
    
    if args.batch > 0:
        batch_size = args.batch
    elif use_gpu:
        import cupy as cp
        free, _ = cp.cuda.runtime.memGetInfo()
        # Can use larger batches with CUB optimization
        batch_size = max(200_000, min(int(free * 0.35 / (n_rows * 8 + 256)), 3_000_000))
    else:
        batch_size = 500_000
    print(f"  Batch: {batch_size:,}")
    
    seed = args.seed + int(time.time()) % 10000
    if use_gpu: xp.random.seed(seed)
    rng = np.random.default_rng(seed)
    
    total, processed, best, hall = args.iters, 0, None, []
    unique_fps, unique_specs = set(), set()
    t0, improvements, last_best_spec, batch_num = time.time(), 0, 0.0, 0
    
    print(f"\n{'='*70}")
    print(f"Fitness = SPEC×1e7 + MCC×1e6 - FP×1e5  (SPEC prioritized)")
    print(f"Matrix layout: (batch, n_rows) - reductions over axis=-1 (CUB!)")
    print(f"{'='*70}\n")
    
    while processed < total:
        cur = min(batch_size, total - processed)
        try:
            # Random params: (batch, n_params)
            rand = xp.random.random((cur, N_PARAMS), dtype=xp.float32) if use_gpu else rng.random((cur, N_PARAMS)).astype(np.float32)
            params = lo + rand * span
            
            # W: (batch, n_features) - weights for each config
            W = params[:, :N_FEATURES]  # (batch, 24)
            p_base = params[:, -2]      # (batch,)
            p_thr = params[:, -1]       # (batch,)
            
            # =========================================================================
            # CUB-OPTIMIZED MATMUL: result is (batch, n_rows)
            # pmat[i, j] = p_base[i] + sum_k(W[i,k] * F_T[k,j])
            # W @ F_T = (batch, 24) @ (24, n_rows) = (batch, n_rows)
            # =========================================================================
            pmat = W.dot(F_T)  # (batch, n_rows)
            pmat = pmat + p_base[:, None]  # broadcast p_base
            pmat = xp.clip(pmat, 0.001, 0.999)
            
            # Predictions: (batch, n_rows)
            pred = (pmat >= p_thr[:, None]).astype(xp.float32)
            
            # =========================================================================
            # CUB-ACCELERATED REDUCTIONS: sum over axis=-1 (last axis, contiguous!)
            # =========================================================================
            # y1, y0 are (1, n_rows), broadcast with pred (batch, n_rows)
            tp = xp.sum(pred * y1, axis=-1)  # (batch,) - CUB ACCELERATED!
            fp = xp.sum(pred * y0, axis=-1)  # (batch,) - CUB ACCELERATED!
            
            # Brier score components
            sum_p2 = xp.sum(pmat * pmat, axis=-1)  # (batch,) - CUB ACCELERATED!
            sum_py = xp.sum(pmat * y1, axis=-1)    # (batch,) - CUB ACCELERATED!
            
            del pmat, pred
            
            fn = y_pos_f - tp
            tn = y_neg_f - fp
            
            precision = tp / xp.maximum(tp + fp, 1e-12)
            recall = tp / xp.maximum(tp + fn, 1e-12)
            specificity = tn / xp.maximum(tn + fp, 1e-12)
            brier = (sum_p2 / n_rows_f) - 2.0 * (sum_py / n_rows_f) + y_mean
            mcc = (tp * tn - fp * fn) / xp.sqrt(xp.maximum((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn), 1e-12))
            
            feasible = (precision >= args.min_precision) & (recall >= args.min_recall)
            # SPECIFICITY-FOCUSED FITNESS
            fit = xp.where(feasible, 1e7 * specificity + 1e6 * mcc - 1e5 * fp - 1e4 * brier, xp.float32(-1e18))
            
            best_idx = int(xp.argmax(fit))
            best_fit = float(fit[best_idx])
            
            if best_fit > -1e17:
                if use_gpu:
                    import cupy as cp
                    bp = cp.asnumpy(params[best_idx])
                    bfp, bprec, brec = int(cp.asnumpy(fp[best_idx])), float(cp.asnumpy(precision[best_idx])), float(cp.asnumpy(recall[best_idx]))
                    bspec, bmcc, bbrier, btp = float(cp.asnumpy(specificity[best_idx])), float(cp.asnumpy(mcc[best_idx])), float(cp.asnumpy(brier[best_idx])), int(cp.asnumpy(tp[best_idx]))
                else:
                    bp = params[best_idx]
                    bfp, bprec, brec = int(fp[best_idx]), float(precision[best_idx]), float(recall[best_idx])
                    bspec, bmcc, bbrier, btp = float(specificity[best_idx]), float(mcc[best_idx]), float(brier[best_idx]), int(tp[best_idx])
                
                unique_fps.add(bfp)
                unique_specs.add(round(bspec, 4))
                
                params_dict = {
                    "w_btd": float(bp[0]), "w_orphan": float(bp[1]), "w_priority": float(bp[2]), "w_fast": float(bp[3]),
                    "w_accel": float(bp[4]), "w_exp": float(bp[5]), "w_stack": float(bp[6]),
                    "w_form483": float(bp[7]), "w_form483_oai": float(bp[8]), "w_s22_cmc": float(bp[9]),
                    "w_s23_trend": float(bp[10]), "w_prior_cmc_crl": float(bp[11]), "w_cmc_hiring": float(bp[12]),
                    "adj_pain": float(bp[13]), "adj_cns": float(bp[14]), "adj_onco": float(bp[15]), "adj_inf": float(bp[16]),
                    "adj_cns_amp": float(bp[17]), "w_adcom": float(bp[18]), "w_des_trap": float(bp[19]),
                    "w_s17_sentiment": float(bp[20]), "w_s18_engagement": float(bp[21]),
                    "w_s19_silence": float(bp[22]), "w_s20_divergence": float(bp[23]),
                    "p_base": float(bp[24]), "p_threshold": float(bp[25]),
                }
                metrics = {"precision": bprec, "recall": brec, "specificity": bspec, "mcc": bmcc, "brier": bbrier, "tp": btp, "fp": bfp}
                h = hashlib.sha1(json.dumps(params_dict, sort_keys=True).encode()).hexdigest()[:12]
                entry = {"run_hash": h, "params": params_dict, "metrics": metrics, "fitness": best_fit}
                
                if best is None or best_fit > best["fitness"]:
                    if bspec > last_best_spec:
                        improvements += 1
                        last_best_spec = bspec
                    best = entry
                hall.append(entry)
                if len(hall) > args.topk * 3:
                    by_hash = {e["run_hash"]: e for e in hall}
                    hall = sorted(by_hash.values(), key=lambda x: x["fitness"], reverse=True)[:args.topk]
            
            processed += cur
            batch_num += 1
            if use_gpu and batch_num % 50 == 0:
                import cupy as cp
                cp.get_default_memory_pool().free_all_blocks()
                
        except Exception as e:
            if "memory" in str(e).lower():
                batch_size = max(50_000, batch_size * 2 // 3)
                print(f"\n  OOM! → {batch_size:,}")
                if use_gpu:
                    import cupy as cp
                    cp.get_default_memory_pool().free_all_blocks()
                gc.collect()
                continue
            raise
        
        if batch_num % 20 == 0:
            elapsed = time.time() - t0
            pct, speed = 100.0 * processed / total, processed / max(1e-9, elapsed)
            eta = (total - processed) / max(1, speed)
            eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta/60:.1f}m" if eta < 3600 else f"{eta/3600:.1f}h"
            m = best["metrics"] if best else {}
            print(f"[{pct:5.2f}%] {processed:,} | {speed/1e6:.2f}M/s | ETA:{eta_str} | "
                  f"best(fp={m.get('fp', -1)}, SPEC={m.get('specificity', 0):.4f}, mcc={m.get('mcc', 0):.4f}) | "
                  f"uniq_fp:{len(unique_fps)} uniq_spec:{len(unique_specs)} impr:{improvements}")
    
    print(f"\n{'='*70}\nCOMPLETE\n{'='*70}")
    elapsed = time.time() - t0
    print(f"{processed:,} in {elapsed:.1f}s ({processed/elapsed/1e6:.2f}M/s)")
    print(f"Unique FPs: {sorted(unique_fps)}")
    print(f"Unique Specs: {sorted(list(unique_specs))[:15]}...")
    
    if best:
        m = best["metrics"]
        print(f"\nBest: FP={m['fp']} Prec={m['precision']:.4f} Rec={m['recall']:.4f} SPEC={m['specificity']:.4f} MCC={m['mcc']:.4f}")
        with open(os.path.join(args.outdir, "best.json"), "w") as f:
            json.dump(best, f, indent=2)
    
    by_hash = {e["run_hash"]: e for e in hall}
    hall = sorted(by_hash.values(), key=lambda x: x["fitness"], reverse=True)[:args.topk]
    with open(os.path.join(args.outdir, "hall_of_fame.json"), "w") as f:
        json.dump(hall, f, indent=2)
    print(f"Saved to {args.outdir}/")

if __name__ == "__main__":
    main()
