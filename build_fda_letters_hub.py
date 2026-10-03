# -*- coding: utf-8 -*-
"""build_fda_letters_hub.py -- /fda-approval-letters: the FDA's own record behind every decision we date.

Audit 2026-09-27 item 4. Since 09-26 every decided row carries the FDA record its action date comes
from (sync_fda_action_dates.py: the Drugs@FDA submission and its approval letter; for CBER products
the FDA's approval letter or notice; for CRLs the letter the FDA released). "fda approval letters"
arrived as a Bing grounding query the same week (15 citations, 13.04% share). This page lists them:
one row per FDA action, newest first, with the letter, the application/supplement, the drug, the
sponsor, the day the sponsor announced it where that differs, and our decision page. The count on
the page is the count in the table, stated once and derived from the rows.

Owner of the facts: the dataset's _d.fda_action_* fields. This script only renders them.

    python build_fda_letters_hub.py
"""
import datetime as dt
import html
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
BASE = "https://www.pdufa.bio"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
       "October", "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(iso, short=False):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month][:3] if short else MON[d.month]} {d.day}, {d.year}"


def kind_of(url, rec):
    if "download.open.fda.gov/crl/" in url:
        return "Complete Response Letter"
    if re.search(r"ltr\.pdf$|/media/\d+/download", url):
        return "Approval letter"
    return "FDA approval notice"


