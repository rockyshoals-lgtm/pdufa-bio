# -*- coding: utf-8 -*-
"""CI guard: the drug-page watcher hears a sponsor's own approval headline (audit 2026-10-10 item 1).

Novartis announced the Rhapsido symptomatic-dermographism approval on 2026-10-07; the lead reached the site
2.5 days later because only openFDA (lagging) could hear it: the FDA issued no notice, and the sponsor-feed
watcher arms only rows with a pending PDUFA date, which this supplement never had. The drug-page watcher
now reads every feed in _sponsor_feeds.json for ANY sponsor. This plants Novartis's real headline against a
universe holding remibrutinib (unresolved) and requires a lead whose source is the sponsor newsroom, and
requires NVS to carry a feed entry.

    python tests/test_drug_watch_hears_sponsor_newsrooms.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import watch_drug_approvals as D  # noqa: E402

HEADLINE = ("Novartis Rhapsido® (remibrutinib) receives FDA approval as first treatment for symptomatic "
            "dermographism (SD), expanding its use beyond chronic spontaneous urticaria (CSU)")
DECOY = "Novartis advances multiple sclerosis innovation with late-breaking remibrutinib data at MSToronto2026"


def main():
    fails = []
    universe = {"remibrutinib": ["remibrutinib", "rhapsido"]}
    leads, seen = [], set()
    D.scan_text_for_drugs(HEADLINE, universe, set(), "sponsor:NVS:2026-10-08", leads, seen)
    if not leads or leads[0][0] != "remibrutinib" or not leads[0][1].startswith("sponsor:NVS"):
        fails.append(f"planted Novartis approval headline produced {leads!r}; expected a remibrutinib lead from sponsor:NVS")
    leads2, seen2 = [], set()
    D.scan_text_for_drugs(DECOY, universe, set(), "sponsor:NVS:2026-10-08", leads2, seen2)
    if leads2:
        fails.append(f"decoy (readout headline, no approval language) produced {leads2!r}")
    feeds = json.load(io.open(os.path.join(HERE, "_sponsor_feeds.json"), encoding="utf-8"))
    if not (feeds.get("NVS") or {}).get("feeds"):
        fails.append("_sponsor_feeds.json has no feed for NVS")
    src = io.open(os.path.join(HERE, "watch_drug_approvals.py"), encoding="utf-8").read()
    if "sponsor newsrooms read" not in src:
        fails.append("watch_drug_approvals.py has no sponsor-newsroom pass")
    if fails:
        print("FAIL: the drug-page watcher does not hear sponsor newsrooms:")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- planted Novartis approval headline yields a remibrutinib lead from the sponsor newsroom; decoy ignored; NVS feed present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
