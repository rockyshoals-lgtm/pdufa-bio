# -*- coding: utf-8 -*-
"""watch_sponsor_newswire.py -- the fourth pass: sponsors' own news feeds, for every armed PDUFA.

Audit 2026-09-26 item 6 (task #48). Three approvals reached the site days late this month:
TLX Pixclara (Telix announcement Sep 14, on site Sep 19), NUVB IBTROZI sNDA (Nuvation release
Sep 16, on site Sep 23), MIRM/INCY Atebrioz (release Sep 25, still "under review" on the 26th).
The three existing passes read Drugs@FDA, the FDA press feed and EDGAR 8-K/6-K text, all of
which trail the sponsor's own release (a label supplement produces no 8-K at all).

This pass reads each armed sponsor's OWN news-release RSS feed -- most Nasdaq/Q4/Drupal investor
sites publish one (investor.incyte.com/rss/news-releases.xml carried Atebrioz within the hour) --
and raises a LEAD when an item names an armed drug together with an FDA decision word. A lead is
never published automatically: verify against the release / FDA, then publish the decision page
(house rule: verify-then-publish). Reviewed non-events go in _newswire_ack.json.

ARMED = every Upcoming PDUFA row, from the day it enters the dataset (i.e. from acceptance), plus
rows whose goal date has passed undecided. A weekend goal date is armed like any other; since
every run reads every armed sponsor, "arm from the Wednesday before" is automatically satisfied.

Feeds: _sponsor_feeds.json {TICKER: {"feeds": [...], "checked": date}}. `--discover` tries the
common IR feed paths on candidate IR hosts for tickers without a working feed and records the
result (hosts that 404 are retried after 14 days). Coverage is printed every run -- a ticker with
no feed is still covered by the three other passes, and the report says which ones are thin.

Google News RSS was tested and rejected: its feed terms forbid anything but personal use.

    python watch_sponsor_newswire.py [--discover] [--dry-run]
Exit 1 when there is an unreviewed lead (same contract as watch_fda_approvals.py).
"""
import argparse
import datetime as dt
import email.utils
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
FEEDS = os.path.join(HERE, "_sponsor_feeds.json")
ACK = os.path.join(HERE, "_newswire_ack.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; pdufa.bio builder; +https://www.pdufa.bio/about)"}
DECISION = re.compile(r"\b(FDA|Food and Drug Administration)\b.{0,160}?\b(approv\w*|complete response|CRL|"
                      r"accelerated approval|clearance)\b|\b(approv\w*|complete response letter)\b.{0,160}?"
                      r"\b(FDA|Food and Drug Administration)\b", re.I | re.S)
RSS_PATHS = ("/rss/news-releases.xml", "/news-releases/rss", "/rss/news-releases", "/rss/pressrelease.aspx",
             "/news-releases/feed", "/feed/PressRelease.svc/GetPressReleaseList?format=rss")
STOP = {"TABLETS", "TABLET", "INJECTION", "CAPSULES", "ORAL", "SNDA", "SBLA", "NDA", "BLA", "WITH", "AND",
        "FOR", "THE", "PLUS", "LOWER", "DOSES", "DOSE", "PHASE", "TRIAL", "STUDY", "THERAPY", "LABEL",
        "UPDATE", "RESUBMISSION", "PEDIATRIC", "PAEDIATRIC", "ADULTS", "CHILDREN", "COMBINATION"}


def eastern_today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=4)).date()


def terms_for(r):
    d = r.get("_d") or {}
    out = []
    def add(s):
        for w in re.split(r"[^A-Za-z0-9\-]+", str(s or "")):
            w = w.strip("-")
            if len(w) >= 5 and w.upper() not in STOP and w.lower() not in (x.lower() for x in out):
                out.append(w)
    add(d.get("brand"))
    name = str(r.get("name") or "")
    add(re.split(r"[(;,]| - ", name)[0])
    for inner in re.findall(r"\(([^)]*)\)", name):
        add(inner)
    return out[:6]


def armed_rows(rows, today):
    out = []
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        st = str(r.get("st", "")).lower()
        if st == "upcoming":
            out.append(r)
    return out


def match(item_text, rows_for_ticker):
    """[(row, term)] for rows named in an item that also carries an FDA decision phrase."""
    # The DECISION must be in the headline (sponsors headline an approval or a CRL); body text of
    # acceptance and readout releases routinely says "if approved" / "potential approval".
    title = item_text.split("\n", 1)[0]
    if not DECISION.search(title) or re.search(r"\b(if approved|potential(ly)? approv\w*|seek\w* approval|"
                                               r"accept(s|ed|ance)|submi(ts|tted|ssion))\b", title, re.I) \
            and not re.search(r"\b(approves|approved|approval of|grants?|complete response)\b", title, re.I):
        return []
    hits = []
    for r in rows_for_ticker:
        for t in terms_for(r):
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", item_text, re.I):
                hits.append((r, t))
                break
    return hits


def fetch(url, timeout=20):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read(2_000_000).decode("utf-8", "replace")
    except Exception:
        return None


