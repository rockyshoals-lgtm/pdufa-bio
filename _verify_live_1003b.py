# -*- coding: utf-8 -*-
"""Live check of the 10-03 Tier 2-4 pass."""
import html
import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"
UA = {"User-Agent": "pdufa-builder-verify/1003b", "Cache-Control": "no-cache"}


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


_, bi = get("/build-info.json")
print("live:", json.loads(bi).get("commit"))
_, d = get("/fda-decision/ABBV-2026-09-28")
t = html.unescape(d)
chk("2.1/2.2 JUVMO lede: FDA date + 43rd novel approval", "JUVMO (tavapadon) was approved by the FDA on September 25, 2026 for Parkinson" in t and "43rd novel drug approval of 2026" in t)
st, d = get("/fda-decision/RHHBY-2026-09-25")
chk("2.6 Gazyva page live, FDA-dated", st == 200 and "Gazyva (obinutuzumab) was approved by the FDA on September 25, 2026" in html.unescape(d), f"status {st}")
_, d = get("/fda-decision/AMPH-2026-02-24")
chk("4.7 no cut title (Ipratropium)", "Ipratropium Bromide HFA Inhalation Aerosol" in d and "Inhala Approved" not in d)
_, d = get("/fda-this-month")
chk("3.1 /fda-this-month lists Sep 25 by FDA date with JUVMO", 'id="fda-2026-09-25"' in d and "ABBV-2026-09-28" in d.split('id="fda-2026-09-25"')[1][:2000])
_, d = get("/fda-approval-letters")
m = re.search(r"(\d+) FDA decisions", d)
chk("3.1 /fda-approval-letters day-by-day + 81 actions", 'id="d-2026-09-25"' in d and m and int(m.group(1)) >= 81, m.group(1) if m else "?")
_, d = get("/decisions")
chk("3.2 /decisions links the letters hub", 'href="/fda-approval-letters"' in d)
_, d = get("/conference/AASLD")
chk("3.4 AASLD lede", "AASLD The Liver Meeting 2026 takes place November 5 to 9, 2026 in Denver" in html.unescape(d))
_, d = get("/fda-decision/RVMD-2026-08-26")
chk("4.1 13F block on RVMD (Baker Bros, quarter ended June 30, 2026)", "Specialist biotech funds, latest 13F" in d and "Baker Bros. Advisors" in d)
_, d = get("/adcomm")
chk("4.2 /adcomm FR history", "Federal Register notices" in d and "federalregister.gov" in d)
st, d = get("/patent-cliff/exclusivity")
chk("4.3 /patent-cliff/exclusivity live", st == 200 and "Regulatory exclusivity cliff" in d, f"status {st}")
_, d = get("/crl")
chk("4.5 /crl shows sections from the PDFs", "Sections addressed (from the PDF)" in d and "Facility Inspections" in d)
_, a = get("/api/v1/readouts?limit=1000")
sts = {}
for r in json.loads(a or "{}").get("data", []):
    sts[r.get("status")] = sts.get(r.get("status"), 0) + 1
chk("4.6 API serves registry / window-passed statuses", sts.get("Completed per registry", 0) > 0 and sts.get("Window passed", 0) > 0, str(sts))
_, c = get("/calendar/2026/october")
chk("calendar: Tecentriq Oct 9 not marked Approved", not re.search(r"RHHBY-2026-09-25\"><div class=\"t\">RHHBY &middot; 2026-10-09", c))
_, p = get("/pdufa/RHHBY-gazyva")
chk("Gazyva lupus event page not bannered with the INS approval", "DECBAN:BEGIN" not in p)
_, p = get("/pdufa/ARQT-zoryve")
chk("ARQT-zoryve (infant AD, 2027-02-23) pending, no June approval text", "approved by the FDA on June 29, 2026" not in p and "Feb 23, 2027" in p)
print("\nALL PASS" if ok else "\nSOME FAILED")
