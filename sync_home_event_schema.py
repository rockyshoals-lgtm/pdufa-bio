# -*- coding: utf-8 -*-
"""sync_home_event_schema.py -- the homepage's "Upcoming FDA PDUFA decisions" structured data lists upcoming decisions.

2026-11-08 (David: "there is something on the home page that says data as of August"). The visible page was current,
but the homepage's JSON-LD ItemList "Upcoming FDA PDUFA decisions" had not been rewritten since late July: six Event
items dated Jul 29 - Aug 17, 2026, all marked EventScheduled -- CAPR on Jul 29 (moved to Nov 22), OTLK, VTRS, MRNA,
LNTH, BMY, every one long decided. That block is what search engines and answer engines read as the page's list of
upcoming decisions, so to them the homepage said August. No builder owned it.

This rewrites it from the dataset every run: the next 10 day-dated pending PDUFA goal dates (Eastern today onward),
each pointing at its event page, with the sourced date only. Idempotent.

    python sync_home_event_schema.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

BASE = "https://www.pdufa.bio"
N = 10


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def month_chips(doc, rows, today):
    """The homepage's month browser, from the current month forward.

    It was static HTML written in July -- "Browse 2026 by month: July, August, September..." -- so in November the first
    thing it offered was four finished months and it stopped at December with 35 sourced 2027 dates on the site.
    Now: every month page from the current month on, each with its count of pending dated goals, then the year hubs,
    then the finished months of the current year as one quiet line."""
    import glob
    pages = sorted((int(p.split(os.sep)[-3]), MONTHS.index(p.split(os.sep)[-2]) + 1)
                   for p in glob.glob(os.path.join(SITE, "calendar", "20[0-9][0-9]", "*", "index.html"))
                   if p.split(os.sep)[-2] in MONTHS)
    cur = (int(today[:4]), int(today[5:7]))
    cnt = {}
    for r in rows:
        if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting") and str(r.get("d") or "") >= today:
            k = (int(r["d"][:4]), int(r["d"][5:7]))
            cnt[k] = cnt.get(k, 0) + 1
    ahead = [k for k in pages if k >= cur]
    past = [k for k in pages if k < cur and k[0] == cur[0]]
    chip = '<a class="chip" href="/calendar/{y}/{m}">{M} {y}{n}</a>'
    html_ = "".join(chip.format(y=y, m=MONTHS[mo - 1], M=MONTHS[mo - 1].capitalize()[:3],
                                n=f' <b>{cnt[(y, mo)]}</b>' if cnt.get((y, mo)) else "") for y, mo in ahead)
    hubs = "".join(f'<a class="chip" href="/calendar/{y}">All {y} dates</a>'
                   for y in sorted({y for y, _ in ahead if y > cur[0]})
                   if os.path.exists(os.path.join(SITE, "calendar", str(y), "index.html")))
    past_html = ""
    if past:
        past_html = ('<div style="margin-top:8px;font-size:12.5px;color:var(--mut2)">Earlier in ' + str(cur[0]) + ': '
                     + " &middot; ".join(f'<a href="/calendar/{y}/{MONTHS[mo - 1]}" style="color:var(--mut2)">'
                                         f'{MONTHS[mo - 1].capitalize()}</a>' for y, mo in past) + "</div>")
    block = (f'<div class="blk"><h2>Upcoming PDUFA dates by month</h2><div class="chips">{html_}{hubs}</div>'
             f'{past_html}</div>')
    pat = re.compile(r'<div class="blk"><h2>(?:Browse \d{4} by month|Upcoming PDUFA dates by month)</h2>.*?</div>'
                     r'(?:<div style="margin-top:8px;font-size:12.5px[^>]*>.*?</div>)?</div>', re.S)
    return pat.sub(lambda _: block, doc, count=1)


QB, QE = "<!--NEXTQ:BEGIN-->", "<!--NEXTQ:END-->"
QNAME = "What are the next FDA PDUFA dates?"


def next_dates_faq(doc, up):
    """A visible FAQ answer naming the next goal dates, mirrored in FAQPage schema (the two must match).

    The homepage's question list was all definitions ("What is a PDUFA date?"); the question people and answer engines
    actually bring to a PDUFA calendar -- which decisions are next -- had no sentence anywhere that answered it."""
    import html as _h
    if not up:
        return doc
    by = {}
    for r in up[:8]:
        by.setdefault(r["d"], []).append(r)
    parts = []
    for d, rs in list(by.items())[:4]:
        dd = f"{MONTHS[int(d[5:7]) - 1].capitalize()} {int(d[8:10])}, {d[:4]}"
        names = "; ".join(f"{str(r.get('name') or '').split(' - ')[0].strip()} ({r['t']})" for r in rs)
        parts.append(f"{dd}: {names}")
    ans = ("The next FDA PDUFA goal dates on pdufa.bio are " + ". ".join(parts) + ". Each date comes from the "
           "sponsor's own filing or release and links its source on the event page; goal dates can move if the FDA "
           "extends a review. The full list is on the calendar.")
    vis = (f'{QB}<details style="border-top:1px solid var(--line);padding:11px 0" open><summary style="cursor:pointer;'
           f'font-weight:600;color:#eef4fc;font-size:14.5px;list-style:none">{QNAME}</summary><p style="margin:8px 0 0;'
           f'font-size:14px;line-height:1.75;color:var(--mut2)">{_h.escape(ans)} <a href="/calendar">See the calendar</a>.'
           f'</p></details>{QE}')
    if QB in doc:
        doc = re.sub(re.escape(QB) + ".*?" + re.escape(QE), lambda _: vis, doc, flags=re.S)
    else:
        m = re.search(r'<details style="border-top:1px solid var\(--line\);padding:11px 0"><summary[^>]*>What is a PDUFA date\?',
                      doc)
        if not m:
            return doc
        doc = doc[:m.start()] + vis + doc[m.start():]
    # FAQPage JSON-LD: same question, same answer text
    pm = re.search(r'(<script type="application/ld\+json"[^>]*>)(\{"@context":"https://schema.org","@type":"FAQPage".*?)'
                   r'(</script>)', doc, re.S)
    if pm:
        try:
            ld = json.loads(pm.group(2))
            ld["mainEntity"] = [q for q in ld.get("mainEntity", []) if q.get("name") != QNAME]
            ld["mainEntity"].insert(0, {"@type": "Question", "name": QNAME,
                                        "acceptedAnswer": {"@type": "Answer", "text": ans}})
            doc = doc[:pm.start(2)] + json.dumps(ld, ensure_ascii=False, separators=(",", ":")) + doc[pm.end(2):]
        except ValueError:
            pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = eastern_today().isoformat()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    up = sorted([r for r in rows if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting")
                 and r.get("dp", "day") == "day" and str(r.get("d") or "") >= today
                 and str(r.get("url") or "").startswith("/pdufa/")], key=lambda r: (r["d"], r["t"]))[:N]
    items = []
    for i, r in enumerate(up, 1):
        drug = re.sub(r"\s+-\s+\(.*?\)$", "", str(r.get("name") or "")).strip()
        url = BASE + r["url"]
        items.append({"@type": "ListItem", "position": i, "item": {
            "@type": "Event", "name": f"{r['t']} FDA decision: {drug}",
            "description": f"FDA PDUFA goal date for {drug} ({r.get('company') or r['t']}), from the sponsor's own "
                           f"disclosure. Facts only, not investment advice.",
            # a goal DATE, not a time: the FDA can act at any hour of that day, so no clock time is claimed
            "startDate": r["d"], "endDate": r["d"],
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
            "location": {"@type": "VirtualLocation", "url": url},
            "organizer": {"@type": "Organization", "name": "U.S. Food and Drug Administration", "url": "https://www.fda.gov"},
            "image": f"{BASE}/og.png", "url": url}})
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Upcoming FDA PDUFA decisions",
          "numberOfItems": len(items), "itemListElement": items}
    p = os.path.join(SITE, "index.html")
    doc = io.open(p, encoding="utf-8").read()
    pat = re.compile(r'(<script type="application/ld\+json"[^>]*>)\{"@context":"https://schema.org","@type":"ItemList",'
                     r'"name":"Upcoming FDA PDUFA decisions".*?(</script>)', re.S)
    block = json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
    if pat.search(doc):
        new = pat.sub(lambda m: m.group(1) + block + m.group(2), doc, count=1)
    else:
        new = doc.replace("</head>", f'<script type="application/ld+json">{block}</script></head>', 1)
    new = month_chips(new, rows, today)
    new = next_dates_faq(new, up)
    if new != doc and not a.dry_run:
        io.open(p, "w", encoding="utf-8").write(new)
    print(f"homepage upcoming-decisions schema: {len(items)} event(s), {up[0]['d'] if up else '-'} .. "
          f"{up[-1]['d'] if up else '-'}" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
