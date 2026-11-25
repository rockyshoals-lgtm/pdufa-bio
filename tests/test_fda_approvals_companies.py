# -*- coding: utf-8 -*-
"""CI guard: /fda-approvals/companies, its CSV and the approvals line on each /crl/company page match the cache.

2026-11-23 (moat round). Recounts _fda_approvals_months.json (the Drugs@FDA approvals the month pages list) on its own
and checks, against the built page:
  * the lede's totals, first and last action dates, company counts and read dates
  * every approval in the cache appears exactly once on the page, under the company whose grouping key its sponsor
    has, and nothing else is listed; each company's table row counts its listed approvals by kind
  * the CSV holds every approval once, every column equal to the cache's
  * the Dataset JSON-LD carries the totals, dates, CC BY 4.0 and the CSV
  * each /crl/company page names its group's approvals exactly when the group has any, with the cache's counts, and
    links an anchor that exists
  * the grouping rule's spot cases, and no rate, odds or percentage anywhere on the page

    python tests/test_fda_approvals_companies.py          (PLANT=1..4 plant an error; the guard must fail)
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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_companies import key_of, slug_of  # noqa: E402

CACHE = os.path.join(HERE, "_fda_approvals_months.json")
PAGE = os.path.join(SITE, "fda-approvals", "companies", "index.html")
CSVF = os.path.join(SITE, "fda-approvals", "data", "approvals-by-company.csv")
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
       "December"]
BAD = re.compile(r"%|\b(rate|rates|odds|likel\w*|predict\w*|chance\w*|probab\w*|success\w*|reject\w*|score\w*)\b", re.I)


def text(doc):
    doc = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc))).strip()


def long_day(d):
    return f"{MON[d.month - 1]} {d.day}, {d.year}"


def main():
    if not os.path.exists(CACHE):
        print("  SKIP the approvals cache is missing")
        return 0
    if not os.path.exists(PAGE):
        print("FAIL test_fda_approvals_companies: /fda-approvals/companies was not built; fix: python build_fda_approvals_companies.py")
        return 1
    fails = []
    raw = json.load(io.open(CACHE, encoding="utf-8"))
    seen, rows = set(), []
    for m in sorted(raw):
        for it in raw[m].get("items") or []:
            k = (it["app"], it["sub"])
            if k not in seen and it.get("date"):
                seen.add(k)
                rows.append(dict(it, read=str(raw[m].get("fetched") or "")[:10]))
    reads = sorted({str(v.get("fetched") or "")[:10] for v in raw.values()})
    doc = io.open(PAGE, encoding="utf-8").read()
    plant = os.environ.get("PLANT", "")
    if plant == "1":                                    # one approval dropped from the page
        doc = re.sub(r'<li data-app="[^"]+">.*?</li>', "", doc, count=1, flags=re.S)
    if plant == "2":                                    # a table count off by one
        doc = re.sub(r'(<tr data-key="[^"]+"><td>.*?</td><td>)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 1),
                     doc, count=1)
    if plant == "3":                                    # the lede's total off by one
        doc = doc.replace(f"lists {len(rows):,} FDA approvals", f"lists {len(rows) + 1:,} FDA approvals", 1)

    # ---- lede -------------------------------------------------------------------------------------------------------
    days = sorted(dt.date.fromisoformat(r["date"]) for r in rows)
    n_new = sum(1 for r in rows if r["kind"] == "new application")
    groups = collections.defaultdict(list)
    for r in rows:
        groups[key_of(r["sponsor"])].append(r)
    named = {k: v for k, v in groups.items() if k}
    multi = sum(1 for v in named.values() if len(v) > 1)
    lede = text((re.search(r'data-acomp="lede"[^>]*>(.*?)</p>', doc, re.S) or [None, ""])[1])
    n_apps = len({r["app"] for r in rows if r["kind"] == "new application"})
    for want in (f"lists {len(rows):,} FDA approvals with action dates from {long_day(days[0])} to {long_day(days[-1])}: "
                 f"{n_new:,} original approval", f"new drug and biologic applications ({n_apps:,} application",
                 f") and {len(rows) - n_new:,} efficacy supplement", f"under {len(named):,} sponsor-name group",
                 f"; {multi:,} group"):
        if want not in lede:
            fails.append(f"lede: missing {want!r}")
    for tag, want in ((r"<title>(.*?)</title>", f"FDA Approvals by Company Since 2025: {len(rows):,} Drugs@FDA Approvals"),
                      (r'<meta name="twitter:title" content="([^"]*)"', "FDA Approvals by Company Since 2025"),
                      (r'<link rel="canonical" href="([^"]*)"', "https://www.pdufa.bio/fda-approvals/companies")):
        m = re.search(tag, doc)
        if not (m and m.group(1).startswith(want)):
            fails.append(f"head: {tag[:24]} is {(m.group(1) if m else None)!r}")
    if "Methodology" in doc[:doc.index("<h1")].split("<title>")[1].split("</title>")[0] or re.search(
            r'<div class="bc">[^<]*<a href="/">Home</a> › Methodology', doc):
        fails.append("head: the methodology template's title or breadcrumb is left in")
    method = text((re.search(r'data-acomp="method"[^>]*>(.*?)</p>', doc, re.S) or [None, ""])[1])
    rd = f"on {reads[0]}" if len(reads) == 1 else f"between {reads[0]} and {reads[-1]}"
    if rd not in method:
        fails.append(f"method: read dates {rd!r} missing")

    # ---- every approval once, under its company ------------------------------------------------------------------
    sections = re.findall(r'<h3 id="([^"]+)" data-group="[^"]*">(.*?)</h3>(.*?)</ul>', doc, re.S)
    ids = [s[0] for s in sections]
    if len(ids) != len(set(ids)):
        fails.append("two company sections share an anchor")
    by_app = {(r["app"], r["sub"]): r for r in rows}
    listed = collections.Counter()
    sec_of = {}
    for sid, _name, body in sections:
        apps = re.findall(r'<li data-app="([^"]+)">(.*?)</li>', body, re.S)
        keys = set()
        for a, li in apps:
            app, sub = a.rsplit(" ", 1)
            r_ = by_app.get((app, sub))
            if r_:
                d = dt.date.fromisoformat(r_["date"])
                t = text(li)
                kind = "original approval" if r_["kind"] == "new application" else "efficacy supplement"
                if not (t.startswith(f"{MON[d.month - 1][:3]} {d.day}, {d.year}:") and f"{app} {sub}, {kind}" in t
                        and f'href="/fda-approvals/{d.year}/{MON[d.month - 1].lower()}"' in li
                        and ((r_.get("letter") or "") == "" or f'href="{html.escape(r_["letter"], quote=True)}"' in li)):
                    fails.append(f"{sid}: the line for {a} does not read as the cache has it ({t[:80]!r})")
            listed[(app, sub)] += 1
            if (app, sub) not in by_app:
                fails.append(f"{sid}: lists {a}, which the cache does not hold")
                continue
            keys.add(key_of(by_app[(app, sub)]["sponsor"]))
            sec_of[(app, sub)] = sid
        if len(keys) > 1:
            fails.append(f"{sid}: holds sponsors of {len(keys)} grouping keys")
        elif keys:
            base = slug_of(next(iter(keys))) or "company"
            if not (sid == base or re.fullmatch(re.escape(base) + r"-\d+", sid)):
                fails.append(f"{sid}: its sponsors' key is {next(iter(keys))!r}")
    miss = [k for k in by_app if listed[k] != 1]
    if miss:
        fails.append(f"{len(miss)} approval(s) not listed exactly once, e.g. {miss[:3]}")
    if len(sections) != len(named) + (1 if "" in groups else 0):
        fails.append(f"{len(sections)} company sections for {len(named)} companies")
    for m in re.finditer(r'<tr data-key="([^"]*)"><td>(.*?)</td><td>(\d+)</td><td>(\d+)</td><td class="dt">(.*?)</td>', doc):
        sid, nn, ne = m.group(1), int(m.group(3)), int(m.group(4))
        mine = [k for k, s in sec_of.items() if s == (sid or "no-sponsor-name")]
        an = sum(1 for k in mine if by_app[k]["kind"] == "new application")
        if (nn, ne) != (an, len(mine) - an):
            fails.append(f"table row {sid}: {nn}/{ne}, the section lists {an}/{len(mine) - an}")
        if sid and f'href="#{sid}"' not in m.group(2):
            fails.append(f"table row {sid}: does not link its section")
        if mine:
            d = max(dt.date.fromisoformat(by_app[k]["date"]) for k in mine)
            if text(m.group(5)) != f"{MON[d.month - 1][:3]} {d.day}, {d.year}":
                fails.append(f"table row {sid}: latest date {text(m.group(5))!r}, the section's is {d}")
    if len(re.findall(r'<tr data-key=', doc)) != len(sections):
        fails.append("the table and the sections hold different companies")

    # ---- CSV ------------------------------------------------------------------------------------------------------
    if not os.path.exists(CSVF):
        fails.append("the CSV is missing")
    else:
        got = list(csv.DictReader(io.open(CSVF, encoding="utf-8", newline="")))
        if plant == "4" and got:
            got[0]["action_date"] = "2025-01-01"
        if len(got) != len(rows) or len({(g["application"], g["submission"]) for g in got}) != len(rows):
            fails.append(f"CSV holds {len(got)} rows for {len(rows)} approvals")
        for g in got:
            r = by_app.get((g["application"], g["submission"]))
            if not r:
                fails.append(f"CSV row {g['application']} {g['submission']} is not in the cache")
                continue
            d = dt.date.fromisoformat(r["date"])
            want = {"sponsor_name_title_case": r["sponsor"], "kind": r["kind"], "submission_class": r.get("class") or "",
                    "action_date": r["date"], "brand": r.get("brand") or "", "generic": r.get("generic") or "",
                    "fda_letter": r.get("letter") or "", "openfda_read_on": r["read"],
                    "month_page": f"https://www.pdufa.bio/fda-approvals/{d.year}/{MON[d.month - 1].lower()}"}
            bad = [c for c, v in want.items() if g.get(c) != v]
            if bad:
                fails.append(f"CSV {g['application']} {g['submission']}: {bad} differ from the cache")
                break

    # ---- Dataset JSON-LD ---------------------------------------------------------------------------------------------
    m = re.search(r'<script type="application/ld\+json">(\{"@context":"https://schema.org","@type":"Dataset".*?)</script>',
                  doc, re.S)
    ld = json.loads(m.group(1)) if m else {}
    if not (ld.get("description", "").startswith(f"{len(rows):,} FDA approvals in Drugs@FDA with action dates from "
                                                  f"{days[0].isoformat()} to {days[-1].isoformat()} ({n_new:,} original")
            and ld.get("license") == "https://creativecommons.org/licenses/by/4.0/"
            and ld.get("temporalCoverage") == f"{days[0].isoformat()}/{days[-1].isoformat()}"
            and [d.get("contentUrl") for d in ld.get("distribution", [])] ==
            ["https://www.pdufa.bio/fda-approvals/data/approvals-by-company.csv"]):
        fails.append("the Dataset schema is missing or not the cache's")

    # ---- the line on each CRL company page ---------------------------------------------------------------------------
    by_slug = {}
    for k, v in named.items():
        if slug_of(k) in by_slug:
            fails.append(f"two sponsor groups share the slug {slug_of(k)!r}")
        by_slug[slug_of(k)] = v
    n_crl = 0
    for p in glob.glob(os.path.join(SITE, "crl", "company", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        cdoc = io.open(p, encoding="utf-8").read()
        blk = re.search(r"<!--APPROVALS:BEGIN-->(.*?)<!--APPROVALS:END-->", cdoc, re.S)
        v = by_slug.get(slug)
        if not v:
            if blk:
                fails.append(f"/crl/company/{slug}: names approvals the cache does not hold for it")
            continue
        n_crl += 1
        t = text(blk.group(1)) if blk else ""
        if not t.startswith("The same sponsor-name group in Drugs@FDA") or re.search(r"\d", t.replace("2025", "")):
            fails.append(f"/crl/company/{slug}: the approvals link is missing or carries a count ({t[:90]!r})")
        a = re.search(r'href="/fda-approvals/companies#([^"]+)"', blk.group(1)) if blk else None
        if a and a.group(1) not in ids:
            fails.append(f"/crl/company/{slug}: links #{a.group(1)}, which the page does not have")

    # ---- rule spot cases and words ------------------------------------------------------------------------------------
    for a, b, same in (("Eli Lilly And Co", "Eli Lilly Co", True), ("Genentech Inc", "Genentech", True),
                       ("Evolus Inc", "Evol", False), ("Janssen Biotech", "Janssen Pharms", False),
                       ("Bristol-Myers Squibb", "Bristol Myers Squibb", True), ("Novo Nordisk A/S", "Novo Nordisk", True)):
        if (key_of(a) == key_of(b)) != same:
            fails.append(f"grouping rule: {a!r} and {b!r} {'split' if same else 'merged'}")
    end = min([i for i in (doc.find("<!--SITELINKS:BEGIN-->"), doc.find("<footer"), doc.find('<div class="legal"'))
               if i > 0] or [len(doc)])               # the page's own words, not the site-wide links and footer
    body = text(doc[doc.index("<h1"):end])
    for w in sorted({m.group(0) for m in BAD.finditer(body)}):
        fails.append(f"the page says {w!r}")

    if fails:
        print(f"FAIL test_fda_approvals_companies: {len(fails)} problem(s); fix: python build_fda_approvals_companies.py")
        for f in fails[:25]:
            print("  " + f)
        return 1
    print(f"PASS test_fda_approvals_companies: {len(rows):,} approvals, {len(named):,} companies, every one listed once; "
          f"CSV and {n_crl} CRL company lines agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
