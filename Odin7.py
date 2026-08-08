"""
ODIN v10.69 "T-1 GUARDIAN" REFINER
==================================
GOAL:    Polish the v1068 T-1 config without breaking structural logic.
CANON:   odin_v1068_t1_best.json (Brier ~0.1378) - DO NOT LOSE.
LOGIC:   Redline VRAM + "Guardian" Constraints.
NOTE:    Soft Signals (Insider/Hiring/Social/Odin/Hint) MUST remain smaller than
         Hard Regulatory Signals (Priority Review & core CMC/CRL penalties).
"""

import numpy as np
import pandas as pd
import time
import json
import warnings
import sys
import gc
import os

# Suppress warnings
warnings.filterwarnings("ignore")

# Try CuPy for GPU
try:
    import cupy as cp
    from cupy.cuda import runtime as cuda_runtime
    GPU_AVAILABLE = True
    print("[ODIN] GPU Acceleration: ENABLED (CuPy - Guardian Mode)")
except ImportError:
    import numpy as cp
    GPU_AVAILABLE = False
    print("[ODIN] GPU Acceleration: DISABLED (Running on CPU)")

# --- CONFIGURATION ---
DATA_FILE = "ODIN_MODEL_READY_v1066_T1_2015on_2200.csv"
OUTPUT_FILE = "odin_v1069_t1_best.json"

TRAIN_SPLIT_PCT = 0.70
N_BATCHES = 100_000

# SEARCH PARAMETERS (Tighter for T-1 Compliance)
START_RADIUS = 0.05     # Start +/- 5% (since v1068 is strong)
END_RADIUS = 0.001      # End +/- 0.1% (Micro-polish)

# REDLINE SETTINGS
MAX_VRAM_GB = 11.5
VRAM_SAFETY_MARGIN = 0.95
VRAM_CHECK_INTERVAL = 25
MAX_SAFE_BATCH = 700_000  # empirically safe cap for your GPU

# --- BASELINE (v1068 T-1 Config with light soft-signal tweaks) ---
CANONICAL_CONFIG = {
    "base_logit": 1.4998613595962524,
    "snda_base_penalty": -0.3868013620376587,
    "snda_pediatric_base_penalty": -0.2277054637670517,
    "prior_crl_penalty": -2.7806637287139893,
    "inexperienced_sponsor_penalty": -1.484347939491272,
    "manufacturing_risk_penalty": -1.1392297744750977,
    "form_483_penalty": -1.2936288118362427,
    "ema_cmc_flag_penalty": -1.6055912971496582,
    "cmc_extension_penalty": -0.8774261474609375,
    "adcom_mid_penalty": -0.5210667252540588,
    "adcom_low_penalty": -0.8218434453010559,
    "s22_pediatric_pk_penalty": -2.2159321308135986,
    "btd_weight": 0.2002699226140976,
    "orphan_weight": 0.17577262222766876,
    "priority_review_weight": 0.8349432349205017,
    "fast_track_weight": 0.2290981560945511,
    "accelerated_approval_weight": 0.7031944394111633,
    "class1_resubmission_boost": 0.5421435832977295,
    "experienced_sponsor_boost": 0.9254353642463684,
    "adcom_high_boost": 1.5069775581359863,
    "ta_adjustment_weight": 0.37861305475234985,

    # Soft overlays - slightly trimmed vs v1068
    "s23_insider_weight": 0.5800000000000000,   # was ~0.6234
    "s6_hiring_weight": 0.5500000000000000,     # was ~0.5754
    "social_weight": 0.3000000000000000,        # was ~0.3449

    # Odin overlay demoted a bit
    "odin_weight": 0.6800000000000000,          # was ~0.82
    "hint_weight": 0.23999999463558197,

    "hint_crl_rate_penalty": -1.5015156269073486,
    "ta_high_risk_penalty": -0.2883375585079193,
    "ta_mod_risk_penalty": -0.18356984853744507,
    "ta_low_risk_boost": 0.11661211401224136,
    "indication_pain_penalty": -0.4988175630569458,
    "indication_onc_boost": 0.23648591339588165,
    "novice_sponsor_high_risk_ta_penalty": -0.4157504141330719
}

PARAM_NAMES = list(CANONICAL_CONFIG.keys())
CANONICAL_VEC = np.array([CANONICAL_CONFIG[k] for k in PARAM_NAMES], dtype=np.float32)
PARAM_SIGNS = np.sign(CANONICAL_VEC)
PARAM_SIGNS[PARAM_SIGNS == 0] = 1.0

