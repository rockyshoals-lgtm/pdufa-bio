# -*- coding: utf-8 -*-
"""sync_readout_outcomes.py -- a Reported readout in the API must carry its outcome.

Audit 2026-09-05 (0800 slot) P2-8: API `outcome` was null on all four Reported readouts
(MPLT 07-27, TENX 08-10, KYTX 08-15, AMLX 08-18) while the pages stated the outcomes in
words. `outcome` is served from the dataset's `oc` field, which only the PDUFA decision
capture ever set. This derives `oc` for Reported readouts from the row's own verified
review text -- the sentence a human wrote against the sponsor's release -- using the
house vocabulary only (house rule 3: "met" / "did not meet its primary endpoint", never
"succeeded" / "failed"). A review that states neither is left null, loudly.

Idempotent; runs daily in CI after the readout builders. Owner of `oc` on Readout rows.
"""
import io, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")

RULES = [   # (pattern on the review text, outcome as served)  -- first match wins
    (r"\bdid not meet (?:its|the) (?:FDA-agreed )?primary endpoint", "Did not meet primary endpoint"),
    (r"\bmet (?:its|the) (?:FDA-agreed )?primary endpoint", "Met primary endpoint"),
    (r"\bTERMINATED\b|\bwas terminated\b|\bdiscontinued\b", "Trial terminated; no readout"),
]


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = src.find("[")
    arr, dend = json.JSONDecoder().raw_decode(src[j:])
    changed, unresolved = 0, []
    for r in arr:
        if r.get("type") != "Readout" or str(r.get("st", "")).lower() != "reported":
            continue
        review = str((r.get("_d") or {}).get("review") or "")
        want = next((oc for pat, oc in RULES if re.search(pat, review, re.I)), None)
        if want is None:
            unresolved.append(f"{r.get('t')} {r.get('d')} ({r.get('id')})")
            continue
        if r.get("oc") != want:
            r["oc"] = want
            changed += 1
            print(f"  {r.get('t')} {r.get('d')}: outcome -> {want}")
    if changed:
        io.open(DATASET, "w", encoding="utf-8").write(src[:j] + json.dumps(arr, indent=1) + src[j + dend:])
    print(f"readout outcomes: {changed} set; {len(unresolved)} Reported row(s) whose review "
          f"states no primary-endpoint result" + (": " + ", ".join(unresolved) if unresolved else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
