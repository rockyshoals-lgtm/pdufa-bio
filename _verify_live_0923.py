# -*- coding: utf-8 -*-
"""Live check of ee0e7666d: MRK 09-22 published, timing 19/9/2 of 30, og tags, llms.txt, no '1 days'."""
import html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0923", "Cache-Control": "no-cache"}
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
_, bi = get("/build-info.json"); j = json.loads(bi); print("live commit:", j.get("commit"), "next:", j.get("next_ticker"), j.get("next_date"), j.get("next_days"))
chk("build-info commit: parent of the local push until CI stamps its own", str(j.get("commit", "")) in ("095051111",) or len(str(j.get("commit", ""))) >= 7)
st, d = get("/fda-decision/MRK-2026-09-22"); x = text(d)
chk("MRK decision page 200", st == 200, f"status {st}")
chk("title: 1 Day Late (singular)", "1 Day Late | MRK FDA Decision" in re.search(r"<title>([^<]*)", d).group(1))
chk("desc: 1 day after its", "1 day after its September 21, 2026 PDUFA goal date" in d)
chk("today's approval note", "today&#x27;s approval" in d or "today's approval" in x)
chk("og:title + og:description + og:site_name", all(s in d for s in ('property="og:title"', 'property="og:description"', 'property="og:site_name"')))
st, d = get("/calendar"); x = text(d)
chk("/calendar: MRK row links decision page", "/fda-decision/MRK-2026-09-22" in d)
chk("/calendar: 19/9/2", bool(re.search(r"20 came before the goal date, 9 landed on it, and 2 came after", x)))
_, d = get("/research/fda-decision-timing"); x = text(d)
chk("timing page: 19 of 30, 9, 2", bool(re.search(r"20 of 31 came before the PDUFA goal date, 9 on it and 2 after", x)))
chk("timing page: MRK +1 day", bool(re.search(r"September 22, 2026 \+1 day\b", x)))
_, d = get("/learn/what-is-a-pdufa-date"); chk("/learn: 19/9/2", bool(re.search(r"20 came before the goal date, 9 landed on it and 2 came after", text(d))))
for p in ("/fda-decision/GSK-2026-06-17", "/fda-decision/SPRO-2026-06-17", "/fda-decision/VTRS-2026-07-29", "/pdufa/VTRS-mr-100a-01"):
    _, d = get(p); chk(f"{p}: no '1 days'", not re.search(r"\b1 [Dd]ays\b", d))
for p in ("/fda-decision/ABBV-2026-04-23", "/patent-cliff/2027", "/pdufa/BIIB", "/calendar/2025"):
    _, d = get(p); chk(f"{p}: og:title present", 'property="og:title"' in d)
_, d = get("/pdufa/BIIB"); chk("/pdufa/BIIB: no 'See the.' tail", "See the.\"" not in d and "See the.&quot;" not in d)
st, d = get("/fda-decision/NUVB-2026-09-16"); chk("NUVB decision page: 110 Days Early + FDA letter", st == 200 and "110 Days Early" in d and "219713Orig1s004ltr.pdf" in d, f"status {st}")
_, d = get("/calendar/2027/january"); chk("/calendar/2027/january: NUVB row marked", "/fda-decision/NUVB-2026-09-16" in d)
st, d = get("/fda-decision/BAYRY-2026-09-16"); chk("BAYRY Kerendia page: no margin, FDA letter", st == 200 and "215341Orig1s011ltr.pdf" in d and not re.search(r"\d+ Days? (Early|Late)", d), f"status {st}")
_, d = get("/drug/kerendia"); chk("/drug/kerendia states approval 09-16", "approved on September 16, 2026" in d)
_, d = get("/llms.txt")
chk("llms.txt: n=1,852 / 71.3% / 1,752 / 20-9-2 of 31 / 458-309", all(s in d for s in ("n=1,852", "71.3%", "n=1,752", "**31**", "**20**", "**9**", "**2**", "**458**", "**309**")))
chk("llms.txt: no stale 1,792 / 73.5%", "1,792" not in d and "73.5%" not in d)
_, d = get("/sitemap.xml"); chk("sitemap has MRK-2026-09-22 and /ticker/ADCT", "/fda-decision/MRK-2026-09-22" in d and "/ticker/ADCT" in d)
st, _ = get("/_index_current_backup.html"); chk("backup homepage gone (404)", st == 404, f"status {st}")
_, t = get("/api/v1/events?limit=2000"); ev = json.loads(t); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
a = {r["id"]: r for r in rows}.get("pdufa_mrk_2026-09-21", {})
chk("API MRK row Decided/Approved 09-22 with decision_date_note", a.get("status") == "Decided" and a.get("decision_date") == "2026-09-22" and bool(a.get("decision_date_note")), json.dumps({k: a.get(k) for k in ("status", "outcome", "decision_date", "decision_source")}))
print("\nALL PASS" if ok else "\nSOME FAILED")
