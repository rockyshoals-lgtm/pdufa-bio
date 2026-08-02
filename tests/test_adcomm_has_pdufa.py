# -*- coding: utf-8 -*-
"""Guard: every AdComm on the site must have a corresponding PDUFA record.

Root cause this catches: the AdComm ingest captured Replimune's Jul 30 CTGTAC meeting but never
created the PDUFA row, so REPL's Aug 2 FDA goal date -- the nearest decision on the whole site --
was missing on the eve of the decision, and the homepage answered "what's next?" with MRNA Aug 5.

An advisory committee reviews a pending application, so an AdComm without a PDUFA is a coverage hole
by definition. This fails the build if one exists, rather than waiting for an audit to notice.

Advisory (does not fail) when the AdComm is old enough that its PDUFA may legitimately have already
decided and been archived.
"""
import json, os, re, sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
TODAY = dt.date.today()
GRACE_DAYS = 120           # an AdComm older than this may have already decided + been archived

src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

adcomms = [r for r in arr if r.get("type") == "AdComm" and r.get("t")]
pdufa_by_tk = {}
for r in arr:
    if r.get("type") == "PDUFA" and r.get("t"):
        pdufa_by_tk.setdefault(r["t"], []).append(r)

decided = set()
if os.path.exists(DECISIONS):
    html = open(DECISIONS, encoding="utf-8", errors="replace").read()
    decided = {m.group(1) for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-\d{4}-\d{2}-\d{2}"', html)}

missing, advisory = [], []
for a in adcomms:
    tk = a["t"]
    if pdufa_by_tk.get(tk):
        continue
    try:
        age = (TODAY - dt.date.fromisoformat(str(a.get("d"))[:10])).days
    except Exception:
        age = 0
    if tk in decided or age > GRACE_DAYS:
        advisory.append(f"{tk} (AdComm {a.get('d')}, {age}d old, archived-or-stale)")
    else:
        missing.append(f"{tk} (AdComm {a.get('d')}) has no PDUFA record")

print(f"  {len(adcomms)} AdComm record(s); {len(pdufa_by_tk)} tickers with a PDUFA record")
for x in advisory:
    print(f"  (advisory) {x}")
if missing:
    print("FAIL -- AdComm without a corresponding PDUFA record:")
    for m in missing:
        print("   -", m)
    print("  An advisory committee reviews a PENDING application; add the PDUFA row.")
    sys.exit(1)
print("OK -- every current AdComm has a corresponding PDUFA record.")
