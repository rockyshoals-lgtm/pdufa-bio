#!/usr/bin/env python3
"""ODIN V5 — evaluate a saved GPU-searched configuration on train/val/test splits.

Usage:
  python ODIN_EVAL_V5.py --data ODIN_PDUFA_1349_GPU_READY.csv --config ODIN_TOP_CONFIGS_V5.json
  python ODIN_EVAL_V5.py --data ODIN_PDUFA_1349_GPU_READY.npz --config ODIN_TOP_CONFIGS_V5.json

The scoring logic matches ODIN_GOD_MODE_V5_GPU_ENGINE.py (including P001 override + P003 trap).
"""

from __future__ import annotations
import argparse, json, os
import numpy as np

SPLIT_MAP = {"train_2020_2023":0, "val_2024":1, "test_2025_2026":2}

def load_npz(path: str):
    d = dict(np.load(path))
    required = ["y_true","btd","orphan","priority","fast","accel","exp","inexp","mfg",
                "pain","cns","onco","inf","stack","class1_cmc","des_trap","adcom_pct","split_code"]
    miss = [k for k in required if k not in d]
    if miss:
        raise ValueError(f"NPZ missing keys: {miss}")
    return d

def load_csv(path: str):
    import pandas as pd
    df = pd.read_csv(path)
    # split_code
    if "split_default" in df.columns:
        split_code = df["split_default"].map(SPLIT_MAP).fillna(-1).astype(np.int8).values
    else:
        split_code = np.full(len(df), -1, dtype=np.int8)

    y = df["outcome_binary"].astype(int).values if "outcome_binary" in df.columns else (
        df["outcome"].astype(str).str.upper().isin(["APPROVAL","APPROVED","1","TRUE","YES"]).astype(int).values
    )

    def gi(col, default=0):
        if col not in df.columns:
            return np.full(len(df), default, dtype=np.int32)
        return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(np.int32).values

    def gf(col, default=0.0):
        if col not in df.columns:
            return np.full(len(df), default, dtype=np.float32)
        return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(np.float32).values

    ta = df["therapeutic_area"].astype(str).str.lower() if "therapeutic_area" in df.columns else pd.Series([""]*len(df))
    pain = ta.str.contains("pain", na=False).astype(np.int32).values
    cns  = ta.str.contains("cns", na=False).astype(np.int32).values
    onco = ta.str.contains("oncol", na=False).astype(np.int32).values
    inf  = ta.str.contains("infect", na=False).astype(np.int32).values

    had_adcom = gi("had_adcom", 0)
    adcom_pct = gf("adcom_vote_pct", 0.0) / 100.0
    adcom_pct = np.where(had_adcom == 1, adcom_pct, 0.0).astype(np.float32)

    exp = (gi("experienced_sponsor", 0) > 0).astype(np.int32)
    inexp = (1 - exp).astype(np.int32)

    d = {
        "y_true": y.astype(np.int32),
        "split_code": split_code.astype(np.int8),
        "btd": gi("btd", 0),
        "orphan": gi("orphan", 0),
        "priority": gi("priority_review", 0),
        "fast": gi("fast_track", 0),
        "accel": gi("accelerated_approval", 0),
        "exp": exp,
        "inexp": inexp,
        "mfg": gi("manufacturing_risk", 0),
        "pain": pain, "cns": cns, "onco": onco, "inf": inf,
        "stack": gi("designation_stack_count", 0),
        "class1_cmc": gi("class1_cmc_resubmission_flag", 0),
        "des_trap": gi("designation_trap_flag", 0),
        "adcom_pct": adcom_pct,
    }
    return d

def score(d, params, mask=None):
    if mask is None:
        mask = np.ones_like(d["y_true"], dtype=bool)

    y = d["y_true"][mask]
    # features
    btd = d["btd"][mask]
    orphan = d["orphan"][mask]
    priority = d["priority"][mask]
    fast = d["fast"][mask]
    accel = d["accel"][mask]
    exp = d["exp"][mask]
    inexp = d["inexp"][mask]
    mfg = d["mfg"][mask]
    pain = d["pain"][mask]
    cns = d["cns"][mask]
    onco = d["onco"][mask]
    inf = d["inf"][mask]
    stack = d["stack"][mask]
    class1 = d["class1_cmc"][mask]
    des_trap = d["des_trap"][mask]
    adcom = d["adcom_pct"][mask].astype(np.float32)

    base = float(params["p_base"])
    thr = float(params["p_threshold"])

    # linear score
    score = np.full_like(adcom, base, dtype=np.float32)
    score += btd * float(params["w_btd"])
    score += orphan * float(params["w_orphan"])
    score += priority * float(params["w_priority"])
    score += fast * float(params["w_fast"])
    score += accel * float(params["w_accel"])
    score += exp * float(params["w_exp"])
    score += stack.astype(np.float32) * float(params["w_stack"])
    score += des_trap * float(params["w_des_trap"])

    eff_pen = float(params["w_mfg_pen"]) * (1.0 + (float(params["i_mfg_inexp"]) - 1.0) * inexp)
    score += mfg * eff_pen * float(params["w_mfg_amp"])

    score += pain * float(params["adj_pain"])
    score += onco * float(params["adj_onco"])
    score += inf  * float(params["adj_inf"])

    cns_adj = float(params["adj_cns"]) + float(params["adj_cns_amp"]) * inexp
    score += cns * cns_adj

    score += adcom * float(params["w_adcom"])

    # clamp
    prob = np.clip(score, 0.01, 0.99)

    # P001 override
    prob = np.where(class1 == 1, 0.995, prob).astype(np.float32)

    pred = (prob >= thr).astype(np.int32)

    brier = float(np.mean((prob - y)**2))
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))

    precision = tp / (tp + fp + 1e-9)
    specificity = tn / (tn + fp + 1e-9)

    return {
        "N": int(y.shape[0]),
        "brier": brier,
        "precision": float(precision),
        "specificity": float(specificity),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "thr": thr
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", required=True, help="JSON output from GPU search (top list) or a single config json.")
    ap.add_argument("--index", type=int, default=0, help="Which config to evaluate if JSON is a list (default 0 = best).")

    args = ap.parse_args()

    if args.data.lower().endswith(".npz"):
        d = load_npz(args.data)
    else:
        d = load_csv(args.data)

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if isinstance(cfg, list):
        cfg = cfg[args.index]
    params = cfg.get("params", cfg)

    split_code = d.get("split_code", np.full_like(d["y_true"], -1, dtype=np.int8))

    for name, code in [("TRAIN",0), ("VAL",1), ("TEST",2), ("ALL",None)]:
        mask = np.ones_like(split_code, dtype=bool) if code is None else (split_code == code)
        res = score(d, params, mask=mask)
        print(f"{name:5s} | N={res['N']:4d} | brier={res['brier']:.5f} | prec={res['precision']:.3f} | spec={res['specificity']:.3f} | FP={res['fp']:3d} FN={res['fn']:3d} | thr={res['thr']:.3f}")

if __name__ == "__main__":
    main()
