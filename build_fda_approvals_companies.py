# -*- coding: utf-8 -*-
"""build_fda_approvals_companies.py -- /fda-approvals/companies: Drugs@FDA approvals since January 2025, by sponsor.

David, 2026-11-22: "continue to build the moat, row the boat." Drugs@FDA lists approvals one application at a time
and /fda-approvals lists them by month. Nobody lists them by the company they went to, next to that company's
released Complete Response Letters. This page does:

  * /fda-approvals/companies: every sponsor-name group with an approved original NDA/BLA submission or efficacy
    supplement in Drugs@FDA (CDER products only) since January 1, 2025, with its count of each and every approval
    listed under it (action date, brand, application, submission, the FDA's letter, the month page)
  * /fda-approvals/data/approvals-by-company.csv: one row per approval, CC BY 4.0
  * /crl/company/<slug>: a link here for the same name group (no count: different files and periods), between
    <!--APPROVALS:BEGIN--> and <!--APPROVALS:END--> (written here, after the month pages refresh the cache, so the
    count is the cache's)

Source: _fda_approvals_months.json, which build_fda_approvals_months.py fills from openFDA drugsfda (no fetching here).
Grouping rule: the one /crl/companies states (build_crl_companies.key_of): the sponsor name as Drugs@FDA prints it,
with capitalization, punctuation and corporate-form words ignored. A company printed two ways stays two groups.

FACTS ONLY: counts and dates from Drugs@FDA. No approval rates, no comparison with letters, no view on any company.

    python build_fda_approvals_companies.py
"""
import collections
import csv
import datetime as dt
import glob
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
sys.path.insert(0, HERE)
from build_crl_companies import GRP, key_of, label_of, slug_of  # noqa: E402

CACHE = os.path.join(HERE, "_fda_approvals_months.json")
OUT = os.path.join(SITE, "fda-approvals", "companies", "index.html")
CSV_OUT = os.path.join(SITE, "fda-approvals", "data", "approvals-by-company.csv")
CRL_CO = os.path.join(SITE, "crl", "company")
BASE = "https://www.pdufa.bio"
MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
NEW = "new application"
CSV_COLS = ["sponsor_group", "sponsor_name_title_case", "application", "submission", "kind", "submission_class",
            "action_date", "brand", "generic", "fda_letter", "openfda_read_on", "month_page"]
esc = lambda s: html.escape(str(s or ""), quote=True)  # noqa: E731


def pretty(d):
    return f"{MON[d.month - 1].capitalize()} {d.day}, {d.year}"


def short_day(d):
    return f"{MON[d.month - 1].capitalize()[:3]} {d.day}, {d.year}"


def pl(k, one, many):
    return f"{k:,} {one if k == 1 else many}"


def load():
    """Every approval in the cache once, in date order: dicts with day, read, key, month_page added."""
    d = json.load(io.open(CACHE, encoding="utf-8"))
    out, seen = [], set()
    for month in sorted(d):
        read = str(d[month].get("fetched") or "")[:10]
        for it in d[month].get("items") or []:
            k = (it.get("app"), it.get("sub"))
            if k in seen or not it.get("date"):
                continue
            seen.add(k)
            day = dt.date.fromisoformat(it["date"])
            out.append(dict(it, day=day, read=read, key=key_of(it.get("sponsor") or ""),
                            month_page=f"/fda-approvals/{day.year}/{MON[day.month - 1]}"))
    out.sort(key=lambda x: (x["day"], x["app"], x["sub"]))
    return out, sorted(d), {m: str(d[m].get("fetched") or "")[:10] for m in d}


def who(x):
    g = x.get("generic") or ""
    return esc(x.get("brand") or g or x["app"]) + (f" ({esc(g)})" if g and g.lower() != str(x.get("brand") or "").lower()
                                                     else "")


