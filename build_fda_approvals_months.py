# -*- coding: utf-8 -*-
"""build_fda_approvals_months.py -- /fda-approvals/{year}/{month}: every FDA drug approval of the month, one sentence each.

Audit 2026-11-11 order 4(b): "FDA approvals {month} {year}" is search demand we already see, and Drugs@FDA lists every
approval. Each month page is built from openFDA's drugsfda endpoint (the Drugs@FDA data): original applications
(NDA/BLA, submission type ORIG) and efficacy supplements (class EFFICACY) with status AP and an action date in the
month. One sentence per approval: brand (generic), sponsor, application, type, the FDA's action day, and the action
letter when Drugs@FDA posts one. Counts are what openFDA returns for the month (openFDA trails Drugs@FDA by about a
week, and the page says so). Generics (ANDA) are out of scope and said to be. Facts only, not investment advice.

Months: January 2025 through the current Eastern month. The two most recent months are re-fetched every run; older
months come from _fda_approvals_months.json once fetched.

    python build_fda_approvals_months.py [--refetch-all] [--dry-run]
"""
import argparse
import collections
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

CACHE = os.path.join(HERE, "_fda_approvals_months.json")
BASE = "https://www.pdufa.bio"
MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
UA = {"User-Agent": "pdufa.bio-research-script/1.0"}
esc = lambda s: html.escape(str(s or ""), quote=True)


def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"results": []}
            time.sleep(2 + 3 * i)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 3 * i)
    return None


