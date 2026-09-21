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
from urllib.parse import quote as _urlq

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from capture_crl_corpus import newest_corpus  # noqa: E402  (the newest dated snapshot on disk)
CORPUS = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
BASE = "https://www.pdufa.bio"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def esc(s):
    return _html.escape(str(s or "").strip())


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    rows, seen, no_file, dupes = [], set(), 0, 0
    n_records = len(recs)
    n_approved = sum(1 for r in recs if str(r.get("approval_status") or "").strip() == "Approved")
    n_unapproved = sum(1 for r in recs if str(r.get("approval_status") or "").strip() == "Unapproved")
    last_updated = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        fn = str(r.get("file_name") or "").strip()
        # Audit 09-20b: the old filter (\w.- only) silently dropped 13 letters whose FDA file
        # names carry spaces or commas ("Pages from 214835Orig1s000_ORIGINAL_APPROVAL_PACKAGE.pdf",
        # "215973,215974Orig1s000OtherActionLtrs.pdf"); all resolve on FDA's server once
        # URL-encoded (HEAD 200, checked 2026-09-20). One record ("Under Review for Release")
        # has no file yet and is counted, not listed.
        if not m or not fn.lower().endswith(".pdf"):
            no_file += 1
            continue
        key = (fn, m.group(0))
        if key in seen:
            dupes += 1          # FDA's release repeats two records verbatim
            continue
        seen.add(key)
        apps = r.get("application_number")
        rows.append({
            "iso": f"{m.group(3)}-{m.group(1)}-{m.group(2)}",
            "year": m.group(3),
            "company": str(r.get("company_name") or "").strip(),
            "app": ", ".join(apps) if isinstance(apps, list) else str(apps or ""),
            "status": str(r.get("approval_status") or "").strip(),
            "url": "https://download.open.fda.gov/crl/" + _urlq(fn),
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
    title = (f"FDA Complete Response Letters: {n_records} Released CRLs, Searchable by Year "
             f"| pdufa.bio")
    desc = (f"{n_records} FDA Complete Response Letters (openFDA), by year, each linking the "
            f"FDA's PDF. {n_approved} went to applications since approved, and why that is not "
            f"an approval rate.")
    # by-year split of openFDA's approval_status -- the shape that shows the release policy
    split = collections.OrderedDict()
    for r in sorted(rows, key=lambda x: x["year"], reverse=True):
        d_ = split.setdefault(r["year"], {"Approved": 0, "Unapproved": 0})
        if r["status"] in d_:
            d_[r["status"]] += 1

    qa = [
        ("What is a Complete Response Letter?",
         "A Complete Response Letter (CRL) is the FDA's formal notice that it will not "
         "approve a drug application in its current form. It lists the deficiencies "
         "the sponsor must address; it is not a permanent rejection. Of the "
         f"{n_records} letters the FDA has released, {n_approved} were issued to "
         "applications the FDA has since approved."),
        ("How many FDA Complete Response Letters are published here?",
         f"{n_records} records in the FDA's release (openFDA transparency/crl, last updated "
         f"{last_updated}): {n} distinct letters with a hosted PDF are listed, {dupes} "
         f"record{'s' if dupes != 1 else ''} repeat{'s' if dupes == 1 else ''} another verbatim and "
         f"{no_file} {'is' if no_file == 1 else 'are'} still marked under review for release. "
         f"{n24} of the listed letters were issued in 2024 or later; the rest go back to 2002."),
        ("How many CRLs are later approved?",
         f"This corpus cannot say. openFDA labels {n_approved} of the {n_records} released "
         f"letters as belonging to applications the FDA has since approved and {n_unapproved} "
         f"as not approved, but the split follows the FDA's release policy, not the odds: the "
         f"agency released archived letters only for applications it had approved, then every "
         f"letter from 2024 on. Nearly every letter dated 2023 or earlier is on an approved "
         f"application and nearly every letter from 2025 on is not. Counts are stated here; a "
         f"rate from this data would measure what the FDA chose to publish."),
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
            f'<h1>FDA Complete Response Letters: <span class="g">{n_records} released '
            f'CRLs</span></h1>'
            f'<div class="sub">The FDA releases Complete Response Letters under its '
            f'CRL transparency program, published through openFDA. This page lists every '
            f'released letter with a hosted file ({n} distinct letters from {n_records} '
            f'records), newest first, each linking the original PDF on FDA&#x27;s servers. '
            f'{n24} listed letters are from 2024 or later; the archive reaches back to 2002. '
            f'Where a letter matches a decision this site tracked, the decision page '
            f'(with the run-up chart and outcome) is linked beside it. This page '
            f'states counts, never approval rates; the section below explains why a rate '
            f'from this data would mislead.</div>'
            f'<h2>What the FDA has released, and what it does and does not show</h2>'
            f'<div class="sub" style="max-width:82ch">A complete response letter is the FDA&#x27;s '
            f'formal notice, at the end of a review cycle, that it will not approve an application '
            f'in its current form. The letter lists the deficiencies. It is not a permanent '
            f'rejection: the sponsor can resubmit, and the same application is often approved on '
            f'a later cycle.<br><br>'
            f'<b style="color:#f2f6fc">{n_records} records</b> in the FDA&#x27;s release '
            f'(<a href="https://api.fda.gov/transparency/crl.json?count=approval_status" '
            f'rel="noopener">openFDA transparency/crl</a>, last updated {esc(last_updated)}). '
            f'openFDA labels <b style="color:#f2f6fc">{n_approved}</b> of them as letters to '
            f'applications the FDA has since approved and <b style="color:#f2f6fc">'
            f'{n_unapproved}</b> as letters to applications not approved as of the release. '
            f'The FDA described its first batch (July 10, 2025) as decision letters '
            f'&ldquo;associated with since-approved applications&rdquo;; later batches added '
            f'letters for applications still unapproved.<br><br>'
            f'<b style="color:#e3ba5e">Read the split by year before drawing anything from it.</b> '
            f'Nearly every letter dated 2023 or earlier is on a since-approved application, and '
            f'nearly every letter from 2025 on is not. That is the shape of a release policy '
            f'(archived letters for approved applications first, then everything from 2024 '
            f'onward), not the shape of the odds. The corpus shows that an application which '
            f'receives a CRL can be approved later, {n_approved} times over; it cannot say how '
            f'often that happens, and this site does not compute a rate from it.</div>'
            + '<table style="max-width:520px"><tr><th>Letter year</th><th>Since approved</th>'
              '<th>Not approved</th><th>Total</th></tr>'
            + "".join(f'<tr><td class="dt">{yr}</td><td>{v["Approved"]}</td><td>{v["Unapproved"]}</td>'
                      f'<td>{v["Approved"] + v["Unapproved"]}</td></tr>' for yr, v in split.items())
            + f'<tr><td class="dt">All</td><td>{sum(v["Approved"] for v in split.values())}</td>'
              f'<td>{sum(v["Unapproved"] for v in split.values())}</td><td>{n}</td></tr></table>'
            + f'<div style="font-size:12px;color:#94a9c9;margin:6px 0 10px">Counts of listed letters by '
              f'openFDA&#x27;s approval_status field; the {no_file} record without a hosted file and '
              f'the {dupes} duplicate record{"s" if dupes != 1 else ""} are not in the table.</div>']

    # the release as a series (capture_crl_corpus.py): one row per capture that changed the set
    try:
        ser = json.load(io.open(os.path.join(HERE, "_crl_capture_series.json"), encoding="utf-8")).get("rows") or []
    except Exception:
        ser = []
    seen_tot, series_rows = None, []
    for r_ in ser:
        if (r_.get("total"), r_.get("approved"), r_.get("unapproved")) != seen_tot:
            series_rows.append(r_); seen_tot = (r_.get("total"), r_.get("approved"), r_.get("unapproved"))
    last_check = ser[-1]["checked"] if ser else ""
    if series_rows:
        body.append('<h2>The release over time</h2>'
                    '<div class="sub">The FDA adds letters to the release in batches. Each row is a '
                    'dated capture of openFDA transparency/crl on which the record set differed from '
                    f'the previous capture; last checked {esc(last_check)}.</div>'
                    '<table style="max-width:560px"><tr><th>Captured</th><th>Records</th>'
                    '<th>Since approved</th><th>Not approved</th><th>Added since prior</th></tr>')
        prev = None
        for r_ in series_rows:
            delta = "" if prev is None else f"+{int(r_['total']) - int(prev)}"
            body.append(f'<tr><td class="dt">{esc(r_["checked"])}</td><td>{r_["total"]}</td>'
                        f'<td>{r_.get("approved") if r_.get("approved") is not None else "&mdash;"}</td>'
                        f'<td>{r_.get("unapproved") if r_.get("unapproved") is not None else "&mdash;"}</td>'
                        f'<td>{delta}</td></tr>')
            prev = r_["total"]
        body.append('</table>')

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
    print(f"/crl: {n_records} records -> {n} listed letters ({dupes} duplicate, {no_file} without a file) "
          f"across {len(by_year)} years; approved {n_approved} / unapproved {n_unapproved}; "
          f"{len(ours)} letter(s) cross-linked to our decision pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
