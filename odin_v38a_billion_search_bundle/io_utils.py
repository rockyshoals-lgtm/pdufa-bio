import json, os, hashlib
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

import pandas as pd

# ---- Column mapping ----
# Edit these keys if your dataset uses different names.
COLUMN_MAP = {
    # label
    "label": ["label", "outcome", "approved", "is_approved", "y", "decision", "fda_decision", "final_outcome"],

    # designations (0/1)
    "btd": ["btd", "breakthrough", "has_btd"],
    "orphan": ["orphan", "has_orphan"],
    "priority": ["priority_review", "priority", "has_priority"],
    "fast": ["fast_track", "fasttrack", "has_fast_track"],
    "accel": ["accelerated_approval", "accelerated", "has_accel"],

    # sponsor experience (0/1)
    "experienced": ["experienced_sponsor", "sponsor_experienced", "exp_sponsor"],

    # designation stack count (int)
    "stack": ["designation_stack", "designation_stack_count", "stack_count"],

    # manufacturing risk (0/1)
    "mfg_risk": ["mfg_risk", "manufacturing_risk", "cmc_risk"],

    # adcom
    "had_adcom": ["had_adcom", "adcom_held"],
    "adcom_vote_pct": ["adcom_vote_pct", "adcom_vote_percent", "adcom_yes_pct"],

    # therapeutic area (string categorical)
    "ta": ["therapeutic_area", "ta", "indication_area", "therapy_area"],
}

def resolve_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

@dataclass(frozen=True)
class ResolvedColumns:
    label: str
    btd: Optional[str]
    orphan: Optional[str]
    priority: Optional[str]
    fast: Optional[str]
    accel: Optional[str]
    experienced: Optional[str]
    stack: Optional[str]
    mfg_risk: Optional[str]
    had_adcom: Optional[str]
    adcom_vote_pct: Optional[str]
    ta: Optional[str]

def resolve_columns(df: pd.DataFrame) -> ResolvedColumns:
    def req(key):
        col = resolve_col(df, COLUMN_MAP[key])
        if col is None:
            raise KeyError(f"Required column not found for '{key}'. Candidates={COLUMN_MAP[key]}")
        return col
    def opt(key):
        return resolve_col(df, COLUMN_MAP[key])

    return ResolvedColumns(
        label=req("label"),
        btd=opt("btd"),
        orphan=opt("orphan"),
        priority=opt("priority"),
        fast=opt("fast"),
        accel=opt("accel"),
        experienced=opt("experienced"),
        stack=opt("stack"),
        mfg_risk=opt("mfg_risk"),
        had_adcom=opt("had_adcom"),
        adcom_vote_pct=opt("adcom_vote_pct"),
        ta=opt("ta"),
    )

def load_dataset(path: str) -> Tuple[pd.DataFrame, ResolvedColumns]:
    df = pd.read_csv(path)
    cols = resolve_columns(df)
    return df, cols

def dataset_fingerprint(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def run_hash(cfg: Dict[str, Any], data_fp: str, code_tag: str) -> str:
    s = canonical_json(cfg) + "|" + data_fp + "|" + code_tag
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)
