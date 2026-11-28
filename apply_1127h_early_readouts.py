# -*- coding: utf-8 -*-
"""apply_1127h_early_readouts.py -- two registry-estimate readouts the sponsor had already reported, red-teamed 2026-11-27.

THE PROBLEM. An Estimated row's window is the trial's ClinicalTrials.gov primary-completion date. The results finder
(resolve_past_readouts.py) only looks for a sponsor release once that window has PASSED. A sponsor that reports early
(a prespecified interim, or topline before the registry is updated) was therefore still listed as "upcoming" on
/readouts months after its release. A sweep of all 70 future-window Estimated rows against each sponsor's release
history (2025-01-01 to 2026-11-27) found two, each re-opened and checked against the registry record:

  readout_mnov_2026-12-15  MediciNova MN-001 (tipelukast), NCT05464784 (window Dec 2026)
      Release Sep 28, 2026 (GlobeNewswire): "MediciNova Announces Topline Results from MN-001-NATG-202 Clinical Trial
      of MN-001 (Tipelukast)". Same trial: the release's design (Phase 2, randomized, double-blind, placebo-controlled,
      40 patients with NAFLD and hypertriglyceridemia associated with T2DM, 24 weeks) is the registry record's, and it
      reports both registry co-primary measures at Week 24 (liver fat CAP score, serum triglycerides).
  readout_huma_2026-10-15  Humacyte ATEV (human acellular vessel) V012 Phase 3, NCT05908084 (window Jun 2027)
      Release Jun 10, 2026 (GlobeNewswire): "Humacyte ATEV Met Superiority Primary Endpoint Compared to Standard of
      Care AV Fistula in Interim Analysis of V012 Phase 3 Study in Female Dialysis Access Patients". Same trial: the
      registry record is the Phase 3 of the ATEV vs an autogenous AV fistula in female hemodialysis patients, primary
      measure catheter-free days to Month 12; the release reports that measure from a prespecified interim analysis.

Both become Reported on the day of the sponsor's release, exactly as apply_1126_readout_mine.py does for a reported
Guided row: review = the release headline verbatim, a readout_reported_manual.json entry (outcome "reported"; nothing
is inferred), a date_history entry, and a /corrections entry. Checked and NOT changed: Cardiff CRDF-004 (dose-selection
data at ASCO 2026; the registry primary measure, ORR by central review, has not been reported as topline) and ten
interim or different-trial releases listed in the working notes.

Idempotent. Facts only, not investment advice. RULE 1: dates are calendar dates as printed by the sponsor (ET).

    python apply_1127h_early_readouts.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MANUAL = os.path.join(HERE, "readout_reported_manual.json")
CORR = os.path.join(HERE, "_corrections.json")
DAY = "2026-11-27"
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

FIX = [
    {"id": "readout_mnov_2026-12-15", "nct": "NCT05464784", "program": "MN-001 (tipelukast)",
     "trial": "MN-001-NATG-202 (Phase 2)", "indication": "NAFLD with type 2 diabetes and hypertriglyceridemia",
     "date": "2026-09-28",
     "head": "MediciNova Announces Topline Results from MN-001-NATG-202 Clinical Trial of MN-001 (Tipelukast)",
     "url": "https://www.globenewswire.com/news-release/2026/09/28/3369686/7767/en/"
            "medicinova-announces-topline-results-from-mn-001-natg-202-clinical-trial-of-mn-001-tipelukast.html",
     "why": "the release's trial design (Phase 2, randomized, double-blind, placebo-controlled, 40 patients with NAFLD "
            "and hypertriglyceridemia associated with T2DM, 24 weeks) matches the registry record, and it reports both "
            "registry co-primary measures at Week 24",
     "page": "/ticker/MNOV", "src": "MediciNova press release, Sep 28, 2026 (GlobeNewswire)",
     "was": "MediciNova's MN-001 (tipelukast) Phase 2 trial in fatty liver disease with type 2 diabetes "
            "(NCT05464784) was listed as an upcoming readout, estimated December 2026.",
     "now": "Listed as reported on Sep 28, 2026, when MediciNova announced topline results from the trial "
            "(MN-001-NATG-202)."},
    {"id": "readout_huma_2026-10-15", "nct": "NCT05908084", "program": "ATEV (human acellular vessel)",
     "trial": "V012 (Phase 3)", "indication": "dialysis access in women with end-stage renal disease",
     "date": "2026-06-10",
     "head": "Humacyte ATEV Met Superiority Primary Endpoint Compared to Standard of Care AV Fistula in Interim "
             "Analysis of V012 Phase 3 Study in Female Dialysis Access Patients",
     "url": "https://www.globenewswire.com/news-release/2026/06/10/3310082/0/en/Humacyte-ATEV-Met-Superiority-"
            "Primary-Endpoint-Compared-to-Standard-of-Care-AV-Fistula-in-Interim-Analysis-of-V012-Phase-3-Study-in-"
            "Female-Dialysis-Access-Patients.html",
     "why": "the registry record is the Phase 3 of the ATEV vs an autogenous AV fistula in female hemodialysis "
            "patients with catheter-free days to Month 12 as its primary measure; the release reports that measure "
            "from a prespecified interim analysis",
     "page": "/ticker/HUMA", "src": "Humacyte press release, Jun 10, 2026 (GlobeNewswire)",
     "was": "Humacyte's V012 Phase 3 trial of the ATEV in female dialysis patients (NCT05908084) was listed as an "
            "upcoming readout, estimated June 2027 from the registry.",
     "now": "Listed as reported on Jun 10, 2026, when Humacyte announced that a prespecified interim analysis met "
            "the trial's primary endpoint."},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    by = {r["id"]: r for r in rows}
    man = json.load(io.open(MANUAL, encoding="utf-8"))
    have = {m["id"] for m in man["reported"]}
    corr = json.load(io.open(CORR, encoding="utf-8"))
    have_c = {(e.get("date"), e.get("page"), e.get("was")) for e in corr["entries"]}
    n = 0
    for f in FIX:
        row = by.get(f["id"])
        if not row:
            print(f"  {f['id']}: not in dataset, skipped")
            continue
        dd = row.setdefault("_d", {})
        blk = dd.get("nct_id") if isinstance(dd.get("nct_id"), dict) else {}
        assert str(blk.get("nct") or "").upper() == f["nct"], f"{f['id']}: NCT is {blk.get('nct')}, expected {f['nct']}"
        review = f"{row.get('company')} reported this readout on {f['date']}: “{f['head']}” (company press release)."
        if row.get("st") != "Reported" or row.get("d") != f["date"]:
            hist = dd.get("date_history") or [{"date": str(row["id"])[-10:], "note": "date the row was keyed on when created"}]
            hist.append({"date": f["date"], "changed": DAY,
                         "why": (f"The sponsor's release of {f['date']} reports this trial's results ({f['why']}). "
                                 f"A reported row carries the day it was reported. Was {row.get('d')} "
                                 f"({row.get('dp')}), the registry primary-completion estimate.")})
            dd["date_history"] = hist
            row.update({"st": "Reported", "d": f["date"], "dp": "day", "url": f["url"], "ua": NOW})
            row.pop("dm", None)
            n += 1
        dd.update({"review": review, "reported_source_url": f["url"], "program": dd.get("program") or f["program"],
                   "trial": dd.get("trial") or f["trial"], "indication": dd.get("indication") or f["indication"],
                   "source": "company release (sponsor reported results before the registry window)",
                   "early_readout_check": {"checked": DAY, "basis": f["why"]}})
        dd.pop("resolution", None)
        if f["id"] not in have:
            man["reported"].append({"id": f["id"], "t": row["t"], "drug": dd["program"], "reported_date": f["date"],
                                    "outcome": "reported", "summary": review, "source_url": f["url"],
                                    "guided_window": "",
                                    "note": f"early-readout sweep {DAY}: the sponsor reported before the registry "
                                            "primary-completion window; red-teamed against the release and the registry"})
        key = (DAY, f["page"], f["was"])
        if key not in have_c:
            corr["entries"].append({"date": DAY, "page": f["page"], "was": f["was"],
                                    "now": f["now"] + " Our results finder only looked for a sponsor release after "
                                                      "a registry window had passed; it now also flags results "
                                                      "releases for windows still ahead, for us to check.",
                                    "source": f["src"]})
        print(f"  {f['id']} -> Reported {f['date']}")
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    io.open(MANUAL, "w", encoding="utf-8").write(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    io.open(CORR, "w", encoding="utf-8").write(json.dumps(corr, indent=1, ensure_ascii=False) + "\n")
    print(f"{n} row(s) moved to Reported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
