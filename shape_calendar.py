# -*- coding: utf-8 -*-
"""shape_calendar.py -- /calendar opens on its dates: upcoming months first, decided months folded below, the notes
at the end.

Design red team 2026-11-18 (change 7). /calendar put six paragraphs, a subscribe box and a heat map ahead of its first
date, one paragraph of them about our own pipeline ("26 of the 88 decided rows ... no row in the API dataset"), then
opened in June, five months of decided rows before the first date still ahead. Names were cut mid-word with no
ellipsis ("CTx-1301 (fixed dose, pediatri"), one row read "Approved: , LYTENAVA", and decided rows came in two
templates.

The page is written by about twenty scripts (reconcile_calendar_table.py, mark_calendar_decided.py,
inject_calendar_explainer.py, ...) that expect the old order: lede, explainer, months in date order. So this pass is
reversible. `--undo` puts the page back in that order and runs first in the daily chain; the plain run shapes it
and runs last, just before inject_mobile_polish.py. A shaped page that a writer touched without the undo still
heals: whatever the writer rewrote wins and the stashed copy is dropped.

Shaped, the page reads: h1, the lede's first sentence, the "Upcoming" heading, search, every month that still holds
an open goal date (oldest first), the 2027+ list, the decided months folded (newest first), then "About this
calendar" with the rest of the lede, the explainer, the subscribe box and the heat map.

Two fixes are permanent, not reversed: decided rows share one template (the one mark_calendar_decided.py writes),
and a decided row's name is the decision page's own (no cut-off names, no stray leading comma). Long names are
clamped to two lines with an ellipsis by CSS.

    python shape_calendar.py [--undo] [--dry-run] [--page PATH]
"""
import argparse
import html as H
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "calendar", "index.html")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
MHEAD = '<div class="mhead">'
ANCHOR = '<!--JUMP:B--><div id="pd-upcoming"></div><!--JUMP:E-->'
JUMP = re.compile(r"<!--JUMP:BEGIN-->.*?<!--JUMP:END-->", re.S)
M_B, M_E = "<!--CALSHAPE:MONTHS:BEGIN-->", "<!--CALSHAPE:MONTHS:END-->"
D_B, D_E = "<!--CALSHAPE:DONE:BEGIN-->", "<!--CALSHAPE:DONE:END-->"
A_B, A_E = "<!--CALSHAPE:ABOUT:BEGIN-->", "<!--CALSHAPE:ABOUT:END-->"
LEDECUT = "<!--CALSHAPE:LEDECUT-->"
EXPL = "<!--CALSHAPE:EXPL-->"
TOP = "<!--CALSHAPE:TOP-->"
STASH = re.compile(r"<!--CALSHAPE:(LEDE|EXPLDIV|TOPSEG)-->(.*?)<!--CALSHAPE:\1:END-->", re.S)
STYLE_ID = "calshape"
CSS = (f'<style id="{STYLE_ID}">'
       ".mdone{border:1px solid var(--line);border-radius:12px;margin:10px 0;padding:0 14px;background:var(--card)}"
       ".mdone>summary{cursor:pointer;padding:12px 0;font-family:'Space Grotesk',sans-serif;font-weight:700;"
       "font-size:15px;color:#eef4fc}"
       ".mdone>summary span{font-family:inherit;font-weight:400;color:var(--mut2);font-size:13px;margin-left:6px}"
       ".mdone .mhead{display:none}.mdone .grid{margin:4px 0 14px}"
       ".calabout{margin:26px 0 8px;padding-top:14px;border-top:1px solid var(--line)}"
       ".mdrows{margin:0 0 14px}.mdrows>summary{cursor:pointer;padding:6px 0;font-size:13px;color:var(--mut2)}"
       ".mdrows>.grid{margin-top:6px}"
       "</style>")
GREEN, RED = "#5fd07a", "#ff8f6b"


def close_div(s, i):
    """End of the <div> that opens at i."""
    d = 0
    for m in re.compile(r"<div\b|</div>").finditer(s, i):
        d += 1 if m.group(0) == "<div" else -1
        if d == 0:
            return m.end()
    raise ValueError("unclosed <div>")


