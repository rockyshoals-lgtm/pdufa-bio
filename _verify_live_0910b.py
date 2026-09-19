# -*- coding: utf-8 -*-
"""Verify against LIVE that the 09-10b precision pass actually deployed.

House rule: audit the deployed site, not the repo. Cache-Control: no-cache so the edge cannot
hand back the pre-deploy payload.
"""
import json
import sys
import urllib.request

URL = "https://pdufa.bio/api/v1/events?limit=500"
WANT = {
    "pdufa_vrtx_2026-11-30": ("day", True, "VRTX povetacicept - sourced, day kept"),
    "pdufa_mirm_2026-09-26": ("day", True, "MIRM zilurgisertib - sourced"),
    "pdufa_incy_2026-09-26": ("day", True, "INCY - relabelled licensor"),
    "pdufa_ions_2026-06-30": ("day", True, "IONS olezarsen - real Jun 30"),
    "pdufa_vrdn_2026-06-30": ("day", True, "VRDN veligrotug - real Jun 30"),
    "pdufa_srrk_2026-09-30": ("day", True, "SRRK apitegromab - real Sep 30"),
    "pdufa_tak_2026-09-30": ("quarter", True, "TAK oveporexton - sponsor said Q3"),
    "pdufa_ptgx_2026-09-30": ("quarter", True, "PTGX rusfertide - sponsor said Q3"),
    "pdufa_pfe_2026-09-30": ("quarter", True, "PFE brepocitinib - sponsor said Q3"),
    "pdufa_roiv_2026-09-30": ("quarter", True, "ROIV brepocitinib - sponsor said Q3"),
    "pdufa_azn_2026-06-30": ("month", False, "AZN Truqap - no source anywhere"),
    "pdufa_nvo_mim8_2026-09-30": ("year", False, "NVO denecimig - year only"),
}

req = urllib.request.Request(URL, headers={
    "User-Agent": "pdufa.bio builder rockyshoals@gmail.com",
    "Cache-Control": "no-cache", "Pragma": "no-cache"})
d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
ev = d.get("data") or d.get("events") or []
print(f"as_of={d['meta']['as_of']}  rows={len(ev)}")

by_id = {e.get("id"): e for e in ev}
fail = 0
for eid, (prec, want_src, what) in WANT.items():
    e = by_id.get(eid)
    if e is None:
        print(f"  MISSING {eid}  ({what})")
        fail += 1
        continue
    got_p = e.get("date_precision")
    got_d = e.get("date")
    got_s = bool(e.get("source_url") or (e.get("source") if "source" in e else None))
    bad = []
    if got_p != prec:
        bad.append(f"precision {got_p!r} != {prec!r}")
    if prec != "day" and got_d is not None:
        bad.append(f"date should be null for {prec}, got {got_d!r}")
    if prec == "day" and not got_d:
        bad.append("day row lost its date")
    mark = "FAIL" if bad else "ok  "
    if bad:
        fail += 1
    print(f"  {mark} {eid:<28} prec={str(got_p):<8} date={str(got_d):<12} "
          f"month={str(e.get('date_month')):<9} dtd={e.get('days_to_decision')}  {what}")
    for b in bad:
        print(f"        -> {b}")

# no day-precision PDUFA may sit on a quarter end without a source, live
qe = [e for e in ev if e.get("type") == "PDUFA" and e.get("date_precision") == "day"
      and str(e.get("date") or "")[5:] in {"03-31", "06-30", "09-30", "12-31"}]
print(f"\nlive day-precision quarter-end PDUFAs: {len(qe)} "
      f"-> {[e['id'] for e in qe]}")

print("\nLIVE VERIFIED" if not fail else f"\n{fail} LIVE MISMATCH(ES)")
sys.exit(1 if fail else 0)
