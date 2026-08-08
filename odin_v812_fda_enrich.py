#!/usr/bin/env python3
"""
ODIN v8.12 — FDA Data Dashboard Enrichment (T-1 compliant)

Implements:
- FDADataDashboardClient
- ODINManufacturingRiskCalculator
- enrich_pdufa_dataset()

Purpose:
- Replace leaked `manufacturing_risk` (post-decision CRL notes leakage) with T-1 compliant
  inspection/CMC proxies derived from FDA Data Dashboard inspection & citation data.

NOTE:
- This script requires FDA Data Dashboard API credentials (Authorization-User/Key).
- It is safe-by-design for T-1: it filters all inspections/citations to <= (catalyst_date - 1 day).

Outputs:
Adds (or overwrites) these columns:
- form_483_oai_flag
- oai_count_pre_pdufa
- cmc_citation_count
- mfg_risk_score
- mfg_risk_level
- s21_form_483_oai
- s22_cmc_citations
- s23_inspection_trend

Also writes an audit JSONL file with per-row evidence used (dates, counts, FEIs).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests


# -----------------------------
# Helpers
# -----------------------------
def iso_date(d: pd.Timestamp) -> str:
    return d.strftime("%Y-%m-%d")

def parse_date_any(x: Any) -> Optional[pd.Timestamp]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    try:
        return pd.to_datetime(x, errors="coerce", utc=True).tz_convert(None)  # naive
    except Exception:
        return None

def sanitize_company_name(name: str) -> str:
    s = (name or "").strip()
    # remove common suffixes that can cause matching problems
    s = re.sub(r"\b(incorporated|inc\.|corp\.|corporation|ltd\.|limited|plc|ag|sa|nv)\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def cache_key(*parts: str) -> str:
    safe = "|".join(parts)
    safe = re.sub(r"[^a-zA-Z0-9_\-|:.]", "_", safe)
    return safe[:180]


# -----------------------------
# FDA Data Dashboard API Client
# -----------------------------
class FDADataDashboardClient:
    """
    Client for FDA Data Dashboard (inspections, citations, compliance).
    Requires authentication credentials from FDA.
    """

    DEFAULT_BASE_URL = "https://api-datadashboard.fda.gov/v1"

    ENDPOINTS = {
        "inspections": "/inspections_classifications",
        "citations": "/inspections_citations",
        "compliance": "/compliance_actions",
        "import_refusals": "/import_refusals",
    }

    def __init__(
        self,
        auth_user: str,
        auth_key: str,
        base_url: str = "",
        timeout_s: int = 60,
        max_retries: int = 6,
        backoff_s: float = 1.5,
    ):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout_s = int(timeout_s)
        self.max_retries = int(max_retries)
        self.backoff_s = float(backoff_s)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization-User": auth_user,
                "Authorization-Key": auth_key,
            }
        )

    def _post_json_with_retries(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, json=body, timeout=self.timeout_s)
                # Some versions return 429 at HTTP layer; others in JSON payload.
                if resp.status_code == 429:
                    time.sleep(60)
                    continue
                resp.raise_for_status()
                data = resp.json()
                # Data Dashboard API uses a nonstandard `statuscode` field:
                # The reference implementation indicates 400 = success.
                sc = data.get("statuscode", None)
                if sc in (200, 400, "200", "400", None):
                    return data
                # If API returned an error, raise with message
                msg = data.get("message", f"statuscode={sc}")
                raise RuntimeError(f"Dashboard API error: {msg}")
            except Exception as e:
                last_err = e
                # exponential-ish backoff
                sleep = self.backoff_s * (2 ** attempt)
                time.sleep(min(sleep, 60))
        raise RuntimeError(f"Dashboard API request failed after retries: {last_err}")

    def query(
        self,
        endpoint: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        sort: str = "",
        sortorder: str = "DESC",
        start: int = 1,
        rows: int = 1000,
        return_total: bool = True,
    ) -> Dict[str, Any]:
        """
        Query FDA Data Dashboard with POST request.
        `start` appears to be 1-indexed in the docs/examples.
        """
        if endpoint not in self.ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}. Valid: {list(self.ENDPOINTS.keys())}")

        url = f"{self.base_url}{self.ENDPOINTS[endpoint]}"
        body = {
            "start": int(start),
            "rows": int(min(rows, 5000)),
            "sort": sort,
            "sortorder": sortorder,
            "filters": filters or {},
            "columns": columns or [],
            "returntotalcount": bool(return_total),
        }
        return self._post_json_with_retries(url, body)

    def query_all(
        self,
        endpoint: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        sort: str = "",
        sortorder: str = "DESC",
        rows: int = 5000,
        hard_limit: int = 200_000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all results with pagination using `start` and `rows`.
        Stops at `hard_limit` as a safety valve.
        """
        out: List[Dict[str, Any]] = []
        start = 1
        while True:
            data = self.query(
                endpoint=endpoint,
                filters=filters,
                columns=columns,
                sort=sort,
                sortorder=sortorder,
                start=start,
                rows=rows,
                return_total=True,
            )
            chunk = data.get("result", []) or []
            out.extend(chunk)
            if len(out) >= hard_limit:
                break

            # Try to infer if there are more results
            total = data.get("totalcount") or data.get("totalCount") or data.get("returntotalcount")
            if isinstance(total, bool):
                total = None
            if total is not None:
                try:
                    total_i = int(total)
                except Exception:
                    total_i = None
            else:
                total_i = None

            if not chunk:
                break
            if total_i is not None and len(out) >= total_i:
                break

            # Advance pagination
            start += len(chunk)

        return out

    def get_inspections(
        self,
        company: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        classification: Optional[str] = None,
        product_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get inspection classifications with flexible filtering.
        Dates should be YYYY-MM-DD.
        """
        filters: Dict[str, Any] = {}
        if company:
            filters["LegalName"] = [company]
        if start_date:
            filters["InspectionEndDateFrom"] = [start_date]
        if end_date:
            filters["InspectionEndDateTo"] = [end_date]
        if classification:
            filters["Classification"] = [classification]
        if product_types:
            filters["ProductType"] = product_types

        columns = [
            "FEINumber",
            "LegalName",
            "InspectionID",
            "Classification",
            "ClassificationCode",
            "InspectionEndDate",
            "ProductType",
            "City",
            "State",
            "CountryName",
            "PostedCitations",
        ]

        data = self.query_all(
            "inspections",
            filters=filters,
            columns=columns,
            sort="InspectionEndDate",
            sortorder="DESC",
        )
        return data

    def get_citations(self, fei_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Get Form 483 citations for specific facilities.
        """
        if not fei_numbers:
            return []
        filters = {"FEINumber": [int(x) for x in fei_numbers]}
        columns = [
            "FEINumber",
            "LegalName",
            "CitationID",
            "InspectionID",
            "ActCFRNumber",
            "ShortDescription",
            "LongDescription",
            "InspectionEndDate",
            "ProgramArea",
        ]
        data = self.query_all("citations", filters=filters, columns=columns, sort="InspectionEndDate", sortorder="DESC")
        return data


# --------------------------------------------
# Manufacturing/CMC risk feature computation
# --------------------------------------------
@dataclass
class MfgRiskFeatures:
    form_483_oai_flag: bool
    oai_count_pre_pdufa: int
    cmc_citation_count: int
    inspection_trend: float
    mfg_risk_score: float
    mfg_risk_level: str
    s21_form_483_oai: float
    s22_cmc_citations: float
    s23_inspection_trend: float

    # evidence for audit
    fei_numbers: List[int]
    max_inspection_end_date_used: Optional[str]
    max_citation_end_date_used: Optional[str]


class ODINManufacturingRiskCalculator:
    """
    Computes T-1 compliant inspection/CMC proxy features for a given sponsor + catalyst_date.

    Strategy:
    - Pull inspections from Data Dashboard (classifications) in a broad window.
    - Pull citations for facilities (FEI) observed in those inspections.
    - For each event, filter to <= cutoff_date (catalyst_date - 1) and within lookback window.

    Notes:
    - Company matching is imperfect. This class supports simple name sanitization.
    - Strongly recommended: maintain an alias mapping table for high-value sponsors.
    """

    CLASS_SEVERITY = {"NAI": 0.0, "VAI": 1.0, "OAI": 2.0}

    def __init__(
        self,
        dashboard: FDADataDashboardClient,
        lookback_days: int = 730,
        product_types: Optional[List[str]] = None,
        cache_dir: str = "./cache_fda_dashboard",
    ):
        self.dashboard = dashboard
        self.lookback_days = int(lookback_days)
        self.product_types = product_types or ["Drugs", "Biologics"]
        self.cache_dir = Path(cache_dir)
        ensure_dir(self.cache_dir)

    def _cache_get(self, key: str) -> Optional[Any]:
        p = self.cache_dir / f"{key}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _cache_put(self, key: str, obj: Any) -> None:
        p = self.cache_dir / f"{key}.json"
        try:
            p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def fetch_company_history(
        self,
        company: str,
        start_date: str,
        end_date: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch (inspections, citations) for company across a wide time window.
        Uses disk cache.
        """
        company_q = sanitize_company_name(company)
        k_ins = cache_key("inspections", company_q, start_date, end_date)
        inspections = self._cache_get(k_ins)
        if inspections is None:
            inspections = self.dashboard.get_inspections(
                company=company_q,
                start_date=start_date,
                end_date=end_date,
                product_types=self.product_types,
            )
            self._cache_put(k_ins, inspections)

        feis = sorted({int(x["FEINumber"]) for x in inspections if x.get("FEINumber") not in (None, "", "0")})
        k_cit = cache_key("citations", company_q, start_date, end_date, "fei", ",".join(map(str, feis[:200])))
        citations = self._cache_get(k_cit)
        if citations is None:
            citations = self.dashboard.get_citations(feis)
            self._cache_put(k_cit, citations)

        return inspections, citations

    @staticmethod
    def _is_cmc_like_citation(rec: Dict[str, Any]) -> bool:
        """
        Heuristic: treat all GMP-related citations as 'CMC-like'.
        You can tighten this later by CFR patterns or keyword filtering.
        """
        txt = " ".join(
            [
                str(rec.get("ActCFRNumber", "")),
                str(rec.get("ShortDescription", "")),
                str(rec.get("LongDescription", "")),
                str(rec.get("ProgramArea", "")),
            ]
        ).lower()
        # Common manufacturing/quality keywords
        kws = [
            "gmp", "cgmp", "manufactur", "aseptic", "steril", "validation", "process",
            "batch", "specification", "stability", "control", "quality", "contamination",
            "cleanroom", "deviation", "capa", "equipment", "facility"
        ]
        if any(k in txt for k in kws):
            return True
        # CFR sections commonly tied to drug GMP
        if re.search(r"\b(21\s*cfr\s*)?(210|211|600|601)\b", txt):
            return True
        return False

    @classmethod
    def _classification_code(cls, rec: Dict[str, Any]) -> str:
        c = str(rec.get("ClassificationCode") or rec.get("Classification") or "").strip().upper()
        # normalize variants
        if "OAI" in c:
            return "OAI"
        if "VAI" in c:
            return "VAI"
        if "NAI" in c:
            return "NAI"
        return c or "NAI"

    def compute_for_event(
        self,
        company: str,
        catalyst_date: pd.Timestamp,
        inspections: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
    ) -> MfgRiskFeatures:
        """
        Compute features for one event, using already-fetched history.
        """
        catalyst_date = pd.to_datetime(catalyst_date)
        cutoff = catalyst_date - pd.Timedelta(days=1)
        lookback_start = cutoff - pd.Timedelta(days=self.lookback_days)

        # Filter inspections to lookback window and <= cutoff
        ins_rows = []
        for r in inspections:
            d = parse_date_any(r.get("InspectionEndDate"))
            if d is None:
                continue
            if d <= cutoff and d >= lookback_start:
                ins_rows.append((d, r))
        ins_rows.sort(key=lambda x: x[0], reverse=True)

        feis = sorted({int(r.get("FEINumber")) for _, r in ins_rows if r.get("FEINumber") not in (None, "", "0")})

        # OAI counts
        oai_count = 0
        sev_series = []
        date_series = []
        for d, r in ins_rows:
            code = self._classification_code(r)
            if code == "OAI":
                oai_count += 1
            sev = float(self.CLASS_SEVERITY.get(code, 0.0))
            sev_series.append(sev)
            date_series.append(d)

        form_483_oai_flag = bool(oai_count > 0)

        # Filter citations to those linked to FEI and <= cutoff, in lookback
        cit_rows = []
        for c in citations:
            fei = c.get("FEINumber")
            if fei in (None, "", "0"):
                continue
            try:
                fei_i = int(fei)
            except Exception:
                continue
            if fei_i not in feis:
                continue
            d = parse_date_any(c.get("InspectionEndDate"))
            if d is None:
                continue
            if d <= cutoff and d >= lookback_start:
                if self._is_cmc_like_citation(c):
                    cit_rows.append((d, c))
        cit_rows.sort(key=lambda x: x[0], reverse=True)
        cmc_citation_count = int(len(cit_rows))

        # Inspection trend: slope of severity vs time (days), scaled
        inspection_trend = 0.0
        if len(date_series) >= 3:
            # Fit y = a + b*t where t is days since earliest
            t0 = min(date_series)
            t = np.array([(d - t0).days for d in date_series], dtype=np.float32)
            y = np.array(sev_series, dtype=np.float32)
            # simple linear regression slope
            t_mean = float(t.mean())
            y_mean = float(y.mean())
            denom = float(((t - t_mean) ** 2).sum())
            if denom > 0:
                slope = float(((t - t_mean) * (y - y_mean)).sum() / denom)  # severity per day
                # scale to "per year"
                inspection_trend = slope * 365.0
        elif len(date_series) == 2:
            # simple difference per year
            d0, d1 = sorted(date_series)
            y0, y1 = sev_series[date_series.index(d0)], sev_series[date_series.index(d1)]
            days = max(1, (d1 - d0).days)
            inspection_trend = (y1 - y0) * 365.0 / days

        # Build a bounded risk score (0..1)
        # These are intentionally conservative; tune later in the ODIN optimizer.
        cit_scaled = min(np.log1p(cmc_citation_count) / 5.0, 1.0)  # ~0..1
        oai_scaled = min(oai_count / 2.0, 1.0)                    # 0,0.5,1
        trend_scaled = float(np.clip((inspection_trend + 0.5) / 2.0, 0.0, 1.0))  # rough mapping
        risk_score = float(np.clip(0.60 * float(form_483_oai_flag) + 0.25 * oai_scaled + 0.12 * cit_scaled + 0.03 * trend_scaled, 0.0, 1.0))

        if risk_score >= 0.75:
            level = "HIGH"
        elif risk_score >= 0.40:
            level = "MED"
        else:
            level = "LOW"

        # ODIN signal columns (these are what the scorer should consume)
        s21 = 1.0 if form_483_oai_flag else 0.0
        s22 = float(cit_scaled)
        s23 = float(np.clip(inspection_trend, -2.0, 2.0) / 2.0)  # normalize to [-1,1]

        max_ins_date = iso_date(ins_rows[0][0]) if ins_rows else None
        max_cit_date = iso_date(cit_rows[0][0]) if cit_rows else None

        return MfgRiskFeatures(
            form_483_oai_flag=form_483_oai_flag,
            oai_count_pre_pdufa=int(oai_count),
            cmc_citation_count=cmc_citation_count,
            inspection_trend=float(inspection_trend),
            mfg_risk_score=risk_score,
            mfg_risk_level=level,
            s21_form_483_oai=float(s21),
            s22_cmc_citations=float(s22),
            s23_inspection_trend=float(s23),
            fei_numbers=feis,
            max_inspection_end_date_used=max_ins_date,
            max_citation_end_date_used=max_cit_date,
        )


# -----------------------------
# Dataset enrichment function
# -----------------------------
def enrich_pdufa_dataset(
    input_csv: str,
    output_csv: str,
    auth_user: str,
    auth_key: str,
    cache_dir: str = "./cache_fda_dashboard",
    lookback_days: int = 730,
    product_types: Optional[List[str]] = None,
    audit_jsonl: str = "",
    resume: bool = True,
) -> str:
    """
    Enrich ODIN PDUFA dataset with T-1 compliant inspection/CMC proxy features.
    Returns output path.

    Best practice:
    - Run once to create output + audit file.
    - Re-run with --resume if interrupted.

    IMPORTANT: This function never uses outcome/crl_notes to derive new columns.
    """
    df_in = pd.read_csv(input_csv)
    if "company" not in df_in.columns:
        raise ValueError("Dataset missing required column: company")
    if "catalyst_date" not in df_in.columns:
        raise ValueError("Dataset missing required column: catalyst_date")

    # Resume: if output exists and resume enabled, load it and keep prior filled values.
    out_path = Path(output_csv)
    if resume and out_path.exists():
        df = pd.read_csv(out_path)
        # ensure we still have original rows
        if len(df) != len(df_in) or "event_id" in df_in.columns and "event_id" in df.columns and not df_in["event_id"].equals(df["event_id"]):
            # fall back to input
            df = df_in.copy()
    else:
        df = df_in.copy()

    # Ensure columns exist
    new_cols = [
        "form_483_oai_flag",
        "oai_count_pre_pdufa",
        "cmc_citation_count",
        "mfg_risk_score",
        "mfg_risk_level",
        "s21_form_483_oai",
        "s22_cmc_citations",
        "s23_inspection_trend",
    ]
    for c in new_cols:
        if c not in df.columns:
            df[c] = np.nan

    df["catalyst_date"] = pd.to_datetime(df["catalyst_date"], errors="coerce")
    if df["catalyst_date"].isna().any():
        bad = int(df["catalyst_date"].isna().sum())
        raise ValueError(f"Found {bad} rows with invalid catalyst_date.")

    # Init clients
    dash = FDADataDashboardClient(auth_user=auth_user, auth_key=auth_key)
    calc = ODINManufacturingRiskCalculator(
        dashboard=dash,
        lookback_days=lookback_days,
        product_types=product_types or ["Drugs", "Biologics"],
        cache_dir=cache_dir,
    )

    # audit file
    audit_path = Path(audit_jsonl) if audit_jsonl else out_path.with_suffix(".mfg_audit.jsonl")
    ensure_dir(audit_path.parent)
    audit_f = open(audit_path, "a", encoding="utf-8")

    # Group by company for efficient fetching
    companies = df["company"].fillna("").astype(str)
    unique_companies = sorted(set(companies))

    # Determine per-company min/max date windows
    by_company_idx: Dict[str, List[int]] = {}
    for i, comp in enumerate(companies):
        by_company_idx.setdefault(comp, []).append(i)

    t_start = time.time()
    for ci, comp in enumerate(unique_companies):
        idxs = by_company_idx.get(comp, [])
        if not idxs:
            continue

        # Resume: if all rows already filled, skip.
        if resume:
            filled = df.loc[idxs, "mfg_risk_score"].notna().all()
            if filled:
                continue

        dates = df.loc[idxs, "catalyst_date"].tolist()
        min_d = min(dates)
        max_d = max(dates)
        # wide pull window: (min - lookback) to (max - 1 day)
        start_date = iso_date(pd.Timestamp(min_d) - pd.Timedelta(days=lookback_days))
        end_date = iso_date(pd.Timestamp(max_d) - pd.Timedelta(days=1))

        try:
            inspections, citations = calc.fetch_company_history(comp, start_date=start_date, end_date=end_date)
        except Exception as e:
            # Write audit entries for all company rows with error
            for i in idxs:
                audit_f.write(json.dumps({"event_id": df.get("event_id", pd.Series([None]*len(df))).iloc[i],
                                          "company": comp,
                                          "status": "error_fetch",
                                          "error": str(e)}) + "\n")
            audit_f.flush()
            continue

        # Compute features per event
        for i in idxs:
            if resume and pd.notna(df.at[i, "mfg_risk_score"]):
                continue

            cat_date = pd.Timestamp(df.at[i, "catalyst_date"])
            feats = calc.compute_for_event(comp, cat_date, inspections, citations)

            df.at[i, "form_483_oai_flag"] = bool(feats.form_483_oai_flag)
            df.at[i, "oai_count_pre_pdufa"] = int(feats.oai_count_pre_pdufa)
            df.at[i, "cmc_citation_count"] = int(feats.cmc_citation_count)
            df.at[i, "mfg_risk_score"] = float(feats.mfg_risk_score)
            df.at[i, "mfg_risk_level"] = str(feats.mfg_risk_level)
            df.at[i, "s21_form_483_oai"] = float(feats.s21_form_483_oai)
            df.at[i, "s22_cmc_citations"] = float(feats.s22_cmc_citations)
            df.at[i, "s23_inspection_trend"] = float(feats.s23_inspection_trend)

            audit_f.write(json.dumps({
                "event_id": df.get("event_id", pd.Series([None]*len(df))).iloc[i] if "event_id" in df.columns else None,
                "company": comp,
                "catalyst_date": iso_date(cat_date),
                "cutoff_date": iso_date(cat_date - pd.Timedelta(days=1)),
                "lookback_days": lookback_days,
                "fei_numbers": feats.fei_numbers,
                "max_inspection_end_date_used": feats.max_inspection_end_date_used,
                "max_citation_end_date_used": feats.max_citation_end_date_used,
                "form_483_oai_flag": feats.form_483_oai_flag,
                "oai_count_pre_pdufa": feats.oai_count_pre_pdufa,
                "cmc_citation_count": feats.cmc_citation_count,
                "inspection_trend": feats.inspection_trend,
                "mfg_risk_score": feats.mfg_risk_score,
                "mfg_risk_level": feats.mfg_risk_level,
                "s21_form_483_oai": feats.s21_form_483_oai,
                "s22_cmc_citations": feats.s22_cmc_citations,
                "s23_inspection_trend": feats.s23_inspection_trend,
                "status": "ok",
            }) + "\n")

        # periodic flush/save
        audit_f.flush()
        if (ci + 1) % 10 == 0:
            df.to_csv(out_path, index=False)
            elapsed = time.time() - t_start
            print(f"[{ci+1}/{len(unique_companies)}] saved checkpoint -> {out_path} | elapsed {elapsed/60:.1f} min")

    audit_f.close()
    df.to_csv(out_path, index=False)
    print(f"Done. Wrote enriched dataset: {out_path}")
    print(f"Wrote audit trail: {audit_path}")
    return str(out_path)


def generate_validation_report(enriched_csv: str, audit_jsonl: str, report_md: str) -> str:
    """
    Generate a basic validation report focused on T-1 compliance and coverage.
    """
    df = pd.read_csv(enriched_csv)
    n = len(df)

    # Coverage
    cov = {c: float(df[c].notna().mean()) if c in df.columns else 0.0 for c in [
        "form_483_oai_flag","oai_count_pre_pdufa","cmc_citation_count",
        "mfg_risk_score","mfg_risk_level","s21_form_483_oai","s22_cmc_citations","s23_inspection_trend"
    ]}

    # Audit scan: confirm max used dates <= cutoff
    violations = 0
    checked = 0
    if os.path.exists(audit_jsonl):
        with open(audit_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("status") != "ok":
                    continue
                cd = parse_date_any(rec.get("catalyst_date"))
                cutoff = parse_date_any(rec.get("cutoff_date"))
                if cutoff is None or cd is None:
                    continue
                mi = parse_date_any(rec.get("max_inspection_end_date_used"))
                mc = parse_date_any(rec.get("max_citation_end_date_used"))
                # If present, both must be <= cutoff
                ok = True
                if mi is not None and mi > cutoff:
                    ok = False
                if mc is not None and mc > cutoff:
                    ok = False
                checked += 1
                if not ok:
                    violations += 1

    md = []
    md.append("# ODIN v8.12 Enrichment Validation Report")
    md.append("")
    md.append(f"- Generated: {datetime.utcnow().isoformat()}Z")
    md.append(f"- Enriched CSV: `{enriched_csv}`")
    md.append(f"- Audit JSONL: `{audit_jsonl}`")
    md.append("")
    md.append("## Coverage")
    for k, v in cov.items():
        md.append(f"- {k}: {v*100:.1f}% non-null")
    md.append("")
    md.append("## T-1 Compliance Audit (date checks)")
    md.append(f"- Audit rows checked: {checked}")
    md.append(f"- Violations (max used date > cutoff): {violations}")
    md.append("")
    md.append("## Notes / Next Steps")
    md.append("- If violations > 0: inspect the offending audit rows and fix parsing or filtering.")
    md.append("- Add sponsor alias mapping for better LegalName matching if coverage is low.")
    md.append("- After enrichment, re-run the GPU optimizer with manufacturing_risk removed and s21/s22/s23 enabled.")
    md_text = "\n".join(md)

    Path(report_md).write_text(md_text, encoding="utf-8")
    print(f"Wrote report: {report_md}")
    return report_md


def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input ODIN dataset CSV (T-1 safe)")
    ap.add_argument("--output", required=True, help="Output enriched CSV")
    ap.add_argument("--auth-user", required=True, help="FDA Data Dashboard Authorization-User")
    ap.add_argument("--auth-key", required=True, help="FDA Data Dashboard Authorization-Key")
    ap.add_argument("--cache-dir", default="./cache_fda_dashboard", help="Disk cache directory")
    ap.add_argument("--lookback-days", type=int, default=730, help="Lookback window in days (default 2 years)")
    ap.add_argument("--audit-jsonl", default="", help="Optional audit jsonl output path")
    ap.add_argument("--no-resume", action="store_true", help="Disable resume/checkpointing")
    ap.add_argument("--validate", action="store_true", help="Generate validation report after enrichment")
    ap.add_argument("--report-md", default="", help="Validation report output path (markdown)")
    args = ap.parse_args()

    enrich_pdufa_dataset(
        input_csv=args.input,
        output_csv=args.output,
        auth_user=args.auth_user,
        auth_key=args.auth_key,
        cache_dir=args.cache_dir,
        lookback_days=args.lookback_days,
        audit_jsonl=args.audit_jsonl,
        resume=(not args.no_resume),
    )

    if args.validate:
        audit = args.audit_jsonl if args.audit_jsonl else str(Path(args.output).with_suffix(".mfg_audit.jsonl"))
        report = args.report_md if args.report_md else str(Path(args.output).with_suffix(".validation.md"))
        generate_validation_report(args.output, audit, report)


if __name__ == "__main__":
    _cli()
