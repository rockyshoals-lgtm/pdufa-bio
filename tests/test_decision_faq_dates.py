# -*- coding: utf-8 -*-
"""CI guard: a decision-page FAQ says "the FDA approved ... on {date}" only with the FDA's own date (red team 10-04).

The FAQ answered "The FDA approved the application for JUVMO (tavapadon) on September 28, 2026" -- the day
AbbVie announced it; the FDA's letter is dated September 25. Fails, on the rendered pages' FAQPage JSON-LD,
when an answer states "The FDA approved ... on <date>" or "On <date> the FDA issued a Complete Response
Letter" and no FDA record (API fda_action_date, or _fda_action_archive.json) holds that date for the page,
or when an answer carries a cut drug name (unbalanced parenthesis).

    python tests/test_decision_faq_dates.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    fda = {}
    for r in rows:
        d = r.get("_d") or {}
        if d.get("fda_action_date") and r.get("dcd") and not d.get("decision_date_unsourced"):
            fda.setdefault(f"{str(r['t']).upper()}-{r['dcd']}", set()).add(pretty(d["fda_action_date"]))
    ap = os.path.join(HERE, "_fda_action_archive.json")
    for slug, e in (json.load(io.open(ap, encoding="utf-8")) if os.path.exists(ap) else {}).items():
        if e.get("date"):
            fda.setdefault(slug, set()).add(pretty(e["date"]))
    vp = os.path.join(HERE, "_decision_verification.json")
    for slug, v in ((json.load(io.open(vp, encoding="utf-8")).get("results") or {}) if os.path.exists(vp) else {}).items():
        ev = (v or {}).get("evidence") or {}
        if ev.get("kind") == "approval" and ev.get("approval_date") and "Drugs@FDA" in str(ev.get("source_label")):
            fda.setdefault(slug, set()).add(pretty(ev["approval_date"]))
    fails, n = [], 0
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'<!--DFAQ:BEGIN-->.*?application/ld\+json">(.*?)</script>', doc, re.S)
        if not m:
            continue
        n += 1
        for q in json.loads(m.group(1)).get("mainEntity", []):
            a = q["acceptedAnswer"]["text"]
            for dm in re.finditer(r"The FDA approved the application for .{2,90}? on ([A-Z][a-z]+ \d{1,2}, \d{4})|"
                                  r"On ([A-Z][a-z]+ \d{1,2}, \d{4}) the FDA issued a Complete Response Letter|"
                                  r"The FDA decision came on ([A-Z][a-z]+ \d{1,2}, \d{4})", a):
                day = next(g for g in dm.groups() if g)
                if day not in fda.get(slug, set()):
                    fails.append(f"/fda-decision/{slug}: FAQ says the FDA acted on {day}; no FDA record holds that date")
            if (q["name"] + a).count("(") != (q["name"] + a).count(")"):
                fails.append(f"/fda-decision/{slug}: FAQ carries a cut name: {q['name'][:80]!r}")
    if fails:
        print(f"FAIL: {len(fails)} FAQ date/name failure(s):")
        for f in sorted(set(fails))[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision FAQs: every 'the FDA approved/issued ... on' date is the FDA's own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
