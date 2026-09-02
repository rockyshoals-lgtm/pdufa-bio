# -*- coding: utf-8 -*-
"""A decision page's meta description must ANSWER the query, not name the page.

SEO audit 2026-09-02b: /fda-decision/RARE-2026-08-19 sat at position 3.70 with zero
clicks -- its description read "FDA decision Aug 19, 2026: Approved." (a label). The
template is entering the index now and scales across the 455-page corpus, so a
regression here compounds. rewrite_decision_snippets.py runs daily; this guard asserts
the RESULT on every 2026+ page with a verifiable outcome: the description must state
what happened to the drug in a sentence ("was approved on" / "received a Complete
Response Letter on" / "was withdrawn on"). Pre-2026 legacy formats and pages whose
outcome is unverified (price-only) are exempt -- an unverified page must NOT assert.
"""
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

ANSWER = re.compile(r"was approved on|received a Complete Response Letter on|"
                    r"was withdrawn on")


def test_decision_descriptions_answer():
    bad, checked = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"[A-Z]{1,6}-(\d{4})-\d{2}-\d{2}$", slug)
        if not m or int(m.group(1)) < 2026:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "outcome unverified" in doc.lower() or "price-only" in doc.lower():
            continue
        tm = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
        ttl = tm.group(1) if tm else ""
        if not re.search(r"Approved|CRL|Complete Response|Withdrawn", ttl, re.I):
            continue          # outcome not stated anywhere machine-readable -- separate problem
        dm = re.search(r'name="description" content="([^"]*)"', doc)
        checked += 1
        if not dm or not ANSWER.search(dm.group(1)):
            bad.append(f"/fda-decision/{slug}: description labels instead of answering")
    assert checked > 100, f"only {checked} 2026 decision pages checked -- glob broken?"
    assert not bad, ("decision pages with label-style descriptions -- run "
                     "rewrite_decision_snippets.py:\n  " + "\n  ".join(bad[:10])
                     + (f"\n  ... and {len(bad) - 10} more" if len(bad) > 10 else ""))


if __name__ == "__main__":
    test_decision_descriptions_answer()
    print("OK")
