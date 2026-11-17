# -*- coding: utf-8 -*-
"""Every indexable /drug page must carry valid Drug JSON-LD.

SEO audit 2026-09-02b, third audit asking: AI grounding queries plateaued at 18 and
breadth comes from entity markup -- "FAQPage says there's a Q&A here; Drug says this
page IS camizestrant." add_drug_schema.py emits it daily from the page's own facts;
this guard asserts the RESULT so the markup can't silently vanish from the template
(the frozen-family lesson): present on every indexable drug page, parses as JSON,
non-empty name.

2026-11-17 (currency audit): the type is MedicalEntity with additionalType schema.org/Drug, not Drug.
schema.org's Drug is a Product subtype, and Search Console's Product snippets report flagged the drug
pages as invalid products (no offers / review / aggregateRating). A second test fails on ANY
Product-family @type (Product, Drug, Offer, AggregateOffer, Review, AggregateRating) in any JSON-LD on
any page, so the markup cannot drift back. PLANT_PRODUCT=1 must FAIL.
"""
import glob
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def test_drug_pages_carry_drug_schema():
    bad, checked = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "noindex" in doc[:2000]:
            continue
        checked += 1
        m = re.search(r"<!--DRUGLD:BEGIN--><script[^>]*>(.*?)</script>", doc, re.S)
        if not m:
            bad.append(f"/drug/{slug}: no Drug JSON-LD block")
            continue
        try:
            ld = json.loads(m.group(1))
        except Exception as e:
            bad.append(f"/drug/{slug}: Drug JSON-LD does not parse ({e})")
            continue
        if (ld.get("@type") != "MedicalEntity" or ld.get("additionalType") != "https://schema.org/Drug"
                or not str(ld.get("name", "")).strip()):
            bad.append(f"/drug/{slug}: JSON-LD is not MedicalEntity + additionalType Drug, or has no name")
    # Floor calibrated to CI, where a thin-page pass noindexes ~229 of the 554 drug
    # pages (local working trees see more indexable pages than a fresh CI build).
    assert checked > 250, f"only {checked} drug pages checked -- glob broken?"
    assert not bad, ("drug pages without valid Drug schema -- run add_drug_schema.py:"
                     "\n  " + "\n  ".join(bad[:10])
                     + (f"\n  ... and {len(bad) - 10} more" if len(bad) > 10 else ""))


PRODUCT_TYPES = {"Product", "Drug", "Offer", "AggregateOffer", "Review", "AggregateRating", "IndividualProduct",
                 "ProductModel", "ProductGroup"}


def _types(node, out):
    if isinstance(node, dict):
        t = node.get("@type")
        for x in (t if isinstance(t, list) else [t]):
            if isinstance(x, str):
                out.add(x)
        for v in node.values():
            _types(v, out)
    elif isinstance(node, list):
        for v in node:
            _types(v, out)


def test_no_product_family_markup():
    bad, n = [], 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        if re.search(r"[\\/]_[a-z]*bak", p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if os.environ.get("PLANT_PRODUCT") and n == 0:
            doc += '<script type="application/ld+json">{"@type":"Product","name":"x"}</script>'
        n += 1
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            try:
                ld = json.loads(m.group(1))
            except Exception:
                continue
            found = set()
            _types(ld, found)
            hit = found & PRODUCT_TYPES
            if hit:
                bad.append(f"/{os.path.relpath(os.path.dirname(p), SITE)}: {sorted(hit)}")
                break
    assert not bad, ("Product-family JSON-LD (Search Console validates it as a product listing):\n  "
                     + "\n  ".join(bad[:10]) + (f"\n  ... and {len(bad) - 10} more" if len(bad) > 10 else ""))


if __name__ == "__main__":
    test_drug_pages_carry_drug_schema()
    test_no_product_family_markup()
    print("OK")
