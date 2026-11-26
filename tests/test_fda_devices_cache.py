# -*- coding: utf-8 -*-
"""Guard: fetch_fda_devices keeps only FDA-recorded device decisions and never guesses a ticker.

2026-11-26 (David: "add ... Device pdufas and releases"). Two parts:
  1. Logic, on SYNTHETIC records (shaped like openFDA's pma.json / 510k.json; the applicant names are
     invented so no fixture can be mistaken for a real decision):
       * a PMA original and a panel-track supplement are kept; a 180-day supplement is not
       * a De Novo (DEN) record is kept; a plain 510(k) is not
       * an applicant gets a ticker only from an exact one-company SEC name match or a sourced alias
       * an SEC name shared by two companies (two CIKs) gives no ticker
  2. The committed cache, when present: every row has an FDA id, an ISO decision date, a link to the FDA's
     own database record built from that id, and a ticker only with a recorded match method.

    python tests/test_fda_devices_cache.py          (PLANT=1 lets a fuzzy match through; the guard must fail)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fetch_fda_devices as D  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


SEC_ROWS = {
    "0": {"cik_str": 1, "ticker": "ZZQA", "title": "ZEPHYRQUILL MEDICAL INC"},
    "1": {"cik_str": 2, "ticker": "ZZQB", "title": "TWINNAME CORP"},
    "2": {"cik_str": 3, "ticker": "ZZQC", "title": "TWINNAME INC"},       # same normalized name, other CIK
    "3": {"cik_str": 1, "ticker": "ZZQA.W", "title": "ZEPHYRQUILL MEDICAL INC"},  # same CIK, second line: still one company
}
tmp_sec = os.path.join(HERE, "tests", "_tmp_sec_devices.json")
json.dump(SEC_ROWS, open(tmp_sec, "w"))
try:
    sec = D.sec_index(tmp_sec)
finally:
    os.remove(tmp_sec)
aliases = {D.norm("Quillwork Neuro Systems GmbH"): {"ticker": "ZZQD", "source": "synthetic fixture"}}

if os.environ.get("PLANT") == "1":
    real = D.ticker_for
    D.ticker_for = lambda a, s, al: real(a, s, al) if real(a, s, al)[0] else ("ZZQB", "sec_name")

pma_orig = {"pma_number": "P990001", "supplement_number": "", "applicant": "Zephyrquill Medical, Inc.",
            "trade_name": "SYNTHETIC VALVE", "generic_name": "valve", "product_code": "ZZZ",
            "advisory_committee_description": "Cardiovascular", "decision_code": "APPR",
            "date_received": "2025-01-02", "decision_date": "2025-09-30"}
pma_panel = dict(pma_orig, supplement_number="S012", supplement_type="Panel Track", decision_date="2025-10-01")
pma_180 = dict(pma_orig, supplement_number="S013", supplement_type="180-Day", decision_date="2025-10-02")
den = {"k_number": "DEN990002", "applicant": "Quillwork Neuro Systems GmbH", "device_name": "SYNTHETIC STIMULATOR",
       "product_code": "ZZY", "decision_code": "DENG", "date_received": "20240105", "decision_date": "20250210"}
k510 = dict(den, k_number="K990003")
unknown = dict(pma_orig, pma_number="P990004", applicant="Zephyrquill Medical Devices Europe BV")
twin = dict(pma_orig, pma_number="P990005", applicant="Twinname, Inc.")

r = D.pma_row(pma_orig, sec, aliases)
check(r and r["pathway"] == "PMA" and r["id"] == "P990001", f"PMA original not kept as PMA: {r}")
check(r and r["ticker"] == "ZZQA" and r["ticker_match"] == "sec_name", f"exact SEC name not matched: {r}")
check(r and r["fda_url"].endswith("pma.cfm?id=P990001"), f"PMA link wrong: {r and r['fda_url']}")
r = D.pma_row(pma_panel, sec, aliases)
check(r and r["pathway"] == "PMA panel-track supplement" and r["id"] == "P990001S012", f"panel-track not kept: {r}")
check(D.pma_row(pma_180, sec, aliases) is None, "a 180-day supplement was kept")
r = D.den_row(den, sec, aliases)
check(r and r["id"] == "DEN990002" and r["decision_date"] == "2025-02-10", f"De Novo not kept: {r}")
check(r and r["ticker"] == "ZZQD" and r["ticker_match"] == "alias", f"sourced alias not used: {r}")
check(r and r["fda_url"].endswith("denovo.cfm?id=DEN990002"), f"De Novo link wrong: {r and r['fda_url']}")
check(D.den_row(k510, sec, aliases) is None, "a plain 510(k) was kept as De Novo")
r = D.pma_row(dict(pma_orig, pma_number="H990006"), sec, aliases)
check(r and r["pathway"] == "HDE", f"an H-number was not labeled HDE: {r and r['pathway']}")
check(r and "cfhde/hde.cfm?id=H990006" in r["fda_url"], f"an HDE is not linked to the HDE database: {r and r['fda_url']}")
tmp_cache = os.path.join(HERE, "tests", "_tmp_devices_cache.json")
json.dump({"rows": [{"pathway": "De Novo"}] * 100 + [{"pathway": "PMA"}] * 50}, open(tmp_cache, "w"))
try:
    check(D.shrinkage([{"pathway": "PMA"}] * 50, tmp_cache) != "", "a pull that lost every De Novo row would replace the cache")
    check(D.shrinkage([{"pathway": "De Novo"}] * 100 + [{"pathway": "PMA"}] * 51, tmp_cache) == "",
          "a pull that grew was refused")
finally:
    os.remove(tmp_cache)
r = D.pma_row(unknown, sec, aliases)
check(r and r["ticker"] is None, f"a subsidiary-like name got a ticker: {r and r['ticker']}")
r = D.pma_row(twin, sec, aliases)
check(r and r["ticker"] is None, f"an SEC name shared by two companies gave a ticker: {r and r['ticker']}")

# --- the committed cache --------------------------------------------------------------------------------
cache = os.path.join(HERE, "_fda_devices.json")
if os.path.exists(cache):
    d = json.load(open(cache))
    rows = d.get("rows") or []
    check(len(rows) == d.get("count"), "cache count does not match its rows")
    if d.get("since", 9999) <= 2012:
        for k, v in D.FLOORS.items():
            n = sum(1 for x in rows if x.get("pathway") == k)
            check(n >= v, f"cache holds only {n} {k} rows (floor {v})")
    ids = set()
    for row in rows:
        rid = row.get("id", "")
        check(rid not in ids, f"duplicate id {rid}")
        ids.add(rid)
        check(re.fullmatch(r"[PHN]\d{5,6}(S\d+)?|DEN\d{6}", rid or ""), f"bad FDA id {rid!r}")
        check(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("decision_date") or ""), f"{rid}: bad decision date")
        want = D.record_url(rid)
        check(row.get("fda_url") == want, f"{rid}: link is not the FDA record for its id")
        if row.get("ticker"):
            check(row.get("ticker_match") in ("sec_name", "alias"), f"{rid}: ticker without a match method")
        if row.get("supplement_number"):
            check(D.is_panel_track(row.get("supplement_type")), f"{rid}: a non-panel-track supplement is in the cache")

if fails:
    print("FAIL test_fda_devices_cache:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ok test_fda_devices_cache")
