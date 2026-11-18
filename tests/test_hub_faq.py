# -*- coding: utf-8 -*-
"""test_hub_faq.py -- every hub answers questions, with numbers that match its own page.

2026-08-12 audit: /drug/rusfertide (363 words, FAQPage) holds 16.67% AI citation share while
/calendar (#1 on Bing, no FAQPage) earned zero citations. build_hub_faq.py fixes that daily.
This guard keeps three promises:

  1. Every target hub carries a FAQPage with at least the expected number of questions.
  2. /calendar's FAQ numbers AGREE with its own lede -- the FAQ is parsed from the lede at build
     time, and this re-checks the equality independently, so a lede rewrite can never leave a
     stale count answering searchers.
     PLANT=faq sets the FAQ to a stale count and must fail.
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
    # red team 2026-11-18: this check matched FAQ wording retired long ago ("on the 2026 calendar;"), so it never
    # ran, and the FAQ said 25 still ahead for days while the lede said 16. It now reads the lede with the FAQ cut
    # out, and the FAQ from its own block, and fails when either is missing so a rewording cannot switch it off.
    if os.environ.get("PLANT") == "faq":
        cal = re.sub(r"and \d+ are still ahead as of", "and 25 are still ahead as of", cal)
    faqblk = re.search(r"HUBFAQ:BEGIN(.*?)HUBFAQ:END", cal, re.S)
    txt = re.sub(r"<[^>]+>", " ", re.sub(r"HUBFAQ:BEGIN.*?HUBFAQ:END", "", cal, flags=re.S))
    ftxt = re.sub(r"<[^>]+>", " ", faqblk.group(1)) if faqblk else ""
    n_l = re.search(r"lists\s+([\d,]+)\s+FDA decision dates", txt)
    a_l = re.search(r"([\d,]+)\s+FDA PDUFA goal dates?\s+(?:are|is)\s+still ahead in \d{4}", txt)
    faq = re.search(r"([\d,]+) FDA decision dates are on this calendar[^.]*?(?:and ([\d,]+) (?:are|is) still "
                    r"ahead as of|\.)", ftxt)
    if cal and not (n_l and faq):
        bad.append("/calendar: could not read the decision count from both the lede and the FAQ")
    elif cal:
        if n_l.group(1) != faq.group(1):
            bad.append(f"/calendar: FAQ says {faq.group(1)} dates but the lede lists {n_l.group(1)}")
        if (a_l.group(1) if a_l else None) != faq.group(2):
            bad.append(f"/calendar: FAQ says {faq.group(2) or 'nothing'} still ahead but the lede says "
                       f"{a_l.group(1) if a_l else 'nothing'} -- the page disagrees with itself")

    for rel in ("calendar", "decisions"):
        m = re.search(r"HUBFAQ:BEGIN(.*?)HUBFAQ:END", docs.get(rel, ""), re.S)
        if m and not COUNTDOWN.search(re.sub(r"<[^>]+>", " ", m.group(1))):
            bad.append(f"/{rel}: no live countdown token in the FAQ -- the honest daily-change "
                       f"mechanism is gone and dateModified will go stale")

    # decisions FAQ sourcing counts must equal the page's own provenance bars (red team
    # 2026-08-12g: body said 285 sourced while the FAQ schema still told AI engines 150 --
    # 'the page learned something the schema didn't'). Independent re-parse of both.
    dtxt = re.sub(r"<[^>]+>", " ", docs.get("decisions", ""))
    bars = re.search(r"([\d,]+)\s+link a primary source.*?([\d,]+)\s+read from the price "
                     r"reaction.*?([\d,]+)\s+asserted, no source", dtxt, re.S)
    faqn = re.search(r"([\d,]+) of ([\d,]+) FDA decisions in this archive link to a primary "
                     r"source\. ([\d,]+) are inferred[^.]*and ([\d,]+) carry no source", dtxt)
    if bars and faqn:
        if (bars.group(1) != faqn.group(1) or bars.group(2) != faqn.group(3)
                or bars.group(3) != faqn.group(4)):
            bad.append(f"/decisions: FAQ says {faqn.group(1)}/{faqn.group(3)}/{faqn.group(4)} "
                       f"but the provenance bars say {bars.group(1)}/{bars.group(2)}/"
                       f"{bars.group(3)} -- the schema is citing the site down again")
    elif bars and not faqn:
        bad.append("/decisions: provenance bars present but the FAQ sourcing sentence is "
                   "missing or in an old format -- run build_hub_faq.py")

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
