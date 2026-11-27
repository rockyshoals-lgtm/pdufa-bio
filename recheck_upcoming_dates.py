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
     6-K, 10-Q, 10-K, exhibits): an EDGAR full-text search on the drug, its code in every spelling,
     and its trial name, plus the newest document any other row of the company cites.

A row passes only when the source still carries the quote, the EDGAR search ran in full, and NO newer
document names the drug, its code or its trial. The script never interprets a newer document: the
second red team (2026-11-18) showed a sentence reader confirming "the FDA will not meet the goal date",
"withdrew its BLA" and "suspended dosing", because no word list covers every way a date can move. A
pass writes a CONFIRMED entry (by "auto re-check") to _date_checks.json; a person's earlier entry is
kept whole under "prior". Known gap: when a person's check re-read only the source, filings between
the source and that check are not searched again (the record_date_check.py procedure reads them).

Everything else is NEVER written to the ledger:
  - "DATE RECHECK NEEDS A HUMAN" (the rebuild's review issue carries it): any newer document naming
    the drug (the excerpt shown is the action, hold, withdrawal or date wording nearest a mention); a crash of this script; or any
    unconfirmed row whose date-guard deadline, or whose date itself, is a week away or less.
  - "Not yet urgent": nothing newer names the drug, but the source or EDGAR could not be read (a
    non-SEC filer such as Roche). Listed in the log; raised a week before the guard would block or
    the date falls due.

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
from date_quote_match import norm  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_date_checks.json")
UA = {"User-Agent": "pdufa.bio research support@pdufa.bio"}
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
           "infections", "gel", "systemic", "subretinal", "first-in-human", "dual", "cell", "cells",
           "acting", "engager", "engagers"}
# targets, mechanisms and hyphenated adjectives: they describe a drug, they do not name it
TARGET = re.compile(r"(?i)^(?:cd\d+\w*|[a-z]{2,5}\d+x[a-z]{2,5}\d+|stat\d+|nlrp\d+|fgfr\d+\w*|il-\d+\w*|"
                    r"glp-1\w*|pd-l?1|her2|egfr|kras|bcl-?\d+|pan-\w+|\w+-(?:state|acting|directed|agonist|targeting|"
                    r"targeted|based|like|label|blind|concept|term|line|human|class|dose|week|arm))$")

# Words near a mention of the drug that mean something may have happened to its date: an action, a
# withdrawal, a hold, a moved or missed date. Any newer document naming the drug goes to a person either
# way; these words make it urgent.
SIGNAL = re.compile(r"approv|complete response|\bCRL\b|refus|withdr|extend|extension|delay|postpon|not meet|"
                    r"\bmiss|no longer|originally|previously|\bmoved|revis|resched|suspend|\bhold\b|wind down|"
                    r"deprioriti|discontinu|terminat|\bhalt|\bpaus|stopp|futility|launch|goal date|action date|"
                    r"\bPDUFA\b|topline|top-line|readout|read out", re.I)
WINDOW = 400              # characters either side of a mention that SIGNAL is looked for in


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


def trial_tokens(name, drugs=()):
    """Trial names in the row's name that are safe to search for: capitals with a digit or a hyphen
    (X-NOVA2, HOPE-3, VELA-TEEN, SENTRY-2), never an English word like PEAK or SUMMIT."""
    low = {d.lower() for d in drugs}
    out = []
    for w in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b|\b[A-Z]+\d[A-Z0-9]*\b", str(name or "")):
        if (len(w) >= 4 and w.lower() not in low and w.lower() not in GENERIC and not TARGET.match(w)
                and not re.fullmatch(r"(?i)(?:hiv|hbv|hcv|covid|glp|il|cd|pd)-?\d+\w*", w) and w not in out):
            out.append(w)
    return out


def variants(tok):
    """A code as filings spell it: "MBX 4291", "MBX-4291", "MBX4291"; "D-PLEX100", "D-PLEX 100"."""
    out = {tok}
    if re.search(r"\d", tok):
        bare = re.sub(r"[- ]", "", tok)
        split = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", bare)
        out |= {bare, split, split.replace(" ", "-"), re.sub(r"(?<=[A-Za-z])[- ]?(?=\d)", " ", tok),
                re.sub(r"(?<=[A-Za-z])[- ]?(?=\d)", "-", tok)}
    return sorted(o for o in out if len(o) >= 4)


def search_terms(row):
    toks = drug_tokens(row.get("name"))
    out = []
    for t in toks + trial_tokens(row.get("name"), toks):
        for v in variants(t):
            if v.lower() not in [o.lower() for o in out]:
                out.append(v)
    return out


