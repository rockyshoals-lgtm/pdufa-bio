# -*- coding: utf-8 -*-
"""Current state of /learn/what-is-a-pdufa-date against the 09-10b item-4 spec.

Spec: five H2 sections (what it is; why it exists / the 1992 Act; how the timeline works; what
the FDA can do on the date; why the date matters), the year in the title, no approval odds, and
no "why investors care" trade framing.
"""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

p = "pdufa_site_src/learn/what-is-a-pdufa-date/index.html"
d = io.open(p, encoding="utf-8", errors="replace").read()
print(f"{p}  {len(d)} bytes")
for tag in ("title", "h1"):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", d, re.S)
    print(f"  {tag}: {re.sub(r'<[^>]+>', '', m.group(1)) if m else '?'}")
m = re.search(r'<meta name="description" content="([^"]+)', d)
print(f"  desc : {m.group(1)[:200] if m else '?'}")

print("\n  H2 sections:")
for h in re.findall(r"<h2[^>]*>(.*?)</h2>", d, re.S):
    print(f"     - {re.sub(r'<[^>]+>', '', h).strip()[:80]}")

body = re.sub(r"<script.*?</script>", " ", d, flags=re.S)
txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
print(f"\n  body words: {len(txt.split())}")
for phrase in ("investor", "trade", "odds", "probability", "1992", "Prescription Drug User Fee",
               "Complete Response", "priority review", "10 months", "six months"):
    n = len(re.findall(re.escape(phrase), txt, re.I))
    print(f"     {phrase:<28} x{n}")
print("\n  first 400 chars of body:")
print("   " + txt[:400])
