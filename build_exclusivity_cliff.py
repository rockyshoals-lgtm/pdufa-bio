# -*- coding: utf-8 -*-
"""build_exclusivity_cliff.py -- /patent-cliff/exclusivity from the Orange Book's exclusivity.txt (audit 4.3).

Regulatory exclusivity is a different, often EARLIER cliff than patent expiry: an NCE's five years, an
orphan drug's seven, a new indication's three, run from approval regardless of patents, and the FDA will
not approve (or for NCE, accept) certain generic or 505(b)(2) applications until they end. The Orange
Book publishes them in exclusivity.txt (Appl_Type~Appl_No~Product_No~Exclusivity_Code~Exclusivity_Date),
and /patent-cliff used them only folded into one "later of" date. This page lists every NDA exclusivity
expiring from today through 2031, joined to products.txt for the brand, ingredient and applicant: one
row per application, exclusivity code and date (product strengths sharing a code and date are one row).
Generic-applicant exclusivities (PC, CGT, on ANDAs) are a different thing and are left out.

Facts from the FDA's data files only; not a prediction of generic entry. RULE 1: dates are calendar dates.
    python build_exclusivity_cliff.py
"""
import collections
import datetime as dt
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402
from site_style import HUB_STYLE, FONTS_LINK  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
OB = os.path.join(HERE, "_orange_book")
OUT = os.path.join(SITE, "patent-cliff", "exclusivity", "index.html")
BASE = "https://www.pdufa.bio"
B, E = "<!--EXCL:BEGIN-->", "<!--EXCL:END-->"
MEANING = {"NCE": "new chemical entity", "ODE": "orphan drug", "PED": "pediatric", "I": "new indication",
           "M": "miscellaneous", "NPP": "new patient population", "NP": "new product", "GAIN": "qualified infectious "
           "disease product (GAIN)", "D": "new dosing schedule", "NS": "new strength"}
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html.escape(str(s or ""), quote=False)


def parse_date(s):
    return dt.datetime.strptime(s.strip(), "%b %d, %Y").date()


def tc(s):
    return " ".join(w if (len(w) <= 3 and w.isupper() and not w.isalpha()) else w.capitalize() for w in str(s).split())


