# -*- coding: utf-8 -*-
"""inject_fda_action_record.py -- every decision page cites the FDA's own record of the action date.

Audit 2026-09-26 section 3: our timing numbers were already more accurate than the incumbent's
(TLX and TAUKLARIFY dated to the FDA's action day, not the announcement), but a reader could not
see why, because decision pages cited the press release. sync_fda_action_dates.py now holds, per
decided row, the FDA record the action date comes from (Drugs@FDA submission + approval letter,
a CBER approval letter or notice, or the FDA's released Complete Response Letter). This script
renders it on the page, between markers, idempotently:

  FDA record of the action: approved September 21, 2026 -- BLA 761363 S-017 (FDA letter).
  The sponsor announced it on September 22, 2026.

Rows whose action day no FDA record states yet get nothing here (their pages already carry the
decision_date_note); the block appears on the next run after the record does.

    python inject_fda_action_record.py [--dry-run]
"""
import argparse
import datetime as dt
import html
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
B, E = "<!--FDAREC:BEGIN-->", "<!--FDAREC:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
       "October", "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    # Audit 2026-10-03 (2.1): archive decision pages with no API row, dated by Drugs@FDA through
    # sync_archive_fda_dates.py (one unambiguous decision-class approval 0-4 days before the
    # announcement), carry the same block. Shaped as pseudo-rows so one renderer serves both.
    arch_p = os.path.join(HERE, "_fda_action_archive.json")
    arch = json.load(io.open(arch_p, encoding="utf-8")) if os.path.exists(arch_p) else {}
    have = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")) for r in rows}
    for slug, ent in sorted(arch.items()):
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not (m and ent.get("date") and (m.group(1), m.group(2)) not in have):
            continue
        rows.append({"t": m.group(1), "dcd": m.group(2), "oc": "Approved",
                     "_d": {"fda_action_source_url": ent.get("source_url"), "fda_action_date": ent["date"],
                            "fda_action_record": ent.get("record")}})
    n = skipped = 0
    for r in rows:
        d = r.get("_d") or {}
        url, fd, dcd = d.get("fda_action_source_url"), d.get("fda_action_date"), str(r.get("dcd") or "")
        if not (url and fd and re.match(r"^\d{4}-\d{2}-\d{2}$", dcd)):
            continue
        tk = str(r.get("t") or "").upper()
        p = os.path.join(SITE, "fda-decision", f"{tk}-{dcd}", "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        verb = "approved" if r.get("oc") == "Approved" else "issued a Complete Response Letter"
        rec = d.get("fda_action_record") or "FDA record"
        kind = ("FDA letter" if re.search(r"ltr\.pdf$|/media/\d+/download|download\.open\.fda\.gov/crl/", url)
                else "Drugs@FDA" if "accessdata.fda.gov" in url else "FDA notice")
        ann = (f" The sponsor announced it on {pretty(dcd)}." if fd != dcd else
               " The sponsor announced it the same day.")
        block = (f'{B}<p class="sub" style="font-size:13px;margin:8px 0">'
                 f'<b>FDA record of the action:</b> the FDA {verb} on <b>{pretty(fd)}</b>, per '
                 f'<a href="{html.escape(url, quote=True)}" rel="noopener" style="color:#e3ba5e">'
                 f'{html.escape(rec)} ({kind})</a>.{ann} Action dates on pdufa.bio come from the '
                 f'FDA\'s own record, not the press release. Every FDA action we hold, by FDA date: '
                 f'<a href="/fda-approval-letters" style="color:#e3ba5e">FDA approval letters</a>.</p>{E}')
        if B in doc:
            new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            i = next((doc.index(x) for x in ("<!--DFAQ:BEGIN-->", '<div class="legal"', "<footer") if x in doc), None)
            if i is None:
                skipped += 1
                continue
            new = doc[:i] + block + doc[i:]
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"fda action record: {n} decision page(s) {'would be ' if a.dry_run else ''}updated, {skipped} skipped (no anchor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
