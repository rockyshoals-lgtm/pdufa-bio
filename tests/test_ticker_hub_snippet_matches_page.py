# -*- coding: utf-8 -*-
"""A ticker hub's snippet must say what the hub itself says, and must not read as truncated.

Audit 2026-09-09 items 1 and 2. /ticker/PFE shipped a title and H1 reading "Pfizer Inc."
(fixed 09-08 by majority vote) over a description reading "Roivant/Priovant (PFE) FDA
catalysts. Next: Readout Oct 2026 for Palbociclib. 1 FDA decision on record." -- a different
company, a catalyst the page's own summary says does not exist, and a decision count of 1
against the 10 rows rendered below it. The description is written last, by
fix_meta_lengths.ticker_desc, which had rebuilt it from its own dataset-derived map instead of
from the page. "pfizer pfe pdufa dates fda approval decisions 2026 2027" earned 82 Bing
impressions at position 3.23 and zero clicks under that snippet.

Contract, for every /ticker/{TK} page carrying the rendered summary `<div class="sub">`:
  1. the description names the same company the <h1> names;
  2. when the summary states a decision count, the description states the same count;
  3. the title does not end mid-word, on a dangling function word, or on an open bracket.

Proved 0 -> 1 -> 0 on 2026-09-09 by planting the live PFE description back into the page.
"""
import glob
import html
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

SUB = re.compile(r'<div class="sub">(.*?)</div>', re.S)
H1 = re.compile(r"<h1>(.*?)<span", re.S)
DESC = re.compile(r'<meta name="description" content="([^"]*)"')
TITLE = re.compile(r"<title>([^<]*)</title>")
DECISIONS = re.compile(r"(\d+)\s+past FDA decision")
# the description may phrase it either way ("10 past FDA decisions", "1 FDA decision on record")
DESC_DECISIONS = re.compile(r"(\d+)\s+(?:past\s+)?FDA decision")
# A dangling function word or an unclosed bracket reads as truncated on its own.
DANGLING = re.compile(r"(?:\b(?:in|and|for|with|plus|of|the|a|to)|\()\s*$", re.I)
# Mid-word is judged against the PAGE, not by guessing at the shape of the last token. A first
# attempt flagged any trailing one- or two-letter token and produced three false positives on
# real names ("ALPHA-1 MP", "Deucrictibant IR", "Neffy 1 mg"). Titles legitimately carry a
# truncated drug name; what makes "...(encorafenib) in co" wrong is that the page continues
# "...in combination", so the cut lands inside a word.



def _text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def test_ticker_hub_snippet_matches_page():
    bad, seen = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html"))):
        tk = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        sub, h1, dm, tm = SUB.search(doc), H1.search(doc), DESC.search(doc), TITLE.search(doc)
        if not (sub and h1 and dm):
            continue
        seen += 1
        company, desc = _text(h1.group(1)), html.unescape(dm.group(1))

        if company and company.split("(")[0].strip()[:18] not in desc:
            bad.append(f"/ticker/{tk}: h1 says {company!r}, description says {desc[:70]!r}")

        want = DECISIONS.search(_text(sub.group(1)))
        got = DESC_DECISIONS.search(desc)
        if want and got and want.group(1) != got.group(1):
            bad.append(f"/ticker/{tk}: page shows {want.group(1)} past decisions, "
                       f"description claims {got.group(1)}")

        if tm:
            stem = re.sub(r"\s*\|\s*pdufa\.bio\s*$", "", html.unescape(tm.group(1))).rstrip()
            if DANGLING.search(stem):
                bad.append(f"/ticker/{tk}: title reads as truncated: {stem!r}")
            clause = stem.split(":", 1)[1].strip() if ":" in stem else ""
            # last listed asset only; the earlier ones are whole by construction
            clause = clause.rsplit(", ", 1)[-1]
            if len(clause) > 3:
                page = _text(doc)
                i = page.find(clause)
                if i >= 0 and page[i + len(clause):i + len(clause) + 1].isalnum():
                    bad.append(f"/ticker/{tk}: title cuts mid-word: {clause!r} continues "
                               f"{page[i:i + len(clause) + 12]!r} on the page")

    assert seen > 0, "no ticker hub with a rendered summary found -- guard cannot see"
    assert not bad, ("ticker hub snippet(s) disagreeing with the page or reading as truncated "
                     "(the /ticker/PFE class):\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    test_ticker_hub_snippet_matches_page()
    print("OK")
