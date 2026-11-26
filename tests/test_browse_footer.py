# -*- coding: utf-8 -*-
"""test_browse_footer.py -- the "Browse pdufa.bio" block at the foot of every page is laid out in even columns.

2026-11-26 (David: "the browse pdufa.bio: is not even, please format it to where it looks better"). Its 30 links ran
as one dot-separated line that wrapped raggedly, and on the homepage the header's own rules (nav{display:flex},
nav a{padding:7px 11px}) made every " · " a stray flex item floating at the top of its row. inject_site_links.py now
writes the links in six labelled columns (SITE_GROUPS) and inject_mobile_polish.py's stylesheet lays them out. This
fails if:

  1. a SITE_LINKS href is in no group, or in two, or a group names an href that is not in SITE_LINKS;
  2. a page's SITELINKS block is not the grouped layout (class pd-browse, a pd-bg grid, a pd-bgt label per column),
     still carries a " &middot; " separator or a bare text node between links, or links a page twice;
  3. a page's block lacks a SITE_LINKS page that exists (other than the page itself), so no link was lost;
  4. a page with the block lacks the stylesheet, or the stylesheet does not outrank the homepage's header rules
     (.pd-browse{display:block!important}, .pd-browse a with its own padding) or lacks the column steps (2, 3, 6) or
     the phone tap-height rule.

PLANT=dots puts the old separators back in one page's block; PLANT=css drops the grid rule from the stylesheet; each
must FAIL.

    python tests/test_browse_footer.py
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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
BLOCK = re.compile(r"<!--SITELINKS:BEGIN-->(.*?)<!--SITELINKS:END-->", re.S)


def main():
    plant = os.environ.get("PLANT", "")
    import inject_mobile_polish as M
    import inject_site_links as L
    fails = []

    hrefs = [h for _, h in L.SITE_LINKS]
    grouped = [h for _, hs in L.SITE_GROUPS for h in hs] + [L.SITE_LAST]
    for h in hrefs:
        if grouped.count(h) != 1:
            fails.append(f"SITE_GROUPS: {h} is in {grouped.count(h)} groups, not one")
    for h in set(grouped) - set(hrefs):
        fails.append(f"SITE_GROUPS: {h} is not in SITE_LINKS")

    css = M.CSS
    if plant == "css":
        css = css.replace(".pd-bg{display:grid", ".pd-bg{display:block")
    for need, why in ((".pd-browse{display:block!important", "outrank the homepage's nav{display:flex}"),
                      (".pd-bg{display:grid;grid-template-columns:repeat(2,", "two columns on a phone"),
                      ("@container pdb (min-width:560px){.pd-bg{grid-template-columns:repeat(3,", "three on a narrow page"),
                      ("@container pdb (min-width:1000px){.pd-bg{grid-template-columns:repeat(6,", "six on a wide page"),
                      ("container:pdb/inline-size", "columns sized by the block's own width"),
                      (".pd-browse a{display:block;margin:0;padding:4px 0", "outrank the homepage's nav a{padding}"),
                      (".pd-browse a{padding:7px 0}", "taller rows for a fingertip on phones")):
        if need not in css:
            fails.append(f"inject_mobile_polish.CSS: no {need!r} ({why})")

    pages = links = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)):
        s = io.open(p, encoding="utf-8", errors="replace").read()
        m = BLOCK.search(s)
        if not m:
            continue
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace(os.sep, "/")
        u = "/" if rel == "/." else rel
        b = m.group(1)
        pages += 1
        if plant == "dots" and pages == 1:
            b = b.replace("</a><a", "</a> &middot; <a", 1)
        if '<style id="mobilepolish">' not in s:
            fails.append(f"{u}: has the Browse block but not the stylesheet that lays it out")
        if not b.startswith('<nav aria-label="Browse pdufa.bio" class="pd-browse"><div class="pd-bh">'):
            fails.append(f"{u}: Browse block is not the grouped layout")
            continue
        if "&middot;" in b or "·" in b or re.search(r"</a>\s*[^<\s]", b):
            fails.append(f"{u}: Browse block still has separators or loose text between links")
        if '<div class="pd-bg">' not in b or b.count('class="pd-bgt"') < 5:
            fails.append(f"{u}: Browse block has no column grid or fewer than 5 labelled columns")
        got = re.findall(r'<a (?:class="pd-ball" )?href="([^"]+)"', b)
        links += len(got)
        if len(got) != len(set(got)):
            fails.append(f"{u}: Browse block links a page twice")
        want = [h for h in hrefs if h != u and L.page_exists(h)]
        miss = [h for h in want if h not in got]
        if miss:
            fails.append(f"{u}: Browse block lost {miss[:3]}")

    print(f"browse footer: {pages} pages, {links} links")
    for f in fails[:25]:
        print("  FAIL", f)
    if fails:
        print(f"  {len(fails)} failure(s). fix: python inject_site_links.py && python inject_mobile_polish.py")
        return 1
    if not pages:
        print("  FAIL no page carries the Browse block")
        return 1
    print("  PASS: every page's Browse links sit in labelled columns, none lost, and the stylesheet lays them out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
