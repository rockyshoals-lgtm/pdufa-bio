# -*- coding: utf-8 -*-
"""CI guard: the Atom feeds (build_feeds.py) are valid, current and say only what their pages say.

  * /feed/decisions.xml and /feed/crl.xml parse as Atom: feed id, title, updated, self link; every entry has a unique
    id, a title, published and updated times (no later than tomorrow), an alternate link and a summary.
  * Every decision entry links an indexable /fda-decision page whose outcome the FDA or the sponsor stated (no
    "Unconfirmed", price-only page), and the newest decision page by first-commit time is in the feed.
  * Every goal-date change on /pdufa-date-changes is in the decisions feed.
  * Every CRL entry is a Complete Response Letter of the release: its related link is the FDA's PDF on
    download.open.fda.gov/crl/, and its count on /feed matches the feed builder's count.
  * Every internal link resolves to a page in the build; the hubs carry <link rel="alternate"> to their feed.
  * Every decision entry's page is "sourced" by the same reading as /decisions, and the entry names its sources.
  * No forecast words (probability, odds, chance, likely, predict, forecast) in any entry: facts only.
  * /feed states the counts the builder finds, and vercel.json sends no redirect from /feed.

PLANT=1 adds a price-only decision entry to the feed text and must FAIL.

    python tests/test_feeds.py      (fix: python build_feeds.py)
"""
import datetime as dt
import glob
import io
import os
import re
import sys
import xml.etree.ElementTree as ET_

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
A = "{http://www.w3.org/2005/Atom}"
BASE = "https://www.pdufa.bio"


