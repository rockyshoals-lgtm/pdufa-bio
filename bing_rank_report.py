# -*- coding: utf-8 -*-
"""bing_rank_report.py -- track Bing separately, because Search Console was hiding a top-3 position.

We are #3 on Bing for the head query and had no idea, because every measurement we take comes from
Google Search Console. That is not a small blind spot. It means the channel where we are actually
winning is the one channel we never look at, so we cannot tell which pages are working, we cannot
tell when we move, and we cannot tell if a change helped or hurt.

Bing Webmaster Tools exposes this over a JSON API, and unlike Google's it gives average position
per query directly. This pulls it, stores a dated snapshot, and reports movement against the last
one.

What it reports, in the order that matters:

  * STRIKING DISTANCE. Queries ranking 2-10. These are worth more attention than anything ranking
    30th, because the distance from 4 to 1 is a page edit and the distance from 34 to 1 is a
    different site. This is the list to work from.
  * MOVEMENT since the previous snapshot, so a change can be attributed to a deploy.
  * Everything with impressions but no clicks, which usually means we rank but the snippet is not
    answering the question.

Setup is owner-only and takes about two minutes: Bing Webmaster Tools -> Settings -> API Access ->
generate an API key, then set BING_WEBMASTER_API_KEY. Without it this prints what to do and exits
zero, so it never breaks a build.

    python bing_rank_report.py [--site https://www.pdufa.bio] [--json]
"""
import argparse, datetime as dt, json, os, re, sys, urllib.error, urllib.parse, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "_bing_rank_history.json")
BASE = "https://ssl.bing.com/webmaster/api.svc/json"
SITE = "https://www.pdufa.bio"


def call(method, key, site, timeout=45):
    url = f"{BASE}/{method}?" + urllib.parse.urlencode({"apikey": key, "siteUrl": site})
    req = urllib.request.Request(url, headers={"User-Agent": "pdufa.bio/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace")).get("d")


def wcf_date(v):
    """These endpoints return .NET epoch strings like /Date(1754524800000)/."""
    m = re.search(r"/Date\((-?\d+)", str(v or ""))
    if not m:
        return str(v or "")
    return dt.datetime.utcfromtimestamp(int(m.group(1)) / 1000).strftime("%Y-%m-%d")


def load_history():
    try:
        return json.load(open(HISTORY, encoding="utf-8"))
    except Exception:
        return {"snapshots": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--json", action="store_true", help="print the snapshot as JSON")
    a = ap.parse_args()

    key = os.environ.get("BING_WEBMASTER_API_KEY", "").strip()
    if not key:
        print("Bing Webmaster API: NOT CONFIGURED.")
        print("  We rank #3 on Bing and currently measure only Google, so every Bing gain is")
        print("  invisible to us. To fix, once: Bing Webmaster Tools -> Settings -> API Access ->")
        print("  generate an API key, then set BING_WEBMASTER_API_KEY (repo secret for CI).")
        print("  Exiting 0 so this never blocks a build.")
        return 0

    try:
        queries = call("GetQueryStats", key, a.site) or []
    except urllib.error.HTTPError as e:
        hint = {401: "key rejected", 403: "key lacks access to this site",
                400: "siteUrl must match the property exactly, including https:// and www"}
        print(f"  Bing API: HTTP {e.code} ({hint.get(e.code, e.reason)}). No data pulled.")
        return 0
    except Exception as e:
        print(f"  Bing API unreachable ({type(e).__name__}). No data pulled.")
        return 0

    rows = []
    for q in queries:
        rows.append({
            "query": q.get("Query"),
            "impressions": int(q.get("Impressions") or 0),
            "clicks": int(q.get("Clicks") or 0),
            # AvgImpressionPosition is the ranking figure; AvgClickPosition only counts positions
            # that were actually clicked, which flatters us and is not what we want to track.
            "position": round(float(q.get("AvgImpressionPosition") or 0), 1),
            "date": wcf_date(q.get("Date")),
        })
    rows.sort(key=lambda r: -r["impressions"])

    hist = load_history()
    prev = hist["snapshots"][-1] if hist["snapshots"] else None
    prev_pos = {r["query"]: r["position"] for r in (prev or {}).get("rows", [])}

    today = dt.date.today().isoformat()
    hist["snapshots"] = [s for s in hist["snapshots"] if s.get("date") != today]
    hist["snapshots"].append({"date": today, "site": a.site, "rows": rows})
    hist["snapshots"] = hist["snapshots"][-180:]
    json.dump(hist, open(HISTORY, "w", encoding="utf-8"), indent=1)

    if a.json:
        print(json.dumps(rows, indent=1)); return 0

    tot_i = sum(r["impressions"] for r in rows)
    tot_c = sum(r["clicks"] for r in rows)
    print(f"Bing: {len(rows)} queries, {tot_i:,} impressions, {tot_c:,} clicks"
          + (f" (vs {sum(r['impressions'] for r in prev['rows']):,} impressions on {prev['date']})"
             if prev else " (first snapshot)"))

    def delta(r):
        p = prev_pos.get(r["query"])
        if p is None:
            return "  new"
        d = p - r["position"]                      # positive = moved up the page
        return "   ==" if abs(d) < 0.1 else f"{d:+5.1f}"

    strike = [r for r in rows if 1.5 <= r["position"] <= 10][:20]
    if strike:
        print("\nSTRIKING DISTANCE (positions 2-10; a page edit can win these)")
        print(f"  {'pos':>5} {'move':>5} {'impr':>7} {'clicks':>7}  query")
        for r in strike:
            print(f"  {r['position']:>5} {delta(r):>5} {r['impressions']:>7,} "
                  f"{r['clicks']:>7,}  {r['query']}")

    top = [r for r in rows if r["position"] < 1.5][:10]
    if top:
        print("\nALREADY #1")
        for r in top:
            print(f"  {r['position']:>5} {r['impressions']:>7,} impr  {r['query']}")

    dead = [r for r in rows if r["impressions"] >= 25 and r["clicks"] == 0][:12]
    if dead:
        print("\nIMPRESSIONS BUT NO CLICKS (we rank; the snippet is not answering)")
        for r in dead:
            print(f"  pos {r['position']:>5} {r['impressions']:>7,} impr  {r['query']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
