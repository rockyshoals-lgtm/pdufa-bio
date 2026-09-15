# -*- coding: utf-8 -*-
"""Prove tests/test_row_fields_agree.py catches each fault class: 0 -> planted 1 -> healed 0."""
import io
import json
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
BAK = DS + ".prove_bak"
GUARD = os.path.join(HERE, "tests", "test_row_fields_agree.py")


def run():
    p = subprocess.run([PY, GUARD], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip().splitlines()[-1:] if p.stdout else []


def load():
    src = io.open(DS, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    return src, i, j, json.loads(src[i:j])


def save(src, i, j, rows):
    io.open(DS, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])


PLANTS = {
    "1 date_month != date[:7]": lambda r: r.__setitem__("dm", "2026-01"),
    "2a id date != d, no history": lambda r: (r.__setitem__("id", "pdufa_plant_2026-02-02"), r.__setitem__("d", "2026-03-03")),
    "2b id date != d, history covers it (must PASS)": lambda r: (
        r.__setitem__("id", "pdufa_plant_2026-02-02"), r.__setitem__("d", "2026-03-03"),
        r.setdefault("_d", {}).__setitem__("date_history", [{"date": "2026-02-02"}, {"date": "2026-03-03", "why": "plant"}])),
    "2c id date != d, history for a DIFFERENT date (must FAIL)": lambda r: (
        r.__setitem__("id", "pdufa_plant_2026-02-02"), r.__setitem__("d", "2026-03-03"),
        r.setdefault("_d", {}).__setitem__("date_history", [{"date": "2026-01-01"}])),
    "3 prefix readout_ on a PDUFA": lambda r: r.__setitem__("id", "readout_plant_" + str(r.get("d"))),
}
EXPECT = {"2b id date != d, history covers it (must PASS)": 0}

shutil.copy2(DS, BAK)
ok = True
try:
    rc, tail = run()
    print(f"baseline rc={rc}  {tail}")
    ok &= rc == 0
    for label, plant in PLANTS.items():
        src, i, j, rows = load()
        tgt = next(r for r in rows if r.get("type") == "PDUFA" and r.get("dp") == "day" and r.get("st") == "Upcoming")
        plant(tgt)
        save(src, i, j, rows)
        rc, tail = run()
        want = EXPECT.get(label, 1)
        print(f"planted [{label}] rc={rc} want={want}  {'PASS' if rc == want else 'FAIL'}")
        ok &= rc == want
        shutil.copy2(BAK, DS)
    rc, tail = run()
    print(f"healed rc={rc}  {tail}")
    ok &= rc == 0
finally:
    shutil.copy2(BAK, DS)
    os.remove(BAK)
print("PROOF", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
