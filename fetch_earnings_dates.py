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
that ticker's exchange tag ("Nasdaq: VKTX") or its headline starts with the company's name, because FMP files some
releases under the wrong symbol (Merck KGaA, Darmstadt, under MRK).

Writes _earnings_dates.json:
  {"fetched": "...Z", "from": "2024-01-01",
   "tickers": {"VKTX": {"name": "...", "backfilled": "2026-11-27", "read": "2026-11-27",
                        "releases": [{"kind": "results"|"schedule", "published_et": "2026-10-28 16:05", "title",
                                      "url", "site", "period", "period_key", "report_date", "timing", "timing_words",
                                      "call_time"}]}}}

Only parsing happens offline; the network is used only with FMP_API_KEY set (CI). The parse rules are tested in
tests/test_earnings_dates_parse.py on real headlines.

    python fetch_earnings_dates.py [--days 21] [--full] [--tickers VKTX,ALNY]
Exit 0 always unless --strict and FMP could not be read at all (2).
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
# law-firm, shareholder-alert, postponement and meeting releases are never earnings rows
NOISE = re.compile(r"\b(investigat\w*|investor alert|shareholders?|stockholders?|class action|law firm|lawsuit|securities "
                   r"fraud|rosen|pomerantz|postpone\w*|delay\w*|annual (general )?meeting|special meeting|voting|vote)\b", re.I)
FUTURE = re.compile(r"\b(to|will|plans? to|set to|schedules?|scheduled)\s+(report|announce|release|host|present|"
                    r"hold|discuss|issue)\b|\b(conference call|webcast)\s+(to|will|on)\b|\b(date|dates|timing)\s+(for|of)\b"
                    r"|\bto (report|announce|release)\b|\bupcoming\b|\breschedul\w*\b", re.I)
NOT_RESULTS = re.compile(r"\b(trial|study|phase|topline|top-line|clinical|data|readout|interim|survey|inducement|"
                         r"preliminary|unaudited preliminary|pre-announce\w*|guidance only)\b", re.I)
SCHEDULE_HINT = re.compile(r"\b(financial results|quarter|earnings|full[\s-]+year|fiscal)\b", re.I)

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
    if NOISE.search(t):
        return False
    m = STRONG_RESULTS.search(t)
    if m and not _future_verb(t, m) and period_of(m.group(0))[0]:
        return True
    if not RESULTS_WORD.search(t) or not REPORTS.search(t):
        return False
    if FUTURE.search(t) or NOT_RESULTS.search(t):
        return False
    p, _ = period_of(t)
    return bool(p)


def is_schedule(title, text):
    t = clean(title)
    if NOISE.search(t) and not re.search(r"\breschedul", t, re.I):
        return False
    if not FUTURE.search(t) or not SCHEDULE_HINT.search(t):
        return False
    if NOT_RESULTS.search(t):
        return False
    # the headline must be about results/earnings, not an investor conference or a data presentation
    if not re.search(r"\b(results|earnings)\b", t, re.I) and not re.search(r"\b(results|earnings)\b", clean(text)[:400], re.I):
        return False
    return True


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WIRE = re.compile(r"\s*(?:/PRNewswire[^/]{0,20}/|\(\s*GLOBE NEWSWIRE\s*\)|-*\s*\(\s*BUSINESS WIRE\s*\)|/CNW/|\(?ACCESSWIRE\)?|"
                  r"/EINPresswire/|\(\s*Newsfile Corp\.?\s*\)|/?\(?\s*Globe Newswire\s*\)?)", re.I)


def find_date(text, published, strict_weekday=True):
    """The reporting day a schedule release announces, resolving a missing year to the next occurrence on or after the
    release day. Skips the newswire dateline (a date followed by /PRNewswire/, (GLOBE NEWSWIRE), (BUSINESS WIRE) ...),
    a period end ('quarter ended September 30, 2026') and the release day itself unless 'today' is printed next to it.
    Prefers a day printed after 'on' or a weekday. A printed weekday that does not match its date voids the release
    (returns False). None when no day is printed."""
    t = clean(text)
    cands = []
    for rx, table in ((DAY_FULL, MONTHS), (DAY_ABBR, MON_ABBR)):
        for m in rx.finditer(t):
            mon = table[m.group(1).lower().rstrip(".")]
            try:
                day = int(m.group(2))
                if m.group(3):
                    d = dt.date(int(m.group(3)), mon, day)
                else:
                    d = dt.date(published.year, mon, day)
                    if d < published - dt.timedelta(days=1):
                        d = dt.date(published.year + 1, mon, day)
            except ValueError:
                continue
            before, after = t[max(0, m.start() - 40):m.start()].lower(), t[m.end():m.end() + 30]
            if WIRE.match(after):
                continue                                   # the dateline
            if re.search(r"\b(ended|ending|end of|as of|through)\s*$", before):
                continue                                   # a period end
            if d == published and not re.search(r"\b(today|tonight|this (morning|afternoon|evening))\b",
                                                before + " " + after.lower()):
                continue
            wd = re.search(r"\b(" + "|".join(WEEKDAYS) + r")\s*,?\s*$", before)
            if wd and strict_weekday and WEEKDAYS.index(wd.group(1)) != d.weekday():
                return False
            score = 0 if (wd or re.search(r"\b(on|for)\s*$", before)) else 1
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
    n = re.sub(r",?\s+(Inc|Incorporated|Corp|Corporation|Ltd|Limited|plc|PLC|N\.V|NV|S\.A|SA|AG|SE|A/S|AB|ASA|LLC)\.?\s*$",
               "", clean(name))
    return n.strip(" ,.")


