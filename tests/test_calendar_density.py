# -*- coding: utf-8 -*-
"""test_calendar_density.py -- the /calendar "Where 2026's decisions cluster" chart matches the dataset, week by week.

Red team 2026-11-26: the chart was a frozen hand-built SVG. It still showed Vertex's povetacicept in the week of
Nov 30 after the FDA extended the goal to no later than Feb 28, 2027, six decisions that week where the dataset
has two, and wrong counts in most other weeks. build_calendar_density.py now rebuilds it every run; this guard
proves it ran:
  * every week's tooltip names exactly the tickers of that week's day-precision PDUFA rows, with the right count;
  * the bars in each week add up to that count, in the right tier colors;
  * the footer's totals are the dataset's.
Run against the page as it stood before the builder (PLANT=stale replays the old Nov 30 week), it FAILS.

    python tests/test_calendar_density.py
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_calendar_density as B  # noqa: E402

GROUP = re.compile(r"<g><title>Week of ([A-Z][a-z]{2} \d{1,2}) · (\d+) decisions? · ([^\n<]*)\n([A-Z0-9. ]*)</title>(.*?)</g>",
                   re.S)
RECT = re.compile(r'<rect x="[\d.]+" y="[\d.]+" width="[\d.]+" height="([\d.]+)" rx="1\.5" fill="(#[0-9a-f]{6})"/>')
FOOT = re.compile(r"(\d+) scheduled FDA decisions? across (\d+) weeks(?:[^<]*?plus (\d+) more dated only)?")


def main():
    doc = io.open(B.PAGE, encoding="utf-8", newline="").read()
    if os.environ.get("PLANT") == "stale":
        doc = doc.replace("Week of Nov 30 · 2 decisions", "Week of Nov 30 · 6 decisions", 1)
    m = B.SVG_OPEN.search(doc)
    if not m:
        print("FAIL\n  the density chart is missing from /calendar")
        return 1
    svg = doc[m.start():doc.index("</svg>", m.end())]
    weeks, approx = B.weekly(B.load_rows())
    want = {}
    for i, w in enumerate(weeks):
        if w:
            want[B.week_label(i)] = (len(w), {str(r["t"]).upper() for r in w},
                                     {t: sum(1 for r in w if B.tier(r) == t) for t in B.TIER_NAMES})
    color = dict(B.TIERS)
    # the frame must cover every day of the chart's span: the first build stopped a week short and dropped
    # Cogent's Dec 30 goal off the right edge
    import datetime as dt
    last = B.FIRST_WEEK + dt.timedelta(days=7 * (B.WEEKS - 1))
    if not (last <= B.FRAME_END < last + dt.timedelta(days=7)) or abs(B.X0 + B.STEP * (B.WEEKS - 1) + B.BAR_W - 1068) > 1:
        bad_frame = [f"frame ends on the week of {last}, not the week holding {B.FRAME_END}, or overruns the axis"]
    else:
        bad_frame = []
    bad, got = list(bad_frame), {}
    for g in GROUP.finditer(svg):
        label, n, _mix, tick, body = g.group(1), int(g.group(2)), g.group(3), g.group(4), g.group(5)
        got[label] = (n, set(tick.split()))
        if label not in want:
            bad.append(f"week of {label}: chart shows {n} ({tick}); dataset has none")
            continue
        wn, wt, wtiers = want[label]
        if n != wn or set(tick.split()) != wt:
            bad.append(f"week of {label}: chart {n} {sorted(set(tick.split()))}, dataset {wn} {sorted(wt)}")
        stacked = {}
        for h, fill in RECT.findall(body):
            stacked[fill] = stacked.get(fill, 0) + round((float(h) + 1.2) / B.UNIT)
        expect = {color[t]: k for t, k in wtiers.items() if k}
        if stacked != expect:
            bad.append(f"week of {label}: bars {stacked} != tiers {expect}")
    for label, (wn, wt, _) in want.items():
        if label not in got:
            bad.append(f"week of {label}: dataset has {wn} {sorted(wt)}; chart shows no bar")
    f = FOOT.search(svg)
    total = sum(len(w) for w in weeks)
    if not f:
        bad.append("footer count missing")
    elif int(f.group(1)) != total or int(f.group(3) or 0) != approx:
        bad.append(f"footer says {f.group(1)} dated + {f.group(3) or 0} approx; dataset {total} + {approx}")
    print(f"density chart: {len(got)} weeks with bars, {total} dated decisions, {approx} month/quarter-only")
    if bad:
        print("FAIL (run build_calendar_density.py)")
        for b in bad[:40]:
            print("  " + b)
        return 1
    print("  PASS: every week's bar, tooltip and tier stack is the dataset's")
    return 0


if __name__ == "__main__":
    sys.exit(main())
