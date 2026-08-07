# -*- coding: utf-8 -*-
"""test_no_retracted_claims.py -- a retraction has to hold everywhere, including in the JSON-LD.

We retracted /fda-decision/SLS-2025-02-20 (an FDA Complete Response Letter for a company that has
never submitted a marketing application). Removing it took four passes, because the claim was
duplicated into surfaces the earlier fixes did not touch:

    1. the decision page itself            (removed)
    2. /decisions archive rows             (removed)
    3. /ticker/SLS visible HTML            (rewritten)
    4. /decisions/crl and /decisions/approvals listing pages   <- missed twice; live and indexable
    5. /ticker/SLS JSON-LD ItemList        <- missed three times; the version machines read

That last one is the lesson: the human-readable page can be correct while the structured data still
asserts the thing. This guard checks every surface at once.

It also enforces the general rule: no page may link a /fda-decision/ URL that has no page, in HTML
or in JSON-LD. That is what a retracted or fabricated decision looks like from the outside.

    python tests/test_no_retracted_claims.py
"""
import glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

# Claims we have retracted and must never republish. Ticker -> why.
RETRACTED = {
    "SLS-2025-02-20": "SELLAS has never submitted a marketing application, so no CRL is possible",
}
# Pages allowed to mention a retracted slug, because their job is to document the retraction.
ALLOWED = {"corrections/index.html", "changelog/index.html"}
DEC_LINK = re.compile(r"/fda-decision/([A-Z]+-\d{4}-\d{2}-\d{2})")


def main():
    on_disk = {os.path.basename(os.path.dirname(p))
               for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))}
    redirected = set()
    v = os.path.join(SITE, "vercel.json")
    if os.path.exists(v):
        try:
            for r in json.load(open(v, encoding="utf-8")).get("redirects", []):
                m = DEC_LINK.search(r.get("source", ""))
                if m:
                    redirected.add(m.group(1))
        except Exception:
            pass

    bad_retracted, dangling = [], []
    pages = [p for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)
             if "_bak" not in p and "_xbak" not in p]
    for p in pages:
        rel = os.path.relpath(p, SITE).replace("\\", "/")
        if rel in ALLOWED:
            continue
        html = open(p, encoding="utf-8", errors="replace").read()
        for slug in DEC_LINK.findall(html):
            if slug in RETRACTED:
                bad_retracted.append((rel, slug))
            elif slug not in on_disk and slug not in redirected:
                dangling.append((rel, slug))

    print(f"checked {len(pages):,} pages, {len(on_disk):,} decision pages on disk")
    ok = True

    # Duplicate page files. A Windows file operation left "index (1).html" beside the real
    # index.html in five decision directories, and a rebase committed all five. Each is a stale
    # near-copy of a live page, served at its own URL, which is duplicate content pointing at
    # superseded data on exactly the pages whose job is being right. They are invisible in normal
    # review because every listing and the sitemap only ever look at index.html.
    dupes = [os.path.relpath(p, SITE).replace("\\", "/")
             for p in glob.glob(os.path.join(SITE, "**", "*(*)*"), recursive=True)
             if os.path.isfile(p) and p.lower().endswith((".html", ".htm"))]
    if dupes:
        ok = False
        print(f"\nFAIL: {len(dupes)} duplicate page file(s) that would be served as their own URL:")
        for d in dupes[:10]:
            print(f"   {d}")
        print("   Delete them. The real page is index.html in the same directory.")
    else:
        print("  PASS: no duplicate 'index (N).html' page files")
    if bad_retracted:
        ok = False
        print(f"\nFAIL: {len(bad_retracted)} reference(s) to a RETRACTED decision:")
        for rel, slug in bad_retracted[:12]:
            print(f"   {rel}  ->  {slug}")
            print(f"      retracted because: {RETRACTED[slug]}")
        print("   These must be removed from HTML *and* JSON-LD. A correct visible page with the "
              "claim still in its structured data is still publishing the claim.")
    else:
        print("  PASS: no page republishes a retracted decision")

    if dangling:
        ok = False
        print(f"\nFAIL: {len(dangling)} link(s) to a decision page that does not exist and is not "
              f"redirected:")
        for rel, slug in dangling[:12]:
            print(f"   {rel}  ->  /fda-decision/{slug}")
    else:
        print("  PASS: every published decision link resolves or redirects")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
