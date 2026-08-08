# -*- coding: utf-8 -*-
"""test_freshness_crawlable.py -- the recency signal has to be in the HTML, not in JavaScript.

We are #3 on Bing, and Bing shows recency in the result. The site that took #1 leads with an hour
stamp; ours showed nothing, because the first version of the freshness stamp rendered the date
client-side from /build-info.json. That is fine for a human and worthless for a crawler, which is
the audience the signal exists for.

The fix was to bake a real <time datetime> into every indexable page. This guards the two ways that
can silently regress:

  1. Back to JS-only, so the date disappears from the served HTML and nobody notices because the
     page still looks right in a browser.
  2. Back to the BUILD time instead of the CONTENT-CHANGE date. That is the failure mode this
     codebase keeps rediscovering: a date that advances every night regardless of whether anything
     changed is a false freshness claim, it retrains Google to ignore our lastmod, and it commits
     850 files a day. The date must come from _sitemap_lastmod.json, so this cross-checks it there
     rather than trusting the page.
"""
import glob, json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STATE = os.path.join(HERE, "_sitemap_lastmod.json")
NOINDEX = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)
FRESH = re.compile(r"<!--FRESH:BEGIN-->(.*?)<!--FRESH:END-->", re.S)
TIME = re.compile(r'<time datetime="(\d{4}-\d{2}-\d{2})"')


def main():
    try:
        state = {k: v.get("date") for k, v in json.load(open(STATE, encoding="utf-8")).items()}
    except Exception:
        print("  SKIP: no _sitemap_lastmod.json yet"); return 0

    # Same clock as the builder: UTC.
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    missing, wrong, future = [], [], []
    checked = 0

    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = open(p, encoding="utf-8", errors="replace").read()
        m = FRESH.search(doc)
        if not m or NOINDEX.search(doc[:4000]):
            continue
        rel = "pdufa_site_src/" + os.path.relpath(p, SITE).replace("\\", "/")
        expected = state.get(rel)
        if expected is None:
            continue
        checked += 1

        t = TIME.search(m.group(1))
        if not t:
            missing.append(rel)
        elif t.group(1) > today:
            future.append((rel, t.group(1)))
        elif t.group(1) != expected:
            wrong.append((rel, t.group(1), expected))

    if missing or wrong or future:
        print("FAIL: the freshness stamp is not a trustworthy crawler-visible date.")
        if missing:
            print(f"   {len(missing)} indexable page(s) have no <time datetime> in the stamp, so a")
            print( "   crawler sees no date at all. Regressed to JavaScript-only rendering?")
            for r in missing[:5]:
                print(f"      {r}")
        if wrong:
            print(f"   {len(wrong)} page(s) show a date that is not their content-change date.")
            print( "   If these all say today, the stamp is printing the BUILD time again.")
            for r, got, exp in wrong[:5]:
                print(f"      {r}: shows {got}, content changed {exp}")
        if future:
            print(f"   {len(future)} page(s) claim a future date.")
            for r, got in future[:5]:
                print(f"      {r}: {got}")
        return 1

    print(f"  PASS: {checked} indexable page(s) carry a crawler-visible date matching their "
          f"real content-change date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
