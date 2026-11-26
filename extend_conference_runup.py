# -*- coding: utf-8 -*-
"""extend_conference_runup.py -- new conference run-up rows from companies' own releases (cache only).

The published study (conf_study/conference_runup_PUBLISHED.csv) stops at 2026-06-04. This finds later
presentations from the presenting company's own press release and prices them with the study's exact
window arithmetic, into a SEPARATE cache, _conference_runup_additions.json. Nothing here is published:
rows are folded into the study only after a red team has checked them against their releases.

ANCHOR (one rule for every row here, stated on each row as anchor_basis):
  the Eastern publication date of the company's EARLIEST release whose headline names the meeting and
  reports data from it ("presents data", "announces results at ESMO 2026"), published from 42 days
  before the meeting opens to the day after it closes. (ASH posts abstracts about five weeks early, but
  companies' abstract-day releases mostly say "to present", which does not anchor, so ASH rows mostly
  anchor on the presentation release in December.)
  A headline that only announces a future presentation ("to present", "will present", "accepted") does
  not anchor, because it carries no data; nor does a topline release that says the full data will be
  presented at the meeting. Read from the headline only: a release led by a drug name rather than the
  company's, or naming the meeting only in its body, is missed (no row, or a later release anchors).

ATTRIBUTION: fetch_earnings_dates.mentions: the headline opens with the company's own name AND the release carries
the ticker's exchange tag or full name. A partner's release that only cites the ticker is not the ticker's.

PRICES (identical to conf_study/RUN_LOCALLY_build_study.py): FMP historical-price-eod/light; i = first
trading day on or after the anchor; needs 35 trading days before and 11 after; d1 = close at i-1;
runup_Nd = d1 / close(i-N) - 1; event_day = close(i+1) / d1 - 1; post_5d, post_10d from d1. Percent,
2 decimals. A row whose window has not closed is "pending"; a window outside -95%..+300% is held as "check"
(a split FMP adjusts late looks like that); rows priced in the last 30 days are priced again.

EVERY RUN re-checks every stored row against the current rules and drops rows that fail. RULES_VERSION re-reads
every ticker when a rule changes, so the right release is found again. Reads are incremental: each ticker is read
from OVERLAP_DAYS before its last read, and from the start of any meeting window it has not been read for.

KEYS follow the published study's meeting codes (STUDY_CODE) at one row per ticker per meeting edition; the
study has one row per asset, so folding these in needs the asset read from each release.

Meetings: conferences.json plus conf_study/meetings_extra.json (past 2026 editions not in the calendar),
every row with its organiser source URL.

    python extend_conference_runup.py [--since 2026-06-05] [--tickers A,B] [--budget-min 8] [--price-min 2]
"""
import argparse, datetime as dt, io, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_earnings_dates as FE  # noqa: E402

CACHE = os.path.join(HERE, "_conference_runup_additions.json")
PUBLISHED = os.path.join(HERE, "conf_study", "conference_runup_PUBLISHED.csv")
EXTRA = os.path.join(HERE, "conf_study", "meetings_extra.json")
PX_URL = "https://financialmodelingprep.com/stable/historical-price-eod/light"
EARLY_DAYS, LATE_DAYS = 42, 1
EARLY_DATE = "2026-06-05"   # the published study stops 2026-06-04
WINDOWS = [("runup_30d", -30), ("runup_20d", -20), ("runup_10d", -10), ("runup_5d", -5)]

RULES_VERSION = 3   # bump when a headline or attribution rule changes: stored rows are re-checked, every ticker re-read

