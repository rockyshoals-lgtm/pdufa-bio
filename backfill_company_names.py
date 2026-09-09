# -*- coding: utf-8 -*-
"""One canonical company name per ticker, on every row, from sources we already hold.

Audit 2026-09-09b items 4 and 6. 265 of 456 public rows (58%) served a blank `company`,
including a live forward catalyst: CORT, relacorilant (GRACE resubmission), PDUFA
2026-12-17, day precision, Upcoming, no sponsor. And 15 tickers carried several spellings of
one company, one of them an exchange listing description rather than a name ("GSK plc
American Depositary Shares (Each representing two)").

Sources, in order, all of them ours or authoritative. Nothing is invented:
  1. the same ticker's other rows in this dataset (majority vote; ties to the longer name),
     which is the same resolution the ticker hubs use;
  2. SEC's own company/ticker file (`sec_company_tickers.json`), title-cased.
A ticker with neither is left blank and reported, because a blank field is honest and a
guessed sponsor is not.

ADR boilerplate never wins: "American Depositary Shares (Each representing two)" is a
listing description. Where the SEC title is the only source and carries it, the boilerplate
is stripped and the remainder used.
"""
import collections
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
SEC = os.path.join(HERE, "sec_company_tickers.json")
ADR = re.compile(r"\s*[-,(]?\s*(?:American Depositary|ADS|ADR|Each representing|"
                 r"Ordinary Shares|Common Stock|Sponsored ADR)\b.*$", re.I)


def sec_names():
    """{TICKER: title} from SEC's own file, whatever shape it ships in."""
    try:
        raw = json.load(io.open(SEC, encoding="utf-8"))
    except Exception:
        return {}
    recs = raw.values() if isinstance(raw, dict) else raw
    out = {}
    for r in recs:
        if not isinstance(r, dict):
            continue
        tk = str(r.get("ticker") or r.get("Ticker") or "").upper().strip()
        nm = str(r.get("title") or r.get("name") or r.get("Title") or "").strip()
        if tk and nm:
            out.setdefault(tk, nm)
    return out


def tidy(name):
    name = ADR.sub("", str(name or "")).strip(" ,-")
    if name.isupper() and len(name) > 4:          # "MANNKIND CORP" -> "MannKind Corp"
        name = name.title()
    return re.sub(r"\s{2,}", " ", name).strip()


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])

    votes = collections.defaultdict(collections.Counter)
    for r in rows:
        tk = str(r.get("t") or "").upper()
        nm = tidy(r.get("company"))
        if tk and nm and not ADR.search(str(r.get("company") or "")):
            votes[tk][nm] += 1
    canon = {tk: max(c.items(), key=lambda kv: (kv[1], len(kv[0])))[0]
             for tk, c in votes.items()}

    sec = sec_names()
    filled = normalised = 0
    still_blank = set()
    for r in rows:
        tk = str(r.get("t") or "").upper()
        cur = str(r.get("company") or "").strip()
        want = canon.get(tk) or tidy(sec.get(tk, ""))
        if not want:
            if not cur:
                still_blank.add(tk)
            continue
        if not cur:
            r["company"] = want
            filled += 1
        elif tidy(cur) != cur or cur != want:
            r["company"] = want
            normalised += 1

    out = src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:]
    if out != src:
        io.open(DATASET, "w", encoding="utf-8").write(out)
    print(f"company names: {filled} blank filled, {normalised} normalised to one spelling; "
          f"{len(still_blank)} ticker(s) still blank (no company anywhere, not invented)")
    if still_blank:
        print("  still blank: " + ", ".join(sorted(still_blank)[:25])
              + (" ..." if len(still_blank) > 25 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
