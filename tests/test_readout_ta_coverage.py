# -*- coding: utf-8 -*-
"""CI guard: forward readouts carry a therapeutic area, tagged by hand from a source (audit 2026-10-03, 3.3).

Fails when, in the RENDERED dataset, more than 30% of forward (Estimated/Guided) readouts carry no
therapeutic area, or when a hand tag in _readout_ta_manual.json has no basis/source, or its basis is only
the row's drug name (a name match), or a row listed as an NCT mismatch got tagged from that registry record.

    python tests/test_readout_ta_coverage.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    src = io.open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = {r["id"]: r for r in json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))}
    man = json.load(io.open(os.path.join(HERE, "_readout_ta_manual.json"), encoding="utf-8"))
    fails = []
    fwd = [r for r in rows.values() if r.get("type") == "Readout" and r.get("st") in ("Estimated", "Guided")]
    un = [r for r in fwd if str(r.get("ta") or "") in ("", "Other")]
    share = len(un) / max(1, len(fwd))
    if share >= 0.30:
        fails.append(f"{len(un)}/{len(fwd)} forward readouts untagged ({share:.0%}); the target is under 30%")
    for k, t in man.get("tags", {}).items():
        if not t.get("basis") or not t.get("source"):
            fails.append(f"{k}: hand tag without basis/source")
            continue
        r = rows.get(k)
        if r:
            name = re.sub(r"\s+readout$", "", str(r.get("name") or ""), flags=re.I).strip().lower()
            body = re.sub(r"^(ClinicalTrials\.gov conditions|Sponsor SEC filing):\s*", "", t["basis"]).strip().lower()
            if body == name or not re.search(r"[a-z]{4,}", body.replace(name, "")):
                fails.append(f"{k}: basis is only the drug name (a name match): {t['basis']!r}")
    for m in man.get("nct_mismatch", []):
        if m["id"] in man.get("tags", {}):
            fails.append(f"{m['id']}: tagged although its NCT record names a different drug")
        if (rows.get(m["id"], {}).get("_d") or {}).get("registry"):
            fails.append(f"{m['id']}: carries registry status from an NCT record that names a different drug")
    if fails:
        print(f"FAIL: {len(fails)} readout-TA failure(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {len(fwd) - len(un)}/{len(fwd)} forward readouts tagged ({1 - share:.0%}); every hand tag has a sourced basis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
