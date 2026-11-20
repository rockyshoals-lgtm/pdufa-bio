# -*- coding: utf-8 -*-
"""apply_1118b_linzess_fda_day.py -- Linzess (linaclotide) pediatric supplement: the FDA acted May 21, 2026, not May 27.

/fda-decision/ABBV-2026-05-27 and /fda-decision/IRWD-2026-05-27 gave May 27, 2026 (the AbbVie / Ironwood
announcement day) as the FDA decision date. sync_archive_fda_dates.py found the record but would not assign it,
because it is 6 days before the announcement, outside its 0-4 day proximity rule. Read directly 2026-11-18 (UTC):
  Drugs@FDA, NDA 202811 (ABBVIE): SUPPL-23, action date 05/21/2026, Efficacy-New Patient Population; letter
  https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/202811Orig1s023ltr.pdf
This pins that date in _fda_action_archive.json with the same 'basis' shape as the 2026-11-18 red-team entries; the
sync keeps any entry that has a date. The pages keep their URLs (as SMMT and VENCLEXTA did); the rebuild chain shows
"FDA decision date 2026-05-21" with "Announced 2026-05-27". Facts only; not investment advice.
"""
import io, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_fda_action_archive.json")
LTR = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/202811Orig1s023ltr.pdf"
d = json.load(io.open(OUT, encoding="utf-8"))
for slug in ("ABBV-2026-05-27", "IRWD-2026-05-27"):
    e = d.get(slug) or {}
    e.update({"basis": "red team 2026-11-18: FDA record read directly (Drugs@FDA NDA 202811, SUPPL-23 action date "
                       "05/21/2026; 6 days before the announcement, outside the sync's 0-4 day rule)",
              "checked": "2026-11-18", "date": "2026-05-21", "oc": "Approved", "record": "NDA 202811 SUPPL-23",
              "class": "EFFICACY", "letter": LTR, "source_url": LTR, "name": "LINZESS (linaclotide)"})
    e.pop("reason", None)
    d[slug] = e
    print(f"  {slug}: FDA day 2026-05-21 (NDA 202811 SUPPL-23)")
io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + "\n")

# key facts: the FDA's day, then the public day (the shape apply_1118b_decision_sources.py writes)
ROWS = ('<div class="kv"><span>FDA decision date</span><b>2026-05-21</b></div>'
        '<div class="kv"><span>Announced</span><b>2026-05-27</b></div>')
for slug in ("ABBV-2026-05-27", "IRWD-2026-05-27"):
    p = os.path.join(HERE, "pdufa_site_src", "fda-decision", slug, "index.html")
    doc = io.open(p, encoding="utf-8").read()
    new, n = re.subn(r'<div class="kv"><span>FDA decision date</span><b>[^<]*</b></div>'
                     r'(?:<div class="kv"><span>Announced</span><b>[^<]*</b></div>)?', lambda m: ROWS, doc, count=1)
    assert n == 1, slug
    if new != doc:
        io.open(p, "w", encoding="utf-8").write(new)
    print(f"  {slug}: key facts FDA decision date 2026-05-21, Announced 2026-05-27")
