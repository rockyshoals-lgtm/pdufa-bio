# -*- coding: utf-8 -*-
"""phone_charts.py -- a phone-sized copy of each inline chart whose labels a phone would draw too small to read.

Used by inject_mobile_polish.py (item 13). Mobile red team 2026-11-18: the run-up price charts on ~540 decision and
PDUFA pages are drawn 640 units wide with 9-11 unit labels. A phone shows them about 290px wide, so the labels came
out 4-5px tall ("$27.37", "PDUFA 12/15/25"). Scaling the chart up does not help: the text grows with it and the
chart no longer fits. So each such chart gets a second, phone-sized drawing of the same data:

  * 320 units wide; x is scaled by 320/W, y by a gentler factor so the plot is taller on a narrow screen;
  * every label at least 12.2 units, which draws at 11px or more in a 290px phone column (larger phones: larger);
  * labels kept inside the chart, edged in the chart's background colour so a line under them does not cut
    through them, and moved off each other: a row of axis labels that would collide wraps at its
    spaces onto extra lines (the rows below move down), and a point label that would collide is put on the other
    side of its point, or just below or above.

Nothing is computed from data: every number, word and point comes from the desktop drawing, in the same order.
Wider screens show the desktop drawing unchanged; phones (up to 640px) show the copy. Idempotent: the copy is
stripped and rebuilt from the desktop drawing on every run.
"""
import html
import re

PW = 320.0            # phone drawing width, in units
LABEL = 12.2          # smallest phone label, in units: 12.2 * 290 / 320 = 11.06px in a 290px column
PHONE_COL = 290.0     # content width of a 320px phone
MIN_PX = 11.0
CHAR_EM = 0.6         # average glyph width, slightly generous (system-ui / mono digits are 0.55-0.6em)
TOP = 8.0             # headroom above the plot for labels over the highest point
MAX_W = 700           # charts this wide or wider scroll sideways instead (inject_mobile_polish.py item 12)

OPEN = '<!--PH:B--><div class="pd-ph">'
CLOSE = '</div><!--PH:E-->'
STRIP = re.compile(r'<!--PH:B--><div class="pd-ph">(<svg\b.*?</svg>)<svg class="pd-phs".*?</svg></div><!--PH:E-->',
                   re.S)
SVG = re.compile(r'<svg\b([^>]*)\bviewBox="0 0 ([\d.]+) ([\d.]+)"([^>]*)>(.*?)</svg>', re.S)
TAG = re.compile(r'<(text)\b([^>]*)>(.*?)</text>|<(line|circle|rect|polyline|polygon)\b([^>]*?)(/?)>', re.S)
NUM = r'(-?[\d.]+)'


def _attr(a, name, default=None):
    m = re.search(r'(?<![\w-])%s="([^"]*)"' % re.escape(name), a)
    return m.group(1) if m else default


def _set(a, name, val):
    v = ('%.1f' % val) if isinstance(val, float) else str(val)
    if re.search(r'(?<![\w-])%s="' % re.escape(name), a):
        return re.sub(r'(?<![\w-])(%s)="[^"]*"' % re.escape(name), lambda m: '%s="%s"' % (m.group(1), v), a, 1)
    return a + ' %s="%s"' % (name, v)


def label_sizes(body):
    return [float(z) for z in re.findall(r'<text\b[^>]*\bfont-size="([\d.]+)"', body)]


def needs_phone(w, body):
    """True when a chart narrower than MAX_W would draw a label under MIN_PX in a phone column."""
    sizes = label_sizes(body)
    return w < MAX_W and bool(sizes) and min(sizes) * min(1.0, PHONE_COL / w) < MIN_PX


def text_width(txt, fs):
    return len(txt) * CHAR_EM * fs


class Label:
    def __init__(self, attrs, inner, x, y, anchor, fs):
        self.attrs, self.inner, self.x, self.y, self.anchor, self.fs = attrs, inner, x, y, anchor, fs
        self.plain = html.unescape(re.sub(r'<[^>]+>', '', inner)).strip()
        self.lines = [inner]           # raw (entity-escaped) text of each line
        self.src_y = y

    def width(self):
        return max(text_width(html.unescape(l), self.fs) for l in self.lines)

    def box(self):
        w = self.width()
        left = {'start': self.x, 'middle': self.x - w / 2, 'end': self.x - w}.get(self.anchor, self.x)
        top = self.y - 0.82 * self.fs
        bottom = self.y + 0.22 * self.fs + (len(self.lines) - 1) * 1.15 * self.fs
        return left, left + w, top, bottom


def _hit(a, b, pad=1.0):
    return a[0] < b[1] + pad and b[0] < a[1] + pad and a[2] < b[3] + pad and b[2] < a[3] + pad