def main():
    ex_p, pr_p = os.path.join(OB, "exclusivity.txt"), os.path.join(OB, "products.txt")
    if not (os.path.exists(ex_p) and os.path.exists(pr_p)):
        print("exclusivity cliff: Orange Book files missing; page keeps its previous build")
        return 0
    ap = os.path.join(OB, "_as_of.txt")
    asof = (dt.date.fromisoformat(io.open(ap, encoding="utf-8").read().split()[0]) if os.path.exists(ap)
            else dt.date.fromtimestamp(os.path.getmtime(ex_p)))
    prod = {}
    for line in io.open(pr_p, encoding="utf-8", errors="replace").read().splitlines()[1:]:
        f = line.split("~")
        if len(f) >= 14:
            prod[(f[5], f[6], f[7])] = {"ingredient": f[0], "trade": f[2], "applicant": f[13] or f[3]}
    today = eastern_today()
    end = dt.date(2031, 12, 31)
    agg = {}
    for line in io.open(ex_p, encoding="utf-8", errors="replace").read().splitlines()[1:]:
        f = line.split("~")
        if len(f) < 5 or f[0] != "N":
            continue
        try:
            d = parse_date(f[4])
        except ValueError:
            continue
        if not (today <= d <= end):
            continue
        p = prod.get((f[0], f[1], f[2]))
        if not p:
            continue
        code = f[3].strip()
        key = (f[1], code, d)
        agg.setdefault(key, {"appl": f[1], "code": code, "date": d, **p})
    rows = sorted(agg.values(), key=lambda r: (r["date"], r["trade"]))
    years = collections.OrderedDict()
    for r in rows:
        years.setdefault(r["date"].year, []).append(r)
    kinds = collections.Counter(re.split(r"[-*]", r["code"])[0] for r in rows)
    body = [f'<h1>Regulatory exclusivity cliff: {len(rows)} FDA exclusivities ending through 2031</h1>',
            f'<p><b>{len(rows)} FDA regulatory exclusivities on brand-name drugs (NDAs) end between '
            f'{today.strftime("%B")} {today.day}, {today.year} and December 31, 2031</b>, per the FDA Orange Book. '
            f'Exclusivity is separate from patents: it runs from approval (five years for a new chemical entity, '
            f'seven for an orphan drug, three for a new indication, six months added for pediatric studies) and '
            f'blocks the FDA from approving certain competing applications until it ends, whatever the patents say. '
            f'It is often an earlier date than the last patent. Orange Book data files dated '
            f'{asof.strftime("%B")} {asof.day}, {asof.year}.</p>',
            '<div style="background:rgba(240,200,106,.08);border:1px solid #6b5a2f;border-radius:10px;padding:12px 14px;'
            'margin:16px 0;font-size:13.5px;color:#e8d9a8"><b>An exclusivity ending is not a generic launch.</b> '
            'Patents, settlements and the time a generic needs for approval decide when a competitor actually '
            'reaches the market. This page lists the FDA&#x27;s exclusivity dates only. Not investment advice.</div>',
            '<p>By type: ' + "; ".join(f'{esc(MEANING.get(k, k))} ({esc(k)}): {n}' for k, n in kinds.most_common()) + '.</p>']
    for y, rs in years.items():
        body.append(f'<h2>{y} &middot; {len(rs)} exclusivit{"ies" if len(rs) != 1 else "y"}</h2>'
                    '<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>'
                    '<th style="text-align:left">Ends</th><th style="text-align:left">Brand (ingredient)</th>'
                    '<th style="text-align:left">Applicant</th><th style="text-align:left">Exclusivity</th>'
                    '<th style="text-align:left">NDA</th></tr>')
        for r in rs:
            base = re.split(r"[-*]", r["code"])[0]
            body.append(f'<tr><td style="padding:4px;white-space:nowrap">{MON[r["date"].month]} {r["date"].day}, {r["date"].year}</td>'
                        f'<td style="padding:4px">{esc(tc(r["trade"]))} ({esc(r["ingredient"].lower()[:60])})</td>'
                        f'<td style="padding:4px">{esc(tc(r["applicant"])[:40])}</td>'
                        f'<td style="padding:4px">{esc(r["code"])}{" (" + esc(MEANING[base]) + ")" if base in MEANING else ""}</td>'
                        f'<td style="padding:4px"><a href="https://www.accessdata.fda.gov/scripts/cder/ob/results_product.cfm?'
                        f'Appl_Type=N&amp;Appl_No={r["appl"]}" rel="noopener">{r["appl"]}</a></td></tr>')
        body.append("</table>")
    body.append('<p style="margin-top:18px"><a href="/patent-cliff">Patent cliff tracker (last patent or exclusivity) &rarr;</a></p>')
    title = f"FDA Exclusivity Expirations 2026-2031: {len(rows)} Brand-Drug Exclusivities | pdufa.bio"
    desc = (f"{len(rows)} FDA regulatory exclusivities on brand drugs end through 2031, from the Orange Book: NCE, "
            f"orphan, new indication and pediatric, with the date for each.")[:158]
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
           f'initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/patent-cliff/exclusivity"><meta name="robots" content="index,follow">'
           # audit 2026-10-04 UX P0: the stub stylesheet left the header unstyled on a phone. One owner now.
           f'{FONTS_LINK}<style>{HUB_STYLE}</style></head><body><div class="wrap">'
           f'<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>'
           f'<div style="font-size:12px;color:#94a9c9;margin:14px 0 4px"><a href="/">Home</a> &rsaquo; '
           f'<a href="/patent-cliff">Patent cliff</a> &rsaquo; Exclusivity</div>' + "".join(body) +
           '<div class="legal"></div></div></body></html>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(doc)
    hub = os.path.join(SITE, "patent-cliff", "index.html")
    if os.path.exists(hub):
        h = io.open(hub, encoding="utf-8", errors="replace").read()
        n2 = re.sub(re.escape(B) + r".*?" + re.escape(E), "", h, flags=re.S)
        blk = (f'{B}<p><b>A different, earlier cliff:</b> <a class="lit" href="/patent-cliff/exclusivity">{len(rows)} FDA '
               f'regulatory exclusivities</a> (new chemical entity, orphan drug, new indication, pediatric) end through '
               f'2031, separately from patents.</p>{E}')
        i = n2.find("<h2>By year</h2>")
        if i > 0:
            n2 = n2[:i] + blk + n2[i:]
            if n2 != h:
                io.open(hub, "w", encoding="utf-8").write(n2)
    print(f"/patent-cliff/exclusivity: {len(rows)} NDA exclusivities ending {today}..2031 "
          f"({', '.join(f'{k} {v}' for k, v in kinds.most_common(5))}); Orange Book files of {asof}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
