# -*- coding: utf-8 -*-
"""gsc_index_status.py -- what Google has actually indexed, read from Search Console every rebuild (2026-11-20).

Until now `_google_indexed.json` was kept by hand (3 paths, seeded Nov 11), so the daily "request indexing" list kept
offering pages Google already had, and nobody could say WHICH kinds of page sit in the 1,612 "Discovered - currently
not indexed". This asks Google, with the same service account that submits the sitemap (GSC_SERVICE_ACCOUNT_JSON):

  1. URL Inspection API, read-only (2,000 a day per property; this uses at most --max per run, default 150):
     today's request-list pages first, then sitemap pages never inspected (round-robin across sections, so every kind
     of page is sampled), then the oldest inspections. Writes `_google_index_status.json`
     {path: {state, verdict, crawled, checked}} and rewrites `_google_indexed.json` from it, so
     build_google_request_list.py skips what Google already indexed.
  2. Search Analytics: daily clicks, impressions and position for the last 90 days -> `_google_search_stats.json`.

Prints a per-section table and writes it to the job summary. Advisory: no credential, or any API error, prints why and
exits 0, because Google's state must never block a deploy. Nothing is submitted or changed in Search Console.

    python gsc_index_status.py [--max 150]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STATUS = os.path.join(HERE, "_google_index_status.json")
INDEXED = os.path.join(HERE, "_google_indexed.json")
STATS = os.path.join(HERE, "_google_search_stats.json")
REQ_LIST = os.path.join(HERE, "_google_request_indexing.txt")
BASE = "https://www.pdufa.bio"
# Each inspection takes ~6 s, so 150 in a row cost 16 minutes of every rebuild (run 578, 2026-11-27). Inspect in
# parallel (the API allows 600 a minute) and stop at a time budget; the stalest pages come first, so the rest go next run.
WORKERS = int(os.environ.get("GSC_WORKERS", "6"))
BUDGET_S = float(os.environ.get("GSC_BUDGET_S", "240"))
sys.path.insert(0, HERE)


def section(path):
    for pre, name in (("/pdufa/", "events"), ("/adcomm/", "events"), ("/fda-application/", "events"),
                      ("/fda-decision/", "decisions"), ("/crl", "decisions"), ("/fda-approvals", "decisions"),
                      ("/drug/", "drugs"), ("/ticker/", "tickers")):
        if path.startswith(pre):
            return name
    return "hubs"


def load(p, default):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def pick(sitemap_paths, status, today, n):
    """Request list first (re-checked daily), then never-inspected round-robin by section, then oldest."""
    out = []
    try:
        req = [ln.split("\t")[0].strip()[len(BASE):] or "/" for ln in io.open(REQ_LIST, encoding="utf-8")
               if ln.startswith(BASE)]
    except Exception:  # noqa: BLE001
        req = []
    for p in req:
        if p in sitemap_paths and status.get(p, {}).get("checked") != today and p not in out:
            out.append(p)
    fresh = {}
    for p in sorted(sitemap_paths):
        if p not in status:
            fresh.setdefault(section(p), []).append(p)
    while len(out) < n and any(fresh.values()):
        for name in sorted(fresh):
            if fresh[name] and len(out) < n:
                out.append(fresh[name].pop(0))
    week_ago = (dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat()
    for p in sorted((p for p in sitemap_paths if p in status and status[p].get("checked", "") < week_ago),
                    key=lambda p: status[p].get("checked", "")):
        if len(out) >= n:
            break
        if p not in out:
            out.append(p)
    return out[:n]


def table(status, sitemap_paths):
    rows = {}
    for p in sitemap_paths:
        s = status.get(p)
        rows.setdefault(section(p), {"listed": 0, "inspected": 0, "indexed": 0, "discovered": 0, "crawled": 0})
        r = rows[section(p)]
        r["listed"] += 1
        if s:
            r["inspected"] += 1
            st = (s.get("state") or "").lower()
            r["indexed"] += s.get("verdict") == "PASS"
            r["discovered"] += "discovered" in st
            r["crawled"] += "crawled - currently not indexed" in st
    lines = ["| kind | in sitemap | inspected | indexed | discovered, not crawled | crawled, not indexed |",
             "|---|---|---|---|---|---|"]
    for name in sorted(rows):
        r = rows[name]
        lines.append(f"| {name} | {r['listed']} | {r['inspected']} | {r['indexed']} | {r['discovered']} | {r['crawled']} |")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=150)
    a = ap.parse_args()
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        print("gsc_index_status: GSC_SERVICE_ACCOUNT_JSON not set; nothing read.")
        return 0
    try:
        from google.oauth2 import service_account  # noqa
        from googleapiclient.discovery import build  # noqa
        from site_dates import eastern_today  # noqa
    except Exception as e:  # noqa: BLE001
        print(f"gsc_index_status: missing library ({e}); nothing read.")
        return 0
    today = eastern_today().isoformat()
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        sites = [s["siteUrl"] for s in (svc.sites().list().execute().get("siteEntry") or [])]
        prop = next((s for s in sites if s == "sc-domain:pdufa.bio"), None) or \
            next((s for s in sites if "pdufa.bio" in s), None)
        if not prop:
            print(f"gsc_index_status: the service account sees no pdufa.bio property ({len(sites)} visible).")
            return 0
    except Exception as e:  # noqa: BLE001
        print(f"gsc_index_status: could not connect: {type(e).__name__}: {str(e)[:160]}")
        return 0

    sm = io.open(os.path.join(SITE, "sitemap.xml"), encoding="utf-8", errors="replace").read()
    paths = {u[len(BASE):] or "/" for u in re.findall(r"<loc>([^<]+)</loc>", sm) if u.startswith(BASE)}
    status = {p: v for p, v in load(STATUS, {}).items() if p in paths}

    # 1. URL Inspection, read-only
    todo = pick(paths, status, today, a.max)
    local, stop, lock, t0 = threading.local(), threading.Event(), threading.Lock(), time.monotonic()

    def inspect(p):
        if stop.is_set() or time.monotonic() - t0 > BUDGET_S:
            return 0
        try:
            if not hasattr(local, "svc"):  # googleapiclient's http object is not thread-safe: one client per thread
                local.svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
            r = local.svc.urlInspection().index().inspect(body={"inspectionUrl": BASE + (p if p != "/" else "/"),
                                                                "siteUrl": prop}).execute()
            ir = (r.get("inspectionResult") or {}).get("indexStatusResult") or {}
            with lock:
                status[p] = {"state": ir.get("coverageState"), "verdict": ir.get("verdict"),
                             "crawled": (ir.get("lastCrawlTime") or "")[:10] or None, "checked": today}
            return 1
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            print(f"  inspect {p}: {type(e).__name__}: {msg[:140]}")
            if ("429" in msg or "quota" in msg.lower()) and not stop.is_set():
                stop.set()
                print("  quota reached; stopping inspections for this run")
            return 0

    with ThreadPoolExecutor(max_workers=max(1, WORKERS)) as ex:
        n_ok = sum(ex.map(inspect, todo))
    if time.monotonic() - t0 > BUDGET_S and n_ok < len(todo):
        print(f"  time budget reached after {n_ok} of {len(todo)}; the rest next run")
    io.open(STATUS, "w", encoding="utf-8").write(json.dumps(status, indent=0, sort_keys=True))
    idx = load(INDEXED, {})
    idx["_note"] = ("Paths Search Console reports as indexed (URL Inspection API verdict PASS), kept each rebuild by "
                    "gsc_index_status.py from _google_index_status.json; a path Google later reports unindexed drops out.")
    # keep what was known (hand-seeded or earlier runs) unless Google has since said otherwise
    passed = {p for p, v in status.items() if v.get("verdict") == "PASS"}
    failed = {p for p, v in status.items() if v.get("verdict") and v.get("verdict") != "PASS"}
    idx["indexed"] = sorted((set(idx.get("indexed") or []) | passed) - failed)
    io.open(INDEXED, "w", encoding="utf-8").write(json.dumps(idx, indent=1))
    print(f"gsc_index_status: inspected {n_ok} of {len(todo)} planned ({prop}); {len(status)} of {len(paths)} sitemap "
          f"pages have a status; {len(idx['indexed'])} indexed")

    # 2. Search Analytics, daily (Google's data lags ~2 days)
    stats_lines = []
    try:
        end = dt.date.fromisoformat(today) - dt.timedelta(days=1)
        start = end - dt.timedelta(days=89)
        rows = svc.searchanalytics().query(siteUrl=prop, body={
            "startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["date"],
            "rowLimit": 200}).execute().get("rows") or []
        daily = {r["keys"][0]: {"clicks": r["clicks"], "impressions": r["impressions"],
                                "position": round(r["position"], 1)} for r in rows}
        io.open(STATS, "w", encoding="utf-8").write(json.dumps({"_note": "Google Search daily totals, from the "
                                                               "Search Console API (gsc_index_status.py).",
                                                               "daily": daily}, indent=0, sort_keys=True))
        last28 = [v for d, v in daily.items() if d > (end - dt.timedelta(days=28)).isoformat()]
        c, i = sum(v["clicks"] for v in last28), sum(v["impressions"] for v in last28)
        stats_lines = [f"- Google Search, last 28 days of data: **{c} clicks, {i} impressions**"]
        print(stats_lines[0][2:].replace("**", ""))
    except Exception as e:  # noqa: BLE001
        print(f"  search analytics: {type(e).__name__}: {str(e)[:140]}")

    t = table(status, paths)
    print("\n".join(t))
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(["### Google index status (URL Inspection API)"] + stats_lines + [""] + t) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
