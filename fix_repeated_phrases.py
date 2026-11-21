# -*- coding: utf-8 -*-
"""fix_repeated_phrases.py -- write each dataset row name with no phrase repeated back to back.

2026-11-20: 60 guided-readout names on the API dataset read "TP-04 Kore Phase 2 Phase 2 topline", "VK2735 VK2735
maintenance dosing study, Part 2 Part 2 results" and the like (apply_1117_readout_mine.row_name joined program, trial
and readout without merging the phrase they share). Every page built from the dataset showed the stutter.

Each affected name has the second copy dropped (text_hygiene.collapse_repeats); nothing else in it changes. (Not
rebuilt from _d.program/_d.trial: on some rows those were edited after the name was written, and a rebuild dropped
trial names such as NATiV3.) Edits the "name" line of each affected row in place, so the rest of
the file is byte-for-byte unchanged. Idempotent: a second run finds nothing.

    python fix_repeated_phrases.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from text_hygiene import collapse_repeats, find_repeat  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.find("["):src.rfind("]") + 1])
    changed = []
    for r in rows:
        old = r.get("name")
        if not isinstance(old, str) or not find_repeat(old):
            continue
        new = collapse_repeats(old)
        rid = json.dumps(r["id"])
        i = src.find(f'"id": {rid},')
        if i < 0 or src.find(f'"id": {rid},', i + 1) >= 0:
            print(f"  SKIP {r['id']}: id not found exactly once")
            continue
        line_old = f'"name": {json.dumps(old)},'
        j = src.find(line_old, i)
        k = src.find('"id": ', i + 1)
        if j < 0 or (0 <= k < j):
            print(f"  SKIP {r['id']}: name line not found in its row")
            continue
        src = src[:j] + f'"name": {json.dumps(new)},' + src[j + len(line_old):]
        changed.append((r["id"], old, new))
    for rid, old, new in changed:
        print(f"  {rid}: {old!r} -> {new!r}")
    print(f"repeated-phrase names fixed: {len(changed)}")
    if changed and not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8", newline="").write(src)
    return changed


if __name__ == "__main__":
    main()
