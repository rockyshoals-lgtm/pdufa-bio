# -*- coding: utf-8 -*-
"""MRK Lipfendra (enlicitide) and OTSKY centanafadine: what goal date does a primary source state?
The earlier sweep's proximity matcher is unreliable on a multi-product release, so read the
sentences around each drug name directly."""
import json, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}


def http(u, t=50):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()


def clean(b):
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", b.decode("utf-8", "replace"))))


def efts(q, forms="8-K,10-Q,10-K,6-K,20-F", start="2025-06-01", end="2026-09-18"):
    u = (f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}"
         f"&dateRange=custom&startdt={start}&enddt={end}")
    return json.loads(http(u))["hits"]["hits"]


print("== MRK enlicitide / Lipfendra: every sentence naming the drug near a date ==")
for q in ['"enlicitide" "target action date"', '"enlicitide" "July 16"', '"Lipfendra"']:
    try:
        hits = efts(q)
    except Exception as e:
        print(f"  {q}: {e}"); continue
    print(f"  -- {q}: {len(hits)} hit(s)")
    for h in hits[:3]:
        s = h["_source"]; adsh, fn = h["_id"].split(":", 1)
        m = re.search(r"CIK (\d+)", s["display_names"][0])
        url = f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/{adsh.replace('-', '')}/{fn}"
        try:
            t = clean(http(url))
        except Exception:
            continue
        for mm in list(re.finditer(r"enlicitide|Lipfendra", t, re.I))[:4]:
            seg = t[max(0, mm.start() - 300): mm.end() + 400]
            if re.search(r"PDUFA|target action date|action date", seg, re.I):
                print(f"     {s['file_date']} {s['form']}: ...{seg.strip()[:480]}")
                print(f"        {url}")
                break
        time.sleep(0.3)

print("\n== OTSKY centanafadine: Otsuka is not a US registrant; check FDA/openFDA instead ==")
try:
    j = json.loads(http("https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:%22centanafadine%22&limit=3"))
    for r in j.get("results", []):
        of = r.get("openfda") or {}
        print("   app", r.get("application_number"), of.get("brand_name"), "| sponsor", r.get("sponsor_name"))
        for s in sorted(r.get("submissions") or [], key=lambda x: str(x.get("submission_status_date"))):
            print("     ", s.get("submission_type"), s.get("submission_number"), s.get("submission_status"),
                  s.get("submission_status_date"))
except Exception as e:
    print("   openFDA:", e)
