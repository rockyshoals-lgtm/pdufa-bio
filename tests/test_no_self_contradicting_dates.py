# -*- coding: utf-8 -*-
"""test_no_self_contradicting_dates.py -- nothing may say a date moved "from X to X".

Red team 2026-08-24. /pdufa/CAPR-deramiocel shipped this sentence:

    "The FDA moved this target action date from November 22, 2026 to November 22, 2026."

The data underneath was right; the TEXT was self-contradicting. Cause: refresh_moved_pdufa_pages
rewrites a page's stated date when the dataset moves it, and its replace ran over the extension
notice as well -- overwriting the historical "from" date with the new one. The date an event
moved AWAY from is deliberate history and the whole point of saying it moved, so the refresher
now freezes marked historical blocks. This guard is the belt to that braces: it fails on the
OUTPUT, whatever produced it, because a reader-facing factual contradiction is the class of bug
that most damages a site whose entire pitch is provenance -- and it is exactly the sort of
sentence an AI engine lifts verbatim.

Also catches the same shape in decision and calendar copy: "extended from X to X", "moved from
X to X", "postponed from X to X", "changed from X to X".
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

VERB = r"(?:moved|extended|changed|postponed|pushed|shifted|revised|updated)"
DATE = (r"(?:\d{4}-\d{2}-\d{2}"
        r"|(?:January|February|March|April|May|June|July|August|September|October|November"
        r"|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4})")
PAT = re.compile(rf"{VERB}[^.<]{{0,80}}?\bfrom\b\s*(?:<b>)?\s*({DATE})\s*(?:</b>)?"
                 rf"\s*\bto\b\s*(?:<b>)?\s*({DATE})", re.I)


def norm(s):
    """Compare dates by value, not spelling: 'Aug 22, 2026' == 'August 22 2026'."""
    s = re.sub(r"[.,]", " ", str(s)).strip().lower()
    s = re.sub(r"\s+", " ", s)
    months = {m[:3]: i for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august",
         "september", "october", "november", "december"], 1)}
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^([a-z]+)\s+(\d{1,2})\s+(\d{4})$", s)
    if m and m.group(1)[:3] in months:
        return (int(m.group(3)), months[m.group(1)[:3]], int(m.group(2)))
    return s


def main():
    bad = []
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if os.sep + "_" in p:
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        for m in PAT.finditer(doc):
            if norm(m.group(1)) == norm(m.group(2)):
                rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
                snip = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(0)))[:90]
                bad.append(f"{rel}: {snip}")

    if bad:
        print(f"FAIL: {len(bad)} page(s) claim a date moved from a value to the SAME value.")
        for b in bad[:8]:
            print(f"   {b}")
        print("\n   A 'from X to X' sentence is a factual self-contradiction on a page whose")
        print("   whole pitch is provenance, and AI engines quote sentences like this verbatim.")
        print("   Usually a date-rewriting pass ran over text that states history on purpose;")
        print("   historical blocks belong between <!--EXTN:BEGIN--> and <!--EXTN:END-->.")
        return 1
    print("  PASS: no page claims a date moved from a value to itself")
    return 0


if __name__ == "__main__":
    sys.exit(main())
