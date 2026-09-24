# -*- coding: utf-8 -*-
"""Live check of bcd30fe94 against the 09-20 audit's four acceptance criteria."""
import datetime as dt, html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0920", "Cache-Control": "no-cache"}
def get(p):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=30); return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", {}
def text(d):
    d = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", d); return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d)))
ok = True
def chk(n, c, d=""):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d else ""))

# item 1
_, t, _ = get("/api/v1/events?limit=2000"); ev = json.loads(t); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
tlx = {r["id"]: r for r in rows}["pdufa_tlx_2026-09-11"]
chk("API TLX decision_date_unsourced true + note present", tlx.get("decision_date_unsourced") is True and bool(tlx.get("decision_date_note")), str(tlx.get("decision_date_note"))[:80])
chk("API exposes decision_source_url", bool(tlx.get("decision_source_url")), str(tlx.get("decision_source_url"))[:70])
_, d, _ = get("/research/fda-decision-timing"); x = text(d)
chk("timing page: TLX not listed", "TLX-2026-09-14" not in d)
chk("timing page: 19 of 29 / 7 / 3", bool(re.search(r"19 of 29 came before the PDUFA goal date, 7 on it and 3 after", x)))
chk("timing page names the exclusion", "TLX (the date held is the sponsor" in x)
for p, pat in (("/calendar", r"Of the 29 FDA decisions in 2026[^.]*19 came before the goal date, 7 landed on it, and 3 came after"),
               ("/learn/what-is-a-pdufa-date", r"29 sourced 2026 decisions[^.]*19 came before the goal date, 7 landed on it and 3 came after")):
    _, d, _ = get(p); chk(f"{p}: 29/19/7/3", bool(re.search(pat, text(d))))
_, d, _ = get("/fda-decision/TLX-2026-09-14"); x = text(d)
chk("TLX decision title = Approval Announced", "Approval Announced Sep 14, 2026" in re.search(r"<title>([^<]*)", d).group(1))
chk("TLX decision page: no margin", not re.search(r"\b3 days (after|late)\b|3 Days Late", x))
_, d, _ = get("/pdufa/TLX"); x = text(d)
chk("/pdufa/TLX: goal date kept, no 'passed' banner, announced wording", "goal date for this application was 2026-09-11" in x and "no decision has been disclosed" not in x and "announced" in x)
# item 2
_, d, _ = get("/fda-this-month"); x = text(d)
bad=[m.group(0) for m in re.finditer(r"Ahead of its (?:September 30|November 30) goal date[^.]{0,120}", x) if re.search(r"\b(TAK|PFE|ROIV|PTGX|BAYRY)\b", m.group(0))]
chk("/fda-this-month: no goal DAY stated for TAK/PFE/ROIV/PTGX/BAYRY (coarse rows)", not bad, "; ".join(bad)[:150])
chk("/fda-this-month: window wording for TAK", bool(re.search(r"within the window the sponsor had given \(the third quarter of 2026[^)]*\), the FDA approved Oveporexton", x)))
# item 3
st, t, h = get("/build-info.json"); bi = json.loads(t) if st == 200 else {}
et = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).date()   # EDT
want = (dt.date.fromisoformat(bi["next_date"]) - et).days if bi.get("next_date") else None
chk("build-info served by function (served_at present)", st == 200 and "served_at" in bi, f"status {st} keys {sorted(bi)[:6]}")
chk(f"build-info next_days == {want} for Eastern {et}", bi.get("next_days") == want, json.dumps({k: bi.get(k) for k in ('next_ticker','next_date','next_days','next_status','as_of_eastern')}))
# Vercel consumes s-maxage at the edge and strips it from the response; max-age=0 to the client is what we want
chk("build-info not client-cached (max-age=0) and served via Vercel edge", "max-age=0" in str(h.get("Cache-Control", h.get("cache-control", ""))) and any(k.lower()=="x-vercel-cache" for k in h), str(h.get("Cache-Control", h.get("cache-control"))))
# item 4
_, d, _ = get("/fda-this-month"); m = re.search(r'name="description" content="([^"]*)"', d).group(1)
chk("/fda-this-month meta counts 2 dates", m.startswith("2 FDA decision dates remain"), m[:70])
# ABEO
_, d, _ = get("/pdufa/ABEO"); x = text(d)
chk("/pdufa/ABEO shows Approved 2026-09-17", "Approved" in x and "is under FDA review" not in x)
print("\nALL PASS" if ok else "\nSOME FAILED")
