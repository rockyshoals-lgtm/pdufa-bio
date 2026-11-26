# -*- coding: utf-8 -*-
"""watch_fmp_press.py -- every armed sponsor's press releases, from the newswires, every 15 minutes.

Audit 2026-11-26 (news speed). Measured on the last ten decisions, the time from the sponsor's own release
to the decision on pdufa.bio ran from about 3 hours (Regeneron, Nov 18) to 35 hours (Roche adjuvant
Wilserdly, Nov 23), and Capricor's Nov 20 Complete Response Letter (GlobeNewswire, 7:55 PM ET) raised no
lead at all:
  * the watchers run only inside the rebuild, whose crons (03:00, 05:00, 14:00 PT) GitHub starts 1.5 to 5 h
    late, so a release after the close waited for the next morning;
  * only 11 of 34 armed sponsors have a news feed watch_sponsor_newswire.py can read; Capricor has none;
  * Capricor headlined the letter "Provides Regulatory Update on Deramiocel BLA", and every watcher wanted
    the decision word in the headline.

This pass reads the sponsors' own releases as the newswires carried them (GlobeNewswire, Business Wire,
PR Newswire), through FMP's press-release feed, for every armed PDUFA row (watch_sponsor_newswire's
armed_rows), and raises a LEAD when
  (a) the headline passes watch_sponsor_newswire.match (decision, withdrawal, extension or RTF headline
      naming an armed drug), or
  (b) one SENTENCE of the release names an armed drug together with an FDA decision (approved / approval
      of / Complete Response Letter), and is not an "if approved" / acceptance / submission / expectation
      sentence (watch_edgar_8k's DECIDE / FDA / NOT rules).
Match terms come from watch_sponsor_newswire.terms_for (rules 1.3 a-d), so one drug matches the same way
in every watcher.

Same contract as the other watchers: a lead holds its own row (quarantine_leads.py) and is NEVER published
by itself; a person or a reviewing session verifies it against the release and the FDA and publishes the
decision page. Non-events are acked in _fmp_press_ack.json with a reason. FMP publishedDate is Eastern
time (RULE 1), and the lead prints it with "ET".

    python watch_fmp_press.py [--days 3] [--fixture items.json]
Exit 1 when there is an unreviewed lead, 2 when it could not read the feed (blind, not a lead), else 0.
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.parse
import unicodedata
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watch_sponsor_newswire as W  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_fmp_press_ack.json")
FMP_PR = "https://financialmodelingprep.com/stable/news/press-releases"
DECIDE = re.compile(r"\b(approved|approval (of|for)|granted approval|approves|complete response letter|CRL)\b", re.I)
FDA = re.compile(r"\b(FDA|Food and Drug Administration)\b")
NOT = re.compile(r"\b(if approved|potential(ly)? approv\w*|seek\w* approval|accept(s|ed|ance) (of|for)|"
                 r"submi(t|tted|ssion)|PDUFA (target|goal)|target action date|anticipat\w+|expect\w*|"
                 r"previously approved|was approved in \d{4}|approved in (the )?(EU|European|Japan|China))\b", re.I)
# (b) also needs a news verb: product boilerplate ("EKITNA is approved by the FDA for ...") names an approved
# drug in every later release of the sponsor and would raise a lead on its next armed goal each time.
NEWS = re.compile(r"\b(today|announc\w*|receiv\w*|has approved|approves|granted|issued)\b", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"(])")
# An abbreviation's full stop is not a sentence end: Capricor wrote "a Complete Response Letter (CRL) from the
# U.S. Food and Drug Administration", and splitting after "U.S." put the CRL and the FDA in two sentences.
ABBR = re.compile(r"\b(U\.S|U\.K|E\.U|Inc|Corp|Ltd|Co|Dr|No|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec|vs|St)\.")
IND_STOP = {"adults", "adult", "patients", "patient", "treatment", "treated", "prior", "received", "receiving",
            "combination", "therapy", "years", "older", "associated", "disease", "indicated", "including", "with",
            "without", "least", "chronic", "first", "line", "second", "previously", "after", "following"}
# (c) a sponsor headline that the drug "Receives Traditional Approval" often leaves out the FDA (BridgeBio,
# Welgemda, Nov 23). Any other regulator named in the headline makes it not ours.
RECEIVES = re.compile(r"\b(receives?|granted|wins?|secures?)\b[^.]{0,40}?\bapproval\b", re.I)
OTHER_REG = re.compile(r"\b(EU|European|EC|EMA|CHMP|Japan\w*|China|Chinese|NMPA|PMDA|MHRA|UK|Health Canada|"
                       r"Swissmedic|TGA|Australia\w*|Brazil\w*|ANVISA|Korea\w*|MFDS)\b")
BATCH = 5            # symbols per request; a big sponsor's releases must not crowd out a small one's


def load_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def term_in(term, text):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I)


def sentence_hits(text, rows):
    """[(row, term, sentence)] for a sentence naming an armed drug with an FDA decision, (b) above."""
    out = []
    text = ABBR.sub(lambda m: m.group(1).replace(".", ""), re.sub(r"\s+", " ", text or ""))
    for s in SENT.split(text):
        if not (FDA.search(s) and DECIDE.search(s) and NEWS.search(s)) or NOT.search(s):
            continue
        for r in rows:
            for t in W.terms_for(r):
                if term_in(t, s):
                    out.append((r, t, s.strip()))
                    break
    return out


def indication_score(row, text):
    """How many of the row's indication words (and acronyms such as GIST, NonAdvSM) the release names."""
    ind = str(((row.get("_d") or {}).get("indication")) or "")
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z-]{4,}", ind) if w.lower() not in IND_STOP}
    words |= set(re.findall(r"\(([A-Za-z0-9]{2,12})\)", ind))
    return sum(1 for w in words if term_in(w, text))


