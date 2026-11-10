# -*- coding: utf-8 -*-
"""build_crl_months.py -- /crl/{year}/{month}: FDA complete response letters by month (audit 2026-11-09 §5 item 5).

Bing shows 172 impressions and 0 clicks for "fda complete response letter {october|november} 2026": a month-dated
question with no month page to answer it. Each page states two counts for the month, from two different records,
and never blends them:

  1. letters in the FDA's own release (openFDA transparency/crl, the corpus /crl lists), by letter date;
  2. Complete Response Letters among the PDUFA decisions pdufa.bio tracked that month (/decisions/crl rows).

The FDA releases letters in batches and late; a month with no released letters says so, with the release's own
last-updated date, rather than implying the FDA issued none. Counts only, no rates. Facts only, not investment advice.
Months built: every month from January 2025 through the current Eastern month, plus any month a letter is dated in.

    python build_crl_months.py [--dry-run]
"""
import argparse
import collections
import datetime as dt
import html
import io
import json
import os
import re
import sys
from urllib.parse import quote as _q

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402
from capture_crl_corpus import newest_corpus  # noqa: E402

BASE = "https://www.pdufa.bio"
MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
B, E = "<!--CRLMONTHS:BEGIN-->", "<!--CRLMONTHS:END-->"
esc = lambda s: html.escape(str(s or "").strip(), quote=True)


