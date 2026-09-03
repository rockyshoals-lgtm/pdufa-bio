# -*- coding: utf-8 -*-
"""rewrite_decision_snippets.py -- decision-page titles/descriptions must ANSWER, not name.

SEO audit 2026-09-02b: /fda-decision/RARE-2026-08-19 sat at position 3.70 with ZERO
clicks from 10 impressions -- position 3.7 should convert at 8-12%. The description read
"Ultragenyx Pharmaceutical Inc. (RARE) FDA decision Aug 19, 2026: Approved." -- it names
the page instead of answering the query. The audit's test: does the snippet answer, or
just label? And the timing lever: decision pages are entering the index NOW, so fixing
the template scales across the 455-page corpus before bad snippets calcify.

Answer format (audit's model sentence, house style, no em dashes):
  title: "GENGLYCOS Approved Aug 19, 2026, 4 Days Early | RARE FDA Decision | pdufa.bio"
  desc:  "Ultragenyx Pharmaceutical Inc. (RARE): GENGLYCOS (DTX401) was approved on
          August 19, 2026, 4 days before its August 23 goal date. Decision source
          document and the 120-trading-day run-up into the date."

Delta clause only when the dataset holds the goal date (matched by ticker + decision
date); pages without a matched row state the outcome and date without inventing a goal.
Idempotent; og:/twitter mirrors kept in sync. build_decision_page.py patched separately
so future pages are BORN in this format -- the rewrite must not be a frozen one-off.
"""
import datetime as dt
import glob
import html as _html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
        "Nov", "Dec"]


def pretty(iso, short=False):
    d = dt.date.fromisoformat(str(iso)[:10])
    return f"{(MON3 if short else MON)[d.month]} {d.day}, {d.year}"


def page_facts(doc):
    """(outcome, drug) from the existing machine-written title; None if unparseable."""
    tm = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
    if not tm:
        return None, None
    ttl = _html.unescape(re.sub(r"\s+", " ", tm.group(1))).strip()
    oc = ("Approved" if re.search(r"\bApproved\b", ttl)
          else "CRL" if re.search(r"CRL|Complete Response", ttl, re.I)
          else "Withdrawn" if re.search(r"\bWithdrawn\b", ttl, re.I) else None)
    dm = (re.match(r"^[A-Z]{1,6} FDA Decision [^:]+:\s*(?:Approved|Complete Response "
                   r"Letter|CRL|Withdrawn)\s*-\s*(.+?)\s*\|", ttl)
          or re.match(r"^[A-Z]{1,6} FDA Decision \([^)]+\):\s*(.+?):\s*(?:Approved|"
                      r"Complete Response Letter|CRL|Withdrawn)\s*\|", ttl, re.I)
          # already-rewritten format: "{drug} Approved {date}... | TK FDA Decision |"
          or re.match(r"^(.+?)\s+(?:Approved|CRL|Withdrawn)\b.*\|\s*[A-Z]{1,6} FDA "
                      r"Decision\s*\|", ttl))
    return oc, (dm.group(1).strip() if dm else "")


def company_of(doc, tk):
    m = re.search(r'name="description" content="([^("]{3,60}) \(' + tk + r'\)', doc)
    if not m:
        m = re.search(r'"name"\s*:\s*"([^"]{3,60})"\s*,\s*"tickerSymbol"', doc)
    # unescape to FIXPOINT: one earlier buggy pass left "&amp;amp;" in 13 pages, and a
    # single unescape stabilized at the double-escaped text instead of repairing it
    if not m:
        return tk
    s = m.group(1).strip()
    while _html.unescape(s) != s:
        s = _html.unescape(s)
    return s


