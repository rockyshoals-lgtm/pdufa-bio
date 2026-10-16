# -*- coding: utf-8 -*-
"""CI guard: a decided PDUFA row's decision page names the same product as the row (2026-10-15).

sync_api_from_pages.py accepted any same-ticker decision page within 14 days of a goal date as that row's
decision. When Pfizer's Tukysa approval page (/fda-decision/PFE-2026-10-07) was published, it replaced the
real decision date (2026-08-27) on the brepocitinib row (goal 2026-09-30), and fix_chart_captions.py then
stamped the brepocitinib FDA action date onto the Tukysa page. For a sponsor with several approvals a month,
proximity is not evidence. Fails when a Decided row's /fda-decision/{TICKER}-{dcd} page names a drug that
shares no word of four or more letters with the row's name, or when a decision page's chart caption cites an
FDA action date belonging to a row whose drug the page does not name.

Plant: PLANT_WRONG_DCD=1 moves the brepocitinib row's dcd onto the Tukysa page in memory and must FAIL.

    python tests/test_decision_page_matches_row_drug.py
"""
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STOP = {"with", "combination", "priority", "review", "tablets", "injection", "plus", "oral", "approval",
        "indication", "patients", "adults", "label", "update", "expanded"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", html.unescape(str(s or "")).lower()) if w not in STOP}


def page_drug(slug):
    p = os.path.join(SITE, "fda-decision", slug, "index.html")
    if not os.path.exists(p):
        return None
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", doc, re.S)
    return re.sub(r"<[^>]+>", " ", m.group(1)) if m else None


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    if os.environ.get("PLANT_WRONG_DCD") == "1":
        for r in rows:
            if r.get("id") == "pdufa_pfe_2026-09-30":
                r["dcd"] = "2026-10-07"
    fails, n = [], 0
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "") != "Decided" or not r.get("dcd"):
            continue
        slug = f"{str(r.get('t')).upper()}-{str(r.get('dcd'))[:10]}"
        drug = page_drug(slug)
        if drug is None:
            continue
        n += 1
        rn = " ".join([str(r.get("name") or ""), str((r.get("_d") or {}).get("brand") or ""),
                       str((r.get("_d") or {}).get("inn") or "")])
        if toks(rn) and toks(drug) and not (toks(rn) & toks(drug)):
            fails.append(f"{r['id']} ({r.get('name')!r}) is dated by /fda-decision/{slug}, which names {drug.strip()!r}")
    if fails:
        print(f"FAIL: {len(fails)} decided row(s) dated by another product's decision page:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decided rows each dated by a decision page that names the same product.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