def corpus():
    p = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
    raw = json.load(io.open(p, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    upd = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    out, seen = [], set()
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        fn = str(r.get("file_name") or "").strip()
        if not m or not fn.lower().endswith(".pdf") or (fn, m.group(0)) in seen:
            continue           # same filter as build_crl_hub: no file yet, or a verbatim duplicate record
        seen.add((fn, m.group(0)))
        apps = r.get("application_number")
        out.append({"iso": f"{m.group(3)}-{m.group(1)}-{m.group(2)}", "company": str(r.get("company_name") or "").strip(),
                    "app": ", ".join(apps) if isinstance(apps, list) else str(apps or ""),
                    "status": str(r.get("approval_status") or "").strip(),
                    "url": "https://download.open.fda.gov/crl/" + _q(fn)})
    return out, upd


def tracked():
    """{'YYYY-MM': [(iso, ticker, drug, href)]} from /decisions/crl's published rows; and decided-row counts by month."""
    crl = collections.defaultdict(list)
    doc = io.open(os.path.join(SITE, "decisions", "crl", "index.html"), encoding="utf-8").read()
    for href, t, iso, drug in re.findall(r'<a class="row" href="(/fda-decision/[^"]+)"><div class="t">([A-Z0-9.]+) '
                                         r'(?:&middot;|·) (\d{4}-\d{2}-\d{2}).*?class="d">.*?</span>:\s*(.*?)</div></a>', doc, re.S):
        crl[iso[:7]].append((iso, t, html.unescape(re.sub(r"<[^>]+>", "", drug)).strip(), href))
    alld = collections.Counter(re.findall(r'<a class="row" href="/fda-decision/[^"]+"><div class="t">[A-Z0-9.]+ '
                                          r'(?:&middot;|·) (\d{4}-\d{2})-\d{2}',
                                          io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8").read()))
    return crl, alld


def page(y, m, letters, ours, n_dec, upd, prev_, next_):
    name = f"{MON[m - 1].capitalize()} {y}"
    n = len(letters)
    url = f"{BASE}/crl/{y}/{MON[m - 1]}"
    title = f"FDA Complete Response Letters {name}: {n} Released, {len(ours)} Tracked | pdufa.bio"
    first = (f"The FDA's public release of complete response letters holds {n} letter{'s' if n != 1 else ''} dated "
             f"{name}" + (f" (openFDA, last updated {upd})" if upd else "") + ". ")
    if n == 0:
        first += ("The FDA publishes these letters in batches after they are issued, so a month with none released "
                  "may still have letters the FDA has not yet published. ")
    first += (f"Of the {n_dec} FDA decision{'s' if n_dec != 1 else ''} on PDUFA goal dates pdufa.bio tracked in {name}, "
              f"{len(ours)} {'was a Complete Response Letter' if len(ours) == 1 else 'were Complete Response Letters'}.")
    desc = (f"FDA complete response letters {name}: {n} released by the FDA (openFDA), {len(ours)} among the PDUFA "
            f"decisions pdufa.bio tracked. Counts and sources only.")[:158]
    rows = "".join(f'<tr><td class="dt">{l["iso"]}</td><td>{esc(l["company"][:48])}</td><td>{esc(l["app"][:28])}</td>'
                   f'<td>{esc(l["status"])}</td><td><a href="{esc(l["url"])}" rel="noopener">letter (PDF)</a></td></tr>'
                   for l in sorted(letters, key=lambda x: x["iso"], reverse=True))
    trows = "".join(f'<tr><td class="dt">{iso}</td><td>{esc(t)}</td><td>{esc(drug[:60])}</td>'
                    f'<td><a href="{href}">decision page</a></td></tr>' for iso, t, drug, href in sorted(ours, reverse=True))
    nav = " &middot; ".join(x for x in (
        f'<a href="/crl/{prev_[0]}/{MON[prev_[1] - 1]}">&larr; {MON[prev_[1] - 1].capitalize()} {prev_[0]}</a>' if prev_ else "",
        f'<a href="/crl/{next_[0]}/{MON[next_[1] - 1]}">{MON[next_[1] - 1].capitalize()} {next_[0]} &rarr;</a>' if next_ else "",
        '<a href="/crl">all released letters</a>', '<a href="/decisions/crl">every CRL decision we tracked</a>') if x)
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "url": url, "mainEntity": [
        {"@type": "Question", "name": f"How many FDA complete response letters were issued in {name}?",
         "acceptedAnswer": {"@type": "Answer", "text": first}}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "CRL letters", "item": f"{BASE}/crl"},
        {"@type": "ListItem", "position": 2, "name": name, "item": url}]}
    css = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,"
           "BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;"
           "text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:900px;margin:0 auto;padding:22px 18px 60px}"
           ".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;"
           "padding-bottom:12px}.brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav a{color:#a7bcd9;"
           "font-size:13px;margin-left:14px}h1{font-size:26px;line-height:1.2;margin:10px 0 8px}h2{font-size:17px;"
           "color:#e3ba5e;margin:24px 0 8px}.sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:76ch}"
           "table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;color:#e3ba5e;font-size:11.5px;"
           "text-transform:uppercase;letter-spacing:.4px;padding:7px 6px;border-bottom:1px solid #294d80}td{padding:7px 6px;"
           "border-bottom:1px solid #14263f;color:#a7bcd9;vertical-align:top}td.dt{color:#f2f6fc;white-space:nowrap}")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title>'
            f'<meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">'
            f'<meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="website">'
            f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{url}">'
            f'<meta property="og:title" content="{esc(title.split(" | ")[0])}"><meta property="og:description" '
            f'content="{esc(desc)}"><script type="application/ld+json">{json.dumps(crumbs)}</script>'
            f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script><style>{css}</style></head>'
            f'<body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">'
            f'<!--NAVC:BEGIN--><!--NAVC:END--></div></div>'
            f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px"><a href="/" style="color:#94a9c9">Home</a> &rsaquo; '
            f'<a href="/crl" style="color:#94a9c9">CRL letters</a> &rsaquo; {name}</div>'
            f'<h1>FDA complete response letters, {name}</h1>'
            f'<!--CRLLEDE:BEGIN--><p class="sub" style="color:#cfe0f5">{esc(first)}</p><!--CRLLEDE:END-->'
            f'<h2>Released by the FDA, dated {name} &middot; {n}</h2>'
            + (f'<table><tr><th>Letter date</th><th>Company</th><th>Application</th><th>openFDA status</th><th>Letter</th></tr>'
               f'{rows}</table>' if n else f'<div class="sub">None in the release as of its last update{(" (" + esc(upd) + ")") if upd else ""}.</div>')
            + f'<h2>Complete Response Letters among decisions pdufa.bio tracked &middot; {len(ours)}</h2>'
            + (f'<table><tr><th>FDA action</th><th>Ticker</th><th>Drug</th><th>Source</th></tr>{trows}</table>' if ours
               else f'<div class="sub">None: the {n_dec} tracked decision{"s" if n_dec != 1 else ""} this month '
                    f'{"was an approval" if n_dec == 1 else "were approvals" if n_dec else "(no tracked decisions)"}.</div>')
            + f'<div class="sub" style="font-size:13px;margin-top:18px">A Complete Response Letter is the FDA&#x27;s notice that it '
              f'will not approve an application in its current form; it is not a permanent rejection, and the sponsor can '
              f'resubmit. The two counts come from different records and are not added together. {nav}</div>'
            + '</div></body></html>')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    letters, upd = corpus()
    ours, alld = tracked()
    by = collections.defaultdict(list)
    for l in letters:
        by[l["iso"][:7]].append(l)
    td = eastern_today()
    months, y, m = [], 2025, 1
    while (y, m) <= (td.year, td.month):
        months.append((y, m)); m += 1
        if m == 13:
            y, m = y + 1, 1
    months = sorted(set(months) | {(int(k[:4]), int(k[5:])) for k in by if k >= "2025-01"})
    written = []
    for i, (y, m) in enumerate(months):
        k = f"{y}-{m:02d}"
        doc = page(y, m, by.get(k, []), ours.get(k, []), alld.get(k, 0), upd,
                   months[i - 1] if i else None, months[i + 1] if i + 1 < len(months) else None)
        p = os.path.join(SITE, "crl", str(y), MON[m - 1], "index.html")
        written.append((y, m, len(by.get(k, [])), len(ours.get(k, []))))
        if not a.dry_run:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="utf-8").write(doc)
    # month index on /crl
    hub = os.path.join(SITE, "crl", "index.html")
    h = io.open(hub, encoding="utf-8").read()
    chips = " ".join(f'<a href="/crl/{y}/{MON[m - 1]}" style="display:inline-block;padding:4px 9px;margin:2px;'
                     f'border:1px solid #1a3358;border-radius:7px;font-size:12.5px">{MON[m - 1][:3].capitalize()} {y} '
                     f'<b>{n}</b>{(" / " + str(o)) if o else ""}</a>' for y, m, n, o in reversed(written))
    blk = (f'{B}<h2>By month</h2><div class="sub" style="font-size:13px">Letters in the FDA release dated each month '
           f'(after the slash: CRLs among the decisions pdufa.bio tracked that month).</div><div>{chips}</div>{E}')
    h = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: blk, h, flags=re.S) if B in h else \
        h.replace("<h2>What the FDA has released", blk + "<h2>What the FDA has released", 1)
    if not a.dry_run:
        io.open(hub, "w", encoding="utf-8").write(h)
    for y, m, n, o in written[-4:]:
        print(f"  /crl/{y}/{MON[m - 1]:9s} released {n}, tracked CRLs {o}")
    print(f"crl month pages: {len(written)} (release last updated {upd})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