def mentions(tk, name, title, text):
    """True when the release is the ticker's own: the headline opens with the company's short name (word boundary),
    AND the release carries the ticker's exchange tag or the company's full name. Both, so 'Merck KGaA, Darmstadt'
    (no 'NYSE: MRK', no 'Merck & Co') is not Merck & Co.'s, and a law firm's or a peer's release that only quotes
    the tag in its body is not the ticker's either."""
    t = clean(title)
    stem = short_name(name)
    if not stem or not re.match(re.escape(stem) + r"(?![A-Za-z0-9])", t, re.I):
        return False
    body = t + " " + clean(text)
    tag = re.compile(r"(NASDAQ|Nasdaq|NYSE|NYSE American|OTCQX|OTCQB|OTC|TSX|ASX|LSE|AIM|Euronext)[A-Za-z :]{0,22}:\s*"
                     + re.escape(tk) + r"\b")
    if tag.search(body):
        return True
    ln = long_name(name)
    if len(ln) > len(stem) and ln.lower() in body.lower():
        return True
    # neither printed (FMP's excerpt is often cut before them): the headline's own name must end where the company's
    # does. 'Arcutis to Report' and 'Viking Therapeutics Reports' pass; 'Merck KGaA, Darmstadt ... Reports' does not.
    words = re.findall(r"[A-Za-z0-9&'.-]+|,", t)
    own = [w.lower().strip(".,") for w in re.findall(r"[A-Za-z0-9&'.-]+", ln)]
    i = 0
    while i < len(words) and i < len(own) and words[i].lower().strip(".") == own[i]:
        i += 1
    if i == 0:
        return False
    nxt = words[i] if i < len(words) else ""
    return bool(nxt) and (nxt[0].islower() or nxt.lower() in HEADLINE_VERBS)


HEADLINE_VERBS = {"to", "will", "reports", "report", "announces", "announce", "provides", "posts", "delivers", "sets",
                  "schedules", "reschedules", "highlights", "issues", "releases", "declares", "confirms", "plans", "and",
                  "q1", "q2", "q3", "q4", "first", "second", "third", "fourth", "full", "fiscal", "hosts", "host"}


def short_name(name):
    n = clean(name)
    n = re.sub(r"\s+&\s+Co\b.*$", "", n)                 # 'Merck & Co., Inc.' -> 'Merck'
    n = re.sub(r",?\s+(Inc|Incorporated|Corp|Corporation|Co|Company|Ltd|Limited|plc|PLC|N\.V|NV|S\.A|SA|AG|SE|A/S|AB|ASA|"
               r"Holdings?|Group|International|Therapeutics|Pharmaceuticals|Pharma|Biosciences|Bio|Biotherapeutics|"
               r"Biopharma|Biotech|Technologies|Medical|Sciences|Oncology|Ltd\.)\.?\b.*$", "", n)
    n = n.strip(" ,.")
    return n if len(n) >= 3 else clean(name)


def parse_item(tk, name, it):
    """One FMP press release -> a cache row, or None when it is neither a schedule nor a results release of `tk`."""
    title, text = clean(it.get("title")), clean(it.get("text"))
    pub_raw = str(it.get("publishedDate") or "")
    try:
        pub = dt.datetime.strptime(pub_raw[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if not mentions(tk, name, title, text):
        return None
    row = {"published_et": pub.strftime("%Y-%m-%d %H:%M"), "title": title, "url": it.get("url") or "",
           "site": it.get("site") or it.get("publisher") or ""}
    if is_results(title):
        p, k = period_of(title)
        row.update(kind="results", period=p, period_key=k)
        return row
    if is_schedule(title, text):
        p, k = period_of(title)
        if not p:
            p, k = period_of(text[:500])
        # the reporting day: the headline's own day first, else the first day in the release text after the headline
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


def universe():
    out = {}
    tdir = os.path.join(SITE, "ticker")
    for tk in sorted(os.listdir(tdir)):
        f = os.path.join(tdir, tk, "index.html")
        if not os.path.isfile(f):
            continue
        m = re.search(r"<title>(.*?)\s*\(" + re.escape(tk) + r"\)", io.open(f, encoding="utf-8").read(3000), re.S)
        out[tk] = clean(m.group(1)) if m else tk
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
    return items


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

    for tk, name in uni.items():
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
        ent["name"] = name
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
