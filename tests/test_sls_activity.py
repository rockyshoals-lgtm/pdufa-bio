# -*- coding: utf-8 -*-
"""test_sls_activity.py -- the /sls activity feed must stay current and stay sourced.

/sls claims to be the record for this name and now says "Updated daily" on the page. Two ways that
becomes a lie: the collector stops running and nobody notices, or an entry appears without a link
back to the filing it came from. Both are checked here.

    python tests/test_sls_activity.py
"""
import json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(HERE, "_sls_activity.json")
PAGE = os.path.join(HERE, "pdufa_site_src", "sls", "index.html")

MAX_RUN_AGE = 4      # days; the job is daily, so 4 tolerates a weekend plus one failure
MAX_PRICE_AGE = 6    # days; trading days only, so a long weekend plus a holiday

# Only these hosts are primary. A third-party aggregator link would break the page's own promise.
OK_HOST = re.compile(r"^https://(www\.sec\.gov|ir\.sellaslifesciences\.com|data\.sec\.gov)/")


def main():
    ok = True
    if not os.path.exists(LOG):
        print("FAIL: _sls_activity.json missing. Run: python sls_daily.py")
        sys.exit(1)
    d = json.load(open(LOG, encoding="utf-8"))
    events = d.get("events", [])
    today = dt.date.today()

    print(f"activity log: {len(events)} events, cursor {d.get('cursor')}, "
          f"last run {d.get('last_run')}")

    # 1. the collector is actually running
    try:
        age = (today - dt.date.fromisoformat(d.get("last_run", ""))).days
    except Exception:
        age = 999
    if age > MAX_RUN_AGE:
        ok = False
        print(f"\nFAIL: collector last ran {age} days ago (limit {MAX_RUN_AGE}). /sls says "
              f"'Updated daily'; it is not. Fix: python sls_daily.py")
    else:
        print(f"  PASS: collector ran {age} day(s) ago")

    # 2. price is fresh
    px = d.get("price") or {}
    try:
        page = (today - dt.date.fromisoformat(px.get("as_of", ""))).days
    except Exception:
        page = 999
    if page > MAX_PRICE_AGE:
        ok = False
        print(f"\nFAIL: price as_of is {page} days old (limit {MAX_PRICE_AGE}).")
    else:
        print(f"  PASS: price as_of {px.get('as_of')} ({page} day(s) old, ${px.get('close')})")

    # 3. every entry is sourced, dated, and points at a primary host
    bad = [e for e in events
           if not e.get("url") or not e.get("date") or not OK_HOST.match(e.get("url", ""))]
    if bad:
        ok = False
        print(f"\nFAIL: {len(bad)} activity entr(ies) without a primary-source link or date:")
        for e in bad[:8]:
            print(f"   {e.get('date','?')}  {e.get('form','?')}  url={e.get('url')!r}")
    else:
        print(f"  PASS: all {len(events)} entries carry a dated SEC or SELLAS source link")

    # 4. a quote must name who said it
    noname = [q for e in events for q in (e.get("quotes") or []) if not q.get("speaker")]
    nq = sum(len(e.get("quotes") or []) for e in events)
    if noname:
        ok = False
        print(f"\nFAIL: {len(noname)} quote(s) with no attributed speaker.")
    else:
        print(f"  PASS: all {nq} extracted quote(s) name a speaker")

    # 5. the page actually renders the feed
    if os.path.exists(PAGE):
        html = open(PAGE, encoding="utf-8", errors="replace").read()
        if "Latest activity" not in html:
            ok = False
            print("\nFAIL: /sls does not contain the Latest activity section. "
                  "Fix: python build_sls_hub.py")
        else:
            print("  PASS: /sls renders the activity section")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
