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
