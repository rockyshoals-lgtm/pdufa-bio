# -*- coding: utf-8 -*-
"""Guard: /devices/decisions shows the FDA's own device records, row for row.

2026-11-26 (David: "add ... Device pdyfas"). Checks, against _fda_devices.json:
  * rules: decision words only where the FDA defines the code (APPR, APWD, APRL from openFDA's PMA field reference;
    DENG from the FDA's De Novo record pages); an undefined code (APCB) is shown as the code, never given a meaning;
    review days are received-to-decision calendar days; only approvals and grants are listed
  * hub: the lede counts and every by-year row recounted from the cache
  * the hub's latest rows and every year page: each row exactly as built from its FDA record, in order; ledes and the
    by-year table recounted
  * no placeholder ticker from the SEC list ('NONE.')
  * the CSV: one row per listed record, every link an FDA database page

    python tests/test_device_decisions.py          (PLANT=1 adds a row the FDA never published; the guard must fail)
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_device_decisions as B  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src", "devices", "decisions")


def rule_checks():
    f = []
    if B.decision_words("APPR") != "Approved" or B.decision_words("DENG") != "Granted":
        f.append("APPR / DENG not shown as the FDA defines them")
    if "withdrawn" not in B.decision_words("APWD") or "reclassified" not in B.decision_words("APRL"):
        f.append("APWD / APRL lose the later withdrawal or reclassification the FDA's code records")
    if "does not define" not in B.decision_words("APCB"):
        f.append("an undefined code is given a meaning")
    if B.review_days({"date_received": "2026-01-01", "decision_date": "2026-01-31"}) != 30 or \
            B.review_days({"date_received": "2026-02-01", "decision_date": "2026-01-31"}) is not None:
        f.append("review days are not received-to-decision calendar days")
    if B.ticker_of({"ticker": "NONE."}) or B.ticker_of({"ticker": "BSX"}) != "BSX":
        f.append("the SEC list's placeholder 'NONE.' would show as a ticker")
    for p, code in (("De Novo", "DENW"), ("De Novo", "DENY"), ("PMA", "DENY"), ("PMA", "WTDR"), ("HDE", "APPR"),
                    ("510(k)", "SESE")):
        if code in B.SHOWN_CODES.get(p, set()):
            f.append(f"{p} {code} would be listed as an approval or grant")
    return f


def page_checks(plant=False):
    f = []
    hub = os.path.join(SITE, "index.html")
    if not os.path.isfile(B.CACHE):
        return f, "no cache (skipped page checks)"
    c, rows = B.load(B.CACHE)
    if not os.path.isfile(hub):
        # in the site build the step before the guards writes the pages: missing pages there are a failed build
        if os.environ.get("GITHUB_ACTIONS") and rows:
            return ["/devices/decisions was not built though the cache has rows"], ""
        return f, "no built /devices/decisions (skipped page checks)"
    by_id = {r["id"]: r for r in rows}
    tdir = os.path.join(HERE, "pdufa_site_src", "ticker")
    tickers = {t for t in (os.listdir(tdir) if os.path.isdir(tdir) else [])
               if os.path.isfile(os.path.join(tdir, t, "index.html"))}
    years = sorted({r["decision_date"][:4] for r in rows}, reverse=True)
    doc = io.open(hub, encoding="utf-8").read()
    if plant:
        doc = doc.replace("<td>Granted</td>", "<td>Approved</td>", 1)
    cnt = {p: sum(1 for r in rows if r["pathway"] == p) for p in B.PATHWAYS}
    m = re.search(r"list ([\d,]+) device approvals and grants from (\d{4}) through [^:]+: ([\d,]+) PMA original "
                  r"approvals, ([\d,]+) PMA panel-track supplement approvals and ([\d,]+) De Novo grants", doc)
    nums = [int(x.replace(",", "")) for x in m.groups()] if m else None
    if not nums or nums != [len(rows), int(rows[-1]["decision_date"][:4]), cnt["PMA"],
                            cnt["PMA panel-track supplement"], cnt["De Novo"]]:
        f.append(f"hub lede counts {nums} do not match the cache")
    yrows_hub = re.findall(r'<tr data-dev-year="(\d{4})">(.*?)</tr>', doc, re.S)
    if [y for y, _ in yrows_hub] != years:
        f.append(f"hub by-year rows {[y for y, _ in yrows_hub]} are not the cache's years {years}")
    for y, cells in yrows_hub:
        tds = re.findall(r"<td>(.*?)</td>", cells, re.S)
        yr = [r for r in rows if r["decision_date"][:4] == y]
        want = [str(sum(1 for r in yr if r["pathway"] == p)) for p in B.PATHWAYS] + [str(len(yr))]
        want += [B.fmt_med(B.med([B.review_days(r) for r in yr if r["pathway"] == p])) for p in ("PMA", "De Novo")]
        if tds[1:7] != want:
            f.append(f"hub {y}: cells {tds[1:7]}, the cache gives {want}")
    # every listed row, on the hub and on the year pages, is exactly the row built from its FDA record
    got = re.findall(r'<tr data-dev="[^"]+">.*?</tr>', doc, re.S)
    want = [B.row_html(r, tickers) for r in rows[:B.RECENT]]
    if got != want:
        bad = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
        f.append(f"hub latest decisions differ from the FDA records at row {bad + 1} ({len(got)} rows, want "
                 f"{len(want)})")
    seen = set()
    for y in sorted(d for d in os.listdir(SITE) if re.fullmatch(r"20\d\d", d)):
        if y not in years:
            f.append(f"/devices/decisions/{y}: no cache rows for {y}")
            continue
        ydoc = io.open(os.path.join(SITE, y, "index.html"), encoding="utf-8").read()
        if plant and not seen:
            ydoc = ydoc.replace("</table>", '<tr data-dev="P999999"><td>x</td></tr></table>', 1)
        yr = [r for r in rows if r["decision_date"][:4] == y]
        got = re.findall(r'<tr data-dev="[^"]+">.*?</tr>', ydoc, re.S)
        want = [B.row_html(r, tickers) for r in yr]
        if got != want:
            bad = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            f.append(f"/devices/decisions/{y}: rows differ from the FDA records at row {bad + 1} ({len(got)} rows, "
                     f"the cache has {len(want)})")
        cn = {p: sum(1 for r in yr if r["pathway"] == p) for p in B.PATHWAYS}
        lm = re.search(r"list (\d+) device approvals and grants dated " + y + r"[^:]*: (\d+) PMA original approvals, "
                       r"(\d+) PMA panel-track supplement approvals and (\d+) De Novo grants", ydoc)
        if not lm or [int(x) for x in lm.groups()] != [len(yr), cn["PMA"], cn["PMA panel-track supplement"],
                                                         cn["De Novo"]]:
            f.append(f"/devices/decisions/{y}: lede counts do not match the cache")
        seen.add(y)
    if seen != set(years):
        f.append(f"years with no page: {sorted(set(years) - seen)}")
    path = os.path.join(SITE, "data", "device-decisions.csv")
    if not os.path.isfile(path):
        f.append("device-decisions.csv missing")
    else:
        crows = list(csv.reader(io.open(path, encoding="utf-8")))
        if not crows or crows[0] != B.COLUMNS:
            f.append("CSV header is not the documented columns")
        elif crows[1:] != [B.csv_row(r) for r in rows]:
            bad = next((i for i, (a, b) in enumerate(zip(crows[1:], [B.csv_row(r) for r in rows])) if a != b),
                       min(len(crows) - 1, len(rows)))
            f.append(f"CSV differs from the FDA records at data row {bad + 1}")
    for r in rows:
        if r.get("ticker") and not B.ticker_of(r) and f"({B.esc(r['ticker'])})" in doc:
            f.append(f"placeholder ticker {r['ticker']!r} shown on the hub")
    return f, f"{len(rows)} FDA records on {len(years)} year pages checked"


def main():
    f = rule_checks()
    pf, note = page_checks(plant=os.environ.get("PLANT") == "1")
    f += pf
    if f:
        print("FAIL test_device_decisions:\n  " + "\n  ".join(f[:40]))
        return 1
    print(f"ok test_device_decisions: rules hold; {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
