# -*- coding: utf-8 -*-
"""Live check of a25196f8a: /crl counts and shape, letters on the decision pages, 19/9/2."""
import html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0920b", "Cache-Control": "no-cache"}
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
_, bi = get("/build-info.json"); print("live commit:", json.loads(bi).get("commit"))
st, d = get("/crl"); x = text(d)
chk("/crl title 458", "458 Released CRLs" in d)
chk("/crl: 309 since approved / 149 not", "openFDA labels 309 of them as letters to applications the FDA has since approved and 149 as" in x)
chk("/crl: release-policy sentence", "That is the shape of a release policy" in x)
chk("/crl: no percentage rate", not re.search(r"\b6\d(?:\.\d)?%", x))
chk("/crl: series table 439 -> 458 +19", bool(re.search(r"2026-06-22 439 309 130 2026-08-29 458 309 149 \+19", x)))
chk("/crl: odd-named FDA file listed (URL-encoded)", "Pages%20from%20214835Orig1s000_ORIGINAL_APPROVAL_PACKAGE.pdf" in d)
for slug, needle in (("ACHV-2026-06-22", "Facility inspections."), ("UNCY-2026-06-30", "Facility inspections."), ("UNCY-2025-06-30", "dated June 27, 2025"), ("CORT-2025-12-31", "action date remains December 30, 2025")):
    st, d = get(f"/fda-decision/{slug}"); x = text(d)
    chk(f"/fda-decision/{slug}: letter block", st == 200 and needle in x and "download.open.fda.gov/crl/" in d, f"status {st}")
st, d = get("/fda-decision/ACHV-2026-06-22")
chk("ACHV title = CRL Jun 20, 2026 (FDA letter date)", "CRL Jun 20, 2026" in re.search(r"<title>([^<]*)", d).group(1))
st, d = get("/pdufa/CORT-relacorilant"); x = text(d)
chk("/pdufa/CORT-relacorilant: What the FDA said the last time", "What the FDA said the last time" in x and "drug-induced liver injury" in x)
for p, pat in (("/research/fda-decision-timing", r"20 of 31 came before the PDUFA goal date, 9 on it and 2 after"),
               ("/calendar", r"20 came before the goal date, 9 landed on it, and 2 came after"),
               ("/learn/what-is-a-pdufa-date", r"20 came before the goal date, 9 landed on it and 2 came after")):
    _, d = get(p); chk(f"{p}: 19/9/2", bool(re.search(pat, text(d))))
_, d = get("/research/fda-decision-timing"); x = text(d)
chk("timing page: ACHV row shows FDA letter date + announced", bool(re.search(r"June 20, 2026 \(FDA letter date; announced June 22, 2026\) \+0 days", x)))
_, t = get("/api/v1/events?limit=2000"); ev = json.loads(t); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
a = {r["id"]: r for r in rows}.get("pdufa_achv_2026-06-20", {})
chk("API ACHV fda_action_date 2026-06-20 + decision_source_url is the FDA PDF", a.get("fda_action_date") == "2026-06-20" and "download.open.fda.gov/crl/" in str(a.get("decision_source_url")), json.dumps({k: a.get(k) for k in ("decision_date", "fda_action_date", "decision_source")}))
print("\nALL PASS" if ok else "\nSOME FAILED")
