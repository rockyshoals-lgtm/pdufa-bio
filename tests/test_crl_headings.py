# -*- coding: utf-8 -*-
"""CI guard: CRL deficiency sections come from the letter's PDF text layer, never OCR (audit 2026-10-03, 4.5).

Fails, on the rendered /crl hub and CRL decision pages, when a section named for a letter is not one of the
headings extract_crl_headings.py read from that letter's PDF text layer (_crl_headings.json), or when a
letter without a text layer is shown with sections.

    python tests/test_crl_headings.py
"""
import html
import io
import json
import os
import re
import sys
from urllib.parse import unquote

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    cache = json.load(io.open(os.path.join(HERE, "_crl_headings.json"), encoding="utf-8"))
    fails, n = [], 0
    hub = io.open(os.path.join(SITE, "crl", "index.html"), encoding="utf-8").read()
    for m in re.finditer(r'download\.open\.fda\.gov/crl/([^"]+)" rel="noopener">letter \(PDF\)</a></td>'
                         r'<td style="font-size:12\.5px">(.*?)</td>', hub):
        fn, cell = unquote(m.group(1)), html.unescape(m.group(2))
        if cell in ("", "·", "no text layer (scanned PDF)"):
            continue
        rec = cache.get(fn) or {}
        heads = {h.lower() for h in rec.get("headings", [])}
        n += 1
        if not rec.get("text_layer"):
            fails.append(f"/crl {fn}: sections shown for a letter without a PDF text layer")
        for sec in cell.split("; "):
            if sec.lower() not in heads:
                fails.append(f"/crl {fn}: '{sec}' is not a heading read from the PDF")
    import glob
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'download\.open\.fda\.gov/crl/([^"]+)".*?Sections the letter addresses</b>[^:]*: (.*?)\.</div>', doc, re.S)
        if not m:
            continue
        fn = unquote(m.group(1))
        heads = {h.lower() for h in (cache.get(fn) or {}).get("headings", [])}
        for sec in html.unescape(m.group(2)).split("; "):
            if sec.lower() not in heads:
                fails.append(f"{os.path.relpath(p, SITE)}: '{sec}' is not a heading read from the PDF")
    if fails:
        print(f"FAIL: {len(fails)} CRL section failure(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} /crl letters show sections, every one a heading read from the PDF's text layer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
