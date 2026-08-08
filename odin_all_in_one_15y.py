#!/usr/bin/env python3
# -*- coding: utf-8 -*-

r"""
ODIN — All-in-One Miner + Scorer (15y)
--------------------------------------
- Company universe (SEC) with SIC enrichment & 30-day caching (auto-heals missing CIKs)
- FDA approvals mining paths:
    * --fda-mode search    → OpenFDA "search" endpoint, year-by-year with month fallback on 500s
    * --fda-mode download  → OpenFDA Download API + directory listing fallback (bulk JSON)
    * --fda-mode both      → Search first; on empty, fall back to Download API; finally DataFiles
    * Always ends with Drugs@FDA **Data Files** fallback:
        - Recognizes FDA links like /media/<id>/download (even without .zip suffix)
- EDGAR miner (8-K/6-K), optional full document text fetch & catalyst classification
- Optional FDA local ingestion: --fda-local-dir /path/to/*.json.zip (no network to bulk host)
- Dedup + Odin pre-approval scoring (percent + tier + confidence + “why”)
- Outputs: CSV + XLSX (Excel with strings_to_urls=False to avoid >65,530-link warning)

USAGE (PowerShell, Windows):
  Set-Location "C:\\Users\\dcmoo\\Documents\\Python"
  $env:SEC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36; rockyshoals@gmail.com OdinBiotech/1.0"
  $env:OPENFDA_API_KEY = "NO3JlhueCMr9TqwduPgnKJVuQMAvkltU7kNZBkfx"

  & "C:\\Program Files\\Python312\\python.exe" ".\\odin_all_in_one_15y.py" `
    --years 15 `
    --fda-mode both `
    --company-map-csv company_map.csv `
    --sic-include 2834,2835,2836,2833,8731,8732,8733,8734,3845 `
    --edgar-fetch-text `
    --out-csv  odin_pdufa_15y.csv `
    --out-xlsx odin_pdufa_15y.xlsx `
    --readable-out-csv  odin_pdufa_15y_readable.csv `
    --readable-out-xlsx odin_pdufa_15y_readable.xlsx `
    --verbose
"""

import os, re, sys, io, json, time, zipfile, argparse, datetime as dt
import html as ihtml
from typing import Optional, List, Dict, Tuple
import pandas as pd

try:
    import requests
except Exception:
    requests = None

TODAY = dt.date.today()
DEFAULT_UA = os.environ.get("SEC_USER_AGENT", "rockyshoals@gmail.com OdinBiotech/1.0")
OPENFDA_API_KEY = os.environ.get("OPENFDA_API_KEY", "").strip()

# ---------------- Console utils ----------------
def log(msg: str):  print(f"[INFO] {msg}", flush=True)
def warn(msg: str): print(f"[WARN] {msg}", flush=True)
def err(msg: str):  print(f"[ERROR] {msg}", flush=True)

def step(title: str):
    print("\n" + "="*78)
    print(title)
    print("="*78, flush=True)

def progress_bar(i: int, n: int, prefix: str = "", width: int = 40):
    n = max(n, 1); i = min(i, n)
    pct = int(i*100/n)
    bar = "█"*int(width*pct/100) + "·"*(width-int(width*pct/100))
    print(f"\r{prefix} [{bar}] {pct:3d}% ({i}/{n})", end="", flush=True)
    if i >= n: print("", flush=True)

# ---------------- Helpers ---------------------
def normalize_ticker(t: Optional[str]) -> str:
    if t is None: return ""
    return str(t).strip().upper().replace("$","")

def parse_date_safe(x):
    try:
        if isinstance(x, dt.date): return x
        return pd.to_datetime(x, errors="coerce").date()
    except Exception:
        return None

def ensure_dir(p: str):
    d = os.path.dirname(os.path.abspath(p))
    if d and not os.path.exists(d): os.makedirs(d, exist_ok=True)

class RPS:
    def __init__(self, per_sec=2.0): self.per_sec = per_sec; self.last=0.0
    def wait(self):
        import time as _t
        now=_t.time(); gap=1.0/max(self.per_sec,1e-6)
        delay=max(0.0, self.last + gap - now)
        if delay>0: _t.sleep(delay)
        self.last=_t.time()

# ---------------- HTTP helpers ---------------
def http_get_json(url: str, params=None, tag="generic", ua=DEFAULT_UA, rps:RPS=None, tries=4, timeout=20):
    if requests is None:
        warn("requests missing; web calls disabled"); return None
    headers = {"User-Agent": ua, "Accept": "application/json,text/plain,*/*"}
    q = dict(params or {})

    # Auto-attach OpenFDA API key for api.fda.gov calls (search + download index)
    if ("api.fda.gov" in url or tag.startswith("openfda")) and OPENFDA_API_KEY and "api_key" not in q:
        q["api_key"] = OPENFDA_API_KEY

    last = None
    for k in range(1, tries+1):
        try:
            if rps: rps.wait()
            r = requests.get(url, params=q, headers=headers, timeout=timeout)
            if r.status_code >= 400:
                if k == tries: warn(f"[HTTP][{tag}] {r.url} -> {r.status_code} {r.reason}")
                if 500 <= r.status_code < 600:
                    time.sleep(min(10, 1.2*k)); continue
                return None
            return r.json()
        except Exception as e:
            last = e
            if k == tries: warn(f"[HTTP][{tag}] error: {e}")
            time.sleep(min(6, 1.0*k))
    return None

