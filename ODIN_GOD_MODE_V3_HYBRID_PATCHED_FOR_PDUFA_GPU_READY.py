#!/usr/bin/env python3
"""
ODIN GOD MODE V4 - MAXIMUM GPU UTILIZATION
Optimized for RTX 4070 (12GB VRAM)
Target: 50-100+ Million iterations/second
"""

import pandas as pd
import numpy as np
import time
import json
import sys
from datetime import datetime

# ==========================================
# HARDWARE CHECK
# ==========================================
try:
    import cupy as cp
    from cupy import cuda
    
    # Get device info using correct CuPy API
    device = cuda.Device(0)
    device.use()
    
    # Get device properties via runtime API
    device_props = cp.cuda.runtime.getDeviceProperties(0)
    device_name = device_props['name'].decode() if isinstance(device_props['name'], bytes) else device_props['name']
    
    # Get memory info
    free_mem, total_mem = device.mem_info
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 GPU: {device_name}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 VRAM: {total_mem / 1e9:.1f} GB ({free_mem / 1e9:.1f} GB free)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 SMs: {device_props['multiProcessorCount']}")
    GPU_MODE = True
    
except ImportError:
    print("❌ CuPy required. Install: pip install cupy-cuda12x")
    sys.exit(1)

# ==========================================
# CONFIGURATION - MAXED FOR RTX 4070
# ==========================================
DATASET_FILE = 'ODIN_PDUFA_1349_GPU_READY.csv'

# RTX 4070: 12GB VRAM, 46 SMs, 5888 CUDA cores
# Optimal batch: maximize occupancy without OOM
# With 14 params * 4 bytes * batch + scores (1349 * batch * 4 bytes)
# ~2.5M batch uses about 6-7GB, leaving headroom
BATCH_SIZE = 2_500_000  # 2.5 Million configs per GPU pass
NUM_STREAMS = 4  # Parallel CUDA streams

