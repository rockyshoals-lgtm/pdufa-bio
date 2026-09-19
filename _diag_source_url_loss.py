# -*- coding: utf-8 -*-
"""source_url was on 262 of 456 rows when I pushed 297e7ea1a on 09-15. Three CI runs later it is
on far fewer. Which rows lost it, and what else did they lose?"""
import io
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def rows_from(text):
    t = text.replace("\x00", "")
    r, _ = json.JSONDecoder().raw_decode(t[t.find("["):])
    return {x["id"]: x for x in r}


def at(rev):
    out = subprocess.run(["git", "show", f"{rev}:pdufa_site_src/api/v1/dataset.mjs"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return rows_from(out.stdout)


mine = at("297e7ea1a")                      # my 09-15 push
now = rows_from(io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
                        errors="replace").read())

def n_src(d):
    return sum(1 for r in d.values() if (r.get("_d") or {}).get("source_url"))


print(f"source_url  09-15 push: {n_src(mine)}/{len(mine)}   now: {n_src(now)}/{len(now)}")
lost, kept_keys, lost_keys = [], set(), set()
for i, r in mine.items():
    had = (r.get("_d") or {}).get("source_url")
    if not had:
        continue
    cur = now.get(i)
    if cur is None:
        lost.append((i, "ROW GONE"))
        continue
    d = cur.get("_d") or {}
    if not d.get("source_url"):
        lost.append((i, r["type"], r.get("st"), str(r.get("url"))[:40]))
        lost_keys |= set((r.get("_d") or {}).keys())
    else:
        kept_keys |= set(d.keys())
print(f"rows that LOST source_url: {len(lost)}")
from collections import Counter
c = Counter((x[1], x[2]) if len(x) > 2 else (x[1],) for x in lost)
for k, v in c.most_common():
    print("   ", v, k)
print("\nfirst 12 lost:")
for x in lost[:12]:
    print("   ", x)

# what does a lost row look like now vs then
if lost:
    i = lost[0][0]
    print(f"\n-- {i} --")
    print("  THEN _d keys:", sorted((mine[i].get('_d') or {}).keys()))
    print("  NOW  _d keys:", sorted((now.get(i, {}).get('_d') or {}).keys()))
    print("  THEN url:", mine[i].get("url"))
    print("  NOW  url:", now.get(i, {}).get("url"))

# other fields I set on 09-15
for f in ("date_history", "source", "source_quote"):
    a = sum(1 for r in mine.values() if (r.get("_d") or {}).get(f))
    b = sum(1 for r in now.values() if (r.get("_d") or {}).get(f))
    print(f"{f:<14} 09-15: {a:>3}   now: {b:>3}")

# and the CORT re-key / url alignment
for i in ("pdufa_cort_2026-12-17", "pdufa_prax_2026-12-27", "pdufa_rare_2026-09-19"):
    r = now.get(i)
    print(f"{i:<26}", "PRESENT" if r else "MISSING",
          (r.get("url"), bool((r.get("_d") or {}).get("source_url"))) if r else "")