def http_get_text(url: str, tag="generic", ua=DEFAULT_UA, rps:RPS=None, tries=3, timeout=20):
    if requests is None:
        warn("requests missing; web calls disabled"); return None
    headers = {"User-Agent": ua, "Accept": "text/html,*/*"}
    last=None
    for k in range(1, tries+1):
        try:
            if rps: rps.wait()
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code >= 400:
                if k == tries: warn(f"[HTTP][{tag}] {r.url} -> {r.status_code} {r.reason}")
                if 500 <= r.status_code < 600: time.sleep(min(10, 1.2*k)); continue
                return None
            return r.text
        except Exception as e:
            last=e
            if k == tries: warn(f"[HTTP][{tag}] text failed: {e}")
            time.sleep(min(6, 1.0*k))
    return None

def http_get_bytes(url: str, tag="generic", ua=DEFAULT_UA, rps:RPS=None, tries=4, timeout=90):
    if requests is None:
        warn("requests missing; web calls disabled"); return None
    headers = {"User-Agent": ua, "Accept": "*/*"}
    last=None
    for k in range(1, tries+1):
        try:
            if rps: rps.wait()
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code >= 400:
                if k == tries: warn(f"[HTTP][{tag}] {r.url} -> {r.status_code} {r.reason}")
                if 500 <= r.status_code < 600: time.sleep(min(10, 1.2*k)); continue
                return None
            return r.content
        except Exception as e:
            last=e; 
            if k == tries: warn(f"[HTTP][{tag}] bytes failed: {e}")
            time.sleep(min(6, 1.0*k))
    return None

# ---------------- Company universe -----------
def file_age_days(p: str) -> Optional[int]:
    try: return int((time.time()-os.path.getmtime(p))/86400)
    except Exception: return None

def fetch_sec_company_index(rps:RPS) -> pd.DataFrame:
    rows=[]
    for u in ["https://www.sec.gov/files/company_tickers.json",
              "https://www.sec.gov/files/company_tickers_exchange.json"]:
        js = http_get_json(u, tag="sec-index", rps=rps)
        if isinstance(js, dict) and js:
            for _, rec in js.items():
                rows.append({"ticker": normalize_ticker(rec.get("ticker")),
                             "cik": int(rec.get("cik_str") or rec.get("cik") or 0),
                             "title": rec.get("title") or rec.get("name")})
        elif isinstance(js, list) and js:
            for rec in js:
                rows.append({"ticker": normalize_ticker(rec.get("ticker")),
                             "cik": int(rec.get("cik_str") or rec.get("cik") or 0),
                             "title": rec.get("title") or rec.get("name")})
        if rows: break
    return pd.DataFrame(rows).drop_duplicates("ticker").reset_index(drop=True)

def enrich_sic(df: pd.DataFrame, rps:RPS) -> pd.DataFrame:
    df = df.copy()
    if "sic" not in df.columns: df["sic"] = None
    need = df[df["sic"].isna()].copy()
    if need.empty: return df
    log(f"[SEC] Enriching SIC for {len(need)} issuers")
    for i, r in enumerate(need.itertuples(index=False), 1):
        progress_bar(i, len(need), prefix="SIC enrich")
        try:
            cik = int(getattr(r, "cik", 0) or 0)
        except Exception:
            cik = 0
        if not cik: continue
        u = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        js = http_get_json(u, tag="sec-submissions", rps=rps)
        if isinstance(js, dict):
            sic = js.get("sic")
            if sic: df.loc[df["cik"]==cik, "sic"] = str(sic)
    progress_bar(len(need), len(need), prefix="SIC enrich")
    return df

def filter_by_sic(df: pd.DataFrame, allow: List[str], strict=False) -> pd.DataFrame:
    if not allow: return df
    if "sic" not in df.columns: return df
    m = df["sic"].astype(str).isin([str(a) for a in allow])
    return df[m] if strict else df[m | df["sic"].isna()]

def heal_missing_ciks(df: pd.DataFrame, rps:RPS) -> pd.DataFrame:
    """If many rows lack CIK, auto-join SEC index by ticker to fill them."""
    if df["cik"].notna().sum() >= max(10, int(0.2*len(df))):
        return df
    base = fetch_sec_company_index(rps)
    base["ticker"] = base["ticker"].map(normalize_ticker)
    df["ticker"] = df["ticker"].map(normalize_ticker)
    merged = df.drop(columns=[c for c in ["cik","title"] if c in df.columns]).merge(
        base[["ticker","cik","title"]], on="ticker", how="left"
    )
    # Keep any original non-null CIK/title
    if "cik" in df.columns:   merged["cik"]   = merged["cik"].fillna(df["cik"])
    if "title" in df.columns: merged["title"] = merged["title"].fillna(df["title"])
    return merged

def ensure_company_map(path: str, sic_include: Optional[List[str]], refresh_days=30, strict=False, verbose=False) -> pd.DataFrame:
    rps = RPS(2.0)
    age = file_age_days(path) if os.path.exists(path) else None
    rebuild = (age is None) or (age > refresh_days)
    if rebuild:
        log("Building company universe (SEC)")
        base = fetch_sec_company_index(rps)
        base = enrich_sic(base, rps)
        base.to_csv(path, index=False, encoding="utf-8")
        log(f"Company map saved: {path} ({len(base)} rows)")
        df = base
    else:
        if verbose: log(f"Using cached company map ({os.path.basename(path)}, age {age} days)")
        df = pd.read_csv(path, dtype={"cik":"Int64","sic":"object"})
    # schema hardening
    if "ticker" not in df.columns: df["ticker"] = ""
    if "cik" not in df.columns:    df["cik"] = pd.NA
    if "title" not in df.columns:
        if "name" in df.columns: df["title"] = df["name"]
        elif "company" in df.columns: df["title"] = df["company"]
        else: df["title"] = df["ticker"]
    if "sic" not in df.columns: df["sic"] = None

    df["ticker"] = df["ticker"].map(normalize_ticker)

    # Auto-heal missing CIKs if the cached file is sparse
    if df["cik"].isna().sum() > 0:
        before = df["cik"].notna().sum()
        df = heal_missing_ciks(df, rps)
        after  = df["cik"].notna().sum()
        if verbose: log(f"[SEC] Healed CIKs via SEC index: {before} -> {after}")

    if sic_include:
        df = filter_by_sic(df, sic_include, strict=strict)
        if verbose: log(f"SIC filter kept {len(df)} rows")
    return df.reset_index(drop=True)

