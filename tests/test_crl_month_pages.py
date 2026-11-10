# -*- coding: utf-8 -*-
"""test_crl_month_pages.py -- each /crl/{year}/{month} page's two counts match their records (audit 2026-11-09 §5.5).

Released count = letters in the corpus /crl lists dated that month; tracked count = CRL rows on /decisions/crl with an
FDA action date in that month. The current Eastern month's page must exist (the month-dated query is about now).
"""
import collections, glob, io, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main():
    import build_crl_months as b
    from site_dates import eastern_today
    letters, _ = b.corpus()
    ours, _ = b.tracked()
    by = collections.Counter(l["iso"][:7] for l in letters)
    pages = glob.glob(os.path.join(HERE, "pdufa_site_src", "crl", "20[0-9][0-9]", "*", "index.html"))
    bad = []
    td = eastern_today()
    cur = os.path.join(HERE, "pdufa_site_src", "crl", str(td.year), b.MON[td.month - 1], "index.html")
    if not os.path.exists(cur):
        bad.append(f"no page for the current month ({td.year}/{b.MON[td.month - 1]})")
    for p in pages:
        y, mon = p.split(os.sep)[-3], p.split(os.sep)[-2]
        if mon not in b.MON:
            continue
        k = f"{y}-{b.MON.index(mon) + 1:02d}"
        doc = io.open(p, encoding="utf-8").read()
        lede = re.search(r"<!--CRLLEDE:BEGIN-->(.*?)<!--CRLLEDE:END-->", doc, re.S)
        if not lede:
            bad.append(f"/crl/{y}/{mon}: no lede"); continue
        t = re.sub(r"<[^>]+>", "", lede.group(1))
        m1 = re.search(r"holds (\d+) letters? dated", t)
        m2 = re.search(r", (\d+) (?:was|were) Complete Response Letters?", t)
        if not m1 or int(m1.group(1)) != by.get(k, 0):
            bad.append(f"/crl/{y}/{mon}: says {m1.group(1) if m1 else '?'} released, corpus has {by.get(k, 0)}")
        if not m2 or int(m2.group(1)) != len(ours.get(k, [])):
            bad.append(f"/crl/{y}/{mon}: says {m2.group(1) if m2 else '?'} tracked CRLs, /decisions/crl has {len(ours.get(k, []))}")
    if bad:
        print(f"FAIL: {len(bad)} CRL month page problem(s)")
        for x in bad[:20]:
            print("   ", x)
        return 1
    print(f"  PASS: {len(pages)} CRL month pages match the corpus and /decisions/crl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
