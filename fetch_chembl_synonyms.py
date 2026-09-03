# -*- coding: utf-8 -*-
"""fetch_chembl_synonyms.py -- drug aliases from ChEMBL, for alternateName at scale.

Audit 2026-09-02c owned a correction: the alternateName recommendation assumed alias
data we do not hold (only 4% of records embed a code name; neither enrichment cache has
a synonym field). The honest route is data acquisition: ChEMBL's molecule endpoint
returns `molecule_synonyms` -- research codes, INNs, trade names -- which is exactly
what lets an AI engine resolve "RMC-6236" and "daraxonrasib" to the same page.

Discipline (verify-then-publish): a synonym is only accepted when the TOP search hit is
demonstrably the SAME molecule -- its pref_name equals our drug name, or our drug name
appears verbatim in its own synonym list. A fuzzy top hit for a different molecule would
publish wrong aliases under a drug's name, which is worse than none. Misses are cached
as empty so re-runs stay cheap; delete chembl_synonyms_cache.json to re-pull.

Reads drug names from the /drug page h1s (the same source add_drug_schema uses), writes
chembl_synonyms_cache.json. Run detached (network, ~5 min for 554 names).
"""
import glob
import html as _html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "chembl_synonyms_cache.json")
API = "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json"


def page_names():
    out = {}
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        h = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        if not h:
            continue
        h1 = _html.unescape(re.sub(r"<[^>]+>", "", h.group(1))).strip()
        m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", h1)
        out[slug] = (m.group(1) if m else h1).strip()
    return out


def fetch(name):
    url = f"{API}?q={urllib.parse.quote(name)}&limit=3"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            mols = json.load(r).get("molecules", [])
    except Exception:
        return None                                  # transient -- do not cache a miss
    lo = name.lower()
    for mol in mols[:3]:
        pref = str(mol.get("pref_name") or "").strip()
        syns = [str(s.get("molecule_synonym") or s.get("synonyms") or "").strip()
                for s in (mol.get("molecule_synonyms") or [])]
        syns = [s for s in syns if s]
        same = (pref.lower() == lo) or any(s.lower() == lo for s in syns)
        if not same:
            continue                                 # top hit is a DIFFERENT molecule
        keep = {}                                    # lower -> preferred casing
        for s in syns:
            k = s.lower()
            if k == lo or not (2 < len(s) <= 40):
                continue
            # prefer the more-uppercase variant on collision: "PTG-300" over "Ptg-300"
            if k not in keep or sum(c.isupper() for c in s) > \
                    sum(c.isupper() for c in keep[k]):
                keep[k] = s
        return list(keep.values())[:8]
    return []                                        # searched, no same-molecule hit


def main():
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(io.open(CACHE, encoding="utf-8"))
    names = page_names()
    todo = {slug: n for slug, n in names.items() if slug not in cache}
    print(f"{len(names)} drug pages; {len(todo)} to fetch ({len(cache)} cached)")
    hits = 0
    for i, (slug, name) in enumerate(sorted(todo.items())):
        syns = fetch(name)
        if syns is None:
            continue                                 # retry next run
        cache[slug] = {"name": name, "synonyms": syns}
        if syns:
            hits += 1
        if (i + 1) % 50 == 0:
            json.dump(cache, io.open(CACHE, "w", encoding="utf-8"), indent=1)
            print(f"  {i + 1}/{len(todo)} ({hits} with synonyms so far)")
        time.sleep(0.35)
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"), indent=1)
    total_hits = sum(1 for v in cache.values() if v.get("synonyms"))
    print(f"done: {len(cache)} cached, {total_hits} drugs with verified same-molecule "
          f"synonyms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
