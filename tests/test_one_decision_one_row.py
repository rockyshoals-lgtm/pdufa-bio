# -*- coding: utf-8 -*-
"""CI guard: one FDA decision resolves one PDUFA row per ticker.

2026-09-26: Pharming's new lower-dose Joenja sNDA (goal 2027-01-30, accepted 2026-09-25) was marked
"Approved 2026-09-11" by sync_api_from_pages within minutes of being added -- the September 11
approval of the 2026-10-24 application, carried forward because both rows say "Joenja". The
calendar marker did the same, and the slate sweep then removed the new event from the forward
calendar. A decision now belongs to the same-ticker row whose goal is closest to it.

Fails when two PDUFA rows of the same ticker carry the same decision date and outcome and share a
drug token (two different drugs decided the same day stay legal), and when a Decided row's
decision predates the filing its goal date is sourced to by more than a review cycle would allow
(a decision before the application was even accepted cannot resolve it).

    python tests/test_one_decision_one_row.py
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = {"with", "and", "for", "the", "plus", "sNDA", "snda", "label", "update", "doses", "lower"}


def toks(s):
    return {w for w in re.findall(r"[a-z]{5,}", str(s or "").lower()) if w not in STOP}


def main():
    src = io.open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    groups = collections.defaultdict(list)
    for r in rows:
        if r.get("type") == "PDUFA" and str(r.get("st", "")).lower() == "decided" and r.get("dcd"):
            groups[(str(r["t"]).upper(), str(r["dcd"]), r.get("oc"))].append(r)
    fails = []
    for (tk, dcd, oc), rs in groups.items():
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                if toks(rs[i].get("name")) & toks(rs[j].get("name")):
                    fails.append(f"{tk} {oc} {dcd} resolves two rows: {rs[i]['id']} and {rs[j]['id']}")
    # a decision cannot resolve an application whose source filing (acceptance) is dated after it
    for r in rows:
        d = r.get("_d") or {}
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided" or not r.get("dcd"):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(d.get("source") or ""))
        if m and str(r["dcd"]) < m.group(1) and "accept" in str(d.get("review") or d.get("source_quote") or "").lower():
            fails.append(f"{r['id']}: decided {r['dcd']} but its goal date's source filing is dated {m.group(1)}")
    if fails:
        print(f"FAIL: {len(fails)} decision(s) assigned to more than one application:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- every decision resolves exactly one PDUFA row per ticker ({sum(len(v) for v in groups.values())} decided rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
