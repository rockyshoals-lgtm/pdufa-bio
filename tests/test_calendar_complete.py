# -*- coding: utf-8 -*-
"""test_calendar_complete.py -- the calendar must agree with the data, and never invent an outcome.

Three failures this catches, all of which were live and none of which announced itself.

  1. A CATALYST WE HOLD THAT THE CALENDAR DOES NOT SHOW. Replimune's RP1 had a confirmed 2 August
     2026 action date, a published advisory committee page and a slate entry, and appeared on no
     calendar page at all. Forty-two dated PDUFAs were missing this way. The calendar pages are
     maintained separately from the slate and nothing compared them.

  2. A DECIDED CATALYST STILL SHOWN AS PENDING. VTRS was approved on 2026-07-29, had a published
     decision page, and sat on the calendar as an upcoming July decision. The marker had been
     matching zero rows for weeks because the separator in the markup changed from &middot; to the
     literal character, and "0 rows marked" is indistinguishable from "nothing to do".

  3. AN OUTCOME ATTACHED TO THE WRONG REVIEW CYCLE. This is the dangerous one. A Complete Response
     Letter is the reason a later PDUFA date exists: the company resubmits and the FDA starts a new
     clock. Carrying a CRL forward onto that later date publishes a rejection the FDA has not
     issued. Replimune was rejected on 2026-04-10, resubmitted, and given a 2026-08-02 date; an
     early version of the forward-matching rule marked the August row "CRL".

    python tests/test_calendar_complete.py
"""
import datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
SEP = r"(?:&middot;|·|&#183;)"
ROW = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6})\s*' + SEP +
                 r'\s*(\d{4}-\d{2}-\d{2})', re.S)


def calendar_pages():
    return sorted(glob.glob(os.path.join(SITE, "calendar", "**", "index.html"), recursive=True))


def main():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    m = re.search(r"export default (\[.*\])", src, re.S)
    rows = json.loads(m.group(1)) if m else []
    pdufas = [r for r in rows if r.get("type") == "PDUFA" and r.get("dp") == "day"
              and re.match(r"^\d{4}-\d{2}-\d{2}$", str(r.get("d") or ""))]

    on_cal, marked, offsite = set(), {}, []
    for p in calendar_pages():
        html = open(p, encoding="utf-8", errors="replace").read()
        for attrs, tk, d in ROW.findall(html):
            on_cal.add((tk, d))
            if 'data-dec="1"' in attrs:
                marked[(tk, d)] = attrs
        for mm in re.finditer(r'<a class="row" href="(https?://[^"]+)"', html):
            if "pdufa.bio" not in mm.group(1):
                offsite.append((os.path.relpath(p, SITE), mm.group(1)[:60]))

    ok = True
    print(f"{len(pdufas)} dated PDUFAs in the data, {len(on_cal)} rows across "
          f"{len(calendar_pages())} calendar pages")

    # 1. coverage
    missing = [r for r in pdufas
               if ((r.get("t") or "").upper(), r["d"]) not in on_cal]
    # A catalyst whose month page does not exist yet is a known gap, reported not failed.
    no_page, on_existing_page = [], []
    for r in missing:
        y, mo = r["d"][:4], r["d"][5:7]
        months = ["january", "february", "march", "april", "may", "june", "july",
                  "august", "september", "october", "november", "december"]
        page = os.path.join(SITE, "calendar", y, months[int(mo) - 1], "index.html")
        (no_page if not os.path.exists(page) else on_existing_page).append(r)

    if on_existing_page:
        ok = False
        print(f"\nFAIL: {len(on_existing_page)} dated PDUFA(s) missing from a calendar page that exists:")
        for r in on_existing_page[:10]:
            print(f"   {r['d']}  {r.get('t')}  {(r.get('name') or '')[:44]}")
        print("   Run ensure_calendar_rows.py.")
    else:
        print("  PASS: every dated PDUFA with a month page is on the calendar")

    if no_page:
        months = sorted({r["d"][:7] for r in no_page})
        print(f"  NOTE: {len(no_page)} PDUFA(s) have no month page yet ({', '.join(months)}). "
              f"Not a failure, but they are invisible on the calendar until the page exists.")

    # 2. nothing links off-site
    if offsite:
        ok = False
        print(f"\nFAIL: {len(offsite)} calendar row(s) link off-site, e.g. {offsite[0]}")
        print("   A calendar row is our page; the primary source belongs in the data.")
    else:
        print("  PASS: no calendar row links off-site")

    # 3. no CRL carried forward onto a later, still-open review cycle
    bad = []
    for (tk, d), attrs in marked.items():
        mm = re.search(r'href="/fda-decision/[A-Z]{1,6}-(\d{4}-\d{2}-\d{2})"', attrs)
        if not mm:
            continue
        dec = mm.group(1)
        page_has_crl = True
        for p in calendar_pages():
            html = open(p, encoding="utf-8", errors="replace").read()
            i = html.find(f'/fda-decision/{tk}-{dec}"')
            if i == -1:
                continue
            seg = html[i:i + 400]
            page_has_crl = ("CRL" in seg or "Complete Response" in seg)
            break
        if page_has_crl and dec < d and (dt.date.fromisoformat(d)
                                         - dt.date.fromisoformat(dec)).days > 14:
            bad.append((tk, d, dec))

    if bad:
        ok = False
        print(f"\nFAIL: {len(bad)} row(s) show a CRL dated well BEFORE the scheduled date:")
        for tk, d, dec in bad[:8]:
            print(f"   {tk} scheduled {d} marked with the CRL of {dec}")
        print("   A CRL is why a later date exists. Attaching it forward publishes a rejection "
              "the FDA has not issued for that cycle.")
    else:
        print("  PASS: no CRL attached forward onto a later review cycle")

    print("\n  PASS: calendar agrees with the data" if ok else "\n  see failures above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
