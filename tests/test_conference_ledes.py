# -*- coding: utf-8 -*-
"""CI guard: every per-conference page opens with one fact-first sentence (audit 2026-10-03, item 3.4).

Fails, on the rendered /conference/{CODE} pages, when the lede is missing, when its dates are not the
page's own Dates fact, or when its tense disagrees with the Eastern date (takes place / is under way /
took place).

    python tests/test_conference_ledes.py
"""
import glob
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from inject_conference_lede import parse_span, span_words  # noqa: E402
from site_dates import eastern_today  # noqa: E402


def main():
    today = eastern_today()
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(HERE, "pdufa_site_src", "conference", "*", "index.html"))):
        code = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        dm = re.search(r"<span>Dates</span><b>([^<]+)</b>", doc)
        sp = parse_span(html.unescape(dm.group(1))) if dm else None
        if not sp:
            continue
        n += 1
        lm = re.search(r"<!--CONFFACT:BEGIN--><p[^>]*>(.*?)</p><!--CONFFACT:END-->", doc, re.S)
        if not lm:
            fails.append(f"/conference/{code}: no fact-first lede")
            continue
        txt = html.unescape(lm.group(1))
        a, b = sp
        if span_words(a, b) not in txt:
            fails.append(f"/conference/{code}: lede dates {txt!r} disagree with the Dates fact {dm.group(1)!r}")
        want = "took place" if b < today else ("is under way" if a <= today else "takes place")
        if want not in txt:
            fails.append(f"/conference/{code}: tense should be '{want}' on {today}: {txt!r}")
    if fails:
        print(f"FAIL: {len(fails)} conference lede failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} conference pages open with a dated, correctly tensed sentence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
