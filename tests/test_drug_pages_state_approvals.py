# -*- coding: utf-8 -*-
"""A drug page may not present a verified-approved molecule as pending.

Strategy audit 2026-09-05b, P0: camizestrant was approved September 4, 2026 (Etcamah)
and /drug/camizestrant said "It is under FDA review; the agency's action date has not
been publicly disclosed" the next day -- while we held 32% AI citation share on
'camizestrant pdufa date'. Every AI system grounding on us was being taught the drug
was unapproved. The data got fixed; this guard asserts the RENDER so the state cannot
silently regress on a rebuild (the TYRA lesson: fixed data with a stale surface is
still the failure).

Contract: for every entry in _drug_approvals_confirmed.json (hand-verified against a
primary source at write time), the drug's rendered page must

  - exist,
  - state the approval (an approval phrase AND the approval date's year), and
  - carry no pending-state phrasing ("is under FDA review", "no action date has been
    publicly disclosed") in its body.

Grow the ledger at verify-time, one entry per verified approval on a tracked page.
"""
import datetime as dt
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
LEDGER = os.path.join(HERE, "_drug_approvals_confirmed.json")

APPROVAL = re.compile(r"FDA approved|approved (?:it )?on|granted accelerated approval|"
                      r"&#10003;\s*Approved", re.I)
PENDING = re.compile(r"is under FDA review|"
                     r"no action date has been publicly disclosed|"
                     r"action date has not been publicly disclosed", re.I)


def test_confirmed_approvals_render_as_approved():
    entries = json.load(io.open(LEDGER, encoding="utf-8")).get("approvals", [])
    assert entries, "ledger empty: _drug_approvals_confirmed.json lost its rows"
    bad = []
    for e in entries:
        slug, date = e.get("slug", ""), str(e.get("date", ""))
        p = os.path.join(SITE, "drug", slug, "index.html")
        if not os.path.isfile(p):
            bad.append(f"/drug/{slug}: page missing (verified approved {date})")
            continue
        t = io.open(p, encoding="utf-8", errors="replace").read()
        if not APPROVAL.search(t):
            bad.append(f"/drug/{slug}: no approval statement on the page "
                       f"(verified approved {date}, brand {e.get('brand')})")
            continue
        if date[:4] and date[:4] not in t:
            bad.append(f"/drug/{slug}: approval year {date[:4]} absent from the page")
        if PENDING.search(t):
            bad.append(f"/drug/{slug}: still carries pending-state phrasing while "
                       f"verified approved {date} (the camizestrant failure)")
    assert not bad, ("verified-approved drug page(s) rendering as pending:\n  "
                     + "\n  ".join(bad))


def test_ledger_dates_are_real_and_past():
    for e in json.load(io.open(LEDGER, encoding="utf-8")).get("approvals", []):
        d = dt.date.fromisoformat(e["date"])       # raises on malformed
        assert d <= dt.date.today(), f"{e['slug']}: approval date {d} is in the future"
        assert e.get("source", "").startswith("http"), f"{e['slug']}: no source URL"


if __name__ == "__main__":
    test_confirmed_approvals_render_as_approved()
    test_ledger_dates_are_real_and_past()
    print("OK")


# Audit 2026-09-08c item 1: the description is the SERP snippet. /drug/camizestrant, our top
# AI entity, drew 29 Bing impressions at position 4.62 and zero clicks while its description
# read "FDA catalyst dates and outcomes" over a body that said "approved ... as Etcamah".
# Contract: a drug page whose latest real decision is an approval (the "&#10003; Approved"
# badge on its most recent decision row) must state that approval in its meta description.
DESC = re.compile(r'<meta name="description" content="([^"]*)"')
GENERIC = "FDA catalyst dates and outcomes"
ROW = re.compile(r'<a class="row" href="/fda-decision/[A-Z]{1,6}-(\d{4}-\d{2}-\d{2})"[^>]*>'
                 r'(.*?)</a>', re.S)


def test_approved_drug_pages_state_approval_in_description():
    import glob
    bad, seen = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        t = io.open(p, encoding="utf-8", errors="replace").read()
        rows = ROW.findall(t)
        if not rows:
            continue
        last_date, last_frag = max(rows, key=lambda x: x[0])
        if "Approved" not in last_frag:
            continue
        seen += 1
        m = DESC.search(t)
        desc = m.group(1) if m else ""
        if GENERIC in desc or not re.search(r"approved", desc, re.I):
            bad.append(f"/drug/{os.path.basename(os.path.dirname(p))}: latest decision "
                       f"{last_date} Approved but description reads {desc[:90]!r}")
    assert seen > 0, "no approved drug page found -- guard cannot see"
    assert not bad, ("approved drug page(s) whose snippet never says so (the camizestrant "
                     "29-impressions-0-clicks class):\n  " + "\n  ".join(bad))