def phone_svg(open_attrs_pre, w, h, open_attrs_post, body):
    """The phone drawing of one chart, or None when it cannot be drawn safely (an element it does not know)."""
    sx = PW / w
    ky = min(1.0, 1.5 * sx) if w > PW else 1.0

    def X(v):
        return float(v) * sx

    def Y(v):
        return TOP + float(v) * ky

    pieces, labels, points, rects = [], [], [], []
    pos = 0
    for m in TAG.finditer(body):
        pieces.append(body[pos:m.start()])
        pos = m.end()
        if m.group(1):
            a, inner = m.group(2), m.group(3)
            if '<' in inner:
                return None            # tspans or other markup inside a label: leave the chart alone
            x, y = float(_attr(a, 'x', '0')), float(_attr(a, 'y', '0'))
            lab = Label(a, inner, X(x), Y(y), _attr(a, 'text-anchor', 'start'),
                        max(LABEL, float(_attr(a, 'font-size', '16'))))
            labels.append(lab)
            pieces.append(lab)
            continue
        tag, a, slash = m.group(4), m.group(5), m.group(6)
        if tag == 'line':
            for k, f in (('x1', X), ('x2', X), ('y1', Y), ('y2', Y)):
                if _attr(a, k) is not None:
                    a = _set(a, k, f(_attr(a, k)))
        elif tag == 'circle':
            cx, cy = X(_attr(a, 'cx', '0')), Y(_attr(a, 'cy', '0'))
            a = _set(_set(a, 'cx', cx), 'cy', cy)
            points.append((cx, cy, float(_attr(a, 'r', '2'))))
        elif tag == 'rect':
            for k, f in (('x', X), ('y', Y)):
                if _attr(a, k) is not None:
                    a = _set(a, k, f(_attr(a, k)))
            if _attr(a, 'width') is not None:
                a = _set(a, 'width', float(_attr(a, 'width')) * sx)
            if _attr(a, 'height') is not None:
                a = _set(a, 'height', float(_attr(a, 'height')) * ky)
            try:
                rx, ry = float(_attr(a, 'x', '0')), float(_attr(a, 'y', '0'))
                rw, rh = float(_attr(a, 'width', '0')), float(_attr(a, 'height', '0'))
                if rw < PW * 0.9 and rh > 0.5:      # a bar, not a background panel or a hairline
                    rects.append((rx, rx + rw, ry, ry + rh))
            except ValueError:
                pass
        else:                          # polyline / polygon
            pts = re.findall(NUM + r'\s*,\s*' + NUM, _attr(a, 'points', ''))
            a = _set(a, 'points', ' '.join('%.1f,%.1f' % (X(px), Y(py)) for px, py in pts))
        if re.search(r'\btransform=', a):
            return None
        pieces.append('<%s%s%s>' % (tag, a, slash))
    pieces.append(body[pos:])
    if re.search(r'<(path|g\b[^>]*transform|use|image|foreignObject|tspan)', body):
        return None
    if not labels:
        return None

    # 0. a label drawn just over or under its own point stays clear of it at the larger size
    for lab in labels:
        own = [p for p in points if abs(p[0] - lab.x) < 1.0 and abs(p[1] - lab.y) < 12 * ky + 4]
        if own:
            cx, cy, r = min(own, key=lambda p: abs(p[1] - lab.y))
            lab.own = (cx, cy, r)
            lab.y = cy - r - 4 if lab.y <= cy else cy + r + 4 + 0.78 * lab.fs
        else:
            lab.own = None

    # 1. rows of axis labels (same source baseline): a label wider than its slot wraps at a space
    rows = {}
    for lab in labels:
        if lab.own is None:
            rows.setdefault(round(lab.src_y, 1), []).append(lab)

    def split(lab):
        words = lab.inner.split(' ')
        if len(lab.lines) > 1 or len(words) < 2:
            return False
        best = min(range(1, len(words)), key=lambda k: abs(len(' '.join(words[:k])) - len(' '.join(words[k:]))))
        lab.lines = [' '.join(words[:best]), ' '.join(words[best:])]
        return True

    for y0 in sorted(rows):
        row = sorted(rows[y0], key=lambda l: l.x)
        grown = False
        for _ in range(len(row)):
            changed = False
            for u, v in zip(row, row[1:]):
                bu, bv = u.box(), v.box()
                if bu[1] + 3 > bv[0]:
                    first, second = (u, v) if u.width() >= v.width() else (v, u)
                    if split(first) or split(second):
                        changed = grown = True
            if not changed:
                break
    # 2. rows top to bottom: a row under bars clears the bars, a row clears the (possibly wrapped) rows above it,
    #    and every row below moves down with it; a single label on a bar's top clears the bar upward
    pushed, above = 0.0, []
    for y0 in sorted(rows):
        row = rows[y0]
        for lab in row:
            lab.y += pushed
        need = 0.0
        for lab in row:
            l, r, t, b = lab.box()
            for (x1, x2, y1, y2) in rects:
                if l < x2 and x1 < r and t < y2 + 2 and y1 < b:
                    if len(row) > 1 and (y1 + y2) / 2 < lab.y:
                        need = max(need, y2 + 2 - t)
                    elif lab.y < (y1 + y2) / 2:
                        lab.y -= b - (y1 - 2)
            l, r, t, b = lab.box()
            for (al, ar, at, ab) in above:
                if l < ar + 2 and al < r + 2 and t < ab + 3 and at < t:
                    need = max(need, ab + 3 - t)
        if need > 0:
            for lab in row:
                lab.y += need
            pushed += need
        above += [lab.box() for lab in row]

    # 3. keep every label inside the drawing, left and right
    for lab in labels:
        l, r, _, _ = lab.box()
        if l < 3:
            lab.x += 3 - l
        elif r > PW - 3:
            lab.x -= r - (PW - 3)

    # 4. a label that collides with another label or with a point moves to the other side of its point, or
    #    beside it, or down, or up
    dots = [(cx - r - 1, cx + r + 1, cy - r - 1, cy + r + 1) for cx, cy, r in points]

    def clear(lab, placed):
        bx = lab.box()
        own = lab.own and (lab.own[0] - lab.own[2] - 1, lab.own[0] + lab.own[2] + 1,
                           lab.own[1] - lab.own[2] - 1, lab.own[1] + lab.own[2] + 1)
        return (bx[2] >= -TOP and not any(_hit(bx, p, 0.5) for p in placed)
                and not any(_hit(bx, d, 0) for d in dots if d != own))

    placed = []
    for lab in labels:
        if clear(lab, placed):
            placed.append(lab.box())
            continue
        y0, x0, a0 = lab.y, lab.x, lab.anchor
        tries = []
        if lab.own:
            cx, cy, r = lab.own
            tries += [(cx, cy + r + 3 + 0.78 * lab.fs, 'middle'), (cx, cy - r - 3, 'middle'),
                      (cx + r + 3, cy + 0.3 * lab.fs, 'start'), (cx - r - 3, cy + 0.3 * lab.fs, 'end')]
        tries += [(x0, y0 + 1.15 * lab.fs, a0), (x0, y0 - 1.15 * lab.fs, a0), (x0, y0 + 2.3 * lab.fs, a0)]
        for tx, ty, ta in tries:
            lab.x, lab.y, lab.anchor = tx, ty, ta
            l, r, _, _ = lab.box()
            if l < 3 or r > PW - 3:
                continue
            if clear(lab, placed):
                break
        else:
            lab.x, lab.y, lab.anchor = x0, y0, a0
        placed.append(lab.box())

    top = min([0.0] + [lab.box()[2] - 2 for lab in labels])
    bottom = max([Y(h)] + [lab.box()[3] + 3 for lab in labels])
    ph = bottom - top

    m = re.search(r'background:\s*(#[0-9a-fA-F]{3,6})', open_attrs_pre + open_attrs_post)
    bg = m.group(1) if m else '#071528'
    out = []
    for p in pieces:
        if isinstance(p, Label):
            a = _set(_set(_set(p.attrs, 'x', p.x), 'y', p.y), 'font-size', p.fs)
            if 'stroke=' not in a:      # a halo in the chart's background colour keeps a label legible over the line
                a += ' stroke="%s" stroke-width="3" stroke-linejoin="round" paint-order="stroke"' % bg
            if p.anchor != _attr(p.attrs, 'text-anchor', 'start'):
                a = _set(a, 'text-anchor', p.anchor)
            if len(p.lines) == 1:
                out.append('<text%s>%s</text>' % (a, p.lines[0]))
            else:
                out.append('<text%s>%s</text>' % (a, ''.join(
                    '<tspan x="%.1f"%s>%s</tspan>' % (p.x, '' if i == 0 else ' dy="%.1f"' % (1.15 * p.fs), t)
                    for i, t in enumerate(p.lines))))
        else:
            out.append(p)
    pre = re.sub(r'\bclass="[^"]*"', '', open_attrs_pre)
    post = open_attrs_post
    attrs = (pre + post)
    attrs = re.sub(r'aspect-ratio:\s*[\d.]+\s*/\s*[\d.]+', 'aspect-ratio:%d/%d' % (PW, round(ph)), attrs)
    attrs = re.sub(r'max-width:\s*[\d.]+px;?', '', attrs)
    attrs = re.sub(r'\s+(id|aria-labelledby)="[^"]*"', '', attrs)
    return '<svg class="pd-phs"%s viewBox="0 %.1f %d %.1f">%s</svg>' % (
        attrs.rstrip(), top, PW, ph, ''.join(out))


def phone_label_px(phone):
    """Smallest label of a phone drawing, in px, in a 290px column."""
    m = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) [\d.]+"', phone)
    sizes = label_sizes(phone)
    return min(sizes) * PHONE_COL / float(m.group(1)) if m and sizes else None


def wrap_phone_charts(doc):
    base = STRIP.sub(r'\1', doc)
    if '<svg' not in base:
        return base

    def one(m):
        pre, w, h, post, body = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4), m.group(5)
        if 'pd-phs' in pre or not needs_phone(w, body):
            return m.group(0)
        ph = phone_svg(pre, w, h, post, body)
        if not ph:
            return m.group(0)
        return OPEN + m.group(0) + ph + CLOSE

    out, last = [], 0
    for m in SVG.finditer(base):
        before = base[:m.start()]
        if before.rfind('<script') > before.rfind('</script>'):
            continue                   # an SVG string inside a script is not a chart on the page
        out += [base[last:m.start()], one(m)]
        last = m.end()
    out.append(base[last:])
    return ''.join(out)
