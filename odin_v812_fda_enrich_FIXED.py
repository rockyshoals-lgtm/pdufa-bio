#!/usr/bin/env python3
"""
ODIN v8.12 — FDA Data Dashboard Enrichment (T-1 compliant)
FIXED VERSION - Credentials embedded as defaults

Run with:
  python odin_v812_fda_enrich_FIXED.py --input your_data.csv --output enriched.csv
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

# ============================================
# HARDCODED CREDENTIALS (verified working 2026-01-24)
# ============================================
DEFAULT_AUTH_USER = "rockyshoals@gmail.com"
DEFAULT_AUTH_KEY = "XulnBCM9GXU6M8ea"


# -----------------------------
# Helpers
# -----------------------------
def iso_date(d: pd.Timestamp) -> str:
    return d.strftime("%Y-%m-%d")

def parse_date_any(x: Any) -> Optional[pd.Timestamp]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    try:
        return pd.to_datetime(x, errors="coerce", utc=True).tz_convert(None)
    except Exception:
        return None

def sanitize_company_name(name: str) -> str:
    s = (name or "").strip()
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
        
        # Test credentials on init
        self._test_credentials()
    
    def _test_credentials(self):
        """Quick test to verify credentials work before processing"""
        url = f"{self.base_url}/inspections_classifications"
        body = {
            "start": 1,
            "rows": 1,
            "sort": "InspectionEndDate",
            "sortorder": "DESC",
            "filters": {},
            "columns": ["LegalName"],
        }
        try:
            resp = self.session.post(url, json=body, timeout=30)
            if resp.status_code == 401:
                raise RuntimeError(
                    f"FDA API credentials are INVALID.\n"
                    f"  User: {self.session.headers.get('Authorization-User')}\n"
                    f"  Key:  {self.session.headers.get('Authorization-Key')[:6]}...{self.session.headers.get('Authorization-Key')[-4:]}\n"
                    f"Please check your credentials and try again."
                )
            resp.raise_for_status()
            data = resp.json()
            if data.get("statuscode") in (200, 400, "200", "400"):
                print(f"✓ FDA API credentials verified successfully")
                return
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to FDA API: {e}")

    def _post_json_with_retries(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, json=body, timeout=self.timeout_s)
                if resp.status_code == 429:
                    time.sleep(60)
                    continue
                resp.raise_for_status()
                data = resp.json()
                sc = data.get("statuscode", None)
                if sc in (200, 400, "200", "400", None):
                    return data
                msg = data.get("message", f"statuscode={sc}")
                raise RuntimeError(f"Dashboard API error: {msg}")
            except Exception as e:
                last_err = e
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
        if endpoint not in self.ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}")

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
            "FEINumber", "LegalName", "InspectionID", "Classification",
            "ClassificationCode", "InspectionEndDate", "ProductType",
            "City", "State", "CountryName", "PostedCitations",
        ]

        return self.query_all(
            "inspections", filters=filters, columns=columns,
            sort="InspectionEndDate", sortorder="DESC",
        )

    def get_citations(self, fei_numbers: List[int]) -> List[Dict[str, Any]]:
        if not fei_numbers:
            return []
        filters = {"FEINumber": [int(x) for x in fei_numbers]}
        columns = [
            "FEINumber", "LegalName", "CitationID", "InspectionID",
            "ActCFRNumber", "ShortDescription", "LongDescription",
            "InspectionEndDate", "ProgramArea",
        ]
        return self.query_all("citations", filters=filters, columns=columns,
                              sort="InspectionEndDate", sortorder="DESC")


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
    fei_numbers: List[int]
    max_inspection_end_date_used: Optional[str]
    max_citation_end_date_used: Optional[str]


class ODINManufacturingRiskCalculator:
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
        txt = " ".join([
            str(rec.get("ActCFRNumber", "")),
            str(rec.get("ShortDescription", "")),
            str(rec.get("LongDescription", "")),
            str(rec.get("ProgramArea", "")),
        ]).lower()
        kws = [
            "gmp", "cgmp", "manufactur", "aseptic", "steril", "validation", "process",
            "batch", "specification", "stability", "control", "quality", "contamination",
            "cleanroom", "deviation", "capa", "equipment", "facility"
        ]
        if any(k in txt for k in kws):
            return True
        if re.search(r"\b(21\s*cfr\s*)?(210|211|600|601)\b", txt):
            return True
        return False

    def compute_for_event(
        self,
        company: str,
        catalyst_date: pd.Timestamp,
        inspections: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
    ) -> MfgRiskFeatures:
        cutoff = catalyst_date - pd.Timedelta(days=1)
        lookback_start = cutoff - pd.Timedelta(days=self.lookback_days)

        def in_window(d: Any) -> bool:
            dt = parse_date_any(d)
            if dt is None:
                return False
            return lookback_start <= dt <= cutoff

        rel_ins = [r for r in inspections if in_window(r.get("InspectionEndDate"))]
        rel_cit = [r for r in citations if in_window(r.get("InspectionEndDate"))]

        fei_nums = sorted({int(r["FEINumber"]) for r in rel_ins if r.get("FEINumber") not in (None, "", "0")})

        oai_count = sum(1 for r in rel_ins if "OAI" in str(r.get("Classification", "")).upper())
        form_483_oai_flag = oai_count > 0

        cmc_cit_count = sum(1 for r in rel_cit if self._is_cmc_like_citation(r))

        # Inspection trend: ratio of good (NAI) to total
        if rel_ins:
            nai_count = sum(1 for r in rel_ins if "NAI" in str(r.get("Classification", "")).upper())
            trend = nai_count / len(rel_ins)
        else:
            trend = 0.5  # neutral if no data

        # Composite risk score
        risk_score = 0.0
        if form_483_oai_flag:
            risk_score += 0.4 * min(oai_count, 3)  # up to 1.2
        risk_score += 0.1 * min(cmc_cit_count, 5)  # up to 0.5
        risk_score += 0.3 * (1 - trend)  # up to 0.3
        risk_score = min(risk_score, 1.0)

        if risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Signal values for ODIN
        s21 = -0.25 if form_483_oai_flag else 0.0
        s22 = -0.05 * min(cmc_cit_count, 3)  # -0.05 to -0.15
        s23 = 0.05 if trend > 0.8 else (-0.10 if trend < 0.3 else 0.0)

        max_ins_date = max((parse_date_any(r.get("InspectionEndDate")) for r in rel_ins), default=None)
        max_cit_date = max((parse_date_any(r.get("InspectionEndDate")) for r in rel_cit), default=None)

        return MfgRiskFeatures(
            form_483_oai_flag=form_483_oai_flag,
            oai_count_pre_pdufa=oai_count,
            cmc_citation_count=cmc_cit_count,
            inspection_trend=trend,
            mfg_risk_score=risk_score,
            mfg_risk_level=risk_level,
            s21_form_483_oai=s21,
            s22_cmc_citations=s22,
            s23_inspection_trend=s23,
            fei_numbers=fei_nums,
            max_inspection_end_date_used=iso_date(max_ins_date) if max_ins_date else None,
            max_citation_end_date_used=iso_date(max_cit_date) if max_cit_date else None,
        )


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
    """Main enrichment function"""
    
    print("=" * 60)
    print("ODIN v8.12 FDA Data Dashboard Enrichment")
    print("=" * 60)
    print(f"Input:  {input_csv}")
    print(f"Output: {output_csv}")
    print(f"Lookback: {lookback_days} days")
    print(f"Auth User: {auth_user}")
    print(f"Auth Key: {auth_key[:6]}...{auth_key[-4:]}")
    print("=" * 60)
    
    in_path = Path(input_csv)
    out_path = Path(output_csv)

    if resume and out_path.exists():
        print(f"Resuming from existing output: {out_path}")
        df = pd.read_csv(out_path)
    else:
        df = pd.read_csv(in_path)

    # Ensure new columns exist
    for col in ["form_483_oai_flag", "oai_count_pre_pdufa", "cmc_citation_count",
                "mfg_risk_score", "mfg_risk_level", "s21_form_483_oai",
                "s22_cmc_citations", "s23_inspection_trend"]:
        if col not in df.columns:
            df[col] = np.nan

    # Parse dates
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

    # Audit file
    audit_path = Path(audit_jsonl) if audit_jsonl else out_path.with_suffix(".mfg_audit.jsonl")
    ensure_dir(audit_path.parent)
    
    # Clear old audit file if not resuming
    if not resume and audit_path.exists():
        audit_path.unlink()
    
    audit_f = open(audit_path, "a", encoding="utf-8")

    # Group by company
    companies = df["company"].fillna("").astype(str)
    unique_companies = sorted(set(companies))

    by_company_idx: Dict[str, List[int]] = {}
    for i, comp in enumerate(companies):
        by_company_idx.setdefault(comp, []).append(i)

    t_start = time.time()
    for ci, comp in enumerate(unique_companies):
        idxs = by_company_idx.get(comp, [])
        if not idxs:
            continue

        # Resume check
        if resume:
            filled = df.loc[idxs, "mfg_risk_score"].notna().all()
            if filled:
                continue

        dates = df.loc[idxs, "catalyst_date"].tolist()
        min_d = min(dates)
        max_d = max(dates)
        start_date = iso_date(pd.Timestamp(min_d) - pd.Timedelta(days=lookback_days))
        end_date = iso_date(pd.Timestamp(max_d) - pd.Timedelta(days=1))

        try:
            inspections, citations = calc.fetch_company_history(comp, start_date=start_date, end_date=end_date)
        except Exception as e:
            for i in idxs:
                eid = df["event_id"].iloc[i] if "event_id" in df.columns else None
                audit_f.write(json.dumps({
                    "event_id": eid,
                    "company": comp,
                    "status": "error_fetch",
                    "error": str(e)
                }) + "\n")
            audit_f.flush()
            continue

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

            eid = df["event_id"].iloc[i] if "event_id" in df.columns else None
            audit_f.write(json.dumps({
                "event_id": eid,
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


def _cli():
    ap = argparse.ArgumentParser(description="ODIN v8.12 FDA Enrichment (credentials embedded)")
    ap.add_argument("--input", required=True, help="Input ODIN dataset CSV")
    ap.add_argument("--output", required=True, help="Output enriched CSV")
    ap.add_argument("--auth-user", default=DEFAULT_AUTH_USER, help=f"FDA auth user (default: {DEFAULT_AUTH_USER})")
    ap.add_argument("--auth-key", default=DEFAULT_AUTH_KEY, help="FDA auth key (default: embedded)")
    ap.add_argument("--cache-dir", default="./cache_fda_dashboard", help="Disk cache directory")
    ap.add_argument("--lookback-days", type=int, default=1095, help="Lookback window in days (default 3 years)")
    ap.add_argument("--audit-jsonl", default="", help="Optional audit jsonl output path")
    ap.add_argument("--no-resume", action="store_true", help="Disable resume/checkpointing")
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


if __name__ == "__main__":
    _cli()
