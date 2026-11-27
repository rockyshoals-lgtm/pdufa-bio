# -*- coding: utf-8 -*-
"""fetch_earnings_sec.py -- results dates the newswire feed missed, from the company's own Form 8-K under Item 2.02
(Results of Operations and Financial Condition), as filed on the SEC's EDGAR system.

David, 2026-11-26 21:07 UTC: "Concurrently continue our moat increase add earning dates ...". 2026-11-27: fill the
report days that passed with no results release read (the newswire feed carried none) from primary sources.

A US-listed company that publishes its quarterly results furnishes the release to the SEC on Form 8-K, Item 2.02,
usually within minutes. For every tracked ticker this reads the company's EDGAR filing list (data.sec.gov
submissions) and keeps the 8-Ks whose item list includes 2.02. A filing is opened only when the newswire cache
(_earnings_dates.json) has no results release for that ticker within a day of it, so the work stays on the gaps:
  * the 8-K body's Item 2.02 paragraph names the period ("announcing its financial results for the quarter ended
    September 30, 2026"), read with fetch_earnings_dates.period_of; when it does not, the first lines of the
    EX-99.1 release are read the same way
  * a filing whose Item 2.02 text calls the figures preliminary (a January conference update) is kept as
    "preliminary" and never shown as the period's results
  * a filing whose Item 2.02 text names no period, or no results, is kept with that status and never shown

Times: EDGAR's acceptance time, US Eastern as EDGAR prints it (CLAUDE.md RULE 1). It is when the SEC accepted the
filing, which can be minutes or hours after the release went out; the pages say so. A self-check compares 8-K times
with newswire times where both exist and stores the median difference; build_earnings_pages.py ignores every 8-K row
if that median is implausible (a time-zone error would show as a shift of hours).

Foreign private issuers (6-K filers) have no Item 2.02; they stay as the newswire feed leaves them.

Writes _earnings_sec.json:
  {"fetched": "...Z", "check": {"n": 120, "median_min": 6.0},
   "tickers": {"BIIB": {"cik": 875045, "filings": {"0000875045-26-000094": {"accepted_et": "2026-10-28 06:07",
      "filing_date": "2026-10-28", "form": "8-K", "items": "2.02,9.01", "url": ".../...-index.htm",
      "status": "results"|"preliminary"|"no_period"|"not_results"|"covered", "period": "...", "period_key": "2026Q3",
      "where": "8-K"|"EX-99.1"}}}}}

Network only in CI (sec.gov is unreachable from the build sandbox); the parse rules are tested offline in
tests/test_earnings_sec.py.

    python fetch_earnings_sec.py [--tickers BIIB,ABCL] [--budget-min 8] [--max-docs 400]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch_earnings_dates import period_of  # noqa: E402

CACHE = os.path.join(HERE, "_earnings_sec.json")
NEWSWIRE = os.path.join(HERE, "_earnings_dates.json")
TICKERS = os.path.join(HERE, "sec_company_tickers.json")
UA = {"User-Agent": "pdufa.bio builder support@pdufa.bio", "Accept-Encoding": "identity"}
FROM = "2024-01-01"
PAUSE = 0.15                       # SEC asks for no more than 10 requests a second
RULES_VERSION = 1                  # bump when the parse rules change: every opened filing is re-read
ACC = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def accepted_et(s):
    """EDGAR's acceptanceDateTime ('2026-10-28T06:07:33.000Z') -> '2026-10-28 06:07'. EDGAR prints the Eastern clock
    time with a 'Z' it does not mean (the filing index page shows the same 06:07:33 as 'Accepted'); the self-check in
    main() and the guard in build_earnings_pages.py catch it if that ever changes."""
    m = re.match(r"(20\d\d-\d\d-\d\d)T(\d\d):(\d\d)", str(s or ""))
    return f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m else ""


def text_of(raw):
    """HTML (or the submission's plain text) -> one line of readable text."""
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t).strip()


