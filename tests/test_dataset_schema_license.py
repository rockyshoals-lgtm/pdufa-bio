# -*- coding: utf-8 -*-
"""CI guard: every schema.org Dataset / DataCatalog object on an indexable page carries `license`,
and no page carries two Dataset objects.

Google Search Console, 2026-09-20: "Missing field 'license'" on the Dataset enhancement report.
Two of the site's nine Dataset objects lacked it -- /developers (the API dataset; the page itself
says "Attribution + link-back required", i.e. CC BY 4.0) and a hand-written duplicate on
/research/pdufa-stock-run-up-by-market-cap that also carried a stale name ("2024-2026", 763
decisions) beside the licensed one. The duplicate was removed; /developers now declares CC BY 4.0
from build_hub_faq.py like every research dataset.

    python tests/test_dataset_schema_license.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_")


def walk(o, out):
    if isinstance(o, dict):
        t = o.get("@type")
        types = t if isinstance(t, list) else [t]
        if "Dataset" in types or "DataCatalog" in types:
            out.append(o)
        for v in o.values():
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)


def main():
    fails, n_pages, n_ds = [], 0, 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*noindex', doc[:4000]) or "Dataset" not in doc:
            continue
        rel = "/" + os.path.relpath(os.path.dirname(f), SITE).replace("\\", "/")
        nodes = []
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            try:
                walk(json.loads(m.group(1)), nodes)
            except Exception:
                fails.append(f"{rel}: JSON-LD block does not parse")
        top_ds = [n for n in nodes if (n.get("@type") == "Dataset")]
        if not nodes:
            continue
        n_pages += 1
        n_ds += len(nodes)
        for n in nodes:
            if not n.get("license"):
                fails.append(f"{rel}: {n.get('@type')} '{str(n.get('name'))[:50]}' has no license")
        # one top-level Dataset per page (nested datasets inside a DataCatalog are fine)
        catalog_children = set()
        for n in nodes:
            if n.get("@type") == "DataCatalog":
                for c in n.get("dataset") or []:
                    catalog_children.add(id(c))
        tops = [n for n in top_ds if id(n) not in catalog_children]
        if len(tops) > 1:
            fails.append(f"{rel}: {len(tops)} Dataset objects on one page: {[str(t.get('name'))[:40] for t in tops]}")
    if fails:
        print(f"FAIL: {len(fails)} Dataset schema issue(s):")
        for x in fails[:20]:
            print("   " + x)
        return 1
    print(f"OK -- {n_ds} Dataset/DataCatalog object(s) on {n_pages} page(s), every one licensed, one per page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