# How each meeting is named in headlines. The code itself (word-bounded) always counts unless it is in NO_BARE;
# these add the names companies actually print. Longest names are tried first, so "ESMO Asia" never lands on ESMO.
ALIASES = {
    "ASH": ["American Society of Hematology", "ASH Annual Meeting"],
    "ACR": ["ACR Convergence", "American College of Rheumatology"],
    "AHA": ["AHA Scientific Sessions", "American Heart Association Scientific Sessions",
            "American Heart Association's Scientific Sessions", "American Heart Association (AHA) Scientific Sessions"],
    "AASLD": ["The Liver Meeting"],
    "ASN": ["Kidney Week", "American Society of Nephrology"],
    "ESMO": ["European Society for Medical Oncology"],
    "ESC": ["ESC Congress", "European Society of Cardiology"],
    "ERS": ["ERS Congress", "ERS International Congress", "European Respiratory Society"],
    "EASD": ["European Association for the Study of Diabetes"],
    "WCLC": ["World Conference on Lung Cancer"],
    "SITC": ["Society for Immunotherapy of Cancer"],
    "EHA": ["European Hematology Association"],
    "ADA": ["ADA Scientific Sessions", "American Diabetes Association Scientific Sessions",
            "American Diabetes Association's Scientific Sessions"],
    "EULAR": ["EULAR Congress", "European Congress of Rheumatology"],
    "ENDO": ["Endocrine Society"],
    "AAIC": ["Alzheimer's Association International Conference"],
    "ISTH": ["ISTH Congress", "International Society on Thrombosis and Haemostasis"],
    "EAN": ["European Academy of Neurology"],
    "ACG": ["American College of Gastroenterology"],
    "AAO": ["American Academy of Ophthalmology"],
    "ASBMR": ["American Society for Bone and Mineral Research"],
    "CTAD": ["Clinical Trials on Alzheimer's Disease"],
    "ACAAI": ["American College of Allergy, Asthma"],
    "SNO": ["Society for Neuro-Oncology"],
    "ASTRO": ["American Society for Radiation Oncology"],
    "WMS": ["World Muscle Society"],
    "ENA": ["EORTC-NCI-AACR", "EORTC NCI AACR", "EORTC/NCI/AACR"],
    "SABCS": ["San Antonio Breast Cancer Symposium"],
    "AES": ["American Epilepsy Society"],
}
# Name shapes with an edition number in the middle ("American Diabetes Association's 86th Scientific Sessions").
RX_ALIASES = {
    "ADA": [r"American Diabetes Association(?:'s|’s)?\s+(?:\d+(?:st|nd|rd|th)\s+)?Scientific Sessions",
            r"\bADA(?:'s|’s)?\s+(?:\d+(?:st|nd|rd|th)\s+)?Scientific Sessions",
            r"Scientific Sessions of the American Diabetes Association"],
    "AHA": [r"American Heart Association(?:'s|’s)?\s+(?:\d+(?:st|nd|rd|th)\s+)?Scientific Sessions",
            r"Scientific Sessions of the American Heart Association"],
}
# Codes too short or too common to trust bare in a headline: they count only through an alias or as code + year
# ("ASH 2026", "AHA 2026"), which is how most companies print them.
NO_BARE = {"ESC", "ADA", "AHA", "ACR", "ASH", "ERS", "ENDO", "EAN", "ERA", "APA", "BIO", "SNO", "AAO", "WMS",
           "AES", "ENA"}
# A headline that also names one of these is about a different meeting (of the same society, or a sibling meeting
# under the same brand). Meeting NAMES only: a disease ("Hypertension", "Heart Failure") is never excluded.
EXCLUDE = {
    "AHA": re.compile(r"AHA Hypertension|Hypertension (?:20\d\d )?Scientific Sessions|HCMS|Hypertrophic Cardiomyopathy "
                      r"(?:Medical Society|Scientific Sessions)|BCVS|Resuscitation Science Symposium|EPI\|?Lifestyle|Vascular Discovery|"
                      r"Quality of Care and Outcomes Research", re.I),
    "ESC": re.compile(r"ESC Heart Failure|Heart Failure (?:20\d\d|Congress)|EHRA|EuroPCR|EuroHeartCare|ESC Preventive|"
                      r"ACVC", re.I),
    "ADA": re.compile(r"Advanced Technologies (?:&|and) Treatments|ATTD|American Dental", re.I),
    "ERS": re.compile(r"Lung Science Conference|Sleep and Breathing Conference", re.I),
    "ASH": re.compile(r"Meeting on Hematologic Malignancies|Highlights of ASH|ASH/?ASCO|ASH Medical Educational", re.I),
    "ESMO": re.compile(r"Virtual Plenary|ESMO (?:GI|Breast|TAT|Gyn\w*|Sarcoma|Lung|Targeted|Asia|IO|Immuno)|"
                       r"World Congress on Gastrointestinal", re.I),
}
# The code the published study uses for the same meeting, so keys line up with it.
STUDY_CODE = {"IDWeek": "IDWEEK", "ObesityWeek": "OBESITYWEEK", "ASCO GI": "ASCO-GI", "ASCO GU": "ASCO-GU",
              "ESMO Breast": "ESMO-B"}

