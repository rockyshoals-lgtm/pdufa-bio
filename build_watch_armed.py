# -*- coding: utf-8 -*-
"""build_watch_armed.py -- what the every-minute news watcher on Vercel listens for.

David, 2026-11-27: "Ensure its down to minutes". The GitHub news watch (news-watch.yml) runs every 15 minutes at
best and only raises HELD leads; a person or a reviewing session then verifies and publishes, so the measured
posting speed (/research/posting-speed) ran a median 13 h after the source. The fast lane runs on Vercel
(pdufa_site_src/api/cron/news-watch.mjs, every minute): it reads the sponsors' own releases, their SEC filings and
the FDA's own press feed, and posts a decision within the minute ONLY when its strict automatic check passes on a
primary source (see the module's header). Everything else stays a lead for the existing watchers.

This writes pdufa_site_src/api/_watch_armed.mjs (a leading underscore keeps it from being a route): every armed
PDUFA row (watch_sponsor_newswire.armed_rows: type PDUFA, status Upcoming) with
  * its match terms (watch_sponsor_newswire.terms_for, rules 1.3 a-d, so one drug matches the same way in every
    watcher) and the terms it SHARES with another row of the same ticker (armed or decided), where only the
    indication words can tell the rows apart;
  * its indication words (watch_fmp_press.indication_score's words);
  * the sponsor's SEC CIK (sec_company_tickers.json) and its own news feeds (_sponsor_feeds.json);
and the kill switch and manual retractions from _fast_lane.json.

Run in the rebuild after dataset.mjs is written (pdufa-rebuild.yml), so a row armed today is heard on the next
deploy. Guard: tests/test_live_watch.py.

    python build_watch_armed.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watch_sponsor_newswire as W  # noqa: E402
import watch_fmp_press as F  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
OUT = os.path.join(HERE, "pdufa_site_src", "api", "_watch_armed.mjs")
FEEDS = os.path.join(HERE, "_sponsor_feeds.json")
TICKERS = os.path.join(HERE, "sec_company_tickers.json")
SWITCH = os.path.join(HERE, "_fast_lane.json")


# Indication words that do not tell two applications apart.
IND_NOISE = {"application", "approval", "children", "class", "resubmission", "activated", "advanced", "patients",
             "adult", "adults", "pediatric", "label", "labeling", "supplemental", "sNDA", "sBLA", "update"}


def ind_words(row):
    ind = str(((row.get("_d") or {}).get("indication")) or "")
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z-]{4,}", ind) if w.lower() not in F.IND_STOP}
    words |= set(re.findall(r"\(([A-Za-z0-9]{2,12})\)", ind))
    return sorted((w for w in words if w.lower() not in {x.lower() for x in IND_NOISE}), key=str.lower)


# Words that describe a form or a pack, never the drug (strong terms only). Trial names never qualify: they stand
# after " - " in the row's name, which strong_terms() cuts off.
GENERIC = {"oral", "cream", "film", "buccal", "sublingual", "capsule", "capsules", "formulation", "carbonate",
           "inhalation", "suspension", "liposome", "lower", "doses", "once-weekly", "weekly", "blister", "co-pack",
           "fast-acting", "gastro-resistant", "tablet", "tablets", "injection", "solution", "extended", "release",
           "resubmission", "children", "adults", "full", "approval"}


def strong_terms(row):
    """The drug's own identifiers: brand and name words before any " - " (indication, trial), " + " or " with "
    (combination partner), plus single-word parentheticals in that part (code names). A term is strong when it is
    at least 5 characters, or a code with a digit (AD109, AXS-12). These are the only terms the fast lane accepts:
    a headline that names only a trial, a partner drug or a form word is left to the watchers' leads."""
    out = []

    def add(w):
        w = w.strip("-.,;:")
        if not w or w.lower() in GENERIC or w.lower() in (x.lower() for x in out):
            return
        if not re.search(r"[A-Za-z]{2}", w):
            return
        if len(w) >= 5 or (re.search(r"\d", w) and re.search(r"[A-Za-z]", w) and len(w) >= 4):
            out.append(w)

    brand = str(((row.get("_d") or {}).get("brand")) or "")
    for w in re.split(r"\s+", brand):
        add(w)
    head = re.split(r" - | \+ | with ", str(row.get("name") or ""), maxsplit=1)[0]
    for inner in re.findall(r"\(([^)]*)\)", head):
        if len(inner.split()) == 1:
            add(inner)
    for w in re.split(r"\s+", re.sub(r"\([^)]*\)", " ", head)):
        add(w)
    return out


APPROVALS = os.path.join(HERE, "_fda_approvals_months.json")


def _pat(t):
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I)


def marketed_hits(terms, rows, approvals):
    """Where a term already names a U.S.-approved product: a decided Approved PDUFA row, or an FDA approval
    letter since 2025 (_fda_approvals_months.json). Such a drug may be armed only with need words."""
    out = []
    for t in terms:
        p = _pat(t)
        for r in rows:
            if r.get("type") == "PDUFA" and str(r.get("oc") or "").lower() == "approved" and p.search(str(r.get("name") or "")):
                out.append(f"{t}: approved row {r.get('id')}")
        for month in (approvals or {}).values():
            for it in month.get("items") or []:
                if p.search(f"{it.get('brand', '')} {it.get('generic', '')}"):
                    out.append(f"{t}: FDA approval {it.get('app')} ({it.get('brand')})")
    return sorted(set(out))


