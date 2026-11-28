# -*- coding: utf-8 -*-
"""test_crl_company_announced.py -- company-announced CRLs and the /crl/{year}/{month}/{day} pages (2026-11-28).

crl_company_announced.json holds Complete Response Letters companies announced themselves, January 2024 on, each with
the company's own dated release, stock-exchange disclosure or SEC filing (re-read against it before it was added).
What this holds:

  * every record is well formed: ISO dates from 2024 on, a letter date (where given) on or before the announcement
    and within 30 days of it, an https source, a known application type, no record twice;
  * every record is on its own day page with its source link, and on the day page of its letter date if that differs;
  * a record that is one of the tracked decisions is not listed again in the month page's company table, and one that
    is not is listed there, with its source;
  * every letter in the FDA's release dated 2024 on is on its day page; every day page is backed by a record; every
    month page links each of its day pages; titles say the date and fit.
"""
import collections, datetime as dt, glob, html, io, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
APPS = {"NDA", "BLA", "sNDA", "sBLA", "biosimilar BLA", ""}
KINDS = {"press release", "SEC 8-K", "stock-exchange disclosure", "earnings release", "company statement",
         "company announcement"}


def read(path):
    p = os.path.join(SITE, path.strip("/"), "index.html")
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else None


def main():
    import build_crl_months as b
    bad = []
    recs = b.announced()
    seen, keys = set(), set()
    for r in recs:
        i = r.get("id")
        if i in seen:
            bad.append(f"{i}: duplicate id")
        seen.add(i)
        k = (r["company_short"].lower(), r["drug_short"].lower(), r["announce_date"])
        if k in keys:
            bad.append(f"{i}: same company, drug and date twice")
        keys.add(k)
        if not ("2024-01-01" <= r["announce_date"] <= b.eastern_today().isoformat()):
            bad.append(f"{i}: announce_date {r['announce_date']} outside 2024-01-01..today")
        if r["crl_date"]:
            gap = (b._D(r["announce_date"]) - b._D(r["crl_date"])).days
            if not 0 <= gap <= 30:
                bad.append(f"{i}: letter dated {r['crl_date']} is not within 30 days before the announcement")
        if not r["source_url"].startswith("https://") or not r["source_label"]:
            bad.append(f"{i}: no https source")
        if r["application"] not in APPS:
            bad.append(f"{i}: application {r['application']!r}")
        if r["source_kind"] not in KINDS:
            bad.append(f"{i}: source_kind {r['source_kind']!r}")
        if not r["company_short"] or not r["drug_short"] or int(r.get("letters") or 0) < 1:
            bad.append(f"{i}: missing company, drug or letter count")

    ours, _ = b.tracked()
    trk = [o for v in ours.values() for o in v]
    letters, _ = b.corpus()
    for r in recs:
        src = html.escape(r["source_url"], quote=True)
        day = read(b.day_href(r["announce_date"]))
        if day is None or src not in day:
            bad.append(f"{r['id']}: not on {b.day_href(r['announce_date'])} with its source")
        if r["crl_date"] and r["crl_date"] != r["announce_date"]:
            d2 = read(b.day_href(r["crl_date"]))
            if d2 is None or src not in d2:
                bad.append(f"{r['id']}: not on the day page of its letter date {r['crl_date']}")
        d = b._D(r["announce_date"])
        month = read(f"/crl/{d.year}/{b.MON[d.month - 1]}") or ""
        listed = src in month
        href = b.match_tracked(r, trk)
        if href and listed:
            bad.append(f"{r['id']}: listed in its month page's company table and as tracked decision {href}")
        if not href and not listed:
            bad.append(f"{r['id']}: not listed on its month page")
        if href and day and f'href="{href}"' not in day:
            bad.append(f"{r['id']}: day page does not link its tracked decision {href}")

    days = {r["announce_date"] for r in recs} | {r["crl_date"] for r in recs if r["crl_date"]} | {o[0] for o in trk}
    for l in letters:
        if l["iso"] >= "2024-01-01":
            days.add(l["iso"])
            doc = read(b.day_href(l["iso"]))
            if doc is None or html.escape(l["url"], quote=True) not in doc:
                bad.append(f"FDA letter {l['fn']} ({l['iso']}) not on its day page")
    days = {x for x in days if "2024-01-01" <= x <= b.eastern_today().isoformat()}
    want = {b.day_href(x) for x in days}
    have = set()
    for p in glob.glob(os.path.join(SITE, "crl", "20[0-9][0-9]", "*", "[0-9]*", "index.html")):
        y, mon, dd = p.split(os.sep)[-4:-1]
        have.add(f"/crl/{y}/{mon}/{dd}")
    for x in sorted(have - want):
        bad.append(f"{x}: day page with no record dated that day")
    for x in sorted(want - have):
        bad.append(f"{x}: record dated that day but no day page")

    by_month = collections.defaultdict(list)
    for x in want:
        by_month[x.rsplit("/", 1)[0]].append(x)
    for m, xs in by_month.items():
        doc = read(m) or ""
        for x in xs:
            if f'href="{x}"' not in doc:
                bad.append(f"{m}: no link to {x}")
    for x in sorted(have & want):
        doc = read(x)
        t = html.unescape(re.search(r"<title>(.*?)</title>", doc, re.S).group(1))
        y, mon, dd = x.split("/")[2:]
        when = f"{mon.capitalize()} {dd}, {y}"
        if not t.startswith("FDA Complete Response Letter") or when not in t or len(t) > 100:
            bad.append(f"{x}: title {t!r}")
        for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            json.loads(blob)

    if bad:
        print(f"FAIL: {len(bad)} company-announced CRL problem(s)")
        for x in bad[:25]:
            print("   ", x)
        return 1
    print(f"  PASS: {len(recs)} company-announced CRLs, {len(have)} day pages, each record on its pages with its source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
