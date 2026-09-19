# -*- coding: utf-8 -*-
"""RARE UX111 -> FAYUVI, approved 2026-09-17, two days before the sourced goal date of 09-19.

Read first-hand before writing:
  FDA press release 2026-09-17 14:31 ET: "The U.S. Food and Drug Administration today approved
  Fayuvi (rebisufligene etisparvovec-hopf), the first treatment for pediatric patients with
  mucopolysaccharidosis type IIIA (MPS IIIA), also known as Sanfilippo syndrome type A."
  Ultragenyx 8-K 2026-09-17, Item 8.01 (acc 0001515673-26-000006): "the FDA granted standard full
  approval of FAYUVI (rebisufligene etisparvovec-hopf), also known as UX111 ... The Company
  received a Priority Review Voucher upon this approval."

The goal date stays as sourced on 09-15 (Ultragenyx 8-K 2026-04-02: "PDUFA action date of
September 19, 2026"), so this decision enters the timing statistic as 2 days early.

WHY THE WATCHER MISSED IT (recorded for the fix): the FDA announced under a brand name, Fayuvi,
that no row carried; our row said "UX111 - (ABO-102)". The early-approval matcher keys on the
names we hold, and a brand assigned at approval is by definition a name we do not hold.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
FDA = "https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapy-pediatric-patients-sanfilippo-syndrome-type"
K8 = "https://www.sec.gov/Archives/edgar/data/1515673/000151567326000006/rare-20260917.htm"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_rare_2026-09-19":
        continue
    assert r["d"] == "2026-09-19" and r["dp"] == "day" and r["st"] == "Upcoming", r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-17"
    r["name"] = "FAYUVI (rebisufligene etisparvovec-hopf; UX111 / ABO-102)"
    r["ua"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dd = r.setdefault("_d", {})
    dd["brand"] = "FAYUVI"
    dd["decision_source"] = "Ultragenyx 8-K 2026-09-17 (Item 8.01); FDA press release 2026-09-17"
    dd["decision_source_url"] = K8
    dd["decision_source_url_2"] = FDA
    dd["decision_quote"] = ("On September 17, 2026, Ultragenyx Pharmaceutical Inc. announced that the U.S. Food "
                            "and Drug Administration granted standard full approval of FAYUVI (rebisufligene "
                            "etisparvovec-hopf), also known as UX111, for the treatment of pediatric patients "
                            "with mucopolysaccharidosis type IIIA (MPS IIIA, Sanfilippo syndrome Type A).")
    dd["review"] = ("Standard full approval on September 17, 2026, two days before the September 19 PDUFA "
                    "goal date; the first FDA-approved treatment for Sanfilippo syndrome type A and "
                    "Ultragenyx's second gene therapy approval. A Priority Review Voucher was awarded. "
                    "UX111 (ABO-102) was licensed from Abeona Therapeutics (ABEO).")
    n += 1
    print(f"  {r['id']}: Upcoming -> Decided/Approved 2026-09-17 (goal 2026-09-19 sourced, 2 days early)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
