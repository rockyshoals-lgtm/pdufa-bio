# -*- coding: utf-8 -*-
"""inject_mobile_polish.py -- phone and tablet fixes that every page needs, applied once, site-wide. Idempotent.

Mobile red team 2026-11-17 (David: "ensure that the site works on all mobile devices and maintains immaculate UX").
What it found, and what this pass does about each:

1. A thin line and a dark band hung across the top of every page with the mobile menu (about 2,000 pages), and
   stayed fixed over the text while scrolling. The collapsed menu panel (style#navpolish, max-height:0) still drew
   its 1px bottom border and its 40px drop shadow. Its 18 links also stayed in the keyboard tab order and in what a
   screen reader reads, although nobody could see them. Closed now means hidden: no border, no shadow, not
   focusable; the open/close animation is unchanged.
2. Tables widened whole pages. /runup-by-year's year table (8 columns) made the entire run-up study scroll
   sideways on a phone, header and logo included. Every <table> that is not already inside a scrolling box gets
   one (div.pd-tw), so a wide table scrolls inside itself and the page stays the width of the screen. Pages whose
   builder already wraps its tables are left alone.
3. Long unbroken strings (URLs, application numbers, chemical names) can no longer push a page wider than the
   screen (overflow-wrap), and images and inline charts never exceed their column.
4. Search boxes used 15px text, which makes iPhone Safari zoom the whole page in when the box is tapped and leave
   it zoomed. Form fields are 16px on phones.
5. iPhones in landscape: about half the pages declare viewport-fit=cover, which lets content run under the notch.
   The page now pads by the safe-area insets (zero everywhere else).
6. In-page links (#anchors) land below the sticky header instead of under it.
7. The site-wide "Browse pdufa.bio" links get taller rows so neighbouring links are not mis-tapped.
8. Linked list rows on ticker, drug and PDUFA pages (a date span, then a description span, both inline) ran
   together: /ticker/SRPT read "2026-09Eteplirsen". The description now starts its own line, as on the
   calendar and decision pages, which already used block elements for it.
9. Links no rule colours (the CSV download on /research/conference-runup, among others) fell back to the
   browser's default dark blue, nearly invisible on the site's near-black background. They now take the site's
   link blue; any colour a page sets itself still wins (zero-specificity :where()).
10. /calendar opens on months that are all decided (June to October) before the first date still ahead. A
   "Jump to upcoming dates" link under the lede goes to the first month that still has an open goal date.
11. Card grids widened pages: a grid column is at least as wide as its widest unbreakable line, so one long
   company name made every /tickers row 403px wide on a 320px phone. Grid items may now shrink (min-width:0)
   on phones; a name that does not fit ends in an ellipsis where the page asks for one, and wraps otherwise.
   The /readouts past-window rows (label block fixed at min-width:150px, a 72px sparkline and the move) were
   325px wide at 320px; the label block may now shrink and wrap on phones.
12. Wide charts shrank to unreadable text: the /readouts monthly bar chart (782 units wide, 9-unit labels) drew its
   labels about 3px tall on a 320px phone, the /calendar weekly density chart about 3px. A chart at least 700
   units wide whose smallest label would draw under 10px in a phone column is put in a sideways-scrolling box
   (div.pd-cx) and drawn on phones at the width that makes its smallest label 11px. Wider screens are unchanged.
13. Narrower charts did the same: the run-up price chart on ~540 decision and PDUFA pages (640 units wide, 9-11 unit
   labels) drew "$27.37" and "PDUFA 12/15/25" 4-5px tall on a phone. Each such chart gets a phone-sized drawing of
   the same points and labels (phone_charts.py): 320 units wide, labels at least 11px in a 290px column, kept
   inside the chart and off each other. Phones show it; wider screens show the original.

The search button (cmdk.js) is a static file and is fixed there. Nothing here changes a fact, a number, a date,
a link target or any text: only layout. build_sitemap.py strips everything this adds before hashing, so the sweep
does not advance any page's lastmod (the runaway that site-wide sweeps caused four times before).

    python inject_mobile_polish.py [--dry-run]
"""
import argparse
import glob
import io
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phone_charts  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