def mentions(text, terms):
    """Character offsets where any term appears as a word (a suffix like "-gpps" still counts)."""
    out = []
    for t in terms:
        out += [m.start() for m in re.finditer(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text or "", re.I)]
    return sorted(out)


def page_text(raw):
    t = re.sub(r"(?is)<(su[bp])[^>]*>(.*?)</\1>", r"\2", raw or "")     # D-PLEX<sub>100</sub> -> D-PLEX100
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def quote_still_there(quote, text):
    """Every substantial fragment of the quote (split on ellipses) appears in the page."""
    page = norm(text)
    frags = [norm(f) for f in re.split(r"\.\.\.|…", html.unescape(quote or ""))]
    frags = [f.strip(" .,;") for f in frags if len(f.strip(" .,;")) >= 20]
    return bool(frags) and all(f in page for f in frags)


def assess(row, source_text, filings, edgar_ran):
    """row: dataset row. source_text: the row's source page text (None if unreadable).
    filings: [(date_iso, url, text)]: every SEC document since the row's source or last check that
    EDGAR matched on the drug, its code or its trial, plus any newer document of the company that
    names them.
    Returns (verdict, detail, kind).

    The rule is deliberately blunt (second red team, 2026-11-18): reading sentences to decide whether a
    newer filing "restates" the date let "the FDA will not meet the December 12 goal date", "withdrew
    its BLA" and "suspended dosing" through, because no word list covers every way a date can move.
    So the automatic re-check never interprets a newer document. It confirms only what it can know:
    the source still carries the quoted date AND nothing newer has been filed that names the drug.
    Any newer document naming it goes to a person at once ('signal'); the excerpt shown is the first
    action, hold, withdrawal or date word near a mention. 'unverified' (raised a week before the guard
    or the date) is only for a row with nothing newer whose source or EDGAR could not be read."""
    d = row.get("_d") or {}
    quote = d.get("source_quote") if row.get("type") == "PDUFA" else d.get("guidance_text")
    terms = search_terms(row)
    if not drug_tokens(row.get("name")):
        return "HUMAN", "no distinctive drug name to search filings for", "unverified"
    if filings:
        sig = None
        for fdate, url, text in filings:
            hits = mentions(text, terms)
            if not hits:                      # EDGAR matched a spelling we cannot place: read it
                sig = sig or (fdate, url, "names the drug in a form this script cannot locate")
            for h in hits:
                win = text[max(0, h - WINDOW): h + WINDOW]
                m = SIGNAL.search(win)
                if m and not sig:
                    a = max(0, m.start() - 120)
                    sig = (fdate, url, re.sub(r"\s+", " ", win[a:m.end() + 120]).strip())
        if sig:
            return "HUMAN", (f"{len(filings)} newer document(s) name this drug; one of {sig[0]} may record an "
                             f"action or a moved date: \"{sig[2][:240]}\" ({sig[1]})"), "signal"
        newest = max(filings)
        return "HUMAN", (f"{len(filings)} newer document(s) name this drug (newest {newest[0]}, {newest[1]}); "
                         "a person must read them"), "signal"
    if not edgar_ran:
        return "HUMAN", "company's SEC filings could not be searched (not an SEC filer, or EDGAR unreachable)", "unverified"
    if source_text is None:
        return "HUMAN", "source page could not be read", "unverified"
    if not quote_still_there(quote, source_text):
        return "HUMAN", "source page no longer carries the quoted sentence", "unverified"
    return "CONFIRMED", ("source still carries the quoted date, and no SEC filing since names this drug, its "
                         "code or its trial|" + (d.get("source_url") or d.get("guidance_url") or "")), "ok"


def guard_deadline(row, entry):
    """The day tests/test_date_checks_current.py starts blocking the rebuild on this row: 14 days before
    it is due, or 31 days after its last check, whichever is later (it may fall after the due date,
    when the guard will never block on the row)."""
    due = dt.date.fromisoformat(row["d"])
    out = due - dt.timedelta(days=14)
    try:
        out = max(out, dt.date.fromisoformat((entry or {}).get("checked", "")) + dt.timedelta(days=31))
    except Exception:
        pass
    return out


