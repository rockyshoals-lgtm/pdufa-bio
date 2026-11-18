# -*- coding: utf-8 -*-
"""recheck_upcoming_dates.py -- every rebuild re-reads the sources of the dates that matter next.

WHY (red team 2026-11-18)
tests/test_date_checks_current.py blocks the rebuild when a date due in the next 14 days was not
checked against its source in the last 30 days. Without a recurring re-check, every rebuild stops on
2026-12-18, when the red team's Nov 17 checks age out. A person re-reading 40 rows every month is the
failure mode we already had. So each rebuild re-reads, for every open PDUFA goal and company-guided
readout due in the next 30 days:

  1. the row's own source: does the page still carry the quoted sentence?
  2. the company's SEC filings since that source or the row's last check, whichever is later (8-K,
     6-K, 10-Q, 10-K, exhibits; EDGAR full-text search on every drug token), plus the newest document
     any other row of the company cites. Every sentence naming the drug and its timing must either be
     history (all its dates before the row's source) or a clean restatement: exactly one date in it
     lies after the filing, that date carries the row's year and states the row's date at its
     precision, and no word in it says the date moved or the FDA acted.

A row passes only when the EDGAR search ran in full, no sentence is anything other than history or a
clean restatement, and either a restatement or the unchanged source holds. When another open row of
the same company names the same drug (KPTI's three selinexor trials), only an unchanged source with
nothing newer about the drug passes. A pass writes a CONFIRMED entry (by "auto re-check") to
_date_checks.json; a person's earlier entry is kept whole under "prior".

Everything else is NEVER written to the ledger:
  - "DATE RECHECK NEEDS A HUMAN" (the rebuild's review issue carries it): a sentence that may move the
    date or record an FDA action, a crash of this script, or any unconfirmed row whose date-guard
    deadline is a week away or less.
  - "Not yet urgent": nothing says the date moved, but nothing re-stated it either (a non-SEC filer
    such as Roche, an unreadable source). Listed in the log; raised a week before the guard would block.

This script never changes a date, a status or a page. It only records re-reads that agreed.

    python recheck_upcoming_dates.py               # re-check, write CONFIRMED entries, print report
    python recheck_upcoming_dates.py --dry-run     # report only
    python recheck_upcoming_dates.py --self-test   # offline logic test (tests/test_recheck_dates_logic.py)
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from date_quote_match import quote_states_date, norm  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_date_checks.json")
UA = {"User-Agent": "pdufa.bio research rockyshoals@gmail.com"}
WINDOW_DAYS = 30          # re-check rows due within this many days
FRESH_DAYS = 6            # a row checked this recently is left alone
MAX_FILINGS = 12          # more EDGAR documents than this naming the drug: a human reads them
BY = "auto re-check (recheck_upcoming_dates.py)"

GENERIC = {"phase", "study", "trial", "trials", "data", "topline", "top-line", "readout", "results", "final",
           "oral", "once", "weekly", "daily", "lower", "doses", "dose", "treatment", "adults", "adult",
           "children", "patients", "pediatric", "new", "snda", "sndas", "sbla", "nda", "bla", "maa", "label",
           "expansion", "naive", "the", "and", "with", "plus", "combination", "program", "pivotal",
           "interim", "primary", "registrational", "cohort", "part", "extension", "update", "first",
           "adolescent", "adolescents", "infants", "week", "weeks", "month", "year", "season", "second",
           "hiv-1", "hiv", "hbv", "hcv", "rsv", "covid", "cancer", "disease", "syndrome", "therapy",
           "updated", "publication", "healthy", "clinical", "small", "vivo", "prevention", "follow-up",
           "advanced", "monotherapy", "investigator-sponsored", "long-term", "fixed-duration",
           "presentation", "allogeneic", "inhalation", "cream", "foam", "film", "capsule",
           # red team 2026-11-18: words that named no drug and matched unrelated filing text
           "innovations", "meeting", "wound", "healing", "molecule", "incl", "randomized", "unblinded",
           "volunteers", "volunteer", "poster", "peak", "grace", "rnai", "sirna", "resubmission", "alfa",
           "calcium", "hydrochloride", "sodium", "tablet", "injection", "subcutaneous", "intravenous",
           "degrader", "inhibitor", "agonist", "antagonist", "antibody", "vaccine", "engager", "conjugate",
           "glue", "molecular", "gamma", "delta", "prodrug", "safety", "efficacy", "multicenter",
           "sub-study", "subgroup", "analysis", "post", "imaging", "brain", "lithium", "ongoing",
           "preliminary", "supplementary", "fmri", "car-t", "exatecan", "escalation", "proof-of-concept",
           "open-label", "double-blind", "biomarker", "biomarkers", "arm", "arms", "surgical", "site",
           "infections", "gel", "systemic", "subretinal", "first-in-human", "dual"}
# targets, mechanisms and hyphenated adjectives: they describe a drug, they do not name it
TARGET = re.compile(r"(?i)^(?:cd\d+\w*|[a-z]{2,5}\d+x[a-z]{2,5}\d+|stat\d+|nlrp\d+|fgfr\d+\w*|il-\d+\w*|"
                    r"glp-1\w*|pd-l?1|her2|egfr|kras|pan-\w+|\w+-(?:state|acting|directed|agonist|targeting|"
                    r"targeted|based|like|label|blind|concept|term|line|human|class|dose|week|arm))$")

REL_PDUFA = re.compile(r"\bPDUFA\b|action date|goal date|\bFDA\b|Food and Drug|approv|complete response|\bCRL\b|"
                       r"extend|extension|delay|postpon|accept|resubmi|under review|review period|"
                       r"advisory committee|expect|anticipat", re.I)
REL_READOUT = re.compile(r"top-?line|\bdata\b|\bresults?\b|read[- ]?out|expect|anticipat|delay|postpon|discontinu|"
                         r"terminat|\bhalt|clinical hold|\bpaus|enrol|present", re.I)
# phrases that sound like an action but are not one
SAFE = re.compile(r"if approved|potential(?:ly)?\s+(?:fda\s+|regulatory\s+|u\.s\.\s+|marketing\s+)?approv\w*|"
                  r"for\s+(?:fda\s+|regulatory\s+|marketing\s+)?approval|seek(?:ing|s)?\s+(?:fda\s+|regulatory\s+)?"
                  r"approval|approval decision|path to approval|toward approval|open-label extension|"
                  r"long-term extension|extension (?:study|trial|period|cohort|phase)", re.I)
SIG_PDUFA = re.compile(r"approv|complete response|\bCRL\b|refus|withdr|extend|extension|delay|postpon|"
                       r"major amendment|advisory committee|\bAdCom\b|discontinu|terminat", re.I)
SIG_READOUT = re.compile(r"delay|postpon|discontinu|terminat|\bhalt|clinical hold|\bpaus|stopp|futility|withdr", re.I)

# ---- every date-like expression a sentence can carry, and the last day it can mean
_M = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
      r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_DATE_KINDS = [
    ("iso", r"\b(20\d\d)-(\d\d)-(\d\d)\b"),
    ("slash", r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b"),
    ("day", rf"\b({_M})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d)\b"),
    ("dayr", rf"\b(\d{{1,2}})\s+({_M})\.?,?\s+(20\d\d)\b"),
    ("month", rf"\b({_M})\.?,?\s+(?:of\s+)?(20\d\d)\b"),
    ("dayny", rf"\b({_M})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b"),
    ("qword", r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+(?:calendar\s+)?quarter"
              r"(?:\s+of)?(?:\s+(?:the\s+)?(?:fiscal\s+)?(?:year\s+)?(20\d\d))?"),
    ("qnum1", r"\b([1-4])Q\s?'?((?:20)?\d\d)?\b"),
    ("qnum2", r"\bQ([1-4])(?:\s?'?((?:20)?\d\d))?\b"),
    ("hword", r"\b(first|second)\s+half(?:\s+of)?(?:\s+(?:the\s+)?(?:year\s+)?(20\d\d))?"),
    ("hnum1", r"\b([12])H\s?'?((?:20)?\d\d)?\b"),
    ("hnum2", r"\bH([12])(?:\s?'?((?:20)?\d\d))?\b"),
    ("part", r"\b(early|mid|late)[- ]?(?:\s*)(20\d\d)\b"),
    ("yend", r"\b(?:year[- ]end|end\s+of(?:\s+the\s+year)?)(?:\s+of)?\s*(20\d\d)\b"),
    ("rel", r"\b(?:year[- ]end|end of (?:the|this) year|(?:later )?this year|next year|mid-year)\b"),
    ("year", r"\b(20\d\d)\b"),
]
_DATE_RX = {k: re.compile(p, re.I) for k, p in _DATE_KINDS}
_DATE_ANY = re.compile("|".join(f"(?P<{k}>{p})" for k, p in _DATE_KINDS), re.I)
_MON = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                                          "oct", "nov", "dec"])}
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}


def _month_end(y, m):
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)) if 1 <= m <= 12 else None


def _yr(v):
    if not v:
        return None
    v = int(v)
    return v + 2000 if v < 100 else v


def find_dates(sentence):
    """[(text, last_day_it_can_mean or None)] for every date-like expression, in order. None means the
    expression has no year (\"Q4\", \"December 12\", \"this year\"), so it cannot be placed."""
    out = []
    for m in _DATE_ANY.finditer(sentence or ""):
        k = m.lastgroup
        g = _DATE_RX[k].fullmatch(m.group(0)).groups()
        end = None
        try:
            if k == "iso":
                end = dt.date(int(g[0]), int(g[1]), int(g[2]))
            elif k == "slash":
                end = dt.date(int(g[2]), int(g[0]), int(g[1]))
            elif k == "day":
                end = dt.date(int(g[2]), _MON[g[0].lower()[:3]], int(g[1]))
            elif k == "dayr":
                end = dt.date(int(g[2]), _MON[g[1].lower()[:3]], int(g[0]))
            elif k == "month":
                end = _month_end(int(g[1]), _MON[g[0].lower()[:3]])
            elif k in ("qword", "qnum1", "qnum2"):
                q, y = (_ORD[g[0].lower()] if k == "qword" else int(g[0])), _yr(g[1])
                end = _month_end(y, 3 * q) if y else None
            elif k in ("hword", "hnum1", "hnum2"):
                h, y = (_ORD[g[0].lower()] if k == "hword" else int(g[0])), _yr(g[1])
                end = _month_end(y, 6 * h) if y else None
            elif k == "part":
                end = _month_end(int(g[1]), {"early": 4, "mid": 6, "late": 12}[g[0].lower()])
            elif k in ("yend", "year"):
                end = dt.date(int(g[0]), 12, 31)
        except (ValueError, KeyError, TypeError):
            end = None
        out.append((m.group(0), end))
    return out


# ---------------------------------------------------------------- pure logic (self-tested offline)

def _ok_token(w):
    w = w.strip("-")
    parts = [p for p in w.lower().split("-") if p]
    if len(w) < 4 or w.lower() in GENERIC or any(p in GENERIC for p in parts) or TARGET.match(w):
        return None
    if re.fullmatch(r"\d+-week|[a-z]+-\d", w.lower()):
        return None
    return w


def drug_tokens(name):
    """The row's drug: the first distinctive word of its name, plus the first word inside the first
    parenthesis (usually the INN or the code), never generic trial words, targets or mechanisms. A
    name that opens with a spaced code ("MBX 4291") uses the code."""
    s = str(name or "")
    out = []
    m = re.match(r"\s*([A-Z]{2,5} \d{3,5})\b", s)
    if m and not re.fullmatch(r"[A-Z]+ (?:19|20)\d\d", m.group(1)):
        out.append(m.group(1))
    for w in ([] if out else re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", re.sub(r"\(.*?\)", " ", s))):
        w = _ok_token(w)
        if w:
            out.append(w)
            break
    m = re.search(r"\(([^()]*)\)", s)
    if m:
        for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", m.group(1)):
            w = _ok_token(w)
            if w and w.lower() not in [o.lower() for o in out]:
                out.append(w)
                break
    return out


_ABBR = re.compile(r"\b(U\.S|U\.K|Inc|Co|Corp|Ltd|No|Nos|e\.g|i\.e|vs|approx|Dr|Mr|Ms|St|Jan|Feb|Mar|Apr|Jun|"
                   r"Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.", re.I)


def sentences(text):
    """Split on sentence ends, never on "U.S.", "Inc.", "No." or "Nov." (which used to cut "approved by
    the U.S. Food and Drug Administration" in two, so the action was never seen)."""
    t = re.sub(r"\s+", " ", text or "")
    t = _ABBR.sub(lambda m: m.group(1).replace(".", "\x00") + "\x00", t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", t)
    return [p.replace("\x00", ".").strip() for p in parts if len(p.strip()) > 20]


def page_text(raw):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def quote_still_there(quote, text):
    """Every substantial fragment of the quote (split on ellipses) appears in the page."""
    page = norm(text)
    frags = [norm(f) for f in re.split(r"\.\.\.|…", html.unescape(quote or ""))]
    frags = [f.strip(" .,;") for f in frags if len(f.strip(" .,;")) >= 20]
    return bool(frags) and all(f in page for f in frags)


def is_history(sentence, src_iso):
    """True when every date the sentence names can only fall before the row's own source: a recap
    ("received a complete response letter in March 2025"), not news. A month counts as its last day,
    a quarter as its last day, a bare year as Dec 31. A sentence with no date, or with any date it
    cannot place (no year), is never history."""
    if not src_iso:
        return False
    ds = find_dates(sentence)
    return bool(ds) and all(e is not None for _, e in ds) and max(e for _, e in ds).isoformat() < src_iso


def clean_restatement(s, row, fdate):
    """The sentence restates the row's date and nothing else: exactly one date in it lies after the
    filing (every other date is past history), that one carries the row's year and states the row's
    date at the row's precision, and no word in it says the date moved or the FDA acted."""
    is_pdufa = row.get("type") == "PDUFA"
    if (SIG_PDUFA if is_pdufa else SIG_READOUT).search(SAFE.sub(" ", s)):
        return False
    try:
        fd = dt.date.fromisoformat(fdate)
    except Exception:
        return False
    fut = [(t, e) for t, e in find_dates(s) if e is None or e > fd]
    if len(fut) != 1 or fut[0][1] is None:
        return False
    t, e = fut[0]
    return str(e.year) == row["d"][:4] and quote_states_date(t, row["d"], row.get("dp") or "day", ref_iso=fdate)


def assess(row, source_text, filings, edgar_ran, shared=False):
    """row: dataset row. source_text: the row's source page text (None if unreadable).
    filings: [(date_iso, url, text)] published after the row's source or its last check.
    shared: another open row of this company names the same drug, so a sentence about the drug may be
    about the other trial; then only an unchanged source with nothing newer about the drug confirms.
    Returns (verdict, detail, kind): verdict 'CONFIRMED' or 'HUMAN'; kind 'ok', 'signal' (a newer
    document may move the date or record an action: always raised) or 'unverified' (nothing says the
    date moved, but nothing re-states it either: raised once the guard's deadline is near)."""
    d = row.get("_d") or {}
    is_pdufa = row.get("type") == "PDUFA"
    quote = d.get("source_quote") if is_pdufa else d.get("guidance_text")
    toks = [t.lower() for t in drug_tokens(row.get("name"))]
    if not toks:
        return "HUMAN", "no distinctive drug name to search filings for", "unverified"
    rel = REL_PDUFA if is_pdufa else REL_READOUT
    sig = SIG_PDUFA if is_pdufa else SIG_READOUT
    src_iso = source_date(d)
    restated, signals, unclear = None, [], []
    for fdate, url, text in filings:
        for s in sentences(text):
            low = s.lower()
            if not any(re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", low) for t in toks):
                continue
            if not rel.search(s) or is_history(s, src_iso):
                continue
            if clean_restatement(s, row, fdate):
                restated = restated or (fdate, url, s[:220])
            elif find_dates(s) or sig.search(SAFE.sub(" ", s)):
                signals.append((fdate, url, s[:220]))
            else:
                unclear.append((fdate, url, s[:220]))
    if signals:
        f = signals[0]
        return "HUMAN", f"a document of {f[0]} may move the date or record an FDA action: \"{f[2]}\" ({f[1]})", "signal"
    if not edgar_ran:
        return "HUMAN", "company's SEC filings could not be searched (not an SEC filer, or EDGAR unreachable)", "unverified"
    src_ok = source_text is not None and quote_still_there(quote, source_text)
    if shared:
        if src_ok and not (restated or unclear):
            return "CONFIRMED", ("source still carries the quoted date; no newer SEC filing says anything about "
                                 "this drug's timing|" + (d.get("source_url") or d.get("guidance_url") or "")), "ok"
        return "HUMAN", ("another open row names the same drug, so newer filing text about it cannot be told "
                         "apart automatically" + (f": \"{(restated or unclear[0])[2]}\"" if (restated or unclear) else
                                                  "; and the source no longer carries its quote")), "unverified"
    if unclear:
        f = unclear[0]
        return "HUMAN", f"a document of {f[0]} discusses this drug's timing without restating the date: \"{f[2]}\" ({f[1]})", "unverified"
    if restated:
        return "CONFIRMED", f"restated in the {restated[0]} filing: \"{restated[2]}\"|{restated[1]}", "ok"
    if src_ok:
        return "CONFIRMED", ("source still carries the quoted date; no newer SEC filing names this drug "
                             "with a different date or an FDA action|" + (d.get("source_url") or d.get("guidance_url") or "")), "ok"
    if source_text is None:
        return "HUMAN", "source page could not be read and no newer filing restates the date", "unverified"
    return "HUMAN", "source page no longer carries the quoted sentence and no newer filing restates the date", "unverified"


def guard_deadline(row, entry):
    """The day tests/test_date_checks_current.py starts blocking the rebuild on this row: 14 days before
    it is due, or 31 days after its last check, whichever is later."""
    due = dt.date.fromisoformat(row["d"])
    out = due - dt.timedelta(days=14)
    try:
        out = max(out, dt.date.fromisoformat((entry or {}).get("checked", "")) + dt.timedelta(days=31))
    except Exception:
        pass
    return out


def due_rows(rows, ledger, today):
    out = []
    for r in rows:
        if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Under review"):
            pass
        elif r.get("type") == "Readout" and r.get("st") == "Guided":
            pass
        else:
            continue
        try:
            due = dt.date.fromisoformat(r["d"])
        except Exception:
            continue
        if not 0 <= (due - today).days <= WINDOW_DAYS:
            continue
        e = ledger.get(r["id"]) or {}
        try:
            if (today - dt.date.fromisoformat(e.get("checked", ""))).days <= FRESH_DAYS:
                continue
        except Exception:
            pass
        out.append(r)
    return out


def ledger_entry(prev, today, source, note):
    """A CONFIRMED re-read. A person's earlier entry is kept whole under "prior", never overwritten."""
    e = {"checked": today, "verdict": "CONFIRMED", "source": source, "by": BY, "note": note[:300]}
    if prev:
        p = prev.get("prior") if prev.get("by") == BY else {k: v for k, v in prev.items() if k != "prior"}
        if p:
            e["prior"] = p
    return e


def self_test():
    row = {"id": "x", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-12", "dp": "day",
           "name": "Bysanti (milsaperidone) - bipolar I",
           "_d": {"source_quote": "PDUFA target action date of December 12, 2026",
                  "source_url": "https://example.invalid/a", "source": "8-K 2026-08-05"}}
    src = "Vanda said the NDA for Bysanti has a PDUFA target action date of December 12, 2026. More."

    def one(text, r=row, s=src, edgar=True, shared=False, fdate="2026-11-05"):
        return assess(r, s, [(fdate, "u", text)] if text else [], edgar, shared)[0]

    H, C = "HUMAN", "CONFIRMED"
    cases = [
        (one(""), C, "source still states the date, nothing newer"),
        (one("The Bysanti NDA remains under review with a PDUFA target action date of December 12, 2026.", s=None),
         C, "source unreadable but a newer filing restates it"),
        (one("In February 2026, the FDA accepted the Bysanti NDA and assigned a PDUFA target action date of "
             "December 12, 2026.", s=None), C, "a past acceptance date beside the goal date still restates it"),
        (one("If approved, Bysanti would launch promptly; its PDUFA target action date is December 12, 2026.",
             s=None), C, "'if approved' is not an action"),
        (one("The FDA extended the Bysanti PDUFA target action date to March 12, 2027."), H, "a moved date"),
        (one("The FDA extended the Bysanti PDUFA target action date from December 12, 2026 to March 12, 2027."),
         H, "old and new date in one sentence"),
        (one("Bysanti's PDUFA date, previously December 12, 2026, is now March 12, 2027."), H,
         "old and new date with no 'extend' word"),
        (one("Bysanti has a PDUFA target action date of December 12, 2025.", s=None), H,
         "last year's day and month never restate this year's date"),
        (one("On November 4, 2026 the FDA approved Bysanti for bipolar I disorder."), H, "an approval"),
        (one("Bysanti was approved by the FDA on November 3, 2026."), H, "'was approved by the FDA'"),
        (one("Bysanti was approved by the U.S. Food and Drug Administration. Sales begin soon."), H,
         "'U.S.' no longer splits the sentence that records the approval"),
        (one("Vanda received approval from the FDA for Bysanti."), H, "'received approval from the FDA'"),
        (one("The FDA issued a CRL for Bysanti."), H, "'issued a CRL'"),
        (one("Bysanti was approved in November and will be launched in January."), H, "approved, will launch"),
        (assess(row, src, [("2026-11-05", "u", "The Bysanti PDUFA target action date is December 12, 2026. "
                            "The FDA extended the Bysanti PDUFA target action date to March 12, 2027.")],
                True)[0], H, "a restatement never outweighs a moved date in the same filing"),
        (one("Revenue grew. Fanapt sales rose in the fourth quarter of 2026."), C, "unrelated filing text"),
        (one("", edgar=False), H, "no EDGAR search, never auto-confirmed"),
        (one("", s="page without it"), H, "quote gone and nothing restates it"),
        (one("", s=None), H, "source unreadable and nothing restates it"),
        (one("In March 2025 Vanda received a complete response letter for Bysanti."), C,
         "a recap of an FDA action before the row's source is history"),
        (one("In August 2026 the FDA approved Bysanti for schizophrenia.",
             r=dict(row, _d=dict(row["_d"], source="8-K 2026-08-10"))), H,
         "a month-only date counts as the month's last day, so it is not before an Aug 10 source"),
        (one("The Bysanti NDA remains under review with a PDUFA target action date of December 12, 2026.",
             shared=True), H, "another row names the drug: newer text about it goes to a human"),
        (one("", shared=True), C, "another row names the drug, nothing newer: the source confirms"),
    ]
    rq = {"id": "y", "t": "Y", "type": "Readout", "st": "Guided", "d": "2026-12-31", "dp": "quarter",
          "name": "sonelokimab VELA-TEEN final results",
          "_d": {"guidance_text": "expects topline data from VELA-TEEN in the fourth quarter of 2026",
                 "guided_filed": "2026-08-10"}}
    for text, want, why in [
        ("MoonLake now expects sonelokimab VELA-TEEN topline data in the first quarter of 2027.", H,
         "a guided readout that slipped a quarter"),
        ("MoonLake now expects sonelokimab VELA-TEEN topline data in February 2027.", H, "slipped to a month"),
        ("Sonelokimab VELA-TEEN topline data are now expected by year-end 2027.", H, "'year-end 2027'"),
        ("Sonelokimab VELA-TEEN topline data timing moved (previously Q4 2026, now Q1 2027).", H,
         "previously and now in one sentence"),
        ("MoonLake expects sonelokimab VELA-TEEN topline data in the fourth quarter of 2026.", C,
         "a readout restated at its quarter"),
        ("MoonLake discontinued the sonelokimab VELA-TEEN trial.", H, "a stopped trial"),
    ]:
        cases.append((assess(rq, None, [("2026-11-10", "u", text)], True)[0], want, why))
    cases += [
        (drug_tokens("IDVYNSO - treatment-naive HIV-1 (P053) and 96-week data (sNDAs)")[:1], ["IDVYNSO"],
         "generic words never become search tokens"),
        (drug_tokens("MBX 4291 (GLP-1/GIP co-agonist prodrug) Phase 1 MAD (Part C, Unblinded)"), ["MBX 4291"],
         "a spaced code is the drug"),
        (drug_tokens("LB2501 (in vivo CD19/CD20 dual-targeting CAR-T) First-in-human"), ["LB2501"],
         "targets are not drugs"),
        (drug_tokens("Bezuclastinib + sunitinib - (PEAK)"), ["Bezuclastinib"], "a trial named PEAK is not searched"),
        (drug_tokens("Relacorilant - (GRACE resubmission)"), ["Relacorilant"], "nor GRACE"),
        (drug_tokens("Cemdisiran (C5 RNAi) - (NIMBLE)"), ["Cemdisiran"], "nor RNAi"),
        (len(sentences("Bysanti was approved by the U.S. Food and Drug Administration on Nov. 3, 2026. "
                       "The next sentence is long enough.")), 2, "abbreviations do not split sentences"),
        (ledger_entry({"checked": "2026-11-17", "verdict": "FIXED", "by": "red team"}, "2026-11-25", "s", "n")
         .get("prior", {}).get("verdict"), "FIXED", "a person's entry is kept under 'prior'"),
        (guard_deadline({"d": "2026-12-12"}, {"checked": "2026-11-17"}).isoformat(), "2026-12-18",
         "the guard blocks 31 days after a check once the row is 14 days out"),
    ]
    bad = [(why, got, want) for got, want, why in cases if got != want]
    for why, got, want in bad:
        print(f"SELF-TEST FAILED: {why}: got {got}, want {want}")
    return not bad


# ---------------------------------------------------------------- network

def get(url, throttle=0.15, binary=False):
    time.sleep(throttle)
    req = urllib.request.Request(url, headers=dict(UA, **{"Accept-Encoding": "identity"}))
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


_CIK = {}


def cik_for(ticker):
    if not _CIK:
        j = json.loads(get("https://www.sec.gov/files/company_tickers.json"))
        for v in j.values():
            _CIK[str(v.get("ticker", "")).upper()] = int(v.get("cik_str", 0))
    return _CIK.get((ticker or "").upper())


def source_date(d):
    v = d.get("guided_filed")
    if v and re.match(r"\d{4}-\d{2}-\d{2}", str(v)):
        return str(v)[:10]
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(d.get("source") or ""))
    return m.group(1) if m else None


def newer_filings(row, cik, since, today):
    """Every EDGAR document since `since` that names any of the row's drug tokens (8-K, 6-K, 10-Q,
    10-K, exhibits included). Raises when a search fails or more than MAX_FILINGS documents match, so
    the row goes to a human rather than being judged on a partial read."""
    seen = {}
    for tok in drug_tokens(row.get("name")):
        q = urllib.parse.quote(f'"{tok}"')
        url = (f"https://efts.sec.gov/LATEST/search-index?q={q}&dateRange=custom&startdt={since}"
               f"&enddt={today}&forms=8-K,6-K,10-Q,10-K&ciks={cik:010d}")
        j = json.loads(get(url, 0.2))
        for h in (j.get("hits", {}) or {}).get("hits", []) or []:
            src = h.get("_source") or {}
            fname = str(h.get("_id", "")).split(":", 1)[-1]
            accn = str(src.get("adsh", "")).replace("-", "")
            if fname and accn:
                seen[f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{fname}"] = str(src.get("file_date", ""))[:10]
    if len(seen) > MAX_FILINGS:
        raise RuntimeError(f"{len(seen)} SEC documents since {since} name this drug; too many to judge automatically")
    out = []
    for doc, fdate in sorted(seen.items(), key=lambda kv: kv[1], reverse=True):
        out.append((fdate, doc, page_text(get(doc))))   # an unreadable document fails the whole search
    return out


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def open_rows(rows, today):
    for r in rows:
        if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Under review"):
            yield r
        elif r.get("type") == "Readout" and r.get("st") == "Guided" and r.get("d", "") >= today.isoformat():
            yield r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--today", help="pretend today is this Eastern date (testing)")
    a = ap.parse_args()
    if not self_test():
        print("*** DATE RECHECK NEEDS A HUMAN: the re-check's own self-test failed; nothing was re-checked ***")
        return 1
    if a.self_test:
        print("OK -- re-check logic: restated/unchanged dates confirm; moved dates, FDA actions, unreadable "
              "sources with nothing newer and non-SEC filers go to a human.")
        return 0
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    today = dt.date.fromisoformat(a.today) if a.today else eastern_today()
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    led = json.load(io.open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {"checks": {}}
    checks = led.setdefault("checks", {})
    opened = list(open_rows(rows, today))
    # the guard's newer-disclosure rule: the newest source any open row of a company cites
    newest = {}
    for r in opened:
        sd = source_date(r.get("_d") or {})
        if sd and sd <= today.isoformat() and (r["t"] not in newest or sd > newest[r["t"]][0]):
            newest[r["t"]] = (sd, r)
    todo = due_rows(rows, checks, today)
    print(f"re-checking {len(todo)} open date(s) due by {today + dt.timedelta(days=WINDOW_DAYS)} "
          f"(checked more than {FRESH_DAYS} days ago or never)\n")
    confirmed, urgent, waiting = [], [], []
    for r in todo:
        d = r.get("_d") or {}
        prev = checks.get(r["id"]) or {}
        url = d.get("source_url") or d.get("guidance_url")
        stext = None
        if url:
            try:
                stext = page_text(get(url, 0.3))
            except Exception:
                stext = None
        toks = {t.lower() for t in drug_tokens(r.get("name"))}
        shared = any(o["id"] != r["id"] and o.get("t") == r.get("t") and
                     toks & {t.lower() for t in drug_tokens(o.get("name"))} for o in opened)
        edgar_ran, filings, extra_fail = False, [], False
        own = source_date(d)
        try:
            cik = cik_for(r.get("t"))
            if cik and toks:
                since = max(x for x in (own, prev.get("checked")) if x) if (own or prev.get("checked")) else \
                    (today - dt.timedelta(days=120)).isoformat()
                filings = newer_filings(r, cik, since, today.isoformat())
                edgar_ran = True
        except Exception as e:
            print(f"  [{r['id']}] EDGAR search failed: {str(e)[:160]}")
        # a newer document this company published (cited by another of its rows) is read too
        nd = newest.get(r.get("t"))
        if nd and nd[1]["id"] != r["id"] and (own is None or nd[0] > own) and nd[0] > prev.get("checked", ""):
            nu = (nd[1].get("_d") or {}).get("source_url") or (nd[1].get("_d") or {}).get("guidance_url")
            try:
                filings.append((nd[0], nu, page_text(get(nu, 0.3))))
            except Exception:
                extra_fail = True
        verdict, detail, kind = assess(r, stext, filings, edgar_ran and not extra_fail, shared)
        if extra_fail and verdict == "HUMAN" and kind != "signal":
            detail = f"a newer document cited by {nd[1]['id']} could not be read; " + detail
        if verdict == "CONFIRMED":
            note, _, source = detail.partition("|")
            confirmed.append(r["id"])
            if not a.dry_run:
                checks[r["id"]] = ledger_entry(prev, today.isoformat(), source or url or "", note)
            print(f"  CONFIRMED {r['id']} [{r['t']}] due {r['d']}: {note[:160]}")
        else:
            block = guard_deadline(r, prev)
            if nd and nd[1]["id"] != r["id"] and (own is None or nd[0] > own) and nd[0] > prev.get("checked", ""):
                block = today          # the guard's newer-disclosure rule already applies
            (urgent if kind == "signal" or (block - today).days <= 7 else waiting).append((r, detail, block))
    if urgent:
        print(f"\n*** DATE RECHECK NEEDS A HUMAN: {len(urgent)} open date(s) could not be confirmed automatically ***")
        print("Re-open the source, then record_date_check.py <row id> <verdict> <url> [note].\n")
        for r, why, block in urgent:
            print(f"  {r['id']} [{r['t']}] due {r['d']}, guard blocks from {block} "
                  f"({r.get('name', '')[:60]}): {why[:300]}")
    if waiting:
        print(f"\nNot yet urgent ({len(waiting)}): nothing says these moved, but nothing re-stated them either. "
              "They are raised a week before the date guard would block on them.")
        for r, why, block in waiting:
            print(f"  {r['id']} [{r['t']}] due {r['d']}, guard blocks from {block}: {why[:200]}")
    if not todo:
        print("Nothing to re-check: every open date due in the next 30 days was checked in the last "
              f"{FRESH_DAYS} days.")
    elif not (urgent or waiting):
        print("\nEvery open date re-checked today was re-read and agrees with its sources.")
    if confirmed and not a.dry_run:
        io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print(f"\n{len(confirmed)} confirmed automatically, {len(urgent)} for a human now, {len(waiting)} not yet urgent.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n*** DATE RECHECK NEEDS A HUMAN: the re-check script failed (above); no open date was re-checked ***")
        sys.exit(0)
