# -*- coding: utf-8 -*-
"""merge_crawl_to_slate.py -- publish NEW crawler catalysts to the site, safely by construction.

THE PROBLEM THIS SOLVES
The crawler is trustworthy for ticker+date+source but conservative on drug names: ~58% of forward
PDUFAs come back with a blank drug (big-pharma multi-asset sponsors it won't guess). A naive merge
would overwrite the hand-curated names already on the site (CYTK aficamten, COGT bezuclastinib, ...)
with those blanks, and a weekday crawl (no --discover) would "drop" off-list names it simply didn't
look for. Both are the exact failure modes that produced phantom/blanked catalysts before.

THE RULE: ADDITIVE + CURATION-PRESERVING.
  * It ONLY ADDS catalysts the site doesn't already have (keyed on ticker+date).
  * It NEVER modifies an existing slate row -- so no curated drug name can be blanked or changed.
  * It NEVER deletes -- so a weekday crawl that lacks an off-list name can't remove it. (Resolved
    PDUFAs leave via the decided-sweep, not here.)
  * Dedupe: multiple crawl rows for one ticker+date collapse to the best (non-blank drug, highest
    confidence).
  * Filters: only type=PDUFA, date>=today, confidence>=MIN_CONF, drug name not a filing artefact.
    A blank drug is still added (the DATE is the value); it's flagged for later fill, never guessed.

Writes BOTH surfaces in agreement: api/data.js (SLATE) and api/v1/dataset.mjs. New rows carry
price/mcap null -> polygon_enrich fills them and stamps a fresh timestamp on the next run.

Dry-run by DEFAULT. Prints exactly what it would add. Pass --write to actually publish.

    python merge_crawl_to_slate.py                 # dry run: show additions
    python merge_crawl_to_slate.py --write         # apply to both surfaces (backs up first)
    python merge_crawl_to_slate.py --min-conf 0.9  # stricter confidence gate
"""
import argparse, csv, json, os, re, sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATA_JS = os.path.join(SITE, "api", "data.js")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
CRAWL = os.path.join(HERE, "catalysts_out", "catalysts_public.csv")
TODAY = dt.date.today()
NOW_ISO = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# same filing-artefact test as the crawler's _is_junk_drug (single source of truth would be nicer,
# but keeping the merge self-contained avoids importing the heavy crawler module)
_JUNK = re.compile(r"^\s*(ex[\s\-]?\d|exhibit\b|form\s|item\s|8-?k\b|10-?[kq]\b|424b|\d+(\.\d+)?\s*$)", re.I)
def is_junk(name):
    n = str(name or "").strip()
    return bool(n) and bool(_JUNK.match(n))


def load_slate_text():
    txt = open(DATA_JS, encoding="utf-8").read()
    i = txt.find("const SLATE=")
    obj, end = json.JSONDecoder().raw_decode(txt[i + len("const SLATE="):])
    span = (i + len("const SLATE="), i + len("const SLATE=") + end)
    return txt, obj, span


# Tickers that appear on filings as royalty holders or out-licensing partners, NOT the FDA
# applicant. The crawler can't tell "mentioned in an 8-K" from "is the sponsor"; these must never
# be published as catalysts. (RPRX = Royalty Pharma; ONC/ANAB = royalty stakes.)
ROYALTY = {"RPRX", "ONC", "ANAB"}
DECIDED_WINDOW_DAYS = 45   # a ticker decided this recently, re-appearing, is a duplicate until proven otherwise


def existing_keys(slate):
    keys = set()
    for c in slate["catalysts"]:
        if c.get("ticker") and c.get("date"):
            keys.add((c["ticker"].upper(), str(c["date"])[:10]))
    return keys


def decided_dates():
    """ticker -> [decided dates]. A catalyst decided a few days off its PDUFA goal date reappears
    with the goal date and would slip a naive ticker+date check (MNKD decided 07-24, goal 07-26)."""
    idx = {}
    if os.path.exists(DECISIONS):
        arch = open(DECISIONS, encoding="utf-8").read()
        for t, d in re.findall(r"/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})", arch):
            idx.setdefault(t.upper(), []).append(d)
    return idx


def risk_flags(c, have, decided, url_owners):
    """Reasons a candidate must NOT be auto-published. Empty list == safe to add."""
    f = []
    if (c["ticker"], c["date"]) in have:
        f.append("already-in-slate")
    if c["ticker"] in ROYALTY:
        f.append("royalty/partner-not-applicant")
    for dd in decided.get(c["ticker"], []):
        try:
            gap = abs((dt.date.fromisoformat(c["date"]) - dt.date.fromisoformat(dd)).days)
        except ValueError:
            continue
        if gap <= DECIDED_WINDOW_DAYS:
            f.append(f"ticker-decided-{dd}(±{gap}d)"); break
    if len(url_owners.get(c["url"], set())) > 1:
        f.append("fan-out(shared-source-across-tickers)")
    if not c["drug"]:
        f.append("blank-drug")
    return f


