# -*- coding: utf-8 -*-
"""Did the INDEX rebuild PRESERVE hand-written summaries, or regenerate over them?"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

pat = re.compile(r"`([^`]+\.md)`\s*[—-]\s*(.*)")


def load(p):
    d = {}
    for line in io.open(p, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            d[m.group(1)] = m.group(2).strip()
    return d


b = load(os.path.join(os.environ["TEMP"], "INDEX.before"))
a = load("odin_cowork_dropbox/INDEX.md")
print(f"before {len(b)} entries, after {len(a)}")
common = [k for k in b if k in a]
changed = [k for k in common if b[k][:70] != a[k][:70]]
print(f"in both: {len(common)}, summary text changed: {len(changed)}")
for k in changed[:8]:
    print(f"\n  {k}")
    print(f"     was: {b[k][:130]}")
    print(f"     now: {a[k][:130]}")
gone = [k for k in b if k not in a]
print(f"\nentries present before and MISSING now: {len(gone)} {gone[:5]}")
