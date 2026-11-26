#!/usr/bin/env python3
"""fetch_fda_devices.py -- FDA medical device decisions from the FDA's own databases (openFDA), cache only.

Writes _fda_devices.json. No page reads it until the device-decisions pages land (stage 2).

What it collects, every row from an FDA record:
  * PMA originals   -- /device/pma.json, records with no supplement number (a new device's premarket approval).
  * Panel-track PMA supplements -- /device/pma.json, supplement_type "Panel Track" (a significant change
    to an approved device that needs clinical data; these are the supplements that move device stocks).
  * De Novo grants  -- /device/510k.json, k_number DEN* (openFDA files De Novo requests with the 510(k)s;
    there is no separate De Novo endpoint).

Every row keeps the FDA's own fields as published (decision code, dates, applicant, names, product code,
advisory committee) and the link to the FDA database record. Nothing is inferred or scored.

Ticker: an applicant gets a ticker ONLY when
  (a) its normalized name equals exactly one SEC company name in sec_company_tickers.json, or
  (b) device_applicant_aliases.json (curated, each entry with a source note) maps that exact applicant.
Anything else stays without a ticker. A subsidiary name is never guessed onto a parent.

Usage: python fetch_fda_devices.py [--since 2010] [--strict]
Without network it keeps the existing cache and exits 0 (unless --strict).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_fda_devices.json")
SEC = os.path.join(HERE, "sec_company_tickers.json")
ALIASES = os.path.join(HERE, "device_applicant_aliases.json")
UA = {"User-Agent": "pdufa.bio-research-script/1.0"}
API = "https://api.fda.gov/device"

PMA_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={id}"
DEN_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm?id={id}"

SUFFIXES = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LLC", "L L C", "LTD", "LIMITED", "PLC",
    "LP", "L P", "SA", "S A", "AG", "NV", "N V", "BV", "B V", "GMBH", "SAS", "SPA", "AB", "AS", "OY", "KK",
    "HOLDINGS", "HOLDING", "THE", "DE", "DEL", "CORP/DE", "/DE/", "/DE",
}


def norm(name):
    """Upper-case, punctuation to spaces, trailing legal suffixes dropped. 'Inari Medical, Inc.' -> 'INARI MEDICAL'."""
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"/[A-Z]{2}/?$", " ", s)          # SEC state tags: 'PENUMBRA INC /DE/'
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    words = s.split()
    while words and words[-1] in SUFFIXES:
        words.pop()
    while words and words[0] == "THE":
        words.pop(0)
    return " ".join(words)


def sec_index(path=SEC):
    """normalized SEC name -> ticker, keeping only names that map to ONE company (CIK)."""
    by = {}
    try:
        d = json.load(open(path))
    except Exception:  # noqa: BLE001
        return {}
    rows = d.values() if isinstance(d, dict) else d
    for r in rows:
        n = norm(r.get("title"))
        if not n:
            continue
        by.setdefault(n, {})
        by[n].setdefault(r.get("cik_str"), r.get("ticker"))
    return {n: list(v.values())[0] for n, v in by.items() if len(v) == 1}


def load_aliases(path=ALIASES):
    """{"APPLICANT AS FDA PRINTS IT": {"ticker": "...", "source": "..."}}; entries without a source are ignored."""
    try:
        d = json.load(open(path))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for k, v in (d.get("aliases") or {}).items():
        if isinstance(v, dict) and v.get("ticker") and v.get("source"):
            out[norm(k)] = v
    return out


def ticker_for(applicant, sec, aliases):
    n = norm(applicant)
    if not n:
        return None, None
    if n in aliases:
        return aliases[n]["ticker"], "alias"
    if n in sec:
        return sec[n], "sec_name"
    return None, None


def iso(d):
    """openFDA prints dates as YYYY-MM-DD (PMA) or YYYYMMDD in some records."""
    d = (d or "").strip()
    if re.fullmatch(r"\d{8}", d):
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return d
    return None


def is_panel_track(t):
    return "PANEL TRACK" in re.sub(r"[^A-Z ]", " ", (t or "").upper())


def pma_row(r, sec, aliases):
    num = (r.get("pma_number") or "").strip().upper()
    sup = (r.get("supplement_number") or "").strip().upper()
    if not re.fullmatch(r"[PHN]\d{6}", num):
        return None
    if sup and not is_panel_track(r.get("supplement_type")):
        return None   # 180-day, real-time, 30-day notices etc. are not collected
    rid = num + (f"S{sup.lstrip('S')}" if sup else "")
    tk, how = ticker_for(r.get("applicant"), sec, aliases)
    return {
        "id": rid,
        "pathway": "PMA" if not sup else "PMA panel-track supplement",
        "pma_number": num,
        "supplement_number": sup or None,
        "supplement_type": r.get("supplement_type") or None,
        "supplement_reason": r.get("supplement_reason") or None,
        "applicant": (r.get("applicant") or "").strip(),
        "trade_name": (r.get("trade_name") or "").strip(),
        "generic_name": (r.get("generic_name") or "").strip(),
        "product_code": (r.get("product_code") or "").strip(),
        "advisory_committee": (r.get("advisory_committee_description") or r.get("advisory_committee") or "").strip(),
        "decision_code": (r.get("decision_code") or "").strip(),
        "date_received": iso(r.get("date_received")),
        "decision_date": iso(r.get("decision_date")),
        "expedited_review": (r.get("expedited_review_flag") or "").strip() == "Y",
        "ao_statement": (r.get("ao_statement") or "").strip() or None,
        "fda_url": PMA_URL.format(id=rid),
        "ticker": tk,
        "ticker_match": how,
    }


def den_row(r, sec, aliases):
    num = (r.get("k_number") or "").strip().upper()
    if not re.fullmatch(r"DEN\d{6}", num):
        return None
    tk, how = ticker_for(r.get("applicant"), sec, aliases)
    return {
        "id": num,
        "pathway": "De Novo",
        "applicant": (r.get("applicant") or "").strip(),
        "trade_name": (r.get("device_name") or "").strip(),
        "generic_name": "",
        "product_code": (r.get("product_code") or "").strip(),
        "advisory_committee": (r.get("advisory_committee_description") or r.get("advisory_committee") or "").strip(),
        "decision_code": (r.get("decision_code") or "").strip(),
        "decision_description": (r.get("decision_description") or "").strip() or None,
        "date_received": iso(r.get("date_received")),
        "decision_date": iso(r.get("decision_date")),
        "fda_url": DEN_URL.format(id=num),
        "ticker": tk,
        "ticker_match": how,
    }


def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"results": [], "meta": {"results": {"total": 0}}}
            time.sleep(2 + 3 * i)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 3 * i)
    return None


def fetch_all(endpoint, search, page=1000, cap=26000):
    """Every record for one search, paged. Returns None if any page failed (so a partial pull never replaces the cache)."""
    out, skip = [], 0
    while skip < cap:
        q = urllib.parse.urlencode({"search": search, "limit": page, "skip": skip})
        j = get(f"{API}/{endpoint}.json?{q}")
        if j is None:
            return None
        res = j.get("results") or []
        out.extend(res)
        total = ((j.get("meta") or {}).get("results") or {}).get("total") or 0
        skip += page
        if not res or skip >= total:
            break
        time.sleep(0.3)
    return out


def year_slices(since):
    """openFDA caps skip at 25,000; slicing by decision year keeps every search well under it."""
    now = datetime.now(timezone.utc).year
    for y in range(since, now + 1):
        yield y, f"[{y}-01-01+TO+{y}-12-31]"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=2010)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)

    sec, aliases = sec_index(), load_aliases()
    rows, failed = {}, []
    for y, rng in year_slices(a.since):
        # PMA: every record decided that year, filtered here (originals = no supplement number; panel-track
        # by the FDA's supplement_type). Filtering client-side avoids depending on _missing_ semantics.
        for label, ep, search, fn in (
            ("PMA", "pma", f"decision_date:{rng}", pma_row),
            ("De Novo", "510k", f"decision_date:{rng}+AND+k_number:DEN*", den_row),
        ):
            # urlencode would escape the '+' that openFDA reads as a space/AND, so pass it as spaces
            res = fetch_all(ep, search.replace("+", " "))
            if res is None:
                failed.append(f"{label} {y}")
                continue
            for r in res:
                row = fn(r, sec, aliases)
                if row and row["decision_date"]:
                    rows[row["id"]] = row

    if failed:
        print(f"fetch_fda_devices: {len(failed)} slices failed ({', '.join(failed[:6])}...); cache NOT replaced")
        return 1 if a.strict else 0
    if not rows:
        print("fetch_fda_devices: openFDA returned nothing; cache NOT replaced")
        return 1 if a.strict else 0

    items = sorted(rows.values(), key=lambda r: (r["decision_date"], r["id"]), reverse=True)
    out = {
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "openFDA device endpoints (pma.json, 510k.json), FDA CDRH databases",
        "since": a.since,
        "count": len(items),
        "rows": items,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(tmp, OUT)
    by = {}
    for r in items:
        by[r["pathway"]] = by.get(r["pathway"], 0) + 1
    print(f"fetch_fda_devices: {len(items)} rows {by}; with ticker {sum(1 for r in items if r['ticker'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
