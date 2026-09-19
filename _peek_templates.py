# -*- coding: utf-8 -*-
"""Read the /readouts and /condition templates so the new hubs match the house markup."""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for p in ("pdufa_site_src/readouts/index.html",
          "pdufa_site_src/condition/rare-disease/index.html"):
    d = io.open(p, encoding="utf-8", errors="replace").read()
    print(f"\n{'=' * 78}\n=== {p}   {len(d)} bytes")
    for tag in ("title", "h1"):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", d, re.S)
        print(f"  {tag}: {re.sub(r'<[^>]+>', '', m.group(1))[:110] if m else '?'}")
    m = re.search(r'<meta name="description" content="([^"]{0,220})', d)
    print(f"  desc: {m.group(1) if m else '?'}")
    m = re.search(r'<div class="sub">(.*?)</div>', d, re.S)
    print(f"  sub : {re.sub(r'<[^>]+>', ' ', m.group(1))[:240] if m else '?'}")
    rows = list(re.finditer(r'<a class="row".*?</a>', d, re.S))
    print(f"  rows: {len(rows)}")
    for r in rows[:2]:
        print("     " + re.sub(r"\s+", " ", r.group(0))[:300])
    m = re.search(r"<style>(.{0,120})", d, re.S)
    print(f"  style starts: {m.group(1)[:110] if m else '?'}")
