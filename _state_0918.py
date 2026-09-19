# -*- coding: utf-8 -*-
"""Where does the tree stand on 2026-09-18, after three days of CI and one fast-forward?"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TODAY = dt.date.today().isoformat()


def load(p):
    s = io.open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
    r, _ = json.JSONDecoder().raw_decode(s[s.find("["):])
    return r


cur = load("pdufa_site_src/api/v1/dataset.mjs")
bak = os.path.join(os.environ["TEMP"], "b0918", "dataset.mjs")
mine = {x["id"]: x for x in load(bak)} if os.path.exists(bak) else {}
print(f"dataset rows: CI={len(cur)}  my-uncommitted-backup={len(mine)}")

up = [r for r in cur if r["type"] == "PDUFA" and r.get("st") == "Upcoming"]
src = sum(1 for r in up if (r.get("_d") or {}).get("source_url"))
print(f"upcoming PDUFA {len(up)}, with source_url {src}")

print("\n-- did my uncommitted batch-b survive the fast-forward? --")
for i in ("pdufa_regn_2026-11-30", "pdufa_nuvl_2026-11-27", "pdufa_rhhby_2026-10-09",
          "pdufa_rhhby_2026-10-15", "pdufa_gsk_2026-10-26", "pdufa_rhhby_2026-11-30",
          "pdufa_rhhby_2026-12-18"):
    r = next((x for x in cur if x["id"] == i), None)
    if r is None:
        print(f"  {i:<28} MISSING FROM CI DATASET")
        continue
    d = r.get("_d") or {}
    print(f"  {i:<28} t={r['t']:<6} dp={r.get('dp'):<8} src={'yes' if d.get('source_url') else 'NO'}")

print("\n-- events whose date has now passed (today %s) --" % TODAY)
for r in sorted(cur, key=lambda x: str(x.get("d"))):
    if r["type"] != "PDUFA":
        continue
    d = str(r.get("d") or "")
    if r.get("st") == "Upcoming" and d and d <= TODAY:
        print(f"  PASSED  {r['id']:<30} {d} {r.get('dp'):<8} {str(r.get('name'))[:44]}")
    if r.get("st") == "Awaiting":
        print(f"  AWAIT   {r['id']:<30} {d} {str(r.get('name'))[:44]}")

nxt = [r for r in cur if r["type"] == "PDUFA" and r.get("st") == "Upcoming"
       and str(r.get("d") or "") > TODAY and r.get("dp") == "day"]
print("\n-- next 6 dated decisions --")
for r in sorted(nxt, key=lambda x: x["d"])[:6]:
    days = (dt.date.fromisoformat(r["d"]) - dt.date.today()).days
    print(f"  {r['d']}  T-{days:<4} {r['t']:<6} {str(r.get('name'))[:42]:<42} "
          f"{'src' if (r.get('_d') or {}).get('source_url') else 'NO SRC'}")

bi = json.load(io.open("pdufa_site_src/build-info.json", encoding="utf-8"))
print("\nbuild-info:", bi)