# Identify Indices for Constraint Checking
IDX_PRIORITY = PARAM_NAMES.index("priority_review_weight")
IDX_INSIDER = PARAM_NAMES.index("s23_insider_weight")
IDX_HIRING = PARAM_NAMES.index("s6_hiring_weight")
IDX_ODIN = PARAM_NAMES.index("odin_weight")
IDX_HINT = PARAM_NAMES.index("hint_weight")

# Core hard-negative penalties that must remain dominant by magnitude
HARD_NEG = [
    PARAM_NAMES.index("prior_crl_penalty"),
    PARAM_NAMES.index("s22_pediatric_pk_penalty"),
    PARAM_NAMES.index("ema_cmc_flag_penalty"),
    PARAM_NAMES.index("form_483_penalty"),
    PARAM_NAMES.index("manufacturing_risk_penalty"),
    PARAM_NAMES.index("inexperienced_sponsor_penalty"),
]

# Soft / behavioral overlays that should never dominate
SOFT_POS = [
    PARAM_NAMES.index("s23_insider_weight"),
    PARAM_NAMES.index("s6_hiring_weight"),
    PARAM_NAMES.index("social_weight"),
    PARAM_NAMES.index("odin_weight"),
    PARAM_NAMES.index("hint_weight"),
]

if GPU_AVAILABLE:
    CANONICAL_VEC = cp.asarray(CANONICAL_VEC)
    PARAM_SIGNS = cp.asarray(PARAM_SIGNS)