# Same exclusions as rebuild_nav.py: backups, locked and private pages are not part of the public site.
SKIP = re.compile(r"(_bak|_xbak|/_|\\_|app\.html|holding\.html|preview\.html|ping\.html|today\.html|index_redesign"
                  r"|[/\\]api[/\\])", re.I)

STYLE_ID = "mobilepolish"
TW_OPEN = '<!--TW:B--><div class="pd-tw">'
TW_CLOSE = '</div><!--TW:E-->'

CSS = (
    f'<style id="{STYLE_ID}">'
    # 3. nothing wider than its column
    'html{-webkit-text-size-adjust:100%;text-size-adjust:100%}'
    'body{overflow-wrap:break-word}'
    'img{max-width:100%;height:auto}svg,video,canvas,iframe{max-width:100%}'
    'pre{max-width:100%;overflow-x:auto}'
    # 14. the "Browse pdufa.bio" block at the foot of every page: six labelled columns of links, sized by the width of
    # the column it sits in (6 across a wide page, 3 on a narrow one, 2 on a phone). It outranks the homepage's
    # header rules nav{display:flex} and nav a{padding:7px 11px}, which used to scatter its separators.
    '.pd-browse{display:block!important;container:pdb/inline-size;margin:30px 0 8px;padding-top:18px;'
    'border-top:1px solid #1a3358;font-size:13px;line-height:1.4;color:#94a9c9}'
    '.pd-bh{margin:0 0 14px;color:#cfe0f5;font-size:14px;font-weight:700}'
    '.pd-bg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 18px}'
    '@container pdb (min-width:560px){.pd-bg{grid-template-columns:repeat(3,minmax(0,1fr))}}'
    '@container pdb (min-width:1000px){.pd-bg{grid-template-columns:repeat(6,minmax(0,1fr))}}'
    '.pd-bgt{margin:0 0 6px;color:#94a9c9;font-size:11px;font-weight:700;letter-spacing:.07em;text-transform:uppercase}'
    '.pd-browse a{display:block;margin:0;padding:4px 0;border-radius:0;background:none;color:#9ec5ff;font-size:13px;'
    'line-height:1.4;text-decoration:none}'
    '.pd-browse a:hover{background:none;color:#eef4fc;text-decoration:underline}'
    '.pd-browse a.pd-ball{display:inline-block;margin-top:16px}'
    # 2. tables scroll inside themselves
    '.pd-tw{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}'
    '.pd-tw>table{margin-left:0;margin-right:0}'
    # 6. anchors clear the sticky header
    ':target{scroll-margin-top:76px}'
    # 9. links nobody coloured: site blue instead of the browser's dark blue (anything a page sets wins)
    ':where(a){color:#6fb6ff}'
    # 10. calendar: jump past decided months
    '.pd-jump{display:inline-flex;align-items:center;min-height:40px;padding:8px 14px;margin:0 0 14px;'
    'border:1px solid #294d80;border-radius:10px;color:#eef4fc;font-size:13.5px;font-weight:600;text-decoration:none}'
    '.pd-jump:hover{border-color:#e3ba5e;text-decoration:none}'
    # 8. list rows: the description sits under its date, not glued to it ("2026-09Eteplirsen")
    '.row>.t+.d{display:block}'
    # 12. wide charts: scroll sideways on phones at a readable size (width per chart in --cxw)
    '.pd-cx{max-width:100%}'
    # 13. narrower charts: a phone-sized drawing replaces the original on phones
    '.pd-ph>.pd-phs{display:none!important}'
    # 5. notch / rounded corners in landscape (env() is 0 where there is none)
    '@supports(padding:max(0px)){html{padding-left:env(safe-area-inset-left);'
    'padding-right:env(safe-area-inset-right)}}'
    '@media(max-width:720px){'
    # 1. a closed menu is hidden, not just zero-height
    'body:not(.pd-navopen) .pd-burger~nav,body:not(.pd-navopen) .pd-burger~.nav{border-bottom-color:transparent;'
    'box-shadow:none;visibility:hidden;transition:max-height .25s ease,visibility 0s linear .25s}'
    'body.pd-navopen .pd-burger~nav,body.pd-navopen .pd-burger~.nav{visibility:visible;transition:max-height .25s ease}'
    # 4. no zoom-on-focus in iOS Safari
    'input:not([type=checkbox]):not([type=radio]):not([type=range]),select,textarea{font-size:16px!important}'
    # 7. link rows: room between links for a fingertip (each Browse link a 32px row)
    '.pd-browse a{padding:7px 0}'
    '}'
    '@media(max-width:640px){'
    # 11. grid cards may shrink below their longest unbreakable line
    '.grid>*{min-width:0}.row>div[style*="min-width:150px"]{min-width:0!important;flex:1 1 auto}'
    # 12. (see above)
    '.pd-cx{overflow-x:auto;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}'
    '.pd-cx>svg{min-width:var(--cxw);max-width:none!important}'
    '.pd-ph>svg:not(.pd-phs){display:none!important}.pd-ph>.pd-phs{display:block!important;width:100%;height:auto}'
    '}'
    '</style>'
)

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
OVERFLOW = re.compile(r"overflow(?:-x)?\s*:\s*(?:auto|scroll)")


