# -*- coding: utf-8 -*-
"""CI guard: each drug page links the month pages for the readout and PDUFA months its catalyst rows give (2026-11-27).

inject_drug_month_links.py writes the MLINK line from the page's own Catalyst history rows. Fails when a page's line
is not the line its rows give today (missing, stale, or on a page with no such month), or links a month page that
does not exist or is noindex. Plants each fault first.

    python tests/test_drug_month_links.py      (fix: python inject_drug_month_links.py)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import inject_drug_month_links as X  # noqa: E402

SITE = X.SITE


def check(docs):
    probs = []
    for slug, doc in docs.items():
        m = X.BLOCK.search(doc)
        have = m.group(0) if m else ""
        want = X.block(X.BLOCK.sub("", doc), SITE)
        if have != want:
            probs.append(f"/drug/{slug}: month links are not what its catalyst rows give")
        for base, y, mon in re.findall(r'href="/(readouts|calendar)/(\d{4})/([a-z]+)"', have):
            if not X.indexable(SITE, base, y, mon):
                probs.append(f"/drug/{slug}: links /{base}/{y}/{mon}, which does not exist or is noindex")
    return probs


def main():
    root = os.path.join(SITE, "drug")
    docs = {s: io.open(os.path.join(root, s, "index.html"), encoding="utf-8").read()
            for s in sorted(os.listdir(root)) if os.path.isfile(os.path.join(root, s, "index.html"))}
    with_ = [s for s in docs if X.B in docs[s]]
    without = [s for s in docs if X.B not in docs[s] and X.rows_span(docs[s])]
    plants = []
    if with_:
        t = with_[0]
        d = dict(docs); d[t] = X.BLOCK.sub("", d[t]); plants.append(("line dropped", d))
        d = dict(docs); d[t] = re.sub(r'(href="/(?:readouts|calendar)/)\d{4}', r"\g<1>2031", d[t], count=1)
        plants.append(("month changed", d))
    if without:
        t = without[0]; sp = X.rows_span(docs[t]); d = dict(docs)
        d[t] = docs[t][:sp[1]] + X.B + '<p class="note">x</p>' + X.E + docs[t][sp[1]:]
        plants.append(("line on a page with no month", d))
    missed = [n for n, d in plants if not check(d)]
    if missed:
        print(f"FAIL: the checker missed planted faults: {missed}")
        return 1
    probs = check(docs)
    if probs:
        print(f"FAIL test_drug_month_links: {len(probs)} problem(s); fix: python inject_drug_month_links.py")
        for p in probs[:20]:
            print("  " + p)
        return 1
    print(f"OK -- {len(docs)} drug pages: {len(with_)} link the readout or PDUFA month pages their rows give; "
          f"{len(plants)} planted faults caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
