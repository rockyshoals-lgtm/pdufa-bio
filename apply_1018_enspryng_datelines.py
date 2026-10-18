# -*- coding: utf-8 -*-
"""apply_1018_enspryng_datelines.py -- Enspryng TED: name both sponsor datelines (audit 2026-10-18, 2c-3).

Genentech's release is datelined "South San Francisco, CA -- October 15, 2026" (gene.com, read 2026-10-16).
Roche's is datelined "Basel, 16 October 2026" (roche.com/media/releases/med-cor-2026-10-16, read 2026-10-18 22:40
UTC). Both are announcements; neither states the FDA's action day, which Drugs@FDA has not posted. Bing's answer
says "October 15-16" because the two aggregators it reads took one each. The row records the second dateline
(announcement_2), the verified-against line names both, and the decision page's note says so in a sentence.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ROCHE = "https://www.roche.com/media/releases/med-cor-2026-10-16"
s = io.open(D, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
r = next(x for x in rows if x["id"] == "pdufa_rhhby_2026-10-15")
r["_d"]["announcement_2"] = {"who": "Roche media release, Basel", "date": "2026-10-16", "url": ROCHE}
r["_d"]["decision_date_note"] = (
    "2026-10-15 is the dateline of Genentech's release (South San Francisco), which \"announced today\" that the FDA "
    "\"has approved\" Enspryng. Roche's own release carries the next day's dateline (Basel, 16 October 2026); both are "
    "announcements of the same approval, and neither states the day the FDA acted. Drugs@FDA had not posted the "
    "BLA 761149 supplement letter when this was published, so no early or late margin against the October 15 goal "
    "date is published until an FDA record states the action day.")
io.open(D, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])

# the decision page's prose: one sentence after the existing "does not state the day the FDA acted" clause
p = os.path.join(HERE, "pdufa_site_src", "fda-decision", "RHHBY-2026-10-15", "index.html")
t = io.open(p, encoding="utf-8", errors="replace").read()
add = (" Roche's own release of the same approval is datelined Basel, October 16, 2026 "
       f"(<a href=\"{ROCHE}\" rel=\"noopener\" style=\"color:#e3ba5e\">Roche release</a>), which is why October 15 and "
       "October 16 both circulate as the approval date; both are announcement dates.")
anchor = "The release does not state the day the FDA acted, and the FDA's letter for BLA 761149 had not been posted on Drugs@FDA when this page was published, so pdufa.bio holds no FDA record of the action day yet and computes no early or late margin."
if anchor in t and "datelined Basel" not in t:
    t = t.replace(anchor, anchor + add, 1)
    io.open(p, "w", encoding="utf-8").write(t)
    print("Enspryng page: Roche dateline sentence added")
else:
    print("Enspryng page: anchor missing or already present", anchor in t, "datelined Basel" in t)
print("row: announcement_2 set")
