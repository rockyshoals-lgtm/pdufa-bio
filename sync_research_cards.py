# -*- coding: utf-8 -*-
"""Keep the /research index cards' numbers equal to the pages they link.

Red team 2026-09-06d, section 4: two cards were stale by two builds -- "Mean price path …
1,754 events" while /runup-by-year says "Medians throughout" and 1,845, and "256
presentations" while the conference study says 1,425. Gemini quoted them accurately and
we called Gemini wrong. Cards are hand-written HTML with no owner; this gives them one.

Numbers come from the same files the linked pages are built from
(runup_study_stats.json, _conference_runup_stats.json), never typed here.
test_research_cards_match_pages.py asserts the render.
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "research", "index.html")


def main():
    n_runup = json.load(io.open(os.path.join(HERE, "runup_study_stats.json"),
                                encoding="utf-8"))["n_events"]
    n_conf = json.load(io.open(os.path.join(HERE, "_conference_runup_stats.json"),
                               encoding="utf-8"))["_events"]
    t = io.open(PAGE, encoding="utf-8", errors="replace").read()
    orig = t

    # Card: PDUFA run-up by year. Medians throughout, n from the study file.
    t = re.sub(r"Mean price path into FDA decisions, T-120&rarr;T\+5, by year: [\d,]+ events",
               f"Median price path into FDA decisions, T-120&rarr;T+5, by year: {n_runup:,} events",
               t)
    t = re.sub(r"(Median price path into FDA decisions, T-120&rarr;T\+5, by year: )[\d,]+ events",
               lambda m: f"{m.group(1)}{n_runup:,} events", t)

    # Card: conference run-up study. n and the real year span (2017-2026).
    t = re.sub(r"[\d,]+ presentations, 20\d\d-20\d\d\.",
               f"{n_conf:,} presentations, 2017-2026.", t)

    if t != orig:
        io.open(PAGE, "w", encoding="utf-8").write(t)
        print(f"research cards synced: run-up n={n_runup:,} (median), conference n={n_conf:,}")
    else:
        print("research cards: already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
