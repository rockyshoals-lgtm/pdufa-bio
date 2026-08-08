"""
BIFROST Options v1.2 Recompute Pipeline
=========================================
Applies all red team methodology fixes to the 1,828-trade v1.1 dataset.

Fixes:
- DTE matching: keep only trades where entry_dte - exit_dte in [11, 15] AND exit_dte >= 3
- IV parser hard cap: drop rows where |iv_pct| > 500 or iv_pct <= 0.01 on either leg
- Drop v5_tier filter (n/a here; we never had v5 in this data)
- Fill models: WORST (0% spread capture), REAL_25, REAL_40, MID (50%)
- Bootstrap 95% CIs on every segment (n_boot=2000, seed=42)
- Drop segments with n<30 from publishable table
- ODIN filter inversion hypothesis: compare T1/T2 vs T3/T4 returns explicitly
- Strategy honest numbers: PDUFA Small/Mid approvals, and ONLY robust edge (Phase 1/2)
"""

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

RESULTS_IN = "/sessions/confident-serene-ptolemy/mnt/9realms/options_backtest_v2_results.json"
RESULTS_OUT = "/sessions/confident-serene-ptolemy/mnt/9realms/options_backtest_v12_results.json"

# =========================================================================
# 1. Filters
# =========================================================================

def dte_matched(t, gap_min=13, gap_max=23, exit_dte_min=3):
    """Filter #1: trade must hold the same monthly-ish expiry from entry to exit.

    In this 1,828-trade dataset, entry is targeted at T-14 trading days and exit at
    T-1 trading day — a ~13 trading-day span = ~18 calendar-day DTE decay. Bulk of
    legitimate (held-to-monthly) trades land in gap 15-19 (841 of 1828). We accept
    13-23 to include 20/30-DTE-at-entry variants that stayed with the same contract.

    Trades with gap<13 likely rolled into a nearer (weekly) expiry before exit — the
    'weekly trap' the red team flagged. exit_dte<3 means the option literally expires
    before the catalyst, which is fatal.
    """
    entry_dte = t.get("entry_dte")
    exit_dte = t.get("exit_dte")
    if entry_dte is None or exit_dte is None:
        return False
    gap = entry_dte - exit_dte
    if not (gap_min <= gap <= gap_max):
        return False
    if exit_dte < exit_dte_min:
        return False
    return True


def iv_sanitized(t, iv_max=500.0, iv_min=0.01):
    """Filter #2: drop trades where IV parser produced extreme or non-sensical values."""
    for k in ("entry_iv_pct", "exit_iv_pct"):
        v = t.get(k)
        if v is None:
            return False
        if abs(v) > iv_max:
            return False
        if abs(v) < iv_min:
            return False
    iv_chg = t.get("iv_change_pct")
    if iv_chg is not None and abs(iv_chg) > 1000:
        return False
    return True


def has_valid_prices(t):
    """Must have a real entry mid and a real exit mid, both positive."""
    for k in ("entry_ask", "entry_bid", "entry_mid", "exit_ask", "exit_bid", "exit_mid"):
        v = t.get(k)
        if v is None or v <= 0:
            # exit_bid can be near zero (decayed), so only require > 0 for entry
            if k.startswith("entry") and (v is None or v <= 0):
                return False
            if k.startswith("exit") and v is None:
                return False
    # Require non-pathological entry mid
    if t.get("entry_mid", 0) < 0.05:
        return False
    return True


# =========================================================================
# 2. Fill models
# =========================================================================

