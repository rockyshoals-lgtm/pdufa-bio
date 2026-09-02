# -*- coding: utf-8 -*-
"""add_drug_schema.py -- Drug JSON-LD with alternateName on every /drug page.

SEO audit 2026-09-02b (third audit asking): AI grounding queries plateaued at 18, and
9 of 18 are "{drug} pdufa date" -- breadth comes from entities. FAQPage says "there's a
Q&A here"; Drug says "this page IS camizestrant". alternateName is the citation lever:
an engine resolving daraxonrasib = RMC-6236, or zanidatamab = Ziihera, from OUR markup
cites our page for either surface form of the same question.

Everything emitted is read from the page itself (verify-then-publish; no external
lookups, no medical claims -- name, alternate names, sponsor, url only):
  name          h1 text before any parenthetical
  alternateName h1 parenthetical code(s) + the "marketed as Brand (generic)" cross-link
  manufacturer  the "Sponsor: ..." line's company names
  url           the canonical link

Marker-wrapped (DRUGLD), idempotent, replaced in full on every run so a renamed drug
re-emits correctly. Runs daily in CI after the drug-page build.
"""
import glob
import html as _html
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
B, E = "<!--DRUGLD:BEGIN-->", "<!--DRUGLD:END-->"


def facts(doc, slug):
    h = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
    if not h:
        return None
    h1 = _html.unescape(re.sub(r"<[^>]+>", "", h.group(1))).strip()
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", h1)
    name = (m.group(1) if m else h1).strip()
    alts = []
    if m:
        alts += [a.strip() for a in re.split(r"[,/]", m.group(2)) if a.strip()]
    am = re.search(r"marketed as\s*<a[^>]*>([^<]+)</a>", doc, re.I)
    if am:
        brand = _html.unescape(am.group(1)).strip()
        bm = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", brand)
        if bm:
            alts += [bm.group(1).strip(), bm.group(2).strip()]
        else:
            alts.append(brand)
    alts = [a for a in dict.fromkeys(alts) if a and a.lower() != name.lower()]
    sm = re.search(r"Sponsor:\s*([^<(]{3,120}?)\s*\((?:[A-Z]{1,6}(?:,\s*)?)+\)", doc)
    makers = ([s.strip() for s in _html.unescape(sm.group(1)).split(",") if s.strip()]
              if sm else [])
    ld = {"@context": "https://schema.org", "@type": "Drug", "name": name,
          "url": f"https://www.pdufa.bio/drug/{slug}"}
    if alts:
        ld["alternateName"] = alts
    if makers:
        ld["manufacturer"] = ([{"@type": "Organization", "name": mk} for mk in makers]
                              if len(makers) > 1
                              else {"@type": "Organization", "name": makers[0]})
    return ld


def main():
    changed = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "noindex" in doc[:2000]:
            continue
        ld = facts(doc, slug)
        if not ld or not ld.get("name"):
            print(f"  SKIP /drug/{slug}: no readable h1 name")
            skipped += 1
            continue
        block = (f"{B}<script type=\"application/ld+json\">"
                 + json.dumps(ld, separators=(",", ":"), ensure_ascii=False)
                 + f"</script>{E}")
        if B in doc:
            new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        elif "</head>" in doc:
            new = doc.replace("</head>", block + "</head>", 1)
        else:
            print(f"  SKIP /drug/{slug}: no </head>")
            skipped += 1
            continue
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            changed += 1
    print(f"Drug schema: {changed} page(s) written, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
