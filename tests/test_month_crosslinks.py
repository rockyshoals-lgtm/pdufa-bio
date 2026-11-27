# -*- coding: utf-8 -*-
"""CI guard: a month's PDUFA page and its readout page link each other (2026-11-27).

inject_month_crosslinks.py writes the MXL line under each /calendar/<y>/<m> and /readouts/<y>/<m> page's
month-to-month links. Fails when a page whose twin exists and is indexable has no line (or the wrong one), when a
page carries a line whose twin is missing or noindex, or when the line links a page that does not exist. Plants
each fault first.

    python tests/test_month_crosslinks.py      (fix: python inject_month_crosslinks.py)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import inject_month_crosslinks as X  # noqa: E402

SITE = X.SITE


def check(docs):
    probs = []
    for (kind, y, m), doc in docs.items():
        want = X.block(SITE, kind, y, m)
        found = X.BLOCK.findall(doc)
        have = found[0] if found else ""
        if len(found) > 1:
            probs.append(f"/{kind}/{y}/{m}: {len(found)} month cross-link lines")
        if have != want:
            probs.append(f"/{kind}/{y}/{m}: month cross-link line is not the one its twin page gives")
        for href in re.findall(r'href="(/[^"]+)"', have):
            if not os.path.isfile(os.path.join(SITE, href.strip("/"), "index.html")):
                probs.append(f"/{kind}/{y}/{m}: links {href}, which does not exist")
    return probs


def main():
    docs = {(k, y, m): io.open(p, encoding="utf-8").read() for k, y, m, p in X.pages(SITE)}
    linked = [k for k, d in docs.items() if X.B in d]
    bare = [k for k, d in docs.items() if X.B not in d]
    plants = []
    if linked:
        t = linked[0]
        d = dict(docs); d[t] = X.BLOCK.sub("", d[t]); plants.append(("line dropped", d))
        d = dict(docs); d[t] = d[t].replace(X.E, X.E + X.BLOCK.search(d[t]).group(0), 1); plants.append(("doubled", d))
        d = dict(docs); d[t] = re.sub(r'(<!--MXL:BEGIN-->.*?href="/[a-z]+/\d{4}/)[a-z]+', r"\1zzz", d[t], count=1)
        plants.append(("wrong month", d))
    if bare:
        t = bare[0]
        d = dict(docs); d[t] = d[t] + X.B + '<p><a href="/readouts/1999/may">x</a></p>' + X.E
        plants.append(("line on a page with no twin", d))
    missed = [n for n, d in plants if not check(d)]
    if missed:
        print(f"FAIL: the checker missed planted faults: {missed}")
        return 1
    probs = check(docs)
    if probs:
        print(f"FAIL test_month_crosslinks: {len(probs)} problem(s); fix: python inject_month_crosslinks.py")
        for p in probs[:20]:
            print("  " + p)
        return 1
    print(f"OK -- {len(docs)} month pages: {len(linked)} link the same month's other catalyst page; "
          f"{len(plants)} planted faults caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
