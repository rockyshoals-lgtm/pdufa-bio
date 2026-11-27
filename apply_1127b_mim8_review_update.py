# -*- coding: utf-8 -*-
"""apply_1127b_mim8_review_update.py -- Mim8 (denecimig): Novo's Oct 2, 2026 update on the US review.

Novo Nordisk, "Novo provides update on the denecimig Biologics License Application (BLA) in the US", 2 October 2026
(read 2026-11-27 at novonordisk.com, news id 917287): the FDA review is ongoing; "the ongoing facility remediation
activities are the cause for extension of the Agency's review"; "The FDA has not communicated a new timeline for expected
regulatory action on the BLA"; the decision had been anticipated "in the third quarter of 2026"; "Pending regulatory
decision, Novo aims to launch denecimig in the US in the first half of 2027." The Q3 2026 6-K (Nov 4) repeats that the
BLA review is ongoing and extended, and that the FDA has not identified deficiencies in the efficacy or safety data.

Writes _d.review_update on the row; fix_not_announced_pages.py shows it on /pdufa/NVO-mim8. The row stays
"goal date not announced" (David's ruling, 2026-11-10). Idempotent. Facts only, not investment advice.
"""
import io, json, os

H = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(H, "pdufa_site_src", "api", "v1", "dataset.mjs")
ID = "pdufa_nvo_mim8_2026-09-30"
UPD = {
    "date": "2026-10-02",
    "source": "Novo Nordisk company announcement, 2 October 2026",
    "source_url": "https://www.novonordisk.com/news-and-media/news-and-ir-materials/news-details.html?id=917287",
    "text": ("Earlier, on October 2, 2026, Novo Nordisk said the FDA had extended its review of the denecimig BLA, which Novo had "
             "expected to be decided in the third quarter of 2026. Novo said the FDA named the ongoing remediation at a "
             "manufacturing facility as the cause, and that the FDA has not given a new timeline."),
    "quote": "The FDA has not communicated a new timeline for expected regulatory action on the BLA.",
    "checked": "2026-11-27",
}

s = io.open(P, encoding="utf-8").read()
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
n = 0
for r in rows:
    if r.get("id") == ID:
        d = r.setdefault("_d", {})
        if d.get("review_update") != UPD:
            d["review_update"] = UPD
            n += 1
if n:
    io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("mim8 review update:", "written" if n else "already there")