# ---------------- FDA mining: Download API ----
def nested_get(d: dict, path: str):
    node = d
    for part in path.split("/"):
        if not isinstance(node, dict): return {}
        node = node.get(part, {})
    return node if isinstance(node, dict) else {}

def list_drugsfda_dir():
    """Directory listing fallback — proper bulk domain."""
    base_url = "https://download.open.fda.gov/drug/drugsfda/"
    html = http_get_text(base_url, tag="openfda-dir")
    if not html:
        warn("[OpenFDA DL] directory listing unavailable (download.open.fda.gov)")
        return []
    hrefs = re.findall(r'href="([^"]+\.json\.zip)"', html, flags=re.IGNORECASE)
    urls = []
    for h in hrefs:
        if not re.search(r"drugsfda.*\.json\.zip", h, re.IGNORECASE):
            continue
        if h.startswith("http"): urls.append(h)
        else: urls.append(base_url + h.lstrip("/"))
    urls = sorted(list(dict.fromkeys(urls)))
    log(f"[OpenFDA DL] directory listing: found {len(urls)} zip(s)")
    return urls

def openfda_download_bulk(drugset="drug/drugsfda"):
    """
    Try download.json first; if empty, parse directory listing and fetch zips.
    Returns list of 'results' records across all zips found.
    """
    js = http_get_json("https://api.fda.gov/download.json", tag="openfda-dl-index")
    files = []
    if isinstance(js, dict):
        node = nested_get(js.get("results", {}), drugset)
        files = node.get("current", {}).get("files", [])
    if not files:
        warn(f"[OpenFDA DL] dataset listing not found for {drugset} — falling back to directory listing")
        file_urls = list_drugsfda_dir()
    else:
        file_urls = [f.get("file") for f in files if f.get("file")]

    if not file_urls:
        warn("[OpenFDA DL] no downloadable files discovered")
        return []

    all_recs = []
    for url in file_urls:
        log(f"[OpenFDA DL] fetching {url}")
        content = http_get_bytes(url, tag="openfda-dl")
        if not content: 
            warn(f"[OpenFDA DL] failed: {url}")
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    with zf.open(name) as fh:
                        data = fh.read()
                        try:
                            js2 = json.loads(data)
                            recs = js2.get("results") or []
                        except Exception:
                            recs=[]
                            for line in io.BytesIO(data):
                                line=line.strip()
                                if not line: continue
                                try: recs.append(json.loads(line))
                                except Exception: pass
                        all_recs.extend(recs)
        except Exception as e:
            warn(f"[OpenFDA DL] zip parse failed: {e}")
    log(f"[OpenFDA DL] loaded {len(all_recs)} records")
    return all_recs

def mine_fda_download_only(start: dt.date, end: dt.date, verbose=False) -> pd.DataFrame:
    recs = openfda_download_bulk("drug/drugsfda")
    rows=[]
    if not recs:
        warn("[FDA DL] No bulk records returned")
        return pd.DataFrame()
    years = list(range(start.year, end.year+1))
    for yi, y in enumerate(years, 1):
        ys = dt.date(y,1,1); ye = dt.date(y,12,31)
        if y == end.year: ye = end
        if verbose: log(f"[FDA DL] Filtering bulk for {ys} → {ye}")
        added=0
        for rec in recs:
            sponsor = (rec.get("sponsor_name") or "").strip()
            applno  = rec.get("application_number") or ""
            for p in (rec.get("products") or []):
                ad = p.get("action_date") or p.get("actionDate")
                d  = parse_date_safe(ad)
                if not d or not (ys <= d <= ye): continue
                atype = (p.get("action_type") or p.get("actionType") or "").lower()
                is_approval = ("approval" in atype) or (atype=="")
                product = p.get("brand_name") or p.get("brandName") or ""
                rows.append({
                    "ticker": "",
                    "company": sponsor,
                    "product": product,
                    "catalyst_type": "FDA Approval",
                    "event_date": d,
                    "pdufa_date": d,
                    "approved": 1 if is_approval else 0,
                    "title": f"FDA action: {product} ({atype or 'approval'})",
                    "application_number": applno,
                    "source": "FDA_DL"
                })
                added += 1
        if verbose: log(f"[FDA DL] +{added} rows for {y}")
    df = pd.DataFrame(rows).drop_duplicates(subset=["company","product","event_date"]).reset_index(drop=True)
    return df

# ---------------- FDA mining: Search API (with month fallback) -----
def _mine_openfda_slice(ys: dt.date, ye: dt.date, verbose=False) -> List[dict]:
    base = "https://api.fda.gov/drug/drugsfda.json"
    rows = []
    q = f"products.action_date:[{ys:%Y-%m-%d}+TO+{ye:%Y-%m-%d}]"
    skip = 0
    while True:
        js = http_get_json(base, params={"search": q, "limit": 100, "skip": skip}, tag="openfda-search")
        if not (js and js.get("results")):
            if verbose: warn(f"[FDA] empty/failed at slice {ys}→{ye} skip={skip}")
            break
        res = js.get("results", [])
        rows.extend(res)
        if len(res) < 100: break
        skip += 100
    return rows

