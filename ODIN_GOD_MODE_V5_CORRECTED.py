#!/usr/bin/env python3
"""
ODIN GOD MODE V5 - CORRECTED & ENHANCED
========================================
Based on audit of V3/V4, with the following fixes:
  1. Correct dataset filename (ODIN_ENRICHED_PDUFA_1356_v5_CORRECTED.csv)
  2. Filter out PENDING/BLA_WITHDRAWN records
  3. Fixed FP normalization bug (was /20, now /N_CRL)
  4. Dynamic base rate calculation
  5. Added high-value features: designation_stack_count, modality
  6. Improved therapeutic area matching (exact match + fallback)
  7. Enhanced CUDA kernel with new feature weights

Target: 50-100+ Million iterations/second on RTX 4070
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
    
    device = cuda.Device(0)
    device.use()
    
    device_props = cp.cuda.runtime.getDeviceProperties(0)
    device_name = device_props['name'].decode() if isinstance(device_props['name'], bytes) else device_props['name']
    
    free_mem, total_mem = device.mem_info
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 GPU: {device_name}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 VRAM: {total_mem / 1e9:.1f} GB ({free_mem / 1e9:.1f} GB free)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 SMs: {device_props['multiProcessorCount']}")
    GPU_MODE = True
    
except ImportError:
    print("❌ CuPy required. Install: pip install cupy-cuda12x")
    sys.exit(1)

# ==========================================
# CONFIGURATION
# ==========================================
# FIX #1: Correct dataset filename
DATASET_FILE = 'ODIN_ENRICHED_PDUFA_1356_v5_CORRECTED.csv'

# RTX 4070: 12GB VRAM, 46 SMs, 5888 CUDA cores
BATCH_SIZE = 2_500_000  # 2.5 Million configs per GPU pass
NUM_STREAMS = 4

# ==========================================
# ENHANCED CUDA KERNEL - With new features
# ==========================================
SCORING_KERNEL_V5 = cp.RawKernel(r'''
extern "C" __global__
void fused_score_kernel_v5(
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
    const int* __restrict__ rare,
    const int* __restrict__ opthal,
    const float* __restrict__ adcom_pct,
    const int* __restrict__ stack_count,  // NEW: designation stack
    const int* __restrict__ is_biologic,  // NEW: modality
    const int* __restrict__ is_cellgene,  // NEW: cell/gene therapy
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
    const float* __restrict__ adj_rare,
    const float* __restrict__ adj_opthal,
    const float* __restrict__ w_adcom,
    const float* __restrict__ i_mfg_inexp,
    const float* __restrict__ w_stack,     // NEW: weight per stack level
    const float* __restrict__ w_biologic,  // NEW: biologic bonus
    const float* __restrict__ w_cellgene,  // NEW: cell/gene therapy bonus
    // Output: aggregated metrics per config (length B)
    float* __restrict__ out_brier,
    int* __restrict__ out_tp,
    int* __restrict__ out_fp,
    int* __restrict__ out_tn,
    int* __restrict__ out_fn,
    // Dimensions
    int N, int B,
    float base_rate  // FIX #4: Dynamic base rate
) {
    int config_idx = blockIdx.x;
    if (config_idx >= B) return;
    
    // Load params into registers
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
    float p_adj_rare = adj_rare[config_idx];
    float p_adj_opthal = adj_opthal[config_idx];
    float p_w_adcom = w_adcom[config_idx];
    float p_i_mfg = i_mfg_inexp[config_idx];
    float p_w_stack = w_stack[config_idx];
    float p_w_biologic = w_biologic[config_idx];
    float p_w_cellgene = w_cellgene[config_idx];
    
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
        // FIX #4: Use dynamic base rate
        float score = base_rate;
        
        // Regulatory designations
        score += btd[i] * p_btd;
        score += orphan[i] * p_orphan;
        score += priority[i] * p_priority;
        score += fast[i] * p_fast;
        score += exp[i] * p_exp;
        
        // Manufacturing interaction
        float eff_pen = p_mfg_pen * (1.0f + (p_i_mfg - 1.0f) * inexp[i]);
        score += mfg[i] * eff_pen * p_mfg_amp;
        
        // Therapeutic areas (expanded)
        score += pain[i] * p_adj_pain;
        score += onco[i] * p_adj_onco;
        score += inf[i] * p_adj_inf;
        score += rare[i] * p_adj_rare;
        score += opthal[i] * p_adj_opthal;
        
        // CNS interaction
        float cns_adj = p_adj_cns + (p_adj_cns_amp * inexp[i]);
        score += cns[i] * cns_adj;
        
        // AdCom
        score += adcom_pct[i] * p_w_adcom;
        
        // NEW: Designation stack bonus (non-linear)
        score += stack_count[i] * p_w_stack;
        
        // NEW: Modality bonuses
        score += is_biologic[i] * p_w_biologic;
        score += is_cellgene[i] * p_w_cellgene;
        
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
''', 'fused_score_kernel_v5')


class ODIN_RTX_Engine_V5:
    def __init__(self, filepath):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 LOADING DATASET...")
        
        # Search bounds - EXPANDED for new features
        self.bounds = {
            'w_btd': (0.05, 0.18),
            'w_orphan': (0.00, 0.10),
            'w_priority': (0.02, 0.15),
            'w_fast': (0.02, 0.12),
            'w_exp': (0.02, 0.15),
            'w_mfg_pen': (-0.55, -0.20),
            'w_mfg_amp': (0.8, 1.6),
            'adj_pain': (-0.45, -0.15),  # Pain: 58% approval (very negative)
            'adj_cns': (-0.20, 0.00),     # CNS: 75% approval (negative)
            'adj_cns_amp': (-0.30, -0.05),
            'adj_onco': (0.02, 0.12),     # Oncology: 92.5% approval (positive)
            'adj_inf': (0.05, 0.18),      # Infectious: 97% approval (very positive)
            'adj_rare': (-0.10, 0.05),    # Rare: 82% approval (neutral)
            'adj_opthal': (-0.20, 0.00),  # Ophthalmology: 73.5% approval (negative)
            'w_adcom': (0.05, 0.30),
            'i_mfg_inexp': (0.90, 1.40),
            'w_stack': (0.01, 0.06),      # NEW: per-stack-level bonus
            'w_biologic': (-0.02, 0.08),  # NEW: biologic modality
            'w_cellgene': (0.02, 0.15),   # NEW: cell/gene therapy (93% approval)
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
        
        # FIX #2: Filter out PENDING and BLA_WITHDRAWN
        if 'outcome' in self.df.columns:
            self.df['target_norm'] = self.df['outcome'].astype(str).str.upper()
            
            # Count before filtering
            pending_count = self.df['target_norm'].isin(['PENDING']).sum()
            withdrawn_count = self.df['target_norm'].isin(['BLA_WITHDRAWN']).sum()
            
            if pending_count > 0 or withdrawn_count > 0:
                print(f"   ⚠️  Filtering out: {pending_count} PENDING, {withdrawn_count} BLA_WITHDRAWN")
                self.df = self.df[self.df['target_norm'].isin(['APPROVAL', 'APPROVED', 'CRL'])]
                print(f"   📊 After filtering: {len(self.df)} valid records")
        else:
            raise ValueError("No 'outcome' column found!")
        
        self.y_true = self.df['target_norm'].isin(['APPROVAL', 'APPROVED']).astype(int).values
        self.N = len(self.y_true)
        
        self.n_approved = self.y_true.sum()
        self.n_crl = self.N - self.n_approved
        
        # FIX #4: Compute dynamic base rate
        self.base_rate = self.n_approved / self.N
        
        print(f"   ✅ Target: {self.n_approved} approvals, {self.n_crl} CRLs ({self.base_rate*100:.1f}% rate)")
        print(f"   📈 Base rate for kernel: {self.base_rate:.4f}")

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
        
        # Core regulatory designations
        self.feat_btd = cp.asarray(get_bool('btd'), dtype=cp.int32)
        self.feat_orphan = cp.asarray(get_bool('orphan'), dtype=cp.int32)
        self.feat_priority = cp.asarray(get_bool('priority_review'), dtype=cp.int32)
        self.feat_fast = cp.asarray(get_bool('fast_track'), dtype=cp.int32)
        
        # Sponsor experience
        if 'experienced_sponsor' in self.df.columns:
            exp_mask = self.df['experienced_sponsor'].astype(str).str.upper().isin(['TRUE', '1', 'YES']).values
        else:
            exp_mask = np.zeros(self.N, dtype=bool)
        
        self.feat_exp = cp.asarray(exp_mask.astype(np.int32))
        self.feat_inexp = cp.asarray((~exp_mask).astype(np.int32))
        
        # Manufacturing risk
        self.feat_mfg = cp.asarray(get_bool('manufacturing_risk'), dtype=cp.int32)
        
        # FIX #6: Improved therapeutic area matching (exact match)
        if 'therapeutic_area' in self.df.columns:
            ta = self.df['therapeutic_area'].astype(str).str.strip()
            
            # Exact matches first, then fallback to contains
            pain_mask = ta.str.lower().str.contains('pain', case=False, na=False)
            cns_mask = ta.str.lower().isin(['cns/neurology', 'cns', 'neurology']) | ta.str.lower().str.contains('neuro', na=False)
            onco_mask = ta.str.lower().str.contains('oncol', case=False, na=False)
            inf_mask = ta.str.lower().str.contains('infect', case=False, na=False)
            rare_mask = ta.str.lower().str.contains('rare', case=False, na=False)
            opthal_mask = ta.str.lower().str.contains('opthal|ophthal|eye', case=False, na=False, regex=True)
            
            self.feat_pain = cp.asarray(pain_mask.values.astype(np.int32))
            self.feat_cns = cp.asarray(cns_mask.values.astype(np.int32))
            self.feat_onco = cp.asarray(onco_mask.values.astype(np.int32))
            self.feat_inf = cp.asarray(inf_mask.values.astype(np.int32))
            self.feat_rare = cp.asarray(rare_mask.values.astype(np.int32))
            self.feat_opthal = cp.asarray(opthal_mask.values.astype(np.int32))
        else:
            self.feat_pain = cp.zeros(self.N, dtype=cp.int32)
            self.feat_cns = cp.zeros(self.N, dtype=cp.int32)
            self.feat_onco = cp.zeros(self.N, dtype=cp.int32)
            self.feat_inf = cp.zeros(self.N, dtype=cp.int32)
            self.feat_rare = cp.zeros(self.N, dtype=cp.int32)
            self.feat_opthal = cp.zeros(self.N, dtype=cp.int32)
        
        # AdCom
        adcom_pct = get_numeric('adcom_vote_pct', default=0) / 100.0
        had_adcom = get_bool('had_adcom')
        self.feat_adcom_pct = cp.asarray(np.where(had_adcom == 1, adcom_pct, 0).astype(np.float32))
        
        # NEW: Designation stack count
        if 'designation_stack_count' in self.df.columns:
            stack = get_numeric('designation_stack_count', default=0).astype(np.int32)
        else:
            # Compute from individual designations
            stack = (get_bool('btd') + get_bool('orphan') + 
                    get_bool('priority_review') + get_bool('fast_track')).astype(np.int32)
        self.feat_stack_count = cp.asarray(stack, dtype=cp.int32)
        
        # NEW: Modality features
        if 'modality' in self.df.columns:
            modality = self.df['modality'].astype(str).str.lower()
            is_biologic = modality.str.contains('antibod|biolog|peptide', case=False, na=False, regex=True)
            is_cellgene = modality.str.contains('cell|gene|rna|car-t|cart', case=False, na=False, regex=True)
            self.feat_is_biologic = cp.asarray(is_biologic.values.astype(np.int32))
            self.feat_is_cellgene = cp.asarray(is_cellgene.values.astype(np.int32))
        else:
            self.feat_is_biologic = cp.zeros(self.N, dtype=cp.int32)
            self.feat_is_cellgene = cp.zeros(self.N, dtype=cp.int32)
        
        # Target
        self.y_true_gpu = cp.asarray(self.y_true.astype(np.int32))
        
        print(f"   ✅ Features uploaded to GPU")

    def preallocate_buffers(self):
        """Pre-allocate all GPU memory to avoid allocation overhead"""
        print("⚙️  PRE-ALLOCATING GPU BUFFERS...")
        
        B = BATCH_SIZE
        
        # Parameter buffers (19 params now)
        self.param_buffers = {name: cp.empty(B, dtype=cp.float32) for name in self.bounds.keys()}
        
        # Output metric buffers
        self.out_brier = cp.empty(B, dtype=cp.float32)
        self.out_tp = cp.empty(B, dtype=cp.int32)
        self.out_fp = cp.empty(B, dtype=cp.int32)
        self.out_tn = cp.empty(B, dtype=cp.int32)
        self.out_fn = cp.empty(B, dtype=cp.int32)
        
        # Random generator
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
            ("CRLs", int(self.n_crl)),
            ("BTD", int(cp.sum(self.feat_btd))),
            ("Orphan", int(cp.sum(self.feat_orphan))),
            ("Priority", int(cp.sum(self.feat_priority))),
            ("Fast Track", int(cp.sum(self.feat_fast))),
            ("Experienced", int(cp.sum(self.feat_exp))),
            ("Mfg Risk", int(cp.sum(self.feat_mfg))),
            ("Pain TA", int(cp.sum(self.feat_pain))),
            ("CNS TA", int(cp.sum(self.feat_cns))),
            ("Oncology TA", int(cp.sum(self.feat_onco))),
            ("Infectious TA", int(cp.sum(self.feat_inf))),
            ("Rare TA", int(cp.sum(self.feat_rare))),
            ("Ophthalmology TA", int(cp.sum(self.feat_opthal))),
            ("Has AdCom", int(cp.sum(self.feat_adcom_pct > 0))),
            ("Biologic", int(cp.sum(self.feat_is_biologic))),
            ("Cell/Gene", int(cp.sum(self.feat_is_cellgene))),
        ]
        
        for name, val in checks:
            status = '✅' if val > 0 else '⚠️'
            print(f"   {status} {name}: {val}")
        print()

    def run_opt(self, total_iterations, phase_name="SEARCH"):
        """Main optimization loop - MAXIMUM GPU UTILIZATION"""
        
        batches = (total_iterations + BATCH_SIZE - 1) // BATCH_SIZE
        actual_iterations = batches * BATCH_SIZE
        
        print(f"\n🔥 {phase_name}: {actual_iterations:,} iterations ({batches:,} batches)")
        print(f"   Batch size: {BATCH_SIZE:,} | Streams: {NUM_STREAMS}")
        
        threads_per_block = 256
        
        # Warmup
        print("   ⏳ Warming up GPU...")
        self._run_single_batch(threads_per_block)
        cp.cuda.Device().synchronize()
        
        start_t = time.time()
        last_report = start_t
        processed = 0
        
        print(f"   🚀 Starting optimization...")
        
        for batch_idx in range(batches):
            self._run_single_batch(threads_per_block)
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
        
        # Generate random parameters
        for name, (low, high) in self.bounds.items():
            self.rng.uniform(low, high, size=B, dtype=cp.float32, out=self.param_buffers[name])
        
        # Launch enhanced kernel
        SCORING_KERNEL_V5(
            (B,), (threads_per_block,),
            (
                # Features (18 inputs)
                self.feat_btd, self.feat_orphan, self.feat_priority, self.feat_fast,
                self.feat_exp, self.feat_inexp, self.feat_mfg,
                self.feat_pain, self.feat_cns, self.feat_onco, self.feat_inf,
                self.feat_rare, self.feat_opthal,
                self.feat_adcom_pct, self.feat_stack_count,
                self.feat_is_biologic, self.feat_is_cellgene,
                self.y_true_gpu,
                # Parameters (19 weights)
                self.param_buffers['w_btd'], self.param_buffers['w_orphan'],
                self.param_buffers['w_priority'], self.param_buffers['w_fast'],
                self.param_buffers['w_exp'], self.param_buffers['w_mfg_pen'],
                self.param_buffers['w_mfg_amp'], self.param_buffers['adj_pain'],
                self.param_buffers['adj_cns'], self.param_buffers['adj_cns_amp'],
                self.param_buffers['adj_onco'], self.param_buffers['adj_inf'],
                self.param_buffers['adj_rare'], self.param_buffers['adj_opthal'],
                self.param_buffers['w_adcom'], self.param_buffers['i_mfg_inexp'],
                self.param_buffers['w_stack'], self.param_buffers['w_biologic'],
                self.param_buffers['w_cellgene'],
                # Outputs
                self.out_brier, self.out_tp, self.out_fp, self.out_tn, self.out_fn,
                # Dimensions
                self.N, B,
                np.float32(self.base_rate)  # FIX #4: Pass dynamic base rate
            )
        )

    def _process_batch_results(self):
        """Process batch results on GPU, extract top candidates"""
        
        # Precision filter
        precision = self.out_tp / (self.out_tp + self.out_fp + 1e-9)
        valid_mask = precision >= 0.94
        
        if not cp.any(valid_mask):
            return
        
        valid_idx = cp.where(valid_mask)[0]
        
        # Compute metrics for valid configs
        spec = self.out_tn[valid_idx] / (self.out_tn[valid_idx] + self.out_fp[valid_idx] + 1e-9)
        brier = self.out_brier[valid_idx]
        fp = self.out_fp[valid_idx]
        
        # FIX #3: Correct FP normalization using actual CRL count
        fp_penalty = 1.0 - (fp / float(self.n_crl))
        fp_penalty = cp.clip(fp_penalty, 0.0, 1.0)
        
        # Objective: balance Brier, specificity, and FP count
        obj_score = ((1.0 - brier) * 0.40) + (spec * 0.30) + (fp_penalty * 0.30)
        
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
                    'tn': int(self.out_tn[real_idx]),
                    'n_crl': self.n_crl,
                    'n_approved': self.n_approved
                },
                'params': {k: float(self.param_buffers[k][real_idx]) for k in self.param_names}
            }
            self.top_10.append(item)
        
        # Keep only top 10 overall
        self.top_10.sort(key=lambda x: x['score'], reverse=True)
        self.top_10 = self.top_10[:10]

    def save_results(self):
        print("\n🏆 TOP 10 CONFIGURATIONS:")
        print("-" * 90)
        for i, res in enumerate(self.top_10):
            m = res['metrics']
            print(f"#{i+1}: Score {res['score']:.5f} | Brier {m['brier']:.5f} | "
                  f"Prec {m['precision']:.3f} | Spec {m['specificity']:.3f} | "
                  f"FP {m['fp']}/{m['n_crl']} | FN {m['fn']}")
        print("-" * 90)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save top 10
        top10_file = f'GOD_ODIN_TOP_10_V5_{timestamp}.json'
        with open(top10_file, 'w') as f:
            json.dump(self.top_10, f, indent=2)
        print(f"💾 Saved to {top10_file}")
        
        # Save best config
        if self.top_10:
            best_file = f'ODIN_BEST_CONFIG_V5_{timestamp}.json'
            with open(best_file, 'w') as f:
                json.dump(self.top_10[0], f, indent=2)
            print(f"💾 Saved to {best_file}")
            
            # Also save a "latest" version for easy access
            with open('ODIN_BEST_CONFIG_V5_LATEST.json', 'w') as f:
                json.dump(self.top_10[0], f, indent=2)


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ODIN GOD MODE V5 - CORRECTED & ENHANCED")
    print("  Fixes: Dataset, Filtering, FP Normalization, Base Rate, Features")
    print("="*70 + "\n")
    
    engine = ODIN_RTX_Engine_V5(DATASET_FILE)
    
    if engine.y_true.sum() == 0:
        print("❌ No approvals detected!")
        sys.exit(1)
    
    # --- PHASE 1: Global Search ---
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
    print(f"   FP: {best_p1['metrics']['fp']}/{engine.n_crl} | FN: {best_p1['metrics']['fn']}")
    
    # --- PHASE 2: Local Refinement ---
    print("\n" + "="*60)
    print("🎯  PHASE 2: LOCAL REFINEMENT (500 MILLION)")
    print("="*60)
    
    # Narrow bounds around winner
    new_bounds = {}
    for k, v in best_p1['params'].items():
        span = max(abs(v * 0.12), 0.015)  # Slightly wider than V4
        new_bounds[k] = (v - span, v + span)
    engine.bounds = new_bounds
    
    ITERATIONS_P2 = 500_000_000
    engine.run_opt(ITERATIONS_P2, "PHASE 2")
    
    # --- RESULTS ---
    print("\n" + "="*60)
    print("🏆 FINAL RESULTS")
    print("="*60)
    engine.save_results()
    
    # Summary
    if engine.top_10:
        best = engine.top_10[0]
        m = best['metrics']
        print(f"\n📊 CHAMPION CONFIG SUMMARY:")
        print(f"   Brier Score: {m['brier']:.5f}")
        print(f"   Precision:   {m['precision']:.3f}")
        print(f"   Specificity: {m['specificity']:.3f}")
        print(f"   True Pos:    {m['tp']}/{m['n_approved']} approvals correctly predicted")
        print(f"   True Neg:    {m['tn']}/{m['n_crl']} CRLs correctly predicted")
        print(f"   False Pos:   {m['fp']} (predicted approval, got CRL)")
        print(f"   False Neg:   {m['fn']} (predicted CRL, got approval)")
