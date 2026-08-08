# -*- coding: utf-8 -*-
"""build_year_archive.py -- historical-year calendar pages, for the years we can actually stand behind.

GSC shows 13 impressions on "pdufa dates 2024" -- proven demand for historical years, uncontested,
and evergreen in a way a live calendar is not. The audit asked for /calendar/2024 and
/calendar/2025.

Only 2025 ships. The decisions archive begins January 2025; we hold no 2024 decisions with source
documents, and a 2024 page built from anything less would be the exact fabrication this site exists
to avoid. When a sourced 2024 archive exists, this script will pick it up automatically -- it
builds one page per year found in the archive, whatever years those are.

Everything on the page is lifted from the decisions archive rows, so it can never disagree with
/decisions. Written only when content changes, so it does not churn lastmod.

    python build_year_archive.py [--dry-run]
"""
import argparse, datetime as dt, html, os, re, sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

ROW = re.compile(
    r'<a class="row" href="/fda-decision/([A-Z]{1,6})-(\d{4})-(\d{2})-(\d{2})"[^>]*>(.*?)</a>', re.S)

SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
:root{{--bg:#0b1017;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#dfe9f7;
font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}}
.wrap{{max-width:880px;margin:0 auto;padding:18px 16px 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}
.brand{{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;
text-decoration:none}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}}
h1{{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}}
h2{{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px}}
.row{{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:11px 0;
border-top:1px solid var(--line);color:inherit;text-decoration:none}}
.row:hover{{background:#141d2d}}
.t{{font-weight:600}}.d{{color:var(--mut2);font-size:13.5px}}
.ok{{color:#46d17f}}.bad{{color:#ff8f6b}}
.legal{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);
font-size:12px;line-height:1.7}}
</style></head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>
<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>
<a href="/readouts">Readouts</a></div></div>
<h1>{h1}</h1>
{body}
<div class="legal">Facts and dates only; not investment advice. Verify against primary FDA, SEC
and company filings. pdufa.bio is not affiliated with the FDA.</div>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    darch = os.path.join(SITE, "decisions", "index.html")
    if not os.path.exists(darch):
        print("no decisions archive; nothing to build"); return 0
    dh = open(darch, encoding="utf-8", errors="replace").read()

    this_year = dt.datetime.now(dt.timezone.utc).year
    years = defaultdict(list)
    for tk, y, m, d, frag in ROW.findall(dh):
        if int(y) >= this_year:
            continue                     # the live calendar owns the current year
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))).strip()
        outcome = ("Approved" if re.search(r"\bapproved\b", txt, re.I)
                   else "CRL" if re.search(r"\bcrl\b|complete response", txt, re.I) else "")
        body = re.split(r"(?:Approved|CRL|Complete Response Letter)\s*:?\s*", txt, maxsplit=1)
        drug = body[1].strip(" :") if len(body) > 1 else ""
        years[y].append((f"{y}-{m}-{d}", tk, outcome, drug))

    built = 0
    for y, evs in sorted(years.items()):
        evs.sort()
        ap_n = sum(1 for e in evs if e[2] == "Approved")
        crl_n = sum(1 for e in evs if e[2] == "CRL")

        bymonth = defaultdict(list)
        for date, tk, outcome, drug in evs:
            bymonth[int(date[5:7])].append((date, tk, outcome, drug))

        sect = []
        for m in sorted(bymonth):
            rows_h = "".join(
                f'<a class="row" href="/fda-decision/{tk}-{date}">'
                f'<span class="t">{tk} &middot; {date}'
                + (f' <span class="ok">&#10003; Approved</span>' if oc == "Approved"
                   else f' <span class="bad">CRL</span>' if oc == "CRL" else "")
                + f'</span><span class="d">{html.escape(drug[:90])}</span></a>'
                for date, tk, oc, drug in bymonth[m])
            sect.append(f"<h2>{MONTHS[m - 1]} {y}</h2>" + rows_h)

        lede = (f"This page lists all {len(evs)} FDA decisions from {y} in our archive: "
                f"{ap_n} approvals and {crl_n} Complete Response Letters. Every decision links "
                f"its own page with the source document and the share-price reaction we measured.")
        title = f"{y} FDA PDUFA Calendar &amp; Decisions: {len(evs)} On Record | pdufa.bio"
        desc = (f"The {y} FDA decision archive: {len(evs)} decisions, {ap_n} approvals, "
                f"{crl_n} CRLs, each with its source document and measured stock reaction.")[:158]

        page = SHELL.format(title=title, desc=html.escape(desc, quote=True),
                            canon=f"{BASE}/calendar/{y}",
                            h1=f"{y} FDA decisions",
                            body=(f'<p style="color:var(--mut2);max-width:74ch">'
                                  f"{html.escape(lede)}</p>" + "".join(sect)))

        out = os.path.join(SITE, "calendar", y, "index.html")
        old = open(out, encoding="utf-8", errors="replace").read() if os.path.exists(out) else ""
        if page != old and not a.dry_run:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(page)
        built += 1
        print(f"  /calendar/{y}: {len(evs)} decisions ({ap_n} approved, {crl_n} CRL)")

    if not years:
        print("no completed years in the archive yet")
    print(f"{built} year page(s)" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
