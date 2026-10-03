# -*- coding: utf-8 -*-
"""CI guard: an event page's decided banner belongs to ITS application, not another indication of the brand.

2026-10-03: /pdufa/RHHBY-gazyva is the pending Gazyva lupus application; the build gave it the 2026-09-25
Gazyva idiopathic nephrotic syndrome approval (same brand, different application), and the October calendar
showed Tecentriq as "Approved" from the same decision. Fails, on the RENDERED /pdufa pages, when a page links
a decision (/fda-decision/TK-DATE) whose API row states an indication that shares no disease word with the
indication the page's own description names in parentheses.

    python tests/test_event_page_indication_match.py
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
STOP = {"with", "from", "patients", "adults", "adult", "years", "older", "disease", "treatment", "and", "the",
        "pediatric", "children", "aged", "ages", "who", "are", "in", "of", "for"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(s or "").lower()) if w not in STOP}


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    dec = {f"{str(r.get('t')).upper()}-{r.get('dcd')}": r for r in rows
           if r.get("type") == "PDUFA" and r.get("st") == "Decided" and r.get("dcd")}
    fails, n = [], 0
    for p in glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'<!--DECBAN:BEGIN-->.*?href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', doc, re.S) or \
            re.search(r'class="(?:ban|decided)[^"]*"[^>]*>.*?href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', doc[:60000], re.S)
        # the page's own indication, as its FAQ states it (pending form, or the decided form
        # mark_event_pages_decided rewrites it to)
        dm = (re.search(r"under FDA review for ([^.\"<]{4,120})", doc)
              or re.search(r"approved by the FDA on [A-Z][a-z]+ \d{1,2}, \d{4} (?:for|to treat) ([^.\"<]{4,120})", doc)
              or re.search(r"whose FDA approval the sponsor announced on [^,]+, for ([^.\"<]{4,120})", doc))
        if not (m and dm):
            continue
        r = dec.get(m.group(1))
        if not r:
            continue
        n += 1
        pt, rt = toks(html.unescape(dm.group(1))), toks((r.get("_d") or {}).get("indication"))
        if pt and rt and not (pt & rt):
            fails.append(f"/pdufa/{os.path.basename(os.path.dirname(p))}: banner links {m.group(1)} "
                         f"({(r.get('_d') or {}).get('indication', '')[:50]!r}), page is for {dm.group(1)!r}")
    if fails:
        print(f"FAIL: {len(fails)} event page(s) carry another application's decision:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decided event pages: each banner's decision matches the page's own indication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
