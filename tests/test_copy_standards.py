# -*- coding: utf-8 -*-
"""test_copy_standards.py -- house-style and legal-footer guard.

Two things that are easy to get right once and then lose silently on the next rebuild:

  1. No em/en dashes used as punctuation in published copy. They are the loudest machine-written
     tell in prose and the site is meant to read like it was written by a person.
  2. Every published page names the operating entity and disclaims FDA affiliation. This is the
     footer's whole job: a reader landing on any single page should be able to tell who publishes
     the site and that it has nothing to do with the FDA.

Hard-fails, so a regression blocks the deploy rather than shipping and being noticed later.

    python tests/test_copy_standards.py
"""
import os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

# Not live routes: scratch copies, backups, the maintenance holding page.
SKIP_FILES = {"index_redesign.html", "preview.html", "ping.html", "holding.html", "app.html"}
SKIP_DIRS = ("_pdufa_bak8", "_pdufa_xbak")

# Dashes inside <script> are code comments or JS-hydrated placeholders, not reader-facing prose.
SCRIPT = re.compile(
    r"<script\b(?![^>]*ld\+json).*?</script>"
    r"|<style\b.*?</style>"
    # loading placeholders that JavaScript replaces on hydration (never seen as prose)
    r"|<(?:b|span|div|td)[^>]*id=\"(?:asof|cnt)\"[^>]*>.*?</(?:b|span|div|td)>",
    re.S | re.I)
DASH = re.compile(r"&mdash;|&ndash;|[—–]")

REQUIRED = ["Odin Catalyst LLC", "Not affiliated"]


def pages():
    for root, _, fs in os.walk(SITE):
        if any(s in root for s in SKIP_DIRS):
            continue
        for f in fs:
            if f.endswith(".html") and not f.startswith("_") and f not in SKIP_FILES:
                yield os.path.join(root, f)


def main():
    dash_hits, missing = [], []
    n = 0
    for p in pages():
        n += 1
        html = open(p, encoding="utf-8", errors="replace").read()
        prose = SCRIPT.sub(" ", html)
        for m in DASH.finditer(prose):
            dash_hits.append((p, re.sub(r"\s+", " ", prose[max(0, m.start() - 60):m.start() + 50])))
        for need in REQUIRED:
            if need not in html:
                missing.append((p, need))
                break

    print(f"checked {n:,} published pages")
    ok = True
    if dash_hits:
        ok = False
        print(f"\nFAIL: {len(dash_hits)} em/en dash(es) used as punctuation, in "
              f"{len({p for p, _ in dash_hits})} file(s):")
        for p, ctx in dash_hits[:15]:
            print(f"   {os.path.relpath(p, HERE)}\n      {ctx}")
        if len(dash_hits) > 15:
            print(f"   ... and {len(dash_hits) - 15} more")
        print("   fix: python strip_dashes.py   (and strip_dashes_generators.py if a template emits it)")
    else:
        print("  PASS: no em/en dashes in published prose")

    if missing:
        ok = False
        print(f"\nFAIL: {len(missing)} page(s) missing required legal footer text:")
        for p, need in missing[:15]:
            print(f"   {os.path.relpath(p, HERE)}  (missing: {need!r})")
        if len(missing) > 15:
            print(f"   ... and {len(missing) - 15} more")
        print("   fix: python apply_legal_footer.py")
    else:
        print("  PASS: every page names Odin Catalyst LLC and disclaims FDA affiliation")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
