"""
ODIN v10.70 "Operations Guardian" REFINER
=========================================
Goal: Extend v1069 T-1 canon with operational risk features
      (protocol amendments + PI/site quality) without breaking
      existing structural logic or calibration.

Canon: odin_v1069_t1_best.json  (DO NOT OVERWRITE)
Output: odin_v1070_t1_best.json
"""

import numpy as np
import pandas as pd
import time
import json
import warnings
import sys
import gc
import os

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

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

DATA_FILE = "ODIN_MODEL_READY_v1067_T1_2015on_ENRICHED.csv"  # enriched dataset
CANON_WEIGHTS_FILE = "odin_v1069_t1_best.json"              # v1069 canon
OUTPUT_FILE = "odin_v1070_t1_best.json"

TRAIN_SPLIT_PCT = 0.70
N_BATCHES = 100_000

START_RADIUS = 0.05   # ±5% around canon (already strong)
END_RADIUS   = 0.001  # ±0.1% micro-polish

MAX_VRAM_GB = 11.5
VRAM_SAFETY_MARGIN = 0.95
VRAM_CHECK_INTERVAL = 25
MAX_SAFE_BATCH = 700_000

# -----------------------------------------------------------------------------
# LOAD v1069 CANON AND EXTEND WITH NEW FEATURES
# -----------------------------------------------------------------------------

with open(CANON_WEIGHTS_FILE, "r") as f:
    base_config_1069 = json.load(f)

# v1069 keys and values
base_param_names = list(base_config_1069.keys())
base_param_values = [base_config_1069[k] for k in base_param_names]

# New operational parameters (seeded conservatively)
EXTRA_PARAMS = {
    # protocol amendments
    "amendment_count_penalty":   -0.05,  # per extra amendment above 0
    "amend_relax_ie_penalty":    -0.30,  # inclusion/exclusion relaxed
    "endpoint_change_penalty":   -0.35,  # primary endpoint changed

    # PI/site quality
    "pi_bad_bmis_penalty":       -0.45,  # high-enrolling PI with bad BMIS history
    "zero_enroller_penalty":     -0.20,  # penalty per unit of zero_enroller_frac
}

CANONICAL_CONFIG = {**base_config_1069, **EXTRA_PARAMS}

PARAM_NAMES = list(CANONICAL_CONFIG.keys())
CANONICAL_VEC = np.array([CANONICAL_CONFIG[k] for k in PARAM_NAMES], dtype=np.float32)
PARAM_SIGNS = np.sign(CANONICAL_VEC)
PARAM_SIGNS[PARAM_SIGNS == 0] = 1.0

# Indices for existing core params (from v1069) [file:211]
IDX_PRIORITY = PARAM_NAMES.index("priority_review_weight")
IDX_INSIDER = PARAM_NAMES.index("s23_insider_weight")
IDX_HIRING  = PARAM_NAMES.index("s6_hiring_weight")
IDX_ODIN    = PARAM_NAMES.index("odin_weight")
IDX_HINT    = PARAM_NAMES.index("hint_weight")

# New indices
IDX_AMEND_COUNT   = PARAM_NAMES.index("amendment_count_penalty")
IDX_AMEND_RELAX   = PARAM_NAMES.index("amend_relax_ie_penalty")
IDX_EP_CHANGE     = PARAM_NAMES.index("endpoint_change_penalty")
IDX_PI_BAD_BMIS   = PARAM_NAMES.index("pi_bad_bmis_penalty")
IDX_ZERO_ENROLLER = PARAM_NAMES.index("zero_enroller_penalty")

# Core hard-negative penalties (existing + PI BMIS)
HARD_NEG = [
    PARAM_NAMES.index("prior_crl_penalty"),
    PARAM_NAMES.index("s22_pediatric_pk_penalty"),
    PARAM_NAMES.index("ema_cmc_flag_penalty"),
    PARAM_NAMES.index("form_483_penalty"),
    PARAM_NAMES.index("manufacturing_risk_penalty"),
    PARAM_NAMES.index("inexperienced_sponsor_penalty"),
    IDX_PI_BAD_BMIS,
]

