#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
edgar_miner.py — Mine SEC EDGAR filings and press releases for phrases,
scoped to industries by SIC code. Built for large runs (thousands of docs):
disk-cached, resumable, rate-limit compliant.

Subcommands
-----------
universe   Build the list of SEC filers for one or more SIC codes -> CSV.
scan       Download filings (incl. 8-K/6-K press-release exhibits) and
           phrase-search them locally. Exact phrases + regex. Cached/resumable.
fts        EDGAR server-side full-text search (2001+, exact phrases only),
           filtered by SIC. Fast reconnaissance before a heavy scan.

Requirements:  pip install requests beautifulsoup4 lxml
SEC etiquette: export SEC_USER_AGENT="Your Name you@example.com"  (required;
               SEC blocks anonymous scrapers), <=10 req/s (default here: 6).

Examples
--------
  python edgar_miner.py universe --sic 2834 2836 8731
  python edgar_miner.py scan --sic 2836 --phrases phrases.txt --forms 8-K 10-K --years 2
  python edgar_miner.py scan --ciks 1862150 1650648 --phrase "complete response letter"
  python edgar_miner.py fts  --sic 2834 2836 --phrase "complete response letter" --forms 8-K --years 2
"""

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SEC_WWW = "https://www.sec.gov"
BROWSE_URL = f"{SEC_WWW}/cgi-bin/browse-edgar"
ARCHIVES = f"{SEC_WWW}/Archives/edgar/data"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_BASE = "https://data.sec.gov/submissions/"
FTS_URL = "https://efts.sec.gov/LATEST/search-index"

# --------------------------------------------------------------------------- #
# Industry scope: SIC codes                                                    #
# --------------------------------------------------------------------------- #
# Measured 2026-07-16 against EDGAR FTS: of 100 8-Ks containing "topline data" YTD,
# these five SICs account for 96 (2834:57, 2836:29, 2833:5, 2835:3, 8731:2). The
# remaining 4% are conglomerates/medtech filing under other codes. Use --sic-preset
# biotech rather than retyping these; a forgotten code is a silent coverage hole.
SIC_PRESETS = {
    # the readout-bearing core. This is what you want for phase readouts.
    "biotech": ["2834", "2836", "8731", "2835", "2833"],
    # narrowest: drug developers only. Faster, ~86% of readout 8-Ks.
    "pharma":  ["2834", "2836"],
    # adds devices + lab tools. Broader, noisier; only if chasing device catalysts.
    "life-sciences": ["2834", "2836", "8731", "2835", "2833", "3841", "3826", "3845"],
}
SIC_NAMES = {
    "2833": "Medicinal Chemicals & Botanical Products",
    "2834": "Pharmaceutical Preparations",
    "2835": "In Vitro & In Vivo Diagnostic Substances",
    "2836": "Biological Products (No Diagnostic Substances)",
    "3826": "Laboratory Analytical Instruments",
    "3841": "Surgical & Medical Instruments & Apparatus",
    "3845": "Electromedical & Electrotherapeutic Apparatus",
    "8731": "Services-Commercial Physical & Biological Research",
}

TEXT_EXTS = (".htm", ".html", ".txt")
OWNERSHIP_FORMS = {"3", "3/A", "4", "4/A", "5", "5/A", "144", "144/A"}
EXHIBIT_BASE_FORMS = {"8-K", "6-K"}  # forms whose EX-99.* exhibits are press releases

HIT_COLUMNS = ["sic", "cik", "ticker", "company", "form", "filing_date",
               "accession", "document", "doc_type", "phrase", "match_count",
               "context", "url"]


# --------------------------------------------------------------------------- #
# HTTP plumbing: global rate limiter + retrying session                        #
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Thread-safe global limiter: at most `rps` requests per second."""

    def __init__(self, rps: float):
        self._lock = threading.Lock()
        self._interval = 1.0 / max(0.1, rps)
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            sleep_for = max(0.0, self._next - now)
            self._next = max(now, self._next) + self._interval
        if sleep_for > 0:
            time.sleep(sleep_for)