def page_path(url):
    p = url.replace(BASE, "").split("#")[0].strip("/")
    for c in (os.path.join(SITE, p, "index.html"), os.path.join(SITE, p), os.path.join(SITE, p + ".html")):
        if os.path.isfile(c):
            return c
    return None


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    fails = []
    feeds = {}
    for name in ("decisions", "crl"):
        p = os.path.join(SITE, "feed", f"{name}.xml")
        if not os.path.exists(p):
            fails.append(f"/feed/{name}.xml missing")
            continue
        raw = io.open(p, encoding="utf-8").read()
        if os.environ.get("PLANT") and name == "decisions":
            bad = next((os.path.basename(os.path.dirname(q)) for q in glob.glob(os.path.join(SITE, "fda-decision", "*",
                        "index.html")) if "Unconfirmed" in io.open(q, encoding="utf-8", errors="replace").read()), "x")
            raw = raw.replace("</feed>", f'<entry><id>{BASE}/fda-decision/{bad}</id><title>t</title><link rel="alternate" '
                              f'href="{BASE}/fda-decision/{bad}"/><published>2026-01-01T00:00:00Z</published><updated>'
                              f'2026-01-01T00:00:00Z</updated><summary>s</summary></entry></feed>')
        try:
            root = ET_.fromstring(raw.encode("utf-8"))
        except ET_.ParseError as e:
            fails.append(f"/feed/{name}.xml is not well-formed XML: {e}")
            continue
        feeds[name] = root
        if root.tag != A + "feed":
            fails.append(f"/feed/{name}.xml root is not an Atom feed")
        for t in ("id", "title", "updated"):
            if root.find(A + t) is None or not (root.find(A + t).text or "").strip():
                fails.append(f"/feed/{name}.xml has no <{t}>")
        if not any(l.get("rel") == "self" for l in root.findall(A + "link")):
            fails.append(f"/feed/{name}.xml has no self link")
        ents = root.findall(A + "entry")
        if not ents:
            fails.append(f"/feed/{name}.xml has no entries")
        ids = [(e.find(A + "id").text if e.find(A + "id") is not None else None) for e in ents]
        if len(set(ids)) != len(ids) or None in ids:
            fails.append(f"/feed/{name}.xml: entry ids missing or repeated")
        tomorrow = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        for e in ents:
            eid = e.find(A + "id").text
            for t in ("title", "published", "updated", "summary"):
                if e.find(A + t) is None or e.find(A + t).text is None:
                    fails.append(f"{name}: {eid} has no <{t}>")
            try:
                if ts(e.find(A + "updated").text) > tomorrow or ts(e.find(A + "published").text) > tomorrow:
                    fails.append(f"{name}: {eid} is dated in the future")
            except Exception:
                fails.append(f"{name}: {eid} has an unreadable time")
            alt = [l.get("href") for l in e.findall(A + "link") if l.get("rel") == "alternate"]
            if not alt or not alt[0].startswith(BASE) or not page_path(alt[0]):
                fails.append(f"{name}: {eid} links {alt[:1]}, not a page in the build")
            body = " ".join((e.find(A + t).text or "") for t in ("title", "summary", "content") if e.find(A + t) is not None)
            if re.search(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast)", body, re.I):
                fails.append(f"{name}: {eid} carries a forecast word")
            if name == "decisions" and alt and "/fda-decision/" in alt[0] and page_path(alt[0]):
                doc = io.open(page_path(alt[0]), encoding="utf-8", errors="replace").read()
                oc = re.search(r'<span>Outcome</span><b[^>]*>(.*?)</b>', doc)
                if not oc or "Unconfirmed" in oc.group(1) or "price-only" in oc.group(1):
                    fails.append(f"decisions: {eid} is a page whose outcome is not stated by the FDA or the sponsor")
                if re.search(r'<meta name="robots" content="[^"]*noindex', doc):
                    fails.append(f"decisions: {eid} is a noindex page")
                from refresh_provenance_counts import page_kind
                if page_kind(doc) != "sourced":
                    fails.append(f"decisions: {eid} is not a sourced page")
                if "Sources:" not in ((e.find(A + "content").text or "") if e.find(A + "content") is not None else ""):
                    fails.append(f"decisions: {eid} names no source")
            if name == "crl":
                rel = [l.get("href") for l in e.findall(A + "link") if l.get("rel") == "related"]
                if rel and not rel[0].startswith("https://download.open.fda.gov/crl/"):
                    fails.append(f"crl: {eid} related link is not the FDA's PDF")
                if "Complete Response Letter" not in (e.find(A + "title").text or ""):
                    fails.append(f"crl: {eid} is not titled as a Complete Response Letter")

    if "decisions" in feeds:
        import build_feeds as F
        import build_date_changes as D
        ids = {e.find(A + "id").text for e in feeds["decisions"].findall(A + "entry")}
        for c in D.collect_changes():
            if f"tag:pdufa.bio,2026:pdufa-date-change/{c['t']}/{c['prior']}/{c['now']}" not in ids:
                fails.append(f"decisions feed lacks the {c['t']} goal-date change {c['prior']} -> {c['now']}")
        dec, n_dec, n_ch = F.decision_entries()
        want = next((x["id"] for x in dec if x["cat"] != "PDUFA goal date change"), None)
        if want and want not in ids:
            fails.append(f"decisions feed lacks the newest decision page {want} (stale; fix: python build_feeds.py)")
        pg = os.path.join(SITE, "feed", "index.html")
        doc = io.open(pg, encoding="utf-8").read() if os.path.exists(pg) else ""
        for k, v in (("n_dec", n_dec), ("n_ch", n_ch)):
            if f'<span data-feed="{k}">{v}</span>' not in doc:
                fails.append(f"/feed states another {k} than the {v} the builder finds")
    if "crl" in feeds:
        import build_feeds as F
        live, _, n_resc = F.crl_letters()
        pg = os.path.join(SITE, "feed", "index.html")
        doc = io.open(pg, encoding="utf-8").read() if os.path.exists(pg) else ""
        for k, v in (("n_crl", len(live)), ("n_crl_all", len(live) + n_resc), ("n_resc", n_resc)):
            if f'<span data-feed="{k}">{v}</span>' not in doc:
                fails.append(f"/feed states another {k} than the {v} in the release")
    vj = os.path.join(SITE, "vercel.json")
    if os.path.exists(vj):
        import json
        for r in json.load(io.open(vj, encoding="utf-8")).get("redirects", []):
            if str(r.get("source", "")).rstrip("/") in ("/feed", "/feed/decisions.xml", "/feed/crl.xml"):
                fails.append(f"vercel.json redirects {r.get('source')} to {r.get('destination')}; /feed is a page")
    for rel, names in __import__("build_feeds").ALTS.items():
        p = os.path.join(SITE, rel)
        if os.path.exists(p):
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            for n in names:
                if f'type="application/atom+xml"' not in doc or f"/feed/{n}.xml" not in doc:
                    fails.append(f"/{rel.replace('index.html', '')} has no alternate link to /feed/{n}.xml")
    if fails:
        print(f"FAIL test_feeds: {len(fails)} problem(s); fix: python build_feeds.py")
        for f in fails[:25]:
            print("  " + f)
        return 1
    print(f"PASS test_feeds: decisions {len(feeds['decisions'].findall(A + 'entry'))} entries, "
          f"crl {len(feeds['crl'].findall(A + 'entry'))} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
