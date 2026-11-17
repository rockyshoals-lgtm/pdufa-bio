# -*- coding: utf-8 -*-
"""build_fda_application_pages.py -- one page per FDA application: /fda-application/nda-215390.

WHY: people search a drug by whatever name they last saw: the brand (IGALMI), the ingredient
(dexmedetomidine), the code name from the trial years (BXCL501), or the company and ticker that sold
it (BioXcel, BTAI). Those names belong to ONE FDA application, but no page joins them, so a
brand-new brand name or a code name lands on nobody's page, and trackers keep listing a drug under a
company that sold it months ago. This page joins them, and every join is sourced.

WHAT IS ON A PAGE (and where each fact comes from):
  * FDA application number, brand, ingredient, applicant of record, the products on the application
    and their approval dates: the FDA Orange Book data files, read at build time (never typed).
  * Development code names: the company's own release or SEC filing, quoted (the quote must name
    the code and the drug together).
  * Owner today and its ticker: the company's own release or filing, quoted (the quote must contain
    the ticker).
  * Earlier owners, originators and partners: primary documents, quoted, with a fixed role phrase
    (no free text).
  * Links to the FDA decisions we track for the drug, the drug page and the ticker hubs.

All rules live in fda_applications_lib.py and are shared with tests/test_fda_application_pages.py.
A mapping that fails a rule is dropped here and the build prints why; the guard fails the run if a
failing mapping is ever on disk. Pages are regenerated from scratch each run, and an application that
leaves the data (or the Orange Book) loses its page.

Schema: MedicalEntity with additionalType schema.org/Drug (never Drug or any Product type; see
tests/test_drug_schema.py), identifier = the FDA application number.

    python build_fda_application_pages.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fda_applications_lib as L  # noqa: E402
from site_dates import eastern_today as _eastern_today  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "fda-application")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
BASE = "https://www.pdufa.bio"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OB_URL = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def full_date(iso):
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"


def title_case(s):
    """'TEVA NEUROSCIENCE INC' stays as the FDA wrote it; only used for prose ingredients."""
    return s


def ob_link(appl_no):
    return (f"https://www.accessdata.fda.gov/scripts/cder/ob/results_product.cfm?"
            f"Appl_Type=N&amp;Appl_No={appl_no}")


def daf_link(appl_no):
    return (f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&amp;"
            f"ApplNo={appl_no}")


def src_cite(src):
    """'Teva press release, Oct 27, 2026' linked, with the quote under it."""
    lab = f"{src['publisher']} {src['doc']}, {full_date(src['doc_date'])}"
    return (f'<a class="lit" href="{esc(src["url"])}" rel="nofollow noopener">{esc(lab)}</a>'
            f'<div class="q">&ldquo;{esc(src["quote"].strip())}&rdquo;'
            + (f' &hellip; &ldquo;{esc(src["quote_2"].strip())}&rdquo;' if src.get("quote_2") else "")
            + '</div>')


SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/IBMPlexMono-600.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts/fonts.css">
{ld}
<style>
:root{{--bg:#0b1017;--card:#111826;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#dfe9f7;
font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}}
.wrap{{max-width:880px;margin:0 auto;padding:18px 16px 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}
.brand{{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;
text-decoration:none}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}}
h1{{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}}
h2{{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px}}
.row{{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:11px 0;
border-top:1px solid var(--line);color:inherit;text-decoration:none}}
.row:hover{{background:#141d2d}}
.t{{font-weight:600}}.d{{color:var(--mut2);font-size:13.5px}}
table.kv{{border-collapse:collapse;width:100%;font-size:14px}}
table.kv th,table.kv td{{text-align:left;vertical-align:top;padding:9px 8px;border-top:1px solid var(--line)}}
table.kv th{{color:var(--mut2);font-weight:400;width:30%}}
.q{{color:var(--mut2);font-size:12.5px;margin-top:3px}}
.lede{{max-width:74ch}}
a.lit{{color:#9ec5ff}}
.legal{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);
font-size:12px;line-height:1.7}}
</style></head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>
<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>
<a href="/readouts">Readouts</a></div></div>
<h1>{h1}</h1>
{body}
<div class="legal">Facts only; not investment advice. The FDA facts on this page are read from the FDA
Orange Book data files; every other name links the company document or SEC filing it comes from.
pdufa.bio is not affiliated with the FDA.</div>
</div></body></html>
"""


