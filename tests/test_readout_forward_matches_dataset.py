# -*- coding: utf-8 -*-
"""The estimated-readouts table on /readouts must be exactly the dataset's forward Estimated rows.

Red team 2026-11-26: the table had no builder and drifted for months. Of 159 rows, 31 had no dataset row
behind them and 21 showed a month the dataset no longer held; its footer said "728 upcoming readouts". It is
now written by build_readout_forward.py, and this guard checks the RESULT so the page and the data cannot
part again:

  - the table sits between its markers, and every row in it is "TK · Mon YYYY (est.)" linking a
    ClinicalTrials.gov record;
  - the multiset of (ticker, month, NCT) on the page equals the dataset's forward Estimated rows that link
    a trial record (build_readout_forward.forward_rows), no more and no fewer;
  - each row sits under the month heading it names, no month heading is in the past, and the footer's
    count equals the number of rows;
  - no company "H1/H2/Q" exhibit row survives inside the table (company dates belong in the guided table,
    which build_guided_readouts.py rebuilds and red-teams).
"""
import collections
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_readout_forward as brf  # noqa: E402

MON3 = {m: i for i, m in enumerate(brf.MON3, 1)}
MONF = {m: i for i, m in enumerate(brf.MONTHS, 1)}


def _table():
    page = io.open(brf.PAGE, encoding="utf-8", errors="replace").read()
    assert page.count(brf.BEGIN) == 1 and page.count(brf.END) == 1, "estimated table markers missing on /readouts"
    return page[page.index(brf.BEGIN):page.index(brf.END)]


def test_forward_table_equals_dataset():
    seg = _table()
    td = brf.today()
    cur = (td.year, td.month)
    page_set = collections.Counter()
    for head, body in re.findall(r'<div class="mhead">([^<]+)</div><div class="grid">(.*?)</div>(?=<div class="mhead">|<div class="note")',
                                 seg, flags=re.S):
        hm = re.match(r"^([A-Za-z]+) (\d{4})$", head.strip())
        assert hm and hm.group(1) in MONF, f"heading {head!r} is not a month"
        hy, hmo = int(hm.group(2)), MONF[hm.group(1)]
        assert (hy, hmo) >= cur, f"past month heading {head!r} in the estimated table"
        for href, t in re.findall(r'<a class="row" href="([^"]+)"[^>]*><div class="t">([^<]*)</div>', body):
            m = re.match(r"^([A-Z0-9.\-]+) &middot; ([A-Z][a-z]{2}) (\d{4}) \(est\.\)$", t)
            assert m, f"row title {t!r} is not 'TK · Mon YYYY (est.)'"
            assert (int(m.group(3)), MON3[m.group(2)]) == (hy, hmo), f"{t!r} sits under {head!r}"
            n = re.match(r"^https://clinicaltrials\.gov/study/(NCT\d{8})$", href)
            assert n, f"{t!r} links {href!r}, not a ClinicalTrials.gov record"
            page_set[(m.group(1), f"{hy:04d}-{hmo:02d}", n.group(1))] += 1

    fwd, _ = brf.forward_rows(brf.load_rows(), td)
    data_set = collections.Counter((r["t"], str(r["d"])[:7], brf.nct_of(r)) for r in fwd)
    extra = page_set - data_set
    missing = data_set - page_set
    assert not extra, f"rows on /readouts with no forward dataset row: {sorted(extra)[:10]}"
    assert not missing, f"forward dataset rows missing from /readouts: {sorted(missing)[:10]}"

    note = re.search(r'<div class="note"[^>]*>(\d+) estimated readout', seg)
    assert note and int(note.group(1)) == sum(page_set.values()), "footer count does not match the rows"
    assert not re.search(r"&middot; [HQ][1-4] 20\d\d<", seg), "a company H/Q exhibit row is inside the estimated table"


if __name__ == "__main__":
    test_forward_table_equals_dataset()
    print("OK")