class Http:
    def __init__(self, user_agent: str, rps: float):
        self.rl = RateLimiter(rps)
        self.sess = requests.Session()
        self.sess.headers.update({"User-Agent": user_agent,
                                  "Accept-Encoding": "gzip, deflate"})
        adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
        self.sess.mount("https://", adapter)
        self.requests_made = 0
        self._count_lock = threading.Lock()

    def get(self, url, params=None, ok404=False, timeout=45):
        last_exc = None
        for attempt in range(7):
            self.rl.wait()
            with self._count_lock:
                self.requests_made += 1
            try:
                r = self.sess.get(url, params=params, timeout=timeout)
            except requests.RequestException as e:
                last_exc = e
                time.sleep(min(30, 2 ** attempt) + random.random())
                continue
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                if ok404:
                    return None
                raise RuntimeError(f"404 for {r.url}")
            if r.status_code in (403, 429, 500, 502, 503, 504):
                time.sleep(min(60, 2 ** attempt) + random.random())
                continue
            r.raise_for_status()
        if ok404:
            return None
        raise RuntimeError(f"Giving up on {url} after retries ({last_exc})")

    def get_json(self, url, params=None, ok404=False):
        r = self.get(url, params=params, ok404=ok404)
        return None if r is None else r.json()


# --------------------------------------------------------------------------- #
# Universe: companies by SIC code (via EDGAR company browse)                   #
# --------------------------------------------------------------------------- #

def parse_browse_page(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="tableFile2")
    rows = []
    if not table:
        return rows
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            a = tds[0].find("a")
            if not a:
                continue
            cik_txt = a.get_text(strip=True)
            if not cik_txt.isdigit():
                continue
            name = tds[1].get_text(" ", strip=True)
            state = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            rows.append((int(cik_txt), name, state))
    return rows


def build_universe(http, sic_codes, verbose=True):
    """Return {cik: {"name":..., "sic":..., "state":...}} for all filers under the SICs.
    Includes delisted / defunct filers (EDGAR keeps them), which is what you want
    to avoid survivorship bias."""
    companies = {}
    for sic in sic_codes:
        start, page_rows = 0, None
        while True:
            r = http.get(BROWSE_URL, params=dict(
                action="getcompany", SIC=str(sic), owner="include",
                count=100, start=start))
            page_rows = parse_browse_page(r.text)
            for cik, name, state in page_rows:
                companies.setdefault(cik, {"name": name, "sic": str(sic),
                                           "state": state})
            if verbose:
                print(f"  SIC {sic}: {start + len(page_rows)} filers listed...",
                      end="\r", flush=True)
            if len(page_rows) < 100:
                break
            start += 100
        if verbose:
            print(f"  SIC {sic}: done ({sum(1 for v in companies.values() if v['sic'] == str(sic))} filers)     ")
    return companies


