# -*- coding: utf-8 -*-
"""test_crl_month_pages.py -- each /crl/{year}/{month} page's two counts match their records (audit 2026-11-09 §5.5).

Released count = letters in the corpus /crl lists dated that month; tracked count = CRL rows on /decisions/crl with an
FDA action date in that month. The current Eastern month's page must exist (the month-dated query is about now).
"""
import collections, glob, io, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def stated(lede_html):
    """(released, tracked) as the month page's lede states them; None where the sentence is missing."""
    t = re.sub(r"<[^>]+>", "", lede_html)
    m1 = re.search(r"holds (\d+) letters? dated", t)
    m2 = re.search(r", (\d+) (?:was|were) (?:a )?Complete Response Letters?", t)
    return (int(m1.group(1)) if m1 else None, int(m2.group(1)) if m2 else None)


def self_test():
    """2026-11-18: the builder writes '1 was a Complete Response Letter' for a one-CRL month and the regex had no
    'a', so a correct page read as '?'. Singular and plural must both read, and a wrong count must still differ."""
    one = ("The FDA's public release holds 2 letters dated March 2026 (openFDA). Of the 22 FDA decisions pdufa.bio "
           "tracked in March 2026, 1 was a Complete Response Letter.")
    many = ("The FDA's public release holds 1 letter dated June 2026. Of the 30 FDA decisions pdufa.bio tracked in "
            "June 2026, 3 were Complete Response Letters.")
    assert stated(one) == (2, 1), stated(one)
    assert stated(many) == (1, 3), stated(many)
    assert stated(one.replace("1 was a", "2 was a")) != (2, 1), "a wrong tracked count must not match"
    assert stated("No counts here.") == (None, None), "a lede without the sentences must not read as a count"


def main():
    self_test()
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
        rel, trk = stated(lede.group(1))
        if rel != by.get(k, 0):
            bad.append(f"/crl/{y}/{mon}: says {'?' if rel is None else rel} released, corpus has {by.get(k, 0)}")
        if trk != len(ours.get(k, [])):
            bad.append(f"/crl/{y}/{mon}: says {'?' if trk is None else trk} tracked CRLs, /decisions/crl has {len(ours.get(k, []))}")
    # 2026-11-24: /crl/{year} states the same two counts for the year; each must equal its own record's sum.
    years = sorted({k[:4] for k in by} | {k[:4] for k in ours})
    for y in years:
        p = os.path.join(HERE, "pdufa_site_src", "crl", y, "index.html")
        if int(y) < 2025:
            continue
        if not os.path.exists(p):
            bad.append(f"/crl/{y}: no year page"); continue
        lede = re.search(r"<!--CRLYEARLEDE:BEGIN-->(.*?)<!--CRLYEARLEDE:END-->", io.open(p, encoding="utf-8").read(), re.S)
        rel, trk = stated(lede.group(1)) if lede else (None, None)
        want_rel = sum(v for k, v in by.items() if k[:4] == y)
        want_trk = sum(len(v) for k, v in ours.items() if k[:4] == y)
        if (rel, trk) != (want_rel, want_trk):
            bad.append(f"/crl/{y}: says {rel} released / {trk} tracked, records have {want_rel} / {want_trk}")
    if bad:
        print(f"FAIL: {len(bad)} CRL month page problem(s)")
        for x in bad[:20]:
            print("   ", x)
        return 1
    print(f"  PASS: {len(pages)} CRL month pages match the corpus and /decisions/crl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