DATA = re.compile(r"\b(present(?:s|ed|ing)?|presentation|data|results?|findings|analys[ie]s|showcas\w+|"
                  r"report(?:s|ed)?|demonstrat\w+|show(?:s|ed|ing)?)\b", re.I)
# Announcements of a talk still to come carry no data. Read on the headline's main clause only (before the
# first ';' or ' - '), so "Presents Phase 3 Results at ESMO 2026; Company to Host Webcast" still counts.
FUTURE = re.compile(r"\b(to (?:present|report|showcase|highlight|share|host|participate|feature|unveil|"
                    r"discuss)|will (?:present|report|showcase|highlight|share|feature|be)|to be \w+|plans? to|"
                    r"accept(?:ed|ance)|selected|upcoming|investor (?:event|day|call)|webcast|"
                    r"conference call|KOL)\b", re.I)
# "Announces (Late-Breaking) Presentation(s) of ... Data at" is a notice of a talk unless a past-tense verb or
# a reported result follows.
NOTICE = re.compile(r"\bannounc\w*\s+(?:[\w-]+\s+){0,4}presentations?\b", re.I)
PAST = re.compile(r"\b(presented|reported|showed|shows|showing|demonstrat\w*|achieved|met|improved|reduced)\b", re.I)
NOT_DATA = re.compile(r"\b(inducement|financial results|quarter|investor alert|law firm|class action|"
                      r"shareholder)\b", re.I)


def meetings(since, today):
    rows = json.load(io.open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))["conferences"]
    if os.path.exists(EXTRA):
        rows = rows + json.load(io.open(EXTRA, encoding="utf-8"))["meetings"]
    out, seen = [], set()
    for c in rows:
        if not c.get("source") or not c.get("start") or not c.get("end"):
            continue
        lo = (dt.date.fromisoformat(c["start"]) - dt.timedelta(days=EARLY_DAYS)).isoformat()
        if c["end"] < since or lo > today:          # abstracts and data can come out before the meeting opens
            continue
        k = (c["code"], c["start"][:4])
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def _pat(c):
    code = c["code"]
    names = [code] if code not in NO_BARE else []
    names += ALIASES.get(code, [])
    pats = [re.compile(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])", re.I if n != n.upper() else 0)
            for n in sorted({n for n in names if n}, key=len, reverse=True)]
    pats.append(re.compile(r"(?<![A-Za-z])" + re.escape(code) + r"[\s-]+20\d\d\b"))   # "ASH 2026", case as printed
    pats += [re.compile(rx, re.I) for rx in RX_ALIASES.get(code, [])]
    return pats


def names_meeting(title, c, others):
    """The headline names THIS meeting, no longer-named sibling ('ESMO Asia' is not ESMO), no other meeting of the
    same society (AHA Hypertension is not AHA), and no other edition year."""
    for o in others:
        if o is not c and o["code"] != c["code"] and o["code"].startswith(c["code"] + " "):
            if any(p.search(title) for p in _pat(o)):
                return False
    if c["code"] in EXCLUDE and EXCLUDE[c["code"]].search(title):
        return False
    if not any(p.search(title) for p in _pat(c)):
        return False
    yrs = set(re.findall(r"\b(20\d\d)\b", title))
    return not yrs or c["start"][:4] in yrs


