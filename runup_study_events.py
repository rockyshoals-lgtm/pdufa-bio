# -*- coding: utf-8 -*-
"""runup_study_events.py -- which published decisions belong in the run-up study, and what each one was.

One owner for three questions every run-up script used to answer on its own, differently:

  1. What drug was decided on (ticker, date)?   The decision page says. The extender used to take the FIRST
     dataset row for the ticker, whatever its date, so every multi-product sponsor's rows carried one label
     (GSK's Nov 17, 2026 neladalkib approval was labelled tebipenem, approved Jun 17; five AZN rows in Apr-May
     2026 all read "Truqap"). Found 2026-11-18.
  2. What was the outcome?                       The decision page's own Outcome line. The extender read
     "anything without 'crl' in the listing text" as APPROVAL, so price-inferred "outcome unverified" pages
     entered the study as approvals.
  3. Is it an FDA decision at all?              Only a primary-sourced decision page qualifies. A page that says
     "outcome unverified" is a price observation by its own banner, and many of the 2025 ones are trial
     readouts, not PDUFA events. runup_study_exclusions.json lists pages whose cited source was checked and
     does NOT announce the FDA action (2026-11-18 re-check of the keyword-matched SEC sources), each with the
     reason. A page marked "label corrected" says in its own CRL reason that it was not a CRL (a trial readout,
     a Refusal-to-File, an approval on another date) and is left out too. Rows removed from the study are kept,
     with the reason, in runup_study_excluded.csv.

Facts only: nothing here decides an outcome; it reads what the page publishes and refuses what the page itself
calls unverified.
"""
import csv
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
EXCLUSIONS = os.path.join(HERE, "runup_study_exclusions.json")
EXCLUDED_CSV = os.path.join(HERE, "runup_study_excluded.csv")
INDICATIONS = os.path.join(HERE, "runup_study_indications.json")
# The /fda-decision archive starts 2025-01-02. From then on every study row must match a published decision
# page; a row whose page was retired (a moved date, a royalty holder's duplicate, the false SELLAS CRL) is not a
# published decision. Rows before this date are the 2020-2024 research set, which has no per-event pages.
ARCHIVE_START = "2025-01-01"


