# -*- coding: utf-8 -*-
"""inject_a11y.py -- keyboard, screen-reader and contrast fixes every page needs, applied once, site-wide. Idempotent.

Design red team 2026-11-18 (change 12, "Accessibility and speed"). What it found, and what this pass does about each:

1. No skip link. Every page opens on a header of 18 to 21 links (30-plus with the Explore and Research menus), so a
   keyboard or screen-reader user went through all of them on every page before reaching its content. A "Skip to
   content" link now comes first in the header (before the logo, so a banner above the header, like the "Unverified
   record" notice on an inferred decision page, is still read first). It is hidden until it has focus, and it jumps
   to an empty target right after the header's navigation.
2. Charts with no name. About 970 price and bar charts are drawn as role="img" with no aria-label, which a screen
   reader announces as "image" and nothing more (it does not read the chart's own text under role="img"). Each one
   is named from its section heading and the caption under it, which on a decision page states the window, the
   run-up high and low with their dates, and the decision day. (Run before inject_mobile_polish.py, whose phone copy
   of a chart carries the desktop chart's name.)
3. Sparklines with no text. The 64x20 and 72x20 price sparklines on the homepage and /readouts showed up or down by
   colour alone and said nothing to a screen reader. Their builders now name each one with the move in words
   (build_home_board.py, build_readout_results.py); this pass names any left from an older build by its direction.
4. The screener's result count changed silently. Its count line is now a polite live region, so a screen reader
   hears "38 catalysts from 2026-11-18" after each filter change.
5. FAQ disclosure markers were hidden (list-style:none on 1,309 <summary> elements), so a question gave no sign that
   it opens. The marker is back.
6. Text fields drew their border at 2.17:1 against the field (#294d80 on #081426), under the 3:1 that WCAG 1.4.11
   asks of a control's boundary. Fields now draw it in #4a78b0 (4.0:1 on the field, 3.7:1 on a card) and gold on
   focus.

tests/test_accessibility.py fails if a page is not at this pass's state, or if any of the above comes back.

    python inject_a11y.py [--dry-run]
"""
import argparse
import glob
import html
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

# Same exclusions as inject_mobile_polish.py: backups, locked and private pages are not part of the public site.
SKIP = re.compile(r"(_bak|_xbak|/_|\\_|app\.html|holding\.html|preview\.html|ping\.html|today\.html|index_redesign"
                  r"|[/\\]api[/\\])", re.I)

STYLE_ID = "pd-a11y"
FIELD_BORDER = "#4a78b0"
CSS = (f'<style id="{STYLE_ID}">'
       '.pd-skip{position:fixed;left:8px;top:-80px;z-index:10000;padding:10px 16px;border-radius:8px;'
       'background:#f0c86a;color:#1a1204!important;font:700 15px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",'
       'Roboto,Helvetica,Arial,sans-serif;text-decoration:none!important}'
       '.pd-skip:focus{top:8px;outline:2px solid #fff;outline-offset:2px}'
       '#main-content:focus{outline:none}'
       'input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=range]):not([type=submit])'
       f':not([type=button]),select,textarea{{border-color:{FIELD_BORDER}!important}}'
       'input:focus,select:focus,textarea:focus{border-color:#f0c86a!important}'
       '</style>')

SKIP_LINK = '<!--SKIP:B--><a class="pd-skip" href="#main-content">Skip to content</a><!--SKIP:E-->'
TARGET = '<!--SKIPT:B--><span id="main-content" tabindex="-1"></span><!--SKIPT:E-->'
SKIP_BLOCKS = re.compile(r"<!--SKIPT?:B-->.*?<!--SKIPT?:E-->", re.S)
NAV_END = re.compile(r"<!--NAVC:END-->(?:\s*</[a-z]+>)*")

METER = '<div class="meta" id="meta">'
METER_LIVE = '<div class="meta" id="meta" role="status" aria-live="polite">'

SVG_OPEN = re.compile(r"<svg\b[^>]*>")
SCRIPT = re.compile(r"<script\b.*?</script>", re.S)


