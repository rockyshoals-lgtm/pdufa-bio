# -*- coding: utf-8 -*-
"""Prove tests/test_awaiting_marked_on_calendar.py: 0 -> planted 1 -> 0."""
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
TEST = os.path.join("tests", "test_awaiting_marked_on_calendar.py")
PAGES = [os.path.join("pdufa_site_src", "calendar", "index.html")] + \
    sorted(glob.glob(os.path.join("pdufa_site_src", "calendar", "*", "*", "index.html")))


def run():
    p = subprocess.run([PY, TEST], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip().splitlines()


bk = tempfile.mkdtemp()
for i, p in enumerate(PAGES):
    shutil.copy2(p, os.path.join(bk, f"{i}.html"))

rc, out = run()
print(f"[baseline] rc={rc}  {out[-1][:110] if out else ''}")
ok = rc == 0

# plant: strip the Awaiting badge back off wherever it is
hit = False
for p in PAGES:
    d = io.open(p, encoding="utf-8", errors="replace").read()
    n = re.sub(r'\s*<span class="awaiting".*?</span>', "", d, flags=re.S)
    if n != d:
        io.open(p, "w", encoding="utf-8").write(n)
        hit = True
if not hit:
    print("  (nothing to strip -- no awaiting badge present, cannot plant)")
rc, out = run()
print(f"[planted]  rc={rc}  {out[0][:130] if out else ''}")
ok &= rc == 1

for i, p in enumerate(PAGES):
    shutil.copy2(os.path.join(bk, f"{i}.html"), p)
rc, out = run()
print(f"[healed]   rc={rc}  {out[-1][:110] if out else ''}")
ok &= rc == 0

print("\nPROVEN 0 -> 1 -> 0" if ok else "\nNOT PROVEN")
sys.exit(0 if ok else 1)