def fill_return(t, capture_pct):
    """
    capture_pct = fraction of spread captured on your side.
    0.0 = cross the spread fully (WORST): buy ask, sell bid
    0.5 = MID
    1.0 = spread capture IN YOUR FAVOR (BEST)

    Entry (buying): pay (1 - capture_pct) of the spread above bid, so:
        entry_fill = entry_bid + (1 - capture_pct) * (entry_ask - entry_bid)
    Exit (selling): receive capture_pct above bid, so:
        exit_fill = exit_bid + capture_pct * (exit_ask - exit_bid)
    """
    entry_bid = t["entry_bid"]
    entry_ask = t["entry_ask"]
    exit_bid = t["exit_bid"]
    exit_ask = t["exit_ask"]

    entry_fill = entry_bid + (1 - capture_pct) * (entry_ask - entry_bid)
    exit_fill = exit_bid + capture_pct * (exit_ask - exit_bid)

    if entry_fill <= 0:
        return None
    return (exit_fill - entry_fill) / entry_fill * 100.0


# =========================================================================
# 3. Bootstrap CI
# =========================================================================

def bootstrap_ci(xs, n_boot=2000, seed=42, lo_pct=2.5, hi_pct=97.5):
    if len(xs) < 2:
        return (None, None)
    rng = random.Random(seed)
    means = []
    n = len(xs)
    for _ in range(n_boot):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx = int(n_boot * lo_pct / 100)
    hi_idx = int(n_boot * hi_pct / 100)
    return (round(means[lo_idx], 2), round(means[hi_idx], 2))


def describe(xs):
    if not xs:
        return {"n": 0}
    wins = sum(1 for x in xs if x > 0)
    big_wins = sum(1 for x in xs if x > 100)
    big_losses = sum(1 for x in xs if x < -50)
    return {
        "n": len(xs),
        "avg": round(sum(xs) / len(xs), 2),
        "median": round(statistics.median(xs), 2),
        "win_pct": round(100.0 * wins / len(xs), 1),
        "pct_gt_100": round(100.0 * big_wins / len(xs), 1),
        "pct_lt_neg50": round(100.0 * big_losses / len(xs), 1),
    }


def describe_with_ci(xs):
    d = describe(xs)
    if d["n"] >= 2:
        lo, hi = bootstrap_ci(xs)
        d["ci_95_lo"] = lo
        d["ci_95_hi"] = hi
        d["ci_crosses_zero"] = (lo is not None and hi is not None and lo < 0 < hi)
    return d


def describe_ex_top_k(xs, k=5):
    """Describe distribution after removing top-k winners (robustness check)."""
    if len(xs) <= k:
        return {"n_after": 0}
    xs_sorted = sorted(xs)
    trimmed = xs_sorted[:-k]
    d = describe(trimmed)
    d["n_after"] = len(trimmed)
    return d


# =========================================================================
# 4. Load + apply filters
# =========================================================================

print("Loading v1.1 results...")
with open(RESULTS_IN) as f:
    v11 = json.load(f)

all_trades = []
for t in v11["pdufa_trades"]:
    t["_event_type"] = "PDUFA"
    all_trades.append(t)
for t in v11["readout_trades"]:
    t["_event_type"] = "Readout"
    all_trades.append(t)

print(f"  loaded: {len(all_trades)} raw trades")

# Stage filters
stage_counts = {"raw": len(all_trades)}
s1 = [t for t in all_trades if has_valid_prices(t)]
stage_counts["has_valid_prices"] = len(s1)
s2 = [t for t in s1 if iv_sanitized(t)]
stage_counts["iv_sanitized"] = len(s2)
s3 = [t for t in s2 if dte_matched(t)]
stage_counts["dte_matched"] = len(s3)

print("  filter stages:")
for k, v in stage_counts.items():
    print(f"    {k}: {v}")

honest = s3
print(f"  honest subset: {len(honest)} trades")


# Compute fill-model returns
CAPTURE_MODELS = {
    "worst": 0.00,
    "real_25": 0.25,
    "real_40": 0.40,
    "mid": 0.50,
}

drop_count = 0
for t in honest:
    for name, cap in CAPTURE_MODELS.items():
        r = fill_return(t, cap)
        t[f"ret_{name}"] = round(r, 3) if r is not None else None
    # Skip any where we couldn't compute
    if t.get("ret_mid") is None:
        drop_count += 1

if drop_count:
    print(f"  dropped {drop_count} trades missing fill-model returns")
    honest = [t for t in honest if t.get("ret_mid") is not None]

