# -*- coding: utf-8 -*-
"""watch_fda_drugs_feed.py -- the FDA's own "What's New: Drugs" feed, for every armed PDUFA.

Audit 2026-09-27 item 1. Atebrioz (zilurgisertib) was posted by the FDA on CDER's "News & Events
for Human Drugs" at 2:46 PM ET on Friday 2026-09-25 -- four hours before Mirum/Incyte's 7:00 PM
release -- and reached pdufa.bio about 34 hours later. The existing FDA pass reads the agency's
PRESS-ANNOUNCEMENTS feed, and CDER's approval notices ("FDA Approves Third Treatment for
Fibrodysplasia Ossificans Progressiva") are not press announcements. They are items on
CDER's "What's New: Drugs" RSS (linked from the News & Events page as "RSS Feed for What's New"):

    https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml

This pass reads that feed, and raises a LEAD when an item headlined as an FDA decision names an
armed drug (brand or INN) in its title or summary -- the summary is where the drug is named
("FDA has approved Atebrioz (zilurgisertib) tablets ..."). Same contract as the other watchers:
a lead BLOCKS the rebuild until someone verifies and publishes it, or acks it in
_fda_drugs_feed_ack.json with a reason. Never publishes by itself.

It also prints, without blocking, FDA approval notices that name NO tracked drug (09-25: Gazyva for
idiopathic nephrotic syndrome) -- the list of what the calendar does not cover.

Network failure / an FDA 401 (the agency intermittently refuses non-browser clients) is reported and
is NOT a lead: exit 0, the other passes still run.

    python watch_fda_drugs_feed.py [--feed FILE_OR_URL] [--since YYYY-MM-DD]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watch_sponsor_newswire as W  # noqa: E402  (one matcher, one set of decision words)

FEED = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml"
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_fda_drugs_feed_ack.json")
UA = {"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}


def load_feed(src):
    if re.match(r"^https?://", src):
        try:
            with urllib.request.urlopen(urllib.request.Request(src, headers=UA), timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"FDA drugs feed: unreachable this run ({e}); not a lead, other passes still run")
            return None
    return io.open(src, encoding="utf-8").read()


def leads_from(xml, rows, since=None, acked=()):
    armed = [r for r in rows if r.get("type") == "PDUFA" and str(r.get("st", "")).lower() == "upcoming"]
    leads, untracked = [], []
    for it in W.parse_items(xml):
        if since and it["date"] and it["date"] < since:
            continue
        text = it["title"] + " \n " + it["desc"]
        hits = W.match(text, armed)
        if hits:
            for r, term in hits:
                key = f"{r['id']}|{it['link']}"
                if key not in acked:
                    leads.append((r, term, it, key))
        elif re.search(r"\bFDA (Approves|Grants)\b", it["title"]):
            untracked.append(it)
    return leads, untracked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=FEED)
    ap.add_argument("--since", help="ignore items before this date (default: 14 days ago)")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    acked = set(json.load(io.open(ACK, encoding="utf-8")).get("acked", [])) if os.path.exists(ACK) else set()
    since = dt.date.fromisoformat(a.since) if a.since else dt.date.today() - dt.timedelta(days=14)
    xml = load_feed(a.feed)
    # Feed health (2026-09-27): fda.gov answered 401 to every non-browser client we tried this
    # weekend, CI included -- and the existing press-feed pass had been reporting "0 press items
    # scanned" without saying why. Record the last good read so blindness is visible, not silent.
    hp = os.path.join(HERE, "_watch_health.json")
    health = json.load(io.open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
    ent = health.setdefault("fda_drugs_whatsnew", {})
    ent["last_attempt"] = dt.date.today().isoformat()
    if xml is not None and a.feed == FEED:
        ent["last_ok"] = dt.date.today().isoformat()
    if a.feed == FEED:
        io.open(hp, "w", encoding="utf-8", newline="\n").write(json.dumps(health, indent=1, sort_keys=True) + "\n")
    if xml is None:
        print(f"   BLIND: last successful read of the FDA drugs feed: {ent.get('last_ok') or 'never'}")
        return 0
    leads, untracked = leads_from(xml, rows, since, acked)
    n = len(W.parse_items(xml))
    print(f"FDA drugs feed: {n} item(s) read; {len(leads)} unreviewed lead(s) on armed events; "
          f"{len(untracked)} FDA approval notice(s) naming no tracked drug")
    for it in untracked:
        print(f"   untracked: {it['date']} {it['title'][:90]} -- {it['desc'][:110]}")
    if leads:
        print("FDA DRUGS-FEED WATCH: the FDA has posted a decision on armed event(s):")
        for r, term, it, key in leads:
            print(f"   {r['t']} {str(r.get('name'))[:50]} (goal {r['d']}): \"{it['title'][:100]}\" "
                  f"[{term}] {it['link']}\n      ack key: {key}")
            W._emit_lead("fda_drugs_feed", r["id"], key, f"{it['date']} \"{it['title'][:160]}\" [{term}] {it['link']}")
        print("   Each is a LEAD: read the FDA notice, publish the decision page (the FDA notice is the "
              "primary source), or ack in _fda_drugs_feed_ack.json with a reason.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
