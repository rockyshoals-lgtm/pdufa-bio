# -*- coding: utf-8 -*-
"""apply_1127_irla_ticker.py -- one company, two hubs: Quince Therapeutics became IRulya Therapeutics (Nasdaq: IRLA).

THE PROBLEM (found 2026-11-27 ET in the Q1 2027 readout recheck). Quince Therapeutics relaunched as IRulya Therapeutics,
its stock trading on Nasdaq as IRLA from Oct 12, 2026 (company release, Oct 9, 2026; restated in its Nov 13, 2026
release). Two of its three LAM-001 readouts sat on /ticker/IRLA, but the nearest one (Phase 2 in bronchiolitis
obliterans syndrome, data guided to Q1 2027) was still keyed QNCX under the old name. So /ticker/IRLA's FAQ called a
Q1 2028 readout the company's next catalyst, and /ticker/QNCX still named "Quince Therapeutics, Inc.".

THE FIX. The BOS row moves to IRLA with the company's current name (its id is kept so its row history follows it).
/ticker/QNCX and /company/quince redirect permanently to /ticker/IRLA (the sitemap leaves redirected paths out).
A /corrections entry records it. Neither hub was indexed by Google (Discovered - currently not indexed), so the
consolidated page loses no ranking.

Idempotent. Facts only, not investment advice. RULE 1: dates are calendar dates as printed by the company (ET).

    python apply_1127_irla_ticker.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
VERCEL = os.path.join(HERE, "pdufa_site_src", "vercel.json")
CORR = os.path.join(HERE, "_corrections.json")
DAY = "2026-11-27"
RID = "readout_qncx_2027-03-31"
NEW_CO = "IRulya Therapeutics Inc. (formerly Quince Therapeutics, QNCX)"
SRC_URL = ("https://www.globenewswire.com/news-release/2026/10/09/3378039/0/en/quince-therapeutics-relaunches-as-irulya-"
           "therapeutics-with-a-focus-on-the-clinical-development-of-lam-001-targeting-a-key-pathway-in-pulmonary-disease.html")
REDIRS = [("/ticker/QNCX", "/ticker/IRLA"), ("/company/quince", "/ticker/IRLA")]
CORR_ENTRY = {
    "date": DAY, "page": "/ticker/IRLA",
    "was": "IRulya Therapeutics' Phase 2 LAM-001 readout in bronchiolitis obliterans syndrome (data guided to Q1 2027) "
           "was listed under its old name and ticker, Quince Therapeutics (QNCX), so the IRLA page gave a Q1 2028 "
           "readout as the company's next catalyst.",
    "now": "The readout is on the IRLA page, which now gives Q1 2027 as the next catalyst. /ticker/QNCX leads to it. "
           "IRulya's stock has traded on Nasdaq as IRLA since Oct 12, 2026.",
    "source": "Quince Therapeutics press release, Oct 9, 2026 (GlobeNewswire); IRulya press release, Nov 13, 2026",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    row = next((r for r in rows if r["id"] == RID), None)
    assert row, f"{RID} not in dataset"
    if row["t"] != "IRLA":
        assert row["t"] == "QNCX", row["t"]
        row["t"], row["company"] = "IRLA", NEW_CO
        dd = row.setdefault("_d", {})
        dd["ticker_history"] = [{"ticker": "QNCX", "until": "2026-10-11"},
                                {"ticker": "IRLA", "from": "2026-10-12", "changed": DAY, "source_url": SRC_URL,
                                 "why": "Quince Therapeutics relaunched as IRulya Therapeutics; its common stock "
                                        "trades on Nasdaq as IRLA effective Oct 12, 2026 (company release, Oct 9, 2026)."}]
        print(f"  {RID}: QNCX -> IRLA")
    left = [r["id"] for r in rows if r["t"] == "QNCX"]
    assert not left, left
    cfg = json.load(io.open(VERCEL, encoding="utf-8"))
    red = cfg.setdefault("redirects", [])
    for s, dst in REDIRS:
        hit = [r for r in red if r.get("source") == s]
        if hit:
            for r in hit:
                r["destination"], r["permanent"] = dst, True
        else:
            red.append({"source": s, "destination": dst, "permanent": True})
    corr = json.load(io.open(CORR, encoding="utf-8"))
    if not any(e.get("page") == CORR_ENTRY["page"] and e.get("was") == CORR_ENTRY["was"] for e in corr["entries"]):
        corr["entries"].append(CORR_ENTRY)
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    io.open(VERCEL, "w", encoding="utf-8").write(json.dumps(cfg, indent=1, ensure_ascii=False))
    io.open(CORR, "w", encoding="utf-8").write(json.dumps(corr, indent=1, ensure_ascii=False) + "\n")
    print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
