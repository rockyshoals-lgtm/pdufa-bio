#!/usr/bin/env python3
"""
readout_scan.py — FORWARD-looking readout guidance, time-sliced. Fast.

WHY THIS EXISTS ALONGSIDE phase_readout_miner.py
------------------------------------------------
The miner is a CENSUS builder: CT.gov + SEC + newswire, 1,500-6,000 doc fetches, 7-30 min. It
answers "what is the 2026H2 pipeline". Keep it. Run it weekly.

This answers a different question, the one that pays: "WHICH COMPANY SAID, IN THE LAST 45 DAYS,
THAT A READOUT IS COMING?" It runs in seconds, so it can run every morning.

WHAT THE RED TEAM FOUND (2026-07-17, measured against live EDGAR)
----------------------------------------------------------------
1. THE PHRASE LIST MIXES TWO OPPOSITE THINGS, AND THE FLAT QUOTA TREATS THEM THE SAME:
      FORWARD  "expects to report topline"    81 docs  -> a readout is COMING. TRADEABLE.
      PAST     "Topline Results"           2,337 docs  -> it already printed. History.
   Same 57-doc quota each. The 2,337-doc past-tense phrase drowns the 81-doc forward one, and
   the forward one is the entire point.

2. TWO GENERIC PHRASES ARE 45% OF THE CORPUS AND ~0 SIGNAL:
      "will host a conference call"  8,000+ docs (29.3%)
      "conference call to discuss"   4,288  docs (15.7%)
   Every company hosts conference calls.

3. A DUPLICATE: "Topline Results" and "topline results" both return 2,337 — EDGAR FTS is
   CASE-INSENSITIVE. It is the same query twice, burning a quota slot and 57 fetches.

4. THE SAMPLE IS RELEVANCE-RANKED, NOT TIME-RANKED. One call per phrase over 450 days keeps
   "the first 57", which is whatever EDGAR's scorer likes. The .bat calls that arbitrary; it is
   worse than arbitrary, it is BIASED, and a 14-month-old guidance is worthless because the
   window it promised has already closed.

PROVEN: an 8-phrase, 45-day, 7-day-sliced walk = 56 FTS calls, ~8 seconds, ZERO doc fetches,
and it surfaced 21 biotech tickers the workbook did not have — including CRBP and AVLN with
FORWARD guidance, and CRBP is already in the tape recorder's always-record list.

ADJACENCY (David's finding, and he is right):
   EDGAR FTS matches quoted phrases by ADJACENCY. "to report topline" does NOT match
   "to Report 36-Week Topline Results" — the intervening words break it. So: search SHORT
   universal fragments that FTS can hit, then regex the FETCHED DOC for the date. Two stages.
   My first live-news scanner tried to regex headlines directly and scored 0 on KLRS.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FTS = "https://efts.sec.gov/LATEST/search-index"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# ---------------------------------------------------------------------------- phrases
# FORWARD: the company is telling you a readout is COMING. This is the whole product.
# Corpus sizes measured 2026-07-17 over 450d/8-K+6-K — note how SMALL they are. That is the
# point: they are specific. A flat quota starves them to feed a 2,337-doc past-tense phrase.
FORWARD = [
    "expects to report topline",      # 81
    "expect to announce topline",     # 34
    "plans to report topline",        # 8
    "on track to report",             # 181
    "anticipate reporting",           # 110
    "initial data expected",          # 59
    "readout expected",               # 174
    "data are expected",              # 158
    "results are expected",           # 410
    "results anticipated",            # 1,725
    "data expected in",               # 696
    "interim analysis expected",      # 19
    "topline data expected",
    "expects to announce",
    "we expect topline",
    # ADDED 2026-07-18 — more FORWARD phrasings mined from the historical catalyst descriptions
    # and the blank-window filings. Each is a distinct way a company says "a readout is coming"
    # that the list above did not cover. Two-stage still applies: these FIND the filing; fetch_date
    # extracts the window with all the guards (fiscal/past/quarter-bucket).
    "data readout expected",
    "expected to report data",
    "expect to report data",
    "primary endpoint data expected",
    "results expected in",
    "data anticipated in",
    "expects to present",
    "on track to deliver",
    "readout anticipated",
    "results to be reported",
    "data are anticipated",
    "expects data",
    "topline readout",
    "proof-of-concept data expected",
]

# PAST: it already happened. Builds the universe, does NOT give you a trade. Weekly, not daily.
PAST = [
    "Topline Results",                # 2,337  (NB: "topline results" is the SAME QUERY — FTS
    "topline results from",           # 1,357   is case-insensitive. Do not add it back.)
    "announces topline",              # 36
    "reports topline",                # 12
    "to discuss the topline",         # 16
    "topline data",                   # 2,406
    "top-line results",               # 919
    "data readout",                   # 834
    "primary endpoint data",          # 76
    "pivotal data",                   # 167
]

# DELIBERATELY EXCLUDED — 45% of the corpus, ~0 readout signal:
#   "will host a conference call"  (8,000+, 29.3%)
#   "conference call to discuss"   (4,288,  15.7%)
# Every company hosts conference calls. They belong in a scheduling-specific pass, if at all.
EXCLUDED = ["will host a conference call", "conference call to discuss"]

FORMS = "8-K,6-K"
BIO_SIC = {"2836", "2834", "8731", "3826", "3841"}

# LEAD regexes — run on the FETCHED DOC, not the headline. This is the second stage that makes
# the short-fragment search work.
DATE_PATTERNS = [
    re.compile(r"\b(1[0-2]|[1-9])[/-](3[01]|[12]\d|0?[1-9])[/-](20\d{2})\b"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|"
               r"November|December)\s+(\d{1,2}),?\s+(20\d{2})\b", re.I),
    re.compile(r"\b(first|second|third|fourth|1st|2nd|3rd|4th|Q[1-4]|1H|2H)\s+"
               r"(?:quarter\s+|half\s+)?(?:of\s+)?(20\d{2})\b", re.I),
    re.compile(r"\b(early|mid|late)[-\s](20\d{2})\b", re.I),
]
# NEAR — the readout anchors we look for a date NEXT TO. Broadened 2026-07-18: the old set
# (topline|readout|data|primary endpoint|interim|pivotal) MISSED "results anticipated in 2H
# 2026" because "results" was not an anchor — 34 of 67 rows came back blank, many for exactly
# this reason. Adding results/efficacy/safety/endpoint/proof-of-concept/analysis roughly
# doubles recall. The cost — "results" also means FINANCIAL results — is paid by FISCAL_RX
# below, which rejects the accounting/offering contexts this broadening would otherwise let in.
NEAR = re.compile(
    r"\b(topline|top-line|readout|read-out|primary endpoint|co-primary|secondary endpoint|"
    r"interim|pivotal|proof[\s-]of[\s-]concept|data\b|results?\b|efficacy|safety data|"
    r"\bcohort|dose[\s-]expansion|analysis\b|met the|did not meet)\b", re.I)

# FISCAL / OFFERING / ACCOUNTING context — if this appears near the matched date, the "results"
# are FINANCIAL and the date is a fiscal year end or an offering timeline, NOT a clinical readout.
# GLMD 2026-07-08 produced window "December 31, 2026" from: "results...to be expected for the
# YEAR ENDING December 31, 2026. Note 2 - Summary of significant ACCOUNTING POLICIES". HELP's
# three rows all came from OFFERING press releases ("net proceeds from the Offering"). Reject.
FISCAL_RX = re.compile(
    r"year end(ed|ing)|fiscal year|fiscal 20\d\d|accounting polic|financial statements|"
    r"balance sheet|net proceeds|the offering\b|registered direct|underwritten|"
    r"securities purchase|shelf registration|private placement|per share\b|gross proceeds|"
    r"quarterly report|annual report|10-Q|10-K|form 20-F|dividend", re.I)

# ---------------------------------------------------------------------------------------------
# THE DATELINE BUG — measured on the 2026-07-17 run, 16 of 40 windows (40%) were WRONG.
#
#   GUTS  filed 2026-07-15  ->  window "July 15, 2026"
#   CANF  filed 2026-07-06  ->  window "JULY 6, 2026"
#   TARS  filed 2026-07-08  ->  window "July 8, 2026"
#
# Every one is `window == filed`. The old fetch_date took the FIRST NEAR hit and the FIRST date
# within +/-220 chars. NEAR matches the bare word "data", which appears on slide 1 of every
# investor deck — right next to THE COVER DATE. So it returned the day the deck was published
# and called it a readout window. Add the 5 "March 31, 2026" fiscal-period references and 52%
# of the column was fiction. I reported CANF -> "July 6" to David from this column.
#
# THREE RULES, each one killing a specific observed failure:
#   1. A date equal to the filing date is the DATELINE. Reject it. (kills 16)
#   2. A date BEFORE the filing cannot be a future readout. Reject it. (kills 5 fiscal refs)
#   3. Require FORWARD language in the same window. "Reports Positive Results" is not guidance
#      no matter what date sits beside it.
# And score every candidate rather than taking the first — real guidance ("2H 2026") is usually
# on page 6, while the dateline is always on page 1.
# ---------------------------------------------------------------------------------------------
FWD_NEAR = re.compile(
    r"\b(expects?|expected|anticipat\w+|plans?|planned|on track|will report|will be reported|"
    r"to report|to announce|upcoming|guidance|projected|remains? on track|targeting)\b", re.I)
VAGUE_RX = re.compile(
    r"\b(?:first|second|third|fourth|1st|2nd|3rd|4th|Q[1-4]|1H|2H|early|mid|late)\b[-\s]?"
    r"(?:quarter|half)?\s*(?:of\s+)?20\d{2}\b", re.I)
_MONTHS = ("january february march april may june july august september october november "
           "december").split()


def _hard_date(s):
    """'July 15, 2026' -> date. None for vague periods and unparseable junk."""
    m = re.match(r"\s*([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(20\d{2})\s*$", s or "")
    if m:
        try:
            return dt.date(int(m.group(3)), _MONTHS.index(m.group(1).lower()) + 1,
                           int(m.group(2)))
        except (ValueError, IndexError):
            return None
    m = re.match(r"\s*(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\s*$", s or "")
    if m:
        try:
            return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
    return None


# THE QUARTER-BUCKET TRAP — discovered 2026-07-18 comparing our list to BiopharmaCatalyst.
# BPC (and many trackers) store "Q3 2026" as the HARD DATE 2026-09-30, "2H 2026" as 2026-12-31,
# "mid-2026" as 2026-08-31. Row after row landed on a quarter-end with catalyst text that said
# "topline data due in 3Q 2026" or even "presented at SAWC 2025". So a date sitting EXACTLY on
# Mar 31 / Jun 30 / Sep 30 / Dec 31 (or Aug 31, the "mid-year" bucket) is almost never a real
# readout date — it is a quarter bucket wearing a hard date's clothes. Trusting it as "the
# readout is Sep 30" is the same class of error as the dateline bug: a precise-looking value
# that is actually a period. Treat these as QUARTER precision, not DAY precision.
_QTR_ENDS = {(3, 31), (6, 30), (9, 30), (12, 31), (8, 31)}


def date_precision(d, text=""):
    """'day' | 'quarter' — is this parsed date a REAL day or a quarter/period bucket?

    A quarter-end date is 'quarter' precision UNLESS the surrounding text names a specific day
    ('on September 30', 'September 30 at 8:00am ET') — a readout really can land on a quarter
    end, but then the text says so specifically rather than 'in 3Q'.
    """
    if not d:
        return None
    if (d.month, d.day) not in _QTR_ENDS:
        return "day"
    t = (text or "").lower()
    # If the text NAMES a quarter/half/period, the quarter-end day is just that bucket's
    # rendering — trust the period. "3Q 2026 on or about September 30" is a quarter, and the
    # "on or about" is itself a tell that the day is soft. This dominates the specific-day check.
    if re.search(r"\b(q[1-4]|[1-4]q|[12]h|first half|second half|first|second|third|fourth"
                 r"|mid|early|late)\b[\s-]*(quarter|half|20\d\d)", t) or "or about" in t:
        return "quarter"
    # Otherwise a genuine specific day near a quarter end says the time-of-day, an ordinal, or
    # anchors to a dated conference/PDUFA.
    specific = re.search(r"\b" + str(d.day) + r"(st|nd|rd|th)?\b.{0,20}(20\d\d|am|pm|\bet\b)", t) or \
        re.search(r"\b(pdufa|conference|present\w*|easd|esmo|aacr|ash|asco|jpm)\b", t)
    return "day" if specific else "quarter"


def ua():
    u = os.environ.get("SEC_USER_AGENT", "").strip()
    if not u:
        sys.exit('SEC requires an identifying User-Agent.\n'
                 '  set SEC_USER_AGENT=Your Name you@example.com')
    return u


def _get(url, agent, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": agent,
                                                       "Accept-Encoding": "gzip, deflate"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                return raw
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(min(8, 2 ** i))
    return None


def fts(phrase, start, end, agent, frm=0):
    q = urllib.parse.urlencode({"q": f'"{phrase}"', "startdt": start, "enddt": end,
                                "forms": FORMS, "from": frm})
    raw = _get(f"{FTS}?{q}", agent)
    if not raw:
        return None
    try:
        return json.loads(raw.decode())
    except Exception:
        return None


def time_slices(days, step):
    """Newest-first. THE fix: a census of recent filings, not a relevance skim of 450 days."""
    end = dt.date.today()
    out = []
    i = 0
    while i < days:
        b = end - dt.timedelta(days=min(i + step, days))
        e = end - dt.timedelta(days=i)
        out.append((b.isoformat(), e.isoformat()))
        i += step
    return out


def walk(phrases, days, step, agent, label, verbose=True):
    """Take EVERYTHING in each slice. Paginate if a slice saturates."""
    hits, calls = {}, 0
    for ph in phrases:
        n = 0
        for (a, b) in time_slices(days, step):
            frm = 0
            while True:
                j = fts(ph, a, b, agent, frm)
                calls += 1
                time.sleep(0.11)                 # SEC: stay well under 10 req/s
                if not j:
                    break
                t = j.get("hits", {}).get("total", {})
                tot, rel = t.get("value", 0), t.get("relation", "eq")
                if frm == 0 and rel != "eq" and verbose:
                    print(f"    [warn] '{ph}' {a}..{b}: total is a FLOOR ({rel}) — "
                          f"slice smaller than {step}d to see it all", file=sys.stderr)
                page = j.get("hits", {}).get("hits", [])
                if not page:
                    break
                for h in page:
                    s = h.get("_source", {})
                    names = s.get("display_names") or []
                    tk = None
                    for nm in names:
                        m = re.search(r"\(([A-Z.]{1,6})\)", nm)
                        if m:
                            tk = m.group(1)
                            break
                    if not tk:
                        continue
                    _id = h.get("_id", ":")
                    accn, _, fname = _id.partition(":")
                    key = (tk, accn, fname)
                    if key in hits:
                        hits[key]["phrases"].add(ph)
                        continue
                    hits[key] = {
                        "ticker": tk, "kind": label, "phrases": {ph},
                        "company": (names[0].split("(")[0].strip() if names else ""),
                        "filed": s.get("file_date", ""),
                        "form": (s.get("root_forms") or [s.get("form", "")])[0],
                        "sics": s.get("sics") or [],
                        "cik": (s.get("ciks") or ["0"])[0],
                        "accn": accn, "doc": fname,
                    }
                    n += 1
                frm += len(page)
                if frm >= min(tot, 10000):
                    break
        if verbose:
            print(f"    {ph:<30} +{n:>4}")
    return hits, calls


# ---- RESULTS-NOW DETECTION (2026-07-18 — THE KLRS LESSON) --------------------------------------
# KLRS filed an 8-K on 7/17 whose investor deck said "preliminary data expected in 1H 2027". The
# scanner dutifully filed KLRS as an UPCOMING readout for 1H 2027 — and completely MISSED that the
# SAME filing was REPORTING fresh positive Phase 1a data that morning (9.2-letter BCVA gain, ~93%
# fluid resolution, generally well tolerated). The stock gapped $4.61 -> $6.25 (+35%) at the open
# and round-tripped to RED by the close. The gap WAS the trade — and we already had the document.
#
# The miss: a filing can BOTH report data now AND guide to a future milestone. We only looked for
# the future window. This detector runs on the doc we already fetched and asks the other question:
# "is THIS filing reporting clinical results right now?" A pure forward-guidance sentence ("we
# expect topline in 2H") never carries a p-value, a letter gain, or "met its primary endpoint".
# These do:
_RES_EFFICACY = re.compile(
    r"\b\d+(?:\.\d+)?[-\s]?letter\b"                          # "9.2-letter" BCVA gain
    r"|\bp\s*[=<]\s*0?\.\d+"                                  # a p-value
    r"|\b(?:ORR|response rate|reduction|resolution|improvement)\b[^.]{0,30}\b\d{1,3}\s?%"
    r"|\b\d{1,3}\s?%[^.]{0,30}\b(?:reduction|resolution|response|improvement|inhibition)\b"
    r"|\bmedian\b[^.]{0,25}\b(?:PFS|OS|survival|DoR)\b", re.I)
_RES_ENDPOINT = re.compile(
    r"\bmet\b[^.]{0,25}\bprimary\b"                           # met (its) primary endpoint
    r"|\bachieved\b[^.]{0,25}\b(?:primary|statistical significance|significance)\b"
    r"|\bstatistically\s+significant\b"
    r"|\bprimary\s+endpoint\b[^.]{0,20}\b(?:met|achieved|was\s+met)\b", re.I)
_RES_SAFETY = re.compile(
    r"\bno\s+dose[-\s]?limiting\b"
    r"|\bgenerally\s+well[-\s]?tolerated\b"
    r"|\bwell[-\s]?tolerated\b"
    r"|\bno\s+(?:treatment[-\s]?related\s+)?serious\s+adverse\b"
    r"|\bno\s+(?:new\s+)?safety\s+signals?\b", re.I)
_RES_VERB = re.compile(                                        # a headline that ANNOUNCES data NOW
    r"\b(?:reported|reports|announced|announces|presented|presents|showed|demonstrated)\b"
    r"[^.]{0,45}\b(?:positive\s+|topline\s+|top-line\s+|interim\s+|updated\s+|new\s+|final\s+)?"
    r"(?:results|data|findings|readout)\b", re.I)


def results_now(txt):
    """Is THIS filing reporting clinical data (not merely promising it later)? -> (bool, snippet).

    Fires when the announce-verb pattern hits, OR when >=2 of {efficacy, endpoint, safety} hit —
    enough specificity that a pure forward-guidance filing can't trip it. KLRS's deck had no
    'announces results' headline but hit efficacy (9.2-letter, ~93% resolution) AND safety (no
    dose-limiting, generally well tolerated) -> 2 categories -> caught."""
    hits = []
    mv = _RES_VERB.search(txt)
    if mv:
        hits.append(("verb", mv))
    # efficacy and endpoint require a SPECIFIC NUMBER or an explicit endpoint claim (p-value, ORR%,
    # letter gain, "met primary") — things forward guidance never states — so each fires ALONE.
    # safety ("well tolerated") is softer and can appear loosely, so it only counts when paired.
    me = _RES_EFFICACY.search(txt)
    mp = _RES_ENDPOINT.search(txt)
    ms = _RES_SAFETY.search(txt)
    if me:
        hits.append(("efficacy", me))
    if mp:
        hits.append(("endpoint", mp))
    if ms:
        hits.append(("safety", ms))
    hard = sum(x is not None for x in (mv, me, mp))          # strong signals
    fired = hard >= 1 or (ms is not None and len(hits) >= 2)
    if not fired:
        return False, ""
    m = hits[0][1]
    snip = re.sub(r"\s+", " ", txt[max(0, m.start() - 40):m.end() + 70]).strip()
    tag = "+".join(h[0] for h in hits)
    return True, f"[{tag}] {snip}"[:200]


def fetch_date(h, agent, filed=None):
    """STAGE 2 — regex the DOC for a FORWARD readout window. See THE DATELINE BUG above.

    Scores every candidate instead of taking the first; rejects the filing's own dateline and
    any date that precedes the filing. Also runs results_now() on the same fetched text so a
    filing that is ITSELF reporting data gets flagged (the KLRS lesson). Returns
    (window, context, just_reported, result_hit).
    """
    cik = str(int(h["cik"]))
    url = f"{ARCHIVES}/{cik}/{h['accn'].replace('-', '')}/{h['doc']}"
    raw = _get(url, agent)
    if not raw:
        return None, None, False, ""
    try:
        txt = raw.decode("utf-8", "replace")
    except Exception:
        return None, None, False, ""
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)

    # THE KLRS LESSON — is this filing reporting data NOW? Runs on the same fetched text, so it
    # costs nothing extra. A filing can report Phase 1 data AND guide to Phase 2; we want both.
    jr, rhit = results_now(txt)

    fd = None
    if filed:
        try:
            fd = dt.date(*map(int, str(filed).split("-")))
        except Exception:
            fd = None

    cands = []
    for m in NEAR.finditer(txt):
        w = txt[max(0, m.start() - 260):m.end() + 260]
        # RULE 3 — no forward verb, no guidance. "Reports Positive Results July 15, 2026" is a
        # PAST readout with a dateline next to it, which is exactly what fooled the old code.
        if not FWD_NEAR.search(w):
            continue
        # RULE 5 (2026-07-18) — FISCAL / OFFERING context. "results...for the year ending Dec 31"
        # is a financial statement, not a clinical readout; the whole point of broadening NEAR to
        # catch "results" is that this guard catches the financial ones it lets in. GLMD's
        # "December 31, 2026" and HELP's offering "Q4 2026" both die here.
        if FISCAL_RX.search(w):
            continue
        ctx = w[:220].strip()

        # A vague period IS the answer. Real guidance says "2H 2026", never "July 15, 2026".
        v = VAGUE_RX.search(w)
        if v:
            # RULE 2 FOR PERIODS (2026-07-18) — a period already CLOSED at the filing date is
            # not a forecast. "Q1 2026" in a July-2026 filing describes something that already
            # happened (or a fiscal quarter). Before this, the nearest-forward sort happily
            # picked those PAST quarters and they won (CMPX 'Q1 2026', LXEO 'Q2 2026'). Reject a
            # period whose END precedes the filing.
            if fd and _period_end(v.group(0)) and _period_end(v.group(0)) < fd:
                continue
            cands.append((3, v.group(0), ctx))
            continue
        for rx in DATE_PATTERNS[:2]:          # hard dates only
            d = rx.search(w)
            if not d:
                continue
            hd = _hard_date(d.group(0))
            if hd and fd:
                if abs((hd - fd).days) <= 3:  # RULE 1 — the dateline
                    continue
                if hd < fd:                   # RULE 2 — the past is not a forecast
                    continue
            # RULE 4 (2026-07-18) — a hard date on a quarter end, with no specific-day language
            # in context, is a QUARTER BUCKET, not a day. Demote it to the same rank as a vague
            # period and RELABEL it as the quarter, so downstream never shows "Sep 30" as if the
            # readout were pinned to that day. Rank 1 < a genuine hard day (2) < a vague period
            # match (3) — so a real specific day still wins if one exists in the same filing.
            if hd and date_precision(hd, w) == "quarter":
                q = (hd.month - 1) // 3 + 1
                cands.append((1, f"Q{q} {hd.year}", ctx))
                continue
            cands.append((2, d.group(0), ctx))
            break

    if not cands:
        return None, None, jr, rhit
    # SELECTION (2026-07-18) — prefer the NEAREST FORWARD window, not just the highest precision
    # rank. STTK's 8-K carries "Q3 2026" (the real Phase 1 readout) AND "first half of 2028" (a
    # different trial's milestone), both rank-3 vague periods; the old `-rank` sort could return
    # either. The soonest readout is the tradeable one, so sort by (nearest start date, then
    # precision). A window with no parseable start falls to the back.
    cands.sort(key=lambda c: (_sort_date(c[1]), -c[0]))
    return cands[0][1], cands[0][2], jr, rhit


_FAR = dt.date(2099, 1, 1)


def _sort_date(label):
    """The date to SORT a window by, so 'nearest forward' is meaningful across mixed precision.

    A hard date sorts as itself. A vague period sorts by its EXPECTED MIDPOINT, not its optimistic
    start — "2H 2026" realistically lands ~September, so a concrete "August 15, 2026" should beat
    it even though the half-year technically opens July 1. Without this, a broad early-half period
    always jumps ahead of a specific near date, which is backwards for a tradeable list.
    """
    hd = _hard_date(label)
    if hd:
        return hd
    ps = _period_start(label)
    if not ps:
        return _FAR
    s = (label or "").lower()
    # quarters span ~3 months (mid = +45d), halves/early/late/mid span ~6 (mid = +75d)
    span = 45 if re.search(r"\bq[1-4]\b|\b[1-4]q\b|quarter", s) else 75
    return ps + dt.timedelta(days=span)


def _period_end(s):
    """Last day a vague period could close. 'Q1 2026'->Mar 31, '2H 2026'->Dec 31, None if not a
    period. Used to reject periods that already CLOSED before the filing date (not a forecast)."""
    ps = _period_start(s)
    if not ps:
        return None
    t = (s or "").lower()
    if re.search(r"\bq[1-4]\b|\b[1-4]q\b|quarter", t):
        m = ps.month + 2                       # a quarter is 3 months
    elif re.search(r"\b[12]h\b|half|early|mid|late", t):
        m = ps.month + 5                       # a half is 6 months
    else:
        m = 12                                 # bare year -> Dec
    yr = ps.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    last = [31, 29 if yr % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(yr, m, last)


def _period_start(s):
    """Earliest day a vague period could open. 'Q3 2026'->Jul 1, '2H 2026'->Jul 1, None if not a
    period. Used only to sort candidates by nearest-forward; not shown to the user."""
    s = (s or "").lower()
    y = re.search(r"20(2\d|3\d)", s)
    if not y:
        return None
    yr = int(y.group(0))
    if re.search(r"\bq1\b|\b1q\b|first quarter", s): mo = 1
    elif re.search(r"\bq2\b|\b2q\b|second quarter", s): mo = 4
    elif re.search(r"\bq3\b|\b3q\b|third quarter", s): mo = 7
    elif re.search(r"\bq4\b|\b4q\b|fourth quarter", s): mo = 10
    elif re.search(r"\b1h\b|first half|early", s): mo = 1
    elif re.search(r"\b2h\b|second half|2nd half|late|latter", s): mo = 7
    elif re.search(r"\bmid\b|mid-", s): mo = 5
    else: mo = 1
    try:
        return dt.date(yr, mo, 1)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45, help="lookback (default 45)")
    ap.add_argument("--step", type=int, default=7, help="slice size in days (default 7)")
    ap.add_argument("--past", action="store_true", help="also walk PAST-tense phrases")
    ap.add_argument("--dates", action="store_true", help="fetch docs to extract the window (slow)")
    ap.add_argument("--max-fetch", type=int, default=60)
    ap.add_argument("--out", default="readout_forward.csv")
    a = ap.parse_args()
    agent = ua()

    t0 = time.time()
    print("=" * 92)
    print(f"  FORWARD READOUT SCAN — last {a.days}d in {a.step}d slices")
    print("=" * 92)
    print(f"  {len(FORWARD)} FORWARD phrases (a readout is COMING — this is the tradeable set)")
    print(f"  excluded on purpose: {EXCLUDED}  (45% of corpus, ~0 signal)\n")
    hits, calls = walk(FORWARD, a.days, a.step, agent, "FORWARD")

    if a.past:
        print(f"\n  {len(PAST)} PAST phrases (already printed — universe only, no trade)\n")
        ph, c2 = walk(PAST, a.days, a.step, agent, "PAST")
        calls += c2
        for k, v in ph.items():
            if k in hits:
                hits[k]["phrases"] |= v["phrases"]
            else:
                hits[k] = v

    bio = {k: v for k, v in hits.items() if any(s in BIO_SIC for s in v["sics"])}
    print(f"\n  {calls} FTS calls in {time.time()-t0:.0f}s")
    print(f"  {len(hits)} filings, {len({v['ticker'] for v in hits.values()})} tickers")
    print(f"  biotech SIC: {len(bio)} filings, {len({v['ticker'] for v in bio.values()})} tickers")

    if a.dates:
        print(f"\n  fetching up to {a.max_fetch} docs for the WINDOW (stage 2)...")
        fwd = [v for v in bio.values() if v["kind"] == "FORWARD"]
        fwd.sort(key=lambda v: v["filed"], reverse=True)
        for i, v in enumerate(fwd[:a.max_fetch]):
            d, ctx, jr, rhit = fetch_date(v, agent, filed=v.get("filed"))
            v["window"], v["context"] = d, (ctx or "")[:180]
            v["just_reported"], v["result_hit"] = ("YES" if jr else ""), (rhit or "")[:180]
            time.sleep(0.11)
            if (i + 1) % 10 == 0:
                print(f"    {i+1}/{min(len(fwd), a.max_fetch)}")

    # ---- DEDUP (2026-07-18) — one row per ticker, keeping the best window -------------------
    # The raw output had STTK 3x (three EXHIBITS of one 8-K: the body said "Q3 2026", a milestone
    # table said "1H 2028") and HELP 3x (three separate OFFERING press releases). A watchlist
    # wants one line per name with the most actionable guidance. Keep, per ticker:
    #   1. a row WITH a window over a blank one,
    #   2. the NEAREST-forward window (soonest readout = most tradeable),
    #   3. the NEWEST filing as the tiebreak (most current guidance).
    # We keep the count of how many filings backed it — repeated guidance is a small confidence
    # signal, and it lets you see "HELP: 3 filings, all offerings, no real window".
    def _win_start(v):
        return _sort_date(v.get("window") or "")

    best = {}
    counts = {}
    jr_any = {}                     # ticker -> result_hit from ANY of its filings (the KLRS flag)
    for v in bio.values():
        if v["kind"] != "FORWARD":
            continue
        tk = v["ticker"]
        counts[tk] = counts.get(tk, 0) + 1
        if v.get("just_reported") == "YES" and tk not in jr_any:
            jr_any[tk] = v.get("result_hit", "")
        cur = best.get(tk)
        has = 1 if (v.get("window") or "").strip() else 0
        if cur is None:
            best[tk] = v
            continue
        chas = 1 if (cur.get("window") or "").strip() else 0
        # prefer has-window; then nearest start; then newest filing
        if (has, chas) == (1, 0):
            best[tk] = v
        elif has == chas == 1 and (_win_start(v), ) < (_win_start(cur), ):
            best[tk] = v
        elif has == chas and v["filed"] > cur["filed"]:
            best[tk] = v
    for tk, v in best.items():
        v["n_filings"] = counts.get(tk, 1)
        if tk in jr_any and v.get("just_reported") != "YES":
            v["just_reported"], v["result_hit"] = "YES", jr_any[tk]
    # JUST REPORTED names float to the top — a filing reporting data TODAY is the morning gapper,
    # the single most actionable row. Then by filing date.
    rows = sorted(best.values(),
                  key=lambda v: (v.get("just_reported") == "YES", v["filed"]), reverse=True)
    out = os.path.join(HERE, a.out)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "kind", "just_reported", "result_hit", "filed", "form", "company",
                    "n_filings", "phrases", "window", "context", "cik", "accession", "document",
                    "url"])
        for v in rows:
            cik = str(int(v["cik"]))
            w.writerow([v["ticker"], v["kind"], v.get("just_reported", ""),
                        v.get("result_hit", ""), v["filed"], v["form"], v["company"],
                        v.get("n_filings", 1), " | ".join(sorted(v["phrases"])),
                        v.get("window", ""), v.get("context", ""), cik, v["accn"], v["doc"],
                        f"{ARCHIVES}/{cik}/{v['accn'].replace('-','')}/{v['doc']}"])

    jr_rows = [v for v in rows if v.get("just_reported") == "YES"]
    if jr_rows:
        print("\n" + "=" * 92)
        print("  🔥 JUST REPORTED — this filing is REPORTING DATA (the morning gapper). KLRS lesson.")
        print("=" * 92)
        print(f"  {'tkr':<7} {'filed':<11} {'form':<5} {'next window':<14} what it reported")
        for v in jr_rows[:20]:
            print(f"  {v['ticker']:<7} {v['filed']:<11} {v['form']:<5} "
                  f"{(v.get('window') or '-'):<14} {(v.get('result_hit') or '')[:44]}")
        print("  ^ The gap IS the trade. Data already out — verify the reaction, do not chase.")

    print("\n" + "=" * 92)
    print("  FORWARD GUIDANCE — a readout is COMING (this is the list that pays)")
    print("=" * 92)
    fw = [v for v in rows if v["kind"] == "FORWARD"]
    print(f"  {'tkr':<7} {'filed':<11} {'form':<5} {'window':<16} company")
    for v in fw[:30]:
        print(f"  {v['ticker']:<7} {v['filed']:<11} {v['form']:<5} "
              f"{(v.get('window') or '-'):<16} {v['company'][:36]}")
    if not fw:
        print("  (none in this window)")
    print(f"\n  {len(fw)} forward, {len(rows)-len(fw)} past-tense")
    print(f"  -> {out}")
    print("\n  NOT investment advice. A company saying 'we expect topline in 2H' is a PLAN.")
    print("  Verify against IR/SEC before acting. Readout dates slip constantly.")


if __name__ == "__main__":
    main()