def save_universe(companies, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cik", "name", "sic", "state"])
        for cik in sorted(companies):
            c = companies[cik]
            w.writerow([cik, c["name"], c["sic"], c["state"]])


def load_universe(path):
    companies = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            companies[int(row["cik"])] = {"name": row.get("name", ""),
                                          "sic": row.get("sic", ""),
                                          "state": row.get("state", "")}
    return companies


# --------------------------------------------------------------------------- #
# Phrases                                                                      #
# --------------------------------------------------------------------------- #

def compile_phrase(line):
    """Plain lines: case-insensitive, whitespace-flexible exact phrase.
    Lines starting with `re:` are treated as raw regex (case-insensitive)."""
    line = line.strip()
    if line.lower().startswith("re:"):
        return line, re.compile(line[3:].strip(), re.IGNORECASE)
    tokens = [re.escape(t) for t in re.split(r"\s+", line) if t]
    pat = r"\s+".join(tokens)
    if line[0].isalnum():
        pat = r"\b" + pat
    if line[-1].isalnum():
        pat = pat + r"\b"
    return line, re.compile(pat, re.IGNORECASE)


def load_phrases(args):
    lines = []
    if getattr(args, "phrases", None):
        with open(args.phrases, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    lines.append(ln)
    for p in (getattr(args, "phrase", None) or []):
        lines.append(p.strip())
    if not lines:
        sys.exit("No phrases given. Use --phrases FILE and/or --phrase '...' (repeatable).")
    return [compile_phrase(ln) for ln in lines]


def phrases_hash(patterns):
    h = hashlib.sha1("\n".join(lbl for lbl, _ in patterns).encode("utf-8"))
    return h.hexdigest()[:12]


# --------------------------------------------------------------------------- #
# Text extraction + search                                                     #
# --------------------------------------------------------------------------- #

def to_text(raw_bytes):
    txt = raw_bytes.decode("utf-8", errors="replace")
    if "<" in txt[:2000]:
        soup = BeautifulSoup(txt, "lxml")
        for t in soup(["script", "style"]):
            t.decompose()
        txt = soup.get_text(" ")
    return re.sub(r"\s+", " ", txt)


def search_text(text, patterns, ctx_chars, max_snippets=2):
    hits = []
    for label, rx in patterns:
        matches = list(rx.finditer(text))
        if not matches:
            continue
        snips = []
        for m in matches[:max_snippets]:
            a = max(0, m.start() - ctx_chars)
            b = min(len(text), m.end() + ctx_chars)
            snips.append("..." + text[a:b].strip() + "...")
        hits.append((label, len(matches), "  ||  ".join(snips)))
    return hits


# --------------------------------------------------------------------------- #
# Filings per company (submissions API) + exhibit discovery                    #
# --------------------------------------------------------------------------- #

def _iter_recs(d):
    accns = d.get("accessionNumber", [])
    dates = d.get("filingDate", [])
    forms = d.get("form", [])
    prims = d.get("primaryDocument", [""] * len(accns))
    for i in range(len(accns)):
        yield {"accn": accns[i], "date": dates[i], "form": forms[i],
               "doc": prims[i] if i < len(prims) else ""}


def base_form(form):
    return form.split("/")[0].strip().upper()


def form_ok(form, include_forms, include_ownership):
    f = form.strip().upper()
    if include_forms:
        return any(f == g or f.startswith(g + "/") for g in include_forms)
    if not include_ownership and f in OWNERSHIP_FORMS:
        return False
    return True


def parse_filing_index(html):
    """Parse {accession}-index.htm -> [(filename, type), ...]."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for table in soup.find_all("table", class_="tableFile"):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 4:
                a = tds[2].find("a")
                if not a or not a.get("href"):
                    continue
                fname = a["href"].split("/")[-1]
                ftype = tds[3].get_text(strip=True)
                out.append((fname, ftype))
    return out


def company_jobs(http, cik, uinfo, start_date, end_date, include_forms,
                 include_ownership, want_exhibits):
    """Fetch the company's filing history and return (meta, [job dicts])."""
    j = http.get_json(SUBMISSIONS_URL.format(cik=cik), ok404=True)
    if j is None:
        return None, []
    meta = {
        "cik": cik,
        "name": j.get("name") or uinfo.get("name", ""),
        "sic": (j.get("sic") or uinfo.get("sic", "")).strip(),
        "ticker": ";".join(j.get("tickers") or []),
    }
    recs = list(_iter_recs(j.get("filings", {}).get("recent", {})))
    # Page back through older submission files if the window extends past "recent"
    oldest = recs[-1]["date"] if recs else None
    if oldest and oldest > start_date:
        for extra in j.get("filings", {}).get("files", []) or []:
            if extra.get("filingTo", "") >= start_date:
                jj = http.get_json(SUBMISSIONS_BASE + extra["name"], ok404=True)
                if jj:
                    recs.extend(_iter_recs(jj))

    jobs = []
    for r in recs:
        if not (start_date <= r["date"] <= end_date):
            continue
        if not form_ok(r["form"], include_forms, include_ownership):
            continue
        accn = r["accn"]
        docs = []
        primary = r["doc"] or (accn + ".txt")
        if primary.lower().endswith(TEXT_EXTS):
            docs.append((primary, "primary"))
        if want_exhibits and base_form(r["form"]) in EXHIBIT_BASE_FORMS:
            nodash = accn.replace("-", "")
            idx_url = f"{ARCHIVES}/{cik}/{nodash}/{accn}-index.htm"
            idx = http.get(idx_url, ok404=True)
            if idx is not None:
                for fname, ftype in parse_filing_index(idx.text):
                    if (ftype.upper().startswith("EX-99")
                            and fname.lower().endswith(TEXT_EXTS)
                            and fname != primary):
                        docs.append((fname, ftype.upper()))
        for fname, dtype in docs:
            jobs.append({"cik": cik, "accn": accn, "form": r["form"],
                         "date": r["date"], "fname": fname, "dtype": dtype,
                         **meta})
    return meta, jobs


# --------------------------------------------------------------------------- #
# Document cache + processing                                                  #
# --------------------------------------------------------------------------- #

def doc_cache_path(cache_dir, cik, accn, fname):
    nodash = accn.replace("-", "")
    return os.path.join(cache_dir, "docs", str(cik), nodash, fname + ".gz")


def fetch_doc(http, cache_dir, cik, accn, fname):
    """Return (bytes, was_cached) or (None, False) if unavailable."""
    p = doc_cache_path(cache_dir, cik, accn, fname)
    if os.path.exists(p):
        try:
            with gzip.open(p, "rb") as f:
                return f.read(), True
        except OSError:
            pass  # corrupt cache entry -> refetch
    nodash = accn.replace("-", "")
    url = f"{ARCHIVES}/{cik}/{nodash}/{fname}"
    r = http.get(url, ok404=True)
    if r is None:
        return None, False
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with gzip.open(tmp, "wb") as f:
        f.write(r.content)
    os.replace(tmp, p)
    return r.content, False


def doc_url(cik, accn, fname):
    return f"{ARCHIVES}/{cik}/{accn.replace('-', '')}/{fname}"


def process_doc(http, cache_dir, job, patterns, ctx_chars, max_bytes):
    raw, cached = fetch_doc(http, cache_dir, job["cik"], job["accn"], job["fname"])
    if raw is None:
        return job, [], cached, "missing"
    if len(raw) > max_bytes:
        return job, [], cached, "skipped_large"
    text = to_text(raw)
    rows = []
    for label, count, context in search_text(text, patterns, ctx_chars):
        rows.append([job["sic"], job["cik"], job["ticker"], job["name"],
                     job["form"], job["date"], job["accn"], job["fname"],
                     job["dtype"], label, count, context,
                     doc_url(job["cik"], job["accn"], job["fname"])])
    return job, rows, cached, "ok"


# --------------------------------------------------------------------------- #
# Shared helpers                                                               #
# --------------------------------------------------------------------------- #

def resolve_dates(args):
    end = args.end_date or dt.date.today().isoformat()
    if args.start_date:
        start = args.start_date
    else:
        days = int(round(365.25 * args.years))
        start = (dt.date.fromisoformat(end) - dt.timedelta(days=days)).isoformat()
    return start, end


def resolve_user_agent(args):
    ua = args.user_agent or os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        sys.exit('SEC requires an identifying User-Agent.\n'
                 'Set it once:  export SEC_USER_AGENT="Your Name you@example.com"\n'
                 'or pass --user-agent "Your Name you@example.com"')
    return ua


def get_universe(http, args, out_dir):
    if getattr(args, "ciks", None):
        return {int(c): {"name": "", "sic": "", "state": ""} for c in args.ciks}
    if getattr(args, "universe", None):
        return load_universe(args.universe)
    if getattr(args, "sic", None):
        print(f"Building universe for SIC {' '.join(map(str, args.sic))} ...")
        companies = build_universe(http, args.sic)
        path = os.path.join(out_dir, "universe_" + "_".join(map(str, args.sic)) + ".csv")
        save_universe(companies, path)
        print(f"Universe: {len(companies)} filers -> {path}")
        return companies
    sys.exit("Provide --sic CODES, --universe FILE, or --ciks CIK [CIK ...]")


def open_hits_csv(path):
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if not exists:
        w.writerow(HIT_COLUMNS)
        f.flush()
    return f, w


# --------------------------------------------------------------------------- #
# Command: universe                                                            #
# --------------------------------------------------------------------------- #

def cmd_universe(args):
    if not args.sic:
        sys.exit("Provide --sic CODES or --sic-preset biotech")
    http = Http(resolve_user_agent(args), args.rps)
    os.makedirs(args.out_dir, exist_ok=True)
    companies = build_universe(http, args.sic)
    path = os.path.join(args.out_dir,
                        "universe_" + "_".join(map(str, args.sic)) + ".csv")
    save_universe(companies, path)
    print(f"\n{len(companies)} filers across SIC {args.sic} -> {path}")


# --------------------------------------------------------------------------- #
# Command: scan (bulk download + local phrase search)                          #
# --------------------------------------------------------------------------- #

def cmd_scan(args):
    ua = resolve_user_agent(args)
    http = Http(ua, args.rps)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)

    patterns = load_phrases(args)
    ph_hash = phrases_hash(patterns)
    start_date, end_date = resolve_dates(args)
    include_forms = [f.upper() for f in args.forms] if args.forms else None
    max_bytes = int(args.max_doc_mb * 1024 * 1024)

    universe = get_universe(http, args, args.out_dir)
    ciks = sorted(universe)
    if args.limit_companies:
        ciks = ciks[:args.limit_companies]

    out_path = args.out or os.path.join(args.out_dir, "hits.csv")
    scanned_log = out_path + ".scanned"
    scanned = set()
    if os.path.exists(scanned_log):
        with open(scanned_log, encoding="utf-8") as f:
            for ln in f:
                parts = ln.strip().split(" ", 1)
                if len(parts) == 2 and parts[0] == ph_hash:
                    scanned.add(parts[1])

    print(f"Scan window {start_date} .. {end_date} | companies: {len(ciks)} | "
          f"forms: {include_forms or 'ALL (minus ownership forms 3/4/5/144)'} | "
          f"phrases: {len(patterns)} | already scanned: {len(scanned)} docs")

    # ---- Phase 1: enumerate filings & documents ---------------------------- #
    jobs, missing_subs = [], 0
    print("Phase 1/2: enumerating filings ...")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(company_jobs, http, cik, universe[cik], start_date,
                          end_date, include_forms, args.include_ownership,
                          not args.no_exhibits): cik for cik in ciks}
        done = 0
        try:
            for fut in as_completed(futs):
                meta, cjobs = fut.result()
                if meta is None:
                    missing_subs += 1
                jobs.extend(cjobs)
                done += 1
                if done % 10 == 0 or done == len(ciks):
                    print(f"  companies {done}/{len(ciks)} | docs queued: {len(jobs)}",
                          end="\r", flush=True)
        except KeyboardInterrupt:
            print("\nInterrupted during enumeration; re-run to resume (cache persists).")
            return
    print()

    fresh_jobs = [j for j in jobs
                  if f"{j['cik']}/{j['accn']}/{j['fname']}" not in scanned]
    cached_ct = sum(1 for j in fresh_jobs if os.path.exists(
        doc_cache_path(args.cache_dir, j["cik"], j["accn"], j["fname"])))
    to_fetch = len(fresh_jobs) - cached_ct
    eta_min = to_fetch / max(args.rps, 0.1) / 60
    print(f"Docs total: {len(jobs)} | to scan now: {len(fresh_jobs)} "
          f"(cached: {cached_ct}, to download: {to_fetch}) | "
          f"rough download ETA at {args.rps} req/s: ~{eta_min:.0f} min")
    if missing_subs:
        print(f"note: {missing_subs} CIKs had no submissions data (very old/never-migrated filers)")

    # ---- Phase 2: fetch + search ------------------------------------------- #
    hits_f, hits_w = open_hits_csv(out_path)
    scan_f = open(scanned_log, "a", encoding="utf-8")
    n_hits = n_done = n_large = 0
    print("Phase 2/2: downloading + searching ...")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(process_doc, http, args.cache_dir, j, patterns,
                          args.context_chars, max_bytes) for j in fresh_jobs]
        try:
            for fut in as_completed(futs):
                job, rows, _cached, status = fut.result()
                n_done += 1
                if status == "skipped_large":
                    n_large += 1
                for row in rows:
                    hits_w.writerow(row)
                    n_hits += 1
                hits_f.flush()
                scan_f.write(f"{ph_hash} {job['cik']}/{job['accn']}/{job['fname']}\n")
                scan_f.flush()
                if n_done % 20 == 0 or rows or n_done == len(fresh_jobs):
                    print(f"  docs {n_done}/{len(fresh_jobs)} | hit rows: {n_hits}",
                          end="\r", flush=True)
        except KeyboardInterrupt:
            print(f"\nInterrupted. Progress saved ({n_done} docs). "
                  f"Re-run the same command to resume.")
        finally:
            hits_f.close()
            scan_f.close()
    print(f"\nDone. {n_done} docs scanned, {n_hits} hit rows "
          f"({n_large} skipped as > {args.max_doc_mb} MB), "
          f"{http.requests_made} HTTP requests.\nHits -> {out_path}")


