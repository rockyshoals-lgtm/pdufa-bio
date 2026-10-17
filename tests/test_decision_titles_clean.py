# -*- coding: utf-8 -*-
"""CI guard: no decision-page <title> ends its drug name on a dangling word (2026-10-16).

The title budget (100 characters) trims the drug name at a word boundary. /fda-decision/TEVA-2026-09-25 was titled
"Degevma (denosumab-adet), biosimilar to and Approved Sep 25, 2026", a cut that reads as broken in a search result.
Fails when the text before the outcome word (Approved / Approval Announced / CRL / Withdrawn) ends in a connector
(and, or, to, of, with, for, the, in, plus, a) or a comma.
Plant: PLANT_TITLE=1 injects the Degevma title in memory and must FAIL.

    python tests/test_decision_titles_clean.py
"""
import glob
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
RX = re.compile(r"^(.*?)\s+(?:FDA Approval Announced|Approval Announced|Approved|CRL|Withdrawn)\b")
BAD = re.compile(r"(?:\s(?:and|or|to|of|with|for|the|in|plus|a)|,)$", re.I)


def main():
    fails, n = [], 0
    titles = []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        m = re.search(r"<title>(.*?)</title>", io.open(p, encoding="utf-8", errors="replace").read(), re.S)
        if m:
            titles.append((os.path.basename(os.path.dirname(p)), html.unescape(m.group(1)).strip()))
    if os.environ.get("PLANT_TITLE") == "1":
        titles.append(("TEVA-2026-09-25", "Degevma (denosumab-adet), biosimilar to and Approved Sep 25, 2026 | TEVA FDA Decision | pdufa.bio"))
    for slug, t in titles:
        m = RX.match(t)
        if not m:
            continue
        n += 1
        if BAD.search(m.group(1)):
            fails.append(f"/fda-decision/{slug}: '{t}'")
    # 2026-10-17 (audit 2b): brand first. RYZUMVI's pages were titled "Phentolamine ophthalmic solution ..." and
    # "MR-141 ...", hiding the name people search. An approved row that records its brand must show it in the title.
    import json
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    tmap = dict(titles)
    if os.environ.get("PLANT_TITLE") == "brand":
        tmap["VTRS-2026-10-16"] = "MR-141 Approval Announced Oct 16, 2026 for Presbyopia | VTRS FDA Decision | pdufa.bio"
    nb = 0
    for r in rows:
        br = str((r.get("_d") or {}).get("brand") or "").strip()
        slug = f"{str(r.get('t') or '').upper()}-{str(r.get('dcd') or '')[:10]}"
        if not br or str(r.get("oc")) != "Approved" or slug not in tmap:
            continue
        nb += 1
        if br.lower() not in tmap[slug].lower():
            fails.append(f"/fda-decision/{slug}: title '{tmap[slug]}' does not name the approved brand {br}")
    # 2026-10-17: a row's hand-written seo_desc (<= 158 chars) IS the decision page's description. CI's
    # fix_meta_lengths.py regenerated RYZUMVI's to a label format ("Opus Genetics (IRD) FDA decision Oct 16, 2026:
    # Approved. RYZUMVI ...") because it did not recognise the sentence; locally the new page was out of its scope.
    ns = 0
    for r in rows:
        sd = str((r.get("_d") or {}).get("seo_desc") or "")
        slug = f"{str(r.get('t') or '').upper()}-{str(r.get('dcd') or '')[:10]}"
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not sd or len(sd) > 158 or not r.get("dcd") or not os.path.exists(p):
            continue
        dm = re.search(r'<meta name="description" content="([^"]*)"', io.open(p, encoding="utf-8", errors="replace").read())
        cur = html.unescape(dm.group(1)) if dm else ""
        if os.environ.get("PLANT_TITLE") == "seo" and slug == "IRD-2026-10-16":
            cur = "Opus Genetics (IRD) FDA decision Oct 16, 2026: Approved. RYZUMVI (phentolamine ophthalmic solution) 0.75%."
        ns += 1
        if cur != sd:
            fails.append(f"/fda-decision/{slug}: description '{cur[:80]}' is not the row's seo_desc '{sd[:60]}'")
    if fails:
        print(f"FAIL: {len(fails)} decision title(s) cut on a dangling word or missing the brand:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision titles end the drug name cleanly; {nb} approved rows with a recorded brand name it in the title; {ns} hand-written descriptions intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
