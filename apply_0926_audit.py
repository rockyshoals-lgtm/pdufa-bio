# -*- coding: utf-8 -*-
"""apply_0926_audit.py -- audit 2026-09-26 ORDER items 1 and 2 (verified before writing).

1. ATEBRIOZ (zilurgisertib), MIRM + INCY rows, goal Saturday 2026-09-26: APPROVED.
   FDA, CDER "News & Events for Human Drugs", published Fri 09/25/2026 14:46 (Eastern):
     https://www.fda.gov/drugs/news-events-human-drugs/fda-approves-third-treatment-fibrodysplasia-ossificans-progressiva
     "The U.S. Food and Drug Administration (FDA) has approved Atebrioz (zilurgisertib) tablets to
      reduce the volume of total new heterotopic ossification ... in adults and pediatric patients
      12 years and older with fibrodysplasia ossificans progressiva (FOP)."
   Mirum/Incyte release, Business Wire 20260925436454, Sep. 25, 2026, 7:00 PM EDT: same approval,
   plus a Rare Pediatric Disease Priority Review Voucher issued to Incyte; 100 mg once daily;
   licensed by Incyte to Mirum; EU MAA under review.
   ACTION DAY: neither document states it; Drugs@FDA (last updated 2026-09-24) has no record yet.
   The FDA's own notice proves approval by Sep 25, before the Sep 26 goal, but a margin needs the
   day, so decision_date_unsourced until sync_fda_action_dates.py finds the letter (it re-checks
   excluded rows every run and re-admits them automatically).
   NOTE the audit said "every source the watcher reads is silent; only the newswire has it". The
   FDA had it first: its CDER notice went up at 2:46 PM ET, four hours before the 7 PM newswire.
   That page is not on the FDA press-announcements feed the watcher reads -- see section 3 of the
   builder note.

2. PHARMING lower-dose Joenja sNDA, PDUFA 2027-01-30 (Priority Review). 6-K 0001828316-26-000041,
   EX-99.1 dated 2026-09-25: "PDUFA target action date of January 30, 2027"; children aged 4 and
   older with APDS weighing 13 kg or more (the approved label covers 27 kg and above).
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DATA = os.path.join(SITE, "api", "data.js")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

FDA_NOTE = ("https://www.fda.gov/drugs/news-events-human-drugs/"
            "fda-approves-third-treatment-fibrodysplasia-ossificans-progressiva")
BW = ("https://www.businesswire.com/news/home/20260925436454/en/Mirum-Pharmaceuticals-and-Incyte-Announce-U.S."
      "-FDA-Approval-of-Atebrioz-zilurgisertib-for-Adult-and-Pediatric-Patients-with-Fibrodysplasia-Ossificans-Progressiva")
PHAR_6K = "https://www.sec.gov/Archives/edgar/data/1828316/000182831626000041/pharmingannouncesusfdaacce.htm"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] in ("pdufa_mirm_2026-09-26", "pdufa_incy_2026-09-26"):
        if r["st"] == "Decided":
            print(f"  {r['id']}: already Decided"); continue
        assert r["st"] == "Upcoming" and r["d"] == "2026-09-26", r
        r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-25"
        r["name"] = ("Atebrioz (zilurgisertib)" if r["t"] == "MIRM"
                     else "Atebrioz (zilurgisertib), licensed to Mirum")
        r["ua"] = NOW
        d = r.setdefault("_d", {})
        d.update({
            "brand": "Atebrioz",
            "indication": "Fibrodysplasia ossificans progressiva (FOP), adults and pediatric patients 12 years and older: reduces the volume of total new heterotopic ossification",
            "decision_source": "FDA notice 2026-09-25 (CDER News & Events for Human Drugs, published 2:46 PM ET)",
            "decision_source_url": FDA_NOTE,
            "announcement_url": BW,
            "decision_quote": ("The U.S. Food and Drug Administration (FDA) has approved Atebrioz (zilurgisertib) "
                               "tablets to reduce the volume of total new heterotopic ossification ... in adults and "
                               "pediatric patients 12 years and older with fibrodysplasia ossificans progressiva (FOP)."),
            "decision_date_unsourced": True,
            "decision_date_note": ("The FDA's notice was published September 25, 2026 and says the FDA \"has approved\" "
                                   "Atebrioz, so the approval came no later than September 25, before the Saturday "
                                   "September 26 goal date. Neither it nor the Mirum/Incyte release states the action "
                                   "day and Drugs@FDA has no record yet, so no margin is published until the approval "
                                   "letter posts."),
            "review": ("NDA approved with Fast Track, Priority Review and Orphan Drug designations (FDA notice). "
                       "100 mg orally once daily. The FDA issued a Rare Pediatric Disease Priority Review Voucher "
                       "to Incyte. Incyte developed zilurgisertib and licensed it to Mirum for worldwide "
                       "development and commercialization; an EU marketing authorization application is under "
                       "review. Efficacy: PROGRESS Cohort 1, 63 patients, mean total new HO volume -3.2 cm3 on "
                       "Atebrioz vs +24.6 cm3 on placebo at week 24."),
        })
        n += 1
        print(f"  {r['id']}: Upcoming -> Decided/Approved 2026-09-25 (FDA notice; action day pending)")

have_phar = any(r.get("t") == "PHAR" and r.get("type") == "PDUFA" and r.get("d") == "2027-01-30" for r in rows)
if have_phar:
    print("  PHAR 2027-01-30 already present")
else:
    rows.append({
        "id": "pdufa_phar_2027-01-30", "t": "PHAR", "company": "Pharming Group N.V.",
        "d": "2027-01-30", "dp": "day",
        "name": "Joenja (leniolisib) lower doses - APDS, ages 4+ from 13 kg (sNDA)",
        "type": "PDUFA", "ta": "Immunology", "cap": "Small", "st": "Upcoming", "oc": None, "dcd": None,
        "url": "/pdufa/PHAR-joenja", "ua": NOW,
        "_d": {"nct_id": None,
               "indication": "Activated PI3K-delta syndrome (APDS), children aged 4 years and older weighing 13 kg or more (lower-dose formulation)",
               "source": "Pharming 6-K 2026-09-25 (EX-99.1)", "source_url": PHAR_6K,
               "source_quote": "PDUFA target action date of January 30, 2027",
               "review": ("Supplemental NDA for lower doses of Joenja, accepted with Priority Review (6-K of "
                          "September 25, 2026). Follows the September 11, 2026 approval for children aged 4 to 11 "
                          "weighing at least 27 kg."),
               "prior_decision": "/fda-decision/PHAR-2026-09-11"}})
    rows.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    print("  + pdufa_phar_2027-01-30 (Joenja lower-dose sNDA, Priority Review, 6-K 2026-09-25)")

io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

# forward slate for the homepage board / calendar
s = io.open(DATA, encoding="utf-8").read()
k = s.find("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s[k + len("const SLATE="):])
if not any(c.get("ticker") == "PHAR" and str(c.get("date"))[:10] == "2027-01-30" for c in slate.get("catalysts", [])):
    slate["catalysts"].append({"ticker": "PHAR", "name": "Pharming Group N.V.", "date": "2027-01-30",
                               "t_minus": (dt.date(2027, 1, 30) - dt.date.today()).days,
                               "drug": "Joenja (leniolisib) lower doses (sNDA)",
                               "indication": "APDS, ages 4+ from 13 kg", "price": None, "mcap": None,
                               "cap": "Small", "adv": None, "cash_months": None})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATA, "w", encoding="utf-8").write(s[:k + len("const SLATE=")] + json.dumps(slate, separators=(",", ":"))
                                               + s[k + len("const SLATE=") + end:])
    print("  data.js: + PHAR 2027-01-30")
print(f"{n} decision row(s) updated")
