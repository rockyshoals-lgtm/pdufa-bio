# -*- coding: utf-8 -*-
"""test_reconcile_main_window.py -- a goal date that moves past the main calendar's last month leaves that page.

Red team 2026-11-26. Vertex's povetacicept moved from November 30, 2026 to February 28, 2027. On /calendar (headings
June to December 2026) reconcile_calendar_table.py rewrote the row's date in place; the page's window then reached
February 2027, the insert pass added every January and February 2027 event, and rehome_rows left all of them under
the 2026 headings (no 2027 heading exists): "33 FDA goal dates in November 2026 ... Enspryng (RHHBY, Jan 10)".
The rebuild runs the same script, so the live flagship page would have shown it.

Replays that on a synthetic two-month main page: the moved row must leave the page, no event dated in a month the
page has no heading for may be inserted, and the rows that stay must keep their months. The month pages keep their
own behaviour (a cross-month move deletes the row and ensure_calendar_rows re-adds it on the right page).

    python tests/test_reconcile_main_window.py
"""
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import reconcile_calendar_table as R  # noqa: E402


def row(tk, d, name):
    return f'<a class="row" href="/pdufa/{tk}"><div class="t">{tk} &middot; {d}</div><div class="d">{name}</div></a>'


def page():
    nov = row("AAAA", "2098-11-20", "Alphamab") + row("VRTX", "2098-11-30", "Povetacicept (ALPN-303)")
    dec = row("CCCC", "2098-12-17", "Gammalimab")
    return ('<html><body><div class="mhead">November 2098</div><div class="grid">' + nov + '</div>'
            '<div class="mhead">December 2098</div><div class="grid">' + dec + '</div></body></html>')


def ev(t, d, name):
    return {"t": t, "d": d, "name": name, "toks": R.toks(name)}


def main():
    events = [ev("AAAA", "2098-11-20", "Alphamab"), ev("VRTX", "2099-02-28", "Povetacicept (ALPN-303)"),
              ev("CCCC", "2098-12-17", "Gammalimab"), ev("DDDD", "2099-01-10", "Deltamab"),
              ev("EEEE", "2099-02-04", "Epsilomab")]
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "calendar"))
        p = os.path.join(tmp, "calendar", "index.html")
        open(p, "w", encoding="utf-8").write(page())
        moved, flagged, renamed = R.reconcile(p, events, False)
        doc = open(p, encoding="utf-8").read()
    grids = dict(re.findall(r'<div class="mhead">([^<]*)</div><div class="grid">(.*?)</div>(?=<div class="mhead">|</body>)',
                            doc, re.S))
    for head, body in grids.items():
        for tk, d in re.findall(r'<div class="t">([A-Z]+) &middot; (\d{4}-\d{2}-\d{2})', body):
            if not head.endswith(d[:4]) or R.MONTH_NAMES[int(d[5:7]) - 1] != head.split()[0]:
                bad.append(f"{tk} {d} sits under '{head}'")
    if "VRTX" in doc:
        bad.append("the row moved to February 2099 is still on a page whose last heading is December 2098")
    for tk in ("DDDD", "EEEE"):
        if tk in doc:
            bad.append(f"{tk} (dated past the page's last heading) was inserted")
    for tk in ("AAAA", "CCCC"):
        if tk not in doc:
            bad.append(f"{tk} (in its own month) was removed")
    print(f"main page replay: {len(moved)} change(s): {moved}")
    if bad:
        print("FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print("  PASS: a row moved past the page's last month leaves the page; nothing past it is inserted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