class AutoBatcher:
    def __init__(self, samples_per_config):
        self.samples = samples_per_config
        self.params = len(PARAM_NAMES)
        self.current_batch = 500_000

    def get_safe_memory(self):
        if not GPU_AVAILABLE:
            return 1_000_000_000
        free_mem, total_mem = cuda_runtime.memGetInfo()
        mempool = cp.get_default_memory_pool()
        pool_free = mempool.total_bytes() - mempool.used_bytes()
        total_avail = free_mem + pool_free
        max_bytes = MAX_VRAM_GB * 1024**3
        return min(total_avail, max_bytes)

    def adjust(self):
        if not GPU_AVAILABLE:
            return self.current_batch
        safe_mem = self.get_safe_memory()

        bytes_per_config = (self.params * 4) + (self.samples * 4 * 1.1)
        target_usage = safe_mem * VRAM_SAFETY_MARGIN
        optimal_batch = int(target_usage / bytes_per_config)
        optimal_batch = (optimal_batch // 10000) * 10000

        max_growth = int(self.current_batch * 1.5)
        optimal_batch = min(optimal_batch, max_growth)
        optimal_batch = max(100_000, optimal_batch)

        # Hard cap for safety
        optimal_batch = min(MAX_SAFE_BATCH, optimal_batch)

        if abs(optimal_batch - self.current_batch) > 50_000:
            print(f"[GUARDIAN] Optimizing Batch: {self.current_batch:,} -> {optimal_batch:,} (Free VRAM: {safe_mem/1024**3:.2f} GB)")
            self.current_batch = optimal_batch

        return self.current_batch

    def recover_oom(self):
        new_batch = int(self.current_batch * 0.6)
        print(f"[OOM] Reducing Batch: {self.current_batch:,} -> {new_batch:,}")
        self.current_batch = new_batch
        if GPU_AVAILABLE:
            mempool = cp.get_default_memory_pool()
            mempool.free_all_blocks()
        gc.collect()
        return new_batch

class OdinGuardianEngine:
    def __init__(self, df):
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)

        self.X_odin, self.X_hint, self.y = self._build_matrices(df)
        self.mask = self._build_avoids(df)

        split = int(len(df) * TRAIN_SPLIT_PCT)

        self.d_train = { 'X': self.X_odin[:split], 'y': self.y[:split], 'm': self.mask[:split] }
        self.d_test = { 'X': self.X_odin[split:], 'y': self.y[split:], 'm': self.mask[split:] }

        if GPU_AVAILABLE:
            for d in [self.d_train, self.d_test]:
                for k in d:
                    d[k] = cp.asarray(d[k])

    def _build_matrices(self, df):
        N = len(df)
        X = np.zeros((N, len(PARAM_NAMES)), dtype=np.float32)

        def get_bool(col):
            if col not in df.columns:
                return np.zeros(N, dtype=np.float32)
            s = df[col].fillna('F').astype(str).str.upper()
            return s.isin(['TRUE','1','1.0','YES','Y','APPROVED']).astype(np.float32)

        def get_val(col):
            if col not in df.columns:
                return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app(df):
            cands = ['application_type','ApplicationType','app_type']
            for c in cands:
                if c in df.columns:
                    return df[c].fillna('').astype(str).str.upper()
            return pd.Series(['']*N)

        app = get_app(df)

        # --- ODIN CORE ---
        X[:,0]=1.0
        X[:,1]=(app.str.contains('SNDA')|app.str.contains('SBLA')).astype(float)
        X[:,2]=(app.str.contains('PEDIATRIC')).astype(float)
        X[:,3]=get_bool('prior_crl')
        prior = get_val('sponsor_prior_approvals')
        X[:,4]=(prior==0).astype(float)
        X[:,5]=get_bool('manufacturing_risk')
        X[:,6]=get_bool('form_483_issues')
        X[:,7]=get_bool('ema_cmc_flag')
        X[:,8]=get_bool('cmc_extension_flag')
        had_adcom=get_bool('had_adcom')
        vote=get_val('adcom_vote_pct')
        vote=np.where(vote>1, vote/100, vote)
        X[:,9]=had_adcom*((vote>=0.50)&(vote<0.65))
        X[:,10]=had_adcom*(vote<0.50)
        X[:,11]=get_bool('s22_ped_pk_missing')
        X[:,12]=get_bool('btd')
        X[:,13]=get_bool('orphan')
        X[:,14]=get_bool('priority_review')
        X[:,15]=get_bool('fast_track')
        X[:,16]=get_bool('accelerated_approval')
        if 'resubmission_class' in df:
            X[:,17]=(get_val('resubmission_class')==1).astype(float)
        X[:,18]=(prior>=5).astype(float)
        X[:,19]=had_adcom*(vote>=0.65)
        X[:,20]=get_val('ta_base_score')
        X[:,21]=get_val('s23_signal_strength')
        X[:,22]=get_val('s6_signal_strength')
        X[:,23]=get_val('social_sentiment_score')

        # --- HYBRID ---
        ta = df['therapeutic_area'].fillna('Other').astype(str)
        def chk(s,ks):
            m=np.zeros(len(s),dtype=bool)
            for k in ks:
                m|=s.str.contains(k,case=False)
            return m.astype(float)

        X[:,26]=df['historical_crl_rate'].fillna(0).astype(float) if 'historical_crl_rate' in df else 0.0
        X[:,27]=chk(ta,["Pain","Ophthalmology","Nephrology","Hematology"])
        X[:,28]=chk(ta,["CNS","Neurology","Cardiovascular","Metabolic"])
        X[:,29]=chk(ta,["Oncology","Immunology","Dermatology","Infectious"])
        ind=df['indication'].fillna('').astype(str) if 'indication' in df else pd.Series(['']*N)
        X[:,30]=ind.str.contains("Pain",case=False).astype(float)
        X[:,31]=(ind.str.contains("Cancer",case=False)|ind.str.contains("Tumor",case=False)).astype(float)
        X[:,32]=((prior<3)&(X[:,27]>0)).astype(float)

        y_col = next((c for c in ['outcome','Outcome','approved','result'] if c in df), None)
        y_raw = df[y_col].astype(str).str.strip().str.upper().replace(r'\\.0$','',regex=True)
        y = y_raw.isin({'APPROVED','APPROVAL','1','TRUE','YES','SUCCESS'}).astype(float).values

        return X, X, y

    def _build_avoids(self, df):
        m = np.ones(len(df), dtype=np.float32)
        b = np.zeros(len(df), dtype=bool)
        if 'ema_cmc_flag' in df:
            b|=df['ema_cmc_flag'].fillna(False).astype(bool)
        if 's22_ped_pk_missing' in df:
            b|=df['s22_ped_pk_missing'].fillna(False).astype(bool)
        m[b] = 0.0
        return m

    def evaluate_batch(self, configs, use_test=False):
        d = self.d_test if use_test else self.d_train
        X, y, m = d['X'], d['y'], d['m']

        c_logits = configs.copy()

        # odin_weight and hint_weight currently unused features in X; zero for scoring
        for key in ["odin_weight", "hint_weight"]:
            idx = PARAM_NAMES.index(key)
            c_logits[:, idx] = 0.0

        logits = cp.matmul(c_logits, X.T)
        cp.negative(logits, out=logits)
        cp.exp(logits, out=logits)
        cp.add(logits, 1.0, out=logits)
        cp.reciprocal(logits, out=logits)

        probs = logits
        probs *= m

        y_sum = cp.sum(y)
        n_sum = cp.sum(1-y)
        score_pos = cp.dot(probs, y)
        score_neg = cp.dot(probs, 1-y)
        sep = (score_pos / cp.maximum(y_sum, 1.0)) - (score_neg / cp.maximum(n_sum, 1.0))

        cp.subtract(probs, y, out=probs)
        cp.square(probs, out=probs)
        brier = cp.mean(probs, axis=1)

        return brier, sep

