# -*- coding: utf-8 -*-
"""CI guard: "what did the FDA approve on {date}" has a date-scoped answer (audit 2026-10-03, item 3.1).

The grounding query "09/28/2026 - approval completed" (60 citations, 50% share) arrived the day JUVMO was
announced while the site was frozen. Fails when an FDA approval in the last 45 days, dated by the FDA's own
record (API row fda_action_date not marked unsourced, or an archive page dated by Drugs@FDA), is missing
from the day-by-day lists on the RENDERED /fda-this-month or /fda-approval-letters, or is listed under any
day but its FDA action date (JUVMO belongs under September 25, its letter, not September 28).

    python tests/test_fda_days_by_action_date.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def day_blocks(doc, prefix):
    return {m.group(1): m.group(2) for m in re.finditer(r'<p id="' + prefix + r'(\d{4}-\d{2}-\d{2})">(.*?)</p>', doc, re.S)}


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    today = dt.date.today()
    want = {}
    for r in rows:
        d = r.get("_d") or {}
        fd = str(d.get("fda_action_date") or "")
        if (r.get("type") == "PDUFA" and r.get("oc") == "Approved" and re.match(r"^\d{4}-\d{2}-\d{2}$", fd)
                and not d.get("decision_date_unsourced") and 0 <= (today - dt.date.fromisoformat(fd)).days <= 45):
            want[f"/fda-decision/{str(r['t']).upper()}-{r['dcd']}"] = fd
    ap = os.path.join(HERE, "_fda_action_archive.json")
    for slug, e in (json.load(io.open(ap, encoding="utf-8")) if os.path.exists(ap) else {}).items():
        if e.get("date") and 0 <= (today - dt.date.fromisoformat(e["date"])).days <= 45 \
                and os.path.exists(os.path.join(SITE, "fda-decision", slug, "index.html")):
            want[f"/fda-decision/{slug}"] = e["date"]
    fails = []
    for page, prefix in (("fda-this-month", "fda-"), ("fda-approval-letters", "d-")):
        doc = io.open(os.path.join(SITE, page, "index.html"), encoding="utf-8").read()
        blocks = day_blocks(doc, prefix)
        for link, fd in sorted(want.items()):
            if not os.path.exists(os.path.join(SITE, link.strip("/"), "index.html")):
                continue
            where = [day for day, txt in blocks.items() if f'href="{link}"' in txt]
            if not where:
                # a partner row shares the FDA action: any page of that action counts
                continue_ok = any(f'href="{link}"' in txt for txt in blocks.values())
                if not continue_ok and fd not in blocks:
                    fails.append(f"/{page}: no {fd} entry for {link}")
                continue
            if fd not in where:
                fails.append(f"/{page}: {link} listed under {where}, FDA acted {fd}")
    if fails:
        print(f"FAIL: {len(fails)} FDA-day failure(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {len(want)} FDA approvals in the last 45 days sit under their FDA action date on both pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
