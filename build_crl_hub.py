# -*- coding: utf-8 -*-
"""build_crl_hub.py -- /crl: the FDA Complete Response Letter corpus, browsable.

Asked in three consecutive audits (09-01, 09-02c, 09-02d): we hold 458 FDA CRLs from
the agency's transparency program and had no page for them. This builds /crl from
CRL_corpus_openFDA_2026-08-29.json: every letter grouped by year, newest first, each
linking FDA's own hosted PDF -- and our decision page where one exists.

Counts, never rates (the corpus README discipline): letters released for pre-2024
applications exist BECAUSE those drugs were later approved (approved-by-construction),
and 2024+ letters are right-censored -- computing an "approval rate after a CRL" from
this corpus would be wrong in both directions, so the page states counts and says why.

Rebuilt daily from the corpus file; refresh the corpus and the page follows.
"""
import collections
import datetime as dt
import html as _html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CORPUS = os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
BASE = "https://www.pdufa.bio"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def esc(s):
    return _html.escape(str(s or "").strip())


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    rows = []
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        fn = str(r.get("file_name") or "").strip()
        if not m or not re.match(r"^[\w.\-]+\.pdf$", fn):
            continue
        apps = r.get("application_number")
        rows.append({
            "iso": f"{m.group(3)}-{m.group(1)}-{m.group(2)}",
            "year": m.group(3),
            "company": str(r.get("company_name") or "").strip(),
            "app": ", ".join(apps) if isinstance(apps, list) else str(apps or ""),
            "status": str(r.get("approval_status") or "").strip(),
            "url": f"https://download.open.fda.gov/crl/{fn}",
        })
    rows.sort(key=lambda x: x["iso"], reverse=True)
    by_year = collections.OrderedDict()
    for r in rows:
        by_year.setdefault(r["year"], []).append(r)

    # our decision pages that already cite a specific letter (link_crl_letters cards)
    ours = {}
    import glob
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        mm = re.search(r'href="https://download\.open\.fda\.gov/crl/([\w.\-]+\.pdf)"',
                       doc)
        if mm:
            ours[mm.group(1)] = "/" + os.path.relpath(
                os.path.dirname(p), SITE).replace("\\", "/")

    n = len(rows)
    n24 = sum(1 for r in rows if r["year"] >= "2024")
    today = dt.date.today()
    title = (f"FDA Complete Response Letters: {n} Released CRLs, Searchable by Year "
             f"| pdufa.bio")
    desc = (f"{n} FDA Complete Response Letters from the agency's transparency "
            f"program, by year, each linking the original PDF on FDA's servers. "
            f"{n24} are from 2024 or later.")

    qa = [
        ("What is a Complete Response Letter?",
         "A Complete Response Letter (CRL) is the FDA's formal notice that it will not "
         "approve a drug application in its current form. It lists the deficiencies "
         "the sponsor must address; it is not a permanent rejection, and many drugs "
         "are approved after resubmission."),
        ("How many FDA Complete Response Letters are published here?",
         f"{n} letters, released by the FDA under its CRL transparency program and "
         f"hosted on FDA's own servers. {n24} were issued in 2024 or later; the rest "
         f"go back as far as 2002."),
        ("Why does this page not show an approval rate after a CRL?",
         "Because this corpus cannot answer that question honestly. Letters for "
         "pre-2024 applications were released because those drugs were LATER APPROVED, "
         "so nearly all of them precede an approval by construction. Letters from 2024 "
         "onward are too recent for many outcomes to exist yet. Counts are stated; "
         "rates from this data would mislead in both directions."),
    ]
    faq_ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "url": f"{BASE}/crl",
         "mainEntity": [{"@type": "Question", "name": q,
                         "acceptedAnswer": {"@type": "Answer", "text": ans}}
                        for q, ans in qa]}, separators=(",", ":")) + "</script>")

    CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;"
           "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
           "Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;text-decoration:none}"
           "a:hover{text-decoration:underline}.wrap{max-width:900px;margin:0 auto;"
           "padding:22px 18px 60px}.top{display:flex;align-items:center;"
           "justify-content:space-between;border-bottom:1px solid #1a3358;"
           "padding-bottom:12px}.brand{font-size:19px;font-weight:800}"
           ".brand b{color:#e3ba5e}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}"
           "h1{font-size:27px;line-height:1.18;margin:10px 0 6px}h1 .g{color:#e3ba5e}"
           "h2{font-size:18px;color:#e3ba5e;margin:26px 0 8px}"
           ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:76ch}"
           "table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px}"
           "th{text-align:left;color:#e3ba5e;font-size:11.5px;text-transform:uppercase;"
           "letter-spacing:.4px;padding:7px 6px;border-bottom:1px solid #294d80}"
           "td{padding:7px 6px;border-bottom:1px solid #14263f;color:#a7bcd9;"
           "vertical-align:top}td.dt{color:#f2f6fc;white-space:nowrap}"
           "footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;"
           "font-size:11.5px;color:#94a9c9;line-height:1.6}")

    NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
           '<div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>')

    body = [f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px">'
            f'<a href="/" style="color:#94a9c9">Home</a> &rsaquo; '
            f'<a href="/decisions" style="color:#94a9c9">Decisions</a> &rsaquo; '
            f'CRL letters</div>'
            f'<h1>FDA Complete Response Letters: <span class="g">{n} released '
            f'CRLs</span></h1>'
            f'<div class="sub">The FDA releases Complete Response Letters under its '
            f'CRL transparency program. This page lists all {n} released letters, '
            f'newest first, each linking the original PDF on FDA&#x27;s servers. '
            f'{n24} letters are from 2024 or later; the archive reaches back to 2002. '
            f'Where a letter matches a decision this site tracked, the decision page '
            f'(with the run-up chart and outcome) is linked beside it. This page '
            f'states counts, never approval rates; the FAQ below explains why a rate '
            f'from this data would mislead.</div>']

    for yr, yrows in by_year.items():
        body.append(f'<h2>{yr} &middot; {len(yrows)} letter'
                    f'{"s" if len(yrows) != 1 else ""}</h2>'
                    '<table><tr><th>Date</th><th>Company</th><th>Application</th>'
                    '<th>Letter</th><th>On this site</th></tr>')
        for r in yrows:
            d = dt.date.fromisoformat(r["iso"])
            our = ours.get(r["url"].rsplit("/", 1)[1])
            body.append(
                f'<tr><td class="dt">{MON[d.month][:3]} {d.day}, {d.year}</td>'
                f'<td>{esc(r["company"][:44])}</td><td>{esc(r["app"][:28])}</td>'
                f'<td><a href="{esc(r["url"])}" rel="noopener">letter (PDF)</a></td>'
                f'<td>' + (f'<a href="{our}">decision page</a>' if our else "&mdash;")
                + '</td></tr>')
        body.append("</table>")

    body.append('<h2>Questions</h2>')
    for q, ans in qa:
        body.append(f'<p><b style="color:#f2f6fc">{esc(q)}</b><br>'
                    f'<span style="color:#a7bcd9">{esc(ans)}</span></p>')
    body.append('<p><a href="/decisions/crl">CRL decisions tracked by this site</a> '
                '&middot; <a href="/decisions">the full decisions archive</a> &middot; '
                '<a href="/learn/what-is-a-pdufa-date">what a PDUFA date is</a></p>')

    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,'
           f'viewport-fit=cover"><title>{esc(title)}</title>'
           f'<meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/crl">'
           f'<meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d">'
           f'<meta property="og:type" content="website">'
           f'<meta property="og:site_name" content="pdufa.bio">'
           f'<meta property="og:url" content="{BASE}/crl">'
           f'<meta property="og:title" content="{esc(title)}">'
           f'<meta property="og:description" content="{esc(desc)}">{faq_ld}'
           f'<style>{CSS}</style></head><body><div class="wrap">{NAV}'
           + "".join(body) + "</div></body></html>")

    out = os.path.join(SITE, "crl", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/crl: {n} letters across {len(by_year)} years; {len(ours)} letter(s) "
          f"cross-linked to our decision pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