def parse_items(xml):
    items = []
    for m in re.finditer(r"<(item|entry)\b.*?</\1>", xml or "", re.S | re.I):
        blk = m.group(0)
        def tag(n):
            mm = re.search(rf"<{n}\b[^>]*>(.*?)</{n}>", blk, re.S | re.I)
            v = mm.group(1) if mm else ""
            v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", v, flags=re.S)
            return html.unescape(re.sub(r"<[^>]+>", " ", v)).strip()
        link = tag("link") or (re.search(r'<link[^>]+href="([^"]+)"', blk) or [None, ""])[1]
        pub = tag("pubDate") or tag("published") or tag("updated") or tag("dc:date")
        try:
            when = email.utils.parsedate_to_datetime(pub).date() if pub and not re.match(r"^\d{4}-", pub) \
                else dt.date.fromisoformat(pub[:10]) if pub else None
        except Exception:
            when = None
        items.append({"title": tag("title"), "desc": tag("description") or tag("summary"), "link": link.strip(),
                      "date": when})
    return items


def candidate_hosts(company):
    base = re.sub(r"\b(inc|corp|corporation|co|ltd|limited|plc|ag|sa|nv|n\.v|se|holdings?|group|the|pharmaceuticals?|"
                  r"therapeutics|biosciences?|biotherapeutics|biopharma|bio|medical|laboratories|incorporated|company)\b\.?",
                  " ", str(company or "").lower())
    words = [w for w in re.split(r"[^a-z0-9]+", base) if w]
    if not words:
        return []
    slugs = {words[0], "".join(words[:2])} if len(words) > 1 else {words[0]}
    hosts = []
    for s in slugs:
        for pre in ("investors.", "investor.", "ir."):
            for tld in (".com",):
                hosts.append(f"https://{pre}{s}{tld}")
    return hosts


def discover(ticker, company, known_hosts):
    """Try every (host, path) candidate in parallel with a short timeout; first working feed wins.
    (The sequential first version took over 25 minutes for 33 tickers -- dead hosts time out.)"""
    from concurrent.futures import ThreadPoolExecutor
    urls = [h + pth for h in list(known_hosts) + candidate_hosts(company) for pth in RSS_PATHS]
    def ok(u):
        xml = fetch(u, timeout=6)
        return u if xml and re.search(r"<(rss|feed)\b", xml[:600], re.I) and parse_items(xml) else None
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(ok, urls):
            if res:
                return res
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--window", type=int, default=10, help="days of feed history to read")
    a = ap.parse_args()
    today = eastern_today()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    feeds = json.load(io.open(FEEDS, encoding="utf-8")) if os.path.exists(FEEDS) else {}
    ack = json.load(io.open(ACK, encoding="utf-8")).get("acked", []) if os.path.exists(ACK) else []
    armed = armed_rows(rows, today)
    by_tk = {}
    for r in armed:
        by_tk.setdefault(str(r["t"]).upper(), []).append(r)

    if a.discover:
        for tk, rs in sorted(by_tk.items()):
            ent = feeds.get(tk) or {}
            if ent.get("feeds") or (ent.get("checked", "") >= (today - dt.timedelta(days=14)).isoformat()):
                continue
            hosts = set()
            for r in rs:
                for u in ((r.get("_d") or {}).get("source_url"), (r.get("_d") or {}).get("announcement_url")):
                    m = re.match(r"(https://[^/]+)", str(u or ""))
                    if m and not re.search(r"sec\.gov|fda\.gov|businesswire|globenewswire|prnewswire|biospace", m.group(1)):
                        hosts.add(m.group(1))
            f = discover(tk, rs[0].get("company"), hosts)
            feeds[tk] = {"feeds": [f] if f else [], "checked": today.isoformat(), "company": rs[0].get("company")}
            print(f"  discover {tk:<6} {f or '-- no feed found'}", flush=True)
            if not a.dry_run:
                io.open(FEEDS, "w", encoding="utf-8", newline="\n").write(json.dumps(feeds, indent=1, sort_keys=True) + "\n")
        if not a.dry_run:
            io.open(FEEDS, "w", encoding="utf-8", newline="\n").write(json.dumps(feeds, indent=1, sort_keys=True) + "\n")

    leads, covered, read_ok = [], [], 0
    since = today - dt.timedelta(days=a.window)
    for tk, rs in sorted(by_tk.items()):
        urls = (feeds.get(tk) or {}).get("feeds") or []
        if not urls:
            continue
        covered.append(tk)
        for u in urls:
            xml = fetch(u)
            if not xml:
                print(f"  {tk}: feed unreachable this run ({u})")
                continue
            read_ok += 1
            for it in parse_items(xml):
                if it["date"] and it["date"] < since:
                    continue
                for r, term in match(it["title"] + " \n " + it["desc"], rs):
                    key = f"{r['id']}|{it['link'] or it['title'][:80]}"
                    if key in ack:
                        continue
                    leads.append((r, term, it, key))
    print(f"sponsor-feed watch: {len(by_tk)} armed sponsor(s); {len(covered)} with a news feed "
          f"({read_ok} read this run); no feed yet: {', '.join(t for t in sorted(by_tk) if t not in covered) or 'none'}")
    if leads:
        print(f"SPONSOR-FEED WATCH: {len(leads)} unreviewed lead(s) on armed events:")
        for r, term, it, key in leads:
            print(f"   {r['t']} {r['name'][:50]} (goal {r['d']}): {it['date']} \"{it['title'][:120]}\" "
                  f"[matched '{term}'] {it['link']}")
        print("\n   Each is a LEAD, not a fact: verify against the release and the FDA, publish the decision "
              "page, and ack non-events in _newswire_ack.json (key printed below).")
        for *_x, key in leads:
            print(f"   ack key: {key}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
