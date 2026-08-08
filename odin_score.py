from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

@dataclass
class Metrics:
    brier: float
    precision: float
    recall: float
    f1: float
    specificity: float
    mcc: float
    tp: int
    fp: int
    tn: int
    fn: int

def safe_div(a, b) -> float:
    return float(a) / float(b) if b else 0.0

def compute_metrics(y: np.ndarray, p: np.ndarray, thr: float) -> Metrics:
    yhat = (p >= thr).astype(np.int8)
    tp = int(np.sum((yhat == 1) & (y == 1)))
    fp = int(np.sum((yhat == 1) & (y == 0)))
    tn = int(np.sum((yhat == 0) & (y == 0)))
    fn = int(np.sum((yhat == 0) & (y == 1)))

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    specificity = safe_div(tn, tn + fp)

    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) if (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn) else 0.0
    mcc = ((tp * tn) - (fp * fn)) / denom if denom else 0.0

    brier = float(np.mean((p - y) ** 2))
    return Metrics(brier=brier, precision=precision, recall=recall, f1=f1, specificity=specificity, mcc=mcc,
                   tp=tp, fp=fp, tn=tn, fn=fn)

def score_probs(df: pd.DataFrame, cols, params: Dict[str, float]) -> np.ndarray:
    """
    Vectorized probabilistic scorer aligned to your top-config fields.

    If you have an exact equation already, replace THIS function only.
    """
    n = len(df)
    p = np.full(n, float(params["p_base"]), dtype=np.float32)

    def colv(name: Optional[str], default=0.0):
        if name is None:
            return np.full(n, default, dtype=np.float32)
        return df[name].fillna(default).astype(np.float32).to_numpy()

    # designations
    p += float(params.get("w_btd", 0.0)) * colv(cols.btd)
    p += float(params.get("w_orphan", 0.0)) * colv(cols.orphan)
    p += float(params.get("w_priority", 0.0)) * colv(cols.priority)
    p += float(params.get("w_fast", 0.0)) * colv(cols.fast)
    p += float(params.get("w_accel", 0.0)) * colv(cols.accel)

    # experience + stack
    exp = colv(cols.experienced)
    stack = colv(cols.stack)
    p += float(params.get("w_exp", 0.0)) * exp
    p += float(params.get("w_stack", 0.0)) * stack

    # manufacturing risk (penalty with inexperienced amplification)
    # Semantics: w_mfg_amp amplifies the base penalty w_mfg_pen for
    # inexperienced sponsors (in_exp==1). Effective extra term is:
    #   gamma = w_mfg_pen * w_mfg_amp * i_mfg_inexp
    mfg = colv(cols.mfg_risk)
    in_exp = (1.0 - exp)
    w_pen = float(params.get("w_mfg_pen", 0.0))
    w_amp = float(params.get("w_mfg_amp", 0.0))
    gate = float(params.get("i_mfg_inexp", 1.0))
    p += w_pen * mfg
    p += (w_pen * w_amp * gate) * (mfg * in_exp)

    # therapeutic area adjustments (string field -> simple buckets)
    if cols.ta is not None:
        ta = df[cols.ta].fillna("").astype(str).str.lower()
        is_pain = ta.str.contains("pain")
        is_cns  = ta.str.contains("cns|neuro|neurolog|psych")
        is_onco = ta.str.contains("onc|cancer|tumor|lymph|leuk")
        is_inf  = ta.str.contains("infect|viral|bacter|hiv|flu|covid")

        p += float(params.get("adj_pain", 0.0)) * is_pain.to_numpy(dtype=np.float32)
        p += float(params.get("adj_cns", 0.0))  * is_cns.to_numpy(dtype=np.float32)
        p += float(params.get("adj_onco", 0.0)) * is_onco.to_numpy(dtype=np.float32)
        p += float(params.get("adj_inf", 0.0))  * is_inf.to_numpy(dtype=np.float32)

        # extra CNS amp: interact with AdCom presence (lightweight)
        had_ad = colv(cols.had_adcom)
        p += float(params.get("adj_cns_amp", 0.0)) * is_cns.to_numpy(dtype=np.float32) * had_ad

    # AdCom curve
    had_adcom = colv(cols.had_adcom)
    vote = colv(cols.adcom_vote_pct, default=50.0)
    vote_scaled = (vote - 50.0) / 50.0
    p += float(params.get("w_adcom", 0.0)) * had_adcom * vote_scaled

    # Trap v2 proxy: very high designation stack + inexperienced sponsor
    trap = (stack >= 4).astype(np.float32) * (1.0 - exp)
    p += float(params.get("w_des_trap", 0.0)) * trap

    return np.clip(p, 0.001, 0.999)

def fitness_from_metrics(m: Metrics, min_precision: float) -> float:
    if m.precision < min_precision:
        return -math.inf
    return (1e6
            - 1e3 * m.fp
            - 1e2 * m.brier
            + 50.0 * m.mcc
            + 10.0 * m.f1
            + 1.0 * m.specificity)
