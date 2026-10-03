# -*- coding: utf-8 -*-
"""CI guard: every Approved decision page opens with the fact (audit 2026-10-03, items 2.1 and 2.2).

Fails, on the RENDERED pages, when an approved decision page (price-only / outcome-unverified pages
excepted):
  1. has no LEDE block directly under the APPROVED banner, or its sentence is not one of the three
     shapes ("{Drug} was approved by the FDA on {date}", "On {date}, the FDA announced its approval of",
     "{Drug} was approved by the FDA ...; the approval was announced on {date}");
  2. says "was approved by the FDA on {date}" with a date that no FDA record holds for that page
     (API row fda_action_date, _fda_action_archive.json from Drugs@FDA, or the FDA's Novel Drug
     Approvals list);
  3. claims "the Nth novel drug approval of 2026" where row N of the FDA's list (_fda_novel_approvals.json)
     is not this drug (brand or ingredient in the lede) within 10 days, or omits the link to the list;
  4. carries an em dash in the lede.

    python tests/test_decision_lede_fact_first.py
"""
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
       "October", "November", "December"]
NOVEL_URL = "https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026"


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def load(name, default):
    p = os.path.join(HERE, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    fda = {}
    for r in rows:
        fd = (r.get("_d") or {}).get("fda_action_date")
        if fd and r.get("dcd"):
            fda.setdefault(f"{str(r.get('t')).upper()}-{r['dcd']}", set()).add(fd)
    for slug, e in load("_fda_action_archive.json", {}).items():
        if e.get("date"):
            fda.setdefault(slug, set()).add(e["date"])
    novel = {r["n"]: r for r in load("_fda_novel_approvals.json", {}).get("rows", [])}
    fails, n, nn = [], 0, 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        low = doc.lower()
        if 'class="ban ap"' not in doc or "price-only" in low or "outcome unverified" in low:
            continue
        n += 1
        lm = re.search(r'<div class="ban ap">[^<]*</div>\s*<!--FACTLEDE:BEGIN--><p class="sub fact"[^>]*>(.*?)</p><!--FACTLEDE:END-->',
                       doc, re.S)
        if not lm:
            fails.append(f"/fda-decision/{slug}: no fact-first lede directly under the APPROVED banner")
            continue
        raw = lm.group(1)
        txt = html.unescape(re.sub(r"<[^>]+>", "", raw))
        if "—" in txt:
            fails.append(f"/fda-decision/{slug}: em dash in the lede")
        a = re.match(r"^.{2,120}? was approved by the FDA on ([A-Z][a-z]+ \d{1,2}, \d{4})", txt)
        b = re.match(r"^On [A-Z][a-z]+ \d{1,2}, \d{4}, the FDA announced its approval of ", txt)
        c = re.match(r"^.{2,120}? was approved by the FDA\b[^;]*; the approval was announced on [A-Z][a-z]+ \d{1,2}, \d{4}\.$", txt)
        if not (a or b or c):
            fails.append(f"/fda-decision/{slug}: lede is not a fact-first sentence: {txt[:100]!r}")
            continue
        nm = re.search(r"the (\d+)(?:st|nd|rd|th) novel drug approval of 2026", txt)
        okdates = {pretty(x) for x in fda.get(slug, set())}
        if nm:
            nn += 1
            row = novel.get(int(nm.group(1)))
            if not row:
                fails.append(f"/fda-decision/{slug}: claims novel approval #{nm.group(1)}, not on the FDA list")
            else:
                keys = [row["brand"].lower()] + [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]{4,}", row["ingredient"])]
                pd_ = dt.date.fromisoformat(m.group(2))
                if not any(k in txt.lower() for k in keys) or not 0 <= (pd_ - dt.date.fromisoformat(row["date"])).days <= 10:
                    fails.append(f"/fda-decision/{slug}: #{nm.group(1)} on the FDA list is {row['brand']} "
                                 f"({row['ingredient']}, {row['date']}), not this page's drug")
                okdates.add(pretty(row["date"]))
            if NOVEL_URL not in raw:
                fails.append(f"/fda-decision/{slug}: novel-approval count without the link to the FDA list")
        if a and a.group(1) not in okdates:
            fails.append(f"/fda-decision/{slug}: 'approved by the FDA on {a.group(1)}' but no FDA record holds that date "
                         f"(have {sorted(okdates) or 'none'})")
    if fails:
        print(f"FAIL: {len(fails)} decision lede failure(s):")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- {n} approved decision pages open with the fact; FDA dates all FDA-sourced; {nn} novel counts match the FDA list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
