# -*- coding: utf-8 -*-
"""build_calendar_density.py -- the "Where 2026's decisions cluster" chart on /calendar, rebuilt from the dataset.

Red team 2026-11-26. The weekly density chart at the top of /calendar was a hand-built SVG with no builder,
frozen on an old slate. It still put Vertex's povetacicept in the week of Nov 30 after the FDA extended that
goal to no later than Feb 28, 2027, showed six decisions that week where the dataset has two, and differed
from the dataset in most weeks (week of Aug 17: six on the chart, two in the dataset). The calendar table
under it was correct; only the chart was stale, and nothing checked it.

This rewrites the chart's bars, week tooltips and footer from api/v1/dataset.mjs on every rebuild:
  * one bar per Monday-to-Sunday week from Jul 6 to Dec 28, 2026 (26 weeks, the chart's existing frame; the old
    footer said 25, but it drew 26 columns;
    the month rules and legend are left as they are);
  * every PDUFA row whose goal date is known to the DAY and falls in that frame, decided or not, at its
    goal date (the date the FDA set, which is what the chart has always plotted);
  * stacked by the row's market-cap tier, bottom to top Nano, Micro, Small, Mid, Large, then Unlisted;
  * the footer counts those decisions and, separately, the PDUFA goals in the frame that are known only
    to a month or quarter, which are not placed on any week.
The tooltip tickers are exactly the dataset rows of that week. tests/test_calendar_density.py fails the
build if the chart and the dataset ever disagree again.

    python build_calendar_density.py [--check]
--check prints what would change and exits 1 if the chart is stale, without writing.
"""
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

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
PAGE = os.path.join(HERE, "pdufa_site_src", "calendar", "index.html")

FIRST_WEEK = dt.date(2026, 7, 6)     # a Monday; the chart's first column
WEEKS = 26                           # Jul 6 .. Dec 28, 2026 (x runs 8.05 to 1068, the axis end)
FRAME_END = dt.date(2026, 12, 31)
X0, STEP, BAR_W = 8.05, 40.8818, 37.9
BASE = 189.0                         # bars stand on the axis line at y=189.5
UNIT = 15.0                          # one decision = 13.8 px bar + 1.2 px gap
TOP = 54.0                           # the tallest stack may reach y=54 (axis area starts at 48)
TIERS = [("Nano", "#ffd27a"), ("Micro", "#f0c86a"), ("Small", "#46d17f"), ("Mid", "#5b8fd0"),
         ("Large", "#33547e"), ("Unlisted", "#28405f")]
TIER_NAMES = [t for t, _ in TIERS]

SVG_OPEN = re.compile(r'<svg [^>]*aria-label="Weekly FDA decision density[^"]*">')
# everything after the axis baseline, up to the end of the svg, is ours to rewrite
BODY = re.compile(r'(<line x1="8" y1="189\.5" x2="1068" y2="189\.5"[^>]*/>)(.*?)(</svg>)', re.S)


def load_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def tier(row):
    cap = str(row.get("cap") or "")
    return cap if cap in TIER_NAMES[:-1] else "Unlisted"


def weekly(rows):
    """(weeks, approx): weeks is a list of WEEKS lists of day-precision PDUFA rows; approx counts PDUFA goals in
    the frame known only to a month or quarter."""
    weeks = [[] for _ in range(WEEKS)]
    approx = 0
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        try:
            d = dt.date.fromisoformat(str(r.get("d") or "")[:10])
        except ValueError:
            continue
        if not (FIRST_WEEK <= d <= FRAME_END):
            continue
        if r.get("dp") != "day":
            approx += 1
            continue
        i = (d - FIRST_WEEK).days // 7
        if 0 <= i < WEEKS:
            weeks[i].append(r)
    return weeks, approx


def fmt(x):
    return f"{x:.1f}"


def week_label(i):
    m = FIRST_WEEK + dt.timedelta(days=7 * i)
    return f"{m.strftime('%b')} {m.day}"


def render(weeks, approx):
    peak = max([len(w) for w in weeks] + [1])
    unit = min(UNIT, (BASE - TOP) / peak)
    out = []
    for i, w in enumerate(weeks):
        x = X0 + STEP * i
        if not w:
            out.append(f'<rect x="{fmt(x)}" y="186" width="{BAR_W}" height="3" rx="1" fill="#132745"/>')
            continue
        counts = {t: sum(1 for r in w if tier(r) == t) for t in TIER_NAMES}
        n = len(w)
        mix = ", ".join(f"{counts[t]} {t}" for t in TIER_NAMES if counts[t])
        tickers = " ".join(sorted({str(r.get("t") or "").upper() for r in w}))
        title = f"Week of {week_label(i)} · {n} decision{'s' if n != 1 else ''} · {mix}\n{tickers}"
        g = [f"<g><title>{html.escape(title, quote=False)}</title>"]
        cum = 0
        for t, color in TIERS:
            k = counts[t]
            if not k:
                continue
            cum += k
            y = BASE - unit * cum
            g.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{BAR_W}" height="{fmt(unit * k - 1.2)}" rx="1.5" '
                     f'fill="{color}"/>')
        if n >= 3:
            g.append(f'<text x="{fmt(x + BAR_W / 2)}" y="{fmt(BASE - unit * n - 3)}" fill="#eef4fc" font-size="10" '
                     f'font-weight="700" text-anchor="middle">{n}</text>')
        g.append("</g>")
        out.append("".join(g))
    total = sum(len(w) for w in weeks)
    foot = (f"{total} scheduled FDA decision{'s' if total != 1 else ''} across {WEEKS} weeks, stacked by "
            f"market-cap tier")
    if approx:
        foot += f" · plus {approx} more dated only to a month or quarter"
    foot += ". Hover a bar for the week&#8217;s tickers."
    out.append(f'<text x="8" y="245" fill="#7c93b6" font-size="10.5">{foot}</text>')
    return "".join(out)


def rebuild(doc, rows):
    """doc with the chart body rewritten, or None when the chart is not on the page."""
    m = SVG_OPEN.search(doc)
    if not m:
        return None
    end = doc.index("</svg>", m.end()) + len("</svg>")
    svg = doc[m.start():end]
    b = BODY.search(svg)
    if not b:
        return None
    weeks, approx = weekly(rows)
    new_svg = svg[:b.start(2)] + render(weeks, approx) + svg[b.end(2):]
    return doc[:m.start()] + new_svg + doc[end:]


def main():
    check = "--check" in sys.argv[1:]
    if not os.path.exists(PAGE):
        print("calendar density: no /calendar page; nothing to do")
        return 0
    doc = io.open(PAGE, encoding="utf-8", newline="").read()
    rows = load_rows()
    new = rebuild(doc, rows)
    if new is None:
        print("calendar density: chart not found on /calendar (markup changed?)")
        return 1
    weeks, approx = weekly(rows)
    total = sum(len(w) for w in weeks)
    if new == doc:
        print(f"calendar density: current ({total} dated decisions, {approx} month/quarter-only)")
        return 0
    if check:
        print(f"calendar density: STALE; would rewrite to {total} dated decisions, {approx} month/quarter-only")
        return 1
    with io.open(PAGE, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print(f"calendar density: rewritten ({total} dated decisions, {approx} month/quarter-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
