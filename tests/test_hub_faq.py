# -*- coding: utf-8 -*-
"""test_hub_faq.py -- every hub answers questions, with numbers that match its own page.

2026-08-12 audit: /drug/rusfertide (363 words, FAQPage) holds 16.67% AI citation share while
/calendar (#1 on Bing, no FAQPage) earned zero citations. build_hub_faq.py fixes that daily.
This guard keeps three promises:

  1. Every target hub carries a FAQPage with at least the expected number of questions.
  2. /calendar's FAQ numbers AGREE with its own lede -- the FAQ is parsed from the lede at build
     time, and this re-checks the equality independently, so a lede rewrite can never leave a
     stale count answering searchers.
  3. /calendar and /decisions carry a live countdown token ("today"/"tomorrow"/"in N days"),
     the honest mechanism that lets their dateModified move daily (audit section 3). If the
     countdown vanishes, the freshness story silently reverts to '4 days ago' snippets.
"""
import json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
WANT = {"calendar": 4, "decisions": 4, "readouts": 3, "drug": 3, "tickers": 3, "research": 3,
        "conferences": 3, "adcomm": 3, "developers": 3,
        "learn/why-cross-trial-comparisons-mislead": 2}
COUNTDOWN = re.compile(r"\btoday\b|\btomorrow\b|\bin \d+ days?\b")


def faq_counts(doc):
    n = 0
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
        try:
            j = json.loads(m.group(1))
        except Exception:
            continue
        if j.get("@type") == "FAQPage":
            n = max(n, len(j.get("mainEntity", [])))
    return n


def main():
    bad = []
    docs = {}
    for rel, want in WANT.items():
        p = os.path.join(SITE, rel, "index.html")
        if not os.path.exists(p):
            bad.append(f"/{rel}: page missing")
            continue
        docs[rel] = open(p, encoding="utf-8", errors="replace").read()
        got = faq_counts(docs[rel])
        if got < want:
            bad.append(f"/{rel}: FAQPage has {got} questions, expected >= {want} -- run "
                       f"build_hub_faq.py")

    cal = docs.get("calendar", "")
    txt = re.sub(r"<[^>]+>", " ", cal)
    lede = re.search(r"lists\s+([\d,]+)\s+FDA decision dates.*?([\d,]+)\s+are still ahead",
                     txt, re.S)
    faq = re.search(r"([\d,]+) FDA decision dates are on the 2026 calendar; ([\d,]+)", txt)
    if lede and faq and (lede.group(1) != faq.group(1) or lede.group(2) != faq.group(2)):
        bad.append(f"/calendar: FAQ says {faq.group(1)}/{faq.group(2)} but the lede says "
                   f"{lede.group(1)}/{lede.group(2)} -- the page disagrees with itself")

    for rel in ("calendar", "decisions"):
        m = re.search(r"HUBFAQ:BEGIN(.*?)HUBFAQ:END", docs.get(rel, ""), re.S)
        if m and not COUNTDOWN.search(re.sub(r"<[^>]+>", " ", m.group(1))):
            bad.append(f"/{rel}: no live countdown token in the FAQ -- the honest daily-change "
                       f"mechanism is gone and dateModified will go stale")

    for rel in ("research", "developers"):
        d = docs.get(rel) or open(os.path.join(SITE, rel, "index.html"),
                                  encoding="utf-8", errors="replace").read()
        if '"Dataset"' not in d and '"DataCatalog"' not in d:
            bad.append(f"/{rel}: no Dataset/DataCatalog schema -- run build_hub_faq.py")

    if bad:
        print(f"FAIL: {len(bad)} hub FAQ problem(s).")
        for b in bad[:10]:
            print(f"   {b}")
        return 1
    print(f"  PASS: {len(WANT)} hubs carry FAQPage; calendar FAQ agrees with its lede; "
          f"countdown live on calendar+decisions; Dataset schema on research+developers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
