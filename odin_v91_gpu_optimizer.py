# ================================================================
# ODIN v9.1 GPU BILLION-PARAMETER OPTIMIZATION ENGINE (VRAM AWARE)
# + Robust CSV encoding (strings -> numeric) for fast GPU use
# ================================================================

import sys
import json
import time
import math
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------- GPU SETUP ----------------
try:
    import cupy as cp
    GPU_AVAILABLE = True
    print("✅ CuPy loaded - GPU acceleration enabled")
except Exception:
    GPU_AVAILABLE = False
    cp = None
    print("⚠️ CuPy not available - running on CPU")


# ---------------- CONFIG ----------------

@dataclass
class OptimizationConfig:
    dataset_path: str = str(
        Path(__file__).with_name("ODIN_ENRICHED_PDUFA_1349_v3_LUNARCRUSH.csv")
    )

    target_configs: int = 5_000_000_000

    # If autoscale_gpu_batch=True, this is treated as a "cap"
    batch_size: int = 500_000

    use_gpu: bool = True
    autoscale_gpu_batch: bool = True

    # VRAM sizing knobs
    vram_utilization: float = 0.70       # use up to 70% of *free* VRAM
    vram_overhead_factor: float = 1.25   # cushion for allocator + temp buffers
    min_batch_size: int = 10_000

    random_seed: int = 42

    # Encoding knobs
    max_unique_for_onehot: int = 0  # keep 0 for speed (we use factorize, not one-hot)
    verbose_encoding: bool = True


# ---------------- UTILS ----------------

def _human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024.0:
            return f"{x:.2f} {u}"
        x /= 1024.0
    return f"{x:.2f} PB"


def _is_probably_date_series(s: pd.Series) -> bool:
    """
    Heuristic: object column is "date-like" if a decent fraction parses as datetime.
    We keep this conservative to avoid wasting time.
    """
    if s.dtype != "object":
        return False
    sample = s.dropna().astype(str).head(200)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", utc=True)
    frac = parsed.notna().mean()
    return frac >= 0.60


def _encode_dataframe_to_float32(df: pd.DataFrame, verbose: bool = True) -> np.ndarray:
    """
    Convert a mixed-type DataFrame into a purely numeric float32 matrix.

    Strategy (fast + robust):
      1) Try numeric coercion for each column
      2) If object and date-like -> datetime -> days since epoch
      3) Else object -> pandas.factorize (category codes)
      4) Fill NaNs
    """
    if verbose:
        print(f"🧬 Encoding columns -> numeric float32 (cols={df.shape[1]:,}, rows={df.shape[0]:,})")

    out_cols = []
    dropped = 0

    for col in df.columns:
        s = df[col]

        # Fast path: already numeric/bool
        if pd.api.types.is_bool_dtype(s):
            out_cols.append(s.astype(np.float32))
            continue

        if pd.api.types.is_numeric_dtype(s):
            out_cols.append(pd.to_numeric(s, errors="coerce").astype(np.float32))
            continue

        # Try numeric coercion for object columns
        if s.dtype == "object":
            # Date-like?
            if _is_probably_date_series(s):
                dt = pd.to_datetime(s, errors="coerce", utc=True)
                # days since epoch (float32)
                days = (dt.view("int64") / 1e9) / 86400.0  # seconds->days
                out_cols.append(pd.Series(days, index=s.index).astype(np.float32))
                continue

            # Otherwise treat as categorical codes
            # factorize returns -1 for NaN
            codes, _uniques = pd.factorize(s, sort=False)
            out_cols.append(pd.Series(codes, index=s.index).astype(np.float32))
            continue

        # Fallback: try numeric coercion
        coerced = pd.to_numeric(s, errors="coerce")
        if coerced.notna().any():
            out_cols.append(coerced.astype(np.float32))
        else:
            dropped += 1

    if not out_cols:
        raise ValueError("❌ After encoding, no usable numeric columns remained.")

    X = np.column_stack(out_cols).astype(np.float32, copy=False)

    # Replace NaNs/Infs with 0 (GPU safe)
    # (NaNs can appear from coercion or invalid dates)
    np.nan_to_num(X, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    if verbose:
        print(f"✅ Encoded matrix: shape={X.shape} dtype={X.dtype} | dropped_cols={dropped}")

    return X


# ---------------- DATA LOADING ----------------

def load_and_encode_data(path: str, verbose: bool = True) -> np.ndarray:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"\n❌ Dataset not found:\n  {p}\n\n"
            f"✔ Fix: Place the CSV in the same folder as odin_v91_gpu_optimizer.py\n"
            f"✔ Or update OptimizationConfig.dataset_path\n"
        )

    print(f"📂 Loading dataset: {p.resolve()}")
    df = pd.read_csv(p, low_memory=False)

    if df.empty:
        raise ValueError("❌ Dataset loaded but is EMPTY")

    # IMPORTANT: We do NOT assume any label column here.
    # This optimizer is (currently) a pure parameter sweep placeholder.
    X = _encode_dataframe_to_float32(df, verbose=verbose)
    return X


