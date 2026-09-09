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
import io
import json
import os
import re
import subprocess
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


HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATEMOD = re.compile(r'"dateModified"\s*:\s*"([^"]{10,32})"')


def repo_date(path):
    """The dateModified in THIS checkout's copy of `path`, or '' when there is no such file.

    This is the reference the live body is graded against: after a deploy, the served page
    must equal the file that was deployed. Only static page paths resolve; /api/* and
    /build-info.json are generated at build time and have no comparable file here."""
    p = path.split("?")[0].strip("/")
    f = os.path.join(SITE, p, "index.html") if p else os.path.join(SITE, "index.html")
    if not os.path.isfile(f):
        return ""
    try:
        m = DATEMOD.search(io.open(f, encoding="utf-8", errors="replace").read())
    except Exception:
        return ""
    return m.group(1)[:10] if m else ""


# WHY THIS IS A FLAG AND NOT AUTOMATIC (2026-09-09, caught before it shipped):
# The first version inferred "the deployed tree is this checkout" by comparing /build-info.json's
# `commit` with local HEAD. That is wrong. CI stamps build-info with the commit it BUILT FROM,
# then regenerates data on top and deploys the result -- so the SHA can match while the files
# differ, and the check reported /calendar "live 09-09 vs deployed 09-08" on a perfectly healthy
# site. The comparison is only sound where the working tree IS the deployed artifact, which is
# the CI runner immediately after its own push. So CI opts in explicitly; a dev box never does.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--gap", type=int, default=45)
    ap.add_argument("--min-built", default=None)
    ap.add_argument("--compare-repo", action="store_true",
                    help="Grade each live page's dateModified against this checkout's copy. "
                         "ONLY valid where the working tree is the deployed artifact (the CI "
                         "runner right after its own push); see the note above.")
    a = ap.parse_args()

    fails = []
    first = {}
    today_et = dt.datetime.now(EASTERN).date().isoformat()
    for p in range(a.passes):
        stamp = dt.datetime.now(EASTERN).strftime("%H:%M:%S ET")
        # LIVE vs REPO, per pass. Auditor 09-08e asks which of two things produced the stale
        # bodies: (1) the production alias still pointed at an older deployment -- then EVERY
        # url is old together and it is promotion timing, not caching; or (2) the edge served
        # one url's old body while others were new -- a routing/cache fault a purge might fix.
        #
        # RETRACTED FIRST ATTEMPT (2026-09-09, before it ever ran in CI): I compared the urls'
        # dateModified values to each other and flagged disagreement. That is wrong and would
        # have failed every healthy run. dateModified is deliberately each page's CONTENT-change
        # date (build_date_modified.py, which refuses to emit build time), so /calendar at
        # 09-08 and /pdufa/SRRK-apitegromab at 09-06 is correct by construction. Verified: the
        # local file on disk carries the same 09-06 the edge served.
        #
        # The sound reference is the repo itself. After a deploy the served page must equal the
        # file we deployed, so compare each live page's dateModified with the same file's
        # dateModified in this checkout -- and only when the live build names this tree, which
        # is the case in CI right after the push and rarely the case on a dev box.
        vintage, live_commit = {}, ""
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
            dm = DATEMOD.search(text)
            if dm:
                vintage[path] = dm.group(1)[:10]
            if path == "/build-info.json":
                info = json.loads(text)
                built, live_commit = info.get("built", ""), str(info.get("commit", ""))
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
        # The 09-08e discriminator, printed every pass so a stale body is diagnosed the moment
        # it is caught rather than argued about afterwards.
        checkable = {k: v for k, v in vintage.items() if repo_date(k)}
        if not a.compare_repo:
            print(f"[{stamp}] live-vs-repo comparison off (--compare-repo not set; live build "
                  f"{live_commit or '?'}), not credited")
        elif checkable:
            stale = {k: (v, repo_date(k)) for k, v in checkable.items() if repo_date(k) != v}
            if stale:
                spread = ", ".join(f"{k}: live {v[0]} vs deployed {v[1]}"
                                   for k, v in sorted(stale.items()))
                print(f"[{stamp}] STALE BODY vs the tree this build deployed: {spread}")
                if len(stale) < len(checkable):
                    print(f"[{stamp}]   -> {len(stale)} of {len(checkable)} stale. Some but not "
                          f"all means the alias is NOT lagging on an older deployment (that "
                          f"would make every url stale together): routing or cache. Purge and "
                          f"re-fetch; if it clears, the 09-07 finding is a caching fault.")
                else:
                    print(f"[{stamp}]   -> EVERY url stale: the alias is still serving an "
                          f"older deployment. Promotion timing, not caching; a purge will "
                          f"not help and the wait loop above ended too early.")
                fails.append(f"pass{p+1}: stale vs deployed tree: {spread}")
            else:
                print(f"[{stamp}] live matches the deployed tree on {len(checkable)} url(s)")
        if p < a.passes - 1:
            time.sleep(a.gap)
    print("RESULT:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
