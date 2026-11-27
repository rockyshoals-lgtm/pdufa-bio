# -*- coding: utf-8 -*-
"""apply_1127g_kpti_ec042_topline.py -- Karyopharm's XPORT-EC-042 (selinexor maintenance, endometrial cancer,
NCT05611931) read out on Jul 30, 2026; the site said "no topline".

Karyopharm's Jul 30, 2026 release "Karyopharm Announces Topline Results from Phase 3 XPORT-EC-042 Trial in
Endometrial Cancer" states the trial did not meet its primary endpoint of progression-free survival. The resolver
missed it (FMP returned only the last few months of releases, and the headline does not name selinexor); both causes
are fixed in resolve_past_readouts.py with tests/test_resolver_finds_trial_headlines.py. This marks the row by hand
(reviewed) so it is right before the next rebuild re-resolves. Idempotent. Facts only; not investment advice.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
RID = "readout_kpti_2026-08-15"
RES = {
    "state": "sponsor_release",
    "date": "2026-07-30",
    "headline": "Karyopharm Announces Topline Results from Phase 3 XPORT-EC-042 Trial in Endometrial Cancer",
    "url": "https://www.prnewswire.com/news-releases/karyopharm-announces-topline-results-from-phase-3-xport-ec-042-trial-in-endometrial-cancer-302839314.html",
    "quote": "The Trial Did Not Meet the Primary Endpoint of Progression-Free Survival (PFS)",
    "checked": "2026-11-27",
    "reviewed": "2026-11-27",
    "basis": "sponsor's own topline release for this trial (XPORT-EC-042 = NCT05611931), read by hand",
}


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    n = 0
    for r in rows:
        if r.get("id") == RID and (r.get("_d") or {}).get("resolution") != RES:
            nct = ((r["_d"].get("nct_id") or {}) if isinstance(r["_d"].get("nct_id"), dict) else {}).get("nct")
            assert nct == "NCT05611931", nct
            r["_d"]["resolution"] = dict(RES)
            n += 1
    if n:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    print(f"{RID}: {'updated' if n else 'already current'}")


if __name__ == "__main__":
    main()