def head(tpl, title, desc, canon, extra, crumb_html):
    h = tpl[:tpl.index("<h1")]
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", h, count=1, flags=re.S)
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")'):
        h = re.sub(pat, lambda mm: mm.group(1) + esc(desc) + mm.group(2), h)
    for pat in (r'(<link rel="canonical" href=")[^"]*(")', r'(<meta property="og:url" content=")[^"]*(")'):
        h = re.sub(pat, lambda mm: mm.group(1) + BASE + canon + mm.group(2), h)
    h = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda mm: mm.group(1) + esc(title.split(" | ")[0])
               + mm.group(2), h)
    h = re.sub(r'(<meta name="twitter:title" content=")[^"]*(")', lambda mm: mm.group(1) + esc(title) + mm.group(2), h)
    h = re.sub(r'<div class="bc">.*?</div>', crumb_html, h, count=1, flags=re.S)
    h = re.sub(r'<script type="application/ld\+json"[^>]*>.*?</script>', "", h, flags=re.S)
    h = re.sub(r"<!--DMOD:BEGIN-->.*?<!--DMOD:END-->", "", h, flags=re.S)
    return h.replace("</head>", extra + "</head>", 1)


def foot(tpl):
    f = tpl[tpl.index("<footer"):] if "<footer" in tpl else "</div></body></html>"
    return re.sub(r"<!--(SITELINKS|RELATED):BEGIN-->.*?<!--\1:END-->", "", f, flags=re.S)


