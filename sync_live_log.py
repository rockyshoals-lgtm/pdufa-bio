# -*- coding: utf-8 -*-
"""sync_live_log.py -- keep pdufa.bio's own record of what the every-minute news watch posted.

The watch (pdufa_site_src/api/cron/news-watch.mjs) posts to the live store, not to git. This reads its public
feed (https://www.pdufa.bio/api/v1/live) in the rebuild and merges it into _live_published.json, so the record
outlives the store and the post time can feed the posting-speed stamp (build_post_speed.py, confirmed posts only).

Append-only: a post is never removed and its post time never changes; only its status moves (posted -> confirmed
or retracted). A post that turns RETRACTED gets one /corrections entry (_corrections.json), dated the day it was
retracted in Eastern time, saying what the automatic post said and why it was withdrawn. A feed that cannot be
read changes nothing.

    python sync_live_log.py [--fixture live.json]
"""
import argparse
import datetime as dt
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_live_published.json")
CORR = os.path.join(HERE, "_corrections.json")
FEED = "https://www.pdufa.bio/api/v1/live"
UA = {"User-Agent": "Mozilla/5.0 (compatible; pdufa.bio builder; +https://www.pdufa.bio/about)"}
KEEP = ("id", "ticker", "kind", "text", "source", "posted_at", "minutes_after_source", "page", "status",
        "confirmed_at", "retracted_at", "retract_reason")


def _key(p):
    return (p.get("id"), p.get("posted_at"))


def merge(log, feed_posts):
    """(new log, [newly retracted posts]). A post is one (row id, posted_at): a later post on the same row is a new
    entry, never an edit of the old one. Only status moves, and only forward: posted -> confirmed or retracted,
    confirmed -> retracted. A retraction is final. What a post said (its text, kind, source) never changes."""
    posts = {_key(p): p for p in log.get("posts") or []}
    newly = []
    for f in feed_posts:
        f = {k: f[k] for k in KEEP if k in f}
        if not f.get("id") or not f.get("posted_at"):
            continue
        if f.get("status") == "retracted" and not f.get("retracted_at"):
            continue                                   # retracted by hand, not yet recorded by the watch: wait (red team 7)
        old = posts.get(_key(f))
        if not old:
            posts[_key(f)] = f
            if f.get("status") == "retracted":
                newly.append(f)
            continue
        if any(old.get(k) != f.get(k) for k in ("kind", "text", "source")):
            continue                                   # not the post we logged: never rewrite what it said
        rank = {"posted": 0, "confirmed": 1, "retracted": 2}
        if rank.get(f.get("status"), -1) <= rank.get(old.get("status"), -1):
            continue                                   # status only moves forward; a retraction is final
        for k in ("status", "confirmed_at", "retracted_at", "retract_reason"):
            if k in f:
                old[k] = f[k]
        if f.get("status") == "retracted":
            newly.append(old)
    out = dict(log)
    out["_note"] = ("Every post the every-minute news watch made (api/cron/news-watch.mjs), synced from "
                    "/api/v1/live by sync_live_log.py. Append-only; times are US Eastern with their offset.")
    out["posts"] = sorted(posts.values(), key=lambda p: (p.get("posted_at") or "", p["id"]))
    return out, newly


def correction(p):
    when = (p.get("retracted_at") or "")[:10] or dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()
    src = p.get("source") or {}
    return {"date": when, "page": p.get("page") or "/",
            "was": f"An automatic post said: {p.get('text', '').strip()}",
            "now": f"Retracted. {str(p.get('retract_reason') or '').strip()}".strip(),
            "source": f"{src.get('label', 'source')}, {src.get('url', '')}".strip(", ")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture")
    a = ap.parse_args()
    try:
        if a.fixture:
            feed = json.load(io.open(a.fixture, encoding="utf-8"))
        else:
            with urllib.request.urlopen(urllib.request.Request(FEED, headers=UA), timeout=30) as r:
                feed = json.loads(r.read().decode("utf-8", "replace"))
        posts = feed["data"]
    except Exception as e:  # noqa: BLE001
        print(f"live log: the feed could not be read ({type(e).__name__}); nothing changed")
        print("::warning::the every-minute news watch's feed could not be read; check live:state and live:control")
        return 0
    beat = (((feed.get("meta") or {}).get("watch") or {}).get("last_heartbeat")) or ""
    try:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(beat)).total_seconds() / 60
    except ValueError:
        age = None
    if age is None or age > 15:
        print(f"::warning::the every-minute news watch has no heartbeat in the last 15 minutes (last: {beat or 'none'})")
    log = json.load(io.open(LOG, encoding="utf-8")) if os.path.exists(LOG) else {"posts": []}
    new, newly = merge(log, posts)
    if new != log:
        io.open(LOG, "w", encoding="utf-8", newline="\n").write(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    if newly:
        corr = json.load(io.open(CORR, encoding="utf-8"))
        have = {(e.get("page"), e.get("was")) for e in corr.get("entries") or []}
        for p in newly:
            e = correction(p)
            if (e["page"], e["was"]) not in have:
                corr.setdefault("entries", []).append(e)
        io.open(CORR, "w", encoding="utf-8", newline="\n").write(json.dumps(corr, indent=1, ensure_ascii=False) + "\n")
    n = {s: sum(1 for p in new["posts"] if p.get("status") == s) for s in ("posted", "confirmed", "retracted")}
    print(f"live log: {len(new['posts'])} post(s): {n['posted']} awaiting review, {n['confirmed']} confirmed, "
          f"{n['retracted']} retracted ({len(newly)} newly, each with a /corrections entry)")
    w = (feed.get("meta") or {}).get("watch") or {}
    print(f"   watch heartbeat {w.get('last_heartbeat')}; posting {'on' if w.get('posting') else 'OFF'}; sources {w.get('sources')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