# ==========================================
# FUSED CUDA KERNEL - Single pass scoring
# ==========================================
SCORING_KERNEL = cp.RawKernel(r'''
extern "C" __global__
void fused_score_kernel(
    // Feature arrays (length N = num_samples)
    const int* __restrict__ btd,
    const int* __restrict__ orphan,
    const int* __restrict__ priority,
    const int* __restrict__ fast,
    const int* __restrict__ exp,
    const int* __restrict__ inexp,
    const int* __restrict__ mfg,
    const int* __restrict__ pain,
    const int* __restrict__ cns,
    const int* __restrict__ onco,
    const int* __restrict__ inf,
    const float* __restrict__ adcom_pct,
    const int* __restrict__ y_true,
    // Parameters (length B = batch_size) 
    const float* __restrict__ w_btd,
    const float* __restrict__ w_orphan,
    const float* __restrict__ w_priority,
    const float* __restrict__ w_fast,
    const float* __restrict__ w_exp,
    const float* __restrict__ w_mfg_pen,
    const float* __restrict__ w_mfg_amp,
    const float* __restrict__ adj_pain,
    const float* __restrict__ adj_cns,
    const float* __restrict__ adj_cns_amp,
    const float* __restrict__ adj_onco,
    const float* __restrict__ adj_inf,
    const float* __restrict__ w_adcom,
    const float* __restrict__ i_mfg_inexp,
    // Output: aggregated metrics per config (length B)
    float* __restrict__ out_brier,
    int* __restrict__ out_tp,
    int* __restrict__ out_fp,
    int* __restrict__ out_tn,
    int* __restrict__ out_fn,
    // Dimensions
    int N, int B
) {
    // Each block handles one config, threads cooperate on samples
    int config_idx = blockIdx.x;
    if (config_idx >= B) return;
    
    // Load params into registers (fast!)
    float p_btd = w_btd[config_idx];
    float p_orphan = w_orphan[config_idx];
    float p_priority = w_priority[config_idx];
    float p_fast = w_fast[config_idx];
    float p_exp = w_exp[config_idx];
    float p_mfg_pen = w_mfg_pen[config_idx];
    float p_mfg_amp = w_mfg_amp[config_idx];
    float p_adj_pain = adj_pain[config_idx];
    float p_adj_cns = adj_cns[config_idx];
    float p_adj_cns_amp = adj_cns_amp[config_idx];
    float p_adj_onco = adj_onco[config_idx];
    float p_adj_inf = adj_inf[config_idx];
    float p_w_adcom = w_adcom[config_idx];
    float p_i_mfg = i_mfg_inexp[config_idx];
    
    // Shared memory for block reduction
    __shared__ float s_brier[256];
    __shared__ int s_tp[256];
    __shared__ int s_fp[256];
    __shared__ int s_tn[256];
    __shared__ int s_fn[256];
    
    int tid = threadIdx.x;
    float local_brier = 0.0f;
    int local_tp = 0, local_fp = 0, local_tn = 0, local_fn = 0;
    
    // Each thread processes multiple samples (grid-stride)
    for (int i = tid; i < N; i += blockDim.x) {
        // Compute score
        float score = 0.85f;  // Base approval rate
        
        score += btd[i] * p_btd;
        score += orphan[i] * p_orphan;
        score += priority[i] * p_priority;
        score += fast[i] * p_fast;
        score += exp[i] * p_exp;
        
        // Manufacturing interaction
        float eff_pen = p_mfg_pen * (1.0f + (p_i_mfg - 1.0f) * inexp[i]);
        score += mfg[i] * eff_pen * p_mfg_amp;
        
        // Therapeutic areas
        score += pain[i] * p_adj_pain;
        score += onco[i] * p_adj_onco;
        score += inf[i] * p_adj_inf;
        
        // CNS interaction
        float cns_adj = p_adj_cns + (p_adj_cns_amp * inexp[i]);
        score += cns[i] * cns_adj;
        
        // AdCom
        score += adcom_pct[i] * p_w_adcom;
        
        // Clamp probability
        float prob = fminf(0.99f, fmaxf(0.01f, score));
        int pred = (prob >= 0.5f) ? 1 : 0;
        int truth = y_true[i];
        
        // Accumulate metrics
        float diff = prob - truth;
        local_brier += diff * diff;
        
        local_tp += (pred == 1 && truth == 1);
        local_fp += (pred == 1 && truth == 0);
        local_tn += (pred == 0 && truth == 0);
        local_fn += (pred == 0 && truth == 1);
    }
    
    // Store to shared memory
    s_brier[tid] = local_brier;
    s_tp[tid] = local_tp;
    s_fp[tid] = local_fp;
    s_tn[tid] = local_tn;
    s_fn[tid] = local_fn;
    __syncthreads();
    
    // Parallel reduction
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            s_brier[tid] += s_brier[tid + s];
            s_tp[tid] += s_tp[tid + s];
            s_fp[tid] += s_fp[tid + s];
            s_tn[tid] += s_tn[tid + s];
            s_fn[tid] += s_fn[tid + s];
        }
        __syncthreads();
    }
    
    // Write results
    if (tid == 0) {
        out_brier[config_idx] = s_brier[0] / N;
        out_tp[config_idx] = s_tp[0];
        out_fp[config_idx] = s_fp[0];
        out_tn[config_idx] = s_tn[0];
        out_fn[config_idx] = s_fn[0];
    }
}
''', 'fused_score_kernel')


