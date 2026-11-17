# -*- coding: utf-8 -*-
"""apply_1117b_crl_announcements.py -- 2026-11-17: two CRL pages cited the FDA letter as the company's announcement.

link_crl_letters.py made the FDA letter each row's decision_source, and these two rows had no separate
announcement field, so the Verified line's "Announcement" linked the letter under a truncated label
("FDA Complete Response Letter, NDA ..., dated"). Each page already cites the company's own release as
its primary source; this records that release as the announcement.

  Achieve Life Sciences, GlobeNewswire, "Achieve Life Sciences Receives Complete Response Letter from FDA
    for Cytisinicline NDA", dated June 22, 2026 8:30am EDT (ir.achievelifesciences.com, read 2026-11-17).
    FDA letter: CRL NDA 218995 dated 2026-06-20 (openFDA transparency/crl).
  Unicycive Therapeutics, GlobeNewswire, "Unicycive Therapeutics Receives Complete Response Letter from FDA
    Regarding Resubmitted Oxylanthanum Carbonate (OLC) NDA", dated June 30, 2026 7:05am EDT
    (ir.unicycive.com, read 2026-11-17). FDA letter: CRL NDA 218607 dated 2026-06-29.

Idempotent. Facts only; not investment advice.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")

WANT = {
    "pdufa_achv_2026-06-20": {
        "announcement": "Achieve Life Sciences press release, June 22, 2026",
        "announcement_url": ("https://ir.achievelifesciences.com/news-events/press-releases/detail/264/"
                             "achieve-life-sciences-receives-complete-response-letter-from-fda-for-cytisinicline-nda"),
        "announcement_date": "2026-06-22",
    },
    "pdufa_uncy_2026-06-29": {
        "announcement": "Unicycive Therapeutics press release, June 30, 2026",
        "announcement_url": ("https://ir.unicycive.com/news/detail/123/"
                             "unicycive-therapeutics-receives-complete-response-letter"),
        "announcement_date": "2026-06-30",
    },
}

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    w = WANT.get(r["id"])
    if not w:
        continue
    assert r["oc"] == "CRL" and r["dcd"] == w["announcement_date"], (r["id"], r["oc"], r["dcd"])
    d = r.setdefault("_d", {})
    if all(d.get(k) == v for k, v in w.items()):
        print(f"  {r['id']}: already set"); continue
    d.update(w)
    n += 1
    print(f"  {r['id']}: announcement -> {w['announcement']}")
if n:
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
print(f"{n} row(s) updated")
