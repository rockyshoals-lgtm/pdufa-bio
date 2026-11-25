# -*- coding: utf-8 -*-
"""build_fda_approvals_drugs.py -- /fda-approvals/drugs: Drugs@FDA approvals since January 2025, by application.

David, 2026-11-25 02:53 UTC (Nov 24, 9:53 PM ET): "keep increasing our moat." Drugs@FDA lists approvals one
submission at a time and /fda-approvals lists them by month, /fda-approvals/companies by sponsor. Nobody lists them
by the drug they went to, with how many approvals one application has had since January 2025 (Keytruda's BLA, for
example, has had more than ten efficacy supplements approved) next to the released Complete Response Letters the FDA
sent on the same application number. This page does:

  * /fda-approvals/drugs: every NDA or BLA with an approved original submission or efficacy supplement in Drugs@FDA
    (CDER products only) since January 1, 2025, with its count of each, its latest action date, and the released
    CRLs on the same application number; every application with more than one approval has its approvals listed
  * /fda-approvals/data/approvals-by-drug.csv: one row per approval, CC BY 4.0
  * /crl/letter/<slug>: a line naming the same application's approvals here, between <!--DRUGAPPROVALS:BEGIN--> and
    <!--DRUGAPPROVALS:END--> (written here, after build_crl_letters.py and the month cache refresh)

Source: _fda_approvals_months.json, which build_fda_approvals_months.py fills from openFDA drugsfda (no fetching
here), and the /crl/letter pages build_crl_letters.py writes from openFDA transparency/crl. An application is the
number Drugs@FDA and the letter print (NDA 217002, BLA 125514; the FDA's "BL" is the same BLA number).

FACTS ONLY: counts and dates from Drugs@FDA and the CRL release. No approval rates, no reading of why a letter was
sent or what it led to, no view on any drug or company. A CRL on the same application number may concern another
submission than the approvals listed; the page says so.

    python build_fda_approvals_drugs.py
"""
import collections
import csv
import glob
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
sys.path.insert(0, HERE)
from build_fda_approvals_companies import (BASE, CACHE, MON, NEW, esc, foot, head, load, pl, pretty,  # noqa: E402
                                           short_day, who)

OUT = os.path.join(SITE, "fda-approvals", "drugs", "index.html")
CSV_OUT = os.path.join(SITE, "fda-approvals", "data", "approvals-by-drug.csv")
LETTERS = os.path.join(SITE, "crl", "letter")
CANON = "/fda-approvals/drugs"
CSV_COLS = ["application", "brand", "generic", "sponsor_name_title_case", "submission", "kind", "submission_class",
            "action_date", "fda_letter", "approvals_on_application_since_2025", "released_crl_letters_same_application",
            "openfda_read_on", "month_page"]
APPNO = re.compile(r"\b(NDA|BLA|BL)\s*0*(\d{5,6})\b")
BLOCK = re.compile(r"<!--DRUGAPPROVALS:BEGIN-->.*?<!--DRUGAPPROVALS:END-->", re.S)
ANCHOR = "<h2>The letter's text</h2>"


def app_label(app):
    """BLA125514 -> BLA 125514"""
    m = re.match(r"([A-Z]+)(\d+)$", app or "")
    return f"{m.group(1)} {m.group(2)}" if m else str(app or "")


def anchor(app):
    return re.sub(r"[^a-z0-9]", "", str(app).lower())


def letter_apps(doc):
    """The application numbers a /crl/letter page's facts table prints, as Drugs@FDA writes them (BLA125514)."""
    m = re.search(r"<tr><th>Application</th><td>(.*?)</td></tr>", doc, re.S)
    out = []
    for kind, num in APPNO.findall(m.group(1) if m else ""):
        a = ("BLA" if kind in ("BL", "BLA") else "NDA") + num.zfill(6)
        if a not in out:
            out.append(a)
    return out


