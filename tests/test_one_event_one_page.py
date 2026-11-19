# -*- coding: utf-8 -*-
"""test_one_event_one_page.py -- one FDA decision, one page, and every link lands on it.

Design red team 2026-11-18 (change 4, "One canonical page per event"). Capricor's Nov 22 decision had three pages
(/pdufa/CAPR, /pdufa/CAPR-deramiocel, /ticker/CAPR) with different depth and content: only the drug page carried the
source quote, only the ticker page the full dossier, and the home cards, home list, screener and condition pages split
between them. build_pdufa_ticker_index.py now keeps one page per event (rules 4 to 7 in its docstring), the builders
of the event surfaces link it, retarget_event_links.py points links at redirected or duplicate URLs at it, and
build_retail_pages.py puts the dossier on it. This fails if:

  1. a bare /pdufa/{T} event page and a /pdufa/{T}-{drug} page for the same drug are both indexable (one event,
     two pages; the duplicate map in canonicalise_duplicate_event_pages.py or a redirect settles which is kept);
  2. a ticker index does not link every upcoming PDUFA of its ticker that has its own page, or links a bare
     /pdufa/{T} where the event has its own page;
  3. a ticker index lists one upcoming event and nothing else (no past decision, nothing withdrawn), or a ticker
     with one upcoming PDUFA and no history at all in the dataset keeps a bare page, where a permanent redirect to
     the event's own page belongs;
  4. a /pdufa/ redirect in vercel.json lands nowhere (its chain does not end on a page of this site), or a redirected
     URL still has a page file, or is listed in sitemap.xml;
  5. any page has an internal link that retarget_event_links.py would change (a link to a redirected /pdufa/ URL or
     to a known duplicate event page);
  6. a retail profile's dossier is on its ticker hub when the profile names an event page (the hub only points there);
  7. the workflow does not run retarget_event_links.py after inject_site_links.py and before build_sitemap.py, the
     local chain does not run it, or quarantine_leads.py does not apply it to the pages it restores;
  8. a ticker index has no inbound link from any other page but the HTML sitemap (the red team's draft rewrote every
     /pdufa/{T} link to the ticker's one upcoming event and left 15 indexes linked from nowhere else);
  9. a homepage board tile for an upcoming event links anything but that event's own page, when it has one.

PLANT=link puts a link to a retired bare /pdufa/{T} on the homepage, PLANT=dupe gives a retired ticker its bare page
back as a copy of its event page, PLANT=file gives a retired ticker a page file behind its redirect, PLANT=index drops
an event link from a ticker index, PLANT=sitemap lists a retired URL in sitemap.xml, PLANT=orphan removes every
inbound link to a ticker index, PLANT=board points a homepage tile at the bare /pdufa/{T}; each must FAIL.

    python tests/test_one_event_one_page.py
"""
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import retarget_event_links as RL  # noqa: E402

BARE = re.compile(r"^[A-Z][A-Z0-9.]{0,6}$")


