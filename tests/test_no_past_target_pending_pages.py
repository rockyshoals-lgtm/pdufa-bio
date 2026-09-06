# -*- coding: utf-8 -*-
"""No /pdufa/* page may still speak in the pending tense after its own target date.

Audit 2026-09-06 NEW-2. The decided-language guard added on 09-05b only looks at pages
that ALREADY carry a decision banner, so four pages with no banner sat weeks past their
stated goal dates telling readers a drug was "under FDA review": /pdufa/MRK-keytruda
(approved July 10, page target Aug 17), /pdufa/BIIB (approved July 13, target Aug 24),
/pdufa/ONC (approved Aug 25 under the partner's JAZZ ticker), and /pdufa/NRXP (ANDA goal
date July 29 passed, no decision disclosed). This is the check that would have caught
camizestrant a day earlier.

Contract: for every /pdufa/*/index.html whose stated target/goal date is before today
(Eastern -- the FDA's clock, and this machine runs Pacific), the page must not carry
pending-tense wording unless it also states what happened: a decision banner, or the
"goal date passed" block that says the date passed with no public decision.

The past-tense restatement ("was under FDA review, with a goal date of X that has
passed") is not a violation; the regex requires the present tense.
"""
import datetime as dt
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

PENDING = re.compile(r"\bis under FDA review\b|\bcandidate under FDA review\b", re.I)
# Resolution is asserted by a MARKER or by the page's own <title>, never by a loose scan.
# First cut used `FDA decision:.*?(Approved|...)` with DOTALL, which spans the whole
# document -- any page containing both phrases anywhere counted as resolved, and the
# planted failure passed. A guard that cannot fail is not a guard; scope it tightly.
RESOLVED = re.compile(r"<!--DECIDED:BEGIN-->|<!--PASSED:BEGIN-->")
RESOLVED_TITLE = re.compile(r"<title>[^<]*FDA decision:[^<]*"
                            r"(?:Approved|Complete Response|Withdrawn)[^<]*</title>", re.I)
TARGET = re.compile(r'<div class="kv"><span>FDA (?:PDUFA target date|goal date[^<]*)'
                    r'</span><b>(\d{4}-\d{2}-\d{2})</b>')
TARGET_ALT = re.compile(r"target date for [A-Z]{1,6} [^<]{0,200}?is (\d{4}-\d{2}-\d{2})")


def eastern_today():
    """The FDA's calendar day. This machine runs Pacific; Eastern is 3 hours ahead, so a
    Pacific-evening run is already tomorrow in Washington."""
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).date()


def test_no_past_target_pending_pages():
    today = eastern_today()
    bad = []
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = TARGET.search(doc) or TARGET_ALT.search(doc)
        if not m:
            continue
        try:
            target = dt.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if target >= today:
            continue
        if not PENDING.search(doc):
            continue
        if RESOLVED.search(doc) or RESOLVED_TITLE.search(doc):
            continue
        bad.append(f"/pdufa/{slug}: target {target} has passed and the page still says a "
                   f"drug 'is under FDA review', with no decision banner and no "
                   f"goal-date-passed statement")
    assert not bad, ("past-target page(s) still in the pending tense (the NEW-2 class):\n  "
                     + "\n  ".join(bad))


if __name__ == "__main__":
    test_no_past_target_pending_pages()
    print("OK")
