# -*- coding: utf-8 -*-
"""Two dead internal-link classes, found 2026-09-18 by walking every rendered page.

1. THE NAV'S "Pro" LINK HAS ALWAYS 404ed. Every page carries nav entry ("/pricing", "Pro") and
   `pdufa_site_src/pricing/index.html` has never existed in this repository's history -- 954
   pages link it. The tier comparison it promises does exist, on /developers under the heading
   "Tiers", so the link points there. No price is invented: /developers describes what Free and
   Pro include and nothing here changes that.

2. FIVE DATASET ROWS POINT AT A /pdufa/{TICKER} PAGE THAT DOES NOT EXIST (CELC x2, VERA x3), and
   a sixth -- the LLY imlunestrant approval added today -- pointed at /pdufa/LLY, which exists but
   is the tirzepatide window page and has nothing to do with the decision. Each moves to the
   ticker hub, which exists and carries that ticker's events.

    python fix_dead_internal_links.py [--dry-run]
"""
import argparse
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
PRO_OLD, PRO_NEW = "/pricing", "/developers#tiers"
# The LLY row is named explicitly because its target EXISTS but is the wrong event: /pdufa/LLY is
# the tirzepatide window page. Every other repair is derived, not listed: any row whose url does
# not resolve moves to that ticker's hub.
ROW_FIX = {"pdufa_lly_2026-09-18": "/ticker/LLY"}


def resolves(rel):
    rel = rel.strip("/")
    return bool(rel) and (os.path.isfile(os.path.join(SITE, rel, "index.html"))
                          or os.path.isfile(os.path.join(SITE, rel)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # 1. the generator first, so the next rebuild does not undo this
    nav = os.path.join(HERE, "rebuild_nav.py")
    t = io.open(nav, encoding="utf-8").read()
    t2 = t.replace('PRO = ("/pricing", "Pro")', f'PRO = ("{PRO_NEW}", "Pro")')
    if t2 != t and not a.dry_run:
        io.open(nav, "w", encoding="utf-8").write(t2)
    print("rebuild_nav.py PRO target:", "updated" if t2 != t else "already correct")

    # 2. every rendered page
    n = 0
    for root, dirs, files in os.walk(SITE):
        if "index.html" not in files:
            continue
        p = os.path.join(root, "index.html")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = doc.replace(f'href="{PRO_OLD}"', f'href="{PRO_NEW}"')
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"pages whose Pro link moved to {PRO_NEW}: {n}")

    # 3. the dataset rows
    ds = os.path.join(SITE, "api", "v1", "dataset.mjs")
    src = io.open(ds, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    m = 0
    for r in rows:
        cur = str(r.get("url") or "")
        tk = str(r.get("t") or "").upper()
        want = ROW_FIX.get(r.get("id"))
        if not want:
            if not cur.startswith("/") or resolves(cur):
                continue            # external, or the page is really there
            want = f"/ticker/{tk}"
        if r.get("url") == want:
            continue
        if not resolves(want):
            print(f"  SKIP {r['id']}: neither {cur} nor {want} exists")
            continue
        print(f"  {r['id']:<30} {cur:<22} -> {want}")
        r["url"] = want
        m += 1
    if m and not a.dry_run:
        io.open(ds, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"{m} dataset row url(s) repointed" + ("   (--dry-run)" if a.dry_run else ""))

    # 4. RENDERED CROSS-LINKS. Event and drug pages cross-link a sponsor's other events by
    # building /pdufa/{TICKER}-{drug-slug} from a name instead of checking that the page was
    # built, so links like /pdufa/AZN-truqap and /pdufa/LNTH-lnth-2501 404 from 108 pages. Where
    # the constructed target does not exist, the ticker hub does and carries the same events.
    fixed_pages, rewrites = 0, {}
    for root, dirs, files in os.walk(SITE):
        if "index.html" not in files or re.search(r"[\\/]_[a-z]+bak|[\\/]_pdufa_", root):
            continue
        p = os.path.join(root, "index.html")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        out = doc
        for href in set(re.findall(r'href="(/pdufa/[A-Z][^"#?]*)"', doc)):
            if resolves(href):
                continue
            tkm = re.match(r"/pdufa/([A-Z]{1,6})", href)
            if not tkm:
                continue
            hub = f"/ticker/{tkm.group(1)}"
            if not resolves(hub):
                continue
            out = out.replace(f'href="{href}"', f'href="{hub}"')
            rewrites[href] = rewrites.get(href, 0) + 1
        if out != doc:
            fixed_pages += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(out)
    print(f"{fixed_pages} page(s) had a dead /pdufa cross-link repointed to the ticker hub")
    for k, v in sorted(rewrites.items(), key=lambda kv: -kv[1])[:10]:
        print(f"   {k:<42} on {v} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
