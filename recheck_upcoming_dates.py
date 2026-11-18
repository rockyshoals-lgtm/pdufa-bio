# -*- coding: utf-8 -*-
"""recheck_upcoming_dates.py -- every rebuild re-reads the sources of the dates that matter next.

WHY (red team 2026-11-18)
tests/test_date_checks_current.py blocks the rebuild when a date due in the next 14 days was not
checked against its source in the last 30 days. Without a recurring re-check, every rebuild stops on
2026-12-18, when the red team's Nov 17 checks age out. A person re-reading 40 rows every month is the
failure mode we already had. So each rebuild re-reads, for every open PDUFA goal and company-guided
readout due in the next 30 days:

  1. the row's own source: does the page still carry the quoted sentence?
  2. the company's SEC filings since that source (8-K, 6-K, 10-Q, 10-K, EDGAR full-text search on the
     drug's name): every sentence that names the drug next to a goal date or a data/readout timing
     must state the row's date at the row's precision, and no sentence may say the FDA acted on it.

A row passes only when (1) or a newer filing restating the date holds, the EDGAR search ran, and no
filing contradicts the date or records an FDA action. Then the ledger (_date_checks.json) gets a
CONFIRMED entry, by "auto re-check", naming the newest document that states the date.

Everything else is NEVER written to the ledger. It is listed under "DATE RECHECK NEEDS A HUMAN" and the
rebuild's review issue carries it: a moved date, a possible approval or CRL, a source that no longer
carries its quote with nothing newer restating it, or a company that does not file with the SEC
(Roche, for one). Those keep the guard's protection: if nobody looks, the guard blocks when the date is
14 days out, which is the point.

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
MAX_FILINGS = 6           # newest EDGAR documents read per row
BY = "auto re-check (recheck_upcoming_dates.py)"

GENERIC = {"phase", "study", "trial", "data", "topline", "readout", "results", "final", "oral", "once",
           "weekly", "daily", "lower", "doses", "dose", "treatment", "adults", "adult", "children",
           "patients", "pediatric", "new", "snda", "sndas", "sbla", "nda", "bla", "maa", "label",
           "expansion", "naive", "the", "and", "with", "plus", "combination", "program", "pivotal",
           "interim", "primary", "registrational", "cohort", "part", "extension", "update", "first",
           "adolescent", "adolescents", "infants", "week", "weeks", "month", "year", "season", "second",
           "hiv-1", "hiv", "hbv", "hcv", "rsv", "covid", "cancer", "disease", "syndrome", "therapy",
           "updated", "publication", "healthy", "clinical", "small", "vivo", "prevention", "follow-up",
           "advanced", "monotherapy", "investigator-sponsored", "long-term", "fixed-duration",
           "presentation", "allogeneic", "oral", "inhalation", "cream", "foam", "film", "capsule"}

KEY_PDUFA = re.compile(r"\bPDUFA\b|target action date|goal date|action date", re.I)
KEY_READOUT = re.compile(r"\btopline\b|\bdata\b|\bresults?\b|\bread[- ]?out\b", re.I)
# a sentence carrying any date-like expression (anything quote_states_date could judge)
DATE_EXPR = re.compile(r"\b(?:january|february|march|april|may|june|july|august|september|october|"
                       r"november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{1,2}\b|"
                       r"\b(?:first|second|third|fourth)\s+quarter\b|\b[1-4]Q\s?'?\d{2,4}\b|\bQ[1-4]\s?'?\d{2,4}\b|"
                       r"\b(?:first|second)\s+half\b|\b[12]H\s?'?\d{2,4}\b|\bH[12]\s?'?\d{2,4}\b|"
                       r"\bmid-?\s?20\d\d\b|\b(?:end|year-end) of 20\d\d\b", re.I)
FDA_ACTED = re.compile(r"\b(?:FDA|Food and Drug Administration)\b[^.]{0,160}?\b(?:has approved|approved|granted"
                       r"(?: accelerated| full| traditional)? approval|issued a complete response letter)\b|"
                       r"\breceived\b[^.]{0,80}?\b(?:FDA approval|complete response letter)\b", re.I)
FUTURE = re.compile(r"\bif approved\b|\bexpect|\bplan|\banticipat|\bpotential|\bwould\b|\bwill\b|\bmay\b|"
                    r"\bseek|\bsubmi|\baccept", re.I)


# ---------------------------------------------------------------- pure logic (self-tested offline)

def _ok_token(w):
    w = w.strip("-")
    parts = [p for p in w.lower().split("-") if p]
    if len(w) < 4 or w.lower() in GENERIC or any(p in GENERIC for p in parts):
        return None
    if re.fullmatch(r"\d+-week|[a-z]+-\d", w.lower()):
        return None
    return w


def drug_tokens(name):
    """The row's drug: the first distinctive word of its name, plus the first word inside the first
    parenthesis (usually the INN or the code), never generic trial words. Search uses the first."""
    s = str(name or "")
    out = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", re.sub(r"\(.*?\)", " ", s)):
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


def sentences(text):
    t = re.sub(r"\s+", " ", text or "")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", t) if len(s.strip()) > 20]


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


_MON = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                                          "oct", "nov", "dec"])}


def is_history(sentence, src_iso):
    """True when every date the sentence names is before the row's own source: a recap ("received a
    complete response letter in March 2025"), not news. A sentence with no date is never history."""
    if not src_iso:
        return False
    latest = []
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?:(\d{1,2}),?\s+)?(20\d\d)\b",
                         sentence, re.I):
        mo, day, yr = _MON[m.group(1).lower()[:3]], int(m.group(2) or 28), int(m.group(3))
        try:
            latest.append(dt.date(yr, mo, min(day, 28) if not m.group(2) else day).isoformat())
        except ValueError:
            pass
    if not latest:
        latest = [f"{y}-12-31" for y in re.findall(r"\b(20\d\d)\b", sentence)]
    return bool(latest) and max(latest) < src_iso


