# -*- coding: utf-8 -*-
"""CI guard: every /fda-application page says only what its sources say.

The per-application pages (build_fda_application_pages.py) join a drug's brand, ingredient, code
names, FDA applicant, owner and ticker. A wrong join is a false claim with a URL, so:

  1. Curation: every mapping in _fda_applications.json passes fda_applications_lib.validate with no
     errors (primary-source URL, document and read dates, a verbatim quote that contains the mapped
     value; brand and ingredient equal to the FDA's Orange Book record). Fail-closed drops caused by
     the FDA record moving (applicant changed, application gone) are printed, not failed.
  2. Disk: every page on disk belongs to a validated entry; every code name, owner ticker and history
     row it shows (data-map cells) is one the validated entry holds; the applicant it prints is the
     Orange Book's current applicant; its JSON-LD is MedicalEntity (never a Product-family type) and
     carries the application number.

PLANT_UNSOURCED_MAPPING=1 adds a code name sourced to an aggregator with a quote that does not name it.
This guard must FAIL with it.

    python tests/test_fda_application_pages.py
"""
import copy
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fda_applications_lib as L  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "fda-application")
PRODUCT_TYPES = {"Product", "Drug", "Offer", "AggregateOffer", "Review", "AggregateRating"}


def entries():
    data = L.load_data()
    if os.environ.get("PLANT_UNSOURCED_MAPPING") == "1":
        data = copy.deepcopy(data)
        e = data["applications"][0]
        e.setdefault("code_names", []).append({"name": "XYZ-999", "src": {
            "url": "https://stocktitan.net/news/x.html", "publisher": "StockTitan", "doc": "article",
            "doc_date": "2026-01-01", "read": "2026-11-17", "quote": "a quote that names nothing at all"}})
    ob = L.load_orange_book()
    doms = data.get("sponsor_domains") or {}
    return [L.validate(e, ob, doms) for e in data.get("applications") or []]


def main():
    fails, notes = [], []
    results = entries()
    clean_by_slug = {}
    for clean, errs, nts in results:
        fails += [f"curation: {x}" for x in errs]
        notes += nts
        if clean is not None:
            clean_by_slug[clean["slug"]] = clean

    pages = sorted(glob.glob(os.path.join(OUT, "*", "index.html")))
    for p in pages:
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        e = clean_by_slug.get(slug)
        if e is None:
            fails.append(f"/fda-application/{slug}: on disk but not a validated entry")
            continue
        codes_ok = {c["name"] for c in e["code_names"]}
        owner_ok = {e["owner"]["ticker"]} if e["owner"] else set()
        hist_ok = {h.get("ticker") or h["company"] for h in e["history"]}
        for kind, val in re.findall(r'data-map="([a-z_]+)" data-value="([^"]*)"', doc):
            val = html.unescape(val)
            ok = {"code_name": codes_ok, "owner": owner_ok, "history": hist_ok}.get(kind)
            if ok is not None and val not in ok:
                fails.append(f"/fda-application/{slug}: shows {kind} {val!r} that no validated source backs")
        m = re.search(r'data-map="applicant">([^<]*)<', doc)
        want = "; ".join(e["fda"]["applicants"])
        if not m or html.unescape(m.group(1)).strip() != want:
            fails.append(f"/fda-application/{slug}: applicant {m.group(1) if m else None!r} is not the "
                         f"Orange Book's {want!r}")
        lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
        ent = None
        for raw in lds:
            try:
                j = json.loads(raw)
            except Exception:
                fails.append(f"/fda-application/{slug}: JSON-LD does not parse")
                continue
            for node in (j if isinstance(j, list) else [j]):
                t = node.get("@type")
                for tt in (t if isinstance(t, list) else [t]):
                    if tt in PRODUCT_TYPES:
                        fails.append(f"/fda-application/{slug}: Product-family JSON-LD type {tt}")
                if t == "MedicalEntity":
                    ent = node
        if not ent or (ent.get("identifier") or {}).get("value") != e["appl"]:
            fails.append(f"/fda-application/{slug}: MedicalEntity JSON-LD missing or without {e['appl']}")
    for slug in clean_by_slug:
        if not os.path.exists(os.path.join(OUT, slug, "index.html")):
            fails.append(f"/fda-application/{slug}: validated entry but no page on disk (builder not run?)")

    for n in notes:
        print("NOTE (withheld, fail-closed): " + n)
    if fails:
        print(f"FAIL: {len(fails)} problem(s) on the FDA application pages:")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print(f"OK -- {len(pages)} FDA application page(s); every mapping on them is backed by a primary "
          f"source quote, and FDA facts match the Orange Book.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