def rows():
    src = io.open(RL.DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    out, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return out


def clean(u):
    return str(u or "").split("#")[0].split("?")[0].rstrip("/")


def main():
    plant = os.environ.get("PLANT", "")
    bad = []
    today = RL.today_et()
    tg = RL.targets()
    cfg = json.load(io.open(RL.VJ, encoding="utf-8"))
    red = {str(r.get("source")): r for r in cfg.get("redirects", []) if str(r.get("source", "")).startswith("/pdufa/")}

    data = rows()
    row_urls = {clean(r.get("url")) for r in data}
    up, history = {}, {}
    for r in data:
        if r.get("type") != "PDUFA" or not r.get("t"):
            continue
        t = str(r["t"]).upper()
        st = str(r.get("st", "")).lower()
        if st not in ("decided", "withdrawn") and str(r.get("d", "")) >= today:
            up.setdefault(t, []).append(clean(r.get("url")))
        else:
            history.setdefault(t, []).append(r)

    bare_dirs = sorted(d for d in os.listdir(os.path.join(SITE, "pdufa")) if BARE.match(d))
    bare_pages = {d: os.path.join(SITE, "pdufa", d, "index.html") for d in bare_dirs
                  if os.path.exists(os.path.join(SITE, "pdufa", d, "index.html"))}

    # the tickers rule 5 retires: one upcoming PDUFA with its own page, nothing decided or withdrawn, no row on /pdufa/T
    # (the builder also reads past decisions from /decisions; the index page itself shows what it found, below)
    sole = {}
    for t, urls in up.items():
        own = [u for u in urls if re.match(r"^/pdufa/[A-Za-z0-9.\-]+$", u) and u != f"/pdufa/{t}" and RL.exists(u)]
        if len(urls) == 1 and own and not history.get(t) and f"/pdufa/{t}" not in row_urls:
            sole[t] = own[0]
    planted = set()
    retired = sorted(t for t in sole if f"/pdufa/{t}" in red and not RL.exists(f"/pdufa/{t}"))
    if plant == "dupe" and retired:
        t = retired[0]
        # its event page, copied to where the bare page would be (a temp file: nothing on the site changes)
        import tempfile
        tmp = os.path.join(tempfile.mkdtemp(), "index.html")
        io.open(tmp, "w", encoding="utf-8").write(io.open(os.path.join(SITE, *sole[t].strip("/").split("/"),
                                                                        "index.html"), encoding="utf-8").read())
        bare_pages[t] = tmp
        planted.add("dupe")

    def toks(x, t):
        return {w for w in re.findall(r"[a-z0-9]+", x.lower()) if len(w) >= 3 and w != t.lower()
                and w not in ("pdufa", "date", "fda", "decision", "approved", "the", "and", "with", "plus")}

    n_index = 0
    for t, p in sorted(bare_pages.items()):
        url = f"/pdufa/{t}"
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        h1 = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""
        is_index = h1 == f"{t} FDA decision dates"
        noindex = bool(re.search(r'<meta name="robots" content="noindex', doc))
        if not is_index:
            # 1. an indexable bare event page must not have an indexable drug-slug twin for the same drug
            if noindex:
                continue
            for d in sorted(os.listdir(os.path.join(SITE, "pdufa"))):
                if not d.startswith(t + "-"):
                    continue
                q = os.path.join(SITE, "pdufa", d, "index.html")
                if not os.path.exists(q) or os.path.abspath(q) == os.path.abspath(p):
                    continue
                tw = io.open(q, encoding="utf-8", errors="replace").read()
                if re.search(r'<meta name="robots" content="noindex', tw):
                    continue
                if toks(h1, t) & toks(d[len(t) + 1:].replace("-", " "), t):
                    bad.append(f"{url} and /pdufa/{d}: two indexable pages for one {t} event ('{h1[:50]}'); "
                               "redirect or canonicalise one (canonicalise_duplicate_event_pages.py DUPES)")
            continue
        n_index += 1
        # 3. an index that lists one upcoming event and nothing else should have been that event's redirect
        rws = re.findall(r'<a class="row" href="([^"]+)"', doc)
        if len(rws) == 1 and rws[0].startswith("/pdufa/") and url not in row_urls and t in up:
            bad.append(f"{url}: lists only {rws[0]}; it should be a permanent redirect there "
                       "(python build_pdufa_ticker_index.py)")
        # 2.
        if plant == "index" and "index" not in planted:
            m = re.search(r'href="/pdufa/[A-Za-z0-9.]+-[a-z0-9\-]+"', doc)
            if m:
                doc = doc.replace(m.group(0), 'href="/calendar"', 1)
                planted.add("index")
        links = set(re.findall(r'href="(?:https://www\.pdufa\.bio)?(/pdufa/[A-Za-z0-9.\-]+)"', doc))
        for u in up.get(t, []):
            if u != url and RL.exists(u) and u.startswith("/pdufa/") and u not in links:
                bad.append(f"{url}: the index does not link {t}'s upcoming decision page {u}")

    # 3b + 4. the redirects
    sm_path = os.path.join(SITE, "sitemap.xml")
    sm = io.open(sm_path, encoding="utf-8", errors="replace").read() if os.path.exists(sm_path) else ""
    if plant == "sitemap" and retired:
        src = f"/pdufa/{retired[0]}"
        sm = sm.replace("</urlset>", f"<url><loc>{RL.BASE}{src}</loc></url></urlset>")
        planted.add("sitemap")
    locs = set(re.findall(r"<loc>https://www\.pdufa\.bio([^<]*)</loc>", sm))
    for t, own in sole.items():
        r = red.get(f"/pdufa/{t}")
        if f"/pdufa/{t}" in row_urls or RL.exists(f"/pdufa/{t}"):
            continue   # a bare page that stayed is an index with a past decision on it (check 3 reads it)
        if not r or clean(r.get("destination")) != own or r.get("permanent") is not True:
            bad.append(f"/pdufa/{t}: no permanent redirect to {own} in vercel.json")
    for src, r in sorted(red.items()):
        if not re.match(r"^/pdufa/[A-Za-z0-9.\-]+$", src):
            continue
        if src not in tg:
            bad.append(f"vercel.json: {src} redirects to {r.get('destination')}, which (followed to its end) is no page "
                       "of this site")
            continue
        fake = plant == "file" and retired and src == f"/pdufa/{retired[0]}"
        if fake:
            planted.add("file")
        if RL.exists(src) or fake:
            bad.append(f"{src}: redirected in vercel.json, but its page file is still built (the redirect hides it)")
        if src in locs:
            bad.append(f"sitemap.xml lists {src}, which redirects to {tg[src]}")

    # 5. every link at its retargeted state
    n_pages = 0
    for p in RL.pages():
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        if plant == "link" and rel == "index.html":
            src = f"/pdufa/{retired[0]}" if retired else None
            if src:
                doc = doc.replace("</body>", f'<a href="{src}">x</a></body>', 1)
                planted.add("link")
        n_pages += 1
        new = RL.apply(doc, rel, tg)
        if new != doc:
            a = re.findall(r'href="[^"]*"', doc)
            b = re.findall(r'href="[^"]*"', new)
            diff = next((f"{x} -> {y}" for x, y in zip(a, b) if x != y), "a JSON-LD URL")
            bad.append(f"/{rel}: links an event by a URL that is not its page ({diff}); "
                       "python retarget_event_links.py")

    # 8. every ticker index is linked from some page other than itself and the HTML sitemap
    index_urls = set()
    for t, p in bare_pages.items():
        if p.startswith(os.path.join(SITE, "")) and f"<h1>{t} FDA decision dates</h1>" in \
                io.open(p, encoding="utf-8", errors="replace").read():
            index_urls.add(f"/pdufa/{t}")
    inbound = {u: 0 for u in index_urls}
    orphan = sorted(index_urls)[0] if (plant == "orphan" and index_urls) else None
    for p in RL.pages():
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        if rel == "sitemap/index.html":
            continue
        own = "/" + rel[:-len("/index.html")] if rel.endswith("/index.html") else None
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        for u in set(re.findall(r'href="(?:https://www\.pdufa\.bio)?(/pdufa/[A-Z][A-Z0-9.]{0,6})/?["#?]', doc)):
            if u in inbound and u != own and u != orphan:
                inbound[u] += 1
    if orphan:
        planted.add("orphan")
    for u, n in sorted(inbound.items()):
        if not n:
            bad.append(f"{u}: the ticker's index is linked from no page but the HTML sitemap")

    # 9. the homepage board links each upcoming event's own page
    by_day = {}
    for r in data:
        if r.get("type") == "PDUFA" and r.get("t"):
            u = clean(r.get("url"))
            if re.match(r"^/pdufa/[A-Za-z0-9.\-]+$", u) and u != f"/pdufa/{str(r['t']).upper()}" and RL.exists(u):
                by_day.setdefault((str(r["t"]).upper(), str(r.get("d", ""))[:10]), set()).add(u)
    home = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    if "Next FDA decisions" in home and "Recently decided" in home:
        board = home[home.index("Next FDA decisions"):home.index("Recently decided")]
        if plant == "board":
            m = re.search(r'<a class="row" href="/pdufa/([A-Z][A-Z0-9.]{0,6})-[^"]+"', board)
            if m:
                board = board.replace(m.group(0), f'<a class="row" href="/pdufa/{m.group(1)}"', 1)
                planted.add("board")
        for m in re.finditer(r'<a class="row" href="([^"]+)">(.*?)</a>', board, re.S):
            tm = re.search(r'<span class="tk">([A-Z][A-Z0-9.]{0,6})\b', m.group(2))
            dm = re.search(r"PDUFA (\d{4}-\d{2}-\d{2})", m.group(2))
            if not (tm and dm):
                continue
            want = by_day.get((tm.group(1), dm.group(1)), set())
            if len(want) == 1 and clean(m.group(1)) not in want:
                bad.append(f"homepage board: the {tm.group(1)} {dm.group(1)} tile links {m.group(1)}, not the event's "
                           f"page {next(iter(want))} (python build_home_board.py)")

    # 6. the dossier sits on the event page
    for pf in sorted(glob.glob(os.path.join(HERE, "retail_profiles", "*.json"))):
        prof = json.load(io.open(pf, encoding="utf-8"))
        ev = prof.get("event_page")
        if not ev:
            continue
        t = os.path.splitext(os.path.basename(pf))[0]
        hub = os.path.join(SITE, "ticker", t, "index.html")
        hubdoc = io.open(hub, encoding="utf-8", errors="replace").read() if os.path.exists(hub) else ""
        evdoc = (io.open(os.path.join(SITE, *ev.strip("/").split("/"), "index.html"), encoding="utf-8",
                         errors="replace").read() if RL.exists(ev) else "")
        if "<!--DEEPDIVE" not in evdoc:
            bad.append(f"{ev}: {t}'s dossier is not on its event page")
        if "What the data showed" in hubdoc:
            bad.append(f"/ticker/{t}: carries {t}'s full dossier, which belongs on {ev}")

    # 7. wiring
    wf = io.open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    a, b, c = (wf.find("python inject_site_links.py"), wf.find("python retarget_event_links.py"),
               wf.find("python build_sitemap.py", wf.find("python inject_site_links.py")))
    if not (0 <= a < b < c):
        bad.append("the workflow does not run retarget_event_links.py after inject_site_links.py and before "
                   "build_sitemap.py")
    chain = io.open(os.path.join(HERE, "_chain_0919.bat"), encoding="utf-8", errors="replace").read()
    if not re.search(r" inject_site_links\.py (?:\S+\.py )*?retarget_event_links\.py (?:\S+\.py )*?\"build_sitemap", chain):
        bad.append("_chain_0919.bat does not run retarget_event_links.py between inject_site_links.py and the sitemap")
    q = io.open(os.path.join(HERE, "quarantine_leads.py"), encoding="utf-8").read()
    if "retarget_event_links" not in q or "_event_links[0](old, rel)" not in q:
        bad.append("quarantine_leads.py restores committed pages without retargeting their event links")

    for want in ("link", "dupe", "file", "index", "sitemap", "orphan", "board"):
        if plant == want and want not in planted:
            bad.append(f"PLANT={plant} found nothing to plant on")
    print(f"{len(bare_pages)} bare /pdufa/ page(s), {n_index} ticker index(es); {len(sole)} sole-event ticker(s) "
          f"redirected; {len(tg)} /pdufa/ URL(s) retargeted; {n_pages} page(s) checked")
    if bad:
        for x in bad[:30]:
            print("  FAIL " + x)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python build_pdufa_ticker_index.py && python retarget_event_links.py && python build_sitemap.py")
        sys.exit(1)
    print("  PASS: one page per event, every bare duplicate redirected, every event link lands on the event's page")


if __name__ == "__main__":
    main()
