# -*- coding: utf-8 -*-
"""sync_calendar_itemlist.py -- the /calendar JSON-LD ItemList is rebuilt from the page's own
still-ahead rows, every build.

Audit 09-06 0840 NEW-1: the ItemList "2026 FDA PDUFA Calendar" was pre-rendered HTML that no CI
step touched. On 2026-09-06 it listed 54 Events against 48 visible ahead rows: 16 decided
applications (camizestrant, rusfertide, oveporexton, Enhertu, ...) were still told to every schema
consumer as EventScheduled, and 9 live rows (SRRK, INCY, RHHBY, GSK, AGIO, CYTK, REGN, CORT, GILD)
were absent. The visible table had been fixed layer by layer; the machine-readable copy of it had
not. "Site knows but does not say", one layer down.

Rule: the ItemList is DERIVED from the rendered rows immediately before it is written, the same way
build_hub_lede.py counts its sentence. It cannot disagree with the table because it is the table.

An "ahead" row is one with an /pdufa/ href, no decision marker (data-dec, checkmark, Approved,
CRL), and a date that is today (Eastern) or later -- or a quarter-only date. That is the same
definition the lede uses for "still ahead", so numberOfItems == the lede's ahead count.

Quarter-only rows carry startDate at month precision (the quarter's last month, which is the
month the page files them under) and say so in `description`; no day is invented.

Owner: this script is the ONLY writer of the /calendar ItemList (grep: numberOfItems). The two
one-off fix_calendar_page*.py scripts are retired from that role.

    python sync_calendar_itemlist.py [--dry-run]
"""
import argparse, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today

SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "calendar", "index.html")
BASE = "https://www.pdufa.bio"

ROW = re.compile(r'<a class="row"([^>]*)>(.*?)</a>', re.S)
Q_LAST_MONTH = {1: "03", 2: "06", 3: "09", 4: "12"}


def text_of(frag):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))).strip()


def ahead_rows(doc, today):
    """[(href, ticker, label, iso_or_None, quarter_or_None)] for rows still ahead."""
    out = []
    for attrs, frag in ROW.findall(doc):
        href = re.search(r'href="([^"]+)"', attrs)
        if not href or not href.group(1).startswith("/pdufa/"):
            continue
        if "data-dec" in attrs:
            continue
        t = text_of(frag)
        low = t.lower()
        if "✓" in t or "approved" in low or "crl" in low or "complete response" in low:
            continue
        iso = re.search(r"\d{4}-\d{2}-\d{2}", t)
        q = re.search(r"\bQ([1-4])\s+(\d{4})", t)
        if iso:
            if iso.group(0) < today:
                continue          # past goal date, no outcome: waiting on the FDA, not ahead
            d, qq = iso.group(0), None
        elif q:
            d, qq = None, (int(q.group(1)), q.group(2))
        else:
            continue
        # "SRRK · 2026-09-30 Apitegromab - (SAPPHIRE)" -> ticker + description
        m = re.match(r"([A-Z][A-Z0-9.\-]*)\s*(?:&middot;|·)\s*(.*)", t)
        ticker = m.group(1) if m else href.group(1).split("/")[2].split("-")[0].upper()
        desc = text_of(re.search(r'<div class="d">(.*?)</div>', frag, re.S).group(1)) \
            if re.search(r'<div class="d">', frag) else t
        out.append((href.group(1), ticker, desc, d, qq))
    return out


def build_items(rows):
    items = []
    for pos, (href, ticker, desc, iso, qq) in enumerate(rows, 1):
        name = f"{ticker} — {desc}" if ticker else desc
        if len(name) > 110:
            name = name[:109].rstrip() + "…"
        ev = {"@type": "Event", "name": name, "url": BASE + href,
              "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
              "eventStatus": "https://schema.org/EventScheduled",
              "location": {"@type": "VirtualLocation", "url": BASE + href}}
        if iso:
            ev["startDate"] = iso
        else:
            qn, yr = qq
            ev["startDate"] = f"{yr}-{Q_LAST_MONTH[qn]}"
            ev["description"] = (f"FDA goal date disclosed by the sponsor only as Q{qn} {yr}; "
                                 f"no day has been announced.")
        items.append({"@type": "ListItem", "position": pos, "item": ev})
    return items


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    doc = open(PAGE, encoding="utf-8", errors="replace").read()
    today = eastern_today().isoformat()
    rows = ahead_rows(doc, today)
    if not rows:
        print("  REFUSING: 0 ahead rows parsed from /calendar -- markup changed?"); sys.exit(2)
    items = build_items(rows)
    il = {"@context": "https://schema.org", "@type": "ItemList",
          "name": "2026 FDA PDUFA Calendar", "numberOfItems": len(items),
          "itemListElement": items}
    block = '<script type="application/ld+json">' + json.dumps(il, ensure_ascii=False) + '</script>'
    pat = re.compile(r'<script type="application/ld\+json">\{"@context":\s*"https://schema.org",\s*'
                     r'"@type":\s*"ItemList",\s*"name":\s*"2026 FDA PDUFA Calendar".*?</script>', re.S)
    new, n = pat.subn(lambda m: block, doc, count=1)
    if n == 0:
        # First time: place it right after the @graph block that carries the BreadcrumbList.
        anchor = re.search(r'</script>', doc[doc.find('"BreadcrumbList"'):])
        i = doc.find('"BreadcrumbList"') + anchor.end()
        new = doc[:i] + block + doc[i:]
    if not a.dry_run:
        open(PAGE, "w", encoding="utf-8").write(new)
    print(f"  /calendar ItemList: {len(items)} items from {len(rows)} ahead rows "
          f"(as of {today} Eastern){' [dry run]' if a.dry_run else ''}")
    for href, ticker, desc, iso, qq in rows:
        print(f"    {ticker:<6} {iso or ('Q%d %s' % qq):<10} {href}")


if __name__ == "__main__":
    main()