CLAUSE = re.compile(r";|\s[-–—|]\s")


def main_clause(title):
    head = CLAUSE.split(title, maxsplit=1)[0]
    return head if len(head.split()) >= 3 else title     # "Co - Late-Breaking Data Presented at AHA": keep it whole


def anchors(title, m, ms):
    """This headline anchors a row for meeting m: it reports data, names m, and no clause that names m is a notice
    of a talk to come ("Reports Topline Results; Full Data to Be Presented at ESMO 2026" is a topline release)."""
    if not (is_data_headline(title) and names_meeting(title, m, ms)):
        return False
    pats = _pat(m)
    for cl in CLAUSE.split(title):
        if any(p.search(cl) for p in pats) and (FUTURE.search(cl) or (NOTICE.search(cl) and not PAST.search(cl))):
            return False
    return True


def is_data_headline(title):
    m = main_clause(title)
    if not DATA.search(m) or FUTURE.search(m) or NOT_DATA.search(title):
        return False
    if NOTICE.search(m) and not PAST.search(m):
        return False
    return True


def own(tk, name, title, text):
    """The release is the ticker's own: its headline opens with the company's name and the release carries the
    ticker's exchange tag or full name (fetch_earnings_dates.mentions). A partner's release that only cites the
    ticker ('Akeso Presents ... partner Summit (NASDAQ: SMMT)') is not."""
    return FE.mentions(tk, name, title, text)


def study_code(code):
    return STUDY_CODE.get(code, code)


def passes(r, ms, name):
    """A stored row still passes every current rule (re-checked each run, and by the guard)."""
    code = r.get("meeting_code", r.get("conf"))
    m = next((x for x in ms if x["code"] == code and x["start"] == r.get("meeting_start")), None)
    if m is None:   # the calendar dropped a past meeting: the row keeps the meeting it was found for
        m = {"code": code, "start": r.get("meeting_start", ""), "end": r.get("meeting_end", ""),
             "source": r.get("meeting_source", "")}
    if not (m["start"] and m["end"] and str(m["source"]).startswith("https://")):
        return False
    lo = (dt.date.fromisoformat(m["start"]) - dt.timedelta(days=EARLY_DAYS)).isoformat()
    hi = (dt.date.fromisoformat(m["end"]) + dt.timedelta(days=LATE_DAYS)).isoformat()
    t = r.get("release_title", "")
    return (lo <= r.get("anchor", "") <= hi and anchors(t, m, ms)
            and own(r["ticker"], name, t, r.get("release_excerpt", "")))


def prices(tk, frm, key):
    q = urllib.parse.urlencode({"symbol": tk, "from": frm, "to": dt.date.today().isoformat(), "apikey": key})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{PX_URL}?{q}", headers=FE.UA), timeout=25) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            if isinstance(d, list):
                return sorted((x["date"][:10], float(x["price"])) for x in d if x.get("price"))
            return None
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                return None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2 + attempt * 3)
    return None


def window(series, anchor):
    """The study's arithmetic. None when the window is not complete."""
    dates = [d for d, _ in series]
    i = next((k for k, d in enumerate(dates) if d >= anchor), len(dates))
    if i < 35 or i + 11 >= len(dates):
        return None
    P = lambda k: series[i + k][1]  # noqa: E731
    d1 = P(-1)
    if d1 <= 0:
        return None
    out = {lbl: round((d1 / P(k) - 1) * 100, 2) for lbl, k in WINDOWS if P(k) > 0}
    out["event_day"] = round((P(1) / d1 - 1) * 100, 2)
    out["post_5d"] = round((P(5) / d1 - 1) * 100, 2)
    out["post_10d"] = round((P(10) / d1 - 1) * 100, 2)
    out["price_d1"] = round(d1, 2)
    out["d_minus_1"] = dates[i - 1]
    out["d0"] = dates[i]
    return out