def month_blocks(s, lo=0, hi=None):
    """[(start, end, 'Month YYYY')] for each month head + sentence + grid in s[lo:hi]."""
    hi = len(s) if hi is None else hi
    out = []
    for m in re.finditer(re.escape(MHEAD) + r"([A-Za-z]+ \d{4})</div>", s[:hi]):
        if m.start() < lo:
            continue
        g = s.find('<div class="grid">', m.end())
        out.append((m.start(), close_div(s, g), m.group(1)))
    return out


def month_key(name):
    mon, yr = name.split()
    return int(yr), MONTHS.index(mon) + 1


def is_open(block):
    return re.search(r'<a class="row" href="/pdufa/', block) is not None


# ---------------------------------------------------------------- open months: open rows first (UX pass 2026-11-20)
# On 2026-11-20 November listed 13 decided rows before its 7 open ones, under "Upcoming FDA PDUFA dates": a reader
# scrolled past a month of outcomes to reach the first date still ahead. In a month that still holds an open goal,
# the open rows come first and the decided and withdrawn rows fold below them. Reversible like the rest: the grid
# keeps its rows' original order in a comment, and unshape puts every row back where it stood.
RO = re.compile(r"<!--CALSHAPE:RO:([0-9,]+)-->")
RD = re.compile(r'<!--CALSHAPE:RD:BEGIN--><details class="mdrows"><summary>[^<]*</summary><div class="grid">(.*?)'
                r"</div></details><!--CALSHAPE:RD:END-->", re.S)
ROW_SPLIT = re.compile(r'(?=<a class="row")')
ROW_DAY = re.compile(r'<div class="t">[^<]*?(\d{4}-\d{2}-\d{2})')


def _rows(inner):
    """The <a class="row"> rows of a grid's inner html, or None when the grid holds anything else."""
    parts = [p for p in ROW_SPLIT.split(inner) if p]
    if not parts or any(not (p.startswith('<a class="row"') and p.endswith("</a>")) for p in parts):
        return None
    return parts


def _settled(row):
    return 'data-dec="1"' in row or 'data-wd="1"' in row or 'href="/fda-decision/' in row


def open_rows_first(blk, name):
    """A month block with its open rows first and its decided rows folded under them; unchanged when there is
    nothing to fold or the grid holds anything but rows."""
    g = blk.find('<div class="grid">')
    if g < 0 or "<!--CALSHAPE:R" in blk:
        return blk
    end = close_div(blk, g)
    rows = _rows(blk[g + len('<div class="grid">'):end - len("</div>")])
    if not rows:
        return blk
    top = [i for i, r in enumerate(rows) if not _settled(r)]
    low = [i for i, r in enumerate(rows) if _settled(r)]
    if not top or not low:
        return blk
    n = len(low)
    wd = sum('data-wd="1"' in rows[i] for i in low)
    what = "already decided" if not wd else ("withdrawn" if wd == n else "already decided or withdrawn")
    summary = f"{n} {'date' if n == 1 else 'dates'} in {name.split()[0]} {what}"
    return (blk[:g] + '<div class="grid">' + "<!--CALSHAPE:RO:" + ",".join(map(str, top + low)) + "-->"
            + "".join(rows[i] for i in top) + "</div>"
            + '<!--CALSHAPE:RD:BEGIN--><details class="mdrows"><summary>' + summary + '</summary><div class="grid">'
            + "".join(rows[i] for i in low) + "</div></details><!--CALSHAPE:RD:END-->" + blk[end:])