def narrow(found, text, siblings):
    """One release that names a drug shared by two of the sponsor's rows (Cogent's bezuclastinib: GIST decided
    Nov 24, systemic mastocytosis armed for Dec 30) leads on a row only when no OTHER row carrying the same term,
    armed or already decided, fits the release's indication better. When the release names no indication,
    every row stays and the reviewer decides."""
    out = []
    for r, t, why in found:
        mine = indication_score(r, text)
        rival = max((indication_score(o, text) for o in siblings
                     if o["id"] != r["id"] and any(term_in(t, x) for x in W.terms_for(o))), default=-1)
        if rival <= mine:
            out.append((r, t, why))
    return out


def leads_for(items, by_tk, ack, all_by_tk=None):
    """[(row, term, item, why, key)] for the given FMP items. all_by_tk: every row of each ticker, decided ones
    included, for narrow(); defaults to by_tk."""
    all_by_tk = all_by_tk or by_tk
    out, seen = [], set()
    for it in items:
        tk = str(it.get("symbol") or "").upper()
        rows = by_tk.get(tk)
        if not rows:
            continue
        # NFKC: PolyPid wrote "D-PLEX₁₀₀" (subscript digits); the row says D-PLEX100.
        title = unicodedata.normalize("NFKC", str(it.get("title") or ""))
        text = unicodedata.normalize("NFKC", str(it.get("text") or ""))
        found = [(r, t, "headline") for r, t in W.match(title + " \n " + text, rows)]
        found += [(r, t, "sentence: " + s[:200]) for r, t, s in sentence_hits(title + ". " + text, rows)]
        if RECEIVES.search(title) and not OTHER_REG.search(title) and not NOT.search(title):
            for r in rows:
                t = next((t for t in W.terms_for(r) if term_in(t, title)), None)
                if t:
                    found.append((r, t, "headline: receives approval"))
        for r, t, why in narrow(found, title + " " + text, all_by_tk.get(tk, rows)):
            key = f"{r['id']}|{it.get('url') or title[:80]}"
            if key in ack or key in seen:
                continue
            seen.add(key)
            out.append((r, t, it, why, key))
    return out


def fetch_items(tickers, days, key):
    """FMP press releases for the tickers over the last `days` days. None when nothing could be read."""
    today = W.eastern_today()
    frm, to = (today - dt.timedelta(days=days)).isoformat(), (today + dt.timedelta(days=1)).isoformat()
    items, read = [], 0
    for i in range(0, len(tickers), BATCH):
        group = tickers[i:i + BATCH]
        q = urllib.parse.urlencode({"symbols": ",".join(group), "from": frm, "to": to, "limit": 100, "apikey": key})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"{FMP_PR}?{q}", headers=W.UA), timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                if isinstance(data, list):
                    items += data
                    read += 1
                else:
                    print(f"  FMP returned no list for {','.join(group)}: {str(data)[:120]}")
                break
            except Exception as e:  # noqa: BLE001
                if attempt:
                    print(f"  FMP unreachable for {','.join(group)}: {type(e).__name__}")
                time.sleep(2)
    return items if read else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="days of releases to read")
    ap.add_argument("--fixture", help="read FMP items from this JSON file instead of the API (tests)")
    a = ap.parse_args()
    rows = load_rows()
    armed = W.armed_rows(rows, W.eastern_today())
    by_tk = {}
    for r in armed:
        by_tk.setdefault(str(r["t"]).upper(), []).append(r)
    all_by_tk = {}
    for r in rows:
        all_by_tk.setdefault(str(r.get("t") or "").upper(), []).append(r)
    ack = json.load(io.open(ACK, encoding="utf-8")).get("acked", []) if os.path.exists(ACK) else []

    if a.fixture:
        items = json.load(io.open(a.fixture, encoding="utf-8"))
    else:
        key = os.environ.get("FMP_API_KEY", "").strip()
        if not key:
            print("fmp-press watch: FMP_API_KEY is not set; BLIND this run (not a lead)")
            return 2
        items = fetch_items(sorted(by_tk), a.days, key)
        if items is None:
            print("fmp-press watch: no FMP request succeeded; BLIND this run (not a lead)")
            return 2

    leads = leads_for(items, by_tk, ack, all_by_tk)
    print(f"fmp-press watch: {len(by_tk)} armed sponsor(s), {len(items)} release(s) read over {a.days} day(s)")
    if not leads:
        return 0
    print(f"FMP-PRESS WATCH: {len(leads)} unreviewed lead(s) on armed events:")
    for r, t, it, why, key in leads:
        print(f"   {r['t']} {str(r.get('name'))[:50]} (goal {r.get('d')}): {it.get('publishedDate')} ET "
              f"{it.get('publisher') or ''} \"{str(it.get('title'))[:120]}\" [matched '{t}', {why[:80]}] {it.get('url')}")
    print("\n   Each is a LEAD, not a fact: verify against the release and the FDA, publish the decision page, "
          "and ack non-events in _fmp_press_ack.json (key printed below).")
    for r, t, it, why, key in leads:
        print(f"   ack key: {key}")
        kind = W.outcome_kind(str(it.get("title") or "")) or "decision"
        W._emit_lead("fmp_press", r["id"], key,
                     f"[{kind}] {it.get('publishedDate')} ET \"{str(it.get('title'))[:160]}\" [{t}] {it.get('url')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
