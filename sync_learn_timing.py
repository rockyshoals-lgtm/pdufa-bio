# -*- coding: utf-8 -*-
"""One source for the decision-timing statistic on /learn/what-is-a-pdufa-date.

Audit 2026-09-08c item 2: the explainer's meta description told the SERP "In 2026, 15 of 26
sourced decisions came early" while /calendar (fed by build_early_decisions.collect() via
inject_calendar_explainer.timing_split) said 32 decisions, 20 early. Same statistic, two
numbers, and the stale one was the snippet Bing and Google display. The learn page is
hand-written HTML with no generator, so the numbers were typed once and never moved.

This script owns those numbers on that page. It rewrites, in place and idempotently:
  - the meta description / og:description sentence "In 2026, N of M sourced decisions came early."
  - the body sentence "of the M sourced 2026 decisions in <a ...>our decision-timing study</a>,
    N came before the goal date, O landed on it and L came after it"
from timing_split(), the same function /calendar renders from. tests/test_learn_timing_matches_calendar.py
asserts the two pages agree.
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PAGE = os.path.join(HERE, "pdufa_site_src", "learn", "what-is-a-pdufa-date", "index.html")

META_RE = re.compile(r"In 2026, \d+ of \d+ sourced decisions came early\.")
BODY_RE = re.compile(r"of the \d+ sourced 2026 decisions in (<a [^>]*>our decision-timing study</a>), "
                     r"\d+ came before the goal date, \d+ landed on it and \d+ [^.<]*")


def main():
    from inject_calendar_explainer import timing_split
    n, early, on, late, _biggest = timing_split()
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    meta = f"In 2026, {early} of {n} sourced decisions came early."
    new = META_RE.sub(meta, doc)
    new = BODY_RE.sub(lambda m: (f"of the {n} sourced 2026 decisions in {m.group(1)}, {early} came "
                                 f"before the goal date, {on} landed on it and {late} came after it"),
                      new)
    if new != doc:
        io.open(PAGE, "w", encoding="utf-8").write(new)
        print(f"learn timing: rewritten to {early} of {n} early, {on} on, {late} late")
    else:
        print(f"learn timing: already {early} of {n} early, {on} on, {late} late")
    if not META_RE.search(new):
        print("WARN: meta sentence not found on the learn page; nothing owned")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
