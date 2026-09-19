# -*- coding: utf-8 -*-
import io, json, os, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
s = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])

print("== do we track imlunestrant / LLY? ==")
for r in rows:
    blob = (str(r.get("name", "")) + str(r.get("t", "")) + json.dumps(r.get("_d") or {})).lower()
    if "imlunestrant" in blob or "ember" in blob:
        print("  ", r["id"], r["t"], r.get("d"), r.get("dp"), r.get("st"), "|", str(r.get("name"))[:60])
print("  LLY rows:", [(r["id"], r.get("d"), r.get("st"), str(r.get("name"))[:40]) for r in rows if r["t"] == "LLY"])

print("\n== is there a drug page / decision page? ==")
for pat in ("imlunestrant", "inluriyo", "verzenio", "abemaciclib"):
    hits = [d for d in os.listdir("pdufa_site_src/drug") if pat in d.lower()] if os.path.isdir("pdufa_site_src/drug") else []
    print(f"  /drug/*{pat}*:", hits[:4])

print("\n== TLX row + any FDA action ==")
for r in rows:
    if r["t"] == "TLX":
        d = r.get("_d") or {}
        print("  ", r["id"], r.get("d"), r.get("dp"), r.get("st"), "|", str(r.get("name"))[:50])
        print("     _d:", {k: str(v)[:110] for k, v in d.items() if k in ("source", "source_url", "review", "goal_note")})

def openfda(q):
    u = f"https://api.fda.gov/drug/drugsfda.json?search={urllib.parse.quote(q)}&limit=5"
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())
    except Exception as e:
        return {"error": str(e)}

import urllib.parse
for q, label in [('openfda.generic_name:"imlunestrant"', "imlunestrant"),
                 ('openfda.brand_name:"pixclara"', "Pixclara"),
                 ('openfda.generic_name:"iodine i 124 girentuximab"', "TLX girentuximab")]:
    j = openfda(q)
    res = j.get("results") or []
    print(f"\n  openFDA {label}: {len(res)} result(s) {j.get('error','')}")
    for x in res[:3]:
        subs = x.get("submissions") or []
        latest = sorted([s for s in subs if s.get("submission_status_date")],
                        key=lambda s: s["submission_status_date"])[-3:]
        print("    app", x.get("application_number"), (x.get("openfda") or {}).get("brand_name"),
              [(s.get("submission_type"), s.get("submission_number"), s.get("submission_status"),
                s.get("submission_status_date")) for s in latest])
