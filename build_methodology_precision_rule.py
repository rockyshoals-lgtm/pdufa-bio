# -*- coding: utf-8 -*-
"""Audit 09-15 ORDER 6: publish the date-precision rule on /methodology, between
<!--PRECISION:BEGIN--> and <!--PRECISION:END--> so reruns replace rather than duplicate.
The section is inserted before the calendar CTA. Idempotent.

    python build_methodology_precision_rule.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "pdufa_site_src", "methodology", "index.html")
ANCHOR = '<a class="cta" href="/calendar">'

BLOCK = """<!--PRECISION:BEGIN--><h2 id="date-precision">How a date gets its precision</h2>
<p class="sub">Every event row carries a <code>date_precision</code> of <b>day</b>, <b>month</b>, <b>quarter</b> or <b>year</b>, and the row means exactly that much. A day-precision row is a calendar day a sponsor or the FDA stated in a filing, a release or an FDA notice, and we link the document. A coarser row is the window the sponsor gave (&ldquo;third quarter of 2026&rdquo;) or the ClinicalTrials.gov primary-completion estimate, and we say which. Three rules decide what happens when two statements about the same event disagree:</p>
<div class="grid">
<div class="kv"><span>1. The most recent stated day wins</span><b>A sponsor that said September 26 in May and November 22 in August moved the date. The later day is the date; the earlier one stays on the row as <code>date_history</code>, with the filing that moved it.</b></div>
<div class="kv"><span>2. A quarter is never rounded to a day</span><b>&ldquo;Q3 2026&rdquo; is published as Q3 2026, in the calendar and in the API, with <code>date: null</code>. We do not turn a quarter into September 30 or a month into the 15th, and a row we cannot source to a stated day is downgraded to the window we can source, not annotated.</b></div>
<div class="kv"><span>3. A later window does not override an earlier day</span><b>A 10-Q that says &ldquo;third quarter&rdquo; after an 8-K that said September 26 is the same date at lower resolution, not a change. The day stands. If the later window does not contain the day, the two statements conflict and a person settles it against the filings before anything is published.</b></div>
</div>
<p class="sub">The rule runs inside the harvester, where two statements first meet, and again as a build guard on the dataset the API ships. The API exposes <code>date_precision</code>, <code>source_url</code> and <code>date_history</code> on every row so you can hold us to it.</p><!--PRECISION:END-->"""


def main():
    t = io.open(PAGE, encoding="utf-8").read()
    t = re.sub(r"<!--PRECISION:BEGIN-->.*?<!--PRECISION:END-->", "", t, flags=re.S)
    if ANCHOR not in t:
        print("FAIL: calendar CTA anchor not found on /methodology"); return 1
    t = t.replace(ANCHOR, BLOCK + ANCHOR, 1)
    io.open(PAGE, "w", encoding="utf-8").write(t)
    print("/methodology: date-precision rule section written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
