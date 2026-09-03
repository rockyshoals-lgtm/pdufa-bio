# -*- coding: utf-8 -*-
"""fetch_fda_brands.py -- brand names from FDA's own feed, for alternateName.

Final audit 2026-09-02 §4: "we hold MIMRYLO's brand name and throw it away." The
watcher's own openFDA payload carries openfda.brand_name next to the approval date it
acts on -- zero new data sources, zero new API budget. But the watcher only scans
UPCOMING events, and a brand materializes exactly when an event stops being upcoming.
So this companion pass sweeps PDUFA events decided in the last 120 days, asks Drugs@FDA
for each drug, and records the brand under the drug's page slug. add_drug_schema merges
the result into alternateName -- "what is MIMRYLO" becomes a query our rusfertide page
can be cited for.

Same same-molecule discipline as the synonyms fetcher: the hit must carry our drug name
in its own generic/active-ingredient fields, or the brand is not recorded. Cache-first;
a normal day fetches only newly decided drugs.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "_fda_brand_names.json")
API = "https://api.fda.gov/drug/drugsfda.json"


def lead_generic(name):
    """First generic-looking token of an event name: 'Garetosmab - (OPTIMA)' ->
    'garetosmab'; 'Bictegravir and Lenacapavir' -> 'bictegravir'."""
    m = re.search(r"[A-Za-z][A-Za-z0-9]{4,}", str(name or ""))
    t = m.group(0).lower() if m else ""
    # ambiguous common substances match half the OTC universe ("estrogen" returned
    # "Equate Hair Regrowth Treatment") -- never query them
    return "" if t in {"estrogen", "insulin", "minoxidil", "aspirin", "testosterone",
                       "progesterone", "caffeine", "nicotine"} else t


def query(term):
    t = urllib.parse.quote(f'"{term}"')
    q = (f"products.active_ingredients.name:{t}+OR+openfda.generic_name:{t}")
    try:
        with urllib.request.urlopen(f"{API}?search={q}&limit=3", timeout=20) as r:
            return json.load(r).get("results", [])
    except Exception:
        return None


def main():
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(io.open(CACHE, encoding="utf-8"))

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    floor = (dt.date.today() - dt.timedelta(days=120)).isoformat()
    recent = [r for r in rows if r.get("type") == "PDUFA"
              and str(r.get("st", "")).lower() == "decided"
              and str(r.get("dcd", "")) >= floor and r.get("oc") == "Approved"]

    fetched = 0
    for r in recent:
        gen = lead_generic(r.get("name"))
        if not gen or gen in cache:
            continue
        res = query(gen)
        if res is None:
            continue                             # transient; retry tomorrow
        brands = []
        for mol in res:
            of = mol.get("openfda") or {}
            gens = [g.lower() for g in (of.get("generic_name") or [])]
            actives = [str(a.get("name", "")).lower()
                       for p in (mol.get("products") or [])
                       for a in (p.get("active_ingredients") or [])]
            if not any(gen in g for g in gens + actives):
                continue                         # different molecule -- do not record
            # brands live in BOTH openfda.brand_name and products[].brand_name; fresh
            # approvals (MIMRYLO) often have only the latter before openfda enrichment
            cand = list(of.get("brand_name") or []) + [
                str(pr.get("brand_name") or "") for pr in (mol.get("products") or [])]
            for b in cand:
                b = str(b).strip()
                # sanity: real FDA brands are 1-2 words of letters ("Biktarvy",
                # "Pasatru") -- "Equate Hair Regrowth Treatment" is monograph noise
                if (b and b.lower() != gen and len(b.split()) <= 2
                        and re.fullmatch(r"[A-Za-z][A-Za-z .\-]{2,25}", b)
                        and b.title() not in [x.title() for x in brands]):
                    brands.append(b.title() if b.isupper() else b)
        cache[gen] = {"brands": brands[:4], "ticker": r.get("t"),
                      "decided": r.get("dcd")}
        fetched += 1
        if brands:
            print(f"  {gen} -> {brands}")
        time.sleep(0.3)
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"), indent=1)
    n_brands = sum(1 for v in cache.values() if v.get("brands"))
    print(f"FDA brands: {fetched} drug(s) fetched this run; {n_brands} of "
          f"{len(cache)} cached drugs have a recorded brand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
