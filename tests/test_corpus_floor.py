# -*- coding: utf-8 -*-
"""No build may quietly shrink a page corpus.

Final audit 2026-09-02: a routine daily refresh deleted 229 drug pages -- brand names,
the site's highest-intent queries -- and ALL 56 guards passed, because every guard
checked the correctness of what exists and none checked that things still exist. (Root
cause: build_drug_pages rebuilds /drug from decision-page TITLES, and the answer-format
title rewrite starved its parser; the by-design prune then deleted everything the
parser could no longer see.) The audit's words: "a floor guard that only protects the
thing someone complained about protects one thing. Make it protect the corpus."

Mechanics: _corpus_floor.json records the high-water page count per page type. A build
whose count falls below 95% of the floor FAILS. When a count grows, the floor rises
automatically (a ratchet, like the provenance baseline). A DELIBERATE shrink (retiring
a page family) must lower the floor by hand, in the same commit, with a reason -- that
is the point: shrinkage requires a human sentence.
"""
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
FLOOR_F = os.path.join(HERE, "_corpus_floor.json")
TYPES = ["drug", "pdufa", "fda-decision", "conference", "ticker", "condition", "learn"]


def counts():
    out = {}
    for t in TYPES:
        out[t] = len(glob.glob(os.path.join(SITE, t, "*", "index.html")))
    return out


def test_no_corpus_shrinks_silently():
    cur = counts()
    floors = {}
    if os.path.exists(FLOOR_F):
        floors = json.load(io.open(FLOOR_F, encoding="utf-8")).get("floors", {})

    bad, grew = [], False
    for t in TYPES:
        floor = floors.get(t, 0)
        if cur[t] < floor * 0.95:
            bad.append(f"/{t}/: {cur[t]} pages, floor {floor} "
                       f"(lost {floor - cur[t]}; >5% of the corpus)")
        elif cur[t] > floor:
            floors[t] = cur[t]
            grew = True
    if grew and not bad:
        json.dump({"note": "high-water page counts per type; a build below 95% of a "
                           "floor fails. Lower a floor BY HAND with a reason when a "
                           "shrink is deliberate.",
                   "floors": floors},
                  io.open(FLOOR_F, "w", encoding="utf-8"), indent=1)
    assert not bad, ("page corpus shrank -- the 229-deleted-drug-pages failure mode:\n  "
                     + "\n  ".join(bad)
                     + "\n  If deliberate, lower _corpus_floor.json by hand with a reason.")


if __name__ == "__main__":
    test_no_corpus_shrinks_silently()
    print("OK", counts())
