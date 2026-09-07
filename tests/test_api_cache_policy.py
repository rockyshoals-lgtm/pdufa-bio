# -*- coding: utf-8 -*-
"""The v1 API's edge cache policy cannot hand a reader a day-old payload.

Audit 2026-09-07 C1 (P1): the first API request of the auditor's run returned as_of two days
old with no SRRK row -- served from stale-while-revalidate=86400 on the deployed function.
The site's product is the date, so the bound is: fresh <= 300 s, stale-while-revalidate
<= 300 s, stale-if-error <= 3600 s, on every Cache-Control the API sets (Vercel honours
CDN-Cache-Control / Vercel-CDN-Cache-Control over Cache-Control at the edge, so all three
carriers are read).

Proved 0 -> 1 -> 0 on 2026-09-07 by planting stale-while-revalidate=86400 in _lib.mjs.

09-07 P2 (midday): the legacy feed /api/data (api/data.js) still shipped s-maxage=16000 /
stale-while-revalidate=86400, and vercel.json carried a SECOND writer of the same header for
that path. Same bound now applies to every file that sets a cache directive for an /api/
route: api/v1/*.mjs, api/data.js, and any vercel.json "headers" entry whose source starts
with /api/. Proved 0 -> 1 -> 0 by planting s-maxage=16000 back into data.js.
"""
import glob
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
API = os.path.join(SITE, "api", "v1")
LIMITS = {"s-maxage": 300, "stale-while-revalidate": 300, "stale-if-error": 3600}
DIRECTIVE = re.compile(r"(s-maxage|stale-while-revalidate|stale-if-error)\s*=\s*(\d+)")


def test_api_cache_policy():
    bad, seen = [], 0
    # vercel.json: a header rule on an /api/ path is a second owner of the policy; it must
    # obey the same bound (and ideally not exist -- the function owns its own header).
    vj = json.load(io.open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
    for rule in vj.get("headers", []):
        if not str(rule.get("source", "")).startswith("/api/"):
            continue
        for h in rule.get("headers", []):
            if str(h.get("key", "")).lower().endswith("cache-control"):
                for d, v in DIRECTIVE.findall(str(h.get("value", ""))):
                    seen += 1
                    if int(v) > LIMITS[d]:
                        bad.append(f"vercel.json {rule['source']}: {d}={v} > {LIMITS[d]}")
    files = sorted(glob.glob(os.path.join(API, "*.mjs"))) + [os.path.join(SITE, "api", "data.js")]
    for p in files:
        # strip block and line comments: the policy that ships is the one in code
        src = re.sub(r"/\*.*?\*/", "", io.open(p, encoding="utf-8", errors="replace").read(),
                     flags=re.S)
        for line in src.splitlines():
            code = line.split("//", 1)[0]
            for d, v in DIRECTIVE.findall(code):
                seen += 1
                if int(v) > LIMITS[d]:
                    bad.append(f"{os.path.basename(p)}: {d}={v} > {LIMITS[d]}  in: {code.strip()}")
    assert seen > 0, "no cache directive found under api/v1 -- guard cannot see"
    assert not bad, "API cache policy allows a stale payload:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_api_cache_policy()
    print("OK")