def assess(row, source_text, filings, edgar_ran):
    """row: dataset row. source_text: the row's source page text (None if unreadable).
    filings: [(date_iso, url, text)] newer than the row's source, newest first.
    Returns (verdict, detail): verdict 'CONFIRMED' or 'HUMAN'."""
    d = row.get("_d") or {}
    is_pdufa = row.get("type") == "PDUFA"
    quote = d.get("source_quote") if is_pdufa else d.get("guidance_text")
    toks = [t.lower() for t in drug_tokens(row.get("name"))]
    if not toks:
        return "HUMAN", "no distinctive drug name to search filings for"
    key = KEY_PDUFA if is_pdufa else KEY_READOUT
    restated, conflicts, acted = None, [], []
    for fdate, url, text in filings:
        for s in sentences(text):
            low = s.lower()
            if not any(re.search(r"\b" + re.escape(t) + r"\b", low) for t in toks):
                continue
            if FDA_ACTED.search(s) and not FUTURE.search(s):
                if not is_history(s, source_date(d)):
                    acted.append((fdate, url, s[:220]))
                continue
            if not (key.search(s) and DATE_EXPR.search(s)):
                continue
            if quote_states_date(s, row["d"], row.get("dp") or "day", ref_iso=fdate):
                restated = restated or (fdate, url, s[:220])
            else:
                conflicts.append((fdate, url, s[:220]))
    if acted:
        f = acted[0]
        return "HUMAN", f"a filing of {f[0]} may record an FDA action on this drug: \"{f[2]}\" ({f[1]})"
    if conflicts and not (restated and restated[0] >= conflicts[0][0]):
        f = conflicts[0]
        return "HUMAN", f"a filing of {f[0]} gives a different date: \"{f[2]}\" ({f[1]})"
    if not edgar_ran:
        return "HUMAN", "company's SEC filings could not be searched (not an SEC filer, or EDGAR unreachable)"
    src_ok = source_text is not None and quote_still_there(quote, source_text)
    if restated:
        return "CONFIRMED", f"restated in the {restated[0]} filing: \"{restated[2]}\"|{restated[1]}"
    if src_ok:
        return "CONFIRMED", ("source still carries the quoted date; no newer SEC filing names this drug "
                             "with a different date or an FDA action|" + (d.get("source_url") or d.get("guidance_url") or ""))
    if source_text is None:
        return "HUMAN", "source page could not be read and no newer filing restates the date"
    return "HUMAN", "source page no longer carries the quoted sentence and no newer filing restates the date"


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