def mine_fda_search_only(start: dt.date, end: dt.date, verbose=False) -> pd.DataFrame:
    years = list(range(start.year, end.year+1))
    rows=[]
    for yi, y in enumerate(years, 1):
        ys = dt.date(y,1,1); ye = dt.date(y,12,31)
        if y == end.year: ye = end
        if verbose: log(f"[FDA] Search slice {ys} → {ye}")
        recs = _mine_openfda_slice(ys, ye, verbose=verbose)
        # If yearly slice failed (frequent 500s), fall back to monthly slices
        if not recs:
            if verbose: warn(f"[FDA] Yearly slice failed; trying month-by-month for {y}")
            for m in range(1, 13):
                ms = dt.date(y, m, 1)
                me = dt.date(y, 12, 31) if m==12 else dt.date(y, m+1, 1)-dt.timedelta(days=1)
                if me > ye: me = ye
                r2 = _mine_openfda_slice(ms, me, verbose=verbose)
                if r2: recs.extend(r2)
        captured=0
        for rec in recs:
            sponsor = rec.get("sponsor_name") or ""
            applno  = rec.get("application_number") or ""
            for p in rec.get("products", []):
                adate = p.get("action_date") or p.get("actionDate")
                d = parse_date_safe(adate)
                if not d or not (ys <= d <= ye): continue
                atype = (p.get("action_type") or p.get("actionType") or "").lower()
                is_approval = ("approval" in atype) or (atype=="")
                product = p.get("brand_name") or p.get("brandName") or ""
                rows.append({
                    "ticker": "",
                    "company": sponsor,
                    "product": product,
                    "catalyst_type": "FDA Approval",
                    "event_date": d,
                    "pdufa_date": d,
                    "approved": 1 if is_approval else 0,
                    "title": f"FDA action: {product} ({atype or 'approval'})",
                    "application_number": applno,
                    "source": "FDA"
                })
                captured += 1
        if verbose: log(f"[FDA] +{captured} for {y}")
    df = pd.DataFrame(rows).drop_duplicates(subset=["company","product","event_date"]).reset_index(drop=True)
    return df

# -------- FDA DataFiles fallback helpers --------
def guess_delim(sample: str) -> str:
    if sample.count("|") > sample.count(",") and sample.count("|") >= 2:
        return "|"
    if sample.count("\t") >= 2:
        return "\t"
    return ","

def read_table_from_zip(zip_bytes: bytes, wanted_names: List[str]) -> Optional[pd.DataFrame]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            candidates = [n for n in zf.namelist()
                          if any(w.lower() in n.lower() for w in wanted_names)]
            for name in candidates:
                with zf.open(name) as fh:
                    raw = fh.read()
                    head = raw[:4096].decode("latin-1", errors="ignore")
                    delim = guess_delim(head)
                    df = pd.read_csv(io.BytesIO(raw), sep=delim, engine="python",
                                     dtype=str, encoding="latin-1")
                    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                    return df
    except Exception as e:
        warn(f"[FDA DataFiles] zip parse failed: {e}")
    return None

def extract_fda_download_candidates(page_html: str) -> List[str]:
    """
    Find download links on fda.gov pages. FDA often uses /media/<id>/download
    (no .zip in the href). We also accept explicit *.zip links if present.
    """
    if not page_html:
        return []
    hrefs = re.findall(r'href=[\'"]([^\'"]+)[\'"]', page_html, flags=re.I)
    cands = []
    for h in hrefs:
        if not h:
            continue
        # Explicit ZIP
        if re.search(r'\.zip(\?|$)', h, re.I):
            cands.append(h); continue
        # FDA media endpoint
        if "/media/" in h and "/download" in h:
            cands.append(h)
    # absolutize + dedupe
    out = []
    seen = set()
    for h in cands:
        if not h.startswith("http"):
            h = "https://www.fda.gov" + ("" if h.startswith("/") else "/") + h
        if h not in seen:
            out.append(h); seen.add(h)
    return out

