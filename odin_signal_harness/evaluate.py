
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class Confusion:
    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True)
class Metrics:
    brier: float
    precision: float
    recall: float
    specificity: float
    mcc: float
    accuracy: float
    fp: int
    tp: int
    tn: int
    fn: int
    threshold: float


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def _confusion(y: np.ndarray, pred_pos: np.ndarray) -> Confusion:
    y = np.asarray(y, dtype=int)
    pred_pos = np.asarray(pred_pos, dtype=bool)

    tp = int(np.sum((pred_pos == 1) & (y == 1)))
    fp = int(np.sum((pred_pos == 1) & (y == 0)))
    tn = int(np.sum((pred_pos == 0) & (y == 0)))
    fn = int(np.sum((pred_pos == 0) & (y == 1)))
    return Confusion(tp=tp, fp=fp, tn=tn, fn=fn)


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den != 0 else 0.0


def mcc_from_conf(c: Confusion) -> float:
    tp, fp, tn, fn = c.tp, c.fp, c.tn, c.fn
    num = tp * tn - fp * fn
    den = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    return float(num / np.sqrt(den)) if den > 0 else 0.0


def metrics_at_threshold(y: np.ndarray, p: np.ndarray, threshold: float) -> Metrics:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    pred_pos = p >= float(threshold)

    c = _confusion(y, pred_pos)
    precision = _safe_div(c.tp, c.tp + c.fp)
    recall = _safe_div(c.tp, c.tp + c.fn)
    specificity = _safe_div(c.tn, c.tn + c.fp)
    accuracy = _safe_div(c.tp + c.tn, c.tp + c.tn + c.fp + c.fn)

    return Metrics(
        brier=brier_score(y, p),
        precision=precision,
        recall=recall,
        specificity=specificity,
        mcc=mcc_from_conf(c),
        accuracy=accuracy,
        fp=c.fp,
        tp=c.tp,
        tn=c.tn,
        fn=c.fn,
        threshold=float(threshold),
    )


def choose_threshold_fp_averse(
    y: np.ndarray,
    p: np.ndarray,
    *,
    precision_floor: float = 0.94,
    grid: Optional[np.ndarray] = None,
) -> Tuple[float, Metrics]:
    """
    Select a classification threshold that:
      1) Meets precision >= precision_floor
      2) Minimizes FP count (primary)
      3) Maximizes recall (secondary)
      4) Maximizes MCC (tertiary tie-breaker)

    This matches ODIN's FP-averse philosophy.
    """
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)

    if grid is None:
        # Candidate thresholds are unique probabilities (plus endpoints).
        uniq = np.unique(p)
        # Add a couple of extremes for safety.
        grid = np.unique(np.concatenate([uniq, [0.0, 1.0]]))

    best: Optional[Metrics] = None
    best_thr: float = 0.5

    for thr in grid:
        m = metrics_at_threshold(y, p, float(thr))
        if m.precision + 1e-12 < precision_floor:
            continue
        if best is None:
            best = m
            best_thr = float(thr)
            continue
        # Primary: minimize FP
        if m.fp < best.fp:
            best = m
            best_thr = float(thr)
            continue
        if m.fp > best.fp:
            continue
        # Secondary: maximize recall
        if m.recall > best.recall + 1e-12:
            best = m
            best_thr = float(thr)
            continue
        if abs(m.recall - best.recall) > 1e-12 and m.recall < best.recall:
            continue
        # Tertiary: maximize MCC
        if m.mcc > best.mcc + 1e-12:
            best = m
            best_thr = float(thr)

    if best is None:
        # If no threshold meets the floor, fall back to threshold=1.0 (never buy).
        best_thr = 1.0
        best = metrics_at_threshold(y, p, best_thr)

    return best_thr, best
