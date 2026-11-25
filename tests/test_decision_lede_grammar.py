"""Guard: a decision page's lede reads as a sentence after "approved by the FDA ... for".

2026-11-25: indications stored in the FDA's use-text form published "approved by the FDA for reduce the occurrence ...",
"... for in combination with sunitinib, adults with ...", "... for single agent, adjuvant treatment ...",
"... for with an androgen receptor pathway inhibitor, ..." and "... for to reduce ..." on six pages.
build_decision_lede.lede_what() words them; this fails if any lede on the site slips back.
"""
import glob
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
BAD = re.compile(r"approved by the FDA(?: on [A-Z][a-z]+ \d{1,2}, \d{4})? for (?:to |in combination |with |single[- ]agent|"
                 r"as |in |reduce |prevent |treat |lower |delay |improve |maintain )", re.I)


def main():
    import build_decision_lede as b
    cases = {
        "reduce the occurrence of infections": " to reduce the occurrence of infections",
        "to reduce the risk of stroke": " to reduce the risk of stroke",
        "in combination with sunitinib, adults with GIST": " for adults with GIST, in combination with sunitinib",
        "single agent, adjuvant treatment of adults": " for adjuvant treatment of adults, as a single agent",
        "Lower-grade glioma": " for lower-grade glioma",
        "Treatment-resistant depression": " for treatment-resistant depression",
    }
    fails = [f"lede_what({k!r}) = {b.lede_what(k)!r}, expected {v!r}" for k, v in cases.items() if b.lede_what(k) != v]
    n = 0
    for f in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        d = open(f, encoding="utf-8").read()
        m = re.search(r"<!--FACTLEDE:BEGIN-->(.*?)<!--FACTLEDE:END-->", d, re.S)
        if not m:
            continue
        n += 1
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        for x in BAD.finditer(t):
            fails.append(f"{os.path.basename(os.path.dirname(f))}: {t[max(0, x.start() - 30):x.end() + 40]!r}")
    if fails:
        print(f"FAIL test_decision_lede_grammar: {len(fails)} problem(s); fix: python build_decision_lede.py")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision ledes read as sentences after 'approved by the FDA ... for'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