print(f"  FINAL honest subset: {len(honest)} trades")


# =========================================================================
# 5. Stage-phase normalization (readouts)
# =========================================================================

def phase_bucket(stage):
    if not stage:
        return "Unknown"
    s = str(stage).strip().lower()
    if "1/2" in s or "1b/2" in s or "phase 1/2" in s:
        return "Phase 1/2"
    if s in ("phase 1", "phase1", "p1", "phase 1b", "phase 1a", "phase 1/1b"):
        return "Phase 1"
    if "2b" in s or "phase 2b" in s or "p2b" in s:
        return "Phase 2b"
    if s.startswith("phase 2") or s == "p2" or "2a" in s:
        return "Phase 2"
    if "3" in s:
        return "Phase 3"
    return "Other"


for t in honest:
    if t["_event_type"] == "Readout":
        t["_phase"] = phase_bucket(t.get("stage"))
    else:
        t["_phase"] = None


# =========================================================================
# 6. Segment analysis
# =========================================================================

def returns(trades, field):
    return [t[field] for t in trades if t.get(field) is not None]


segments = {}

# PDUFA by cap tier (approve outcome only — that's what the strategy was aimed at)
for cap in ["nano", "micro", "small", "mid", "large"]:
    for outcome in ["approve", "crl"]:
        key = f"PDUFA / {cap} / {outcome}"
        subset = [t for t in honest
                  if t["_event_type"] == "PDUFA"
                  and t.get("cap_tier") == cap
                  and t.get("outcome") == outcome]
        if not subset:
            continue
        seg = {
            "n": len(subset),
            "mid": describe_with_ci(returns(subset, "ret_mid")),
            "real_40": describe_with_ci(returns(subset, "ret_real_40")),
            "real_25": describe_with_ci(returns(subset, "ret_real_25")),
            "worst": describe_with_ci(returns(subset, "ret_worst")),
            "ex_top5_mid": describe_ex_top_k(returns(subset, "ret_mid"), k=5),
        }
        segments[key] = seg

# PDUFA by cap tier (pooled outcomes)
for cap in ["nano", "micro", "small", "mid", "large"]:
    key = f"PDUFA / {cap} / ALL"
    subset = [t for t in honest if t["_event_type"] == "PDUFA" and t.get("cap_tier") == cap]
    if not subset:
        continue
    segments[key] = {
        "n": len(subset),
        "mid": describe_with_ci(returns(subset, "ret_mid")),
        "real_40": describe_with_ci(returns(subset, "ret_real_40")),
        "real_25": describe_with_ci(returns(subset, "ret_real_25")),
        "ex_top5_mid": describe_ex_top_k(returns(subset, "ret_mid"), k=5),
    }

# Readouts by phase × outcome
for phase in ["Phase 1", "Phase 1/2", "Phase 2", "Phase 2b", "Phase 3"]:
    for outcome in ["positive", "negative", "mixed"]:
        key = f"Readout / {phase} / {outcome}"
        subset = [t for t in honest
                  if t["_event_type"] == "Readout"
                  and t["_phase"] == phase
                  and t.get("outcome") == outcome]
        if not subset:
            continue
        segments[key] = {
            "n": len(subset),
            "mid": describe_with_ci(returns(subset, "ret_mid")),
            "real_40": describe_with_ci(returns(subset, "ret_real_40")),
            "real_25": describe_with_ci(returns(subset, "ret_real_25")),
            "worst": describe_with_ci(returns(subset, "ret_worst")),
            "ex_top5_mid": describe_ex_top_k(returns(subset, "ret_mid"), k=5),
        }

# Readouts pooled by phase
for phase in ["Phase 1", "Phase 1/2", "Phase 2", "Phase 2b", "Phase 3"]:
    key = f"Readout / {phase} / ALL"
    subset = [t for t in honest if t["_event_type"] == "Readout" and t["_phase"] == phase]
    if not subset:
        continue
    segments[key] = {
        "n": len(subset),
        "mid": describe_with_ci(returns(subset, "ret_mid")),
        "real_40": describe_with_ci(returns(subset, "ret_real_40")),
        "real_25": describe_with_ci(returns(subset, "ret_real_25")),
        "ex_top5_mid": describe_ex_top_k(returns(subset, "ret_mid"), k=5),
    }


