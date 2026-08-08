#!/usr/bin/env python3
"""
ODIN v8.12 — FDA Data Dashboard Enrichment (HIGH PERFORMANCE)
Uses concurrent requests to maximize throughput.

Expected: ~10-20 companies/second with 10 concurrent workers
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================
# HARDCODED CREDENTIALS (verified working)
# ============================================
DEFAULT_AUTH_USER = "rockyshoals@gmail.com"
DEFAULT_AUTH_KEY = "XulnBCM9GXU6M8ea"

# Performance settings
MAX_WORKERS = 10  # Concurrent API requests
TIMEOUT_SECONDS = 30
MAX_RETRIES = 2
CHECKPOINT_INTERVAL = 25  # Save every N companies


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


class FastFDAClient:
    """High-performance FDA API client with connection pooling."""
    
    BASE_URL = "https://api-datadashboard.fda.gov/v1"
    
    def __init__(self, auth_user: str, auth_key: str):
        self.session = requests.Session()
        
        # Connection pooling for performance
        adapter = HTTPAdapter(
            pool_connections=MAX_WORKERS,
            pool_maxsize=MAX_WORKERS * 2,
            max_retries=Retry(total=MAX_RETRIES, backoff_factor=0.1)
        )
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization-User": auth_user,
            "Authorization-Key": auth_key,
        })
        
        # Verify credentials
        self._test_credentials()
    
    def _test_credentials(self):
        resp = self.session.post(
            f"{self.BASE_URL}/inspections_classifications",
            json={"start": 1, "rows": 1, "filters": {}, "columns": ["LegalName"]},
            timeout=30
        )
        if resp.status_code == 401:
            raise RuntimeError("FDA API credentials INVALID")
        print("✓ FDA API credentials verified")
    
    def get_inspections(self, company: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch inspections for a company. Returns empty list if none found."""
        body = {
            "start": 1,
            "rows": 5000,
            "sort": "InspectionEndDate",
            "sortorder": "DESC",
            "filters": {
                "LegalName": [company],
                "InspectionEndDateFrom": [start_date],
                "InspectionEndDateTo": [end_date],
                "ProductType": ["Drugs", "Biologics"],
            },
            "columns": [
                "FEINumber", "LegalName", "InspectionID", "Classification",
                "ClassificationCode", "InspectionEndDate", "ProductType",
                "City", "State", "CountryName", "PostedCitations",
            ],
        }
        
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/inspections_classifications",
                json=body,
                timeout=TIMEOUT_SECONDS
            )
            if resp.status_code == 401:
                raise RuntimeError("401 Unauthorized")
            
            data = resp.json()
            # 400 = success, 412 = no results (both valid)
            if data.get("statuscode") in (200, 400, 412, "200", "400", "412"):
                return data.get("result", []) or []
            
            return []
        except requests.exceptions.RequestException:
            return []
    
    def get_citations(self, fei_numbers: List[int]) -> List[Dict]:
        """Fetch citations for FEI numbers."""
        if not fei_numbers:
            return []
        
        body = {
            "start": 1,
            "rows": 5000,
            "sort": "InspectionEndDate",
            "sortorder": "DESC",
            "filters": {"FEINumber": [int(x) for x in fei_numbers[:100]]},
            "columns": [
                "FEINumber", "LegalName", "CitationID", "InspectionID",
                "ActCFRNumber", "ShortDescription", "LongDescription",
                "InspectionEndDate", "ProgramArea",
            ],
        }
        
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/inspections_citations",
                json=body,
                timeout=TIMEOUT_SECONDS
            )
            data = resp.json()
            if data.get("statuscode") in (200, 400, 412, "200", "400", "412"):
                return data.get("result", []) or []
            return []
        except:
            return []


