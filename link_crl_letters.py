# -*- coding: utf-8 -*-
"""link_crl_letters.py -- CRL decision pages link the FDA's actual letter.

Audits 09-01 through 09-02c, item open since the corpus landed: we hold 458 FDA
Complete Response Letters (openFDA transparency program) and cited zero of them. The
letters are public, hosted by FDA at https://download.open.fda.gov/crl/{file_name}
(verified 200), and they are the PRIMARY source for the very pages that assert a CRL
happened. The 09-02c audit's timing point: the decision template was just rewritten,
so this is the cheapest moment to add the source link.

Match rule (verify-then-publish, conservative): a corpus letter attaches to a CRL
decision page only when the letter_date equals the page's decision date exactly AND the
letter's company name shares a meaningful token with the page's company name. Two
different sponsors can receive CRLs on the same day; the company check keeps their
letters apart. No match = no card; a wrong primary source is worse than none.

Injects a marker-based card (CRLSRC) after the freshness stamp: application number,
letter date, and the FDA-hosted PDF. Idempotent; re-runs replace in place. Counts,
never rates -- the card states what the letter is, not what CRLs "mean".
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
CORPUS = os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
B, E = "<!--CRLSRC:BEGIN-->", "<!--CRLSRC:END-->"
STOP = {"inc", "corp", "llc", "ltd", "pharmaceuticals", "pharmaceutical", "pharma",
        "therapeutics", "biosciences", "bioscience", "sciences", "company", "holdings",
        "group", "limited", "plc"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{3,}", str(s or "").lower())
            if w not in STOP}


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    by_date = {}
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        if not m or str(r.get("letter_type", "")).upper() != "COMPLETE RESPONSE":
            continue
        iso = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
        by_date.setdefault(iso, []).append(r)

    linked = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, dcd = m.group(1), m.group(2)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not re.search(r"CRL|Complete Response", doc[:3000], re.I):
            continue                     # approvals and withdrawals have other sources
        # The LETTER is dated the FDA action day; our page often carries the company's
        # ANNOUNCEMENT day (ACHV: goal Fri Jun 20, announced Mon Jun 22). Accept a
        # letter dated up to 4 days BEFORE the page date, never after -- a letter dated
        # after our decision date would belong to a different action.
        d0 = dt.date.fromisoformat(dcd)
        cands = []
        for back in range(0, 5):
            cands += by_date.get((d0 - dt.timedelta(days=back)).isoformat(), [])
        if not cands:
            continue
        # page company from the description ("{Company} ({TK}): ...") or breadcrumb
        cm = re.search(r'name="description" content="([^("]{2,60}?)(?: \(' + tk + r'\))?:',
                       doc)
        page_co = toks(_html.unescape(cm.group(1)) if cm else tk)
        hits = [r for r in cands if toks(r.get("company_name")) & page_co]
        if len(hits) != 1:
            if len(hits) > 1:
                print(f"  SKIP {slug}: {len(hits)} same-day letters match the company "
                      f"-- resolve by hand")
                skipped += 1
            continue
        r = hits[0]
        fn = str(r.get("file_name") or "").strip()
        if not re.match(r"^[\w.\-]+\.pdf$", fn):
            continue
        apps = r.get("application_number")
        app = ", ".join(apps) if isinstance(apps, list) else str(apps or "")
        d = dt.date.fromisoformat(dcd)
        MONN = ["", "January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]
        card = (f'{B}<div style="background:#0c1d38;border:1px solid #2a496f;'
                f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;'
                f'font-size:14px"><b style="color:#e3ba5e">The FDA\'s own letter</b> '
                f'&middot; <a href="https://download.open.fda.gov/crl/{fn}" '
                f'rel="noopener">Complete Response Letter, {_html.escape(app)} (PDF)'
                f'</a>, dated {MONN[d.month]} {d.day}, {d.year}, released under '
                f'FDA\'s CRL transparency program.</div>{E}')
        if B in doc:
            new = doc.split(B, 1)[0] + card + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            if anchor not in doc:
                continue
            i = doc.index(anchor) + len(anchor)
            new = doc[:i] + card + doc[i:]
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            linked += 1
            print(f"  /fda-decision/{slug}: {app} letter linked")
    print(f"CRL letters: {linked} page(s) linked, {skipped} ambiguous-skipped "
          f"(corpus {len(recs)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
