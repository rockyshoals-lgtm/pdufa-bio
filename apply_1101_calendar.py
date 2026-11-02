# -*- coding: utf-8 -*-
"""apply_1101_calendar.py -- calendar fixes from the 2026-11-01 currency + red-team pass.

1. Month pages for March 2027 and May 2027 did not exist, so EXEL (moved to 2027-03-03), AXSM (2027-05-01) and
   BBIO (2027-05-08) had no calendar row anywhere (ensure_calendar_rows.py reported them as "no month page").
   Both are cloned from the February 2027 page with the rows replaced; prev/next links are rechained
   Jan -> Feb -> Mar -> Apr -> May.
2. Rows that no longer describe a pending event:
     AGIO 2026-11-01 (moved to 2027-02-01, Agios 8-K), EXEL 2026-12-03 (moved to 2027-03-03) -- removed; the
       chain's ensure_calendar_rows places the new dates.
     RHHBY "Q4 2026 (est.)" Lunsumio + Polivy -- removed; the dataset row (2027-02-09, Genentech) replaces it.
     GILD / MRK "Q4 2026 (est.)" Trodelvy + Keytruda -- removed; approved 2026-06-24, already a decided row.
     NVS "Q4 2026 (est.)" Pluvicto, LLY "Q4 2026 (est.)" Tirzepatide -- removed; both were approved months ago
       (Pluvicto S-037 on 2026-07-31, Mounjaro S-044/S-045 on 2026-08-27, FDA letters) and now have decided rows
       on their own month pages and on /calendar.
3. BTAI IGALMI rows relabelled TEVA (BioXcel sold IGALMI to Teva; the dataset row is TEVA since this pass).
4. The December 2026 Giredestrant row linked href="#" with rel=nofollow; it now links its event page.
5. _calendar_unbacked_q4_rows.json: Lunsumio, Pluvicto, Tirzepatide, Tukysa and the two Trodelvy pages are
   resolved (sourced date, or decided with an FDA record); ABBV Rinvoq and AZN gefurulimab remain. Baseline 8 -> 2.
Facts only; not investment advice.
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CAL = os.path.join(SITE, "calendar")


def rd(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def row_re(href_pat, t_pat):
    return re.compile(r'<a class="row"[^>]*href="' + href_pat + r'"[^>]*>\s*<div class="t">' + t_pat
                      + r'(?:(?!</a>).)*</a>', re.S)


# ---- 1. new month pages
feb = rd(os.path.join(CAL, "2027", "february", "index.html"))
s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
rows = json.loads(s[s.index("["):s.rindex("]") + 1])
import sys
sys.path.insert(0, HERE)
from ensure_calendar_rows import row_html  # noqa: E402

for mon, Mon, num in (("march", "March", "03"), ("may", "May", "05")):
    out = os.path.join(CAL, "2027", mon, "index.html")
    mine = sorted([r for r in rows if str(r.get("d", "")).startswith(f"2027-{num}") and r["id"].startswith("pdufa")
                   and r.get("dp", "day") == "day" and r.get("st") in ("Upcoming", "Estimated", None)],
                  key=lambda r: r["d"])
    doc = feb.replace("February", Mon).replace("february", mon)
    gi = doc.index('<div class="grid" style="margin-top:12px">') + len('<div class="grid" style="margin-top:12px">')
    ge = doc.index('</div><div class="callout">', gi)
    doc = doc[:gi] + "".join(row_html(r) for r in mine) + doc[ge:]
    prev_, next_ = (("february", "February"), ("april", "April")) if mon == "march" else (("april", "April"), None)
    pn = f'<div class="pn"><a href="/calendar/2027/{prev_[0]}">&larr; {prev_[1]} 2027</a>'
    pn += (f'<a href="/calendar/2027/{next_[0]}">{next_[1]} 2027 &rarr;</a>' if next_ else "") + "</div>"
    doc = re.sub(r'<div class="pn">.*?</div>', pn, doc, count=1, flags=re.S)
    # ticker index block: rebuilt from this page's rows
    tks = sorted({(r.get("t") or "").upper() for r in mine})
    chip = ('<a href="/ticker/{0}" style="display:inline-block;padding:3px 8px;margin:2px;border:1px solid '
            'var(--line);border-radius:7px;font-size:12.5px;text-decoration:none" class="lit">{0}</a>')
    doc = re.sub(r"(<!--TICKERIDX:BEGIN-->.*?<div>)(?:<a href=\"/ticker/[^\"]+\"[^>]*>[^<]*</a>)*(</div>)",
                 lambda m: m.group(1) + "".join(chip.format(t) for t in tks) + m.group(2), doc, count=1, flags=re.S)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        wr(out, doc)
        print(f"  + /calendar/2027/{mon}: {len(mine)} row(s): " + ", ".join(f"{r['t']} {r['d']}" for r in mine))
    else:
        print(f"  /calendar/2027/{mon} exists, left alone")

# rechain neighbours
for mon, old, new in (("february", '<a href="/calendar/2027/april">April 2027 &rarr;</a>',
                       '<a href="/calendar/2027/march">March 2027 &rarr;</a>'),
                      ("april", '<a href="/calendar/2027/february">&larr; February 2027</a>',
                       '<a href="/calendar/2027/march">&larr; March 2027</a>')):
    p = os.path.join(CAL, "2027", mon, "index.html")
    d = rd(p)
    if old in d:
        wr(p, d.replace(old, new, 1)); print(f"  /calendar/2027/{mon}: neighbour link -> March")
p = os.path.join(CAL, "2027", "april", "index.html")
d = rd(p)
m = re.search(r'<div class="pn">(.*?)</div>', d, re.S)
if m and "/calendar/2027/may" not in m.group(1):
    d = d[:m.end(1)] + '<a href="/calendar/2027/may">May 2027 &rarr;</a>' + d[m.end(1):]
    wr(p, d); print("  /calendar/2027/april: next -> May 2027")

# ---- 2/3/4. row edits across every calendar page
REMOVE = [row_re(r"/pdufa/AGIO-mitapivat", r"AGIO &middot; 2026-11-01"),
          row_re(r"/pdufa/EXEL-zanzalintinib", r"EXEL &middot; 2026-12-03"),
          row_re(r"/ticker/RHHBY", r"RHHBY · Q4 2026 \(est\.\)</div><div class=\"d\">Lunsumio"),
          row_re(r"/ticker/GILD", r"GILD / MRK · Q4 2026 \(est\.\)</div><div class=\"d\">Trodelvy"),
          row_re(r"/ticker/NVS", r"NVS · Q4 2026 \(est\.\)</div><div class=\"d\">Pluvicto"),
          row_re(r"/ticker/LLY", r"LLY · Q4 2026 \(est\.\)</div><div class=\"d\">Tirzepatide")]
OK = '<span style="color:#5fd07a;font-weight:700">'
DECIDED = {
    "2026-07": ("NVS", "2026-07-31", "Pluvicto (lutetium Lu 177 vipivotide tetraxetan) with an ARPI - PSMA-positive metastatic hormone-sensitive prostate cancer"),
    "2026-08": ("LLY", "2026-08-27", "Mounjaro (tirzepatide) - cardiovascular risk reduction (SURPASS-CVOT)"),
}


def dec_row(t, d, drug):
    return (f'<a class="row" data-dec="1" href="/fda-decision/{t}-{d}"><div class="t">{t} &middot; {d} {OK}✓</span>'
            f'</div><div class="d">{OK}Approved</span>: {drug}</div></a>')


def insert_dated(doc, row, d):
    for m in re.finditer(r'<a class="row"[^>]*>\s*<div class="t">[A-Z./ ]+\s*(?:&middot;|·)\s*(\d{4}-\d{2}-\d{2})', doc):
        if m.group(1) > d:
            return doc[:m.start()] + row + doc[m.start():]
    last = None
    for m in re.finditer(r'<a class="row".*?</a>', doc, re.S):
        last = m
    return doc[:last.end()] + row + doc[last.end():] if last else doc


for root, _, files in os.walk(CAL):
    if "index.html" not in files:
        continue
    p = os.path.join(root, "index.html")
    rel = os.path.relpath(p, SITE).replace("\\", "/")
    d0 = d = rd(p)
    for rx in REMOVE:
        d, n = rx.subn("", d)
        if n:
            print(f"  - {rel}: removed {n} row(s) matching {rx.pattern[30:90]}")
    d = re.sub(r'(<a class="row"[^>]*href="/pdufa/BTAI-igalmi"[^>]*>\s*<div class="t">)BTAI', r"\1TEVA", d)
    d = d.replace('<a class="row" href="#" rel="nofollow"><div class="t">RHHBY &middot; 2026-12-18</div>',
                  '<a class="row" href="/pdufa/RHHBY-giredestrant-evera"><div class="t">RHHBY &middot; 2026-12-18</div>')
    targets = []
    if rel == "calendar/index.html":
        targets = list(DECIDED.values())
    else:
        mm = re.match(r"calendar/(\d{4})/(\w+)/index.html", rel)
        if mm:
            months = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
                      "october", "november", "december"]
            key = f"{mm.group(1)}-{months.index(mm.group(2)) + 1:02d}" if mm.group(2) in months else ""
            if key in DECIDED:
                targets = [DECIDED[key]]
    for t, dd, drug in targets:
        if f'/fda-decision/{t}-{dd}"' not in d:
            d = insert_dated(d, dec_row(t, dd, drug), dd)
            print(f"  + {rel}: decided row {t} {dd}")
    if d != d0:
        wr(p, d)

# ---- 5. unbacked list
UB = os.path.join(HERE, "_calendar_unbacked_q4_rows.json")
ub = json.load(io.open(UB, encoding="utf-8"))
keep = {"/pdufa/ABBV-rinvoq", "/pdufa/AZN-gefurulimab"}
before = len(ub["rows"])
ub["rows"] = [x for x in ub["rows"] if x.get("page") in keep]
if len(ub["rows"]) < ub.get("baseline_count", 99):
    ub["baseline_count"] = len(ub["rows"])
    ub["baseline_note"] += (f" Lowered to {len(ub['rows'])} on 2026-11-01: Lunsumio + Polivy is dated 2027-02-09 "
                            "(Genentech); Pluvicto (S-037, 2026-07-31), Tirzepatide/Mounjaro (S-044/S-045, 2026-08-27) "
                            "and Tukysa (2026-10-07) were decided, each with an FDA letter; Trodelvy + Keytruda was "
                            "approved 2026-06-24 (both GILD and MRK pages).")
io.open(UB, "w", encoding="utf-8").write(json.dumps(ub, indent=1, ensure_ascii=False) + "\n")
print(f"  unbacked window rows: {before} -> {len(ub['rows'])}; baseline {ub['baseline_count']}")
