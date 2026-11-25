# -*- coding: utf-8 -*-
"""build_fda_approvals_types.py -- /fda-approvals/types: Drugs@FDA original approvals since January 2025, by the NDA
classification code ("chemical type") Drugs@FDA prints for each.

David, 2026-11-25 06:08 UTC (Nov 25, 1:08 AM ET): "Continue building moat and red team everything".

Drugs@FDA prints a classification code on most original NDA approvals: Type 1 (new molecular entity), Type 3 (new
dosage form), Type 5 (new formulation or manufacturer) and so on, defined in the FDA's MAPP 5018.2 "NDA Classification
Codes". Nobody lists the approvals since 2025 under those codes with a count per year. This page does:

  * /fda-approvals/types: each code with its meaning (paraphrased from MAPP 5018.2, which is linked), how many original
    approvals in Drugs@FDA carry it in 2025 and in 2026 to date, and every one of those approvals with its FDA letter
  * /fda-approvals/data/approvals-by-type.csv: one row per original approval, CC BY 4.0

Source: _fda_approvals_months.json, which build_fda_approvals_months.py fills from openFDA drugsfda (no fetching here).
An approval whose printed class names two codes ("Type 1 - New Molecular Entity and Type 4 - New Combination") is listed
under each code and counted once in the totals. A class Drugs@FDA leaves blank, or prints as something that is not one
of the MAPP codes, is listed as printed.

FACTS ONLY: codes, counts and dates as Drugs@FDA prints them. No view on any drug, company or outcome, and no claim
about the FDA's separate novel drug approvals list.

    python build_fda_approvals_types.py
"""
import collections
import csv
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

OUT = os.path.join(SITE, "fda-approvals", "types", "index.html")
CSV_OUT = os.path.join(SITE, "fda-approvals", "data", "approvals-by-type.csv")
CANON = "/fda-approvals/types"
MAPP = "https://www.fda.gov/media/94381/download"
NOVEL = "https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda"
CSV_COLS = ["application", "brand", "generic", "sponsor_name_title_case", "submission", "action_date",
            "classification_as_printed", "codes", "fda_letter", "openfda_read_on", "month_page"]

# code -> (name as MAPP 5018.2 prints it, what it means in our words; read 2026-11-25 06:15 UTC from MAPP)
CODES = [
    ("1", "Type 1 - New Molecular Entity",
     "The drug contains an active moiety the FDA has not approved before and that has not been marketed in the US."),
    ("2", "Type 2 - New Active Ingredient",
     "A new active ingredient, such as a new salt or ester, of an active moiety that has been approved or marketed "
     "before."),
    ("3", "Type 3 - New Dosage Form",
     "An active ingredient already approved or marketed, in a dosage form that has not been."),
    ("4", "Type 4 - New Combination",
     "A new combination of two or more active ingredients in one product."),
    ("5", "Type 5 - New Formulation or Other Differences",
     "A product that differs from an approved one in a way other than its dosage form, for example its inactive "
     "ingredients, or a duplicate from another applicant or manufacturer."),
    ("7", "Type 7 - Previously Marketed Without an Approved NDA",
     "The first NDA for an active moiety that was marketed in the US without an approved application."),
    ("8", "Type 8 - Rx to OTC",
     "An over-the-counter product whose active ingredient was marketed before only by prescription."),
    ("9", "Type 9 - New Indication or Claim, Not Marketed Under This NDA",
     "A new indication or claim filed as its own NDA while another NDA for the drug is under review; the applicant "
     "does not market the drug under this one."),
    ("10", "Type 10 - New Indication or Claim, Marketed Under This NDA",
     "A duplicate of a drug under review in another NDA, normally for a new indication or claim, that the applicant "
     "markets under this NDA after approval."),
    ("gas", "Medical Gas",
     "A designated medical gas certification request under section 576 of the Federal Food, Drug, and Cosmetic Act."),
]
NAME = {c: n for c, n, _ in CODES}
ORDER = [c for c, _, _ in CODES]
NONE_KEY = "none"
NONE_LABEL = "No classification code printed"


