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


def test_letters_hub_lists_crls_as_crls():
    """2026-11-26: the /fda-approval-letters hub listed 28 archive CRLs as "Drugs@FDA record" (and the three
    unannounced letters as announced "same day"); a CRL row must name the Complete Response Letter."""
    t = open("pdufa_site_src/fda-approval-letters/index.html", encoding="utf-8").read()
    bad = []
    for row in re.findall(r"<tr>.*?</tr>", t, flags=re.S):
        cells = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)]
        if len(cells) < 5:
            continue
        if re.search(r"\bCRL$", cells[3]) and "Complete Response Letter" not in cells[3]:
            bad.append(f"CRL listed as {cells[3]!r}: {cells[1]}")
        for slug in re.findall(r'/fda-decision/([A-Z]+-\d{4}-\d{2}-\d{2})', row):
            p = f"pdufa_site_src/fda-decision/{slug}/index.html"
            try:
                doc = open(p, encoding="utf-8").read()
            except OSError:
                continue
            if UNANNOUNCED.search(doc) and cells[4] == "same day":
                bad.append(f"unannounced letter shown as same day: {slug}")
    assert not bad, "\n".join(bad)


if __name__ == "__main__":   # run_ci_guards.py runs each test file as a script
    import os
    import sys
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    fails = 0
    for fn in (test_unannounced_letters_claim_no_announcement, test_letters_hub_lists_crls_as_crls):
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {fn.__name__}:\n{e}")
    sys.exit(1 if fails else 0)
