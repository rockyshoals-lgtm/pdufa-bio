#!/usr/bin/env python3
"""build_device_decisions.py -- /devices/decisions: FDA device approvals (PMA) and De Novo grants, from the FDA's own
records.

2026-11-26 (David: "add ... Device pdufas and releases ... increase the moat"). Reads _fda_devices.json (written by
fetch_fda_devices.py from openFDA's device endpoints) and writes:

  pdufa_site_src/devices/decisions/index.html          hub: counts and review days by year, latest decisions, key
  pdufa_site_src/devices/decisions/<YEAR>/index.html   every decision of that year
  pdufa_site_src/devices/decisions/data/device-decisions.csv

Rules:
  * Every row is one FDA record, linked to the FDA database page it came from. Nothing is inferred or scored.
  * The decision is shown in words only where the FDA defines its code: openFDA's PMA field reference
    (open.fda.gov/fields/devicepma_reference.pdf) defines APPR "Approval", APWD "Withdrawal after approval" and APRL
    "Reclassification after approval"; the FDA's De Novo record pages print DENG as "Decision granted". A code the
    reference does not define (APCB) is shown as the code, with that said.
  * Only decisions that approved a device (PMA originals and panel-track supplements) or granted it (De Novo) are
    listed. 510(k) clearances are not.
  * Review days are calendar days from the FDA's received date to its decision date, both as the FDA records them.
  * A ticker is shown only where fetch_fda_devices.py matched the applicant exactly (see the cache's ticker_basis).
  * Facts only; not investment advice.

    python build_device_decisions.py [--cache _fda_devices.json] [--site pdufa_site_src]
Guard: tests/test_device_decisions.py
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_crl_companies import BASE, page  # noqa: E402
from build_crl_facts import esc, pretty  # noqa: E402

CACHE = os.path.join(HERE, "_fda_devices.json")
SITE = os.path.join(HERE, "pdufa_site_src")
RECENT = 50
TICKER_OK = re.compile(r"^(?!NONE$)[A-Z]{1,5}(?:[.-][A-Z])?$")   # not the SEC list's placeholders ('NONE.')
FIELD_REF = "https://open.fda.gov/fields/devicepma_reference.pdf"

# decision code -> words, only as the FDA defines them (see the module docstring)
DECISION = {
    "APPR": "Approved",
    "APWD": "Approved; withdrawn after approval",
    "APRL": "Approved; reclassified after approval",
    "DENG": "Granted",
}
SHOWN_CODES = {"PMA": {"APPR", "APWD", "APRL", "APCB"}, "PMA panel-track supplement": {"APPR", "APWD", "APRL", "APCB"},
               "De Novo": {"DENG"}}
PATHWAYS = ["PMA", "PMA panel-track supplement", "De Novo"]
PATH_LABEL = {"PMA": "PMA original", "PMA panel-track supplement": "PMA panel-track supplement", "De Novo": "De Novo"}

COLUMNS = ["decision_date", "pathway", "fda_number", "trade_name", "applicant", "ticker", "decision_code",
           "decision", "date_received", "review_days", "product_code", "advisory_committee", "supplement_reason",
           "fda_record_url"]


def d_of(s):
    try:
        return dt.date.fromisoformat(str(s or "")[:10])
    except ValueError:
        return None


def ok_url(u):
    return isinstance(u, str) and u.startswith("https://www.accessdata.fda.gov/")


def decision_words(code):
    return DECISION.get(code) or f"Approved (FDA code {code}, which openFDA's field reference does not define)"


def review_days(r):
    a, b = d_of(r.get("date_received")), d_of(r.get("decision_date"))
    return (b - a).days if a and b and a <= b else None


def load(path):
    c = json.load(io.open(path, encoding="utf-8"))
    rows, seen = [], set()
    for r in c.get("rows") or []:
        if not isinstance(r, dict):
            continue
        p, code = r.get("pathway"), (r.get("decision_code") or "").strip()
        if p not in SHOWN_CODES or code not in SHOWN_CODES[p]:
            continue
        if not d_of(r.get("decision_date")) or not ok_url(r.get("fda_url")) or not r.get("id") or r["id"] in seen:
            continue
        seen.add(r["id"])
        rows.append(r)
    rows.sort(key=lambda r: (r["decision_date"], r["id"]), reverse=True)
    return c, rows


def fetched_day(c):
    s = str(c.get("fetched") or "")
    try:
        t = dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
        from zoneinfo import ZoneInfo
        return pretty(t.astimezone(ZoneInfo("America/New_York")).date())
    except (ValueError, ImportError):
        return ""


def name_of(r):
    return (r.get("trade_name") or r.get("generic_name") or r.get("id") or "").strip()


def ticker_of(r):
    tk = r.get("ticker") or ""
    return tk if TICKER_OK.match(tk) else ""


def co(r, tickers):
    a = esc((r.get("applicant") or "").strip())
    tk = ticker_of(r)
    if tk:
        if tk in tickers:
            return f'{a} (<a href="/ticker/{esc(tk)}">{esc(tk)}</a>)'
        return f"{a} ({esc(tk)})"
    return a


def row_html(r, tickers, year_col=True):
    n = review_days(r)
    sup = (r.get("supplement_reason") or "").strip()
    what = esc(name_of(r)) + (f'<br><span class="sub">{esc(sup)}</span>' if sup else "")
    return (f'<tr data-dev="{esc(r["id"])}"><td>{esc(pretty(d_of(r["decision_date"])))}</td>'
            f'<td>{esc(PATH_LABEL[r["pathway"]])}</td><td>{what}</td><td>{co(r, tickers)}</td>'
            f'<td>{esc(decision_words(r["decision_code"]))}</td><td>{"" if n is None else n}</td>'
            f'<td><a href="{esc(r["fda_url"])}" rel="noopener nofollow">{esc(r["id"])}</a></td></tr>')


TABLE_HEAD = ('<table><tr><th>Decision date</th><th>Pathway</th><th>Device</th><th>Applicant</th><th>Decision</th>'
              '<th>Review days</th><th>FDA record</th></tr>')

KEY = ('<h2>How to read the decision column</h2><p class="sub">PMA decisions use the FDA\'s own four-letter codes. '
       f'openFDA\'s <a href="{FIELD_REF}" rel="noopener nofollow">PMA field reference</a> defines APPR as approval, '
       'APWD as withdrawal after approval and APRL as reclassification after approval. Every PMA row here carries an '
       'FDA approval order dated the decision date shown; the FDA record page shows any later status. A code the '
       'reference does not define (APCB) is printed with that note. The FDA\'s De Novo record pages print DENG as "Decision granted". Review days are '
       'calendar days from the date the FDA records the submission as received to its decision date; for a '
       'supplement they count from the supplement\'s own receipt.</p>')


def source_para(c):
    basis = esc(str(c.get("ticker_basis") or ""))
    f = fetched_day(c)
    return (f'<p class="sub">Source: the FDA\'s device databases through openFDA (PMA and De Novo records)'
            + (f', read {esc(f)}' if f else '') + '. Each row links to its FDA record. 510(k) clearances are not '
            f'listed. Tickers: {basis}. Facts only; not investment advice.</p>')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(csv_row(r))


def csv_row(r):
    n = review_days(r)
    return [r["decision_date"], PATH_LABEL[r["pathway"]], r["id"], name_of(r), r.get("applicant") or "",
            ticker_of(r), r["decision_code"], decision_words(r["decision_code"]), r.get("date_received") or "",
            "" if n is None else str(n), r.get("product_code") or "", r.get("advisory_committee") or "",
            r.get("supplement_reason") or "", r["fda_url"]]


def year_stats(rows):
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["decision_date"][:4]][r["pathway"]].append(review_days(r))
    return by


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def fmt_med(x):
    return "" if x is None else f"{x:g}"


def hub(c, rows, tickers, years):
    n = len(rows)
    cnt = collections.Counter(r["pathway"] for r in rows)
    first, last = rows[-1]["decision_date"][:4], rows[0]["decision_date"]
    title = "FDA Device Approvals and De Novo Grants Since 2010 | pdufa.bio"
    desc = ("FDA PMA device approvals, panel-track supplements and De Novo grants since 2010 as openFDA lists them: "
            "dates, applicants, review days, FDA links.")
    B = ['<h1>FDA device approvals and De Novo grants</h1>',
         f'<p class="sub" data-dev="lede">openFDA\'s PMA and 510(k) files list {n:,} device approvals and grants '
         f'from {first} through {esc(pretty(d_of(last)))}: {cnt["PMA"]:,} PMA original approvals, {cnt["PMA panel-track supplement"]:,} '
         f'PMA panel-track supplement approvals and {cnt["De Novo"]:,} De Novo grants. Each row links to the FDA '
         f'record it comes from.</p>',
         source_para(c),
         '<h2>By year</h2><p class="sub">Decisions by the year of the FDA decision date, and the median review days '
         '(received to decision) for PMA originals and De Novo grants.</p>',
         '<table><tr><th>Year</th><th>PMA originals</th><th>Panel-track supplements</th><th>De Novo grants</th>'
         '<th>Total</th><th>Median review days, PMA originals</th><th>Median review days, De Novo</th></tr>']
    ys = year_stats(rows)
    for y in years:
        s = ys[y]
        tot = sum(len(v) for v in s.values())
        B.append(f'<tr data-dev-year="{y}"><td><a href="/devices/decisions/{y}">{y}</a></td><td>{len(s["PMA"])}</td>'
                 f'<td>{len(s["PMA panel-track supplement"])}</td><td>{len(s["De Novo"])}</td><td>{tot}</td>'
                 f'<td>{fmt_med(med(s["PMA"]))}</td><td>{fmt_med(med(s["De Novo"]))}</td></tr>')
    B.append('</table>')
    if years and years[0] == str(eastern_year()):
        B.append(f'<p class="sub">{years[0]} runs through {esc(pretty(d_of(last)))}, the latest FDA decision in the '
                 f'data.</p>')
    B += [f'<h2>The latest {min(RECENT, n)} decisions</h2>', TABLE_HEAD]
    B += [row_html(r, tickers) for r in rows[:RECENT]]
    B.append('</table>')
    tk = collections.Counter(ticker_of(r) for r in rows if ticker_of(r))
    if tk:
        B += ['<h2>Listed applicants</h2><p class="sub">Applicants matched to a company listed today, with their '
              'number of decisions here. Most applicants are private or not matched, so this is not a market '
              'share.</p><p>']
        B.append(" &middot; ".join(
            (f'<a href="/ticker/{esc(t)}">{esc(t)}</a>' if t in tickers else esc(t)) + f" {k}"
            for t, k in sorted(tk.items(), key=lambda x: (-x[1], x[0]))))
        B.append('</p>')
    B += [KEY,
          '<h2>Download</h2><p><a href="/devices/decisions/data/device-decisions.csv">device-decisions.csv</a>: every '
          'row on these pages, with the FDA number, dates, product code, panel and the FDA record link (CC BY 4.0, '
          'credit pdufa.bio).</p>',
          '<p class="sub">See also: <a href="/devices">upcoming device milestones</a> &middot; '
          '<a href="/fda-approvals">FDA drug approvals by month</a> &middot; <a href="/crl">CRL database</a></p>']
    ld = {"@context": "https://schema.org", "@type": "Dataset", "name": "FDA device approvals and De Novo grants",
          "description": desc, "url": f"{BASE}/devices/decisions",
          "license": "https://creativecommons.org/licenses/by/4.0/",
          "creator": {"@type": "Organization", "name": "pdufa.bio"},
          "isBasedOn": "https://open.fda.gov/apis/device/",
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                            "contentUrl": f"{BASE}/devices/decisions/data/device-decisions.csv"}]}
    B.append(f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    return page(title, desc, "/devices/decisions", B)


def year_page(c, y, yrows, tickers, years):
    cnt = collections.Counter(r["pathway"] for r in yrows)
    title = f"FDA Device Approvals and De Novo Grants in {y} | pdufa.bio"
    desc = (f"The {len(yrows)} FDA PMA device approvals, panel-track supplements and De Novo grants dated {y} in "
            f"openFDA's files, each linked to its FDA record.")
    if len(desc) > 155:
        desc = f"FDA PMA device approvals and De Novo grants dated {y} in openFDA's files, linked to FDA records."
    nav = " &middot; ".join(f'<a href="/devices/decisions/{x}">{x}</a>' if x != y else f"<b>{x}</b>" for x in years)
    B = [f'<h1>FDA device approvals and De Novo grants in {y}</h1>',
         f'<p class="sub" data-dev="lede">openFDA\'s PMA and 510(k) files list {len(yrows)} device approvals and '
         f'grants dated {y}'
         + (f" through {esc(pretty(d_of(yrows[0]['decision_date'])))}" if y == str(eastern_year()) else "")
         + f': {cnt["PMA"]} PMA original approvals, {cnt["PMA panel-track supplement"]} PMA panel-track supplement '
         f'approvals and {cnt["De Novo"]} De Novo grants. Newest first.</p>',
         source_para(c), TABLE_HEAD]
    B += [row_html(r, tickers) for r in yrows]
    B += ['</table>', KEY, f'<p class="sub">Other years: {nav}</p>',
          '<p class="sub"><a href="/devices/decisions">All device decisions</a> &middot; '
          '<a href="/devices/decisions/data/device-decisions.csv">CSV</a></p>']
    return page(title, desc, f"/devices/decisions/{y}", B)


def eastern_year():
    try:
        from site_dates import eastern_today
        return eastern_today().year
    except Exception:  # noqa: BLE001
        return dt.date.today().year


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--site", default=SITE)
    a = ap.parse_args(argv)
    if not os.path.isfile(a.cache):
        print(f"device decisions: {os.path.basename(a.cache)} not found; nothing written")
        return 0
    c, rows = load(a.cache)
    if not rows:
        print("device decisions: no approval or grant rows; nothing written")
        return 0
    root = os.path.join(a.site, "devices", "decisions")
    tdir = os.path.join(a.site, "ticker")
    tickers = {t for t in (os.listdir(tdir) if os.path.isdir(tdir) else [])
               if os.path.isfile(os.path.join(tdir, t, "index.html"))}
    years = sorted({r["decision_date"][:4] for r in rows}, reverse=True)
    # year pages the data no longer backs are removed
    if os.path.isdir(root):
        for d in os.listdir(root):
            if re.fullmatch(r"20\d\d", d) and d not in years:
                shutil.rmtree(os.path.join(root, d))
    write_csv(os.path.join(root, "data", "device-decisions.csv"), rows)
    write(os.path.join(root, "index.html"), hub(c, rows, tickers, years))
    for y in years:
        write(os.path.join(root, y, "index.html"),
              year_page(c, y, [r for r in rows if r["decision_date"][:4] == y], tickers, years))
    print(f"/devices/decisions: {len(rows)} decisions, {len(years)} year pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