P_ITEM = re.compile(r"\bItem\s*2\.02\.?\s*(?:[-:.]\s*)?Results\s+of\s+Operations\s+and\s+Financial\s+Condition\.?",
                    re.I)
P_NEXT = re.compile(r"\bItem\s*(?:[1-8]\.\d\d|9\.01)\b", re.I)
P_PRELIM = re.compile(r"\bpreliminary\b|\bestimated\s+(?:unaudited\s+)?(?:revenue|cash|net\s+product)|"
                      r"\bexpects?\s+to\s+report\b|\banticipates?\s+reporting\b", re.I)
P_RESULTS = re.compile(r"\b(?:financial|operating|quarterly|annual|fiscal|earnings)\s+results\b|"
                       r"\bresults\s+of\s+operations\s+for\b|\breport(?:ed|ing)?\s+(?:its\s+)?(?:financial\s+)?results\b|"
                       r"\bfinancial\s+condition\s+(?:as\s+of|for)\b", re.I)


def item_202(body):
    """The Item 2.02 paragraph of an 8-K body (text), or '' when the body has no Item 2.02 heading. The body's
    first Item 2.02 heading with words after it (a table of contents can print the heading twice)."""
    best = ""
    for m in P_ITEM.finditer(body):
        rest = body[m.end():m.end() + 4000]
        n = P_NEXT.search(rest)
        seg = rest[:n.start()] if n else rest[:1500]
        if len(seg.strip()) > len(best.strip()):
            best = seg
        if len(best.strip()) > 80:
            break
    return best.strip()


MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
P_Q_ENDED = re.compile(r"\b(?:(first|second|third|fourth)\s+(fiscal\s+)?)?quarter\s+(?:(and\s+(?:the\s+)?(full\s+|fiscal\s+)?"
                       r"year)\s+)?ended\s+(january|february|march|april|may|june|july|august|september|october|"
                       r"november|december)\s+(\d{1,2}),?\s+(20\d\d)\b", re.I)


def period_202(s, pub):
    """(printed period, key) from an 8-K's Item 2.02 sentence. 8-Ks usually name the quarter by its last day ('the
    third quarter ended September 30, 2026', 'the quarter and year ended December 31, 2025'), which the newswire
    headline parser does not read. A day that does not end a calendar quarter, or an ordinal that does not match the
    calendar quarter (a fiscal year), gives no key: the period is the company's own and its year is not printed."""
    m = P_Q_ENDED.search(s)
    if m:
        o, fisc, yr_and, yr_kind, mon, day, y = m.groups()
        mon, day = MONTHS[mon.lower()], int(day)
        if (pub and int(y) > pub.year) or (mon, day) not in ((3, 31), (6, 30), (9, 30), (12, 31)):
            return m.group(0), None
        q = mon // 3
        if (o and ORD[o.lower()] != q) or fisc or (yr_kind or "").strip().lower() == "fiscal":
            return m.group(0), None
        return m.group(0), f"{y}Q{q}" + ("+FY" if q == 4 and yr_and else "")
    return period_of(s, pub)


def classify(seg, accepted):
    """(status, printed period, period key) for an Item 2.02 paragraph."""
    if not seg:
        return "no_item", None, None
    pub = dt.date.fromisoformat(accepted[:10]) if accepted else None
    sent = re.split(r"(?<=[a-z0-9\)])\.\s+(?=[A-Z])", seg)
    lead = " ".join(sent[:3])
    if P_PRELIM.search(lead):
        p, k = period_202(lead, pub)
        return "preliminary", p, k
    if not P_RESULTS.search(seg):
        return "not_results", None, None
    for s in sent[:4]:
        if P_RESULTS.search(s) or re.search(r"\bquarter|months\s+ended|year\s+ended", s, re.I):
            p, k = period_202(s, pub)
            if k:
                return "results", p, k
    return "no_period", None, None


