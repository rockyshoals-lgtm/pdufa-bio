# -*- coding: utf-8 -*-
"""CI guard: the data's build time is published next to the request date (audit 2026-10-03, Tier 1.4).

From 2026-09-27 to 10-03 no build deployed. The API's meta.as_of is the request's Eastern date, so it
kept advancing and a consumer could not tell the data was six days old; the site's stamps carried a
content date and nothing said the build had stopped. Fails when:
  1. the rendered build-info (pdufa_site_src/build-info.json, api/_build-info.json) has no
     data_built_at in ISO-8601;
  2. the API library does not put meta.data_built_at in its JSON meta (both the normal and the
     stale-cache responses), read from the same build-info;
  3. the home page or /calendar freshness stamp has no [data-fresh-built] slot, or its script does
     not read data_built_at.

    python tests/test_data_built_at.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    fails = []
    for rel in ("build-info.json", os.path.join("api", "_build-info.json")):
        bi = json.load(io.open(os.path.join(SITE, rel), encoding="utf-8"))
        v = str(bi.get("data_built_at") or "")
        if not re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d", v):
            fails.append(f"/{rel}: data_built_at missing or not ISO ({v!r})")
    lib = io.open(os.path.join(SITE, "api", "v1", "_lib.mjs"), encoding="utf-8").read()
    if lib.count("data_built_at: DATA_BUILT_AT") < 2:
        fails.append("api/v1/_lib.mjs: meta.data_built_at is not in both JSON meta blocks")
    if "_build-info.json" not in lib:
        fails.append("api/v1/_lib.mjs: data_built_at is not read from _build-info.json")
    for rel in ("index.html", os.path.join("calendar", "index.html")):
        doc = io.open(os.path.join(SITE, rel), encoding="utf-8", errors="replace").read()
        if "data-fresh-built" not in doc:
            fails.append(f"/{rel}: freshness stamp has no data-fresh-built slot")
        if "j.data_built_at" not in doc:
            fails.append(f"/{rel}: freshness stamp script does not read data_built_at")
    if fails:
        print(f"FAIL: {len(fails)} data_built_at failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- data_built_at in build-info, in the API meta, and read by the home and /calendar stamps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