@dataclass
class MfgRiskResult:
    company: str
    form_483_oai_flag: bool = False
    oai_count_pre_pdufa: int = 0
    cmc_citation_count: int = 0
    inspection_trend: float = 0.5
    mfg_risk_score: float = 0.0
    mfg_risk_level: str = "LOW"
    s21_form_483_oai: float = 0.0
    s22_cmc_citations: float = 0.0
    s23_inspection_trend: float = 0.0
    fda_data_available: bool = False
    fei_numbers: List[int] = None
    error: str = ""
    
    def __post_init__(self):
        if self.fei_numbers is None:
            self.fei_numbers = []


def is_cmc_citation(rec: Dict) -> bool:
    txt = " ".join([
        str(rec.get("ActCFRNumber", "")),
        str(rec.get("ShortDescription", "")),
        str(rec.get("LongDescription", "")),
    ]).lower()
    kws = ["gmp", "cgmp", "manufactur", "aseptic", "steril", "validation",
           "batch", "specification", "stability", "control", "quality", "contamination"]
    return any(k in txt for k in kws) or re.search(r"\b(210|211|600|601)\b", txt)


def compute_risk(
    company: str,
    catalyst_date: pd.Timestamp,
    inspections: List[Dict],
    citations: List[Dict],
    lookback_days: int,
) -> MfgRiskResult:
    """Compute manufacturing risk features for a single event."""
    
    cutoff = catalyst_date - pd.Timedelta(days=1)
    lookback_start = cutoff - pd.Timedelta(days=lookback_days)
    
    def in_window(d: Any) -> bool:
        dt = parse_date_any(d)
        return dt is not None and lookback_start <= dt <= cutoff
    
    rel_ins = [r for r in inspections if in_window(r.get("InspectionEndDate"))]
    rel_cit = [r for r in citations if in_window(r.get("InspectionEndDate"))]
    
    fei_nums = sorted({int(r["FEINumber"]) for r in rel_ins 
                       if r.get("FEINumber") not in (None, "", "0", 0)})
    
    data_available = len(rel_ins) > 0
    
    oai_count = sum(1 for r in rel_ins if "OAI" in str(r.get("Classification", "")).upper())
    form_483_oai_flag = oai_count > 0
    
    cmc_count = sum(1 for r in rel_cit if is_cmc_citation(r))
    
    # Trend: ratio of clean (NAI) inspections
    if rel_ins:
        nai_count = sum(1 for r in rel_ins if "NAI" in str(r.get("Classification", "")).upper())
        trend = nai_count / len(rel_ins)
    else:
        trend = 0.5
    
    # Composite score
    risk_score = 0.0
    if form_483_oai_flag:
        risk_score += 0.4 * min(oai_count, 3)
    risk_score += 0.1 * min(cmc_count, 5)
    risk_score += 0.3 * (1 - trend)
    risk_score = min(risk_score, 1.0)
    
    risk_level = "HIGH" if risk_score >= 0.6 else ("MEDIUM" if risk_score >= 0.3 else "LOW")
    
    # ODIN signals
    s21 = -0.25 if form_483_oai_flag else 0.0
    s22 = -0.05 * min(cmc_count, 3)
    s23 = 0.05 if trend > 0.8 else (-0.10 if trend < 0.3 else 0.0)
    
    return MfgRiskResult(
        company=company,
        form_483_oai_flag=form_483_oai_flag,
        oai_count_pre_pdufa=oai_count,
        cmc_citation_count=cmc_count,
        inspection_trend=trend,
        mfg_risk_score=risk_score,
        mfg_risk_level=risk_level,
        s21_form_483_oai=s21,
        s22_cmc_citations=s22,
        s23_inspection_trend=s23,
        fda_data_available=data_available,
        fei_numbers=fei_nums,
    )