def read_crawl_candidates(min_conf):
    rows = list(csv.DictReader(open(CRAWL, encoding="utf-8")))
    best = {}
    for r in rows:
        if (r.get("catalyst_type") or "").strip().upper() != "PDUFA":
            continue
        tk = (r.get("ticker") or "").strip().upper()
        date = (r.get("catalyst_date") or "").strip()[:10]
        if not tk or not re.match(r"\d{4}-\d{2}-\d{2}", date):
            continue
        if date < TODAY.isoformat():
            continue
        try:
            conf = float(r.get("confidence") or 0)
        except ValueError:
            conf = 0
        if conf < min_conf:
            continue
        drug = "" if is_junk(r.get("drug")) else (r.get("drug") or "").strip()
        cand = {"ticker": tk, "date": date, "company": (r.get("company") or "").strip(),
                "drug": drug, "indication": (r.get("indication") or "").strip(),
                "dp": (r.get("date_precision") or "day").strip() or "day",
                "url": (r.get("source_url") or "").strip(), "conf": conf}
        k = (tk, date)
        # dedupe: prefer non-blank drug, then higher confidence
        cur = best.get(k)
        if cur is None or (bool(cand["drug"]) > bool(cur["drug"])) or \
           (bool(cand["drug"]) == bool(cur["drug"]) and cand["conf"] > cur["conf"]):
            best[k] = cand
    return best


def tmin(date):
    p = date.split("-")
    v = dt.date(int(p[0]), int(p[1]), int(p[2]))
    return (v - TODAY).days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply changes (default is dry run)")
    ap.add_argument("--min-conf", type=float, default=0.85)
    a = ap.parse_args()

    if not os.path.exists(CRAWL):
        sys.exit(f"crawl not found: {CRAWL} (run PDUFA_Crawler.bat first)")

    txt, slate, span = load_slate_text()
    have = existing_keys(slate)
    decided = decided_dates()
    cands = read_crawl_candidates(a.min_conf)

    # who owns each source_url -> fan-out detection (one filing, several tickers = co-development)
    url_owners = {}
    for c in cands.values():
        url_owners.setdefault(c["url"], set()).add(c["ticker"])

    fresh = [c for k, c in sorted(cands.items()) if k not in have]
    safe, review = [], []
    for c in fresh:
        flags = risk_flags(c, have, decided, url_owners)
        (safe if not flags else review).append((c, flags))

    print(f"crawl PDUFA candidates (forward, conf>={a.min_conf}): {len(cands)} | "
          f"already on site: {len(cands)-len(fresh)} | not-on-site: {len(fresh)} "
          f"-> AUTO-SAFE: {len(safe)}  |  NEEDS REVIEW: {len(review)}\n")

    if safe:
        print("AUTO-SAFE (passes every guard -- clean to add):")
        for c, _ in safe:
            print(f"  + {c['ticker']:6s} {c['date']}  {c['drug'][:34]:34s} conf={c['conf']}")
    if review:
        print("\nNEEDS REVIEW (held back -- verify against the primary source before publishing):")
        for c, flags in review:
            d = c["drug"] or "(blank)"
            print(f"  ? {c['ticker']:6s} {c['date']}  {d[:28]:28s} {', '.join(flags)}")
    if not safe:
        print("\nNothing is auto-safe to add this run.")
    additions = [c for c, _ in safe]

    if not a.write:
        print("\nDRY RUN -- nothing written. --write publishes ONLY the auto-safe set above.")
        return
    if not additions:
        return

    # ---- build new rows for both surfaces ----
    new_slate = [{"ticker": c["ticker"], "name": c["company"], "date": c["date"],
                  "t_minus": tmin(c["date"]), "drug": c["drug"],
                  "indication": c["indication"], "price": None, "mcap": None,
                  "cap": "", "adv": None, "cash_months": None} for c in additions]
    slate["catalysts"].extend(new_slate)
    slate["as_of"] = TODAY.isoformat()
    new_djs = txt[:span[0]] + json.dumps(slate, separators=(",", ":")) + txt[span[1]:]

    dtxt = open(DATASET, encoding="utf-8").read()
    s = dtxt.index("["); e = dtxt.rindex("]") + 1
    arr = json.loads(dtxt[s:e])
    for c in additions:
        arr.append({"id": f"pdufa_{c['ticker'].lower()}_{c['date']}", "t": c["ticker"],
                    "company": c["company"], "d": c["date"], "dp": c["dp"], "name": c["drug"],
                    "type": "PDUFA", "ta": "", "cap": "", "st": "Upcoming", "url": c["url"],
                    "ua": NOW_ISO, "_d": {"nct_id": None, "indication": c["indication"] or None,
                                          "market_cap_usd": None}})
    new_dtxt = dtxt[:s] + json.dumps(arr, separators=(",", ":")) + dtxt[e:]

    for path, new in ((DATA_JS, new_djs), (DATASET, new_dtxt)):
        open(path + ".bak_merge", "w", encoding="utf-8").write(open(path, encoding="utf-8").read())
        open(path, "w", encoding="utf-8").write(new)
    print(f"\nAdded {len(additions)} catalyst(s) to both surfaces (backups: *.bak_merge).")
    print("Next: run polygon_enrich.py to fill price/mcap, then the guard suite, then deploy.")


if __name__ == "__main__":
    main()
