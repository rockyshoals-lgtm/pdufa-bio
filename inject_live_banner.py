# -*- coding: utf-8 -*-
"""inject_live_banner.py -- load the "Just in" banner (lib/live-banner.js) on the home page and on every armed
drug's PDUFA page, so a decision the every-minute news watch posts shows there within the minute.

The pages are static and rebuilt by the rebuild; the banner fetches /api/v1/live (CDN, 30 s) in the browser and
adds nothing when there is nothing to show. One marker-delimited script tag per page (LIVE:B ... LIVE:E), placed
before </body>; a page that is no longer armed keeps its tag for 14 days after a post on it (the banner shows a
post for 14 days), then loses it. Reads pdufa_site_src/api/_watch_armed.mjs (build_watch_armed.py) and
_live_published.json (sync_live_log.py). Guard: tests/test_live_watch.py.

    python inject_live_banner.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
ARMED = os.path.join(SITE, "api", "_watch_armed.mjs")
LOG = os.path.join(HERE, "_live_published.json")
TAG = '<!--LIVE:B--><script src="/lib/live-banner.js" defer></script><!--LIVE:E-->'
RX = re.compile(r"<!--LIVE:B-->.*?<!--LIVE:E-->", re.S)


def page_file(url):
    url = str(url or "").strip("/")
    return os.path.join(SITE, *url.split("/"), "index.html") if url else os.path.join(SITE, "index.html")


def wanted(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    s = io.open(ARMED, encoding="utf-8").read()
    armed = json.loads(s[s.index("{"):s.rindex("}") + 1])
    pages = {"/"} | {r["url"] for r in armed["rows"] if str(r.get("url") or "").startswith("/pdufa/")}
    if os.path.exists(LOG):
        for p in json.load(io.open(LOG, encoding="utf-8")).get("posts", []):
            try:
                at = dt.datetime.fromisoformat(p["posted_at"])
            except Exception:  # noqa: BLE001
                continue
            if now - at < dt.timedelta(days=14) and str(p.get("page") or "").startswith("/pdufa/"):
                pages.add(p["page"])
    return pages


def main():
    want = {os.path.normpath(page_file(u)) for u in wanted()}
    added = removed = 0
    for f in [os.path.join(SITE, "index.html")] + glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
        f = os.path.normpath(f)
        html = io.open(f, encoding="utf-8").read()
        has = RX.search(html)
        if f in want and not has and "</body>" in html:
            i = html.rindex("</body>")
            io.open(f, "w", encoding="utf-8", newline="").write(html[:i] + TAG + html[i:])
            added += 1
        elif f not in want and has:
            io.open(f, "w", encoding="utf-8", newline="").write(RX.sub("", html))
            removed += 1
    missing = [u for u in want if not os.path.exists(u)]
    print(f"live banner: {len(want)} page(s) wanted, {added} added, {removed} removed"
          + (f"; {len(missing)} wanted page(s) not built yet" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