# --------------------------------------------------------------------------- #
# Command: fts (EDGAR full-text search, server-side)                           #
# --------------------------------------------------------------------------- #

def _fts_total(j):
    t = j.get("hits", {}).get("total", {})
    return t.get("value", 0), t.get("relation", "eq")


def _month_windows(start, end):
    s = dt.date.fromisoformat(start)
    e = dt.date.fromisoformat(end)
    cur = s
    while cur <= e:
        nxt = (cur.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        yield cur.isoformat(), min(e, nxt - dt.timedelta(days=1)).isoformat()
        cur = nxt


def _fts_pages(http, phrase, forms, start, end):
    """Yield hit dicts, transparently splitting date windows if a window
    saturates the API's 10,000-result cap."""
    params = {"q": f'"{phrase}"', "startdt": start, "enddt": end}
    if forms:
        params["forms"] = ",".join(forms)
    j = http.get_json(FTS_URL, params=dict(params, **{"from": 0}))
    total, rel = _fts_total(j)
    if (total >= 10000 or rel != "eq") and start != end:
        for s, e in _month_windows(start, end):
            yield from _fts_pages(http, phrase, forms, s, e)
        return
    frm = 0
    while frm < min(total, 10000):
        if frm > 0:
            j = http.get_json(FTS_URL, params=dict(params, **{"from": frm}))
        hits = j.get("hits", {}).get("hits", [])
        if not hits:
            break
        yield from hits
        frm += len(hits)


def cmd_fts(args):
    http = Http(resolve_user_agent(args), args.rps)
    os.makedirs(args.out_dir, exist_ok=True)
    patterns = load_phrases(args)
    for lbl, _ in patterns:
        if lbl.lower().startswith("re:"):
            sys.exit(f"fts mode is exact-phrase only (server-side); regex line not supported: {lbl}\n"
                     f"Use `scan` for regex patterns.")
    start_date, end_date = resolve_dates(args)
    forms = [f.upper() for f in args.forms] if args.forms else None
    sic_set = {str(s) for s in (args.sic or [])}
    cik_set = set(load_universe(args.universe)) if args.universe else set()
    if not sic_set and not cik_set:
        sys.exit("fts needs --sic CODES (recommended) and/or --universe FILE to scope an industry.")

    out_path = args.out or os.path.join(args.out_dir, "fts_hits.csv")
    exists = os.path.exists(out_path) and os.path.getsize(out_path) > 0
    f = open(out_path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if not exists:
        w.writerow(["sic", "cik", "company", "form", "file_type", "filing_date",
                    "accession", "document", "phrase", "url"])

    seen = set()
    kept = dropped = 0
    for label, _rx in patterns:
        print(f'fts: "{label}"  [{start_date}..{end_date}]  forms={forms or "ALL"}')
        for h in _fts_pages(http, label, forms, start_date, end_date):
            src = h.get("_source", {})
            _id = h.get("_id", ":")
            accn, _, fname = _id.partition(":")
            ciks = [int(c) for c in src.get("ciks", []) if str(c).strip().isdigit()]
            sics = [str(s) for s in (src.get("sics") or [])]
            keep = (sic_set and any(s in sic_set for s in sics)) or \
                   (cik_set and any(c in cik_set for c in ciks))
            if not keep:
                dropped += 1
                continue
            cik = ciks[0] if ciks else 0
            key = (accn, fname, label)
            if key in seen:
                continue
            seen.add(key)
            kept += 1
            w.writerow([";".join(sics), cik,
                        (src.get("display_names") or [""])[0],
                        ";".join(src.get("root_forms") or []) or src.get("form", ""),
                        src.get("file_type", ""), src.get("file_date", ""),
                        accn, fname, label, doc_url(cik, accn, fname)])
            f.flush()
    f.close()
    print(f"Done. {kept} in-industry hits kept, {dropped} out-of-industry hits filtered, "
          f"{http.requests_made} HTTP requests.\nHits -> {out_path}")


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def add_common(p):
    p.add_argument("--user-agent", help='Identifying UA per SEC policy, e.g. "Name you@example.com". '
                                        "Defaults to $SEC_USER_AGENT.")
    p.add_argument("--rps", type=float, default=6.0, help="Max requests/sec (SEC cap is 10; default 6)")
    p.add_argument("--out-dir", default="out", help="Output directory (default ./out)")


def add_scope(p):
    p.add_argument("--sic", nargs="+", help="One or more SIC codes, e.g. 2834 2836 8731")
    p.add_argument("--sic-preset", choices=sorted(SIC_PRESETS),
                   help="Named SIC set instead of --sic. 'biotech' = 2834 2836 8731 2835 2833 "
                        "(96%% of readout-bearing 8-Ks).")
    p.add_argument("--universe", help="Reuse a previously built universe CSV")


def add_window(p):
    p.add_argument("--years", type=float, default=2.0, help="Lookback window in years (default 2)")
    p.add_argument("--start-date", help="YYYY-MM-DD (overrides --years)")
    p.add_argument("--end-date", help="YYYY-MM-DD (default today)")


def add_phrases(p):
    p.add_argument("--phrases", help="File with one phrase per line; lines starting "
                                     "with 're:' are regex; '#' comments allowed")
    p.add_argument("--phrase", action="append", help="Inline phrase (repeatable)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pu = sub.add_parser("universe", help="Build company universe by SIC code")
    pu.add_argument("--sic", nargs="+")
    pu.add_argument("--sic-preset", choices=sorted(SIC_PRESETS),
                    help="Named SIC set, e.g. biotech")
    add_common(pu)
    pu.set_defaults(func=cmd_universe)

    ps = sub.add_parser("scan", help="Download filings and phrase-search locally (regex-capable)")
    add_scope(ps)
    ps.add_argument("--ciks", nargs="+", type=int, help="Scan specific CIKs (bypasses universe)")
    add_window(ps)
    add_phrases(ps)
    ps.add_argument("--forms", nargs="+", help="Filing types, e.g. 8-K 10-K 10-Q S-1 "
                                               "(amendments like 10-K/A included automatically). "
                                               "Omit to scan ALL filings except ownership forms.")
    ps.add_argument("--include-ownership", action="store_true",
                    help="Also scan Forms 3/4/5/144 when no --forms filter is set")
    ps.add_argument("--no-exhibits", action="store_true",
                    help="Skip 8-K/6-K press-release exhibits (EX-99.*)")
    ps.add_argument("--limit-companies", type=int, help="Cap number of companies (testing)")
    ps.add_argument("--max-doc-mb", type=float, default=40.0, help="Skip documents larger than this")
    ps.add_argument("--context-chars", type=int, default=240, help="Context chars around each match")
    ps.add_argument("--workers", type=int, default=6, help="Parallel workers (throughput is still rps-capped)")
    ps.add_argument("--cache-dir", default="edgar_cache", help="Document cache directory")
    ps.add_argument("--out", help="Hits CSV path (default OUT_DIR/hits.csv)")
    add_common(ps)
    ps.set_defaults(func=cmd_scan)

    pf = sub.add_parser("fts", help="EDGAR full-text search (2001+, exact phrases), SIC-filtered")
    add_scope(pf)
    add_window(pf)
    add_phrases(pf)
    pf.add_argument("--forms", nargs="+", help="Filing types filter, e.g. 8-K 10-K")
    pf.add_argument("--out", help="Hits CSV path (default OUT_DIR/fts_hits.csv)")
    add_common(pf)
    pf.set_defaults(func=cmd_fts)

    args = ap.parse_args()
    # Resolve --sic-preset into --sic before any command reads it. Done once, here, so every
    # subcommand (universe/scan/fts) sees the same expansion and they cannot drift apart.
    preset = getattr(args, "sic_preset", None)
    if preset:
        if getattr(args, "sic", None):
            sys.exit("Use --sic OR --sic-preset, not both.")
        args.sic = list(SIC_PRESETS[preset])
        print(f"SIC preset '{preset}': " + ", ".join(f"{c} ({SIC_NAMES.get(c, '?')})" for c in args.sic))
    args.func(args)


if __name__ == "__main__":
    main()
