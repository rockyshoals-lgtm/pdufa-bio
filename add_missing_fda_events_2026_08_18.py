# -*- coding: utf-8 -*-
"""add_missing_fda_events_2026_08_18.py -- three verified forward FDA decision events the
dataset lacked, surfaced by tests/test_calendar_two_sources.py on its first run.

The two-source guard (audit 2026-08-18 s3) reconciled the page's slate (data.js) against the
API's dataset (dataset.mjs) and found three forward events only the slate knew:

  GILD 2026-12-23  Anito-cel (anitocabtagene autoleucel), r/r multiple myeloma 4L.
                   VERIFIED: BLA accepted with PDUFA action date December 23, 2026, stated in
                   Gilead's own Arcellx-acquisition release (Feb 23, 2026).
  IRD  2026-10-17  VERIFIED with a CORRECTION: the slate labelled this OPGx-RDH12 (an
                   early-clinical gene therapy -- wrong). The real Oct 17 event is the sNDA for
                   phentolamine ophthalmic solution 0.75% in presbyopia, per Opus Genetics' FDA-
                   acceptance release. Slate text is fixed here too.
  NVCR 2026-11-15  TTFields (Optune) for brain metastases from NSCLC. VERIFIED as a PMA decision
                   the company guides to Q4 2026 (Q1-2026 8-K). NOT a PDUFA with a day: stored
                   at the quarter midpoint with dp='quarter' so the API claims no more precision
                   than the source (the slate's bare 2026-11-15 day was invented precision).

Idempotent, same pattern as add_repl_pdufa.py. Facts only; every row carries its source URL.
"""
import json, os, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATA = os.path.join(SITE, "api", "data.js")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

EVENTS = [
    {
        "t": "GILD", "company": "Gilead Sciences, Inc.", "d": "2026-12-23", "dp": "day",
        "dm": None, "drug": "Anito-cel (anitocabtagene autoleucel)",
        "ind": "Relapsed or refractory multiple myeloma (fourth-line), BCMA CAR-T",
        "ta": "Oncology",
        "src": ("https://www.gilead.com/news/news-details/2026/"
                "gilead-sciences-to-acquire-arcellx-to-maximize-long-term-potential-of-anito-cel"),
        "extra": {"review": "BLA accepted; pivotal Phase 2 iMMagine-1",
                  "note": "PDUFA action date stated by the sponsor"},
    },
    {
        "t": "IRD", "company": "Opus Genetics, Inc.", "d": "2026-10-17", "dp": "day",
        "dm": None, "drug": "Phentolamine ophthalmic solution 0.75%",
        "ind": "Presbyopia (sNDA)", "ta": "Ophthalmology",
        "src": ("https://www.biospace.com/press-releases/opus-genetics-announces-fda-acceptance-"
                "of-supplemental-new-drug-application-for-phentolamine-ophthalmic-solution-0-75-"
                "for-the-treatment-of-presbyopia"),
        "extra": {"review": "sNDA accepted; PDUFA goal date Oct 17, 2026",
                  "note": "slate previously mislabelled this event OPGx-RDH12; corrected"},
    },
    {
        "t": "NVCR", "company": "NovoCure Limited", "d": "2026-11-15", "dp": "quarter",
        "dm": "2026-11", "drug": "TTFields therapy (Optune) - brain metastases from NSCLC",
        "ind": "Brain metastases from non-small cell lung cancer (PMA, Breakthrough Device)",
        "ta": "Oncology",
        "src": ("https://www.sec.gov/Archives/edgar/data/0001645113/000164511326000043/"
                "nvcr-20260331xpr.htm"),
        "extra": {"review": "PMA under FDA review; company guides decision in Q4 2026",
                  "note": "device PMA, not a PDUFA goal date; date is the quarter midpoint, "
                          "shown at quarter precision"},
    },
]


def main():
    # ---- data.js slate: correct the IRD drug text; add any event the slate lacks ----------
    src = open(DATA, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i = src.find("const SLATE=")
    key = "const SLATE="
    if i < 0:
        i, key = src.find("SLATE="), "SLATE="
    slate, end = json.JSONDecoder().raw_decode(src[i + len(key):])
    changed = False
    today = dt.date.today()
    for ev in EVENTS:
        hit = [c for c in slate.get("catalysts", [])
               if c.get("ticker") == ev["t"] and str(c.get("date"))[:10] == ev["d"]]
        if hit:
            if str(hit[0].get("drug") or "") != ev["drug"]:
                print(f"data.js: {ev['t']} drug text corrected "
                      f"('{str(hit[0].get('drug'))[:30]}' -> '{ev['drug'][:30]}')")
                hit[0]["drug"] = ev["drug"]
                hit[0]["indication"] = ev["ind"]
                changed = True
        else:
            slate["catalysts"].append({
                "ticker": ev["t"], "name": ev["company"], "date": ev["d"],
                "t_minus": (dt.date.fromisoformat(ev["d"]) - today).days,
                "drug": ev["drug"], "indication": ev["ind"],
                "price": None, "mcap": None, "cap": "", "adv": None, "cash_months": None,
            })
            print(f"data.js: added {ev['t']} {ev['d']}")
            changed = True
    if changed:
        slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
        open(DATA, "w", encoding="utf-8").write(
            src[:i + len(key)] + json.dumps(slate, separators=(",", ":"), ensure_ascii=False)
            + src[i + len(key) + end:])
    else:
        print("data.js: nothing to change")

    # ---- dataset.mjs: add missing events -------------------------------------------------
    ds = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = ds.find("[")
    arr, dend = json.JSONDecoder().raw_decode(ds[j:])
    added = 0
    # Dual-listing repair: VTRS 2026-10-17 'MR-141' IS the phentolamine presbyopia sNDA --
    # Viatris co-develops phentolamine ophthalmic with Opus Genetics (IRD). The bare code name
    # shares no token with the partner row, so event clustering saw two events where there is
    # one. Name the drug on the row.
    for r in arr:
        if (r.get("t") == "VTRS" and str(r.get("d"))[:10] == "2026-10-17"
                and str(r.get("name")) == "MR-141"):
            r["name"] = "MR-141 (phentolamine ophthalmic solution 0.75%)"
            added += 1
            print("dataset.mjs: VTRS 2026-10-17 named -- MR-141 is phentolamine (Opus/IRD "
                  "partner event)")
    for ev in EVENTS:
        if any(r.get("t") == ev["t"] and r.get("type") == "PDUFA"
               and str(r.get("d"))[:10] == ev["d"] for r in arr):
            print(f"dataset.mjs: {ev['t']} {ev['d']} already present")
            continue
        row = {
            "id": f"pdufa_{ev['t'].lower()}_{ev['d']}", "t": ev["t"], "company": ev["company"],
            "d": ev["d"], "dp": ev["dp"], "name": ev["drug"], "type": "PDUFA", "ta": ev["ta"],
            "cap": "", "st": "Upcoming", "url": ev["src"], "ua": NOW,
            "_d": dict(ev["extra"], indication=ev["ind"], market_cap_usd=None),
        }
        if ev["dm"]:
            row["dm"] = ev["dm"]
        arr.append(row)
        added += 1
        print(f"dataset.mjs: added {ev['t']} {ev['d']} (dp={ev['dp']})")
    if added:
        arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
        open(DATASET, "w", encoding="utf-8").write(
            ds[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + ds[j + dend:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