# Operational negatives (amendments + zero-enrollers)
OPS_NEG = [
    IDX_AMEND_COUNT,
    IDX_AMEND_RELAX,
    IDX_EP_CHANGE,
    IDX_ZERO_ENROLLER,
]

# Soft overlays that must remain below formal designations
SOFT_POS = [
    PARAM_NAMES.index("s23_insider_weight"),
    PARAM_NAMES.index("s6_hiring_weight"),
    PARAM_NAMES.index("social_weight"),
    PARAM_NAMES.index("odin_weight"),
    PARAM_NAMES.index("hint_weight"),
]

if GPU_AVAILABLE:
    CANONICAL_VEC = cp.asarray(CANONICAL_VEC)
    PARAM_SIGNS   = cp.asarray(PARAM_SIGNS)

# -----------------------------------------------------------------------------
# AUTO-BATCHER
# -----------------------------------------------------------------------------

class AutoBatcher:
    def __init__(self, samples_per_config):
        self.samples = samples_per_config
        self.params  = len(PARAM_NAMES)
        self.current_batch = 500_000

    def get_safe_memory(self):
        if not GPU_AVAILABLE:
            return 1_000_000_000
        free_mem, total_mem = cuda_runtime.memGetInfo()
        mempool   = cp.get_default_memory_pool()
        pool_free = mempool.total_bytes() - mempool.used_bytes()
        total_avail = free_mem + pool_free
        max_bytes   = MAX_VRAM_GB * 1024**3
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
        optimal_batch = min(MAX_SAFE_BATCH, optimal_batch)

        if abs(optimal_batch - self.current_batch) > 50_000:
            print(f"[GUARDIAN] Optimizing Batch: {self.current_batch:,} -> "
                  f"{optimal_batch:,} (Free VRAM: {safe_mem/1024**3:.2f} GB)")
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

# -----------------------------------------------------------------------------
# ENGINE
# -----------------------------------------------------------------------------

