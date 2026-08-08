"""ODIN v37.6 — Multi-head calibration engine.

No web fetching. Provide pre-decision inputs only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
import json
import math
import hashlib
import datetime as dt

try:
    from odin_allfather_engine import AllFatherScorer, CatalystEvent, CatalystSignals
except Exception:
    AllFatherScorer = None
    CatalystEvent = None
    CatalystSignals = None


FORECAST_PRECEDENCE = [
    "ODIN_v37.6_HYBRID_HUNTER",
    "ODIN_v37_HYBRID",
    "ODIN_v36",
    "ODIN_v35",
    "ODIN_v34",
    "ODIN_v33",
    "ODIN_v32",
    "ODIN_v28",
    "ODIN_v26",
    "ODIN_v14",
    "ODIN_v6",
    "UNKNOWN",
]
PRECEDENCE_RANK = {k: i for i, k in enumerate(FORECAST_PRECEDENCE)}


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def _logit(p: float) -> float:
    p = min(1 - 1e-9, max(1e-9, float(p)))
    return math.log(p / (1 - p))


def shrink_logit(p: float, completeness: float) -> float:
    """Shrink probability toward 0.5 when completeness is low."""
    c = min(1.0, max(0.0, float(completeness)))
    scale = 0.35 + 0.65 * c
    return _sigmoid(_logit(p) * scale)


def apply_europa_caps(p: float, europa_status: str | None) -> Tuple[float, Optional[str]]:
    """Europa Shield caps (CMC hard gate) for PDUFA head."""
    if europa_status is None:
        europa_status = "UNKNOWN"
    s = str(europa_status).upper().strip()
    if s == "GREEN":
        return p, None
    if s == "UNKNOWN":
        return min(p, 0.78), "EUROPA_CAP_UNKNOWN"
    if s == "YELLOW":
        return min(p, 0.72), "EUROPA_CAP_YELLOW"
    if s == "RED":
        return min(p, 0.55), "EUROPA_CAP_RED"
    return min(p, 0.78), "EUROPA_CAP_UNKNOWN"


def route_head(event: Dict[str, Any]) -> str:
    et = str(event.get("event_type") or event.get("catalyst_type") or "").upper()
    if et in ("PDUFA", "NDA", "BLA", "SNDA", "SBLA"):
        return "HEAD_PDUFA"
    if et in ("ADCOM", "ADVISORY", "ADVISORY_COMMITTEE"):
        return "HEAD_ADCOM"
    if et in ("PHASE2", "PHASE3", "PHASE_2", "PHASE_3"):
        return "HEAD_PHASE"
    if et in ("MA", "M&A", "MERGER", "ACQUISITION"):
        return "HEAD_MA"
    # default
    return "HEAD_PDUFA"


def compute_segment_id(head: str, event: Dict[str, Any]) -> str:
    year = "UNKNOWN"
    d = event.get("catalyst_date") or event.get("date")
    if isinstance(d, str) and len(d) >= 4:
        year = d[:4]
    review = str(event.get("review_type") or "UNKNOWN").upper()
    modality = str(event.get("modality_bucket") or "UNKNOWN").upper()
    ta = str(event.get("therapy_area") or "UNKNOWN").upper()
    return f"{head}|{year}|{review}|{modality}|{ta}"


def compute_completeness(head: str, event: Dict[str, Any]) -> float:
    # Simple presence-based completeness per spec
    def present(x: Any) -> bool:
        if x is None:
            return False
        if isinstance(x, str) and not x.strip():
            return False
        return True

    if head == "HEAD_PDUFA":
        weights = {
            "clinical": 0.25,
            "safety": 0.15,
            "designations": 0.10,
            "cmc": 0.25,
            "fda_tone": 0.15,
            "hiring": 0.10,
        }
        buckets = {
            "clinical": present(event.get("clinical_summary")) or present(event.get("trial_met_primary")) or present(event.get("phase3_met_primary")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
            "designations": present(event.get("designations")) or any(present(event.get(k)) for k in ["btd", "priority_review", "orphan", "fast_track", "rmat", "accelerated"]),
            "cmc": present(event.get("europa_status")) or present(event.get("manufacturing_sites")) or present(event.get("inspection_status")),
            "fda_tone": present(event.get("fda_tone")) or present(event.get("info_requests")) or present(event.get("timeline_extension_reason")),
            "hiring": present(event.get("hiring_signals")) or present(event.get("commercial_hiring_ramp_score")),
        }
    elif head == "HEAD_ADCOM":
        weights = {"vote_pct": 0.40, "topic": 0.15, "briefing": 0.15, "cmc": 0.15, "safety": 0.15}
        buckets = {
            "vote_pct": present(event.get("adcom_yes_pct")),
            "topic": present(event.get("adcom_topic_risk")),
            "briefing": present(event.get("briefing_docs")) or present(event.get("briefing_doc_url")),
            "cmc": present(event.get("europa_status")) or present(event.get("inspection_status")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
        }
    elif head == "HEAD_PHASE":
        weights = {"trial_phase": 0.15, "endpoint": 0.25, "prior": 0.25, "design": 0.25, "safety": 0.10}
        buckets = {
            "trial_phase": present(event.get("trial_phase")),
            "endpoint": present(event.get("endpoint_type")),
            "prior": present(event.get("prior_signal_strength")),
            "design": present(event.get("trial_design_quality")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
        }
    else:
        weights = {"fit": 0.25, "rumor": 0.25, "gov": 0.20, "banker": 0.15, "fin": 0.15}
        buckets = {
            "fit": present(event.get("strategic_fit_score")),
            "rumor": present(event.get("deal_rumor_evidence")),
            "gov": present(event.get("poison_pill_removed")),
            "banker": present(event.get("banker_hired")),
            "fin": present(event.get("cash_runway_months")) or present(event.get("financing_risk")),
        }

    score = 0.0
    for k, w in weights.items():
        if buckets.get(k, False):
            score += float(w)
    return max(0.0, min(1.0, score))


@dataclass
class PriorTable:
    """Holds empirical priors for segments. Populate from your dataset offline."""
    # key: segment_id
    counts: Dict[str, Tuple[int, int]]  # (successes, total)
    global_counts: Tuple[int, int] = (0, 0)

    def prior(self, segment_id: str, k: int = 50) -> float:
        s_g, n_g = self.global_counts
        p_global = (s_g / n_g) if n_g > 0 else 0.70
        s, n = self.counts.get(segment_id, (0, 0))
        return (s + k * p_global) / (n + k) if (n + k) > 0 else p_global


class CalibrationRegistry:
    """Append-only calibration registry writer (JSONL)."""

    def __init__(self, path: str):
        self.path = path

    def append(self, payload: Dict[str, Any]) -> str:
        payload = dict(payload)
        payload.setdefault("created_utc", dt.datetime.now(dt.timezone.utc).isoformat())
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        payload["calibration_id"] = payload.get("calibration_id") or h
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload["calibration_id"]


class OdinV37MultiHead:
    """Operational prediction engine implementing the v37.6 calibration upgrades."""

    def __init__(
        self,
        prior_table: Optional[PriorTable] = None,
        calibration_registry_path: str = "/mnt/data/odin_v37/ledgers/calibration_registry.jsonl",
    ):
        self.priors = prior_table or PriorTable(counts={}, global_counts=(0, 0))
        self.registry = CalibrationRegistry(calibration_registry_path)
        self._pdufa_base = AllFatherScorer(calibrator=None) if AllFatherScorer else None

    def base_probability(self, head: str, event: Dict[str, Any]) -> Tuple[float, List[str]]:
        flags: List[str] = []

        if head == "HEAD_PDUFA":
            # Prefer v37 signals if provided; fall back to AllFather scorer when CatalystSignals supplied.
            if self._pdufa_base and event.get("signals") and CatalystSignals and CatalystEvent:
                sig = CatalystSignals(**event["signals"])
                ev = CatalystEvent(
                    ticker=str(event.get("ticker") or "UNKNOWN"),
                    asset=event.get("asset"),
                    indication=event.get("indication"),
                    catalyst_type=str(event.get("event_type") or event.get("catalyst_type") or "PDUFA"),
                    catalyst_date=event.get("catalyst_date"),
                    forecast_timestamp_utc=event.get("forecast_timestamp_utc"),
                    evidence=event.get("sources") or [],
                    signals=sig,
                )
                res = self._pdufa_base.score(ev)
                p = float(res.poa_raw)
            else:
                # Deterministic fallback: use provided poa_raw if given, else neutral prior.
                p = float(event.get("poa_raw") if event.get("poa_raw") is not None else 0.70)

            p, cap = apply_europa_caps(p, event.get("europa_status"))
            if cap:
                flags.append(cap)
            return p, flags

        if head == "HEAD_ADCOM":
            y = event.get("adcom_yes_pct")
            if y is None:
                return 0.65, flags
            y = float(y)
            if y >= 70:
                return 0.97, flags
            if y >= 50:
                return 0.90, flags
            if y >= 40:
                return 0.55, flags
            return 0.20, flags

        if head == "HEAD_PHASE":
            # If prior_signal_strength provided, map [0,1] to probability
            p = event.get("prior_signal_strength")
            if p is None:
                # default base
                return 0.55 if str(event.get("trial_phase") or "3") in ("3", "PHASE3") else 0.50, flags
            return max(0.01, min(0.99, float(p))), flags

        if head == "HEAD_MA":
            # M&A is hardest; keep conservative
            fit = event.get("strategic_fit_score")
            rumor = event.get("deal_rumor_evidence")
            if fit is None and rumor is None:
                return 0.15, flags
            fit = float(fit or 0.0)
            rumor = float(rumor or 0.0)
            return max(0.01, min(0.60, 0.10 + 0.35 * fit + 0.35 * rumor)), flags

        return 0.50, flags

    def predict(self, event: Dict[str, Any]) -> Dict[str, Any]:
        head = route_head(event)
        segment_id = compute_segment_id(head, event)
        completeness = compute_completeness(head, event)

        p_raw, flags = self.base_probability(head, event)
        p_shrunk = shrink_logit(p_raw, completeness)

        p_prior = self.priors.prior(segment_id)
        # default blend weight 0.35 prior / 0.65 model (configurable)
        p_blend = 0.35 * p_prior + 0.65 * p_shrunk

        # No learned calibrator fit is performed here; hook point.
        p_final = max(0.01, min(0.99, p_blend))

        return {
            "head": head,
            "segment_id": segment_id,
            "data_completeness": completeness,
            "poa_raw": p_raw,
            "poa_shrunk": p_shrunk,
            "poa_prior": p_prior,
            "poa_blend": p_blend,
            "poa_final": p_final,
            "flags": flags,
        }

PRECEDENCE_ORDER = [
    "ODIN_v37.6_HYBRID_HUNTER",
    "ODIN_v37_HYBRID",
    "ODIN_v36",
    "ODIN_v35",
    "ODIN_v34",
    "ODIN_v33",
    "ODIN_v32",
    "ODIN_v28",
    "ODIN_v26",
    "ODIN_v14",
    "ODIN_v6",
    "UNKNOWN",
]
PRECEDENCE_RANK = {k: i for i, k in enumerate(PRECEDENCE_ORDER)}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = max(1e-6, min(1 - 1e-6, float(p)))
    return math.log(p / (1.0 - p))


def shrink_logit(p: float, completeness: float) -> float:
    """Logit shrinkage toward 0 (p->0.5) based on completeness ∈ [0,1]."""
    completeness = max(0.0, min(1.0, float(completeness)))
    scale = 0.35 + 0.65 * completeness
    return _sigmoid(_logit(p) * scale)


def route_head(event: Dict[str, Any]) -> str:
    et = str(event.get("event_type") or event.get("catalyst_type") or "").upper()
    if et in {"PDUFA", "SNDA", "SBLA", "NDA", "BLA", "FDA"}:
        return "HEAD_PDUFA"
    if "ADCOM" in et or "ADVISORY" in et:
        return "HEAD_ADCOM"
    if et in {"PHASE2", "PHASE3", "PHASE 2", "PHASE 3", "READOUT"}:
        return "HEAD_PHASE"
    if et in {"MA", "M&A", "MERGER", "ACQUISITION"}:
        return "HEAD_MA"
    return "HEAD_PDUFA"


def compute_segment_id(event: Dict[str, Any], head: str) -> str:
    """Coarse segmentation key. Keep simple + deterministic."""
    year = "UNKNOWN"
    d = event.get("catalyst_date") or event.get("date")
    if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
        year = d[:4]

    review = str(event.get("review_type") or "UNKNOWN").upper()
    modality = str(event.get("modality_bucket") or "UNKNOWN").upper()
    ta = str(event.get("therapy_area") or "UNKNOWN").upper()

    if head == "HEAD_PDUFA":
        return f"{year}|{review}|{modality}|{ta}"
    if head == "HEAD_ADCOM":
        topic = str(event.get("adcom_topic_risk") or "UNKNOWN").upper()
        return f"{year}|{topic}|{ta}"
    if head == "HEAD_PHASE":
        phase = str(event.get("trial_phase") or "UNKNOWN").upper()
        return f"{year}|{phase}|{modality}|{ta}"
    if head == "HEAD_MA":
        return f"{year}|{ta}"
    return f"{year}|UNKNOWN"


def compute_completeness(event: Dict[str, Any], head: str) -> float:
    """Simple presence-based completeness (0-1)."""
    def present(x: Any) -> bool:
        if x is None:
            return False
        if isinstance(x, str) and not x.strip():
            return False
        return True

    if head == "HEAD_PDUFA":
        parts = {
            "clinical": present(event.get("clinical_summary")) or present(event.get("trial_met_primary")) or present(event.get("phase3_met_primary")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
            "designations": present(event.get("designations")) or any(present(event.get(k)) for k in ["btd", "priority_review", "orphan", "fast_track", "rmat", "accelerated"]),
            "cmc": present(event.get("europa_status")) or present(event.get("manufacturing_sites")) or present(event.get("inspection_status")),
            "fda_tone": present(event.get("fda_tone")) or present(event.get("info_requests")) or present(event.get("timeline_extension_reason")),
            "hiring": present(event.get("hiring_signals")) or present(event.get("commercial_hiring_ramp_score")),
        }
        weights = {"clinical": 0.25, "safety": 0.15, "designations": 0.10, "cmc": 0.25, "fda_tone": 0.15, "hiring": 0.10}
        return sum(weights[k] for k, ok in parts.items() if ok)

    if head == "HEAD_ADCOM":
        parts = {
            "vote": present(event.get("adcom_yes_pct")),
            "topic": present(event.get("adcom_topic_risk")),
            "briefing": present(event.get("briefing_docs")) or present(event.get("briefing_doc_url")),
            "cmc": present(event.get("europa_status")) or present(event.get("inspection_status")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
        }
        weights = {"vote": 0.40, "topic": 0.15, "briefing": 0.15, "cmc": 0.15, "safety": 0.15}
        return sum(weights[k] for k, ok in parts.items() if ok)

    if head == "HEAD_PHASE":
        parts = {
            "phase": present(event.get("trial_phase")),
            "endpoint": present(event.get("endpoint_type")),
            "prior": present(event.get("prior_signal_strength")),
            "design": present(event.get("trial_design_quality")),
            "safety": present(event.get("safety_summary")) or present(event.get("safety_signal")),
        }
        weights = {"phase": 0.15, "endpoint": 0.25, "prior": 0.25, "design": 0.25, "safety": 0.10}
        return sum(weights[k] for k, ok in parts.items() if ok)

    if head == "HEAD_MA":
        parts = {
            "fit": present(event.get("strategic_fit_score")),
            "rumor": present(event.get("deal_rumor_evidence")),
            "gov": present(event.get("poison_pill_removed")),
            "banker": present(event.get("banker_hired")),
            "fin": present(event.get("cash_runway_months")) or present(event.get("financing_risk")),
        }
        weights = {"fit": 0.25, "rumor": 0.25, "gov": 0.20, "banker": 0.15, "fin": 0.15}
        return sum(weights[k] for k, ok in parts.items() if ok)

    return 0.0


def apply_europa_caps(p: float, event: Dict[str, Any], head: str) -> Tuple[float, Optional[str]]:
    """Europa Shield caps (PDUFA head only)."""
    if head != "HEAD_PDUFA":
        return p, None
    status = str(event.get("europa_status") or "UNKNOWN").upper()
    if status == "UNKNOWN":
        return min(p, 0.78), "EUROPA_CAP_UNKNOWN"
    if status == "YELLOW":
        return min(p, 0.72), "EUROPA_CAP_YELLOW"
    if status == "RED":
        return min(p, 0.55), "EUROPA_CAP_RED"
    return p, None


@dataclass
class PriorTable:
    """Holds empirical priors. Values can be updated offline and versioned."""
    # key -> (successes, total)
    counts: Dict[str, Tuple[int, int]]

    def prior(self, key: str, global_key: str = "GLOBAL", k: int = 50) -> float:
        s, n = self.counts.get(key, (0, 0))
        gs, gn = self.counts.get(global_key, (0, 0))
        p_global = (gs / gn) if gn > 0 else 0.70
        return (s + k * p_global) / (n + k) if (n + k) > 0 else p_global


@dataclass
class PlattCalibrator:
    """Simple Platt scaling: p' = sigmoid(a*logit(p) + b)."""
    a: float = 1.0
    b: float = 0.0

    def transform(self, p: float) -> float:
        return _sigmoid(self.a * _logit(p) + self.b)


