# -*- coding: utf-8 -*-
"""apply_1117_smmt_crl_letter.py -- the FDA released Summit's ivonescimab letter; the FDA action day is November 13.

Rebuild run 44152651622 (2026-11-17, BLOCKED issue #95): link_crl_letters.py found the FDA's own Complete Response
Letter for BLA 761524 in openFDA's CRL release and gave the dataset row the FDA action date, but the page's Verified
line and chart caption had already been written from the row without it, so two guards failed and the run never
committed. Nothing persisted, so every later run would fail the same way.

Primary source, read 2026-11-17 (openFDA transparency/crl, file CRL_BLA761524_20261113.pdf, hosted by FDA):
  letter_date "11/13/2026", letter_type "COMPLETE RESPONSE", company "Summit Therapeutics Inc.", BLA 761524,
  electronic signature "11/13/2026 02:08:40 PM". The letter refers to the BLA "dated and received November 14, 2025"
  for "AK112/SMT112 (also referred to by the Applicant as ivonescimab)".
So the FDA acted on 2026-11-13, one day before the 2026-11-14 goal date; Summit announced it on 2026-11-15.

This records on the row what link_crl_letters.py records for any matched letter (same fields, same wording), so the
first rebuild step already sees it, and corrects the page sentence that said no letter date was known. The workflow
now also re-runs the Verified line and the announcement-only labelling after link_crl_letters.py, so the next letter
the FDA releases does not block a run. Facts only; not investment advice. Idempotent.
"""
import datetime as dt, io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
URL = "https://download.open.fda.gov/crl/CRL_BLA761524_20261113.pdf"
WANT = {"fda_action_date": "2026-11-13",
        "decision_source": "FDA Complete Response Letter, BLA 761524, dated November 13, 2026 (openFDA transparency/crl)",
        "decision_source_url": URL,
        "decision_date_note": "2026-11-15 is the company's announcement date; the FDA's letter is dated 2026-11-13."}
OLD_NOTE = ("The release does not state the letter's own date; the date shown is Summit's announcement, so no early or "
            "late margin is stated.")
NEW_NOTE = ("The FDA's letter (BLA 761524) is dated November 13, 2026, one day before the November 14 goal date; "
            "Summit announced it on November 15.")

s = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
r = next(x for x in rows if x["id"] == "pdufa_smmt_2026-11-14")
d = r["_d"]
ch = False
if any(d.get(k) != v for k, v in WANT.items()):
    d.update(WANT); ch = True
if OLD_NOTE in (d.get("decision_note") or ""):
    d["decision_note"] = d["decision_note"].replace(OLD_NOTE, NEW_NOTE); ch = True
if d.pop("decision_date_unsourced", None) is not None:
    ch = True
if ch:
    r["ua"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
    print("  pdufa_smmt_2026-11-14: FDA action date 2026-11-13 from the FDA's letter (BLA 761524)")
else:
    print("  pdufa_smmt_2026-11-14: already carries the FDA letter")

# the page's own sentence said the letter date was unknown
PG = os.path.join(SITE, "fda-decision", "SMMT-2026-11-15", "index.html")
OLD = "Summit's release does not state the letter's own date, so no margin is stated."
NEW = ("The FDA's Complete Response Letter is dated November 13, 2026, one day before the goal date; Summit announced "
       "it on November 15.")
doc = io.open(PG, encoding="utf-8", errors="replace").read()
for old, new in ((OLD, NEW), (OLD.replace("'", "&#x27;"), NEW), (OLD.replace("'", "&#39;"), NEW)):
    if old in doc:
        doc = doc.replace(old, new)
        io.open(PG, "w", encoding="utf-8", newline="").write(doc)
        print("  /fda-decision/SMMT-2026-11-15: goal-date note now states the letter date")
        break
