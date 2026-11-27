# -*- coding: utf-8 -*-
"""CI guard: each company hub (/ticker/<T>) states exactly the earnings dates and FDA device decisions its own
pages hold (2026-11-27).

inject_ticker_crosslinks.py writes the TXL block from _earnings_dates.json and _fda_devices.json with the same rules
as /earnings/<T> and /devices/decisions. Fails when a hub's block is not the block those caches give today (a stale
date, a dropped or extra row, a hub with an earnings page that does not link it, a block on a hub with nothing to
show), or when the block links an earnings page that does not exist. Plants each fault first.

    python tests/test_ticker_crosslinks.py      (fix: python inject_ticker_crosslinks.py)
"""
import collections
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import inject_ticker_crosslinks as X  # noqa: E402

SITE = X.SITE


def expected():
    today = X.E.eastern_today()
    T, pages = {}, set()
    if os.path.isfile(X.E.CACHE):
        _, T = X.E.load(X.E.CACHE)
        pages = {tk for tk, t in T.items() if X.E.has_page(t, today)
                 and os.path.isfile(os.path.join(SITE, "earnings", tk, "index.html"))}
    by_tk = collections.defaultdict(list)
    if os.path.isfile(X.D.CACHE):
        for r in X.D.load(X.D.CACHE)[1]:
            if X.D.ticker_of(r):
                by_tk[X.D.ticker_of(r)].append(r)
    return {tk: X.block(tk, T, pages, today, by_tk, SITE) for tk in hubs()}


def hubs():
    root = os.path.join(SITE, "ticker")
    return sorted(t for t in os.listdir(root) if os.path.isfile(os.path.join(root, t, "index.html")))


def check(docs, exp):
    probs = []
    for tk, doc in docs.items():
        m = X.BLOCK.search(doc)
        have = m.group(0) if m else ""
        if have != exp.get(tk, ""):
            probs.append(f"/ticker/{tk}: earnings/device block is not what the caches give today")
        for e in re.findall(r'href="/earnings/([A-Z0-9.]+)"', have):
            if not os.path.isfile(os.path.join(SITE, "earnings", e, "index.html")):
                probs.append(f"/ticker/{tk}: links /earnings/{e}, which does not exist")
    return probs


def main():
    exp = expected()
    docs = {tk: io.open(os.path.join(SITE, "ticker", tk, "index.html"), encoding="utf-8").read() for tk in hubs()}
    with_e = [tk for tk in docs if 'id="earnings"' in exp.get(tk, "")]
    with_d = [tk for tk in docs if 'id="devices"' in exp.get(tk, "")]
    empty = [tk for tk in docs if not exp.get(tk)]
    plants = []
    if with_e:
        t = with_e[0]; d = dict(docs); d[t] = X.BLOCK.sub("", d[t]); plants.append(("block dropped", d))
        d = dict(docs); d[t] = re.sub(r'(<span class="t">)[A-Z][a-z]{2} \d', r"\g<1>Jan 9", d[t], count=1)
        plants.append(("date altered", d))
    if with_d:
        t = with_d[0]; d = dict(docs); d[t] = d[t].replace('</h2><a class="row"', '</h2>', 1)
        plants.append(("device row dropped", d))
    if empty:
        t = empty[0]; d = dict(docs); d[t] = d[t].replace(X.ANCHORS[2], X.B + '<h2 id="earnings">x</h2>' + X.END + X.ANCHORS[2], 1)
        plants.append(("block on a hub with nothing to show", d))
    missed = [n for n, d in plants if not check(d, exp)]
    if missed:
        print(f"FAIL: the checker missed planted faults: {missed}")
        return 1
    probs = check(docs, exp)
    if probs:
        print(f"FAIL test_ticker_crosslinks: {len(probs)} problem(s); fix: python inject_ticker_crosslinks.py")
        for p in probs[:20]:
            print("  " + p)
        return 1
    print(f"OK -- {len(docs)} hubs: {len(with_e)} link their earnings page, {len(with_d)} list FDA device decisions, "
          f"each matching the caches; {len(plants)} planted faults caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