def main():
    sys.path.insert(0, HERE)
    from drug_names import clean_drug_name as _cdn
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    by_action = {}
    for r in rows:
        d = r.get("_d") or {}
        url, fd = d.get("fda_action_source_url"), d.get("fda_action_date")
        if r.get("type") != "PDUFA" or not url or not fd or not re.match(r"https://(www\.)?[a-z.]*fda\.gov/", url):
            continue
        key = (d.get("fda_action_record") or url, fd)          # co-listed partners = one FDA action
        tk = str(r.get("t") or "").upper()
        dcd = str(r.get("dcd") or "")
        page = f"/fda-decision/{tk}-{dcd}"
        has_page = os.path.exists(os.path.join(SITE, "fda-decision", f"{tk}-{dcd}", "index.html"))
        ent = by_action.setdefault(key, {"date": fd, "url": url, "record": d.get("fda_action_record") or "",
                                         "kind": kind_of(url, d.get("fda_action_record")),
                                         "drug": _cdn(str(r.get("name") or "")),
                                         "company": str(r.get("company") or ""), "tickers": [], "pages": [],
                                         "announced": dcd if dcd and dcd != fd else "", "oc": r.get("oc")})
        ent["tickers"].append(tk)
        if has_page:
            ent["pages"].append((tk, page))
    # Audit 2026-10-03 (2.1 / 3.1): archive decision pages with no API row, dated by Drugs@FDA through
    # sync_archive_fda_dates.py (one unambiguous decision-class approval 0-4 days before the
    # announcement). Same key (record, date), so a record already held through a row is not repeated.
    sys.path.insert(0, HERE)
    from drug_names import clean_drug_name
    arch_p = os.path.join(HERE, "_fda_action_archive.json")
    arch = json.load(io.open(arch_p, encoding="utf-8")) if os.path.exists(arch_p) else {}
    for slug, e in sorted(arch.items()):
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not (m and e.get("date") and e.get("source_url")):
            continue
        tk, dcd = m.group(1), m.group(2)
        pth = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(pth):
            continue
        pdoc = io.open(pth, encoding="utf-8", errors="replace").read()
        cm = re.search(r"<span>Company</span><b>(.*?)</b>", pdoc)
        key = (e.get("record") or e["source_url"], e["date"])
        ent = by_action.setdefault(key, {"date": e["date"], "url": e["source_url"], "record": e.get("record") or "",
                                         "kind": "Approval letter" if e.get("letter") else "Drugs@FDA record",
                                         "drug": clean_drug_name(e.get("name") or ""),
                                         "company": html.unescape(cm.group(1)) if cm else "", "tickers": [], "pages": [],
                                         "announced": dcd if dcd != e["date"] else "", "oc": "Approved"})
        if tk not in ent["tickers"]:
            ent["tickers"].append(tk)
            ent["pages"].append((tk, f"/fda-decision/{slug}"))
    acts = sorted(by_action.values(), key=lambda e: e["date"], reverse=True)
    n = len(acts)
    n_ap = sum(1 for e in acts if e["kind"] == "Approval letter")
    n_no = sum(1 for e in acts if e["kind"] == "FDA approval notice")
    n_crl = sum(1 for e in acts if e["kind"] == "Complete Response Letter")
    n_rec = sum(1 for e in acts if e["kind"] == "Drugs@FDA record")
    n_later = sum(1 for e in acts if e["announced"])
    title = f"FDA Approval Letters: {n} FDA Decisions, Each Linked to the FDA's Own Record | pdufa.bio"
    desc = (f"{n} FDA decisions tracked by pdufa.bio, each dated by the FDA's own record: {n_ap} approval "
            f"letter{'s' if n_ap != 1 else ''}, {n_no} FDA notice{'s' if n_no != 1 else ''}, {n_crl} released CRL{'s' if n_crl != 1 else ''}. Newest first, every letter linked.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."
    qa = [
        ("Where can I find an FDA approval letter?",
         "For drugs reviewed by CDER, the FDA posts the approval letter in Drugs@FDA under the application "
         "number, usually within a few days of the action; biologics reviewed by CBER have their letters on "
         "the product's page at fda.gov. This page links the letter for every decision pdufa.bio tracks."),
        ("What date does an FDA approval letter show?",
         "The day the FDA acted. It is often not the day the company announced the decision: of the "
         f"{n} actions listed here, {n_later} were announced by the sponsor on a later day than the FDA's "
         "letter or record, typically the next business day."),
        ("Why does pdufa.bio date decisions by the FDA letter rather than the press release?",
         "Because the letter is the FDA's record of when it acted, and a press release is the company's "
         "record of when it chose to announce. Our decision-timing statistic compares each action date with "
         "the PDUFA goal date, so it uses the FDA's date, and every row here links the document it comes from."),
    ]
    faq_ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "url": f"{BASE}/fda-approval-letters",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                        for q, a in qa]}, separators=(",", ":")) + "</script>")
    ds_ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "Dataset", "name": "FDA action records behind pdufa.bio decisions",
         "description": desc, "url": f"{BASE}/fda-approval-letters",
         "license": "https://creativecommons.org/licenses/by/4.0/",
         "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE},
         "isBasedOn": ["https://open.fda.gov/apis/drug/drugsfda/", "https://www.accessdata.fda.gov/scripts/cder/daf/"],
         "variableMeasured": ["FDA action date", "application and supplement", "sponsor announcement date"]},
        separators=(",", ":")) + "</script>")

    CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,"
           "BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;"
           "text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:960px;margin:0 auto;padding:22px 18px 60px}"
           ".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}"
           ".brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}"
           "h1{font-size:27px;line-height:1.18;margin:10px 0 6px}h1 .g{color:#e3ba5e}h2{font-size:18px;color:#e3ba5e;margin:26px 0 8px}"
           ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:80ch}table{width:100%;border-collapse:collapse;"
           "font-size:13.5px;margin-top:6px}th{text-align:left;color:#e3ba5e;font-size:11.5px;text-transform:uppercase;"
           "letter-spacing:.4px;padding:7px 6px;border-bottom:1px solid #294d80}td{padding:7px 6px;border-bottom:1px solid #14263f;"
           "color:#a7bcd9;vertical-align:top}td.dt{color:#f2f6fc;white-space:nowrap}")
    NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
           '<div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>')
    body = [f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px"><a href="/" style="color:#94a9c9">Home</a> '
            f'&rsaquo; <a href="/decisions" style="color:#94a9c9">Decisions</a> &rsaquo; FDA approval letters</div>'
            f'<h1>FDA approval letters: <span class="g">{n} FDA decisions, each dated by the FDA&#x27;s own record</span></h1>'
            f'<div class="sub">Every FDA decision this site dates is dated from the FDA&#x27;s record of the action, not '
            f'from the company&#x27;s press release: the approval letter in Drugs@FDA ({n_ap}), the FDA&#x27;s approval '
            f'notice or letter for biologics reviewed by CBER ({n_no}), or the Complete Response Letter the FDA released '
            f'({n_crl}), or, for decisions in our archive without an API row, the Drugs@FDA approval record ({n_rec}). '
            f'{n_later} of the {n} were announced by the company on a later day than the FDA acted; those rows '
            f'show both dates. Newest first. This is the evidence behind the '
            f'<a href="/research/fda-decision-timing">decision-timing study</a>.</div>']
    # 3.1 (audit 2026-10-03): "what did the FDA approve on {date}" is a live grounding query (60 citations
    # on 09-28). The last 60 days, one line per FDA action DAY, by the FDA's date, not the announcement.
    today_ = dt.date.today()
    days = {}
    for e in acts:
        if e["oc"] == "Approved" and (today_ - dt.date.fromisoformat(e["date"])).days <= 60:
            days.setdefault(e["date"], []).append(e)
    if days:
        body.append('<h2>What the FDA approved, day by day (last 60 days, by FDA action date)</h2>')
        for day_ in sorted(days, reverse=True):
            items = []
            for e in days[day_]:
                lab = esc(e["drug"][:60]) + f' ({esc("/".join(sorted(set(e["tickers"]))))})'
                if e["pages"]:
                    lab = f'<a href="{esc(e["pages"][0][1])}">{lab}</a>'
                items.append(f'{lab}, <a href="{esc(e["url"])}" rel="noopener">{esc(e["record"] or e["kind"])}</a>'
                             + (f', announced {pretty(e["announced"], short=True)}' if e["announced"] else ""))
            body.append(f'<p id="d-{day_}"><b style="color:#f2f6fc">{pretty(day_)}</b>: the FDA approved '
                        + "; ".join(items) + ".</p>")
    years = {}
    for e in acts:
        years.setdefault(e["date"][:4], []).append(e)
    for yr, ys in years.items():
        body.append(f'<h2>{yr} &middot; {len(ys)} FDA action{"s" if len(ys) != 1 else ""}</h2>'
                    '<table><tr><th>FDA action date</th><th>Drug</th><th>Sponsor</th><th>FDA record</th>'
                    '<th>Announced</th><th>On this site</th></tr>')
        for e in ys:
            pages = " &middot; ".join(f'<a href="{esc(p)}">{esc(t)}</a>' for t, p in e["pages"]) or "&mdash;"
            body.append(f'<tr><td class="dt">{pretty(e["date"], short=True)}</td><td>{esc(e["drug"][:60])}</td>'
                        f'<td>{esc(e["company"][:36])} ({esc("/".join(sorted(set(e["tickers"]))))})</td>'
                        f'<td><a href="{esc(e["url"])}" rel="noopener">{esc(e["kind"])}</a>'
                        f'{"<br><span style=font-size:12px>" + esc(e["record"]) + "</span>" if e["record"] and not e["record"].startswith("CRL letter") else ""}</td>'
                        f'<td>{pretty(e["announced"], short=True) if e["announced"] else "same day"}</td><td>{pages}</td></tr>')
        body.append("</table>")
    body.append('<h2>Questions</h2>')
    for q, a in qa:
        body.append(f'<p><b style="color:#f2f6fc">{esc(q)}</b><br><span style="color:#a7bcd9">{esc(a)}</span></p>')
    body.append('<p><a href="/crl">Every released Complete Response Letter</a> &middot; <a href="/decisions">the decisions '
                'archive</a> &middot; <a href="/research/fda-decision-timing">does the FDA decide on the PDUFA date?</a></p>'
                '<p class="sub" style="font-size:12px">Historical record, linked to the FDA&#x27;s documents. Not investment advice.</p>')
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
           f'initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/fda-approval-letters"><meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d"><meta property="og:type" content="website">'
           f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{BASE}/fda-approval-letters">'
           f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
           f'{faq_ld}{ds_ld}<style>{CSS}</style></head><body><div class="wrap">{NAV}' + "".join(body) + "</div></body></html>")
    out = os.path.join(SITE, "fda-approval-letters", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/fda-approval-letters: {n} FDA actions ({n_ap} approval letters, {n_no} notices, {n_crl} CRL letters); "
          f"{n_later} announced later than the FDA acted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