def process_company(
    client: FastFDAClient,
    company: str,
    events: List[Tuple[int, pd.Timestamp]],  # (row_idx, catalyst_date)
    lookback_days: int,
) -> List[Tuple[int, MfgRiskResult]]:
    """Process all events for a single company. Returns list of (row_idx, result)."""
    
    results = []
    
    # Get date range for all events
    dates = [d for _, d in events]
    min_d = min(dates)
    max_d = max(dates)
    start_date = iso_date(pd.Timestamp(min_d) - pd.Timedelta(days=lookback_days))
    end_date = iso_date(pd.Timestamp(max_d) - pd.Timedelta(days=1))
    
    company_q = sanitize_company_name(company)
    
    try:
        # Fetch inspections
        inspections = client.get_inspections(company_q, start_date, end_date)
        
        # Fetch citations if we have FEIs
        feis = sorted({int(x["FEINumber"]) for x in inspections 
                       if x.get("FEINumber") not in (None, "", "0", 0)})
        citations = client.get_citations(feis) if feis else []
        
        # Compute risk for each event
        for row_idx, cat_date in events:
            result = compute_risk(company, cat_date, inspections, citations, lookback_days)
            results.append((row_idx, result))
            
    except Exception as e:
        # Return error results for all events
        for row_idx, _ in events:
            err_result = MfgRiskResult(company=company, error=str(e))
            results.append((row_idx, err_result))
    
    return results