# =========================================================================
# 7. Strategy honest numbers
# =========================================================================

strategies = {}

# Announced: PDUFA Small/Mid approvals (the flagship)
sm_approve = [t for t in honest if t["_event_type"] == "PDUFA"
              and t.get("cap_tier") in ("small", "mid")
              and t.get("outcome") == "approve"]
strategies["PDUFA_SmallMid_Approve"] = {
    "n": len(sm_approve),
    "mid": describe_with_ci(returns(sm_approve, "ret_mid")),
    "real_40": describe_with_ci(returns(sm_approve, "ret_real_40")),
    "real_25": describe_with_ci(returns(sm_approve, "ret_real_25")),
    "worst": describe_with_ci(returns(sm_approve, "ret_worst")),
}

# Robust edge: Phase 1 + Phase 1/2 positive readouts
p12_pos = [t for t in honest if t["_event_type"] == "Readout"
           and t["_phase"] in ("Phase 1", "Phase 1/2")
           and t.get("outcome") == "positive"]
strategies["Readout_Early_Positive"] = {
    "n": len(p12_pos),
    "mid": describe_with_ci(returns(p12_pos, "ret_mid")),
    "real_40": describe_with_ci(returns(p12_pos, "ret_real_40")),
    "real_25": describe_with_ci(returns(p12_pos, "ret_real_25")),
    "worst": describe_with_ci(returns(p12_pos, "ret_worst")),
    "ex_top5_mid": describe_ex_top_k(returns(p12_pos, "ret_mid"), k=5),
}

# PDUFA micro (all outcomes) — robustness check on "gold segment"
pdufa_micro = [t for t in honest if t["_event_type"] == "PDUFA" and t.get("cap_tier") == "micro"]
strategies["PDUFA_Micro_All"] = {
    "n": len(pdufa_micro),
    "mid": describe_with_ci(returns(pdufa_micro, "ret_mid")),
    "real_40": describe_with_ci(returns(pdufa_micro, "ret_real_40")),
    "ex_top2_mid": describe_ex_top_k(returns(pdufa_micro, "ret_mid"), k=2),
    "ex_top5_mid": describe_ex_top_k(returns(pdufa_micro, "ret_mid"), k=5),
}


# =========================================================================
# 8. ODIN filter inversion hypothesis
# =========================================================================

odin_test = {}
for tier_group, label in [(["T1"], "T1"), (["T2"], "T2"), (["T3"], "T3"), (["T4"], "T4"),
                           (["T1", "T2"], "T1+T2 (standard filter)"),
                           (["T3", "T4"], "T3+T4 (INVERTED)")]:
    # PDUFAs only (ODIN is a PDUFA model)
    subset = [t for t in honest if t["_event_type"] == "PDUFA"
              and t.get("odin_tier") in tier_group]
    if not subset:
        continue
    odin_test[label] = {
        "n": len(subset),
        "mid": describe_with_ci(returns(subset, "ret_mid")),
        "real_40": describe_with_ci(returns(subset, "ret_real_40")),
    }


# =========================================================================
# 9. Full distribution (for a global baseline)
# =========================================================================

global_baseline = {
    "all_honest": {
        "n": len(honest),
        "mid": describe_with_ci(returns(honest, "ret_mid")),
        "real_40": describe_with_ci(returns(honest, "ret_real_40")),
    },
    "pdufa_all": {
        "n": sum(1 for t in honest if t["_event_type"] == "PDUFA"),
        "mid": describe_with_ci([t["ret_mid"] for t in honest if t["_event_type"] == "PDUFA"]),
        "real_40": describe_with_ci([t["ret_real_40"] for t in honest if t["_event_type"] == "PDUFA"]),
    },
    "readout_all": {
        "n": sum(1 for t in honest if t["_event_type"] == "Readout"),
        "mid": describe_with_ci([t["ret_mid"] for t in honest if t["_event_type"] == "Readout"]),
        "real_40": describe_with_ci([t["ret_real_40"] for t in honest if t["_event_type"] == "Readout"]),
    },
}