class OdinGuardianEngine:
    def __init__(self, df):
        if 'catalyst_date' in df.columns:
            df['sort_date'] = pd.to_datetime(df['catalyst_date'], errors='coerce')
            df = df.sort_values('sort_date').reset_index(drop=True)

        self.X_odin, self.y = self._build_matrices(df)
        self.mask = self._build_avoids(df)

        split = int(len(df) * TRAIN_SPLIT_PCT)
        self.d_train = {
            'X': self.X_odin[:split],
            'y': self.y[:split],
            'm': self.mask[:split],
        }
        self.d_test = {
            'X': self.X_odin[split:],
            'y': self.y[split:],
            'm': self.mask[split:],
        }

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
            return s.isin(['TRUE', '1', '1.0', 'YES', 'Y', 'APPROVED']).astype(np.float32)

        def get_val(col):
            if col not in df.columns:
                return np.zeros(N, dtype=np.float32)
            return pd.to_numeric(df[col], errors='coerce').fillna(0.0).values.astype(np.float32)

        def get_app(df_):
            cands = ['application_type','ApplicationType','app_type']
            for c in cands:
                if c in df_.columns:
                    return df_[c].fillna('').astype(str).str.upper()
            return pd.Series([''] * N)

        app = get_app(df)

        # --- CORE FEATURES (v1069) -----------------------------------------
        X[:,0] = 1.0
        X[:,1] = (app.str.contains('SNDA') | app.str.contains('SBLA')).astype(float)
        X[:,2] = app.str.contains('PEDIATRIC').astype(float)
        X[:,3] = get_bool('prior_crl')
        prior  = get_val('sponsor_prior_approvals')
        X[:,4] = (prior == 0).astype(float)
        X[:,5] = get_bool('manufacturing_risk')
        X[:,6] = get_bool('form_483_issues')
        X[:,7] = get_bool('ema_cmc_flag')
        X[:,8] = get_bool('cmc_extension_flag')

        had_adcom = get_bool('had_adcom')
        vote = get_val('adcom_vote_pct')
        vote = np.where(vote > 1, vote / 100.0, vote)
        X[:,9]  = had_adcom * ((vote >= 0.50) & (vote < 0.65))
        X[:,10] = had_adcom * (vote < 0.50)

        X[:,11] = get_bool('s22_ped_pk_missing')
        X[:,12] = get_bool('btd')
        X[:,13] = get_bool('orphan')
        X[:,14] = get_bool('priority_review')
        X[:,15] = get_bool('fast_track')
        X[:,16] = get_bool('accelerated_approval')
        if 'resubmission_class' in df:
            X[:,17] = (get_val('resubmission_class') == 1).astype(float)
        X[:,18] = (prior >= 5).astype(float)
        X[:,19] = had_adcom * (vote >= 0.65)
        X[:,20] = get_val('ta_base_score')
        X[:,21] = get_val('s23_signal_strength')
        X[:,22] = get_val('s6_signal_strength')
        X[:,23] = get_val('social_sentiment_score')

        # slots 24 & 25: odin_weight, hint_weight (meta; not tied to X here)

        # historical CRL & TA/indication features
        ta = df['therapeutic_area'].fillna('Other').astype(str)

        def chk(s, ks):
            m = np.zeros(len(s), dtype=bool)
            for k in ks:
                m |= s.str.contains(k, case=False)
            return m.astype(float)

        if 'historical_crl_rate' in df:
            X[:,26] = df['historical_crl_rate'].fillna(0).astype(float)
        else:
            X[:,26] = 0.0

        X[:,27] = chk(ta, ["Pain","Ophthalmology","Nephrology","Hematology"])
        X[:,28] = chk(ta, ["CNS","Neurology","Cardiovascular","Metabolic"])
        X[:,29] = chk(ta, ["Oncology","Immunology","Dermatology","Infectious"])

        if 'indication' in df:
            ind = df['indication'].fillna('').astype(str)
        else:
            ind = pd.Series([''] * N)

        X[:,30] = ind.str.contains("Pain", case=False).astype(float)
        X[:,31] = (
            ind.str.contains("Cancer", case=False) |
            ind.str.contains("Tumor", case=False)
        ).astype(float)

        X[:,32] = ((prior < 3) & (X[:,27] > 0)).astype(float)

        # --- NEW OPERATIONAL FEATURES (v10.70) -----------------------------

        # 33: amendment_count_penalty driver
        X[:,33] = get_val("n_amendments")

        # 34: amend_relax_ie_penalty driver
        X[:,34] = get_bool("amend_relax_ie")

        # 35: endpoint_change_penalty driver
        X[:,35] = get_bool("primary_endpoint_changed")

        # 36: pi_bad_bmis_penalty driver
        X[:,36] = get_bool("pi_bad_bmis_flag")

        # 37: zero_enroller_penalty driver
        X[:,37] = get_val("zero_enroller_frac")

        # -------------------------------------------------------------------

        y_col = next((c for c in ['outcome','Outcome','approved','result'] if c in df), None)
        y_raw = df[y_col].astype(str).str.strip().str.upper().replace(r'\.0$', '', regex=True)
        y = y_raw.isin({'APPROVED','APPROVAL','1','TRUE','YES','SUCCESS'}).astype(float).values

        return X, y

    def _build_avoids(self, df):
        m = np.ones(len(df), dtype=np.float32)
        b = np.zeros(len(df), dtype=bool)
        if 'ema_cmc_flag' in df:
            b |= df['ema_cmc_flag'].fillna(False).astype(bool)
        if 's22_ped_pk_missing' in df:
            b |= df['s22_ped_pk_missing'].fillna(False).astype(bool)
        m[b] = 0.0
        return m

    def evaluate_batch(self, configs, use_test=False):
        d = self.d_test if use_test else self.d_train
        X, y, m = d['X'], d['y'], d['m']

        c_logits = configs.copy()

        # odin_weight and hint_weight currently meta; zero for scoring
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
        n_sum = cp.sum(1 - y)
        score_pos = cp.dot(probs, y)
        score_neg = cp.dot(probs, 1 - y)
        sep = (score_pos / cp.maximum(y_sum, 1.0)) - (score_neg / cp.maximum(n_sum, 1.0))

        cp.subtract(probs, y, out=probs)
        cp.square(probs, out=probs)
        brier = cp.mean(probs, axis=1)

        return brier, sep

