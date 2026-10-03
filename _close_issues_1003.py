# -*- coding: utf-8 -*-
"""Close the 17 blocking issues of 09-28..10-03 with a one-line reason each (audit 10-03, Tier 0)."""
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
GREEN = "run 37148030700 (2026-10-03, green)"
R_ABBV = ("REAL: JUVMO (tavapadon) approved by the FDA 2026-09-25 (NDA 220415 letter), AbbVie announced 09-28; "
          f"published as /fda-decision/ABBV-2026-09-28 in 4da0c4fa1. Rebuild green again: {GREEN}.")
R_ENSP = ("FALSE: the FDA's MCT8-deficiency notice is Emcitate (tiratricol, Egetis); it matched Enspryng only on the word "
          "'thyroid'. Acked in _fda_drugs_feed_ack.json; matcher rule 1.3(d) now forbids lone organ-word matches "
          f"(tests/test_matcher_rules_replay.py). {GREEN}.")
R_AGIO = "AGIO SUPPL-7 is class MANUF (CMC), not the RISE UP efficacy decision (acked; rule 1.3(b))"
R_GIRE = "RHHBY 'everolimus' hit is ANDA 220597, Novitium's generic, not Roche's giredestrant NDA (acked; rules 1.3(a)+(c))"

for n in range(2, 19):
    body = json.loads(subprocess.run(["gh", "issue", "view", str(n), "--json", "body,state"],
                                     capture_output=True, text=True).stdout or "{}")
    if body.get("state") != "OPEN":
        print(f"#{n}: already {body.get('state')}")
        continue
    b = body.get("body", "")
    if "Tavapadon" in b or "JUVMO" in b:
        reason = R_ABBV
    elif "thyroid" in b or "MCT8" in b:
        reason = R_ENSP
    else:
        parts = []
        if "AGIO" in b:
            parts.append(R_AGIO)
        if "everolimus" in b:
            parts.append(R_GIRE)
        if not parts:
            print(f"#{n}: unrecognised body, left open")
            continue
        reason = "FALSE: " + "; ".join(parts) + f". Watchers now hold a lead's own row instead of blocking the site. {GREEN}."
    r = subprocess.run(["gh", "issue", "close", str(n), "--comment", reason], capture_output=True, text=True)
    print(f"#{n}: {'closed' if r.returncode == 0 else 'FAILED ' + r.stderr.strip()[:120]} -- {reason[:90]}")