class ODIN_RTX_Engine_V4:
    def __init__(self, filepath):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 LOADING DATASET...")
        
        # Search bounds - define FIRST before preallocate_buffers needs it
        self.bounds = {
            'w_btd': (0.08, 0.15), 
            'w_orphan': (0.01, 0.08), 
            'w_priority': (0.04, 0.13), 
            'w_fast': (0.03, 0.11),
            'w_exp': (0.03, 0.15), 
            'w_mfg_pen': (-0.50, -0.25), 
            'w_mfg_amp': (1.0, 1.5),
            'adj_pain': (-0.40, -0.20), 
            'adj_cns': (-0.15, 0.00), 
            'adj_cns_amp': (-0.25, -0.05),
            'adj_onco': (0.03, 0.12), 
            'adj_inf': (0.08, 0.15),
            'w_adcom': (0.10, 0.25),
            'i_mfg_inexp': (0.95, 1.35)
        }
        self.param_names = list(self.bounds.keys())
        self.top_10 = []
        
        self.load_and_sanitize(filepath)
        self.prepare_tensors()
        self.preallocate_buffers()
        self.create_streams()
        self.validate_features()

    def load_and_sanitize(self, filepath):
        try:
            self.df = pd.read_csv(filepath)
        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            sys.exit(1)
            
        self.df.columns = self.df.columns.str.strip()
        print(f"   📊 Loaded {len(self.df)} rows, {len(self.df.columns)} columns")
        
        if 'outcome' in self.df.columns:
            self.df['target_norm'] = self.df['outcome'].astype(str).str.upper()
        else:
            raise ValueError("No 'outcome' column found!")
            
        self.y_true = self.df['target_norm'].isin(['APPROVAL', 'APPROVED', '1', 'TRUE', 'YES']).astype(int).values
        self.N = len(self.y_true)
        
        n_approved = self.y_true.sum()
        n_crl = self.N - n_approved
        print(f"   ✅ Target: {n_approved} approvals, {n_crl} CRLs ({n_approved/self.N*100:.1f}% rate)")

    def prepare_tensors(self):
        """Upload features to GPU as int32 for kernel compatibility"""
        print("⚙️  PREPARING GPU TENSORS...")
        
        def get_bool(col):
            if col in self.df.columns:
                vals = self.df[col].astype(str).str.upper()
                return vals.isin(['TRUE', '1', 'YES']).values.astype(np.int32)
            return np.zeros(self.N, dtype=np.int32)
        
        def get_numeric(col, default=0):
            if col in self.df.columns:
                return pd.to_numeric(self.df[col], errors='coerce').fillna(default).values.astype(np.float32)
            return np.full(self.N, default, dtype=np.float32)
        
        # Integer features for kernel
        self.feat_btd = cp.asarray(get_bool('btd'), dtype=cp.int32)
        self.feat_orphan = cp.asarray(get_bool('orphan'), dtype=cp.int32)
        self.feat_priority = cp.asarray(get_bool('priority_review'), dtype=cp.int32)
        self.feat_fast = cp.asarray(get_bool('fast_track'), dtype=cp.int32)
        
        if 'experienced_sponsor' in self.df.columns:
            exp_mask = self.df['experienced_sponsor'].astype(str).str.upper().isin(['TRUE', '1', 'YES']).values
        else:
            exp_mask = np.zeros(self.N, dtype=bool)
        
        self.feat_exp = cp.asarray(exp_mask.astype(np.int32))
        self.feat_inexp = cp.asarray((~exp_mask).astype(np.int32))
        
        self.feat_mfg = cp.asarray(get_bool('manufacturing_risk'), dtype=cp.int32)
        
        ta = self.df['therapeutic_area'].astype(str).str.lower() if 'therapeutic_area' in self.df.columns else pd.Series([''] * self.N)
        self.feat_pain = cp.asarray(ta.str.contains('pain', case=False, na=False).values.astype(np.int32))
        self.feat_cns = cp.asarray(ta.str.contains('cns', case=False, na=False).values.astype(np.int32))
        self.feat_onco = cp.asarray(ta.str.contains('oncol', case=False, na=False).values.astype(np.int32))
        self.feat_inf = cp.asarray(ta.str.contains('infect', case=False, na=False).values.astype(np.int32))
        
        adcom_pct = get_numeric('adcom_vote_pct', default=0) / 100.0
        had_adcom = get_bool('had_adcom')
        self.feat_adcom_pct = cp.asarray(np.where(had_adcom == 1, adcom_pct, 0).astype(np.float32))
        
        self.y_true_gpu = cp.asarray(self.y_true.astype(np.int32))
        
        print(f"   ✅ Features uploaded to GPU")

    def preallocate_buffers(self):
        """Pre-allocate all GPU memory to avoid allocation overhead"""
        print("⚙️  PRE-ALLOCATING GPU BUFFERS...")
        
        B = BATCH_SIZE
        
        # Parameter buffers (14 params)
        self.param_buffers = {name: cp.empty(B, dtype=cp.float32) for name in self.bounds.keys()}
        
        # Output metric buffers
        self.out_brier = cp.empty(B, dtype=cp.float32)
        self.out_tp = cp.empty(B, dtype=cp.int32)
        self.out_fp = cp.empty(B, dtype=cp.int32)
        self.out_tn = cp.empty(B, dtype=cp.int32)
        self.out_fn = cp.empty(B, dtype=cp.int32)
        
        # Pre-generate random states for faster random number generation
        self.rng = cp.random.default_rng()
        
        print(f"   ✅ Buffers allocated: {BATCH_SIZE:,} configs/batch")

    def create_streams(self):
        """Create CUDA streams for overlapping operations"""
        self.streams = [cuda.Stream(non_blocking=True) for _ in range(NUM_STREAMS)]
        print(f"   ✅ Created {NUM_STREAMS} CUDA streams")

    def validate_features(self):
        print("\n📋 FEATURE VALIDATION:")
        
        checks = [
            ("Approvals", int(self.y_true.sum())),
            ("BTD", int(cp.sum(self.feat_btd))),
            ("Orphan", int(cp.sum(self.feat_orphan))),
            ("Priority", int(cp.sum(self.feat_priority))),
            ("Fast Track", int(cp.sum(self.feat_fast))),
            ("Experienced", int(cp.sum(self.feat_exp))),
            ("Mfg Risk", int(cp.sum(self.feat_mfg))),
            ("Oncology", int(cp.sum(self.feat_onco))),
        ]
        
        for name, val in checks:
            print(f"   {'✅' if val > 0 else '⚠️'} {name}: {val}")
        print()

    def run_opt(self, total_iterations, phase_name="SEARCH"):
        """Main optimization loop - MAXIMUM GPU UTILIZATION"""
        
        batches = (total_iterations + BATCH_SIZE - 1) // BATCH_SIZE
        actual_iterations = batches * BATCH_SIZE
        
        print(f"\n🔥 {phase_name}: {actual_iterations:,} iterations ({batches:,} batches)")
        print(f"   Batch size: {BATCH_SIZE:,} | Streams: {NUM_STREAMS}")
        
        # Kernel config: 256 threads per block, 1 block per config
        threads_per_block = 256
        blocks = BATCH_SIZE
        
        # Warmup kernel
        print("   ⏳ Warming up GPU...")
        self._run_single_batch(threads_per_block)
        cp.cuda.Device().synchronize()
        
        start_t = time.time()
        last_report = start_t
        processed = 0
        
        print(f"   🚀 Starting optimization...")
        
        for batch_idx in range(batches):
            # Run batch
            self._run_single_batch(threads_per_block)
            
            # Process results (overlap with next batch generation)
            self._process_batch_results()
            
            processed += BATCH_SIZE
            
            # Progress report every 2 seconds
            now = time.time()
            if now - last_report >= 2.0:
                elapsed = now - start_t
                rate = processed / elapsed / 1e6
                pct = 100.0 * batch_idx / batches
                eta = (batches - batch_idx) * (elapsed / (batch_idx + 1))
                
                best_score = self.top_10[0]['score'] if self.top_10 else 0
                
                print(f"\r   [{pct:5.1f}%] {processed/1e9:.2f}B done | "
                      f"{rate:.1f}M iter/s | ETA: {eta/60:.1f}min | "
                      f"Best: {best_score:.5f}", end='', flush=True)
                last_report = now
        
        # Final sync
        cp.cuda.Device().synchronize()
        
        total_time = time.time() - start_t
        final_rate = actual_iterations / total_time / 1e6
        
        print(f"\n\n✅ {phase_name} COMPLETE")
        print(f"   ⏱️  Time: {total_time:.1f}s")
        print(f"   🚀 Speed: {final_rate:.1f} Million iter/s")
        print(f"   📊 Total: {actual_iterations/1e9:.2f} Billion iterations")

    def _run_single_batch(self, threads_per_block):
        """Execute one batch using fused CUDA kernel"""
        
        B = BATCH_SIZE
        
        # Generate random parameters directly into pre-allocated buffers
        for name, (low, high) in self.bounds.items():
            buf = self.param_buffers[name]
            # CuPy RNG APIs vary by version; try 'out=' fast-path, else fallback.
            try:
                self.rng.uniform(low, high, size=B, dtype=cp.float32, out=buf)
            except TypeError:
                try:
                    r = self.rng.random(B, dtype=cp.float32)
                except TypeError:
                    r = self.rng.random(B).astype(cp.float32)
                buf[:] = r
                buf *= (high - low)
                buf += low
        
        # Launch fused kernel
        SCORING_KERNEL(
            (B,), (threads_per_block,),
            (
                self.feat_btd, self.feat_orphan, self.feat_priority, self.feat_fast,
                self.feat_exp, self.feat_inexp, self.feat_mfg,
                self.feat_pain, self.feat_cns, self.feat_onco, self.feat_inf,
                self.feat_adcom_pct, self.y_true_gpu,
                self.param_buffers['w_btd'], self.param_buffers['w_orphan'],
                self.param_buffers['w_priority'], self.param_buffers['w_fast'],
                self.param_buffers['w_exp'], self.param_buffers['w_mfg_pen'],
                self.param_buffers['w_mfg_amp'], self.param_buffers['adj_pain'],
                self.param_buffers['adj_cns'], self.param_buffers['adj_cns_amp'],
                self.param_buffers['adj_onco'], self.param_buffers['adj_inf'],
                self.param_buffers['w_adcom'], self.param_buffers['i_mfg_inexp'],
                self.out_brier, self.out_tp, self.out_fp, self.out_tn, self.out_fn,
                self.N, B
            )
        )

    def _process_batch_results(self):
        """Process batch results on GPU, extract top candidates"""
        
        # Compute precision filter on GPU
        precision = self.out_tp / (self.out_tp + self.out_fp + 1e-9)
        valid_mask = precision >= 0.94
        
        if not cp.any(valid_mask):
            return
        
        valid_idx = cp.where(valid_mask)[0]
        
        # Compute objective for valid configs
        spec = self.out_tn[valid_idx] / (self.out_tn[valid_idx] + self.out_fp[valid_idx] + 1e-9)
        brier = self.out_brier[valid_idx]
        fp = self.out_fp[valid_idx]
        
        obj_score = ((1.0 - brier) * 0.40) + (spec * 0.30) + ((1.0 - (fp / 20.0)) * 0.30)
        
        # Get top 10 from this batch
        k = min(10, len(obj_score))
        top_local_idx = cp.argsort(obj_score)[-k:]
        
        # Extract results to CPU only for top candidates
        for local_i in top_local_idx:
            real_idx = int(valid_idx[local_i])
            
            item = {
                'score': float(obj_score[local_i]),
                'metrics': {
                    'brier': float(brier[local_i]),
                    'precision': float(precision[real_idx]),
                    'specificity': float(spec[local_i]),
                    'fp': int(self.out_fp[real_idx]),
                    'fn': int(self.out_fn[real_idx]),
                    'tp': int(self.out_tp[real_idx]),
                    'tn': int(self.out_tn[real_idx])
                },
                'params': {k: float(self.param_buffers[k][real_idx]) for k in self.param_names}
            }
            self.top_10.append(item)
        
        # Keep only top 10 overall
        self.top_10.sort(key=lambda x: x['score'], reverse=True)
        self.top_10 = self.top_10[:10]

    def save_results(self):
        print("\n🏆 TOP 10 CONFIGURATIONS:")
        print("-" * 80)
        for i, res in enumerate(self.top_10):
            m = res['metrics']
            print(f"#{i+1}: Score {res['score']:.5f} | Brier {m['brier']:.5f} | "
                  f"Prec {m['precision']:.3f} | Spec {m['specificity']:.3f} | "
                  f"FP {m['fp']} | FN {m['fn']}")
        print("-" * 80)
        
        with open('GOD_ODIN_TOP_10_V4.json', 'w') as f:
            json.dump(self.top_10, f, indent=2)
        print(f"💾 Saved to GOD_ODIN_TOP_10_V4.json")
        
        if self.top_10:
            with open('ODIN_BEST_CONFIG_V4.json', 'w') as f:
                json.dump(self.top_10[0], f, indent=2)
            print("💾 Saved to ODIN_BEST_CONFIG_V4.json")


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    engine = ODIN_RTX_Engine_V4(DATASET_FILE)
    
    if engine.y_true.sum() == 0:
        print("❌ No approvals detected!")
        sys.exit(1)
    
    # --- PHASE 1 ---
    print("\n" + "="*60)
    print("⚔️  PHASE 1: GLOBAL SEARCH (1 BILLION ITERATIONS)")
    print("="*60)
    
    ITERATIONS_P1 = 1_000_000_000
    engine.run_opt(ITERATIONS_P1, "PHASE 1")
    
    if not engine.top_10:
        print("❌ No valid configs found. Try relaxing precision constraint.")
        sys.exit(1)
    
    best_p1 = engine.top_10[0]
    print(f"\n✅ PHASE 1 BEST: Score {best_p1['score']:.5f}")
    
    # --- PHASE 2 ---
    print("\n" + "="*60)
    print("🎯  PHASE 2: LOCAL REFINEMENT (500 MILLION)")
    print("="*60)
    
    # Narrow bounds around winner
    new_bounds = {}
    for k, v in best_p1['params'].items():
        span = max(abs(v * 0.10), 0.01)
        new_bounds[k] = (v - span, v + span)
    engine.bounds = new_bounds
    
    ITERATIONS_P2 = 500_000_000
    engine.run_opt(ITERATIONS_P2, "PHASE 2")
    
    # --- RESULTS ---
    print("\n" + "="*60)
    print("🏆 FINAL RESULTS")
    print("="*60)
    engine.save_results()