def self_test():
    row = {"id": "x", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-12", "dp": "day",
           "name": "Bysanti (milsaperidone) - bipolar I",
           "_d": {"source_quote": "PDUFA target action date of December 12, 2026",
                  "source_url": "https://example.invalid/a"}}
    src = "Vanda said the NDA for Bysanti has a PDUFA target action date of December 12, 2026. More."
    same = [("2026-11-05", "u1", "The Bysanti NDA remains under review with a PDUFA target action date of December 12, 2026.")]
    moved = [("2026-11-05", "u2", "The FDA extended the Bysanti PDUFA target action date to March 12, 2027.")]
    acted = [("2026-11-05", "u3", "On November 4, 2026 the FDA approved Bysanti for bipolar I disorder.")]
    other = [("2026-11-05", "u4", "Revenue grew. Fanapt sales rose in the fourth quarter of 2026.")]
    cases = [
        (assess(row, src, [], True)[0], "CONFIRMED", "source still states the date, nothing newer"),
        (assess(row, None, same, True)[0], "CONFIRMED", "source unreadable but a newer filing restates it"),
        (assess(row, src, moved, True)[0], "HUMAN", "a newer filing moves the date"),
        (assess(row, src, acted, True)[0], "HUMAN", "a newer filing records an FDA approval"),
        (assess(row, src, other, True)[0], "CONFIRMED", "unrelated filing text is ignored"),
        (assess(row, src, [], False)[0], "HUMAN", "no EDGAR search, never auto-confirmed"),
        (assess(row, "page without it", [], True)[0], "HUMAN", "quote gone and nothing restates it"),
        (assess(row, None, [], True)[0], "HUMAN", "source unreadable and nothing restates it"),
        (assess(dict(row, _d=dict(row["_d"], source="8-K 2026-08-05")), src,
                [("2026-11-05", "u6", "In March 2025 Vanda received a complete response letter for Bysanti.")],
                True)[0], "CONFIRMED", "a recap of an FDA action before the row's source is history"),
    ]
    rq = {"id": "y", "t": "Y", "type": "Readout", "st": "Guided", "d": "2026-12-31", "dp": "quarter",
          "name": "sonelokimab VELA-TEEN final results",
          "_d": {"guidance_text": "expects topline data from VELA-TEEN in the fourth quarter of 2026"}}
    slip = [("2026-11-10", "u5", "MoonLake now expects sonelokimab VELA-TEEN topline data in the first quarter of 2027.")]
    cases.append((assess(rq, None, slip, True)[0], "HUMAN", "a guided readout that slipped a quarter"))
    cases.append((drug_tokens("IDVYNSO - treatment-naive HIV-1 (P053) and 96-week data (sNDAs)")[:1] == ["IDVYNSO"],
                  True, "generic words never become search tokens"))
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
    toks = drug_tokens(row.get("name"))
    q = urllib.parse.quote(f'"{toks[0]}"')
    url = (f"https://efts.sec.gov/LATEST/search-index?q={q}&dateRange=custom&startdt={since}"
           f"&enddt={today}&forms=8-K,6-K,10-Q,10-K&ciks={cik:010d}")
    j = json.loads(get(url, 0.2))
    hits = (j.get("hits", {}) or {}).get("hits", []) or []
    hits.sort(key=lambda h: str((h.get("_source") or {}).get("file_date", "")), reverse=True)
    out = []
    for h in hits[:MAX_FILINGS]:
        src = h.get("_source") or {}
        fname = str(h.get("_id", "")).split(":", 1)[-1]
        accn = str(src.get("adsh", "")).replace("-", "")
        if not (fname and accn):
            continue
        doc = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{fname}"
        try:
            out.append((str(src.get("file_date", ""))[:10], doc, page_text(get(doc))))
        except Exception:
            continue
    return out


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if not self_test():
        return 1
    if a.self_test:
        print("OK -- re-check logic: restated/unchanged dates confirm; moved dates, FDA actions, unreadable "
              "sources with nothing newer and non-SEC filers go to a human.")
        return 0
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    today = eastern_today()
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    led = json.load(io.open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {"checks": {}}
    checks = led.setdefault("checks", {})
    todo = due_rows(rows, checks, today)
    print(f"re-checking {len(todo)} open date(s) due by {today + dt.timedelta(days=WINDOW_DAYS)} "
          f"(checked more than {FRESH_DAYS} days ago or never)\n")
    confirmed, human = [], []
    for r in todo:
        d = r.get("_d") or {}
        url = d.get("source_url") or d.get("guidance_url")
        stext = None
        if url:
            try:
                stext = page_text(get(url, 0.3))
            except Exception:
                stext = None
        edgar_ran, filings = False, []
        try:
            cik = cik_for(r.get("t"))
            if cik and drug_tokens(r.get("name")):
                prev = (checks.get(r["id"]) or {}).get("checked")
                since = min(x for x in (source_date(d), prev) if x) if (source_date(d) or prev) else \
                    (today - dt.timedelta(days=120)).isoformat()
                filings = newer_filings(r, cik, since, today.isoformat())
                edgar_ran = True
        except Exception as e:
            print(f"  [{r['id']}] EDGAR search failed: {str(e)[:120]}")
        verdict, detail = assess(r, stext, filings, edgar_ran)
        if verdict == "CONFIRMED":
            note, _, newest = detail.partition("|")
            confirmed.append(r["id"])
            if not a.dry_run:
                checks[r["id"]] = {"checked": today.isoformat(), "verdict": "CONFIRMED",
                                   "source": newest or url or "", "by": BY, "note": note[:300]}
            print(f"  CONFIRMED {r['id']} [{r['t']}] due {r['d']}: {note[:160]}")
        else:
            human.append((r, detail))
    if human:
        print(f"\n*** DATE RECHECK NEEDS A HUMAN: {len(human)} open date(s) could not be confirmed automatically ***")
        print("Re-open the source, then record_date_check.py <row id> <verdict> <url> [note].\n")
        for r, why in human:
            print(f"  {r['id']} [{r['t']}] due {r['d']} ({r.get('name', '')[:60]}): {why[:300]}")
    else:
        print("\nEvery open date due in the next 30 days was re-read and agrees with its sources.")
    if confirmed and not a.dry_run:
        io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print(f"\n{len(confirmed)} confirmed automatically, {len(human)} for a human.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