def mine_fda_datafiles_fallback(start: dt.date, end: dt.date, verbose=False) -> pd.DataFrame:
    page_url = "https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files"
    page = http_get_text(page_url, tag="fda-datafiles")
    if not page:
        warn("[FDA DataFiles] page unavailable")
        return pd.DataFrame()
    links = extract_fda_download_candidates(page)
    if verbose: log(f"[FDA DataFiles] found {len(links)} candidate link(s)")
    if not links:
        warn("[FDA DataFiles] no download links discovered on page")
        return pd.DataFrame()

    df_sub = df_prod = None
    for url in links:
        if verbose: log(f"[FDA DataFiles] fetching {url}")
        b = http_get_bytes(url, tag="fda-datafiles", timeout=120)
        if not b:
            continue
        try:
            z_df_sub = read_table_from_zip(b, ["submission", "submissions"])
            z_df_prod = read_table_from_zip(b, ["product", "products"])
        except Exception as e:
            warn(f"[FDA DataFiles] parse failed for {url}: {e}")
            continue
        if z_df_sub is not None: df_sub = z_df_sub
        if z_df_prod is not None: df_prod = z_df_prod
        if df_sub is not None and df_prod is not None:
            break

    if df_sub is None and df_prod is None:
        warn("[FDA DataFiles] could not read submissions/products from any download")
        return pd.DataFrame()

    def col(df, *names):
        for n in names:
            if n and n in df.columns:
                return n
        return None

    rows=[]
    if df_sub is not None:
        df_sub = df_sub.rename(columns={c: c.strip().lower().replace(" ", "_") for c in df_sub.columns})
        c_appl     = col(df_sub, "applno", "appl_no", "appl_number", "application_number")
        c_action   = col(df_sub, "actiontype", "action_type", "submission_status", "action_type_description")
        c_actdate  = col(df_sub, "actiondate", "action_date", "submission_status_date")
        c_sponsor  = col(df_sub, "sponsor_name", "applicant", "applicant_name")
        c_product  = col(df_sub, "productname", "drugname", "proprietary_name", "brand_name")

        prod_map = {}
        if df_prod is not None:
            df_prod = df_prod.rename(columns={c: c.strip().lower().replace(" ", "_") for c in df_prod.columns})
            p_appl = col(df_prod, "applno", "appl_no", "appl_number", "application_number")
            p_name = col(df_prod, "productname", "drugname", "proprietary_name", "brand_name")
            if p_appl and p_name:
                tmp = df_prod[[p_appl, p_name]].dropna().drop_duplicates()
                prod_map = dict(zip(tmp[p_appl].astype(str), tmp[p_name].astype(str)))

        for r in df_sub.itertuples(index=False):
            try:
                appl = getattr(r, c_appl) if c_appl else ""
                actd = parse_date_safe(getattr(r, c_actdate) if c_actdate else None)
                if not actd or not (start <= actd <= end):
                    continue
                at   = str(getattr(r, c_action) if c_action else "").strip().lower()
                sponsor = str(getattr(r, c_sponsor) if c_sponsor else "").strip()
                product = str(getattr(r, c_product) if c_product else "").strip()
                if not product and appl and appl in prod_map:
                    product = prod_map.get(appl, "")

                is_approval = ("approval" in at) or ("tentative" in at)
                rows.append({
                    "ticker": "",
                    "company": sponsor,
                    "product": product,
                    "catalyst_type": "FDA Approval",
                    "event_date": actd,
                    "pdufa_date": actd,
                    "approved": 1 if is_approval else 0,
                    "title": f"FDA action (DataFiles): {product or appl} ({at or 'action'})",
                    "application_number": appl,
                    "source": "FDA_DATAFILES"
                })
            except Exception:
                continue

    df = pd.DataFrame(rows).drop_duplicates(subset=["company","product","event_date"]).reset_index(drop=True)
    if verbose:
        log(f"[FDA DataFiles] built {len(df)} rows from page candidates")
    return df

# -------- FDA local ingestion (optional) --------
def mine_fda_from_local_dir(local_dir: str, start: dt.date, end: dt.date, verbose=False) -> pd.DataFrame:
    """Ingest *.json.zip from a local folder (downloaded elsewhere)."""
    local_dir = os.path.abspath(local_dir or "")
    if not local_dir or not os.path.isdir(local_dir):
        warn(f"[FDA LOCAL] Not a directory: {local_dir}")
        return pd.DataFrame()
    zips = [os.path.join(local_dir, n) for n in os.listdir(local_dir)
            if re.search(r"\.json\.zip$", n, re.I)]
    if not zips:
        warn(f"[FDA LOCAL] No *.json.zip files in {local_dir}")
        return pd.DataFrame()
    rows = []
    if verbose: log(f"[FDA LOCAL] scanning {len(zips)} zip(s)")
    for zi, zp in enumerate(sorted(zips), 1):
        if verbose and (zi % 3 == 1 or zi == len(zips)):
            progress_bar(zi, len(zips), prefix="FDA local")
        try:
            with zipfile.ZipFile(zp) as zf:
                for name in zf.namelist():
                    with zf.open(name) as fh:
                        data = fh.read()
                        # JSON array with "results" OR JSONL
                        try:
                            js = json.loads(data)
                            recs = js.get("results") or []
                        except Exception:
                            recs = []
                            for line in io.BytesIO(data):
                                line = line.strip()
                                if not line: continue
                                try: recs.append(json.loads(line))
                                except Exception: pass
                        for rec in recs:
                            sponsor = (rec.get("sponsor_name") or "").strip()
                            applno  = rec.get("application_number") or ""
                            for p in (rec.get("products") or []):
                                ad = p.get("action_date") or p.get("actionDate")
                                d  = parse_date_safe(ad)
                                if not d or not (start <= d <= end): 
                                    continue
                                atype = (p.get("action_type") or p.get("actionType") or "").lower()
                                product = p.get("brand_name") or p.get("brandName") or ""
                                rows.append({
                                    "ticker": "",
                                    "company": sponsor,
                                    "product": product,
                                    "catalyst_type": "FDA Approval",
                                    "event_date": d,
                                    "pdufa_date": d,
                                    "approved": 1 if ("approval" in atype or atype=="") else 0,
                                    "title": f"FDA action (LOCAL): {product} ({atype or 'approval'})",
                                    "application_number": applno,
                                    "source": "FDA_LOCAL"
                                })
        except Exception as e:
            warn(f"[FDA LOCAL] zip parse failed ({os.path.basename(zp)}): {e}")
    if verbose: log(f"[FDA LOCAL] built {len(rows)} rows")
    return pd.DataFrame(rows).drop_duplicates(subset=["company","product","event_date"]).reset_index(drop=True)

# ---------------- EDGAR miner (best-effort) -----
def _company_name_from_universe_row(r) -> str:
    for attr in ("title","name","company"):
        try:
            v = getattr(r, attr, None)
            if v and str(v).strip(): return str(v)
        except Exception:
            pass
    try:
        return getattr(r, "ticker", "")
    except Exception:
        return ""

