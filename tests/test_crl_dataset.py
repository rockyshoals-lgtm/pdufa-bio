# -*- coding: utf-8 -*-
"""CI guard: the CRL dataset download (build_crl_dataset.py) matches the FDA release it was built from.

  * crl-letters.json has one row per distinct Complete Response Letter in the corpus the CRL pages read (the /crl
    repeat rule), with the columns and licence its meta states, and meta.openfda_last_updated is the corpus's.
  * crl-letters.csv holds the same rows, in the same order.
  * A dated copy exists for that FDA release holding these rows, and every dated copy's own meta names its date (and,
    for a second copy of one release, the day it was read).
  * /crl/facts carries the download line and one schema.org Dataset with a licence and both downloads, and the row
    count equals the CRL count /crl/facts and the /crl hub state.
  * No row is dated after the day the release was read (openFDA can add a letter without moving its own
    last_updated; a row after that stated date needs the meta rule saying so); every letter_pdf is the FDA's own address.

PLANT=1 drops one CSV row in memory and must FAIL.

    python tests/test_crl_dataset.py      (fix: python build_crl_dataset.py)
"""
import csv
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
D = os.path.join(SITE, "crl", "data")


def main():
    import build_crl_dataset as B
    from build_feeds import crl_letters
    fails = []
    jp, cp = os.path.join(D, "crl-letters.json"), os.path.join(D, "crl-letters.csv")
    if not (os.path.exists(jp) and os.path.exists(cp)):
        print("FAIL test_crl_dataset: /crl/data/crl-letters.json or .csv missing; fix: python build_crl_dataset.py")
        return 1
    doc = json.load(io.open(jp, encoding="utf-8"))
    meta, rows = doc.get("meta", {}), doc.get("rows", [])
    letters, last_updated, _ = crl_letters(include_rescinded=True)
    if len(rows) != len(letters):
        fails.append(f"crl-letters.json has {len(rows)} rows; the release holds {len(letters)} distinct CRLs")
    if meta.get("openfda_last_updated") != last_updated:
        fails.append(f"meta.openfda_last_updated {meta.get('openfda_last_updated')} is not the corpus's {last_updated}")
    if meta.get("license") != B.LIC or meta.get("columns") != B.COLS or meta.get("rows") != len(rows):
        fails.append("meta licence, columns or row count does not match the file")
    with io.open(cp, encoding="utf-8-sig", newline="") as f:
        back = list(csv.DictReader(f))
    if os.environ.get("PLANT"):
        back = back[1:]
    if len(back) != len(rows) or any(b["letter_date"] != r["letter_date"] or
                                     b["application_numbers"] != r["application_numbers"] for b, r in zip(back, rows)):
        fails.append(f"crl-letters.csv ({len(back)} rows) does not hold the JSON's {len(rows)} rows in order")
    if back and list(back[0].keys()) != B.COLS:
        fails.append("crl-letters.csv columns are not meta.columns")
    if last_updated and not any(B.sig(json.load(io.open(p, encoding="utf-8")).get("rows", [])) == B.sig(rows)
                                for p in glob.glob(os.path.join(D, f"crl-letters-{last_updated}*.json"))):
        fails.append(f"no dated copy crl-letters-{last_updated}*.json holds this release's rows")
    for p in glob.glob(os.path.join(D, "crl-letters-????-??-??*.json")):
        nm = os.path.basename(p)
        m = re.match(r"crl-letters-(\d{4}-\d{2}-\d{2})(?:-read-(\d{4}-\d{2}-\d{2}))?\.json$", nm)
        dm = json.load(io.open(p, encoding="utf-8")).get("meta", {})
        if not m or dm.get("openfda_last_updated") != m.group(1) or (m.group(2) and dm.get("snapshot_read") != m.group(2)):
            fails.append(f"{nm} is not the release its name says")
    # 2026-11-25 (BLOCKED run 45687661301): openFDA added Capricor's 2026-11-20 letter (BL 125842) to the release and
    # left its own meta.last_updated at 2026-11-18, so a row can be dated after the date openFDA states. What can never
    # happen is a row dated after the day pdufa.bio read the release (snapshot_read, the corpus file's date), and a row
    # after openFDA's stated date must sit under the meta rule that tells a reader why.
    snap = meta.get("snapshot_read") or ""
    from build_crl_facts import CORPUS
    want_snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(CORPUS)) or [None, ""])[1]
    if snap != want_snap:
        fails.append(f"meta.snapshot_read {snap!r} is not the day the corpus was read ({want_snap!r})")
    late = [r["letter_date"] for r in rows if last_updated and r["letter_date"] > last_updated]
    if late and not any(B.LATE_RULE == x for x in meta.get("rules", [])):
        fails.append(f"{len(late)} row(s) dated after openFDA's stated update ({last_updated}) and no meta rule says why")
    for r in rows:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap) and r["letter_date"] > snap:
            fails.append(f"row dated {r['letter_date']} after the day the release was read ({snap})")
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap) and last_updated and r["letter_date"] > last_updated:
            fails.append(f"row dated {r['letter_date']} after the release ({last_updated}) and no read date")
        if r["letter_pdf"] and not r["letter_pdf"].startswith("https://download.open.fda.gov/crl/"):
            fails.append(f"row {r['letter_date']} {r['application_numbers']}: letter_pdf is not the FDA's address")
    fp = os.path.join(SITE, "crl", "facts", "index.html")
    page = io.open(fp, encoding="utf-8", errors="replace").read() if os.path.exists(fp) else ""
    if 'href="/crl/data/crl-letters.csv"' not in page or f"({len(rows)} rows" not in page:
        fails.append("/crl/facts lacks the download line or states another row count")
    lds = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
           if '"Dataset"' in m]
    if len(lds) != 1 or not lds[0].get("license") or len(lds[0].get("distribution", [])) != 2:
        fails.append(f"/crl/facts should carry one licensed Dataset with two downloads (found {len(lds)})")
    # the download and the pages it sits on must say the same count (a stale corpus once gave 444 rows beside 452)
    m = re.search(r"([\d,]+) are Complete Response Letters", page)
    if m and int(m.group(1).replace(",", "")) != len(rows):
        fails.append(f"/crl/facts states {m.group(1)} CRLs; the download has {len(rows)} rows")
    hp = os.path.join(SITE, "crl", "index.html")
    hub = io.open(hp, encoding="utf-8", errors="replace").read() if os.path.exists(hp) else ""
    m = re.search(r"([\d,]+) released CRLs", hub)
    if m and int(m.group(1).replace(",", "")) != len(rows):
        fails.append(f"/crl states {m.group(1)} released CRLs; the download has {len(rows)} rows")
    if fails:
        print(f"FAIL test_crl_dataset: {len(fails)} problem(s); fix: python build_crl_dataset.py")
        for f in fails[:20]:
            print("  " + f)
        return 1
    print(f"PASS test_crl_dataset: {len(rows)} rows, openFDA {last_updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
