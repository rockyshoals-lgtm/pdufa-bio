# -*- coding: utf-8 -*-
"""Verify against LIVE that the 2026-09-14 currency pass is actually deployed."""
import json
import sys
import urllib.request

URL = "https://pdufa.bio/api/v1/events?limit=500"
EXPECT = {
    "pdufa_srrk_2026-09-30": ("Decided", "Approved", "2026-09-11"),
    "pdufa_phar_2026-10-24": ("Decided", "Approved", "2026-09-11"),
    "pdufa_bfri_2026-09-28": ("Decided", "Approved", "2026-09-09"),
    "pdufa_bayry_2026-11-30": ("Decided", "Approved", "2026-09-09"),
}

req = urllib.request.Request(URL, headers={
    "User-Agent": "pdufa.bio builder rockyshoals@gmail.com",
    "Cache-Control": "no-cache", "Pragma": "no-cache"})
d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
ev = d.get("data") or []
by = {e.get("id"): e for e in ev}
print(f"as_of={d['meta']['as_of']}  rows={len(ev)}")

fail = 0
for eid, (st, oc, dcd) in EXPECT.items():
    e = by.get(eid)
    if not e:
        print(f"  MISSING {eid}")
        fail += 1
        continue
    got = (e.get("status"), e.get("outcome"), e.get("decision_date"))
    ok = got == (st, oc, dcd)
    print(f"  {'ok  ' if ok else 'FAIL'} {eid:<26} {got}")
    if not ok:
        fail += 1

# nothing pending may sit in the past unlabelled
awaiting = [e for e in ev if e.get("type") == "PDUFA"
            and str(e.get("status") or "") == "Awaiting"]
print(f"\nAwaiting PDUFAs live: {[e['id'] for e in awaiting]}")

stale = [e for e in ev if e.get("type") == "PDUFA"
         and str(e.get("status") or "") == "Upcoming"
         and (e.get("days_to_decision") is not None and e["days_to_decision"] < 0)]
print(f"past-dated rows still labelled Upcoming: {len(stale)}  {[e['id'] for e in stale]}")
if stale:
    fail += 1

print("\nLIVE VERIFIED" if not fail else f"\n{fail} LIVE PROBLEM(S)")
sys.exit(1 if fail else 0)