def restore_rows(s):
    """Every folded month's rows back in one grid, in their original order (date order when the order is lost)."""
    while True:
        d = RD.search(s)
        if not d:
            break
        low = _rows(d.group(1)) or []
        g = s.rfind('<div class="grid">', 0, d.start())
        ok = g >= 0 and s[d.start() - len("</div>"):d.start()] == "</div>"
        if not ok:
            # something now sits between the grid and the fold (a writer touched the shaped page): the fold's rows
            # go back to the end of the grid above it, then into date order below. Never left loose between months,
            # where the month rebuild below would drop them.
            if g < 0:
                raise SystemExit("shape_calendar: folded rows with no month grid above them; refusing to drop them")
            ge = close_div(s, g)
            if ge > d.start():
                raise SystemExit("shape_calendar: a fold sits inside a grid; refusing to guess where its rows go")
            s = s[:ge - len("</div>")] + "".join(low) + s[ge - len("</div>"):d.start()] + s[d.end():]
            g2 = s.rfind('<div class="grid">', 0, ge)
            inner_end = close_div(s, g2) - len("</div>")
            rows = _rows(RO.sub("", s[g2 + len('<div class="grid">'):inner_end], count=1))
            if rows:
                rows = sorted(rows, key=lambda r: ROW_DAY.search(r).group(1) if ROW_DAY.search(r) else "")
                s = s[:g2 + len('<div class="grid">')] + "".join(rows) + s[inner_end:]
            continue
        inner = s[g + len('<div class="grid">'):d.start() - len("</div>")]
        ro = RO.match(inner)
        order = [int(x) for x in ro.group(1).split(",")] if ro else []
        top = _rows(RO.sub("", inner, count=1)) or []
        rows = top + low
        if sorted(order) == list(range(len(rows))) and top:
            back = [None] * len(rows)
            for k, i in enumerate(order):
                back[i] = rows[k]
        else:
            back = sorted(rows, key=lambda r: ROW_DAY.search(r).group(1) if ROW_DAY.search(r) else "")
        s = s[:g] + '<div class="grid">' + "".join(back) + "</div>" + s[d.end():]
    return RO.sub("", s)


# ---------------------------------------------------------------- undo
def unshape(s):
    """The page in the order its writers expect. A page with no CALSHAPE markers comes back unchanged."""
    if "<!--CALSHAPE:" not in s:
        return s
    s = restore_rows(s)
    stash = {}
    a = re.search(re.escape(A_B) + r".*?" + re.escape(A_E), s, re.S)
    if a:
        stash = {k: v for k, v in STASH.findall(a.group(0))}
        s = s[:a.start()] + s[a.end():]
    # the lede: put its other sentences back, unless a writer has rewritten it since
    if LEDECUT in s:
        s = s.replace(LEDECUT, (" " + stash["LEDE"]) if stash.get("LEDE") else "", 1)
    # the explainer: back into its block, unless inject_calendar_explainer has written a fresh one
    if EXPL in s:
        s = s.replace(EXPL, stash.get("EXPLDIV", ""), 1)
    # the subscribe box and heat map: back between the search and the first month
    if TOP in s:
        s = s.replace(TOP, stash.get("TOPSEG", ""), 1)
    elif stash.get("TOPSEG") and MHEAD in s:
        i = s.find(M_B) if M_B in s else s.find(MHEAD)
        s = s[:i] + stash["TOPSEG"] + s[i:]
    # the months: every block, open and folded, back in date order where the open ones stood
    blocks, dpos = [], len(s)
    d = re.search(re.escape(D_B) + r".*?" + re.escape(D_E), s, re.S)
    if d:
        dpos = d.start()
        part = d.group(0)
        blocks += [part[b:e] for b, e, _n in month_blocks(part)]
        s = s[:d.start()] + s[d.end():]
    m = re.search(re.escape(M_B) + r"(.*?)" + re.escape(M_E), s, re.S)
    if m:
        part = m.group(1)
        blocks += [part[b:e] for b, e, _n in month_blocks(part)]
        blocks.sort(key=lambda b: month_key(re.match(re.escape(MHEAD) + r"([A-Za-z]+ \d{4})", b).group(1)))
        s = s[:m.start()] + "".join(blocks) + s[m.end():]
    elif blocks:
        # the open-months markers are gone (a writer rewrote that stretch): put the folded months back after the
        # last month still on the page rather than drop them
        rest = month_blocks(s)
        at = rest[-1][1] if rest else dpos
        s = s[:at] + "".join(sorted(blocks, key=lambda b: month_key(
            re.match(re.escape(MHEAD) + r"([A-Za-z]+ \d{4})", b).group(1)))) + s[at:]
    s = re.sub(r'<style id="%s">.*?</style>' % STYLE_ID, "", s, flags=re.S)
    return s


