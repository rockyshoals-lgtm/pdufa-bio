# -*- coding: utf-8 -*-
"""Dump each H2 section of the learn page, plus whatever markers sync_learn_timing needs."""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

p = "pdufa_site_src/learn/what-is-a-pdufa-date/index.html"
d = io.open(p, encoding="utf-8", errors="replace").read()

body = d.split("<body>", 1)[1] if "<body>" in d else d
body = body.split("<footer", 1)[0]
parts = re.split(r"(<h2[^>]*>.*?</h2>)", body, flags=re.S)
print(f"--- lede (before first h2), raw:\n")
print(re.sub(r"\s+", " ", parts[0])[-1400:])
for i in range(1, len(parts), 2):
    h = re.sub(r"<[^>]+>", "", parts[i]).strip()
    seg = re.sub(r"\s+", " ", parts[i + 1]) if i + 1 < len(parts) else ""
    print(f"\n\n=== H2: {h}\n{seg[:1100]}")

print("\n\n--- markers sync_learn_timing may key on:")
for m in re.finditer(r"<!--[A-Z:_/-]{3,40}-->", d):
    print("   ", m.group(0))
