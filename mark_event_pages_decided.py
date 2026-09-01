# -*- coding: utf-8 -*-
"""mark_event_pages_decided.py -- a per-event PDUFA page must not present a decided
event as pending.

THE GAP (re-audit 2026-09-01b, root cause #2): build_pdufa_event_pages deliberately never
overwrites existing pages -- they carry hand-grown story cards a rebuild would flatten --
so nothing ever told /pdufa/REGN-garetosmab that garetosmab had been APPROVED. The page
sat 25 days stale saying "target 2026-08-31" on a query converting at 33% CTR at position
2, and its dateModified argued against its own freshness. Same for LNTH-florquinitau and
every other decided event's page.

This injector completes the write-once design instead of fighting it: when a page's event
is Decided in the dataset, a marker-based outcome banner (DECBAN) goes in right after the
freshness stamp, linking the decision page that carries the source. Idempotent; re-runs
update the banner in place; nothing else on the page is touched, so the hand-grown
content survives. Runs daily in CI after refresh_moved_pdufa_pages -- moves handled
there, outcomes here, and build_date_modified then stamps the real change honestly.

Matching is conservative, single-candidate-or-skip, same discipline as
refresh_moved_pdufa_pages: slug ticker must match, slug drug tokens (if any) must
intersect the event name, and multiple candidates mean a skip with a loud line.
"""
import datetime as dt
import glob
import html as _html
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
B, E = "<!--DECBAN:BEGIN-->", "<!--DECBAN:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def pretty(iso):
    try:
        d = dt.date.fromisoformat(str(iso)[:10])
        return f"{MON[d.month]} {d.day}, {d.year}"
    except Exception:
        return str(iso or "")


def toks(s):
    return set(re.findall(r"[a-z0-9]{4,}", str(s or "").lower()))


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    decided = [r for r in rows if r.get("type") == "PDUFA"
               and str(r.get("st", "")).lower() == "decided" and r.get("dcd")]

    changed = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})(?:-(.+))?$", slug)
        if not m:
            continue
        tk, drug_part = m.group(1), (m.group(2) or "").replace("-", " ")
        if not drug_part:
            continue          # bare-ticker pages are owned by build_pdufa_ticker_index
        tk_cands = [r for r in decided if str(r.get("t", "")).upper() == tk]
        dtoks = toks(drug_part)
        cands = [r for r in tk_cands if dtoks & toks(r.get("name"))]
        if not cands and tk_cands:
            # Alias gap: slug carries the generic (florquinitau), the dataset the code
            # name (MK-6240). The page TITLE is machine-written from the dataset name at
            # creation, so match event-name tokens against it instead.
            doc0 = io.open(p, encoding="utf-8", errors="replace").read()
            tm = re.search(r"<title[^>]*>[A-Z]{1,6} PDUFA date:\s*(.+?),\s*[A-Z][a-z]{2}",
                           doc0)
            ttoks = toks(tm.group(1)) if tm else set()
            cands = [r for r in tk_cands if ttoks & toks(r.get("name"))]
        if not cands:
            continue
        if len(cands) > 1:
            print(f"  SKIP /pdufa/{slug}: {len(cands)} decided events match; a wrong "
                  f"banner is worse than none -- resolve by hand")
            skipped += 1
            continue
        r = cands[0]
        oc = str(r.get("oc") or "Decided")
        dcd, goal = str(r.get("dcd")), str(r.get("d"))
        try:
            delta = (dt.date.fromisoformat(dcd) - dt.date.fromisoformat(goal)).days
        except Exception:
            delta = None
        timing = ("" if delta is None else
                  " on its goal date" if delta == 0 else
                  f", {-delta} days before its {pretty(goal)} goal date" if delta < 0 else
                  f", {delta} days after its {pretty(goal)} goal date")
        ok = oc == "Approved"
        col = "#46d17f" if ok else "#ff8f6b"
        word = "Approved" if ok else ("Complete Response Letter" if oc == "CRL" else oc)
        dec_url = f"/fda-decision/{tk}-{dcd}"
        has_dec_page = os.path.exists(os.path.join(SITE, "fda-decision", f"{tk}-{dcd}",
                                                   "index.html"))
        link = (f' <a href="{dec_url}" style="color:#9ec5ff">Decision page with the '
                f'source and measured reaction</a>.' if has_dec_page else "")
        banner = (f'{B}<div style="background:#0c1d38;border:1px solid {col};'
                  f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;'
                  f'font-size:14.5px"><b style="color:{col}">{"&#10003;" if ok else "&#10007;"} '
                  f'{_html.escape(word)}</b> &middot; the FDA decided this application on '
                  f'<b>{pretty(dcd)}</b>{_html.escape(timing)}.{link}</div>{E}')

        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            new = doc.split(B, 1)[0] + banner + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            if anchor not in doc:
                print(f"  SKIP /pdufa/{slug}: no insertion anchor")
                skipped += 1
                continue
            i = doc.index(anchor) + len(anchor)
            new = doc[:i] + banner + doc[i:]
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            changed += 1
            print(f"  /pdufa/{slug}: {word} {dcd}{timing}")
    print(f"decided banners: {changed} page(s) updated, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
