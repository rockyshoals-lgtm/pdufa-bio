# -*- coding: utf-8 -*-
"""link_pdufa_explainer.py -- every drug and event page links the PDUFA explainer once.

SEO audit 2026-09-02b: /learn/what-is-a-pdufa-date has gone THREE audits at zero clicks
from position 8 on the site's own core term. It was retitled and still earns nothing --
at position 8 it never will. The route to top 3 is internal authority: the 544 drug
pages and the per-event PDUFA pages all use the word "PDUFA" in their first sentence,
and none of them linked the page that defines it. "The cheapest authority transfer
available, and it's entirely internal."

Mechanics: on each /drug/* and /pdufa/* page, the FIRST occurrence of "PDUFA" in
visible body text (after </h1>, outside tags, anchors, scripts and titles) becomes a
link to /learn/what-is-a-pdufa-date -- anchor text "PDUFA date" when the word "date"
follows, else "PDUFA". One link per page; a page already carrying the href is skipped,
so the pass is idempotent and safe to run daily.
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
URL = "/learn/what-is-a-pdufa-date"


def link_first_pdufa(doc):
    """Return doc with the first safe visible 'PDUFA( date)?' wrapped, or None."""
    h1 = doc.find("</h1>")
    if h1 < 0:
        return None
    for m in re.finditer(r"PDUFA(?: date)?\b", doc[h1:]):
        i = h1 + m.start()
        # inside a tag? (nearest angle bracket to the left is '<')
        lt, gt = doc.rfind("<", 0, i), doc.rfind(">", 0, i)
        if lt > gt:
            continue
        # inside an existing anchor?
        ao, ac = doc.rfind("<a ", 0, i), doc.rfind("</a>", 0, i)
        if ao > ac:
            continue
        # inside script/style?
        so, sc = doc.rfind("<script", 0, i), doc.rfind("</script>", 0, i)
        if so > sc:
            continue
        so, sc = doc.rfind("<style", 0, i), doc.rfind("</style>", 0, i)
        if so > sc:
            continue
        j = h1 + m.end()
        return (doc[:i] + f'<a href="{URL}" style="color:inherit;'
                f'text-decoration:underline dotted">{doc[i:j]}</a>' + doc[j:])
    return None


def main():
    pages = (sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html")))
             + sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))))
    linked = already = nothing = 0
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if f'href="{URL}"' in doc:
            already += 1
            continue
        new = link_first_pdufa(doc)
        if new is None:
            nothing += 1
            continue
        io.open(p, "w", encoding="utf-8").write(new)
        linked += 1
    print(f"explainer links: {linked} page(s) linked, {already} already carried it, "
          f"{nothing} had no linkable PDUFA mention (of {len(pages)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
