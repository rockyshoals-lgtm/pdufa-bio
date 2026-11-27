# -*- coding: utf-8 -*-
"""CI guard: /pdufa-date-changes lists every sourced goal-date extension, each with both dates quoted.

2026-11-27 (OMW, date-change history): the page listed only the 4 changes the live dataset rows carry, while the
2024-2025 decision-timing census held 21 extensions with the sponsor's quote for the old and the new date. The
builder now reads both (plus pdufa_extensions_sourced.json for later ones). This fails if an extension row lost a
quote or a link, if a stated reason reads like a research note, or if the built page leaves a row out.

    python tests/test_date_changes_extensions.py      (PLANT=1 drops a quote; the guard must fail)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_date_changes as D  # noqa: E402

PAGE = os.path.join(HERE, "pdufa_site_src", "pdufa-date-changes", "index.html")
NOTE_WORDS = re.compile(r"snippet|per search|not read|\bTODO\b|\bpass \d\b", re.I)


def main():
    exts = D.collect_extensions()
    bad = []
    if os.environ.get("PLANT") == "1" and exts:
        exts[0]["old_quote"] = ""
    if len(exts) < 21:
        bad.append(f"only {len(exts)} sourced extensions (expected at least 21 from the 2024-2025 census)")
    for x in exts:
        tag = f'{x["t"] or "-"} {x["drug"]} {x["new"]}'
        if not (x["old_quote"] and x["new_quote"]):
            bad.append(f"{tag}: a goal date has no quote")
        if not (x["old_url"].startswith("http") and x["new_url"].startswith("http")):
            bad.append(f"{tag}: a goal date has no source link")
        if not 28 <= x["days"] <= 200:
            bad.append(f"{tag}: extension of {x['days']} days is outside 28-200; check both dates")
        if NOTE_WORDS.search(x["public_reason"]):
            bad.append(f"{tag}: the stated reason reads like a research note: {x['public_reason'][:80]}")
    if os.path.exists(PAGE):
        doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
        if "Goal date extensions" in doc:
            for x in exts:
                if x["new_url"].replace("&", "&amp;") not in doc and x["new_url"] not in doc:
                    bad.append(f'{x["t"] or "-"} {x["drug"]}: extension source missing from the built page')
            if not os.path.exists(os.path.join(os.path.dirname(PAGE), D.CSV_NAME)):
                bad.append(f"{D.CSV_NAME} is linked from the page but was not written")
    if bad:
        print(f"FAIL test_date_changes_extensions: {len(bad)} problem(s); fix: decision_timing_2024_2025.json / "
              f"pdufa_extensions_sourced.json, then python build_date_changes.py")
        for b in bad[:20]:
            print("   " + b)
        return 1
    print(f"OK -- {len(exts)} sourced goal-date extensions, each with both dates quoted and linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
