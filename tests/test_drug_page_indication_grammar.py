# -*- coding: utf-8 -*-
"""A drug page's approved-use sentence reads as English.

2026-11-27 phone pass (/drug/bezuclastinib): "What is Ekitna used for?" answered "FDA-approved for in combination
with sunitinib, adults with advanced GIST ...". Other pages read "FDA-approved for reduce the occurrence of ...",
"igA Nephropathy", "parkinson's disease", "sanfilippo syndrome" and "thyroid Eye Disease", because the label text
was pasted after "for" with its first letter lower-cased. build_drug_pages.indication_clause now moves the label's
lead-in after the patients, writes "to reduce ...", and keeps acronyms, eponyms and title-case names as they are.

This fails when a built /drug page has "FDA-approved for" or "tracked on pdufa.bio:" followed by a lead-in
("in combination with", "with X,"), a bare verb, a lower-cased eponym or acronym, or a lower-cased word in front of
a title-case word; and when indication_clause gets any of the planted label texts wrong.

    python tests/test_drug_page_indication_grammar.py
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
LEAD = r"(?:FDA-approved for|tracked on pdufa\.bio:) "
BAD = [
    (re.compile(LEAD + r"(?:in combination with|with [^,<]{1,40},|as monotherapy)", re.I), "a label lead-in after 'for'"),
    (re.compile(LEAD + r"(?:reduce|prevent|treat|lower|improve|increase|delay|slow|maintain|induce)\b"), "a bare verb after 'for'"),
    (re.compile(LEAD + r"(?:igA|parkinson|alzheimer|sanfilippo|alexander disease|crohn|huntington|duchenne|fabry|pompe"
                r"|gaucher|hodgkin|cushing|graves)", re.I), None),
    (re.compile(LEAD + r"[a-z][a-z-]+ [A-Z][a-z]+\b(?! [a-z])"), "a lower-cased word before a title-case name"),
]
CASES = {
    "In combination with sunitinib, adults with advanced GIST who have received imatinib":
        "adults with advanced GIST who have received imatinib, in combination with sunitinib",
    "With BCG, adults with BCG-unresponsive bladder cancer; now includes papillary-only tumors":
        "adults with BCG-unresponsive bladder cancer, in combination with BCG; now includes papillary-only tumors",
    "Reduce the occurrence of surgical site infections": "to reduce the occurrence of surgical site infections",
    "IgA Nephropathy": "IgA Nephropathy",
    "Parkinson's disease in adults": "Parkinson's disease in adults",
    "Sanfilippo syndrome type A": "Sanfilippo syndrome type A",
    "Alexander disease": "Alexander disease",
    "Thyroid Eye Disease": "Thyroid Eye Disease",
    "Adults with symptomatic obstructive HCM": "adults with symptomatic obstructive HCM",
    "Primary IgA nephropathy": "primary IgA nephropathy",
    "Relapsed/refractory multiple myeloma": "relapsed/refractory multiple myeloma",
    "HIV": "HIV",
}


def page_problems(slug, doc):
    out = []
    for rx, why in BAD:
        m = rx.search(doc)
        if m:
            # the eponym pattern matches case-insensitively; only a lower-case first letter is wrong
            hit = m.group(0)
            if why is None:
                tail = re.sub(LEAD, "", m.group(0))
                if tail[:1].isupper():
                    continue
                why = "a lower-cased eponym or acronym"
            out.append(f"/drug/{slug}: {why}: {hit[:90]!r}")
    return out


def main():
    from build_drug_pages import indication_clause
    bad = [f"indication_clause({k!r}) gave {indication_clause(k)!r}, want {v!r}"
           for k, v in CASES.items() if indication_clause(k) != v]
    pages = sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html")))
    n = 0
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(LEAD, doc):
            n += 1
        bad += page_problems(os.path.basename(os.path.dirname(p)), doc)
    planted = ("FDA-approved for in combination with sunitinib, adults | tracked on pdufa.bio: igA Nephropathy | "
               "FDA-approved for reduce the occurrence | tracked on pdufa.bio: thyroid Eye Disease")
    if len(page_problems("planted", planted)) < 4:
        bad.append(f"planted bad sentences: {len(page_problems('planted', planted))} of 4 caught")
    if bad:
        print("FAIL test_drug_page_indication_grammar:")
        for b in bad[:20]:
            print("  -", b)
        print("  fix: build_drug_pages.indication_clause, then python build_drug_pages.py")
        return 1
    print(f"PASS test_drug_page_indication_grammar: {n} drug pages with an approved-use sentence, "
          f"{len(CASES)} label texts read as clauses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
