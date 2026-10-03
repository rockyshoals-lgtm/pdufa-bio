# -*- coding: utf-8 -*-
"""CI guard: time-derived statuses are computed at REQUEST time (audit 2026-10-03, Tier 1.5).

While the build stalled (2026-09-27 to 10-03) the API kept serving the statuses baked into
dataset.mjs: AACR Pancreatic and ASTRO "In progress" after they ended, EASD and WMS "Scheduled"
while they ran. This runs the API's own code (api/v1/_lib.mjs, under node) for several Eastern dates,
including 2026-10-03, and fails when:
  * a Conference row's served status disagrees with its dates on that day
    (end < today -> Ended; start <= today <= end -> In progress; else Scheduled);
  * an Upcoming day-precision PDUFA whose goal date has passed is not served as "Awaiting";
  * a Decided row is served as anything but Decided;
  * the ?status= filter does not use the request-time status.

    python tests/test_request_time_status.py
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(HERE, "pdufa_site_src", "api", "v1", "_lib.mjs").replace("\\", "/")

JS = r"""
const m = await import('file:///%s');
const out = [];
for (const today of ['2026-09-27', '2026-10-03', '2026-10-15', '2027-01-04']) {
  for (const e of m.DATA) {
    if (!['Conference', 'PDUFA'].includes(e.type)) continue;
    out.push([today, e.id, e.type, e.st, e.dp, e.d, (e._d && e._d.end) || null, m.liveStatus(e, today)]);
  }
}
const src = (await import('node:fs')).readFileSync(new URL('file:///%s'), 'utf8');
console.log(JSON.stringify({ rows: out,
  shape_uses_live: /const live = liveStatus\(e\)/.test(src),
  filter_uses_live: /rows\.filter\(e => String\(liveStatus\(e, td\)/.test(src) }));
""" % (LIB, LIB)


def expected(typ, st, dp, d, end, today):
    if typ == "Conference":
        end = (end or d)[:10]
        return "Ended" if end < today else ("In progress" if d[:10] <= today else "Scheduled")
    if st == "Upcoming" and dp == "day" and d[:10] < today:
        return "Awaiting"
    return st


def main():
    node = shutil.which("node")
    if not node:
        print("FAIL: node not found; this guard runs the API's own code")
        return 1
    r = subprocess.run([node, "--input-type=module", "-e", JS], capture_output=True, text=True, cwd=HERE)
    if r.returncode != 0:
        print("FAIL: node could not run api/v1/_lib.mjs:\n" + r.stderr[-1500:])
        return 1
    j = json.loads(r.stdout.strip().splitlines()[-1])
    fails = []
    if not j["shape_uses_live"]:
        fails.append("shape() does not apply liveStatus(e): the baked status is served")
    if not j["filter_uses_live"]:
        fails.append("?status= filters on the baked status, not the request-time one")
    for today, rid, typ, st, dp, d, end, got in j["rows"]:
        want = expected(typ, st, dp, d, end, today)
        if got != want:
            fails.append(f"{today} {rid}: served {got!r}, dates say {want!r} (baked {st!r})")
    if fails:
        print(f"FAIL: {len(fails)} request-time status failure(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    n = len({x[1] for x in j['rows']})
    print(f"OK -- {n} Conference/PDUFA rows x 4 Eastern dates: statuses follow the date, not the build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
