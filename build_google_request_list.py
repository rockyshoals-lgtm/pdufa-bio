# -*- coding: utf-8 -*-
"""build_google_request_list.py -- the 10 URLs most worth a manual "Request indexing" today (audit 2026-11-11 order 3).

Google Search Console allows about 10 indexing requests a day per property, and a requested page was indexed within a
day three times out of three (Nov 10-11). This writes `_google_request_indexing.txt` each run, in priority order:

  1. decision pages for FDA actions in the last 7 days (Eastern);
  2. event pages for goal dates in the next 30 days, soonest first;
  3. the studies and hubs (calendar, decisions/2026, CRL, timing study, run-up study).

URLs known to be indexed (`_google_indexed.json`, list of paths, kept by whoever reads the console) and URLs requested
in the last 7 days (`_google_requested.json`, {path: "YYYY-MM-DD"}) are skipped, so the list moves on each day. Mark a
request done with:  python build_google_request_list.py --requested /pdufa/CAPR-deramiocel /crl
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

OUT = os.path.join(HERE, "_google_request_indexing.txt")
IDX = os.path.join(HERE, "_google_indexed.json")
REQ = os.path.join(HERE, "_google_requested.json")
HUBS = ["/calendar", "/decisions/2026", "/fda-decisions-today", "/crl", "/research/fda-decision-timing", "/runup-by-year",
        "/fda-approval-decisions-this-week", "/calendar/2027", "/readouts/oncology", "/sitemap", "/fda-approval-letters"]
N = 10


def load(p, d):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--requested", nargs="*"); a = ap.parse_args()
    today = eastern_today()
    req = load(REQ, {})
    if a.requested:
        for u in a.requested:
            req[u.rstrip("/") or "/"] = today.isoformat()
        io.open(REQ, "w", encoding="utf-8").write(json.dumps(req, indent=1, sort_keys=True) + "\n")
    indexed = set(load(IDX, {"indexed": []}).get("indexed", []))
    recent = {u for u, d in req.items() if (today - dt.date.fromisoformat(d)).days < 7}
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    exists = lambda u: os.path.exists(os.path.join(SITE, *u.strip("/").split("/"), "index.html"))
    week = (today - dt.timedelta(days=7)).isoformat()
    soon = (today + dt.timedelta(days=30)).isoformat()
    cand = []
    for r in sorted(rows, key=lambda r: str(r.get("dcd") or ""), reverse=True):
        u = str(r.get("url") or "")
        if r.get("st") == "Decided" and u.startswith("/fda-decision/") and str(r.get("dcd") or "") >= week:
            cand.append((u, f"decision {r.get('dcd')}: {r['t']} {str(r.get('name') or '')[:50]}"))
    for r in sorted(rows, key=lambda r: str(r.get("d") or "")):
        u = str(r.get("url") or "")
        if (r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting") and u.startswith("/pdufa/")
                and today.isoformat() <= str(r.get("d") or "") <= soon):
            cand.append((u, f"goal date {r['d']}: {r['t']} {str(r.get('name') or '')[:50]}"))
    cand += [(u, "hub / study") for u in HUBS]
    out, seen = [], set()
    for u, why in cand:
        if u in seen or u in indexed or u in recent or not exists(u):
            continue
        seen.add(u)
        out.append((u, why))
        if len(out) == N:
            break
    body = (f"# Google Search Console: request indexing for these, in order ({today.isoformat()} Eastern).\n"
            f"# About 10 requests a day per property. Then run: python build_google_request_list.py --requested <paths>\n"
            f"# Skipped: {len(indexed)} known indexed (_google_indexed.json), {len(recent)} requested in the last 7 days.\n")
    body += "".join(f"https://www.pdufa.bio{u}\t# {why}\n" for u, why in out)
    io.open(OUT, "w", encoding="utf-8").write(body)
    print(f"google request list: {len(out)} URL(s) -> {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
