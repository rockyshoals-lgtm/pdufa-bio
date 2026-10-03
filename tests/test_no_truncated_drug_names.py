# -*- coding: utf-8 -*-
"""CI guard: no cut drug name on a decision page or in /decisions (audit 2026-10-03, item 4.7, #65).

The archive feed cut names at 44 characters and the title builder re-read its own cut titles, so pages
shipped titled "Ipratropium Bromide HFA Inhala" and "TRUQAP (capivasertib) in combi", and /decisions
listed "PAPZIMEOS (zopapogene imadenov". Fails, on the RENDERED pages, when:
  * a decision page's <title> drug, lede, or headline has unbalanced parentheses;
  * the <title> drug is a strict prefix of the page's own "Drug / candidate" fact that stops mid-word;
  * a /decisions row's drug text does either.

    python tests/test_no_truncated_drug_names.py
"""
import glob
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def cut_prefix(short, full):
    return bool(full) and full.startswith(short) and len(full) > len(short) and full[len(short)].isalnum()


def main():
    fails, kvs = [], {}
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        kv = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", doc)
        full = html.unescape(kv.group(1)) if kv else ""
        kvs[slug] = full
        t = re.search(r"<title>(.*?)</title>", doc, re.S)
        title = html.unescape(t.group(1)) if t else ""
        dm = re.match(r"^(.+?)\s+(?:FDA Approval Announced|Approved|Approval Announced|CRL|Withdrawn)\b", title)
        td = dm.group(1) if dm else ""
        if td and (td.count("(") != td.count(")") or cut_prefix(td, full)):
            fails.append(f"/fda-decision/{slug}: title drug cut: {td!r}")
        for mark in (r"<!--FACTLEDE:BEGIN-->(.*?)<!--FACTLEDE:END-->",
                     r'<div class="ban (?:ap|cr)">[^<]*</div>\s*(?:<!--FACTLEDE:BEGIN-->.*?<!--FACTLEDE:END-->\s*)?<p class="sub">(.*?)</p>'):
            mm = re.search(mark, doc, re.S)
            if mm:
                txt = html.unescape(re.sub(r"<[^>]+>", "", mm.group(1)))
                if txt.count("(") != txt.count(")"):
                    fails.append(f"/fda-decision/{slug}: unbalanced parentheses (a cut name): {txt[:90]!r}")
    listing = io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})">.{0,200}?<span class="(?:ok|bad)">'
                         r'(?:Approved|CRL)</span>: ([^<]{2,80})</div>', listing, re.S):
        slug, text = m.group(1), html.unescape(m.group(2))
        if text.count("(") != text.count(")") or cut_prefix(text, kvs.get(slug, "")):
            fails.append(f"/decisions row {slug}: cut drug name {text!r}")
    if fails:
        print(f"FAIL: {len(fails)} cut drug name(s):")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- no cut drug names in {len(kvs)} decision pages or the /decisions listing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
