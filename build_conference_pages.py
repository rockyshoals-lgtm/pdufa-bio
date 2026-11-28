# -*- coding: utf-8 -*-
"""build_conference_pages.py -- one page per meeting, organiser-dated, with the presenters we can source.

Audit 2026-10-11 section 4b item 3: `aasld 2026` had 80 impressions at position 9.28 and 0 clicks, `sabcs 2026`
16 at 9.50. The site had 14 hand-made /conference/{CODE} pages (dates, city, presenters, FAQ) and 42 meetings
in conferences.json; the other 28, including every 2027 meeting, had no page, and the API's conference rows
pointed at the hub. Each page's title now carries the organiser's dates and city, which is what the query
asks for.

What this does, from conferences.json (organiser-verified dates; nothing projected) and the presenter files
build_conferences.py already publishes:
  * creates /conference/{CODE}/index.html for every meeting whose END is today or later and that has no
    page, from the AASLD page as skeleton (same CSS, nav, freshness stamp and marker blocks, so the
    chain's conference scripts -- lede, FAQ, run-up module, legal footer, nav -- fill it like any other);
  * on every page (new or existing) regenerates the parts that are pure data between <!--CONFCORE--> markers:
    title, description, canonical, breadcrumb + Event JSON-LD, h1, dates/location card, presenters sourced
    to their filing or release, and the "filings that mention this meeting" list for mined rows;
  * never touches a page's FAQ, run-up or lede blocks: those have their own owners.

    python build_conference_pages.py [--dry-run]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import build_conferences as BC  # noqa: E402
from site_dates import eastern_today  # noqa: E402

TEMPLATE = os.path.join(SITE, "conference", "AASLD", "index.html")
CB, CE = "<!--CONFCORE:BEGIN-->", "<!--CONFCORE:END-->"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONF = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
        "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def short_span(c):
    a, b = dt.date.fromisoformat(c["start"]), dt.date.fromisoformat(c["end"])
    if a == b:
        return f"{MON[a.month - 1]} {a.day}, {a.year}"
    if a.month == b.month:
        return f"{MON[a.month - 1]} {a.day}-{b.day}, {a.year}"
    return f"{MON[a.month - 1]} {a.day}-{MON[b.month - 1]} {b.day}, {a.year}"


def long_span(c):
    a, b = dt.date.fromisoformat(c["start"]), dt.date.fromisoformat(c["end"])
    if a == b:
        return f"{MONF[a.month - 1]} {a.day}, {a.year}"
    if a.month == b.month:
        return f"{MONF[a.month - 1]} {a.day} to {b.day}, {a.year}"
    return f"{MONF[a.month - 1]} {a.day} to {MONF[b.month - 1]} {b.day}, {a.year}"


def city_short(c):
    return str(c.get("city") or "").split(",")[0].strip()


def organiser_host(u):
    return re.sub(r"^https?://(www\.)?", "", str(u or "")).split("/")[0]


def hub_exists(tk):
    return bool(tk) and os.path.exists(os.path.join(SITE, "ticker", tk, "index.html"))


# 2026-11-28 (Bing: "asco 2027" at position 7.5 with 0 clicks; Copilot cited asco.org, not us): someone searching a
# meeting's name months ahead wants its calendar: when abstracts are due, when titles post, when the embargo lifts.
# The organiser publishes those on a "Dates to Know" page; conferences.json now carries them as read there
# (key_dates, with key_dates_source and key_dates_read), in the organiser's own precision: "Late May 2027" stays
# that, never turned into a day. Rendered only where the organiser's list was read; nothing is projected.
def key_dates_html(c, today=None):
    kd = c.get("key_dates") or []
    if not kd or not c.get("key_dates_source"):
        return ""
    today = today or eastern_today().isoformat()
    rows = []
    for k in kd:
        iso = k.get("iso") or ""
        passed = bool(iso) and iso < today and k.get("kind") != "meeting"
        # divs, not a <table>: a table needs a mobile scroll box (tests/test_mobile_layout.py), and two short
        # stacked lines read better on a phone anyway
        rows.append(f'<div style="padding:6px 0;border-top:1px solid #1e3a63"><div style="color:#e3ba5e;font-weight:700">'
                    f'{esc(k["when"])}' + (' <span style="color:#8aa0bf;font-weight:400">(passed)</span>' if passed else '')
                    + f'</div><div style="color:#cfe0f5">{esc(k["what"])}</div></div>')
    read = c.get("key_dates_read") or ""
    try:
        y, m, d = (int(x) for x in read.split("-"))
        read_h = f"{MONF[m - 1]} {d}, {y}"
    except Exception:  # noqa: BLE001
        read_h = read
    # 2026-11-28: an entry may name its own organiser page (source / source_page) when one meeting's calendar is
    # split across two pages (ADA: deadlines on Abstracts, embargo lifts on Embargo Policy). The note names each.
    pages = []
    for u, n in [(c["key_dates_source"], c.get("key_dates_page") or "Dates to Know")] + \
            [(k["source"], k.get("source_page") or "") for k in kd if k.get("source")]:
        if (u, n) not in pages:
            pages.append((u, n))
    links = [f'<a href="{esc(u)}" rel="nofollow noopener" style="color:#6fb6ff">{esc(n)}</a>' for u, n in pages]
    named = (links[0] + " page") if len(links) == 1 else (", ".join(links[:-1]) + " and " + links[-1] + " pages")
    return (f'<h2>Key dates for {esc(c["code"])} {esc(c["start"][:4])}</h2>'
            f'<div class="card"><div style="font-size:13.5px">{"".join(rows)}</div>'
            f'<div class="note" style="margin:8px 0 0">From the organiser\'s {named}'
            + (f', read {esc(read_h)}' if read_h else '') + '. Dates the organiser gives only as a part of a month are '
            'shown as given, and times are as the organiser states them.</div></div>')


def core_html(c, pres, mined):
    code, name, year = c["code"], c["name"], c["start"][:4]
    out = [f'<p class="sub">{esc(short_span(c))} &middot; {esc(c.get("city") or "location per organiser")} &middot; '
           f'{esc(c.get("focus") or "")}.</p>',
           '<div class="card">'
           f'<div class="kv"><span>Dates</span><b>{esc(short_span(c))}</b></div>'
           f'<div class="kv"><span>Location</span><b>{esc(c.get("city") or "per organiser")}</b></div>'
           f'<div class="kv"><span>Therapeutic focus</span><b>{esc(c.get("focus") or "")}</b></div>'
           f'<div class="kv"><span>Biotech presenters sourced</span><b>{len(pres)}</b></div>'
           + (f'<div class="kv"><span>Organiser</span><b><a href="{esc(c["source"])}" rel="nofollow noopener" '
              f'style="color:#6fb6ff">{esc(organiser_host(c["source"]))}</a></b></div>'
              if c.get("source") else "")
           + '</div>']
    out.append(key_dates_html(c))
    out.append('<h2>Biotech presenters</h2>')
    if pres:
        cards = []
        for r in pres:
            tk = (r.get("ticker") or "").upper()
            head = (f'<a href="/ticker/{tk}" style="color:#e3ba5e;font-weight:800">{esc(tk)}</a>' if hub_exists(tk)
                    else f'<b style="color:#e3ba5e">{esc(tk or r.get("company") or "")}</b>')
            bits = [x for x in (r.get("drug"), r.get("pres_type")) if x]
            src = r.get("source_url") or r.get("filing_url") or ""
            sent = re.sub(r"\s+", " ", html.unescape(str(r.get("matched_sentence") or r.get("review_note") or ""))).strip()
            cards.append(f'<span class="card" style="display:block">{head}'
                         f'<div style="font-size:12.5px;color:#a7bcd9">{esc("; ".join(bits)) or "presenting at " + esc(code) + " " + esc(year)}'
                         + (f' &middot; <a href="{esc(src)}" rel="nofollow noopener" style="color:#6fb6ff">source</a>' if src else "")
                         + '</div>'
                         + (f'<div style="font-size:12px;color:#8aa0bf;margin-top:4px">{esc(sent[:220])}</div>' if sent else "")
                         + '</span>')
        out.append(f'<div class="grid">{"".join(cards)}</div>')
        out.append('<div class="note" style="margin:8px 0 0">Each presenter is sourced to the company\'s own filing or '
                   'release naming this meeting; this is not the organiser\'s programme, and abstract titles are '
                   'embargoed until the organiser publishes them.</div>')
    else:
        out.append('<div class="card"><div class="sub" style="margin:0">None sourced yet. A company is listed only when '
                   'its own SEC filing or press release commits to this edition; the organiser\'s abstract list '
                   'usually lands a few weeks before the meeting.</div></div>')
    if mined:
        items = []
        for r in mined[:12]:
            tk = (r.get("ticker") or "").upper()
            sent = re.sub(r"\s+", " ", html.unescape(str(r.get("matched_sentence") or ""))).strip()
            src = r.get("source_url") or r.get("filing_url") or ""
            items.append(f'<li><b>{esc(tk or r.get("company") or "")}</b>: &ldquo;{esc(sent[:200])}&rdquo;'
                         + (f' <a href="{esc(src)}" rel="nofollow noopener" style="color:#6fb6ff">filing</a>' if src else "")
                         + '</li>')
        out.append(f'<h2>Filings that mention {esc(code)} {esc(year)}</h2>'
                   '<div class="note" style="margin:-4px 0 6px">A filing that names the meeting is not a '
                   'commitment to present; these are listed with the sentence, for the reader to judge.</div>'
                   f'<ul style="font-size:13.5px;color:#cfe0f5;line-height:1.6">{"".join(items)}</ul>')
    return "".join(out)


def head_bits(c, pres):
    code, name, year = c["code"], c["name"], c["start"][:4]
    city = city_short(c)
    title = f"{name} {year}: {short_span(c)}" + (f", {city}" if city else "") + ": biotech presenters | pdufa.bio"
    if len(title) > 100:
        title = f"{code} {year}: {short_span(c)}" + (f", {city}" if city else "") + ": biotech presenters | pdufa.bio"
    tail = (f"{len(pres)} biotech presenter{'s' if len(pres) != 1 else ''} sourced to company filings."
            if pres else "Biotech presenters listed as companies announce them in filings and releases.")
    rel = next((k for k in c.get("key_dates") or [] if k.get("kind") == "release"), None)
    if rel and c.get("key_dates_source"):
        tail += f" Abstracts released {', '.join(rel['when'].split(', ')[:2])}."
    where = f" in {c.get('city')}" if c.get("city") else ""
    desc = f"{name} ({code}) {year}: {short_span(c)}{where}. {c.get('focus') or 'Medical'} meeting, dates from the organiser. {tail}"
    if len(desc) > 158:
        desc = f"{name} {year}: {short_span(c)}{where}. {tail}"
    if len(desc) > 158:
        desc = f"{code} {year}: {short_span(c)}{where}. {tail}"
    if len(desc) > 158 and rel and c.get("key_dates_source"):
        desc = (f"{code} {year}: {short_span(c)}{where}. Abstracts released {', '.join(rel['when'].split(', ')[:2])}. "
                "Biotech presenters from company filings and releases.")
    ev = {"@context": "https://schema.org", "@type": "Event", "name": f"{name} ({code}) {year}",
          "startDate": c["start"], "endDate": c["end"],
          "eventStatus": "https://schema.org/EventScheduled",
          "url": f"https://www.pdufa.bio/conference/{BC.conf_slug(code)}"}
    if c.get("city"):
        ev["location"] = {"@type": "Place", "name": c["city"]}
    if c.get("source"):
        ev["sameAs"] = c["source"]
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pdufa.bio/"},
        {"@type": "ListItem", "position": 2, "name": "Conferences", "item": "https://www.pdufa.bio/conferences"},
        {"@type": "ListItem", "position": 3, "name": f"{name} {year}", "item": f"https://www.pdufa.bio/conference/{BC.conf_slug(code)}"}]}
    return title, desc, json.dumps(ev, ensure_ascii=False), json.dumps(bc, ensure_ascii=False)


def apply(doc, c, pres, mined, is_new):
    code, name, year = c["code"], c["name"], c["start"][:4]
    title, desc, ev_ld, bc_ld = head_bits(c, pres)
    doc = re.sub(r"<title>.*?</title>", lambda m: f"<title>{esc(title)}</title>", doc, count=1, flags=re.S)
    doc = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + esc(title) + m.group(2), doc, count=1)
    doc = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + esc(desc) + m.group(2), doc, count=1)
    doc = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + esc(desc) + m.group(2), doc, count=1)
    doc = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + f"https://www.pdufa.bio/conference/{BC.conf_slug(code)}" + m.group(2), doc, count=1)
    doc = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m.group(1) + f"https://www.pdufa.bio/conference/{BC.conf_slug(code)}" + m.group(2), doc, count=1)
    # JSON-LD: replace the Event and BreadcrumbList blocks (FAQ block belongs to build_conference_faq.py)
    def _ld(m):
        body = m.group(1)
        if '"@type":"Event"' in body.replace(" ", "") or '"@type": "Event"' in body:
            return f'<script type="application/ld+json">{ev_ld}</script>'
        if '"@type":"BreadcrumbList"' in body.replace(" ", ""):
            return f'<script type="application/ld+json">{bc_ld}</script>'
        return m.group(0)
    doc = re.sub(r'<script type="application/ld\+json">(.*?)</script>', _ld, doc, flags=re.S)
    doc = re.sub(r'<div class="bc">.*?</div>',
                 f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/conferences">Conferences</a> &rsaquo; {esc(code)}</div>',
                 doc, count=1, flags=re.S)
    doc = re.sub(r"<h1>.*?</h1>", f'<h1>{esc(name)} <span class="g">{esc(year)}</span></h1>', doc, count=1, flags=re.S)
    core = CB + core_html(c, pres, mined) + CE
    if CB in doc and CE in doc:
        doc = doc.split(CB, 1)[0] + core + doc.split(CE, 1)[1]
    else:
        # first build on a hand-made page: the core runs from the sub line after the lede to the legal footer
        m = re.search(r'<!--CONFFACT:END-->\s*', doc)
        n = re.search(r'<div class="legal">', doc)
        if not (m and n and n.start() > m.end()):
            return None
        doc = doc[:m.end()] + core + " " + doc[n.start():]
    doc = re.sub(r"Not affiliated with [A-Za-z0-9 -]+ or its organizer", f"Not affiliated with {esc(code)} or its organizer", doc)
    if is_new:
        for b in ("CRUN", "CRUNALL", "CFAQ", "CFAQS", "DMOD"):
            doc = re.sub(rf"<!--{b}:BEGIN-->.*?<!--{b}:END-->", f"<!--{b}:BEGIN--><!--{b}:END-->", doc, flags=re.S)
        doc = re.sub(r"<!--CONFFACT:BEGIN-->.*?<!--CONFFACT:END-->",
                     f'<!--CONFFACT:BEGIN--><p class="sub fact" style="font-size:17px;color:#eef4fc">{esc(name)} {esc(year)} '
                     f'takes place {esc(long_span(c))}' + (f' in {esc(c["city"])}' if c.get("city") else "") + '.</p><!--CONFFACT:END-->',
                     doc, flags=re.S)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = eastern_today().isoformat()
    data = json.load(io.open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))
    by_code = BC.load_presenters()
    tpl = io.open(TEMPLATE, encoding="utf-8", errors="replace").read()
    # one page per code: the next edition whose end is today or later, else the latest past edition that has a page
    per_code = {}
    for c in sorted(data["conferences"], key=lambda x: x["start"]):
        code = c["code"]
        if c["end"] >= today and code not in per_code:
            per_code[code] = c
    for c in sorted(data["conferences"], key=lambda x: x["start"]):
        if c["code"] not in per_code and os.path.exists(os.path.join(SITE, "conference", BC.conf_slug(c["code"]), "index.html")):
            per_code[c["code"]] = c
    made = refreshed = 0
    for code, c in sorted(per_code.items()):
        rows = BC.presenters_for(c, by_code)
        pres = [r for r in rows if r.get("_tier") != "mined"]
        mined = [r for r in rows if r.get("_tier") == "mined"]
        path = os.path.join(SITE, "conference", BC.conf_slug(code), "index.html")
        is_new = not os.path.exists(path)
        doc = tpl if is_new else io.open(path, encoding="utf-8", errors="replace").read()
        new = apply(doc, c, pres, mined, is_new)
        if new is None:
            print(f"  skip /conference/{code}: no core insertion point")
            continue
        if not a.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w", encoding="utf-8").write(new)
        made += is_new
        refreshed += (not is_new)
        print(f"  /conference/{code:<10} {'NEW' if is_new else 'refreshed'}  {short_span(c):<20} presenters {len(pres):>2}  mined {len(mined):>2}")
    print(f"conference pages: {made} created, {refreshed} refreshed{' (dry run)' if a.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