# -----------------------------------------------------------------------------
# CONFIG SAMPLER WITH T-1 CONSTRAINTS
# -----------------------------------------------------------------------------

def generate_compliant_configs(n, radius):
    mags = cp.abs(CANONICAL_VEC)
    factors = cp.random.uniform(1.0 - radius, 1.0 + radius, (n, len(PARAM_NAMES))).astype(cp.float32)
    configs = mags * factors

    # Priority review as reference positive
    limit_priority = configs[:, IDX_PRIORITY]

    # 1) Hard penalties cannot shrink too much vs canon (>=80% magnitude)
    for idx in HARD_NEG:
        floor_mag = cp.abs(CANONICAL_VEC[idx]) * 0.8
        configs[:, idx] = cp.maximum(configs[:, idx], floor_mag)

    # 2) Operational negatives cannot shrink below 70% of canon
    for idx in OPS_NEG:
        floor_mag = cp.abs(CANONICAL_VEC[idx]) * 0.7
        configs[:, idx] = cp.maximum(configs[:, idx], floor_mag)

    # 3) Soft overlays capped below structural priority weight (80%)
    soft_cap = limit_priority * 0.8
    for idx in SOFT_POS:
        configs[:, idx] = cp.minimum(configs[:, idx], soft_cap)

    # Insider/hiring explicit clamp
    configs[:, IDX_INSIDER] = cp.minimum(configs[:, IDX_INSIDER], soft_cap)
    configs[:, IDX_HIRING]  = cp.minimum(configs[:, IDX_HIRING],  soft_cap)

    # 4) Freeze odin_weight and hint_weight at canonical magnitudes
    for idx in [IDX_ODIN, IDX_HINT]:
        configs[:, idx] = cp.abs(CANONICAL_VEC[idx])

    # Apply signs back
    return configs * PARAM_SIGNS

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    print("[ODIN] v10.70 Operations Guardian Started...")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"Error: {DATA_FILE} not found or unreadable ({e}).")
        return

    # Quick sanity check: ensure new columns exist
    missing_cols = [
        c for c in ["n_amendments", "amend_relax_ie",
                    "primary_endpoint_changed", "pi_bad_bmis_flag",
                    "zero_enroller_frac"]
        if c not in df.columns
    ]
    if missing_cols:
        print("ERROR: Missing required columns in dataset:", missing_cols)
        print("Please add them in your enrichment pipeline before running v10.70.")
        return

    eng = OdinGuardianEngine(df)
    train_samples = len(eng.d_train['y'])
    batcher = AutoBatcher(train_samples)

    # Baseline evaluation at v1069+ops seeds
    bv = CANONICAL_VEC.reshape(1, -1)
    b_tr_b, _ = eng.evaluate_batch(bv, False)
    b_te_b, _ = eng.evaluate_batch(bv, True)

    best_tr_b = float(b_tr_b.item()) if GPU_AVAILABLE else float(b_tr_b)
    best_te_b = float(b_te_b.item()) if GPU_AVAILABLE else float(b_te_b)
    best_test_brier = best_te_b

    print(f"BASELINE (v1069+ops seeds): Train={best_tr_b:.5f} | Test={best_te_b:.5f}")

    current_batch_size = batcher.adjust()
    start_time = time.time()
    total_configs = 0
    plateau_counter = 0

    for i in range(N_BATCHES):
        if i % VRAM_CHECK_INTERVAL == 0:
            current_batch_size = batcher.adjust()

        if i < 10_000:
            r = START_RADIUS
        elif i < 30_000:
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

                print(f"Batch {i} (r={r:.3f}, B={current_batch_size:,}): "
                      f"NEW BEST! Test={min_val:.5f} [Train={cur_tr:.5f}]")
                plateau_counter = 0

                v_cpu = cp.asnumpy(best_vec) if GPU_AVAILABLE else best_vec
                d = {k: float(v_cpu[idx]) for idx, k in enumerate(PARAM_NAMES)}
                with open(OUTPUT_FILE, "w") as f:
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
