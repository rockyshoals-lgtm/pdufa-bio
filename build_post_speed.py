# -*- coding: utf-8 -*-
"""build_post_speed.py -- "Posted N min after the source": how fast pdufa.bio published each catalyst, to the minute.

David (2026-11-27): show how fast each catalyst was posted, down to the minute; 100% accurate, red-teamed, never a
claim of "first" or "fastest". Two times per catalyst event, both checkable by anyone:

  source time   when the catalyst's primary source was published, read on the primary page itself and recorded in
                _source_times.json: a newswire page's printed time, the sec.gov filing index's "Accepted" time
                (EDGAR prints Eastern time), or an FDA RSS item's pubDate with its zone. Never guessed, never
                inferred from a date (RULE 1: every time carries its own offset).
  site time     when the fact landed on pdufa.bio: the first-parent commit on main of the public repository that
                first carried it (the decision's outcome, or the moved goal date), from _row_history.json, with the
                commit's own timestamp in seconds read from git. Pushes to main deploy the site. Cached append-only in
                _post_speed.json so CI's shallow clone never recomputes it; an entry is never moved.

The reference is the EARLIEST verified source time of the event, so a gap is never shorter than it was measured
against any source we timed. An event gets no stamp when an earlier disclosure exists that prints no time
("earlier_untimed"), when no site time can be read to the second, or when the gap is not positive.

Writes, idempotently:
  * a marker-bounded stamp (POSTSPEED) on the event page (/fda-decision/<slug> after the first-recorded line;
    /pdufa/<slug> after the moved-date note) and a one-line entry per stamped event on the /drug page(s) linking
    the event (POSTSPEEDDRUG, before the related block);
  * a JSON-LD block (POSTSPEEDLD) on the event page: the source's datePublished and ours;
  * /research/posting-speed, every stamped event with both times and the gap, and the timed events left out with
    the reason; /api/v1/post-speed (post_speed_data.mjs).
Corrections: a source time that changes needs a dated _corrections.json entry naming the event page
(tests/test_post_speed.py). Facts only; not investment advice.

    python build_post_speed.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
import html
import io
import json
import os
import re
import statistics
import subprocess
import sys
from zoneinfo import ZoneInfo

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
SOURCES = os.path.join(HERE, "_source_times.json")
CACHE = os.path.join(HERE, "_post_speed.json")
ROWHIST = os.path.join(HERE, "_row_history.json")
API_DATA = os.path.join(SITE, "api", "v1", "post_speed_data.mjs")
PAGE_REL = "research/posting-speed"
PAGE_URL = "https://www.pdufa.bio/" + PAGE_REL
REPO = "https://github.com/rockyshoals-lgtm/pdufa-bio/commit/"
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
B, E = "<!--POSTSPEED:BEGIN-->", "<!--POSTSPEED:END-->"
LB, LE = "<!--POSTSPEEDLD:BEGIN-->", "<!--POSTSPEEDLD:END-->"
DB, DE = "<!--POSTSPEEDDRUG:BEGIN-->", "<!--POSTSPEEDDRUG:END-->"
ISO_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?([+-]\d\d:\d\d)$")


def esc(s):
    return html.escape(str(s), quote=True)


def load_rows():
    s = io.open(DATASET, encoding="utf-8", errors="replace").read()
    return {r["id"]: r for r in json.loads(s[s.index("["):s.rindex("]") + 1]) if isinstance(r, dict) and r.get("id")}


def parse_iso(s):
    """A time with its own numeric offset, or None. A time without an offset is refused (RULE 1)."""
    if not isinstance(s, str) or not ISO_RE.match(s):
        return None
    return dt.datetime.fromisoformat(s)


def git_time(sha):
    try:
        r = subprocess.run(["git", "show", "-s", "--format=%cI", sha], cwd=HERE, capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return parse_iso(r.stdout.strip()) if r.returncode == 0 else None


def landing_change(ev, changes):
    """The _row_history entry for the first-parent commit that first published this event's fact."""
    rid = ev["row"]
    for c in changes:                              # the ledger is in commit order
        if c.get("id") != rid:
            continue
        if ev["kind"] == "decision":
            if c["field"] == "oc" and c.get("new"):
                return c
            if c["field"] == "row" and c.get("new") == "entered" and c.get("st_now") == "Decided":
                return c
        elif ev["kind"] == "date_change":
            if c["field"] == "d" and c.get("new") == ev.get("new_date"):
                return c
    return None


