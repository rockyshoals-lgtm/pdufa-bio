# -*- coding: utf-8 -*-
"""fetch_earnings_dates.py -- the quarterly-results dates of every company pdufa.bio tracks, from the companies'
own press releases as the newswires carried them (read through FMP's press-release feed).

David, 2026-11-26 21:07 UTC: "Concurrently continue our moat increase add earning dates ...".

Two kinds of release are kept, both written by the company itself:
  * SCHEDULE: "Viking Therapeutics to Report Financial Results for Third Quarter 2026 on October 28, 2026" -- the
    date the company says it will report, the period, and when in the day ("after the market close", "before the
    market opens") as the release words it.
  * RESULTS: "Viking Therapeutics Reports Third Quarter 2026 Financial Results ..." -- the day and the newswire
    timestamp (Eastern, CLAUDE.md RULE 1) at which the results went out.

Nothing is estimated. A vendor's projected next earnings date is NOT read: when a company has not announced its next
date, the cache simply has no SCHEDULE row for it. A release is attributed to a ticker only when its own text carries
that ticker's exchange tag ("Nasdaq: VKTX") or its headline starts with the company's name -- see mentions() for the
full rule -- because FMP files some releases under the wrong symbol (Merck KGaA, Darmstadt, under MRK).
A third kind, POSTPONED ("... Postpones Third Quarter 2026 Financial Results Release"), marks an announced day void.

Writes _earnings_dates.json:
  {"fetched": "...Z", "from": "2024-01-01",
   "tickers": {"VKTX": {"name": "...", "backfilled": "2026-11-27", "read": "2026-11-27",
                        "releases": [{"kind": "results"|"schedule", "published_et": "2026-10-28 16:05", "title",
                                      "url", "site", "period", "period_key", "report_date", "timing", "timing_words",
                                      "call_time"}]}}}

Only parsing happens offline; the network is used only with FMP_API_KEY set (CI). The parse rules are tested in
tests/test_earnings_dates_parse.py on real headlines.

    python fetch_earnings_dates.py [--days 21] [--full] [--tickers VKTX,ALNY]
Exit 0, or 3 (with a ::warning::, cache untouched) when no ticker could be read. No key: exit 0, nothing read.
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
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "_earnings_dates.json")
FMP_PR = "https://financialmodelingprep.com/stable/news/press-releases"
UA = {"User-Agent": "pdufa.bio-research-script/1.0"}
FROM = "2024-01-01"
# Bump when the parse rules change: every ticker is then re-read from FROM (90 a run), so no row parsed by older
# rules stays in the cache.
PARSER_VERSION = 2

MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}
MON_ABBR = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
            "oct": 10, "nov": 11, "dec": 12}
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}

# period as printed: "Third Quarter 2026", "Third-Quarter 2026", "Q3 2026", "3Q26", "Fourth Quarter and Full Year 2025",
# "Full Year 2025", "Fiscal 2027 First Quarter", "first half 2026" (semiannual filers)
P_QUARTER = re.compile(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)[\s-]+quarter\b(?:[\s,]+(?:and|&)[\s,]+"
                       r"(?:full|fiscal)[\s-]+year)?(?:\s+(?:of\s+)?(?:fiscal\s+(?:year\s+)?)?(20\d\d))?", re.I)
P_QN = re.compile(r"\b(?:Q([1-4])|([1-4])Q)[\s'-]*(?:FY)?\s*((?:20)?\d\d)\b", re.I)
P_FY = re.compile(r"\b(?:full[\s-]+year|fiscal[\s-]+(?:year[\s-]+)?(20\d\d)?\s*(?:full[\s-]+year)?|year[\s-]+end(?:ed)?)"
                  r"\s*(20\d\d)?\b", re.I)
P_FISCAL_Q = re.compile(r"\bfiscal\s+(?:year\s+)?(20\d\d)\s+(first|second|third|fourth)\s+quarter\b", re.I)
P_HALF = re.compile(r"\b(first|second)[\s-]+half(?:[\s-]+(?:of\s+)?(?:year\s+)?(20\d\d))?\b|\b(H[12])\s*(20\d\d)\b", re.I)

RESULTS_WORD = re.compile(r"\b(financial results|results|earnings)\b", re.I)
REPORTS = re.compile(r"\b(reports?|announces?|provides?|posts?|delivers?|highlights?)\b", re.I)
# "<Company> Reports Third Quarter 2026 Financial Results and Provides Clinical Update": the verb comes before the period
# and the results words, so the rest of the headline (clinical, data, upcoming ...) does not make it a non-results row
STRONG_RESULTS = re.compile(r"\b(reports?|announces?|posts?|delivers?)\s+(?:its\s+|the\s+)?(?:unaudited\s+)?"
                            r"(?:[\w'-]+\s+){0,6}?(?:quarter|full[\s-]+year|fiscal|half|Q[1-4]|[1-4]Q)\b[^.;:]{0,45}?"
                            r"\b(?:financial\s+)?(?:results|earnings)\b", re.I)
# "... Third Quarter 2026 Financial Results Conference Call", "... Earnings Release Date", "Announces Date of ...":
# a release ABOUT the results release, i.e. a schedule, even though it 'announces ... results'
ABOUT_RESULTS = re.compile(r"^\s*(conference call|call|webcast|release|date|announcement|timing)\b", re.I)
SCHEDULE_LEAD = re.compile(r"\b(date|dates|timing|upcoming|schedule[sd]?)\b", re.I)
# law-firm and shareholder-alert releases are never earnings rows (word forms chosen so 'Investigational' and
# 'Letter to Shareholders' do not match)
NOISE = re.compile(r"\b(investigation|investigations|investigating|investigates|investor alert|shareholder alert|"
                   r"class action|law firm|lawsuit|securities fraud|rosen law|pomerantz|levi & korsinsky|lost money|"
                   r"annual (general )?meeting|special meeting|voting results)\b", re.I)
POSTPONED = re.compile(r"\b(postpone\w*|delays?|delayed)\b", re.I)
FUTURE = re.compile(r"\b(to|will|plans? to|set to|schedules?|scheduled)\s+(report|announce|release|host|present|"
                    r"hold|discuss|issue)\b|\b(conference call|webcast)\s+(to|will|on)\b|\b(date|dates|timing)\s+(for|of)\b"
                    r"|\bto (report|announce|release)\b|\bupcoming\b|\breschedul\w*\b|\b(results|earnings)\s+(conference "
                    r"call|call|webcast|release date|release)\b|\brelease date\b", re.I)
NOT_RESULTS = re.compile(r"\b(trial|study|phase|topline|top-line|clinical|data|readout|interim|survey|inducement|"
                         r"preliminary|unaudited preliminary|pre-announce\w*|guidance only)\b", re.I)
SCHEDULE_HINT = re.compile(r"\b(financial results|results|quarter|earnings|full[\s-]+year|fiscal)\b", re.I)

# timing words as the release prints them
T_AFTER = re.compile(r"\b(after|following)\s+(the\s+)?((u\.?s\.?|us|nasdaq|nyse|stock|financial|global|nasdaq global "
                     r"(select\s+)?market)\s+)*(markets?|trading)?\s*(close[sd]?|closing)\b|\bafter[\s-]+(the\s+)?"
                     r"(market\s+)?(close|hours)\b|\bpost[\s-]market\b", re.I)
T_BEFORE = re.compile(r"\b(before|prior to|ahead of)\s+(the\s+)?((u\.?s\.?|us|nasdaq|nyse|stock|financial|global)\s+)*"
                      r"(markets?\s+|trading\s+)?(open[s]?|opening)\b|\bpre[\s-]?market\b|\bbefore\s+(the\s+)?(market|"
                      r"trading)\s+(day\s+)?(begins|starts)\b", re.I)
CALL = re.compile(r"\b(\d{1,2}(?::\d\d)?)\s*([ap])\.?\s*m\.?\s*(\(?\s*(?:E[SD]?T|Eastern(?: Time)?|ET)\b\)?)", re.I)

DAY_FULL = re.compile(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+"
                      r"(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b", re.I)
DAY_ABBR = re.compile(r"\b(jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+"
                      r"(20\d\d))?\b", re.I)


def clean(s):
    s = html.unescape(str(s or ""))
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def period_of(text):
    """(printed period, period key) from a headline/sentence. Key like '2026Q3', '2025FY', '2026H1'; None if unknown."""
    t = clean(text)
    m = P_FISCAL_Q.search(t)
    if m:
        return m.group(0), f"FY{m.group(1)}Q{ORD[m.group(2).lower()]}"
    m = P_QUARTER.search(t)
    if m:
        q = ORD[m.group(1).lower()]
        yr = m.group(2)
        full = bool(re.search(r"(full|fiscal)[\s-]+year", m.group(0), re.I))
        if yr:
            return m.group(0), f"{yr}Q{q}" + ("+FY" if full else "")
        # year printed after "full year" ("Fourth Quarter and Full Year 2025" is caught above); else look nearby
        y2 = re.search(r"\b(20\d\d)\b", t[m.end():m.end() + 25])
        if y2:
            return m.group(0) + " " + y2.group(1), f"{y2.group(1)}Q{q}" + ("+FY" if full else "")
        return m.group(0), None
    m = P_QN.search(t)
    if m:
        q = m.group(1) or m.group(2)
        y = m.group(3)
        y = y if len(y) == 4 else "20" + y
        return m.group(0), f"{y}Q{q}"
    m = P_HALF.search(t)
    if m:
        if m.group(3):
            return m.group(0), f"{m.group(4)}{m.group(3).upper()}"
        h = "H1" if m.group(1).lower() == "first" else "H2"
        return m.group(0), (f"{m.group(2)}{h}" if m.group(2) else None)
    m = re.search(r"\b(full[\s-]+year|fiscal(?:\s+year)?)\s+(20\d\d)\b|\b(20\d\d)\s+(full[\s-]+year|annual)\b", t, re.I)
    if m:
        return m.group(0), f"{m.group(2) or m.group(3)}FY"
    return None, None


def _future_verb(t, m):
    """True when the matched verb is itself future ('to Report', 'will report', 'plans to announce')."""
    return bool(re.search(r"\b(to|will|plans? to|set to|expects? to|intends? to)\s*$", t[:m.start()], re.I))


def is_results(title):
    """A headline that says the company reports its periodic results (not a schedule, not trial results)."""
    t = clean(title)
    if NOISE.search(t) or POSTPONED.search(t):
        return False
    m = STRONG_RESULTS.search(t)
    if m and not _future_verb(t, m) and period_of(m.group(0))[0]:
        if ABOUT_RESULTS.match(t[m.end():]) or SCHEDULE_LEAD.search(m.group(0)):
            return False            # 'Announces Third Quarter 2026 Financial Results Conference Call'
        return True
    if not RESULTS_WORD.search(t) or not REPORTS.search(t):
        return False
    if FUTURE.search(t) or NOT_RESULTS.search(t):
        return False
    p, _ = period_of(t)
    return bool(p)


def is_schedule(title, text):
    t = clean(title)
    if NOISE.search(t) or POSTPONED.search(t):
        return False
    if not FUTURE.search(t) or not SCHEDULE_HINT.search(t):
        return False
    if NOT_RESULTS.search(t):
        return False
    # the headline must be about results/earnings, not an investor conference or a data presentation
    if not re.search(r"\b(results|earnings)\b", t, re.I) and not re.search(r"\b(results|earnings)\b", clean(text)[:400], re.I):
        return False
    return True


def is_postponed(title):
    """'Viking Therapeutics Postpones Third Quarter 2026 Financial Results Release': the earlier announced day no longer
    holds. Kept as its own row so a page never shows the old day as current."""
    t = clean(title)
    return bool(POSTPONED.search(t) and re.search(r"\b(results|earnings)\b", t, re.I) and not NOISE.search(t)
                and not NOT_RESULTS.search(t))


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WIRE = re.compile(r"\s*(?:/PRNewswire[^/]{0,20}/|\(\s*GLOBE NEWSWIRE\s*\)|-*\s*\(\s*BUSINESS WIRE\s*\)|/CNW/|\(?ACCESSWIRE\)?|"
                  r"/EINPresswire/|\(\s*Newsfile Corp\.?\s*\)|/?\(?\s*Globe Newswire\s*\)?)", re.I)
CALL_WORD = re.compile(r"\b(conference call|call|webcast|teleconference|fireside)\b", re.I)
REL_WORD = re.compile(r"\b(report|reports|release|released|releases|announce|announced|results|earnings)\b", re.I)


def find_date(text, published):
    """The reporting day a schedule release announces, resolving a missing year to the next occurrence on or after the
    release day. Skips: the newswire dateline (a date followed by /PRNewswire/, (GLOBE NEWSWIRE), (BUSINESS WIRE) ...);
    a period end ('quarter ended September 30, 2026'); the release day itself unless 'today' is printed next to it; a
    conference-call or webcast day (a call word nearer before it than any report/release word); a day whose printed
    weekday does not match it. Prefers a day printed after 'on'/'for' or a weekday. None when no day qualifies."""
    t = clean(text)
    cands = []
    for rx, table in ((DAY_FULL, MONTHS), (DAY_ABBR, MON_ABBR)):
        for m in rx.finditer(t):
            mon = table[m.group(1).lower().rstrip(".")]
            rolled = False
            try:
                day = int(m.group(2))
                if m.group(3):
                    d = dt.date(int(m.group(3)), mon, day)
                else:
                    d = dt.date(published.year, mon, day)
                    if d < published - dt.timedelta(days=1):
                        d = dt.date(published.year + 1, mon, day)
                        rolled = True
            except ValueError:
                continue
            before, after = t[max(0, m.start() - 60):m.start()], t[m.end():m.end() + 30]
            bl = before.lower()
            if WIRE.match(after):
                continue                                   # the dateline
            if re.search(r"\b(ended|ending|end of|as of|through)\s*$", bl):
                continue                                   # a period end
            if d == published and not re.search(r"\b(today|tonight|this (morning|afternoon|evening))\b",
                                                bl + " " + after.lower()):
                continue
            calls = [c.end() for c in CALL_WORD.finditer(before)]
            rels = [r.end() for r in REL_WORD.finditer(before)]
            if calls and (not rels or max(calls) > max(rels)):
                continue                                   # the call's day, not the report day
            wd = re.search(r"\b(" + "|".join(WEEKDAYS) + r")\s*,?\s*$", bl)
            if wd and not rolled and WEEKDAYS.index(wd.group(1)) != d.weekday():
                continue                                   # weekday and date disagree: not trusted
            if wd and rolled:
                continue                                   # a past day with a weekday ('reported on Wednesday, Oct 28')
            score = 0 if (wd or re.search(r"\b(on|for)\s*$", bl)) else 1
            cands.append((score, m.start(), d))
    if not cands:
        return None
    return min(cands)[2]


def timing_of(text):
    t = clean(text)
    a, b = T_AFTER.search(t), T_BEFORE.search(t)
    if a and (not b or a.start() < b.start()):
        return "after_close", a.group(0)
    if b:
        return "before_open", b.group(0)
    return None, None


def call_time(text):
    """The call or webcast time: the first ET time printed within 120 characters after 'call' or 'webcast'."""
    t = clean(text)
    m = None
    for c in re.finditer(r"\b(conference call|call|webcast)\b", t, re.I):
        m = CALL.search(t[c.end():c.end() + 120])
        if m:
            break
    if not m:
        return None
    return f"{m.group(1)} {m.group(2).lower()}.m. ET"


def long_name(name):
    """The company name without its legal suffix: 'Merck & Co., Inc.' -> 'Merck & Co'."""
    n = re.sub(r",?\s+(Inc|Incorporated|Corp|Corporation|Ltd|Limited|plc|N\.V|NV|S\.A|SA|AG|SE|A/S|AB|ASA|LLC)\.?\s*$",
               "", clean(name), flags=re.I)
    return n.strip(" ,.")


# Headline brand names companies use for themselves that differ from the legal name (each seen on the company's own
# results headlines). Used only as extra headline stems; the other attribution checks still apply.
HEADLINE_NAMES = {
    "LLY": ["Lilly"], "BMY": ["Bristol Myers Squibb"], "TEVA": ["Teva"], "GSK": ["GSK"], "SNY": ["Sanofi"],
    "NVS": ["Novartis"], "AZN": ["AstraZeneca"], "NVO": ["Novo Nordisk"], "JNJ": ["Johnson & Johnson"],
}
# A short name another company also uses on the wires. Merck KGaA, Darmstadt, Germany headlines itself 'Merck' and
# FMP files its releases under MRK (tests/test_earnings_dates_parse.py fixture n1). Such a stem never attributes a
# release on the headline alone.
HOMONYM_STEMS = {"MERCK"}
TAG = re.compile(r"\b(?:NASDAQ|NYSE(?:\s+American)?|OTCQX|OTCQB|OTC|TSX|ASX|LSE|AIM|Euronext)[A-Za-z :]{0,22}:\s*([A-Z][A-Z0-9.]{0,6})\b",
                 re.I)
_SEC_FIRST = None


def _sec_stem_count(stem):
    """How many SEC registrants (distinct CIKs) have a name starting with `stem` as whole words."""
    global _SEC_FIRST
    if _SEC_FIRST is None:
        _SEC_FIRST = {}
        try:
            d = json.load(io.open(os.path.join(HERE, "sec_company_tickers.json"), encoding="utf-8"))
            for r in (d.values() if isinstance(d, dict) else d):
                words = re.sub(r"[^A-Z0-9& ]+", " ", str(r.get("title", "")).upper()).split()
                for i in range(1, min(4, len(words)) + 1):
                    _SEC_FIRST.setdefault(" ".join(words[:i]), set()).add(r.get("cik_str"))
        except Exception:  # noqa: BLE001
            pass
    key = " ".join(re.sub(r"[^A-Z0-9& ]+", " ", stem.upper()).split())
    return len(_SEC_FIRST.get(key, ()))


def _norm_words(s):
    return re.sub(r"[-‐‑]", " ", s).lower()


def mentions(tk, name, title, text):
    """True when the release is the ticker's own.
    1. The headline must open with one of the company's names (short name, full name or a listed headline brand),
       on a word boundary.
    2. Then: the ticker's own exchange tag in the release, or the company's full name in it, settles it.
    3. A release that carries exchange tags, none of them the ticker's, is someone else's ('Vertex, Inc. (NASDAQ: VERX)').
    4. Otherwise (FMP's excerpt often stops before the tag) the headline alone may attribute it only when the name is
       not shared: not a listed homonym, not the start of another SEC registrant's name, and the headline's name ends
       where the company's does ('Arcutis to Report' yes; 'Merck KGaA ... Reports' no)."""
    t = clean(title)
    tn = _norm_words(t)
    stems = [s for s in [short_name(name), long_name(name)] + HEADLINE_NAMES.get(tk, []) if s]
    hit = None
    for s in sorted(set(stems), key=len, reverse=True):
        if re.match(re.escape(_norm_words(s)) + r"(?![a-z0-9])", tn):
            hit = s
            break
    if not hit:
        return False
    body = t + " " + clean(text)
    tags = {m.group(1).upper().rstrip(".") for m in TAG.finditer(body)}
    if tk.upper() in tags:
        return True
    ln = long_name(name)
    if len(ln) > len(short_name(name)) and _norm_words(ln) in _norm_words(body):
        return True
    if tags:
        return False
    if hit.upper() in HOMONYM_STEMS or short_name(name).upper() in HOMONYM_STEMS:
        return False
    if _sec_stem_count(hit) > 1:
        return False
    words = re.findall(r"[A-Za-z0-9&'.]+|,", _norm_words(t))
    own = [w.strip(".,") for w in re.findall(r"[A-Za-z0-9&'.]+", _norm_words(ln))]
    i = 0
    while i < len(words) and i < len(own) and words[i].strip(".") == own[i]:
        i += 1
    if i == 0:
        i = len(re.findall(r"[A-Za-z0-9&'.]+", _norm_words(hit)))
    nxt = words[i] if i < len(words) else ""
    return bool(nxt) and (nxt in HEADLINE_VERBS)


HEADLINE_VERBS = {"to", "will", "reports", "report", "announces", "announce", "provides", "posts", "delivers", "sets",
                  "schedules", "reschedules", "highlights", "issues", "releases", "declares", "confirms", "plans", "and",
                  "q1", "q2", "q3", "q4", "first", "second", "third", "fourth", "full", "fiscal", "hosts", "host",
                  "postpones", "delays"}


def short_name(name):
    n = clean(name)
    n = re.sub(r"\s+&\s+Co\b.*$", "", n)                 # 'Merck & Co., Inc.' -> 'Merck'
    n = re.sub(r",?\s+(Inc|Incorporated|Corp|Corporation|Co|Company|Ltd|Limited|plc|N\.V|NV|S\.A|SA|AG|SE|A/S|AB|ASA|"
               r"Holdings?|Group|International|Therapeutics|Pharmaceuticals?|Pharma|Biosciences|Bio|Biotherapeutics|"
               r"Biopharma|Biotech|Technologies|Medical|Sciences|Oncology|Industries|Genetics|LLC)\.?(?![A-Za-z]).*$",
               "", n, flags=re.I)
    n = re.sub(r"\s+(and|&)$", "", n.strip(" ,."), flags=re.I)
    return n if len(n) >= 2 else clean(name)


def parse_item(tk, name, it):
    """One FMP press release -> a cache row, or None when it is neither a schedule, a postponement nor a results
    release of `tk`."""
    title, text = clean(it.get("title")), clean(it.get("text"))
    pub_raw = str(it.get("publishedDate") or "")
    try:
        pub = dt.datetime.strptime(pub_raw[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if not mentions(tk, name, title, text):
        return None
    row = {"published_et": pub.strftime("%Y-%m-%d %H:%M"), "title": title, "url": it.get("url") or "",
           "site": it.get("site") or it.get("publisher") or "", "stem": short_name(name)}

    def period():
        p, k = period_of(title)
        if not k:
            p2, k2 = period_of(text[:500])
            if k2:
                return p2, k2
        return p, k

    if is_results(title):
        p, k = period()
        row.update(kind="results", period=p, period_key=k)
        return row
    if is_postponed(title):
        p, k = period()
        row.update(kind="postponed", period=p, period_key=k)
        return row
    if is_schedule(title, text):
        p, k = period()
        # the reporting day: the headline's own day first, else the release text
        d = find_date(title, pub.date())
        if d is None:
            d = find_date(text, pub.date())
        if not d or d < pub.date() or (d - pub.date()).days > 75:
            return None
        tm, words = timing_of(text) if timing_of(text)[0] else timing_of(title)
        row.update(kind="schedule", period=p, period_key=k, report_date=d.isoformat(), timing=tm, timing_words=words,
                   call_time=call_time(text))
        return row
    return None


def sec_names():
    """ticker -> SEC registrant name (fallback when a ticker page title is unreadable)."""
    try:
        d = json.load(io.open(os.path.join(HERE, "sec_company_tickers.json"), encoding="utf-8"))
        return {str(r.get("ticker", "")).upper(): str(r.get("title", "")) for r in (d.values() if isinstance(d, dict) else d)}
    except Exception:  # noqa: BLE001
        return {}


def universe():
    out, sec = {}, None
    tdir = os.path.join(SITE, "ticker")
    for tk in sorted(os.listdir(tdir)):
        f = os.path.join(tdir, tk, "index.html")
        if not os.path.isfile(f):
            continue
        m = re.search(r"<title>([^<]*?)\s*\(" + re.escape(tk) + r"\)", io.open(f, encoding="utf-8").read(4000))
        nm = clean(m.group(1)) if m else ""
        if not nm or tk in nm.split() or len(nm) > 80:
            sec = sec if sec is not None else sec_names()
            nm = sec.get(tk, tk)
        out[tk] = nm
    return out


def fetch(tk, frm, to, key):
    """Every release for `tk` from `frm`, newest first, paged until a page is empty or reaches `frm`.
    Returns None on ANY failure (so a partial pull never marks a ticker backfilled). HTTP 4xx other than 429 is not
    retried (a plan or key error will not fix itself in seconds)."""
    items, page = [], 0
    while page < 40:
        q = urllib.parse.urlencode({"symbols": tk, "from": frm, "to": to, "limit": 100, "page": page, "apikey": key})
        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"{FMP_PR}?{q}", headers=UA), timeout=25) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                break
            except urllib.error.HTTPError as e:
                if (400 <= e.code < 500 and e.code != 429) or attempt == 2:
                    print(f"  {tk}: FMP HTTP {e.code}")
                    return None
                time.sleep(2 + attempt * 3)
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    print(f"  {tk}: FMP unreachable ({type(e).__name__})")
                    return None
                time.sleep(2 + attempt * 3)
        if not isinstance(data, list):
            print(f"  {tk}: FMP returned no list: {str(data)[:120]}")
            return None
        if not data:
            break
        items += data
        oldest = min(str(x.get("publishedDate") or "9999")[:10] for x in data)
        if oldest <= frm:
            break
        page += 1
    else:
        print(f"  {tk}: more than 40 pages; not marked read")
        return None
    return items


def profile_name(tk, key):
    """The company name from FMP's profile, for the few tickers whose page title carries no name."""
    q = urllib.parse.urlencode({"symbol": tk, "apikey": key})
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"https://financialmodelingprep.com/stable/profile?{q}", headers=UA), timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(d, list) and d and d[0].get("companyName"):
            return clean(d[0]["companyName"])
    except Exception:  # noqa: BLE001
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--full", action="store_true", help="re-read every ticker from FROM")
    ap.add_argument("--tickers", default="")
    ap.add_argument("--max-backfill", type=int, default=90, help="tickers backfilled from FROM per run; the rest next run")
    ap.add_argument("--budget-min", type=float, default=9.0, help="stop reading after this many minutes (the step's"
                    " timeout is 12); everything read so far is saved")
    a = ap.parse_args()
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        print("FMP_API_KEY not set; earnings cache not refreshed")
        return 0
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    cache.setdefault("from", FROM)
    tks = cache.setdefault("tickers", {})
    if cache.get("parser_version") != PARSER_VERSION:
        for ent in tks.values():
            ent.pop("backfilled", None)          # re-read and re-parse everything under the new rules
        cache["parser_version"] = PARSER_VERSION
    uni = universe()
    tracked = set(uni)
    if a.tickers:
        uni = {t: uni.get(t, t) for t in a.tickers.split(",")}
    today = dt.datetime.utcnow().date()
    to = (today + dt.timedelta(days=1)).isoformat()
    read = failed = new = streak = backfills = 0
    t0 = time.time()

    def save():
        tmp = CACHE + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
        os.replace(tmp, CACHE)

    # least recently read first, so a run that hits its time budget never starves the same tickers every day
    order = sorted(uni.items(), key=lambda kv: ((tks.get(kv[0]) or {}).get("read") or "", kv[0]))
    for tk, name in order:
        if time.time() - t0 > a.budget_min * 60:
            print(f"earnings: time budget reached after {read} tickers; the rest are read next run")
            break
        if streak >= 5:
            print("::warning::earnings: 5 tickers in a row unreadable; stopping (FMP down or key refused)")
            break
        full = a.full or not (tks.get(tk) or {}).get("backfilled")
        if full and backfills >= a.max_backfill:
            continue
        ent = tks.setdefault(tk, {"releases": []})
        if name == tk:                     # no name on the ticker page or in the SEC file
            name = ent.get("name") if ent.get("name") and ent.get("name") != tk else (profile_name(tk, key) or tk)
        ent["name"] = name
        if name == tk:
            ent["read"] = today.isoformat()
            ent["skipped"] = "no company name to match headlines against"
            continue
        backfills += full
        frm = FROM if full else (today - dt.timedelta(days=a.days)).isoformat()
        items = fetch(tk, frm, to, key)
        if items is None:
            failed += 1
            streak += 1
            continue
        read += 1
        streak = 0
        rows = [r for r in (parse_item(tk, name, it) for it in items) if r]
        if full:
            ent["releases"] = []       # a full read replaces the ticker's rows, so a fixed parser clears old misreads
        have = {r["url"] for r in ent["releases"]}
        for r in rows:
            if r["url"] and r["url"] not in have:
                ent["releases"].append(r)
                have.add(r["url"])
                new += 1
        ent["releases"].sort(key=lambda r: r["published_et"])
        ent["read"] = today.isoformat()
        if full:
            ent["backfilled"] = today.isoformat()
        if read % 40 == 0:
            save()            # a timeout keeps what was read
        time.sleep(0.15)
    # tickers that left the universe are kept (their history stays true) but marked
    if read == 0:
        print(f"::warning::earnings: no ticker readable ({failed} failed); cache NOT rewritten")
        return 3
    for tk in tks:
        tks[tk]["tracked"] = tk in tracked
    cache["fetched"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    save()
    nres = sum(1 for t in tks.values() for r in t["releases"] if r["kind"] == "results")
    nsch = sum(1 for t in tks.values() for r in t["releases"] if r["kind"] == "schedule")
    print(f"earnings: read {read} tickers, {failed} unreadable, {new} new releases; cache holds {nres} results and "
          f"{nsch} schedule releases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
