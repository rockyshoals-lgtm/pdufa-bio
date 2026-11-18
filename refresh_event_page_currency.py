# -*- coding: utf-8 -*-
"""refresh_event_page_currency.py -- a /pdufa/ event page carries nothing that went stale after it was written.

Four parts of these pages were written once by one-off generators (_build_pdufa_charts*, build_pdufa_story_blocks,
xlink_schema_injector) that no rebuild runs, so they froze on the day they were made. Each is redrawn or removed
here, every rebuild:

  1. The price chart (below).
  2. The "All <Month> 2026 PDUFA dates" chip, in both forms the builders write, follows the page's current target
     (CAPR's still said August after its date moved to November), whether the page writes it 2026-11-22,
     Nov 22, 2026 or Nov 2026; it goes when that month has no calendar page. Pages that state no target
     (decided, or the date withdrawn) keep theirs.
  3. "Same area" / "Same month" related rows: each row's date is re-read from the page it links; a row whose
     event is no longer ahead (CAPR's three were NRXP Jul 29, LNTH Aug 13, MRNA Aug 5) or whose page no longer
     states a day is dropped, and so is a "Same month" row outside this page's own target month. A /ticker/ row
     keeps a date only when that ticker has exactly one live day-precision PDUFA.
  4. The "Balance sheet: about N months of cash, runway ..." sentence and its risk badge ("HIGH: runway ends
     before this catalyst") are removed. None of the 14 cites a filing, most are this site's own estimate, and
     the badge is a judgment. The facts-only rule allows neither.

THE PRICE CHART

Design red team 2026-11-18: all 60 /pdufa/ pages that carry a "run-up into the PDUFA (last ~120 days)" chart
were drawn once, on 2026-06-19, and never again. Four days before Capricor's Nov 22 decision, /pdufa/CAPR showed a
$25-$35 price path "to 2026-06-19" under the heading "last ~120 days", while the stock closed at $8.41. The chart
had no axes either, so a reader could not tell what range or dates it covered.

This step redraws each such chart from the same daily closes the ticker pages use (build_stock_runup.bars: the
recorded series, extended by price_source), every rebuild:

  * the last 120 sessions, ending at the latest close, with the first and last dates on the x axis and the
    high, low and latest close on the y axis;
  * the page's own PDUFA target date marked when it falls inside the window, and named in the note when it is
    still ahead of the last close;
  * a caption that states the range and the source. Historical closes only; nothing is projected.

Only a page whose decision is still ahead carries the chart; on a decided or undated page a window ending today
is not about the event (its /fda-decision page has the decision-day chart). A close dated today (Eastern) is left
out, since it may be an intraday print. A page whose ticker has fewer than 20 closes, or whose newest close is more
than 7 days old (a failed feed serves the recorded series), loses the chart rather than keep a stale one, and a run
that withholds more than it draws warns. Marker-based and
idempotent: the block sits between <!--EVRUNUP:B:TICKER--> and <!--EVRUNUP:E--> and is redrawn in place. Must run before
inject_mobile_polish.py, which draws the phone-sized copy from this desktop drawing.

    python refresh_event_page_currency.py [--dry-run] [--page CAPR]
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "stock_runup_cache.json")
E = "<!--EVRUNUP:E-->"
SESSIONS = 120
MIN_CLOSES = 20
MAX_AGE_DAYS = 7          # newest close older than this: no chart (covers a weekend plus a holiday)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# The original block: heading, the desktop svg (optionally inside the phone wrapper inject_mobile_polish adds),
# and the "Price path to DATE" note. Nothing else may sit between them, so a match never swallows other content.
OLD = re.compile(
    r'<h2>(?P<t>[A-Z0-9.\-]+) run-up into the PDUFA \(last ~120 days\)</h2>'
    r'(?:<!--PH:B--><div class="pd-ph">)?'
    r'<svg viewBox="0 0 \d+ \d+"[^>]*>(?:(?!</svg>).)*</svg>'
    r'(?:<svg class="pd-phs"(?:(?!</svg>).)*</svg></div><!--PH:E-->)?'
    r'<div class="note">Price path to \d{4}-\d{2}-\d{2}\.[^<]*</div>', re.S)
MARKED = re.compile(r"<!--EVRUNUP:B(?::(?P<t>[A-Z0-9.\-]+))?-->.*?" + re.escape(E), re.S)
# The target as the page states it. Two builders write it: ISO ("2026-11-22") or "Nov 22, 2026"; a window page says
# "Dec 2026" (a month, never turned into a day here).
TARGET = re.compile(r'FDA decision \(PDUFA\) target <b>(?:(?P<iso>\d{4}-\d{2}-\d{2})|'
                    r'(?P<mon>[A-Z][a-z]{2}) (?:(?P<day>\d{1,2}), )?(?P<y>\d{4}))</b>')


def page_target_of(doc):
    """(day, month) a page states as its target: ('2026-11-22', '2026-11'), (None, '2026-12') for a month window,
    (None, None) when the page states none (decided, undated or "Date not sourced")."""
    m = TARGET.search(doc)
    if not m:
        return None, None
    if m.group("iso"):
        return m.group("iso"), m.group("iso")[:7]
    if m.group("mon") not in MON:
        return None, None
    ym = f"{m.group('y')}-{MON.index(m.group('mon')) + 1:02d}"
    return (f"{ym}-{int(m.group('day')):02d}" if m.group("day") else None), ym


def short(d):
    return f"{MON[int(d[5:7]) - 1]} {int(d[8:10])}, {d[:4]}"


def money(v):
    return f"${v:,.2f}"


def draw(ticker, closes, target, today):
    """The block for one page, or the empty markers when there is too little current data to draw honestly."""
    empty = f"<!--EVRUNUP:B:{ticker}-->{E}"    # kept so a later rebuild redraws once closes are back
    # Only completed sessions: a row dated today (Eastern) may be an intraday print, not a close.
    s = [(d, float(c)) for d, c, *_ in closes if c not in (None, "") and str(d) < today]
    s = s[-SESSIONS:]
    if len(s) < MIN_CLOSES:
        return empty
    # A series whose newest close is a week old is what this step exists to stop showing: when the feed fails,
    # bars() serves the recorded series, so a stale one is dropped here rather than captioned "the latest close".
    if s[-1][0] < (dt.date.fromisoformat(today) - dt.timedelta(days=MAX_AGE_DAYS)).isoformat():
        return empty
    dates = [d for d, _ in s]
    px = [c for _, c in s]
    first, last = dates[0], dates[-1]
    hi, lo = max(px), min(px)
    W, H = 640, 214
    x0, x1, y0, y1 = 76, 560, 18, 176          # plot box; left margin fits "$1,411.95", right the latest close
    span = (hi - lo) or (hi * 0.02 or 1)
    top, bot = hi + span * 0.06, lo - span * 0.06
    X = lambda i: x0 + i * (x1 - x0) / max(1, len(px) - 1)
    Y = lambda v: y1 - (v - bot) / (top - bot) * (y1 - y0)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(px))
    ih, il = px.index(hi), px.index(lo)
    g = []
    g.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="none" stroke="#1a3358"/>')
    for v, col in ((hi, "#9db3d4"), (lo, "#9db3d4")):
        g.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x1}" y2="{Y(v):.1f}" stroke="#1a3358" '
                 f'stroke-dasharray="2,3"/>')
        g.append(f'<text x="{x0 - 6}" y="{Y(v) + 4:.1f}" fill="{col}" font-size="11" '
                 f'text-anchor="end">{money(v)}</text>')
    mark = ""
    if target and first <= target <= last:
        i = max(k for k, d in enumerate(dates) if d <= target)
        lx = min(max(X(i), x0 + 86), x1 - 86)  # keep the ~170px label inside the plot box
        mark = (f'<line x1="{X(i):.1f}" y1="{y0}" x2="{X(i):.1f}" y2="{y1}" stroke="#7fa8d8" '
                f'stroke-width="1.2"/>'
                f'<text x="{lx:.1f}" y="{y0 - 5}" fill="#7fa8d8" font-size="11" '
                f'text-anchor="middle">PDUFA target {short(target)}</text>')
    g.append(mark)
    g.append(f'<polyline points="{pts}" fill="none" stroke="#e3ba5e" stroke-width="1.6"/>')
    g.append(f'<circle cx="{X(ih):.1f}" cy="{Y(hi):.1f}" r="2.6" fill="#9db3d4"/>')
    g.append(f'<circle cx="{X(il):.1f}" cy="{Y(lo):.1f}" r="2.6" fill="#9db3d4"/>')
    g.append(f'<circle cx="{X(len(px) - 1):.1f}" cy="{Y(px[-1]):.1f}" r="3" fill="#e3ba5e"/>')
    g.append(f'<text x="{X(len(px) - 1) + 8:.1f}" y="{Y(px[-1]) + 4:.1f}" fill="#e3ba5e" font-size="11" '
             f'text-anchor="start">{money(px[-1])}</text>')
    g.append(f'<text x="{x0}" y="{y1 + 18}" fill="#9db3d4" font-size="11" text-anchor="start">{short(first)}</text>')
    g.append(f'<text x="{x1}" y="{y1 + 18}" fill="#e3ba5e" font-size="11" text-anchor="end">'
             f'{short(last)}</text>')
    label = (f"{ticker} daily closing price, {short(first)} to {short(last)}: from {money(px[0])} to "
             f"{money(px[-1])}; high {money(hi)}, low {money(lo)}")
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(label, quote=True)}" '
           f'style="width:100%;display:block;aspect-ratio:{W}/{H};background:#071528;border:1px solid #1a3358;'
           f'border-radius:10px" font-family="IBM Plex Mono,monospace">' + "".join(g) + '</svg>')
    ahead = ""
    if target and target > last:
        ahead = f" The PDUFA target date, {short(target)}, is after the last close shown."
    note = (f'<div class="note">Daily closes for {html.escape(ticker)}, the last {len(px)} recorded daily closes: '
            f'{short(first)} to {short(last)}, the latest close.{ahead} Gold line = closing price; the dotted '
            f'lines mark the high and low of the window. Closes from pdufa.bio\'s recorded price series. '
            f'Historical prices, not a forecast.</div>')
    return (f'<!--EVRUNUP:B:{ticker}--><h2>{html.escape(ticker)} share price, last {len(px)} daily closes</h2>'
            f'{svg}{note}{E}')


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
# Both chip forms the builders write: a plain link, and build_pdufa_event_pages.py's <a class="cta"><b>...</b></a>.
CHIP = re.compile(r'<a (?P<pre>[^>]*?)href="/calendar/(?P<y>\d{4})/(?P<m>[a-z]+)"(?P<st>[^>]*)>(?P<b><b>)?'
                  r'All [A-Za-z]+ \d{4} PDUFA dates (?P<arr>→|&rarr;)(?(b)</b>)</a>')
ROW = re.compile(r'<a class="row" href="(?P<href>/[^"]+)"><span class="t">(?P<label>[^<]*?) \. '
                 r'(?P<d>\d{4}-\d{2}-\d{2})</span><span class="d">(?P<why>Same (?P<kind>area|month)[^<]*)</span></a>')
RUNWAY = re.compile(r' ?Balance sheet: about <b>\d+ months of cash</b>[^<]*?\.(?: <span class="badge amb">[^<]*</span>)?')


def today_et():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return dt.date.today().isoformat()


def page_target(href, memo):
    """The target day a linked /pdufa/ page states now, or None."""
    if href in memo:
        return memo[href]
    f = os.path.join(SITE, href.strip("/"), "index.html")
    d = None
    if href.startswith("/pdufa/") and os.path.exists(f):
        d = page_target_of(open(f, encoding="utf-8", errors="replace").read())[0]
    elif href.startswith("/ticker/"):
        # A ticker hub names no drug, so its date is only unambiguous when the ticker has exactly one live
        # day-precision PDUFA; with two, the row's drug label could be paired with the other drug's date.
        days = live_by_ticker().get(href.split("/")[2].upper(), [])
        d = days[0] if len(days) == 1 else None
    memo[href] = d
    return d


_LIVE = None


def live_by_ticker():
    global _LIVE
    if _LIVE is None:
        _LIVE = {}
        f = os.path.join(SITE, "api", "v1", "dataset.mjs")
        m = re.search(r"export default (\[.*\])", open(f, encoding="utf-8", errors="replace").read(), re.S) \
            if os.path.exists(f) else None
        for e in (json.loads(m.group(1)) if m else []):
            if e.get("type") == "PDUFA" and e.get("st") == "Upcoming" and e.get("dp") == "day" and e.get("d"):
                _LIVE.setdefault(str(e.get("t", "")).upper(), []).append(e["d"])
    return _LIVE


def fix_chip(doc, ym):
    if not ym:              # a decided or undated page: its chip names the month it was written for; leave it
        return doc

    def sub(m):
        y, mon = ym[:4], MONTHS[int(ym[5:7]) - 1]
        if not os.path.exists(os.path.join(SITE, "calendar", y, mon, "index.html")):
            return ""
        text = f'All {mon.capitalize()} {y} PDUFA dates {m.group("arr")}'
        if m.group("b"):
            text = f"<b>{text}</b>"
        return f'<a {m.group("pre")}href="/calendar/{y}/{mon}"{m.group("st")}>{text}</a>'
    return CHIP.sub(sub, doc)


def fix_rows(doc, today, memo, ym):
    """Re-date each related row from the page it links; drop it when that date has passed or is unknown, and drop
    a "Same month" row whose month is not this page's own target month (or when this page states none)."""
    def sub(m):
        d = page_target(m.group("href"), memo)
        if not d or d < today:
            return ""
        if m.group("kind") == "month" and (not ym or d[:7] != ym):
            return ""
        return m.group(0).replace(f' . {m.group("d")}</span>', f' . {d}</span>', 1)
    return ROW.sub(sub, doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--page", help="only this /pdufa/ slug, e.g. CAPR")
    ap.add_argument("--no-prices", action="store_true", help="skip the chart (offline runs and tests)")
    a = ap.parse_args()

    from build_stock_runup import bars, load_key   # the series of record the ticker pages use
    key = load_key() or "price_source"
    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    today = today_et()
    pages = sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")))
    if a.page:
        pages = [p for p in pages if os.path.basename(os.path.dirname(p)) == a.page]
    n = {"drawn": 0, "nochart": 0, "decided": 0, "chips": 0, "rows": 0, "runway": 0, "pages": 0}
    series, memo = {}, {}
    for p in pages:
        doc = open(p, encoding="utf-8", errors="replace").read()
        new = doc
        target, ym = page_target_of(new)
        # A chart belongs only on a page whose decision is still ahead: on a decided or undated page a window
        # ending today is not about the event (the /fda-decision page carries the decision-day chart).
        pending = bool(ym) and ((target or "") >= today if target else ym >= today[:7])

        if not a.no_prices:
            m, mm = OLD.search(new), MARKED.search(new)
            if m or mm:
                ticker = (m.group("t") if m else mm.group("t")) or \
                    os.path.basename(os.path.dirname(p)).split("-")[0].upper()
                if pending and ticker not in series:
                    try:
                        series[ticker] = bars(ticker, key, cache) or []
                    except Exception as ex:      # one ticker's feed failing must not stop the others
                        print(f"  {ticker}: no closes ({ex.__class__.__name__}); chart withheld")
                        series[ticker] = []
                block = draw(ticker, series[ticker], target, today) if pending else \
                    f"<!--EVRUNUP:B:{ticker}-->{E}"
                hit = m or mm
                new = new[:hit.start()] + block + new[hit.end():]
                n["drawn" if "<svg" in block else ("nochart" if pending else "decided")] += 1

        before = new
        new = fix_chip(new, ym)
        n["chips"] += before != new
        before = new
        new = fix_rows(new, today, memo, ym)
        n["rows"] += before != new
        before = new
        new = RUNWAY.sub("", new)
        n["runway"] += before != new

        if new != doc:
            n["pages"] += 1
            if not a.dry_run:
                open(p, "w", encoding="utf-8").write(new)
    if not a.dry_run and cache and not a.no_prices:
        json.dump(cache, open(CACHE, "w"), separators=(",", ":"))
    if n["drawn"] + n["nochart"] and n["nochart"] > n["drawn"] and not a.no_prices:
        print(f"::warning::event pages: {n['nochart']} price chart(s) withheld, {n['drawn']} drawn; check the price "
              f"feed (FMP_API_KEY) if this persists")
    print(f"event page currency: {n['pages']} page(s) changed; charts {n['drawn']} drawn to the latest close, "
          f"{n['nochart']} withheld (no current closes), {n['decided']} removed (no decision ahead); month chips fixed on {n['chips']}, related rows on "
          f"{n['rows']}, unsourced runway removed from {n['runway']}")


if __name__ == "__main__":
    main()
