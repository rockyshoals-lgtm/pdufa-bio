# -*- coding: utf-8 -*-
"""Live check of the audit 10-03 acceptance list (Tier 0 + Tier 1). Times are UTC unless stated."""
import datetime as dt
import html
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"
UA = {"User-Agent": "pdufa-builder-verify/1003", "Cache-Control": "no-cache"}


def get(p):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=40)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


ok = True


def chk(n, c, d=""):
    global ok
    ok &= bool(c)
    print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d else ""))


et_today = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).date().isoformat()
_, bi = get("/build-info.json")
bi = json.loads(bi)
print("live commit:", bi.get("commit"), "built:", bi.get("built"), "| Eastern today:", et_today)
chk("/build-info built today (UTC date of build is today or Eastern today)",
    str(bi.get("built", ""))[:10] >= et_today, bi.get("built"))
chk("/build-info has data_built_at", bool(bi.get("data_built_at")), bi.get("data_built_at"))
chk("/build-info has held_since + held_leads", "held_since" in bi and "held_leads" in bi,
    f"held_since={bi.get('held_since')} leads={len(bi.get('held_leads') or [])}")

_, d = get("/pdufa/ABBV-tavapadon")
chk("/pdufa/ABBV-tavapadon says Approved", "Approved" in d and "JUVMO" in d)
st, d = get("/fda-decision/ABBV-2026-09-28")
chk("/fda-decision/ABBV-2026-09-28 live, fact-first, FDA date 2026-09-25",
    st == 200 and "was approved by the FDA on September 25, 2026" in html.unescape(d) and "2026-09-25" in d, f"status {st}")
chk("decision page cites NDA 220415 letter", "220415Orig1s000ltr.pdf" in d)

_, a = get("/api/v1/pdufa?ticker=ABBV&limit=50")
j = json.loads(a or "{}")
row = next((r for r in j.get("data", []) if r.get("id") == "pdufa_abbv_2026-12-31"), {})
chk("API row pdufa_abbv_2026-12-31 Decided/Approved", row.get("status") == "Decided" and row.get("outcome") == "Approved",
    f"{row.get('status')} {row.get('outcome')} {row.get('decision_date')}")
chk("API meta.data_built_at present", bool((j.get("meta") or {}).get("data_built_at")), (j.get("meta") or {}).get("data_built_at"))

_, c = get("/api/v1/conferences?limit=200")
cj = {r["id"]: r for r in json.loads(c or "{}").get("data", [])}
for cid, want_not in (("conf_aacr-panc_2026-09-25", "In progress"), ("conf_astro_2026-09-26", "In progress"),
                      ("conf_easd_2026-09-28", "Scheduled"), ("conf_wms_2026-09-29", "Scheduled")):
    s = (cj.get(cid) or {}).get("status")
    chk(f"API {cid} no longer '{want_not}'", s and s != want_not, s)

_, h = get("/fda-approval-letters")
chk("/fda-approval-letters lists NDA 220415", "220415" in h)
for p in ("/", "/calendar"):
    _, doc = get(p)
    chk(f"{p} stamp reads data_built_at", "data-fresh-built" in doc and "j.data_built_at" in doc)
_, dp = get("/drug/tavapadon")
chk("/drug/tavapadon live and names JUVMO", "JUVMO" in dp)
print("\nALL PASS" if ok else "\nSOME FAILED")
