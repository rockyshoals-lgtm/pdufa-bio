# -*- coding: utf-8 -*-
"""Every indexable /drug page must carry valid Drug JSON-LD.

SEO audit 2026-09-02b, third audit asking: AI grounding queries plateaued at 18 and
breadth comes from entity markup -- "FAQPage says there's a Q&A here; Drug says this
page IS camizestrant." add_drug_schema.py emits it daily from the page's own facts;
this guard asserts the RESULT so the markup can't silently vanish from the template
(the frozen-family lesson): present on every indexable drug page, parses as JSON,
@type Drug, non-empty name.
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
        if ld.get("@type") != "Drug" or not str(ld.get("name", "")).strip():
            bad.append(f"/drug/{slug}: JSON-LD missing @type Drug or name")
    # Floor calibrated to CI, where a thin-page pass noindexes ~229 of the 554 drug
    # pages (local working trees see more indexable pages than a fresh CI build).
    assert checked > 250, f"only {checked} drug pages checked -- glob broken?"
    assert not bad, ("drug pages without valid Drug schema -- run add_drug_schema.py:"
                     "\n  " + "\n  ".join(bad[:10])
                     + (f"\n  ... and {len(bad) - 10} more" if len(bad) > 10 else ""))


if __name__ == "__main__":
    test_drug_pages_carry_drug_schema()
    print("OK")
