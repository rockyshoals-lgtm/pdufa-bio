from __future__ import annotations
import random
from typing import Dict, Any, List, Tuple

def infer_bounds_from_top_configs(top_cfgs: List[Dict[str, Any]], pad_frac: float = 0.15) -> Dict[str, Tuple[float, float]]:
    mins = {}
    maxs = {}
    for c in top_cfgs:
        params = c.get("params", c)
        for k, v in params.items():
            v = float(v)
            mins[k] = min(mins.get(k, v), v)
            maxs[k] = max(maxs.get(k, v), v)

    bounds = {}
    for k in mins:
        lo, hi = mins[k], maxs[k]
        span = (hi - lo) if hi > lo else (abs(lo) * 0.1 + 1e-6)
        bounds[k] = (lo - pad_frac * span, hi + pad_frac * span)
    return bounds

def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v

def perturb_params(base: Dict[str, float], bounds: Dict[str, Tuple[float, float]], sigma_frac: float = 0.08) -> Dict[str, float]:
    out = dict(base)
    for k, (lo, hi) in bounds.items():
        x = float(base.get(k, (lo + hi) / 2.0))
        span = hi - lo
        sigma = sigma_frac * span
        x2 = random.gauss(x, sigma)
        out[k] = clamp(x2, lo, hi)
    return out

def random_params(bounds: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    return {k: random.uniform(lo, hi) for k, (lo, hi) in bounds.items()}
