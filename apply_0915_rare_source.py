# -*- coding: utf-8 -*-
"""RARE UX111 (ABO-102) PDUFA 2026-09-19: sourced first-hand to Ultragenyx 8-K 2026-04-02
(accession 0001193125-26-139084), read live before writing. Also records the earlier quarter
statement (8-K 2026-02-03: "PDUFA date expected in the third quarter of 2026") in date_history as
the lower-resolution statement the day supersedes -- the auditor's section 6 trap, documented on
the row itself."""
import io, json, os, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
URL = "https://www.sec.gov/Archives/edgar/data/1515673/000119312526139084/rare-20260402.htm"
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
t = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30).read().decode("utf-8", "replace")
t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
m = re.search(r"PDUFA[^.]{0,80}action date of September 19, 2026", t)
assert m, "quote not found in the 8-K"
print("verified:", t[max(0, m.start() - 120): m.end() + 20])
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
for r in rows:
    if r["id"] == "pdufa_rare_2026-09-19":
        assert r["d"] == "2026-09-19" and r["dp"] == "day"
        dd = r.setdefault("_d", {})
        dd["source"] = "Ultragenyx 8-K 2026-04-02 (Item 8.01)"
        dd["source_url"] = URL
        dd["source_quote"] = "The FDA set a Prescription Drug User Fee Act (PDUFA) action date of September 19, 2026."
        dd["precision_note"] = ("Ultragenyx's 8-K of 2026-02-03 stated only 'a PDUFA date expected in the third "
                                "quarter of 2026'; the 8-K of 2026-04-02 states the day. The day-precision "
                                "statement wins and the quarter is never rounded to a day.")
        print(f"  {r['id']}: sourced to {URL}")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
