# -*- coding: utf-8 -*-
"""label_announcement_only_dates.py -- a decision page whose FDA action day is not on the FDA's record yet
states the announcement day AS the announcement day (2026-11-17 currency audit).

SMMT-2026-11-15, CYTK-2026-11-16 and TEVA-2026-11-16 carried, on the same page,
  "Verified against: FDA action day not yet posted on Drugs@FDA · Announcement November 16, 2026 (...)"
and, above it,
  "<h1>CYTK FDA decision: Nov 16, 2026</h1>"  ·  key facts "FDA decision date 2026-11-16"  ·  chart "FDA decision 11/16/26."
The 16th is the day the sponsor announced; the FDA's action may have come earlier (a weekend, a letter dated the
day before). The page asserted a fact its own Verified line says we do not have.

On every /fda-decision page whose Verified line says the FDA action day is not yet posted:
  * h1   "FDA decision: Nov 16, 2026"            -> "FDA decision: announced Nov 16, 2026"
  * kv   "FDA decision date | 2026-11-16"        -> "FDA decision date | not yet posted on Drugs@FDA" + "Announced | 2026-11-16"
  * chart caption "FDA decision 11/16/26."       -> "Decision announced 11/16/26."
Each change carries an <!--ANNONLY--> marker. When the Verified line later names the FDA record (sync_fda_action_dates
fills it), the page is put back to the canonical form, and fix_decision_h1_action_date / fix_chart_captions then state
the FDA day. Runs after inject_verified_against.py and before fix_decision_h1_action_date.py. Idempotent.
Guard: tests/test_announcement_only_dates.py. Facts only; not investment advice.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
# 2026-11-17 red team: "not yet posted on Drugs@FDA" was wrong for a device (Drugs@FDA never lists a PMA) and for a
# complete response letter (not a Drugs@FDA action). The line now says what we know: no public FDA record states the day.
NOT_POSTED_RX = re.compile(r"FDA action day (?:not yet posted|not found in a public FDA record)")
KV_TEXT = "not found in a public FDA record"
H1 = re.compile(r'(<h1>[A-Z][A-Z./ ]{0,12} <span class="g">FDA decision</span>: )([A-Z][a-z]{2} \d{1,2}, \d{4})(</h1>)')
H1_DONE = re.compile(r'(<h1>[A-Z][A-Z./ ]{0,12} <span class="g">FDA decision</span>: )<!--ANNONLY-->announced '
                     r'([A-Z][a-z]{2} \d{1,2}, \d{4})(</h1>)')
KV = re.compile(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b></div>')
KV_DONE = re.compile(r'<!--ANNONLY:KV--><div class="kv"><span>FDA decision date</span><b>(?:not yet posted on Drugs@FDA|not found in a public FDA record)</b></div>'
                     r'<div class="kv"><span>Announced</span><b>(\d{4}-\d{2}-\d{2})</b></div><!--/ANNONLY:KV-->')
CAP = re.compile(r"FDA decision (\d{1,2}/\d{1,2}/\d{2})\. ")
CAP_DONE = re.compile(r"<!--ANNONLY-->Decision announced (\d{1,2}/\d{1,2}/\d{2})\. ")


def verified_block(doc):
    m = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
    return m.group(1) if m else ""


def label(doc):
    doc = H1.sub(lambda m: m.group(1) + "<!--ANNONLY-->announced " + m.group(2) + m.group(3), doc, count=1)
    doc = KV.sub(lambda m: ('<!--ANNONLY:KV--><div class="kv"><span>FDA decision date</span><b>' + KV_TEXT +
                            '</b></div><div class="kv"><span>Announced</span><b>' + m.group(1) +
                            '</b></div><!--/ANNONLY:KV-->'), doc, count=1)
    doc = CAP.sub(lambda m: "<!--ANNONLY-->Decision announced " + m.group(1) + ". ", doc)
    return doc


def unlabel(doc):
    doc = H1_DONE.sub(lambda m: m.group(1) + m.group(2) + m.group(3), doc)
    doc = KV_DONE.sub(lambda m: f'<div class="kv"><span>FDA decision date</span><b>{m.group(1)}</b></div>', doc)
    doc = CAP_DONE.sub(lambda m: "FDA decision " + m.group(1) + ". ", doc)
    return doc


def main():
    n_lab = n_un = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "ANNONLY" not in doc and not NOT_POSTED_RX.search(doc):
            continue
        base = unlabel(doc)
        new = label(base) if NOT_POSTED_RX.search(verified_block(base)) else base
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            if NOT_POSTED_RX.search(verified_block(base)):
                n_lab += 1
                print(f"  labelled announcement-only: {os.path.relpath(p, SITE)}")
            else:
                n_un += 1
                print(f"  FDA day now on record, canonical form restored: {os.path.relpath(p, SITE)}")
    print(f"announcement-only decision pages labelled: {n_lab}; restored: {n_un}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
