# -*- coding: utf-8 -*-
"""watch_edgar_8k.py -- poll every armed SEC-registrant sponsor's own 8-K / 6-K filings, every run.

Audit 2026-10-03, item 2.4. 8 of 33 armed sponsors publish a readable news feed. Merck publishes none
(merck.com's /feed/ is empty), and MRK's Oct 10 ifinatamab deruxtecan decision rested on feeds we could
not read. Merck, like every U.S.-listed sponsor, files material news with the SEC. EDGAR full-text
search (watch_fda_approvals.py, third pass) lags its index by hours to days; this reads each sponsor's
submissions list directly (data.sec.gov/submissions/CIK##########.json), takes every 8-K and 6-K filed
in the last 10 days, opens its press-release exhibits, and raises a LEAD when one SENTENCE names an
armed drug (match terms from watch_sponsor_newswire.terms_for, rules 1.3 a-d) together with an FDA
decision (approved / approval of / Complete Response Letter), and is not an "if approved" / acceptance
/ submission sentence. Same contract as the other watchers: a lead holds its own row (quarantine), it
is never published by itself; non-events are acked in _edgar_8k_ack.json with a reason.

Also writes _sponsor_coverage.json: for every sponsor with an armed goal in the next 60 days, the
channels that can see its decision (sponsor feed, this EDGAR poll, the FDA's own feeds) or the recorded
reason it has none of its own (Roche: not an SEC registrant, no public RSS; the FDA feeds remain).
Times: EDGAR filingDate is the Eastern calendar date (RULE 1).

    python watch_edgar_8k.py [--days 10] [--horizon 60]
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
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watch_sponsor_newswire as W  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_edgar_8k_ack.json")
COVER = os.path.join(HERE, "_sponsor_coverage.json")
HEALTH = os.path.join(HERE, "_watch_health.json")
UA = {"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}
DECIDE = re.compile(r"\b(approved|approval (of|for)|granted approval|approves|complete response letter|CRL)\b", re.I)
FDA = re.compile(r"\b(FDA|Food and Drug Administration)\b")
NOT = re.compile(r"\b(if approved|potential(ly)? approv\w*|seek\w* approval|accept(s|ed|ance) (of|for)|"
                 r"submi(t|tted|ssion)|PDUFA (target|goal)|target action date|anticipat\w+|expect\w*|"
                 r"previously approved|was approved in \d{4}|approved in (the )?(EU|European|Japan|China))\b", re.I)
# Roche files nothing with the SEC; the reason is recorded, not guessed each run.
NO_SEC = {"RHHBY": "Roche Holding AG is not an SEC registrant (OTC ADR, no 8-K/6-K) and publishes no "
                   "news-release RSS; its U.S. decisions are covered by the FDA's What's New: Drugs feed "
                   "(watch_fda_drugs_feed.py) and Drugs@FDA (watch_fda_approvals.py)."}


def get(url, timeout=25, limit=3_000_000):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.read(limit).decode("utf-8", "replace")
    except Exception:
        return None


def cik_map():
    p = os.path.join(HERE, "sec_company_tickers.json")
    j = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    by_tk = {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()}
    by_title = {re.sub(r"[^a-z]", "", v["title"].lower())[:12]: int(v["cik_str"]) for v in j.values()}
    return by_tk, by_title


def find_cik(tk, company, by_tk, by_title):
    if tk in by_tk:
        return by_tk[tk]
    if tk + "Q" in by_tk:                      # bankruptcy suffix (BioXcel trades as BTAIQ)
        return by_tk[tk + "Q"]
    key = re.sub(r"[^a-z]", "", str(company or "").lower())[:12]
    return by_title.get(key)


def sentences(text):
    return re.split(r"(?<=[.!?])\s+(?=[A-Z\"(])", text)


def leads_in(text, rows):
    out = []
    for s in sentences(text):
        if len(s) > 600 or not FDA.search(s) or not DECIDE.search(s) or NOT.search(s):
            continue
        for r in rows:
            for t in W.terms_for(r):
                if re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", s, re.I):
                    out.append((r, t, s.strip()[:300]))
                    break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--horizon", type=int, default=60)
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    today = W.eastern_today() if hasattr(W, "eastern_today") else dt.date.today()
    horizon = today + dt.timedelta(days=a.horizon)
    armed = [r for r in rows if r.get("type") == "PDUFA" and str(r.get("st", "")).lower() == "upcoming"
             and r.get("d") and today - dt.timedelta(days=7) <= dt.date.fromisoformat(str(r["d"])[:10]) <= horizon]
    by = {}
    for r in armed:
        by.setdefault(str(r["t"]).upper(), []).append(r)
    ack = set(json.load(io.open(ACK, encoding="utf-8")).get("acked", [])) if os.path.exists(ACK) else set()
    feeds = json.load(io.open(os.path.join(HERE, "_sponsor_feeds.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(HERE, "_sponsor_feeds.json")) else {}
    by_tk, by_title = cik_map()
    since = today - dt.timedelta(days=a.days)
    coverage, leads, read_ok, blind, nfil = {}, [], 0, [], 0
    for tk, rs in sorted(by.items()):
        chans = []
        if (feeds.get(tk) or {}).get("feeds"):
            chans.append("sponsor_feed")
        cik = None if tk in NO_SEC else find_cik(tk, rs[0].get("company"), by_tk, by_title)
        reason = NO_SEC.get(tk)
        if cik:
            j = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
            time.sleep(0.15)
            if not j:
                blind.append(tk)
            else:
                read_ok += 1
                chans.append("edgar_8k")
                rec = json.loads(j)["filings"]["recent"]
                for i, form in enumerate(rec.get("form", [])):
                    if form not in ("8-K", "6-K", "8-K/A", "6-K/A"):
                        continue
                    fdate = rec["filingDate"][i]
                    if fdate < since.isoformat():
                        break
                    nfil += 1
                    acc = rec["accessionNumber"][i]
                    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
                    idx = get(base + "/index.json")
                    time.sleep(0.15)
                    names = []
                    if idx:
                        names = [x["name"] for x in json.loads(idx).get("directory", {}).get("item", [])
                                 if re.search(r"\.htm[l]?$", x["name"], re.I)]
                    docs = sorted(names, key=lambda n: (0 if re.search(r"ex-?99|ex99|press", n, re.I) else 1, n))[:4]
                    for dn in docs:
                        body = get(f"{base}/{dn}")
                        time.sleep(0.15)
                        if not body:
                            continue
                        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
                        for r, t, s in leads_in(text, rs):
                            key = f"{r['id']}|{acc}"
                            if key not in ack and key not in {k for *_x, k in leads}:
                                leads.append((r, t, s, fdate, f"{base}/{dn}", form, key))
        elif not reason:
            reason = "no SEC CIK found for this ticker in sec_company_tickers.json"
        chans.append("fda_feeds")
        coverage[tk] = {"company": rs[0].get("company"), "goals": sorted(str(r["d"])[:10] for r in rs),
                        "channels": chans, "cik": cik,
                        **({"reason_no_own_channel": reason} if not ({"sponsor_feed", "edgar_8k"} & set(chans)) else {})}
    io.open(COVER, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"as_of": today.isoformat(), "horizon_days": a.horizon, "sponsors": coverage}, indent=1, ensure_ascii=False) + "\n")
    try:
        health = json.load(io.open(HEALTH, encoding="utf-8")) if os.path.exists(HEALTH) else {}
        ent = health.setdefault("edgar_8k", {})
        ent.update({"last_attempt": today.isoformat(), "sponsors_read": read_ok, "blind": blind, "filings_read": nfil})
        if read_ok:
            ent["last_ok"] = today.isoformat()
        io.open(HEALTH, "w", encoding="utf-8", newline="\n").write(json.dumps(health, indent=1, sort_keys=True) + "\n")
    except Exception:
        pass
    own = sum(1 for c in coverage.values() if {"sponsor_feed", "edgar_8k"} & set(c["channels"]))
    print(f"EDGAR 8-K poll: {len(by)} sponsor(s) with an armed goal in {a.horizon} days; {read_ok} read on EDGAR, "
          f"{nfil} 8-K/6-K filing(s) since {since}; {own}/{len(by)} with an own channel"
          + (f"; BLIND: {', '.join(blind)}" if blind else "")
          + "".join(f"\n   no own channel: {tk} -- {c['reason_no_own_channel']}" for tk, c in coverage.items()
                    if c.get("reason_no_own_channel")))
    if leads:
        print(f"EDGAR 8-K WATCH: {len(leads)} unreviewed lead(s) on armed events:")
        for r, t, s, fdate, url, form, key in leads:
            print(f"   {r['t']} {str(r.get('name'))[:50]} (goal {r['d']}): {form} filed {fdate} [{t}] \"{s[:200]}\" {url}")
            print(f"      ack key: {key}")
            W._emit_lead("edgar_8k", r["id"], key, f"{form} {fdate} [{t}] {s[:200]} {url}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