def load_dataset():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def tracked_rows(e, rows):
    """FDA-decision rows on our calendar for this drug: the row name carries the brand, the
    ingredient's leading word or a sourced code name. PDUFA rows only (the page is about the FDA
    application, not trials)."""
    keys = {L.norm(e["brand"])}
    for ing in e["fda"]["ingredients"]:
        w = ing.split(";")[0].strip().split(" ")[0]
        if len(w) >= 6:
            keys.add(L.norm(w))
    keys |= {L.norm(c["name"]) for c in e["code_names"] if len(L.norm(c["name"])) >= 5}
    out = []
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        nm = L.norm(r.get("name"))
        if any(k and k in nm for k in keys):
            out.append(r)
    seen, uniq = set(), []
    for r in sorted(out, key=lambda r: (r.get("d") or "", r.get("t") or "")):
        k = (r.get("url"), r.get("d"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def page_for(e, rows, as_of, today):
    appl, no = e["appl"], e["appl"].split()[1]
    fda = e["fda"]
    brand = e["brand"]
    ing = e["ingredient"]
    applicants = fda["applicants"]
    codes = [c["name"] for c in e["code_names"]]
    own = e["owner"]

    # ---- lede: every clause is one of the sourced facts below, nothing else
    lede = (f"{esc(appl)} is the FDA application for {esc(brand)} ({esc(ing)}). The FDA's Orange Book "
            f"lists the applicant of record as {esc(' and '.join(applicants))}"
            + (f" and the first approval on it as {full_date(fda['first_approval'])}" if fda["first_approval"] else "")
            + ".")
    if codes:
        lede += f" Code name{'s' if len(codes) > 1 else ''} used in development: {esc(', '.join(codes))}."
    if own:
        lede += f" Owner today: {esc(own['company'])} ({esc(own.get('exchange') or '')}{': ' if own.get('exchange') else ''}{esc(own['ticker'])})."

    names = [f'<tr><th>Brand name (FDA)</th><td data-map="brand">{esc(brand)}'
             f'<div class="q">Orange Book trade name{"s" if len(fda["brands"]) > 1 else ""}: '
             f'{esc(", ".join(fda["brands"]))}</div></td></tr>',
             f'<tr><th>Active ingredient (FDA)</th><td data-map="ingredient">'
             f'{esc("; ".join(fda["ingredients"]))}</td></tr>']
    for c in e["code_names"]:
        names.append(f'<tr><th>Code name</th><td data-map="code_name" data-value="{esc(c["name"])}">'
                     f'<b>{esc(c["name"])}</b><div class="q">Source: {src_cite(c["src"])}</div></td></tr>')

    who = [f'<tr><th>FDA applicant of record</th><td data-map="applicant">{esc("; ".join(applicants))}'
           f'<div class="q">FDA Orange Book data files as of {full_date(as_of)}</div></td></tr>']
    if own:
        who.append(f'<tr><th>Owner today</th><td data-map="owner" data-value="{esc(own["ticker"])}">'
                   f'{esc(own["company"])} (<a class="lit" href="/ticker/{esc(own["ticker"])}">'
                   f'{esc(own["ticker"])}</a>)<div class="q">Source: {src_cite(own["src"])}</div></td></tr>')
    for h in e["history"]:
        tk = h.get("ticker")
        # a company that sold the product or was bought may no longer trade under that symbol
        # (BioXcel's 8-K: Nasdaq suspended BTAI); say which time the ticker belongs to
        pre = "ticker at the time: " if h["role"] in ("sold_to_owner", "acquired_by_owner") else ""
        tkh = (f' ({pre}<a class="lit" href="/ticker/{esc(tk)}">{esc(tk)}</a>)' if tk and
               os.path.isdir(os.path.join(SITE, "ticker", tk)) else (f" ({pre}{esc(tk)})" if tk else ""))
        role = L.HISTORY_ROLES[h["role"]]
        when = f", {full_date(h['date'])}" if h.get("date") else ""
        who.append(f'<tr><th>Earlier / partner</th><td data-map="history" data-value="{esc(tk or h["company"])}">'
                   f'{esc(h["company"])}{tkh}: {esc(role)}{esc(when)}'
                   f'<div class="q">Source: {src_cite(h["src"])}</div></td></tr>')
    if e["withheld"]:
        who.append('<tr><th>Owner today</th><td>Not shown: ' + esc("; ".join(e["withheld"])) + '</td></tr>')

    prods = "".join(
        f'<tr><td>{esc(p["no"])}</td><td>{esc(p["trade"])}</td><td>{esc(p["form"])}</td>'
        f'<td>{esc(p["strength"])}</td><td>{full_date(p["approved"]) or "before 1982"}</td></tr>'
        for p in fda["products"])

    trk = tracked_rows(e, rows)
    trk_html = ""
    if trk:
        items = []
        for r in trk:
            d_ = r.get("_d") or {}
            cands = [str(r.get("url") or ""), f"/fda-decision/{r.get('t')}-{r.get('d')}",
                     f"/fda-decision/{r.get('t')}-{d_.get('fda_action_date') or ''}"]
            u = next((c for c in cands if c.startswith("/") and re.match(r"^/[A-Za-z0-9/_-]+$", c)
                      and os.path.exists(os.path.join(SITE, c.strip("/"), "index.html"))), "")
            if not u:
                continue
            items.append(f'<a class="row" href="{esc(u)}"><span class="t">{esc(r.get("name"))}</span>'
                         f'<span class="d">{esc(r.get("t"))} &middot; {esc(r.get("st"))}</span></a>')
        if items:
            trk_html = "<h2>FDA decisions we track for this drug</h2>" + "".join(items)

    links = []
    cands = ([L.norm(brand), re.sub(r"[^a-z0-9]+", "-", ing.lower()).strip("-"), ing.split(" ")[0].lower()]
             + e["drug_pages"])
    for cand in cands:
        if cand and re.match(r"^[a-z0-9-]+$", cand) and os.path.isdir(os.path.join(SITE, "drug", cand)) \
                and f"/drug/{cand}" not in links:
            links.append(f"/drug/{cand}")
    see = ""
    if links:
        see = ("<p>Drug page: " + " &middot; ".join(f'<a class="lit" href="{l}">{l}</a>' for l in links) + "</p>")

    body = (f'<p class="lede">{lede}</p>'
            f'<p class="d">Page updated {full_date(today)}. FDA records: '
            f'<a class="lit" href="{daf_link(no)}" rel="nofollow noopener">Drugs@FDA {esc(appl)}</a> &middot; '
            f'<a class="lit" href="{ob_link(no)}" rel="nofollow noopener">Orange Book {esc(appl)}</a></p>'
            f'<h2>Names for this drug</h2><table class="kv">{"".join(names)}</table>'
            f'<h2>Who holds the application</h2><table class="kv">{"".join(who)}</table>'
            f'<h2>Products on {esc(appl)} (FDA Orange Book)</h2>'
            f'<table class="kv"><tr><th>No.</th><th>Trade name</th><th>Form; route</th><th>Strength</th>'
            f'<th>Approved</th></tr>{prods}</table>'
            f'{trk_html}{see}'
            f'<p class="d">Orange Book data: <a class="lit" href="{OB_URL}" rel="nofollow noopener">'
            f'FDA Orange Book data files</a>, as of {full_date(as_of)}. Approval dates are the FDA\'s dates '
            f'for each product; a later supplement (a new use) does not change them.</p>')

    alt = [ing] + codes
    if L.norm(e["fda"]["ingredients"][0]) != L.norm(ing):
        alt.insert(1, fda["ingredients"][0].lower())
    ld_ent = {"@context": "https://schema.org", "@type": "MedicalEntity",
              "additionalType": "https://schema.org/Drug", "name": brand,
              "url": f"{BASE}/fda-application/{e['slug']}",
              "alternateName": alt,
              "identifier": {"@type": "PropertyValue", "propertyID": "FDA application number", "value": appl}}
    ld_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE}/"},
        {"@type": "ListItem", "position": 2, "name": "FDA applications", "item": f"{BASE}/fda-application"},
        {"@type": "ListItem", "position": 3, "name": f"{brand} {appl}",
         "item": f"{BASE}/fda-application/{e['slug']}"}]}
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
                 for x in (ld_ent, ld_bc))

    title = f"{brand} ({ing}) {appl}: applicant, code name, owner | pdufa.bio"
    if len(title) > 95:
        title = f"{brand} {appl}: applicant, code name, owner | pdufa.bio"
    desc = f"{brand} ({ing}), FDA {appl}."
    for extra in ((f" Code name {codes[0]}." if codes else ""),
                  (f" Owner today: {own['company']} ({own['ticker']})." if own else ""),
                  f" FDA applicant of record: {applicants[0]}.",
                  " Every name sourced.", " Facts only."):
        if extra and len(desc) + len(extra) <= 158:
            desc += extra
    h1 = f"{brand} ({ing}): FDA {appl}"
    return SHELL.format(title=esc(title), desc=esc(desc), canon=f"{BASE}/fda-application/{e['slug']}",
                        ld=ld, h1=esc(h1), body=body)


