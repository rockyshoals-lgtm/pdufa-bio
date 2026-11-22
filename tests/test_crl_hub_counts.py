# -*- coding: utf-8 -*-
"""CI guard: /crl states exactly what the CRL corpus file holds -- records, approved, unapproved.

Moat audit 09-20b item 1. The page said 444 letters while the corpus held 458 (a file-name
filter dropped 13 letters FDA named with spaces or commas), and it carried none of the counts
that make the archive mean anything. The counts are openFDA's (transparency/crl,
approval_status) and this asserts the RENDER equals the FILE: the h1/title record count, the
since-approved and not-approved counts in the released block, and the by-year table's totals.

    python tests/test_crl_hub_counts.py
"""
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


def main():
    p = os.path.join(SITE, "crl", "index.html")
    if not (os.path.exists(p) and os.path.exists(CORPUS)):
        print("  SKIP /crl or corpus missing"); return 0
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    n = len(recs)
    ap = sum(1 for r in recs if str(r.get("approval_status") or "").strip() == "Approved")
    un = sum(1 for r in recs if str(r.get("approval_status") or "").strip() == "Unapproved")
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc))))
    fails = []
    if not re.search(rf"\b{n} records in the FDA's release", t):
        fails.append(f"released block does not say '{n} records'")
    if not re.search(rf"openFDA labels {ap} of them as letters to applications the FDA has since approved and {un} as", t):
        fails.append(f"released block does not carry approved={ap} / unapproved={un}")
    m = re.search(r"All (\d+) (\d+) (\d+)", t)
    if not m:
        fails.append("by-year table has no 'All' row")
    else:
        a, u, tot = map(int, m.groups())
        if a + u != tot or a > ap or u > un or tot > n:
            fails.append(f"by-year totals inconsistent: {a}+{u}={tot} vs corpus {ap}/{un}/{n}")
    # 2026-11-22 (CRL red team): the distinct-letter count. A record repeats another only when its letter date,
    # application numbers and text are the same; two applications sharing one combined PDF are two letters.
    keys, n_pdf, cr_keys = set(), 0, set()
    for r in recs:
        if not (re.match(r"\d{2}/\d{2}/\d{4}", str(r.get("letter_date") or ""))
                and str(r.get("file_name") or "").strip().lower().endswith(".pdf")):
            continue
        n_pdf += 1
        k = (str(r.get("letter_date"))[:10], tuple(sorted(str(a).strip() for a in (r.get("application_number") or []))),
             re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower())
        keys.add(k)
        if str(r.get("letter_type") or "") == "COMPLETE RESPONSE":
            cr_keys.add(k)
    # 2026-11-22: the release also holds tentative approvals, a refusal to file, a rescission and untyped records;
    # the title and h1 count only the distinct letters openFDA types COMPLETE RESPONSE (as /crl/facts does)
    if f"{len(cr_keys)} Released CRLs" not in re.search(r"<title>([^<]*)", doc).group(1):
        fails.append(f"title does not say '{len(cr_keys)} Released CRLs' (distinct letters typed COMPLETE RESPONSE)")
    if not re.search(rf"\b{len(cr_keys)} released CRLs\b", t):
        fails.append(f"h1 does not say '{len(cr_keys)} released CRLs'")
    if not re.search(rf"\b{len(keys)} distinct letters\b", t):
        fails.append(f"page does not say '{len(keys)} distinct letters' (records with a PDF: {n_pdf}, repeats: "
                     f"{n_pdf - len(keys)})")
    if re.search(r"\b\d{1,3}(?:\.\d)?% of (?:CRLs|letters|applications)", t) or "approval rate after a CRL" in t.lower() and "%" in t:
        fails.append("page states a percentage rate from the corpus (counts only -- release policy, not odds)")
    if fails:
        print("FAIL /crl vs corpus:\n   " + "\n   ".join(fails)); return 1
    print(f"OK -- /crl states {n} records, {ap} since-approved, {un} not approved; counts match the corpus; no rate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