def _text(seg):
    seg = re.sub(r"<!--.*?-->", " ", seg, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", seg))).strip()


def _attr(s):
    return html.escape(s, quote=True)


def _outside_scripts(doc, fn):
    out, pos = [], 0
    for s in SCRIPT.finditer(doc):
        out.append(fn(doc[pos:s.start()]))
        out.append(s.group(0))
        pos = s.end()
    out.append(fn(doc[pos:]))
    return "".join(out)


def chart_name(doc, start, end):
    """A name for the role="img" chart at doc[start:end]: its section heading, then the caption under it."""
    before = SCRIPT.sub(" ", doc[max(0, start - 3000):start])
    heads = re.findall(r"<h[23]\b[^>]*>(.*?)</h[23]>", before, re.S)
    head = _text(heads[-1]) if heads else ""
    note = ""
    close = doc.find("</svg>", end)
    end = close + 6 if close >= 0 else end
    after = doc[end:end + 20000]
    m = re.search(r"<div class=['\"]note['\"][^>]*>(.*?)</div>", after, re.S)
    if m:
        gap = re.sub(r'<svg class="pd-phs".*?</svg>', "", after[:m.start()], flags=re.S)
        if not _text(gap) and "<svg" not in gap:
            note = _text(m.group(1))
    if not head and not note:
        body = doc[start:end]
        note = _text(re.sub(r"<(?:text|tspan)\b[^>]*>", " ", body))
    name = ". ".join(x.rstrip(".") for x in (head, note) if x) or "Chart"
    if len(name) > 420:
        name = name[:417].rsplit(" ", 1)[0] + "..."
    return name if name.endswith((".", "...")) else name + "."


def name_charts(doc):
    def fix(seg):
        out, pos = [], 0
        for m in SVG_OPEN.finditer(seg):
            tag = m.group(0)
            if 'aria-hidden="true"' in tag or "aria-label=" in tag or "aria-labelledby=" in tag:
                continue
            if 'role="img"' in tag and "pd-phs" not in tag:
                new = tag[:-1].rstrip() + f' aria-label="{_attr(chart_name(seg, m.start(), m.end()))}">'
            elif (re.search(r'\bheight="20"', tag) and re.search(r'viewBox="0 0 (?:64|72) 20"', tag)
                  and "flex:0 0 auto" in tag and "role=" not in tag):
                # a sparkline from an older build: name it by the direction its builder coloured it
                body = seg[m.end():seg.find("</svg>", m.end())]
                up = 'stroke="#46d17f"' in body
                down = 'stroke="#ff7a72"' in body
                if not (up or down):
                    continue
                words = f"Share price over the period shown: {'rose' if up else 'fell'}"
                new = tag[:-1] + f' role="img" aria-label="{words}"><title>{words}</title>'
            else:
                continue
            out += [seg[pos:m.start()], new]
            pos = m.end()
        out.append(seg[pos:])
        return "".join(out)
    return _outside_scripts(doc, fix)


def skip_link(doc):
    doc = SKIP_BLOCKS.sub("", doc)
    end = NAV_END.search(doc)
    brand = doc.find('<a class="brand"')
    if not end or brand < 0 or brand > end.start():
        return doc
    doc = doc[:end.end()] + TARGET + doc[end.end():]
    return doc[:brand] + SKIP_LINK + doc[brand:]


def summary_markers(doc):
    def fix(m):
        tag = re.sub(r";\s*list-style:\s*none\s*(?=[;\"])|list-style:\s*none\s*;?\s*", "", m.group(0))
        return tag.replace(' style=""', "")
    return re.sub(r"<summary\b[^>]*>", fix, doc)


def apply(doc):
    if "</head>" not in doc:
        return doc
    new = skip_link(doc)
    new = summary_markers(new)
    new = name_charts(new)
    new = new.replace(METER, METER_LIVE)
    # like inject_mobile_polish.py: a current style block stays where it is (later steps insert before </head>)
    blocks = re.findall(r'<style id="%s">.*?</style>' % STYLE_ID, new, flags=re.S)
    if blocks != [CSS]:
        new = re.sub(r'<style id="%s">.*?</style>' % STYLE_ID, "", new, flags=re.S)
        new = new.replace("</head>", CSS + "</head>", 1)
    return new


def pages():
    return [p for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)) if not SKIP.search(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = skips = charts = 0
    for p in pages():
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        new = apply(doc)
        skips += SKIP_LINK in new
        charts += len(re.findall(r'<svg\b[^>]*role="img"[^>]*aria-label=', new))
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"accessibility pass: {n} page(s) " + ("would change [dry run]" if a.dry_run else "written")
          + f"; {skips} with a skip link; {charts} named chart(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
