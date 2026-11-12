# -*- coding: utf-8 -*-
"""inject_site_links.py -- internal links so Google finds the pages it has not indexed (audit 2026-11-11 order 2).

Google Search Console (Nov 8): 55 pages indexed, 1,568 "Discovered - currently not indexed". Requested indexing gets a
page in within a day (three pages proved it on Nov 10-11), so the pages are indexable; Google is not being led to
them. The homepage carried 61 internal links and none to the daily pages, the CRL database, the studies or the
next decisions' event pages. This writes four marker-bounded blocks, idempotently, from the dataset and the
published pages:

  1. SITELINKS on every page, above the footer: the hubs, the daily pages, the studies and /sitemap.
  2. LINKHUB on the homepage: the next 12 FDA goal dates (event pages), the last 10 decisions (decision pages),
     today / this week / this month, and the data pages.
  3. RELATED on every leaf page: event pages link the six nearest other upcoming goal dates, their month and their
     ticker; decision pages the six decisions nearest in time, their year and ticker; drug and ticker pages their
     six alphabetical neighbours. Every leaf therefore gets about six inbound links from its peers.
  4. /sitemap: an HTML list of every URL in sitemap.xml, grouped by section, with each page's own title.

tests/test_reachability.py asserts every sitemap URL is within 3 clicks of / in the built HTML, no orphans, and a
median of at least 5 inbound links. Facts only, not investment advice.

    python inject_site_links.py [--dry-run]
"""
import argparse
import collections
import glob
import html
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

MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
SKIP = {"index_redesign.html", "preview.html", "ping.html", "holding.html", "app.html"}
esc = lambda s: html.escape(str(s or ""), quote=True)
A = 'style="color:#9ec5ff;text-decoration:none"'

SITE_LINKS = [
    ("FDA calendar 2026", "/calendar"), ("2027 PDUFA dates", "/calendar/2027"), ("FDA decisions today", "/fda-decisions-today"),
    ("This week", "/fda-approval-decisions-this-week"), ("This month", "/fda-this-month"),
    ("Decisions 2026", "/decisions/2026"), ("Decisions 2025", "/decisions/2025"), ("CRL database", "/crl"), ("FDA approvals by month", "/fda-approvals"),
    ("FDA approval letters", "/fda-approval-letters"), ("Decision timing study", "/research/fda-decision-timing"),
    ("Run-up study", "/runup-by-year"), ("FDA approval rate", "/fda-approval-rate"), ("Oncology readouts", "/readouts/oncology"),
    ("Readouts", "/readouts"), ("Conferences", "/conferences"), ("Corrections", "/corrections"), ("All pages", "/sitemap"),
]


def page_exists(href):
    if href in ("/", "/sitemap"):   # /sitemap is written by this script
        return True
    return os.path.exists(os.path.join(SITE, *href.strip("/").split("/"), "index.html"))


def all_pages():
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        if rel.startswith(("_", "api/")) or "/_" in rel:
            continue
        yield p, "/" + rel[:-len("index.html")].rstrip("/")


def put(doc, b, e, block, before=("<footer", '<div class="legal"', "</body>")):
    if b in doc:
        return re.sub(re.escape(b) + ".*?" + re.escape(e), lambda _: block, doc, flags=re.S)
    for anchor in before:
        k = doc.find(anchor)
        if k >= 0:
            return doc[:k] + block + doc[k:]
    return doc


def nav_block(title, items, b, e):
    links = " &middot; ".join(f'<a href="{h}" {A}>{esc(t)}</a>' for t, h in items)
    return (f'{b}<nav aria-label="{esc(title)}" style="margin:22px 0 6px;padding-top:12px;border-top:1px solid #1a3358;'
            f'font-size:13px;line-height:1.9;color:#94a9c9"><b style="color:#cfe0f5">{esc(title)}:</b> {links}</nav>{e}')


