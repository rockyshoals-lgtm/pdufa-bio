# -*- coding: utf-8 -*-
"""build_calendar_year_hub.py -- /calendar/{next year}: every PDUFA goal date already set beyond /calendar's window.

Audit 2026-11-05 (UX + search). /calendar's live grid ends at December 2026 and had no link to any 2027 month, while
35 sourced 2027 goal dates sat on month pages reachable only by paging through December. The homepage said "tracks 25
upcoming FDA decision dates". A reader -- or a search engine, or an answer engine asked "pdufa dates 2027" -- had no
entry point to more than half the forward calendar.

This writes, for every year after /calendar's last month heading that has month pages:
  /calendar/{YEAR}           a year hub: one quotable sentence, the rows grouped by month (copied from the month
                             pages, so it can never disagree with them), month links
  /calendar  AHEAD block     "Already set for {YEAR}: N FDA goal dates" with month chips, before the company index
Rows are read from the published month pages (same rule as every other count on the site). Idempotent; a page is
rewritten only when its content changes.

    python build_calendar_year_hub.py [--dry-run]
"""
import argparse
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
CAL = os.path.join(SITE, "calendar")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
B, E = "<!--AHEAD:BEGIN-->", "<!--AHEAD:END-->"
ROW = re.compile(r'<a class="row"[^>]*>.*?</a>', re.S)