def letter_subs(doc):
    """The submissions a letter's facts table names after a slash ("NDA 220381/Original 2" -> {"NDA220381": "Original 2"})."""
    m = re.search(r"<tr><th>Application</th><td>(.*?)</td></tr>", doc, re.S)
    out = {}
    for kind, num, sub in re.findall(r"\b(NDA|BLA|BL)\s*0*(\d{5,6})\s*/\s*([A-Za-z]+\s*\d+)", m.group(1) if m else ""):
        out.setdefault(("BLA" if kind in ("BL", "BLA") else "NDA") + num.zfill(6), re.sub(r"\s+", " ", sub))
    return out


def https(u):
    return re.sub(r"^http://", "https://", str(u or ""))


def letter_pages():
    """application -> [(letter date, /crl/letter/<slug>)], from the built letter pages, oldest first."""
    by_app = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(LETTERS, "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.search(r"-(\d{4}-\d{2}-\d{2})(?:-\d+)?$", slug)
        if not m:
            continue
        doc = io.open(p, encoding="utf-8").read()
        for a in letter_apps(doc):
            by_app[a].append((m.group(1), f"/crl/letter/{slug}"))
    return {a: sorted(v) for a, v in by_app.items()}


def counts(nn, ne):
    """'2 original approvals and 7 efficacy supplements', leaving out a zero"""
    p = [pl(k, one, many) for k, one, many in ((nn, "original approval", "original approvals"),
                                                (ne, "efficacy supplement", "efficacy supplements")) if k]
    return " and ".join(p)


def counts_approved(nn, ne):
    """'1 approved original submission and 2 approved efficacy supplements', leaving out a zero"""
    p = [pl(k, one, many) for k, one, many in ((nn, "approved original submission", "approved original submissions"),
                                                (ne, "approved efficacy supplement", "approved efficacy supplements")) if k]
    return " and ".join(p)


def iso_pretty(s):
    y, mo, d = (int(x) for x in s.split("-"))
    return f"{MON[mo - 1].capitalize()[:3]} {d}, {y}"


def main():
    if not os.path.exists(CACHE):
        print("no _fda_approvals_months.json; nothing to build")
        return 0
    items, months, fetched = load()
    if not items:
        print("the approvals cache is empty; nothing to build")
        return 0
    apps = collections.defaultdict(list)
    for x in items:
        apps[x["app"]].append(x)
    crl = letter_pages()
    try:
        import build_crl_months
        crl_upd = build_crl_months.corpus()[1]
    except Exception:  # noqa: BLE001
        crl_upd = ""
    crl_src = ("this site's letter pages, from the FDA's CRL release" + (f" as last updated {crl_upd}" if crl_upd else ""))

    def name(xs):
        """The brand (and generic) the newest approval that prints one; with none, the application and its sponsor."""
        for x in reversed(xs):
            if x.get("brand") or x.get("generic"):
                return who(x)
        return f"{esc(app_label(xs[-1]['app']))} ({esc(xs[-1]['sponsor'])})"

    def sponsor(xs):
        """The sponsor on the newest approval, and any other name earlier approvals print."""
        last = xs[-1]["sponsor"]
        others = sorted({x["sponsor"] for x in xs} - {last})
        return last + (f" (earlier approvals: {', '.join(others)})" if others else "")

    rows = sorted(apps.items(), key=lambda kv: (-len(kv[1]), -kv[1][-1]["day"].toordinal(),
                                                str(kv[1][-1].get("brand") or "").lower(), kv[0]))
    n_all = len(items)
    n_new = sum(1 for x in items if x["kind"] == NEW)
    n_eff = n_all - n_new
    multi = [(a, xs) for a, xs in rows if len(xs) > 1]
    with_crl = [a for a, _ in rows if crl.get(a)]
    first_day, last_day = items[0]["day"], items[-1]["day"]
    reads = sorted(set(fetched.values()))
    read_txt = (f"read from openFDA on {reads[0]}" if len(reads) == 1 else
                f"read from openFDA between {reads[0]} and {reads[-1]} (each approval's read date is in the CSV's "
                f"openfda_read_on column)")
    top_a, top_xs = rows[0]
    top_n = len(top_xs)
    tops = [a for a, xs in rows if len(xs) == top_n]

    lede = (f"Drugs@FDA lists {n_all:,} FDA approvals with action dates from {pretty(first_day)} to {pretty(last_day)}, "
            f"on {pl(len(rows), 'application', 'applications')}: "
            f"{pl(n_new, 'original approval', 'original approvals')} and "
            f"{pl(n_eff, 'efficacy supplement', 'efficacy supplements')}. "
            f"{pl(len(multi), 'application has', 'applications have')} more than one approval in that time"
            + (f"; the most is {top_n}, on {' and '.join(re.sub(r'<[^>]+>', '', name(apps[a])) + ', ' + app_label(a) for a in tops)}"
               if top_n > 1 else "")
            + f". {crl_src[0].upper() + crl_src[1:]}, include at least one Complete Response Letter on the same "
              f"application number for {pl(len(with_crl), 'of these applications', 'of these applications')}.")
    lede = lede.replace("&amp;", "&")
    method = (f"Source: openFDA drugsfda (the Drugs@FDA data), {read_txt}, and the FDA's released Complete Response "
              f"Letters (openFDA transparency/crl{', release last updated ' + crl_upd if crl_upd else ''}) as this site's "
              f"letter pages hold them. Drugs@FDA covers drugs and the "
              f"therapeutic biologics the FDA's drug center (CDER) reviews; products the biologics center (CBER) "
              f"reviews, such as vaccines and cell and gene therapies, are not in it. An approval here is an approved "
              f"original submission of an NDA or BLA (biosimilars and medical gases included; an application approved "
              f"in two original submissions counts twice) or an approved supplement in Drugs@FDA's efficacy class, "
              f"which holds supplements backed by clinical data, such as a new indication. Generic approvals (ANDAs), "
              f"labeling-only and manufacturing supplements are not listed. openFDA trails Drugs@FDA by about a week, "
              f"so the latest days can be missing until the next read. One brand can sit on more than one application "
              f"(a new formulation often has its own), and each application is listed on its own. A released CRL is "
              f"matched on the application number the letter prints; it may concern a submission other than the "
              f"approvals listed here, before or after them, and a letter the FDA has not released is not counted. A few "
              f"approvals have no FDA letter link in Drugs@FDA; those rows link none.")
    title = f"FDA Approvals by Drug Since 2025 ({len(rows):,} Applications) | pdufa.bio"
    desc = (f"{n_new:,} original and {n_eff:,} efficacy-supplement approvals in Drugs@FDA since January 2025, by NDA "
            f"or BLA, with FDA letters where listed and any released CRL.")
    if len(desc) > 158:
        desc = (f"Drugs@FDA original and efficacy-supplement approvals since January 2025, by NDA or BLA, with any "
                f"released CRL on the same application.")[:158]

    def crl_cell(a):
        ls = crl.get(a) or []
        if not ls:
            return "none found"
        return ", ".join(f'<a href="{esc(u)}">{esc(iso_pretty(d))}</a>' for d, u in ls)

    B = ['<h1>FDA approvals by drug application, since January 2025</h1>',
         f'<p class="sub" data-adrug="lede" style="color:#cfe0f5">{esc(lede)}</p>',
         f'<p class="sub" data-adrug="method" style="font-size:13px">{esc(method)}</p>',
         '<p class="sub">Every approval, one row each: <a href="/fda-approvals/data/approvals-by-drug.csv">CSV</a>, '
         'free under CC BY 4.0: cite pdufa.bio and link this page. By month: <a href="/fda-approvals">FDA approvals by '
         'month</a> &middot; by sponsor: <a href="/fda-approvals/companies">FDA approvals by company</a> &middot; '
         'letters: <a href="/crl">the CRL database</a></p>',
         '<table data-adrug="table"><tr><th>Drug</th><th>Application</th><th>Original approvals</th>'
         '<th>Efficacy supplements</th><th>Latest action date</th><th>Released CRLs, same application</th></tr>']
    for a, xs in rows:
        nn = sum(1 for x in xs if x["kind"] == NEW)
        drug = (f'<a href="#{anchor(a)}">{name(xs)}</a>' if len(xs) > 1 else
                (f'<a href="{esc(https(xs[0]["letter"]))}" rel="noopener">{name(xs)}</a>' if xs[0].get("letter") else name(xs)))
        rid = f' id="{anchor(a)}"' if len(xs) == 1 else ""      # a multi-approval application's anchor is its h3
        B.append(f'<tr data-app="{esc(a)}"{rid}><td>{drug}</td><td>{esc(app_label(a))}</td><td>{nn}</td>'
                 f'<td>{len(xs) - nn}</td><td class="dt">{esc(short_day(xs[-1]["day"]))}</td>'
                 f'<td>{crl_cell(a)}</td></tr>')
    B.append('</table>')
    B.append('<p class="sub">A drug with one approval links its FDA letter from the table. Each application with more '
             'than one approval lists them below, newest first.</p>')

    def line(x):
        lt = f' <a href="{esc(https(x["letter"]))}" rel="noopener">FDA letter</a>' if x.get("letter") else ""
        cls = f' (submission class: {esc(x["class"])})' if x.get("class") and x["kind"] == NEW else ""
        return (f'<li data-sub="{esc(x["app"])} {esc(x["sub"])}"><b>{esc(short_day(x["day"]))}:</b> {esc(x["sub"])}, '
                f'{esc("original approval" if x["kind"] == NEW else "efficacy supplement")}{cls}.{lt} &middot; '
                f'<a href="{esc(x["month_page"])}">{esc(MON[x["day"].month - 1].capitalize())} {x["day"].year}</a></li>')

    for a, xs in multi:
        nn = sum(1 for x in xs if x["kind"] == NEW)
        B.append(f'<h3 id="{anchor(a)}" data-group="{esc(a)}">{name(xs)}, {esc(app_label(a))}</h3>'
                 f'<p class="sub">{counts(nn, len(xs) - nn).capitalize()} since January 2025. Sponsor in '
                 f'Drugs@FDA on the latest approval: {esc(sponsor(xs))}.'
                 + (f' CRLs on the same application number on this site\'s letter pages: {crl_cell(a)}.' if crl.get(a) else "")
                 + f'</p><ul style="line-height:1.75">{"".join(line(x) for x in reversed(xs))}</ul>')
    B.append('<p class="sub">Facts only: counts and dates from Drugs@FDA and the FDA\'s CRL release, with no view on '
             'any drug, company or outcome. <a href="/fda-approvals">FDA approvals by month</a> &middot; '
             '<a href="/fda-approvals/companies">by company</a> &middot; <a href="/crl/facts">CRL facts</a> &middot; '
             '<a href="/research">research</a></p>')

    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": "FDA drug approvals by application since January 2025",
          "description": (f"{n_all:,} FDA approvals in Drugs@FDA with action dates from {first_day.isoformat()} to "
                          f"{last_day.isoformat()} ({n_new:,} original NDA and BLA approvals, {n_eff:,} efficacy "
                          f"supplement approvals) on {len(rows):,} applications, each with its submission, action date "
                          f"and FDA letter, and the FDA's released Complete Response Letters on the same application "
                          f"number."),
          "url": BASE + CANON, "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
          "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"},
          "isBasedOn": ["https://open.fda.gov/apis/drug/drugsfda/", "https://open.fda.gov/apis/transparency/crl/"],
          "temporalCoverage": f"{first_day.isoformat()}/{last_day.isoformat()}", "dateModified": reads[-1],
          "identifier": BASE + "/fda-approvals/data/approvals-by-drug.csv",
          "keywords": ["FDA approvals", "Drugs@FDA", "NDA", "BLA", "efficacy supplement", "Complete Response Letter"],
          "variableMeasured": ["application", "submission", "kind", "submission class", "action date", "FDA letter",
                               "approvals on application since 2025", "released CRL letters on the same application"],
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                            "contentUrl": BASE + "/fda-approvals/data/approvals-by-drug.csv"}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "FDA approvals", "item": BASE + "/fda-approvals"},
        {"@type": "ListItem", "position": 3, "name": "By drug", "item": BASE + CANON}]}
    extra = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False, separators=(",", ":"))}'
                    f'</script>' for o in (ld, crumbs))
    tpl = io.open(os.path.join(SITE, "methodology", "index.html"), encoding="utf-8").read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(head(tpl, title, desc, CANON, extra, '<div class="bc"><a href="/">Home</a> › '
                                             '<a href="/fda-approvals">FDA approvals</a> › By drug</div>') + "".join(B) + foot(tpl))

    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(CSV_COLS)
        for a, xs in rows:
            ls = "; ".join(BASE + u for _, u in crl.get(a) or [])
            for x in xs:
                w.writerow([app_label(a), x.get("brand") or "", x.get("generic") or "", x["sponsor"], x["sub"],
                            x["kind"], x.get("class") or "", x["day"].isoformat(), https(x.get("letter")), len(xs), ls,
                            x["read"], BASE + x["month_page"]])

    # the same application's approvals, named on each released letter's page (a line, no reading of the two together)
    linked = 0
    for p in sorted(glob.glob(os.path.join(LETTERS, "*", "index.html"))):
        doc = io.open(p, encoding="utf-8").read()
        new = BLOCK.sub("", doc)
        hits = [a for a in letter_apps(new) if a in apps]
        if hits and ANCHOR in new:
            ldate = re.search(r"-(\d{4}-\d{2}-\d{2})(?:-\d+)?$", os.path.basename(os.path.dirname(p)))
            ldate = ldate.group(1) if ldate else ""
            lsubs = letter_subs(new)
            parts = []
            for a in hits:
                xs = apps[a]
                nn = sum(1 for x in xs if x["kind"] == NEW)
                t = (f'lists {counts_approved(nn, len(xs) - nn)} on <a href="{CANON}#{anchor(a)}">{esc(app_label(a))}</a> '
                     f'with action dates since January 1, 2025, {"the latest " if len(xs) > 1 else ""}dated '
                     f'{esc(pretty(xs[-1]["day"]))}')
                same = [x for x in xs if x["day"].isoformat() == ldate]
                if same:
                    t += (f' (one, {esc(same[0]["sub"])}, has this letter\'s date; the letter names '
                          + (f'{esc(lsubs[a])}' if a in lsubs else "no submission number") + ")")
                parts.append(t)
            read = max(x["read"] for a in hits for x in apps[a])
            block = (f'<!--DRUGAPPROVALS:BEGIN--><p class="sub" data-crl-letter="approvals">Drugs@FDA, a separate FDA '
                     f'dataset read {esc(read)}, {"; and ".join(parts)}. The letter may concern another submission on '
                     f'that application; the status in the table above is the CRL release\'s.</p><!--DRUGAPPROVALS:END-->')
            new = new.replace(ANCHOR, block + ANCHOR, 1)
            linked += 1
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
    print(f"/fda-approvals/drugs: {n_all:,} approvals ({n_new:,} new, {n_eff:,} efficacy) on {len(rows):,} "
          f"applications, {len(multi):,} with more than one, {len(with_crl):,} with a released CRL on the same number; "
          f"{linked} letter pages linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
