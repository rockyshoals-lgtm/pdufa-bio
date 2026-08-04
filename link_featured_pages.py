# -*- coding: utf-8 -*-
"""link_featured_pages.py -- stop the deep-dive pages being orphans.

/vktx was built, deployed, and listed in the sitemap, and then nothing on the site linked to it.
The owner's reaction was "I didn't see anything on Viking Therapeutics", which is the correct
reaction: a page no page links to effectively does not exist. Google treats an orphan as low value
regardless of how good it is, and a reader has no path to it at all.

There are two separate holes, and this closes both:

  1. /ticker/VKTX returned 404 while 208 other tickers had hubs. Anyone guessing the URL, and any
     inbound link built on the obvious pattern, hit nothing. Fixed with a 301 to the deep dive, so
     the deep dive keeps the authority instead of splitting it across two URLs.
  2. /tickers listed every hub except the featured deep dives. Fixed by inserting them in the index
     in alphabetical position, pointing at the deep dive rather than a thin hub.

Runs after the ticker-hub generator so a regeneration cannot silently re-orphan these pages.

    python link_featured_pages.py [--dry-run]
"""
import argparse, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TICKERS = os.path.join(SITE, "tickers", "index.html")
VERCEL = os.path.join(SITE, "vercel.json")

# ticker -> (deep-dive path, label shown in the index)
FEATURED = {
    "VKTX": ("/vktx", "Viking Therapeutics"),
    "SLS":  ("/sls",  "SELLAS Life Sciences"),
}


def ensure_redirects(dry):
    """/ticker/<T> should not 404 when a deep dive exists. 301 so link equity lands on one URL."""
    if not os.path.exists(VERCEL):
        print("  note: vercel.json missing"); return 0
    cfg = json.load(open(VERCEL, encoding="utf-8"))
    reds = cfg.setdefault("redirects", [])
    have = {r.get("source") for r in reds}
    added = 0
    for tick, (path, _) in FEATURED.items():
        src = f"/ticker/{tick}"
        if src in have:
            continue
        if os.path.isdir(os.path.join(SITE, "ticker", tick)):
            continue                      # a real hub exists; leave it alone
        reds.append({"source": src, "destination": path, "permanent": True})
        added += 1
        print(f"  redirect {src} -> {path} (301)")
    if added and not dry:
        json.dump(cfg, open(VERCEL, "w", encoding="utf-8"), indent=1)
    return added


def ensure_index_links(dry):
    """Insert featured pages into /tickers in alphabetical position."""
    if not os.path.exists(TICKERS):
        print("  note: /tickers page missing"); return 0
    html = open(TICKERS, encoding="utf-8", errors="replace").read()

    # Learn the row's CSS classes so the inserted row inherits current styling, but build its
    # CONTENT ourselves.
    #
    # The first version of this cloned the donor row's inner HTML and swapped the ticker. That
    # silently copied the donor's data too, so VKTX shipped claiming "1 decision on record" purely
    # because the alphabetically-first hub said so. It looked completely normal. Copying markup is
    # fine; copying a neighbour's facts is how a site that promises traceable data starts asserting
    # things no source supports.
    m = re.search(r'<a\s+class="([^"]*)"\s+href="/ticker/[A-Z.\-]+"', html)
    row_cls = m.group(1) if m else "trow"
    tk_cls = "tk" if 'class="tk"' in html else ""
    tm_cls = "tm" if 'class="tm"' in html else ""
    cn_cls = "cn" if 'class="cn"' in html else ""
    dd_cls = "dd" if 'class="dd"' in html else ""

    added = 0
    for tick, (path, label) in sorted(FEATURED.items()):
        if f'href="{path}"' in html:
            continue
        # "Deep dive" is a claim about our own page, which we can always support. No counts.
        row = (f'<a class="{row_cls}" href="{path}">'
               f'<span class="{tk_cls}">{tick}</span>'
               f'<span class="{tm_cls}"><span class="{cn_cls}">{label}</span>'
               f'<span class="{dd_cls}">Deep dive</span></span></a>')
        # Alphabetical: sit in front of the first hub that sorts after us.
        anchor = None
        for mm in re.finditer(r'<a\s+[^>]*href="/ticker/([A-Z.\-]+)"', html):
            if mm.group(1) > tick:
                anchor = mm.start(); break
        if anchor is None:
            print(f"  note: no insertion point for {tick}"); continue
        html = html[:anchor] + row + html[anchor:]
        added += 1
        print(f"  /tickers now links {tick} -> {path}")

    if added and not dry:
        open(TICKERS, "w", encoding="utf-8").write(html)
    return added


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = ensure_redirects(a.dry_run)
    i = ensure_index_links(a.dry_run)
    if not r and not i:
        print("featured pages already linked; nothing to do")
    elif a.dry_run:
        print("dry-run: nothing written")


if __name__ == "__main__":
    main()