def dur(minutes):
    """Whole minutes, floored by the caller, as a reader says it."""
    m = int(minutes)
    if m < 60:
        return f"{m} min"
    h, mm = divmod(m, 60)
    if h < 48:
        return f"{h} h {mm} min" if mm else f"{h} h"
    d, hh = divmod(h, 24)
    return f"{d} d {hh} h" if hh else f"{d} d"


def clock(t):
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def fmt_et(t):
    e = t.astimezone(ET)
    return f"{MON[e.month - 1]} {e.day}, {e.year}, {clock(e)} ET"


def fmt_utc(t, ref):
    u = t.astimezone(UTC)
    day = "" if u.date() == ref.astimezone(ET).date() else f", {MON[u.month - 1]} {u.day}"
    return f"{u.hour:02d}:{u.minute:02d} UTC{day}"


def floor_minutes(a, b):
    return int((b - a).total_seconds() // 60)


def compute(rows, src_led, cache, changes, now_iso):
    """[(event_key, record)] for every timed event, stamped or not, plus the cache additions."""
    out, added = [], 0
    for key, ev in sorted((src_led.get("events") or {}).items()):
        r = rows.get(ev.get("row"))
        rec = {"key": key, "row": ev.get("row"), "kind": ev.get("kind"), "event": ev.get("event")}
        srcs = []
        for s in ev.get("sources") or []:
            t = parse_iso(s.get("at"))
            if t and s.get("url", "").startswith("https://") and s.get("label"):
                srcs.append((t, s))
        if not r:
            rec["skip"] = "the row is no longer in the dataset"
        elif not srcs:
            rec["skip"] = "no verified source time"
        if "skip" not in rec:
            ref_t, ref = min(srcs, key=lambda x: x[0])
            rec.update({"t": r.get("t"), "name": r.get("name"), "page": r.get("url") if ev["kind"] == "decision"
                        else (r.get("url") or ""), "source": ref, "source_at": ref_t})
            if ev.get("earlier_untimed"):
                rec["skip"] = ev["earlier_untimed"]
        if "skip" not in rec:
            hit = cache.get(key)
            if not hit:
                c = landing_change(ev, changes)
                t = git_time(c["sha"]) if c else None
                if c and t:
                    hit = cache[key] = {"site_at": t.isoformat(), "commit": c["sha"], "cached": now_iso}
                    added += 1
            if not hit:
                rec["skip"] = "the commit that published it could not be read to the second yet"
            else:
                st = parse_iso(hit["site_at"])
                rec.update({"site_at": st, "commit": hit["commit"]})
                gap = floor_minutes(rec["source_at"], st)
                if gap <= 0:
                    rec["skip"] = "pdufa.bio's record came before this source's time"
                else:
                    rec["gap_min"] = gap
        out.append(rec)
    return out, added


def stamp_html(rec):
    s, sa, st = rec["source"], rec["source_at"], rec["site_at"]
    c = rec["commit"]
    return (f'{B}<p class="note" id="posted" style="margin:0 0 10px;font-size:12.5px;color:#a7bcd9">'
            f'<b style="color:#cfe0f5">Posted {esc(dur(rec["gap_min"]))} after the source.</b> '
            f'Source: <a href="{esc(s["url"])}" rel="noopener" style="color:#e3ba5e">{esc(s["label"])}</a>, '
            f'{esc(fmt_et(sa))} ({esc(fmt_utc(sa, sa))}). '
            f'Published on pdufa.bio: {esc(fmt_et(st))} ({esc(fmt_utc(st, st))}), when '
            f'<a href="{REPO}{c}" rel="noopener" style="color:#94a9c9">public commit {c[:7]}</a> reached the branch '
            f'the live site deploys from. '
            f'<a href="/{PAGE_REL}" style="color:#94a9c9">How we time this</a>.</p>{E}')


def what_label(rec):
    """Plain words for the event on a /drug page line."""
    if rec["kind"] == "date_change":
        return "The PDUFA date change"
    ev = rec["event"].split(" (")[0].replace("FDA decision: ", "").strip().lower()
    return {"approved": "The approval", "crl": "The complete response letter",
            "not approvable letter": "The not-approvable letter"}.get(ev, "The FDA decision")


def ld_html(rec, page_url):
    s = rec["source"]
    ld = {"@context": "https://schema.org", "@type": "CreativeWork", "@id": page_url + "#posted",
          "name": f"When pdufa.bio posted this ({dur(rec['gap_min'])} after the source)",
          "url": page_url + "#posted", "datePublished": rec["site_at"].astimezone(ET).isoformat(),
          "publisher": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
          "isBasedOn": {"@type": "CreativeWork", "name": s["label"], "url": s["url"],
                        "datePublished": rec["source_at"].astimezone(ET).isoformat()}}
    return LB + '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>" + LE


def put_block(doc, b, e, block, anchors):
    base = re.sub(re.escape(b) + ".*?" + re.escape(e), "", doc, flags=re.S)
    if not block:
        return base
    for anchor, after in anchors:
        i = base.find(anchor)
        if i >= 0:
            j = i + len(anchor) if after else i
            return base[:j] + block + base[j:]
    return base


def page_path(url):
    if not url or not url.startswith("/") or ".." in url:
        return None
    p = os.path.join(SITE, url.strip("/"), "index.html")
    return p if os.path.exists(p) else None


def write(path, new, old, dry):
    if new != old and not dry:
        io.open(path, "w", encoding="utf-8", newline="").write(new)
    return new != old


def event_pages(stamped, dry):
    """Stamp + JSON-LD on each stamped event's page; remove both from every page no longer stamped."""
    want = {}
    for rec in stamped:
        p = page_path(rec["page"])
        if p:
            want[p] = rec
    n = 0
    for p in sorted(set(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")) +
                        glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B not in doc and LB not in doc and p not in want:
            continue
        rec = want.get(p)
        anchors = [("<!--FIRSTREC:END-->", True), ("<!--VERIFIED:END-->", True), ("<!--DATEMOVE:END-->", True),
                   ("<!--SRC:END-->", True), ("<h2>Key facts</h2>", False)]
        new = put_block(doc, B, E, stamp_html(rec) if rec else "", anchors)
        url = "https://www.pdufa.bio" + rec["page"] if rec else ""
        new = put_block(new, LB, LE, ld_html(rec, url) if rec else "", [("</head>", False)])
        n += write(p, new, doc, dry)
    return n, len(want)


def drug_pages(stamped, dry):
    """One line per stamped event on every /drug page that links the event page."""
    by_page = {rec["page"]: rec for rec in stamped if rec.get("page")}
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        hits = [rec for u, rec in by_page.items() if f'href="{u}"' in doc]
        block = ""
        if hits:
            items, seen = [], set()
            for rec in sorted(hits, key=lambda r: (r["source_at"], r["page"])):
                key = (rec["source"]["url"], rec["commit"], rec["kind"])
                if key in seen:          # co-sponsor rows of one decision (IRD and VTRS) say the same thing once
                    continue
                seen.add(key)
                items.append(f'<a href="{esc(rec["page"])}#posted" style="color:#e3ba5e">{esc(what_label(rec))}</a>: posted '
                             f'{esc(dur(rec["gap_min"]))} after {esc(rec["source"]["label"])} '
                             f'({esc(fmt_et(rec["source_at"]))})')
            block = (f'{DB}<p class="note" style="margin:8px 0;font-size:12.5px;color:#a7bcd9"><b style="color:#cfe0f5">'
                     f'How fast pdufa.bio posted it:</b> ' + " &middot; ".join(items) +
                     f'. <a href="/{PAGE_REL}" style="color:#94a9c9">How we time this</a>.</p>{DE}')
        new = put_block(doc, DB, DE, block, [("<!--RELATED:BEGIN-->", False), ("<!--SITELINKS:BEGIN-->", False)])
        n += write(p, new, doc, dry)
    return n


def api_rows(stamped):
    out = []
    for rec in sorted(stamped, key=lambda r: r["source_at"]):
        s = rec["source"]
        out.append({"id": rec["row"], "ticker": rec["t"], "name": rec["name"], "event": rec["event"],
                    "kind": rec["kind"], "page": "https://www.pdufa.bio" + rec["page"] if rec["page"] else None,
                    "source_label": s["label"], "source_kind": s["kind"], "source_url": s["url"],
                    "source_printed": s.get("printed"), "source_published_at": rec["source_at"].isoformat(),
                    "source_published_at_utc": rec["source_at"].astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "site_published_at": rec["site_at"].isoformat(),
                    "site_published_at_utc": rec["site_at"].astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "site_commit": rec["commit"], "minutes_after_source": rec["gap_min"]})
    return out


def write_api(stamped, dry):
    rows = api_rows(stamped)
    body = ("// Generated by build_post_speed.py. Do not edit by hand. /api/v1/post-speed: per catalyst event, the verified\n"
            "// time its primary source was published and the time pdufa.bio first published it (public commit).\n"
            "export default " + json.dumps(rows, ensure_ascii=False, indent=1) + ";\n")
    old = io.open(API_DATA, encoding="utf-8").read() if os.path.exists(API_DATA) else ""
    if body != old and not dry:
        io.open(API_DATA, "w", encoding="utf-8", newline="\n").write(body)
    return body != old


def research_page(stamped, skipped, dry):
    css = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,"
           "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5}a{color:#6fb6ff;text-decoration:none}a:hover{text-decoration:underline}"
           ".wrap{max-width:920px;margin:0 auto;padding:22px 18px 60px}.top{display:flex;align-items:center;justify-content:space-between;"
           "border-bottom:1px solid #1a3358;padding-bottom:12px}.brand{font-size:19px;font-weight:800;color:#f2f6fc}.brand b{color:#e3ba5e}"
           ".nav a{color:#a7bcd9;font-size:13px;margin-left:14px}h1{font-size:27px;line-height:1.18;margin:10px 0 6px}"
           "h2{font-size:18px;color:#e3ba5e;margin:28px 0 8px}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}.bc a{color:#94a9c9}"
           ".sub{color:#cfe0f5;font-size:15.5px}.note{font-size:13px;color:#9db3d4;line-height:1.65}"
           "table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0}th,td{border-bottom:1px solid #1a3358;padding:7px 8px;"
           "text-align:left;vertical-align:top}th{color:#a7bcd9;font-weight:600}.tw{overflow-x:auto}.box{background:#0c1d38;"
           "border:1px solid #1e3a63;border-radius:12px;padding:13px 15px;margin:12px 0}footer{border-top:1px solid #1a3358;"
           "margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")
    st = sorted(stamped, key=lambda r: r["source_at"], reverse=True)
    gaps = [r["gap_min"] for r in st]
    n = len(st)
    if n:
        med = statistics.median(gaps)
        lede = (f"{n} catalyst events on pdufa.bio have a verified time for their primary source. pdufa.bio published "
                f"them a median {dur(med // 1)} after that source; the shortest gap was {dur(min(gaps))} and the longest "
                f"{dur(max(gaps))}.")
    else:
        lede = "No catalyst event has both a verified source time and a verified publication time yet."
    title = "How fast pdufa.bio posts FDA catalysts, to the minute"
    desc = (f"Every FDA decision and PDUFA date change on pdufa.bio with a verified source time: when the company, the "
            f"SEC filing or the FDA published it, when pdufa.bio published it (public commit), and the gap in minutes.")
    trs = []
    for r in st:
        s = r["source"]
        trs.append(f'<tr><td><a href="{esc(r["page"])}#posted">{esc(r["t"])} &middot; {esc(str(r["name"])[:60])}</a><br>'
                   f'<span class="note">{esc(r["event"])}</span></td><td><a href="{esc(s["url"])}" rel="noopener">'
                   f'{esc(s["label"])}</a><br>{esc(fmt_et(r["source_at"]))}</td><td>{esc(fmt_et(r["site_at"]))}<br>'
                   f'<a href="{REPO}{r["commit"]}" rel="noopener">commit {r["commit"][:7]}</a></td>'
                   f'<td><b>{esc(dur(r["gap_min"]))}</b></td></tr>')
    table = ('<div class="tw"><table><tr><th>Catalyst</th><th>Source and its time</th><th>pdufa.bio published</th>'
             '<th>Gap</th></tr>' + "".join(trs) + "</table></div>") if trs else ""
    sk = [f'<li>{esc(r.get("t") or r["row"])} &middot; {esc(r.get("event") or "")}: {esc(r["skip"])}</li>'
          for r in sorted(skipped, key=lambda r: r["key"])]
    ld = {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": desc, "url": PAGE_URL,
          "creator": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
          "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
          "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                            "contentUrl": "https://www.pdufa.bio/api/v1/post-speed"}]}
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f'initial-scale=1,viewport-fit=cover"><title>{esc(title)} | pdufa.bio</title><meta name="description" '
            f'content="{esc(desc)}"><link rel="canonical" href="{PAGE_URL}"><meta name="robots" content="index,follow,'
            f'max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" '
            f'href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">'
            f'<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{PAGE_URL}">'
            f'<style>{css}</style><script type="application/ld+json">'
            + json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") +
            '</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
            '<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts'
            '</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">'
            f'Research</a> &rsaquo; Posting speed</div><h1>{esc(title)}</h1><div class="sub">{esc(lede)}</div>'
            '<div class="box note"><b style="color:#e3ba5e">How each time is read.</b> <b>Source time</b>: when the '
            'catalyst&rsquo;s primary source was published, read on that source itself: the time a newswire page prints '
            'on the company&rsquo;s release, the &ldquo;Accepted&rdquo; time on the SEC&rsquo;s EDGAR index page of the '
            'company&rsquo;s 8-K or 6-K (EDGAR prints Eastern time), or the publication time with its time zone in the '
            'FDA&rsquo;s own RSS feed. When an event has more than one timed source, the earliest is used. A source that '
            'prints a date but no time is never given one. <b>pdufa.bio time</b>: when the change that first published the '
            'decision or the moved goal date landed on the main branch of pdufa.bio&rsquo;s public repository, which '
            'deploys the site; each row links that commit. <b>Gap</b>: the second time minus the first, in whole minutes, '
            'rounded down. An event is left out when a disclosure that prints no time may have come earlier, because the gap '
            'could then look shorter than it was.</div>'
            '<h2>Every timed catalyst</h2>' + (table or '<p class="note">None yet.</p>') +
            (('<h2>Timed but not stamped</h2><ul class="note">' + "".join(sk) + "</ul>") if sk else "") +
            '<h2>Data</h2><p class="note">The same records as JSON, free: <a href="/api/v1/post-speed">/api/v1/post-speed</a> '
            '(see <a href="/developers">the API docs</a>). A time found to be wrong is fixed with a dated entry on '
            '<a href="/corrections">/corrections</a>.</p>'
            '<p class="note">These are records of when pdufa.bio published facts, not a claim about any other site, and '
            'not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an '
            'independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. '
            'Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> '
            'Verify every date and outcome against primary FDA, SEC or company filings.<br><br>&copy; 2026 pdufa.bio. All '
            'rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>')
    p = os.path.join(SITE, PAGE_REL, "index.html")
    old = io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    keep = {}
    for mk in re.findall(r"<!--([A-Z_]+):BEGIN-->", old):          # blocks other builders inject stay where they were
        if mk not in ("POSTSPEED",):
            m = re.search(r"<!--" + mk + r":BEGIN-->.*?<!--" + mk + r":END-->", old, re.S)
            if m:
                keep[mk] = m.group(0)
    if keep and old:
        # re-run injectors own those blocks; regenerating them here is not this builder's job, so the page is rewritten
        # only when its own content changed (compare without injected blocks)
        strip = lambda t: re.sub(r"<!--([A-Z_]+):BEGIN-->.*?<!--\1:END-->", "", t, flags=re.S)
        if strip(old) == strip(page):
            return False
    if not dry:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="").write(page)
    return page != old


CARD_B, CARD_E = "<!--POSTSPEED-CARD:BEGIN-->", "<!--POSTSPEED-CARD:END-->"


def research_card(stamped, dry):
    """The /research hub card carries this page's own numbers, rewritten every build."""
    path = os.path.join(SITE, "research", "index.html")
    if not os.path.exists(path):
        return 0
    doc = io.open(path, encoding="utf-8", errors="replace").read()
    card = ""
    if stamped:
        g = sorted(r["gap_min"] for r in stamped)
        card = (f"{CARD_B}<a class='row' href='/{PAGE_REL}'><div class='t'>How long after the source pdufa.bio posted each "
                f"FDA decision</div><div class='d'>{len(g)} decisions and goal-date changes timed to the minute against the "
                f"SEC filing, wire release or FDA notice they rest on: median {esc(dur(int(statistics.median(g))))}, from "
                f"{esc(dur(g[0]))} to {esc(dur(g[-1]))}, each with its public commit.</div></a>{CARD_E}")
    new = put_block(doc, CARD_B, CARD_E, card, [("<!--TIMING2024-CARD:END-->", True), ("<div class='grid'>", True)])
    return write(path, new, doc, dry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["research", "pages"], default=None,
                    help="research: the /research page, the API data and the cache (runs before the site-wide "
                         "normalisers); pages: the stamps on event and /drug pages (runs after the pages are built "
                         "and linked). Default: both.")
    a = ap.parse_args()
    do_pages, do_research = a.only in (None, "pages"), a.only in (None, "research")
    rows = load_rows()
    src_led = json.load(io.open(SOURCES, encoding="utf-8")) if os.path.exists(SOURCES) else {"events": {}}
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    changes = (json.load(io.open(ROWHIST, encoding="utf-8")).get("changes") or []) if os.path.exists(ROWHIST) else []
    now_iso = dt.datetime.now(ET).replace(microsecond=0).isoformat()
    recs, added = compute(rows, src_led, cache, changes, now_iso)
    stamped = [r for r in recs if "gap_min" in r and "skip" not in r]
    skipped = [r for r in recs if "skip" in r]
    if added and not a.dry_run:
        io.open(CACHE, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(sorted(cache.items())), indent=1) + "\n")
    w_ev, n_ev = event_pages(stamped, a.dry_run) if do_pages else (0, 0)
    w_dr = drug_pages(stamped, a.dry_run) if do_pages else 0
    w_api = write_api(stamped, a.dry_run) if do_research else 0
    w_pg = research_page(stamped, skipped, a.dry_run) if do_research else 0
    if do_research:
        research_card(stamped, a.dry_run)
    gaps = [r["gap_min"] for r in stamped]
    print(f"posting speed: {len(stamped)} event(s) stamped on {n_ev} page(s) ({w_ev} written), {len(skipped)} timed but not "
          f"stamped; drug pages written {w_dr}; api {'written' if w_api else 'same'}; /{PAGE_REL} "
          f"{'written' if w_pg else 'same'}; cache +{added}"
          + (f"; median {dur(statistics.median(gaps) // 1)}, range {dur(min(gaps))} to {dur(max(gaps))}" if gaps else ""))
    for r in skipped:
        print(f"   not stamped: {r['key']}: {r['skip']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
