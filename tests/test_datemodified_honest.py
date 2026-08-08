# -*- coding: utf-8 -*-
"""test_datemodified_honest.py -- a page may date itself and nothing else.

We publish schema.org dateModified so search engines print a timestamp beside our result. The first
version of the generator stamped every page-type node it found, and on /calendar that meant 14
nested ListItem entries describing OTHER urls. The page was telling Google that /pdufa/NVO-am833
and thirteen more had been modified on the calendar's change date. A listing page knows when it
changed; it cannot know when the pages it links to changed. That is a fabricated fact about
fourteen other pages, published in machine-readable form, on a site whose whole claim is
traceability.

Three checks:

  1. NO NODE DATES A URL THAT IS NOT THE PAGE'S OWN CANONICAL. This is the bug above.
  2. NO FUTURE DATES. A page claiming tomorrow discredits every other date we publish.
  3. THE SCHEMA DATE MATCHES THE VISIBLE DATE AND THE SITEMAP. All three read from the same
     content-change state, so a divergence means one of them has started using the build clock,
     which is the failure this codebase keeps rediscovering.
"""
import datetime as dt
import glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STATE = os.path.join(HERE, "_sitemap_lastmod.json")
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
CANON = re.compile(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"')


def norm(u):
    return re.sub(r"/+$", "", str(u or "").strip().lower())


def walk(o, out):
    if isinstance(o, list):
        for x in o:
            walk(x, out)
        return
    if isinstance(o, dict):
        if "dateModified" in o:
            out.append((o.get("url") or o.get("@id"), o["dateModified"]))
        for v in o.values():
            walk(v, out)


def main():
    try:
        state = {k: v.get("date") for k, v in json.load(open(STATE, encoding="utf-8")).items()}
    except Exception:
        print("  SKIP: no _sitemap_lastmod.json"); return 0

    today = dt.date.today().isoformat()
    foreign, future, mismatch = [], [], []
    checked = 0

    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = open(p, encoding="utf-8", errors="replace").read()
        if "dateModified" not in doc:
            continue
        cm = CANON.search(doc)
        if not cm:
            continue
        rel = "pdufa_site_src/" + os.path.relpath(p, SITE).replace("\\", "/")
        canon = cm.group(1)
        checked += 1

        for m in LD.finditer(doc):
            found = []
            try:
                walk(json.loads(m.group(1)), found)
            except Exception:
                continue
            for url, d in found:
                if url and norm(url) != norm(canon):
                    foreign.append((rel, url))
                if str(d)[:10] > today:
                    future.append((rel, d))
                elif state.get(rel) and str(d)[:10] != state[rel] and (
                        not url or norm(url) == norm(canon)):
                    mismatch.append((rel, d, state[rel]))

    if foreign or future or mismatch:
        print("FAIL: dateModified is making claims we cannot support.")
        if foreign:
            print(f"   {len(foreign)} node(s) date a URL that is not the page's own canonical.")
            print( "   A listing page cannot know when the pages it links to changed.")
            for r, u in foreign[:5]:
                print(f"      {r} dates {u}")
        if future:
            print(f"   {len(future)} node(s) claim a future date.")
            for r, d in future[:5]:
                print(f"      {r}: {d}")
        if mismatch:
            print(f"   {len(mismatch)} page(s) disagree with their own content-change date.")
            print( "   If these all say today, something switched to the build clock.")
            for r, got, exp in mismatch[:5]:
                print(f"      {r}: schema {got}, content changed {exp}")
        return 1

    print(f"  PASS: {checked} page(s) date only themselves, none in the future, all matching "
          f"their content-change date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