# ---------------------------------------------------------------- rows (permanent)
B_ROW = re.compile(r'<a class="row" href="(/fda-decision/[^"]+)"><div class="t">([^<]*?) · (\d{4}-\d{2}-\d{2}) · '
                   r'<span class="(ok|no)">(?:✓ Approved|✕ CRL)</span></div><div class="d">(.*?)</div></a>', re.S)
A_ROW = re.compile(r'(<a class="row" data-dec="1" href="/fda-decision/([^"]+)"><div class="t">.*?</div><div class="d">'
                   r'<span style="color:#[0-9a-f]{6};font-weight:700">(?:Approved|CRL)</span>: )(.*?)(</div></a>)', re.S)
TITLE = re.compile(r"<title>(.*?) (?:Approved|CRL|Complete Response Letter|Not Approved|Withdrawn)\b")
_titles = {}


def page_name(slug):
    if slug not in _titles:
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        t = TITLE.search(io.open(p, encoding="utf-8", errors="replace").read()[:4000]) if os.path.exists(p) else None
        _titles[slug] = H.unescape(t.group(1)).strip() if t else ""
    return _titles[slug]


def one_template(s):
    """The ~18 decided rows written as "AZN · 2026-06-12 · ✓ Approved" take the template of the other 77."""
    def b(m):
        href, label, day, kind, body = m.groups()
        col, icon, word = (GREEN, "✓", "Approved") if kind == "ok" else (RED, "✗", "CRL")
        return (f'<a class="row" data-dec="1" href="{href}"><div class="t">{label} &middot; {day} '
                f'<span style="color:{col};font-weight:700">{icon}</span></div>'
                f'<div class="d"><span style="color:{col};font-weight:700">{word}</span>: {body}</div></a>')
    return B_ROW.sub(b, s)


def whole_names(s):
    """A decided row's name, cut by an old build at a fixed width ("CTx-1301 (fixed dose, pediatri", "Romidepsin
    injection solution,") or opened with a stray comma (", LYTENAVA"), reads as its decision page names it."""
    def a(m):
        head, slug, body, tail = m.groups()
        text = body.strip()
        text = re.sub(r"^[,;:]\s*", "", text)
        bare = re.sub(r"<[^>]+>", "", text)
        name = page_name(slug)
        stem = bare.rstrip(" ,;:")
        cut = len(name) > len(stem) >= 6 and name.startswith(stem) and (
            name[len(stem)].isalnum() or stem.count("(") > stem.count(")"))   # stopped mid-word or inside a bracket
        if name and "<" not in text and cut:
            text = H.escape(name, quote=False)
        elif "<" not in text:
            text = text.rstrip(" ,")
            # "EBGLYSS (lebrikizumab-lbkz) -": a dash with nothing after it
            text = re.sub(r"\s+[-\u2013\u2014]$", "", text)
            # "MR-141 (phentolamine ophthalmic solution…: Presbyopia": a drug name cut by an old build and marked
            # with an ellipsis takes its decision page's name; a cut indication keeps its ellipsis, which says so
            drug, sep, rest = text.partition(": ")
            if name and drug.endswith("\u2026"):
                text = H.escape(name, quote=False) + (sep + rest if sep else "")
        return head + text + tail
    return A_ROW.sub(a, s)


