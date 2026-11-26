# -*- coding: utf-8 -*-
"""build_screener_rows.py -- server-render the screener's rows (SEO playbook B3).

The problem: /screener is 72KB but contains ZERO <tr> rows and zero links to ticker/event pages --
the table is built client-side from the data file, so Googlebot's initial HTML fetch sees an empty
shell. It is indexed on its title alone and passes NO link equity to the pages it displays, despite
being the site's highest-intent commercial page.

Fix (progressive enhancement): bake the first N rows into the HTML at build time with real anchors,
inside a <noscript>-friendly container that the existing JS replaces on load. Crawlers and no-JS
visitors get real content and real links; JS users get the full interactive table exactly as before.

Idempotent: the block is delimited and replaced on each run.

    python build_screener_rows.py [--rows 120] [--dry-run]
"""
import argparse, json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "screener", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
sys.path.insert(0, HERE)
try:
    from site_dates import eastern_today
    TODAY = eastern_today()
except Exception:  # noqa: BLE001
    TODAY = dt.date.today()
from site_windows import is_day, window_label, window_span  # noqa: E402
from readout_links import drug_page  # noqa: E402


def date_text(r):
    """Design red team 2026-11-18 (change 1): a month/quarter/year row is printed as its window ("Nov 2026", "Q4 2026"),
    never as the day it is stored under; an exact day stays that day. " (est.)" marks pdufa.bio's own estimates. One
    definition, shared with the interactive list (sync_screener_data.date_text), so the two cannot disagree."""
    from sync_screener_data import date_text as _dt
    return _dt(r)


def ends(r):
    """Last day of the row's window (its own day for a day row): an open window is still ahead."""
    return window_span(r)[1] or str(r.get("d") or "")[:10]
START, END = "<!--ssr-rows-->", "<!--/ssr-rows-->"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

    # ONLY render rows for entities the site actually knows as companies. The dataset also carries
    # conference codes in the ticker field (AASLD, ESMO, ESC, SITC, WCLC...), and emitting those as
    # /pdufa/<code> would manufacture phantom pages -- the ticker-fan-out failure the CI guard exists
    # to catch. A row qualifies only if it has a real /ticker/<T> hub on disk.
    known = {d for d in os.listdir(os.path.join(SITE, "ticker"))
             if os.path.isdir(os.path.join(SITE, "ticker", d))}

    def own_page(r):
        u = str(r.get("url") or "").split("#")[0].split("?")[0].rstrip("/")
        if re.match(r"^/(?:pdufa|fda-decision|adcomm|readout|readouts)/[A-Za-z0-9.\-]+$", u) and \
                os.path.exists(os.path.join(SITE, *u.strip("/").split("/"), "index.html")):
            return u
        return None

    def has_pdufa_page(t):
        return os.path.exists(os.path.join(SITE, "pdufa", t, "index.html"))

    fwd = [r for r in arr
           if ends(r) >= TODAY.isoformat() and r.get("st") not in ("Decided", "Withdrawn")
           and r.get("t") in known]
    fwd.sort(key=lambda r: (ends(r), 0 if is_day(r) else 1, str(r.get("t"))))   # window end, days first (change 1)
    dropped = sum(1 for r in arr
                  if ends(r) >= TODAY.isoformat() and r.get("st") not in ("Decided", "Withdrawn")
                  and r.get("t") and r.get("t") not in known)
    fwd = fwd[:a.rows]

    trs = []
    for r in fwd:
        t = r["t"]
        d = str(r.get("d") or "")[:10]
        typ = esc(r.get("type") or "")
        nm = esc(r.get("name") or "")[:52]
        ta = esc(r.get("ta") or "")
        dtxt = esc(date_text(r))
        # The row's own page when it has one (design red team 2026-11-18, change 4: the screener linked every
        # row, readouts included, to /pdufa/<T>, while the calendar linked the event's own page); otherwise a
        # PDUFA row links /pdufa/<T> when that page really exists, and anything else is plain text.
        #
        # 2026-11-26 (GSC): /screener drew 383 impressions at position 6.6 with no click, and the queries it ranked
        # for were drug names ("donidalorsen", "abcl635", "eyp-1901", "vadadustat"). Each of those has a /drug page,
        # but the readout rows here printed the name as plain text, so Google offered the 120-row table to a reader
        # who wanted one drug. A row with no page of its own now links its drug page when that page exists, resolved
        # exactly as /readouts resolves it (readout_links.drug_page: same slug as build_drug_pages, same-company
        # check, None when the page is not on disk). The workflow runs this again after build_drug_pages, so a link
        # written here is never to a page that build removed.
        own = own_page(r)
        dpage = None if own or (r.get("type") == "PDUFA" and has_pdufa_page(t)) else drug_page(r)
        if nm and own:
            drug_cell = f'<a href="{esc(own)}">{nm}</a>'
        elif nm and r.get("type") == "PDUFA" and has_pdufa_page(t):
            drug_cell = f'<a href="/pdufa/{t}">{nm}</a>'
        elif nm and dpage:
            drug_cell = f'<a href="{esc(dpage)}">{nm}</a>'
        else:
            drug_cell = nm or "n/a"
        trs.append(
            f'<tr><td><a href="/ticker/{t}">{t}</a></td>'
            f'<td>{dtxt}</td><td>{typ}</td>'
            f'<td>{drug_cell}</td><td>{ta}</td></tr>')

    block = (START +
             '<table id="ssr-table" style="width:100%;border-collapse:collapse;font-size:13.5px">'
             '<caption style="text-align:left;color:#9db3d4;font-size:12.5px;padding:6px 0">'
             f'Next {len(trs)} catalysts: server-rendered. Sorting and filtering load with JavaScript; '
             'this table is the same data without it.</caption>'
             '<thead><tr>'
             '<th style="text-align:left;padding:7px 6px;color:#f0c86a;font-size:11.5px;text-transform:uppercase">Ticker</th>'
             '<th style="text-align:left;padding:7px 6px;color:#f0c86a;font-size:11.5px;text-transform:uppercase">Date</th>'
             '<th style="text-align:left;padding:7px 6px;color:#f0c86a;font-size:11.5px;text-transform:uppercase">Type</th>'
             '<th style="text-align:left;padding:7px 6px;color:#f0c86a;font-size:11.5px;text-transform:uppercase">Drug</th>'
             '<th style="text-align:left;padding:7px 6px;color:#f0c86a;font-size:11.5px;text-transform:uppercase">Area</th>'
             '</tr></thead><tbody>' + "".join(trs) + "</tbody></table>" + END)

    html = open(PAGE, encoding="utf-8", errors="replace").read()
    if START in html and END in html:
        new = re.sub(re.escape(START) + ".*?" + re.escape(END), block, html, flags=re.S)
    else:
        # insert before the closing </main> (or </body> as fallback) so it renders in-page
        anchor = "</main>" if "</main>" in html else "</body>"
        new = html.replace(anchor, block + anchor, 1)

    links = new.count('href="/ticker/') + new.count('href="/pdufa/') + new.count('href="/drug/')
    print(f"screener: {len(trs)} server-rendered rows, {links} internal anchors on the page "
          f"(was 0 rows / 0 event links); dropped {dropped} non-company entries "
          f"(conference codes etc. with no /ticker hub)")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    open(PAGE, "w", encoding="utf-8").write(new)
    print("wrote screener/index.html")


if __name__ == "__main__":
    main()
