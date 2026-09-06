# -*- coding: utf-8 -*-
"""Every row on /calendar sits under the month heading its date belongs to.

Found 2026-09-06 while adding SRRK: the main page's row insert anchored "before the first
later-dated row" with no regard for the per-month grids, so eleven October-December rows
(RHHBY 10-15 ... PRAX 12-27) were rendered under the "September 2026" heading, two July
rows under August, one under September. A reader scanning September saw December. This
asserts the RENDER: a dated row's month equals its heading; a "Qn YYYY (est.)" row sits
under the quarter's last month; and the decided rows restored from the archive each link
a decision page that exists in the build.

Proven 2026-09-06: 0 -> planted a 2026-12-27 row into the September grid -> 1 -> removed -> 0.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def test_calendar_rows_under_their_month():
    doc = io.open(os.path.join(SITE, "calendar", "index.html"), encoding="utf-8",
                  errors="replace").read()
    parts = re.split(r'(<div class="mhead">[A-Za-z]+ \d{4}</div>)', doc)
    assert len(parts) > 2, "no month headings on /calendar -- markup changed"
    bad, rows = [], 0
    for k in range(1, len(parts), 2):
        head = re.search(r">([A-Za-z]+ \d{4})<", parts[k]).group(1)
        for row in re.findall(r'<a class="row"[^>]*>.*?</a>', parts[k + 1], re.S):
            t = re.search(r'<div class="t">(.*?)</div>', row, re.S)
            if not t:
                continue
            rows += 1
            label = re.sub(r"<[^>]+>", " ", t.group(1))
            dm = re.search(r"(\d{4})-(\d{2})-\d{2}", label)
            qm = re.search(r"Q([1-4]) (\d{4}) \(est\.\)", label)
            want = (f"{MONTHS[int(dm.group(2)) - 1]} {dm.group(1)}" if dm else
                    f"{MONTHS[int(qm.group(1)) * 3 - 1]} {qm.group(2)}" if qm else None)
            if want and want != head:
                bad.append(f"{label.strip()[:40]!r} under '{head}', belongs under '{want}'")
            hm = re.search(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', row)
            if hm and not os.path.exists(os.path.join(SITE, "fda-decision", hm.group(1), "index.html")):
                bad.append(f"{label.strip()[:40]!r} links /fda-decision/{hm.group(1)} which does not exist")
    assert rows > 20, f"only {rows} rows parsed on /calendar -- markup changed"
    assert not bad, (f"{len(bad)} /calendar row(s) under the wrong month or linking nothing:\n  "
                     + "\n  ".join(bad[:20]))


if __name__ == "__main__":
    test_calendar_rows_under_their_month()
    print("OK")
