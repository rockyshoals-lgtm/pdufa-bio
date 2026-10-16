# -*- coding: utf-8 -*-
"""CI guard: every /calendar row is backed by the data, and each month sentence is ordered and honest (audit 2026-10-16).

The calendar grids are patched in place, never regenerated. Retiring four false decision pages on 2026-10-15 left
their rows behind on /calendar: Camzyos "pending" on June 1 (the acceptance day), Miplyffa "pending" on June 8 for
ZVRA and XOMA (a patent listing), and an LGND "Approved: Miplyffa" row linking a FILSPARI page. The brepocitinib goal
row (09-30) linked the Tukysa page. /calendar/2026/june labelled the ACHV cytisinicline row "Custirsen" and the IONS
olezarsen row "Donidalorsen". The month sentences named dates out of order ("Oct 15, Oct 26, Oct 17") and named 5 of
November's 12 still-ahead rows as if complete. Over /calendar and every /calendar/2026/<month>, fails when:
  1. a row not marked decided has no dataset PDUFA row with that ticker and date;
  2. a decided row links a decision page whose "Drug / candidate" shares no word with the row's drug;
  3. a row matching a dataset row (ticker + date) names a drug sharing no word with that row's name/brand/INN/indication;
  4. (/calendar) a month sentence names dates out of order, names a passed date as due, or reads as complete while
     the month holds more still-ahead rows than it names (it must say "N of them are still ahead, including").
  5. a month/quarter row is shown pending while the archive holds its approval (same matcher as mark_calendar_period_rows).
Plants: PLANT_CAL=orphan | wrongpage | order | wrongname | period must each FAIL.

    python tests/test_calendar_rows_backed.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
STOP = {"with", "plus", "and", "the", "for", "injection", "tablets", "oral", "approved", "approval", "label",
        "update", "expanded", "indication", "patients", "adults", "combination", "therapy", "treatment"}
LABEL = re.compile(r"\s*([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*)\s*·\s*(\d{4}-\d{2}-\d{2})")
MLABEL = re.compile(r"\s*[A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*\s*·\s*(?:[A-Z][a-z]{2}|Q\d|H\d) \d{4}")
PER = re.compile(r"\s*([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*)\s*·\s*((?:[A-Z][a-z]{2}|Q\d|H\d) (\d{4}))")
_argv, sys.argv = sys.argv, sys.argv[:1]
import mark_calendar_period_rows as MP  # noqa: E402
sys.argv = _argv
BY_TK = MP.M.load_decisions()


def plant_period(rel, ttxt):
    """PLANT_CAL=period: pretend the archive decided the Ultomiris IgAN row (still pending) -- must FAIL."""
    return os.environ.get("PLANT_CAL") == "period" and rel == "calendar" and ttxt.startswith("AZN · Dec 2026")


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", html.unescape(str(s or "")).lower()) if w not in STOP}


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def page_drug(href):
    """(drug, whole page text). A code-named row (ARV-471) is the same product when the page itself names that code."""
    p = os.path.join(SITE, href.strip("/").replace("/", os.sep), "index.html")
    if not os.path.exists(p):
        return None
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", doc, re.S)
    if not m:
        return None
    return txt(m.group(1)) + " " + " ".join(re.findall(r"\b[A-Z]{2,5}-?\d{2,6}[A-Z]?\b", txt(doc)))


def check_page(rel, cal, by_key, today, fails, stats, sentences):
    parts = re.split(r'<div class="mhead">([A-Za-z]+ \d{4})</div>', cal)
    if len(parts) == 1:
        parts = ["", rel, cal]
    for k in range(1, len(parts), 2):
        mon, grid = parts[k], parts[k + 1]
        ahead = 0
        for m in re.finditer(r'<a class="row"([^>]*)>(.*?)</a>', grid, re.S):
            attrs, body = m.group(1), m.group(2)
            t_m = re.search(r'<div class="t">(.*?)</div>', body, re.S)
            ttxt = txt(t_m.group(1)) if t_m else ""
            href = (re.search(r'href="([^"]+)"', attrs) or [None, ""])[1]
            decided = "data-dec" in attrs or href.startswith("/fda-decision/")
            lab = LABEL.match(ttxt)
            if not lab:
                if MLABEL.match(ttxt) and not decided:
                    ahead += 1
                    # 5. a month/quarter row still shown pending while the archive holds its approval (Tavapadon,
                    #    Kerendia T1D and Tukysa on 2026-10-16). Same matcher as the step that marks them.
                    pm = PER.match(ttxt)
                    body = (re.search(r'<div class="d">(.*?)</div>', body, re.S) or [None, ""])[1]
                    hit = MP.find(BY_TK, pm.group(1), body, MP.period_end(pm.group(2), pm.group(3))) if pm else None
                    if hit or plant_period(rel, ttxt):
                        fails.append(f"/{rel} {mon}: '{ttxt[:30]}' '{txt(body)[:45]}' is shown pending but "
                                     f"/fda-decision/{hit[2] if hit else '?'}-{hit[0] if hit else '?'} decided it")
                continue
            stats["rows"] += 1
            tks, iso = [x.strip() for x in lab.group(1).split("/")], lab.group(2)
            drug = txt((re.search(r'<div class="d">(.*?)</div>', body, re.S) or [None, ""])[1])
            drug = re.sub(r"^(Approved|CRL)\s*:\s*", "", drug)
            cands = [r for tk in tks for r in by_key.get((tk, iso), [])]
            if cands and toks(drug) and not any(
                    toks(drug) & toks(" ".join([str(r.get("name") or "")] + [str((r.get("_d") or {}).get(f) or "")
                                                for f in ("brand", "inn", "indication")])) for r in cands):
                fails.append(f"/{rel} {mon}: row {lab.group(0).strip()} names '{drug[:45]}'; the dataset row is "
                             f"'{cands[0].get('name')}'")
            if decided:
                stats["dec"] += 1
                pd = page_drug(href) if href.startswith("/fda-decision/") else None
                if pd and toks(drug) and toks(pd) and not (toks(drug) & toks(pd)):
                    fails.append(f"/{rel} {mon}: decided row {lab.group(0).strip()} '{drug[:45]}' links {href}, a page "
                                 f"for '{pd[:45]}'")
                continue
            if not cands:
                fails.append(f"/{rel} {mon}: row {lab.group(0).strip()} '{drug[:45]}' is not decided and has no dataset "
                             "PDUFA row")
            if "(est.)" in ttxt or iso >= today:
                ahead += 1
        if not sentences:
            continue
        sm = re.search(r'<p class="msent"[^>]*>(.*?)</p>', grid, re.S)
        if not sm:
            continue
        s = txt(sm.group(1))
        named = re.findall(r"\([A-Z/]+, (\w{3}) (\d{1,2})\)", s)
        if not named:
            continue
        stats["sent"] += 1
        isos = [f"{mon[-4:]}-{MON.index(a):02d}-{int(b):02d}" for a, b in named]
        if isos != sorted(isos):
            fails.append(f"/{rel} {mon}: month sentence names dates out of order: "
                         f"{', '.join(a + ' ' + b for a, b in named)}")
        if any(x < today for x in isos):
            fails.append(f"/{rel} {mon}: month sentence names a passed date as due: {s[:160]}")
        cm = re.search(r"(\d+) of them (?:are|is) still ahead, including", s)
        if cm:
            if int(cm.group(1)) != ahead:
                fails.append(f"/{rel} {mon}: sentence says {cm.group(1)} still ahead; the grid has {ahead}")
        elif len(named) != ahead:
            fails.append(f"/{rel} {mon}: sentence names {len(named)} as the month's decisions but the grid has {ahead} "
                         "still ahead (say 'N of them are still ahead, including')")


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    by_key = {}
    for r in rows:
        if r.get("type") == "PDUFA":
            for t in str(r.get("t") or "").split("/"):
                by_key.setdefault((t.strip(), str(r.get("d") or "")[:10]), []).append(r)
    today = eastern_today().isoformat()
    plant = os.environ.get("PLANT_CAL", "")
    fails, stats = [], {"rows": 0, "dec": 0, "sent": 0}
    pages = ["calendar/index.html"] + sorted(os.path.relpath(p, SITE).replace(os.sep, "/")
                                             for p in glob.glob(os.path.join(SITE, "calendar", "2026", "*", "index.html")))
    for rel in pages:
        cal = io.open(os.path.join(SITE, rel), encoding="utf-8", errors="replace").read()
        main_page = rel == "calendar/index.html"
        if main_page and plant == "orphan":
            cal = cal.replace('<div class="mhead">December 2026</div>',
                              '<div class="mhead">December 2026</div><a class="row" href="/pdufa/ZZZQ"><div class="t">'
                              'ZZZQ &middot; 2026-12-02</div><div class="d">Planted drug</div></a>', 1)
        if main_page and plant == "wrongpage":
            cal = re.sub(r'(<a class="row" data-dec="1" href=")/fda-decision/PFE-2026-08-27', r"\1/fda-decision/PFE-2026-10-07", cal, 1)
        if main_page and plant == "order":
            cal = re.sub(r"(due to decide on )([^.]*?\([A-Z/]+, \w{3} \d+\)), ([^.]*?\([A-Z/]+, \w{3} \d+\))", r"\1\3, \2", cal, 1)
        if rel.endswith("june/index.html") and plant == "wrongname":
            cal = cal.replace("Cytisinicline: Smoking cessation (ORCA-3)", "Custirsen: Non-Small Cell Lung Cancer", 1)
        check_page(rel.replace("/index.html", ""), cal, by_key, today, fails, stats, main_page)
    if fails:
        print(f"FAIL: {len(fails)} calendar row or month-sentence failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {stats['rows']} rows across {len(pages)} calendar pages backed by the data ({stats['dec']} decided rows "
          f"link a page naming the same drug); {stats['sent']} /calendar month sentence(s) in date order and complete "
          "or counted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
