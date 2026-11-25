# -*- coding: utf-8 -*-
"""CI guard: /fda-approvals/drugs, its CSV and the approvals line on each /crl/letter page match their sources.

2026-11-25 (moat round). Recounts _fda_approvals_months.json (the Drugs@FDA approvals the month pages list) and the
application numbers the /crl/letter pages print, on its own, and checks against the built page:
  * the lede's totals, first and last action dates, application counts and the most-approved application
  * every application in the cache has one table row, with its counts by kind and its latest action date, and nothing
    else is listed; every application with more than one approval lists each approval once under its own heading
  * the released-CRL cell of each row links exactly the letter pages that print that application number
  * every anchor a letter page or the table links exists on the page
  * the CSV holds every approval once, every column equal to the cache's
  * the Dataset JSON-LD carries the totals, dates, CC BY 4.0 and the CSV
  * each /crl/letter page names its application's approvals exactly when the cache has any, with the cache's counts
  * each application's heading names the sponsor on its newest approval, every FDA letter link is https, every month
    page a row links exists, the drug cell names a brand or generic wherever Drugs@FDA prints one
  * the title and description fit (title <= 70 characters with the site name, description <= 158), the read-date
    clause makes no claim about read order, and the workflow force-adds the CSV (*.csv is ignored in .gitignore)
  * no rate, odds, percentage or causal wording on the page or in the letter-page lines; every hit is reported

    python tests/test_fda_approvals_drugs.py          (PLANT=1..4 plant an error; the guard must fail)
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
CACHE = os.path.join(HERE, "_fda_approvals_months.json")
PAGE = os.path.join(SITE, "fda-approvals", "drugs", "index.html")
CSVF = os.path.join(SITE, "fda-approvals", "data", "approvals-by-drug.csv")
LETTERS = os.path.join(SITE, "crl", "letter")
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
       "December"]
BAD = re.compile(r"%|\b(rate|rates|odds|likel\w*|predict\w*|chance\w*|probab\w*|success\w*|reject\w*|score\w*|"
                 r"led to|leads? to|after a CRL|resubmit\w*|delay\w*|because|caus\w*|due to)\b", re.I)
WORKFLOW = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")
APPNO = re.compile(r"\b(NDA|BLA|BL)\s*0*(\d{5,6})\b")


def text(doc):
    doc = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc))).strip()


def long_day(d):
    return f"{MON[d.month - 1]} {d.day}, {d.year}"


def short_day(d):
    return f"{MON[d.month - 1][:3]} {d.day}, {d.year}"


def label(app):
    m = re.match(r"([A-Z]+)(\d+)$", app)
    return f"{m.group(1)} {m.group(2)}"


def main():
    if not os.path.exists(CACHE):
        print("  SKIP the approvals cache is missing")
        return 0
    if not os.path.exists(PAGE):
        print("FAIL test_fda_approvals_drugs: /fda-approvals/drugs was not built; fix: python build_fda_approvals_drugs.py")
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
    apps = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["date"], r["app"], r["sub"])):
        apps[r["app"]].append(r)

    # the letter pages, read on their own: application -> set of /crl/letter/<slug>
    letters = collections.defaultdict(set)
    letter_docs = {}
    for p in sorted(glob.glob(os.path.join(LETTERS, "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        d = io.open(p, encoding="utf-8").read()
        letter_docs[slug] = d
        if not re.search(r"-\d{4}-\d{2}-\d{2}(?:-\d+)?$", slug):
            continue
        m = re.search(r"<tr><th>Application</th><td>(.*?)</td></tr>", d, re.S)
        for kind, num in APPNO.findall(m.group(1) if m else ""):
            letters[("BLA" if kind in ("BL", "BLA") else "NDA") + num.zfill(6)].add(f"/crl/letter/{slug}")

    doc = io.open(PAGE, encoding="utf-8").read()
    plant = os.environ.get("PLANT", "")
    if plant == "1":                                    # one approval dropped from a heading's list
        doc = re.sub(r'<li data-sub="[^"]+">.*?</li>', "", doc, count=1, flags=re.S)
    if plant == "2":                                    # a table count off by one
        doc = re.sub(r'(<tr data-app="[^"]+"[^>]*><td>.*?</td><td>[^<]*</td><td>)(\d+)',
                     lambda m: m.group(1) + str(int(m.group(2)) + 1), doc, count=1)
    if plant == "3":                                    # the lede's total off by one
        doc = doc.replace(f"lists {len(rows):,} FDA approvals", f"lists {len(rows) + 1:,} FDA approvals", 1)
    if plant == "4":                                    # a CRL link dropped from a row
        doc = re.sub(r'(<tr data-app="[^"]+"[^>]*>(?:<td>.*?</td>){5}<td>)<a href="/crl/letter/[^"]+">[^<]+</a>(, )?',
                     r"\1", doc, count=1)

    # ---- lede -------------------------------------------------------------------------------------------------------
    days = sorted(dt.date.fromisoformat(r["date"]) for r in rows)
    n_new = sum(1 for r in rows if r["kind"] == "new application")
    multi = [a for a, xs in apps.items() if len(xs) > 1]
    with_crl = [a for a in apps if letters.get(a)]
    lede = text(re.search(r'<p class="sub" data-adrug="lede"[^>]*>(.*?)</p>', doc, re.S).group(1))
    want = [f"lists {len(rows):,} FDA approvals", f"from {long_day(days[0])} to {long_day(days[-1])}",
            f"on {len(apps):,} applications", f"{n_new:,} original approval", f"{len(rows) - n_new:,} efficacy supplement",
            f"{len(multi):,} application", f"for {len(with_crl):,} of these applications"]
    top = max(len(xs) for xs in apps.values())
    if top > 1:
        want.append(f"the most is {top}, on")
        want += [label(a) for a, xs in apps.items() if len(xs) == top]
    for w in want:
        if w not in lede:
            fails.append(f"the lede does not say {w!r}")

    # ---- table ------------------------------------------------------------------------------------------------------
    tbl = {}
    for m in re.finditer(r'<tr data-app="([^"]+)"[^>]*>(.*?)</tr>', doc, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)
        if m.group(1) in tbl:
            fails.append(f"{m.group(1)} has two table rows")
        tbl[m.group(1)] = cells
    if set(tbl) != set(apps):
        fails.append(f"table rows {len(tbl)} vs cache applications {len(apps)}: missing "
                     f"{sorted(set(apps) - set(tbl))[:5]}, extra {sorted(set(tbl) - set(apps))[:5]}")
    for a, cells in tbl.items():
        xs = apps.get(a)
        if not xs or len(cells) != 6:
            continue
        nn = sum(1 for x in xs if x["kind"] == "new application")
        if text(cells[1]) != label(a):
            fails.append(f"{a}: application cell {text(cells[1])!r}")
        if (text(cells[2]), text(cells[3])) != (str(nn), str(len(xs) - nn)):
            fails.append(f"{a}: counts {text(cells[2])}/{text(cells[3])}, cache {nn}/{len(xs) - nn}")
        if text(cells[4]) != short_day(dt.date.fromisoformat(xs[-1]["date"])):
            fails.append(f"{a}: latest {text(cells[4])!r}, cache {xs[-1]['date']}")
        got = set(re.findall(r'href="(/crl/letter/[^"]+)"', cells[5]))
        if got != letters.get(a, set()):
            fails.append(f"{a}: CRL cell links {sorted(got)}, letter pages print it on {sorted(letters.get(a, set()))}")

    # ---- per-application lists ----------------------------------------------------------------------------------------
    listed = collections.Counter(re.findall(r'<li data-sub="([^"]+)">', doc))
    want_li = collections.Counter(f'{x["app"]} {x["sub"]}' for a in multi for x in apps[a])
    if listed != want_li:
        fails.append(f"listed approvals differ from the cache's multi-approval applications: missing "
                     f"{sorted((want_li - listed).elements())[:5]}, extra {sorted((listed - want_li).elements())[:5]}")
    ids = set(re.findall(r'\sid="([^"]+)"', doc))
    for a in apps:
        if re.sub(r"[^a-z0-9]", "", a.lower()) not in ids:
            fails.append(f"{a}: no anchor on the page")
    for h in re.findall(r'href="#([^"]+)"', doc):
        if h not in ids:
            fails.append(f"in-page link #{h} has no anchor")

    # ---- CSV --------------------------------------------------------------------------------------------------------
    with io.open(CSVF, encoding="utf-8", newline="") as f:
        cr = list(csv.DictReader(f))
    by = {(r["application"], r["submission"]): r for r in cr}
    if len(cr) != len(rows) or len(by) != len(rows):
        fails.append(f"CSV rows {len(cr)} (unique {len(by)}) vs cache {len(rows)}")
    for r in rows:
        c = by.get((label(r["app"]), r["sub"]))
        if not c:
            fails.append(f"CSV lacks {r['app']} {r['sub']}")
            continue
        exp = {"brand": r.get("brand") or "", "generic": r.get("generic") or "", "sponsor_name_title_case": r["sponsor"],
               "kind": r["kind"], "submission_class": r.get("class") or "", "action_date": r["date"],
               "fda_letter": re.sub(r"^http://", "https://", r.get("letter") or ""), "approvals_on_application_since_2025": str(len(apps[r["app"]])),
               "openfda_read_on": r["read"],
               "released_crl_letters_same_application": "; ".join(sorted("https://www.pdufa.bio" + u
                                                                         for u in letters.get(r["app"], set())))}
        got = dict(c)
        got["released_crl_letters_same_application"] = "; ".join(sorted(
            x for x in got["released_crl_letters_same_application"].split("; ") if x))
        for k, v in exp.items():
            if got.get(k) != v:
                fails.append(f"CSV {r['app']} {r['sub']} {k}: {got.get(k)!r} != {v!r}")
                break

    # ---- JSON-LD ----------------------------------------------------------------------------------------------------
    lds = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)]
    ds = next((x for x in lds if x.get("@type") == "Dataset"), None)
    if not ds:
        fails.append("no Dataset JSON-LD")
    else:
        if f"{len(rows):,} FDA approvals" not in ds.get("description", ""):
            fails.append("Dataset description lacks the total")
        if ds.get("temporalCoverage") != f"{days[0].isoformat()}/{days[-1].isoformat()}":
            fails.append(f"Dataset temporalCoverage {ds.get('temporalCoverage')}")
        if "creativecommons.org/licenses/by/4.0" not in str(ds.get("license")):
            fails.append("Dataset license is not CC BY 4.0")
        if "approvals-by-drug.csv" not in json.dumps(ds.get("distribution")):
            fails.append("Dataset distribution lacks the CSV")

    # ---- letter pages -----------------------------------------------------------------------------------------------
    app_of_letter = collections.defaultdict(list)
    for a, us in letters.items():
        for u in us:
            app_of_letter[u.rsplit("/", 1)[1]].append(a)
    n_lines = 0
    for slug, d in letter_docs.items():
        blk = re.findall(r"<!--DRUGAPPROVALS:BEGIN-->(.*?)<!--DRUGAPPROVALS:END-->", d, re.S)
        hits = [a for a in app_of_letter.get(slug, []) if a in apps]
        if len(blk) > 1:
            fails.append(f"/crl/letter/{slug}: {len(blk)} approvals lines")
        if hits and not blk:
            fails.append(f"/crl/letter/{slug}: {hits} have approvals in the cache, no line names them")
        if blk and not hits:
            fails.append(f"/crl/letter/{slug}: an approvals line, but the cache has none for its application")
        if blk and hits:
            n_lines += 1
            t = text(blk[0])
            for a in hits:
                xs = apps[a]
                nn = sum(1 for x in xs if x["kind"] == "new application")
                need = [label(a), long_day(dt.date.fromisoformat(xs[-1]["date"]))]
                need += [f"{nn} approved original submission"] if nn else []
                need += [f"{len(xs) - nn} approved efficacy supplement"] if len(xs) > nn else []
                for w in need:
                    if w not in t:
                        fails.append(f"/crl/letter/{slug}: the approvals line does not say {w!r}")
                if f'/fda-approvals/drugs#{re.sub(r"[^a-z0-9]", "", a.lower())}' not in blk[0]:
                    fails.append(f"/crl/letter/{slug}: the approvals line does not link {a}'s anchor")

                for m in BAD.finditer(t):
                    fails.append(f"/crl/letter/{slug}: forbidden word in the approvals line: "
                                 f"{t[max(0, m.start() - 40):m.end() + 40]!r}")

    # ---- headings, names, links -------------------------------------------------------------------------------------
    for m in re.finditer(r'<h3 id="[^"]+" data-group="([^"]+)">.*?</h3><p class="sub">(.*?)</p>', doc, re.S):
        xs = apps.get(m.group(1))
        if xs and f"latest approval: {xs[-1]['sponsor']}" not in text(m.group(2)):
            fails.append(f"{m.group(1)}: heading does not name the newest approval's sponsor {xs[-1]['sponsor']!r}")
    for a, cells in tbl.items():
        xs = apps.get(a) or []
        names = [x.get("brand") or x.get("generic") for x in xs if x.get("brand") or x.get("generic")]
        if names and not any(html.unescape(n).lower() in text(cells[0]).lower() for n in names):
            fails.append(f"{a}: drug cell {text(cells[0])!r} names none of {names[:2]}")
        if not text(cells[0]):
            fails.append(f"{a}: empty drug cell")
    for u in re.findall(r'href="(http://[^"]+)"', doc[doc.index("<h1"):]):
        fails.append(f"an http:// link on the page: {u}")
    for u in sorted(set(re.findall(r'href="(/fda-approvals/\d{4}/[a-z]+)"', doc))):
        if not os.path.exists(os.path.join(SITE, u.strip("/"), "index.html")):
            fails.append(f"month page {u} does not exist")
    t_ = re.search(r"<title>(.*?)</title>", doc, re.S)
    d_ = re.search(r'<meta name="description" content="([^"]*)"', doc)
    if not t_ or len(html.unescape(t_.group(1))) > 70:
        fails.append(f"title too long: {t_.group(1) if t_ else None!r}")
    if not d_ or not 70 <= len(html.unescape(d_.group(1))) <= 158:
        fails.append(f"description length {len(d_.group(1)) if d_ else 0}")
    if "the latest months last" in doc:
        fails.append("the read-date clause claims an order the cache does not have")
    wf = io.open(WORKFLOW, encoding="utf-8").read() if os.path.exists(WORKFLOW) else ""
    if "git add -f pdufa_site_src/fda-approvals/data/approvals-by-drug.csv" not in wf:
        fails.append("the workflow does not force-add approvals-by-drug.csv; *.csv is ignored, so it would 404 live")

    # ---- words ------------------------------------------------------------------------------------------------------
    # 2026-11-25: the rebuild's inject_site_links.py adds a sitewide nav ("Trial success rates", "FDA approval rate")
    # between SITELINKS/RELATED markers before the footer, which this word check read as page text and blocked the
    # 9:22 PM PT run. Injected link blocks are not this page's words; test_fda_approvals_companies.py stops there too.
    page = re.sub(r"(?s)<!--(SITELINKS|RELATED|LINKHUB|DMOD):BEGIN-->.*?<!--\1:END-->", "", doc)
    body = text(page[page.index("<h1"):page.index("<footer") if "<footer" in page else len(page)])
    for m in BAD.finditer(body):
        fails.append(f"forbidden word on the page: {body[max(0, m.start() - 40):m.end() + 40]!r}")

    if fails:
        print(f"FAIL test_fda_approvals_drugs: {len(fails)} problem(s); fix: python build_fda_approvals_drugs.py")
        for f in fails[:40]:
            print("   " + f)
        return 1
    print(f"  PASS /fda-approvals/drugs: {len(rows):,} approvals on {len(apps):,} applications, {len(multi)} listed in "
          f"full, {len(with_crl)} with released CRLs; CSV and JSON-LD match; {n_lines} letter pages carry the line")
    return 0


if __name__ == "__main__":
    sys.exit(main())
