# -*- coding: utf-8 -*-
"""The 'landed on the goal date' bucket, audited row by row, and the goal dates sourced.

I raised an alarm on 2026-09-18 that all nine "on the day" rows in the published 2026 timing
statistic had a goal date identical to their decision date, and suspected the bucket was an
artefact of filling the goal from the decision. EDGAR says I was wrong about seven of them: the
sponsor stated exactly that day in its own filing and the FDA acted on it. Those seven are real
and the retraction is on the record.

Two are not:

  MRK 2026-07-16, Lipfendra (enlicitide decanoate). Merck never published a PDUFA goal date for
  it. The Q2 10-Q says only "In July 2026, the FDA approved Lipfendra tablets"; the Q1 10-Q
  discusses the EU review and gives no US date; the 8-K of 2026-02-03 notes a priority review
  voucher under the CNPV pilot, a pathway that need not carry a conventional PDUFA date. Our
  2026-07-16 "goal date" is the action date copied over.

  OTSKY 2026-07-24, centanafadine. Otsuka files nothing EDGAR-searchable for it and openFDA has
  no record under that generic name. No goal date is verifiable from any primary source we hold.

Both keep their APPROVAL (the action date is sourced); both are marked `goal_unsourced` so the
timing statistic stops counting them as punctuality measurements. The statistic moves from
30 / 18 early / 9 on the day / 3 late to 28 / 18 / 7 / 3.

    python apply_0918_goal_provenance.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}

# id -> (label, url, the date string that must appear near the drug name, drug token)
SOURCED = {
    "pdufa_arqt_2026-06-29": ("Arcutis 10-Q 2026-05-06",
        "https://www.sec.gov/Archives/edgar/data/1787306/000178730626000040/arqt-20260331.htm",
        "June 29, 2026", "roflumilast"),
    "pdufa_vera_2026-07-07": ("Vera Therapeutics 8-K 2026-02-26 (EX-99.1)",
        "https://www.sec.gov/Archives/edgar/data/1831828/000119312526073421/vera-ex99_1.htm",
        "July 7, 2026", "atacicept"),
    "pdufa_mrna_2026-08-05": ("Moderna 8-K 2026-07-31 (EX-99.1, Q2 2026 results)",
        "https://www.sec.gov/Archives/edgar/data/1682852/000168285226000147/exhibit9912026q2pressrelea.htm",
        "August 5, 2026", "mRNA-1010"),
    "pdufa_lnth_2026-08-13": ("Lantheus 8-K 2025-11-06 (EX-99.1)",
        "https://www.sec.gov/Archives/edgar/data/1521036/000119312525268103/lnth-ex99_1.htm",
        "August 13, 2026", "MK-6240"),
    "pdufa_jazz_2026-08-25": ("Jazz Pharmaceuticals 8-K 2026-05-07 (EX-99.1, Q1 2026 results)",
        "https://www.sec.gov/Archives/edgar/data/1937653/000193765326000033/ex991q12026_earningsxrelea.htm",
        "August 25, 2026", "zanidatamab"),
    "pdufa_zyme_2026-08-25": ("Jazz Pharmaceuticals 8-K 2026-05-07 (EX-99.1) -- Jazz holds the BLA; Zymeworks licensed zanidatamab to Jazz",
        "https://www.sec.gov/Archives/edgar/data/1937653/000193765326000033/ex991q12026_earningsxrelea.htm",
        "August 25, 2026", "zanidatamab"),
    "pdufa_gild_2026-08-27": ("Gilead 8-K 2026-05-07 (EX-99.1, Q1 2026 results)",
        "https://www.sec.gov/Archives/edgar/data/882095/000088209526000022/exhibit991earningspressrel.htm",
        "August 27, 2026", "bictegravir"),
}

UNSOURCED = {
    "pdufa_mrk_2026-07-16": (
        "Merck has never published a PDUFA goal date for enlicitide decanoate (Lipfendra). Its Q2 "
        "2026 10-Q states only \"In July 2026, the FDA approved Lipfendra tablets\"; the Q1 10-Q "
        "covers the EU review and gives no US date; the 8-K of 2026-02-03 records a priority "
        "review voucher under the CNPV pilot, which need not carry a conventional PDUFA date. The "
        "2026-07-16 we carried as a goal date is the action date. The approval stands and is "
        "sourced to the FDA's own announcement; the goal date is withdrawn as a measurement."),
    "pdufa_otsky_2026-07-24": (
        "Otsuka files nothing EDGAR-searchable for centanafadine and openFDA holds no record under "
        "that generic name, so no goal date is verifiable from a primary source we can link. The "
        "approval stands; the goal date is withdrawn as a measurement."),
}


def fetch(u):
    for i in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=70).read()
            return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ",
                          re.sub(r"<[^>]+>", " ", b.decode("utf-8", "replace"))))
        except Exception:
            if i == 2:
                raise
            time.sleep(3 * (i + 1))


PHRASE = (r"(?:PDUFA|Prescription Drug User Fee Act|target action date|goal date|action date)"
          r"[^.]{0,160}?")


def quote_for(text, datestr, drug):
    """Anchor on the PDUFA-phrase-then-date pair, not on the date alone.

    The first version anchored on the date string and took 420 characters around it, which in a
    long earnings release returns the document's opening boilerplate rather than the sentence that
    states the goal date. It also could not distinguish a multi-product release (Merck's, where
    the nearest PDUFA date to "enlicitide" belongs to WINREVAIR). This version requires the
    PDUFA phrase and the date to be part of one clause, and the drug name to appear within 900
    characters with no COMPETING PDUFA date closer to the drug than this one."""
    d = drug.lower()[:7]
    best = None
    for m in re.finditer(PHRASE + re.escape(datestr), text, re.I):
        window = text[max(0, m.start() - 900): m.end() + 900].lower()
        if d not in window:
            continue
        # a competing date inside the same window means the release covers several products
        others = {x for x in re.findall(r"(?:January|February|March|April|May|June|July|August|"
                                        r"September|October|November|December) \d{1,2}, 20\d{2}",
                                        text[max(0, m.start() - 400): m.end() + 400])} - {datestr}
        clause = text[max(0, m.start() - 120): m.end() + 120].strip()
        if others:
            # keep it, but say so, so a human sees the ambiguity rather than a clean-looking quote
            return clause, sorted(others)
        best = (clause, [])
        break
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    by = {r["id"]: r for r in rows}

    ok = fail = 0
    for rid, (label, url, datestr, drug) in SOURCED.items():
        r = by.get(rid)
        if r is None:
            print(f"  MISSING {rid}"); fail += 1; continue
        try:
            t = fetch(url)
        except Exception as e:
            print(f"  FETCH FAILED {rid}: {e}"); fail += 1; continue
        got = quote_for(t, datestr, drug)
        if not got:
            print(f"  NOT CONFIRMED {rid}: no '<PDUFA phrase> ... {datestr}' clause with "
                  f"{drug} within 900 chars -- NOT WRITTEN")
            fail += 1
            continue
        q, others = got
        d = r.setdefault("_d", {})
        d["goal_source"] = label
        d["goal_source_url"] = url
        d["goal_source_quote"] = q[:420]
        if others:
            d["goal_source_caveat"] = ("The filing names other dates nearby (%s); the quote was "
                                       "read and attributed by hand." % ", ".join(others))
        d.setdefault("source_url", url)
        d.setdefault("source", label)
        ok += 1
        print(f"  SOURCED {rid}  {label[:46]}")
        print(f"     QUOTE: {q}")
        if others:
            print(f"     CAVEAT other dates in the same window: {others}")
        time.sleep(0.6)

    for rid, why in UNSOURCED.items():
        r = by.get(rid)
        if r is None:
            print(f"  MISSING {rid}"); fail += 1; continue
        d = r.setdefault("_d", {})
        d["goal_unsourced"] = True
        d["goal_note"] = why
        print(f"  GOAL WITHDRAWN {rid}: {why[:90]}...")

    if not a.dry_run and ok:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"\n{ok} goal date(s) sourced, {len(UNSOURCED)} withdrawn as measurements, {fail} failure(s)"
          + ("   (--dry-run)" if a.dry_run else ""))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
