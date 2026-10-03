# -*- coding: utf-8 -*-
"""CI guard: replay the 09-28 -> 10-03 blockade through quarantine_leads.step (audit 2026-10-03, Tier 1.2).

What happened: from 2026-09-28 17:56 UTC the watchers raised a lead on every run; 17 issues were
opened (#2-#18), no one was told, and nothing deployed for six days. Replaying the same runs through
the escalation logic must give: held_since = the first held run (non-null), ONE email (after the
second consecutive held run), one issue per distinct lead rather than one per run, and a clean run
resets the streak. Times are UTC (RULE 1).

    python tests/test_escalation_replay.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import quarantine_leads as Q  # noqa: E402

ABBV = {"source": "sponsor_feed", "row_id": "pdufa_abbv_2026-12-31",
        "key": "pdufa_abbv_2026-12-31|https://news.abbvie.com/2026-09-28-U-S-FDA-Approves-AbbVies-JUVMO-TM-tavapadon-for-Parkinsons-Disease",
        "text": "U.S. FDA Approves AbbVie's JUVMO (tavapadon) for Parkinson's Disease"}
ENSP = {"source": "fda_drugs_feed", "row_id": "pdufa_rhhby_2026-10-15",
        "key": "pdufa_rhhby_2026-10-15|http://www.fda.gov/news-events/press-announcements/fda-approves-first-treatment-mct8-deficiency",
        "text": "FDA Approves First Treatment for MCT8 Deficiency [thyroid]"}
AGIO = {"source": "drugs_at_fda", "row_id": "pdufa_agio_2026-11-01", "key": "AGIO|2026-09-28", "text": "SUPPL-7 MANUF (CMC)"}
GIRE = {"source": "drugs_at_fda", "row_id": "pdufa_rhhby_2026-12-18", "key": "RHHBY|2026-09-21", "text": "ANDA 220597 everolimus"}

# the runs that opened issues #2-#18 (createdAt, UTC) and the leads each carried
RUNS = [("2026-09-28T17:56:34Z", [ABBV]), ("2026-09-28T19:21:28Z", [ABBV]),
        ("2026-09-29T00:46:36Z", [ABBV, ENSP]), ("2026-09-29T16:20:22Z", [ABBV, ENSP]),
        ("2026-09-29T17:47:18Z", [ABBV, ENSP])] + \
       [(t, [ABBV, ENSP, AGIO, GIRE]) for t in (
           "2026-09-30T00:01:58Z", "2026-09-30T16:13:41Z", "2026-09-30T17:42:57Z", "2026-10-01T00:18:28Z",
           "2026-10-01T16:50:55Z", "2026-10-01T18:09:00Z", "2026-10-02T00:23:11Z", "2026-10-02T16:04:29Z",
           "2026-10-02T17:34:44Z", "2026-10-03T00:05:59Z", "2026-10-03T14:30:48Z", "2026-10-03T15:50:54Z")]


def main():
    fails = []
    st = Q.load_state("__no_such_file__")
    emails, issues, held_since_seen = [], [], set()
    for now, leads in RUNS:
        st, acts = Q.step(st, leads, now)
        emails += [now for a in acts if a == "email"]
        issues += [a for a in acts if a.startswith("issue:")]
        held_since_seen.add(st["held_since"])
    if len(RUNS) != 17:
        fails.append(f"replay has {len(RUNS)} runs, expected 17 (issues #2-#18)")
    if emails != ["2026-09-28T19:21:28Z"]:
        fails.append(f"expected exactly one email at the 2nd held run (2026-09-28T19:21:28Z), got {emails}")
    if held_since_seen != {"2026-09-28T17:56:34Z"}:
        fails.append(f"held_since should stay 2026-09-28T17:56:34Z through the streak, saw {held_since_seen}")
    if len(issues) != 4:
        fails.append(f"expected 4 issues (one per distinct lead), got {len(issues)}")
    first = {l["key"]: l["first_seen"] for l in st["leads"]}
    if first.get(ABBV["key"]) != "2026-09-28T17:56:34Z" or first.get(AGIO["key"]) != "2026-09-30T00:01:58Z":
        fails.append(f"first_seen not carried across runs: {first}")
    # a clean run clears the hold; a new streak may email again
    st, acts = Q.step(st, [], "2026-10-03T23:00:00Z")
    if st["held_since"] is not None or st["consecutive_held_runs"] != 0 or acts:
        fails.append(f"a clean run must reset the streak: {st['held_since']}, {st['consecutive_held_runs']}, {acts}")
    if fails:
        print(f"FAIL: {len(fails)} escalation replay failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- 09-28 replay: held_since 2026-09-28T17:56:34Z, 1 email (2nd run), 4 issues not 17, clean run resets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
