# -*- coding: utf-8 -*-
"""CI guard: /crl/companies and every /crl/company/<slug> page count what the CRL corpus holds.

2026-11-22 (CRL red team). The company pages group the FDA's released Complete Response Letters by company. This
recounts from the corpus file, independently of the builder's grouping: the index's letter column plus "name not
given" must equal the distinct CRLs in the corpus (same date, application numbers and text counted once); every
company page's h1 count must equal its table rows; every index row with two or more letters must link its page and
every page must be linked from the index; no page or index may state a percentage.

    python tests/test_crl_company_counts.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from capture_crl_corpus import newest_corpus  # noqa: E402
CORPUS = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")


def text(doc):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc))))


def main():
    idx = os.path.join(SITE, "crl", "companies", "index.html")
    if not (os.path.exists(idx) and os.path.exists(CORPUS)):
        print("  SKIP /crl/companies or corpus missing"); return 0
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    keys = set()
    for r in recs:
        if str(r.get("letter_type") or "") != "COMPLETE RESPONSE" or not re.match(r"\d{2}/\d{2}/\d{4}", str(r.get("letter_date") or "")):
            continue
        keys.add((str(r.get("letter_date"))[:10], tuple(sorted(str(a).strip() for a in (r.get("application_number") or []))),
                  re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower()))
    doc = io.open(idx, encoding="utf-8", errors="replace").read()
    fails = []
    rows = re.findall(r"<tr><td>(.*?)</td><td>(\d+)</td>", doc)
    total = sum(int(n) for _, n in rows)
    if total != len(keys):
        fails.append(f"/crl/companies rows add to {total}, corpus holds {len(keys)} distinct CRLs")
    if not re.search(rf"holds {len(keys)} distinct Complete Response Letters", text(doc)):
        fails.append(f"/crl/companies intro does not say 'holds {len(keys)} distinct Complete Response Letters'")
    linked = set()
    for cell, n in rows:
        m = re.search(r'href="/crl/company/([^"]+)"', cell)
        if int(n) >= 2 and "name not given" not in cell and not m:
            fails.append(f"index row with {n} letters has no page link: {cell[:60]}")
        if m:
            linked.add(m.group(1))
    pages = {os.path.basename(os.path.dirname(p)): p for p in glob.glob(os.path.join(SITE, "crl", "company", "*", "index.html"))}
    if set(pages) != linked:
        fails.append(f"pages not linked from the index: {sorted(set(pages) - linked)[:5]}; links with no page: "
                     f"{sorted(linked - set(pages))[:5]}")
    for slug, p in pages.items():
        d = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<h1>.*?(\d+) Complete Response Letters</span></h1>", d)
        n_rows = len(re.findall(r'<tr><td class="dt">', d))
        if not m or int(m.group(1)) != n_rows:
            fails.append(f"/crl/company/{slug}: h1 says {m.group(1) if m else '?'} letters, table has {n_rows}")
        if re.search(r"\b\d{1,3}(?:\.\d)?%", text(d)):
            fails.append(f"/crl/company/{slug} states a percentage")
    if re.search(r"\b\d{1,3}(?:\.\d)?%", text(doc)):
        fails.append("/crl/companies states a percentage")
    if fails:
        print("FAIL /crl/companies vs corpus:\n   " + "\n   ".join(fails[:20])); return 1
    print(f"OK -- /crl/companies adds to {len(keys)} distinct CRLs; {len(pages)} company pages, each h1 count = its rows; no rate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
