# -*- coding: utf-8 -*-
"""test_home_first_screen.py -- the homepage opens on its data: one sentence, one stamp, one list of each.

Design red team 2026-11-18 (change 8). Above its first date the homepage stacked three freshness stamps ("Data through
Nov 18", "Page updated November 18, 2026", "Data as of Nov 18, 2026 3:12 AM ET"), two intro paragraphs and two
buttons. Below them it listed the next decisions twice, and the two lists disagreed: the cards dropped Roche's
giredestrant (lidERA, goal Nov 30), which /calendar and the second list showed, because an approval of the same drug
for another use (Wilserdly, Nov 16) read as its outcome. It listed recent decisions twice, repeated its footer links,
said "18 upcoming" over month chips that summed to 16 (two of the 18 were unsourced "Q4 2026 (est.)" rows) and could
print "-0%". This fails if:

  1. the hero (eyebrow to the first list) shows more than one date stamp, "Page updated" or a visible "Data as of",
     a lede of more than one sentence, the tagline paragraph or the button row;
  2. the homepage carries the LINKHUB block, or its SITELINKS more than once;
  3. an open goal in the dataset dated between today and the day before the last card has no card, a card names a
     ticker and day (or, for a window card, a month or quarter goal) the dataset holds as no open goal, a card shows
     an "(est.)" date, or a card links a ticker page when the goal has its own event page;
  4. a decided card prints "-0%";
  5. the "upcoming PDUFAs" tile differs from the sum of this year's month chips;
  6. cmdk.js does not step aside for a page's own search box;
  7. inject_site_links.py (SITELINKS, RELATED, /sitemap) does not run.
A second stamp is allowed only when the eyebrow says the rows are stale ("Data through ...").

PLANT=stamp adds a second stamp, PLANT=card drops a card, PLANT=chips adds 1 to the tile; each must FAIL.

    python tests/test_home_first_screen.py
"""
import html
import io
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

DAY = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?!\d)|\b\d{4}-\d{2}-\d{2}\b")


def visible(seg):
    seg = re.sub(r"<script\b.*?</script>", " ", seg, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg)))