def enrich_parallel(
    input_csv: str,
    output_csv: str,
    auth_user: str = DEFAULT_AUTH_USER,
    auth_key: str = DEFAULT_AUTH_KEY,
    lookback_days: int = 1095,
    max_workers: int = MAX_WORKERS,
    resume: bool = True,
):
    """Main enrichment with parallel processing."""
    
    print("=" * 60)
    print("ODIN v8.12 FDA Enrichment (HIGH PERFORMANCE)")
    print("=" * 60)
    print(f"Input:       {input_csv}")
    print(f"Output:      {output_csv}")
    print(f"Workers:     {max_workers} concurrent")
    print(f"Lookback:    {lookback_days} days")
    print("=" * 60)
    
    in_path = Path(input_csv)
    out_path = Path(output_csv)
    audit_path = out_path.with_suffix(".mfg_audit.jsonl")
    
    # Load data
    if resume and out_path.exists():
        print(f"Resuming from: {out_path}")
        df = pd.read_csv(out_path)
    else:
        df = pd.read_csv(in_path)
        if audit_path.exists():
            audit_path.unlink()
    
    # Ensure columns
    for col in ["form_483_oai_flag", "oai_count_pre_pdufa", "cmc_citation_count",
                "mfg_risk_score", "mfg_risk_level", "s21_form_483_oai",
                "s22_cmc_citations", "s23_inspection_trend", "fda_data_available"]:
        if col not in df.columns:
            df[col] = np.nan
    
    df["catalyst_date"] = pd.to_datetime(df["catalyst_date"], errors="coerce")
    
    # Group by company
    by_company: Dict[str, List[Tuple[int, pd.Timestamp]]] = {}
    for i, row in df.iterrows():
        comp = str(row.get("company", "")).strip()
        if not comp:
            continue
        # Skip if already processed
        if resume and pd.notna(df.at[i, "mfg_risk_score"]):
            continue
        cat_date = row["catalyst_date"]
        if pd.isna(cat_date):
            continue
        by_company.setdefault(comp, []).append((i, cat_date))
    
    companies_to_process = list(by_company.keys())
    total_companies = len(companies_to_process)
    total_events = sum(len(v) for v in by_company.values())
    
    print(f"Companies to process: {total_companies}")
    print(f"Events to process:    {total_events}")
    print("=" * 60)
    
    if total_companies == 0:
        print("Nothing to process!")
        return str(out_path)
    
    # Initialize client
    client = FastFDAClient(auth_user, auth_key)
    
    # Thread-safe counters
    stats = {"processed": 0, "with_data": 0, "no_data": 0, "errors": 0}
    stats_lock = Lock()
    
    # Audit file
    audit_f = open(audit_path, "a", encoding="utf-8")
    audit_lock = Lock()
    
    t_start = time.time()
    
    def update_results(results: List[Tuple[int, MfgRiskResult]]):
        """Update DataFrame with results (thread-safe for stats only)."""
        for row_idx, result in results:
            df.at[row_idx, "form_483_oai_flag"] = result.form_483_oai_flag
            df.at[row_idx, "oai_count_pre_pdufa"] = result.oai_count_pre_pdufa
            df.at[row_idx, "cmc_citation_count"] = result.cmc_citation_count
            df.at[row_idx, "mfg_risk_score"] = result.mfg_risk_score
            df.at[row_idx, "mfg_risk_level"] = result.mfg_risk_level
            df.at[row_idx, "s21_form_483_oai"] = result.s21_form_483_oai
            df.at[row_idx, "s22_cmc_citations"] = result.s22_cmc_citations
            df.at[row_idx, "s23_inspection_trend"] = result.s23_inspection_trend
            df.at[row_idx, "fda_data_available"] = result.fda_data_available
            
            with stats_lock:
                stats["processed"] += 1
                if result.error:
                    stats["errors"] += 1
                elif result.fda_data_available:
                    stats["with_data"] += 1
                else:
                    stats["no_data"] += 1
            
            # Audit
            eid = df["event_id"].iloc[row_idx] if "event_id" in df.columns else None
            audit_rec = {
                "event_id": eid,
                "company": result.company,
                "status": "error" if result.error else "ok",
                "fda_data_available": result.fda_data_available,
                "mfg_risk_score": result.mfg_risk_score,
                "mfg_risk_level": result.mfg_risk_level,
            }
            if result.error:
                audit_rec["error"] = result.error
            
            with audit_lock:
                audit_f.write(json.dumps(audit_rec) + "\n")
    
    # Process with thread pool
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_company, client, comp, by_company[comp], lookback_days): comp
            for comp in companies_to_process
        }
        
        for future in as_completed(futures):
            comp = futures[future]
            try:
                results = future.result()
                update_results(results)
            except Exception as e:
                print(f"Error processing {comp}: {e}")
            
            completed += 1
            
            # Progress & checkpoints
            if completed % CHECKPOINT_INTERVAL == 0 or completed == total_companies:
                elapsed = time.time() - t_start
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_companies - completed) / rate if rate > 0 else 0
                
                print(f"[{completed:4d}/{total_companies}] {rate:.1f} companies/sec | "
                      f"ETA: {eta/60:.1f} min | {stats['processed']} events")
                
                # Checkpoint save
                audit_f.flush()
                df.to_csv(out_path, index=False)
    
    audit_f.close()
    df.to_csv(out_path, index=False)
    
    elapsed = time.time() - t_start
    
    print()
    print("=" * 60)
    print("ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"Time:           {elapsed/60:.1f} minutes")
    print(f"Rate:           {total_companies/elapsed:.1f} companies/sec")
    print(f"Events:         {stats['processed']}")
    print(f"  With FDA data: {stats['with_data']}")
    print(f"  No FDA data:   {stats['no_data']}")
    print(f"  Errors:        {stats['errors']}")
    print(f"Output:         {out_path}")
    print(f"Audit:          {audit_path}")
    
    return str(out_path)


def main():
    ap = argparse.ArgumentParser(description="ODIN v8.12 FDA Enrichment (FAST)")
    ap.add_argument("--input", required=True, help="Input CSV")
    ap.add_argument("--output", required=True, help="Output CSV")
    ap.add_argument("--auth-user", default=DEFAULT_AUTH_USER)
    ap.add_argument("--auth-key", default=DEFAULT_AUTH_KEY)
    ap.add_argument("--lookback-days", type=int, default=1095)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    
    enrich_parallel(
        input_csv=args.input,
        output_csv=args.output,
        auth_user=args.auth_user,
        auth_key=args.auth_key,
        lookback_days=args.lookback_days,
        max_workers=args.workers,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
