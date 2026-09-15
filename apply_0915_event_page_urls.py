# -*- coding: utf-8 -*-
"""Seven upcoming rows on multi-event tickers pointed at the ticker's bare page, which states the
OTHER event's date (PRAX ulixacaltamide -> a page saying Dec 27; COGT PEAK -> a page saying Dec 30).
Each has its own per-event page already; the row now names it. Verified: each target page's
"FDA PDUFA target date" fact equals the row's date."""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MAP = {"pdufa_prax_2026-12-27": "/pdufa/PRAX-relutrigine",
       "pdufa_prax_2027-01-29": "/pdufa/PRAX-ulixacaltamide",
       "pdufa_cogt_2026-11-30": "/pdufa/COGT-bezuclastinib",
       "pdufa_gild_2026-12-23": "/pdufa/GILD-anito-cel",
       "pdufa_gild_2027-02-02": "/pdufa/GILD-yeztugo",
       "pdufa_rhhby_2026-10-15": "/pdufa/RHHBY-enspryng"}
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    p = MAP.get(r["id"])
    if not p:
        continue
    t = io.open(os.path.join(HERE, "pdufa_site_src", p.strip("/"), "index.html"), encoding="utf-8").read()
    kv = re.search(r"PDUFA target date</span><b>([^<]+)</b>", t)
    assert kv and kv.group(1) == r["d"], (r["id"], p, kv and kv.group(1), r["d"])
    print(f"  {r['id']}: {r['url']} -> {p}  (page states {kv.group(1)})")
    r["url"] = p
    n += 1
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
