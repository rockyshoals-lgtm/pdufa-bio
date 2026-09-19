# -*- coding: utf-8 -*-
"""Prove tests/test_no_unsourced_day_dates.py: 0 -> planted 1 -> healed 0, per invariant.

A guard that has only ever seen a clean tree is not a guard. Each of the four invariants gets
its own planted defect, run separately, and every file is restored byte-for-byte afterwards.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
TEST = os.path.join("tests", "test_no_unsourced_day_dates.py")
DATASET = os.path.join("pdufa_site_src", "api", "v1", "dataset.mjs")
LIB = os.path.join("pdufa_site_src", "api", "v1", "_lib.mjs")
EARLY = "build_early_decisions.py"


def run():
    p = subprocess.run([PY, TEST], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip().splitlines()


def backup(paths):
    d = tempfile.mkdtemp()
    for p in paths:
        shutil.copy2(p, os.path.join(d, os.path.basename(p)))
    return d


def restore(d, paths):
    for p in paths:
        shutil.copy2(os.path.join(d, os.path.basename(p)), p)


PATHS = [DATASET, LIB, EARLY]
bk = backup(PATHS)
ok = True

rc, out = run()
print(f"[baseline]        rc={rc}  {out[-1][:100] if out else ''}")
ok &= rc == 0

# --- 1: a ledger row returns to day precision with no source
s = io.open(DATASET, encoding="utf-8", errors="replace").read()
a, b = s.index("["), s.rindex("]") + 1
rows = json.loads(s[a:b])
for r in rows:
    if str(r.get("t")).upper() == "TAK" and r.get("type") == "PDUFA" \
            and str(r.get("d", "")).startswith("2026-09"):
        r["dp"] = "day"
        (r.setdefault("_d", {})).pop("source_url", None)
        break
io.open(DATASET, "w", encoding="utf-8").write(
    s[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + s[b:])
rc, out = run()
print(f"[1 ledger day]    rc={rc}  {out[0][:110] if out else ''}")
ok &= rc == 1
restore(bk, PATHS)

# --- 2: a brand-new unsourced quarter-end day
s = io.open(DATASET, encoding="utf-8", errors="replace").read()
a, b = s.index("["), s.rindex("]") + 1
rows = json.loads(s[a:b])
rows.append({"id": "pdufa_zzz_2026-03-31", "t": "ZZZ", "company": "Planted Co",
             "d": "2026-03-31", "dp": "day", "name": "Planted", "type": "PDUFA",
             "ta": "", "cap": "", "st": "Upcoming", "url": "/pdufa/ZZZ",
             "ua": "2026-09-10T00:00:00Z", "_d": {}})
io.open(DATASET, "w", encoding="utf-8").write(
    s[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + s[b:])
rc, out = run()
print(f"[2 new Q-end]     rc={rc}  {out[0][:110] if out else ''}")
ok &= rc == 1
restore(bk, PATHS)

# --- 3: the timing statistic loses its precision gate
s = io.open(EARLY, encoding="utf-8", errors="replace").read()
io.open(EARLY, "w", encoding="utf-8").write(
    s.replace('if r.get("dp") != "day":\n            continue', "pass", 1))
rc, out = run()
print(f"[3 stat ungated]  rc={rc}  {out[0][:110] if out else ''}")
ok &= rc == 1
restore(bk, PATHS)

# --- 4: year rows get a derived month again
s = io.open(LIB, encoding="utf-8", errors="replace").read()
io.open(LIB, "w", encoding="utf-8").write(
    s.replace("e.dp === 'year' ? null : (e.d ? String(e.d).slice(0, 7) : null)",
              "(e.d ? String(e.d).slice(0, 7) : null)", 1))
rc, out = run()
print(f"[4 year month]    rc={rc}  {out[0][:110] if out else ''}")
ok &= rc == 1
restore(bk, PATHS)

rc, out = run()
print(f"[healed]          rc={rc}  {out[-1][:100] if out else ''}")
ok &= rc == 0

print("\nPROVEN 0 -> 1 (x4) -> 0" if ok else "\nNOT PROVEN — guard did not behave")
sys.exit(0 if ok else 1)