def published_keys():
    import csv
    try:
        return {(r["ticker"], r["conf"], str(r["year"])[:4])
                for r in csv.DictReader(io.open(PUBLISHED, encoding="utf-8-sig", errors="replace"))}
    except Exception:  # noqa: BLE001
        return set()


RANGE = (-95.0, 300.0)   # a window outside this is held as "check" (a late split adjustment looks like this)
OVERLAP_DAYS = 10        # re-read this far before where a ticker's last read stopped (FMP backfills releases)


def _mlo(m):
    return (dt.date.fromisoformat(m["start"]) - dt.timedelta(days=EARLY_DAYS)).isoformat()


def save(out):
    tmp = CACHE + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True))
    os.replace(tmp, CACHE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=EARLY_DATE, help="meetings ending on or after this day")
    ap.add_argument("--tickers", default="")
    ap.add_argument("--budget-min", type=float, default=8.0, help="minutes for reading releases")
    ap.add_argument("--price-min", type=float, default=2.0, help="minutes for pricing")
    a = ap.parse_args()
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        print("FMP_API_KEY not set; conference additions not refreshed")
        return 0
    today = dt.date.today()
    ms = meetings(a.since, today.isoformat())
    if not ms:
        print("no meetings in range")
        return 0
    mkey = {f"{m['code']} {m['start'][:4]}": m for m in ms}
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if cache.get("rules_version") != RULES_VERSION:
        cache["scanned"] = {}            # new rules: every ticker is read again in full
    uni = FE.universe()
    if a.tickers:
        uni = {t: uni.get(t, t) for t in a.tickers.split(",")}
    # Rows that no longer pass the current rules, or whose meeting left the list, are dropped (and found again
    # from the right release when that ticker is re-read).
    rows, dropped = {}, 0
    for r in cache.get("rows", []):
        if passes(r, ms, r.get("company") or uni.get(r["ticker"], r["ticker"])):   # the name it was found under
            rows[r["key"]] = r
        else:
            dropped += 1
    pub = published_keys()
    # scanned[tk] = {"to": last day read, "m": meeting keys it was read for}. A ticker is read from OVERLAP_DAYS
    # before "to", and from the start of any new meeting's window; a ticker never read reads everything.
    scanned = {tk: v for tk, v in cache.get("scanned", {}).items() if isinstance(v, dict)}
    tried = cache.get("tried", {})
    fails = cache.get("fails", {})      # consecutive failed reads; a ticker failing 3+ times goes to the back
    frm_all = min(_mlo(m) for m in ms)
    to = (today + dt.timedelta(days=1)).isoformat()
    order = sorted(uni.items(), key=lambda kv: (fails.get(kv[0], 0) >= 3, scanned.get(kv[0], {}).get("to", ""),
                                                tried.get(kv[0], ""), kv[0]))

    def snapshot():
        return {"about": "Conference run-up rows after the published study, from companies' own releases. Not in the "
                         "published study; folded in only after a red team. See extend_conference_runup.py.",
                "built": today.isoformat(), "since": a.since, "rules_version": RULES_VERSION,
                "meetings": sorted(mkey), "scanned": scanned, "tried": tried, "fails": fails,
                "rows": sorted(rows.values(), key=lambda r: (r["anchor"], r["ticker"]))}

    t0, read, failed, streak = time.time(), 0, 0, 0
    for tk, name in order:
        if time.time() - t0 > a.budget_min * 60:
            print(f"conference additions: read budget reached after {read} tickers")
            break
        if streak >= 5:
            print("::warning::conference additions: 5 tickers in a row unreadable; stopping the read")
            break
        if name == tk:
            continue
        sc = scanned.get(tk)
        if sc:
            f = max(frm_all, (dt.date.fromisoformat(sc["to"]) - dt.timedelta(days=OVERLAP_DAYS)).isoformat())
            new = [mkey[k] for k in mkey if k not in set(sc.get("m", []))]
            if new:
                f = min(f, min(_mlo(m) for m in new))
        else:
            f = frm_all
        tried[tk] = today.isoformat()
        items = FE.fetch(tk, f, to, key)
        if items is None:
            failed += 1
            streak += 1
            fails[tk] = fails.get(tk, 0) + 1
            continue
        fails.pop(tk, None)
        read += 1
        streak = 0
        for it in sorted(items, key=lambda x: str(x.get("publishedDate") or "")):
            title, text = FE.clean(it.get("title")), FE.clean(it.get("text"))
            pub_et = str(it.get("publishedDate") or "")[:10]   # FMP timestamps are Eastern (CLAUDE.md rule 1)
            url = str(it.get("url") or "")
            if not (title and pub_et and url.startswith("https://")) or not is_data_headline(title):
                continue
            for m in ms:
                hi = (dt.date.fromisoformat(m["end"]) + dt.timedelta(days=LATE_DAYS)).isoformat()
                if not (_mlo(m) <= pub_et <= hi) or not anchors(title, m, ms):
                    continue
                if not own(tk, name, title, text):
                    continue
                code = study_code(m["code"])
                if (tk, code, m["start"][:4]) in pub:
                    continue
                k = f"{tk}|{code}|{m['start'][:4]}"
                old = rows.get(k)
                if old and old["anchor"] <= pub_et:
                    continue                      # keep the earliest data release
                rows[k] = {"key": k, "ticker": tk, "company": name, "conf": code, "meeting_code": m["code"],
                           "year": int(m["start"][:4]), "conf_full": f"{m['name']} {m['start'][:4]}",
                           "meeting_start": m["start"], "meeting_end": m["end"],
                           "meeting_source": m["source"], "anchor": pub_et,
                           "anchor_basis": "earliest company release found reporting data from the meeting",
                           "release_title": title[:300], "release_url": url, "release_excerpt": text[:600],
                           "status": "pending", "found": today.isoformat()}
        scanned[tk] = {"to": today.isoformat(), "m": sorted(mkey)}
        if read % 40 == 0:
            save(snapshot())
        time.sleep(0.12)
    # Price rows whose window may be complete, with the study's own arithmetic. Rows priced in the last 30 days
    # are priced again, so a split FMP adjusts late is picked up.
    priced, t1 = 0, time.time()
    for r in sorted(rows.values(), key=lambda r: r.get("priced", "")):
        if time.time() - t1 > a.price_min * 60:
            print("conference additions: price budget reached")
            break
        if r.get("status") == "complete" and r.get("priced", "") < (today - dt.timedelta(days=30)).isoformat():
            continue
        a0 = dt.date.fromisoformat(r["anchor"])
        if (today - a0).days < 16:
            continue
        s = prices(r["ticker"], (a0 - dt.timedelta(days=80)).isoformat(), key)
        time.sleep(0.12)
        if not s:
            continue
        w = window(s, r["anchor"])
        if not w:
            continue
        r.update(w)
        vals = [w[f] for f in ("runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day", "post_5d", "post_10d")
                if f in w]
        r["status"] = "complete" if len(vals) == 7 and all(RANGE[0] < v < RANGE[1] for v in vals) else "check"
        r["priced"] = today.isoformat()
        priced += 1
    out = snapshot()
    save(out)            # rows are only ever added, re-priced or dropped by the rules, so a failed read loses nothing
    if read == 0:
        print(f"::warning::conference additions: no ticker readable ({failed} failed)")
        return 3
    done = sum(1 for r in out["rows"] if r["status"] == "complete")
    print(f"conference additions: read {read} tickers ({failed} failed); {len(scanned)}/{len(uni)} scanned; "
          f"{len(out['rows'])} rows, {done} priced ({priced} this run), {dropped} dropped by the rules, "
          f"{len(ms)} meetings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
