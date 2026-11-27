# -*- coding: utf-8 -*-
"""inject_ticker_crosslinks.py -- a company's catalyst hub (/ticker/<T>) links its earnings dates and FDA device
decisions (design pass, OMW, 2026-11-27).

The earnings pages (/earnings/<T>, build_earnings_pages.py) and the device decision pages (/devices/decisions,
build_device_decisions.py) link a company's hub, but the hub linked neither back: a reader on /ticker/ILMN could not
see Illumina's device approvals or its next results day without leaving for a hub page and finding the row.

This writes one marker-bounded block (<!--TXL:BEGIN--> ... <!--TXL:END-->) on each hub, built from the same caches
and the same rules as those pages, so the hub can never state a date the earnings or device page does not:

  * Earnings dates, only when /earnings/<T> exists: the report days the company has announced that are still ahead,
    or, with none ahead, its latest results release; then a link to the full page.
  * FDA device decisions, only for rows whose applicant matched this ticker exactly (fetch_fda_devices.py): the
    three newest PMA approvals and De Novo grants, each linking the FDA's own record, and the year pages.

Nothing is estimated: a date appears only where the company's release or the FDA's record states it. A hub with
nothing to show loses the block. Idempotent; run after build_earnings_pages.py, build_device_decisions.py and every
generator that writes /ticker pages, before inject_site_links.py.

    python inject_ticker_crosslinks.py [--site DIR] [--today YYYY-MM-DD]
"""
import argparse
import collections
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_device_decisions as D  # noqa: E402
import build_earnings_pages as E  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
B, END = "<!--TXL:BEGIN-->", "<!--TXL:END-->"
BLOCK = re.compile(re.escape(B) + r".*?" + re.escape(END), re.S)
ANCHORS = ('<a class="cta" href="/calendar">', "<!--STOCKRUNUP:BEGIN-->", "<!--RELATED:BEGIN-->")
MAX_ROWS = 3

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def esc(s):
    return html.escape(str(s or ""), quote=True)


def short(d):
    """'Dec 30, 2025', the hub's own date style."""
    return esc(f"{d:%b} {d.day}, {d.year}") if d else ""


def row(href, when, what, external=False):
    rel = ' rel="noopener nofollow"' if external else ""
    return f'<a class="row" href="{esc(href)}"{rel}><span class="t">{when}</span><span class="d">{what}</span></a>'


def earnings_rows(tk, T, pages, today):
    if tk not in pages:
        return []
    t = T[tk]
    ahead, latest = [], None
    for k, p in t["P"].items():
        s, st = E.status_of(p, today)
        if st == "ahead":
            ahead.append((E.d_of(s["report_date"]), k, p, s))
        r = p["results"]
        if r and (latest is None or (r.get("published_et") or "") > (latest[2].get("published_et") or "")):
            latest = (k, p, r)
    out = []
    for d, k, p, s in sorted(ahead, key=lambda x: x[0])[:MAX_ROWS]:
        out.append(row(f"/earnings/{tk}", short(d),
                       f"{esc(E.label(k, p))} results: the day {esc(t['name'])} announced"))
    if not out and latest:
        k, p, r = latest
        out.append(row(f"/earnings/{tk}", short(E.d_of(r["published_et"])),
                       f"{esc(E.label(k, p))} results released: the newest results release we have read"))
    if not out:
        return []
    out.append(row(f"/earnings/{tk}", "All dates", f"Every {esc(tk)} results date read from the company's releases"))
    return [f'<h2 id="earnings">Earnings dates</h2>'] + out


def device_rows(tk, by_tk, site):
    rows = by_tk.get(tk) or []
    if not rows:
        return []
    out = []
    for r in rows[:MAX_ROWS]:
        out.append(row(r["fda_url"], short(D.d_of(r["decision_date"])),
                       f"{esc(D.name_of(r))}: {esc(D.PATH_LABEL[r['pathway']])}, "
                       f"{esc(D.decision_words(r['decision_code']).split(' (')[0].lower())}", external=True))
    years = sorted({r["decision_date"][:4] for r in rows}, reverse=True)
    links = " &middot; ".join(f'<a href="/devices/decisions/{y}">{y}</a>' for y in years
                              if os.path.isfile(os.path.join(site, "devices", "decisions", y, "index.html")))
    n = len(rows)
    head = f'<h2 id="devices">FDA device decisions ({n})</h2>'
    tail = (f'<p class="note">PMA approvals and De Novo grants the FDA\'s records list for this company'
            + (f"; by year: {links}" if links else "") + '. Each row links the FDA\'s own record.</p>')
    return [head] + out + [tail]


def block(tk, T, pages, today, by_tk, site):
    parts = earnings_rows(tk, T, pages, today) + device_rows(tk, by_tk, site)
    return (B + "".join(parts) + END) if parts else ""


def apply(doc, blk):
    if BLOCK.search(doc):
        return BLOCK.sub(lambda m: blk, doc, count=1)
    if not blk:
        return doc
    for a in ANCHORS:
        i = doc.find(a)
        if i >= 0:
            return doc[:i] + blk + doc[i:]
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--today", default="")
    a = ap.parse_args(argv)
    today = E.d_of(a.today) or E.eastern_today()
    T, pages = {}, set()
    if os.path.isfile(E.CACHE):
        _, T = E.load(E.CACHE)
        pages = {tk for tk, t in T.items() if E.has_page(t, today)
                 and os.path.isfile(os.path.join(a.site, "earnings", tk, "index.html"))}
    by_tk = collections.defaultdict(list)
    if os.path.isfile(D.CACHE):
        for r in D.load(D.CACHE)[1]:                    # newest first, approvals and grants only, as the pages show
            tk = D.ticker_of(r)
            if tk:
                by_tk[tk].append(r)
    root = os.path.join(a.site, "ticker")
    n = n_e = n_d = 0
    for tk in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        p = os.path.join(root, tk, "index.html")
        if not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8").read()
        blk = block(tk, T, pages, today, by_tk, a.site)
        new = apply(doc, blk)
        n_e += 'id="earnings"' in blk
        n_d += 'id="devices"' in blk
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n += 1
    print(f"ticker cross-links: {n} hub(s) changed; {n_e} link earnings dates, {n_d} list FDA device decisions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