# ---------------- VRAM-AWARE BATCH AUTOSCALING ----------------

def estimate_safe_gpu_batch_size(num_features: int, config: OptimizationConfig) -> int:
    """
    Estimate a safe batch size given free VRAM.
    Main allocations per batch (float32):
      params: batch * num_features * 4 bytes
      scores: batch * 4 bytes
    """
    if not GPU_AVAILABLE:
        return config.batch_size

    free_bytes, total_bytes = cp.cuda.runtime.memGetInfo()
    usable = int(free_bytes * float(config.vram_utilization))

    bytes_per_row = 4 * (num_features + 1)  # params row + score
    denom = int(bytes_per_row * float(config.vram_overhead_factor))
    if denom <= 0:
        return config.batch_size

    est = usable // denom
    est = max(int(config.min_batch_size), int(est))
    est = min(int(config.batch_size), int(est))  # cap

    print(
        f"🧠 VRAM autoscale: free={_human_bytes(free_bytes)} total={_human_bytes(total_bytes)} | "
        f"usable≈{_human_bytes(usable)} | est_batch≈{est:,} (cap={config.batch_size:,})"
    )
    return est


def find_working_batch_size(num_features: int, config: OptimizationConfig) -> int:
    """
    Probe allocation. If OOM, shrink by half until success.
    """
    if not (GPU_AVAILABLE and config.use_gpu):
        return config.batch_size

    bs = estimate_safe_gpu_batch_size(num_features, config) if config.autoscale_gpu_batch else config.batch_size

    while True:
        try:
            _a = cp.empty((bs, num_features), dtype=cp.float32)
            _b = cp.empty((bs,), dtype=cp.float32)
            del _a, _b
            cp.get_default_memory_pool().free_all_blocks()
            return bs
        except cp.cuda.memory.OutOfMemoryError:
            new_bs = max(config.min_batch_size, bs // 2)
            if new_bs == bs:
                raise
            print(f"⚠️ OOM at batch={bs:,} -> reducing to {new_bs:,} and retrying...")
            bs = new_bs


# ---------------- CORE OPTIMIZATION ----------------

def run_optimization(config: OptimizationConfig):
    np.random.seed(config.random_seed)

    print("=" * 70)
    print("ODIN v9.1 GPU BILLION-PARAMETER OPTIMIZATION (VRAM AWARE)")
    print("=" * 70)
    print(f"Target: {config.target_configs:,} configurations")
    print(f"Batch cap: {config.batch_size:,}")
    print(f"GPU: {'Yes' if (GPU_AVAILABLE and config.use_gpu) else 'No'}")
    print(f"Autoscale: {'Yes' if (GPU_AVAILABLE and config.use_gpu and config.autoscale_gpu_batch) else 'No'}")
    print()

    print("Loading dataset...")
    data_cpu = load_and_encode_data(config.dataset_path, verbose=config.verbose_encoding)  # float32 matrix
    num_features = data_cpu.shape[1]

    working_batch = find_working_batch_size(num_features, config)
    total_batches = math.ceil(config.target_configs / working_batch)

    # Precompute feature means once (fast)
    if GPU_AVAILABLE and config.use_gpu:
        data_gpu = cp.asarray(data_cpu, dtype=cp.float32)
        feature_means = cp.mean(data_gpu, axis=0)  # (num_features,)
        inv_features = cp.float32(1.0 / float(num_features))
    else:
        feature_means = np.mean(data_cpu, axis=0).astype(np.float32, copy=False)
        inv_features = np.float32(1.0 / float(num_features))

    best_score = -np.inf
    best_params = None
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch_start = batch_idx * working_batch
        batch_end = min((batch_idx + 1) * working_batch, config.target_configs)
        current_batch_size = batch_end - batch_start
        if current_batch_size <= 0:
            break

        try:
            if GPU_AVAILABLE and config.use_gpu:
                params = cp.random.random((current_batch_size, num_features), dtype=cp.float32)
                # scores = (params @ feature_means) / num_features
                scores = params.dot(feature_means) * inv_features

                bi = int(cp.argmax(scores).get())
                bs = float(scores[bi].get())
                bp = cp.asnumpy(params[bi])

            else:
                params = np.random.random((current_batch_size, num_features)).astype(np.float32, copy=False)
                scores = (params @ feature_means) * inv_features
                bi = int(np.argmax(scores))
                bs = float(scores[bi])
                bp = params[bi]

        except Exception as e:
            # If runtime OOM, shrink and continue
            if GPU_AVAILABLE and config.use_gpu and isinstance(e, cp.cuda.memory.OutOfMemoryError):
                new_batch = max(config.min_batch_size, working_batch // 2)
                if new_batch < working_batch:
                    print(f"🔥 Runtime OOM: shrinking batch {working_batch:,} -> {new_batch:,} and continuing...")
                    working_batch = new_batch
                    total_batches = math.ceil(config.target_configs / working_batch)
                    cp.get_default_memory_pool().free_all_blocks()
                    continue
            raise

        if bs > best_score:
            best_score = bs
            best_params = bp

        if (batch_idx + 1) % 5 == 0 or batch_idx == 0:
            elapsed = time.time() - start_time
            done = min((batch_idx + 1) * working_batch, config.target_configs)
            rate = done / max(elapsed, 1e-6)
            print(
                f"Batch {batch_idx + 1}/{total_batches} | done={done:,}/{config.target_configs:,} | "
                f"best={best_score:.6f} | {rate:,.0f} cfg/s | elapsed={elapsed:.1f}s | batch={working_batch:,}"
            )

    return {
        "best_score": float(best_score),
        "best_params": best_params.tolist() if best_params is not None else None,
        "elapsed_sec": float(time.time() - start_time),
        "effective_batch_size": int(working_batch),
        "gpu_used": bool(GPU_AVAILABLE and config.use_gpu),
        "num_features": int(num_features),
    }


# ---------------- MAIN ----------------

if __name__ == "__main__":
    try:
        config = OptimizationConfig()
        result = run_optimization(config)

        print("\n🏆 OPTIMIZATION COMPLETE")
        print(f"Best score: {result['best_score']:.6f}")
        print(f"Effective batch size: {result['effective_batch_size']:,}")
        print(f"GPU used: {result['gpu_used']}")
        print(f"Features: {result['num_features']:,}")
        print(f"Elapsed time: {result['elapsed_sec']:.2f}s")

        with open("odin_v91_best_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print("💾 Results saved to odin_v91_best_result.json")

    except Exception:
        print("\n❌ FATAL ERROR")
        traceback.print_exc()
        sys.exit(1)
