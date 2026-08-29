# -*- coding: utf-8 -*-
"""NAV FREEZE (red team 2026-08-29e, Part 0): the navigation must not change before
2027-01-01.

FDA Tracker holds Bing #1 for "pdufa calendar" with a nine-link sitelink block; we sit #2
with none. Sitelinks are the one visible difference at the top of that SERP, and Bing
awards them for a stable, shallow, clearly-labelled hub structure observed consistently
over months. The clock restarts from the LAST change, so four months of stability is the
asset and one careless rename burns it. The audit called this "the one most likely to be
broken by accident" -- in this codebase, a directive without a guard IS an accident
waiting to happen, so this guard makes the freeze mechanical.

Two checks:
  1. rebuild_nav.py's PRIMARY / GROUPS / PRO match _nav_frozen_until_2027.json exactly --
     labels, order, groupings, URLs.
  2. A sample of live pages carries exactly the frozen link sequence inside the NAVC
     block, so a stray builder writing its own nav is caught too.

The freeze self-expires: from 2027-01-01 this test passes with a note, and the frozen
file can then be updated deliberately (never casually -- the clock restarts).

Frozen: the nav bar, labels, order, groupings, URLs.
Not frozen: page content, titles, meta descriptions, schema, in-page links.
"""
import datetime as dt
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "pdufa_site_src")
FROZEN = os.path.join(ROOT, "_nav_frozen_until_2027.json")

SAMPLE = ["index.html", os.path.join("calendar", "index.html"),
          os.path.join("decisions", "index.html"),
          os.path.join("drug", "index.html"),
          os.path.join("research", "index.html")]


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "rebuild_nav", os.path.join(ROOT, "rebuild_nav.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    frozen = json.load(io.open(FROZEN, encoding="utf-8"))
    today = dt.date.today().isoformat()
    if today >= frozen["frozen_until"]:
        print(f"  PASS (freeze expired {frozen['frozen_until']}): the nav may now be "
              f"changed DELIBERATELY -- update the frozen file with any change, because "
              f"the sitelink clock restarts from it")
        return 0

    bad = 0
    mod = load_builder()
    want_primary = [tuple(x) for x in frozen["primary"]]
    want_groups = [(g, [tuple(x) for x in items]) for g, items in frozen["groups"]]
    want_pro = tuple(frozen["pro"])
    if [tuple(x) for x in mod.PRIMARY] != want_primary:
        print(f"  FAIL rebuild_nav.PRIMARY changed: {mod.PRIMARY} != {want_primary}")
        bad += 1
    if [(g, [tuple(x) for x in items]) for g, items in mod.GROUPS] != want_groups:
        print(f"  FAIL rebuild_nav.GROUPS changed (labels, order or grouping)")
        bad += 1
    if tuple(mod.PRO) != want_pro:
        print(f"  FAIL rebuild_nav.PRO changed: {mod.PRO} != {want_pro}")
        bad += 1

    # the frozen link sequence as it should appear on every page
    want_seq = ([h for h, _ in want_primary]
                + [h for _, items in want_groups for h, _ in items]
                + [want_pro[0]])
    checked = 0
    for rel in SAMPLE:
        p = os.path.join(SITE, rel)
        if not os.path.exists(p):
            print(f"  FAIL sample page missing: {rel}")
            bad += 1
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<!--NAVC:BEGIN-->(.*?)<!--NAVC:END-->", doc, re.S)
        if not m:
            print(f"  FAIL {rel}: no NAVC block -- a builder is writing its own nav")
            bad += 1
            continue
        got_seq = re.findall(r'href="([^"]+)"', m.group(1))
        got_seq = [h for h in got_seq if h != "/"]          # brand link is chrome
        if got_seq != want_seq:
            print(f"  FAIL {rel}: nav links deviate from the frozen sequence")
            print(f"       got : {got_seq}")
            print(f"       want: {want_seq}")
            bad += 1
        checked += 1

    if bad:
        print(f"\nNAV FREEZE VIOLATED ({bad} finding(s)). The nav is frozen until "
              f"{frozen['frozen_until']} -- red team 2026-08-29e Part 0. Every change "
              f"resets Bing's sitelink stability clock; revert unless David has "
              f"explicitly lifted the freeze.")
        return 1
    print(f"  PASS: nav frozen and intact (builder spec + {checked} sample pages) "
          f"until {frozen['frozen_until']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
