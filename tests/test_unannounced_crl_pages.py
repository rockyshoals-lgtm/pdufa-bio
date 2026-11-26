"""Pages for FDA letters the sponsor never announced must not claim a same-day or linked company announcement.

2026-11-26: ALVO-2025-11-24 went live saying "The sponsor announced it the same day." and "the company's own
announcement is linked on this page" although Alvotech never announced the letter.
"""
import glob
import re

UNANNOUNCED = re.compile(r"did not announce (?:the|this) letter on its date")
BAD = ("announced it the same day", "company's own announcement is linked")


def test_unannounced_letters_claim_no_announcement():
    bad = []
    for p in glob.glob("pdufa_site_src/fda-decision/*/index.html"):
        t = open(p, encoding="utf-8").read()
        if UNANNOUNCED.search(t):
            bad += [f"{p}: {b}" for b in BAD if b in t]
    assert not bad, "\n".join(bad)