def title_of(doc):
    m = re.search(r"<title>(.*?)</title>", doc, re.S)
    return html.unescape(re.sub(r"\s*\|\s*pdufa\.bio\s*$", "", m.group(1).strip())) if m else ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    today = eastern_today().isoformat()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    pages = dict((u, p) for p, u in all_pages() if os.path.basename(os.path.dirname(p)) + "/index.html" not in SKIP)
    docs = {u: io.open(p, encoding="utf-8", errors="replace").read() for u, p in pages.items()}
    noindex = {u for u, d in docs.items() if re.search(r'<meta name="robots" content="[^"]*noindex', d)}
    live = lambda u: u in docs and u not in noindex

    # ---- upcoming event pages (by goal date) and decision pages (by date)
    up = sorted({(r["d"], r["url"], r["t"], re.sub(r"\s+-\s+.*$", "", str(r.get("name") or ""))[:60])
                 for r in rows if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting")
                 and str(r.get("url") or "").startswith("/pdufa/") and str(r.get("d") or "") >= today
                 and live(r["url"])})
    dec_doc = docs.get("/decisions", "")
    decs = sorted({(m.group(2), m.group(1), m.group(3)) for m in re.finditer(
        r'<a class="row" href="(/fda-decision/([A-Z0-9.]+-\d{4}-\d{2}-\d{2}))"><div class="t">[^<]*</div><div class="d">'
        r'(?:<span[^>]*>[^<]*</span>:\s*)?([^<]*)</div>', dec_doc)})
    decs = [(k[-10:], u, k.rsplit("-", 3)[0], html.unescape(d)[:60]) for k, u, d in decs if live(u)]
    decs.sort()

    out, n_rel = {}, 0
    # ---- RELATED on leaves
    up_idx = {u: i for i, (_, u, _, _) in enumerate(up)}
    dec_idx = {u: i for i, (_, u, _, _) in enumerate(decs)}
    fam = collections.defaultdict(list)
    for u in sorted(docs):
        parts = u.strip("/").split("/")
        if len(parts) == 2 and parts[0] in ("drug", "ticker", "conference", "condition") and live(u):
            fam[parts[0]].append(u)
    for u, doc in docs.items():
        if u in noindex:
            continue
        items = []
        if u in up_idx:
            i = up_idx[u]
            near = [x for x in up[max(0, i - 3):i + 4] if x[1] != u][:6]
            items = [(f"{t} {d}: {nm}", h) for d, h, t, nm in near]
            d0, t0 = up[i][0], up[i][2]
            for t_, h_ in ((f"All {MON[int(d0[5:7]) - 1].capitalize()} {d0[:4]} PDUFA dates", f"/calendar/{d0[:4]}/{MON[int(d0[5:7]) - 1]}"),
                           (f"{t0} catalyst hub", f"/ticker/{t0}")):
                if page_exists(h_):
                    items.append((t_, h_))
            title = "Other upcoming FDA decisions"
        elif u in dec_idx:
            i = dec_idx[u]
            near = [x for x in decs[max(0, i - 3):i + 4] if x[1] != u][:6]
            items = [(f"{t} {d}: {nm}", h) for d, h, t, nm in near]
            d0, t0 = decs[i][0], decs[i][2]
            for t_, h_ in ((f"All FDA decisions in {d0[:4]}", f"/decisions/{d0[:4]}"), (f"{t0} catalyst hub", f"/ticker/{t0}")):
                if page_exists(h_):
                    items.append((t_, h_))
            title = "FDA decisions near this one"
        else:
            parts = u.strip("/").split("/")
            if len(parts) == 2 and parts[0] in fam:
                lst = fam[parts[0]]
                if u in lst:
                    i = lst.index(u)
                    near = [x for x in lst[max(0, i - 3):i + 4] if x != u][:6]
                    items = [(title_of(docs[x])[:60] or x, x) for x in near]
                    title = {"drug": "Other drugs", "ticker": "Other companies", "conference": "Other conferences",
                             "condition": "Other conditions"}[parts[0]]
        new = doc
        if items:
            new = put(new, "<!--RELATED:BEGIN-->", "<!--RELATED:END-->",
                      nav_block(title, items, "<!--RELATED:BEGIN-->", "<!--RELATED:END-->"))
            n_rel += 1
        new = put(new, "<!--SITELINKS:BEGIN-->", "<!--SITELINKS:END-->",
                  nav_block("Browse pdufa.bio", [(t, h) for t, h in SITE_LINKS if page_exists(h) and h != u],
                            "<!--SITELINKS:BEGIN-->", "<!--SITELINKS:END-->"))
        out[u] = new

    # ---- LINKHUB on the homepage
    nxt = up[:12]
    last = list(reversed(decs))[:10]
    def ul(items):
        return "<ul style=\"margin:6px 0 0;padding-left:18px;line-height:1.8\">" + "".join(
            f'<li><a href="{h}" {A}>{esc(t)}</a></li>' for t, h in items) + "</ul>"
    hub = ('<!--LINKHUB:BEGIN--><section style="margin:26px 0 8px;padding-top:14px;border-top:1px solid #1a3358;'
           'display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;font-size:13.5px">'
           f'<div><h2 style="font-size:15px;margin:0">Next FDA decision dates</h2>'
           f'{ul([(f"{d}  {t}: {nm}", h) for d, h, t, nm in nxt])}</div>'
           f'<div><h2 style="font-size:15px;margin:0">Latest FDA decisions</h2>'
           f'{ul([(f"{d}  {t}: {nm}", h) for d, h, t, nm in last])}</div>'
           f'<div><h2 style="font-size:15px;margin:0">Daily pages, studies and data</h2>'
           f'{ul([(t, h) for t, h in SITE_LINKS if page_exists(h)])}</div></section><!--LINKHUB:END-->')
    hp = out.get("/") or docs.get("/")
    if hp is not None:
        out["/"] = put(hp, "<!--LINKHUB:BEGIN-->", "<!--LINKHUB:END-->", hub,
                       before=("<!--SITELINKS:BEGIN-->", "<footer", "</body>"))

    # ---- /sitemap (HTML)
    sm = io.open(os.path.join(SITE, "sitemap.xml"), encoding="utf-8").read()
    locs = [re.sub(r"^https://www\.pdufa\.bio", "", x).rstrip("/") or "/" for x in re.findall(r"<loc>([^<]+)</loc>", sm)]
    groups = collections.OrderedDict()
    label = {"pdufa": "FDA decision dates (event pages)", "fda-decision": "FDA decisions", "drug": "Drugs",
             "ticker": "Companies", "calendar": "Calendar months", "conference": "Conferences", "readouts": "Readouts",
             "research": "Research", "learn": "Learn", "decisions": "Decision archives", "crl": "Complete response letters",
             "condition": "Conditions"}
    for u in sorted(set(locs) | {"/sitemap"}, key=lambda x: (x.split("/")[1] if x != "/" else "", x)):
        if u not in docs or u in noindex:
            continue
        sec = u.split("/")[1] if u != "/" else ""
        groups.setdefault(label.get(sec, "Site"), []).append(u)
    body = "".join(f'<h2 style="font-size:17px;color:#e3ba5e;margin:22px 0 6px">{esc(g)} &middot; {len(us)}</h2>'
                   + ul([(title_of(docs.get(x, "")) or x, x) for x in us]) for g, us in groups.items())
    n_sm = sum(len(v) for v in groups.values())
    tpl = docs.get("/methodology") or ""
    if tpl:
        head = tpl[:tpl.index("<h1")] if "<h1" in tpl else ""
        head = re.sub(r"<title>.*?</title>", f"<title>All pages on pdufa.bio: {n_sm} pages by section | pdufa.bio</title>",
                      head, count=1, flags=re.S)
        head = re.sub(r'(<meta name="description" content=")[^"]*(")',
                      lambda m: m.group(1) + f"Every page on pdufa.bio, {n_sm} in all, grouped by section: FDA decision "
                      "dates, decisions, drugs, companies, calendar months, conferences and research." + m.group(2), head)
        for pat in (r'(<link rel="canonical" href=")[^"]*(")', r'(<meta property="og:url" content=")[^"]*(")'):
            head = re.sub(pat, lambda m: m.group(1) + "https://www.pdufa.bio/sitemap" + m.group(2), head)
        head = re.sub(r'<script type="application/ld\+json"[^>]*>.*?</script>', "", head, flags=re.S)
        head = re.sub(r"<!--DMOD:BEGIN-->.*?<!--DMOD:END-->", "", head, flags=re.S)
        bc = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pdufa.bio/"},
            {"@type": "ListItem", "position": 2, "name": "All pages", "item": "https://www.pdufa.bio/sitemap"}]})
        head = head.replace("</head>", f'<script type="application/ld+json">{bc}</script></head>', 1)
        foot = tpl[tpl.index("<footer"):] if "<footer" in tpl else "</div></body></html>"
        foot = re.sub(r"<!--SITELINKS:BEGIN-->.*?<!--SITELINKS:END-->", "", foot, flags=re.S)
        out["/sitemap"] = (head + f"<h1>All pages on pdufa.bio</h1><p class=\"sub\">Every page in the sitemap, {n_sm} "
                           f"in all, grouped by section, each under its own title. The <a href=\"/sitemap.xml\" {A}>XML "
                           f"sitemap</a> carries the same list for crawlers.</p>" + body + foot)

    if not a.dry_run:
        for u, doc in out.items():
            if u == "/sitemap":
                os.makedirs(os.path.join(SITE, "sitemap"), exist_ok=True)
                p = os.path.join(SITE, "sitemap", "index.html")
            else:
                p = pages[u]
            if doc != docs.get(u):
                io.open(p, "w", encoding="utf-8").write(doc)
    print(f"site links: SITELINKS on {len(out) - 1} page(s); RELATED on {n_rel}; homepage LINKHUB {len(nxt)} next + "
          f"{len(last)} latest; /sitemap {n_sm} pages" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

