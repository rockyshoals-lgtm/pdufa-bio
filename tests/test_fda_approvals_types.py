# -*- coding: utf-8 -*-
"""CI guard: /fda-approvals/types and its CSV match the Drugs@FDA cache they are built from.

2026-11-25 (moat round, David: "Continue building moat and red team everything"). Recounts
_fda_approvals_months.json on its own (no import of the builder) and checks against the built page:
  * the lede's total of original approvals, first and last action dates, the count with a code and the Type 1 count
  * the code table: every code group's count per year and in total, and the all-approvals row, equal the recount
  * every original approval is listed under each code its printed class names (once per code), blank and non-MAPP
    classes under their own headings, and nothing else is listed
  * the CSV holds every original approval once, its printed class and codes equal to the cache's
  * the page links the FDA's MAPP 5018.2 and carries a Dataset JSON-LD with CC BY 4.0 and the CSV
  * the title and description fit, and the workflow builds the page and force-adds the CSV (*.csv is ignored)
  * no rate, odds, percentage or causal wording in the page's own text (the site-wide link bar is left out)

    python tests/test_fda_approvals_types.py          (PLANT=1..3 plant an error; the guard must fail)
"""
import collections
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "_fda_approvals_months.json")
PAGE = os.path.join(SITE, "fda-approvals", "types", "index.html")
CSVF = os.path.join(SITE, "fda-approvals", "data", "approvals-by-type.csv")
WORKFLOW = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")
MAPP = "https://www.fda.gov/media/94381/download"
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
       "December"]
ORDER = ["1", "2", "3", "4", "5", "7", "8", "9", "10", "gas"]
BAD = re.compile(r"%|\b(rate|rates|odds|likel\w*|predict\w*|chance\w*|probab\w*|success\w*|reject\w*|score\w*|"
                 r"led to|leads? to|delay\w*|because|caus\w*|due to|better|worse|innovative)\b", re.I)


def text(doc):
    doc = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc))).strip()


def codes(printed):
    p = str(printed or "")
    got = set(re.findall(r"\bType (\d+)\b", p))
    if not got:
        if "New Combination" in p:
            got.add("4")
        if "New Formulation" in p or "New Manufacturer" in p:
            got.add("5")
        if p.strip() == "Medical Gas":
            got.add("gas")
    return [c for c in ORDER if c in got]


def groups_of(x):
    cs = codes(x.get("class"))
    if cs:
        return cs
    p = str(x.get("class") or "").strip()
    return ["printed:" + p] if p else ["none"]


def long_day(d):
    return f"{MON[d.month - 1]} {d.day}, {d.year}"