def scrolling_classes(doc):
    """Class names the page's own CSS already makes horizontally scrollable."""
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S))
    out = set()
    for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if OVERFLOW.search(decl):
            for part in sel.split(","):
                m = re.search(r"\.([\w-]+)(?:[^\w-][^.]*)?$", part.strip())
                if m:
                    out.add(m.group(1))
    return out


class TableFinder(HTMLParser):
    """Byte offsets of each top-level <table>...</table> that has no scrolling ancestor."""

    def __init__(self, doc, ovcls):
        super().__init__(convert_charrefs=False)
        self.doc, self.ovcls = doc, ovcls
        self.stack = []          # (tag, scrolls)
        self.open_at = None      # offset of the <table> being tracked
        self.depth = 0           # nested table depth inside the tracked one
        self.spans = []
        # line -> offset map for getpos()
        self.line_starts = [0]
        for m in re.finditer(r"\n", doc):
            self.line_starts.append(m.end())

    def _off(self):
        ln, col = self.getpos()
        return self.line_starts[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            if self.open_at is not None:
                self.depth += 1
            elif not any(s for _, s in self.stack):
                self.open_at, self.depth = self._off(), 0
        if tag in VOID:
            return
        cls = (a.get("class") or "").split()
        scrolls = bool(OVERFLOW.search(a.get("style") or "")) or any(c in self.ovcls for c in cls)
        self.stack.append((tag, scrolls))

    def handle_endtag(self, tag):
        if tag == "table" and self.open_at is not None:
            if self.depth:
                self.depth -= 1
            else:
                end = self.doc.find(">", self._off()) + 1
                self.spans.append((self.open_at, end))
                self.open_at = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def wrap_tables(doc):
    if "<table" not in doc:
        return doc, 0
    # strip our own earlier wrappers first so the result is the same every run
    base = doc.replace(TW_OPEN, "").replace(TW_CLOSE, "")
    p = TableFinder(base, scrolling_classes(base))
    try:
        p.feed(base)
        p.close()
    except Exception:
        return doc, 0
    if not p.spans:
        return base, 0
    out, last = [], 0
    for s, e in p.spans:
        if e <= s or not base.startswith("<table", s) or not base[:e].endswith("</table>"):
            continue
        out += [base[last:s], TW_OPEN, base[s:e], TW_CLOSE]
        last = e
    out.append(base[last:])
    return "".join(out), len(p.spans)


CX_OPEN = re.compile(r'<!--CX:B--><div class="pd-cx" style="--cxw:\d+px">')
CX_CLOSE = '</div><!--CX:E-->'
SVG = re.compile(r'<svg\b[^>]*\bviewBox="0 0 ([\d.]+) [\d.]+"[^>]*>.*?</svg>', re.S)
PHONE_COL, MIN_LABEL, CHART_MIN_W = 330.0, 11.0, 700


def wrap_charts(doc):
    """Wrap each wide inline chart whose smallest label would draw under 10px in a phone column (12. above)."""
    base = CX_OPEN.sub("", doc).replace(CX_CLOSE, "")
    if "<svg" not in base:
        return base

    def one(m):
        w = float(m.group(1))
        sizes = [float(z) for z in re.findall(r'<text\b[^>]*\bfont-size="([\d.]+)"', m.group(0))]
        if w < CHART_MIN_W or not sizes or min(sizes) * PHONE_COL / w >= 10:
            return m.group(0)
        cxw = max(int(w), int(-(-w * MIN_LABEL // min(sizes))))
        return f'<!--CX:B--><div class="pd-cx" style="--cxw:{cxw}px">' + m.group(0) + CX_CLOSE

    return SVG.sub(one, base)


JUMP_B, JUMP_E = "<!--JUMP:BEGIN-->", "<!--JUMP:END-->"
ANCHOR = '<!--JUMP:B--><div id="pd-upcoming"></div><!--JUMP:E-->'
MHEAD = '<div class="mhead">'


def calendar_jump(doc):
    """On a calendar page (month heads + a lede), link past the decided months to the first month that still has
    an open goal date (a row linking /pdufa/, not a published /fda-decision/ record). No date arithmetic, so the
    result depends on the page alone and the guard can recompute it. The month head itself is left untouched
    (tests/test_calendar_rows_under_their_month.py reads it); the target is an empty div just above it."""
    doc = re.sub(re.escape(JUMP_B) + ".*?" + re.escape(JUMP_E), "", doc, flags=re.S)
    doc = doc.replace(ANCHOR, "")
    if "<!--LEDE:END-->" not in doc or MHEAD not in doc:
        return doc
    heads = [m.start() for m in re.finditer(re.escape(MHEAD), doc)]
    for i, at in enumerate(heads):
        seg = doc[at:heads[i + 1] if i + 1 < len(heads) else len(doc)]
        if re.search(r'<a class="row" href="/pdufa/', seg):
            if i == 0:
                return doc          # the first month is already open: nothing to skip
            doc = doc[:at] + ANCHOR + doc[at:]
            return doc.replace("<!--LEDE:END-->", "<!--LEDE:END-->" + JUMP_B
                               + '<a class="pd-jump" href="#pd-upcoming">Jump to upcoming dates &darr;</a>'
                               + JUMP_E, 1)
    return doc


def apply(doc):
    new, n = wrap_tables(doc)
    new = calendar_jump(new)
    new = wrap_charts(new)
    new = phone_charts.wrap_phone_charts(new)
    # A current style block stays exactly where it is. Later build steps (freshness stamp, dateModified, article
    # schema, quarantine) also insert before </head>, so "always re-insert last" moved the block on every run and the
    # guard's apply(doc) == doc failed on 1,826 pages after the 2026-11-18 rebuild (issue 113). Only a missing,
    # stale or duplicated block is replaced.
    blocks = re.findall(r'<style id="%s">.*?</style>' % STYLE_ID, new, flags=re.S)
    if blocks == [CSS]:
        return new, n
    new = re.sub(r'<style id="%s">.*?</style>' % STYLE_ID, "", new, flags=re.S)
    if "</head>" in new:
        new = new.replace("</head>", CSS + "</head>", 1)
    return new, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pages = tables = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if SKIP.search(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        if "</head>" not in doc:
            continue
        new, n = apply(doc)
        tables += n
        if new != doc:
            pages += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"mobile polish: {pages} page(s) updated, {tables} table(s) given a scroll box"
          + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
