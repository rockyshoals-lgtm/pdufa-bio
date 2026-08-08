# -*- coding: utf-8 -*-
"""test_meta_lengths.py -- titles and descriptions must fit in a search result, and read like prose.

Bing Webmaster Tools inspected /sls and returned two errors: "Title too long" and "Meta Description
too long or too short". They were not one page's problem. 264 of 473 indexable pages had a
description over 160 characters and 188 had a title over 65, and nothing caught it because the only
SEO guard we had checks that titles do not advertise a score. A limit with no test drifts.

What this enforces, and why each one is here:

  * LENGTH. Over 160 characters and the end is cut off in the result, so the part meant to earn the
    click is the part nobody reads.
  * NO MID-SENTENCE ENDING. The first repair pass trimmed to a character budget and produced
    "...and the run-up we" and "...with dates, locations, and presenting". A summary that stops
    mid-phrase reads as a broken page.
  * BALANCED PARENTHESES. Six pages shipped as "Learn the common reasons (efficacy, safety." long
    before today. Under the length limit, so nothing flagged them, and an unclosed bracket in a
    search result looks like the site is malfunctioning.
  * NO LOWERCASE AFTER A FULL STOP, abbreviations excepted. Catches a clause assembled onto the end
    of a sentence without being capitalised, which happened when an optional clause was dropped.

Titles are held to 100, not Bing's 65. Several pages sit just over 65 and rewriting the title of a
page that already ranks is the edit most likely to lose ground; 100 catches only the indefensible
ones, like the 140-character decision titles.
"""
import glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STATE = os.path.join(HERE, "_sitemap_lastmod.json")

DESC_MAX, DESC_MIN, TITLE_MAX = 160, 70, 100
D = re.compile(r'<meta name="description" content="([^"]*)"', re.I)
T = re.compile(r"<title[^>]*>(.*?)</title>", re.S)
ABBR = re.compile(r"\b(?:Eur|Assoc|Inc|Ltd|Co|Corp|St|Dr|No|vs|approx|Univ|Soc|Am|Natl|Intl|Jr|Sr"
                  r"|etc|e\.g|i\.e|U\.S|Fig|No)\.\s+[a-z]", re.I)


def main():
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        print("  SKIP: no _sitemap_lastmod.json"); return 0

    bad = []
    checked = 0
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        rel = "pdufa_site_src/" + os.path.relpath(p, SITE).replace("\\", "/")
        if rel not in state:
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        checked += 1
        short = rel.replace("pdufa_site_src", "")

        tm = T.search(doc)
        if tm:
            t = html.unescape(re.sub(r"\s+", " ", tm.group(1))).strip()
            if len(t) > TITLE_MAX:
                bad.append((short, f"title {len(t)} chars (max {TITLE_MAX})"))

        dm = D.search(doc)
        if not dm:
            bad.append((short, "no meta description")); continue
        s = html.unescape(dm.group(1))

        if len(s) > DESC_MAX:
            bad.append((short, f"description {len(s)} chars (max {DESC_MAX})"))
        elif len(s) < DESC_MIN:
            bad.append((short, f"description only {len(s)} chars (min {DESC_MIN})"))
        elif not s.rstrip().endswith((".", "!", "?")):
            bad.append((short, f"ends mid-sentence: ...{s[-40:]!r}"))
        elif s.count("(") != s.count(")"):
            bad.append((short, f"unbalanced parentheses: ...{s[-40:]!r}"))
        else:
            for m in re.finditer(r"\.\s+[a-z]", s):
                if not ABBR.search(s[max(0, m.start() - 12):m.end()]):
                    bad.append((short, f"lowercase after full stop: {s[max(0,m.start()-25):m.end()+12]!r}"))
                    break

    if bad:
        print(f"FAIL: {len(bad)} page(s) have a title or description a search engine will mangle.")
        for r, why in bad[:20]:
            print(f"   {r}: {why}")
        if len(bad) > 20:
            print(f"   ... and {len(bad) - 20} more")
        print("\n   Run fix_meta_lengths.py. It rebuilds ticker and decision pages from data and")
        print("   trims the hand-written ones at a sentence boundary.")
        return 1

    print(f"  PASS: {checked} page(s) have titles under {TITLE_MAX} and descriptions of "
          f"{DESC_MIN}-{DESC_MAX} chars that end cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