def main():
    if not os.path.exists(CACHE):
        print("no _fda_approvals_months.json; nothing to build")
        return 0
    items, months, fetched = load()
    if not items:
        print("the approvals cache is empty; nothing to build")
        return 0
    groups = collections.defaultdict(list)
    for x in items:
        groups[x["key"]].append(x)
    no_name = groups.pop("", [])
    labels, printed = {}, {}
    for k, xs in groups.items():
        printed[k] = collections.Counter(x["sponsor"] for x in xs)
        # the label is the most-printed name without its corporate-form words; ties go to the first alphabetically
        top = sorted(printed[k].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        labels[k] = label_of(top)
    slugs, used = {}, collections.Counter()
    for k in sorted(groups):
        s = slug_of(k) or "company"
        used[s] += 1
        slugs[k] = s if used[s] == 1 else f"{s}-{used[s]}"
    crl_pages = {os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(CRL_CO, "*", "index.html"))}

    n_all = len(items)
    n_new = sum(1 for x in items if x["kind"] == NEW)
    n_eff = n_all - n_new
    first_day, last_day = items[0]["day"], items[-1]["day"]
    reads = sorted(set(fetched.values()))
    read_txt = (f"read from openFDA on {reads[0]}" if len(reads) == 1 else
                f"read from openFDA between {reads[0]} and {reads[-1]} (each approval's read date is in the CSV's "
                f"openfda_read_on column)")
    rows = sorted(groups.items(), key=lambda kv: (-len(kv[1]), labels[kv[0]].lower(), kv[0]))
    multi = sum(1 for _, xs in rows if len(xs) > 1)

    n_apps = len({x["app"] for x in items if x["kind"] == NEW})
    lede = (f"Drugs@FDA lists {n_all:,} FDA approvals with action dates from {pretty(first_day)} to {pretty(last_day)}: "
            f"{pl(n_new, 'original approval', 'original approvals')} of new drug and biologic applications "
            f"({pl(n_apps, 'application', 'applications')}) and {pl(n_eff, 'efficacy supplement', 'efficacy supplements')}. "
            f"They fall under {pl(len(rows), 'sponsor-name group', 'sponsor-name groups')}"
            + (f" (and {pl(len(no_name), 'approval', 'approvals')} with no sponsor name)" if no_name else "")
            + f"; {pl(multi, 'group has', 'groups have')} more than one approval.")
    method = (f"Source: openFDA drugsfda (the Drugs@FDA data), {read_txt}. Drugs@FDA covers drugs and the therapeutic "
              f"biologics the FDA's drug center (CDER) reviews; products the biologics center (CBER) reviews, such as "
              f"vaccines and cell and gene therapies, are not in it. An approval here is an approved original "
              f"submission of an NDA or BLA (biosimilars and medical gases included; an application approved in two "
              f"original submissions counts twice) or an approved supplement in Drugs@FDA's efficacy class, which "
              f"holds supplements backed by clinical data, such as a new indication. Generic approvals (ANDAs), "
              f"labeling-only and manufacturing supplements are not listed. openFDA trails Drugs@FDA by about a week, "
              f"so the latest days can be missing until the next read. Drugs@FDA lists each application under its "
              f"current sponsor, which may not be the sponsor at approval. Approvals are grouped on {GRP}, the rule "
              f"/crl/companies uses, so one company printed two ways (an abbreviated word, another legal entity) "
              f"forms two groups; each group shows every sponsor name it holds, in title case (Drugs@FDA prints them "
              f"in capitals).")
    title = f"FDA Approvals by Company Since 2025: {n_all:,} Drugs@FDA Approvals | pdufa.bio"
    desc = (f"FDA approvals in Drugs@FDA since January 2025 by sponsor: {n_new:,} original approvals and {n_eff:,} "
            f"efficacy supplements, each with its FDA letter.")[:158]
    canon = "/fda-approvals/companies"

    B = [f'<h1>FDA approvals by sponsor company, since January 2025</h1>',
         f'<p class="sub" data-acomp="lede" style="color:#cfe0f5">{esc(lede)}</p>',
         f'<p class="sub" data-acomp="method" style="font-size:13px">{esc(method)}</p>',
         f'<p class="sub">Every approval, one row each: <a href="/fda-approvals/data/approvals-by-company.csv">CSV</a>, '
         f'free under CC BY 4.0: cite pdufa.bio and link this page. By month: <a href="/fda-approvals">FDA approvals by '
         f'month</a> &middot; by drug: <a href="/fda-approvals/drugs">FDA approvals by drug application</a> &middot; '
         f'letters: <a href="/crl/companies">Complete Response Letters by company</a></p>',
         '<table data-acomp="table"><tr><th>Sponsor</th><th>Original approvals</th><th>Efficacy supplements</th>'
         '<th>Latest action date</th></tr>']
    for k, xs in rows:
        nn = sum(1 for x in xs if x["kind"] == NEW)
        B.append(f'<tr data-key="{esc(slugs[k])}"><td><a href="#{esc(slugs[k])}">{esc(labels[k])}</a></td>'
                 f'<td>{nn}</td><td>{len(xs) - nn}</td><td class="dt">{esc(short_day(xs[-1]["day"]))}</td></tr>')
    if no_name:
        nn = sum(1 for x in no_name if x["kind"] == NEW)
        B.append(f'<tr data-key=""><td>no sponsor name</td><td>{nn}</td><td>{len(no_name) - nn}</td>'
                 f'<td class="dt">{esc(short_day(no_name[-1]["day"]))}</td></tr>')
    B.append('</table>')

    def line(x):
        lt = f' <a href="{esc(x["letter"])}" rel="noopener">FDA letter</a>' if x.get("letter") else ""
        cls = f' ({esc(x["class"])})' if x.get("class") and x["kind"] == NEW else ""
        return (f'<li data-app="{esc(x["app"])} {esc(x["sub"])}"><b>{esc(short_day(x["day"]))}:</b> {who(x)}, '
                f'{esc(x["app"])} {esc(x["sub"])}, {esc("original approval" if x["kind"] == NEW else "efficacy supplement")}{cls}.{lt} &middot; '
                f'<a href="{esc(x["month_page"])}">{esc(MON[x["day"].month - 1].capitalize())} {x["day"].year}</a></li>')

    for k, xs in rows + ([("", no_name)] if no_name else []):
        nn = sum(1 for x in xs if x["kind"] == NEW)
        sl = slugs.get(k, "no-sponsor-name")
        name = labels.get(k, "No sponsor name")
        names = ("; ".join(f"{esc(n)} ({c})" for n, c in sorted(printed[k].items(), key=lambda kv: (-kv[1], kv[0])))
                 if k else "")
        crl = (f' &middot; <a href="/crl/company/{esc(slug_of(k))}">its released Complete Response Letters</a>'
               if k and slug_of(k) in crl_pages else "")
        B.append(f'<h3 id="{esc(sl)}" data-group="{esc(sl)}">{esc(name)}</h3>'
                 f'<p class="sub">{pl(nn, "original approval", "original approvals")}, '
                 f'{pl(len(xs) - nn, "efficacy supplement", "efficacy supplements")}'
                 + (f". Sponsor names in Drugs@FDA: {names}" if names else "") + f".{crl}</p>"
                 f'<ul style="line-height:1.75">{"".join(line(x) for x in reversed(xs))}</ul>')
    B.append('<p class="sub">Facts only: counts and dates from Drugs@FDA, with no view on any company or outcome. '
             '<a href="/fda-approvals">FDA approvals by month</a> &middot; <a href="/crl/companies">Complete Response '
             'Letters by company</a> &middot; <a href="/research">research</a></p>')

    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": "FDA drug approvals by company since January 2025",
          "description": (f"{n_all:,} FDA approvals in Drugs@FDA with action dates from {first_day.isoformat()} to "
                          f"{last_day.isoformat()} ({n_new:,} original NDA and BLA approvals, {n_eff:,} efficacy "
                          f"supplement approvals), grouped by the sponsor name Drugs@FDA lists, each with its "
                          f"application, submission, action date and FDA letter."),
          "url": BASE + canon, "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
          "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"},
          "isBasedOn": "https://open.fda.gov/apis/drug/drugsfda/",
          "temporalCoverage": f"{first_day.isoformat()}/{last_day.isoformat()}", "dateModified": reads[-1],
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                            "contentUrl": BASE + "/fda-approvals/data/approvals-by-company.csv"}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "FDA approvals by month", "item": BASE + "/fda-approvals"},
        {"@type": "ListItem", "position": 3, "name": "By company", "item": BASE + canon}]}
    extra = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False, separators=(",", ":"))}'
                    f'</script>' for o in (ld, crumbs))
    tpl = io.open(os.path.join(SITE, "methodology", "index.html"), encoding="utf-8").read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(head(tpl, title, desc, canon, extra, '<div class="bc"><a href="/">Home</a> › '
                                             '<a href="/fda-approvals">FDA approvals</a> › By company</div>') + "".join(B) + foot(tpl))

    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(CSV_COLS)
        for k, xs in rows + ([("", no_name)] if no_name else []):
            for x in xs:
                w.writerow([labels.get(k, ""), x["sponsor"], x["app"], x["sub"], x["kind"], x.get("class") or "",
                            x["day"].isoformat(), x.get("brand") or "", x.get("generic") or "", x.get("letter") or "",
                            x["read"], BASE + x["month_page"]])

    # a link from the same group's CRL company page. Link only, no count: the two lists come from different FDA files
    # and periods, and another spelling of the company's name can sit in another group (red team 2026-11-23).
    by_slug = {slug_of(k): k for k in groups}      # key_of leaves letters, digits and single spaces: one slug a key
    linked = 0
    for p in sorted(glob.glob(os.path.join(CRL_CO, "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8").read()
        doc = re.sub(r"<!--APPROVALS:BEGIN-->.*?<!--APPROVALS:END-->", "", doc, flags=re.S)
        k = by_slug.get(slug)
        if k is not None:
            block = (f'<!--APPROVALS:BEGIN--><p class="sub" data-approvals="{esc(slug)}">The same sponsor-name group '
                     f'in Drugs@FDA, a different FDA file: <a href="/fda-approvals/companies#{esc(slugs[k])}">its '
                     f'approvals since January 2025</a>, each with its FDA letter.</p><!--APPROVALS:END-->')
            anchor = '<p class="sub"><a href="/crl/companies">Every company in the release</a>'
            if anchor in doc:
                doc = doc.replace(anchor, block + anchor, 1)
                linked += 1
        io.open(p, "w", encoding="utf-8").write(doc)
    print(f"/fda-approvals/companies: {n_all:,} approvals ({n_new:,} new, {n_eff:,} efficacy) across {len(rows):,} "
          f"companies, {multi:,} with more than one; {len(no_name)} with no name; {linked} CRL company pages linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