class CalibrationRegistry:
    """Append-only calibrator registry (JSONL)."""

    def __init__(self, path: str):
        self.path = path

    def append(self, payload: Dict[str, Any]) -> str:
        payload = dict(payload)
        payload.setdefault("created_utc", dt.datetime.now(dt.timezone.utc).isoformat())
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        cid = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
        payload["calibration_id"] = cid
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return cid


class OdinV37MultiHead:
    """ODIN v37.6 multi-head predictor.

    This class focuses on the probability post-processing + logging contract.
    Deterministic base scoring is:
    - PDUFA: via AllFatherScorer if CatalystSignals provided; otherwise uses priors
    - ADCOM: piecewise mapping from yes_pct
    - PHASE: uses prior_signal_strength if provided, else priors
    - M&A: uses strategic_fit_score/rumor evidence if provided, else priors
    """

    def __init__(
        self,
        priors: Optional[PriorTable] = None,
        calibrators: Optional[Dict[str, PlattCalibrator]] = None,
        registry_path: str = "/mnt/data/odin_v37/ledgers/calibration_registry.jsonl",
    ):
        self.priors = priors or PriorTable(counts={"GLOBAL": (70, 100)})
        self.calibrators = calibrators or {}
        self.registry = CalibrationRegistry(registry_path)
        self.base_scorer = AllFatherScorer(calibrator=None) if AllFatherScorer is not ... else None

    def predict(self, event: Dict[str, Any]) -> Dict[str, Any]:
        head = route_head(event)
        segment_id = compute_segment_id(event, head)
        completeness = compute_completeness(event, head)

        # --- base probability ---
        p_raw = self._base_probability(event, head, segment_id)

        # Europa Shield caps
        p_capped, cap_flag = apply_europa_caps(p_raw, event, head)

        # Completeness shrink
        p_shrunk = shrink_logit(p_capped, completeness)

        # Prior blend
        p_prior = self.priors.prior(f"{head}|{segment_id}", global_key=f"{head}|GLOBAL")
        # Blend weight: 0.35 prior, 0.65 model
        p_blend = 0.35 * p_prior + 0.65 * p_shrunk

        # Calibration overlay (per head|segment)
        cal_key = f"{head}|{segment_id}"
        cal = self.calibrators.get(cal_key) or self.calibrators.get(f"{head}|GLOBAL")
        p_final = cal.transform(p_blend) if cal is not None else p_blend

        out = {
            "head": head,
            "segment_id": segment_id,
            "data_completeness": round(completeness, 4),
            "poa_raw": round(float(p_raw), 6),
            "poa_capped": round(float(p_capped), 6),
            "poa_shrunk": round(float(p_shrunk), 6),
            "poa_prior": round(float(p_prior), 6),
            "poa_blend": round(float(p_blend), 6),
            "poa_final": round(float(p_final), 6),
            "cap_flag": cap_flag,
            "calibration_id": getattr(cal, "calibration_id", None) if cal is not None else None,
        }

        return out

    def _base_probability(self, event: Dict[str, Any], head: str, segment_id: str) -> float:
        # PDUFA: if we have structured CatalystSignals dict, reuse deterministic scorer
        if head == "HEAD_PDUFA" and self.base_scorer is not None:
            sig = event.get("signals")
            if isinstance(sig, dict):
                try:
                    cs = CatalystSignals(event_type=str(event.get("catalyst_type") or "PDUFA"), **sig)
                    ce = CatalystEvent(
                        ticker=str(event.get("ticker") or "UNKNOWN"),
                        asset=event.get("asset"),
                        indication=event.get("indication"),
                        catalyst_type=str(event.get("catalyst_type") or "PDUFA"),
                        catalyst_date=event.get("catalyst_date"),
                        forecast_timestamp_utc=event.get("forecast_timestamp_utc"),
                        evidence=event.get("evidence") or [],
                        signals=cs,
                    )
                    res = self.base_scorer.score(ce)
                    return float(res.poa_raw)
                except Exception:
                    pass

        # ADCOM: piecewise monotone mapping from yes_pct
        if head == "HEAD_ADCOM":
            y = event.get("adcom_yes_pct")
            try:
                y = float(y)
            except Exception:
                y = None
            if y is None:
                return self.priors.prior(f"{head}|{segment_id}", global_key=f"{head}|GLOBAL")
            if y >= 70:
                return 0.97
            if y >= 50:
                return 0.90
            if y >= 40:
                return 0.55
            return 0.20

        # PHASE: use prior_signal_strength if present
        if head == "HEAD_PHASE":
            p = event.get("prior_signal_strength")
            try:
                p = float(p)
            except Exception:
                p = None
            if p is not None:
                return max(0.01, min(0.99, p))
            return self.priors.prior(f"{head}|{segment_id}", global_key=f"{head}|GLOBAL")

        # M&A: blend fit + rumor if present
        if head == "HEAD_MA":
            fit = event.get("strategic_fit_score")
            rumor = event.get("deal_rumor_evidence")
            try:
                fit = float(fit)
            except Exception:
                fit = None
            try:
                rumor = float(rumor)
            except Exception:
                rumor = None
            if fit is None and rumor is None:
                return self.priors.prior(f"{head}|{segment_id}", global_key=f"{head}|GLOBAL")
            fit = 0.5 if fit is None else max(0.0, min(1.0, fit))
            rumor = 0.5 if rumor is None else max(0.0, min(1.0, rumor))
            return max(0.01, min(0.99, 0.5 * fit + 0.5 * rumor))

        # fallback
        return self.priors.prior(f"{head}|{segment_id}", global_key=f"{head}|GLOBAL")
