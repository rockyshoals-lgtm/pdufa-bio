# -*- coding: utf-8 -*-
"""sync_screener_data.py -- /screener renders from the dataset, not from a July snapshot.

Red team 2026-11-01: /screener's table is drawn client-side from an inline `const DATA=[...]`, and that array had
not changed since the site's first commit (2026-07-25). 395 rows, 31 of them "Upcoming" with dates already past
(AGIO on Nov 1 after the goal moved to Feb 2027, IGALMI under BioXcel after the sale to Teva, decided approvals
still listed as pending). No step in the workflow ever rewrote it.

This rewrites DATA from api/v1/dataset.mjs every run: same keys the page's JS reads (t, d, name, type, ta, cap, st,
url), names cut at 50 characters as before, rows from 150 days back onward. Idempotent.

Design red team 2026-11-18 (change 1, date precision). The page printed every row's `d` as a day. For 202 estimated
and 236 guided readouts that day is a storage key, not a date anyone stated: "Q4 2026" was shown as 2026-12-31 and a
month as its 15th. Decided PDUFAs stayed under their goal date with a check mark, so a CRL (SMMT) showed a tick and
an approval from September showed as a December catalyst. Now, through site_windows (the one owner of window labels):
  * a row whose stored precision is month, quarter or year carries `w`, its label ("Nov 2026", "Q4 2026", "2026",
    plus " (est.)" when st is Estimated), and `e`, the window's last day, so the From filter keeps an open window;
  * a day-precision row is untouched: an exact day a source gives is printed as that day;
  * a decided PDUFA with a decision date (dcd) is placed on that FDA action date, with its outcome (oc), so the page
    marks approvals and complete response letters differently and never lists a decided application as upcoming.

    python sync_screener_data.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "screener", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
sys.path.insert(0, HERE)
try:
    from site_dates import eastern_today
except Exception:  # noqa: BLE001
    eastern_today = dt.date.today
from site_windows import is_day, window_label, window_span  # noqa: E402


def date_text(r):
    """What a row prints as its date (also build_screener_rows.py's table): a stated day as that day, a month /
    quarter / year as its window ("Nov 2026", "Q4 2026", "2026"), "Not announced" when the sponsor states no goal
    date, and " (est.)" on pdufa.bio's own estimates."""
    lab = window_label(r)                     # a day row's label is its day; not-announced wins over precision
    return lab + (" (est.)" if r.get("st") == "Estimated" else "")


def screener_row(r):
    """The DATA entry for one dataset row (also used by tests/test_date_precision.py).

    Keys the page reads: t d name type ta cap st url, plus
      w   the printed date when it differs from d (window label, "Not announced", " (est.)");
      s/e the window's first / last day when they differ from d, so From and To filter on the whole window;
      oc  the recorded outcome of a decided PDUFA;
      a   1 when the decision date is the sponsor's announcement day, not a sourced FDA action date."""
    d = str(r.get("d") or "")
    out = {"t": r.get("t") or "", "d": d, "name": str(r.get("name") or "")[:50], "type": r.get("type"),
           "ta": r.get("ta") or "", "cap": r.get("cap") or "", "st": r.get("st") or "",
           "url": r.get("url") or f"/ticker/{r.get('t')}"}
    decided = r.get("type") == "PDUFA" and r.get("st") == "Decided"
    if decided and r.get("oc"):
        out["oc"] = str(r.get("oc"))
    dcd = str(r.get("dcd") or "")
    if decided and len(dcd) == 10:
        out["d"] = dcd                       # the FDA action date, a day
        if ((r.get("_d") or {}) if isinstance(r.get("_d"), dict) else {}).get("decision_date_unsourced"):
            out["a"] = 1                     # LNTH, NVCR: the day the sponsor announced it
        return out
    w = date_text(r)
    if w != d:
        out["w"] = w
    s, e = window_span(r)
    if s and s != d:
        out["s"] = s
    if e and e != d:
        out["e"] = e
    return out


def sort_key(row):
    """Window end (a day row's own day), exact days before windows that end the same day, then ticker. Sorting by
    the storage day put "Nov 2026 (est.)" rows (stored on the 15th) ahead of Nov 16-30 exact days."""
    return (row.get("e") or row["d"], 1 if row.get("s") else 0, row["t"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    floor = (eastern_today() - dt.timedelta(days=150)).isoformat()
    out = []
    for r in rows:
        if not r.get("d") or r.get("type") not in ("PDUFA", "Readout", "Conference", "AdComm"):
            continue
        row = screener_row(r)
        if max(row["d"], row.get("e", "")) < floor:
            continue
        out.append(row)
    out.sort(key=sort_key)
    doc = io.open(PAGE, encoding="utf-8").read()
    m = re.search(r"const DATA=(\[.*?\]);\s*\nconst q=", doc, re.S)
    if not m:
        print("::warning::/screener: const DATA not found; nothing written")
        return 0
    new = doc[:m.start(1)] + json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + doc[m.end(1):]
    if new != doc and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(new)
    print(f"/screener DATA: {len(out)} row(s) from the dataset (from {floor})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
