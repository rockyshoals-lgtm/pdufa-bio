# -*- coding: utf-8 -*-
"""Live check of e6424cbb8 (audit 09-27)."""
import html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0927", "Cache-Control": "no-cache"}
def get(p):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=30); return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
ok = True
def chk(n, c, d=""):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d else ""))
_, bi = get("/build-info.json"); print("live:", json.loads(bi).get("commit"))
for s in ("MIRM-2026-09-25", "INCY-2026-09-25"):
    _, d = get(f"/fda-decision/{s}"); h = html.unescape(d[:d.find("</head>")])
    chk(f"{s}: fact-first description", "On Sep 25, 2026, the FDA announced its approval of Atebrioz (zilurgisertib)" in h and "third FOP treatment" in h)
    chk(f"{s}: no 'announced by the sponsor' in head", "announced by the sponsor" not in h)
st, d = get("/fda-approval-letters"); chk("/fda-approval-letters live, 38 actions", st == 200 and "38 FDA decisions" in d and "219713Orig1s004ltr.pdf" in d, f"status {st}")
_, d = get("/research/fda-decision-timing"); chk("timing page links the letters hub", 'href="/fda-approval-letters"' in d)
_, d = get("/conferences"); chk("/conferences links /conference/AASLD and /conference/SABCS", 'href="/conference/AASLD"' in d and 'href="/conference/SABCS"' in d)
_, d = get("/llms.txt"); chk("llms.txt lists /fda-approval-letters", "/fda-approval-letters" in d)
_, d = get("/sitemap.xml"); chk("sitemap has /fda-approval-letters", "/fda-approval-letters" in d)
print("\nALL PASS" if ok else "\nSOME FAILED")
