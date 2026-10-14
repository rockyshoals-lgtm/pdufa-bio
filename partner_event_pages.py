# -*- coding: utf-8 -*-
"""partner_event_pages.py -- one application filed by two listed partners gets ONE page that names both.

Audit 2026-10-13 order 5: the VTRS MR-141 row's API url was the IRD page (phentolamine ophthalmic 0.75%, goal
2026-10-17: Opus Genetics / Viatris), while /pdufa/VTRS-mr-141 existed, indexable and self-canonical. Two pages
for one FDA decision split the signal and one of them named only the partner. Ruling: the alphabetically first
page is the event's page; its title, og:title, h1 and breadcrumb carry both tickers ("IRD / VTRS PDUFA date:
..."), both rows carry `_d.event_slug` pointing at it, and the twin page is canonicalised to it (noindex,follow,
with the duplicate notice canonicalise_duplicate_event_pages.py uses).

Partners are two pending day-dated PDUFA rows with the same date, different tickers and a shared drug token (the
same test sync_event_urls.py uses). Idempotent. Runs in the chain after build_pdufa_event_pages.py and before
sync_event_urls.py.

    python partner_event_pages.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
sys.path.insert(0, HERE)
import event_pages as EP  # noqa: E402
from site_dates import eastern_today  # noqa: E402


def toks(r):
    return set(re.findall(r"[a-z]{5,}", str(r.get("name") or "").lower()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    pend = [r for r in EP.pending_rows(rows, eastern_today().isoformat()) if str(r.get("dp") or "day") == "day"]
    pairs = []
    for r in pend:
        for x in pend:
            if x is r or str(x.get("d"))[:10] != str(r.get("d"))[:10]:
                continue
            tk, xt = str(r.get("t") or "").upper(), str(x.get("t") or "").upper()
            if tk == xt or tk > xt:
                continue
            if EP.drug_token(x) == EP.drug_token(r) or (toks(x) & toks(r)):
                pairs.append((r, x))
    changed_rows = 0
    for r, x in pairs:
        ur, ux = EP.resolve(r), EP.resolve(x)
        cands = sorted(u for u in (ur, ux) if u)
        if not cands:
            print(f"  {r['t']}/{x['t']} {r['d']}: no page for either row; skipped")
            continue
        prim = cands[0]
        slug = prim[len("/pdufa/"):]
        p = os.path.join(SITE, "pdufa", slug, "index.html")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        tks = sorted({str(r.get("t")).upper(), str(x.get("t")).upper()})
        label = " / ".join(tks)
        comps = " and ".join(dict.fromkeys(str(y.get("company") or y.get("t")) for y in (r, x)))
        o = doc
        # title / og:title / twitter:title: "{TK} PDUFA date: ..." -> "{TK1} / {TK2} PDUFA date: ..."
        for tk in tks:
            doc = re.sub(rf"(<title>|og:title\" content=\"|twitter:title\" content=\"){re.escape(tk)} PDUFA date:",
                         lambda m: m.group(1) + html.escape(label) + " PDUFA date:", doc)
            doc = re.sub(rf"<h1>{re.escape(tk)} PDUFA Date:", f"<h1>{html.escape(label)} PDUFA Date:", doc, count=1)
            doc = re.sub(rf"(PDUFA Calendar</a> &rsaquo; ){re.escape(tk)}</div>", lambda m: m.group(1) + html.escape(label) + "</div>", doc, count=1)
        if "<!--PARTNERS:BEGIN-->" not in doc:
            note = (f'<!--PARTNERS:BEGIN--><p class="sub" style="margin:6px 0 0">One application, two listed sponsors: '
                    f'{html.escape(comps)}. This is the page for the {html.escape(label)} decision; both companies\' '
                    f'calendar rows link here.</p><!--PARTNERS:END-->')
            doc = re.sub(r"(<div class=\"sub\">FDA decision \(PDUFA\) target.*?</div>)", lambda m: m.group(1) + note, doc, count=1, flags=re.S)
        for y in (r, x):
            if (y.get("_d") or {}).get("event_slug") != slug:
                y.setdefault("_d", {})["event_slug"] = slug
                changed_rows += 1
        # the twin page, if any, is canonicalised to the primary
        twin = [u for u in (ur, ux) if u and u != prim]
        twin_note = ""
        for u in twin:
            tp = os.path.join(SITE, "pdufa", u[len("/pdufa/"):], "index.html")
            t = io.open(tp, encoding="utf-8", errors="replace").read()
            t, n1 = re.subn(r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="https://www.pdufa.bio{prim}"', t)
            t, n2 = re.subn(r'<meta name="robots" content="[^"]*"', '<meta name="robots" content="noindex,follow"', t)
            if "<!--DUPLICATE-OF-->" not in t:
                t = t.replace("<h1", f'<p class="sub" style="margin:0 0 8px"><!--DUPLICATE-OF-->This page duplicates '
                                     f'<a href="{prim}">{prim}</a>, which is the page we maintain.</p><h1', 1)
            if not a.dry_run:
                io.open(tp, "w", encoding="utf-8").write(t)
            twin_note = f"; twin {u} -> canonical {prim}, noindex"
        if doc != o and not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(doc)
        print(f"  {label} {r['d']}: page {prim}{' (title/h1 updated)' if doc != o else ''}{twin_note}")
    if changed_rows and not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"partner event pages: {len(pairs)} pair(s); {changed_rows} row(s) given event_slug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
