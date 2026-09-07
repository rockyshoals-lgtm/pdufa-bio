# -*- coding: utf-8 -*-
"""Every sponsor caveat in the dataset is RENDERED on every event page for that application.

Audit 2026-09-07 item 5 (carried from 09-06 ORDER 2): the 09-06 ack claimed the Scholar Rock
Catalent Indiana / second fill-finish caveat on both /pdufa/SRRK-apitegromab and /pdufa/SRRK.
Live, only the slug page had it: build_pdufa_ticker_index.py regenerates /pdufa/{TICKER} from
a bare shell and ran AFTER inject_sponsor_caveat.py in CI, so the index page lost the block
every run. A guard asserts the render, not the process: for each PDUFA row carrying
`_d.sponsor_caveat`, each existing event page (bare ticker + drug slug) must contain the
CAVEAT marker AND the caveat's own opening words.

Proved 0 -> 1 -> 0 on 2026-09-07 by deleting the block from /pdufa/SRRK/index.html.
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s[:30].rstrip("-")


def test_sponsor_caveat_rendered():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    bad, checked = [], 0
    for r in rows:
        d = r.get("_d") or {}
        caveat = str(d.get("sponsor_caveat") or "").strip()
        if not caveat or r.get("type") != "PDUFA":
            continue
        tk = str(r.get("t") or "").upper()
        nm = slugify(re.split(r"\s*[-(]", str(r.get("name") or ""))[0])
        pages = [os.path.join(SITE, "pdufa", tk, "index.html")]
        if nm:
            pages.append(os.path.join(SITE, "pdufa", f"{tk}-{nm}", "index.html"))
        head = re.sub(r"\s+", " ", caveat)[:40]
        for p in pages:
            if not os.path.isfile(p):
                continue
            checked += 1
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            flat = re.sub(r"\s+", " ", doc)
            if "<!--CAVEAT:BEGIN-->" not in doc or head.replace("'", "&#x27;") not in flat \
                    and head not in flat:
                bad.append(f"/pdufa/{os.path.basename(os.path.dirname(p))}: sponsor caveat "
                           f"for {tk} not rendered ('{head}...')")
    assert checked > 0, "no event page carries a dataset sponsor caveat -- guard cannot see"
    assert not bad, "sponsor caveat missing from event page(s):\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_sponsor_caveat_rendered()
    print("OK")