def fetch_month(y, m):
    lo = f"{y}{m:02d}01"
    hi = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).strftime("%Y%m%d")
    q = f"submissions.submission_status_date:[{lo}+TO+{hi}]+AND+submissions.submission_status:AP"
    out, skip = [], 0
    while True:
        j = get(f"https://api.fda.gov/drug/drugsfda.json?search={q}&limit=100&skip={skip}")
        if j is None:
            return None
        res = j.get("results") or []
        for a in res:
            appno = a.get("application_number", "")
            if appno.startswith("ANDA"):
                continue
            of = a.get("openfda") or {}
            prods = a.get("products") or []
            brand = (of.get("brand_name") or [p.get("brand_name") for p in prods if p.get("brand_name")] or [""])[0]
            generic = (of.get("generic_name") or [", ".join(i.get("name", "") for i in (prods[0].get("active_ingredients")
                                                                                      or []))] if prods else [""])[0]
            for s in a.get("submissions") or []:
                d = str(s.get("submission_status_date") or "")
                if s.get("submission_status") != "AP" or not (lo <= d <= hi):
                    continue
                orig = s.get("submission_type") == "ORIG"
                if not orig and s.get("submission_class_code") != "EFFICACY":
                    continue
                letter = next((x.get("url") for x in s.get("application_docs") or []
                               if "letter" in str(x.get("type", "")).lower()), "")
                out.append({"app": appno, "brand": str(brand).title() if str(brand).isupper() else brand,
                            "generic": str(generic).lower(), "sponsor": str(a.get("sponsor_name") or "").title(),
                            "kind": "new application" if orig else "efficacy supplement",
                            "sub": f"{s.get('submission_type')}-{s.get('submission_number')}",
                            "class": s.get("submission_class_code_description") or "",
                            "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "letter": letter})
        skip += len(res)
        total = ((j.get("meta") or {}).get("results") or {}).get("total", 0)
        if not res or skip >= total or skip >= 1000:
            break
        time.sleep(0.3)
    out.sort(key=lambda x: (x["date"], x["brand"]))
    return out


def page(y, m, items, fetched, prev_, next_, tpl):
    name = f"{MON[m - 1].capitalize()} {y}"
    url = f"{BASE}/fda-approvals/{y}/{MON[m - 1]}"
    n_new = sum(1 for x in items if x["kind"] == "new application")
    n_eff = len(items) - n_new
    first = (f"The FDA approved {n_new} new drug or biologic application{'s' if n_new != 1 else ''} and {n_eff} efficacy "
             f"supplement{'s' if n_eff != 1 else ''} (new uses for approved drugs) in {name}, per Drugs@FDA as read on "
             f"{fetched}.")
    title = f"FDA Approvals {name}: {n_new} New Applications, {n_eff} New Uses | pdufa.bio"
    desc = (f"Every FDA drug approval in {name}: {n_new} new applications and {n_eff} efficacy supplements, each with "
            f"its sponsor, FDA action day and letter. From Drugs@FDA.")[:158]
    def sent(x):
        d = dt.date.fromisoformat(x["date"])
        who = f"{esc(x['brand'])}" + (f" ({esc(x['generic'])})" if x["generic"] and x["generic"].lower() != str(x["brand"]).lower() else "")
        lt = f' <a href="{esc(x["letter"])}" rel="noopener">FDA letter</a>.' if x["letter"] else ""
        what = "approved" if x["kind"] == "new application" else "approved an efficacy supplement for"
        return (f'<li><b>{d.strftime("%b")} {d.day}:</b> the FDA {what} {who}, {esc(x["sponsor"])}, '
                f'{esc(x["app"])} {esc(x["sub"])}{(" (" + esc(x["class"]) + ")") if x["class"] and x["kind"] == "new application" else ""}.{lt}</li>')
    news = [x for x in items if x["kind"] == "new application"]
    effs = [x for x in items if x["kind"] != "new application"]
    nav = " &middot; ".join(z for z in (
        f'<a href="/fda-approvals/{prev_[0]}/{MON[prev_[1] - 1]}">&larr; {MON[prev_[1] - 1].capitalize()} {prev_[0]}</a>' if prev_ else "",
        f'<a href="/fda-approvals/{next_[0]}/{MON[next_[1] - 1]}">{MON[next_[1] - 1].capitalize()} {next_[0]} &rarr;</a>' if next_ else "",
        '<a href="/fda-approvals">all months</a>', '<a href="/fda-this-month">PDUFA decisions this month</a>',
        f'<a href="/decisions/{y}">decisions we tracked in {y}</a>' if os.path.exists(os.path.join(SITE, "decisions", str(y))) else "") if z)
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "url": url, "mainEntity": [
        {"@type": "Question", "name": f"How many drugs did the FDA approve in {name}?",
         "acceptedAnswer": {"@type": "Answer", "text": first}}]}
    body = (f'<h1>FDA approvals, {name}</h1><!--APLEDE:BEGIN--><p class="sub" style="color:#cfe0f5">{esc(first)}</p><!--APLEDE:END-->'
            f'<h2>New drug and biologic applications &middot; {n_new}</h2>'
            + (f'<ul style="line-height:1.75">{"".join(sent(x) for x in news)}</ul>' if news else '<p class="sub">None in Drugs@FDA yet.</p>')
            + f'<h2>New uses for approved drugs (efficacy supplements) &middot; {n_eff}</h2>'
            + (f'<ul style="line-height:1.75">{"".join(sent(x) for x in effs)}</ul>' if effs else '<p class="sub">None in Drugs@FDA yet.</p>')
            + f'<p class="sub" style="font-size:13px">Source: openFDA drugsfda (the Drugs@FDA data), read {fetched}. openFDA '
              f'trails Drugs@FDA by about a week, so the latest days of a month can be missing until the next read. Generic '
              f'approvals (ANDAs), labeling-only and manufacturing supplements are not listed. {nav}</p>')
    head = tpl[:tpl.index("<h1")]
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", head, count=1, flags=re.S)
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")'):
        head = re.sub(pat, lambda mm: mm.group(1) + esc(desc) + mm.group(2), head)
    for pat in (r'(<link rel="canonical" href=")[^"]*(")', r'(<meta property="og:url" content=")[^"]*(")'):
        head = re.sub(pat, lambda mm: mm.group(1) + url + mm.group(2), head)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda mm: mm.group(1) + esc(title.split(" | ")[0]) + mm.group(2), head)
    head = re.sub(r'<script type="application/ld\+json"[^>]*>.*?</script>', "", head, flags=re.S)
    head = re.sub(r"<!--DMOD:BEGIN-->.*?<!--DMOD:END-->", "", head, flags=re.S)
    head = head.replace("</head>", f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script></head>', 1)
    foot = tpl[tpl.index("<footer"):] if "<footer" in tpl else "</div></body></html>"
    foot = re.sub(r"<!--(SITELINKS|RELATED):BEGIN-->.*?<!--\1:END-->", "", foot, flags=re.S)
    return head + body + foot, len(items), n_new, n_eff


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--refetch-all", action="store_true")
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    td = eastern_today()
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    months, y, m = [], 2025, 1
    while (y, m) <= (td.year, td.month):
        months.append((y, m)); m += 1
        if m == 13:
            y, m = y + 1, 1
    for (y, m) in months:
        k = f"{y}-{m:02d}"
        if a.refetch_all or k not in cache or (y, m) >= months[-2]:
            got = fetch_month(y, m)
            if got is None:
                print(f"  {k}: openFDA unreachable; keeping cached copy ({len((cache.get(k) or {}).get('items', []))} items)")
                continue
            cache[k] = {"fetched": td.isoformat(), "items": got}
            time.sleep(0.3)
    if not a.dry_run:
        io.open(CACHE, "w", encoding="utf-8").write(json.dumps(cache, indent=0, ensure_ascii=False))
    tpl = io.open(os.path.join(SITE, "methodology", "index.html"), encoding="utf-8").read()
    rows = []
    for i, (y, m) in enumerate(months):
        k = f"{y}-{m:02d}"
        if k not in cache:
            continue
        doc, n, nn, ne = page(y, m, cache[k]["items"], cache[k]["fetched"], months[i - 1] if i else None,
                              months[i + 1] if i + 1 < len(months) else None, tpl)
        rows.append((y, m, nn, ne))
        if not a.dry_run:
            p = os.path.join(SITE, "fda-approvals", str(y), MON[m - 1], "index.html")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="utf-8").write(doc)
    # hub
    lis = "".join(f'<li><a href="/fda-approvals/{y}/{MON[m - 1]}">{MON[m - 1].capitalize()} {y}</a>: {nn} new application'
                  f'{"s" if nn != 1 else ""}, {ne} efficacy supplement{"s" if ne != 1 else ""}</li>' for y, m, nn, ne in reversed(rows))
    tot_n = sum(r[2] for r in rows if r[0] == td.year)
    hub_first = (f"Every FDA drug approval by month from Drugs@FDA: {tot_n} new drug and biologic applications approved so "
                 f"far in {td.year}, each month listing every approval with its sponsor, action day and letter.")
    hub = page.__wrapped__ if hasattr(page, "__wrapped__") else None  # noqa: F841
    head = tpl[:tpl.index("<h1")]
    ttl = f"FDA Approvals by Month 2025-{td.year}: Every New Application and New Use | pdufa.bio"
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(ttl)}</title>", head, count=1, flags=re.S)
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")'):
        head = re.sub(pat, lambda mm: mm.group(1) + esc(hub_first[:156]) + mm.group(2), head)
    for pat in (r'(<link rel="canonical" href=")[^"]*(")', r'(<meta property="og:url" content=")[^"]*(")'):
        head = re.sub(pat, lambda mm: mm.group(1) + f"{BASE}/fda-approvals" + mm.group(2), head)
    head = re.sub(r'<script type="application/ld\+json"[^>]*>.*?</script>', "", head, flags=re.S)
    head = re.sub(r"<!--DMOD:BEGIN-->.*?<!--DMOD:END-->", "", head, flags=re.S)
    foot = tpl[tpl.index("<footer"):] if "<footer" in tpl else "</div></body></html>"
    foot = re.sub(r"<!--(SITELINKS|RELATED):BEGIN-->.*?<!--\1:END-->", "", foot, flags=re.S)
    if not a.dry_run:
        os.makedirs(os.path.join(SITE, "fda-approvals"), exist_ok=True)
        io.open(os.path.join(SITE, "fda-approvals", "index.html"), "w", encoding="utf-8").write(
            head + f'<h1>FDA approvals by month</h1><p class="sub" style="color:#cfe0f5">{esc(hub_first)}</p>'
            f'<ul style="line-height:1.9">{lis}</ul>' + foot)
    for y, m, nn, ne in rows[-3:]:
        print(f"  /fda-approvals/{y}/{MON[m - 1]:9s} new {nn}, efficacy supplements {ne}")
    print(f"fda-approvals: {len(rows)} month page(s)" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
