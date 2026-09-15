# -*- coding: utf-8 -*-
"""Four upcoming PDUFA rows with no /calendar row to align to (MIRM is co-listed under INCY's
row; NVCR is a Q4 window row; AXSM and BBIO are 2027) carried an SEC filing in `url`. The filing
moves to `source_url` (kept if already set) and `url` becomes the row's own event page, verified
to exist and to carry the row's date.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MAP = {"pdufa_mirm_2026-09-26": "/pdufa/MIRM-zilurgisertib",
       "pdufa_nvcr_2026-11-15": "/pdufa/NVCR-ttfields-therapy",
       "pdufa_axsm_2027-05-01": "/pdufa/AXSM-axs-12",
       "pdufa_bbio_2027-05-08": "/pdufa/BBIO-encaleret"}
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    p = MAP.get(r["id"])
    if not p:
        continue
    assert os.path.exists(os.path.join(HERE, "pdufa_site_src", p.strip("/"), "index.html")), p
    dd = r.setdefault("_d", {})
    if str(r["url"]).startswith("http") and not dd.get("source_url"):
        dd["source_url"] = r["url"]
    print(f"  {r['id']}: {str(r['url'])[:50]} -> {p}   (source_url={dd.get('source_url','')[:50]})")
    r["url"] = p
    n += 1
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