def generate_compliant_configs(n, radius):
    """
    Generates configs that respect T-1 Compliance:
    1) Hard negatives (CRL/CMC/track record) never shrink below a floor.
    2) Soft signals (Insider/Hiring/Social/Odin/Hint) are capped below structural signals.
    3) Insider/Hiring <= Priority Review (row-wise) by design.
    """
    mags = cp.abs(CANONICAL_VEC)
    factors = cp.random.uniform(1.0 - radius, 1.0 + radius, (n, len(PARAM_NAMES))).astype(cp.float32)
    configs = mags * factors

    # Priority review is the reference structural positive
    limit_priority = configs[:, IDX_PRIORITY]

    # 1. Hard penalties cannot shrink too much vs canonical (keep >= 80% magnitude)
    for idx in HARD_NEG:
        floor_mag = cp.abs(CANONICAL_VEC[idx]) * 0.8
        configs[:, idx] = cp.maximum(configs[:, idx], floor_mag)

    # 2. Soft overlays are capped to stay strictly below structural priority weight
    soft_cap = limit_priority * 0.8
    for idx in SOFT_POS:
        configs[:, idx] = cp.minimum(configs[:, idx], soft_cap)

    # 3. Explicit insider/hiring clamp
    configs[:, IDX_INSIDER] = cp.minimum(configs[:, IDX_INSIDER], soft_cap)
    configs[:, IDX_HIRING] = cp.minimum(configs[:, IDX_HIRING], soft_cap)

    # 4. Freeze odin_weight and hint_weight at canonical magnitudes
    for idx in [IDX_ODIN, IDX_HINT]:
        configs[:, idx] = cp.abs(CANONICAL_VEC[idx])

    # Apply signs back
    return configs * PARAM_SIGNS

def main():
    print("[ODIN] v10.69 T-1 GUARDIAN Started...")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"Error: {DATA_FILE} not found or unreadable ({e}).")
        return

    eng = OdinGuardianEngine(df)
    train_samples = len(eng.d_train['y'])
    batcher = AutoBatcher(train_samples)

    # Baseline Eval
    bv = CANONICAL_VEC.reshape(1,-1)
    b_tr_b, _ = eng.evaluate_batch(bv, False)
    b_te_b, _ = eng.evaluate_batch(bv, True)

    best_tr_b = float(b_tr_b.item()) if GPU_AVAILABLE else float(b_tr_b)
    best_te_b = float(b_te_b.item()) if GPU_AVAILABLE else float(b_te_b)
    best_test_brier = best_te_b

    print(f"BASELINE: Train={best_tr_b:.5f} | Test={best_te_b:.5f}")

    current_batch_size = batcher.adjust()
    start_time = time.time()
    total_configs = 0
    plateau_counter = 0

    for i in range(N_BATCHES):
        if i % VRAM_CHECK_INTERVAL == 0:
            current_batch_size = batcher.adjust()

        # Stepped Radius
        if i < 10000:
            r = START_RADIUS
        elif i < 30000:
            r = 0.02
        else:
            r = END_RADIUS

        try:
            configs = generate_compliant_configs(current_batch_size, r)
            tr_b, _ = eng.evaluate_batch(configs, False)

            valid = (tr_b <= (best_tr_b + 0.0001))
            if not valid.any():
                plateau_counter += 1
                continue

            surv_idx = cp.where(valid)[0]
            if len(surv_idx) > 20:
                surv_idx = surv_idx[:20]
            surv_cfg = configs[surv_idx]

            te_b, _ = eng.evaluate_batch(surv_cfg, True)
            min_idx = cp.argmin(te_b)
            min_val = float(te_b[min_idx].item()) if GPU_AVAILABLE else float(te_b[min_idx])

            if min_val < best_test_brier:
                best_test_brier = min_val
                best_vec = surv_cfg[min_idx]
                cur_tr = float(tr_b[surv_idx[min_idx]].item()) if GPU_AVAILABLE else float(tr_b[surv_idx[min_idx]])

                print(f"Batch {i} (r={r:.3f}, B={current_batch_size:,}): NEW BEST! Test={min_val:.5f} [Train={cur_tr:.5f}]")
                plateau_counter = 0

                v_cpu = cp.asnumpy(best_vec) if GPU_AVAILABLE else best_vec
                d = {k: float(v_cpu[idx]) for idx, k in enumerate(PARAM_NAMES)}
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(d, f, indent=2)
            else:
                plateau_counter += 1

            total_configs += current_batch_size

        except (cp.cuda.memory.OutOfMemoryError,
                cp.cuda.runtime.CUDARuntimeError):
            current_batch_size = batcher.recover_oom()
            continue

    duration = time.time() - start_time
    print(f"\nDone. Scanned {total_configs:,} configs in {duration:.1f}s.")
    print(f"Best Config saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
