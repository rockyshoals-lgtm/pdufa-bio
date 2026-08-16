# -*- coding: utf-8 -*-
"""test_conference_presenters.py -- no presenter publishes unless its own sentence names its
edition.

Red team 2026-08-12c: of 102 mined presenter rows, fewer than 10% were about an upcoming
conference. The killer bug was EDITION MISMATCH -- the miner matched by conference NAME and
attached the next future occurrence, so 'ASCO GI data presented January 8, 2026' was filed
under ASCO GI 2027: a row that looks perfectly forward and is wrong by a year. Their fix spec
ends with: 'no presenter row publishes unless its conf_start year matches a year cited in its
own matched sentence.' This is that guard.

Checks the PUBLISHABLE selection (verified file + high-confidence mined rows, the same gate
build_conferences.py applies): every row's matched sentence must contain the edition year, or
an in-window month with no conflicting year. The curated history file is editorial and exempt
here (its own dating rule is the render window); the mined pipeline is the machine that
produced 93 wrong rows, so the machine's output is what gets machine-checked.
"""
import csv, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CO = os.path.join(HERE, "catalysts_out")
MONTHS = ("january february march april may june july august september october november "
          "december").split()


def edition_in_sentence(sentence, conf_start):
    year = str(conf_start)[:4]
    years = set(re.findall(r"\b(20\d{2})\b", sentence))
    if years - {year}:
        return False
    if year in years:
        return True
    try:
        m = int(str(conf_start)[5:7])
        return bool(re.search(rf"\b{MONTHS[m - 1]}\b", sentence, re.I))
    except Exception:
        return False


def main():
    bad, checked = [], 0
    files = [(os.path.join(CO, "conference_presenters_VERIFIED_2026-08-12.csv"), False),
             (os.path.join(CO, "conference_presenters_mined.csv"), True)]
    for path, gated in files:
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8-sig", errors="replace")):
            if gated and (r.get("confidence") or "").strip().lower() != "high":
                continue                      # unpublishable rows are evidence, not claims
            s = r.get("matched_sentence") or ""
            cs = r.get("conf_start") or ""
            if not s or not cs:
                continue
            checked += 1
            if not edition_in_sentence(s, cs):
                # a HUMAN-reviewed row (named reviewer in the verified file) may pass on the
                # reviewer's judgement -- ZLAB's evidence is a milestones table naming ESMO
                # amid multi-year guidance, verified by the red team by reading the filing.
                # The machine check is for the machine's rows; a human override is visible,
                # attributed, and warned about, not silently equal.
                if not gated and (r.get("reviewer") or "").strip():
                    print(f"  [warn] {r.get('ticker', '?')} -> {r.get('conference', '?')} "
                          f"{cs[:4]}: edition not in sentence; passing on reviewer "
                          f"'{r.get('reviewer', '')[:30]}'")
                    continue
                bad.append(f"{r.get('ticker', '?')} -> {r.get('conference', '?')} "
                           f"{cs[:4]}: sentence names no year/month for this edition: "
                           f"'{s[:80]}...'")

    if bad:
        print(f"FAIL: {len(bad)} publishable presenter row(s) whose own sentence does not "
              f"name the edition.")
        for b in bad[:8]:
            print(f"   {b}")
        print("\n   This is Bug B (edition mismatch) trying to ship again. Fix the row or")
        print("   demote its confidence; the page must never claim an edition the filing")
        print("   does not.")
        return 1
    print(f"  PASS: {checked} publishable presenter row(s) all name their own edition in "
          f"their own sentence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