def codes_of(printed):
    """The MAPP codes a printed class names, in code order: 'Type 1 - ... and Type 4 - ...' -> ['1', '4']."""
    p = str(printed or "")
    got = set(re.findall(r"\bType (\d+)\b", p))
    if not got:   # Drugs@FDA once prints the names without numbers
        if "New Combination" in p:
            got.add("4")
        if "New Formulation" in p or "New Manufacturer" in p:
            got.add("5")
        if p.strip() == "Medical Gas":
            got.add("gas")
    return [c for c in ORDER if c in got]


def key_of(x):
    cs = codes_of(x.get("class"))
    if cs:
        return cs
    p = str(x.get("class") or "").strip()
    return [("printed:" + p) if p else NONE_KEY]


def app_label(app):
    m = re.match(r"([A-Z]+)(\d+)$", app or "")
    return f"{m.group(1)} {m.group(2)}" if m else str(app or "")


def https(u):
    return re.sub(r"^http://", "https://", str(u or ""))


def anchor(k):
    return "type-" + re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-")


def main():
    if not os.path.exists(CACHE):
        print("no _fda_approvals_months.json; nothing to build")
        return 0
    items, months, fetched = load()
    orig = [x for x in items if x["kind"] == NEW]
    if not orig:
        print("no original approvals in the cache; nothing to build")
        return 0
    groups = collections.defaultdict(list)
    for x in orig:
        for k in key_of(x):
            groups[k].append(x)
    years = sorted({x["day"].year for x in orig})
    first_day, last_day = orig[0]["day"], orig[-1]["day"]
    reads = sorted(set(fetched.values()))
    read_txt = (f"read from openFDA on {reads[0]}" if len(reads) == 1 else
                f"read from openFDA between {reads[0]} and {reads[-1]} (each approval's read date is in the CSV's "
                f"openfda_read_on column)")
    other = sorted(k for k in groups if k not in ORDER)
    keys = [c for c in ORDER if c in groups] + other

    def label(k):
        if k in NAME:
            return NAME[k]
        if k == NONE_KEY:
            return NONE_LABEL
        return f'Printed as "{k.split(":", 1)[1]}"'

    def per_year(xs):
        return {y: sum(1 for x in xs if x["day"].year == y) for y in years}

    multi = [x for x in orig if len(key_of(x)) > 1]
    bla_coded = sum(1 for x in orig if x["app"].startswith("BLA") and codes_of(x.get("class")))
    blank_bla = sum(1 for x in orig if x["app"].startswith("BLA") and not str(x.get("class") or "").strip())
    blank_nda = sum(1 for x in orig if not x["app"].startswith("BLA") and not str(x.get("class") or "").strip())
    eff_orig = sum(1 for x in orig if str(x.get("class") or "").strip() == "Efficacy")
    n1 = per_year(groups.get("1", []))
    ytxt = " and ".join(f"{n1[y]:,} in {y}" + (f" (through {pretty(last_day)})" if y == last_day.year else "")
                        for y in years)
    lede = (f"Drugs@FDA lists {pl(len(orig), 'original NDA or BLA approval', 'original NDA and BLA approvals')} with "
            f"action dates from {pretty(first_day)} to {pretty(last_day)}. It prints an NDA classification code (the "
            f"\"chemical type\" in the FDA's Drugs@FDA glossary) on {sum(1 for x in orig if codes_of(x.get('class'))):,} of them. "
            f"Type 1, a new molecular entity, is on {len(groups.get('1', [])):,}: {ytxt}. The most common code is "
            f"{NAME[max((c for c in ORDER if c in groups), key=lambda c: len(groups[c]))]}"
            f" ({max(len(groups[c]) for c in ORDER if c in groups):,}).")
    method = (f"Source: openFDA drugsfda (the Drugs@FDA data), {read_txt}. The codes and their meanings are the FDA's, "
              f"from its manual MAPP 5018.2, NDA Classification Codes; the meanings here are short paraphrases, and "
              f"the manual is the authority. Only original approvals carry a code; efficacy supplements, such as a new "
              f"indication on an existing application, do not and are not counted here (they are on "
              f"/fda-approvals/drugs). An approval whose code names two types, such as Type 1 and Type 4, is listed "
              f"under each, so the counts by code add up to more than the total. The manual is written for NDAs; "
              f"Drugs@FDA prints the same codes on {pl(bla_coded, 'original BLA approval', 'original BLA approvals')} "
              f"too. It leaves the class blank on {pl(blank_bla, 'BLA', 'BLAs')} and {pl(blank_nda, 'NDA', 'NDAs')}"
              + (f", and prints \"Efficacy\" as the class of {pl(eff_orig, 'original approval', 'original approvals')}"
                 if eff_orig else "")
              + f"; those are listed as printed. Drugs@FDA covers what the FDA's drug "
              f"center (CDER) reviews; vaccines and cell and gene therapies, reviewed by the biologics center, are not "
              f"in it. openFDA trails Drugs@FDA by about a week, so the latest days can be missing until the next read. "
              f"The FDA keeps its own list of novel drug approvals, which is a separate list; this page does not "
              f"reproduce it.")
    title = f"FDA Approvals by NDA Type Since 2025 ({len(orig):,} Originals) | pdufa.bio"
    desc = (f"Every original FDA approval in Drugs@FDA since January 2025 under its NDA classification code: Type 1 "
            f"new molecular entity, Type 3 new dosage form and more.")
    if len(desc) > 158:
        desc = desc[:155].rsplit(" ", 1)[0] + "."

    yh = "".join(f"<th>{y}{' to date' if y == last_day.year else ''}</th>" for y in years)
    B = ['<h1>FDA approvals by NDA classification code, since January 2025</h1>',
         f'<p class="sub" data-atype="lede" style="color:#cfe0f5">{esc(lede)}</p>',
         f'<p class="sub" data-atype="method" style="font-size:13px">{esc(method)} The FDA\'s manual: '
         f'<a href="{MAPP}" rel="noopener">MAPP 5018.2, NDA Classification Codes</a>; the FDA\'s own list: '
         f'<a href="{NOVEL}" rel="noopener">Novel Drug Approvals at FDA</a>.</p>',
         '<p class="sub">Every original approval, one row each: <a href="/fda-approvals/data/approvals-by-type.csv">CSV'
         '</a>, free under CC BY 4.0: cite pdufa.bio and link this page. By month: <a href="/fda-approvals">FDA '
         'approvals by month</a> &middot; by sponsor: <a href="/fda-approvals/companies">by company</a> &middot; by '
         'application: <a href="/fda-approvals/drugs">by drug</a></p>',
         f'<table data-atype="table"><tr><th>Code</th><th>What the FDA\'s manual says it means</th>{yh}<th>Total</th>'
         f'</tr>']
    for k in keys:
        xs = groups[k]
        py = per_year(xs)
        meaning = next((m for c, _, m in CODES if c == k),
                       "Drugs@FDA leaves the class blank." if k == NONE_KEY else
                       "Printed by Drugs@FDA as the class of these original approvals; not one of the codes in MAPP "
                       "5018.2.")
        B.append(f'<tr data-code="{esc(k)}"><td><a href="#{anchor(k)}">{esc(label(k))}</a></td><td>{esc(meaning)}</td>'
                 + "".join(f"<td>{py[y]}</td>" for y in years) + f"<td>{len(xs)}</td></tr>")
    B.append(f'<tr data-code="all"><td><b>All original approvals</b></td><td>Each counted once.</td>'
             + "".join(f"<td>{sum(1 for x in orig if x['day'].year == y)}</td>" for y in years)
             + f"<td>{len(orig)}</td></tr></table>")
    if multi:
        B.append(f'<p class="sub">{pl(len(multi), "approval carries", "approvals carry")} two codes and '
                 f'{"is" if len(multi) == 1 else "are"} listed under each.</p>')

    def line(x, k):
        lt = f' <a href="{esc(https(x["letter"]))}" rel="noopener">FDA letter</a>' if x.get("letter") else ""
        also = [c for c in codes_of(x.get("class")) if c != k]
        al = f' (also {", ".join(NAME[c].split(" - ")[0] for c in also)})' if also else ""
        return (f'<li data-sub="{esc(x["app"])} {esc(x["sub"])}"><b>{esc(short_day(x["day"]))}:</b> {who(x)}, '
                f'{esc(app_label(x["app"]))}, {esc(x["sponsor"])}{esc(al)}.{lt} &middot; '
                f'<a href="{esc(x["month_page"])}">{esc(MON[x["day"].month - 1].capitalize())} {x["day"].year}</a></li>')

    for k in keys:
        xs = groups[k]
        B.append(f'<h2 id="{anchor(k)}" data-group="{esc(k)}">{esc(label(k))} ({len(xs)})</h2>'
                 f'<ul style="line-height:1.75">{"".join(line(x, k) for x in reversed(xs))}</ul>')
    B.append('<p class="sub">Facts only: codes, counts and dates as Drugs@FDA prints them, with no view on any drug, '
             'company or outcome. <a href="/fda-approvals">FDA approvals by month</a> &middot; '
             '<a href="/fda-approvals/drugs">by drug</a> &middot; <a href="/fda-approvals/companies">by company</a> '
             '&middot; <a href="/crl">CRL database</a></p>')

    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": "FDA original drug approvals by NDA classification code since January 2025",
          "description": (f"{len(orig):,} original NDA and BLA approvals in Drugs@FDA with action dates from "
                          f"{first_day.isoformat()} to {last_day.isoformat()}, each with the NDA classification code "
                          f"(chemical type) Drugs@FDA prints, its action date and FDA letter."),
          "url": BASE + CANON, "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
          "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"},
          "isBasedOn": ["https://open.fda.gov/apis/drug/drugsfda/", MAPP],
          "temporalCoverage": f"{first_day.isoformat()}/{last_day.isoformat()}", "dateModified": reads[-1],
          "identifier": BASE + "/fda-approvals/data/approvals-by-type.csv",
          "keywords": ["FDA approvals", "Drugs@FDA", "NDA classification code", "chemical type",
                       "new molecular entity", "Type 1 NDA"],
          "variableMeasured": ["application", "submission", "action date", "NDA classification code as printed",
                               "FDA letter"],
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                            "contentUrl": BASE + "/fda-approvals/data/approvals-by-type.csv"}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "FDA approvals", "item": BASE + "/fda-approvals"},
        {"@type": "ListItem", "position": 3, "name": "By NDA type", "item": BASE + CANON}]}
    extra = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False, separators=(",", ":"))}'
                    f'</script>' for o in (ld, crumbs))
    tpl = io.open(os.path.join(SITE, "methodology", "index.html"), encoding="utf-8").read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(head(tpl, title, desc, CANON, extra, '<div class="bc"><a href="/">Home</a> › '
                                             '<a href="/fda-approvals">FDA approvals</a> › By NDA type</div>')
                                             + "".join(B) + foot(tpl))

    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(CSV_COLS)
        for x in orig:
            w.writerow([app_label(x["app"]), x.get("brand") or "", x.get("generic") or "", x["sponsor"], x["sub"],
                        x["day"].isoformat(), x.get("class") or "", ";".join(codes_of(x.get("class"))),
                        https(x.get("letter")), x["read"], BASE + x["month_page"]])
    print(f"{CANON}: {len(orig)} original approvals, {len(groups.get('1', []))} Type 1, {len(keys)} groups, "
          f"{len(multi)} with two codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
