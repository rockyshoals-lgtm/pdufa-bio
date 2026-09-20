# -*- coding: utf-8 -*-
"""CI guard: no rendered surface states a goal DAY for a row whose precision is not day.

Audit 09-20 P0-B. /fda-this-month said "Ahead of its September 30 goal date, on August 5, the
FDA approved Oveporexton (TAK)" for a row whose sponsor said "third quarter of calendar year
2026" and whose API `date` is null. Same for PFE, PTGX (Q3) and BAYRY ("November 30", withdrawn
09-14 -- no Bayer filing states it). The dataset keeps a coarse row's `d` as the END of its
window; the API nulls `date` unless precision is day; this renderer read `d` as a day.

THE INVARIANT. For every PDUFA row with dp != "day", no indexable page may print
"<Month> <D> goal date" (or "goal date of <Month> <D>") where <Month> <D> is that row's window
end (`d`) -- next to that row's ticker or drug name.

    python tests/test_no_goal_day_from_coarse_row.py
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
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
PAGES = ["fda-this-month/index.html", "index.html", "calendar/index.html", "decisions/index.html"] + \
    [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, "calendar", "20*", "*", "index.html"))] + \
    [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))]


def text(doc):
    doc = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc)))


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    coarse = []
    for r in rows:
        if r.get("type") != "PDUFA" or (r.get("dp") or "day") == "day":
            continue
        d = str(r.get("d") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        y, m, dd = d.split("-")
        first = re.split(r"[\s(\-:]", str(r.get("name") or "").strip())[0].lower()
        coarse.append((str(r.get("t") or "").upper(), first, f"{MONTHS[int(m)]} {int(dd)}", d))
    fails = []
    for rel in PAGES:
        p = os.path.join(SITE, rel)
        if not os.path.exists(p) or SKIP.search(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*noindex', doc[:4000]):
            continue
        t = text(doc)
        for tk, first, label, d in coarse:
            for m in re.finditer(rf"(?:{re.escape(label)},? \d{{4}} goal date|{re.escape(label)} goal date|goal date of {re.escape(label)}|goal date, {re.escape(label)})", t):
                win = t[max(0, m.start() - 220): m.end() + 220]
                if re.search(rf"\b{re.escape(tk)}\b", win) or (first and len(first) > 4 and first in win.lower()):
                    fails.append(f"/{rel.replace('/index.html', '')}: '{m.group(0)}' stated for {tk} ({d}, precision != day)")
                    break
    if fails:
        print(f"FAIL: {len(fails)} goal DAY(s) rendered for coarse-precision rows:")
        for f in sorted(set(fails))[:15]:
            print("   " + f)
        print("\n   A window is a span, not a point. Render it with site_windows; never say 'goal date' for it.")
        return 1
    print(f"OK -- {len(coarse)} coarse-precision PDUFA rows; no page states a goal day for any of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
