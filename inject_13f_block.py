# -*- coding: utf-8 -*-
"""inject_13f_block.py -- the specialist-fund 13F block on decision and drug pages (audit 2026-10-03, 4.1).

Renders _13f_specialists.json (sync_13f_specialists.py: each fund's latest 13F-HR read from EDGAR, CIK
checked against the filer name) as one paragraph per ticker, between markers, before the page footer:

  Specialist biotech funds, latest 13F (quarter ended June 30, 2026): Baker Bros. Advisors reported
  71,034,567 shares of INCY ($3.49 billion at quarter end); ... Filed with the SEC August 14, 2026.

Only funds that reported a long position are named; nothing is said about a fund that did not (a 13F
cannot show a short or a sale after the quarter). Pages whose tickers no tracked fund holds get no block.
Facts from public filings only; not investment advice. Idempotent.

    python inject_13f_block.py
"""
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--F13:BEGIN-->", "<!--F13:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def money(v):
    if v >= 1e9:
        return f"${v / 1e9:.2f} billion"
    if v >= 1e6:
        return f"${v / 1e6:.1f} million"
    return f"${v:,.0f}"


COMMON = re.compile(r"\b(COM|COMMON|ORD|ORDINARY|ADR|ADS|CL ?A|CLASS A|SHS|STK)\b")
NOT_COMMON = re.compile(r"\b(NOTE|NT|WARRANT|WT|DEBT|CONV|PFD|PREF|UNIT|RT|RIGHT)\b")


def is_common_shares(h):
    """Only a row typed SH with a common-stock class is ever rendered as shares (audit 2026-10-04 UX P1)."""
    cls = str(h.get("title_of_class") or "").upper()
    return str(h.get("type") or "").upper() == "SH" and bool(COMMON.search(cls)) and not NOT_COMMON.search(cls)


def para(tk, holds):
    """A headed table: fund / shares / value, the filing linked per row, the caveat beneath."""
    holds = sorted((h for h in holds if is_common_shares(h)), key=lambda h: -h["shares"])
    if not holds:
        return ""
    periods = sorted({h["period"] for h in holds})
    per = " / ".join(pretty(p) for p in periods)
    rows = "".join(
        f'<tr><td style="padding:5px 4px"><a href="{html.escape(h["url"], quote=True)}" rel="noopener" style="color:#e3ba5e">'
        f'{html.escape(h["fund"])}</a></td><td style="padding:5px 4px;text-align:right">{h["shares"]:,}</td>'
        f'<td style="padding:5px 4px;text-align:right">{money(h["value_usd"])}</td>'
        f'<td style="padding:5px 4px;color:#94a9c9">filed {pretty(h["filed"])}</td></tr>' for h in holds)
    return (f'<h2 style="font-size:16px;margin:22px 0 6px">Specialist biotech funds holding {html.escape(tk)}, 13F for the '
            f'quarter ended {html.escape(per)}</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>'
            f'<th style="text-align:left;color:#e3ba5e;font-size:12px;padding:4px">Fund</th>'
            f'<th style="text-align:right;color:#e3ba5e;font-size:12px;padding:4px">Shares</th>'
            f'<th style="text-align:right;color:#e3ba5e;font-size:12px;padding:4px">Value at quarter end</th>'
            f'<th style="text-align:left;color:#e3ba5e;font-size:12px;padding:4px">Filing</th></tr>{rows}</table>'
            f'<p class="sub" style="font-size:12.5px;margin:6px 0 0">13F reports list long positions in common stock at quarter '
            f'end, are due 45 days later, and show no short positions or later trades. Notes, warrants and other '
            f'instruments are not counted as shares.</p>')


def para_legacy(tk, holds):
    holds = sorted(holds, key=lambda h: -h["shares"])
    periods = sorted({h["period"] for h in holds})
    filed = sorted({h["filed"] for h in holds})
    parts = [f'<a href="{html.escape(h["url"], quote=True)}" rel="noopener" style="color:#e3ba5e">'
             f'{html.escape(h["fund"])}</a> reported {h["shares"]:,} shares of {html.escape(tk)} '
             f'({money(h["value_usd"])} at quarter end)' for h in holds]
    per = " / ".join(pretty(p) for p in periods)
    fil = " / ".join(pretty(f) for f in filed)
    return (f'<p class="sub" style="font-size:13px;margin:8px 0"><b>Specialist biotech funds, latest 13F '
            f'(quarter ended {per}):</b> ' + "; ".join(parts) + f'. Filed with the SEC {fil}. 13F reports list long '
            f'positions at quarter end, are due 45 days later, and show no short positions or later trades.</p>')


def main():
    p13 = os.path.join(HERE, "_13f_specialists.json")
    if not os.path.exists(p13):
        print("13F block: no _13f_specialists.json; nothing rendered")
        return 0
    bt = json.load(io.open(p13, encoding="utf-8")).get("by_ticker", {})
    n = nb = 0
    pages = sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))) + \
        sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html")))
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        slug = os.path.basename(os.path.dirname(p))
        if "/fda-decision/" in p.replace("\\", "/"):
            m = re.match(r"([A-Z]{1,6})-\d{4}-\d{2}-\d{2}$", slug)
            tks = [m.group(1)] if m else []
        else:
            tks = []
            for t in re.findall(r'href="/ticker/([A-Z]{1,6})"', new):
                if t not in tks:
                    tks.append(t)
        paras = [x for x in (para(t, bt[t]) for t in tks[:4] if bt.get(t)) if x]
        if paras:
            blk = B + "".join(paras) + E
            # above the FAQ, under its own heading (audit 2026-10-04: it sat as a paragraph under the footer line)
            i = next((new.index(x) for x in ("<!--DFAQ:BEGIN-->", "<!--HUBFAQ:BEGIN-->", '<h2>Questions</h2>',
                                             '<div class="legal"', "<footer") if x in new), None)
            if i is not None:
                new = new[:i] + blk + new[i:]
                nb += 1
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n += 1
    print(f"13F block: {nb} page(s) carry it, {n} page(s) changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