def get(url, as_json=False, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                b = r.read()
            time.sleep(PAUSE)
            return json.loads(b.decode("utf-8", "replace")) if as_json else b.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503) or i == tries - 1:
                raise
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
        time.sleep(2 + 3 * i)
    return None


def newswire():
    """ticker -> [(published day, period key)] of newswire results releases, and ticker -> name."""
    try:
        c = json.load(io.open(NEWSWIRE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}, {}
    res, names = {}, {}
    for tk, v in (c.get("tickers") or {}).items():
        if not isinstance(v, dict):
            continue
        names[tk] = v.get("name") or tk
        res[tk] = [(str(r.get("published_et") or ""), r.get("period_key") or "")
                   for r in (v.get("releases") or []) if isinstance(r, dict) and r.get("kind") == "results"]
    return res, names


def covered(day, wire):
    """A newswire results release went out within a day of this 8-K: the gap is not here."""
    try:
        d = dt.date.fromisoformat(day[:10])
    except ValueError:
        return False
    for pub, _ in wire:
        try:
            if abs((dt.date.fromisoformat(pub[:10]) - d).days) <= 1:
                return True
        except ValueError:
            continue
    return False


def self_check(cache, wire_all):
    """Median minutes from the newswire results release to the 8-K accepted for the same day, over covered filings
    whose times are both known. A few minutes is normal; hours mean a time-zone reading error."""
    diffs = []
    for tk, ent in (cache.get("tickers") or {}).items():
        for f in (ent.get("filings") or {}).values():
            a = f.get("accepted_et") or ""
            if len(a) < 16:
                continue
            ta = dt.datetime.strptime(a, "%Y-%m-%d %H:%M")
            best = None
            for pub, _ in wire_all.get(tk, []):
                if len(pub) < 16:
                    continue
                d = (ta - dt.datetime.strptime(pub[:16], "%Y-%m-%d %H:%M")).total_seconds() / 60
                if abs(d) <= 18 * 60 and (best is None or abs(d) < abs(best)):
                    best = d
            if best is not None:
                diffs.append(best)
    return {"n": len(diffs), "median_min": round(statistics.median(diffs), 1) if diffs else None}


def doc_url(cik, acc, name):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{name}"


def read_filing(cik, acc, primary, accepted):
    """(status, period, period key, where) for one 8-K."""
    raw = get(doc_url(cik, acc, primary)) if primary else None
    seg = item_202(text_of(raw)) if raw else ""
    st, p, k = classify(seg, accepted)
    if st in ("results", "preliminary") or not raw:
        return st, p, k, "8-K"
    # the body names no period: the release itself (EX-99.1), first lines only
    idx = get(doc_url(cik, acc, "index.json"), as_json=True) or {}
    items = ((idx.get("directory") or {}).get("item")) or []
    ex = [i.get("name") for i in items if re.search(r"(?i)ex[-_]?99|exhibit99|ex991|pressrel",
                                                    str(i.get("name") or "")) and
          str(i.get("name") or "").lower().endswith((".htm", ".html", ".txt"))]
    if not ex:
        return st, p, k, "8-K"
    rel = get(doc_url(cik, acc, sorted(ex)[0]))
    if not rel:
        return st, p, k, "8-K"
    head = text_of(rel)[:1200]
    pub = dt.date.fromisoformat(accepted[:10]) if accepted else None
    if P_PRELIM.search(head[:500]):
        p2, k2 = period_of(head[:500], pub)
        return "preliminary", p2, k2, "EX-99.1"
    if P_RESULTS.search(head) or re.search(r"\bReports?\b", head[:300]):
        p2, k2 = period_of(head[:400], pub)
        if k2:
            return "results", p2, k2, "EX-99.1"
    return st, p, k, "8-K"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default="")
    ap.add_argument("--budget-min", type=float, default=8.0)
    ap.add_argument("--max-docs", type=int, default=400)
    a = ap.parse_args()
    if not os.environ.get("CI") and not os.environ.get("EARNINGS_SEC_LOCAL"):
        print("earnings 8-K: not in CI (sec.gov is reachable only from the rebuild); cache untouched")
        return 0
    wire, names = newswire()
    try:
        cmap = {str(v["ticker"]).upper(): int(v["cik_str"])
                for v in json.load(io.open(TICKERS, encoding="utf-8")).values()}
    except Exception as e:  # noqa: BLE001
        print(f"::warning::earnings 8-K: {os.path.basename(TICKERS)} unreadable ({type(e).__name__}); nothing read")
        return 0
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if cache.get("rules_version") != RULES_VERSION:
        for ent in (cache.get("tickers") or {}).values():
            for f in (ent.get("filings") or {}).values():
                if f.get("status") != "covered":
                    f.pop("status", None)          # re-open under the new rules
        cache["rules_version"] = RULES_VERSION
    tks = cache.setdefault("tickers", {})
    want = sorted(a.tickers.split(",")) if a.tickers else sorted(names)
    t0, docs, lists, fails = time.time(), 0, 0, 0
    stats = {"results": 0, "preliminary": 0, "no_period": 0, "not_results": 0, "no_item": 0, "covered": 0}
    for tk in want:
        if time.time() - t0 > a.budget_min * 60:
            print(f"earnings 8-K: time budget reached after {lists} filing lists; the rest next run")
            break
        cik = cmap.get(tk) or cmap.get(tk.replace(".", "-"))
        if not cik:
            continue
        try:
            sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"  {tk}: EDGAR filing list unreadable ({type(e).__name__})")
            if fails >= 8 and lists == 0:
                print("::warning::earnings 8-K: EDGAR unreachable; cache untouched")
                return 3
            continue
        lists += 1
        rec = ((sub or {}).get("filings") or {}).get("recent") or {}
        cols = ["accessionNumber", "form", "items", "filingDate", "acceptanceDateTime", "primaryDocument"]
        if not all(isinstance(rec.get(c), list) for c in cols):
            continue
        ent = tks.setdefault(tk, {"cik": cik, "filings": {}})
        ent["cik"] = cik
        fl = ent.setdefault("filings", {})
        for acc, form, items, fdate, acct, prim in zip(*(rec[c] for c in cols)):
            if form != "8-K" or "2.02" not in str(items or "") or str(fdate) < FROM or not ACC.match(str(acc)):
                continue
            f = fl.setdefault(acc, {})
            f.update({"form": form, "items": items, "filing_date": fdate, "accepted_et": accepted_et(acct),
                      "url": doc_url(cik, acc, f"{acc}-index.htm")})
            if f.get("status") and f["status"] != "covered":
                continue
            if covered(f["accepted_et"] or fdate, wire.get(tk, [])):
                f["status"] = "covered"
                continue
            f.pop("status", None)              # was covered by a newswire row that is gone: open it
            if docs >= a.max_docs or time.time() - t0 > a.budget_min * 60:
                continue                       # opened on a later run
            try:
                st, p, k, where = read_filing(cik, acc, prim, f["accepted_et"])
            except Exception as e:  # noqa: BLE001
                print(f"  {tk} {acc}: filing unreadable ({type(e).__name__}); next run")
                continue
            docs += 1
            f.update({"status": st, "period": p, "period_key": k, "where": where})
    for ent in tks.values():
        for f in (ent.get("filings") or {}).values():
            if f.get("status") in stats:
                stats[f["status"]] += 1
    cache["check"] = self_check(cache, {tk: [(p, k) for p, k in v] for tk, v in wire.items()})
    cache["fetched"] = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    if lists == 0:
        print("::warning::earnings 8-K: no filing list read; cache untouched")
        return 3
    tmp = CACHE + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, CACHE)
    print(f"earnings 8-K: {lists} filing lists, {docs} filings opened; " +
          ", ".join(f"{v} {k}" for k, v in stats.items()) +
          f"; 8-K minus newswire median {cache['check']['median_min']} min over {cache['check']['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
