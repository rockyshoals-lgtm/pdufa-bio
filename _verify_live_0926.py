# -*- coding: utf-8 -*-
"""Live check of the 09-26 push: Atebrioz, PHAR 2027, timing 29: 18/10/1 from FDA records, head markup."""
import html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0926", "Cache-Control": "no-cache"}
def get(p):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=30); return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
def text(d):
    d = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", d); return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d)))
ok = True
def chk(n, c, d=""):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d else ""))
_, bi = get("/build-info.json"); j = json.loads(bi); print("live:", j.get("commit"), "next:", j.get("next_ticker"), j.get("next_date"))
chk("next pointer no longer names a decided event", j.get("next_ticker") not in ("INCY", "MIRM"), f"{j.get('next_ticker')} {j.get('next_date')}")
for s in ("MIRM-2026-09-25", "INCY-2026-09-25"):
    st, d = get(f"/fda-decision/{s}"); x = text(d)
    chk(f"/fda-decision/{s}: Atebrioz, FOP 12+, PRV, FDA notice", st == 200 and "Atebrioz" in x and "12 years and older" in x
        and "Priority Review Voucher" in x and "fibrodysplasia-ossificans-progressiva" in d, f"status {st}")
_, t = get("/api/v1/events?limit=3000"); ev = json.loads(t); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
a = {r["id"]: r for r in rows}
for i in ("pdufa_mirm_2026-09-26", "pdufa_incy_2026-09-26"):
    r = a.get(i, {}); chk(f"API {i} Decided/Approved 2026-09-25", r.get("status") == "Decided" and r.get("decision_date") == "2026-09-25", str({k: r.get(k) for k in ("status", "decision_date")}))
r = a.get("pdufa_phar_2027-01-30", {}); chk("API PHAR 2027-01-30 Upcoming with 6-K source", r.get("status") == "Upcoming" and "000182831626000041" in str(r.get("source_url")), str({k: r.get(k) for k in ("status", "source_url")}))
r = a.get("pdufa_mrk_2026-09-21", {}); chk("API MRK fda_action_date 2026-09-21", r.get("fda_action_date") == "2026-09-21", str(r.get("fda_action_date")))
_, d = get("/calendar/2027/january"); chk("/calendar/2027/january: PHAR row, not marked approved", "PHAR &middot; 2027-01-30" in d and "/fda-decision/PHAR-2026-09-11\"><div class=\"t\">PHAR &middot; 2027-01-30" not in d)
_, d = get("/pdufa/PHAR-joenja"); chk("/pdufa/PHAR-joenja pending, Jan 30 2027", "Jan 30, 2027" in d and "&#10003; Approved" not in d)
pat = {"/research/fda-decision-timing": r"18 of 29 came before the PDUFA goal date, 10 on it and 1 after",
       "/calendar": r"18 came before the goal date, 10 landed on it, and 1 came after",
       "/learn/what-is-a-pdufa-date": r"18 came before the goal date, 10 landed on it and 1 came after"}
for p, rx in pat.items():
    _, d = get(p); chk(f"{p}: 18/10/1 of 29", bool(re.search(rx, text(d))))
_, d = get("/research/fda-decision-timing"); x = text(d)
chk("timing page: 29 of 29 from the FDA's record, GSK/SPRO merged", "29 of 29 action dates on this page are taken from the FDA" in x and "GSK/SPRO" in x)
chk("timing page: median 3 days before", "median decision landed 3 days before" in x)
_, d = get("/fda-decision/MRK-2026-09-22"); chk("MRK title: Approved Sep 21, On Goal Date + FDA record block", "Approved Sep 21, 2026, On Goal Date" in d and "FDA record of the action" in d)
_, d = get("/fda-decision/TLX-2026-09-14"); chk("TLX title: Approved Sep 11, On Goal Date", "Approved Sep 11, 2026, On Goal Date" in d)
_, d = get("/fda-decision/LNTH-2026-08-13"); chk("LNTH: no StockTitan, FDA letter cited", "stocktitan" not in d and "220496Orig1s000ltr.pdf" in d)
_, d = get("/fda-decision/ABBV-2026-04-23"); chk("head markup: no tag spliced into the description", not re.search(r'"<meta', d[:d.find("</head>")]))
_, d = get("/llms.txt"); chk("llms.txt: 18 / 10 / 1 of 29", "**29**" in d and "**18**" in d and "**10**" in d)
print("\nALL PASS" if ok else "\nSOME FAILED")
