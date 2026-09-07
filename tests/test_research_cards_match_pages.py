# -*- coding: utf-8 -*-
"""Every n on a /research index card equals the n on the page the card links.

Red team 2026-09-06d section 4: "Mean price path … 1,754 events" sat on /research while
/runup-by-year said "Medians throughout" and 1,845; "256 presentations" sat beside a FAQ
saying 1,425 three lines below. A stale index card is a live defect: it is what an AI
answer quoted back at us, accurately.

Contract (the render, not the process):
  - the run-up card says "Median", not "Mean", and its event count equals the count in
    runup_study_stats.json AND appears on /runup-by-year;
  - the conference card's presentation count equals _conference_runup_stats.json's
    `_events` AND appears on /research/conference-runup;
  - the retired numbers never reappear.
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def _read(*parts):
    return io.open(os.path.join(SITE, *parts), encoding="utf-8", errors="replace").read()


def test_research_cards_match_linked_pages():
    idx = _read("research", "index.html")
    n_runup = json.load(io.open(os.path.join(HERE, "runup_study_stats.json"),
                                encoding="utf-8"))["n_events"]
    n_conf = json.load(io.open(os.path.join(HERE, "_conference_runup_stats.json"),
                               encoding="utf-8"))["_events"]
    bad = []
    m = re.search(r"(Mean|Median) price path into FDA decisions[^<]*?([\d,]+) events", idx)
    if not m:
        bad.append("/research: run-up card sentence not found")
    else:
        if m.group(1) != "Median":
            bad.append(f"/research: run-up card says '{m.group(1)} price path' (study is medians)")
        if m.group(2) != f"{n_runup:,}":
            bad.append(f"/research: run-up card n={m.group(2)} but study n={n_runup:,}")
        if f"{n_runup:,}" not in _read("runup-by-year", "index.html"):
            bad.append(f"/runup-by-year does not state {n_runup:,}")
    m2 = re.search(r"([\d,]+) presentations, 20\d\d-20\d\d\.", idx)
    if not m2:
        bad.append("/research: conference card sentence not found")
    else:
        if m2.group(1) != f"{n_conf:,}":
            bad.append(f"/research: conference card n={m2.group(1)} but study n={n_conf:,}")
        if f"{n_conf:,}" not in _read("research", "conference-runup", "index.html"):
            bad.append(f"/research/conference-runup does not state {n_conf:,}")
    for stale in ("Mean price path", "1,754 events", "256 presentations"):
        if stale in idx:
            bad.append(f"/research still carries retired text: {stale!r}")
    assert not bad, "research index cards disagree with their pages:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_research_cards_match_linked_pages()
    print("OK")
