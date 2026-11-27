# -*- coding: utf-8 -*-
"""CI guard: each /readouts/<year>/<month> page lists exactly that month's readouts in today's dataset (2026-11-27).

build_readout_months.py writes the RMONTH block from api/v1/dataset.mjs. Before it, the month pages were never
rebuilt: December 2026 listed 49 "estimates" against 20 in the dataset, and passed months said nothing of what came
of their windows. This fails when a month page has no block, when its block is not the block the dataset gives
today (a dropped, added or moved row, a stale count, a passed window's result missing), when the FAQ count differs
from the rows, or when a /drug or /ticker link in the block has no page. Plants each fault first.

    python tests/test_readout_months.py      (fix: python build_readout_months.py)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_readout_months as M  # noqa: E402

SITE = M.SITE
BLOCK = re.compile(re.escape(M.B) + r".*?" + re.escape(M.E), re.S)


def expected(pages):
    today = M.eastern_today()
    rows = M.load_rows(M.DATASET)
    return {ym: M.render(rows, ym, today, SITE) for ym in pages}


def check(docs, exp):
    probs = []
    for ym, doc in docs.items():
        blk, n = exp[ym]
        m = BLOCK.search(doc)
        if not m:
            probs.append(f"/readouts/{ym}: no RMONTH block (the rows are not rebuilt from the dataset)")
            continue
        if m.group(0) != blk:
            probs.append(f"/readouts/{ym}: rows are not what the dataset gives today")
        for c in re.findall(r"currently tracks (\d+) clinical-trial readouts", doc):
            if int(c) != n:
                probs.append(f"/readouts/{ym}: FAQ says {c} readouts, the page lists {n}")
        for kind, slug in re.findall(r'href="/(drug|ticker)/([^"/#?]+)"', m.group(0)):
            if not os.path.isfile(os.path.join(SITE, kind, slug, "index.html")):
                probs.append(f"/readouts/{ym}: links /{kind}/{slug}, which does not exist")
    return probs


def main():
    pages = dict(M.month_pages(SITE))
    docs = {ym: io.open(p, encoding="utf-8").read() for ym, p in pages.items()}
    exp = expected(pages)
    plants = []
    busy = [ym for ym in docs if exp[ym][1] > 1]
    if busy:
        t = busy[0]
        d = dict(docs); d[t] = BLOCK.sub("", d[t]); plants.append(("block dropped", d))
        d = dict(docs); d[t] = re.sub(r'<div class="row">.*?</div></div>', "", d[t], count=1)
        plants.append(("row dropped", d))
        d = dict(docs); d[t] = re.sub(r"currently tracks \d+", "currently tracks 999", d[t], count=1)
        if d[t] != docs[t]:
            plants.append(("FAQ count off", d))
        d = dict(docs); d[t] = d[t].replace('href="/drug/', 'href="/drug/zz-no-such-', 1)
        plants.append(("dead drug link", d))
    missed = [n for n, d in plants if not check(d, exp)]
    if missed:
        print(f"FAIL: the checker missed planted faults: {missed}")
        return 1
    probs = check(docs, exp)
    if probs:
        print(f"FAIL test_readout_months: {len(probs)} problem(s); fix: python build_readout_months.py")
        for p in probs[:20]:
            print("  " + p)
        return 1
    n = sum(e[1] for e in exp.values())
    print(f"OK -- {len(docs)} readout month pages list {n} readouts, each matching today's dataset; "
          f"{len(plants)} planted faults caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