def main():
    doc = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    plant = os.environ.get("PLANT", "")
    if plant == "stamp":
        doc = doc.replace("<!--FRESH:END-->", "<!--FRESH:END--><span>Page updated Nov 18, 2026</span>", 1)
    if plant == "card":
        doc = re.sub(r'<a class="row" href="/pdufa/[^"]+">.*?</a>', "", doc, count=1, flags=re.S)
    if plant == "chips":
        doc = re.sub(r'(<span class="stat gld"><b>)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 1), doc, count=1)
    bad = []
    today = eastern_today().isoformat()

    # 1. the hero
    a, b = doc.find('<div class="eyebrow">'), doc.find('<div class="list">')
    hero = doc[a:b]
    text = visible(hero)
    stamps = DAY.findall(text)
    # one stamp; a second only when the eyebrow says the rows are stale ("Data through Nov 9 · free, no login")
    allowed = 2 if "Data through" in text else 1
    if not 1 <= len(stamps) <= allowed:
        bad.append(f"home: the hero shows {len(stamps)} date stamp(s) ({', '.join(stamps)}); it should show one")
    for phrase in ("Page updated", "Data as of"):
        if phrase in text:
            bad.append(f"home: the hero still shows '{phrase}'")
    if re.search(r"textContent\s*=\s*['\"](?:Data as of|Page updated)", hero):
        bad.append("home: a script writes a visible 'Data as of' / 'Page updated' stamp into the hero")
    lede = re.search(r"<!--LEDE:BEGIN-->(.*?)<!--LEDE:END-->", doc, re.S)
    if not lede or re.search(r"[.!?;]\s+\S", visible(lede.group(1)).strip()):
        bad.append("home: the lede is missing or runs past one sentence")
    if re.search(r'<p class="lede[" ]|<div class="cta[" ]', hero):
        bad.append("home: the tagline paragraph or the button row is back above the lists")

    # 2. one list of each
    if "<!--LINKHUB:BEGIN-->" in doc or re.search(r">\s*(?:Next FDA decision dates|Latest FDA decisions)\s*<", doc):
        bad.append("home: the LINKHUB block lists the next and latest decisions a second time")
    if doc.count("<!--SITELINKS:BEGIN-->") > 1:
        bad.append("home: SITELINKS appears more than once")

    # 3. the cards against the dataset
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    # every goal the dataset holds open, including one past its date and awaiting the FDA (the board shows those for
    # ten days); only the ones still ahead must each have a card
    pend = [r for r in rows if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting")]
    open_ = [r for r in pend if str(r.get("d") or "") >= today]
    lst = doc[b:doc.find("</div>", b)]
    cards = []
    for m in re.finditer(r'<a class="row" href="([^"]+)">.*?<span class="tk">([A-Z.]+)\s.*?<span class="dg">(.*?)</span>',
                         lst, re.S):
        day = re.search(r"PDUFA (\d{4}-\d{2}-\d{2})", m.group(3))
        cards.append((m.group(1), m.group(2), day.group(1) if day else None))
        if re.search(r"\(est\.?\)", m.group(3), re.I):
            bad.append(f"home: the card {m.group(2)} shows an unsourced (est.) date")
    if not cards:
        bad.append("home: no Next FDA decisions cards")
    days = [d for _h, _t, d in cards if d]
    last = max(days) if days else today
    have = {(t, d) for _h, t, d in cards}
    for r in open_:
        d = str(r["d"])[:10]
        if d < last and (r["t"], d) not in have and not any(t == r["t"] and dd is None for _h, t, dd in cards):
            bad.append(f"home: {r['t']} {d} ({str(r.get('name'))[:40]}) is an open goal before the last card, with no card")
    for href, t, d in cards:
        if d is None:
            # a window card ("PDUFA window Nov 2026"): the ticker must hold an open goal given only as a month or quarter
            match = [r for r in pend if r.get("t") == t and str(r.get("dp") or "day") != "day"]
            if not match:
                bad.append(f"home: the window card {t} matches no open month or quarter goal in the dataset")
                continue
        else:
            match = [r for r in pend if r.get("t") == t and str(r["d"])[:10] == d]
        if not match:
            bad.append(f"home: the card {t} {d} matches no open goal in the dataset")
            continue
        own = {str(r.get("url") or "") for r in match if str(r.get("url") or "").startswith("/pdufa/")
               and os.path.exists(os.path.join(SITE, *str(r["url"]).strip("/").split("/"), "index.html"))}
        if own and href not in own:
            bad.append(f"home: the card {t} {d} links {href}, not the goal's own page {sorted(own)[0]}")

    # 4. no "-0%"
    if re.search(r"(?<![\d.])-0(?:\.0+)?%", visible(doc)):
        bad.append("home: a decided card prints -0%")

    # 5. the tile against the chips
    tile = re.search(r'<span class="stat gld"><b>([\d,]+)</b><span>upcoming', doc)
    chips = sum(int(n) for n in re.findall(r'<a class="chip" href="/calendar/' + today[:4] + r'/[a-z]+">[A-Za-z]+ \d{4} '
                                            r'<b>(\d+)</b></a>', doc))
    if not tile or int(tile.group(1).replace(",", "")) != chips:
        bad.append(f"home: the tile says {tile.group(1) if tile else 'nothing'} upcoming, this year's month chips sum "
                   f"to {chips}")

    # 6. one search at a time
    js = io.open(os.path.join(SITE, "cmdk.js"), encoding="utf-8", errors="replace").read()
    if "getElementById('pdq')" not in js or "IntersectionObserver" not in js:
        bad.append("cmdk.js: the floating search button does not step aside for the page's own search box")

    # 7. the writer that used to add LINKHUB still runs (it also writes SITELINKS, RELATED and /sitemap)
    r = subprocess.run([sys.executable, os.path.join(HERE, "inject_site_links.py"), "--dry-run"], capture_output=True,
                       text=True, cwd=HERE)
    if r.returncode != 0:
        bad.append("inject_site_links.py --dry-run fails: " + (r.stderr.strip().splitlines() or ["?"])[-1])

    print(f"home: {len(cards)} next-decision card(s), tile {tile.group(1) if tile else '?'}, chips {chips}")
    if bad:
        for x in bad[:30]:
            print("  FAIL " + x)
        print("  fix: python build_home_board.py && python build_hub_lede.py && python sync_home_event_schema.py && "
              "python inject_site_links.py && python build_freshness_stamp.py")
        sys.exit(1)
    print("  PASS: one sentence, one stamp, one list of next decisions and one of recent ones, and the count matches")


if __name__ == "__main__":
    main()