def index_page(entries, as_of):
    items = "".join(
        f'<a class="row" href="/fda-application/{esc(e["slug"])}"><span class="t">{esc(e["brand"])} '
        f'({esc(e["ingredient"])})</span><span class="d">{esc(e["appl"])}'
        + (f' &middot; {esc(", ".join(c["name"] for c in e["code_names"]))}' if e["code_names"] else "")
        + (f' &middot; {esc(e["owner"]["ticker"])}' if e["owner"] else "")
        + '</span></a>'
        for e in sorted(entries, key=lambda e: e["brand"].lower()))
    lede = (f"{len(entries)} FDA applications, each on one page with its brand, ingredient, code names, "
            f"FDA applicant of record and today's owner and ticker. FDA facts come from the Orange Book "
            f"(as of {full_date(as_of)}); every other name links its source.")
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE}/"},
        {"@type": "ListItem", "position": 2, "name": "FDA applications", "item": f"{BASE}/fda-application"}]})
    return SHELL.format(
        title="FDA Applications: Brand, Code Name, Applicant and Owner | pdufa.bio",
        desc=esc(lede[:158].rsplit(" ", 1)[0] + "."), canon=f"{BASE}/fda-application",
        ld=f'<script type="application/ld+json">{ld}</script>', h1="FDA applications",
        body=f'<p class="lede">{esc(lede)}</p>' + items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = _eastern_today().isoformat()
    as_of = L.ob_as_of()
    rows = load_dataset()
    built, dropped = [], []
    for clean, errs, notes in L.all_entries():
        for p in errs:
            print("  DROP " + p)
        for p in notes:
            print("  WITHHELD " + p)
        if clean is None:
            dropped.append((errs + notes or ["?"])[0])
            continue
        built.append(clean)
    if not a.dry_run:
        if os.path.isdir(OUT):
            shutil.rmtree(OUT)
        os.makedirs(OUT, exist_ok=True)
        for e in built:
            os.makedirs(os.path.join(OUT, e["slug"]), exist_ok=True)
            io.open(os.path.join(OUT, e["slug"], "index.html"), "w", encoding="utf-8").write(
                page_for(e, rows, as_of, today))
        io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_page(built, as_of))
    n_codes = sum(len(e["code_names"]) for e in built)
    n_own = sum(1 for e in built if e["owner"])
    n_hist = sum(len(e["history"]) for e in built)
    print(f"fda-application pages: {len(built)} (+ index); code names {n_codes}, owners {n_own}, "
          f"history rows {n_hist}; pages dropped {len(dropped)}")
    if a.dry_run:
        print("DRY RUN -- nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