def html_to_text(html: str) -> str:
    if not html: return ""
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = ihtml.unescape(text)
    text = re.sub(r"[ \t\r\f]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()

EDGAR_PATTERNS = [
    (r"\bcomplete response letter\b|\b\Wcrl\W", "CRL"),
    (r"\bpdufa\b|\btarget action\b|\baction date\b|\bgoal date\b", "PDUFA"),
    (r"\badvisory committee\b|\badcom\b|\bcommittee vote\b", "ADCOM"),
    (r"\bpriority review\b|\bbreakthrough therapy\b|\bfast track\b|\brtor\b|\brmat\b", "DESIG"),
]

def classify_from_text(txt: str) -> List[str]:
    hits = []
    t = txt.lower()
    for pat, lab in EDGAR_PATTERNS:
        if re.search(pat, t, flags=re.I):
            hits.append(lab)
    return sorted(list(dict.fromkeys(hits)))

def fetch_edgar_doc_text(url: str, max_bytes: int = 1_200_000) -> str:
    b = http_get_bytes(url, tag="edgar-doc", timeout=30)
    if not b: return ""
    if len(b) > max_bytes:
        b = b[:max_bytes]
    url_l = url.lower()
    if any(url_l.endswith(ext) for ext in (".htm",".html",".xhtml",".txt")):
        try:
            return html_to_text(b.decode("utf-8", errors="ignore"))
        except Exception:
            return ""
    try:
        s = b.decode("utf-8", errors="ignore")
        if "<html" in s[:1000].lower():
            return html_to_text(s)
        return s
    except Exception:
        return ""  # PDFs skipped (can add pdfminer if needed)

def mine_edgar_filings(universe: pd.DataFrame, start: dt.date, end: dt.date, fetch_text=False, verbose=False) -> pd.DataFrame:
    if requests is None:
        warn("requests missing; EDGAR mining skipped"); return pd.DataFrame()
    rps = RPS(2.0)

    uni = universe.copy()
    if "title" not in uni.columns:
        if "name" in uni.columns: uni["title"] = uni["name"]
        elif "company" in uni.columns: uni["title"] = uni["company"]
        else: uni["title"] = uni["ticker"]
    if "cik" not in uni.columns: uni["cik"] = pd.NA
    if "ticker" not in uni.columns: uni["ticker"] = ""

    uniq = uni[uni["cik"].notna()][["ticker","cik","title"]].drop_duplicates().reset_index(drop=True)
    if verbose: log(f"[EDGAR] Universe with CIKs: {len(uniq)}")

    rows=[]
    for i, r in enumerate(uniq.itertuples(index=False), 1):
        if i % 25 == 1 or i == len(uniq): progress_bar(i, len(uniq), prefix="EDGAR scan")
        try:
            cik = int(getattr(r, "cik", 0) or 0)
        except Exception:
            cik = 0
        if not cik: continue
        u = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        js = http_get_json(u, tag="sec-submissions", ua=DEFAULT_UA, rps=rps)
        recent = (js or {}).get("filings", {}).get("recent", {})
        forms = recent.get("form", []) or []
        fdt   = recent.get("filingDate", []) or []
        prim  = recent.get("primaryDocDescription", []) or []
        docs  = recent.get("primaryDocument", []) or []
        acc   = recent.get("accessionNumber", []) or []
        n = min(len(forms), len(fdt))
        comp_name = _company_name_from_universe_row(r)
        for k in range(n):
            fd = parse_date_safe(fdt[k]); form = str(forms[k]).upper()
            if not fd or not (start <= fd <= end): continue
            desc = " ".join([str(prim[k] if k<len(prim) else ""), str(docs[k] if k<len(docs) else "")]).lower()
            hit_meta = any(t in desc for t in ["complete response letter"," crl ","advisory committee","adcom","pdufa","action date","goal date"])
            if form in ["8-K","6-K"] and (hit_meta or fetch_text):
                docname = docs[k] if k<len(docs) else ""
                an = str(acc[k] if k<len(acc) else "").replace("-","")
                src_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{an}/{docname}"
                cat = "CRL/AdCom/Press (EDGAR)"
                terms = []
                if fetch_text:
                    txt = fetch_edgar_doc_text(src_url)
                    if txt:
                        labs = classify_from_text(txt)
                        terms = labs
                        if "CRL" in labs: cat = "CRL (EDGAR)"
                        elif "ADCOM" in labs: cat = "AdCom (EDGAR)"
                        elif "PDUFA" in labs: cat = "PDUFA target (EDGAR)"
                        elif "DESIG" in labs: cat = "Reg. designation (EDGAR)"
                rows.append({
                    "ticker": getattr(r,"ticker",""),
                    "company": comp_name,
                    "catalyst_type": cat,
                    "event_date": fd,
                    "title": (prim[k] if k<len(prim) and prim[k] else "")[:256],
                    "source": "EDGAR",
                    "source_url": src_url,
                    "edgar_text_terms": ";".join(terms) if terms else ""
                })
    if not rows and verbose:
        warn("[EDGAR] No rows captured — check CIK coverage in company_map.csv")
    progress_bar(len(uniq), len(uniq), prefix="EDGAR scan")
    return pd.DataFrame(rows)

# ------------- RSS/IR tiny miner -------------
def mine_rss(universe: pd.DataFrame, verbose=False) -> pd.DataFrame:
    if requests is None:
        warn("requests missing; RSS mining skipped"); return pd.DataFrame()
    if "rss" not in universe.columns and "ir" not in universe.columns:
        return pd.DataFrame()
    rows=[]
    uni = universe.copy()
    if "title" not in uni.columns:
        uni["title"] = uni.get("name", uni.get("company", uni.get("ticker","")))
    for i, r in enumerate(uni.itertuples(index=False), 1):
        if i % 50 == 1 or i == len(uni): progress_bar(i, len(uni), prefix="RSS scan")
        ticker = getattr(r,"ticker",""); comp = getattr(r,"title","")
        for col in ["rss","ir"]:
            if col not in uni.columns: continue
            url = str(getattr(r, col, "") or "").strip()
            if not url.startswith("http"): continue
            try:
                resp = requests.get(url, timeout=8)
                if resp.status_code != 200: continue
                t = resp.text.lower()
                if any(k in t for k in ["pdufa","complete response letter","advisory committee","fda approved"]):
                    rows.append({
                        "ticker": ticker, "company": comp, "catalyst_type": "Press (RSS/IR)",
                        "event_date": None, "title": f"{col} hint", "source": col, "source_url": url
                    })
            except Exception:
                continue
    progress_bar(len(uni), len(uni), prefix="RSS scan")
    return pd.DataFrame(rows)

# ------------- Dedupe & Scoring --------------
def dedupe_events(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    for c in ["ticker","catalyst_type","event_date"]:
        if c not in df.columns: df[c] = ""
    df["event_date"] = df["event_date"].apply(parse_date_safe)
    df["dedupe_key"] = df["ticker"].astype(str)+"||"+df["catalyst_type"].astype(str)+"||"+df["event_date"].astype(str)
    picks=[]
    for _, g in df.groupby("dedupe_key", sort=False):
        na = g.isna().sum(axis=1)
        picks.append(g.loc[na.idxmin()])
    out = pd.DataFrame(picks).reset_index(drop=True)
    return out.drop(columns=["dedupe_key"], errors="ignore")

# Odin pre-approval scoring
FEATURES = [
    (r"\bpdufa\b|\btarget action\b|\baction date\b|\bgoal date\b|\btarget date\b", 8.0,  "PDUFA/target-date"),
    (r"\badvisory committee\b|\badcom\b|\bcommittee vote\b",                         10.0, "AdCom scheduled/held"),
    (r"\bphase\s*iii\b|\bphase\s*3\b|\bpivotal\b",                                   10.0, "Phase 3/pivotal mention"),
    (r"\bphase\s*ii\b|\bphase\s*2\b",                                                5.0,  "Phase 2 mention"),
    (r"\bbreakthrough\b|\bpriority review\b|\bfast track\b|\brtor\b|\brmat\b",       5.0,  "BTD/PR/FT/RTOR/RMAT"),
]
OUTCOME_PAT = re.compile(r"\bapproval\b|\bapproved\b|\bcomplete response letter\b|\b\Wcrl\W", re.I)

def preapproval_score_for_row(row: dict) -> Tuple[float, List[str]]:
    t = " ".join([str(row.get(k,"")) for k in ("catalyst_type","title")])
    t = OUTCOME_PAT.sub(" ", t or "")
    base = 55.0
    bonus = 0.0
    fired = []
    for pat, pts, label in FEATURES:
        if re.search(pat, t, flags=re.I):
            bonus += pts
            fired.append(f"{label} (+{pts:.0f})")
    sc = max(0.0, min(99.5, base + bonus))
    return sc, fired

def compute_readable_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    scores=[]; whys=[]; confs=[]
    for r in df.to_dict(orient="records"):
        sc, fired = preapproval_score_for_row(r)
        scores.append(round(sc,1))
        if not fired:
            whys.append("No pre-approval signals detected in this row (baseline only).")
            confs.append("low")
        else:
            whys.append("; ".join(fired))
            confs.append("high" if len(fired)>=3 else ("medium" if len(fired)>=1 else "low"))
    df["Odin_PreApproval_%"] = scores
    df["Odin_Tier"] = pd.cut(df["Odin_PreApproval_%"],
                             bins=[-1,50,70,90,100],
                             labels=["C/D (<50)","B (50–70)","A (70–90)","S (≥90)"],
                             right=False).astype(str)
    df["Odin_Confidence"] = confs
    df["Odin_Why"] = whys
    return df

# ------------- Output writers ---------------
def clean_and_format(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    rename = {}
    for c in df.columns:
        cl=c.lower()
        if cl=="ticker": rename[c]="Ticker"
        elif cl=="company": rename[c]="Company"
        elif cl=="catalyst_type": rename[c]="Catalyst Type"
        elif "event_date" in cl: rename[c]="Date"
        elif "pdufa_date" in cl: rename[c]="PDUFA Date"
        elif "approval_score" in cl or cl=="odin_preapproval_%": rename[c]="Odin_PreApproval_%"
    df = df.rename(columns=rename)
    cols = [c for c in ["Date","PDUFA Date","Ticker","Company","Catalyst Type","title",
                        "Odin_PreApproval_%","Odin_Tier","Odin_Confidence","Odin_Why",
                        "source","source_url","edgar_text_terms"] if c in df.columns]
    others = [c for c in df.columns if c not in cols]
    return df[cols + others]

def write_outputs(df: pd.DataFrame, out_csv: Optional[str], out_xlsx: Optional[str]):
    if out_csv:
        ensure_dir(out_csv)
        df.to_csv(out_csv, index=False, encoding="utf-8")
        log(f"CSV: {out_csv}")
    if out_xlsx:
        try:
            import xlsxwriter
            ensure_dir(out_xlsx)
            with pd.ExcelWriter(out_xlsx, engine="xlsxwriter",
                                engine_kwargs={"options":{"strings_to_urls": False}}) as writer:
                df.to_excel(writer, sheet_name="Catalysts", index=False)
                ws = writer.sheets["Catalysts"]
                for i, col in enumerate(df.columns):
                    try:
                        width = min(50, max(len(col), int(df[col].astype(str).map(len).quantile(0.9))+2))
                    except Exception:
                        width = min(50, len(col)+2)
                    ws.set_column(i, i, width)
            log(f"Excel: {out_xlsx}")
        except Exception as e:
            warn(f"Excel write failed: {e}")

# ------------- Orchestrator -----------------
def run_auto_mine(years: int, universe: pd.DataFrame, fda_mode: str, fetch_edgar_text: bool, verbose: bool, fda_local_dir: str="") -> pd.DataFrame:
    end = TODAY
    start = TODAY - dt.timedelta(days=int(365.25*years))

    step("=== Auto-mine: FDA approvals ===")
    fda = pd.DataFrame()
    fm = (fda_mode or "both").lower()

    if fm == "download":
        fda = mine_fda_download_only(start, end, verbose=verbose)
    elif fm == "search":
        fda = mine_fda_search_only(start, end, verbose=verbose)
    else:  # both
        fda = mine_fda_search_only(start, end, verbose=verbose)
        if fda.empty:
            warn("[FDA] Search returned 0; trying Download API")
            fda = mine_fda_download_only(start, end, verbose=verbose)

    # Optional: local ingestion if network routes fail or explicitly provided
    if (fda is None or fda.empty) and fda_local_dir:
        fda = mine_fda_from_local_dir(fda_local_dir, start, end, verbose=verbose)

    # Final fallback: Drugs@FDA Data Files
    if fda.empty:
        warn("[FDA] Download paths yielded 0 — trying Drugs@FDA Data Files fallback")
        fda = mine_fda_datafiles_fallback(start, end, verbose=verbose)

    step("=== Auto-mine: EDGAR filings (best-effort CRL/AdCom/PR) ===")
    edgar = mine_edgar_filings(universe, start, end, fetch_text=fetch_edgar_text, verbose=verbose)

    step("=== Auto-mine: RSS / IR press (best-effort) ===")
    rss = mine_rss(universe, verbose=verbose)

    parts = [x for x in [fda, edgar, rss] if x is not None and not x.empty]
    if not parts:
        warn("No catalysts captured from miners.")
        return pd.DataFrame()
    cats = pd.concat(parts, axis=0, ignore_index=True)
    return cats

def main():
    ap = argparse.ArgumentParser(description="ODIN All-in-One Miner + Scorer (15y)")
    ap.add_argument("--years", type=int, default=15)
    ap.add_argument("--fda-mode", choices=["download","search","both"], default="both",
                    help="FDA mining mode: search (live), download (bulk JSON), or both")
    ap.add_argument("--fda-local-dir", default="", help="Path with drugsfda *.json.zip (use when bulk host is blocked)")
    ap.add_argument("--openfda-api-key", default=os.environ.get("OPENFDA_API_KEY",""),
                    help="OpenFDA API key (else read from env OPENFDA_API_KEY)")

    ap.add_argument("--company-map-csv", default="company_map.csv")
    ap.add_argument("--sic-include", default="", help="comma SICs")
    ap.add_argument("--sic-strict", action="store_true")
    ap.add_argument("--edgar-fetch-text", action="store_true", help="fetch EDGAR document text to classify CRL/PDUFA/AdCom")

    ap.add_argument("--out-csv", default="odin_pdufa_15y.csv")
    ap.add_argument("--out-xlsx", default="odin_pdufa_15y.xlsx")
    ap.add_argument("--readable-out-csv", default="", help="optional investor-ready CSV with Odin readable scoring")
    ap.add_argument("--readable-out-xlsx", default="", help="optional investor-ready XLSX with Odin readable scoring")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    # Set global OpenFDA key from CLI/env
    global OPENFDA_API_KEY
    OPENFDA_API_KEY = (args.openfda_api_key or os.environ.get("OPENFDA_API_KEY","")).strip()
    if OPENFDA_API_KEY:
        log("[OpenFDA] API key detected — elevated rate limits enabled.")
    else:
        warn("[OpenFDA] No API key detected; using public rate limits.")

    sic_list = [s.strip() for s in args.sic_include.split(",") if s.strip()]
    step("Company universe")
    try:
        universe = ensure_company_map(args.company_map_csv, sic_list, refresh_days=30,
                                      strict=args.sic_strict, verbose=args.verbose)
    except Exception as e:
        err(f"Company universe failed: {e}")
        universe = pd.DataFrame(columns=["ticker","cik","title","sic"])

    step("Run miners")
    cats = run_auto_mine(args.years, universe, fda_mode=args.fda_mode,
                         fetch_edgar_text=args.edgar_fetch_text,
                         verbose=args.verbose, fda_local_dir=args.fda_local_dir)
    if cats.empty:
        err("Auto-mine produced no rows."); return

    step("Deduplicate & readable pre-approval scoring")
    cats = dedupe_events(cats)
    readable = compute_readable_scores(cats)

    step("Final formatting")
    out = clean_and_format(readable)

    write_outputs(out, os.path.abspath(args.out_csv) if args.out_csv else None,
                      os.path.abspath(args.out_xlsx) if args.out_xlsx else None)

    r_csv = args.readable_out_csv.strip()
    r_xls = args.readable_out_xlsx.strip()
    if r_csv or r_xls:
        write_outputs(out, os.path.abspath(r_csv) if r_csv else None,
                          os.path.abspath(r_xls) if r_xls else None)

    step("Done")
    fda_ct   = int((out.get('source', pd.Series(dtype=str)).astype(str).str.contains('FDA')).sum()) if 'source' in out.columns else 0
    edgar_ct = int((out.get('source', pd.Series(dtype=str)).astype(str).str.contains('EDGAR')).sum()) if 'source' in out.columns else 0
    log(f"Rows: {len(out)} | FDA-like: {fda_ct} | EDGAR-like: {edgar_ct}")

if __name__ == "__main__":
    main()