def build(rows, feeds, tickers, switch, today, approvals=None, log=print):
    by_tk = {v["ticker"].upper(): int(v["cik_str"]) for v in tickers.values()}
    armed = W.armed_rows(rows, today)
    by_ticker = {}
    for r in rows:
        if r.get("type") == "PDUFA":     # an approval or a letter can only be another application's, not a readout's
            by_ticker.setdefault(str(r.get("t") or "").upper(), []).append(r)
    lane = switch.get("fast_lane") or []
    out, unreviewed = [], []
    for r in armed:
        tk = str(r["t"]).upper()
        entries = [e for e in lane if str(e.get("t", "")).upper() == tk
                   and str(e.get("match", "")).lower() in str(r.get("name") or "").lower()]
        if len(entries) != 1:
            unreviewed.append(r["id"])
            continue
        e = entries[0]
        if sum(1 for o in armed if str(o["t"]).upper() == tk
               and str(e["match"]).lower() in str(o.get("name") or "").lower()) != 1:
            log(f"   not armed: {r['id']}: '{e['match']}' fits more than one armed row")
            continue
        terms = [t for t in e.get("terms") or [] if t]
        need = [w for w in e.get("need") or [] if w]
        avoid = [w for w in e.get("avoid") or [] if w]
        if not need:
            log(f"   not armed: {r['id']}: no need words (the headline must name this application's indication)")
            continue
        phrases = [w for w in e.get("phrases") or [] if w]
        if not phrases:
            log(f"   not armed: {r['id']}: no indication phrases (the headline's closing clause must name one)")
            continue
        hits = marketed_hits(terms, [o for o in rows if o.get("id") != r.get("id")], approvals)
        if hits:
            log(f"   note: {r['id']}: {' ; '.join(hits[:3])} -- armed on its need words only")
        shared = sorted({t for t in terms for o in by_ticker.get(tk, [])
                         if o.get("id") != r.get("id") and _pat(t).search(str(o.get("name") or ""))}, key=str.lower)
        siblings = [{"id": o.get("id"), "ind": ind_words(o)} for o in by_ticker.get(tk, [])
                    if o.get("id") != r.get("id") and any(_pat(t).search(str(o.get("name") or "")) for t in shared)]
        out.append({
            "id": r["id"], "t": tk, "company": r.get("company") or "", "name": r.get("name") or "",
            "d": str(r.get("d") or "")[:10], "url": r.get("url") or "",
            "terms": terms, "need": need, "avoid": avoid, "phrases": phrases,
            "tok": [w for w in e.get("tok") or [] if w], "partners": [w for w in e.get("partners") or [] if w],
            "forms": [w for w in e.get("forms") or [] if w], "aliases": [w for w in e.get("aliases") or [] if w],
            "cls": [w for w in e.get("cls") or [] if w], "paren": [w for w in e.get("paren") or [] if w], "shared": shared, "ind": ind_words(r), "siblings": siblings,
            "cik": by_tk.get(tk) or by_tk.get(tk + "Q"),
            "feeds": [f for f in (feeds.get(tk) or {}).get("feeds") or [] if str(f).startswith("https://")],  # RSS only; "html:" pages are not read here
        })
    if unreviewed:
        log(f"   {len(unreviewed)} armed row(s) not on the reviewed fast-lane list (they keep the reviewed path): "
            + ", ".join(unreviewed))
    out.sort(key=lambda x: (x["t"], x["d"], x["id"]))
    # Every PDUFA row's status, so the watcher can tell a post it made from the reviewed record: confirmed when the
    # reviewed row says the same outcome, retracted when it says another (api/cron/news-watch.mjs, self-heal).
    status = {r["id"]: {"st": r.get("st") or "", "oc": r.get("oc") or "", "dcd": str(r.get("dcd") or "")[:10],
                        "url": r.get("url") or ""}
              for r in rows if r.get("type") == "PDUFA" and r.get("id")}
    return {
        "as_of": today.isoformat(),
        "publish": bool(switch.get("publish", False)),
        "retract": dict(switch.get("retract") or {}),
        "rows": out,
        "status": status,
    }


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    feeds = json.load(io.open(FEEDS, encoding="utf-8")) if os.path.exists(FEEDS) else {}
    tickers = json.load(io.open(TICKERS, encoding="utf-8")) if os.path.exists(TICKERS) else {}
    switch = json.load(io.open(SWITCH, encoding="utf-8")) if os.path.exists(SWITCH) else {}
    approvals = json.load(io.open(APPROVALS, encoding="utf-8")) if os.path.exists(APPROVALS) else {}
    data = build(rows, feeds, tickers, switch, W.eastern_today(), approvals)
    body = ("// Generated by build_watch_armed.py from dataset.mjs, _sponsor_feeds.json, sec_company_tickers.json and\n"
            "// _fast_lane.json. Do not edit by hand. Read by api/cron/news-watch.mjs (every minute).\n"
            "export default " + json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + ";\n")
    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if old != body:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
    n_cik = sum(1 for r in data["rows"] if r["cik"])
    n_feed = sum(1 for r in data["rows"] if r["feeds"])
    print(f"watch armed: {len(data['rows'])} armed row(s); {n_cik} with an SEC CIK, {n_feed} with a sponsor feed; "
          f"publishing {'ON' if data['publish'] else 'OFF'}; {len(data['retract'])} manual retraction(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
