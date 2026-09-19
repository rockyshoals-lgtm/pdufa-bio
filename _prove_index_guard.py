# -*- coding: utf-8 -*-
"""Prove tests/test_dropbox_index_complete.py: 0 -> planted 1 -> 0."""
import io
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
T = os.path.join("tests", "test_dropbox_index_complete.py")
IDX = os.path.join("odin_cowork_dropbox", "INDEX.md")


def run():
    p = subprocess.run([PY, T], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode


bk = tempfile.mkdtemp()
shutil.copy2(IDX, os.path.join(bk, "INDEX.md"))

print(f"[baseline] rc={run()}")
ok = run() == 0

lines = io.open(IDX, encoding="utf-8", errors="replace").read().splitlines(True)
drop = next(i for i, l in enumerate(lines) if l.startswith("- **"))
io.open(IDX, "w", encoding="utf-8").writelines(
    [l for i, l in enumerate(lines) if i != drop])
rc = run()
print(f"[planted: one entry deleted] rc={rc}")
ok &= rc == 1

shutil.copy2(os.path.join(bk, "INDEX.md"), IDX)
rc = run()
print(f"[healed] rc={rc}")
ok &= rc == 0
print("\nPROVEN 0 -> 1 -> 0" if ok else "\nNOT PROVEN")
sys.exit(0 if ok else 1)