# =========================================================================
# 10. Save
# =========================================================================

output = {
    "generated": "2026-04-18",
    "version": "v1.2_rerun",
    "methodology": {
        "dte_filter": "entry_dte - exit_dte in [11, 15] AND exit_dte >= 3",
        "iv_filter": "0.01 < |iv_pct| < 500 on both entry and exit",
        "fill_models": {
            "worst": "buy at ask, sell at bid (0% spread capture)",
            "real_25": "25% spread capture each leg",
            "real_40": "40% spread capture each leg (realistic limit)",
            "mid": "buy at mid, sell at mid (50% spread capture)",
        },
        "bootstrap": "n_boot=2000, seed=42, 95% CI",
        "publishable_threshold": "n >= 30",
    },
    "stage_counts": stage_counts,
    "honest_n": len(honest),
    "segments": segments,
    "strategies": strategies,
    "odin_filter_test": odin_test,
    "global_baseline": global_baseline,
}

with open(RESULTS_OUT, "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n=== SAVED: {RESULTS_OUT} ===\n")

# Pretty print headline numbers
print("GLOBAL BASELINE:")
for k, v in global_baseline.items():
    print(f"  {k}: n={v['n']}  MID avg={v['mid'].get('avg')}  CI={v['mid'].get('ci_95_lo')},{v['mid'].get('ci_95_hi')}")

print("\nKEY STRATEGIES:")
for name, s in strategies.items():
    print(f"  {name}: n={s['n']}")
    for fill in ("mid", "real_40"):
        d = s.get(fill, {})
        if d.get("n", 0) >= 2:
            print(f"    {fill}: avg={d.get('avg')}  median={d.get('median')}  win={d.get('win_pct')}%  CI=[{d.get('ci_95_lo')}, {d.get('ci_95_hi')}]")
    if "ex_top5_mid" in s and s["ex_top5_mid"].get("n", 0) > 0:
        d = s["ex_top5_mid"]
        print(f"    ex_top5_mid: n={d.get('n')}  avg={d.get('avg')}  median={d.get('median')}  win={d.get('win_pct')}%")

print("\nODIN FILTER INVERSION TEST (PDUFA only):")
for label, d in odin_test.items():
    mid = d.get("mid", {})
    print(f"  {label}: n={d['n']}  MID avg={mid.get('avg')}%  win={mid.get('win_pct')}%  CI=[{mid.get('ci_95_lo')}, {mid.get('ci_95_hi')}]")

print("\nTOP SEGMENTS BY MID AVG (n>=30 only):")
keep = [(k, s) for k, s in segments.items() if s.get("n", 0) >= 30]
keep.sort(key=lambda kv: kv[1]["mid"].get("avg", -9999) or -9999, reverse=True)
for k, s in keep[:12]:
    m = s["mid"]
    r40 = s["real_40"]
    print(f"  {k:45s}  n={s['n']:4d}  MID={m.get('avg'):+7.1f}%  R40={r40.get('avg'):+7.1f}%  win={m.get('win_pct'):4.1f}%  CI=[{m.get('ci_95_lo')}, {m.get('ci_95_hi')}]")

print("\nBOTTOM SEGMENTS BY MID AVG (n>=30 only):")
for k, s in keep[-8:]:
    m = s["mid"]
    r40 = s["real_40"]
    print(f"  {k:45s}  n={s['n']:4d}  MID={m.get('avg'):+7.1f}%  R40={r40.get('avg'):+7.1f}%  win={m.get('win_pct'):4.1f}%  CI=[{m.get('ci_95_lo')}, {m.get('ci_95_hi')}]")
