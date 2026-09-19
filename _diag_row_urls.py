# -*- coding: utf-8 -*-
"""How many dataset rows name a site page that does not exist?"""
import io, json, os, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"
s = io.open(f"{SITE}/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])


def ok(u):
    rel = u.strip("/")
    return os.path.isfile(os.path.join(SITE, rel, "index.html")) or \
        os.path.isfile(os.path.join(SITE, rel))


bad = []
for r in rows:
    u = str(r.get("url") or "")
    if u.startswith("/") and not ok(u):
        tk = str(r.get("t") or "").upper()
        fallback = f"/ticker/{tk}"
        bad.append((r["id"], r["type"], str(r.get("st")), u, fallback, ok(fallback)))
print(f"{len(bad)} row(s) of {len(rows)} name a page that does not exist\n")
print(Counter(b[3] for b in bad).most_common(25))
print("\nfallback /ticker/{TK} exists for:", sum(1 for b in bad if b[5]), "of", len(bad))
print("\nexamples:")
for b in bad[:15]:
    print(f"   {b[0]:<32} {b[1]:<8} {b[2]:<10} {b[3]:<38} -> {b[4]} {'ok' if b[5] else 'MISSING TOO'}")