# ---------------------------------------------------------------- shape
def shape(s):
    s = unshape(s)
    s = one_template(s)
    s = whole_names(s)
    if MHEAD not in s or "<!--LEDE:END-->" not in s:
        return s
    s = JUMP.sub("", s).replace(ANCHOR, "")
    blocks = month_blocks(s)
    lo, hi = blocks[0][0], blocks[-1][1]
    if re.sub(r"\s+", "", "".join(s[blocks[i][1]:blocks[i + 1][0]] for i in range(len(blocks) - 1))):
        return s                         # something else sits between the months: leave the page as it is
    texts = [(s[b:e], n) for b, e, n in blocks]
    open_ = sorted([t for t in texts if is_open(t[0])], key=lambda t: month_key(t[1]))
    done = sorted([t for t in texts if not is_open(t[0])], key=lambda t: month_key(t[1]), reverse=True)
    folded = ""
    if done:
        parts = []
        for blk, name in done:
            n = len(re.findall(r'<a class="row"', blk))
            wd = len(re.findall(r'<a class="row"[^>]*\bdata-wd="1"', blk))
            what = "all decided" if not wd else f"{n - wd} decided, {wd} withdrawn"
            parts.append(f'<details class="mdone"><summary>{name} <span>{n} date{"s" if n != 1 else ""}, '
                         f'{what}</span></summary>{blk}</details>')
        folded = (D_B + '<section class="caldone" style="margin:26px 0 8px;padding-top:14px;border-top:1px solid '
                  'var(--line)"><h2 style="font-size:16px;margin:0 0 4px">Months with no open goal date</h2>'
                  + "".join(parts) + "</section>" + D_E)
    s = s[:lo] + M_B + "".join(open_rows_first(t[0], t[1]) for t in open_) + M_E + s[hi:]
    # the decided months go after the 2027+ list when there is one, else straight after the open months
    at = s.find("<!--AHEAD:END-->")
    at = at + len("<!--AHEAD:END-->") if at >= 0 else s.find(M_E) + len(M_E)
    s = s[:at] + folded + s[at:]
    # the lede keeps its first sentence; the counts after it move to About
    stash = {}
    lm = re.search(r"(<!--LEDE:BEGIN--><p[^>]*>)(.*?)(</p><!--LEDE:END-->)", s, re.S)
    if lm:
        cut = re.search(r"\. (?=[A-Z0-9])", lm.group(2))
        if cut:
            stash["LEDE"] = lm.group(2)[cut.end():]
            s = s[:lm.start(2)] + lm.group(2)[:cut.start() + 1] + LEDECUT + s[lm.end(2):]
    em = re.search(r"(<!--EXPLAINER:BEGIN-->)(<div class=\"explainer\".*?</div>)", s, re.S)
    if em:
        stash["EXPLDIV"] = em.group(2)
        s = s[:em.start(2)] + EXPL + s[em.end(2):]
    sm = s.find("<!--SEARCH:END-->")
    if sm >= 0:
        sm += len("<!--SEARCH:END-->")
        stop = s.find(M_B)
        if 0 <= sm < stop:
            stash["TOPSEG"] = s[sm:stop]
            s = s[:sm] + TOP + s[stop:]
    if stash:
        lede_p = (f'<p style="margin:0 0 12px;font-size:14.5px;line-height:1.7;color:var(--mut2);max-width:76ch">'
                  f'<!--CALSHAPE:LEDE-->{stash["LEDE"]}<!--CALSHAPE:LEDE:END--></p>') if stash.get("LEDE") else ""
        about = (A_B + '<section class="calabout" id="about-this-calendar"><h2 style="font-size:16px;margin:0 0 8px">'
                 "About this calendar</h2>" + lede_p
                 + "".join(f"<!--CALSHAPE:{k}-->{stash[k]}<!--CALSHAPE:{k}:END-->" for k in ("EXPLDIV", "TOPSEG")
                           if stash.get(k))
                 + "</section>" + A_E)
        for mark in (D_E, "<!--AHEAD:END-->", M_E):     # after the folded months, else the 2027+ list
            if mark in s:
                at = s.find(mark) + len(mark)
                break
        s = s[:at] + about + s[at:]
    # right after the title: writers that re-append their own block before </head> each run (build_date_modified's
    # DMOD metas) would otherwise land between this style and </head>, and the next shape would move it back
    t = s.find("</title>")
    if t >= 0:
        s = s[:t + 8] + CSS + s[t + 8:]
    elif "</head>" in s:
        s = s.replace("</head>", CSS + "</head>", 1)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--undo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--page", default=PAGE)
    a = ap.parse_args()
    doc = io.open(a.page, encoding="utf-8", errors="replace").read()
    new = unshape(doc) if a.undo else shape(doc)
    if new == doc:
        print(f"calendar {'undo' if a.undo else 'shape'}: unchanged")
        return 0
    if not a.dry_run:
        io.open(a.page, "w", encoding="utf-8", newline="").write(new)
    print(f"calendar {'undo' if a.undo else 'shape'}: {'would write' if a.dry_run else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