def _kv(doc, key):
    m = re.search(r'<div class="kv"><span>' + re.escape(key) + r'</span>(.*?)(?=<div class="kv">|</section>|<h2)',
                  doc, re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()


def page_id(tk, d):
    return f"{tk}-{d[:10]}"


def decision_facts(tk, d):
    """What the published /fda-decision/{tk}-{d} page states, or None if there is no page.

    outcome: APPROVAL | CRL | UNVERIFIED | OTHER
    """
    p = os.path.join(SITE, "fda-decision", page_id(tk, d), "index.html")
    if not os.path.exists(p):
        return None
    doc = open(p, encoding="utf-8", errors="replace").read()
    title = html.unescape((re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1])
    out = _kv(doc, "Outcome")
    if not out:   # a few hand-built pages carry no Outcome line; their title states it ("... Approved Mar 25, 2026")
        mt = re.search(r"\b(Approved|CRL)\b", title)
        out = mt.group(1) if mt else ""
    if "outcome unverified" in title.lower() or out.startswith("Unconfirmed") or "price-only" in out:
        oc = "UNVERIFIED"
    elif "label corrected" in out.lower():
        # "✗ CRL ⚠ label corrected": the page keeps the archive's CRL mark but its own CRL reason says it was not
        # one ("Mislabel: Phase 3 EQUATOR readout miss, no CRL"; a Refusal-to-File; an approval months later).
        # 15 such pages were counted as CRLs until the 2026-11-18 red team.
        oc = "OTHER"
    elif "not approvable" in out.lower():
        oc = "OTHER"
    elif re.search(r"\bCRL\b|complete response", out, re.I):
        oc = "CRL"
    elif re.search(r"\bApproved\b", out):
        oc = "APPROVAL"
    else:
        oc = "OTHER"
    drug = _kv(doc, "Drug / candidate") or _kv(doc, "Drug") or _kv(doc, "Brand / candidate")
    # "Verified ...: Drugs@FDA, application NDA219164, action date 2026-02-27": two pages of one ticker naming the
    # same application and action date are one FDA action (ASND Feb 27/28 2026, BMY Apr 8/11 2025).
    mv = re.search(r"application\s+((?:NDA|BLA|ANDA)\s?\d+)\b.*?action date (\d{4}-\d{2}-\d{2})", _kv(doc, "Validation"))
    return {"page": page_id(tk, d), "outcome": oc, "drug": drug, "indication": _kv(doc, "Indication"),
            "outcome_text": out, "title": title, "crl_reason": _kv(doc, "CRL reason"),
            "fda_action": (mv.group(1).replace(" ", ""), mv.group(2)) if mv else None}


def load_exclusions():
    if not os.path.exists(EXCLUSIONS):
        return {}
    return {k: v for k, v in json.load(open(EXCLUSIONS, encoding="utf-8")).get("pages", {}).items()}


def excluded_keys(reason_prefix=""):
    """cache_keys removed from the study (runup_study_excluded.csv), optionally only those whose reason starts so."""
    if not os.path.exists(EXCLUDED_CSV):
        return set()
    return {r["cache_key"] for r in csv.DictReader(open(EXCLUDED_CSV, encoding="utf-8"))
            if r.get("reason", "").startswith(reason_prefix)}


def load_sourced_indications():
    """runup_study_indications.json: indications read from a primary source for decision pages that carry none."""
    if not os.path.exists(INDICATIONS):
        return {}
    return json.load(open(INDICATIONS, encoding="utf-8")).get("rows", {})


def expected_indication(tk, d, asset, facts=None, sourced=None):
    """(indication, where it came from) a study row must carry, or None for a 2020-2024 research row with no page.

    Found 2026-11-18: until that day extend_runup_study.py copied the ticker's FIRST dataset row's indication onto
    every new row, so Pfizer's Hympavzi read "Dermatomyositis", Merck's Keytruda and Capvaxive "Hypercholesterolemia",
    GSK's linerixibat "cUTI". A row's indication is its own decision page's Indication line; where the page has none,
    the entry in runup_study_indications.json for that page, read from the FDA letter or label or the sponsor's own
    release, and only while that entry names the row's drug; otherwise blank. Never another row's.
    """
    facts = facts if facts is not None else decision_facts(tk, d)
    if facts is None:
        return None
    if facts.get("indication"):
        return facts["indication"], "decision page"
    sourced = sourced if sourced is not None else load_sourced_indications()
    e = sourced.get(page_id(tk, d))
    if e and e.get("indication") and e.get("drug") == asset and e.get("source"):
        return e["indication"], "primary source " + e["source"]
    return "", "no sourced indication"


def eligibility(tk, d, facts=None, excl=None):
    """(eligible, reason). Rows with no decision page (the 2020-2024 research rows) are judged elsewhere."""
    facts = facts if facts is not None else decision_facts(tk, d)
    excl = excl if excl is not None else load_exclusions()
    if facts is None:
        if d[:10] >= ARCHIVE_START:
            return False, "no published decision page (page retired or moved to another date)"
        if page_id(tk, d) in excl:   # a 2020-2024 research row checked and found not to be an FDA action
            return False, "research row re-checked: " + excl[page_id(tk, d)].get("reason", "")
        return True, "no decision page (2020-2024 research set)"
    if facts["page"] in excl:
        return False, "source re-checked: " + excl[facts["page"]].get("reason", "")
    if facts["outcome"] == "UNVERIFIED":
        return False, "decision page says outcome unverified (price-inferred, no primary source)"
    # 2026-11-18 (design red team, change 5): "primary-sourced" was assumed, never checked. 17 2026 pages that cite
    # nothing (ABBV-2026-05-27, MRK-2026-06-12, ...) fed their outcomes into the study's statistics. The page has
    # to cite a document, read the way /decisions counts it.
    from refresh_provenance_counts import page_kind
    kind = page_kind(open(os.path.join(SITE, "fda-decision", facts["page"], "index.html"), encoding="utf-8",
                          errors="replace").read())
    if kind == "inferred":
        return False, "decision page says its outcome is inferred from the price move"
    if kind == "unsourced":
        return False, "decision page cites no source for the outcome"
    if facts["outcome"] == "OTHER" and "label corrected" in facts["outcome_text"].lower():
        return False, "decision page says its CRL label was wrong: " + (facts.get("crl_reason") or "")[:90]
    if facts["outcome"] == "OTHER":
        return False, f"not a PDUFA approval or CRL ({facts['outcome_text'][:60]})"
    return True, "primary-sourced decision page"