def main():
    if not os.path.exists(CACHE):
        print("  SKIP the approvals cache is missing")
        return 0
    if not os.path.exists(PAGE):
        print("FAIL test_fda_approvals_types: /fda-approvals/types was not built; fix: python build_fda_approvals_types.py")
        return 1
    fails = []
    raw = json.load(io.open(CACHE, encoding="utf-8"))
    seen, orig = set(), []
    for m in sorted(raw):
        for it in raw[m].get("items") or []:
            k = (it["app"], it["sub"])
            if k not in seen and it.get("date"):
                seen.add(k)
                if it.get("kind") == "new application":
                    orig.append(dict(it, day=dt.date.fromisoformat(it["date"])))
    orig.sort(key=lambda x: (x["day"], x["app"], x["sub"]))
    doc = io.open(PAGE, encoding="utf-8").read()
    plant = os.environ.get("PLANT", "")
    if plant == "1":   # a code group's total off by one
        doc = re.sub(r'(<tr data-code="1">.*?<td>)(\d+)(</td></tr>)', lambda m: m.group(1) + str(int(m.group(2)) + 1)
                     + m.group(3), doc, count=1, flags=re.S)
    if plant == "2":   # one approval dropped from its list
        doc = re.sub(r'<li data-sub="[^"]*">.*?</li>', "", doc, count=1, flags=re.S)
    if plant == "3":   # forbidden wording in the page's own text
        doc = doc.replace("</h1>", "</h1><p>approval odds</p>", 1)
    years = sorted({x["day"].year for x in orig})
    grp = collections.defaultdict(list)
    for x in orig:
        for g in groups_of(x):
            grp[g].append(x)

    # ---- lede --------------------------------------------------------------------------------------------------------
    t = text(doc[doc.index("<h1"):])
    coded = sum(1 for x in orig if codes(x.get("class")))
    for want in (f"lists {len(orig):,} original", f"from {long_day(orig[0]['day'])} to {long_day(orig[-1]['day'])}",
                 f"on {coded:,} of them", f"is on {len(grp.get('1', [])):,}:"):
        if want not in t:
            fails.append(f"lede does not say {want!r}")

    # ---- table -------------------------------------------------------------------------------------------------------
    rows = dict(re.findall(r'<tr data-code="([^"]+)">(.*?)</tr>', doc, re.S))
    for g, xs in grp.items():
        r = rows.get(g)
        if r is None:
            fails.append(f"code group {g} ({len(xs)} approvals) has no table row")
            continue
        nums = [int(n) for n in re.findall(r"<td>(\d+)</td>", r)]
        want = [sum(1 for x in xs if x["day"].year == y) for y in years] + [len(xs)]
        if nums[-len(want):] != want:
            fails.append(f"table row {g}: {nums[-len(want):]} on the page, {want} in the cache")
    for g in rows:
        if g != "all" and g not in grp:
            fails.append(f"table row {g} has no approval in the cache")
    allr = [int(n) for n in re.findall(r"<td>(\d+)</td>", rows.get("all", ""))]
    want_all = [sum(1 for x in orig if x["day"].year == y) for y in years] + [len(orig)]
    if allr != want_all:
        fails.append(f"all-approvals row {allr} on the page, {want_all} in the cache")

    # ---- lists -------------------------------------------------------------------------------------------------------
    sections = re.findall(r'<h2 id="[^"]*" data-group="([^"]+)">.*?</h2><ul[^>]*>(.*?)</ul>', doc, re.S)
    listed = {html.unescape(g): collections.Counter(re.findall(r'<li data-sub="([^"]+)">', body))
              for g, body in sections}
    for g, xs in grp.items():
        want = collections.Counter(f"{x['app']} {x['sub']}" for x in xs)
        got = listed.get(g, collections.Counter())
        if got != want:
            miss = sorted((want - got).elements())[:3]
            extra = sorted((got - want).elements())[:3]
            fails.append(f"list {g}: missing {miss}, extra {extra}")
    for g in listed:
        if g not in grp:
            fails.append(f"list {g} on the page has no approval in the cache")

    # ---- CSV ---------------------------------------------------------------------------------------------------------
    if not os.path.exists(CSVF):
        fails.append("approvals-by-type.csv was not written")
    else:
        got = {}
        for r in csv.DictReader(io.open(CSVF, encoding="utf-8")):
            k = (r["application"].replace(" ", ""), r["submission"])
            if k in got:
                fails.append(f"CSV lists {k} twice")
            got[k] = r
        for x in orig:
            r = got.get((x["app"], x["sub"]))
            if not r:
                fails.append(f"CSV is missing {x['app']} {x['sub']}")
                continue
            if r["classification_as_printed"] != (x.get("class") or "") or r["codes"] != ";".join(codes(x.get("class"))) \
                    or r["action_date"] != x["date"]:
                fails.append(f"CSV row {x['app']} {x['sub']} differs from the cache")
        if len(got) != len(orig):
            fails.append(f"CSV has {len(got)} rows, the cache {len(orig)} original approvals")

    # ---- page furniture ----------------------------------------------------------------------------------------------
    if MAPP not in doc:
        fails.append("the page does not link the FDA's MAPP 5018.2")
    lds = [json.loads(s) for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)]
    ds = next((o for o in lds if o.get("@type") == "Dataset"), None)
    if not ds or "creativecommons.org/licenses/by/4.0" not in str(ds.get("license")) or \
            "approvals-by-type.csv" not in json.dumps(ds):
        fails.append("Dataset JSON-LD missing, or without CC BY 4.0 and the CSV")
    t_ = re.search(r"<title>(.*?)</title>", doc, re.S)
    d_ = re.search(r'<meta name="description" content="([^"]*)"', doc)
    if not t_ or len(html.unescape(t_.group(1))) > 70:
        fails.append(f"title too long: {t_.group(1) if t_ else None!r}")
    if not d_ or not 70 <= len(html.unescape(d_.group(1))) <= 158:
        fails.append(f"description length {len(d_.group(1)) if d_ else 0}")
    wf = io.open(WORKFLOW, encoding="utf-8").read() if os.path.exists(WORKFLOW) else ""
    if "python build_fda_approvals_types.py" not in wf:
        fails.append("the workflow does not run build_fda_approvals_types.py")
    if "git add -f pdufa_site_src/fda-approvals/data/approvals-by-type.csv" not in wf:
        fails.append("the workflow does not force-add approvals-by-type.csv; *.csv is ignored, so it would 404 live")

    # ---- words (the site-wide link bar names other pages and is left out) ----------------------------------------------
    main_ = re.sub(r"(?s)<!--SITELINKS:BEGIN-->.*?<!--SITELINKS:END-->", "", doc)
    body = text(main_[main_.index("<h1"):main_.index("<footer") if "<footer" in main_ else len(main_)])
    for m in BAD.finditer(body):
        fails.append(f"forbidden word on the page: {body[max(0, m.start() - 40):m.end() + 40]!r}")

    if fails:
        print(f"FAIL test_fda_approvals_types: {len(fails)} problem(s); fix: python build_fda_approvals_types.py")
        for f in fails[:40]:
            print("   " + f)
        return 1
    print(f"  PASS /fda-approvals/types: {len(orig)} original approvals in {len(grp)} code groups, "
          f"{len(grp.get('1', []))} Type 1; table, lists, CSV and JSON-LD match the cache")
    return 0


if __name__ == "__main__":
    sys.exit(main())