def is_urgent(kind, row, entry, today, newer_rule=False):
    """Raise now: a signal; the guard's newer-disclosure rule already applies; the guard blocks within a
    week; or the date itself is within a week (the guard may never block on it, but it is about to be
    published as current)."""
    due = dt.date.fromisoformat(row["d"])
    return (kind == "signal" or newer_rule or (guard_deadline(row, entry) - today).days <= 7
            or (due - today).days <= 7)


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
    """A CONFIRMED re-read. A person's earlier entry is kept whole (its own history included) under
    "prior", never overwritten; an earlier automatic entry is replaced, its "prior" carried forward."""
    e = {"checked": today, "verdict": "CONFIRMED", "source": source, "by": BY, "note": note[:300]}
    if prev:
        p = prev.get("prior") if prev.get("by") == BY else dict(prev)
        if p:
            e["prior"] = p
    return e


def self_test():
    row = {"id": "x", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-12", "dp": "day",
           "name": "Imsidolimab (ANB019) - (GEMINI-2)",
           "_d": {"source_quote": "PDUFA target action date of December 12, 2026",
                  "source_url": "https://example.invalid/a", "source": "8-K 2026-08-05"}}
    src = "Vanda said the BLA for imsidolimab has a PDUFA target action date of December 12, 2026. More."

    def one(text, s=src, edgar=True, r=row):
        return assess(r, s, [("2026-11-25", "u", text)] if text else [], edgar)

    H, C = "HUMAN", "CONFIRMED"
    cases = [(one("")[0], C, "source still states the date and nothing newer names the drug")]
    # second red team: every one of these was CONFIRMED by the sentence reader
    for text in [
        "The FDA notified Vanda that it will not meet the imsidolimab PDUFA target action date of December 12, 2026.",
        "Vanda does not expect the FDA to take action on the imsidolimab BLA by the December 12, 2026 goal date.",
        "The imsidolimab goal date, originally December 12, 2026, has been moved.",
        "Vanda voluntarily withdrew its Biologics License Application for imsidolimab.",
        "Vanda has decided to discontinue development of imsidolimab.",
        "The U.S. FDA approved QUIMILZA (imsidolimab-gpps) for generalized pustular psoriasis on November 20, 2026.",
        "On November 20, 2026, the FDA approved the Company's BLA. The product is imsidolimab.",
        "In 2025, Vanda submitted the BLA for imsidolimab, which was approved earlier this month.",
        "GEMINI-2 results were presented; the FDA review continues.",
    ]:
        cases.append((one(text)[::2], (H, "signal"), f"newer text naming the drug: {text[:50]}"))
    cases.append((one("Imsidolimab is one of our pipeline products.")[::2], (H, "signal"),
                  "a bare newer mention goes to a person too"))
    cases += [
        (one("", edgar=False)[0], H, "no EDGAR search, never auto-confirmed"),
        (one("", s="page without it")[0], H, "quote gone"),
        (one("", s=None)[0], H, "source unreadable"),
        (one("Revenue grew. Fanapt sales rose.")[0], H,
         "a document EDGAR matched but where the drug cannot be located is read by a person"),
    ]
    rx = {"id": "y", "t": "XENE", "type": "Readout", "st": "Guided", "d": "2026-12-31", "dp": "month",
          "name": "azetukalner X-NOVA2 Phase 3 Phase 3 topline",
          "_d": {"guidance_text": "expects topline data from X-NOVA2 in December 2026"}}
    for text in ["Xenon has suspended dosing in the X-NOVA2 study.",
                 "Topline data from X-NOVA2 are now expected in the first quarter of 2027.",
                 "Xenon no longer expects to report azetukalner topline data in December 2026."]:
        cases.append((assess(rx, None, [("2026-11-25", "u", text)], True)[:3:2], (H, "signal"),
                      f"readout: {text[:40]}"))
    cases += [
        ("X-NOVA2" in search_terms(rx), True, "the trial name is searched"),
        (set(variants("MBX 4291")) >= {"MBX 4291", "MBX-4291", "MBX4291"}, True, "spaced codes in every spelling"),
        ("D-PLEX 100" in variants("D-PLEX100"), True, "D-PLEX100 also as D-PLEX 100"),
        (mentions(page_text("D-PLEX<sub>100</sub> met its endpoint"), ["D-PLEX100"]) != [], True,
         "subscripts are joined, not spaced"),
        (mentions("QUIMILZA (imsidolimab-gpps) approved", ["imsidolimab"]) != [], True,
         "an FDA suffix does not hide the drug"),
        (trial_tokens("Bezuclastinib + sunitinib - (PEAK)", ["Bezuclastinib"]), [], "PEAK is not searched"),
        (drug_tokens("IDVYNSO - treatment-naive HIV-1 (P053) and 96-week data (sNDAs)")[:1], ["IDVYNSO"],
         "generic words never become search tokens"),
        (drug_tokens("MBX 4291 (GLP-1/GIP co-agonist prodrug) Phase 1 MAD (Part C, Unblinded)"), ["MBX 4291"],
         "a spaced code is the drug"),
        (drug_tokens("LB2501 (in vivo CD19/CD20 dual-targeting CAR-T) First-in-human"), ["LB2501"],
         "targets are not drugs"),
        (drug_tokens("CLN-978 (CD19xCD3 T cell engager) ongoing clinical trials"), ["CLN-978"], "nor 'cell'"),
        (drug_tokens("Relacorilant - (GRACE resubmission)"), ["Relacorilant"], "nor GRACE"),
        (drug_tokens("Cemdisiran (C5 RNAi) - (NIMBLE)"), ["Cemdisiran"], "nor RNAi"),
        (ledger_entry({"checked": "2026-11-17", "verdict": "FIXED", "by": "red team",
                       "prior": {"verdict": "HELD"}}, "2026-11-25", "s", "n")["prior"].get("prior"),
         {"verdict": "HELD"}, "a person's entry is kept whole under 'prior', its own history too"),
        (is_urgent("unverified", {"d": "2026-11-30"}, {"checked": "2026-11-17"}, dt.date(2026, 11, 24)), True,
         "a row due within a week is raised even when the guard would never block on it"),
        (is_urgent("unverified", {"d": "2026-12-20"}, {"checked": "2026-11-17"}, dt.date(2026, 11, 24)), False,
         "an unverified row with weeks to go waits"),
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
    """Every EDGAR document since `since` that names the row's drug, its code (every spelling) or its
    trial (8-K, 6-K, 10-Q, 10-K, exhibits included). A document filed on `since` itself is included. Raises when a search fails or more than MAX_FILINGS documents match, so
    the row goes to a human rather than being judged on a partial read."""
    seen = {}
    for tok in search_terms(row):
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
        newest = max(seen.items(), key=lambda kv: kv[1])
        return [(newest[1], f"EDGAR full-text search: {len(seen)} documents since {since}, newest {newest[0]}",
                 "")]           # too many to fetch: assess() sends the row to a person
    
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
        print("OK -- re-check logic: a date confirms only when its source still carries it and no newer SEC "
              "filing names the drug, its code or its trial; everything else goes to a person.")
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
        toks = drug_tokens(r.get("name"))
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
        # the guard's newer-disclosure rule: a newer document this company published (cited by another of
        # its rows) after this row's last check. It is read; if it names this drug it goes to a person.
        nd = newest.get(r.get("t"))
        newer_rule = bool(prev.get("checked") and nd and nd[1]["id"] != r["id"] and
                          (own is None or nd[0] > own) and nd[0] > prev["checked"])
        if newer_rule:
            nu = (nd[1].get("_d") or {}).get("source_url") or (nd[1].get("_d") or {}).get("guidance_url")
            try:
                nt = page_text(get(nu, 0.3))
                if mentions(nt, search_terms(r)):
                    filings.append((nd[0], nu, nt))
            except Exception:
                extra_fail = True
        verdict, detail, kind = assess(r, stext, filings, edgar_ran and not extra_fail)
        if extra_fail and verdict == "HUMAN" and kind != "signal":
            detail = f"a newer document cited by {nd[1]['id']} could not be read; " + detail
        if verdict == "CONFIRMED":
            note, _, source = detail.partition("|")
            confirmed.append(r["id"])
            if not a.dry_run:
                checks[r["id"]] = ledger_entry(prev, today.isoformat(), source or url or "", note)
            print(f"  CONFIRMED {r['id']} [{r['t']}] due {r['d']}: {note[:160]}")
        else:
            block = today if newer_rule else guard_deadline(r, prev)
            (urgent if is_urgent(kind, r, prev, today, newer_rule) else waiting).append((r, detail, block))
    if urgent:
        print(f"\n*** DATE RECHECK NEEDS A HUMAN: {len(urgent)} open date(s) could not be confirmed automatically ***")
        print("Re-open the source, then record_date_check.py <row id> <verdict> <url> [note].\n")
        for r, why, block in urgent:
            print(f"  {r['id']} [{r['t']}] due {r['d']}, guard blocks from {block} "
                  f"({r.get('name', '')[:60]}): {why[:300]}")
    if waiting:
        print(f"\nNot yet urgent ({len(waiting)}): nothing says these moved, but nothing re-stated them either. "
              "They are raised a week before the date guard would block on them, or a week before they are due.")
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
