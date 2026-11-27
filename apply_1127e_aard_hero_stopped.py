# -*- coding: utf-8 -*-
"""apply_1127e_aard_hero_stopped.py -- serve Aardvark's ARD-101 HERO readout as stopped by the company.

WHY (2026-11-27). The row readout_aard_2026-09-30 (company guidance, Feb 12, 2026: "topline Phase 3 data expected in
the third quarter of 2026") was served "Window passed, no topline announced". Aardvark's own release of Oct 23,
2026 (GlobeNewswire, read 2026-11-27) says "The HERO trial randomized 67 of the planned 90 participants and was
terminated early", and reports only exploratory data ("all efficacy data are considered exploratory"). The Q3 release
of Nov 13, 2026 repeats it. The Nov 26 readout mine had found this (red team CONFIRMED), but
apply_1126_readout_mine.py wrote a passed "stopped" record as no_topline; that is fixed there and guarded by
tests/test_readout_mine_stopped_applied.py.

No outcome is inferred: the company itself says the data are exploratory and inconclusive. Idempotent.
Facts only; not investment advice.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
RID = "readout_aard_2026-09-30"
URL = ("https://www.globenewswire.com/news-release/2026/10/23/3387158/0/en/"
       "aardvark-therapeutics-reports-exploratory-data-from-the-terminated-hero-and-open-label-extension-trials.html")
RES = {"state": "company_stopped", "date": "2026-10-23", "url": URL,
       "quote": "The HERO trial randomized 67 of the planned 90 participants and was terminated early.",
       "note": "Exploratory data only, per the company: “all efficacy data are considered exploratory.”",
       "checked": "2026-11-27", "reviewed": "2026-11-27"}


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    hit = [r for r in rows if r.get("id") == RID]
    if not hit:
        print("row not found; nothing to do")
        return
    dd = hit[0].setdefault("_d", {})
    if dd.get("resolution") != RES:
        dd["resolution"] = RES
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
        print(f"{RID}: resolution -> company_stopped 2026-10-23")
    ack = json.load(io.open(ACK, encoding="utf-8"))
    for a in ack.get("acks", []):
        if a.get("id") == RID and "terminated early" not in a.get("reason", ""):
            a["reason"] = ("2026-11-27: Aardvark's Oct 23, 2026 release says the HERO trial was terminated early; "
                           "served 'Stopped per company 2026-10-23' (resolution reviewed by hand).")
            io.open(ACK, "w", encoding="utf-8").write(json.dumps(ack, indent=1, ensure_ascii=False) + "\n")
            print("ack updated")


if __name__ == "__main__":
    main()