def main():
    # goal dates for the delta clause, keyed (ticker, decision date)
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    goals = {(str(r.get("t", "")).upper(), str(r.get("dcd", ""))[:10]): str(r.get("d"))[:10]
             for r in rows if r.get("type") == "PDUFA"
             and str(r.get("st", "")).lower() == "decided" and r.get("dcd") and r.get("d")}

    # listing rows as a drug-name fallback for drug-less titles ("AQST FDA Decision
    # 2026-02-02: CRL") -- the /decisions row states "CRL: Anaphylm" for the same slug
    listing = io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8",
                      errors="replace").read()
    listing_drug = {}
    for lm in re.finditer(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"'
                          r'.{0,260}?(?:Approved|CRL)</span>:\s*([^<]{2,80})', listing,
                          re.S):
        listing_drug[lm.group(1)] = _html.unescape(lm.group(2).strip())

    changed = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, dcd = m.group(1), m.group(2)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        low = doc.lower()
        if ("price-only" in low or "outcome unverified" in low
                or "validation in progress" in low):
            # Price-inferred pages must NOT get an answer-format assertion -- the first
            # run wrote "price-only received a Complete Response Letter" on CYTK,
            # asserting an unvalidated outcome AND taking a label as a drug name.
            skipped += 1
            continue
        oc, drug = page_facts(doc)
        # Provenance labels are NOT drug names -- 24 pages briefly read "Primary-sourced
        # was approved on..." because the label sat where the drug belongs in old titles.
        JUNK = {"price-only", "source-verified", "primary-sourced", "unverified", ""}
        if drug.lower() in JUNK:
            drug = listing_drug.get(slug, "")
        if drug.lower() in JUNK:
            drug = ""
        if not oc:
            print(f"  SKIP {slug}: unparseable title, not rewriting blind")
            skipped += 1
            continue
        if not drug:
            drug = "the application under review"   # answers without inventing a name
        company = company_of(doc, tk)

        goal = goals.get((tk, dcd))
        delta = None
        if goal:
            delta = (dt.date.fromisoformat(dcd) - dt.date.fromisoformat(goal)).days

        drug = drug.rstrip(". ")          # an earlier ellipsis truncation must not
                                          # re-enter as fake sentence stops
        while drug.count("(") > drug.count(")"):   # nor an earlier mid-paren cut
            drug = drug[:drug.rindex("(")].rstrip(" ,(-/")
        if oc == "Approved":
            tdelta = (f", {-delta} Days Early" if delta and delta < 0 else
                      f", {delta} Days Late" if delta and delta > 0 else "")
            word_t, verb = f"Approved {pretty(dcd, short=True)}{tdelta}", "was approved on"
        elif oc == "CRL":
            word_t, verb = (f"CRL {pretty(dcd, short=True)}",
                            "received a Complete Response Letter on")
        else:
            word_t, verb = f"Withdrawn {pretty(dcd, short=True)}", "was withdrawn on"
        # title budget 100 chars (test_meta_lengths.py); the drug name gives way at a
        # word boundary, WITHOUT an ellipsis (". w" reads as a mangled sentence stop)
        if drug == "the application under review":
            title = f"{tk} FDA Decision: {word_t} | pdufa.bio"
        else:
            suffix = f" {word_t} | {tk} FDA Decision | pdufa.bio"
            room = 100 - len(suffix)
            dshort = drug
            if len(dshort) > room:
                dshort = dshort[:room].rsplit(" ", 1)[0].rstrip(" ,(-/")
                while dshort.count("(") > dshort.count(")"):   # never "(vusolimogene"
                    dshort = dshort[:dshort.rindex("(")].rstrip(" ,(-/")
            title = f"{dshort}{suffix}"

        if delta is None or delta == 0:
            when = f"{pretty(dcd)}" + (" (its PDUFA goal date)" if delta == 0 else "")
        elif delta < 0:
            when = f"{pretty(dcd)}, {-delta} days before its {pretty(goal)} PDUFA goal date"
        else:
            when = f"{pretty(dcd)}, {delta} days after its {pretty(goal)} PDUFA goal date"
        # 160-char budget (test_meta_lengths.py): the answer sentence is non-negotiable,
        # the tail and the long-form names give way in order.
        # Older archive records lack a company name and fall back to the ticker --
        # "LLY (LLY):" shipped on ~25% of the first rewrite (audit 09-02c). When the
        # company IS the ticker, say it once.
        who = f"{company} ({tk})" if company != tk else tk
        core = f"{who}: {drug} {verb} {when}."
        for tail in (" Decision source document and the 120-trading-day run-up "
                     "into the date.", " Source and run-up included.", ""):
            desc = core + tail
            if len(desc) <= 160:
                break
        if len(desc) > 160:
            core = f"{tk}: {drug} {verb} {when}."          # drop the long company name
            desc = core if len(core) <= 160 else \
                f"{tk}: {dshort} {verb} {when}."           # then the long drug name

        new = re.sub(r"<title[^>]*>.*?</title>",
                     f"<title>{_html.escape(title)}</title>", doc, count=1, flags=re.S)
        new = re.sub(r'(<meta name="description" content=")[^"]*(")',
                     lambda mm: mm.group(1) + _html.escape(desc, quote=True) + mm.group(2),
                     new, count=1)
        new = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                     lambda mm: mm.group(1) + _html.escape(title, quote=True) + mm.group(2),
                     new, count=1)
        new = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                     lambda mm: mm.group(1) + _html.escape(desc, quote=True) + mm.group(2),
                     new, count=1)
        new = re.sub(r'(<meta name="twitter:title" content=")[^"]*(")',
                     lambda mm: mm.group(1) + _html.escape(title, quote=True) + mm.group(2),
                     new, count=1)
        new = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")',
                     lambda mm: mm.group(1) + _html.escape(desc, quote=True) + mm.group(2),
                     new, count=1)
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            changed += 1
    print(f"decision snippets: {changed} page(s) rewritten to answer format, "
          f"{skipped} skipped; {len(goals)} goal dates available for delta clauses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
