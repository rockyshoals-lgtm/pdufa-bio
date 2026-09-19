# -*- coding: utf-8 -*-
"""Live verification of the 09-15 ORDER from a non-browser client."""
import json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
H = {"User-Agent": "pdufa-verify/1.0", "Cache-Control": "no-cache"}
def get(path):
    return urllib.request.urlopen(urllib.request.Request("https://www.pdufa.bio" + path, headers=H), timeout=60).read().decode("utf-8", "replace")
api = json.loads(get("/api/v1/events?limit=1000"))
rows = api.get("data") or api.get("events") or api
if isinstance(rows, dict):
    rows = rows.get("data", [])
print("API rows:", len(rows), "as_of:", (api.get("meta") or {}).get("as_of"))
src = sum(1 for r in rows if r.get("source_url"))
print("source_url present:", src, "of", len(rows), "| date_history present:", sum(1 for r in rows if r.get("date_history")))
for r in rows:
    if r.get("ticker") == "CORT" and r.get("status") == "Upcoming":
        print("CORT:", {k: r.get(k) for k in ("id", "date", "date_month", "date_precision", "therapeutic_area", "indication", "url", "source_url", "days_to_decision")})
    if r.get("id") == "pdufa_prax_2026-12-27":
        print("PRAX relutrigine:", {k: r.get(k) for k in ("date", "url", "source_url")}, "history:", [h.get("date") for h in (r.get("date_history") or [])])
    if r.get("id") == "pdufa_rare_2026-09-19":
        print("RARE:", {k: r.get(k) for k in ("date", "url", "source_url")})
bad = [r["id"] for r in rows if r.get("date_month") and r.get("date") and r["date_month"] != r["date"][:7]]
print("date_month != date[:7] live:", bad)
nxt10 = sorted([r for r in rows if r.get("type") == "PDUFA" and r.get("status") == "Upcoming" and r.get("date")], key=lambda r: r["date"])[:10]
print("next 10 upcoming PDUFAs source_url:", [(r["ticker"], r["date"], "src" if r.get("source_url") else "NULL") for r in nxt10])
bi = json.loads(get("/build-info.json"))
print("build-info:", bi)
p = get("/pdufa/PRAX")
print("/pdufa/PRAX title:", re.search(r"<title>(.*?)</title>", p, re.S).group(1), "| says Sep 27:", "Sep 27" in p or "2026-09-27" in p)
p = get("/pdufa/PRAX-relutrigine")
print("/pdufa/PRAX-relutrigine kv:", re.search(r"PDUFA target date</span><b>([^<]+)</b>", p).group(1))
d = get("/developers")
print("/developers mentions source_url:", "source_url" in d, "| date_history:", "date_history" in d)
m = get("/methodology")
print("/methodology precision section:", 'id="date-precision"' in m)
for s in ("ABBV-tavapadon-2", "NVO-cagrisema", "PTGX-rusfertide"):
    t = get(f"/pdufa/{s}")
    print(f"/pdufa/{s}: canonical", re.search(r'rel="canonical" href="([^"]+)"', t).group(1), "| robots", re.search(r'name="robots" content="([^"]+)"', t).group(1))
ro = get("/readouts")
evs = re.findall(r'\{"@type":"Event"(?:[^{}]|\{[^{}]*\})*\}', ro)
print("/readouts Events:", len(evs), "| day-stamped:", sum(1 for e in evs if re.search(r'"startDate":"\d{4}-\d{2}-\d{2}', e)))
dc = get("/pdufa-date-changes")
print("/pdufa-date-changes PRAX:", "PRAX" in dc, "| CAPR:", "CAPR" in dc)
cal = get("/calendar")
print("/calendar CORT link:", re.findall(r'href="(/pdufa/CORT[^"]*)"', cal)[:3])