def rows_on(p, today):
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    g = doc.find('<div class="grid"')
    doc = doc[g:doc.find('<div class="callout">', g)] if g >= 0 else ""
    out = []
    for r in ROW.findall(doc):
        d = re.search(r"(\d{4}-\d{2}-\d{2})", r)
        if "data-dec" in r or (d and d.group(1) < today):
            continue
        out.append((d.group(1) if d else "", r))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = eastern_today().isoformat()
    main_p = os.path.join(CAL, "index.html")
    main_doc = io.open(main_p, encoding="utf-8").read()
    heads = re.findall(r'<div class="mhead">[A-Za-z]+ (\d{4})</div>', main_doc)
    cal_year = max(heads) if heads else today[:4]
    years = sorted({p.split(os.sep)[-3] for p in glob.glob(os.path.join(CAL, "20[0-9][0-9]", "*", "index.html"))
                    if p.split(os.sep)[-2] in MONTHS and p.split(os.sep)[-3] > cal_year})
    ahead_html = ""
    for y in years:
        months = []
        for i, m in enumerate(MONTHS):
            p = os.path.join(CAL, y, m, "index.html")
            if os.path.exists(p):
                months.append((m, rows_on(p, today)))
        n = sum(len(r) for _, r in months)
        if not n:
            continue
        shell = io.open(os.path.join(CAL, y, months[0][0], "index.html"), encoding="utf-8").read()
        mname0 = f"{months[0][0].capitalize()} {y}"
        per = ", ".join(f"{len(r)} in {m.capitalize()}" for m, r in months if r)
        first = next((r for _, rr in months for r in rr), None)
        lede = (f"pdufa.bio lists {n} FDA PDUFA goal date{'s' if n != 1 else ''} already set for {y}, each taken from "
                f"the sponsor's own SEC filing or press release: {per}. Dates move when the FDA extends a review; "
                f"every row links the event page that records the source and any change.")
        title = f"PDUFA Dates {y}: {n} FDA Decision Dates Already Set | pdufa.bio"
        desc = (f"{n} FDA PDUFA goal dates already announced for {y}, by month, each with company, ticker, drug and "
                f"the sponsor filing that set it. Updated daily.")
        body = []
        for m, rr in months:
            if not rr:
                continue
            body.append(f'<h2 style="font-size:17px;margin:22px 0 6px"><a href="/calendar/{y}/{m}">{m.capitalize()} {y}</a>'
                        f' <span style="color:var(--mut2);font-size:13px;font-weight:400">{len(rr)} date'
                        f'{"s" if len(rr) != 1 else ""}</span></h2><div class="grid">' + "".join(r for _, r in rr) + "</div>")
        doc = shell
        doc = re.sub(r"<title>[^<]*</title>", f"<title>{html.escape(title, quote=False)}</title>", doc, count=1)
        for attr, name, val in (("name", "description", desc), ("property", "og:title", title),
                                ("property", "og:description", desc), ("name", "twitter:title", title),
                                ("name", "twitter:description", desc)):
            doc = re.sub(r'(<meta ' + attr + r'="' + re.escape(name) + r'" content=")[^"]*(")',
                         lambda mm: mm.group(1) + html.escape(val, quote=True) + mm.group(2), doc, count=1)
        url = f"https://www.pdufa.bio/calendar/{y}"
        doc = re.sub(r'(<link rel="canonical" href=")[^"]*(")', rf"\g<1>{url}\g<2>", doc, count=1)
        doc = re.sub(r'(<meta property="og:url" content=")[^"]*(")', rf"\g<1>{url}\g<2>", doc, count=1)
        doc = re.sub(r'<script type="application/ld\+json">.*?</script>', "", doc, flags=re.S)
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pdufa.bio/"},
                {"@type": "ListItem", "position": 2, "name": "Calendar", "item": "https://www.pdufa.bio/calendar"},
                {"@type": "ListItem", "position": 3, "name": f"{y} PDUFA dates", "item": url}]},
            {"@type": "CollectionPage", "name": title.split(" | ")[0], "url": url, "description": desc,
             "hasPart": [{"@type": "WebPage", "name": f"{m.capitalize()} {y} PDUFA dates",
                          "url": f"https://www.pdufa.bio/calendar/{y}/{m}"} for m, rr in months if rr]}]}
        doc = doc.replace("</head>", f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>', 1)
        doc = re.sub(r'<div class="bc">.*?</div>', f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/calendar">Calendar</a> '
                     f'&rsaquo; {y}</div>', doc, count=1, flags=re.S)
        doc = re.sub(r"<h1>.*?</h1>", f'<h1>{y} <span class="g">FDA PDUFA dates</span></h1>', doc, count=1, flags=re.S)
        doc = re.sub(r'<div class="sub">.*?</div>', f'<div class="sub">{html.escape(lede)}</div>', doc, count=1, flags=re.S)
        doc = re.sub(r'<div class="pn">.*?</div>', f'<div class="pn"><a href="/calendar">&larr; {cal_year} calendar</a>'
                     f'<a href="/calendar/{y}/{months[0][0]}">{mname0} &rarr;</a></div>', doc, count=1, flags=re.S)
        doc = re.sub(r'<span class="count">[^<]*</span>', f'<span class="count">{n} PDUFA dates</span>', doc, count=1)
        g = doc.index('<div class="grid" style="margin-top:12px">')
        ge = doc.index('</div><div class="callout">', g) + len("</div>")
        doc = doc[:g] + "".join(body) + doc[ge:]
        tks = sorted({re.sub(r"\s.*", "", tk) for _, rr in months for _, r in rr
                      for tk in re.findall(r'<div class="t">([A-Z][A-Z./ ]{0,20}?)\s*(?:&middot;|·)', r)
                      for tk in tk.split(" / ")})
        chip = ('<a href="/ticker/{0}" style="display:inline-block;padding:3px 8px;margin:2px;border:1px solid '
                'var(--line);border-radius:7px;font-size:12.5px;text-decoration:none" class="lit">{0}</a>')
        doc = re.sub(r"(<!--TICKERIDX:BEGIN-->.*?<div>)(?:<a href=\"/ticker/[^\"]+\"[^>]*>[^<]*</a>)*(</div>)",
                     lambda mm: mm.group(1) + "".join(chip.format(t) for t in tks) + mm.group(2), doc, count=1, flags=re.S)
        # the month page's FAQ block speaks about one month; the hub has its own lede instead
        doc = re.sub(r"<!--FAQ:BEGIN-->.*?<!--FAQ:END-->", "", doc, flags=re.S)
        out = os.path.join(CAL, y, "index.html")
        old = io.open(out, encoding="utf-8").read() if os.path.exists(out) else ""
        if re.sub(r"<!--FRESH:BEGIN-->.*?<!--FRESH:END-->", "", old, flags=re.S) != \
                re.sub(r"<!--FRESH:BEGIN-->.*?<!--FRESH:END-->", "", doc, flags=re.S) and not a.dry_run:
            io.open(out, "w", encoding="utf-8").write(doc)
            print(f"  /calendar/{y}: {n} dates ({per})")
        chips = "".join(f'<a href="/calendar/{y}/{m}" style="display:inline-block;padding:5px 10px;margin:3px;border:1px solid '
                        f'var(--line);border-radius:8px;font-size:13px;text-decoration:none" class="lit">{m.capitalize()} '
                        f'{y} <b>{len(rr)}</b></a>' for m, rr in months if rr)
        ahead_html += (f'<section style="margin:26px 0 8px;padding-top:14px;border-top:1px solid var(--line)">'
                       f'<h2 style="font-size:16px;margin:0 0 4px"><a href="/calendar/{y}">Already set for {y}: {n} FDA goal '
                       f'date{"s" if n != 1 else ""}</a></h2><div style="font-size:12.5px;color:var(--mut2);line-height:1.6;'
                       f'margin:0 0 8px">Sponsors have announced these {y} PDUFA dates; each month page lists them with '
                       f'their sources.</div><div>{chips}</div></section>')
    block = B + ahead_html + E
    new = main_doc
    if B in new:
        new = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: block, new, flags=re.S)
    elif "<!--TICKERIDX:BEGIN-->" in new:
        new = new.replace("<!--TICKERIDX:BEGIN-->", block + "<!--TICKERIDX:BEGIN-->", 1)
    if new != main_doc and not a.dry_run:
        io.open(main_p, "w", encoding="utf-8").write(new)
        print("  /calendar: AHEAD block written")
    print(f"year hubs: {', '.join(years) or 'none'}" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
