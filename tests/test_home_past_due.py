# -*- coding: utf-8 -*-
"""test_home_past_due.py -- the home page's "Past their goal date" box is complete, exact and current.

David, 2026-11-25: "add a past due box on the home page for pdufas that missed their date so it stays current and
accurate ... we have to be fast and completely infallible in our information". The box (build_home_past_due.py)
lists every PDUFA goal that has passed with no FDA decision on record. This guard recomputes that list on its own
from the dataset (a miniature of the rule, so a bug in the builder cannot vouch for itself) and fails if:

  1. the box is missing, or sits outside the side column above "Recently decided";
  2. an open PDUFA row (Upcoming, Awaiting, Under review) whose stated goal period ended before today (Eastern) has
     no row in the box, or the box lists a goal the dataset holds as decided, withdrawn or not yet past;
  3. a row's goal date differs from the dataset's, or a row whose sponsor announced the FDA would miss the date
     (_goal_date_passed.json) does not say so;
  4. the box's "as of" day is not today, Eastern (a box frozen on an old day is the stale page this exists to stop);
  5. a past-due goal is also listed under "Next FDA decisions" (one goal, one place).

PLANT=drop removes a row from the box in memory and PLANT=stale moves its day back; each must FAIL.

    python tests/test_home_past_due.py      (fix: python build_home_past_due.py)
"""
import calendar
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]


def end_of(d, dp):
    dp = (dp or "day").lower()
    if dp == "month":
        return d.replace(day=calendar.monthrange(d.year, d.month)[1])
    if dp == "quarter":
        m = ((d.month - 1) // 3 + 1) * 3
        return dt.date(d.year, m, calendar.monthrange(d.year, m)[1])
    if dp == "year":
        return dt.date(d.year, 12, 31)
    return d


def words(d, dp):
    dp = (dp or "day").lower()
    return {"month": f"{MONTH[d.month]} {d.year}", "quarter": f"Q{(d.month - 1) // 3 + 1} {d.year}",
            "year": str(d.year)}.get(dp, f"{MON[d.month]} {d.day}, {d.year}")


def main():
    today = eastern_today()
    plant = os.environ.get("PLANT", "")
    doc = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    try:
        led = {e["slug"]: e for e in json.load(io.open(os.path.join(HERE, "_goal_date_passed.json"),
                                                         encoding="utf-8")).get("passed", [])}
    except Exception:  # noqa: BLE001
        led = {}
    bad = []

    want = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() not in ("upcoming", "awaiting", "under review"):
            continue
        if str((r.get("_d") or {}).get("goal_date") or "").lower() == "not announced":
            continue
        try:
            d = dt.date.fromisoformat(str(r.get("d") or "")[:10])
        except ValueError:
            continue
        if end_of(d, r.get("dp")) < today:
            want[str(r.get("url") or "")] = (str(r.get("t") or "").upper(), words(d, r.get("dp")))

    m = re.search(r"<!--PASTDUE:BEGIN-->(.*?)<!--PASTDUE:END-->", doc, re.S)
    if not m:
        bad.append("home: the past-due box is missing")
        box = ""
    else:
        box = m.group(1)
        a, rd = doc.rfind("<aside>", 0, m.start()), doc.find("Recently decided")
        if a < 0 or doc.find("</aside>", a) < m.start() or not (m.end() < rd):
            bad.append("home: the past-due box is not at the top of the side column, above Recently decided")
    if plant == "drop":
        if want:
            box = re.sub(r'<a class="pdr".*?</a>', "", box, count=1, flags=re.S)
        else:
            want["/pdufa/PLANTED"] = ("PLANT", "Jan 1, 2026")
    if plant == "stale":
        box = re.sub(r"as of [A-Z][a-z]+ \d{1,2}, \d{4} \(Eastern\)", "as of January 1, 2026 (Eastern)", box)

    shown = {}
    for href, inner in re.findall(r'<a class="pdr" href="([^"]+)">(.*?)</a>', box, re.S):
        g = re.search(r'<span class="pdg">PDUFA goal (.*?) passed</span>', inner)
        shown[html.unescape(href)] = (html.unescape(g.group(1)) if g else "", html.unescape(re.sub(r"<[^>]+>", " ", inner)))
    for u, (t, w) in sorted(want.items()):
        if u not in shown:
            bad.append(f"home: {t} (goal {w}, {u}) has passed with no decision on record and is not in the past-due box")
        elif shown[u][0] != w:
            bad.append(f"home: past-due row {u} shows goal {shown[u][0]!r}; the dataset holds {w!r}")
    for u in shown:
        if u not in want:
            bad.append(f"home: past-due row {u} is not an open PDUFA goal past its date in the dataset")
    for u, (_w, text) in shown.items():
        slug = u.rsplit("/", 1)[-1]
        e = led.get(slug, {})
        if e.get("announced_miss_date") and "said the FDA would not act by the goal date" not in text:
            bad.append(f"home: past-due row {u} omits the sponsor's announcement that the FDA would miss the date")
    day = f"as of {MONTH[today.month]} {today.day}, {today.year} (Eastern)"
    if box and day not in box:
        bad.append(f"home: the past-due box is not stamped {day!r}")

    i = doc.find('<div class="list">')
    lst = doc[i:doc.find("</div>", i)] if i >= 0 else ""
    for u, (t, w) in want.items():
        if u.startswith("/pdufa/") and f'href="{u}"' in lst:
            bad.append(f"home: {t} (goal {w}) is past due and still listed under Next FDA decisions")

    print(f"{len(want)} past-due goal(s) in the dataset, {len(shown)} row(s) in the box, as of {today} (Eastern)")
    if bad:
        print("FAIL")
        for b in bad[:20]:
            print("  " + b)
        print("  fix: python build_home_board.py && python build_home_past_due.py")
        return 1
    print("  PASS: every PDUFA goal past its date with no decision is in the home past-due box, and nothing else is")
    return 0


if __name__ == "__main__":
    sys.exit(main())
