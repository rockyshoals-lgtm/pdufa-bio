# -*- coding: utf-8 -*-
"""apply_1110_novo_not_announced.py -- Mim8 (denecimig) and CagriSema: "FDA goal date not announced" (David, 2026-11-10).

Novo Nordisk's Q3 2026 6-K (Nov 4, https://www.sec.gov/Archives/edgar/data/353278/000162828026069805/caq32026.htm)
gives neither application a goal date. Denecimig: "In the US, the regulatory review of denecimig is still ongoing, and
pending regulatory decision, a US launch is expected in H1 2027." CagriSema: "preparing for the US launch of CagriSema
in early 2027, subject to regulatory approval". Our rows showed "2026" (Mim8; the event page said "December 2026") and
"Dec 2026" (CagriSema; the NVO hub printed "Dec 31, 2026"), windows no Novo document states. David's ruling (11-10):
relabel both "date not announced"; they leave the calendar grid and every count of dated goals.

  dataset.mjs   st "Upcoming" -> "Under review"; _d.goal_date = "not announced"; d/dp kept only as the row's sort key
  data.js       both removed from SLATE.catalysts (the slate is the calendar's dated forward list)
  calendar      the CagriSema row removed from /calendar and /calendar/2026/december (Mim8 had no grid row)
  event pages   /pdufa/NVO-am833 and /pdufa/NVO-mim8 state "FDA goal date not announced" with the 6-K sentence
Facts only, not investment advice.
"""
import io, json, os, re

H = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(H, "pdufa_site_src")
SIXK = "https://www.sec.gov/Archives/edgar/data/353278/000162828026069805/caq32026.htm"
Q = {"pdufa_nvo_mim8_2026-09-30": ("In the US, the regulatory review of denecimig is still ongoing, and pending regulatory "
                                   "decision, a US launch is expected in H1 2027."),
     "pdufa_nvo_2026-12-31": "preparing for the US launch of CagriSema in early 2027, subject to regulatory approval"}
URL = {"pdufa_nvo_mim8_2026-09-30": "NVO-mim8", "pdufa_nvo_2026-12-31": "NVO-am833"}

# 1. dataset
p = os.path.join(S, "api", "v1", "dataset.mjs"); s = io.open(p, encoding="utf-8").read()
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j]); n = 0
for r in rows:
    if r.get("id") in Q:
        r["st"] = "Under review"
        d = r.setdefault("_d", {})
        d["goal_date"] = "not announced"
        d["source"] = "Novo Nordisk 6-K 2026-11-04 (Q3 2026 company announcement)"
        d["source_url"] = SIXK
        d["source_quote"] = Q[r["id"]]
        d["date_note"] = ("FDA goal date not announced. Novo Nordisk's Q3 2026 6-K (Nov 4) states no goal date; it gives a "
                          "US launch expectation only. Relabelled 2026-11-10 (David); the row's date field is a sort key, "
                          "not a goal date, and the row is excluded from the calendar and from counts of dated goals.")
        n += 1
io.open(p, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("dataset rows relabelled:", n)

# 2. slate
p = os.path.join(S, "api", "data.js"); t = io.open(p, encoding="utf-8").read()
k = t.find("const SLATE=") + len("const SLATE=")
o, e = json.JSONDecoder().raw_decode(t[k:])
before = len(o["catalysts"])
o["catalysts"] = [c for c in o["catalysts"] if not (c.get("ticker") == "NVO" and re.search(r"cagrisema|am833|mim8|denecimig",
                                                                                             str(c.get("drug")), re.I))]
io.open(p, "w", encoding="utf-8").write(t[:k] + json.dumps(o, separators=(",", ":")) + t[k + e:])
print("slate catalysts removed:", before - len(o["catalysts"]))

# 3. calendar grid rows
for rel in ("calendar/index.html", "calendar/2026/december/index.html"):
    p = os.path.join(S, rel); h = io.open(p, encoding="utf-8").read()
    h2, m = re.subn(r'<a class="row" href="/pdufa/NVO-(?:am833|mim8)">.*?</a>', "", h, flags=re.S)
    io.open(p, "w", encoding="utf-8").write(h2); print(f"{rel}: {m} row(s) removed")

# 4. event pages
for rid, slug in URL.items():
    p = os.path.join(S, "pdufa", slug, "index.html"); h = io.open(p, encoding="utf-8").read(); o_ = h
    h = re.sub(r"FDA decision \(PDUFA\) target [A-Z][a-z]+ 2026", "FDA goal date not announced", h)
    h = re.sub(r"(<span>FDA PDUFA target date</span><b>)[^<]*(</b>)", r"\g<1>Not announced\g<2>", h)
    h = re.sub(r"All December 2026 PDUFA dates &rarr;", "All upcoming PDUFA dates &rarr;", h)
    h = h.replace('href="/calendar/2026/december"', 'href="/calendar"')
    note = (f'<!--NOGOAL:BEGIN--><div class="card" style="margin:10px 0;border-color:#e3ba5e"><b>No FDA goal date has been '
            f'announced.</b> Novo Nordisk&#x27;s latest report (<a href="{SIXK}" rel="noopener">Q3 2026 6-K, November 4, '
            f'2026</a>) says: &ldquo;{Q[rid]}&rdquo; That is a launch expectation, not the FDA&#x27;s goal date, so this '
            f'application is not on the calendar. We will add the date when Novo Nordisk or the FDA states it.</div><!--NOGOAL:END-->')
    if "<!--NOGOAL:BEGIN-->" in h:
        h = re.sub(r"<!--NOGOAL:BEGIN-->.*?<!--NOGOAL:END-->", lambda _: note, h, flags=re.S)
    else:
        h = re.sub(r"(</h1>)", lambda m: m.group(1) + note, h, count=1)
    h = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{'Mim8 (denecimig)' if 'mim8' in slug else 'CagriSema'} FDA goal date: "
               f"not announced (Novo Nordisk) | pdufa.bio</title>", h, count=1)
    io.open(p, "w", encoding="utf-8").write(h); print(slug, "page updated" if h != o_ else "page unchanged")
