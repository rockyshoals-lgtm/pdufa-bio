"""Post-deploy verifier: audits the LIVE site the way the auditor does (2026-09-08 ORDER 1).

For each graded URL, N fetches spaced S seconds apart with Cache-Control: no-cache, and asserts:
  * body md5 == ETag (Vercel's ETag is the body md5; a mismatch is the stale-body window seen
    on 2026-09-07 when the CDN served a 40-hour-old body under the new build's headers);
  * bodies are byte-identical across passes (no flip-flop between two builds);
  * /build-info.json `built` is not older than --min-built (ISO), if given;
  * /api/v1/events meta.as_of == Eastern date now (T-1 rule: a build is never dated tomorrow);
  * /calendar lede sums: ahead + decided == total.

Exit 0 only if every check passes on every pass. Prints one line per fetch so the output can be
pasted verbatim into a builder ack.

Usage:  python verify_live_deploy.py [--passes 3] [--gap 45] [--min-built 2026-09-08T16:00:00+00:00]
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

BASE = "https://www.pdufa.bio"
PAGES = ["/calendar", "/fda-this-month", "/api/v1/events?limit=5",
         "/pdufa/SRRK-apitegromab", "/pdufa/NRXP", "/build-info.json"]
EASTERN = ZoneInfo("America/New_York")


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={
        "Cache-Control": "no-cache", "Pragma": "no-cache",
        "User-Agent": "pdufa.bio-verify/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return body, {k.lower(): v for k, v in r.headers.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--gap", type=int, default=45)
    ap.add_argument("--min-built", default=None)
    a = ap.parse_args()

    fails = []
    first = {}
    today_et = dt.datetime.now(EASTERN).date().isoformat()
    for p in range(a.passes):
        stamp = dt.datetime.now(EASTERN).strftime("%H:%M:%S ET")
        for path in PAGES:
            try:
                body, h = fetch(path)
            except Exception as e:  # noqa: BLE001
                fails.append(f"{path}: fetch error {e}")
                print(f"[{stamp}] {path}: FETCH ERROR {e}")
                continue
            md5 = hashlib.md5(body).hexdigest()
            etag = (h.get("etag") or "").replace("W/", "").strip('"')
            cache = h.get("x-vercel-cache", "?")
            # Static files: Vercel's ETag is the body md5. /api/* is a function response whose
            # ETag is not a body hash (observed 2026-09-08: "d43bc993bfc..." vs md5 a2940748ce89),
            # so only body stability across passes is asserted there.
            static = not path.startswith("/api/")
            ok_etag = (etag == md5) if (etag and static) else True
            same = first.setdefault(path, md5) == md5
            note = []
            if not ok_etag:
                note.append(f"ETAG MISMATCH etag={etag[:12]}")
                fails.append(f"{path} pass{p+1}: md5 {md5[:12]} != etag {etag[:12]}")
            if not same:
                note.append("BODY CHANGED vs pass 1")
                fails.append(f"{path} pass{p+1}: body differs from pass 1")
            text = body.decode("utf-8", "replace")
            if path == "/build-info.json":
                built = json.loads(text).get("built", "")
                note.append(f"built={built}")
                if a.min_built and built < a.min_built:
                    fails.append(f"build-info built {built} < {a.min_built}")
                    note.append("OLDER THAN MIN")
            elif path.startswith("/api/v1/events"):
                meta = json.loads(text).get("meta", {})
                note.append(f"as_of={meta.get('as_of')}")
                if meta.get("as_of") != today_et:
                    fails.append(f"api as_of {meta.get('as_of')} != Eastern today {today_et}")
                    note.append("AS_OF NOT TODAY")
            elif path == "/calendar":
                m = re.search(r"(\d+) FDA decision dates.*?(\d+) are still ahead, and (\d+) have been decided",
                              text, re.S)
                if m:
                    tot, ahead, dec = (int(x) for x in m.groups())
                    note.append(f"lede {tot}={ahead}+{dec}")
                    if ahead + dec != tot:
                        fails.append(f"calendar lede {ahead}+{dec}!={tot}")
                else:
                    fails.append("calendar lede not found")
                    note.append("LEDE MISSING")
            print(f"[{stamp}] {path}: md5={md5[:12]} etag={'ok' if ok_etag else 'BAD'} "
                  f"cache={cache} {' '.join(note)}")
        if p < a.passes - 1:
            time.sleep(a.gap)
    print("RESULT:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
